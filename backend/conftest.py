import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("ENABLE_BACKGROUND_JOBS", "0")
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-key.ey.ey")
os.environ.setdefault("GROQ_API_KEY", "mock-groq-key")
os.environ.setdefault("META_CLIENT_SECRET", "mock-app-secret")
os.environ.setdefault("META_ACCESS_TOKEN", "mock-token")
os.environ.setdefault("META_PHONE_NUMBER_ID", "mock-phone-id")

patch("supabase.create_client", return_value=MagicMock()).start()
