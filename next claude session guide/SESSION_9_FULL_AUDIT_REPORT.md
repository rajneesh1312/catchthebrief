# CatchTheBrief — Full Project Audit Report
## Session 9 Analysis | Date: 13 May 2026
### Covers: Content Quality · Design · Distribution · Repository · Growth Strategy

---

> **How to use this document**
> Read through, mark your own notes inline, and use the Session Roadmap at the bottom
> to create the updated handoff file for the next Claude session.
> Each section has a ✅ POSITIVES block and an ❌ ISSUES/MISSING block,
> followed by concrete ACTION STEPS.

---

## TABLE OF CONTENTS

1. [Project Health Summary](#1-project-health-summary)
2. [Content Quality Audit](#2-content-quality-audit)
3. [Design & Visual Audit](#3-design--visual-audit)
4. [Distribution Strategy Audit](#4-distribution-strategy-audit)
5. [Repository & Technical Audit](#5-repository--technical-audit)
6. [SEO Audit](#6-seo-audit)
7. [Growth Feature Gaps](#7-growth-feature-gaps)
8. [Prioritised Session Roadmap](#8-prioritised-session-roadmap)
9. [Quick Reference — All Action Items](#9-quick-reference--all-action-items)

---

## 1. PROJECT HEALTH SUMMARY

### What CatchTheBrief Is (Current State)

- Automated daily news briefing site for India tech & startup audience
- 5 AI-curated briefs published every morning at 8 AM IST
- Fully free infrastructure: GitHub Pages + GitHub Actions + free AI APIs
- 28 days of published content (April 15 – May 12, 2026)
- Distribution: Telegram (auto) · WhatsApp Channel (manual) · Email (MailerLite) · LinkedIn (just added) · Twitter/X (manual)

### Overall Health Rating

| Area | Rating | Notes |
|---|---|---|
| Technical infrastructure | 8/10 | Solid, zero cost, runs reliably |
| Content quality | 5/10 | Formatted well, but generic voice, no opinion |
| Design & UX | 6/10 | Good foundation, critical UX gaps |
| SEO | 4/10 | Broken sitemap, missing pages, no Twitter cards on homepage |
| Distribution | 4/10 | Channels exist, no active growth strategy |
| Repository hygiene | 4/10 | Outdated README, no .gitignore, orphan files |

### The Core Problem in One Paragraph

CatchTheBrief's briefs are technically correct but editorially generic.
They are well-formatted summaries of articles that the target audience
(India tech professionals) have likely already seen on Inc42 or YourStory.
There is no distinctive voice, no opinion, no reason to choose CatchTheBrief
over reading the source directly. The design is solid but has broken UX
patterns (no next/prev navigation, wrong conversion order, missing freshness signals).
The distribution channels exist but are passive — no active audience acquisition strategy.

---

## 2. CONTENT QUALITY AUDIT

### 2A. How Content Is Generated (Current Flow)

```
10:00 PM IST — fetch_and_rank.py runs
  → Pulls from 8 RSS feeds (max 25 articles, past 36 hours)
  → Filters junk keywords
  → Source diversity filter (max 3 per source in candidate pool)
  → AI ranks top 15 → selects best 5 (topic diversity enforced)
  → Saves review_candidates.json

[Manual review window: 10 PM to 7:30 AM]

8:00 AM IST — generate_and_publish.py runs
  → Reads review_candidates.json
  → For each of 5 candidates: calls Gemini (fallback: Groq)
  → Generates: Title, Category, Read Time, Hook, Context, 
               Key Facts (5 bullets), What Next, Why India
  → Builds HTML pages, sitemap, archive, publishes to GitHub Pages
```

### 2B. Current Content Sources

| Source | Type | Quality |
|---|---|---|
| Inc42 | India startup news | Medium — some original, some PR |
| YourStory | India startup news | Low-Medium — heavy PR bias |
| Entrackr | India funding/startup scoops | High — original reporting |
| The Ken | India business deep-dives | High — but paywalled, feed is limited |
| TechCrunch India | Global tech with India tag | Medium — US-first angle |
| Gadgets360 | India tech products | Low for this audience |
| Medianama | India digital policy | High for policy stories |
| Analytics India Mag | India AI coverage | Medium — generic |

### 2C. ✅ WHAT IS WORKING — Content

- **Brief format structure is correct.** Hook → Context → Key Facts → What Next → Why India mirrors how Finshots structures their content
- **Gemini 2.5 Flash produces readable language** — no major grammar or coherence issues
- **Groq fallback works** — continuity even when Gemini quota hits
- **Manual review window is well-designed** — 10-hour window gives editorial control without needing to be awake at 8 AM
- **Category system is well-chosen** — 5 categories cover the India tech niche appropriately
- **Source diversity filter prevents single-source days** — at least at candidate pool level
- **manual_briefs.json is now in place** — persistent editorial override ready to use (added Session 9)

### 2D. ❌ WHAT IS BROKEN — Content

**Problem 1: No editorial voice or opinion**
Every brief reads like "Here is what happened." Great content sites add:
"Here is what happened, and here is what WE think about it."
Finshots ends every brief with their take. Morning Brew adds wit and commentary.
CatchTheBrief adds nothing beyond a structured summary.
Result: Readers feel nothing. They don't share it. They don't come back.

**Problem 2: "Why India" section is always generic filler**
Examples from actual published briefs:
- "makes daily commutes better and showcases how tech can empower talent from all corners of India"
- "crucial pulse check on the health of India's burgeoning tech economy"
- "This story has direct relevance to India's growing tech ecosystem."
These sentences could be pasted onto ANY brief and no one would notice.
They are meaningless. The section exists but delivers zero value.

**Problem 3: Hooks open with questions — lazy AI default**
Example: "Ever been stuck on a Mumbai local platform, wondering when your train
will *actually* show up?"
Question-based hooks are the first thing AI defaults to when it isn't pushed harder.
Real storytelling hooks establish stakes and tension, not ask the reader a question.

**Problem 4: Key Facts are product features, not news facts**
Example (Yatri brief): 4 of 5 "key facts" describe what the app does
(shows train location, shows delays, shows platform changes).
These are product features, not what is newsworthy.
The newsworthy angle (talent sourcing beyond Bengaluru) was Fact 5.
The AI is summarising the article rather than identifying the news angle.

**Problem 5: Exclamation marks in every headline**
From May 12 archive: 4 of 5 headlines end with `!`
- "CashKaro Crushes It: Revenue Up 72%, Profitability Within Reach!"
- "Digital Gold Gets Its Own Watchdog: New Rules Brewing!"
No credible news publication uses exclamation marks in headlines.
This makes the site look like clickbait. The BRIEF_PROMPT does not prohibit this.

**Problem 6: Markdown asterisks appearing as literal text in HTML**
When Gemini uses *word* for emphasis in its output, the asterisks appear
as literal characters in the rendered HTML: "It was *actually* a major shift."
The parse_brief() function does not strip or convert markdown formatting.

**Problem 7: Source concentration — 4 of 5 from same source**
May 12 archive: 3 articles from inc42.com, 2 from yourstory.com.
Today's review_candidates.json: 4 of 5 from yourstory.com.
The source diversity filter (max 3/source in candidate pool) is not
preventing this at the final-5 level. The AI ranking is consistently
picking multiple articles from the same source.

**Problem 8: YourStory articles are often press releases**
YourStory publishes 30+ articles per day, many of which are founder-submitted
PR pieces with no external validation. These should be weighted lower
in the ranking prompt or capped at 1 per day at the final-5 level.

### 2E. ACTION STEPS — Content (Session 10)

```
STEP 1 — Add to BRIEF_PROMPT (3 new instructions):

  "Before writing, identify the ONE most surprising or counterintuitive
   thing about this story. Lead with that. Do not open with a question.
   Open by establishing stakes."

  "WHY_INDIA must include at least one specific number, city name, job type,
   or sector. Generic phrases like 'India's growing tech ecosystem' or
   'this matters for Indian tech workers' are not acceptable. Be specific."

  "Never use exclamation marks (!) in the TITLE."

STEP 2 — Add new brief section: TAKE

  After WHY_INDIA, add:
  TAKE: [One opinionated sentence. Is this good news, a warning sign,
         overhyped, or underrated? Example: 'This looks like a growth story
         but the unit economics suggest the next 12 months are the real test.'
         Never say 'time will tell' or 'only time will tell'. Take a position.]

STEP 3 — Fix parse_brief() in generate_and_publish.py

  Before returning the parsed brief dict, strip markdown artifacts:
  - Replace *word* → word (remove asterisks used for emphasis)
  - Replace **word** → word
  - Strip leading/trailing asterisks from any field value

STEP 4 — Update rank_articles() prompt in fetch_and_rank.py

  Add to ranking criteria:
  "STRONGLY PREFER: Stories with external validation (analyst quotes,
   regulatory action, actual user/revenue numbers from named sources).
   AVOID: Stories where the only source is the founder/company
   (press releases, funding announcements with no lead investor named,
   product launches with no user numbers)."

  Add to ranking criteria:
  "HARD LIMIT: Select maximum 2 articles from any single source domain
   in the final TOP5. If 3+ candidates from the same source are ranked
   highest, replace the 3rd+ with the next best from a different source."

STEP 5 — Add source name mapping in fetch_and_rank.py

  SOURCE_NAMES = {
    "yourstory.com":          "YourStory",
    "inc42.com":              "Inc42",
    "entrackr.com":           "Entrackr",
    "the-ken.com":            "The Ken",
    "techcrunch.com":         "TechCrunch",
    "gadgets360.com":         "Gadgets360",
    "medianama.com":          "Medianama",
    "analyticsindiamag.com":  "Analytics India Mag",
  }
  Use SOURCE_NAMES.get(domain, domain) when saving candidates.

STEP 6 — Add new RSS sources, deprioritise weak ones

  ADD:
    https://www.cnbctv18.com/tech/feed/ (CNBCTV18 Tech)

  LIMIT YourStory to max 1 in final-5 (add to ranking prompt).
```

---

## 3. DESIGN & VISUAL AUDIT

### 3A. Design System Overview

| Element | Value |
|---|---|
| Heading font | Space Grotesk (Google Fonts) |
| Body font | Inter (Google Fonts) |
| Primary accent | #2563EB (blue) |
| Background | #FAFAFA |
| Card background | #FFFFFF |
| Text primary | #1A1A2E |
| Max width (homepage) | 1100px |
| Max width (article) | 680px |
| Category colors | Purple · Green · Red · Amber · Blue |

### 3B. ✅ WHAT IS WORKING — Design

- **Typography pairing** (Space Grotesk + Inter) is professional and readable
- **CSS variable system** is clean and well-organised — easy to maintain
- **Color system** is coherent — category badge colors are distinct and accessible
- **Hero card layout** (image + text side by side) is the right pattern for a featured article
- **Frosted glass sticky header** with backdrop-filter is modern
- **Reading progress bar** on article page — professional signal
- **Newsletter section** dark gradient with decorative circles looks polished
- **Card hover animations** (translateY -2px, shadow lift) are subtle and correct
- **Responsive design** — mobile breakpoints at 768px and 480px are implemented
- **Archive page** is cleanly structured with good visual hierarchy

### 3C. ❌ BROKEN — Things That Look Broken to Readers

**Issue 1: Empty publication date creates broken meta bar**
Every article shows: "AI & ML · 3 min read · "
The trailing dot-and-space comes from the `{{PUB_DATE}}` tag rendering empty.
pub_date is never populated in the engine, but the separator `·` renders regardless.
Fix: Wrap the separator and date span in a conditional — only render if pub_date is not empty.

**Issue 2: ARTICLE_INDEX and TOTAL_ARTICLES passed but never used**
The engine passes `{{ARTICLE_INDEX}}` and `{{TOTAL_ARTICLES}}` to every article page.
The template ignores them. The "Brief 2 of 5" concept is invisible.
This means there is no way for a reader to navigate between today's 5 briefs.
After reading Article 1, they are stuck — no next/prev button exists.

**Issue 3: Markdown asterisks in brief text**
Some briefs contain *word* displayed as literal asterisks in HTML.
Looks like broken template rendering to any reader.

### 3D. ❌ MISSING — UX Gaps That Cost Readers

**Gap 1: No previous/next article navigation**
The single highest-impact missing feature on the article page.
After reading Brief 1, there is no way to go to Brief 2 without returning to homepage.
This kills session depth — the goal is for each reader to read all 5 briefs.
The engine already passes ARTICLE_INDEX and TOTAL_ARTICLES. The slugs for all 5
briefs of the day are available. This needs a Previous/Next button row at article bottom.
Format: "← Brief 1/5: [Previous title]     Brief 3/5: [Next title] →"

**Gap 2: No date headline — site doesn't feel fresh**
The homepage has no prominent display of today's date.
The date appears in tiny muted text in the section intro.
A news site must feel time-anchored. "Wednesday, 13 May 2026" in visible type
immediately signals: this is today's news, not old content.

**Gap 3: No above-the-fold explanation for new visitors**
A new visitor landing on catchthebrief.com sees: top bar, header, articles.
Zero context about what this site is, how often it updates, or why to read it here
instead of Inc42. 15 words above the hero card would solve this:
"5 India tech & startup stories. Written clearly. Every morning at 8 AM."

**Gap 4: Newsletter CTA is between articles and yesterday's briefs**
Current order: Today's articles → NEWSLETTER CTA → Yesterday's briefs → Footer
The newsletter CTA appears BEFORE the reader has finished reading today's content.
Correct order: Today's articles → Yesterday's briefs → NEWSLETTER CTA → Footer
Subscribe prompt should come after the reader has consumed the value, not before.

**Gap 5: Newsletter headline is overused industry cliche**
"Never miss a brief" — every single newsletter on the internet says this.
Should be specific and value-driven:
"5 stories. 15 minutes. Everything that matters in India tech."

**Gap 6: Conversion element order on article page is wrong**
Current: Article → Share buttons → Newsletter CTA
Correct: Article → Newsletter CTA → Share buttons
The newsletter ask should come while the reader is most engaged (immediately after reading),
not after they've already decided whether to share and leave.

**Gap 7: Share section and Follow section are crammed together**
"Share this brief" (WhatsApp, Twitter, Reddit, Copy) and
"Follow CatchTheBrief" (Channel links) are both inside the same visual box.
Two different actions in one container. Readers visually skip one or both.
They should be separated into distinct visual components.

**Gap 8: Top bar is wasted real estate**
"📬 Get 5 India tech briefs every morning — Subscribe free →"
This is static and identical every day. After the first visit it is ignored.
Better use: display today's date and brief count, or tease the day's top story.
Makes the bar worth looking at on repeat visits.

**Gap 9: Card preview text clamped too aggressively**
Grid cards show only 2 lines of hook preview (~80-100 characters).
Not enough to make the reader want to click. Should be 3 lines.

**Gap 10: Section label "TODAY'S BRIEFS" is invisible**
13px, uppercase, muted color — this is the most important heading on the page
and it reads like a footnote. Either enlarge it or replace with the date headline.

### 3E. IMPROVEMENTS — Visual Polish

**Improvement 1: Section label text could have more personality**
Current → Suggested upgrade:

| Current | Upgrade |
|---|---|
| The Backstory | How We Got Here |
| Key Facts | The Numbers |
| What to Watch | What Happens Next |
| Why This Matters for India | The India Angle |

This is a pure text change — zero code, zero breaking changes.
4 lines changed in article.html template.

**Improvement 2: Logo needs a symbol mark**
"CatchTheBrief" as text works for desktop. But there is no symbol —
no icon mark that works at 16×16 as a WhatsApp DP, social media icon, or sticker.
The favicon is just "C" in a blue square. As the brand grows, a proper
logomark (even a simple abstract shape) is needed.

**Improvement 3: Dark mode is not supported**
In 2026, a large share of mobile users (especially at night) use dark mode.
The site forces white-on-dark on everyone.
Not a blocker now, but plan for Session 12+.

**Improvement 4: No loading skeleton for cards**
When Pollinations images are slow to load (2-5 seconds), cards show flat background.
A CSS shimmer loading state would make the page feel faster and more polished.

**Improvement 5: Category filter tabs on homepage**
A simple tab row — All · AI & ML · Startup · Policy — would dramatically
improve engagement for returning readers who only care about one topic.
Pure client-side JavaScript, no backend needed.

### 3F. ACTION STEPS — Design (Sessions 10 + 11)

```
SESSION 10 — Quick wins (text + template only, no engine changes needed):

  STEP 1 — Change section labels in article.html:
    "The Backstory"      → "How We Got Here"
    "Key Facts"          → "The Numbers"
    "What to Watch"      → "What Happens Next"
    (Keep "Why This Matters for India" — it's distinctive)

  STEP 2 — Fix empty pub_date separator in article.html:
    Wrap the meta-sep and meta-item spans in a JS conditional,
    OR populate pub_date from the RSS feed in the engine.

  STEP 3 — Fix newsletter CTA placement on article page:
    Move newsletter-cta div ABOVE the share-section div.

  STEP 4 — Separate Share and Follow into distinct sections:
    Share buttons (WhatsApp, Twitter, Reddit, Copy) → keep in share-section
    Follow buttons (Channel links) → move below newsletter CTA, own styled row

  STEP 5 — Increase card preview clamp from 2 lines to 3 in index.html:
    Change -webkit-line-clamp: 2 to -webkit-line-clamp: 3 on .card-preview

  STEP 6 — Change newsletter headline:
    "Never miss a brief"
    → "5 stories. 15 minutes. Everything that matters in India tech."

  STEP 7 — Move newsletter section on homepage:
    AFTER {{YESTERDAY_BRIEFS}}, not between articles and yesterday.

  STEP 8 — Add date headline above hero card on homepage:
    Replace/augment the section-intro to show "Wednesday, 13 May 2026"
    prominently above the articles.

  STEP 9 — Add 2-line site tagline for new visitors:
    Below the date headline:
    "5 India tech & startup stories. Written clearly. Every morning at 8 AM."

SESSION 11 — Bigger UX improvements:

  STEP 10 — Previous/Next article navigation:
    The engine already passes ARTICLE_INDEX and TOTAL_ARTICLES.
    Add prev_slug and next_slug to generate_article_page().
    Add nav row at article bottom with links to prev/next brief.

  STEP 11 — Category filter tabs on homepage:
    5 buttons (All, AI & ML, Startup Funding, Digital India, India Tech)
    Client-side JS hides/shows cards by category class.

  STEP 12 — Loading shimmer for card images:
    CSS @keyframes shimmer on card-img-wrap before image loads.
```

---

## 4. DISTRIBUTION STRATEGY AUDIT

### 4A. Current Distribution Channels

| Channel | Status | Automation | Reach |
|---|---|---|---|
| Email (MailerLite) | Live | Form on site | 0 subscribers estimated |
| Telegram | Auto-posting daily | Yes (bot) | Channel created |
| WhatsApp Channel | Manual posting | No | Channel created |
| Twitter/X | Manual daily | No | New account, low reach |
| LinkedIn | Auto-posting (just added) | Yes (needs token setup) | Personal account reach |
| Reddit | Share button added | No | No posts yet |

### 4B. ✅ WHAT IS WORKING — Distribution

- All major channels have been set up — foundation is in place
- Telegram auto-posting removes manual effort — content goes out reliably
- LinkedIn bot now added — will auto-post daily once tokens are configured
- WhatsApp Channel is created and branded
- Email form is functional on site

### 4C. ❌ THE ROOT PROBLEM

The distribution strategy is entirely passive. 
Channels are set up to receive content, but there is zero active audience acquisition.
The only people who can find CatchTheBrief right now are:
  a) People you personally shared the link with
  b) Anyone who accidentally finds it via Google (minimal, SEO is broken)
  c) Channel followers — but you need to grow those first

Passive distribution (posting content on channels) only works once you have an audience.
To get that audience, active distribution is required for the first 3-6 months.

### 4D. Tier 1 — Do This Week (Highest ROI, Zero Cost)

**Channel 1: Reddit — Active posting 3x per week**
Not just link-sharing. Post as community contribution.

Subreddits to post in:
- r/indianstartups (131K members) — for startup/funding/product stories
- r/IndiaInvestments (120K members) — for VC, IPO, fintech stories
- r/india (1.1M members) — only for major stories (policy, big company news)

How to post correctly:
- Write the hook text + 2-3 key facts as the Reddit post body
- End with: "Full brief here: [link]"
- Do NOT post bare links — they get removed by moderators
- Post 3x per week max — not daily. Reddit users flag spam.
- Comment on existing India startup threads with your brief as a resource

Expected result: 50-300 visitors per good post
Time cost: 10 minutes per post

**Channel 2: Google News Publisher Center submission (One-time)**
- Go to: https://publishercenter.google.com
- Submit catchthebrief.com for review
- Google News appears in the India section of Google News and Google Discover
- If accepted: potentially 100-1000+ readers per day on big stories
- Requirements: consistent publication schedule ✓, original content ✓, sitemap ✓
- Time cost: 30 minutes to set up
- This is FREE and potentially the biggest traffic source available

**Channel 3: LinkedIn Newsletter (Different from LinkedIn posts)**
LinkedIn has a separate "Newsletter" feature that:
- Sends email-style notifications to your followers
- Gets promoted in LinkedIn feeds with a newsletter badge
- Accumulates subscribers separately from connections
Create: "India Tech Digest" — weekly newsletter posting every Sunday
Best of the week's 5 stories, assembled from archive JSON.
Expected: 50-500 subscribers in first month from existing connections
Time cost: 15 minutes per week

**Channel 4: Twitter/X — Switch to thread format**
Instead of posting one link tweet, post a 5-tweet thread:
- Tweet 1: Hook from top story
- Tweets 2-5: One line summary of each brief
- Last tweet: "Full briefs: catchthebrief.com" + hashtags
Threads get ~10x more impressions than single-link tweets.
The hook text already exists — no new writing needed.

### 4E. Tier 2 — Do This Month

**Channel 5: IndieHackers project post**
Write a "How I Built This" post on IndieHackers.com.
The IH community values: automation + India + zero-cost infrastructure.
This gets organic backlinks (SEO benefit) + an initial burst of curious traffic.
One post, permanent benefit. Time cost: 1 hour.
URL: https://www.indiehackers.com

**Channel 6: WhatsApp groups — Targeted sharing**
Find 3-5 relevant WhatsApp groups:
- Local startup/tech WhatsApp groups (Jaipur, Rajasthan startup community)
- College alumni groups with tech professionals
- iSPIRT community groups
- Product management WhatsApp groups
Share 2-3 times per week, not daily.
Ask group admins for permission first.

**Channel 7: Quora — Answer relevant questions**
Search Quora for: "best India tech newsletter", "India startup news",
"how to follow Indian startups", "India tech updates"
Write genuine answers recommending CatchTheBrief.
These answers rank on Google permanently and drive long-tail traffic.
Time cost: 30 minutes, one-time setup per question.

### 4F. Tier 3 — After 100 Daily Readers

**Channel 8: Newsletter cross-promotion**
Find 3 small India-focused newsletters (finance, product, SaaS topics).
Propose mutual mentions: you mention them, they mention you.
No money changes hands. This is how Finshots grew early.

**Channel 9: Product Hunt launch**
Launch CatchTheBrief on Product Hunt.
One-time burst of traffic + high-quality backlinks.
Requires 5+ upvoters lined up before launch.
Plan it 2 weeks in advance. Don't launch randomly.

**Channel 10: Google Discover (longer term)**
Google Discover (Android home screen news cards) requires:
- Articles 1500+ words (current briefs: ~400-500 words) — need to grow length
- Strong click-through on article thumbnails (Pollinations images may not cut it)
- Consistent publication history (growing)
This is a 6-month goal, not a this-month goal.

### 4G. Hashtag Standards (Updated Session 9)

Telegram posts now use:
`#IndiaStartups #IndiaTech #IndianStartups #StartupIndia #CatchTheBrief`

LinkedIn posts use:
`#IndiaStartup #IndianStartups #IndiaTech #StartupIndia #TechNews`

Twitter/X threads should use:
`#IndianStartups #IndiaTech #StartupIndia #IndiaVC #TechTwitter`

---

## 5. REPOSITORY & TECHNICAL AUDIT

### 5A. ✅ WHAT IS WORKING — Technical

- Two-step workflow (fetch_and_rank + generate_and_publish) is clean and logical
- GitHub Actions runs reliably — 28 consecutive daily builds confirmed
- Gemini key rotation + Groq fallback — no single point of failure
- Pollinations images are free, deterministic, and automatic
- Archive system — 28 days of content preserved in JSON + HTML
- MailerLite integration is functional
- Telegram bot posts automatically every morning

### 5B. ❌ CRITICAL BUGS

**Bug 1: Sitemap only includes TODAY's 5 articles — 80+ are missing**
The `generate_sitemap()` function only adds today's article slugs.
Every article from April 15 – May 11 is absent from the sitemap.
Google cannot discover those 80+ articles.
This is the most significant SEO problem in the entire project.

Fix in generate_and_publish.py:
```python
def generate_sitemap(slugs, now):
    # Collect ALL article slugs from ARTICLES_DIR, not just today's
    all_article_files = sorted(ARTICLES_DIR.glob("????-??-??-*.html"), reverse=True)
    all_slugs = [f.stem for f in all_article_files]
    # today's slugs may not be written yet, so merge
    for s in slugs:
        if s not in all_slugs:
            all_slugs.insert(0, s)
    # then build sitemap from all_slugs
```

**Bug 2: LinkedIn token expiry will silently break daily site publish**
When the LinkedIn access token expires (every 60 days),
`post_to_linkedin.py` exits with error code 1.
GitHub Actions stops the workflow at that step.
The `git commit && git push` step never runs.
The site doesn't update that day. No visible error to the user.

Fix in generate_and_publish.yml — add `continue-on-error: true`:
```yaml
- name: Post daily Telegram message
  continue-on-error: true
  ...

- name: Post daily LinkedIn update
  continue-on-error: true
  ...
```

**Bug 3: requirements.txt contains lxml — banned on Windows**
The handoff explicitly states: "NO lxml — causes Windows build error"
But requirements.txt has `lxml==5.2.2`.
Anyone running `pip install -r requirements.txt` on Windows gets a broken install.
The GitHub Actions workflows bypass requirements.txt (they pip install directly),
which is why Actions works but local development does not.

Fix requirements.txt:
```
requests==2.31.0
beautifulsoup4==4.12.3
google-genai>=1.0.0
```
Remove lxml. Update google-genai from pinned 1.0.0 to >=1.0.0.

### 5C. ❌ ORPHAN FILES — Should Be Cleaned Up

| File/Directory | Problem | Action |
|---|---|---|
| `deals.html` | Old deals page, publicly accessible, paused feature | Delete |
| `deals/` directory | Old deals code/templates | Delete |
| `daily.yml` (repo root) | Old workflow file in wrong location (not in .github/workflows/) — never executed, just confusing | Delete |
| `New folder/` | Accidental Windows directory committed to repo | Delete |
| `news_engine.py` | Legacy engine — fine to keep, but README should clearly label it as legacy fallback | Update README label |

### 5D. ❌ MISSING STANDARD FILES

**Missing: .gitignore**
No .gitignore exists in the repository.
Python cache files, OS files, and potential .env files can be committed accidentally.

Contents to add:
```
__pycache__/
*.pyc
*.pyo
.env
.env.local
Thumbs.db
.DS_Store
*.log
```

**Missing: 404.html**
GitHub Pages serves /404.html for broken URLs.
Without it, any mistyped URL or broken link shows GitHub's generic grey 404 page,
sending readers completely off the site.
A custom 404 with site branding and links to today's briefs keeps readers on catchthebrief.com.

**Missing: about.html**
No /about.html exists. New readers who find CatchTheBrief via Google or Reddit
have no way to understand who runs this, why to trust it, or what makes it different.
An About page is also important for Google News eligibility review.

Contents needed (3 short paragraphs):
- What is CatchTheBrief (5 sharp India tech briefs, every morning, free)
- Who runs it (Rajneesh, based in India, built for professionals)
- How it works (AI curation + editorial review, published 8 AM IST daily)

**Missing: privacy.html**
MailerLite's terms of service require a privacy policy link in any email subscription form.
Without one, the MailerLite account is technically non-compliant.
One page is sufficient: what data is collected (email only), how it is used
(morning briefs only), and how to unsubscribe (one click).

### 5E. ❌ SECURITY / EXPOSURE ISSUES

**review_candidates.json is publicly accessible**
The file is committed to the repo and served via GitHub Pages.
Anyone can read catchthebrief.com/review_candidates.json before 8 AM
and see tomorrow's articles before they publish.
Not a security risk, but removes the morning freshness surprise.

Fix in robots.txt:
```
User-agent: *
Allow: /

Disallow: /review_candidates.json
Disallow: /manual_briefs.json
Disallow: /deals/
Disallow: /deals.html

Sitemap: https://catchthebrief.com/sitemap.xml
```

### 5F. README.md — Completely Outdated

The current README.md describes Session 1's architecture:
- References news_engine.py as the primary script (now legacy)
- References Google News RSS (replaced with India-focused feeds)
- References 10 categories (now 1 niche: India Tech & Startups)
- References Reddit deals section (paused)
- References Buttondown newsletter (replaced by MailerLite)
- References single GEMINI_API_KEY (now 3 keys + Groq fallback)
- References lxml as dependency (banned on Windows)

The README needs a complete rewrite reflecting the Session 9 current state.
This is important because: GitHub is public, potential collaborators/journalists
will find it, and it is the first thing anyone sees when they find the project.

### 5G. ACTION STEPS — Technical

```
SESSION 10:

  STEP 1 — Fix sitemap to include ALL article URLs from ALL days
  STEP 2 — Add continue-on-error: true to social posting steps in workflow
  STEP 3 — Fix requirements.txt (remove lxml, update google-genai)
  STEP 4 — Create .gitignore
  STEP 5 — Create 404.html with site branding
  STEP 6 — Create about.html
  STEP 7 — Create privacy.html
  STEP 8 — Update robots.txt to disallow review/manual JSON files
  STEP 9 — Delete deals.html, deals/, daily.yml (root), New folder/
  STEP 10 — Rewrite README.md to reflect current architecture

SESSION 11:
  STEP 11 — Add {{TAKE}} section from BRIEF_PROMPT to article template
  STEP 12 — Add source name mapping dict (yourstory.com → YourStory)
  STEP 13 — Populate pub_date from RSS feed in engine
```

---

## 6. SEO AUDIT

### 6A. ✅ WHAT IS WORKING — SEO

- Unique `<title>` and `<meta description>` per article ✓
- og:title, og:description, og:image per article ✓
- og:image on homepage ✓
- JSON-LD NewsArticle schema on every article ✓
- Canonical URLs on all pages ✓
- sitemap.xml exists ✓
- robots.txt points to sitemap ✓
- favicon.svg ✓
- lang="en-IN" on all pages ✓
- Google Analytics GA4 active ✓
- 28 days of daily published content — consistent schedule ✓

### 6B. ❌ SEO GAPS

| Gap | Impact | Fix |
|---|---|---|
| Sitemap only has today's 5 articles — 80+ missing | Critical | Fix generate_sitemap() to scan all articles |
| Homepage missing Twitter card meta tags | Medium | Add 4 meta tags to index.html template |
| Homepage missing JSON-LD structured data | Medium | Add WebSite + ItemList JSON-LD |
| Archive pages missing og:image | Low | Add default OG image to archive page HTML |
| No About page | Medium | Creates Google News credibility signal |
| No Privacy Policy | Medium | Required by MailerLite, signals legitimacy |
| Source names shown as domains not names | Low | Source name mapping dict |
| Article image alt text = title (not descriptive) | Low | Better alt text generation in engine |
| No Google News submission done yet | Critical | Submit to publishercenter.google.com |
| review_candidates.json indexed by Google | Low | Add to robots.txt Disallow |

### 6C. Google News Submission — Priority Action

Google News is potentially the biggest free traffic channel available.
Requirements CatchTheBrief currently meets:
✓ Consistent daily publication
✓ News-focused content
✓ Unique articles per day
✓ Sitemap (needs fixing first)
✓ Structured data (JSON-LD) on articles

Steps:
1. Fix sitemap to include all articles (prerequisite)
2. Create about.html (required for Google News review)
3. Create privacy.html
4. Go to https://publishercenter.google.com
5. Add property: catchthebrief.com
6. Verify ownership (Google Search Console — already set up with GA)
7. Submit for News content review
8. Wait 1-4 weeks for review decision

---

## 7. GROWTH FEATURE GAPS

Features that do not exist yet and would have measurable growth impact:

### 7A. Weekly Digest Email — Highest ROI Missing Feature

**What:** A Sunday "Week in India Tech" email: best 5 briefs from the past 7 days.
Automatically assembled from archive JSON — zero new content generation needed.

**Why it matters:**
- Daily newsletters: 20-30% open rates
- Weekly digests: 40-60%+ open rates consistently
- People choose a dedicated weekly reading time
- Most shareable format — "forward this to your team"

**How to build:**
- New script: `generate_weekly_digest.py`
  - Reads last 7 days of archive JSON
  - Picks top 5 by diversity (1 per category or AI-ranked)
  - Generates a MailerLite campaign via their API
  - Triggered by a new GitHub Actions cron: Sunday 9 AM IST
- Zero additional AI calls needed
- Zero new infrastructure needed

### 7B. Category Pages — SEO Multiplier

**What:** /category/ai-ml/ listing all AI & ML briefs ever published. 5 pages total.

**Why it matters:**
- Each category page is a new, independently-indexable SEO page
- Answers specific search queries: "India AI news", "India startup funding news"
- Gives repeat readers a bookmark destination for their specific interest
- LinkedIn posts can link to category page ("all India AI stories this month")

**How to build:**
- In `generate_archive_index()`, also generate 5 category pages
- Read all archive JSON, filter by category
- Output: /category/ai-ml.html, /category/startup-funding.html, etc.
- Add to sitemap

### 7C. Search Across All Briefs

**What:** A search bar that filters through all 80+ published briefs, client-side.

**Why it matters:**
- Users searching for "DPDP Act" or "Groww" or "Zomato" can find every brief
- No server needed — JavaScript filters the archive JSON
- Google values sites where users find answers via search
- Creates a "reference resource" use case beyond daily reading

**How to build:**
- Dump all archive JSON into a single `search-index.json`
- Add a search page (`/search.html`) with client-side JS filtering
- Or add a search widget to the archive/index.html page
- No new AI calls or infrastructure needed

### 7D. "Best of CatchTheBrief" Curated Page

**What:** A hand-picked /best/ page with 10-15 most interesting briefs from all time.

**Why it matters:**
- New readers can judge the site's quality immediately
- Shareable as a standalone URL: "check out the best stories"
- Works for Reddit/LinkedIn posts: share /best/ not just today's briefs

**How to build:**
- Static HTML page, manually curated
- You choose the 10 briefs, list them with links
- Updated once a month with new picks
- Zero automation needed — purely editorial

### 7E. Subscriber Count Social Proof

**What:** Display "Join 500+ India tech professionals" in newsletter CTA.

**Why it matters:**
- Proven conversion driver — people subscribe when they see others have
- Even 50 is worth displaying: "Join 50+ readers"
- Update manually once a week from MailerLite dashboard

**How to build:**
- Hardcode the number in the newsletter template
- Update manually once a week
- Or: MailerLite API to fetch subscriber count at build time
  (one API call in generate_and_publish.py, inject as {{SUBSCRIBER_COUNT}})

### 7F. Open Graph Image Improvement

**What:** Replace generic Pollinations flat-design images with more distinctive visuals.

**Why it matters:**
- The og:image is what social media shows when anyone shares your article
- Current images are generic blue/tech flat illustrations — look AI-generated at a glance
- A more distinctive image style would get more clicks from social shares

**Options:**
- Category-branded templates: consistent background color (from category color system)
  with article title as large text overlay — clean and brandable
- Use Pollinations with more specific/varied prompts per category
- Consider: a simple title-card style image (white text on dark gradient)
  generated with `textlayout` parameter in Pollinations

---

## 8. PRIORITISED SESSION ROADMAP

### Session 10 — Quality & Critical Fixes
**Focus: Make every brief worth sharing. Fix everything that looks broken.**

Quality:
- [ ] Rewrite BRIEF_PROMPT: angle-first, specific Why India, no exclamation marks
- [ ] Add TAKE section to prompt and article template
- [ ] Fix markdown asterisk stripping in parse_brief()
- [ ] Add source diversity hard limit (max 2 from same source in final-5) to ranking prompt
- [ ] Add source name mapping dict

Critical fixes:
- [ ] Fix sitemap — accumulate ALL article URLs, not just today's
- [ ] Add continue-on-error to Telegram and LinkedIn workflow steps
- [ ] Fix requirements.txt (remove lxml, update google-genai)
- [ ] Create .gitignore
- [ ] Delete orphan files (deals.html, deals/, daily.yml in root, New folder/)
- [ ] Rewrite README.md

Design quick wins:
- [ ] Rename article section labels (4 text changes)
- [ ] Fix empty pub_date separator
- [ ] Move newsletter CTA above share section on article page
- [ ] Increase card preview clamp from 2 to 3 lines
- [ ] Change newsletter headline

---

### Session 11 — Missing Pages & Distribution Setup
**Focus: Fill the gaps that affect credibility and SEO.**

Pages to create:
- [ ] 404.html — custom error page with branding
- [ ] about.html — 3 paragraphs about the project
- [ ] privacy.html — 1 page, MailerLite compliance

Distribution:
- [ ] Submit to Google News Publisher Center (publishercenter.google.com)
- [ ] Add Twitter card meta tags to homepage
- [ ] Add homepage JSON-LD structured data (WebSite + SearchAction)
- [ ] Update robots.txt (disallow review JSON files)

Design:
- [ ] Date headline above hero card on homepage
- [ ] Site tagline for new visitors
- [ ] Move newsletter section on homepage (after yesterday's briefs)
- [ ] Populate pub_date from RSS data in engine

---

### Session 12 — UX Depth & Navigation
**Focus: Keep readers longer, make them read more.**

- [ ] Previous/Next article navigation on article page
- [ ] Category filter tabs on homepage (client-side JS)
- [ ] Separate Share and Follow sections on article page
- [ ] Add CNBCTV18 as RSS source, limit YourStory to 1/day
- [ ] Weekly digest email setup (generate_weekly_digest.py + MailerLite automation)

---

### Session 13 — Growth Features
**Focus: Surface area for organic discovery.**

- [ ] Category pages (5 pages: /category/*.html)
- [ ] "Best of CatchTheBrief" curated page (/best.html)
- [ ] Search index generation + /search.html client-side search
- [ ] Subscriber count in newsletter CTA (MailerLite API or manual hardcode)

---

### Session 14 — Polish & Performance
**Focus: Details that signal quality.**

- [ ] Loading shimmer for card images (CSS only)
- [ ] Open Graph image improvement — category-branded title cards
- [ ] Dark mode support
- [ ] PWA manifest.json — Add to Home Screen
- [ ] Google Discover length optimization (expand briefs to 800+ words)

---

## 9. QUICK REFERENCE — ALL ACTION ITEMS

### Immediate (Do Before Next Session)

| # | Action | File | Time |
|---|---|---|---|
| 1 | Add continue-on-error to social steps | generate_and_publish.yml | 5 min |
| 2 | Add "no exclamation marks" to BRIEF_PROMPT | generate_and_publish.py | 5 min |
| 3 | Submit to Google News Publisher Center | External | 30 min |
| 4 | Start posting to r/indianstartups 3x/week | External | 10 min/post |
| 5 | Set up LinkedIn Newsletter on LinkedIn | External | 20 min |

### Session 10 (Code Changes)

| # | Action | Complexity |
|---|---|---|
| 1 | Rewrite BRIEF_PROMPT with new rules | Medium |
| 2 | Add TAKE section to prompt + template | Medium |
| 3 | Fix markdown stripping in parse_brief() | Low |
| 4 | Fix sitemap to include all historical articles | Medium |
| 5 | Fix requirements.txt | Low |
| 6 | Create .gitignore | Low |
| 7 | Delete orphan files | Low |
| 8 | Rewrite README.md | Low |
| 9 | Rename article section labels | Low |
| 10 | Fix empty pub_date separator | Low |
| 11 | Move newsletter CTA on article page | Low |
| 12 | Increase card preview to 3 lines | Low |
| 13 | Add source name mapping dict | Low |

### Session 11 (New Pages + SEO)

| # | Action | Complexity |
|---|---|---|
| 1 | Create 404.html | Low |
| 2 | Create about.html | Low |
| 3 | Create privacy.html | Low |
| 4 | Add Twitter card to homepage | Low |
| 5 | Update robots.txt | Low |
| 6 | Add date headline to homepage | Medium |
| 7 | Submit to Google News | External |

### Session 12 (UX)

| # | Action | Complexity |
|---|---|---|
| 1 | Previous/Next article navigation | Medium |
| 2 | Category filter tabs | Medium |
| 3 | Weekly digest email | High |

---

## APPENDIX A — Current File Structure (Post Session 9)

```
catchthebrief/
├── fetch_and_rank.py           # Step 1: fetch/filter/rank → review_candidates.json
├── generate_and_publish.py     # Step 2: read candidates → generate briefs → publish
├── post_to_telegram.py         # Auto-posts to Telegram channel after publish
├── post_to_linkedin.py         # Auto-posts to LinkedIn after publish [Session 9 NEW]
├── post_to_twitter.py          # Unused (Twitter API requires $100/month paid plan)
├── news_engine.py              # LEGACY — manual fallback only, do not use for daily
├── manual_briefs.json          # Editorial override file [Session 9 NEW] — NEVER auto-overwritten
├── review_candidates.json      # Auto-generated nightly, reviewable before 8 AM IST
├── requirements.txt            # NEEDS FIX — remove lxml, update google-genai
├── README.md                   # NEEDS REWRITE — describes old architecture
├── robots.txt                  # NEEDS UPDATE — add disallow rules
├── CNAME                       # catchthebrief.com ✓
├── favicon.svg                 # Blue "C" icon ✓
├── sitemap.xml                 # NEEDS FIX — missing 80+ historical articles
│
├── templates/
│   ├── index.html              # Homepage template
│   └── article.html            # Article template [Session 9: Reddit share button added]
│
├── .github/workflows/
│   ├── fetch_and_rank.yml      # Cron 10:00 PM IST — runs fetch_and_rank.py
│   ├── generate_and_publish.yml # Cron 8:00 AM IST — runs generate + telegram + linkedin
│   └── daily.yml               # LEGACY — manual trigger only, rarely used
│
├── daily.yml           [ROOT]  # ORPHAN — wrong location, should be deleted
├── deals.html          [ROOT]  # ORPHAN — old paused feature, should be deleted
├── deals/              [ROOT]  # ORPHAN — old code, should be deleted
├── New folder/         [ROOT]  # ORPHAN — Windows accident, should be deleted
│
├── articles/           # ~90 generated article HTML pages ✓
└── archive/            # 28 JSON data files + HTML archive pages ✓
```

---

## APPENDIX B — Environment Variables Reference

| Variable | Purpose | Where |
|---|---|---|
| GEMINI_API_KEY_1 | Primary Gemini API key | GitHub Secret |
| GEMINI_API_KEY_2 | Rotation backup | GitHub Secret |
| GEMINI_API_KEY_3 | Rotation backup | GitHub Secret |
| GROQ_API_KEY | Fallback AI (14,400 req/day free) | GitHub Secret |
| TELEGRAM_BOT_TOKEN | Telegram bot posting | GitHub Secret |
| TELEGRAM_CHAT_ID | Channel ID: -1003783025490 | GitHub Secret |
| LINKEDIN_ACCESS_TOKEN | Expires every 60 days — refresh manually | GitHub Secret |
| LINKEDIN_AUTHOR_URN | urn:li:person:... or urn:li:organization:... | GitHub Secret |

---

## APPENDIX C — Session History Quick Reference

| Session | Focus | Status |
|---|---|---|
| 1 | Initial build | ✅ Done |
| 2 | First deployment | ✅ Done |
| 3 | Strategy pivot (India niche, quality focus) | ✅ Done |
| 4 | Content engine rewrite, Gemini, 8 India RSS feeds | ✅ Done |
| 5 | Design overhaul (Inter + Space Grotesk, hero layout) | ✅ Done |
| 6 | Manual review workflow, source diversity, MailerLite | ✅ Done |
| 7 | Pollinations images, archive pages, JSON-LD, SEO | ✅ Done |
| 8 | Telegram bot, WhatsApp channel, distribution buttons | ✅ Done |
| 9 | manual_briefs.json, LinkedIn bot, Reddit share button | ✅ Done |
| 10 | Prompt rewrite (TAKE section), sitemap fix, missing pages | ⏳ Next |
| 11 | About/Privacy/404 pages, Google News submission, homepage UX | ⏳ Planned |
| 12 | Prev/Next navigation, category filter, weekly digest | ⏳ Planned |
| 13 | Category pages, search, Best-of page | ⏳ Planned |
| 14 | Polish — shimmer, dark mode, PWA, Discover optimization | ⏳ Planned |

---

*Report generated: 13 May 2026 | Session 9 | CatchTheBrief Full Audit*
*Author: Claude (Anthropic) acting as Project Manager, Content Strategist, and Design Auditor*
*Next action: Review this document, add your own notes, then use as basis for Session 10 handoff*
