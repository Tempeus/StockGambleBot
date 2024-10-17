import sqlite3
import datetime

class StockDB:
    def __init__(self, db_name='investments.db'):
        # Initialize the connection to the database
        self.conn = sqlite3.connect(db_name)
        self.c = self.conn.cursor()
        self.setup_db()

    def setup_db(self):
        """Create the investments table if it doesn't exist."""
        self.c.execute('''CREATE TABLE IF NOT EXISTS investments (
                            user_id TEXT,
                            stock_ticker TEXT,
                            quantity REAL,
                            price REAL,
                            date TEXT
                        )''')
        self.conn.commit()

    def add_investment(self, user_id, stock_ticker, quantity, price):
        """Add a new investment to the database."""
        self.c.execute('''INSERT INTO investments (user_id, stock_ticker, quantity, price, date)
                          VALUES (?, ?, ?, ?, DATETIME('now'))''',
                          (user_id, stock_ticker, quantity, price))
        self.conn.commit()

    def get_investment(self, user_id, stock_ticker):
        self.c.execute("SELECT * FROM investments WHERE user_id = ? AND stock_ticker = ?", (user_id, stock_ticker))
        return self.c.fetchone()

    def delete_investment(self, user_id, stock_ticker):
        self.c.execute("DELETE FROM investments WHERE user_id = ? AND stock_ticker = ?", (user_id, stock_ticker))
        self.conn.commit()

    def get_investments(self, user_id):
        """Retrieve all investments for a specific user."""
        self.c.execute('SELECT stock_ticker, quantity, price FROM investments WHERE user_id = ?', (user_id,))
        return self.c.fetchall()
    
    def get_all_investments(self):
        """Retrieve all investments for all users."""
        self.c.execute('SELECT user_id, stock_ticker, quantity, price FROM investments')
        return self.c.fetchall()

    def get_all_users(self):
        """Fetch all unique users from the investments table."""
        self.c.execute('SELECT DISTINCT user_id FROM investments')
        return self.c.fetchall()

    def close(self):
        """Close the connection to the database."""
        self.conn.close()
