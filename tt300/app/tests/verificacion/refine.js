global.FEA = require('./fea_mod.js');
global.performance = global.performance || require('perf_hooks').performance;
const C = require('./calc_mod.js');
const P = C.defaults();
const deg = Math.PI / 180;
function nodalAvgVM(f) {
  // promedio nodal de momentos (centro de elemento) -> σvm nodal suavizado
  const m = f.model, nn = m.nodes.length, S = Array.from({ length: nn }, () => [0, 0, 0, 0]);
  f.res.el.forEach((e, i) => m.elems[i].forEach((k) => { for (let c = 0; c < 3; c++) S[k][c] += e.M[c]; S[k][3]++; }));
  let mx = 0, at = null; const k6 = 6 / (m.t * m.t);
  S.forEach((s, k) => { if (!s[3]) return; const sx = s[0] / s[3] * k6, sy = s[1] / s[3] * k6, t = s[2] / s[3] * k6;
    const vm = Math.sqrt(sx * sx - sx * sy + sy * sy + 3 * t * t); if (vm > mx) { mx = vm; at = m.pol[k]; } });
  return [mx, at];
}
for (const which of ['bot', 'top']) {
  console.log('==', which);
  for (const [hr, dth] of [[null, null], [10, 0.625 * deg], [5, 0.3125 * deg], [3, 0.2 * deg]]) {
    const f = C.runDisc(P, which, hr, dth);
    let vn = 0; f.res.el.forEach((e) => { vn = Math.max(vn, e.vmNode); });
    const [va, at] = nodalAvgVM(f);
    console.log(`hr ${hr || 'def'} dθ ${dth ? (dth / deg).toFixed(3) : 'def'} nodes ${f.model.nodes.length} vmC ${f.vmC.toFixed(2)} vmGauss ${f.vmMax.toFixed(2)} at r=${f.maxAt[0].toFixed(0)} θ=${f.maxAt[1].toFixed(2)} vmCorner ${vn.toFixed(2)} vmNodalAvg ${va.toFixed(2)} at r=${at[0].toFixed(0)} θ=${(at[1] / deg).toFixed(2)} w ${f.wMax.toFixed(4)} rings ${f.ringLine.map((v) => v.toFixed(0))} bars ${f.barF.map((v) => v.toFixed(1))} rib ${f.ribF.toFixed(1)} hub ${f.hubF.toFixed(1)} F ${f.Fapp.toFixed(1)} R ${f.Rsum.toFixed(1)} ms ${f.ms.toFixed(0)}`);
  }
}
