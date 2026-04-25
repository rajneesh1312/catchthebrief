"""
Post a daily summary tweet after briefs are published.
Reads the latest archive JSON and composes a tweet with today's 5 headlines.
Requires env vars: TWITTER_API_KEY, TWITTER_API_SECRET,
                   TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
"""
import os
import json
import glob
import sys

import tweepy


def get_latest_archive():
    files = sorted(glob.glob("archive/????-??-??.json"))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def shorten(title, max_len=52):
    return title if len(title) <= max_len else title[: max_len - 1] + "…"


def build_tweet(data):
    date = data.get("date", "")
    briefs = data.get("briefs", [])[:5]

    lines = [f"Today's India Tech Briefs ⚡ ({date})\n"]
    for i, b in enumerate(briefs, 1):
        lines.append(f"{i}. {shorten(b['title'])}")
    lines.append("\nRead all 5 → catchthebrief.com")
    lines.append("#IndiaStartups #IndianTech")

    tweet = "\n".join(lines)
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."
    return tweet


def main():
    api_key    = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    acc_token  = os.environ.get("TWITTER_ACCESS_TOKEN")
    acc_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, acc_token, acc_secret]):
        print("Twitter credentials not set — skipping tweet")
        sys.exit(0)

    data = get_latest_archive()
    if not data:
        print("No archive found — skipping tweet")
        sys.exit(0)

    tweet = build_tweet(data)
    print("Posting tweet:")
    print(tweet)
    print(f"({len(tweet)} chars)")

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=acc_token,
        access_token_secret=acc_secret,
    )
    response = client.create_tweet(text=tweet)
    print(f"Tweet posted! ID: {response.data['id']}")


if __name__ == "__main__":
    main()
