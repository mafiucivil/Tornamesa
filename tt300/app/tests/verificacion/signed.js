global.FEA = require('./fea_mod.js');
const C = require('./calc_mod.js'); const P = C.defaults(); const deg=Math.PI/180;
for (const [hr,dth] of [[null,null],[10,0.625*deg],[5,0.3125*deg]]) {
  const f = C.runDisc(P,'bot',hr,dth), m=f.model, r=f.res.reac;
  const s=(g)=>g.reduce((a,k)=>a+r[k],0)/1e3, ab=(g)=>g.reduce((a,k)=>a+Math.abs(r[k]),0)/1e3;
  const neg=(g)=>g.filter(k=>Math.sign(r[k])!==Math.sign(s(g))).length;
  console.log(hr, 'bars signed', m.groups.bar.map(s).map(v=>v.toFixed(1)), 'abs', m.groups.bar.map(ab).map(v=>v.toFixed(1)), 'nodes', m.groups.bar.map(g=>g.length), 'oppSign', m.groups.bar.map(neg),
   'rings signed kN', m.groups.ring.map(s).map(v=>v.toFixed(1)), 'abs', m.groups.ring.map(ab).map(v=>v.toFixed(1)), 'rib', s(m.groups.rib).toFixed(1), ab(m.groups.rib).toFixed(1), 'hub', s(m.groups.hub).toFixed(1));
}
