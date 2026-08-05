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

# Tag-strip block: a per-row ruler of product labels, added BELOW the main
# room drawing, appended to overall height. Every column in a strip lines
# up horizontally with that same row's position ticks above (same x0/x1/
# pos_w), so "count to the 7th line" and "read the label under the 7th
# line" are the same physical column — no separate legend lookup needed to
# know what a given crate position holds.
ROW_CODES = [entry['row'] for entry in g['layout'] if 'row' in entry]
STRIP_HEAD_H = 24
STRIP_H = 150
STRIP_GAP = 22
STRIP_BLOCK_TOP_PAD = 54
STRIP_BLOCK_H = STRIP_BLOCK_TOP_PAD + len(ROW_CODES) * (STRIP_HEAD_H + STRIP_H + STRIP_GAP)

SVG_H = Y(ROOM_D) + MARGIN*2 + 60 + STRIP_BLOCK_H

TEAL = '#2BBFAA'
ORANGE = '#E8612C'
INK = '#111417'
DIM = '#767c85'
LINE = '#dfe3e8'
BAKERY_FILL = '#eafaf7'
MEALS_FILL = '#eef0f4'
FLAG_BG = '#fff3ea'

# lane code -> lane_plan record, for the position-tick numbering
lane_by_code = {}
for sec in lane_plan.values():
    for l in sec['lanes']:
        lane_by_code[l['code']] = l

svg_parts = []
def add(s): svg_parts.append(s)

def room_x(v): return MARGIN + X(v)
def room_y(v): return MARGIN + Y(v)

def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))

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
add(f'<text x="{(rx0+rx1)/2}" y="{ry0-20}" text-anchor="middle" font-size="12" fill="{DIM}">10\' ceiling &nbsp;•&nbsp; single blue roll-up door (in + out) &nbsp;•&nbsp; floor-stacked crates, no racking &nbsp;•&nbsp; notch confirmed NOT present on site (removed from this drawing)</text>')

# ---- entry spine (drawn EARLY, right after the room outline, so its opaque
# fill sits UNDER the door/flag annotations that share this same x-range) ----
sx0, sy0 = room_x(0), room_y(0)
sx1, sy1 = room_x(g['SPINE_W_IN']), room_y(ROOM_D)
add(f'<rect x="{sx0}" y="{sy0}" width="{sx1-sx0}" height="{sy1-sy0}" fill="#fdfdfd" stroke="{LINE}" stroke-width="1" stroke-dasharray="4,3"/>')
add(f'<text x="{(sx0+sx1)/2}" y="{(sy0+sy1)/2}" transform="rotate(-90 {(sx0+sx1)/2} {(sy0+sy1)/2})" text-anchor="middle" font-size="11" font-weight="700" fill="{DIM}">entry spine — 60"</text>')

# ---- NOTE: the 98"x108" notch from the original CAD sheet has been
# confirmed as NOT physically present in the room and is intentionally
# omitted from this drawing. It's still on file (blueprint_geometry.json)
# in case that ever needs re-checking, but nothing here draws it. ----

# ---- door (left wall, position estimated) ----
door_y0 = room_y(ROOM_D*0.32)
door_y1 = room_y(ROOM_D*0.32 + g['DOOR_W_IN'])
add(f'<rect x="{rx0-8}" y="{door_y0}" width="10" height="{door_y1-door_y0}" fill="{TEAL}"/>')
add(text_lines(rx0-16, (door_y0+door_y1)/2 - 6, ['DOOR', 'in / out'], anchor='end', size=12.5, weight='800', fill=TEAL, line_h=15))

# ---- rows + aisles (drawn BEFORE columns/drains so those flagged markers
# paint on top and stay visible, instead of being hidden under the opaque
# row/aisle fill rectangles). Position tick numbers are added so every lane
# on the floor cross-references directly to the product legend table below
# the drawing (e.g. "K1-07" here = row K1, 7th tick from the left = the same
# K1-07 row in the legend table). ----
row_x0, row_x1 = g['row_x0'], g['row_x1']
POS_BY_SECTION = g['positions_per_row_by_section']  # bakery rows now hold more, narrower positions than meals rows
row_geom = {}  # row code -> (x0, x1, pos_w, stroke) for the tag-strip block below
for entry in g['layout']:
    if 'row' in entry:
        r = entry['row']
        sec = g['row_section'][r]
        POSITIONS_PER_ROW = POS_BY_SECTION[sec]
        fill = BAKERY_FILL if sec == 'bakery' else MEALS_FILL
        stroke = TEAL if sec == 'bakery' else INK
        x0, y0 = room_x(row_x0), room_y(entry['y0'])
        x1, y1 = room_x(row_x1), room_y(entry['y1'])
        add(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        pos_w = (x1-x0) / POSITIONS_PER_ROW
        row_geom[r] = (x0, x1, pos_w, stroke)
        for p in range(1, POSITIONS_PER_ROW):
            px = x0 + p*pos_w
            add(f'<line x1="{px}" y1="{y0}" x2="{px}" y2="{y1}" stroke="{stroke}" stroke-width="0.4" opacity="0.35"/>')
        # position numbers + an occupied/empty dot so the drawing shows, at a
        # glance, which slots per row are actually assigned a product (vs.
        # open floor space) without needing the legend table. Each dot also
        # carries a native SVG tooltip (hover, on-screen only) and lines up
        # exactly with its product tag in the strip below.
        for p in range(1, POSITIONS_PER_ROW+1):
            cx = x0 + (p-0.5)*pos_w
            code = f'{r}-{p:02d}'
            lane = lane_by_code.get(code)
            occupied = lane is not None
            dot_fill = stroke if occupied else '#fff'
            tip = esc(f'{code} — {lane["product"]}') if lane else f'{code} — empty'
            add(f'<circle cx="{cx}" cy="{y1-6}" r="2.2" fill="{dot_fill}" stroke="{stroke}" stroke-width="0.6"><title>{tip}</title></circle>')
            if pos_w > 20:  # only label numbers when there's room to read them
                add(f'<text x="{cx}" y="{y0+9}" text-anchor="middle" font-size="6" fill="{stroke}" opacity="0.8">{p}</text>')
        # Row label sits INSIDE the row's own left edge, not to the left of
        # it — the space to the left is the narrow 60"-wide entry spine,
        # already carrying the spine label, door label, and flag #1 circle.
        # Positioned near the top of the row band rather than dead-center,
        # since the pathway arrow for aisle A runs along the row's
        # vertical midline in the general vicinity and would otherwise
        # strike through the label.
        add(f'<text x="{x0+8}" y="{y0+11}" text-anchor="start" font-size="12" font-weight="800" fill="{stroke}">{r}</text>')
    elif 'aisle' in entry:
        x0, y0 = room_x(row_x0), room_y(entry['y0'])
        x1, y1 = room_x(row_x1), room_y(entry['y1'])
        add(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#fdfdfd"/>')
        # Moved from dead-center to the top-left corner of the aisle band --
        # dead-center is where the zone-transition pathway arrows and the
        # row-direction labels for the row below this aisle both land, and
        # collided with this label there.
        add(f'<text x="{x0+8}" y="{y0+11}" text-anchor="start" font-size="11" font-weight="700" fill="{DIM}">{entry["aisle"]}</text>')

# ---- columns (drawn AFTER rows so the marker is visible, not painted over
# by the row/aisle fill) ----
col_r = X(6)  # ~12in diameter columns
for i in range(4):
    cx_in = ROOM_W * (0.30 + i*0.16)
    cy_in = ROOM_D * 0.5
    cx, cy = room_x(cx_in), room_y(cy_in)
    add(f'<circle cx="{cx}" cy="{cy}" r="{col_r}" fill="#fff" stroke="{ORANGE}" stroke-width="2.5"/>')
    add(f'<text x="{cx}" y="{cy+4}" text-anchor="middle" font-size="9" font-weight="800" fill="{ORANGE}">COL</text>')

# ---- floor drains (also drawn after rows for visibility) ----
for i in range(3):
    dx_in = ROOM_W * (0.15 + i*0.35)
    dy_in = ROOM_D * 0.85
    dx, dy = room_x(dx_in), room_y(dy_in)
    add(f'<circle cx="{dx}" cy="{dy}" r="{X(4)}" fill="#fff" stroke="{DIM}" stroke-width="2" stroke-dasharray="3,2"/>')

# ---- far-end clearance label (inside the room, between the last row and
# the room's right wall) ----
fx0 = room_x(row_x1)
fx1 = room_x(ROOM_W)
add(f'<text x="{(fx0+fx1)/2}" y="{room_y(ROOM_D/2)}" transform="rotate(-90 {(fx0+fx1)/2} {room_y(ROOM_D/2)})" text-anchor="middle" font-size="10.5" fill="{DIM}">{g["far_clearance"]:.0f}" spare — reserve pallets / overflow crates</text>')

# ---- pathway arrows — real confirmed walk order (Aug 2026 correction from
# Tony): NOT a single loop through each aisle once. The picker actually
# zigzags row by row -- row 1 of a zone ascending (low position -> high),
# row 2 descending (high back to low), row 3 ascending again -- and that
# alternation RESETS to ascending at the start of each new zone rather than
# continuing across the zone boundary. Meals (M1-M3) is walked first,
# bakery (K1-K3) second.
#
# Physically, each aisle sits between exactly two rows (Aisle A: K1/K2,
# Aisle B: K3/M1, Aisle C: M2/M3), so a row that isn't the first or last in
# its zone shares its aisle with the row before or after it in the order --
# the confirmed direction pattern is exactly consistent with that: the
# picker walks the shared aisle, turns around at the end, and walks back
# for the paired row (M2 desc immediately followed by M3 asc back through
# Aisle C; K1 asc immediately followed by K2 desc back through Aisle A).
#
# Each row's own arrow is drawn along THAT row's centerline (not just the
# adjacent aisle's), per Tony's request that "each row's arrowhead points
# in its actual walked direction" -- turns between rows still route through
# an aisle or margin, never straight across a different crate row, so nothing
# here draws a path on top of crates that aren't the ones being picked.
def arrow(points, color=TEAL):
    d = 'M ' + ' L '.join(f'{p[0]},{p[1]}' for p in points)
    marker = 'arrowhead-teal' if color == TEAL else 'arrowhead-ink'
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="10,6" marker-end="url(#{marker})"/>')

add(f'''<defs>
<marker id="arrowhead-teal" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto"><polygon points="0 0, 10 4, 0 8" fill="{TEAL}"/></marker>
<marker id="arrowhead-ink" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto"><polygon points="0 0, 10 4, 0 8" fill="{INK}"/></marker>
</defs>''')

door_mid_y = (door_y0+door_y1)/2
spine_mid_x = (sx0+sx1)/2
aisleA_mid_y = room_y((g['layout'][2]['y0']+g['layout'][2]['y1'])/2)
aisleB_mid_y = room_y((g['layout'][5]['y0']+g['layout'][5]['y1'])/2)
aisleC_mid_y = room_y((g['layout'][8]['y0']+g['layout'][8]['y1'])/2)
row_end_x = room_x(row_x1) - 14

# Each row's own crate band is only ~24px tall in this drawing (already
# packed with position-number ticks near the top and occupied/empty dots
# near the bottom) -- nowhere near enough room for a direction arrow AND a
# readable label. Each aisle band, by contrast, is ~74px tall and serves
# exactly two rows (Aisle A: K1 above / K2 below, Aisle B: K3 above / M1
# below, Aisle C: M2 above / M3 below). So each row's arrow is drawn inside
# its ADJACENT aisle, offset toward whichever side that row is actually on
# (near the top of the aisle for the row above, near the bottom for the row
# below) -- close enough to read as "this row's arrow," with an explicit
# text label next to it so there's no ambiguity about which row it's for.
aisleA_y0, aisleA_y1 = room_y(g['layout'][2]['y0']), room_y(g['layout'][2]['y1'])
aisleB_y0, aisleB_y1 = room_y(g['layout'][5]['y0']), room_y(g['layout'][5]['y1'])
aisleC_y0, aisleC_y1 = room_y(g['layout'][8]['y0']), room_y(g['layout'][8]['y1'])
NEAR, FAR = 0.30, 0.70  # fraction down the aisle band: near the top row vs. the bottom row

K1_y = aisleA_y0 + (aisleA_y1-aisleA_y0)*NEAR   # K1 is above Aisle A
K2_y = aisleA_y0 + (aisleA_y1-aisleA_y0)*FAR    # K2 is below Aisle A
K3_y = aisleB_y0 + (aisleB_y1-aisleB_y0)*NEAR   # K3 is above Aisle B
M1_y = aisleB_y0 + (aisleB_y1-aisleB_y0)*FAR    # M1 is below Aisle B
M2_y = aisleC_y0 + (aisleC_y1-aisleC_y0)*NEAR   # M2 is above Aisle C
M3_y = aisleC_y0 + (aisleC_y1-aisleC_y0)*FAR    # M3 is below Aisle C

def row_label(text, x, y, color):
    add(f'<text x="{x}" y="{y-6}" text-anchor="middle" font-size="10.5" font-weight="800" fill="{color}">{text}</text>')

mid_x = (spine_mid_x + row_end_x) / 2

# ---- Meals zone first (dark/INK), reset to ascending ----
# Enter door -> spine down to M1's level -> M1 ascending (1 -> 27)
arrow([(rx0, door_mid_y), (spine_mid_x, door_mid_y), (spine_mid_x, M1_y), (row_end_x, M1_y)], color=INK)
row_label('M1 →', mid_x, M1_y, INK)
# M1 ends at the far end -> M2 descending (27 -> 1), immediate return pass
arrow([(row_end_x, M1_y), (row_end_x, M2_y), (spine_mid_x, M2_y)], color=INK)
row_label('M2 ←', mid_x, M2_y, INK)
# M2 ends at the spine -> M3 ascending (1 -> 27), immediate return pass
arrow([(spine_mid_x, M2_y), (spine_mid_x, M3_y), (row_end_x, M3_y)], color=INK)
row_label('M3 →', mid_x, M3_y, INK)

# ---- Zone transition: meals done, reset to ascending for bakery ----
# From M3's end, up the far-end margin, left through Aisle A (a clear
# walkway, not a crate row) to the spine, then up to K1's level -- gets us
# from the far end of the room back to K1's start (position 1) without ever
# crossing a row that isn't the one currently being picked.
# The horizontal jog is offset 16px above the aisle's dead-center so it
# doesn't run straight through the pre-existing "Aisle A/B" label text,
# which sits exactly at that center point.
aisleA_trans_y = aisleA_mid_y - 16
arrow([(row_end_x, M3_y), (row_end_x, aisleA_trans_y), (spine_mid_x, aisleA_trans_y), (spine_mid_x, K1_y), (row_end_x, K1_y)], color=TEAL)
row_label('K1 →', mid_x, K1_y, TEAL)

# ---- Bakery zone second (teal), same reset-to-ascending pattern ----
# K1 ends at the far end -> K2 descending (35 -> 1), immediate return pass
arrow([(row_end_x, K1_y), (row_end_x, K2_y), (spine_mid_x, K2_y)], color=TEAL)
row_label('K2 ←', mid_x, K2_y, TEAL)
# K2 ends at the spine -> K3 ascending, immediate return pass
arrow([(spine_mid_x, K2_y), (spine_mid_x, K3_y), (row_end_x, K3_y)], color=TEAL)
row_label('K3 →', mid_x, K3_y, TEAL)

# Exit: from K3's end, down through Aisle B (clear walkway) to the spine,
# then up the spine and out the same door. Same 16px offset as the meals
# -> bakery transition, so this jog also clears the "Aisle B" label text.
aisleB_trans_y = aisleB_mid_y - 16
arrow([(row_end_x, K3_y), (row_end_x, aisleB_trans_y), (spine_mid_x, aisleB_trans_y), (spine_mid_x, door_mid_y), (rx0, door_mid_y)], color=TEAL)

# Centered under the full room width (not the narrow entry spine) — a long
# line anchored at the spine's midpoint previously ran off past x=0 where
# the SVG viewport clipped it.
add(f'<text x="{(rx0+rx1)/2}" y="{ry1+34}" text-anchor="middle" font-size="11" font-weight="700" fill="{DIM}">Zigzag path — each row walked its own direction (ascending →, descending ←), resetting to ascending at the start of each new zone &nbsp;•&nbsp; Dark = Meals leg, walked first (M1 → M2 → M3) &nbsp;•&nbsp; Teal = Bakery leg, walked second (K1 → K2 → K3) &nbsp;•&nbsp; cart exits the same door</text>')

# ---- section labels — placed OUTSIDE the room's right wall ----
label_x = rx1 + 60
bakery_y0 = room_y(g['layout'][0]['y0'])
bakery_y1 = room_y(g['layout'][3]['y1'])
meals_y0 = room_y(g['layout'][4]['y0'])
meals_y1 = room_y(g['layout'][7]['y1'])
bakery_used = len(lane_plan['bakery']['lanes'])
bakery_total = lane_plan['bakery']['total_positions']
meals_used = len(lane_plan['meals']['lanes'])
meals_total = lane_plan['meals']['total_positions']
add(f'<text x="{label_x}" y="{(bakery_y0+bakery_y1)/2}" text-anchor="start" font-size="13" font-weight="800" fill="{TEAL}">Bakery &amp; Snacks</text>')
add(f'<text x="{label_x}" y="{(bakery_y0+bakery_y1)/2+18}" text-anchor="start" font-size="10.5" fill="{DIM}">K1-K3 · {bakery_total} positions</text>')
add(f'<text x="{label_x}" y="{(bakery_y0+bakery_y1)/2+34}" text-anchor="start" font-size="10.5" fill="{DIM}">{bakery_used}/{bakery_total} in use — Muffins zone (K1-K2ish) + Oats &amp; Snacks zone</text>')
add(f'<text x="{label_x}" y="{(meals_y0+meals_y1)/2}" text-anchor="start" font-size="13" font-weight="800" fill="{INK}">Meals</text>')
add(f'<text x="{label_x}" y="{(meals_y0+meals_y1)/2+18}" text-anchor="start" font-size="10.5" fill="{DIM}">M1-M3 · {meals_total} positions</text>')
add(f'<text x="{label_x}" y="{(meals_y0+meals_y1)/2+34}" text-anchor="start" font-size="10.5" fill="{DIM}">{meals_used}/{meals_total} in use — alphabetical, one zone</text>')

# ---- product tag strip block — the direct fix for "what crate is exactly
# what product": one ruler per row, positioned below the main drawing,
# whose 27 columns line up exactly (same x0/x1/pos_w) with that row's
# ticks above. No click, no separate legend needed to read a position. ----
def short_name(name):
    import re as _re
    s = _re.sub(r'^(Buffin Muffin|Overnight Oats|Buff Crisp Bar)\s*-\s*', '', name)
    return s if len(s) <= 30 else s[:28] + '…'

strip_top = ry1 + STRIP_BLOCK_TOP_PAD
add(f'<text x="{rx0}" y="{strip_top-30}" text-anchor="start" font-size="15" font-weight="800" fill="{INK}">Shelf Tag Strip — every position, aligned directly under its tick above</text>')
add(f'<text x="{rx0}" y="{strip_top-12}" text-anchor="start" font-size="11" fill="{DIM}">Column 7 in a strip = tick 7 in that row\'s diagram above = the same physical crate position. No lookup required.</text>')

sy = strip_top
for r in ROW_CODES:
    x0, x1, pos_w, stroke = row_geom[r]
    sec = g['row_section'][r]
    POSITIONS_PER_ROW = POS_BY_SECTION[sec]
    fill = BAKERY_FILL if sec == 'bakery' else MEALS_FILL
    add(f'<text x="{x0}" y="{sy+STRIP_HEAD_H-8}" text-anchor="start" font-size="12" font-weight="800" fill="{stroke}">Row {r}</text>')
    strip_y0 = sy + STRIP_HEAD_H
    strip_y1 = strip_y0 + STRIP_H
    add(f'<rect x="{x0}" y="{strip_y0}" width="{x1-x0}" height="{STRIP_H}" fill="{fill}" stroke="{LINE}" stroke-width="1"/>')
    for p in range(1, POSITIONS_PER_ROW+1):
        code = f'{r}-{p:02d}'
        lane = lane_by_code.get(code)
        cx = x0 + (p-0.5)*pos_w
        add(f'<line x1="{cx}" y1="{strip_y0}" x2="{cx}" y2="{strip_y1}" stroke="{stroke}" stroke-width="0.4" opacity="0.25"/>')
        if lane:
            color = {'muffin': TEAL, 'oats': '#4C9BE8', 'snack': ORANGE, 'meal': INK}.get(lane['category'], stroke)
            flag = ' ~' if lane.get('divergence_flag') else ''
            label = esc(f'{p}. {short_name(lane["product"])}{flag}')
            ty = strip_y0 + 8
            add(f'<text x="{cx+4}" y="{ty}" transform="rotate(90 {cx+4} {ty})" text-anchor="start" font-size="7.4" font-weight="700" fill="{color}"><title>{esc(code + chr(45) + chr(45) + lane["product"])}</title>{label}</text>')
        else:
            ty = strip_y0 + 8
            add(f'<text x="{cx+4}" y="{ty}" transform="rotate(90 {cx+4} {ty})" text-anchor="start" font-size="7" fill="{DIM}" opacity="0.55">{p}. empty</text>')
    sy = strip_y1 + STRIP_GAP

add('</svg>')

svg = '\n'.join(svg_parts)
open('/home/claude/hummusfit-warehouse/blueprint.svg', 'w').write(svg)
print('SVG written', len(svg), 'bytes')
print('SVG_W', SVG_W, 'SVG_H', SVG_H, 'label_x', label_x, 'rx1', rx1)
