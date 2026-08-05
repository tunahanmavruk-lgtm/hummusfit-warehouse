const Database = require('better-sqlite3');
const path = require('path');

// Railway: mount a volume at /data and set DB_PATH=/data/warehouse.db so this
// survives redeploys. Falls back to a local file for dev.
const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'warehouse.db');
const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');

db.exec(`
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL,           -- meal | muffin | oats | snack
  u30 REAL NOT NULL DEFAULT 0,      -- 30-day units sold (blended Shopify, until real pick data exists)
  cap INTEGER NOT NULL DEFAULT 24,  -- units per crate
  crate_w REAL NOT NULL DEFAULT 21.65,
  crate_d REAL NOT NULL DEFAULT 15.70,
  crate_h REAL NOT NULL DEFAULT 10.70
);

CREATE TABLE IF NOT EXISTS lanes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,        -- e.g. K1-07
  section TEXT NOT NULL,            -- bakery | meals
  row_num INTEGER NOT NULL,
  position_num INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS lane_assignments (
  lane_id INTEGER PRIMARY KEY REFERENCES lanes(id),
  product_id INTEGER REFERENCES products(id),
  crates_current INTEGER NOT NULL DEFAULT 0,
  max_stack INTEGER NOT NULL DEFAULT 5,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restock_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lane_id INTEGER REFERENCES lanes(id),
  product_id INTEGER REFERENCES products(id),
  crates_added INTEGER NOT NULL,
  ts TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS pick_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lane_id INTEGER REFERENCES lanes(id),
  product_id INTEGER REFERENCES products(id),
  qty INTEGER NOT NULL DEFAULT 1,
  ts TEXT DEFAULT CURRENT_TIMESTAMP
);
`);

// target_crates: live crate target from Shopify on-hand inventory
// (ceil(units_on_hand / cap)), replacing the old static 3.5-day demand
// forecast that ran way ahead of what's actually produced. NULL until the
// first successful sync. Added via ALTER since these columns didn't exist
// in earlier deploys -- guarded because SQLite errors on a duplicate ADD
// COLUMN and this file runs on every boot.
for (const stmt of [
  `ALTER TABLE products ADD COLUMN target_crates INTEGER`,
  `ALTER TABLE products ADD COLUMN target_crates_source TEXT`,
]) {
  try { db.exec(stmt); } catch (e) { /* column already exists, fine */ }
}

module.exports = db;
