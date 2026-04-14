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
Each key = 20 free requests/day. 3 keys = 60/day (enough for 12 articles + 6 deals).
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
#  API KEY POOL
# ══════════════════════════════════════════════════════════════════════════════
_raw_keys = [
    os.environ.get("GEMINI_API_KEY_1"),
    os.environ.get("GEMINI_API_KEY_2"),
    os.environ.get("GEMINI_API_KEY_3"),
    # os.environ.get("GEMINI_API_KEY_4"),  # add more if needed
]
API_KEYS = [k for k in _raw_keys if k]

if not API_KEYS:
    raise ValueError(
        "\n\n  No Gemini API keys found!\n"
        "  Set at least one key:\n\n"
        "  Windows CMD:  set GEMINI_API_KEY_1=your_key_here\n"
        "  PowerShell:   $env:GEMINI_API_KEY_1='your_key_here'\n\n"
        "  Get a free key at: https://aistudio.google.com\n"
    )

_clients   = [genai.Client(api_key=k) for k in API_KEYS]
_key_index = 0


def get_client():
    return _clients[_key_index]


def rotate_key() -> bool:
    global _key_index
    if _key_index + 1 < len(_clients):
        _key_index += 1
        print(f"    ↻ Switched to API key {_key_index + 1} of {len(_clients)}")
        return True
    print(f"    ✗ All {len(_clients)} Gemini key(s) exhausted — will use Groq fallback.")
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  GROQ FALLBACK — free tier: 14,400 requests/day (essentially unlimited)
#  Used automatically when ALL Gemini keys are exhausted for the day.
#
#  Setup:
#    1. Sign up free at https://console.groq.com
#    2. Create an API key
#    3. Set env variable:
#       Windows CMD:        set GROQ_API_KEY=your_key_here
#       Windows PowerShell: $env:GROQ_API_KEY="your_key_here"
#       GitHub Secret:      name = GROQ_API_KEY
# ══════════════════════════════════════════════════════════════════════════════
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY")
GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama-3.3-70b-versatile"   # best free model on Groq
_groq_available = bool(GROQ_API_KEY)

if _groq_available:
    print(f"  ✓ Groq fallback: available (model: {GROQ_MODEL})")
else:
    print(f"  ⚠ Groq fallback: not configured (set GROQ_API_KEY to enable)")


def call_groq(prompt: str) -> str:
    """
    Call Groq API (OpenAI-compatible). Returns raw text response.
    Raises on failure.
    """
    if not _groq_available:
        raise RuntimeError("Groq API key not set")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 800,
    }
    r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Groq HTTP {r.status_code}: {r.text[:200]}")

    raw = r.json()["choices"][0]["message"]["content"].strip()
    return raw.replace("```json", "").replace("```", "").strip()


# ── AFFILIATE CONFIG ───────────────────────────────────────────────────────────
AMAZON_AFFILIATE_TAG = "catchthebrief-21"

# ── SITE CONFIG ────────────────────────────────────────────────────────────────
SITE_URL = "https://catchthebrief.com"

# ══════════════════════════════════════════════════════════════════════════════
#  NEWS CATEGORIES — 5 during development (reduces Gemini API load)
#  Total AI calls per run: 5 articles + 6 deals = 11 calls
#  Well within 1 key's 20/day free limit — no key rotation needed.
#
#  TO EXPAND LATER: uncomment the extra categories below when ready.
# ══════════════════════════════════════════════════════════════════════════════
NEWS_CATEGORIES = [
    {"query": "artificial intelligence India 2026",      "label": "AI & Machine Learning", "color": "accent-purple"},
    {"query": "smartphone deals India under 20000",      "label": "Smartphone Deals",      "color": "accent-green"},
    {"query": "India cricket IPL 2026 news today",       "label": "Cricket",               "color": "accent-cricket"},
    {"query": "Indian startup funding technology 2026",  "label": "Startup Scene",         "color": "accent-teal"},
    {"query": "India top news today 2026",               "label": "India Today",           "color": "accent-india"},

    # ── UNCOMMENT BELOW TO EXPAND (add more API keys first) ──────────────────
    # {"query": "budget laptop deals India 2026",          "label": "Laptop Deals",          "color": "accent-blue"},
    # {"query": "smart TV best buy India",                 "label": "Smart TV",              "color": "accent-orange"},
    # {"query": "cybersecurity India data breach 2026",    "label": "Cybersecurity",         "color": "accent-red"},
    # {"query": "gaming PC console deals India 2026",      "label": "Gaming",                "color": "accent-pink"},
    # {"query": "budget audio earphones India review 2026","label": "Audio Gear",            "color": "accent-yellow"},
    # {"query": "Bollywood entertainment news India 2026", "label": "Entertainment",         "color": "accent-entertain"},
    # {"query": "India economy business market news 2026", "label": "Business & Economy",    "color": "accent-business"},
]

# ══════════════════════════════════════════════════════════════════════════════
#  DEAL SOURCES — India-focused (replaces US-only Slickdeals)
# ══════════════════════════════════════════════════════════════════════════════
DEAL_FEEDS = [
    "https://feeds.feedburner.com/91mobiles",           # India's top gadget deals site
    "https://www.mysmartprice.com/gear/feed/",          # India price comparison + deals
    "https://www.reddit.com/r/IndiaDeals.rss",          # Community India deals Reddit
    "https://www.smartprix.com/bytes/feed/",            # Smartprix India deals
]

# ── RATE LIMITING ──────────────────────────────────────────────────────────────
AI_SLEEP_SECONDS = 13  # safely under 15 requests/minute per key

# ── PATHS ──────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent
TEMPLATES = ROOT / "templates"
ARTICLES  = ROOT / "articles"
DEALS_DIR = ROOT / "deals"
ARTICLES.mkdir(exist_ok=True)
DEALS_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def timestamp() -> str:
    now    = datetime.now()
    hour   = now.hour % 12 or 12
    am_pm  = "AM" if now.hour < 12 else "PM"
    return f"{now.day} {now.strftime('%B %Y')} at {hour}:{now.strftime('%M')} {am_pm} IST"


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


def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


def load_template(name: str) -> str:
    path = TEMPLATES / name
    if not path.exists():
        raise FileNotFoundError(
            f"\n  Template not found: {path}\n"
            f"  Make sure templates/ contains: index.html, article.html, deals.html, deal_detail.html\n"
        )
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ {path.relative_to(ROOT)}")


# ══════════════════════════════════════════════════════════════════════════════
#  ARTICLE BODY FETCHING
# ══════════════════════════════════════════════════════════════════════════════

def fetch_article_body(url: str) -> str:
    """Scrape article body. Returns up to 1500 chars of clean text, or '' on failure."""
    try:
        headers = {"User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
        url   = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                print(f"  ✗ {cat['label']}: HTTP {r.status_code}")
                continue

            root    = ET.fromstring(r.content)
            entries = root.findall(".//item")[:3]

            for entry in entries:
                title    = strip_html(entry.findtext("title")   or "").strip()
                link     = (entry.findtext("link")    or "").strip()
                pub_date = (entry.findtext("pubDate") or "").strip()
                source   = (entry.findtext("source")  or "News").strip()
                desc     = strip_html(entry.findtext("description") or "").strip()

                if not title or not link:
                    continue

                print(f"  ✓ {cat['label']}: {title[:65]}...")
                items.append({
                    "title":    title,
                    "link":     link,
                    "pub_date": pub_date,
                    "source":   source,
                    "label":    cat["label"],
                    "color":    cat["color"],
                    "slug":     slugify(title),
                    "summary":  "",
                    "hook":     "",
                    "why_it_matters": "",
                    "rss_desc": desc,
                })
                break  # first valid item per category

        except Exception as e:
            print(f"  ✗ {cat['label']}: {e}")

    return items


# ══════════════════════════════════════════════════════════════════════════════
#  AI SUMMARIZATION
#  New hybrid format: hook paragraph + 3 bullets + "Why it matters"
# ══════════════════════════════════════════════════════════════════════════════

def _call_gemini(prompt: str) -> str:
    """Single Gemini call. Raises on error."""
    resp = get_client().models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return resp.text.strip().replace("```json", "").replace("```", "").strip()


def _call_ai(prompt: str) -> str:
    """
    Call Gemini first. If all Gemini keys are exhausted, fall back to Groq.
    Returns raw text (JSON string expected by callers).
    """
    # Try Gemini
    for attempt in range(3):
        try:
            return _call_gemini(prompt)
        except Exception as e:
            err = str(e)
            if "429" in err and "GenerateRequestsPerMinute" in err and attempt == 0:
                print(f"    ⏳ Gemini rate limit — waiting 35s...")
                time.sleep(35)
            elif "429" in err and ("PerDay" in err or "per_day" in err or "daily" in err.lower()):
                print(f"    ⚠ Gemini daily quota hit on key {_key_index + 1}")
                if rotate_key():
                    time.sleep(3)
                else:
                    # All Gemini keys exhausted — try Groq
                    print(f"    ↷ Switching to Groq fallback...")
                    return call_groq(prompt)
            else:
                if attempt < 2:
                    print(f"    ✗ Gemini error (attempt {attempt+1}): {e} — retrying...")
                    time.sleep(5)
                else:
                    raise

    raise RuntimeError("All Gemini attempts failed")


def ai_summarize(item: dict) -> dict:
    """
    Generate hybrid brief: hook paragraph + 3 bullet facts + why it matters.
    Falls back to RSS description — never publishes blank content.
    """
    body    = fetch_article_body(item["link"])
    context = body if body else f"Headline: {item['title']}\n{item.get('rss_desc', '')}"

    prompt = f"""You are a sharp journalist writing for Indian readers aged 18-35.
Mix of tech-savvy and general news audience. Write in clear, friendly English.

Article content:
\"\"\"{context}\"\"\"

Headline: {item['title']}
Category: {item['label']}

Return a JSON object with exactly these three keys:
1. "hook": A paragraph of 2-3 sentences. Tell the story naturally — what happened, why it's interesting. Max 60 words. Friendly tone. NOT a headline rewrite.
2. "bullets": List of exactly 3 strings. Each = one concrete fact, stat, name, or number. Max 20 words each. Quick-scan version.
3. "why_it_matters": Single sentence (max 20 words) — the India angle. Why should an Indian reader care?

RULES:
- Return ONLY valid JSON. No markdown fences, no extra text.
- If body is thin, infer intelligently from the headline.
- Never start with "The article says" or "According to".
- "hook" should feel like a friend explaining the news, not a press release.

Example:
{{"hook": "OpenAI just dropped GPT-5 and it's already reshaping how developers think about AI. The new model beats benchmarks by 40% and costs half as much to run.", "bullets": ["GPT-5 scores 40% higher than GPT-4 on coding benchmarks.", "API pricing drops by 50% — a major win for startups.", "Available to all paid users today; free tier gets access next month."], "why_it_matters": "Indian AI startups can now build smarter apps at half the cost."}}"""

    for attempt in range(2):
        try:
            raw  = _call_ai(prompt)
            data = json.loads(raw)
            hook = data.get("hook", "").strip()
            buls = data.get("bullets", [])
            why  = data.get("why_it_matters", "").strip()

            if not hook or not buls:
                raise ValueError("Empty AI response")

            li = "\n".join(f"            <li>{b}</li>" for b in buls[:3])
            item["hook"]           = hook
            item["why_it_matters"] = why
            item["summary"] = (
                f'<p class="brief-hook">{hook}</p>\n'
                f'<ul>\n{li}\n          </ul>\n'
                f'<p class="brief-why"><strong>Why it matters:</strong> {why}</p>'
            )
            print(f"    ✓ Done")
            return item

        except Exception as e:
            print(f"    ✗ AI error (attempt {attempt+1}): {e}")
            if attempt == 0:
                time.sleep(5)

    # ── FALLBACK — use RSS description, never publish blank ──────────────────
    desc = item.get("rss_desc", "").strip()
    if desc and len(desc) > 30:
        item["hook"]           = desc[:200]
        item["why_it_matters"] = "Read the full story for complete details."
        item["summary"] = (
            f'<p class="brief-hook">{desc[:200]}</p>\n'
            f'<ul>\n'
            f'            <li>Full details available at the source — click the Source link below.</li>\n'
            f'            <li>Story published by {item["source"]}.</li>\n'
            f'            <li>Check back tomorrow for an updated brief on this topic.</li>\n'
            f'          </ul>\n'
            f'<p class="brief-why"><strong>Why it matters:</strong> Read the full story for complete details.</p>'
        )
        print(f"    ⚠ Used RSS description fallback")
    else:
        # Last resort — meaningful generic content
        item["hook"] = f"This story from {item['source']} covers {item['label'].lower()} developments relevant to Indian readers. Click the Source link below to read the full article."
        item["why_it_matters"] = "Read the full story for details."
        item["summary"] = (
            f'<p class="brief-hook">This story from {item["source"]} covers important {item["label"].lower()} news. Click Source below to read the full article.</p>\n'
            f'<ul>\n'
            f'            <li>Full article available at {item["source"]}.</li>\n'
            f'            <li>Category: {item["label"]}.</li>\n'
            f'            <li>Published: {item["pub_date"][:16] if item["pub_date"] else "Today"}.</li>\n'
            f'          </ul>\n'
            f'<p class="brief-why"><strong>Why it matters:</strong> Read the full story for details.</p>'
        )
        print(f"    ⚠ Used last-resort fallback")

    return item


def process_all_articles(items: list[dict]) -> list[dict]:
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
#  DEALS — India-focused + AI detail pages
# ══════════════════════════════════════════════════════════════════════════════

def fetch_deals() -> list[dict]:
    """Fetch deals from India-focused RSS feeds."""
    print("\n── Fetching Deals ──────────────────────────────────────")
    all_deals = []
    headers   = {"User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )}

    for feed_url in DEAL_FEEDS:
        try:
            r = requests.get(feed_url, headers=headers, timeout=10)
            if r.status_code != 200:
                print(f"  ✗ {feed_url}: HTTP {r.status_code}")
                continue

            root  = ET.fromstring(r.content)
            items = root.findall(".//item") or root.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            )
            domain = feed_url.split("/")[2].replace("www.", "").replace("feeds.feedburner.com", "91mobiles.com")

            for item in items[:8]:
                title = strip_html(
                    item.findtext("title")
                    or item.findtext("{http://www.w3.org/2005/Atom}title")
                    or ""
                ).strip()

                link = (
                    item.findtext("link")
                    or item.findtext("{http://www.w3.org/2005/Atom}link")
                    or ""
                ).strip()
                if not link:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")
                    if link_el is not None:
                        link = link_el.get("href", "")

                desc = strip_html(
                    item.findtext("description")
                    or item.findtext("{http://www.w3.org/2005/Atom}summary")
                    or ""
                ).strip()[:300]

                if not title or not link:
                    continue

                all_deals.append({
                    "title":       title,
                    "link":        tag_amazon_link(link),
                    "source":      domain,
                    "description": desc,
                    "slug":        slugify(title),
                    "ai_desc":     "",
                    "highlights":  [],
                    "amazon_link": "",
                })
                print(f"  ✓ {title[:60]}...")

        except Exception as e:
            print(f"  ✗ {feed_url}: {e}")

    # Deduplicate
    seen, unique = set(), []
    for d in all_deals:
        key = d["title"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(d)

    result = unique[:6]
    if not result:
        result = [{
            "title":       "Check back soon — India deals updating!",
            "link":        "#",
            "source":      "catchthebrief",
            "description": "Fresh deals from top Indian retailers added every morning.",
            "slug":        "check-back-soon",
            "ai_desc":     "",
            "highlights":  [],
            "amazon_link": "",
        }]
    return result


def ai_describe_deal(deal: dict) -> dict:
    """Generate AI description + highlights + Amazon link for deal detail page."""
    context = deal["description"] if deal["description"] else deal["title"]

    prompt = f"""You are a deal analyst writing for Indian tech buyers.

Deal title: {deal['title']}
Context: {context}
Source: {deal['source']}

Return a JSON object with exactly these keys:
1. "description": 2-3 sentence paragraph. What is this deal? Why is it good value? Who should buy it? Friendly tone. Max 60 words.
2. "highlights": List of exactly 3 strings. Each = one key selling point or saving. Max 15 words each. Punchy and scannable.
3. "amazon_search": Amazon.in search URL for this product.
   Format: https://www.amazon.in/s?k=SEARCH+TERMS&tag={AMAZON_AFFILIATE_TAG}
   Use the most relevant 3-5 keywords from the title. Use + for spaces.

RULES:
- Return ONLY valid JSON. No markdown, no backticks.
- If the deal is unclear, write a helpful general description.

Example:
{{"description": "The boAt Rockerz 450 is India's favourite wireless headphone, now at its lowest price ever. Great 15-hour battery and punchy bass make it ideal for commuters and WFH users.", "highlights": ["15 hours battery life on a single charge", "Deep bass tuned for Indian music", "Foldable and travel-friendly design"], "amazon_search": "https://www.amazon.in/s?k=boAt+Rockerz+450+wireless+headphones&tag={AMAZON_AFFILIATE_TAG}"}}"""

    for attempt in range(2):
        try:
            raw  = _call_ai(prompt)
            data = json.loads(raw)
            deal["ai_desc"]    = data.get("description", "").strip()
            deal["highlights"] = data.get("highlights", [])[:3]
            deal["amazon_link"]= data.get("amazon_search", "").strip()
            print(f"    ✓ Deal AI done: {deal['title'][:50]}...")
            return deal
        except Exception as e:
            print(f"    ✗ Deal AI error (attempt {attempt+1}): {e}")
            if attempt == 0:
                time.sleep(5)

    # Fallback
    deal["ai_desc"]    = f"Great deal spotted on {deal['source']}. Click below for full pricing and availability."
    deal["highlights"] = ["Verified from community deal forum", "Limited time offer — check current price", "Compare prices before buying"]
    search_terms       = "+".join(deal["title"].split()[:4])
    deal["amazon_link"]= f"https://www.amazon.in/s?k={search_terms}&tag={AMAZON_AFFILIATE_TAG}"
    return deal


def process_all_deals(deals: list[dict]) -> list[dict]:
    print("\n── Generating AI Deal Descriptions ─────────────────────")
    for i, deal in enumerate(deals):
        if deal["slug"] == "check-back-soon":
            continue
        print(f"  [{i+1}/{len(deals)}] {deal['title'][:55]}...")
        if i > 0:
            print(f"    ⏳ Waiting {AI_SLEEP_SECONDS}s...")
            time.sleep(AI_SLEEP_SECONDS)
        deals[i] = ai_describe_deal(deal)
    return deals


# ══════════════════════════════════════════════════════════════════════════════
#  HTML BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_article_card(item: dict, index: int) -> str:
    article_url  = f"articles/{item['slug']}.html"
    hook_preview = item.get("hook", "")[:120]
    return f"""
        <article class="card" style="animation-delay:{index * 80}ms" data-color="{item['color']}">
          <div class="card-tag {item['color']}">{item['label']}</div>
          <p class="card-hook">{hook_preview}</p>
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


def build_deal_card(deal: dict, featured: bool = False, link_to_detail: bool = True) -> str:
    badge      = '<span class="deal-badge">🔥 Hot</span>' if featured else ''
    detail_url = f"deals/{deal['slug']}.html"
    dest       = detail_url if (link_to_detail and deal["slug"] != "check-back-soon") else deal["link"]
    btn_text   = "View Deal →" if link_to_detail else "Claim Deal →"
    return f"""
          <div class="deal-card{'  deal-featured' if featured else ''}">
            {badge}
            <div class="deal-meta"><span class="deal-sub">{deal['source']}</span></div>
            <p class="deal-title">{deal['title']}</p>
            <a href="{dest}" class="deal-btn">{btn_text}</a>
          </div>"""


def build_index_page(items: list[dict], deals: list[dict], ts: str) -> str:
    template  = load_template("index.html")
    arts_html = "\n".join(build_article_card(item, i) for i, item in enumerate(items))
    side_html = "\n".join(build_deal_card(d, featured=(i == 0)) for i, d in enumerate(deals[:3]))
    return (template
            .replace("{{ALL_ARTICLES}}",  arts_html)
            .replace("{{SIDEBAR_DEALS}}", side_html)
            .replace("{{LAST_UPDATED}}", ts)
            .replace("{{ARTICLE_COUNT}}", f"{len(items)} briefs · {len(deals)} deals")
            .replace("{{SITE_URL}}",      SITE_URL)
            .replace("{{ISO_DATE}}",      iso_date()))


def build_article_page(item: dict, ts: str) -> str:
    template = load_template("article.html")
    return (template
            .replace("{{TITLE}}",       item["title"])
            .replace("{{LABEL}}",       item["label"])
            .replace("{{COLOR}}",       item["color"])
            .replace("{{HOOK}}",        item.get("hook", ""))
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


def build_deal_detail_page(deal: dict, ts: str) -> str:
    template    = load_template("deal_detail.html")
    hi_html     = "\n".join(f"          <li>{h}</li>" for h in deal.get("highlights", []))
    amazon_link = deal.get("amazon_link") or deal["link"]
    return (template
            .replace("{{DEAL_TITLE}}",        deal["title"])
            .replace("{{DEAL_SOURCE}}",       deal["source"])
            .replace("{{DEAL_DESCRIPTION}}",  deal.get("ai_desc", ""))
            .replace("{{DEAL_HIGHLIGHTS}}",   hi_html)
            .replace("{{DEAL_AMAZON_LINK}}",  amazon_link)
            .replace("{{DEAL_SOURCE_LINK}}",  deal["link"])
            .replace("{{LAST_UPDATED}}",      ts)
            .replace("{{SITE_URL}}",          SITE_URL)
            .replace("{{ISO_DATE}}",          iso_date()))


def build_sitemap(items: list[dict], deals: list[dict]) -> str:
    today = iso_date()
    urls  = [SITE_URL + "/", SITE_URL + "/deals.html"]
    urls += [f"{SITE_URL}/articles/{item['slug']}.html" for item in items]
    urls += [f"{SITE_URL}/deals/{deal['slug']}.html" for deal in deals
             if deal["slug"] != "check-back-soon"]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append(
            f"  <url><loc>{u}</loc><lastmod>{today}</lastmod>"
            f"<changefreq>daily</changefreq></url>"
        )
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
    deals = process_all_deals(deals)

    print("\n── Building Pages ──────────────────────────────────────")
    write_file(ROOT / "index.html",  build_index_page(items, deals, ts))
    write_file(ROOT / "deals.html",  build_deals_page(deals, ts))
    write_file(ROOT / "sitemap.xml", build_sitemap(items, deals))

    for item in items:
        write_file(ARTICLES / f"{item['slug']}.html", build_article_page(item, ts))

    for deal in deals:
        if deal["slug"] != "check-back-soon":
            write_file(DEALS_DIR / f"{deal['slug']}.html", build_deal_detail_page(deal, ts))

    print("\n" + "=" * 56)
    print("  ✓ BUILD COMPLETE")
    print(f"  Articles   : {len(items)}")
    print(f"  Deals      : {len(deals)}")
    print(f"  Updated    : {ts}")
    print("=" * 56)
    print("\n  Open index.html in your browser to preview.\n")


if __name__ == "__main__":
    main()
