# CatchTheBrief — Claude Handoff After Session 9

**Date:** 13 May 2026  
**Session focus:** Full repository audit + implementation across all audit findings  
**Priority order established:** Content Quality → SEO → Design/UX → Distribution

---

## What Was Done in Session 9

### Part A: New Features (early in session)
1. **Editorial control** — `manual_briefs.json` created as a persistent URL-keyed override file, never overwritten by automation. `generate_and_publish.py` updated with 3-level priority: manual_briefs.json → inline candidate override → AI.
2. **LinkedIn auto-posting** — `post_to_linkedin.py` created. Uses UGC Posts API v2. Added to `generate_and_publish.yml` workflow.
3. **Reddit share button** — Added to `templates/article.html` with `#FF4500` brand color.
4. **Telegram hashtag improvement** — Updated in `post_to_telegram.py`.

### Part B: Comprehensive Audit
Full 9-section audit covering: content quality, distribution, design, SEO, technical debt, missing pages, repository hygiene. Output: `SESSION_9_FULL_AUDIT_REPORT.md`.

### Part C: Full Implementation (end of session)
All audit findings implemented. Details below.

---

## Architecture Overview

**Two-step daily engine:**
- **Step 1** (`fetch_and_rank.py`) — 10:00 PM IST: Fetches RSS from 9 sources, filters, AI-ranks, saves `review_candidates.json`
- **Step 2** (`generate_and_publish.py`) — 8:00 AM IST: Reads candidates, generates briefs, builds all HTML, pushes to GitHub Pages

**AI stack:** Gemini 2.5 Flash (primary, 3-key rotation) → Groq Llama 3.3 70B (fallback)  
**Images:** Pollinations.AI (free, deterministic, seed = MD5(slug)[:6])  
**Hosting:** GitHub Pages (zero cost, zero server)

---

## All Changes Made in Session 9

### `generate_and_publish.py`

**BRIEF_PROMPT** (complete rewrite):
- Added angle-first instruction — lead with implication, not preamble
- No exclamation marks rule explicitly stated
- No rhetorical question openings
- Specific Why India rule — must name a city, sector, company, or person (not generic "India's tech ecosystem")
- New **TAKE section** — 1–2 sentence editorial opinion, honest and confident

**`parse_brief()`** (updated):
- Added `strip_md()` inner function — strips `**bold**`, `*italic*`, `__bold__`, `_italic_` markdown artifacts from all text fields
- Added `TAKE` parsing: `get_section(raw_text, "TAKE", ["SOURCE", "---"])`
- All text sections now pass through `strip_md()`
- KEY_FACTS bullet stripping done per-item after extraction (safe from regex interference)

**`generate_brief()`** (three branches updated):
- All three return dicts (manual_briefs.json, inline override, fallback) now include `"take": mb.get("take", "")` or `"take": ""`

**`build_take_html()`** (new helper):
- Renders amber-style callout box, returns `""` if take is empty

**`generate_article_page()`** (updated):
- `{{PUB_DATE}}` → `{{PUB_DATE_HTML}}` — conditionally rendered (no empty `·` separator when pub_date is blank)
- `{{TAKE_SECTION}}` added — renders full take callout or empty string

**`generate_homepage()`** (updated):
- `{{DATE_DISPLAY}}` added — renders `<div class="date-herald"><div class="date-day">Wednesday, 14 May 2026</div></div>`

**`generate_sitemap()`** (CRITICAL SEO fix):
- Was: only included today's 5 article slugs
- Now: scans `ARTICLES_DIR` for all `.html` files + adds today's new slugs if not already in directory

### `fetch_and_rank.py`

- Added CNBCTV18 RSS feed: `https://www.cnbctv18.com/tech/feed/`
- Added `SOURCE_NAMES` dict mapping domains to proper display names (YourStory, Inc42, Entrackr, The Ken, Gadgets 360, MediaNama, Analytics India Mag, TechCrunch, CNBC TV18)
- Added `get_source_name(url)` helper — replaces raw domain with mapped name
- Applied `get_source_name()` in `save_candidates()` — source field now shows proper names
- **Ranking prompt updated:**
  - Added hard rule: max 2 articles from same source domain in final 5
  - Added PR/brand announcement penalty
  - Sharpened relevance criterion

### `templates/article.html`

- **Section labels renamed:**
  - "The Backstory" → "How We Got Here"
  - "Key Facts" → "The Numbers"
  - "What to Watch" → "What Happens Next"
- **TAKE section added** — `{{TAKE_SECTION}}` placeholder after why-india-box, before source-row
- **CSS added:** `.take-box`, `.take-label`, `.take-text` (amber/yellow gradient, italic text)
- **pub_date fix:** `{{PUB_DATE}}` → `{{PUB_DATE_HTML}}` (no orphan `·` separator)
- **Newsletter moved** — from below share section to **above** share section (better visibility)
- **Footer updated** — Added About and Privacy links

### `templates/index.html`

- **Twitter card meta tags added:** `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`
- **JSON-LD WebSite structured data added** in `<head>`
- **Date herald CSS added:** `.date-herald`, `.date-day` (large, stylish date display)
- **`{{DATE_DISPLAY}}` placeholder added** before section-intro
- **Newsletter headline changed:** "Never miss a brief" → "5 stories. 15 minutes. Everything that matters in India tech."
- **Newsletter moved** — now appears **before** `{{YESTERDAY_BRIEFS}}` (articles → newsletter → yesterday)
- **Card preview clamp:** `-webkit-line-clamp: 2` → `3`
- **Footer updated** — Added About and Privacy links

### `.github/workflows/generate_and_publish.yml`

- `continue-on-error: true` added to both **Telegram** and **LinkedIn** steps
- Prevents LinkedIn token expiry (60-day TTL) from halting the entire workflow before git push

### `requirements.txt`

- Removed `lxml==5.2.2` (banned on Windows, never needed)
- Changed `google-genai==1.0.0` to `google-genai>=1.0.0`

### `robots.txt`

- Added `Disallow: /review_candidates.json`
- Added `Disallow: /manual_briefs.json`

### New files created

- `.gitignore` — standard Python/OS gitignore
- `404.html` — styled 404 page with site branding
- `about.html` — About page explaining what CatchTheBrief is, how it works, subscribe CTA
- `privacy.html` — Privacy policy (email collection, MailerLite, Google Analytics)

### Orphan files deleted

- `deals.html` — early experiment, not referenced anywhere
- `deals/` directory — same
- `daily.yml` (root) — superseded by `.github/workflows/generate_and_publish.yml`
- `New folder/` — old session scratch files (index.html, news_engine.py, news_engine_v4.py, template.html)
- `templates/deals.html` — unused template

### `README.md`

- Complete rewrite — removed Session 1 architecture description
- Now documents: two-step engine, AI stack, editorial control, distribution, directory structure, required secrets, brief format

---

## Current File State (key files)

| File | State |
|------|-------|
| `generate_and_publish.py` | Updated — TAKE, markdown strip, sitemap fix, DATE_DISPLAY |
| `fetch_and_rank.py` | Updated — CNBCTV18, SOURCE_NAMES, ranking prompt |
| `templates/article.html` | Updated — TAKE section, new labels, pub_date fix, newsletter moved |
| `templates/index.html` | Updated — date herald, Twitter cards, JSON-LD, newsletter order |
| `generate_and_publish.yml` | Updated — continue-on-error on social steps |
| `requirements.txt` | Fixed — lxml removed |
| `robots.txt` | Updated — internal JSON files disallowed |
| `manual_briefs.json` | Exists — empty briefs array, ready for use |
| `post_to_linkedin.py` | Created — full setup instructions in docstring |
| `post_to_telegram.py` | Updated — better hashtags |
| `404.html` | New |
| `about.html` | New |
| `privacy.html` | New |
| `.gitignore` | New |
| `README.md` | Rewritten |

---

## Known Remaining Items (for future sessions)

### Content Quality
- [ ] **YourStory hard limit** — ranking prompt has PR penalty but no explicit "max 1 YourStory in final-5" rule. Add to rank_articles() prompt in fetch_and_rank.py
- [ ] **"STRONGLY PREFER external validation"** — audit recommended adding this to ranking criteria (analyst quotes, regulatory action, named revenue numbers). Not yet in prompt.
- [ ] AI prompt for TAKE could include 2-3 example takes to sharpen voice
- [ ] Prev/Next article navigation — engine already passes ARTICLE_INDEX and TOTAL_ARTICLES, just needs prev_slug/next_slug and template nav row
- [ ] Hook quality still depends entirely on AI — consider editorial review workflow

### SEO
- [ ] **Submit to Google News Publisher Center** — `publishercenter.google.com`. All prerequisites now met (sitemap fixed, about.html created, consistent daily schedule). Described in audit as "potentially the biggest free traffic source." Takes 30 minutes, one-time action. Wait 1–4 weeks for review.
- [ ] `about.html` and `privacy.html` not in sitemap — add static entries to `generate_sitemap()`
- [ ] `lastmod` for historical articles should use actual file modification date, not today's date
- [ ] Archive pages missing `og:image` — add default OG image tag to archive template
- [ ] Article image alt text currently = title — generate more descriptive alt text in engine

### Design
- [ ] **Site tagline for new visitors** — audit §3D Gap 3: "5 India tech & startup stories. Written clearly. Every morning at 8 AM." 1–2 lines below the date herald in index.html. The date herald was added but no tagline.
- [ ] **Separate Share vs Follow sections on article page** — audit §3D Gap 7: "Share this brief" buttons (WhatsApp, Twitter, Reddit, Copy) and "Follow CatchTheBrief" channel links are in the same visual box. Split into two distinct sections. Not done.
- [ ] Prev/Next article navigation (same as content item above)
- [ ] Top bar (currently static "Subscribe free →") could show today's date or tease top story on repeat visits
- [ ] Mobile: hero card hook preview truncation could show more

### Distribution — Active Actions (all manual, no code)
- [ ] **Reddit — 3x per week posting** (audit §4D Tier 1): Post to r/indianstartups (131K), r/IndiaInvestments (120K), r/india (1.1M for big stories only). Write hook + 2–3 facts in post body, end with link. Do NOT post bare links — moderators remove them. 10 min/post.
- [ ] **Google News submission** (same as SEO item above — also a distribution win)
- [ ] **LinkedIn Newsletter** (audit §4D Tier 1): Create "India Tech Digest" as a LinkedIn Newsletter (different from standard posts). Weekly Sunday send. Gets email-style notifications to followers + newsletter badge. 15 min/week.
- [ ] **Twitter/X thread format** (audit §4D Tier 1): 5-tweet thread instead of single link. Tweet 1 = hook from top story, Tweets 2–5 = one-line summary each, last tweet = link + hashtags. Gets ~10x more impressions than link tweet. Hashtags: `#IndianStartups #IndiaTech #StartupIndia #IndiaVC #TechTwitter`
- [ ] **IndieHackers "How I Built This" post** (audit §4E Tier 2): Gets organic backlinks + initial curious traffic burst. One-time, permanent benefit. 1 hour.
- [ ] **Quora answers** (audit §4E Tier 2): Search "best India tech newsletter", "India startup news" — write genuine answers. These rank on Google permanently. 30 min one-time per question.
- [ ] LinkedIn token expires every 60 days — refresh via LinkedIn Developer App → Auth → OAuth 2.0 tools → update `LINKEDIN_ACCESS_TOKEN` secret
- [ ] No Twitter/X auto-posting in workflow — `post_to_twitter.py` exists, just needs a workflow step added (requires Twitter API paid tier)

### Growth Features (Session 12–14)
- [ ] **Weekly digest email** (audit §7A) — Sunday "Week in India Tech" email. New script `generate_weekly_digest.py` reads last 7 days of archive JSON, assembles top 5, generates MailerLite campaign. New cron: Sunday 9 AM IST. Zero new AI calls.
- [ ] **Category pages** (audit §7B) — `/category/ai-ml.html`, `/category/startup-funding.html` etc. 5 pages, generated from archive JSON, each independently indexable for SEO. Add to sitemap.
- [ ] **Client-side search** (audit §7C) — Dump all archive JSON into `search-index.json`, add `/search.html` with JS filtering. No backend needed.
- [ ] **"Best of CatchTheBrief" page** (audit §7D) — `/best.html`, manually curated 10–15 briefs, updated monthly. Great for sharing on Reddit/LinkedIn as a standalone URL.
- [ ] **Subscriber count social proof** (audit §7E) — Hardcode "Join 50+ readers" in newsletter CTA, update weekly from MailerLite dashboard. Or: MailerLite API call at build time → `{{SUBSCRIBER_COUNT}}` injection.
- [ ] **OG image improvement** (audit §7F) — Current Pollinations images look generic. Option: category-branded title card (large text, category color gradient). More distinctive social share appearance.

### Technical
- [ ] `news_engine.py` (root) — old legacy engine, can be deleted once confirmed unused
- [ ] `templates/archive.html` — check it's in sync with current category CSS class names
- [ ] Loading shimmer for card images (CSS `@keyframes shimmer` on `.card-img-wrap`)
- [ ] Dark mode support (CSS `prefers-color-scheme: dark`) — plan for Session 13+
- [ ] PWA `manifest.json` — Add to Home Screen support

---

## LinkedIn Setup Reminder

LinkedIn access token expires every **60 days**. To refresh:
1. Go to LinkedIn Developer App → Auth tab → OAuth 2.0 tools
2. Generate new access token with `w_member_social` scope
3. Update `LINKEDIN_ACCESS_TOKEN` secret in GitHub repo settings

Current token was last set: **[Update this when you refresh]**

---

## Session 10 Suggested Focus

Given priority order (Content → SEO → Design → Distribution):

**Session 10 — Content + SEO + Design gaps:**
- Review first batch of articles with new BRIEF_PROMPT to assess TAKE quality
- Add site tagline for new visitors (below date herald in index.html — 2 lines)
- Separate Share vs Follow sections in article.html
- Add YourStory max-1 hard limit to ranking prompt
- Add `about.html` and `privacy.html` to sitemap
- Add prev/next article navigation
- Submit to Google News Publisher Center (30 min manual action)

**Session 11 — Distribution + Growth:**
- Reddit posting strategy — set up 3x/week rhythm (manual, 10 min/post)
- LinkedIn Newsletter feature setup (separate from daily posts)
- Weekly digest email script (`generate_weekly_digest.py`)
- Twitter/X thread format for manual posting
- Category pages generation

**Session 12 — UX + Discovery:**
- Category filter tabs on homepage (client-side JS)
- Client-side search across all briefs
- "Best of CatchTheBrief" curated page
- Loading shimmer for card images

---

## Key Config Values

```
SITE_URL:            https://catchthebrief.com
SITE_NAME:           CatchTheBrief
MailerLite Account:  2285640
MailerLite Form:     185448516399662487
Telegram Chat ID:    -1003783025490
Google Analytics:    G-V6N03CT88P
Gemini Model:        gemini-2.5-flash
Groq Model:          llama-3.3-70b-versatile
```
