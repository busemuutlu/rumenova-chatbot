// ==========================================================================
// RUMENOVA - NOVA CHATBOT KUTUSU (Page Code: ANA SAYFA ve HAKKIMIZDA)
// ==========================================================================
// HTML widget ile aynı konuşma motorunu kullanır (/api/chat/init, /api/chat).
// Mesajlar, brif cevapları ve aşama backend'de (SQLite) tutulur; bu kod
// yalnızca Nova'nın son yanıtını ve seçenekleri gösterir.
// Aynı kod iki sayfada da kullanılır; bu sayfalarda HTML widget (Özel Kod) yüklenmez.
//
// Eleman ID'leri:
//   #txtCevap   Nova'nın yanıtı + numaralı seçenekler
//   #inpSoru    kullanıcı mesajı (Enter ile de gönderilir)
//   #btnSor     gönder
//   #button43   "Ön Görüşme Formunu Tamamla" (linkine oturum numarası eklenir)
// Seçenekler numaralı listelenir; kullanıcı numarasını veya cevabını yazar.
// Görsel yükleme bu kutuda yoktur (HTML widget'ta vardır); görsel adımında
// "Görsel paylaşmadan devam et" seçeneği çıkar.
// ==========================================================================

import { local } from 'wix-storage';
import wixLocation from 'wix-location';

const API_BASE_URL = "https://rumenova-chatbot.onrender.com";
const FORM_URL = "https://busemutlubg.wixstudio.com/rumenova/ongorusme";
const TOKEN_KEY = "rumenova_wix_chat_token";
// Bu sorularda "2" gibi bir sayı seçenek numarası değil, cevabın kendisidir
const NUMERIC_ANSWER_FIELDS = ["kullanici_sayisi", "kat_sayisi", "mevcut_kat_sayisi"];

let sessionToken = null;
let currentUI = null;
let busy = false;

$w.onReady(async function () {
  $w("#btnSor").onClick(() => sendMessage());
  $w("#inpSoru").onKeyPress((event) => {
    if (event.key === "Enter") sendMessage();
  });

  await initChat();
});

async function postJSON(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return response.json();
}

function readToken() {
  try {
    return local.getItem(TOKEN_KEY) || null;
  } catch (e) {
    return null;
  }
}

function saveToken(token) {
  sessionToken = token;
  try {
    local.setItem(TOKEN_KEY, token);
  } catch (e) {}
  // Form butonu her zaman bu sohbetin oturumuyla açılır (brif panele bu sayede düşer)
  try {
    $w("#button43").link = `${FORM_URL}?session_token=${encodeURIComponent(token)}`;
    $w("#button43").target = "_self";
  } catch (e) {}
}

async function initChat() {
  showText("Nova bağlanıyor...");
  try {
    const data = await postJSON("/api/chat/init", { session_token: readToken() });
    if (!data.success) throw new Error(data.error || "init");
    saveToken(data.session_token);

    // Sayfa yenilendiyse: son kullanıcı mesajından sonraki Nova yanıtlarını göster
    const history = data.history || [];
    const lastReplies = [];
    for (let i = history.length - 1; i >= 0 && history[i].role !== "user"; i--) {
      lastReplies.unshift(history[i].content);
    }
    render(lastReplies, data.ui);
  } catch (error) {
    console.error("Nova başlatılamadı:", error);
    showText("Şu anda sunucuya ulaşılamıyor. Lütfen birkaç dakika sonra tekrar deneyin.");
  }
}

async function sendMessage() {
  if (busy) return;

  const text = String($w("#inpSoru").value || "").trim();
  if (!text) {
    showText("Lütfen önce mesajınızı yazın.");
    return;
  }
  if (!sessionToken) {
    await initChat();
    if (!sessionToken) return;
  }

  const option = optionByNumber(text);
  if (option && option.action === "open_url") {
    wixLocation.to(option.value);
    return;
  }

  busy = true;
  $w("#btnSor").disable();
  $w("#inpSoru").value = "";
  showText("Nova yazıyor...");

  try {
    const payload = option
      ? { action: option.action, value: option.value, label: option.label }
      : { message: text };
    const data = await postJSON("/api/chat", { session_token: sessionToken, ...payload });

    if (!data.success) {
      showText(data.error || "Bir sorun oluştu, lütfen tekrar deneyin.");
      return;
    }
    // Sunucu oturumu bulamayıp yenisini açtıysa yeni oturum numarasını sakla
    if (data.session_token && data.session_token !== sessionToken) saveToken(data.session_token);
    render((data.messages || []).map(m => m.content), data.ui);
  } catch (error) {
    console.error("Nova mesajı iletilemedi:", error);
    showText("Mesajınız iletilemedi. Lütfen tekrar deneyin.");
  } finally {
    busy = false;
    $w("#btnSor").enable();
  }
}

// Kullanıcı seçenek numarası yazdıysa ilgili seçeneği döner
function optionByNumber(text) {
  const options = (currentUI && currentUI.options) || [];
  if (!/^\d+$/.test(text) || options.length === 0) return null;

  const question = currentUI.question || {};
  if (currentUI.type === "question" && NUMERIC_ANSWER_FIELDS.includes(question.field)) return null;

  return options[Number(text) - 1] || null;
}

function render(messages, ui) {
  currentUI = ui || { type: "none", options: [] };
  const options = currentUI.options || [];

  let text = messages.filter(Boolean).join("\n\n");
  if (options.length > 0) {
    text += "\n\n" + options.map((opt, i) => `${i + 1}) ${opt.label}`).join("\n");
    if (currentUI.type === "question") {
      text += "\n\nNumarasını yazabilir ya da cevabınızı kendiniz yazabilirsiniz.";
    } else if (currentUI.type === "media") {
      text += "\n\nEk talebinizi yazabilir ya da 1 yazarak devam edebilirsiniz.";
    } else if (currentUI.type !== "none") {
      text += "\n\nSeçiminizin numarasını ya da adını yazabilirsiniz.";
    }
  }
  showText(text || "Size nasıl yardımcı olabilirim?");
}

function showText(text) {
  $w("#txtCevap").text = text;
}
