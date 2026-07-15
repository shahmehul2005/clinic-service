-- Enable pg_cron extension if not already enabled (Requires Superuser/Supabase Dashboard access)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Create a function to clean up old no-show appointments
CREATE OR REPLACE FUNCTION delete_noshow_appointments()
RETURNS void AS $$
BEGIN
    -- Delete appointments that were just booked (never arrived or seen)
    -- and the appointment time is older than 24 hours in the past.
    DELETE FROM appointments
    WHERE status = 'booked'
    AND appointment_time < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Schedule the function to run every day at midnight (UTC)
SELECT cron.schedule('cleanup-noshows', '0 0 * * *', 'SELECT delete_noshow_appointments()');

-- Create a function to reset token queues for tokenized clinics
CREATE OR REPLACE FUNCTION reset_daily_tokens()
RETURNS void AS $$
BEGIN
    UPDATE clinics
    SET current_serving_token = 0
    WHERE booking_mode = 'token';
END;
$$ LANGUAGE plpgsql;

-- Schedule the token reset to run every day at midnight IST (18:30 UTC)
SELECT cron.schedule('reset-tokens', '30 18 * * *', 'SELECT reset_daily_tokens()');
