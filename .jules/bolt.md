## 2024-05-18 - SQLite Performance Bottleneck in Electron App
**Learning:** Inserting records one-by-one in Node.js `sqlite3` without a transaction forces a disk fsync for every `db.run()`, acting as a major performance bottleneck for bulk operations.
**Action:** Always batch multiple inserts using `BEGIN TRANSACTION` and `COMMIT` within `db.serialize()` along with `db.prepare()` to ensure performance scaling. Wrap synchronous operations within `db.serialize()` in `try...catch` blocks to prevent uncaught errors from leaking transactions and locking the database.
