"""
Post a daily summary to LinkedIn via the UGC Posts API.
Reads the latest archive JSON and posts today's 5 headlines.

SETUP (one-time, takes ~10 minutes):
──────────────────────────────────────
1. Create a LinkedIn Developer App
   → https://www.linkedin.com/developers/apps/new
   Name: CatchTheBrief | Company: your LinkedIn company page

2. Under "Products" tab → request "Share on LinkedIn"
   This unlocks the w_member_social permission needed to post.

3. Under "Auth" tab → "OAuth 2.0 tools"
   → Generate access token
   → Select scope: w_member_social
   → Copy the access token (valid 60 days)

4. Get your Person URN (your personal LinkedIn ID):
   Run in terminal:
     curl -H "Authorization: Bearer YOUR_TOKEN" https://api.linkedin.com/v2/me
   Copy the "id" field (looks like: abc123XYZ)
   Your URN is: urn:li:person:abc123XYZ

   OR for a LinkedIn Company Page:
     curl -H "Authorization: Bearer YOUR_TOKEN" https://api.linkedin.com/v2/organizationAcls?q=roleAssignee
   Your URN is: urn:li:organization:12345678

5. Add to GitHub Secrets:
     LINKEDIN_ACCESS_TOKEN  = the access token from step 3
     LINKEDIN_AUTHOR_URN    = urn:li:person:... or urn:li:organization:...

TOKEN REFRESH (every 60 days):
   Repeat step 3. Update LINKEDIN_ACCESS_TOKEN secret in GitHub.
"""
import os
import json
import glob
import sys
from datetime import datetime

import requests


def get_latest_archive():
    files = sorted(glob.glob("archive/????-??-??.json"))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %B %Y")
    except Exception:
        return date_str


def build_post_text(data):
    date   = format_date(data.get("date", ""))
    briefs = data.get("briefs", [])[:5]

    lines = [f"⚡ Today's India Tech & Startup Briefs — {date}", ""]
    for i, b in enumerate(briefs, 1):
        lines.append(f"{i}. {b['title']}")
    lines.append("")
    lines.append("Read all 5 briefs with full analysis 👉 https://catchthebrief.com")
    lines.append("")
    lines.append("#IndiaStartup #IndianStartups #IndiaTech #StartupIndia #TechNews")

    return "\n".join(lines)


def main():
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    author_urn   = os.environ.get("LINKEDIN_AUTHOR_URN")

    if not access_token or not author_urn:
        print("LinkedIn credentials not set — skipping")
        sys.exit(0)

    data = get_latest_archive()
    if not data:
        print("No archive found — skipping")
        sys.exit(0)

    post_text = build_post_text(data)
    print("Posting to LinkedIn:")
    print(post_text)

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=payload,
        timeout=15,
    )

    if resp.status_code == 201:
        post_id = resp.headers.get("x-restli-id", "unknown")
        print(f"LinkedIn post successful! Post ID: {post_id}")
    else:
        print(f"LinkedIn post failed: {resp.status_code} — {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
