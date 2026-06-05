# ai-news-bot

Use the files in this repo as the source of truth for runtime behavior and deployment.

## Setup checklist

- Create `.env` with `DISCORD_TOKEN` and `CHANNEL_ID`.
- Create the virtualenv and install `requirements.txt`.
- Make sure `posted_links.json` is writable by the service user.

## Things to keep current

- `NEWS_SOURCE_URL` in `main.py` if the source changes.
- `posted_links.json` is the unique dedupe list. Commit it regularly so reposts stay suppressed across restarts.
- Only clear `posted_links.json` when you intentionally want to reseed or repost.

## Commands

- Local run: `./venv/bin/python main.py`
- Service health: `systemctl status ainewsbot.service`
- Logs: `journalctl -u ainewsbot.service -f`
