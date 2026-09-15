CREATE DATABASE IF NOT EXISTS ridex_db;
USE ridex_db;

DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS drivers;
DROP TABLE IF EXISTS cars;
DROP TABLE IF EXISTS admins;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(80) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE drivers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    status ENUM('Active','Inactive') NOT NULL DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cars (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    brand VARCHAR(80) NOT NULL,
    category ENUM('Sedan','SUV','Hatchback','Luxury','Electric','MPV') NOT NULL,
    seats INT NOT NULL DEFAULT 5,
    price_per_day DECIMAL(10,2) NOT NULL,
    image_url TEXT,
    status ENUM('Available','Unavailable') NOT NULL DEFAULT 'Available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_no VARCHAR(50) UNIQUE,
    user_id INT NOT NULL,
    car_id INT NOT NULL,
    pickup_date DATE NOT NULL,
    pickup_time TIME NOT NULL,
    pickup_location VARCHAR(255) NOT NULL,
    return_date DATE NOT NULL,
    return_location VARCHAR(255) NOT NULL,
    duration_days INT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_status ENUM('Pending','Paid','Refunded') DEFAULT 'Pending',
    booking_status ENUM('Confirmed','Completed','Cancelled') DEFAULT 'Confirmed',
    driver_request_status ENUM('Pending','Accepted','Rejected') DEFAULT 'Pending',
    driver_id INT DEFAULT NULL,
    driver_name VARCHAR(100) DEFAULT NULL,
    driver_phone VARCHAR(15) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_bookings_car_schedule (car_id, booking_status, pickup_date, pickup_time),
    INDEX idx_bookings_driver_schedule (driver_id, booking_status, pickup_date, pickup_time),
    INDEX idx_bookings_user_created (user_id, created_at),
    CONSTRAINT fk_booking_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_booking_car FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE RESTRICT,
    CONSTRAINT fk_booking_driver FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL
);

INSERT INTO admins (name, username, password)
VALUES ('ShreeRide Administrator', 'admin', 'scrypt:32768:8:1$MEepp04E2Mi0WXwQ$196a646d70ddaaf3c941cc24650cf78cc2945db59f03130fe0d5b6db419c4a9db54d660869efc027b395d2e2f9cb7266269049838f2d26330f18c9789976e661');

INSERT INTO drivers (name, phone, password) VALUES
('Arjun Das', '9876543210', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Rahul Roy', '9123456780', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Sourav Sen', '9830123456', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Amit Ghosh', '9007123456', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Rohan Dutta', '8910123456', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'),
('Vikram Singh', '9087654321', 'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790');

INSERT INTO cars (name, brand, category, seats, price_per_day, image_url) VALUES
('City ZX', 'Honda', 'Sedan', 5, 1800, 'https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?auto=format&fit=crop&w=1000&q=80'),
('Creta', 'Hyundai', 'SUV', 5, 2400, 'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=1000&q=80'),
('Nexon', 'Tata', 'SUV', 5, 2100, 'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1000&q=80'),
('Swift', 'Maruti Suzuki', 'Hatchback', 5, 1500, 'https://images.unsplash.com/photo-1494976388531-d1058494cdd8?auto=format&fit=crop&w=1000&q=80'),
('Camry', 'Toyota', 'Luxury', 5, 4200, 'https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=1000&q=80'),
('Verna', 'Hyundai', 'Sedan', 5, 2000, 'https://commons.wikimedia.org/wiki/Special:FilePath/0%20Hyundai%20Verna%20(MC)%201.jpg?width=1000'),
('Seltos', 'Kia', 'SUV', 5, 2600, 'https://commons.wikimedia.org/wiki/Special:FilePath/White%20KIA%20Seltos%20(Front).jpg?width=1000'),
('Thar ROXX', 'Mahindra', 'SUV', 5, 3000, 'https://commons.wikimedia.org/wiki/Special:FilePath/Mahindra%20Thar%20ROXX%20on%20dirt.jpg?width=1000'),
('Ertiga', 'Maruti Suzuki', 'MPV', 7, 2200, 'https://commons.wikimedia.org/wiki/Special:FilePath/Maruti%20Suzuki%20Ertiga(2).jpg?width=1000'),
('Innova Crysta', 'Toyota', 'MPV', 7, 3500, 'https://commons.wikimedia.org/wiki/Special:FilePath/Toyota%20Innova%20Crysta%202.4%20Z%20front%20right.jpg?width=1000'),
('Nexon EV', 'Tata', 'Electric', 5, 2500, 'https://commons.wikimedia.org/wiki/Special:FilePath/Tata%20Nexon%20EV%20in%20Hyderabad%2002.jpg?width=1000'),
('Comet EV', 'MG', 'Electric', 4, 1400, 'https://commons.wikimedia.org/wiki/Special:FilePath/2023%20MG%20Comet%20EV%20Plush%20(India).png?width=1000');

-- Demo driver accounts. Login with phone number and password driver123.
-- Arjun Das       9876543210
-- Rahul Roy       9123456780
-- Sourav Sen      9830123456
-- Amit Ghosh      9007123456
-- Rohan Dutta     8910123456
-- Vikram Singh    9087654321
