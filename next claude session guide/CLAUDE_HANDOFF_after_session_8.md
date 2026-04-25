# CatchTheBrief — Project Handoff Document
# Paste this at the start of any new Claude session to resume instantly.
# Last updated: 25 April 2026 — Session 8 (Distribution: WhatsApp, Telegram, Social)

---

## ONE-LINE BRIEF
CatchTheBrief (catchthebrief.com) is an automated daily news briefing site
that publishes 5 AI-curated, in-depth briefs every morning for Indian readers.
Focused on quality over quantity. Zero server. Zero monthly cost.
Runs on GitHub Actions + GitHub Pages.

---

## STRATEGIC DIRECTION (decided Session 3)

### What changed and why
Session 3 was a full project review. Key decisions:
1. **Deals section: PAUSED** — Can't compete with 91mobiles, Smartprix, MySmartPrice.
   Deals code stays in repo but is disabled. Revisit only after 500+ daily readers.
2. **Content quality is the #1 priority** — not monetization, not features.
3. **Monetization: DELAYED 90 days** — AdSense code removed from templates.
   Amazon Associates paused. Focus purely on building readership first.
4. **Niche focus: India Tech & Startups** — dropped scattered 5-category approach.
   All 5 daily briefs now come from a single focused niche.
5. **Smart article selection** — engine fetches 15-25 articles, AI ranks them,
   top 5 get published. Quality selection, not random RSS grab.
6. **Richer briefs with images** — longer format, more readable, includes
   relevant AI-generated images (Session 7). Users should want to read the full brief.
7. **Distribution-first mindset** — WhatsApp Channel + Telegram + social sharing
   are higher priority than any new feature.

### Inspiration: Finshots model
Finshots (finshots.in) grew to 500K+ subscribers by:
- Picking ONE niche (finance) and going deep
- Writing in simple, jargon-free language with storytelling
- Building audience FIRST, then monetizing via Ditto Insurance
- Using word of mouth + social media + college partnerships
CatchTheBrief should follow a similar "audience first, money later" path.

---

## TECH STACK
- Language:     Python 3.11
- Engine:       news_engine.py v5.0 (legacy single-script, kept as manual fallback)
- Step 1:       fetch_and_rank.py (Session 6) — runs at 10 PM IST
- Step 2:       generate_and_publish.py (Session 7) — runs at 8 AM IST
- AI Primary:   Google Gemini 2.5 Flash (free tier, multiple API keys rotated)
- AI Model:     gemini-2.5-flash  ← IMPORTANT: use this exact string
- AI Fallback:  Groq — Llama 3.3 70B (free tier, 14,400 req/day — auto-activates when Gemini quota exhausted)
- Groq HTTP:    Must use `requests` library NOT urllib (urllib gets Cloudflare 403)
- AI Images:    Pollinations.AI (free, no API key needed) — URL embedded directly in HTML
                URL format: https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true&seed={seed}
                Seed is deterministic (MD5 of slug) so same article = same image every time
                LOCAL TESTING: open in Incognito mode — Pollinations blocks logged-in users on legacy endpoint
                LIVE SITE: works fine for all visitors (they are not logged into Pollinations)
- Frontend:     Pure HTML + CSS (no framework)
- Fonts:        Inter (body) + Space Grotesk (headings) via Google Fonts ✅ LIVE
- Hosting:      GitHub Pages (free)
- Automation:   GitHub Actions — TWO separate workflow files (Session 6):
                  fetch_and_rank.yml:        4:30 PM UTC = 10:00 PM IST
                  generate_and_publish.yml:  2:30 AM UTC =  8:00 AM IST
                  daily.yml:                 manual trigger only (legacy fallback)
- Newsletter:   MailerLite (free plan: 500 subs / 12,000 emails/month — permanent free tier, NOT a trial)
                  Account ID: 2285640 | Form ID: 185448516399662487
                  Form action: https://assets.mailerlite.com/jsonp/2285640/forms/185448516399662487/subscribe
                  Email field name: fields[email] | Hidden inputs: ml-submit=1, anticsrf=true
                  Universal script added to <head> of all pages (index.html + article.html)
                  GOTCHA: form uses mode:'no-cors' so success message shows regardless of result
                  DEBUG: check MailerLite dashboard → Subscribers to confirm submissions land
                  If no email arrives: check spam, OR double opt-in is on (MailerLite → Form settings)
- Telegram:     Bot API (free, no limits) — auto-posts daily summary at 8 AM IST
                  Bot token:  stored as GitHub Secret TELEGRAM_BOT_TOKEN
                  Channel ID: -1003783025490 (stored as GitHub Secret TELEGRAM_CHAT_ID)
                  Channel link: https://t.me/+i1f2M9MJ7mgyODFl
                  Script: post_to_telegram.py — reads latest archive JSON, sends HTML message
                  GOTCHA: chat_id must be the numeric ID (not invite link) — get via getUpdates API
- WhatsApp:     Manual channel — https://whatsapp.com/channel/0029VbCVn180bIdk2cPgSF1L
                  Posting is manual (no WhatsApp automation possible without Business API)
- Twitter/X:    Manual posting daily (API free tier is read-only — paid plan needed to post)
                  post_to_twitter.py exists in repo but is unused
- Dependencies: requests, beautifulsoup4, google-genai  (NO lxml — causes Windows build error)
- Analytics:    Google Analytics GA4 (G-V6N03CT88P) — keep on all pages
- AdSense:      PAUSED — ca-pub-2453013968799709 (commented out in templates, re-add after 90 days)
- Affiliate:    PAUSED — Amazon Associates tag: catchthebrief-21 (re-add with readership)

---

## FILE STRUCTURE (after Session 8)
```
catchthebrief/
├── news_engine.py              # Legacy engine v5.0 — manual trigger only ✅
├── fetch_and_rank.py           # Session 6 — Step 1: fetch, filter, rank, save candidates ✅
├── generate_and_publish.py     # Session 7 — Step 2: read candidates, generate, publish ✅
├── post_to_telegram.py         # Session 8 — NEW: daily Telegram channel post ✅
├── post_to_twitter.py          # Session 8 — unused (Twitter API requires paid plan) ✅
├── review_candidates.json      # Auto-generated nightly, manually editable before 8 AM IST ✅
├── favicon.svg                 # Session 7 — blue "C" SVG favicon ✅
├── requirements.txt            # requests, beautifulsoup4, google-genai
├── README.md
├── robots.txt
├── .gitignore
├── CNAME                       # catchthebrief.com
├── templates/
│   ├── index.html              # Session 8: WhatsApp + Telegram follow buttons in
│   │                           #            newsletter section + footer ✅
│   └── article.html            # Session 8: WhatsApp Channel + Telegram follow buttons
│                               #            in share section + footer ✅
├── .github/
│   └── workflows/
│       ├── fetch_and_rank.yml          # Session 6 — cron 4:30 PM UTC ✅
│       ├── generate_and_publish.yml    # Session 8 — now runs post_to_telegram.py ✅
│       └── daily.yml                   # Legacy — manual trigger only ✅
│
# GENERATED by engine (not hand-edited):
├── index.html
├── sitemap.xml
├── articles/
│   └── YYYY-MM-DD-slug.html
└── archive/
    ├── index.html
    ├── YYYY-MM-DD.html
    └── *.json
```

---

## NEWS ENGINE — ARCHITECTURE (Session 7 two-step flow, unchanged Session 8)

### fetch_and_rank.py — Step 1 (runs 10 PM IST)

#### Step 1: Fetch wide (up to 25 articles)
Pull from multiple India tech/startup RSS feeds:
- TechCrunch India:       https://techcrunch.com/tag/india/feed/
- YourStory:              https://yourstory.com/feed
- Inc42:                  https://inc42.com/feed/
- Entrackr:               https://entrackr.com/feed/          ← returns 404 sometimes, handled
- The Ken (free posts):   https://the-ken.com/feed/
- Gadgets360:             https://feeds.feedburner.com/gadgets360-latest
- Medianama:              https://www.medianama.com/feed/
- Analytics India Mag:    https://analyticsindiamag.com/feed/ ← XML parse errors sometimes, handled
Cap at 25 unique articles from past 36 hours.

#### Step 2: Filter junk
Remove listicles, sponsored content, lifestyle posts.
Junk keywords: "inspiring", "motivat", "books to read", "tips for", "how to be",
"sponsored", "advertis", "partner content", "brand story", "zodiac", "horoscope"

#### Step 2b: Source diversity filter — Session 6
- Keep max 3 articles per source domain (not 1 — was too aggressive, left only 2 candidates)
- Sorted newest-first per domain
- Prevents all candidates coming from same 1-2 sources

#### Step 3: AI ranking (1 call)
Send up to 15 headlines to Gemini/Groq in ONE call.
Prompt requires top 5 to span 3+ different sub-topics.
Falls back to first 5 if AI ranking fails.

#### Step 4: Save review_candidates.json
Saves ranked candidates JSON and commits to GitHub.
Rajneesh reviews and can reorder/swap before 7:30 AM IST.

### generate_and_publish.py — Step 2 (runs 8 AM IST)

#### Step 5: Read review_candidates.json
If `manually_reviewed: true` → uses Rajneesh's edited top 5
If `manually_reviewed: false` → uses auto-ranked top 5

#### Step 6: Generate rich briefs (5 AI calls)
For each candidate, calls Gemini/Groq with BRIEF_PROMPT.
If candidate has `manual_brief` key → skips AI, publishes exactly as written.

#### Step 7: Generate AI image URL via Pollinations.AI
Seed = MD5(slug)[:6] converted to int → deterministic, same article = same image always.
URL format: `https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true&seed={seed}`

#### Step 8: Generate article HTML pages
Slug format: `2026-04-23-my-title.html` (date-prefixed)
Includes JSON-LD NewsArticle structured data

#### Step 9: Generate homepage, sitemap, archive JSON
Homepage includes {{YESTERDAY_BRIEFS}} teaser
Sitemap includes /archive/ and /archive/YYYY-MM-DD.html pages

#### Step 10: Generate per-day archive page
Creates archive/YYYY-MM-DD.html for today's briefs.

#### Step 11: Regenerate archive/index.html

#### Step 12: robots.txt

### post_to_telegram.py — Step 3 (runs after Step 2, 8 AM IST)
- Reads latest archive/YYYY-MM-DD.json
- Builds an HTML-formatted message with 5 headlines + site link + hashtags
- Posts to Telegram channel via Bot API (free, no limits)
- Skips silently if TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set
- Uses `requests` library (already in dependencies)

### AI CALL BUDGET
- Article ranking:     1 call (fetch_and_rank.py at 10 PM IST)
- Article briefs:      5 calls (generate_and_publish.py at 8 AM IST)
- Total:               6 calls/day
- Groq fallback:       auto-activates on any Gemini/error
- Pollinations images: 0 AI calls
- Telegram:            0 AI calls — plain Bot API

---

## MANUAL REVIEW WORKFLOW (Session 6, unchanged)

### Daily schedule
```
10:00 PM IST  → fetch_and_rank.py runs (GitHub Action)
                Fetches, filters, deduplicates by source, AI ranks.
                Saves review_candidates.json and commits to GitHub.

10:00 PM       → Review window opens
  to            Open GitHub on phone/laptop.
7:30 AM IST    Edit review_candidates.json if needed.
                Set "manually_reviewed": true and commit.

8:00 AM IST  → generate_and_publish.py runs (GitHub Action)
                Reads review_candidates.json.
                Generates briefs, publishes site.
                → post_to_telegram.py runs automatically after publish
                → Rajneesh posts manually on X/Twitter (2 min)
                → Rajneesh shares on WhatsApp Channel (2 min)
```

### review_candidates.json structure
```json
{
  "generated_at": "2026-04-25T22:00:00+05:30",
  "manually_reviewed": false,
  "review_deadline": "Edit this file before 8:00 AM IST if you want to change the top 5",
  "_manual_brief_template": { ... proforma always included ... },
  "top_5": [
    {"rank": 1, "title": "...", "source": "Inc42", "url": "...", "summary": "..."},
    ...
  ],
  "remaining_candidates": [...]
}
```

---

## BRIEF FORMAT — ENHANCED (implemented Session 4, unchanged)

```
TITLE:        Compelling headline (AI-rewritten for engagement, max 12 words)
CATEGORY:     AI & ML | Startup Funding | Digital India | Product Launch | India Tech
READ_TIME:    e.g. "3 min read"
HOOK:         3-4 sentence story-style opening. Friendly, conversational.
CONTEXT:      2-3 sentences of background.
KEY_FACTS:    5 bullet points — concrete numbers, names, dates, amounts.
WHAT_NEXT:    2-3 sentences on what to watch for next.
WHY_INDIA:    1 sentence — why this matters specifically to Indian readers.
SOURCE:       Original source name + link  ← KEEP THIS — legally required even with AI content
```

### Source attribution policy (decided Session 7)
Content is AI-rewritten and images are AI-generated, but the underlying news facts
came from the original journalists. Always keep source attribution. Style it subtly
if needed, never remove it.

### Brief Parser — important notes (Session 4)
- Uses `get_section()` split approach, NOT regex multiline (regex was failing)
- Handles both • and - bullet styles (Gemini uses •, Groq uses -)
- If hook/context parse as empty → check that section labels are on their own line

---

## TEMPLATE INJECTION TAGS (updated Session 7, unchanged Session 8)
| Tag                  | Replaced with                                          |
|----------------------|--------------------------------------------------------|
| {{ALL_ARTICLES}}     | Hero card + two 2×2 grid rows                          |
| {{YESTERDAY_BRIEFS}} | Yesterday's briefs teaser section (or empty)           |
| {{LAST_UPDATED}}     | Human timestamp e.g. "25 April 2026, 9:00 AM"         |
| {{ISO_DATE}}         | Machine date e.g. "2026-04-25"                         |
| {{ARTICLE_COUNT}}    | e.g. "5 briefs"                                        |
| {{SITE_URL}}         | https://catchthebrief.com                              |
| {{OG_IMAGE_HOME}}    | Pollinations URL of first article (homepage)           |
| {{TITLE}}            | Article title (article.html only)                      |
| {{META_DESCRIPTION}} | Unique per article (from hook text, max 160 chars)     |
| {{OG_TITLE}}         | Open Graph title per article                           |
| {{OG_DESCRIPTION}}   | Open Graph description per article                     |
| {{OG_IMAGE}}         | Pollinations.AI image URL (absolute, used for og:image)|
| {{JSON_LD}}          | JSON-LD NewsArticle structured data block              |
| {{SLUG}}             | Date-prefixed slug: 2026-04-25-my-title                |
| {{LABEL}}            | Category label                                         |
| {{COLOR}}            | CSS badge class (ai/startup/policy/product/funding)    |
| {{READ_TIME}}        | e.g. "3 min read"                                      |
| {{HERO_IMAGE_HTML}}  | <img> or emoji placeholder div                         |
| {{HOOK}}             | Story hook (3-4 sentences)                             |
| {{CONTEXT}}          | Background context (2-3 sentences)                     |
| {{KEY_FACTS}}        | 5 bullet <li> items                                    |
| {{WHAT_NEXT}}        | Forward-looking section                                |
| {{WHY_INDIA}}        | Why it matters for India                               |
| {{SOURCE_NAME}}      | News source domain                                     |
| {{SOURCE_LINK}}      | Original article URL                                   |
| {{PUB_DATE}}         | Publication date from RSS                              |
| {{WHATSAPP_URL}}     | Pre-built WhatsApp share URL (share THIS article)      |
| {{TWITTER_URL}}      | Pre-built Twitter/X share URL                          |

---

## SEO STATUS (after Session 7, unchanged Session 8)
| Signal                        | Status                                                |
|-------------------------------|-------------------------------------------------------|
| Unique `<title>` per article  | ✅ Working                                            |
| `<meta description>` per article | ✅ From hook text, max 160 chars                   |
| og:title, og:description, og:url | ✅ Working                                         |
| og:image per article          | ✅ Pollinations.AI absolute URL                      |
| og:image on homepage          | ✅ First article's image                             |
| og:type: article              | ✅ Working                                            |
| og:site_name                  | ✅ "CatchTheBrief" on all pages                      |
| og:locale                     | ✅ "en_IN" on all pages                              |
| Twitter card (summary_large_image) | ✅ Working                                       |
| Canonical URLs                | ✅ Working                                            |
| JSON-LD NewsArticle schema    | ✅ On every article page                             |
| sitemap.xml                   | ✅ Includes homepage, articles, archive              |
| robots.txt                    | ✅ Points to sitemap                                  |
| Favicon                       | ✅ favicon.svg (blue "C")                            |
| lang="en-IN"                  | ✅ On all pages                                      |
| Google Analytics GA4          | ✅ G-V6N03CT88P on all pages                         |

---

## DISTRIBUTION CHANNELS (Session 8)
| Channel        | Status     | Details                                                    |
|----------------|------------|------------------------------------------------------------|
| Telegram       | ✅ AUTO    | Bot posts daily at 8 AM IST — chat ID: -1003783025490     |
| WhatsApp       | ✅ MANUAL  | https://whatsapp.com/channel/0029VbCVn180bIdk2cPgSF1L     |
| X/Twitter      | ✅ MANUAL  | Post manually each morning (~2 min)                        |
| Email (MailerLite) | ✅ LIVE | account: 2285640, form: 185448516399662487                 |
| LinkedIn       | ⬜ TODO    | Manual posting — good for startup audience                 |

---

## CATEGORY → CSS COLOR MAPPING
| Category        | CSS class | Color  | Badge bg  |
|-----------------|-----------|--------|-----------|
| AI & ML         | ai        | purple | #EDE9FE   |
| Startup Funding | startup   | green  | #D1FAE5   |
| Digital India   | policy    | red    | #FEE2E2   |
| Product Launch  | product   | amber  | #FEF3C7   |
| India Tech      | funding   | blue   | #DBEAFE   |

---

## DESIGN SYSTEM (implemented Session 5, unchanged)

### Typography
- Headings:    Space Grotesk (Google Fonts)
- Body text:   Inter (Google Fonts)
- Base size:   18px body on mobile, 20px on desktop
- Line height: 1.6 for body text
- Max width:   680px for article text (article.html)
             1100px for layout container (index.html)
             860px for archive pages

### Color Palette
```css
--bg-primary:       #FAFAFA;
--bg-card:          #FFFFFF;
--bg-accent:        #F0F4F8;
--text-primary:     #1A1A2E;
--text-secondary:   #4A5568;
--text-muted:       #718096;
--accent-primary:   #2563EB;
--accent-hover:     #1D4ED8;
--border:           #E2E8F0;
--border-strong:    #CBD5E0;
--category-ai:      #7C3AED;
--category-startup: #059669;
--category-policy:  #DC2626;
--category-product: #D97706;
--category-funding: #2563EB;
```

---

## KEY ENGINE FUNCTIONS

### fetch_and_rank.py key functions
- `fetch_all_articles()` — pulls from 8 RSS feeds, deduplicates by URL, caps at 25
- `filter_articles()` — removes junk/listicles/sponsored
- `source_diversity_filter(articles, max_per_source=3)` — keeps 3 newest per domain
- `rank_articles(articles, gemini, groq)` — 1 AI call, picks top 5 with topic diversity
- `save_candidates(articles, top_indices)` — writes review_candidates.json with template

### generate_and_publish.py key functions
- `date_slug(date_str, title)` — returns "2026-04-25-my-title"
- `generate_ai_image_url(title, category, slug)` — Pollinations.AI URL (deterministic seed)
- `read_candidates()` — reads JSON, detects manual vs auto
- `generate_brief(candidate, gemini, groq)` — checks for manual_brief key first, then AI
- `get_yesterday_data(now)` — reads most recent archive JSON before today
- `generate_yesterday_teaser_html(now)` — builds yesterday's briefs HTML block
- `generate_hero_card(brief, image_url, slug)` — hero card HTML
- `generate_grid_card(brief, image_url, slug)` — grid card HTML
- `build_all_articles_html(briefs_data)` — assembles {{ALL_ARTICLES}} block
- `generate_article_page(brief, image_url, slug, idx, total, now)` — full article.html with JSON-LD
- `generate_homepage(briefs_data, now)` — full index.html with yesterday teaser
- `generate_sitemap(slugs, now)` — includes archive pages
- `save_archive(briefs_data, now)` — saves today's archive JSON
- `generate_day_archive_page(archive_data)` — writes archive/YYYY-MM-DD.html
- `generate_archive_index()` — reads all archive/*.json, regenerates archive/index.html

### post_to_telegram.py key functions (Session 8)
- `get_latest_archive()` — reads most recent archive/YYYY-MM-DD.json
- `format_date(date_str)` — "2026-04-25" → "25 April 2026"
- `build_message(data)` — composes HTML-formatted Telegram message with 5 headlines
- `main()` — posts via Bot API, exits silently if credentials missing

---

## BUGS FIXED (all sessions)
1.  lxml Windows build error → FIXED: xml.etree.ElementTree
2.  Windows %-d date format crash → FIXED: manual timestamp
3.  Hardcoded API key → FIXED: env vars
4.  Single API key quota → FIXED: 3-key rotation + Groq fallback
5.  templates/ folder not found → FIXED: created manually
6.  .github/workflows/daily.yml not pushed → FIXED
7.  git push rejected (CNAME conflict) → FIXED: git pull --no-edit then push
8.  GitHub Actions push permission denied → FIXED: Settings → Actions → Read+Write
9.  Reddit deals HTTP 403 → FIXED: switched to India RSS feeds
10. Gemini 503 on articles 5-10 → MITIGATED: Groq fallback
11. Empty articles (API errors) → FIXED: 3-tier fallback, never blank
12. US deals showing to Indian users → FIXED: switched to India-focused sources
13. Wrong Gemini model name → FIXED: use gemini-2.5-flash
14. Gemini limit:0 quota → FIXED: accept terms at aistudio.google.com first
15. Groq 403 Cloudflare block → FIXED: use requests library not urllib
16. Brief parser failing silently → FIXED: replaced regex with get_section() splitter
17. Junk articles ranked → FIXED: filter_articles() step added
18. Old HTML cached after engine fix → FIXED: del articles\*.html before each run
19. urllib.parse imported after function → FIXED: moved to top of imports
20. Old CSS classes in card HTML → FIXED: rewrote card functions
21. All 5 briefs from same source → FIXED Session 6: source_diversity_filter (max 3/source)
22. Source diversity filter too aggressive → FIXED Session 6: max 3 per source instead of 1
23. /archive/ returning 404 → FIXED Session 6: archive/index.html auto-regenerated daily
24. Buttondown subscribe "not found" → FIXED Session 6: inline JS shows ✓ success message
25. "All Briefs" back button plain text → FIXED Session 6: pill button with border + hover
26. Buttondown account rejected → FIXED Session 6: migrated to MailerLite
27. Pollinations images not loading locally → NOT A BUG: test in Incognito
28. Newsletter shows "You're in!" but no email → check MailerLite dashboard + disable double opt-in
29. Twitter API 402 Payment Required → NOT A BUG: free tier is read-only since 2023.
    Posting requires Basic plan ($100/month). Solution: post manually.
30. Telegram "chat not found" 400 error → FIXED Session 8: must use numeric chat ID
    (e.g. -1003783025490) not the invite link. Get via getUpdates API endpoint.

---

## ENVIRONMENT VARIABLES REQUIRED
| Variable            | Purpose                              | Where to set           |
|---------------------|--------------------------------------|------------------------|
| GEMINI_API_KEY_1    | First Gemini free API key            | GitHub Secret + CMD    |
| GEMINI_API_KEY_2    | Second key (rotation backup)         | GitHub Secret + CMD    |
| GEMINI_API_KEY_3    | Third key (rotation backup)          | GitHub Secret + CMD    |
| GROQ_API_KEY        | Groq fallback (14,400 req/day free)  | GitHub Secret + CMD    |
| TELEGRAM_BOT_TOKEN  | Telegram bot token from BotFather    | GitHub Secret + CMD    |
| TELEGRAM_CHAT_ID    | Channel numeric ID: -1003783025490   | GitHub Secret + CMD    |

How to set locally on Windows CMD (resets when CMD closes):
```
set GEMINI_API_KEY_1=your_key
set GROQ_API_KEY=your_groq_key
set TELEGRAM_BOT_TOKEN=your_bot_token
set TELEGRAM_CHAT_ID=-1003783025490
python fetch_and_rank.py
python generate_and_publish.py
python post_to_telegram.py
```

### Gemini API key gotchas (learned Session 4)
- Model name must be: gemini-2.5-flash
- Keys created BEFORE accepting terms on aistudio.google.com have limit:0 quota
- Fix: go to aistudio.google.com, accept terms, then generate a fresh key
- Free tier resets at midnight Pacific (1:30 PM IST)
- Per-minute rate limit also exists — add time.sleep(1.5) between calls

### Groq API gotchas (learned Session 4)
- MUST use `requests` library — urllib gets Cloudflare 403 error code 1010
- Prompt must be trimmed to 6000 chars max to avoid token errors
- Model: llama-3.3-70b-versatile
- Uses - bullets (not •) — parser handles both

### Telegram Bot gotchas (learned Session 8)
- Bot must be added as Admin in channel with "Post Messages" permission
- chat_id must be numeric (e.g. -1003783025490) — invite links don't work as chat_id
- Get numeric ID: POST any message in channel, then call getUpdates API
- parse_mode: "HTML" — use <b>, <i> tags (not markdown)
- disable_web_page_preview: False → shows article link preview in channel

---

## HOW TO RUN LOCALLY
```
cd "C:\Users\sub office\Desktop\news deals project\code\claude"
set GEMINI_API_KEY_1=your_key_here
set GROQ_API_KEY=your_groq_key
set TELEGRAM_BOT_TOKEN=your_bot_token
set TELEGRAM_CHAT_ID=-1003783025490

# Step 1 — fetch and rank (run at night)
python fetch_and_rank.py

# Optionally edit review_candidates.json

# Step 2 — generate and publish (run next morning)
python generate_and_publish.py

# Step 3 — post to Telegram
python post_to_telegram.py
```

Before each test run, delete old generated files:
```
del articles\*.html
del index.html
python fetch_and_rank.py
python generate_and_publish.py
```

---

## DEPLOYMENT STATUS
- [x] GitHub repo created (rajneesh1312/catchthebrief)
- [x] API keys added as GitHub Secrets (Gemini x3 + Groq)
- [x] Code pushed to GitHub
- [x] GitHub Pages enabled
- [x] Custom domain connected (catchthebrief.com)
- [x] SSL provisioned
- [x] GitHub Actions — workflow permissions set to Read+Write
- [x] Daily cron verified — two separate workflows (Session 6)
- [x] Manual workflow test — GREEN tick confirmed
- [x] Google Analytics wired (G-V6N03CT88P)
- [x] MailerLite newsletter embedded — account 2285640, form 185448516399662487 (Session 6)
- [x] Groq fallback wired in engine
- [x] Deals section paused (commented out in engine + templates)
- [x] AdSense code commented out in templates
- [x] Engine rewritten for smart article selection (Session 4)
- [x] New RSS feeds added — 8 India tech sources (Session 4)
- [x] Junk article filter added (Session 4)
- [x] Enhanced brief format implemented (Session 4)
- [x] robots.txt added (Session 4)
- [x] Unique meta tags per article — title, description, og:* (Session 4)
- [x] WhatsApp + Twitter share buttons on every article (Session 4)
- [x] Newsletter CTA on homepage + article pages (Session 4)
- [x] Archive system — daily JSON saved to /archive/ (Session 4)
- [x] Homepage redesigned — Inter + Space Grotesk, hero + 2x2 grid (Session 5)
- [x] Article page redesigned — clean reading layout, 680px max-width (Session 5)
- [x] Reading progress bar on article page (Session 5)
- [x] Back-to-top button on article page (Session 5)
- [x] Source diversity rule — max 3 articles per source in candidate pool (Session 6)
- [x] Topic diversity in AI ranking prompt (Session 6)
- [x] Split engine into fetch_and_rank.py + generate_and_publish.py (Session 6)
- [x] review_candidates.json — auto-generated nightly, manually editable (Session 6)
- [x] Manual brief injection — manual_brief key skips AI (Session 6)
- [x] Two cron jobs — fetch_and_rank.yml + generate_and_publish.yml (Session 6)
- [x] archive/index.html — browse page, auto-regenerated daily (Session 6)
- [x] Newsletter form — MailerLite embedded, inline JS success (Session 6)
- [x] Date-prefixed article slugs — YYYY-MM-DD-slug.html (Session 7)
- [x] AI-generated images via Pollinations.AI (Session 7)
- [x] Per-day archive pages — /archive/YYYY-MM-DD.html (Session 7)
- [x] Yesterday's briefs teaser on homepage (Session 7)
- [x] JSON-LD NewsArticle structured data on every article (Session 7)
- [x] og:image on homepage + og:site_name + og:locale + lang=en-IN (Session 7)
- [x] Favicon (favicon.svg — blue "C") (Session 7)
- [x] Sitemap includes /archive/ + /archive/YYYY-MM-DD.html (Session 7)
- [x] WhatsApp Channel created — https://whatsapp.com/channel/0029VbCVn180bIdk2cPgSF1L (Session 8)
- [x] Telegram Channel created — https://t.me/+i1f2M9MJ7mgyODFl (Session 8)
- [x] Automated daily Telegram post — post_to_telegram.py (Session 8)
- [x] WhatsApp + Telegram follow buttons on homepage newsletter section (Session 8)
- [x] WhatsApp + Telegram follow buttons on article share section (Session 8)
- [x] WhatsApp + Telegram links in footer on all pages (Session 8)
- [x] TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID added as GitHub Secrets (Session 8)
- [ ] LinkedIn posting (manual — do when you have time)
- [ ] Manual brief injection via separate manual_briefs.json editorial layer (Session 9)
- [ ] Edit AI briefs before publish — editorial override system (Session 9)
- [ ] Previous/Next brief navigation (Session 10)
- [ ] PWA manifest.json — "Add to Home Screen" for mobile (Session 10)

---

## MONETIZATION STATUS
| Channel           | Status                                               |
|-------------------|------------------------------------------------------|
| Google AdSense    | ⏸️ PAUSED — code commented out, re-add after 90 days  |
| Amazon Associates | ⏸️ PAUSED — tag saved (catchthebrief-21)              |
| Google Analytics  | ✅ Live — G-V6N03CT88P (keep — need data)             |
| Newsletter        | ✅ MailerLite — account: 2285640, form: 185448516399662487 |

---

## FUTURE FEATURES ROADMAP

### ✅ Phase 1: Content Engine Rewrite (Session 4 — DONE)
### ✅ Phase 2: Design Overhaul (Session 5 — DONE)
### ✅ Phase 3: Manual Review + Source Diversity (Session 6 — DONE)
### ✅ Phase 4: Archive, AI Images & SEO (Session 7 — DONE)
### ✅ Phase 5: Distribution (Session 8 — DONE)
- WhatsApp Channel + Telegram Channel created
- Automated daily Telegram post via GitHub Actions
- WhatsApp Channel + Telegram follow buttons on site
- Twitter/X: manual posting (API costs $100/month)

### 🔄 Phase 6: Editorial Control (Session 9 — NEXT)
Goal: Upgrade the manual_brief system into a proper editorial layer.
Current state: manual_brief works via review_candidates.json (Session 6).
Session 9 upgrade: migrate to manual_briefs.json — a separate persistent file
where briefs survive across days (not overwritten nightly like review_candidates.json).
Also: ability to edit AI-generated briefs before publish.

### Phase 7: UX Polish (Session 10)
- Previous/Next brief navigation
- PWA manifest.json — "Add to Home Screen" for mobile

### Phase 8: Growth & Monetization (Day 90+)
Only after hitting 500+ daily readers.

---

## CONVERSATION CONTEXT
- Developer: Rajneesh, based in Ajmer, Rajasthan, India
- New developer — prefers clear explanations with code
- Running Windows (important for compatibility decisions)
- Using free tiers only — no paid APIs, no paid hosting
- GitHub repo: https://github.com/rajneesh1312/catchthebrief
- Live site: https://catchthebrief.com
- Claude (Anthropic) is the AI pair programmer

---

## HOW TO USE CLAUDE EFFICIENTLY
- Start each session: paste this handoff + today's goal in ONE message
- Share only relevant code sections, never the whole file
- One session = one goal (e.g. "Session 9: Editorial Control")
- Say "✅ done" when code works
- Paste exact error messages, not descriptions
- Update this file at end of every session
- Follow the session roadmap above — don't skip phases
