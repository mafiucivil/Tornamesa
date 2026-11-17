/* Exporta el diseño TT300-BX para el generador de planos (fuente única): MISMO esquema que tools/export_design.js más el bloque «bx»
   (disco inoxidable y semidiscos, CJP, malla de tornillos, portador con su patrón de agujeros, pastillas, soldaduras, tabla de fabricación
   y verificaciones BX).
   Uso: node tools/export_design_bx.js [parametros.json] > design_bx.json
   Cómo: ejecuta el código de tools/export_design.js tal cual, con «require» redirigido a una fachada del núcleo que pasa cada P por BX.coreP
   (P con la geometría BX en el gancho __bx) y usa BX.analyze / BX.thermal / BX.defaults, y a los agentes adaptados (agentes_bx.js). Así el
   esquema no se duplica y sigue a export_design.js; el JSON se completa con el bloque «bx». */
const fs = require("fs"), path = require("path"), Module = require("module"), vm = require("vm");
const TT = require("../packages/core/tt300c.js"), BX = require("../packages/core/tt300bx.js"), AGBX = require("../packages/agents/agentes_bx.js");

const isP = (x) => x && typeof x === "object" && !Array.isArray(x) && "W_tf" in x && "D_top" in x && !x.__bx;
const FAC = {};
for (const k of Object.keys(TT)) {
  const v = TT[k];
  FAC[k] = typeof v === "function" ? function (...a) { if (isP(a[0])) a[0] = BX.coreP(a[0]); return v.apply(TT, a); } : v;
}
Object.assign(FAC, { defaults: BX.defaults, analyze: BX.analyze, thermal: BX.thermal, PARAM_GROUPS: BX.PARAM_GROUPS, compute: (P) => BX.compute(P) });

const src = path.join(__dirname, "export_design.js");
const code = fs.readFileSync(src, "utf8");
const req = (id) => (/tt300c\.js$/.test(id) ? FAC : /agentes\.js$/.test(id) ? AGBX : require(id));
let buf = "";
const write0 = process.stdout.write.bind(process.stdout);
process.stdout.write = (chunk) => { buf += chunk; return true; };
try {
  const fn = vm.runInThisContext(Module.wrap(code), { filename: src });
  const m = { exports: {} };
  fn.call(m.exports, m.exports, req, m, src, path.dirname(src));
} finally { process.stdout.write = write0; }

const out = JSON.parse(buf);
const P = out.P;
out.proyecto = "TT300-BX";
out.modulo = { nombre: "TT300-BX", nucleo: "packages/core/tt300c.js (gancho P.__bx)", archivo: "packages/core/tt300bx.js", esquema: "tools/export_design.js + bloque «bx»" };
const A = BX.analyze(P, { noFEA: true });
out.bx = BX.exportBX(P, A);
process.stdout.write(JSON.stringify(out, null, 1));
