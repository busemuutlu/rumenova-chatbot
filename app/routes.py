import os
import uuid
import json
from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename
from config import Config
from app.services.ai_service import AIService, QUESTION_POOLS, ai_service
from app.services.brief import build_wix_summary_dict, save_brief_snapshot
from app.services.conversation import chat_init, chat_turn
from app.database import (
    get_all_professionals, get_professionals_by_service,
    get_expert_or_office_by_code, get_available_slots,
    get_or_create_session, get_latest_active_session, update_session, complete_form_submission,
    get_all_completed_leads, lead_ekle, tum_leadler
)


main_bp = Blueprint("main", __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- SAĞLIK KONTROLÜ (Modül E: /health) ---

@main_bp.route("/health")
def health_check():
    """Yönerge & Yazılım Kontrol Modül E: Backend canlılık kontrolü."""
    return jsonify({
        "basari": True,
        "status": "ok",
        "service": "Rumenova Backend",
        "version": "1.0.0"
    })

# --- WEB SAYFALARI ---

@main_bp.route("/")
def index():
    prof = get_all_professionals()
    return render_template("index.html", experts=prof["experts"], offices=prof["offices"])

@main_bp.route("/dashboard")
def dashboard():
    expert_id = request.args.get("expert_id")
    office_id = request.args.get("office_id")
    leads = get_all_completed_leads(expert_id=expert_id, office_id=office_id)
    prof = get_all_professionals()
    return render_template("dashboard.html", leads=leads, experts=prof["experts"], offices=prof["offices"])

# --- CHATBOT OTURUM API'LERİ ---

@main_bp.route("/api/session/init", methods=["POST"])
def session_init():
    data = request.get_json() or {}
    token = data.get("session_token")
    expert_code = data.get("expert_code")
    office_code = data.get("office_code")
    service = data.get("service")

    session = get_or_create_session(token)
    updates = {}

    # Profil Butonundan Giriş (Madde 4 & 5)
    if expert_code:
        found = get_expert_or_office_by_code(expert_code)
        if found and found["type"] == "expert":
            exp = found["data"]
            updates["selected_expert_id"] = exp["id"]
            if exp["office_id"]:
                updates["selected_office_id"] = exp["office_id"]
                updates["selected_team_member_id"] = exp["id"]
            if len(exp["service_areas"]) == 1:
                updates["service_type"] = exp["service_areas"][0]

    elif office_code:
        found = get_expert_or_office_by_code(office_code)
        if found and found["type"] == "office":
            off = found["data"]
            updates["selected_office_id"] = off["id"]
            if len(off["service_areas"]) == 1:
                updates["service_type"] = off["service_areas"][0]

    if service:
        updates["service_type"] = service

    if updates:
        update_session(session["session_token"], updates)
        session = get_or_create_session(session["session_token"])

    next_q = None
    if session.get("service_type") and (session.get("selected_expert_id") or session.get("selected_office_id")):
        next_q = AIService.get_next_question(
            session["service_type"],
            session.get("collected_data", {}),
            (session.get("flow_state") or {}).get("skipped_fields", [])
        )

    slots = []
    if session.get("selected_expert_id") or session.get("selected_office_id"):
        slots = get_available_slots(
            expert_id=session.get("selected_expert_id"),
            office_id=session.get("selected_office_id")
        )

    # Seçilen uzman / ofis isimlerini çözümle
    expert_name = None
    office_name = None
    all_profs = get_all_professionals()

    if session.get("selected_expert_id"):
        for e in all_profs.get("experts", []):
            if e["id"] == session["selected_expert_id"]:
                expert_name = e["name"]
                break
        if not expert_name:
            for o in all_profs.get("offices", []):
                for tm in o.get("team_members", []):
                    if tm["id"] == session["selected_expert_id"]:
                        expert_name = tm["name"]
                        office_name = o["name"]
                        break

    if not office_name and session.get("selected_office_id"):
        for o in all_profs.get("offices", []):
            if o["id"] == session["selected_office_id"]:
                office_name = o["name"]
                break

    return jsonify({
        "success": True,
        "session_token": session["session_token"],
        "service_type": session.get("service_type"),
        "selected_expert_id": session.get("selected_expert_id"),
        "selected_expert_name": expert_name,
        "selected_office_id": session.get("selected_office_id"),
        "selected_office_name": office_name,
        "collected_data": session.get("collected_data", {}),
        "uploaded_images": session.get("uploaded_images", []),
        "selected_slot_id": session.get("selected_slot_id"),
        "selected_slot_text": session.get("selected_slot_text"),
        "is_brief_approved": session.get("is_brief_approved", 0),
        "brief_summary": session.get("brief_summary", {}),
        "chat_messages": session.get("chat_messages", []),
        "available_slots": slots,
        "next_question": next_q
    })

@main_bp.route("/api/session/select-service", methods=["POST"])
def session_select_service():
    """Hizmet alanı seçildiğinde oturuma kaydeder."""
    data = request.get_json() or {}
    token = data.get("session_token")
    service_type = data.get("service_type")
    service_title = data.get("service_title", service_type)

    if not token or not service_type:
        return jsonify({"error": "Eksik parametre"}), 400

    session = get_or_create_session(token)
    chat_msgs = session.get("chat_messages", [])
    chat_msgs.append({"role": "user", "content": f"{service_title} alanını seçtim."})
    chat_msgs.append({"role": "assistant", "content": "Bu alanda hangi mimar veya ofisle görüşmek istersiniz?"})

    update_session(token, {
        "service_type": service_type,
        "chat_messages": chat_msgs
    })
    return jsonify({"success": True, "service_type": service_type})

@main_bp.route("/api/session/select-expert", methods=["POST"])
def session_select_expert():
    """Mimar veya ofis seçildiğinde kaydeder ve ilk soruyu döner."""
    data = request.get_json() or {}
    token = data.get("session_token")
    expert_id = data.get("expert_id")
    office_id = data.get("office_id")
    prof_name = data.get("name", "Uzmanımız")

    if not token:
        return jsonify({"error": "Oturum eksik"}), 400

    session = get_or_create_session(token)
    service_type = session.get("service_type", "mimari")
    collected = session.get("collected_data", {})
    chat_msgs = session.get("chat_messages", [])

    updates = {}

    # 1. Bireysel Uzman Seçildiyse
    if expert_id:
        updates["selected_expert_id"] = expert_id
        first_q = AIService.get_next_question(service_type, collected)

        chat_msgs.append({"role": "user", "content": f"{prof_name} ile görüşmek istiyorum."})
        chat_msgs.append({"role": "assistant", "content": f"Harika bir tercih! {prof_name} ile ön görüşme sorularımıza başlıyoruz."})
        if first_q:
            chat_msgs.append({"role": "assistant", "content": first_q["question"]})
        updates["chat_messages"] = chat_msgs

        update_session(token, updates)
        return jsonify({
            "success": True,
            "need_team_selection": False,
            "next_question": first_q,
            "collected_data": collected
        })

    # 2. Ofis Seçildiyse -> Ekip Üyelerini Kontrol Et
    if office_id:
        updates["selected_office_id"] = office_id
        prof_data = get_all_professionals()
        office = next((o for o in prof_data["offices"] if o["id"] == office_id), None)
        
        team_members_in_service = []
        if office and "team_members" in office:
            team_members_in_service = [
                m for m in office["team_members"] 
                if service_type in m.get("service_areas", [])
            ]

        chat_msgs.append({"role": "user", "content": f"{prof_name} ile görüşmek istiyorum."})

        # Kural: Eğer o alanda 2 veya daha fazla uzman varsa seçtir
        if len(team_members_in_service) > 1:
            chat_msgs.append({"role": "assistant", "content": f"{office['name']} ekibimizden hangi uzmanımızla görüşmek istersiniz?"})
            updates["chat_messages"] = chat_msgs
            update_session(token, updates)
            return jsonify({
                "success": True,
                "need_team_selection": True,
                "office_name": office["name"],
                "team_members": team_members_in_service
            })
        
        # Kural: Eğer yalnızca 1 uzman varsa doğrudan o uzman ile başla
        elif len(team_members_in_service) == 1:
            single_expert = team_members_in_service[0]
            updates["selected_expert_id"] = single_expert["id"]
            first_q = AIService.get_next_question(service_type, collected)

            chat_msgs.append({"role": "assistant", "content": f"{office['name']} ekibinden {single_expert['name']} ile ön görüşmenize başlayalım."})
            if first_q:
                chat_msgs.append({"role": "assistant", "content": first_q["question"]})
            updates["chat_messages"] = chat_msgs

            update_session(token, updates)
            return jsonify({
                "success": True,
                "need_team_selection": False,
                "auto_expert": single_expert,
                "office_name": office["name"],
                "next_question": first_q,
                "collected_data": collected
            })
        else:
            # Ekip üyesi tanımlanmamışsa ofis olarak devam et
            first_q = AIService.get_next_question(service_type, collected)
            chat_msgs.append({"role": "assistant", "content": f"{office['name']} ile ön görüşmenize başlayalım."})
            if first_q:
                chat_msgs.append({"role": "assistant", "content": first_q["question"]})
            updates["chat_messages"] = chat_msgs

            update_session(token, updates)
            return jsonify({
                "success": True,
                "need_team_selection": False,
                "next_question": first_q,
                "collected_data": collected
            })


@main_bp.route("/api/session/message", methods=["POST"])
def session_message():
    """Kullanıcının yazdığı cevabı alır, birden fazla bilgiyi çıkarır ve sonraki tek soruyu döner."""
    data = request.get_json() or {}
    token = data.get("session_token")
    message_text = data.get("message", "").strip()
    current_field = data.get("current_field")

    if not token or not message_text:
        return jsonify({"error": "Oturum veya mesaj eksik."}), 400

    session = get_or_create_session(token)
    service_type = session.get("service_type", "mimari")
    collected = session.get("collected_data", {})
    chat_msgs = session.get("chat_messages", [])

    # Alan bazında oturumda tutulan akış durumu (atlanan alanlar, tahmin istenen alanlar)
    flow_state = session.get("flow_state") or {}
    skipped_fields = flow_state.setdefault("skipped_fields", [])
    estimate_asked = flow_state.setdefault("estimate_asked", {})
    field_key = current_field or "_genel"
    question_def = AIService.get_question_by_field(service_type, current_field) if current_field else None

    # Kullanıcı mesajını ekle
    chat_msgs.append({"role": "user", "content": message_text})

    is_skipping = message_text.lower() in ["geç", "gec", "atla", "devam", "bilmiyorum geç", "pas"]
    notice = None
    answer_handled = False  # True ise bu mesaj bu alanın cevabı olarak işlendi; ayrıca çıkarım yapılmaz

    def stay_on_question(reply, extra):
        """Aynı soruda kalır: yanıtı ve akış durumunu kaydeder."""
        chat_msgs.append({"role": "assistant", "content": reply})
        update_session(token, {"chat_messages": chat_msgs, "flow_state": flow_state})
        payload = {
            "success": True,
            "reply": reply,
            "next_question": None,  # aynı soruda kal
            "collected_data": collected,
            "is_complete": False
        }
        payload.update(extra)
        return jsonify(payload)

    if is_skipping:
        # 'Geç' cevabı: değer olarak kaydedilmez; alan 'atlanmış' işaretlenir, soru tekrar sorulmaz
        if current_field and current_field not in skipped_fields:
            skipped_fields.append(current_field)
        answer_handled = True
        notice = Config.MSG_SKIPPED
    else:
        # 0. Doğrudan Yapay Zekâ İletişimi (Komut: /ai, /sor, @nova veya Serbest Soru)
        is_direct_ai, ai_query = AIService.is_free_question_or_command(message_text)
        if is_direct_ai:
            current_q_text = question_def.get("question") if question_def else None
            ai_reply = ai_service.serbest_sohbet_yaniti(
                soru=ai_query,
                mevcut_soru=current_q_text,
                service_type=service_type,
                gecmis=chat_msgs
            )
            return stay_on_question(ai_reply, {"is_ai_chat": True})
        # 1. Anlamsız / Saçma Cevap Kontrolü (Örn: 'asdasd', '123123', '????')
        if AIService.is_gibberish_or_irrelevant(message_text):
            return stay_on_question(
                "Tam olarak ne demek istediğinizi söyler misiniz?",
                {"invalid_input": True}
            )

        # 2. Evet/hayır tipi sorularda düz 'yok / hayır' geçerli bir cevaptır
        if (current_field and question_def and question_def.get("allow_negative")
                and AIService.is_plain_negative(message_text)):
            collected[current_field] = "Yok"
            answer_handled = True

        # 3. Olumsuz / Belirsiz Cevap ('bilmiyorum' vb.): önce tahmin iste, tekrar ederse uzmana bırak
        elif AIService.check_if_uncertain_answer(message_text):
            if not estimate_asked.get(field_key):
                estimate_asked[field_key] = True
                return stay_on_question(Config.MSG_ESTIMATE_REQUEST, {"ask_estimate": True})

            # İkinci kez belirsiz cevap: döngüye girme, uzmanla görüşülecek şekilde not al
            if current_field:
                collected[current_field] = Config.VALUE_TO_DISCUSS
            answer_handled = True
            notice = Config.MSG_ESTIMATE_NOTED

        # 4. Konum Sorusu İse 81 İl Doğrulaması
        elif current_field == "konum":
            prov, dist = AIService.find_turkey_province_and_district(message_text)
            if not prov:
                return stay_on_question(
                    "Projenizin hangi ilde bulunduğunu öğrenebilir miyim? (Örn: İstanbul, Ankara, İzmir, Muğla vb. 81 ilimizden biri)",
                    {"retry_location": True}
                )
            collected["konum"] = f"{prov}, {dist}" if dist else f"{prov}"

        # Son sorulan alanın cevabı (konum yukarıda kaydedildi)
        elif current_field:
            collected[current_field] = message_text

    # Cevabı alınan alan için tahmin sayıcısını sıfırla
    if answer_handled or current_field:
        estimate_asked.pop(field_key, None)

    # Çoklu bilgi çıkarma (Madde 6): yalnızca bu hizmet alanının soru havuzundaki alanlar,
    # atlanmış veya 'uzmanla görüşülecek' işaretli cevaplar üzerine yazılmaz
    if not answer_handled:
        valid_fields = AIService.get_valid_fields(service_type)
        extra_extracted = AIService.extract_info_from_message(message_text, collected)
        for k, v in extra_extracted.items():
            if k in valid_fields and k not in skipped_fields and (k not in collected or not collected[k]):
                collected[k] = v

    # Sonraki tek soru (Cevaplanmış ve atlanmış sorular geçilir!)
    next_q = AIService.get_next_question(service_type, collected, skipped_fields)

    updates = {
        "collected_data": collected,
        "chat_messages": chat_msgs,
        "flow_state": flow_state
    }

    if next_q:
        bot_reply = next_q["question"]
        chat_msgs.append({"role": "assistant", "content": bot_reply})
        update_session(token, updates)

        return jsonify({
            "success": True,
            "reply": bot_reply,
            "notice": notice,
            "next_question": next_q,
            "collected_data": collected,
            "is_complete": False
        })
    else:
        # Sorular tamamlandı -> Uygun Saatler
        bot_reply = "Harika! Projenizle ilgili tüm ön bilgileri kaydettim. Şimdi lütfen görüşme yapmak istediğiniz uygun bir saat seçiniz:"
        chat_msgs.append({"role": "assistant", "content": bot_reply})
        update_session(token, updates)

        slots = get_available_slots(
            expert_id=session.get("selected_expert_id"),
            office_id=session.get("selected_office_id")
        )

        return jsonify({
            "success": True,
            "reply": bot_reply,
            "notice": notice,
            "next_question": None,
            "collected_data": collected,
            "is_complete": True,
            "available_slots": slots
        })

@main_bp.route("/api/session/upload-image", methods=["POST"])
def upload_image():
    token = request.form.get("session_token")
    if 'file' not in request.files or not token:
        return jsonify({"error": "Dosya veya oturum bulunamadı."}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Geçersiz dosya formatı. (Desteklenenler: jpg, png, webp)"}), 400

    session = get_or_create_session(token)
    uploaded = session.get("uploaded_images", [])

    if len(uploaded) >= 3:
        return jsonify({"error": "En fazla 3 görsel yükleyebilirsiniz."}), 400

    unique_filename = f"{uuid.uuid4().hex[:10]}_{secure_filename(file.filename)}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(file_path)

    image_url = f"/static/uploads/{unique_filename}"
    uploaded.append({"url": image_url, "name": file.filename})

    update_session(token, {"uploaded_images": uploaded})

    return jsonify({
        "success": True,
        "image_url": image_url,
        "images": uploaded,
        "message": "Görsel başarıyla yüklendi."
    })

@main_bp.route("/api/session/remove-image", methods=["POST"])
def remove_image():
    data = request.get_json() or {}
    token = data.get("session_token")
    img_url = data.get("image_url")

    session = get_or_create_session(token)
    uploaded = session.get("uploaded_images", [])
    updated_list = [img for img in uploaded if img["url"] != img_url]

    update_session(token, {"uploaded_images": updated_list})
    return jsonify({"success": True, "images": updated_list})

@main_bp.route("/api/session/select-slot", methods=["POST"])
def select_slot():
    data = request.get_json() or {}
    token = data.get("session_token")
    slot_id = data.get("slot_id")
    slot_text = data.get("slot_text")

    session = get_or_create_session(token)
    chat_msgs = session.get("chat_messages", [])
    if slot_text:
        chat_msgs.append({"role": "user", "content": f"Görüşme Saati Tercihim: {slot_text}"})
        chat_msgs.append({"role": "assistant", "content": f"Görüşme saati tercihiniz '{slot_text}' olarak kaydedildi. Lütfen oluşturulan ön brif özetinizi inceleyip onaylayınız."})

    update_session(token, {
        "selected_slot_id": slot_id,
        "selected_slot_text": slot_text,
        "chat_messages": chat_msgs
    })

    return jsonify({"success": True, "message": "Saat tercihi kaydedildi."})

@main_bp.route("/api/session/approve-brief", methods=["POST"])
def approve_brief():
    data = request.get_json() or {}
    token = data.get("session_token")
    extra_note = data.get("extra_note", "")

    session = get_or_create_session(token)
    chat_msgs = session.get("chat_messages", [])
    chat_msgs.append({"role": "user", "content": "Bilgilerimi onaylıyorum."})
    chat_msgs.append({"role": "assistant", "content": Config.MSG_BRIEF_APPROVED})

    update_session(token, {
        "is_brief_approved": 1,
        "extra_note": extra_note,
        "status": "brif_onaylandi",
        "chat_messages": chat_msgs
    })
    if token:
        save_brief_snapshot(token)

    wix_contact_url = f"https://busemutlubg.wixstudio.com/rumenova/ongorusme?session_token={token}"

    return jsonify({
        "success": True,
        "message": Config.MSG_BRIEF_APPROVED,
        "wix_contact_url": wix_contact_url,
        "session_token": token
    })


# Panelde gösterilen durum metinleri (chat_sessions.status -> Wix paneli "durum")
LEAD_STATUS_LABELS = {
    "form_tamamlandi": "Randevu Bekliyor",
    "uzman_onayladi": "Onaylandı",
    "reddedildi": "Reddedildi"
}


def format_panel_lead(lead):
    """Tamamlanmış talebi Wix yönetim paneli / detay sayfası alan adlarıyla döner."""
    brief = lead.get("brief_summary") or build_wix_summary_dict(lead)

    ad = lead.get("client_ad")
    soyad = lead.get("client_soyad")
    if ad is None and soyad is None:
        # Ad/soyad kolonlarından önceki kayıtlar: birleşik isim son boşluktan bölünür
        parts = (lead.get("client_name") or "").rsplit(" ", 1)
        ad, soyad = parts[0], (parts[1] if len(parts) > 1 else "")

    created = lead.get("form_completed_at") or lead.get("created_at") or ""
    return {
        "_id": str(lead["id"]),
        "title": f"talep-{lead['id']:03d}",
        "ad": ad or "",
        "soyad": soyad or "",
        "email": lead.get("client_email") or "",
        "telefon": lead.get("client_phone") or "",
        "mesaj": lead.get("client_form_note") or "",
        "hizmetAlan": brief.get("hizmetAlan", ""),
        "seilenUzman": brief.get("seilenUzman", ""),
        "randevuTarihi": brief.get("randevuTarihi", ""),
        "projeBrifi": brief.get("projeBrifi", ""),
        "projeGorselleri": brief.get("gallery_items", []),
        "durum": LEAD_STATUS_LABELS.get(lead.get("status"), "Randevu Bekliyor"),
        # SQLite CURRENT_TIMESTAMP UTC'dir; Wix tarafı ISO 8601 bekler
        "_createdDate": created.replace(" ", "T") + "Z" if created else ""
    }


@main_bp.route("/api/panel/on-gorusmeler", methods=["GET"])
def panel_on_gorusmeler():
    """Wix 'Ön Görüşme Yönetim Paneli' için tamamlanmış talepler (yeniden eskiye)."""
    leads = [format_panel_lead(l) for l in get_all_completed_leads()]
    return jsonify({"success": True, "items": leads, "totalCount": len(leads)})


@main_bp.route("/api/panel/on-gorusmeler/<int:lead_id>", methods=["GET"])
def panel_on_gorusme_detay(lead_id):
    """Wix 'Ön Görüşme Detayı' sayfası için tek talep."""
    leads = get_all_completed_leads(lead_id=lead_id)
    if not leads:
        return jsonify({"success": False, "error": "Kayıt bulunamadı."}), 404
    return jsonify({"success": True, "item": format_panel_lead(leads[0])})


@main_bp.route("/api/session/wix-summary", methods=["GET"])
def get_session_wix_summary():
    token = request.args.get("session_token")
    if not token:
        return jsonify({"success": False, "error": "session_token parametresi gerekli."}), 400

    session = get_or_create_session(token)
    if not session:
        return jsonify({"success": False, "error": "Oturum bulunamadı."}), 404

    data = build_wix_summary_dict(session)
    return jsonify(data)


@main_bp.route("/api/session/latest", methods=["GET"])
def get_latest_session_summary():
    session = get_latest_active_session()
    if not session:
        return jsonify({"success": False, "error": "Aktif oturum bulunamadı."}), 404

    data = build_wix_summary_dict(session)
    return jsonify(data)




@main_bp.route("/api/wix/complete-form", methods=["POST"])
def wix_complete_form():
    """
    Wix ön görüşme formunun TEK kayıt noktası (Wix CMS/dataset kullanılmaz).
    Ad/soyad ayrı (ad, soyad) veya birleşik (name) gelebilir; telefon opsiyoneldir.
    Chatbot oturumu (session_token) yoksa veya bulunamazsa form yeni bir talep olarak kaydedilir.
    """
    data = request.get_json() or {}
    token = (data.get("session_token") or "").strip()
    ad = (data.get("ad") or "").strip()
    soyad = (data.get("soyad") or "").strip()
    client_name = f"{ad} {soyad}".strip() or (data.get("name") or "").strip()
    client_email = (data.get("email") or "").strip()
    client_phone = (data.get("phone") or data.get("telefon") or "").strip()
    client_note = (data.get("note") or data.get("not") or "").strip()

    if not client_name or not client_email:
        return jsonify({
            "success": False,
            "error": "missing_fields",
            "message": "Lütfen ad, soyad ve e-posta alanlarını doldurun."
        }), 400

    if "@" not in client_email or "." not in client_email.split("@")[-1]:
        return jsonify({
            "success": False,
            "error": "invalid_email",
            "message": "Lütfen geçerli bir e-posta adresi girin."
        }), 400

    form_args = (client_name, client_email, client_phone, client_note, ad or None, soyad or None)
    result = complete_form_submission(token, *form_args) if token else {"status": "not_found"}
    status = result.get("status")

    if status == "not_found":
        # Chatbot'u kullanmadan formu dolduran kişi de panele düşsün
        token = get_or_create_session(None)["session_token"]
        result = complete_form_submission(token, *form_args)
        status = result.get("status")

    if status == "completed":
        # Panelde gösterilecek brif çıktısı kayıt anındaki haliyle saklanır
        save_brief_snapshot(token)

    if status == "slot_unavailable":
        session = get_or_create_session(token)
        slots = get_available_slots(
            expert_id=session.get("selected_expert_id"),
            office_id=session.get("selected_office_id")
        )
        return jsonify({
            "success": False,
            "error": "slot_unavailable",
            "message": Config.MSG_SLOT_UNAVAILABLE,
            "available_slots": slots
        }), 409

    if status == "already_completed":
        return jsonify({
            "success": True,
            "already_completed": True,
            "message": Config.MSG_FORM_COMPLETED_WITH_SLOT
        })

    message = Config.MSG_FORM_COMPLETED_WITH_SLOT if result.get("slot_booked") else Config.MSG_FORM_COMPLETED_NO_SLOT
    return jsonify({
        "success": True,
        "slot_booked": bool(result.get("slot_booked")),
        "message": message
    })


# --- YÖNERGE & YAZILIM KONTROL MODÜL D: STANDART API ADRESLERİ ---

# --- ORTAK KONUŞMA MOTORU (HTML widget ve Wix chatbot kutusu) ---

@main_bp.route("/api/chat/init", methods=["POST"])
def api_chat_init():
    """Sohbeti açar ya da kaldığı yerden yükler (geçmiş + o anki seçenekler)."""
    data = request.get_json() or {}
    return jsonify(chat_init(data))


@main_bp.route("/api/chat", methods=["POST"])
def api_chat():
    """Kullanıcı mesajı ({message}) veya buton seçimi ({action, value, label}) işler."""
    data = request.get_json() or {}
    if not data.get("session_token"):
        return jsonify({"success": False, "error": "Oturum bilgisi eksik."}), 400
    if not str(data.get("message") or "").strip() and not data.get("action"):
        return jsonify({"success": False, "error": "Mesaj boş olamaz."}), 400
    return jsonify(chat_turn(data))


@main_bp.route("/api/sohbet", methods=["POST"])
def api_sohbet():
    """
    POST /api/sohbet:
    Kullanıcı mesajını ve geçmişi alır, Nova'nın Türkçe yanıtını üretir.
    """
    data = request.get_json() or {}
    mesaj = data.get("mesaj") or data.get("message")
    gecmis = data.get("gecmis") or data.get("history") or []

    hizmet_turu = data.get("hizmet_turu") or data.get("service_type")
    toplanan_bilgiler = data.get("toplanan_bilgiler") or data.get("collected_data") or {}

    if not mesaj or not str(mesaj).strip():
        return jsonify({"basari": False, "error": "Mesaj alanı boş olamaz."}), 400

    try:
        if hizmet_turu:
            yanit = ai_service.sorulari_ai_ile_yonet(
                mesaj=mesaj,
                service_type=hizmet_turu,
                toplanan_bilgiler=toplanan_bilgiler,
                gecmis=gecmis
            )
        else:
            yanit = ai_service.yanit_uret(mesaj=mesaj, gecmis=gecmis)

        return jsonify({
            "basari": True,
            "yanit": yanit
        }), 200
    except Exception as e:
        return jsonify({
            "basari": False,
            "error": "Yapay zekâ servisinde bir hata oluştu."
        }), 503

@main_bp.route("/api/leads", methods=["POST", "GET"])
def api_leads():
    """
    POST /api/leads: Müşteri ve talep bilgilerini kaydeder.
    GET /api/leads: Kaydedilmiş müşteri/talep listesini Wix Repeater uyumlu döner.
    """
    if request.method == "POST":
        data = request.get_json() or {}
        isim = data.get("isim") or data.get("name")
        telefon = data.get("telefon") or data.get("phone")
        mesaj = data.get("mesaj") or data.get("message") or ""

        if not isim or not telefon:
            return jsonify({
                "basari": False,
                "error": "İsim ve telefon alanları zorunludur."
            }), 400

        lead_id = lead_ekle(isim=isim, telefon=telefon, mesaj=mesaj)
        return jsonify({
            "basari": True,
            "lead_id": lead_id,
            "mesaj": "Müşteri/talep kaydı başarıyla oluşturuldu."
        }), 201

    else:
        # GET /api/leads: Wix Repeater ve yönetim paneli için kayıtları listele
        raw_leads = tum_leadler()
        
        # Tamamlanmış seans taleplerini de dahil et (eğer varsa)
        completed_sessions = get_all_completed_leads()
        
        formatted_leads = []
        for l in raw_leads:
            formatted_leads.append({
                "_id": str(l["id"]),
                "id": l["id"],
                "isim": l["isim"],
                "telefon": l["telefon"],
                "mesaj": l.get("mesaj", ""),
                "tarih": l.get("tarih", "")
            })
        
        for s in completed_sessions:
            formatted_leads.append({
                "_id": f"sess_{s['id']}",
                "id": s["id"],
                "isim": s.get("client_name", "İsimsiz"),
                "telefon": s.get("client_phone", "-"),
                "mesaj": f"Uzman: {s.get('expert_name') or s.get('office_name')} | Saat: {s.get('selected_slot_text', '-')} | Brif: {json.dumps(s.get('collected_data', {}), ensure_ascii=False)}",
                "tarih": s.get("form_completed_at", "")
            })

        return jsonify({
            "basari": True,
            "leads": formatted_leads,
            "count": len(formatted_leads)
        }), 200
