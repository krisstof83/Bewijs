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

  // ⚡ Bolt: Optimize bulk inserts by wrapping them in a single transaction.
  // This drastically reduces SQLite disk I/O wait times since each insert
  // isn't treated as a separate transaction.
  db.serialize(() => {
    db.run('BEGIN TRANSACTION');
    const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');

    for (const f of files) {
      const hash = crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')
      const stats = fs.statSync(f);
      stmt.run([f, path.basename(f), stats.birthtime, hash])
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