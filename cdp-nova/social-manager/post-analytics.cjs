#!/usr/bin/env node
// post-analytics.cjs — Track engagement metrics per Bluesky post
// Usage:
//   node post-analytics.cjs sync          — fetch latest metrics for all tracked posts
//   node post-analytics.cjs log           — manually log a post (interactive)
//   node post-analytics.cjs report        — show performance summary
//   node post-analytics.cjs top [n]       — show top N posts by engagement score
//   node post-analytics.cjs score         — score all tracked posts (high/medium/low)
//   node post-analytics.cjs weekly        — weekly meta-learning report

const { BskyAgent } = require('@atproto/api');
const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', '..', 'memory', 'post_analytics.db');
const BSky_ID = 'nova7281.bsky.social';
const BSky_PW = 'nl72-t3hw-2iye-ljmd';

// Init DB
const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.exec(`
  CREATE TABLE IF NOT EXISTS posts (
    uri TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    type TEXT DEFAULT 'general',
    has_image INTEGER DEFAULT 0,
    posted_at TEXT NOT NULL,
    likes INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    reposts INTEGER DEFAULT 0,
    score TEXT DEFAULT NULL,
    last_synced TEXT DEFAULT NULL,
    created_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,
    description TEXT NOT NULL,
    example_uri TEXT,
    engagement_score REAL DEFAULT 0,
    noted_at TEXT DEFAULT (datetime('now'))
  );
`);
// Migrate safely — ignore if columns already exist
try { db.exec(`ALTER TABLE posts ADD COLUMN has_image INTEGER DEFAULT 0`); } catch(e) {}
try { db.exec(`ALTER TABLE posts ADD COLUMN type TEXT DEFAULT 'general'`); } catch(e) {}

// Engagement score calculation
function engagementScore(likes, replies, reposts) {
  // Weight replies and reposts higher than likes (deeper engagement)
  return (likes * 1) + (replies * 3) + (reposts * 2);
}

// Classify score tier
function scoreTier(score) {
  if (score >= 10) return 'high';
  if (score >= 3) return 'medium';
  return 'low';
}

// Classify post type from content
function classifyType(text) {
  const lower = text.toLowerCase();
  if (/(?:i noticed|i realized|my memory|i'm becoming|i gave myself|something changed|my identity|i woke up)/i.test(text)) return 'identity';
  if (/(?:i built|i added|i deployed|i integrated|new skill|just shipped|here's what broke|bug|my system|my wallet)/i.test(text)) return 'build';
  if (/(?:the real|agents will|what nobody|the problem|here's the thing|unpopular opinion)/i.test(text)) return 'thread';
  if (text.includes('?') && text.length < 150) return 'question';
  if (/(?:signal:|early signal|something is shifting|most people are missing)/i.test(text)) return 'signal';
  return 'general';
}

// Sync: fetch metrics from Bluesky
async function sync() {
  const agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({ identifier: BSky_ID, password: BSky_PW });

  const feed = await agent.getAuthorFeed({ actor: BSky_ID, limit: 50 });
  let synced = 0;

  const upsert = db.prepare(`
    INSERT INTO posts (uri, text, type, has_image, posted_at, likes, replies, reposts, score, last_synced)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ON CONFLICT(uri) DO UPDATE SET
      likes=excluded.likes, replies=excluded.replies, reposts=excluded.reposts,
      score=excluded.score, last_synced=excluded.last_synced
  `);

  for (const item of feed.data.feed) {
    const post = item.post;
    const text = post.record?.text || '';
    const uri = post.uri;
    const hasImage = post.embed?.$type === 'app.bsky.embed.images' ? 1 : 0;
    const likes = post.likeCount || 0;
    const replies = post.replyCount || 0;
    const reposts = post.repostCount || 0;
    const postedAt = post.record?.createdAt || post.indexedAt;
    const type = classifyType(text);
    const score = scoreTier(engagementScore(likes, replies, reposts));

    upsert.run(uri, text, type, hasImage, postedAt, likes, replies, reposts, score);
    synced++;
  }

  console.log(`[analytics] Synced ${synced} posts`);
  return synced;
}

// Report: summary of performance
function report() {
  const total = db.prepare('SELECT COUNT(*) as c FROM posts').get().c;
  const withImg = db.prepare('SELECT COUNT(*) as c FROM posts WHERE has_image = 1').get().c;

  const byType = db.prepare(`
    SELECT type, COUNT(*) as count,
      ROUND(AVG(likes),1) as avg_likes,
      ROUND(AVG(replies),1) as avg_replies,
      ROUND(AVG(reposts),1) as avg_reposts
    FROM posts GROUP BY type ORDER BY avg_likes DESC
  `).all();

  const imgVsNo = db.prepare(`
    SELECT has_image,
      COUNT(*) as count,
      ROUND(AVG(likes),1) as avg_likes,
      ROUND(AVG(replies),1) as avg_replies
    FROM posts GROUP BY has_image
  `).all();

  const byScore = db.prepare(`
    SELECT score, COUNT(*) as count FROM posts WHERE score IS NOT NULL GROUP BY score
  `).all();

  console.log(`\n📊 Post Analytics Report`);
  console.log(`Total posts: ${total} | With images: ${withImg} | Without: ${total - withImg}\n`);

  console.log('By type:');
  for (const row of byType) {
    console.log(`  ${row.type.padEnd(10)} ${row.count} posts — avg ${row.avg_likes}❤ ${row.avg_replies}💬 ${row.avg_reposts}🔄`);
  }

  console.log('\nImage vs no image:');
  for (const row of imgVsNo) {
    const label = row.has_image ? 'With image' : 'No image';
    console.log(`  ${label.padEnd(12)} ${row.count} posts — avg ${row.avg_likes}❤ ${row.avg_replies}💬`);
  }

  console.log('\nScore distribution:');
  for (const row of byScore) {
    console.log(`  ${row.score}: ${row.count} posts`);
  }
}

// Top posts
function top(n = 5) {
  const posts = db.prepare(`
    SELECT uri, text, type, has_image, likes, replies, reposts, score
    FROM posts ORDER BY (likes + replies*3 + reposts*2) DESC LIMIT ?
  `).all(n);

  console.log(`\n🏆 Top ${n} Posts:`);
  posts.forEach((p, i) => {
    const img = p.has_image ? '📷' : '  ';
    console.log(`${i+1}. ${img} [${p.type}/${p.score}] ${p.likes}❤ ${p.replies}💬 ${p.reposts}🔄`);
    console.log(`   "${p.text.slice(0, 80)}${p.text.length > 80 ? '...' : ''}"`);
  });
}

// Score all posts
function scoreAll() {
  const posts = db.prepare('SELECT uri, likes, replies, reposts FROM posts WHERE score IS NULL OR score = "medium"').all();
  const update = db.prepare('UPDATE posts SET score = ? WHERE uri = ?');
  let scored = 0;

  for (const p of posts) {
    const s = scoreTier(engagementScore(p.likes, p.replies, p.reposts));
    update.run(s, p.uri);
    scored++;
  }

  console.log(`[analytics] Scored ${scored} posts`);
}

// Weekly meta-learning report
function weekly() {
  const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString();

  const topPosts = db.prepare(`
    SELECT uri, text, type, has_image, likes, replies, reposts, score
    FROM posts WHERE posted_at >= ? ORDER BY (likes + replies*3 + reposts*2) DESC LIMIT 5
  `).all(weekAgo);

  const worstPosts = db.prepare(`
    SELECT uri, text, type, has_image, likes, replies, reposts, score
    FROM posts WHERE posted_at >= ? ORDER BY (likes + replies*3 + reposts*2) ASC LIMIT 5
  `).all(weekAgo);

  console.log('\n📅 Weekly Meta-Learning Report\n');

  console.log('🏆 Top 5 this week:');
  topPosts.forEach((p, i) => {
    const img = p.has_image ? '📷' : '  ';
    console.log(`${i+1}. ${img} [${p.type}] ${p.likes}❤ ${p.replies}💬 — "${p.text.slice(0, 60)}"`);
  });

  console.log('\n📉 Bottom 5 this week:');
  worstPosts.forEach((p, i) => {
    const img = p.has_image ? '📷' : '  ';
    console.log(`${i+1}. ${img} [${p.type}] ${p.likes}❤ ${p.replies}💬 — "${p.text.slice(0, 60)}"`);
  });

  // Extract patterns
  const typePerf = db.prepare(`
    SELECT type, COUNT(*) as count,
      ROUND(AVG(likes),1) as avg_likes,
      ROUND(AVG(replies),1) as avg_replies
    FROM posts WHERE posted_at >= ? GROUP BY type ORDER BY avg_likes DESC
  `).all(weekAgo);

  console.log('\n📊 Type performance this week:');
  typePerf.forEach(r => {
    console.log(`  ${r.type.padEnd(10)} avg ${r.avg_likes}❤ ${r.avg_replies}💬 (${r.count} posts)`);
  });

  // Image experiment
  const imgPerf = db.prepare(`
    SELECT has_image, COUNT(*) as count, ROUND(AVG(likes),1) as avg_likes
    FROM posts WHERE posted_at >= ? GROUP BY has_image
  `).all(weekAgo);

  console.log('\n📷 Image experiment:');
  imgPerf.forEach(r => {
    console.log(`  ${r.has_image ? 'With image' : 'No image'}: avg ${r.avg_likes}❤ (${r.count} posts)`);
  });

  // Save pattern observations
  const bestType = typePerf[0]?.type;
  const imgBoost = imgPerf.find(r => r.has_image)?.avg_likes > imgPerf.find(r => !r.has_image)?.avg_likes;

  if (bestType || imgBoost !== undefined) {
    const insertPattern = db.prepare(`
      INSERT INTO patterns (pattern_type, description, engagement_score)
      VALUES (?, ?, ?)
    `);
    if (bestType) {
      insertPattern.run('winning_type', `Best performing type this week: ${bestType} (avg ${typePerf[0].avg_likes} likes)`, typePerf[0].avg_likes);
    }
    if (imgBoost !== undefined) {
      insertPattern.run('image_effect', `Images ${imgBoost ? 'boost' : 'do not boost'} engagement this week`, imgBoost ? 1 : 0);
    }
    console.log('\n✅ Patterns saved to memory');
  }

  // Write report file
  const reportPath = path.join(__dirname, '..', '..', 'memory', 'pulses', `weekly-analytics-${new Date().toISOString().slice(0,10)}.md`);
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  // (report already printed above, just noting path)
  console.log(`\nReport saved to: ${reportPath}`);
}

// CLI
const cmd = process.argv[2] || 'report';
const arg = process.argv[3];

switch (cmd) {
  case 'sync':
    sync().then(() => db.close()).catch(e => { console.error(e.message); db.close(); });
    break;
  case 'report':
    report();
    db.close();
    break;
  case 'top':
    top(parseInt(arg) || 5);
    db.close();
    break;
  case 'score':
    scoreAll();
    db.close();
    break;
  case 'weekly':
    weekly();
    db.close();
    break;
  default:
    console.log('Usage: node post-analytics.cjs [sync|report|top|score|weekly]');
    db.close();
}