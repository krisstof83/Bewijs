
## 2024-06-01 - [Optimize SQLite Inserts]
**Learning:** SQLite inserts without an explicit transaction in the `sqlite3` driver cause massive performance bottlenecks because each `INSERT` creates its own implicit transaction (triggering an fsync). When batching operations with `db.serialize()`, wrapping synchronous FS reads in `try/catch` is crucial to prevent uncaught errors from stopping the execution flow before `COMMIT` is called.
**Action:** Always wrap loops of `db.run` in `BEGIN TRANSACTION` and `COMMIT` when modifying multiple rows in Node.js, and use `db.prepare()` for the statements. Make sure that failures in reading files do not cause the entire transaction batch to fail or leave the database locked.
