## 2024-05-17 - [SQLite Bulk Inserts]
**Learning:** SQLite in Node.js performs each `INSERT` in a separate transaction by default, causing excessive disk I/O and making bulk operations slow.
**Action:** Always wrap multiple consecutive `INSERT` statements in an explicit transaction (`BEGIN TRANSACTION` and `COMMIT`) using `db.serialize()` to dramatically improve performance.
