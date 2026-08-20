import os
import hmac
import hashlib
import requests
import asyncio
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv

from ops import call_rpc, get_now, iter_slots, serialize_messages, trim_messages
from workflow import default_workflow, handle_turn

load_dotenv()

# Timezone Helper (kept for tests that patch agent.IST / agent.get_now)
IST = timezone(timedelta(hours=5, minutes=30))


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    enabled = os.getenv("ENABLE_BACKGROUND_JOBS", "1").lower() not in ("0", "false", "no")
    if enabled:
        task = asyncio.create_task(reminder_worker())
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)

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
def get_patient_name(phone_number: str) -> str:
    """
    Checks past appointments to find the patient's name to save them from re-typing it.
    """
    try:
        response = supabase.table("appointments") \
            .select("patient_name") \
            .eq("phone_number", phone_number) \
            .order("appointment_time", desc=True) \
            .limit(1) \
            .execute()
        if response.data:
            return response.data[0].get("patient_name", "")
    except Exception as e:
        print(f"Error looking up patient name: {e}")
    return ""

def get_all_clinics() -> list:
    """Retrieves all active registered clinics and their live stats."""
    try:
        response = supabase.table("clinics") \
            .select("id, business_name, trial_end_date, booking_mode, current_serving_token, closed_date, working_days, working_hours") \
            .execute()
        if response.data:
            now = get_now()
            today_str = now.strftime("%Y-%m-%d")
            active_clinics = []
            for c in response.data:
                trial_end = c.get("trial_end_date")
                if not trial_end or datetime.fromisoformat(trial_end.replace('Z', '+00:00')) > now.astimezone():
                    # Calculate token queue if token mode
                    if c.get("booking_mode") == "token":
                        t_resp = supabase.table("appointments").select("token_number").eq("clinic_id", c["id"]).gte("appointment_time", f"{today_str} 00:00:00").lte("appointment_time", f"{today_str} 23:59:59").execute()
                        max_t = max([r["token_number"] for r in t_resp.data if r["token_number"] is not None] or [0]) if t_resp.data else 0
                        cur_t = c.get("current_serving_token") or 0
                        c["waiting_queue"] = max(0, max_t - cur_t)
                        c["last_token"] = max_t
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
            return datetime.fromisoformat(trial_end_date.replace('Z', '+00:00')) > get_now().astimezone()
    except Exception as e:
        print(f"Error checking clinic active status: {e}")
    return False

# Rate Limiting Helper
def check_and_increment_usage() -> bool:
    """Atomically increment monthly LLM usage. Fail closed on errors."""
    try:
        result = call_rpc(supabase, "increment_api_usage", {"p_limit": 990})
        if result is True or result is False:
            allowed = bool(result)
        elif isinstance(result, dict) and "message" in result and result.get("status") == "error":
            print(f"Error checking API usage: {result['message']}")
            print("Failing closed to prevent accidental billing.")
            return False
        else:
            allowed = bool(result)
        if not allowed:
            print("CRITICAL: Monthly limit of 990 reached. Message ignored.")
        return allowed
    except Exception as e:
        print(f"Error checking API usage: {e}")
        print("Failing closed to prevent accidental billing.")
        return False

# Signature Verification Helper
async def verify_signature(request: Request) -> bool:
    """Verifies that the request signature matches Meta client secret to secure the webhook."""
    secret = os.getenv("META_CLIENT_SECRET") or META_CLIENT_SECRET
    if not secret:
        # Bypassed if no secret is set (useful for local dev/testing)
        return True
        
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header or not signature_header.startswith("sha256="):
        return False
        
    expected_sig = signature_header.split("sha256=")[1]
    body = await request.body()
    
    computed_sig = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_sig, computed_sig)


# 2. Booking tools (writes go through Postgres RPCs for row locks + unique slots)

def check_availability(clinic_id: str, date_str: str) -> dict:
    """Lists free canonical slots for a scheduled clinic on one date."""
    try:
        clinic_resp = supabase.table("clinics").select(
            "booking_mode, closed_date, working_days, working_hours, slot_duration_minutes"
        ).eq("id", clinic_id).execute()
        if not clinic_resp.data:
            return {"status": "error", "message": "Clinic not found."}
        cdata = clinic_resp.data[0]
        if cdata.get("booking_mode") == "token":
            return {"status": "error", "message": "CRITICAL: Token clinic. Call generate_token instead of check_availability."}

        duration = int(cdata.get("slot_duration_minutes") or 10)
        working_hours = cdata.get("working_hours") or {"start": "09:00", "end": "21:00"}
        working_days = cdata.get("working_days") or []
        target_day = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = target_day.strftime("%A")
        if working_days and day_name not in working_days:
            return {"status": "error", "message": f"CRITICAL: The clinic is closed on {day_name}s. Offer another date."}
        if cdata.get("closed_date") == date_str:
            return {"status": "error", "message": f"CRITICAL: The clinic is closed on {date_str}. Offer another date."}

        booked_resp = supabase.table("appointments").select("slot_start, appointment_time").eq(
            "clinic_id", clinic_id
        ).gte("appointment_time", f"{date_str} 00:00:00").lte(
            "appointment_time", f"{date_str} 23:59:59"
        ).execute()

        booked = set()
        for record in (booked_resp.data or []):
            raw = record.get("slot_start") or record.get("appointment_time")
            if not raw:
                continue
            booked.add(str(raw).replace("T", " ")[:16])

        now = get_now()
        available_slots = []
        for slot_dt in iter_slots(date_str, working_hours, duration, now):
            key = slot_dt.strftime("%Y-%m-%d %H:%M")
            if key not in booked:
                available_slots.append(slot_dt.strftime("%H:%M"))

        import random
        suggested = random.sample(available_slots, min(5, len(available_slots)))
        suggested.sort()

        return {
            "status": "success",
            "slot_duration_minutes": duration,
            "all_available_slots": available_slots,
            "suggested_available_slots": suggested,
            "instruction": "DO NOT show the full list to the user. Offer ONLY the 'suggested_available_slots'. But if the user asks for a specific time, check if it exists in 'all_available_slots'."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def book_slot(clinic_id: str, phone_number: str, date_str: str, time_str: str, patient_name: str = "Unknown") -> dict:
    """Atomically books a canonical slot (Postgres lock + unique slot_start)."""
    time_str = (time_str or "")[:5]
    timestamp = f"{date_str} {time_str}"
    return call_rpc(supabase, "book_slot_atomic", {
        "p_clinic_id": clinic_id,
        "p_phone_number": phone_number,
        "p_patient_name": patient_name,
        "p_appointment_time": timestamp,
    })

def generate_token(clinic_id: str, phone_number: str, patient_name: str = "Unknown") -> dict:
    """Atomically issues the next token under a clinic row lock."""
    return call_rpc(supabase, "generate_token_atomic", {
        "p_clinic_id": clinic_id,
        "p_phone_number": phone_number,
        "p_patient_name": patient_name,
    })

def cancel_appointment(clinic_id: str, phone_number: str) -> dict:
    """Cancels the soonest upcoming booked appointment for this patient."""
    return call_rpc(supabase, "cancel_appointment_atomic", {
        "p_clinic_id": clinic_id,
        "p_phone_number": phone_number,
    })

def reschedule_slot(clinic_id: str, phone_number: str, date_str: str, time_str: str) -> dict:
    """Moves the soonest upcoming booking to a new canonical slot."""
    time_str = (time_str or "")[:5]
    return call_rpc(supabase, "reschedule_slot_atomic", {
        "p_clinic_id": clinic_id,
        "p_phone_number": phone_number,
        "p_appointment_time": f"{date_str} {time_str}",
    })

def execute_tool(function_name: str, function_args: dict) -> dict:
    if function_name == "check_availability":
        return check_availability(function_args.get("clinic_id"), function_args.get("date_str"))
    if function_name == "book_slot":
        return book_slot(
            function_args.get("clinic_id"),
            function_args.get("phone_number"),
            function_args.get("date_str"),
            function_args.get("time_str"),
            function_args.get("patient_name", "Unknown"),
        )
    if function_name == "generate_token":
        return generate_token(
            function_args.get("clinic_id"),
            function_args.get("phone_number"),
            function_args.get("patient_name", "Unknown"),
        )
    if function_name == "cancel_appointment":
        return cancel_appointment(function_args.get("clinic_id"), function_args.get("phone_number"))
    if function_name == "reschedule_slot":
        return reschedule_slot(
            function_args.get("clinic_id"),
            function_args.get("phone_number"),
            function_args.get("date_str"),
            function_args.get("time_str"),
        )
    return {"error": "Unknown function"}

# 3. Initialize the Groq Client
client = Groq() # automatically looks for GROQ_API_KEY in env

instruction = (
    "You are a highly efficient clinic receptionist chatbot. Keep all messages MINIMAL and straight to the point. Avoid fluff.\n"
    "LANGUAGE PREFERENCE:\n"
    "- First message: Ask the user to choose their preferred language (English or Hindi). Do NOT call tools.\n"
    "- Stick STRICTLY to the chosen language. If Hindi is chosen, use Devanagari script. Do NOT use Hinglish or mix languages.\n\n"
    
    "WORKFLOW & ROUTING:\n"
    "Step 1 (Identify Clinic): Present the available clinics and ask which one they want to visit. Format as a natural list based on the ACTUAL `available_clinics` Context. Do NOT output raw JSON.\n"
    
    "Step 2 (Apply Specific Clinic Workflow): Once the patient states the clinic name (e.g. 'naman clinic', 'test clinic'), you MUST immediately follow the `booking_mode` specified in the `available_clinics` list for that clinic! DO NOT hallucinate random responses or change the subject.\n"
    "- Follow the matching workflow below based on the chosen clinic's `booking_mode`:\n\n"
    
    "WORKFLOW A: SCHEDULED CLINICS (`booking_mode='scheduled'`)\n"
    "1. Ask for their preferred date and time. (If `patient_name` is NOT in Context, ask for their name too).\n"
    "2. If they provide ANY time (e.g. 'tomorrow evening'), deduce the YYYY-MM-DD date using the Current System Time and convert the time to 24-hour HH:MM format, then call `check_availability`!\n"
    "3. If the slot is free, call `book_slot` to confirm.\n"
    "4. If the time clashes, ask for another time.\n\n"
    
    "WORKFLOW B: TOKENIZED CLINICS (`booking_mode='token'`)\n"
    "1. If `patient_name` is NOT in Context, ask for it.\n"
    "2. Inform them of the queue status using `current_serving` and `last_token` from the `available_clinics` context.\n"
    "3. Ask 'Do you want to book an appointment for today?'. (Token clinics ONLY book for today).\n"
    "4. If they say YES: Immediately call the `generate_token` tool.\n"
    "5. If they say NO: Decline politely.\n\n"
    
    "CRITICAL TOOL INSTRUCTION: When booking an appointment, you MUST actually execute the tool (`generate_token` or `book_slot`). Do NOT just say 'your appointment is booked' without calling the tool!\n\n"
    "CANCELLATIONS AND RESCHEDULES:\n"
    "- If the patient wants to cancel, call `cancel_appointment` with clinic_id and phone_number from Context.\n"
    "- If they want a different time at a scheduled clinic, call `reschedule_slot` (do not book a second slot).\n"
    "- Token clinics cannot reschedule to a clock time; cancel then generate_token if they still want to visit.\n\n"
    
    "STRICT ANTI-HALLUCINATION RULES:\n"
    "- If the user types a clinic name (like 'naman clinic'), immediately proceed to the workflow steps (ask for name/time). DO NOT make up conversational filler like 'eat salt' or unrelated phrases.\n"
    "- If the user's message is completely unrelated to clinics, decline: 'I can only assist with booking appointments. How can I help you schedule a visit today?'\n"
    "- Do NOT trigger this off-topic message if the user is simply stating a clinic name. That IS related to booking!\n"
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
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancels the patient's soonest upcoming booked appointment at a clinic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clinic_id": {"type": "string"},
                    "phone_number": {"type": "string"}
                },
                "required": ["clinic_id", "phone_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_slot",
            "description": "Moves the patient's soonest upcoming scheduled appointment to a new date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clinic_id": {"type": "string"},
                    "phone_number": {"type": "string"},
                    "date_str": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "HH:MM"}
                },
                "required": ["clinic_id", "phone_number", "date_str", "time_str"]
            }
        }
    }
]

# Conversation memory is persisted per phone so Render restarts / multiple instances stay consistent.

def load_chat(phone: str) -> list:
    messages, _wf = load_session(phone)
    return messages


def load_session(phone: str, patient_name: str = ""):
    try:
        resp = supabase.table("chat_histories").select("messages").eq("phone_number", phone).limit(1).execute()
        if resp.data and resp.data[0].get("messages") is not None:
            blob = resp.data[0]["messages"]
            if isinstance(blob, dict) and ("workflow" in blob or "messages" in blob):
                msgs = blob.get("messages") or []
                wf = blob.get("workflow") or default_workflow(patient_name)
                return msgs, wf
            if isinstance(blob, list):
                return blob, default_workflow(patient_name)
    except Exception as e:
        print(f"Error loading chat history: {e}")
    return [], default_workflow(patient_name)


def save_chat(phone: str, messages: list):
    save_session(phone, messages, default_workflow())


def save_session(phone: str, messages: list, workflow: dict):
    try:
        payload = {
            "phone_number": phone,
            "messages": {
                "workflow": workflow,
                "messages": trim_messages(serialize_messages(messages or []), max_len=20),
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("chat_histories").upsert(payload).execute()
    except Exception as e:
        print(f"Error saving chat history: {e}")


def claim_message_id(wamid: str, phone: str) -> bool:
    """Return False if Meta already delivered this wamid (retry). Missing id always proceeds."""
    if not wamid:
        return True
    result = call_rpc(supabase, "claim_wamid", {"p_wamid": wamid, "p_phone": phone})
    if result is False:
        return False
    if result is True:
        return True
    if isinstance(result, dict) and result.get("status") == "error":
        print(f"claim_wamid failed open to process once: {result}")
        return True
    return bool(result)


def mark_appointment_cancelled(appointment_id: str):
    supabase.table("appointments").update({
        "status": "cancelled",
        "slot_start": None,
    }).eq("id", appointment_id).execute()
    try:
        supabase.table("scheduled_messages").update({"status": "cancelled"}).eq(
            "appointment_id", appointment_id
        ).eq("status", "pending").execute()
    except Exception as e:
        print(f"Could not cancel scheduled messages: {e}")


def process_due_reminders():
    rows = call_rpc(supabase, "claim_due_reminders", {"p_limit": 20})
    if isinstance(rows, dict) and rows.get("status") == "error":
        print(f"claim_due_reminders: {rows.get('message')}")
        return
    if not rows:
        return
    if isinstance(rows, dict):
        rows = [rows]
    for row in rows:
        apt_id = row.get("appointment_id")
        phone = row.get("phone_number")
        msg_id = row.get("id")
        try:
            apt_resp = supabase.table("appointments").select(
                "status, appointment_time, patient_name, clinic_id"
            ).eq("id", apt_id).limit(1).execute()
            apt = apt_resp.data[0] if apt_resp.data else None
            if not apt or apt.get("status") in ("cancelled", "completed"):
                supabase.table("scheduled_messages").update({"status": "skipped"}).eq("id", msg_id).execute()
                continue
            clinic_resp = supabase.table("clinics").select("business_name").eq("id", apt["clinic_id"]).limit(1).execute()
            clinic_name = clinic_resp.data[0]["business_name"] if clinic_resp.data else "the clinic"
            when = str(apt.get("appointment_time", "")).replace("T", " ")[:16]
            body = f"Reminder: your appointment at {clinic_name} is at {when}. Reply CANCEL if you cannot make it."
            send_whatsapp_message(phone, body)
            supabase.table("scheduled_messages").update({"status": "sent"}).eq("id", msg_id).execute()
        except Exception as e:
            supabase.table("scheduled_messages").update({
                "status": "pending",
                "last_error": str(e)[:500],
            }).eq("id", msg_id).execute()
            print(f"Reminder send failed: {e}")


async def reminder_worker():
    await asyncio.sleep(5)
    while True:
        try:
            process_due_reminders()
        except Exception as e:
            print(f"reminder_worker: {e}")
        await asyncio.sleep(60)


# Back-compat name used by older tests
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
        trial_end = (get_now() + timedelta(days=7)).isoformat()
        
        # We use the shared META_PHONE_NUMBER_ID for the MVP
        clinic_response = supabase.table("clinics").insert({
            "business_name": req.business_name,
            "meta_phone_number_id": META_PHONE_NUMBER_ID or "NOT_SET",
            "admin_email": req.admin_email,
            "admin_auth_uid": user_id,
            "trial_end_date": trial_end,
            "booking_mode": req.booking_mode,
            "working_days": req.working_days,
            "working_hours": req.working_hours,
            "slot_duration_minutes": 10,
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
        
        if req.status == "cancelled":
            mark_appointment_cancelled(appointment_id)
        else:
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
                            wamid = message_obj.get("id")
                            if not claim_message_id(wamid, user_phone):
                                print(f"Skipping duplicate webhook wamid={wamid}")
                                return

                            user_message = message_obj["text"]["body"]
                            patient_name = get_patient_name(user_phone)
                            clinics = get_all_clinics()
                            _history, wf = load_session(user_phone, patient_name)
                            if patient_name and not wf.get("patient_name"):
                                wf["patient_name"] = patient_name

                            tools = {
                                "book_slot": book_slot,
                                "generate_token": generate_token,
                                "cancel_appointment": cancel_appointment,
                                "reschedule_slot": reschedule_slot,
                                "check_availability": check_availability,
                            }
                            try:
                                reply, wf, used_groq = handle_turn(
                                    user_message,
                                    wf,
                                    clinics,
                                    user_phone,
                                    get_now(),
                                    tools,
                                    groq_client=client,
                                )
                                if used_groq and not check_and_increment_usage():
                                    send_whatsapp_message(
                                        user_phone,
                                        "Our AI receptionist is currently experiencing high traffic. Please wait about 1 minute and send your message again!",
                                    )
                                    return
                                if reply:
                                    send_whatsapp_message(user_phone, reply)
                                save_session(user_phone, _history, wf)
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
            mark_appointment_cancelled(apt["id"])
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
        today_str = get_now().strftime("%Y-%m-%d")
        
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
                mark_appointment_cancelled(apt["id"])
                bg_tasks.add_task(send_whatsapp_template, apt["phone_number"], "appointment_cancelled")
                
        return {"status": "success", "message": f"Closed clinic and cancelled {len(resp.data) if resp.data else 0} appointments."}
    except Exception as e:
        print("Error in close_day:", e)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=True)