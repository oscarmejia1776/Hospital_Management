# Hospital Management System

A simple Flask-based appointment booking system for a small hospital.

## Features

- **Patient Registration & Login:** Secure account creation with password hashing.
- **Appointment Booking:** Patients can book appointments with doctors.
- **Doctor Selection:** Dynamic dropdown of available doctors and specialties.
- **Dashboard:** View upcoming appointments.
- **Session Management:** Secure login sessions.

## Prerequisites

- Python 3.x
- pip (Python package installer)

## Installation & Setup

1.  **Clone or Download the project** to your local machine.

2.  **Create a Virtual Environment** (Recommended):
    It's best practice to run Python projects in a virtual environment to isolate dependencies.

    ```bash
    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    With the virtual environment activated, install the required packages from `requirements.txt`:

    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

1.  **Initialize the Database:**
    The application is designed to automatically initialize the SQLite database (`hospital.db`) and seed it with example doctors the first time you run it.

2.  **Start the Server:**
    Run the main application file:

    ```bash
    python app.py
    ```

    You should see output indicating the server is running, usually at `http://127.0.0.1:5000`.

3.  **Access the App:**
    Open your web browser and go to:
    [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Usage Guide

1.  **Register:** Click "Register" to create a new patient account.
2.  **Login:** Use your email and password to log in.
3.  **Book:** Click "Book Appointment" to choose a doctor, date, and time.
4.  **View:** Check "My Appointments" to see your scheduled visits.
5.  **Logout:** Click "Logout" to end your session.

## Project Structure

- `app.py`: Main application logic and routes.
- `templates/`: HTML files for the user interface.
- `static/`: CSS styles.
- `hospital.db`: SQLite database file (created automatically).

