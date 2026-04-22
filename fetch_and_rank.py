"""
CatchTheBrief — Step 1: Fetch & Rank
Session 6: Runs at 10:00 PM IST (4:30 PM UTC) daily.
Fetches articles from RSS, applies source diversity filter, AI-ranks top 15,
saves review_candidates.json. Rajneesh reviews before 8 AM IST.
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

# ─── CONFIG ──────────────────────────────────────────────────────────────────
SITE_URL  = "https://catchthebrief.com"
CANDIDATES_FILE = Path("review_candidates.json")

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

GEMINI_KEYS = [k for k in [
    os.environ.get("GEMINI_API_KEY_1", ""),
    os.environ.get("GEMINI_API_KEY_2", ""),
    os.environ.get("GEMINI_API_KEY_3", ""),
] if k]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.5-flash"
IST = timezone(timedelta(hours=5, minutes=30))

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def ist_now():
    return datetime.now(IST)

def fetch_url(url, timeout=15):
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "CatchTheBrief/6.0 (+https://catchthebrief.com)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f"  fetch_url error {url}: {e}")
        return None

# ─── STEP 1: FETCH ───────────────────────────────────────────────────────────

def parse_rss(raw_bytes):
    articles = []
    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
        return articles

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)

    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el  = item.find("link")
        desc_el  = item.find("description")
        date_el  = item.find("pubDate")

        title       = (title_el.text or "").strip()
        link        = (link_el.text  or "").strip()
        description = re.sub(r"<[^>]+>", "", (desc_el.text or "") if desc_el is not None else "")[:400]
        pub_date_raw = (date_el.text or "").strip() if date_el is not None else ""

        pub_dt = None
        for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT", "%Y-%m-%dT%H:%M:%S%z"]:
            try:
                pub_dt = datetime.strptime(pub_date_raw, fmt)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue

        if pub_dt and pub_dt < cutoff:
            continue
        if title and link:
            articles.append({"title": title, "link": link, "description": description,
                              "pub_date": pub_date_raw, "pub_dt": pub_dt})

    for entry in root.findall("atom:entry", ns):
        title_el   = entry.find("atom:title", ns)
        link_el    = entry.find("atom:link", ns)
        summary_el = entry.find("atom:summary", ns)
        date_el    = entry.find("atom:published", ns) or entry.find("atom:updated", ns)

        title       = (title_el.text  or "").strip() if title_el is not None else ""
        link        = link_el.get("href", "") if link_el is not None else ""
        description = re.sub(r"<[^>]+>", "", (summary_el.text or "") if summary_el is not None else "")[:400]
        pub_date_raw = (date_el.text or "").strip() if date_el is not None else ""

        if title and link:
            articles.append({"title": title, "link": link, "description": description,
                              "pub_date": pub_date_raw, "pub_dt": None})
    return articles

def fetch_all_articles():
    all_articles = []
    seen_links = set()
    for feed_url in RSS_FEEDS:
        print(f"  Fetching: {feed_url}")
        raw = fetch_url(feed_url)
        if not raw:
            continue
        items = parse_rss(raw)
        for item in items:
            if item["link"] not in seen_links:
                seen_links.add(item["link"])
                all_articles.append(item)
        print(f"    → {len(items)} articles")
    print(f"\nTotal unique articles: {len(all_articles)}")
    return all_articles[:25]

# ─── STEP 2: FILTER JUNK ─────────────────────────────────────────────────────

def filter_articles(articles):
    junk_keywords = [
        "inspiring", "motivat", "books to read", "tips for", "how to be",
        "sponsored", "advertis", "partner content", "brand story",
        "zodiac", "horoscope", "recipe", "deal of the day",
    ]
    filtered = []
    for a in articles:
        if any(kw in a["title"].lower() for kw in junk_keywords):
            print(f"  Filtered junk: {a['title'][:60]}")
            continue
        filtered.append(a)
    print(f"  After junk filter: {len(filtered)} remain")
    return filtered

# ─── STEP 2b: SOURCE DIVERSITY ────────────────────────────────────────────────

def source_diversity_filter(articles, max_per_source=3):
    """Keep up to max_per_source articles per domain, sorted newest-first.
    This keeps the candidate pool large enough for AI ranking while preventing
    one source from dominating. The AI ranking prompt enforces final-5 diversity."""
    domain_buckets = {}
    for a in articles:
        m = re.search(r"https?://(?:www\.)?([^/]+)", a["link"])
        domain = m.group(1) if m else "unknown"
        domain_buckets.setdefault(domain, []).append(a)

    diverse = []
    for domain, items in domain_buckets.items():
        # Sort newest first (articles with pub_dt None go last)
        items_sorted = sorted(items, key=lambda x: x["pub_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        kept = items_sorted[:max_per_source]
        diverse.extend(kept)
        if len(items) > max_per_source:
            print(f"    {domain}: kept {max_per_source}/{len(items)} articles")

    removed = len(articles) - len(diverse)
    print(f"  After source diversity filter: {len(diverse)} remain ({removed} excess duplicates removed, max {max_per_source}/source)")
    return diverse

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
                      "max_tokens": 800, "temperature": 0.5},
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

# ─── STEP 3: AI RANKING ──────────────────────────────────────────────────────

def rank_articles(articles, gemini, groq):
    articles_to_rank = articles[:15]
    lines = []
    for i, a in enumerate(articles_to_rank):
        desc = a["description"][:60].replace("\n", " ")
        lines.append(f"{i}: {a['title']} — {desc}")

    prompt = f"""You are the editor of CatchTheBrief, an Indian tech and startup news site.
Readers: 25-35 year old professionals in Bangalore, Mumbai, Delhi, Hyderabad, Pune.

Here are {len(articles_to_rank)} articles from the past 24 hours:

{chr(10).join(lines)}

Pick the TOP 5 most valuable articles. Criteria:
1. IMPACT — affects Indian tech workers, founders, or consumers
2. NOVELTY — genuinely new news, not a repeat
3. VARIETY — IMPORTANT: the 5 selected articles MUST span at least 3 different sub-topics
   (e.g. funding, AI, policy, product launch, industry). Do NOT select more than 1 article
   about the same event or funding round.
4. RELEVANCE — "Would a 28-year-old Bangalore engineer or startup founder care?"
5. NO DUPLICATES — if multiple articles cover the same story, pick only the best one

Respond in EXACT format (no extra text):
TOP5: [index1, index2, index3, index4, index5]
REASON1: one line reason
REASON2: one line reason
REASON3: one line reason
REASON4: one line reason
REASON5: one line reason"""

    response, source = ai_call(prompt, gemini, groq)
    if not response:
        print("  Ranking failed — using first 5 articles")
        return list(range(min(5, len(articles))))

    match = re.search(r"TOP5:\s*\[([0-9,\s]+)\]", response)
    if not match:
        print(f"  Cannot parse ranking:\n{response[:200]}")
        return list(range(min(5, len(articles))))

    try:
        indices = [int(x.strip()) for x in match.group(1).split(",")]
        indices = [i for i in indices if 0 <= i < len(articles)][:5]
        print(f"  AI selected indices: {indices} (via {source})")
        return indices
    except Exception as e:
        print(f"  Ranking parse error: {e}")
        return list(range(min(5, len(articles))))

# ─── STEP 4: SAVE CANDIDATES JSON ────────────────────────────────────────────

def save_candidates(articles, top_indices):
    top_5 = []
    for rank, idx in enumerate(top_indices, 1):
        a = articles[idx]
        m = re.search(r"https?://(?:www\.)?([^/]+)", a["link"])
        source = m.group(1) if m else a["link"]
        top_5.append({
            "rank":    rank,
            "title":   a["title"],
            "source":  source,
            "url":     a["link"],
            "summary": a["description"][:150],
        })

    remaining_indices = [i for i in range(len(articles)) if i not in top_indices]
    remaining = []
    for rank, idx in enumerate(remaining_indices[:10], len(top_indices) + 1):
        a = articles[idx]
        m = re.search(r"https?://(?:www\.)?([^/]+)", a["link"])
        source = m.group(1) if m else a["link"]
        remaining.append({
            "rank":    rank,
            "title":   a["title"],
            "source":  source,
            "url":     a["link"],
            "summary": a["description"][:150],
        })

    now_ist = ist_now()
    data = {
        "generated_at":    now_ist.isoformat(),
        "manually_reviewed": False,
        "review_deadline": "Edit this file before 8:00 AM IST if you want to change the top 5",
        "_manual_brief_template": {
            "_instructions": "To publish your own written article: copy this template into any top_5 entry as a 'manual_brief' key, fill in the fields, set manually_reviewed to true, commit before 8 AM IST.",
            "title":       "Your headline here (max 12 words, punchy)",
            "category":    "India Tech | AI & ML | Startup Funding | Digital India | Product Launch",
            "read_time":   "3 min read",
            "hook":        "3-4 sentence opening. Tell it like a story. Conversational, chai-over-friend tone.",
            "context":     "2-3 sentences of background. What led to this? Why now?",
            "facts": [
                "Fact 1 — include a number, name, or date",
                "Fact 2 — include a number, name, or date",
                "Fact 3 — include a number, name, or date",
                "Fact 4 — include a number, name, or date",
                "Fact 5 — include a number, name, or date"
            ],
            "what_next":   "2-3 sentences. What should readers watch for? When will we know more?",
            "why_india":   "One sentence. Why does this matter specifically for Indian readers?",
            "source_name": "Your name, or the publication name",
            "source_link": "https://link-to-original-source.com"
        },
        "top_5":           top_5,
        "remaining_candidates": remaining,
    }

    CANDIDATES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Saved: {CANDIDATES_FILE}")
    print("  Top 5 for tomorrow:")
    for item in top_5:
        print(f"    [{item['rank']}] {item['title'][:65]} — {item['source']}")

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("CatchTheBrief — Fetch & Rank (Session 6, Step 1)")
    print(f"Run time: {ist_now().strftime('%d %b %Y, %I:%M %p')} IST")
    print("=" * 60)

    if not GEMINI_KEYS:
        print("WARNING: No Gemini API keys found")
    if not GROQ_API_KEY:
        print("WARNING: No Groq API key found")

    gemini = GeminiClient(GEMINI_KEYS)
    groq   = GroqClient(GROQ_API_KEY)

    print("\n[Step 1] Fetching articles from RSS feeds...")
    articles = fetch_all_articles()
    if len(articles) < 3:
        print("ERROR: Too few articles fetched. Exiting.")
        return

    print("\n[Step 2] Filtering junk articles...")
    articles = filter_articles(articles)

    print("\n[Step 2b] Applying source diversity filter...")
    articles = source_diversity_filter(articles)

    print(f"\n[Step 3] AI ranking {len(articles)} articles → top 5...")
    top_indices = rank_articles(articles, gemini, groq)

    print("\n[Step 4] Saving review_candidates.json...")
    save_candidates(articles, top_indices)

    print("\n" + "=" * 60)
    print("✅ Done! review_candidates.json saved.")
    print("   Review and edit on GitHub before 8:00 AM IST.")
    print("   generate_and_publish.py will read this file at 8 AM.")
    print("=" * 60)


if __name__ == "__main__":
    main()
