import json
import logging
import re
from config import Config

logger = logging.getLogger(__name__)

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

# 81 TÜRKİYE İLİ VE POPÜLER İLÇE HARİTASI
TURKEY_81_PROVINCES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın",
    "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı",
    "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep",
    "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars",
    "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa",
    "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya",
    "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa",
    "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman",
    "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
]

# İl takma isimleri ve yaygın ilçeler
PROVINCE_ALIASES_AND_DISTRICTS = {
    "Adana": ["adana", "seyhan", "çukurova", "yüreğir", "ceyhan", "kozan"],
    "Adıyaman": ["adıyaman", "adiyaman", "kahta", "besni", "gölbaşı"],
    "Afyonkarahisar": ["afyonkarahisar", "afyon", "sandıklı", "dinar", "bolvadin"],
    "Ağrı": ["ağrı", "agri", "doğubayazıt", "patnos"],
    "Amasya": ["amasya", "merzifon", "suluova"],
    "Ankara": ["ankara", "çankaya", "cankaya", "gölbaşı", "golbasi", "yenimahalle", "ümitköy", "umitkoy", "incek", "keçiören", "kecioren", "etimesgut", "mamak", "sincan", "altındağ", "batıkent", "eryaman", "beypazarı"],
    "Antalya": ["antalya", "muratpaşa", "muratpasa", "konyaaltı", "konyaalti", "kaş", "kas", "kalkan", "alanya", "kemer", "belek", "manavgat", "döşemealtı", "dosemealti", "kumluca", "side"],
    "Artvin": ["artvin", "hopa", "borçka", "şavşat"],
    "Aydın": ["aydın", "aydin", "kuşadası", "kusadasi", "didim", "efeler", "söke", "nazilli"],
    "Balıkesir": ["balıkesir", "balikesir", "ayvalık", "ayvalik", "edremit", "bandırma", "bandirma", "burhaniye", "erdek", "akçay", "cunda"],
    "Bilecik": ["bilecik", "bozüyük", "söğüt"],
    "Bingöl": ["bingöl", "bingol", "genç"],
    "Bitlis": ["bitlis", "tatvan", "ahlat", "güroymak"],
    "Bolu": ["bolu", "gerede", "mengen", "abant"],
    "Burdur": ["burdur", "bucak", "yeşilova"],
    "Bursa": ["bursa", "nilüfer", "nilufer", "osmangazi", "yıldırım", "mudanya", "inegöl", "gemlik", "iznik"],
    "Çanakkale": ["çanakkale", "canakkale", "bozcaada", "gökçeada", "gokceada", "gelibolu", "biga", "assos", "ayvacık"],
    "Çankırı": ["çankırı", "cankiri", "ılgaz"],
    "Çorum": ["çorum", "corum", "sungurlu", "osmancık"],
    "Denizli": ["denizli", "pamukkale", "merkezefendi", "tavas"],
    "Diyarbakır": ["diyarbakır", "diyarbakir", "bağlar", "kayapınar", "sur", "yenişehir", "ergani"],
    "Edirne": ["edirne", "keşan", "uzunköprü", "enez"],
    "Elazığ": ["elazığ", "elazig", "kovancılar", "sivrice"],
    "Erzincan": ["erzincan", "tercan", "üzümlü"],
    "Erzurum": ["erzurum", "palandöken", "yakutiye", "aziziye"],
    "Eskişehir": ["eskişehir", "eskisehir", "tepebaşı", "odunpazarı", "sivrihisar"],
    "Gaziantep": ["gaziantep", "antep", "şahinbey", "şehitkamil", "nizip"],
    "Giresun": ["giresun", "bulancak", "espiye", "görele"],
    "Gümüşhane": ["gümüşhane", "gumushane", "kelkit", "şiran"],
    "Hakkari": ["hakkari", "yüksekova", "şemdinli"],
    "Hatay": ["hatay", "antakya", "iskenderun", "defne", "samandağ", "arsuz", "dörtyol"],
    "Isparta": ["isparta", "yalvaç", "eğirdir"],
    "Mersin": ["mersin", "içel", "icel", "yenişehir", "mezitli", "tarsus", "erdemli", "silifke", "anamur"],
    "İstanbul": ["istanbul", "beykoz", "kadıköy", "kadikoy", "beşiktaş", "besiktas", "sarıyer", "sariyer", "şişli", "sisli", "bakırköy", "bakirkoy", "üsküdar", "uskudar", "kartal", "pendik", "başakşehir", "basaksehir", "çekmeköy", "cekmekoy", "ataşehir", "atasehir", "maltepe", "tuzla", "silivri", "şile", "sile", "beylikdüzü", "beyoglu", "beyoğlu", "fatih", "kağıthane", "eyüpsultan", "arnavutköy", "zeytinburnu", "esenler", "bahçelievler", "esenyurt", "avcılar", "küçükçekmece", "büyükçekmece"],
    "İzmir": ["izmir", "urla", "çeşme", "cesme", "alaçatı", "alacati", "karşıyaka", "karsiyaka", "bornova", "güzelbahçe", "guzelbahce", "konak", "seferihisar", "foça", "foca", "bayraklı", "çiğli", "alsancak", "buca", "balçova", "narlıdere", "gaziemir", "torbalı", "dikili", "menderes", "karaburun"],
    "Kars": ["kars", "sarıkamış", "kağızman"],
    "Kastamonu": ["kastamonu", "tosya", "taşköprü", "inebolu", "cide"],
    "Kayseri": ["kayseri", "melikgazi", "kocasinan", "talas", "develi"],
    "Kırklareli": ["kırklareli", "kirklareli", "lüleburgaz", "babaeski", "iğneada"],
    "Kırşehir": ["kırşehir", "kirsehir", "kaman", "mucur"],
    "Kocaeli": ["kocaeli", "izmit", "gebze", "darıca", "körfez", "gölcük", "kartepe", "başiskele", "kandıra"],
    "Konya": ["konya", "selçuklu", "meram", "karatay", "ereğli", "akşehir", "beyşehir"],
    "Kütahya": ["kütahya", "kutahya", "tavşanlı", "gediz", "simav"],
    "Malatya": ["malatya", "battalgazi", "yeşilyurt", "doğanşehir"],
    "Manisa": ["manisa", "yunusemre", "şehzadeler", "akhisar", "turgutlu", "salihli", "soma", "alaşehir"],
    "Kahramanmaraş": ["kahramanmaraş", "kahramanmaras", "maraş", "maras", "onikişubat", "dulkadiroğlu", "elbistan", "afşin"],
    "Mardin": ["mardin", "artuklu", "midyat", "kızıltepe", "nusaybin"],
    "Muğla": ["muğla", "mugla", "bodrum", "fethiye", "marmaris", "datça", "datca", "milas", "menteşe", "ortaca", "dalaman", "köyceğiz", "koycegiz", "akyaka", "göcek", "gocek", "turgutreis", "yalıkavak"],
    "Muş": ["muş", "mus", "bulanık", "malazgirt"],
    "Nevşehir": ["nevşehir", "nevsehir", "ürgüp", "urgup", "avanos", "göreme", "goreme", "kapadokya", "uçhisar"],
    "Niğde": ["niğde", "nigde", "bor", "çamardı"],
    "Ordu": ["ordu", "altınordu", "ünye", "fatsa"],
    "Rize": ["rize", "çayeli", "ardeşen", "çamlıhemşin", "ayder", "fındıklı"],
    "Sakarya": ["sakarya", "adapazarı", "adapazari", "serdivan", "sapanca", "hendek", "karasu", "akyazı"],
    "Samsun": ["samsun", "atakum", "ilkadım", "canik", "bafra", "çarşamba"],
    "Siirt": ["siirt", "kurtalan", "pervari"],
    "Sinop": ["sinop", "boyabat", "gerze", "ayancık"],
    "Sivas": ["sivas", "şarkışla", "suşehri", "zara", "divriği"],
    "Tekirdağ": ["tekirdağ", "tekirdag", "çorlu", "corlu", "süleymanpaşa", "çerkezköy", "malkara", "şarköy"],
    "Tokat": ["tokat", "erbaa", "turhal", "niksar", "zile"],
    "Trabzon": ["trabzon", "ortahisar", "akçaabat", "akcaabat", "yomra", "araklı", "of", "maçka"],
    "Tunceli": ["tunceli", "dersim", "ovacık", "pertek", "çemişgezek"],
    "Şanlıurfa": ["şanlıurfa", "sanliurfa", "urfa", "haliliye", "eyyübiye", "karaköprü", "siverek", "viranşehir", "birecik"],
    "Uşak": ["uşak", "usak", "banaz", "eşme"],
    "Van": ["van", "ipekyolu", "tuşba", "edremit", "erciş"],
    "Yozgat": ["yozgat", "sorgun", "akdağmadeni", "boğazlıyan"],
    "Zonguldak": ["zonguldak", "ereğli", "kdz ereğli", "çaycuma", "devrek"],
    "Aksaray": ["aksaray", "eskil", "gülağaç"],
    "Bayburt": ["bayburt", "aydıntepe", "demirözü"],
    "Karaman": ["karaman", "ermenek", "sarıveliler"],
    "Kırıkkale": ["kırıkkale", "kirikkale", "yahşihan", "keskin"],
    "Batman": ["batman", "kozluk", "hasankeyf", "beşiri"],
    "Şırnak": ["şırnak", "sirnak", "cizre", "silopi", "idil"],
    "Bartın": ["bartın", "bartin", "amasra", "ulus"],
    "Ardahan": ["ardahan", "göle", "posof"],
    "Iğdır": ["ığdır", "igdir", "aralık", "tuzluca"],
    "Yalova": ["yalova", "çiftlikköy", "çınarcık", "armutlu", "altınova"],
    "Karabük": ["karabük", "karabuk", "safranbolu", "yenice"],
    "Kilis": ["kilis", "elbeyli", "musabeyli"],
    "Osmaniye": ["osmaniye", "kadirli", "düziçi"],
    "Düzce": ["düzce", "duzce", "akçakoca", "kaynaşlı"]
}

def normalize_tr(text):
    """Türkçe karakterleri ve boşlukları eşleştirme için normalize eder."""
    if not text:
        return ""
    mapping = {
        'ı': 'i', 'İ': 'i', 'I': 'i',
        'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u',
        'ş': 's', 'Ş': 's',
        'ö': 'o', 'Ö': 'o',
        'ç': 'c', 'Ç': 'c'
    }
    t = text.lower()
    for tr_char, eng_char in mapping.items():
        t = t.replace(tr_char.lower(), eng_char)
    return t

class AIService:
    @classmethod
    def is_gibberish_or_irrelevant(cls, text):
        """
        Anlamsız, saçma veya klavye rastgele basımı (asdasd, qwerty, 1111, ????) tespit eder.
        """
        if not text:
            return True
        t = text.strip()
        t_norm = normalize_tr(t)

        # 1. Çok kısa veya sadece noktalama / özel karakter
        clean_letters = re.sub(r'[^a-zA-Z0-9]', '', t_norm)
        if len(clean_letters) == 0 and len(t) > 0:
            return True

        # 2. Tek bir karakterin 3 veya daha fazla ardışık tekrarı (aaaa, sssss, 1111)
        if re.search(r'(.)\1{3,}', t_norm):
            return True

        # 3. Klavye rastgele basma kalıpları
        keyboard_mash = [
            "asdasd", "asdfgh", "sdfgh", "dfghjk", "fghjkl", "qwerty", "wertyu",
            "zxcvbn", "xcvbnm", "qweqwe", "asdfasdf", "hjkhjk", "jkljkl", "ghjghj",
            "123123", "123456", "abcabc", "aaasss"
        ]
        for pattern in keyboard_mash:
            if pattern in t_norm:
                return True

        # 4. Uzun harf dizisinde sesli harf oranı
        words = t_norm.split()
        for word in words:
            letters_only = re.sub(r'[^a-z]', '', word)
            if len(letters_only) >= 5:
                vowels = re.findall(r'[aeiou]', letters_only)
                if len(vowels) == 0:
                    return True
                if len(vowels) / len(letters_only) < 0.12:
                    return True

        return False

    @classmethod
    def check_if_uncertain_answer(cls, text):
        """
        Kullanıcı 'bilmiyorum', 'hayır', 'yok', 'emin değilim' gibi olumsuz ve belirsiz cevap yazdıysa tespit eder.
        """
        t_norm = normalize_tr(text.strip())

        exact_uncertain = [
            "bilmiyorum", "bilmiom", "belirlemedim", "emin degilim", "fikrim yok",
            "henuz yok", "bilmem", "fark etmez", "farketmez", "kararsizim",
            "net degil", "belli degil", "dusunmedim", "hayir", "yok", "yoktur",
            "yok henuz", "hayir yok", "yok maalesef", "bilmiyorum maalesef",
            "yok gibi", "henuz belirlemedim", "hicbir fikrim yok", "yok hayir"
        ]
        
        if t_norm in exact_uncertain:
            return True

        uncertain_patterns = [
            r'\bbilmiyorum\b', r'\bbilmiom\b', r'\bemin degilim\b', r'\bfikrim yok\b',
            r'\bbelirlemedim\b', r'\bkararsizim\b', r'\bfark etmez\b', r'\bfarketmez\b',
            r'\bnet degil\b', r'\bbelli degil\b', r'\bdusunmedim\b', r'\bhayir yok\b',
            r'\byok maalesef\b', r'\bbilmiyorum maalesef\b'
        ]
        return any(re.search(p, t_norm) for p in uncertain_patterns)

    @classmethod
    def find_turkey_province_and_district(cls, text):
        """
        81 il ve ilçeler listesi üzerinden metindeki ili ve ilçeyi doğrular ve çıkarır.
        Bulamazsa (None, None) döner.
        """
        if not text:
            return None, None

        t_norm = normalize_tr(text)
        
        found_province = None
        found_district = None

        # 1. 81 il ve altındaki takma isim/ilçeleri kontrol et
        for province, keywords in PROVINCE_ALIASES_AND_DISTRICTS.items():
            prov_norm = normalize_tr(province)
            if re.search(r'\b' + re.escape(prov_norm) + r'\b', t_norm):
                found_province = province

            for kw in keywords:
                kw_norm = normalize_tr(kw)
                if kw_norm != prov_norm and re.search(r'\b' + re.escape(kw_norm) + r'\b', t_norm):
                    found_district = kw.capitalize()
                    found_province = province
                    break
            
            if found_province and found_district:
                break

        # 2. Eğer özel eşleşmediyse düz 81 il listesini kontrol et
        if not found_province:
            for p in TURKEY_81_PROVINCES:
                p_norm = normalize_tr(p)
                if re.search(r'\b' + re.escape(p_norm) + r'\b', t_norm):
                    found_province = p
                    break

        return found_province, found_district

    @classmethod
    def extract_info_from_message(cls, text, current_data):
        extracted = {}
        t_lower = text.lower().strip()

        if t_lower in ["başla", "start", "merhaba", "selam", "evet", "tamam"]:
            return extracted

        # 1. 81 İl ve İlçe Doğrulama
        prov, dist = cls.find_turkey_province_and_district(text)
        if prov and dist:
            extracted["konum"] = f"{prov}, {dist}"
        elif prov:
            extracted["konum"] = f"{prov}"

        # 2. Kat Sayısı
        kat_match = re.search(r'(\d+)\s*kat(lı)?', t_lower)
        if kat_match:
            extracted["kat_sayisi"] = f"{kat_match.group(1)} Katlı"
        elif "tek kat" in t_lower or "tek katlı" in t_lower:
            extracted["kat_sayisi"] = "Tek Katlı"
        elif "dubleks" in t_lower:
            extracted["kat_sayisi"] = "2 Katlı (Dubleks)"
        elif "tripleks" in t_lower:
            extracted["kat_sayisi"] = "3 Katlı (Tripleks)"

        # 3. Alan (m2, metrekare)
        alan_match = re.search(r'(\d+[\d\.,]*)\s*(m2|m²|metrekare|metre kare)', t_lower)
        if alan_match:
            extracted["yaklasik_alan"] = f"{alan_match.group(1)} m²"

        # 4. Kullanım Amacı / Yapı Türü
        if "villa" in t_lower:
            extracted["kullanim_amaci"] = "Villa"
        elif re.search(r'\b(daire|apartman|ev|evim|evi)\b', t_lower):
            extracted["kullanim_amaci"] = "Konut / Daire"
        elif "ofis" in t_lower or "işyeri" in t_lower or "iş yeri" in t_lower:
            extracted["kullanim_amaci"] = "Ticari / Ofis"

        # 5. Yeni Yapı vs Yenileme
        if "sıfırdan" in t_lower or "yeni yapı" in t_lower or "arsa" in t_lower or "yeni yapıda" in t_lower:
            extracted["proje_turu"] = "Yeni Yapı"
        elif "tadilat" in t_lower or "yenileme" in t_lower or "dönüşüm" in t_lower or "içini yenile" in t_lower:
            extracted["proje_turu"] = "Yenileme"
        elif "restorasyon" in t_lower or "tarihi" in t_lower:
            extracted["proje_turu"] = "Restorasyon"

        # 6. Ek Talep (Bahçe, Havuz vb.)
        if "bahçe" in t_lower or "bahçeli" in t_lower:
            extracted["ek_talepler"] = "Bahçe"
        if "havuz" in t_lower or "havuzlu" in t_lower:
            extracted["ek_talepler"] = "Havuz"

        return extracted

    @classmethod
    def get_question_by_field(cls, service_type, field):
        """Alan adına göre soru tanımını döner (yoksa None)."""
        pool = QUESTION_POOLS.get(service_type, QUESTION_POOLS["mimari"])
        for q in pool:
            if q["field"] == field:
                return q
        return None

    @classmethod
    def get_valid_fields(cls, service_type):
        """Hizmet alanının soru havuzundaki geçerli alan adları."""
        pool = QUESTION_POOLS.get(service_type, QUESTION_POOLS["mimari"])
        return {q["field"] for q in pool}

    @classmethod
    def is_plain_negative(cls, text):
        """'yok', 'hayır' gibi düz olumsuz cevap (evet/hayır tipi sorularda geçerli cevaptır)."""
        return normalize_tr(text.strip()) in [
            "hayir", "yok", "yoktur", "hayir yok", "yok hayir", "yok gibi",
            "henuz yok", "yok henuz", "yok maalesef"
        ]

    @classmethod
    def _apply_units(cls, field, value):
        """AI birim eklemeyi unutursa yedek: alan -> m², kullanıcı sayısı -> kişi, bütçe -> TL."""
        v = (value or "").strip()
        if not v or not re.search(r'\d', v):
            return v
        low = v.lower()
        if field == "yaklasik_alan" and not re.search(r'm2|m²|metre', low):
            return f"{v} m²"
        if field == "kullanici_sayisi" and "kişi" not in low and "kisi" not in low:
            return f"{v} kişi"
        if field == "butce_araligi" and not re.search(r'tl|₺|lira|\$|€|usd|eur', low):
            return f"{v} TL"
        return v

    @classmethod
    def evaluate_answer(cls, question_def, answer, collected_data):
        """
        Sabit sorunun cevabını AI ile değerlendirir (BUSINESS_CONTEXT kuralları geçerlidir).
        Dönüş: {"status": valid|invalid|uncertain|side_question, "value": str, "reply": str}
        AI kapalıysa veya hata verirse None döner; çağıran taraf kural motoruna düşer.
        """
        if not (Config.GROQ_API_KEY and Config.AI_ANSWER_VALIDATION):
            return None

        try:
            from groq import Groq
            client = Groq(api_key=Config.GROQ_API_KEY, timeout=Config.AI_TIMEOUT, max_retries=0)

            task = (
                "GÖREV: Kullanıcıya aşağıdaki SABİT soru soruldu. Kullanıcının cevabını değerlendir.\n"
                f"Soru: {question_def['question']}\n"
                f"Alan: {question_def['field']}\n"
                f"Örnek seçenekler (zorunlu değil): {question_def.get('choices', [])}\n"
                f"Şimdiye kadar toplanan bilgiler: {json.dumps(collected_data, ensure_ascii=False)}\n"
                f"Kullanıcının cevabı: {answer}\n\n"
                "SADECE şu JSON'u döndür, başka metin yazma:\n"
                '{"status": "valid|invalid|uncertain|side_question", "value": "...", "reply": "..."}\n'
                "- valid: cevap soruyla ilgili bir bilgi içeriyor. EKSİK, KISMI veya yazım hatalı olsa bile valid say "
                "(örn. 'malzeme ve renk' sorusuna sadece 'beyaz' demek geçerlidir). value = cevabın kısa, temiz Türkçe hali; "
                "yazım hatalarını düzelt, kullanıcının söylemediği bilgiyi ekleme. reply boş.\n"
                "- invalid: SADECE cevap soruyla tamamen ilgisiz, anlamsız (rastgele harf/rakam yığını) veya hiçbir bilgi içermiyorsa. value boş. "
                "reply = 1 kısa cümleyle nazikçe sebebini söyle ve AYNI soruyu tekrar sor.\n"
                "- Alan 'konum' ise yalnızca il yeterlidir (ilçe zorunlu değil); value'ya düzeltilmiş il (varsa ilçe) adını yaz.\n"
                "- Kullanıcı kararı sana bırakıyor veya önceki önerini onaylıyorsa (örn. 'tamam', 'sen bilirsin', 'dediklerin', 'olur', 'sence') "
                "ve somut bir bilgi vermiyorsa bunu cevap SAYMA: status=invalid; reply = kullanıcıdan kendi tercihini yazmasını "
                "isteyen 1 kısa cümle (seçenekler varsa say) + AYNI soru. Evet/hayır tipi sorularda açık 'evet' geçerlidir.\n"
                "- Birimler: yaklasik_alan için value'ya 'm²', kullanici_sayisi için 'kişi', butce_araligi için 'TL' ekle "
                "(k=bin, m=milyon kısaltmalarını açık yaz, örn. '76k-3m' -> '76.000 - 3.000.000 TL'). Birim zaten varsa tekrar ekleme.\n"
                "- uncertain: kullanıcı bilmiyor / karar vermemiş / emin değil. value ve reply boş.\n"
                "- side_question: kullanıcı cevap yerine yan bir soru sordu. value boş. "
                "reply = yan soruya 1-2 kısa cümleyle cevap (kesin fiyat/süre verme, uydurma) + AYNI soruyu tekrar sor."
            )

            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": Config.BUSINESS_CONTEXT},
                    {"role": "user", "content": task}
                ],
                model=Config.GROQ_MODEL,
                temperature=0.2,
                max_tokens=300
            )
            raw = completion.choices[0].message.content or ""
            match = re.search(r'\{.*\}', raw, re.S)
            if not match:
                return None
            data = json.loads(match.group(0))

            status = str(data.get("status", "")).strip().lower()
            if status not in ("valid", "invalid", "uncertain", "side_question"):
                return None

            value = str(data.get("value") or "").strip()
            reply = str(data.get("reply") or "").strip()

            if status == "valid" and not value:
                value = answer.strip()
            if status == "valid":
                value = cls._apply_units(question_def["field"], value)
            if status in ("invalid", "side_question") and not reply:
                return None

            return {"status": status, "value": value, "reply": reply}
        except Exception as e:
            logger.warning("AI cevap değerlendirme hatası, kural motoruna düşülüyor: %s", e)
            return None

    @classmethod
    def chat_after_completion(cls, message, brief_text, history, status_info=""):
        """
        Sorular bittikten sonra gelen serbest mesajları BUSINESS_CONTEXT ile cevaplar
        (örn. 'brifimi tekrar göster'). AI kapalı/hatalı ise None döner.
        """
        if not (Config.GROQ_API_KEY and Config.AI_ANSWER_VALIDATION):
            return None

        try:
            from groq import Groq
            client = Groq(api_key=Config.GROQ_API_KEY, timeout=Config.AI_TIMEOUT, max_retries=0)

            context = (
                Config.BUSINESS_CONTEXT
                + "\n\nŞU ANKI DURUM: Ön görüşme soruları tamamlandı. Yeni soru sorma. "
                "Kullanıcının mesajını yalnızca aşağıdaki bilgilere dayanarak 1-3 kısa cümleyle cevapla. "
                "Brif istenirse bilgileri düzenli ve kısa bir özet olarak yaz. Bilgi uydurma; kesin fiyat, süre veya "
                "randevu onayı verme. Kullanıcı bir bilgiyi değiştirmek isterse bunu not ettiğini söyle ve "
                "iletişim formunda uzmana iletebileceğini belirt.\n\n"
                f"TOPLANAN BRİF:\n{brief_text}\n\n{status_info}"
            )
            messages = [{"role": "system", "content": context}]
            for m in (history or [])[-10:]:
                if m.get("role") in ("user", "assistant") and m.get("content"):
                    messages.append({"role": m["role"], "content": m["content"]})
            messages.append({"role": "user", "content": message})

            completion = client.chat.completions.create(
                messages=messages,
                model=Config.GROQ_MODEL,
                temperature=0.4,
                max_tokens=500
            )
            reply = (completion.choices[0].message.content or "").strip()
            return reply or None
        except Exception as e:
            logger.warning("AI serbest sohbet hatası, sabit mesaja düşülüyor: %s", e)
            return None

    @classmethod
    def get_next_question(cls, service_type, collected_data, skipped_fields=None):
        pool = QUESTION_POOLS.get(service_type, QUESTION_POOLS["mimari"])
        skipped = set(skipped_fields or [])

        for q in pool:
            field = q["field"]
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
        Yönerge & Yazılım Kontrol Modül C:
        Kullanıcı mesajını ve geçmişi alıp Nova'nın Türkçe yanıtını üretir.
        Groq API anahtarı varsa LLM ile üretir, yoksa kural tabanlı mimari motor ile yanıtlar.
        """
        if gecmis is None:
            gecmis = []

        # 1. Groq Anahtarı Varsa LLM ile Çağır
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
                messages.append({"role": "user", "content": mesaj})

                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="openai/gpt-oss-120b",
                    temperature=0.6,
                    max_tokens=600
                )
                return chat_completion.choices[0].message.content.strip()
            except Exception as e:
                # Groq hatası durumunda mimari motora fallback yap
                pass

        # 2. Akıllı Mimari Kural Motoru (Fallback / Demo Modu)
        if self.is_gibberish_or_irrelevant(mesaj):
            return "Tam olarak ne demek istediğinizi söyler misiniz?"

        if self.check_if_uncertain_answer(mesaj):
            return "Anladım, yaklaşık veya tahmini olarak belirtiniz."

        return "Harika, projenizle ilgili bilgileri not aldım. Sıradaki sorumuzla devam edelim."

class AIServiceError(Exception):
    """Yönerge Modül C: Özel yapay zekâ servis hatası."""
    pass

# Modül C: Dosya sonunda ai_service örneği
ai_service = AIService()

