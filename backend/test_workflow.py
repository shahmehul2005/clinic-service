from datetime import datetime
from unittest.mock import MagicMock

from workflow import (
    detect_language,
    default_workflow,
    handle_turn,
    match_clinic,
    parse_date_time,
)


CLINICS = [
    {"id": "c1", "business_name": "Naman Clinic", "booking_mode": "scheduled"},
    {"id": "c2", "business_name": "City Care", "booking_mode": "token", "current_serving_token": 3, "last_token": 8, "waiting_queue": 5},
]


def tools_ok():
    return {
        "book_slot": MagicMock(return_value={"status": "success", "message": "Successfully booked for 2026-08-22 17:00.", "slot_start": "2026-08-22 17:00"}),
        "generate_token": MagicMock(return_value={"status": "success", "message": "Successfully generated Token #9."}),
        "cancel_appointment": MagicMock(return_value={"status": "success", "message": "Cancelled the appointment at 2026-08-22 17:00."}),
        "reschedule_slot": MagicMock(return_value={"status": "success", "message": "Rescheduled."}),
        "check_availability": MagicMock(return_value={"status": "success", "all_available_slots": ["17:00", "17:10"], "suggested_available_slots": ["17:00"]}),
    }


def test_hi_greeting_is_not_hindi_language():
    assert detect_language("hi") is None
    assert detect_language("2") == "hi"
    assert detect_language("english") == "en"


def test_parse_kal_shaam():
    now = datetime(2026, 8, 21, 10, 0)
    d, t = parse_date_time("kal shaam 5pm", now)
    assert d == "2026-08-22"
    assert t == "17:00"


def test_match_clinic_by_number_and_name():
    assert match_clinic("1", CLINICS)["id"] == "c1"
    assert match_clinic("naman", CLINICS)["id"] == "c1"


def test_language_then_clinic_then_name_then_book():
    now = datetime(2026, 8, 21, 10, 0)
    tools = tools_ok()
    wf = default_workflow()
    reply, wf, used = handle_turn("hello", wf, CLINICS, "91", now, tools)
    assert "English" in reply
    assert used is False
    reply, wf, _ = handle_turn("1", wf, CLINICS, "91", now, tools)
    assert "Naman Clinic" in reply
    reply, wf, _ = handle_turn("1", wf, CLINICS, "91", now, tools)
    assert "name" in reply.lower()
    reply, wf, _ = handle_turn("Riya Shah", wf, CLINICS, "91", now, tools)
    assert "date" in reply.lower()
    reply, wf, _ = handle_turn("tomorrow 5pm", wf, CLINICS, "91", now, tools)
    assert "Booked" in reply
    tools["book_slot"].assert_called()
    assert wf["step"] == "idle"


def test_token_yes_issues_token():
    now = datetime(2026, 8, 21, 10, 0)
    tools = tools_ok()
    wf = default_workflow("Amit")
    wf.update({"step": "clinic", "language": "en", "patient_name": "Amit"})
    reply, wf, _ = handle_turn("2", wf, CLINICS, "91", now, tools)
    assert "YES" in reply
    reply, wf, _ = handle_turn("yes", wf, CLINICS, "91", now, tools)
    assert "Token #9" in reply
    tools["generate_token"].assert_called()


def test_cancel_uses_tool_not_model():
    now = datetime(2026, 8, 21, 10, 0)
    tools = tools_ok()
    wf = {
        "step": "idle",
        "language": "en",
        "clinic_id": "c1",
        "clinic_name": "Naman Clinic",
        "booking_mode": "scheduled",
        "patient_name": "Riya",
    }
    reply, wf, used = handle_turn("please cancel", wf, CLINICS, "91", now, tools)
    assert used is False
    tools["cancel_appointment"].assert_called_with("c1", "91")
    assert "Cancelled" in reply
