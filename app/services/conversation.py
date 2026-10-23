"""
Rumenova konuşma motoru (/api/chat/init, /api/chat).

HTML widget ve Wix chatbot kutusu aynı motoru kullanır; yalnızca görünümleri farklıdır.
Her istek oturumu SQLite'tan okur, işler ve mevcut chat_sessions sütunlarına geri yazar:
  chat_messages  -> tüm mesajlar (aşama ve soru alanıyla)
  collected_data -> brif cevaplarının düzeltilmiş hali
  flow_state     -> aşama, sıradaki soru, ham cevaplar, sohbetten not alınan bilgiler

Aşamalar (flow_state["stage"]):
  sohbet -> onay -> hizmet -> uzman -> ekip -> sorular -> saat -> ozet (-> duzelt) -> tamamlandi
"""
from config import Config
from app.database import (
    get_or_create_session, update_session, get_all_professionals,
    get_professionals_by_service, get_expert_or_office_by_code, get_available_slots
)
from app.services.ai_service import AIService, QUESTION_POOLS, ai_service
from app.services.brief import build_wix_summary_dict, save_brief_snapshot, field_label
from app.services import normalizer as nz

WIX_FORM_URL = "https://busemutlubg.wixstudio.com/rumenova/ongorusme"
SERVICE_TITLES = {"mimari": "Mimari Tasarım", "ic_mimari": "İç Mimarlık", "peyzaj": "Peyzaj Tasarımı"}
# Belirsiz cevapta bir kez tahmin istenen alanlar (diğerleri doğrudan "uzmanla görüşülecek" olur)
ESTIMATE_FIELDS = {"yaklasik_alan", "butce_araligi", "hedef_zaman", "kat_sayisi", "mevcut_kat_sayisi", "kullanici_sayisi"}
# Bu alanlarda "2" gibi bir sayı seçenek numarası değil, cevabın kendisidir
NO_DIGIT_CHOICE_FIELDS = {"kullanici_sayisi", "kat_sayisi", "mevcut_kat_sayisi"}
# Reddedilen brif teklifinden sonra yeniden teklif için gereken kullanıcı mesajı sayısı
OFFER_COOLDOWN = 4
MAX_MESSAGE_LENGTH = 1000

MSG_WELCOME = ("Merhaba, ben Rumenova'nın yapay zekâ destekli asistanı Nova. Mimari, iç mimari veya peyzaj "
               "projenizle ilgili merak ettiklerinizi sorabilirsiniz; hazır olduğunuzda ön görüşme brifinizi "
               "birlikte oluşturalım.")
MSG_OFFER = "Talebinizi uzmanımıza iletebilmem için ön görüşme brifinizi oluşturalım mı? Birkaç kısa soru soracağım."
MSG_BRIEF_START = ("Harika! Sizi ön görüşme formumuza yönlendiriyorum; sorularımı tek tek soracağım. "
                   "Cevaplamak istemediğiniz soruyu \"geç\" yazarak atlayabilirsiniz.")
MSG_OFFER_DECLINED = "Tabii, sohbetimize devam edelim. Hazır olduğunuzda \"brif oluştur\" yazmanız yeterli."
MSG_ASK_SERVICE = "Hangi hizmet alanında ön görüşme yapmak istersiniz?"
MSG_ASK_PROF = "Bu alanda hangi mimar veya ofisle görüşmek istersiniz?"
MSG_NO_PROF = "Bu alanda şu an tanımlı bir uzman bulunmuyor; brifiniz Rumenova ekibine iletilecek."
MSG_SLOTS = ("Seçtiğiniz uzmanın uygun görüşme saatleri aşağıda. Size uygun olanı seçebilir ya da "
             "\"fark etmez\" diyebilirsiniz.")
MSG_NO_SLOTS = "Şu an tanımlı uygun saat bulunmuyor; görüşme saati uzmanla birlikte netleştirilecek."
MSG_SLOT_NOTE = "Görüşme saati tercihiniz kaydedildi. Seçtiğiniz saat, mimarın/ofisin teyidine sunulacaktır."
MSG_BRIEF_INTRO = "İşte verdiğiniz bilgilere göre hazırlanan ön görüşme brif özetiniz:"
MSG_BRIEF_CONFIRM = "Bilgiler doğruysa onaylayın; değiştirmek istediğiniz bir şey varsa \"düzelt\" yazın."
MSG_BRIEF_DONE = ("Brifiniz onaylandı. Sizi şimdi ön görüşme formumuza yönlendiriyorum: iletişim bilgilerinizi "
                  "bırakarak talebinizi tamamlayabilirsiniz. Seçtiğiniz görüşme saati, mimarın/ofisin teyidine "
                  "tabidir. Merak ettiğiniz başka bir şey olursa buradan sormaya devam edebilirsiniz.")
MSG_EDIT = "Hangi bilgiyi güncellemek istersiniz?"
MSG_NOT_UNDERSTOOD = "Tam olarak ne demek istediğinizi anlayamadım."
MSG_CHOOSE = "Lütfen seçeneklerden birini seçin ya da numarasını yazın."
MSG_SIDE_FALLBACK = "Bu konuyu ön görüşmede uzmanınızla ayrıntılı konuşabilirsiniz."
MSG_CONTINUE = "Kaldığımız yerden devam edelim:"

BRIEF_REQUEST_PREFIXES = ["brif", "randevu", "basvur"]
BRIEF_REQUEST_PHRASES = ["on gorusme", "formu doldur", "baslayalim", "basla"]


def form_url(token):
    return f"{WIX_FORM_URL}?session_token={token}"


def _option(label, action, value=None, **extra):
    opt = {"label": label, "action": action}
    if value is not None:
        opt["value"] = value
    opt.update({k: v for k, v in extra.items() if v})
    return opt


def _public_question(q):
    return {k: q.get(k) for k in ("id", "field", "question", "choices", "type") if q.get(k) is not None}


def _fallback_reply(text):
    n = nz.norm(text)
    if any(w in n.split() for w in ["merhaba", "selam", "slm", "gunaydin"]) or "iyi gunler" in n:
        return "Merhaba! Ben Rumenova'nın dijital asistanı Nova. Size projenizde nasıl yardımcı olabilirim?"
    return ("Projenizle ilgili detayları memnuniyetle dinlemek isterim. İhtiyacınızı kısaca anlatırsanız "
            "size en uygun uzmanla ön görüşme brifinizi oluşturabiliriz.")


def derive_stage(session):
    """flow_state'te aşama yoksa (eski /api/session akışı oturumları) aşamayı verilerden çıkarır."""
    if session.get("is_brief_approved"):
        return "tamamlandi"
    service = session.get("service_type")
    if not service:
        return "sohbet"
    if not (session.get("selected_expert_id") or session.get("selected_office_id")):
        return "uzman"
    skipped = (session.get("flow_state") or {}).get("skipped_fields", [])
    if AIService.get_next_question(service, session.get("collected_data") or {}, skipped):
        return "sorular"
    return "ozet" if session.get("selected_slot_text") else "saat"


def find_professional(expert_id=None, office_id=None):
    """Uzman (bağımsız veya ofis ekibi) ya da ofis kaydını bulur."""
    profs = get_all_professionals()
    if expert_id:
        for e in profs["experts"]:
            if e["id"] == expert_id:
                return {"type": "expert", "data": e, "office": None}
        for o in profs["offices"]:
            for tm in o.get("team_members", []):
                if tm["id"] == expert_id:
                    return {"type": "expert", "data": tm, "office": o}
    if office_id:
        for o in profs["offices"]:
            if o["id"] == office_id:
                return {"type": "office", "data": o, "office": o}
    return None


class ChatTurn:
    """Tek bir kullanıcı isteğinin işlenmesi: oturumu okur, işler, kaydeder."""

    def __init__(self, token=None):
        self.session = get_or_create_session(token)
        self.token = self.session["session_token"]
        self.state = self.session.get("flow_state") or {}
        self.state.setdefault("skipped_fields", [])
        self.state.setdefault("estimate_asked", {})
        self.state.setdefault("raw_answers", {})
        self.state.setdefault("prefill", {})
        self.collected = dict(self.session.get("collected_data") or {})
        self.history = list(self.session.get("chat_messages") or [])
        self.columns = {}
        self.out = []
        self.ui = {"type": "none", "options": []}
        if not self.state.get("stage"):
            self.state["stage"] = derive_stage(self.session)

    # --- Oturum yardımcıları ---

    @property
    def stage(self):
        return self.state["stage"]

    def get(self, key):
        return self.columns[key] if key in self.columns else self.session.get(key)

    def set(self, **cols):
        self.columns.update(cols)

    def merged_session(self):
        merged = dict(self.session)
        merged.update(self.columns)
        merged["collected_data"] = self.collected
        merged["flow_state"] = self.state
        return merged

    def _log(self, role, text):
        entry = {"role": role, "content": text, "stage": self.stage}
        if self.stage == "sorular" and self.state.get("current_field"):
            entry["field"] = self.state["current_field"]
        self.history.append(entry)

    def user(self, text):
        self._log("user", text)

    def say(self, text):
        self.out.append(text)
        self._log("assistant", text)

    def user_message_count(self):
        return sum(1 for m in self.history if m.get("role") == "user")

    def save(self):
        updates = dict(self.columns)
        updates.update({
            "collected_data": self.collected,
            "chat_messages": self.history,
            "flow_state": self.state
        })
        update_session(self.token, updates)

    def response(self, include_history=False):
        approved = bool(self.get("is_brief_approved"))
        res = {
            "success": True,
            "session_token": self.token,
            "stage": self.stage,
            "messages": [{"role": "assistant", "content": m} for m in self.out],
            "ui": self.ui,
            "is_brief_approved": approved,
            "form_url": form_url(self.token) if approved else None,
            "service_type": self.get("service_type"),
            "collected_data": self.collected
        }
        if include_history:
            res["history"] = [{"role": m.get("role"), "content": m.get("content")}
                              for m in self.history if m.get("content")]
        return res

    # --- Soru havuzu ---

    def service(self):
        return self.get("service_type")

    def next_question(self):
        service = self.service()
        if not service:
            return None
        editing = self.state.get("editing")
        if editing:
            q = AIService.get_question_by_field(service, editing)
            if q:
                return q
        return AIService.get_next_question(service, self.collected, self.state["skipped_fields"])

    def current_question(self):
        field = self.state.get("current_field")
        if field and self.service():
            return AIService.get_question_by_field(self.service(), field)
        return None

    def open_questions(self, exclude=None):
        """Henüz cevaplanmamış ve atlanmamış sorular (yapay zekânın ek bilgi çıkarması için)."""
        service = self.service()
        out = []
        for q in QUESTION_POOLS.get(service, []):
            f = q["field"]
            if f == exclude or self.collected.get(f) or f in self.state["skipped_fields"]:
                continue
            if q.get("type") == "media_and_notes":
                continue
            out.append(q)
        return out

    def store_extra_fields(self, extras, raw_text, source):
        valid = AIService.get_valid_fields(self.service()) if self.service() else set()
        for f, v in (extras or {}).items():
            if f in valid and not self.collected.get(f) and f not in self.state["skipped_fields"] \
                    and f != "gorsel_ve_ek":
                self.collected[f] = v
                self.state["raw_answers"][f] = {"ham": raw_text, "kaynak": source}

    def apply_prefill(self):
        """Serbest sohbette not alınan bilgileri, hizmet alanı belli olunca brife aktarır."""
        service = self.service()
        prefill = self.state.get("prefill") or {}
        if not service or not prefill:
            return
        valid = AIService.get_valid_fields(service)
        notes = []
        for f, v in list(prefill.items()):
            if f in valid and f != "gorsel_ve_ek" and not self.collected.get(f) \
                    and f not in self.state["skipped_fields"]:
                self.collected[f] = v
                self.state["raw_answers"][f] = {"ham": v, "kaynak": "sohbet"}
                notes.append(f"{field_label(f)}: {v}")
                prefill.pop(f)
        self.state["prefill"] = prefill
        if notes:
            self.say("Sohbetimizden not aldıklarım: " + "; ".join(notes) + ". Bunları tekrar sormayacağım.")

    # --- Aşamaya giriş: mesaj + ekranda gösterilecek seçenekler ---

    def enter(self, stage, emit=True):
        self.state["stage"] = stage
        handler = getattr(self, f"_enter_{stage}")
        handler(emit)
        return self

    def _enter_sohbet(self, emit):
        self.ui = {"type": "none", "options": [_option("Ön görüşme brifi oluştur", "start_brief")]}

    def _enter_tamamlandi(self, emit):
        if emit:
            self.say(MSG_BRIEF_DONE)
        url = form_url(self.token)
        self.ui = {"type": "form", "form_url": url,
                   "options": [_option("Ön Görüşme Formunu Tamamla", "open_url", url)]}

    def _enter_onay(self, emit):
        if emit:
            self.say(MSG_OFFER)
        self.ui = {"type": "consent", "options": [
            _option("Evet, başlayalım", "consent_yes"),
            _option("Şimdilik hayır", "consent_no")
        ]}

    def _service_choices(self):
        expert = find_professional(self.get("selected_expert_id"), self.get("selected_office_id"))
        if expert:
            areas = expert["data"].get("service_areas") or list(SERVICE_TITLES)
        else:
            areas = list(SERVICE_TITLES)
        suggested = self.state.get("suggested_service")
        if suggested in areas:
            areas = [suggested] + [a for a in areas if a != suggested]
        return [_option(SERVICE_TITLES.get(a, a), "select_service", a) for a in areas if a in SERVICE_TITLES]

    def _enter_hizmet(self, emit):
        options = self._service_choices()
        if len(options) == 1:
            # Uzman / ofis tek alanda hizmet veriyorsa sormadan devam et
            self.select_service(options[0]["value"], auto=True)
            return
        if emit:
            self.say(MSG_ASK_SERVICE)
        self.ui = {"type": "services", "options": options}

    def _enter_uzman(self, emit):
        profs = get_professionals_by_service(self.service())
        options = []
        for e in profs["experts"]:
            options.append(_option(e["name"], "select_expert", e["id"],
                                   subtitle=f"{e.get('title') or ''} • {e.get('location') or ''}".strip(" •"),
                                   image=e.get("avatar_url")))
        for o in profs["offices"]:
            team = ", ".join(t["name"] for t in o.get("team_members", []))
            options.append(_option(f"{o['name']} (Ofis)", "select_office", o["id"],
                                   subtitle=f"{o.get('location') or ''}{' • Ekip: ' + team if team else ''}"))
        if not options:
            if emit:
                self.say(MSG_NO_PROF)
            self.state["no_professional"] = True
            self.advance()
            return
        if emit:
            self.say(MSG_ASK_PROF)
        self.ui = {"type": "professionals", "options": options}

    def _team_options(self):
        office = find_professional(office_id=self.get("selected_office_id"))
        if not office:
            return []
        return [
            _option(m["name"], "select_expert", m["id"], subtitle=f"{m.get('title') or ''} • {office['data']['name']} Ekibi",
                    image=m.get("avatar_url"))
            for m in office["data"].get("team_members", [])
            if self.service() in m.get("service_areas", [])
        ]

    def _enter_ekip(self, emit):
        office = find_professional(office_id=self.get("selected_office_id"))
        if emit and office:
            self.say(f"{office['data']['name']} ekibimizden hangi uzmanımızla görüşmek istersiniz?")
        self.ui = {"type": "team", "options": self._team_options()}

    def _enter_sorular(self, emit):
        q = self.next_question()
        if not q:
            self.state["current_field"] = None
            self.advance()
            return
        self.state["current_field"] = q["field"]
        if emit:
            self.say(q["question"])
        if q.get("type") == "media_and_notes":
            images = self.get("uploaded_images") or []
            options = []
            if images:
                options.append(_option(f"Yüklenen {len(images)} görsel ile devam et", "media_done"))
            else:
                options.append(_option("Görsel paylaşmadan devam et", "media_skip"))
            self.ui = {"type": "media", "question": _public_question(q), "options": options,
                       "images": images, "max_images": 3}
            return
        self.ui = {"type": "question", "question": _public_question(q),
                   "options": [_option(c, "answer", c) for c in (q.get("choices") or [])]}

    def _enter_saat(self, emit):
        slots = get_available_slots(expert_id=self.get("selected_expert_id"), office_id=self.get("selected_office_id"))
        if not slots:
            if emit:
                self.say(MSG_NO_SLOTS)
            self.state["slot_skipped"] = True
            self.enter("ozet", emit)
            return
        if emit:
            self.say(MSG_SLOTS)
        options = [_option(f"{s['slot_date']} • {s['slot_time']}", "select_slot", s["id"]) for s in slots]
        options.append(_option("Fark etmez / esnek saat", "skip_slot"))
        self.ui = {"type": "slots", "options": options}

    def _enter_ozet(self, emit):
        summary = build_wix_summary_dict(self.merged_session())
        if emit:
            self.say(f"{MSG_BRIEF_INTRO}\n\n{summary['projeBrifi']}\n\n{MSG_BRIEF_CONFIRM}")
        self.ui = {"type": "brief", "brief": summary["projeBrifi"], "options": [
            _option("Bilgilerimi onaylıyorum", "approve"),
            _option("Düzeltmek istiyorum", "correct")
        ]}

    def _enter_duzelt(self, emit):
        if emit:
            self.say(MSG_EDIT)
        options = []
        for q in QUESTION_POOLS.get(self.service(), []):
            f = q["field"]
            if self.collected.get(f) or f in self.state["skipped_fields"]:
                options.append(_option(field_label(f), "edit_field", f))
        options.append(_option("Görüşme saati", "edit_slot"))
        options.append(_option("Özete geri dön", "back_to_brief"))
        self.ui = {"type": "edit", "options": options}

    # --- Akış ---

    def advance(self):
        """Verilere göre bir sonraki eksik adıma geçer."""
        if not self.service():
            return self.enter("hizmet")
        if not (self.get("selected_expert_id") or self.get("selected_office_id")) \
                and not self.state.get("no_professional"):
            return self.enter("uzman")
        if self.get("selected_office_id") and not self.get("selected_expert_id") \
                and not self.state.get("office_only"):
            office = find_professional(office_id=self.get("selected_office_id"))
            team = self._team_options()
            if len(team) > 1:
                return self.enter("ekip")
            name = office["data"]["name"] if office else "Ofis"
            if len(team) == 1:
                self.set(selected_expert_id=team[0]["value"], selected_team_member_id=team[0]["value"])
                self.say(f"{name} ekibinden {team[0]['label']} ile ön görüşmenize başlayalım.")
            else:
                self.state["office_only"] = True
                self.say(f"{name} ile ön görüşmenize başlayalım.")
        if self.next_question():
            return self.enter("sorular")
        if not self.get("selected_slot_text") and not self.state.get("slot_skipped") \
                and not self.state.get("no_professional"):
            return self.enter("saat")
        return self.enter("ozet")

    def can_offer(self):
        declined_at = self.state.get("offer_declined_at")
        return declined_at is None or self.user_message_count() - declined_at >= OFFER_COOLDOWN

    def start_brief(self):
        self.state.pop("offer_declined_at", None)
        self.state["brief_started"] = True
        self.say(MSG_BRIEF_START)
        self.apply_prefill()
        return self.advance()

    def decline(self):
        self.state["offer_declined_at"] = self.user_message_count()
        self.say(MSG_OFFER_DECLINED)
        return self.enter("sohbet", emit=False)

    def select_service(self, service, auto=False):
        if service not in SERVICE_TITLES:
            return self.enter("hizmet", emit=False)
        self.set(service_type=service)
        self.state.pop("suggested_service", None)
        if auto:
            self.say(f"{SERVICE_TITLES[service]} alanında ilerliyoruz.")
        self.apply_prefill()
        return self.advance()

    def select_expert(self, expert_id):
        try:
            expert_id = int(expert_id)
        except (TypeError, ValueError):
            return self.enter(self.stage, emit=False)
        found = find_professional(expert_id=expert_id)
        if not found:
            return self.enter(self.stage, emit=False)
        self.set(selected_expert_id=expert_id)
        if found["office"]:
            self.set(selected_office_id=found["office"]["id"], selected_team_member_id=expert_id)
        service_title = SERVICE_TITLES.get(self.service(), "")
        self.say(f"{found['data']['name']} ile {service_title.lower()} alanında ön görüşmenize başlıyoruz.")
        return self.advance()

    def select_office(self, office_id):
        try:
            office_id = int(office_id)
        except (TypeError, ValueError):
            return self.enter(self.stage, emit=False)
        found = find_professional(office_id=office_id)
        if not found:
            return self.enter(self.stage, emit=False)
        self.set(selected_office_id=office_id, selected_expert_id=None, selected_team_member_id=None)
        self.state.pop("office_only", None)
        return self.advance()

    def finish_answer(self, field):
        self.state["estimate_asked"].pop(field, None)
        self.state["editing"] = None
        self.state["current_field"] = None
        return self.advance()

    def answer(self, text, exact=False):
        q = self.current_question()
        if not q:
            return self.advance()
        field = q["field"]
        choices = q.get("choices") or []

        if q.get("type") == "media_and_notes":
            self.collected[field] = nz.clean_free_text(text)
            self.state["raw_answers"][field] = {"ham": text}
            return self.finish_answer(field)

        result = None
        if exact:
            result = {"tur": "cevap", "deger": text, "ek_bilgiler": {}}
        elif choices and text.strip().isdigit() and field not in NO_DIGIT_CHOICE_FIELDS \
                and 1 <= int(text.strip()) <= len(choices):
            result = {"tur": "cevap", "deger": choices[int(text.strip()) - 1], "ek_bilgiler": {}}
        elif any(nz.norm(text) == nz.norm(c) for c in choices):
            result = {"tur": "cevap", "deger": next(c for c in choices if nz.norm(text) == nz.norm(c)), "ek_bilgiler": {}}
        if result is None:
            result = ai_service.cevabi_yorumla(
                q, text, self.service(), self.collected, self.open_questions(exclude=field), self.history[:-1]
            )
            source = "yapay_zeka"
            if result is None:
                result = nz.interpret_answer(q, text)
                source = "kural"
        else:
            source = "secenek"

        tur = result["tur"]
        if tur == "atla":
            if field not in self.state["skipped_fields"]:
                self.state["skipped_fields"].append(field)
            self.collected.pop(field, None)
            self.say(Config.MSG_SKIPPED)
            return self.finish_answer(field)

        if tur == "belirsiz":
            if field in ESTIMATE_FIELDS and not self.state["estimate_asked"].get(field):
                self.state["estimate_asked"][field] = True
                self.say(Config.MSG_ESTIMATE_REQUEST)
                return self.enter("sorular", emit=False)
            self.collected[field] = Config.VALUE_TO_DISCUSS
            self.state["raw_answers"][field] = {"ham": text, "kaynak": source}
            self.say(Config.MSG_ESTIMATE_NOTED)
            return self.finish_answer(field)

        if tur == "yan_soru":
            reply = result.get("yanit") or ai_service.kisa_yanit(text, self.history[:-1]) or MSG_SIDE_FALLBACK
            self.say(f"{reply}\n\n{MSG_CONTINUE} {q['question']}")
            return self.enter("sorular", emit=False)

        if tur == "anlamsiz":
            self.say(f"{MSG_NOT_UNDERSTOOD} {q['question']}")
            return self.enter("sorular", emit=False)

        value = result.get("deger") or nz.clean_free_text(text)
        exact_choice = next((c for c in choices if nz.norm(c) == nz.norm(value)), None)
        value = exact_choice or value
        if field in self.state["skipped_fields"]:
            self.state["skipped_fields"].remove(field)
        self.collected[field] = value
        self.state["raw_answers"][field] = {"ham": text, "kaynak": source}
        self.store_extra_fields(result.get("ek_bilgiler"), text, source)
        return self.finish_answer(field)

    def chat(self, text):
        """Serbest sohbet (ve brif sonrası sohbet): yapay zekâ yanıtı + niyet tespiti."""
        done = self.stage == "tamamlandi"
        brief_text = None
        if done:
            brief_text = (self.get("brief_summary") or {}).get("projeBrifi")
        result = ai_service.sohbet_analizi(text, self.history[:-1], self.service(), done, brief_text)
        if result is None:
            result = {
                "yanit": _fallback_reply(text),
                "proje_talebi": not done and nz.looks_like_project_request(text),
                "hizmet": nz.detect_service(text),
                "bilgiler": nz.extract_prefill(text)
            }

        known = {q["field"] for pool in QUESTION_POOLS.values() for q in pool}
        for f, v in (result.get("bilgiler") or {}).items():
            if f in known and f != "gorsel_ve_ek" and not self.collected.get(f):
                self.state["prefill"][f] = v
        if result.get("hizmet") and not self.service():
            self.state["suggested_service"] = result["hizmet"]

        self.say(result["yanit"])
        if done:
            return self.enter("tamamlandi", emit=False)
        if self.stage == "onay":
            return self.enter("onay", emit=False)
        if result.get("proje_talebi") and self.can_offer():
            return self.enter("onay")
        return self.enter("sohbet", emit=False)

    def side_or_reprompt(self, text):
        """Seçim beklenen aşamalarda anlaşılmayan mesaj: yan soruysa yanıtla, değilse seçenekleri hatırlat."""
        if nz.is_side_question(text):
            reply = ai_service.kisa_yanit(text, self.history[:-1]) or MSG_SIDE_FALLBACK
            self.say(reply)
        else:
            self.say(MSG_CHOOSE)
        return self.enter(self.stage, emit=False)

    def wants_brief(self, text):
        n = nz.norm(text)
        if nz.is_side_question(text):
            return False
        return any(w.startswith(p) for w in n.split() for p in BRIEF_REQUEST_PREFIXES) \
            or nz._contains_phrase(n, BRIEF_REQUEST_PHRASES)

    # --- Giriş noktaları ---

    def handle_text(self, text):
        self.user(text)
        stage = self.stage

        if stage == "sohbet":
            if self.wants_brief(text):
                return self.start_brief()
            return self.chat(text)
        if stage == "tamamlandi":
            return self.chat(text)
        if stage == "onay":
            if nz.is_yes(text):
                return self.start_brief()
            if nz.is_no(text):
                return self.decline()
            return self.chat(text)
        if stage == "sorular":
            return self.answer(text)
        if stage == "hizmet":
            opt = nz.match_option(text, self._service_choices())
            service = opt["value"] if opt else nz.detect_service(text)
            if service:
                return self.select_service(service)
            return self.side_or_reprompt(text)
        if stage == "saat" and (nz.is_uncertain(text) or nz.is_skip(text)):
            return self.handle_action("skip_slot", echo=False)
        if stage == "ozet":
            n = nz.norm(text)
            if any(w in n for w in ["duzelt", "degistir", "guncelle"]) or nz.is_no(text):
                return self.handle_action("correct", echo=False)
            if nz.is_yes(text):
                return self.handle_action("approve", echo=False)
            return self.side_or_reprompt(text)
        if stage in ("uzman", "ekip", "saat", "duzelt"):
            self.enter(stage, emit=False)
            opt = nz.match_option(text, self.ui["options"])
            if opt:
                return self.handle_action(opt["action"], opt.get("value"), echo=False)
            return self.side_or_reprompt(text)
        return self.chat(text)

    ALLOWED_ACTIONS = {
        "sohbet": {"start_brief"},
        "onay": {"consent_yes", "consent_no", "start_brief"},
        "hizmet": {"select_service"},
        "uzman": {"select_expert", "select_office"},
        "ekip": {"select_expert"},
        "sorular": {"answer", "media_skip", "media_done"},
        "saat": {"select_slot", "skip_slot"},
        "ozet": {"approve", "correct"},
        "duzelt": {"edit_field", "edit_slot", "back_to_brief"},
        "tamamlandi": frozenset()
    }

    def handle_action(self, action, value=None, label=None, echo=True):
        if action not in self.ALLOWED_ACTIONS.get(self.stage, frozenset()):
            # Eski bir butona basıldı: mevcut aşamanın seçeneklerini yeniden göster
            return self.enter(self.stage, emit=False)
        if echo:
            self.user(label or (str(value) if value is not None else action))

        if action in ("start_brief", "consent_yes"):
            return self.start_brief()
        if action == "consent_no":
            return self.decline()
        if action == "select_service":
            return self.select_service(value)
        if action == "select_expert":
            return self.select_expert(value)
        if action == "select_office":
            return self.select_office(value)
        if action == "answer":
            return self.answer(str(value or ""), exact=True)
        if action == "media_skip":
            return self._media_answer("Yok")
        if action == "media_done":
            count = len(self.get("uploaded_images") or [])
            return self._media_answer(f"{count} adet referans görsel yüklendi")
        if action == "select_slot":
            slots = get_available_slots(expert_id=self.get("selected_expert_id"),
                                        office_id=self.get("selected_office_id"))
            slot = next((s for s in slots if str(s["id"]) == str(value)), None)
            if not slot:
                self.say("Bu saat artık uygun değil, lütfen başka bir saat seçin.")
                return self.enter("saat", emit=False)
            self.set(selected_slot_id=slot["id"], selected_slot_text=f"{slot['slot_date']} • {slot['slot_time']}")
            self.state["slot_skipped"] = False
            self.say(MSG_SLOT_NOTE)
            return self.enter("ozet")
        if action == "skip_slot":
            self.set(selected_slot_id=None, selected_slot_text=None)
            self.state["slot_skipped"] = True
            return self.enter("ozet")
        if action == "approve":
            return self.approve()
        if action == "correct":
            return self.enter("duzelt")
        if action == "edit_field":
            if value not in AIService.get_valid_fields(self.service()):
                return self.enter("duzelt", emit=False)
            self.state["editing"] = value
            if value in self.state["skipped_fields"]:
                self.state["skipped_fields"].remove(value)
            return self.enter("sorular")
        if action == "edit_slot":
            self.set(selected_slot_id=None, selected_slot_text=None)
            self.state["slot_skipped"] = False
            return self.enter("saat")
        if action == "back_to_brief":
            return self.enter("ozet")
        return self.enter(self.stage, emit=False)

    def _media_answer(self, value):
        q = self.current_question()
        if not q:
            return self.advance()
        self.collected[q["field"]] = value
        return self.finish_answer(q["field"])

    def approve(self):
        self.set(is_brief_approved=1, status="brif_onaylandi")
        self.enter("tamamlandi")
        self.save()
        save_brief_snapshot(self.token)
        return self

    def apply_entry_presets(self, data):
        """Profil butonlarından gelen expert_code / office_code / service (yalnızca brif başlamadan)."""
        if self.get("is_brief_approved") or self.get("selected_expert_id") or self.get("selected_office_id"):
            return None
        preset = None
        code = data.get("expert_code") or data.get("office_code")
        found = get_expert_or_office_by_code(code) if code else None
        if found and found["type"] == "expert" and data.get("expert_code"):
            exp = found["data"]
            self.set(selected_expert_id=exp["id"])
            if exp.get("office_id"):
                self.set(selected_office_id=exp["office_id"], selected_team_member_id=exp["id"])
            if len(exp["service_areas"]) == 1:
                self.set(service_type=exp["service_areas"][0])
            preset = exp["name"]
        elif found and found["type"] == "office" and data.get("office_code"):
            off = found["data"]
            self.set(selected_office_id=off["id"])
            if len(off["service_areas"]) == 1:
                self.set(service_type=off["service_areas"][0])
            preset = off["name"]
        if data.get("service") in SERVICE_TITLES and not self.get("service_type"):
            self.set(service_type=data["service"])
        return preset


def chat_init(data):
    """Sohbeti açar veya kaldığı yerden yükler. Yeni oturumda karşılama mesajı üretir."""
    turn = ChatTurn(data.get("session_token"))
    is_new = not turn.history
    preset = turn.apply_entry_presets(data) if is_new else None

    if is_new:
        if preset:
            service_title = SERVICE_TITLES.get(turn.service())
            area = f" {service_title.lower()} alanında" if service_title else ""
            turn.say(f"Merhaba, ben Nova. {preset} ile{area} ön görüşmeniz için buradayım.")
            turn.enter("onay")
        else:
            turn.say(MSG_WELCOME)
            turn.enter("sohbet", emit=False)
    else:
        turn.enter(turn.stage, emit=False)

    turn.save()
    return turn.response(include_history=True)


def chat_turn(data):
    """Kullanıcı mesajı (message) veya buton seçimi (action, value, label) işler."""
    turn = ChatTurn(data.get("session_token"))
    action = data.get("action")
    message = str(data.get("message") or "").strip()[:MAX_MESSAGE_LENGTH]

    if action:
        turn.handle_action(action, data.get("value"), data.get("label"))
    elif message:
        turn.handle_text(message)
    else:
        turn.enter(turn.stage, emit=False)

    turn.save()
    return turn.response()
