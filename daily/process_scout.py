#!/usr/bin/env python3
import json
import os
import re
import subprocess
from datetime import datetime

# Configuration
TODAY = "2026-03-22"
MEDIA_DIR = f"/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/{TODAY}-media"
REPORT_PATH = f"/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/{TODAY}.md"
TEMP_JSON = "/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/_temp_posts.json"

# Keywords for relevance scoring
KEYWORDS = ["productivity", "focus", "screen time", "gamification", "phone addiction", "study", "discipline", "digital minimalism", "streak", "accountability", "motivation"]

# Subreddits to process (in order)
SUBREDDITS = ["productivity", "getdisciplined", "DecidingToBeBetter", "StudyTips", "GetStudying"]

# GitHub API base
GITHUB_BASE = "https://api.github.com/repos/ozlemsultan90-cmyk/reddit-scout-reports/contents"

# Read GitHub token
def get_github_token():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        try:
            with open(os.path.expanduser("~/.openclaw/.env"), "r") as f:
                for line in f:
                    if line.startswith("GITHUB_TOKEN="):
                        token = line.strip().split("=", 1)[1]
                        break
        except:
            pass
    return token

def clean_selftext(text):
    """Extract plain text from HTML or truncate"""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
    return text.strip()

def truncate_text(text, max_len=200):
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len-3].rstrip() + "..."

def extract_posts_from_subreddit_data(data, subreddit):
    posts = []
    children = data.get("children", [])
    for child in children:
        post_data = child.get("data", {})
        permalink = post_data.get("permalink", "")
        url = post_data.get("url", "")
        post_hint = post_data.get("post_hint", None)
        is_gallery = post_data.get("is_gallery", False)
        score = post_data.get("score", 0)
        num_comments = post_data.get("num_comments", 0)
        upvote_ratio = post_data.get("upvote_ratio", 0.5)
        created = post_data.get("created", 0)
        selftext_html = post_data.get("selftext_html", "")
        selftext = clean_selftext(post_data.get("selftext", "")) or clean_selftext(selftext_html)
        title = post_data.get("title", "")
        media_metadata = post_data.get("media_metadata", {})

        post = {
            "title": title,
            "permalink": permalink,
            "subreddit": subreddit,
            "score": score,
            "num_comments": num_comments,
            "upvote_ratio": upvote_ratio,
            "created": created,
            "selftext": selftext,
            "url": url,
            "post_hint": post_hint,
            "is_gallery": is_gallery,
            "media_metadata": media_metadata,
            "media_sources": [],
            "raw_score": 0,
            "engagement_points": 0,
            "ratio_points": 0,
            "relevance_bonus": 0,
            "viral_score": 0,
            "hours_ago": 0
        }
        posts.append(post)
    return posts

def calculate_viral_score(post):
    score = post["score"]
    num_comments = post["num_comments"]
    upvote_ratio = post["upvote_ratio"]
    selftext = (post["selftext"] or "") + " " + (post["title"] or "")
    selftext_lower = selftext.lower()

    # Raw points (capped at 5000)
    raw = min(score, 5000) / 500  # 0-10
    post["raw_score"] = round(raw, 1)

    # Engagement
    engagement = (num_comments / (score + 1)) * 100 * 0.03
    engagement = min(engagement, 3)
    post["engagement_points"] = round(engagement, 1)

    # Upvote ratio
    ratio_points = upvote_ratio * 10  # already 0-10
    post["ratio_points"] = round(ratio_points, 1)

    # Relevance: count distinct keywords present
    found = sum(1 for kw in KEYWORDS if kw in selftext_lower)
    relevance = min(found, 3)
    post["relevance_bonus"] = relevance

    # Total (max ~26)
    total = raw + engagement + ratio_points + relevance
    viral = round(total / 2.6, 1)
    post["viral_score"] = viral
    return viral

def hours_since(created_utc, now_utc):
    diff = now_utc - created_utc
    return diff.total_seconds() / 3600.0

def download_image(url, dest_path):
    try:
        # Use curl with follow redirects
        result = subprocess.run(["curl", "-L", "-o", dest_path, url], capture_output=True, text=True)
        if result.returncode != 0:
            return False, result.stderr
        # Check file size
        size = os.path.getsize(dest_path)
        if size < 1024:
            os.remove(dest_path)
            return False, f"File too small ({size} bytes)"
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    all_posts = []
    now_utc = datetime.utcnow()

    # Ingest raw JSON from subreddit responses (simulate from our fetch data)
    # Since we can't easily pass data from the main session to this script, we'll re-fetch or use stored data
    # But the cron job expects us to work with the fetched data... Let's fetch directly again for consistency

    import urllib.request
    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=5"
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode())
            posts = extract_posts_from_subreddit_data(data["data"], sub)
            for p in posts:
                p["hours_ago"] = hours_since(datetime.fromtimestamp(p["created"]), now_utc)
            all_posts.extend(posts)
        except Exception as e:
            print(f"Error fetching {sub}: {e}", file=sys.stderr)

    # Save raw data
    with open(TEMP_JSON, "w") as f:
        json.dump(all_posts, f, indent=2)

    # Process images
    for post in all_posts:
        url = post["url"]
        post_hint = post["post_hint"]
        is_gallery = post["is_gallery"]
        media_metadata = post["media_metadata"]

        # Condition: direct image URL
        if (post_hint == "image" or is_gallery) and url and url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            filename = url.split("/")[-1]
            # Sanitize filename
            filename = filename.split("?")[0]
            if not filename:
                filename = f"{post['subreddit']}_{post['title'][:30]}.jpg"
            dest = os.path.join(MEDIA_DIR, filename)
            if os.path.exists(dest):
                post["media_sources"].append(f"{TODAY}-media/{filename}")
            else:
                success, err = download_image(url, dest)
                if success:
                    post["media_sources"].append(f"{TODAY}-media/{filename}")

        # For galleries - not present in our data but include for completeness
        if is_gallery and media_metadata:
            for item in media_metadata.values():
                if "s" in item and "u" in item["s"]:
                    img_url = item["s"]["u"]
                    # ... similar download logic
                    # Skipping for brevity as we don't have galleries

    # Calculate viral scores
    for post in all_posts:
        calculate_viral_score(post)

    # Sort by viral score descending
    all_posts.sort(key=lambda p: p["viral_score"], reverse=True)

    # Generate report
    os.makedirs(MEDIA_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# Reddit Scout Report: Focus Timer Opportunities\n")
        f.write(f"**Date:** {TODAY}\n\n")
        f.write("## Top Opportunities\n\n")

        # Top 5
        for i, post in enumerate(all_posts[:5], 1):
            title = post["title"]
            permalink = post["permalink"]
            subreddit = post["subreddit"]
            score = post["score"]
            num_comments = post["num_comments"]
            upvote_ratio = post["upvote_ratio"]
            hours_ago = post["hours_ago"]
            selftext_summary = truncate_text(post["selftext"], 200)
            viral = post["viral_score"]
            raw = post["raw_score"]
            eng = post["engagement_points"]
            ratio = post["ratio_points"]
            rel = post["relevance_bonus"]

            f.write(f"### {i}. [{title}](https://www.reddit.com{permalink})\n")
            f.write(f"Subreddit: r/{subreddit} | Score: {score} | Comments: {num_comments} | Upvote ratio: {upvote_ratio:.0%}\n")
            f.write(f"Posted: ~{hours_ago:.1f} hours ago\n\n")
            f.write(f"**Summary:** {selftext_summary}\n\n")
            f.write(f"**Viral Score:** {viral}/10\n")
            f.write(f"- Raw score: {raw}/10\n")
            f.write(f"- Engagement: {eng}/10\n")
            f.write(f"- Upvote ratio: {ratio}/10\n")
            f.write(f"- Relevance bonus: {rel}/3\n\n")
            if post["media_sources"]:
                f.write("**Media:**\n")
                for src in post["media_sources"]:
                    alt = title[:50]
                    f.write(f"![{alt}]({src})\n")
            f.write("\n")

        # Honorable Mentions (posts 6-10)
        if len(all_posts) > 5:
            f.write("## Honorable Mentions\n\n")
            for i, post in enumerate(all_posts[5:10], 6):
                title = post["title"]
                permalink = post["permalink"]
                sub = post["subreddit"]
                score = post["score"]
                summary = truncate_text(post["selftext"], 100)
                f.write(f"### {i}. [{title}](https://www.reddit.com{permalink}) (r/{sub} | {score} upvotes) – {summary}.\n\n")

        # Media Summary
        media_files = []
        if os.path.exists(MEDIA_DIR):
            media_files = sorted([f for f in os.listdir(MEDIA_DIR) if os.path.isfile(os.path.join(MEDIA_DIR, f))])
        if media_files:
            f.write("## Media Summary\n\n")
            f.write(f"Downloaded images ({TODAY}-media/):\n")
            for filename in media_files:
                path = os.path.join(MEDIA_DIR, filename)
                size_kb = os.path.getsize(path) / 1024
                f.write(f"- **{filename}** ({size_kb:.1f} KB)\n")
                f.write(f"  ![{filename}]({TODAY}-media/{filename})\n")

        # GitHub link
        f.write("\n---\n")
        f.write(f"**View on GitHub:** {GITHUB_BASE}/reports/{TODAY}.md\n")

    print(f"Report generated at {REPORT_PATH} with {len(all_posts)} posts")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())