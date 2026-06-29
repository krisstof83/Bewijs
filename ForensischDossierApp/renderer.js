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
  const files = glob.sync(path.join(homeDir, '**/*.pdf').replace(/\\/g, '/'));
  document.getElementById('result').innerHTML = `Gevonden: ${files.length} PDF’s`;

  const filesData = [];
  for (const f of files) {
    try {
      const hash = await new Promise((resolve, reject) => {
        const hashInstance = crypto.createHash('sha256');
        const stream = fs.createReadStream(f);
        stream.on('error', reject);
        stream.on('data', chunk => hashInstance.update(chunk));
        stream.on('end', () => resolve(hashInstance.digest('hex')));
      });
      const stats = fs.statSync(f);
      filesData.push({ f, name: path.basename(f), date: stats.birthtime, hash });
    } catch (err) {
      console.error(`Error processing ${f}:`, err);
    }
  }

  db.serialize(() => {
    db.run('BEGIN TRANSACTION');
    const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');
    for (const data of filesData) {
      stmt.run([data.f, data.name, data.date, data.hash]);
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