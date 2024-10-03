import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

last_posts = set()  # Store the IDs of the last batch of posts

def retrieve_and_parse_html():
    url = "https://histre.com/hn/?tags=+ai"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')

def extract_posts(soup):
    target_div = soup.find('div', class_='text-muted', string=lambda text: 'Provide comma' in text if text else False)
    
    if not target_div:
        print("Target div not found. Check if the page structure has changed.")
        return []
    
    card_divs = target_div.find_all_next('div', class_='card')
    posts = []
    for card in card_divs:
        title_link = card.find('a', class_='fs-3')
        if title_link:
            title = title_link.text.strip()
            link = title_link['href']
            
            meta_div = card.find('div', class_='text-muted')
            if meta_div:
                points = meta_div.contents[0].strip().split()[0]
                time_ago = meta_div.contents[2].strip()
                
                comments_link = meta_div.find('a')
                comments = comments_link.text.strip() if comments_link else "0 comments"
                hn_link = comments_link['href'] if comments_link else None
                
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

async def check_for_new_posts():
    global last_posts
    try:
        soup = retrieve_and_parse_html()
        current_posts = extract_posts(soup)
        if not current_posts:
            print("No posts found.")
            return []

        current_post_ids = set(post['id'] for post in current_posts)
        
        if not last_posts:
            print("Initializing last_posts")
            last_posts = current_post_ids
            return []

        new_post_ids = current_post_ids - last_posts
        new_posts = [post for post in current_posts if post['id'] in new_post_ids]
        
        last_posts = current_post_ids  # Update last_posts for the next check

        return new_posts

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

async def post_stories(stories, channel):
    if stories:
        for post in stories:
            await channel.send(f"New post: {post['title']}\n"
                               f"Link: {post['link']}\n"
                               f"HN Link: {post['hn_link']}\n"
                               f"Points: {post['points']} | {post['time']} | {post['comments']}")
        print(f"Sent {len(stories)} posts to Discord.")
    else:
        print("No new posts to send.")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    bot.loop.create_task(scheduled_check())

async def scheduled_check():
    while True:
        new_posts = await check_for_new_posts()
        if new_posts:
            channel = bot.get_channel(CHANNEL_ID)
            await post_stories(new_posts, channel)
        await asyncio.sleep(900)  # 15 minutes

@bot.command(name='test')
async def test(ctx):
    """Test command to verify bot's ability to send messages"""
    await ctx.send('Hello! I am working correctly.')

@bot.command(name='forcecheckposts')
async def force_check_posts(ctx):
    """Force an immediate check for new posts"""
    await ctx.send('Forcing a check for new posts...')
    new_posts = await check_for_new_posts()
    await post_stories(new_posts, ctx.channel)
    await ctx.send('Check complete.')

@bot.command(name='latest')
async def get_latest_post(ctx):
    """Fetch and post the latest story"""
    await ctx.send('Fetching the latest post...')
    try:
        soup = retrieve_and_parse_html()
        posts = extract_posts(soup)
        if posts:
            latest_post = posts[0]
            await ctx.send(f"{latest_post['link']}\n"
                           f"HN Link: <{latest_post['hn_link']}>")
        else:
            await ctx.send('No posts found. This could indicate an issue with the website structure or the scraping process.')
    except Exception as e:
        await ctx.send(f'An error occurred while fetching the latest post: {e}')

bot.run(DISCORD_TOKEN)