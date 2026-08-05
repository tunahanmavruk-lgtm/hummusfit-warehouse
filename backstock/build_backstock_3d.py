"""
3D mockup of the backstock room -- built from the confirmed geometry in
backstock_geometry.json, with the ACTUAL product-location assignment from
backstock_location_assignment.csv / position_fill.json rendered as colored
crate-load blocks per position (real 3.5-day crate counts, real Shopify u30
demand -- see build_backstock_location_assignment.py for the math). Color =
category. Block height = how full that position is relative to its capacity.
"""
import json

g = json.load(open('/home/claude/hummusfit-warehouse/backstock/backstock_geometry.json'))
pos_fill = json.load(open('/home/claude/hummusfit-warehouse/backstock/position_fill.json'))
THREE_JS = open('/tmp/package/build/three.min.js').read()
ORBIT_JS = open('/tmp/package/examples/js/controls/OrbitControls.js').read()
POINTERLOCK_JS = open('/tmp/package/examples/js/controls/PointerLockControls.js').read()

ZONE_W = g['zone_width_in']          # 384in (32ft) -- Wall A's confirmed span
ZONE_L = g['zone_length_in']
WA_BAYS, WA_LEVELS, WA_DEPTH = 4, 3, 42
WD_BAYS_OURS, WD_LEVELS, WD_DEPTH = 2, 4, 42
WD_BAY_W = g['wall_d_bay_width_in']  # 96in, confirmed same as Wall A
WD_BAY_LEN = WD_BAY_W
C_BAYS = g['center_bays']            # 7, corrected from 6 (C07 added)
C_TOTAL_RUN = g['center_total_run_in']  # 378in (31.5ft) -- shorter than Wall A
CENTER_DEPTH = 40
AISLE = 132
LEVEL_H = 60  # placeholder, unconfirmed per-level height
GAP_TO_WD = 40
X_OFFSET = GAP_TO_WD + WD_DEPTH

wa_bay_w = ZONE_W / WA_BAYS          # 96in/bay, confirmed 8ft
c_bay_w = C_TOTAL_RUN / C_BAYS       # Center's own 31.5ft run / 7 bays

room_w = ZONE_W + X_OFFSET
room_d = ZONE_L + 60

config = {
    'roomW': room_w, 'roomD': room_d,
    'wallA': {'bays': WA_BAYS, 'levels': WA_LEVELS, 'depth': WA_DEPTH, 'bayW': wa_bay_w, 'x0': X_OFFSET, 'y0': 0},
    'wallD': {'bays': WD_BAYS_OURS, 'levels': WD_LEVELS, 'depth': WD_DEPTH, 'bayLen': WD_BAY_LEN, 'x0': 0, 'y0': 0},
    'center': {'bays': C_BAYS, 'depth': CENTER_DEPTH, 'bayW': c_bay_w, 'totalRun': C_TOTAL_RUN, 'zoneW': ZONE_W, 'x0': X_OFFSET, 'y0': WA_DEPTH + AISLE},
    'levelH': LEVEL_H,
}

CAT_COLOR = {'meal': 0x3b82f6, 'muffin': 0xE8612C, 'oats': 0x22c55e, 'snack': 0x8b5cf6}
CAT_LABEL = {'meal': 'Meals (blue)', 'muffin': 'Muffins (orange)', 'oats': 'Oats (green)', 'snack': 'Snacks (purple)'}

# Turn position_fill.json (bay/level/zone/cat/filled/cap keyed by e.g. "C03-L2")
# into per-position 3D placements matching the rack geometry above.
loads = []
for code, v in pos_fill.items():
    if not v['filled']:
        continue
    bay, level, zone, cat = v['bay'], v['level'], v['zone'], v['cat']
    frac = min(1.0, v['filled'] / v['cap'])
    if zone == 'walla':
        x = X_OFFSET + (bay-1)*wa_bay_w
        z = 0
        w, d = wa_bay_w - 4, WA_DEPTH - 4
    elif zone == 'walld':
        x = 0
        z = (bay-1)*WD_BAY_LEN
        w, d = WD_DEPTH - 4, WD_BAY_LEN - 6
    else:  # center
        x = X_OFFSET + (bay-1)*c_bay_w
        z = WA_DEPTH + AISLE
        w, d = c_bay_w - 4, CENTER_DEPTH - 4
    y0 = (level-1) * LEVEL_H + 4
    h = max(6, (LEVEL_H - 10) * frac)
    # Structured per-product rows (lane code, name, crates) for the click panel --
    # full detail lives here now, not crammed into an always-visible floating label.
    rows = [{'lane': pr['lane'], 'name': pr['name'], 'crates': pr['crates']} for pr in v['products']]
    loads.append({
        'x': x, 'z': z, 'w': w, 'd': d, 'y0': y0, 'h': h,
        'color': CAT_COLOR.get(cat, 0x9aa0a8), 'code': code, 'cat': cat,
        'filled': v['filled'], 'cap': v['cap'], 'rows': rows,
    })

html_doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Hummus Fit — Backstock Room 3D (DRAFT)</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  html,body{{margin:0;height:100%;overflow:hidden;font-family:'Inter',-apple-system,sans-serif;background:#dfe3e6;}}
  #wrap{{position:relative;width:100%;height:100%;}}
  #hud{{position:absolute;top:16px;left:16px;background:rgba(17,20,23,0.85);color:#fff;padding:14px 18px;border-radius:12px;font-size:12.5px;line-height:1.6;max-width:340px;}}
  #hud b{{color:#2BBFAA;}}
  #hud .warn{{color:#ffb066;}}
  #toggle{{position:absolute;top:16px;right:16px;background:rgba(17,20,23,0.85);color:#fff;padding:8px 14px;border-radius:10px;font-size:12px;cursor:pointer;user-select:none;}}
  #pagenav{{position:absolute;top:16px;left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:10;}}
  #pagenav a{{text-decoration:none;font-size:12.5px;font-weight:800;color:#fff;background:rgba(17,20,23,0.85);border-radius:10px;padding:8px 14px;}}
  #pagenav a.active{{background:#2BBFAA;}}
  #labelLayer{{position:absolute;inset:0;overflow:hidden;pointer-events:none;}}
  .pos-label{{position:absolute;transform:translate(-50%,-100%);font-size:9.5px;font-weight:800;line-height:1;background:rgba(255,255,255,.92);border:1px solid rgba(17,20,23,.15);border-radius:4px;padding:2px 5px;color:#111417;pointer-events:none;box-shadow:0 1px 2px rgba(0,0,0,.08);white-space:nowrap;}}
  #panel{{position:absolute;top:150px;right:16px;width:280px;background:rgba(255,255,255,.97);border:1.5px solid #e9ebee;border-radius:14px;padding:14px 16px;font-size:12.5px;box-shadow:0 6px 20px rgba(0,0,0,.12);display:none;max-height:calc(100% - 170px);overflow-y:auto;}}
  #panel .code{{font-weight:900;font-size:16px;color:#111417;}}
  #panel .row{{margin:8px 0 2px;font-weight:700;line-height:1.4;padding-bottom:6px;border-bottom:1px solid #f0f1f3;}}
  #panel .meta{{color:#767c85;font-size:11.5px;margin-top:8px;}}
  #panel .hint{{color:#767c85;font-size:11.5px;line-height:1.5;}}
  #crosshair{{position:absolute;top:50%;left:50%;width:6px;height:6px;margin:-3px 0 0 -3px;border-radius:50%;background:rgba(255,255,255,.85);border:1px solid rgba(0,0,0,.4);display:none;pointer-events:none;}}
</style>
</head>
<body>
<div id="wrap">
  <div id="pagenav"><a href="/blueprint.html">Blueprint</a><a href="/3d-model.html">3D Model</a><a href="/backstock-blueprint.html">Backstock Blueprint</a><a href="/backstock-3d.html" class="active">Backstock 3D</a></div>
  <div id="hud">
    <b>Backstock Room — tiered reserve plan (Center = pallets, one SKU each)</b><br>
    Colored blocks = actual crate load per position, from backstock_location_assignment.csv.<br>
    <span style="color:#60a5fa">■</span> Meals &nbsp; <span style="color:#E8612C">■</span> Muffins &nbsp; <span style="color:#4ade80">■</span> Oats &nbsp; <span style="color:#a78bfa">■</span> Snacks<br>
    Block height = how full that position is (short = lightly filled, tall = at capacity).<br>
    <span class="warn">Room only holds 720 crates total, so not every SKU gets a backstock reserve. Tier A: top 28 movers, one dedicated pallet each on Center, full 3.5-day reserve. Tier B: next 21 movers, shared shelving on Wall A/D, 1-day reserve. Tier C: remaining 69 slower-moving products — walk-in pick face only, no backstock buffer, restocked directly. Beam spacing/level heights still placeholders.</span>
  </div>
  <div id="toggle">
    Click any block for full details · drag to rotate · scroll to zoom<br>
    <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-weight:600;margin-top:4px;"><input type="checkbox" id="labelToggle" checked> Show position code tags</label>
    <button id="walkBtn" style="margin-top:8px;width:100%;background:#2BBFAA;color:#fff;border:none;border-radius:8px;padding:7px 10px;font-size:12px;font-weight:800;cursor:pointer;">Walk mode (WASD + mouse)</button>
  </div>
  <div id="labelLayer"></div>
  <div id="panel">
    <div class="code" id="panelCode"></div>
    <div id="panelRows"></div>
    <div class="meta" id="panelMeta"></div>
  </div>
  <div id="crosshair"></div>
</div>
<script>{THREE_JS}</script>
<script>{ORBIT_JS}</script>
<script>{POINTERLOCK_JS}</script>
<script>
const CFG = {json.dumps(config)};
const LOADS = {json.dumps(loads)};
const wrap = document.getElementById('wrap');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdfe3e6);

const camera = new THREE.PerspectiveCamera(50, wrap.clientWidth/wrap.clientHeight, 1, 5000);
camera.position.set(CFG.roomW*1.4, 900, CFG.roomD*1.6);
camera.lookAt(CFG.roomW*0.5, 60, CFG.roomD*0.5);

const renderer = new THREE.WebGLRenderer({{antialias:true}});
renderer.setSize(wrap.clientWidth, wrap.clientHeight);
renderer.setPixelRatio(window.devicePixelRatio || 1);
wrap.appendChild(renderer.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.target.set(CFG.roomW*0.5, 60, CFG.roomD*0.5);
controls.enableDamping = true;

scene.add(new THREE.AmbientLight(0xffffff, 0.8));
const sun = new THREE.DirectionalLight(0xffffff, 0.6);
sun.position.set(400, 600, 300);
scene.add(sun);

// floor
const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(CFG.roomW, CFG.roomD),
  new THREE.MeshStandardMaterial({{color: 0x9aa0a8}})
);
floor.rotation.x = -Math.PI/2;
floor.position.set(CFG.roomW/2, 0, CFG.roomD/2);
scene.add(floor);

// room outline walls (low, just for orientation)
function wallSeg(x0, z0, x1, z1, h=180) {{
  const len = Math.hypot(x1-x0, z1-z0);
  const geo = new THREE.BoxGeometry(len, h, 4);
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({{color:0xf2f3f5}}));
  mesh.position.set((x0+x1)/2, h/2, (z0+z1)/2);
  mesh.rotation.y = -Math.atan2(z1-z0, x1-x0);
  scene.add(mesh);
}}
wallSeg(0,0, CFG.roomW,0);
wallSeg(0,0, 0,CFG.roomD);
wallSeg(CFG.roomW,0, CFG.roomW,CFG.roomD);

const GREEN = 0x5b6470, ORANGE = 0xE8612C, DARKINK = 0x111417, GRAYKIT = 0x9aa0a8;

function rackBay(x, z, w, d, levels, levelH, color) {{
  const group = new THREE.Group();
  // uprights
  const postGeo = new THREE.BoxGeometry(3, levels*levelH, 3);
  const postMat = new THREE.MeshStandardMaterial({{color}});
  [[0,0],[w,0],[0,d],[w,d]].forEach(([px,pz]) => {{
    const post = new THREE.Mesh(postGeo, postMat);
    post.position.set(x+px, levels*levelH/2, z+pz);
    group.add(post);
  }});
  // beam levels (wire deck shelves)
  const shelfMat = new THREE.MeshStandardMaterial({{color: 0xeeeeee, transparent:true, opacity:0.55}});
  const beamMat = new THREE.MeshStandardMaterial({{color: ORANGE}});
  for (let l=1; l<=levels; l++) {{
    const y = l*levelH;
    const shelf = new THREE.Mesh(new THREE.BoxGeometry(w, 2, d), shelfMat);
    shelf.position.set(x+w/2, y, z+d/2);
    group.add(shelf);
    const beam = new THREE.Mesh(new THREE.BoxGeometry(w, 4, 3), beamMat);
    beam.position.set(x+w/2, y, z);
    group.add(beam);
  }}
  return group;
}}

// Wall A -- 4 bays, 3 levels, green, door end
for (let b=0; b<CFG.wallA.bays; b++) {{
  scene.add(rackBay(CFG.wallA.x0 + b*CFG.wallA.bayW, CFG.wallA.y0, CFG.wallA.bayW-2, CFG.wallA.depth, CFG.wallA.levels, CFG.levelH, GREEN));
}}

// Wall D -- 2 bays, 4 levels, green, left side (only 2 of 3 bays ours; 3rd shown gray)
for (let b=0; b<3; b++) {{
  const color = b < CFG.wallD.bays ? GREEN : GRAYKIT;
  scene.add(rackBay(CFG.wallD.x0, CFG.wallD.y0 + b*CFG.wallD.bayLen, CFG.wallD.depth, CFG.wallD.bayLen-2, CFG.wallD.levels, CFG.levelH, color));
}}

// Center -- 7 bays (C01-C07), double-deep. Front face (ours, dark) + back face (kitchen's, gray)
// Center's total run (31.5ft) is shorter than Wall A's 32ft -- the leftover
// strip past Center's last bay is shown as a flat gray "no rack here" pad,
// matching the blueprint's hatched gap.
for (let b=0; b<CFG.center.bays; b++) {{
  scene.add(rackBay(CFG.center.x0 + b*CFG.center.bayW, CFG.center.y0, CFG.center.bayW-2, CFG.center.depth, 4, CFG.levelH, DARKINK));
  scene.add(rackBay(CFG.center.x0 + b*CFG.center.bayW, CFG.center.y0 + CFG.center.depth, CFG.center.bayW-2, CFG.center.depth, 4, CFG.levelH, GRAYKIT));
}}
if (CFG.center.totalRun < CFG.center.zoneW) {{
  const gapW = CFG.center.zoneW - CFG.center.totalRun;
  const gapPad = new THREE.Mesh(
    new THREE.BoxGeometry(gapW - 2, 2, CFG.center.depth*2 - 2),
    new THREE.MeshStandardMaterial({{color: 0xc7cbd1, transparent:true, opacity:0.5}})
  );
  gapPad.position.set(CFG.center.x0 + CFG.center.totalRun + gapW/2, 1, CFG.center.y0 + CFG.center.depth);
  scene.add(gapPad);
}}

// Real crate loads per position, from the actual product-location assignment
// (backstock_location_assignment.csv) -- one solid block per filled position,
// colored by category, height scaled to how full that position is.
//
// Fix for "so confusing when zoomed in": the old version put a full
// multi-product text label permanently floating over EVERY one of the 48
// positions -- at any zoom close enough to read one, a dozen others were
// overlapping it. Same problem the main walk-in 3D model already solved:
// small always-on tags for orientation (position code only, short), full
// detail only in a side panel on click. That's what this does now.
const labelLayer = document.getElementById('labelLayer');
const panel = document.getElementById('panel');
const panelCode = document.getElementById('panelCode');
const panelRows = document.getElementById('panelRows');
const panelMeta = document.getElementById('panelMeta');
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const pickables = [];
const posLabels = [];

LOADS.forEach(ld => {{
  const mat = new THREE.MeshStandardMaterial({{color: ld.color}});
  const block = new THREE.Mesh(new THREE.BoxGeometry(ld.w, ld.h, ld.d), mat);
  block.position.set(ld.x + ld.w/2, ld.y0 + ld.h/2, ld.z + ld.d/2);
  block.userData = ld;
  scene.add(block);
  pickables.push(block);
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(block.geometry),
    new THREE.LineBasicMaterial({{color: 0x111417, transparent:true, opacity:0.35}})
  );
  edges.position.copy(block.position);
  scene.add(edges);

  // Small code-only tag -- orientation, not detail. Short enough that
  // overlap stays readable even with many positions on screen at once.
  const div = document.createElement('div');
  div.className = 'pos-label';
  div.textContent = ld.code;
  labelLayer.appendChild(div);
  posLabels.push({{div, x: ld.x + ld.w/2, y: ld.y0 + ld.h + 8, z: ld.z + ld.d/2}});
}});

function showPanel(ld) {{
  panelCode.textContent = ld.code;
  panelRows.innerHTML = ld.rows.map(r => `<div class="row">${{r.lane}} — ${{r.name}} <span style="color:#767c85;font-weight:600;">(${{r.crates}}cr)</span></div>`).join('');
  panelMeta.textContent = `${{ld.filled}} / ${{ld.cap}} crates (${{Math.round(100*ld.filled/ld.cap)}}% full)`;
  panel.style.display = 'block';
}}

function onPick(clientX, clientY) {{
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);
  const hit = raycaster.intersectObjects(pickables)[0];
  if (hit) showPanel(hit.object.userData);
}}
renderer.domElement.addEventListener('click', (e) => onPick(e.clientX, e.clientY));

const labelVec = new THREE.Vector3();
const labelToggle = document.getElementById('labelToggle');
function updateLabels() {{
  const show = labelToggle.checked;
  labelLayer.style.display = show ? 'block' : 'none';
  if (!show) return;
  const rect = renderer.domElement.getBoundingClientRect();
  for (const lb of posLabels) {{
    labelVec.set(lb.x, lb.y, lb.z);
    labelVec.project(camera);
    if (labelVec.z > 1) {{ lb.div.style.display = 'none'; continue; }}
    const sx = (labelVec.x * 0.5 + 0.5) * rect.width;
    const sy = (-labelVec.y * 0.5 + 0.5) * rect.height;
    if (sx < -30 || sx > rect.width + 30 || sy < -20 || sy > rect.height + 20) {{
      lb.div.style.display = 'none';
      continue;
    }}
    lb.div.style.display = 'block';
    lb.div.style.left = sx + 'px';
    lb.div.style.top = sy + 'px';
  }}
}}

// ---- Walk mode: first-person WASD + mouse-look, like walking the aisle
// yourself instead of orbiting the whole room from outside. Toggle back to
// the normal orbit/overview camera any time with the same button or Esc. ----
const walkBtn = document.getElementById('walkBtn');
const crosshair = document.getElementById('crosshair');
const plControls = new THREE.PointerLockControls(camera, renderer.domElement);
let walking = false;
const walkKeys = {{}};
const EYE_HEIGHT = 66; // ~5'6" eye height in inches, matches the room's inch units
document.addEventListener('keydown', e => walkKeys[e.code] = true);
document.addEventListener('keyup', e => walkKeys[e.code] = false);
walkBtn.addEventListener('click', () => {{
  if (!walking) {{
    camera.position.set(CFG.roomW*0.5, EYE_HEIGHT, -60);
    plControls.getObject().rotation.set(0,0,0);
    plControls.lock();
  }} else {{
    plControls.unlock();
  }}
}});
plControls.addEventListener('lock', () => {{
  walking = true;
  controls.enabled = false;
  walkBtn.textContent = 'Exit walk mode (Esc)';
  crosshair.style.display = 'block';
  panel.style.display = 'none';
}});
plControls.addEventListener('unlock', () => {{
  walking = false;
  controls.enabled = true;
  walkBtn.textContent = 'Walk mode (WASD + mouse)';
  crosshair.style.display = 'none';
}});
renderer.domElement.addEventListener('click', () => {{
  // Walking-mode click = pick whatever's under the crosshair (screen center),
  // since the mouse cursor itself is hidden/locked during pointer-lock.
  if (walking) {{
    raycaster.setFromCamera(new THREE.Vector2(0,0), camera);
    const hit = raycaster.intersectObjects(pickables)[0];
    if (hit) showPanel(hit.object.userData);
  }}
}});
const WALK_SPEED = 160; // inches/sec
const walkVelocity = new THREE.Vector3();
function updateWalk(dt) {{
  if (!walking) return;
  walkVelocity.set(0,0,0);
  if (walkKeys['KeyW']) walkVelocity.z -= 1;
  if (walkKeys['KeyS']) walkVelocity.z += 1;
  if (walkKeys['KeyA']) walkVelocity.x -= 1;
  if (walkKeys['KeyD']) walkVelocity.x += 1;
  if (walkVelocity.lengthSq() > 0) {{
    walkVelocity.normalize().multiplyScalar(WALK_SPEED*dt);
    plControls.moveRight(walkVelocity.x);
    plControls.moveForward(-walkVelocity.z);
  }}
  camera.position.y = EYE_HEIGHT;
  // clamp inside the room so you can't walk through walls
  camera.position.x = Math.max(4, Math.min(CFG.roomW-4, camera.position.x));
  camera.position.z = Math.max(-100, Math.min(CFG.roomD-4, camera.position.z));
}}
let lastT = 0;

function animate(t) {{
  requestAnimationFrame(animate);
  const dt = Math.min(0.05, (t - lastT) / 1000 || 0);
  lastT = t;
  if (walking) {{
    updateWalk(dt);
  }} else {{
    controls.update();
  }}
  renderer.render(scene, camera);
  updateLabels();
}}
requestAnimationFrame(animate);

window.addEventListener('resize', () => {{
  camera.aspect = wrap.clientWidth/wrap.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
}});
</script>
</body></html>
'''

open('/home/claude/hummusfit-warehouse/backstock/backstock_3d.html', 'w').write(html_doc)
print('3D HTML written:', len(html_doc), 'bytes')
