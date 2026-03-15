#!/bin/bash
set -euo pipefail

# Get today's date in Europe/Istanbul timezone
TODAY=$(TZ='Europe/Istanbul' date +'%Y-%m-%d')
BASE_DIR="/Users/ozlemsultan/.openclaw/workspace/reddit-productivity"
DAILY_DIR="$BASE_DIR/daily"
MEDIA_DIR="$DAILY_DIR/${TODAY}-media"
TEMP_FILE="$DAILY_DIR/_temp_posts.json"
REPORT_FILE="$DAILY_DIR/${TODAY}.md"

mkdir -p "$MEDIA_DIR"

SUBREDDITS=("productivity" "getdisciplined" "DecidingToBeBetter" "StudyTips" "GetStudying")
KEYWORDS_JSON=$(printf '%s\n' "productivity" "focus" "screen time" "gamification" "phone addiction" "study" "discipline" "digital minimalism" "streak" "accountability" "motivation" | jq -R . | jq -s '.')

echo "Fetching posts..." >&2
> /tmp/posts_numbered.txt
idx=0
for sub in "${SUBREDDITS[@]}"; do
    echo " - r/$sub" >&2
    curl -s -H "User-Agent: RedditScout/1.0" "https://www.reddit.com/r/${sub}/top.json?t=day&limit=5" | \
        jq -c '.data.children[].data' | while IFS= read -r post; do
            echo "$idx|$post" >> /tmp/posts_numbered.txt
            idx=$((idx+1))
    done
done

cut -d'|' -f2- /tmp/posts_numbered.txt > /tmp/posts_raw.txt
echo "[" > /tmp/all_posts.json
paste -sd',' /tmp/posts_raw.txt >> /tmp/all_posts.json
echo "]" >> /tmp/all_posts.json
jq '.' /tmp/all_posts.json > "$TEMP_FILE"

echo "Downloading images..." >&2
> /tmp/downloaded_media.txt

while IFS='|' read -r idx post_line; do
    subreddit=$(echo "$post_line" | jq -r '.subreddit')
    url=$(echo "$post_line" | jq -r '.url // empty')
    post_hint=$(echo "$post_line" | jq -r '.post_hint // empty')
    is_gallery=$(echo "$post_line" | jq -r '.is_gallery // false')
    media_metadata=$(echo "$post_line" | jq -c '.media_metadata // empty')

    img_ext="jpg jpeg png gif webp"
    url_lc=$(echo "$url" | tr '[:upper:]' '[:lower:]')

    download() {
        local u=$1
        local proposed=$2
        local ext="${proposed##*.}"
        local filename="${subreddit}_${idx}.${ext}"
        local filepath="$MEDIA_DIR/$filename"
        if [ ! -f "$filepath" ]; then
            curl -s -L "$u" -o "$filepath"
            if [ -s "$filepath" ] && [ $(stat -f%z "$filepath" 2>/dev/null || echo 0) -gt 1024 ]; then
                echo "$idx:$filename" >> /tmp/downloaded_media.txt
            else
                rm -f "$filepath"
            fi
        else
            echo "$idx:$filename" >> /tmp/downloaded_media.txt
        fi
    }

    for ext in $img_ext; do
        if [[ "$url_lc" == *."$ext" ]]; then
            download "$url" "$url"
            break
        fi
    done

    if ! grep -q "^$idx:" /tmp/downloaded_media.txt 2>/dev/null; then
        if [ "$post_hint" = "image" ]; then
            for ext in $img_ext; do
                if [[ "$url_lc" == *."$ext" ]]; then
                    download "$url" "$url"
                    break
                fi
            done
        fi
    fi

    if ! grep -q "^$idx:" /tmp/downloaded_media.txt 2>/dev/null; then
        if [ "$is_gallery" = "true" ] && [ -n "$media_metadata" ] && [ "$media_metadata" != "null" ]; then
            echo "$media_metadata" | jq -c 'to_entries[]' | while read -r entry; do
                img_url=$(echo "$entry" | jq -r '.value.s.u // empty')
                if [ -n "$img_url" ]; then
                    media_id=$(echo "$entry" | jq -r '.key')
                    img_url_lc=$(echo "$img_url" | tr '[:upper:]' '[:lower:]')
                    if [[ "$img_url_lc" =~ \.(jpg|jpeg|png|gif|webp)$ ]]; then
                        ext="${img_url##*.}"
                        filename="${subreddit}_${idx}_${media_id}.${ext}"
                        filepath="$MEDIA_DIR/$filename"
                        if [ ! -f "$filepath" ]; then
                            curl -s -L "$img_url" -o "$filepath"
                            if [ -s "$filepath" ] && [ $(stat -f%z "$filepath" 2>/dev/null || echo 0) -gt 1024 ]; then
                                echo "$idx:$filename" >> /tmp/downloaded_media.txt
                                break
                            else
                                rm -f "$filepath"
                            fi
                        else
                            echo "$idx:$filename" >> /tmp/downloaded_media.txt
                            break
                        fi
                    fi
                fi
            done
        fi
    fi
done < /tmp/posts_numbered.txt

echo "Building media map..." >&2
if [ -s /tmp/downloaded_media.txt ]; then
    jq -n -R 'reduce inputs as $line ({}; .[$line|split(":")[0]] = (.[$line|split(":")[0]] + [$line|split(":")[1]] // [$line|split(":")[1]]))' \
        < /tmp/downloaded_media.txt > /tmp/media_map.json
else
    echo '{}' > /tmp/media_map.json
fi

echo "Processing scores and sorting..." >&2
jq -n \
      --argjson posts "$(cat "$TEMP_FILE")" \
      --argjson keywords "$KEYWORDS_JSON" \
      --argjson media_map "$(cat /tmp/media_map.json)" \
      -f "$BASE_DIR/process_no_reduce.jq" > "$TEMP_FILE.sorted"

echo "Writing report..." >&2
{
    echo "# Reddit Scout Report: Focus Timer Opportunities"
    echo "**Date:** $TODAY"
    echo ""
    echo "## Top Opportunities"
    echo ""

    jq -r '
      range(0;5) as $i |
      .[$i] as $p |
      [
        "### \($i+1). [\($p.title)](https://www.reddit.com\($p.permalink))",
        "Subreddit: r/\($p.subreddit) | Score: \($p.score) | Comments: \($p.num_comments) | Upvote ratio: \($p.upvote_ratio|floor)%",
        "Posted: ~\($p.hours_ago) hours ago",
        "",
        "**Summary:** \($p.selftext[:200] // "")",
        "",
        "**Viral Score:** \($p.viral_score)/10",
        "- Raw score: \($p.raw_points)/10",
        "- Engagement: \($p.engagement_points)/10",
        "- Upvote ratio: \($p.ratio_points)/10",
        "- Relevance bonus: \($p.relevance_bonus)/3",
        ""
      ] + ( if ($p.media_sources|length) > 0 then ["**Media:**"] + ( $p.media_sources | map("![Image](\(.))") ) + [""] else [] end ) | join("\n")
    ' "$TEMP_FILE.sorted"

    echo ""

    jq -r '
      range(5;10) as $i |
      .[$i] as $p |
      "### \($i+1). [\($p.title)](https://www.reddit.com\($p.permalink)) (r/\($p.subreddit) | \($p.score) upvotes) – \($p.selftext[:100] // "")."
    ' "$TEMP_FILE.sorted"

    echo ""
    echo "## Media Summary"
    echo "Downloaded images ($TODAY-media/):"
    if [ -d "$MEDIA_DIR" ]; then
        if [ "$(ls -A "$MEDIA_DIR" 2>/dev/null)" ]; then
            find "$MEDIA_DIR" -type f | while read -r file; do
                fname=$(basename "$file")
                size_kb=$(( $(stat -f%z "$file" 2>/dev/null || echo 0) / 1024 ))
                echo "- **$fname** ($size_kb KB)"
                echo "  ![Description]($TODAY-media/$fname)"
            done
        else
            echo "*No images downloaded*"
        fi
    else
        echo "*Media directory not found*"
    fi

    echo ""
    echo "---"
    echo "**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/$TODAY.md"
} > "$REPORT_FILE"

if [ -s "$REPORT_FILE" ]; then
    # Upload to GitHub
    GITHUB_TOKEN=$(grep -E '^GITHUB_TOKEN=' ~/.openclaw/.env 2>/dev/null | cut -d= -f2-)
    if [ -z "$GITHUB_TOKEN" ]; then
        echo "GitHub token not found, skipping upload." >&2
    else
        BASE="https://api.github.com/repos/ozlemsultan90-cmyk/reddit-scout-reports/contents"
        # Upload media files (with temp JSON to avoid command-line size limits)
        if [ -d "$MEDIA_DIR" ] && [ "$(ls -A "$MEDIA_DIR" 2>/dev/null)" ]; then
            cd "$MEDIA_DIR" || exit 1
            for file in *; do
                [ -f "$file" ] || continue
                echo "Uploading media: $file" >&2
                b64=$(base64 -i "$file" | tr -d '\n')
                path="reports/${TODAY}-media/$file"
                sha=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "$BASE/$path" | grep -o '"sha":"[^"]*"' | cut -d'"' -f2 || echo "")
                tmp=$(mktemp)
                if [ -n "$sha" ]; then
                    printf '{"message":"Update %s","content":"%s","sha":"%s"}' "$file" "$b64" "$sha" > "$tmp"
                else
                    printf '{"message":"Add %s","content":"%s"}' "$file" "$b64" > "$tmp"
                fi
                curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
                    --data-binary @"$tmp" \
                    "$BASE/$path" > /dev/null
                rm -f "$tmp"
            done
            cd - > /dev/null
        fi
        # Upload report
        echo "Uploading report: ${TODAY}.md" >&2
        report_path="reports/${TODAY}.md"
        b64=$(base64 -i "$REPORT_FILE" | tr -d '\n')
        sha=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "$BASE/$report_path" | grep -o '"sha":"[^"]*"' | cut -d'"' -f2 || echo "")
        tmp=$(mktemp)
        if [ -n "$sha" ]; then
            printf '{"message":"Update Reddit Scout report for %s","content":"%s","sha":"%s"}' "$TODAY" "$b64" "$sha" > "$tmp"
        else
            printf '{"message":"New Reddit Scout report for %s","content":"%s"}' "$TODAY" "$b64" > "$tmp"
        fi
        curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
            --data-binary @"$tmp" \
            "$BASE/$report_path"
        rm -f "$tmp"
        echo "GitHub upload complete." >&2
    fi
    # Output the report to stdout
    cat "$REPORT_FILE"
else
    echo "Report generation failed." >&2
    exit 1
fi
