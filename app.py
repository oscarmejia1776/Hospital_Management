import mysql.connector
import os
from datetime import date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-this-in-production')
# Database configuration
app.config['DB_HOST'] = os.getenv('DB_HOST', 'localhost')
app.config['DB_USER'] = os.getenv('DB_USER', 'root')
app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD', '')
app.config['DB_NAME'] = os.getenv('DB_NAME', 'hospital_db')

# --- Database Helpers ---

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=app.config['DB_HOST'],
            user=app.config['DB_USER'],
            password=app.config['DB_PASSWORD'],
            database=app.config['DB_NAME']
        )
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
        cursor = db.cursor()
        
        # Create Patients Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(255) NOT NULL,
                last_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL
            )
        ''')

        # Create Doctors Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doctors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                specialty VARCHAR(255) NOT NULL
            )
        ''')

        # Create Appointments Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                doctor_id INT NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            )
        ''')

        # Seed Doctors if empty
        cursor.execute('SELECT COUNT(*) FROM doctors')
        if cursor.fetchone()[0] == 0:
            doctors = [
                ('Sarah Jenkins', 'Cardiology'),
                ('Michael Chen', 'Pediatrics'),
                ('Emily Rodriguez', 'Dermatology'),
                ('James Wilson', 'Orthopedics'),
                ('Priya Patel', 'General Practice')
            ]
            cursor.executemany('INSERT INTO doctors (name, specialty) VALUES (%s, %s)', doctors)
            db.commit()
            print("Database initialized and seeded with doctors.")
        else:
            print("Database already exists.")
        
        cursor.close()

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
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM patients WHERE id = %s', (user_id,))
        g.user = cursor.fetchone()
        cursor.close()

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
        cursor = db.cursor()
        error = None

        if not first_name or not last_name or not email or not password:
            error = 'All fields are required.'
        
        if error is None:
            try:
                hashed_pw = generate_password_hash(password)
                cursor.execute(
                    'INSERT INTO patients (first_name, last_name, email, password_hash) VALUES (%s, %s, %s, %s)',
                    (first_name, last_name, email, hashed_pw)
                )
                db.commit()
            except mysql.connector.IntegrityError:
                error = f"User {email} is already registered."
            else:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            finally:
                cursor.close()

        flash(error, 'error')

    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor(dictionary=True)
        error = None
        
        cursor.execute('SELECT * FROM patients WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()

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
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO appointments (patient_id, doctor_id, date, time, notes) VALUES (%s, %s, %s, %s, %s)',
                (g.user['id'], doctor_id, appt_date, appt_time, notes)
            )
            db.commit()
            cursor.close()
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('my_appointments'))
        
        flash(error, 'error')

    # GET request: fetch doctors for dropdown
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT * FROM doctors')
    doctors = cursor.fetchall()
    cursor.close()
    today_str = date.today().isoformat()
    return render_template('book_appointment.html', doctors=doctors, today=today_str)

@app.route('/my-appointments')
@login_required
def my_appointments():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute('''
        SELECT a.id, a.date, a.time, a.notes, d.name as doctor_name, d.specialty 
        FROM appointments a 
        JOIN doctors d ON a.doctor_id = d.id 
        WHERE a.patient_id = %s 
        ORDER BY a.date, a.time
    ''', (g.user['id'],))
    appointments = cursor.fetchall()
    cursor.close()
    
    return render_template('my_appointments.html', appointments=appointments)

@app.route('/edit-appointment/<int:id>', methods=('GET', 'POST'))
@login_required
def edit_appointment(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Verify appointment exists and belongs to user
    cursor.execute('SELECT * FROM appointments WHERE id = %s AND patient_id = %s', (id, g.user['id']))
    appointment = cursor.fetchone()
    
    if appointment is None:
        cursor.close()
        flash('Appointment not found or access denied.', 'error')
        return redirect(url_for('my_appointments'))

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        appt_date = request.form['date']
        appt_time = request.form['time']
        notes = request.form['notes']
        error = None

        if not doctor_id or not appt_date or not appt_time:
            error = 'Doctor, date, and time are required.'

        if error is None:
            cursor.execute(
                'UPDATE appointments SET doctor_id = %s, date = %s, time = %s, notes = %s WHERE id = %s',
                (doctor_id, appt_date, appt_time, notes, id)
            )
            db.commit()
            cursor.close()
            flash('Appointment updated successfully!', 'success')
            return redirect(url_for('my_appointments'))
        
        flash(error, 'error')

    # GET request: fetch doctors for dropdown
    cursor.execute('SELECT * FROM doctors')
    doctors = cursor.fetchall()
    cursor.close()
    
    # Handle time formatting if it's a timedelta (MySQL connector returns timedelta for TIME columns)
    if isinstance(appointment['time'], timedelta):
        total_seconds = int(appointment['time'].total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        appointment['time'] = f"{hours:02}:{minutes:02}"

    return render_template('edit_appointment.html', appointment=appointment, doctors=doctors)

@app.route('/delete-appointment/<int:id>', methods=('POST',))
@login_required
def delete_appointment(id):
    db = get_db()
    cursor = db.cursor()
    
    # Verify appointment exists and belongs to user (safe delete)
    cursor.execute('DELETE FROM appointments WHERE id = %s AND patient_id = %s', (id, g.user['id']))
    db.commit()
    
    if cursor.rowcount == 0:
        flash('Appointment not found or access denied.', 'error')
    else:
        flash('Appointment deleted successfully.', 'success')
        
    cursor.close()
    return redirect(url_for('my_appointments'))

# Initialize DB if run directly
if __name__ == '__main__':
    # Just try to init db every time, it handles "IF NOT EXISTS"
    try:
        init_db()
    except Exception as e:
        print(f"Database init error (ensure MySQL is running): {e}")
    app.run(debug=True, port=5000)
