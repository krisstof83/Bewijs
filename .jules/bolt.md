
## 2024-05-18 - SQLite transactions and file hashing streams
**Learning:** In Electron Node.js environments processing many files, synchronous file reads (`fs.readFileSync`) block the main thread, and inserting into SQLite outside of a transaction executes an fsync for every row, drastically slowing down processing.
**Action:** Always use streams (`fs.createReadStream`) for processing large file data (like hashes) and always wrap multiple SQLite inserts in `BEGIN TRANSACTION` and `COMMIT` within a `db.serialize()` block to maximize batch insert performance.
