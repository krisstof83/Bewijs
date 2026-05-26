## 2024-05-26 - SQLite Transaction Bottleneck
**Learning:** In Node.js `sqlite3`, inserting records one-by-one without a transaction forces a synchronous disk fsync for every `db.run()`, acting as a major performance bottleneck, especially when scanning hundreds of PDF files.
**Action:** Always batch multiple inserts using `BEGIN TRANSACTION` and `COMMIT` within `db.serialize()` to ensure performance scaling.
