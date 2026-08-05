import json
svg = open('/home/claude/hummusfit-warehouse/backstock/backstock_blueprint.svg').read().strip()
g = json.load(open('/home/claude/hummusfit-warehouse/backstock/backstock_geometry.json'))
pos_fill = json.load(open('/home/claude/hummusfit-warehouse/backstock/position_fill.json'))

# name -> {position, lane, category, crates (static baseline)} lookup, embedded
# into the page so the live-inventory overlay (fetched client-side from
# /api/target-crates) has something to join against without another round
# trip. This is the same "location stays put, only the number changes" model
# used on blueprint.html.
product_positions = {}
for pos_code, pos in pos_fill.items():
    for pr in pos['products']:
        product_positions[pr['name']] = {
            'position': pos_code, 'lane': pr['lane'], 'cat': pos['cat'], 'crates': pr['crates'],
        }
product_positions_json = json.dumps(product_positions)

# Compute stat-card numbers from the live geometry instead of hardcoding them,
# so this script can't silently go stale again the way it just did (v4's
# numbers got shipped as "v7" until this was caught).
WA_BAYS, WA_LEVELS = 4, 7
WD_BAYS_OURS, WD_LEVELS = 2, 7
C_BAYS = g['center_bays']
C_LEVELS = 4  # still unconfirmed, see _relabel_v5_open
wa_positions = WA_BAYS * WA_LEVELS
wd_positions = WD_BAYS_OURS * WD_LEVELS
c_positions = C_BAYS * C_LEVELS
wa_span_ft = g['wall_a_total_span_in'] / 12
c_run_ft = g['center_total_run_in'] / 12

html_doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hummus Fit — Backstock Room (DRAFT v7, C07 added, real measurements)</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800;900&display=swap" rel="stylesheet">
<style>
  :root{{ --teal:#2BBFAA; --orange:#E8612C; --ink:#111417; --dim:#767c85; --line:#e9ebee; --bg:#fafafa; --green:#2e9e5b; }}
  *{{box-sizing:border-box;}}
  body{{margin:0;font-family:'Inter',sans-serif;background:var(--bg);color:var(--ink);}}
  .wrap{{max-width:1200px;margin:0 auto;padding:32px 28px 60px;}}
  h1{{font-size:24px;margin:0 0 4px;font-weight:900;}}
  .sub{{color:var(--dim);font-size:14px;margin:0 0 20px;font-weight:600;}}
  .confirmedbanner{{background:#eafaf0;border:1.5px solid var(--green);border-radius:14px;padding:16px 20px;margin-bottom:16px;}}
  .confirmedbanner h2{{margin:0 0 8px;font-size:14px;color:var(--green);text-transform:uppercase;letter-spacing:.04em;}}
  .confirmedbanner ul{{margin:0;padding-left:20px;font-size:13px;line-height:1.6;color:#1e5c37;}}
  .draftbanner{{background:#fff3ea;border:1.5px solid var(--orange);border-radius:14px;padding:16px 20px;margin-bottom:24px;}}
  .draftbanner h2{{margin:0 0 8px;font-size:14px;color:var(--orange);text-transform:uppercase;letter-spacing:.04em;}}
  .draftbanner ul{{margin:0;padding-left:20px;font-size:13px;line-height:1.6;color:#5a4130;}}
  .diagram-card{{background:#fff;border:1.5px solid var(--line);border-radius:20px;padding:20px;overflow-x:auto;margin-bottom:28px;}}
  .diagram-card svg{{display:block;width:100%;height:auto;min-width:500px;}}
  .statgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:28px;}}
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
  <span class="live-badge" id="liveBadge"><span class="dot"></span><span id="liveBadgeText">Checking live inventory…</span></span>

  <div class="statgrid">
    <div class="stat"><div class="n">{wd_positions}</div><div class="l">positions — Wall D ({WD_BAYS_OURS}×{WD_LEVELS})</div></div>
    <div class="stat"><div class="n">{wa_positions}</div><div class="l">positions — Wall A ({WA_BAYS}×{WA_LEVELS}, {wa_span_ft:.0f}ft)</div></div>
    <div class="stat"><div class="n">{c_positions}</div><div class="l">positions — Center front ({C_BAYS}×{C_LEVELS}, {c_run_ft:.1f}ft, levels unconfirmed)</div></div>
  </div>

  <div class="diagram-card">{svg}</div>

  <div class="livetable">
    <h2>Live crate targets by position</h2>
    <p class="hint">Position stays fixed — only the crate count updates, pulled straight from Shopify on-hand inventory every 20 minutes. Rows still showing the old baseline number haven't matched a Shopify product name yet.</p>
    <table>
      <thead><tr><th>Position</th><th>Lane</th><th>Product</th><th>Category</th><th>Crates</th></tr></thead>
      <tbody id="liveTableBody"><tr><td colspan="5" style="color:var(--dim);">Loading…</td></tr></tbody>
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
      return `<tr class="${{isLive ? '' : 'stale'}}"><td>${{p.position}}</td><td>${{p.lane}}</td><td>${{name}}</td><td>${{p.cat}}</td><td class="n">${{crates}}${{isLive ? '' : ' (baseline)'}}</td></tr>`;
    }});
  document.getElementById('liveTableBody').innerHTML = rows.join('') || '<tr><td colspan="5">No positions found.</td></tr>';
  if (!data.last_sync) {{ badgeText.textContent = 'Live inventory not connected yet'; return; }}
  badge.classList.add('on');
  badgeText.textContent = `Live inventory synced ${{new Date(data.last_sync).toLocaleString()}}`;
}}).catch(() => {{
  document.getElementById('liveBadgeText').textContent = 'Live inventory unavailable';
  document.getElementById('liveTableBody').innerHTML = '<tr><td colspan="5">Could not load live data.</td></tr>';
}});
</script>
</body></html>
'''
open('/home/claude/hummusfit-warehouse/backstock/backstock_blueprint.html', 'w').write(html_doc)
print('HTML written', len(html_doc), 'bytes')
