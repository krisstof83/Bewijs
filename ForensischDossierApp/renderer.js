const { app } = require('electron').remote;
const path = require('path');
const glob = require('glob')
const parsePDF = require('./parser')
const merge = require('./merger')
const crypto = require('crypto')
const db = require('./database')
const fs = require('fs')

// Helper to calculate file hash asynchronously using streams to prevent blocking
function calculateHash(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath);
    stream.on('error', err => reject(err));
    stream.on('data', chunk => hash.update(chunk));
    stream.on('end', () => resolve(hash.digest('hex')));
  });
}

async function scanPDFs() {
  const homeDir = app.getPath('home');
  const files = glob.sync(path.join(homeDir, '**/*.pdf').replace(/\\/g, '/'))
  document.getElementById('result').innerHTML = `Gevonden: ${files.length} PDF’s`

  // Pre-calculate file data asynchronously to avoid blocking the main thread
  const fileData = [];
  for (const f of files) {
    try {
      const hash = await calculateHash(f);
      const stats = fs.statSync(f);
      fileData.push({ path: f, name: path.basename(f), date: stats.birthtime, hash });
    } catch (err) {
      console.error(`Error processing file ${f}:`, err);
    }
  }

  // Batch insert into database for massive performance boost
  db.serialize(() => {
    db.run('BEGIN TRANSACTION');
    const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');

    for (const data of fileData) {
      try {
        stmt.run([data.path, data.name, data.date, data.hash]);
      } catch (err) {
        console.error(`Error inserting ${data.path}:`, err);
      }
    }

    stmt.finalize();
    db.run('COMMIT');
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