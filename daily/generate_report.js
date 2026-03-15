const fs = require('fs');
const path = require('path');

const analyzed = JSON.parse(fs.readFileSync(path.join(__dirname, '_analyzed_posts.json'), 'utf8'));

// Map by id
const byId = {};
analyzed.forEach(p => byId[p.id] = p);

// Selected top post IDs (order: as we want to present)
const selectedIds = [
  '1r575s6', // GetStudying Might as well start
  '1r5ajqx', // GetStudying How can I study 10 hours a day?
  '1r4xs8k', // nosurf I've deleted all my addictive apps
  '1r56r88', // productivity tactics
  '1r5cokr'  // ADHD I realized I don't avoid tasks...
];

// Relevancy scores (0-3) for each selected post (assigned manually)
const relevance = {
  '1r575s6': 3,
  '1r5ajqx': 3,
  '1r4xs8k': 3,
  '1r56r88': 3,
  '1r5cokr': 3
};

const mediaFolder = '2026-02-16-media';

// Prepare report lines
let report = `# Reddit Trending Posts for Focus Timer – ${new Date().toISOString().split('T')[0]}\n\n`;
report += `**Date:** 2026-02-16\n`;
report += `**Subreddits scanned:** 12\n`;
report += `**Total posts collected:** ${analyzed.length}\n\n`;

report += `## Top Posts\n\n`;

selectedIds.forEach((id, idx) => {
  const p = byId[id];
  if (!p) return;
  const finalScore = p.base_viral + relevance[id];
  const mediaFile = p.image_url ? (p.subreddit.toLowerCase() + '_' + (idx+1) + '.jpg') : null;
  // If mediaFile exists, ensure it is listed in the report
  report += `### ${idx+1}. ${p.title} (r/${p.subreddit})\n\n`;
  report += `- **Stats:** ${p.score} upvotes, ${p.num_comments} comments, ${(p.upvote_ratio*100).toFixed(0)}% upvote ratio\n`;
  report += `- **Viral Score:** ${finalScore} (base ${p.base_viral} + relevance ${relevance[id]}/3)\n`;
  report += `- **Breakdown:**\n`;
  report += `  - Velocity: ${p.velocity.toFixed(1)} upvotes/hour\n`;
  report += `  - Comment ratio: ${p.comment_ratio.toFixed(3)} (comments/upvotes)\n`;
  report += `  - Upvote ratio: ${p.upvote_ratio}\n`;
  report += `  - Relevance: ${relevance[id]}/3\n`;
  report += `- **Body summary:** ${p.selftext ? p.selftext.substring(0, 200) + (p.selftext.length>200?'...':'') : '(no text)'}\n`;
  if (mediaFile) {
    report += `- **Media:** \`${mediaFile}\`\n`;
  } else {
    report += `- **Media:** none\n`;
  }
  report += `- **Permalink:** https://www.reddit.com${p.permalink}\n\n`;
});

report += `## Honorable Mentions\n\n`;
// Pick next 5 interesting posts that are not in selectedIds, sorted by combined descending
const others = analyzed.filter(p => !selectedIds.includes(p.id));
// Sort by combined descending (or base_viral) to get near-top
others.sort((a,b) => b.combined - a.combined);
const topOthers = others.slice(0, 5);
topOthers.forEach(p => {
  report += `- **${p.title}** (r/${p.subreddit}) – ${p.score} upvotes, ${p.num_comments} comments – https://www.reddit.com${p.permalink}\n`;
});

report += `\n## Recommendation\n\n`;
report += `For Focus Timer's social media, I recommend adapting these two posts:\n\n`;
report += `1. **GetStudying: “Might as well start”** – This image has massive appeal (2216 upvotes) with a simple, motivating message. Perfect for a visual quote post. Content idea: Overlay the text on a clean background with Focus Timer branding, or turn it into a daily prompt notification.\n`;
report += `2. **nosurf: “I've deleted all my addictive apps”** – This text post sparked high engagement (22 comments on 8 upvotes) because it addresses the real struggle of bypassing restrictions. Content idea: Create a carousel post: "When you delete apps but still find ways to access them – Focus Timer's always-on display stops that."\n`;

report += `\n## Media Summary\n\n`;
selectedIds.forEach(id => {
  const p = byId[id];
  if (p.image_url) {
    const filename = p.subreddit.toLowerCase() + '_' + (selectedIds.indexOf(id)+1) + '.jpg';
    report += `- \`${filename}\` (${p.subreddit})\n`;
  }
});
report += `\nAll downloaded media stored in: \`/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/2026-02-16-media/\`\n`;

// Write report
fs.writeFileSync(path.join(__dirname, '2026-02-16.md'), report);
console.log('Report generated: 2026-02-16.md');
