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
