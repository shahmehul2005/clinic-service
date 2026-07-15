-- token_migration.sql
-- Run this in the Supabase SQL Editor to support the new Dual-Mode Queue System

-- 1. Add booking_mode and current_serving_token to clinics table
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS booking_mode text DEFAULT 'scheduled';
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS current_serving_token integer DEFAULT 0;

-- 2. Add token_number to appointments table
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS token_number integer;
