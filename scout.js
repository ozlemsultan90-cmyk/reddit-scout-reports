#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SUBREDDITS = [
  'productivity',
  'getdisciplined',
  'DecidingToBeBetter',
  'StudyTips',
  'GetStudying'
];

const DATE = '2026-03-14';
const BASE_DIR = __dirname;
const MEDIA_DIR = path.join(BASE_DIR, 'daily', `${DATE}-media`);
const REPORT_PATH = path.join(BASE_DIR, 'daily', `${DATE}.md`);
const TEMP_POSTS_PATH = path.join(BASE_DIR, '_temp_posts.json');

const USER_AGENT = 'RedditScout/1.0 (by u/ozlemsultan)';

async function fetchJSON(url) {
  const res = await fetch(url, {
    headers: { 'User-Agent': USER_AGENT }
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${url}`);
  }
  return res.json();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
  // Ensure media dir exists
  fs.mkdirSync(MEDIA_DIR, { recursive: true });

  let allPosts = [];

  for (let i = 0; i < SUBREDDITS.length; i++) {
    const sub = SUBREDDITS[i];
    const url = `https://www.reddit.com/r/${sub}/top.json?t=day&limit=5`;
    try {
      const data = await fetchJSON(url);
      const children = data.data?.children || [];
      children.forEach(child => {
        const post = child.data;
        post.source_subreddit = sub;
        allPosts.push(post);
      });
      console.log(`Fetched ${children.length} posts from r/${sub}`);
    } catch (err) {
      console.error(`Failed to fetch r/${sub}: ${err.message}`);
      // Continue without this subreddit's posts
    }
    // Delay between requests to respect rate limits
    if (i < SUBREDDITS.length - 1) {
      await sleep(2000);
    }
  }

  // Write raw posts as JSON lines
  const lines = allPosts.map(post => JSON.stringify(post));
  fs.writeFileSync(TEMP_POSTS_PATH, lines.join('\n') + '\n');
  console.log(`Wrote ${allPosts.length} raw posts to ${TEMP_POSTS_PATH}`);

  // Compute viral scores
  const postsWithScores = allPosts.map(post => {
    const score = post.score || 0;
    const comments = post.num_comments || 0;
    const ratio = post.upvote_ratio || 0;
    const viral = (score + comments * 2) * ratio;
    return { ...post, viral_score: viral };
  });

  // Sort descending by viral_score
  postsWithScores.sort((a, b) => b.viral_score - a.viral_score);

  const top5 = postsWithScores.slice(0, 5);
  const top20 = postsWithScores.slice(0, 20);

  console.log(`Top viral score: ${top5[0]?.viral_score}`);
  console.log(`Threshold (5th): ${top5[4]?.viral_score}`);

  // Download images for top5
  for (const post of top5) {
    let imgUrl = null;
    if (post.domain === 'i.redd.it' && post.url) {
      imgUrl = post.url;
    } else if (post.thumbnail && post.thumbnail.startsWith('http')) {
      imgUrl = post.thumbnail;
    } else if (post.preview && post.preview.images && post.preview.images.length > 0) {
      imgUrl = post.preview.images[0].source.url;
    }
    if (!imgUrl) continue;
    // Extract extension
    let ext = imgUrl.split('.').pop().split('?')[0];
    if (!ext || ext.includes('/')) ext = 'jpg';
    const filename = `${post.id}.${ext}`;
    const filepath = path.join(MEDIA_DIR, filename);
    try {
      const imgRes = await fetch(imgUrl, { headers: { 'User-Agent': USER_AGENT } });
      if (!imgRes.ok) throw new Error(`HTTP ${imgRes.status}`);
      const buffer = await imgRes.buffer();
      fs.writeFileSync(filepath, buffer);
      console.log(`Downloaded image for ${post.id} to ${filename}`);
    } catch (err) {
      console.error(`Failed to download image for ${post.id}: ${err.message}`);
    }
  }

  // Generate report markdown
  const uniqueSubreddits = new Set(postsWithScores.map(p => p.source_subreddit)).size;
  const thresholdScore = top5.length === 5 ? top5[4].viral_score : (top5[0] ? top5[0].viral_score : 0);

  let md = `# Reddit Scout Report\n\n`;
  md += `**Scout:** Reddit Scout\n`;
  md += `**Date:** ${DATE} (Europe/Istanbul)\n`;
  md += `**Subreddits fetched:** ${uniqueSubreddits}\n`;
  md += `**Total posts collected:** ${allPosts.length}\n`;
  md += `**Top 5 viral threshold score:** ${thresholdScore.toFixed(1)}\n\n`;

  md += `## Top 5 Viral Posts\n\n`;
  md += `| Rank | Thumbnail | Title/Author | Stats | Link |\n`;
  md += `|------|-----------|--------------|-------|------|\n`;

  for (let i = 0; i < top5.length; i++) {
    const post = top5[i];
    const rank = i + 1;
    const title = post.title.replace(/\|/g, '\\|');
    const author = post.author || 'unknown';
    const score = post.score || 0;
    const comments = post.num_comments || 0;
    const ratio = Math.round((post.upvote_ratio || 0) * 100) + '%';
    const permalink = `https://www.reddit.com${post.permalink}`;
    // Check if an image file exists for this post in media dir
    let thumbMarkdown = '';
    try {
      const files = fs.readdirSync(MEDIA_DIR);
      const matched = files.find(f => f.startsWith(post.id + '.'));
      if (matched) {
        thumbMarkdown = `![thumb](./${DATE}-media/${matched})`;
      }
    } catch (e) {
      // media dir may not exist yet; ignore
    }
    const stats = `Upvotes: ${score}\\nComments: ${comments}\\nRatio: ${ratio}`;
    md += `| ${rank} | ${thumbMarkdown} | **${title}** by u/${author} | ${stats} | [view](${permalink}) |\n`;
  }

  md += `\n## Topics, Themes, Patterns\n\n`;

  // Categorization keywords
  const categories = {
    'study hacks': ['hack', 'tip', 'technique', 'method', 'trick', 'cheat', 'strategy', 'advice', 'guide', 'resource', 'improve', 'better', 'productivity', 'study', 'tips', 'how to', 'stop', 'change', 'reflection'],
    'mental health': ['stress', 'anxiety', 'depression', 'burnout', 'mental', 'therapy', 'emotion', 'feeling', 'mindset', 'self care', 'wellbeing', 'health', 'anger', 'patience', 'losing my mind', 'sobriety', 'friends', 'coworkers', 'joke', 'relationship', 'taking a break', 'dating', 'isolation', 'lonely'],
    'tools': ['app', 'tool', 'software', 'ai', 'coursology', 'platform', 'flashcard', 'notion', 'digital', 'online', 'website', 'extension', 'service', 'subscription'],
    'exams': ['exam', 'test', 'final', 'quiz', 'midterm', 'finals', 'revision', 'assessment', 'grade', 'score'],
    'discipline': ['discipline', 'habit', 'routine', 'consistency', 'procrastination', 'focus', 'concentration', 'productivity', 'time management', 'motivation', 'goal', 'plan', 'schedule', 'body doubling']
  };

  // Initialize category arrays
  const categorized = {};
  for (const cat of Object.keys(categories)) {
    categorized[cat] = [];
  }

  // Categorize top20 (first-match)
  for (const post of top20) {
    const titleLower = post.title.toLowerCase();
    for (const [cat, keywords] of Object.entries(categories)) {
      if (keywords.some(kw => titleLower.includes(kw))) {
        categorized[cat].push(post);
        break;
      }
    }
  }

  // Add category sections with posts sorted by viral score desc within each
  for (const [cat, posts] of Object.entries(categorized)) {
    if (posts.length > 0) {
      md += `### ${cat}\n`;
      posts.sort((a,b) => b.viral_score - a.viral_score);
      for (const p of posts) {
        md += `- **${p.title}** by u/${p.author} (r/${p.source_subreddit}, Score: ${p.score})\n`;
      }
      md += `\n`;
    }
  }

  // All Posts Sorted by Viral Score (top 20) table
  md += `## All Posts Sorted by Viral Score (top 20)\n\n`;
  md += `| Rank | Title | Author | Subreddit | Score | Comments | Viral |\n`;
  md += `|------|-------|--------|-----------|-------|----------|-------|\n`;

  for (let i = 0; i < top20.length; i++) {
    const post = top20[i];
    const rank = i + 1;
    const title = post.title.replace(/\|/g, '\\|');
    const author = post.author || 'unknown';
    const sub = post.source_subreddit;
    const score = post.score || 0;
    const comments = post.num_comments || 0;
    const viral = post.viral_score ? post.viral_score.toFixed(1) : '0.0';
    md += `| ${rank} | ${title} | u/${author} | r/${sub} | ${score} | ${comments} | ${viral} |\n`;
  }

  // Write report
  fs.writeFileSync(REPORT_PATH, md);
  console.log(`Report written to ${REPORT_PATH}`);

  // Git commit and push
  try {
    execSync('git add .', { cwd: BASE_DIR, stdio: 'inherit' });
    execSync(`git commit -m "Scout report ${DATE}"`, { cwd: BASE_DIR, stdio: 'inherit' });
    execSync('git push origin main', { cwd: BASE_DIR, stdio: 'inherit' });
    console.log('Git push completed.');
  } catch (err) {
    console.error('Git operation failed:', err.message);
  }
}

main().catch(err => {
  console.error('Scout failed:', err);
  process.exit(1);
});
