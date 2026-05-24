## 2025-02-24 - SQLite Transaction Performance
**Learning:** Inserting records one-by-one in Node.js `sqlite3` without a transaction forces a disk fsync for every single `db.run()`, acting as a major bottleneck during large file scans.
**Action:** Always wrap multiple SQLite inserts in `BEGIN TRANSACTION` and `COMMIT` using `db.serialize()` and `db.prepare()`.
