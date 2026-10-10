// ==========================================================================
// RUMENOVA - WIX ÖN GÖRÜŞME FORMU VELO KODU
// Hedef Sayfa: https://busemutlubg.wixstudio.com/rumenova/ongorusme
// ==========================================================================
// Bu kod, Wix sayfasındaki form doldurulduğunda hem kullanıcının girdiği 
// ad/soyad bilgilerini hem de Nova Chatbot'tan gelen mimari brif, uzman ve 
// randevu saatini CMS koleksiyonunuza tek seferde kaydeder.
// ==========================================================================

import wixLocation from 'wix-location';
import wixData from 'wix-data';
import { fetch } from 'wix-fetch';

// Render üzerinde canlıya aldığınız API URL adresiniz:
// (Örnek: "https://rumenova-chatbot.onrender.com")
const RENDER_API_URL = "https://rumenova-chatbot.onrender.com"; 

let chatbotData = null;
let sessionToken = null;

$w.onReady(async function () {
  // 1. URL'den session_token parametresini oku (?session_token=...)
  sessionToken = wixLocation.query.session_token;

  if (sessionToken) {
    console.log("Chatbot oturum kodu algılandı:", sessionToken);

    try {
      // Backend API'mizden chatbotta konuşulan tüm verileri çek
      const response = await fetch(`${RENDER_API_URL}/api/session/wix-summary?session_token=${sessionToken}`);
      const res = await response.json();

      if (res.success) {
        chatbotData = res;
        console.log("Chatbot CMS verileri başarıyla yüklendi:", chatbotData);

        // İsteğe bağlı: Sayfada bilgilendirme metni varsa doldur
        if ($w("#txtBriefBadge")) {
          $w("#txtBriefBadge").text = `✓ ${chatbotData.seilenUzman} ile görüşme brifiniz hazır.`;
          $w("#txtBriefBadge").show();
        }
      }
    } catch (err) {
      console.error("Chatbot verileri alınırken hata oluştu:", err);
    }
  }

  // ========================================================================
  // YÖNTEM A: Formunuz Wix Dataset (#dataset1) üzerinden kaydediliyorsa:
  // ========================================================================
  if ($w("#dataset1")) {
    $w("#dataset1").onBeforeSave(() => {
      if (chatbotData) {
        // Form gönderilirken arka planda chatbot verilerini CMS kolonlarına ekle
        $w("#dataset1").setFieldValues({
          hizmetAlan: chatbotData.hizmetAlan || "Genel",
          seilenUzman: chatbotData.seilenUzman || "Belirtilmedi",
          randevuTarihi: chatbotData.randevuTarihi || "Esnek",
          projeBrifi: chatbotData.projeBrifi || "Brif detayı belirtilmedi.",
          durum: "Randevu Bekliyor"
        });
        console.log("Chatbot alanları dataset'e eklendi.");
      }
    });

    $w("#dataset1").onAfterSave(async () => {
      console.log("CMS kaydı başarıyla tamamlandı!");
      // Arka uç Flask veritabanını da bilgilendir
      if (sessionToken) {
        const item = $w("#dataset1").getCurrentItem();
        await fetch(`${RENDER_API_URL}/api/wix/complete-form`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_token: sessionToken,
            name: `${item.ad || ''} ${item.soyad || ''}`.trim(),
            email: item.email || "",
            phone: item.telefon || item.phone || "",
            note: item.not || ""
          })
        }).catch(e => console.error("Flask senkronizasyon hatası:", e));
      }
    });
  }

  // ========================================================================
  // YÖNTEM B: Özel Gönder Butonu (#btnSubmit) ile doğrudan wixData.insert:
  // (Dataset yerine form elemanlarını doğrudan kodla kaydetmek isterseniz)
  // ========================================================================
  if ($w("#btnSubmit")) {
    $w("#btnSubmit").onClick(async () => {
      const ad = $w("#inputAd") ? $w("#inputAd").value : "";
      const soyad = $w("#inputSoyad") ? $w("#inputSoyad").value : "";

      const yeniKayit = {
        ad: ad,
        soyad: soyad,
        hizmetAlan: chatbotData ? chatbotData.hizmetAlan : "Genel",
        seilenUzman: chatbotData ? chatbotData.seilenUzman : "Belirtilmedi",
        randevuTarihi: chatbotData ? chatbotData.randevuTarihi : "Esnek",
        projeBrifi: chatbotData ? chatbotData.projeBrifi : "Chatbot brifi bulunamadı.",
        durum: "Randevu Bekliyor"
      };

      try {
        // "OnGorusmeler" kısmına kendi Wix CMS koleksiyon adınızı yazın
        await wixData.insert("OnGorusmeler", yeniKayit);
        console.log("Kayıt CMS'e yazıldı:", yeniKayit);

        if ($w("#txtStatusMsg")) {
          $w("#txtStatusMsg").text = "Ön görüşme talebiniz başarıyla kaydedildi.";
          $w("#txtStatusMsg").show();
        }
      } catch (insertErr) {
        console.error("CMS kayıt hatası:", insertErr);
      }
    });
  }
});
