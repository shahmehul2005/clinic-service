-- ============================================================
-- New Features Migration
-- Run this in your Supabase SQL Editor
-- ============================================================

-- 1. Add broadcast_count to clinics table
--    Tracks how many times a clinic has sent a broadcast.
--    Trial clinics are limited to 2. NULL trial_end_date = permanent.
ALTER TABLE clinics
  ADD COLUMN IF NOT EXISTS broadcast_count INTEGER DEFAULT 0;

-- 2. Create patient_details table
--    Stores persistent health info per patient per clinic.
--    Keyed by (clinic_id, phone_number) so it survives across multiple appointments.
CREATE TABLE IF NOT EXISTS patient_details (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinic_id       UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    phone_number    TEXT NOT NULL,
    patient_name    TEXT,
    age             TEXT DEFAULT '',
    blood_group     TEXT DEFAULT '',
    allergies       TEXT DEFAULT '',
    conditions      TEXT DEFAULT '',
    emergency_contact TEXT DEFAULT '',
    notes           TEXT DEFAULT '',
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (clinic_id, phone_number)
);

-- 3. Disable RLS on patient_details (consistent with rest of schema)
ALTER TABLE patient_details DISABLE ROW LEVEL SECURITY;

-- 4. Index for fast lookups by phone
CREATE INDEX IF NOT EXISTS idx_patient_details_clinic_phone
  ON patient_details (clinic_id, phone_number);

-- Done!

-- ============================================================
-- BUGFIX: generate_token_atomic — stale current_serving_token
-- When a new day starts, the DB still holds yesterday's
-- current_serving_token (e.g. 17). The function now resets it
-- to 0 on the first token of the day so WhatsApp messages show
-- correct "people ahead of you" counts.
-- ============================================================
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
    v_max_from_apts INTEGER;
    v_base INTEGER;
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

    -- (open-hours check calls existing helper if present)
    BEGIN
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
    EXCEPTION WHEN undefined_function THEN
        NULL; -- clinic_is_open_at not defined yet, skip check
    END;

    -- ── KEY FIX: reset in-memory serving counter on new day ──
    IF c.token_seq_date IS DISTINCT FROM v_today THEN
        v_base := 0;
        c.current_serving_token := 0;   -- use 0 for ahead-count calc
    ELSE
        v_base := COALESCE(c.last_issued_token, 0);
    END IF;

    -- Also read max token from today's appointments (dashboard-inserted rows)
    SELECT COALESCE(MAX(token_number), 0)
    INTO v_max_from_apts
    FROM appointments
    WHERE clinic_id = p_clinic_id
      AND (
        token_date = v_today
        OR (token_date IS NULL AND (appointment_time AT TIME ZONE 'Asia/Kolkata')::date = v_today)
      );

    v_base := GREATEST(v_base, v_max_from_apts);
    v_next := v_base + 1;

    -- ── KEY FIX: also reset current_serving_token in DB on new day ──
    UPDATE clinics
    SET last_issued_token     = v_next,
        token_seq_date        = v_today,
        current_serving_token = CASE
            WHEN token_seq_date IS DISTINCT FROM v_today THEN 0
            ELSE current_serving_token
        END
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
            'Successfully generated Token #%s. Current serving: #%s. People ahead: %s.',
            v_next, COALESCE(c.current_serving_token, 0), v_ahead
        )
    );
EXCEPTION WHEN unique_violation THEN
    RETURN jsonb_build_object('status', 'error', 'message', 'CRITICAL: Token assignment collided. Retry generate_token.');
END;
$$;

