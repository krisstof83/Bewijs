
## 2026-05-27 - Batching SQLite Inserts
**Learning:** In Node.js `sqlite3`, inserting records one-by-one without a transaction forces a disk fsync for every `db.run()`, acting as a major performance bottleneck, especially in synchronous-heavy loops.
**Action:** Always batch multiple inserts using `BEGIN TRANSACTION` and `COMMIT` within `db.serialize()` to ensure performance scaling.
