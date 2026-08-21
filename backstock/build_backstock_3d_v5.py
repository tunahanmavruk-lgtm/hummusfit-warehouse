"""
3D backstock room, v5 -- confirmed layout (not a mockup). Every position
holds exactly one lane code shared with the main walk-in blueprint (M1/M2/M3
meals, K1/K2/K3 bakery/oats/snacks). Replaces the old A/C/D demand-mixed
model entirely per Tony's relayout request (Aug 21, 2026): "coordinate this
fridge to sync with smaller fridge and the codes so its less confusing for
pickers." Confirmed to build exactly as mockup v4 showed -- no manual
K2-05-first reshuffle, M1-28 stays Ground Beef.

Reuses the crate-visual look, walk mode, live-inventory overlay, and pick
panel verbatim from the prior build_backstock_3d.py -- only the room
geometry and per-position load list changed.
"""
import json, colorsys, hashlib

geo = json.load(open('/home/claude/hummusfit-warehouse/backstock/backstock_geometry_v5.json'))
positions = json.load(open('/home/claude/hummusfit-warehouse/backstock/position_fill_v5.json'))
THREE_JS = open('/tmp/package/build/three.min.js').read()
ORBIT_JS = open('/tmp/package/examples/js/controls/OrbitControls.js').read()
POINTERLOCK_JS = open('/tmp/package/examples/js/controls/PointerLockControls.js').read()

CAT_COLOR = {'meal': 0x3b82f6, 'muffin': 0xE8612C, 'oats': 0x22c55e, 'snack': 0x8b5cf6}
CAT_HUE = {'meal': 217, 'muffin': 16, 'oats': 142, 'snack': 262}

def product_color(name, cat):
    base_hue = CAT_HUE.get(cat, 210)
    hval = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue_offset = ((hval % 45) - 22)
    lightness = 0.42 + ((hval // 45) % 5) * 0.045
    hue = ((base_hue + hue_offset) % 360) / 360
    r, gg, b = colorsys.hls_to_rgb(hue, lightness, 0.62)
    return (int(r * 255) << 16) | (int(gg * 255) << 8) | int(b * 255)

config = {
    'roomW': geo['room_w'], 'roomD': geo['room_d'],
    'xOffset': geo['x_offset'],
    'wallA': geo['wallA'], 'wallD': geo['wallD'],
    'pallets': geo['pallets'], 'center': geo['center'],
}

loads = []
for code, v in positions.items():
    if not v.get('code'):
        continue  # empty Wall D slot, drawn as an unfilled rack bay only
    zone = v['zone']
    if zone == 'walld':
        x = v['x']
        z = v['z']
    else:
        x = config['xOffset'] + v['x']
        z = v['z']
    w, d = v['w'] - 2, v['d'] - 4
    level_h = v['level_h']
    level = v['level']
    y0 = (level - 1) * level_h + 4
    cap = v['cap'] or 1
    frac = min(1.0, v['crates'] / cap) if cap else 0.3
    h = max(10, (level_h - 14) * max(frac, 0.35))
    loads.append({
        'x': x, 'z': z, 'w': max(w, 4), 'd': max(d, 4), 'y0': y0, 'h': h,
        'color': product_color(v['product'], v['cat']),
        'code': v['code'], 'cat': v['cat'], 'product': v['product'],
        'crates': v['crates'], 'cap': v['cap'], 'zone': zone,
    })

print(f"{len(loads)} loaded positions -> 3D")

html_doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Hummus Fit — Backstock Room 3D</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  html,body{{margin:0;height:100%;overflow:hidden;font-family:'Inter',-apple-system,sans-serif;background:#dfe3e6;}}
  #wrap{{position:relative;width:100%;height:100%;}}
  #hud{{position:absolute;top:16px;left:16px;background:rgba(17,20,23,0.85);color:#fff;padding:14px 18px;border-radius:12px;font-size:12.5px;line-height:1.6;max-width:340px;}}
  #hud b{{color:#2BBFAA;}}
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
  #crosshair{{position:absolute;top:50%;left:50%;width:6px;height:6px;margin:-3px 0 0 -3px;border-radius:50%;background:rgba(255,255,255,.85);border:1px solid rgba(0,0,0,.4);display:none;pointer-events:none;}}
  #walkTouchHint{{position:absolute;bottom:16px;left:50%;transform:translateX(-50%);background:rgba(17,20,23,0.75);color:#fff;font-size:11.5px;font-weight:700;padding:6px 12px;border-radius:8px;display:none;pointer-events:none;text-align:center;}}
  #joyBase{{position:absolute;width:110px;height:110px;border-radius:50%;background:rgba(255,255,255,.14);border:2px solid rgba(255,255,255,.4);display:none;touch-action:none;}}
  #joyKnob{{position:absolute;width:46px;height:46px;border-radius:50%;background:rgba(255,255,255,.55);border:2px solid rgba(255,255,255,.75);left:32px;top:32px;pointer-events:none;}}
  #walkExitBtn{{position:absolute;top:16px;left:50%;transform:translateX(-50%);background:rgba(232,97,44,0.92);color:#fff;border:none;border-radius:10px;padding:10px 20px;font-size:13px;font-weight:800;display:none;z-index:20;}}
</style>
</head>
<body>
<div id="wrap">
  <div id="pagenav"><a href="/blueprint.html">Blueprint</a><a href="/3d-model.html">3D Model</a><a href="/backstock-blueprint.html">Backstock Blueprint</a><a href="/backstock-3d.html" class="active">Backstock 3D</a></div>
  <div id="hud">
    <b>Backstock Room — codes match the main walk-in (M1/M2/M3 meals, K1/K2 bakery/oats/snacks)</b><br>
    Each block = one lane code's backstock reserve position.<br>
    <span style="color:#60a5fa">■</span> Meals &nbsp; <span style="color:#E8612C">■</span> Muffins &nbsp; <span style="color:#4ade80">■</span> Oats &nbsp; <span style="color:#a78bfa">■</span> Snacks<br>
    Block height = reserve crates vs. that lane's capacity.
  </div>
  <div id="toggle">
    Click any block for details · drag to rotate · scroll to zoom<br>
    <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-weight:600;margin-top:4px;"><input type="checkbox" id="labelToggle" checked> Show position code tags</label>
    <button id="walkBtn" style="margin-top:8px;width:100%;background:#2BBFAA;color:#fff;border:none;border-radius:8px;padding:7px 10px;font-size:12px;font-weight:800;cursor:pointer;">Walk mode (WASD + mouse)</button>
    <div id="liveBadge" style="margin-top:8px;display:flex;align-items:center;gap:6px;"><span id="liveDot" style="width:7px;height:7px;border-radius:50%;background:#767c85;flex-shrink:0;"></span><span id="liveBadgeText">Checking live inventory…</span></div>
  </div>
  <div id="labelLayer"></div>
  <div id="panel">
    <div class="code" id="panelCode"></div>
    <div id="panelRows"></div>
    <div class="meta" id="panelMeta"></div>
  </div>
  <div id="crosshair"></div>
  <button id="walkExitBtn">Exit walk mode</button>
  <div id="walkTouchHint">Left thumb: move &nbsp;•&nbsp; right side: drag to look &nbsp;•&nbsp; tap a shelf to select</div>
  <div id="joyBase"><div id="joyKnob"></div></div>
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
camera.position.set(CFG.roomW*1.3, 500, CFG.roomD*1.3);
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

const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(CFG.roomW, CFG.roomD),
  new THREE.MeshStandardMaterial({{color: 0x9aa0a8}})
);
floor.rotation.x = -Math.PI/2;
floor.position.set(CFG.roomW/2, 0, CFG.roomD/2);
scene.add(floor);

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
  const postGeo = new THREE.BoxGeometry(3, levels*levelH, 3);
  const postMat = new THREE.MeshStandardMaterial({{color}});
  [[0,0],[w,0],[0,d],[w,d]].forEach(([px,pz]) => {{
    const post = new THREE.Mesh(postGeo, postMat);
    post.position.set(x+px, levels*levelH/2, z+pz);
    group.add(post);
  }});
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

// Wall A -- 4 bays, 2 shelves, door end
for (let b=0; b<CFG.wallA.bays; b++) {{
  scene.add(rackBay(CFG.xOffset + b*CFG.wallA.bay_w, CFG.wallA.z0, CFG.wallA.bay_w-2, CFG.wallA.depth, CFG.wallA.levels, CFG.wallA.level_h, GREEN));
}}

// Wall D -- 2 bays (ours), 2 floors, left side. 3rd physical bay (not ours) shown gray.
for (let b=0; b<3; b++) {{
  const color = b < CFG.wallD.bays ? GREEN : GRAYKIT;
  scene.add(rackBay(0, b*CFG.wallD.bay_len, CFG.wallD.depth, CFG.wallD.bay_len-2, CFG.wallD.levels, CFG.wallD.level_h, color));
}}

// Pallets -- 8 double-sided, between the two aisles
for (let p=0; p<CFG.pallets.count; p++) {{
  const x = CFG.xOffset + p*CFG.pallets.w;
  scene.add(rackBay(x, CFG.pallets.z_front, CFG.pallets.w-2, CFG.pallets.face_depth-2, 1, CFG.pallets.face_depth, ORANGE));
  scene.add(rackBay(x, CFG.pallets.z_back, CFG.pallets.w-2, CFG.pallets.face_depth-2, 1, CFG.pallets.face_depth, ORANGE));
}}

// Center -- 7 bays, double-deep. Front (ours, K1/K2) + back (kitchen's, gray)
for (let b=0; b<CFG.center.bays; b++) {{
  scene.add(rackBay(CFG.xOffset + b*CFG.center.bay_w, CFG.center.z0, CFG.center.bay_w-2, CFG.center.depth, CFG.center.levels, CFG.center.level_h, DARKINK));
  scene.add(rackBay(CFG.xOffset + b*CFG.center.bay_w, CFG.center.z0 + CFG.center.depth, CFG.center.bay_w-2, CFG.center.depth, CFG.center.levels, CFG.center.level_h, GRAYKIT));
}}
if (CFG.center.total_run < CFG.wallA.bays * CFG.wallA.bay_w) {{
  const gapW = CFG.wallA.bays*CFG.wallA.bay_w - CFG.center.total_run;
  const gapPad = new THREE.Mesh(
    new THREE.BoxGeometry(gapW - 2, 2, CFG.center.depth*2 - 2),
    new THREE.MeshStandardMaterial({{color: 0xc7cbd1, transparent:true, opacity:0.5}})
  );
  gapPad.position.set(CFG.xOffset + CFG.center.total_run + gapW/2, 1, CFG.center.z0 + CFG.center.depth);
  scene.add(gapPad);
}}

const labelLayer = document.getElementById('labelLayer');
const panel = document.getElementById('panel');
const panelCode = document.getElementById('panelCode');
const panelRows = document.getElementById('panelRows');
const panelMeta = document.getElementById('panelMeta');
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const pickables = [];
const posLabels = [];

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

LOADS.forEach(ld => {{
  const cx = ld.x + ld.w/2, cz = ld.z + ld.d/2;
  const unit = buildCrateUnit(ld.w, ld.h * 0.92, ld.d, ld.color);
  unit.position.set(cx, ld.y0 + ld.h/2, cz);
  unit.userData = ld;
  scene.add(unit);
  unit.children[0].userData = ld;
  pickables.push(unit.children[0]);

  const div = document.createElement('div');
  div.className = 'pos-label';
  div.textContent = ld.code;
  labelLayer.appendChild(div);
  posLabels.push({{div, x: cx, y: ld.y0 + ld.h + 8, z: cz}});
}});

let LIVE_TARGETS = {{}};
let LIVE_SYNCED_AT = null;
fetch('/api/target-crates').then(r => r.json()).then(data => {{
  LIVE_TARGETS = data.products || {{}};
  LIVE_SYNCED_AT = data.last_sync;
  const dot = document.getElementById('liveDot');
  const txt = document.getElementById('liveBadgeText');
  if (!LIVE_SYNCED_AT) {{ txt.textContent = 'Live inventory not connected yet'; return; }}
  dot.style.background = '#2BBFAA';
  txt.textContent = `Live inventory synced ${{new Date(LIVE_SYNCED_AT).toLocaleString()}}`;
}}).catch(() => {{
  document.getElementById('liveBadgeText').textContent = 'Live inventory unavailable';
}});

function showPanel(ld) {{
  panelCode.textContent = ld.code;
  const live = LIVE_TARGETS[ld.product];
  const crateText = (live && live.target_crates != null)
    ? `<span style="color:#2BBFAA;font-weight:800;" title="Live from Shopify on-hand inventory as of ${{LIVE_SYNCED_AT ? new Date(LIVE_SYNCED_AT).toLocaleString() : ''}}">${{live.target_crates}}cr live</span>`
    : `<span style="color:#767c85;font-weight:600;">${{ld.crates}}cr</span>`;
  panelRows.innerHTML = `<div class="row">${{ld.product}} ${{crateText}}</div>`;
  panelMeta.textContent = `Matches main blueprint lane ${{ld.code}} · cap ${{ld.cap}}`;
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

function enterWalk() {{
  walking = true;
  controls.enabled = false;
  camera.position.set(CFG.roomW*0.5, EYE_HEIGHT, 30);
  camera.quaternion.setFromEuler(new THREE.Euler(0, Math.PI, 0, 'YXZ'));
  crosshair.style.display = 'block';
  panel.style.display = 'none';
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
renderer.domElement.addEventListener('click', () => {{
  if (walking && !IS_TOUCH) {{
    raycaster.setFromCamera(new THREE.Vector2(0,0), camera);
    const hit = raycaster.intersectObjects(pickables)[0];
    if (hit) showPanel(hit.object.userData);
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
  camera.position.x = Math.max(4, Math.min(CFG.roomW-4, camera.position.x));
  camera.position.z = Math.max(4, Math.min(CFG.roomD-4, camera.position.z));
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
    joyKnob.style.left = '32px';
    joyKnob.style.top = '32px';
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
          const hit = raycaster.intersectObjects(pickables)[0];
          if (hit) showPanel(hit.object.userData);
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
