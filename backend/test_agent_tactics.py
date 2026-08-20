import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, MagicMock, patch

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["ENABLE_BACKGROUND_JOBS"] = "0"
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock-key.ey.ey"
os.environ["GROQ_API_KEY"] = "mock-groq-key"

mock_supabase = MagicMock()
with patch("supabase.create_client", return_value=mock_supabase):
    from agent import book_slot, generate_token, check_availability, execute_tool, get_now


class TestAgentBookingTactics(unittest.TestCase):
    def setUp(self):
        mock_supabase.reset_mock()
        self.now = get_now()
        self.tomorrow_str = (self.now + timedelta(days=1)).strftime("%Y-%m-%d")
        self.default_clinic = {
            "id": "c1",
            "booking_mode": "scheduled",
            "closed_date": None,
            "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "working_hours": {"start": "00:00", "end": "23:59"},
            "slot_duration_minutes": 10,
        }

    def _rpc(self, payload):
        mock_resp = MagicMock()
        mock_resp.data = payload
        mock_supabase.rpc.return_value.execute.return_value = mock_resp

    def _setup_clinic_mock(self, clinic_data):
        mock_resp = MagicMock()
        mock_resp.data = [clinic_data]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resp

    def test_book_slot_token_clinic_protection(self):
        self._rpc({
            "status": "error",
            "message": "CRITICAL: This clinic operates on a Token System. You MUST call generate_token",
        })
        result = book_slot("c1", "999", self.tomorrow_str, "12:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("CRITICAL", result["message"])
        self.assertIn("Token System", result["message"])
        mock_supabase.rpc.assert_called_with("book_slot_atomic", ANY)

    def test_book_slot_closed_date(self):
        self._rpc({"status": "error", "message": f"CRITICAL: The clinic is closed on {self.tomorrow_str}. Offer another date."})
        result = book_slot("c1", "999", self.tomorrow_str, "12:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("closed on", result["message"])

    def test_book_slot_outside_working_hours(self):
        self._rpc({"status": "error", "message": "CRITICAL: Requested time is outside working hours (09:00:00 to 17:00:00). Offer another time."})
        result = book_slot("c1", "999", self.tomorrow_str, "08:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("outside working hours", result["message"])

    def test_book_slot_in_past(self):
        self._rpc({"status": "error", "message": "CRITICAL: Cannot book appointments in the past. Ask the user for a future date/time."})
        past_date = (self.now - timedelta(days=1)).strftime("%Y-%m-%d")
        result = book_slot("c1", "999", past_date, "12:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("Cannot book appointments in the past", result["message"])

    def test_book_slot_conflict_detection(self):
        self._rpc({"status": "error", "message": "CRITICAL: Slot is taken (another patient already holds this slot). Apologize and offer another time."})
        result = book_slot("c1", "999", self.tomorrow_str, "12:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("Slot is taken", result["message"])

    def test_generate_token_scheduled_clinic_protection(self):
        self._rpc({
            "status": "error",
            "message": "CRITICAL: This clinic operates on a Scheduled System. You MUST call book_slot instead of generate_token.",
        })
        result = generate_token("c1", "999", "Test")
        self.assertEqual(result["status"], "error")
        self.assertIn("Scheduled System", result["message"])

    def test_generate_token_outside_working_hours(self):
        self._rpc({
            "status": "error",
            "message": "CRITICAL: The clinic is closed right now. Working hours are 09:00 to 17:00. Tell the patient.",
        })
        result = generate_token("c1", "999", "Test")
        self.assertEqual(result["status"], "error")
        self.assertIn("closed right now", result["message"])

    def test_generate_token_success(self):
        self._rpc({
            "status": "success",
            "message": "Successfully generated Token #3. The current serving token is #0. There are 2 people ahead of them in the queue. Tell all this info to the patient.",
        })
        result = generate_token("c1", "999", "Test")
        self.assertEqual(result["status"], "success")
        self.assertIn("Token #3", result["message"])

    def test_execute_tool_cancel_and_reschedule(self):
        self._rpc({"status": "success", "message": "Cancelled"})
        result = execute_tool("cancel_appointment", {"clinic_id": "c1", "phone_number": "999"})
        self.assertEqual(result["status"], "success")
        mock_supabase.rpc.assert_called_with("cancel_appointment_atomic", {
            "p_clinic_id": "c1",
            "p_phone_number": "999",
        })

        self._rpc({"status": "success", "message": "Rescheduled"})
        result = execute_tool("reschedule_slot", {
            "clinic_id": "c1",
            "phone_number": "999",
            "date_str": self.tomorrow_str,
            "time_str": "14:00",
        })
        self.assertEqual(result["status"], "success")

    def test_check_availability_uses_clinic_hours(self):
        self._setup_clinic_mock(self.default_clinic)
        mock_appts = MagicMock()
        mock_appts.data = []
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[self.default_clinic])
        table.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_appts

        with patch("agent.get_now", return_value=datetime(2026, 8, 22, 8, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))):
            result = check_availability("c1", "2026-08-22")
        self.assertEqual(result["status"], "success")
        self.assertIn("slot_duration_minutes", result)


if __name__ == "__main__":
    unittest.main()
