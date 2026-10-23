// ==========================================================================
// RUMENOVA - WIX BACKEND WEB MODÜLÜ
// Wix'te yeri: Code Files -> Backend -> rumenova-service.web.js
// ==========================================================================
// Ön görüşme formu verisi SADECE Flask API'ye gönderilir.
// Wix CMS / dataset / wixData KULLANILMAZ.
// ==========================================================================

import { Permissions, webMethod } from 'wix-web-module';
import { fetch } from 'wix-fetch';

// Render üzerinde canlıda çalışan API adresi
const API_BASE_URL = "https://rumenova-chatbot.onrender.com";

/**
 * Ön görüşme formunu backend'e gönderir.
 * Chatbot oturumu (session_token) varsa kayıt o oturumun brifiyle birleşir,
 * yoksa backend yeni bir talep olarak kaydeder.
 */
export const submitOnGorusmeForm = webMethod(Permissions.Anyone, async (formData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/wix/complete-form`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_token: formData.session_token || "",
        ad: formData.ad,
        soyad: formData.soyad,
        email: formData.email,
        phone: formData.phone || "",
        note: formData.note || ""
      })
    });

    const data = await response.json();
    return { ...data, httpStatus: response.status };
  } catch (error) {
    console.error("Rumenova API hatası:", error);
    return {
      success: false,
      error: "network_error",
      message: "Şu anda sunucuya ulaşılamıyor. Lütfen birkaç dakika sonra tekrar deneyin."
    };
  }
});

/**
 * Ön Görüşme Yönetim Paneli: tamamlanmış talepleri backend'den getirir.
 * Dönen alanlar eski Wix koleksiyonuyla aynıdır (ad, soyad, hizmetAlan, durum, projeBrifi...).
 */
export const getOnGorusmeler = webMethod(Permissions.Anyone, async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/panel/on-gorusmeler`, { method: 'GET' });
    return await response.json();
  } catch (error) {
    console.error("Rumenova panel listesi alınamadı:", error);
    return { success: false, items: [], error: "network_error" };
  }
});

/**
 * Ön Görüşme Detayı sayfası: tek talebi backend'den getirir.
 */
export const getOnGorusme = webMethod(Permissions.Anyone, async (id) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/panel/on-gorusmeler/${encodeURIComponent(id)}`, { method: 'GET' });
    return await response.json();
  } catch (error) {
    console.error("Rumenova talep detayı alınamadı:", error);
    return { success: false, error: "network_error" };
  }
});
