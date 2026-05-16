## 2025-05-16 - Add database index on date field
**Learning:** Found a missing index on the `date` field in `database.js` which is queried with `ORDER BY date` in `renderer.js`. Adding an index improves retrieval speed.
**Action:** Always check for missing indexes on frequently queried or ordered fields in SQLite databases.
