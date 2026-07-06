const { app } = require('electron').remote;
const path = require('path');
const glob = require('glob')
const parsePDF = require('./parser')
const merge = require('./merger')
const crypto = require('crypto')
const db = require('./database')
const fs = require('fs')

// ⚡ Bolt: helper to generate file hash asynchronously to avoid blocking main thread
function generateHashAsync(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath);
    stream.on('data', chunk => hash.update(chunk));
    stream.on('end', () => resolve(hash.digest('hex')));
    stream.on('error', reject);
  });
}

async function scanPDFs() {
  const homeDir = app.getPath('home');
  const files = glob.sync(path.join(homeDir, '**/*.pdf').replace(/\\/g, '/'))
  document.getElementById('result').innerHTML = `Gevonden: ${files.length} PDF’s`

  // ⚡ Bolt: gather data asynchronously
  const fileData = [];
  for (const f of files) {
    try {
      const hash = await generateHashAsync(f);
      const stats = fs.statSync(f);
      fileData.push({ path: f, name: path.basename(f), date: stats.birthtime, hash });
    } catch (err) {
      console.error(`Error processing file ${f}:`, err);
    }
  }

  // ⚡ Bolt: batch inserts in a single transaction for massive SQLite performance boost
  db.serialize(() => {
    db.run('BEGIN TRANSACTION');
    const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');
    try {
      for (const data of fileData) {
        stmt.run(data.path, data.name, data.date, data.hash);
      }
    } catch (e) {
      console.error('Error during batch insert', e);
    } finally {
      stmt.finalize();
      db.run('COMMIT');
    }
  });
}

async function buildMaster() {
  const files = []
  db.each('SELECT path FROM files ORDER BY date', (err, row) => {
    if (row) {
      files.push(row.path)
    }
  }, async () => {
    if (files.length > 0) {
      await merge(files)
    } else {
      console.log('No files found to merge.');
    }
  })
}

document.getElementById('scan').onclick = scanPDFs
document.getElementById('merge').onclick = buildMaster