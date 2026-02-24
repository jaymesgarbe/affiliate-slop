#!/usr/bin/env python3
"""
Affiliate Content Engine
Generates multi-channel content from a single brief using Claude API.

Usage:
    python content_engine.py --topic "GCP vs AWS for ML pipelines" \
                              --affiliate "DigitalOcean" \
                              --affiliate-url "https://digitalocean.com/?ref=YOUR_ID" \
                              --commission "25% recurring" \
                              --audience "ML engineers and data scientists"
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

console = Console()
client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var

# ─────────────────────────────────────────────
# PROMPT TEMPLATES
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert content strategist and copywriter specializing in 
technical SaaS affiliate marketing. You create authentic, value-first content that earns 
trust with developer and technical audiences. You never sound spammy or salesy — you 
educate first, promote second. Always include FTC-compliant affiliate disclosures where appropriate."""

CHANNEL_PROMPTS = {
    "blog": """Write a detailed, SEO-optimized blog post comparing/covering: {topic}

Affiliate product to naturally integrate: {affiliate} ({affiliate_url})
Commission note (internal only, don't mention): {commission}
Target audience: {audience}
Blog canonical URL: https://jaymesinthestack.hashnode.dev
Author: Jaymes (Berkeley EECS grad, developer tools & AI/ML infrastructure)

Requirements:
- Title with primary keyword
- Meta description (155 chars max)
- 1200-1800 words
- H2/H3 structure with markdown
- Include a comparison table if relevant
- 2-3 natural affiliate link placements with anchor text
- Include "Affiliate disclosure: This post contains affiliate links..." at the top
- End with a clear CTA linking back to jaymesinthestack.hashnode.dev
- Tone: authoritative but approachable, like a senior engineer sharing what they learned
- Write in first person — this is a personal blog, not a content farm

Output as JSON with keys: title, meta_description, content (full markdown)""",

    "newsletter": """Write a newsletter section covering: {topic}

Affiliate product to feature: {affiliate} ({affiliate_url})
Target audience: {audience}

Requirements:
- Subject line (A/B test: give 2 options)
- Preview text (90 chars max)
- Newsletter body: conversational, 300-400 words
- Personal angle — write as if sharing something genuinely useful you discovered
- 1 affiliate mention, natural and value-add
- Include affiliate disclosure inline (e.g. "← affiliate link")
- Strong PS line (these get high open rates)

Output as JSON with keys: subject_a, subject_b, preview_text, body (markdown), ps_line""",

    "instagram": """Write Instagram content for: {topic}

Affiliate product: {affiliate}
Target audience: {audience}

Requirements:
- Caption: 150-200 words, hook in first line (before "more" cutoff), value-packed
- Use line breaks for readability
- 3-5 relevant hashtags (mix of niche + broad)
- Subtle CTA to link in bio
- Reel concept: describe a 30-60 second video idea that would perform well for this topic
- Story sequence: 3-slide story concept

Output as JSON with keys: caption, hashtags, reel_concept, story_sequence""",

    "pinterest": """Write Pinterest content for: {topic}

Affiliate product: {affiliate}
Target audience: {audience}

Requirements:
- Pin title (100 chars max, keyword-rich)
- Pin description (500 chars, keyword-rich, natural)
- 5 Pinterest-style keywords/tags
- Board suggestion
- Visual concept: describe the ideal pin image/graphic

Output as JSON with keys: pin_title, pin_description, keywords, board_suggestion, visual_concept""",

    "twitter_thread": """Write a Twitter/X thread about: {topic}

Affiliate product to mention: {affiliate} ({affiliate_url})
Target audience: {audience}

Requirements:
- 8-12 tweets
- Hook tweet that makes people stop scrolling
- Each tweet standalone but builds on previous
- 1 natural affiliate mention mid-thread (not the last tweet)
- Last tweet: engagement CTA (retweet, follow, etc.)
- Include "(🧵 thread)" in first tweet

Output as JSON with keys: tweets (array of strings, each under 280 chars)""",

    "ad_copy": """Write paid ad copy for promoting: {topic} via {affiliate}

Target audience: {audience}
Affiliate URL: {affiliate_url}

Requirements:
- Meta/Instagram Ad: 3 variations
  - Primary text (125 chars)
  - Headline (40 chars)  
  - Description (30 chars)
- Google Search Ad: 2 variations
  - Headlines x3 (30 chars each)
  - Descriptions x2 (90 chars each)
- Hook angles to try: curiosity, pain point, social proof, FOMO

Output as JSON with keys: meta_ads (array of 3 objects), google_ads (array of 2 objects)"""
}

# ─────────────────────────────────────────────
# CORE GENERATION
# ─────────────────────────────────────────────

def generate_content(channel: str, brief: dict) -> dict:
    """Generate content for a specific channel."""
    prompt = CHANNEL_PROMPTS[channel].format(**brief)
    
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = message.content[0].text
    
    # Extract JSON from response
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Fallback: return raw text
    return {"raw": raw}


def save_output(channel: str, content: dict, output_dir: Path, brief: dict):
    """Save generated content to files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = brief['topic'][:40].lower().replace(' ', '_').replace('/', '_')
    
    if channel == "blog":
        # Save as markdown
        filepath = output_dir / f"blog_{slug}_{timestamp}.md"
        if "content" in content:
            md = f"# {content.get('title', '')}\n\n"
            md += f"*Meta: {content.get('meta_description', '')}*\n\n"
            md += content["content"]
            filepath.write_text(md)
        else:
            filepath.write_text(content.get("raw", str(content)))
    else:
        # Save as JSON
        filepath = output_dir / f"{channel}_{slug}_{timestamp}.json"
        filepath.write_text(json.dumps(content, indent=2))
    
    return filepath


def display_content(channel: str, content: dict):
    """Pretty print content to console."""
    console.print(f"\n[bold cyan]━━━ {channel.upper().replace('_', ' ')} ━━━[/bold cyan]")
    
    if channel == "blog" and "content" in content:
        console.print(f"[bold]Title:[/bold] {content.get('title', 'N/A')}")
        console.print(f"[bold]Meta:[/bold] {content.get('meta_description', 'N/A')}")
        console.print(f"[dim](Full content saved to file)[/dim]")
    
    elif channel == "newsletter":
        console.print(f"[bold]Subject A:[/bold] {content.get('subject_a', 'N/A')}")
        console.print(f"[bold]Subject B:[/bold] {content.get('subject_b', 'N/A')}")
        console.print(f"[bold]Preview:[/bold] {content.get('preview_text', 'N/A')}")
        console.print(f"[bold]PS:[/bold] {content.get('ps_line', 'N/A')}")
    
    elif channel == "instagram":
        console.print(f"[bold]Caption:[/bold]\n{content.get('caption', 'N/A')}")
        console.print(f"[bold]Hashtags:[/bold] {content.get('hashtags', 'N/A')}")
        console.print(f"[bold]Reel Concept:[/bold] {content.get('reel_concept', 'N/A')}")
    
    elif channel == "pinterest":
        console.print(f"[bold]Pin Title:[/bold] {content.get('pin_title', 'N/A')}")
        console.print(f"[bold]Description:[/bold] {content.get('pin_description', 'N/A')}")
        console.print(f"[bold]Board:[/bold] {content.get('board_suggestion', 'N/A')}")
    
    elif channel == "twitter_thread":
        tweets = content.get("tweets", [])
        for i, tweet in enumerate(tweets, 1):
            console.print(f"[bold]Tweet {i}:[/bold] {tweet}")
    
    elif channel == "ad_copy":
        meta_ads = content.get("meta_ads", [])
        if meta_ads:
            console.print("[bold]Meta Ad #1:[/bold]")
            ad = meta_ads[0]
            console.print(f"  Primary: {ad.get('primary_text', 'N/A')}")
            console.print(f"  Headline: {ad.get('headline', 'N/A')}")
    
    elif "raw" in content:
        console.print(content["raw"][:500] + "..." if len(content.get("raw","")) > 500 else content.get("raw",""))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

CHANNELS = ["blog", "newsletter", "instagram", "pinterest", "twitter_thread", "ad_copy"]

def main():
    parser = argparse.ArgumentParser(description="Affiliate Content Engine — Generate multi-channel content")
    parser.add_argument("--topic", required=True, help="The topic/comparison to cover")
    parser.add_argument("--affiliate", required=True, help="Affiliate product/company name")
    parser.add_argument("--affiliate-url", default="https://example.com/?ref=YOUR_ID", help="Your affiliate URL")
    parser.add_argument("--commission", default="recurring commission", help="Commission structure (for your reference)")
    parser.add_argument("--audience", default="developers and technical professionals", help="Target audience")
    parser.add_argument("--channels", nargs="+", choices=CHANNELS, default=CHANNELS, help="Channels to generate for")
    parser.add_argument("--output-dir", default="./output", help="Directory to save output files")
    args = parser.parse_args()

    brief = {
        "topic": args.topic,
        "affiliate": args.affiliate,
        "affiliate_url": args.affiliate_url,
        "commission": args.commission,
        "audience": args.audience,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Header
    console.print(Panel.fit(
        f"[bold green]Affiliate Content Engine[/bold green]\n"
        f"Topic: [cyan]{args.topic}[/cyan]\n"
        f"Affiliate: [yellow]{args.affiliate}[/yellow]\n"
        f"Channels: [magenta]{', '.join(args.channels)}[/magenta]",
        title="🚀 Content Generation"
    ))

    results = {}
    saved_files = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for channel in args.channels:
            task = progress.add_task(f"Generating {channel.replace('_', ' ')}...", total=None)
            try:
                content = generate_content(channel, brief)
                results[channel] = content
                filepath = save_output(channel, content, output_dir, brief)
                saved_files.append((channel, filepath))
                progress.update(task, description=f"[green]✓[/green] {channel.replace('_', ' ')}")
            except Exception as e:
                progress.update(task, description=f"[red]✗[/red] {channel}: {e}")
                results[channel] = {"error": str(e)}
            progress.stop_task(task)

    # Display results
    for channel, content in results.items():
        if "error" not in content:
            display_content(channel, content)

    # Summary table
    console.print("\n")
    table = Table(title="📁 Saved Files", show_header=True, header_style="bold magenta")
    table.add_column("Channel", style="cyan")
    table.add_column("File", style="green")
    for channel, filepath in saved_files:
        table.add_row(channel.replace("_", " ").title(), str(filepath))
    console.print(table)
    console.print(f"\n[bold green]✓ Done! All content saved to {output_dir}/[/bold green]")


if __name__ == "__main__":
    main()
