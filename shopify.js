// Live Shopify inventory sync.
//
// Root problem this fixes: the crate targets shown on the blueprint/backstock
// pages were a 3.5-day DEMAND FORECAST (90-day sales velocity x reserve days),
// not a measurement of what's actually produced and sitting on hand. For
// products made in smaller batches (meals especially), the forecast ran way
// ahead of reality -- e.g. Broritto Burrito: forecast said 62 crates, actual
// on-hand was 36. Fix: read real inventory from Shopify instead of guessing.
//
// This does NOT touch lane/position assignments (where a product lives) --
// only the crate-count target shown alongside it. Locations are a separate,
// intentionally-stable decision; on-hand quantity changes by the hour.
//
// OAuth notes: this app is unlisted/custom, non-embedded, installed on a
// single store (myhummusfit.myshopify.com). Client ID/Secret + shop domain
// come from Railway variables (SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET,
// SHOPIFY_SHOP, SHOPIFY_SCOPES). The Admin API access token obtained via the
// OAuth flow is persisted in the `meta` table (key 'shopify_access_token') so
// it survives redeploys via the mounted volume -- Tony only has to grant
// access once at /shopify/install, not every deploy.
const crypto = require('crypto');

const SHOP = process.env.SHOPIFY_SHOP;
const CLIENT_ID = process.env.SHOPIFY_CLIENT_ID;
const CLIENT_SECRET = process.env.SHOPIFY_CLIENT_SECRET;
const SCOPES = process.env.SHOPIFY_SCOPES || 'read_inventory,read_products';
const API_VERSION = '2026-07';

// In-memory OAuth state store -- short-lived (install flow completes in
// seconds), a single admin user, restart just means "click install again."
// Not worth persisting to the DB.
const pendingStates = new Map();

function configured() {
  return Boolean(SHOP && CLIENT_ID && CLIENT_SECRET);
}

function installUrl(redirectUri) {
  const state = crypto.randomBytes(16).toString('hex');
  pendingStates.set(state, Date.now());
  // Prune anything older than 10 minutes so this map never grows unbounded.
  for (const [s, t] of pendingStates) {
    if (Date.now() - t > 10 * 60 * 1000) pendingStates.delete(s);
  }
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    scope: SCOPES,
    redirect_uri: redirectUri,
    state,
  });
  return `https://${SHOP}/admin/oauth/authorize?${params.toString()}`;
}

function verifyState(state) {
  if (!pendingStates.has(state)) return false;
  pendingStates.delete(state);
  return true;
}

async function exchangeCodeForToken(code) {
  const res = await fetch(`https://${SHOP}/admin/oauth/access_token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      code,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Token exchange failed (${res.status}): ${text}`);
  }
  const data = await res.json();
  return data.access_token;
}

function saveToken(db, token) {
  db.prepare(
    `INSERT INTO meta (key, value) VALUES ('shopify_access_token', ?)
     ON CONFLICT(key) DO UPDATE SET value = excluded.value`
  ).run(token);
  db.prepare(
    `INSERT INTO meta (key, value) VALUES ('shopify_token_saved_at', ?)
     ON CONFLICT(key) DO UPDATE SET value = excluded.value`
  ).run(new Date().toISOString());
}

function getToken(db) {
  const row = db.prepare(`SELECT value FROM meta WHERE key = 'shopify_access_token'`).get();
  return row ? row.value : null;
}

// Names that don't line up between our product list and Shopify's real
// titles, discovered by diffing the first live sync's unmatched list against
// a manual Shopify lookup (Aug 5, 2026). Two real patterns:
//  - Buff Crisp Bar: each flavor is its OWN single-variant Shopify product,
//    not a variant of one "Buff Crisp Bar" product -- and Shopify's title
//    has the flavor word BEFORE "Buff Crisp Bar" ("Cinna Crunch Buff Crisp
//    Bar"), the reverse of our "Buff Crisp Bar - Cinna Crunch". This was
//    already flagged as a known risk in pick-list-generator-design-reference.
//  - A couple of others drifted from a rename on the Shopify side ("Fit Ala
//    Vodka With Chicken" -> "Fit A La Vodka With Chicken", "Peanut Butter
//    Chocolate Gree-Yo" -> "Peanut butter gree-yo" dropped "Chocolate").
// Add to this map instead of renaming products.json -- it keeps our product
// names stable (they're also lane/lookup keys elsewhere) while still
// tolerating Shopify's actual title.
const NAME_ALIASES = {
  'Buff Crisp Bar - Cinna Crunch': 'Cinna Crunch Buff Crisp Bar',
  'Buff Crisp Bar - Original Recipe': 'Buff Crisp Bar Original Recipe',
  'Buff Crisp Bar - Fruity Cereal': 'Fruity Cereal Buff Crisp Bar',
  'Buff Crisp Bar - Chocolate': 'Chocolate Buff Crisp Bar',
  'Fit Ala Vodka With Chicken': 'Fit A La Vodka With Chicken',
  'Peanut Butter Chocolate Gree-Yo': 'Peanut butter gree-yo',
};

// Loose key for matching: lowercase, collapse whitespace, and fold curly
// apostrophes/quotes to straight ones. Fixes real mismatches seen on the
// first live sync -- "Blueberry French Toast" vs Shopify's "Blueberry
// french toast" (case only), and "S'Mores Gree-Yo" vs Shopify's literal
// "S’Mores Gree-Yo" (curly apostrophe, a different Unicode character than
// the straight one our product list uses).
function normalizeKey(s) {
  return String(s)
    .toLowerCase()
    .replace(/[‘’‛]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/\s+/g, ' ')
    .trim();
}

// Pull every active product's title + variant titles + inventory quantities.
// Returns a map of "matchable name" -> total on-hand units, built two ways
// per product so the products.json naming style ("Buffin Muffin - X") and a
// plain variant title both have a chance to match:
//   - "{ProductTitle}" -> inventory (single-variant products, e.g. meals)
//   - "{ProductTitle} - {VariantTitle}" -> inventory (multi-variant products)
// Keys are stored both as-is and under a normalized (case/quote-insensitive)
// form so lookups can fall back to the normalized form without every caller
// needing to know about it.
async function fetchInventoryMap(token) {
  // sortKey: ID makes cursor pagination deterministic across pages -- without
  // it, a query-filtered connection's ordering isn't guaranteed stable while
  // paging, which is the leading suspect for why "MsWendy Buff Nuggets" (an
  // exact-title, active product) came back missing from the first live sync
  // despite existing exactly as named.
  const query = `
    query($cursor: String) {
      products(first: 100, after: $cursor, query: "status:active", sortKey: ID) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            title
            variants(first: 100) {
              edges { node { title inventoryQuantity } }
            }
          }
        }
      }
    }
  `;
  const inventory = {};
  const normalized = {};
  const setKey = (key, qty) => {
    inventory[key] = (inventory[key] || 0) + qty;
    const nk = normalizeKey(key);
    normalized[nk] = (normalized[nk] || 0) + qty;
  };
  let cursor = null;
  let hasNext = true;
  while (hasNext) {
    const res = await fetch(`https://${SHOP}/admin/api/${API_VERSION}/graphql.json`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': token,
      },
      body: JSON.stringify({ query, variables: { cursor } }),
    });
    if (!res.ok) {
      throw new Error(`Shopify inventory fetch failed: ${res.status} ${await res.text()}`);
    }
    const json = await res.json();
    if (json.errors) throw new Error(`Shopify GraphQL error: ${JSON.stringify(json.errors)}`);
    const products = json.data.products;
    for (const { node: p } of products.edges) {
      const variants = p.variants.edges.map((e) => e.node);
      const totalQty = variants.reduce((sum, v) => sum + Math.max(0, v.inventoryQuantity || 0), 0);
      setKey(p.title, totalQty);
      for (const v of variants) {
        if (v.title && v.title !== 'Default Title') {
          setKey(`${p.title} - ${v.title}`, Math.max(0, v.inventoryQuantity || 0));
        }
      }
    }
    hasNext = products.pageInfo.hasNextPage;
    cursor = products.pageInfo.endCursor;
  }
  return { exact: inventory, normalized };
}

// Look up a product by our name: exact match first, then the alias table,
// then a case/quote-insensitive match as a last resort. Returns undefined
// if none of those find anything -- a real "doesn't exist in Shopify (yet,
// or anymore)" case, which the caller reports as unmatched rather than
// guessing.
function lookupInventory(inventoryMap, name) {
  if (inventoryMap.exact[name] !== undefined) return inventoryMap.exact[name];
  const alias = NAME_ALIASES[name];
  if (alias && inventoryMap.exact[alias] !== undefined) return inventoryMap.exact[alias];
  const nk = normalizeKey(alias || name);
  if (inventoryMap.normalized[nk] !== undefined) return inventoryMap.normalized[nk];
  return undefined;
}

// Recompute products.target_crates = ceil(on-hand units / cap) for every
// product we can match by name. Does NOT touch lane_assignments (location
// stays put) -- only the target number shown alongside it.
async function syncInventory(db) {
  const token = getToken(db);
  if (!token) throw new Error('Not connected to Shopify yet -- visit /shopify/install first.');
  const inventory = await fetchInventoryMap(token);

  const products = db.prepare('SELECT id, name, cap FROM products').all();
  const update = db.prepare('UPDATE products SET target_crates = ?, target_crates_source = ? WHERE id = ?');
  let matched = 0, unmatched = [];
  const applyAll = db.transaction(() => {
    for (const p of products) {
      const onHand = lookupInventory(inventory, p.name);
      if (onHand === undefined) {
        unmatched.push(p.name);
        continue;
      }
      const crates = Math.ceil(onHand / p.cap);
      update.run(crates, 'shopify_live', p.id);
      matched++;
    }
  });
  applyAll();

  db.prepare(
    `INSERT INTO meta (key, value) VALUES ('shopify_last_sync', ?)
     ON CONFLICT(key) DO UPDATE SET value = excluded.value`
  ).run(new Date().toISOString());

  return { matched, unmatchedCount: unmatched.length, unmatched: unmatched.slice(0, 20) };
}

module.exports = {
  configured,
  installUrl,
  verifyState,
  exchangeCodeForToken,
  saveToken,
  getToken,
  fetchInventoryMap,
  syncInventory,
  lookupInventory,
  normalizeKey,
  NAME_ALIASES,
};
