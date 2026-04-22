"""
CatchTheBrief — News Engine v5.0
Session 5: Design Overhaul (HTML generation updated to match new templates)
- India tech/startup RSS feeds (8 sources)
- Fetch wide: 15-20 articles from past 24 hours
- AI ranking: Gemini picks top 5 in ONE call
- Enhanced brief format: hook + context + 5 facts + what next + why India
- og:image extraction from source articles
- Unique meta tags per article
- Groq fallback when Gemini quota exhausted
- Session 5: Hero card + 2x2 grid layout on homepage
- Session 5: Progress bar, back-to-top, share buttons on article pages
- Session 5: New CSS classes matching Inter + Space Grotesk design system
"""

import os
import json
import time
import re
import urllib.parse
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── API imports ─────────────────────────────────────────────────────────────
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("google-genai not installed — Gemini unavailable")

try:
    import requests as req_lib
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("requests not installed — some features degraded")

# ─── CONFIG ──────────────────────────────────────────────────────────────────
SITE_URL = "https://catchthebrief.com"
SITE_NAME = "CatchTheBrief"
ARTICLES_DIR = Path("articles")
ARCHIVE_DIR = Path("archive")
TEMPLATES_DIR = Path("templates")
IMAGES_DIR = Path("images/defaults")

# India tech + startup RSS feeds (Session 3 decision)
RSS_FEEDS = [
    "https://techcrunch.com/tag/india/feed/",
    "https://yourstory.com/feed",
    "https://inc42.com/feed/",
    "https://entrackr.com/feed/",
    "https://the-ken.com/feed/",
    "https://feeds.feedburner.com/gadgets360-latest",
    "https://www.medianama.com/feed/",
    "https://analyticsindiamag.com/feed/",
]

# Gemini API keys — rotate on quota exhaustion
GEMINI_KEYS = [
    os.environ.get("GEMINI_API_KEY_1", ""),
    os.environ.get("GEMINI_API_KEY_2", ""),
    os.environ.get("GEMINI_API_KEY_3", ""),
]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]  # drop empties

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.5-flash"

# Category accent colors (for CSS class injection)
CATEGORY_COLORS = {
    "AI & ML": "ai",
    "Startup Funding": "startup",
    "Digital India": "policy",
    "Product Launch": "product",
    "India Tech": "funding",
}

IST = timezone(timedelta(hours=5, minutes=30))

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def ist_now():
    return datetime.now(IST)

def human_date(dt):
    day = dt.day
    month = dt.strftime("%B")
    year = dt.year
    hour = dt.strftime("%I").lstrip("0") or "12"
    minute = dt.strftime("%M")
    ampm = dt.strftime("%p")
    return f"{day} {month} {year}, {hour}:{minute} {ampm}"

def iso_date(dt):
    return dt.strftime("%Y-%m-%d")

def sanitize_filename(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:80]

def fetch_url(url, timeout=10):
    """Fetch URL bytes. Returns None on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CatchTheBrief/4.0 (+https://catchthebrief.com)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f"  fetch_url error {url}: {e}")
        return None

# ─── STEP 1: FETCH WIDE (15-20 articles) ─────────────────────────────────────

def parse_rss(raw_bytes):
    """Parse RSS/Atom XML. Returns list of dicts with title, link, description, pub_date."""
    articles = []
    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
        return articles

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)  # slightly generous

    # RSS 2.0
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        date_el = item.find("pubDate")

        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()
        description = (desc_el.text or "").strip() if desc_el is not None else ""
        pub_date_raw = (date_el.text or "").strip() if date_el is not None else ""

        # Strip HTML from description
        description = re.sub(r"<[^>]+>", "", description)[:400]

        # Parse pub date — skip old articles
        pub_dt = None
        for fmt in [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%dT%H:%M:%S%z",
        ]:
            try:
                pub_dt = datetime.strptime(pub_date_raw, fmt)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue

        if pub_dt and pub_dt < cutoff:
            continue  # too old

        if title and link:
            articles.append({
                "title": title,
                "link": link,
                "description": description,
                "pub_date": pub_date_raw,
                "pub_dt": pub_dt,
            })

    # Atom feeds
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link", ns)
        summary_el = entry.find("atom:summary", ns)
        date_el = entry.find("atom:published", ns) or entry.find("atom:updated", ns)

        title = (title_el.text or "").strip() if title_el is not None else ""
        link = link_el.get("href", "") if link_el is not None else ""
        description = (summary_el.text or "").strip() if summary_el is not None else ""
        description = re.sub(r"<[^>]+>", "", description)[:400]
        pub_date_raw = (date_el.text or "").strip() if date_el is not None else ""

        if title and link:
            articles.append({
                "title": title,
                "link": link,
                "description": description,
                "pub_date": pub_date_raw,
                "pub_dt": None,
            })

    return articles

def fetch_all_articles():
    """Pull from all RSS feeds. Return list of up to 25 unique articles."""
    all_articles = []
    seen_links = set()

    for feed_url in RSS_FEEDS:
        print(f"  Fetching: {feed_url}")
        raw = fetch_url(feed_url, timeout=15)
        if not raw:
            continue
        items = parse_rss(raw)
        for item in items:
            if item["link"] not in seen_links:
                seen_links.add(item["link"])
                all_articles.append(item)
        print(f"    → {len(items)} articles found")

    print(f"\nTotal unique articles fetched: {len(all_articles)}")
    return all_articles[:25]  # cap at 25

# ─── STEP 2: og:image EXTRACTION ─────────────────────────────────────────────

def extract_og_image(url):
    """Fetch article HTML and extract og:image. Returns image URL or None."""
    raw = fetch_url(url, timeout=8)
    if not raw:
        return None
    try:
        html = raw.decode("utf-8", errors="ignore")
    except Exception:
        return None

    # Look for og:image meta tag
    match = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()

    # Also try content-first format
    match = re.search(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        html, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()

    return None

def get_default_image(category):
    """Return a default image path based on category."""
    defaults = {
        "AI & ML": "/images/defaults/ai.jpg",
        "Startup Funding": "/images/defaults/startup.jpg",
        "Digital India": "/images/defaults/policy.jpg",
        "Product Launch": "/images/defaults/product.jpg",
        "India Tech": "/images/defaults/tech.jpg",
    }
    return defaults.get(category, "/images/defaults/tech.jpg")

# ─── AI CLIENTS ──────────────────────────────────────────────────────────────

class GeminiClient:
    def __init__(self, api_keys):
        self.keys = api_keys
        self.key_index = 0
        self._clients = {}  # reuse clients

    def call(self, prompt, retries=2):
        if not GENAI_AVAILABLE or not self.keys:
            return None

        for attempt in range(len(self.keys)):
            key = self.keys[self.key_index % len(self.keys)]
            
            # Reuse client instead of creating new one each call
            if key not in self._clients:
                self._clients[key] = genai.Client(api_key=key)
            client = self._clients[key]
            
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                )
                return response.text
            except Exception as e:
                err = str(e).lower()
                if "quota" in err or "429" in err or "resource_exhausted" in err:
                    print(f"  Gemini key {self.key_index+1} quota hit — rotating")
                    self.key_index += 1
                    time.sleep(2)
                else:
                    print(f"  Gemini error: {e}")
                    if retries > 0:
                        time.sleep(3)
                        retries -= 1
                    else:
                        break
        return None

class GroqClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def call(self, prompt):
        if not self.api_key:
            print("  Groq error: no API key set")
            return None
        try:
            import requests
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt[:6000]}],
                    "max_tokens": 1200,
                    "temperature": 0.7,
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  Groq error: {e}")
            return None

def ai_call(prompt, gemini: GeminiClient, groq: GroqClient):
    """Try Gemini first, fall back to Groq."""
    result = gemini.call(prompt)
    if result:
        return result, "gemini"
    print("  → Falling back to Groq")
    result = groq.call(prompt)
    if result:
        return result, "groq"
    return None, "none"

# ─── STEP 2: AI RANKING ──────────────────────────────────────────────────────
def filter_articles(articles):
    """Remove listicles, sponsored content, and off-topic articles."""
    junk_keywords = [
        "inspiring", "motivat", "books to read", "tips for", "how to be",
        "sponsored", "advertis", "partner content", "brand story",
        "zodiac", "horoscope", "recipe", "deal of the day",
    ]
    filtered = []
    for a in articles:
        title_lower = a["title"].lower()
        if any(kw in title_lower for kw in junk_keywords):
            print(f"  Filtered out: {a['title'][:60]}")
            continue
        filtered.append(a)
    print(f"  After filtering: {len(filtered)} articles remain")
    return filtered

def rank_articles(articles, gemini, groq):
    """Send all article headlines to Gemini for ranking. Returns list of top-5 indices."""
    # Only send top 15 to save tokens
    articles_to_rank = articles[:15]
    
    lines = []
    for i, a in enumerate(articles_to_rank):
        # Trim description to 60 chars to save tokens
        desc = a['description'][:60].replace('\n', ' ')
        lines.append(f"{i}: {a['title']} — {desc}")

    prompt = f"""You are the editor of CatchTheBrief, an Indian tech and startup news site.
Your readers are 25–35 year old professionals based in Indian cities — Bangalore, Mumbai, Delhi, Hyderabad, Pune.

Here are {len(articles)} articles from the past 24 hours:

{chr(10).join(lines)}

Your task: Pick the TOP 5 most valuable articles for our readers.

Ranking criteria:
1. IMPACT — Does this affect Indian tech workers, founders, or consumers?
2. NOVELTY — Is this genuinely new news, not a repeat of yesterday's story?
3. VARIETY — Pick from different sub-topics (funding, AI, policy, product, industry)
4. RELEVANCE — "Would a 28-year-old Bangalore software engineer or startup founder care?"
5. NO DUPLICATES — If 3 articles cover the same story, pick only the best one.

Respond in this EXACT format (no extra text):
TOP5: [index1, index2, index3, index4, index5]
REASON1: one line reason for index1
REASON2: one line reason for index2
REASON3: one line reason for index3
REASON4: one line reason for index4
REASON5: one line reason for index5"""

    response, source = ai_call(prompt, gemini, groq)
    if not response:
        print("  Ranking failed — using first 5 articles")
        return list(range(min(5, len(articles))))

    # Parse TOP5 line
    match = re.search(r"TOP5:\s*\[([0-9,\s]+)\]", response)
    if not match:
        print(f"  Could not parse ranking response:\n{response[:200]}")
        return list(range(min(5, len(articles))))

    try:
        indices = [int(x.strip()) for x in match.group(1).split(",")]
        indices = [i for i in indices if 0 <= i < len(articles)][:5]
        print(f"  AI selected articles: {indices} (via {source})")
        return indices
    except Exception as e:
        print(f"  Ranking parse error: {e}")
        return list(range(min(5, len(articles))))

# ─── STEP 3: ENHANCED BRIEF GENERATION ───────────────────────────────────────

BRIEF_PROMPT = """You are a writer for CatchTheBrief, an Indian tech news site.
Write in simple, conversational English — like explaining to a smart friend over chai.
No jargon. No corporate language. Keep it engaging and human.

Article to brief:
TITLE: {title}
SOURCE: {source}
DESCRIPTION: {description}
URL: {url}

Write a brief in this EXACT format (use the exact labels):

TITLE: [rewrite the headline to be punchy and engaging — max 12 words]
CATEGORY: [pick ONE: AI & ML | Startup Funding | Digital India | Product Launch | India Tech]
READ_TIME: [e.g. "3 min read"]

HOOK: [3-4 sentences. Story-style opening. Set the scene. Make the reader care. Friendly tone.]

CONTEXT: [2-3 sentences. What's the background? What led to this? Make it feel like insider knowledge.]

KEY_FACTS:
• [Concrete fact with number, name, or date]
• [Concrete fact with number, name, or date]
• [Concrete fact with number, name, or date]
• [Concrete fact with number, name, or date]
• [Concrete fact with number, name, or date]

WHAT_NEXT: [2-3 sentences. What to watch for. When? What will happen? Give readers a reason to follow up.]

WHY_INDIA: [1 sentence. Why does this specifically matter to Indian readers?]"""

def parse_brief(raw_text):
    """Parse structured brief by splitting on known section labels."""

    def get_section(text, label, next_labels):
        """Extract text between label and the next known label."""
        # Find where this label starts
        pattern = rf"^{label}:\s*"
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if not match:
            return ""
        start = match.end()

        # Find where next section starts
        end = len(text)
        for next_label in next_labels:
            next_match = re.search(rf"^{next_label}:", text[start:], re.IGNORECASE | re.MULTILINE)
            if next_match:
                end = min(end, start + next_match.start())

        return text[start:end].strip()

    # Single line fields
    def get_line(text, label):
        match = re.search(rf"^{label}:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    all_labels = ["TITLE", "CATEGORY", "READ_TIME", "HOOK", "CONTEXT", "KEY_FACTS", "WHAT_NEXT", "WHY_INDIA"]

    title     = get_line(raw_text, "TITLE")
    category  = get_line(raw_text, "CATEGORY")
    read_time = get_line(raw_text, "READ_TIME")
    hook      = get_section(raw_text, "HOOK",      ["CONTEXT", "KEY_FACTS", "WHAT_NEXT", "WHY_INDIA"])
    context   = get_section(raw_text, "CONTEXT",   ["KEY_FACTS", "WHAT_NEXT", "WHY_INDIA"])
    what_next = get_section(raw_text, "WHAT_NEXT", ["WHY_INDIA", "SOURCE"])
    why_india = get_section(raw_text, "WHY_INDIA", ["SOURCE", "---"])
    if not why_india:
        why_india = get_line(raw_text, "WHY_INDIA")

    # Facts — handles •, -, * bullets
    facts_raw = get_section(raw_text, "KEY_FACTS", ["WHAT_NEXT", "WHY_INDIA"])
    facts = re.findall(r"[•\-\*]\s*(.+)", facts_raw)

    return {
        "title":     title    or "Tech Brief",
        "category":  category or "India Tech",
        "read_time": read_time or "3 min read",
        "hook":      hook     or "",
        "context":   context  or "",
        "facts":     facts[:5],
        "what_next": what_next or "",
        "why_india": why_india or "",
    }

def generate_brief(article, gemini, groq):
    """Generate an enhanced brief for one article. Returns parsed brief dict."""
    # Extract source domain for display
    url = article["link"]
    domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    source = domain_match.group(1) if domain_match else url

    prompt = BRIEF_PROMPT.format(
        title=article["title"],
        source=source,
        description=article["description"][:400],
        url=url,
    )

    response, ai_source = ai_call(prompt, gemini, groq)

    if response:
        brief = parse_brief(response)
        brief["source_name"] = source
        brief["source_link"] = url
        brief["pub_date"] = article.get("pub_date", "")
        print(f"  Brief generated via {ai_source}: {brief['title'][:60]}")
        return brief

    # Fallback — use RSS content
    print("  All AI failed — using RSS fallback brief")
    return {
        "title": article["title"],
        "category": "India Tech",
        "read_time": "2 min read",
        "hook": article["description"][:300] if article["description"] else "Read the full story at the source link below.",
        "context": "This story is making waves in the Indian tech ecosystem.",
        "facts": [
            "Story sourced from " + source,
            "Published: " + article.get("pub_date", "today"),
            "Full details at the source link below",
            "Part of CatchTheBrief's India tech coverage",
            "Check back tomorrow for more tech briefs",
        ],
        "what_next": "Follow the source for updates on this developing story.",
        "why_india": "This story has direct relevance to India's growing tech ecosystem.",
        "source_name": source,
        "source_link": url,
        "pub_date": article.get("pub_date", ""),
    }

# ─── HTML GENERATION (Session 5) ─────────────────────────────────────────────

# Category → CSS badge class (matches .badge.ai / .badge.startup etc in new templates)
CATEGORY_CSS = {
    "AI & ML":          "ai",
    "Startup Funding":  "startup",
    "Digital India":    "policy",
    "Product Launch":   "product",
    "India Tech":       "funding",
}

# Emoji placeholder shown when og:image is not found
CATEGORY_EMOJI = {
    "AI & ML":          "🤖",
    "Startup Funding":  "💰",
    "Digital India":    "🇮🇳",
    "Product Launch":   "🚀",
    "India Tech":       "💻",
}

# Gradient background for emoji placeholder cards
CATEGORY_GRADIENT = {
    "AI & ML":          "background:linear-gradient(135deg,#EDE9FE,#DDD6FE);",
    "Startup Funding":  "background:linear-gradient(135deg,#D1FAE5,#A7F3D0);",
    "Digital India":    "background:linear-gradient(135deg,#FEE2E2,#FECACA);",
    "Product Launch":   "background:linear-gradient(135deg,#FEF3C7,#FDE68A);",
    "India Tech":       "background:linear-gradient(135deg,#DBEAFE,#BFDBFE);",
}

def color_class(category):
    """Return CSS badge class string for a given category."""
    return CATEGORY_CSS.get(category, "funding")

def facts_to_html(facts):
    """Convert facts list to <li> items — inserted into .facts-list in article.html."""
    if not facts:
        return "<li>See source article for full details</li>"
    return "\n".join(f"<li>{f}</li>" for f in facts)

def make_share_urls(title, slug):
    """Build WhatsApp and Twitter/X share URLs for an article."""
    article_url  = f"{SITE_URL}/articles/{slug}.html"
    encoded_text = urllib.parse.quote(f"{title} — Read the full brief: {article_url}")
    whatsapp_url = f"https://wa.me/?text={encoded_text}"
    twitter_url  = f"https://twitter.com/intent/tweet?text={encoded_text}"
    return whatsapp_url, twitter_url

def hero_image_html(image_url, image_alt, category):
    """
    Returns HTML for {{HERO_IMAGE_HTML}} in article.html.
    Shows <img> if URL exists, otherwise a gradient emoji placeholder.
    """
    if image_url:
        alt = (image_alt or "").replace('"', "&quot;")
        return f'<img src="{image_url}" alt="{alt}" loading="lazy">'
    emoji = CATEGORY_EMOJI.get(category, "📰")
    return f'<div class="hero-image-placeholder">{emoji}</div>'

def card_image_html(image_url, image_alt, category):
    """
    Returns HTML for the image area inside a homepage article card.
    Shows <img> if URL exists, otherwise a gradient emoji placeholder.
    """
    if image_url:
        alt = (image_alt or "").replace('"', "&quot;")
        return f'<img src="{image_url}" alt="{alt}" loading="lazy">'
    emoji    = CATEGORY_EMOJI.get(category, "📰")
    gradient = CATEGORY_GRADIENT.get(category, "background:#F0F4F8;")
    return f'<div class="card-img-placeholder" style="{gradient}">{emoji}</div>'

def generate_hero_card(brief, image_url, slug):
    """
    Build the large hero card (article #1) for index.html.
    Full-width split layout: image left, content right.
    """
    css     = color_class(brief["category"])
    img     = card_image_html(image_url, brief["title"], brief["category"])
    preview = brief["hook"][:200].strip()
    url     = f"/articles/{slug}.html"

    return f"""<a href="{url}" class="hero-card">
  <div class="hero-img-wrap">
    {img}
  </div>
  <div class="hero-content">
    <div class="hero-eyebrow">
      <span class="badge {css}">{brief["category"]}</span>
      <span class="read-time">{brief["read_time"]}</span>
    </div>
    <h2>{brief["title"]}</h2>
    <p class="hook-preview">{preview}</p>
    <span class="read-btn">Read brief <span class="arrow">→</span></span>
  </div>
</a>"""

def generate_grid_card(brief, image_url, slug):
    """
    Build a regular grid card (articles #2-5) for the 2×2 grid on index.html.
    """
    css     = color_class(brief["category"])
    img     = card_image_html(image_url, brief["title"], brief["category"])
    preview = brief["hook"][:140].strip()
    url     = f"/articles/{slug}.html"

    return f"""<a href="{url}" class="article-card">
  <div class="card-img-wrap">
    {img}
  </div>
  <div class="card-body">
    <div class="card-eyebrow">
      <span class="badge {css}">{brief["category"]}</span>
      <span class="read-time">{brief["read_time"]}</span>
    </div>
    <h3>{brief["title"]}</h3>
    <p class="card-preview">{preview}</p>
    <span class="card-read-link">Read brief →</span>
  </div>
</a>"""

def build_all_articles_html(briefs_data):
    """
    Assemble the full {{ALL_ARTICLES}} block for index.html:
      Article 0       → hero card (full width)
      Articles 1-2    → first .grid-2x2 row
      Articles 3-4    → second .grid-2x2 row
    briefs_data: list of (brief_dict, image_url, slug)
    """
    if not briefs_data:
        return '<p style="color:#718096;text-align:center;padding:40px 0;">No briefs today. Check back tomorrow!</p>'

    blocks = []

    # Hero card — article 0
    brief, image_url, slug = briefs_data[0]
    blocks.append(generate_hero_card(brief, image_url, slug))

    # Grid row 1 — articles 1 & 2
    row1 = briefs_data[1:3]
    if row1:
        cards = "\n".join(generate_grid_card(b, img, s) for b, img, s in row1)
        blocks.append(f'<div class="grid-2x2">\n{cards}\n</div>')

    # Grid row 2 — articles 3 & 4
    row2 = briefs_data[3:5]
    if row2:
        cards = "\n".join(generate_grid_card(b, img, s) for b, img, s in row2)
        blocks.append(f'<div class="grid-2x2">\n{cards}\n</div>')

    return "\n\n".join(blocks)

def generate_article_page(brief, image_url, image_alt, slug, article_index, total):
    """Render article.html template with all Session 5 injection tags."""
    template_path = TEMPLATES_DIR / "article.html"
    if not template_path.exists():
        print(f"  WARNING: {template_path} not found — skipping article page")
        return None

    template = template_path.read_text(encoding="utf-8")

    meta_desc    = brief["hook"][:160].replace('"', "'")
    og_image     = image_url or f"{SITE_URL}/images/defaults/tech.jpg"
    whatsapp_url, twitter_url = make_share_urls(brief["title"], slug)

    replacements = {
        "{{TITLE}}":            brief["title"],
        "{{META_DESCRIPTION}}": meta_desc,
        "{{OG_TITLE}}":         brief["title"],
        "{{OG_DESCRIPTION}}":   meta_desc,
        "{{OG_IMAGE}}":         og_image,
        "{{SITE_URL}}":         SITE_URL,
        "{{SLUG}}":             slug,
        "{{LABEL}}":            brief["category"],
        "{{COLOR}}":            color_class(brief["category"]),
        "{{READ_TIME}}":        brief["read_time"],
        "{{PUB_DATE}}":         brief.get("pub_date", ""),
        "{{HERO_IMAGE_HTML}}":  hero_image_html(image_url, brief["title"], brief["category"]),
        "{{HOOK}}":             brief["hook"].replace("\n", " "),
        "{{CONTEXT}}":          brief["context"].replace("\n", " "),
        "{{KEY_FACTS}}":        facts_to_html(brief["facts"]),
        "{{WHAT_NEXT}}":        brief["what_next"].replace("\n", " "),
        "{{WHY_INDIA}}":        brief["why_india"],
        "{{SOURCE_NAME}}":      brief["source_name"],
        "{{SOURCE_LINK}}":      brief["source_link"],
        "{{WHATSAPP_URL}}":     whatsapp_url,
        "{{TWITTER_URL}}":      twitter_url,
        # Legacy tags kept for backwards compatibility
        "{{IMAGE_URL}}":        image_url or get_default_image(brief["category"]),
        "{{IMAGE_ALT}}":        image_alt or brief["title"],
        "{{ARTICLE_INDEX}}":    str(article_index),
        "{{TOTAL_ARTICLES}}":   str(total),
    }

    html = template
    for tag, value in replacements.items():
        html = html.replace(tag, value)

    return html

def generate_homepage(briefs_data, now):
    """Render index.html with Session 5 hero card + 2×2 grid layout."""
    template_path = TEMPLATES_DIR / "index.html"
    if not template_path.exists():
        print(f"  WARNING: {template_path} not found")
        return None

    template = template_path.read_text(encoding="utf-8")

    count_str = f"{len(briefs_data)} brief{'s' if len(briefs_data) != 1 else ''}"

    replacements = {
        "{{ALL_ARTICLES}}":  build_all_articles_html(briefs_data),
        "{{LAST_UPDATED}}":  human_date(now),
        "{{ISO_DATE}}":      iso_date(now),
        "{{ARTICLE_COUNT}}": count_str,
        "{{SITE_URL}}":      SITE_URL,
    }

    html = template
    for tag, value in replacements.items():
        html = html.replace(tag, value)

    return html

def generate_sitemap(slugs, now):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    lines.append(f"  <url><loc>{SITE_URL}/</loc><lastmod>{iso_date(now)}</lastmod></url>")
    for slug in slugs:
        lines.append(
            f"  <url><loc>{SITE_URL}/articles/{slug}.html</loc>"
            f"<lastmod>{iso_date(now)}</lastmod></url>"
        )
    lines.append("</urlset>")
    return "\n".join(lines)

def save_archive(briefs_data, now):
    """Save today's briefs as JSON archive."""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    archive = {
        "date": iso_date(now),
        "generated_at": now.isoformat(),
        "briefs": [
            {
                "title": brief["title"],
                "category": brief["category"],
                "slug": slug,
                "source": brief["source_name"],
                "url": f"{SITE_URL}/articles/{slug}.html",
            }
            for brief, image_url, slug in briefs_data
        ]
    }
    path = ARCHIVE_DIR / f"{iso_date(now)}.json"
    path.write_text(json.dumps(archive, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Archive saved: {path}")

def generate_archive_index():
    """Read all archive JSON files and write archive/index.html."""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    json_files = sorted(ARCHIVE_DIR.glob("*.json"), reverse=True)
    if not json_files:
        print("  No archive files found — skipping archive index")
        return

    CATEGORY_CSS_MAP = {
        "AI & ML": "ai", "Startup Funding": "startup",
        "Digital India": "policy", "Product Launch": "product", "India Tech": "funding",
    }
    CATEGORY_LABEL_MAP = {
        "AI & ML": "AI &amp; ML", "Startup Funding": "Startup Funding",
        "Digital India": "Digital India", "Product Launch": "Product Launch", "India Tech": "India Tech",
    }

    day_blocks = []
    for i, jf in enumerate(json_files):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        date_str = data.get("date", "")
        briefs = data.get("briefs", [])
        # Format date nicely
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            nice_date = f"{dt.day} {dt.strftime('%B')}, {dt.year}"
        except Exception:
            nice_date = date_str

        delay = i * 0.05
        items = []
        for n, b in enumerate(briefs, 1):
            slug = b.get("slug", "")
            title = b.get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            source = b.get("source", "")
            cat = b.get("category", "India Tech")
            css = CATEGORY_CSS_MAP.get(cat, "funding")
            label = CATEGORY_LABEL_MAP.get(cat, cat)
            items.append(
                f'<li class="brief-item"><a class="brief-link" href="/articles/{slug}.html">'
                f'<span class="brief-num">{n}</span>'
                f'<div class="brief-info"><div class="brief-title">{title}</div>'
                f'<div class="brief-source">{source}</div></div>'
                f'<span class="brief-cat {css}">{label}</span>'
                f'<span class="brief-arrow">→</span></a></li>'
            )
        items_html = "\n        ".join(items)
        day_blocks.append(f"""    <div class="day-block" style="animation-delay:{delay:.2f}s">
      <div class="day-header">
        <span class="day-date">{nice_date}</span>
        <span class="day-count">{len(briefs)} briefs</span>
      </div>
      <ul class="brief-list">
        {items_html}
      </ul>
    </div>""")

    blocks_html = "\n\n".join(day_blocks)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Archive — CatchTheBrief</title>
  <meta name="description" content="Browse all past India tech &amp; startup briefs from CatchTheBrief.">
  <link rel="canonical" href="{SITE_URL}/archive/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-V6N03CT88P"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-V6N03CT88P');</script>
  <style>
    :root{{--bg-primary:#FAFAFA;--bg-card:#FFFFFF;--bg-accent:#F0F4F8;--text-primary:#1A1A2E;--text-secondary:#4A5568;--text-muted:#718096;--accent-primary:#2563EB;--border:#E2E8F0;--border-strong:#CBD5E0;--shadow-sm:0 1px 3px rgba(0,0,0,0.06);--shadow-md:0 4px 12px rgba(0,0,0,0.08);--font-head:'Space Grotesk',sans-serif;--font-body:'Inter',sans-serif;--max-w:860px;}}
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:var(--font-body);background:var(--bg-primary);color:var(--text-primary);line-height:1.6;-webkit-font-smoothing:antialiased;}}
    a{{color:inherit;text-decoration:none;}}
    header{{position:sticky;top:0;z-index:100;background:rgba(250,250,250,0.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);}}
    .header-inner{{max-width:var(--max-w);margin:0 auto;padding:0 20px;height:60px;display:flex;align-items:center;justify-content:space-between;gap:16px;}}
    .logo{{font-family:var(--font-head);font-size:20px;font-weight:700;letter-spacing:-0.5px;}}
    .logo span{{color:var(--accent-primary);}}
    .back-link{{display:inline-flex;align-items:center;gap:6px;font-family:var(--font-body);font-size:13px;font-weight:600;color:var(--text-secondary);padding:8px 16px;border:1.5px solid var(--border-strong);border-radius:999px;background:var(--bg-card);transition:color 0.2s,border-color 0.2s,background 0.2s;}}
    .back-link:hover{{color:var(--accent-primary);border-color:var(--accent-primary);background:#EFF6FF;}}
    main{{max-width:var(--max-w);margin:0 auto;padding:48px 20px 80px;}}
    .page-title{{font-family:var(--font-head);font-size:clamp(28px,4vw,40px);font-weight:700;letter-spacing:-0.8px;margin-bottom:8px;}}
    .page-subtitle{{font-size:16px;color:var(--text-muted);margin-bottom:48px;}}
    .day-block{{margin-bottom:40px;background:var(--bg-card);border:1px solid var(--border);border-radius:14px;overflow:hidden;box-shadow:var(--shadow-sm);transition:box-shadow 0.2s;animation:fadeUp 0.4s ease both;}}
    .day-block:hover{{box-shadow:var(--shadow-md);}}
    .day-header{{padding:18px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:12px;background:var(--bg-accent);}}
    .day-date{{font-family:var(--font-head);font-size:16px;font-weight:700;letter-spacing:-0.3px;}}
    .day-count{{font-size:12px;color:var(--text-muted);background:var(--border);padding:3px 10px;border-radius:999px;}}
    .brief-list{{list-style:none;}}
    .brief-item{{border-bottom:1px solid var(--border);}}
    .brief-item:last-child{{border-bottom:none;}}
    .brief-link{{display:flex;align-items:center;gap:14px;padding:14px 24px;transition:background 0.15s;}}
    .brief-link:hover{{background:#F7FAFF;}}
    .brief-num{{font-family:var(--font-head);font-size:12px;font-weight:700;color:var(--text-muted);min-width:20px;text-align:center;}}
    .brief-info{{flex:1;}}
    .brief-title{{font-size:15px;font-weight:600;color:var(--text-primary);line-height:1.4;margin-bottom:3px;}}
    .brief-source{{font-size:12px;color:var(--text-muted);}}
    .brief-cat{{display:inline-block;font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;padding:3px 8px;border-radius:999px;white-space:nowrap;}}
    .brief-cat.ai{{background:#EDE9FE;color:#7C3AED;}} .brief-cat.startup{{background:#D1FAE5;color:#059669;}} .brief-cat.policy{{background:#FEE2E2;color:#DC2626;}} .brief-cat.product{{background:#FEF3C7;color:#D97706;}} .brief-cat.funding{{background:#DBEAFE;color:#2563EB;}}
    .brief-arrow{{font-size:14px;color:var(--text-muted);flex-shrink:0;}}
    .brief-link:hover .brief-arrow{{color:var(--accent-primary);}}
    footer{{border-top:1px solid var(--border);padding:32px 20px;}}
    .footer-inner{{max-width:var(--max-w);margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;}}
    .footer-logo{{font-family:var(--font-head);font-size:16px;font-weight:700;}}
    .footer-logo span{{color:var(--accent-primary);}}
    .footer-tagline{{font-size:13px;color:var(--text-muted);margin-top:2px;}}
    .footer-links{{display:flex;gap:20px;list-style:none;}}
    .footer-links a{{font-size:13px;color:var(--text-muted);transition:color 0.2s;}}
    .footer-links a:hover{{color:var(--accent-primary);}}
    .footer-copy{{font-size:12px;color:var(--text-muted);text-align:center;margin-top:20px;}}
    @keyframes fadeUp{{from{{opacity:0;transform:translateY(12px);}}to{{opacity:1;transform:translateY(0);}}}}
    @media(max-width:640px){{main{{padding:32px 16px 60px;}}.brief-link{{padding:12px 16px;}}.day-header{{padding:14px 16px;}}.brief-cat{{display:none;}}}}
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <a href="/" class="logo">Catch<span>The</span>Brief</a>
      <a href="/" class="back-link">← Today's Briefs</a>
    </div>
  </header>
  <main>
    <h1 class="page-title">Archive</h1>
    <p class="page-subtitle">Every brief we've published — newest first.</p>
{blocks_html}
  </main>
  <footer>
    <div class="footer-inner">
      <div>
        <div class="footer-logo">Catch<span>The</span>Brief</div>
        <div class="footer-tagline">India's daily tech &amp; startup briefing</div>
      </div>
      <ul class="footer-links">
        <li><a href="/">Home</a></li>
        <li><a href="/archive/">Archive</a></li>
        <li><a href="https://buttondown.com/catchthebrief" target="_blank" rel="noopener">Newsletter</a></li>
      </ul>
    </div>
    <p class="footer-copy">© 2026 CatchTheBrief · Made with ☕ in India</p>
  </footer>
</body>
</html>"""

    out_path = ARCHIVE_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  Archive index written: {out_path} ({len(json_files)} days)")


def write_robots_txt():
    """Create robots.txt for Google crawling."""
    content = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
    Path("robots.txt").write_text(content)
    print("  robots.txt written")

# ─── MAIN ENGINE ──────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("CatchTheBrief News Engine v5.0")
    print(f"Run time: {human_date(ist_now())} IST")
    print("=" * 60)

    # Check keys
    if not GEMINI_KEYS:
        print("WARNING: No Gemini API keys found in environment")
    if not GROQ_API_KEY:
        print("WARNING: No Groq API key found in environment")

    gemini = GeminiClient(GEMINI_KEYS)
    groq = GroqClient(GROQ_API_KEY)

    # Setup dirs
    ARTICLES_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)

    # ── Step 1: Fetch wide ────────────────────────────────────────────────────
    print("\n[Step 1] Fetching articles from RSS feeds...")
    articles = fetch_all_articles()

    if len(articles) < 3:
        print("ERROR: Too few articles fetched. Exiting.")
        return

    # ── Step 2: AI Ranking ────────────────────────────────────────────────────
    print(f"\n[Step 2] AI ranking {len(articles)} articles → top 5...")
    articles = filter_articles(articles)
    top_indices = rank_articles(articles, gemini, groq)
    top_articles = [articles[i] for i in top_indices]

    # ── Step 3: Generate briefs + extract images ───────────────────────────────
    print("\n[Step 3] Generating enhanced briefs...")
    briefs_data = []  # list of (brief_dict, image_url, slug)

    for i, article in enumerate(top_articles):
        print(f"\n  Article {i+1}/5: {article['title'][:70]}")

        # Generate brief
        brief = generate_brief(article, gemini, groq)

        # Extract og:image
        print(f"  Extracting image from {article['link'][:60]}...")
        image_url = extract_og_image(article["link"])
        if image_url:
            print(f"  Image found: {image_url[:60]}")
        else:
            print(f"  No og:image — will use default")
            image_url = get_default_image(brief["category"])

        image_alt = brief["title"]
        slug = sanitize_filename(brief["title"])

        briefs_data.append((brief, image_url, slug))
        time.sleep(1.5)  # be polite to APIs

    # ── Step 4: Write article HTML pages ─────────────────────────────────────
    print("\n[Step 4] Writing article HTML pages...")
    for i, (brief, image_url, slug) in enumerate(briefs_data):
        html = generate_article_page(brief, image_url, brief["title"], slug, i + 1, len(briefs_data))
        if html:
            out_path = ARTICLES_DIR / f"{slug}.html"
            out_path.write_text(html, encoding="utf-8")
            print(f"  Written: articles/{slug}.html")

    # ── Step 5: Write homepage ────────────────────────────────────────────────
    print("\n[Step 5] Writing homepage...")
    now = ist_now()
    homepage_html = generate_homepage(briefs_data, now)
    if homepage_html:
        Path("index.html").write_text(homepage_html, encoding="utf-8")
        print("  Written: index.html")

    # ── Step 6: Write sitemap ─────────────────────────────────────────────────
    slugs = [slug for _, _, slug in briefs_data]
    sitemap = generate_sitemap(slugs, now)
    Path("sitemap.xml").write_text(sitemap, encoding="utf-8")
    print("  Written: sitemap.xml")

    # ── Step 7: Save archive ──────────────────────────────────────────────────
    save_archive(briefs_data, now)

    # ── Step 8: Archive index ─────────────────────────────────────────────────
    generate_archive_index()

    # ── Step 9: robots.txt ────────────────────────────────────────────────────
    write_robots_txt()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"✅ Done! {len(briefs_data)} briefs published.")
    for brief, _, slug in briefs_data:
        print(f"   [{brief['category']}] {brief['title'][:55]}")
    print("=" * 60)


# ─── DEALS SECTION (PAUSED — Session 3) ──────────────────────────────────────
# DO NOT DELETE — re-enable after 500+ daily readers
#
# def fetch_deals():
#     """Fetch deals from Indian deal RSS feeds."""
#     pass
#
# def generate_deals_page(deals):
#     """Generate deals.html from deal data."""
#     pass
#
# DEALS_FEEDS = [
#     "https://www.desidime.com/feed",
#     "https://www.slickdeals.net/newsearch.php?mode=rss&searchin=1&q=india",
# ]
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
