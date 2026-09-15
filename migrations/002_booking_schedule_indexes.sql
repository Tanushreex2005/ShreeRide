-- Run this once on an existing ShreeRide database. Do not run it after rebuilding
-- from database.sql, because that fresh schema already contains these indexes.
USE ridex_db;

ALTER TABLE bookings
    ADD INDEX idx_bookings_car_schedule (car_id, booking_status, pickup_date, pickup_time),
    ADD INDEX idx_bookings_user_created (user_id, created_at);
