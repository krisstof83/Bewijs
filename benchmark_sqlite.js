const sqlite3 = require('sqlite3').verbose();
const db = new sqlite3.Database('test.db');
const fs = require('fs');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT,
    name TEXT,
    date TEXT,
    hash TEXT
  )`);

  const runWithTransaction = () => {
    return new Promise((resolve) => {
      const start = Date.now();
      db.run("BEGIN TRANSACTION");
      for (let i = 0; i < 1000; i++) {
        db.run('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)', ['/test/path', 'test.pdf', '2023-01-01', 'hash']);
      }
      db.run("COMMIT", () => {
        console.log(`With transaction: ${Date.now() - start}ms`);
        resolve();
      });
    });
  };

  const runWithoutTransaction = () => {
    return new Promise((resolve) => {
      const start = Date.now();
      let completed = 0;
      for (let i = 0; i < 1000; i++) {
        db.run('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)', ['/test/path', 'test.pdf', '2023-01-01', 'hash'], () => {
          completed++;
          if (completed === 1000) {
            console.log(`Without transaction: ${Date.now() - start}ms`);
            resolve();
          }
        });
      }
    });
  };

  runWithoutTransaction().then(() => runWithTransaction());
});
