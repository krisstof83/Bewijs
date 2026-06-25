## 2024-06-25 - Prevent SQLite Transaction Leakage
**Learning:** When batching SQLite inserts using `db.serialize()` with `BEGIN TRANSACTION`, synchronous operations (like `fs.readFileSync`) within the loop must be wrapped in a `try...catch`. Uncaught synchronous errors will prevent subsequent database operations (like `COMMIT`) from being queued, causing transaction leakage and permanently locking the database.
**Action:** Always wrap synchronous code within a `db.serialize()` block in a `try...catch` to ensure `COMMIT` or `ROLLBACK` executes, avoiding database lockups.
