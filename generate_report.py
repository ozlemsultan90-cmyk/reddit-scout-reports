#!/usr/bin/env python3
import json
import os
from datetime import datetime

TODAY = "2026-03-02"
OUTPUT_DIR = "/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily"
RAW_JSON = os.path.join(OUTPUT_DIR, "_temp_posts.json")
REPORT_FILE = os.path.join(OUTPUT_DIR, f"{TODAY}.md")
MEDIA_DIR = f"{TODAY}-media"

KEYWORDS = ["productivity", "focus", "screen time", "gamification", "phone addiction", "study", "discipline", "digital minimalism", "streak", "accountability", "motivation"]

def calculate_viral_score(post):
    score = post.get('score', 0)
    num_comments = post.get('num_comments', 0)
    upvote_ratio = post.get('upvote_ratio', 1.0)
    text = (post.get('title','') + " " + post.get('selftext','')).lower()

    # Raw points (0-10)
    raw_points = min(score, 5000) / 500

    # Engagement points (cap 3, later scaled)
    engagement_raw = (num_comments / (score + 1)) * 100 * 0.03
    engagement_points = min(engagement_raw, 3)

    # Upvote ratio points (max 10)
    ratio_points = upvote_ratio * 10

    # Relevance bonus (max 3)
    found_keywords = set()
    for kw in KEYWORDS:
        if kw in text:
            found_keywords.add(kw)
    relevance_bonus = min(len(found_keywords), 3)

    total = raw_points + engagement_points + ratio_points + relevance_bonus
    viral_score = round(total / 2.6, 1)
    return {
        'viral_score': viral_score,
        'raw_points': raw_points,
        'engagement_points': engagement_points,
        'ratio_points': ratio_points,
        'relevance_bonus': relevance_bonus
    }

# Load posts
with open(RAW_JSON, 'r') as f:
    posts = json.load(f)

# Compute scores
for post in posts:
    scores = calculate_viral_score(post)
    post.update(scores)

# Sort by viral_score descending
posts.sort(key=lambda x: x['viral_score'], reverse=True)

# Write report
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    f.write(f"# Reddit Scout Report: Focus Timer Opportunities\n")
    f.write(f"**Date:** {TODAY}\n\n")

    f.write("## Top Opportunities\n\n")

    # Top 5
    for idx, post in enumerate(posts[:5], 1):
        hours_ago = round((datetime.now().timestamp() - post['created']) / 3600, 1)
        f.write(f"### {idx}. [{post['title']}](https://www.reddit.com{post['permalink']})\n")
        f.write(f"Subreddit: r/{post['subreddit']} | Score: {post['score']} | Comments: {post['num_comments']} | Upvote ratio: {post['upvote_ratio']:.0%}\n")
        f.write(f"Posted: ~{hours_ago} hours ago\n\n")
        summary = post['selftext'].strip()
        if not summary:
            summary = "(No text content)"
        # Make 2-3 sentences summary - just use first 200 chars as per instructions
        f.write(f"**Summary:** {summary}\n\n")
        f.write(f"**Viral Score:** {post['viral_score']:.1f}/10\n")
        f.write(f"- Raw score: {post['raw_points']:.1f}/10\n")
        f.write(f"- Engagement: {post['engagement_points']:.1f}/10\n")
        f.write(f"- Upvote ratio: {post['ratio_points']:.1f}/10\n")
        f.write(f"- Relevance bonus: {post['relevance_bonus']}/3\nn")
        f.write("**Media:**\n")
        if post['media_sources']:
            for src in post['media_sources']:
                # Use alt text based on filename
                alt = f"Image from r/{post['subreddit']}"
                f.write(f"![{alt}]({src})\n")
        else:
            f.write("(No media)\n")
        f.write("\n")

    # Honorable Mentions (6-10)
    f.write("## Honorable Mentions\n\n")
    for idx, post in enumerate(posts[5:10], 6):
        summary = post['selftext'].strip()[:100]
        if not summary:
            summary = "(No text content)"
        f.write(f"### {idx}. [{post['title']}](https://www.reddit.com{post['permalink']}) (r/{post['subreddit']} | {post['score']} upvotes) – {summary}.\n")

    # Media Summary
    f.write("\n## Media Summary\n")
    f.write(f"Downloaded images ({TODAY}-media/):\n")
    # List files in media directory with sizes
    try:
        files = os.listdir(os.path.join(OUTPUT_DIR, TODAY + "-media"))
        for file in sorted(files):
            filepath = os.path.join(OUTPUT_DIR, TODAY + "-media", file)
            size_kb = round(os.path.getsize(filepath) / 1024, 1)
            alt = f"Image from r/{TODAY}"
            f.write(f"- **{file}** ({size_kb} KB)\n")
            f.write(f"  ![Description]({TODAY}-media/{file})\n")
    except Exception as e:
        f.write(f"(Error listing media: {e})\n")

    # GitHub link at the very end
    f.write("\n---\n")
    f.write(f"**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/{TODAY}.md\n")

print(f"Report written to {REPORT_FILE}")
