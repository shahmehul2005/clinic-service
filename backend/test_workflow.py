"""
test_workflow.py — Tests for the V2 interactive WhatsApp workflow.

Key V2 differences from V1:
  - Replies are dicts for interactive messages (list/button) and strings for text
  - Patients tap button/list IDs (interactive_id param) instead of typing
  - Flow: language → clinic_select → main_menu → booking sub-flow
  - Token booking: one button tap (ID_TOKEN_CONFIRM)
  - Time booking: date buttons → slot list → confirm button
  - Cancel / FAQ answered from main menu
"""
from datetime import datetime
from unittest.mock import MagicMock

from workflow import (
    detect_language,
    default_workflow,
    handle_turn,
    match_clinic,
    parse_date_time,
    ID_LANG_EN,
    ID_LANG_HI,
    ID_BOOK,
    ID_CANCEL,
    ID_TODAY,
    ID_TOKEN_CONFIRM,
    ID_TOKEN_BACK,
    ID_CONFIRM,
    ID_ABORT,
    ID_TIMING,
    ID_FEE,
    ID_LOCATION,
    ID_DOCTOR_STATUS,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

CLINICS = [
    {
        "id": "c1",
        "business_name": "Naman Clinic",
        "booking_mode": "scheduled",
        "working_hours": {"start": "09:00", "end": "21:00"},
        "consultation_fee": "300",
        "maps_link": "https://maps.app.goo.gl/test",
        "closed_date": None,
    },
    {
        "id": "c2",
        "business_name": "City Care",
        "booking_mode": "token",
        "current_serving_token": 3,
        "last_token": 8,
        "waiting_queue": 5,
        "working_hours": {"start": "09:00", "end": "21:00"},
        "consultation_fee": None,
        "maps_link": None,
        "closed_date": None,
    },
]


def tools_ok():
    return {
        "book_slot": MagicMock(return_value={
            "status": "success",
            "message": "Booked!",
            "slot_start": "2026-08-22 17:00",
        }),
        "generate_token": MagicMock(return_value={
            "status": "success",
            "message": "Successfully generated Token #9.",
        }),
        "cancel_appointment": MagicMock(return_value={
            "status": "success",
            "message": "Cancelled the appointment at 2026-08-22 17:00.",
        }),
        "reschedule_slot": MagicMock(return_value={
            "status": "success",
            "message": "Rescheduled.",
        }),
        "check_availability": MagicMock(return_value={
            "status": "success",
            "all_available_slots": ["17:00", "17:20", "17:40"],
            "suggested_available_slots": ["17:00"],
        }),
    }


NOW = datetime(2026, 8, 21, 10, 0)


# ── Utility helpers ───────────────────────────────────────────────────────────

def is_interactive(reply, itype=None):
    """Check reply is an interactive dict (optionally of a specific type)."""
    if not isinstance(reply, dict):
        return False
    if reply.get("type") != "interactive":
        return False
    if itype and reply.get("interactive_type") != itype:
        return False
    return True


def is_text(reply):
    return isinstance(reply, str)


# ── Basic unit tests ──────────────────────────────────────────────────────────

def test_detect_language_basics():
    assert detect_language("hi") is None          # "hi" is a greeting, not Hindi
    assert detect_language("2") == "hi"
    assert detect_language("hindi") == "hi"
    assert detect_language("english") == "en"
    assert detect_language(ID_LANG_EN) == "en"
    assert detect_language(ID_LANG_HI) == "hi"


def test_parse_kal_shaam():
    now = datetime(2026, 8, 21, 10, 0)
    d, t = parse_date_time("kal shaam 5pm", now)
    assert d == "2026-08-22"
    assert t == "17:00"


def test_match_clinic_by_number():
    assert match_clinic("1", CLINICS)["id"] == "c1"
    assert match_clinic("2", CLINICS)["id"] == "c2"


def test_match_clinic_by_name():
    assert match_clinic("naman", CLINICS)["id"] == "c1"
    assert match_clinic("city care", CLINICS)["id"] == "c2"
    assert match_clinic("nonexistent", CLINICS) is None


# ── Language step ─────────────────────────────────────────────────────────────

def test_unknown_text_at_language_step_returns_language_list():
    wf = default_workflow()
    reply, wf2, used = handle_turn("hello", wf, CLINICS, "91", NOW, tools_ok())
    assert is_interactive(reply, "list"), "Expected a list message for language selection"
    assert wf2["step"] == "language"
    assert used is False


def test_lang_en_button_advances_to_clinic_select():
    wf = default_workflow()
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                 interactive_id=ID_LANG_EN)
    assert wf2["language"] == "en"
    assert wf2["step"] == "clinic_select"
    assert is_interactive(reply, "list")


def test_lang_hi_button_advances_to_clinic_select():
    wf = default_workflow()
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                 interactive_id=ID_LANG_HI)
    assert wf2["language"] == "hi"
    assert wf2["step"] == "clinic_select"
    assert is_interactive(reply, "list")


# ── Clinic select step ────────────────────────────────────────────────────────

def test_clinic_select_by_text_number():
    wf = {"step": "clinic_select", "language": "en", "patient_name": None}
    reply, wf2, _ = handle_turn("1", wf, CLINICS, "91", NOW, tools_ok())
    assert wf2["clinic_id"] == "c1"
    assert wf2["step"] == "main_menu"
    assert is_interactive(reply, "list")


def test_clinic_select_by_list_id():
    wf = {"step": "clinic_select", "language": "en", "patient_name": None}
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                  interactive_id="clinic_c2")
    assert wf2["clinic_id"] == "c2"
    assert wf2["step"] == "main_menu"
    assert is_interactive(reply, "list")


def test_clinic_select_by_partial_name():
    wf = {"step": "clinic_select", "language": "en", "patient_name": None}
    reply, wf2, _ = handle_turn("naman", wf, CLINICS, "91", NOW, tools_ok())
    assert wf2["clinic_id"] == "c1"


# ── Main menu options ─────────────────────────────────────────────────────────

def _menu_wf(clinic_id="c1", booking_mode="scheduled", patient_name="Riya"):
    clinic = next(c for c in CLINICS if c["id"] == clinic_id)
    return {
        "step": "main_menu",
        "language": "en",
        "clinic_id": clinic_id,
        "clinic_name": clinic["business_name"],
        "booking_mode": booking_mode,
        "patient_name": patient_name,
        "clinic_fee": clinic.get("consultation_fee"),
        "clinic_maps": clinic.get("maps_link"),
        "clinic_hours": clinic.get("working_hours", {"start": "09:00", "end": "21:00"}),
        "clinic_closed_date": clinic.get("closed_date"),
    }


def test_menu_timing_returns_text():
    wf = _menu_wf()
    reply, _, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                               interactive_id=ID_TIMING)
    assert is_text(reply)
    assert "09:00" in reply and "21:00" in reply


def test_menu_fee_returns_text_with_fee():
    wf = _menu_wf()
    reply, _, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                               interactive_id=ID_FEE)
    assert is_text(reply)
    assert "300" in reply


def test_menu_fee_unavailable():
    wf = _menu_wf("c2", "token")
    reply, _, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                               interactive_id=ID_FEE)
    assert is_text(reply)
    assert "not available" in reply.lower() or "available" in reply.lower()


def test_menu_location_returns_maps_link():
    wf = _menu_wf()
    reply, _, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                               interactive_id=ID_LOCATION)
    assert is_text(reply)
    assert "maps.app.goo.gl" in reply


def test_menu_doctor_status_open():
    wf = _menu_wf()
    reply, _, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                               interactive_id=ID_DOCTOR_STATUS)
    assert is_text(reply)
    assert "available" in reply.lower() or "✅" in reply


def test_menu_cancel_calls_tool():
    wf = _menu_wf()
    tools = tools_ok()
    reply, wf2, used = handle_turn("", wf, CLINICS, "91", NOW, tools,
                                    interactive_id=ID_CANCEL)
    assert used is False
    tools["cancel_appointment"].assert_called_with("c1", "91")
    assert "cancelled" in reply.lower() or "Cancelled" in reply


# ── Book → name collection (no existing name) ─────────────────────────────────

def test_book_without_name_asks_for_name():
    wf = _menu_wf(patient_name=None)
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                  interactive_id=ID_BOOK)
    assert wf2["step"] == "name"
    assert is_text(reply)
    assert "name" in reply.lower()


def test_name_step_accepts_valid_name():
    wf = {**_menu_wf(patient_name=None), "step": "name"}
    reply, wf2, _ = handle_turn("Riya Shah", wf, CLINICS, "91", NOW, tools_ok())
    assert wf2["patient_name"] == "Riya Shah"
    # After name, scheduled clinic goes to date selection
    assert wf2["step"] == "date_select"
    assert is_interactive(reply, "button")


def test_name_step_rejects_numbers():
    wf = {**_menu_wf(patient_name=None), "step": "name"}
    reply, wf2, _ = handle_turn("12345", wf, CLINICS, "91", NOW, tools_ok())
    assert wf2["step"] == "name"


# ── Token clinic flow ─────────────────────────────────────────────────────────

def test_book_token_clinic_shows_button_confirm():
    wf = _menu_wf("c2", "token", "Amit")
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                  interactive_id=ID_BOOK)
    assert wf2["step"] == "token_confirm"
    assert is_interactive(reply, "button")


def test_token_confirm_yes_issues_token():
    wf = {**_menu_wf("c2", "token", "Amit"), "step": "token_confirm"}
    tools = tools_ok()
    reply, wf2, used = handle_turn("", wf, CLINICS, "91", NOW, tools,
                                    interactive_id=ID_TOKEN_CONFIRM)
    assert used is False
    tools["generate_token"].assert_called()
    assert wf2["step"] == "idle"
    assert is_text(reply)
    assert "Token #9" in reply


def test_token_confirm_no_goes_back_to_menu():
    wf = {**_menu_wf("c2", "token", "Amit"), "step": "token_confirm"}
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                  interactive_id=ID_TOKEN_BACK)
    assert wf2["step"] == "main_menu"
    assert is_interactive(reply, "list")


# ── Time-based booking flow ───────────────────────────────────────────────────

def test_book_scheduled_with_name_goes_to_date_select():
    wf = _menu_wf("c1", "scheduled", "Riya")
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                  interactive_id=ID_BOOK)
    assert wf2["step"] == "date_select"
    assert is_interactive(reply, "button")


def test_date_select_today_button_returns_slot_list():
    wf = {**_menu_wf("c1", "scheduled", "Riya"), "step": "date_select"}
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                  interactive_id=ID_TODAY)
    assert wf2["step"] == "slot_select"
    assert wf2["pending_date"] == NOW.strftime("%Y-%m-%d")
    assert is_interactive(reply, "list")


def test_slot_select_via_id_goes_to_booking_confirm():
    wf = {
        **_menu_wf("c1", "scheduled", "Riya"),
        "step": "slot_select",
        "pending_date": "2026-08-22",
    }
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                  interactive_id="slot_17:00")
    assert wf2["step"] == "booking_confirm"
    assert wf2["pending_time"] == "17:00"
    assert is_interactive(reply, "button")
    # Confirm button should show the time in the body text
    assert "17:00" in reply.get("body", "") or "17:00" in str(reply)


def test_booking_confirm_yes_books_slot():
    wf = {
        **_menu_wf("c1", "scheduled", "Riya"),
        "step": "booking_confirm",
        "pending_date": "2026-08-22",
        "pending_time": "17:00",
    }
    tools = tools_ok()
    reply, wf2, used = handle_turn("", wf, CLINICS, "91", NOW, tools,
                                    interactive_id=ID_CONFIRM)
    assert used is False
    tools["book_slot"].assert_called_with("c1", "91", "2026-08-22", "17:00", "Riya")
    assert wf2["step"] == "idle"
    assert is_text(reply)
    assert "Booked" in reply or "booked" in reply.lower()


def test_booking_confirm_no_goes_back_to_date_select():
    wf = {
        **_menu_wf("c1", "scheduled", "Riya"),
        "step": "booking_confirm",
        "pending_date": "2026-08-22",
        "pending_time": "17:00",
    }
    reply, wf2, _ = handle_turn("", wf, CLINICS, "91", NOW, tools_ok(),
                                  interactive_id=ID_ABORT)
    assert wf2["step"] == "date_select"
    assert wf2["pending_date"] is None
    assert is_interactive(reply, "button")


# ── Idle / restart ────────────────────────────────────────────────────────────

def test_restart_with_hi_goes_to_clinic_select():
    wf = {
        **_menu_wf(),
        "step": "idle",
        "language": "en",
    }
    reply, wf2, _ = handle_turn("hi", wf, CLINICS, "91", NOW, tools_ok())
    assert wf2["step"] == "clinic_select"
    assert is_interactive(reply, "list")


def test_idle_with_unknown_text_shows_menu():
    wf = {**_menu_wf(), "step": "idle"}
    reply, wf2, _ = handle_turn("what to do?", wf, CLINICS, "91", NOW, tools_ok())
    assert wf2["step"] == "main_menu"
    assert is_interactive(reply, "list")
