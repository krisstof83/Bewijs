const { app } = require('electron').remote;
const path = require('path');
const glob = require('glob')
const parsePDF = require('./parser')
const merge = require('./merger')
const crypto = require('crypto')
const db = require('./database')
const fs = require('fs')

// ⚡ Bolt Optimization: Replace synchronous fs.readFileSync with asynchronous fs.createReadStream
// Why: Prevents blocking the Electron main thread and avoids memory spikes when calculating hashes for large PDF files.
// Impact: Unblocks UI and reduces memory usage significantly during large directory scans.
async function calculateHash(filepath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filepath);
    stream.on('data', data => hash.update(data));
    stream.on('end', () => resolve(hash.digest('hex')));
    stream.on('error', err => reject(err));
  });
}

async function scanPDFs() {
  const homeDir = app.getPath('home');
  const files = glob.sync(path.join(homeDir, '**/*.pdf').replace(/\\/g, '/'))
  document.getElementById('result').innerHTML = `Gevonden: ${files.length} PDF’s`

  const fileData = [];
  for (const f of files) {
    try {
      const hash = await calculateHash(f);
      const stats = fs.statSync(f);
      fileData.push({ path: f, name: path.basename(f), date: stats.birthtime, hash });
    } catch (e) {
      console.error('Error processing file:', f, e);
    }
  }

  // ⚡ Bolt Optimization: Batch SQLite inserts inside a single transaction
  // Why: Inserting records one-by-one without a transaction forces a disk fsync for every db.run(), causing severe performance degradation.
  // Impact: Improves database insertion speed exponentially (often 100x+ faster) by batching operations.
  db.serialize(() => {
    db.run("BEGIN TRANSACTION");
    const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');
    for (const data of fileData) {
      try {
        stmt.run([data.path, data.name, data.date, data.hash]);
      } catch (e) {
        console.error('Error inserting record:', e);
      }
    }
    stmt.finalize();
    db.run("COMMIT");
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