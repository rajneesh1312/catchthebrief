"""
Post a daily summary message to the CatchTheBrief Telegram channel.
Reads the latest archive JSON and sends today's 5 headlines.
Requires env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import os
import json
import glob
import sys

import requests


def get_latest_archive():
    files = sorted(glob.glob("archive/????-??-??.json"))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def format_date(date_str):
    from datetime import datetime
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %B %Y")
    except Exception:
        return date_str


def build_message(data):
    date = format_date(data.get("date", ""))
    briefs = data.get("briefs", [])[:5]

    lines = [f"⚡ <b>Today's India Tech Briefs</b> — {date}\n"]
    for i, b in enumerate(briefs, 1):
        lines.append(f"{i}. {b['title']}")
    lines.append("\nRead all 5 briefs 👉 https://catchthebrief.com")
    lines.append("\n#IndiaStartups #IndianTech #CatchTheBrief")

    return "\n".join(lines)


def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id   = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram credentials not set — skipping")
        sys.exit(0)

    data = get_latest_archive()
    if not data:
        print("No archive found — skipping")
        sys.exit(0)

    message = build_message(data)
    print("Sending to Telegram:")
    print(message)

    resp = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=15,
    )

    if resp.ok:
        print(f"Message sent! Message ID: {resp.json()['result']['message_id']}")
    else:
        print(f"Failed: {resp.status_code} — {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
