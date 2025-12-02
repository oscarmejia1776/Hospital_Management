import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'hospital_db')
)
cursor = conn.cursor()
cursor.execute("SELECT time FROM appointments LIMIT 1")
row = cursor.fetchone()
if row:
    print(f"Type: {type(row[0])}")
    print(f"Value: {row[0]}")
else:
    print("No appointments")
conn.close()

