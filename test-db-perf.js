const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const time = Date.now();
const dbFile = 'test-' + time + '.db';
const db = new sqlite3.Database(dbFile);

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT,
    name TEXT,
    date TEXT,
    hash TEXT
  )`);
});

const numRows = 1000;

function runWithoutTx() {
  return new Promise((resolve) => {
    const start = Date.now();
    let count = 0;
    for (let i = 0; i < numRows; i++) {
      db.run('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)', ['path', 'name', 'date', 'hash'], () => {
        count++;
        if (count === numRows) {
          resolve(Date.now() - start);
        }
      });
    }
  });
}

function runWithTx() {
  return new Promise((resolve) => {
    const start = Date.now();
    db.serialize(() => {
      db.run('BEGIN TRANSACTION');
      const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');
      for (let i = 0; i < numRows; i++) {
        stmt.run(['path', 'name', 'date', 'hash']);
      }
      stmt.finalize();
      db.run('COMMIT', () => {
        resolve(Date.now() - start);
      });
    });
  });
}

async function run() {
  const t1 = await runWithoutTx();
  console.log(`Without TX: ${t1}ms`);

  const dbFile2 = 'test2-' + time + '.db';
  const db2 = new sqlite3.Database(dbFile2);
  db2.serialize(() => {
    db2.run(`CREATE TABLE IF NOT EXISTS files (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      path TEXT,
      name TEXT,
      date TEXT,
      hash TEXT
    )`);
  });

  const start2 = Date.now();
  db2.serialize(() => {
    db2.run('BEGIN TRANSACTION');
    const stmt = db2.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)');
    for (let i = 0; i < numRows; i++) {
      stmt.run(['path', 'name', 'date', 'hash']);
    }
    stmt.finalize();
    db2.run('COMMIT', () => {
      console.log(`With TX: ${Date.now() - start2}ms`);
      process.exit(0);
    });
  });
}

run();
