# Affiliate Content Engine

Automated multi-channel content generation for SaaS affiliate marketing.
Built for technical audiences. Powered by Claude API.

---

## Affiliate Programs (Pre-loaded)

All 8 programs are pre-configured in `scheduler.py` and `topics.json`.
Replace `YOUR_ID` with your real affiliate ID in the `AFFILIATES` registry in `scheduler.py`.

| # | Program | Commission | Niche | Sign Up |
|---|---|---|---|---|
| 1 | **AI/ML API** | 30% recurring ∞ | LLM APIs | aimlapi.com/affiliate-program |
| 2 | **Bannerbear** | 30% recurring ∞ | Dev automation | bannerbear.com/affiliate |
| 3 | **Feather** | 25% recurring ∞ | Developer blogging | feather.getrewardful.com |
| 4 | **Keygen** | 30% recurring ∞ | Software licensing | keygen.sh/affiliates |
| 5 | **Serply.io** | 25% recurring ∞ | SERP/scraping APIs | affiliates.reflio.com/invite/serply |
| 6 | **NeuralText** | 30% recurring ∞ | AI content ops | neuraltext.getrewardful.com |
| 7 | **Compint** | 25% recurring ∞ | Competitor tracking | compint.lemonsqueezy.com/affiliates |
| 8 | **Instatus** | 30% recurring ∞ | Status pages | instatus.com/affiliates |

---

## Quick Start

### 1. Install
```bash
pip install anthropic rich
export ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Sign up for Tier 1 affiliates first
Sign up for AI/ML API, Bannerbear, Feather, Keygen, and Serply.io.
Replace `YOUR_ID` in the `AFFILIATES` dict in `scheduler.py` with your real IDs.

### 3. Preview your content queue
```bash
python scheduler.py --list           # All topics
python scheduler.py --list --tier 1  # Tier 1 only
```

### 4. Run a single topic first (recommended)
```bash
python scheduler.py --slug aimlapi-llm-comparison
```

### 5. Run all Tier 1 topics
```bash
python scheduler.py --tier 1
```

### 6. Run everything
```bash
python scheduler.py --all
```

---

## Content Queue (Pre-loaded Topics)

### Tier 1 — Start here (15 topics, 5 programs)

**AI/ML API** — Your highest-ROI program. ML engineers are your exact audience.
- `aimlapi-llm-comparison` — Best LLM APIs in 2025: Claude vs GPT-4 vs Gemini benchmark
- `aimlapi-cut-costs` — Cut LLM API costs by 60% without sacrificing quality
- `aimlapi-getting-started` — Stop juggling 5 API keys — unified LLM gateway in Python

**Bannerbear** — API-first image generation, write tutorials from real experience.
- `bannerbear-automate-visuals` — Auto-generate 100 social images in 5 minutes
- `bannerbear-ecommerce` — Automate product images with Python + Bannerbear
- `bannerbear-og-images` — Dynamic OG images with Bannerbear + Vercel Edge Functions

**Feather** — Write about your own blogging setup authentically.
- `feather-notion-blog` — Turn Notion into an SEO blog without code
- `feather-vs-ghost` — Feather vs Ghost vs Hashnode vs Substack for developers
- `feather-content-workflow` — My complete developer blog workflow

**Keygen** — Niche but high-intent: developers shipping paid tools.
- `keygen-software-licensing` — Add software licensing in under an hour
- `keygen-vs-alternatives` — Keygen vs Paddle vs LemonSqueezy vs Gumroad
- `keygen-python-integration` — License-gated Python CLI tool walkthrough

**Serply.io** — Every developer scraping Google knows this pain.
- `serply-web-scraping` — Stop getting blocked: reliable Google scraping
- `serply-seo-pipeline` — Automated SERP rank tracker in Python for $10/month
- `serply-vs-alternatives` — Serply vs SerpApi vs DataForSEO comparison

### Tier 2 — Add after Tier 1 has traction (6 topics)

**NeuralText**, **Compint**, **Instatus** — unlock once you have consistent traffic.

---

## Output Structure

```
output/
  aimlapi-llm-comparison/
    blog_aimlapi-llm-comparison_20250301.md      ← Publish to your blog
    newsletter_aimlapi-llm-comparison_*.json     ← Send via Beehiiv
    twitter_thread_aimlapi-llm-comparison_*.json ← Schedule via Buffer
    instagram_aimlapi-llm-comparison_*.json      ← Schedule via Buffer/Later
```

---

## Posting Integrations

### Blog → Ghost
```python
import requests
requests.post("https://yourblog.ghost.io/ghost/api/v3/admin/posts/",
    headers={"Authorization": f"Ghost {GHOST_KEY}"},
    json={"posts": [{"title": title, "mobiledoc": content, "status": "draft"}]})
```

### Newsletter → Beehiiv
```python
requests.post(f"https://api.beehiiv.com/v2/publications/{PUB_ID}/posts",
    headers={"Authorization": f"Bearer {BEEHIIV_KEY}"},
    json={"subject": subject, "content": {"free": {"web": body}}, "status": "draft"})
```

### Social → Buffer
```python
requests.post("https://api.bufferapp.com/1/updates/create.json",
    headers={"Authorization": f"Bearer {BUFFER_TOKEN}"},
    data={"text": caption, "profile_ids[]": PROFILE_ID,
          "scheduled_at": "2025-03-03T09:00:00Z"})
```

---

## Automate with GitHub Actions

`.github/workflows/content.yml`:
```yaml
name: Weekly Content
on:
  schedule:
    - cron: '0 9 * * 1'   # Every Monday 9am UTC
  workflow_dispatch:        # Also allows manual trigger

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install anthropic rich
      - run: python scheduler.py --tier 1
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - uses: actions/upload-artifact@v3
        with:
          name: weekly-content
          path: output/
```

---

## Realistic Timeline

| Month | Goal | Action |
|---|---|---|
| 1 | Foundation | Sign up for all 5 Tier 1 programs. Publish first 5 blog posts. Start newsletter. |
| 2 | SEO traction | Publish remaining Tier 1 posts. Set up Buffer for social scheduling. |
| 3 | First conversions | Monitor which posts get traffic. Double down on those topics. |
| 4–6 | Tier 2 + expand | Add Tier 2 programs. Start writing about adjacent niches. |
| 6+ | Compound growth | Recurring commissions stack. Each new post adds to the base. |

---

## Tips

1. **Edit before publishing** — AI output is a strong first draft, not final copy. Add your voice.
2. **Blog is highest ROI** — An SEO post compounds for years. Social posts die in 24 hours.
3. **Always disclose affiliates** — The FTC requires it. Your audience respects it.
4. **Track with UTMs** — Add `?utm_source=blog&utm_medium=affiliate` to your links so you know what converts.
5. **Start with what you've used** — The AI/ML API and Bannerbear posts should come from real experience.
