## 2024-05-24 - SQLite Insert Performance
**Learning:** Inserting records one-by-one into SQLite without a transaction forces a disk fsync for every `db.run()`, which is a major performance bottleneck. Uncaught synchronous errors (like `fs.readFileSync`) within `db.serialize()` prevent subsequent db operations (like `COMMIT`) from queuing, permanently locking the database.
**Action:** Always batch multiple inserts using `BEGIN TRANSACTION` and `COMMIT` within `db.serialize()` with `db.prepare()`. Wrap synchronous operations within the transaction block in a `try...catch` block.
