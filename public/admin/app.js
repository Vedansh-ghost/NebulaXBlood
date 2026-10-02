const API=localStorage.getItem('nebula_api')||window.location.origin;
const HEADERS=()=>({'Content-Type':'application/json','X-Nebula-Admin':localStorage.getItem('nebula_admin_token')||''});
function saveToken(){localStorage.setItem('nebula_admin_token',adminToken.value); location.reload()}
async function get(p){const r=await fetch(API+p,{headers:HEADERS()});return r.json()}
async function createPlan(){const b={name:name.value,kind:kind.value,ram_mb:+ram.value||1024,cpu_percent:+cpu.value||100,disk_mb:+disk.value||10240,price_minor:(+price.value||0)*100};const r=await fetch(API+'/api/plans',{method:'POST',headers:HEADERS(),body:JSON.stringify(b)});alert(r.ok?'Plan created':'Failed: '+await r.text());location.reload()}
(async()=>{try{nodes.innerHTML=(await get('/api/nodes')).map(n=>`<p>${n.name} · ${n.kind} · ${n.status}</p>`).join('')||'No nodes yet'}catch(e){nodes.textContent='API offline'}})();
