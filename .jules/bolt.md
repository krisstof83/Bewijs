## 2024-05-25 - SQLite Batch Insert Bottleneck
**Learning:** In Node.js `sqlite3`, inserting records one-by-one without a transaction forces a disk fsync for every `db.run()`, which acts as a major performance bottleneck when processing large numbers of files like PDFs in the user's home directory.
**Action:** Always batch multiple inserts using `BEGIN TRANSACTION` and `COMMIT` within `db.serialize()` to ensure performance scaling.
