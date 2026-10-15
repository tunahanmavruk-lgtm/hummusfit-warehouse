# Backstock explorer — October 14, 2026

Published entry points: `/backstock-blueprint.html` and `/backstock-3d.html`.

The public layout file is `public/backstock-studio/layout.json`; `layout-data.js` is its browser script form. Both must be regenerated together after geometry edits. Maps and rendered geometry must agree.

Pinned browser engine: three.js 0.186.1, bundled with esbuild 0.28.2. Rebuild using `npm ci` then `node build.cjs` inside this directory. The checked-in bundle needs no CDN or production build step. MIT dependency notices are retained in the bundle.

Features: physical materials and room lighting, soft PCF shadows, instanced rack geometry, orbit and bird’s-eye views, collision-aware eye-level keyboard/touch navigation, six-stop guided tour with aisle waypoints, interactive minimap, code/name lookup, section/level guidance, shelf filtering, wall cutaway, PNG export and fullscreen.

All prior product homes and picking codes are preserved. B’s kitchen face remains excluded. A’s highest physical wire deck remains excluded. The entrance is shifted two more feet to the right relative to the previous review. The kitchen door is on the kitchen-use side of B. Door widths and room width remain schematic.

Stock is a dated research snapshot, not a live count or historical average. Final allocation remains pending measured clear heights, usable bay widths, loaded stack approval and SKU/packout checks. The review guide explicitly warns against using unvalidated capacity as loading instructions.

Deployment changes only static backstock assets; picking blueprint, lane plan, seed code, database and inventory APIs are unchanged.
