# ShreeRide - Advance Car Booking System

Flask + MySQL car rental web app with customer, driver, and admin workflows.

## Features - Customers
- Signup/login with hashed passwords
- Browse cars with search, seats and price filters
- Availability check per pickup period (no double booking)
- Advance booking only: tomorrow to +2 months
- Live total price preview, demo payment as Paid
- Digital invoice view + print
- Cancel Confirmed only before 24h of pickup (becomes Refunded)

## Features - Drivers and Admin
- Driver login by phone, Accept/Reject jobs
- Customer sees driver details only after Accept
- Admin: add cars, toggle Available, view all bookings/invoices
- Admin: add/activate drivers, manual or auto assign
- Conflict-safe driver assignment, overdue flags

## Tech Stack
- Python 3.12, Flask 3.1, Werkzeug
- MySQL 8.0 via mysql-connector-python
- Jinja2 templates, HTML/CSS, optional Google Places
- python-dotenv + .env config

## Project Structure
- app.py : main Flask app
- database.sql : fresh schema + seed data
- migrations/ : 002 to 005 upgrade scripts in order
- static/style.css and templates/ : frontend (12 pages)
- requirements.txt, .env.example, .gitignore, LICENSE

## Requirements
- Python 3.10+ (tested 3.12.3), MySQL 8.0+, pip + venv
- Optional Google Maps browser key for Places autocomplete

## Quick Start
1. git clone https://github.com/<YOUR_USERNAME>/ShreeRide.git
2. cd ShreeRide
3. python -m venv venv
4. venv/Scripts/activate (Windows) or source venv/bin/activate (Linux/Mac)
5. pip install -r requirements.txt
6. cp .env.example .env  (then edit MYSQL password + SECRET_KEY)
7. In MySQL run: SOURCE database.sql;
8. python app.py, open http://127.0.0.1:5000/

## Env Example
- MYSQL_HOST=localhost
- MYSQL_USER=root
- MYSQL_PASSWORD=YOUR_MYSQL_PASSWORD
- MYSQL_DATABASE=ridex_db
- SECRET_KEY=long-random-string (generate via secrets.token_urlsafe)
- FLASK_ENV=development
- GOOGLE_MAPS_API_KEY=optional

## Demo Logins (change before deploy)
- Admin: /admin/login admin / admin123
- Drivers: /driver/login phones 9876543210, 9123456780, 9830123456, 9007123456, 8910123456, 9087654321 password driver123
- Customers: self-register at /signup

## Routes
- / Home, /cars Fleet, /book/<car_id> Booking (login)
- /my-bookings History, /invoice/<id> Invoice
- /admin/login Dashboard, /driver/login Dashboard

## Security
- Real .env never committed (gitignored)
- Passwords hashed, HttpOnly SameSite=Lax cookies, Secure in prod
- Server validates dates, overlap, 24h cancel rule, category/seats/price

## License
MIT - see LICENSE. Author Tanushree. Private repo.
