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
  // ⚡ Bolt Optimization: Batch SQLite inserts inside a transaction.
  // 💡 What: Wrapped individual row inserts into a single BEGIN/COMMIT transaction.
  // 🎯 Why: Without transactions, sqlite3 performs a disk fsync for every single `db.run()`, which is an O(N) IO bottleneck.
  // 📊 Impact: Massively reduces I/O wait times and improves PDF scan speed from O(N) fsyncs to O(1).
  db.serialize(() => {
    db.run('BEGIN TRANSACTION');
    const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');
    try {
      for (const f of files) {
        try {
          const hash = crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')
          const stats = fs.statSync(f);
          stmt.run([f, path.basename(f), stats.birthtime, hash]);
        } catch (e) {
          console.error(`Error processing file ${f}:`, e);
          // Continue with the next file
        }
      }
      db.run('COMMIT');
    } catch (e) {
      console.error('Error during bulk insert:', e);
      db.run('ROLLBACK');
    } finally {
      stmt.finalize();
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