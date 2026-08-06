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
POINTERLOCK_JS = open('/tmp/package/examples/js/controls/PointerLockControls.js').read()

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
  #walkBtn{{margin-top:0;background:var(--teal);color:#fff;border:none;border-radius:8px;padding:7px 12px;font-size:12px;font-weight:800;cursor:pointer;}}
  #crosshair{{position:absolute;top:50%;left:50%;width:6px;height:6px;margin:-3px 0 0 -3px;border-radius:50%;background:rgba(255,255,255,.85);border:1px solid rgba(0,0,0,.4);display:none;pointer-events:none;}}
  #walkTouchHint{{position:absolute;bottom:16px;left:50%;transform:translateX(-50%);background:rgba(17,20,23,0.75);color:#fff;font-size:11.5px;font-weight:700;padding:6px 12px;border-radius:8px;display:none;pointer-events:none;text-align:center;}}
  #joyBase{{position:absolute;width:110px;height:110px;border-radius:50%;background:rgba(255,255,255,.14);border:2px solid rgba(255,255,255,.4);display:none;touch-action:none;}}
  #joyKnob{{position:absolute;width:46px;height:46px;border-radius:50%;background:rgba(255,255,255,.55);border:2px solid rgba(255,255,255,.75);left:32px;top:32px;pointer-events:none;}}
  #walkExitBtn{{position:absolute;top:14px;left:50%;transform:translateX(-50%);background:rgba(232,97,44,0.92);color:#fff;border:none;border-radius:10px;padding:10px 20px;font-size:13px;font-weight:800;display:none;z-index:20;}}
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
    <button id="walkBtn">Walk mode (WASD + mouse)</button>
  </div>
  <div id="labelLayer"></div>
  <div id="crosshair"></div>
  <button id="walkExitBtn">Exit walk mode</button>
  <div id="walkTouchHint">Left thumb: move &nbsp;•&nbsp; right side: drag to look &nbsp;•&nbsp; tap a crate to select</div>
  <div id="joyBase"><div id="joyKnob"></div></div>
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
{POINTERLOCK_JS}
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

// ---- Real-crate look (Aug 2026, matching backstock's 3D page -- same
// IRIS 45QT clear storage bin w/ buckles Tony linked, 21.65"L x 15.70"W x
// 10.70"H, semi-clear plastic + black snap-lock buckles + grooved lid).
// This room already stacked crates at the real 10.70in unit height (see
// `h = c.stack * 10.70` below, unchanged) -- it was just drawing that stack
// as one flat solid-color slab. Now each 10.70in level gets its own
// crate-look unit instead, so a 4-crate stack reads as 4 visibly separate
// totes, the way it actually sits in the room.
const CRATE_CLEAR = new THREE.MeshPhysicalMaterial({{
  color: 0xffffff, transparent: true, opacity: 0.32, roughness: 0.15,
  metalness: 0, side: THREE.DoubleSide, depthWrite: false,
}});
const CRATE_LID = new THREE.MeshPhysicalMaterial({{
  color: 0xf3f5f6, transparent: true, opacity: 0.5, roughness: 0.25, metalness: 0,
}});
const BUCKLE_MAT = new THREE.MeshStandardMaterial({{color: 0x1c1e22, roughness: 0.6}});
const crateCoreMatCache = {{}};
function crateCoreMat(color) {{
  if (!crateCoreMatCache[color]) {{
    crateCoreMatCache[color] = new THREE.MeshStandardMaterial({{color, roughness: 0.85}});
  }}
  return crateCoreMatCache[color];
}}
function buildCrateUnit(w, h, d, color) {{
  const group = new THREE.Group();
  const shell = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), CRATE_CLEAR);
  group.add(shell);
  const core = new THREE.Mesh(new THREE.BoxGeometry(w*0.72, h*0.6, d*0.72), crateCoreMat(color));
  core.position.y = -h*0.05;
  group.add(core);
  const lidH = Math.max(1.2, h*0.14);
  const lid = new THREE.Mesh(new THREE.BoxGeometry(w*1.04, lidH, d*1.04), CRATE_LID);
  lid.position.y = h/2 - lidH/2 + 0.3;
  group.add(lid);
  const buckleW = Math.max(1.5, w*0.09);
  const buckleH = Math.max(1.5, h*0.5);
  [-1, 1].forEach(side => {{
    const buckle = new THREE.Mesh(new THREE.BoxGeometry(buckleW, buckleH, d*1.02), BUCKLE_MAT);
    buckle.position.set(side * w*0.32, -h*0.03, 0);
    group.add(buckle);
  }});
  return group;
}}

const crateLabels = [];
crates.forEach(c => {{
  if (!c.color) return;
  const unitH = 10.70;
  const h = c.stack * unitH;
  for (let i = 0; i < c.stack; i++) {{
    const unit = buildCrateUnit(19, unitH * 0.92, 14, c.color);
    unit.position.set(c.x, unitH*i + unitH/2, c.y);
    unit.userData = c;
    scene.add(unit);
    unit.children[0].userData = c;
    pickables.push(unit.children[0]);
  }}

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

function panelFromHit(hit) {{
  const panel = document.getElementById('panel');
  if (!hit) return;
  const c = hit.object.userData;
  const srcNote = c.source === 'real' ? 'real order data' : 'corrected blended estimate (no real order match)';
  panel.innerHTML = `<div class="code">${{c.code}}</div>
    <div class="prod">${{c.product}}</div>
    <div class="meta">${{c.crates}} crate${{c.crates!==1?'s':''}} · ${{c.cat}}</div>
    <div class="meta" style="margin-top:6px;">${{srcNote}}</div>`;
}}
function onPick(clientX, clientY) {{
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((clientX-rect.left)/rect.width)*2-1;
  mouse.y = -((clientY-rect.top)/rect.height)*2+1;
  raycaster.setFromCamera(mouse, camera);
  panelFromHit(raycaster.intersectObjects(pickables)[0]);
}}

// ---- Walk mode: same system as backstock's 3D page (Aug 2026) -- desktop
// gets WASD + Pointer Lock mouse-look, touch (iPad/iPhone, the picking
// team's primary devices) gets a virtual joystick + drag-to-look instead,
// since Pointer Lock is unimplemented on iOS/iPadOS Safari entirely. See
// backstock/build_backstock_3d.py for the full history of why this exact
// shape (shared enter/exit, touch joystick math, entry-position fix) is
// what it is -- ported here as-is rather than re-derived, since this room's
// walls have the exact same "solid box, no real door gap" issue that
// caused walk mode to visually blank out in backstock until the entry
// point was moved inside the walls instead of outside them.
const walkBtn = document.getElementById('walkBtn');
const walkExitBtn = document.getElementById('walkExitBtn');
const walkTouchHint = document.getElementById('walkTouchHint');
const joyBase = document.getElementById('joyBase');
const joyKnob = document.getElementById('joyKnob');
const crosshair = document.getElementById('crosshair');
const plControls = new THREE.PointerLockControls(camera, renderer.domElement);
const IS_TOUCH = ('ontouchstart' in window) || navigator.maxTouchPoints > 0;
let walking = false;
const walkKeys = {{}};
const EYE_HEIGHT = 66;
document.addEventListener('keydown', e => walkKeys[e.code] = true);
document.addEventListener('keyup', e => walkKeys[e.code] = false);
if (IS_TOUCH) {{ walkBtn.textContent = 'Walk mode (touch)'; }}

// Entry point: just inside the door wall (x=0), facing +X into the room --
// NOT at x=0 itself, which sits ON the solid door-wall panel (this room's
// four walls are full solid planes with no actual cut-out where the door
// graphic is drawn, same as backstock). doorY0/doorH already define the
// door's real position on that wall.
function enterWalk() {{
  walking = true;
  controls.enabled = false;
  camera.position.set(40, EYE_HEIGHT, doorY0 + doorH/2);
  camera.quaternion.setFromEuler(new THREE.Euler(0, -Math.PI/2, 0, 'YXZ')); // faces +X, into the room
  crosshair.style.display = 'block';
  document.getElementById('panel').style.display = 'none';
  if (IS_TOUCH) {{
    walkBtn.style.display = 'none';
    walkExitBtn.style.display = 'block';
    walkTouchHint.style.display = 'block';
    setTimeout(() => {{ walkTouchHint.style.display = 'none'; }}, 4000);
  }} else {{
    walkBtn.textContent = 'Exit walk mode (Esc)';
    walkBtn.disabled = false;
  }}
}}
function exitWalk() {{
  walking = false;
  controls.enabled = true;
  const lookDir = new THREE.Vector3();
  camera.getWorldDirection(lookDir);
  controls.target.copy(camera.position).addScaledVector(lookDir, 200);
  controls.update();
  crosshair.style.display = 'none';
  joyBase.style.display = 'none';
  walkTouchHint.style.display = 'none';
  document.getElementById('panel').style.display = 'block';
  if (IS_TOUCH) {{
    walkBtn.style.display = 'block';
    walkExitBtn.style.display = 'none';
  }} else {{
    walkBtn.textContent = 'Walk mode (WASD + mouse)';
  }}
}}
walkBtn.addEventListener('click', () => {{
  if (walking) return;
  if (IS_TOUCH) {{ enterWalk(); }} else {{ plControls.lock(); }}
}});
walkExitBtn.addEventListener('click', () => {{ if (walking) exitWalk(); }});
plControls.addEventListener('lock', enterWalk);
plControls.addEventListener('unlock', exitWalk);
document.addEventListener('pointerlockerror', () => {{
  walkBtn.textContent = 'Walk mode unavailable in this browser';
  walkBtn.disabled = true;
  setTimeout(() => {{ walkBtn.textContent = 'Walk mode (WASD + mouse)'; walkBtn.disabled = false; }}, 3000);
}});
renderer.domElement.addEventListener('click', (e) => {{
  if (walking && !IS_TOUCH) {{
    raycaster.setFromCamera(new THREE.Vector2(0,0), camera);
    panelFromHit(raycaster.intersectObjects(pickables)[0]);
  }} else if (!walking) {{
    onPick(e.clientX, e.clientY);
  }}
}});
const WALK_SPEED = 160;
const walkVelocity = new THREE.Vector3();
const touchMove = {{x: 0, y: 0}};
function updateWalk(dt) {{
  if (!walking) return;
  walkVelocity.set(0,0,0);
  if (IS_TOUCH) {{
    walkVelocity.x = touchMove.x;
    walkVelocity.z = touchMove.y;
  }} else {{
    if (walkKeys['KeyW']) walkVelocity.z -= 1;
    if (walkKeys['KeyS']) walkVelocity.z += 1;
    if (walkKeys['KeyA']) walkVelocity.x -= 1;
    if (walkKeys['KeyD']) walkVelocity.x += 1;
  }}
  if (walkVelocity.lengthSq() > 0) {{
    const mag = Math.min(1, walkVelocity.length());
    walkVelocity.normalize().multiplyScalar(mag * WALK_SPEED*dt);
    plControls.moveRight(walkVelocity.x);
    plControls.moveForward(-walkVelocity.z);
  }}
  camera.position.y = EYE_HEIGHT;
  camera.position.x = Math.max(6, Math.min(ROOM_W-6, camera.position.x));
  camera.position.z = Math.max(6, Math.min(ROOM_D-6, camera.position.z));
}}

if (IS_TOUCH) {{
  const JOY_R = 55;
  let joyTouchId = null, joyOriginX = 0, joyOriginY = 0;
  const LOOK_SENS = 0.0035;
  const TAP_MOVE_THRESHOLD = 12;
  const lookTouches = {{}};
  function placeJoyBase(x, y) {{
    joyOriginX = x; joyOriginY = y;
    joyBase.style.left = (x - JOY_R) + 'px';
    joyBase.style.top = (y - JOY_R) + 'px';
    joyBase.style.display = 'block';
    joyKnob.style.left = '32px'; joyKnob.style.top = '32px';
  }}
  function updateJoyKnob(x, y) {{
    let dx = x - joyOriginX, dy = y - joyOriginY;
    const dist = Math.hypot(dx, dy);
    if (dist > JOY_R) {{ dx = dx/dist*JOY_R; dy = dy/dist*JOY_R; }}
    joyKnob.style.left = (32 + dx) + 'px';
    joyKnob.style.top = (32 + dy) + 'px';
    touchMove.x = dx / JOY_R;
    touchMove.y = dy / JOY_R;
  }}
  function resetJoy() {{
    joyTouchId = null;
    joyBase.style.display = 'none';
    touchMove.x = 0; touchMove.y = 0;
  }}
  renderer.domElement.addEventListener('touchstart', e => {{
    if (!walking) return;
    e.preventDefault();
    for (const t of e.changedTouches) {{
      const leftHalf = t.clientX < wrap.clientWidth * 0.5;
      if (leftHalf && joyTouchId === null) {{
        joyTouchId = t.identifier;
        placeJoyBase(t.clientX, t.clientY);
      }} else if (!leftHalf) {{
        lookTouches[t.identifier] = {{x: t.clientX, y: t.clientY, startX: t.clientX, startY: t.clientY, moved: false}};
      }}
    }}
  }}, {{passive: false}});
  renderer.domElement.addEventListener('touchmove', e => {{
    if (!walking) return;
    e.preventDefault();
    for (const t of e.changedTouches) {{
      if (t.identifier === joyTouchId) {{
        updateJoyKnob(t.clientX, t.clientY);
      }} else if (lookTouches[t.identifier]) {{
        const lt = lookTouches[t.identifier];
        const dx = t.clientX - lt.x, dy = t.clientY - lt.y;
        lt.x = t.clientX; lt.y = t.clientY;
        if (Math.hypot(t.clientX - lt.startX, t.clientY - lt.startY) > TAP_MOVE_THRESHOLD) lt.moved = true;
        const _euler = new THREE.Euler(0, 0, 0, 'YXZ');
        _euler.setFromQuaternion(camera.quaternion);
        _euler.y -= dx * LOOK_SENS;
        _euler.x -= dy * LOOK_SENS;
        _euler.x = Math.max(-Math.PI/2, Math.min(Math.PI/2, _euler.x));
        camera.quaternion.setFromEuler(_euler);
      }}
    }}
  }}, {{passive: false}});
  renderer.domElement.addEventListener('touchend', e => {{
    if (!walking) return;
    for (const t of e.changedTouches) {{
      if (t.identifier === joyTouchId) {{
        resetJoy();
      }} else if (lookTouches[t.identifier]) {{
        const lt = lookTouches[t.identifier];
        if (!lt.moved) {{
          const ndcX = (t.clientX / wrap.clientWidth) * 2 - 1;
          const ndcY = -(t.clientY / wrap.clientHeight) * 2 + 1;
          raycaster.setFromCamera(new THREE.Vector2(ndcX, ndcY), camera);
          panelFromHit(raycaster.intersectObjects(pickables)[0]);
        }}
        delete lookTouches[t.identifier];
      }}
    }}
  }}, {{passive: false}});
  renderer.domElement.addEventListener('touchcancel', e => {{
    for (const t of e.changedTouches) {{
      if (t.identifier === joyTouchId) resetJoy();
      delete lookTouches[t.identifier];
    }}
  }}, {{passive: false}});
}}

window.addEventListener('resize', () => {{
  camera.aspect = wrap.clientWidth/wrap.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
}});

let lastT = 0;
function animate(t) {{
  requestAnimationFrame(animate);
  const dt = Math.min(0.05, (t - lastT) / 1000 || 0);
  lastT = t;
  if (walking) {{ updateWalk(dt); }} else {{ controls.update(); }}
  renderer.render(scene, camera);
  updateLabels();
}}
requestAnimationFrame(animate);
</script>
</body>
</html>
'''

open('/home/claude/hummusfit-warehouse/3d_model.html', 'w').write(html)
print('3D model written', len(html), 'bytes')
