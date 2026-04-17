"""
app.py - Main Flask Application
================================
This is the main entry point for the Office Money Collection app.
It defines all the routes (URLs) for:
- Dashboard (homepage)
- Add/Edit/Delete Transactions
- Transactions List with filters
- Staff Contribution Summary
- Staff Management (CRUD)
- CSV Export

Run this file to start the web server:
    python app.py
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, Response, session
)
from database import get_db_connection, init_db, seed_data
from datetime import date, datetime
import csv
import io
from functools import wraps
from werkzeug.security import check_password_hash

# Create the Flask app
app = Flask(__name__)
app.secret_key = 'up-funds-secret-key-2026'  # Required for flash messages


# Make current datetime and user role available in all templates
@app.context_processor
def inject_now():
    """Inject current datetime and admin status into every template."""
    is_admin = session.get('role') == 'admin'
    return {'now': datetime.now(), 'is_admin': is_admin}

# --- Authentication Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access is required to view this page.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# AUTHENTICATION
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    if session.get('role') == 'admin':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            
            # Redirect back to where they came from, or dashboard
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout the user."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('dashboard'))


# ============================================================
# DASHBOARD - Homepage with summary cards
# ============================================================
@app.route('/')
def dashboard():
    """Show the dashboard with summary statistics."""
    conn = get_db_connection()

    # Get totals for summary cards
    totals = conn.execute('''
        SELECT
            COALESCE(SUM(amount_in), 0) as total_in,
            COALESCE(SUM(amount_out), 0) as total_out
        FROM cash_records
    ''').fetchone()

    # Count total staff
    staff_count = conn.execute('SELECT COUNT(*) as count FROM staff').fetchone()['count']

    # Count total transactions
    transaction_count = conn.execute('SELECT COUNT(*) as count FROM cash_records').fetchone()['count']

    # Get recent transactions (last 5)
    recent = conn.execute('''
        SELECT cr.*, s.name as staff_name
        FROM cash_records cr
        JOIN staff s ON cr.staff_id = s.id
        ORDER BY cr.record_date DESC, cr.id DESC
        LIMIT 5
    ''').fetchall()

    # Monthly summary for current year
    monthly = conn.execute('''
        SELECT
            strftime('%Y-%m', record_date) as month,
            SUM(amount_in) as total_in,
            SUM(amount_out) as total_out
        FROM cash_records
        WHERE strftime('%Y', record_date) = strftime('%Y', 'now')
        GROUP BY strftime('%Y-%m', record_date)
        ORDER BY month DESC
    ''').fetchall()

    conn.close()

    return render_template('dashboard.html',
                           total_in=totals['total_in'],
                           total_out=totals['total_out'],
                           balance=totals['total_in'] - totals['total_out'],
                           staff_count=staff_count,
                           transaction_count=transaction_count,
                           recent=recent,
                           monthly=monthly)


# ============================================================
# TRANSACTIONS - List, Add, Edit, Delete
# ============================================================
@app.route('/transactions')
def transactions():
    """Show all transactions with filters and search."""
    conn = get_db_connection()

    # Get filter parameters from URL query string
    staff_filter = request.args.get('staff', '')
    date_filter = request.args.get('date', '')
    month_filter = request.args.get('month', '')
    search_query = request.args.get('search', '')

    # Build dynamic query with filters
    query = '''
        SELECT cr.*, s.name as staff_name
        FROM cash_records cr
        JOIN staff s ON cr.staff_id = s.id
        WHERE 1=1
    '''
    params = []

    if staff_filter:
        query += ' AND cr.staff_id = ?'
        params.append(staff_filter)

    if date_filter:
        query += ' AND cr.record_date = ?'
        params.append(date_filter)

    if month_filter:
        query += " AND strftime('%Y-%m', cr.record_date) = ?"
        params.append(month_filter)

    if search_query:
        query += ' AND (s.name LIKE ? OR cr.note LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%'])

    query += ' ORDER BY cr.record_date DESC, cr.id DESC'

    records = conn.execute(query, params).fetchall()

    # Get staff list for the filter dropdown
    staff_list = conn.execute('SELECT * FROM staff ORDER BY name').fetchall()

    # Get distinct months for the month filter
    months = conn.execute('''
        SELECT DISTINCT strftime('%Y-%m', record_date) as month
        FROM cash_records
        ORDER BY month DESC
    ''').fetchall()

    conn.close()

    return render_template('transactions.html',
                           records=records,
                           staff_list=staff_list,
                           months=months,
                           staff_filter=staff_filter,
                           date_filter=date_filter,
                           month_filter=month_filter,
                           search_query=search_query)


@app.route('/transactions/add', methods=['GET', 'POST'])
@admin_required
def add_transaction():
    """Show the add transaction form and handle form submission."""
    conn = get_db_connection()
    staff_list = conn.execute('SELECT * FROM staff WHERE is_active = 1 ORDER BY name').fetchall()

    if request.method == 'POST':
        # Get form data
        staff_id = request.form.get('staff_id', '').strip()
        record_date = request.form.get('record_date', '').strip()
        amount_in = request.form.get('amount_in', '').strip()
        amount_out = request.form.get('amount_out', '').strip()
        expense_type = request.form.get('expense_type', 'shared').strip()
        note = request.form.get('note', '').strip()

        # --- Validation ---
        errors = []

        if not staff_id:
            errors.append('Staff name is required.')

        if not record_date:
            errors.append('Date is required.')

        # Convert amounts (empty = 0)
        try:
            amount_in = float(amount_in) if amount_in else 0.0
        except ValueError:
            errors.append('Amount In must be a valid number.')
            amount_in = 0.0

        try:
            amount_out = float(amount_out) if amount_out else 0.0
        except ValueError:
            errors.append('Amount Out must be a valid number.')
            amount_out = 0.0

        if amount_in < 0:
            errors.append('Amount In cannot be negative.')
        if amount_out < 0:
            errors.append('Amount Out cannot be negative.')

        if amount_in == 0 and amount_out == 0:
            errors.append('Either Amount In or Amount Out must be greater than 0.')

        if amount_in > 0 and amount_out > 0:
            errors.append('Amount In and Amount Out cannot both be greater than 0 for the same entry.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            conn.close()
            return render_template('add_transaction.html',
                                   staff_list=staff_list,
                                   today=date.today().strftime('%Y-%m-%d'))

        # Insert the transaction
        conn.execute('''
            INSERT INTO cash_records (staff_id, record_date, amount_in, amount_out, expense_type, note)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (staff_id, record_date, amount_in, amount_out, expense_type, note))
        conn.commit()
        conn.close()

        flash('Transaction added successfully!', 'success')
        return redirect(url_for('transactions'))

    conn.close()
    return render_template('add_transaction.html',
                           staff_list=staff_list,
                           today=date.today().strftime('%Y-%m-%d'))


@app.route('/transactions/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_transaction(id):
    """Edit an existing transaction."""
    conn = get_db_connection()

    # Get the transaction to edit
    record = conn.execute('SELECT * FROM cash_records WHERE id = ?', (id,)).fetchone()
    if not record:
        conn.close()
        flash('Transaction not found.', 'danger')
        return redirect(url_for('transactions'))

    staff_list = conn.execute('SELECT * FROM staff ORDER BY name').fetchall()

    if request.method == 'POST':
        # Get form data
        staff_id = request.form.get('staff_id', '').strip()
        record_date = request.form.get('record_date', '').strip()
        amount_in = request.form.get('amount_in', '').strip()
        amount_out = request.form.get('amount_out', '').strip()
        expense_type = request.form.get('expense_type', 'shared').strip()
        note = request.form.get('note', '').strip()

        # --- Validation ---
        errors = []

        if not staff_id:
            errors.append('Staff name is required.')

        if not record_date:
            errors.append('Date is required.')

        try:
            amount_in = float(amount_in) if amount_in else 0.0
        except ValueError:
            errors.append('Amount In must be a valid number.')
            amount_in = 0.0

        try:
            amount_out = float(amount_out) if amount_out else 0.0
        except ValueError:
            errors.append('Amount Out must be a valid number.')
            amount_out = 0.0

        if amount_in < 0:
            errors.append('Amount In cannot be negative.')
        if amount_out < 0:
            errors.append('Amount Out cannot be negative.')

        if amount_in == 0 and amount_out == 0:
            errors.append('Either Amount In or Amount Out must be greater than 0.')

        if amount_in > 0 and amount_out > 0:
            errors.append('Amount In and Amount Out cannot both be greater than 0 for the same entry.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            conn.close()
            return render_template('edit_transaction.html',
                                   record=record,
                                   staff_list=staff_list)

        # Update the transaction
        conn.execute('''
            UPDATE cash_records
            SET staff_id = ?, record_date = ?, amount_in = ?, amount_out = ?, expense_type = ?, note = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (staff_id, record_date, amount_in, amount_out, expense_type, note, id))
        conn.commit()
        conn.close()

        flash('Transaction updated successfully!', 'success')
        return redirect(url_for('transactions'))

    conn.close()
    return render_template('edit_transaction.html',
                           record=record,
                           staff_list=staff_list)


@app.route('/transactions/delete/<int:id>', methods=['POST'])
@admin_required
def delete_transaction(id):
    """Delete a transaction."""
    conn = get_db_connection()
    conn.execute('DELETE FROM cash_records WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Transaction deleted successfully.', 'success')
    return redirect(url_for('transactions'))


# ============================================================
# STAFF SUMMARY - Contribution summary grouped by staff
# ============================================================
@app.route('/summary')
def staff_summary():
    """Show staff contribution summary."""
    conn = get_db_connection()

    search_query = request.args.get('search', '')

    # Calculate global grand totals first
    global_totals = conn.execute('''
        SELECT 
            COALESCE(SUM(amount_in), 0) as total_in,
            COALESCE(SUM(CASE WHEN expense_type = 'shared' THEN amount_out ELSE 0 END), 0) as total_shared_out,
            COALESCE(SUM(CASE WHEN expense_type = 'personal' THEN amount_out ELSE 0 END), 0) as total_refunds
        FROM cash_records
    ''').fetchone()
    grand_total_in = global_totals['total_in']
    grand_total_out = global_totals['total_shared_out']  # Shared expenses only
    grand_total_refunds = global_totals['total_refunds']
    grand_balance = grand_total_in - grand_total_out - grand_total_refunds

    # calculate active_total_in for proportional shared expenses
    active_total_in = conn.execute('''
        SELECT COALESCE(SUM(cr.amount_in), 0) as active_total_in
        FROM cash_records cr
        JOIN staff s ON cr.staff_id = s.id
        WHERE s.is_active = 1
    ''').fetchone()['active_total_in']

    query = '''
        SELECT
            s.id,
            s.name,
            COALESCE(SUM(cr.amount_in), 0) as total_in,
            COALESCE(SUM(CASE WHEN cr.expense_type = 'personal' THEN cr.amount_out ELSE 0 END), 0) as personal_refunds,
            COUNT(CASE WHEN cr.amount_in > 0 THEN cr.id END) as transaction_count
        FROM staff s
        LEFT JOIN cash_records cr ON s.id = cr.staff_id
        WHERE s.is_active = 1
    '''
    params = []

    if search_query:
        query += ' WHERE s.name LIKE ?'
        params.append(f'%{search_query}%')

    query += ' GROUP BY s.id, s.name ORDER BY s.name'

    summary_raw = conn.execute(query, params).fetchall()

    # Build the final summary list with shared expenses and personal refunds
    summary = []
    for row in summary_raw:
        # Calculate shared expense based on contribution percentage from ACTIVE members
        contribution_percentage = row['total_in'] / active_total_in if active_total_in > 0 else 0
        shared_expense = grand_total_out * contribution_percentage

        summary.append({
            'name': row['name'],
            'transaction_count': row['transaction_count'],
            'total_in': row['total_in'],
            'personal_refunds': row['personal_refunds'],
            'shared_expense': shared_expense,
            'net_balance': row['total_in'] - shared_expense - row['personal_refunds']
        })

    conn.close()

    return render_template('summary.html',
                           summary=summary,
                           grand_total_in=grand_total_in,
                           grand_total_out=grand_total_out,
                           grand_total_refunds=grand_total_refunds,
                           grand_balance=grand_balance,
                           search_query=search_query)


# ============================================================
# STAFF MANAGEMENT - CRUD for staff
# ============================================================
@app.route('/staff')
@admin_required
def staff_list():
    """Show all staff members."""
    conn = get_db_connection()

    # Get staff with their transaction counts
    staff = conn.execute('''
        SELECT s.*, COUNT(cr.id) as transaction_count
        FROM staff s
        LEFT JOIN cash_records cr ON s.id = cr.staff_id
        WHERE s.is_active = 1
        GROUP BY s.id
        ORDER BY s.name
    ''').fetchall()

    conn.close()
    return render_template('staff.html', staff=staff)


@app.route('/staff/add', methods=['POST'])
@admin_required
def add_staff():
    """Add a new staff member."""
    name = request.form.get('name', '').strip()

    if not name:
        flash('Staff name is required.', 'danger')
        return redirect(url_for('staff_list'))

    conn = get_db_connection()

    # Check if name already exists
    existing = conn.execute('SELECT id FROM staff WHERE LOWER(name) = LOWER(?)', (name,)).fetchone()
    if existing:
        conn.close()
        flash(f'Staff "{name}" already exists.', 'warning')
        return redirect(url_for('staff_list'))

    conn.execute('INSERT INTO staff (name) VALUES (?)', (name,))
    conn.commit()
    conn.close()

    flash(f'Staff "{name}" added successfully!', 'success')
    return redirect(url_for('staff_list'))


@app.route('/staff/add-ajax', methods=['POST'])
@admin_required
def add_staff_ajax():
    """
    Add a new staff member via AJAX (from the transaction form).
    Returns JSON so JavaScript can update the dropdown without page reload.
    """
    data = request.get_json()
    name = data.get('name', '').strip() if data else ''

    if not name:
        return jsonify({'success': False, 'message': 'Staff name is required.'}), 400

    conn = get_db_connection()

    # Check if name already exists
    existing = conn.execute('SELECT id FROM staff WHERE LOWER(name) = LOWER(?)', (name,)).fetchone()
    if existing:
        conn.close()
        return jsonify({
            'success': True,
            'message': f'Staff "{name}" already exists.',
            'staff': {'id': existing['id'], 'name': name}
        })

    cursor = conn.execute('INSERT INTO staff (name) VALUES (?)', (name,))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f'Staff "{name}" added successfully!',
        'staff': {'id': new_id, 'name': name}
    })


@app.route('/staff/edit/<int:id>', methods=['POST'])
@admin_required
def edit_staff(id):
    """Edit a staff member's name."""
    name = request.form.get('name', '').strip()

    if not name:
        flash('Staff name is required.', 'danger')
        return redirect(url_for('staff_list'))

    conn = get_db_connection()

    # Check if name already exists for a different staff member
    existing = conn.execute(
        'SELECT id FROM staff WHERE LOWER(name) = LOWER(?) AND id != ?',
        (name, id)
    ).fetchone()
    if existing:
        conn.close()
        flash(f'Staff name "{name}" is already taken.', 'warning')
        return redirect(url_for('staff_list'))

    conn.execute('UPDATE staff SET name = ? WHERE id = ?', (name, id))
    conn.commit()
    conn.close()

    flash(f'Staff updated to "{name}" successfully!', 'success')
    return redirect(url_for('staff_list'))


@app.route('/staff/delete/<int:id>', methods=['POST'])
@admin_required
def delete_staff(id):
    """Delete a staff member (Soft delete)."""
    conn = get_db_connection()

    global_totals = conn.execute('''
        SELECT 
            COALESCE(SUM(CASE WHEN expense_type = 'shared' THEN amount_out ELSE 0 END), 0) as total_shared_out
        FROM cash_records
    ''').fetchone()
    grand_total_out = global_totals['total_shared_out']

    active_total_in = conn.execute('''
        SELECT COALESCE(SUM(cr.amount_in), 0) as active_total_in
        FROM cash_records cr
        JOIN staff s ON cr.staff_id = s.id
        WHERE s.is_active = 1
    ''').fetchone()['active_total_in']

    staff_totals = conn.execute('''
        SELECT 
            COALESCE(SUM(amount_in), 0) as total_in,
            COALESCE(SUM(CASE WHEN expense_type = 'personal' THEN amount_out ELSE 0 END), 0) as personal_refunds
        FROM cash_records
        WHERE staff_id = ?
    ''', (id,)).fetchone()

    their_shared_expense = grand_total_out * (staff_totals['total_in'] / active_total_in) if active_total_in > 0 else 0
    their_net_balance = staff_totals['total_in'] - their_shared_expense - staff_totals['personal_refunds']

    if abs(their_net_balance) > 0.01:
        conn.close()
        flash(f'Cannot delete staff. Their balance must be exactly RM 0.00 first (Current: RM {their_net_balance:.2f}).', 'danger')
        return redirect(url_for('staff_list'))

    conn.execute('UPDATE staff SET is_active = 0 WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Staff deleted successfully.', 'success')
    return redirect(url_for('staff_list'))


# ============================================================
# CSV EXPORT
# ============================================================
@app.route('/export/csv')
def export_csv():
    """Export all transactions as a CSV file."""
    conn = get_db_connection()

    records = conn.execute('''
        SELECT cr.id, s.name as staff_name, cr.record_date,
               cr.amount_in, cr.amount_out, cr.expense_type, cr.note
        FROM cash_records cr
        JOIN staff s ON cr.staff_id = s.id
        ORDER BY cr.record_date DESC, cr.id DESC
    ''').fetchall()

    conn.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow(['ID', 'Staff Name', 'Date', 'Amount In (RM)', 'Amount Out (RM)', 'Expense Type', 'Note'])

    # Write data rows
    for record in records:
        writer.writerow([
            record['id'],
            record['staff_name'],
            record['record_date'],
            f"{record['amount_in']:.2f}",
            f"{record['amount_out']:.2f}",
            record['expense_type'],
            record['note']
        ])

    # Create the response with CSV content
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=transactions_{date.today().strftime("%Y%m%d")}.csv'
        }
    )


# ============================================================
# RUN THE APP
# ============================================================
if __name__ == '__main__':
    # Initialize database tables and seed sample data
    init_db()
    seed_data()

    # Start the Flask development server
    print("\n========================================")
    print("  UP Funds - Office Money Collection")
    print("  Open: http://127.0.0.1:5000")
    print("========================================\n")
    app.run(debug=True, port=5000)
