## 2025-06-04 - SQLite Bulk Inserts Performance
**Learning:** In Node.js `sqlite3`, inserting records one-by-one without a transaction forces a disk fsync for every `db.run()`, which acts as a major performance bottleneck for large datasets like a filesystem scan.
**Action:** Always batch multiple inserts using `BEGIN TRANSACTION` and `COMMIT` within `db.serialize()` along with `db.prepare()` to ensure performance scaling. Wrap synchronous operations within the transaction in a `try...catch` so that failures don't leak the transaction.
