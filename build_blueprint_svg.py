import json

g = json.load(open('/home/claude/hummusfit-warehouse/blueprint_geometry.json'))
lane_plan = json.load(open('/home/claude/hummusfit-warehouse/lane_plan.json'))

PX_PER_IN = 1.55
def X(v): return round(v * PX_PER_IN, 1)
def Y(v): return round(v * PX_PER_IN, 1)

ROOM_W = g['ROOM_W_IN']; ROOM_D = g['ROOM_D_IN']
MARGIN = 100
RIGHT_MARGIN = 300   # extra right margin for row-end / section labels, kept clear of the room
SVG_W = X(ROOM_W) + MARGIN + RIGHT_MARGIN
SVG_H = Y(ROOM_D) + MARGIN*2 + 60

TEAL = '#2BBFAA'
ORANGE = '#E8612C'
INK = '#111417'
DIM = '#767c85'
LINE = '#dfe3e8'
BAKERY_FILL = '#eafaf7'
MEALS_FILL = '#eef0f4'
FLAG_BG = '#fff3ea'

svg_parts = []
def add(s): svg_parts.append(s)

def room_x(v): return MARGIN + X(v)
def room_y(v): return MARGIN + Y(v)

def text_lines(x, y, lines, anchor='start', size=12, weight='400', fill=INK, line_h=None):
    """Proper multi-line SVG text using tspans (a literal \\n in a <text> node
    does NOT break lines in SVG - it renders as a collapsed space, which was
    silently pushing single-line-rendered labels wide enough to overflow past
    x=0 and get clipped by the SVG viewport)."""
    lh = line_h or (size * 1.25)
    parts = [f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{fill}">']
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else lh
        parts.append(f'<tspan x="{x}" dy="{dy}">{line}</tspan>')
    parts.append('</text>')
    return ''.join(parts)

add(f'<svg viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg" font-family="Inter, Arial, sans-serif">')
add(f'<rect x="0" y="0" width="{SVG_W}" height="{SVG_H}" fill="#ffffff"/>')

# ---- room outline ----
rx0, ry0 = room_x(0), room_y(0)
rx1, ry1 = room_x(ROOM_W), room_y(ROOM_D)
add(f'<rect x="{rx0}" y="{ry0}" width="{rx1-rx0}" height="{ry1-ry0}" fill="#fbfbfc" stroke="{INK}" stroke-width="3"/>')

# room dimension labels
add(f'<text x="{(rx0+rx1)/2}" y="{ry0-42}" text-anchor="middle" font-size="15" font-weight="800" fill="{INK}">Room width: 60\'-11 5/8" (confirmed)</text>')
add(f'<text x="{rx1+18}" y="{(ry0+ry1)/2}" transform="rotate(90 {rx1+18} {(ry0+ry1)/2})" text-anchor="middle" font-size="15" font-weight="800" fill="{INK}">Room depth: 21\'-11 1/2" (confirmed)</text>')
add(f'<text x="{(rx0+rx1)/2}" y="{ry0-20}" text-anchor="middle" font-size="12" fill="{DIM}">10\' ceiling &nbsp;•&nbsp; single blue roll-up door (in + out) &nbsp;•&nbsp; floor-stacked crates, no racking</text>')

# ---- entry spine (drawn EARLY, right after the room outline, so its opaque
# fill sits UNDER the notch/door/flag annotations that share this same
# x-range. Previously this was drawn near the end of the script, which
# silently painted over — and hid — the notch label and flag #1. ----
sx0, sy0 = room_x(0), room_y(0)
sx1, sy1 = room_x(g['SPINE_W_IN']), room_y(ROOM_D)
add(f'<rect x="{sx0}" y="{sy0}" width="{sx1-sx0}" height="{sy1-sy0}" fill="#fdfdfd" stroke="{LINE}" stroke-width="1" stroke-dasharray="4,3"/>')
add(f'<text x="{(sx0+sx1)/2}" y="{(sy0+sy1)/2}" transform="rotate(-90 {(sx0+sx1)/2} {(sy0+sy1)/2})" text-anchor="middle" font-size="11" font-weight="700" fill="{DIM}">entry spine — 60" (est.)</text>')

flags = []
def add_flag(x, y, n, text):
    flags.append((n, text))
    add(f'<circle cx="{x}" cy="{y}" r="11" fill="{ORANGE}"/>')
    add(f'<text x="{x}" y="{y+4}" text-anchor="middle" font-size="12" font-weight="800" fill="#fff">{n}</text>')

# ---- notch (bottom-left corner, per CAD sheet) ----
nx0, ny0 = room_x(0), room_y(ROOM_D - g['NOTCH_D_IN'])
nx1, ny1 = room_x(g['NOTCH_W_IN']), room_y(ROOM_D)
add(f'<rect x="{nx0}" y="{ny0}" width="{nx1-nx0}" height="{ny1-ny0}" fill="url(#hatch)" stroke="{ORANGE}" stroke-width="2" stroke-dasharray="6,4"/>')
add(text_lines((nx0+nx1)/2, (ny0+ny1)/2 - 6, ['98"x108"', 'notch'], anchor='middle', size=10.5, weight='700', fill=ORANGE, line_h=13))
add_flag(nx0+18, ny0+18, 1, '98"x108" notch, bottom-left corner — CAD sheet shows it here. You raised removing it for dunnage racks, but that was never confirmed done. If it\'s still there, M3 row loses its first ~6 positions of clearance — verify on site before stocking M3.')

# pattern def for notch hatch
add('<defs><pattern id="hatch" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#fff3ea"/><line x1="0" y1="0" x2="0" y2="8" stroke="#f0c4ab" stroke-width="3"/></pattern></defs>')

# ---- door (left wall, position estimated) ----
door_y0 = room_y(ROOM_D*0.32)
door_y1 = room_y(ROOM_D*0.32 + g['DOOR_W_IN'])
add(f'<rect x="{rx0-8}" y="{door_y0}" width="10" height="{door_y1-door_y0}" fill="{TEAL}"/>')
add(text_lines(rx0-16, (door_y0+door_y1)/2 - 6, ['DOOR', 'in / out'], anchor='end', size=12.5, weight='800', fill=TEAL, line_h=15))
add(text_lines(rx0-16, (door_y0+door_y1)/2 + 26, ['(exact position', 'estimated — #2)'], anchor='end', size=10.5, weight='400', fill=DIM, line_h=14))
add_flag(rx0-30, door_y0-14, 2, 'Door\'s exact position along this wall has never been field-measured — only that it\'s a blue roll-up door used for both entry and exit. Shown here at an estimated 1/3 of the way down the wall. Confirm before the entry spine (below) is framed in.')

# ---- rows + aisles (drawn BEFORE columns/drains so those flagged markers
# paint on top and stay visible, instead of being hidden under the opaque
# row/aisle fill rectangles) ----
row_x0, row_x1 = g['row_x0'], g['row_x1']
for entry in g['layout']:
    if 'row' in entry:
        r = entry['row']
        sec = g['row_section'][r]
        fill = BAKERY_FILL if sec == 'bakery' else MEALS_FILL
        stroke = TEAL if sec == 'bakery' else INK
        x0, y0 = room_x(row_x0), room_y(entry['y0'])
        x1, y1 = room_x(row_x1), room_y(entry['y1'])
        add(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        # position tick marks (every position, thin lines)
        pos_w = (x1-x0) / g['POSITIONS_PER_ROW']
        for p in range(1, g['POSITIONS_PER_ROW']):
            px = x0 + p*pos_w
            add(f'<line x1="{px}" y1="{y0}" x2="{px}" y2="{y1}" stroke="{stroke}" stroke-width="0.4" opacity="0.35"/>')
        # Row label sits INSIDE the row's own left edge, not to the left of
        # it — the space to the left is the narrow 60"-wide entry spine,
        # already carrying the spine label, door label, and flag #1/#2
        # circles, and six stacked row labels crammed in there on top of
        # that was unreadable. Positioned near the top of the row band
        # rather than dead-center, since the pathway arrow for K1 runs
        # straight through the row's vertical midline and would otherwise
        # strike through the label.
        add(f'<text x="{x0+8}" y="{y0+11}" text-anchor="start" font-size="12" font-weight="800" fill="{stroke}">{r}</text>')
    elif 'aisle' in entry:
        x0, y0 = room_x(row_x0), room_y(entry['y0'])
        x1, y1 = room_x(row_x1), room_y(entry['y1'])
        add(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#fdfdfd"/>')
        add(f'<text x="{(x0+x1)/2}" y="{(y0+y1)/2-4}" text-anchor="middle" font-size="11" font-weight="700" fill="{DIM}">{entry["aisle"]} — 48" wide (est.)</text>')
        add(f'<text x="{(x0+x1)/2}" y="{(y0+y1)/2+12}" text-anchor="middle" font-size="9.5" fill="{ORANGE}">needs field check — #5</text>')

add_flag(room_x(row_x0)+20, room_y(g['layout'][2]['y0'])+22, 5, 'All 3 aisle widths (48") are a planning placeholder, not a measured/tested clearance. The tote cart needs to physically pass and, ideally, turn around. Before building, push the actual cart through a taped-off 48" lane and confirm — narrow it only if the cart doesn\'t need two-way clearance there.')

# ---- estimated columns (drawn AFTER rows so the marker is visible, not
# painted over by the row/aisle fill) ----
col_r = X(6)  # ~12in diameter columns
for i in range(4):
    cx_in = ROOM_W * (0.30 + i*0.16)
    cy_in = ROOM_D * 0.5
    cx, cy = room_x(cx_in), room_y(cy_in)
    add(f'<circle cx="{cx}" cy="{cy}" r="{col_r}" fill="#fff" stroke="{ORANGE}" stroke-width="2.5"/>')
    add(f'<text x="{cx}" y="{cy+4}" text-anchor="middle" font-size="9" font-weight="800" fill="{ORANGE}">COL</text>')
add_flag(room_x(ROOM_W*0.30)-16, room_y(ROOM_D*0.5)-24, 3, 'Site photos show ~4 structural steel columns roughly along the room\'s centerline — positions here are an EVEN-SPACING ESTIMATE, not a survey. Nothing (racking, cart path, crate stack) can overlap the real position. Evaporator/fan units appear mounted near them — keep the top stack tier clear underneath for airflow.')

# ---- floor drains (approximate, also drawn after rows for visibility) ----
for i in range(3):
    dx_in = ROOM_W * (0.15 + i*0.35)
    dy_in = ROOM_D * 0.85
    dx, dy = room_x(dx_in), room_y(dy_in)
    add(f'<circle cx="{dx}" cy="{dy}" r="{X(4)}" fill="#fff" stroke="{DIM}" stroke-width="2" stroke-dasharray="3,2"/>')
add_flag(room_x(ROOM_W*0.15)-16, room_y(ROOM_D*0.85)+22, 4, 'Floor drain positions are approximate from site photos, not measured. Dunnage racks are assumed to let crates stack over them — confirm rack height clears the lowest crate opening.')

# ---- far-end clearance label (inside the room, between the last row and
# the room's right wall) ----
fx0 = room_x(row_x1)
fx1 = room_x(ROOM_W)
add(f'<text x="{(fx0+fx1)/2}" y="{room_y(ROOM_D/2)}" transform="rotate(-90 {(fx0+fx1)/2} {room_y(ROOM_D/2)})" text-anchor="middle" font-size="10.5" fill="{DIM}">{g["far_clearance"]:.0f}" spare — reserve pallets / overflow crates</text>')

# ---- pathway arrows ----
def arrow(points, color=TEAL):
    d = 'M ' + ' L '.join(f'{p[0]},{p[1]}' for p in points)
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="10,6" marker-end="url(#arrowhead)"/>')

add(f'''<defs><marker id="arrowhead" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto">
<polygon points="0 0, 10 4, 0 8" fill="{TEAL}"/></marker></defs>''')

door_mid_y = (door_y0+door_y1)/2
spine_mid_x = (sx0+sx1)/2
k1_mid_y = room_y((g['layout'][0]['y0']+g['layout'][0]['y1'])/2)
aisleA_mid_y = room_y((g['layout'][2]['y0']+g['layout'][2]['y1'])/2)
aisleB_mid_y = room_y((g['layout'][5]['y0']+g['layout'][5]['y1'])/2)
aisleC_mid_y = room_y((g['layout'][8]['y0']+g['layout'][8]['y1'])/2)
row_end_x = room_x(row_x1) - 14

arrow([(rx0, door_mid_y), (spine_mid_x, door_mid_y), (spine_mid_x, k1_mid_y)])
arrow([(spine_mid_x, k1_mid_y), (row_end_x, k1_mid_y)])
arrow([(row_end_x, k1_mid_y), (row_end_x, aisleA_mid_y), (spine_mid_x, aisleA_mid_y)])
arrow([(spine_mid_x, aisleA_mid_y), (row_end_x, aisleA_mid_y)])
arrow([(row_end_x, aisleA_mid_y), (row_end_x, aisleB_mid_y), (spine_mid_x, aisleB_mid_y)])
arrow([(spine_mid_x, aisleB_mid_y), (row_end_x, aisleB_mid_y)])
arrow([(row_end_x, aisleB_mid_y), (row_end_x, aisleC_mid_y), (spine_mid_x, aisleC_mid_y)])
arrow([(spine_mid_x, aisleC_mid_y), (row_end_x, aisleC_mid_y)], color=INK)
arrow([(row_end_x, aisleC_mid_y), (row_end_x, aisleC_mid_y+40), (spine_mid_x, aisleC_mid_y+40), (spine_mid_x, door_mid_y), (rx0, door_mid_y)], color=INK)

# Centered under the full room width (not the narrow entry spine) — this is
# a long line and was previously anchored at spine_mid_x, which pushed most
# of the text off past x=0 where the SVG viewport clipped it.
add(f'<text x="{(rx0+rx1)/2}" y="{ry1+34}" text-anchor="middle" font-size="11" font-weight="700" fill="{DIM}">Teal = Bakery &amp; Snacks leg (Aisle A → B, K1/K2/K3) · Dark = Meals leg (Aisle B → C, M1/M2/M3) · cart re-enters spine and exits same door</text>')

# ---- section labels — placed OUTSIDE the room's right wall (past rx1 +
# clear of the room-depth dimension label), not inside the far-clearance
# strip where they were previously overlapping both the room-depth label
# and the far-clearance label ----
label_x = rx1 + 60
bakery_y0 = room_y(g['layout'][0]['y0'])
bakery_y1 = room_y(g['layout'][3]['y1'])
meals_y0 = room_y(g['layout'][4]['y0'])
meals_y1 = room_y(g['layout'][7]['y1'])
add(f'<text x="{label_x}" y="{(bakery_y0+bakery_y1)/2}" text-anchor="start" font-size="13" font-weight="800" fill="{TEAL}">Bakery &amp; Snacks</text>')
add(f'<text x="{label_x}" y="{(bakery_y0+bakery_y1)/2+18}" text-anchor="start" font-size="10.5" fill="{DIM}">K1-K3 · 81 positions</text>')
add(f'<text x="{label_x}" y="{(bakery_y0+bakery_y1)/2+34}" text-anchor="start" font-size="10.5" fill="{DIM}">44 in use (real demand)</text>')
add(f'<text x="{label_x}" y="{(meals_y0+meals_y1)/2}" text-anchor="start" font-size="13" font-weight="800" fill="{INK}">Meals</text>')
add(f'<text x="{label_x}" y="{(meals_y0+meals_y1)/2+18}" text-anchor="start" font-size="10.5" fill="{DIM}">M1-M3 · 81 positions</text>')
add(f'<text x="{label_x}" y="{(meals_y0+meals_y1)/2+34}" text-anchor="start" font-size="10.5" fill="{DIM}">79 in use (real demand)</text>')

add('</svg>')

svg = '\n'.join(svg_parts)
open('/home/claude/hummusfit-warehouse/blueprint.svg', 'w').write(svg)
print('SVG written', len(svg), 'bytes')
print('SVG_W', SVG_W, 'SVG_H', SVG_H, 'label_x', label_x, 'rx1', rx1)
json.dump(flags, open('/home/claude/hummusfit-warehouse/blueprint_flags.json','w'))
