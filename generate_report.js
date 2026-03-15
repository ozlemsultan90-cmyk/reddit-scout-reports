const fs = require('fs');
const path = require('path');
const https = require('https');

// Determine today's date in Europe/Istanbul timezone
const now = new Date();
const options = { timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit' };
const parts = new Intl.DateTimeFormat('en-CA', options).formatToParts(now);
const year = parts.find(p => p.type === 'year').value;
const month = parts.find(p => p.type === 'month').value;
const day = parts.find(p => p.type === 'day').value;
const today = `${year}-${month}-${day}`;

const mediaDir = `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/${today}-media`;
const tempFile = `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/_temp_posts.json`;
const reportFile = `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/${today}.md`;

const keywords = ['productivity', 'focus', 'screen time', 'gamification', 'phone addiction', 'study', 'discipline', 'digital minimalism', 'streak', 'accountability', 'motivation'];

// Load posts
const posts = JSON.parse(fs.readFileSync(tempFile, 'utf8'));

function calculateViralScore(post) {
  const score = post.score || 0;
  const numComments = post.num_comments || 0;
  const upvoteRatio = post.upvote_ratio || 0.5;

  // Raw score (0-10)
  const rawPoints = Math.min(score, 5000) / 500;

  // Engagement (cap 3 before scaling)
  const engagementRaw = (numComments / (score + 1)) * 100 * 0.03;
  const engagementPoints = Math.min(engagementRaw, 3);

  // Upvote ratio (max 10)
  const ratioPoints = upvoteRatio * 10;

  // Relevance bonus (max 3)
  const combinedText = ((post.title || '') + ' ' + (post.selftext || '')).toLowerCase();
  const distinctMatches = new Set();
  for (const kw of keywords) {
    if (combinedText.includes(kw)) {
      distinctMatches.add(kw);
    }
  }
  const relevanceBonus = Math.min(distinctMatches.size, 3);

  // Total scaled to 0-10
  const total = rawPoints + engagementPoints + ratioPoints + relevanceBonus;
  const viralScore = Math.round((total / 2.6) * 10) / 10;

  return {
    viral_score: viralScore,
    raw_points: Math.round(rawPoints * 10) / 10,
    engagement_points: Math.round(engagementPoints * 10) / 10,
    ratio_points: Math.round(ratioPoints * 10) / 10,
    relevance_bonus: relevanceBonus
  };
}

function downloadImage(url, destPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(destPath);
    https.get(url, (response) => {
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        const stats = fs.statSync(destPath);
        if (stats.size > 1024) {
          resolve(destPath);
        } else {
          fs.unlinkSync(destPath);
          reject(new Error('File too small'));
        }
      });
    }).on('error', (err) => {
      file.close();
      if (fs.existsSync(destPath)) fs.unlinkSync(destPath);
      reject(err);
    });
  });
}

async function processPosts() {
  const enrichedPosts = [];

  for (const post of posts) {
    const { viral_score, raw_points, engagement_points, ratio_points, relevance_bonus } = calculateViralScore(post);
    const mediaSources = [];

    // Check for image to download
    const postHint = post.post_hint;
    const isGallery = post.is_gallery === true;
    const url = post.url || '';

    try {
      if (postHint === 'image' && (url.endsWith('.jpg') || url.endsWith('.png') || url.endsWith('.jpeg') || url.endsWith('.gif'))) {
        const filename = path.basename(url.split('?')[0]);
        const dest = path.join(mediaDir, filename);
        if (!fs.existsSync(dest)) {
          await downloadImage(url, dest);
        }
        mediaSources.push(`${today}-media/${filename}`);
      } else if (isGallery && post.media_metadata) {
        for (const [key, item] of Object.entries(post.media_metadata)) {
          const imgUrl = item.s?.u || item.p?.replace('&amp;', '&');
          if (imgUrl) {
            const ext = imgUrl.match(/\.(jpg|jpeg|png|gif)/i)?.[1] || 'jpg';
            const filename = `${key}.${ext}`;
            const dest = path.join(mediaDir, filename);
            if (!fs.existsSync(dest)) {
              await downloadImage(imgUrl, dest);
            }
            mediaSources.push(`${today}-media/${filename}`);
          }
        }
      } else if (url.includes('i.redd.it') && (url.endsWith('.jpg') || url.endsWith('.png') || url.endsWith('.jpeg') || url.endsWith('.gif'))) {
        const filename = path.basename(url.split('?')[0]);
        const dest = path.join(mediaDir, filename);
        if (!fs.existsSync(dest)) {
          await downloadImage(url, dest);
        }
        mediaSources.push(`${today}-media/${filename}`);
      }
    } catch (e) {
      // Continue even if image download fails
      console.error(`Failed to download image for post ${post.id}:`, e.message);
    }

    // Calculate hours ago
    const created = post.created * 1000;
    const now = Date.now();
    const hoursAgo = Math.max(0, Math.floor((now - created) / (1000 * 60 * 60)));

    enrichedPosts.push({
      ...post,
      viral_score,
      raw_points,
      engagement_points,
      ratio_points,
      relevance_bonus,
      mediaSources,
      hours_ago: hoursAgo
    });
  }

  // Sort by viral score descending
  enrichedPosts.sort((a, b) => b.viral_score - a.viral_score);

  return enrichedPosts;
}

function formatReport(topPosts) {
  const lines = [];
  lines.push(`# Reddit Scout Report: Focus Timer Opportunities`);
  lines.push(`**Date:** ${today}`);
  lines.push('');
  lines.push(`## Top Opportunities`);
  lines.push('');

  for (let i = 0; i < Math.min(5, topPosts.length); i++) {
    const post = topPosts[i];
    const rank = i + 1;
    const title = post.title.replace(/[#*_`]/g, '');
    const summary = (post.selftext || '').substring(0, 200).replace(/\n/g, ' ').trim();
    const summary2 = summary.length > 180 ? summary.substring(0, 180) + '...' : summary;

    lines.push(`### ${rank}. [${title}](https://www.reddit.com${post.permalink})`);
    lines.push(`Subreddit: r/${post.subreddit} | Score: ${post.score} | Comments: ${post.num_comments} | Upvote ratio: ${Math.round(post.upvote_ratio * 100)}%`);
    lines.push(`Posted: ~${post.hours_ago} hours ago`);
    lines.push('');
    lines.push(`**Summary:** ${summary2}`);
    lines.push('');
    lines.push(`**Viral Score:** ${post.viral_score.toFixed(1)}/10`);
    lines.push(`- Raw score: ${post.raw_points.toFixed(1)}/10`);
    lines.push(`- Engagement: ${post.engagement_points.toFixed(1)}/10`);
    lines.push(`- Upvote ratio: ${post.ratio_points.toFixed(1)}/10`);
    lines.push(`- Relevance bonus: ${post.relevance_bonus}/3`);
    lines.push('');

    if (post.mediaSources && post.mediaSources.length > 0) {
      lines.push('**Media:**');
      for (const src of post.mediaSources) {
        lines.push(`![](${src})`);
      }
      lines.push('');
    }
  }

  lines.push('## Honorable Mentions');
  lines.push('');
  for (let i = 5; i < Math.min(10, topPosts.length); i++) {
    const post = topPosts[i];
    const title = post.title.replace(/[#*_`]/g, '');
    const summary = (post.selftext || '').substring(0, 100).replace(/\n/g, ' ').trim();
    const summary2 = summary.length > 90 ? summary.substring(0, 90) + '...' : summary;
    lines.push(`### ${i + 1}. [${title}](https://www.reddit.com${post.permalink}) (r/${post.subreddit} | ${post.score} upvotes) – ${summary2}.`);
  }

  lines.push('');
  lines.push('## Media Summary');
  lines.push(`Downloaded images (${today}-media/):`);

  if (fs.existsSync(mediaDir)) {
    const files = fs.readdirSync(mediaDir).filter(f => !f.startsWith('.'));
    for (const file of files) {
      const stats = fs.statSync(path.join(mediaDir, file));
      const sizeKB = Math.round(stats.size / 1024);
      lines.push(`- **${file}** (${sizeKB} KB)`);
      lines.push(`  ![](${today}-media/${file})`);
    }
  } else {
    lines.push('No images downloaded.');
  }

  lines.push('');
  lines.push('---');
  lines.push(`**View on GitHub:** https://github.com/ozlemsultan90-cmyk/reddit-scout-reports/blob/main/reports/${today}.md`);

  return lines.join('\n');
}

async function run() {
  try {
    const topPosts = await processPosts();
    const report = formatReport(topPosts);
    fs.writeFileSync(reportFile, report);
    console.log(`Report generated: ${reportFile}`);
    return report;
  } catch (error) {
    console.error('Error generating report:', error);
    throw error;
  }
}

run();
