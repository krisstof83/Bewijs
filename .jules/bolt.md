## 2024-05-14 - SQLite Bulk Insert Performance
**Learning:** SQLite wraps each `INSERT` into an individual transaction by default if it's not wrapped in a manual transaction. This is extremely slow for bulk inserts like scanning many files, due to excessive disk I/O and synchronous `fsync` calls for each insert.
**Action:** When performing multiple inserts (e.g., scanning multiple files), always wrap them in `db.serialize` with a `BEGIN TRANSACTION` and a `COMMIT` statement to execute them in batches.
