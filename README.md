# CatchTheBrief

> AI-curated tech news summaries and daily deals for Indian buyers.
> Updated every morning automatically. No server required.

---

## How it works

1. `news_engine.py` runs daily via GitHub Actions
2. Fetches real article content from Google News RSS (10 categories)
3. Passes full article body to Gemini AI → extracts 3 real insights + India angle hook
4. Fetches top deals from r/IndiaDeals and r/deals, tags Amazon links with affiliate ID
5. Builds `index.html`, `articles/*.html`, `deals.html`, `sitemap.xml`
6. GitHub Actions commits the files and GitHub Pages serves them live

---

## Local setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/catchthebrief.git
cd catchthebrief

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Gemini API key
# Windows CMD:
set GEMINI_API_KEY=your_key_here
# Windows PowerShell:
$env:GEMINI_API_KEY="your_key_here"
# Mac/Linux:
export GEMINI_API_KEY=your_key_here

# 4. Run
python news_engine.py

# 5. Open index.html in your browser
```

The script takes ~3 minutes to run (rate limiting between AI calls).

---

## Deployment to GitHub Pages

### Step 1 — Create GitHub repo
- Go to github.com → New repository → name it `catchthebrief`
- Set to **Public** (required for free GitHub Pages)

### Step 2 — Add your Gemini API key as a Secret
- Repo → Settings → Secrets and variables → Actions → New repository secret
- Name: `GEMINI_API_KEY`
- Value: your actual Gemini API key

### Step 3 — Push your code
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/catchthebrief.git
git push -u origin main
```

### Step 4 — Enable GitHub Pages
- Repo → Settings → Pages
- Source: **Deploy from a branch**
- Branch: `main` / `/ (root)`
- Save

### Step 5 — Connect custom domain (catchthebrief.com)
- In Pages settings, enter `catchthebrief.com` in Custom domain field
- At your domain registrar (GoDaddy, Namecheap, etc.), add these DNS records:

```
Type    Host    Value
A       @       185.199.108.153
A       @       185.199.109.153
A       @       185.199.110.153
A       @       185.199.111.153
CNAME   www     YOUR_USERNAME.github.io
```

- Wait 10–30 minutes for DNS propagation
- GitHub will auto-provision SSL (free)

### Step 6 — Test automation
- Repo → Actions → Daily Content Update → Run workflow (manual trigger)
- Confirm it runs successfully before relying on the daily cron

---

## Affiliate setup (Amazon Associates India)

1. Apply at https://affiliate-program.amazon.in/
2. Once approved, get your tracking ID (format: `yourname-21`)
3. Open `news_engine.py`, find this line:
   ```python
   AMAZON_AFFILIATE_TAG = "catchthebrief-21"
   ```
4. Replace with your actual tag

Every Amazon.in link in the deals section will now be tagged automatically.

---

## Email newsletter (Buttondown — free tier)

1. Sign up at https://buttondown.email (free up to 100 subscribers)
2. Create a newsletter called "CatchTheBrief"
3. Go to Settings → API → copy your username
4. Open `templates/index.html`, find:
   ```html
   action="https://buttondown.email/api/emails/embed-subscribe/catchthebrief"
   ```
5. Replace `catchthebrief` with your Buttondown username

---

## Project structure

```
catchthebrief/
├── news_engine.py          # Master content engine
├── requirements.txt        # Python dependencies
├── .gitignore
├── README.md
├── templates/
│   ├── index.html          # Homepage template
│   ├── article.html        # Individual article template
│   └── deals.html          # Deals page template
├── .github/
│   └── workflows/
│       └── daily.yml       # GitHub Actions cron job
│
# Generated daily by the engine (committed by bot):
├── index.html
├── deals.html
├── sitemap.xml
└── articles/
    ├── ai-news-today.html
    ├── laptop-deals-india.html
    └── ...
```

---

## Customization

**Add/remove news categories** — edit `NEWS_CATEGORIES` list in `news_engine.py`

**Change deal sources** — edit `REDDIT_SOURCES` list in `news_engine.py`

**Change run time** — edit the cron schedule in `.github/workflows/daily.yml`
- `'30 3 * * *'` = 3:30 AM UTC = 9:00 AM IST
- Use https://crontab.guru to generate other schedules

**Change email provider** — swap the `<form>` action URL in `templates/index.html`
- Mailchimp embed: find it under Audience → Signup forms → Embedded forms
- ConvertKit: Forms → your form → Embed

---

## Costs

| Service | Cost |
|---------|------|
| GitHub Pages hosting | Free |
| GitHub Actions (2000 min/month) | Free |
| Gemini API (free tier, 1500 req/day) | Free |
| Buttondown newsletter (≤100 subs) | Free |
| Amazon Associates | Free (earn commission) |
| Domain (catchthebrief.com) | ~₹1000/year |

**Total monthly cost: ₹0** (until you scale beyond free tiers)
