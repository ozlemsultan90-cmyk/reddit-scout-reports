#!/usr/bin/env python3
import json
import os
import re
import requests
import base64
from datetime import datetime

# Date
TODAY = "2026-03-17"
MEDIA_DIR = f"/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/{TODAY}-media"
BASE_URL = "https://api.github.com/repos/ozlemsultan90-cmyk/reddit-scout-reports/contents"

# Keywords for relevance
KEYWORDS = {"productivity", "focus", "screen time", "gamification", "phone addiction", "study", "discipline", "digital minimalism", "streak", "accountability", "motivation"}

# Load all JSON data
def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

data_productivity = load_json("data_productivity.json")
data_getdisciplined = load_json("data_getdisciplined.json")
data_deciding = load_json("data_deciding.json")
data_studytips = load_json("data_studytips.json")
data_getstudying = load_json("data_getstudying.json")

all_posts = []

def extract_posts(data, subreddit_name):
    posts = []
    for child in data.get("data", {}).get("children", []):
        p = child["data"]
        title = p.get("title", "")
        permalink = p.get("permalink", "")
        score = p.get("score", 0)
        num_comments = p.get("num_comments", 0)
        upvote_ratio = p.get("upvote_ratio", 0)
        created = p.get("created_utc", 0)
        selftext = p.get("selftext", "")
        if selftext:
            selftext = re.sub(r'<[^>]+>', '', selftext)
            selftext_summary = selftext[:200].strip()
        else:
            selftext_summary = ""
        url = p.get("url", "")
        post_hint = p.get("post_hint", "")
        is_gallery = p.get("is_gallery", False)
        media_metadata = p.get("media_metadata", {})

        post = {
            "title": title,
            "permalink": permalink,
            "subreddit": subreddit_name,
            "score": score,
            "num_comments": num_comments,
            "upvote_ratio": upvote_ratio,
            "created": created,
            "selftext": selftext_summary,
            "url": url,
            "post_hint": post_hint,
            "is_gallery": is_gallery,
            "media_metadata": media_metadata,
            "media_sources": []
        }
        posts.append(post)
    return posts

all_posts.extend(extract_posts(data_productivity, "productivity"))
all_posts.extend(extract_posts(data_getdisciplined, "getdisciplined"))
all_posts.extend(extract_posts(data_deciding, "DecidingToBeBetter"))
all_posts.extend(extract_posts(data_studytips, "studytips"))
all_posts.extend(extract_posts(data_getstudying, "GetStudying"))

print(f"Total posts collected: {len(all_posts)}")

# Download images
def download_image(url, filename):
    try:
        resp = requests.get(url, headers={"User-Agent": "RedditScout/1.0"}, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 1024:
            path = os.path.join(MEDIA_DIR, filename)
            with open(path, 'wb') as f:
                f.write(resp.content)
            return filename
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return None

downloaded_files = []

for post in all_posts:
    url = post["url"]
    # Check for direct image links (i.redd.it)
    if url and url.startswith("https://i.redd.it/") and url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        filename = url.split("/")[-1]
        if download_image(url, filename):
            post["media_sources"].append(f"{TODAY}-media/{filename}")
            downloaded_files.append(filename)
    # Check for post_hint image
    if post["post_hint"] == "image" and url and url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        filename = url.split("/")[-1]
        if download_image(url, filename):
            post["media_sources"].append(f"{TODAY}-media/{filename}")
            downloaded_files.append(filename)
    # Gallery
    if post["is_gallery"] and post["media_metadata"]:
        for media_id, meta in post["media_metadata"].items():
            # Get the best quality image URL
            if "p" in meta:
                p_list = meta["p"]
                if isinstance(p_list, list) and len(p_list) > 0:
                    img_url = p_list[-1].get("u", "")
                    if img_url:
                        # Convert to direct URL if needed
                        if img_url.startswith("https://preview.redd.it/"):
                            img_url = img_url.replace("preview.redd.it/", "i.redd.it/").split("?")[0]
                        filename = f"{media_id}.jpg"
                        if download_image(img_url, filename):
                            post["media_sources"].append(f"{TODAY}-media/{filename}")
                            downloaded_files.append(filename)

print(f"Images downloaded: {len(downloaded_files)}")

# Save raw data
raw_data = {"posts": all_posts}
with open(f"/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/_temp_posts.json", 'w') as f:
    json.dump(raw_data, f, indent=2)

# Calculate viral score
def calculate_viral_score(post):
    score = post["score"]
    num_comments = post["num_comments"]
    upvote_ratio = post["upvote_ratio"]

    # Raw score
    raw_points = min(score, 5000) / 500
    if raw_points > 10:
        raw_points = 10

    # Engagement
    engagement = (num_comments / (score + 1)) * 100 * 0.03
    if engagement > 3:
        engagement = 3
    engagement_points = engagement

    # Upvote ratio
    ratio_points = upvote_ratio * 10
    if ratio_points > 10:
        ratio_points = 10

    # Relevance
    text = (post["title"] + " " + post["selftext"]).lower()
    found_keywords = set()
    for kw in KEYWORDS:
        if kw in text:
            found_keywords.add(kw)
    relevance_bonus = len(found_keywords)
    if relevance_bonus > 3:
        relevance_bonus = 3

    total = raw_points + engagement_points + ratio_points + relevance_bonus
    viral_score = round(total / 2.6, 1)
    return viral_score, raw_points, engagement_points, ratio_points, relevance_bonus

# Add viral scores and hours ago
now = datetime.now()
for post in all_posts:
    viral_score, raw, eng, ratio, rel = calculate_viral_score(post)
    post["viral_score"] = viral_score
    post["raw_points"] = raw
    post["engagement_points"] = eng
    post["ratio_points"] = ratio
    post["relevance_bonus"] = rel
    # Hours ago
    created_dt = datetime.fromtimestamp(post["created"])
    hours_ago = (now - created_dt).total_seconds() / 3600
    post["hours_ago"] = int(hours_ago) if hours_ago >= 1 else 1

# Sort by viral score descending
all_posts.sort(key=lambda x: x["viral_score"], reverse=True)

# Format the report
report_lines = []
report_lines.append(f"# Reddit Scout Report: Focus Timer Opportunities")
report_lines.append(f"**Date:** {TODAY}")
report_lines.append("")
report_lines.append("## Top Opportunities")
report_lines.append("")

for i, post in enumerate(all_posts[:5], 1):
    title = post["title"]
    permalink = post["permalink"]
    subreddit = post["subreddit"]
    score = post["score"]
    num_comments = post["num_comments"]
    upvote_ratio = post["upvote_ratio"]
    hours_ago = post["hours_ago"]
    selftext = post["selftext"]
    viral_score = post["viral_score"]
    raw_points = post["raw_points"]
    engagement_points = post["engagement_points"]
    ratio_points = post["ratio_points"]
    relevance_bonus = post["relevance_bonus"]
    media_sources = post["media_sources"]

    # Summary: first 200 chars, 2-3 sentences (already truncated)
    summary = selftext if selftext else "(No text summary available)"

    report_lines.append(f"### {i}. [{title}](https://www.reddit.com{permalink})")
    report_lines.append(f"Subreddit: r/{subreddit} | Score: {score} | Comments: {num_comments} | Upvote ratio: {upvote_ratio:.0%}")
    report_lines.append(f"Posted: ~{hours_ago} hours ago")
    report_lines.append("")
    report_lines.append(f"**Summary:** {summary}")
    report_lines.append("")
    report_lines.append(f"**Viral Score:** {viral_score:.1f}/10")
    report_lines.append(f"- Raw score: {raw_points:.1f}/10")
    report_lines.append(f"- Engagement: {engagement_points:.1f}/10")
    report_lines.append(f"- Upvote ratio: {ratio_points:.1f}/10")
    report_lines.append(f"- Relevance bonus: {relevance_bonus}/3")
    report_lines.append("")
    if media_sources:
        report_lines.append("**Media:**")
        for src in media_sources:
            # alt text: first few words of title
            alt = title[:50] + ("..." if len(title) > 50 else "")
            report_lines.append(f"![{alt}]({src})")
    report_lines.append("")

if len(all_posts) > 5:
    report_lines.append("## Honorable Mentions")
    for i, post in enumerate(all_posts[5:10], 6):
        title = post["title"]
        permalink = post["permalink"]
        subreddit = post["subreddit"]
        score = post["score"]
        summary = post["selftext"][:100] if post["selftext"] else "(No text)"
        report_lines.append(f"### {i}. [{title}](https://www.reddit.com{permalink}) (r/{subreddit} | {score} upvotes) – {summary}.")
    report_lines.append("")

# Media Summary
if downloaded_files:
    report_lines.append("## Media Summary")
    report_lines.append(f"Downloaded images ({TODAY}-media/):")
    # List files with sizes
    for fname in sorted(set(downloaded_files)):
        path = os.path.join(MEDIA_DIR, fname)
        try:
            size_kb = os.path.getsize(path) // 1024
        except:
            size_kb = 0
        report_lines.append(f"- **{fname}** ({size_kb} KB)")
        # embed image
        report_lines.append(f"  ![{fname}]({TODAY}-media/{fname})")
    report_lines.append("")

# GitHub link
report_lines.append("---")
report_lines.append(f"**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/{TODAY}.md")

# Write report
report_content = "\n".join(report_lines)
report_path = f"/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/{TODAY}.md"
with open(report_path, 'w') as f:
    f.write(report_content)

print(f"Report written to {report_path}")

# Upload to GitHub
# Get token
token = os.getenv("GITHUB_TOKEN") or os.getenv("REDDIT_TOKEN") or os.getenv("OPENCLAW_GITHUB_TOKEN")
if not token:
    # Try to read from ~/.openclaw/.env
    env_path = os.path.expanduser("~/.openclaw/.env")
    creds = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    creds[k] = v.strip('"\'')
        token = creds.get("GITHUB_TOKEN") or creds.get("REDDIT_TOKEN") or creds.get("OPENCLAW_GITHUB_TOKEN")

if not token:
    print("ERROR: No GitHub token found in environment or ~/.openclaw/.env")
    exit(1)

headers = {"Authorization": f"token {token}", "Content-Type": "application/json"}

# Upload media files to reports/YYYY-MM-DD-media/
for fname in sorted(set(downloaded_files)):
    path = os.path.join(MEDIA_DIR, fname)
    try:
        with open(path, 'rb') as f:
            content_b64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"Error reading {fname}: {e}")
        continue
    github_path = f"reports/{TODAY}-media/{fname}"
    url = f"{BASE_URL}/{github_path}"
    # Check existing
    try:
        get_resp = requests.get(url, headers=headers)
        sha = ""
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha", "")
    except:
        sha = ""
    # Prepare payload
    payload = {
        "message": f"Add {fname}",
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha
    # Upload
    try:
        put_resp = requests.put(url, headers=headers, json=payload)
        if put_resp.status_code in (200, 201):
            print(f"Uploaded media: {fname}")
        else:
            print(f"Failed to upload {fname}: {put_resp.status_code} {put_resp.text}")
    except Exception as e:
        print(f"Error uploading {fname}: {e}")

# Upload report markdown
report_file_path = report_path
try:
    with open(report_file_path, 'rb') as f:
        report_b64 = base64.b64encode(f.read()).decode('utf-8')
except Exception as e:
    print(f"Error reading report: {e}")
    exit(1)

github_report_path = f"reports/{TODAY}.md"
url = f"{BASE_URL}/{github_report_path}"
# Check existing
try:
    get_resp = requests.get(url, headers=headers)
    sha = ""
    if get_resp.status_code == 200:
        sha = get_resp.json().get("sha", "")
except:
    sha = ""
payload = {
    "message": f"Update Reddit Scout report for {TODAY}",
    "content": report_b64
}
if sha:
    payload["sha"] = sha
try:
    put_resp = requests.put(url, headers=headers, json=payload)
    if put_resp.status_code in (200, 201):
        print(f"Uploaded report: {TODAY}.md")
    else:
        print(f"Failed to upload report: {put_resp.status_code} {put_resp.text}")
except Exception as e:
    print(f"Error uploading report: {e}")

print("Scout job completed.")
