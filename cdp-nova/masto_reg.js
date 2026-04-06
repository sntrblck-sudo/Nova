const https = require('https');

const INSTANCE = 'mastodon.social';

https.get('https://mastodon.social/auth/sign_in', {
  headers: { 'User-Agent': 'Mozilla/5.0' }
}, res => {
  let data = '';
  res.on('data', c => data += c);
  res.on('end', () => {
    console.log('Status:', res.statusCode);
    const csrf = data.match(/csrf-token.*?content="([^"]+)"/);
    const auth = data.match(/authenticity_token.*?value="([^"]+)"/);
    console.log('CSRF:', csrf ? csrf[1].slice(0, 30) : 'none');
    console.log('Auth:', auth ? auth[1].slice(0, 30) : 'none');
  });
}).on('error', e => console.error(e.message));
