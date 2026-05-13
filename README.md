# CatchTheBrief

India's daily tech and startup briefing. 5 sharp stories, every morning. Zero servers, zero cost.

**Live site:** [catchthebrief.com](https://catchthebrief.com)

---

## How It Works

Two GitHub Actions run on a schedule each day:

| Step | File | Schedule | What it does |
|------|------|----------|--------------|
| 1 — Fetch & Rank | `fetch_and_rank.py` | 10:00 PM IST | Pulls RSS from 9 India tech sources, filters junk, AI-ranks top 15, saves `review_candidates.json` |
| 2 — Generate & Publish | `generate_and_publish.py` | 8:00 AM IST | Reads the top 5 candidates, writes AI briefs, builds all HTML, pushes to GitHub Pages |

Between steps, `review_candidates.json` can be edited manually on GitHub to swap articles or inject pre-written briefs.

---

## AI Stack

- **Primary:** Gemini 2.5 Flash (3-key rotation)
- **Fallback:** Groq Llama 3.3 70B
- **Images:** Pollinations.AI (deterministic, seed = MD5(slug)[:6])

---

## Editorial Control

**Manual override (persistent):** Edit `manual_briefs.json`. Add any brief keyed by URL. These are never overwritten by automation and take highest priority.

**Daily override:** Edit `review_candidates.json` on GitHub before 8 AM IST. Add a `manual_brief` key to any entry, or reorder the `top_5` array.

---

## Distribution

| Channel | File | Trigger |
|---------|------|---------|
| Newsletter | MailerLite (account 2285640) | Subscribers sign up on site |
| Telegram | `post_to_telegram.py` | After publish step |
| LinkedIn | `post_to_linkedin.py` | After publish step (token expires every 60 days) |
| WhatsApp Channel | Manual | Separate from automation |

---

## Directory Structure

```
catchthebrief/
├── .github/workflows/
│   ├── generate_and_publish.yml   # Main daily workflow (8 AM IST)
│   └── fetch_and_rank.yml         # Step 1 workflow (10 PM IST)
├── templates/
│   ├── index.html                 # Homepage template
│   ├── article.html               # Article page template
│   └── archive.html               # Archive page template
├── articles/                      # Generated article pages (YYYY-MM-DD-slug.html)
├── archive/                       # Per-day archive pages + JSON records
├── next claude session guide/     # Session handoff notes
├── generate_and_publish.py        # Step 2: generates briefs + builds site
├── fetch_and_rank.py              # Step 1: fetches + ranks candidates
├── post_to_telegram.py            # Posts daily summary to Telegram
├── post_to_linkedin.py            # Posts daily summary to LinkedIn
├── post_to_twitter.py             # Posts daily summary to Twitter/X
├── manual_briefs.json             # Persistent editorial overrides (never auto-overwritten)
├── review_candidates.json         # Today's ranked candidates (regenerated daily)
├── index.html                     # Live homepage (generated)
├── sitemap.xml                    # Full sitemap (generated, includes all articles)
├── robots.txt
├── favicon.svg
├── about.html
├── privacy.html
└── 404.html
```

---

## Required GitHub Secrets

| Secret | Used by |
|--------|---------|
| `GEMINI_API_KEY_1/2/3` | Both Python scripts |
| `GROQ_API_KEY` | Both Python scripts |
| `TELEGRAM_BOT_TOKEN` | `post_to_telegram.py` |
| `TELEGRAM_CHAT_ID` | `post_to_telegram.py` |
| `LINKEDIN_ACCESS_TOKEN` | `post_to_linkedin.py` (refresh every 60 days) |
| `LINKEDIN_AUTHOR_URN` | `post_to_linkedin.py` |

---

## Brief Format

Each AI-generated brief follows this structure:

1. **Hook** — 3–4 sentence lead, conversational, angle-first
2. **How We Got Here** — backstory context
3. **The Numbers** — 5 bullet-point facts
4. **What Happens Next** — forward-looking summary
5. **Why This Matters for India** — specific India angle
6. **The Take** — editorial opinion

---

## Development Notes

See `next claude session guide/` for session-by-session implementation history and the current handoff document.
