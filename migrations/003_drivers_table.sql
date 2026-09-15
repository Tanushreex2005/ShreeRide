-- Run this once on an existing ShreeRide database after 002_booking_schedule_indexes.sql.
USE ridex_db;

CREATE TABLE drivers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    status ENUM('Active','Inactive') NOT NULL DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO drivers (name, phone, password) VALUES
('Arjun Das', '9876543210', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Rahul Roy', '9123456780', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Sourav Sen', '9830123456', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Amit Ghosh', '9007123456', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Rohan Dutta', '8910123456', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Vikram Singh', '9087654321', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790');

ALTER TABLE bookings
    ADD COLUMN driver_id INT NULL AFTER driver_request_status,
    ADD INDEX idx_bookings_driver_id_schedule (driver_id, booking_status, pickup_date, pickup_time),
    ADD CONSTRAINT fk_booking_driver FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL;

UPDATE bookings b
JOIN drivers d ON d.phone = b.driver_phone
SET b.driver_id = d.id
WHERE b.driver_id IS NULL AND b.driver_phone IS NOT NULL;
