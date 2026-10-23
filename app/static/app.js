// ==========================================================================
// RUMENOVA NOVA CHATBOT (HTML widget görünümü)
// ==========================================================================
// Konuşma kuralları backend'deki ortak motordadır (/api/chat/init, /api/chat).
// Wix chatbot kutusu da aynı motoru kullanır; bu dosya yalnızca mesajları
// ve backend'in gönderdiği seçenekleri (ui) ekrana çizer.
// ==========================================================================

const urlParams = new URLSearchParams(window.location.search);
const paramExpertCode = urlParams.get("expert_code");
const paramOfficeCode = urlParams.get("office_code");
const paramService = urlParams.get("service");
const paramSessionToken = urlParams.get("session_token");

let sessionToken = paramSessionToken || localStorage.getItem("rumenova_session_token") || null;
let currentUI = null;
let uploadedImages = [];
let busy = false;

document.addEventListener("DOMContentLoaded", async () => {
  await initChatSession();
});

async function postJSON(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return res.json();
}

function saveToken(token) {
  sessionToken = token;
  localStorage.setItem("rumenova_session_token", sessionToken);

  // Wix ana sayfasına haber ver (Wix kendi localStorage'ında saklasın)
  try {
    window.parent.postMessage({
      type: "rumenova-session-sync",
      sessionToken: sessionToken
    }, "*");
  } catch (e) {}
}

async function initChatSession() {
  try {
    const data = await postJSON("/api/chat/init", {
      session_token: sessionToken,
      expert_code: paramExpertCode,
      office_code: paramOfficeCode,
      service: paramService
    });
    if (!data.success) return;

    saveToken(data.session_token);
    document.getElementById("chatMessages").innerHTML = "";

    // Konuşmayı aynen geri yükle, ardından o anki seçenekleri göster
    (data.history || []).forEach(msg => {
      if (msg.role === "user") {
        appendUserMessage(msg.content);
      } else {
        appendBotMessage(msg.content);
      }
    });
    renderUI(data.ui);
  } catch (err) {
    console.error("Session hatası:", err);
    appendBotMessage("Şu anda sunucuya ulaşılamıyor. Lütfen birkaç dakika sonra tekrar deneyin.");
  }
}

// --- MESAJ VE SEÇİM GÖNDERME ---

function handleSendText(e) {
  e.preventDefault();
  const input = document.getElementById("chatInput");
  const text = input.value.trim();
  if (!text || busy) return;

  input.value = "";
  sendToBackend({ message: text }, text);
}

function handleOptionClick(index) {
  if (!currentUI || !currentUI.options || busy) return;
  const opt = currentUI.options[index];
  if (!opt) return;

  if (opt.action === "open_url") {
    window.top.location.href = opt.value;
    return;
  }
  sendToBackend({ action: opt.action, value: opt.value, label: opt.label }, opt.label);
}

async function sendToBackend(payload, userText) {
  busy = true;
  disableActiveOptions();
  appendUserMessage(userText);
  const typing = showTyping();

  try {
    const data = await postJSON("/api/chat", { session_token: sessionToken, ...payload });
    typing.remove();
    if (!data.success) {
      appendBotMessage(data.error || "Bir sorun oluştu, lütfen tekrar deneyin.");
      renderUI(currentUI);
      return;
    }
    (data.messages || []).forEach(m => appendBotMessage(m.content));
    renderUI(data.ui);
  } catch (err) {
    console.error(err);
    typing.remove();
    appendBotMessage("Mesajınız iletilemedi. Lütfen tekrar deneyin.");
    renderUI(currentUI);
  } finally {
    busy = false;
  }
}

// --- BACKEND'İN GÖNDERDİĞİ SEÇENEKLERİ ÇİZ ---

function renderUI(ui) {
  currentUI = ui || { type: "none", options: [] };
  const options = currentUI.options || [];

  switch (currentUI.type) {
    case "professionals":
    case "team":
      appendBotOptions(renderCards(options));
      break;
    case "slots":
      appendBotOptions(renderSlots(options));
      break;
    case "media":
      uploadedImages = currentUI.images || [];
      renderMediaUploadStep();
      break;
    case "brief":
      appendBotOptions(renderBriefButtons(options));
      break;
    case "form":
      appendBotOptions(`
        <a href="${escapeHtml(currentUI.form_url)}" target="_top" class="btn-primary-action" style="margin-top:14px; text-decoration:none;">
          <i class="fa-solid fa-arrow-up-right-from-square"></i> Ön Görüşme Formunu Tamamla
        </a>
      `);
      break;
    default:
      if (options.length > 0) {
        let html = renderChips(options);
        if (currentUI.type === "question") {
          html += `
            <p style="font-size:0.75rem; color:var(--color-text-muted); margin-top:8px; font-style:italic;">
              <i class="fa-solid fa-pen"></i> Seçenekler dışında bir tercihiniz varsa aşağıya yazarak da belirtebilirsiniz.
            </p>
          `;
        }
        appendBotOptions(html);
      }
  }

  const input = document.getElementById("chatInput");
  if (input) input.focus();
}

function renderChips(options) {
  return `<div class="options-chips" style="flex-direction: row; flex-wrap: wrap; gap: 8px;">` +
    options.map((opt, i) => `
      <button class="opt-btn" style="flex:1; min-width:110px; justify-content:center;" onclick="handleOptionClick(${i})">
        ${escapeHtml(opt.label)}
      </button>
    `).join("") + `</div>`;
}

function renderCards(options) {
  return `<div class="options-chips">` + options.map((opt, i) => `
    <div class="expert-card-item" onclick="handleOptionClick(${i})">
      ${opt.image
        ? `<img src="${escapeHtml(opt.image)}" class="exp-thumb" alt="${escapeHtml(opt.label)}">`
        : `<div class="avatar-tiny" style="width:44px; height:44px; font-size:1.1rem;"><i class="fa-solid fa-building"></i></div>`}
      <div class="exp-text">
        <h4>${escapeHtml(opt.label)}</h4>
        ${opt.subtitle ? `<span>${escapeHtml(opt.subtitle)}</span>` : ""}
      </div>
    </div>
  `).join("") + `</div>`;
}

function renderSlots(options) {
  return `<div class="slot-chips-grid">` + options.map((opt, i) => `
    <div class="slot-btn" onclick="handleOptionClick(${i})">
      ${opt.action === "select_slot" ? '<i class="fa-regular fa-clock"></i>' : ""} ${escapeHtml(opt.label)}
    </div>
  `).join("") + `</div>`;
}

function renderBriefButtons(options) {
  return options.map((opt, i) => `
    <button class="${opt.action === "approve" ? "btn-primary-action" : "btn-secondary-action"}" onclick="handleOptionClick(${i})">
      <i class="fa-solid ${opt.action === "approve" ? "fa-check" : "fa-pen-to-square"}"></i> ${escapeHtml(opt.label)}
    </button>
  `).join("");
}

// Önceki adımın butonlarına tekrar basılmasın
function disableActiveOptions() {
  document.querySelectorAll(".options-active").forEach(row => {
    row.classList.remove("options-active");
    row.style.pointerEvents = "none";
    row.style.opacity = "0.55";
  });
}

// --- GÖRSEL YÜKLEME ADIMI ---

function renderMediaUploadStep() {
  const container = document.createElement("div");
  container.className = "options-container options-active";
  container.id = "mediaUploadStepContainer";
  const old = document.getElementById("mediaUploadStepContainer");
  if (old) old.removeAttribute("id");
  updateMediaUploadUI(container);

  const chatBody = document.getElementById("chatMessages");
  chatBody.appendChild(container);
  chatBody.scrollTop = chatBody.scrollHeight;
}

function updateMediaUploadUI(container) {
  if (!container) {
    container = document.getElementById("mediaUploadStepContainer");
  }
  if (!container) return;

  const count = uploadedImages.length;
  container.innerHTML = `
    <div class="media-upload-container">
      <p style="font-size:0.8rem; color:var(--color-text-muted); margin-bottom:10px;">
        Desteklenen: JPG, PNG, WEBP (Maksimum 3 görsel, dosya başı 5MB)
      </p>

      <div style="display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-bottom:10px;">
        ${count < 3 ? `
          <button class="opt-btn" onclick="document.getElementById('imageFileInput').click()">
            <i class="fa-solid fa-cloud-arrow-up" style="color:var(--color-primary);"></i> ${count > 0 ? '+ Daha Fazla Görsel Ekle' : 'Görsel Seç & Yükle'}
          </button>
        ` : ''}
        ${count === 0 ? `
          <button class="opt-btn" onclick="sendMediaStep('media_skip', 'Görsel paylaşmadan devam et')">
            Görsel Paylaşmadan Devam Et
          </button>
        ` : ''}
      </div>

      <div class="upload-thumbnails" id="thumbContainer">
        ${uploadedImages.map(img => `
          <div class="thumb-preview">
            <img src="${escapeHtml(img.url)}" alt="Önizleme">
            <button class="remove-thumb" onclick="removeImage('${escapeHtml(img.url)}')" title="Kaldır">&times;</button>
          </div>
        `).join("")}
      </div>
      <div id="uploadStatusText" style="font-size:0.78rem; color:var(--color-primary); margin-top:6px; display:none;">
        <i class="fa-solid fa-spinner fa-spin"></i> Görseller yükleniyor...
      </div>

      ${count > 0 ? `
        <button class="btn-primary-action" style="margin-top:12px;" onclick="sendMediaStep('media_done', 'Yüklenen ${count} görsel ile devam et')">
          <i class="fa-solid fa-check"></i> Yüklenen ${count} Görsel ile Devam Et
        </button>
      ` : ''}
      <p style="font-size:0.75rem; color:var(--color-text-muted); margin-top:8px; font-style:italic;">
        <i class="fa-solid fa-pen"></i> Ek taleplerinizi veya açıklamalarınızı aşağıya yazarak da belirtebilirsiniz.
      </p>
    </div>
  `;
}

function sendMediaStep(action, label) {
  if (busy) return;
  sendToBackend({ action, label }, label);
}

async function handleImageSelected(event) {
  const files = Array.from(event.target.files || []);
  if (files.length === 0) return;

  const statusEl = document.getElementById("uploadStatusText");
  if (statusEl) statusEl.style.display = "block";

  for (const file of files) {
    if (uploadedImages.length >= 3) {
      appendBotMessage("En fazla 3 görsel yükleyebilirsiniz.");
      break;
    }
    const formData = new FormData();
    formData.append("session_token", sessionToken);
    formData.append("file", file);

    try {
      const res = await fetch("/api/session/upload-image", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        uploadedImages = data.images || [];
      } else {
        appendBotMessage(data.error || "Görsel yüklenemedi.");
      }
    } catch (err) {
      appendBotMessage("Yükleme sırasında hata oluştu.");
    }
  }

  event.target.value = "";
  if (statusEl) statusEl.style.display = "none";
  updateMediaUploadUI();
}

async function removeImage(url) {
  await postJSON("/api/session/remove-image", { session_token: sessionToken, image_url: url });
  uploadedImages = uploadedImages.filter(i => i.url !== url);
  updateMediaUploadUI();
}

// --- YARDIMCI FONKSİYONLAR ---

function appendBotMessage(text) {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "chat-row bot";
  div.innerHTML = `
    <div class="avatar-tiny"><i class="fa-solid fa-sparkles"></i></div>
    <div class="bubble"><p>${escapeHtml(text).replace(/\n/g, '<br>')}</p></div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendBotOptions(htmlContent) {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "chat-row bot options-active";
  div.style.maxWidth = "100%";
  div.innerHTML = `
    <div class="avatar-tiny"><i class="fa-solid fa-list-ul"></i></div>
    <div class="bubble" style="width:100%;">${htmlContent}</div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendUserMessage(text) {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "chat-row user";
  div.innerHTML = `
    <div class="bubble"><p>${escapeHtml(text)}</p></div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showTyping() {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "chat-row bot";
  div.innerHTML = `
    <div class="avatar-tiny"><i class="fa-solid fa-sparkles"></i></div>
    <div class="bubble"><p><em>Nova yazıyor…</em></p></div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function startNewSessionConfirm() {
  if (confirm("Mevcut ön görüşmeyi sıfırlayıp yeni bir görüşme başlatmak istiyor musunuz?")) {
    localStorage.removeItem("rumenova_session_token");
    try {
      window.parent.postMessage({ type: "rumenova-session-reset" }, "*");
    } catch (e) {}
    window.location.href = window.location.pathname;
  }
}

function closeChatWindow() {
  window.parent.postMessage("close-rumenova-chat", "*");
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[m]);
}
