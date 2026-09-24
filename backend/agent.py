import os
import io
import hmac
import hashlib
import requests
import asyncio
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, Response, BackgroundTasks, UploadFile, File, Form
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
            .select("id, business_name, trial_end_date, booking_mode, current_serving_token, closed_date, working_days, working_hours, consultation_fee, maps_link") \
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
        ).in_("status", ["booked", "arrived"]).gte("appointment_time", f"{date_str} 00:00:00").lte(
            "appointment_time", f"{date_str} 23:59:59"
        ).execute()

        # Build set of booked minute-timestamps for gap checking
        booked_minutes = set()
        for record in (booked_resp.data or []):
            raw = record.get("slot_start") or record.get("appointment_time")
            if not raw:
                continue
            raw_str = str(raw).replace("T", " ")[:16]
            try:
                booked_dt = datetime.strptime(raw_str, "%Y-%m-%d %H:%M")
                booked_minutes.add(booked_dt)
            except Exception:
                pass

        # 20-minute gap: block any slot within 20 min of a booked slot
        def is_too_close(slot_dt):
            for b in booked_minutes:
                diff = abs((slot_dt - b).total_seconds() / 60)
                if diff < 20:
                    return True
            return False

        now = get_now()
        cutoff = now + timedelta(minutes=30)  # must be at least 30 min in future
        available_slots = []
        for slot_dt in iter_slots(date_str, working_hours, duration, now):
            # Past/too-soon filter
            if slot_dt < cutoff:
                continue
            if is_too_close(slot_dt):
                continue
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

def send_whatsapp_interactive(to_phone: str, interactive_payload: dict):
    """
    Sends an interactive message (button or list) via Meta Graph API.
    interactive_payload must follow the workflow.py dict format:
      {
        "interactive_type": "button" | "list",
        "header": "...",   (optional)
        "body": "...",
        "buttons": [...],  (for type=button, max 3)
        "rows": [...],     (for type=list, max 10)
        "button_label": "...", (for type=list, the CTA button label)
      }
    Falls back to plain text if Meta API keys are missing.
    """
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("WARNING: Meta API keys missing. Interactive message not sent.")
        return

    sanitized_phone = ''.join(filter(str.isdigit, to_phone))
    if not sanitized_phone:
        return

    itype = interactive_payload.get("interactive_type", "button")
    body_text = interactive_payload.get("body", "")
    header_text = interactive_payload.get("header", "")

    interactive = {"type": itype, "body": {"text": body_text}}
    if header_text:
        interactive["header"] = {"type": "text", "text": header_text}

    if itype == "button":
        buttons = interactive_payload.get("buttons", [])
        interactive["action"] = {
            "buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                for b in buttons[:3]
            ]
        }
    elif itype == "list":
        rows = interactive_payload.get("rows", [])
        button_label = interactive_payload.get("button_label", "View Options")[:20]
        formatted_rows = []
        for r in rows[:10]:
            row = {"id": r["id"], "title": r["title"][:24]}
            if r.get("description"):
                row["description"] = r["description"][:72]
            formatted_rows.append(row)
        interactive["action"] = {
            "button": button_label,
            "sections": [{"title": "Options", "rows": formatted_rows}]
        }

    url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": sanitized_phone,
        "type": "interactive",
        "interactive": interactive,
    }
    print(f"[WA] Sending interactive '{itype}' to {sanitized_phone}...")
    response = requests.post(url, headers=headers, json=payload)
    print(f"[WA] Interactive response: {response.status_code} — {response.text[:200]}")
    if response.status_code != 200:
        print(f"ERROR sending interactive message: {response.text}")
        # Fallback to plain text with the body
        send_whatsapp_message(to_phone, body_text)

def send_whatsapp_template(to_phone: str, template_name: str, components: list = None, language_code: str = "en"):
    """Sends a pre-approved template message via Meta Graph API."""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("WARNING: Meta API keys are missing. Template not sent.")
        return

    # Sanitize phone number: Meta requires E.164 format without + or spaces
    # e.g., "91XXXXXXXXXX" not "+91XXXXXXXXXX" or "91-XX-XXXX-XXXX"
    sanitized_phone = ''.join(filter(str.isdigit, to_phone))
    if not sanitized_phone:
        print(f"ERROR: Invalid phone number '{to_phone}' - cannot send template.")
        return

    url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": sanitized_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
    }
    if components:
        payload["template"]["components"] = components
    
    print(f"[WA] Sending template '{template_name}' to {sanitized_phone}...")
    print(f"[WA] Payload: {payload}")
    response = requests.post(url, headers=headers, json=payload)
    print(f"[WA] Response status: {response.status_code}")
    print(f"[WA] Response body: {response.text}")
    if response.status_code != 200:
        print(f"ERROR sending WhatsApp template '{template_name}' to {sanitized_phone}: {response.text}")

# ---------- PDF Report Generation ----------

def generate_patient_report_pdf(report_data: dict, clinic_data: dict) -> bytes:
    """
    Generates a professional medical report PDF using ReportLab.
    Returns the PDF as raw bytes.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    brand_blue = colors.HexColor("#1a6eb0")
    light_blue = colors.HexColor("#e8f4fd")
    dark_gray = colors.HexColor("#333333")
    mid_gray = colors.HexColor("#666666")

    h1 = ParagraphStyle("h1", parent=styles["Normal"], fontSize=20, textColor=brand_blue,
                        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Normal"], fontSize=11, textColor=brand_blue,
                        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
    label = ParagraphStyle("label", parent=styles["Normal"], fontSize=9,
                           textColor=mid_gray, fontName="Helvetica")
    value = ParagraphStyle("value", parent=styles["Normal"], fontSize=10,
                           textColor=dark_gray, fontName="Helvetica")
    center = ParagraphStyle("center", parent=styles["Normal"], fontSize=8,
                            textColor=mid_gray, alignment=TA_CENTER)

    clinic_name = clinic_data.get("business_name", "Clinic")
    doctor_name = clinic_data.get("doctor_name") or "Attending Doctor"
    clinic_address = clinic_data.get("clinic_address") or ""

    story = []

    # Header block
    header_data = [
        [
            Paragraph(f"<b>{clinic_name}</b>", h1),
            Paragraph(
                f"<b>Dr. {doctor_name}</b><br/>"
                + (f"<font color='#666666' size='8'>{clinic_address}</font>" if clinic_address else ""),
                ParagraphStyle("right", parent=styles["Normal"], fontSize=10,
                               fontName="Helvetica", alignment=TA_LEFT)
            )
        ]
    ]
    header_table = Table(header_data, colWidths=[9 * cm, 8 * cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_blue),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=brand_blue))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("PATIENT MEDICAL REPORT", ParagraphStyle(
        "title", parent=styles["Normal"], fontSize=14, textColor=brand_blue,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6
    )))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#aaaaaa")))
    story.append(Spacer(1, 0.3 * cm))

    # Patient info 2-column
    visit_date = report_data.get("visit_date") or get_now().strftime("%d %b %Y")
    info_data = [
        [
            Paragraph("<b>Patient:</b>", label), Paragraph(report_data.get("patient_name", "—"), value),
            Paragraph("<b>Visit Date:</b>", label), Paragraph(visit_date, value),
        ],
        [
            Paragraph("<b>Age:</b>", label), Paragraph(str(report_data.get("patient_age") or "—"), value),
            Paragraph("<b>Phone:</b>", label), Paragraph(report_data.get("phone_number", "—"), value),
        ],
    ]
    info_table = Table(info_data, colWidths=[3 * cm, 5.5 * cm, 3 * cm, 5.5 * cm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd")))
    story.append(Spacer(1, 0.2 * cm))

    # Chief Complaint & Diagnosis
    story.append(Paragraph("Chief Complaint", h2))
    story.append(Paragraph(report_data.get("chief_complaint") or "—", value))
    story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph("Diagnosis", h2))
    story.append(Paragraph(report_data.get("diagnosis") or "—", value))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd")))

    # Prescription table
    story.append(Paragraph("Prescription", h2))
    medicines = report_data.get("medicines") or []
    if medicines:
        med_table_data = [["Medicine", "Dosage", "Frequency", "Duration"]]
        for m in medicines:
            med_table_data.append([
                m.get("name", ""), m.get("dosage", ""),
                m.get("frequency", ""), m.get("duration", ""),
            ])
        med_table = Table(med_table_data, colWidths=[5 * cm, 3 * cm, 4 * cm, 5 * cm])
        med_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), brand_blue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_blue]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(med_table)
    else:
        story.append(Paragraph("No medicines prescribed.", value))

    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd")))

    # Follow-up & Notes
    story.append(Paragraph("Follow-up Date", h2))
    story.append(Paragraph(report_data.get("followup_date") or "No follow-up required", value))

    if report_data.get("special_notes"):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Special Instructions", h2))
        story.append(Paragraph(report_data["special_notes"], value))

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_blue))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Powered by ClinicOS · This is a computer-generated report.", center))

    doc.build(story)
    return buf.getvalue()


def generate_image_report_pdf(image_bytes: bytes, patient_name: str, clinic_data: dict) -> bytes:
    """
    Wraps an uploaded image (scan, lab report photo, etc.) in a PDF
    with clinic letterhead and patient header above it.
    Uses Pillow to handle image format conversion and ReportLab for PDF.
    """
    from PIL import Image as PILImage
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    # Convert image bytes to RGB and save as JPEG in memory (compatible with ReportLab)
    pil_img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
    img_buf = io.BytesIO()
    pil_img.save(img_buf, format="JPEG", quality=90)
    img_buf.seek(0)

    page_w, page_h = A4
    usable_w = page_w - 4 * cm  # 2cm margin each side

    # Scale image to fit page width while preserving aspect ratio
    orig_w, orig_h = pil_img.size
    scale = usable_w / orig_w
    img_display_h = orig_h * scale

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    brand_blue = colors.HexColor("#1d4ed8")

    clinic_name = clinic_data.get("business_name") or "Clinic"
    doctor_name = clinic_data.get("doctor_name") or ""
    address = clinic_data.get("clinic_address") or ""

    header_style = ParagraphStyle("header", fontSize=16, textColor=brand_blue, spaceAfter=2,
                                   fontName="Helvetica-Bold", alignment=TA_CENTER)
    sub_style = ParagraphStyle("sub", fontSize=10, textColor=colors.grey,
                                fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4)
    label_style = ParagraphStyle("label", fontSize=11, textColor=colors.HexColor("#1e293b"),
                                  fontName="Helvetica-Bold")

    story = [
        Paragraph(clinic_name, header_style),
    ]
    if doctor_name:
        story.append(Paragraph(doctor_name, sub_style))
    if address:
        story.append(Paragraph(address, sub_style))

    story.append(HRFlowable(width="100%", thickness=2, color=brand_blue, spaceAfter=8))
    story.append(Paragraph(f"Patient: {patient_name}", label_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd"), spaceAfter=8))
    story.append(Spacer(1, 0.3 * cm))

    # Add the image, capping height to fit on one page
    max_h = page_h - 10 * cm  # leave room for header
    if img_display_h > max_h:
        scale2 = max_h / img_display_h
        img_display_h *= scale2
        usable_w *= scale2

    story.append(RLImage(img_buf, width=usable_w, height=img_display_h))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_blue))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Powered by ClinicOS · This is a computer-generated report.",
                             ParagraphStyle("foot", fontSize=8, textColor=colors.grey,
                                            fontName="Helvetica", alignment=TA_CENTER)))

    doc.build(story)
    return buf.getvalue()


def upload_media_to_meta(pdf_bytes: bytes, filename: str = "report.pdf") -> str | None:
    """
    Uploads a PDF to Meta's hosted media endpoint.
    Returns the media_id string, or None on failure.
    """
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("WARNING: Meta API keys missing. Cannot upload media.")
        return None
    url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
    files = {
        "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
        "messaging_product": (None, "whatsapp"),
        "type": (None, "application/pdf"),
    }
    try:
        resp = requests.post(url, headers=headers, files=files)
        if resp.status_code == 200:
            return resp.json().get("id")
        print(f"Meta media upload failed ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"Exception uploading media: {e}")
    return None


def send_whatsapp_document(to_phone: str, media_id: str, filename: str, clinic_name: str, patient_name: str):
    """Sends a document message via Meta Graph API using the patient_report_document template."""
    first_name = (patient_name or "there").split()[0]
    components = [
        {
            "type": "header",
            "parameters": [
                {
                    "type": "document",
                    "document": {
                        "id": media_id,
                        "filename": filename
                    }
                }
            ]
        },
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": first_name},
                {"type": "text", "text": clinic_name}
            ]
        }
    ]
    send_whatsapp_template(to_phone, "patient_report_document", components)


def send_google_review_request(to_phone: str, patient_name: str, clinic_name: str, clinic_id: str):
    """Sends a WhatsApp template asking the patient for a Google review."""
    first_name = (patient_name or "there").split()[0]
    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": clinic_name},
                {"type": "text", "text": first_name}
            ]
        }
    ]
    
    # Send the backend redirect URL path so Meta can append it to the Base URL
    clean_link = f"api/reviews/{clinic_id}"
    
    components.append({
        "type": "button",
        "sub_type": "url",
        "index": "0", # The index of the button (0 for the first button)
        "parameters": [
            {
                "type": "text",
                "text": clean_link
            }
        ]
    })
    
    send_whatsapp_template(to_phone, "google_review_request", components)


# Health check endpoint for keepalive pings (Render free-tier spin-down prevention)
@app.get("/health")
async def health_check():
    """Health check that also touches Supabase to prevent 7-day inactivity pause."""
    try:
        # Lightweight query — just count clinics, keeps Supabase active
        supabase.table("clinics").select("id", count="exact").limit(1).execute()
        return {"status": "ok", "supabase": "alive"}
    except Exception:
        # Still return 200 so UptimeRobot doesn't flag Render as down
        return {"status": "ok", "supabase": "unreachable"}


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

@app.get("/api/reviews/{clinic_id}")
async def redirect_to_google_review(clinic_id: str):
    """Universal redirect endpoint for Meta WhatsApp Button."""
    try:
        resp = supabase.table("clinics").select("google_review_link").eq("id", clinic_id).execute()
        if resp.data and resp.data[0].get("google_review_link"):
            url = resp.data[0]["google_review_link"]
            if not url.startswith("http"):
                url = "https://" + url
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=url)
        return Response(content="Review link not configured for this clinic.", status_code=404)
    except Exception as e:
        return Response(content=str(e), status_code=500)

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
async def update_appointment_status(appointment_id: str, req: StatusUpdateRequest, background_tasks: BackgroundTasks):
    """Updates appointment status and sends automated WhatsApp messages."""
    try:
        # 1. Fetch appointment details to get patient phone and clinic_id
        apt_response = supabase.table("appointments").select("phone_number, clinic_id, patient_name").eq("id", appointment_id).execute()
        if not apt_response.data:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": "Appointment not found"})
            
        apt = apt_response.data[0]
        patient_phone = apt["phone_number"]
        patient_name = apt.get("patient_name", "")
        clinic_id = apt["clinic_id"]
        
        if req.status == "cancelled":
            mark_appointment_cancelled(appointment_id)
        else:
            supabase.table("appointments").update({"status": req.status}).eq("id", appointment_id).execute()
        
        # 3. Trigger WhatsApp template messages based on new status
        if req.status == 'completed' or req.status == 'cancelled':
            # Fetch clinic data (name + google review link)
            clinic_resp = supabase.table("clinics").select(
                "business_name, google_review_link"
            ).eq("id", clinic_id).execute()
            clinic_row = clinic_resp.data[0] if clinic_resp.data else {}
            clinic_name = clinic_row.get("business_name") or "our clinic"
            google_review_link = clinic_row.get("google_review_link")
            
            # Send Meta Template Message
            if META_ACCESS_TOKEN and META_PHONE_NUMBER_ID:
                template_name = "visit_thanks" if req.status == 'completed' else "appointment_cancelled"
                components = [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": clinic_name}
                        ]
                    }
                ]
                background_tasks.add_task(send_whatsapp_template, patient_phone, template_name, components)
                print(f"Scheduled '{template_name}' template to {patient_phone}")

            # NEW: Auto-send Google Review request when appointment is completed
            if req.status == 'completed' and google_review_link:
                background_tasks.add_task(
                    send_google_review_request,
                    patient_phone,
                    patient_name,
                    clinic_name,
                    clinic_id,
                )
                print(f"Scheduled Google review request to {patient_phone}")
                
        return {"status": "success", "message": f"Status updated to {req.status}"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

# ---------- Report Sending Endpoint ----------

class MedicineItem(BaseModel):
    name: str
    dosage: str = ""
    frequency: str = ""
    duration: str = ""

class SendReportRequest(BaseModel):
    appointment_id: str
    patient_age: str = ""
    chief_complaint: str = ""
    diagnosis: str = ""
    medicines: list = []  # list of MedicineItem dicts
    followup_date: str = ""
    special_notes: str = ""

@app.post("/api/reports/send-image")
async def send_patient_report_image(
    appointment_id: str = Form(...),
    image: UploadFile = File(...),
):
    """
    Accepts an uploaded image (jpg/png/pdf scan), wraps it in a
    clinic-branded PDF, and sends it to the patient via WhatsApp.
    """
    from fastapi.responses import JSONResponse
    try:
        # 1. Fetch appointment
        apt_resp = supabase.table("appointments").select(
            "phone_number, patient_name, clinic_id, appointment_time"
        ).eq("id", appointment_id).limit(1).execute()
        if not apt_resp.data:
            return JSONResponse(status_code=404, content={"detail": "Appointment not found"})
        apt = apt_resp.data[0]

        # 2. Fetch clinic details
        clinic_resp = supabase.table("clinics").select(
            "business_name, doctor_name, clinic_address"
        ).eq("id", apt["clinic_id"]).limit(1).execute()
        clinic_data = clinic_resp.data[0] if clinic_resp.data else {}

        patient_name = apt.get("patient_name") or "Patient"

        # 3. Read the uploaded image
        image_bytes = await image.read()

        # 4. Generate PDF wrapping the image
        pdf_bytes = generate_image_report_pdf(image_bytes, patient_name, clinic_data)

        # 5. Upload & send
        patient_name_safe = patient_name.replace(" ", "_")
        filename = f"report_image_{patient_name_safe}.pdf"
        media_id = upload_media_to_meta(pdf_bytes, filename)
        if not media_id:
            return JSONResponse(status_code=502, content={"detail": "Failed to upload PDF to WhatsApp."})

        clinic_name = clinic_data.get("business_name", "our clinic")
        send_whatsapp_document(apt["phone_number"], media_id, filename, clinic_name, patient_name)

        return {"status": "success", "message": f"Image report sent to {apt['phone_number']}", "patient_name": patient_name}
    except Exception as e:
        print(f"Error sending image report: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/reports/send")
async def send_patient_report(req: SendReportRequest):
    """Generates a PDF medical report and sends it to the patient via WhatsApp."""
    from fastapi.responses import JSONResponse
    try:
        # 1. Fetch appointment details
        apt_resp = supabase.table("appointments").select(
            "phone_number, patient_name, clinic_id, appointment_time"
        ).eq("id", req.appointment_id).limit(1).execute()
        if not apt_resp.data:
            return JSONResponse(status_code=404, content={"detail": "Appointment not found"})
        apt = apt_resp.data[0]

        # 2. Fetch clinic details
        clinic_resp = supabase.table("clinics").select(
            "business_name, doctor_name, clinic_address"
        ).eq("id", apt["clinic_id"]).limit(1).execute()
        clinic_data = clinic_resp.data[0] if clinic_resp.data else {}

        visit_date = str(apt.get("appointment_time", ""))[:10]
        try:
            from datetime import datetime as dt
            visit_date = dt.strptime(visit_date, "%Y-%m-%d").strftime("%d %b %Y")
        except Exception:
            pass

        report_data = {
            "patient_name": apt.get("patient_name") or "Patient",
            "phone_number": apt.get("phone_number", ""),
            "patient_age": req.patient_age,
            "visit_date": visit_date,
            "chief_complaint": req.chief_complaint,
            "diagnosis": req.diagnosis,
            "medicines": req.medicines,
            "followup_date": req.followup_date,
            "special_notes": req.special_notes,
        }

        # 3. Generate PDF
        pdf_bytes = generate_patient_report_pdf(report_data, clinic_data)

        # 4. Upload to Meta media endpoint
        patient_name_safe = (apt.get("patient_name") or "patient").replace(" ", "_")
        filename = f"report_{patient_name_safe}_{visit_date.replace(' ', '_')}.pdf"
        media_id = upload_media_to_meta(pdf_bytes, filename)

        if not media_id:
            return JSONResponse(status_code=502, content={"detail": "Failed to upload PDF to WhatsApp. Check Meta API keys."})

        # 5. Send the document via WhatsApp
        clinic_name = clinic_data.get('business_name', 'our clinic')
        send_whatsapp_document(apt["phone_number"], media_id, filename, clinic_name, apt.get("patient_name", ""))

        # 6. Save to patient_reports table (audit trail)
        supabase.table("patient_reports").insert({
            "clinic_id": apt["clinic_id"],
            "appointment_id": req.appointment_id,
            "phone_number": apt["phone_number"],
            "patient_name": apt.get("patient_name"),
            "patient_age": req.patient_age,
            "doctor_name": clinic_data.get("doctor_name"),
            "chief_complaint": req.chief_complaint,
            "diagnosis": req.diagnosis,
            "medicines": req.medicines,
            "followup_date": req.followup_date,
            "special_notes": req.special_notes,
        }).execute()

        return {
            "status": "success",
            "message": f"Report sent to {apt['phone_number']}",
            "patient_name": apt.get("patient_name"),
        }
    except Exception as e:
        print(f"Error sending report: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ---------- Clinic Settings Endpoint ----------

class ClinicSettingsRequest(BaseModel):
    google_review_link: str = ""
    doctor_name: str = ""
    clinic_address: str = ""
    consultation_fee: str = ""
    maps_link: str = ""

@app.patch("/api/clinics/{clinic_id}/settings")
async def update_clinic_settings(clinic_id: str, req: ClinicSettingsRequest):
    """Updates editable clinic profile settings from the Dashboard."""
    from fastapi.responses import JSONResponse
    try:
        update_data = {}
        if req.google_review_link is not None:
            update_data["google_review_link"] = req.google_review_link or None
        if req.doctor_name is not None:
            update_data["doctor_name"] = req.doctor_name or None
        if req.clinic_address is not None:
            update_data["clinic_address"] = req.clinic_address or None
        if req.consultation_fee is not None:
            update_data["consultation_fee"] = req.consultation_fee or None
        if req.maps_link is not None:
            update_data["maps_link"] = req.maps_link or None

        if not update_data:
            return {"status": "success", "message": "Nothing to update."}

        supabase.table("clinics").update(update_data).eq("id", clinic_id).execute()
        return {"status": "success", "message": "Clinic settings updated."}
    except Exception as e:
        print(f"Error updating clinic settings: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ---------- Appointment Reminders Endpoint (called by GitHub Actions every 10 min) ----------

class RemindersRequest(BaseModel):
    pin: str

@app.post("/api/internal/send-reminders")
async def send_appointment_reminders(req: RemindersRequest):
    """Sends 1-hour reminder templates to time-based appointments. Called by GitHub Actions cron."""
    from fastapi.responses import JSONResponse
    if req.pin != ADMIN_PIN:
        return JSONResponse(status_code=401, content={"detail": "Invalid PIN"})
    try:
        now = get_now()
        window_start = now + timedelta(minutes=55)
        window_end = now + timedelta(minutes=65)
        ws = window_start.strftime("%Y-%m-%d %H:%M:%S")
        we = window_end.strftime("%Y-%m-%d %H:%M:%S")

        resp = supabase.table("appointments") \
            .select("id, phone_number, patient_name, appointment_time, clinic_id, reminder_sent") \
            .eq("status", "booked") \
            .eq("reminder_sent", False) \
            .gte("appointment_time", ws) \
            .lte("appointment_time", we) \
            .execute()

        sent = 0
        for apt in (resp.data or []):
            phone = apt.get("phone_number")
            clinic_id = apt.get("clinic_id")
            apt_time = str(apt.get("appointment_time", ""))[:16]

            # Get clinic name
            c_resp = supabase.table("clinics").select("business_name").eq("id", clinic_id).single().execute()
            clinic_name = (c_resp.data or {}).get("business_name", "Clinic")

            # Format time nicely
            try:
                apt_dt = datetime.strptime(apt_time, "%Y-%m-%d %H:%M")
                time_label = apt_dt.strftime("%I:%M %p")
            except Exception:
                time_label = apt_time

            components = [
                {"type": "body", "parameters": [
                    {"type": "text", "text": clinic_name},
                    {"type": "text", "text": time_label},
                ]}
            ]
            send_whatsapp_template(phone, "appointment_reminder", components)
            supabase.table("appointments").update({"reminder_sent": True}).eq("id", apt["id"]).execute()
            sent += 1
            print(f"[REMINDER] Sent to {phone} for {apt_time}")

        return {"status": "success", "reminders_sent": sent}
    except Exception as e:
        print(f"Error sending reminders: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


# 5. Webhook Ingestion (POST) for WhatsApp Messages

def process_whatsapp_message(payload: dict):
    """Background task to process incoming WhatsApp message (text or interactive)."""
    try:
        if "object" not in payload or payload["object"] != "whatsapp_business_account":
            return

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                if not messages:
                    continue

                message_obj = messages[0]
                user_phone = message_obj.get("from")
                msg_type = message_obj.get("type")  # "text" | "interactive"

                wamid = message_obj.get("id")
                if not claim_message_id(wamid, user_phone):
                    print(f"Skipping duplicate webhook wamid={wamid}")
                    continue

                # ── Extract text and interactive_id ──────────────────────
                user_message = ""
                interactive_id = None

                if msg_type == "text":
                    user_message = message_obj.get("text", {}).get("body", "")
                elif msg_type == "interactive":
                    interactive = message_obj.get("interactive", {})
                    itype = interactive.get("type")
                    if itype == "button_reply":
                        btn = interactive.get("button_reply", {})
                        interactive_id = btn.get("id", "")
                        user_message = btn.get("title", "")
                    elif itype == "list_reply":
                        lst = interactive.get("list_reply", {})
                        interactive_id = lst.get("id", "")
                        user_message = lst.get("title", "")
                    else:
                        print(f"Unsupported interactive type: {itype}")
                        continue
                else:
                    print(f"Unsupported message type: {msg_type}")
                    continue

                # ── Load session + clinics ────────────────────────────────
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
                        interactive_id=interactive_id,
                    )
                    if used_groq and not check_and_increment_usage():
                        send_whatsapp_message(
                            user_phone,
                            "Our AI receptionist is currently experiencing high traffic. Please wait about 1 minute and send your message again!",
                        )
                        save_session(user_phone, _history, wf)
                        continue

                    if reply:
                        # Dispatch as interactive or plain text based on reply type
                        if isinstance(reply, dict) and reply.get("type") == "interactive":
                            send_whatsapp_interactive(user_phone, reply)
                        else:
                            send_whatsapp_message(user_phone, str(reply))

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
            clinic_resp = supabase.table("clinics").select("business_name").eq("id", req.clinic_id).execute()
            clinic_name = clinic_resp.data[0]["business_name"] if clinic_resp.data else "our clinic"
            supabase.table("appointments").update({"status": "completed"}).eq("id", apt["id"]).execute()
            components = [{"type": "body", "parameters": [{"type": "text", "text": clinic_name}]}]
            bg_tasks.add_task(send_whatsapp_template, apt["phone_number"], "visit_thanks", components)
            
        # 2. Update clinics counter
        new_token = req.current_token + 1
        supabase.table("clinics").update({"current_serving_token": new_token}).eq("id", req.clinic_id).execute()
        
        # 3. Alert 2nd next in queue
        target_token = new_token + 1
        resp2 = supabase.table("appointments").select("phone_number").eq("clinic_id", req.clinic_id).eq("token_number", target_token).order("created_at", desc=True).limit(1).execute()
        if resp2.data:
            components = [{"type": "body", "parameters": [{"type": "text", "text": str(target_token)}]}]
            bg_tasks.add_task(send_whatsapp_template, resp2.data[0]["phone_number"], "queue_turn_alert", components)
            
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
            clinic_resp = supabase.table("clinics").select("business_name").eq("id", req.clinic_id).execute()
            clinic_name = clinic_resp.data[0]["business_name"] if clinic_resp.data else "our clinic"
            mark_appointment_cancelled(apt["id"])
            components = [{"type": "body", "parameters": [{"type": "text", "text": clinic_name}]}]
            bg_tasks.add_task(send_whatsapp_template, apt["phone_number"], "appointment_cancelled", components)
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
            clinic_resp = supabase.table("clinics").select("business_name").eq("id", req.clinic_id).execute()
            clinic_name = clinic_resp.data[0]["business_name"] if clinic_resp.data else "our clinic"
            components = [{"type": "body", "parameters": [{"type": "text", "text": clinic_name}]}]
            for apt in resp.data:
                mark_appointment_cancelled(apt["id"])
                bg_tasks.add_task(send_whatsapp_template, apt["phone_number"], "appointment_cancelled", components)
                
        return {"status": "success", "message": f"Closed clinic and cancelled {len(resp.data) if resp.data else 0} appointments."}
    except Exception as e:
        print("Error in close_day:", e)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=True)