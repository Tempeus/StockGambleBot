import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import datetime
import yfinance as yf
from StockDB import StockDB

# Troll APIs
import inspirobot

# Define your intents
intents = discord.Intents.default()
intents.members = False  # Disable typing events, if needed
intents.presences = False  # Disable presence events, if needed
intents.message_content = True    # Enable message content updates (required for commands)

# environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHAN_NAME = os.getenv('CHAN')

client = discord.Client(intents=discord.Intents.default())

# Initialize the bot with the intents
bot = commands.Bot(command_prefix='$', intents=intents, help_command=None)
db = StockDB()

# Helper function to check if ticker exists
def ticker_exists(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Check if valid data can be retrieved for the ticker
        if stock.info:
            price = stock.history(period="1d")['Close'][0]
            return price is not None and price > 0
        else:
            return False
    except Exception as e:
        return False

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

# Helper function to generate leaderboard message
async def generate_leaderboard_message(title):
    # Retrieve all users' investments
    user_investments = db.get_all_investments()  # This method should return all user investments
    user_stats = {}

    for user_id, stock_name, quantity, purchase_price in user_investments:
        if user_id not in user_stats:
            user_stats[user_id] = {'total_invested': 0, 'total_quantity': 0, 'total_gain': 0, 'stocks': []}

        total_invested = quantity * purchase_price
        user_stats[user_id]['total_invested'] += total_invested
        user_stats[user_id]['total_quantity'] += quantity
        user_stats[user_id]['stocks'].append(stock_name)

        current_price = get_stock_price(stock_name)
        if current_price is not None:
            gain = (current_price - purchase_price) * quantity
            user_stats[user_id]['total_gain'] += gain

    # Prepare leaderboard message
    leaderboard_message = f"**{title}**\n"
    leaderboard_data = []

    for user_id, stats in user_stats.items():
        if stats['total_quantity'] > 0 and stats['total_invested'] > 0:
            average_gain_percentage = (stats['total_gain'] / stats['total_invested']) * 100
            leaderboard_data.append((user_id, average_gain_percentage, stats['stocks']))

    # Sort by gain percentage
    leaderboard_data.sort(key=lambda x: x[1], reverse=True)

    # Format the leaderboard message
    for rank, (user_id, gain_percentage, stocks) in enumerate(leaderboard_data, start=1):
        user = await bot.fetch_user(int(user_id))
        leaderboard_message += f"{rank}. **{user}**: {gain_percentage:.2f}% - "
        for stock in stocks:
            leaderboard_message += f" {stock} "
        leaderboard_message += '\n'

    if not leaderboard_data:
        leaderboard_message = "No investments found for any users."

    return leaderboard_message

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    weekly_leaderboard.start()

# Command to add a new stock investment
@bot.command(name='invest')
async def invest(ctx, stock_name: str, current_price = None):
    """
    Invest $20 into a stock.

    Usage: $invest <stock_name> [purchase price]

    If no purchase price is provided, the bot will use the latest price from Yahoo Finance
    """
    if current_price is not None:
        try:
            current_price = float(current_price)
            if current_price <= 0:
                await ctx.send(f"Please put a valid price.")
                return
        except ValueError:
            await ctx.send(f"Please provide a valid numerical price for {stock_name}.")
            return
    
    if ticker_exists(stock_name):
        if current_price is None:
            try:
                current_price = get_stock_price(stock_name)
            except Exception as e:
                await ctx.send(f"Stock {stock_name} does not exist. Please try again.")
                return
            
        if current_price is None:
            await ctx.send(f"Stock {stock_name} does not exist. Please try again.")
            return

        # Calculate the number of fractional shares
        fractional_shares = 20 / current_price

        # Save the investment to the database (or update existing entry)
        db.add_investment(user_id=ctx.author.id, stock_ticker=stock_name, quantity=fractional_shares, price=current_price)

        await ctx.send(f"Successfully invested ${20} into {stock_name} at ${current_price:.2f} per share. You now own {fractional_shares:.6f} shares.")
    else:
        await ctx.send(f"Stock {stock_name} does not exist. Please try again.")

@bot.command(name='remove')
async def delete_investment(ctx, stock_name: str):
    """
    Removes the stock from your portfolio

    Usage: $remove <stock_name>
    """
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
@bot.command(name='portfolio')
async def portfolio(ctx):
    """
    Shows a summary of all your investments, including the ticker name, invested amount, and gain percentage.

    Usage: $portfolio
    """
     
    # Fetch the user ID from the context
    user_id = ctx.author.id

    # Retrieve all investments for the user
    investments = db.get_investments(user_id)
    
    if not investments:
        await ctx.send("You have no investments in your portfolio.")
        return

    # Aggregate investments
    aggregated_investments = {}
    for stock_name, quantity, purchase_price in investments:
        if stock_name not in aggregated_investments:
            aggregated_investments[stock_name] = {'total_quantity': 0, 'total_invested': 0}
        
        aggregated_investments[stock_name]['total_quantity'] += quantity
        aggregated_investments[stock_name]['total_invested'] += quantity * purchase_price

    # Prepare the portfolio message
    portfolio_message = "**Your Investment Portfolio:**\n"

    for stock_name, data in aggregated_investments.items():
        total_quantity = data['total_quantity']
        total_invested = data['total_invested']
        average_price = total_invested / total_quantity
        
        current_price = get_stock_price(stock_name)
        
        if current_price is None:
            await ctx.send(f"Could not retrieve current price for {stock_name}.")
            continue

        # Calculate gain percentage based on average price
        gain_percentage = ((current_price - average_price) / average_price) * 100
        
        # Format the investment details
        portfolio_message += (
            f"**Ticker:** {stock_name}\n"
            f"**Total Quantity:** {total_quantity:.3f}\n"
            f"**Average Invested Price:** ${average_price:.2f}\n"
            f"**Current Price:** ${current_price:.2f}\n"
            f"**Average Gain Percentage:** {gain_percentage:.2f}%\n"
            "---------------------------\n"
        )

    # Send the portfolio message in the channel
    await ctx.send(portfolio_message)


# Leaderboard command to display all users' gains/losses sorted
@bot.command(name='leaderboard')
async def leaderboard(ctx):
    """
    Show a leaderboard of all users ranked by gain percentage from investments.

    Usage: $leaderboard
    """
    leaderboard_message = await generate_leaderboard_message("Leaderboard")
    await ctx.send(leaderboard_message)


# Custom help command
@bot.command(name='help')
async def help_command(ctx, command_name: str = None):
    """
    Custom help command to display available commands and their usage.
    """
    if command_name is None:
        # Display a list of commands
        help_message = "**Help Menu**\n\n"
        help_message += "`$invest` - Invest in a stock.\n"
        help_message += "`$leaderboard` - Show a leaderboard of users sorted by gain percentage.\n"
        help_message += "`$portfolio` - Display your portfolio with all investments.\n"
        help_message += "`$remove` - Delete an investment from your portfolio.\n"
        help_message += "\nFor more details on a specific command, use `$help <command>`."
        await ctx.send(help_message)
    else:
        # Provide detailed help for a specific command
        command = bot.get_command(command_name)
        if command:
            await ctx.send(f"**Help for `{command_name}`**\n\n{command.help}")
        else:
            await ctx.send(f"Command `{command_name}` not found.")


# Task that checks hourly and posts the weekly leaderboard every Saturday at 9 PM
@tasks.loop(hours=1)  # Check every hour
async def weekly_leaderboard():
    # Get the current time in the system's local timezone
    current_time = datetime.datetime.now()

    # Check if today is Saturday and the time is 9 PM
    if current_time.weekday() == 5 and current_time.hour == 21:  # 5 = Saturday, 21 = 9 PM
        for guild in bot.guilds:
            channel = discord.utils.get(guild.channels, name=CHAN_NAME)
            if channel:
                # Send inspirational quote
                flow = inspirobot.flow()
                await channel.send("**Inspirational Quote of the Week:**\n" + flow[0].text)

                # Send leaderboard message
                leaderboard_message = await generate_leaderboard_message("Weekly Leaderboard")
                await channel.send(leaderboard_message)

# Start the bot
bot.run(TOKEN)

'''
ARMAGEDON CODE. THIS SHIT WILL SEND A MESSAGE TO EVERYONE ON THE SERVER
for guild in bot.guilds:
    for member in guild.members:
        if not member.bot:  # Don't messages to bots
            try:
                await member.send(f"I'm tritin and I like feet")
'''


'''
shit to fix

$invest stock -12
$invest stock 0
$invest '--; 'DROP TABLE *';
$invest :MikeWeird: :MikeWeird: :MikeWeird:
$invest emoji 3 (implement a check that the stock exists)
'''