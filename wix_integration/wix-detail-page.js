// ==========================================================================
// RUMENOVA - ÖN GÖRÜŞME DETAY SAYFASI (Page Code)
// Adres: /on-gorusme-detay?id=<talep id>
// ==========================================================================
// Veri Wix CMS'ten DEĞİL, backend'den (Flask) gelir:
//   backend/rumenova-service.web.js -> getOnGorusme(id)
// Eski dinamik sayfa (Ön Görüşme Mesajları (Item)) silinmedi; yerinde duruyor.
//
// Eleman ID'leri:
//   #text71 Ad, #text72 Soyad, #text73 E-posta, #text74 Telefon,
//   #text82 Hizmet Alanı, #text80 Proje Brifi, #gallery1 Proje Görselleri
// ==========================================================================

import wixLocation from 'wix-location';
import { getOnGorusme } from 'backend/rumenova-service.web';

$w.onReady(async function () {
  const id = wixLocation.query.id;

  if (!id) {
    showMissing("Görüntülenecek talep seçilmedi.");
    return;
  }

  const res = await getOnGorusme(id);

  if (!res.success || !res.item) {
    showMissing("Talep bulunamadı veya şu anda yüklenemiyor.");
    return;
  }

  const item = res.item;

  $w("#text71").text = item.ad || "-";
  $w("#text72").text = item.soyad || "-";
  $w("#text73").text = item.email || "-";
  $w("#text74").text = item.telefon || "-";
  $w("#text82").text = item.hizmetAlan || "-";

  // Proje brifi + müşterinin formda yazdığı not
  let brif = item.projeBrifi || "Brif bilgisi yok.";
  if (item.mesaj) {
    brif += `\n------------------------------------\nMüşteri Notu: ${item.mesaj}`;
  }
  $w("#text80").text = brif;

  const gorseller = (item.projeGorselleri || []).filter(g => g && g.src);
  if (gorseller.length > 0) {
    $w("#gallery1").items = gorseller;
    $w("#gallery1").show();
    $w("#gallery1").expand();
  } else {
    $w("#gallery1").items = [];
    $w("#gallery1").collapse();
  }
});

function showMissing(message) {
  ["#text71", "#text72", "#text73", "#text74", "#text82"].forEach(id => {
    $w(id).text = "-";
  });
  $w("#text80").text = message;
  $w("#gallery1").items = [];
  $w("#gallery1").collapse();
}
