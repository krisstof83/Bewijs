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
  // ⚡ Bolt Optimization: Use explicit transaction for bulk inserts
  // Why: By default, SQLite creates a new transaction per INSERT which requires disk flush.
  // Wrapping all inserts in one transaction provides ~10x speedup for bulk operations.
  db.serialize(() => {
    db.run('BEGIN TRANSACTION');
    try {
      for (const f of files) {
        const hash = crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')
        const stats = fs.statSync(f);
        db.run('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)', [f, path.basename(f), stats.birthtime, hash])
      }
      db.run('COMMIT');
    } catch (e) {
      db.run('ROLLBACK');
      console.error('Error during bulk insert:', e);
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