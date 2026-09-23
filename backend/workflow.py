"""V2 WhatsApp booking workflow — interactive buttons & list messages.

Key design principles:
- Language, clinic, menu, slot selection all use WhatsApp interactive messages
- Quick Reply buttons (max 3) for simple yes/no/confirm choices
- List messages (max 10 rows) for menus and slot selection
- Groq is used only as a fallback name/date extractor
- Bookings are never invented by the AI
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

# Interactive reply IDs
ID_LANG_EN = "lang_en"
ID_LANG_HI = "lang_hi"
ID_BOOK = "book"
ID_TIMING = "timing"
ID_FEE = "fee"
ID_LOCATION = "location"
ID_DOCTOR_STATUS = "doctor_status"
ID_CANCEL = "cancel"
ID_TOKEN_CONFIRM = "token_yes"
ID_TOKEN_BACK = "token_no"
ID_TODAY = "date_today"
ID_TOMORROW = "date_tomorrow"
ID_DAY_AFTER = "date_day_after"
ID_CONFIRM = "booking_confirm"
ID_ABORT = "booking_abort"
ID_BACK = "back_menu"


def t(lang: str, en: str, hi: str) -> str:
    return hi if lang == "hi" else en


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def detect_language(text: str):
    n = normalize(text)
    if n in {"1", "en", "eng", "english", "angrezi"} or n == ID_LANG_EN:
        return "en"
    if n in {"2", "hin", "hindi", "हिंदी", "हिन्दी"} or n == ID_LANG_HI:
        return "hi"
    if "english" in n:
        return "en"
    if "hindi" in n or "हिंद" in n:
        return "hi"
    return None


def is_yes(text: str) -> bool:
    n = normalize(text)
    return n in YES or n.startswith("yes") or n.startswith("haan") or n == ID_TOKEN_CONFIRM or n == ID_CONFIRM


def is_no(text: str) -> bool:
    n = normalize(text)
    return n in NO or n.startswith("nahi") or n == "no" or n in {ID_TOKEN_BACK, ID_ABORT}


def is_cancel(text: str) -> bool:
    n = normalize(text)
    return any(k in n for k in CANCEL_KEYS) or n == ID_CANCEL


def is_reschedule(text: str) -> bool:
    n = normalize(text)
    return any(k in n for k in RESCHEDULE_KEYS)


def is_restart(text: str) -> bool:
    return normalize(text) in RESTART


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
    # Exclude button/list reply IDs
    if raw.startswith(("lang_", "date_", "slot_", "booking_", "token_", "back_")):
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

    return date_str, time_str


def _clinic_by_id(clinics, clinic_id):
    for c in clinics:
        if c.get("id") == clinic_id:
            return c
    return None


def default_workflow(patient_name: str = "") -> dict:
    return {
        "step": "language",
        "language": None,
        "clinic_id": None,
        "clinic_name": None,
        "booking_mode": None,
        "patient_name": patient_name or None,
        "pending_date": None,
        "pending_time": None,
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


def _build_language_list(lang: str) -> dict:
    """Returns an interactive LIST payload for language selection."""
    return {
        "type": "interactive",
        "interactive_type": "list",
        "header": "Welcome to Sanwariya Clinic Booking 👋",
        "body": "Please select your preferred language / कृपया अपनी भाषा चुनें:",
        "button_label": "Select Language",
        "rows": [
            {"id": ID_LANG_EN, "title": "🇬🇧 English", "description": "Continue in English"},
            {"id": ID_LANG_HI, "title": "🇮🇳 हिन्दी", "description": "हिंदी में जारी रखें"},
        ],
    }


def _build_clinic_list(clinics: list, lang: str) -> dict:
    """Returns an interactive LIST payload for clinic selection."""
    rows = []
    for c in clinics[:10]:
        mode = t(lang, "Token queue" if c.get("booking_mode") == "token" else "Timed slots",
                      "टोकन कतार" if c.get("booking_mode") == "token" else "समय स्लॉट")
        rows.append({
            "id": f"clinic_{c['id']}",
            "title": c.get("business_name", "Clinic")[:24],
            "description": mode,
        })
    return {
        "type": "interactive",
        "interactive_type": "list",
        "header": t(lang, "Choose a Clinic", "क्लिनिक चुनें"),
        "body": t(lang, "Select the clinic you'd like to visit:", "किस क्लिनिक में जाना है?"),
        "button_label": t(lang, "View Clinics", "क्लिनिक देखें"),
        "rows": rows,
    }


def _build_main_menu(clinic: dict, lang: str) -> dict:
    """Returns an interactive LIST payload for the main clinic menu."""
    name = clinic.get("business_name", "Clinic")
    return {
        "type": "interactive",
        "interactive_type": "list",
        "header": f"🏥 {name}",
        "body": t(lang, "What would you like to do?", "आप क्या करना चाहते हैं?"),
        "button_label": t(lang, "View Options", "विकल्प देखें"),
        "rows": [
            {"id": ID_BOOK, "title": t(lang, "📅 Book Appointment", "📅 अपॉइंटमेंट बुक करें"),
             "description": t(lang, "Get a slot or token", "स्लॉट या टोकन लें")},
            {"id": ID_TIMING, "title": t(lang, "🕐 Clinic Hours", "🕐 क्लिनिक का समय"),
             "description": t(lang, "Opening & closing time", "खुलने-बंद होने का समय")},
            {"id": ID_FEE, "title": t(lang, "💰 Consultation Fee", "💰 परामर्श शुल्क"),
             "description": t(lang, "Doctor's charges", "डॉक्टर की फीस")},
            {"id": ID_LOCATION, "title": t(lang, "📍 Location / Maps", "📍 स्थान / नक्शा"),
             "description": t(lang, "Get Google Maps link", "गूगल मैप्स लिंक पाएं")},
            {"id": ID_DOCTOR_STATUS, "title": t(lang, "👨‍⚕️ Doctor Available?", "👨‍⚕️ डॉक्टर उपलब्ध हैं?"),
             "description": t(lang, "Is clinic open today?", "क्या क्लिनिक आज खुला है?")},
            {"id": ID_CANCEL, "title": t(lang, "❌ Cancel Appointment", "❌ अपॉइंटमेंट रद्द करें"),
             "description": t(lang, "Cancel your booking", "अपनी बुकिंग रद्द करें")},
        ],
    }


def _build_token_confirm(clinic: dict, lang: str) -> dict:
    """Returns a BUTTON payload to confirm token booking."""
    serving = clinic.get("current_serving_token") or 0
    last = clinic.get("last_token") or 0
    next_token = last + 1
    wait = max(0, (next_token - serving - 1)) * 10  # rough 10-min estimate per token
    name = clinic.get("business_name", "Clinic")
    body = t(
        lang,
        f"🏥 *{name}* Token Clinic\n\nNow serving: *#{serving}*\nYour token would be: *#{next_token}*\nEstimated wait: ~{wait} minutes",
        f"🏥 *{name}* टोकन क्लिनिक\n\nअभी सेवा: *#{serving}*\nआपका टोकन होगा: *#{next_token}*\nअनुमानित प्रतीक्षा: ~{wait} मिनट",
    )
    return {
        "type": "interactive",
        "interactive_type": "button",
        "body": body,
        "buttons": [
            {"id": ID_TOKEN_CONFIRM, "title": t(lang, "✅ Get My Token", "✅ टोकन लें")},
            {"id": ID_TOKEN_BACK, "title": t(lang, "❌ Go Back", "❌ वापस जाएं")},
        ],
    }


def _build_date_buttons(lang: str, now: datetime) -> dict:
    """Returns a BUTTON payload to pick a booking date (today/tomorrow/day after)."""
    today = now.strftime("%a, %b %d")
    tomorrow = (now + timedelta(days=1)).strftime("%a, %b %d")
    day_after = (now + timedelta(days=2)).strftime("%a, %b %d")
    return {
        "type": "interactive",
        "interactive_type": "button",
        "body": t(lang, f"📅 Which day would you like to book?\n\n• Today: {today}\n• Tomorrow: {tomorrow}\n• Day After: {day_after}",
                       f"📅 किस दिन बुकिंग करनी है?\n\n• आज: {today}\n• कल: {tomorrow}\n• परसों: {day_after}"),
        "buttons": [
            {"id": ID_TODAY, "title": t(lang, "📅 Today", "📅 आज")},
            {"id": ID_TOMORROW, "title": t(lang, "📅 Tomorrow", "📅 कल")},
            {"id": ID_DAY_AFTER, "title": t(lang, "📅 Day After", "📅 परसों")},
        ],
    }


def _build_slot_list(slots: list, date_str: str, lang: str) -> dict:
    """Returns a LIST payload with available time slots."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        date_label = dt.strftime("%a, %b %d")
    except Exception:
        date_label = date_str

    rows = []
    for s in slots[:10]:
        # Format slot nicely: "10:00" → "10:00 AM"
        try:
            slot_dt = datetime.strptime(s, "%H:%M")
            label = slot_dt.strftime("%-I:%M %p") if hasattr(slot_dt, 'strftime') else s
        except Exception:
            label = s
        rows.append({"id": f"slot_{s}", "title": label})

    if not rows:
        return None  # signal caller: no slots available

    return {
        "type": "interactive",
        "interactive_type": "list",
        "header": t(lang, f"Available Slots — {date_label}", f"उपलब्ध स्लॉट — {date_label}"),
        "body": t(lang, "Select a time slot to book your appointment:",
                       "अपॉइंटमेंट के लिए एक समय स्लॉट चुनें:"),
        "button_label": t(lang, "View Slots", "स्लॉट देखें"),
        "rows": rows,
    }


def _build_booking_confirm(wf: dict, lang: str, date_str: str, time_str: str) -> dict:
    """Returns a BUTTON payload to confirm the chosen slot."""
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        date_label = dt.strftime("%A, %b %d")
        time_label = dt.strftime("%-I:%M %p")
    except Exception:
        date_label = date_str
        time_label = time_str

    body = t(
        lang,
        f"✅ Confirm your appointment?\n\n📅 {date_label} at {time_label}\n🏥 {wf.get('clinic_name')}\n👤 {wf.get('patient_name')}",
        f"✅ अपॉइंटमेंट की पुष्टि करें?\n\n📅 {date_label} को {time_label}\n🏥 {wf.get('clinic_name')}\n👤 {wf.get('patient_name')}",
    )
    return {
        "type": "interactive",
        "interactive_type": "button",
        "body": body,
        "buttons": [
            {"id": ID_CONFIRM, "title": t(lang, "✅ Confirm", "✅ पुष्टि करें")},
            {"id": ID_ABORT, "title": t(lang, "❌ Cancel", "❌ रद्द करें")},
        ],
    }


def handle_turn(text, wf, clinics, phone, now, tools, groq_client=None,
                interactive_id: str = None):
    """
    Returns (reply, updated_workflow, used_groq).
    reply is either a str (plain text) or a dict (interactive message payload).
    interactive_id: the button/list reply ID if patient tapped a button, else None.
    tools: book_slot, generate_token, cancel_appointment, reschedule_slot, check_availability
    """
    wf = dict(wf or default_workflow())
    lang = wf.get("language") or "en"
    used_groq = False

    # Normalize: if a button was tapped, use its ID as the effective text
    effective = interactive_id if interactive_id else text

    # Global restart trigger (text only, not button IDs)
    if not interactive_id and is_restart(text) and wf.get("step") != "language":
        keep_lang = wf.get("language")
        keep_name = wf.get("patient_name")
        wf = default_workflow(keep_name or "")
        wf["language"] = keep_lang
        wf["step"] = "clinic_select"
        lang = keep_lang or "en"
        return _build_clinic_list(clinics, lang), wf, False

    step = wf.get("step") or "language"

    # ── LANGUAGE SELECTION ──────────────────────────────────────────────────
    if step == "language":
        detected = detect_language(effective)
        if not detected:
            return _build_language_list(lang), wf, False
        wf["language"] = detected
        lang = detected
        wf["step"] = "clinic_select"
        return _build_clinic_list(clinics, lang), wf, False

    # ── CLINIC SELECTION ────────────────────────────────────────────────────
    if step == "clinic_select":
        chosen = None

        # Check if a list item was tapped: ID format is "clinic_<uuid>"
        if interactive_id and interactive_id.startswith("clinic_"):
            clinic_id = interactive_id[len("clinic_"):]
            chosen = _clinic_by_id(clinics, clinic_id)

        # Fallback: text match or groq
        if not chosen:
            # Try exact number or name match
            n = normalize(text)
            if n.isdigit():
                idx = int(n) - 1
                if 0 <= idx < len(clinics):
                    chosen = clinics[idx]
            if not chosen:
                for c in clinics:
                    name = normalize(c.get("business_name") or "")
                    if name and (name == n or name in n or n in name):
                        chosen = c
                        break
            if not chosen and groq_client:
                extracted = groq_extract(groq_client, text, now, clinics)
                used_groq = True
                if extracted.get("clinic_name"):
                    for c in clinics:
                        if normalize(c.get("business_name") or "") in normalize(extracted["clinic_name"]):
                            chosen = c
                            break

        if not chosen:
            return _build_clinic_list(clinics, lang), wf, used_groq

        wf["clinic_id"] = chosen["id"]
        wf["clinic_name"] = chosen.get("business_name")
        wf["booking_mode"] = chosen.get("booking_mode") or "scheduled"
        # Store extra fields needed for menu info
        wf["clinic_fee"] = chosen.get("consultation_fee")
        wf["clinic_maps"] = chosen.get("maps_link")
        wf["clinic_hours"] = chosen.get("working_hours") or {"start": "09:00", "end": "21:00"}
        wf["clinic_closed_date"] = chosen.get("closed_date")

        wf["step"] = "main_menu"
        return _build_main_menu(chosen, lang), wf, used_groq

    # ── MAIN MENU ───────────────────────────────────────────────────────────
    if step == "main_menu":
        menu_id = effective

        if menu_id == ID_BOOK:
            if not wf.get("patient_name"):
                wf["step"] = "name"
                return t(lang, "👤 What is the patient's full name?", "👤 मरीज का पूरा नाम क्या है?"), wf, False

            # Skip name — go straight to booking flow
            return _enter_booking_flow(wf, clinics, lang, now, tools)

        elif menu_id == ID_TIMING:
            hours = wf.get("clinic_hours") or {}
            start, end = hours.get("start", "09:00"), hours.get("end", "21:00")
            reply = t(lang, f"🕐 *{wf.get('clinic_name')}* is open from *{start}* to *{end}*.", f"🕐 *{wf.get('clinic_name')}* सुबह *{start}* से शाम *{end}* तक खुला है।")
            clinic = _clinic_by_id(clinics, wf.get("clinic_id"))
            return reply + "\n\n" + t(lang, "Send *menu* to go back.", "*menu* टाइप करें वापस जाने के लिए।"), wf, False

        elif menu_id == ID_FEE:
            fee = wf.get("clinic_fee")
            if fee:
                reply = t(lang, f"💰 Consultation fee at *{wf.get('clinic_name')}*: *₹{fee}*", f"💰 *{wf.get('clinic_name')}* की परामर्श फीस: *₹{fee}*")
            else:
                reply = t(lang, "💰 Fee information is not available. Please call the clinic.", "💰 फीस की जानकारी उपलब्ध नहीं है। क्लिनिक से संपर्क करें।")
            return reply + "\n\n" + t(lang, "Send *menu* to go back.", "*menu* टाइप करें वापस जाने के लिए।"), wf, False

        elif menu_id == ID_LOCATION:
            maps = wf.get("clinic_maps")
            if maps:
                return t(lang, f"📍 *{wf.get('clinic_name')}* location:\n{maps}", f"📍 *{wf.get('clinic_name')}* का स्थान:\n{maps}"), wf, False
            return t(lang, "📍 Location link not available. Please call the clinic.", "📍 स्थान लिंक उपलब्ध नहीं है।"), wf, False

        elif menu_id == ID_DOCTOR_STATUS:
            closed = wf.get("clinic_closed_date")
            today_str = now.strftime("%Y-%m-%d")
            if closed and str(closed)[:10] == today_str:
                reply = t(lang, f"😔 Sorry, *{wf.get('clinic_name')}* is closed today. Please try another day.", f"😔 खेद है, *{wf.get('clinic_name')}* आज बंद है। कृपया कोई और दिन आजमाएं।")
            else:
                hours = wf.get("clinic_hours") or {}
                start, end = hours.get("start", "09:00"), hours.get("end", "21:00")
                reply = t(lang, f"✅ Doctor is available today at *{wf.get('clinic_name')}* ({start}–{end}).", f"✅ डॉक्टर आज *{wf.get('clinic_name')}* में उपलब्ध हैं ({start}–{end})।")
            return reply + "\n\n" + t(lang, "Send *menu* to go back.", "*menu* टाइप करें वापस जाने के लिए।"), wf, False

        elif menu_id == ID_CANCEL:
            result = tools["cancel_appointment"](wf["clinic_id"], phone)
            if result.get("status") == "success":
                wf["step"] = "idle"
            return t(lang, result.get("message", "Appointment cancelled."), result.get("message", "अपॉइंटमेंट रद्द हो गई।")), wf, False

        else:
            # Unrecognized — re-show menu
            clinic = _clinic_by_id(clinics, wf.get("clinic_id"))
            if clinic:
                return _build_main_menu(clinic, lang), wf, False
            wf["step"] = "clinic_select"
            return _build_clinic_list(clinics, lang), wf, False

    # ── NAME COLLECTION ─────────────────────────────────────────────────────
    if step == "name":
        candidate = extract_name(text)
        if looks_like_name(candidate):
            wf["patient_name"] = candidate
            return _enter_booking_flow(wf, clinics, lang, now, tools)
        return t(lang, "Please send the patient's full name (letters only, no numbers).", "कृपया मरीज का पूरा नाम भेजें (केवल अक्षर, कोई नंबर नहीं)।"), wf, False

    # ── TOKEN CONFIRM ────────────────────────────────────────────────────────
    if step == "token_confirm":
        if is_yes(effective):
            result = tools["generate_token"](wf["clinic_id"], phone, wf.get("patient_name") or "Unknown")
            wf["step"] = "idle"
            return t(lang, result.get("message", "Done."), result.get("message", "हो गया।")), wf, False
        if is_no(effective):
            wf["step"] = "main_menu"
            clinic = _clinic_by_id(clinics, wf.get("clinic_id"))
            return _build_main_menu(clinic, lang), wf, False
        # Re-show button
        clinic = _clinic_by_id(clinics, wf.get("clinic_id"))
        return _build_token_confirm(clinic, lang), wf, False

    # ── DATE SELECTION (time-based) ──────────────────────────────────────────
    if step == "date_select":
        selected_date = None
        if effective == ID_TODAY:
            selected_date = now.strftime("%Y-%m-%d")
        elif effective == ID_TOMORROW:
            selected_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        elif effective == ID_DAY_AFTER:
            selected_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")
        else:
            # Try text parse as fallback
            d, _ = parse_date_time(text, now)
            selected_date = d

        if not selected_date:
            return _build_date_buttons(lang, now), wf, False

        # Fetch available slots for that date
        avail = tools["check_availability"](wf["clinic_id"], selected_date)
        slots = avail.get("all_available_slots") or []

        slot_payload = _build_slot_list(slots, selected_date, lang)
        if not slot_payload:
            reply = t(lang, f"😔 No slots available on {selected_date}. Please choose another day.",
                           f"😔 {selected_date} को कोई स्लॉट उपलब्ध नहीं है। कोई और दिन चुनें।")
            return reply, wf, False

        wf["pending_date"] = selected_date
        wf["step"] = "slot_select"
        return slot_payload, wf, False

    # ── SLOT SELECTION ───────────────────────────────────────────────────────
    if step == "slot_select":
        time_str = None

        # Check if list item tapped: ID format is "slot_HH:MM"
        if effective.startswith("slot_"):
            time_str = effective[len("slot_"):]
        else:
            _, time_str = parse_date_time(text, now)

        if not time_str:
            # Re-show slots
            date_str = wf.get("pending_date")
            avail = tools["check_availability"](wf["clinic_id"], date_str)
            slots = avail.get("all_available_slots") or []
            slot_payload = _build_slot_list(slots, date_str, lang)
            return slot_payload or t(lang, "No slots available.", "कोई स्लॉट नहीं है।"), wf, False

        date_str = wf.get("pending_date")
        wf["pending_time"] = time_str

        # Show confirmation button
        confirm_payload = _build_booking_confirm(wf, lang, date_str, time_str)
        wf["step"] = "booking_confirm"
        return confirm_payload, wf, False

    # ── BOOKING CONFIRMATION ─────────────────────────────────────────────────
    if step == "booking_confirm":
        date_str = wf.get("pending_date")
        time_str = wf.get("pending_time")

        if is_yes(effective):
            result = tools["book_slot"](wf["clinic_id"], phone, date_str, time_str, wf.get("patient_name") or "Unknown")
            if result.get("status") == "success":
                wf["step"] = "idle"
                booked = result.get("slot_start") or f"{date_str} {time_str}"
                return t(
                    lang,
                    f"✅ Booked! Your appointment at *{wf.get('clinic_name')}* is confirmed.\n📅 {booked}\n\nSend *menu* to start again.",
                    f"✅ बुकिंग हो गई! *{wf.get('clinic_name')}* में आपकी अपॉइंटमेंट पक्की है।\n📅 {booked}\n\n*menu* टाइप करके फिर से शुरू करें।",
                ), wf, False
            return t(lang, result.get("message", "Could not book. Please try again."), result.get("message", "बुकिंग नहीं हो सकी। कृपया पुनः प्रयास करें।")), wf, False

        if is_no(effective):
            # Go back to date selection
            wf["step"] = "date_select"
            wf["pending_date"] = None
            wf["pending_time"] = None
            return _build_date_buttons(lang, now), wf, False

        return _build_booking_confirm(wf, lang, date_str, time_str), wf, False

    # ── IDLE STATE ───────────────────────────────────────────────────────────
    if step == "idle":
        if is_reschedule(text):
            if wf.get("booking_mode") == "token":
                return t(lang, "Token visits cannot be rescheduled. Please cancel and take a new token.", "टोकन का समय नहीं बदला जा सकता। रद्द करके नया टोकन लें।"), wf, False
            wf["step"] = "date_select"
            return _build_date_buttons(lang, now), wf, False

        # Show main menu again
        clinic = _clinic_by_id(clinics, wf.get("clinic_id"))
        if clinic:
            wf["step"] = "main_menu"
            return _build_main_menu(clinic, lang), wf, False
        wf["step"] = "clinic_select"
        return _build_clinic_list(clinics, lang), wf, False

    # Fallback
    return t(lang, "Send *hi* to start booking.", "बुकिंग शुरू करने के लिए *hi* लिखें।"), wf, False


def _enter_booking_flow(wf, clinics, lang, now, tools):
    """Common entry point once patient name is set and clinic is selected."""
    clinic = _clinic_by_id(clinics, wf.get("clinic_id"))

    if wf.get("booking_mode") == "token":
        # Token-based: just show confirm button
        wf["step"] = "token_confirm"
        # Refresh token info from passed-in clinic object
        return _build_token_confirm(clinic or {}, lang), wf, False

    # Time-based: start date selection
    wf["step"] = "date_select"
    return _build_date_buttons(lang, now), wf, False
