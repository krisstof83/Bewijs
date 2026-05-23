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

  db.serialize(() => {
    // Wrap in a single transaction for significantly better database insertion performance
    db.run('BEGIN TRANSACTION');
    const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');
    try {
      for (const f of files) {
        const hash = crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')
        const stats = fs.statSync(f);
        stmt.run([f, path.basename(f), stats.birthtime, hash], (err) => {
          if (err) console.error("Error inserting file:", err);
        });
      }
    } finally {
      // Ensure statement is finalized and transaction committed, as per memory rules
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