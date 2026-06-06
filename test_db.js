const sqlite3 = require('sqlite3').verbose()
const fs = require('fs')

function testWithoutTransaction() {
  return new Promise((resolve) => {
    const db = new sqlite3.Database(':memory:')
    db.run(`CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, name TEXT, date TEXT, hash TEXT)`, () => {
      console.time('without transaction')
      let count = 0;
      for (let i = 0; i < 1000; i++) {
        db.run('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)', ['path', 'name', 'date', 'hash'], () => {
          count++;
          if (count === 1000) {
            console.timeEnd('without transaction')
            resolve()
          }
        })
      }
    })
  })
}

function testWithTransaction() {
  return new Promise((resolve) => {
    const db = new sqlite3.Database(':memory:')
    db.run(`CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, name TEXT, date TEXT, hash TEXT)`, () => {
      console.time('with transaction')
      db.serialize(() => {
        db.run('BEGIN TRANSACTION')
        const stmt = db.prepare('INSERT INTO files (path, name, date, hash) VALUES (?, ?, ?, ?)')
        for (let i = 0; i < 1000; i++) {
          stmt.run('path', 'name', 'date', 'hash')
        }
        stmt.finalize()
        db.run('COMMIT', () => {
            console.timeEnd('with transaction')
            resolve()
        })
      })
    })
  })
}

async function run() {
  await testWithoutTransaction()
  await testWithTransaction()
}

run()
