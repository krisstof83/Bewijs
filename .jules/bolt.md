## 2026-05-19 - SQLite Transaction Batching
**Learning:** Default SQLite inserts using `db.run` wrap every statement in an implicit transaction, causing significant I/O overhead due to disk syncing. In a forensic app scanning hundreds of PDFs, this is a massive performance bottleneck.
**Action:** Always wrap bulk SQLite `INSERT` statements in an explicit `BEGIN TRANSACTION` and `COMMIT` block to improve performance dramatically. Combining this with a prepared statement (`db.prepare`) further reduces parsing overhead. Ensure to run them sequentially using `db.serialize()`.
