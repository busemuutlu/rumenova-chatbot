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

1. **Wix Editör'de** İletişim sayfasını açın ve **Dev Mode**'u aktif edin.
2. **Backend Kod Dosyası:**
   - Code Files -> Backend -> **New Web Module (.jsw)** oluşturun.
   - Adını `rumenova-service.jsw` koyun ve [`wix_integration/wix-velo-backend.jsw`](file:///c:/wamp64/www/chat/wix_integration/wix-velo-backend.jsw) kodunu yapıştırın.
3. **Sayfa Kodu:**
   - İletişim sayfasının altındaki **Page Code** sekmesine [`wix_integration/wix-velo-frontend.js`](file:///c:/wamp64/www/chat/wix_integration/wix-velo-frontend.js) kodunu yapıştırın.

---

## 📊 Adım 4: Mimar ve Yönetici Paneli

Müşteri Wix formunu gönderdiğinde:
- İletişim bilgileri + Ön Brif + Seçilen Uygun Randevu Saati + Yüklenen Görseller tek kayıtta birleşir.
- **`http://127.0.0.1:5000/dashboard`** adresinde ilgili mimarın veya Buse Mutlu'nun paneline düşer.
