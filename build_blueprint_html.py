"""
Assembles the full blueprint.html from the generated SVG (blueprint.svg)
and the per-lane product plan (lane_plan.json). Rewritten as a single
generator (instead of generating the SVG and hand-splicing it into a
hand-written HTML shell) so the product legend stays in sync with the
drawing automatically instead of drifting out of sync across manual edits.

Per direct feedback: the numbered flaw/assumption callouts and the raw
site-survey photos were cluttering the page and aren't wanted here anymore
— dropped. In their place: a single rendered mockup image (from the 3D
model, with real crate stacks placed) so the page shows what the stocked
room actually looks like instead of an empty room photo.
"""
import json, html, base64

def data_uri(path, mime='image/jpeg'):
    b = open(path, 'rb').read()
    return f'data:{mime};base64,' + base64.b64encode(b).decode('ascii')

svg = open('/home/claude/hummusfit-warehouse/blueprint.svg').read().strip()
lane_plan = json.load(open('/home/claude/hummusfit-warehouse/lane_plan.json'))

ROWS_ORDER = ['K1', 'K2', 'K3', 'M1', 'M2', 'M3']
ROW_SECTION = {'K1': 'bakery', 'K2': 'bakery', 'K3': 'bakery', 'M1': 'meals', 'M2': 'meals', 'M3': 'meals'}

lanes_by_row = {r: [] for r in ROWS_ORDER}
for sec in lane_plan.values():
    for l in sec['lanes']:
        row = l['code'].split('-')[0]
        lanes_by_row[row].append(l)
for r in lanes_by_row:
    lanes_by_row[r].sort(key=lambda l: int(l['code'].split('-')[1]))

def esc(s):
    return html.escape(str(s))

# ---- product legend: one card per row, a compact grid of lane-code ->
# product cells, color-coded by category, so staff can find "what goes in
# K1-07" by looking at the row card instead of hunting a spreadsheet ----
CAT_COLOR = {
    'muffin': '#2BBFAA', 'oats': '#4C9BE8', 'snack': '#E8612C', 'meal': '#111417',
}
CAT_LABEL = {
    'muffin': 'Muffin', 'oats': 'Oats', 'snack': 'Snack', 'meal': 'Meal',
}

def legend_row_card(r):
    lanes = lanes_by_row[r]
    sec = ROW_SECTION[r]
    accent = '#2BBFAA' if sec == 'bakery' else '#111417'
    cells = []
    for l in lanes:
        color = CAT_COLOR.get(l['category'], '#767c85')
        flag = ''
        if l['demand_source'] != 'real':
            flag = '<span class="lc-flag" title="No real order match — corrected blended estimate">~</span>'
        cells.append(f'''<div class="lc-cell">
      <div class="lc-code" style="color:{color}">{esc(l['code'])}{flag}</div>
      <div class="lc-name">{esc(l['product'])}</div>
      <div class="lc-meta">{esc(l['crates_needed'])} crate{'s' if l['crates_needed']!=1 else ''} · {CAT_LABEL.get(l['category'], l['category'])}</div>
    </div>''')
    used = len(lanes)
    return f'''<div class="rowcard">
    <div class="rowcard-head" style="border-color:{accent}">
      <span class="rowcard-title" style="color:{accent}">Row {r}</span>
      <span class="rowcard-sub">{used}/27 positions in use</span>
    </div>
    <div class="lc-grid">{''.join(cells)}</div>
  </div>'''

legend_html = '\n'.join(legend_row_card(r) for r in ROWS_ORDER)

mockup_uri = data_uri('/home/claude/hummusfit-warehouse/mockup.png', mime='image/png')

html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hummus Fit — Walk-In Blueprint (Birds-Eye)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800;900&display=swap" rel="stylesheet">
<style>
  :root{{ --teal:#2BBFAA; --orange:#E8612C; --ink:#111417; --dim:#767c85; --line:#e9ebee; --bg:#fafafa; }}
  *{{box-sizing:border-box;}}
  body{{margin:0;font-family:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);}}
  .wrap{{max-width:1400px;margin:0 auto;padding:32px 28px 60px;}}
  .pagenav{{display:flex;gap:8px;margin-bottom:16px;}}
  .pagenav a{{text-decoration:none;font-size:13px;font-weight:800;color:var(--dim);border:1.5px solid var(--line);border-radius:10px;padding:9px 18px;}}
  .pagenav a.active{{background:var(--ink);color:#fff;border-color:var(--ink);}}
  h1{{font-size:24px;margin:0 0 4px;font-weight:900;letter-spacing:-.01em;}}
  .sub{{color:var(--dim);font-size:14px;margin:0 0 28px;font-weight:600;}}
  .diagram-card{{background:#fff;border:1.5px solid var(--line);border-radius:20px;padding:20px;overflow-x:auto;margin-bottom:32px;}}
  .diagram-card svg{{display:block;width:100%;height:auto;min-width:900px;}}
  h2{{font-size:15px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);margin:0 0 14px;font-weight:800;}}
  .legend{{display:flex;flex-wrap:wrap;gap:22px;margin-bottom:28px;background:#fff;border:1.5px solid var(--line);border-radius:16px;padding:18px 20px;}}
  .legend .item{{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:var(--dim);}}
  .legend .swatch{{width:16px;height:16px;border-radius:4px;flex:none;}}
  .swatch.bakery{{background:#eafaf7;border:1.5px solid var(--teal);}}
  .swatch.meals{{background:#eef0f4;border:1.5px solid var(--ink);}}
  .swatch.path{{background:none;border-bottom:3px dashed var(--teal);height:0;width:20px;}}
  .stackcard{{background:#fff;border:1.5px solid var(--line);border-radius:16px;padding:22px 24px;margin-bottom:28px;}}
  .stackrow{{display:flex;align-items:flex-end;gap:6px;margin-top:14px;}}
  .crate{{width:70px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:#fff;}}
  .crate.pick{{background:var(--teal);height:38px;}}
  .crate.reserve{{background:var(--orange);height:38px;}}
  .stacklabel{{font-size:13px;color:var(--dim);font-weight:600;margin-left:20px;}}
  .footnote{{font-size:12.5px;color:var(--dim);text-align:center;margin-top:8px;}}
  .mockupcard{{background:#fff;border:1.5px solid var(--line);border-radius:20px;padding:20px;margin-bottom:32px;}}
  .mockupcard img{{width:100%;height:auto;display:block;border-radius:14px;background:#dfe3e6;}}
  .rowcard{{background:#fff;border:1.5px solid var(--line);border-radius:16px;margin-bottom:16px;overflow:hidden;}}
  .rowcard-head{{display:flex;align-items:baseline;gap:12px;padding:14px 18px;border-bottom:2px solid;}}
  .rowcard-title{{font-size:15px;font-weight:900;}}
  .rowcard-sub{{font-size:12px;color:var(--dim);font-weight:600;}}
  .lc-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:1px;background:var(--line);}}
  .lc-cell{{background:#fff;padding:10px 12px;min-height:64px;}}
  .lc-code{{font-size:11.5px;font-weight:800;letter-spacing:.02em;}}
  .lc-flag{{color:var(--orange);font-weight:900;margin-left:2px;}}
  .lc-name{{font-size:12px;font-weight:600;color:var(--ink);line-height:1.3;margin-top:2px;}}
  .lc-meta{{font-size:10.5px;color:var(--dim);margin-top:3px;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="pagenav"><a href="/blueprint.html" class="active">Blueprint</a><a href="/3d-model.html">3D Model</a></div>
  <h1>Walk-In Storage Blueprint — Birds-Eye View</h1>
  <p class="sub">To scale · single view · pathway runs in the aisles only, never across a crate row</p>

  <div class="mockupcard">
    <h2 style="margin-bottom:6px;">Room Mockup — Fully Stocked</h2>
    <p class="sub" style="margin-bottom:12px;">Generated from the same room geometry and product plan as the drawing below, with every lane's real crate stack placed. Open the full interactive version on the <a href="/3d-model.html">3D Model</a> page.</p>
    <img src="{mockup_uri}" alt="Rendered mockup of the walk-in with crate stacks placed in every lane">
  </div>

  <div class="diagram-card">
    {svg}
  </div>

  <div class="legend">
    <div class="item"><span class="swatch bakery"></span>Bakery &amp; Snacks (K1-K3)</div>
    <div class="item"><span class="swatch meals"></span>Meals (M1-M3)</div>
    <div class="item">┄┄&gt;&nbsp; Picker walking path, aisles only (in and out the same door)</div>
    <div class="item">●&nbsp; filled dot = position stocked &nbsp;&nbsp; ○&nbsp; open dot = position empty</div>
  </div>

  <h2>Product Legend — Every Lane, By Row</h2>
  <p class="sub" style="margin-top:-10px;">Cross-references the lane codes on the drawing above. "~" next to a code means that lane's count is a corrected blended estimate — no real order for that product in the sample used.</p>
  {legend_html}

  <div class="stackcard">
    <h2 style="margin-bottom:6px;">Crate Stack — Side View (per lane)</h2>
    <p class="sub" style="margin-bottom:0;">21.65"L x 15.70"W x 10.70"H crates, self-stacking lid grooves. Applies to every lane in every row above.</p>
    <div class="stackrow">
      <div style="display:flex;flex-direction:column-reverse;gap:4px;">
        <div class="crate pick">1</div>
        <div class="crate pick">2</div>
        <div class="crate pick">3</div>
        <div class="crate pick">4</div>
        <div class="crate reserve">5</div>
      </div>
      <div class="stacklabel">
        Bottom 4 (teal) = active pick face, grabbed straight off without a stool.<br>
        Top 1 (orange) = reserve only — restock crew brings it down when a pick-face crate empties.<br>
        5 crates x 10.70" = 53.5" — clears the 10' ceiling with room for the lid-groove stacking mechanism.
      </div>
    </div>
  </div>

  <p class="footnote">Generated from the room dimensions and the real 178-order demand sample. Product legend generated directly from lane_plan.json — the same file that drives the live picking app.</p>
</div>
</body>
</html>
'''

open('/home/claude/hummusfit-warehouse/blueprint.html', 'w').write(html_doc)
print('HTML written', len(html_doc), 'bytes')
