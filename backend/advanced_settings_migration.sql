ALTER TABLE clinics ADD COLUMN IF NOT EXISTS closed_date DATE;
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS working_days JSONB DEFAULT '["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]'::jsonb;
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS working_hours JSONB DEFAULT '{"start": "09:00", "end": "21:00"}'::jsonb;
