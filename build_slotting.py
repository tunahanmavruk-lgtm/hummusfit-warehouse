"""
Builds lane_plan.json: which product goes in which physical lane, and how
many crates it gets.

REWRITTEN per direct feedback: this walk-in is for daily operational
picking only — backstock lives in a separate part of the building. The
previous version gave high-velocity products extra "backstock" lanes out
of whatever floor space was left in a zone, which packed the room full
but meant a picker saw the same product name repeated 2-4 times across
different shelves with no explanation. That's confusing, not efficient.

Current rules:
  - Every product gets exactly ONE lane. Only exception: its daily need
    (with buffer) physically doesn't fit in one lane's max stack — then,
    and only then, it gets the minimum extra lanes required to hold that
    day's volume, split evenly across them. That's a capacity fact, not
    a backstock decision.
  - Crates per lane = today's real daily demand (from Shopify) plus a
    15% cushion, not a full extra day of stock. Enough to not run dry
    mid-shift, not enough to be backstock.
  - Every product line still gets its own contiguous, alphabetically
    ordered zone (muffins together, oats+snacks together, meals on
    their own rows) — that part of the design didn't change.
  - Positions a zone doesn't need stay empty. No filling for the sake of
    filling — an empty position is floor space you didn't need to use,
    not a problem to solve.
"""
import json, math, re

products = json.load(open('/home/claude/hummusfit-warehouse/products.json'))
demand = json.load(open('/home/claude/hummusfit-warehouse/products_demand_shopify.json'))

def cap_for(p):
    if p['cat'] == 'meal': return 24
    if p['cat'] == 'muffin': return 24
    if p['cat'] == 'oats': return 28
    if p['cat'] == 'snack':
        if re.search(r'gree-yo|pudding', p['name'], re.I): return 28
        if re.search(r'buff crisp bar', p['name'], re.I): return 48
        return 24
    return 24

MAX_STACK = 7      # confirmed vertical clearance for 7 crates under the 10' ceiling
BAKERY_BUFFER = 0.15   # Bakery & Snacks has room to spare (58-62/81 positions at 0% buffer)
MEALS_BUFFER = 0.0     # Meals is EXACTLY saturated by real demand at 0% buffer (81/81 -- any
                        # cushion at all pushes it over capacity and starts dropping products)

for p in products:
    p['cap'] = cap_for(p)
    d = demand[p['name']]
    p['daily_avg'] = d['daily_avg']
    p['demand_source'] = d['demand_source']
    p['divergence_flag'] = d['divergence_flag']
    buffer = MEALS_BUFFER if p['cat'] == 'meal' else BAKERY_BUFFER
    p['buffer_applied'] = buffer
    # crates sized to real daily demand + a cushion -- this room holds ONE
    # day's operational stock, not standing backstock.
    p['crates_needed'] = max(1, math.ceil((p['daily_avg'] * (1 + buffer)) / p['cap']))
    # lanes_needed is a capacity fact: how many physical lanes does it take
    # to hold that many crates at MAX_STACK each. 1 for the overwhelming
    # majority of products; >1 only for the handful whose daily crate need
    # exceeds what a single lane can physically stack.
    p['lanes_needed'] = math.ceil(p['crates_needed'] / MAX_STACK)

# Bakery rows (K1-K3) hold 35 positions/row now that crates there are
# turned to their 15.70" side facing the aisle instead of the 21.65" side
# -- more, narrower positions fit the same physical shelf run. Meals rows
# (M1-M3) are unchanged at 27 positions/row (crates still 21.65" facing out).
BAKERY_POSITIONS_PER_ROW = 35
MEALS_POSITIONS_PER_ROW = 27

def alpha_key(p):
    # sort by the meaningful part of the name (strip the shared line prefix)
    # so e.g. "Buffin Muffin - Blueberry" files under B, not under
    # "Buffin Muffin" repeated 20 times.
    name = re.sub(r'^(Buffin Muffin|Overnight Oats|Buff Crisp Bar)\s*-\s*', '', p['name'])
    # "Low Carb Keto Cheeseburger Bowl" was filing under L, so pickers
    # searching under "Cheeseburger" (what staff actually call it) never
    # found it on the blueprint. File it under its recognizable name instead.
    name = re.sub(r'^Low Carb Keto\s+', '', name)
    return name.lower()

def build_zone(prods_in_zone, total_positions_for_zone):
    """Alphabetical, category-stable placement. Every product gets exactly
    the lanes its own daily volume requires -- nothing more. Whatever
    positions are left over in the zone simply stay empty; this room is
    sized for what a day of picking needs, not for filling every shelf."""
    ordered = sorted(prods_in_zone, key=alpha_key)
    expanded = []
    for p in ordered:
        for _ in range(p['lanes_needed']):
            expanded.append(p)

    overflow = []
    if len(expanded) > total_positions_for_zone:
        # shouldn't happen at current catalog size, but don't silently
        # drop product if the catalog grows past physical capacity
        overflow = expanded[total_positions_for_zone:]
        expanded = expanded[:total_positions_for_zone]
    return expanded, overflow

def split_crates_across_lanes(product_lane_group, total_crates):
    """For the rare product that needs >1 lane just to physically hold its
    daily volume, split the total evenly across its lanes rather than
    showing the same full total on every one of them (which would make
    each lane look like it needs the WHOLE product's daily crates)."""
    n = len(product_lane_group)
    base = total_crates // n
    remainder = total_crates % n
    return [max(1, base + (1 if i < remainder else 0)) for i in range(n)]

def lanes_from_expanded(expanded, rows, positions_per_row):
    # positions_per_row: either a single int (uniform across rows) or a
    # list with one capacity per row (e.g. row 1 wider than the rest).
    if isinstance(positions_per_row, int):
        row_caps = [positions_per_row] * len(rows)
    else:
        row_caps = list(positions_per_row)
    # precompute the starting index (offset) of each row given its capacity
    row_starts = []
    acc = 0
    for cap in row_caps:
        row_starts.append(acc)
        acc += cap

    def locate(idx):
        for r in range(len(rows) - 1, -1, -1):
            if idx >= row_starts[r]:
                return r, idx - row_starts[r]
        return 0, idx

    lanes = []
    # group consecutive entries by product identity to split crates evenly
    i = 0
    n = len(expanded)
    while i < n:
        p = expanded[i]
        j = i
        while j < n and expanded[j] is p:
            j += 1
        group_size = j - i
        per_lane_crates = split_crates_across_lanes(range(group_size), p['crates_needed'])
        for k in range(group_size):
            idx = i + k
            row_idx, pos_idx = locate(idx)
            pos = pos_idx + 1
            code = f"{rows[row_idx]}-{pos:02d}"
            lanes.append({
                'code': code, 'product': p['name'], 'category': p['cat'],
                'daily_avg': p['daily_avg'], 'demand_source': p['demand_source'],
                'divergence_flag': p['divergence_flag'],
                'cap': p['cap'],
                'crates_needed': per_lane_crates[k],
                'max_stack': MAX_STACK,
                'lane_of_product': f"{k+1} of {group_size}" if group_size > 1 else None,
            })
        i = j
    return lanes

# ---- Bakery & Snacks (K1-K3, 81 positions): muffins get their own zone,
# oats+snacks share a zone, contiguous and alphabetical within each ----
muffins = [p for p in products if p['cat'] == 'muffin']
oats_snacks = [p for p in products if p['cat'] in ('oats', 'snack')]

BAKERY_ROWS = ['K1', 'K2', 'K3']
BAKERY_TOTAL = len(BAKERY_ROWS) * BAKERY_POSITIONS_PER_ROW  # 105

# Muffins zone gets exactly the lanes muffins need; oats+snacks zone gets
# exactly the lanes it needs, placed right after (no proportional padding
# to fill 81 -- that was the backstock-by-another-name behavior).
muffins_expanded, muffins_overflow = build_zone(muffins, BAKERY_TOTAL)
oats_snacks_room_left = BAKERY_TOTAL - len(muffins_expanded)
oats_snacks_expanded, oats_snacks_overflow = build_zone(oats_snacks, oats_snacks_room_left)

muffins_zone_size = len(muffins_expanded)
oats_snacks_zone_size = len(oats_snacks_expanded)

bakery_expanded = muffins_expanded + oats_snacks_expanded
bakery_overflow = muffins_overflow + oats_snacks_overflow
bakery_lanes = lanes_from_expanded(bakery_expanded, BAKERY_ROWS, BAKERY_POSITIONS_PER_ROW)

# ---- Meals (M1-M3, 84 positions): one zone, alphabetical ----
# All three rows flexed from 27 to 28 positions per Tony (2026-08-07) to
# make room for Cheeseburger Bowl (previously missing from the catalog
# entirely) without bumping Zeus Bowl or Zeus Bowl V2 off the layout --
# confirmed physically fine on his end.
meals = [p for p in products if p['cat'] == 'meal']
MEALS_ROWS = ['M1', 'M2', 'M3']
MEALS_ROW_CAPS = [28, 28, 28]
MEALS_TOTAL = sum(MEALS_ROW_CAPS)  # 84
meals_expanded, meals_overflow = build_zone(meals, MEALS_TOTAL)
meals_lanes = lanes_from_expanded(meals_expanded, MEALS_ROWS, MEALS_ROW_CAPS)

lane_plan = {
    'bakery': {
        'lanes': bakery_lanes,
        'overflow_lane_slots_dropped': len(bakery_overflow),
        'overflow_products': sorted(set(p['name'] for p in bakery_overflow)),
        'total_positions': BAKERY_TOTAL,
        'zones': [
            {'name': 'Muffins', 'category': 'muffin', 'positions': muffins_zone_size, 'products': len(muffins)},
            {'name': 'Oats & Snacks', 'category': 'oats+snack', 'positions': oats_snacks_zone_size, 'products': len(oats_snacks)},
        ],
    },
    'meals': {
        'lanes': meals_lanes,
        'overflow_lane_slots_dropped': len(meals_overflow),
        'overflow_products': sorted(set(p['name'] for p in meals_overflow)),
        'total_positions': MEALS_TOTAL,
        'zones': [
            {'name': 'Meals', 'category': 'meal', 'positions': MEALS_TOTAL, 'products': len(meals)},
        ],
    },
}

json.dump(lane_plan, open('/home/claude/hummusfit-warehouse/lane_plan.json', 'w'), indent=2)
json.dump(products, open('/home/claude/hummusfit-warehouse/products_with_demand.json', 'w'), indent=2)

for sec, d in lane_plan.items():
    print(sec, '-> positions used:', len(d['lanes']), '/', d['total_positions'], ' overflow dropped:', d['overflow_lane_slots_dropped'])
    for z in d['zones']:
        print('   zone:', z)

multi_lane = [p for p in products if p['lanes_needed'] > 1]
print(f'\nProducts needing >1 lane just to physically hold daily volume: {len(multi_lane)}')
for p in multi_lane:
    print(f"   {p['name']}: {p['crates_needed']} crates/day -> {p['lanes_needed']} lanes")

diverged = [p for p in products if p['divergence_flag']]
print('\nDivergence flags (7d vs 90d Shopify averages differ >2x):', len(diverged))
