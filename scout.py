#!/usr/bin/env python3
import json
import os
import re
import math
import requests
from datetime import datetime
from pathlib import Path

WORKDIR = Path("/Users/ozlemsultan/.openclaw/workspace/reddit-productivity")
OUTDIR = WORKDIR / "daily" / "2026-03-15"
MEDIA_DIR = OUTDIR / "media"
OUTDIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Subreddits (first 5 from subreddits.md)
subreddits = [
    "productivity",
    "getdisciplined",
    "DecidingToBeBetter",
    "StudyTips",
    "GetStudying"
]

# Fetch top posts from each subreddit with proper headers
session = requests.Session()
session.headers.update({
    "User-Agent": "RedditScout/1.0 (by /u/yourusername)"
})

raw_posts = []
for sub in subreddits:
    url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=5"
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            for child in data.get("data", {}).get("children", []):
                raw_posts.append(child["data"])
        else:
            print(f"Warning: {sub} returned {resp.status_code}")
    except Exception as e:
        print(f"Error fetching {sub}: {e}")

def get_best_image_url(post):
    # Check media_metadata (largest preview)
    if "media_metadata" in post and post["media_metadata"]:
        first_key = list(post["media_metadata"].keys())[0]
        meta = post["media_metadata"][first_key]
        # Get the largest resolution 's' or 'u'
        if "s" in meta:
            return meta["s"]["u"]
        if "u" in meta:
            return meta["u"]
    # Check preview images
    if "preview" in post and "images" in post["preview"] and post["preview"]["images"]:
        # source is largest
        src = post["preview"]["images"][0].get("source", {})
        if "url" in src:
            return src["url"]
    # Check if direct image link (i.redd.it or imgur)
    url = post.get("url", "")
    if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return url
    if "i.redd.it" in url or "i.imgur.com" in url:
        return url
    return None

def truncate_text(text, max_len=300):
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."

processed = []
for post in raw_posts:
    post_id = post["id"]
    title = post["title"]
    author = post.get("author", "[deleted]")
    score = post.get("ups", 0)
    num_comments = post.get("num_comments", 0)
    subreddit = post.get("subreddit", "")
    permalink = f"https://www.reddit.com{post.get('permalink', '')}"
    created = datetime.fromtimestamp(post.get("created_utc", 0)).strftime("%Y-%m-%d %H:%M UTC")
    upvote_ratio = post.get("upvote_ratio", 0)
    is_self = post.get("is_self", False)
    selftext = post.get("selftext", "") if is_self else None
    thumbnail = post.get("thumbnail", "") if post.get("thumbnail", "").startswith("http") else None
    selftext_html = post.get("selftext_html", "")
    media_metadata = post.get("media_metadata", None)
    preview = post.get("preview", None)

    # Viral score
    raw_score = upvote_ratio * math.log10(score + num_comments + 1)
    viral_score = round(raw_score * 100) / 100

    # Image downloading
    image_url = get_best_image_url(post)
    local_image = None
    if image_url:
        try:
            ext = os.path.splitext(image_url)[1].split("?")[0] or ".jpg"
            if not ext.startswith("."):
                ext = "." + ext
            local_path = MEDIA_DIR / f"{post_id}{ext}"
            resp = requests.get(image_url, timeout=15)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                local_image = str(local_path.relative_to(WORKDIR))
        except Exception as e:
            print(f"Failed to download {image_url}: {e}")

    processed.append({
        "id": post_id,
        "title": title,
        "author": author,
        "score": score,
        "num_comments": num_comments,
        "subreddit": subreddit,
        "permalink": permalink,
        "created": created,
        "upvote_ratio": upvote_ratio,
        "viral_score": viral_score,
        "is_self": is_self,
        "selftext": selftext,
        "selftext_html": selftext_html,
        "thumbnail": thumbnail,
        "media_metadata": media_metadata,
        "preview": preview,
        "image_url": image_url,
        "local_image": local_image
    })

# Sort by viral_score descending
processed.sort(key=lambda x: x["viral_score"], reverse=True)

# Save raw data
with open(OUTDIR / "raw_posts.json", "w") as f:
    json.dump(processed, f, indent=2)

# Generate markdown report
MD_HEADER = f"""# Reddit Trending Posts — Focus Timer Scout\n\nScout run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Europe/Istanbul\nSource subreddits: r/productivity, r/getdisciplined, r/DecidingToBeBetter, r/StudyTips, r/GetStudying (top 5 of past day)\nTotal posts collected: {len(processed)}\n\n---\n"""

top10 = processed[:10]
others = processed[10:]

md_lines = [MD_HEADER]

md_lines.append("## 🔥 Top 10 Viral Posts\n")
for i, p in enumerate(top10, 1):
    img_md = f"\n\n![image]({p['local_image']})" if p.get('local_image') else ""
    self_preview = ""
    if p.get('is_self') and p.get('selftext'):
        snippet = truncate_text(p['selftext'].replace('\n', ' '), 200)
        self_preview = f"\n\n> {snippet}"
    md_lines.append(f"{i}. **{p['title']}**  \n   _r/{p['subreddit']} | u/{p['author']} | 👍 {p['score']} ({int(p['upvote_ratio']*100)}%) | 💬 {p['num_comments']} | Viral: {p['viral_score']}_  \n   {p['permalink']}{img_md}{self_preview}\n")

if others:
    md_lines.append("\n## 📊 Remaining Posts (ranked)\n")
    for p in others:
        img_flag = " 🖼" if p.get('local_image') else ""
        md_lines.append(f"- **{p['title']}** (r/{p['subreddit']}, 👍 {p['score']}, 💬 {p['num_comments']}, Viral: {p['viral_score']}){img_flag}")

md_content = "\n".join(md_lines)
report_path = OUTDIR / "report.md"
with open(report_path, "w") as f:
    f.write(md_content)

print(f"Wrote report: {report_path}")
print(f"Total posts: {len(processed)}")
print(f"Top viral score: {processed[0]['viral_score'] if processed else 'N/A'}")
