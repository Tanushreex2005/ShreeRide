import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set to initialize PostgreSQL.")

schema_path = Path(__file__).with_name("database_postgres.sql")
schema_sql = schema_path.read_text(encoding="utf-8")
connection = psycopg2.connect(DATABASE_URL.replace("postgres://", "postgresql://", 1))
try:
    with connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.users')")
            if cursor.fetchone()[0] is None:
                cursor.execute(schema_sql)
                print("PostgreSQL schema and seed data initialized.")
            else:
                print("PostgreSQL schema already exists; initialization skipped.")
finally:
    connection.close()
