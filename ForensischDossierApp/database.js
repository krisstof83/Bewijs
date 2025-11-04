const sqlite3 = require('sqlite3').verbose()
const db = new sqlite3.Database('dossier.db')

db.run(`CREATE TABLE IF NOT EXISTS files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT,
  name TEXT,
  date TEXT,
  hash TEXT
)`)

module.exports = db