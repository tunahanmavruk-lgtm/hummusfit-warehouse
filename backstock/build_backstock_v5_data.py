"""
Backstock re-layout v5 -- the CONFIRMED (not mockup) data build.

Replaces the old A01-A04 / C01-C07 / D01-D02 zone codes and the old
demand-mixed multi-product-per-shelf packing with a 1:1 model: every
physical backstock position holds exactly ONE lane code, and that code
is the SAME code the main walk-in blueprint uses (M1/M2/M3 for meals,
K1/K2/K3 for bakery/oats/snacks). This is the entire point of the
relayout Tony asked for -- "coordinate this fridge to sync with smaller
fridge and the codes so its less confusing for pickers".

Confirmed by Tony (Aug 21, 2026):
  - Build exactly as mockup v4 showed: codes in their natural
    alphabetical/pipeline order, NOT the manual K2-05-first reshuffle
    he originally described. No physical section reordering applied.
  - M1-28 stays as Ground Beef (already correct on the live blueprint,
    no change needed).

Physical room geometry (bay counts/widths, depths) is carried over
UNCHANGED from the confirmed measurements in backstock_geometry.json --
only the CODE LABELING and shelf/floor COUNT per wall changes (Wall A
and Wall D now model 2 levels each, matching Tony's "2 shelves" / "2
floors" description, not the old 7-level demand-fill version; Center
now models 2 levels -- K1 floor 1, K2 floor 2 -- not the old 4).
"""
import json

g = json.load(open('/home/claude/hummusfit-warehouse/backstock/backstock_geometry.json'))
lp = json.load(open('/home/claude/hummusfit-warehouse/lane_plan.json'))
meals = {l['code']: l for l in lp['meals']['lanes']}
bakery = {l['code']: l for l in lp['bakery']['lanes']}

def codes(prefix, n, start=1):
    return [f"{prefix}-{i:02d}" for i in range(start, start + n)]

M1 = codes('M1', 28)   # Wall D
M2 = codes('M2', 28)   # Pallets
M3 = codes('M3', 27)   # Wall A
K1 = codes('K1', 35)   # Center floor 1
K2 = codes('K2', 30)   # Center floor 2

for c in M1 + M2 + M3:
    assert c in meals, f"missing {c} in lane_plan meals"
for c in K1 + K2:
    assert c in bakery, f"missing {c} in lane_plan bakery"

# ---------------------------------------------------------------------
# Physical geometry -- reuses confirmed real-world measurements from
# backstock_geometry.json (bay widths, depths, zone span). Only the
# level counts change (2 per wall/center instead of the old 7/7/4),
# matching what Tony actually confirmed in the mockup rounds.
# ---------------------------------------------------------------------
ZONE_W = g['zone_width_in']              # 384in (32ft) -- Wall A's confirmed span
WA_BAYS = 4
WA_LEVELS = 2
WA_DEPTH = g['wall_a_depth_in']          # 42in
WA_BAY_W = ZONE_W / WA_BAYS              # 96in/bay

WD_BAYS_OURS = 2
WD_LEVELS = 2
WD_DEPTH = g['wall_d_depth_in']          # 42in
WD_BAY_LEN = g['wall_d_bay_width_in']    # 96in
WD_TOTAL_LEN = WD_BAYS_OURS * WD_BAY_LEN  # 192in

C_BAYS = g['center_bays']                # 7
C_TOTAL_RUN = g['center_total_run_in']   # 378in
C_BAY_W = C_TOTAL_RUN / C_BAYS
C_DEPTH = 40
C_LEVELS = 2                             # K1 (floor 1), K2 (floor 2)

PALLET_COUNT = 8
PALLET_W = ZONE_W / PALLET_COUNT         # 48in, same span as Wall A
PALLET_FACE_DEPTH = 30                   # front + back = 60in total

AISLE_1 = 57
AISLE_2 = 57
# Z axis (room depth, door end = 0): Wall A -> aisle 1 -> pallets (front+back)
# -> aisle 2 -> Center (front=ours, back=kitchen's)
Z_WALLA = 0
Z_PALLET_FRONT = WA_DEPTH + AISLE_1
Z_PALLET_BACK = Z_PALLET_FRONT + PALLET_FACE_DEPTH
Z_CENTER = Z_PALLET_BACK + PALLET_FACE_DEPTH + AISLE_2

X_OFFSET = 40 + WD_DEPTH   # gap-to-Wall-D clearance + Wall D's own depth
LEVEL_H_WALL = 70          # in, Wall A/D shelf pitch (2 levels)
LEVEL_H_CENTER = 70        # in, Center floor pitch (2 levels)

GEOMETRY = {
    'zone_w': ZONE_W, 'x_offset': X_OFFSET,
    'wallA': {'bays': WA_BAYS, 'levels': WA_LEVELS, 'depth': WA_DEPTH, 'bay_w': WA_BAY_W, 'z0': Z_WALLA, 'level_h': LEVEL_H_WALL},
    'wallD': {'bays': WD_BAYS_OURS, 'levels': WD_LEVELS, 'depth': WD_DEPTH, 'bay_len': WD_BAY_LEN, 'total_len': WD_TOTAL_LEN, 'level_h': LEVEL_H_WALL},
    'pallets': {'count': PALLET_COUNT, 'w': PALLET_W, 'face_depth': PALLET_FACE_DEPTH, 'z_front': Z_PALLET_FRONT, 'z_back': Z_PALLET_BACK},
    'center': {'bays': C_BAYS, 'bay_w': C_BAY_W, 'depth': C_DEPTH, 'total_run': C_TOTAL_RUN, 'z0': Z_CENTER, 'level_h': LEVEL_H_CENTER},
    'aisle_1': AISLE_1, 'aisle_2': AISLE_2,
    'room_w': ZONE_W + X_OFFSET,
    'room_d': Z_CENTER + C_DEPTH * 2 + 40,
}

# ---------------------------------------------------------------------
# Position list -- one entry per physical slot. Every real lane code
# gets exactly one slot; Wall D has 4 unused slots (32 physical - 28
# real M1 codes) shown as empty.
# ---------------------------------------------------------------------
def chunk_even(items, n_blocks):
    L = len(items); base = L // n_blocks; rem = L % n_blocks
    out = []; idx = 0
    for b in range(n_blocks):
        size = base + (1 if b < rem else 0)
        out.append(items[idx:idx + size]); idx += size
    return out

positions = {}

# --- Wall D: 2 floors x 16 slots (2 cols x 8 rows), M1 codes ---
wd_floor1 = M1[0:15]     # M1-01..15
wd_floor2 = M1[15:28]    # M1-16..28
for floor_idx, floor_codes in enumerate([wd_floor1, wd_floor2]):
    slots = floor_codes + [None] * (16 - len(floor_codes))
    for i, code in enumerate(slots):
        col = i // 8
        row = i % 8
        x = col * (WD_DEPTH / 2)
        z = row * (WD_TOTAL_LEN / 8)
        entry = {
            'zone': 'walld', 'floor': floor_idx + 1, 'x': x, 'z': z,
            'w': WD_DEPTH / 2, 'd': WD_TOTAL_LEN / 8, 'level_h': LEVEL_H_WALL,
            'level': floor_idx + 1,
        }
        if code:
            lane = meals[code]
            entry.update(code=code, cat=lane['category'], product=lane['product'],
                         cap=lane['cap'], crates=lane['crates_needed'])
        else:
            entry.update(code=None, cat=None, product=None, cap=0, crates=0)
        positions[code or f'WD-empty-{floor_idx}-{i}'] = entry

# --- Wall A: 2 shelves, M3 codes, individually spaced across the 384in span ---
wa_shelf1 = M3[0:15]   # M3-01..15 (bottom)
wa_shelf2 = M3[15:27]  # M3-16..27 (top)
for shelf_idx, shelf_codes in enumerate([wa_shelf1, wa_shelf2]):
    n = len(shelf_codes)
    slot_w = ZONE_W / n
    for i, code in enumerate(shelf_codes):
        lane = meals[code]
        positions[code] = {
            'zone': 'walla', 'floor': shelf_idx + 1, 'x': i * slot_w, 'z': Z_WALLA,
            'w': slot_w, 'd': WA_DEPTH, 'level_h': LEVEL_H_WALL, 'level': shelf_idx + 1,
            'code': code, 'cat': lane['category'], 'product': lane['product'],
            'cap': lane['cap'], 'crates': lane['crates_needed'],
        }

# --- Pallets: 8 pallets, double-sided, M2 codes ---
pallet_front = chunk_even(M2[0:15], 8)   # M2-01..15 across 8 pallet fronts
pallet_back = chunk_even(M2[15:28], 8)   # M2-16..28 across 8 pallet backs
for p in range(PALLET_COUNT):
    front_codes = pallet_front[p]
    n_f = len(front_codes)
    for i, code in enumerate(front_codes):
        lane = meals[code]
        positions[code] = {
            'zone': 'pallet', 'face': 'front', 'pallet': p + 1,
            'x': p * PALLET_W + i * (PALLET_W / n_f), 'z': Z_PALLET_FRONT,
            'w': PALLET_W / n_f, 'd': PALLET_FACE_DEPTH, 'level_h': PALLET_FACE_DEPTH, 'level': 1,
            'code': code, 'cat': lane['category'], 'product': lane['product'],
            'cap': lane['cap'], 'crates': lane['crates_needed'],
        }
    back_codes = pallet_back[p]
    n_b = len(back_codes)
    for i, code in enumerate(back_codes):
        lane = meals[code]
        positions[code] = {
            'zone': 'pallet', 'face': 'back', 'pallet': p + 1,
            'x': p * PALLET_W + i * (PALLET_W / n_b), 'z': Z_PALLET_BACK,
            'w': PALLET_W / n_b, 'd': PALLET_FACE_DEPTH, 'level_h': PALLET_FACE_DEPTH, 'level': 1,
            'code': code, 'cat': lane['category'], 'product': lane['product'],
            'cap': lane['cap'], 'crates': lane['crates_needed'],
        }

# --- Center: K1 floor 1 (7 x 5, exact), K2 floor 2 (7 sections, 5,5,4,4,4,4,4) ---
k1_blocks = [K1[i * 5:(i + 1) * 5] for i in range(7)]
k2_sizes = [5, 5, 4, 4, 4, 4, 4]
k2_blocks = []
idx = 0
for s in k2_sizes:
    k2_blocks.append(K2[idx:idx + s]); idx += s

for floor_idx, blocks in enumerate([k1_blocks, k2_blocks]):
    for bay_idx, block_codes in enumerate(blocks):
        n = len(block_codes)
        slot_w = C_BAY_W / n
        for i, code in enumerate(block_codes):
            lane = bakery[code]
            positions[code] = {
                'zone': 'center', 'floor': floor_idx + 1, 'bay': bay_idx + 1,
                'x': bay_idx * C_BAY_W + i * slot_w, 'z': Z_CENTER,
                'w': slot_w, 'd': C_DEPTH, 'level_h': LEVEL_H_CENTER, 'level': floor_idx + 1,
                'code': code, 'cat': lane['category'], 'product': lane['product'],
                'cap': lane['cap'], 'crates': lane['crates_needed'],
            }

real_positions = {k: v for k, v in positions.items() if v.get('code')}
print(f"Total positions: {len(positions)} ({len(real_positions)} real codes, "
      f"{len(positions) - len(real_positions)} empty Wall D slots)")

json.dump(GEOMETRY, open('/home/claude/hummusfit-warehouse/backstock/backstock_geometry_v5.json', 'w'), indent=2)
json.dump(positions, open('/home/claude/hummusfit-warehouse/backstock/position_fill_v5.json', 'w'), indent=2)
print("Written backstock_geometry_v5.json and position_fill_v5.json")
