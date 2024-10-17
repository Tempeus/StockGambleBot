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
CHAN_NAME = 'bot-spam'

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
@bot.command(name='invest')
async def invest(ctx, stock_name: str, quantity: int, price: float = None):
    # Fetch the user ID from the context
    user_id = ctx.author.id

    # If price is not provided, fetch the latest price from Yahoo Finance
    if price is None:
        stock = yf.Ticker(stock_name)
        stock_info = stock.history(period="1d")
        
        # Get the latest closing price
        if not stock_info.empty:
            price = stock_info['Close'].iloc[-1]
        else:
            await ctx.send(f"Could not retrieve price for {stock_name}. Please specify a price.")
            return

    # Now that we have a price, proceed to store the investment
    db.add_investment(user_id, stock_name, quantity, price)
    await ctx.send(f"You have invested in {quantity} shares of {stock_name} at a price of ${price:.2f}.")

@bot.command(name='remove')
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
@bot.command(name='portfolio')
async def portfolio(ctx):
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
            f"**Total Quantity:** {total_quantity}\n"
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
    # Retrieve all users' investments
    user_investments = db.get_all_investments()  # This method should return all user investments

    user_stats = {}

    for user_id, stock_name, quantity, purchase_price in user_investments:
        if user_id not in user_stats:
            user_stats[user_id] = {'total_invested': 0, 'total_quantity': 0, 'total_gain': 0}

        total_invested = quantity * purchase_price
        user_stats[user_id]['total_invested'] += total_invested
        user_stats[user_id]['total_quantity'] += quantity

        current_price = get_stock_price(stock_name)

        if current_price is not None:
            gain = (current_price - purchase_price) * quantity
            user_stats[user_id]['total_gain'] += gain

    # Prepare leaderboard message
    leaderboard_message = "**Leaderboard:**\n"
    
    # Calculate average gain percentage and create a sortable list
    leaderboard_data = []
    for user_id, stats in user_stats.items():
        if stats['total_quantity'] > 0 and stats['total_invested'] > 0:
            average_gain_percentage = (stats['total_gain'] / stats['total_invested']) * 100
            leaderboard_data.append((user_id, average_gain_percentage))

    # Sort the leaderboard data by gain percentage in descending order
    leaderboard_data.sort(key=lambda x: x[1], reverse=True)

    # Format the sorted leaderboard with ranks
    for rank, (user_id, gain_percentage) in enumerate(leaderboard_data, start=1):
        user = await bot.fetch_user(int(user_id))  # Fetch user name
        leaderboard_message += f"{rank}. **{user}**: {gain_percentage:.2f}%\n"

    if not leaderboard_data:
        leaderboard_message = "No investments found for any users."

    # Send the leaderboard message in the channel
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
            # Find the channel name in the guild
            channel = discord.utils.get(guild.channels, name=CHAN_NAME)
            if channel is not None:
                #Send some motivational quotes
                flow = inspirobot.flow()

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
                await channel.send("**Inspirational Quote of the Month:**\n" + flow[0].text + "\n\n" + leaderboard_message)
            else:
                print(f"{CHAN_NAME} channel not found in guild {guild.name}")

@tasks.loop(hours=24)
async def monthly_update():
    channel = discord.utils.get(bot.get_all_channels(), name=CHAN_NAME)

    # Retrieve all users' investments
    user_investments = db.get_all_investments()  # This method should return all user investments

    user_stats = {}

    #Send some motivational quotes
    flow = inspirobot.flow()

    for user_id, stock_name, quantity, purchase_price in user_investments:
        if user_id not in user_stats:
            user_stats[user_id] = {'total_invested': 0, 'total_quantity': 0, 'total_gain': 0}

        total_invested = quantity * purchase_price
        user_stats[user_id]['total_invested'] += total_invested
        user_stats[user_id]['total_quantity'] += quantity

        current_price = get_stock_price(stock_name)

        if current_price is not None:
            gain = (current_price - purchase_price) * quantity
            user_stats[user_id]['total_gain'] += gain

    # Prepare leaderboard message
    leaderboard_message = "**Monthly Leaderboard:**\n"
    
    # Calculate average gain percentage and create a sortable list
    leaderboard_data = []
    for user_id, stats in user_stats.items():
        if stats['total_quantity'] > 0 and stats['total_invested'] > 0:
            average_gain_percentage = (stats['total_gain'] / stats['total_invested']) * 100
            leaderboard_data.append((user_id, average_gain_percentage))

    # Sort the leaderboard data by gain percentage in descending order
    leaderboard_data.sort(key=lambda x: x[1], reverse=True)

    # Format the sorted leaderboard with ranks
    for rank, (user_id, gain_percentage) in enumerate(leaderboard_data, start=1):
        user = await bot.fetch_user(int(user_id))  # Fetch user name
        leaderboard_message += f"{rank}. **{user}**: {gain_percentage:.2f}%\n"

    if not leaderboard_data:
        leaderboard_message = "No investments found for any users."

    # Send the monthly update message in the designated channel
    await channel.send("**Inspirational Quote of the Month:**\n" + flow[0].text + "\n\n" + leaderboard_message)             

# Start the bot
bot.run(TOKEN)

'''
ARMAGEDON CODE. THIS SHIT WILL SEND A MESSAGE TO EVERYONE ON THE SERVER
for guild in bot.guilds:
    for member in guild.members:
        if not member.bot:  # Don't send updates to bots
            user_id = str(member.id)
            result = calculate_gain_loss(user_id)
            if result:
                try:
                    await member.send(f"I'm tritin and I like feet")
'''