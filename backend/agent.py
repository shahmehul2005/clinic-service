import os
import requests
from fastapi import FastAPI, Request, Response
from supabase import create_client, Client
from google.adk.agents import Agent
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 1. Initialize Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_KEY")
)

# Meta API Configuration
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "clinic_os_secure_token_123")

# 2. Define ADK Tools
def check_availability(clinic_id: str, date_str: str) -> dict:
    """
    Checks Supabase for booked slots on a specific date for a specific clinic.
    Args:
        clinic_id (str): The UUID of the clinic.
        date_str (str): Date in YYYY-MM-DD format.
    Returns:
        dict: List of already booked slots, or an error.
    """
    try:
        response = supabase.table("appointments") \
            .select("appointment_time") \
            .eq("clinic_id", clinic_id) \
            .like("appointment_time", f"{date_str}%") \
            .execute()
            
        booked = [record["appointment_time"] for record in response.data]
        
        return {
            "status": "success",
            "clinic_hours": "10:00 AM to 6:00 PM, 30-minute slots",
            "already_booked_slots": booked,
            "instruction": "Offer the user 2 or 3 available slot times that are NOT in the already_booked_slots list."
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def book_slot(clinic_id: str, phone_number: str, date_str: str, time_str: str, patient_name: str = "Unknown") -> dict:
    """
    Books the appointment slot in the database.
    Args:
        clinic_id (str): The UUID of the clinic.
        phone_number (str): The patient's WhatsApp number.
        date_str (str): Date in YYYY-MM-DD format.
        time_str (str): Time in HH:MM:00 format (24-hour).
        patient_name (str): Optional name of the patient.
    """
    timestamp = f"{date_str} {time_str}"
    
    try:
        supabase.table("appointments").insert({
            "clinic_id": clinic_id,
            "phone_number": phone_number,
            "patient_name": patient_name,
            "appointment_time": timestamp,
            "status": "booked"
        }).execute()
        return {"status": "success", "message": f"Successfully booked for {timestamp}."}
    except Exception as e:
        # The unique SQL constraint (clinic_id, appointment_time) triggers an exception if the slot is taken
        error_msg = str(e)
        if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower() or "23505" in error_msg:
            return {"status": "error", "message": "CRITICAL: Slot taken. Apologize and offer another time."}
        return {"status": "error", "message": f"Database error: {error_msg}"}

# 3. Initialize the Google ADK Agent
receptionist_agent = Agent(
    name="whatsapp_receptionist",
    model="gemini-2.5-flash",
    description="A Hinglish-speaking clinic receptionist.",
    instruction=(
        "You are a helpful clinic receptionist. Speak entirely in polite Hinglish. "
        "When a user asks for an appointment, use 'check_availability' to find open slots. "
        "Ask the user to confirm a specific time and their name. "
        "Once they confirm, use 'book_slot' to save it. "
        "Keep messages extremely short and easy to read on WhatsApp."
    ),
    tools=[check_availability, book_slot]
)

def send_whatsapp_message(to_phone: str, message: str):
    """Sends a text message back to the user via Meta Graph API."""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("WARNING: Meta API keys are missing. Message not sent.")
        return

    url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"preview_url": False, "body": message}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"ERROR sending WhatsApp message: {response.text}")

# 4. Webhook Handshake (GET) for Meta Verification
@app.get("/webhook")
async def verify_webhook(request: Request):
    """Handles the initial verification handshake from Meta."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return Response(content=challenge, media_type="text/plain", status_code=200)
        else:
            return Response(status_code=403)
    return Response(status_code=400)

# 5. Webhook Ingestion (POST) for WhatsApp Messages
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Handles incoming WhatsApp messages directly from Meta."""
    try:
        payload = await request.json()
        
        # Meta sends a specific payload structure. We must parse it to find the message.
        if "object" in payload and payload["object"] == "whatsapp_business_account":
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    
                    if messages:
                        message_obj = messages[0]
                        user_phone = message_obj.get("from")
                        
                        if message_obj.get("type") == "text":
                            user_message = message_obj["text"]["body"]
                            
                            # Hardcode clinic_id for MVP, would normally look up based on META_PHONE_NUMBER_ID
                            demo_clinic_id = "00000000-0000-0000-0000-000000000001"
                            
                            # Execute the agent, injecting the clinic_id context
                            agent_prompt = f"[Context: clinic_id={demo_clinic_id}, phone={user_phone}]\nUser says: {user_message}"
                            response = receptionist_agent.run(agent_prompt)
                            
                            # Send reply back to Meta API
                            send_whatsapp_message(user_phone, response.text)
                            
            return Response(status_code=200)
        else:
            return Response(status_code=404)
    except Exception as e:
        print(f"Webhook Error: {e}")
        return Response(status_code=500)