const mapping=require('./inventory-code-mapping.json');
const plan=require('./lane_plan.json');
const SOURCE_CONFIG={meals:'https://web-production-524d8.up.railway.app/api/fifo',buffins:'https://buffin-fifo-production.up.railway.app/api/fifo',oats:'https://oats-snacks-fifo-production.up.railway.app/api/fifo'};
const finite=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
function collectLanes(n,out=[]){if(Array.isArray(n))n.forEach(v=>collectLanes(v,out));else if(n&&typeof n==='object'){if(n.code&&n.product)out.push(n);Object.values(n).forEach(v=>collectLanes(v,out));}return out;}
function normalizeSource(id,data,receivedAt=new Date().toISOString()){
 const meal=id==='meals',rows=meal?data.meals:data.products;if(!Array.isArray(rows))throw Error('Invalid inventory response');
 const byId=new Map(),byName=new Map();
 for(const p of rows){const record={name:p.name,variantId:p.variantId||null,onHand:finite(p.onHand),available:finite(meal?p.shopifyAvailable:p.available),committed:finite(p.committed),source:id,reportedAt:meal?data.lastRun:data.generatedAt,locationId:meal?null:data.locationId};
  if(p.variantId)byId.set(p.variantId,record);
  if(byName.has(p.name)&&byName.get(p.name).onHand!==record.onHand)throw Error('Conflicting duplicate inventory values');
  byName.set(p.name,record);
 }
 const reportTime=(meal?data.lastRun:data.generatedAt)||null;const oldReport=!reportTime||!Number.isFinite(Date.parse(reportTime))||Date.now()-Date.parse(reportTime)>10*60*1000;return {id,byId,byName,status:data.stale||oldReport?'stale':'ok',reportedAt:reportTime,receivedAt,locationId:meal?null:data.locationId};
}
function assemble(sources){const products={},byCode={};
 for(const lane of collectLanes(plan)){
  if(!lane.product||lane.product.toLowerCase()==='empty')continue;
  const approved=mapping[lane.code];const sourceId=approved?.department||(lane.code.startsWith('M')?'meals':null);const source=sources[sourceId];
  const record=source&&(!approved||approved.productName===lane.product)&&(approved?source.byId?.get(approved.variantId):source.byName?.get(lane.product));
  const key=record?.variantId||sourceId+':'+lane.product;
  const status=!record?'unmatched':source.status==='stale'?'stale':record.onHand===null?'unavailable':record.onHand<0?'count-needed':'ok';
  byCode[lane.code]={name:lane.product,onHand:record?.onHand??null,available:record?.available??null,committed:record?.committed??null,source:sourceId,reportedAt:source?.reportedAt||null,status,productKey:key};
  if(!products[key])products[key]={...byCode[lane.code],codes:[]};products[key].codes.push(lane.code);
 }
 return {checkedAt:new Date().toISOString(),scope:'Whole shipping warehouse: picking + backstock; not shelf-specific counts.',refreshSeconds:60,sources:Object.fromEntries(Object.entries(sources).map(([id,s])=>[id,{status:s.status,reportedAt:s.reportedAt||null,receivedAt:s.receivedAt||null,locationId:s.locationId||null}])),byCode,products:Object.values(products)};
}
function createInventoryService(fetchImpl=fetch){let cache=null,expires=0,pending=null;const lastGood={};
 async function refresh(){const entries=await Promise.all(Object.entries(SOURCE_CONFIG).map(async([id,url])=>{try{const r=await fetchImpl(url,{signal:AbortSignal.timeout(15000),headers:{accept:'application/json'}});if(!r.ok)throw Error('Source unavailable');const s=normalizeSource(id,await r.json());lastGood[id]=s;return[id,s];}catch{return[id,lastGood[id]?{...lastGood[id],status:'stale'}:{id,status:'unavailable',reportedAt:null}];}}));cache=assemble(Object.fromEntries(entries));expires=Date.now()+60000;return cache;}
 return async function get(){if(cache&&Date.now()<expires)return cache;if(!pending)pending=refresh().finally(()=>pending=null);return pending;};
}
module.exports={normalizeSource,assemble,collectLanes,createInventoryService,SOURCE_CONFIG};
