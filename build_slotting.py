"""
Builds lane_plan.json: which product goes in which physical lane, and how
many crates it gets.

REWRITTEN per direct feedback: the previous version sorted the entire
catalog by a single Monday's order velocity and packed products into lanes
starting from the fastest mover — which quietly left an ENTIRE row (K3, 27
positions) completely empty once it ran out of "important enough" products,
and jumbled muffins/oats/snacks together in velocity order instead of
giving each product line its own findable home.

That's backwards for a room staff have to work in every day. The room now
maps to the real, permanent structure of the catalog:
  - Every product line gets its own contiguous, alphabetically-ordered zone
    (all muffins together, all oats together, all snacks together, meals
    on their own rows) — the same zone every day, not reshuffled by
    whichever day's orders got sampled.
  - Real order data (with the same 0.173 correction for the 17 products
    that never appeared in the sample) still drives HOW MANY CRATES a lane
    gets — that's legitimate inventory sizing, not shelf placement — so
    high-volume items get more standing stock and get restocked less
    often, without moving to a "better" location for it.
  - Any leftover floor space in a zone (a category doesn't perfectly fill
    its rows) goes to extra backstock capacity for that same zone's
    products, round-robin — not to a different, empty-looking row.
"""
import json, math, re
from collections import defaultdict

products = json.load(open('/home/claude/hummusfit-warehouse/products.json'))
real_counts = json.load(open('/home/claude/hummusfit-warehouse/real_matched_counts.json'))
by_name = {p['name']: p for p in products}

def cap_for(p):
    if p['cat'] == 'meal': return 24
    if p['cat'] == 'muffin': return 24
    if p['cat'] == 'oats': return 28
    if p['cat'] == 'snack':
        if re.search(r'gree-yo|pudding', p['name'], re.I): return 28
        if re.search(r'buff crisp bar', p['name'], re.I): return 48
        return 24
    return 24

DAYS_COVER = 1
MAX_STACK = 5
NUM_REAL_ORDER_DAYS = 1
UNMATCHED_CORRECTION = 0.173  # see build_slotting notes above / blueprint flaw #6-7

for p in products:
    p['cap'] = cap_for(p)
    blended_daily = p['u30'] / 30.0
    real_daily = real_counts.get(p['name'])
    if real_daily is not None:
        real_daily = real_daily / NUM_REAL_ORDER_DAYS
        p['daily_avg'] = real_daily
        p['demand_source'] = 'real'
    else:
        p['daily_avg'] = blended_daily * UNMATCHED_CORRECTION
        p['demand_source'] = 'blended x0.173 correction (no real-order match)'
    p['blended_daily'] = round(blended_daily, 1)
    p['real_daily'] = round(real_daily, 1) if real_daily is not None else None
    if real_daily is not None and blended_daily > 0:
        ratio = real_daily / blended_daily
        p['divergence_flag'] = ratio < 0.4 or ratio > 2.5
    else:
        p['divergence_flag'] = False
    # crates/lanes are sized off real demand -> legitimate inventory sizing,
    # not a placement decision.
    p['crates_needed'] = max(1, math.ceil((p['daily_avg'] * DAYS_COVER) / p['cap']))
    p['lanes_needed'] = math.ceil(p['crates_needed'] / MAX_STACK)

POSITIONS_PER_ROW = 27

def alpha_key(p):
    # sort by the meaningful part of the name (strip the shared line prefix)
    # so e.g. "Buffin Muffin - Blueberry" files under B, not under
    # "Buffin Muffin" repeated 20 times.
    name = re.sub(r'^(Buffin Muffin|Overnight Oats|Buff Crisp Bar)\s*-\s*', '', p['name'])
    return name.lower()

def build_zone(prods_in_zone, total_positions_for_zone):
    """Alphabetical, category-stable placement. Every product gets its
    base lane(s) first; any positions left over in the zone go to extra
    backstock capacity — allocated PROPORTIONALLY to real daily demand
    (largest-remainder apportionment), not a flat round-robin. A flat
    round-robin was handing nearly every product exactly one extra lane
    regardless of whether it actually sells enough to justify it — that's
    not real inventory sizing, just a different way of ignoring demand.
    This way the room's real movers get real backstock, low-volume items
    stay at their base lane, and the zone still fills completely so no
    row is left empty."""
    ordered = sorted(prods_in_zone, key=alpha_key)
    expanded = []
    for p in ordered:
        for _ in range(p['lanes_needed']):
            expanded.append(p)

    remaining = total_positions_for_zone - len(expanded)
    if remaining > 0:
        weight_total = sum(max(p['daily_avg'], 0.01) for p in prods_in_zone)
        raw_shares = [(p, remaining * max(p['daily_avg'], 0.01) / weight_total) for p in prods_in_zone]
        floor_counts = {id(p): int(share) for p, share in raw_shares}
        allocated = sum(floor_counts.values())
        leftover = remaining - allocated
        # largest-remainder method: give the +1 lanes to whichever products
        # had the biggest fractional share left over, until leftover is 0
        remainders = sorted(raw_shares, key=lambda ps: -(ps[1] - int(ps[1])))
        for p, share in remainders:
            if leftover <= 0:
                break
            floor_counts[id(p)] += 1
            leftover -= 1
        bonus = []
        for p in prods_in_zone:
            bonus.extend([p] * floor_counts[id(p)])
        expanded.extend(bonus)
    overflow = []
    if remaining < 0:
        # zone genuinely doesn't have room for every base lane (shouldn't
        # happen at current catalog size, but don't silently drop product
        # if the catalog grows past capacity)
        overflow = expanded[total_positions_for_zone:]
        expanded = expanded[:total_positions_for_zone]
    return expanded, overflow

def lanes_from_expanded(expanded, rows, positions_per_row):
    lanes = []
    for idx, p in enumerate(expanded):
        row_idx = idx // positions_per_row
        pos = idx % positions_per_row + 1
        code = f"{rows[row_idx]}-{pos:02d}"
        lanes.append({
            'code': code, 'product': p['name'], 'category': p['cat'],
            'daily_avg': p['daily_avg'], 'demand_source': p['demand_source'],
            'divergence_flag': p['divergence_flag'],
            'cap': p['cap'], 'crates_needed': p['crates_needed'],
        })
    return lanes

# ---- Bakery & Snacks (K1-K3, 81 positions): muffins get their own zone,
# oats+snacks share a zone, contiguous and alphabetical within each ----
muffins = [p for p in products if p['cat'] == 'muffin']
oats_snacks = [p for p in products if p['cat'] in ('oats', 'snack')]

BAKERY_ROWS = ['K1', 'K2', 'K3']
BAKERY_TOTAL = len(BAKERY_ROWS) * POSITIONS_PER_ROW  # 81

# Split the 81 positions between the two zones proportionally to how many
# base lanes each needs, so muffins (more products) get more of the room
# without hand-picking row boundaries.
muffins_base = sum(p['lanes_needed'] for p in muffins)
oats_snacks_base = sum(p['lanes_needed'] for p in oats_snacks)
base_total = muffins_base + oats_snacks_base
muffins_zone_size = round(BAKERY_TOTAL * muffins_base / base_total) if base_total else 0
oats_snacks_zone_size = BAKERY_TOTAL - muffins_zone_size

muffins_expanded, muffins_overflow = build_zone(muffins, muffins_zone_size)
oats_snacks_expanded, oats_snacks_overflow = build_zone(oats_snacks, oats_snacks_zone_size)

bakery_expanded = muffins_expanded + oats_snacks_expanded
bakery_overflow = muffins_overflow + oats_snacks_overflow
bakery_lanes = lanes_from_expanded(bakery_expanded, BAKERY_ROWS, POSITIONS_PER_ROW)

# ---- Meals (M1-M3, 81 positions): one zone, alphabetical, 78 products
# fill 78 of 81 positions on their own — no separate overflow row needed ----
meals = [p for p in products if p['cat'] == 'meal']
MEALS_ROWS = ['M1', 'M2', 'M3']
MEALS_TOTAL = len(MEALS_ROWS) * POSITIONS_PER_ROW  # 81
meals_expanded, meals_overflow = build_zone(meals, MEALS_TOTAL)
meals_lanes = lanes_from_expanded(meals_expanded, MEALS_ROWS, POSITIONS_PER_ROW)

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

diverged = [p for p in products if p['divergence_flag']]
print('\nDivergence flags (real vs blended differ >2.5x or <0.4x):', len(diverged))
