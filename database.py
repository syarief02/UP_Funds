"""
database.py - Database Helper Module
=====================================
This file handles all SQLite database operations:
- Creating/connecting to the database
- Initializing tables (staff, cash_records)
- Seeding sample data for testing
- Providing a reusable connection function

The database file (office_money.db) is stored in the project root folder.
"""

import sqlite3
import os
from datetime import datetime, date, timedelta

# Path to the SQLite database file (in the same folder as this script)
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'office_money.db')


def get_db_connection():
    """
    Create and return a database connection.
    - row_factory = sqlite3.Row makes rows behave like dictionaries
      so you can access columns by name (e.g., row['name'])
    - Foreign keys are enabled for data integrity
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key support
    return conn


def init_db():
    """
    Initialize the database by creating tables if they don't exist.
    This runs automatically when the app starts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create the 'staff' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create the 'cash_records' table with foreign key to staff
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            record_date DATE NOT NULL,
            amount_in REAL DEFAULT 0.00,
            amount_out REAL DEFAULT 0.00,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES staff(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")


def seed_data():
    """
    Insert sample data for testing purposes.
    Only seeds if the staff table is empty (first run).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if data already exists
    count = cursor.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
    if count > 0:
        conn.close()
        print("[DB] Data already exists. Skipping seed.")
        return

    # --- Insert sample staff members ---
    sample_staff = [
        ('Ahmad Razif',),
        ('Nurul Aisyah',),
        ('Muhammad Hafiz',),
        ('Siti Aminah',),
        ('Farah Diana',),
    ]
    cursor.executemany("INSERT INTO staff (name) VALUES (?)", sample_staff)

    # --- Insert sample cash records spread across recent dates ---
    today = date.today()
    sample_records = [
        # (staff_id, record_date, amount_in, amount_out, note)
        (1, (today - timedelta(days=30)).strftime('%Y-%m-%d'), 500.00, 0.00, 'Monthly office contribution'),
        (2, (today - timedelta(days=25)).strftime('%Y-%m-%d'), 300.00, 0.00, 'Weekly collection'),
        (3, (today - timedelta(days=20)).strftime('%Y-%m-%d'), 0.00, 150.00, 'Office supplies purchase'),
        (4, (today - timedelta(days=15)).strftime('%Y-%m-%d'), 200.00, 0.00, 'Event fund contribution'),
        (5, (today - timedelta(days=10)).strftime('%Y-%m-%d'), 0.00, 80.00, 'Printing costs'),
        (1, (today - timedelta(days=7)).strftime('%Y-%m-%d'), 0.00, 200.00, 'Stationery reimbursement'),
        (2, (today - timedelta(days=3)).strftime('%Y-%m-%d'), 150.00, 0.00, 'Extra contribution'),
        (3, today.strftime('%Y-%m-%d'), 400.00, 0.00, 'Monthly office contribution'),
    ]
    cursor.executemany(
        "INSERT INTO cash_records (staff_id, record_date, amount_in, amount_out, note) VALUES (?, ?, ?, ?, ?)",
        sample_records
    )

    conn.commit()
    conn.close()
    print("[DB] Sample data seeded successfully.")
