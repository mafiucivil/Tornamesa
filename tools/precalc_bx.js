/* Precalcula, con el mismo código del worker de Tornamesa_BX (packages/web_bx/worker_bx.js), el resultado de los valores por defecto
   que la página muestra al abrir sin esperar al worker. Lo usa tools/build_tt300bx.py; imprime JSON con los no finitos codificados
   («__NaN», «__Inf», «__-Inf»). Uso: node tools/precalc_bx.js > pre.json */
const BX = require("../packages/core/tt300bx.js"), BXW = require("../packages/web_bx/worker_bx.js");
const P = Object.assign(BX.defaults(), { opt_uhmw: 1, opt_ss: 0, opt_bz: 0 });
const r = BXW.analyze(P);
const enc = (k, v) => (typeof v === "number" && !isFinite(v) ? (isNaN(v) ? "__NaN" : v > 0 ? "__Inf" : "__-Inf") : v);
process.stdout.write(JSON.stringify({ key: JSON.stringify(P), fecha: new Date().toISOString().slice(0, 10), r }, enc));
