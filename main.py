# ---------------------------------------------------------------------------
# AI News Bot for Discord
# ---------------------------------------------------------------------------
# Description:
# This Discord bot scrapes AI-related news headlines and links from
# histre.com/hn/?tags=+ai every 15 minutes. It posts new, unique links
# to a specified Discord channel.
#
# Modifications requested:
# 1. Persistence: Remember previously posted links even if the bot restarts
#    (e.g., due to laptop sleep/shutdown). Achieved by saving/loading
#    the set of posted link IDs to/from a file ('posted_links.json').
# 2. Graceful Error Handling: Implement try-except blocks for network
#    operations (fetching news, connecting/posting to Discord) with
#    logging and retry logic (exponential backoff) to handle temporary
#    network issues (like DNS errors or connection timeouts) more gracefully.
# 3. Code Commenting: Added detailed comments explaining the code logic.
# ---------------------------------------------------------------------------

import discord
from discord.ext import commands, tasks
import requests
from requests.exceptions import RequestException # Import specific exception for requests
from bs4 import BeautifulSoup
import asyncio
import os
from dotenv import load_dotenv
import json                     # For saving/loading posted links
import time                     # For exponential backoff
import traceback                # For logging full tracebacks
import logging                  # For better logging

# --- Configuration ---
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
NEWS_SOURCE_URL = "https://histre.com/hn/?tags=+ai"
CHECK_INTERVAL_SECONDS = 900  # 15 minutes
POSTED_LINKS_FILE = 'posted_links.json' # File to store posted link IDs
LOG_FILE = 'ai_news_bot.log' # Combined log file

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE), # Log to a file
        logging.StreamHandler()         # Log to console
    ]
)

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- Persistence ---
posted_link_ids = set() # Use this set to track posted links in the current session

def load_posted_links():
    """Loads the set of already posted link IDs from the JSON file."""
    global posted_link_ids
    try:
        if os.path.exists(POSTED_LINKS_FILE):
            with open(POSTED_LINKS_FILE, 'r') as f:
                posted_link_ids = set(json.load(f))
                logging.info(f"Loaded {len(posted_link_ids)} previously posted link IDs from {POSTED_LINKS_FILE}")
        else:
            logging.info(f"{POSTED_LINKS_FILE} not found. Starting with an empty set of posted links.")
            posted_link_ids = set()
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading {POSTED_LINKS_FILE}: {e}. Starting with an empty set.")
        posted_link_ids = set() # Start fresh if file is corrupted or unreadable

def save_posted_links():
    """Saves the current set of posted link IDs to the JSON file."""
    try:
        with open(POSTED_LINKS_FILE, 'w') as f:
            json.dump(list(posted_link_ids), f) # Convert set to list for JSON serialization
            # logging.info(f"Saved {len(posted_link_ids)} posted link IDs to {POSTED_LINKS_FILE}") # Optional: Log every save
    except IOError as e:
        logging.error(f"Error saving posted links to {POSTED_LINKS_FILE}: {e}")

# --- News Fetching and Parsing ---
def retrieve_and_parse_html_with_retries(max_retries=5, initial_delay=5):
    """
    Retrieves and parses HTML from the news source URL with retry logic.
    Uses exponential backoff for delays between retries.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            response = requests.get(NEWS_SOURCE_URL, headers=headers, timeout=30) # Added timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return BeautifulSoup(response.text, 'html.parser')
        except RequestException as e:
            logging.warning(f"Attempt {attempt + 1}/{max_retries} failed to fetch news: {e}")
            if attempt < max_retries - 1:
                logging.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2 # Exponential backoff
            else:
                logging.error(f"Failed to retrieve news from {NEWS_SOURCE_URL} after {max_retries} attempts.")
                return None # Return None if all retries fail
    return None

def extract_posts(soup):
    """Extracts post details from the parsed HTML soup."""
    if not soup:
        return []

    posts = []
    try:
        # Find the target div more robustly if possible, or adjust based on site structure
        # Assuming the structure remains similar to the original code for now
        target_div = soup.find('div', class_='text-muted', string=lambda text: text and 'Provide comma' in text)

        if not target_div:
            logging.warning("Target div for post extraction not found. Page structure might have changed.")
            # Fallback or alternative finding method could be added here if needed
            card_divs = soup.find_all('div', class_='card') # Try finding all cards directly as a fallback
            if not card_divs:
                 logging.error("Could not find any post cards.")
                 return []
        else:
             card_divs = target_div.find_all_next('div', class_='card')

        for card in card_divs:
            title_link = card.find('a', class_='fs-3')
            if title_link and title_link.get('href'): # Check if href exists
                link = title_link['href']
                # Use link as the unique ID
                post_id = link

                title = title_link.text.strip()
                points = "N/A"
                time_ago = "N/A"
                comments = "N/A"
                hn_link = None

                meta_div = card.find('div', class_='text-muted')
                if meta_div:
                    try:
                        points_text = meta_div.contents[0].strip()
                        points = points_text.split()[0] if points_text else "N/A"
                    except (IndexError, AttributeError): pass # Ignore if points can't be parsed

                    try:
                        time_ago = meta_div.contents[2].strip() if len(meta_div.contents) > 2 else "N/A"
                    except (IndexError, AttributeError): pass # Ignore if time can't be parsed

                    comments_link = meta_div.find('a')
                    if comments_link:
                        comments = comments_link.text.strip()
                        hn_link = comments_link.get('href')

                posts.append({
                    'id': post_id,
                    'title': title,
                    'link': link,
                    'points': points,
                    'time': time_ago,
                    'comments': comments,
                    'hn_link': hn_link
                })
    except Exception as e:
        logging.error(f"Error parsing posts: {e}\n{traceback.format_exc()}")
    return posts

# --- Core Bot Logic ---
async def check_and_post_new_stories():
    """Checks for new stories, compares with posted ones, and posts new ones."""
    global posted_link_ids
    logging.info("Running scheduled check...")

    soup = retrieve_and_parse_html_with_retries()
    if not soup:
        logging.warning("Skipping check as news fetching failed.")
        return # Skip this cycle if fetching failed

    current_posts = extract_posts(soup)
    if not current_posts:
        logging.info("No posts extracted from the source.")
        return # Skip if no posts found

    current_post_ids = set(post['id'] for post in current_posts)
    new_post_ids = current_post_ids - posted_link_ids

    if not new_post_ids:
        logging.info("No new posts found.")
        return

    new_posts = [post for post in current_posts if post['id'] in new_post_ids]
    logging.info(f"Found {len(new_posts)} new posts.")

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        logging.error(f"Could not find channel with ID {CHANNEL_ID}. Cannot post.")
        return

    posted_in_this_run = set() # Track links successfully posted in this run
    for post in reversed(new_posts): # Post oldest first
        try:
            message_content = f"{post['title']}\nLink: {post['link']}"
            if post.get('hn_link'):
                 message_content += f"\nComments: <{post['hn_link']}> ({post.get('comments', 'N/A')})"
            else:
                 message_content += f"\n(Comments: {post.get('comments', 'N/A')})"

            await channel.send(message_content)
            logging.info(f"Posted: {post['title']} ({post['link']})")
            posted_in_this_run.add(post['id'])
            await asyncio.sleep(1) # Short delay between posts to avoid rate limits

        except discord.errors.HTTPException as e:
            logging.error(f"Discord API error posting link {post['id']}: {e.status} - {e.text}")
            # Decide if retry is needed based on status code, e.g., rate limits (429)
            if e.status == 429:
                 retry_after = e.retry_after or 5 # Use Retry-After header or default
                 logging.warning(f"Rate limited. Retrying post after {retry_after} seconds.")
                 await asyncio.sleep(retry_after)
                 # Optionally retry posting the same message here
            # Don't add to posted_link_ids if sending failed permanently
            continue # Skip this post if sending failed

        except discord.errors.Forbidden:
             logging.error(f"Permission error: Cannot send messages to channel {CHANNEL_ID}.")
             # Might want to stop the task or notify admin if permissions are wrong
             break # Stop trying to post in this run

        except Exception as e:
            logging.error(f"Unexpected error posting link {post['id']}: {e}\n{traceback.format_exc()}")
            # Don't add to posted_link_ids if sending failed
            continue # Skip this post

    # Update the global set and save to file only AFTER attempting to post
    if posted_in_this_run:
        posted_link_ids.update(posted_in_this_run)
        save_posted_links()
        logging.info(f"Successfully posted {len(posted_in_this_run)} links. Total posted: {len(posted_link_ids)}")


# --- Bot Events and Tasks ---
@bot.event
async def on_ready():
    """Event handler for when the bot connects to Discord."""
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    logging.info('------')
    load_posted_links() # Load previously posted links on startup
    scheduled_check_task.start() # Start the background task

@bot.event
async def on_connect():
    logging.info("Bot connected to Discord gateway.")

@bot.event
async def on_disconnect():
    logging.warning("Bot disconnected from Discord gateway.")
    # The discord.py library handles reconnection automatically with backoff

@bot.event
async def on_resumed():
    logging.info("Bot resumed session with Discord gateway.")

@tasks.loop(seconds=CHECK_INTERVAL_SECONDS)
async def scheduled_check_task():
    """Background task that periodically calls check_and_post_new_stories."""
    try:
        await check_and_post_new_stories()
    except Exception as e:
        # Catch any unexpected errors within the task loop itself
        logging.error(f"Error in scheduled_check_task loop: {e}\n{traceback.format_exc()}")

@scheduled_check_task.before_loop
async def before_scheduled_check():
    """Wait until the bot is ready before starting the task loop."""
    await bot.wait_until_ready()
    logging.info("Bot is ready, starting scheduled check task.")


# --- Bot Commands ---
@bot.command(name='test')
async def test(ctx):
    """Test command to check if the bot is responsive."""
    logging.info(f"Received !test command from {ctx.author}")
    await ctx.send('Hello! AI News Bot is running.')

@bot.command(name='forcecheckposts')
@commands.is_owner() # Optional: Restrict command to bot owner
async def force_check_posts(ctx):
    """Manually triggers a check for new posts."""
    logging.info(f"Received !forcecheckposts command from {ctx.author}")
    await ctx.send('Forcing a check for new posts...')
    try:
        await check_and_post_new_stories()
        await ctx.send('Manual check complete.')
    except Exception as e:
         await ctx.send(f'An error occurred during manual check: {e}')
         logging.error(f"Error during manual check: {e}\n{traceback.format_exc()}")

@bot.command(name='latest')
async def get_latest_post(ctx):
    """Fetches and posts the single most recent story found."""
    logging.info(f"Received !latest command from {ctx.author}")
    await ctx.send('Fetching the latest post...')
    soup = retrieve_and_parse_html_with_retries()
    if not soup:
        await ctx.send('Failed to fetch news from the source.')
        return

    posts = extract_posts(soup)
    if not posts:
        await ctx.send('No posts could be extracted from the source.')
        return

    latest_post = posts[0] # Assuming the first post is the latest
    try:
        message_content = f"**Latest Post:** {latest_post['title']}\nLink: {latest_post['link']}"
        if latest_post.get('hn_link'):
             message_content += f"\nComments: <{latest_post['hn_link']}> ({latest_post.get('comments', 'N/A')})"
        else:
            message_content += f"\n(Comments: {latest_post.get('comments', 'N/A')})"
        await ctx.send(message_content)
        logging.info(f"Sent latest post ({latest_post['id']}) on command.")
    except discord.errors.HTTPException as e:
        logging.error(f"Discord API error sending latest post: {e.status} - {e.text}")
        await ctx.send("Failed to send the latest post due to a Discord error.")
    except Exception as e:
        logging.error(f"Unexpected error sending latest post: {e}\n{traceback.format_exc()}")
        await ctx.send("An unexpected error occurred while sending the latest post.")

# --- Main Execution ---
if __name__ == "__main__":
    if not DISCORD_TOKEN or not CHANNEL_ID:
        logging.critical("DISCORD_TOKEN or CHANNEL_ID environment variable not set. Exiting.")
        exit()

    try:
        logging.info("Starting AI News Bot...")
        bot.run(DISCORD_TOKEN, log_handler=None) # Disable default discord.py logging handler to use ours
    except discord.errors.LoginFailure:
        logging.critical("Login failed: Improper token provided.")
    except Exception as e:
        # Catch unexpected errors during startup or runtime not caught elsewhere
        logging.critical(f"Unhandled exception in bot.run: {e}\n{traceback.format_exc()}")
    finally:
         logging.info("AI News Bot shutting down.")