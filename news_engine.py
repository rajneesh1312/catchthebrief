"""
CatchTheBrief — News Engine v4.0
Session 4: Content Engine Rewrite
- India tech/startup RSS feeds (8 sources)
- Fetch wide: 15-20 articles from past 24 hours
- AI ranking: Gemini picks top 5 in ONE call
- Enhanced brief format: hook + context + 5 facts + what next + why India
- og:image extraction from source articles
- Unique meta tags per article
- Groq fallback when Gemini quota exhausted
"""

import os
import json
import time
import re
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

# ─── HTML GENERATION ──────────────────────────────────────────────────────────

def color_class(category):
    return CATEGORY_COLORS.get(category, "funding")

def facts_to_html(facts):
    if not facts:
        return "<li>See source article for full details</li>"
    return "\n".join(f"<li>{f}</li>" for f in facts)

def share_text(title):
    encoded = urllib.parse.quote(f"{title} — {SITE_URL}")
    return encoded

try:
    import urllib.parse
except ImportError:
    pass

def generate_article_page(brief, image_url, image_alt, slug, article_index, total):
    """Render article.html template with brief content."""
    template_path = TEMPLATES_DIR / "article.html"
    if not template_path.exists():
        print(f"  WARNING: {template_path} not found — skipping article page")
        return None

    template = template_path.read_text(encoding="utf-8")

    meta_desc = brief["hook"][:160].replace('"', "'")
    og_title = brief["title"]
    og_desc = meta_desc
    share_encoded = urllib.parse.quote(f"{brief['title']} — Read the full brief: {SITE_URL}/articles/{slug}.html")
    whatsapp_url = f"https://wa.me/?text={share_encoded}"
    twitter_url = f"https://twitter.com/intent/tweet?text={share_encoded}"

    replacements = {
        "{{TITLE}}": brief["title"],
        "{{META_DESCRIPTION}}": meta_desc,
        "{{OG_TITLE}}": og_title,
        "{{OG_DESCRIPTION}}": og_desc,
        "{{OG_IMAGE}}": image_url or f"{SITE_URL}/images/defaults/tech.jpg",
        "{{SITE_URL}}": SITE_URL,
        "{{LABEL}}": brief["category"],
        "{{COLOR}}": color_class(brief["category"]),
        "{{READ_TIME}}": brief["read_time"],
        "{{IMAGE_URL}}": image_url or get_default_image(brief["category"]),
        "{{IMAGE_ALT}}": image_alt or brief["title"],
        "{{HOOK}}": brief["hook"].replace("\n", " "),
        "{{CONTEXT}}": brief["context"].replace("\n", " "),
        "{{KEY_FACTS}}": facts_to_html(brief["facts"]),
        "{{WHAT_NEXT}}": brief["what_next"].replace("\n", " "),
        "{{WHY_INDIA}}": brief["why_india"],
        "{{SOURCE_NAME}}": brief["source_name"],
        "{{SOURCE_LINK}}": brief["source_link"],
        "{{PUB_DATE}}": brief["pub_date"],
        "{{WHATSAPP_URL}}": whatsapp_url,
        "{{TWITTER_URL}}": twitter_url,
        "{{ARTICLE_INDEX}}": str(article_index),
        "{{TOTAL_ARTICLES}}": str(total),
    }

    html = template
    for tag, value in replacements.items():
        html = html.replace(tag, value)

    return html

def article_card_html(brief, image_url, slug, is_hero=False):
    """Generate article card HTML for homepage."""
    color = color_class(brief["category"])
    hook_preview = brief["hook"][:120] + "…" if len(brief["hook"]) > 120 else brief["hook"]
    img_tag = ""
    if image_url:
        img_tag = f'<img src="{image_url}" alt="{brief["title"]}" loading="lazy">'
    else:
        img_tag = f'<div class="card-img-placeholder"></div>'

    hero_class = " hero-card" if is_hero else ""
    return f"""<article class="article-card{hero_class}">
  <a href="/articles/{slug}.html">
    <div class="card-img">{img_tag}</div>
    <div class="card-body">
      <span class="badge badge-{color}">{brief["category"]}</span>
      <span class="read-time">{brief["read_time"]}</span>
      <h2 class="card-title">{brief["title"]}</h2>
      <p class="card-preview">{hook_preview}</p>
    </div>
  </a>
</article>"""

def generate_homepage(briefs_data, now):
    """Render index.html template."""
    template_path = TEMPLATES_DIR / "index.html"
    if not template_path.exists():
        print(f"  WARNING: {template_path} not found")
        return None

    template = template_path.read_text(encoding="utf-8")

    cards_html = ""
    for i, (brief, image_url, slug) in enumerate(briefs_data):
        cards_html += article_card_html(brief, image_url, slug, is_hero=(i == 0))
        cards_html += "\n"

    replacements = {
        "{{ALL_ARTICLES}}": cards_html,
        "{{LAST_UPDATED}}": human_date(now),
        "{{ISO_DATE}}": iso_date(now),
        "{{ARTICLE_COUNT}}": f"{len(briefs_data)} briefs",
        "{{SITE_URL}}": SITE_URL,
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
    print("CatchTheBrief News Engine v4.0")
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

    # ── Step 8: robots.txt ────────────────────────────────────────────────────
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
