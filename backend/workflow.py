"""Rule-first WhatsApp booking workflow.

Groq is used only to extract JSON when regex/keywords cannot parse the user.
Replies and bookings are never invented by the model.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

YES = {
    "yes", "y", "ok", "okay", "sure", "haan", "ha", "han", "ji", "जी", "हां", "हाँ",
    "confirm", "book",
}
NO = {"no", "n", "nahi", "nahin", "nope", "नहीं", "ना"}
CANCEL_KEYS = ("cancel", "radd", "रद्द")
RESCHEDULE_KEYS = ("reschedule", "change time", "postpone", "shift", "badal", "badlo")
RESTART = {"hi", "hello", "hey", "menu", "start", "restart", "namaste", "namaskar", "hii"}
FAQ_HOURS = ("hours", "timing", "timings", "open", "kitne baje", "working hours")


def t(lang: str, en: str, hi: str) -> str:
    return hi if lang == "hi" else en


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def detect_language(text: str):
    n = normalize(text)
    if n in {"1", "en", "eng", "english", "angrezi"}:
        return "en"
    if n in {"2", "hin", "hindi", "हिंदी", "हिन्दी"}:
        return "hi"
    if "english" in n:
        return "en"
    if "hindi" in n or "हिंद" in n:
        return "hi"
    return None


def is_yes(text: str) -> bool:
    n = normalize(text)
    return n in YES or n.startswith("yes") or n.startswith("haan")


def is_no(text: str) -> bool:
    n = normalize(text)
    return n in NO or n.startswith("nahi") or n == "no"


def is_cancel(text: str) -> bool:
    n = normalize(text)
    return any(k in n for k in CANCEL_KEYS)


def is_reschedule(text: str) -> bool:
    n = normalize(text)
    return any(k in n for k in RESCHEDULE_KEYS)


def is_restart(text: str) -> bool:
    return normalize(text) in RESTART


def is_hours_faq(text: str) -> bool:
    n = normalize(text)
    return any(k in n for k in FAQ_HOURS)


def parse_date_time(text: str, now: datetime):
    """Return (YYYY-MM-DD|None, HH:MM|None) from common EN/HI phrases."""
    n = normalize(text)
    date_str = None
    time_str = None

    if re.search(r"\b(aaj|today)\b", n):
        date_str = now.strftime("%Y-%m-%d")
    elif re.search(r"\b(kal|tomorrow|tommorow|tommorrow)\b", n):
        date_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    elif re.search(r"\b(parso|day after)\b", n):
        date_str = (now + timedelta(days=2)).strftime("%Y-%m-%d")

    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", n)
    if m:
        date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    else:
        m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", n)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
            year = int(y) if y else now.year
            if year < 100:
                year += 2000
            try:
                date_str = datetime(year, mo, d).strftime("%Y-%m-%d")
            except ValueError:
                try:
                    date_str = datetime(year, d, mo).strftime("%Y-%m-%d")
                except ValueError:
                    pass

    m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", n)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        ap = m.group(3)
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= mi <= 59:
            time_str = f"{h:02d}:{mi:02d}"
    else:
        m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", n)
        if m:
            h = int(m.group(1))
            if m.group(2) == "pm" and h < 12:
                h += 12
            if m.group(2) == "am" and h == 12:
                h = 0
            time_str = f"{h:02d}:00"

    if not time_str:
        if re.search(r"\b(subah|morning|savera)\b", n):
            time_str = "10:00"
        elif re.search(r"\b(dopahar|afternoon)\b", n):
            time_str = "14:00"
        elif re.search(r"\b(shaam|sham|evening|saanjh)\b", n):
            time_str = "17:00"
        elif re.search(r"\b(raat|night)\b", n):
            time_str = "19:00"

    return date_str, time_str


def looks_like_name(text: str) -> bool:
    raw = (text or "").strip()
    if not raw or not (2 <= len(raw) <= 40):
        return False
    if detect_language(raw) or is_yes(raw) or is_no(raw) or is_cancel(raw):
        return False
    if re.search(r"\d", raw):
        return False
    d, tm = parse_date_time(raw, datetime(2026, 1, 1))
    if d or tm:
        return False
    return bool(re.fullmatch(r"[a-zA-Z\u0900-\u097F .']{2,40}", raw))


def extract_name(text: str) -> str:
    raw = (text or "").strip()
    cleaned = re.sub(
        r"^(my name is|naam(?:\s+hai)?|name is|i am|i'm|main)\s+",
        "",
        raw,
        flags=re.I,
    ).strip(" .")
    return cleaned or raw


def match_clinic(text: str, clinics: list):
    n = normalize(text)
    if not clinics:
        return None
    if n.isdigit():
        idx = int(n) - 1
        if 0 <= idx < len(clinics):
            return clinics[idx]
    for c in clinics:
        name = normalize(c.get("business_name") or "")
        if name and (name == n or name in n or n in name):
            return c
    return None


def clinic_list_text(clinics: list, lang: str) -> str:
    if not clinics:
        return t(lang, "No clinics are available right now.", "अभी कोई क्लिनिक उपलब्ध नहीं है।")
    lines = []
    for i, c in enumerate(clinics, 1):
        if c.get("booking_mode") == "token":
            mode = "टोकन कतार" if lang == "hi" else "token queue"
            extra = f" (#{c.get('current_serving_token') or 0} serving)"
        else:
            mode = "समय स्लॉट" if lang == "hi" else "timed slots"
            extra = ""
        lines.append(f"{i}. {c.get('business_name')} — {mode}{extra}")
    return "\n".join(lines)


def hours_text(clinic: dict, lang: str) -> str:
    wh = clinic.get("working_hours") or {}
    start, end = wh.get("start", "09:00"), wh.get("end", "21:00")
    name = clinic.get("business_name") or "clinic"
    return t(lang, f"{name} hours: {start}–{end}.", f"{name} का समय: {start}–{end}।")


def default_workflow(patient_name: str = "") -> dict:
    return {
        "step": "language",
        "language": None,
        "clinic_id": None,
        "clinic_name": None,
        "booking_mode": None,
        "patient_name": patient_name or None,
    }


def groq_extract(client, text: str, now: datetime, clinics: list) -> dict:
    names = [c.get("business_name") for c in clinics]
    prompt = (
        "Extract booking fields. Reply with JSON only, no markdown.\n"
        '{"intent":"book|cancel|reschedule|faq|other|clinic|name|datetime|yes|no",'
        '"clinic_name":"","patient_name":"","date":"YYYY-MM-DD or empty",'
        '"time":"HH:MM 24h or empty"}\n'
        f"Now: {now.strftime('%Y-%m-%d %H:%M')}\n"
        f"Clinics: {names}\n"
        f"User: {text}"
    )
    for model in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You only output valid JSON. You never confirm a booking."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=200,
            )
            raw = (resp.choices[0].message.content or "").strip()
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"groq_extract {model} failed: {e}")
    return {}


def _clinic_by_id(clinics, clinic_id):
    for c in clinics:
        if c.get("id") == clinic_id:
            return c
    return None


def _prompt_after_identity(wf, clinics, lang):
    clinic = _clinic_by_id(clinics, wf.get("clinic_id"))
    if (wf.get("booking_mode") or "scheduled") == "token":
        wf["step"] = "token_confirm"
        serving = (clinic or {}).get("current_serving_token") or 0
        waiting = (clinic or {}).get("waiting_queue") or 0
        last = (clinic or {}).get("last_token") or 0
        return t(
            lang,
            f"{wf.get('clinic_name')} is a walk-in token clinic (today only).\nNow serving #{serving}, last #{last}, waiting ~{waiting}.\nReply YES for a token, NO to skip.",
            f"{wf.get('clinic_name')} टोकन क्लिनिक है (केवल आज)।\nअभी #{serving}, आखिरी #{last}, प्रतीक्षा ~{waiting}।\nटोकन के लिए YES, नहीं तो NO।",
        )
    wf["step"] = "datetime"
    return t(
        lang,
        f"Got it, {wf.get('patient_name')}. Send date and time (e.g. tomorrow 5pm).",
        f"ठीक है, {wf.get('patient_name')}। तारीख और समय भेजें (जैसे: कल शाम 5 बजे)।",
    )


def handle_turn(text, wf, clinics, phone, now, tools, groq_client=None):
    """
    Returns (reply_text, updated_workflow, used_groq).
    tools: book_slot, generate_token, cancel_appointment, reschedule_slot, check_availability
    """
    wf = dict(wf or default_workflow())
    lang = wf.get("language") or "en"
    used_groq = False

    if wf.get("step") != "language":
        if is_restart(text):
            keep_lang, keep_name = wf.get("language"), wf.get("patient_name")
            wf = default_workflow(keep_name or "")
            wf["language"] = keep_lang
            wf["step"] = "clinic"
            lang = keep_lang or "en"
            return (
                t(lang, "Let's start again. Choose a clinic:\n", "फिर से शुरू करते हैं। क्लिनिक चुनें:\n")
                + clinic_list_text(clinics, lang),
                wf,
                False,
            )
        if is_cancel(text) and wf.get("clinic_id"):
            result = tools["cancel_appointment"](wf["clinic_id"], phone)
            if result.get("status") == "success":
                wf["step"] = "idle"
            return t(lang, result.get("message", "Could not cancel."), result.get("message", "रद्द नहीं हो सका।")), wf, False
        if is_hours_faq(text) and _clinic_by_id(clinics, wf.get("clinic_id")):
            return hours_text(_clinic_by_id(clinics, wf.get("clinic_id")), lang), wf, False

    step = wf.get("step") or "language"

    if step == "language":
        detected = detect_language(text)
        if not detected:
            return (
                "Welcome to Sanwariya Tech booking.\n"
                "Choose language / भाषा चुनें:\n"
                "1. English\n"
                "2. हिन्दी",
                wf,
                False,
            )
        wf["language"] = detected
        lang = detected
        wf["step"] = "clinic"
        return (
            t(lang, "Choose a clinic (number or name):\n", "क्लिनिक चुनें (नंबर या नाम):\n")
            + clinic_list_text(clinics, lang),
            wf,
            False,
        )

    if step == "clinic":
        chosen = match_clinic(text, clinics)
        if not chosen and groq_client:
            extracted = groq_extract(groq_client, text, now, clinics)
            used_groq = True
            if extracted.get("clinic_name"):
                chosen = match_clinic(extracted["clinic_name"], clinics)
        if not chosen:
            return (
                t(lang, "Please pick a clinic from this list:\n", "कृपया सूची से क्लिनिक चुनें:\n")
                + clinic_list_text(clinics, lang),
                wf,
                used_groq,
            )
        wf["clinic_id"] = chosen["id"]
        wf["clinic_name"] = chosen.get("business_name")
        wf["booking_mode"] = chosen.get("booking_mode") or "scheduled"
        if not wf.get("patient_name"):
            wf["step"] = "name"
            return t(lang, "What is the patient's name?", "मरीज का नाम क्या है?"), wf, used_groq
        return _prompt_after_identity(wf, clinics, lang), wf, used_groq

    if step == "name":
        candidate = extract_name(text)
        if looks_like_name(candidate):
            wf["patient_name"] = candidate
            return _prompt_after_identity(wf, clinics, lang), wf, False
        return t(lang, "Please send the patient's name (letters only).", "कृपया मरीज का नाम भेजें।"), wf, False

    if step == "datetime":
        if is_reschedule(text):
            wf["step"] = "reschedule_datetime"
            return t(lang, "What new date and time?", "नई तारीख और समय क्या है?"), wf, False
        date_str, time_str = parse_date_time(text, now)
        if (not date_str or not time_str) and groq_client:
            extracted = groq_extract(groq_client, text, now, clinics)
            used_groq = True
            date_str = date_str or extracted.get("date") or None
            time_str = time_str or extracted.get("time") or None
            if date_str == "":
                date_str = None
            if time_str == "":
                time_str = None
        if not date_str or not time_str:
            return t(lang, "Please send both date and time, e.g. tomorrow 5pm.", "कृपया तारीख और समय दोनों भेजें, जैसे: कल शाम 5 बजे।"), wf, used_groq
        avail = tools["check_availability"](wf["clinic_id"], date_str)
        if avail.get("status") == "success" and time_str not in (avail.get("all_available_slots") or []):
            suggested = ", ".join((avail.get("suggested_available_slots") or [])[:5]) or "none"
            return t(lang, f"{time_str} is not free on {date_str}. Try: {suggested}", f"{date_str} को {time_str} खाली नहीं है। ये स्लॉट आज़माएँ: {suggested}"), wf, used_groq
        result = tools["book_slot"](wf["clinic_id"], phone, date_str, time_str, wf.get("patient_name") or "Unknown")
        if result.get("status") == "success":
            wf["step"] = "idle"
            booked = result.get("slot_start") or f"{date_str} {time_str}"
            return t(
                lang,
                f"Booked for {wf.get('patient_name')} at {wf.get('clinic_name')} on {booked}. Reply CANCEL to cancel, or hi for a new booking.",
                f"{wf.get('patient_name')} की बुकिंग {wf.get('clinic_name')} में {booked} पर हो गई। रद्द: CANCEL।",
            ), wf, used_groq
        return t(lang, result.get("message", "Could not book."), result.get("message", "बुकिंग नहीं हो सकी।")), wf, used_groq

    if step == "token_confirm":
        if is_yes(text):
            result = tools["generate_token"](wf["clinic_id"], phone, wf.get("patient_name") or "Unknown")
            wf["step"] = "idle"
            return t(lang, result.get("message", "Done."), result.get("message", "हो गया।")), wf, False
        if is_no(text):
            wf["step"] = "idle"
            return t(lang, "Okay, no token issued. Send hi to start again.", "ठीक है। फिर से शुरू करने के लिए hi लिखें।"), wf, False
        return t(lang, "Reply YES for a token today, or NO to skip.", "आज का टोकन: YES, नहीं तो NO।"), wf, False

    if step == "reschedule_datetime":
        date_str, time_str = parse_date_time(text, now)
        if (not date_str or not time_str) and groq_client:
            extracted = groq_extract(groq_client, text, now, clinics)
            used_groq = True
            date_str = date_str or extracted.get("date") or None
            time_str = time_str or extracted.get("time") or None
        if not date_str or not time_str:
            return t(lang, "Send the new date and time, e.g. tomorrow 5pm.", "नई तारीख और समय भेजें, जैसे: कल शाम 5 बजे।"), wf, used_groq
        result = tools["reschedule_slot"](wf["clinic_id"], phone, date_str, time_str)
        if result.get("status") == "success":
            wf["step"] = "idle"
        return t(lang, result.get("message", ""), result.get("message", "")), wf, used_groq

    if step == "idle":
        if is_reschedule(text):
            if wf.get("booking_mode") == "token":
                return t(lang, "Token visits cannot be moved. Cancel, then take a new token.", "टोकन का समय नहीं बदला जा सकता। पहले रद्द करें।"), wf, False
            wf["step"] = "reschedule_datetime"
            return t(lang, "What new date and time?", "नई तारीख और समय क्या है?"), wf, False
        wf["step"] = "clinic"
        return t(lang, "Choose a clinic:\n", "क्लिनिक चुनें:\n") + clinic_list_text(clinics, lang), wf, False

    return t(lang, "Send hi to start booking.", "बुकिंग के लिए hi लिखें।"), wf, used_groq
