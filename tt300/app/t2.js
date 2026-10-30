global.FEA = require('./fea.js');
const C = require('./calc.js');
const P = C.defaults(); const R = C.compute(P);
const pw = C.runPawl(P, R);
const arr = pw.res.el.map((e,i)=>[e.vm, pw.cent[i][0], pw.cent[i][1]]).sort((a,b)=>b[0]-a[0]);
console.log(arr.slice(0,15).map(a=>a.map(v=>v.toFixed(1)).join(' ')).join('\n'));
console.log('Xs',pw.Xs.toFixed(1),'Xm',pw.Xm);
// stress along vertical line x ~ 100
for (const x of [70, 90, 110, 114]) { const col = pw.res.el.map((e,i)=>[e.sx,pw.cent[i][0],pw.cent[i][1]]).filter(a=>Math.abs(a[1]-x)<1.3); console.log(x, col.filter((a,i)=>i%4==0).map(a=>a[0].toFixed(0)+'@'+a[2].toFixed(0)).join(' ')); }
