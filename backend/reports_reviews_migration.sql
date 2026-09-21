-- ============================================================
-- Migration: Reports & Google Reviews
-- Run this in Supabase SQL Editor
-- ============================================================

-- 1. Add new settings columns to clinics table
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS google_review_link TEXT;
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS doctor_name TEXT;
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS clinic_address TEXT;

-- 2. Create patient_reports table (audit trail of sent reports)
CREATE TABLE IF NOT EXISTS patient_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
    phone_number TEXT NOT NULL,
    patient_name TEXT,
    patient_age TEXT,
    doctor_name TEXT,
    chief_complaint TEXT,
    diagnosis TEXT,
    medicines JSONB DEFAULT '[]'::jsonb,   -- [{name, dosage, frequency, duration}]
    followup_date TEXT,
    special_notes TEXT,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Disable RLS for MVP (consistent with existing tables)
ALTER TABLE patient_reports DISABLE ROW LEVEL SECURITY;

-- 4. Index for fast clinic/phone lookups
CREATE INDEX IF NOT EXISTS idx_patient_reports_clinic_id ON patient_reports(clinic_id);
CREATE INDEX IF NOT EXISTS idx_patient_reports_phone ON patient_reports(phone_number);
