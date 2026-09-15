-- Run this once on an existing ShreeRide database after 003_drivers_table.sql.
-- Adds the pickup location captured at booking time.
USE ridex_db;

ALTER TABLE bookings
    ADD COLUMN pickup_location VARCHAR(255) NOT NULL DEFAULT 'Not specified' AFTER pickup_time;

-- Remove the temporary default so new bookings must always supply a pickup location.
ALTER TABLE bookings
    ALTER COLUMN pickup_location DROP DEFAULT;
