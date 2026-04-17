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
from werkzeug.security import generate_password_hash

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
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create the 'users' table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create the 'cash_records' table with foreign key to staff
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER,
            record_date DATE NOT NULL,
            amount_in REAL DEFAULT 0.00,
            amount_out REAL DEFAULT 0.00,
            expense_type TEXT DEFAULT 'shared',
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES staff(id)
        )
    ''')

    # Create the 'transaction_splits' table for ledger architecture
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_splits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            staff_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES cash_records(id) ON DELETE CASCADE,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
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

    # --- Insert default Admin user ---
    # Username: admin, Password: admin123
    admin_password_hash = generate_password_hash('admin123')
    cursor.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        ('admin', admin_password_hash, 'admin')
    )

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
        # (staff_id, record_date, amount_in, amount_out, expense_type, note)
        (1, (today - timedelta(days=30)).strftime('%Y-%m-%d'), 500.00, 0.00, 'shared', 'Monthly office contribution'),
        (2, (today - timedelta(days=25)).strftime('%Y-%m-%d'), 300.00, 0.00, 'shared', 'Weekly collection'),
        (3, (today - timedelta(days=20)).strftime('%Y-%m-%d'), 0.00, 150.00, 'shared', 'Office supplies purchase'),
        (4, (today - timedelta(days=15)).strftime('%Y-%m-%d'), 200.00, 0.00, 'shared', 'Event fund contribution'),
        (5, (today - timedelta(days=10)).strftime('%Y-%m-%d'), 0.00, 80.00, 'shared', 'Printing costs'),
        (1, (today - timedelta(days=7)).strftime('%Y-%m-%d'), 0.00, 200.00, 'shared', 'Stationery reimbursement'),
        (2, (today - timedelta(days=3)).strftime('%Y-%m-%d'), 150.00, 0.00, 'shared', 'Extra contribution'),
        (3, today.strftime('%Y-%m-%d'), 400.00, 0.00, 'shared', 'Monthly office contribution'),
        (1, today.strftime('%Y-%m-%d'), 0.00, 150.00, 'personal', 'Partial refund requested'),
    ]
    # Note: Because seed_data has shared expenses, we must calculate their splits right here!
    # Instead of complex logic here, we'll just insert them and let app.py handle new ones,
    # but for seeding, we'll run a quick script to generate splits.
    
    # 1. Insert records first
    cursor.executemany(
        "INSERT INTO cash_records (staff_id, record_date, amount_in, amount_out, expense_type, note) VALUES (?, ?, ?, ?, ?, ?)",
        sample_records
    )

    # 2. Generate initial splits based on final totals (acceptable for seed data)
    # Calculate total in for everyone
    cursor.execute("SELECT id, SUM(amount_in) as total_in FROM cash_records GROUP BY staff_id")
    staff_totals = cursor.fetchall()
    active_total_in = sum(row['total_in'] for row in staff_totals)
    
    # Get all shared expenses
    cursor.execute("SELECT id, amount_out FROM cash_records WHERE expense_type = 'shared' AND amount_out > 0")
    shared_expenses = cursor.fetchall()
    
    for expense in shared_expenses:
        for s in staff_totals:
            if active_total_in > 0:
                split_amount = expense['amount_out'] * (s['total_in'] / active_total_in)
                cursor.execute(
                    "INSERT INTO transaction_splits (transaction_id, staff_id, amount) VALUES (?, ?, ?)",
                    (expense['id'], s['id'], split_amount)
                )

    conn.commit()
    conn.close()
    print("[DB] Sample data and splits seeded successfully.")
