const https = require('https');
const fs = require('fs');
const path = require('path');

const subreddits = ['productivity', 'getdisciplined', 'DecidingToBeBetter', 'StudyTips', 'GetStudying'];
const today = '2026-03-07';
const allPosts = [];

function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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

async function downloadImage(url, filename) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(filename);
    https.get(url, (response) => {
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        const stats = fs.statSync(filename);
        if (stats.size > 1024) {
          resolve(filename);
        } else {
          fs.unlinkSync(filename);
          reject(new Error('File too small'));
        }
      });
    }).on('error', (err) => {
      file.close();
      fs.unlinkSync(filename);
      reject(err);
    });
  });
}

async function processSubreddit(subreddit) {
  const url = `https://www.reddit.com/r/${subreddit}/top.json?t=day&limit=5`;
  try {
    const data = await fetchJSON(url);
    const posts = data.data.children.map(child => child.data);
    return posts;
  } catch (error) {
    console.error(`Error fetching r/${subreddit}:`, error.message);
    return [];
  }
}

async function main() {
  for (const subreddit of subreddits) {
    const posts = await processSubreddit(subreddit);
    allPosts.push(...posts);
  }

  // Save raw data
  const tempPath = `/Users/ozlemsultan/.openclaw/workspace/reddit-productivity/daily/_temp_posts.json`;
  fs.writeFileSync(tempPath, JSON.stringify(allPosts, null, 2));
  console.log(`Saved ${allPosts.length} posts to _temp_posts.json`);
}

main();
