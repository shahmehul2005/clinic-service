import os
os.environ["ENABLE_BACKGROUND_JOBS"] = "0"
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock-key.ey.ey"
os.environ["GROQ_API_KEY"] = "mock-groq-key"
os.environ["META_CLIENT_SECRET"] = ""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from ops import iter_slots, serialize_messages, trim_messages

IST = timezone(timedelta(hours=5, minutes=30))


def test_iter_slots_skips_lunch_and_past():
    now = datetime(2026, 8, 21, 11, 0, tzinfo=IST)
    hours = {"start": "09:00", "end": "13:00", "break_start": "12:00", "break_end": "12:30"}
    slots = [s.strftime("%H:%M") for s in iter_slots("2026-08-21", hours, 30, now)]
    assert "09:00" not in slots  # already past
    assert "11:00" in slots
    assert "11:30" in slots
    assert "12:00" not in slots
    assert "12:30" in slots


def test_serialize_and_trim_keeps_system_prompt():
    class Fake:
        role = "assistant"
        content = "hi"
        tool_calls = None

    messages = [{"role": "system", "content": "sys"}] + [{"role": "user", "content": str(i)} for i in range(50)]
    trimmed = trim_messages(messages, max_len=5)
    assert trimmed[0]["role"] == "system"
    assert len(trimmed) == 5
    assert serialize_messages([Fake()])[0]["content"] == "hi"
