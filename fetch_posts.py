#!/usr/bin/env python3
import sys, json, datetime, os, requests

SUBREDDITS = ['productivity', 'getdisciplined', 'DecidingToBeBetter', 'StudyTips', 'GetStudying']
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

all_posts = []

for sub in SUBREDDITS:
    url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=5"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"Error fetching {sub}: {resp.status_code}", file=sys.stderr)
            continue
        data = resp.json()
        posts = data.get('data', {}).get('children', [])
        for p in posts:
            d = p['data']
            media_sources = []
            img_url = d.get('url', '')
            post_hint = d.get('post_hint')
            is_gallery = d.get('is_gallery', False)
            media_meta = d.get('media_metadata', {})

            # Condition A: post_hint image
            if post_hint == 'image' and img_url and img_url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                media_sources.append(img_url)

            # Condition B: gallery
            if is_gallery:
                for meta in media_meta.values():
                    if 'p' in meta and 'u' in meta['p'][0]:
                        media_sources.append(meta['p'][0]['u'])

            # Condition C: direct image link (common for i.redd.it)
            if not media_sources and img_url and img_url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                media_sources.append(img_url)

            all_posts.append({
                'title': d.get('title', ''),
                'permalink': d.get('permalink', ''),
                'subreddit': d.get('subreddit', ''),
                'score': d.get('score', 0),
                'num_comments': d.get('num_comments', 0),
                'upvote_ratio': d.get('upvote_ratio', 0),
                'created': d.get('created_utc', 0),
                'selftext': d.get('selftext', '')[:200],
                'url': img_url,
                'post_hint': post_hint,
                'is_gallery': is_gallery,
                'media_metadata': media_meta,
                'media_sources': media_sources
            })
    except Exception as e:
        print(f"Exception fetching {sub}: {e}", file=sys.stderr)

print(json.dumps(all_posts))
