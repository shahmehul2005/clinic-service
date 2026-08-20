"""DB-backed booking helpers. Atomic writes live in reliability_migration.sql RPCs."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def get_now():
    return datetime.now(IST)


def parse_rpc(resp):
    data = getattr(resp, "data", resp)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return {"status": "error", "message": data}
    return data if data is not None else {"status": "error", "message": "Empty RPC response"}


def call_rpc(supabase, name: str, params: dict) -> dict:
    try:
        resp = supabase.rpc(name, params).execute()
        return parse_rpc(resp)
    except Exception as e:
        err = str(e)
        if "unique" in err.lower() or "23505" in err:
            return {"status": "error", "message": "CRITICAL: Slot taken. Apologize and offer another time."}
        return {"status": "error", "message": f"Database error: {err}"}


def serialize_messages(messages: list) -> list:
    out = []
    for m in messages:
        if isinstance(m, dict):
            item = {k: v for k, v in m.items() if k in ("role", "content", "tool_calls", "tool_call_id", "name")}
            out.append(item)
            continue
        item = {
            "role": getattr(m, "role", "assistant"),
            "content": getattr(m, "content", None),
        }
        tool_calls = getattr(m, "tool_calls", None)
        if tool_calls:
            serialized = []
            for tc in tool_calls:
                fn = getattr(tc, "function", None)
                serialized.append({
                    "id": getattr(tc, "id", ""),
                    "type": "function",
                    "function": {
                        "name": getattr(fn, "name", "") if fn else "",
                        "arguments": getattr(fn, "arguments", "{}") if fn else "{}",
                    },
                })
            item["tool_calls"] = serialized
        out.append(item)
    return out


def trim_messages(messages: list, max_len: int = 41) -> list:
    if len(messages) <= max_len:
        return messages
    system = messages[0] if messages and (
        (isinstance(messages[0], dict) and messages[0].get("role") == "system")
        or getattr(messages[0], "role", None) == "system"
    ) else None
    tail = messages[-(max_len - 1):] if system is not None else messages[-max_len:]
    return ([system] + tail) if system is not None else tail


def iter_slots(date_str: str, working_hours: dict, duration_minutes: int, now: datetime):
    """Yield slot datetimes for a calendar day, skipping lunch and past times."""
    duration_minutes = max(int(duration_minutes or 10), 1)
    start_s = (working_hours or {}).get("start") or "09:00"
    end_s = (working_hours or {}).get("end") or "21:00"
    start_t = datetime.strptime(start_s, "%H:%M").time()
    end_t = datetime.strptime(end_s, "%H:%M").time()
    break_start = (working_hours or {}).get("break_start")
    break_end = (working_hours or {}).get("break_end")
    bs = datetime.strptime(break_start, "%H:%M").time() if break_start else None
    be = datetime.strptime(break_end, "%H:%M").time() if break_end else None

    cursor = datetime.strptime(f"{date_str} {start_s}", "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    end_dt = datetime.strptime(f"{date_str} {end_s}", "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    is_today = date_str == now.strftime("%Y-%m-%d")

    while cursor <= end_dt:
        t = cursor.time()
        in_break = bs and be and bs <= t < be
        in_past = is_today and cursor < now
        if not in_break and not in_past and t >= start_t and t <= end_t:
            yield cursor.replace(tzinfo=None)
        cursor += timedelta(minutes=duration_minutes)
