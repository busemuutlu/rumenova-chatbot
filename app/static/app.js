// ==========================================================================
// RUMENOVA NOVA CHATBOT MOTORU
// ==========================================================================

const urlParams = new URLSearchParams(window.location.search);
const paramExpertCode = urlParams.get("expert_code");
const paramOfficeCode = urlParams.get("office_code");
const paramService = urlParams.get("service");
const paramSessionToken = urlParams.get("session_token");

let sessionToken = paramSessionToken || localStorage.getItem("rumenova_session_token") || null;
let currentService = null;
let selectedExpert = null;
let selectedOffice = null;
let currentQuestion = null;
let collectedData = {};
let uploadedImages = [];
let selectedSlotText = "";
let selectedSlotId = null;
document.addEventListener("DOMContentLoaded", async () => {
  await initChatSession();
});

async function initChatSession() {
  try {
    const res = await fetch("/api/session/init", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_token: sessionToken,
        expert_code: paramExpertCode,
        office_code: paramOfficeCode,
        service: paramService
      })
    });

    const result = await res.json();
    if (result.success) {
      sessionToken = result.session_token;
      localStorage.setItem("rumenova_session_token", sessionToken);

      // Wix ana sayfasına haber ver (Wix kendi localStorage'ında saklasın)
      try {
        window.parent.postMessage({
          type: "rumenova-session-sync",
          sessionToken: sessionToken
        }, "*");
      } catch (e) {}

      currentService = result.service_type;
      collectedData = result.collected_data || {};
      uploadedImages = result.uploaded_images || [];
      selectedSlotId = result.selected_slot_id || null;
      selectedSlotText = result.selected_slot_text || "";

      if (result.selected_expert_id) {
        selectedExpert = {
          id: result.selected_expert_id,
          name: result.selected_expert_name || "Uzmanımız"
        };
      }
      if (result.selected_office_id) {
        selectedOffice = {
          id: result.selected_office_id,
          name: result.selected_office_name || "Ofisimiz"
        };
      }

      renderInitialFlow(result);
    }
  } catch (err) {
    console.error("Session hatası:", err);
  }
}

function renderInitialFlow(data) {
  const container = document.getElementById("chatMessages");
  container.innerHTML = "";

  // 1. MEVCUT GEÇMİŞ VARSA (Sayfa geçişinde konuşmayı aynen geri yükle!)
  if (data.chat_messages && data.chat_messages.length > 0) {
    data.chat_messages.forEach(msg => {
      if (msg.role === "user") {
        appendUserMessage(msg.content);
      } else {
        appendBotMessage(msg.content);
      }
    });

    // Oturumun ulaştığı aşamaya göre doğru kontrolü göster:
    // A) Brif onaylandıysa iletişim butonunu göster
    if (data.is_brief_approved) {
      const wixUrl = `https://busemutlubg.wixstudio.com/rumenova/ongorusme?session_token=${sessionToken}`;
      appendBotOptions(`
        <a href="${wixUrl}" target="_top" class="btn-primary-action" style="margin-top:14px; text-decoration:none;">
          <i class="fa-solid fa-arrow-up-right-from-square"></i> Ön Görüşme Formunu Tamamla
        </a>
        <p style="font-size:0.75rem; color:var(--color-text-muted); text-align:center; margin-top:8px;">
          * Ön görüşme özetinizi onayladınız. Lütfen ön görüşme formuna geçerek süreci tamamlayın.
        </p>
      `);
      return;
    }

    // B) Saat seçildiyse brif özetini göster
    if (data.selected_slot_text) {
      renderBriefSummary(false);
      return;
    }

    // C) Sorular bitti ama saat seçilmediyse saat seçimini göster
    if (!data.next_question && (data.available_slots && data.available_slots.length > 0)) {
      renderSlotSelection(data.available_slots, false);
      return;
    }

    // D) Sıradaki soru varsa kontrollerini göster
    if (data.next_question) {
      currentQuestion = data.next_question;
      renderQuestionControls(data.next_question);
      return;
    }

    // E) Eğer uzman seçilmediyse uzman listesini göster
    if (currentService && !selectedExpert && !selectedOffice) {
      renderExpertSelection(false);
      return;
    }

    return;
  }

  // 2. YENİ OTURUM AKIŞI (Henüz mesaj yoksa)
  // Profil Butonundan Tek Hizmetli Uzmanla Giriş
  if (paramExpertCode && data.next_question) {
    const profs = getProfessionalsData();
    const exp = profs.experts.find(e => e.expert_code === paramExpertCode);
    const expName = exp ? exp.name : "Uzmanımız";
    selectedExpert = { id: exp ? exp.id : 1, name: expName };
    const serviceTitle = getServiceTitle(currentService);

    appendBotMessage(`<strong>${expName}</strong> ile ${serviceTitle.toLowerCase()} alanında ön görüşmenize başlayalım.`);
    setTimeout(() => {
      displayQuestion(data.next_question);
    }, 400);
    return;
  }

  // Çok Hizmetli Ofisten Giriş
  if (paramOfficeCode && !currentService) {
    const profs = getProfessionalsData();
    const off = profs.offices.find(o => o.office_code === paramOfficeCode);
    const offName = off ? off.name : "Ofisimiz";

    appendBotMessage(`<strong>${offName}</strong> ile hangi hizmet alanında ön görüşme yapmak istersiniz?`);
    const chipsHtml = (off ? off.service_areas : ["mimari", "ic_mimari"]).map(sKey => `
      <button class="opt-btn" onclick="selectServiceArea('${sKey}', '${getServiceTitle(sKey)}')">
        ${getServiceIcon(sKey)} ${getServiceTitle(sKey)}
      </button>
    `).join("");
    appendBotOptions(chipsHtml);
    return;
  }

  // Genel Chatbot Butonundan Giriş (Madde 2: Hizmet Alanı Seçimi)
  if (!currentService) {
    appendBotMessage("Merhaba, Rumenova’ya hoş geldiniz. Ben yapay zekâ destekli asistan Nova. Hangi hizmet alanında ön görüşme yapmak istersiniz?");
    const optionsHtml = `
      <div class="options-chips">
        <button class="opt-btn" onclick="selectServiceArea('mimari', 'Mimari Tasarım')">
          <i class="fa-solid fa-compass-drafting" style="color:var(--color-primary);"></i> Mimari Tasarım
        </button>
        <button class="opt-btn" onclick="selectServiceArea('ic_mimari', 'İç Mimarlık')">
          <i class="fa-solid fa-couch" style="color:var(--color-primary);"></i> İç Mimarlık
        </button>
        <button class="opt-btn" onclick="selectServiceArea('peyzaj', 'Peyzaj Tasarımı')">
          <i class="fa-solid fa-tree" style="color:var(--color-primary);"></i> Peyzaj Tasarımı
        </button>
      </div>
    `;
    appendBotOptions(optionsHtml);
    return;
  }

  // Hizmet Seçilmiş ama Uzman Seçilmemişse
  if (!selectedExpert && !selectedOffice) {
    renderExpertSelection(true);
    return;
  }

  // Kaldığı Sorudan Devam Et
  if (data.next_question) {
    displayQuestion(data.next_question);
  }
}

// 1. ADIM: HİZMET SEÇİMİ
async function selectServiceArea(serviceKey, serviceTitle) {
  currentService = serviceKey;
  appendUserMessage(serviceTitle + " alanını seçtim.");

  await fetch("/api/session/select-service", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_token: sessionToken,
      service_type: serviceKey,
      service_title: serviceTitle
    })
  });

  setTimeout(() => {
    renderExpertSelection();
  }, 350);
}

// 2. ADIM: UZMAN / OFİS LİSTESİ
function renderExpertSelection(showMsg = true) {
  if (showMsg) {
    appendBotMessage("Bu alanda hangi mimar veya ofisle görüşmek istersiniz?");
  }


  const profs = getProfessionalsData();
  const matchingExperts = profs.experts.filter(e => e.service_areas.includes(currentService));
  const matchingOffices = profs.offices.filter(o => o.service_areas.includes(currentService));

  let cardsHtml = `<div class="options-chips">`;

  // Bireysel Uzmanlar
  matchingExperts.forEach(exp => {
    cardsHtml += `
      <div class="expert-card-item" onclick="selectProfessional(${exp.id}, '${escapeHtml(exp.name)}', 'expert')">
        <img src="${exp.avatar_url}" class="exp-thumb" alt="${exp.name}">
        <div class="exp-text">
          <h4>${exp.name}</h4>
          <span>${exp.title} • ${exp.location}</span>
        </div>
      </div>
    `;
  });

  // Ofisler
  matchingOffices.forEach(off => {
    cardsHtml += `
      <div class="expert-card-item" onclick="selectProfessional(${off.id}, '${escapeHtml(off.name)}', 'office')">
        <div class="avatar-tiny" style="width:44px; height:44px; font-size:1.1rem;"><i class="fa-solid fa-building"></i></div>
        <div class="exp-text">
          <h4>${off.name} (Ofis)</h4>
          <span>${off.location} • Ekip: ${(off.team_members || []).map(t => t.name).join(', ')}</span>
        </div>
      </div>
    `;
  });

  cardsHtml += `</div>`;
  appendBotOptions(cardsHtml);
}

// 3. ADIM: UZMAN / OFİS SEÇİLDİ (OFİS EKİP KURALI ENTEGRE)
async function selectProfessional(id, name, type) {
  appendUserMessage(`${name} ile görüşmek istiyorum.`);

  const bodyData = { session_token: sessionToken, name: name };
  if (type === "expert") {
    selectedExpert = { id, name };
    bodyData.expert_id = id;
  } else {
    selectedOffice = { id, name };
    bodyData.office_id = id;
  }

  const res = await fetch("/api/session/select-expert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bodyData)
  });

  const data = await res.json();
  if (!data.success) return;

  const serviceTitle = getServiceTitle(currentService);

  // KURAL: Eğer ofiste 2 veya daha fazla uzman varsa seçtir
  if (data.need_team_selection && data.team_members && data.team_members.length > 1) {
    setTimeout(() => {
      appendBotMessage(`<strong>${data.office_name}</strong> ekibimizden hangi uzmanımızla görüşmek istersiniz?`);
      let teamHtml = `<div class="options-chips">`;
      data.team_members.forEach(member => {
        teamHtml += `
          <div class="expert-card-item" onclick="selectTeamMember(${member.id}, '${escapeHtml(member.name)}')">
            <img src="${member.avatar_url}" class="exp-thumb" alt="${member.name}">
            <div class="exp-text">
              <h4>${member.name}</h4>
              <span>${member.title} • ${data.office_name} Ekibi</span>
            </div>
          </div>
        `;
      });
      teamHtml += `</div>`;
      appendBotOptions(teamHtml);
    }, 300);
    return;
  }

  // KURAL: Eğer ofiste yalnızca 1 uzman varsa doğrudan o uzmanla başla
  if (data.auto_expert) {
    selectedExpert = { id: data.auto_expert.id, name: data.auto_expert.name };
    setTimeout(() => {
      appendBotMessage(`<strong>${data.office_name}</strong> ekibinden <strong>${data.auto_expert.name}</strong> ile ${serviceTitle.toLowerCase()} alanında ön görüşmenize başlayalım.`);
      if (data.next_question) {
        setTimeout(() => {
          displayQuestion(data.next_question);
        }, 400);
      }
    }, 300);
    return;
  }

  // Bireysel uzman ile doğrudan başla
  if (data.next_question) {
    setTimeout(() => {
      appendBotMessage(`Harika bir tercih! <strong>${name}</strong> ile ${serviceTitle.toLowerCase()} alanında ön görüşme sorularımıza başlıyoruz.`);
      setTimeout(() => {
        displayQuestion(data.next_question);
      }, 400);
    }, 300);
  }
}

// EKİP ÜYESİ SEÇİLDİĞİNDE
async function selectTeamMember(expertId, expertName) {
  selectedExpert = { id: expertId, name: expertName };
  appendUserMessage(`${expertName} ile görüşmek istiyorum.`);

  const res = await fetch("/api/session/select-expert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_token: sessionToken, expert_id: expertId, name: expertName })
  });

  const data = await res.json();
  if (data.success && data.next_question) {
    setTimeout(() => {
      appendBotMessage(`Harika! <strong>${expertName}</strong> ile ön görüşme sorularımıza başlıyoruz.`);
      setTimeout(() => {
        displayQuestion(data.next_question);
      }, 400);
    }, 300);
  }
}

// 4. ADIM: SORUYU GÖSTER (Seçenekler varsa buton + altta farklı tercih yazma notu)
function renderQuestionControls(q) {
  if (!q) return;
  currentQuestion = q;

  // Görsel yükleme adımı
  if (q.type === "media_and_notes" || (q.id && q.id.includes("gorsel"))) {
    renderMediaUploadStep();
    return;
  }

  // Eğer soruda seçenekler (choices) varsa buton olarak göster
  if (q.choices && q.choices.length > 0) {
    let choicesHtml = `<div class="options-chips" style="flex-direction: row; flex-wrap: wrap; gap: 8px;">`;
    q.choices.forEach(choice => {
      choicesHtml += `
        <button class="opt-btn" style="flex:1; min-width:110px; justify-content:center;" onclick="handleChoiceClick('${escapeHtml(choice)}')">
          ${choice}
        </button>
      `;
    });
    choicesHtml += `</div>`;
    
    // Müşteriye seçenekler dışındaki tercihini yazabileceğini belirten not
    choicesHtml += `
      <p style="font-size:0.75rem; color:var(--color-text-muted); margin-top:8px; font-style:italic;">
        <i class="fa-solid fa-pen"></i> Seçenekler dışında bir tercihiniz varsa aşağıya yazarak da belirtebilirsiniz.
      </p>
    `;

    appendBotOptions(choicesHtml);
  }

  // Doğrudan klavyeden yazabilmesi için input'a odaklan
  const input = document.getElementById("chatInput");
  if (input) input.focus();
}

function displayQuestion(q) {
  currentQuestion = q;
  appendBotMessage(q.question);
  renderQuestionControls(q);
}


function handleChoiceClick(choiceText) {
  handleUserAnswer(choiceText);
}

function handleSendText(e) {
  e.preventDefault();
  const input = document.getElementById("chatInput");
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  handleUserAnswer(text);
}

let askedForEstimate = false;

// CEVABI GÖNDER VE SONRAKİ SORUYU AL
async function handleUserAnswer(answerText) {
  appendUserMessage(answerText);
  const field = currentQuestion ? currentQuestion.field : null;

  try {
    const res = await fetch("/api/session/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_token: sessionToken,
        message: answerText,
        current_field: field,
        asked_for_estimate: askedForEstimate
      })
    });

    const data = await res.json();
    if (data.success) {
      collectedData = data.collected_data || {};

      // Eğer kullanıcı 'bilmiyorum' dediğinde tahmini cevap isteniyorsa
      if (data.ask_estimate) {
        askedForEstimate = true;
        setTimeout(() => {
          appendBotMessage(data.reply);
        }, 300);
        return;
      }

      askedForEstimate = false;

      // Atlandı / 'uzmanla görüşülecek' bilgilendirmesi
      if (data.notice) {
        appendBotMessage(data.notice);
      }

      if (data.next_question) {
        setTimeout(() => {
          displayQuestion(data.next_question);
        }, 400);
      } else if (data.reply && !data.is_complete) {
        // İl doğrulaması tekrarı veya anlamsız mesaj uyarısı
        setTimeout(() => {
          appendBotMessage(data.reply);
        }, 300);
      } else if (data.is_complete) {
        // Sorular tamamlandı -> Uygun Saatler
        setTimeout(() => {
          renderSlotSelection(data.available_slots || []);
        }, 400);
      }
    }
  } catch (err) {
    console.error(err);
  }
}

// 5. ADIM: GÖRSEL YÜKLEME VE EK TALEPLER (Madde 11)
function renderMediaUploadStep() {
  const container = document.createElement("div");
  container.className = "options-container";
  container.id = "mediaUploadStepContainer";
  updateMediaUploadUI(container);
  
  const chatBody = document.getElementById("chatMessages");
  chatBody.appendChild(container);
  chatBody.scrollTop = chatBody.scrollHeight;
  document.getElementById("chatInput").focus();
}

function updateMediaUploadUI(container) {
  if (!container) {
    container = document.getElementById("mediaUploadStepContainer");
  }
  if (!container) return;

  const count = uploadedImages.length;
  let html = `
    <div class="media-upload-container">
      <p style="font-size:0.8rem; color:var(--color-text-muted); margin-bottom:10px;">
        Desteklenen: JPG, PNG, WEBP (Maksimum 3 görsel, dosya başı 5MB)
      </p>

      <div style="display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-bottom:10px;">
        <button class="opt-btn" onclick="document.getElementById('imageFileInput').click()">
          <i class="fa-solid fa-cloud-arrow-up" style="color:var(--color-primary);"></i> ${count > 0 ? '+ Daha Fazla Görsel Ekle' : 'Görsel Seç & Yükle'}
        </button>
        ${count === 0 ? `
          <button class="opt-btn" onclick="handleUserAnswer('Özel bir ek talep veya görselim yok.')">
            Görsel Paylaşmadan Devam Et
          </button>
        ` : ''}
      </div>

      <div class="upload-thumbnails" id="thumbContainer">
        ${uploadedImages.map(img => `
          <div class="thumb-preview">
            <img src="${img.url}" alt="Önizleme">
            <button class="remove-thumb" onclick="removeImage('${img.url}')" title="Kaldır">&times;</button>
          </div>
        `).join("")}
      </div>
      <div id="uploadStatusText" style="font-size:0.78rem; color:var(--color-primary); margin-top:6px; display:none;">
        <i class="fa-solid fa-spinner fa-spin"></i> Görseller yükleniyor...
      </div>

      ${count > 0 ? `
        <button class="btn-primary-action" style="margin-top:12px;" onclick="submitMediaStep()">
          <i class="fa-solid fa-check"></i> Yüklenen ${count} Görsel ile Devam Et
        </button>
        <p style="font-size:0.75rem; color:var(--color-text-muted); margin-top:8px; font-style:italic;">
          <i class="fa-solid fa-pen"></i> Ayrıca eklemek istediğiniz bir not varsa aşağıya yazarak da gönderebilirsiniz.
        </p>
      ` : `
        <p style="font-size:0.75rem; color:var(--color-text-muted); margin-top:8px; font-style:italic;">
          <i class="fa-solid fa-pen"></i> Ek taleplerinizi veya açıklamalarınızı aşağıya yazarak da belirtebilirsiniz.
        </p>
      `}
    </div>
  `;
  container.innerHTML = html;
}

async function handleImageSelected(event) {
  const files = Array.from(event.target.files || []);
  if (files.length === 0) return;

  const statusEl = document.getElementById("uploadStatusText");
  if (statusEl) statusEl.style.display = "block";

  for (const file of files) {
    if (uploadedImages.length >= 3) {
      alert("En fazla 3 görsel yükleyebilirsiniz.");
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
        alert(data.error || "Görsel yüklenemedi.");
      }
    } catch (err) {
      alert("Yükleme sırasında hata oluştu.");
    }
  }

  event.target.value = "";
  if (statusEl) statusEl.style.display = "none";
  updateMediaUploadUI();
}

async function removeImage(url) {
  await fetch("/api/session/remove-image", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_token: sessionToken, image_url: url })
  });
  uploadedImages = uploadedImages.filter(i => i.url !== url);
  updateMediaUploadUI();
}

function submitMediaStep() {
  const count = uploadedImages.length;
  const msg = count > 0 
    ? `${count} adet örnek görsel yükledim.` 
    : "Özel bir ek talep veya görselim yok.";
  handleUserAnswer(msg);
}

// 6. ADIM: UYGUN GÖRÜŞME SAATLERİ (Madde 12)
function renderSlotSelection(slots, showMsg = true) {
  if (showMsg) {
    appendBotMessage("Seçtiğiniz uzmanın sistemde tanımlı uygun görüşme saatleri aşağıdadır:");
  }

  let slotsHtml = `<div class="slot-chips-grid">`;
  if (slots && slots.length > 0) {
    slots.forEach(slot => {
      const label = `${slot.slot_date} • ${slot.slot_time}`;
      const isActive = selectedSlotId === slot.id ? ' active' : '';
      slotsHtml += `
        <div class="slot-btn${isActive}" onclick="handleSlotSelect(${slot.id}, '${label}', this)">
          <i class="fa-regular fa-clock"></i> ${label}
        </div>
      `;
    });
  } else {
    slotsHtml += `<p style="grid-column: span 2; font-size:0.8rem; color:var(--color-text-muted);">Şu an uygun saat bulunamadı. Mimarla iletişimde saat netleştirilecektir.</p>`;
  }
  slotsHtml += `</div>`;

  appendBotOptions(slotsHtml);
}

async function handleSlotSelect(slotId, slotLabel, element) {
  document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('active'));
  element.classList.add('active');
  selectedSlotId = slotId;
  selectedSlotText = slotLabel;

  await fetch("/api/session/select-slot", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_token: sessionToken, slot_id: slotId, slot_text: slotLabel })
  });

  appendUserMessage(`Görüşme Saati: ${slotLabel}`);

  setTimeout(() => {
    appendBotMessage("<em>Not: Seçtiğiniz görüşme saati, mimarın/ofisin teyidine sunulacaktır.</em>");
    setTimeout(() => {
      renderBriefSummary();
    }, 400);
  }, 300);
}

// 7. ADIM: ÖN GÖRÜŞME BRİFİ ÖZETİ (Madde 14 & 15)
function renderBriefSummary(showMsg = true) {
  if (showMsg) {
    appendBotMessage("İşte verdiğiniz bilgilere göre hazırlanan <strong>Ön Görüşme Brif Özeti</strong>:");
  }


  const expName = selectedExpert ? selectedExpert.name : (selectedOffice ? selectedOffice.name : "Belirtilmedi");
  const serviceTitle = getServiceTitle(currentService);

  let summaryHtml = `
    <div class="summary-box">
      <div class="summary-row"><span>Uzman / Ofis:</span><strong>${escapeHtml(expName)}</strong></div>
      <div class="summary-row"><span>Hizmet Alanı:</span><strong>${serviceTitle}</strong></div>
      <div class="summary-row"><span>Konum:</span><strong>${collectedData.konum || 'Belirtilmedi'}</strong></div>
      <div class="summary-row"><span>Alan / m²:</span><strong>${collectedData.yaklasik_alan || 'Belirtilmedi'}</strong></div>
      <div class="summary-row"><span>Kullanım Amacı:</span><strong>${collectedData.kullanim_amaci || collectedData.mekan_turu || collectedData.acik_alan_turu || 'Belirtilmedi'}</strong></div>
      <div class="summary-row"><span>Bütçe Aralığı:</span><strong>${collectedData.butce_araligi || 'Belirtilmedi'}</strong></div>
      <div class="summary-row"><span>Hedef Zaman:</span><strong>${collectedData.hedef_zaman || 'Belirtilmedi'}</strong></div>
      <div class="summary-row"><span>Talep Saati:</span><strong>${selectedSlotText || 'Serbest Saat'}</strong></div>
      ${uploadedImages.length > 0 ? `<div class="summary-row"><span>Referans Görseller:</span><strong>${uploadedImages.length} adet yüklendi</strong></div>` : ''}
    </div>

    <!-- ONAY VE DÜZELTME BUTONLARI -->
    <button class="btn-primary-action" onclick="handleApproveBrief()">
      <i class="fa-solid fa-check"></i> Bilgilerimi Onaylıyorum
    </button>
    <button class="btn-secondary-action" onclick="handleRequestCorrection()">
      <i class="fa-solid fa-pen-to-square"></i> Düzeltmek İstiyorum
    </button>
  `;

  appendBotOptions(summaryHtml);
}

function handleRequestCorrection() {
  appendUserMessage("Bilgilerimde düzeltme yapmak istiyorum.");

  setTimeout(() => {
    appendBotMessage("Hangi bilgiyi güncellemek istersiniz?");
    const editFieldsHtml = `
      <div class="options-chips">
        <button class="opt-btn" onclick="editSpecificField('konum', 'Projeniz hangi il ve ilçede bulunuyor?')">📍 Konumu Değiştir</button>
        <button class="opt-btn" onclick="editSpecificField('yaklasik_alan', 'Yaklaşık alan kaç metrekaredir?')">📐 Alanı Değiştir</button>
        <button class="opt-btn" onclick="editSpecificField('butce_araligi', 'Ayırmayı düşündüğünüz bütçe aralığı nedir?')">💰 Bütçeyi Değiştir</button>
        <button class="opt-btn" onclick="renderBriefSummary()">↩️ Özete Geri Dön</button>
      </div>
    `;
    appendBotOptions(editFieldsHtml);
  }, 300);
}

function editSpecificField(fieldKey, questionPrompt) {
  currentQuestion = { field: fieldKey, question: questionPrompt };
  appendBotMessage(questionPrompt);
}

// 8. ADIM: BRİFİ ONAYLAMA & WİX İLETİŞİM FORMUNA YÖNLENDİRME (Madde 16)
async function handleApproveBrief() {
  appendUserMessage("Bilgilerimi onaylıyorum.");

  try {
    const res = await fetch("/api/session/approve-brief", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_token: sessionToken })
    });

    const data = await res.json();
    if (data.success) {
      setTimeout(() => {
        appendBotMessage(data.message);

        const wixRedirectHtml = `
          <a href="${data.wix_contact_url}" target="_top" class="btn-primary-action" style="margin-top:14px; text-decoration:none;">
            <i class="fa-solid fa-arrow-up-right-from-square"></i> Ön Görüşme Formunu Tamamla
          </a>
          <p style="font-size:0.75rem; color:var(--color-text-muted); text-align:center; margin-top:8px;">
            * Ön görüşme özetinizi onayladınız. Lütfen ön görüşme formuna geçerek süreci tamamlayın.
          </p>
        `;
        appendBotOptions(wixRedirectHtml);
      }, 400);
    }
  } catch (err) {
    console.error(err);
  }
}

// --- YARDIMCI FONKSİYONLAR ---

function appendBotMessage(text) {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "chat-row bot";
  div.innerHTML = `
    <div class="avatar-tiny"><i class="fa-solid fa-sparkles"></i></div>
    <div class="bubble"><p>${text.replace(/\n/g, '<br>')}</p></div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendBotOptions(htmlContent) {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "chat-row bot";
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

function getProfessionalsData() {
  try {
    const script = document.getElementById("professionalsData");
    return script ? JSON.parse(script.textContent) : { experts: [], offices: [] };
  } catch (e) {
    return { experts: [], offices: [] };
  }
}

function getServiceTitle(key) {
  const map = { "mimari": "Mimari Tasarım", "ic_mimari": "İç Mimarlık", "peyzaj": "Peyzaj Tasarımı" };
  return map[key] || "Mimari Tasarım";
}

function getServiceIcon(key) {
  const map = {
    "mimari": '<i class="fa-solid fa-compass-drafting" style="color:var(--color-primary);"></i>',
    "ic_mimari": '<i class="fa-solid fa-couch" style="color:var(--color-primary);"></i>',
    "peyzaj": '<i class="fa-solid fa-tree" style="color:var(--color-primary);"></i>'
  };
  return map[key] || '';
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
  if (!str) return "";
  return str.replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[m]);
}
