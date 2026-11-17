// Geometría en planta de lo que hay sobre la base (exploración del inserto). Uso: node geo.js '{"opt_uhmw":1}' > geo.json
const fs = require("fs"), path = require("path");
const CORE = process.env.CORE || path.join(__dirname, "..", "..", "..", "packages", "core", "tt300c.js");
let src = fs.readFileSync(CORE, "utf8").replace("return { woodGeo,", "return { pivMoving, woodGeo,");
const m = { exports: {} };
new Function("module", "require", "__dirname", src)(m, (p) => require(path.resolve(path.dirname(CORE), p)), path.dirname(CORE));
const TT = m.exports;
const extra = process.argv[2] ? JSON.parse(process.argv[2]) : {};
const P = Object.assign(TT.defaults(), { drive_mode: 2 }, extra);
const R = TT.compute(P);
const BC = TT.baseClear(P, R);
const mov = []; TT.pivMoving(P, R).forEach((s) => s.partes.forEach((p) => mov.push({ id: p.id + " c" + s.cil + " " + s.sentido, poly: p.poly, z: p.z })));
const out = { P: { B: P.B, t_base: P.t_base, D_top: P.D_top, rim_t: P.rim_t, rim_h: P.rim_h, hAxis: TT.hAxis(P), D_body: P.D_body, E: R.K.E },
  ears: BC.ears.map((e) => ({ poly: e.poly, z: e.z })), plates: BC.plates.map((p) => ({ id: p.id, poly: p.poly, z: p.z })), sup: BC.sup.map((p) => ({ id: p.id, poly: p.poly, z: p.z })), mov };
process.stdout.write(JSON.stringify(out));
