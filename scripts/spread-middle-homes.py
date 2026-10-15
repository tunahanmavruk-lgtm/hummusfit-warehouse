"""Spread existing middle homes without changing picking codes or sequence."""
import json,csv,html,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'public/backstock-studio';data=json.loads((out/'layout.json').read_text());racks={r['id']:r for r in data['racks']}
racks['middle-2-a']['name']='C · Face 1 · M3 meals';racks['middle-2-b']['name']='C · Face 2 · M3 meals';racks['middle-2-b']['groups']=['M3']
for prefix in ['M2','M3']:
 for level in range(3):
  homes=sorted([p for p in data['positions'] if p['code'].startswith(prefix+'-') and p['level']==level],key=lambda p:int(p['code'].split('-')[1]))
  if prefix=='M2':
   per=[len(homes)//5+(b<len(homes)%5) for b in range(5)];slots=[('middle-1-b',b+1,j+1,n) for b,n in enumerate(per) for j in range(n)]
  else:
   # Continue ascending codes on face 1, then face 2, on each level.
   slots=[(face,b,1,1) for face in ['middle-2-a','middle-2-b'] for b in range(1,6)]
   skip=[('middle-2-b',5),('middle-2-a',5),('middle-2-b',1)][level]
   slots=[s for s in slots if s[:2]!=skip]
  assert len(homes)==len(slots)
  for i,(p,(face,bay,spot,n)) in enumerate(zip(homes,slots)):
   p.update(rack=face,bay=bay,spot=spot,slot=i,x=(bay-1)*96+(96/(n+1))*spot-8,z=racks[face]['z']+5)
data['middle_assignment_revision']='2026-10-15: B five warehouse sections; C five sections on both faces; codes ordered by level, face, section, spot. Kitchen excluded.'
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
 if node.text=='C · First warehouse face · M3':node.text='C · FACE 1 · M3'
 if node.text=='C · Second warehouse face · warehouse face':node.text='C · FACE 2 · M3'
for rid in ['middle-1-b','middle-2-a','middle-2-b']:
 r=racks[rid]
 for bay in range(1,6):
  for level in range(3):
   homes=sorted([p for p in data['positions'] if p['rack']==rid and p['bay']==bay and p['level']==level],key=lambda p:p['spot'])
   text=ET.SubElement(svg,ns+'text',{'x':str((bay-.5)*96),'y':str(r['z']+22+level*10),'text-anchor':'middle','font-size':'6.7','fill':'#173c35','data-middle-codes':'1'})
   text.text=['F','M','T'][level]+' '+(', '.join(p['code'] for p in homes) or 'Unassigned')
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
(out/'staff-map.html').write_text('''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hummus Fit · Middle shelf locations</title><style>body{margin:0;font:14px -apple-system,BlinkMacSystemFont,Arial;color:#173c35;background:white}svg{width:100%;height:auto}article{padding:20px}h2{font-size:20px}h3{margin-top:0}h4{font-size:12px;margin:18px 0 8px;color:#007f73}.sections{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}section{border:1px solid #d6e6df;border-radius:16px;padding:16px}a{display:block;color:#173c35;text-decoration:none;font-size:13px;line-height:1.5;padding:5px 0}a b{color:#008e85}p{color:#687c73;font-size:12px}@media print{section{break-inside:avoid}article{padding:0}}</style></head><body>'''+svgtext+'<article><h1>Middle shelf locations</h1><p>Follow codes in order across Face 1, then Face 2, on each shelf level. B’s kitchen side is DO NOT USE. Product locations only; physical crate capacity still needs measurements.</p>'+''.join(sections)+'</article></body></html>')
