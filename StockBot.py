import os
import discord
from dotenv import load_dotenv
import datetime
import yfinance as yf
from StockDB import setup_db, add_investment, get_investments

TOKEN = 'YOUR_DISCORD_BOT_TOKEN'

client = discord.Client(intents=discord.Intents.default())

# Set up the database when the bot starts
setup_db()

# Helper function to get stock price
def get_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")['Close'][0]
        return price
    except Exception as e:
        print(f"Error fetching stock price: {e}")
        return None

# Helper function to calculate the gain/loss for a user
def calculate_gain_loss(user_id):
    investments = get_investments(user_id)
    result = []
    for stock, quantity, invested_price in investments:
        current_price = get_stock_price(stock)
        if current_price is not None:
            gain_loss = (current_price - invested_price) * quantity
            result.append(f"{stock}: {'+' if gain_loss >= 0 else ''}{gain_loss:.2f} USD")
    return "\n".join(result) if result else "No valid stock data."

# Bot event for when it's ready
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

# Bot event for new messages
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Command to add a new stock investment
    if message.content.startswith('!invest'):
        try:
            _, ticker, quantity, price = message.content.split()
            ticker = ticker.upper()
            quantity = float(quantity)
            price = float(price)
            user_id = str(message.author.id)

            # Add investment to the database
            add_investment(user_id, ticker, quantity, price)

            await message.channel.send(f"Added investment: {quantity} shares of {ticker} at {price} USD.")
        except ValueError:
            await message.channel.send("Usage: !invest [STOCK_TICKER] [QUANTITY] [PRICE]")

    # Command to check the user's current gains/losses
    elif message.content.startswith('!portfolio'):
        user_id = str(message.author.id)
        result = calculate_gain_loss(user_id)
        await message.channel.send(f"Your portfolio update:\n{result}")

# Monthly check task (triggered manually for simplicity)
@client.event
async def on_message(message):
    if message.content.startswith('!monthly_update'):
        for user_id, user in message.guild.members.items():
            result = calculate_gain_loss(user_id)
            await user.send(f"Monthly update on your portfolio:\n{result}")

client.run(TOKEN)
