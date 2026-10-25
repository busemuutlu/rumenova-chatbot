import sqlite3
import json
import uuid
import os
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """PDF belgesine birebir uygun veritabanı tablolarını ve başlangıç verilerini kurar."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Ofisler Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        office_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        service_areas TEXT NOT NULL, -- JSON array: ["mimari", "ic_mimari"]
        profile_url TEXT,
        is_active INTEGER DEFAULT 1
    )
    """)

    # 2. Uzmanlar ve Ofis Ekip Üyeleri Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS experts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expert_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        title TEXT NOT NULL, -- 'Mimar', 'İç Mimar', 'Peyzaj Mimarı'
        office_role TEXT, -- Ofis içi rol
        location TEXT NOT NULL,
        service_areas TEXT NOT NULL, -- JSON array: ["mimari"]
        specialties TEXT, -- Profil uzmanlıkları
        is_independent INTEGER DEFAULT 1, -- 1: Bireysel Uzman, 0: Ofis Ekip Üyesi
        office_id INTEGER,
        is_selectable_individually INTEGER DEFAULT 1,
        profile_url TEXT,
        avatar_url TEXT,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (office_id) REFERENCES offices (id)
    )
    """)

    # 3. Uygun Randevu Saatleri Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS available_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expert_id INTEGER,
        office_id INTEGER,
        slot_date TEXT NOT NULL, -- YYYY-MM-DD
        slot_time TEXT NOT NULL, -- HH:MM (örn: 10:00, 11:30, 14:00, 15:30)
        timezone TEXT DEFAULT 'Europe/Istanbul',
        is_booked INTEGER DEFAULT 0,
        FOREIGN KEY (expert_id) REFERENCES experts (id),
        FOREIGN KEY (office_id) REFERENCES offices (id)
    )
    """)

    # 4. Görüşme Oturumları (Sessions & Briefs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_token TEXT UNIQUE NOT NULL,
        service_type TEXT, -- 'mimari', 'ic_mimari', 'peyzaj'
        selected_expert_id INTEGER,
        selected_office_id INTEGER,
        selected_team_member_id INTEGER,
        current_step_index INTEGER DEFAULT 0,
        collected_data TEXT, -- JSON formatında tüm toplanan cevaplar
        uploaded_images TEXT, -- JSON array of file urls
        selected_slot_id INTEGER,
        selected_slot_text TEXT,
        extra_note TEXT,
        is_brief_approved INTEGER DEFAULT 0,
        brief_summary TEXT, -- JSON özet
        chat_messages TEXT, -- JSON konuşma geçmişi
        flow_state TEXT, -- JSON: {"skipped_fields": [...], "estimate_asked": {alan: sayı}}
        -- İletişim Formu Tamamlama Bilgileri
        is_form_completed INTEGER DEFAULT 0,
        client_name TEXT,
        client_email TEXT,
        client_phone TEXT,
        client_form_note TEXT,
        form_completed_at TIMESTAMP,
        status TEXT DEFAULT 'devam_ediyor', -- 'devam_ediyor', 'brif_onaylandi', 'form_tamamlandi', 'uzman_onayladi', 'reddedildi'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (selected_expert_id) REFERENCES experts (id),
        FOREIGN KEY (selected_office_id) REFERENCES offices (id)
    )
    """)

    # Eski veritabanları için migrasyon: flow_state sütunu yoksa ekle
    cursor.execute("PRAGMA table_info(chat_sessions)")
    existing_cols = [r["name"] for r in cursor.fetchall()]
    if "flow_state" not in existing_cols:
        cursor.execute("ALTER TABLE chat_sessions ADD COLUMN flow_state TEXT")
    # Wix ön görüşme formundaki ad / soyad ayrı tutulur (yönetim paneli alanları)
    if "client_ad" not in existing_cols:
        cursor.execute("ALTER TABLE chat_sessions ADD COLUMN client_ad TEXT")
    if "client_soyad" not in existing_cols:
        cursor.execute("ALTER TABLE chat_sessions ADD COLUMN client_soyad TEXT")

    # 5. Leads (Temel Müşteri / Talep Tablosu - Yönerge & Yazılım Kontrol)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isim TEXT NOT NULL,
        telefon TEXT NOT NULL,
        mesaj TEXT,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # --- BAŞLANGIÇ VERİLERİ (PDF Sayfa 32-34) ---
    cursor.execute("SELECT COUNT(*) FROM offices")
    if cursor.fetchone()[0] == 0:
        # Ofisler
        offices_data = [
            ("forma_mimarlik", "Forma Mimarlık", "İzmir", json.dumps(["mimari", "ic_mimari"]), "/ofisler/forma-mimarlik"),
            ("kuzey_studyo", "Kuzey Stüdyo", "Ankara", json.dumps(["mimari"]), "/ofisler/kuzey-studyo")
        ]
        cursor.executemany("""
            INSERT INTO offices (office_code, name, location, service_areas, profile_url)
            VALUES (?, ?, ?, ?, ?)
        """, offices_data)

        # Bireysel Uzmanlar (PDF)
        individual_experts = [
            ("aylin_aydeniz", "Aylin Aydeniz", "Mimar", "", "İstanbul", json.dumps(["mimari"]), "Konut, yenileme, restorasyon", 1, None, 1, "/uzmanlar/aylin-aydeniz", "/static/images/aylin_aydeniz.png"),
            ("deniz_arslan", "Deniz Arslan", "Mimar", "", "Ankara", json.dumps(["mimari"]), "Konut, villa, küçük ölçekli ticari yapılar", 1, None, 1, "/uzmanlar/deniz-arslan", "/static/images/deniz_arslan.png"),
            ("idil_ergin", "İdil Ergin", "İç Mimar", "", "İstanbul", json.dumps(["ic_mimari"]), "Ofis, mağaza, iç mekân yenileme", 1, None, 1, "/uzmanlar/idil-ergin", "/static/images/idil_ergin.png"),
            ("mert_kaya", "Mert Kaya", "Peyzaj Mimarı", "", "Antalya", json.dumps(["peyzaj"]), "Konut bahçeleri, teras, açık alan düzenleme", 1, None, 1, "/uzmanlar/mert-kaya", "/static/images/mert_kaya.png")
        ]
        cursor.executemany("""
            INSERT INTO experts (expert_code, name, title, office_role, location, service_areas, specialties, is_independent, office_id, is_selectable_individually, profile_url, avatar_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, individual_experts)

        # Ofis Ekip Üyeleri (PDF)
        # Forma Mimarlık (id: 1), Kuzey Stüdyo (id: 2)
        team_members = [
            ("yalin_tanyel", "Yalın Tanyel", "Mimar", "Mimar", "İzmir", json.dumps(["mimari"]), "Mimari Tasarım", 0, 1, 1, "/uzmanlar/yalin-tanyel", "/static/images/yalin_tanyel.png"),
            ("lara_soyer", "Lara Soyer", "Mimar", "Mimar", "İzmir", json.dumps(["mimari"]), "Mimari Tasarım", 0, 1, 1, "/uzmanlar/lara-soyer", "/static/images/lara_soyer.png"),
            ("nil_deren", "Nil Deren", "İç Mimar", "İç Mimar", "İzmir", json.dumps(["ic_mimari"]), "İç Mimarlık", 0, 1, 1, "/uzmanlar/nil-deren", "/static/images/nil_deren.png"),
            ("ozan_ilgaz", "Ozan Ilgaz", "Mimar", "Mimar", "Ankara", json.dumps(["mimari"]), "Mimari Tasarım", 0, 2, 1, "/uzmanlar/ozan-ilgaz", "/static/images/ozan_ilgaz.png"),
            ("duru_aksel", "Duru Aksel", "Mimar", "Mimar", "Ankara", json.dumps(["mimari"]), "Mimari Tasarım", 0, 2, 1, "/uzmanlar/duru-aksel", "/static/images/duru_aksel.png")
        ]
        cursor.executemany("""
            INSERT INTO experts (expert_code, name, title, office_role, location, service_areas, specialties, is_independent, office_id, is_selectable_individually, profile_url, avatar_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, team_members)

        # Örnek Uygun Saatler (Her uzman ve ofis için sistemde tanımlı gerçek saatler)
        sample_slots = []
        # Tüm uzmanlar için (id 1'den 9'a)
        for exp_id in range(1, 10):
            sample_slots.extend([
                (exp_id, None, "2026-10-06", "10:00"),
                (exp_id, None, "2026-10-06", "11:30"),
                (exp_id, None, "2026-10-07", "14:00"),
                (exp_id, None, "2026-10-07", "15:30"),
                (exp_id, None, "2026-10-08", "11:00"),
                (exp_id, None, "2026-10-08", "16:00")
            ])
        # Ofisler için de
        sample_slots.extend([
            (None, 1, "2026-10-06", "14:00"),
            (None, 1, "2026-10-07", "16:30"),
            (None, 2, "2026-10-06", "11:00"),
            (None, 2, "2026-10-08", "15:00")
        ])
        cursor.executemany("""
            INSERT INTO available_slots (expert_id, office_id, slot_date, slot_time)
            VALUES (?, ?, ?, ?)
        """, sample_slots)

    # Sonradan eklenen uzmanlar: mevcut veritabanlarında da (yoksa) eklenir
    later_experts = [
        ("meltem_turan", "Meltem Turan", "Peyzaj Mimarı", "", "Ankara", json.dumps(["peyzaj"]), "Konut bahçeleri, teras, açık alan düzenleme", 1, None, 1, "/uzmanlar/meltem-turan", "/static/images/meltem_turan.png")
    ]
    for exp in later_experts:
        cursor.execute("SELECT id FROM experts WHERE expert_code = ?", (exp[0],))
        if cursor.fetchone():
            continue
        cursor.execute("""
            INSERT INTO experts (expert_code, name, title, office_role, location, service_areas, specialties, is_independent, office_id, is_selectable_individually, profile_url, avatar_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, exp)
        new_id = cursor.lastrowid
        cursor.executemany("""
            INSERT INTO available_slots (expert_id, office_id, slot_date, slot_time)
            VALUES (?, ?, ?, ?)
        """, [(new_id, None, d, t) for d, t in [
            ("2026-10-06", "10:00"), ("2026-10-06", "11:30"),
            ("2026-10-07", "14:00"), ("2026-10-07", "15:30"),
            ("2026-10-08", "11:00"), ("2026-10-08", "16:00")
        ]])

    conn.commit()
    conn.close()

# --- VERİ ERİŞİM FONKSİYONLARI ---

def get_all_professionals():
    """Tüm bağımsız uzmanları ve ofisleri getirir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experts WHERE is_independent = 1 AND is_active = 1")
    ind_experts = [dict(r) for r in cursor.fetchall()]
    for e in ind_experts:
        e["service_areas"] = json.loads(e["service_areas"])

    cursor.execute("SELECT * FROM offices WHERE is_active = 1")
    offices = [dict(r) for r in cursor.fetchall()]
    for o in offices:
        o["service_areas"] = json.loads(o["service_areas"])
        cursor.execute("SELECT * FROM experts WHERE office_id = ? AND is_active = 1", (o["id"],))
        team = [dict(t) for t in cursor.fetchall()]
        for t in team:
            t["service_areas"] = json.loads(t["service_areas"])
        o["team_members"] = team

    conn.close()
    return {"experts": ind_experts, "offices": offices}

def get_professionals_by_service(service_type):
    """Belirli bir hizmet alanına göre uzman ve ofisleri filtreler."""
    all_data = get_all_professionals()
    filtered_experts = [e for e in all_data["experts"] if service_type in e["service_areas"]]
    filtered_offices = [o for o in all_data["offices"] if service_type in o["service_areas"]]
    return {"experts": filtered_experts, "offices": filtered_offices}

def get_expert_or_office_by_code(code):
    """Uzman koduna veya ofis koduna göre bulur."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experts WHERE expert_code = ?", (code,))
    r = cursor.fetchone()
    if r:
        exp = dict(r)
        exp["service_areas"] = json.loads(exp["service_areas"])
        conn.close()
        return {"type": "expert", "data": exp}

    cursor.execute("SELECT * FROM offices WHERE office_code = ?", (code,))
    r = cursor.fetchone()
    if r:
        off = dict(r)
        off["service_areas"] = json.loads(off["service_areas"])
        cursor.execute("SELECT * FROM experts WHERE office_id = ?", (off["id"],))
        team = [dict(t) for t in cursor.fetchall()]
        for t in team:
            t["service_areas"] = json.loads(t["service_areas"])
        off["team_members"] = team
        conn.close()
        return {"type": "office", "data": off}

    conn.close()
    return None

def get_available_slots(expert_id=None, office_id=None):
    """Seçilen uzmanın veya ofisin gerçek rezerve edilmemiş uygun saatlerini getirir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if expert_id:
        cursor.execute("""
            SELECT * FROM available_slots 
            WHERE expert_id = ? AND is_booked = 0 
            ORDER BY slot_date ASC, slot_time ASC
        """, (expert_id,))
    elif office_id:
        cursor.execute("""
            SELECT * FROM available_slots 
            WHERE office_id = ? AND is_booked = 0 
            ORDER BY slot_date ASC, slot_time ASC
        """, (office_id,))
    else:
        conn.close()
        return []

    slots = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return slots

# --- OTURUM & GÖRÜŞME İŞLEMLERİ ---

def get_or_create_session(session_token=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if session_token:
        cursor.execute("SELECT * FROM chat_sessions WHERE session_token = ?", (session_token,))
        row = cursor.fetchone()
        if row:
            sess = dict(row)
            sess["collected_data"] = json.loads(sess["collected_data"]) if sess["collected_data"] else {}
            sess["uploaded_images"] = json.loads(sess["uploaded_images"]) if sess["uploaded_images"] else []
            sess["chat_messages"] = json.loads(sess["chat_messages"]) if sess["chat_messages"] else []
            sess["brief_summary"] = json.loads(sess["brief_summary"]) if sess["brief_summary"] else {}
            sess["flow_state"] = _parse_flow_state(sess.get("flow_state"))
            conn.close()
            return sess

    # Yeni Oturum Aç
    new_token = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO chat_sessions (session_token, collected_data, uploaded_images, chat_messages, status)
        VALUES (?, '{}', '[]', '[]', 'devam_ediyor')
    """, (new_token,))
    conn.commit()
    cursor.execute("SELECT * FROM chat_sessions WHERE session_token = ?", (new_token,))
    sess = dict(cursor.fetchone())
    sess["collected_data"] = {}
    sess["uploaded_images"] = []
    sess["chat_messages"] = []
    sess["brief_summary"] = {}
    sess["flow_state"] = _parse_flow_state(None)
    conn.close()
    return sess

def get_latest_active_session():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_token FROM chat_sessions 
        WHERE status IN ('brif_onaylandi', 'devam_ediyor')
        ORDER BY updated_at DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    if row:
        return get_or_create_session(row["session_token"])
    return None

def update_session(session_token, updates):

    conn = get_db_connection()
    cursor = conn.cursor()

    set_clauses = []
    params = []
    for k, v in updates.items():
        if k in ["collected_data", "uploaded_images", "chat_messages", "brief_summary", "flow_state"]:
            set_clauses.append(f"{k} = ?")
            params.append(json.dumps(v, ensure_ascii=False))
        else:
            set_clauses.append(f"{k} = ?")
            params.append(v)

    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    query = f"UPDATE chat_sessions SET {', '.join(set_clauses)} WHERE session_token = ?"
    params.append(session_token)

    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return True

def _parse_flow_state(raw):
    """flow_state JSON'unu güvenli şekilde okur ve eksik anahtarları tamamlar."""
    state = {}
    if raw:
        try:
            state = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (ValueError, TypeError):
            state = {}
    state.setdefault("skipped_fields", [])
    state.setdefault("estimate_asked", {})
    return state

def complete_form_submission(session_token, client_name, client_email, client_phone, client_note="",
                             client_ad=None, client_soyad=None):
    """
    Wix veya harici iletişim sayfasından gelen form verisini oturumla birleştirir.

    Seçilen saat form gönderiminde YENİDEN kontrol edilir ve tek bir SQL işlemiyle
    (is_booked = 0 koşuluyla) rezerve edilir. Dönen sözlük:
      {"status": "completed", "slot_booked": bool}  -> form kaydedildi
      {"status": "already_completed"}              -> aynı oturum daha önce tamamlanmış
      {"status": "slot_unavailable"}               -> saat dolmuş; form kaydedilmedi
      {"status": "not_found"}                      -> oturum yok
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Yarış durumlarına karşı yazma kilidi al
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT selected_slot_id, selected_expert_id, selected_office_id, is_form_completed "
            "FROM chat_sessions WHERE session_token = ?", (session_token,)
        )
        sess = cursor.fetchone()
        if not sess:
            conn.rollback()
            return {"status": "not_found"}

        if sess["is_form_completed"]:
            conn.rollback()
            return {"status": "already_completed"}

        slot_booked = False
        slot_id = sess["selected_slot_id"]
        if slot_id:
            # Saat hâlâ boş mu ve seçilen uzman/ofise mi ait? Aynı sorguda rezerve et.
            cursor.execute("""
                UPDATE available_slots SET is_booked = 1
                WHERE id = ? AND is_booked = 0
                  AND ((expert_id IS NOT NULL AND expert_id = ?)
                    OR (office_id IS NOT NULL AND office_id = ?))
            """, (slot_id, sess["selected_expert_id"], sess["selected_office_id"]))
            if cursor.rowcount != 1:
                # Saat dolmuş: seçimi temizle, kullanıcı yeni saat seçsin
                cursor.execute("""
                    UPDATE chat_sessions
                    SET selected_slot_id = NULL, selected_slot_text = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_token = ?
                """, (session_token,))
                conn.commit()
                return {"status": "slot_unavailable"}
            slot_booked = True

        cursor.execute("""
            UPDATE chat_sessions
            SET client_name = ?,
                client_ad = ?,
                client_soyad = ?,
                client_email = ?,
                client_phone = ?,
                client_form_note = ?,
                is_form_completed = 1,
                status = 'form_tamamlandi',
                form_completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE session_token = ?
        """, (client_name, client_ad, client_soyad, client_email, client_phone, client_note, session_token))

        conn.commit()
        return {"status": "completed", "slot_booked": slot_booked}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_all_completed_leads(expert_id=None, office_id=None, lead_id=None):
    """Panel için tamamlanmış talepleri getirir (lead_id verilirse yalnızca o kayıt)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT s.*, 
               e.name as expert_name, e.title as expert_title,
               o.name as office_name
        FROM chat_sessions s
        LEFT JOIN experts e ON s.selected_expert_id = e.id
        LEFT JOIN offices o ON s.selected_office_id = o.id
        WHERE s.is_form_completed = 1
    """
    params = []
    if lead_id is not None:
        query += " AND s.id = ?"
        params.append(lead_id)
    if expert_id:
        query += " AND s.selected_expert_id = ?"
        params.append(expert_id)
    elif office_id:
        query += " AND s.selected_office_id = ?"
        params.append(office_id)

    query += " ORDER BY s.form_completed_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    leads = []
    for r in rows:
        d = dict(r)
        d["collected_data"] = json.loads(d["collected_data"]) if d["collected_data"] else {}
        d["uploaded_images"] = json.loads(d["uploaded_images"]) if d["uploaded_images"] else []
        d["brief_summary"] = json.loads(d["brief_summary"]) if d["brief_summary"] else {}
        d["flow_state"] = _parse_flow_state(d.get("flow_state"))
        leads.append(d)
    conn.close()
    return leads

def get_db():
    """Yönerge uyumlu veritabanı bağlantısı fonksiyonu."""
    return get_db_connection()

def lead_ekle(isim, telefon, mesaj=""):
    """
    Yönerge & Yazılım Kontrol Modül B:
    SQLite veritabanına yeni müşteri/ön görüşme kaydı ekler.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leads (isim, telefon, mesaj)
        VALUES (?, ?, ?)
    """, (isim, telefon, mesaj))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def tum_leadler():
    """
    Yönerge & Yazılım Kontrol Modül B:
    Kayıtları en yeniden eskiye doğru getirir.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY tarih DESC")
    rows = cursor.fetchall()
    leads = [dict(r) for r in rows]
    conn.close()
    return leads

