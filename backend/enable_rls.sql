-- enable_rls.sql
-- Run this in the Supabase SQL Editor to lock down data access to only authorized clinics.

-- 1. Enable RLS on both tables
ALTER TABLE clinics ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

-- 2. Drop existing policies just in case
DROP POLICY IF EXISTS "Clinics can view their own data" ON clinics;
DROP POLICY IF EXISTS "Appointments are viewable by clinic" ON appointments;
DROP POLICY IF EXISTS "Appointments are insertable by clinic" ON appointments;
DROP POLICY IF EXISTS "Appointments are updatable by clinic" ON appointments;
DROP POLICY IF EXISTS "Appointments are deletable by clinic" ON appointments;

-- 3. Policy for Clinics Table
-- A logged-in user can only read their own clinic's metadata.
CREATE POLICY "Clinics can view their own data" ON clinics
FOR SELECT USING (
  id = (auth.jwt()->'user_metadata'->>'clinic_id')::uuid
);

-- 4. Policies for Appointments Table
-- A logged-in user can only SELECT, INSERT, UPDATE, or DELETE appointments that belong to their clinic_id.
CREATE POLICY "Appointments are viewable by clinic" ON appointments
FOR SELECT USING (
  clinic_id = (auth.jwt()->'user_metadata'->>'clinic_id')::uuid
);

CREATE POLICY "Appointments are insertable by clinic" ON appointments
FOR INSERT WITH CHECK (
  clinic_id = (auth.jwt()->'user_metadata'->>'clinic_id')::uuid
);

CREATE POLICY "Appointments are updatable by clinic" ON appointments
FOR UPDATE USING (
  clinic_id = (auth.jwt()->'user_metadata'->>'clinic_id')::uuid
);

CREATE POLICY "Appointments are deletable by clinic" ON appointments
FOR DELETE USING (
  clinic_id = (auth.jwt()->'user_metadata'->>'clinic_id')::uuid
);

-- Note: The backend python app connects using the 'service_role' key, which automatically bypasses RLS.
-- Therefore, webhooks and the admin onboarding portal will continue to work normally without extra policies.
