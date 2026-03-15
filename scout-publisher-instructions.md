# Reddit Scout - Publisher Phase

Your mission: Take the raw data collected and produce the final formatted markdown report, then upload it to GitHub.

## Input
Read the file `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/_temp_posts.json`. It contains an array of post objects with fields:
- title, permalink, subreddit, score, num_comments, upvote_ratio, created, selftext
- local_image_path (string or array of strings) relative to the daily folder

## Processing Steps

1. **Calculate Viral Score** for each post (1-10 scale):
   - Raw score: `min(score, 5000) / 500` (0-10)
   - Engagement: `(num_comments / (score + 1)) * 100` → map to 0-3 points (multiply by 0.03, cap at 3)
   - Upvote ratio: `upvote_ratio * 10` (max 10)
   - Relevance bonus: 0-3 points. Check title+selftext for keywords: productivity, focus, screen time, gamification, phone addiction, study, discipline, digital minimalism. Count distinct matches (case-insensitive): 0→0, 1→1, 2→2, 3+→3.
   - Total = sum of four components (max ~23). Normalize to 1-10: `total * 10 / 23`? Actually we want 1-10. Simpler: total / 2.3 (since max ~23) rounded to 1 decimal. Or: keep as is then scale: `virality = total / 2.3`. We'll compute: `viral_score = round((raw + engagement + ratio + relevance) / 2.3, 1)` (max 10).

2. **Sort posts** by descending viral_score.

3. **Top 5 posts (main section)** — format each EXACTLY:

```
### 1. [POST TITLE](https://www.reddit.com{permalink})
Subreddit: r/{subreddit} | Score: {score} | Comments: {num_comments} | Upvote ratio: {upvote_ratio:.0%}
Posted: ~{hours_ago} hours ago (based on created timestamp)

**Summary:** {selftext (first 200 chars, 2-3 sentences, max 200 chars)}

**Viral Score:** {viral_score:.1f}/10
- Raw score: {raw_points:.1f}/10
- Engagement: {engagement_points:.1f}/10
- Upvote ratio: {ratio_points:.1f}/10
- Relevance bonus: {relevance_bonus}/3

**Media:**
{media_markdown}
```

Where `media_markdown`:
- If `local_image_path` is a string: `![Alt text describing image]({local_image_path})`
- If array: for each path: `![Alt {i}]({path})`
- If no image: omit the **Media:** line entirely.

Use meaningful alt text: e.g., `Study motivation meme from r/StudyTips` or `Infographic about spaced repetition`.

4. **Honorable mentions** (remaining posts, up to 5). Format:

```
6. **[Post title](https://www.reddit.com{permalink})** (r/{subreddit} | {score} upvotes) – {one-line summary (first 100 chars)}.
```

Continue numbering from after the top 5.

5. **Media Summary**: List all downloaded images with embedded thumbnails.

```
## Media Summary
Downloaded images (YYYY-MM-DD-media/):
- **filename.jpg** (size KB)
  ![Description](YYYY-MM-DD-media/filename.jpg)
```

Iterate over all files in `YYYY-MM-DD-media/`. Get file size via `stat -f%z` (macOS) or `stat -c%s`. Use a concise description: subreddit + post title snippet.

6. **Compose full report**:
   - Header: `# Reddit Scout Report: Focus Timer Opportunities` and date line `**Date:** YYYY-MM-DD`
   - Then the formatted sections

7. **Save** to `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/YYYY-MM-DD.md`.

8. **Upload to GitHub** (run as shell commands):
   - Repo: `ozlemsultan90-cmyk/reddit-scout-reports`
   - Path: `reports/YYYY-MM-DD.md`
   - Use:
     ```
     export GITHUB_TOKEN=$(grep '^GITHUB_TOKEN' ~/.openclaw/.env | cut -d'=' -f2)
     SHA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/ozlemsultan90-cmyk/reddit-scout-reports/contents/reports/YYYY-MM-DD.md" | grep -o '"sha":"[^"]*"' | cut -d'"' -f4 || echo "")
     CONTENT=$(base64 -i /Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/YYYY-MM-DD.md | tr -d '\n')
     if [ -n "$SHA" ]; then
       curl -X PUT -H "Authorization: token $GITHUB_TOKEN" -d "{\"message\":\"Update Reddit Scout report for $(date +%Y-%m-%d)\",\"content\":\"$CONTENT\",\"sha\":\"$SHA\"}" "https://api.github.com/repos/ozlemsultan90-cmyk/reddit-scout-reports/contents/reports/$(date +%Y-%m-%d).md"
     else
       curl -X PUT -H "Authorization: token $GITHUB_TOKEN" -d "{\"message\":\"New Reddit Scout report for $(date +%Y-%m-%d)\",\"content\":\"$CONTENT\"}" "https://api.github.com/repos/ozlemsultan90-cmyk/reddit-scout-reports/contents/reports/$(date +%Y-%m-%d).md"
     fi
     ```
   - If curl returns a JSON with `"sha"`, upload succeeded. Otherwise, print error to stderr but continue.

9. **Final Output**: Your entire response must be the raw contents of the markdown report file (read it and output). Do not add any extra text or formatting around it. The OpenClaw system will send this as the Telegram message.

## Rules
- Headings must be clickable links.
- Images must be embedded with `![]()`.
- No bullet lists for top posts; use the heading template.
- No separate "View" links; title IS the link.
- All downloaded images must appear in the Media Summary and in their respective post's Media section.
- Strict adherence to templates ensures consistent formatting.
