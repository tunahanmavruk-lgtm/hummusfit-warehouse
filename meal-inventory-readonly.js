// Fixed read-only query: no caller-supplied operations or inventory mutations.
const QUERY=`query WarehouseMealInventory($cursor: String, $location: ID!) {
 products(first: 100, after: $cursor, query: "status:active", sortKey: ID) {
  pageInfo { hasNextPage endCursor }
  nodes { title variants(first: 2) { nodes { inventoryItem { inventoryLevel(locationId: $location) { quantities(names: ["on_hand", "committed", "available"]) { name quantity } } } } } }
 }
}`;
async function readMealInventory(token,fetchImpl=fetch){
 const shop=process.env.SHOPIFY_SHOP;if(!token||!shop)throw Error('Read-only Shopify connection unavailable');
 const meals=[];let cursor=null;const key=s=>s.toLowerCase().replace(/[‘’]/g,"'").replace(/\s+/g,' ').trim();const names=new Map(require('./warehouse-inventory').collectLanes(require('./lane_plan.json')).filter(p=>p.code.startsWith('M')).map(p=>[key(p.product),p.product]));const seen=new Set();
 do{
  const r=await fetchImpl(`https://${shop}/admin/api/2026-07/graphql.json`,{method:'POST',signal:AbortSignal.timeout(15000),headers:{'Content-Type':'application/json','X-Shopify-Access-Token':token},body:JSON.stringify({query:QUERY,variables:{cursor,location:'gid://shopify/Location/103133642999'}})});
  if(!r.ok)throw Error('Read-only Shopify report unavailable');const json=await r.json();if(json.errors||!json.data?.products)throw Error('Invalid Shopify inventory report');
  const conn=json.data.products;
  for(const p of conn.nodes){if(p.variants.nodes.length!==1)continue;const q=p.variants.nodes[0].inventoryItem?.inventoryLevel?.quantities;if(!q)continue;const values=Object.fromEntries(q.map(v=>[v.name,v.quantity]));const name=names.get(key(p.title));if(!name)continue;if(seen.has(name))throw Error("Ambiguous meal identity");seen.add(name);meals.push({name,onHand:values.on_hand,committed:values.committed,shopifyAvailable:values.available});}
  cursor=conn.pageInfo.hasNextPage?conn.pageInfo.endCursor:null;
 }while(cursor);
 return {meals,lastRun:new Date().toISOString(),locationId:'gid://shopify/Location/103133642999'};
}
module.exports={readMealInventory,QUERY};
