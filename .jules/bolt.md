## 2024-05-15 - SQLite Bulk Insert Optimization
**Learning:** Default `db.run('INSERT ...')` in SQLite without an explicit transaction wrapper triggers a separate file system sync (autocommit) per insert. This represents a massive disk I/O bottleneck when parsing and storing thousands of files sequentially.
**Action:** Always wrap multiple SQLite inserts inside `db.serialize()` with a `db.run('BEGIN TRANSACTION')` and `db.run('COMMIT')`. Combine this with a prepared statement (`db.prepare()`) to cut down statement compilation time and drastically reduce insertion overhead to milliseconds.
