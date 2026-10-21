import os
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle
load_dotenv()

class Config:
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "rumenova-super-secret-key-2026")
    DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "rumenova.db"))
    DATABASE_URL = os.getenv("DATABASE_URL", DATABASE_PATH)
    
    # Yapay Zeka Sağlayıcı Ayarları (Groq, OpenAI, Gemini veya Mock)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "groq" if os.getenv("GROQ_API_KEY") else "mock")
    
    # CORS İzinleri
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    
    # Nova Asistan Sistem Talimatı (Business Context)
    BUSINESS_CONTEXT = """
Sen Rumenova platformunun yapay zekâ destekli ön görüşme asistanı **Nova**'sın.
Rumenova bir mimarlık ofisi değil, kariyerinin başındaki mimarlar, iç mimarlar, peyzaj mimarları ve küçük mimarlık ofisleri için müşteri ön görüşmesini düzenleyen profesyonel bir dijital sistemdir.

GÖREV VE SINIRLARIN (ÇOK ÖNEMLİ):
1. Görevin müşterinin mimari tasarım, iç mimarlık veya peyzaj ihtiyaçlarını toplamak ve mimarın inceleyeceği standart bir ön brife dönüştürmektir.
2. ASLA proje üretme, teknik/statik karar verme, kesin maliyet veya kesin süre taahhüdünde bulunma!
3. Kullanıcının söylediği bilgileri dikkate al; daha önce cevaplanan soruları ASLA tekrar sorma (Örn: "Üç katlı, bahçeli ev istiyorum" dediyse kat sayısı veya bahçe sorma, eksik bilgileri anlaşılır sorularla tamamla).
4. Randevu özelliği varsa yalnızca sistemdeki tanımlı uygun saatleri göster; müşteri seçiminin mimarın teyidine tabi olduğunu belirt.
5. Bilinmeyen veya kullanıcının bilmediği noktaları zorlama, tahmini belirtmesini iste veya uzmanla görüşülecek şekilde not al.
6. İletişim tarzın samimi, güven veren, modern ve mimari estetiğe değer veren profesyonel bir tonda olmalıdır.
"""
    NOVA_SYSTEM_PROMPT = BUSINESS_CONTEXT

    # --- Kullanıcıya gösterilen sabit mesajlar (tek yerden yönetilir) ---
    # Direktif (BUSINESS_CONTEXT madde 4): randevu, uzmanın teyidine tabidir.
    # Metinler .env üzerinden de geçersiz kılınabilir.
    MSG_BRIEF_APPROVED = os.getenv(
        "MSG_BRIEF_APPROVED",
        "Ön görüşme özetinizi onayladınız. Bilgilerinizin seçtiğiniz mimara/ofise iletilebilmesi için "
        "iletişim formunu tamamlayın. Seçtiğiniz görüşme saati, mimarın/ofisin teyidine tabidir."
    )
    MSG_FORM_COMPLETED_WITH_SLOT = os.getenv(
        "MSG_FORM_COMPLETED_WITH_SLOT",
        "Bizi tercih ettiğiniz için teşekkür ederiz. Ön görüşme bilgileriniz seçtiğiniz mimara/ofise iletildi. "
        "Seçtiğiniz saat sizin için ayrıldı; görüşme saati uzmanın teyidine tabidir."
    )
    MSG_FORM_COMPLETED_NO_SLOT = os.getenv(
        "MSG_FORM_COMPLETED_NO_SLOT",
        "Bizi tercih ettiğiniz için teşekkür ederiz. Ön görüşme bilgileriniz seçtiğiniz mimara/ofise iletildi. "
        "Bir görüşme saati seçilmediği için uzman sizinle iletişime geçerek uygun bir saat belirleyecektir."
    )
    MSG_SLOT_UNAVAILABLE = os.getenv(
        "MSG_SLOT_UNAVAILABLE",
        "Seçtiğiniz görüşme saati artık uygun değil. Lütfen listeden başka bir saat seçip formu tekrar gönderin."
    )
    MSG_ESTIMATE_REQUEST = os.getenv(
        "MSG_ESTIMATE_REQUEST", "Anladım, yaklaşık veya tahmini olarak belirtiniz."
    )
    MSG_ESTIMATE_NOTED = os.getenv(
        "MSG_ESTIMATE_NOTED", "Sorun değil, bu noktayı uzmanla görüşülmek üzere not aldım."
    )
    MSG_SKIPPED = os.getenv("MSG_SKIPPED", "Tamam, bu soruyu atlıyorum.")
    # Uzmanla görüşülecek (bilinmeyen) alanlar için brife yazılan değer
    VALUE_TO_DISCUSS = os.getenv("VALUE_TO_DISCUSS", "Bilinmiyor – uzmanla görüşülecek")
