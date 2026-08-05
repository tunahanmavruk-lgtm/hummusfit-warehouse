"""
Builds an interactive, to-scale 3D model of the walk-in (orbit/zoom in the
browser via Three.js). This is explicitly NOT a photorealistic walkthrough —
that needs real photogrammetry/360 capture this environment doesn't have.
What this is: accurate room geometry (walls, columns, drains, door, aisles,
lane footprints, crate stacks) built from the same blueprint_geometry.json
and lane_plan.json that drive the 2D blueprint and the live app, with every
product-labeled crate stack placed. Also used, via headless screenshot, to
render the static "room mockup" image embedded at the top of blueprint.html.
"""
import json, base64

g = json.load(open('/home/claude/hummusfit-warehouse/blueprint_geometry.json'))
lane_plan = json.load(open('/home/claude/hummusfit-warehouse/lane_plan.json'))

lane_by_code = {}
for sec in lane_plan.values():
    for l in sec['lanes']:
        lane_by_code[l['code']] = l

CAT_COLOR = {'muffin': '#2BBFAA', 'oats': '#4C9BE8', 'snack': '#E8612C', 'meal': '#3A3F46'}

row_x0, row_x1 = g['row_x0'], g['row_x1']
POS_BY_SECTION = g['positions_per_row_by_section']  # bakery rows: 35/row, meals rows: 27/row
CRATE_W, CRATE_D, CRATE_H = g['CRATE_W'], g['CRATE_D'], g['CRATE_H']

crates_js = []
for entry in g['layout']:
    if 'row' not in entry:
        continue
    r = entry['row']
    sec = g['row_section'][r]
    POS = POS_BY_SECTION[sec]
    pos_w = (row_x1 - row_x0) / POS
    y0, y1 = entry['y0'], entry['y1']
    for p in range(1, POS + 1):
        code = f'{r}-{p:02d}'
        lane = lane_by_code.get(code)
        cx = row_x0 + (p - 0.5) * pos_w
        cy = (y0 + y1) / 2
        if lane:
            color = CAT_COLOR.get(lane['category'], '#767c85')
            stack = min(7, lane['crates_needed'])
            product = lane['product'].replace("'", "\\'")
            crates_js.append(
                f"{{code:'{code}',row:'{r}',sec:'{sec}',x:{cx:.2f},y:{cy:.2f},"
                f"color:'{color}',stack:{stack},product:'{product}',"
                f"cat:'{lane['category']}',crates:{lane['crates_needed']},"
                f"source:'{lane['demand_source']}'}}"
            )
        else:
            crates_js.append(
                f"{{code:'{code}',row:'{r}',sec:'{sec}',x:{cx:.2f},y:{cy:.2f},"
                f"color:null,stack:0,product:null,cat:null,crates:0,source:null}}"
            )

rows_js = []
for entry in g['layout']:
    if 'row' in entry:
        rows_js.append(f"{{kind:'row',code:'{entry['row']}',sec:'{g['row_section'][entry['row']]}',y0:{entry['y0']:.2f},y1:{entry['y1']:.2f}}}")
    else:
        rows_js.append(f"{{kind:'aisle',name:'{entry['aisle']}',y0:{entry['y0']:.2f},y1:{entry['y1']:.2f}}}")

def data_uri(path):
    return 'data:image/jpeg;base64,' + base64.b64encode(open(path, 'rb').read()).decode('ascii')

THREE_JS = open('/tmp/package/build/three.min.js').read()
ORBIT_JS = open('/tmp/package/examples/js/controls/OrbitControls.js').read()

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hummus Fit — Walk-In 3D Model</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800;900&display=swap" rel="stylesheet">
<style>
  :root{{ --teal:#2BBFAA; --orange:#E8612C; --ink:#111417; --dim:#767c85; --line:#e9ebee; --bg:#fafafa; }}
  *{{box-sizing:border-box;}}
  html,body{{margin:0;height:100%;font-family:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);}}
  .topbar{{padding:18px 24px 10px;}}
  h1{{font-size:22px;margin:0 0 4px;font-weight:900;letter-spacing:-.01em;}}
  .sub{{color:var(--dim);font-size:13.5px;margin:0;font-weight:600;max-width:900px;line-height:1.5;}}
  .stage{{position:relative;height:calc(100vh - 118px);min-height:520px;margin:14px 24px 0;border-radius:16px;overflow:hidden;border:1.5px solid var(--line);background:#dfe3e6;}}
  #canvas-wrap{{position:absolute;inset:0;}}
  canvas{{display:block;width:100%;height:100%;}}
  .panel{{position:absolute;top:14px;right:14px;width:260px;background:rgba(255,255,255,.97);border:1.5px solid var(--line);border-radius:14px;padding:14px 16px;font-size:12.5px;box-shadow:0 6px 20px rgba(0,0,0,.08);}}
  .panel h3{{margin:0 0 6px;font-size:13px;font-weight:800;}}
  .panel .code{{font-weight:900;font-size:15px;}}
  .panel .prod{{font-weight:700;margin:4px 0;line-height:1.35;}}
  .panel .meta{{color:var(--dim);font-size:11.5px;}}
  .panel .hint{{color:var(--dim);font-size:11.5px;line-height:1.5;}}
  .legend{{position:absolute;bottom:14px;left:14px;background:rgba(255,255,255,.97);border:1.5px solid var(--line);border-radius:14px;padding:10px 14px;font-size:11.5px;display:flex;gap:14px;flex-wrap:wrap;max-width:calc(100% - 300px);}}
  .legend .item{{display:flex;align-items:center;gap:6px;font-weight:700;color:var(--dim);}}
  .dot{{width:11px;height:11px;border-radius:3px;flex:none;}}
  .camdot{{width:11px;height:11px;border-radius:50%;flex:none;background:#fff;border:2px solid var(--orange);}}
  .controls-hint{{position:absolute;top:14px;left:14px;background:rgba(255,255,255,.97);border:1.5px solid var(--line);border-radius:14px;padding:9px 13px;font-size:11.5px;color:var(--dim);font-weight:600;display:flex;align-items:center;gap:10px;}}
  .controls-hint label{{display:flex;align-items:center;gap:5px;cursor:pointer;user-select:none;}}
  #labelLayer{{position:absolute;inset:0;overflow:hidden;pointer-events:none;}}
  .crate-label{{position:absolute;transform:translate(-50%,-100%);font-size:9.5px;font-weight:700;line-height:1.2;background:rgba(255,255,255,.94);border:1px solid rgba(17,20,23,.12);border-radius:4px;padding:1.5px 5px;white-space:nowrap;color:var(--ink);pointer-events:none;box-shadow:0 1px 2px rgba(0,0,0,.06);}}
  .crate-label .cl-code{{color:var(--dim);font-weight:800;margin-right:4px;}}
  .pagenav{{display:flex;gap:8px;margin:0 24px 4px;}}
  .pagenav a{{text-decoration:none;font-size:13px;font-weight:800;color:var(--dim);border:1.5px solid var(--line);border-radius:10px;padding:9px 18px;}}
  .pagenav a.active{{background:var(--ink);color:#fff;border-color:var(--ink);}}
</style>
</head>
<body>
<div class="topbar">
  <div class="pagenav"><a href="/blueprint.html">Blueprint</a><a href="/3d-model.html" class="active">3D Model</a><a href="/backstock-blueprint.html">Backstock Blueprint</a><a href="/backstock-3d.html">Backstock 3D</a></div>
  <h1>Walk-In Storage — Interactive 3D Model</h1>
  <p class="sub">To the real room dimensions, built from the same geometry and product plan as the 2D blueprint. Orbit, pan, zoom. Click a crate stack for its product.</p>
</div>
<div class="stage">
  <div id="canvas-wrap"></div>
  <div class="controls-hint">
    <span>Drag to orbit · scroll to zoom · right-drag to pan</span>
    <label><input type="checkbox" id="labelToggle" checked> Show product labels</label>
  </div>
  <div id="labelLayer"></div>
  <div class="panel" id="panel">
    <h3>Tap a crate stack</h3>
    <p class="hint">Every colored block is a stocked lane, sized to its real crate count (capped at the 7-crate max stack). Gaps are empty floor positions. Click one to see what goes there.</p>
  </div>
  <div class="legend">
    <div class="item"><span class="dot" style="background:#2BBFAA"></span>Muffin</div>
    <div class="item"><span class="dot" style="background:#4C9BE8"></span>Oats</div>
    <div class="item"><span class="dot" style="background:#E8612C"></span>Snack</div>
    <div class="item"><span class="dot" style="background:#3A3F46"></span>Meal</div>
  </div>
</div>

<script>
{THREE_JS}
</script>
<script>
{ORBIT_JS}
</script>
<script>
const ROOM_W = {g['ROOM_W_IN']}, ROOM_D = {g['ROOM_D_IN']}, CEIL = {g['CEILING_IN']};
const ROW_X0 = {row_x0}, ROW_X1 = {row_x1};
const rows = [{','.join(rows_js)}];
const crates = [{','.join(crates_js)}];

const wrap = document.getElementById('canvas-wrap');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdfe3e6);

const camera = new THREE.PerspectiveCamera(50, wrap.clientWidth/wrap.clientHeight, 1, 5000);
camera.position.set(ROOM_W*0.55, 520, ROOM_D*1.35);
camera.lookAt(ROOM_W*0.4, 0, ROOM_D*0.4);

const renderer = new THREE.WebGLRenderer({{antialias:true}});
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(wrap.clientWidth, wrap.clientHeight);
wrap.appendChild(renderer.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.target.set(ROOM_W*0.4, 0, ROOM_D*0.4);
controls.maxPolarAngle = Math.PI*0.49;
controls.minDistance = 80;
controls.maxDistance = 1800;
controls.update();

scene.add(new THREE.AmbientLight(0xffffff, 0.75));
const sun = new THREE.DirectionalLight(0xffffff, 0.65);
sun.position.set(ROOM_W*0.3, 500, ROOM_D*0.2);
scene.add(sun);
const sun2 = new THREE.DirectionalLight(0xffffff, 0.35);
sun2.position.set(-ROOM_W*0.3, 400, ROOM_D*0.9);
scene.add(sun2);

// floor
const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(ROOM_W, ROOM_D),
  new THREE.MeshStandardMaterial({{color:0xb9bec3, roughness:0.9}})
);
floor.rotation.x = -Math.PI/2;
floor.position.set(ROOM_W/2, 0, ROOM_D/2);
scene.add(floor);

// walls (open top, matching real photos: white ribbed panel walls)
const wallMat = new THREE.MeshStandardMaterial({{color:0xf3f4f5, roughness:0.95, side:THREE.DoubleSide}});
function wall(w, h, x, z, ry) {{
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), wallMat);
  m.position.set(x, h/2, z);
  m.rotation.y = ry;
  scene.add(m);
}}
wall(ROOM_D, CEIL, 0, ROOM_D/2, Math.PI/2);          // left wall (door wall), x=0
wall(ROOM_D, CEIL, ROOM_W, ROOM_D/2, -Math.PI/2);    // right wall
wall(ROOM_W, CEIL, ROOM_W/2, 0, 0);                  // back wall
wall(ROOM_W, CEIL, ROOM_W/2, ROOM_D, Math.PI);       // front wall

// door (blue roll-up, estimated position — matches blueprint flag #1)
const doorY0 = ROOM_D*0.32, doorH = 120;
const door = new THREE.Mesh(
  new THREE.PlaneGeometry(doorH, 96),
  new THREE.MeshStandardMaterial({{color:0x2456c9, roughness:0.6}})
);
door.position.set(0.3, 48, doorY0 + doorH/2);
door.rotation.y = Math.PI/2;
scene.add(door);

// columns (estimated even spacing — matches blueprint flag #2)
const colMat = new THREE.MeshStandardMaterial({{color:0x3a3f46, roughness:0.7}});
for (let i=0;i<4;i++) {{
  const cx = ROOM_W*(0.30+i*0.16), cz = ROOM_D*0.5;
  const col = new THREE.Mesh(new THREE.CylinderGeometry(6,6,CEIL,16), colMat);
  col.position.set(cx, CEIL/2, cz);
  scene.add(col);
}}

// drains (approximate — matches blueprint flag #3)
const drainMat = new THREE.MeshStandardMaterial({{color:0x55595e, roughness:0.8}});
for (let i=0;i<3;i++) {{
  const dx = ROOM_W*(0.15+i*0.35), dz = ROOM_D*0.85;
  const d = new THREE.Mesh(new THREE.CylinderGeometry(4,4,0.6,20), drainMat);
  d.position.set(dx, 0.4, dz);
  scene.add(d);
}}

// row footprints + aisle floor tint
rows.forEach(r => {{
  if (r.kind === 'row') {{
    const color = r.sec === 'bakery' ? 0xeafaf7 : 0xeef0f4;
    const w = ROW_X1-ROW_X0, d = r.y1-r.y0;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({{color, roughness:0.9}}));
    m.rotation.x = -Math.PI/2;
    m.position.set(ROW_X0+w/2, 0.15, r.y0+d/2);
    scene.add(m);
  }}
}});

// crate stacks — every stocked lane gets a floating product-name tag,
// not just a click target. Previously the only way to learn what a crate
// stack was, in this model, was to click it and read the side panel; the
// birds-eye blueprint had the same gap (a lane code + dot, full name only
// in a legend table below). Both now label the product directly.
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const pickables = [];
const labelLayer = document.getElementById('labelLayer');
const labelToggle = document.getElementById('labelToggle');

function shortName(name) {{
  if (!name) return '';
  const s = name.replace(/^(Buffin Muffin|Overnight Oats|Buff Crisp Bar)\s*-\s*/, '');
  return s.length > 24 ? s.slice(0, 22) + '…' : s;
}}

const crateLabels = [];
crates.forEach(c => {{
  if (!c.color) return;
  const h = c.stack * 10.70;
  const geo = new THREE.BoxGeometry(19, h, 14);
  const mat = new THREE.MeshStandardMaterial({{color:c.color, roughness:0.55}});
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(c.x, h/2, c.y);
  mesh.userData = c;
  scene.add(mesh);
  pickables.push(mesh);

  // Code-only tag -- with ~189 lanes, a full product name on every always-on
  // label overlapped into an unreadable smear even zoomed in. Full product
  // detail is one click away in the side panel; the floating tag is just
  // for "which lane is this" orientation, so it needs to stay short.
  const div = document.createElement('div');
  div.className = 'crate-label';
  div.textContent = c.code;
  labelLayer.appendChild(div);
  crateLabels.push({{div, x: c.x, y: h + 16, z: c.y}});
}});

const labelVec = new THREE.Vector3();
function updateLabels() {{
  const show = labelToggle.checked;
  labelLayer.style.display = show ? 'block' : 'none';
  if (!show) return;
  const rect = renderer.domElement.getBoundingClientRect();
  const camDist = camera.position.distanceTo(controls.target);
  // Fade labels out once zoomed far enough out that 160+ tags would just
  // overlap into an unreadable smear — the click panel still works at any
  // zoom level, this is purely about keeping the wide view legible.
  const declutter = camDist > 900;
  for (const lb of crateLabels) {{
    labelVec.set(lb.x, lb.y, lb.z);
    labelVec.project(camera);
    if (labelVec.z > 1 || declutter) {{ lb.div.style.display = 'none'; continue; }}
    const sx = (labelVec.x * 0.5 + 0.5) * rect.width;
    const sy = (-labelVec.y * 0.5 + 0.5) * rect.height;
    if (sx < -40 || sx > rect.width + 40 || sy < -20 || sy > rect.height + 20) {{
      lb.div.style.display = 'none';
      continue;
    }}
    lb.div.style.display = 'block';
    lb.div.style.left = sx + 'px';
    lb.div.style.top = sy + 'px';
  }}
}}

// pathway line (aisles only — matches the fixed 2D routing)
const spineX = 30;
const aisleAY = (rows.find(r=>r.kind==='aisle').y0 + rows.find(r=>r.kind==='aisle').y1)/2;
const aisleRows = rows.filter(r=>r.kind==='aisle');
const aY = (aisleRows[0].y0+aisleRows[0].y1)/2, bY=(aisleRows[1].y0+aisleRows[1].y1)/2, cY=(aisleRows[2].y0+aisleRows[2].y1)/2;
const rowEndX = ROW_X1 - 10;
const pts = [
  [0, doorY0+60], [spineX, doorY0+60], [spineX, aY],
  [spineX, aY], [rowEndX, aY],
  [rowEndX, aY], [rowEndX, bY],
  [rowEndX, bY], [spineX, bY],
  [spineX, bY], [spineX, cY],
  [spineX, cY], [rowEndX, cY],
  [rowEndX, cY], [rowEndX, cY+30], [spineX, cY+30], [spineX, doorY0+60], [0, doorY0+60],
].map(p => new THREE.Vector3(p[0], 6, p[1]));
const pathGeo = new THREE.BufferGeometry().setFromPoints(pts);
const pathLine = new THREE.Line(pathGeo, new THREE.LineDashedMaterial({{color:0x2BBFAA, dashSize:8, gapSize:5, linewidth:2}}));
pathLine.computeLineDistances();
scene.add(pathLine);

function onPick(clientX, clientY) {{
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((clientX-rect.left)/rect.width)*2-1;
  mouse.y = -((clientY-rect.top)/rect.height)*2+1;
  raycaster.setFromCamera(mouse, camera);
  let hit = raycaster.intersectObjects(pickables)[0];
  const panel = document.getElementById('panel');
  if (hit) {{
    const c = hit.object.userData;
    const srcNote = c.source === 'real' ? 'real order data' : 'corrected blended estimate (no real order match)';
    panel.innerHTML = `<div class="code">${{c.code}}</div>
      <div class="prod">${{c.product}}</div>
      <div class="meta">${{c.crates}} crate${{c.crates!==1?'s':''}} · ${{c.cat}}</div>
      <div class="meta" style="margin-top:6px;">${{srcNote}}</div>`;
  }}
}}
renderer.domElement.addEventListener('click', (e) => onPick(e.clientX, e.clientY));

window.addEventListener('resize', () => {{
  camera.aspect = wrap.clientWidth/wrap.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
}});

function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
  updateLabels();
}}
animate();
</script>
</body>
</html>
'''

open('/home/claude/hummusfit-warehouse/3d_model.html', 'w').write(html)
print('3D model written', len(html), 'bytes')
