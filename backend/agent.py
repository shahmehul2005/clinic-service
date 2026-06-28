import os
from fastapi import FastAPI, Request
from supabase import create_client, Client
from google.adk.agents import Agent

app = FastAPI()

# 1. Initialize Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_KEY")
)

# 2. Define ADK Tools (The docstrings tell Gemini how to use them)
def check_availability(date_str: str) -> dict:
    """
    Checks Supabase for booked slots on a specific date.
    Args:
        date_str (str): Date in YYYY-MM-DD format.
    Returns:
        dict: List of already booked slots, or an error.
    """
    try:
        # Fetch all appointments for the given day
        response = supabase.table("appointments").select("appointment_time").like("appointment_time", f"{date_str}%").execute()
        booked = [record["appointment_time"] for record in response.data]
        
        return {
            "status": "success",
            "clinic_hours": "10:00 AM to 6:00 PM, 30-minute slots",
            "already_booked_slots": booked,
            "instruction": "Offer the user 2 or 3 available slot times that are NOT in the already_booked_slots list."
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def book_slot(phone_number: str, date_str: str, time_str: str) -> dict:
    """
    Books the appointment slot in the database.
    Args:
        phone_number (str): The patient's WhatsApp number.
        date_str (str): Date in YYYY-MM-DD format.
        time_str (str): Time in HH:MM:00 format (24-hour).
    """
    timestamp = f"{date_str} {time_str}"
    
    try:
        supabase.table("appointments").insert({
            "phone_number": phone_number,
            "appointment_time": timestamp,
            "doctor_id": "clinic_01" # Hardcoded for demo, dynamic later
        }).execute()
        return {"status": "success", "message": f"Successfully booked for {timestamp}."}
    except Exception:
        # The unique SQL constraint triggers an exception if the slot is taken
        return {"status": "error", "message": "Slot taken. Apologize and offer another time."}

# 3. Initialize the Google ADK Agent
receptionist_agent = Agent(
    name="whatsapp_receptionist",
    model="gemini-2.5-flash",
    description="A Hinglish-speaking clinic receptionist.",
    instruction=(
        "You are a helpful clinic receptionist. Speak entirely in polite Hinglish. "
        "When a user asks for an appointment, use 'check_availability' to find open slots. "
        "Ask the user to confirm a specific time. "
        "Once they confirm, use 'book_slot' to save it. "
        "Keep messages extremely short and easy to read on WhatsApp."
    ),
    tools=[check_availability, book_slot]
)

# 4. Expose the Webhook for n8n
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    payload = await request.json()
    
    user_message = payload.get("message")
    user_phone = payload.get("phone")
    
    # Execute the agent against the incoming WhatsApp message
    response = receptionist_agent.run(user_message)
    
    return {
        "reply": response.text,
        "phone": user_phone
    }