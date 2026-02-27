#!/usr/bin/env python3
"""
Affiliate Content Engine
Generates multi-channel content from a single brief using Claude API.
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
from rich.table import Table

console = Console()
client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an expert content strategist and copywriter specializing in \
technical SaaS affiliate marketing. You create authentic, value-first content that earns \
trust with developer and technical audiences. You never sound spammy or salesy — you \
educate first, promote second. Always include FTC-compliant affiliate disclosures where appropriate.
IMPORTANT: The current year is 2026. Always reference 2026 (not 2025) when writing about current tools, pricing, benchmarks, or trends."""

CHANNEL_PROMPTS = {
    "blog": """Write a detailed, SEO-optimized blog post comparing/covering: {topic}

Affiliate product to naturally integrate: {affiliate} ({affiliate_url})
Commission note (internal only, don't mention): {commission}
Target audience: {audience}
Blog canonical URL: https://jaymesinthestack.hashnode.dev
Domain: https://jaymesinthestack.com
Author: Jaymes (Berkeley EECS grad, developer tools & AI/ML infrastructure)
Social: @jaymes_stack (Twitter/X), @jaymesinthestack (Instagram, Pinterest)
Newsletter: https://jaymesinthestack.beehiiv.com

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

    "newsletter": """Write a newsletter issue covering: {topic}

Newsletter URL: https://jaymesinthestack.beehiiv.com
Blog: https://jaymesinthestack.hashnode.dev
Domain: https://jaymesinthestack.com
Author: Jaymes (Berkeley EECS grad, developer tools & AI/ML infrastructure)
Social: @jaymes_stack (Twitter/X), @jaymesinthestack (Instagram, Pinterest)

Affiliate product to feature: {affiliate} ({affiliate_url})
Target audience: {audience}

Requirements:
- Subject line (A/B test: give 2 options, subject_b should be the stronger/more curious one)
- Preview text (90 chars max)
- opener: 1-2 sentence personal opener — what you've been building or thinking this week
- Main body: conversational, 300-400 words, first person
- Affiliate mention: 1 natural placement, value-add framing, include inline disclosure
- quick_hits: 3 bullet strings — interesting things found this week related to the topic
- Strong PS line

Output as JSON with keys: subject_a, subject_b, preview_text, opener, body (markdown), quick_hits (array of 3 strings), ps_line""",

    "instagram": """Write Instagram content for: {topic}

Affiliate product: {affiliate}
Target audience: {audience}

Requirements:
- Caption: 150-200 words, hook in first line (before "more" cutoff), value-packed, written in first person (I not We)
- Use line breaks for readability
- 3-5 relevant hashtags (mix of niche + broad)
- CTA pointing to links.jaymesinthestack.com
- carousel_points: 5 key data points or facts for a visual carousel (each under 15 words)

Output as JSON with keys: caption, hashtags, cta, carousel_points (array of 5 strings)""",

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
Current year: 2026

Requirements:
- 8-12 tweets
- Hook tweet that makes people stop scrolling
- Each tweet standalone but builds on previous
- 1 natural affiliate mention mid-thread (not the last tweet)
- Last tweet: engagement CTA ending with #buildinpublic — NO other hashtags anywhere in the thread
- Include "(thread)" in first tweet — NO emoji
- CRITICAL: Every single tweet MUST be 280 characters or fewer including spaces. Count carefully.
- Write like a real senior engineer sharing genuine insights, not a marketer

Output as JSON with keys: tweets (array of strings, each STRICTLY under 280 chars)""",

    "ad_copy": """Write paid ad copy for promoting: {topic} via {affiliate}

Target audience: {audience}
Affiliate URL: {affiliate_url}

Requirements:
- Meta/Instagram Ad: 3 variations (primary text 125 chars, headline 40 chars, description 30 chars)
- Google Search Ad: 2 variations (headlines x3 30 chars, descriptions x2 90 chars)

Output as JSON with keys: meta_ads (array of 3 objects), google_ads (array of 2 objects)"""
}


def _slug(brief: dict) -> str:
    return (brief['topic'][:40].lower()
            .replace(' ', '_').replace('/', '_').replace(':', '')
            .replace('?', '').replace('*', '').replace('"', '')
            .replace('<', '').replace('>', '').replace('|', '').replace('\\', ''))


def _generate_blog_thumbnail_html(content: dict, brief: dict, output_path: Path):
    title = content.get('title', brief.get('topic', ''))
    display_title = title if len(title) <= 60 else title[:57] + '...'
    topic_tag = brief.get('affiliate', 'Dev Tools')
    date = datetime.now().strftime('%b %Y')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@700;800;900&display=swap" rel="stylesheet">
<style>
  * {{ margin:0;padding:0;box-sizing:border-box; }}
  body {{ width:1200px;height:630px;overflow:hidden;background:#0a0a0f;font-family:'JetBrains Mono',monospace;display:flex;align-items:center;justify-content:center; }}
  .bg-grid {{ position:absolute;inset:0;background-image:linear-gradient(rgba(0,255,135,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,135,0.03) 1px,transparent 1px);background-size:48px 48px; }}
  .glow {{ position:absolute;width:800px;height:800px;border-radius:50%;background:radial-gradient(circle,rgba(0,255,135,0.07) 0%,transparent 65%);top:50%;left:50%;transform:translate(-50%,-50%); }}
  .accent-top {{ position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#00ff87,#00d4ff,#8b5cf6); }}
  .accent-bottom {{ position:absolute;bottom:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#8b5cf6,#00d4ff,#00ff87); }}
  .content {{ position:relative;z-index:1;width:100%;padding:64px 80px;display:flex;flex-direction:column;justify-content:space-between;height:100%; }}
  .top-row {{ display:flex;align-items:center;gap:16px; }}
  .tag {{ font-size:12px;color:#00ff87;letter-spacing:2px;text-transform:uppercase;border:1px solid #00ff8740;background:#00ff8712;padding:5px 14px;border-radius:99px; }}
  .date {{ font-size:12px;color:#333;letter-spacing:1px; }}
  .title {{ font-family:'Syne',sans-serif;font-size:58px;font-weight:900;color:#fff;line-height:1.05;letter-spacing:-2px;max-width:900px; }}
  .title span {{ color:#00ff87; }}
  .bottom-row {{ display:flex;align-items:center;justify-content:space-between; }}
  .brand {{ display:flex;flex-direction:column;gap:4px; }}
  .brand-name {{ font-family:'Syne',sans-serif;font-size:20px;font-weight:800;color:#fff;letter-spacing:-0.5px; }}
  .brand-url {{ font-size:13px;color:#444; }}
  .terminal-badge {{ background:#0e0e16;border:1px solid #1e1e2e;border-radius:10px;padding:14px 20px;display:flex;align-items:center;gap:10px; }}
  .dr {{ width:10px;height:10px;border-radius:50%;background:#ff5f57; }}
  .dy {{ width:10px;height:10px;border-radius:50%;background:#febc2e; }}
  .dg {{ width:10px;height:10px;border-radius:50%;background:#28c840; }}
  .tt {{ font-size:14px;color:#555;margin-left:8px; }}
  .tt span {{ color:#00ff87; }}
</style>
</head>
<body>
<div class="bg-grid"></div><div class="glow"></div>
<div class="accent-top"></div><div class="accent-bottom"></div>
<div class="content">
  <div class="top-row"><span class="tag">{topic_tag}</span><span class="date">// {date}</span></div>
  <div class="title">{display_title}</div>
  <div class="bottom-row">
    <div class="brand"><div class="brand-name">Jaymes in the Stack</div><div class="brand-url">jaymesinthestack.com</div></div>
    <div class="terminal-badge"><div class="dr"></div><div class="dy"></div><div class="dg"></div><div class="tt"><span>@jaymes_stack</span></div></div>
  </div>
</div>
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")


def _generate_newsletter_html(content: dict, brief: dict, output_path: Path):
    subject_b = content.get('subject_b', content.get('subject_a', brief.get('topic', '')))
    opener = content.get('opener', '')
    body = content.get('body', '')
    quick_hits = content.get('quick_hits', [])
    affiliate = brief.get('affiliate', '')
    affiliate_url = brief.get('affiliate_url', '')
    ps_line = content.get('ps_line', '')
    date_str = datetime.now().strftime('%b %Y')
    issue_label = datetime.now().strftime('%Y%m')

    def md(text):
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#fff;">\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#00d4ff;text-decoration:none;">\1</a>', text)
        return text

    body_html = ''
    for para in body.strip().split('\n\n'):
        para = para.strip()
        if not para:
            continue
        if para.startswith('## '):
            body_html += f'<h2 style="font-family:Georgia,serif;font-size:20px;font-weight:bold;color:#fff;margin:24px 0 12px;">{md(para[3:])}</h2>'
        else:
            body_html += f'<p style="font-family:Georgia,serif;font-size:15px;color:#aaa;line-height:1.8;margin:0 0 16px;">{md(para)}</p>'

    qh_html = ''
    for hit in quick_hits:
        qh_html += f'<tr><td style="padding:8px 0;border-bottom:1px solid #13131f;"><span style="font-family:\'Courier New\',monospace;font-size:12px;color:#8b5cf6;">&#8594;</span><span style="font-family:Georgia,serif;font-size:14px;color:#aaa;margin-left:8px;">{md(hit)}</span></td></tr>'

    html = f"""<!-- JAYMES IN THE STACK — Newsletter — Inline styles for Beehiiv -->
<div style="background-color:#0a0a0f;padding:0;margin:0;font-family:'Courier New',Courier,monospace;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#0a0a0f;">
<tr><td align="center" style="padding:32px 16px;">
<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#0e0e16;border:1px solid #1e1e2e;border-radius:12px;overflow:hidden;">
<tr><td style="height:3px;background:linear-gradient(90deg,#00ff87,#00d4ff,#8b5cf6);font-size:0;line-height:0;">&nbsp;</td></tr>
<tr><td style="padding:28px 32px 20px;border-bottom:1px solid #1e1e2e;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
    <td>
      <div style="font-family:'Courier New',monospace;font-size:11px;color:#00ff87;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;">// jaymes in the stack</div>
      <div style="font-family:Georgia,serif;font-size:22px;font-weight:bold;color:#fff;letter-spacing:-0.5px;line-height:1.2;">{subject_b}</div>
      <div style="font-family:'Courier New',monospace;font-size:11px;color:#444;margin-top:8px;">Issue #{issue_label} &nbsp;&middot;&nbsp; {date_str} &nbsp;&middot;&nbsp; 3 min read</div>
    </td>
    <td align="right" valign="top" style="padding-left:16px;">
      <div style="background-color:#00ff8715;border:1px solid #00ff8740;border-radius:8px;padding:8px 12px;text-align:center;">
        <div style="font-family:'Courier New',monospace;font-size:18px;font-weight:bold;color:#00ff87;">&gt;_</div>
        <div style="font-family:'Courier New',monospace;font-size:9px;color:#00ff87;letter-spacing:1px;margin-top:2px;">STACK</div>
      </div>
    </td>
  </tr></table>
</td></tr>
<tr><td style="padding:24px 32px 0;">
  <p style="font-family:Georgia,serif;font-size:15px;color:#999;line-height:1.7;margin:0;">Hey &mdash;</p>
  <p style="font-family:Georgia,serif;font-size:15px;color:#999;line-height:1.7;margin:12px 0 0;">{md(opener)}</p>
</td></tr>
<tr><td style="padding:24px 32px;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="border-top:1px solid #1e1e2e;font-size:0;line-height:0;">&nbsp;</td></tr></table></td></tr>
<tr><td style="padding:0 32px;">
  <div style="font-family:'Courier New',monospace;font-size:10px;color:#00ff87;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">&#9655; This week in the stack</div>
  {body_html}
  <table cellpadding="0" cellspacing="0" border="0" style="margin:20px 0;">
    <tr><td style="background-color:#00ff8715;border:1px solid #00ff8740;border-radius:6px;padding:12px 20px;">
      <a href="https://jaymesinthestack.hashnode.dev" style="font-family:'Courier New',monospace;font-size:13px;color:#00ff87;text-decoration:none;font-weight:bold;">&#9658; Read the full breakdown &rarr;</a>
    </td></tr>
  </table>
</td></tr>
<tr><td style="padding:24px 32px;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="border-top:1px solid #1e1e2e;font-size:0;line-height:0;">&nbsp;</td></tr></table></td></tr>
<tr><td style="padding:0 32px;">
  <div style="font-family:'Courier New',monospace;font-size:10px;color:#00d4ff;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">&#9655; Tool worth knowing</div>
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#0b0b18;border:1px solid #1e2a3a;border-radius:8px;">
    <tr><td style="padding:20px 24px;">
      <div style="font-family:'Courier New',monospace;font-size:13px;color:#00d4ff;font-weight:bold;margin-bottom:8px;">{affiliate}</div>
      <p style="font-family:Georgia,serif;font-size:14px;color:#888;line-height:1.7;margin:0 0 12px;">Worth checking out if you're building anything AI-related. Saves a ton of time.</p>
      <p style="font-family:'Courier New',monospace;font-size:11px;color:#444;margin:0;">&larr; affiliate link &nbsp;&middot;&nbsp; <a href="{affiliate_url}" style="color:#00d4ff;text-decoration:none;">{affiliate_url}</a></p>
    </td></tr>
  </table>
</td></tr>
<tr><td style="padding:24px 32px;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="border-top:1px solid #1e1e2e;font-size:0;line-height:0;">&nbsp;</td></tr></table></td></tr>
<tr><td style="padding:0 32px;">
  <div style="font-family:'Courier New',monospace;font-size:10px;color:#8b5cf6;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">&#9655; Quick hits</div>
  <table width="100%" cellpadding="0" cellspacing="0" border="0">{qh_html}</table>
</td></tr>
<tr><td style="padding:24px 32px;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="border-top:1px solid #1e1e2e;font-size:0;line-height:0;">&nbsp;</td></tr></table></td></tr>
<tr><td style="padding:0 32px 8px;">
  <p style="font-family:Georgia,serif;font-size:15px;color:#aaa;line-height:1.7;margin:0;">Drop me a reply if you want to dig deeper. Happy to share.</p>
  <p style="font-family:Georgia,serif;font-size:15px;color:#aaa;line-height:1.7;margin:16px 0 0;">&mdash; Jaymes</p>
  <p style="font-family:'Courier New',monospace;font-size:11px;color:#444;margin:8px 0 0;">Berkeley EECS &nbsp;&middot;&nbsp; Developer tools &amp; AI/ML infrastructure<br><a href="https://twitter.com/jaymes_stack" style="color:#444;text-decoration:none;">@jaymes_stack</a> on X &nbsp;&middot;&nbsp; <a href="https://jaymesinthestack.hashnode.dev" style="color:#444;text-decoration:none;">jaymesinthestack.com</a></p>
</td></tr>
<tr><td style="padding:20px 32px;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#0f1a14;border-left:3px solid #00ff87;border-radius:0 6px 6px 0;">
    <tr><td style="padding:16px 20px;">
      <p style="font-family:Georgia,serif;font-size:14px;color:#888;line-height:1.7;margin:0;"><strong style="color:#00ff87;font-family:'Courier New',monospace;font-size:12px;letter-spacing:1px;">P.S.</strong> &nbsp;{md(ps_line)}</p>
    </td></tr>
  </table>
</td></tr>
<tr><td style="padding:20px 32px;border-top:1px solid #1e1e2e;background-color:#0b0b14;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
    <td><p style="font-family:'Courier New',monospace;font-size:10px;color:#333;margin:0;line-height:1.6;">You're receiving this because you subscribed at <a href="https://jaymesinthestack.beehiiv.com" style="color:#333;text-decoration:none;">jaymesinthestack.beehiiv.com</a><br><a href="*|UNSUBSCRIBE|*" style="color:#333;text-decoration:none;">Unsubscribe</a> &nbsp;&middot;&nbsp; <a href="*|UPDATE_PROFILE|*" style="color:#333;text-decoration:none;">Update preferences</a></p></td>
    <td align="right"><p style="font-family:'Courier New',monospace;font-size:10px;color:#00ff87;margin:0;">JITS #{issue_label}</p></td>
  </tr></table>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,#8b5cf6,#00d4ff,#00ff87);font-size:0;line-height:0;">&nbsp;</td></tr>
</table>
</td></tr>
</table>
</div>"""
    output_path.write_text(html, encoding="utf-8")


def _generate_instagram_carousel_html(content: dict, brief: dict, output_path: Path):
    topic = brief.get('topic', '')
    affiliate_url = brief.get('affiliate_url', '')
    points = content.get('carousel_points', [
        'API pricing varies wildly — always benchmark before committing',
        'Latency at p99 matters more than average for production apps',
        'Context window size is an architectural decision, not a feature',
        'Open-source models now match frontier models on many tasks',
        'Unified API routing cuts costs 60-70% with smart model selection',
    ])
    while len(points) < 5:
        points.append('More in the full breakdown — link in bio')

    colors = ['#00d4ff', '#8b5cf6', '#f59e0b']

    slide1 = f"""
<div class="label">SLIDE 1 of 5 — Screenshot at 1080x1080</div>
<div class="slide" style="background:#0a0a0f;">
  <div class="brand-bar"></div><div class="bg-grid"></div>
  <div style="position:absolute;width:700px;height:700px;border-radius:50%;background:radial-gradient(circle,rgba(0,255,135,0.08) 0%,transparent 70%);top:50%;left:50%;transform:translate(-50%,-50%);"></div>
  <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:80px;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:16px;color:#00ff87;letter-spacing:3px;text-transform:uppercase;margin-bottom:32px;">// breakdown</div>
    <div style="font-family:'Syne',sans-serif;font-size:82px;font-weight:900;color:#fff;line-height:0.95;letter-spacing:-3px;margin-bottom:40px;">I tested<br><span style="color:#00ff87;">this</span><br>so you<br>don't have<br>to.</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:17px;color:#555;line-height:1.6;">{topic[:55]}</div>
  </div>
  <div style="position:absolute;bottom:60px;left:80px;display:flex;align-items:center;gap:12px;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:14px;color:#444;letter-spacing:1px;">swipe for results</span>
    <span style="color:#00ff87;font-size:20px;">&#8594;</span>
  </div>
  <div class="handle">@jaymesinthestack</div><div class="slide-num">01 / 05</div>
  <div class="brand-footer"></div>
</div>"""

    data_slides = ''
    labels = ['insight 01', 'insight 02', 'insight 03']
    for i, (pt, color, label) in enumerate(zip(points[:3], colors, labels), 2):
        data_slides += f"""
<div class="label">SLIDE {i} of 5 — Screenshot at 1080x1080</div>
<div class="slide" style="background:#0a0a0f;">
  <div class="brand-bar"></div><div class="bg-grid"></div>
  <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:80px;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:13px;color:{color};letter-spacing:3px;text-transform:uppercase;margin-bottom:40px;">// {label}</div>
    <div style="font-family:'Syne',sans-serif;font-size:68px;font-weight:900;color:#fff;line-height:1.05;letter-spacing:-2px;margin-bottom:48px;">{pt}</div>
    <div style="width:60px;height:4px;background:{color};border-radius:99px;"></div>
  </div>
  <div class="handle">@jaymesinthestack</div><div class="slide-num">0{i} / 05</div>
  <div class="brand-footer"></div>
</div>"""

    slide5 = f"""
<div class="label">SLIDE 5 of 5 — Screenshot at 1080x1080</div>
<div class="slide" style="background:#0a0a0f;">
  <div class="brand-bar"></div><div class="bg-grid"></div>
  <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:80px;">
    <div style="background:#0e0e16;border:1px solid #1e1e2e;border-radius:12px;padding:40px 48px;width:100%;max-width:860px;margin-bottom:56px;">
      <div style="display:flex;gap:8px;margin-bottom:24px;">
        <div style="width:12px;height:12px;border-radius:50%;background:#ff5f57;"></div>
        <div style="width:12px;height:12px;border-radius:50%;background:#febc2e;"></div>
        <div style="width:12px;height:12px;border-radius:50%;background:#28c840;"></div>
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:17px;color:#555;text-align:left;margin-bottom:10px;"><span style="color:#00ff87;">$</span> full breakdown + tools</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:17px;color:#00d4ff;text-align:left;">links.jaymesinthestack.com</div>
    </div>
    <div style="font-family:'Syne',sans-serif;font-size:50px;font-weight:900;color:#fff;line-height:1.1;letter-spacing:-2px;margin-bottom:20px;">Follow for more<br>no-BS AI engineering.</div>
    <div style="font-family:'Syne',sans-serif;font-size:38px;font-weight:900;color:#00ff87;letter-spacing:-1px;">@jaymesinthestack</div>
  </div>
  <div class="slide-num">05 / 05</div>
  <div class="brand-footer"></div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Instagram Carousel</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@700;800;900&display=swap" rel="stylesheet">
<style>
  * {{ margin:0;padding:0;box-sizing:border-box; }}
  body {{ background:#111;font-family:'JetBrains Mono',monospace;padding:40px;display:flex;flex-direction:column;gap:40px;align-items:center; }}
  .label {{ color:#555;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;align-self:flex-start;width:1080px; }}
  .slide {{ width:1080px;height:1080px;position:relative;overflow:hidden;flex-shrink:0; }}
  .brand-bar {{ position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#00ff87,#00d4ff,#8b5cf6); }}
  .brand-footer {{ position:absolute;bottom:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#8b5cf6,#00d4ff,#00ff87); }}
  .handle {{ position:absolute;bottom:28px;right:40px;font-family:'JetBrains Mono',monospace;font-size:18px;color:#00ff87;font-weight:700;letter-spacing:1px; }}
  .slide-num {{ position:absolute;bottom:28px;left:40px;font-family:'JetBrains Mono',monospace;font-size:14px;color:#333;letter-spacing:2px; }}
  .bg-grid {{ position:absolute;inset:0;background-image:linear-gradient(rgba(0,255,135,0.025) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,135,0.025) 1px,transparent 1px);background-size:60px 60px; }}
</style>
</head>
<body>
{slide1}
{data_slides}
{slide5}
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")


def _generate_benchmark_html(content: dict, brief: dict, output_path: Path):
    topic = brief.get("topic", "Comparison")
    tweets = content.get("tweets", [])
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
  * {{ margin:0;padding:0;box-sizing:border-box; }}
  body {{ background:#0a0a0f;display:flex;align-items:center;justify-content:center;min-height:100vh;font-family:'JetBrains Mono',monospace;padding:40px; }}
  .card {{ width:860px;background:#0e0e16;border:1px solid #1e1e2e;border-radius:16px;overflow:hidden;position:relative; }}
  .card::before {{ content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#00ff87,#00d4ff,#8b5cf6,#00ff87);background-size:200% 100%;animation:shimmer 3s linear infinite; }}
  @keyframes shimmer {{ 0% {{ background-position:0% 0; }} 100% {{ background-position:200% 0; }} }}
  .header {{ padding:28px 32px 20px;border-bottom:1px solid #1e1e2e;display:flex;align-items:baseline;gap:16px; }}
  .header h1 {{ font-family:'Syne',sans-serif;font-size:20px;font-weight:800;color:#fff;letter-spacing:-0.5px; }}
  .tag {{ font-size:11px;color:#00ff87;border:1px solid #00ff8740;background:#00ff8710;padding:3px 10px;border-radius:99px;letter-spacing:1px;text-transform:uppercase; }}
  .byline {{ margin-left:auto;font-size:11px;color:#444; }}
  .body {{ padding:24px 32px; }}
  .tweet-list {{ list-style:none; }}
  .tweet-item {{ padding:12px 0;border-bottom:1px solid #13131f;font-size:13px;color:#ccc;line-height:1.6; }}
  .tweet-item:last-child {{ border-bottom:none; }}
  .tweet-num {{ color:#00ff87;font-weight:700;margin-right:8px; }}
  .footer {{ padding:16px 32px;border-top:1px solid #1e1e2e;display:flex;justify-content:space-between;background:#0b0b14; }}
  .footer-note {{ font-size:10px;color:#333; }}
  .footer-brand {{ font-size:11px;color:#00ff87;font-weight:600; }}
</style>
</head>
<body>
<div class="card">
  <div class="header"><h1>{topic}</h1><span class="tag">2026</span><span class="byline">jaymesinthestack.com</span></div>
  <div class="body"><ul class="tweet-list">
"""
    for i, tweet in enumerate(tweets[:5], 1):
        clean = tweet.replace('<', '&lt;').replace('>', '&gt;')
        html += f'    <li class="tweet-item"><span class="tweet-num">{i}/</span>{clean}</li>\n'
    html += """  </ul></div>
  <div class="footer"><span class="footer-note">Full thread on X — @jaymes_stack</span><span class="footer-brand">jaymes_stack</span></div>
</div></body></html>"""
    output_path.write_text(html, encoding="utf-8")


def generate_content(channel: str, brief: dict) -> dict:
    prompt = CHANNEL_PROMPTS[channel].format(**brief)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {"raw": raw}


def save_output(channel: str, content: dict, output_dir: Path, brief: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug(brief)

    if channel == "blog":
        filepath = output_dir / f"blog_{slug}_{timestamp}.md"
        if "content" in content:
            md = f"TITLE:\n{content.get('title', '')}\n\nSUBTITLE:\n{content.get('meta_description', '')}\n\nBODY:\n{content['content']}"
            filepath.write_text(md, encoding="utf-8")
        else:
            filepath.write_text(content.get("raw", str(content)), encoding="utf-8")
        # Thumbnail (also used by newsletter as cover)
        thumb_path = output_dir / f"thumbnail_{slug}_{timestamp}.html"
        _generate_blog_thumbnail_html(content, brief, thumb_path)

    elif channel == "newsletter":
        filepath = output_dir / f"newsletter_{slug}_{timestamp}.json"
        filepath.write_text(json.dumps(content, indent=2), encoding="utf-8")
        # Styled HTML for Beehiiv
        _generate_newsletter_html(content, brief, output_dir / f"newsletter_{slug}_{timestamp}.html")
        # Subject + preview text
        (output_dir / f"newsletter_{slug}_{timestamp}_subject.txt").write_text(
            f"SUBJECT A:\n{content.get('subject_a', '')}\n\nSUBJECT B (recommended):\n{content.get('subject_b', '')}\n\nPREVIEW TEXT:\n{content.get('preview_text', '')}\n",
            encoding="utf-8"
        )

    elif channel == "twitter_thread":
        filepath = output_dir / f"twitter_thread_{slug}_{timestamp}.json"
        filepath.write_text(json.dumps(content, indent=2), encoding="utf-8")
        tweets = content.get("tweets", [])
        txt_content = ""  # Typefully-ready format
        over_limit = []
        for i, tweet in enumerate(tweets, 1):
            txt_content += tweet + "\n\n---\n\n"
            if len(tweet) > 280:
                over_limit.append((i, len(tweet)))
        (output_dir / f"twitter_thread_{slug}_{timestamp}.txt").write_text(txt_content.strip(), encoding="utf-8")
        if over_limit:
            w = "TWEETS OVER 280 CHARACTERS:\n\n"
            for num, length in over_limit:
                w += f"Tweet {num}: {length} chars ({length - 280} over)\n{tweets[num-1]}\n\n"
            (output_dir / f"twitter_thread_{slug}_{timestamp}_WARNINGS.txt").write_text(w, encoding="utf-8")
        _generate_benchmark_html(content, brief, output_dir / f"twitter_graphic_{slug}_{timestamp}.html")

    elif channel == "instagram":
        filepath = output_dir / f"instagram_{slug}_{timestamp}.json"
        filepath.write_text(json.dumps(content, indent=2), encoding="utf-8")
        # Clean caption txt
        caption_txt = content.get('caption', '') + '\n\n' + ' '.join(content.get('hashtags', [])) + '\n'
        (output_dir / f"instagram_{slug}_{timestamp}_caption.txt").write_text(caption_txt, encoding="utf-8")
        # Carousel HTML
        _generate_instagram_carousel_html(content, brief, output_dir / f"instagram_carousel_{slug}_{timestamp}.html")

    else:
        filepath = output_dir / f"{channel}_{slug}_{timestamp}.json"
        filepath.write_text(json.dumps(content, indent=2), encoding="utf-8")

    return filepath


def display_content(channel: str, content: dict):
    console.print(f"\n[bold cyan]━━━ {channel.upper().replace('_', ' ')} ━━━[/bold cyan]")
    if channel == "blog" and "content" in content:
        console.print(f"[bold]Title:[/bold] {content.get('title', 'N/A')}")
        console.print(f"[bold]Meta:[/bold] {content.get('meta_description', 'N/A')}")
        console.print(f"[dim](Full content + thumbnail.html saved)[/dim]")
    elif channel == "newsletter":
        console.print(f"[bold]Subject A:[/bold] {content.get('subject_a', 'N/A')}")
        console.print(f"[bold]Subject B:[/bold] {content.get('subject_b', 'N/A')}")
        console.print(f"[bold]Preview:[/bold] {content.get('preview_text', 'N/A')}")
        console.print(f"[bold]PS:[/bold] {content.get('ps_line', 'N/A')}")
        console.print(f"[dim](newsletter.html + _subject.txt saved)[/dim]")
    elif channel == "instagram":
        console.print(f"[bold]Caption:[/bold]\n{content.get('caption', 'N/A')}")
        console.print(f"[bold]Hashtags:[/bold] {' '.join(content.get('hashtags', []))}")
        console.print(f"[dim](carousel HTML + caption.txt saved)[/dim]")
    elif channel == "pinterest":
        console.print(f"[bold]Pin Title:[/bold] {content.get('pin_title', 'N/A')}")
        console.print(f"[bold]Description:[/bold] {content.get('pin_description', 'N/A')}")
        console.print(f"[bold]Board:[/bold] {content.get('board_suggestion', 'N/A')}")
    elif channel == "twitter_thread":
        tweets = content.get("tweets", [])
        for i, tweet in enumerate(tweets, 1):
            flag = " [red]OVER 280[/red]" if len(tweet) > 280 else ""
            console.print(f"[bold]Tweet {i} ({len(tweet)} chars):[/bold]{flag} {tweet}")
    elif channel == "ad_copy":
        meta_ads = content.get("meta_ads", [])
        if meta_ads:
            ad = meta_ads[0]
            console.print(f"[bold]Meta Ad #1:[/bold] {ad.get('primary_text', 'N/A')}")
    elif "raw" in content:
        raw = content.get("raw", "")
        console.print(raw[:500] + "..." if len(raw) > 500 else raw)


CHANNELS = ["blog", "newsletter", "instagram", "pinterest", "twitter_thread", "ad_copy"]


def main():
    parser = argparse.ArgumentParser(description="Affiliate Content Engine")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--affiliate", required=True)
    parser.add_argument("--affiliate-url", default="https://example.com/?ref=YOUR_ID")
    parser.add_argument("--commission", default="recurring commission")
    parser.add_argument("--audience", default="developers and technical professionals")
    parser.add_argument("--channels", nargs="+", choices=CHANNELS, default=CHANNELS)
    parser.add_argument("--output-dir", default="./output")
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

    console.print(Panel.fit(
        f"[bold green]Affiliate Content Engine[/bold green]\n"
        f"Topic: [cyan]{args.topic}[/cyan]\n"
        f"Affiliate: [yellow]{args.affiliate}[/yellow]\n"
        f"Channels: [magenta]{', '.join(args.channels)}[/magenta]",
        title=">> Content Generation"
    ))

    results = {}
    saved_files = []

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        for channel in args.channels:
            task = progress.add_task(f"Generating {channel.replace('_', ' ')}...", total=None)
            try:
                content = generate_content(channel, brief)
                results[channel] = content
                filepath = save_output(channel, content, output_dir, brief)
                saved_files.append((channel, filepath))
                progress.update(task, description=f"[green]OK[/green] {channel.replace('_', ' ')}")
            except Exception as e:
                progress.update(task, description=f"[red]XX[/red] {channel}: {e}")
                results[channel] = {"error": str(e)}
            progress.stop_task(task)

    for channel, content in results.items():
        if "error" not in content:
            display_content(channel, content)

    console.print("\n")
    table = Table(title="Saved Files", show_header=True, header_style="bold magenta")
    table.add_column("Channel", style="cyan")
    table.add_column("File", style="green")
    for channel, filepath in saved_files:
        table.add_row(channel.replace("_", " ").title(), str(filepath))
    console.print(table)
    console.print(f"\n[bold green]Done! All content saved to {output_dir}/[/bold green]")


if __name__ == "__main__":
    main()
