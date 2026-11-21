/* TT300-BX · Exportación del JSON de diseño (fuente única para Node y navegador).
   El JSON de BX es el MISMO esquema que tools/export_design.js / packages/web/planos_export.js (buildDesign) más el bloque «bx».
   · facade(TT, BX, opt): fachada del núcleo que pasa cada P por BX.coreP (P con la geometría BX en el gancho __bx) y usa BX.defaults,
     BX.analyze, BX.thermal y BX.PARAM_GROUPS. Con opt.coreP se usa otra función para inyectar __bx (la interfaz del navegador inyecta
     la geometría que ya calculó el worker, sin volver a dimensionar) y con opt.keep = true no se reemplazan analyze/thermal/compute.
   · finish(out, P, BX): completa el JSON con proyecto, modulo y el bloque «bx» = BX.exportBX(P, BX.analyze(P, { noFEA: true })).
   Lo usan tools/export_design_bx.js (Node) y el worker de Tornamesa_BX (packages/web_bx/worker_bx.js). */
const PLANOS_BX = (() => {
  const isP = (x) => x && typeof x === "object" && !Array.isArray(x) && "W_tf" in x && "D_top" in x && !x.__bx;
  function facade(TT, BX, opt) {
    opt = opt || {};
    const cp = opt.coreP || BX.coreP, FAC = {};
    for (const k of Object.keys(TT)) {
      const v = TT[k];
      FAC[k] = typeof v === "function" ? function (...a) { if (isP(a[0])) a[0] = cp(a[0]); return v.apply(TT, a); } : v;
    }
    Object.assign(FAC, { defaults: BX.defaults, PARAM_GROUPS: BX.PARAM_GROUPS });
    if (!opt.keep) Object.assign(FAC, { analyze: BX.analyze, thermal: BX.thermal, compute: (P) => BX.compute(P) });
    if (opt.memo) MEMO_FN.forEach((k) => { const f = FAC[k]; FAC[k] = function (...a) { const m = opt.memo, key = memoKey(k, a); return m.has(key) ? m.get(key) : f.apply(this, a); }; });
    return FAC;
  }
  /* Resultados que el exportador pide además del análisis (planos_export.js → buildDesign: interfazChecks, bombaBarrido, cubierta,
     mercado, capCil, termica). El navegador los calcula en paralelo en varios workers y se los entrega al worker que arma el JSON en una
     memoria (opt.memo: Map clave → resultado); una clave que no esté se calcula allí mismo (mismo resultado, solo más lento). */
  const MEMO_FN = ["analyze", "compute", "market", "capacityByCyl", "thermal"];
  const memoKey = (fn, args) => fn + "|" + JSON.stringify(args);
  function exportCalls(P) {
    const c = [["market", [P]], ["capacityByCyl", [P, [1, 2]]], ["thermal", [P]]];
    [1, 2, 3].forEach((k) => c.push(["analyze", [Object.assign({}, P, { opt_ss: k === 1 ? 1 : 0, opt_uhmw: k === 2 ? 1 : 0, opt_bz: k === 3 ? 1 : 0 }), { noFEA: true }]]));
    [[1.8, 0], [5, 0], [10, 0], [10, 20], [20, 0]].forEach(([q, qr]) => c.push(["compute", [Object.assign({}, P, { Q_pump: q, Q_ret: qr })]]));
    c.push(["analyze", [Object.assign({}, P, { opt_wood: 1, opt_bz: 0 }), { noFEA: true }]], ["analyze", [Object.assign({}, P, { opt_wood: 0 }), { noFEA: true }]]);
    return c.map(([fn, args]) => ({ fn, args, key: memoKey(fn, args) }));
  }
  // solo lo que buildDesign lee de cada resultado (bombaBarrido: pump, tRev, tCycle; interfazChecks y cubierta: checks y R.m)
  function memoTrim(fn, v) {
    if (!v || typeof v !== "object") return v;
    if (fn === "compute") return { pump: v.pump, tRev: v.tRev, tCycle: v.tCycle };
    if (fn === "analyze") return { checks: v.checks, R: { m: v.R && v.R.m } };
    return v;
  }
  function finish(out, P, BX, Anf) {
    out.proyecto = "TT300-BX";
    out.modulo = { nombre: "TT300-BX", nucleo: "packages/core/tt300c.js (gancho P.__bx)", archivo: "packages/core/tt300bx.js", esquema: "tools/export_design.js + bloque «bx»" };
    const A = Anf || BX.analyze(P, { noFEA: true });
    out.bx = BX.exportBX(P, A);
    if (BX.patchDesign) BX.patchDesign(out, P);   // rev. 9: textos de materiales del núcleo corregidos para el juego BX
    return out;
  }
  return { isP, facade, finish, exportCalls, memoKey, memoTrim, MEMO_FN };
})();
if (typeof module !== "undefined") module.exports = PLANOS_BX;
