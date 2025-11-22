import sqlite3
import os
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-this-in-production'
app.config['DATABASE'] = 'hospital.db'

# --- Database Helpers ---

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row  # Access columns by name
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with tables and seed data."""
    with app.app_context():
        db = get_db()
        
        # Create Patients Table
        db.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')

        # Create Doctors Table
        db.execute('''
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialty TEXT NOT NULL
            )
        ''')

        # Create Appointments Table
        db.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                doctor_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            )
        ''')

        # Seed Doctors if empty
        cur = db.execute('SELECT COUNT(*) FROM doctors')
        if cur.fetchone()[0] == 0:
            doctors = [
                ('Sarah Jenkins', 'Cardiology'),
                ('Michael Chen', 'Pediatrics'),
                ('Emily Rodriguez', 'Dermatology'),
                ('James Wilson', 'Orthopedics'),
                ('Priya Patel', 'General Practice')
            ]
            db.executemany('INSERT INTO doctors (name, specialty) VALUES (?, ?)', doctors)
            db.commit()
            print("Database initialized and seeded with doctors.")
        else:
            print("Database already exists.")

# --- Decorators ---

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM patients WHERE id = ?', (user_id,)).fetchone()

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        error = None

        if not first_name or not last_name or not email or not password:
            error = 'All fields are required.'
        
        if error is None:
            try:
                hashed_pw = generate_password_hash(password)
                db.execute(
                    'INSERT INTO patients (first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?)',
                    (first_name, last_name, email, hashed_pw)
                )
                db.commit()
            except sqlite3.IntegrityError:
                error = f"User {email} is already registered."
            else:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))

        flash(error, 'error')

    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        error = None
        
        user = db.execute('SELECT * FROM patients WHERE email = ?', (email,)).fetchone()

        if user is None:
            error = 'Incorrect email.'
        elif not check_password_hash(user['password_hash'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['first_name']
            flash(f"Welcome back, {user['first_name']}!", 'success')
            return redirect(url_for('index'))

        flash(error, 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/book', methods=('GET', 'POST'))
@login_required
def book_appointment():
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        appt_date = request.form['date']
        appt_time = request.form['time']
        notes = request.form['notes']
        error = None

        if not doctor_id or not appt_date or not appt_time:
            error = 'Doctor, date, and time are required.'

        if error is None:
            db = get_db()
            db.execute(
                'INSERT INTO appointments (patient_id, doctor_id, date, time, notes) VALUES (?, ?, ?, ?, ?)',
                (g.user['id'], doctor_id, appt_date, appt_time, notes)
            )
            db.commit()
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('my_appointments'))
        
        flash(error, 'error')

    # GET request: fetch doctors for dropdown
    db = get_db()
    doctors = db.execute('SELECT * FROM doctors').fetchall()
    today_str = date.today().isoformat()
    return render_template('book_appointment.html', doctors=doctors, today=today_str)

@app.route('/my-appointments')
@login_required
def my_appointments():
    db = get_db()
    appointments = db.execute('''
        SELECT a.date, a.time, a.notes, d.name as doctor_name, d.specialty 
        FROM appointments a 
        JOIN doctors d ON a.doctor_id = d.id 
        WHERE a.patient_id = ? 
        ORDER BY a.date, a.time
    ''', (g.user['id'],)).fetchall()
    
    return render_template('my_appointments.html', appointments=appointments)

# Initialize DB if run directly
if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    app.run(debug=True)

