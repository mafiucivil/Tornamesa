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
    return FAC;
  }
  function finish(out, P, BX, Anf) {
    out.proyecto = "TT300-BX";
    out.modulo = { nombre: "TT300-BX", nucleo: "packages/core/tt300c.js (gancho P.__bx)", archivo: "packages/core/tt300bx.js", esquema: "tools/export_design.js + bloque «bx»" };
    const A = Anf || BX.analyze(P, { noFEA: true });
    out.bx = BX.exportBX(P, A);
    return out;
  }
  return { isP, facade, finish };
})();
if (typeof module !== "undefined") module.exports = PLANOS_BX;
