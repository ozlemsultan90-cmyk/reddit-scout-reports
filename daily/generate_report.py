#!/usr/bin/env python3
import json
import os
from datetime import datetime
import urllib.request

# Configuration
TODAY = "2026-03-04"
REPORT_DIR = "/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily"
MEDIA_DIR = f"{REPORT_DIR}/{TODAY}-media"
REPORT_PATH = f"{REPORT_DIR}/{TODAY}.md"
TEMP_JSON = f"{REPORT_DIR}/_temp_posts.json"

KEYWORDS = ["productivity", "focus", "screen time", "gamification", "phone addiction", "study", "discipline", "digital minimalism", "streak", "accountability", "motivation"]

# Timestamp for midnight UTC, March 4 2026
TODAY_TS = 1772630400

os.makedirs(MEDIA_DIR, exist_ok=True)

# Load JSON files
subreddit_files = [
    ("productivity.json", "productivity"),
    ("getdisciplined.json", "getdisciplined"),
    ("DecidingToBeBetter.json", "DecidingToBeBetter"),
    ("StudyTips.json", "studytips"),
    ("GetStudying.json", "GetStudying")
]

all_posts = []

def extract_posts(data, subreddit_name):
    posts = []
    children = data.get("data", {}).get("children", [])
    for child in children:
        post_data = child.get("data", {})
        post = {
            "title": post_data.get("title", ""),
            "permalink": post_data.get("permalink", ""),
            "subreddit": post_data.get("subreddit", subreddit_name),
            "score": post_data.get("ups", 0),
            "num_comments": post_data.get("num_comments", 0),
            "upvote_ratio": post_data.get("upvote_ratio", 0),
            "created": post_data.get("created", 0),
            "selftext": post_data.get("selftext", ""),
            "url": post_data.get("url", ""),
            "post_hint": post_data.get("post_hint"),
            "is_gallery": post_data.get("is_gallery", False),
            "media_metadata": post_data.get("media_metadata"),
            "id": post_data.get("id", post_data.get("permalink", "").split("/")[-1] if post_data.get("permalink") else ""),
            "media_sources": []
        }
        posts.append(post)
    return posts

for filename, subreddit in subreddit_files:
    filepath = os.path.join(REPORT_DIR, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            posts = extract_posts(data, subreddit)
            all_posts.extend(posts)
            print(f"Loaded {len(posts)} posts from {filename}")
        except Exception as e:
            print(f"Error loading {filename}: {e}")
    else:
        print(f"Missing file: {filepath}")

print(f"Total posts: {len(all_posts)}")

# Calculate hours ago
for post in all_posts:
    hours_ago = (TODAY_TS - post["created"]) / 3600
    post["hours_ago"] = round(hours_ago, 1)

# Viral score calculation
def calculate_viral_score(post):
    score = post["score"]
    num_comments = post["num_comments"]
    upvote_ratio = post["upvote_ratio"]
    selftext = post["selftext"] or ""
    title = post["title"] or ""
    combined = (title + " " + selftext).lower()
    
    raw = min(score, 5000) / 500
    engagement = (num_comments / (score + 1)) * 100 * 0.03
    engagement_points = min(engagement, 3)
    ratio_points = upvote_ratio * 10
    relevance = sum(1 for kw in KEYWORDS if kw in combined)
    relevance_bonus = min(relevance, 3)
    
    total = raw + engagement_points + ratio_points + relevance_bonus
    return {
        "viral_score": round(total / 2.6, 1),
        "raw_points": round(raw, 1),
        "engagement_points": round(engagement_points, 1),
        "ratio_points": round(ratio_points, 1),
        "relevance_bonus": relevance
    }

for post in all_posts:
    score_data = calculate_viral_score(post)
    post.update(score_data)

all_posts.sort(key=lambda x: x["viral_score"], reverse=True)

# Save raw JSON for records
with open(TEMP_JSON, "w") as f:
    json.dump(all_posts, f, indent=2)
print(f"Raw data saved to {TEMP_JSON}")

# Download images
def download_image(url, path):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) > 1024:
            with open(path, "wb") as f:
                f.write(data)
            if os.path.getsize(path) > 1024:
                return True
    except Exception as e:
        print(f"  Download error: {e}")
    return False

media_list = []

for post in all_posts:
    url = post.get("url", "")
    post_hint = post.get("post_hint")
    is_gallery = post.get("is_gallery", False)
    metadata = post.get("media_metadata")
    
    has_image = False
    image_urls = []
    
    # Direct image links (i.redd.it or imgur with image extension)
    if url and ('i.redd.it' in url or url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))):
        has_image = True
        image_urls = [url]
    
    if has_image:
        for idx, img_url in enumerate(image_urls):
            sub = post['subreddit']
            post_id = post.get('id', str(hash(img_url))[-8:])
            if img_url.lower().endswith('.jpg') or img_url.lower().endswith('.jpeg'):
                ext = 'jpg'
            elif img_url.lower().endswith('.png'):
                ext = 'png'
            elif img_url.lower().endswith('.gif'):
                ext = 'gif'
            elif img_url.lower().endswith('.webp'):
                ext = 'webp'
            else:
                ext = 'jpg'
            filename = f"{sub}_{post_id}_{idx}.{ext}"
            filename = filename.replace('/', '_').replace('\\', '_')
            filepath = os.path.join(MEDIA_DIR, filename)
            
            print(f"Downloading: {img_url}")
            if download_image(img_url, filepath):
                media_list.append((post, f"{TODAY}-media/{filename}"))
            else:
                print(f"  Failed: {filename}")

# Build report
lines = []
lines.append(f"# Reddit Scout Report: Focus Timer Opportunities")
lines.append(f"**Date:** {TODAY}")
lines.append("")
lines.append("## Top Opportunities")
lines.append("")

# Top 5
for idx, post in enumerate(all_posts[:5]):
    title = post['title']
    url = f"https://www.reddit.com{post['permalink']}"
    subreddit = post['subreddit']
    score = post['score']
    comments = post['num_comments']
    ratio_pct = int(post['upvote_ratio'] * 100)
    hours = post['hours_ago']
    short_text = (post['selftext'] or "")[:200] + ("..." if len(post['selftext'] or "") > 200 else "")
    
    lines.append(f"### {idx+1}. [{title}]({url})")
    lines.append(f"Subreddit: r/{subreddit} | Score: {score} | Comments: {comments} | Upvote ratio: {ratio_pct}%")
    lines.append(f"Posted: ~{hours} hours ago")
    lines.append("")
    lines.append("**Summary:** " + short_text)
    lines.append("")
    lines.append(f"**Viral Score:** {post['viral_score']:.1f}/10")
    lines.append(f"- Raw score: {post['raw_points']:.1f}/10")
    lines.append(f"- Engagement: {post['engagement_points']:.1f}/10")
    lines.append(f"- Upvote ratio: {post['ratio_points']:.1f}/10")
    lines.append(f"- Relevance bonus: {post['relevance_bonus']}/3")
    lines.append("")
    
    # Add media for this post if downloaded
    for p, media_path in media_list:
        if p.get('permalink') == post['permalink']:
            alt = title.replace('[', '').replace(']', '').replace('(', '').replace(')', '').replace('|', '').strip()[:50]
            lines.append(f"![{alt}]({media_path})")
            lines.append("")

# Honorable Mentions 6-10
if len(all_posts) > 5:
    lines.append("## Honorable Mentions")
    lines.append("")
    for idx, post in enumerate(all_posts[5:10], start=6):
        title = post['title']
        url = f"https://www.reddit.com{post['permalink']}"
        one_liner = (post['selftext'] or "")[:100] + ("..." if len(post['selftext'] or "") > 100 else "")
        lines.append(f"### {idx}. [{title}]({url}) (r/{post['subreddit']} | {post['score']} upvotes) – {one_liner}")

# Media Summary
lines.append("")
lines.append("## Media Summary")
lines.append(f"Downloaded images ({TODAY}-media/):")
if os.path.exists(MEDIA_DIR):
    files = sorted(os.listdir(MEDIA_DIR))
    if files:
        for fname in files:
            fpath = os.path.join(MEDIA_DIR, fname)
            size_kb = os.path.getsize(fpath) // 1024
            lines.append(f"- **{fname}** ({size_kb} KB)")
            lines.append(f"  ![{fname}]({TODAY}-media/{fname})")
    else:
        lines.append("No images downloaded.")
else:
    lines.append("Media directory not found.")

lines.append("")
lines.append("---")
lines.append(f"**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/{TODAY}.md")

report = "\n".join(lines)
with open(REPORT_PATH, "w") as f:
    f.write(report)

print(f"\nReport complete: {REPORT_PATH}")

EOF