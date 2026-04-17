# UP Funds - Office Money Collection System

UP Funds is a local-first, lightweight web application built with Python (Flask) and SQLite. It is designed to manage and track pooled office funds, individual contributions, and shared laboratory expenses.

## 🚀 Getting Started

The easiest way to run the application is to double-click the `start.bat` file. 

1. Double-click `start.bat`.
2. A terminal window will open to start the server.
3. Your default web browser will automatically open to the dashboard at `http://127.0.0.2:5001`.

*Note: If it's your first time running the app, it will automatically create the `office_money.db` database file and seed it with some initial sample data.*

## 🌟 Key Features

- **Dashboard:** At-a-glance view of total funds in, total funds out, net balance, and recent transaction history.
- **Transaction Management:** Easily log money coming in (contributions) and money going out (shared lab expenses or personal refunds).
- **Proportional Sharing:** Shared expenses are automatically split among active staff based on their contribution percentage. Staff who contribute more absorb a larger share of the expenses.
- **External Lab Expenses:** You can log shared expenses without assigning them to a specific staff member (e.g., direct payments to vendors).
- **Staff Lifecycle Management:** Safely add, edit, or remove staff members. Removed staff members are "soft deleted" to preserve historical accounting.
- **Returning Members:** If an old staff member returns, adding their name creates a fresh profile. They start with a RM 0 contribution, ensuring they don't unfairly absorb historical expenses until they begin contributing again.
- **CSV Export:** One-click export of all transactions to Excel/CSV for external bookkeeping.

## 🧠 The "Ledger" Architecture

The mathematical foundation of this app uses a **Ledger System** (`transaction_splits` table) to prevent "Ghost Balances". 

When a shared expense is recorded, the system calculates everyone's proportional share *at that exact moment* and permanently locks it into the database. 
- If someone joins the lab later, they are not retroactively charged for past expenses.
- If someone leaves, the remaining active staff do not suddenly absorb their past expenses.
- This ensures the Grand Totals always perfectly match the sum of the individual staff balances.

## 🛠️ Tech Stack

- **Backend:** Python 3, Flask
- **Database:** SQLite3 (Local file `office_money.db`)
- **Frontend:** HTML5, Bootstrap 5 (CSS/JS), Vanilla JavaScript
- **Icons:** Bootstrap Icons

## 🔒 Security Note

This application is designed to be run **locally** on a single office machine or within a secure, trusted local network. It comes with a basic admin login (default username: `admin`, password: `admin123`). This login gate prevents unauthorized modifications but is not intended for high-security public deployment.
