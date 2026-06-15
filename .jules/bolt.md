## 2025-10-24 - Uncaught Synchronous Errors in db.serialize() causing Database Locking
**Learning:** When batching SQLite inserts using `db.serialize()` with Node.js `sqlite3`, any synchronous operation (like `fs.readFileSync`) within the block needs to be carefully handled. An uncaught synchronous error will prevent subsequent operations (like `COMMIT`) from queueing up properly. This can cause the transaction to leak and the database to become locked.
**Action:** Always wrap synchronous logic inside a `try...catch` block when operating within a `db.serialize()` transaction.
