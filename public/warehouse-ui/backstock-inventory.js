(()=>{
 const originalRender=renderProducts;
 const fmt=n=>n==null?'Unavailable':Number(n).toLocaleString();
 function currentFor(p){const rows=p.codes.map(code=>window.HFInventory.forCode(code)).filter(Boolean);return rows[0]||null;}
 window.renderProducts=function(){originalRender();const visible=STUDIO.products.filter(p=>(p.codes.join(' ')+' '+p.name).toLowerCase().includes(document.getElementById('productSearch').value.toLowerCase()));document.querySelectorAll('#productRows tr').forEach((row,i)=>{const p=currentFor(visible[i]);const cell=row.children[2];if(!cell)return;cell.textContent=p?.onHand!=null?fmt(p.onHand)+(p.status==='stale'?' · saved':p.status==='count-needed'?' · count needed':''):'Unavailable';const packout=visible[i].packout;row.children[6].textContent=packout?(p?.status==='ok'&&p.onHand>=0?fmt(Math.ceil(p.onHand/packout)):'Unavailable'):'Packout needed';if(p?.reportedAt){const stamp=document.createElement('div');stamp.className='hf-stock-time';stamp.textContent=window.HFInventory.when(p.reportedAt);cell.append(stamp);}cell.title=p?'Whole warehouse total. Source report '+window.HFInventory.when(p.reportedAt):'No verified current match';});};
 document.getElementById('productSearch').oninput=window.renderProducts;
 // Current capacity scenarios use verified current units only, never historical fallback or negative counts.
 window.packingUnits=p=>{if(document.getElementById('stockBasis').value!=='current')return p.designUnits;const live=currentFor(p);return live&&live.status==='ok'&&live.onHand>=0?live.onHand:null;};
 function update(){window.renderProducts();calculate();}
 document.addEventListener('hf:inventory',update);update();
})();
