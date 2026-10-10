// ==========================================================================
// WIX İLETİŞİM SAYFASI VELO KODU (PDF Madde 16 & 17)
// Bu kod Wix Editör'de "İletişim" sayfasının Page Code sekmesine yapıştırılır.
// ==========================================================================

import wixLocation from 'wix-location';
import { submitWixContactFormWithSession } from 'backend/rumenova-service';

$w.onReady(function () {
  // 1. Chatbot'tan gelen session_token'ı URL'den al
  const sessionToken = wixLocation.query.session_token;

  if (sessionToken) {
    console.log("Chatbot oturumu tespit edildi:", sessionToken);
    // İsteğe bağlı: Sayfa üstüne "Ön brifiniz hazırlandı, lütfen iletişim bilgilerinizi giriniz" bilgi kutusu gösterilebilir
    if ($w("#txtBriefInfoBadge")) {
      $w("#txtBriefInfoBadge").text = "✓ Nova ile oluşturduğunuz ön brifiniz hazır. Formu tamamladığınızda doğrudan mimarınıza iletilecektir.";
      $w("#txtBriefInfoBadge").show();
    }
  }

  // 2. İletişim Formu Gönder Butonuna Tıklandığında
  $w("#btnSubmitContact").onClick(async () => {
    const name = $w("#inputName").value;
    const email = $w("#inputEmail").value;
    const phone = $w("#inputPhone").value;
    const note = $w("#inputNote") ? $w("#inputNote").value : "";

    if (!name || !phone) {
      $w("#txtStatusMsg").text = "Lütfen adınızı ve telefon numaranızı giriniz.";
      $w("#txtStatusMsg").show();
      return;
    }

    $w("#btnSubmitContact").disable();
    $w("#txtStatusMsg").text = "Bilgileriniz mimarımıza aktarılıyor...";
    $w("#txtStatusMsg").show();

    // Backend servisine gönder ve chatbot brifiyle birleştir
    const result = await submitWixContactFormWithSession({
      session_token: sessionToken,
      name: name,
      email: email,
      phone: phone,
      note: note
    });

    if (result.success) {
      // PDF Madde 17 Başarılı Tamamlanma Mesajı:
      $w("#txtStatusMsg").text = "Bizi tercih ettiğiniz için teşekkür ederiz. Ön görüşme bilgileriniz seçtiğiniz mimara/ofise iletildi. Görüşme saatiniz, uzman tarafından teyit edildikten sonra kesinleşecektir.";
      // Form alanlarını temizle
      $w("#inputName").value = "";
      $w("#inputEmail").value = "";
      $w("#inputPhone").value = "";
    } else {
      $w("#btnSubmitContact").enable();
      $w("#txtStatusMsg").text = "Hata: " + (result.error || "Gönderilemedi, lütfen tekrar deneyin.");
    }
  });
});
