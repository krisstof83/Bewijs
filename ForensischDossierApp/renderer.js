const { app } = require('electron').remote;
const path = require('path');
const glob = require('glob')
const parsePDF = require('./parser')
const merge = require('./merger')
const crypto = require('crypto')
const db = require('./database')
const fs = require('fs')

async function scanPDFs() {
  const homeDir = app.getPath('home');
  const files = glob.sync(path.join(homeDir, '**/*.pdf').replace(/\\/g, '/'))
  document.getElementById('result').innerHTML = `Gevonden: ${files.length} PDF’s`

  // ⚡ Bolt: Gather file data asynchronously to prevent main-thread blocking on large files
  const fileData = [];
  for (const f of files) {
    try {
      const hash = await new Promise((resolve, reject) => {
        const h = crypto.createHash('sha256');
        const stream = fs.createReadStream(f);
        stream.on('data', chunk => h.update(chunk));
        stream.on('end', () => resolve(h.digest('hex')));
        stream.on('error', reject);
      });
      const stats = await fs.promises.stat(f);
      fileData.push({ f, name: path.basename(f), date: stats.birthtime, hash });
    } catch (err) {
      console.error(`Error processing file ${f}:`, err);
    }
  }

  // ⚡ Bolt: Batch insert into SQLite using a transaction to avoid per-file fsync bottleneck
  if (fileData.length > 0) {
    await new Promise((resolve, reject) => {
      db.serialize(() => {
        db.run('BEGIN TRANSACTION');
        const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');
        for (const row of fileData) {
          stmt.run(row.f, row.name, row.date, row.hash);
        }
        stmt.finalize();
        db.run('COMMIT', (err) => {
          if (err) reject(err);
          else resolve();
        });
      });
    });
  }
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