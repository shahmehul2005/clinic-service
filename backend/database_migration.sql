-- Drop tables if they exist to allow clean recreation during testing
DROP TABLE IF EXISTS api_usage;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS clinics;

-- 0. Create API Usage Table for Rate Limiting
CREATE TABLE api_usage (
    month_year TEXT PRIMARY KEY, -- e.g. "2026-07"
    message_count INTEGER DEFAULT 0
);

-- 1. Create Clinics Table
CREATE TABLE clinics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_name TEXT NOT NULL,
    meta_phone_number_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create Appointments Table
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    patient_name TEXT,
    appointment_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    status TEXT NOT NULL DEFAULT 'booked',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. CRITICAL: Composite UNIQUE Constraint for Atomic Transaction Control
-- This absolute protection guarantees that for a specific clinic, 
-- an appointment_time can only be booked exactly once.
ALTER TABLE appointments 
ADD CONSTRAINT unique_clinic_appointment_time 
UNIQUE (clinic_id, appointment_time);

-- 4. Disable Row Level Security (RLS) for MVP
-- RLS blocks all frontend access by default unless specific policies are created.
-- For this sandbox/MVP phase, we disable it so the dashboard works.
ALTER TABLE clinics DISABLE ROW LEVEL SECURITY;
ALTER TABLE appointments DISABLE ROW LEVEL SECURITY;

-- 5. Insert a Mock Clinic for immediate testing
INSERT INTO clinics (id, business_name, meta_phone_number_id)
VALUES ('00000000-0000-0000-0000-000000000001', 'Demo Clinic', 'DEMO_META_PHONE_ID')
ON CONFLICT DO NOTHING;
