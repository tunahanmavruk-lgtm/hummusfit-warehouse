// Seeds products + lanes into the SQLite db.
// Layout: 6 rows total = 3 double-row blocks, 2 aisles (the corrected, honest
// layout — NOT the flawed 8-row version). Bakery & Snacks = K1-K3, Meals = M1-M3.
// ~27 positions/row -> ~162 total floor positions.
const fs = require('fs');
const path = require('path');

function capFor(p) {
  if (p.cat === 'meal') return 24;
  if (p.cat === 'muffin') return 24;
  if (p.cat === 'oats') return 28;
  if (p.cat === 'snack') {
    if (/gree-yo|pudding/i.test(p.name)) return 28;
    if (/buff crisp bar/i.test(p.name)) return 48;
    return 24; // poppers, energy bites, etc.
  }
  return 24;
}

function runSeed(db) {
  const products = JSON.parse(
    fs.readFileSync(path.join(__dirname, 'products.json'), 'utf8')
  );

  const insertProduct = db.prepare(`
    INSERT INTO products (name, category, u30, cap, crate_w, crate_d, crate_h)
    VALUES (@name, @category, @u30, @cap, 21.65, 15.70, 10.70)
    ON CONFLICT(name) DO UPDATE SET
      category=excluded.category, u30=excluded.u30, cap=excluded.cap
  `);

  const insertLane = db.prepare(`
    INSERT OR IGNORE INTO lanes (code, section, row_num, position_num)
    VALUES (?, ?, ?, ?)
  `);

  const insertAssignment = db.prepare(`
    INSERT OR IGNORE INTO lane_assignments (lane_id, product_id, crates_current, max_stack)
    VALUES (?, ?, 0, 5)
  `);

  const seed = db.transaction(() => {
    for (const p of products) {
      insertProduct.run({
        name: p.name,
        category: p.cat,
        u30: p.u30,
        cap: capFor(p),
      });
    }

    const POSITIONS_PER_ROW = 27;
    const sections = [
      { section: 'bakery', rows: ['K1', 'K2', 'K3'] },
      { section: 'meals', rows: ['M1', 'M2', 'M3'] },
    ];
    for (const s of sections) {
      s.rows.forEach((rowLabel, rowIdx) => {
        for (let pos = 1; pos <= POSITIONS_PER_ROW; pos++) {
          const code = `${rowLabel}-${String(pos).padStart(2, '0')}`;
          insertLane.run(code, s.section, rowIdx + 1, pos);
        }
      });
    }

    const bakeryProducts = db
      .prepare(`SELECT * FROM products WHERE category != 'meal' ORDER BY u30 DESC`)
      .all();
    const mealProducts = db
      .prepare(`SELECT * FROM products WHERE category = 'meal' ORDER BY u30 DESC`)
      .all();

    const bakeryLanes = db
      .prepare(`SELECT * FROM lanes WHERE section = 'bakery' ORDER BY row_num, position_num`)
      .all();
    const mealLanes = db
      .prepare(`SELECT * FROM lanes WHERE section = 'meals' ORDER BY row_num, position_num`)
      .all();

    bakeryProducts.forEach((prod, i) => {
      if (bakeryLanes[i]) insertAssignment.run(bakeryLanes[i].id, prod.id);
    });
    mealProducts.forEach((prod, i) => {
      if (mealLanes[i]) insertAssignment.run(mealLanes[i].id, prod.id);
    });

    return {
      products: products.length,
      lanes: bakeryLanes.length + mealLanes.length,
      bakeryAssigned: Math.min(bakeryProducts.length, bakeryLanes.length),
      mealAssigned: Math.min(mealProducts.length, mealLanes.length),
      unassignedBakery: Math.max(0, bakeryProducts.length - bakeryLanes.length),
      unassignedMeals: Math.max(0, mealProducts.length - mealLanes.length),
    };
  });

  return seed();
}

module.exports = { runSeed };

// Allow running directly: `node seed.js`
if (require.main === module) {
  const db = require('./db');
  const result = runSeed(db);
  console.log('Seed complete:', result);
  if (result.unassignedBakery || result.unassignedMeals) {
    console.log(
      `WARNING: ${result.unassignedBakery} bakery/snack + ${result.unassignedMeals} meal products had no lane to land in. ` +
      `This is the known floor-capacity shortfall — see notes.`
    );
  }
}
