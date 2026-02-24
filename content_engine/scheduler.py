#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
"""
Content Scheduler
Runs content_engine.py in batch mode from topics.json.
Supports tiered rollout: start with Tier 1, unlock Tier 2 after traction.

Usage:
    python scheduler.py              # Run all scheduled Tier 1 topics
    python scheduler.py --tier 2     # Run Tier 2 topics
    python scheduler.py --slug aimlapi-llm-comparison  # Run one specific topic
    python scheduler.py --list       # Preview all topics without generating

Cron (every Monday 9am):
    0 9 * * 1 cd /path/to/project && python scheduler.py >> logs/scheduler.log 2>&1

GitHub Actions: see .github/workflows/content.yml
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

TOPICS_FILE = Path("topics.json")
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "scheduler.log"

# ── Site config ──────────────────────────────────────────────────────────────
BLOG_URL = "https://jaymesinthestack.hashnode.dev"
BLOG_PLATFORM = "hashnode"
NEWSLETTER_URL = "https://jaymesinthestack.beehiiv.com"
DOMAIN = "https://jaymesinthestack.com"
TWITTER = "https://x.com/jaymes_stack"
INSTAGRAM = "https://www.instagram.com/jaymesinthestack/"
PINTEREST = "https://www.pinterest.com/jaymesinthestack/"

# ── Affiliate registry ────────────────────────────────────────────────────────
AFFILIATES = {
    "AI/ML API": {
        "url": "https://aimlapi.com/?via=jaymes",
        "commission": "30% recurring forever",
        "signup": "https://aimlapi.com/affiliate-program"
    },
    "Feather": {
        "url": "https://feather.so/?via=jaymes",
        "commission": "25% recurring forever",
        "signup": "https://feather.getrewardful.com/"
    },
    "Railway": {
        "url": "https://railway.com?referralCode=tIqKm6",
        "commission": "20 credits per referral",
        "signup": "https://railway.com/referral"
    },
    "SearchApi": {
        "url": "https://www.searchapi.io/?via=jaymes",
        "commission": "30% recurring for 12 months",
        "signup": "https://www.searchapi.io/affiliate-program"
    },
    "Instatus": {
        "url": "https://instatus.com?via=jaymes",
        "commission": "30% recurring forever",
        "signup": "https://instatus.com/affiliates"
    },
    "Apify": {
        "url": "PENDING",
        "commission": "20% months 1-3, 30% recurring forever after",
        "signup": "https://affiliate.apify.com/"
    },
}
# ─────────────────────────────────────────────────────────────────────────────


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_topic(topic: dict) -> bool:
    affiliate_name = topic["affiliate"]
    affiliate_info = AFFILIATES.get(affiliate_name, {})

    affiliate_url = topic.get("affiliate_url", "")
    if ("YOUR_ID" in affiliate_url or affiliate_url == "") and affiliate_info.get("url"):
        affiliate_url = affiliate_info["url"]

    if affiliate_url == "PENDING":
        log(f"⚠ Skipping {topic['slug']} — {affiliate_name} affiliate link is still pending approval.")
        return False

    log(f">> Starting: [Tier {topic.get('tier','?')}] {topic['slug']}")
    if topic.get("notes"):
        log(f"  Strategy: {topic['notes']}")

    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent))
        from content_engine import generate_content, save_output, CHANNELS
        from pathlib import Path as _Path

        brief = {
            "topic":         topic["topic"],
            "affiliate":     affiliate_name,
            "affiliate_url": affiliate_url,
            "commission":    topic.get("commission", affiliate_info.get("commission", "recurring")),
            "audience":      topic.get("audience", "developers and technical professionals"),
        }

        channels = topic.get("channels", ["blog", "newsletter", "twitter_thread"])
        output_dir = _Path("output") / topic["slug"]
        output_dir.mkdir(parents=True, exist_ok=True)

        for channel in channels:
            log(f"  Generating {channel}...")
            result = generate_content(channel, brief)
            filepath = save_output(channel, result, output_dir, brief)
            log(f"  Saved: {filepath}")

        log(f"OK Done: {topic['slug']}")
        return True
    except Exception as e:
        log(f"XX Failed: {topic['slug']}")
        log(f"  Error: {e}")
        return False


def list_topics(topics: list, tier: int = None):
    filtered = [t for t in topics if tier is None or t.get("tier") == tier]
    by_affiliate = {}
    for t in filtered:
        by_affiliate.setdefault(t["affiliate"], []).append(t)

    print(f"\n{'═'*70}")
    print(f"  TOPIC QUEUE  {'(Tier ' + str(tier) + ')' if tier else '(All Tiers)'}")
    print(f"{'═'*70}")
    for affiliate, tops in by_affiliate.items():
        info = AFFILIATES.get(affiliate, {})
        print(f"\n  📦 {affiliate}  [{info.get('commission','?')}]")
        print(f"     Sign up: {info.get('signup', 'N/A')}")
        for t in tops:
            status = "* scheduled" if t.get("scheduled") else "  paused"
            print(f"     [Tier {t.get('tier','?')}] {status}  {t['slug']}")
            print(f"          \"{t['topic'][:72]}{'...' if len(t['topic'])>72 else ''}\"")
    print(f"\n  Total: {len(filtered)} topics\n")


def main():
    parser = argparse.ArgumentParser(description="Content Scheduler")
    parser.add_argument("--tier", type=int, choices=[1, 2], help="Only run this tier")
    parser.add_argument("--slug", help="Run a single topic by slug")
    parser.add_argument("--list", action="store_true", help="Preview topics without generating")
    parser.add_argument("--all", action="store_true", help="Run all scheduled topics (both tiers)")
    args = parser.parse_args()

    if not TOPICS_FILE.exists():
        log("topics.json not found. Run from the content_engine directory.")
        sys.exit(1)

    topics = json.loads(TOPICS_FILE.read_text())

    if args.list:
        list_topics(topics, args.tier)
        return

    if args.slug:
        to_run = [t for t in topics if t["slug"] == args.slug]
        if not to_run:
            log(f"No topic found with slug: {args.slug}")
            sys.exit(1)
    elif args.tier:
        to_run = [t for t in topics if t.get("scheduled") and t.get("tier") == args.tier]
    elif args.all:
        to_run = [t for t in topics if t.get("scheduled")]
    else:
        to_run = [t for t in topics if t.get("scheduled") and t.get("tier", 1) == 1]

    if not to_run:
        log("No topics matched. Use --list to see available topics.")
        return

    # Warn about pending affiliates
    pending = {
        t["affiliate"] for t in to_run
        if AFFILIATES.get(t["affiliate"], {}).get("url") == "PENDING"
    }
    if pending:
        log("⚠️  Affiliates with pending approval (will be skipped):")
        for a in sorted(pending):
            log(f"   → {a}: {AFFILIATES[a]['signup']}")

    log(f"Starting batch: {len(to_run)} topics")
    success, failed, skipped = 0, 0, 0

    for topic in to_run:
        result = run_topic(topic)
        if result:
            success += 1
        elif AFFILIATES.get(topic["affiliate"], {}).get("url") == "PENDING":
            skipped += 1
        else:
            failed += 1

    log(f"{'─'*50}")
    log(f"Batch complete: {success} succeeded, {failed} failed, {skipped} skipped (pending)")
    log(f"Output saved to: output/")


if __name__ == "__main__":
    main()
