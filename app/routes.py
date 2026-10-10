import os
import uuid
import json
from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename
from app.services.ai_service import AIService, QUESTION_POOLS, ai_service
from app.database import (
    get_all_professionals, get_professionals_by_service,
    get_expert_or_office_by_code, get_available_slots,
    get_or_create_session, update_session, complete_form_submission,
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
        next_q = AIService.get_next_question(session["service_type"], session.get("collected_data", {}))

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

    # Kullanıcı mesajını ekle
    chat_msgs.append({"role": "user", "content": message_text})

    is_skipping = message_text.lower() in ["geç", "gec", "atla", "devam", "bilmiyorum geç", "pas"]
    asked_for_estimate = data.get("asked_for_estimate", False)

    # 1. Anlamsız / Saçma Cevap Kontrolü (Örn: 'asdasd', '123123', '????')
    if not is_skipping and AIService.is_gibberish_or_irrelevant(message_text):
        bot_reply = "Tam olarak ne demek istediğinizi söyler misiniz?"
        chat_msgs.append({"role": "assistant", "content": bot_reply})
        update_session(token, {"chat_messages": chat_msgs})
        return jsonify({
            "success": True,
            "reply": bot_reply,
            "invalid_input": True,
            "next_question": None,
            "collected_data": collected,
            "is_complete": False
        })

    # 2. Konum Sorusu İse 81 İl Doğrulaması
    if current_field == "konum" and not is_skipping:
        prov, dist = AIService.find_turkey_province_and_district(message_text)
        if not prov:
            bot_reply = "Projenizin hangi ilde bulunduğunu öğrenebilir miyim? (Örn: İstanbul, Ankara, İzmir, Muğla vb. 81 ilimizden biri)"
            chat_msgs.append({"role": "assistant", "content": bot_reply})
            update_session(token, {"chat_messages": chat_msgs})
            return jsonify({
                "success": True,
                "reply": bot_reply,
                "retry_location": True,
                "next_question": None,
                "collected_data": collected,
                "is_complete": False
            })
        else:
            if dist:
                collected["konum"] = f"{prov}, {dist}"
            else:
                collected["konum"] = f"{prov}"

    # 3. Olumsuz / Belirsiz Cevap Kontrolü ('bilmiyorum', 'hayır', 'yok' vb.)
    is_uncertain = AIService.check_if_uncertain_answer(message_text)
    if is_uncertain and not is_skipping:
        bot_reply = "Anladım, yaklaşık veya tahmini olarak belirtiniz."
        chat_msgs.append({"role": "assistant", "content": bot_reply})
        update_session(token, {"chat_messages": chat_msgs})
        return jsonify({
            "success": True,
            "reply": bot_reply,
            "ask_estimate": True,
            "next_question": None, # aynı soruda kal
            "collected_data": collected,
            "is_complete": False
        })

    # Son sorulan alanın cevabı (konum harici, konum yukarıda kaydedildi)
    if current_field and current_field != "konum":
        collected[current_field] = message_text

    # Çoklu bilgi çıkarma (Madde 6)
    extra_extracted = AIService.extract_info_from_message(message_text, collected)
    for k, v in extra_extracted.items():
        if k not in collected or not collected[k]:
            collected[k] = v

    # Sonraki tek soru (Cevaplanmış sorular atlanır!)
    next_q = AIService.get_next_question(service_type, collected)

    updates = {
        "collected_data": collected,
        "chat_messages": chat_msgs
    }

    if next_q:
        bot_reply = next_q["question"]
        chat_msgs.append({"role": "assistant", "content": bot_reply})
        update_session(token, updates)

        return jsonify({
            "success": True,
            "reply": bot_reply,
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

    if len(uploaded) >= 5:
        return jsonify({"error": "En fazla 5 görsel yükleyebilirsiniz."}), 400

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
    chat_msgs.append({"role": "assistant", "content": "Ön görüşme özetinizi onayladınız. Bilgilerinizin seçtiğiniz mimara/ofise iletilebilmesi için iletişim formunu tamamlayın. Seçtiğiniz görüşme saati, mimarın/ofisin teyidinden sonra kesinleşecektir."})

    update_session(token, {
        "is_brief_approved": 1,
        "extra_note": extra_note,
        "status": "brif_onaylandi",
        "chat_messages": chat_msgs
    })

    wix_contact_url = f"https://busemutlubg.wixstudio.com/rumenova/ongorusme?session_token={token}"

    return jsonify({
        "success": True,
        "message": "Ön görüşme özetinizi onayladınız. Bilgilerinizin seçtiğiniz mimara/ofise iletilebilmesi için iletişim formunu tamamlayın.",
        "wix_contact_url": wix_contact_url,
        "session_token": token
    })


@main_bp.route("/api/session/wix-summary", methods=["GET"])
def get_session_wix_summary():
    """
    Wix Ön Görüşme CMS entegrasyonu için oturum verilerini çeker.
    Wix CMS kolon adlarıyla birebir uyumlu JSON üretir.
    """
    token = request.args.get("session_token")
    if not token:
        return jsonify({"success": False, "error": "session_token parametresi gerekli."}), 400

    session = get_or_create_session(token)
    if not session:
        return jsonify({"success": False, "error": "Oturum bulunamadı."}), 404

    # Seçilen Uzman veya Ofis Adı
    all_profs = get_all_professionals()
    expert_name = "Belirtilmedi"
    if session.get("selected_expert_id"):
        for e in all_profs.get("experts", []):
            if e["id"] == session["selected_expert_id"]:
                expert_name = e["name"]
                break
        if expert_name == "Belirtilmedi":
            for o in all_profs.get("offices", []):
                for tm in o.get("team_members", []):
                    if tm["id"] == session["selected_expert_id"]:
                        expert_name = f"{tm['name']} ({o['name']})"
                        break
    elif session.get("selected_office_id"):
        for o in all_profs.get("offices", []):
            if o["id"] == session["selected_office_id"]:
                expert_name = o["name"]
                break

    # Hizmet Alanı Adı
    service_map = {
        "mimari": "Mimari Tasarım",
        "ic_mimari": "İç Mimarlık",
        "peyzaj": "Peyzaj Tasarımı"
    }
    raw_service = session.get("service_type") or ""
    hizmet_alan = service_map.get(raw_service, raw_service or "Genel Mimari Ön Görüşme")

    # Randevu Tarihi ve Saati
    randevu_tarihi = session.get("selected_slot_text") or "Randevu Seçilmedi (Esnek Saat)"

    # Proje Brifini metin olarak derle
    collected = session.get("collected_data") or {}
    brief_lines = []
    field_labels = {
        "konum": "Konum",
        "yaklasik_alan": "Yaklaşık Alan (m²)",
        "kullanim_amaci": "Kullanım Amacı",
        "mekan_turu": "Mekân Türü",
        "acik_alan_turu": "Açık Alan Türü",
        "oda_bolum_sayisi": "Oda / Bölüm Sayısı",
        "mevcut_durum": "Mevcut Durum",
        "butce_araligi": "Bütçe Aralığı",
        "hedef_zaman": "Hedef Zaman",
        "ozel_istekler": "Özel İstekler / Notlar"
    }
    for k, label in field_labels.items():
        if k in collected and collected[k]:
            brief_lines.append(f"• {label}: {collected[k]}")

    for k, v in collected.items():
        if k not in field_labels and v:
            clean_k = k.replace("_", " ").title()
            brief_lines.append(f"• {clean_k}: {v}")

    uploaded_images = session.get("uploaded_images") or []
    if uploaded_images:
        brief_lines.append(f"• Referans Görseller: {len(uploaded_images)} adet yüklendi")

    proje_brifi = "\n".join(brief_lines) if brief_lines else "Brif detayları görüşmede aktarılacak."

    # Wix Pro Gallery (#gallery1) uyumlu görsel listesi
    base_url = "https://rumenova-chatbot.onrender.com"
    gallery_items = []
    gorsel_linkleri = []
    for img in uploaded_images:
        raw_url = img.get("url", "")
        if raw_url.startswith("http"):
            full_url = raw_url
        else:
            full_url = f"{base_url}{raw_url}"
        gallery_items.append({
            "type": "image",
            "src": full_url,
            "title": img.get("name", "Referans Görsel"),
            "description": "Nova Chatbot Üzerinden Yüklenen Proje Görseli"
        })
        gorsel_linkleri.append(full_url)

    return jsonify({
        "success": True,
        "session_token": token,
        "hizmetAlan": hizmet_alan,
        "seilenUzman": expert_name,
        "randevuTarihi": randevu_tarihi,
        "projeBrifi": proje_brifi,
        "durum": "Randevu Bekliyor",
        "gallery_items": gallery_items,
        "gorseller": gorsel_linkleri,
        "collected_data": collected
    })



@main_bp.route("/api/wix/complete-form", methods=["POST"])
def wix_complete_form():
    data = request.get_json() or {}
    token = data.get("session_token")
    client_name = data.get("name")
    client_email = data.get("email")
    client_phone = data.get("phone")
    client_note = data.get("note", "")

    if not token or not client_name or not client_phone:
        return jsonify({"error": "Eksik form bilgileri."}), 400

    complete_form_submission(token, client_name, client_email, client_phone, client_note)

    return jsonify({
        "success": True,
        "message": "Bizi tercih ettiğiniz için teşekkür ederiz. Ön görüşme bilgileriniz seçtiğiniz mimara/ofise iletildi. Görüşme saatiniz, uzman tarafından teyit edildikten sonra kesinleşecektir."
    })


# --- YÖNERGE & YAZILIM KONTROL MODÜL D: STANDART API ADRESLERİ ---

@main_bp.route("/api/sohbet", methods=["POST"])
def api_sohbet():
    """
    POST /api/sohbet:
    Kullanıcı mesajını ve geçmişi alır, Nova'nın Türkçe yanıtını üretir.
    """
    data = request.get_json() or {}
    mesaj = data.get("mesaj") or data.get("message")
    gecmis = data.get("gecmis") or data.get("history") or []

    if not mesaj or not str(mesaj).strip():
        return jsonify({"basari": False, "error": "Mesaj alanı boş olamaz."}), 400

    try:
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
