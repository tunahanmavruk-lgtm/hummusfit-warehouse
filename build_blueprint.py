"""
Generates a single to-scale, birds-eye SVG blueprint of the walk-in room:
room outline, door, columns, drains, notch, all 6 lane rows, aisles, and a
picker pathway — plus a numbered flaws/assumptions list so every unconfirmed
element is visible on the same page, not buried in prose.
"""
import json

# ---------- confirmed physical facts ----------
ROOM_W_IN = 60*12 + 11 + 5/8      # 60'-11 5/8"
ROOM_D_IN = 21*12 + 11 + 0.5      # 21'-11 1/2"
CEILING_IN = 10*12
DOOR_W_IN = 120                    # typical roll-up door, EXACT width/position unconfirmed
NOTCH_W_IN, NOTCH_D_IN = 98, 108   # bottom-left corner, per CAD sheet
CRATE_W, CRATE_D, CRATE_H = 21.65, 15.70, 10.70
POSITIONS_PER_ROW = 27
MAX_STACK = 5

# ---------- layout geometry (this is the design being proposed) ----------
SPINE_W_IN = 60                    # entry corridor along the door wall, two-way
AISLE_W_IN = 48                    # width of each of the 3 working aisles (NEEDS FIELD CHECK)
ROW_DEPTH_IN = CRATE_D             # crates single-file, full pick face exposed to the aisle

rows = ['K1', 'K2', 'K3', 'M1', 'M2', 'M3']
row_section = {'K1':'bakery','K2':'bakery','K3':'bakery','M1':'meals','M2':'meals','M3':'meals'}

# y-position (depth from the door wall, y=0) of each row band and its facing aisle
# Pairing: (K1,K2) face Aisle A, (K3,M1) face Aisle B, (M2,M3) face Aisle C
layout = []
y = 0
pairs = [('K1','K2'), ('K3','M1'), ('M2','M3')]
aisle_names = ['Aisle A', 'Aisle B', 'Aisle C']
for (r1, r2), aname in zip(pairs, aisle_names):
    layout.append({'row': r1, 'y0': y, 'y1': y+ROW_DEPTH_IN})
    y += ROW_DEPTH_IN
    aisle_y0 = y
    y += AISLE_W_IN
    layout.append({'row': r2, 'y0': y, 'y1': y+ROW_DEPTH_IN})
    y += ROW_DEPTH_IN
    layout.append({'aisle': aname, 'y0': aisle_y0, 'y1': aisle_y0+AISLE_W_IN, 'between': (r1, r2)})
end_clearance = ROOM_D_IN - y

row_x0 = SPINE_W_IN
row_len = POSITIONS_PER_ROW * CRATE_W
row_x1 = row_x0 + row_len
far_clearance = ROOM_W_IN - row_x1

print(f"Room: {ROOM_W_IN}in x {ROOM_D_IN}in, ceiling {CEILING_IN}in")
print(f"Row length used: {row_len:.1f}in of {ROOM_W_IN:.1f}in width (far clearance {far_clearance:.1f}in)")
print(f"Depth used: {y:.1f}in of {ROOM_D_IN:.1f}in (end clearance {end_clearance:.1f}in)")
for l in layout:
    print(l)

json.dump({
    'ROOM_W_IN': ROOM_W_IN, 'ROOM_D_IN': ROOM_D_IN, 'CEILING_IN': CEILING_IN,
    'DOOR_W_IN': DOOR_W_IN, 'NOTCH_W_IN': NOTCH_W_IN, 'NOTCH_D_IN': NOTCH_D_IN,
    'SPINE_W_IN': SPINE_W_IN, 'AISLE_W_IN': AISLE_W_IN, 'ROW_DEPTH_IN': ROW_DEPTH_IN,
    'row_x0': row_x0, 'row_x1': row_x1, 'row_len': row_len, 'far_clearance': far_clearance,
    'end_clearance': end_clearance, 'layout': layout, 'row_section': row_section,
    'POSITIONS_PER_ROW': POSITIONS_PER_ROW, 'CRATE_W': CRATE_W, 'CRATE_D': CRATE_D, 'CRATE_H': CRATE_H,
    'MAX_STACK': MAX_STACK,
}, open('/home/claude/hummusfit-warehouse/blueprint_geometry.json', 'w'), indent=2)
