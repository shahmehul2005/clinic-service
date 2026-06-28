-- Drop tables if they exist to allow clean recreation during testing
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS clinics;

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

-- 4. Enable Row Level Security (Optional but recommended for SaaS)
ALTER TABLE clinics ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

-- 5. Insert a Mock Clinic for immediate testing
INSERT INTO clinics (id, business_name, meta_phone_number_id)
VALUES ('00000000-0000-0000-0000-000000000001', 'Demo Clinic', 'DEMO_META_PHONE_ID')
ON CONFLICT DO NOTHING;
