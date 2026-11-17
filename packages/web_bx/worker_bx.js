/* TT300-BX · Cálculo fuera del hilo principal (Web Worker de Tornamesa_BX).
   El dimensionamiento BX (BX.design) tarda varios segundos y el mercado, la capacidad por cilindros, los escenarios y la térmica entre
   segundos y minutos: todo eso corre aquí para que la página nunca quede bloqueada. Devuelve datos (sin funciones): la interfaz rearma
   las funciones de A.R con TT.compute sobre P con el gancho __bx que entrega este worker (sin volver a dimensionar).
   Operaciones: analyze (validate + BX.analyze + crossCheck + audit), lazy (SC escenarios, MK mercado, CN capacidad por cilindros,
   TH térmica, CMP análisis con drive_mode = 2 para la comparación de la guía) y design (JSON de diseño con el bloque «bx»).
   En el navegador las librerías (TT, BX, AG, AGBX, PLANOS_BX y PLANOS_W) vienen del mismo script de la página; en Node, por require. */
const BXW = (() => {
  const BX_ = (typeof BX !== "undefined") ? BX : require("../core/tt300bx.js");
  const AGBX_ = (typeof AGBX !== "undefined") ? AGBX : require("../agents/agentes_bx.js");
  const TT_ = (typeof TT !== "undefined") ? TT : require("../core/tt300c.js");
  // copia profunda sin funciones (estructura clonable para postMessage y JSON)
  function strip(o, seen) {
    if (typeof o === "function") return undefined;
    if (!o || typeof o !== "object") return (typeof o === "number" && !isFinite(o)) ? o : o;
    seen = seen || new Map();
    if (seen.has(o)) return seen.get(o);
    if (ArrayBuffer.isView(o)) return o;
    const r = Array.isArray(o) ? [] : {};
    seen.set(o, r);
    for (const k of Object.keys(o)) { const v = o[k]; if (typeof v !== "function") r[k] = strip(v, seen); }
    return r;
  }
  const keyOf = (P) => JSON.stringify(P);
  let last = { key: "", A: null };
  function analyzeFull(P) {
    const k = keyOf(P);
    if (last.key === k && last.A) return last.A;
    const A = BX_.analyze(P); last = { key: k, A }; return A;
  }
  function analyze(P) {
    const t0 = Date.now(), VAL = AGBX_.validate(P);
    if (VAL.some((v) => v.lvl === "error")) return { VAL, A: null };
    try {
      const A = analyzeFull(P), X = AGBX_.crossCheck(A), AU = AGBX_.audit(A.checks);
      let DD = null; try { DD = strip(TT_.designDrive(A.Pc, A.R)); } catch (e) { DD = null; }   // datos de dibujo del accionamiento (la página no los recalcula)
      return { VAL, A: strip(A), X: strip(X), AU: strip(AU), DD, ms: Date.now() - t0 };
    } catch (err) { VAL.push({ lvl: "error", msg: "Error de cálculo: " + err.message }); return { VAL, A: null }; }
  }
  const LAZY = {
    SC: (P) => AGBX_.scenarios(analyzeFull(P)),
    MK: (P) => BX_.market(P),
    CN: (P) => BX_.capacityByCyl(P, [1, 2]),
    TH: (P) => BX_.thermal(P, { wood: "form" }),
    CMP: (P) => BX_.analyze(Object.assign({}, P, { drive_mode: 2 }), { noFEA: true }),
  };
  function lazy(k, P) { return strip(LAZY[k](P)); }
  function design(P) {
    if (typeof PLANOS_W === "undefined") throw new Error("Módulo de planos no disponible en el worker");
    const A = analyzeFull(P), out = PLANOS_W.buildDesign(P, A);
    PLANOS_BX.finish(out, out.P, BX_);
    return PLANOS_W.designJSON(out);
  }
  function run(m) {
    if (m.op === "analyze") return analyze(m.P);
    if (m.op === "lazy") return lazy(m.k, m.P);
    if (m.op === "design") return design(m.P);
    throw new Error("operación desconocida: " + m.op);
  }
  return { run, strip, analyze, lazy, design };
})();
if (typeof module !== "undefined") module.exports = BXW;
else if (typeof self !== "undefined" && typeof document === "undefined") {
  self.onmessage = (e) => {
    const m = e.data;
    try { self.postMessage({ id: m.id, ok: true, r: BXW.run(m) }); }
    catch (err) { self.postMessage({ id: m.id, ok: false, err: String(err && err.message || err) }); }
  };
}
