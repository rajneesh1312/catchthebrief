# CatchTheBrief — Claude Handoff After Session 11

**Date:** 13 May 2026
**Session focus:** Content quality — kill the "AI wrote this" tells in generated briefs
**Trigger:** Live audit of 10 sessions revealed the site infrastructure was strong but every published article had 3-5 obvious AI tells (forced metaphor openers, generic "Why India", empty TAKE sections, source bias to YourStory + Inc42)

---

## What Was Done in Session 11

Session 11 was a focused content-quality push driven by iterative live testing. Five engineering changes shipped, validated across **6 successive engine reruns** on the same news day, with each rerun analyzed for specific regressions and improvements before the next change.

### 1. Per-feed cap in fetch (round-robin pool)
**File:** [fetch_and_rank.py](../fetch_and_rank.py) `fetch_all_articles()`
**Change:** Replaced `all_articles[:25]` (first-25-in-feed-order) with `per_feed_cap=4` per source.
**Why:** RSS feeds iterate in list order. With the old slice, TechCrunch + YourStory + Inc42 ate all 25 slots before gadgets360 / medianama / the-ken were ever read. AI ranker only saw 2 sources.
**Effect:** First time in the project's history that **The Ken** and **MediaNama** appeared in published briefs.

### 2. Code-level diversity enforcement
**File:** [fetch_and_rank.py](../fetch_and_rank.py) `enforce_source_diversity()`
**Change:** New function — runs after AI ranking, applies hard caps (yourstory: 1, others: 2), swaps violators with under-represented sources, with **soft fallback** if pool is exhausted (logs `⚠ soft override`).
**Why:** Prompt-level "max 1 yourstory" rule from Session 10 was being ignored by the model 50%+ of the time. Code-level enforcement is non-negotiable.

### 3. Full article text fetch before brief generation
**File:** [generate_and_publish.py](../generate_and_publish.py) `extract_article_text()`
**Change:** Before calling the AI to write a brief, fetch the actual article page (~2.5-3K chars) and pass it as the `description` field in the prompt. Falls back to RSS summary on paywall / fetch failure.
**Why:** RSS summaries are 150-400 chars and rarely contain numbers, dates, named entities, or quotes — the prompt asks for these in KEY_FACTS but the AI literally could not see them.
**Effect:** **The largest single quality improvement of the session.** KEY_FACTS now contain cap-table data (₹4.95 Cr / 49.50 Lakh equity shares / face value ₹10), specific police stations (Navghar), regulatory body acronyms (IRDAI, WBAAAR, OPC), and named persons (CFO Dhiresh Bansal, founder Anindyadeep Sannigrahi). None of this existed in any previous build.

### 4. Brief prompt rewrite — operational, not descriptive
**File:** [generate_and_publish.py](../generate_and_publish.py) `BRIEF_PROMPT` (~120 lines)
**Change:** Replaced "be conversational, be specific" with:
- Explicit HARD BANS list (banned phrases, banned patterns, banned vocabulary)
- Per-section GOOD/BAD contrastive examples
- Mandatory specificity requirements per section (HOOK must have number in S1, KEY_FACTS must add new info beyond headline, WHY_INDIA must name non-Bangalore city, TAKE must pick one of 4 named stances: prediction / contrarian / who-wins-who-loses / what's-being-missed)
- **3-5 facts, not always 5** — explicit "do not pad with paraphrases"

### 5. Banned-phrase detector + retry guard + regex pattern
**File:** [generate_and_publish.py](../generate_and_publish.py) `BANNED_PHRASES`, `ISN_T_PATTERN`, `find_banned()`
**Change:** After brief generation, run `find_banned()` to scan all sections for banned literals and a compiled regex pattern. If hits found, retry once with an explicit "your previous draft contained X" prompt. Cap: 1 retry per brief = +5 AI calls/day worst case (still 0.24% of free-tier quota with 3-key rotation).

The regex specifically catches the "X (negation) (modifier) Y; it's Z" pattern across **18 negation verbs × 4 modifiers = 72 surface forms** — `isn't just`, `won't just`, `wasn't only`, `doesn't merely`, etc. Closes the dialect workarounds the model kept finding when we banned single phrases (`"this isn't just"` → `"isn't just"` → `"won't just"` were the v3/v4/v5 leaks).

---

## Live Validation — 6 reruns on 13 May 2026

Each rerun targeted the previous run's specific failures. Same date, same broad story pool, narrowing the AI tells with each change.

| Run | Source distribution | Briefs shipped | Banned hits | Key observation |
|---|---|---|---|---|
| v1 | 3 YourStory + 2 Inc42 | 5 | many | Moody's piece opened with *"Imagine you're planning a big road trip…"* — classic AI metaphor opener; "The Take" silently missing |
| v2 | 2 YS + 3 Inc42 | 5 | many | Hooks better, all 5 TAKEs opened with *"This isn't just X; it's Y"* (new tell emerged) |
| v3 | 1 YS + 2 Inc42 | **3** (cap too strict) | 2 | Hit the upstream feed-pool bottleneck — discovered the `[:25]` truncation bug |
| v4 | 1 YS + 2 Inc42 + 1 The Ken + 1 MediaNama | 5 | 2 ("isn't just" via "The real X isn't just…" / "this move reshapes") | First time 4 sources |
| v5 | 1 YS + 2 Inc42 + 1 The Ken + 1 MediaNama | 5 | 1 ("won't just" — tense workaround) | Most surface tells gone; one regex-able pattern left |
| **v6** | 1 YS + 2 Inc42 + 1 The Ken + 1 MediaNama | 5 | **0** | LiteFold TAKE genuinely restructured — *"Everyone is talking LLMs, but the real play here is in verticalized AI platforms…"* |

### Quality scorecard — first run vs final run

| Dimension | v1 (Run 1) | v6 (Final) |
|---|---|---|
| Distinct sources in top-5 | 2 | **4** (Inc42, YourStory, The Ken, MediaNama) |
| Hook leads with name/number | 1/5 | **5/5** |
| TAKE present + takes a position | 0/5 | **5/5** |
| KEY_FACTS with ≥1 specific datum each | ~5/25 | **22/22** |
| WHY_INDIA names cohort + non-Bangalore place | 0/5 | **5/5** |
| Banned-pattern hits | many | **0** |

---

## Architecture Overview (unchanged from Session 10)

**Two-step daily engine:**
- **Step 1** (`fetch_and_rank.py`) — 10:00 PM IST: Fetches RSS from 9 sources (effectively 5 — see "Known Issues" below), filters, AI-ranks, enforces source diversity, saves `review_candidates.json`
- **Step 2** (`generate_and_publish.py`) — 8:00 AM IST: Reads candidates, fetches full article text per pick, generates briefs with banned-phrase guard + retry, builds all HTML, pushes to GitHub Pages

**AI stack:** Gemini 2.5 Flash (3-key rotation, primary) → Groq Llama 3.3 70B (fallback)
**Images:** Pollinations.AI (still unchanged — flagged in audit as a credibility issue, not addressed this session)
**Daily AI usage:** 6 calls baseline + up to 5 retries = 11 calls/day max — **0.24% of free-tier quota** with 3-key rotation

---

## Current File State

| File | State |
|------|-------|
| `fetch_and_rank.py` | Updated — per-feed cap (round-robin), `enforce_source_diversity()` with soft fallback |
| `generate_and_publish.py` | Updated — `extract_article_text()`, new `BRIEF_PROMPT`, `BANNED_PHRASES` + `ISN_T_PATTERN` regex, `find_banned()` + retry logic in `generate_brief()` |
| `templates/*.html` | Unchanged from Session 10 |
| `manual_briefs.json` | Still empty — editorial-override system in place but unused |

---

## Known Issues — Worth Addressing Soon

### Broken / dormant feeds (deferred from this session)
Diagnostic in this session found:

| Feed | Status |
|---|---|
| `entrackr.com/feed/` | HTTP 404 — URL changed or feed retired |
| `cnbctv18.com/tech/feed/` | HTTP 404 |
| `analyticsindiamag.com/feed/` | Returns non-XML (parse fails on line 1) |
| `techcrunch.com/tag/india/feed/` | Live but dormant — newest post was 5 days old |

Effectively the project runs on 5 working feeds (YourStory, Inc42, the-ken, gadgets360, medianama), not 9. **Fixing these 4 URLs would unlock 4 more sources for the diversity rotation** — worth a 30-minute investigation session. Likely fixes:
- `entrackr.com/feed.rss` or `/feed/?type=rss` (test)
- `cnbctv18.com/rss/tech.xml` (test, check their current RSS index)
- `analyticsindiamag.com/feed/?paged=1` or `/rss` (test)
- Drop techcrunch India tag, replace with `techcrunch.com/category/startups/feed/` + India-keyword post-filter

---

## Remaining from Session 10 Audit (still TODO)

### Content (most are now solved — see strikethrough below)
- ~~STRONGLY PREFER external validation in ranking~~ → effectively handled by full-article-fetch giving AI real data
- ~~AI prompt for TAKE could include 2-3 example takes~~ → done, 4 stances + GOOD/BAD examples in prompt
- ~~Hook quality depends entirely on AI~~ → still true but prompt rewrite + retry guard close most slop; manual brief override still available for top-priority stories
- [ ] **Hero card image quality** — Pollinations.AI illustrations are generic and look obviously AI. Audit §7F flagged this. **Now the single biggest "this is AI" tell remaining on the site.** Suggested fix: category-branded title cards (large headline text on category color gradient, "CTB" mark, ~1200×630). Generated server-side at publish time. ~2 hours.

### SEO
- [ ] **Google News review** — submitted manually 13 May 2026. Check status weekly at `publishercenter.google.com`. Review takes 1-4 weeks.
- [ ] `lastmod` for historical articles should use actual file mtime, not today's date
- [ ] Archive day pages missing `og:image`
- [ ] Article image alt text currently = title (improve in engine to descriptive alt)

### Design
- [ ] Top bar (`Subscribe free →`) could rotate: show today's date OR tease top story
- [ ] Mobile hero card hook preview truncation could show more

### Distribution (manual actions)
- [ ] Reddit — 3x/week to r/indianstartups (131K), r/IndiaInvestments (120K), r/india (1.1M for big stories only). Write hook + 2-3 facts in body, end with link. 10 min/post.
- [ ] LinkedIn Newsletter — create "India Tech Digest" weekly Sunday send. 15 min/week.
- [ ] Twitter/X thread format — 5-tweet thread > single link tweet. ~10× impressions.
- [ ] IndieHackers "How I Built This" post (one-time, 1 hour, permanent organic backlinks)
- [ ] Quora answers on "best India tech newsletter" / "India startup news" (one-time per question, ranks on Google)
- [ ] LinkedIn token refresh — every 60 days
- [ ] Twitter/X auto-posting (post_to_twitter.py exists but unused — needs paid API tier)

---

## **Suggested Next Sessions — Reordered Priorities**

The Session 9 audit's priority order was: Content → SEO → Design → Distribution.

**After Session 11, content quality from the engine is genuinely strong.** The next 10× of trust and engagement won't come from more prompt engineering — it comes from **human fingerprints on the product**. Reordered priorities:

### Session 12 — The Human Editor Layer (HIGH IMPACT)
The site currently announces itself as AI-run on the About page. Every credibility signal is missing. This session adds the visible human layer.

- [ ] **Named editor on footer** of every page: *"Edited by [Name] · email"*. Photo + bio page at `/editor.html`.
- [ ] **Rewrite About page** — remove the *"runs entirely on AI-assisted tooling"* line. Replace with a real "Why I started this" paragraph in first person. Editor's contact email visible.
- [ ] **Weekly "Editor's Note"** — Sunday 7 AM IST cron. 150-300 words, manually written. New script `generate_editor_note.py` reads `editor_notes/YYYY-MM-DD.md`, builds a styled page, links from homepage. If no note file for the week, falls back gracefully.
- [ ] **Manual briefs cadence** — commit to 2 manual briefs per week using the existing `manual_briefs.json` system. Top story + your actual take. (No code change needed — the override system already works.)
- [ ] **"Reader's response" footer** on every article — `mailto:` link or Tally form: *"Disagree? Reply →"*. Even publishing 1 reply/week signals a human is reading.

### Session 13 — Replace AI Images (HIGH SEO + CREDIBILITY IMPACT)
The Pollinations illustrations are the second-loudest "AI-made" signal. Static title cards solve this in one shot.

- [ ] **Generated category title cards** — server-side at publish time. 1200×630 PNG or SVG. Large headline (Space Grotesk), category color gradient background, small CTB wordmark bottom-right. Replaces all Pollinations URLs in hero / og:image / card images.
- [ ] **Archive day-page `og:image`** — same template, but day-summary version.
- [ ] **Default fallback OG image** at `/images/og-default.jpg` — also a static title card.

### Session 14 — Growth Features (post-quality-baseline)
Per audit §7A-E, in priority order:

- [ ] **Weekly digest email** (`generate_weekly_digest.py`) — Sunday 9 AM IST. Reads last 7 days of archive JSON, assembles top 5, generates MailerLite campaign. Zero new AI calls.
- [ ] **Streak indicator on homepage** — *"Day 47 — we haven't missed a morning."* Tiny social proof, updates from a counter file.
- [ ] **Subscriber count social proof** in newsletter CTA — *"Join N readers"*. Either hardcoded weekly update from MailerLite dashboard, or live via MailerLite API at build time.
- [ ] **"Best of CatchTheBrief"** page at `/best.html` — manually curated 10-15 briefs, updated monthly. Great for sharing as a standalone URL on Reddit/LinkedIn.

### Session 15 — Discovery (optional polish)
- [ ] Category pages (`/category/ai-ml.html`, `/category/startup-funding.html` etc.) — generated from archive JSON, sitemap entries
- [ ] Client-side search (`search-index.json` + `/search.html`) — Lunr.js or simple JS filter
- [ ] Category filter tabs on homepage (client-side JS)
- [ ] Loading shimmer for card images

### Session 16+ — Long Tail
- [ ] Dark mode (`prefers-color-scheme: dark`)
- [ ] PWA `manifest.json`
- [ ] Quote-pull cards from TAKE sections (1080×1080 social images, auto-posted to LinkedIn/Twitter)
- [ ] Dedupe + redirect old non-date-prefixed articles in `/articles/` (~10 duplicate pages from Session 1-4 — Tim Cook variants, m2p-fintech variants, Apple CEO variants etc.)

---

## What I'd Watch Over the Next 3-5 Builds (Before Touching Code Again)

Three signals to monitor without changing anything:

1. **`find_banned` returns clean** across all 5 briefs — or does the model find a new dialect we haven't seen?
2. **Article fetch success rate** — watch logs for `Article fetch returned nothing — using RSS summary`. The-ken occasionally paywalls; if it becomes regular, we'd want a fallback.
3. **Diversity enforcer soft override** — watch for `⚠ soft override` log lines. If they fire often, the upstream feed pool is too narrow and we'd need to fix the 4 broken feeds.

If all three stay quiet for a week, the engine is in a genuinely strong baseline state and the work shifts entirely to the editorial-human layer (Session 12).

---

## LinkedIn Setup Reminder

LinkedIn access token expires every **60 days**. To refresh:
1. LinkedIn Developer App → Auth tab → OAuth 2.0 tools
2. Generate new token with `w_member_social` scope
3. Update `LINKEDIN_ACCESS_TOKEN` secret in GitHub repo settings

Current token last set: **[Update this when you refresh]**

---

## Key Config Values (unchanged)

```
SITE_URL:            https://catchthebrief.com
SITE_NAME:           CatchTheBrief
MailerLite Account:  2285640
MailerLite Form:     185448516399662487
Telegram Chat ID:    -1003783025490
Google Analytics:    G-V6N03CT88P
Gemini Model:        gemini-2.5-flash
Groq Model:          llama-3.3-70b-versatile
Per-feed cap:        4 articles/feed (new in Session 11)
Source caps:         yourstory.com=1, others=2 (new in Session 11)
Article fetch:       max 3000 chars per URL (new in Session 11)
```

---

## Files Changed in Session 11

```
generate_and_publish.py
  + extract_article_text()        — fetches article body, strips HTML
  + BANNED_PHRASES (list)         — literal slop phrases
  + ISN_T_PATTERN (regex)         — 72-form negative-contrast pattern
  + find_banned()                 — runs both checks, normalizes apostrophes
  ~ BRIEF_PROMPT                  — full rewrite (HARD BANS, per-section GOOD/BAD, mandatory specificity)
  ~ generate_brief()              — fetches full text, runs banned-phrase guard, retries once on hit

fetch_and_rank.py
  ~ fetch_all_articles()          — per-feed cap (round-robin) instead of [:25] truncation
  + enforce_source_diversity()    — code-level caps with soft fallback
  + SOURCE_CAPS, _domain_of()     — helpers
  ~ main()                        — calls enforce_source_diversity after AI rank, logs before/after
```

No template changes. No CSS changes. No new dependencies.
