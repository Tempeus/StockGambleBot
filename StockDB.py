import sqlite3
import datetime

# Connect to the SQLite database (or create it)
conn = sqlite3.connect('investments.db')

# Create a cursor object to execute SQL commands
c = conn.cursor()

# Create a table to store investments
def setup_db():
    c.execute('''CREATE TABLE IF NOT EXISTS investments (
                    user_id TEXT,
                    stock_ticker TEXT,
                    quantity REAL,
                    price REAL,
                    date TEXT
                )''')
    conn.commit()

# Add an investment to the database
def add_investment(user_id, stock_ticker, quantity, price):
    c.execute('''INSERT INTO investments (user_id, stock_ticker, quantity, price, date)
                 VALUES (?, ?, ?, ?, DATETIME('now'))''',
                 (user_id, stock_ticker, quantity, price))
    conn.commit()

# Get all investments for a specific user
def get_investments(user_id):
    c.execute('SELECT stock_ticker, quantity, price FROM investments WHERE user_id = ?', (user_id,))
    return c.fetchall()

# Close the database connection
def close_db():
    conn.close()
