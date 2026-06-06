## 2024-05-18 - [Tesseract Recognize API Performance vs Shared Worker]
**Learning:** Using `Tesseract.recognize` on every PDF/image parse takes significantly longer than reusing a shared `Worker` with `Tesseract.createWorker`, but creating a shared global worker in this module without terminating it causes process hangs in CLI environments and creates a concurrency bottleneck, because Tesseract workers process sequentially and can't be gracefully terminated without modifying consumer code.
**Action:** Do not use a globally shared worker in library code like `parser.js` unless lifecycle management is properly architected, or stick to `Tesseract.recognize` since it properly cleans up and allows concurrency, or optimize inside the batch processing loop instead.

## 2024-05-18 - [SQLite Bulk Insert Performance]
**Learning:** Inserting hundreds of files sequentially without a transaction causes SQLite to write to disk for every single insert, causing a massive performance bottleneck.
**Action:** When performing bulk database inserts in an Electron/Node environment, always wrap the inserts in a single transaction (`db.run('BEGIN TRANSACTION')`) and use prepared statements (`db.prepare(...)`) to maximize speed. Always use a `try...finally` block (or `try...catch`) to finalize statements and commit/rollback.
