#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime

# Today's date
TODAY = "2026-03-01"
BASE_DIR = "/Users/ozlemsultan/.openclaw/workspace/reddit-productivity"
MEDIA_DIR = f"{BASE_DIR}/daily/{TODAY}-media"
REPORT_PATH = f"{BASE_DIR}/daily/{TODAY}.md"
TEMP_JSON = f"{BASE_DIR}/daily/_temp_posts.json"

# Subreddits to fetch (first 5)
subreddits = [
    "productivity",
    "getdisciplined",
    "DecidingToBeBetter",
    "StudyTips",
    "GetStudying"
]

# Read raw responses (from files we'd have saved or direct strings)
# Since we have the data in memory from web_fetch, we'll simulate by processing the JSON directly
# In a real scenario, we'd have saved the responses. Let's create the data from what we fetched.

# Instead, I'll parse the JSON strings from the responses we got
# We'll need to extract the JSON from each response. The response has the JSON as text outside the security wrapper

# For this script, I'll simulate having the data. We'll construct posts manually from the fetched data
posts = []

# Keywords for relevance
KEYWORDS = ['productivity', 'focus', 'screen time', 'gamification', 'phone addiction', 'study', 'discipline', 'digital minimalism', 'streak', 'accountability', 'motivation']

def count_relevance(text):
    text_lower = text.lower()
    found = set()
    for kw in KEYWORDS:
        if kw in text_lower:
            found.add(kw)
    return len(found)

def calculate_viral_score(post):
    score = post.get('score', 0)
    num_comments = post.get('num_comments', 0)
    upvote_ratio = post.get('upvote_ratio', 0)
    title = post.get('title', '')
    selftext = post.get('selftext', '')

    # Raw points
    raw_points = min(score, 5000) / 500

    # Engagement points
    engagement_points = (num_comments / (score + 1)) * 100 * 0.03
    if engagement_points > 3:
        engagement_points = 3

    # Upvote ratio points
    ratio_points = upvote_ratio * 10

    # Relevance bonus
    relevance_bonus = count_relevance(title + " " + selftext)
    if relevance_bonus > 3:
        relevance_bonus = 3

    total = raw_points + engagement_points + ratio_points + relevance_bonus
    viral_score = round(total / 2.6, 1)
    return raw_points, engagement_points, ratio_points, relevance_bonus, viral_score

def truncate_text(text, limit=200):
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."

def hours_ago(created_utc):
    # created_utc is timestamp
    now = datetime.now()
    post_time = datetime.fromtimestamp(created_utc)
    diff = now - post_time
    hours = diff.total_seconds() / 3600
    return round(hours)

def process_post_data():
    # We'll manually construct posts based on the fetched JSON we have
    # Since this is a script that runs after we fetched, we need to have the data
    # For now, I'll assume we parse from the responses that were fetched
    # But I'll actually just create the posts array by directly parsing the JSON content from the fetched files

    # Let's read the temp file if exists, otherwise we need to create it
    if os.path.exists(TEMP_JSON):
        with open(TEMP_JSON, 'r') as f:
            data = json.load(f)
            posts.extend(data)
    else:
        print("Temp JSON not found. Should have been created earlier.", file=sys.stderr)
        sys.exit(1)

    # Now we have all posts. Sort by viral_score descending
    for post in posts:
        raw, eng, ratio, rel, viral = calculate_viral_score(post)
        post['raw_points'] = raw
        post['engagement_points'] = eng
        post['ratio_points'] = ratio
        post['relevance_bonus'] = rel
        post['viral_score'] = viral

    posts.sort(key=lambda x: x['viral_score'], reverse=True)

    # Top 5
    top5 = posts[:5]
    # Honorable mentions: posts 6-10
    mentions = posts[5:10]

    # Generate report content
    lines = []
    lines.append(f"# Reddit Scout Report: Focus Timer Opportunities")
    lines.append(f"**Date:** {TODAY}")
    lines.append("")
    lines.append("## Top Opportunities")
    lines.append("")

    for i, post in enumerate(top5, 1):
        title = post['title']
        permalink = post['permalink']
        subreddit = post['subreddit']
        score = post['score']
        num_comments = post['num_comments']
        upvote_ratio = post['upvote_ratio']
        created = post['created']
        selftext = truncate_text(post.get('selftext', ''), 200)
        media_sources = post.get('media_sources', [])

        # Format summary
        # Convert selftext to plain text (strip markdown/HTML). It's plain text already.
        summary = selftext if selftext else "No text content."

        hours = hours_ago(created)

        lines.append(f"### {i}. [{title}](https://www.reddit.com{permalink})")
        lines.append(f"Subreddit: r/{subreddit} | Score: {score} | Comments: {num_comments} | Upvote ratio: {upvote_ratio:.0%}")
        lines.append(f"Posted: ~{hours} hours ago")
        lines.append("")
        lines.append("**Summary:** " + summary)
        lines.append("")
        lines.append(f"**Viral Score:** {post['viral_score']:.1f}/10")
        lines.append(f"- Raw score: {post['raw_points']:.1f}/10")
        lines.append(f"- Engagement: {post['engagement_points']:.1f}/10")
        lines.append(f"- Upvote ratio: {post['ratio_points']:.1f}/10")
        lines.append(f"- Relevance bonus: {post['relevance_bonus']}/3")
        lines.append("")
        if media_sources:
            lines.append("**Media:**")
            for media_path in media_sources:
                # alt text from filename
                filename = os.path.basename(media_path)
                lines.append(f"![{filename}]({media_path})")
        else:
            lines.append("**Media:** No images")
        lines.append("")

    lines.append("## Honorable Mentions")
    lines.append("")
    for i, post in enumerate(mentions, 6):
        title = post['title']
        permalink = post['permalink']
        subreddit = post['subreddit']
        score = post['score']
        selftext = post.get('selftext', '')
        summary = truncate_text(selftext, 100) if selftext else "No text."
        lines.append(f"### {i}. [{title}](https://www.reddit.com{permalink}) (r/{subreddit} | {score} upvotes) – {summary}.")
    lines.append("")

    # Media Summary
    lines.append("## Media Summary")
    lines.append(f"Downloaded images ({TODAY}-media/):")
    if os.path.exists(MEDIA_DIR):
        files = os.listdir(MEDIA_DIR)
        if files:
            for fname in files:
                fpath = os.path.join(MEDIA_DIR, fname)
                size_kb = os.path.getsize(fpath) // 1024
                lines.append(f"- **{fname}** ({size_kb} KB)")
                # embed the image (relative path)
                lines.append(f"  ![Description]({TODAY}-media/{fname})")
        else:
            lines.append("No media files downloaded.")
    else:
        lines.append("Media directory not found.")

    lines.append("")
    lines.append("---")
    lines.append(f"**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/{TODAY}.md")

    # Write report
    with open(REPORT_PATH, 'w') as f:
        f.write("\n".join(lines))

    print(f"Report written to {REPORT_PATH}")

if __name__ == "__main__":
    process_post_data()
