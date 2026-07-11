import os
import hmac
import hashlib
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
META_CLIENT_SECRET = os.getenv("META_CLIENT_SECRET")

# Database Context Helpers
def get_patient_clinic_context(phone_number: str) -> str:
    """
    Checks past appointments to find the patient's last visited clinic ID.
    Args:
        phone_number (str): The patient's WhatsApp number.
    Returns:
        str: The clinic UUID or None if new patient.
    """
    try:
        response = supabase.table("appointments") \
            .select("clinic_id") \
            .eq("phone_number", phone_number) \
            .order("appointment_time", desc=True) \
            .limit(1) \
            .execute()
        if response.data:
            return response.data[0]["clinic_id"]
    except Exception as e:
        print(f"Error looking up patient clinic history: {e}")
    return None

def get_all_clinics() -> list:
    """Retrieves all registered clinics from the database."""
    try:
        response = supabase.table("clinics") \
            .select("id, business_name") \
            .execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching clinics list: {e}")
        return []

# Signature Verification Helper
async def verify_signature(request: Request) -> bool:
    """Verifies that the request signature matches Meta client secret to secure the webhook."""
    if not META_CLIENT_SECRET:
        # Bypassed if no secret is set (useful for local dev/testing)
        return True
        
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header or not signature_header.startswith("sha256="):
        return False
        
    expected_sig = signature_header.split("sha256=")[1]
    body = await request.body()
    
    computed_sig = hmac.new(
        META_CLIENT_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_sig, computed_sig)


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
        error_msg = str(e)
        if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower() or "23505" in error_msg:
            return {"status": "error", "message": "CRITICAL: Slot taken. Apologize and offer another time."}
        return {"status": "error", "message": f"Database error: {error_msg}"}

# 3. Initialize the Google ADK Agent (Hindi by default)
receptionist_agent = Agent(
    name="whatsapp_receptionist",
    model="gemini-2.5-flash",
    description="A Hindi-speaking clinic receptionist.",
    instruction=(
        "You are a helpful and polite clinic receptionist. Speak entirely in clean, polite Hindi (using Devanagari script). "
        "Your goal is to book appointment slots for patients.\n\n"
        "CLINIC ROUTING RULES:\n"
        "1. Check the context injected at the start of the prompt.\n"
        "2. If `clinic_id` is present, it means the patient has a history with this clinic. Immediately greet them, check availability for that clinic using `check_availability`, and guide them to confirm a slot. Do NOT ask them which clinic they want to visit.\n"
        "3. If `IS_FIRST_TIME=True` or `clinic_id` is missing, you MUST present the list of available clinics (which will be provided in the context) and politely ask the patient to choose which clinic they would like to visit.\n"
        "4. Once a clinic is identified or selected, ask for their preferred time and name, and then call `book_slot` to save the appointment.\n\n"
        "Keep your WhatsApp messages warm, short, and formatted with spacing for readability."
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

# 5. Webhook Ingestion (POST) for WhatsApp Messages (Secured with Signature check)
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Handles incoming WhatsApp messages directly from Meta."""
    if not await verify_signature(request):
        return Response(status_code=401, content="Invalid signature validation.")

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
                            
                            # Retrieve smart clinic context based on patient booking history
                            clinic_id = get_patient_clinic_context(user_phone)
                            
                            if clinic_id:
                                # Returning patient - auto route to their clinic
                                context = f"[Context: clinic_id={clinic_id}, phone={user_phone}]"
                            else:
                                # First time patient - fetch all available clinics to display options
                                clinics = get_all_clinics()
                                clinics_str = ", ".join([f"{c['business_name']} (ID: {c['id']})" for c in clinics])
                                context = f"[Context: phone={user_phone}, IS_FIRST_TIME=True, available_clinics=[{clinics_str}]]"
                                
                            agent_prompt = f"{context}\nUser says: {user_message}"
                            response = receptionist_agent.run(agent_prompt)
                            
                            # Send reply back to Meta API
                            send_whatsapp_message(user_phone, response.text)
                            
            return Response(status_code=200)
        else:
            return Response(status_code=404)
    except Exception as e:
        print(f"Webhook Error: {e}")
        return Response(status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=True)