import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("ENABLE_BACKGROUND_JOBS", "0")
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-key.ey.ey")
os.environ.setdefault("GROQ_API_KEY", "mock-groq-key")
os.environ.setdefault("META_CLIENT_SECRET", "mock-app-secret")

from agent import claim_message_id, process_due_reminders, execute_tool


def test_claim_message_id_missing_always_true():
    assert claim_message_id("", "91") is True
    assert claim_message_id(None, "91") is True


@patch("agent.call_rpc", return_value=False)
def test_claim_message_id_duplicate(mock_rpc):
    assert claim_message_id("wamid.1", "91") is False
    mock_rpc.assert_called_once()


@patch("agent.send_whatsapp_message")
@patch("agent.supabase")
@patch("agent.call_rpc")
def test_process_due_reminders_skips_cancelled_appointments(mock_rpc, mock_sb, mock_send):
    mock_rpc.return_value = [{
        "id": "m1",
        "appointment_id": "a1",
        "phone_number": "91",
    }]
    apt = MagicMock()
    apt.data = [{"status": "cancelled", "appointment_time": "2026-08-21 12:00", "patient_name": "A", "clinic_id": "c1"}]
    mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = apt
    process_due_reminders()
    mock_sb.table.return_value.update.assert_called()
    mock_send.assert_not_called()


def test_unknown_tool():
    assert execute_tool("nope", {}) == {"error": "Unknown function"}
