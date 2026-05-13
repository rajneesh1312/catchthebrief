# CatchTheBrief — Claude Handoff After Session 10

**Date:** 13 May 2026  
**Session focus:** Content + SEO + Design gaps from Session 9 audit  
**Priority order maintained:** Content Quality → SEO → Design → Distribution

---

## What Was Done in Session 10

1. **Site tagline** — Added below date herald in `templates/index.html`: "5 India tech & startup stories. Written clearly. Every morning at 8 AM." with `.site-tagline` CSS class.
2. **Share vs Follow split** — `templates/article.html`: separated the single combined share box into `.share-section` (WhatsApp, X, Reddit, Copy Link) and `.follow-section` (WhatsApp Channel, Telegram). Two distinct visual blocks with independent borders and spacing.
3. **Prev/Next article navigation** — `templates/article.html`: `{{PREV_NAV}}` placeholder added after follow section, with `.article-nav`, `.nav-btn` CSS (pill-style, mobile-stacks). `generate_and_publish.py`: `build_prev_next_nav()` helper added, `generate_article_page()` updated to accept `prev_slug`/`next_slug`, call site computes these from `briefs_data` index.
4. **YourStory max-1 limit** — `fetch_and_rank.py` `rank_articles()` prompt: criterion 3 now reads "at most 1 article from yourstory.com (their content trends PR-heavy)".
5. **Sitemap: about + privacy** — `generate_and_publish.py` `generate_sitemap()`: `about.html` and `privacy.html` now included as static entries on every build.
6. **Google News submission** — Submitted manually by Rajneesh. Review takes 1–4 weeks.

---

## Architecture Overview

**Two-step daily engine:**
- **Step 1** (`fetch_and_rank.py`) — 10:00 PM IST: Fetches RSS from 9 sources, filters, AI-ranks, saves `review_candidates.json`
- **Step 2** (`generate_and_publish.py`) — 8:00 AM IST: Reads candidates, generates briefs, builds all HTML, pushes to GitHub Pages

**AI stack:** Gemini 2.5 Flash (primary, 3-key rotation) → Groq Llama 3.3 70B (fallback)  
**Images:** Pollinations.AI (free, deterministic, seed = MD5(slug)[:6])  
**Hosting:** GitHub Pages (zero cost, zero server)

---

## Current File State (key files)

| File | State |
|------|-------|
| `generate_and_publish.py` | Updated — prev/next nav helper + call site, sitemap static pages |
| `fetch_and_rank.py` | Updated — YourStory max-1 in ranking prompt |
| `templates/article.html` | Updated — Share/Follow split, prev/next nav placeholder + CSS |
| `templates/index.html` | Updated — site tagline below date herald |
| All other files | Unchanged from Session 9 |

---

## Known Remaining Items

### Content Quality
- [ ] **"STRONGLY PREFER external validation"** — audit recommended adding to ranking criteria (analyst quotes, regulatory action, named revenue numbers). Not yet in prompt.
- [ ] AI prompt for TAKE could include 2–3 example takes to sharpen voice
- [ ] Hook quality still depends entirely on AI — consider editorial review workflow

### SEO
- [ ] **Google News review** — submitted manually 13 May 2026. Check status in 1–4 weeks at `publishercenter.google.com`.
- [ ] `lastmod` for historical articles should use actual file modification date, not today's date
- [ ] Archive pages missing `og:image` — add default OG image tag to archive template
- [ ] Article image alt text currently = title — generate more descriptive alt text in engine

### Design
- [ ] Top bar (currently static "Subscribe free →") could show today's date or tease top story on repeat visits
- [ ] Mobile: hero card hook preview truncation could show more

### Distribution — Active Actions (all manual, no code)
- [ ] **Reddit — 3x per week posting** (audit §4D Tier 1): Post to r/indianstartups (131K), r/IndiaInvestments (120K), r/india (1.1M for big stories only). Write hook + 2–3 facts in post body, end with link. Do NOT post bare links — moderators remove them. 10 min/post.
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

## Session 11 Suggested Focus

**Session 11 — Distribution + Growth (code side):**
- Weekly digest email script (`generate_weekly_digest.py`) — reads last 7 days of archive JSON, assembles top 5, generates MailerLite campaign via API. New cron: Sunday 9 AM IST.
- Category pages — `/category/*.html` generated from archive JSON, added to sitemap
- LinkedIn Newsletter setup reminder (manual, 15 min)
- Twitter/X thread format guidance for manual posting rhythm

**Session 12 — UX + Discovery:**
- Category filter tabs on homepage (client-side JS, no backend)
- Client-side search across all briefs (`search-index.json` + `/search.html`)
- "Best of CatchTheBrief" curated page (`/best.html`)
- Loading shimmer for card images

**Session 13 — Polish:**
- Dark mode (`prefers-color-scheme: dark`)
- PWA `manifest.json`
- OG image improvement (category-branded title cards)
- Archive page `og:image` fix

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
