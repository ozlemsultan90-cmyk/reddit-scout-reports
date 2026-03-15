const https = require('https');
const fs = require('fs');
const path = require('path');

const subreddits = [
  'productivity',
  'getdisciplined',
  'pomodoro',
  'nosurf',
  'digitalminimalism',
  'gamification',
  'habitgames',
  'incremental_games',
  'memes',
  'ADHD',
  'GetStudying',
  'selfimprovement'
];

const outFile = path.join(__dirname, '_temp_posts.json');
const allPosts = [];

function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'OpenClaw Reddit Scout/1.0'
      }
    };
    https.get(url, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function extractPostData(post, subreddit) {
  const data = post.data;
  // selftext first 200 chars
  let selftext = data.selftext || '';
  if (selftext.length > 200) selftext = selftext.substring(0, 200) + '...';
  const extracted = {
    subreddit: subreddit,
    title: data.title,
    selftext: selftext,
    score: data.ups || data.score,
    num_comments: data.num_comments,
    upvote_ratio: data.upvote_ratio,
    created: data.created,
    url: data.url,
    permalink: data.permalink,
    post_hint: data.post_hint || null,
    is_gallery: data.is_gallery || false,
    thumbnail: data.thumbnail || null,
    image_url: null,
    media_metadata: data.is_gallery ? (data.media_metadata || null) : null,
    id: data.id,
    domain: data.domain
  };
  // For image posts, capture direct image URL
  if (data.post_hint === 'image' && data.url) {
    extracted.image_url = data.url;
  } else if (data.url && data.url.includes('i.redd.it')) {
    extracted.image_url = data.url;
  }
  // Also check url_overridden_by_dest
  if (data.url_overridden_by_dest && !extracted.image_url) {
    extracted.image_url = data.url_overridden_by_dest;
  }
  return extracted;
}

async function run() {
  for (const sub of subreddits) {
    const url = `https://www.reddit.com/r/${sub}/top.json?t=day&limit=5`;
    try {
      const json = await fetchJSON(url);
      if (json && json.data && json.data.children) {
        for (const child of json.data.children) {
          try {
            const post = await extractPostData(child, sub);
            allPosts.push(post);
          } catch (e) {
            console.error(`Error extracting post from ${sub}: ${e}`);
          }
        }
        console.log(`Fetched ${json.data.children.length} posts from r/${sub}`);
      } else {
        console.log(`No posts found in r/${sub}`);
      }
    } catch (e) {
      console.error(`Error fetching r/${sub}: ${e.message}`);
    }
  }

  // Save all posts to temp file
  fs.writeFileSync(outFile, JSON.stringify(allPosts, null, 2));
  console.log(`Saved ${allPosts.length} total posts to ${outFile}`);
}

run().catch(console.error);
