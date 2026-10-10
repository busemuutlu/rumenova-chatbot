(function () {
  // RUMENOVA NOVA FLOATING CHATBOT WIDGET (PDF Madde 1 & 2)
  const SERVER_URL = (function() {
    const scripts = document.getElementsByTagName('script');
    for (let s of scripts) {
      if (s.src && s.src.includes('/static/widget.js')) {
        return s.src.replace('/static/widget.js', '');
      }
    }
    return window.location.origin;
  })();

  // PDF Renkleri: Ana Vurgu #5A2027
  const style = document.createElement('style');
  style.innerHTML = `
    #rumenova-widget-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: #5A2027;
      color: #FAF9F7;
      box-shadow: 0 10px 28px rgba(90, 32, 39, 0.35), 0 2px 8px rgba(0,0,0,0.15);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      z-index: 999999;
      transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      border: 2px solid #FAF9F7;
    }
    #rumenova-widget-btn:hover {
      transform: scale(1.08) translateY(-3px);
      box-shadow: 0 14px 34px rgba(90, 32, 39, 0.5);
    }
    #rumenova-chat-frame {
      position: fixed;
      bottom: 96px;
      right: 24px;
      width: 420px;
      height: 520px;
      max-width: calc(100vw - 32px);
      max-height: calc(100vh - 120px);
      border: 1px solid #D9D5D0;
      border-radius: 20px;
      box-shadow: 0 20px 50px rgba(41, 34, 34, 0.25);
      z-index: 999998;
      display: none;
      background: #FAF9F7;
      overflow: hidden;
      transition: all 0.3s ease;
    }
    #rumenova-chat-frame.active {
      display: block;
      animation: rumenovaSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes rumenovaSlideUp {
      from { opacity: 0; transform: translateY(20px) scale(0.96); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
  `;
  document.head.appendChild(style);

  const ICON_SVG = `<svg style="width:28px;height:28px;fill:#FAF9F7;display:block;" viewBox="20 19.999 160 160.001"><g><path d="M23.061 95.603c-4.081 1.51-4.081 7.283 0 8.793l21.009 7.775a74.07 74.07 0 0 1 43.759 43.759l7.775 21.009c1.51 4.081 7.283 4.081 8.793 0l7.775-21.009a74.07 74.07 0 0 1 43.759-43.759l21.009-7.775c4.081-1.51 4.081-7.283 0-8.793l-21.009-7.775a74.07 74.07 0 0 1-43.759-43.759l-7.775-21.009c-1.511-4.081-7.283-4.081-8.793 0l-7.775 21.009A74.07 74.07 0 0 1 44.07 87.828z"></path></g></svg>`;
  const CLOSE_SVG = `<span style="font-size:24px;line-height:1;font-family:sans-serif;color:#FAF9F7;">✕</span>`;

  // Wix / Site hafızasından kayıtlı oturum token'ı ve açık/kapalı durumunu oku
  const savedToken = localStorage.getItem('rumenova_session_token') || '';
  const wasOpen = localStorage.getItem('rumenova_chat_open') === 'true';

  // Widget Butonu
  const btn = document.createElement('div');
  btn.id = 'rumenova-widget-btn';
  btn.title = 'Nova ile Ön Görüşme Başlat';
  btn.innerHTML = `<span id="rumenova-btn-icon">${wasOpen ? CLOSE_SVG : ICON_SVG}</span>`;
  document.body.appendChild(btn);

  // Iframe Penceresi (Token parametresi ile yüklenir, böylece sayfa geçişinde konuşma asla kaybolmaz)
  const iframe = document.createElement('iframe');
  iframe.id = 'rumenova-chat-frame';
  const iframeUrl = new URL(SERVER_URL + '/');
  if (savedToken) {
    iframeUrl.searchParams.set('session_token', savedToken);
  }
  iframe.src = iframeUrl.toString();
  if (wasOpen) {
    iframe.classList.add('active');
  }
  document.body.appendChild(iframe);

  // Açma / Kapatma (Görüşme sıfırlanmaz!)
  let isOpen = wasOpen;
  btn.addEventListener('click', function () {
    isOpen = !isOpen;
    localStorage.setItem('rumenova_chat_open', isOpen ? 'true' : 'false');
    if (isOpen) {
      iframe.classList.add('active');
      document.getElementById('rumenova-btn-icon').innerHTML = CLOSE_SVG;
    } else {
      iframe.classList.remove('active');
      document.getElementById('rumenova-btn-icon').innerHTML = ICON_SVG;
    }
  });

  // Dışarıdan veya içeriden kapatma ve senkronizasyon mesajları
  window.addEventListener('message', function(e) {
    if (e.data === 'close-rumenova-chat') {
      isOpen = false;
      localStorage.setItem('rumenova_chat_open', 'false');
      iframe.classList.remove('active');
      document.getElementById('rumenova-btn-icon').innerHTML = ICON_SVG;
    }
    if (e.data && e.data.type === 'rumenova-session-sync' && e.data.sessionToken) {
      localStorage.setItem('rumenova_session_token', e.data.sessionToken);
    }
    if (e.data && e.data.type === 'rumenova-session-reset') {
      localStorage.removeItem('rumenova_session_token');
    }
  });
})();
