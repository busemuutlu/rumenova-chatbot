import json
import re
from config import Config

# PDF MADDE 8, 9, 10 BİREBİR SORU SETLERİ
QUESTION_POOLS = {
    "mimari": [
        {
            "id": "m_tur",
            "question": "Yeni yapı, yenileme veya restorasyon mu düşünüyorsunuz?",
            "field": "proje_turu",
            "choices": ["Yeni Yapı", "Yenileme", "Restorasyon"]
        },
        {
            "id": "m_konum",
            "question": "Projeniz hangi il ve ilçede?",
            "field": "konum"
        },
        {
            "id": "m_amac",
            "question": "Yapının kullanım amacı nedir?",
            "field": "kullanim_amaci",
            "choices": ["Konut", "Villa", "Ticari Yapı", "Ofis"]
        },
        {
            "id": "m_alan",
            "question": "Yapının yaklaşık alanı nedir?",
            "field": "yaklasik_alan"
        },
        {
            "id": "m_kat_yeni",
            "question": "Yeni yapıda kaç kat düşünüyorsunuz?",
            "field": "kat_sayisi",
            "condition": lambda data: "yeni" in str(data.get("proje_turu", "")).lower() or not data.get("proje_turu"),
            "choices": ["Tek Katlı", "2 Katlı (Dubleks)", "3 Katlı (Tripleks)"]
        },
        {
            "id": "m_kat_mevcut",
            "question": "Mevcut yapınız kaç katlı?",
            "field": "mevcut_kat_sayisi",
            "condition": lambda data: "yenileme" in str(data.get("proje_turu", "")).lower() or "restorasyon" in str(data.get("proje_turu", "")).lower(),
            "choices": ["1 Kat", "2 Kat", "3 Kat ve üzeri"]
        },
        {
            "id": "m_odalar",
            "question": "Hangi odalara ve kullanım alanlarına ihtiyaç duyuyorsunuz?",
            "field": "mekansal_ihtiyaclar"
        },
        {
            "id": "m_tarz",
            "question": "Nasıl bir mimari tarz düşünüyorsunuz?",
            "field": "mimari_tarz",
            "choices": ["Modern & Minimalist", "Doğal & Akdeniz Tarzı", "Geleneksel / Taş Yapı"]
        },
        {
            "id": "m_malzeme",
            "question": "Tercih ettiğiniz malzeme ve renkler nelerdir?",
            "field": "malzeme_renk"
        },
        {
            "id": "m_korunacak",
            "question": "Mevcut yapıda korunmasını istediğiniz özellikler nelerdir?",
            "field": "korunacak_ozellikler",
            "condition": lambda data: "yenileme" in str(data.get("proje_turu", "")).lower() or "restorasyon" in str(data.get("proje_turu", "")).lower()
        },
        {
            "id": "m_ek_talep",
            "question": "Havuz, teras, balkon veya otopark gibi ek talepleriniz var mı?",
            "field": "ek_talepler",
            "allow_negative": True,
            "choices": ["Havuz", "Teras / Veranda", "Balkon", "Kapalı Otopark"]
        },
        {
            "id": "m_butce",
            "question": "Ayırmayı düşündüğünüz bütçe aralığı nedir?",
            "field": "butce_araligi"
        },
        {
            "id": "m_zaman",
            "question": "Başlangıç ve tamamlanma zamanı için beklentiniz nedir?",
            "field": "hedef_zaman",
            "choices": ["En kısa sürede", "3-6 ay içinde", "Önümüzdeki yıl"]
        },
        {
            "id": "m_gorsel",
            "question": "Paylaşmak istediğiniz örnek görseller veya başka talepler var mı?",
            "field": "gorsel_ve_ek",
            "type": "media_and_notes"
        }
    ],

    "ic_mimari": [
        {
            "id": "ic_tur",
            "question": "Ev, iş yeri veya başka bir mekân mı düzenlemek istiyorsunuz?",
            "field": "mekan_turu",
            "choices": ["Ev / Konut", "İş Yeri / Ofis", "Kafe / Mağaza"]
        },
        {
            "id": "ic_konum",
            "question": "Mekânınız hangi il ve ilçede?",
            "field": "konum"
        },
        {
            "id": "ic_alan",
            "question": "Düzenlenecek alan yaklaşık kaç metrekare?",
            "field": "yaklasik_alan"
        },
        {
            "id": "ic_odalar",
            "question": "Hangi odalarda veya bölümlerde değişiklik istiyorsunuz?",
            "field": "degisecek_bolumler",
            "choices": ["Tüm Ev / Mekan", "Sadece Salon & Mutfak", "Banyo & Yatak Odası"]
        },
        {
            "id": "ic_zorluk",
            "question": "Mevcut düzende sizi zorlayan noktalar neler?",
            "field": "mevcut_zorluklar",
            "choices": ["Yetersiz Depolama", "Aydınlatma / Işık Eksikliği", "Kullanışsız Yerleşim"]
        },
        {
            "id": "ic_kisi",
            "question": "Mekânı kaç kişi kullanıyor?",
            "field": "kullanici_sayisi",
            "choices": ["1-2 Kişi", "3-4 Kişi (Aile)", "Geniş Ekip"]
        },
        {
            "id": "ic_oncelik",
            "question": "Hangi ihtiyaçlara öncelik veriyorsunuz?",
            "field": "oncelikler",
            "choices": ["Ferahlık & Açıklık", "Depolama Kapasitesi", "Şıklık & Prestij", "Fonksiyonellik"]
        },
        {
            "id": "ic_tarz",
            "question": "Nasıl bir tarz düşünüyorsunuz?",
            "field": "tarz",
            "choices": ["Modern & Minimalist", "İskandinav / Japandi", "Klasik / Neoklasik"]
        },
        {
            "id": "ic_malzeme",
            "question": "Tercih ettiğiniz malzeme ve renkler nelerdir?",
            "field": "malzeme_renk"
        },
        {
            "id": "ic_mobilya",
            "question": "Korunmasını istediğiniz mobilyalar ve eşyalar var mı?",
            "field": "korunacak_mobilyalar",
            "allow_negative": True,
            "choices": ["Tüm eşyalar sıfırdan seçilecek", "Bazı mobilyalar korunacak"]
        },
        {
            "id": "ic_depolama",
            "question": "Depolama, aydınlatma veya yerleşim konusunda beklentileriniz neler?",
            "field": "aydinlatma_depolama",
            "choices": ["Gizli Led Aydınlatma", "Gömme Dolap & Depolama", "Özel Yerleşim Planı"]
        },
        {
            "id": "ic_butce",
            "question": "Ayırmayı düşündüğünüz bütçe aralığı nedir?",
            "field": "butce_araligi"
        },
        {
            "id": "ic_zaman",
            "question": "Başlangıç ve tamamlanma zamanı için beklentiniz nedir?",
            "field": "hedef_zaman",
            "choices": ["Hemen başlamak istiyorum", "1-2 ay içinde", "Tarih esnek"]
        },
        {
            "id": "ic_gorsel",
            "question": "Paylaşmak istediğiniz örnek görseller veya başka talepler var mı?",
            "field": "gorsel_ve_ek",
            "type": "media_and_notes"
        }
    ],

    "peyzaj": [
        {
            "id": "p_tur",
            "question": "Bahçe, teras, park veya başka bir açık alan mı düzenlemek istiyorsunuz?",
            "field": "acik_alan_turu",
            "choices": ["Villa Bahçesi", "Çatı / Kat Terası", "Site Ortak Alanı", "Park"]
        },
        {
            "id": "p_konum",
            "question": "Alanınız hangi il ve ilçede?",
            "field": "konum"
        },
        {
            "id": "p_alan",
            "question": "Düzenlenecek alan yaklaşık kaç metrekare?",
            "field": "yaklasik_alan"
        },
        {
            "id": "p_durum",
            "question": "Alanın mevcut durumu nedir?",
            "field": "mevcut_durum",
            "choices": ["Boş Toprak / Ham Arazi", "Eski Bakımsız Bahçe", "Yeni Yapı Çevresi"]
        },
        {
            "id": "p_egim",
            "question": "Düzenlenmesini istediğiniz açık alanda eğim veya belirgin bir kot farkı var mı?",
            "field": "egim_kot",
            "choices": ["Düz Arazi", "Hafif Eğimli", "Kademeli / Belirgin Kot Farkı Var"]
        },
        {
            "id": "p_kullanim",
            "question": "Alanı kimler, hangi amaçlarla kullanacak?",
            "field": "kullanim_amaci",
            "choices": ["Ailece Dinlenme", "Çocuk ve Evcil Hayvan", "Yemek & Davetler"]
        },
        {
            "id": "p_korunacak",
            "question": "Korunmasını istediğiniz ağaçlar, bitkiler veya mevcut öğeler var mı?",
            "field": "korunacak_bitkiler",
            "allow_negative": True,
            "choices": ["Mevcut yetişkin ağaçlar korunsun", "Tamamen sıfırdan planlansın"]
        },
        {
            "id": "p_tarz",
            "question": "Nasıl bir peyzaj tarzı düşünüyorsunuz?",
            "field": "peyzaj_tarzi",
            "choices": ["Doğal & Akdeniz Tarzı", "Modern & Minimalist", "Tropikal & Yoğun Yeşil"]
        },
        {
            "id": "p_malzeme",
            "question": "Tercih ettiğiniz bitkiler, renkler ve zemin malzemeleri nelerdir?",
            "field": "zemin_ve_bitki",
            "choices": ["Ahşap Deck & Çim", "Doğal Taş Yürüyüş Yolları"]
        },
        {
            "id": "p_talepler",
            "question": "Oturma, oyun, spor veya yürüyüş alanı gibi talepleriniz var mı?",
            "field": "yapisal_talepler",
            "allow_negative": True,
            "choices": ["Oturma & Dinlenme Alanı", "Pergola / Kamelya", "Çocuk Oyun Alanı", "Ateş Çukuru & Barbekü"]
        },
        {
            "id": "p_golge",
            "question": "Gölgelendirme, mahremiyet veya dış aydınlatma beklentiniz var mıdır?",
            "field": "aydinlatma_mahremiyet",
            "allow_negative": True,
            "choices": ["Mahremiyet Çiti", "Dış Mekan Aydınlatması", "Otomatik Sulama"]
        },
        {
            "id": "p_bakim",
            "question": "Bahçenin bakımı için ne kadar zaman ayırabilirsiniz?",
            "field": "bakim_zamani",
            "choices": ["Kolay Bakımlı (Az Zaman)", "Haftada Birkaç Saat", "Profesyonel Bahçıvan Bakacak"]
        },
        {
            "id": "p_butce",
            "question": "Ayırmayı düşündüğünüz bütçe aralığı nedir?",
            "field": "butce_araligi"
        },
        {
            "id": "p_zaman",
            "question": "Başlangıç ve tamamlanma zamanı için beklentiniz nedir?",
            "field": "hedef_zaman",
            "choices": ["En kısa sürede bu sezon", "Önümüzdeki bahar", "Tarih esnek"]
        },
        {
            "id": "p_gorsel",
            "question": "Paylaşmak istediğiniz örnek görseller veya başka talepler var mı?",
            "field": "gorsel_ve_ek",
            "type": "media_and_notes"
        }
    ]
}

# Kapsamlı if alanları ve 81 il sözlüğü şu anlık devre dışı bırakılmıştır.
# Sadece temel koşullar ve chatbot alanı aktif tutulmuştur.

class AIService:
    @classmethod
    def is_gibberish_or_irrelevant(cls, text):
        """Kapsamlı saçma/anlamsız metin kontrolleri şu anlık devre dışı."""
        if not text or not str(text).strip():
            return True
        return False

    @classmethod
    def check_if_uncertain_answer(cls, text):
        """Belli başlı temel belirsizlik ('bilmiyorum' vb.) kontrolü."""
        if not text:
            return False
        t = str(text).lower().strip()
        uncertain_words = ["bilmiyorum", "emin degilim", "emin değilim", "fikrim yok", "kararsizim", "kararsızım"]
        return any(w in t for w in uncertain_words)

    @classmethod
    def find_turkey_province_and_district(cls, text):
        """Kapsamlı il/ilçe doğrulama devre dışı; girilen konumu doğrudan kabul eder."""
        if not text or not str(text).strip():
            return None, None
        return str(text).strip(), None

    @classmethod
    def extract_info_from_message(cls, text, current_data):
        """Kapsamlı if çıkarımları şu anlık devre dışı; doğrudan cevaplar toplanır."""
        return {}

    @classmethod
    def get_question_by_field(cls, service_type, field):
        """Alan adına göre soru tanımını döner."""
        pool = QUESTION_POOLS.get(service_type, QUESTION_POOLS["mimari"])
        for q in pool:
            if q.get("field") == field:
                return q
        return None

    @classmethod
    def get_valid_fields(cls, service_type):
        """Hizmet alanının soru havuzundaki geçerli alan adları."""
        pool = QUESTION_POOLS.get(service_type, QUESTION_POOLS["mimari"])
        return {q["field"] for q in pool}

    @classmethod
    def is_plain_negative(cls, text):
        """Temel olumsuz cevap kontrolü (hayır / yok)."""
        if not text:
            return False
        return str(text).lower().strip() in ["hayir", "hayır", "yok", "yoktur"]

    @classmethod
    def get_next_question(cls, service_type, collected_data, skipped_fields=None):
        """Bir sonraki soruyu belirler."""
        pool = QUESTION_POOLS.get(service_type, QUESTION_POOLS["mimari"])
        skipped = set(skipped_fields or [])

        for q in pool:
            field = q.get("field")
            if field in skipped:
                continue

            if field in collected_data and collected_data[field] and str(collected_data[field]).strip() != "":
                continue

            if "condition" in q and callable(q["condition"]):
                if not q["condition"](collected_data):
                    continue

            clean_q = {k: v for k, v in q.items() if k != "condition"}
            return clean_q

        return None

    def yanit_uret(self, mesaj, gecmis=None):
        """
        Nova Chatbot yanıt üretici.
        Groq API anahtarı varsa LLM ile yanıt üretir, yoksa temel koşullarla fallback yanıt döner.
        """
        if not mesaj or not str(mesaj).strip():
            return "Size nasıl yardımcı olabilirim?"

        if gecmis is None:
            gecmis = []

        # 1. Groq LLM Yanıt Üretimi
        if Config.GROQ_API_KEY:
            try:
                from groq import Groq
                client = Groq(api_key=Config.GROQ_API_KEY)
                messages = [{"role": "system", "content": Config.BUSINESS_CONTEXT}]
                for msg in gecmis:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ["user", "assistant"] and content:
                        messages.append({"role": role, "content": content})
                messages.append({"role": "user", "content": str(mesaj).strip()})

                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="openai/gpt-oss-120b",
                    temperature=0.6,
                    max_tokens=600
                )
                return chat_completion.choices[0].message.content.strip()
            except Exception:
                pass

        # 2. Temel Koşullar ve Fallback
        t_lower = str(mesaj).lower().strip()
        if any(w in t_lower for w in ["merhaba", "selam", "günaydın", "iyi günler", "iyi aksamlar"]):
            return "Merhaba! Ben Rumenova Dijital Mimari Asistanı Nova. Size projenizde nasıl yardımcı olabilirim?"

        return "Projenizle ilgili detayları memnuniyetle dinlemek isterim. Size en uygun çözümü sunabilmemiz için ihtiyaçlarınızı paylaşabilirsiniz."

    def sorulari_ai_ile_yonet(self, mesaj, service_type="peyzaj", toplanan_bilgiler=None, gecmis=None):
        """
        Soruları yapay zekâya bağlar. 
        Yapay zekâ belirlenen soru listesini rehber alarak kullanıcıyla doğal 
        bir mimari diyalog kurar ve eksik kalan soruları sırayla sorar.
        """
        if not mesaj or not str(mesaj).strip():
            return "Size nasıl yardımcı olabilirim?"

        if gecmis is None:
            gecmis = []
        if toplanan_bilgiler is None:
            toplanan_bilgiler = {}

        # 1. Hizmete ait soru havuzunu hazırla
        soru_havuzu = QUESTION_POOLS.get(service_type, QUESTION_POOLS["mimari"])
        soru_maddeleri = "\n".join([f"- [{q.get('field')}]: {q.get('question')}" for q in soru_havuzu])

        # 2. Yapay Zekâ Yönergesi (Prompt)
        system_prompt = f"""Sen Rumenova Mimarlık'ın dijital asistanı Nova'sın.
Görevin: Kullanıcıdan seçtiği hizmet ({service_type}) için gerekli mimari/teknik bilgileri samimi, profesyonel ve doğal bir diyalog içerisinde toplamak.

Rehber Soru Listen:
{soru_maddeleri}

Şu ana kadar toplanmış bilgiler:
{json.dumps(toplanan_bilgiler, ensure_ascii=False, indent=2)}

DİYALOG KURALLARI:
1. Kullanıcıyı asla soru yağmuruna tutma. Her seferinde en fazla 1 (veya birbiriyle çok bağlantılı en çok 2) soru yönelt.
2. Kullanıcının son mesajındaki cevabını zarifçe karşıla veya mimari bir bakışla yorumla, ardından sıradaki eksik soruyu sor.
3. Kullanıcı "bilmiyorum", "kararsızım" veya "fark etmez" derse ısrar etme, bu konuyu uzman mimarla yapılacak görüşmeye not aldığını belirtip bir sonraki konuya geç.
4. Tüm temel bilgiler tamamlandığında görüşmeyi toparla ve kullanıcıyı uzman mimardan randevu almaya davet et.
"""

        # 3. Mesaj geçmişini derle
        messages = [{"role": "system", "content": system_prompt}]
        for msg in gecmis:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": str(mesaj).strip()})

        # 4. Groq LLM Çağrısı
        if Config.GROQ_API_KEY:
            try:
                from groq import Groq
                client = Groq(api_key=Config.GROQ_API_KEY)
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="openai/gpt-oss-120b",
                    temperature=0.7,
                    max_tokens=500
                )
                return chat_completion.choices[0].message.content.strip()
            except Exception as e:
                pass

        # Fallback (API anahtarı yoksa veya hata oluşursa)
        next_q = self.get_next_question(service_type, toplanan_bilgiler)
        if next_q:
            return f"Anladım, not aldım. Peki {next_q['question']}"
        return "Harika, projenizle ilgili tüm detayları not aldım. Dilerseniz uzman mimarımızla randevu oluşturabiliriz."

    @classmethod
    def is_free_question_or_command(cls, text):
        """
        Kullanıcının form akışı yerine doğrudan yapay zekaya bir soru sorduğunu
        veya komut (/ai, /sor, @nova vb.) kullandığını tespit eder.
        Döner: (bool, temizlenmiş_metin)
        """
        if not text:
            return False, ""
        t = str(text).strip()
        t_lower = t.lower()

        # 1. Özel Komut Kontrolü (/ai, /sor, /chat, /nova, @nova, nova:)
        cmd_prefixes = ["/ai", "/sor", "/chat", "/nova", "@nova", "nova:"]
        for p in cmd_prefixes:
            if t_lower.startswith(p):
                clean_query = t[len(p):].strip()
                return True, clean_query if clean_query else t

        # 2. Soru İşareti veya Doğrudan Soru Kalıpları
        question_words = [
            "nedir", "nasıl", "ne kadar", "kaç para", "fiyatı", "maliyeti", "ücreti",
            "tavsiye", "öneri", "önerir misin", "tavsiyen nedir", "fikrin nedir",
            "siz kimsiniz", "neredesiniz", "iletişim", "yardım edebilir misin",
            "ne düşünüyorsun", "hangi tarz", "hangisi daha iyi", "ne yapmalıyım",
            "mümkün mü", "olur mu", "yapabilir miyiz", "yapabilir misiniz",
            "bilgi almak istiyorum", "bir şey sorabilir miyim", "sorum var"
        ]

        has_question_mark = "?" in t
        has_question_word = any(qw in t_lower for qw in question_words)

        if has_question_mark or has_question_word:
            if len(t) >= 4 and t_lower not in ["evet?", "hayır?", "yok?", "tamam?"]:
                return True, t

        return False, ""

    def serbest_sohbet_yaniti(self, soru, mevcut_soru=None, service_type="mimari", gecmis=None):
        """
        Kullanıcı form dışı bir soru sorduğunda veya doğrudan yapay zekâya danıştığında
        uzman mimar asistanı gibi yanıt verir, ardından mevcut soruya nazikçe geri bağlar.
        """
        if not soru or not str(soru).strip():
            return "Size nasıl yardımcı olabilirim?"

        if gecmis is None:
            gecmis = []

        system_prompt = f"""Sen Rumenova Mimarlık'ın samimi, vizyoner ve profesyonel dijital asistanı Nova'sın.
Kullanıcı şu an bir ön görüşme formunda ilerlerken sana doğrudan bir soru sordu veya danıştı.

GÖREVİN:
1. Kullanıcının sorusuna bir mimar/iç mimar/peyzaj uzmanı gözüyle kısa, açıklayıcı, samimi ve profesyonel bir yanıt ver (en fazla 2-3 cümle).
2. Yanıtının sonuna kullanıcının projesine devam edebilmesi için şu cümleyi ekle:
{f'Bu arada projenize devam etmek isterseniz: "{mevcut_soru}"' if mevcut_soru else 'Projenizle ilgili başka merak ettiğiniz bir detay var mı?'}
"""

        messages = [{"role": "system", "content": system_prompt}]
        for msg in gecmis:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": str(soru).strip()})

        if Config.GROQ_API_KEY:
            try:
                from groq import Groq
                client = Groq(api_key=Config.GROQ_API_KEY)
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="openai/gpt-oss-120b",
                    temperature=0.7,
                    max_tokens=400
                )
                return chat_completion.choices[0].message.content.strip()
            except Exception:
                pass

        fallback_msg = "Mimari ve tasarım süreçlerimizde her detayı sizin konforunuz ve estetik beklentileriniz doğrultusunda titizlikle planlıyoruz."
        if mevcut_soru:
            fallback_msg += f" Dilerseniz projemize kaldığımız yerden devam edelim: {mevcut_soru}"
        return fallback_msg

    # --- Konuşma motoru (/api/chat) için yapay zekâ görevleri ---

    def _llm(self, messages, temperature=0.4, max_tokens=700, json_mode=False):
        """Groq çağrısı. Anahtar yoksa veya hata olursa None döner (çağıran kural tabanlı yedeğe geçer)."""
        if not Config.GROQ_API_KEY:
            return None
        try:
            from groq import Groq
            # Render (gunicorn) isteği 30 sn sonra keser; tek turda en fazla iki çağrı olabilir
            client = Groq(api_key=Config.GROQ_API_KEY, timeout=12.0, max_retries=0)
            kwargs = {
                "messages": messages,
                "model": "openai/gpt-oss-120b",
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            chat_completion = client.chat.completions.create(**kwargs)
            return (chat_completion.choices[0].message.content or "").strip() or None
        except Exception:
            return None

    @staticmethod
    def _parse_json(text):
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            match = re.search(r"\{.*\}", text, re.S)
            if match:
                try:
                    return json.loads(match.group(0))
                except ValueError:
                    return None
        return None

    @staticmethod
    def _field_catalog(service_type=None):
        """Yapay zekâya verilen alan listesi: 'alan_adi: soru' satırları."""
        services = [service_type] if service_type in QUESTION_POOLS else list(QUESTION_POOLS)
        lines, seen = [], set()
        for s in services:
            for q in QUESTION_POOLS[s]:
                field = q["field"]
                if field in seen or q.get("type") == "media_and_notes":
                    continue
                seen.add(field)
                choices = f" (seçenekler: {', '.join(q['choices'])})" if q.get("choices") else ""
                lines.append(f"- {field}: {q['question']}{choices}")
        return "\n".join(lines)

    @staticmethod
    def _history_for_llm(gecmis, limit=12):
        out = []
        for msg in (gecmis or [])[-limit:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in ["user", "assistant"] and content:
                out.append({"role": role, "content": str(content)})
        return out

    def sohbet_analizi(self, mesaj, gecmis=None, service_type=None, brif_tamamlandi=False, brif_ozeti=None):
        """
        Serbest sohbet aşaması: Nova'nın yanıtı + niyet tespiti.
        Döner: {"yanit": str, "proje_talebi": bool, "hizmet": str|None, "bilgiler": {alan: değer}}
        Yapay zekâ yoksa None döner.
        """
        if brif_tamamlandi:
            durum = (
                "Kullanıcının ön görüşme brifi tamamlandı ve onaylandı. Brif özeti:\n"
                f"{brif_ozeti or '-'}\n"
                "Kullanıcının sorularını yanıtla. Gerekirse ekrandaki 'Ön Görüşme Formunu Tamamla' "
                "bağlantısıyla iletişim formunu doldurmasını hatırlat. Yeni brif sorusu sorma; "
                "proje_talebi alanını false döndür."
            )
        else:
            durum = (
                "Şu an SERBEST SOHBET aşamasındasın. Kullanıcının sorularını kısaca yanıtla. "
                "Bu aşamada brif sorularını sen sorma: kullanıcı bir proje talebi belirttiğinde sistem ona "
                "ön görüşme brifi oluşturmayı ayrıca teklif edecek. proje_talebi true ise yanıtında soru sorma."
            )

        system_prompt = f"""{Config.BUSINESS_CONTEXT}

AŞAMA BİLGİSİ:
{durum}

ÇIKTI: Yalnızca şu JSON nesnesini döndür, başka metin yazma:
{{"yanit": "kullanıcıya gösterilecek kısa Türkçe yanıt", "proje_talebi": true/false, "hizmet": "mimari" | "ic_mimari" | "peyzaj" | null, "bilgiler": {{"alan_adi": "değer"}}}}

- proje_talebi: kullanıcı bir mimari / iç mimari / peyzaj projesi yaptırmak, tasarlatmak, yenilemek veya bir uzmanla ön görüşme yapmak istediğini belli ettiyse true.
- hizmet: talebin ait olduğu alan (mimari = yeni yapı / bina / restorasyon, ic_mimari = iç mekân düzenleme / tadilat / dekorasyon, peyzaj = bahçe / teras / açık alan). Emin değilsen null.
- bilgiler: kullanıcının mesajlarında AÇIKÇA verdiği bilgiler; yalnızca aşağıdaki alan adlarıyla. Yazım hatalarını ve Türkçe karakter eksiklerini düzelt (ör. "istnbul" -> "İstanbul"), metrekareyi "150 m²" biçiminde yaz. Verilmeyen bilgiyi yazma, tahmin etme.
Alan adları:
{self._field_catalog(service_type)}
"""
        messages = [{"role": "system", "content": system_prompt}]
        messages += self._history_for_llm(gecmis)
        messages.append({"role": "user", "content": str(mesaj).strip()})

        data = self._parse_json(self._llm(messages, temperature=0.5, max_tokens=900, json_mode=True))
        if not isinstance(data, dict) or not str(data.get("yanit") or "").strip():
            return None
        hizmet = data.get("hizmet")
        bilgiler = data.get("bilgiler") if isinstance(data.get("bilgiler"), dict) else {}
        return {
            "yanit": str(data["yanit"]).strip(),
            "proje_talebi": bool(data.get("proje_talebi")) and not brif_tamamlandi,
            "hizmet": hizmet if hizmet in QUESTION_POOLS else None,
            "bilgiler": {str(k): str(v).strip() for k, v in bilgiler.items() if v not in (None, "", [], {})}
        }

    def cevabi_yorumla(self, soru, mesaj, service_type, toplanan=None, acik_alanlar=None, gecmis=None):
        """
        Brif aşaması: kullanıcının cevabını sorunun bağlamında anlar, yazım hatalarını düzeltir.
        Döner: {"tur": cevap|belirsiz|atla|yan_soru|anlamsiz, "deger": str|None, "ek_bilgiler": {}, "yanit": str|None}
        Yapay zekâ yoksa None döner.
        """
        choices = soru.get("choices") or []
        acik = "\n".join(f"- {q['field']}: {q['question']}" for q in (acik_alanlar or [])) or "-"
        system_prompt = f"""Sen Rumenova'nın ön görüşme asistanı Nova'nın cevap yorumlayıcısısın.
Kullanıcıya bir brif sorusu soruldu. Görevin kullanıcının cevabını sorunun bağlamında anlamak.

Hizmet alanı: {service_type}
Soru alanı: {soru.get('field')}
Soru: {soru.get('question')}
Seçenekler: {', '.join(choices) if choices else 'yok (serbest cevap)'}
Şu ana kadar toplanan bilgiler: {json.dumps(toplanan or {}, ensure_ascii=False)}
Henüz cevaplanmamış diğer alanlar:
{acik}

ÇIKTI: Yalnızca şu JSON nesnesini döndür:
{{"tur": "cevap" | "belirsiz" | "atla" | "yan_soru" | "anlamsiz", "deger": "...", "ek_bilgiler": {{}}, "yanit": "..."}}

KURALLAR:
- tur=cevap: kullanıcı soruya cevap verdi. deger: cevabın düzeltilmiş, kısa ve temiz hali. Yazım hatalarını ve eksik Türkçe karakterleri düzelt (ör. "istnbul kadikoy" -> "İstanbul, Kadıköy"; "modrn" -> "Modern & Minimalist"). Cevap bir seçeneğe karşılık geliyorsa seçeneğin metnini aynen yaz; seçenek dışı bir tercih ise kullanıcının ifadesini düzeltilmiş haliyle yaz. Alan sorularında "150 m²" biçimini kullan. Anlamı değiştirme, bilgi ekleme.
- Kısa cevapları, yazım hatalı cevapları ve tek başına sayıları anlamsız sayma; soruyla birlikte değerlendir (alan sorusuna "150" = "150 m²").
- "Hayır", "yok" gibi olumsuz cevaplar geçerli cevaptır: tur=cevap, deger="Yok".
- tur=belirsiz: "bilmiyorum", "emin değilim", "henüz belli değil", "fark etmez" gibi.
- tur=atla: "geç", "atla", "paylaşmak istemiyorum".
- tur=yan_soru: kullanıcı soruyu cevaplamak yerine başka bir şey sordu. yanit: bu soruya 1-2 cümlelik kısa, profesyonel Türkçe yanıt (kesin fiyat / süre verme, bilgi uydurma).
- tur=anlamsiz: yalnızca cevap gerçekten anlaşılamıyorsa (ör. "asdasd", rastgele harfler).
- ek_bilgiler: kullanıcı aynı mesajda yukarıdaki cevaplanmamış alanlara ait bilgi de verdiyse {{"alan_adi": "düzeltilmiş değer"}}. Yalnızca listedeki alan adlarını kullan.
- Kullanılmayan alanlar için null yaz.
"""
        messages = [{"role": "system", "content": system_prompt}]
        messages += self._history_for_llm(gecmis, limit=4)
        messages.append({"role": "user", "content": str(mesaj).strip()})

        data = self._parse_json(self._llm(messages, temperature=0.1, max_tokens=900, json_mode=True))
        if not isinstance(data, dict) or data.get("tur") not in ["cevap", "belirsiz", "atla", "yan_soru", "anlamsiz"]:
            return None
        if data["tur"] == "cevap" and not str(data.get("deger") or "").strip():
            return None
        ek = data.get("ek_bilgiler") if isinstance(data.get("ek_bilgiler"), dict) else {}
        return {
            "tur": data["tur"],
            "deger": str(data.get("deger")).strip() if data.get("deger") else None,
            "ek_bilgiler": {str(k): str(v).strip() for k, v in ek.items() if v not in (None, "", [], {})},
            "yanit": str(data.get("yanit")).strip() if data.get("yanit") else None
        }

    def kisa_yanit(self, soru, gecmis=None):
        """Brif aşamasında yan soruya kısa yanıt (yapay zekâ yoksa None)."""
        system_prompt = (
            f"{Config.BUSINESS_CONTEXT}\n\nKullanıcı ön görüşme brifi sırasında bir yan soru sordu. "
            "Yalnızca bu soruya 1-2 cümlelik kısa ve profesyonel bir yanıt ver; yeni soru sorma."
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages += self._history_for_llm(gecmis, limit=6)
        messages.append({"role": "user", "content": str(soru).strip()})
        return self._llm(messages, temperature=0.6, max_tokens=500)

class AIServiceError(Exception):
    """Yönerge Modül C: Özel yapay zekâ servis hatası."""
    pass

# Modül C: Dosya sonunda ai_service örneği
ai_service = AIService()

