# ai-news-bot

Discord bot that scrapes AI-related headlines and links from `https://histre.com/hn/?tags=+ai` and posts new items to one Discord channel.

## What it does

- Checks the source every 15 minutes by default.
- Deduplicates posts by link ID and stores them in `posted_links.json`.
- Survives restarts without reposting old items.
- Supports a few manual commands:
  - `!test` — health check
  - `!latest` — show the latest fetched story
  - `!forcecheckposts` — owner-only manual check and post

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```dotenv
DISCORD_TOKEN=your_discord_bot_token
CHANNEL_ID=123456789012345678
```

## Run locally

```bash
./venv/bin/python main.py
```

## Discord setup

In the Discord Developer Portal:

1. Create a bot application.
2. Enable **Message Content Intent** if you want prefix commands like `!test`.
3. Invite the bot to the target server with permission to read and send messages.
4. Put the target text channel ID in `CHANNEL_ID`.

## Operational notes

- `posted_links.json` is the bot's memory. Delete it only if you want to reseed the feed.
- The bot is pointed at one source only. If you want to change the feed, change `NEWS_SOURCE_URL` in `main.py`.
- The source is noisy and changes over time, so the scraping logic may need maintenance if Histre changes its HTML.

## Server deployment

```bash
sudo useradd --system --home /srv/apps/ai-news-bot --shell /usr/sbin/nologin ainewsbot
sudo chown -R ainewsbot:ainewsbot /srv/apps/ai-news-bot
sudo chmod +x /srv/apps/ai-news-bot/scripts/preflight.sh
sudo -u ainewsbot python3 -m venv /srv/apps/ai-news-bot/venv
sudo -u ainewsbot /srv/apps/ai-news-bot/venv/bin/pip install -r /srv/apps/ai-news-bot/requirements.txt
sudo cp /srv/apps/ai-news-bot/deploy/ainewsbot.service /etc/systemd/system/ainewsbot.service
sudo systemctl daemon-reload
sudo systemctl enable --now ainewsbot.service
sudo journalctl -u ainewsbot.service -f
```
