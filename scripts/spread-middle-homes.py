"""Spread existing middle homes without changing picking codes or sequence."""
import json,csv,html,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'public/backstock-studio';data=json.loads((out/'layout.json').read_text());racks={r['id']:r for r in data['racks']}
# Entrance is south; the open access corridor is on the right.
for rid,prefix in [('middle-1-b','M3'),('middle-2-a','M2'),('middle-2-b','M2')]:
 racks[rid]['groups']=[prefix]
 racks[rid]['name']=('B · Warehouse face · ' if rid=='middle-1-b' else 'C · Face '+('1' if rid.endswith('-a') else '2')+' · ')+prefix+' meals'
for prefix,faces,bays in [('M1',['south'],3),('M2',['middle-2-a','middle-2-b'],5),('M3',['middle-1-b'],5)]:
 homes=sorted([p for p in data['positions'] if p['code'].startswith(prefix+'-')],key=lambda p:int(p['code'].split('-')[1]))
 # Each physical section keeps a contiguous run. Enter from the right,
 # finish both C faces in that section, then move one section left.
 offset=0
 for index,bay in enumerate(range(bays,0,-1)):
  count=len(homes)//bays+(index<len(homes)%bays)
  section=homes[offset:offset+count];offset+=count
  facecounts=[count//len(faces)+(i<count%len(faces)) for i in range(len(faces))]
  j=0
  for face,nface in zip(reversed(faces),facecounts):
   for level in range(3):
    n=nface//3+(level<nface%3)
    for spot in range(1,n+1):
     p=section[j];j+=1
     p.update(rack=face,bay=bay,level=level,spot=spot,slot=spot-1,x=(bay-1)*96+96-96/(n+1)*spot-8,z=racks[face]['z']+5,y=[8,58,106][level])
# Snacks follow the same entrance-first rule; retain every existing physical slot.
homes=sorted([p for p in data['positions'] if p['code'].startswith('K')],key=lambda p:(p['code'].split('-')[0],int(p['code'].split('-')[1])))
slots=[{k:p[k] for k in ['rack','bay','level','spot','slot','x','z','y']} for p in sorted(homes,key=lambda p:(-p['bay'],p['level'],-p['spot']))]
for p,slot in zip(homes,slots):p.update(slot)
data['middle_assignment_revision']='2026-10-15: entrance route A/M1 → C/M2 → B/M3. Code 01 starts at the right access aisle; contiguous runs proceed section by section toward the left wall. C uses both warehouse faces per section. K1 then K2 starts at the entrance end of D. Kitchen excluded.'
(out/'layout.json').write_text(json.dumps(data,indent=2)+'\n');(out/'layout-data.js').write_text('const DATA='+json.dumps(data,separators=(',',':'))+';\n')
with (out/'product-locations.csv').open('w') as f:
 w=csv.writer(f,lineterminator="\n");w.writerow(['Code','Product','Area','Section','Shelf','Spot','Status'])
 for p in data['positions']:w.writerow([p['code'],p['product'],racks[p['rack']]['name'],p['bay'],['Floor','Middle','Top'][p['level']],p['spot'],'LOCATION PREVIEW — crate allocation pending measurements'])
# Preserve approved walls/doors and add exact per-level codes inside middle bays.
ET.register_namespace('','http://www.w3.org/2000/svg');tree=ET.parse(out/'staff-map.svg');svg=tree.getroot();ns='{http://www.w3.org/2000/svg}'
for node in list(svg):
 if node.attrib.get('data-middle-codes'):svg.remove(node)
 for rid in ['middle-1-b','middle-2-a','middle-2-b']:
  r=racks[rid]
  if node.tag==ns+'text' and node.attrib.get('y')==str(r['z']+28.0):
   node.set('y',str(r['z']+10));node.set('font-size','8')
 if node.text in ['B · Warehouse face · M2','B · M2 warehouse','B · M3 warehouse']:
  node.text='B · M3 warehouse';node.attrib.update({'x':'-12','y':'412','text-anchor':'end','font-size':'10'})
 if node.text in ['C · First warehouse face · M3','C · FACE 1 · M3','C · FACE 1 · M2']:
  node.text='C · FACE 1 · M2';node.attrib.update({'x':'-12','y':'556','text-anchor':'end','font-size':'10'})
 if node.text in ['C · Second warehouse face · warehouse face','C · FACE 2 · M3','C · FACE 2 · M2']:
  node.text='C · FACE 2 · M2';node.attrib.update({'x':'-12','y':'604','text-anchor':'end','font-size':'10'})
 if node.text=='C · First warehouse face · M3':node.text='C · FACE 1 · M2'
 if node.text=='C · Second warehouse face · warehouse face':node.text='C · FACE 2 · M2'
for rid in ['south','middle-1-b','middle-2-a','middle-2-b']:
 r=racks[rid]
 for bay in range(1,r['bays']+1):
  for level in range(3):
   homes=sorted([p for p in data['positions'] if p['rack']==rid and p['bay']==bay and p['level']==level],key=lambda p:p['spot'])
   text=ET.SubElement(svg,ns+'text',{'x':str((bay-.5)*96),'y':str(r['z']+22+level*10),'text-anchor':'middle','font-size':'6.7','fill':'#173c35','data-middle-codes':'1'})
   text.text=['F','M','T'][level]+' '+(', '.join(p['code'] for p in homes) or 'Unassigned')
# Show the walking route in open floor, outside product shelves.
for node in list(svg):
 if node.attrib.get('data-entrance-route'):svg.remove(node)
for x,y,label in [(360,706,'1 · A / M1 ← 01'),(365,650,'2 · C / M2 ← 01'),(360,465,'3 · B / M3 ← 01')]:
 node=ET.SubElement(svg,ns+'text',{'x':str(x),'y':str(y),'text-anchor':'middle','font-size':'12','font-weight':'bold','fill':'#007f73','data-entrance-route':'1'});node.text=label
node=ET.SubElement(svg,ns+'path',{'d':'M 520 748 L 550 748 L 550 450','stroke':'#007f73','stroke-width':'4','stroke-dasharray':'8 6','fill':'none','data-entrance-route':'1'})
svgtext=ET.tostring(svg,encoding='unicode');(out/'staff-map.svg').write_text(svgtext)
sections=[]
for rid in ['middle-1-b','middle-2-a','middle-2-b']:
 r=racks[rid];sections.append('<h2>'+html.escape(r['name'])+'</h2><div class="sections">')
 for bay in range(1,6):
  sections.append('<section><h3>Section '+str(bay)+'</h3>')
  for level in range(3):
   homes=sorted([p for p in data['positions'] if p['rack']==rid and p['bay']==bay and p['level']==level],key=lambda p:p['spot'])
   sections.append('<h4>'+['1 · Floor','2 · Middle','3 · Top usable shelf'][level]+'</h4>')
   for p in homes:sections.append('<a target="_top" href="/backstock-3d.html?code='+p['code']+'"><b>'+p['code']+'</b> · '+html.escape(p['product'])+'</a>')
   if not homes:sections.append('<p>Unassigned — no product home</p>')
  sections.append('</section>')
 sections.append('</div>')
(out/'staff-map.html').write_text('''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hummus Fit · Middle shelf locations</title><style>body{margin:0;font:14px -apple-system,BlinkMacSystemFont,Arial;color:#173c35;background:white}svg{width:100%;height:auto}article{padding:20px}h2{font-size:20px}h3{margin-top:0}h4{font-size:12px;margin:18px 0 8px;color:#007f73}.sections{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}section{border:1px solid #d6e6df;border-radius:16px;padding:16px}a{display:block;color:#173c35;text-decoration:none;font-size:13px;line-height:1.5;padding:5px 0}a b{color:#008e85}p{color:#687c73;font-size:12px}@media print{section{break-inside:avoid}article{padding:0}}</style></head><body>'''+svgtext+'<article><h1>Middle shelf locations</h1><p>From the blue entrance: A / M1 → C / M2 → B / M3. Start at the right aisle with code 01, finish that section floor → middle → top, then move left. On C, finish Face 2 then Face 1 in each section. D starts K1 then K2 at the entrance end. B’s kitchen side is DO NOT USE. Product locations only; physical crate capacity still needs measurements.</p>'+''.join(sections)+'</article></body></html>')
