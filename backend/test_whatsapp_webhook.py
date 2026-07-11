import unittest
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock env vars before importing agent
import os
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock-key"
os.environ["META_ACCESS_TOKEN"] = "mock-token"
os.environ["META_PHONE_NUMBER_ID"] = "mock-phone-id"
os.environ["META_CLIENT_SECRET"] = "mock-app-secret"

# Create a mock for Supabase create_client to avoid validation errors on dummy key during module load
mock_supabase_client = MagicMock()
with patch('supabase.create_client', return_value=mock_supabase_client):
    from agent import app, get_patient_clinic_context, get_all_clinics

client = TestClient(app)

class TestWhatsAppWebhook(unittest.TestCase):

    def test_webhook_verify_success(self):
        """Test GET webhook verification handshake with correct token."""
        response = client.get(
            "/webhook?hub.mode=subscribe&hub.verify_token=clinic_os_secure_token_123&hub.challenge=test_challenge"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "test_challenge")

    def test_webhook_verify_failure(self):
        """Test GET webhook verification handshake with incorrect token."""
        response = client.get(
            "/webhook?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=test_challenge"
        )
        self.assertEqual(response.status_code, 403)

    @patch('agent.supabase')
    def test_get_patient_clinic_context(self, mock_supabase):
        """Test get_patient_clinic_context returns last visited clinic ID."""
        # Setup mock db query chain
        mock_response = MagicMock()
        mock_response.data = [{"clinic_id": "clinic-123-uuid"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        clinic_id = get_patient_clinic_context("+1234567890")
        self.assertEqual(clinic_id, "clinic-123-uuid")
        mock_supabase.table.assert_called_with("appointments")

    @patch('agent.supabase')
    def test_get_all_clinics(self, mock_supabase):
        """Test get_all_clinics queries clinics correctly."""
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "c1", "business_name": "Clinic A"},
            {"id": "c2", "business_name": "Clinic B"}
        ]
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_response

        clinics = get_all_clinics()
        self.assertEqual(len(clinics), 2)
        self.assertEqual(clinics[0]["business_name"], "Clinic A")

    @patch('agent.verify_signature')
    @patch('agent.get_patient_clinic_context')
    @patch('agent.receptionist_agent')
    @patch('agent.send_whatsapp_message')
    def test_whatsapp_webhook_post_success(self, mock_send_msg, mock_agent, mock_clinic_context, mock_verify_sig):
        """Test POST webhook processing with successful agent run."""
        mock_verify_sig.return_value = True
        mock_clinic_context.return_value = "clinic-123-uuid"
        
        # Mock agent output
        mock_agent_response = MagicMock()
        mock_agent_response.text = "नमस्ते, हम आपका स्लॉट बुक कर रहे हैं।"
        mock_agent.run.return_value = mock_agent_response

        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "type": "text",
                                        "text": {"body": "Appointment slots?"}
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }

        # Send POST request
        response = client.post("/webhook", json=payload)
        self.assertEqual(response.status_code, 200)
        
        # Verify agent was called with correct context
        mock_agent.run.assert_called_once()
        agent_call_arg = mock_agent.run.call_args[0][0]
        self.assertIn("clinic_id=clinic-123-uuid", agent_call_arg)
        self.assertIn("phone=919876543210", agent_call_arg)
        
        # Verify reply was sent back to WhatsApp
        mock_send_msg.assert_called_once_with("919876543210", "नमस्ते, हम आपका स्लॉट बुक कर रहे हैं।")


    def test_webhook_post_invalid_signature(self):
        """Test POST webhook fails with 401 if signature validation fails."""
        payload = {"test": "data"}
        body = json.dumps(payload).encode("utf-8")
        
        # Compute real signature with WRONG secret
        wrong_secret = "wrong-secret"
        sig = hmac.new(wrong_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-Hub-Signature-256": f"sha256={sig}"
        }
        
        response = client.post("/webhook", json=payload, headers=headers)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid signature", response.text)


    def test_webhook_post_valid_signature(self):
        """Test POST webhook passes signature verification when correct secret is used."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "type": "text",
                                        "text": {"body": "Hello"}
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        
        body = json.dumps(payload).encode("utf-8")
        # Compute signature with CORRECT secret
        correct_secret = "mock-app-secret"
        sig = hmac.new(correct_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-Hub-Signature-256": f"sha256={sig}"
        }
        
        with patch('agent.get_patient_clinic_context') as mock_context, \
             patch('agent.receptionist_agent') as mock_agent, \
             patch('agent.send_whatsapp_message') as mock_send:
            
            mock_context.return_value = None
            mock_agent_response = MagicMock()
            mock_agent_response.text = "नमस्ते"
            mock_agent.run.return_value = mock_agent_response
            
            response = client.post("/webhook", json=payload, headers=headers)
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
