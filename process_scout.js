#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const TODAY = '2026-03-18';
const MEDIA_DIR = path.join('/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily', `${TODAY}-media`);
const TEMP_JSON = path.join('/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily', '_temp_posts.json');
const REPORT_FILE = path.join('/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily', `${TODAY}.md`);

const subreddits = ['productivity', 'getdisciplined', 'DecidingToBeBetter', 'StudyTips', 'GetStudying'];
const allPosts = [];

subreddits.forEach(sub => {
  try {
    // Use old.reddit.com with a user-agent to reduce rate limiting
    const url = `https://old.reddit.com/r/${sub}/top.json?t=day&limit=5`;
    const cmd = `curl -s -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "${url}"`;
    const jsonStr = execSync(cmd, { encoding: 'utf8' });
    const data = JSON.parse(jsonStr);
    const children = data.data?.children || [];
    children.forEach(child => {
      const post = child.data;
      const media_sources = [];

      // Conditions for image: post_hint === "image" and url ends with image extension, or is_gallery, or url ends with i.redd.it
      const url = post.url || '';
      const post_hint = post.post_hint;
      const is_gallery = post.is_gallery === true;
      const isImageUrl = /\.(jpg|jpeg|png|gif|webp)$/i.test(url);

      if ((post_hint === 'image' && isImageUrl) || is_gallery || isImageUrl) {
        // Determine filename
        let filename = '';
        if (is_gallery && post.media_metadata) {
          // For gallery, download first image or all? We'll download each but for simplicity, note multiple
          // We'll handle gallery download later
        } else if (url) {
          filename = path.basename(url);
          // Sanitize filename
          filename = filename.replace(/[^a-zA-Z0-9._-]/g, '_');
          if (!filename) filename = `${post.id}_image.jpg`;
        }
        if (filename) {
          media_sources.push(`${TODAY}-media/${filename}`);
        }
      }

      allPosts.push({
        title: post.title || '',
        permalink: post.permalink || '',
        subreddit: post.subreddit || sub,
        score: post.score || 0,
        num_comments: post.num_comments || 0,
        upvote_ratio: post.upvote_ratio || 1,
        created: post.created ? new Date(post.created * 1000).toISOString() : '',
        selftext: post.selftext ? post.selftext.substring(0, 200) : '',
        url: url,
        post_hint: post_hint || '',
        is_gallery: is_gallery,
        media_metadata: post.media_metadata || null,
        media_sources: media_sources
      });
    });
  } catch (e) {
    console.error(`Error processing ${sub}:`, e.message);
  }
});

// Save raw data
fs.writeFileSync(TEMP_JSON, JSON.stringify(allPosts, null, 2));

// Download images
allPosts.forEach(post => {
  if (post.is_gallery && post.media_metadata) {
    // For gallery, download each image
    const metadata = post.media_metadata;
    const ids = Object.keys(metadata);
    ids.forEach((id, idx) => {
      const item = metadata[id];
      if (item.s && item.m) {
        const ext = item.m.includes('png') ? 'png' : 'jpg';
        const filename = `${post.id}_${idx}.${ext}`;
        const dest = path.join(MEDIA_DIR, filename);
        const src = `https://i.redd.it/${id}.${ext}`;
        try {
          execSync(`curl -L -o "${dest}" "${src}"`);
          // Verify size > 1024
          const stats = fs.statSync(dest);
          if (stats.size > 1024) {
            post.media_sources.push(`${TODAY}-media/${filename}`);
          } else {
            fs.unlinkSync(dest);
          }
        } catch (e) {
          // ignore errors
        }
      }
    });
  } else if (post.media_sources.length > 0) {
    const [relPath] = post.media_sources;
    const filename = path.basename(relPath);
    const dest = path.join(MEDIA_DIR, filename);
    if (fs.existsSync(dest)) {
      // Already perhaps downloaded
    } else {
      try {
        execSync(`curl -L -o "${dest}" "${post.url}"`);
        const stats = fs.statSync(dest);
        if (stats.size <= 1024) {
          fs.unlinkSync(dest);
          post.media_sources = post.media_sources.filter(() => false);
        }
      } catch (e) {
        post.media_sources = post.media_sources.filter(() => false);
      }
    }
  }
});

// Keyword list for relevance
const keywords = ['productivity', 'focus', 'screen time', 'gamification', 'phone addiction', 'study', 'discipline', 'digital minimalism', 'streak', 'accountability', 'motivation'];
function countRelevance(text) {
  const lower = text.toLowerCase();
  let count = 0;
  keywords.forEach(kw => {
    if (lower.includes(kw)) count++;
  });
  return Math.min(count, 3);
}

// Calculate viral score
allPosts.forEach(post => {
  const rawScore = Math.min(post.score, 5000) / 500; // 0-10
  const engagement = Math.min(((post.num_comments / (post.score + 1)) * 100 * 0.03), 3) * 10 / 3; // scale to max 10? Actually the spec: engagement adds 0-3 points, then total sum scaled. Let's compute raw components as described.
  // Actually spec says: Engagement: (num_comments/(score+1))*100*0.03 => up to ~3, later scaled in total.
  // Then total = raw + engagement + ratio + relevance; final viral_score = round(total/2.6, 1)
  // So we compute components roughly as intended:
  const rawPoints = rawScore; // 0-10
  const engagementRaw = (post.num_comments / (post.score + 1)) * 100 * 0.03; // 0-3 typically
  const ratioPoints = post.upvote_ratio * 10; // max 10
  const relevanceBonus = countRelevance(post.title + ' ' + post.selftext); // 0-3

  const total = rawPoints + engagementRaw + ratioPoints + relevanceBonus; // max ~26
  const viral_score = parseFloat((total / 2.6).toFixed(1));

  post.viral_score = viral_score;
  post.raw_points = parseFloat(rawPoints.toFixed(1));
  post.engagement_points = parseFloat(engagementRaw.toFixed(1));
  post.ratio_points = parseFloat(ratioPoints.toFixed(1));
  post.relevance_bonus = relevanceBonus;
});

// Sort descending by viral_score
allPosts.sort((a, b) => b.viral_score - a.viral_score);

// Format hours ago
function hoursAgo(createdStr) {
  if (!createdStr) return 'unknown';
  const created = new Date(createdStr);
  const now = new Date();
  const diffMs = now - created;
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  return hours;
}

// Build report
let report = `# Reddit Scout Report: Focus Timer Opportunities
**Date:** ${TODAY}

## Top Opportunities

`;

// Top 5
for (let i = 0; i < Math.min(5, allPosts.length); i++) {
  const post = allPosts[i];
  const hours = hoursAgo(post.created);
  const summary = post.selftext || 'No text content.';
  report += `### ${i + 1}. [${post.title}](https://www.reddit.com${post.permalink})
Subreddit: r/${post.subreddit} | Score: ${post.score} | Comments: ${post.num_comments} | Upvote ratio: ${Math.round(post.upvote_ratio * 100)}%
Posted: ~${hours} hours ago

**Summary:** ${summary}

**Viral Score:** ${post.viral_score.toFixed(1)}/10
- Raw score: ${post.raw_points.toFixed(1)}/10
- Engagement: ${post.engagement_points.toFixed(1)}/10
- Upvote ratio: ${post.ratio_points.toFixed(1)}/10
- Relevance bonus: ${post.relevance_bonus}/3

**Media:**
`;
  if (post.media_sources && post.media_sources.length > 0) {
    post.media_sources.forEach(src => {
      report += `![](${src})\n`;
    });
  } else {
    report += `None\n`;
  }
  report += '\n';
}

// Honorable Mentions (posts 6-10)
report += `## Honorable Mentions\n\n`;
for (let i = 5; i < Math.min(10, allPosts.length); i++) {
  const post = allPosts[i];
  const summary = (post.title + ' ' + post.selftext).substring(0, 100).trim();
  report += `### ${i + 1}. [${post.title}](https://www.reddit.com${post.permalink}) (r/${post.subreddit} | ${post.score} upvotes) – ${summary}.\n`;
}
report += '\n';

// Media Summary
report += `## Media Summary\nDownloaded images (${TODAY}-media/):\n`;
try {
  const files = fs.readdirSync(MEDIA_DIR);
  files.forEach(file => {
    const stats = fs.statSync(path.join(MEDIA_DIR, file));
    const sizeKB = (stats.size / 1024).toFixed(1);
    report += `- **${file}** (${sizeKB} KB)\n  ![](${TODAY}-media/${file})\n`;
  });
} catch (e) {
  report += `No media files downloaded.\n`;
}

report += `\n---
**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/${TODAY}.md
`;

fs.writeFileSync(REPORT_FILE, report);
console.log('Report generated at:', REPORT_FILE);