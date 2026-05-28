## 2024-03-24 - SQLite Node.js Performance Tuning
**Learning:** In Node.js `sqlite3`, inserting records one-by-one without a transaction forces a disk fsync for every `db.run()`, acting as a major performance bottleneck.
**Action:** Always batch multiple inserts using `BEGIN TRANSACTION` and `COMMIT` within `db.serialize()` along with `db.prepare()` to ensure performance scaling.
