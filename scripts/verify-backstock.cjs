const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'..'),pub=path.join(root,'public');
const DATA=JSON.parse(fs.readFileSync(path.join(pub,'backstock-studio/layout.json')));
const source=fs.readFileSync(path.join(root,'backstock/studio-build/src/warehouse.js'),'utf8');
const scope={DATA,Math,PICKING:false};vm.createContext(scope);const clear=source.match(/function clearAt\(x,z\)\{.*?\}\);\}/s)?.[0];assert(clear);vm.runInContext(clear,scope);
for(const [x,z] of [[540,690],[540,100],[250,480],[330,680],[180,270]])assert(scope.clearAt(x,z),`clear aisle ${x},${z}`);
for(const [x,z] of [[100,360],[200,550],[625,300],[30,280],[100,740],[-1,500],[650,600]])assert(!scope.clearAt(x,z),`blocked rack/swing/wall ${x},${z}`);
assert.equal(DATA.entrance_blue_door.x,396);assert.deepEqual(DATA.kitchen_door.opening_z_in,[240,336]);
assert(!DATA.positions.some(p=>p.rack==='middle-1-kitchen'));assert(DATA.positions.every(p=>p.level>=0&&p.level<=2));
assert.equal(DATA.racks.find(r=>r.id==='middle-2-a').z-(DATA.racks.find(r=>r.id==='middle-1-b').z+48),96);
assert.equal(DATA.racks.find(r=>r.id==='right').x-480,120);
const laneCodes=new Map();function visit(n){if(Array.isArray(n))n.forEach(visit);else if(n&&typeof n==='object'){if(n.code&&n.product)laneCodes.set(n.code,n.product);Object.values(n).forEach(visit);}}visit(JSON.parse(fs.readFileSync(path.join(root,'lane_plan.json'))));
for(const p of DATA.positions)assert.equal(p.product,laneCodes.get(p.code),p.code+' matches picking master');assert.equal(DATA.positions.length,146);
const dataScript=fs.readFileSync(path.join(pub,'backstock-studio/layout-data.js'),'utf8');const browserData=vm.runInNewContext(dataScript+';JSON.stringify(DATA)');assert.deepEqual(JSON.parse(browserData),DATA);
for(const name of ['backstock-blueprint.html','backstock-3d.html']){const html=fs.readFileSync(path.join(pub,name),'utf8');for(const match of html.matchAll(/(?:src|href)="([^"]+)"/g)){const link=match[1];if(/^(https?:|#)/.test(link))continue;assert(fs.existsSync(path.join(pub,link.split('?')[0])),name+' asset '+link);}}
console.log('PASS: navigation collisions, door sweeps, aisle widths, kitchen/top-level exclusions, 146 exact master codes, shared layout data and all entry-page asset paths.');

for(const id of ['middle-1-b','middle-2-a','middle-2-b']){const homes=DATA.positions.filter(p=>p.rack===id);assert.deepEqual([...new Set(homes.map(p=>p.bay))].sort(),[1,2,3,4,5]);}
for(const prefix of ['M2','M3'])for(let level=0;level<3;level++){const homes=DATA.positions.filter(p=>p.code.startsWith(prefix+'-')&&p.level===level);const ordered=[...homes].sort((a,b)=>a.rack.localeCompare(b.rack)||a.bay-b.bay||a.spot-b.spot);assert.deepEqual(ordered.map(p=>p.code),homes.map(p=>p.code).sort((a,b)=>+a.split('-')[1]-+b.split('-')[1]));}
console.log('PASS: all five middle sections on B and both C faces; ascending code neighbors retained on each level; kitchen excluded.');
