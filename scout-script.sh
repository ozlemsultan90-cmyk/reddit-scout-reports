#!/bin/bash
set -euo pipefail

# 1. Determine date
TODAY="2026-03-10"
echo "Running Reddit Scout for date: $TODAY"

# 2. Setup directories
WORKDIR="/Users/ozlemsultan/.openclaw/workspace/reddit-productivity"
DAILY_DIR="$WORKDIR/daily"
MEDIA_DIR="$DAILY_DIR/$TODAY-media"
mkdir -p "$MEDIA_DIR"
TEMP_JSON="$DAILY_DIR/_temp_posts.json"

# 3. Subreddits (first 5)
SUBREDDITS=("productivity" "getdisciplined" "DecidingToBeBetter" "StudyTips" "GetStudying")

# Keywords for relevance
KEYWORDS=("productivity" "focus" "screen time" "gamification" "phone addiction" "study" "discipline" "digital minimalism" "streak" "accountability" "motivation")

# 4. Fetch and process posts
POSTS_FILE=$(mktemp)
ALL_POSTS="[]"

for sub in "${SUBREDDITS[@]}"; do
  echo "Fetching r/$sub ..."
  URL="https://www.reddit.com/r/$sub/top.json?t=day&limit=5"
  RESPONSE=$(curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "$URL")
  
  # Extract posts array and iterate
  echo "$RESPONSE" | jq -c '.data.children[].data' | while IFS= read -r post; do
    # Extract fields
    title=$(echo "$post" | jq -r '.title')
    permalink=$(echo "$post" | jq -r '.permalink')
    subreddit=$(echo "$post" | jq -r '.subreddit')
    score=$(echo "$post" | jq -r '.score')
    num_comments=$(echo "$post" | jq -r '.num_comments')
    upvote_ratio=$(echo "$post" | jq -r '.upvote_ratio')
    created=$(echo "$post" | jq -r '.created')
    selftext=$(echo "$post" | jq -r '.selftext' | head -c 200)
    url=$(echo "$post" | jq -r '.url // empty')
    post_hint=$(echo "$post" | jq -r '.post_hint // empty')
    is_gallery=$(echo "$post" | jq -r '.is_gallery // false')
    media_metadata=$(echo "$post" | jq -c '.media_metadata // empty')
    
    # Initialize media_sources array
    media_sources="[]"
    
    # Download images if applicable
    if [[ "$post_hint" == "image" ]] && [[ "$url" =~ \.(jpg|jpeg|png|gif)$ ]]; then
      filename=$(basename "$url")
      filename=$(echo "$filename" | sed 's/[^a-zA-Z0-9._-]/_/g')
      filepath="$TODAY-media/$filename"
      fullpath="$MEDIA_DIR/$filename"
      
      if curl -s -L -o "$fullpath" "$url"; then
        size=$(wc -c < "$fullpath")
        if [ "$size" -gt 1024 ]; then
          media_sources=$(echo "$media_sources" | jq --arg fp "$filepath" '. + [$fp]')
          echo "  Downloaded image: $filename"
        fi
      fi
    fi
    
    # Handle galleries
    if [[ "$is_gallery" == "true" ]]; then
      if [ "$media_metadata" != "null" ]; then
        ids=$(echo "$media_metadata" | jq -r 'keys[]')
        count=0
        for id in $ids; do
          img_url=$(echo "$media_metadata" | jq -r ".[$id].p[-1].u")
          if [[ -n "$img_url" ]] && [[ "$img_url" =~ \.(jpg|jpeg|png|gif)$ ]]; then
            ext="${img_url##*.}"
            filename="gallery_${sub}_${count}.$ext"
            filename=$(echo "$filename" | sed 's/[^a-zA-Z0-9._-]/_/g')
            filepath="$TODAY-media/$filename"
            fullpath="$MEDIA_DIR/$filename"
            
            if curl -s -L -o "$fullpath" "$img_url"; then
              size=$(wc -c < "$fullpath")
              if [ "$size" -gt 1024 ]; then
                media_sources=$(echo "$media_sources" | jq --arg fp "$filepath" '. + [$fp]')
                echo "  Downloaded gallery image: $filename"
              fi
            fi
            ((count++))
          fi
        done
      fi
    fi
    
    # Also check if URL itself is an image (i.redd.it)
    if [[ -z "$post_hint" ]] && [[ "$url" =~ i\.redd\.it/.*\.(jpg|jpeg|png|gif) ]]; then
      filename=$(basename "$url")
      filename=$(echo "$filename" | sed 's/[^a-zA-Z0-9._-]/_/g')
      filepath="$TODAY-media/$filename"
      fullpath="$MEDIA_DIR/$filename"
      
      if [ ! -f "$fullpath" ]; then
        if curl -s -L -o "$fullpath" "$url"; then
          size=$(wc -c < "$fullpath")
          if [ "$size" -gt 1024 ]; then
            media_sources=$(echo "$media_sources" | jq --arg fp "$filepath" '. + [$fp]')
            echo "  Downloaded direct image: $filename"
          fi
        fi
      fi
    fi
    
    # Build post object
    post_obj=$(jq -n \
      --arg title "$title" \
      --arg permalink "$permalink" \
      --arg subreddit "$subreddit" \
      --argjson score "$score" \
      --argjson num_comments "$num_comments" \
      --arg upvote_ratio "$upvote_ratio" \
      --arg created "$created" \
      --arg selftext "$selftext" \
      --argjson media_sources "$media_sources" \
      '{
        title: $title,
        permalink: $permalink,
        subreddit: $subreddit,
        score: $score,
        num_comments: $num_comments,
        upvote_ratio: ($upvote_ratio|tonumber),
        created: ($created|tonumber),
        selftext: $selftext,
        media_sources: $media_sources
      }')
    
    # Append to temporary file
    echo "$post_obj" >> "$POSTS_FILE"
  done
done

# Combine all posts into array
ALL_POSTS=$(jq -s '.' "$POSTS_FILE")
rm "$POSTS_FILE"

# Save raw data
echo "$ALL_POSTS" | jq '.' > "$TEMP_JSON"
echo "Saved raw posts to $TEMP_JSON"

# 5. Calculate viral scores and sort
POSTS_WITH_SCORES=$(echo "$ALL_POSTS" | jq -c '.[]' | while IFS= read -r p; do
  score=$(echo "$p" | jq -r '.score')
  num_comments=$(echo "$p" | jq -r '.num_comments')
  upvote_ratio=$(echo "$p" | jq -r '.upvote_ratio')
  title=$(echo "$p" | jq -r '.title')
  selftext=$(echo "$p" | jq -r '.selftext')
  
  # Raw points (0-10)
  raw_points=$(echo "$score" | awk '{v=($1>5000?5000:$1)/500; printf "%.1f", v}')
  
  # Engagement (cap 3)
  engagement=$(echo "$score $num_comments" | awk '{e=($2/($1+1))*100*0.03; if(e>3) e=3; printf "%.1f", e}')
  
  # Upvote ratio points (max 10)
  ratio_points=$(echo "$upvote_ratio" | awk '{v=$1*10; if(v>10) v=10; printf "%.1f", v}')
  
  # Relevance (count distinct keywords)
  combined=$(echo "$title $selftext" | tr '[:upper:]' '[:lower:]')
  relevance=0
  found=0
  for kw in "${KEYWORDS[@]}"; do
    if echo "$combined" | grep -q "$kw"; then
      ((found++))
    fi
  done
  if [ "$found" -gt 3 ]; then found=3; fi
  relevance=$found
  
  # Total and final viral score
  total=$(echo "$raw_points $engagement $ratio_points $relevance" | awk '{printf "%.1f", $1+$2+$3+$4}')
  viral_score=$(echo "$total" | awk '{v=$1/2.6; printf "%.1f", v}')
  
  # Build updated post with scores
  echo "$p" | jq --argjson raw "$raw_points" \
                  --argjson eng "$engagement" \
                  --argjson ratio "$ratio_points" \
                  --argjson rel "$relevance" \
                  --argjson vs "$viral_score" \
                  '. + {raw_points: $raw, engagement_points: $eng, ratio_points: $ratio, relevance_bonus: $rel, viral_score: $vs}'
done)

# Sort by viral_score descending
SORTED_POSTS=$(echo "$POSTS_WITH_SCORES" | jq -s 'sort_by(.viral_score) | reverse')

# 6. Generate report
REPORT="$DAILY_DIR/$TODAY.md"
echo "# Reddit Scout Report: Focus Timer Opportunities" > "$REPORT"
echo "**Date:** $TODAY" >> "$REPORT"
echo "" >> "$REPORT"
echo "## Top Opportunities" >> "$REPORT"
echo "" >> "$REPORT"

# Top 5
echo "$SORTED_POSTS" | jq -r '
  .[0:5] | to_entries |
  .[] |
  "### \(.key+1). [\(.value.title)](https://www.reddit.com\(.value.permalink))\n" +
  "Subreddit: r/\(.value.subreddit) | Score: \(.value.score) | Comments: \(.value.num_comments) | Upvote ratio: \(.value.upvote_ratio * 100 | round)%\n" +
  "Posted: ~\(((now - .value.created) / 3600 | floor)) hours ago\n\n" +
  "**Summary:** \(.value.selftext | if length > 200 then .[0:200] + "..." else . end)\n\n" +
  "**Viral Score:** \(.value.viral_score)/10\n" +
  "- Raw score: \(.value.raw_points)/10\n" +
  "- Engagement: \(.value.engagement_points)/10\n" +
  "- Upvote ratio: \(.value.ratio_points)/10\n" +
  "- Relevance bonus: \(.value.relevance_bonus)/3\n\n" +
  "**Media:**\n" +
  (if (.value.media_sources | length) > 0 then
    (.value.media_sources | map("![](" + . + ")") | join("\n"))
   else
    "No media"
   end) + "\n"
' >> "$REPORT"

# Honorable Mentions (posts 6-10)
echo "## Honorable Mentions" >> "$REPORT"
echo "$SORTED_POSTS" | jq -r '.[5:10] | to_entries[] | "### \(.key+6). [\(.value.title)](https://www.reddit.com\(.value.permalink)) (r/\(.value.subreddit) | \(.value.score) upvotes) – \(.value.selftext | gsub("\\n";" ") | .[0:100])..."' >> "$REPORT"
echo "" >> "$REPORT"

# Media Summary
echo "## Media Summary" >> "$REPORT"
echo "Downloaded images ($TODAY-media/):" >> "$REPORT"
for file in "$MEDIA_DIR"/*; do
  if [ -f "$file" ]; then
    fname=$(basename "$file")
    size_kb=$(wc -c < "$file" | awk '{printf "%.1f", $1/1024}')
    echo "- **$fname** ($size_kb KB)" >> "$REPORT"
    echo "  ![]($TODAY-media/$fname)" >> "$REPORT"
  fi
done

# GitHub link
echo "" >> "$REPORT"
echo "---" >> "$REPORT"
echo "**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/$TODAY.md" >> "$REPORT"

echo "Report generated: $REPORT"

# 7. Upload to GitHub
if [ -f "$HOME/.openclaw/.env" ]; then
  source "$HOME/.openclaw/.env"
  TOKEN="${GITHUB_TOKEN:-${GITHUB_OAUTH_TOKEN:-}}"
  if [ -n "$TOKEN" ]; then
    BASE="https://api.github.com/repos/ozlemsultan90-cmyk/reddit-scout-reports/contents"
    
    # Upload media files to reports/$TODAY-media/
    mkdir -p "$MEDIA_DIR"
    for file in "$MEDIA_DIR"/*; do
      if [ -f "$file" ]; then
        fname=$(basename "$file")
        echo "Uploading $fname to GitHub..."
        base64_content=$(base64 -i "$file" | tr -d '\n')
        path="reports/$TODAY-media/$fname"
        # Check existing SHA
        sha=$(curl -s -H "Authorization: token $TOKEN" "$BASE/$path" | grep -o '"sha":"[^"]*"' | cut -d'"' -f4 || echo "")
        if [ -n "$sha" ]; then
          curl -s -X PUT -H "Authorization: token $TOKEN" -d "{\"message\":\"Add $fname\",\"content\":\"$base64_content\",\"sha\":\"$sha\"}" "$BASE/$path" > /dev/null || echo "  Warning: failed to upload $fname"
        else
          curl -s -X PUT -H "Authorization: token $TOKEN" -d "{\"message\":\"Add $fname\",\"content\":\"$base64_content\"}" "$BASE/$path" > /dev/null || echo "  Warning: failed to upload $fname"
        fi
      fi
    done
    
    # Upload report
    report_path="reports/$TODAY.md"
    echo "Uploading report to GitHub..."
    report_base64=$(base64 -i "$REPORT" | tr -d '\n')
    report_sha=$(curl -s -H "Authorization: token $TOKEN" "$BASE/$report_path" | grep -o '"sha":"[^"]*"' | cut -d'"' -f4 || echo "")
    if [ -n "$report_sha" ]; then
      curl -s -X PUT -H "Authorization: token $TOKEN" -d "{\"message\":\"Update Reddit Scout report for $TODAY\",\"content\":\"$report_base64\",\"sha\":\"$report_sha\"}" "$BASE/$report_path" > /dev/null && echo "  Report uploaded successfully"
    else
      curl -s -X PUT -H "Authorization: token $TOKEN" -d "{\"message\":\"New Reddit Scout report for $TODAY\",\"content\":\"$report_base64\"}" "$BASE/$report_path" > /dev/null && echo "  Report uploaded successfully"
    fi
  else
    echo "GitHub token not found; skipping upload."
  fi
else
  echo "No .env file; skipping upload."
fi

# 8. Output final report
cat "$REPORT"
