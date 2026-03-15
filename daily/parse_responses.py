#!/usr/bin/env python3
import json
import sys
import re

def extract_json_from_response(text):
    """Extract the JSON object from the web_fetch response."""
    # Find the JSON after "Source: Web Fetch\n---\n" and before END marker
    match = re.search(r'Source: Web Fetch\n---\n(.*?)\n<<<END_EXTERNAL_UNTRUSTED_CONTENT', text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        return json.loads(json_str)
    else:
        # Fallback: try to find any JSON object
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    return None

# Read all 5 response files
responses = []
for i in range(5):
    filename = f"/ Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/response{i+1}.txt"
    try:
        with open(filename, 'r') as f:
            responses.append(f.read())
    except FileNotFoundError:
        print(f"Warning: {filename} not found", file=sys.stderr)

all_posts = []

for resp in responses:
    data = extract_json_from_response(resp)
    if data and 'data' in data and 'children' in data['data']:
        all_posts.extend(data['data']['children'])
    else:
        print(f"Warning: Could not extract posts from response", file=sys.stderr)

# Save combined raw posts
output = {
    "posts": all_posts,
    "count": len(all_posts),
    "subreddits": ["productivity", "getdisciplined", "DecidingToBeBetter", "studytips", "GetStudying"]
}

with open("/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/_temp_posts.json", 'w') as f:
    json.dump(output, f, indent=2)

print(f"Saved {len(all_posts)} posts to _temp_posts.json")
