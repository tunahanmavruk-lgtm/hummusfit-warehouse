const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const THREE=require(path.resolve('../../output/backstock-remodel/build-tools/node_modules/three'));
const src=fs.readFileSync('backstock/studio-build/src/warehouse.js','utf8');
const fitSource=src.slice(src.indexOf('function fittedView('),src.indexOf('function home(){'));
for(const [W,D] of [[648,768],[1000,300]])for(const aspect of [.64,1,1.64,2.2])for(const top of [false,true]){
 const camera=new THREE.PerspectiveCamera(48,aspect,1,10000),scope={THREE,W,D,camera};vm.createContext(scope);vm.runInContext(fitSource+';result=fittedView('+top+')',scope);const fit=scope.result;camera.position.copy(fit.position);camera.lookAt(fit.target);camera.updateMatrixWorld();
 for(const x of [0,W])for(const y of [0,150])for(const z of [0,D]){const p=new THREE.Vector3(x,y,z).project(camera);assert(Math.abs(p.x)<=1&&Math.abs(p.y)<=1,'room clipped');}
}
const data=JSON.parse(fs.readFileSync('public/backstock-studio/layout.json','utf8'));
const movement=src.slice(src.indexOf('function clearAt('),src.indexOf("canvas.addEventListener('pointerdown'"));
const scope={DATA:data,PICKING:false,Math,camera:{position:{x:540,z:690}},walkYaw:0};vm.createContext(scope);vm.runInContext(movement,scope);
vm.runInContext('for(let i=0;i<1000;i++)moveWalk(1,0,.05);result=clearAt(camera.position.x,camera.position.z)',scope);assert(scope.result,'walk crossed obstacle/boundary');
for(const page of ['3d-model','backstock-3d']){const html=fs.readFileSync('public/'+page+'.html','utf8');for(const id of ['quickOverview','quickWalk','walkJoystick','joystickKnob'])assert(html.includes('id="'+id+'"'));}
assert(src.includes('controls.enablePan=false'));assert(src.includes('controls.maxDistance=fit.distance*1.25'));assert(src.includes("document.addEventListener('visibilitychange'"));
console.log('PASS: room corners fit desktop/portrait overview and bird view; walking stops at obstacles; shared reset, joystick and focus-loss safeguards.');
