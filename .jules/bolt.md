## 2024-05-18 - SQLite Loop Inserts
**Learning:** In the Electron app, SQLite inserts are performed inside a loop without an explicit transaction in `renderer.js` when scanning PDFs. This causes SQLite to autocommit each insert individually, which forces a disk sync for every file and severely degrades performance.
**Action:** Always wrap multiple SQLite inserts in a `BEGIN TRANSACTION` and `COMMIT` block (using `db.serialize` and prepared statements) when iterating over collections, especially for file metadata storage.
