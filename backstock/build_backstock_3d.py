"""
3D mockup of the backstock room -- built from the confirmed geometry in
backstock_geometry.json, with the ACTUAL product-location assignment from
backstock_location_assignment.csv / position_fill.json rendered as colored
crate-load blocks per position (real 3.5-day crate counts, real Shopify u30
demand -- see build_backstock_location_assignment.py for the math). Color =
category. Block height = how full that position is relative to its capacity.
"""
import json, colorsys, hashlib

g = json.load(open('/home/claude/hummusfit-warehouse/backstock/backstock_geometry.json'))
pos_fill = json.load(open('/home/claude/hummusfit-warehouse/backstock/position_fill.json'))
THREE_JS = open('/tmp/package/build/three.min.js').read()
ORBIT_JS = open('/tmp/package/examples/js/controls/OrbitControls.js').read()
POINTERLOCK_JS = open('/tmp/package/examples/js/controls/PointerLockControls.js').read()

ZONE_W = g['zone_width_in']          # 384in (32ft) -- Wall A's confirmed span
ZONE_L = g['zone_length_in']
WA_BAYS, WA_LEVELS, WA_DEPTH = 4, 7, 42
WD_BAYS_OURS, WD_LEVELS, WD_DEPTH = 2, 7, 42
WD_BAY_W = g['wall_d_bay_width_in']  # 96in, confirmed same as Wall A
WD_BAY_LEN = WD_BAY_W
C_BAYS = g['center_bays']            # 7, corrected from 6 (C07 added)
C_TOTAL_RUN = g['center_total_run_in']  # 378in (31.5ft) -- shorter than Wall A
CENTER_DEPTH = 40
AISLE = 132
LEVEL_H = 60  # Center pallet beam spacing, confirmed by Tony
# Wall A/D went from 3-4 levels to 7 per Tony's "add however many shelves you
# want" -- needed so every one of the 118 products gets an actual position
# instead of 69 having zero backstock reserve. Wire-deck shelving needs a much
# tighter pitch than Center's pallet beams: 10.70in crate + ~5in hand-grab/deck
# clearance = ~16in/level. 7 levels x 16in = 112in, fits inside a 10ft (120in)
# ceiling -- ASSUMED same as the main walk-in's confirmed 10ft, NOT independently
# confirmed for this room. Flag to Tony before building: if backstock ceiling is
# shorter than 10ft, 7 levels will not physically fit and this needs to drop.
WALL_LEVEL_H = 16
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
    'wallLevelH': WALL_LEVEL_H,
}

CAT_COLOR = {'meal': 0x3b82f6, 'muffin': 0xE8612C, 'oats': 0x22c55e, 'snack': 0x8b5cf6}
CAT_LABEL = {'meal': 'Meals (blue)', 'muffin': 'Muffins (orange)', 'oats': 'Oats (green)', 'snack': 'Snacks (purple)'}
# Hue (degrees) matching each CAT_COLOR, used as the center of that
# category's color family below.
CAT_HUE = {'meal': 217, 'muffin': 16, 'oats': 142, 'snack': 262}

# Per-Tony (Aug 2026): "if a pallet or shelf shares space with another
# variant of product we should indicate in crate colors to differentiate
# for my staff." position_fill.json shows this is common -- 42 of 70 filled
# backstock positions hold more than one product (a shelf's category is
# uniform, but the specific products on it aren't). A single category color
# per shelf hides that. Fix: give each distinct product its own shade
# within its category's color family -- a stable hash of the product name
# picks a hue offset (+/-22 degrees) and a lightness variant, so two
# products on the same shelf are visibly different crate colors, while
# still reading as "this is the meals shelf" at a glance from the category
# hue family. Deterministic (same product always gets the same shade,
# across rebuilds) rather than randomly assigned per build.
def product_color(name, cat):
    base_hue = CAT_HUE.get(cat, 210)
    hval = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue_offset = ((hval % 45) - 22)  # -22..+22 degrees
    lightness = 0.42 + ((hval // 45) % 5) * 0.045  # 0.42..0.60, 5 steps
    hue = ((base_hue + hue_offset) % 360) / 360
    r, gg, b = colorsys.hls_to_rgb(hue, lightness, 0.62)
    return (int(r*255) << 16) | (int(gg*255) << 8) | int(b*255)

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
    pitch = WALL_LEVEL_H if zone in ('walla', 'walld') else LEVEL_H
    y0 = (level-1) * pitch + 4
    h = max(6, (pitch - 10) * frac)
    # Structured per-product rows (lane code, name, crates) for the click panel --
    # full detail lives here now, not crammed into an always-visible floating label.
    # Sorted by crates desc so, on a mixed shelf, the biggest product gets the
    # first (bottom) crate-unit and its own distinct color takes priority if
    # there are more distinct products than crate-units to show.
    products_sorted = sorted(v['products'], key=lambda pr: -pr['crates'])
    rows = [{'lane': pr['lane'], 'name': pr['name'], 'crates': pr['crates']} for pr in products_sorted]
    row_colors = [product_color(pr['name'], cat) for pr in products_sorted]
    loads.append({
        'x': x, 'z': z, 'w': w, 'd': d, 'y0': y0, 'h': h,
        'color': CAT_COLOR.get(cat, 0x9aa0a8), 'code': code, 'cat': cat,
        'filled': v['filled'], 'cap': v['cap'], 'rows': rows, 'rowColors': row_colors,
        'mixed': len(products_sorted) > 1,
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
  /* Touch walk controls (iPad/iPhone) -- Pointer Lock API doesn't exist on
     iOS/iPadOS Safari at all (not "flaky", genuinely unimplemented -- WebKit
     has never shipped it on touch platforms), so walk mode there can't use
     the same mouse-look + WASD scheme as desktop. This is a virtual
     joystick (left thumb, move) + drag-to-look (right thumb, look),
     the standard mobile-FPS control split, with a real on-screen exit
     button since there's no Escape key to fall back on. */
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
    <b>Backstock Room — full 118-product coverage (Center = pallets, one SKU each)</b><br>
    Colored blocks = actual crate load per position, from backstock_location_assignment.csv.<br>
    <span style="color:#60a5fa">■</span> Meals &nbsp; <span style="color:#E8612C">■</span> Muffins &nbsp; <span style="color:#4ade80">■</span> Oats &nbsp; <span style="color:#a78bfa">■</span> Snacks<br>
    Block height = how full that position is (short = lightly filled, tall = at capacity).
  </div>
  <div id="toggle">
    Click any block for full details · drag to rotate · scroll to zoom<br>
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
  scene.add(rackBay(CFG.wallA.x0 + b*CFG.wallA.bayW, CFG.wallA.y0, CFG.wallA.bayW-2, CFG.wallA.depth, CFG.wallA.levels, CFG.wallLevelH, GREEN));
}}

// Wall D -- 2 bays, 4 levels, green, left side (only 2 of 3 bays ours; 3rd shown gray)
for (let b=0; b<3; b++) {{
  const color = b < CFG.wallD.bays ? GREEN : GRAYKIT;
  scene.add(rackBay(CFG.wallD.x0, CFG.wallD.y0 + b*CFG.wallD.bayLen, CFG.wallD.depth, CFG.wallD.bayLen-2, CFG.wallD.levels, CFG.wallLevelH, color));
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

// ---- Real-crate look (Aug 2026, per Tony's Costco link): IRIS 45QT clear
// storage bin w/ buckles, 21.65"L x 15.70"W x 10.70"H, semi-clear plastic
// body, black snap-lock buckle latches, grooved stacking lid. Shopify
// product photos were ruled out as textures (container photos don't match
// the actual physical totes), so this instead builds an actual crate LOOK
// out of geometry -- a translucent clear shell + a solid inner "contents"
// core tinted by category (so the at-a-glance color coding survives even
// though the shell itself is no longer solid-colored) + dark buckle straps
// + a lid cap line. Each position's existing envelope (x/y0/w/h/d, still
// computed in Python exactly as before -- this does NOT change layout,
// fullness math, or footprint, only how each fill amount is drawn) gets
// subdivided into 1-3 stacked crate-look units instead of one flat slab,
// since real totes are visibly separate stacked units, not a single solid
// block. Unit count is a visual read of "how full" (more stacked crates =
// fuller), NOT a literal per-unit inventory count -- position_fill.json's
// filled/cap are unit counts (up to 24), not literal crate counts, so a
// literal 1-crate-per-unit render would mean dozens of boxes per shelf.
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

  // Solid-colored contents core, visible through the translucent shell --
  // this is what preserves the category color-coding at a glance.
  const core = new THREE.Mesh(
    new THREE.BoxGeometry(w*0.72, h*0.6, d*0.72),
    crateCoreMat(color)
  );
  core.position.y = -h*0.05;
  group.add(core);

  // Grooved lid cap -- a slightly wider, flatter slab sitting on top,
  // matching the real bin's lid overhang.
  const lidH = Math.max(1.2, h*0.14);
  const lid = new THREE.Mesh(new THREE.BoxGeometry(w*1.04, lidH, d*1.04), CRATE_LID);
  lid.position.y = h/2 - lidH/2 + 0.3;
  group.add(lid);

  // Black snap-lock buckle straps on the two long (depth-facing) sides,
  // matching the real bin's side latches.
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
  // 1-3 stacked crate-look units per position. For a single-product shelf
  // this is still just a visual read of fullness (see comment above). For a
  // MIXED shelf (ld.mixed -- more than one distinct product sharing this
  // position, common: 42/70 filled backstock positions), each unit instead
  // gets that product's own distinct color from ld.rowColors, biggest
  // product first, so staff can see at a glance "this shelf has more than
  // one thing on it" instead of one flat category color hiding the mix.
  // With more distinct products than crate-units (rare, only shows up to
  // 3), the remaining smaller products still show correctly in the click
  // panel's full product list -- only the crate-color slots are capped.
  const nCrates = ld.mixed
    ? Math.min(3, ld.rows.length)
    : Math.max(1, Math.min(3, Math.round(ld.h / 14)));
  const unitH = ld.h / nCrates;
  const cx = ld.x + ld.w/2, cz = ld.z + ld.d/2;
  let pickTarget = null;
  for (let i = 0; i < nCrates; i++) {{
    const color = ld.mixed ? ld.rowColors[i] : ld.color;
    const unit = buildCrateUnit(ld.w, unitH * 0.92, ld.d, color);
    unit.position.set(cx, ld.y0 + unitH*i + unitH/2, cz);
    unit.userData = ld;
    scene.add(unit);
    // Only the outer shell needs to be pickable -- raycasting against every
    // sub-mesh (core/lid/buckles) is redundant since they're all coincident.
    unit.children[0].userData = ld;
    pickables.push(unit.children[0]);
    if (!pickTarget) pickTarget = unit;
  }}

  // Small code-only tag -- orientation, not detail. Short enough that
  // overlap stays readable even with many positions on screen at once.
  const div = document.createElement('div');
  div.className = 'pos-label';
  div.textContent = ld.code;
  labelLayer.appendChild(div);
  posLabels.push({{div, x: ld.x + ld.w/2, y: ld.y0 + ld.h + 8, z: ld.z + ld.d/2}});
}});

// Live Shopify on-hand crate targets, fetched once on load and reused by
// showPanel() below. This is the SAME live layer that patches blueprint.html
// -- backstock physical locations never change, only the "how many crates
// should be here" number does, so this just overlays that number wherever a
// product name matches. See /api/target-crates on the server.
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
  panelRows.innerHTML = ld.rows.map(r => {{
    const live = LIVE_TARGETS[r.name];
    const crateText = (live && live.target_crates != null)
      ? `<span style="color:#2BBFAA;font-weight:800;" title="Live from Shopify on-hand inventory as of ${{LIVE_SYNCED_AT ? new Date(LIVE_SYNCED_AT).toLocaleString() : ''}}">${{live.target_crates}}cr live</span>`
      : `<span style="color:#767c85;font-weight:600;">${{r.crates}}cr</span>`;
    return `<div class="row">${{r.lane}} — ${{r.name}} ${{crateText}}</div>`;
  }}).join('');
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

// ---- Walk mode: first-person move + look, like walking the aisle yourself
// instead of orbiting the whole room from outside. Two control schemes:
//  - Desktop (has a mouse): WASD + Pointer Lock mouse-look, via
//    THREE.PointerLockControls, toggled/exited with the walk button or Esc.
//  - Touch (iPad/iPhone -- confirmed Aug 2026 as the primary device for the
//    picking team): the Pointer Lock API is not a "sometimes flaky" thing
//    here, it's UNIMPLEMENTED on iOS/iPadOS Safari entirely (no mouse to
//    lock -- WebKit has never shipped it on touch platforms), so no amount
//    of retry/fallback logic makes plControls.lock() succeed there. Touch
//    gets its own scheme instead: a virtual joystick (left thumb, move) +
//    drag-to-look (right side of screen, look), the standard mobile-FPS
//    split, driving the SAME camera via plControls.moveForward/moveRight
//    (those just read/write camera.position + camera.matrix directly --
//    nothing in them actually depends on pointer lock being active) plus
//    a manual quaternion update for look, copied from the same Euler math
//    PointerLockControls itself uses for mouse movement. A real on-screen
//    exit button is shown too, since touch has no Escape key.
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
const EYE_HEIGHT = 66; // ~5'6" eye height in inches, matches the room's inch units
document.addEventListener('keydown', e => walkKeys[e.code] = true);
document.addEventListener('keyup', e => walkKeys[e.code] = false);
if (IS_TOUCH) {{
  walkBtn.textContent = 'Walk mode (touch)';
}}

// ---- shared enter/exit, used by both the desktop pointer-lock path and
// the touch path so behavior (camera reset, orbit-controls disable, panel
// hide, etc.) can't drift between the two. ----
function enterWalk() {{
  walking = true;
  controls.enabled = false;
  // Two stacked pre-existing bugs found testing the touch fix (Aug 2026),
  // both independent of pointer lock, both making walk mode look "broken"
  // even when everything under the hood is working:
  //  1. identity/zero rotation here faces straight down -Z, which is AWAY
  //     from the room, not into it (room geometry is all at z > 0).
  //  2. the old z=-60 starting position sits OUTSIDE the room, in front of
  //     the front wall (wallSeg draws one continuous panel across the full
  //     room width at z=0-ish, with no door gap actually cut into the
  //     mesh). So even facing the right way, the camera was still staring
  //     at a flat, evenly-lit wall face from ~2ft away -- which fills the
  //     entire frame with one flat gray color, visually indistinguishable
  //     from a blank/broken screen in a quick glance. Confirmed by sampling
  //     rendered pixels directly: uniform color across the whole canvas at
  //     z=-60, varied real geometry colors once moved to z=30.
  // Fix: face +Z (into the room), AND start just inside the wall instead
  // of outside it.
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
  // Point orbit controls at wherever walking left off, so returning to
  // orbit mode doesn't snap the camera back to its pre-walk framing.
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
  if (IS_TOUCH) {{
    enterWalk(); // no lock to request -- touch has nothing pointer lock can grant
  }} else {{
    plControls.lock();
  }}
}});
walkExitBtn.addEventListener('click', () => {{ if (walking) exitWalk(); }});
// Bug fix (Aug 2026): this used to set camera.position/rotation and call
// plControls.lock() together in the click handler, BEFORE knowing whether
// pointer lock actually succeeded. PointerLockControls silently swallows a
// failed lock request (just a console.error, no 'unlock' or error event
// fires from the library) -- so on any browser/context where pointer lock
// is rejected, the camera got yanked into the walking eye position and
// orbit controls got left enabled with a stale internal state, rendering a
// blank gray screen with no recovery. Fix: only touch the camera once
// 'lock' actually fires, and listen for pointerlockerror ourselves so a
// rejected request fails visibly instead of corrupting the view silently.
plControls.addEventListener('lock', enterWalk);
plControls.addEventListener('unlock', exitWalk);
document.addEventListener('pointerlockerror', () => {{
  // Desktop-only path (IS_TOUCH never calls plControls.lock(), so this
  // can't fire there). Library only console.errors this -- without our own
  // listener the UI stays stuck saying "Walk mode (WASD + mouse)" with no
  // clue anything went wrong, while nothing in the scene actually changed
  // (we no longer mutate the camera before lock succeeds, so orbit mode is
  // still intact).
  walkBtn.textContent = 'Walk mode unavailable in this browser';
  walkBtn.disabled = true;
  setTimeout(() => {{ walkBtn.textContent = 'Walk mode (WASD + mouse)'; walkBtn.disabled = false; }}, 3000);
}});
renderer.domElement.addEventListener('click', () => {{
  // Desktop walking-mode click = pick whatever's under the crosshair
  // (screen center), since the mouse cursor itself is hidden/locked during
  // pointer-lock. Touch has its own tap-to-pick in the touch handlers below
  // (a synthetic 'click' doesn't fire reliably the same way after a
  // touchend during an active custom drag gesture).
  if (walking && !IS_TOUCH) {{
    raycaster.setFromCamera(new THREE.Vector2(0,0), camera);
    const hit = raycaster.intersectObjects(pickables)[0];
    if (hit) showPanel(hit.object.userData);
  }}
}});
const WALK_SPEED = 160; // inches/sec
const walkVelocity = new THREE.Vector3();
// Touch joystick state -- set by the joystick touch handlers below, read
// each frame by updateWalk(). x/y in [-1,1], 0 when the joystick isn't
// currently being dragged.
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
  // Clamp inside the room so you can't walk through walls. z used to allow
  // back down to -100 -- letting you walk backward straight through the
  // (doorless, in this model) front wall and out into the same dead zone
  // the entry-position bug above put you in by default. 4 keeps you just
  // inside the front wall instead.
  camera.position.x = Math.max(4, Math.min(CFG.roomW-4, camera.position.x));
  camera.position.z = Math.max(4, Math.min(CFG.roomD-4, camera.position.z));
}}

// ---- Touch controls: virtual joystick (move) + drag-to-look, tracked by
// touch identifier so two thumbs on screen at once don't fight each other.
// Joystick "claims" any touch that starts inside its base circle; every
// other touch that starts while walking is a look/select touch. ----
if (IS_TOUCH) {{
  const JOY_R = 55; // px, matches #joyBase's 110px diameter
  let joyTouchId = null, joyOriginX = 0, joyOriginY = 0;
  const LOOK_SENS = 0.0035;
  const TAP_MOVE_THRESHOLD = 12; // px -- drags shorter than this count as a tap-to-select, not a look-drag
  const lookTouches = {{}}; // id -> {{x, y, startX, startY, moved}}

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
    // x: left/right strafe, matches walkKeys A/D. y: forward is dragging UP
    // (negative dy), matching W -- so touchMove.z uses dy directly (both
    // "up/forward" are negative in their respective axes).
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
          // Tap without a drag = pick whatever's at the tap point.
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
