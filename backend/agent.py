import os
import hmac
import hashlib
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
ADMIN_PIN = os.getenv("ADMIN_PIN", "123456")

# Database Context Helpers
def get_patient_clinic_context(phone_number: str):
    """
    Checks past appointments to find the patient's last visited clinic.
    Args:
        phone_number (str): The patient's WhatsApp number.
    Returns:
        tuple: (clinic_id, clinic_name, booking_mode, extra_context) or (None, None, None, None) if new patient.
    """
    try:
        response = supabase.table("appointments") \
            .select("clinic_id") \
            .eq("phone_number", phone_number) \
            .order("appointment_time", desc=True) \
            .limit(1) \
            .execute()
        if response.data:
            clinic_id = response.data[0]["clinic_id"]
            clinic_resp = supabase.table("clinics").select("business_name, booking_mode, closed_date, working_days, working_hours, current_serving_token").eq("id", clinic_id).execute()
            if clinic_resp.data:
                cdata = clinic_resp.data[0]
                clinic_name = cdata["business_name"]
                booking_mode = cdata.get("booking_mode") or "scheduled"
                
                extra_context = {}
                if cdata.get("closed_date"): extra_context["closed_date"] = cdata["closed_date"]
                if cdata.get("working_days"): extra_context["working_days"] = cdata["working_days"]
                if cdata.get("working_hours"): extra_context["working_hours"] = cdata["working_hours"]
                
                if booking_mode == "token":
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    t_resp = supabase.table("appointments").select("token_number").eq("clinic_id", clinic_id).gte("appointment_time", f"{today_str} 00:00:00").lte("appointment_time", f"{today_str} 23:59:59").not_("token_number", "is", "null").execute()
                    max_t = max([r["token_number"] for r in t_resp.data if r["token_number"] is not None] or [0]) if t_resp.data else 0
                    cur_t = cdata.get("current_serving_token") or 0
                    extra_context["waiting_queue"] = max(0, max_t - cur_t)
            else:
                clinic_name = "Unknown Clinic"
                booking_mode = "scheduled"
                extra_context = {}
            return clinic_id, clinic_name, booking_mode, extra_context
    except Exception as e:
        print(f"Error looking up patient clinic history: {e}")
    return None, None, None, None

def get_all_clinics() -> list:
    """Retrieves all active registered clinics from the database."""
    try:
        response = supabase.table("clinics") \
            .select("id, business_name, trial_end_date, booking_mode") \
            .execute()
        if response.data:
            now = datetime.now()
            # A clinic is active if trial_end_date is NULL (permanent) or in the future
            active_clinics = []
            for c in response.data:
                trial_end = c.get("trial_end_date")
                if not trial_end or datetime.fromisoformat(trial_end.replace('Z', '+00:00')) > now.astimezone():
                    active_clinics.append(c)
            return active_clinics
        return []
    except Exception as e:
        print(f"Error fetching clinics list: {e}")
        return []

def is_clinic_active(clinic_id: str) -> bool:
    """Checks if a clinic's trial is active or permanent."""
    try:
        response = supabase.table("clinics").select("trial_end_date").eq("id", clinic_id).execute()
        if response.data:
            trial_end_date = response.data[0].get("trial_end_date")
            if not trial_end_date:
                return True # Permanent
            return datetime.fromisoformat(trial_end_date.replace('Z', '+00:00')) > datetime.now().astimezone()
    except Exception as e:
        print(f"Error checking clinic active status: {e}")
    return False

# Rate Limiting Helper
def check_and_increment_usage() -> bool:
    """
    Checks if the monthly API usage is under the strict limit of 990.
    If it is, increments the usage count.
    Returns True if allowed, False if limit exceeded.
    """
    try:
        current_month = datetime.now().strftime("%Y-%m")
        # Fetch current count
        response = supabase.table("api_usage").select("message_count").eq("month_year", current_month).execute()
        
        if response.data:
            current_count = response.data[0]["message_count"]
            if current_count >= 990:
                print(f"CRITICAL: Monthly limit of 990 reached for {current_month}. Message ignored.")
                return False
            else:
                # Increment
                supabase.table("api_usage").update({"message_count": current_count + 1}).eq("month_year", current_month).execute()
                return True
        else:
            # First message of the month
            supabase.table("api_usage").insert({"month_year": current_month, "message_count": 1}).execute()
            return True
            
    except Exception as e:
        print(f"Error checking API usage: {e}")
        # Fail closed to prevent accidental billing
        print("Failing closed to prevent accidental billing.")
        return False

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
            .gte("appointment_time", f"{date_str} 00:00:00") \
            .lte("appointment_time", f"{date_str} 23:59:59") \
            .execute()
            
        booked_dts = []
        for record in response.data:
            # Handle both "YYYY-MM-DD HH:MM" and "YYYY-MM-DDTHH:MM:SS" formats
            dt_str = record["appointment_time"].replace("T", " ")[:16]
            booked_dts.append(datetime.strptime(dt_str, "%Y-%m-%d %H:%M"))
            
        import random
        available_slots = []
        now = datetime.now()
        is_today = (date_str == now.strftime("%Y-%m-%d"))
        
        for h in range(10, 20):
            for m in (0, 10, 20, 30, 40, 50):
                slot_str = f"{date_str} {h:02d}:{m:02d}"
                slot_dt = datetime.strptime(slot_str, "%Y-%m-%d %H:%M")
                
                # If booking for today, don't suggest past times
                if is_today and slot_dt < now:
                    continue
                    
                conflict = False
                for b_dt in booked_dts:
                    if abs((b_dt - slot_dt).total_seconds()) < 600: # 10 minutes
                        conflict = True
                        break
                if not conflict:
                    available_slots.append(f"{h:02d}:{m:02d}")
                    
        suggested = random.sample(available_slots, min(5, len(available_slots)))
        suggested.sort()
        
        return {
            "status": "success",
            "all_available_slots": available_slots,
            "suggested_available_slots": suggested,
            "instruction": "DO NOT show the full list to the user. Offer ONLY the 'suggested_available_slots'. But if the user asks for a specific time, check if it exists in 'all_available_slots'."
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
        # Fetch clinic settings
        clinic_resp = supabase.table("clinics").select("closed_date, working_days, working_hours").eq("id", clinic_id).execute()
        if clinic_resp.data:
            cdata = clinic_resp.data[0]
            if cdata.get("closed_date") == date_str:
                 return {"status": "error", "message": f"CRITICAL: The clinic is closed on {date_str}. Offer another date."}
            
            target_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
            day_name = target_dt.strftime("%A")
            
            working_days = cdata.get("working_days") or []
            if working_days and day_name not in working_days:
                 return {"status": "error", "message": f"CRITICAL: The clinic is closed on {day_name}s. Offer another date."}
                 
            working_hours = cdata.get("working_hours") or {}
            if working_hours:
                start_time = datetime.strptime(working_hours.get("start", "00:00"), "%H:%M").time()
                end_time = datetime.strptime(working_hours.get("end", "23:59"), "%H:%M").time()
                if not (start_time <= target_dt.time() <= end_time):
                    return {"status": "error", "message": f"CRITICAL: Requested time is outside working hours ({start_time} to {end_time}). Offer another time."}

        # 1. Check if time is in the past
        target_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
        if target_dt < datetime.now():
            return {"status": "error", "message": "CRITICAL: Cannot book appointments in the past. Ask the user for a future date/time."}
            
        # 2. Check for 10-minute conflicts
        start_window = (target_dt - timedelta(minutes=9)).strftime("%Y-%m-%d %H:%M:%S")
        end_window = (target_dt + timedelta(minutes=9)).strftime("%Y-%m-%d %H:%M:%S")
        
        conflict_check = supabase.table("appointments") \
            .select("appointment_time") \
            .eq("clinic_id", clinic_id) \
            .gte("appointment_time", start_window) \
            .lte("appointment_time", end_window) \
            .execute()
            
        if conflict_check.data:
            return {"status": "error", "message": "CRITICAL: Slot is taken (another patient is booked within 10 minutes of this time). Apologize and offer another time."}

        # 2. Insert if free
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

def generate_token(clinic_id: str, phone_number: str, patient_name: str = "Unknown") -> dict:
    """Generates a queue token for clinics in token mode."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        # Get current max token for today
        response = supabase.table("appointments") \
            .select("token_number") \
            .eq("clinic_id", clinic_id) \
            .gte("appointment_time", f"{today_str} 00:00:00") \
            .lte("appointment_time", f"{today_str} 23:59:59") \
            .not_("token_number", "is", "null") \
            .execute()
            
        next_token = 1
        if response.data:
            tokens = [r["token_number"] for r in response.data if r["token_number"] is not None]
            if tokens:
                next_token = max(tokens) + 1
                
        # Get currently serving token and clinic settings
        clinic_resp = supabase.table("clinics").select("current_serving_token, closed_date, working_days, working_hours").eq("id", clinic_id).execute()
        cdata = clinic_resp.data[0] if clinic_resp.data else {}
        current_serving = cdata.get("current_serving_token", 0)
        
        if cdata.get("closed_date") == today_str:
            return {"status": "error", "message": "CRITICAL: The clinic is closed for today. Tell the patient no more tokens are being issued today."}
        
        now = datetime.now()
        day_name = now.strftime("%A")
        working_days = cdata.get("working_days") or []
        working_hours = cdata.get("working_hours") or {}
        if working_days and day_name not in working_days:
            return {"status": "error", "message": f"CRITICAL: The clinic is closed today ({day_name}). Tell the patient."}
        if working_hours:
            start_time = datetime.strptime(working_hours.get("start", "00:00"), "%H:%M").time()
            end_time = datetime.strptime(working_hours.get("end", "23:59"), "%H:%M").time()
            if not (start_time <= now.time() <= end_time):
                return {"status": "error", "message": f"CRITICAL: The clinic is closed right now. Working hours are {start_time} to {end_time}. Tell the patient."}
                
        # Insert appointment with token
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        supabase.table("appointments").insert({
            "clinic_id": clinic_id,
            "phone_number": phone_number,
            "patient_name": patient_name,
            "appointment_time": timestamp,
            "status": "booked",
            "token_number": next_token
        }).execute()
        
        people_ahead = max(0, next_token - current_serving - 1)
        
        return {
            "status": "success",
            "message": f"Successfully generated Token #{next_token}. There are {people_ahead} people ahead of them in the queue. Tell this to the patient."
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

# 3. Initialize the Groq Client
client = Groq() # automatically looks for GROQ_API_KEY in env

instruction = (
    "You are a professional, highly efficient clinic receptionist chatbot. Keep all messages MINIMAL and straight to the point (fixing an appointment). Avoid unnecessary conversational fluff.\n"
    "LANGUAGE PREFERENCE:\n"
    "- On your first message, ask the user to choose their preferred language (e.g., English or Hindi).\n"
    "- CRITICAL RULE FOR HINDI: If the user speaks Hindi, you MUST reply ONLY in pure Devanagari script (e.g. नमस्ते). NEVER use Hinglish.\n\n"
    "CLINIC ROUTING RULES:\n"
    "1. Check the [Context] injected at the start of the prompt for `booking_mode` and `clinic_id`.\n"
    "2. If `clinic_id` is present, acknowledge it (e.g. 'Welcome back to [Clinic Name]'). Do NOT ask which clinic they want UNLESS the patient explicitly asks to change clinics.\n"
    "3. If `IS_FIRST_TIME=True` OR the patient asks to switch clinics, present the list of available clinic NAMES from the context and ask them to choose. (Never show the internal ID). IMPORTANT: Once they choose a clinic from the list, apply the rules below based on the `booking_mode` shown for that specific clinic in the list!\n"
    "4. IF booking_mode='scheduled': Ask for their preferred date, time and name. IMPORTANT: Do NOT list available slots preemptively. Only use `check_availability` to check the specific time they requested, or to list slots ONLY IF they explicitly ask 'what slots are available'. Then call `book_slot`.\n"
    "5. IF booking_mode='token': The clinic uses a Live Token Queue. If `waiting_queue` is in the Context, IMMEDIATELY tell the patient how many people are currently waiting before they even book. Do NOT ask for a date or time. Just ask for the patient's name, then call `generate_token`.\n\n"
    "OFF-TOPIC PREVENTION:\n"
    "- If the user asks ANY question unrelated to clinic appointments, politely decline with a standard reply: 'I can only assist with booking appointments. How can I help you schedule a visit today?'\n"
)

groq_tools = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Checks Supabase for booked slots on a specific date for a specific clinic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clinic_id": {"type": "string"},
                    "date_str": {"type": "string", "description": "Date in YYYY-MM-DD format"}
                },
                "required": ["clinic_id", "date_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_slot",
            "description": "Books the appointment slot in the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clinic_id": {"type": "string"},
                    "phone_number": {"type": "string"},
                    "date_str": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "HH:MM"},
                    "patient_name": {"type": "string"}
                },
                "required": ["clinic_id", "phone_number", "date_str", "time_str", "patient_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_token",
            "description": "Generates a live queue token for clinics operating in token mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clinic_id": {"type": "string"},
                    "phone_number": {"type": "string"},
                    "patient_name": {"type": "string"}
                },
                "required": ["clinic_id", "phone_number", "patient_name"]
            }
        }
    }
]

# In-memory dictionary to hold multi-turn conversation history per phone number
chat_sessions = {}

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

def send_whatsapp_template(to_phone: str, template_name: str, language_code: str = "en_US"):
    """Sends a pre-approved template message via Meta Graph API."""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("WARNING: Meta API keys are missing. Template not sent.")
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
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"ERROR sending WhatsApp template: {response.text}")
        # Fallback to standard text message if the template fails (e.g., due to language mismatch or review status)
        fallback_msg = "Your appointment has been cancelled. Thank you."
        if template_name == "visit_thanks":
            fallback_msg = "Thank you for visiting! We hope you have a great day."
        print(f"Attempting fallback to text message for {to_phone}...")
        send_whatsapp_message(to_phone, fallback_msg)

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

class OnboardRequest(BaseModel):
    pin: str
    business_name: str
    admin_email: str
    password: str
    booking_mode: str = "scheduled"
    working_days: list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    working_hours: dict = {"start": "09:00", "end": "21:00"}

@app.post("/api/admin/onboard")
async def onboard_clinic(req: OnboardRequest):
    """Secure endpoint to create a new clinic and its auth user."""
    if req.pin != ADMIN_PIN:
        return Response(status_code=401, content="Invalid PIN")
        
    try:
        # 1. Create Supabase Auth User using Admin API
        auth_response = supabase.auth.admin.create_user({
            "email": req.admin_email,
            "password": req.password,
            "email_confirm": True
        })
        user_id = auth_response.user.id
        
        # 2. Insert into Clinics table with 7-day trial
        trial_end = (datetime.now() + timedelta(days=7)).isoformat()
        
        # We use the shared META_PHONE_NUMBER_ID for the MVP
        clinic_response = supabase.table("clinics").insert({
            "business_name": req.business_name,
            "meta_phone_number_id": META_PHONE_NUMBER_ID or "NOT_SET",
            "admin_email": req.admin_email,
            "admin_auth_uid": user_id,
            "trial_end_date": trial_end,
            "booking_mode": req.booking_mode,
            "working_days": req.working_days,
            "working_hours": req.working_hours
        }).execute()
        
        clinic_id = clinic_response.data[0]["id"]
        
        # 3. Store clinic_id in user metadata for easy access on the frontend
        supabase.auth.admin.update_user_by_id(user_id, {"user_metadata": {"clinic_id": clinic_id}})
        
        return {"status": "success", "clinic_id": clinic_id, "trial_end_date": trial_end}
    except Exception as e:
        print(f"Error onboarding: {e}")
        # Return JSONResponse instead of raw Response so CORS middleware processes it properly
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

class UpgradeRequest(BaseModel):
    pin: str
    clinic_id: str

@app.post("/api/admin/upgrade")
async def upgrade_clinic(req: UpgradeRequest):
    """Secure endpoint to upgrade a clinic to a permanent account."""
    if req.pin != ADMIN_PIN:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"detail": "Invalid PIN"})
    try:
        # Set trial_end_date to NULL to make it permanent
        supabase.table("clinics").update({"trial_end_date": None}).eq("id", req.clinic_id).execute()
        return {"status": "success", "message": "Clinic upgraded to permanent account."}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

class StatusUpdateRequest(BaseModel):
    status: str

@app.put("/api/admin/appointments/{appointment_id}/status")
async def update_appointment_status(appointment_id: str, req: StatusUpdateRequest):
    """Updates appointment status and sends automated WhatsApp messages."""
    try:
        # 1. Fetch appointment details to get patient phone and clinic_id
        apt_response = supabase.table("appointments").select("phone_number, clinic_id, patient_name").eq("id", appointment_id).execute()
        if not apt_response.data:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": "Appointment not found"})
            
        apt = apt_response.data[0]
        patient_phone = apt["phone_number"]
        clinic_id = apt["clinic_id"]
        
        # 2. Update the status in the database
        supabase.table("appointments").update({"status": req.status}).eq("id", appointment_id).execute()
        
        # 3. Trigger WhatsApp template messages based on new status
        if req.status == 'completed' or req.status == 'cancelled':
            # Fetch clinic name dynamically for the template
            clinic_resp = supabase.table("clinics").select("business_name").eq("id", clinic_id).execute()
            clinic_name = clinic_resp.data[0]["business_name"] if clinic_resp.data else "our clinic"
            
            # Send Meta Template Message
            if META_ACCESS_TOKEN and META_PHONE_NUMBER_ID:
                url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
                headers = {
                    "Authorization": f"Bearer {META_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                }
                
                template_name = "visit_thanks" if req.status == 'completed' else "appointment_cancelled"
                
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": patient_phone,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {
                            "code": "en"
                        },
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {
                                        "type": "text",
                                        "text": clinic_name
                                    }
                                ]
                            }
                        ]
                    }
                }
                # Fire and forget
                requests.post(url, headers=headers, json=payload)
                print(f"Sent '{template_name}' template to {patient_phone}")
                
        return {"status": "success", "message": f"Status updated to {req.status}"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

# 5. Webhook Ingestion (POST) for WhatsApp Messages (Secured with Signature check)

def process_whatsapp_message(payload: dict):
    """Background task to process the incoming message without delaying the webhook response."""
    try:
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
                            # CRITICAL: Strict rate limiting check
                            if not check_and_increment_usage():
                                return
                                
                            user_message = message_obj["text"]["body"]
                            
                            # Retrieve smart clinic context based on patient booking history
                            clinic_id, clinic_name, booking_mode, extra_context = get_patient_clinic_context(user_phone)
                            
                            if clinic_id:
                                if not is_clinic_active(clinic_id):
                                    print(f"Ignored message: Clinic {clinic_id} trial expired.")
                                    return
                                    
                                # Returning patient - auto route to their clinic
                                clinics = get_all_clinics()
                                clinics_str = ", ".join([f"[Name: '{c['business_name']}', Internal_ID: '{c['id']}', booking_mode: '{c.get('booking_mode', 'scheduled')}']" for c in clinics])
                                context = f"[Context: clinic_id={clinic_id}, clinic_name='{clinic_name}', booking_mode='{booking_mode}', phone={user_phone}, available_clinics={clinics_str}, clinic_settings={json.dumps(extra_context)}]"
                            else:
                                # First time patient - fetch all available clinics to display options
                                clinics = get_all_clinics()
                                clinics_str = ", ".join([f"[Name: '{c['business_name']}', Internal_ID: '{c['id']}', booking_mode: '{c.get('booking_mode', 'scheduled')}']" for c in clinics])
                                context = f"[Context: phone={user_phone}, IS_FIRST_TIME=True, available_clinics={clinics_str}]"
                                
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            agent_prompt = f"[Current System Time: {current_time}]\n{context}\nUser says: {user_message}"
                            
                            # Retrieve or create a chat session for this user to maintain multi-turn history
                            if user_phone not in chat_sessions:
                                chat_sessions[user_phone] = [{"role": "system", "content": instruction}]
                                
                            chat_sessions[user_phone].append({"role": "user", "content": agent_prompt})
                                
                            try:
                                while True:
                                    response = client.chat.completions.create(
                                        model="llama-3.1-8b-instant",
                                        messages=chat_sessions[user_phone],
                                        tools=groq_tools,
                                        tool_choice="auto",
                                        temperature=0.4
                                    )
                                    
                                    response_message = response.choices[0].message
                                    chat_sessions[user_phone].append(response_message)
                                    
                                    # Fallback manual parsing for Llama 3 tool hallucinations
                                    fallback_tool_executed = False
                                    if not response_message.tool_calls and response_message.content:
                                        match = re.search(r'[\(<]function=(\w+)>(.*?)</function[\)>]?', response_message.content, re.DOTALL)
                                        if match:
                                            function_name = match.group(1)
                                            try:
                                                function_args = json.loads(match.group(2))
                                                if function_name == "check_availability":
                                                    result = check_availability(function_args.get("clinic_id"), function_args.get("date_str"))
                                                elif function_name == "book_slot":
                                                    result = book_slot(function_args.get("clinic_id"), function_args.get("phone_number"), function_args.get("date_str"), function_args.get("time_str"), function_args.get("patient_name", "Unknown"))
                                                elif function_name == "generate_token":
                                                    result = generate_token(function_args.get("clinic_id"), function_args.get("phone_number"), function_args.get("patient_name", "Unknown"))
                                                else:
                                                    result = {"error": "Unknown function"}
                                                    
                                                # Simulate tool response so the model can read it
                                                chat_sessions[user_phone].append({"role": "user", "content": f"System Tool Result from {function_name}: {json.dumps(result)}"})
                                                fallback_tool_executed = True
                                            except json.JSONDecodeError:
                                                pass

                                    if response_message.tool_calls:
                                        for tool_call in response_message.tool_calls:
                                            function_name = tool_call.function.name
                                            function_args = json.loads(tool_call.function.arguments)
                                            
                                            if function_name == "check_availability":
                                                result = check_availability(function_args.get("clinic_id"), function_args.get("date_str"))
                                            elif function_name == "book_slot":
                                                result = book_slot(function_args.get("clinic_id"), function_args.get("phone_number"), function_args.get("date_str"), function_args.get("time_str"), function_args.get("patient_name", "Unknown"))
                                            elif function_name == "generate_token":
                                                result = generate_token(function_args.get("clinic_id"), function_args.get("phone_number"), function_args.get("patient_name", "Unknown"))
                                            else:
                                                result = {"error": "Unknown function"}
                                                
                                            chat_sessions[user_phone].append({
                                                "tool_call_id": tool_call.id,
                                                "role": "tool",
                                                "name": function_name,
                                                "content": json.dumps(result)
                                            })
                                        # Loop continues to send tool results back to Groq
                                    elif fallback_tool_executed:
                                        # Loop again to let AI process the fallback tool result!
                                        continue
                                    else:
                                        # Final text response
                                        if response_message.content:
                                            # Clean any weird tags just in case before sending to WhatsApp
                                            clean_text = re.sub(r'[\(<]function=.*?</function[\)>]?', '', response_message.content, flags=re.DOTALL).strip()
                                            if clean_text:
                                                send_whatsapp_message(user_phone, clean_text)
                                        break
                                        
                            except Exception as api_err:
                                error_str = str(api_err)
                                if "429" in error_str or "rate limit" in error_str.lower():
                                    send_whatsapp_message(user_phone, "Our AI receptionist is currently experiencing high traffic. Please wait about 1 minute and send your message again!")
                                    print(f"API Rate limit hit for {user_phone}: {error_str}")
                                else:
                                    print(f"Agent processing error: {error_str}")
    except Exception as general_err:
        print(f"Error in background processing: {general_err}")

@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handles incoming WhatsApp messages directly from Meta."""
    if not await verify_signature(request):
        return Response(status_code=401, content="Invalid signature validation.")

    try:
        payload = await request.json()
        background_tasks.add_task(process_whatsapp_message, payload)
        return Response(status_code=200)
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return Response(status_code=200)
class CallNextRequest(BaseModel):
    clinic_id: str
    current_token: int

@app.post("/api/queue/call-next")
def api_call_next(req: CallNextRequest, bg_tasks: BackgroundTasks):
    """Marks current as completed, updates counter, and alerts next patients."""
    try:
        # 1. Update current to completed and send Thanks
        resp1 = supabase.table("appointments").select("id, phone_number").eq("clinic_id", req.clinic_id).eq("token_number", req.current_token).order("created_at", desc=True).limit(1).execute()
        if resp1.data:
            apt = resp1.data[0]
            supabase.table("appointments").update({"status": "completed"}).eq("id", apt["id"]).execute()
            bg_tasks.add_task(send_whatsapp_template, apt["phone_number"], "visit_thanks")
            
        # 2. Update clinics counter
        new_token = req.current_token + 1
        supabase.table("clinics").update({"current_serving_token": new_token}).eq("id", req.clinic_id).execute()
        
        # 3. Alert 2nd next in queue
        target_token = new_token + 1
        resp2 = supabase.table("appointments").select("phone_number").eq("clinic_id", req.clinic_id).eq("token_number", target_token).order("created_at", desc=True).limit(1).execute()
        if resp2.data:
            bg_tasks.add_task(send_whatsapp_message, resp2.data[0]["phone_number"], f"Get ready! Your token (#{target_token}) is almost up. Please make sure you are near the clinic.")
            
        return {"status": "success", "new_token": new_token}
    except Exception as e:
        print("Error in call_next:", e)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

class CancelTokenRequest(BaseModel):
    clinic_id: str
    appointment_id: str

@app.post("/api/queue/cancel-token")
def api_cancel_token(req: CancelTokenRequest, bg_tasks: BackgroundTasks):
    """Cancels a token and notifies the patient."""
    try:
        resp = supabase.table("appointments").select("phone_number, token_number").eq("id", req.appointment_id).execute()
        if resp.data:
            apt = resp.data[0]
            supabase.table("appointments").update({"status": "cancelled"}).eq("id", req.appointment_id).execute()
            bg_tasks.add_task(send_whatsapp_template, apt["phone_number"], "appointment_cancelled")
        return {"status": "success"}
    except Exception as e:
        print("Error in cancel_token:", e)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

class CloseDayRequest(BaseModel):
    clinic_id: str

@app.post("/api/queue/close-day")
def api_close_day(req: CloseDayRequest, bg_tasks: BackgroundTasks):
    """Closes the clinic for the rest of the day and cancels remaining booked appointments."""
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 1. Set closed_date
        supabase.table("clinics").update({"closed_date": today_str}).eq("id", req.clinic_id).execute()
        
        # 2. Find all remaining booked appointments for today
        resp = supabase.table("appointments") \
            .select("id, phone_number") \
            .eq("clinic_id", req.clinic_id) \
            .eq("status", "booked") \
            .gte("appointment_time", f"{today_str} 00:00:00") \
            .lte("appointment_time", f"{today_str} 23:59:59") \
            .execute()
            
        if resp.data:
            for apt in resp.data:
                supabase.table("appointments").update({"status": "cancelled"}).eq("id", apt["id"]).execute()
                bg_tasks.add_task(send_whatsapp_template, apt["phone_number"], "appointment_cancelled")
                
        return {"status": "success", "message": f"Closed clinic and cancelled {len(resp.data) if resp.data else 0} appointments."}
    except Exception as e:
        print("Error in close_day:", e)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=True)