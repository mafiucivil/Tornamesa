/* Pruebas del módulo TT300-BX (packages/core/tt300bx.js): disco inoxidable atornillado a la mesa (dos semidiscos con CJP) y pastillas de UHMW
   en un portador de acero soldado a la base. Corre en < 120 s:  node --test tests/test_tt300bx.js
   Incluye la verificación de que el núcleo TT300-C original sigue idéntico: (a) el subconjunto «golden» de tests/test_tt300c.js en un proceso hijo y
   (b) comparación bit a bit (JSON) del núcleo actual contra el de la base a67d98e (git show) en varias configuraciones, sin FEA. */
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), os = require("os"), cp = require("child_process");
const TT = require("../packages/core/tt300c.js"), BX = require("../packages/core/tt300bx.js"), AGBX = require("../packages/agents/agentes_bx.js");
const ROOT = path.join(__dirname, "..");
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol * Math.abs(b) + 1e-12, `${msg}: ${a} vs ${b} (tol ${tol * 100} %)`);

const P0 = BX.defaults();
const A0 = BX.analyze(P0, { noFEA: true });   // análisis por defecto sin FEA (rápido); la FEA se prueba aparte una vez
const G0 = A0.bx;
let A8_ = null; const A8 = () => (A8_ = A8_ || BX.analyze(Object.assign({}, P0, { bx_disc_modo: 0 }), { noFEA: true }));   // modo 0: disco macizo atornillado (revisiones 1–4)

/* ---------- 1. El núcleo original no cambia ---------- */
test("Núcleo: el gancho P.__bx es aditivo; sin él los resultados son bit-idénticos a la base a67d98e (JSON, sin FEA)", () => {
  let src;
  try { src = cp.execFileSync("git", ["show", "a67d98e:packages/core/tt300c.js"], { cwd: ROOT, encoding: "utf8", maxBuffer: 64 << 20 }); }
  catch (e) { return; }   // sin git: la prueba del golden (abajo) cubre el caso
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "tt300c_base_"));
  fs.writeFileSync(path.join(dir, "tt300c.js"), src);
  fs.copyFileSync(path.join(ROOT, "packages/core/fea.js"), path.join(dir, "fea.js"));
  const OLD = require(path.join(dir, "tt300c.js"));
  const ser = (A) => JSON.stringify({ R: A.R, checks: A.checks, verdict: A.verdict }, (k, v) => (typeof v === "function" ? undefined : (typeof v === "number" && !isFinite(v) ? String(v) : v)));
  const cfgs = [{}, { opt_uhmw: 1 }, { opt_ss: 1 }, { opt_ss: 1, fix_mode: 2 }, { opt_bz: 1, bz_conf: 3 }, { opt_uhmw: 1, drive_mode: 1 }, { opt_uhmw: 1, opt_wood: 1 }];
  for (const o of cfgs) {
    const Pn = Object.assign(TT.defaults(), o), Po = Object.assign(OLD.defaults(), o);
    assert.equal(ser(TT.analyze(Pn, { noFEA: true })), ser(OLD.analyze(Po, { noFEA: true })), "configuración " + JSON.stringify(o));
  }
  // izaje (FEA de la base): usa la masa sobre la huella; sin BX no cambia
  const Pn = Object.assign(TT.defaults(), { opt_uhmw: 1 }), Rn = TT.compute(Pn), Ro = OLD.compute(Object.assign(OLD.defaults(), { opt_uhmw: 1 }));
  assert.equal(TT.runLift(Pn, Rn, true).vmMax, OLD.runLift(Object.assign(OLD.defaults(), { opt_uhmw: 1 }), Ro, true).vmMax, "izaje");
  assert.deepEqual(Object.keys(TT).sort(), Object.keys(OLD).sort(), "API del núcleo sin claves nuevas");
});

test("Núcleo: subconjunto golden de tests/test_tt300c.js sin cambios (proceso hijo)", () => {
  const env = Object.assign({}, process.env, { UPDATE_GOLDEN: "" }); delete env.NODE_TEST_CONTEXT; delete env.UPDATE_GOLDEN;   // proceso hijo independiente del ejecutor de pruebas; nunca regenera el golden
  const r = cp.spawnSync(process.execPath, ["--test", "--test-reporter=tap", "--test-name-pattern=[Gg]olden", path.join(ROOT, "tests/test_tt300c.js")], { cwd: ROOT, encoding: "utf8", timeout: 110000, env });
  assert.equal(r.status, 0, (r.stdout || "").slice(-3000) + (r.stderr || ""));
  assert.match(r.stdout, /# pass 6/);
  assert.match(r.stdout, /# fail 0/);
});

/* ---------- 2. Módulo BX: activación, gancho y masas ---------- */
test("BX: valores por defecto activan la opción B con el gancho; A y C pasan al núcleo sin tocar", () => {
  assert.equal(P0.opt_uhmw, 1); assert.equal(P0.opt_ss, 0); assert.equal(P0.opt_bz, 0);
  assert.ok(BX.active(P0));
  const I = A0.R.ifc;
  assert.equal(I.bx, true);
  assert.equal(I.topes.length, 0, "sin topes ni sectores");
  assert.equal(I.cortes.length, 0);
  near(I.delta, G0.portador.t + G0.pastillas.h_p + G0.disco.t, 1e-12, "δ = t_portador + saliente + t_disco");
  near(A0.R.m.ssTop, G0.disco.masa, 1e-12, "masa rotatoria = disco inoxidable");
  near(A0.R.m.uhmw, G0.pastillas.masa_total, 1e-12, "m.uhmw = pastillas");
  near(A0.R.m.bxPortador, G0.portador.masa, 1e-12, "portador en m.total");
  assert.ok(!A0.checks.some((c) => /sectores\)|Lámina UHMW|Disco de la base/.test(c.name)), "sin filas de los sectores de la opción B");
  // A y C: el módulo devuelve el análisis del núcleo
  const Aa = BX.analyze(Object.assign({}, P0, { opt_uhmw: 0, opt_ss: 1 }), { noFEA: true }), Ta = TT.analyze(Object.assign(TT.defaults(), BX.A36.despues, { opt_ss: 1 }), { noFEA: true });
  assert.equal(Aa.bx, null);
  assert.equal(Aa.R.m.total, Ta.R.m.total);
});

test("BX: dimensiones adoptadas por defecto (lámina 304 de 3 mm soldada; en modo 0 disco de 6 u 8 mm con 60–200 tornillos M10/M12) y estado de cada parte", () => {
  const D = G0.disco, U = G0.pastillas, C = G0.portador;
  assert.match(D.material, /304/);
  assert.equal(D.t, 3, "lámina " + D.t + " mm");
  assert.ok(D.t >= D.t_req - 1e-9);
  const D8 = A8().bx.disco, T = D8.tornillos;
  assert.ok([6, 8].includes(D8.t), "disco modo 0 " + D8.t + " mm"); assert.ok(D8.t >= D8.t_req - 1e-9);
  assert.ok([10, 12].includes(T.d) && T.n >= 60 && T.n <= 200 && T.paso_malla >= 150, "tornillos " + T.n + " M" + T.d + " a " + T.paso_malla);
  A8().checks.filter((c) => c.bx && /Disco|Tornillos del disco/.test(c.name) && (c.kind === "fu" || c.kind === "geo")).forEach((c) => assert.ok(c.st === "ok", "modo 0: " + c.name + " FU " + c.fu));
  assert.ok(U.n > 30 && U.n < 2000, "n pastillas " + U.n);
  assert.equal(U.forma, "redonda"); assert.equal(U.lado, null); assert.ok(U.d >= 60 && U.d <= 300);
  assert.equal(C.agujeros.forma, "redonda"); assert.equal(C.agujeros.d, U.d);
  // a 20 °C cumple todo (FU ≤ 0,90; geométricas ≤ 1)
  // rev. 5 a 7 (UHMW de 30 mm, portador fijo de 22 mm A572, Ø ≤ 185): todo FU ≤ 1; sobre 0,90 (advertencia) solo la planitud de las pastillas, la torsión y el
  // ligamento del portador, las filas BX de anillos distintos y la base bajo E con el factor de la FEA (≤ 0,965) (docs/bx/README_BX.md §9 a §11)
  const WARN_OK = /^BX · (Pastillas( a \d+ °C)?: presión más sobrepresión por (falta de )?planitud|Portador: corte por torsión|Portador: ligamento junto a la pastilla|Aplastamiento en el agujero del anillo inferior|Pasador de empuje: flexión con la luz entre los planos medios|Plancha base bajo el soporte del ojal E: .* ajuste por la FEA)/;
  A0.checks.filter((c) => c.bx && (c.kind === "fu" || c.kind === "geo") && !/a 50 °C/.test(c.name)).forEach((c) => assert.ok(c.st === "ok" || (c.st === "warn" && WARN_OK.test(c.name) && c.fu < 0.966), "20 °C: " + c.name + " FU " + c.fu));
  // camino del arrastre por la cara inferior (μ_b): la pared y el tornillo usan el residual; la fila informa el FU sin μ_b
  const w = A0.checks.find((c) => /pared del agujero del portador \(arrastre residual/.test(c.name)), sinMu = +/sin μ_b: FU ([\d,]+)/.exec(w.formula)[1].replace(",", ".");
  near(w.fu * (0.25 / (0.25 - P0.bx_mu_base)), sinMu, 0.01, "FU sin μ_b = FU·μ_máx/(μ_máx − μ_b)");
  assert.ok([20, 25, 30, 40, 50].includes(U.H), "pastilla cortada de plancha comercial: H = " + U.H);
  near(U.H, C.t + U.h_p, 1e-12, "H = t_portador + saliente");
  assert.ok(C.paso - U.d >= C.ligamento - 1e-9, "ligamento");
  assert.equal(A0.verdict.gira, true);
  const bxRows = A0.checks.filter((c) => c.bx);
  assert.ok(bxRows.length >= 40, "filas BX " + bxRows.length);
  bxRows.forEach((c) => { assert.ok(c.ref && c.formula && c.grp && c.sys, "fila completa: " + c.name); });
  // disco, tornillos y portador cumplen con margen (FU ≤ 0,90 o geométricas ≤ 1)
  bxRows.filter((c) => /Disco|Tornillos del disco|Portador|Lámina|Tapones|Costura|Plancha inferior/.test(c.name) && (c.kind === "fu" || c.kind === "geo")).forEach((c) => assert.ok(c.st === "ok" || (WARN_OK.test(c.name) && c.fu < 0.955), c.name + " FU " + c.fu));
  // lo que no cumple es solo el UHMW (pastillas): documentado en docs/bx/README_BX.md
  A0.checks.filter((c) => c.st === "fail").forEach((c) => assert.match(c.name, /^BX · Pastillas/, "falla no prevista: " + c.name));
  // 80 °C: limitación de uso informativa (no pendiente crítico)
  assert.ok(A0.verdict.limitaciones_uso.some((l) => l.id === "BX-T-SELLO"));
  assert.ok(!A0.verdict.pendientes_criticos.some((c) => /80 °C/.test(c.nombre)));
  assert.ok(A0.checks.some((c) => c.bx && c.name.includes("Pastillas a " + P0.T_ifc_max + " °C: valor PV")));   // fila a la temperatura de uso (17-11-2026: 20 °C)
});

test("BX: lámina inox 304 espejo de 3 mm soldada a la mesa con tapones y costura perimetral (bx_disc_modo = 1, por defecto)", () => {
  const D = G0.disco, Lm = D.lamina, T = D.tapones;
  assert.equal(P0.bx_disc_modo, 1); assert.equal(D.modo, 1);
  assert.equal(D.t, 3); assert.match(D.material, /304/);
  assert.equal(D.tornillos.n, 0, "sin tornillos avellanados");
  near(A0.R.ifc.delta, G0.portador.t + G0.pastillas.h_p + 3, 1e-12, "δ con la lámina de 3 mm");
  // paneles: caben en el formato comercial (el mayor por defecto, 1500 × 3000), juntas a tope
  assert.ok(Lm.paneles.length >= 2);
  Lm.paneles.forEach((p) => assert.ok(p.ancho <= P0.bx_fmt_a - 2 * Lm.margen_corte + 1e-9 && p.largo <= P0.bx_fmt_b - 2 * Lm.margen_corte + 1e-9, JSON.stringify(p)));
  assert.match(Lm.junta.tipo, /tope/); assert.match(Lm.junta.aporte, /309L/);
  // tapones: Ø entre t + 8 y máx(Ø_mín + 3; 2,25·t) (AISC J2.3a), separación ≥ 4·Ø, borde ≥ 1,5·Ø, relleno = t
  assert.ok(T.d >= D.t + 8 - 1e-9 && T.d <= Math.max(D.t + 8 + 3, 2.25 * D.t) + 1e-9, "Ø tapón " + T.d);
  assert.ok(T.n >= 20, "n tapones " + T.n);
  let m = Infinity; for (let i = 0; i < T.lista.length; i++) for (let j = i + 1; j < T.lista.length; j++) m = Math.min(m, Math.hypot(T.lista[i].x - T.lista[j].x, T.lista[i].y - T.lista[j].y));
  assert.ok(m >= 4 * T.d - 1e-6, "separación " + m);
  T.lista.forEach((q) => { assert.ok(q.r <= Lm.R_ext - 1.5 * T.d + 1e-6 && q.r >= Lm.R_int + 1.5 * T.d - 1e-6, "borde " + q.r); assert.ok(Math.abs(q.y) >= P0.bx_c_cjp - 1e-9, "fuera de la junta"); });
  // Σ V·r de los tapones = par de calado (reparto polar elástico)
  near(T.lista.reduce((s, q) => s + q.V * q.r, 0) / 1e6, A0.R.TmaxTopes || A0.R.Tmax, 1e-9, "Σ V·r = T_calado");
  // filas propias de la lámina, todas cumplen con margen
  const L = (k) => A0.checks.find((c) => c.bx && c.name.includes(k));
  ["Tapones: corte del metal de aporte", "Tapones: aplastamiento y desgarro de la lámina", "Tapones: arrastre local de la pastilla más cargada", "Costura perimetral exterior",
   "pandeo por la compresión térmica", "pandeo combinado", "despegue entre tapones", "vacío local", "pastilla faltante", "celda entre pastillas", "sobreespesor", "Tapones: separación", "Tapones: distancia al borde", "Tapones: Ø"].forEach((k) => {
    const c = L(k); assert.ok(c, "fila " + k); assert.ok(c.st === "ok", k + " FU " + c.fu); });
  assert.ok(L("pistas de las pastillas"), "fila de coincidencia tapones–pistas");
  assert.ok(A0.checks.some((c) => c.bx && /Lámina: planitud después de soldar/.test(c.name)), "nota de fabricación de planitud");
  assert.ok(!A0.checks.some((c) => c.bx && /Tornillos del disco/.test(c.name)), "sin filas de tornillos del disco");
  // modo 0 (disco macizo atornillado) sigue disponible
  const G8 = BX.design(Object.assign({}, P0, { bx_disc_modo: 0 }));
  assert.equal(G8.disco.modo, 0); assert.ok([6, 8, 10].includes(G8.disco.t)); assert.ok(G8.disco.tornillos.n >= 60);   // rev. 7 (680 bar, mesa A572): 82 M10; las filas del modo 0 se verifican con FU arriba
});

test("BX: pastillas de ULTRA VST de 30 mm (Ø ≤ 185, cortadas de cuadrados de 190) en portador A572 Gr. 50 de 22 mm fijo (rev. 6/7)", () => {
  const U = G0.pastillas, C = G0.portador;
  assert.equal(P0.bx_H_uh, 30); assert.equal(P0.bx_tc, 22); assert.equal(P0.bx_dp_max, 185); assert.equal(P0.bx_rho_uh, 0.97);
  assert.equal(P0.Fy_bxc, 0); assert.equal(P0.Fu_bxc, 0); assert.equal(P0.Fy, 345);   // rev. 7: el global (A572 Gr. 50)
  assert.equal(U.H, 30); assert.equal(C.t, 22); near(U.h_p, 8, 1e-12, "saliente = 30 − 22");
  assert.ok(U.d <= 185 + 1e-9 && U.d_torneado <= 185 + 1e-9, "Ø " + U.d + " (corte " + U.d_torneado + ") ≤ 185");
  assert.ok(U.d_torneado <= P0.bx_cuad_uh - 2 * 2.5 + 1e-9, "cabe en el cuadrado de " + P0.bx_cuad_uh);
  assert.match(U.material, /ULTRA VST/); assert.match(U.material, /pendiente/i);
  // masa de las pastillas con la densidad de la ficha (0,97)
  assert.equal(U.densidad, 0.97);
  const Hc = U.H, dC = U.d_torneado, hs = P0.bx_d_sp + 2 * P0.bx_c_sp;
  assert.ok(U.masa_unit < 0.97e-6 * Math.PI / 4 * dC * dC * Hc && U.masa_unit > 0.97e-6 * Math.PI / 4 * (dC * dC - 4 * hs * hs) * Hc, "masa unitaria con ρ = 0,97");
  assert.match(C.material, /A572 Gr\. 50/);
  // portador de 22 mm: torsión y ligamento con Fy 345 cumplen (FU < 1; rev. 7: 0,900 y 0,810); con A36 (Fy_bxc = 250) el ligamento no cumple
  const tor = A0.checks.find((c) => /Portador: corte por torsión/.test(c.name)), lig = A0.checks.find((c) => /Portador: ligamento junto a la pastilla/.test(c.name));
  assert.ok(tor.fu < 0.95 && lig.fu < 0.90, "torsión " + tor.fu + ", ligamento " + lig.fu);
  near(tor.cap, 345 / (P0.Nd * Math.sqrt(3)), 1e-12, "torsión con Fy 345");
  A0.checks.filter((c) => c.bx && /Portador|Pastillas/.test(c.name) && (c.kind === "fu" || c.kind === "geo")).forEach((c) => assert.ok(c.fu <= 1 + 1e-9, "A572: " + c.name + " FU " + c.fu));
  const Aa = BX.analyze(Object.assign({}, P0, { Fy_bxc: 250, Fu_bxc: 400 }), { noFEA: true });
  assert.ok(Aa.checks.some((c) => c.bx && /Portador: ligamento junto a la pastilla/.test(c.name) && c.fu > 1), "con A36 de 22 mm el ligamento no cumple");
  assert.match(Aa.bx.portador.material, /A36/);
  assert.equal(Aa.bx.portador.t, 22); assert.equal(Aa.bx.pastillas.H, 30);
});

test("BX: rev. 7 (290 t, 680/600 bar, todas las planchas A572 Gr. 50 y de 22 mm, atiesador 22): valores por defecto, filas y FU", () => {
  const TD = TT.defaults(), A = BX.A36, Nd = P0.Nd;
  assert.deepEqual([P0.W_tf, P0.p_relief, P0.p_alarm, P0.Fy, P0.Fu], [290, 680, 600, 345, 450]);
  for (const k of ["Fy_pin", "Fy_dog", "Fy_pp", "Fy_piv", "Fy_shoe", "Fy_cara", "Fy_cam", "Fy_camP", "Fy_surf", "Fu_bolt"]) assert.equal(P0[k], TD[k], "acero especial sin cambio: " + k);
  for (const k of ["pr", "base", "boxE", "bxc", "dbl"]) { assert.equal(P0["Fy_" + k], 0, "Fy_" + k + " = global"); assert.equal(P0["Fu_" + k], 0, "Fu_" + k); }
  for (const [k, v] of Object.entries(A.despues)) { assert.equal(P0[k], v, k); assert.equal(A.antes[k], TD[k], "antes = núcleo: " + k); }
  assert.deepEqual([P0.t_top, P0.t_bot, P0.t_pr, P0.t_base, P0.bx_tc, P0.pv_tbox, P0.pv_tl, P0.rib_t], [22, 22, 22, 22, 22, 22, 22, 22], "planchas de 22 mm");
  assert.deepEqual([P0.t_web, P0.t_rib, P0.h_boss, P0.t_ear, P0.rim_t], [8, 8, 70, 18, 10]);
  const Pold = BX.defaults({ a36: false }); for (const k of Object.keys(A.despues)) assert.equal(Pold[k], TD[k], "opción anterior: " + k);
  const by = (re) => A0.checks.find((c) => re.test(c.name));
  // atiesador de 22 (clave rib_t del núcleo) y refuerzo automático (≈ 45 mm en A572)
  assert.ok(by(/^Plancha base bajo el soporte del ojal E: atiesador tangencial 22 × \d+ mm: flexión/), "atiesador de 22");
  const tdM = /refuerzo de (\d+) mm/.exec(A0.checks.find((c) => /base de 22 mm con refuerzo de/.test(c.name)).name); assert.ok(tdM && +tdM[1] >= 40 && +tdM[1] <= 50, "refuerzo " + (tdM && tdM[1]));
  near(A0.R.Fstall, 432.6, 0.001, "fuerza de calado con 680 bar");
  const FS = Object.fromEntries(A0.R.cases.map((c) => [c.id, c.FS]));
  [["nom", 4.124], ["dis", 1.396], ["borde", 1.118], ["cont", 1.117], ["seco", 1.320]].forEach(([k, v]) => near(FS[k], v, 0.001, "FS " + k));
  // valores de la rev. 7 (sin FEA; docs/bx/README_BX.md §11). Las tapas E son lineales en p_relief: 1,006 con 700 bar → 0,977 con 680
  [[/^Tapas del cajón E: desgarro por corte hacia las paredes/, 0.999], [/^Tapas del cajón E \(orejas del pasador\): aplastamiento/, 0.977], [/^Alarma bajo el alivio/, 0.980],
   [/^Aplastamiento en el agujero del anillo$/, 0.900], [/bisel dentro del anillo/, 0.941], [/^Flexión \(biapoyado entre anillos/, 0.905], [/^Pasador vertical E: flexión/, 0.756],
   [/^Soporte del ojal E: flexión de las paredes/, 0.794], [/^Soporte del ojal E: CJP paredes–base/, 0.794], [/^BX · Portador: corte por torsión/, 0.900], [/^BX · Portador: ligamento junto/, 0.810],
   [/^BX · Pastillas: presión más sobrepresión por falta de planitud/, 0.747], [/^BX · Pastillas: valor PV en la pastilla más exigida/, 0.815],
   [/^Plancha base bajo el soporte del ojal E: atiesador tangencial 22/, 0.482], [/^Asiento del pivote con momento/, 0.653]].forEach(([re, v]) => {
    const c = by(re); assert.ok(c, String(re)); near(c.fu, v, 0.006, c.name.slice(0, 60)); });
  assert.equal(A0.checks.filter((c) => c.st === "fail").length, 0, "sin fallas");
  assert.equal(A0.verdict.estructura, true); assert.equal(A0.verdict.gira, true);
  // un solo espesor de anillo (22): sin filas BX de anillos distintos; con t_pr < t_top vuelven
  assert.equal(BX._int.ringRows(P0, A0.R, A0.checks).length, 0);
  assert.equal(BX._int.ringRows(Object.assign({}, P0, { t_top: 25 }), A0.R, A0.checks).length, 3);
  // base bajo el soporte E: la FEA independiente (mallas 20–35 mm; con 40 el sistema es singular) supera al núcleo: factor de penalización, no crédito
  const cr = A0.checks.filter((c) => c.bx && /ajuste por la FEA de Mindlin de la base/.test(c.name));
  assert.equal(cr.length, 4, "nom, dis, cal y retorno");
  const crC = cr.find((c) => /empuje a calado/.test(c.name)), crR = cr.find((c) => /atasco del retorno/.test(c.name));
  near(crC.k_tb, 0.962 / 0.831, 1e-9, "empuje"); near(crR.k_tb, 0.824 / 0.785, 1e-9, "retorno");
  near(crC.fu, 0.962, 0.006, "calado = envolvente de la FEA"); assert.ok(crR.fu >= 0.824 - 0.003, "retorno ≥ FEA " + crR.fu);
  cr.forEach((c) => { assert.ok(c.fu < 1, c.name + " " + c.fu); near(c.cap, 1.25 * 345 / Nd, 1e-12, "Fy 345"); });
  const sub = A0.checks.filter((c) => c.sustituida); assert.equal(sub.length, cr.length); sub.forEach((c) => assert.equal(c.st, "info"));
  // con t_base = 21 se interpola entre 20 (1,045 / 1,0) y 22; sin factor con t_base = 20
  const A21 = BX.analyze(Object.assign({}, P0, { t_base: 21 }), { noFEA: true }), r21 = A21.checks.find((c) => c.bx && /atasco del retorno/.test(c.name) && /FEA de Mindlin de la base/.test(c.name));
  near(r21.k_tb, (1 + 0.824 / 0.785) / 2, 1e-9, "interpolado");
  const A20 = BX.analyze(Object.assign({}, P0, { t_base: 20 }), { noFEA: true });
  assert.ok(!A20.checks.some((c) => c.sustituida || /FEA de Mindlin de la base/.test(c.name)));
  // la calidad por pieza sigue disponible (rev. 6): con el refuerzo A36 la CJP de las paredes E usa la menor
  const A6 = BX.analyze(Object.assign({}, P0, { Fy_dbl: 250, Fu_dbl: 400 }), { noFEA: true });
  near(A6.checks.find((c) => /^Soporte del ojal E: CJP paredes–base/.test(c.name)).fu, by(/^Soporte del ojal E: CJP paredes–base/).fu * 345 / 250, 1e-9, "CJP con refuerzo A36");
  // capacidad en el bloque bx exportado y en la tabla de fabricación
  const X = BX.exportBX(P0); assert.equal(X.capacidad_nominal_tf, 290); assert.match(X.revision, /290 t/);
  assert.ok(G0.fabricacion.some((f) => /Calidad del acero/.test(f.pieza) && /A572 Gr\. 50/.test(f.despues) && !/A36 \(Fy/.test(f.despues)));
  // masa (rev. 5: 4100 kg; rev. 6: 3843 kg; rev. 7: ≈ 3721 kg)
  near(A0.R.m.total, 3721, 0.003, "masa");
});

test("BX: cinemática y reenganche con la nueva δ (lámina de 3 mm) y las alturas de la rev. 5", () => {
  assert.ok(A0.R.K.ok); assert.equal(A0.verdict.gira, true);
  near(A0.R.hax, P0.h_disc / 2 + A0.R.ifc.delta, 1e-12, "eje del cilindro = h_disc/2 + δ");
  const giro = A0.checks.filter((c) => (c.sys === "giro" || /Uña|Placas-leva/.test(c.grp)) && (c.kind === "fu" || c.kind === "geo"));
  giro.forEach((c) => assert.ok(c.fu <= 1 + 1e-9 && c.st !== "fail", c.grp + " | " + c.name + " FU " + c.fu));
  ["Carrera requerida con margen", "Sincronía del retorno", "Flanco de reenganche", "Garra: en la toma", "Garra: salida del pasador", "Garra: retorno sin traba", "Bloque-uña libre del pasador siguiente",
   "Bloque-uña libre de los pasadores en el empuje guiado", "Placa-guía libre del seguidor", "Pasador Q fuera de la mesa", "Bloque-uña dentro de la luz libre", "Cuerpo del cilindro sobre la placa-guía (alzado)"].forEach((k) =>
    assert.ok(giro.some((c) => c.name.includes(k)), "fila de cinemática: " + k));
});

/* ---------- 3. Fórmulas ---------- */
test("BX: celda anular (borde interior empotrado, exterior guiado) frente a diferencias finitas", () => {
  const q = 1.7, a = 50, b = 80, D = 200000 * 8 ** 3 / (12 * (1 - 0.09)), nu = 0.3;
  const c = BX.cellPlate(q, a, b, D, nu);
  // Ecuación axisimétrica en la pendiente θ = w' por diferencias finitas centradas (tridiagonal), θ(a) = θ(b) = 0; M_r = −D(θ' + νθ/r); w(b) − w(a) = ∫θ dr.
  const n = 4000, h = (b - a) / n, A = [], B = [], Cc = [], Rhs = [];
  for (let i = 1; i < n; i++) { const r = a + i * h, Q = q * (r * r - b * b) / (2 * r);   // D·d/dr[(1/r)·d(rθ)/dr] = q·(r² − b²)/(2r) (corte nulo en el borde guiado b)
    // θ'' + θ'/r − θ/r² = Q/D
    A.push(1 / (h * h) - 1 / (2 * r * h)); B.push(-2 / (h * h) - 1 / (r * r)); Cc.push(1 / (h * h) + 1 / (2 * r * h)); Rhs.push(Q / D); }
  const m = n - 1, cp_ = new Array(m), dp = new Array(m), th = new Array(m);
  for (let i = 0; i < m; i++) { const den = B[i] - (i ? A[i] * cp_[i - 1] : 0); cp_[i] = Cc[i] / den; dp[i] = (Rhs[i] - (i ? A[i] * dp[i - 1] : 0)) / den; }
  for (let i = m - 1; i >= 0; i--) th[i] = dp[i] - (i < m - 1 ? cp_[i] * th[i + 1] : 0);
  const thAt = (i) => (i <= 0 || i >= n ? 0 : th[i - 1]);
  const Mr = (i) => { const r = a + i * h, d = (i === 0 ? (-3 * thAt(0) + 4 * thAt(1) - thAt(2)) / (2 * h) : i === n ? (3 * thAt(n) - 4 * thAt(n - 1) + thAt(n - 2)) / (2 * h) : (thAt(i + 1) - thAt(i - 1)) / (2 * h)); return -D * (d + nu * thAt(i) / r); };
  let w = 0; for (let i = 0; i < n; i++) w += (thAt(i) + thAt(i + 1)) / 2 * h;
  near(Math.abs(c.Ma), Math.abs(Mr(0)), 0.01, "M_r en el borde empotrado");
  near(Math.abs(c.Mb), Math.abs(Mr(n)), 0.01, "M_r en el borde guiado");
  near(Math.abs(c.w), Math.abs(w), 0.01, "flecha relativa");
});

test("BX: rigidez de Huth y fuerza térmica de borde frente a una cadena discreta de resortes", () => {
  const k = BX.huth(8, 193000, 16, 200000, 10);
  assert.ok(k > 1e5 && k < 4e5, "rigidez " + k);
  // franja radial: barra E·t·s/(1−ν²) sobre resortes k cada s_r; deformación libre ε(1+ν); semi-infinita (n grande): fuerza en el último resorte
  const E = 200000, t = 8, nu = 0.3, s = 150, sr = 150, eps = 1.3e-6 * 60, kb = k;
  const F = BX.edgeForce({ E, t, nu, eps, kb, st: s, sr });
  const EA = E * t * s / (1 - nu * nu), n = 200, kbar = EA / sr, e0 = eps * (1 + nu);
  // equilibrio de nudos: u_i, barra entre i e i+1 con fuerza kbar·(u_{i+1} − u_i − e0·sr); resorte k·u_i; nudo 0 en el centro (u = 0), nudo n en el borde libre
  const a = [], b = [], c = [], r = [];
  for (let i = 1; i <= n; i++) { const last = i === n; a.push(-kbar); b.push((last ? kbar : 2 * kbar) + kb); c.push(last ? 0 : -kbar); r.push(last ? kbar * e0 * sr : 0); }
  const m = n, cp_ = [], dp = [], u = new Array(m);
  for (let i = 0; i < m; i++) { const den = b[i] - (i ? a[i] * cp_[i - 1] : 0); cp_[i] = c[i] / den; dp[i] = (r[i] - (i ? a[i] * dp[i - 1] : 0)) / den; }
  for (let i = m - 1; i >= 0; i--) u[i] = dp[i] - (i < m - 1 ? cp_[i] * u[i + 1] : 0);
  near(F, kb * u[m - 1], 0.01, "fuerza del resorte de borde (fórmula cerrada de la cadena frente a la solución numérica)");
});

test("BX: equilibrio de presiones de las pastillas, presión ≥ q y PV con la velocidad del núcleo", () => {
  const U = G0.pastillas, Rr = A0.R;
  near(U.suma_N_kN, Rr.ND, 0.01, "Σ q·dA sobre las pastillas = N_D");
  assert.ok(U.p_max > Rr.q_max, "p_pastilla > q_máx (cobertura < 1)");
  assert.ok(U.cobertura > 0.4 && U.cobertura < 0.9);
  const vcyl = P0.Q_pump * 1e6 / 60 / (P0.n_cyl * Rr.A), w = vcyl / Rr.K.armMin;
  near(U.PV_max, Math.max(...U.lista.map((q) => q.p * q.r * w / 1000)), 1e-9, "PV");
});

test("BX: patrón radial con transferencia perimetral; la variante con agujeros de soldadura cumple la regla de un salto", () => {
  const Gr = G0, C = Gr.portador;   // por defecto: redondas, patrón elegido entre radial y triangular
  const Gq = BX.design(Object.assign({}, P0, { bx_forma: 1 }));   // la forma cuadrada queda disponible
  assert.equal(Gq.pastillas.forma, "cuadrada"); assert.equal(Gq.pastillas.d, null); assert.ok(Gq.pastillas.lado > 0 && Gq.pastillas.r_esquina > 0);
  assert.equal(Gr.pastillas.forma, "redonda"); assert.ok(Gr.pastillas.d > 0); assert.equal(Gr.pastillas.lado, null);
  assert.equal(C.patron.tipo, "radial");
  assert.equal(C.tapones.n, 0, "sin agujeros de soldadura por defecto");
  // separación mínima entre centros ≥ paso (ligamento ≥ lig)
  const L = Gr.pastillas.lista; let m = Infinity;
  for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) m = Math.min(m, Math.hypot(L[i].x - L[j].x, L[i].y - L[j].y));
  assert.ok(m >= C.paso - 1e-6, "separación " + m + " < paso " + C.paso);
  // variante triangular con agujeros de soldadura √7: un salto como máximo
  const Gt = BX.design(Object.assign({}, P0, { bx_forma: 0, bx_pat: 1, bx_nw: 7 }));
  assert.equal(Gt.portador.patron.tipo, "triangular");
  assert.equal(Gt.portador.patron.saltos_max, 1);
  assert.ok(Gt.portador.tapones.n > 0);
});

test("BX: interferencia en frío, montaje y caliente; tornillo de la pastilla fuera del camino del arrastre", () => {
  const U = G0.pastillas, f = U.ajuste;
  assert.ok(f.delta_min_20 >= -1e-9, "interferencia mínima a 20 °C ≥ 0");
  assert.ok(f.holgura_frio <= P0.bx_c_sp - 0.2 + 1e-9, "holgura en frío ≤ holgura del agujero del tornillo − 0,2");
  assert.ok(f.eps_caliente <= P0.bx_eps_max / 100 + 1e-12);
  near(f.d_dil_caliente, (P0.bx_al_uh * 1e-6 - P0.bx_al_st * 1e-6) * (P0.T_ifc_max - P0.T_ref) * (U.lado || U.d), 1e-9, "Δd caliente con α_UHMW = 190×10⁻⁶");
});

test("BX: tornillos del disco (modo 0): corte primario por el par (J3.7); térmica secundaria repartida por rigidez; membrana y pandeo del disco", () => {
  const A0 = A8(), G0 = A0.bx, T = G0.disco.tornillos;
  near(T.lista.reduce((s, b) => s + b.VT * b.r, 0) / 1e6, A0.R.TmaxTopes, 1e-9, "Σ V_T·r = T_calado");
  assert.ok(T.V_primario <= 0.9 * T.capV);
  assert.equal(T.dT_diseno, Math.max(P0.T_ifc_max - P0.T_ref, P0.T_ref - P0.T_ifc_min), "ΔT de servicio = máx(T_ifc,máx − T_ref; T_ref − T_ifc,mín) (20 °C de uso y 0 °C mínimo: 20 K)");
  assert.equal(T.Vth_anillos.length, T.anillos.length);
  assert.ok(T.Vth_anillos[T.Vth_anillos.length - 1] >= T.Vth_anillos[0], "el anillo exterior toma más");
  const prim = A0.checks.find((c) => /corte de diseño por el par/.test(c.name)), sec = A0.checks.find((c) => /componente térmica secundaria/.test(c.name));
  assert.equal(prim.kind, "fu"); assert.equal(sec.kind, "info");
  const th = G0.disco.termico; near(th.sigma_uniaxial, 193000 * 5.3e-6 * T.dT_diseno, 1e-9, "σ = E·Δα·ΔT (≈ 20 MPa con ΔT = 20 K)");
  ["rango frente a 2·Fy", "frente a Fy", "pandeo por la compresión térmica"].forEach((k) => { const c = A0.checks.find((x) => x.bx && x.name.includes(k)); assert.ok(c && c.st === "ok", k); });
  T.lista.forEach((b) => { assert.ok(Math.abs(b.y) >= P0.bx_c_cjp - 1e-9); });
});

test("BX: tabla de fabricación (antes → después, motivo y verificación) y JSON puro", () => {
  const F = G0.fabricacion;
  assert.ok(F.length >= 12);
  F.forEach((f) => { assert.ok(f.pieza && f.antes && f.despues && f.motivo && f.verificacion && f.estado, JSON.stringify(f)); });
  assert.ok(F.some((f) => f.estado === "se mantiene") && F.some((f) => f.estado === "simplificada") && F.some((f) => f.estado === "eliminada"));
  JSON.stringify(G0);
});

test("BX: agentes (validador, auditor, revisor cruzado y escenarios) sobre el módulo", () => {
  assert.equal(AGBX.validate(P0).filter((v) => v.lvl === "error").length, 0);
  const au = AGBX.audit(A0.checks); assert.ok(au.ok, JSON.stringify(au.missing.map((c) => c.name)));
  const cc = AGBX.crossCheck(A0); assert.ok(cc.length >= 5); cc.filter((c) => c.bx).forEach((c) => assert.ok(c.ok, c.name + " " + c.tool + " / " + c.indep));
  const sc = AGBX.scenarios(A0); assert.match(sc.ifaces[2].name, /BX/);
  assert.ok(AGBX.validate(Object.assign({}, P0, { bx_pat: 3 })).some((v) => v.lvl === "error"));
});

test("BX: análisis con FEA (mesa, flexión global, izaje con el portador) y escenario térmico a 80 °C", () => {
  const A = BX.analyze(P0);
  assert.ok(A.fea && A.fea.lift.vmMax > 0);
  assert.equal(A.verdict.gira, true);
  A.checks.filter((c) => c.st === "fail").forEach((c) => assert.fail("con FEA, falla: " + c.grp + " | " + c.name + " FU " + c.fu));   // rev. 7: todo cumple
  assert.equal(A.verdict.estructura, true);
  [[/^Plancha superior: global \+ local/, 0.692], [/^Plancha inferior: global \+ local/, 0.465]].forEach(([re, v]) => near(A.checks.find((c) => re.test(c.name)).fu, v, 0.006, String(re)));
  A.checks.filter((c) => /^Mesa/.test(c.grp) && c.kind === "fu" && isFinite(c.fu)).forEach((c) => assert.ok(c.fu <= 0.9 + 1e-9, "mesa A36: " + c.name + " FU " + c.fu));
  const th = BX.thermal(P0, { T: [20, 80] });
  const b = th.alternativas[0], b80 = b.byT.find((x) => x.T === 80), b20 = b.byT.find((x) => x.T === 20);
  assert.ok(b80.bx && b80.bx.filas.length > 10);
  assert.ok(b80.bx.fuEst >= b20.bx.fuEst, "a 80 °C empeora");
  const p80 = b80.bx.filas.find((r) => /presión máxima/.test(r.nombre));
  near(p80.cap, P0.p_uhmw * P0.kT_p_uh, 1e-9, "p_adm a 80 °C = k_p·p_adm");
});
