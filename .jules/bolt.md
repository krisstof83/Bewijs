## 2025-10-24 - Transaction leakage in Node.js SQLite3 batch inserts
**Learning:** In Node.js `sqlite3`, uncaught synchronous errors (like `fs.readFileSync` failing on a file) inside a `db.serialize()` block will prevent subsequent queued operations (like `COMMIT`) from executing. This causes the transaction to leak, permanently locking the database.
**Action:** Always wrap synchronous operations inside a `db.serialize()` transaction block with a `try...catch` block to ensure `COMMIT` or `ROLLBACK` is reached and the database transaction finishes successfully.
