"""
Ön görüşme brifi: chatbot oturumundan Wix paneli / detay sayfası alanlarını üretir.
routes.py (eski /api/session/* adresleri) ve konuşma motoru (/api/chat) birlikte kullanır.
"""
from app.database import get_all_professionals, get_or_create_session, update_session

# Brifte ve chatbot mesajlarında gösterilen alan adları
FIELD_LABELS = {
    "konum": "Konum",
    "yaklasik_alan": "Yaklaşık Alan (m²)",
    "kullanim_amaci": "Kullanım Amacı",
    "mekan_turu": "Mekân Türü",
    "acik_alan_turu": "Açık Alan Türü",
    "oda_bolum_sayisi": "Oda / Bölüm Sayısı",
    "mevcut_durum": "Mevcut Durum",
    "butce_araligi": "Bütçe Aralığı",
    "hedef_zaman": "Hedef Zaman",
    "ozel_istekler": "Özel İstekler / Notlar",
    "proje_turu": "Proje Türü",
    "kat_sayisi": "Kat Sayısı",
    "mevcut_kat_sayisi": "Mevcut Kat Sayısı",
    "mekansal_ihtiyaclar": "Mekânsal İhtiyaçlar",
    "mimari_tarz": "Mimari Tarz",
    "malzeme_renk": "Malzeme ve Renkler",
    "korunacak_ozellikler": "Korunacak Özellikler",
    "ek_talepler": "Ek Talepler",
    "gorsel_ve_ek": "Görseller ve Ek Talepler",
    "degisecek_bolumler": "Değişecek Bölümler",
    "mevcut_zorluklar": "Mevcut Zorluklar",
    "kullanici_sayisi": "Kullanıcı Sayısı",
    "oncelikler": "Öncelikler",
    "tarz": "Tarz",
    "korunacak_mobilyalar": "Korunacak Mobilyalar",
    "aydinlatma_depolama": "Aydınlatma ve Depolama",
    "egim_kot": "Eğim / Kot Farkı",
    "korunacak_bitkiler": "Korunacak Bitkiler",
    "peyzaj_tarzi": "Peyzaj Tarzı",
    "zemin_ve_bitki": "Zemin ve Bitki Tercihleri",
    "yapisal_talepler": "Yapısal Talepler",
    "aydinlatma_mahremiyet": "Aydınlatma ve Mahremiyet",
    "bakim_zamani": "Bakım Zamanı",
}
# Brifte önce (bu sırayla) gösterilen alanlar
PRIMARY_FIELDS = [
    "konum", "yaklasik_alan", "kullanim_amaci", "mekan_turu", "acik_alan_turu",
    "oda_bolum_sayisi", "mevcut_durum", "butce_araligi", "hedef_zaman", "ozel_istekler"
]


def field_label(field):
    return FIELD_LABELS.get(field, field.replace("_", " ").title())

def build_wix_summary_dict(session):
    if not session:
        return None

    token = session.get("session_token")
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
    brief_lines = [
        f"Uzman / Ofis: {expert_name}",
        f"Hizmet Alanı: {hizmet_alan}",
        f"Randevu Saati Tercihi: {randevu_tarihi}",
        "------------------------------------"
    ]
    field_labels = {k: FIELD_LABELS[k] for k in PRIMARY_FIELDS}
    for k, label in field_labels.items():
        if k in collected and collected[k]:
            brief_lines.append(f"• {label}: {collected[k]}")

    for k, v in collected.items():
        if k not in field_labels and v:
            brief_lines.append(f"• {field_label(k)}: {v}")

    uploaded_images = session.get("uploaded_images") or []
    if uploaded_images:
        brief_lines.append(f"• Referans Görseller: {len(uploaded_images)} Adet Yüklendi")

    skipped_fields = (session.get("flow_state") or {}).get("skipped_fields", [])
    if skipped_fields:
        skipped_labels = [field_label(f) for f in skipped_fields]
        brief_lines.append(f"• Atlanan Sorular: {', '.join(skipped_labels)}")

    proje_brifi = "\n".join(brief_lines)

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

    return {
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
    }


def save_brief_snapshot(token):
    """Chatbot'un ürettiği brif çıktısını (panelde gösterilen hali) brief_summary olarak saklar."""
    session = get_or_create_session(token)
    summary = build_wix_summary_dict(session)
    update_session(token, {"brief_summary": {
        "hizmetAlan": summary["hizmetAlan"],
        "seilenUzman": summary["seilenUzman"],
        "randevuTarihi": summary["randevuTarihi"],
        "projeBrifi": summary["projeBrifi"],
        "gallery_items": summary["gallery_items"],
        "collected_data": summary["collected_data"]
    }})
