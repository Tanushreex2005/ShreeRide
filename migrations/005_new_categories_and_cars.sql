-- Run this once on an existing ShreeRide database after 004_pickup_location.sql.
-- Adds the Electric and MPV car categories plus 7 new cars.
-- Images are free-licensed photos of the actual Indian models (Wikimedia Commons,
-- which permits hotlinking). Google Images cannot be hotlinked (blocked + copyrighted).
USE ridex_db;

ALTER TABLE cars
    MODIFY COLUMN category ENUM('Sedan','SUV','Hatchback','Luxury','Electric','MPV') NOT NULL;

INSERT INTO cars (name, brand, category, seats, price_per_day, image_url, status) VALUES
('Verna', 'Hyundai', 'Sedan', 5, 2000, 'https://commons.wikimedia.org/wiki/Special:FilePath/0%20Hyundai%20Verna%20(MC)%201.jpg?width=1000', 'Available'),
('Seltos', 'Kia', 'SUV', 5, 2600, 'https://commons.wikimedia.org/wiki/Special:FilePath/White%20KIA%20Seltos%20(Front).jpg?width=1000', 'Available'),
('Thar ROXX', 'Mahindra', 'SUV', 5, 3000, 'https://commons.wikimedia.org/wiki/Special:FilePath/Mahindra%20Thar%20ROXX%20on%20dirt.jpg?width=1000', 'Available'),
('Ertiga', 'Maruti Suzuki', 'MPV', 7, 2200, 'https://commons.wikimedia.org/wiki/Special:FilePath/Maruti%20Suzuki%20Ertiga(2).jpg?width=1000', 'Available'),
('Innova Crysta', 'Toyota', 'MPV', 7, 3500, 'https://commons.wikimedia.org/wiki/Special:FilePath/Toyota%20Innova%20Crysta%202.4%20Z%20front%20right.jpg?width=1000', 'Available'),
('Nexon EV', 'Tata', 'Electric', 5, 2500, 'https://commons.wikimedia.org/wiki/Special:FilePath/Tata%20Nexon%20EV%20in%20Hyderabad%2002.jpg?width=1000', 'Available'),
('Comet EV', 'MG', 'Electric', 4, 1400, 'https://commons.wikimedia.org/wiki/Special:FilePath/2023%20MG%20Comet%20EV%20Plush%20(India).png?width=1000', 'Available');
