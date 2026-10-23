"""
Kural tabanlı cevap anlama katmanı.

Yapay zekâ (Groq) kapalıyken veya hata verdiğinde konuşma motoru bu fonksiyonlarla
cevapları yorumlar: Türkçe karakter / yazım hatası toleransı, seçeneklere en yakın
eşleşme, 81 il eşleşmesi, metrekare ayıklama ve cevap türü (cevap / belirsiz / atla /
yan soru / anlamsız) tespiti.
"""
import re
from difflib import SequenceMatcher

TR_ASCII = str.maketrans("çğıöşüâîû", "cgiosuaiu")

ILLER = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin",
    "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale",
    "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum",
    "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin",
    "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli",
    "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş",
    "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas",
    "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak",
    "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan",
    "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
]
IL_TAKMA_ADLARI = {
    "afyon": "Afyonkarahisar", "maras": "Kahramanmaraş", "urfa": "Şanlıurfa",
    "antep": "Gaziantep", "icel": "Mersin", "izmit": "Kocaeli", "adapazari": "Sakarya"
}

SKIP_WORDS = ["gec", "atla", "pas", "gecelim", "atlayalim", "paylasmak istemiyorum", "soylemek istemiyorum"]
UNCERTAIN_PATTERNS = [
    "bilmiyorum", "bilmiyom", "bilmiom", "emin degilim", "fikrim yok", "kararsizim",
    "karar vermedim", "belli degil", "netlesmedi", "henuz bilmiyorum", "farketmez", "fark etmez"
]
NEGATIVE_WORDS = ["hayir", "yok", "yoktur", "istemiyorum", "gerek yok", "hayir yok"]
YES_WORDS = ["evet", "olur", "tamam", "tamamdir", "peki", "baslayalim", "basla", "ok", "okey",
             "uygun", "hadi", "sor", "sorabilirsin", "sorun", "evt", "tabi", "tabii", "elbette", "onayliyorum", "onay"]
NO_WORDS = ["hayir", "istemiyorum", "simdi degil", "sonra", "gerek yok", "yok", "daha sonra", "simdilik hayir"]

SERVICE_KEYWORDS = {
    "ic_mimari": ["ic mimar", "ic mimari", "icmimar", "dekorasyon", "tadilat", "mutfak", "banyo",
                  "salon", "yatak odasi", "mobilya", "daire", "ofis duzen", "kafe", "magaza"],
    "peyzaj": ["peyzaj", "bahce", "bahcem", "teras", "park", "acik alan", "cim", "bitki", "agac", "havuz"],
    "mimari": ["mimari", "mimar", "bina", "yapi", "villa", "insaat", "ev yap", "konut", "restorasyon",
               "yeni yapi", "kat"]
}
# Yapay zekâ yokken proje talebi sayılan ifadeler (yalnızca somut proje / iş isteği)
PROJECT_WORDS = ["projem", "tasarlat", "tadilat", "yenilet", "yaptir", "insa et", "dekore", "duzenlet",
                 "metrekare", "m2", "villa", "dairem", "bahcem", "evim", "ofisim"]
COMPLAINT_WORDS = ["dayat", "israr", "surekli", "neden hep", "niye hep", "rahatsiz", "biktim", "yeter", "sacma",
                   "istemiyorum", "zorla"]
KEYBOARD_MASH = ["asd", "qwe", "sdf", "dfg", "zxc", "jkl", "hjk", "wer", "xcv", "fgh"]
VOWELS = set("aeiou")


def norm(text):
    """Küçük harf + Türkçe karakterleri ASCII'ye indirger, noktalama siler."""
    t = str(text or "").replace("I", "ı").replace("İ", "i").lower().translate(TR_ASCII)
    t = re.sub(r"[^a-z0-9²\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def _contains_phrase(normalized, phrases):
    padded = f" {normalized} "
    return any(f" {p} " in padded for p in phrases)


def _fuzzy_word_hit(normalized, keywords, threshold=0.8):
    """Kelime bazında yazım hatası toleranslı anahtar kelime eşleşmesi."""
    if _contains_phrase(normalized, keywords) or any(k in normalized for k in keywords if " " in k):
        return True
    words = [w for w in normalized.split() if len(w) >= 4]
    single = [k for k in keywords if " " not in k and len(k) >= 4]
    return any(similar(w, k) >= threshold for w in words for k in single)


def is_skip(text):
    n = norm(text)
    return n in SKIP_WORDS or _contains_phrase(n, ["paylasmak istemiyorum", "soylemek istemiyorum"])


def is_uncertain(text):
    n = norm(text)
    if any(p in n for p in UNCERTAIN_PATTERNS):
        return True
    return any(similar(w, "bilmiyorum") >= 0.8 for w in n.split())


def is_negative(text):
    n = norm(text)
    return n in NEGATIVE_WORDS


def is_yes(text):
    n = norm(text)
    if not n or len(n.split()) > 5:
        return False
    if _contains_phrase(n, ["istemiyorum", "hayir", "degil"]):
        return False
    words = n.split()
    return any(w in YES_WORDS or (len(w) >= 4 and any(similar(w, y) >= 0.85 for y in YES_WORDS if len(y) >= 4))
               for w in words)


def is_no(text):
    n = norm(text)
    if not n or len(n.split()) > 6:
        return False
    return n in NO_WORDS or _contains_phrase(n, ["hayir", "istemiyorum", "simdi degil", "gerek yok", "simdilik hayir"])


def is_gibberish(text):
    """Klavye karmaşası / anlamsız tek kelimelik girdiler."""
    n = norm(text)
    if not n:
        return True
    if re.search(r"\d", n):
        return False
    letters = n.replace(" ", "")
    if len(letters) < 4:
        return False
    if re.search(r"(.)\1{3,}", letters):
        return True
    if len(n.split()) <= 2 and any(m in letters for m in KEYBOARD_MASH):
        return True
    for word in n.split():
        if len(word) >= 5 and sum(c in VOWELS for c in word) / len(word) < 0.2:
            return True
        if re.search(r"[^aeiou\s]{5,}", word):
            return True
    return False


def is_side_question(text):
    t = str(text or "").strip()
    n = norm(t)
    if t.endswith("?") and len(n) >= 4:
        return True
    starts = ["nasil", "ne kadar", "neden", "nedir", "kac para", "hangisi", "ne onerirsin", "onerir misin"]
    return any(n.startswith(s) for s in starts)


def detect_service(text):
    n = norm(text)
    for service in ["ic_mimari", "peyzaj", "mimari"]:
        if _fuzzy_word_hit(n, SERVICE_KEYWORDS[service]):
            return service
    return None


def is_complaint(normalized):
    """Kullanıcı rahatsızlık / şikâyet belirtiyor mu (norm() uygulanmış metin)."""
    return any(w in normalized for w in COMPLAINT_WORDS)


def looks_like_project_request(text):
    n = norm(text)
    if is_complaint(n) or is_side_question(text):
        return False
    return detect_service(text) is not None or any(w in f" {n} " for w in PROJECT_WORDS)


def match_province(text):
    """Metindeki ili (yazım hatası toleranslı) ve kalan ilçe ifadesini bulur."""
    words = norm(text).split()
    raw_words = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ\s]", " ", str(text or "")).split()
    best = (0.0, None, None)
    for i, w in enumerate(words):
        if len(w) < 3:
            continue
        if w in IL_TAKMA_ADLARI:
            best = (1.0, IL_TAKMA_ADLARI[w], i)
            break
        for il in ILLER:
            score = similar(w, norm(il))
            threshold = 1.0 if len(norm(il)) <= 3 else 0.8
            if score >= threshold and score > best[0]:
                best = (score, il, i)
    if not best[1]:
        return None, None
    filler = {"ili", "il", "ilce", "ilcesi", "de", "da", "te", "ta", "merkez", "sehir", "sehri", "bolgesi", "ve"}
    district_parts = [
        raw_words[j] for j, w in enumerate(words)
        if j != best[2] and w not in filler and j < len(raw_words)
    ]
    district = " ".join(tr_title(p) for p in district_parts) if district_parts else None
    return best[1], district


def tr_title(word):
    word = str(word)
    if not word:
        return word
    first = word[0]
    first = "İ" if first == "i" else ("I" if first == "ı" else first.upper())
    rest = word[1:].replace("I", "ı").replace("İ", "i").lower()
    return first + rest


def match_choice(text, choices):
    """Serbest yazılmış cevabı (yazım hatası toleranslı) seçeneklerden birine eşler."""
    if not choices:
        return None
    n = norm(text)
    if not n or len(n.split()) > 5:
        return None
    best_choice, best_score, second = None, 0.0, 0.0
    for choice in choices:
        c = norm(choice)
        if n == c:
            return choice
        score = similar(n, c)
        if len(n) >= 4 and (n in c or c in n):
            score = max(score, 0.9)
        choice_words = [w for w in c.split() if len(w) >= 3]
        # Kısa cevap tam kelime eşleşmesi ("ev" -> "Ev / Konut")
        if len(n.split()) <= 2 and any(len(w) >= 2 and w in c.split() for w in n.split()):
            score = max(score, 0.9)
        for word in n.split():
            if len(word) < 3:
                continue
            for cw in choice_words:
                score = max(score, similar(word, cw) * (0.95 if len(choice_words) > 1 else 1.0))
        if score > best_score:
            best_choice, second, best_score = choice, best_score, score
        elif score > second:
            second = score
    if best_score >= 0.8 and best_score - second >= 0.05:
        return best_choice
    return None


def extract_area(text):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(m2|m²|metrekare|metre kare|metre|mt|m\b)?", str(text or "").lower())
    if not m:
        return None
    return f"{m.group(1).replace(',', '.')} m²"


def clean_free_text(text):
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t[:1].upper() + t[1:] if t else t


def match_option(text, options):
    """Buton seçeneklerini numara ("2") veya etiket (yazım hatası toleranslı) ile eşler."""
    if not options:
        return None
    t = str(text or "").strip().rstrip(").")
    if t.isdigit():
        idx = int(t) - 1
        return options[idx] if 0 <= idx < len(options) else None
    label = match_choice(text, [o["label"] for o in options])
    if label:
        return next(o for o in options if o["label"] == label)
    return None


def interpret_answer(question, text):
    """
    Kural tabanlı cevap yorumu. Döner: {"tur": ..., "deger": ..., "ek_bilgiler": {}}
    tur: cevap | belirsiz | atla | yan_soru | anlamsiz
    """
    field = question.get("field")
    choices = question.get("choices") or []
    raw = str(text or "").strip()

    if is_skip(raw):
        return {"tur": "atla", "deger": None, "ek_bilgiler": {}}
    if question.get("allow_negative") and is_negative(raw):
        return {"tur": "cevap", "deger": "Yok", "ek_bilgiler": {}}
    if is_uncertain(raw):
        return {"tur": "belirsiz", "deger": None, "ek_bilgiler": {}}

    choice = match_choice(raw, choices)
    if choice:
        return {"tur": "cevap", "deger": choice, "ek_bilgiler": {}}
    if is_side_question(raw):
        return {"tur": "yan_soru", "deger": None, "ek_bilgiler": {}}
    if is_gibberish(raw):
        return {"tur": "anlamsiz", "deger": None, "ek_bilgiler": {}}

    if field == "konum":
        il, ilce = match_province(raw)
        if il:
            return {"tur": "cevap", "deger": f"{il}, {ilce}" if ilce else il, "ek_bilgiler": {}}
    if field == "yaklasik_alan":
        area = extract_area(raw)
        if area:
            return {"tur": "cevap", "deger": area, "ek_bilgiler": {}}

    return {"tur": "cevap", "deger": clean_free_text(raw), "ek_bilgiler": {}}


def extract_prefill(text):
    """Serbest sohbet mesajından brif alanlarına önceden yazılabilecek bilgiler."""
    found = {}
    il, ilce = match_province(text)
    if il:
        found["konum"] = f"{il}, {ilce}" if ilce and len(ilce.split()) == 1 else il
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(m2|m²|metrekare|metre kare)", str(text or "").lower())
    if m:
        found["yaklasik_alan"] = f"{m.group(1).replace(',', '.')} m²"
    return found
