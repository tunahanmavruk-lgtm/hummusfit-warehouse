# Hummus Fit Warehouse

Digital floor plan / lane config + restock tracking for the walk-in picking room. Built for a single shared kiosk tablet on the floor — no individual logins.

## Stack
- Node.js + Express
- SQLite via `better-sqlite3` (file-based; mount a Railway volume at `/data` in production and set `DB_PATH=/data/warehouse.db` so data survives redeploys)
- Static kiosk frontend in `public/` (vanilla JS, no build step)

## Local dev
```
npm install
npm run seed   # loads products.json + builds the lane layout (only needed once, or to reset)
npm start
```
Then open http://localhost:3000

## Layout
- 6 rows total: `K1`–`K3` (Bakery & Snacks: muffins, oats, snack bars) and `M1`–`M3` (Meals), ~27 positions per row, ~162 total floor positions.
- This is the corrected layout — 3 double-row blocks with 2 aisles. An earlier 8-row version was arithmetically wrong (each additional row block needs its own aisle) and was discarded.
- Products are auto-assigned to lanes by 30-day sales velocity on seed; reassign anytime from the Floor Plan tab.

## Known open item
Product velocity (`u30`) is currently blended 30-day Shopify sales (all channels), not warehouse-only pick data — Shopify doesn't reliably expose fulfillment-location-level sales for this store. A real 180-order Monday shipout batch was cross-checked against this and the category split roughly held (meals ~62% real vs 60% blended, muffins ~35% real vs 30% blended), so it's a reasonable proxy, not a verified one. Swap in real per-SKU daily averages if/when available — it's a single column update, not a rebuild.
