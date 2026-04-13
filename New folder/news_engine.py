import os
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
from google import genai

# --- SECURE API KEY ---
# Windows CMD:        set GEMINI_API_KEY=your_key_here
# Windows PowerShell: $env:GEMINI_API_KEY="your_key_here"
# On GitHub, store it in: Settings > Secrets > Actions > GEMINI_API_KEY
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set. Cannot start.")

client = genai.Client(api_key=api_key)

# --- CONFIG ---
NEWS_CATEGORIES = [
    "AI Software news",
    "Laptop deals India",
    "Smartphone deals India",
    "Smart TV deals India",
    "Gaming news",
    "Cybersecurity news",
    "Tech startup news India",
    "Software deals",
]

REDDIT_DEAL_SOURCES = [
    "https://www.reddit.com/r/deals/hot.json?limit=6",
    "https://www.reddit.com/r/IndiaDeals/hot.json?limit=6",
]

# How long to wait between each Gemini API call (seconds).
# Free tier allows 5 requests/minute, so 13s gap keeps us safely under the limit.
AI_SLEEP_SECONDS = 13

# -----------------------------------------------

def fetch_deals():
    """Fetch top deals from multiple Reddit sources."""
    print("\n--- Hunting for Top Daily Deals ---")
    all_deals = []
    headers = {"User-Agent": "CatchTheBriefBot/1.0"}

    for url in REDDIT_DEAL_SOURCES:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                posts = data['data']['children']
                for post in posts[1:4]:   # Skip index 0 (usually pinned)
                    p = post['data']
                    if p.get('stickied'):
                        continue
                    all_deals.append({
                        "title": p['title'],
                        "link": p['url'],
                        "score": p.get('score', 0),
                        "source": url.split('/r/')[1].split('/')[0]
                    })
                    print(f"  Deal found: {p['title'][:60]}...")
            else:
                print(f"  Reddit returned status {response.status_code} for {url}")
        except Exception as e:
            print(f"  Error fetching from {url}: {e}")

    # Sort by community score, return top 3
    all_deals.sort(key=lambda x: x['score'], reverse=True)
    top_deals = all_deals[:3]

    if not top_deals:
        top_deals = [
            {"title": "Check back soon — today's hottest deals loading!", "link": "#", "source": "deals"},
            {"title": "Amazing tech deals curated daily", "link": "#", "source": "deals"},
            {"title": "Visit r/IndiaDeals for the latest offers", "link": "https://reddit.com/r/IndiaDeals", "source": "IndiaDeals"},
        ]

    return top_deals


def build_deal_card_html(deal, is_featured=False):
    """Build HTML for a single deal card."""
    badge = '<div class="absolute top-4 right-4 bg-green-500 text-white text-xs font-black px-2 py-1 rounded shadow-lg uppercase z-10">HOT DEAL</div>' if is_featured else ''
    source_label = deal.get('source', 'deals')

    return f"""
    <div class="glass-panel rounded-2xl p-5 shadow-xl flex flex-col items-center text-center relative mb-5">
        {badge}
        <div class="w-full h-32 bg-gray-800 rounded-xl mb-4 flex items-center justify-center border border-gray-700">
            <svg width="36" height="36" class="text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
        </div>
        <span class="text-xs text-gray-400 mb-2 uppercase tracking-wider">r/{source_label}</span>
        <h3 class="text-sm font-bold text-white mb-4 leading-snug">{deal['title']}</h3>
        <a href="{deal['link']}" target="_blank" rel="noopener noreferrer"
           class="w-full bg-blue-600 hover:bg-blue-500 text-white font-black text-sm py-2 px-4 rounded-xl shadow-lg transition-all duration-200 transform hover:-translate-y-1 block">
            Claim Deal &rarr;
        </a>
    </div>
    """


def summarize_with_ai(title):
    """Call Gemini to generate a 3-bullet HTML summary. Retries once on rate limit."""
    prompt = (
        f"Act as an engaging tech blogger writing for an Indian tech audience. "
        f"Write a 3-bullet-point summary about this news headline: '{title}'. "
        f"Keep each bullet concise (max 20 words). "
        f"FORMATTING RULE: Return ONLY HTML code. "
        f"Wrap the three points in a <ul> tag, with each point inside an <li> tag. "
        f"Do not include markdown backticks or any text outside the <ul> tag."
    )

    for attempt in range(2):  # Try up to 2 times
        try:
            ai_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            clean = ai_response.text.replace('```html', '').replace('```', '').strip()
            print("  AI summary generated.")
            return clean

        except Exception as e:
            if '429' in str(e) and attempt == 0:
                # Rate limited — wait and try once more
                print("  Rate limit hit. Waiting 35 seconds before retry...")
                time.sleep(35)
                continue
            else:
                print("  AI error — using fallback text.")
                return "<ul><li>AI servers are busy. Click the link below to read the full story!</li></ul>"

    return "<ul><li>AI servers are busy. Click the link below to read the full story!</li></ul>"


def build_news_card_html(category, title, link, ai_summary):
    """Build HTML for a single news article card."""
    return f"""
    <article class="glass-panel rounded-2xl p-8 shadow-2xl transition-all duration-300 hover:bg-opacity-20 hover:bg-white mb-8">
        <span class="inline-block bg-blue-900 text-blue-200 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider mb-4 border border-blue-500">
            {category}
        </span>
        <h3 class="text-xl font-bold text-white leading-tight mb-2">{title}</h3>
        <div class="ai-content">{ai_summary}</div>
        <a href="{link}" target="_blank" rel="noopener noreferrer"
           class="mt-6 inline-block text-blue-400 hover:text-blue-300 font-bold text-sm uppercase tracking-wide">
            Read Full Story &rarr;
        </a>
    </article>
    """


def get_timestamp():
    """Generate a Windows-compatible timestamp string."""
    now = datetime.now()
    # %-d and %-I don't work on Windows — build it manually
    day = now.day
    hour = now.hour % 12 or 12   # Convert 0->12, 13->1, etc.
    minute = now.strftime("%M")
    am_pm = "AM" if now.hour < 12 else "PM"
    month_year = now.strftime("%B %Y")
    return f"{day} {month_year} at {hour}:{minute} {am_pm} IST"


def fetch_and_update_website():
    print("=" * 50)
    print("  CatchTheBrief Engine Starting...")
    print("=" * 50)

    # 1. Fetch Deals
    deals = fetch_deals()
    deals_html = ""
    for i, deal in enumerate(deals):
        deals_html += build_deal_card_html(deal, is_featured=(i == 0))

    # 2. Fetch News + AI Summaries
    print("\n--- Fetching News Articles ---")
    print(f"  (Pausing {AI_SLEEP_SECONDS}s between AI calls to respect free tier limits)\n")
    all_articles_html = ""
    headers = {"User-Agent": "Mozilla/5.0"}
    ai_call_count = 0

    for category in NEWS_CATEGORIES:
        print(f"Processing: {category}")
        search_query = category.replace(" ", "+")
        url = f"https://news.google.com/rss/search?q={search_query}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, features="xml")
                items = soup.find_all('item')
                if not items:
                    print(f"  No items found for '{category}', skipping.")
                    continue

                title = items[0].title.text
                link = items[0].link.text
                print(f"  Headline: {title[:70]}...")

                # Pace the AI calls to stay within free tier (5 req/min)
                if ai_call_count > 0:
                    print(f"  Waiting {AI_SLEEP_SECONDS}s before next AI call...")
                    time.sleep(AI_SLEEP_SECONDS)

                ai_summary = summarize_with_ai(title)
                ai_call_count += 1
                all_articles_html += build_news_card_html(category, title, link, ai_summary)

            else:
                print(f"  News fetch failed — status {response.status_code}")

        except Exception as e:
            print(f"  Error for '{category}': {e}")

    # 3. Generate timestamp (Windows-compatible)
    last_updated = get_timestamp()

    # 4. Inject everything into the template
    print("\n--- Injecting into Template ---")
    try:
        with open("template.html", "r", encoding="utf-8") as f:
            template_data = f.read()
    except FileNotFoundError:
        print("ERROR: template.html not found. Make sure it is in the same folder.")
        return

    output = template_data.replace("{{ALL_ARTICLES}}", all_articles_html)
    output = output.replace("{{ALL_DEALS}}", deals_html)
    output = output.replace("{{LAST_UPDATED}}", last_updated)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(output)

    print("\n" + "=" * 50)
    print("  SUCCESS! index.html has been generated.")
    print(f"  Articles: {ai_call_count} summaries generated")
    print(f"  Deals:    {len(deals)} deals fetched")
    print(f"  Updated:  {last_updated}")
    print("=" * 50)
    print("\n  Open index.html in your browser to preview the site.")


if __name__ == "__main__":
    fetch_and_update_website()