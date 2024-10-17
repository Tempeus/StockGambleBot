import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import datetime
import yfinance as yf
from StockDB import StockDB

# Define your intents
intents = discord.Intents.default()
intents.members = False  # Disable typing events, if needed
intents.presences = False  # Disable presence events, if needed
intents.message_content = True    # Enable message content updates (required for commands)

# environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHAN_NAME = 'test_invest'

client = discord.Client(intents=discord.Intents.default())

# Initialize the bot with the intents
bot = commands.Bot(command_prefix='$', intents=intents)
db = StockDB()

# Helper function to get stock price
def get_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")['Close'][0]
        return price
    except Exception as e:
        print(f"Error fetching stock price: {e}")
        return None

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
    investments = db.get_investments(user_id)
    total_gain_loss = 0
    result = []
    for stock, quantity, invested_price in investments:
        current_price = get_stock_price(stock)
        if current_price is not None:
            gain_loss = (current_price - invested_price) * quantity
            total_gain_loss += gain_loss
    return total_gain_loss

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    monthly_update.start()

# Command to add a new stock investment
@bot.command()
async def invest(ctx, ticker: str, quantity: float, price: float):
    """Add a new investment in a stock."""
    ticker = ticker.upper()
    user_id = str(ctx.author.id)
    db.add_investment(user_id, ticker, quantity, price)
    await ctx.send(f"Added investment: {quantity} shares of {ticker} at {price} USD.")

@bot.command(name='delete_investment')
async def delete_investment(ctx, stock_name: str):
    # Fetch the user ID from the context
    user_id = ctx.author.id

    # Check if the investment exists for the user in the database
    investment = db.get_investment(user_id, stock_name)
    
    if investment:
        # If investment exists, delete it
        db.delete_investment(user_id, stock_name)
        await ctx.send(f"Investment in {stock_name} has been deleted successfully.")
    else:
        # If investment doesn't exist, notify the user
        await ctx.send(f"No investment found for {stock_name}. Please check the stock name and try again.")


# Command to check the user's current gains/losses
@bot.command()
async def portfolio(ctx):
    """Check your portfolio's gain/loss."""
    user_id = str(ctx.author.id)
    total_gain_loss = calculate_gain_loss(user_id)
    await ctx.send(f"Your portfolio gain/loss: {'+' if total_gain_loss >= 0 else ''}{total_gain_loss:.2f} USD")

# Leaderboard command to display all users' gains/losses sorted
@bot.command(name='leaderboard')
async def leaderboard(ctx):
    # Retrieve all investments from the database
    investments = db.get_all_investments()
    user_gains_losses = {}

    # Calculate percentage gains/losses for each user
    for user_id, stock, quantity, price in investments:
        current_price = get_stock_price(stock)
        if current_price is not None:
            # Calculate percentage gain/loss
            percentage_gain_loss = ((current_price - price) / price) * 100
            if user_id in user_gains_losses:
                user_gains_losses[user_id] += percentage_gain_loss
            else:
                user_gains_losses[user_id] = percentage_gain_loss

    # Sort users by percentage gains/losses
    sorted_leaderboard = sorted(user_gains_losses.items(), key=lambda x: x[1], reverse=True)

    # Create the leaderboard message
    leaderboard_message = "**Leaderboard (Percentage Gains/Losses):**\n"
    for rank, (user_id, percentage_gain_loss) in enumerate(sorted_leaderboard, start=1):
        user = await bot.fetch_user(int(user_id))  # Fetch user name
        leaderboard_message += f"{rank}. {user.name}: {percentage_gain_loss:.2f}%\n"

    # Send the leaderboard message in the channel where the command was invoked
    await ctx.send(leaderboard_message)

# A task that checks daily and posts leaderboard on the last day of the month
@tasks.loop(hours=24)  # Check once per day
async def monthly_update():
    # Get today's date
    today = datetime.date.today()

    # Check if today is the last day of the month
    tomorrow = today + datetime.timedelta(days=1)
    
    if tomorrow.day == 1:
        # It's the last day of the month, so send the leaderboard
        for guild in bot.guilds:
            # Find the 'silenced-people' channel in the guild
            channel = discord.utils.get(guild.channels, name=CHAN_NAME)
            if channel is not None:
                # Retrieve all investments from the database
                investments = db.get_all_investments()
                user_gains_losses = {}

                # Calculate percentage gains/losses for each user
                for user_id, stock, quantity, price in investments:
                    current_price = get_stock_price(stock)
                    if current_price is not None:
                        # Calculate percentage gain/loss
                        percentage_gain_loss = ((current_price - price) / price) * 100
                        if user_id in user_gains_losses:
                            user_gains_losses[user_id] += percentage_gain_loss
                        else:
                            user_gains_losses[user_id] = percentage_gain_loss

                # Sort users by percentage gains/losses
                sorted_leaderboard = sorted(user_gains_losses.items(), key=lambda x: x[1], reverse=True)

                # Create the leaderboard message
                leaderboard_message = "**Monthly Leaderboard (Percentage Gains/Losses):**\n"
                for rank, (user_id, percentage_gain_loss) in enumerate(sorted_leaderboard, start=1):
                    user = await bot.fetch_user(int(user_id))  # Fetch user name
                    leaderboard_message += f"{rank}. {user.name}: {percentage_gain_loss:.2f}%\n"

                # Send leaderboard message to the 'silenced-people' channel
                await channel.send(leaderboard_message)
            else:
                print(f"{CHAN_NAME} channel not found in guild {guild.name}")


'''
ARMAGEDON CODE. THIS SHIT WILL SEND A MESSAGE TO EVERYONE ON THE SERVER
for guild in bot.guilds:
    for member in guild.members:
        if not member.bot:  # Don't send updates to bots
            user_id = str(member.id)
            result = calculate_gain_loss(user_id)
            if result:
                try:
                    await member.send(f"My bad, i'm a bot and my circuits malfunctioned. ignore the previous message")
                except discord.Forbidden:
                    print(f"Couldn't send a message to {member.name}")
'''

# Start the bot
bot.run(TOKEN)