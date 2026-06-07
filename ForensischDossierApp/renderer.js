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

  // ⚡ Bolt Optimization: Batching SQLite inserts within a transaction.
  // In Node.js sqlite3, individual db.run() calls without a transaction force a disk fsync
  // per insert, creating a major performance bottleneck. Batching with a transaction and a
  // prepared statement scales performance drastically when scanning many files.
  db.serialize(() => {
    db.run('BEGIN TRANSACTION');
    const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');

    for (const f of files) {
      try {
        // Synchronous operations within db.serialize MUST be wrapped in try/catch,
        // otherwise an error prevents the COMMIT from queueing, locking the database.
        const hash = crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')
        const stats = fs.statSync(f);
        stmt.run(f, path.basename(f), stats.birthtime, hash);
      } catch (err) {
        console.error(`Failed to process ${f}:`, err);
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