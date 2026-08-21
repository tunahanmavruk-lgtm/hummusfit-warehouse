"""
2D top-down backstock blueprint, v5 -- confirmed layout. One box per lane
code (matching the main walk-in blueprint's own code scheme), built from
position_fill_v5.json / backstock_geometry_v5.json. Replaces the old
A01-A04/C01-C07/D01-D02 diagram.

This is a diagrammatic ("exploded") layout, not a literal single-plane
top-down projection: Wall D's 2 floors, Wall A's 2 shelves, and Center's 2
floors (K1/K2) are stacked in HEIGHT in the real room (same X/Z footprint
per level), so each level gets its own horizontal strip here instead of
literally overlapping. Same convention the mockup (v4) used.
"""
import json

geo = json.load(open('/home/claude/hummusfit-warehouse/backstock/backstock_geometry_v5.json'))
positions = json.load(open('/home/claude/hummusfit-warehouse/backstock/position_fill_v5.json'))

SCALE = 1.15
MARGIN = 44
GAP = 26

wallA = geo['wallA']; wallD = geo['wallD']; pallets = geo['pallets']; center = geo['center']
ZONE_W = geo['zone_w']
X_OFF = geo['x_offset']

# ---- Right-hand column layout cursor (Wall A / Pallets / Center), top to bottom ----
cursor = 0
wa_shelf_h = wallA['depth']
WA_Y0 = {2: cursor, 1: cursor + wa_shelf_h + 6}  # shelf 2 (top) drawn above shelf 1 (bottom)
cursor += 2 * wa_shelf_h + 6 + GAP

PALLET_FRONT_Y0 = cursor
PALLET_BACK_Y0 = cursor + pallets['face_depth'] + 4
cursor += 2 * pallets['face_depth'] + 4 + GAP

c_floor_h = center['depth']
CENTER_Y0 = {1: cursor, 2: cursor + c_floor_h + 6}
cursor += 2 * c_floor_h + 6 + GAP
RIGHT_COL_H = cursor

# ---- Left column: Wall D, 2 floors stacked, each floor = 8 rows x 2 cols ----
wd_floor_h = wallD['total_len']  # one floor's full length-of-wall footprint
WD_Y0 = {1: 0, 2: wd_floor_h + GAP}
LEFT_COL_H = 2 * wd_floor_h + GAP

ROOM_D = max(LEFT_COL_H, RIGHT_COL_H)
ROOM_W = X_OFF + ZONE_W
SVG_W = ROOM_W * SCALE + MARGIN * 2
SVG_H = (ROOM_D + 40) * SCALE + MARGIN * 2 + 20

CAT_FILL = {'meal': '#dbe9ff', 'muffin': '#fde0d3', 'oats': '#d7f5e0', 'snack': '#ece0fb', None: '#f4f5f7'}

def X(x): return x * SCALE + MARGIN
def Y(y): return y * SCALE + MARGIN + 46

parts = []
parts.append(f'<rect x="{MARGIN}" y="{MARGIN+20}" width="{SVG_W - 2*MARGIN:.1f}" height="{SVG_H - 2*MARGIN - 20:.1f}" fill="#fafafa" stroke="#111417" stroke-width="3"/>')
parts.append(f'<text x="{X(4)}" y="{MARGIN+14:.1f}" font-size="11" font-weight="800" fill="#E8612C" font-family="Inter,sans-serif">DOOR END</text>')

def box(x, y, w, h, code, cat, mismatch=False):
    fill = CAT_FILL.get(cat) if code else '#eef0f4'
    stroke = '#c0392b' if mismatch else '#111417'
    sw = 2 if mismatch else 0.7
    parts.append(f'<rect x="{X(x):.1f}" y="{Y(y):.1f}" width="{w*SCALE:.1f}" height="{h*SCALE:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    label = code or '—'
    box_px = w * SCALE
    cx, cy = X(x + w/2), Y(y + h/2) + 2.5
    if box_px < 16:
        # Too narrow for horizontal text (Center's 30-35-wide rows) --
        # rotate the label vertically so it still fits and stays readable.
        parts.append(f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="6.4" text-anchor="middle" font-family="Inter,sans-serif" fill="#111417" transform="rotate(-90 {cx:.1f} {cy:.1f})">{label}</text>')
    else:
        fs = 6.4 if box_px < 28 else 7.2
        parts.append(f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="{fs}" text-anchor="middle" font-family="Inter,sans-serif" fill="#111417">{label}</text>')

for code, v in positions.items():
    zone = v['zone']
    real = bool(v.get('code'))
    w, d = v['w'] - 1.5, v['d'] - 1.5
    mismatch = v.get('code') == 'M1-28'
    if zone == 'walld':
        x = v['x']
        y = WD_Y0[v['level']] + v['z']
    elif zone == 'walla':
        x = X_OFF + v['x']
        y = WA_Y0[v['level']]
    elif zone == 'pallet':
        x = X_OFF + v['x']
        y = PALLET_FRONT_Y0 if v['face'] == 'front' else PALLET_BACK_Y0
    else:  # center
        x = X_OFF + v['x']
        y = CENTER_Y0[v['level']]
    box(x, y, w, d, v.get('code'), v.get('cat'), mismatch)

def zlabel(x, y, s, color='#5b6470', size=10.5):
    parts.append(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" font-size="{size}" font-weight="800" fill="{color}" text-anchor="middle" font-family="Inter,sans-serif">{s}</text>')

zlabel(X_OFF + ZONE_W / 2, WA_Y0[2] - 10, 'Wall A → M3 (2 shelves, shelf 2 on top)', '#5b6470', 10)
zlabel(X_OFF + ZONE_W / 2, PALLET_FRONT_Y0 - 10, 'Pallets → M2 (double-sided, 8 pallets)', '#E8612C', 10)
zlabel(X_OFF + ZONE_W / 2, CENTER_Y0[1] - 10, 'Center → K1 floor 1 (top strip) / K2 floor 2 (bottom strip)', '#111417', 10)
zlabel(X_OFF / 2, WD_Y0[1] - 14, 'Wall D floor 1 (M1-01…15)', '#E8612C', 8.5)
zlabel(X_OFF / 2, WD_Y0[2] - 14, 'Wall D floor 2 (M1-16…28)', '#E8612C', 8.5)

svg = f'<svg viewBox="0 0 {SVG_W:.0f} {SVG_H:.0f}" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">\n' + '\n'.join(parts) + '\n</svg>'
open('/home/claude/hummusfit-warehouse/backstock/backstock_blueprint.svg', 'w').write(svg)
print('SVG written', len(svg), 'bytes')
