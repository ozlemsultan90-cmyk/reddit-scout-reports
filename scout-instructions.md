# Reddit Scout - Complete Report Generator

Your mission: Collect Reddit data, download images, format a markdown report, upload everything to GitHub, and output the final report.

## Steps

1. **Determine today's date** in Europe/Istanbul timezone. Format: YYYY-MM-DD.

2. **Read subreddits** from `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/subreddits.md`. Use the first 5 subreddits.

3. **Fetch top posts** from each subreddit: `https://www.reddit.com/r/{subreddit}/top.json?t=day&limit=5`.

4. **Extract fields** per post:
   - title, permalink, subreddit, score, num_comments, upvote_ratio, created, selftext (first 200 chars)
   - url, post_hint, is_gallery, media_metadata
   - Initialize `media_sources: []`
   Store all posts in an array `posts`.

5. **Download images** for posts that have them:
   - Create folder: `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/$TODAY-media/`
   - Conditions for having an image:
     - `post_hint === "image"` and `url` ends with image extension
     - `is_gallery === true` (download each from `media_metadata`)
     - `url` itself ends with image extension (i.redd.it links)
   - Download with `curl -L -o`, verify > 1024 bytes.
   - Record downloaded file paths in `media_sources` as `YYYY-MM-DD-media/filename.ext`.

6. **Save raw data** to `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/_temp_posts.json`.

7. **Calculate Viral Score** (1-10):
   - Raw: `min(score, 5000) / 500` (0-10)
   - Engagement: `(num_comments / (score + 1)) * 100 * 0.03` (cap 3, later scaled)
   - Upvote ratio: `upvote_ratio * 10` (max 10)
   - Relevance: count distinct keywords (productivity, focus, screen time, gamification, phone addiction, study, discipline, digital minimalism, streak, accountability, motivation) in title+selftext; each distinct adds 1 (max 3).
   - Total = raw + engagement + ratio + relevance (max ~26). Final: `viral_score = round(total / 2.6, 1)`.

8. **Sort posts** by descending `viral_score`.

9. **Format report** and write to `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/$TODAY.md`:

```
# Reddit Scout Report: Focus Timer Opportunities
**Date:** YYYY-MM-DD

## Top Opportunities

### 1. [POST TITLE](https://www.reddit.com{permalink})
Subreddit: r/{subreddit} | Score: {score} | Comments: {num_comments} | Upvote ratio: {upvote_ratio:.0%}
Posted: ~{hours_ago} hours ago

**Summary:** {selftext (first 200 chars, 2-3 sentences)}

**Viral Score:** {viral_score:.1f}/10
- Raw score: {raw_points:.1f}/10
- Engagement: {engagement_points:.1f}/10
- Upvote ratio: {ratio_points:.1f}/10
- Relevance bonus: {relevance_bonus}/3

**Media:**
{for each path in media_sources: ![Alt](path)}
```

Top 5 posts. Then Honorable Mentions (posts 6‑10):

```
### 6. [Post title](https://www.reddit.com{permalink}) (r/{subreddit} | {score} upvotes) – {one‑line summary (first 100 chars)}.
```

Media Summary:

```
## Media Summary
Downloaded images (YYYY-MM-DD-media/):
- **filename.jpg** (size KB)
  ![Description](YYYY-MM-DD-media/filename.jpg)
```

List all files in `YYYY-MM-DD-media/` (read filesystem), show size in KB, embed each.

**At the very end**, add:

```
---
**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/YYYY-MM-DD.md
```

10. **Upload to GitHub** (use token from `~/.openclaw/.env`).

   - Base URL: `https://api.github.com/repos/ozlemsultan90-cmyk/reddit-scout-reports/contents`
   - First, **upload all media files** to `reports/YYYY-MM-DD-media/`:
     - For each file in that directory:
       - `BASE64=$(base64 -i "$file" | tr -d '\n')`
       - Check existing: `SHA=$(curl -s -H "Authorization: token $TOKEN" "$BASE/reports/YYYY-MM-DD-media/$filename" | grep -o '"sha":"[^"]*"' | cut -d'"' -f4 || echo "")`
       - If SHA: `curl -X PUT -H "Authorization: token $TOKEN" -d "{\"message\":\"Add $filename\",\"content\":\"$BASE64\",\"sha\":\"$SHA\"}" "$BASE/reports/YYYY-MM-DD-media/$filename"`
       - Else: `curl -X PUT -H "Authorization: token $TOKEN" -d "{\"message\":\"Add $filename\",\"content\":\"$BASE64\"}" "$BASE/reports/YYYY-MM-DD-media/$filename"`
       - Verify JSON contains `"sha"`; if not, log error but continue.
   - Then **upload the report** to `reports/YYYY-MM-DD.md`:
     - `BASE64=$(base64 -i "$REPORT" | tr -d '\n')`
     - Get existing SHA if any.
     - PUT with message `Update Reddit Scout report for YYYY-MM-DD` (or "New...").
     - Verify success.

11. **Final Output**: Read `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/$TODAY.md` and output its full contents as your final message (this includes the GitHub link at the bottom).

## Rules
- Top post headings: `### N. [Title](permalink)` — title must be clickable, no quotes.
- All downloaded images must appear in post Media sections AND in Media Summary.
- Use relative paths `YYYY-MM-DD-media/filename.ext`.
- Markdown must be valid.
- Do not add any extra text outside the report contents in your final output.
