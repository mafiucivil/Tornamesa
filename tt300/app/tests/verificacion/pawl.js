global.FEA = require('./fea_mod.js');
const C = require('./calc_mod.js');
for (const h of [5, 2.5, 1.25]) {
  const P = C.defaults(); P._h = h; const R = C.compute(P);
  const pw = C.runPawl(P, R);
  // localizar vmFar y perfil σx en secciones
  let far = 0, fat = null;
  pw.res.el.forEach((e, i) => { const [cx, cy] = pw.cent[i];
    const nearLoad = Math.hypot(cx - pw.Xs, cy - pw.Ys) < pw.Rs + 4 * h;
    const nearSup = pw.sup.some((k) => Math.hypot(cx - pw.nodes[k][0], cy - pw.nodes[k][1]) < 4 * h);
    if (!nearLoad && !nearSup && e.vm > far) { far = e.vm; fat = [cx, cy]; } });
  let top = pw.res.el.map((e,i)=>[e.vm,...pw.cent[i]]).sort((a,b)=>b[0]-a[0]).slice(0,3).map(a=>a.map(v=>v.toFixed(1)).join('@'));
  // sección justo antes de la boca: σx en fibra superior e inferior, y momento integrado
  const xs = pw.Xm - h/2; let M=0, Nx=0; const col = pw.res.el.map((e,i)=>[e.sx,...pw.cent[i]]).filter(a=>Math.abs(a[1]-xs)<h/2+1e-6);
  col.forEach(a=>{ M += a[0]*(a[2]-pw.b/2)*h*P.pawl_h; Nx += a[0]*h*P.pawl_h; });
  console.log(`h=${h}: vmMax ${pw.vmMax.toFixed(0)} mouth ${pw.vmMouth.toFixed(0)} far ${pw.vmFar.toFixed(0)} @(${fat.map(v=>v.toFixed(1))}) beam ${pw.beam.toFixed(0)} dmax ${pw.dmax.toFixed(3)} top3 ${top.join(' | ')}; sección x=${xs.toFixed(2)}: M_int ${(M/1e6).toFixed(2)} kN·m (F·lev ${(R.Fmax*(xs-pw.Xs)/1e3).toFixed(2)}), σx sup ${Math.max(...col.map(a=>a[0])).toFixed(0)} inf ${Math.min(...col.map(a=>a[0])).toFixed(0)}`);
  // reacciones en apoyos
  const rs = pw.res.reac; let Rm=0, Rb=0; rs.forEach(([k,d,f])=>{ if(d!==1) return; if(pw.nodes[k][1]<1) Rm+=f; else Rb+=f; });
  console.log(`   reacción boca (inf) ${(Rm/1e3).toFixed(1)} kN, labio posterior (sup) ${(Rb/1e3).toFixed(1)} kN`);
}
