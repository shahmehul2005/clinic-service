import os
import hmac
import hashlib
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
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
    """Retrieves all active registered clinics from the database."""
    try:
        response = supabase.table("clinics") \
            .select("id, business_name, trial_end_date") \
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
            
        booked = [record["appointment_time"] for record in response.data]
        
        return {
            "status": "success",
            "clinic_hours": "10:00 AM to 8:00 PM, 10-minute slots",
            "already_booked_slots": booked,
            "instruction": "Offer the user 2 or 3 available slot times that are AT LEAST 10 minutes apart from any already_booked_slots."
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
        # 1. Check for 10-minute conflicts
        target_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
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

# 3. Initialize the Groq Client
client = Groq() # automatically looks for GROQ_API_KEY in env

instruction = (
    "You are a professional, friendly clinic receptionist chatbot. You must stay focused on your primary goal: guiding the patient through a flow to book an appointment.\n"
    "While you can be warm and lightly creative in your greetings, do not deviate into unrelated chatting. Maintain a clear schema for booking.\n\n"
    "LANGUAGE PREFERENCE:\n"
    "- On your very first message, briefly greet the user and ask them to choose their preferred language (e.g., English or Hindi).\n"
    "- Once they choose, speak entirely in that language for the rest of the conversation.\n\n"
    "CLINIC ROUTING RULES:\n"
    "1. Check the [Context] injected at the start of the prompt.\n"
    "2. If `clinic_id` is present, the patient has a history with this clinic. Acknowledge this, check availability for that clinic using `check_availability`, and guide them to confirm a slot. Do NOT ask them which clinic they want to visit.\n"
    "3. If `IS_FIRST_TIME=True` or `clinic_id` is missing, present the list of available clinic NAMES and politely ask the patient to choose. CRITICAL: NEVER show the Clinic ID (the long string of letters/numbers) to the patient. Keep the IDs hidden for your internal use only.\n"
    "4. Once a clinic is identified, ask for their preferred date/time and name. Then call `book_slot` to save the appointment.\n\n"
    "Keep your WhatsApp messages warm, short, and formatted with spacing for readability."
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
            "trial_end_date": trial_end
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
                            # CRITICAL: Strict rate limiting check
                            if not check_and_increment_usage():
                                return Response(status_code=200) # Return 200 so Meta stops retrying
                                
                            user_message = message_obj["text"]["body"]
                            
                            # Retrieve smart clinic context based on patient booking history
                            clinic_id = get_patient_clinic_context(user_phone)
                            
                            if clinic_id:
                                if not is_clinic_active(clinic_id):
                                    print(f"Ignored message: Clinic {clinic_id} trial expired.")
                                    return Response(status_code=200)
                                    
                                # Returning patient - auto route to their clinic
                                context = f"[Context: clinic_id={clinic_id}, phone={user_phone}]"
                            else:
                                # First time patient - fetch all available clinics to display options
                                clinics = get_all_clinics()
                                clinics_str = ", ".join([f"[Name: '{c['business_name']}', Internal_ID: '{c['id']}']" for c in clinics])
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
                                        match = re.search(r'<function=(\w+)>(.*?)</function>', response_message.content, re.DOTALL)
                                        if match:
                                            function_name = match.group(1)
                                            try:
                                                function_args = json.loads(match.group(2))
                                                if function_name == "check_availability":
                                                    result = check_availability(function_args.get("clinic_id"), function_args.get("date_str"))
                                                elif function_name == "book_slot":
                                                    result = book_slot(function_args.get("clinic_id"), function_args.get("phone_number"), function_args.get("date_str"), function_args.get("time_str"), function_args.get("patient_name", "Unknown"))
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
                                            clean_text = re.sub(r'<function=.*?</function>', '', response_message.content, flags=re.DOTALL).strip()
                                            if clean_text:
                                                send_whatsapp_message(user_phone, clean_text)
                                        break
                                        
                            except Exception as api_err:
                                error_str = str(api_err)
                                if "429" in error_str or "rate limit" in error_str.lower():
                                    send_whatsapp_message(user_phone, "Our AI receptionist is currently experiencing high traffic. Please wait about 1 minute and send your message again!")
                                    print(f"API Rate limit hit for {user_phone}: {error_str}")
                                else:
                                    raise api_err
                            
            return Response(status_code=200)
        else:
            return Response(status_code=404)
    except Exception as e:
        print(f"Webhook Error: {e}")
        return Response(status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=True)