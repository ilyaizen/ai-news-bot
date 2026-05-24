#!/usr/bin/env bash
set -euo pipefail
APP_DIR="/srv/apps/ai-news-bot"
ENV_FILE="$APP_DIR/.env"
POSTED_LINKS_FILE="$APP_DIR/posted_links.json"

if [[ ! -r "$ENV_FILE" ]]; then
  echo "Missing readable $ENV_FILE" >&2
  exit 1
fi

# Source only simple KEY=VALUE lines. .env should contain DISCORD_TOKEN and CHANNEL_ID.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${DISCORD_TOKEN:-}" ]]; then
  echo "DISCORD_TOKEN is missing in $ENV_FILE" >&2
  exit 1
fi

if [[ -z "${CHANNEL_ID:-}" ]]; then
  echo "CHANNEL_ID is missing in $ENV_FILE" >&2
  exit 1
fi

if ! [[ "$CHANNEL_ID" =~ ^[0-9]+$ ]]; then
  echo "CHANNEL_ID must be numeric" >&2
  exit 1
fi

if [[ ! -w "$POSTED_LINKS_FILE" ]]; then
  echo "$POSTED_LINKS_FILE is not writable by service user" >&2
  exit 1
fi

exit 0
