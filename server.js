const express = require('express');
const path = require('path');
const db = require('./db');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ---------- Products ----------
app.get('/api/products', (req, res) => {
  res.json(db.prepare('SELECT * FROM products ORDER BY category, name').all());
});

// ---------- Floor plan / lanes ----------
app.get('/api/lanes', (req, res) => {
  const lanes = db.prepare(`
    SELECT
      l.id, l.code, l.section, l.row_num, l.position_num,
      la.product_id, la.crates_current, la.max_stack,
      p.name AS product_name, p.category, p.cap, p.u30
    FROM lanes l
    LEFT JOIN lane_assignments la ON la.lane_id = l.id
    LEFT JOIN products p ON p.id = la.product_id
    ORDER BY l.section, l.row_num, l.position_num
  `).all();
  res.json(lanes);
});

// Assign (or clear) a product to a lane. Body: { product_id: number|null, max_stack?: number }
app.put('/api/lanes/:id/assign', (req, res) => {
  const laneId = Number(req.params.id);
  const { product_id, max_stack } = req.body;
  const lane = db.prepare('SELECT * FROM lanes WHERE id = ?').get(laneId);
  if (!lane) return res.status(404).json({ error: 'lane not found' });

  const existing = db.prepare('SELECT * FROM lane_assignments WHERE lane_id = ?').get(laneId);
  if (product_id == null) {
    if (existing) db.prepare('DELETE FROM lane_assignments WHERE lane_id = ?').run(laneId);
    return res.json({ ok: true, cleared: true });
  }

  const product = db.prepare('SELECT * FROM products WHERE id = ?').get(product_id);
  if (!product) return res.status(404).json({ error: 'product not found' });

  if (existing) {
    db.prepare(`
      UPDATE lane_assignments SET product_id = ?, max_stack = COALESCE(?, max_stack), updated_at = CURRENT_TIMESTAMP
      WHERE lane_id = ?
    `).run(product_id, max_stack ?? null, laneId);
  } else {
    db.prepare(`
      INSERT INTO lane_assignments (lane_id, product_id, crates_current, max_stack)
      VALUES (?, ?, 0, COALESCE(?, 5))
    `).run(laneId, product_id, max_stack ?? null);
  }
  res.json({ ok: true });
});

// ---------- Restock ----------
// Add crates to a lane. Body: { crates_added: number }
app.post('/api/lanes/:id/restock', (req, res) => {
  const laneId = Number(req.params.id);
  const { crates_added } = req.body;
  if (!Number.isFinite(crates_added) || crates_added === 0) {
    return res.status(400).json({ error: 'crates_added must be a non-zero number' });
  }
  const assignment = db.prepare('SELECT * FROM lane_assignments WHERE lane_id = ?').get(laneId);
  if (!assignment) return res.status(400).json({ error: 'lane has no product assigned' });

  const newCount = Math.max(0, assignment.crates_current + crates_added);
  db.prepare(`
    UPDATE lane_assignments SET crates_current = ?, updated_at = CURRENT_TIMESTAMP WHERE lane_id = ?
  `).run(newCount, laneId);
  db.prepare(`
    INSERT INTO restock_log (lane_id, product_id, crates_added) VALUES (?, ?, ?)
  `).run(laneId, assignment.product_id, crates_added);

  res.json({ ok: true, crates_current: newCount });
});

// Recent restock activity feed
app.get('/api/restock-log', (req, res) => {
  const rows = db.prepare(`
    SELECT r.id, r.crates_added, r.ts, l.code AS lane_code, p.name AS product_name
    FROM restock_log r
    JOIN lanes l ON l.id = r.lane_id
    LEFT JOIN products p ON p.id = r.product_id
    ORDER BY r.ts DESC
    LIMIT 100
  `).all();
  res.json(rows);
});

// Lanes running low: fewer crates than max_stack - 1 (i.e. down to the top/reserve crate or below)
app.get('/api/low-stock', (req, res) => {
  const rows = db.prepare(`
    SELECT l.code, l.section, la.crates_current, la.max_stack, p.name AS product_name, p.cap
    FROM lane_assignments la
    JOIN lanes l ON l.id = la.lane_id
    JOIN products p ON p.id = la.product_id
    WHERE la.crates_current <= 1
    ORDER BY la.crates_current ASC, l.section, l.code
  `).all();
  res.json(rows);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Hummus Fit warehouse app running on port ${PORT}`);
});
