# RUMENOVA NOVA CHATBOT & WIX ENTEGRASYON REHBERİ
(YAZILIMA KOMUTLAR.pdf Dökümanına Birebir Uygun)

Bu rehber, **Nova Chatbot** sistemini Wix Studio web sitenize bağlamak için gereken 3 adımı anlatır:

---

## 🚀 Adım 1: Chatbot'u Wix'in Tüm Sayfalarına Ekleme (Floating Widget)

Sitenizin her sayfasının sağ alt köşesinde Rumenova marka renklerinde (`#5A2027`) Nova butonu yer alır.

1. **Wix Yönetim Paneline** girin.
2. **Ayarlar (Settings)** -> **Özel Kod (Custom Code)** bölümüne gidin.
3. **`+ Kod Ekle`** butonuna tıklayın:
   ```html
   <script src="http://127.0.0.1:5000/static/widget.js"></script>
   ```
   *(Canlıya aldığınızda `http://127.0.0.1:5000` yerine kendi API sunucu adresinizi yazın).*
4. **Kodun Yeri:** `Body - end (Gövde - Son)` seçin.
5. **Sayfalar:** `Tüm Sayfalar` seçin ve kaydedin.

---

## 👤 Adım 2: Mimarlar ve Ofisler Profil Butonları (PDF Madde 4 & 5)

Mimar veya ofis profillerindeki *"Bu uzmanla görüşmeye başla"* butonuna tıklandığında chatbot doğrudan o uzmanın kimliğiyle açılır:

Wix profil sayfasında butona link verirken:
- **Aylin Aydeniz için:** `http://127.0.0.1:5000/?expert_code=aylin_aydeniz`
- **Deniz Arslan için:** `http://127.0.0.1:5000/?expert_code=deniz_arslan`
- **İdil Ergin için:** `http://127.0.0.1:5000/?expert_code=idil_ergin`
- **Mert Kaya için:** `http://127.0.0.1:5000/?expert_code=mert_kaya`
- **Forma Mimarlık için:** `http://127.0.0.1:5000/?office_code=forma_mimarlik`
- **Kuzey Stüdyo için:** `http://127.0.0.1:5000/?office_code=kuzey_studyo`

*Tek hizmet sunan profilden girildiğinde Nova doğrudan o uzmanın alan sorularına başlar; hizmeti yeniden sormaz!*

---

## 📝 Adım 3: Wix İletişim Sayfası Bağlantısı (PDF Madde 8, 16 & 17)

**Önemli Kural:** Chatbot içinde kesinlikle bir form açılmaz. Chatbotta brif onaylandıktan sonra **"İletişim Formunu Tamamla"** butonu müşteriyi Wix iletişim sayfasına yönlendirir (`/iletisim?session_token=...`).

> **Kural:** Form verisi Wix CMS'e / dataset'e **yazılmaz**. Tek kayıt noktası Flask backend'dir (`/api/wix/complete-form`).

1. **Wix Editör'de** ÖN GÖRÜŞME sayfasını açın ve kodlamayı aktif edin.
2. **Backend Kod Dosyası:**
   - Code -> Backend & Public -> Backend -> **+** -> `rumenova-service.web.js` oluşturun.
   - [`wix_integration/rumenova-service.web.js`](rumenova-service.web.js) kodunu yapıştırın.
3. **Sayfa Kodu:**
   - ÖN GÖRÜŞME sayfasının **Page Code** sekmesine [`wix_integration/wix-velo-frontend.js`](wix-velo-frontend.js) kodunu yapıştırın.
   - Eleman ID'leri: `#input1` Ad, `#input2` Soyad, `#input3` E-posta, `#input4` Telefon, `#input5` Not, `#button39` Brifimi Gönder.
   - İsteğe bağlı: formun altına bir metin elemanı ekleyip ID'sini `#txtStatusMsg` yapın (başarı/hata mesajı burada görünür).
4. **Eski Wix veritabanı akışını kapatın:**
   - Form inputları bir dataset'e bağlıysa bağlantıyı kaldırın.
   - Backend `data.js` içindeki `IletisimMesajlari_beforeInsert` hook'unu silin (`/api/session/latest` başka kullanıcının brifini kayda ekleyebilir).

---

## 🗂️ Adım 4: Wix Ön Görüşme Yönetim Paneli (veri backend'den)

Panel ve detay sayfası verileri Wix CMS'ten değil, backend'den okur:

| Wix sayfası | Sayfa kodu | Backend adresi |
|---|---|---|
| Ön Görüşme Yönetim Paneli | [`wix-panel-page.js`](wix-panel-page.js) | `GET /api/panel/on-gorusmeler` |
| Ön Görüşme Detay (`/on-gorusme-detay?id=...`) | [`wix-detail-page.js`](wix-detail-page.js) | `GET /api/panel/on-gorusmeler/<id>` |

- Panelde `#repeater1` dataset'e bağlı değildir; satırları kod doldurur. `#dataset1` ve eski dinamik sayfa (Ön Görüşme Mesajları (Item)) silinmedi, kullanılmıyor.
- "Brifi görüntüle" (`#button44`) yeni detay sayfasını `?id=` ile açar.
- Chatbot brifi, brif onaylandığında ve form gönderildiğinde `chat_sessions.brief_summary` alanına kaydedilir; panel bu kayıtlı brifi gösterir.

---

## 💬 Adım 5: Ortak Konuşma Motoru (HTML widget + Wix chatbot kutusu)

İki chatbot da aynı backend akışını kullanır; yalnızca görünümleri farklıdır.

| Chatbot | Kod | Backend adresi |
|---|---|---|
| HTML widget (sağ alttaki Nova balonu) | `app/static/app.js` | `POST /api/chat/init`, `POST /api/chat` |
| Wix ana sayfa sohbet kutusu | [`wix-home-chatbot.js`](wix-home-chatbot.js) (ANA SAYFA Page Code) | aynı |

Akış: serbest sohbet (yapay zekâ) → proje talebi algılanınca brif teklifi (Evet / Şimdilik hayır) → hizmet alanı → uzman → soru listesi → görsel → görüşme saati → brif özeti ve onay → ön görüşme formuna yönlendirme → serbest sohbete dönüş.

- Mesajlar `chat_messages`, düzeltilmiş cevaplar `collected_data`, aşama ve ham cevaplar `flow_state` sütununda tutulur (veritabanı yapısı değişmedi).
- Brif cevaplarını yapay zekâ (Groq) yorumlar ve yazım hatalarını düzeltir; yapay zekâ yoksa `app/services/normalizer.py` kuralları devreye girer.
- Wix kutusunda seçenekler numaralı listelenir; kullanıcı numarasını veya cevabını yazar. Görsel yükleme yalnızca HTML widget'tadır.
- Wix kutusu eleman ID'leri: `#txtCevap`, `#inpSoru`, `#btnSor`, `#button43` (Ön Görüşme Formunu Tamamla; linkine oturum numarası eklenir).
- Eski `/api/session/*` ve `/api/sohbet` adresleri çalışmaya devam eder.

---

## 📊 Adım 6: Mimar ve Yönetici Paneli

Müşteri Wix formunu gönderdiğinde:
- İletişim bilgileri + Ön Brif + Seçilen Uygun Randevu Saati + Yüklenen Görseller tek kayıtta birleşir.
- **`http://127.0.0.1:5000/dashboard`** adresinde ilgili mimarın veya Buse Mutlu'nun paneline düşer.
