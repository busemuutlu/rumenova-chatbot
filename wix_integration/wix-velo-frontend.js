// ==========================================================================
// RUMENOVA - WIX ÖN GÖRÜŞME FORMU VELO KODU (Page Code)
// Hedef Sayfa: https://busemutlubg.wixstudio.com/rumenova/ongorusme
// ==========================================================================
// Form verisi SADECE backend'e (rumenova-service.web.js -> Flask API) gider.
// Wix CMS / dataset / wixData KULLANILMAZ.
//
// Sayfadaki eleman ID'leri (Wix Editor'deki gerçek ID'ler):
//   #input1 -> Ad *          #input2 -> Soyad *
//   #input3 -> E-posta *     #input4 -> Telefon
//   #input5 -> Ekleme İstedikleriniz *
//   #button39 -> "Brifimi Gönder"
//   #txtStatusMsg -> (isteğe bağlı) durum mesajı için metin elemanı
// ==========================================================================

import wixLocation from 'wix-location';
import { submitOnGorusmeForm } from 'backend/rumenova-service.web';

const BUTTON_LABEL = "Brifimi Gönder";

$w.onReady(function () {
  // Chatbot'tan gelindiyse URL'de ?session_token=... bulunur
  const sessionToken = wixLocation.query.session_token || "";

  $w("#button39").onClick(async () => {
    const ad = $w("#input1").value.trim();
    const soyad = $w("#input2").value.trim();
    const email = $w("#input3").value.trim();
    const telefon = $w("#input4").value.trim();
    const not = $w("#input5").value.trim();

    if (!ad || !soyad || !email || !not) {
      ["#input1", "#input2", "#input3", "#input5"].forEach(id => $w(id).updateValidityIndication());
      showStatus("Lütfen yıldızlı (*) alanları doldurun.", true);
      return;
    }

    $w("#button39").disable();
    $w("#button39").label = "Gönderiliyor...";

    const res = await submitOnGorusmeForm({
      session_token: sessionToken,
      ad: ad,
      soyad: soyad,
      email: email,
      phone: telefon,
      note: not
    });

    if (res.success) {
      $w("#button39").label = "Gönderildi ✓";
      showStatus(res.message || "Ön görüşme talebiniz başarıyla alındı.", false);
      ["#input1", "#input2", "#input3", "#input4", "#input5"].forEach(id => {
        $w(id).value = "";
        $w(id).resetValidityIndication();
      });
      return;
    }

    // Hata: buton tekrar kullanılabilir olsun
    $w("#button39").enable();
    $w("#button39").label = BUTTON_LABEL;
    showStatus(res.message || "Talebiniz gönderilemedi. Lütfen tekrar deneyin.", true);
  });
});

// Sayfada #txtStatusMsg metin elemanı varsa mesajı orada gösterir
function showStatus(message, isError) {
  console.log(isError ? "Form hatası:" : "Form gönderildi:", message);
  try {
    const statusEl = $w("#txtStatusMsg");
    statusEl.text = message;
    statusEl.show();
  } catch (e) {
    // Sayfada durum metni yok; mesaj sadece konsola yazıldı
  }
}
