import sqlite3
import datetime
import yfinance as yf
import StockBot
import pandas as pd

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
        self.c.execute('''CREATE TABLE IF NOT EXISTS historical_data (
                            user_id TEXT,
                            stock_ticker TEXT,
                            date TEXT,
                            gain_loss REAL
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

    def store_historical_data(self, yahoo_api_client):
        """Store historical gains or losses for each user's stocks."""
        investments = self.get_all_investments()
        for user_id, stock_ticker, quantity, purchase_price in investments:
            # Fetch the current stock price using the Yahoo API client
            current_price = StockBot.get_stock_price(stock_ticker)  # Assume this method exists
            
            # Calculate the gain or loss
            gain_loss = (current_price - purchase_price) * quantity
            
            # Insert the data into the historical_data table
            self.c.execute('''INSERT INTO historical_data (user_id, stock_ticker, date, gain_loss)
                              VALUES (?, ?, DATETIME('now'), ?)''',
                           (user_id, stock_ticker, gain_loss))
        self.conn.commit()

    def get_historical_data(self, user_id, stock_ticker=None):
        """Retrieve historical data for a specific user and optionally a specific stock."""
        if stock_ticker:
            self.c.execute('''SELECT date, gain_loss FROM historical_data
                              WHERE user_id = ? AND stock_ticker = ?''', (user_id, stock_ticker))
        else:
            self.c.execute('''SELECT stock_ticker, date, gain_loss FROM historical_data
                              WHERE user_id = ?''', (user_id,))
        return self.c.fetchall()
    
    def export_historical_data_to_excel(self, file_name='historical_data.xlsx'):
        """Export all historical data to an Excel sheet."""
        # Fetch all historical data
        self.c.execute('SELECT user_id, stock_ticker, date, gain_loss FROM historical_data')
        data = self.c.fetchall()

        # Define column names
        columns = ['User ID', 'Stock Ticker', 'Date', 'Gain/Loss']

        # Create a pandas DataFrame
        df = pd.DataFrame(data, columns=columns)

        # Export to an Excel file
        df.to_excel(file_name, index=False)
        print(f"Historical data successfully exported to {file_name}")

    def close(self):
        """Close the connection to the database."""
        self.conn.close()
