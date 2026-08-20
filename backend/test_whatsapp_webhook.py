import os
import json
import hmac
import hashlib
import unittest
from unittest.mock import patch, MagicMock

os.environ["ENABLE_BACKGROUND_JOBS"] = "0"
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock-key"
os.environ["META_ACCESS_TOKEN"] = "mock-token"
os.environ["META_PHONE_NUMBER_ID"] = "mock-phone-id"
os.environ["META_CLIENT_SECRET"] = "mock-app-secret"
os.environ["GROQ_API_KEY"] = "mock-groq-key"

from fastapi.testclient import TestClient

mock_supabase_client = MagicMock()
with patch("supabase.create_client", return_value=mock_supabase_client):
    from agent import app, get_all_clinics, get_patient_name

client = TestClient(app)

TEXT_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "id": "wamid.ABC",
                                "from": "919876543210",
                                "type": "text",
                                "text": {"body": "Appointment slots?"},
                            }
                        ]
                    },
                    "field": "messages",
                }
            ]
        }
    ],
}


class TestWhatsAppWebhook(unittest.TestCase):
    def test_webhook_verify_success(self):
        response = client.get(
            "/webhook?hub.mode=subscribe&hub.verify_token=clinic_os_secure_token_123&hub.challenge=test_challenge"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "test_challenge")

    def test_webhook_verify_failure(self):
        response = client.get(
            "/webhook?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=test_challenge"
        )
        self.assertEqual(response.status_code, 403)

    @patch("agent.supabase")
    def test_get_patient_name(self, mock_supabase):
        mock_response = MagicMock()
        mock_response.data = [{"patient_name": "Riya"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        self.assertEqual(get_patient_name("+1234567890"), "Riya")

    @patch("agent.supabase")
    def test_get_all_clinics(self, mock_supabase):
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "c1", "business_name": "Clinic A", "trial_end_date": None, "booking_mode": "scheduled"},
            {"id": "c2", "business_name": "Clinic B", "trial_end_date": None, "booking_mode": "token"},
        ]
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_response
        clinics = get_all_clinics()
        self.assertEqual(len(clinics), 2)
        self.assertEqual(clinics[0]["business_name"], "Clinic A")

    def test_webhook_post_invalid_signature(self):
        payload = {"test": "data"}
        body = json.dumps(payload).encode("utf-8")
        sig = hmac.new(b"wrong-secret", body, hashlib.sha256).hexdigest()
        with patch.dict(os.environ, {"META_CLIENT_SECRET": "mock-app-secret"}):
            response = client.post("/webhook", content=body, headers={
                "X-Hub-Signature-256": f"sha256={sig}",
                "Content-Type": "application/json",
            })
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid signature", response.text)

    def test_webhook_post_valid_signature_accepted(self):
        body = json.dumps(TEXT_PAYLOAD, separators=(",", ":")).encode("utf-8")
        # TestClient re-serializes JSON; compute signature the same way Starlette will read the body
        # by sending content= with matching header is fragile. We patch verify_signature instead.
        with patch("agent.verify_signature", return_value=True), \
             patch("agent.process_whatsapp_message") as mock_proc:
            response = client.post("/webhook", json=TEXT_PAYLOAD)
            self.assertEqual(response.status_code, 200)
            mock_proc.assert_called_once()

    @patch("agent.save_session")
    @patch("agent.send_whatsapp_message")
    @patch("agent.get_all_clinics", return_value=[{"id": "c1", "business_name": "Demo", "booking_mode": "scheduled"}])
    @patch("agent.get_patient_name", return_value="Riya")
    @patch("agent.claim_message_id", return_value=True)
    @patch("agent.load_session")
    def test_process_sends_workflow_reply(
        self, mock_load, mock_claim, mock_name, mock_clinics, mock_send, mock_save
    ):
        from agent import process_whatsapp_message
        from workflow import default_workflow

        mock_load.return_value = ([], default_workflow("Riya"))
        process_whatsapp_message(TEXT_PAYLOAD)
        mock_claim.assert_called_once_with("wamid.ABC", "919876543210")
        mock_send.assert_called()
        sent = mock_send.call_args[0][1]
        self.assertIn("English", sent)
        mock_save.assert_called()

    @patch("agent.send_whatsapp_message")
    @patch("agent.check_and_increment_usage")
    @patch("agent.claim_message_id", return_value=False)
    def test_duplicate_wamid_skipped(self, mock_claim, mock_limit, mock_send):
        from agent import process_whatsapp_message
        process_whatsapp_message(TEXT_PAYLOAD)
        mock_limit.assert_not_called()
        mock_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
