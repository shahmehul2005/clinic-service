import os
import sys
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# User needs to set this before running
# os.environ["GROQ_API_KEY"] = "your_groq_api_key_here"

# Mock the entire Supabase Client to avoid JWT/dependency errors locally
mock_supabase = MagicMock()
with patch("supabase.create_client", return_value=mock_supabase):
    from agent import receptionist_agent, chat_sessions, get_all_clinics

print("\n=== LOCAL LLM DEEP EDGE CASE TEST ===")
if "GROQ_API_KEY" not in os.environ:
    print("CRITICAL: You must set the GROQ_API_KEY environment variable to run this test locally.")
    print("Example: $env:GROQ_API_KEY='gsk_xxx' ; python backend/local_llm_test.py")
    sys.exit(1)

def simulate_chat(phone_number, user_message, clinic_context=None):
    if phone_number not in chat_sessions:
        # Note: the real agent sets a dynamic instruction with clinic context. 
        # We simplify here for the mock.
        chat_sessions[phone_number] = [{"role": "system", "content": "You are a receptionist. Respond concisely."}]
        
    chat_sessions[phone_number].append({"role": "user", "content": user_message})
    print(f"\n[Patient {phone_number}]: {user_message}")
    
    # Mocking the adk tool executions
    with patch("agent.get_all_clinics", return_value=[
        {"id": "c1", "business_name": "Test Token Clinic", "booking_mode": "token"},
        {"id": "c2", "business_name": "Test Scheduled Clinic", "booking_mode": "scheduled"}
    ]), \
    patch("agent.generate_token", return_value={"status": "success", "token_number": 42}), \
    patch("agent.check_availability", return_value={"status": "success", "all_available_slots": ["10:00", "11:00"]}), \
    patch("agent.book_slot", return_value={"status": "success", "message": "Booked"}):
        
        # Run LLM
        response = receptionist_agent.run(
            user_message,
            deps={"clinic_id": clinic_context, "phone": phone_number}
        )
        
        reply = response.text
        chat_sessions[phone_number].append({"role": "assistant", "content": reply})
        print(f"[AI Receptionist]: {reply}")

# Run Edge Case 1: Token Clinic Booking Flow
phone1 = "1111111111"
simulate_chat(phone1, "Hi, I want a token for Test Token Clinic")
simulate_chat(phone1, "My name is Mehul")
simulate_chat(phone1, "Yes, book it")

# Run Edge Case 2: Scheduled Clinic Booking Flow
phone2 = "2222222222"
simulate_chat(phone2, "Hello, schedule an appointment for Test Scheduled Clinic")
simulate_chat(phone2, "I am Mehul")
simulate_chat(phone2, "Tomorrow at 10 AM")

print("\n=== TESTS COMPLETE ===")
