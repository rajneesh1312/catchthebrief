# CatchTheBrief

India's daily tech and startup briefing. 5 sharp stories, every morning. Zero servers, zero cost.

**Live site:** [catchthebrief.com](https://catchthebrief.com)

---

## How It Works

Two GitHub Actions run on a schedule each day:

| Step | File | Cron (UTC) | Scheduled IST | Actual IST delivery |
|------|------|-----------|--------------|---------------------|
| 1 — Fetch & Rank | `fetch_and_rank.py` | `30 16 * * *` | 10:00 PM | ~11:00 PM – midnight |
| 2 — Generate & Publish | `generate_and_publish.py` | `30 2 * * *` | 8:00 AM | ~11:00 AM – noon |

> **Note on timing drift.** GitHub Actions schedules are best-effort on the free tier and routinely run 1-4 hours late, especially around the top/bottom of the hour. The cron is set to the scheduled time above; actual delivery has been consistently ~3 hours late for the morning build. See the latest session handoff for the run-time table.

Between steps, `review_candidates.json` can be edited manually on GitHub to swap articles or inject pre-written briefs.

---

## AI Stack

- **Primary:** Gemini 2.5 Flash (3-key rotation)
- **Fallback:** Groq Llama 3.3 70B
- **Images:** Branded 1200×630 title cards rendered server-side by `generate_title_card.py` (Pillow). Replaced Pollinations.AI in Session 13.

---

## Editorial Control

**Manual override (persistent):** Edit `manual_briefs.json`. Add any brief keyed by URL. These are never overwritten by automation and take highest priority.

**Daily override:** Edit `review_candidates.json` on GitHub before the morning build. Add a `manual_brief` key to any entry, or reorder the `top_5` array.

**Editor's notes:** Drop a markdown file at `editor_notes/YYYY-MM-DD.md` (front-matter `title:` only). The next build renders it and shows the latest as a banner on the homepage.

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
│   ├── generate_and_publish.yml   # Daily publish workflow (cron 02:30 UTC)
│   └── fetch_and_rank.yml         # Daily fetch workflow (cron 16:30 UTC)
├── templates/
│   ├── index.html                 # Homepage template
│   ├── article.html               # Article page template
│   ├── deal_detail.html           # Legacy deal-detail template
│   └── editor_note.html           # Editor's note page template
├── articles/                      # Generated article pages (YYYY-MM-DD-slug.html)
├── archive/                       # Per-day archive pages + JSON records
├── editor_notes/                  # Source markdown for editor's notes
├── editor-notes/                  # Generated HTML for editor's notes
├── images/
│   ├── og-default.png             # Site-wide fallback OG card (generated)
│   └── cards/                     # Per-page title cards (generated)
├── next claude session guide/     # Session handoff notes
├── fetch_and_rank.py              # Step 1: fetch + rank candidates
├── generate_and_publish.py        # Step 2: generate briefs + build site
├── generate_editor_note.py        # Renders editor-note pages from markdown
├── generate_title_card.py         # Renders 1200×630 PNG title cards (Pillow)
├── post_to_telegram.py            # Posts daily summary to Telegram
├── post_to_linkedin.py            # Posts daily summary to LinkedIn
├── manual_briefs.json             # Persistent editorial overrides (never auto-overwritten)
├── review_candidates.json         # Today's ranked candidates (regenerated daily)
├── index.html                     # Live homepage (generated)
├── sitemap.xml                    # Full sitemap (generated)
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
