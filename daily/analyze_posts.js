const fs = require('fs');
const path = require('path');

const now = 1771192382; // current timestamp from exec
const posts = JSON.parse(fs.readFileSync(path.join(__dirname, '_temp_posts.json'), 'utf8'));

// Enhance each post with computed metrics
posts.forEach(p => {
  const age_seconds = now - p.created;
  const age_hours = age_seconds / 3600;
  p.age_hours = age_hours;
  p.velocity = p.score > 0 ? p.score / age_hours : 0;
  p.comment_ratio = p.score > 0 ? p.num_comments / p.score : 0;
  // upvote_ratio already there
});

// Collect arrays for normalization
const velocities = posts.map(p => p.velocity);
const commentRatios = posts.map(p => p.comment_ratio);
const upvoteRatios = posts.map(p => p.upvote_ratio);

function minMax(arr) {
  return { min: Math.min(...arr), max: Math.max(...arr) };
}

const vRange = minMax(velocities);
const cRange = minMax(commentRatios);
const uRange = minMax(upvoteRatios);

function normalize(val, r) {
  if (r.max === r.min) return 1; // all equal
  return (val - r.min) / (r.max - r.min);
}

// Compute composite and base viral (0-7)
posts.forEach(p => {
  const nV = normalize(p.velocity, vRange);
  const nC = normalize(p.comment_ratio, cRange);
  const nU = normalize(p.upvote_ratio, uRange);
  // equal weights
  p.combined = (nV + nC + nU) / 3;
  p.base_viral = Math.round(p.combined * 7); // 0-7
});

// Sort by combined descending
posts.sort((a,b) => b.combined - a.combined);

// Write enhanced posts for review
fs.writeFileSync(path.join(__dirname, '_analyzed_posts.json'), JSON.stringify(posts, null, 2));

// Print top 15 to console for manual relevance check
console.log('Top 15 posts by viral metrics (before relevance):');
console.table(posts.slice(0, 15).map(p => ({
  subreddit: p.subreddit,
  title: p.title.substring(0, 60) + (p.title.length>60?'...':''),
  score: p.score,
  age_hours: p.age_hours.toFixed(1),
  velocity: p.velocity.toFixed(1),
  comment_ratio: p.comment_ratio.toFixed(3),
  upvote_ratio: p.upvote_ratio,
  base_viral: p.base_viral,
  image_url: p.image_url ? 'yes' : 'no',
  id: p.id
})));

console.log(`\nTotal posts: ${posts.length}`);
console.log(`Velocity range: ${vRange.min.toFixed(2)} - ${vRange.max.toFixed(2)}`);
console.log(`Comment ratio range: ${cRange.min.toFixed(4)} - ${cRange.max.toFixed(4)}`);
console.log(`Upvote ratio range: ${uRange.min.toFixed(2)} - ${uRange.max.toFixed(2)}`);
