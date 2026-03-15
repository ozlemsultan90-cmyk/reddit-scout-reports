#!/bin/bash
set -e

TODAY="2026-03-13"
WORKSPACE="/Users/ozlemsultan/.openclaw/workspace/reddit-productivity"
MEDIA_DIR="$WORKSPACE/daily/$TODAY-media"
TEMP_FILE="$WORKSPACE/daily/_temp_posts.json"
REPORT_FILE="$WORKSPACE/daily/$TODAY.md"

mkdir -p "$MEDIA_DIR"

# Subreddits list (first 5)
SUBREDDITS=("productivity" "getdisciplined" "DecidingToBeBetter" "StudyTips" "GetStudying")

# Initialize posts array
echo "[]" > "$TEMP_FILE"

# Fetch and process posts from each subreddit
for sub in "${SUBREDDITS[@]}"; do
  echo "Fetching r/$sub..."
  curl -s "https://www.reddit.com/r/$sub/top.json?t=day&limit=5" > /tmp/reddit_raw.json

  # Parse using python later
  python3 <<'PYTHON_EOF' > /tmp/posts_extracted.json
import json, sys, os
sub = os.environ.get('CURRENT_SUB')
with open('/tmp/reddit_raw.json', 'r') as f:
    data = json.load(f)

extracted = []
for child in data.get('data', {}).get('children', []):
    post = child.get('data', {})
    created = post.get('created_utc', 0)
    permalink = post.get('permalink', '')
    url = post.get('url', '')
    post_hint = post.get('post_hint', '')
    is_gallery = post.get('is_gallery', False)
    media_metadata = post.get('media_metadata', {})

    item = {
        'title': post.get('title', ''),
        'permalink': permalink,
        'subreddit': sub,
        'score': post.get('score', 0),
        'num_comments': post.get('num_comments', 0),
        'upvote_ratio': post.get('upvote_ratio', 0),
        'created': created,
        'selftext': post.get('selftext', '')[:200],
        'url': url,
        'post_hint': post_hint,
        'is_gallery': is_gallery,
        'media_metadata': media_metadata,
        'media_sources': []
    }
    extracted.append(item)

print(json.dumps(extracted))
PYTHON_EOF

  # Merge into master posts array
  python3 <<'PYTHON_MERGE' > /tmp/merged.json
import json
with open('$TEMP_FILE', 'r') as f:
    master = json.load(f)
with open('/tmp/posts_extracted.json', 'r') as f:
    new = json.load(f)
master.extend(new)
print(json.dumps(master))
PYTHON_MERGE
  mv /tmp/merged.json "$TEMP_FILE"
done

# Calculate viral scores
python3 <<'PYTHON_SCORE' > /tmp/posts_scored.json
import json, os
from datetime import datetime

# Istanbul timezone offset (UTC+3)
TZ_OFFSET = 3 * 3600
now = datetime.now().timestamp()

def calculate_viral(post):
    score = post['score']
    num_comments = post['num_comments']
    upvote_ratio = post['upvote_ratio']
    title_selftext = (post.get('title', '') + ' ' + post.get('selftext', '')).lower()

    # Raw points (0-10)
    raw_points = min(score, 5000) / 500

    # Engagement points (cap 3, then scaled later)
    engagement_factor = (num_comments / (score + 1)) * 100 * 0.03
    engagement_points = min(engagement_factor, 3)

    # Upvote ratio points (max 10)
    ratio_points = upvote_ratio * 10

    # Relevance bonus (max 3)
    keywords = ['productivity', 'focus', 'screen time', 'gamification', 'phone addiction',
                'study', 'discipline', 'digital minimalism', 'streak', 'accountability',
                'motivation']
    distinct_matches = sum(1 for kw in keywords if kw in title_selftext)
    relevance_bonus = min(distinct_matches, 3)

    # Total before scaling
    total = raw_points + engagement_points + ratio_points + relevance_bonus
    viral_score = round(total / 2.6, 1)  # scale to ~1-10

    return {
        'raw_points': round(raw_points, 2),
        'engagement_points': round(engagement_points, 2),
        'ratio_points': round(ratio_points, 2),
        'relevance_bonus': relevance_bonus,
        'viral_score': viral_score
    }

with open('$TEMP_FILE', 'r') as f:
    posts = json.load(f)

scored_posts = []
for post in posts:
    score_data = calculate_viral(post)
    post.update(score_data)
    scored_posts.append(post)

print(json.dumps(scored_posts))
PYTHON_SCORE
mv /tmp/posts_scored.json "$TEMP_FILE"

# Sort by viral_score descending
python3 -c "import json; d=json.load(open('$TEMP_FILE')); d.sort(key=lambda x: x.get('viral_score',0), reverse=True); json.dump(d, open('$TEMP_FILE','w'))"

# Download images
python3 <<'PYTHON_DOWNLOAD'
import json, os, subprocess, time
from datetime import datetime

TODAY = "2026-03-13"
TZ_OFFSET = 3 * 3600
MEDIA_DIR = f"/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/{TODAY}-media"

with open('$TEMP_FILE', 'r') as f:
    posts = json.load(f)

def download_file(url, dest):
    try:
        result = subprocess.run(['curl', '-L', '-s', '-o', dest, url], capture_output=True)
        if result.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 1024:
            return True
    except:
        pass
    return False

reddit_image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

for i, post in enumerate(posts):
    # Check if direct image link
    url = post.get('url', '')
    if url.lower().endswith(reddit_image_extensions):
        filename = f"{TODAY}_img{i}_{os.path.basename(url)}"
        dest = os.path.join(MEDIA_DIR, filename)
        if download_file(url, dest):
            post['media_sources'].append(f"{TODAY}-media/{filename}")

    # Check if gallery
    if post.get('is_gallery') and post.get('media_metadata'):
        for idx, (media_id, meta) in enumerate(post['media_metadata'].items()):
            img_url = meta.get('s', {}).get('u', '')
            if img_url:
                filename = f"{TODAY}_gallery{i}_{idx}_{os.path.basename(img_url)}"
                dest = os.path.join(MEDIA_DIR, filename)
                if download_file(img_url, dest):
                    post['media_sources'].append(f"{TODAY}-media/{filename}")

# save updated posts
with open('$TEMP_FILE', 'w') as f:
    json.dump(posts, f, indent=2)
PYTHON_DOWNLOAD

# Generate report
python3 <<'PYTHON_REPORT' > "$REPORT_FILE"
import json, os, time
from datetime import datetime

TODAY = "2026-03-13"
TZ_OFFSET = 3 * 3600
REPORT_LINES = []

# Header
REPORT_LINES.append("# Reddit Scout Report: Focus Timer Opportunities")
REPORT_LINES.append(f"**Date:** {TODAY}")
REPORT_LINES.append("")
REPORT_LINES.append("## Top Opportunities")
REPORT_LINES.append("")

with open('$TEMP_FILE', 'r') as f:
    posts = json.load(f)

def hours_ago(created_utc):
    diff_seconds = time.time() - created_utc
    return round(diff_seconds / 3600)

# Top 5
for idx, post in enumerate(posts[:10], 1):
    title = post['title']
    permalink = post['permalink']
    subreddit = post['subreddit']
    score = post['score']
    num_comments = post['num_comments']
    upvote_ratio = post['upvote_ratio']
    created = post['created']
    selftext = post.get('selftext', '') or ''
    viral_score = post.get('viral_score', 0)
    raw = post.get('raw_points', 0)
    eng = post.get('engagement_points', 0)
    ratio = post.get('ratio_points', 0)
    relevance = post.get('relevance_bonus', 0)
    media = post.get('media_sources', [])

    hours = hours_ago(created)

    if idx <= 5:
        REPORT_LINES.append(f"### {idx}. [{title}](https://www.reddit.com{permalink})")
        REPORT_LINES.append(f"Subreddit: r/{subreddit} | Score: {score} | Comments: {num_comments} | Upvote ratio: {upvote_ratio:.0%}")
        REPORT_LINES.append(f"Posted: ~{hours} hours ago")
        REPORT_LINES.append("")
        REPORT_LINES.append("**Summary:** " + (selftext if selftext else 'No selftext available.'))
        REPORT_LINES.append("")
        REPORT_LINES.append(f"**Viral Score:** {viral_score:.1f}/10")
        REPORT_LINES.append(f"- Raw score: {raw:.1f}/10")
        REPORT_LINES.append(f"- Engagement: {eng:.1f}/10")
        REPORT_LINES.append(f"- Upvote ratio: {ratio:.1f}/10")
        REPORT_LINES.append(f"- Relevance bonus: {relevance}/3")
        REPORT_LINES.append("")
        if media:
            REPORT_LINES.append("**Media:**")
            for path in media:
                REPORT_LINES.append(f"![Image]({path})")
        REPORT_LINES.append("")
    else:
        # Honorable mentions
        summary = (selftext[:100] if selftext else 'No summary').strip()
        REPORT_LINES.append(f"### {idx}. [{title}](https://www.reddit.com{permalink}) (r/{subreddit} | {score} upvotes) – {summary}.")
        REPORT_LINES.append("")

# Media Summary
REPORT_LINES.append("## Media Summary")
REPORT_LINES.append(f"Downloaded images ({TODAY}-media/):")
if os.path.exists(MEDIA_DIR):
    files = sorted([f for f in os.listdir(MEDIA_DIR) if f.lower().endswith(('.jpg','.jpeg','.png','.gif','.webp'))])
    for filename in files:
        filepath = os.path.join(MEDIA_DIR, filename)
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        REPORT_LINES.append(f"- **{filename}** ({size_kb} KB)")
        REPORT_LINES.append(f"  ![Description]({TODAY}-media/{filename})")
else:
    REPORT_LINES.append("No media files downloaded.")

REPORT_LINES.append("")
REPORT_LINES.append("---")
REPORT_LINES.append(f"**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/{TODAY}.md")

# Write to file
with open('$REPORT_FILE', 'w') as f:
    f.write('\n'.join(REPORT_LINES))

print("Report generated")
PYTHON_REPORT

echo "Report written to $REPORT_FILE"