import hmac

import os

import secrets

import re

from dotenv import load_dotenv

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

import mysql.connector

from functools import wraps
import calendar
from datetime import date, datetime, time, timedelta

from decimal import Decimal

import random
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()  # This line loads values from a .env file

app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
)

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "SECRET_KEY must be set in the environment. Copy .env.example to .env first."
    )


CAR_CATEGORIES = {"Sedan", "SUV", "Hatchback", "Luxury", "Electric", "MPV"}
DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "user": os.environ.get("MYSQL_USER"),
    "password": os.environ.get("MYSQL_PASSWORD"),
    "database": os.environ.get("MYSQL_DATABASE", "ridex_db"),
}
if not all([DB_CONFIG["user"], DB_CONFIG["password"]]):
    raise RuntimeError("MYSQL_USER and MYSQL_PASSWORD must be set in the environment.")

BOOKING_START_SQL = "TIMESTAMP(pickup_date, pickup_time)"
BOOKING_END_SQL = f"DATE_ADD({BOOKING_START_SQL}, INTERVAL duration_days DAY)"

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")


# Bookings are allowed only inside the advance window:

# from tomorrow (current date + 1) up to 2 calendar months ahead.

MAX_ADVANCE_BOOKING_MONTHS = 2


def add_months(source: date, months: int) -> date:
    """Add calendar months, clamping the day for shorter months."""

    month_index = source.month - 1 + months

    year = source.year + month_index // 12

    month = month_index % 12 + 1  # Target month (1-12)

    last_day = calendar.monthrange(year, month)[
        1
    ]  # For November 2026, the number of days is 30,so:last_day = 30

    return date(year, month, min(source.day, last_day))


def booking_window(today: date | None = None):
    """Return (min_pickup_date, max_pickup_date) allowed for new bookings."""

    today = today or date.today()

    min_pickup = today + timedelta(days=1)

    max_pickup = add_months(today, MAX_ADVANCE_BOOKING_MONTHS)

    return min_pickup, max_pickup


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def query_db(query, params=(), fetchone=False, commit=False) -> Any:
    conn = cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        if commit:
            conn.commit()
            return cursor.lastrowid
        result = cursor.fetchone() if fetchone else cursor.fetchall()
        return result
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def verify_password(stored_password, submitted_password):
    """Support existing demo accounts once, then upgrade them to secure hashes."""

    if stored_password.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored_password, submitted_password), False

    return (
        hmac.compare_digest(stored_password, submitted_password),
        True,
    )  # For checking Old passwords


def booking_start(booking):
    """Normalize MySQL TIME values, which mysql-connector may return as timedelta."""

    pickup_time = booking["pickup_time"]

    if isinstance(pickup_time, timedelta):
        total_seconds = int(pickup_time.total_seconds()) % (24 * 60 * 60)

        pickup_time = time(
            total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60
        )

    elif isinstance(pickup_time, str):
        pickup_time = time.fromisoformat(pickup_time)

    return datetime.combine(booking["pickup_date"], pickup_time)


def booking_end(booking):

    return booking_start(booking) + timedelta(days=booking["duration_days"])


def is_overdue(booking, now: datetime | None = None) -> bool:
    """A Confirmed booking whose rental/return datetime has already passed."""

    if booking.get("booking_status") != "Confirmed":
        return False

    try:
        return booking_end(booking) < (now or datetime.now())

    except (KeyError, TypeError, ValueError):
        return False


def car_is_available(car_id, pickup_at, return_at, exclude_booking_id=None):
    """Check whether a car is free for [pickup_at, return_at)."""

    params = [
        car_id,
        return_at,
        pickup_at,
    ]  # SQL query-à¦à¦° parameters à¦¤à§ˆà¦°à¦¿....à¦à¦‡ à¦®à¦¾à¦¨à¦—à§à¦²à§‹ SQL query-à¦à¦° %s placeholder-à¦ à¦¬à¦¸à¦¾à¦¨à§‹ à¦¹à¦¬à§‡

    query = f"""SELECT id FROM bookings

               WHERE car_id=%s AND booking_status='Confirmed'

                 AND {BOOKING_START_SQL} < %s

                 AND {BOOKING_END_SQL} > %s"""

    if exclude_booking_id:
        query += " AND id<>%s"

        params.append(exclude_booking_id)

    query += " LIMIT 1"

    return query_db(query, tuple(params), fetchone=True) is None


def driver_is_available(driver_id, booking):
    """A driver may take bookings whose rental periods do not overlap."""

    conflict = query_db(
        f"""SELECT id FROM bookings

           WHERE driver_id=%s AND booking_status='Confirmed' AND id<>%s

             AND {BOOKING_START_SQL} < %s

             AND {BOOKING_END_SQL} > %s

           LIMIT 1""",  # AND id<>%s = à¦¬à¦°à§à¦¤à¦®à¦¾à¦¨ à¦¬à§à¦•à¦¿à¦‚à¦Ÿà¦¿à¦•à§‡ à¦¬à¦¾à¦¦ à¦¦à§‡à¦“à§Ÿà¦¾ à¦¹à¦šà§à¦›à§‡à¥¤
        (driver_id, booking["id"], booking_end(booking), booking_start(booking)),
        fetchone=True,
    )

    return conflict is None


def available_drivers_for_booking(booking, drivers=None):

    if booking["booking_status"] != "Confirmed":
        return []

    if drivers is None:
        drivers = query_db(
            "SELECT id, name, phone FROM drivers WHERE status='Active' ORDER BY name"
        )

    return [driver for driver in drivers if driver_is_available(driver["id"], booking)]


def create_booking(
    user_id, car_id, pickup_at, pickup_location, return_location, duration_days
):
    """Lock the car row while checking and creating a booking to prevent double-booking."""

    conn = cursor = None  # conn: à¦¡à¦¾à¦Ÿà¦¾à¦¬à§‡à¦¸ à¦¸à¦‚à¦¯à§‹à¦—

    # cursor: SQL query à¦šà¦¾à¦²à¦¾à¦¨à§‹à¦° à¦®à¦¾à¦§à§à¦¯à¦®

    try:
        conn = get_db()

        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM cars WHERE id=%s AND status='Available' FOR UPDATE",
            (car_id,),
        )  # FOR UPDATE à¦—à¦¾à§œà¦¿à¦° database row-à¦Ÿà¦¿ lock à¦•à¦°à§‡à¥¤

        car = cursor.fetchone()

        if not car:
            conn.rollback()

            return None, "This car is currently unavailable."

        return_at = pickup_at + timedelta(days=duration_days)

        cursor.execute(
            f"""SELECT id FROM bookings

               WHERE car_id=%s AND booking_status='Confirmed'

                 AND {BOOKING_START_SQL} < %s

                 AND {BOOKING_END_SQL} > %s

               LIMIT 1""",
            (car_id, return_at, pickup_at),
        )

        if cursor.fetchone():
            conn.rollback()

            return None, "This car is already booked during that time period."

        total = Decimal(str(car["price_per_day"])) * duration_days

        insert_booking_sql = """INSERT INTO bookings

               (user_id,car_id,pickup_date,pickup_time,pickup_location,return_date,return_location,

                duration_days,total_amount,payment_status,booking_status,driver_request_status)

               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Paid','Confirmed','Pending')"""

        booking_params = (
            user_id,
            car_id,
            pickup_at.date(),
            pickup_at.time(),
            pickup_location,
            return_at.date(),
            return_location,
            duration_days,
            total,
        )
        cursor.execute(insert_booking_sql, booking_params)
        booking_id = cursor.lastrowid

        invoice_no = f"SR-{datetime.now().strftime('%Y%m%d')}-{booking_id:05d}"

        cursor.execute(
            "UPDATE bookings SET invoice_no=%s WHERE id=%s", (invoice_no, booking_id)
        )

        conn.commit()

        return booking_id, None

    except mysql.connector.Error:
        if conn:
            conn.rollback()

        raise

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


@app.context_processor  # Flask-à¦à¦° context processor decorator...à¦à¦° à¦«à¦²à§‡ à¦à¦‡ function à¦¯à§‡ dictionary à¦«à§‡à¦°à¦¤ à¦¦à§‡à§Ÿ, à¦¤à¦¾ à¦¸à¦¬ Jinja template-à¦ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à¦¾ à¦¯à¦¾à§Ÿà¥¤
def csrf_context():

    token = session.get(
        "csrf_token"
    )  # à¦¬à¦°à§à¦¤à¦®à¦¾à¦¨ user session-à¦ à¦†à¦—à§‡ à¦¥à§‡à¦•à§‡ csrf_token à¦†à¦›à§‡ à¦•à¦¿ à¦¨à¦¾ à¦ªà¦°à§€à¦•à§à¦·à¦¾ à¦•à¦°à¦¾ à¦¹à¦šà§à¦›à§‡

    if not token:
        token = secrets.token_urlsafe(32)

        session["csrf_token"] = token

    return {"csrf_token": token}


@app.before_request
def protect_post_requests():

    if request.method == "POST":
        expected = session.get("csrf_token", "")

        submitted = request.form.get(
            "csrf_token", ""
        )  # HTML form à¦¥à§‡à¦•à§‡ csrf_token field-à¦à¦° value à¦¨à§‡à¦“à§Ÿà¦¾ à¦¹à¦šà§à¦›à§‡...Field à¦¨à¦¾ à¦¥à¦¾à¦•à¦²à§‡ à¦–à¦¾à¦²à¦¿ string à¦ªà¦¾à¦“à§Ÿà¦¾ à¦¯à¦¾à¦¬à§‡à¥¤

        if (
            not expected
            or not submitted
            or not hmac.compare_digest(expected, submitted)
        ):
            abort(400, "Invalid or missing CSRF token.")


def user_required(view):

    @wraps(
        view
    )  # @wraps(view) à¦®à§‚à¦² function-à¦à¦° à¦¨à¦¾à¦® à¦“ metadata à¦¸à¦‚à¦°à¦•à§à¦·à¦£ à¦•à¦°à§‡
    def wrapped(
        *args, **kwargs
    ):  # à¦à¦–à¦¾à¦¨à§‡ view à¦¹à¦²à§‹ à¦¸à§‡à¦‡ route function, à¦¯à§‡à¦Ÿà¦¿à¦•à§‡ login protection à¦¦à§‡à¦“à§Ÿà¦¾ à¦¹à¦¬à§‡

        if "user_id" not in session:
            flash("Please login first.", "warning")

            return redirect(url_for("login"))

        return view(
            *args, **kwargs
        )  # à¦¯à¦¦à¦¿ session-à¦ user_id à¦¥à¦¾à¦•à§‡, à¦¤à¦¾à¦¹à¦²à§‡ user login à¦•à¦°à¦¾ à¦†à¦›à§‡à¥¤ à¦¤à¦¾à¦‡ à¦®à§‚à¦² route function à¦šà¦¾à¦²à¦¾à¦¨à§‹ à¦¹à§Ÿ

    return wrapped  # à¦¶à§‡à¦·à§‡ à¦¨à¦¤à§à¦¨ wrapper function à¦«à§‡à¦°à¦¤ à¦¦à§‡à¦“à§Ÿà¦¾ à¦¹à§Ÿ


def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "admin_id" not in session:
            flash("Admin login required.", "warning")

            return redirect(url_for("admin_login"))

        return view(*args, **kwargs)

    return wrapped


def driver_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "driver_id" not in session:
            flash("Driver login required.", "warning")

            return redirect(url_for("driver_login"))

        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():

    cars = query_db(
        "SELECT * FROM cars WHERE status='Available' ORDER BY id DESC LIMIT 3"
    )

    return render_template("index.html", cars=cars)


@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        name = request.form["name"].strip()

        email = request.form["email"].strip().lower()

        phone = request.form["phone"].strip()

        password = request.form["password"]

        if not all([name, email, phone, password]):
            flash("All fields are required.", "error")

            return render_template("signup.html")

        if (
            not 2 <= len(name) <= 100
            or not EMAIL_PATTERN.fullmatch(email)
            or not PHONE_PATTERN.fullmatch(phone)
        ):
            flash(
                "Enter a valid name, email address, and 10-digit Indian phone number.",
                "error",
            )

            return render_template("signup.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")

            return render_template("signup.html")

        if query_db(
            "SELECT id FROM users WHERE email=%s OR phone=%s",
            (email, phone),
            fetchone=True,
        ):
            flash("Email or phone number is already registered.", "error")

            return render_template("signup.html")

        query_db(
            "INSERT INTO users (name,email,phone,password) VALUES (%s,%s,%s,%s)",
            (name, email, phone, generate_password_hash(password)),
            commit=True,
        )

        flash("Account created successfully. Please login.", "success")

        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form["email"].strip().lower()

        password = request.form["password"]

        user = query_db("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)

        if not user:
            flash("Invalid email or password.", "error")

            return render_template("login.html")

        password_valid, needs_upgrade = verify_password(user["password"], password)

        if not password_valid:
            flash("Invalid email or password.", "error")

            return render_template("login.html")

        if needs_upgrade:
            query_db(
                "UPDATE users SET password=%s WHERE id=%s",
                (generate_password_hash(password), user["id"]),
                commit=True,
            )

        session.clear()

        session["user_id"] = user["id"]

        session["user_name"] = user["name"]

        return redirect(url_for("cars"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("index"))


@app.route("/cars")
@user_required
def cars():

    category = request.args.get("category", "All")

    search_query = request.args.get("q", "").strip()

    min_seats = request.args.get("seats", "").strip()

    max_price = request.args.get("max_price", "").strip()

    pickup_date = request.args.get("pickup_date", "").strip()

    pickup_time = request.args.get("pickup_time", "").strip() or "10:00"

    duration = request.args.get("duration", "").strip() or "1"

    where = ["status='Available'"]

    params: list = []  # params-à¦ SQL query-à¦à¦° à¦¨à¦¿à¦°à¦¾à¦ªà¦¦ parameter à¦°à¦¾à¦–à¦¾ à¦¹à¦¬à§‡à¥¤

    if category != "All":
        where.append("category=%s")

        params.append(category)

    if search_query:
        where.append("(name LIKE %s OR brand LIKE %s)")

        like = f"%{search_query}%"

        params.extend([like, like])

    try:
        seats_value = int(min_seats) if min_seats else None

        if seats_value is not None and not 2 <= seats_value <= 12:
            seats_value = None

    except ValueError:
        seats_value = None

    if seats_value:
        where.append("seats>=%s")

        params.append(seats_value)

    try:
        price_value = Decimal(max_price) if max_price else None

        if price_value is not None and not price_value.is_finite():
            price_value = None

    except (ValueError, ArithmeticError):
        price_value = None

    if price_value:
        where.append("price_per_day<=%s")

        params.append(price_value)

    car_list = query_db(
        f"SELECT * FROM cars WHERE {' AND '.join(where)} ORDER BY price_per_day ASC, id DESC",
        tuple(params),
    )

    # Optional availability check: only keep cars free for the requested period.

    availability_checked = False

    availability_error = ""

    availability_summary = ""

    if pickup_date:
        try:
            duration_days = int(duration)

            if not 1 <= duration_days <= 30:
                raise ValueError

            pickup_at = datetime.strptime(
                f"{pickup_date} {pickup_time}", "%Y-%m-%d %H:%M"
            )  # à¦¤à¦¾à¦°à¦¿à¦– à¦“ à¦¸à¦®à§Ÿà¦•à§‡ Python datetime object-à¦ à¦°à§‚à¦ªà¦¾à¦¨à§à¦¤à¦° à¦•à¦°à¦¾ à¦¹à§Ÿà¥¤

            return_at = pickup_at + timedelta(days=duration_days)

            min_pickup, max_pickup = (
                booking_window()
            )  # Booking-à¦à¦° à¦…à¦¨à§à¦®à§‹à¦¦à¦¿à¦¤ à¦¸à¦°à§à¦¬à¦¨à¦¿à¦®à§à¦¨ à¦“ à¦¸à¦°à§à¦¬à§‹à¦šà§à¦š à¦¤à¦¾à¦°à¦¿à¦– à¦¨à§‡à¦“à§Ÿà¦¾ à¦¹à§Ÿà¥¤

            if (
                pickup_at <= datetime.now()
                or not min_pickup <= pickup_at.date() <= max_pickup
            ):
                availability_error = f"Pickup must be between {min_pickup.isoformat()} and {max_pickup.isoformat()}."

            else:
                car_list = [
                    car
                    for car in car_list
                    if car_is_available(car["id"], pickup_at, return_at)
                ]

                availability_checked = True

                availability_summary = (
                    f"Showing cars free from {pickup_at.strftime('%d %b %Y %H:%M')} "
                    f"to {return_at.strftime('%d %b %Y %H:%M')} ({duration_days} day(s))."
                )

        except ValueError:
            availability_error = (
                "Enter a valid pickup date, time and duration (1-30 days)."
            )

    min_pickup, max_pickup = booking_window()

    return render_template(  # cars.html template-à¦ à¦—à¦¾à§œà¦¿à¦° à¦¤à¦¾à¦²à¦¿à¦•à¦¾, filter-à¦à¦° à¦®à¦¾à¦¨, error message à¦à¦¬à¦‚ booking window à¦ªà¦¾à¦ à¦¾à¦¨à§‹ à¦¹à§Ÿà¥¤
        "cars.html",
        cars=car_list,
        category=category,
        search_query=search_query,
        min_seats=min_seats,
        max_price=max_price if max_price else "",
        pickup_date=pickup_date,
        pickup_time=pickup_time,
        duration=duration,
        availability_checked=availability_checked,
        availability_error=availability_error,
        availability_summary=availability_summary,
        min_pickup_date=min_pickup.isoformat(),
        max_pickup_date=max_pickup.isoformat(),
    )


@app.route("/api/car-availability/<int:car_id>")
@user_required
def car_availability(car_id):
    """Live availability check used by the booking page calendar."""

    pickup_date = request.args.get(
        "pickup_date", ""
    ).strip()  # URL query string à¦¥à§‡à¦•à§‡ pickup date à¦¨à§‡à¦“à§Ÿà¦¾ à¦¹à§Ÿà¥¤..../api/car-availability/5?pickup_date=2026-09-20

    pickup_time = request.args.get("pickup_time", "").strip() or "10:00"

    duration = request.args.get("duration", "1").strip()

    try:
        duration_days = int(duration)

        if not 1 <= duration_days <= 30:
            raise ValueError

        pickup_at = datetime.strptime(f"{pickup_date} {pickup_time}", "%Y-%m-%d %H:%M")

    except ValueError:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "Enter a valid pickup date, time and duration.",
                }
            ),
            400,
        )  # 400 status code-à¦à¦° à¦…à¦°à§à¦¥ à¦¹à¦²à§‹ request-à¦ invalid input à¦†à¦›à§‡à¥¤

    return_at = pickup_at + timedelta(days=duration_days)

    if pickup_at <= datetime.now():
        return jsonify(
            {
                "ok": False,
                "available": False,
                "message": "Pickup must be in the future.",
            }
        )

    min_pickup, max_pickup = booking_window()

    if not min_pickup <= pickup_at.date() <= max_pickup:
        return jsonify(
            {
                "ok": False,
                "available": False,
                "message": f"Pickup must be between {min_pickup.isoformat()} and {max_pickup.isoformat()}.",
            }
        )

    car = query_db(
        "SELECT id, price_per_day FROM cars WHERE id=%s AND status='Available'",
        (car_id,),
        fetchone=True,
    )

    if not car:
        return jsonify({"ok": False, "available": False, "message": "Car unavailable."})

    available = car_is_available(car_id, pickup_at, return_at)

    total = Decimal(str(car["price_per_day"])) * duration_days

    return jsonify(
        {
            "ok": True,
            "available": available,
            "return_date": return_at.date().isoformat(),
            "return_datetime": return_at.strftime("%d %b %Y %H:%M"),
            "total_amount": float(total),
            "message": (
                "Car is available for this period."
                if available
                else "Car is already booked during that period."
            ),
        }
    )


# à¦à¦‡ à¦«à¦¾à¦‚à¦¶à¦¨à¦Ÿà¦¿ à¦¨à¦¿à¦°à§à¦¦à¦¿à¦·à§à¦Ÿ à¦à¦•à¦Ÿà¦¿ à¦—à¦¾à§œà¦¿à¦° à¦œà¦¨à§à¦¯ à¦¬à§à¦•à¦¿à¦‚ à¦«à¦°à§à¦® à¦¦à§‡à¦–à¦¾à§Ÿ à¦à¦¬à¦‚ à¦«à¦°à§à¦® à¦¸à¦¾à¦¬à¦®à¦¿à¦Ÿ à¦¹à¦²à§‡ à¦¬à§à¦•à¦¿à¦‚ à¦¤à§ˆà¦°à¦¿ à¦•à¦°à§‡à¥¤


@app.route("/book/<int:car_id>", methods=["GET", "POST"])
@user_required
def book(car_id):

    car = query_db(
        "SELECT * FROM cars WHERE id=%s AND status='Available'",
        (car_id,),
        fetchone=True,
    )

    if not car:
        flash("This car is currently unavailable.", "error")

        return redirect(url_for("cars"))

    min_pickup_date, max_pickup_date = booking_window()

    # Allow the cars page to carry its checked date/time into the booking form.

    # à¦—à¦¾à§œà¦¿à¦° à¦¤à¦¾à¦²à¦¿à¦•à¦¾ à¦ªà§‡à¦œ à¦¥à§‡à¦•à§‡ URL query parameter à¦¹à¦¿à¦¸à§‡à¦¬à§‡ à¦ªà¦¾à¦ à¦¾à¦¨à§‹ à¦¤à¦¾à¦°à¦¿à¦–, à¦¸à¦®à§Ÿ à¦à¦¬à¦‚ duration à¦¨à§‡à¦“à§Ÿà¦¾ à¦¹à§Ÿà¥¤

    prefill_pickup_date = request.args.get("pickup_date", "").strip()

    prefill_pickup_time = request.args.get("pickup_time", "").strip() or "10:00"

    prefill_duration = request.args.get("duration", "").strip() or "1"

    try:
        prefill_duration_days = int(prefill_duration)

        if not 1 <= prefill_duration_days <= 30:
            prefill_duration_days = 1

    except ValueError:
        prefill_duration_days = 1

    try:
        if prefill_pickup_date:
            datetime.strptime(
                f"{prefill_pickup_date} {prefill_pickup_time}", "%Y-%m-%d %H:%M"
            )  # à¦¤à¦¾à¦°à¦¿à¦– à¦“ à¦¸à¦®à§Ÿ à¦¸à¦ à¦¿à¦• format-à¦ à¦†à¦›à§‡ à¦•à¦¿à¦¨à¦¾ à¦ªà¦°à§€à¦•à§à¦·à¦¾ à¦•à¦°à¦¾ à¦¹à§Ÿ

        else:
            prefill_pickup_date = ""  # à¦­à§à¦² à¦¹à¦²à§‡ à¦¤à¦¾à¦°à¦¿à¦– à¦–à¦¾à¦²à¦¿ à¦•à¦°à§‡ à¦¦à§‡à¦“à§Ÿà¦¾ à¦¹à§Ÿà¥¤

    except ValueError:
        prefill_pickup_date = ""

    booking_context = {
        "min_pickup_date": min_pickup_date.isoformat(),
        "max_pickup_date": max_pickup_date.isoformat(),
        "prefill_pickup_date": prefill_pickup_date,
        "prefill_pickup_time": prefill_pickup_time,
        "prefill_duration": prefill_duration_days,
        "prefill_pickup_location": "",
        "prefill_return_location": "",
    }

    if request.method == "POST":
        pickup_date = request.form.get("pickup_date", "").strip()

        pickup_time = request.form.get("pickup_time", "").strip()

        pickup_location = (
            request.form.get("pickup_location", "").strip()
        )  # strip() à¦…à¦¤à¦¿à¦°à¦¿à¦•à§à¦¤ whitespace à¦¸à¦°à¦¿à§Ÿà§‡ à¦¦à§‡à§Ÿ

        return_location = request.form.get("return_location", "").strip()

        duration = request.form.get("duration", "").strip()
        booking_context.update(
            prefill_pickup_date=pickup_date,
            prefill_pickup_time=pickup_time,
            prefill_pickup_location=pickup_location,
            prefill_return_location=return_location,
        )
        try:
            booking_context["prefill_duration"] = int(duration)
        except ValueError:
            pass

        try:
            booking_date = datetime.strptime(
                f"{pickup_date} {pickup_time}", "%Y-%m-%d %H:%M"
            )

        except ValueError:
            flash("Please enter a valid booking date and time.", "error")

            return render_template("book.html", car=car, **booking_context)

        if booking_date <= datetime.now():
            flash("Booking must be for a future date and time.", "error")

            return render_template("book.html", car=car, **booking_context)

        if (
            not min_pickup_date <= booking_date.date() <= max_pickup_date
        ):  # à¦¬à§à¦•à¦¿à¦‚à§Ÿà§‡à¦° à¦¤à¦¾à¦°à¦¿à¦– à¦¬à¦°à§à¦¤à¦®à¦¾à¦¨ à¦¤à¦¾à¦°à¦¿à¦– à¦¥à§‡à¦•à§‡ à¦ªà¦°à¦¬à¦°à§à¦¤à§€ à¦¦à§à¦‡ à¦®à¦¾à¦¸à§‡à¦° à¦®à¦§à§à¦¯à§‡ à¦•à¦¿à¦¨à¦¾ à¦ªà¦°à§€à¦•à§à¦·à¦¾ à¦•à¦°à¦¾ à¦¹à§Ÿà¥¤
            flash(
                f"Pickup date must be between {min_pickup_date.strftime('%d %b %Y')} "
                f"and {max_pickup_date.strftime('%d %b %Y')} (current date to next 2 months).",
                "error",
            )

            return render_template("book.html", car=car, **booking_context)

        if not 2 <= len(pickup_location) <= 255:
            flash("Pickup location must be between 2 and 255 characters.", "error")

            return render_template("book.html", car=car, **booking_context)

        if not 2 <= len(return_location) <= 255:
            flash("Return location must be between 2 and 255 characters.", "error")

            return render_template("book.html", car=car, **booking_context)

        try:
            duration_days = int(duration)

            if not 1 <= duration_days <= 30:
                raise ValueError

        except ValueError:
            flash("Duration must be between 1 and 30 days.", "error")

            return render_template("book.html", car=car, **booking_context)

        booking_id, error = create_booking(
            session["user_id"],
            car_id,
            booking_date,
            pickup_location,
            return_location,
            duration_days,
        )  # create_booking() à¦«à¦¾à¦‚à¦¶à¦¨à§‡ à¦ªà¦¾à¦ à¦¾à¦¨à§‹ à¦¹à§Ÿ

        if error:
            flash(error, "error")

            return render_template("book.html", car=car, **booking_context)

        flash("Booking confirmed and invoice generated.", "success")

        return redirect(url_for("invoice", booking_id=booking_id))

    return render_template("book.html", car=car, **booking_context)


def get_booking(
    booking_id,
):  # à¦à¦‡ get_booking() à¦«à¦¾à¦‚à¦¶à¦¨à¦Ÿà¦¿ à¦¨à¦¿à¦°à§à¦¦à¦¿à¦·à§à¦Ÿ à¦à¦•à¦Ÿà¦¿ booking-à¦à¦° à¦¬à¦¿à¦¸à§à¦¤à¦¾à¦°à¦¿à¦¤ à¦¤à¦¥à§à¦¯ à¦¡à§‡à¦Ÿà¦¾à¦¬à§‡à¦¸ à¦¥à§‡à¦•à§‡ à¦¸à¦‚à¦—à§à¦°à¦¹ à¦•à¦°à§‡à¥¤

    return query_db(
        """SELECT b.*, u.name AS user_name, u.email, u.phone AS user_phone,

                  c.name AS car_name, c.brand, c.category, c.price_per_day

           FROM bookings b JOIN users u ON b.user_id=u.id JOIN cars c ON b.car_id=c.id

           WHERE b.id=%s""",
        (booking_id,),
        fetchone=True,
    )


# à¦à¦–à¦¾à¦¨à§‡:

# bookings à¦Ÿà§‡à¦¬à¦¿à¦²à¦•à§‡ b à¦¨à¦¾à¦®à§‡ à¦¸à¦‚à¦•à§à¦·à¦¿à¦ªà§à¦¤ à¦•à¦°à¦¾ à¦¹à§Ÿà§‡à¦›à§‡à¥¤

# users à¦Ÿà§‡à¦¬à¦¿à¦²à§‡à¦° à¦¸à¦™à§à¦—à§‡ b.user_id = u.id à¦¦à¦¿à§Ÿà§‡ à¦¸à¦®à§à¦ªà¦°à§à¦• à¦¤à§ˆà¦°à¦¿ à¦•à¦°à¦¾ à¦¹à§Ÿà§‡à¦›à§‡à¥¤

# cars à¦Ÿà§‡à¦¬à¦¿à¦²à§‡à¦° à¦¸à¦™à§à¦—à§‡ b.car_id = c.id à¦¦à¦¿à§Ÿà§‡ à¦¸à¦®à§à¦ªà¦°à§à¦• à¦¤à§ˆà¦°à¦¿ à¦•à¦°à¦¾ à¦¹à§Ÿà§‡à¦›à§‡à¥¤


# à¦…à¦°à§à¦¥à¦¾à§Ž, à¦à¦•à¦Ÿà¦¿ booking-à¦à¦° à¦¸à¦™à§à¦—à§‡ à¦¸à¦‚à¦¶à§à¦²à¦¿à¦·à§à¦Ÿ user à¦à¦¬à¦‚ car-à¦à¦° à¦¤à¦¥à§à¦¯ à¦à¦•à¦¸à¦™à§à¦—à§‡ à¦ªà¦¾à¦“à§Ÿà¦¾ à¦¯à¦¾à¦¬à§‡à¥¤


@app.route("/invoice/<int:booking_id>")
@user_required
def invoice(booking_id):

    booking = query_db(
        """SELECT b.*, u.name AS user_name, u.email, u.phone AS user_phone,

                  c.name AS car_name, c.brand, c.category, c.price_per_day

           FROM bookings b JOIN users u ON b.user_id=u.id JOIN cars c ON b.car_id=c.id

           WHERE b.id=%s AND b.user_id=%s""",
        (booking_id, session["user_id"]),
        fetchone=True,
    )

    if not booking:
        flash("Invoice not found.", "error")

        return redirect(url_for("cars"))

    return render_template("invoice.html", booking=booking, admin_view=False)


@app.route("/my-bookings")
@user_required
def my_bookings():

    status_filter = request.args.get("status", "All").strip()

    driver_filter = request.args.get("driver", "All").strip()

    search_query = request.args.get("q", "").strip()

    query = """SELECT b.*, c.name AS car_name, c.brand FROM bookings b JOIN cars c ON b.car_id=c.id

               WHERE b.user_id=%s"""

    params: list = [session["user_id"]]

    if status_filter in {"Confirmed", "Completed", "Cancelled"}:
        query += " AND b.booking_status=%s"

        params.append(status_filter)

    else:
        status_filter = "All"

    if driver_filter in {"Accepted", "Pending", "Rejected"}:
        query += " AND b.driver_request_status=%s"

        params.append(driver_filter)

    elif driver_filter == "NoDriver":
        query += " AND (b.driver_name IS NULL OR b.driver_request_status<>'Accepted')"

    else:
        driver_filter = "All"

    if search_query:
        query += " AND (b.invoice_no LIKE %s OR c.name LIKE %s OR c.brand LIKE %s)"

        like = f"%{search_query}%"

        params.extend([like, like, like])

    query += " ORDER BY b.created_at DESC"

    bookings = query_db(query, tuple(params))

    now = datetime.now()

    for booking in bookings:
        booking["is_overdue"] = is_overdue(booking, now)

    overdue_count = sum(1 for booking in bookings if booking["is_overdue"])

    return render_template(
        "my_bookings.html",
        bookings=bookings,
        status_filter=status_filter,
        driver_filter=driver_filter,
        search_query=search_query,
        overdue_count=overdue_count,
    )


@app.route("/cancel/<int:booking_id>", methods=["POST"])
@user_required
def cancel_booking(booking_id):

    booking = query_db(
        """SELECT * FROM bookings WHERE id=%s AND user_id=%s AND booking_status='Confirmed'""",
        (booking_id, session["user_id"]),
        fetchone=True,
    )

    if not booking:
        flash("Booking cannot be cancelled.", "error")

        return redirect(url_for("my_bookings"))

    pickup_dt = booking_start(booking)

    if pickup_dt - datetime.now() < timedelta(hours=24):
        flash(
            "Cancellation is allowed only before 24 hours of the pickup time.", "error"
        )

        return redirect(url_for("my_bookings"))

    query_db(
        "UPDATE bookings SET booking_status='Cancelled', payment_status='Refunded', driver_request_status='Rejected' WHERE id=%s",
        (booking_id,),
        commit=True,
    )

    flash(
        "Booking cancelled successfully. Refund status marked as Refunded.", "success"
    )

    return redirect(url_for("my_bookings"))


@app.route("/driver/login", methods=["GET", "POST"])
def driver_login():

    if request.method == "POST":
        phone = request.form["phone"].strip()

        password = request.form["password"]

        driver = query_db(
            "SELECT * FROM drivers WHERE phone=%s AND status='Active'",
            (phone,),
            fetchone=True,
            commit=False,
        )

        if not driver:
            flash("Invalid driver phone or password.", "error")

            return render_template("driver_login.html")

        password_valid, needs_upgrade = verify_password(driver["password"], password)

        if not password_valid:
            flash("Invalid driver phone or password.", "error")

            return render_template("driver_login.html")

        if needs_upgrade:
            query_db(
                "UPDATE drivers SET password=%s WHERE id=%s",
                (generate_password_hash(password), driver["id"]),
                commit=True,
            )

        session.clear()

        session["driver_id"] = driver["id"]

        session["driver_name"] = driver["name"]

        session["driver_phone"] = driver["phone"]

        return redirect(url_for("driver_dashboard"))

    return render_template("driver_login.html")


@app.route("/driver/dashboard")
@driver_required
def driver_dashboard():

    request_filter = request.args.get("status", "All").strip()

    base_query = """SELECT b.*, u.name AS user_name, u.phone AS user_phone,

                  c.name AS car_name, c.brand, c.category

           FROM bookings b JOIN users u ON b.user_id=u.id JOIN cars c ON b.car_id=c.id

           WHERE b.driver_id=%s AND b.payment_status='Paid'"""

    params: list = [session["driver_id"]]

    if request_filter in {"Pending", "Accepted", "Rejected"}:
        base_query += " AND b.driver_request_status=%s"

        params.append(request_filter)

    else:
        request_filter = "All"

    base_query += " ORDER BY b.created_at DESC"

    bookings = query_db(base_query, tuple(params))

    now = datetime.now()

    for booking in bookings:
        booking["is_overdue"] = is_overdue(booking, now)

    counts = {
        "All": query_db(
            "SELECT COUNT(*) AS n FROM bookings WHERE driver_id=%s AND payment_status='Paid'",
            (session["driver_id"],),
            fetchone=True,
        )["n"],
        "Pending": query_db(
            "SELECT COUNT(*) AS n FROM bookings WHERE driver_id=%s AND payment_status='Paid' AND driver_request_status='Pending'",
            (session["driver_id"],),
            fetchone=True,
        )["n"],
        "Accepted": query_db(
            "SELECT COUNT(*) AS n FROM bookings WHERE driver_id=%s AND payment_status='Paid' AND driver_request_status='Accepted'",
            (session["driver_id"],),
            fetchone=True,
        )["n"],
        "Rejected": query_db(
            "SELECT COUNT(*) AS n FROM bookings WHERE driver_id=%s AND payment_status='Paid' AND driver_request_status='Rejected'",
            (session["driver_id"],),
            fetchone=True,
        )["n"],
    }

    return render_template(
        "driver_dashboard.html",
        bookings=bookings,
        request_filter=request_filter,
        counts=counts,
    )


@app.route("/driver/respond/<int:booking_id>", methods=["POST"])
@driver_required
def driver_respond(booking_id):

    action = request.form.get("action")

    if action not in {"accept", "reject"}:
        flash("Invalid driver response.", "error")

        return redirect(url_for("driver_dashboard"))

    booking = query_db(
        """SELECT * FROM bookings WHERE id=%s AND driver_id=%s

           AND payment_status='Paid' AND driver_request_status='Pending'""",
        (booking_id, session["driver_id"]),
        fetchone=True,
    )

    if not booking:
        flash("This request is no longer available.", "error")

        return redirect(url_for("driver_dashboard"))

    if action == "accept":
        if not driver_is_available(session["driver_id"], booking):
            flash(
                "This booking overlaps with another confirmed ride assigned to you.",
                "error",
            )

            return redirect(url_for("driver_dashboard"))

        query_db(
            "UPDATE bookings SET driver_request_status='Accepted' WHERE id=%s",
            (booking_id,),
            commit=True,
        )

        flash("Ride request accepted.", "success")

    else:
        query_db(
            "UPDATE bookings SET driver_request_status='Rejected', driver_id=NULL, driver_name=NULL, driver_phone=NULL WHERE id=%s",
            (booking_id,),
            commit=True,
        )

        flash("Ride request rejected. The admin can assign another driver.", "warning")

    return redirect(url_for("driver_dashboard"))


@app.route("/driver/logout", methods=["POST"])
def driver_logout():

    session.clear()

    flash("Driver logged out.", "success")

    return redirect(url_for("index"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":
        username = request.form["username"].strip()

        password = request.form["password"]

        admin = query_db(
            "SELECT * FROM admins WHERE username=%s", (username,), fetchone=True
        )

        if not admin:
            flash("Invalid admin credentials.", "error")

            return render_template("admin_login.html")

        password_valid, needs_upgrade = verify_password(admin["password"], password)

        if not password_valid:
            flash("Invalid admin credentials.", "error")

            return render_template("admin_login.html")

        if needs_upgrade:
            query_db(
                "UPDATE admins SET password=%s WHERE id=%s",
                (generate_password_hash(password), admin["id"]),
                commit=True,
            )

        session.clear()

        session["admin_id"] = admin["id"]

        session["admin_name"] = admin["name"]

        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    booking_status = request.args.get("booking_status", "All").strip()

    driver_status = request.args.get("driver_status", "All").strip()

    admin_search = request.args.get("q", "").strip()

    stats = {
        "users": query_db("SELECT COUNT(*) AS n FROM users", fetchone=True)["n"],
        "cars": query_db("SELECT COUNT(*) AS n FROM cars", fetchone=True)["n"],
        "bookings": query_db("SELECT COUNT(*) AS n FROM bookings", fetchone=True)["n"],
        "revenue": query_db(
            "SELECT COALESCE(SUM(total_amount),0) AS total FROM bookings WHERE payment_status='Paid' AND booking_status <> 'Cancelled'",
            fetchone=True,
        )["total"],
        "pending_drivers": query_db(
            "SELECT COUNT(*) AS n FROM bookings WHERE booking_status='Confirmed' AND driver_request_status='Pending'",
            fetchone=True,
        )["n"],
        "accepted_drivers": query_db(
            "SELECT COUNT(*) AS n FROM bookings WHERE booking_status='Confirmed' AND driver_request_status='Accepted'",
            fetchone=True,
        )["n"],
        "overdue": 0,
    }

    booking_query = """SELECT b.*, u.name AS user_name, u.phone AS user_phone, c.name AS car_name, c.brand

                       FROM bookings b JOIN users u ON b.user_id=u.id JOIN cars c ON b.car_id=c.id

                       WHERE 1=1"""

    booking_params: list = []

    if booking_status in {"Confirmed", "Completed", "Cancelled"}:
        booking_query += " AND b.booking_status=%s"

        booking_params.append(booking_status)

    else:
        booking_status = "All"

    if driver_status in {"Pending", "Accepted", "Rejected"}:
        booking_query += " AND b.driver_request_status=%s"

        booking_params.append(driver_status)

    elif driver_status == "NoDriver":
        booking_query += (
            " AND (b.driver_name IS NULL OR b.driver_request_status<>'Accepted')"
        )

    else:
        driver_status = "All"

    if admin_search:
        booking_query += " AND (b.invoice_no LIKE %s OR u.name LIKE %s OR u.phone LIKE %s OR c.name LIKE %s OR c.brand LIKE %s)"

        like = f"%{admin_search}%"

        booking_params.extend([like, like, like, like, like])

    booking_query += " ORDER BY b.created_at DESC"

    bookings = query_db(booking_query, tuple(booking_params))

    now = datetime.now()

    for booking in bookings:
        booking["is_overdue"] = is_overdue(booking, now)

    stats["overdue"] = sum(1 for booking in bookings if booking["is_overdue"])

    cars_list = query_db("SELECT * FROM cars ORDER BY id DESC")

    users = query_db(
        "SELECT id,name,email,phone,created_at FROM users ORDER BY id DESC"
    )

    drivers = query_db("SELECT id, name, phone, status FROM drivers ORDER BY name")

    active_drivers = [driver for driver in drivers if driver["status"] == "Active"]

    available_drivers_by_booking = {
        booking["id"]: available_drivers_for_booking(booking, active_drivers)
        for booking in bookings
    }

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        bookings=bookings,
        cars=cars_list,
        users=users,
        drivers=drivers,
        available_drivers_by_booking=available_drivers_by_booking,
        booking_status=booking_status,
        driver_status=driver_status,
        admin_search=admin_search,
    )


@app.route("/admin/add-driver", methods=["POST"])
@admin_required
def add_driver():

    name = request.form.get("name", "").strip()

    phone = request.form.get("phone", "").strip()

    password = request.form.get("password", "")

    if not 2 <= len(name) <= 100 or not PHONE_PATTERN.fullmatch(phone):
        flash("Enter a valid driver name and 10-digit Indian phone number.", "error")

        return redirect(url_for("admin_dashboard"))

    if len(password) < 8:
        flash("Driver password must contain at least 8 characters.", "error")

        return redirect(url_for("admin_dashboard"))

    if query_db("SELECT id FROM drivers WHERE phone=%s", (phone,), fetchone=True):
        flash("That driver phone number is already registered.", "error")

        return redirect(url_for("admin_dashboard"))

    query_db(
        "INSERT INTO drivers (name, phone, password, status) VALUES (%s,%s,%s,'Active')",
        (name, phone, generate_password_hash(password)),
        commit=True,
    )

    flash(f"Driver {name} added successfully.", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/toggle-driver/<int:driver_id>", methods=["POST"])
@admin_required
def toggle_driver(driver_id):

    driver = query_db(
        "SELECT id, status, name FROM drivers WHERE id=%s", (driver_id,), fetchone=True
    )

    if not driver:
        flash("Driver not found.", "error")

        return redirect(url_for("admin_dashboard"))

    new_status = "Inactive" if driver["status"] == "Active" else "Active"

    query_db(
        "UPDATE drivers SET status=%s WHERE id=%s", (new_status, driver_id), commit=True
    )

    flash(f"Driver {driver['name']} marked {new_status}.", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/invoice/<int:booking_id>")
@admin_required
def admin_invoice(booking_id):

    booking = get_booking(booking_id)

    if not booking:
        flash("Invoice not found.", "error")

        return redirect(url_for("admin_dashboard"))

    return render_template("invoice.html", booking=booking, admin_view=True)


@app.route("/admin/assign-driver/<int:booking_id>", methods=["POST"])
@admin_required
def assign_driver(booking_id):

    driver_id = request.form.get("driver_id", "").strip()

    if not driver_id.isdigit():
        flash("Please select a driver.", "error")

        return redirect(url_for("admin_dashboard"))

    selected = query_db(
        "SELECT id, name, phone FROM drivers WHERE id=%s AND status='Active'",
        (int(driver_id),),
        fetchone=True,
    )

    if not selected:
        flash("Invalid driver selection.", "error")

        return redirect(url_for("admin_dashboard"))

    booking = query_db(
        "SELECT * FROM bookings WHERE id=%s", (booking_id,), fetchone=True
    )

    if not booking:
        flash("Booking not found.", "error")

        return redirect(url_for("admin_dashboard"))

    if booking["booking_status"] != "Confirmed":
        flash("Drivers can only be assigned to confirmed bookings.", "error")

        return redirect(url_for("admin_dashboard"))

    if not driver_is_available(selected["id"], booking):
        flash("That driver has an overlapping confirmed booking.", "error")

        return redirect(url_for("admin_dashboard"))

    query_db(
        "UPDATE bookings SET driver_id=%s, driver_name=%s, driver_phone=%s, driver_request_status='Pending' WHERE id=%s",
        (selected["id"], selected["name"], selected["phone"], booking_id),
        commit=True,
    )

    flash(f"{selected['name']} has been assigned to the booking.", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/auto-assign-driver/<int:booking_id>", methods=["POST"])
@admin_required
def auto_assign_driver(booking_id):

    booking = query_db(
        "SELECT * FROM bookings WHERE id=%s", (booking_id,), fetchone=True
    )

    if not booking:
        flash("Booking not found.", "error")

        return redirect(url_for("admin_dashboard"))

    if booking["booking_status"] != "Confirmed":
        flash("Drivers can only be assigned to confirmed bookings.", "error")

        return redirect(url_for("admin_dashboard"))

    available = available_drivers_for_booking(booking)

    if not available:
        flash("No driver is free for this booking's time period.", "error")

        return redirect(url_for("admin_dashboard"))

    selected = random.choice(available)

    query_db(
        "UPDATE bookings SET driver_id=%s, driver_name=%s, driver_phone=%s, driver_request_status='Pending' WHERE id=%s",
        (selected["id"], selected["name"], selected["phone"], booking_id),
        commit=True,
    )

    flash(f"Driver automatically assigned: {selected['name']}.", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/update-status/<int:booking_id>", methods=["POST"])
@admin_required
def update_status(booking_id):

    status = request.form["status"]

    if status not in {"Confirmed", "Completed", "Cancelled"}:
        flash("Invalid booking status.", "error")

        return redirect(url_for("admin_dashboard"))

    query_db(
        "UPDATE bookings SET booking_status=%s WHERE id=%s",
        (status, booking_id),
        commit=True,
    )

    flash("Booking status updated.", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/add-car", methods=["POST"])
@admin_required
def add_car():

    name = request.form["name"].strip()

    brand = request.form["brand"].strip()

    category = request.form["category"].strip()

    seats = request.form["seats"]

    price = request.form["price"]

    image_url = request.form["image_url"].strip()

    if not (
        1 <= len(name) <= 100 and 1 <= len(brand) <= 80 and category in CAR_CATEGORIES
    ):
        flash("Enter a valid car name, brand, and category.", "error")

        return redirect(url_for("admin_dashboard"))

    try:
        seats = int(seats)

        price = Decimal(price)

        if (
            not 2 <= seats <= 12
            or not price.is_finite()
            or not Decimal("1") <= price <= Decimal("1000000")
        ):
            raise ValueError

    except (ValueError, ArithmeticError):
        flash(
            "Seats must be between 2 and 12, and price must be a valid positive amount.",
            "error",
        )

        return redirect(url_for("admin_dashboard"))

    if image_url:
        image = urlparse(image_url)

        if (
            image.scheme not in {"http", "https"}
            or not image.netloc
            or len(image_url) > 2048
        ):
            flash("Car image URL must be a valid HTTP or HTTPS URL.", "error")

            return redirect(url_for("admin_dashboard"))

    query_db(
        """INSERT INTO cars (name,brand,category,seats,price_per_day,image_url,status)

                 VALUES (%s,%s,%s,%s,%s,%s,'Available')""",
        (name, brand, category, seats, price, image_url),
        commit=True,
    )

    flash("Car added successfully.", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/toggle-car/<int:car_id>", methods=["POST"])
@admin_required
def toggle_car(car_id):

    car = query_db("SELECT status FROM cars WHERE id=%s", (car_id,), fetchone=True)

    if not car:
        flash("Car not found.", "error")

        return redirect(url_for("admin_dashboard"))

    new_status = "Unavailable" if car["status"] == "Available" else "Available"

    query_db("UPDATE cars SET status=%s WHERE id=%s", (new_status, car_id), commit=True)

    flash("Car availability updated.", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout", methods=["POST"])
def admin_logout():

    session.clear()

    flash("Admin logged out.", "success")

    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="127.0.0.1", port=port, debug=os.environ.get("FLASK_ENV") == "development"
    )
