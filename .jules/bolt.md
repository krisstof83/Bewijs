
## 2026-05-21 - SQLite Bulk Inserts Performance
**Learning:** In SQLite, every individual `INSERT` statement is wrapped in its own transaction by default, causing a full disk sync for every file processed. For bulk operations (like scanning hundreds of PDFs), this is a massive performance bottleneck.
**Action:** When performing multiple database modifications (like inserts), always wrap them in an explicit transaction (`BEGIN TRANSACTION` / `COMMIT`) and reuse a prepared statement. Include a `try...finally` block with rollback logic to ensure data integrity during file processing errors.
