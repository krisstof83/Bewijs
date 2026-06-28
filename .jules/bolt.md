## 2024-05-15 - SQLite Fsync Bottleneck and Transaction Leaks

**Learning:** In Node.js `sqlite3`, inserting records one-by-one without a transaction forces a disk fsync for every `db.run()`, acting as a major performance bottleneck for bulk operations. Furthermore, when batching inserts using `db.serialize()`, if a synchronous error occurs inside the transaction block (such as an error reading a file synchronously using `fs.readFileSync`), it can prevent the `COMMIT` operation from being queued, causing transaction leakage and permanently locking the database for the rest of the application's lifecycle.

**Action:** Always batch multiple inserts using `BEGIN TRANSACTION` and `COMMIT` within `db.serialize()` along with `db.prepare()` to ensure performance scaling. Crucially, always wrap synchronous operations that can throw inside the transaction block with a `try...catch` statement to handle errors safely and ensure `COMMIT` or `ROLLBACK` commands are successfully queued.
