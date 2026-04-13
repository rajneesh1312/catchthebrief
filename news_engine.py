"""
CatchTheBrief — Master Content Engine
======================================
Fetches real article content, generates AI summaries, builds affiliate deal links,
and compiles a full multi-page static site ready for GitHub Pages.

API KEY SETUP (set these before running):
  Windows CMD:
    set GEMINI_API_KEY_1=your_first_key
    set GEMINI_API_KEY_2=your_second_key
    set GEMINI_API_KEY_3=your_third_key
  Windows PowerShell:
    $env:GEMINI_API_KEY_1="your_first_key"
    $env:GEMINI_API_KEY_2="your_second_key"
    $env:GEMINI_API_KEY_3="your_third_key"

Get more free keys: https://aistudio.google.com → New Project → Get API Key
Each key = 20 free requests/day. 3 keys = 60/day (more than enough for 10 articles).
"""

import os
import re
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from google import genai

# ══════════════════════════════════════════════════════════════════════════════
#  API KEY POOL — rotate across multiple free keys to avoid daily quota limits
# ══════════════════════════════════════════════════════════════════════════════
#
# Free Gemini tier: 20 requests/day per key, 15 requests/minute per key.
# With 3 keys you get 60 requests/day — enough for 10 articles + retries.
#
# Get more free keys at: https://aistudio.google.com
#   → Click project name (top left) → New Project → Get API Key
#   Repeat for as many keys as you need.

_raw_keys = [
    os.environ.get("GEMINI_API_KEY_1"),
    os.environ.get("GEMINI_API_KEY_2"),
    os.environ.get("GEMINI_API_KEY_3"),
    # Add more if you have them:
    # os.environ.get("GEMINI_API_KEY_4"),
]
API_KEYS = [k for k in _raw_keys if k]   # only keep keys that are actually set

if not API_KEYS:
    raise ValueError(
        "\n\n  No Gemini API keys found!\n"
        "  Set at least one key:\n\n"
        "  Windows CMD:\n"
        "    set GEMINI_API_KEY_1=your_key_here\n\n"
        "  Windows PowerShell:\n"
        "    $env:GEMINI_API_KEY_1=\"your_key_here\"\n\n"
        "  Get a free key at: https://aistudio.google.com\n"
    )

# Build one Gemini client per key
_clients     = [genai.Client(api_key=k) for k in API_KEYS]
_key_index   = 0   # which key we're currently using


def get_client():
    """Return the currently active Gemini client."""
    return _clients[_key_index]


def rotate_key() -> bool:
    """
    Switch to the next available API key.
    Returns True if successfully rotated, False if all keys exhausted.
    """
    global _key_index
    if _key_index + 1 < len(_clients):
        _key_index += 1
        print(f"    ↻ Switched to API key {_key_index + 1} of {len(_clients)}")
        return True
    print(f"    ✗ All {len(_clients)} API key(s) exhausted for today.")
    print(f"      Add more keys or wait until tomorrow (quota resets at midnight UTC).")
    return False


# ── AFFILIATE CONFIG ───────────────────────────────────────────────────────────
# Replace with your actual Amazon Associates India tag after approval.
# Apply at: https://affiliate-program.amazon.in/
AMAZON_AFFILIATE_TAG = "catchthebrief-21"   # <-- update this once approved

# ── SITE CONFIG ────────────────────────────────────────────────────────────────
SITE_URL  = "https://catchthebrief.com"

# ── NEWS CATEGORIES ────────────────────────────────────────────────────────────
NEWS_CATEGORIES = [
    {"query": "artificial intelligence India 2025",       "label": "AI & Machine Learning", "color": "accent-purple"},
    {"query": "budget laptop deals India",                "label": "Laptop Deals",          "color": "accent-blue"},
    {"query": "smartphone deals India under 20000",       "label": "Smartphone Deals",      "color": "accent-green"},
    {"query": "smart TV best buy India",                  "label": "Smart TV",              "color": "accent-orange"},
    {"query": "cybersecurity India data breach",          "label": "Cybersecurity",         "color": "accent-red"},
    {"query": "Indian startup funding technology",        "label": "Startup Scene",         "color": "accent-teal"},
    {"query": "best software deals SaaS discount",        "label": "Software Deals",        "color": "accent-indigo"},
    {"query": "gaming PC console deals India",            "label": "Gaming",                "color": "accent-pink"},
    {"query": "budget audio earphones India review",      "label": "Audio Gear",            "color": "accent-yellow"},
    {"query": "refurbished electronics India certified",  "label": "Refurb Picks",          "color": "accent-gray"},
]

# ── REDDIT DEAL SOURCES ────────────────────────────────────────────────────────
DEAL_FEEDS = [
    "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
    "https://www.reddit.com/r/IndiaDeals.rss",
]

# ── RATE LIMITING ──────────────────────────────────────────────────────────────
# 13 seconds between AI calls = ~4.6 requests/minute (safely under the 15/min limit).
# The daily limit (20/key) is handled by key rotation above.
AI_SLEEP_SECONDS = 13

# ── PATHS ──────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent
TEMPLATES = ROOT / "templates"
ARTICLES  = ROOT / "articles"
ARTICLES.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def timestamp() -> str:
    """Windows-compatible human-readable timestamp."""
    now      = datetime.now()
    day      = now.day
    hour     = now.hour % 12 or 12
    minute   = now.strftime("%M")
    am_pm    = "AM" if now.hour < 12 else "PM"
    month_yr = now.strftime("%B %Y")
    return f"{day} {month_yr} at {hour}:{minute} {am_pm} IST"


def iso_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:80]


def tag_amazon_link(url: str) -> str:
    if "amazon.in" in url or "amazon.com" in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AMAZON_AFFILIATE_TAG}"
    return url


def load_template(name: str) -> str:
    path = TEMPLATES / name
    if not path.exists():
        raise FileNotFoundError(
            f"\n  Template not found: {path}\n"
            f"  Make sure the 'templates' folder exists next to news_engine.py\n"
            f"  and contains: index.html, article.html, deals.html\n"
        )
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ {path.name}")


# ══════════════════════════════════════════════════════════════════════════════
#  ARTICLE BODY FETCHING
# ══════════════════════════════════════════════════════════════════════════════

def fetch_article_body(url: str) -> str:
    """
    Scrape the article body from the source page.
    Returns up to 1500 chars of clean paragraph text, or '' on failure.
    """
    try:
        headers = {"User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.content, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer",
                          "aside", "form", "figure", "iframe", "noscript"]):
            tag.decompose()
        paras = soup.find_all("p")
        body  = " ".join(p.get_text(strip=True) for p in paras
                         if len(p.get_text(strip=True)) > 60)
        return body[:1500]
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
#  NEWS FETCHING
# ══════════════════════════════════════════════════════════════════════════════

def fetch_news_items() -> list[dict]:
    """Fetch one article per category from Google News RSS."""
    print("\n── Fetching News Articles ──────────────────────────────")
    items   = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for cat in NEWS_CATEGORIES:
        query = cat["query"].replace(" ", "+")
        label = cat["label"]
        color = cat["color"]
        url   = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                print(f"  ✗ {label}: HTTP {r.status_code}")
                continue

            root  = ET.fromstring(r.content)
            entry = root.find(".//item")
            if entry is None:
                print(f"  ✗ {label}: no items in feed")
                continue

            title    = (entry.findtext("title")   or "").strip()
            link     = (entry.findtext("link")    or "").strip()
            pub_date = (entry.findtext("pubDate") or "").strip()
            source   = (entry.findtext("source")  or "News").strip()

            print(f"  ✓ {label}: {title[:65]}...")

            items.append({
                "title":    title,
                "link":     link,
                "pub_date": pub_date,
                "source":   source,
                "label":    label,
                "color":    color,
                "slug":     slugify(title),
                "summary":  "",
                "hook":     "",
            })

        except Exception as e:
            print(f"  ✗ {label}: {e}")

    return items


# ══════════════════════════════════════════════════════════════════════════════
#  AI SUMMARIZATION — with key rotation on daily quota exhaustion
# ══════════════════════════════════════════════════════════════════════════════

def ai_summarize(item: dict) -> dict:
    """
    Fetch real article body, then ask Gemini to extract:
      1. 3 surprising/actionable facts (not headline rewrites)
      2. A one-sentence India-angle hook
    Rotates to next API key if daily quota is hit.
    """
    body    = fetch_article_body(item["link"])
    context = body if body else f"Headline: {item['title']}"

    prompt = f"""You are a sharp tech journalist writing for Indian readers.

Given this article content:
\"\"\"{context}\"\"\"

Headline: {item['title']}

Return a JSON object with exactly these two keys:
1. "bullets": list of exactly 3 strings. Each = one surprising or actionable fact. NOT a headline rewrite. Max 25 words each. Plain conversational English.
2. "hook": single sentence (max 20 words) why this matters for Indian buyers or tech users.

RULES:
- Return ONLY valid JSON. No markdown, no backticks, no extra text.
- If body is empty, infer from headline but find 3 distinct angles.
- Never start a bullet with "The article says" or "According to".

Example: {{"bullets": ["Fact one.", "Fact two.", "Fact three."], "hook": "Why India cares."}}"""

    # Try with up to 3 different strategies per article:
    # 1. Normal call
    # 2. Wait 35s and retry same key (handles per-minute rate limit)
    # 3. Rotate to next key and try once more (handles daily quota)
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            resp = get_client().models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw     = resp.text.strip().replace("```json", "").replace("```", "").strip()
            data    = json.loads(raw)
            bullets = data.get("bullets", [])
            hook    = data.get("hook", "")

            li_items       = "\n".join(f"            <li>{b}</li>" for b in bullets[:3])
            item["summary"] = f"<ul>\n{li_items}\n          </ul>"
            item["hook"]    = hook
            print(f"    ✓ Done (key {_key_index + 1})")
            return item

        except Exception as e:
            err = str(e)

            # Per-minute rate limit (too many requests in 60s) → wait and retry same key
            if "429" in err and "GenerateRequestsPerMinute" in err and attempt == 0:
                print(f"    ⏳ Per-minute limit — waiting 35s...")
                time.sleep(35)
                continue

            # Daily quota exhausted on this key → rotate to next key
            elif "429" in err and ("PerDay" in err or "per_day" in err or "daily" in err.lower()):
                print(f"    ⚠ Daily quota hit on key {_key_index + 1}")
                if rotate_key():
                    time.sleep(3)   # brief pause before trying new key
                    continue
                else:
                    break           # all keys exhausted — use fallback

            # Any other error → use fallback immediately
            else:
                print(f"    ✗ AI error: {e}")
                break

    # Fallback if all attempts failed
    item["summary"] = "<ul><li>Click the link below to read the full story.</li></ul>"
    item["hook"]    = "Read the full story for details."
    return item


def process_all_articles(items: list[dict]) -> list[dict]:
    """Run AI summarization on all articles with rate limiting between calls."""
    print("\n── Generating AI Summaries ─────────────────────────────")
    print(f"   Keys available: {len(API_KEYS)}  |  Max requests today: {len(API_KEYS) * 20}")
    for i, item in enumerate(items):
        print(f"  [{i+1}/{len(items)}] {item['label']}")
        if i > 0:
            print(f"    ⏳ Waiting {AI_SLEEP_SECONDS}s...")
            time.sleep(AI_SLEEP_SECONDS)
        items[i] = ai_summarize(item)
    return items


# ══════════════════════════════════════════════════════════════════════════════
#  DEALS
# ══════════════════════════════════════════════════════════════════════════════

def fetch_deals() -> list[dict]:
    """Fetch top deals from RSS feeds, affiliate-tag Amazon links."""
    print("\n── Fetching Deals ──────────────────────────────────────")
    all_deals = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    for feed_url in DEAL_FEEDS:
        try:
            r = requests.get(feed_url, headers=headers, timeout=10)
            if r.status_code != 200:
                print(f"  ✗ {feed_url}: HTTP {r.status_code}")
                continue

            root = ET.fromstring(r.content)
            # Handle both RSS <item> and Atom <entry> formats
            items = root.findall(".//item") or root.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            )

            for item in items[:8]:
                title = (
                    item.findtext("title")
                    or item.findtext("{http://www.w3.org/2005/Atom}title")
                    or ""
                ).strip()

                link = (
                    item.findtext("link")
                    or item.findtext("{http://www.w3.org/2005/Atom}link")
                    or ""
                ).strip()

                # Atom <link> is sometimes an attribute, not text
                if not link:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")
                    if link_el is not None:
                        link = link_el.get("href", "")

                if not title or not link:
                    continue

                all_deals.append({
                    "title":     title,
                    "link":      tag_amazon_link(link),
                    "score":     0,
                    "subreddit": feed_url.split("/")[2],  # domain as source label
                    "flair":     "",
                })
                print(f"  ✓ {title[:60]}...")

        except Exception as e:
            print(f"  ✗ {feed_url}: {e}")

    # Deduplicate by title prefix
    seen, unique = set(), []
    for d in all_deals:
        key = d["title"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return unique[:6] or [{
        "title": "Check back soon — deals updating!",
        "link": "#",
        "score": 0,
        "subreddit": "deals",
        "flair": ""
    }]


# ══════════════════════════════════════════════════════════════════════════════
#  HTML BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_article_card(item: dict, index: int) -> str:
    article_url = f"articles/{item['slug']}.html"
    delay       = index * 80
    return f"""
        <article class="card" style="animation-delay:{delay}ms" data-color="{item['color']}">
          <div class="card-tag {item['color']}">{item['label']}</div>
          <p class="card-hook">{item['hook']}</p>
          <h2 class="card-title">{item['title']}</h2>
          <div class="card-bullets">{item['summary']}</div>
          <div class="card-footer">
            <span class="card-source">{item['source']}</span>
            <div class="card-links">
              <a href="{article_url}" class="btn-brief">Full Brief →</a>
              <a href="{item['link']}" target="_blank" rel="noopener" class="btn-source">Source ↗</a>
            </div>
          </div>
        </article>"""


def build_deal_card(deal: dict, featured: bool = False) -> str:
    badge = '<span class="deal-badge">🔥 Hot</span>' if featured else ''
    flair = f'<span class="deal-flair">{deal["flair"]}</span>' if deal.get("flair") else ''
    return f"""
          <div class="deal-card{'  deal-featured' if featured else ''}">
            {badge}
            <div class="deal-meta">{flair}<span class="deal-sub">r/{deal['subreddit']}</span></div>
            <p class="deal-title">{deal['title']}</p>
            <a href="{deal['link']}" target="_blank" rel="noopener sponsored" class="deal-btn">
              Claim Deal →
            </a>
          </div>"""


def build_index_page(items: list[dict], deals: list[dict], ts: str) -> str:
    template           = load_template("index.html")
    articles_html      = "\n".join(build_article_card(item, i) for i, item in enumerate(items))
    sidebar_deals_html = "\n".join(build_deal_card(d, featured=(i == 0)) for i, d in enumerate(deals[:3]))
    return (template
            .replace("{{ALL_ARTICLES}}",  articles_html)
            .replace("{{SIDEBAR_DEALS}}", sidebar_deals_html)
            .replace("{{LAST_UPDATED}}", ts)
            .replace("{{SITE_URL}}",      SITE_URL)
            .replace("{{ISO_DATE}}",      iso_date()))


def build_article_page(item: dict, ts: str) -> str:
    template = load_template("article.html")
    return (template
            .replace("{{TITLE}}",       item["title"])
            .replace("{{LABEL}}",       item["label"])
            .replace("{{COLOR}}",       item["color"])
            .replace("{{HOOK}}",        item["hook"])
            .replace("{{SUMMARY}}",     item["summary"])
            .replace("{{SOURCE_NAME}}", item["source"])
            .replace("{{SOURCE_LINK}}", item["link"])
            .replace("{{PUB_DATE}}",    item["pub_date"])
            .replace("{{LAST_UPDATED}}",ts)
            .replace("{{SITE_URL}}",    SITE_URL)
            .replace("{{ISO_DATE}}",    iso_date()))


def build_deals_page(deals: list[dict], ts: str) -> str:
    template   = load_template("deals.html")
    deals_html = "\n".join(build_deal_card(d, featured=(i == 0)) for i, d in enumerate(deals))
    return (template
            .replace("{{ALL_DEALS}}",   deals_html)
            .replace("{{LAST_UPDATED}}",ts)
            .replace("{{SITE_URL}}",    SITE_URL)
            .replace("{{ISO_DATE}}",    iso_date()))


def build_sitemap(items: list[dict]) -> str:
    today = iso_date()
    urls  = [SITE_URL + "/", SITE_URL + "/deals.html"]
    urls += [f"{SITE_URL}/articles/{item['slug']}.html" for item in items]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq></url>")
    lines.append("</urlset>")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 56)
    print("  CatchTheBrief — Content Engine")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  API keys loaded: {len(API_KEYS)}")
    print("=" * 56)

    ts = timestamp()

    items = fetch_news_items()
    if not items:
        print("\n✗ No news items fetched. Check your internet connection.")
        return

    items = process_all_articles(items)
    deals = fetch_deals()

    print("\n── Building Pages ──────────────────────────────────────")
    write_file(ROOT / "index.html",  build_index_page(items, deals, ts))
    write_file(ROOT / "deals.html",  build_deals_page(deals, ts))
    write_file(ROOT / "sitemap.xml", build_sitemap(items))
    for item in items:
        write_file(ARTICLES / f"{item['slug']}.html", build_article_page(item, ts))

    print("\n" + "=" * 56)
    print("  ✓ BUILD COMPLETE")
    print(f"  Articles : {len(items)}")
    print(f"  Deals    : {len(deals)}")
    print(f"  Updated  : {ts}")
    print("=" * 56)
    print("\n  Open index.html in your browser to preview.\n")


if __name__ == "__main__":
    main()