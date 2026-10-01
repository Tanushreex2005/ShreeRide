-- PostgreSQL schema and starter data for Render.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(80) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS drivers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Active' CHECK (
        status IN ('Active', 'Inactive')
    ),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cars (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    brand VARCHAR(80) NOT NULL,
    category VARCHAR(20) NOT NULL CHECK (
        category IN (
            'Sedan',
            'SUV',
            'Hatchback',
            'Luxury',
            'Electric',
            'MPV'
        )
    ),
    seats INT NOT NULL DEFAULT 5,
    price_per_day DECIMAL(10, 2) NOT NULL,
    image_url TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'Available' CHECK (
        status IN ('Available', 'Unavailable')
    ),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    invoice_no VARCHAR(50) UNIQUE,
    user_id INT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    car_id INT NOT NULL REFERENCES cars (id) ON DELETE RESTRICT,
    pickup_date DATE NOT NULL,
    pickup_time TIME NOT NULL,
    pickup_location VARCHAR(255) NOT NULL,
    return_date DATE NOT NULL,
    return_location VARCHAR(255) NOT NULL,
    duration_days INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'Pending' CHECK (
        payment_status IN ('Pending', 'Paid', 'Refunded')
    ),
    booking_status VARCHAR(20) DEFAULT 'Confirmed' CHECK (
        booking_status IN (
            'Confirmed',
            'Completed',
            'Cancelled'
        )
    ),
    driver_request_status VARCHAR(20) DEFAULT 'Pending' CHECK (
        driver_request_status IN (
            'Pending',
            'Accepted',
            'Rejected'
        )
    ),
    driver_id INT REFERENCES drivers (id) ON DELETE SET NULL,
    driver_name VARCHAR(100),
    driver_phone VARCHAR(15),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bookings_car_schedule ON bookings (
    car_id,
    booking_status,
    pickup_date,
    pickup_time
);

CREATE INDEX IF NOT EXISTS idx_bookings_driver_schedule ON bookings (
    driver_id,
    booking_status,
    pickup_date,
    pickup_time
);

CREATE INDEX IF NOT EXISTS idx_bookings_user_created ON bookings (user_id, created_at);

INSERT INTO
    admins (name, username, password)
VALUES (
        'ShreeRide Administrator',
        'admin',
        'scrypt:32768:8:1$MEepp04E2Mi0WXwQ$196a646d70ddaaf3c941cc24650cf78cc2945db59f03130fe0d5b6db419c4a9db54d660869efc027b395d2e2f9cb7266269049838f2d26330f18c9789976e661'
    ) ON CONFLICT (username) DO NOTHING;

INSERT INTO
    drivers (name, phone, password)
VALUES (
        'Arjun Das',
        '9876543210',
        'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'
    ),
    (
        'Rahul Roy',
        '9123456780',
        'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'
    ),
    (
        'Sourav Sen',
        '9830123456',
        'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'
    ),
    (
        'Amit Ghosh',
        '9007123456',
        'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'
    ),
    (
        'Rohan Dutta',
        '8910123456',
        'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'
    ),
    (
        'Vikram Singh',
        '9087654321',
        'scrypt:32768:8:1$6Vbmr4uWfkqehOAC$7db654e86589a8d9dab29f928086bc7659e5538c9d83eff080a540a0d5ae556a19966e893c9f22e715b86517c05150e258a627e505fbed1e41ac9c7aa0928790'
    ) ON CONFLICT (phone) DO NOTHING;

INSERT INTO
    cars (
        name,
        brand,
        category,
        seats,
        price_per_day,
        image_url
    )
VALUES (
        'City ZX',
        'Honda',
        'Sedan',
        5,
        1800,
        'https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?auto=format&fit=crop&w=1000&q=80'
    ),
    (
        'Creta',
        'Hyundai',
        'SUV',
        5,
        2400,
        'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=1000&q=80'
    ),
    (
        'Nexon',
        'Tata',
        'SUV',
        5,
        2100,
        'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1000&q=80'
    ),
    (
        'Swift',
        'Maruti Suzuki',
        'Hatchback',
        5,
        1500,
        'https://images.unsplash.com/photo-1494976388531-d1058494cdd8?auto=format&fit=crop&w=1000&q=80'
    ),
    (
        'Camry',
        'Toyota',
        'Luxury',
        5,
        4200,
        'https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=1000&q=80'
    ),
    (
        'Verna',
        'Hyundai',
        'Sedan',
        5,
        2000,
        'https://commons.wikimedia.org/wiki/Special:FilePath/0%20Hyundai%20Verna%20(MC)%201.jpg?width=1000'
    ),
    (
        'Seltos',
        'Kia',
        'SUV',
        5,
        2600,
        'https://commons.wikimedia.org/wiki/Special:FilePath/White%20KIA%20Seltos%20(Front).jpg?width=1000'
    ),
    (
        'Thar ROXX',
        'Mahindra',
        'SUV',
        5,
        3000,
        'https://commons.wikimedia.org/wiki/Special:FilePath/Mahindra%20Thar%20ROXX%20on%20dirt.jpg?width=1000'
    ),
    (
        'Ertiga',
        'Maruti Suzuki',
        'MPV',
        7,
        2200,
        'https://commons.wikimedia.org/wiki/Special:FilePath/Maruti%20Suzuki%20Ertiga(2).jpg?width=1000'
    ),
    (
        'Innova Crysta',
        'Toyota',
        'MPV',
        7,
        3500,
        'https://commons.wikimedia.org/wiki/Special:FilePath/Toyota%20Innova%20Crysta%202.4%20Z%20front%20right.jpg?width=1000'
    ),
    (
        'Nexon EV',
        'Tata',
        'Electric',
        5,
        2500,
        'https://commons.wikimedia.org/wiki/Special:FilePath/Tata%20Nexon%20EV%20in%20Hyderabad%2002.jpg?width=1000'
    ),
    (
        'Comet EV',
        'MG',
        'Electric',
        4,
        1400,
        'https://commons.wikimedia.org/wiki/Special:FilePath/2023%20MG%20Comet%20EV%20Plush%20(India).png?width=1000'
    ) ON CONFLICT DO NOTHING;