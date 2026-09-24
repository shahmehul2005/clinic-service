-- V2 Migration: Add consultation_fee, maps_link, and reminder_sent columns
-- Run this in Supabase SQL Editor before deploying v2-interactive

-- New clinic profile fields
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS consultation_fee TEXT;
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS maps_link TEXT;

-- Reminder deduplication flag on appointments
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT FALSE;
