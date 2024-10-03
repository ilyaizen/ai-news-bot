import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file (DISCORD_TOKEN and CHANNEL_ID)
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')  # Discord bot token from environment
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))  # ID of the Discord channel where posts will be sent

# Setup bot intents to handle messages
intents = discord.Intents.default()
intents.message_content = True  # Enable reading the content of messages
bot = commands.Bot(command_prefix='!', intents=intents)  # Create bot instance with command prefix '!' and specified intents

last_posts = set()  # Set to store IDs of the last batch of posts to avoid reposting

# Function to retrieve and parse HTML content from a specific URL
def retrieve_and_parse_html():
    url = "https://histre.com/hn/?tags=+ai"  # Target URL to scrape AI-related posts
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Send GET request to fetch the webpage
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an exception if the request fails
    return BeautifulSoup(response.text, 'html.parser')  # Parse the HTML response using BeautifulSoup

# Function to extract post details (title, link, points, etc.) from the parsed HTML
def extract_posts(soup):
    # Find the target div where post data is contained
    target_div = soup.find('div', class_='text-muted', string=lambda text: 'Provide comma' in text if text else False)

    # Handle the case where the expected div is not found
    if not target_div:
        print("Target div not found. Check if the page structure has changed.")
        return []

    # Find all post cards that follow the target div
    card_divs = target_div.find_all_next('div', class_='card')
    posts = []

    # Iterate over all cards to extract details for each post
    for card in card_divs:
        title_link = card.find('a', class_='fs-3')  # Post title and link
        if title_link:
            title = title_link.text.strip()
            link = title_link['href']

            # Extract additional metadata like points and comments
            meta_div = card.find('div', class_='text-muted')
            if meta_div:
                points = meta_div.contents[0].strip().split()[0]  # Number of points (first item in the text)
                time_ago = meta_div.contents[2].strip()  # Post age (e.g., '5 hours ago')

                # Extract comments and Hacker News link if available
                comments_link = meta_div.find('a')
                comments = comments_link.text.strip() if comments_link else "0 comments"
                hn_link = comments_link['href'] if comments_link else None

            # Append post details to the list
            posts.append({
                'id': link,
                'title': title,
                'link': link,
                'points': points,
                'time': time_ago,
                'comments': comments,
                'hn_link': hn_link
            })
    return posts

# Asynchronous function to check for new posts and avoid duplicates
async def check_for_new_posts():
    global last_posts  # Use the global variable to track post history
    try:
        soup = retrieve_and_parse_html()  # Retrieve and parse the HTML
        current_posts = extract_posts(soup)  # Extract post data
        if not current_posts:
            print("No posts found.")  # Handle case when no posts are found
            return []

        current_post_ids = set(post['id'] for post in current_posts)  # Collect current post IDs

        # If this is the first run, initialize last_posts with the current batch of IDs
        if not last_posts:
            print("Initializing last_posts")
            last_posts = current_post_ids
            return []

        # Determine new posts by finding the difference between current and previous post IDs
        new_post_ids = current_post_ids - last_posts
        new_posts = [post for post in current_posts if post['id'] in new_post_ids]

        print(f"Total posts: {len(current_posts)}")
        print(f"New posts: {len(new_posts)}")

        # Update last_posts to include the new set of posts
        last_posts = current_post_ids

        return new_posts  # Return the list of new posts

    except Exception as e:
        print(f"An error occurred: {e}")  # Handle any errors encountered during scraping
        return []

# Asynchronous function to send new posts to a specified Discord channel
async def post_stories(stories, channel):
    if stories:
        for post in stories:
            # Send the post link directly or include Hacker News link for non-HN posts
            if 'ycombinator.com' in post['link']:
                await channel.send(f"{post['link']}")
            else:
                await channel.send(f"{post['link']} (<{post['hn_link']}>)")
        print(f"Sent {len(stories)} posts to Discord.")  # Log the number of posts sent
    else:
        print("No new posts to send.")  # Handle case when no new posts are available

# Event handler that runs when the bot connects to Discord
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')  # Print a message when bot is online
    bot.loop.create_task(scheduled_check())  # Start the scheduled check for new posts

# Function to periodically check for new posts every 15 minutes
async def scheduled_check():
    while True:
        print("Running scheduled check...")
        new_posts = await check_for_new_posts()  # Retrieve new posts
        if new_posts:
            print(f"Found {len(new_posts)} new posts")
            channel = bot.get_channel(CHANNEL_ID)  # Fetch the Discord channel
            await post_stories(new_posts, channel)  # Send new posts to the channel
        else:
            print("No new posts found")
        await asyncio.sleep(900)  # Wait for 15 minutes before checking again

# Command to test if the bot is working correctly by sending a test message
@bot.command(name='test')
async def test(ctx):
    """Test command to verify bot's ability to send messages"""
    await ctx.send('Hello! I am working correctly.')  # Send a test message to the channel

# Command to manually trigger an immediate post check
@bot.command(name='forcecheckposts')
async def force_check_posts(ctx):
    """Force an immediate check for new posts"""
    await ctx.send('Forcing a check for new posts...')
    new_posts = await check_for_new_posts()  # Trigger new post retrieval
    await post_stories(new_posts, ctx.channel)  # Send new posts to the current channel
    await ctx.send('Check complete.')

# Command to fetch and post the latest story
@bot.command(name='latest')
async def get_latest_post(ctx):
    """Fetch and post the latest story"""
    await ctx.send('Fetching the latest post...')
    try:
        soup = retrieve_and_parse_html()  # Retrieve HTML content
        posts = extract_posts(soup)  # Extract post details
        if posts:
            latest_post = posts[0]  # Select the latest post
            if 'ycombinator.com' in latest_post['link']:
                await ctx.send(f"{latest_post['link']}")  # Send the post link
            else:
                await ctx.send(f"{latest_post['link']} (<{latest_post['hn_link']}>)")  # Include Hacker News link if applicable
        else:
            await ctx.send('No posts found. This could indicate an issue with the website structure or the scraping process.')
    except Exception as e:
        await ctx.send(f'An error occurred while fetching the latest post: {e}')  # Handle errors

# Run the bot using the Discord token
bot.run(DISCORD_TOKEN)
