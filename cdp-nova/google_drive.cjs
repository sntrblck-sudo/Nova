/**
 * Nova's Google Drive Integration
 * Handles OAuth flow and file uploads to Google Drive
 * 
 * Setup flow:
 * 1. Run: node google_drive.js auth
 * 2. Visit the URL it outputs, authorize, copy the code
 * 3. Run: node google_drive.js token <code>
 * 4. Test with: node google_drive.js upload <filePath> [folderId]
 */

const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');
const http = require('http');
const readline = require('readline');

const CREDENTIALS_PATH = path.join(__dirname, 'google_credentials.json');
const TOKENS_PATH = path.join(__dirname, 'google_tokens.json');

const CLIENT_ID = '434440884156-42922vpnivr3v0eiba2q1rolaiseb15p.apps.googleusercontent.com';
const CLIENT_SECRET = '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';
const REDIRECT_URI = 'http://localhost';

const SCOPES = [
  'https://www.googleapis.com/auth/drive.file',
  'https://www.googleapis.com/auth/drive.appdata'
];

function loadCredentials() {
  return {
    installed: {
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      redirect_uris: [REDIRECT_URI]
    }
  };
}

function loadTokens() {
  if (fs.existsSync(TOKENS_PATH)) {
    return JSON.parse(fs.readFileSync(TOKENS_PATH, 'utf8'));
  }
  return null;
}

function saveTokens(tokens) {
  fs.writeFileSync(TOKENS_PATH, JSON.stringify(tokens, null, 2));
  console.log('Tokens saved to', TOKENS_PATH);
}

function getAuthUrl() {
  const client = new google.auth.OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);
  return client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    prompt: 'consent'
  });
}

function exchangeCodeForTokens(code) {
  return new Promise((resolve, reject) => {
    const client = new google.auth.OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);
    client.getToken(code, (err, tokens) => {
      if (err) reject(err);
      else resolve(tokens);
    });
  });
}

function getDriveClient() {
  const tokens = loadTokens();
  if (!tokens) throw new Error('Not authenticated. Run "node google_drive.js auth" first.');
  
  const client = new google.auth.OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);
  client.setCredentials(tokens);
  
  return google.drive({ version: 'v3', auth: client });
}

async function listFiles() {
  const drive = getDriveClient();
  const result = await drive.files.list({
    pageSize: 20,
    fields: 'files(id, name, mimeType, createdTime)',
    q: "'me' in owners"
  });
  return result.data.files;
}

async function uploadFile(filePath, folderId = null) {
  const drive = getDriveClient();
  const fileName = path.basename(filePath);
  const fileSize = fs.statSync(filePath).size;
  
  console.log(`Uploading ${fileName} (${(fileSize/1024).toFixed(1)}KB)...`);
  
  const requestBody = { name: fileName };
  if (folderId) requestBody.parents = [folderId];
  
  const media = {
    mimeType: 'application/octet-stream',
    body: fs.createReadStream(filePath)
  };
  
  const result = await drive.files.create({
    resource: requestBody,
    media,
    fields: 'id, name, webViewLink'
  });
  
  return result.data;
}

async function createOrGetFolder(name) {
  const drive = getDriveClient();
  
  // Check if folder exists
  const result = await drive.files.list({
    q: `name='${name}' and mimeType='application/vnd.google-apps.folder' and 'me' in owners`,
    fields: 'files(id, name)'
  });
  
  if (result.data.files.length > 0) {
    console.log(`Found existing folder: ${name}`);
    return result.data.files[0].id;
  }
  
  // Create folder
  const folder = await drive.files.create({
    resource: {
      name,
      mimeType: 'application/vnd.google-apps.folder'
    },
    fields: 'id, name'
  });
  
  console.log(`Created folder: ${name}`);
  return folder.data.id;
}

async function shareFile(fileId) {
  const drive = getDriveClient();
  await drive.permissions.create({
    fileId,
    resource: {
      type: 'anyone',
      role: 'reader'
    }
  });
}

// Simple local server to capture the OAuth callback
function startCallbackServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, `http://localhost:${REDIRECT_URI.split(':')[2]}`);
      const code = url.searchParams.get('code');
      
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body><h1>Authorization complete!</h1><p>You can close this window and return to the terminal.</p></body></html>');
      
      server.close();
      resolve(code);
    });
    
    server.listen(REDIRECT_URI.split(':')[2] || 8888, () => {
      console.log(`Callback server running on ${REDIRECT_URI}`);
    });
  });
}

async function cmdAuth() {
  const authUrl = getAuthUrl();
  console.log('\n=== Google Drive Authorization ===\n');
  console.log('1. Visit this URL in your browser:\n');
  console.log(authUrl);
  console.log('\n2. Sign in with your Google account and authorize the app');
  console.log('3. You\'ll be redirected to a page that says "This site can\'t be reached"');
  console.log('   (That\'s expected — we\'re using localhost as the redirect)');
  console.log('4. Copy the FULL URL from your browser\'s address bar and paste it here\n');
  
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  
  rl.question('Paste the full redirect URL here: ', async (url) => {
    rl.close();
    try {
      const parsedUrl = new URL(url);
      const code = parsedUrl.searchParams.get('code');
      if (!code) {
        console.error('No authorization code found in URL');
        process.exit(1);
      }
      
      console.log('\nExchanging code for tokens...');
      const tokens = await exchangeCodeForTokens(code);
      saveTokens(tokens);
      console.log('\n✅ Authentication complete!');
      console.log('Run "node google_drive.js test" to verify.');
    } catch (e) {
      console.error('Error:', e.message);
    }
  });
}

async function cmdToken(code) {
  try {
    console.log('Exchanging code for tokens...');
    const tokens = await exchangeCodeForTokens(code);
    saveTokens(tokens);
    console.log('\n✅ Authentication complete!');
  } catch (e) {
    console.error('Error:', e.message);
    process.exit(1);
  }
}

async function cmdTest() {
  try {
    const files = await listFiles();
    console.log('\n=== Google Drive - Your Files ===\n');
    files.forEach(f => console.log(`  ${f.name} (${f.id})`));
    console.log(`\nTotal: ${files.length} files\n`);
  } catch (e) {
    console.error('Error:', e.message);
    if (e.message.includes('invalid_grant') || e.message.includes('Token expired')) {
      console.error('\nTokens may be expired. Run "node google_drive.js auth" to re-authenticate.');
    }
  }
}

async function cmdUpload(filePath, folderName = 'Nova Backups') {
  try {
    const folderId = await createOrGetFolder(folderName);
    const result = await uploadFile(filePath, folderId);
    console.log(`\n✅ Uploaded: ${result.name}`);
    console.log(`   ID: ${result.id}`);
    console.log(`   Link: ${result.webViewLink}`);
  } catch (e) {
    console.error('Error:', e.message);
    if (e.message.includes('invalid_grant') || e.message.includes('Token expired')) {
      console.error('\nTokens may be expired. Run "node google_drive.js auth" to re-authenticate.');
    }
  }
}

const [,, cmd, ...args] = process.argv;

(async () => {
  switch (cmd) {
    case 'auth':
      await cmdAuth();
      break;
    case 'token':
      await cmdToken(args[0]);
      break;
    case 'test':
      await cmdTest();
      break;
    case 'upload':
      if (!args[0]) {
        console.error('Usage: node google_drive.js upload <filePath> [folderName]');
        process.exit(1);
      }
      await cmdUpload(args[0], args[1]);
      break;
    case 'folder':
      if (!args[0]) {
        console.error('Usage: node google_drive.js folder <folderName>');
        process.exit(1);
      }
      await createOrGetFolder(args[0]);
      break;
    default:
      console.log('\n=== Nova Google Drive CLI ===\n');
      console.log('Commands:');
      console.log('  node google_drive.js auth              - Start OAuth flow');
      console.log('  node google_drive.js token <code>     - Exchange auth code for tokens');
      console.log('  node google_drive.js test             - List your Google Drive files');
      console.log('  node google_drive.js upload <path>    - Upload a file');
      console.log('  node google_drive.js folder <name>    - Create/get a folder by name');
      console.log('\nFirst time setup:');
      console.log('  1. node google_drive.js auth');
      console.log('  2. Visit URL, authorize, paste redirect URL');
      console.log('  3. node google_drive.js test\n');
  }
})();
