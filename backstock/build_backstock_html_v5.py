import json

svg = open('/home/claude/hummusfit-warehouse/backstock/backstock_blueprint.svg').read().strip()
positions = json.load(open('/home/claude/hummusfit-warehouse/backstock/position_fill_v5.json'))

real = {code: v for code, v in positions.items() if v.get('code')}

product_positions = {}
for code, v in real.items():
    product_positions[v['product']] = {
        'position': code, 'lane': code, 'cat': v['cat'], 'crates': v['crates'],
    }
product_positions_json = json.dumps(product_positions)

n_walld = sum(1 for v in real.values() if v['zone'] == 'walld')
n_walla = sum(1 for v in real.values() if v['zone'] == 'walla')
n_pallet = sum(1 for v in real.values() if v['zone'] == 'pallet')
n_center = sum(1 for v in real.values() if v['zone'] == 'center')

html_doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hummus Fit — Backstock Room</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800;900&display=swap" rel="stylesheet">
<style>
  :root{{ --teal:#2BBFAA; --orange:#E8612C; --ink:#111417; --dim:#767c85; --line:#e9ebee; --bg:#fafafa; --green:#2e9e5b; }}
  *{{box-sizing:border-box;}}
  body{{margin:0;font-family:'Inter',sans-serif;background:var(--bg);color:var(--ink);}}
  .wrap{{max-width:1200px;margin:0 auto;padding:32px 28px 60px;}}
  h1{{font-size:24px;margin:0 0 4px;font-weight:900;}}
  .sub{{color:var(--dim);font-size:14px;margin:0 0 20px;font-weight:600;}}
  .confirmedbanner{{background:#eafaf0;border:1.5px solid var(--green);border-radius:14px;padding:16px 20px;margin-bottom:24px;}}
  .confirmedbanner h2{{margin:0 0 8px;font-size:14px;color:var(--green);text-transform:uppercase;letter-spacing:.04em;}}
  .confirmedbanner ul{{margin:0;padding-left:20px;font-size:13px;line-height:1.6;color:#1e5c37;}}
  .diagram-card{{background:#fff;border:1.5px solid var(--line);border-radius:20px;padding:20px;overflow-x:auto;margin-bottom:28px;}}
  .diagram-card svg{{display:block;width:100%;height:auto;min-width:700px;}}
  .statgrid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px;}}
  .stat{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:16px;text-align:center;}}
  .stat .n{{font-size:26px;font-weight:900;color:var(--teal);}}
  .stat .l{{font-size:11.5px;color:var(--dim);font-weight:700;text-transform:uppercase;margin-top:4px;}}
  .pagenav{{display:flex;gap:8px;margin-bottom:16px;}}
  .pagenav a{{text-decoration:none;font-size:13px;font-weight:800;color:var(--dim);border:1.5px solid var(--line);border-radius:10px;padding:9px 18px;}}
  .pagenav a.active{{background:var(--ink);color:#fff;border-color:var(--ink);}}
  .live-badge{{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:700;color:var(--dim);margin-bottom:20px;}}
  .live-badge .dot{{width:8px;height:8px;border-radius:50%;background:#c7cbd1;}}
  .live-badge.on .dot{{background:var(--teal);}}
  .livetable{{background:#fff;border:1.5px solid var(--line);border-radius:20px;padding:20px;margin-bottom:28px;}}
  .livetable h2{{font-size:15px;margin:0 0 4px;}}
  .livetable .hint{{color:var(--dim);font-size:12.5px;margin:0 0 14px;}}
  .livetable table{{width:100%;border-collapse:collapse;font-size:13px;}}
  .livetable th{{text-align:left;color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.03em;padding:6px 10px;border-bottom:1.5px solid var(--line);}}
  .livetable td{{padding:7px 10px;border-bottom:1px solid var(--line);}}
  .livetable td.n{{font-weight:800;color:var(--teal);}}
  .livetable tr.stale td.n{{color:var(--dim);font-weight:600;}}
</style></head>
<body><div class="wrap">
  <div class="pagenav"><a href="/blueprint.html">Blueprint</a><a href="/3d-model.html">3D Model</a><a href="/backstock-blueprint.html" class="active">Backstock Blueprint</a><a href="/backstock-3d.html">Backstock 3D</a></div>
  <h1>Backstock Room</h1>
  <div class="sub">Every position uses the SAME code as the main walk-in blueprint — M1/M2/M3 for meals, K1/K2 for bakery/oats/snacks. No separate backstock code to learn.</div>
  <span class="live-badge" id="liveBadge"><span class="dot"></span><span id="liveBadgeText">Checking live inventory…</span></span>

  <div class="confirmedbanner">
    <h2>Confirmed layout</h2>
    <ul>
      <li>Wall D → M1 (2 floors × 16 slots, 28 real codes)</li>
      <li>Wall A → M3 (2 shelves, 27 codes)</li>
      <li>Middle pallet row → M2 (8 double-sided pallets, 28 codes)</li>
      <li>Center → K1 floor 1 (35 codes) / K2 floor 2 (30 codes) — codes stay in their natural alphabetical/pipeline order</li>
    </ul>
  </div>

  <div class="statgrid">
    <div class="stat"><div class="n">{n_walld}</div><div class="l">Wall D positions (M1)</div></div>
    <div class="stat"><div class="n">{n_walla}</div><div class="l">Wall A positions (M3)</div></div>
    <div class="stat"><div class="n">{n_pallet}</div><div class="l">Pallet positions (M2)</div></div>
    <div class="stat"><div class="n">{n_center}</div><div class="l">Center positions (K1/K2)</div></div>
  </div>

  <div class="diagram-card">{svg}</div>

  <div class="livetable">
    <h2>Live crate targets by position</h2>
    <p class="hint">Position stays fixed — only the crate count updates, pulled straight from Shopify on-hand inventory every 20 minutes. Rows still showing the old baseline number haven't matched a Shopify product name yet.</p>
    <table>
      <thead><tr><th>Code</th><th>Product</th><th>Category</th><th>Crates</th></tr></thead>
      <tbody id="liveTableBody"><tr><td colspan="4" style="color:var(--dim);">Loading…</td></tr></tbody>
    </table>
  </div>
</div>
<script>
const PRODUCT_POSITIONS = {product_positions_json};
fetch('/api/target-crates').then(r => r.json()).then(data => {{
  const badge = document.getElementById('liveBadge');
  const badgeText = document.getElementById('liveBadgeText');
  const live = data.products || {{}};
  const rows = Object.entries(PRODUCT_POSITIONS)
    .sort((a, b) => a[1].position.localeCompare(b[1].position))
    .map(([name, p]) => {{
      const l = live[name];
      const isLive = l && l.target_crates != null;
      const crates = isLive ? l.target_crates : p.crates;
      return `<tr class="${{isLive ? '' : 'stale'}}"><td>${{p.position}}</td><td>${{name}}</td><td>${{p.cat}}</td><td class="n">${{crates}}${{isLive ? '' : ' (baseline)'}}</td></tr>`;
    }});
  document.getElementById('liveTableBody').innerHTML = rows.join('') || '<tr><td colspan="4">No positions found.</td></tr>';
  if (!data.last_sync) {{ badgeText.textContent = 'Live inventory not connected yet'; return; }}
  badge.classList.add('on');
  badgeText.textContent = `Live inventory synced ${{new Date(data.last_sync).toLocaleString()}}`;
}}).catch(() => {{
  document.getElementById('liveBadgeText').textContent = 'Live inventory unavailable';
  document.getElementById('liveTableBody').innerHTML = '<tr><td colspan="4">Could not load live data.</td></tr>';
}});
</script>
</body></html>
'''
open('/home/claude/hummusfit-warehouse/backstock/backstock_blueprint.html', 'w').write(html_doc)
print('HTML written', len(html_doc), 'bytes')
