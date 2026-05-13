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
CANDIDATES_FILE    = Path("review_candidates.json")
MANUAL_BRIEFS_FILE = Path("manual_briefs.json")

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
    article_url   = f"{SITE_URL}/articles/{slug}.html"
    encoded_text  = urllib.parse.quote(f"{title} — Read the full brief: {article_url}")
    encoded_url   = urllib.parse.quote(article_url)
    encoded_title = urllib.parse.quote(title)
    return (
        f"https://wa.me/?text={encoded_text}",
        f"https://twitter.com/intent/tweet?text={encoded_text}",
        f"https://www.reddit.com/submit?url={encoded_url}&title={encoded_title}",
    )

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

# ─── ARTICLE BODY EXTRACTION (for richer AI context) ─────────────────────────

def extract_article_text(url, timeout=10, max_chars=3000):
    """Fetch the actual article page and return cleaned body text.

    RSS summaries are 150-400 chars and rarely contain the specific numbers,
    dates, or quotes the brief prompt needs to write good KEY_FACTS. Fetching
    the real article gives the LLM 10-20× more concrete data to work with —
    same number of AI calls, dramatically richer input.

    Returns "" on failure or paywall — caller should fall back to RSS summary.
    """
    raw = fetch_url(url, timeout=timeout)
    if not raw:
        return ""
    try:
        html = raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""

    # Strip non-content sections so they don't pollute the extracted text
    for tag in ("script", "style", "nav", "header", "footer", "aside",
                "form", "iframe", "noscript", "svg"):
        html = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", " ", html,
                       flags=re.IGNORECASE | re.DOTALL)

    # Prefer <article>, then <main>, then full body as fallback
    body = ""
    for pat in (r"<article\b[^>]*>(.*?)</article>",
                r"<main\b[^>]*>(.*?)</main>"):
        m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
        if m:
            body = m.group(1)
            break
    if not body:
        m = re.search(r"<body\b[^>]*>(.*?)</body>", html, re.IGNORECASE | re.DOTALL)
        body = m.group(1) if m else html

    text = re.sub(r"<[^>]+>", " ", body)
    text = (text
            .replace("&nbsp;", " ").replace("&amp;", "&")
            .replace("&quot;", '"').replace("&apos;", "'")
            .replace("&#8217;", "'").replace("&#8216;", "'")
            .replace("&#8220;", '"').replace("&#8221;", '"')
            .replace("&#8211;", "-").replace("&#8212;", "—")
            .replace("&#8230;", "..."))
    text = re.sub(r"\s+", " ", text).strip()

    # Paywalled / error pages typically return very little real text
    if len(text) < 500:
        return ""

    return text[:max_chars]

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

BRIEF_PROMPT = """You are the editor of CatchTheBrief, an Indian tech and startup news brief.
Audience: 25-35 year old founders, engineers, product managers, and investors in Bangalore, Mumbai, Delhi, Hyderabad, Pune.
Voice: A senior editor explaining a story to a sharp friend over coffee. Direct. Specific. Confident. Mildly opinionated.

You are NOT writing marketing copy. You are NOT writing a corporate blog. Strip every sentence that could appear in a press release.

═══════════════════════════════════════════════════════════════
ARTICLE TO BRIEF
═══════════════════════════════════════════════════════════════
TITLE: {title}
SOURCE: {source}
DESCRIPTION: {description}
URL: {url}

═══════════════════════════════════════════════════════════════
HARD BANS — NEVER USE THESE PHRASES OR PATTERNS ANYWHERE
═══════════════════════════════════════════════════════════════
• THE NEGATIVE-CONTRAST PATTERN — banned in EVERY tense and EVERY phrasing. NEVER write any sentence of the form "X [negation] just/merely/only/about Y; it's Z" or its grammatical cousins. Specifically banned negation verbs: isn't, is not, aren't, are not, wasn't, was not, weren't, were not, won't, will not, doesn't, does not, didn't, did not, hasn't, has not, haven't, have not. Specifically banned modifiers: just, merely, only, about. Examples ALL banned: "This isn't just X", "The bottleneck isn't just X", "It's not just A; it's B", "It won't just speed up X; it will Y", "Allianz doesn't just sell insurance; it…", "More than just". The contrast structure is the slop, not any single word — kill it at the root by writing positive, declarative sentences instead.
• Filler bridges: "This is a significant move" / NEVER start any sentence with "This move " followed by a verb (use "The move", "The deal", "The JV", or name the actual subject) / "This signals a shift" / "It's no surprise that" / "Make no mistake"
• Forced openers: "Imagine you're…" / "Picture this…" / "In a move that…" / "Get ready for…" / "Buckle up"
• Corporate-blog crutches: "Doubling down" / "Strategic vote of confidence" / "Shake up" / "Game-changing" / "Set to disrupt" / "Eyeing" / "Underscores" / "Cementing its position"
• Vague flattery: "India's booming startup ecosystem" / "India's growing tech ecosystem" / standalone "ecosystem" used as filler / "vibrant" / "bustling" / "robust" / "seamless" / "seamlessly" / "empowering" / "thriving" / "Indian readers"
• Exclamation marks anywhere.
• Rhetorical questions in HOOK or TAKE.
• Em-dashes are fine — use them naturally.

═══════════════════════════════════════════════════════════════
SECTION-BY-SECTION RULES
═══════════════════════════════════════════════════════════════

TITLE
   Max 12 words. Specific. Punchy. Include a number, a named entity, or a sharp verb.
   GOOD: "Flipkart Loses GST Battle: 18% Tax on Delivery Charges"
   BAD:  "Big GST News for Flipkart — What's Up?"

HOOK — 3 sentences.
   S1: Subject + verb + the most surprising number or fact. No preamble.
   S2: The angle — WHY this is interesting, concretely (a tension, a stake, a contrast).
   S3 (optional): One specific consequence or stakeholder named.
   GOOD: "Zoho put ₹70 crore into ONDC, its largest single bet on India's public commerce stack. The cheque lands four months after Reliance quietly scaled back its own ONDC pilot. For Tier-2 SMBs, the difference is paying 18% to Amazon versus 0.5% to ONDC."
   BAD:  "Zoho just dropped a significant ₹70 crore into ONDC. This move is all about empowering India's small businesses."

CONTEXT (How We Got Here) — 2 sentences.
   Must include AT LEAST ONE specific anchor: a prior date, a prior funding round, a named regulation, a named earlier event.
   Forbidden vague openers: "For years…" / "Consistently…" / "Historically…" / "Always known for…"
   GOOD: "JFS spun out of Reliance in August 2023 and got its NBFC licence within four months. The Allianz tie-up replaces its earlier exclusive arrangement with Bajaj Allianz, which ended in March 2026."
   BAD:  "JFS has been making aggressive moves since its spin-off, aiming to become a full-stack financial services powerhouse."

KEY_FACTS — 3 to 5 bullets. QUALITY OVER QUANTITY.
   RULES (all required):
   • Each fact MUST add information NOT already in the TITLE or HOOK.
   • Each fact MUST include at least one of: a number, a named person, a date, a regulator/entity name, a city, a product name, or a competitor name.
   • Background descriptions ("X is an Indian SaaS company") are NOT facts — DROP them.
   • If the source doesn't yield 5 distinct new facts, write 3 or 4. Do not pad.
   GOOD bullets:
      • "WBAAAR upheld the earlier WBAAR ruling from January 2026"
      • "The 18% rate matches standard service tax — appellate body treating Flipkart as a principal supplier, not a 'pure agent'"
      • "Amazon faces a similar pending ruling in Karnataka, expected June 2026"
   BAD bullets (do not write):
      • "Flipkart had argued these charges were reimbursements" (already in hook)
      • "The ruling is binding on Flipkart" (filler conclusion)
      • "GST stands for Goods and Services Tax" (definitional padding)

WHAT_NEXT (What Happens Next) — 2 sentences.
   Must name AT LEAST ONE concrete checkpoint: a specific date, a quarter, an upcoming event, a pending decision, a number to watch.
   Forbidden: "Keep an eye on…" / "We'll see…" / "Watch this space" / "Time will tell"
   GOOD: "Flipkart's appeal route now points to the High Court — expect a filing within 30 days. Amazon's Karnataka ruling is due in June; that's the one that turns this industry-wide."
   BAD:  "Keep an eye on how this impacts consumer delivery costs in the coming months."

WHY_INDIA — 1 sentence. Specific stakeholder + specific city/sector + specific impact.
   Must include AT LEAST ONE OF: a named non-metro city, a specific sector, a named reader cohort (founders, dev-tools buyers, FMCG SMBs, etc.).
   Forbidden: "India's growing/booming ecosystem", "huge for India", "across the country".
   GOOD: "For the 12 lakh Flipkart sellers in Surat, Ludhiana, and Coimbatore, an 18% delivery tax could compress already-thin margins by 200-400 bps."
   BAD:  "This ruling impacts India's massive e-commerce sector across cities like Bangalore, Mumbai, and Delhi."

TAKE — 1 to 2 sentences. This is the editorial differentiator. The one section that makes the brief worth reading.
   You MUST take a clear position. Pick ONE stance:
      (a) PREDICTION — what specifically happens in the next 3-12 months
      (b) CONTRARIAN — the consensus reading is wrong, here is why
      (c) WHO-WINS / WHO-LOSES — name the winner and the loser explicitly
      (d) WHAT'S BEING MISSED — the angle other coverage ignores
   FORBIDDEN openers: "This isn't just" / "This is more than just" / "More than" / "While X, Y also…"
   FORBIDDEN phrases: "strategic validation" / "vote of confidence" / "doubling down" / "shake up" / "game-changing"
   GOOD: "The losers here aren't Flipkart shareholders — they're the 5-person seller-side teams in Bhiwandi who'll absorb the cost. Watch Meesho move fast to differentiate on this within 60 days."
   BAD:  "This isn't just a tax adjustment; it's a clear signal from regulators that e-commerce giants aren't exempt."

═══════════════════════════════════════════════════════════════
OUTPUT — EXACT FORMAT. NO PREAMBLE. NO MARKDOWN BOLD/ITALICS.
═══════════════════════════════════════════════════════════════
TITLE: [rewritten headline, max 12 words]
CATEGORY: [exactly one of: AI & ML | Startup Funding | Digital India | Product Launch | India Tech]
READ_TIME: [e.g. "3 min read"]

HOOK: [3 sentences per HOOK rules]

CONTEXT: [2 sentences per CONTEXT rules]

KEY_FACTS:
• [fact 1 — new info, with number/name/date]
• [fact 2 — new info, with number/name/date]
• [fact 3 — new info, with number/name/date]
[optional fact 4 — only if genuinely additive]
[optional fact 5 — only if genuinely additive]

WHAT_NEXT: [2 sentences with at least one concrete checkpoint]

WHY_INDIA: [1 sentence per WHY_INDIA rules]

TAKE: [1-2 sentences taking a clear position per TAKE rules]"""

def parse_brief(raw_text):
    def strip_md(text):
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*',     r'\1', text)
        text = re.sub(r'__(.+?)__',     r'\1', text)
        text = re.sub(r'_(.+?)_',       r'\1', text)
        return text.strip()

    def get_section_raw(text, label, next_labels):
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

    def get_section(text, label, next_labels):
        return strip_md(get_section_raw(text, label, next_labels))

    def get_line(text, label):
        match = re.search(rf"^{label}:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
        return strip_md(match.group(1).strip()) if match else ""

    raw_facts = get_section_raw(raw_text, "KEY_FACTS", ["WHAT_NEXT", "WHY_INDIA", "TAKE"])

    return {
        "title":     get_line(raw_text, "TITLE")    or "Tech Brief",
        "category":  get_line(raw_text, "CATEGORY") or "India Tech",
        "read_time": get_line(raw_text, "READ_TIME") or "3 min read",
        "hook":      get_section(raw_text, "HOOK",      ["CONTEXT", "KEY_FACTS", "WHAT_NEXT", "WHY_INDIA", "TAKE"]),
        "context":   get_section(raw_text, "CONTEXT",   ["KEY_FACTS", "WHAT_NEXT", "WHY_INDIA", "TAKE"]),
        "what_next": get_section(raw_text, "WHAT_NEXT", ["WHY_INDIA", "TAKE", "SOURCE"]),
        "why_india": get_section(raw_text, "WHY_INDIA", ["TAKE", "SOURCE", "---"]) or get_line(raw_text, "WHY_INDIA"),
        "take":      get_section(raw_text, "TAKE",      ["SOURCE", "---"]) or get_line(raw_text, "TAKE"),
        "facts":     [strip_md(f) for f in re.findall(r"[•\-\*]\s*(.+)", raw_facts)][:5],
    }

# Lowercase substrings that count as "banned tells" if found in any generated
# section. Keep this conservative — only patterns that are nearly always slop.
# Order: structural patterns first, then specific phrases, then vague words.
BANNED_PHRASES = [
    # NOTE: the "X isn't Y; it's Z" structural pattern is handled by
    # ISN_T_PATTERN below — it catches all tenses (isn't/won't/wasn't/doesn't…)
    # plus all modifiers (just/merely/only/about) in one rule. Earlier we
    # listed literal variants here, but the model kept finding fresh tense
    # workarounds (v4: "isn't just" → v5: "won't just").
    "more than just",
    # Filler bridges. "this move " (with trailing space) catches every
    # "This move {verb}…" sentence — almost always corporate filler.
    "this is a significant move", "this move ", "this signals a shift",
    "make no mistake", "it's no surprise",
    # Forced openers
    "imagine you're", "picture this", "in a move that", "get ready for",
    "buckle up",
    # Corporate-blog crutches
    "doubling down", "strategic vote of confidence", "vote of confidence",
    "game-changing", "set to disrupt", "underscores",
    "cementing its position",
    # Vague flattery — single-word matches kept narrow to avoid false positives
    "booming startup ecosystem", "growing tech ecosystem",
    "seamlessly", "vibrant", "bustling",
]

# Catches the full "X (tense+negation) (modifier) Y; it's Z" pattern in any
# tense the model might try. Bullet-proof against future tense workarounds.
ISN_T_PATTERN = re.compile(
    r"\b(?:isn'?t|is\s+not|aren'?t|are\s+not"
    r"|wasn'?t|was\s+not|weren'?t|were\s+not"
    r"|won'?t|will\s+not"
    r"|doesn'?t|does\s+not|didn'?t|did\s+not"
    r"|hasn'?t|has\s+not|haven'?t|have\s+not)"
    r"\s+(?:just|merely|only|about)\b"
)

def find_banned(brief):
    """Return list of banned phrase/pattern hits across all brief sections."""
    sections = [
        brief.get("title", ""),
        brief.get("hook", ""),
        brief.get("context", ""),
        brief.get("what_next", ""),
        brief.get("why_india", ""),
        brief.get("take", ""),
    ]
    # Normalize curly apostrophes so "won't" (U+2019) and "won't" (ASCII)
    # both match the regex/literals uniformly.
    text = " ".join(sections).lower().replace("’", "'")
    hits = [p for p in BANNED_PHRASES if p in text]
    for m in ISN_T_PATTERN.finditer(text):
        hits.append(m.group(0))
    return hits


def load_manual_briefs():
    """Load manual_briefs.json as a URL-keyed dict. Never raises — returns {} on any error."""
    if not MANUAL_BRIEFS_FILE.exists():
        return {}
    try:
        data   = json.loads(MANUAL_BRIEFS_FILE.read_text(encoding="utf-8"))
        briefs = data.get("briefs", [])
        return {b["url"]: b for b in briefs if "url" in b}
    except Exception as e:
        print(f"  Warning: could not read manual_briefs.json: {e}")
        return {}

def generate_brief(candidate, gemini, groq, manual_briefs=None):
    # 1. Persistent editorial file (manual_briefs.json) — highest priority
    if manual_briefs and candidate.get("url") in manual_briefs:
        mb = manual_briefs[candidate["url"]]
        print(f"  Editorial override (manual_briefs.json): {mb.get('title', '')[:60]}")
        return {
            "title":       mb.get("title",       candidate["title"]),
            "category":    mb.get("category",    "India Tech"),
            "read_time":   mb.get("read_time",   "3 min read"),
            "hook":        mb.get("hook",        ""),
            "context":     mb.get("context",     ""),
            "facts":       mb.get("facts",       []),
            "what_next":   mb.get("what_next",   ""),
            "why_india":   mb.get("why_india",   ""),
            "take":        mb.get("take",        ""),
            "source_name": mb.get("source_name", candidate.get("source", "")),
            "source_link": mb.get("source_link", candidate.get("url", "")),
            "pub_date":    mb.get("pub_date",    ""),
        }

    # 2. Inline override from review_candidates.json
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
            "take":        mb.get("take",      ""),
            "source_name": mb.get("source_name", candidate.get("source", "")),
            "source_link": mb.get("source_link", candidate.get("url", "")),
            "pub_date":    mb.get("pub_date",  ""),
        }

    url    = candidate["url"]
    source = candidate["source"]

    # Pull the full article text so the AI has real data (numbers, dates, named
    # entities) to write specific KEY_FACTS — not just paraphrase the RSS blurb.
    article_text = extract_article_text(url)
    if article_text:
        print(f"  Fetched article body: {len(article_text)} chars")
        body_for_prompt = article_text
    else:
        body_for_prompt = candidate.get("summary", "")[:400]
        print(f"  Article fetch returned nothing — using RSS summary ({len(body_for_prompt)} chars)")

    prompt = BRIEF_PROMPT.format(
        title=candidate["title"], source=source,
        description=body_for_prompt, url=url,
    )
    response, ai_source = ai_call(prompt, gemini, groq)
    if response:
        brief = parse_brief(response)

        # Banned-phrase guard: if the draft contains slop tells, retry ONCE
        # with explicit callouts. Costs +1 AI call when triggered, ~0 most days.
        hits = find_banned(brief)
        if hits:
            print(f"  ⚠ Banned phrase(s) detected: {hits}. Retrying once.")
            retry_prompt = (
                prompt
                + "\n\n═══════════════════════════════════════════════════════════════\n"
                + "RETRY — YOUR PREVIOUS DRAFT VIOLATED THE BAN LIST\n"
                + "═══════════════════════════════════════════════════════════════\n"
                + f"Banned tokens found in your last response: {', '.join(hits)}\n"
                + "Rewrite the brief avoiding ALL banned phrases AND patterns above.\n"
                + "In particular: never open a sentence with 'This isn't' / 'This is not' / 'This move'.\n"
                + "Lead sentences with a subject (a company, a person, a number) and an active verb."
            )
            response2, _ = ai_call(retry_prompt, gemini, groq)
            if response2:
                brief2 = parse_brief(response2)
                hits2 = find_banned(brief2)
                if len(hits2) < len(hits):
                    print(f"  Retry kept: hits dropped {len(hits)} → {len(hits2)}")
                    brief = brief2
                else:
                    print(f"  Retry rejected (hits unchanged: {len(hits2)}). Using original.")

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
        "take": "", "source_name": source, "source_link": url, "pub_date": "",
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

def build_prev_next_nav(prev_slug, next_slug):
    if not prev_slug and not next_slug:
        return ""
    prev_part = (
        f'<a href="/articles/{prev_slug}.html" class="nav-btn nav-prev">← Previous Brief</a>'
        if prev_slug else '<span></span>'
    )
    next_part = (
        f'<a href="/articles/{next_slug}.html" class="nav-btn nav-next">Next Brief →</a>'
        if next_slug else '<span></span>'
    )
    return f'<nav class="article-nav">{prev_part}{next_part}</nav>'

def build_take_html(take_text):
    if not take_text:
        return ""
    return (
        '<div class="take-box">'
        '<div class="take-label">The Take</div>'
        f'<div class="take-text">{take_text}</div>'
        '</div>'
    )

def generate_article_page(brief, image_url, slug, article_index, total, prev_slug, next_slug, now):
    template_path = TEMPLATES_DIR / "article.html"
    if not template_path.exists():
        print(f"  WARNING: {template_path} not found")
        return None
    template  = template_path.read_text(encoding="utf-8")
    meta_desc = brief["hook"][:160].replace('"', "'")
    og_image  = image_url if image_url else f"{SITE_URL}/images/og-default.jpg"
    wa_url, tw_url, reddit_url = make_share_urls(brief["title"], slug)

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

    pub_date = brief.get("pub_date", "")
    pub_date_html = (
        f'<span class="meta-sep">·</span><span class="meta-item">{pub_date}</span>'
        if pub_date else ""
    )

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
        "{{PUB_DATE_HTML}}":   pub_date_html,
        "{{HERO_IMAGE_HTML}}": hero_image_html(image_url, brief["title"], brief["category"]),
        "{{HOOK}}":            brief["hook"].replace("\n", " "),
        "{{CONTEXT}}":         brief["context"].replace("\n", " "),
        "{{KEY_FACTS}}":       facts_to_html(brief["facts"]),
        "{{WHAT_NEXT}}":       brief["what_next"].replace("\n", " "),
        "{{WHY_INDIA}}":       brief["why_india"],
        "{{TAKE_SECTION}}":    build_take_html(brief.get("take", "")),
        "{{SOURCE_NAME}}":     brief["source_name"],
        "{{SOURCE_LINK}}":     brief["source_link"],
        "{{WHATSAPP_URL}}":    wa_url,
        "{{TWITTER_URL}}":     tw_url,
        "{{REDDIT_URL}}":      reddit_url,
        "{{IMAGE_URL}}":       image_url or get_default_image(brief["category"]),
        "{{IMAGE_ALT}}":       brief["title"],
        "{{ARTICLE_INDEX}}":   str(article_index),
        "{{TOTAL_ARTICLES}}":  str(total),
        "{{PREV_NAV}}":        build_prev_next_nav(prev_slug, next_slug),
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

    day_name  = now.strftime("%A")
    date_disp = f"{now.day} {now.strftime('%B')} {now.year}"
    date_display_html = (
        f'<div class="date-herald">'
        f'<div class="date-day">{day_name}, {date_disp}</div>'
        f'</div>'
    )

    replacements = {
        "{{ALL_ARTICLES}}":      build_all_articles_html(briefs_data),
        "{{LAST_UPDATED}}":      human_date(now),
        "{{ISO_DATE}}":          iso_date(now),
        "{{ARTICLE_COUNT}}":     count_str,
        "{{SITE_URL}}":          SITE_URL,
        "{{OG_IMAGE_HOME}}":     og_image_home,
        "{{YESTERDAY_BRIEFS}}":  generate_yesterday_teaser_html(now),
        "{{DATE_DISPLAY}}":      date_display_html,
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
        f'  <url><loc>{SITE_URL}/about.html</loc><lastmod>{iso_date(now)}</lastmod></url>',
        f'  <url><loc>{SITE_URL}/privacy.html</loc><lastmod>{iso_date(now)}</lastmod></url>',
    ]
    # Include all historical article pages, not just today's
    seen_slugs = set()
    if ARTICLES_DIR.exists():
        for html_file in sorted(ARTICLES_DIR.glob("*.html")):
            s = html_file.stem
            seen_slugs.add(s)
            lines.append(f'  <url><loc>{SITE_URL}/articles/{s}.html</loc><lastmod>{iso_date(now)}</lastmod></url>')
    # Add today's new slugs in case they haven't been written to disk yet
    for s in slugs:
        if s not in seen_slugs:
            seen_slugs.add(s)
            lines.append(f'  <url><loc>{SITE_URL}/articles/{s}.html</loc><lastmod>{iso_date(now)}</lastmod></url>')
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

    # ── Load editorial overrides ──────────────────────────────────────────────
    manual_briefs = load_manual_briefs()
    if manual_briefs:
        print(f"  manual_briefs.json loaded — {len(manual_briefs)} override(s) available")
    else:
        print("  manual_briefs.json empty — no overrides")

    # ── Generate briefs + AI images ───────────────────────────────────────────
    print(f"\n[Step 2] Generating {len(candidates)} enhanced briefs...")
    briefs_data = []
    date_str = iso_date(now)

    for i, candidate in enumerate(candidates):
        print(f"\n  Article {i+1}/{len(candidates)}: {candidate['title'][:70]}")
        brief     = generate_brief(candidate, gemini, groq, manual_briefs)
        slug      = date_slug(date_str, brief["title"])
        image_url = generate_ai_image_url(brief["title"], brief["category"], slug)
        print(f"  AI image URL generated (seed deterministic)")
        briefs_data.append((brief, image_url, slug))
        time.sleep(1.5)

    # ── Write article pages ───────────────────────────────────────────────────
    print("\n[Step 3] Writing article HTML pages...")
    for i, (brief, image_url, slug) in enumerate(briefs_data):
        prev_slug = briefs_data[i - 1][2] if i > 0 else ""
        next_slug = briefs_data[i + 1][2] if i + 1 < len(briefs_data) else ""
        html = generate_article_page(brief, image_url, slug, i + 1, len(briefs_data), prev_slug, next_slug, now)
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
