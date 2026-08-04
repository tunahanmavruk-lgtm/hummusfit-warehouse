# Pick List Generator — Design Reference

Paste this into your route board app chat and tell it: "Build our delivery/route pick list using this same approach, adapted to our data." It has everything needed to replicate the logic without needing this conversation.

## Live data source — use this, not a static file

Don't hand-copy a CSV snapshot into the route board app. Point it at the live endpoint instead:

`https://ravishing-exploration-production-83e3.up.railway.app/api/lanes`

This returns the current lane assignments straight from the warehouse app's database, which auto-reseeds itself from `lane_plan.json` every time that file changes and gets redeployed — so it can never silently go stale the way a hand-copied file would. Every field in the "Data model" section below is present on each row that endpoint returns.

## Product-name matching — the part most likely to break silently

If the route board app needs to join Shopify order line items against the warehouse's product/location list, do NOT assume you can just concatenate Shopify's `title` and `variantTitle` fields and get a match. Two things to watch for:

- Most products with flavors (Buffin Muffin, Overnight Oats) do split cleanly as `title + " - " + variantTitle` (e.g. `"Buffin Muffin - Apple Pie-Ceps"`), matching the warehouse's product name exactly.
- At least one product line (Buff Crisp Bar) does NOT — Shopify's `product_title` for at least one flavor came back as a single flat string with the flavor word order reversed (`"Cinna Crunch Buff Crisp Bar"` instead of `"Buff Crisp Bar - Cinna Crunch"`). A naive concatenation will produce a string that matches nothing.
- Build the join defensively: log every row that fails to match rather than dropping it silently, and expect to hand-correct a small number of name mismatches (word order, punctuation) the first time you run it against real data.

## The core idea

A pick list is only useful if it matches how a human actually moves through physical space. Two different orderings solve two different jobs — don't collapse them into one list:

1. **Walking-order sheet** — sorted in the exact physical sequence a person moves through (aisle by aisle, stop by stop, shelf by shelf). This is what the person in the field/warehouse uses while doing the work.
2. **Alphabetical (or ID-based) index** — same data, sorted by name/product/customer instead. This is what a manager uses to answer "how much of X do we need" without hunting through the walking-order sheet.

Generate both from the *same* source data in one document (walking-order pages first, index as an appendix), so they can never drift out of sync with each other.

## Data model

Every row in the source data needs these fields — for the warehouse this was per storage lane, for a route board it'd be per stop/drop:

- **Location code** — the physical/positional identifier (here: lane code like `K1-01`; for routes: stop number or sequence position on the route).
- **Item/product name** — what's there.
- **Category/type** — a grouping label (here: muffin/oats/snack/meal) so someone can jump to their section. For routes this might be delivery zone, customer type, or route leg.
- **Daily quantity needed** — the actual number to act on (here: crates/day, computed from `daily_avg units ÷ units_per_crate`). For a route, this is probably units to load per stop, or time-window/priority.
- **Unit conversion field** — a second number that lets someone working in a different unit act correctly (here: units per crate, so a picker grabbing loose units instead of a full crate knows the conversion). For routes this might be items-per-box or stops-per-zone.
- **Confidence/data-source flag** — mark any row where the number is estimated/blended rather than backed by real order data. Never let an estimated number look identical to a verified one — a manager needs to know which numbers to trust before reordering or rerouting based on them.
- **Positions-per-row can vary by section** — don't hardcode one constant. The warehouse's Bakery rows hold 35 positions each and Meals rows hold 27, because the crates are physically turned to a different side depending on section. Compute "row, position" from whatever the source data's own per-section capacity is, never from a single global number — the same mistake would misplace every route stop past the shortest leg's length if a route board ever has legs of different sizes.

## Sort logic (the part that actually matters)

- Group by top-level section first (here: Bakery & Snacks vs. Meals; for routes: maybe by driver, zone, or morning/afternoon run).
- Within a section, group by the next physical unit (here: row K1/K2/K3; for routes: maybe by leg or neighborhood cluster).
- Within that, sort by position number in the literal order a person walks/drives it (here: position 1→27 left to right down the aisle; for routes: stop 1→N in drive order, not alphabetical by customer name).
- The alphabetical/ID appendix ignores all of the above and just sorts flat by name — it's the "cross-reference" view, not the "do the work" view.

## Output format that worked well

- One table per physical grouping (here: one table per row, ~15-30 rows each) rather than one giant table — easier to scan on paper, and naturally paginates into something that can be torn off or handed to one person covering one section/route.
- Header row repeats on every page (a PDF table feature — `repeatRows=1` in reportlab) so a multi-page section never loses its column labels.
- Zebra-striped rows in a color tied to the section (teal-tinted for Bakery, gray-tinted for Meals) so someone flipping pages instantly knows which section they're in without re-reading the header.
- A footer with room-wide/route-wide totals (total items, total estimated-vs-confirmed count) so a manager glancing at the last page gets the summary without reading every row.
- Location codes flagged with `~` inline (not a separate column) when the number for that location is a blended estimate — visible without adding a whole extra column to scan.

## What made this data trustworthy enough to print

The daily quantity wasn't guessed — it's computed as `real observed daily demand ÷ unit-conversion factor`, sourced directly from Shopify Online Store sales (90-day trailing daily average per product/flavor), not from a blended estimate. Each row also carries a divergence flag: if that product's most recent 7-day average differs from its 90-day average by more than 2x, the row is flagged `~` as worth a spot-check before trusting blindly (a real spike/dip, not a data error, but still worth a human glance). Before trusting this pattern for the route board app: identify whichever data source is the *real, observed* signal for that app (actual delivery history, actual order timestamps, etc.) and compute from that first, falling back to blended/estimated numbers only where real data doesn't exist — and flag those fallback rows the same way.

## Minimal build recipe (Python, reportlab)

```
1. Load source data (JSON/DB/CSV) with location, item, category, qty, unit-conversion, source-flag fields.
2. Group into physical/logical sections, then sub-groups, sorted by walking/drive order.
3. Build one reportlab Table per sub-group: header row (bold, dark background, white text),
   data rows (zebra-striped, section-tinted), repeatRows=1.
4. Stack sub-group tables in physical order inside a SimpleDocTemplate story.
5. PageBreak, then one big Table sorted alphabetically/by-ID as the appendix.
6. Footer paragraph: total item count, total daily quantity, count of estimated/flagged rows.
7. Regenerate straight from the live source data file — never hand-maintain a copy of these numbers.
```

This is exactly the shape of `build_pick_sheet.py` from the Hummus Fit walk-in project — same script structure, different source data and different notion of "physical order."
