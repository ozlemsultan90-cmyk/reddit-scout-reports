const fs = require('fs');
const path = require('path');
const https = require('https');
const { execSync } = require('child_process');

const DATE = '2026-03-16';
const WORKSPACE = '/Users/ozlemsultan/.openclaw/workspace/reddit-productivity';
const DAILY_DIR = path.join(WORKSPACE, 'daily');
const MEDIA_DIR = path.join(DAILY_DIR, `${DATE}-media`);
const REPORTS_DIR = path.join(WORKSPACE, 'reports');
const REPORT_MEDIA_DIR = path.join(REPORTS_DIR, `${DATE}-media`);
const TEMP_JSON = path.join(DAILY_DIR, '_temp_posts.json');

// Ensure directories
fs.mkdirSync(MEDIA_DIR, { recursive: true });
fs.mkdirSync(REPORT_MEDIA_DIR, { recursive: true });

// Read subreddits
const subredditsFile = path.join(WORKSPACE, 'subreddits.md');
const subredditsContent = fs.readFileSync(subredditsFile, 'utf8');
const subredditNames = [];
subredditsContent.split('\n').forEach(line => {
  const match = line.match(/^-\s*r\/([a-zA-Z0-9_]+)/);
  if (match) {
    subredditNames.push(match[1]);
  }
});
const selectedSubs = subredditNames.slice(0, 5);
console.log(`Using subreddits: ${selectedSubs.join(', ')}`);

// Keywords for relevance
const KEYWORDS = ['productivity', 'focus', 'screen time', 'gamification', 'phone addiction', 'study', 'discipline', 'digital minimalism', 'streak', 'accountability', 'motivation'];

// Function to fetch JSON from URL (returns Promise)
function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          // Extract JSON between "---" and "<<<END" if wrapper present
          let jsonStr = data;
          const jsonStart = data.indexOf('---');
          if (jsonStart !== -1) {
            const afterDash = data.substring(jsonStart + 3);
            const jsonEnd = afterDash.indexOf('<<<END');
            jsonStr = jsonEnd !== -1 ? afterDash.substring(0, jsonEnd).trim() : afterDash.trim();
          }
          const parsed = JSON.parse(jsonStr);
          resolve(parsed);
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

// Function to download image
function downloadImage(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    https.get(url, (response) => {
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => reject(err));
    });
  });
}

// Main async function
async function main() {
  let allPosts = [];
  
  // Fetch all subreddits
  for (const sub of selectedSubs) {
    const url = `https://www.reddit.com/r/${sub}/top.json?t=day&limit=5`;
    try {
      const data = await fetchJSON(url);
      const children = data.data?.children || [];
      children.forEach(child => {
        allPosts.push(child.data);
      });
      console.log(`Fetched ${children.length} posts from r/${sub}`);
    } catch (e) {
      console.error(`Failed to fetch r/${sub}:`, e.message);
    }
  }
  
  // Save raw posts to _temp_posts.json (as array)
  fs.writeFileSync(TEMP_JSON, JSON.stringify(allPosts, null, 2));
  console.log(`Raw posts saved to ${TEMP_JSON} (${allPosts.length} total)`);
  
  // Process each post: extract fields and calculate viral score
  const processed = allPosts.map(post => {
    // Extract fields
    const title = post.title;
    const permalink = post.permalink;
    const subreddit = post.subreddit;
    const score = post.score;
    const num_comments = post.num_comments;
    const upvote_ratio = post.upvote_ratio;
    const created = post.created;
    const selftext = post.selftext || '';
    const selftextExcerpt = selftext.substring(0, 200) + (selftext.length > 200 ? '...' : '');
    const url = post.url;
    const post_hint = post.post_hint || null;
    const is_gallery = post.is_gallery || false;
    const media_metadata = post.media_metadata || null;
    const media_sources = [];
    
    // Determine if we need to download images and collect URLs
    let imagesToDownload = [];
    
    const hasImageExtension = /\.(jpg|jpeg|png|gif)$/i.test(url);
    if (post_hint === 'image' && hasImageExtension) {
      const ext = path.extname(url).split('?')[0] || '.jpg';
      const filename = `${post.id}${ext}`;
      imagesToDownload.push({ url, filename });
    } else if (is_gallery && media_metadata) {
      const items = post.gallery_data?.items || [];
      const orderedItems = items.length > 0 ? items : Object.keys(media_metadata).map(k => ({ media_id: k }));
      orderedItems.forEach((item, idx) => {
        const meta = media_metadata[item.media_id];
        if (meta && meta.s && meta.s.u) {
          const imgUrl = meta.s.u;
          const ext = path.extname(imgUrl).split('?')[0] || '.jpg';
          const filename = `${post.id}-${idx}${ext}`;
          imagesToDownload.push({ url: imgUrl, filename });
        }
      });
    } else if (hasImageExtension) {
      const ext = path.extname(url).split('?')[0] || '.jpg';
      const filename = `${post.id}${ext}`;
      imagesToDownload.push({ url, filename });
    }
    
    // Download images and record paths
    const downloadedPaths = [];
    for (const img of imagesToDownload) {
      const destPath = path.join(MEDIA_DIR, img.filename);
      try {
        await downloadImage(img.url, destPath);
        downloadedPaths.push(`${DATE}-media/${img.filename}`);
      } catch (e) {
        console.error(`Failed to download ${img.url} for post ${post.id}:`, e.message);
      }
    }
    media_sources.push(...downloadedPaths);
    
    // Compute viral score
    const raw = Math.min(score, 5000) / 500;
    const engagementRaw = (num_comments / (score + 1)) * 100 * 0.03;
    const engagement = Math.min(engagementRaw, 3);
    const ratio = upvote_ratio * 10;
    const text = (title + ' ' + selftext).toLowerCase();
    let relevanceCount = 0;
    const foundKeywords = new Set();
    for (const kw of KEYWORDS) {
      if (text.includes(kw.toLowerCase()) && !foundKeywords.has(kw)) {
        foundKeywords.add(kw);
        relevanceCount++;
      }
    }
    relevanceCount = Math.min(relevanceCount, 3);
    const total = raw + engagement + ratio + relevanceCount;
    const viral_score = Math.round(total * 10 / 2.6) / 10; // round to 1 decimal
    
    return {
      title,
      permalink,
      subreddit,
      score,
      num_comments,
      upvote_ratio,
      created,
      selftextExcerpt,
      url,
      media_sources,
      viral_score
    };
  });
  
  // Sort descending by viral_score
  processed.sort((a, b) => b.viral_score - a.viral_score);
  
  // Take top 5
  const top5 = processed.slice(0, 5);
  
  // Generate markdown report
  const generatedStr = `${DATE} 17:00 UTC (Europe/Istanbul 20:00)`;
  
  let report = `# Reddit Trending Posts for Focus Timer — ${DATE}\n\n`;
  report += `**Scout:** OpenClaw (v0.1)\n`;
  report += `**Generated:** ${generatedStr}\n`;
  report += `**Sources:** ${selectedSubs.join(', ')} (top 5 of past 24h each)\n\n`;
  report += `### Top 5 Viral Posts\n\n`;
  
  top5.forEach((post, index) => {
    const rank = index + 1;
    const scoreFormatted = post.score >= 1000 ? (post.score/1000).toFixed(1) + 'k' : post.score;
    const commentsFormatted = post.num_comments >= 1000 ? (post.num_comments/1000).toFixed(1) + 'k' : post.num_comments;
    const upvotePercent = Math.round(post.upvote_ratio * 100) + '%';
    
    let thumbLine = '';
    if (post.media_sources && post.media_sources.length > 0) {
      thumbLine = `![Thumb](${post.media_sources[0]})\n`;
    }
    
    const fullPermalink = `https://www.reddit.com${post.permalink}`;
    
    report += `${rank}. **[${post.viral_score.toFixed(1)}]** "${post.title}" (r/${post.subreddit})\n`;
    report += `   Score: ${scoreFormatted} | Comments: ${commentsFormatted} | Upvote: ${upvotePercent}\n`;
    if (thumbLine) report += `   ${thumbLine}`;
    report += `   <${fullPermalink}>\n`;
    if (post.selftextExcerpt) {
      report += `   > ${post.selftextExcerpt}\n`;
    } else {
      report += `   > (no selftext)\n`;
    }
    report += '\n';
  });
  
  // Write report to daily folder
  const dailyReportPath = path.join(DAILY_DIR, `${DATE}.md`);
  fs.writeFileSync(dailyReportPath, report);
  console.log(`Report written to ${dailyReportPath}`);
  
  // Copy report and media to reports folder
  const reportPathDest = path.join(REPORTS_DIR, `${DATE}.md`);
  fs.writeFileSync(reportPathDest, report);
  // Copy media files
  const mediaFiles = fs.readdirSync(MEDIA_DIR);
  for (const file of mediaFiles) {
    fs.copyFileSync(path.join(MEDIA_DIR, file), path.join(REPORT_MEDIA_DIR, file));
  }
  
  // Git add, commit, push
  try {
    execSync('git add -A', { cwd: WORKSPACE, stdio: 'inherit' });
    execSync(`git commit -m "Reddit scout report ${DATE}"`, { cwd: WORKSPACE, stdio: 'inherit' });
    execSync('git push', { cwd: WORKSPACE, stdio: 'inherit' });
    console.log('Git push completed.');
  } catch (e) {
    console.error('Git operations failed:', e.message);
  }
  
  // Output report to stdout for cron delivery
  console.log('\n' + report);
}

main().catch(err => {
  console.error('Scout failed:', err);
  process.exit(1);
});
