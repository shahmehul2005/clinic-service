import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock-key.ey.ey"
os.environ["GROQ_API_KEY"] = "mock-groq-key"

# Mock the entire Supabase Client before importing agent
mock_supabase = MagicMock()
with patch("supabase.create_client", return_value=mock_supabase):
    from agent import book_slot, generate_token, check_availability, get_now

class TestAgentBookingTactics(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test
        mock_supabase.reset_mock()
        self.now = get_now()
        self.today_str = self.now.strftime("%Y-%m-%d")
        self.tomorrow_str = (self.now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Helper to create a basic clinic response
        self.default_clinic = {
            "id": "c1",
            "booking_mode": "scheduled",
            "closed_date": None,
            "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "working_hours": {"start": "00:00", "end": "23:59"}
        }

    def _setup_clinic_mock(self, clinic_data):
        mock_resp = MagicMock()
        mock_resp.data = [clinic_data]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resp

    def test_book_slot_token_clinic_protection(self):
        """Test that the agent prevents booking a slot if the clinic is token-based."""
        clinic = self.default_clinic.copy()
        clinic["booking_mode"] = "token"
        self._setup_clinic_mock(clinic)
        
        result = book_slot("c1", "999", self.tomorrow_str, "12:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("CRITICAL", result["message"])
        self.assertIn("Token System", result["message"])

    def test_book_slot_closed_date(self):
        """Test that the agent prevents booking on a closed date."""
        clinic = self.default_clinic.copy()
        clinic["closed_date"] = self.tomorrow_str
        self._setup_clinic_mock(clinic)
        
        result = book_slot("c1", "999", self.tomorrow_str, "12:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("closed on", result["message"])

    def test_book_slot_outside_working_hours(self):
        """Test that the agent prevents booking outside working hours."""
        clinic = self.default_clinic.copy()
        clinic["working_hours"] = {"start": "09:00", "end": "17:00"}
        self._setup_clinic_mock(clinic)
        
        # Try 08:00 AM (too early)
        result = book_slot("c1", "999", self.tomorrow_str, "08:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("outside working hours", result["message"])
        
        # Try 18:00 (too late)
        result = book_slot("c1", "999", self.tomorrow_str, "18:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("outside working hours", result["message"])

    def test_book_slot_in_past(self):
        """Test that the agent prevents booking in the past."""
        self._setup_clinic_mock(self.default_clinic)
        past_date = (self.now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        result = book_slot("c1", "999", past_date, "12:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("Cannot book appointments in the past", result["message"])

    def test_book_slot_conflict_detection(self):
        """Test that the agent prevents booking within 10 minutes of an existing slot."""
        self._setup_clinic_mock(self.default_clinic)
        
        # Mock existing appointments at 12:05
        mock_apt_resp = MagicMock()
        mock_apt_resp.data = [{"appointment_time": f"{self.tomorrow_str}T12:05:00"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_apt_resp
        
        # Try 12:00 (5 mins away) - should conflict
        result = book_slot("c1", "999", self.tomorrow_str, "12:00")
        self.assertEqual(result["status"], "error")
        self.assertIn("another patient is booked within 10 minutes", result["message"])

    def _setup_token_mock(self):
        mock_token_resp = MagicMock()
        mock_token_resp.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_token_resp

    def test_generate_token_scheduled_clinic_protection(self):
        """Test that generate_token fails if clinic is scheduled-based."""
        clinic = self.default_clinic.copy()
        clinic["booking_mode"] = "scheduled"
        self._setup_clinic_mock(clinic)
        self._setup_token_mock()
        
        result = generate_token("c1", "999", "Test")
        self.assertEqual(result["status"], "error")
        self.assertIn("CRITICAL", result["message"])
        self.assertIn("Scheduled System", result["message"])

    @patch("agent.get_now")
    def test_generate_token_outside_working_hours(self, mock_get_now):
        """Test that generate_token fails if the clinic is currently closed (time-wise)."""
        clinic = self.default_clinic.copy()
        clinic["booking_mode"] = "token"
        clinic["working_hours"] = {"start": "09:00", "end": "17:00"}
        self._setup_clinic_mock(clinic)
        self._setup_token_mock()
        
        # Mock time to be 22:00 (10 PM)
        mock_now = datetime(2026, 7, 15, 22, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        mock_get_now.return_value = mock_now
        
        result = generate_token("c1", "999", "Test")
        self.assertEqual(result["status"], "error")
        self.assertIn("CRITICAL: The clinic is closed right now", result["message"])
        
    @patch("agent.get_now")
    def test_generate_token_success(self, mock_get_now):
        """Test successful token generation."""
        clinic = self.default_clinic.copy()
        clinic["booking_mode"] = "token"
        clinic["working_hours"] = {"start": "00:00", "end": "23:59"}
        self._setup_clinic_mock(clinic)
        
        # Mock time to be inside hours
        mock_now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        mock_get_now.return_value = mock_now
        
        # Mock token count (2 previous tokens today)
        mock_token_resp = MagicMock()
        mock_token_resp.data = [{"token_number": 1}, {"token_number": 2}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_token_resp
        
        result = generate_token("c1", "999", "Test")
        self.assertEqual(result["status"], "success")
        self.assertIn("Token #3", result["message"])

if __name__ == '__main__':
    unittest.main()
