#!/usr/bin/env python3
import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta

# Configuration
TODAY = "2026-03-13"
WORKSPACE = "/Users/ozlemsultan/.openclaw/workspace/reddit-productivity"
MEDIA_DIR = os.path.join(WORKSPACE, "daily", f"{TODAY}-media")
TEMP_FILE = os.path.join(WORKSPACE, "daily", "_temp_posts.json")
REPORT_FILE = os.path.join(WORKSPACE, "daily", f"{TODAY}.md")

os.makedirs(MEDIA_DIR, exist_ok=True)

SUBREDDITS = ["productivity", "getdisciplined", "DecidingToBeBetter", "StudyTips", "GetStudying"]

REDDIT_BASE = "https://www.reddit.com/r/{}/top.json?t=day&limit=5"
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

def fetch_subreddit(sub):
    url = REDDIT_BASE.format(sub)
    try:
        # Use a proper User-Agent to avoid being blocked
        result = subprocess.run(
            ['curl', '-s', '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
             url],
            capture_output=True, text=True
        )
        return result.stdout
    except Exception as e:
        print(f"Error fetching {sub}: {e}")
        return ""

def extract_posts(raw_json, sub):
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    posts = []
    for child in data.get('data', {}).get('children', []):
        p = child.get('data', {})
        post = {
            'title': p.get('title', ''),
            'permalink': p.get('permalink', ''),
            'subreddit': sub,
            'score': p.get('score', 0),
            'num_comments': p.get('num_comments', 0),
            'upvote_ratio': p.get('upvote_ratio', 0),
            'created': p.get('created_utc', 0),
            'selftext': p.get('selftext', '')[:200],
            'url': p.get('url', ''),
            'post_hint': p.get('post_hint', ''),
            'is_gallery': p.get('is_gallery', False),
            'media_metadata': p.get('media_metadata', {}),
            'media_sources': []
        }
        posts.append(post)
    return posts

def download_file(url, dest):
    try:
        result = subprocess.run(['curl', '-L', '-s', '-o', dest, url], capture_output=True)
        if result.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 1024:
            return True
    except:
        pass
    return False

def download_images(posts):
    for i, post in enumerate(posts):
        url = post['url']
        if url.lower().endswith(IMAGE_EXTS):
            filename = f"{TODAY}_img{i}_{os.path.basename(url)}"
            dest = os.path.join(MEDIA_DIR, filename)
            if download_file(url, dest):
                post['media_sources'].append(f"{TODAY}-media/{filename}")

        if post.get('is_gallery') and post.get('media_metadata'):
            for idx, (media_id, meta) in enumerate(post['media_metadata'].items()):
                img_url = meta.get('s', {}).get('u', '')
                if img_url:
                    filename = f"{TODAY}_gallery{i}_{idx}_{os.path.basename(img_url)}"
                    dest = os.path.join(MEDIA_DIR, filename)
                    if download_file(img_url, dest):
                        post['media_sources'].append(f"{TODAY}-media/{filename}")

def calculate_viral(post):
    score = post['score']
    num_comments = post['num_comments']
    upvote_ratio = post['upvote_ratio']
    title_selftext = (post.get('title', '') + ' ' + post.get('selftext', '')).lower()

    raw_points = min(score, 5000) / 500
    engagement_factor = (num_comments / (score + 1)) * 100 * 0.03
    engagement_points = min(engagement_factor, 3)
    ratio_points = upvote_ratio * 10
    keywords = ['productivity', 'focus', 'screen time', 'gamification', 'phone addiction',
                'study', 'discipline', 'digital minimalism', 'streak', 'accountability',
                'motivation']
    distinct_matches = sum(1 for kw in keywords if kw in title_selftext)
    relevance_bonus = min(distinct_matches, 3)
    total = raw_points + engagement_points + ratio_points + relevance_bonus
    viral_score = round(total / 2.6, 1)

    return {
        'raw_points': round(raw_points, 2),
        'engagement_points': round(engagement_points, 2),
        'ratio_points': round(ratio_points, 2),
        'relevance_bonus': relevance_bonus,
        'viral_score': viral_score
    }

def hours_ago(created_utc):
    diff_seconds = time.time() - created_utc
    return round(diff_seconds / 3600)

# Main execution
print("Starting Reddit Scout...")

all_posts = []
for sub in SUBREDDITS:
    print(f"Fetching r/{sub}...")
    raw = fetch_subreddit(sub)
    posts = extract_posts(raw, sub)
    all_posts.extend(posts)
    time.sleep(0.5)  # be nice to Reddit

print(f"Total posts fetched: {len(all_posts)}")

# Score and sort
for post in all_posts:
    score_data = calculate_viral(post)
    post.update(score_data)

all_posts.sort(key=lambda x: x.get('viral_score', 0), reverse=True)

# Save scored posts
with open(TEMP_FILE, 'w') as f:
    json.dump(all_posts, f, indent=2)
print(f"Raw data saved to {TEMP_FILE}")

# Download images
print("Downloading images...")
download_images(all_posts)

# Generate report
print("Generating report...")
lines = []
lines.append("# Reddit Scout Report: Focus Timer Opportunities")
lines.append(f"**Date:** {TODAY}")
lines.append("")
lines.append("## Top Opportunities")
lines.append("")

# Top 5
for idx, post in enumerate(all_posts[:5], 1):
    lines.append(f"### {idx}. [{post['title']}](https://www.reddit.com{post['permalink']})")
    lines.append(f"Subreddit: r/{post['subreddit']} | Score: {post['score']} | Comments: {post['num_comments']} | Upvote ratio: {post['upvote_ratio']:.0%}")
    lines.append(f"Posted: ~{hours_ago(post['created'])} hours ago")
    lines.append("")
    summary = post['selftext'] if post['selftext'] else 'No selftext available.'
    lines.append(f"**Summary:** {summary}")
    lines.append("")
    vs = post.get('viral_score', 0)
    lines.append(f"**Viral Score:** {vs:.1f}/10")
    lines.append(f"- Raw score: {post.get('raw_points', 0):.1f}/10")
    lines.append(f"- Engagement: {post.get('engagement_points', 0):.1f}/10")
    lines.append(f"- Upvote ratio: {post.get('ratio_points', 0):.1f}/10")
    lines.append(f"- Relevance bonus: {post.get('relevance_bonus', 0)}/3")
    lines.append("")
    if post['media_sources']:
        lines.append("**Media:**")
        for path in post['media_sources']:
            lines.append(f"![Image]({path})")
        lines.append("")

# Honorable mentions (6-10)
if len(all_posts) > 5:
    lines.append("")
    lines.append("### Honorable Mentions")
    lines.append("")
    for idx, post in enumerate(all_posts[5:10], 6):
        summary = post['selftext'][:100].strip() if post['selftext'] else 'No summary'
        lines.append(f"- ### {idx}. [{post['title']}](https://www.reddit.com{post['permalink']}) (r/{post['subreddit']} | {post['score']} upvotes) – {summary}.")
    lines.append("")

# Media Summary
lines.append("## Media Summary")
lines.append(f"Downloaded images ({TODAY}-media/):")
if os.path.exists(MEDIA_DIR):
    files = sorted([f for f in os.listdir(MEDIA_DIR) if f.lower().endswith(IMAGE_EXTS)])
    for filename in files:
        filepath = os.path.join(MEDIA_DIR, filename)
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        lines.append(f"- **{filename}** ({size_kb} KB)")
        lines.append(f"  ![Description]({TODAY}-media/{filename})")
else:
    lines.append("No media files downloaded.")

lines.append("")
lines.append("---")
lines.append(f"**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/{TODAY}.md")

with open(REPORT_FILE, 'w') as f:
    f.write('\n'.join(lines))

print(f"Report generated at {REPORT_FILE}")

# Upload to GitHub
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or os.getenv('OPENCLAW_GITHUB_TOKEN')
if not GITHUB_TOKEN:
    print("Warning: No GitHub token found in environment (GITHUB_TOKEN or OPENCLAW_GITHUB_TOKEN). Skipping upload.")
else:
    BASE_URL = "https://api.github.com/repos/ozlemsultan90-cmyk/reddit-scout-reports/contents"
    print("Uploading to GitHub...")
    # Upload media files first
    if os.path.exists(MEDIA_DIR):
        for filename in sorted([f for f in os.listdir(MEDIA_DIR) if f.lower().endswith(IMAGE_EXTS)]):
            filepath = os.path.join(MEDIA_DIR, filename)
            github_path = f"reports/{TODAY}-media/{filename}"
            b64_cmd = f"base64 -i \"{filepath}\" | tr -d '\\n'"
            b64_result = subprocess.run(b64_cmd, shell=True, capture_output=True, text=True)
            content_b64 = b64_result.stdout.strip()

            # Check if file exists to get SHA
            check_url = f"{BASE_URL}/{github_path}"
            check_cmd = ['curl', '-s', '-H', f'Authorization: token {GITHUB_TOKEN}', check_url]
            check_res = subprocess.run(check_cmd, capture_output=True, text=True)
            sha = ""
            try:
                check_data = json.loads(check_res.stdout)
                sha = check_data.get('sha', '')
            except:
                pass

            put_data = {"message": f"Add {filename}", "content": content_b64}
            if sha:
                put_data["sha"] = sha

            put_resp = subprocess.run(
                ['curl', '-X', 'PUT', '-s', '-H', f'Authorization: token {GITHUB_TOKEN}',
                 '-H', 'Content-Type: application/json',
                 '-d', json.dumps(put_data), f"{BASE_URL}/{github_path}"],
                capture_output=True, text=True
            )
            try:
                resp_data = json.loads(put_resp.stdout)
                if 'sha' in resp_data:
                    print(f"Uploaded {filename}")
                else:
                    print(f"Error uploading {filename}: {put_resp.stdout}")
            except:
                print(f"Error parsing response for {filename}")

    # Upload report
    report_b64_cmd = f"base64 -i \"{REPORT_FILE}\" | tr -d '\\n'"
    report_b64_result = subprocess.run(report_b64_cmd, shell=True, capture_output=True, text=True)
    report_content_b64 = report_b64_result.stdout.strip()

    report_path = f"reports/{TODAY}.md"
    check_report_url = f"{BASE_URL}/{report_path}"
    check_report_cmd = ['curl', '-s', '-H', f'Authorization: token {GITHUB_TOKEN}', check_report_url]
    check_report_res = subprocess.run(check_report_cmd, capture_output=True, text=True)
    report_sha = ""
    try:
        check_report_data = json.loads(check_report_res.stdout)
        report_sha = check_report_data.get('sha', '')
    except:
        pass

    put_report_data = {"message": f"Update Reddit Scout report for {TODAY}", "content": report_content_b64}
    if report_sha:
        put_report_data["sha"] = report_sha

    put_report_resp = subprocess.run(
        ['curl', '-X', 'PUT', '-s', '-H', f'Authorization: token {GITHUB_TOKEN}',
         '-H', 'Content-Type: application/json',
         '-d', json.dumps(put_report_data), f"{BASE_URL}/{report_path}"],
        capture_output=True, text=True
    )
    try:
        report_resp_data = json.loads(put_report_resp.stdout)
        if 'sha' in report_resp_data:
            print("Report uploaded successfully.")
        else:
            print(f"Error uploading report: {put_report_resp.stdout}")
    except:
        print("Error parsing report upload response")

print("Done.")
