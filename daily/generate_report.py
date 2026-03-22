#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime
import subprocess
import base64

TODAY = "2026-03-16"
WORKSPACE = "/Users/ozlemsultan/.openclaw/workspace/reddit-productivity"
DAILY_DIR = os.path.join(WORKSPACE, "daily")
MEDIA_DIR = os.path.join(DAILY_DIR, f"{TODAY}-media")
TEMP_JSON = os.path.join(DAILY_DIR, "_temp_posts.json")
REPORT_MD = os.path.join(DAILY_DIR, f"{TODAY}.md")

# Create media directory
os.makedirs(MEDIA_DIR, exist_ok=True)

# Keywords for relevance
KEYWORDS = ["productivity", "focus", "screen time", "gamification", "phone addiction", "study", "discipline", "digital minimalism", "streak", "accountability", "motivation"]

# Image extensions
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

# Load raw data from the 5 subreddit fetches (simulate reading from memory)
# Since we can't re-fetch easily, I'll reconstruct from the fetches we already did.
# But we need the actual JSON content. We'll read from stored fetches if available, but better to refetch.
# For this script, we'll expect a combined JSON file or refetch.
# Since I'm the agent, I'll re-fetch the subreddits to get clean data.

SUBREDDITS = ["productivity", "getdisciplined", "DecidingToBeBetter", "StudyTips", "GetStudying"]
posts = []

def fetch_subreddit(sub):
    url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=5"
    # Use curl to fetch with a User-Agent
    result = subprocess.run(["curl", "-s", "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", url], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error fetching {sub}: {result.stderr}", file=sys.stderr)
        return None
    try:
        data = json.loads(result.stdout)
        return data.get("data", {}).get("children", [])
    except Exception as e:
        print(f"Error parsing {sub}: {e}", file=sys.stderr)
        print(f"Response sample: {result.stdout[:200]}", file=sys.stderr)
        return None

def download_image(url, dest):
    # Use curl -L to follow redirects
    result = subprocess.run(["curl", "-L", "-o", dest, url], capture_output=True)
    if result.returncode != 0:
        print(f"Download failed: {url} -> {dest}", file=sys.stderr)
        return False
    # Verify > 1024 bytes
    if os.path.getsize(dest) > 1024:
        return True
    else:
        print(f"File too small: {dest}", file=sys.stderr)
        os.remove(dest)
        return False

def calculate_viral_score(post):
    score = post.get("score", 0)
    num_comments = post.get("num_comments", 0)
    upvote_ratio = post.get("upvote_ratio", 0)
    title = post.get("title", "")
    selftext = post.get("selftext", "")
    
    # Raw score
    raw_points = min(score, 5000) / 500
    
    # Engagement
    engagement_points = min((num_comments / (score + 1)) * 100 * 0.03, 3)
    
    # Upvote ratio
    ratio_points = upvote_ratio * 10
    
    # Relevance bonus
    text_lower = (title + " " + selftext).lower()
    found_keywords = set()
    for kw in KEYWORDS:
        if kw in text_lower:
            found_keywords.add(kw)
    relevance_bonus = min(len(found_keywords), 3)
    
    total = raw_points + engagement_points + ratio_points + relevance_bonus
    viral_score = round(total / 2.6, 1)
    
    return {
        "viral_score": viral_score,
        "raw_points": round(raw_points, 1),
        "engagement_points": round(engagement_points, 1),
        "ratio_points": round(ratio_points, 1),
        "relevance_bonus": relevance_bonus
    }

# Main processing
all_posts = []

for sub in SUBREDDITS:
    children = fetch_subreddit(sub)
    if not children:
        continue
    for child in children:
        data = child["data"]
        # Extract fields
        post = {
            "title": data.get("title"),
            "permalink": data.get("permalink"),
            "subreddit": data.get("subreddit"),
            "score": data.get("score", 0),
            "num_comments": data.get("num_comments", 0),
            "upvote_ratio": data.get("upvote_ratio", 0),
            "created": data.get("created", 0),
            "selftext": data.get("selftext", "")[:200],
            "url": data.get("url", ""),
            "post_hint": data.get("post_hint"),
            "is_gallery": data.get("is_gallery", False),
            "media_metadata": data.get("media_metadata"),
            "media_sources": []
        }
        # Check for images and download if present
        downloaded_any = False
        
        # Case 1: is_gallery
        if post["is_gallery"] and post["media_metadata"]:
            # gallery_data contains items with media_id
            gallery_items = data.get("gallery_data", {}).get("items", [])
            for item in gallery_items:
                media_id = item["media_id"]
                meta = post["media_metadata"].get(media_id)
                if meta:
                    # Get the full resolution URL from 's' or largest 'p'
                    img_url = None
                    if "s" in meta:
                        img_url = meta["s"]["u"]
                    elif "p" in meta and meta["p"]:
                        # Find the largest resolution
                        largest = max(meta["p"], key=lambda x: x.get("x", 0))
                        img_url = largest["u"]
                    if img_url:
                        # Convert URL to direct image if needed (preview.redd.it -> i.redd.it)
                        img_url = img_url.replace("preview.redd.it", "i.redd.it")
                        # Extract filename
                        filename = img_url.split("/")[-1].split("?")[0]
                        dest = os.path.join(MEDIA_DIR, filename)
                        if download_image(img_url, dest):
                            rel_path = f"{TODAY}-media/{filename}"
                            post["media_sources"].append(rel_path)
                            downloaded_any = True
        # Case 2: post_hint image or direct image URL
        elif (post["post_hint"] == "image" or post["url"].endswith(IMAGE_EXTS)) and post["url"]:
            img_url = post["url"]
            # If it's a preview.redd.it link, convert to i.redd.it for full image?
            # Usually the url is already direct. For gallery, we already handled.
            filename = img_url.split("/")[-1].split("?")[0]
            # Ensure it has image extension
            if not filename.lower().endswith(IMAGE_EXTS):
                # Try to get from content-type? Skip for simplicity
                filename = f"{post['id']}.jpg" if 'id' in data else "image.jpg"
            dest = os.path.join(MEDIA_DIR, filename)
            if download_image(img_url, dest):
                rel_path = f"{TODAY}-media/{filename}"
                post["media_sources"].append(rel_path)
                downloaded_any = True
        
        # Compute viral score
        vs_data = calculate_viral_score(post)
        post["viral_score"] = vs_data["viral_score"]
        post["raw_points"] = vs_data["raw_points"]
        post["engagement_points"] = vs_data["engagement_points"]
        post["ratio_points"] = vs_data["ratio_points"]
        post["relevance_bonus"] = vs_data["relevance_bonus"]
        
        all_posts.append(post)

# Save raw data
with open(TEMP_JSON, "w") as f:
    json.dump(all_posts, f, indent=2)

# Sort by viral score descending
all_posts.sort(key=lambda x: x["viral_score"], reverse=True)

# Generate report
lines = []
lines.append(f"# Reddit Scout Report: Focus Timer Opportunities")
lines.append(f"**Date:** {TODAY}")
lines.append("")
lines.append("## Top Opportunities")
lines.append("")

for i, post in enumerate(all_posts[:5], 1):
    title = post["title"]
    permalink = post["permalink"]
    subreddit = post["subreddit"]
    score = post["score"]
    num_comments = post["num_comments"]
    upvote_ratio = post["upvote_ratio"]
    created_ts = post["created"]
    # Calculate hours ago from created timestamp relative to current time
    # Current time is 2026-03-16 17:00 UTC (from the cron)
    now_ts = datetime(2026, 3, 16, 17, 0).timestamp()
    hours_ago = (now_ts - created_ts) / 3600 if created_ts else 0
    hours_ago = int(hours_ago)
    
    selftext = post["selftext"]
    if len(selftext) > 200:
        selftext = selftext[:200] + "..."
    
    viral_score = post["viral_score"]
    raw_points = post["raw_points"]
    engagement_points = post["engagement_points"]
    ratio_points = post["ratio_points"]
    relevance_bonus = post["relevance_bonus"]
    
    lines.append(f"### {i}. [{title}](https://www.reddit.com{permalink})")
    lines.append(f"Subreddit: r/{subreddit} | Score: {score} | Comments: {num_comments} | Upvote ratio: {upvote_ratio:.0%}")
    lines.append(f"Posted: ~{hours_ago} hours ago")
    lines.append("")
    lines.append("**Summary:**")
    # Convert selftext to plain summary (2-3 sentences)
    # Just use first 200 chars
    lines.append(selftext if selftext else "*No selftext*")
    lines.append("")
    lines.append(f"**Viral Score:** {viral_score:.1f}/10")
    lines.append(f"- Raw score: {raw_points:.1f}/10")
    lines.append(f"- Engagement: {engagement_points:.1f}/10")
    lines.append(f"- Upvote ratio: {ratio_points:.1f}/10")
    lines.append(f"- Relevance bonus: {relevance_bonus}/3")
    
    if post["media_sources"]:
        lines.append("")
        lines.append("**Media:**")
        for src in post["media_sources"]:
            lines.append(f"![Image]({src})")
    lines.append("")

# Honorable Mentions (posts 6-10)
if len(all_posts) >= 6:
    lines.append("## Honorable Mentions")
    lines.append("")
    for i, post in enumerate(all_posts[5:10], 6):
        title = post["title"]
        permalink = post["permalink"]
        subreddit = post["subreddit"]
        score = post["score"]
        selftext = post["selftext"][:100] if post["selftext"] else ""
        lines.append(f"### {i}. [{title}](https://www.reddit.com{permalink}) (r/{subreddit} | {score} upvotes) – {selftext}.")

# Media Summary
lines.append("## Media Summary")
lines.append(f"Downloaded images ({TODAY}-media/):")
# List files in media dir
if os.path.exists(MEDIA_DIR):
    for fname in sorted(os.listdir(MEDIA_DIR)):
        fpath = os.path.join(MEDIA_DIR, fname)
        if os.path.isfile(fpath):
            size_kb = os.path.getsize(fpath) // 1024
            lines.append(f"- **{fname}** ({size_kb} KB)")
            lines.append(f"  ![{fname}]({TODAY}-media/{fname})")
else:
    lines.append("*No media downloaded*")

# GitHub link
lines.append("---")
lines.append(f"**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/{TODAY}.md")

# Write report
with open(REPORT_MD, "w") as f:
    f.write("\n".join(lines))

print(f"Report generated: {REPORT_MD}")
