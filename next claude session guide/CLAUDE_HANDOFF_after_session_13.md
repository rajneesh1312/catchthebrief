# CatchTheBrief — Claude Handoff After Session 13

**Date:** 14 May 2026
**Session focus:** Kill the AI-illustration "tell" — replace Pollinations.AI with branded server-side title cards
**Trigger:** Session 12 added the visible human-editor layer. The remaining "this is AI-run" signal was the Pollinations.AI images shown on every hero / card / og:image. Session 13 swaps every one of them for a generated 1200×630 PNG with category gradient, bold headline, and CTB wordmark.

---

## What Was Done in Session 13

### 1. New title-card generator
**New file:** [generate_title_card.py](../generate_title_card.py)

Pure-Python Pillow renderer. No external assets, no font files bundled. Uses system bold sans-serif via a fallback chain: Arial Bold (Windows) → Liberation Sans Bold (Ubuntu / GitHub Actions) → DejaVu Sans Bold → macOS Helvetica → Pillow default. Public API:

- `build_for_article(title, category, slug)` — per-article card at `/images/cards/<slug>.png`
- `build_for_day(date_iso, brief_count=5)` — per-day archive card at `/images/cards/day-<date>.png`
- `build_for_editor_note(title, date_iso)` — editor's note card at `/images/cards/note-<date>.png`
- `build_default()` — site-wide fallback at `/images/og-default.png`

Each function returns an **absolute URL** suitable for `<meta property="og:image">`. Returns `""` if Pillow isn't available; callers fall back to the default OG card so a page is never published with a missing image.

Layout (all four card types):
- 1200×630 with a 135° linear gradient (color1 top-left → color2 bottom-right)
- Kicker top-left (small uppercase: "AI & ML", "DAILY ARCHIVE", "EDITOR'S NOTE", etc.)
- Big bold white headline, auto-fit to box (84→44px sweep, max 4 lines, greedy word-wrap)
- White accent bar bottom-left (small visual flourish)
- "CatchTheBrief" wordmark bottom-right

Category gradient palette (chosen for white-on-color contrast):
- AI & ML → purple (#7C3AED → #4C1D95)
- Startup Funding → emerald (#059669 → #065F46)
- Digital India → red (#DC2626 → #7F1D1D)
- Product Launch → amber (#D97706 → #78350F)
- India Tech → blue (#2563EB → #1E40AF)
- Default / archive index → blue → purple
- Editor's note → amber → burnt orange (matches the on-site kicker palette)

Standalone runnable: `python generate_title_card.py` rebuilds the default OG card and three samples — useful for previewing typography changes without touching the engine.

### 2. Engine wired to generator
**Modified:** [generate_and_publish.py](../generate_and_publish.py)

- Removed `generate_ai_image_url()` (Pollinations URL builder) and its `hashlib` import.
- Replaced with `generate_title_card_url(title, category, slug)` — thin wrapper around `generate_title_card.build_for_article()` that falls back to `og-default.png` on failure.
- `get_default_image()` now returns the absolute URL of `/images/og-default.png` for every category (the per-category JPG defaults at `/images/defaults/*.jpg` were never actually shipped — those paths returned 404s in production. The new single fallback is genuinely generated at build time).
- `main()` now calls `generate_title_card.build_default()` at startup so the fallback PNG always exists before any page references it.
- Article-page generation now passes `image_url` straight into the article HTML — no separate code path between "AI image" and "fallback".

### 3. Archive day pages now have og:image
**Modified:** [generate_and_publish.py](../generate_and_publish.py) — `_archive_page_html()` + `generate_day_archive_page()`

- `_archive_page_html()` gained an optional `og_image` param (defaults to `og-default.png` if not passed) and now emits `og:image` + `twitter:card=summary_large_image` + `twitter:image` meta tags (previously archive pages had none — sharing them on Twitter produced an image-less card).
- `generate_day_archive_page()` calls `generate_title_card.build_for_day(date_str, brief_count=len(briefs))` and passes the URL through.

### 4. Editor's Notes now have og:image
**Modified:** [generate_editor_note.py](../generate_editor_note.py), [templates/editor_note.html](../templates/editor_note.html)

- `_render_note_page()` imports `generate_title_card` lazily and renders a per-note card via `build_for_editor_note(title, date)`. Falls back to `og-default.png` on any failure.
- Template now exposes `{{OG_IMAGE}}` and emits `og:image` + upgraded `twitter:card=summary_large_image` + `twitter:image` meta tags (the note pages previously had no image at all and used the smaller `summary` Twitter card).

### 5. Dependencies + workflow
**Modified:** [requirements.txt](../requirements.txt), [.github/workflows/generate_and_publish.yml](../.github/workflows/generate_and_publish.yml)

- Added `Pillow>=10.0.0` to requirements.
- Added `Pillow` to the workflow's `pip install` line so GitHub Actions has it on next build.
- Did **not** touch the legacy `daily.yml` workflow — it's manual-only and runs `news_engine.py` which doesn't use title cards.

---

## Local validation

Ran without any AI API calls — exercised the renderer, file wiring, and HTML token replacement:

| Check | Result |
|---|---|
| `python generate_title_card.py` standalone | Renders default + 3 sample cards |
| `generate_and_publish.generate_title_card_url()` for an AI & ML brief | Returns `https://catchthebrief.com/images/cards/<slug>.png`; file exists; gradient + headline + wordmark all visible |
| `generate_article_page()` HTML | Contains `og:image`, `twitter:image`, the title-card URL, and the editor footer line |
| `generate_title_card.build_for_day('2026-05-13')` | PNG written; URL absolute |
| `generate_title_card.build_for_editor_note(...)` | PNG written; URL absolute |
| `generate_editor_note.build_all()` | Note HTML now contains `og:image` + `twitter:image` |
| `generate_day_archive_page(yesterday)` | HTML contains `og:image` + `twitter:image` |
| `generate_homepage([...])` | Homepage `OG_IMAGE_HOME` is the first article's title-card URL |
| Spot-checked card renders for: AI & ML, Startup Funding, Editor's Note, Daily Archive, default | All four templates render cleanly at 1200×630, ~40-65KB each |

---

## Architecture overview (deltas from Session 12)

**New file structure:**
```
images/
  ├── og-default.png             # site-wide fallback, generated at build time
  └── cards/                     # all per-page title cards
      ├── <slug>.png             # per-article (one per published brief)
      ├── day-YYYY-MM-DD.png     # per-archive-day
      └── note-YYYY-MM-DD.png    # per-editor-note
generate_title_card.py           # NEW — standalone renderer
```

**Engine flow (Session 13 deltas):**
1. `fetch_and_rank.py` — unchanged
2. `generate_and_publish.py`:
   - **NEW startup step:** `generate_title_card.build_default()` — guarantees the fallback PNG exists
   - Step 2 now calls `generate_title_card_url()` per brief instead of `generate_ai_image_url()`
   - Step 3b (editor notes) now also renders a per-note title card via `build_for_editor_note()`
   - Day-archive HTML now embeds an og:image generated by `build_for_day()`

**Filesystem footprint:** each PNG is 40-65KB. A full year of daily 5-brief days ≈ 5×365 = ~1,825 article cards × 50KB = ~90MB. GitHub Pages soft limit is 1GB, so we have plenty of room. The daily workflow's `git add -A` already commits everything in `images/` automatically.

---

## What is NOT done — known caveats / follow-ups

1. **Legacy articles still reference Pollinations URLs.** The 150+ already-generated article HTML files in `articles/` are frozen — they were written before Session 13 and still embed `https://image.pollinations.ai/prompt/...` URLs in their `<img>` and `og:image` meta. Going forward, every new daily build writes title-card URLs into fresh HTML, but historical articles will keep showing AI illustrations unless we run a one-shot backfill.

   - **Optional backfill script idea (Session 14 if desired):**
     - Walk `articles/*.html`
     - Regex out the slug from the filename, look up the brief JSON in `archive/<date>.json` to recover the title + category
     - Call `generate_title_card.build_for_article(...)`
     - Substring-replace the Pollinations URL with the new title card URL in the HTML file
     - Zero API calls, ~150 cards × 50KB = ~7.5MB to add
   - **Why it's not in this session:** the user opted to keep scope tight to the engine change. The backlog is visible from one place (`articles/`) and is purely a find/replace once we want to do it.

2. **Twitter does not render PNGs over HTTPS-with-cache-bust for the first few minutes.** Twitter's card validator caches aggressively. After deploying, run the validator at `https://cards-dev.twitter.com/validator` once per template type to prime the cache.

3. **Pillow font fallback.** On Ubuntu (GitHub Actions runners), Liberation Sans Bold is guaranteed to be present at `/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf`. If GitHub ever changes the runner image and that path disappears, the renderer falls back to DejaVu Sans Bold; if that's also missing it falls back to Pillow's default bitmap font (cards still render but typography degrades visibly). The fallback chain is logged inside `_find_font()` — search for "BOLD_CANDIDATES" if you want to add a path.

4. **No Space Grotesk on the cards.** On-page typography is Space Grotesk; cards are Arial/Liberation Sans Bold. The visual mismatch is small (both are geometric sans) but a designer would notice. Easy follow-up if it matters: bundle `SpaceGrotesk-Bold.ttf` (SIL Open Font License, ~80KB) in `assets/fonts/` and add it as the first entry in `BOLD_CANDIDATES`. Decided against bundling in this session per user preference (no binary commits).

5. **Editor's-note OG card uses the note title only.** No date appears on the card. The date is implied by the kicker ("EDITOR'S NOTE") and the wordmark. If you want a date stamp on the card, add a third small line near the kicker — straightforward edit in `_render_card`.

---

## Current file state

| File | State |
|------|-------|
| `generate_title_card.py` | **NEW** — Pillow renderer, 4 public functions |
| `generate_and_publish.py` | Updated — imports title-card module, removed `generate_ai_image_url()` + `hashlib`, added `generate_title_card_url()`, default-card built in `main()`, day-archive pages now thread `og_image` through `_archive_page_html()` |
| `generate_editor_note.py` | Updated — `_render_note_page()` builds a per-note title card, exposes `{{OG_IMAGE}}` |
| `templates/editor_note.html` | Updated — emits `og:image` + upgraded twitter card to `summary_large_image` + `twitter:image` |
| `requirements.txt` | Updated — added `Pillow>=10.0.0` |
| `.github/workflows/generate_and_publish.yml` | Updated — `pip install ... Pillow` |
| `templates/index.html` | Unchanged — already consumed `{{OG_IMAGE_HOME}}` which now resolves to a title-card URL |
| `templates/article.html` | Unchanged — already consumed `{{OG_IMAGE}}` which now resolves to a title-card URL |
| `images/og-default.png` | **NEW** — generated at every build |
| `images/cards/note-2026-05-11.png` | **NEW** — title card for the sample editor note |
| `images/cards/day-2026-05-13.png` | **NEW** — title card for yesterday's archive day page |

---

## Open items — user actions

None blocking. The next daily build at 8 AM IST (2:30 AM UTC) will:
1. Install Pillow on the runner
2. Render `og-default.png`
3. Render a per-brief title card for each of today's 5 briefs
4. Render `day-<today>.png` for today's archive page
5. Re-render the editor-note OG image if a note is present
6. Commit all the new PNGs alongside the regenerated HTML

If anything breaks at the Pillow install step (network hiccup on the runner, etc.), the renderer falls back to `og-default.png` silently and pages still publish — just without per-article cards.

**Optional preview:** before the next scheduled build, run `python generate_and_publish.py` locally (or just `python generate_title_card.py` to preview the four card templates without touching the AI engine).

---

## Remaining from prior sessions (still TODO)

### Session 14 — Growth Features (next focus)
- [ ] **Weekly digest email** (`generate_weekly_digest.py`) — Sunday 9 AM IST. Reads last 7 days of archive JSON, assembles top 5, generates MailerLite campaign. Zero new AI calls.
- [ ] **Streak indicator on homepage** — *"Day 47 — we haven't missed a morning."*
- [ ] **Subscriber count social proof** in newsletter CTA — *"Join N readers"*
- [ ] **"Best of CatchTheBrief"** page at `/best.html` — manually curated 10-15 briefs, updated monthly

### Optional cleanup work
- [ ] **Historical article backfill** — see "Known caveats" #1 above. ~7.5MB of additional PNGs to render once, zero API cost.
- [ ] **Broken feeds from Session 11** — `entrackr.com/feed/` (404), `cnbctv18.com/tech/feed/` (404), `analyticsindiamag.com/feed/` (non-XML), `techcrunch.com/tag/india/feed/` (dormant). Fixing these unlocks 4 more sources for the diversity rotation.
- [ ] **Google News review** — submitted 13 May 2026. Check weekly at `publishercenter.google.com`. Review typically takes 1-4 weeks.
- [ ] `lastmod` for historical articles should use actual file mtime, not today's date.
- [ ] Article image alt text currently = title. With the new title cards, alt text could read better as `<TITLE> — CatchTheBrief title card` to be explicit. Trivial edit in `hero_image_html()` / `card_image_html()`.
- [ ] **Custom email forwarding** (from Session 12 open items, optional) — migrate `catchthebrief@gmail.com` → `editor@catchthebrief.com` via Cloudflare Email Routing or ImprovMX.

### Session 15 — Discovery (deferred)
- Category pages, client-side search, category filter tabs, loading shimmer

---

## What I'd watch over the next 1-2 weeks

1. **Twitter/LinkedIn share rendering.** Once the next daily build ships, share a fresh article URL on Twitter and LinkedIn (both have built-in preview cards). The title card should appear at 1200×630 with the brief headline + category. If it doesn't, the most common cause is Twitter's CDN caching the old Pollinations URL — re-validate via `https://cards-dev.twitter.com/validator`.

2. **Visual consistency across categories.** All five category gradients were tuned for white-text contrast, but the amber/orange "Product Launch" gradient is the most marginal. If a Product Launch headline ever feels hard to read on the card, deepen the second gradient stop to `(101, 45, 12)` — that's a 1-line change in `CATEGORY_GRADIENTS`.

3. **Filesystem growth.** Each daily build now adds 5-7 PNGs (~250-350KB/day). Over a year that's ~100MB. Well within GitHub Pages limits, but if you ever want to swap to JPEG to halve the size, change `img.save(out_path, "PNG", optimize=True)` to `img.save(out_path, "JPEG", quality=88, optimize=True)` and rename the paths. JPEGs are slightly worse for the sharp text edges on gradients (you may see banding) — recommend sticking with PNG unless storage becomes a real issue.

---

## Key config values (unchanged + new)

```
SITE_URL:                  https://catchthebrief.com
SITE_NAME:                 CatchTheBrief
EDITOR_NAME:               Rajneesh                        (Session 12)
EDITOR_EMAIL:              catchthebrief@gmail.com         (Session 12, planned migration to editor@catchthebrief.com)
Title card dimensions:     1200 × 630 PNG                  (Session 13)
Title card fallback path:  /images/og-default.png          (Session 13)
Title card per-article:    /images/cards/<slug>.png        (Session 13)
Title card per-day:        /images/cards/day-<date>.png    (Session 13)
Title card per-note:       /images/cards/note-<date>.png   (Session 13)
MailerLite Account:        2285640
MailerLite Form:           185448516399662487
Telegram Chat ID:          -1003783025490
Google Analytics:          G-V6N03CT88P
Gemini Model:              gemini-2.5-flash
Groq Model:                llama-3.3-70b-versatile
Per-feed cap:              4 articles/feed                 (Session 11)
Source caps:               yourstory.com=1, others=2       (Session 11)
Article fetch:             max 3000 chars per URL          (Session 11)
```

---

## Files changed in Session 13

```
NEW:
  generate_title_card.py                        — Pillow renderer, 4 card templates
  images/og-default.png                         — site-wide fallback OG card
  images/cards/note-2026-05-11.png              — sample editor-note card
  images/cards/day-2026-05-13.png               — sample day-archive card
  next claude session guide/CLAUDE_HANDOFF_after_session_13.md  — this file

MODIFIED:
  generate_and_publish.py
    - removed generate_ai_image_url() + hashlib import
    + import generate_title_card
    + generate_title_card_url() wrapper with og-default fallback
    + main() now builds default OG card at startup
    ~ get_default_image() returns og-default.png (was per-category JPGs that never existed)
    ~ _archive_page_html() accepts og_image, emits og:image + twitter:card=summary_large_image
    ~ generate_day_archive_page() now builds + passes a per-day card
  generate_editor_note.py
    ~ _render_note_page() renders a per-note title card and threads {{OG_IMAGE}}
  templates/editor_note.html
    + og:image + twitter:image meta tags
    ~ twitter:card upgraded summary -> summary_large_image
  requirements.txt
    + Pillow>=10.0.0
  .github/workflows/generate_and_publish.yml
    ~ pip install line includes Pillow
```

No engine-pipeline restructuring beyond the default-card build step. The brief-generation prompt, source mix, banned-phrase guard, and editor-note system are unchanged.
