## 2024-05-20 - SQLite Bulk Inserts
**Learning:** Performing multiple individual `INSERT` statements in SQLite triggers a new transaction for each insert, causing massive I/O overhead.
**Action:** Always wrap multiple insertions in a single transaction (`BEGIN TRANSACTION` ... `COMMIT`) and use prepared statements (`db.prepare()`) when dealing with loops.
