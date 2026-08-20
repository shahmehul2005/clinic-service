-- Reliability layer: atomic slots/tokens, reminders, webhook idempotency, chat memory.
-- Run this in the Supabase SQL Editor (service role / dashboard) after the earlier migrations.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Columns
-- ---------------------------------------------------------------------------
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS slot_start TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS token_date DATE;

ALTER TABLE clinics ADD COLUMN IF NOT EXISTS slot_duration_minutes INTEGER DEFAULT 10;
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS last_issued_token INTEGER DEFAULT 0;
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS token_seq_date DATE;

-- Exact-timestamp unique is not a 10-minute window. Replace with canonical slot_start.
-- Cancelled rows set slot_start NULL so UNIQUE allows a re-book of the same slot.
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS unique_clinic_appointment_time;

UPDATE appointments
SET slot_start = date_trunc('minute', appointment_time)
WHERE slot_start IS NULL
  AND status IS DISTINCT FROM 'cancelled'
  AND token_number IS NULL;

UPDATE appointments
SET token_date = appointment_time::date
WHERE token_number IS NOT NULL AND token_date IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uniq_clinic_active_slot
  ON appointments (clinic_id, slot_start)
  WHERE slot_start IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uniq_clinic_token_day
  ON appointments (clinic_id, token_date, token_number)
  WHERE token_number IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Job / idempotency / memory tables
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scheduled_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID REFERENCES appointments(id) ON DELETE CASCADE,
    clinic_id UUID REFERENCES clinics(id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'reminder',
    send_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_messages_due
  ON scheduled_messages (send_at)
  WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS processed_webhook_messages (
    wamid TEXT PRIMARY KEY,
    phone_number TEXT,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_histories (
    phone_number TEXT PRIMARY KEY,
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION align_slot_start(p_ts TIMESTAMP, p_duration_minutes INTEGER)
RETURNS TIMESTAMP
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT date_trunc('day', p_ts)
         + make_interval(mins => (FLOOR(
                (EXTRACT(HOUR FROM p_ts) * 60 + EXTRACT(MINUTE FROM p_ts))
                / GREATEST(COALESCE(p_duration_minutes, 10), 1)
           )::int * GREATEST(COALESCE(p_duration_minutes, 10), 1)));
$$;

CREATE OR REPLACE FUNCTION clinic_is_open_at(c clinics, p_ts TIMESTAMP)
RETURNS TEXT
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    day_name TEXT;
    start_t TIME;
    end_t TIME;
    break_start TIME;
    break_end TIME;
BEGIN
    IF c.closed_date IS NOT NULL AND c.closed_date = p_ts::date THEN
        RETURN format('CRITICAL: The clinic is closed on %s. Offer another date.', p_ts::date);
    END IF;

    day_name := trim(to_char(p_ts, 'FMDay'));
    IF c.working_days IS NOT NULL
       AND jsonb_typeof(c.working_days) = 'array'
       AND jsonb_array_length(c.working_days) > 0
       AND NOT (c.working_days @> to_jsonb(day_name)) THEN
        RETURN format('CRITICAL: The clinic is closed on %ss. Offer another date.', day_name);
    END IF;

    IF c.working_hours IS NOT NULL AND c.working_hours ? 'start' THEN
        start_t := (c.working_hours->>'start')::time;
        end_t := COALESCE((c.working_hours->>'end')::time, '23:59'::time);
        IF p_ts::time < start_t OR p_ts::time > end_t THEN
            RETURN format('CRITICAL: Requested time is outside working hours (%s to %s). Offer another time.', start_t, end_t);
        END IF;
        IF c.working_hours ? 'break_start' AND c.working_hours ? 'break_end' THEN
            break_start := (c.working_hours->>'break_start')::time;
            break_end := (c.working_hours->>'break_end')::time;
            IF p_ts::time >= break_start AND p_ts::time < break_end THEN
                RETURN format('CRITICAL: That time is during lunch break (%s to %s). Offer another time.', break_start, break_end);
            END IF;
        END IF;
    END IF;

    RETURN NULL;
END;
$$;

-- ---------------------------------------------------------------------------
-- Atomic booking
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION book_slot_atomic(
    p_clinic_id UUID,
    p_phone_number TEXT,
    p_patient_name TEXT,
    p_appointment_time TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    c clinics%ROWTYPE;
    v_ts TIMESTAMP;
    v_slot TIMESTAMP;
    v_now TIMESTAMP;
    v_id UUID;
    v_err TEXT;
    v_remind TIMESTAMP;
    v_dur INTEGER;
BEGIN
    v_now := NOW() AT TIME ZONE 'Asia/Kolkata';
    BEGIN
        v_ts := p_appointment_time::timestamp;
    EXCEPTION WHEN OTHERS THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Could not parse date/time. Use YYYY-MM-DD and HH:MM.');
    END;

    SELECT * INTO c FROM clinics WHERE id = p_clinic_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Clinic not found.');
    END IF;

    IF COALESCE(c.booking_mode, 'scheduled') = 'token' THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: This clinic operates on a Token System. You MUST call generate_token instead of book_slot. Do NOT ask for date or time, just call generate_token immediately!');
    END IF;

    v_dur := GREATEST(COALESCE(c.slot_duration_minutes, 10), 1);
    v_slot := align_slot_start(v_ts, v_dur);
    v_ts := v_slot;

    IF v_ts < v_now THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Cannot book appointments in the past. Ask the user for a future date/time.');
    END IF;

    v_err := clinic_is_open_at(c, v_ts);
    IF v_err IS NOT NULL THEN
        RETURN jsonb_build_object('status', 'error', 'message', v_err);
    END IF;

    INSERT INTO appointments (
        clinic_id, phone_number, patient_name, appointment_time, slot_start, status
    ) VALUES (
        p_clinic_id, p_phone_number, COALESCE(p_patient_name, 'Unknown'), v_ts, v_slot, 'booked'
    )
    RETURNING id INTO v_id;

    v_remind := v_ts - INTERVAL '2 hours';
    IF v_remind > v_now THEN
        INSERT INTO scheduled_messages (appointment_id, clinic_id, phone_number, kind, send_at, status)
        VALUES (v_id, p_clinic_id, p_phone_number, 'reminder', v_remind, 'pending');
    END IF;

    RETURN jsonb_build_object(
        'status', 'success',
        'appointment_id', v_id,
        'slot_start', to_char(v_slot, 'YYYY-MM-DD HH24:MI'),
        'message', format('Successfully booked for %s.', to_char(v_slot, 'YYYY-MM-DD HH24:MI'))
    );
EXCEPTION WHEN unique_violation THEN
    RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Slot is taken (another patient already holds this slot). Apologize and offer another time.');
END;
$$;

-- ---------------------------------------------------------------------------
-- Atomic tokens
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION generate_token_atomic(
    p_clinic_id UUID,
    p_phone_number TEXT,
    p_patient_name TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    c clinics%ROWTYPE;
    v_now TIMESTAMP;
    v_today DATE;
    v_next INTEGER;
    v_id UUID;
    v_err TEXT;
    v_ahead INTEGER;
BEGIN
    v_now := NOW() AT TIME ZONE 'Asia/Kolkata';
    v_today := v_now::date;

    SELECT * INTO c FROM clinics WHERE id = p_clinic_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Clinic not found.');
    END IF;

    IF COALESCE(c.booking_mode, 'scheduled') = 'scheduled' THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: This clinic operates on a Scheduled System. You MUST call book_slot instead of generate_token.');
    END IF;

    v_err := clinic_is_open_at(c, v_now);
    IF v_err IS NOT NULL THEN
        IF c.closed_date IS NOT NULL AND c.closed_date = v_today THEN
            RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: The clinic is closed for today. Tell the patient no more tokens are being issued today.');
        END IF;
        IF v_err LIKE 'CRITICAL: Requested time is outside working hours%' THEN
            RETURN jsonb_build_object(
                'status', 'error',
                'message', format(
                    'CRITICAL: The clinic is closed right now. Working hours are %s to %s. Tell the patient.',
                    COALESCE(c.working_hours->>'start', '00:00'),
                    COALESCE(c.working_hours->>'end', '23:59')
                )
            );
        END IF;
        RETURN jsonb_build_object('status', 'error', 'message', v_err);
    END IF;

    IF c.token_seq_date IS DISTINCT FROM v_today THEN
        c.last_issued_token := 0;
    END IF;

    v_next := COALESCE(c.last_issued_token, 0) + 1;

    UPDATE clinics
    SET last_issued_token = v_next,
        token_seq_date = v_today
    WHERE id = p_clinic_id;

    INSERT INTO appointments (
        clinic_id, phone_number, patient_name, appointment_time, status, token_number, token_date
    ) VALUES (
        p_clinic_id, p_phone_number, COALESCE(p_patient_name, 'Unknown'), v_now, 'booked', v_next, v_today
    )
    RETURNING id INTO v_id;

    v_ahead := GREATEST(0, v_next - COALESCE(c.current_serving_token, 0) - 1);

    RETURN jsonb_build_object(
        'status', 'success',
        'appointment_id', v_id,
        'token_number', v_next,
        'message', format(
            'Successfully generated Token #%s. The current serving token is #%s. There are %s people ahead of them in the queue. Tell all this info to the patient.',
            v_next, COALESCE(c.current_serving_token, 0), v_ahead
        )
    );
EXCEPTION WHEN unique_violation THEN
    RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Token assignment collided. Retry generate_token.');
END;
$$;

-- ---------------------------------------------------------------------------
-- Cancel / reschedule
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cancel_appointment_atomic(
    p_clinic_id UUID,
    p_phone_number TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    apt appointments%ROWTYPE;
    v_now TIMESTAMP := NOW() AT TIME ZONE 'Asia/Kolkata';
BEGIN
    PERFORM 1 FROM clinics WHERE id = p_clinic_id FOR UPDATE;

    SELECT * INTO apt
    FROM appointments
    WHERE clinic_id = p_clinic_id
      AND phone_number = p_phone_number
      AND status = 'booked'
      AND appointment_time >= v_now
    ORDER BY appointment_time ASC
    LIMIT 1
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: No upcoming booked appointment found for this patient at this clinic.');
    END IF;

    UPDATE appointments
    SET status = 'cancelled', slot_start = NULL
    WHERE id = apt.id;

    UPDATE scheduled_messages
    SET status = 'cancelled'
    WHERE appointment_id = apt.id AND status = 'pending';

    RETURN jsonb_build_object(
        'status', 'success',
        'appointment_id', apt.id,
        'message', format(
            'Cancelled the appointment at %s%s.',
            to_char(apt.appointment_time, 'YYYY-MM-DD HH24:MI'),
            CASE WHEN apt.token_number IS NOT NULL THEN format(' (token #%s)', apt.token_number) ELSE '' END
        )
    );
END;
$$;

CREATE OR REPLACE FUNCTION reschedule_slot_atomic(
    p_clinic_id UUID,
    p_phone_number TEXT,
    p_appointment_time TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    c clinics%ROWTYPE;
    apt appointments%ROWTYPE;
    v_ts TIMESTAMP;
    v_slot TIMESTAMP;
    v_now TIMESTAMP := NOW() AT TIME ZONE 'Asia/Kolkata';
    v_err TEXT;
    v_dur INTEGER;
    v_remind TIMESTAMP;
BEGIN
    BEGIN
        v_ts := p_appointment_time::timestamp;
    EXCEPTION WHEN OTHERS THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Could not parse the new date/time.');
    END;

    SELECT * INTO c FROM clinics WHERE id = p_clinic_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Clinic not found.');
    END IF;

    IF COALESCE(c.booking_mode, 'scheduled') = 'token' THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Token clinics cannot reschedule to a time. Cancel the token and generate a new one if needed.');
    END IF;

    SELECT * INTO apt
    FROM appointments
    WHERE clinic_id = p_clinic_id
      AND phone_number = p_phone_number
      AND status = 'booked'
      AND appointment_time >= v_now
    ORDER BY appointment_time ASC
    LIMIT 1
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: No upcoming booked appointment to reschedule. Use book_slot instead.');
    END IF;

    v_dur := GREATEST(COALESCE(c.slot_duration_minutes, 10), 1);
    v_slot := align_slot_start(v_ts, v_dur);
    v_ts := v_slot;

    IF v_ts < v_now THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Cannot reschedule into the past.');
    END IF;

    v_err := clinic_is_open_at(c, v_ts);
    IF v_err IS NOT NULL THEN
        RETURN jsonb_build_object('status', 'error', 'message', v_err);
    END IF;

    -- Free the old slot first so a move to a new time cannot collide with itself
    UPDATE appointments SET slot_start = NULL WHERE id = apt.id;

    UPDATE appointments
    SET appointment_time = v_ts,
        slot_start = v_slot
    WHERE id = apt.id;

    DELETE FROM scheduled_messages WHERE appointment_id = apt.id AND kind = 'reminder' AND status = 'pending';
    v_remind := v_ts - INTERVAL '2 hours';
    IF v_remind > v_now THEN
        INSERT INTO scheduled_messages (appointment_id, clinic_id, phone_number, kind, send_at, status)
        VALUES (apt.id, p_clinic_id, p_phone_number, 'reminder', v_remind, 'pending');
    END IF;

    RETURN jsonb_build_object(
        'status', 'success',
        'appointment_id', apt.id,
        'slot_start', to_char(v_slot, 'YYYY-MM-DD HH24:MI'),
        'message', format('Rescheduled from %s to %s.', to_char(apt.appointment_time, 'YYYY-MM-DD HH24:MI'), to_char(v_slot, 'YYYY-MM-DD HH24:MI'))
    );
EXCEPTION WHEN unique_violation THEN
    -- Restore original slot if the new one was taken
    UPDATE appointments
    SET slot_start = align_slot_start(apt.appointment_time, GREATEST(COALESCE(c.slot_duration_minutes, 10), 1))
    WHERE id = apt.id AND slot_start IS NULL AND status = 'booked';
    RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: The new slot is taken. Keep the original appointment and offer another time.');
END;
$$;

CREATE OR REPLACE FUNCTION claim_wamid(p_wamid TEXT, p_phone TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO processed_webhook_messages (wamid, phone_number)
    VALUES (p_wamid, p_phone);
    RETURN TRUE;
EXCEPTION WHEN unique_violation THEN
    RETURN FALSE;
END;
$$;

CREATE OR REPLACE FUNCTION increment_api_usage(p_limit INTEGER DEFAULT 990)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_month TEXT := to_char(NOW() AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM');
    v_count INTEGER;
BEGIN
    INSERT INTO api_usage (month_year, message_count)
    VALUES (v_month, 1)
    ON CONFLICT (month_year) DO UPDATE
      SET message_count = api_usage.message_count + 1
      WHERE api_usage.message_count < p_limit
    RETURNING message_count INTO v_count;

    IF v_count IS NULL THEN
        RETURN FALSE;
    END IF;
    RETURN TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION claim_due_reminders(p_limit INTEGER DEFAULT 20)
RETURNS SETOF scheduled_messages
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    WITH due AS (
        SELECT id
        FROM scheduled_messages
        WHERE status = 'pending'
          AND send_at <= (NOW() AT TIME ZONE 'Asia/Kolkata')
        ORDER BY send_at
        LIMIT p_limit
        FOR UPDATE SKIP LOCKED
    )
    UPDATE scheduled_messages s
    SET status = 'sending',
        attempts = s.attempts + 1
    FROM due
    WHERE s.id = due.id
    RETURNING s.*;
END;
$$;

REVOKE ALL ON FUNCTION book_slot_atomic(UUID, TEXT, TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION generate_token_atomic(UUID, TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION cancel_appointment_atomic(UUID, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION reschedule_slot_atomic(UUID, TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION claim_wamid(TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION increment_api_usage(INTEGER) FROM PUBLIC;
REVOKE ALL ON FUNCTION claim_due_reminders(INTEGER) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION book_slot_atomic(UUID, TEXT, TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION generate_token_atomic(UUID, TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION cancel_appointment_atomic(UUID, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION reschedule_slot_atomic(UUID, TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION claim_wamid(TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION increment_api_usage(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION claim_due_reminders(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION align_slot_start(TIMESTAMP, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION clinic_is_open_at(clinics, TIMESTAMP) TO service_role;
