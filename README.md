# RUMENOVA - SmartLead AI Mimari Ön Görüşme Sistemi

Rumenova, **SmartLead AI** yönergesi ve **YAZILIMA KOMUTLAR.pdf** şartnamesine %100 uyumlu olarak geliştirilmiş, yapay zekâ destekli (Nova) dijital mimari ön görüşme ve müşteri adayı (lead) toplama sistemidir.

---

## 🏛️ Mimari Yapı (Separation of Concerns — SoC)

Proje, yönergede belirtilen katmanlı kurumsal mimariye tam sadık kalınarak geliştirilmiştir:

```text
chat/
├── run.py                 ← Sunucuyu başlatan giriş noktası (gunicorn run:app / python run.py)
├── config.py              ← Tüm ayarlar ve .env yapılandırması (BUSINESS_CONTEXT, SECRET_KEY, GROQ_API_KEY)
├── requirements.txt       ← Bağımlılık listesi (Flask, Groq, Gunicorn vb.)
├── .env                   ← Gizli anahtarlar (GitHub'a YÜKLENMEZ)
├── .gitignore             ← Git hariç tutma kuralları
├── wix_integration/       ← Wix Velo frontend & backend kodları
└── app/
    ├── __init__.py        ← create_app() fabrika fonksiyonu, CORS ve veritabanı başlatma
    ├── database.py        ← SQLite işlemleri (SADECE burada - leads, sessions, slots)
    ├── routes.py          ← HTTP API rotaları ve sayfa yönlendirmeleri
    ├── templates/
    │   ├── index.html     ← Karşılama ve chatbot sayfası (Z-Pattern & Glassmorphism)
    │   └── dashboard.html ← Yönetim paneli (F-Pattern & Lead listesi)
    ├── static/            ← CSS, JS ve yerel uzman fotoğrafları
    └── services/
        ├── __init__.py
        └── ai_service.py  ← Yapay zekâ çağrıları ve soru motoru (SADECE burada)
```

---

## 🚀 API Uç Noktaları

| Metot | Uç Nokta | Görevi | Durum Kodu |
| :--- | :--- | :--- | :---: |
| **GET** | `/health` | Sunucu canlılık ve sağlık kontrolü | `200` |
| **POST** | `/api/sohbet` | Nova ile mesajlaşma (Groq LLM / Akıllı Motor) | `200` / `503` |
| **POST** | `/api/leads` | Yeni müşteri adayı/talep kaydı oluşturma | `201` / `400` |
| **GET** | `/api/leads` | Kayıtlı talepleri listeleme (Wix Repeater `_id` uyumlu) | `200` |
| **GET** | `/` | B2C Karşılama & Nova Chatbot Arayüzü | `200` |
| **GET** | `/dashboard` | B2B Mimar / Yönetici Paneli | `200` |

---

## 🛠️ Kurulum ve Yerel Çalıştırma

1. **Sanal Ortamı Kurun ve Paketleri Yükleyin:**
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Paketleri yükleyin:
   pip install -r requirements.txt
   ```

2. **Uygulamayı Başlatın:**
   ```bash
   python run.py
   ```

3. **Erişim Adresleri:**
   - **Canlı Chatbot:** `http://127.0.0.1:5000/`
   - **Yönetici Paneli:** `http://127.0.0.1:5000/dashboard`
   - **Sağlık Kontrolü:** `http://127.0.0.1:5000/health`

---

## 🌐 Render Canlı Yayınlama (Modül H)

1. GitHub'da public bir depo oluşturup kodu push edin (`.env` hariç).
2. [Render.com](https://render.com) üzerinde **New Web Service** seçeneğini tıklayın.
3. Ayarlar:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn run:app`
4. Environment Variables kısmına `GROQ_API_KEY`, `SECRET_KEY`, `DEBUG=False` ekleyin.
5. Render canlı URL'inizi Wix kodundaki backend adresine bağlayın.

