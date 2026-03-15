#!/usr/bin/env python3
import sys, json, datetime

data = json.load(sys.stdin)
posts = data['data']['children']
out = []

for p in posts:
    d = p['data']
    media_sources = []
    url = d.get('url', '')
    post_hint = d.get('post_hint')
    is_gallery = d.get('is_gallery', False)
    media_meta = d.get('media_metadata', {})

    # Condition A: post_hint image
    if post_hint == 'image' and url and url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        media_sources.append(url)

    # Condition B: gallery
    if is_gallery:
        for meta in media_meta.values():
            if 'p' in meta and 'u' in meta['p'][0]:
                media_sources.append(meta['p'][0]['u'])

    # Condition C: direct image link (common for i.redd.it)
    if not media_sources and url and url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        media_sources.append(url)

    out.append({
        'title': d.get('title', ''),
        'permalink': d.get('permalink', ''),
        'subreddit': d.get('subreddit', ''),
        'score': d.get('score', 0),
        'num_comments': d.get('num_comments', 0),
        'upvote_ratio': d.get('upvote_ratio', 0),
        'created': d.get('created_utc', 0),
        'selftext': d.get('selftext', '')[:200],
        'url': url,
        'post_hint': post_hint,
        'is_gallery': is_gallery,
        'media_metadata': media_meta,
        'media_sources': media_sources
    })

print(json.dumps(out))
