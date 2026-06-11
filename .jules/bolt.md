## 2024-06-11 - Optimize SQLite Batch Inserts
**Learning:** In Node.js `sqlite3`, `db.serialize()` serializes statements, but if synchronous operations inside the loop (like `fs.readFileSync`) throw uncaught errors, it interrupts the normal execution flow and prevents `COMMIT` from being queued. This leads to transaction leakage and permanently locks the database.
**Action:** Always wrap synchronous operations inside a `db.serialize()` transaction loop in a `try...catch` block to ensure execution proceeds to the `COMMIT` statement and prevents database locks.
