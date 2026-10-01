# ShreeRide - Advance Car Booking System

Flask + PostgreSQL car rental web app for Render, with the original MySQL setup preserved.
Search and filter cars, book by date/time period, generate invoices, assign
drivers, and manage fleet.

## Badges

Python 3.12 | Flask 3.1 | MySQL 8.0 | Private repo | MIT License

## Highlights

- Triple-role app: customer, driver, admin in one Flask codebase
- Conflict-safe booking: no double-booked car or driver for overlapping periods
- Advance window: tomorrow to +2 calendar months, 24h cancel rule
- Invoices, search + filters, overdue flags, Google Places (optional)

## Features - Customers

- Signup/login with hashed passwords (Werkzeug scrypt)
- Browse cars with search (name/brand), seats and price filters
- Availability check per pickup period, live return-date + total preview
- Demo payment recorded as Paid, digital invoice view + print
- Cancel Confirmed only before 24h of pickup (becomes Refunded)
- My Bookings dashboard with search + status filters

## Features - Drivers and Admin

- Driver login by phone, Accept/Reject jobs, Active/Inactive control
- Customer sees driver details only after Accept
- Admin: add cars, toggle Available/Unavailable, view all bookings + invoices
- Admin: add drivers, manual pick or random auto-assign of free driver
- Completed/Cancelled releases car + driver

## Tech Stack

- Backend: Python 3.12, Flask 3.1, Werkzeug, psycopg2-binary for Render PostgreSQL
- Frontend: Jinja2, HTML/CSS, Google Places autocomplete (optional)
- Config: python-dotenv + .env, session cookies HttpOnly SameSite=Lax

## Project Structure

- app.py : routes, auth, booking logic, validation
- database_postgres.sql : Render PostgreSQL schema and starter data
- init_postgres.py : initializes an empty Render database before deploy
- database.sql : preserved MySQL schema and seed
  (admin, 6 drivers, 12 cars, all indexes, Electric/MPV included)
- static/style.css + templates/ (12 pages) : UI
- requirements.txt, .env.example, .gitignore, LICENSE

## Requirements

- Python 3.10+ (tested 3.12.3), MySQL 8.0+, pip + venv
- Optional Google Maps browser key for Places autocomplete

## Quick Start

1. git clone https://github.com/Tanushreex2005/ShreeRide.git
2. cd ShreeRide
3. python -m venv venv
4. venv/Scripts/activate (Windows) or source venv/bin/activate (Mac/Linux)
5. pip install -r requirements.txt
6. cp .env.example .env (edit MYSQL password + SECRET_KEY)
7. In MySQL run: SOURCE database.sql; (single file creates everything)
8. python app.py, open http://127.0.0.1:5000/

No migrations folder - database.sql already contains all tables,
indexes, drivers, and latest cars.

## Render PostgreSQL

The root `render.yaml` Blueprint provisions Render PostgreSQL, initializes it from `database_postgres.sql`, and starts `app.py` with Gunicorn. Render supplies `DATABASE_URL` and generates `SECRET_KEY`. The original MySQL schema remains available, with its optional Blueprint in `render-mysql.yaml`.

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment steps and demo-account details.

## Env Example

- MYSQL_HOST=localhost, MYSQL_USER=root
- MYSQL_PASSWORD=YOUR_MYSQL_PASSWORD, MYSQL_DATABASE=ridex_db
- SECRET_KEY=long-random-string via python secrets.token_urlsafe(32)
- FLASK_ENV=development, GOOGLE_MAPS_API_KEY=optional

## Demo Logins (change before deploy)

- Admin /admin/login : admin / admin123
- Drivers /driver/login password driver123 :
  9876543210 Arjun, 9123456780 Rahul, 9830123456 Sourav,
  9007123456 Amit, 8910123456 Rohan, 9087654321 Vikram
- Customers: self-register at /signup

## Routes and Rules

- / Home, /cars Fleet + filters, /book/<car_id> Booking
- /my-bookings History, /invoice/<id> Invoice
- /admin/login Dashboard, /driver/login Dashboard
- pickup tomorrow to +2 months, return after pickup, no overlap,
  cancel only if pickup minus now >= 24h

## Screenshots

Add your screenshots under docs/screenshots/ then link here:

- docs/screenshots/home.png, cars.png, booking.png, invoice.png,
  admin-dashboard.png, driver-dashboard.png

## Security

- Real .env never committed (gitignored), fail-fast if keys missing
- Passwords hashed, HttpOnly SameSite=Lax cookies, Secure in prod
- Validates email/phone, category whitelist, seats/price, image URL

## Contributing

See CONTRIBUTING.md. Use feature branches + PRs to main.

## License

MIT - see LICENSE. Author Tanushree.
Built with Flask + PostgreSQL for Render. Private repo.
