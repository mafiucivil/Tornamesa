/* Precalcula, con el mismo código del worker de Tornamesa_BX (packages/web_bx/worker_bx.js), lo que la página muestra para los valores por
   defecto sin esperar a los workers. Lo usa tools/build_tt300bx.py (varios procesos en paralelo). Imprime JSON con los no finitos
   codificados («__NaN», «__Inf», «__-Inf»).
   Uso: node tools/precalc_bx.js analyze            → { key, fecha, r } (resultado de la operación «analyze» del worker)
        node tools/precalc_bx.js lazy:SC|MK|CN|TH    → resultado del bloque diferido
        node tools/precalc_bx.js calls:0,3,4         → { clave: resultado } de PLANOS_BX.exportCalls (memoria del JSON de diseño) */
const BX = require("../packages/core/tt300bx.js"), BXW = require("../packages/web_bx/worker_bx.js"), PBX = require("../packages/web/planos_export_bx.js");
const P = Object.assign(BX.defaults(), { opt_uhmw: 1, opt_ss: 0, opt_bz: 0 });
const enc = (k, v) => (typeof v === "number" && !isFinite(v) ? (isNaN(v) ? "__NaN" : v > 0 ? "__Inf" : "__-Inf") : v);
const mode = process.argv[2] || "analyze";
let out;
if (mode === "analyze") out = { key: JSON.stringify(P), fecha: new Date().toISOString().slice(0, 10), r: BXW.analyze(P) };
else if (mode.startsWith("lazy:")) out = BXW.lazy(mode.slice(5), P);
else if (mode.startsWith("calls:")) {
  const C = PBX.exportCalls(Object.assign(BX.defaults(), P)), idx = mode.slice(6).split(",").map(Number);
  out = {}; idx.forEach((i) => { out[C[i].key] = BXW.call(C[i].fn, C[i].args); });
} else throw new Error("modo desconocido: " + mode);
process.stdout.write(JSON.stringify(out, enc));
