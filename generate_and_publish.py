"""
CatchTheBrief — Step 2: Generate & Publish
Session 7: Runs at 8:00 AM IST (2:30 AM UTC) daily.
Reads review_candidates.json (manually reviewed or auto-ranked),
generates 5 enhanced briefs, builds all HTML pages, publishes site.

Session 7 changes:
- Date-prefixed article slugs: YYYY-MM-DD-title.html
- Per-day archive pages: archive/YYYY-MM-DD.html
- Yesterday's briefs teaser on homepage
- AI-generated images via Pollinations.AI (no source og:image scraping)
- SEO: JSON-LD NewsArticle schema, og:site_name, og:locale, og:image on homepage, favicon
"""

import os
import json
import time
import re
import hashlib
import urllib.parse
import xml.etree.ElementTree as ET
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("google-genai not installed — Gemini unavailable")

# ─── CONFIG ──────────────────────────────────────────────────────────────────
SITE_URL        = "https://catchthebrief.com"
SITE_NAME       = "CatchTheBrief"
ARTICLES_DIR    = Path("articles")
ARCHIVE_DIR     = Path("archive")
TEMPLATES_DIR   = Path("templates")
CANDIDATES_FILE = Path("review_candidates.json")

GEMINI_KEYS = [k for k in [
    os.environ.get("GEMINI_API_KEY_1", ""),
    os.environ.get("GEMINI_API_KEY_2", ""),
    os.environ.get("GEMINI_API_KEY_3", ""),
] if k]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.5-flash"
IST = timezone(timedelta(hours=5, minutes=30))

CATEGORY_CSS = {
    "AI & ML": "ai", "Startup Funding": "startup",
    "Digital India": "policy", "Product Launch": "product", "India Tech": "funding",
}
CATEGORY_EMOJI = {
    "AI & ML": "🤖", "Startup Funding": "💰",
    "Digital India": "🇮🇳", "Product Launch": "🚀", "India Tech": "💻",
}
CATEGORY_GRADIENT = {
    "AI & ML":         "background:linear-gradient(135deg,#EDE9FE,#DDD6FE);",
    "Startup Funding": "background:linear-gradient(135deg,#D1FAE5,#A7F3D0);",
    "Digital India":   "background:linear-gradient(135deg,#FEE2E2,#FECACA);",
    "Product Launch":  "background:linear-gradient(135deg,#FEF3C7,#FDE68A);",
    "India Tech":      "background:linear-gradient(135deg,#DBEAFE,#BFDBFE);",
}

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def ist_now():
    return datetime.now(IST)

def human_date(dt):
    hour = dt.strftime("%I").lstrip("0") or "12"
    return f"{dt.day} {dt.strftime('%B')} {dt.year}, {hour}:{dt.strftime('%M')} {dt.strftime('%p')}"

def iso_date(dt):
    return dt.strftime("%Y-%m-%d")

def sanitize_filename(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:80]

def date_slug(date_str, title):
    """Return a date-prefixed slug: 2026-04-23-my-title"""
    return f"{date_str}-{sanitize_filename(title)}"

def fetch_url(url, timeout=10):
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "CatchTheBrief/7.0 (+https://catchthebrief.com)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f"  fetch_url error {url}: {e}")
        return None

def color_class(category):
    return CATEGORY_CSS.get(category, "funding")

def facts_to_html(facts):
    if not facts:
        return "<li>See source article for full details</li>"
    return "\n".join(f"<li>{f}</li>" for f in facts)

def make_share_urls(title, slug):
    article_url  = f"{SITE_URL}/articles/{slug}.html"
    encoded_text = urllib.parse.quote(f"{title} — Read the full brief: {article_url}")
    return f"https://wa.me/?text={encoded_text}", f"https://twitter.com/intent/tweet?text={encoded_text}"

def hero_image_html(image_url, image_alt, category):
    if image_url:
        return f'<img src="{image_url}" alt="{(image_alt or "").replace(chr(34), "&quot;")}" loading="lazy">'
    return f'<div class="hero-image-placeholder">{CATEGORY_EMOJI.get(category, "📰")}</div>'

def card_image_html(image_url, image_alt, category):
    if image_url:
        return f'<img src="{image_url}" alt="{(image_alt or "").replace(chr(34), "&quot;")}" loading="lazy">'
    emoji    = CATEGORY_EMOJI.get(category, "📰")
    gradient = CATEGORY_GRADIENT.get(category, "background:#F0F4F8;")
    return f'<div class="card-img-placeholder" style="{gradient}">{emoji}</div>'

def get_default_image(category):
    defaults = {
        "AI & ML":         "/images/defaults/ai.jpg",
        "Startup Funding": "/images/defaults/startup.jpg",
        "Digital India":   "/images/defaults/policy.jpg",
        "Product Launch":  "/images/defaults/product.jpg",
        "India Tech":      "/images/defaults/tech.jpg",
    }
    return defaults.get(category, "/images/defaults/tech.jpg")

# ─── AI IMAGE GENERATION (Pollinations.AI) ───────────────────────────────────

def generate_ai_image_url(title, category, slug):
    """Return a deterministic Pollinations.AI image URL for an article.

    Uses slug as the seed source so the same article always gets the same image.
    The URL is embedded directly in HTML — no file download needed.
    Pollinations caches by prompt+seed, so repeat page loads are fast.
    """
    hints = {
        "AI & ML":         "artificial intelligence India technology abstract blue modern",
        "Startup Funding": "India startup business funding investment growth modern",
        "Digital India":   "India digital innovation technology government modern",
        "Product Launch":  "India tech product launch innovation modern design",
        "India Tech":      "India technology industry digital innovation modern",
    }
    hint  = hints.get(category, "India technology news modern digital")
    clean = re.sub(r"[^a-zA-Z0-9 ]", " ", title)[:50].strip()
    prompt  = f"{clean} {hint} editorial illustration flat design"
    encoded = urllib.parse.quote(prompt)
    seed    = int(hashlib.md5(slug.encode()).hexdigest()[:6], 16) % 99999 + 1
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1200&height=630&nologo=true&seed={seed}"
    )

# ─── og:image EXTRACTION (kept as utility, unused in main flow) ───────────────

def extract_og_image(url):
    raw = fetch_url(url, timeout=8)
    if not raw:
        return None
    try:
        html = raw.decode("utf-8", errors="ignore")
    except Exception:
        return None
    for pattern in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ]:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

# ─── AI CLIENTS ──────────────────────────────────────────────────────────────

class GeminiClient:
    def __init__(self, api_keys):
        self.keys = api_keys
        self.key_index = 0
        self._clients = {}

    def call(self, prompt, retries=2):
        if not GENAI_AVAILABLE or not self.keys:
            return None
        for _ in range(len(self.keys)):
            key = self.keys[self.key_index % len(self.keys)]
            if key not in self._clients:
                self._clients[key] = genai.Client(api_key=key)
            client = self._clients[key]
            try:
                response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
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
            return None
        try:
            import requests
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt[:6000]}],
                      "max_tokens": 1200, "temperature": 0.7},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  Groq error: {e}")
            return None

def ai_call(prompt, gemini, groq):
    result = gemini.call(prompt)
    if result:
        return result, "gemini"
    print("  → Falling back to Groq")
    result = groq.call(prompt)
    if result:
        return result, "groq"
    return None, "none"

# ─── BRIEF GENERATION ────────────────────────────────────────────────────────

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

WHAT_NEXT: [2-3 sentences. What to watch for. When? What will happen?]

WHY_INDIA: [1 sentence. Why does this specifically matter to Indian readers?]"""

def parse_brief(raw_text):
    def get_section(text, label, next_labels):
        match = re.search(rf"^{label}:\s*", text, re.IGNORECASE | re.MULTILINE)
        if not match:
            return ""
        start = match.end()
        end = len(text)
        for nl in next_labels:
            nm = re.search(rf"^{nl}:", text[start:], re.IGNORECASE | re.MULTILINE)
            if nm:
                end = min(end, start + nm.start())
        return text[start:end].strip()

    def get_line(text, label):
        match = re.search(rf"^{label}:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    return {
        "title":     get_line(raw_text, "TITLE")    or "Tech Brief",
        "category":  get_line(raw_text, "CATEGORY") or "India Tech",
        "read_time": get_line(raw_text, "READ_TIME") or "3 min read",
        "hook":      get_section(raw_text, "HOOK",      ["CONTEXT", "KEY_FACTS", "WHAT_NEXT", "WHY_INDIA"]),
        "context":   get_section(raw_text, "CONTEXT",   ["KEY_FACTS", "WHAT_NEXT", "WHY_INDIA"]),
        "what_next": get_section(raw_text, "WHAT_NEXT", ["WHY_INDIA", "SOURCE"]),
        "why_india": get_section(raw_text, "WHY_INDIA", ["SOURCE", "---"]) or get_line(raw_text, "WHY_INDIA"),
        "facts":     re.findall(r"[•\-\*]\s*(.+)", get_section(raw_text, "KEY_FACTS", ["WHAT_NEXT", "WHY_INDIA"]))[:5],
    }

def generate_brief(candidate, gemini, groq):
    if "manual_brief" in candidate:
        mb = candidate["manual_brief"]
        print(f"  Manual brief: {mb.get('title', '')[:60]}")
        return {
            "title":       mb.get("title",     candidate["title"]),
            "category":    mb.get("category",  "India Tech"),
            "read_time":   mb.get("read_time", "3 min read"),
            "hook":        mb.get("hook",      ""),
            "context":     mb.get("context",   ""),
            "facts":       mb.get("facts",     []),
            "what_next":   mb.get("what_next", ""),
            "why_india":   mb.get("why_india", ""),
            "source_name": mb.get("source_name", candidate.get("source", "")),
            "source_link": mb.get("source_link", candidate.get("url", "")),
            "pub_date":    mb.get("pub_date",  ""),
        }

    url    = candidate["url"]
    source = candidate["source"]
    prompt = BRIEF_PROMPT.format(
        title=candidate["title"], source=source,
        description=candidate.get("summary", "")[:400], url=url,
    )
    response, ai_source = ai_call(prompt, gemini, groq)
    if response:
        brief = parse_brief(response)
        brief["source_name"] = source
        brief["source_link"] = url
        brief["pub_date"]    = ""
        print(f"  Brief via {ai_source}: {brief['title'][:60]}")
        return brief

    print("  All AI failed — using fallback brief")
    return {
        "title": candidate["title"], "category": "India Tech", "read_time": "2 min read",
        "hook": candidate.get("summary", "Read the full story at the source link below.")[:300],
        "context": "This story is making waves in the Indian tech ecosystem.",
        "facts": [f"Story sourced from {source}", "See source for full details",
                  "Part of CatchTheBrief's India tech coverage",
                  "Check back tomorrow for more", "Follow the source for updates"],
        "what_next": "Follow the source for updates on this developing story.",
        "why_india": "This story has direct relevance to India's growing tech ecosystem.",
        "source_name": source, "source_link": url, "pub_date": "",
    }

# ─── HTML GENERATION ─────────────────────────────────────────────────────────

def generate_hero_card(brief, image_url, slug):
    css     = color_class(brief["category"])
    img     = card_image_html(image_url, brief["title"], brief["category"])
    preview = brief["hook"][:200].strip()
    cat     = brief["category"].replace("&", "&amp;")
    return f"""<a href="/articles/{slug}.html" class="hero-card">
  <div class="hero-img-wrap">{img}</div>
  <div class="hero-content">
    <div class="hero-eyebrow">
      <span class="badge {css}">{cat}</span>
      <span class="read-time">{brief["read_time"]}</span>
    </div>
    <h2>{brief["title"]}</h2>
    <p class="hook-preview">{preview}</p>
    <span class="read-btn">Read brief <span class="arrow">→</span></span>
  </div>
</a>"""

def generate_grid_card(brief, image_url, slug):
    css     = color_class(brief["category"])
    img     = card_image_html(image_url, brief["title"], brief["category"])
    preview = brief["hook"][:140].strip()
    cat     = brief["category"].replace("&", "&amp;")
    return f"""<a href="/articles/{slug}.html" class="article-card">
  <div class="card-img-wrap">{img}</div>
  <div class="card-body">
    <div class="card-eyebrow">
      <span class="badge {css}">{cat}</span>
      <span class="read-time">{brief["read_time"]}</span>
    </div>
    <h3>{brief["title"]}</h3>
    <p class="card-preview">{preview}</p>
    <span class="card-read-link">Read brief →</span>
  </div>
</a>"""

def build_all_articles_html(briefs_data):
    if not briefs_data:
        return '<p style="color:#718096;text-align:center;padding:40px 0;">No briefs today. Check back tomorrow!</p>'
    blocks = []
    brief, image_url, slug = briefs_data[0]
    blocks.append(generate_hero_card(brief, image_url, slug))
    for row in [briefs_data[1:3], briefs_data[3:5]]:
        if row:
            cards = "\n".join(generate_grid_card(b, img, s) for b, img, s in row)
            blocks.append(f'<div class="grid-2x2">\n{cards}\n</div>')
    return "\n\n".join(blocks)

def get_yesterday_data(now):
    """Return archive JSON data for the most recent day strictly before today."""
    today_str  = iso_date(now)
    json_files = sorted(ARCHIVE_DIR.glob("*.json"), reverse=True) if ARCHIVE_DIR.exists() else []
    for jf in json_files:
        if jf.stem < today_str:
            try:
                return json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                return None
    return None

def generate_yesterday_teaser_html(now):
    """Generate HTML for the 'Yesterday's Briefs' teaser on the homepage."""
    data = get_yesterday_data(now)
    if not data:
        return ""
    briefs   = data.get("briefs", [])
    date_str = data.get("date", "")
    if not briefs:
        return ""
    try:
        dt        = datetime.strptime(date_str, "%Y-%m-%d")
        nice_date = f"{dt.day} {dt.strftime('%B')}, {dt.year}"
    except Exception:
        nice_date = date_str

    items_html = ""
    for b in briefs:
        slug  = b.get("slug", "")
        title = b.get("title", "").replace("&", "&amp;").replace("<", "&lt;")
        cat   = b.get("category", "India Tech")
        css   = CATEGORY_CSS.get(cat, "funding")
        label = cat.replace("&", "&amp;")
        items_html += (
            f'    <li class="yday-item">'
            f'<a href="/articles/{slug}.html" class="yday-link">'
            f'<span class="yday-title">{title}</span>'
            f'<span class="badge {css}">{label}</span>'
            f'</a></li>\n'
        )

    day_link = f'/archive/{date_str}.html' if date_str else '/archive/'
    return (
        f'<div class="yesterday-section">\n'
        f'  <div class="section-intro" style="margin-top:48px;">\n'
        f'    <h2>Yesterday\'s Briefs</h2>\n'
        f'    <a href="{day_link}" class="brief-count yday-date-link">{nice_date}</a>\n'
        f'  </div>\n'
        f'  <ul class="yday-list">\n{items_html}  </ul>\n'
        f'  <div class="yday-footer">'
        f'<a href="/archive/" class="yday-archive-link">Browse all archives →</a>'
        f'</div>\n'
        f'</div>\n'
    )

def generate_article_page(brief, image_url, slug, article_index, total, now):
    template_path = TEMPLATES_DIR / "article.html"
    if not template_path.exists():
        print(f"  WARNING: {template_path} not found")
        return None
    template  = template_path.read_text(encoding="utf-8")
    meta_desc = brief["hook"][:160].replace('"', "'")
    og_image  = image_url if image_url else f"{SITE_URL}/images/og-default.jpg"
    wa_url, tw_url = make_share_urls(brief["title"], slug)

    json_ld_data = {
        "@context": "https://schema.org",
        "@type":    "NewsArticle",
        "headline": brief["title"],
        "description": meta_desc,
        "image":    og_image,
        "datePublished": iso_date(now),
        "dateModified":  iso_date(now),
        "author":    {"@type": "Organization", "name": SITE_NAME},
        "publisher": {
            "@type": "Organization",
            "name":  SITE_NAME,
            "logo":  {"@type": "ImageObject", "url": f"{SITE_URL}/favicon.svg"},
        },
        "url": f"{SITE_URL}/articles/{slug}.html",
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id":   f"{SITE_URL}/articles/{slug}.html",
        },
    }

    replacements = {
        "{{TITLE}}":           brief["title"],
        "{{META_DESCRIPTION}}": meta_desc,
        "{{OG_TITLE}}":        brief["title"],
        "{{OG_DESCRIPTION}}":  meta_desc,
        "{{OG_IMAGE}}":        og_image,
        "{{SITE_URL}}":        SITE_URL,
        "{{SLUG}}":            slug,
        "{{LABEL}}":           brief["category"].replace("&", "&amp;"),
        "{{COLOR}}":           color_class(brief["category"]),
        "{{READ_TIME}}":       brief["read_time"],
        "{{PUB_DATE}}":        brief.get("pub_date", ""),
        "{{HERO_IMAGE_HTML}}": hero_image_html(image_url, brief["title"], brief["category"]),
        "{{HOOK}}":            brief["hook"].replace("\n", " "),
        "{{CONTEXT}}":         brief["context"].replace("\n", " "),
        "{{KEY_FACTS}}":       facts_to_html(brief["facts"]),
        "{{WHAT_NEXT}}":       brief["what_next"].replace("\n", " "),
        "{{WHY_INDIA}}":       brief["why_india"],
        "{{SOURCE_NAME}}":     brief["source_name"],
        "{{SOURCE_LINK}}":     brief["source_link"],
        "{{WHATSAPP_URL}}":    wa_url,
        "{{TWITTER_URL}}":     tw_url,
        "{{IMAGE_URL}}":       image_url or get_default_image(brief["category"]),
        "{{IMAGE_ALT}}":       brief["title"],
        "{{ARTICLE_INDEX}}":   str(article_index),
        "{{TOTAL_ARTICLES}}":  str(total),
        "{{JSON_LD}}":         json.dumps(json_ld_data, ensure_ascii=False),
    }
    html = template
    for tag, value in replacements.items():
        html = html.replace(tag, value)
    return html

def generate_homepage(briefs_data, now):
    template_path = TEMPLATES_DIR / "index.html"
    if not template_path.exists():
        print(f"  WARNING: {template_path} not found")
        return None
    template  = template_path.read_text(encoding="utf-8")
    count_str = f"{len(briefs_data)} brief{'s' if len(briefs_data) != 1 else ''}"

    # Use the first article's AI image as the homepage og:image (already an absolute URL)
    og_image_home = f"{SITE_URL}/images/og-default.jpg"
    if briefs_data and briefs_data[0][1]:
        og_image_home = briefs_data[0][1]

    replacements = {
        "{{ALL_ARTICLES}}":      build_all_articles_html(briefs_data),
        "{{LAST_UPDATED}}":      human_date(now),
        "{{ISO_DATE}}":          iso_date(now),
        "{{ARTICLE_COUNT}}":     count_str,
        "{{SITE_URL}}":          SITE_URL,
        "{{OG_IMAGE_HOME}}":     og_image_home,
        "{{YESTERDAY_BRIEFS}}":  generate_yesterday_teaser_html(now),
    }
    html = template
    for tag, value in replacements.items():
        html = html.replace(tag, value)
    return html

def generate_sitemap(slugs, now):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f'  <url><loc>{SITE_URL}/</loc><lastmod>{iso_date(now)}</lastmod></url>',
        f'  <url><loc>{SITE_URL}/archive/</loc><lastmod>{iso_date(now)}</lastmod></url>',
    ]
    for slug in slugs:
        lines.append(f'  <url><loc>{SITE_URL}/articles/{slug}.html</loc><lastmod>{iso_date(now)}</lastmod></url>')
    if ARCHIVE_DIR.exists():
        for jf in sorted(ARCHIVE_DIR.glob("*.json")):
            date = jf.stem
            lines.append(f'  <url><loc>{SITE_URL}/archive/{date}.html</loc><lastmod>{date}</lastmod></url>')
    lines.append('</urlset>')
    return "\n".join(lines)

def save_archive(briefs_data, now):
    ARCHIVE_DIR.mkdir(exist_ok=True)
    archive = {
        "date":         iso_date(now),
        "generated_at": now.isoformat(),
        "briefs": [
            {
                "title":    brief["title"],
                "category": brief["category"],
                "slug":     slug,
                "source":   brief["source_name"],
                "url":      f"{SITE_URL}/articles/{slug}.html",
            }
            for brief, image_url, slug in briefs_data
        ],
    }
    path = ARCHIVE_DIR / f"{iso_date(now)}.json"
    path.write_text(json.dumps(archive, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Archive saved: {path}")
    return archive

# ─── ARCHIVE PAGE SHELL (shared by index + day pages) ────────────────────────

def _archive_page_html(title, description, canonical, og_title, content_html):
    """Shared HTML shell for all archive pages."""
    return f"""<!DOCTYPE html>
<html lang="en-IN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta property="og:title" content="{og_title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical}">
  <meta property="og:site_name" content="CatchTheBrief">
  <meta property="og:locale" content="en_IN">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
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
    .page-nav{{margin-bottom:24px;}}
    .page-title{{font-family:var(--font-head);font-size:clamp(28px,4vw,40px);font-weight:700;letter-spacing:-0.8px;margin-bottom:8px;}}
    .page-subtitle{{font-size:16px;color:var(--text-muted);margin-bottom:40px;}}
    .day-block{{margin-bottom:40px;background:var(--bg-card);border:1px solid var(--border);border-radius:14px;overflow:hidden;box-shadow:var(--shadow-sm);transition:box-shadow 0.2s;animation:fadeUp 0.4s ease both;}}
    .day-block:hover{{box-shadow:var(--shadow-md);}}
    .day-header{{padding:18px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:12px;background:var(--bg-accent);}}
    .day-date{{font-family:var(--font-head);font-size:16px;font-weight:700;letter-spacing:-0.3px;}}
    .day-date a{{color:inherit;}}.day-date a:hover{{color:var(--accent-primary);}}
    .day-count{{font-size:12px;color:var(--text-muted);background:var(--border);padding:3px 10px;border-radius:999px;}}
    .brief-list{{list-style:none;}}
    .brief-item{{border-bottom:1px solid var(--border);}}.brief-item:last-child{{border-bottom:none;}}
    .brief-link{{display:flex;align-items:center;gap:14px;padding:14px 24px;transition:background 0.15s;}}
    .brief-link:hover{{background:#F7FAFF;}}
    .brief-num{{font-family:var(--font-head);font-size:12px;font-weight:700;color:var(--text-muted);min-width:20px;text-align:center;}}
    .brief-info{{flex:1;}}
    .brief-title{{font-size:15px;font-weight:600;color:var(--text-primary);line-height:1.4;margin-bottom:3px;}}
    .brief-source{{font-size:12px;color:var(--text-muted);}}
    .brief-cat{{display:inline-block;font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;padding:3px 8px;border-radius:999px;white-space:nowrap;}}
    .brief-cat.ai{{background:#EDE9FE;color:#7C3AED;}}.brief-cat.startup{{background:#D1FAE5;color:#059669;}}.brief-cat.policy{{background:#FEE2E2;color:#DC2626;}}.brief-cat.product{{background:#FEF3C7;color:#D97706;}}.brief-cat.funding{{background:#DBEAFE;color:#2563EB;}}
    .brief-arrow{{font-size:14px;color:var(--text-muted);flex-shrink:0;}}
    .brief-link:hover .brief-arrow{{color:var(--accent-primary);}}
    footer{{border-top:1px solid var(--border);padding:32px 20px;}}
    .footer-inner{{max-width:var(--max-w);margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;}}
    .footer-logo{{font-family:var(--font-head);font-size:16px;font-weight:700;}}.footer-logo span{{color:var(--accent-primary);}}
    .footer-tagline{{font-size:13px;color:var(--text-muted);margin-top:2px;}}
    .footer-links{{display:flex;gap:20px;list-style:none;}}.footer-links a{{font-size:13px;color:var(--text-muted);transition:color 0.2s;}}.footer-links a:hover{{color:var(--accent-primary);}}
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
{content_html}
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
        <li><a href="/#newsletter">Newsletter</a></li>
      </ul>
    </div>
    <p class="footer-copy">© 2026 CatchTheBrief · Made with ☕ in India</p>
  </footer>
</body>
</html>"""

def generate_day_archive_page(archive_data):
    """Generate archive/YYYY-MM-DD.html for a single day."""
    date_str = archive_data.get("date", "")
    briefs   = archive_data.get("briefs", [])
    try:
        dt        = datetime.strptime(date_str, "%Y-%m-%d")
        nice_date = f"{dt.day} {dt.strftime('%B')}, {dt.year}"
    except Exception:
        nice_date = date_str

    items = []
    for n, b in enumerate(briefs, 1):
        slug   = b.get("slug", "")
        title  = b.get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        source = b.get("source", "")
        cat    = b.get("category", "India Tech")
        css    = CATEGORY_CSS.get(cat, "funding")
        label  = cat.replace("&", "&amp;")
        items.append(
            f'<li class="brief-item"><a class="brief-link" href="/articles/{slug}.html">'
            f'<span class="brief-num">{n}</span>'
            f'<div class="brief-info"><div class="brief-title">{title}</div>'
            f'<div class="brief-source">{source}</div></div>'
            f'<span class="brief-cat {css}">{label}</span>'
            f'<span class="brief-arrow">→</span></a></li>'
        )

    brief_word = "brief" if len(briefs) == 1 else "briefs"
    content = (
        f'    <div class="page-nav"><a href="/archive/" class="back-link">← All Archives</a></div>\n'
        f'    <h1 class="page-title">{nice_date}</h1>\n'
        f'    <p class="page-subtitle">{len(briefs)} {brief_word} published</p>\n'
        f'    <div class="day-block" style="animation-delay:0s">\n'
        f'      <ul class="brief-list">{"".join(items)}</ul>\n'
        f'    </div>'
    )
    html = _archive_page_html(
        title       = f"{nice_date} — CatchTheBrief",
        description = f"5 India tech &amp; startup briefs from {nice_date} — CatchTheBrief.",
        canonical   = f"{SITE_URL}/archive/{date_str}.html",
        og_title    = f"{nice_date} — CatchTheBrief",
        content_html = content,
    )
    out = ARCHIVE_DIR / f"{date_str}.html"
    out.write_text(html, encoding="utf-8")
    print(f"  Day archive written: archive/{date_str}.html")

def generate_archive_index():
    """Read all archive JSON files and regenerate archive/index.html."""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    json_files = sorted(ARCHIVE_DIR.glob("*.json"), reverse=True)
    if not json_files:
        return

    day_blocks = []
    for i, jf in enumerate(json_files):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        date_str = data.get("date", "")
        briefs   = data.get("briefs", [])
        try:
            dt        = datetime.strptime(date_str, "%Y-%m-%d")
            nice_date = f"{dt.day} {dt.strftime('%B')}, {dt.year}"
        except Exception:
            nice_date = date_str

        delay = i * 0.05
        items = []
        for n, b in enumerate(briefs, 1):
            slug   = b.get("slug", "")
            title  = b.get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            source = b.get("source", "")
            cat    = b.get("category", "India Tech")
            css    = CATEGORY_CSS.get(cat, "funding")
            label  = cat.replace("&", "&amp;")
            items.append(
                f'<li class="brief-item"><a class="brief-link" href="/articles/{slug}.html">'
                f'<span class="brief-num">{n}</span>'
                f'<div class="brief-info"><div class="brief-title">{title}</div>'
                f'<div class="brief-source">{source}</div></div>'
                f'<span class="brief-cat {css}">{label}</span>'
                f'<span class="brief-arrow">→</span></a></li>'
            )

        date_label = (
            f'<a href="/archive/{date_str}.html">{nice_date}</a>'
            if date_str else nice_date
        )
        day_blocks.append(
            f'    <div class="day-block" style="animation-delay:{delay:.2f}s">\n'
            f'      <div class="day-header">\n'
            f'        <span class="day-date">{date_label}</span>\n'
            f'        <span class="day-count">{len(briefs)} briefs</span>\n'
            f'      </div>\n'
            f'      <ul class="brief-list">{"".join(items)}</ul>\n'
            f'    </div>'
        )

    content = (
        f'    <h1 class="page-title">Archive</h1>\n'
        f'    <p class="page-subtitle">Every brief we\'ve published — newest first.</p>\n'
        + "\n".join(day_blocks)
    )
    html = _archive_page_html(
        title        = "Archive — CatchTheBrief",
        description  = "Browse all past India tech &amp; startup briefs from CatchTheBrief.",
        canonical    = f"{SITE_URL}/archive/",
        og_title     = "Archive — CatchTheBrief",
        content_html = content,
    )
    out_path = ARCHIVE_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  Archive index written ({len(json_files)} days)")

def write_robots_txt():
    Path("robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    )
    print("  robots.txt written")

# ─── READ CANDIDATES ─────────────────────────────────────────────────────────

def read_candidates():
    if not CANDIDATES_FILE.exists():
        print("ERROR: review_candidates.json not found. Run fetch_and_rank.py first.")
        return None, False
    data = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
    manually_reviewed = data.get("manually_reviewed", False)
    top_5 = data.get("top_5", [])
    if manually_reviewed:
        print(f"  Manually reviewed — using Rajneesh's top 5 selection")
    else:
        print(f"  Auto-ranked — using AI's top 5 selection")
    return top_5, manually_reviewed

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("CatchTheBrief — Generate & Publish (Session 7, Step 2)")
    print(f"Run time: {ist_now().strftime('%d %b %Y, %I:%M %p')} IST")
    print("=" * 60)

    if not GEMINI_KEYS:
        print("WARNING: No Gemini API keys found")
    if not GROQ_API_KEY:
        print("WARNING: No Groq API key found")

    gemini = GeminiClient(GEMINI_KEYS)
    groq   = GroqClient(GROQ_API_KEY)

    ARTICLES_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)

    now = ist_now()

    # ── Read candidates ───────────────────────────────────────────────────────
    print("\n[Step 1] Reading review_candidates.json...")
    candidates, manually_reviewed = read_candidates()
    if not candidates:
        return

    # ── Generate briefs + AI images ───────────────────────────────────────────
    print(f"\n[Step 2] Generating {len(candidates)} enhanced briefs...")
    briefs_data = []
    date_str = iso_date(now)

    for i, candidate in enumerate(candidates):
        print(f"\n  Article {i+1}/{len(candidates)}: {candidate['title'][:70]}")
        brief     = generate_brief(candidate, gemini, groq)
        slug      = date_slug(date_str, brief["title"])
        image_url = generate_ai_image_url(brief["title"], brief["category"], slug)
        print(f"  AI image URL generated (seed deterministic)")
        briefs_data.append((brief, image_url, slug))
        time.sleep(1.5)

    # ── Write article pages ───────────────────────────────────────────────────
    print("\n[Step 3] Writing article HTML pages...")
    for i, (brief, image_url, slug) in enumerate(briefs_data):
        html = generate_article_page(brief, image_url, slug, i + 1, len(briefs_data), now)
        if html:
            out_path = ARTICLES_DIR / f"{slug}.html"
            out_path.write_text(html, encoding="utf-8")
            print(f"  Written: articles/{slug}.html")

    # ── Write homepage ────────────────────────────────────────────────────────
    print("\n[Step 4] Writing homepage...")
    homepage_html = generate_homepage(briefs_data, now)
    if homepage_html:
        Path("index.html").write_text(homepage_html, encoding="utf-8")
        print("  Written: index.html")

    # ── Sitemap ───────────────────────────────────────────────────────────────
    slugs = [slug for _, _, slug in briefs_data]
    Path("sitemap.xml").write_text(generate_sitemap(slugs, now), encoding="utf-8")
    print("  Written: sitemap.xml")

    # ── Archive ───────────────────────────────────────────────────────────────
    archive_data = save_archive(briefs_data, now)
    generate_day_archive_page(archive_data)
    generate_archive_index()

    # ── robots.txt ────────────────────────────────────────────────────────────
    write_robots_txt()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"✅ Done! {len(briefs_data)} briefs published.")
    reviewed_str = "manually reviewed" if manually_reviewed else "auto-ranked"
    print(f"   Source: {reviewed_str} candidates")
    for brief, _, slug in briefs_data:
        print(f"   [{brief['category']}] {brief['title'][:55]}")
    print("=" * 60)


if __name__ == "__main__":
    main()
