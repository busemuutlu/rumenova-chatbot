// ==========================================================================
// RUMENOVA - ÖN GÖRÜŞME YÖNETİM PANELİ (Page Code)
// ==========================================================================
// Veriler Wix CMS'ten DEĞİL, backend'den (Flask) gelir:
//   backend/rumenova-service.web.js -> getOnGorusmeler()
// Sayfadaki #dataset1 silinmedi ama artık kullanılmıyor.
//
// Eleman ID'leri:
//   #repeater1 -> talep listesi
//     #text103 Ad, #text107 Soyad, #text104 Hizmet Alanı,
//     #text105 Kayıt Tarihi, #text106 Durum, #button44 "Brifi görüntüle"
//   #text86 Toplam, #text89 Bu Ay, #text92 Bekleyen, #text95 Onaylanan
//   #input1 arama, #button39 Yenile, #button47 Verileri Yenile,
//   #button48 CSV İndir, #htmlCsv CSV indirme iframe'i
// ==========================================================================

import wixLocation from 'wix-location';
import { getOnGorusmeler } from 'backend/rumenova-service.web';

// Detay sayfasının adresi (Ön Görüşme Detay sayfası, ?id=... ile açılır)
const DETAY_SAYFASI = '/on-gorusme-detay';

let queue = Promise.resolve();
let searchTimer;
let allItems = [];
let pendingDownload = null;

$w.onReady(() => {
  $w('#button48').disable();

  $w('#htmlCsv').onMessage((event) => {
    if (event.data?.type === 'CSV_READY' && pendingDownload) {
      $w('#htmlCsv').postMessage(pendingDownload);
      pendingDownload = null;
    }
  });

  $w('#repeater1').onItemReady(($item, item) => {
    $item('#text103').text = item.ad || '-';
    $item('#text107').text = item.soyad || '';
    $item('#text104').text = item.hizmetAlan || '-';
    $item('#text105').text = shortDate(item._createdDate);
    $item('#text106').text = item.durum || '-';
    $item('#button44').onClick(() => {
      wixLocation.to(`${DETAY_SAYFASI}?id=${encodeURIComponent(item._id)}`);
    });
  });

  $w('#input1').onInput(() => {
    clearTimeout(searchTimer);

    searchTimer = setTimeout(() => {
      enqueue(applySearch);
    }, 300);
  });

  $w('#button39').onClick(() => {
    enqueue(refreshPanel);
  });

  $w('#button47').onClick(() => {
    enqueue(refreshPanel);
  });

  $w('#button48').onClick(() => {
    enqueue(exportCsv);
  });

  enqueue(refreshPanel);
});

function enqueue(task) {
  queue = queue.then(async () => {
    $w('#button39').disable();
    $w('#button47').disable();
    $w('#button48').disable();

    try {
      await task();
    } catch (error) {
      console.error(
        'Ön görüşme paneli işlemi tamamlanamadı:',
        error
      );

      $w('#button39').label = 'Tekrar dene';
    } finally {
      $w('#button39').enable();
      $w('#button47').enable();
      $w('#button48').enable();
    }
  });
}

function statusKey(value) {
  return String(value || '')
    .trim()
    .toLocaleLowerCase('tr-TR');
}

function monthKey(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return '';

  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Europe/Istanbul',
    year: 'numeric',
    month: '2-digit'
  }).formatToParts(date);

  const year = parts.find(
    part => part.type === 'year'
  ).value;

  const month = parts.find(
    part => part.type === 'month'
  ).value;

  return `${year}-${month}`;
}

async function refreshPanel() {
  const res = await getOnGorusmeler();

  if (!res.success) {
    throw new Error(res.error || 'Kayıtlar backend\'den alınamadı.');
  }

  allItems = res.items || [];
  const thisMonth = monthKey(new Date());

  const waitingStatuses = [
    'bekleyen',
    'randevu bekliyor',
    'bekleyen randevu'
  ];

  const confirmedStatuses = [
    'onaylandı',
    'onaylanan',
    'onaylanan randevu'
  ];

  $w('#text86').text = String(allItems.length);

  $w('#text89').text = String(
    allItems.filter(item =>
      item._createdDate &&
      monthKey(item._createdDate) === thisMonth
    ).length
  );

  $w('#text92').text = String(
    allItems.filter(item =>
      waitingStatuses.includes(statusKey(item.durum))
    ).length
  );

  $w('#text95').text = String(
    allItems.filter(item =>
      confirmedStatuses.includes(statusKey(item.durum))
    ).length
  );

  await applySearch();

  $w('#button39').label = 'Yenile';
}

function filteredItems() {
  const terms = String($w('#input1').value || '')
    .trim()
    .toLocaleLowerCase('tr-TR')
    .split(/\s+/)
    .filter(Boolean);

  return allItems.filter(item => {
    const name = `${item.ad || ''} ${item.soyad || ''}`.toLocaleLowerCase('tr-TR');
    return terms.every(term => name.includes(term));
  });
}

async function applySearch() {
  $w('#repeater1').data = filteredItems();
}

function csvCell(value) {
  let text = String(value ?? '');

  // Kullanıcı metninin Excel formülü olarak çalışmasını önler.
  if (/^[\s]*[=+\-@]/.test(text)) {
    text = "'" + text;
  }

  return '"' + text.replace(/"/g, '""') + '"';
}

function dateText(value) {
  if (!value) return '';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat('tr-TR', {
    timeZone: 'Europe/Istanbul',
    dateStyle: 'short',
    timeStyle: 'short'
  }).format(date);
}

function shortDate(value) {
  if (!value) return '-';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return String(value);

  return new Intl.DateTimeFormat('tr-TR', {
    timeZone: 'Europe/Istanbul',
    day: '2-digit',
    month: '2-digit',
    year: '2-digit'
  }).format(date);
}

async function exportCsv() {
  const items = filteredItems();

  const rows = [
    [
      'Ad',
      'Soyad',
      'E-posta',
      'Telefon',
      'Hizmet Alanı',
      'Kayıt Tarihi',
      'Durum',
      'Seçilen Uzman',
      'Randevu Tarihi ve Saati',
      'Müşteri Notu',
      'Proje Brifi'
    ]
  ];

  for (const item of items) {
    rows.push([
      item.ad,
      item.soyad,
      item.email,
      item.telefon,
      item.hizmetAlan,
      dateText(item._createdDate),
      item.durum,
      item.seilenUzman,
      item.randevuTarihi,
      item.mesaj,
      item.projeBrifi
    ]);
  }

  const content = '\uFEFF' + rows
    .map(row => row.map(csvCell).join(';'))
    .join('\r\n');

  pendingDownload = {
    type: 'CSV_DOWNLOAD',
    content,
    filename:
      'Rumenova_OnGorusme_' +
      new Date().toISOString().slice(0, 10) +
      '.csv'
  };

  $w('#htmlCsv').postMessage({
    type: 'CSV_PING'
  });
}
