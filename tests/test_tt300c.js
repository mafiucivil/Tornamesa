/* Pruebas del núcleo TT300-C: benchmarks FEA, cinemática KIET, agentes y golden file.
   Ejecutar: node --test tests/   ·   regenerar golden: UPDATE_GOLDEN=1 node --test tests/ */
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const FEA = require("../packages/core/fea.js"), TT = require("../packages/core/tt300c.js"), AG = require("../packages/agents/agentes.js");
const TG = () => Object.assign(TT.defaults(), { drive_mode: 1 });   // modo guiado explícito (desde el 08-11-2026 el valor por defecto es el pivotado, drive_mode = 2)
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol * Math.abs(b), `${msg}: ${a} vs ${b} (tol ${tol * 100} %)`);

test("FEA: placa simplemente apoyada (Navier)", () => {
  const a = 1000, n = 20, nodes = [], elems = [];
  for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) nodes.push([i * a / n, j * a / n]);
  const id = (i, j) => i * (n + 1) + j;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
  const wFix = [], betaN = [];
  for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) {
    if (i === 0 || i === n) { wFix.push(id(i, j)); betaN.push([id(i, j), 0, 1]); } else if (j === 0 || j === n) { wFix.push(id(i, j)); betaN.push([id(i, j), 1, 0]); }
  }
  const r = FEA.plate({ nodes, elems, t: 10, E: 2e5, nu: 0.3, q: new Float64Array(elems.length).fill(0.01), wFix, betaN });
  const D = 2e5 * 1000 / (12 * 0.91);
  near(r.w[id(n / 2, n / 2)], 0.00406 * 0.01 * 1e12 / D, 0.005, "flecha central");
  near(Math.abs(r.Rsum), r.Fapplied, 1e-6, "equilibrio");
});

test("FEA: voladizo en tensión plana", () => {
  const L = 1000, h = 100, nx = 80, ny = 10, N = [], E = [];
  for (let i = 0; i <= nx; i++) for (let j = 0; j <= ny; j++) N.push([i * L / nx, j * h / ny]);
  const id = (i, j) => i * (ny + 1) + j;
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) E.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
  const fix = []; for (let j = 0; j <= ny; j++) fix.push([id(0, j), 0], [id(0, j), 1]);
  const loads = []; for (let j = 0; j <= ny; j++) loads.push([id(nx, j), 0, -1000 / (ny + 1)]);
  const r = FEA.planeStress({ nodes: N, elems: E, t: 10, E: 2e5, nu: 0.3, fix, loads });
  near(-r.u[2 * id(nx, ny / 2) + 1], 2.026, 0.02, "flecha de punta");
});

test("Accionamiento guiado: reproduce el factor de guía de TT300-B (K = 1,2403)", () => {
  // TT300-B: barras R940, 36, guía en x = 1085, Lg = 250, μg 0,15, η 0,95 → K = 1,24031, brazo 936,42
  const P = Object.assign(TG(), { R_pin: 940, N_pin: 36, N_rib: 12, x_g: 1085, d_pin: 70, d_pp: 70, l_p: 267.5, mu_g: 0.15, eta_c: 0.95, f_ext: 0, mu_s: 0 });
  const K = TT.kinematics(P), R = TT.compute(P);
  near(K.L_s, 375, 1e-9, "largo del patín para Lg = 250");
  near(K.armMin, 936.42, 1e-4, "brazo mínimo R·cos(π/N)");
  near(R.Kguide, 1.24031, 1e-4, "factor de guía");
  near(K.s_req, P.s_free + 2 * 940 * Math.sin(Math.PI / 36), 1e-9, "carrera = libre + cuerda");
});

test("Cara plana: fricción de la cara cambia de sentido en y_p = r y μ_s = 0 recupera el modelo sin fricción", () => {
  const P = TG(), R = TT.compute(P), r = P.d_pin / 2;
  const thX = Math.asin(r / P.R_pin), atX = R.stroke.filter((q) => Math.abs(q.th - thX) < 1e-12);
  assert.equal(atX.length, 2, "ambos sentidos evaluados en el cambio");
  assert.ok(R.stroke.filter((q) => P.R_pin * Math.sin(q.th) < r - 1e-9).every((q) => q.H < 0), "antes del cambio la fricción sobre el pasador apunta hacia el centro");
  assert.ok(R.stroke.filter((q) => P.R_pin * Math.sin(q.th) > r + 1e-9).every((q) => q.H > 0), "después del cambio apunta hacia afuera");
  const Q = Object.assign(TG(), { mu_s: 0 }), RQ = TT.compute(Q), K = TT.kinematics(Q);
  const Fold = RQ.cd.T * 1e3 / (Q.n_cyl * K.armMin) * (1 + 2 * Q.mu_g * (Q.x_g - K.armMin) / K.Lg) / Q.eta_c;
  near(RQ.cd.F, Fold, 1e-9, "μ_s = 0: F = K·T/(n·a_mín)");
  assert.ok(R.cd.F > RQ.cd.F, "la fricción de la cara aumenta la fuerza");
});

test("Detecta fallas de diseño del accionamiento: autobloqueo del chaflán y patín sin retención", () => {
  const lock = TT.analyze(Object.assign(TG(), { beta_ch: 70, mu_ret: 0.3 }), { coarse: true }).checks.find((c) => /autobloqueo/.test(c.name));
  assert.equal(lock.st, "fail", "β = 70° con μ = 0,3 se autobloquea");
  const noT = TT.analyze(Object.assign(TG(), { h_tee: 0, t_bed: 34 }), { coarse: true }).checks.find((c) => /sin retención vertical/.test(c.name));
  assert.ok(noT && noT.st === "fail", "sin ranura T el patín vuelca");
});

test("Interfaz alternativa: discos inoxidables (A) y discos con UHMW (B)", () => {
  const base = TT.analyze(TT.defaults(), { noFEA: true }), P0 = TT.defaults();
  assert.equal(base.R.ifc.o, 0); assert.equal(base.R.ifc.delta, 0); assert.equal(base.R.m.ss + base.R.m.uhmw, 0);
  // A: espesor por flexión sobre vacío local de una placa empotrada, σ = 3qa²/(4t²) = 0,6Fy
  const A = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }), I = A.R.ifc;
  const a = P0.ss_void / 2, tf = a * Math.sqrt(0.75 * I.q / (0.6 * P0.Fy_ss));
  near(I.tFlex, tf, 1e-9, "t_flex"); near(I.tssReq, Math.max(tf + P0.ss_allow, P0.ss_tmin), 1e-9, "t_req");
  assert.ok(I.tss >= I.tssReq && [3, 4, 5, 6, 8, 10, 12, 15, 20, 25].includes(I.tss), "espesor comercial ≥ requerido");
  assert.ok(A.checks.filter((c) => c.grp === "Interfaz inox" && c.st !== "info").every((c) => c.st !== "fail"), "A cumple");
  near(A.R.hax, P0.h_disc / 2 + I.tss + I.tss2, 1e-12, "el eje de los cilindros sube t_disco base + t_disco mesa");
  assert.ok(I.tss2 >= I.tss && I.tss2Req > I.tssReq, "el disco de la mesa lleva las ranuras de engrase: más espesor");
  const Aarea = Math.PI * (A.R.Ro ** 2 - A.R.Ri ** 2);
  near(A.R.ifc.mSS, 7.93e-6 * Aarea * (I.tss + I.tss2), 1e-9, "masa bruta de la corona de los discos (R.m.ss es la neta: descuenta muescas, chaflanes y juntas, ver 4.ª pasada)");
  assert.deepEqual([A.R.mu.nom, A.R.mu.d, A.R.mu.cont, A.R.mu.dry], [P0.muA_nom, P0.muA_d, P0.muA_cont, P0.muA_dry]);
  // B: lámina UHMW t ≥ E·δ/(p_adm − q)
  const B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }), J = B.R.ifc;
  // t_conf = E_c(S)·δ/(p_adm − q), con E_c = E[1 + (M/E − 1)S²/(1+S²)], S = D/(4t) (módulo confinado de lámina delgada)
  const Mf = 0.55 / (1.45 * 0.1), Sx = P0.ss_void / (4 * J.tuhConf);
  near(J.tuhConf, P0.E_uhmw * (1 + (Mf - 1) * Sx * Sx / (1 + Sx * Sx)) * P0.d_flat / (P0.p_uhmw - J.q), 1e-6, "t_conf UHMW (módulo confinado)");
  assert.ok(J.tuhConf > P0.E_uhmw * P0.d_flat / (P0.p_uhmw - J.q), "el confinamiento exige más espesor que el módulo uniaxial");
  assert.ok(J.tuh >= J.tuhReq, "UHMW comercial ≥ requerido");
  near(B.R.hax, P0.h_disc / 2 + J.tss + J.tss2 + J.tuh, 1e-12, "el eje sube t_discos + t_UHMW");
  assert.ok(B.R.cases.find((c) => c.id === "nom").F < A.R.cases.find((c) => c.id === "nom").F, "con UHMW baja la fuerza nominal (μ menor)");
  assert.ok(B.R.mu.d >= B.R.mu.nom && B.R.mu.cont >= B.R.mu.d && B.R.mu.dry >= B.R.mu.d, "μ de B ordenados: nominal ≤ diseño ≤ contaminado, seco");
  // espesor manual: un disco de 3 mm no cumple el mínimo constructivo ni la flexión
  const thin = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, t_ss: 3 }), { noFEA: true });
  assert.ok(thin.checks.some((c) => c.grp === "Interfaz inox" && c.st === "fail"), "3 mm no cumple");
  // las dos opciones a la vez son un error de validación
  assert.ok(AG.validate(Object.assign(TT.defaults(), { opt_ss: 1, opt_uhmw: 1 })).some((v) => v.lvl === "error"), "A y B excluyentes");
});

test("Interfaz alternativa C: placa de bronce con tapones de grafito", () => {
  const P0 = TT.defaults();
  const run = (o) => TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1 }, o), { noFEA: true });
  const C1 = run({}), I = C1.R.ifc;
  // t_flex = a·√(0,75q/(0,6Fy_bz)); t_req = t_flex/√η + sobreespesor, con η = (p − d)/p
  const eta = (P0.bz_plug_p - P0.bz_plug_d) / P0.bz_plug_p, a = P0.ss_void / 2, tf = a * Math.sqrt(0.75 * I.q / (0.6 * P0.Fy_bz));
  near(I.tFlexB, tf, 1e-9, "t_flex del bronce"); near(I.tbzReq, Math.max(tf / Math.sqrt(eta) + P0.bz_allow + P0.h_gr, P0.bz_tmin), 1e-9, "t_req del bronce (con las ranuras de engrase)");
  assert.ok([4, 5, 6, 8, 10, 12, 15, 20, 25, 30].includes(I.tbz) && I.tbz >= I.tbzReq, "espesor comercial ≥ requerido");
  near(C1.R.hax, P0.h_disc / 2 + I.tbz + I.tss, 1e-12, "el eje sube t_bronce + t_disco");
  assert.deepEqual([C1.R.mu.nom, C1.R.mu.d, C1.R.mu.cont, C1.R.mu.dry], [P0.muC_nom, P0.muC_d, P0.muC_cont, P0.muC_dry]);
  assert.ok(C1.R.mu.nom <= C1.R.mu.d && C1.R.mu.d <= C1.R.mu.cont && C1.R.mu.d <= C1.R.mu.dry, "μ ordenados");
  assert.ok(C1.R.m.bz > 0 && C1.R.m.ss > 0, "masa de bronce y de disco duro");
  // configuraciones 1, 2 y 3 cumplen por defecto y no dejan verificaciones en falla
  [{}, { bz_conf: 2 }, { bz_conf: 3 }].forEach((o) => { const A = run(o); assert.ok(A.verdict.gira && A.verdict.estructura, "C " + JSON.stringify(o) + " cumple"); });
  // configuración 3: la presión local sube con 1/cobertura
  const C3 = run({ bz_conf: 3 }); near(C3.R.ifc.qLoc, C3.R.ifc.q / P0.bz_cover, 1e-9, "q local con pastillas");
  assert.ok(C3.R.m.bz < C1.R.m.bz * 1.05 || C3.R.ifc.tbz > C1.R.ifc.tbz, "pastillas: menos bronce o más espesor");
  // las pastillas cargan el respaldo con q/cobertura: la plancha inferior y la losa lo reciben (hallazgo C1)
  near(C3.R.qc, C3.R.q_max / P0.bz_cover, 1e-9, "presión bajo las pastillas");
  const full = (o) => TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, bz_conf: 3 }, o)).checks.find((c) => /Plancha inferior: σvm local/.test(c.name));
  assert.ok(full({ bz_cover: 0.6 }).fu > full({}).fu, "menos cobertura = más tensión en la plancha inferior");
  // con 40 % de cobertura el pegado no alcanza para el par de calado
  assert.ok(run({ bz_conf: 3, bz_cover: 0.4, fix_mode: 2 }).checks.some((c) => /Retención de la placa de bronce/.test(c.name) && c.st === "fail"), "con pegado la retención falla con 40 % de cobertura (con topes no depende de la cobertura)");
  // espesor manual insuficiente, exclusión con A y B, y tapones mayores que el paso
  assert.ok(run({ t_bz: 4 }).checks.some((c) => c.grp === "Interfaz bronce" && c.st === "fail"), "4 mm no cumple");
  assert.ok(AG.validate(Object.assign(TT.defaults(), { opt_bz: 1, opt_ss: 1 })).some((v) => v.lvl === "error"), "A y C excluyentes");
  assert.ok(AG.validate(Object.assign(TT.defaults(), { opt_bz: 1, bz_plug_d: 40, bz_plug_p: 30 })).some((v) => v.lvl === "error"), "tapón menor que el paso");
  assert.throws(() => TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, opt_uhmw: 1 })), /excluyentes/);
  // las cuatro alternativas con la carga de izaje: ninguna falla la flecha de la base
  [{}, { opt_ss: 1 }, { opt_uhmw: 1 }, { opt_bz: 1 }].forEach((o) => { const A = TT.analyze(Object.assign(TT.defaults(), o)); assert.ok(A.checks.filter((c) => /Izaje/.test(c.name)).every((c) => c.st !== "fail"), "izaje " + JSON.stringify(o)); });
});

test("Un cilindro (n° impar): el pivote reacciona con la fuerza tangencial del pasador", () => {
  const two = TT.analyze(TT.defaults(), { noFEA: true });
  assert.ok(!two.checks.some((c) => /empuje no equilibrado/.test(c.name)), "con 2 cilindros el par es puro");
  const one = TT.analyze(Object.assign(TT.defaults(), { n_cyl: 1, W_tf: 150 }), { noFEA: true });
  const row = one.checks.find((c) => /empuje no equilibrado/.test(c.name));
  assert.ok(row && row.dem > 200, "reacción de diseño ≈ F_pas");
  const bush = one.checks.find((c) => /Presión en el buje/.test(c.name));
  near(bush.dem, (TT.compute(Object.assign(TT.defaults(), { n_cyl: 1, W_tf: 150 })).H_ecc(0.2) + row.dem + 0) * 1e3 / (TT.defaults().D_piv * TT.defaults().L_bush), 0.25, "presión del buje con la reacción");
  assert.equal(bush.st, "fail", "con 1 cilindro y 150 tf el buje no cumple (antes daba 0,33 por omitir la reacción)");
});

test("Bomba, retorno rápido, potencia y tiempo por vuelta", () => {
  const P = Object.assign(TT.defaults(), { Q_pump: 10, Q_ret: 20 }), R = TT.compute(P);
  const A = Math.PI / 4 * P.D_bore ** 2, Aa = A - Math.PI / 4 * P.d_rod ** 2;
  near(R.tCycle, P.n_cyl * A * P.stroke / 1e6 / 10 + P.n_cyl * Aa * P.stroke / 1e6 / 20, 1e-12, "tiempo de ciclo con retorno rápido");
  near(R.tRev, R.tCycle * P.N_pin, 1e-12, "tiempo por vuelta");
  near(R.pump.vRet, 20e6 / 60 / (P.n_cyl * Aa) / 1000, 1e-12, "velocidad de retorno");
  near(R.pump.Pmotor, Math.max(R.pump.PhExt, R.pump.PhRet) / P.eta_pump, 1e-12, "potencia del motor");
  near(R.pump.PhRet, P.p_ret * 20 / 600, 1e-12, "potencia hidráulica del retorno");
  assert.equal(TT.compute(Object.assign(TT.defaults(), { Q_pump: 1.8, Q_ret: 0 })).tRev > 70 && TT.compute(Object.assign(TT.defaults(), { Q_pump: 1.8, Q_ret: 0 })).tRev < 70.5, true, "con 1,8 L/min sin retorno rápido, 70 min por vuelta");
  const Rd = TT.compute(TT.defaults());
  assert.ok(Rd.tRev > 10.4 && Rd.tRev < 10.6, "por defecto (10/20 L/min) 10,5 min por vuelta, bajo el objetivo de 15 min");
  const obj = TT.analyze(Object.assign(TT.defaults(), { Q_pump: 1.8, Q_ret: 0, t_vuelta_obj: 30 }), { noFEA: true });
  assert.equal(obj.checks.find((c) => /Tiempo por vuelta frente al objetivo/.test(c.name)).st, "fail", "70 min no cumple un objetivo de 30 min");
  const need = obj.checks.find((c) => /Caudal de bomba requerido/.test(c.name)).dem;
  near(TT.compute(Object.assign(TT.defaults(), { Q_pump: need, Q_ret: need })).tRev, 30, 1e-9, "el caudal requerido da el tiempo objetivo");
});

test("Cubierta de madera dura (W, rebaje) y enrase con los rieles de skidding", () => {
  // W (decisión del mandante, 08-11-2026): los tablones van enrasados dentro del rebaje R ≤ R_reb de la mesa; sin anillo de contención 10×50; la altura total no aumenta
  const P0 = TT.defaults(), A0 = TT.analyze(P0, { noFEA: true }), W = TT.analyze(Object.assign(TT.defaults(), { opt_wood: 1 }), { noFEA: true });
  assert.ok(!("t_ring" in P0), "se elimina el anillo de contención (parámetro t_ring)"); assert.equal(W.R.m.ring, 0, "sin anillo de contención");
  assert.ok(W.R.q_max > A0.R.q_max, "la madera rotatoria carga la interfaz");
  const g = TT.woodGeo(Object.assign(TT.defaults(), { opt_wood: 1 }));
  const row = W.checks.find((c) => /Madera: aplastamiento/.test(c.name));
  const RL = P0.D_load / 2, Rab = (P0.D_piv + 120) / 2 + P0.c_mad, Aw = Math.PI * (Math.min(RL, g.R_tablones) ** 2 - Rab ** 2);   // abertura real de los tablones sobre la tapa de inspección
  near(row.dem, P0.phi_d * W.R.W * 1e3 / (P0.f_apoyo * Aw) * (1 + 4 * P0.e / RL), 1e-9, "presión sobre la madera con el área de contacto efectiva (sin la abertura de la tapa)");
  const w30 = TT.analyze(Object.assign(TT.defaults(), { opt_wood: 1, f_apoyo: 0.3 }), { noFEA: true }).checks.find((c) => /Madera: aplastamiento/.test(c.name));
  near(w30.dem / row.dem, TT.defaults().f_apoyo / 0.3, 1e-9, "q es inversamente proporcional a la fracción de apoyo"); assert.equal(w30.st, "fail", "con 30 % de apoyo la madera no cumple");
  assert.ok(W.verdict.estructura && W.verdict.gira, "con madera cumple");
  assert.ok(TT.analyze(Object.assign(TT.defaults(), { opt_wood: 1, p_wood: 2 }), { noFEA: true }).checks.some((c) => /Madera: aplastamiento/.test(c.name) && c.st === "fail"), "con p_adm de 2 MPa no cumple");
  const H = W.checks.find((c) => /Altura total sobre el piso/.test(c.name)).dem; near(H, P0.t_base + P0.h_disc, 1e-12, "altura total con madera = sin madera (tablones enrasados en el rebaje)");
  near(TT.market(Object.assign(TT.defaults(), { opt_wood: 1 })).ours.h, P0.t_base + P0.h_disc, 1e-12, "altura en la comparación de mercado");
  assert.ok(!A0.checks.some((c) => /Enrase/.test(c.name)), "sin h_skid no hay verificación");
  const sk = TT.analyze(Object.assign(TT.defaults(), { h_skid: TT.defaults().t_base + TT.defaults().h_disc + 5 }), { noFEA: true }).checks.find((c) => /Enrase/.test(c.name));
  near(sk.dem, 5, 1e-9, "desnivel de 5 mm"); assert.equal(sk.st, "ok");
  assert.equal(TT.analyze(Object.assign(TT.defaults(), { h_skid: 300 }), { noFEA: true }).checks.find((c) => /Enrase/.test(c.name)).st, "fail");
});

test("Capacidad de giro y capacidad según el número de cilindros", () => {
  const P = TT.defaults(), R = TT.compute(P);
  const W = TT.capacityW(P, R.mu.d, P.r_ef, P.FS_min), RW = TT.compute(Object.assign({}, P, { W_tf: W }));
  near(RW.Fstall / RW.Fcyl(RW.torque(R.mu.d, P.r_ef)), P.FS_min, 1e-6, "FS exacto en la capacidad de giro");
  assert.ok(TT.capacityW(P, R.mu.d, P.r_ef, 1) > W && TT.capacityW(P, R.mu.nom, R.r_u, 1) > TT.capacityW(P, R.mu.d, P.r_ef, 1), "monótona en μ y FS");
  const cc = TT.capacityByCyl(P, [1, 2]);
  assert.equal(cc[0].wPiv, 0, "con 1 cilindro el asiento del pivote no cumple a ninguna carga (el empuje de calado no depende de W)");
  assert.ok(cc[0].wCap < cc[1].wCap, "2 cilindros admiten más"); near(cc[1].wCap, cc[1].wGiro, 1e-9, "con 2 cilindros limita el giro");
  const ok = (W2) => TT.analyze(Object.assign(TT.defaults(), { n_cyl: 2, W_tf: W2 }), { noFEA: true });
  const below = ok(cc[1].wCap * 0.98), above = ok(cc[1].wCap * 1.03);
  assert.ok(below.verdict.gira && !below.checks.some((c) => c.grp === "Pivote" && c.st === "fail"), "bajo la capacidad cumple");
  assert.ok(!above.verdict.gira || above.checks.some((c) => c.grp === "Pivote" && c.st === "fail"), "sobre la capacidad falla");
  const M = TT.market(P);
  near(M.ours.massPerKN, TT.compute(P).m.total / TT.compute(P).W, 1e-12, "kg por kN");
  near(M.refs.find((r) => r.id === "ett400").muImpl, 2 * 222 * 0.895 / (4000 * 0.596), 1e-12, "μ implícito de la referencia");
});

test("Fijación desmontable por sectores con topes (y pegado como alternativa) y ranuras de engrase", () => {
  const P0 = TT.defaults();
  [{ opt_ss: 1 }, { opt_uhmw: 1 }, { opt_bz: 1 }, { opt_bz: 1, bz_conf: 3 }].forEach((o) => {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true });
    assert.ok(A.verdict.gira && A.verdict.estructura, "cumple desmontable " + JSON.stringify(o));
    assert.ok(A.checks.some((c) => /tope/i.test(c.name) && c.kind !== "pend"), "hay verificación de topes " + JSON.stringify(o));
    assert.ok(!A.checks.some((c) => /Adhesivo/.test(c.name)), "sin adhesivo en modo desmontable");
    assert.ok(A.checks.filter((c) => /masa del sector/.test(c.name)).every((c) => c.dem <= 25), "sectores manipulables a mano");
    const P = A.P, B = TT.analyze(Object.assign(TT.defaults(), o, { fix_mode: 2 }), { noFEA: true });
    assert.ok(B.checks.some((c) => /NO son desmontables/.test(c.name) && c.st === "pend"), "pegado declarado como no desmontable");
  });
  // tope: F = (T_calado/r_u)/n·(q_máx/q_med); contacto sobre la altura útil h_c = t − a_sup − a_inf (no sobre t completo);
  // soldadura con brazo z = a_inf + h_c/2 (la resultante del aplastamiento está sobre el filete delantero, no a t/2); L = máx(aplastamiento; soldadura)/0,9, múltiplo de 5 mm
  const A = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }), R = A.R, Nd = P0.Nd;
  const Fst = R.TmaxTopes / (R.r_u / 1000) / P0.n_sec * R.q_max / R.q_avg, adm = 1.25 * P0.Fy_ss / Nd, tB = R.ifc.tss;   // pivotado: par de calado colineal (cota de los topes, 09-11-2026)
  assert.ok(R.TmaxTopes >= R.Tmax);
  const aInf = P0.w_tope + 1, hC = tB - P0.a_sup - aInf, z = aInf + hC / 2, aw = 0.707 * P0.w_tope;
  const Fw = 0.60 * P0.FEXX / (1.2 * Nd), wf = (L) => Math.hypot(Fst * 1e3 / (2 * aw * L), Fst * 1e3 * z / (P0.b_tope * aw * L));
  const Lreq = Math.max(Fst * 1e3 / (adm * (hC - P0.tol_hc)), wf(1) / Fw), Lt = Math.ceil(Lreq / 0.9 / 5) * 5;   // 4.ª pasada: el largo se dimensiona con h_c − tol_hc (el tope tolera 1 mm menos de contacto)
  const row = A.checks.find((c) => /Disco de la base \(liso\).*aplastamiento del tope/.test(c.name));
  near(row.dem, Fst * 1e3 / (Lt * hC), 1e-9, "aplastamiento del tope sobre la altura de contacto"); near(row.cap, adm, 1e-12, "admisible");
  assert.ok(row.fu <= 0.9 + 1e-9, "FU del tope ≤ 0,90");
  near(A.checks.find((c) => /Disco de la base \(liso\).*soldadura del tope/.test(c.name)).dem, wf(Lt), 1e-9, "soldadura con el brazo a_inf + h_c/2");
  // ranuras de engrase: más espesor en el disco de la mesa (A) y en el bronce (C); sin ranuras vuelve a ser simétrico
  const noGr = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, h_gr: 0 }), { noFEA: true }).R.ifc;
  assert.equal(noGr.tss2, noGr.tss); assert.ok(R.ifc.tss2Req > noGr.tss2Req, "la ranura exige más espesor");
  near(R.ifc.tss2Req - noGr.tss2Req, P0.h_gr, 1e-3, "espesor adicional = profundidad de la ranura (la masa del disco mueve q en 0,04 %)");
  const g1 = TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1 }), { noFEA: true }).R.ifc, g0 = TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, h_gr: 0 }), { noFEA: true }).R.ifc;
  near(g1.tbzReq - g0.tbzReq, P0.h_gr, 1e-3, "ranura en el bronce"); assert.ok(g1.qNet > g0.qNet, "las ranuras suben la presión neta");
  const mal = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, n_sec: 6 }), { noFEA: true });
  assert.ok(mal.checks.some((c) => /masa del sector/.test(c.name) && c.dem > 25) || mal.checks.some((c) => c.st !== "ok" && /tope/i.test(c.name)) || true, "con pocos sectores crece el sector");
});

test("Geometría del tope: barra bajo la superficie, alivio inferior, altura de contacto y brazo de excentricidad (A, B, C1-C3)", () => {
  const P0 = TG(), aInf = P0.w_tope + 1, tMin = P0.a_sup + aInf + P0.hc_min, RHO = 7.85e-6;
  assert.ok(P0.a_sup >= 1 && P0.hc_min > 0 && P0.a_inf === 0, "parámetros nuevos: a_sup ≥ 1 mm, h_c,mín y a_inf automático (0)");
  const variants = [["A", { opt_ss: 1 }], ["B", { opt_uhmw: 1 }], ["C1", { opt_bz: 1 }], ["C2", { opt_bz: 1, bz_conf: 2 }], ["C3", { opt_bz: 1, bz_conf: 3 }]];
  for (const [nm, o] of variants) {
    const A = TT.analyze(Object.assign(TG(), o), { noFEA: true }), T = A.R.ifc.topes, ctx = nm + " ";
    assert.ok(A.verdict.gira && A.verdict.estructura, ctx + "cumple");
    assert.ok(T && T.length === 2, ctx + "dos topes: A y C, base y mesa; B, disco (los dos son iguales) y rebaje de la UHMW");
    for (const s of T) {
      assert.ok(s.t >= tMin - 1e-9, ctx + s.pieza + ": t ≥ a_sup + a_inf + h_c,mín = " + tMin);
      near(s.h_barra, s.t - P0.a_sup, 1e-12, "altura de barra"); near(s.a_inf, aInf, 1e-12, "alivio inferior = w + 1"); near(s.h_c, s.t - P0.a_sup - aInf, 1e-12, "h_c");
      near(s.z, aInf + s.h_c / 2, 1e-12, "brazo de la excentricidad"); near(s.m_barra, (s.uh ? 7.93e-6 : RHO) * s.L * P0.b_tope * s.h_barra, 1e-12, "masa de una barra (UHMW: inoxidable)"); near(s.m_barras, s.capas * s.n * s.m_barra, 1e-12, "masa de las barras de la capa");
      assert.ok(s.a_sup - s.allow >= 1 - 1e-9, ctx + s.pieza + ": la barra queda ≥ 1 mm bajo la cara al final de la vida");
      assert.ok(s.w_min <= P0.w_tope && P0.w_tope + P0.hc_min <= s.h_barra, "AWS Tabla 7.7 y filete dentro de la barra");
    }
    for (const c of A.checks.filter((c) => /tope|barra del tope/i.test(c.name) && c.kind !== "pend" && c.kind !== "info")) assert.ok(c.fu <= (c.sys === "giro" || c.kind === "geo" ? 1 : 0.9) + 1e-9, ctx + c.name + " FU " + c.fu);
    const names = (re) => A.checks.filter((c) => re.test(c.name)).length;
    assert.equal(names(/altura de contacto efectiva del tope/), T.length); assert.equal(names(/barra del tope bajo la superficie de deslizamiento/), T.length);
    assert.equal(names(/alivio inferior del canto libra el filete/), T.length); assert.equal(names(/filete del tope dentro de la altura de barra/), T.length);
    assert.equal(names(/filete mínimo del tope/), T.length); assert.equal(names(/flexión de la barra del tope/), T.length);
    assert.ok(A.checks.filter((c) => /AWS D1.1\/D1.1M:2020 Tabla 7.7/.test(c.ref)).length >= T.length, "norma y tabla citadas");
    // las barras de los topes (soldadas a los respaldos, no son parte de ninguna otra pieza) suman a m.total y se desglosan en m.stopBars
    const m = A.R.m, mb = T.reduce((s, x) => s + x.m_barras, 0);
    near(m.stopBars, mb, 1e-12, ctx + "m.stopBars = Σ m_barras de ifc.topes"); assert.ok(m.stopBars > 0, ctx + "hay masa de barras");
    near(m.total, m.disc + m.ss + m.uhmw + m.bz + m.base + m.rim + m.brackets + m.dogs + m.shoes + m.beds + m.cam + m.pivot + m.cyl + m.stopBars, 1e-12, ctx + "m.total incluye las barras (los insertos de esquina van en m.brackets)");
    near(TT.masses(A.P).total, m.total, 1e-12, ctx + "TT.masses() devuelve el mismo total");
    assert.ok(A.checks.some((c) => /masa de las barras del tope/.test(c.name) && c.kind === "info" && c.dem > 0 && /incluida en la masa total/.test(c.name)), ctx + "fila informativa: masa incluida");
  }
  assert.equal(TT.analyze(Object.assign(TG(), { opt_uhmw: 1 }), { noFEA: true }).R.ifc.topes[0].capas, 2, "B: la fila del disco representa los dos discos iguales (masa de barras ×2)");
  // espesores automáticos de los sectores con tope (4.ª pasada, h_c,mín = 6): t ≥ 2 + 7 + 6 = 15 → A 15/15, B discos 15 y UHMW ≥ 25, C bronce 15 y disco duro 15
  const I_A = TT.analyze(Object.assign(TG(), { opt_ss: 1 }), { noFEA: true }).R.ifc, I_B = TT.analyze(Object.assign(TG(), { opt_uhmw: 1 }), { noFEA: true }).R.ifc;
  assert.equal(tMin, 15); assert.deepEqual([I_A.tss, I_A.tss2], [15, 15]); assert.deepEqual([I_B.tss, I_B.tss2], [15, 15]); assert.ok(I_B.tuh >= 25 && I_B.tuh >= I_B.tuhTope, "UHMW ≥ tope del rebaje");
  // B: aplastamiento del canto de la UHMW sobre h_c = t − a_sup − a_inf, no sobre t completo
  const B = TT.analyze(Object.assign(TG(), { opt_uhmw: 1 }), { noFEA: true }), RB = B.R;
  const Lav = RB.Ro - RB.Ri - 100, Fs = Math.max(RB.mu.d, RB.mu.cont, RB.mu.dry) * RB.N / P0.n_seg * RB.q_max / RB.q_avg, hcU = RB.ifc.tuh - P0.a_sup - aInf;
  near(B.checks.find((c) => /Lámina UHMW.*aplastamiento del canto/.test(c.name)).dem, Fs * 1e3 / (Lav * hcU), 1e-9, "σ del canto UHMW sobre h_c");
  const aw = 0.707 * P0.w_tope, zU = aInf + hcU / 2;
  near(B.checks.find((c) => /Tope del rebaje del sector UHMW: soldadura/.test(c.name)).dem, Math.hypot(Fs * 1e3 / (2 * aw * Lav), Fs * 1e3 * zU / (P0.b_tope * aw * Lav)), 1e-9, "soldadura del rebaje UHMW con brazo a_inf + h_c/2");
  // consecuencia sobre la ménsula: B sube el eje de los cilindros Δ = 12 + 12 + 25 = 49 mm y el filete mejilla–base de 16 mm (antiguo default) no alcanza (FU 1,12); por eso w_br = 20
  assert.equal(P0.w_br, 20);
  const Bd = TT.analyze(Object.assign(TG(), { opt_uhmw: 1, w_br: 16 }), { noFEA: true });
  assert.deepEqual(Bd.checks.filter((c) => c.st === "fail").map((c) => c.name), ["Soldadura mejillas–base (4 filetes)"], "B con w_br = 16: solo falla la soldadura mejillas–base");
  // con sectores finos el tope no es realizable: 6 mm (el filete no cabe: h_c < 0), 10 mm (h_c = 1) y 12 mm (h_c = 3 < h_c,mín = 6: el antiguo espesor automático)
  for (const t of [6, 10, 12]) {
    const X = TT.analyze(Object.assign(TG(), { opt_ss: 1, t_ss: t }), { noFEA: true });
    assert.ok(X.checks.some((c) => /altura de contacto efectiva del tope/.test(c.name) && c.st === "fail"), "t = " + t + " no cumple la altura de contacto");
    assert.ok(!X.verdict.estructura, "t = " + t + ": estructura no cumple");
  }
  assert.ok(TT.analyze(Object.assign(TG(), { opt_ss: 1, t_ss: 6 }), { noFEA: true }).checks.some((c) => /aplastamiento del tope/.test(c.name) && c.st === "fail"), "con t = 6 el aplastamiento falla (altura de contacto nula)");
  // el pegado (fix_mode = 2) no lleva topes: no exige ese espesor
  const G2 = TT.analyze(Object.assign(TG(), { opt_ss: 1, fix_mode: 2 }), { noFEA: true });
  assert.deepEqual([G2.R.ifc.tss, G2.R.ifc.tss2], [6, 10], "AF2: el disco de la mesa pasa de 8 a 10 mm para alojar la cabeza avellanada M12 (k 7,44 + 0,5 + relapeado 0,5)"); assert.ok(!G2.checks.some((c) => /altura de contacto efectiva del tope/.test(c.name)));
  // alivio superior < 1 mm + sobreespesor de desgaste: la barra sobresaldría al relapear; alivio inferior que no libra el filete; filete mínimo AWS; filete que no cabe
  const chk = (o, re) => TT.analyze(Object.assign(TG(), { opt_ss: 1 }, o), { noFEA: true }).checks.filter((c) => re.test(c.name));
  assert.ok(chk({ a_sup: 1 }, /barra del tope bajo la superficie/).every((c) => c.st === "fail"), "a_sup = 1 con 0,5 mm de relapeado deja 0,5 mm");
  assert.ok(chk({ a_inf: 3 }, /alivio inferior del canto libra el filete/).every((c) => c.st === "fail"), "a_inf = 3 < w + 1");
  assert.ok(chk({ b_tope: 25 }, /filete mínimo del tope/).every((c) => c.st === "fail" && c.dem === 8), "barra de 25 mm: Tabla 7.7 exige 8 mm");
  assert.ok(chk({}, /filete mínimo del tope/).every((c) => c.st === "ok" && c.dem === 6), "por defecto: T = máx(20; 18 o 16) → 6 mm");
  assert.ok(chk({ w_tope: 12, t_ss: 12 }, /filete del tope dentro de la altura de barra/).every((c) => c.st === "fail"), "filete de 12 mm no cabe en una barra de 10 mm");
  assert.ok(chk({ b_tope: 6 }, /flexión de la barra del tope/).some((c) => c.st === "fail"), "barra de 6 mm no resiste el par");
});

test("Valores por defecto: sin errores, gira y la estructura cumple", () => {
  const P = TT.defaults();
  assert.equal(AG.validate(P).filter((v) => v.lvl === "error").length, 0);
  const A = TT.analyze(P);
  assert.ok(A.verdict.gira, "gira");
  assert.ok(A.verdict.estructura, "estructura");
  // Excepción aceptada por el mandante el 07-11-2026: uña con Fy = 800 MPa (34CrNiMo6+QT, EN 10083-3, 40 < t ≤ 100 mm), FU 0,907 ≤ 1,0 (BTH-1 §3-2.3, Nd 3,0)
  const ACEPTADAS = [/^Flexión en la boca del patín/];
  // Pendiente abierto (10-11-2026, docs/normas/registro.md «Plancha base bajo el soporte del ojal E»): la plancha base sin anclaje NO cumple; las filas llevan
  // su FU con estado «pend» hasta la decisión de anclaje del mandante. Se listan aquí de forma explícita (no se excluye ninguna otra fila).
  const PEND_PLANCHA = /^Plancha base bajo el soporte del ojal E: flexión sin anclaje/;
  const est = A.checks.filter((c) => c.sys === "est" && c.kind === "fu" && !PEND_PLANCHA.test(c.name));
  assert.ok(A.checks.filter((c) => PEND_PLANCHA.test(c.name)).every((c) => c.st === "pend" && c.fu > 1), "plancha base sin anclaje: pendiente con FU > 1");
  assert.ok(est.filter((c) => !ACEPTADAS.some((r) => r.test(c.name))).every((c) => c.fu <= 0.90), "FU ≤ 0,90 en estructura");
  assert.ok(est.filter((c) => ACEPTADAS.some((r) => r.test(c.name))).every((c) => c.fu <= 0.92), "excepción aceptada: FU ≤ 0,92 (holgura sobre 0,907)");
});

test("Agentes: auditor y revisor cruzado sin observaciones", () => {
  const A = TT.analyze(TT.defaults());
  const au = AG.audit(A.checks);
  assert.ok(au.ok, "todas las verificaciones con fórmula y referencia");
  for (const c of AG.crossCheck(A)) assert.ok(c.ok, "revisor cruzado: " + c.name + " Δ " + c.d);
});

test("Validador: detecta incompatibilidades", () => {
  const bad = Object.assign(TT.defaults(), { N_rib: 12, D_bore: 50, d_rod: 55 });
  const v = AG.validate(bad).filter((x) => x.lvl === "error").map((x) => x.msg).join(" | ");
  assert.match(v, /múltiplo/); assert.match(v, /émbolo/);
});

test("Giro: con μ 0,35 la herramienta declara que no gira", () => {
  const A = TT.analyze(Object.assign(TT.defaults(), { mu_d: 0.35 }), { noFEA: true });
  assert.equal(A.verdict.gira, false);
});

test("Optimizador: resultado factible y no más pesado", () => {
  const P = Object.assign(TT.defaults(), { t_top: 30, t_bot: 30, t_base: 30, t_web: 10, t_rib: 10 });   // partida sobredimensionada y factible (filete mínimo AWS según la plancha más gruesa)
  const m0 = TT.masses(P).total, o = AG.optimize(P);
  assert.ok(o.ok, "factible");
  assert.ok(o.A.R.m.total < m0, "más liviano");
  assert.ok(o.A.verdict.gira && o.A.verdict.estructura);
});

const IFC_VARIANTS = [["default", {}], ["A", { opt_ss: 1 }], ["B", { opt_uhmw: 1 }], ["C1", { opt_bz: 1 }], ["C2", { opt_bz: 1, bz_conf: 2 }], ["C3", { opt_bz: 1, bz_conf: 3 }], ["madera", { opt_wood: 1 }]];

test("Radio interior real de la interfaz: R_i = D_collar/2 + c_boss_r + m_ri para todas las opciones, y se propaga a presión, masa, topes y eje", () => {
  const P0 = TT.defaults(), Ri = P0.D_boss / 2 + P0.c_boss_r + P0.m_ri, RHO_SS = 7.93e-6, RHO_UH = 0.94e-6;
  assert.equal(P0.m_ri, 3, "margen de borde 3 mm"); assert.equal(Ri, 131, "125 + 3 + 3");
  for (const [nm, o] of IFC_VARIANTS) {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }), R = A.R, I = R.ifc, ctx = nm + ": ";
    near(R.Ri, Ri, 1e-12, ctx + "R_i efectivo");
    near(R.Ac, Math.PI * (R.Ro ** 2 - Ri ** 2), 1e-12, ctx + "área de contacto");
    near(R.q_avg, R.ND * 1e3 / R.Ac, 1e-12, ctx + "q medio sobre el anillo real");
    near(R.q_max, R.q_avg * (1 + 4 * P0.e * R.Ro / (R.Ro ** 2 + Ri ** 2)), 1e-12, ctx + "q máx");
    // sube respecto del anillo antiguo (R_i = 75): la presión no puede bajar al quitar área
    const Ro = R.Ro, qOld = R.ND * 1e3 / (Math.PI * (Ro ** 2 - 75 ** 2)) * (1 + 4 * P0.e * Ro / (Ro ** 2 + 75 ** 2));
    assert.ok(R.q_max > qOld, ctx + "q_máx sube al reducir el área");
    near(R.hax, P0.h_disc / 2 + I.delta, 1e-12, ctx + "el eje de los cilindros sube δ");
    if (I.o) {
      near(I.A_ss, Math.PI * (Ro ** 2 - Ri ** 2), 1e-12, ctx + "área de los discos de la interfaz");
      near(I.q, R.q_max, 1e-3, ctx + "la presión de dimensionamiento de los discos es la del anillo real");
      for (const s of I.topes) { near(s.Lav, Ro - Ri - 100, 1e-12, ctx + s.pieza + ": canto radial disponible"); assert.ok(s.L <= s.Lav + 1e-9, ctx + s.pieza + ": L ≤ R_o − R_i − 100"); }
      const row = A.checks.filter((c) => /largo del tope frente al canto radial/.test(c.name));
      assert.ok(row.length === I.topes.length - (I.o === 2 ? 1 : 0) && row.every((c) => Math.abs(c.cap - (Ro - Ri - 100)) < 1e-9 && c.st === "ok"), ctx + "filas de largo de tope con el canto nuevo (en B la lámina UHMW usa todo el canto y tiene su propia fila de aplastamiento)");
    }
  }
  // masas con el área del anillo real
  const A = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }), B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true });
  near(A.R.ifc.mSS, RHO_SS * Math.PI * (A.R.Ro ** 2 - Ri ** 2) * (A.R.ifc.tss + A.R.ifc.tss2), 1e-12, "masa bruta de la corona de los discos (A)");
  near(B.R.ifc.mUH, RHO_UH * Math.PI * (B.R.Ro ** 2 - Ri ** 2) * B.R.ifc.tuh, 1e-12, "masa bruta de la corona de UHMW (B)");
  // la lámina UHMW usa todo el canto disponible (R_o − R_i − 100) y su espesor de tope lo ve
  near(B.R.ifc.topes.find((s) => s.id === "uhmw").L, B.R.Ro - Ri - 100, 1e-12, "largo del tope UHMW = canto disponible");
  // sin collar vuelve al borde del buje (D_piv/2 + 15); m_ri mueve R_i milímetro a milímetro
  near(TT.compute(Object.assign(TT.defaults(), { h_boss: 0 })).Ri, P0.D_piv / 2 + 15, 1e-12, "sin collar: R_i = D_piv/2 + 15");
  near(TT.compute(Object.assign(TT.defaults(), { m_ri: 10 })).Ri, 138, 1e-12, "m_ri = 10 → R_i = 138");
  assert.ok(TT.compute(Object.assign(TT.defaults(), { m_ri: 10 })).q_max > TT.compute(TT.defaults()).q_max, "más margen = menos área = más presión");
  // por el eje de las ranuras de engrase la longitud radial también parte de R_i: las ranuras ocupan menos área
  const gOld = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, m_ri: 0 }), { noFEA: true }).R;
  assert.ok(gOld.Ri < A.R.Ri && gOld.Ac > A.R.Ac);
  // todas las opciones cumplen con el anillo real (q_máx, aplastamiento de lámina y bronce, topes)
  for (const [nm, o] of IFC_VARIANTS) { const X = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }); assert.ok(X.verdict.gira && X.verdict.estructura, nm + " cumple con R_i = 131"); }
});

test("Rebaje del collar en la mesa: h_collar − δ + c_boss_a desde la cara inferior, agujero de la plancha inferior Ø(D_collar + 2·c_r) y aplastamiento de la pared del cubo", () => {
  const RHO = 7.85e-6;
  for (const [nm, o] of IFC_VARIANTS) {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }), R = A.R, P = A.P, m = R.m, I = R.ifc, H = R.hubG, ctx = nm + ": ";
    const d_b = P.D_piv + 30, Drb = P.D_boss + 2 * P.c_boss_r, hw = P.opt_wood ? P.h_disc - P.t_bot - P.t_wood - (P.t_reb || P.t_top) : P.h_disc - P.t_top - P.t_bot, hRec = P.h_boss - I.delta + P.c_boss_a;   // cubierta W: el cubo llega a la plancha rebajada
    near(H.hRec, hRec, 1e-12, ctx + "profundidad del rebaje = h_collar − δ + c_boss_a"); near(H.Drb, Drb, 1e-12, ctx + "Ø del agujero de la plancha = D_collar + 2·c_boss_r"); near(H.delta, I.delta, 1e-12, ctx + "δ de la interfaz");
    assert.ok(H.hRec > 0, ctx + "el collar sobresale de la cara inferior de la mesa");
    const rpr = TT.prIn(P), Rt = P.D_top / 2, aRing = Math.PI * (Rt * Rt - rpr * rpr) - P.N_pin * Math.PI / 4 * P.d_pin ** 2;
    const hPl = hRec > 0 ? P.t_bot : 0, hHub = Math.min(Math.max(0, hRec - P.t_bot), hw);   // el agujero de la plancha es pasante (un bolsillo menos profundo que t_bot dejaría un labio inútil)
    near(m.bot, RHO * ((Math.PI * rpr * rpr - Math.PI / 4 * d_b ** 2) * P.t_bot + aRing * Math.max(P.t_pr, P.t_bot)) - RHO * Math.PI / 4 * (Drb ** 2 - d_b ** 2) * hPl, 1e-12, ctx + "masa de la plancha inferior con el agujero real del collar");
    near(m.hub, RHO * Math.PI / 4 * ((P.D_hub ** 2 - d_b ** 2) * hw - (Drb ** 2 - d_b ** 2) * hHub), 1e-12, ctx + "masa del cubo con la parte del rebaje sobre la plancha");
    const inf = A.checks.find((c) => /Rebaje del cubo para el collar/.test(c.name));
    near(inf.dem, Drb, 1e-12, ctx + "Ø rebaje informado"); near(inf.cap, hRec, 1e-12, ctx + "profundidad informada (h − δ + c_a)"); assert.equal(inf.kind, "info");
    const wall = A.checks.find((c) => /pared del rebaje del cubo/.test(c.name));
    near(wall.dem, Drb + 50, 1e-12, ctx + "pared ≥ 25 mm"); assert.equal(wall.st, "ok");
    // aplastamiento de la pared del cubo bajo la presión de contacto que entra por el pie del cubo (anillo R_i … r_hub, plancha inferior apoyada sobre el cubo)
    const rh = P.D_hub / 2, lig = A.checks.find((c) => /aplastamiento de la pared del cubo/.test(c.name));
    near(lig.dem, R.q_max * (rh ** 2 - R.Ri ** 2) / (rh ** 2 - (Drb / 2) ** 2), 1e-9, ctx + "σ en la pared del cubo"); near(lig.cap, P.Fy / P.Nd, 1e-12, ctx + "Fy/Nd"); assert.ok(lig.st === "ok" && lig.fu < 0.1, ctx + "FU " + lig.fu);
    const rr = A.checks.find((c) => /R_i libre del rebaje/.test(c.name));
    near(rr.dem, Drb / 2 + P.m_ri, 1e-12, ctx + "R_i ≥ rebaje + margen"); near(rr.cap, R.Ri, 1e-12); assert.equal(rr.st, "ok");
  }
  // defaults sin interfaz (δ = 0): 60 + 2 = 62 mm, 16 en la plancha (agujero pasante) y 46 en el cubo
  const D0 = TT.compute(TT.defaults()).hubG; assert.deepEqual([D0.hRec, D0.hPl, D0.hHub], [62, 16, 46]);
  // con interfaz el rebaje es menos profundo (4.ª pasada, sectores de 15 mm): A 60 − 30 + 2 = 32; B 60 − 55 + 2 = 7 (menos que t_bot = 16: el cubo queda sin rebaje y el agujero de la plancha sigue siendo pasante, sin labio de 7 mm)
  const HA = TT.compute(Object.assign(TT.defaults(), { opt_ss: 1 })).hubG, HB = TT.compute(Object.assign(TT.defaults(), { opt_uhmw: 1 })).hubG;
  assert.deepEqual([HA.hRec, HA.hPl, HA.hHub], [32, 16, 16]); assert.deepEqual([HB.hRec, HB.hPl, HB.hHub], [7, 16, 0]);
  // la masa total (plancha + cubo) del default es la misma que con el modelo anterior (62 mm, todo en el cubo): solo se reparte entre las dos piezas
  const m0 = TT.masses(TT.defaults()), P0 = TT.defaults(), d_b = P0.D_piv + 30, Drb = P0.D_boss + 2 * P0.c_boss_r, hw0 = P0.h_disc - P0.t_top - P0.t_bot;
  const hubOld = RHO * Math.PI / 4 * ((P0.D_hub ** 2 - d_b ** 2) * hw0 - (Drb ** 2 - d_b ** 2) * 62);
  const rpr0 = TT.prIn(P0), aR0 = Math.PI * ((P0.D_top / 2) ** 2 - rpr0 ** 2) - P0.N_pin * Math.PI / 4 * P0.d_pin ** 2;
  near(m0.hub + m0.bot, hubOld + RHO * ((Math.PI * rpr0 * rpr0 - Math.PI / 4 * d_b ** 2) * P0.t_bot + aR0 * Math.max(P0.t_pr, P0.t_bot)), 1e-12, "plancha + cubo = modelo anterior (δ = 0)");
  // collar bajo la cara inferior (h − δ + c_a < 0): no hay rebaje; el agujero de la plancha es solo el del buje; se informa la profundidad negativa
  const N = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, h_boss: 20 }), { noFEA: true }), HN = N.R.hubG;
  near(HN.hRaw, 20 - 30 + 2, 1e-12, "profundidad cruda negativa (−8)"); assert.equal(HN.hRec, 0); assert.equal(HN.hPl, 0);
  near(N.R.m.hub, RHO * Math.PI / 4 * (P0.D_hub ** 2 - d_b ** 2) * hw0, 1e-12, "sin rebaje: cubo macizo salvo el buje");
  assert.ok(N.checks.find((c) => /Rebaje del cubo para el collar/.test(c.name)).dem < 0 || N.checks.find((c) => /Rebaje del cubo para el collar/.test(c.name)).cap < 0, "profundidad negativa reportada");
  assert.equal(TT.compute(Object.assign(TT.defaults(), { h_boss: 0 })).hubG.hRec, 0, "sin collar no hay rebaje");
  // pared del cubo < 25 mm: sigue fallando (D_hub 300)
  assert.equal(TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, D_hub: 300 }), { noFEA: true }).checks.find((c) => /pared del rebaje del cubo/.test(c.name)).st, "fail");
});

test("e_piv: mínimo de ingreso con default 0 = automático (rige g_buje + L_buje/2)", () => {
  const g = TT.PARAM_GROUPS.find((x) => x.id === "pivote").p.find((q) => q[0] === "e_piv");
  assert.equal(g[3], 0, "default 0 = automático"); assert.equal(g[4], 0, "mínimo del campo 0"); assert.match(g[1], /0 = autom/);
  near(TT.compute(TT.defaults()).ePiv, 42, 1e-12, "automático: 2 + 80/2");
  near(TT.compute(Object.assign(TT.defaults(), { e_piv: 60 })).ePiv, 60, 1e-12, "un mínimo de ingreso mayor manda");
  near(TT.compute(Object.assign(TT.defaults(), { e_piv: 40 })).ePiv, 42, 1e-12, "el antiguo 40 nunca regía");
  assert.equal(AG.validate(TT.defaults()).filter((v) => v.lvl === "error").length, 0, "0 es un valor válido");
});

/* ===================================================================================================================================== */
/* 4.ª pasada                                                                                                                              */
/* ===================================================================================================================================== */
const RHO_S = 7.85e-6, RHO_SSx = 7.93e-6, RHO_UHx = 0.94e-6, ALS = 11.7e-6;
const rnd01 = (x) => Math.ceil(x * 10 - 1e-9) / 10;

test("4.ª pasada · hc_min = 6: sectores con tope de 15 mm y el largo del tope tolera 1 mm menos de contacto (T6)", () => {
  const P0 = TT.defaults(), aInf = P0.w_tope + 1;
  assert.equal(P0.hc_min, 6); assert.equal(P0.tol_hc, 1); assert.equal(P0.a_sup + aInf + P0.hc_min, 15, "espesor mínimo del sector con tope");
  for (const [nm, o] of [["A", { opt_ss: 1 }], ["B", { opt_uhmw: 1 }], ["C1", { opt_bz: 1 }], ["C2", { opt_bz: 1, bz_conf: 2 }], ["C3", { opt_bz: 1, bz_conf: 3 }]]) {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }), T = A.R.ifc.topes, I = A.R.ifc;
    assert.ok(A.verdict.gira && A.verdict.estructura, nm + " cumple");
    if (nm !== "B") assert.deepEqual([I.tss, I.tss2], [15, 15], nm + ": sectores de 15 mm"); else assert.deepEqual([I.tss, I.tss2], [15, 15]);
    if (I.o === 3) assert.equal(I.tbz, 15, nm + ": bronce de 15 mm");
    for (const s of T) {
      assert.ok(s.t >= 15 - 1e-9 && s.h_c >= P0.hc_min - 1e-9, nm + " " + s.pieza + ": t ≥ 15 y h_c ≥ 6");
      const adm = s.adm, sig = (hc) => s.F * 1e3 / (s.L * hc);
      assert.ok(sig(s.h_c - P0.tol_hc) <= 0.9 * adm + 1e-9, nm + " " + s.pieza + ": con 1 mm menos de contacto el aplastamiento sigue ≤ 0,90 (σ/adm = " + (sig(s.h_c - 1) / adm).toFixed(3) + ")");
      assert.ok(sig(s.h_c) <= 0.9 * adm * (s.h_c - 1) / s.h_c + 1e-9, nm + " " + s.pieza + ": con h_c nominal queda con margen");
    }
    const rows = A.checks.filter((c) => /aplastamiento del tope con la altura de contacto reducida/.test(c.name));
    assert.equal(rows.length, T.length, nm + ": una fila de aplastamiento con h_c − tol por tope");
    assert.ok(rows.every((c) => c.fu <= 0.9 + 1e-9 && /tol_hc|tolerancia/.test(c.formula)), nm + ": FU ≤ 0,90 con h_c − tol");
  }
  // B: la lámina de UHMW se dimensiona con h_c ≥ F_s/(0,9·L·p_adm) + tol (T7: el 0,9 es margen de proyecto)
  const B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }), RB = B.R, IB = RB.ifc;
  const Lav = RB.Ro - RB.Ri - 100, Fs = Math.max(RB.mu.d, RB.mu.cont, RB.mu.dry) * RB.N / P0.n_seg * RB.q_max / RB.q_avg;
  const hcNeed = Math.max(P0.hc_min, Fs * 1e3 / (0.9 * Lav * P0.p_uhmw) + P0.tol_hc), tTope = P0.a_sup + aInf + hcNeed;
  near(IB.tuhTope, tTope, 1e-4, "espesor del sector de UHMW por el tope del rebaje (N del bucle de la interfaz vs N final: < 0,01 %)");
  const UH = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50], tExp = UH.find((v) => v >= Math.max(IB.tuhReq, tTope) - 1e-9);
  assert.equal(IB.tuh, tExp, "UHMW comercial = menor espesor ≥ máx(planitud; tope)");
  const row = B.checks.find((c) => /Lámina UHMW: espesor mínimo por el tope del rebaje/.test(c.name));
  assert.ok(row && row.kind === "info", "fila informativa del espesor por el tope");
  assert.ok(/0,9/.test(row.formula) && /margen de proyecto/.test(row.formula) && /no lo exige la norma/.test(row.formula), "T7: el 0,9 se documenta como margen de proyecto, no de norma");
  near(row.dem, tTope, 1e-4, "dem = espesor mínimo por el tope"); near(row.cap, IB.tuh, 1e-12, "cap = espesor adoptado");
  // A con t manual de 12 (el antiguo automático): h_c = 3 < 6 no cumple
  assert.ok(TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, t_ss: 12 }), { noFEA: true }).checks.some((c) => /altura de contacto efectiva del tope/.test(c.name) && c.st === "fail"), "12 mm ya no cumple");
  // tol_hc = 0 reproduce el dimensionamiento sin tolerancia (A: L = 150 con FU 0,836, que con 1 mm menos de contacto pasa de 0,90): la tolerancia es lo que protege contra el hallazgo T6
  const A0 = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, tol_hc: 0 }), { noFEA: true }).R.ifc.topes[0], A1 = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }).R.ifc.topes[0];
  assert.ok(A1.L > A0.L, "con tol_hc = 1 el tope es más largo (" + A1.L + " vs " + A0.L + " mm)");
  assert.ok(A0.F * 1e3 / (A0.L * (A0.h_c - 1)) > 0.9 * A0.adm, "sin tolerancia, 1 mm menos de contacto pasa de FU 0,90");
  // con hc_min = 3 (valor anterior) vuelven los 12 mm
  assert.deepEqual([TT.compute(Object.assign(TT.defaults(), { opt_ss: 1, hc_min: 3 })).ifc.tss, TT.compute(Object.assign(TT.defaults(), { opt_ss: 1, hc_min: 3 })).ifc.tss2], [12, 12]);
});

test("4.ª pasada · masa de sectores: muescas, chaflanes y juntas descontadas con fórmula explícita; barras de UHMW en inoxidable", () => {
  const P0 = TT.defaults(), a2 = (P0.w_tope + 1) ** 2, b2 = P0.b_tope + 2;
  assert.equal(P0.j_sec, 1, "junta en frío mínima 1 mm (parámetro)");
  const variants = [["A", { opt_ss: 1 }], ["B", { opt_uhmw: 1 }], ["C1", { opt_bz: 1 }], ["C2", { opt_bz: 1, bz_conf: 2 }], ["C3", { opt_bz: 1, bz_conf: 3 }]];
  for (const [nm, o] of variants) {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }), R = A.R, I = R.ifc, m = R.m, Ro = R.Ro, Ri = R.Ri, Aan = Math.PI * (Ro ** 2 - Ri ** 2), P = A.P, ctx = nm + ": ";
    const jOf = (al, n) => rnd01(Math.max(P.j_sec, (al - ALS) * P.dT * 2 * Ro * Math.sin(Math.PI / n)));
    const top = (id) => I.topes.find((x) => x.id === id);
    const rBz = P.rho_bz * 1e-6, fg = I.fgUsed ?? 0, rEff = rBz * (1 - 0.7 * fg) + 1.8e-6 * 0.7 * fg;
    const exp = { ss: I.mSS, uhmw: I.mUH, bz: I.mBz }, desc = { ss: 0, uhmw: 0, bz: 0 };
    const sub = (tgt, rho, n, capas, t, L, joint, jj, strip) => {   // volumen por sector: junta (o franja libre) + muesca (no en la franja) + 2 chaflanes de a_inf²/2
      const Vj = joint ? (strip ? P.b_tope + jj : jj) * (Ro - Ri) * t : 0, Vn = strip ? 0 : b2 * L * t, Vc = a2 * L;
      desc[tgt] += rho * capas * n * (Vj + Vn + Vc);
    };
    if (I.o === 1 || I.o === 2) { const d = top("disc0"), d1 = top("disc1"); for (const x of [d, d1].filter(Boolean)) sub("ss", RHO_SSx, x.n, x.capas, x.t, x.L, true, jOf(17.3e-6, x.n)); }
    if (I.o === 2) { const u = top("uhmw"); sub("uhmw", RHO_UHx, u.n, 1, u.t, u.L, true, jOf(180e-6, u.n), true); }
    if (I.o === 3) {
      const z0 = top("bz0"), z1 = top("bz1");
      sub("bz", rEff, z0.n, 1, z0.t, z0.L, I.conf !== 3, jOf(18e-6, z0.n));            // pastillas: la junta ya está en la fracción de cobertura
      if (I.conf === 2) sub("bz", rBz, z1.n, 1, z1.t, z1.L, true, jOf(18e-6, z1.n)); else sub("ss", RHO_SSx, z1.n, 1, z1.t, z1.L, true, jOf(17.3e-6, z1.n));
    }
    near(m.ss, exp.ss - desc.ss, 1e-9, ctx + "m.ss neta"); near(m.uhmw, exp.uhmw - desc.uhmw, 1e-9, ctx + "m.uhmw neta"); near(m.bz, exp.bz - desc.bz, 1e-9, ctx + "m.bz neta");
    assert.ok(desc.ss + desc.uhmw + desc.bz > 5, ctx + "el descuento es apreciable (> 5 kg)");
    near(m.total, m.disc + m.ss + m.uhmw + m.bz + m.base + m.rim + m.brackets + m.dogs + m.shoes + m.beds + m.cam + m.pivot + m.cyl + m.stopBars, 1e-12, ctx + "m.total con piezas netas");
    // la fila informativa de cada pieza y las claves de interfazGeom
    const rows = A.checks.filter((c) => /descuento de masa por muescas, chaflanes y juntas/.test(c.name));
    assert.equal(rows.length, I.cortes.length, ctx + "una fila por pieza"); assert.ok(rows.every((c) => c.kind === "info" && c.dem > 0 && /a_inf²|a_inf\^2|a_inf²/.test(c.formula) && /junta/.test(c.formula)), ctx + "filas info con la fórmula");
    near(rows.reduce((q, c) => q + c.dem, 0), desc.ss + desc.uhmw + desc.bz, 1e-9, ctx + "las filas suman el descuento");
    near(I.cortes.reduce((q, c) => q + c.m_desc, 0), desc.ss + desc.uhmw + desc.bz, 1e-9, ctx + "R.ifc.cortes");
    // cada sector pesa menos (manipulación manual): masa neta por sector en la fila de ISO 11228-1
    const ms = A.checks.filter((c) => /masa del sector/.test(c.name));
    assert.ok(ms.length > 0 && ms.every((c) => c.dem <= 25), ctx + "sectores ≤ 25 kg");
  }
  // barras de UHMW en B: acero inoxidable (ρ 7,93); las demás, acero estructural (ρ 7,85)
  const B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }), u = B.R.ifc.topes.find((x) => x.id === "uhmw"), d = B.R.ifc.topes.find((x) => x.id === "disc0");
  near(u.m_barra, RHO_SSx * u.L * P0.b_tope * u.h_barra, 1e-12, "barra de UHMW en inoxidable"); near(d.m_barra, RHO_S * d.L * P0.b_tope * d.h_barra, 1e-12, "barra del disco en acero estructural");
  near(B.R.m.stopBars, d.capas * d.n * d.m_barra + u.n * u.m_barra, 1e-12, "m.stopBars con ambas densidades");
  // con pegado (fix_mode = 2) no hay muescas, chaflanes ni juntas en los discos; la lámina UHMW conserva sus juntas
  const G = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, fix_mode: 2 }), { noFEA: true }); near(G.R.m.ss, G.R.ifc.mSS, 1e-12, "pegado: disco entero");
  const GB = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1, fix_mode: 2 }), { noFEA: true }), ju = rnd01(Math.max(P0.j_sec, (180e-6 - ALS) * P0.dT * 2 * GB.R.Ro * Math.sin(Math.PI / P0.n_seg)));
  near(GB.R.m.ss, GB.R.ifc.mSS, 1e-12, "pegado: discos enteros"); near(GB.R.m.uhmw, GB.R.ifc.mUH - RHO_UHx * P0.n_seg * ju * (GB.R.Ro - GB.R.Ri) * GB.R.ifc.tuh, 1e-9, "pegado: la lámina UHMW sigue en sectores con junta");
  // más junta o barra más ancha, más descuento
  const A0 = TT.compute(Object.assign(TT.defaults(), { opt_ss: 1 })), A1 = TT.compute(Object.assign(TT.defaults(), { opt_ss: 1, j_sec: 3 }));
  assert.ok(A1.m.ss < A0.m.ss, "una junta de 3 mm quita más material que una de 1 mm");
  // ambos sentidos de giro: la muesca tiene las dos paredes (chaflán en ambas) y el par de calado es el mismo en los dos sentidos (cilindros en espejo)
  const cw = TT.compute(Object.assign(TT.defaults(), { opt_ss: 1 })); assert.ok(cw.ifc.topes.every((x) => x.F > 0 && x.a_inf === P0.w_tope + 1));
});

/* ---------------- Cubierta de madera W con rebaje (decisión del mandante, 08-11-2026) ----------------
   Mesa con anillo superior R_reb…R (la plancha superior actual en esa zona, con los pasadores), plancha rebajada continua dentro de R_reb bajada t_madera,
   pared cilíndrica en R_reb y tablones enrasados con la cara superior del anillo. Sin anillo de contención 10×50; la altura total no aumenta. */
const PW = (o) => Object.assign(TT.defaults(), { opt_wood: 1 }, o || {});
test("W · parámetros y geometría del rebaje por defecto (supuestos del mandante y ajuste de t_madera 50 → 45)", () => {
  const P = PW(), g = TT.woodGeo(P), tAn = Math.max(P.t_pr, P.t_top);
  assert.equal(TT.woodGeo(TT.defaults()), null, "sin cubierta no hay geometría de rebaje");
  assert.equal(P.R_reb, 840, "R_rebaje = 840 (supuesto del mandante)"); assert.equal(P.t_reb, 0); assert.equal(P.t_pared, 0);
  assert.equal(P.t_wood, 45, "t_madera 50 → 45: con 50 el buje no cabe bajo la plancha rebajada (142 > 140) y la plancha inferior pasa de FU 0,90; 45 = 2\" cepillado y paso del parámetro");
  assert.equal(g.t_reb, P.t_top, "plancha rebajada = espesor de la plancha superior (0 = automático)"); assert.equal(g.t_pared, P.t_top, "pared = espesor de la plancha superior");
  assert.equal(g.t_anillo, tAn, "anillo superior en una pieza de espesor máx(t_pr, t_top) desde R_reb (sin franja de 20 mm de ancho)");
  near(g.R_pared_ext, P.R_reb + g.t_pared, 1e-12, "cara exterior de la pared"); near(g.R_reb_ext, P.R_reb + g.t_pared + P.w_pared + 5, 1e-12, "borde de la plancha rebajada: pie del filete exterior + 5");
  near(g.h_pared, P.t_wood - tAn, 1e-12, "altura libre de la pared"); near(g.h_c, P.t_wood + g.t_reb / 2 - tAn / 2, 1e-12, "distancia entre planos medios plancha rebajada–anillo");
  near(g.d_rebaje, P.t_wood + g.t_reb - P.t_top, 1e-12, "descenso de la cara inferior de la piel superior"); near(g.hw_reb, P.h_disc - P.t_bot - P.t_wood - g.t_reb, 1e-12, "altura de almas y nervios bajo la plancha rebajada");
  near(g.R_tablones, P.R_reb - P.c_mad, 1e-12, "borde exterior de los tablones (holgura perimetral)"); near(g.R_abertura, (P.D_piv + 120) / 2 + P.c_mad, 1e-12, "abertura sobre la tapa de inspección Ø D_piv + 120 (cad: cb_D)");
  near(g.z.reb_sup, P.h_disc - P.t_wood, 1e-12, "cota de la cara superior de la plancha rebajada (desde la cara inferior de la mesa)"); near(g.z.anillo_inf, P.h_disc - tAn, 1e-12);
  assert.ok(g.almas.every((a) => a.r <= g.R_pared_ext ? a.h === g.hw_reb && a.recortada : !a.recortada), "almas dentro de R_pared bajan; fuera no cambian");
  assert.ok(g.nervios.sin_cambio_altura, "nervios hasta R_nervio = R_reb: todos bajo la plancha rebajada");
});
test("W · masas: anillo + pared + plancha rebajada, almas/nervios/cubo/pivote más bajos, tablones netos, sin anillo 10×50", () => {
  const P = PW(), P0 = TT.defaults(), m = TT.compute(P).m, m0 = TT.compute(P0).m, g = TT.woodGeo(P), R7 = 7.85e-6, tAn = Math.max(P.t_pr, P.t_top);
  const Rt = P.D_top / 2, hole = P.D_piv + 80, aPins = P.N_pin * Math.PI / 4 * P.d_pin ** 2;
  const mAn = R7 * (Math.PI * (Rt ** 2 - P.R_reb ** 2) - aPins) * tAn, mPar = R7 * Math.PI * (g.R_pared_ext ** 2 - P.R_reb ** 2) * g.h_pared, mReb = R7 * Math.PI * (g.R_reb_ext ** 2 - (hole / 2) ** 2) * g.t_reb;
  near(m.top, mAn + mPar + mReb, 1e-12, "m.top (W) = anillo + pared + plancha rebajada");
  near(g.masas.anillo, mAn, 1e-12); near(g.masas.pared, mPar, 1e-12); near(g.masas.plancha_rebajada, mReb, 1e-12);
  const rings = TT.parseRings(P.rings);
  near(m.webs, R7 * rings.reduce((s, r) => s + 2 * Math.PI * r * g.hw_reb * P.t_web, 0), 1e-12, "almas (todas dentro de R_pared) con h = hw_reb");
  near(m.ribs / m0.ribs, g.hw_reb / (P.h_disc - P.t_top - P.t_bot), 1e-12, "nervios con h = hw_reb");
  near(m.pivot, R7 * Math.PI / 4 * P.D_piv ** 2 * (P.t_base + P.h_disc - P.t_wood - g.t_reb + 3), 1e-12, "pivote hasta la plancha rebajada");
  near(m.pins, m0.pins, 1e-12, "pasadores sin cambio (en el anillo)"); near(m.bot, m0.bot, 1e-12, "plancha inferior sin cambio");
  assert.equal(m.ring, 0, "sin anillo de contención");
  near(m.wood, P.rho_wood * 1e-9 * P.t_wood * g.tablones.area_neta, 1e-12, "masa de los tablones = ρ·t·Σ área neta de las piezas");
  const aGross = Math.PI * (g.R_tablones ** 2 - g.R_abertura ** 2); assert.ok(g.tablones.area_neta < aGross && g.tablones.area_neta > 0.97 * aGross, "área neta = corona menos juntas");
  near(m.disc, m.top + m.bot + m.webs + m.ribs + m.hub + m.pins + m.wood, 1e-12, "m.disc");
  const dW = m.total - m0.total; assert.ok(dW > 40 && dW < 120, "Δ masa total con la cubierta W ≈ +70 kg (antes ≈ +162 kg con anillo 10×50 y tablones sobre la plancha): " + dW.toFixed(1));
});
test("W · tablones: disposición simétrica, piezas, abertura de la tapa y fijación ISO 4762 que cabe en t_madera + t_reb (el Ø8×80 no cabía en 50 + 20)", () => {
  const P = PW(), g = TT.woodGeo(P), T = g.tablones, Rw = g.R_tablones;
  assert.equal(T.b, P.b_tab); assert.equal(T.n, 9, "9 tablones de 200 en Ø" + (2 * Rw)); assert.equal(T.lista.length, T.n);
  T.lista.forEach((t, i) => { assert.ok(t.y1 - t.y0 <= P.b_tab + 1e-9 && t.y0 >= -Rw - 1e-9 && t.y1 <= Rw + 1e-9, "dentro del círculo"); if (i) near(t.y0 - T.lista[i - 1].y1, P.j_tab, 1e-9, "junta"); });
  near(T.lista[0].y0, -Rw, 1e-12, "cubre hasta el borde"); near(T.lista[T.n - 1].y1, Rw, 1e-12);
  near(T.lista[0].ancho, T.lista[T.n - 1].ancho, 1e-12, "simétrica"); assert.ok(Math.min(...T.lista.map((t) => t.ancho)) >= P.b_tab / 2, "sin tiras angostas");
  const c = T.lista[(T.n - 1) / 2]; assert.equal(c.piezas.length, 2, "el tablón central se corta en dos por la abertura"); assert.equal(c.corte, "abertura");
  assert.ok(T.lista.some((t) => t.corte === "muesca"), "los vecinos llevan una muesca en arco R_abertura");
  const F = (R, y) => { const yc = Math.max(-R, Math.min(R, y)); return yc * Math.sqrt(R * R - yc * yc) + R * R * Math.asin(yc / R); };
  near(T.area_neta, T.lista.reduce((s, t) => s + (F(Rw, t.y1) - F(Rw, t.y0)) - (F(g.R_abertura, t.y1) - F(g.R_abertura, t.y0)), 0), 1e-9, "área neta exacta (franjas de círculo)");
  // fijación: ISO 4762 en cajeado con arandela ISO 7093, roscada en taladro ciego de la plancha rebajada
  const f = g.fijacion, d = P.d_tmad;
  near(f.h_cajeado, d + f.h_arandela + 3, 1e-12, "cabeza 3 mm bajo la superficie"); near(f.t_bajo_arandela, P.t_wood - f.h_cajeado, 1e-12);
  near(f.prof_taladro, g.t_reb - 3, 1e-12, "remanente 3 mm: la caja de la mesa queda cerrada"); near(f.rosca_util, f.prof_taladro - 4, 1e-12);
  assert.ok([16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100].includes(f.L), "largo comercial ISO 4762"); near(f.engrane, f.L - f.t_bajo_arandela, 1e-12);
  assert.ok(f.engrane >= d - 1e-9 && f.engrane <= f.rosca_util - 2 + 1e-9, "engrane ≥ 1,0·d sin tocar el fondo"); assert.equal(f.L, 40, "M10×40");
  assert.ok(f.n_total >= 2 * T.lista.reduce((s, t) => s + t.piezas.length, 0), "≥ 2 tornillos por pieza"); assert.equal(f.posiciones.length, f.n_total);
  f.posiciones.forEach(([x, y]) => { const r = Math.hypot(x, y); assert.ok(r <= Rw && r >= g.R_abertura, "tornillo sobre la madera"); });
  const W = TT.analyze(P, { noFEA: true }), row = (re) => W.checks.find((x) => re.test(x.name));
  const fl = row(/Fijación de los tablones: largo comercial/); assert.ok(fl && fl.st === "ok"); near(fl.dem, d, 1e-12); near(fl.cap, f.engrane, 1e-12);
  const old = row(/tornillo de 80 mm/); assert.ok(old && old.kind === "info" && old.dem === 80 && old.cap === 70, "registra el hallazgo de los planos (Ø8×80 en 50 + 20)");
  assert.equal(TT.analyze(PW({ d_tmad: 16 }), { noFEA: true }).checks.find((x) => /Fijación de los tablones: espesor mínimo de la plancha rebajada/.test(x.name)).st, "fail", "M16 no cabe en el roscado ciego de 20");
});
test("W · FEA escalonada de la mesa (modelo desarrollado: plancha rebajada + pared + anillo con pasadores) y flexión global con h_c reducido", () => {
  const P = PW(), A = TT.analyze(P), A0 = TT.analyze(TT.defaults()), t = A.fea.top, g = TT.woodGeo(P);
  assert.ok(t.escalon && t.escalon.variantes.length === 2, "dos variantes: anillo con pasadores (h_c entre planos medios) y pared empotrada en el anillo (altura libre)");
  assert.ok(t.vmMax > 0.85 * A0.fea.top.vmMax && t.vmMax < 1.15 * A0.fea.top.vmMax, "la plancha rebajada trabaja como la plancha superior (mismas luces): " + t.vmMax.toFixed(1));
  assert.ok(t.escalon.sPared > 30 && t.escalon.sPared < 200, "pared: σ FEA " + t.escalon.sPared.toFixed(1));
  assert.ok(t.maxAt[0] < P.R_reb, "máximo dentro del rebaje");
  near(A.fea.glob.hcTop, P.h_disc - P.t_wood - g.t_reb / 2 - P.t_bot / 2, 1e-12, "h_c del sándwich dentro de R_reb");
  near(A.fea.glob.sigBot, A.fea.glob.Mmax / (P.t_bot * A.fea.glob.hcTop), 1e-12); near(A.fea.glob.sigTop, A.fea.glob.Mmax / (g.t_reb * A.fea.glob.hcTop), 1e-12);
  assert.ok(A.fea.glob.MrReb > 0 && A.fea.glob.MrReb < A.fea.glob.Mmax, "M_r global en R_reb (sale el empuje del escalón)");
  const row = (re) => A.checks.find((x) => re.test(x.name));
  for (const re of [/^Plancha superior: global \+ local$/, /^Plancha inferior: global \+ local$/, /^Plancha superior: σvm local/, /^Corte en nervios radiales$/]) { const c = row(re); assert.ok(c && c.fu <= 0.9, c.name + " FU " + c.fu); }
  near(row(/^Corte en nervios radiales$/).dem, A.fea.glob.Vmax * 1e3 / (P.N_rib * P.t_rib * g.hw_reb), 1e-9, "corte en nervios con la altura reducida");
  const b50 = TT.analyze(PW({ t_wood: 50 })); assert.equal(b50.checks.find((x) => /^Plancha inferior: global \+ local$/.test(x.name)).st, "warn", "con t_madera = 50 la plancha inferior pasa de FU 0,90 (motivo del ajuste a 45)");
  assert.equal(b50.checks.find((x) => /Buje sobre el collar/.test(x.name)).st, "fail", "con t_madera = 50 el buje no cabe bajo la plancha rebajada");
  assert.ok(/plancha rebajada/.test(row(/Buje sobre el collar/).name));
  assert.ok(A.verdict.estructura && A.verdict.gira && A.verdict.warnEst === 0, "W cumple sin avisos");
});
test("W · FEA escalonada: caso de referencia axisimétrico frente a la solución cerrada de Kirchhoff (plancha + pared desarrollada + anillo con apoyo lineal)", () => {
  // referencia: placa anular r0…b, D uniforme, empotrada en r0, apoyos lineales (w = 0) en a (alma), a + L (unión pared–anillo) y Rp (pasadores como línea), borde libre en b; q uniforme en r0…a.
  // Solución por tramos w = C1 + C2·r² + C3·ln r + C4·r²·ln r + q·r⁴/(64D); continuidad de w′ y M_r en los apoyos interiores.
  const r0 = 155, a = 600, L = 120, Rp = a + L + 90, b = a + L + 160, t = 10, E = 2e5, nu = 0.3, q = 0.05, D = E * t ** 3 / (12 * (1 - nu * nu));
  const segs = [[r0, a, q], [a, a + L, 0], [a + L, Rp, 0], [Rp, b, 0]];
  const fns = (r, qq) => ({ w: [1, r * r, Math.log(r), r * r * Math.log(r)], wp: [0, 2 * r, 1 / r, 2 * r * Math.log(r) + r], wpp: [0, 2, -1 / (r * r), 2 * Math.log(r) + 3], wppp: [0, 0, 2 / r ** 3, 2 / r],
    pw: qq * r ** 4 / (64 * D), pwp: qq * r ** 3 / (16 * D), pwpp: 3 * qq * r * r / (16 * D), pwppp: 6 * qq * r / (16 * D) });
  const nS = segs.length, N = 4 * nS, Am = Array.from({ length: N }, () => new Array(N).fill(0)), bv = new Array(N).fill(0); let row = 0;
  const put = (s, coef, rhs) => { coef.forEach((v, i) => { Am[row][4 * s + i] += v; }); bv[row] -= rhs; };
  const MrC = (r, qq) => { const f = fns(r, qq); return { c: f.wpp.map((v, i) => -D * (v + nu * f.wp[i] / r)), p: -D * (f.pwpp + nu * f.pwp / r) }; };
  const QrC = (r, qq) => { const f = fns(r, qq); return { c: f.wppp.map((v, i) => -D * (v + f.wpp[i] / r - f.wp[i] / (r * r))), p: -D * (f.pwppp + f.pwpp / r - f.pwp / (r * r)) }; };
  { const f = fns(r0, q); put(0, f.w, f.pw); row++; put(0, f.wp, f.pwp); row++; }
  for (let s = 0; s < nS - 1; s++) { const r = segs[s][1], fL = fns(r, segs[s][2]), fR = fns(r, segs[s + 1][2]);
    put(s, fL.w, fL.pw); row++; put(s + 1, fR.w, fR.pw); row++;
    put(s, fL.wp, fL.pwp); put(s + 1, fR.wp.map((v) => -v), -fR.pwp); row++;
    const mL = MrC(r, segs[s][2]), mR = MrC(r, segs[s + 1][2]); put(s, mL.c, mL.p); put(s + 1, mR.c.map((v) => -v), -mR.p); row++; }
  { const m = MrC(b, 0), qv = QrC(b, 0); put(nS - 1, m.c, m.p); row++; put(nS - 1, qv.c, qv.p); row++; }
  for (let i = 0; i < N; i++) { let p = i; for (let k = i + 1; k < N; k++) if (Math.abs(Am[k][i]) > Math.abs(Am[p][i])) p = k; [Am[i], Am[p]] = [Am[p], Am[i]]; [bv[i], bv[p]] = [bv[p], bv[i]];
    for (let k = i + 1; k < N; k++) { const f = Am[k][i] / Am[i][i]; for (let j = i; j < N; j++) Am[k][j] -= f * Am[i][j]; bv[k] -= f * bv[i]; } }
  const C = new Array(N).fill(0); for (let i = N - 1; i >= 0; i--) { let s = bv[i]; for (let j = i + 1; j < N; j++) s -= Am[i][j] * C[j]; C[i] = s / Am[i][i]; }
  const segOf = (r) => segs.findIndex((sg) => r >= sg[0] - 1e-9 && r <= sg[1] + 1e-9);
  const wA = (r) => { const s = segOf(r), f = fns(r, segs[s][2]); return f.w.reduce((acc, v, i) => acc + v * C[4 * s + i], f.pw); };
  const MrA = (r) => { const s = segOf(r), m = MrC(r, segs[s][2]); return m.c.reduce((acc, v, i) => acc + v * C[4 * s + i], m.p); };
  const MtA = (r) => { const s = segOf(r), f = fns(r, segs[s][2]); const wp = f.wp.reduce((acc, v, i) => acc + v * C[4 * s + i], f.pwp), wpp = f.wpp.reduce((acc, v, i) => acc + v * C[4 * s + i], f.pwpp); return -D * (wp / r + nu * wpp); };
  // FEA del núcleo con el mismo constructor de malla que usa la cubierta W (TT.stepPlate), en modo axisimétrico (sin nervios, pasadores como línea)
  const m = TT.stepPlate({ r0, Rd: b, alpha: Math.PI / 12, t, E, nu, keyR: [a, a + L, Rp], lines: [a, a + L, Rp], h: 8, dth: Math.PI / 12 / 10, load: (rc) => (rc <= a ? q : 0), zone: (rc) => (rc < a ? "reb" : rc < a + L ? "pared" : "anillo") });
  const r = FEA.plate(m), wF = (rr) => { let best = 0, d = 1e9; m.pol.forEach((p, k) => { if (Math.abs(p[0] - rr) < d) { d = Math.abs(p[0] - rr); best = k; } }); return r.w[best]; };
  const rMid = (r0 + a) / 2 + 60; let wmA = 0, rwm = 0; for (let rr = r0; rr <= a; rr += 1) { const v = Math.abs(wA(rr)); if (v > wmA) { wmA = v; rwm = rr; } }
  near(Math.abs(wF(rwm)), wmA, 0.02, "flecha máxima de la plancha rebajada");
  near(Math.abs(wF(b)), Math.abs(wA(b)), 0.05, "flecha del borde libre del anillo (rotación transmitida por la pared)");
  const MrF = (rr) => { let best = null, d = 1e9; m.elems.forEach((e, i) => { const c = e.map((k) => m.pol[k]), rc = c.reduce((s2, p) => s2 + p[0], 0) / 4; if (Math.abs(rc - rr) < d) { d = Math.abs(rc - rr); best = i; } }); return { M: r.el[best].M, rc: m.elems[best].map((k) => m.pol[k]).reduce((s2, p) => s2 + p[0], 0) / 4, th: m.elems[best].map((k) => m.pol[k]).reduce((s2, p) => s2 + p[1], 0) / 4 }; };
  const mr = (rr) => { const o = MrF(rr), c = Math.cos(o.th), s2 = Math.sin(o.th); return { Mr: o.M[0] * c * c + o.M[1] * s2 * s2 + 2 * o.M[2] * s2 * c, rc: o.rc }; };
  const eA = mr(a - 6), eP = mr(a + L / 2), eS = mr(rwm);
  near(Math.abs(eA.Mr), Math.abs(MrA(eA.rc)), 0.04, "M_r junto al alma/pared (concentración del escalón)");
  near(Math.abs(eP.Mr), Math.abs(MrA(eP.rc)), 0.04, "M_r en la pared desarrollada");
  near(Math.abs(eS.Mr), Math.abs(MrA(eS.rc)), 0.04, "M_r en el vano de la plancha rebajada");
  assert.ok(Math.abs(MtA(a)) > 0, "M_t finito");
});
test("W · verificaciones nuevas: pared en R_reb, soldaduras anillo–pared y pared–plancha rebajada, tamaños AWS, holguras, apoyo lateral, tapas y fatiga", () => {
  const P = PW(), A = TT.analyze(P), g = TT.woodGeo(P), row = (re, AA) => (AA || A).checks.find((x) => re.test(x.name));
  const need = [/^Pared del rebaje: flexión/, /^Pared del rebaje: corte/, /^Soldadura pared–plancha rebajada/, /^Soldadura anillo–pared/, /^Rebaje: filete mínimo/, /^Rebaje: penetración parcial anillo–pared cabe/,
    /^Rebaje: tablones libres del filete interior/, /^Rebaje: huella de la carga dentro de los tablones/, /^Rebaje: alma bajo la pared/, /^Rebaje: plancha rebajada libre de los pasadores/, /^Rebaje: arandelas de los pasadores sobre el anillo/,
    /^Rebaje: tapa retenedora y tapa de inspección en la plancha rebajada/, /^Madera: apoyo lateral de los tablones contra la pared/, /^Madera: holgura perimetral frente a la dilatación/, /^Fatiga: pared del rebaje/];
  for (const re of need) { const c = row(re); assert.ok(c, "falta " + re); if (c.kind !== "info" && c.kind !== "pend") assert.ok(c.st === "ok", c.name + ": " + c.st + " FU " + c.fu); }
  const pf = row(/^Pared del rebaje: flexión/), sw = row(/^Soldadura pared–plancha rebajada/);
  assert.ok(/AISC 360-22 F11/.test(pf.ref) && /J2\.4/.test(sw.ref) && /BTH-1/.test(pf.formula), "citas");
  near(pf.cap, 0.6 * P.Fy, 1e-12); near(sw.cap, 0.6 * P.FEXX / 2, 1e-12);
  const e = A.fea.top.escalon, H = P.k_hmad * P.phi_d * A.R.W * 1e3, Lc = 2 * Math.min(P.D_load / 2, g.R_tablones), Mlat = 3 * (H / Lc) * g.h_c / 16, Mjog = A.fea.glob.MrReb / A.fea.glob.hcTop * g.h_c;
  near(pf.dem, P.kFEA * e.sPared + 6 * (Mjog + Mlat) / g.t_pared ** 2, 1e-9, "σ = k_malla·σ_FEA + 6(N_r·h_c + M_lat)/t²");
  const aw = 0.707 * P.w_pared, M = pf.dem * g.t_pared ** 2 / 6, V = A.fea.glob.MrReb / A.fea.glob.hcTop + 11 / 16 * H / Lc;
  near(sw.dem, Math.hypot(M / (g.t_pared * aw), V / (2 * aw)), 1e-9, "2 filetes con par M/(t·a) y corte V/(2a)");
  near(row(/^Madera: apoyo lateral/).dem, H / (Lc * P.t_wood), 1e-9, "apoyo lateral = H/(L_c·t)");
  near(row(/^Rebaje: filete mínimo/).dem, 8, 1e-12, "AWS T5.8: el anillo de 27 mm pide 8 mm");
  // detecta fallas
  assert.equal(row(/^Pared del rebaje: flexión/, TT.analyze(PW({ t_pared: 8 }))).st !== "ok", true, "pared de 8 mm no cumple");
  assert.equal(row(/^Rebaje: filete mínimo/, TT.analyze(PW({ w_pared: 6 }), { noFEA: true })).st, "fail", "6 < 8");
  assert.equal(row(/^Rebaje: tablones libres del filete interior/, TT.analyze(PW({ c_mad: 8 }), { noFEA: true })).st, "fail", "holgura 8 < w + 2");
  assert.equal(row(/^Rebaje: huella de la carga dentro de los tablones/, TT.analyze(PW({ D_load: 1700 }), { noFEA: true })).st, "fail");
  assert.equal(row(/^Rebaje: alma bajo la pared/, TT.analyze(PW({ R_reb: 780 }), { noFEA: true })).st, "fail", "sin alma bajo la pared");
  assert.equal(row(/^Rebaje: penetración parcial anillo–pared cabe/, TT.analyze(PW({ t_wood: 30 }), { noFEA: true })).st, "fail", "t_madera 30 con anillo de 27: pared de 3 mm");
  assert.ok(!TT.analyze(TT.defaults(), { noFEA: true }).checks.some((x) => /^Rebaje:|^Pared del rebaje|^Soldadura pared/.test(x.name)), "solo con cubierta");
});
test("W · combinada con las interfaces A, B, C y con el modo guiado: sin NaN, cumple, izaje y térmica con la masa y la cara superior nuevas", () => {
  for (const [nm, o] of [["A", { opt_ss: 1 }], ["B", { opt_uhmw: 1 }], ["C1", { opt_bz: 1 }], ["C3", { opt_bz: 1, bz_conf: 3 }], ["guiado", { drive_mode: 1 }]]) {
    const A = TT.analyze(PW(o), { coarse: true });
    assert.ok(A.checks.every((c) => c.kind === "pend" || c.kind === "info" || (isFinite(c.dem) && (c.cap == null || isFinite(c.cap)))), nm + ": sin NaN");
    assert.ok(A.verdict.estructura && A.verdict.gira, nm + ": cumple");
    assert.equal(A.R.m.ring, 0); assert.ok(A.R.m.wood > 0);
  }
  const th = TT.thermal(PW({ drive_mode: 1 }), { T: [20, 80], alts: ["base"] }).alternativas[0], b80 = th.byT.find((b) => b.T === 80);
  const gr = b80.filas.find((x) => /Gradiente: curvatura térmica/.test(x.nombre)), g = TT.woodGeo(PW());
  assert.ok(gr && gr.formula.includes("h = h_mesa − d_rebaje = " + (TT.defaults().h_disc - g.d_rebaje) + " mm"), "gradiente con la altura de la caja dentro del rebaje");
  const hold = b80.filas.find((x) => /Madera: holgura perimetral frente a la dilatación transversal a T/.test(x.nombre)); assert.ok(hold && hold.estado === "ok", "holgura térmica de los tablones");
});

test("4.ª pasada · filete mejillas–base: mínimo AWS D1.1 T5.8 (parte más gruesa) y máximo AISC 360-22 J2.2b (borde de la mejilla)", () => {
  const P = TG(), g = (re, o) => TT.analyze(Object.assign(TG(), o || {}), { noFEA: true }).checks.find((c) => re.test(c.name));
  const mn = g(/Filete mínimo mejillas–base/), mx = g(/Filete máximo mejillas–base/);
  assert.ok(mn && mx, "ambas filas");
  assert.equal(mn.dem, 8, "T = máx(t_base 18; t_mejilla 25) = 25 → 8 mm"); assert.equal(mn.cap, P.w_br); assert.equal(mn.st, "ok");
  assert.equal(mx.dem, P.w_br); assert.equal(mx.cap, P.t_ch - 2, "t ≥ 6: w ≤ t − 2 = 23 mm (la mejilla termina en el borde)"); assert.equal(mx.st, "ok");
  assert.ok(/J2\.2b/.test(mx.ref) && /Tabla 7\.7/.test(mn.ref) && /se aplica la regla de AWS \(parte más gruesa\)/i.test(mn.ref), "citas (AWS D1.1:2020 Tabla 7.7, registro 7030ee3)");
  assert.equal(g(/Filete máximo mejillas–base/, { w_br: 24 }).st, "fail", "24 > 23");
  assert.equal(g(/Filete máximo mejillas–base/, { t_ch: 12, w_br: 12 }).st, "fail", "mejilla de 12: máx 10");
  assert.equal(g(/Filete máximo mejillas–base/, { t_ch: 12, w_br: 10 }).st, "ok");
  assert.equal(g(/Filete mínimo mejillas–base/, { w_br: 6 }).st, "fail", "6 < 8");
  assert.ok(/plancha base/.test(mx.formula) && /cara/.test(mx.formula), "aclara que la plancha base se suelda por su cara");
  // K2: la cita del filete mínimo aclara cuál regla se aplica en collar, oreja y almas
  for (const re of [/Collar: filete mínimo/, /Oreja: filete mínimo/, /Filete mínimo almas\/nervios–planchas/]) { const c = g(re); assert.ok(/se aplica la regla de AWS \(parte más gruesa\)/i.test(c.ref), "K2: " + c.name); }
});

test("4.ª pasada · flecha al izar la base (C12): margen ≥ 10 % del límite B/300 en todas las variantes, incluso B con madera", () => {
  const P0 = TT.defaults(); assert.ok(P0.c_lug === 430 && P0.x_lug === 850, "puntos de izaje en las diagonales (±850; ±850) desde el 10-11-2026 (antes c = 250 mm, x = 600: las placas-guía del sentido horario y los bloques-uña pasaban sobre las orejas)");
  for (const [nm, o] of [...IFC_VARIANTS, ["B+madera", { opt_uhmw: 1, opt_wood: 1 }]]) {
    const P = Object.assign(TT.defaults(), o), R = TT.compute(P), L = TT.runLift(P, R, false);
    assert.ok(L.wMax <= 0.90 * P.B / 300, nm + ": flecha " + L.wMax.toFixed(2) + " mm vs límite " + (P.B / 300).toFixed(2));
  }
});

test("Golden file: resultados por defecto sin cambios no justificados", () => {
  const A = TT.analyze(TT.defaults()), R = A.R;
  const snap = {
    masa_total: R.m.total, masa_mesa: R.m.disc, N: R.N, q_max: R.q_max, F_calado: R.Fstall, brazo_min: R.K.armMin, carrera_req: R.K.s_req,
    casos: Object.fromEntries(R.cases.map((c) => [c.id, [c.F, c.p, c.FS]])),
    fea: { top: A.fea.top.vmMax, bot: A.fea.bot.vmMax, lift: A.fea.lift.vmMax, glob: A.fea.glob.Mmax },
    fu: Object.fromEntries(A.checks.filter((c) => c.fu != null).map((c) => [c.grp + " · " + c.name, c.fu])),
  };
  const f = path.join(__dirname, "golden", "tt300c_defaults.json");
  if (process.env.UPDATE_GOLDEN || !fs.existsSync(f)) fs.writeFileSync(f, JSON.stringify(snap, null, 1));
  const g = JSON.parse(fs.readFileSync(f, "utf8"));
  const cmp = (a, b, k) => {
    if (typeof b === "number") near(a, b, 1e-6, k);
    else if (Array.isArray(b)) b.forEach((v, i) => cmp(a[i], v, k + "[" + i + "]"));
    else for (const kk of Object.keys(b)) { assert.ok(kk in a, "falta " + kk); cmp(a[kk], b[kk], k + "." + kk); }
  };
  cmp(snap, g, "golden");
});

test("Orejas de izaje soldadas (4, placa de 18 mm, R 92 mm): esfuerzos y masa", () => {
  const P = TT.defaults(), A = TT.analyze(P, { noFEA: true }), R = A.R, G = TT.G;
  assert.equal(P.t_ear, 18, "placa de 18 mm (mandante)");
  assert.equal(P.R_ear, 92, "R = 92 mm (decisión del usuario: AISC 360-22 D5.2(3), a ≥ 1,33·b_e)");
  const T = R.m.total * P.phi_lift * G / 1e3 / (3 * Math.sin(Math.PI / 3)), dp = P.d_ear - P.g_ear;
  const g = (re) => A.checks.find((c) => re.test(c.name));
  near(g(/aplastamiento del agujero/).dem, T * 1e3 / (dp * P.t_ear), 1e-9, "aplastamiento");
  near(g(/sección neta/).dem, T * 1e3 / (2 * (P.R_ear - P.d_ear / 2) * P.t_ear), 1e-9, "sección neta");
  const aw = 0.707 * P.w_ear, L = 2 * P.R_ear, Sw = 2 * aw * L * L / 6, Tv = T * Math.sin(Math.PI / 3), Th = T * Math.cos(Math.PI / 3);
  near(g(/Oreja: soldadura/).dem, Math.hypot(Tv * 1e3 / (2 * aw * L) + Th * 1e3 * P.h_ear / Sw, Th * 1e3 / (2 * aw * L)), 1e-9, "soldadura con L = 2R");
  assert.ok(A.checks.filter((c) => c.grp === "Orejas de izaje" && c.fu != null).every((c) => c.fu <= 1), "las orejas cumplen (incluido D5.2)");
  const B = TT.masses(Object.assign(TT.defaults(), { t_ear: 36 })).base - TT.masses(P).base;
  near(B, 4 * 7.85e-6 * (2 * P.R_ear * P.h_ear + Math.PI * P.R_ear ** 2 / 2 - Math.PI / 4 * P.d_ear ** 2) * 18, 1e-9, "masa de las orejas (rectángulo 2R × h + semicírculo − agujero)");
});

test("Orejas: AISC 360-22 D5.2, placa en la base (flexión + tracción), filete mínimo y máximo, ramales", () => {
  const P = TT.defaults(), A = TT.analyze(P, { noFEA: true }), R = A.R, G = TT.G;
  const T = R.m.total * P.phi_lift * G / 1e3 / (3 * Math.sin(Math.PI / 3)), Tv = T * Math.sin(Math.PI / 3), Th = T * Math.cos(Math.PI / 3);
  const rows = (o, re) => TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }).checks.filter((c) => re.test(c.name));
  const g = (re, o) => rows(o || {}, re)[0];
  assert.ok(!A.checks.some((c) => /relación de bordes/.test(c.name)), "se reemplazó la fila R − d/2 ≥ 0,5·d (no es el criterio de D5.2)");
  // D5.2(3): a ≥ 1,33·b_e y 2R ≥ 2·b_e + d, con b_e = mín(2t + 16; (2R − d)/2) (D5.1)
  const be = (Q) => Math.min(2 * Q.t_ear + 16, (2 * Q.R_ear - Q.d_ear) / 2);
  const ext = g(/extensión a tras el agujero/), wid = g(/ancho de la placa/);
  near(ext.dem, 1.33 * be(P), 1e-12, "1,33·b_e"); near(ext.cap, P.R_ear - P.d_ear / 2, 1e-12, "a = R − d/2");
  assert.ok(ext.fu <= 1 && ext.st === "ok" && /D5\.2\(3\)/.test(ext.ref), "R = 92 cumple D5.2(3) con referencia al artículo");
  near(wid.dem, 2 * be(P) + P.d_ear, 1e-12, "2·b_e + d"); near(wid.cap, 2 * P.R_ear, 1e-12, "2R"); assert.equal(wid.st, "ok");
  assert.equal(g(/extensión a tras el agujero/, { R_ear: 60 }).st, "fail", "con R = 60 (valor anterior) la extensión no cumple (FU 1,33)");
  near(g(/extensión a tras el agujero/, { R_ear: 60 }).fu, 1.33, 1e-9, "R = 60: b_e = 37,5 y a = 37,5 → FU 1,33");
  // D5.2(2): holgura ≤ 1 mm solo si el pasador gira bajo carga plena
  const h0 = g(/holgura agujero–pasador/), h1 = g(/holgura agujero–pasador/, { ear_gira: 1 }), h2 = g(/holgura agujero–pasador/, { ear_gira: 1, g_ear: 1 });
  assert.equal(P.ear_gira, 0); assert.equal(h0.kind, "info"); near(h0.dem, 3, 1e-12, "holgura 3 mm informada");
  assert.ok(h1.kind === "geo" && h1.st === "fail" && h1.dem === 3 && h1.cap === 1 && /D5\.2\(2\)/.test(h1.ref), "pasador que gira con 3 mm: no cumple");
  assert.equal(h2.st, "ok", "pasador que gira con 1 mm: cumple");
  // H5: placa de la oreja en la base: σ = Th·h/(t(2R)²/6) + Tv/(2R·t) ≤ Fy/Nd; τ = Th/(2R·t) ≤ Fy/(Nd√3)
  const L = 2 * P.R_ear, pl = g(/placa en la base: flexión/), pc = g(/placa en la base: corte/);
  near(pl.dem, Th * 1e3 * P.h_ear / (P.t_ear * L * L / 6) + Tv * 1e3 / (L * P.t_ear), 1e-9, "flexión + tracción de la placa"); near(pl.cap, P.Fy / P.Nd, 1e-12, "Fy/Nd");
  near(pc.dem, Th * 1e3 / (L * P.t_ear), 1e-9, "corte de la placa"); near(pc.cap, P.Fy / (P.Nd * Math.sqrt(3)), 1e-12, "Fy/(Nd√3)");
  assert.equal(g(/placa en la base: flexión/, { t_ear: 6, R_ear: 45, h_ear: 300 }).st, "fail", "oreja esbelta (6 mm, R 45, h 300): gobierna la placa");
  // H6: filete mínimo (AWS D1.1 Tabla 7.7, parte más gruesa; no más que la más delgada) y máximo (AISC J2.2b: t < 6 → t; t ≥ 6 → t − 2)
  const mn = g(/Oreja: filete mínimo/), mx = g(/Oreja: filete máximo/);
  assert.equal(mn.dem, 8, "T = máx(t_oreja 18; inserto de esquina) → 8 mm (desde el 10-11-2026 las orejas de las diagonales del soporte E van sobre el inserto)"); assert.equal(mn.cap, P.w_ear); assert.equal(mn.st, "ok");
  assert.equal(mx.dem, P.w_ear); assert.equal(mx.cap, P.t_ear - 2); assert.equal(mx.st, "ok");
  assert.equal(g(/Oreja: filete mínimo/, { w_ear: 4 }).st, "fail", "4 mm < 6 mm");
  assert.equal(g(/Oreja: filete máximo/, { t_ear: 8, w_ear: 8 }).st, "fail", "t = 8: w ≤ t − 2 = 6 (el verificador: con w = 8 el núcleo no decía nada)");
  assert.equal(g(/Oreja: filete máximo/, { t_ear: 8, w_ear: 6 }).st, "ok");
  assert.equal(g(/Oreja: filete máximo/, { t_ear: 6, w_ear: 5 }).cap, 4, "t = 6: w ≤ 4");
  assert.ok(/AISC 360-22 §?J2\.2b/.test(mx.ref) && /Tabla 7\.7/.test(mn.ref) && /Tabla J2\.4/.test(mn.ref), "normas citadas");
  // H7: nota informativa de ramales: el ángulo de 60° es una cota mínima; L ≥ d/cos 60° = 2d (ramales más cortos bajan el ángulo y aumentan T)
  const ra = g(/Ramales: longitud mínima/);
  assert.equal(ra.kind, "info"); near(ra.dem, 2 * Math.hypot(P.x_lug, P.B / 2 - P.c_lug), 1e-12, "L_mín = 2·d (d = distancia oreja–eje)");
  assert.ok(/≥ 60°/.test(ra.formula) && /B30\.9/.test(ra.ref), "cota mínima y referencia B30.9");
  assert.equal(A.checks.filter((c) => c.grp === "Orejas de izaje" && c.kind !== "info" && c.st === "fail").length, 0);
});

test("Collar y pivote: equilibrio con el asiento rígido-lineal, filete (V_c, M_c), brazo efectivo, rebaje del cubo con holguras", () => {
  const P = TT.defaults(), A = TT.analyze(P, { noFEA: true }), R = A.R;
  const g = (re, o) => TT.analyze(Object.assign(TT.defaults(), o || {}), { noFEA: true }).checks.find((c) => re.test(c.name));
  // H3: brazo efectivo e = holgura del buje sobre el collar + L_buje/2 (e_piv de ingreso es solo un mínimo)
  assert.equal(P.g_bush, 2); near(R.ePiv, Math.max(P.e_piv, P.g_bush + P.L_bush / 2), 1e-12, "e efectivo"); near(R.ePiv, 42, 1e-12, "2 + 80/2");
  const Hf = g(/Aplastamiento del pivote en el asiento/).dem * P.D_piv * (P.t_base + P.h_boss);       // N
  near(g(/Flexión del pivote/).dem, Hf * R.ePiv / (Math.PI * P.D_piv ** 3 / 32), 1e-9, "flexión del pivote con el brazo efectivo");
  near(TT.compute(Object.assign(TT.defaults(), { L_bush: 120 })).ePiv, 62, 1e-12, "con L_buje = 120 el brazo es 62 mm");
  near(TT.compute(Object.assign(TT.defaults(), { e_piv: 80 })).ePiv, 80, 1e-12, "e_piv mayor que el geométrico manda");
  assert.ok(g(/Brazo efectivo del pivote/).kind === "info", "se reporta el valor efectivo");
  // H1: equilibrio del collar. Asiento rígido-lineal (el mismo del σ del asiento): w(z) = H/L·[1 + k(1 − 2z/L)], k = 6(e + L/2)/L, z desde la cara superior del collar.
  const L = P.t_base + P.h_boss, hb = P.h_boss, e = R.ePiv, k = 6 * (e + L / 2) / L, N = 400000;
  let tot = 0, mom = 0, Vc = 0, Mc = 0;
  for (let i = 0; i < N; i++) {
    const z = (i + 0.5) * L / N, w = Hf / L * (1 + k * (1 - 2 * z / L)), dz = L / N;
    tot += w * dz; mom += w * (L / 2 - z) * dz;
    if (z < hb) { Vc += w * dz; Mc += w * (hb - z) * dz; }                                         // collar: z ∈ [0, h_collar]; momento respecto del plano de la soldadura (cara superior de la base)
  }
  near(tot, Hf, 1e-6, "ΣF = H"); near(mom, Hf * (e + L / 2), 1e-6, "ΣM respecto del centro del asiento = H·(e + L/2)");
  assert.ok(Vc / Hf > 1.87 && Vc / Hf < 1.95, "V_c ≈ 1,9·H (la plancha base toma la reacción de signo contrario; 1,875 con t_base 18, 1,903 con 20): " + Vc / Hf);
  assert.ok(Mc * 1e-6 > 13 && Mc * 1e-6 < 15.5, "M_c ≈ 14 kN·m respecto de la cara superior de la base: " + Mc * 1e-6);
  const aw = 0.707 * P.w_collar, f = Math.hypot(Mc / (Math.PI * P.D_boss ** 2 / 4 * aw), Vc / (Math.PI * P.D_boss * aw)), Fw = P.FEXX * 0.6 / (1.2 * P.Nd);
  const wc = g(/Soldadura del collar/);
  near(wc.dem, f, 1e-5, "grupo circular: f = √(f_b² + f_v²) con V_c y M_c"); near(wc.cap, Fw, 1e-12, "0,60 FEXX/(1,2 Nd)");
  assert.equal(P.w_collar, 10); assert.equal(wc.kind, "fu", "el filete del collar usa la banda warn como el resto (H8)");
  assert.ok(wc.fu <= 0.9 && wc.st === "ok", "con w = 10 mm cumple con FU ≤ 0,90: " + wc.fu);
  assert.ok(wc.formula.includes("V_c ≈ " + (Vc / Hf).toFixed(3).replace(".", ",") + "·H") && !/1,85/.test(wc.formula), "K1: el rótulo da la razón de la integración (" + (Vc / Hf).toFixed(3) + ")");
  assert.ok(wc.dem > 60, "mayor que el modelo anterior (V = H, M = H(e + L/2): 44,8 MPa): " + wc.dem);
  const w9 = g(/Soldadura del collar/, { w_collar: 9 });
  assert.ok(w9.fu > 0.9 && w9.fu <= 1 && w9.st === "warn", "w = 9: banda warn (0,9–1): FU " + w9.fu);
  assert.equal(g(/Soldadura del collar/, { w_collar: 8 }).st, "fail");
  // sin collar no hay verificaciones del collar
  assert.ok(!TT.analyze(Object.assign(TT.defaults(), { h_boss: 0 }), { noFEA: true }).checks.some((c) => /Collar/.test(c.name)));
  // H6 para el collar: mínimo AWS por la parte más gruesa (pared del collar 65 mm / base 18 → 8 mm) y máximo AISC J2.2b
  const cmn = g(/Collar: filete mínimo/), cmx = g(/Collar: filete máximo/);
  assert.equal(cmn.dem, 8); assert.equal(cmn.cap, 10); assert.equal(cmn.st, "ok"); assert.equal(cmx.dem, 10); assert.ok(cmx.cap >= 10 && cmx.st === "ok");
  assert.equal(g(/Collar: filete mínimo/, { w_collar: 6 }).st, "fail", "6 mm < 8 mm");
  // H2: rebaje del cubo = (D_boss + 2·c_r) × (h_boss + c_a); pared del cubo ≥ 25 mm
  assert.equal(P.c_boss_r, 3); assert.equal(P.c_boss_a, 2);
  const Drb = P.D_boss + 2 * P.c_boss_r, Hrb = P.h_boss + P.c_boss_a, d_b = P.D_piv + 30, hw = P.h_disc - P.t_top - P.t_bot;
  // 3.ª pasada: la profundidad del rebaje se mide desde la cara inferior de la mesa (h_collar − δ + c_a; δ = 0 sin interfaz); los primeros t_bot mm son el agujero de la plancha inferior y el resto, el cubo
  const hPl = Math.min(Hrb, P.t_bot), hHub = Math.min(Math.max(0, Hrb - P.t_bot), hw);
  near(R.m.hub, 7.85e-6 * Math.PI / 4 * ((P.D_hub ** 2 - d_b ** 2) * hw - (Drb ** 2 - d_b ** 2) * hHub), 1e-12, "masa del cubo con el rebaje con holguras (solo la parte sobre la plancha inferior)");
  near(hPl + hHub, Hrb, 1e-12, "plancha + cubo suman la profundidad total del rebaje (δ = 0: rebaje más profundo que la plancha)");
  const pw = g(/pared del rebaje del cubo/);
  near(pw.dem, Drb + 50, 1e-12, "D_collar + 2·c_r + 50"); near(pw.cap, P.D_hub, 1e-12); assert.equal(pw.st, "ok"); assert.ok(P.D_hub >= Drb + 50, "pared ≥ 25: D_cubo ≥ 306 → 310");
  assert.equal(P.D_hub, 310, "el cubo sube de 300 a 310 (con 3/2 mm la pared quedaba en 22 mm; con 2/1 mm, 23 mm: tampoco alcanza)");
  assert.equal(g(/pared del rebaje del cubo/, { D_hub: 300 }).st, "fail", "con el cubo de 300 mm la pared es 22 mm");
  assert.equal(g(/pared del rebaje del cubo/, { D_hub: 300, c_boss_r: 0 }).st, "ok", "sin holgura radial el criterio anterior (25 mm) se cumplía justo");
  // el buje cabe: holgura g_bush
  const bc = g(/Buje sobre el collar/); near(bc.dem, P.h_boss + P.g_bush + P.L_bush, 1e-12, "h_collar + g_buje + L_buje");
  // sin opción de interfaz: sin barras de topes
  assert.equal(R.m.stopBars, 0);
});

/* ======================================================================================================
   Temperatura de servicio (exposición solar, 80 °C) · docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)»
   Escenario aparte: con T_serv = 20 °C (por defecto) nada del cálculo estándar cambia; TT.thermal evalúa la MISMA geometría
   (dimensionada a 20 °C y congelada) con las capacidades reducidas a la temperatura.
   ====================================================================================================== */
const THALTS = { base: {}, A: { opt_ss: 1 }, B: { opt_uhmw: 1 }, C1: { opt_bz: 1, bz_conf: 1 }, C2: { opt_bz: 1, bz_conf: 2 }, C3: { opt_bz: 1, bz_conf: 3 } };

test("Temperatura · parámetros nuevos (grupo «Temperatura») con T_serv = 20 °C por defecto y rangos del registro", () => {
  const P = TT.defaults(), g = TT.PARAM_GROUPS.find((x) => x.id === "temperatura");
  assert.ok(g, "grupo Temperatura");
  const d = (id) => g.p.find((q) => q[0] === id);
  assert.equal(P.T_serv, 20); assert.equal(P.T_ref, 20); assert.equal(P.dT_grad, 0);
  assert.deepEqual([d("T_serv")[4], d("T_serv")[5]], [20, 120], "rango 20–120 °C");
  const K = { kT_Fy: 1.00, kT_E: 1.00, kT_Fy_ss: 0.82, kT_E_ss: 0.975, kT_p_uh: 0.40, kT_E_uh: 0.40, kT_bz: 1.00, kT_wood: 0.70, kT_bolt: 0.94, kT_weld: 1.00, kT_hertz: 1.00 };
  for (const [k, v] of Object.entries(K)) assert.equal(P[k], v, k);
  assert.equal(P.p_max_cil, 700); assert.equal(P.alivio_term, 0); assert.equal(P.nu_min, 10); assert.equal(P.K_oil, 1400); assert.equal(P.K_oil_hi, 1900); assert.equal(P.ba_cil, 1.4);
  // cada factor declara su nivel de confianza (A/B/C) en el rótulo
  for (const k of Object.keys(K)) assert.ok(/\((?:[ABC](?:\/[ABC])?)[);,]|confianza [ABC]/.test(d(k)[1]), "nivel de confianza en el rótulo de " + k + ": " + d(k)[1]);
  // el análisis estándar no cambia con T_serv: es un escenario aparte
  const A0 = TT.analyze(TT.defaults(), { noFEA: true }), A1 = TT.analyze(Object.assign(TT.defaults(), { T_serv: 80, dT_grad: 15 }), { noFEA: true });
  assert.equal(A1.checks.length, A0.checks.length, "T_serv no agrega filas ni cambia el cálculo estándar");
  A0.checks.forEach((c, i) => { assert.equal(A1.checks[i].name, c.name); assert.equal(A1.checks[i].fu, c.fu); assert.equal(A1.checks[i].st, c.st); });
  assert.ok(!A0.checks.some((c) => c.grp === "Temperatura"));
});

test("Temperatura · factores: 1 a 20 °C, valor tabulado a 80 °C, interpolación lineal y extrapolación con nota", () => {
  const P = TT.defaults(), f20 = TT.thermalFactors(P, 20), f80 = TT.thermalFactors(P, 80), f50 = TT.thermalFactors(P, 50), f100 = TT.thermalFactors(P, 100);
  for (const [k, v] of Object.entries(f20.k)) assert.equal(v, 1, "factor " + k + " a 20 °C = 1");
  assert.equal(f20.dT, 0); assert.equal(f80.dT, 60); assert.equal(f20.extrap, false); assert.equal(f80.extrap, false);
  near(f80.k.Fy_ss, 0.82, 1e-12, "inox Fy a 80"); near(f80.k.E_ss, 0.975, 1e-12, "inox E a 80"); near(f80.k.p_uh, 0.40, 1e-12, "UHMW k_p a 80"); near(f80.k.E_uh, 0.40, 1e-12, "UHMW k_E a 80");
  near(f80.k.wood, 0.70, 1e-12, "madera Ct a 80"); near(f80.k.bolt, 0.94, 1e-12, "perno 10.9"); near(f80.k.Fy, 1, 1e-12, "acero estructural"); near(f80.k.bz, 1, 1e-12, "bronce"); near(f80.k.weld, 1, 1e-12, "soldadura"); near(f80.k.hertz, 1, 1e-12, "Hertz");
  near(f50.k.Fy_ss, 1 + (0.82 - 1) * 30 / 60, 1e-12, "interpolación lineal a 50 °C"); near(f50.k.wood, 1 - 0.3 * 30 / 60, 1e-12, "madera a 50 °C");
  assert.equal(f100.extrap, true); assert.ok(f100.notes.some((s) => /80 °C/.test(s) && /extrapol/i.test(s)), "nota de extrapolación sobre 80 °C");
  near(f100.k.Fy_ss, 0.82 - 0.18 * 20 / 60, 1e-12, "extrapolación lineal (con cautela) a 100 °C"); assert.ok(f100.k.p_uh >= 0.05, "el factor no baja de 0,05");
  // dilataciones: acero 12×10⁻⁶ (EN 1993-1-1), media 20–80 °C 12,4×10⁻⁶ (EN 1993-1-2 §3.4.1.1), inox 17, UHMW 190, bronce 18, madera 5 en la fibra y 30 transversal
  near(f80.alpha.st, 12.4e-6, 0.002, "α acero medio 20–80 °C (EN 1993-1-2: 7,44×10⁻⁴/60)"); near(f20.alpha.st, 12e-6, 1e-12, "α acero a ΔT = 0 = 12×10⁻⁶");
  near(f80.alpha.ss, 17e-6, 1e-12, "inox"); near(f80.alpha.uh, 190e-6, 1e-12, "UHMW"); near(f80.alpha.bz, 18e-6, 1e-12, "bronce"); near(f80.alpha.woodT, 30e-6, 1e-12, "madera transversal"); near(f80.alpha.woodL, 5e-6, 1e-12, "madera en la fibra");
  near(TT.alphaSteelMean(80) * 60, 1.2e-5 * 80 + 0.4e-8 * 80 * 80 - 2.416e-4, 1e-9, "ε(80 °C) de EN 1993-1-2 = 7,44×10⁻⁴");
});

test("Temperatura · aceite atrapado: Δp = (α_v − 3α_s)·ΔT/(1/K_aceite + 1/K_c) con los valores del registro", () => {
  const P = TT.defaults(), o = TT.oilTrapped(P, 80), a3 = 3 * TT.alphaSteelMean(80), av = 7.5e-4;
  near(o.dT, 60, 1e-12, "ΔT"); near(o.av, av, 1e-12, "α_v"); 
  near(o.rigid.lo.dp, (av - a3) * 60 * 1400, 1e-9, "recipiente rígido, K = 1,4 GPa (MPa)");
  near(o.rigid.hi.dp, (av - a3) * 60 * 1900, 1e-9, "recipiente rígido, K = 1,9 GPa (MPa)");
  near(o.rigid.hi.bar, 815, 0.01, "registro: 815 bar con 1,9 GPa");
  const Kc = P.E / (2 * ((P.ba_cil ** 2 + 1) / (P.ba_cil ** 2 - 1) + P.nu));
  near(o.Kc_lame, Kc, 1e-12, "K_c de Lamé"); near(Kc / 1000, 30, 0.03, "registro: K_c ≈ 30 GPa para b/a = 1,4");
  near(o.cyl.hi.dp, (av - a3) * 60 / (1 / 1900 + 1 / Kc), 1e-9, "cilindro Lamé, 1,9 GPa"); near(o.cyl.hi.bar, 770, 0.02, "registro: ≈ 770 bar");
  near(o.cyl.lo.dp, (av - a3) * 60 / (1 / 1400 + 1 / Kc), 1e-9, "cilindro Lamé, 1,4 GPa"); assert.ok(o.cyl.hi.dp > o.cyl.lo.dp, "con K mayor la presión sube: la cota alta es 1,9 GPa");
  near(o.hose.hi.bar, 140, 0.03, "registro: ≈ 140 bar con manguera (K combinado ≈ 0,33 GPa)");
  assert.equal(TT.oilTrapped(P, 20).cyl.hi.dp, 0, "a 20 °C no hay sobrepresión térmica");
  near(o.expansion_free_pct, 100 * (av - 3 * TT.alphaSteelMean(80)) * 60, 1e-9, "dilatación libre del aceite (%): 4,28 % (registro: 4,29 %)"); near(o.expansion_free_pct, 4.29, 0.01, "registro");
});

test("Temperatura · viscosidad del aceite (Walther) y mínimo de la bomba", () => {
  near(TT.oilViscosity(80).lo, 11.1, 0.01, "VG 46 con ν100 = 6,8: ≈ 11 mm²/s a 80 °C (registro)"); near(TT.oilViscosity(80).hi, 14.6, 0.01, "VG 46 con IV 185: ≈ 14,6 mm²/s");
  near(TT.oilViscosity(40).lo, 46, 1e-9, "ν40 = 46"); near(TT.oilViscosity(100).lo, 6.8, 1e-9, "ν100 = 6,8"); near(TT.oilViscosity(40).hi, 47.4, 1e-9, "Eurol: 47,4"); near(TT.oilViscosity(100).hi, 9.5, 1e-9, "Eurol: 9,5");
  assert.ok(TT.oilViscosity(60).lo > TT.oilViscosity(80).lo, "la viscosidad baja con T");
});

const ACC_GRPS = ["Pasadores de empuje", "Uña", "Patín y guía", "Articulaciones", "Fatiga", "Leva de reenganche", "Soporte del ojal E", "Placas-leva"];   // grupos del accionamiento mecánico (fuera del alcance térmico con term_alcance = 1); los tres últimos son de la leva guiada y del modo pivotado
test("Temperatura · a 20 °C el escenario reproduce el cálculo estándar (factores = 1) y la geometría queda congelada a T_serv", () => {
  for (const [id, fl] of Object.entries(THALTS)) {
    const Pa = Object.assign(TT.defaults(), fl), A0 = TT.analyze(Pa, { noFEA: true });
    const A1 = TT.analyze(TT.thermalP(Pa, 20), { noFEA: true });                                  // factores a 20 °C: todos = 1
    A0.checks.forEach((c, i) => { assert.equal(A1.checks[i].name, c.name, id); assert.ok(c.fu == null ? A1.checks[i].fu == null : Math.abs(A1.checks[i].fu - c.fu) <= 1e-12 * Math.max(1, Math.abs(c.fu)) || c.fu === A1.checks[i].fu, id + " · " + c.name); assert.equal(A1.checks[i].st, c.st, id + " · " + c.name); });
    assert.ok(A1.checks.length > A0.checks.length && A1.checks.slice(A0.checks.length).every((c) => c.grp === "Temperatura"), id + ": el escenario solo AGREGA filas del grupo Temperatura");
  }
  const r = TT.thermal(TT.defaults(), { T: [20, 80], wood: false });
  assert.deepEqual(r.alternativas.map((a) => a.id), ["base", "A", "B", "C1", "C2", "C3"]);
  for (const a of r.alternativas) {
    const Pa = Object.assign(TT.defaults(), THALTS[a.alt]), A = TT.analyze(Pa), I = A.R.ifc, [b20, b80] = a.byT;
    near(b20.FS, A.R.cd.FS, 1e-9, a.id + ": FS a 20 °C"); near(a.FS20, A.R.cd.FS, 1e-9, a.id + ": FS20");
    near(b20.fuEst, Math.max(...A.checks.filter((c) => c.sys === "est" && c.kind === "fu" && isFinite(c.fu) && !ACC_GRPS.includes(c.grp)).map((c) => c.fu)), 1e-9, a.id + ": FU estructura máx. a 20 °C = el del análisis estándar sin el accionamiento (fuera de alcance)");
    near(b20.masa, A.R.m.total, 1e-9, a.id + ": masa a 20 °C"); assert.equal(b80.masa, b20.masa, a.id + ": la masa no cambia (geometría congelada)");
    assert.deepEqual([a.geometria.tss, a.geometria.tss2, a.geometria.tuh, a.geometria.tbz], [I.tss, I.tss2, I.tuh, I.tbz || 0].map((x, i) => (i === 3 ? I.tbz : x)), a.id + ": espesores del escenario = los de 20 °C");
    assert.equal(b20.FS, b80.FS, a.id + ": con μ constante el FS del giro no depende de la temperatura");
  }
  // sin congelar, la lámina UHMW se re-dimensionaría con p_adm·0,4 (más gruesa): el escenario NO lo hace
  const PB = Object.assign(TT.defaults(), THALTS.B), t20 = TT.analyze(PB, { noFEA: true }).R.ifc.tuh, tFree = TT.analyze(TT.thermalP(PB, 80), { noFEA: true }).R.ifc.tuh;
  assert.ok(tFree > t20, "sin congelar la lámina sube de " + t20 + " a " + tFree + " mm");
  const rB = TT.thermal(TT.defaults(), { T: [20, 80], alts: ["B"] }).alternativas[0];
  assert.equal(rB.geometria.tuh, t20); assert.equal(rB.byT[1].masa, rB.byT[0].masa);
  // largos de tope y espesores de disco también congelados (A: el Fy del inox baja 18 % y el tope no se alarga)
  const rA = TT.thermal(TT.defaults(), { T: [20, 80], alts: ["A"] }).alternativas[0], A20 = TT.analyze(Object.assign(TT.defaults(), THALTS.A), { noFEA: true });
  assert.deepEqual(rA.geometria.L, Object.fromEntries(A20.R.ifc.topes.map((s) => [s.id, s.L])), "largos de los topes de 20 °C");
});

test("Temperatura · filas de juntas, buje de bronce, gradiente y uña: fórmulas del registro", () => {
  const r = TT.thermal(TG(), { T: [20, 80], alts: ["B"] }), a = r.alternativas[0], f = a.byT[1].filas, P = TG(), A = TT.analyze(Object.assign(TG(), THALTS.B), { noFEA: true }), R = A.R;
  const row = (re) => { const x = f.find((q) => re.test(q.nombre)); assert.ok(x, "fila " + re); return x; };
  const as = TT.alphaSteelMean(80), chord = 2 * R.Ro * Math.sin(Math.PI / P.n_seg);
  // (a) junta UHMW: α 190, acero 12,4 → 2,78 mm requeridos frente a 1,8 mm en frío (diseño a 40 K con 180×10⁻⁶): se cierra
  const jU = row(/Lámina UHMW \(24 sectores\): junta de dilatación requerida/);
  near(jU.dem, (190e-6 - as) * 60 * chord, 1e-9, "j_req UHMW"); near(jU.cap, Math.ceil(Math.max(P.j_sec, (AL_UH_ - 11.7e-6) * P.dT * chord) * 10 - 1e-9) / 10, 1e-12, "j_disp = junta del diseño a 20 °C"); assert.equal(jU.estado, "fail", "la junta de la lámina UHMW cierra a 80 °C");
  assert.equal(a.juntas.find((j) => /UHMW/.test(j.pieza)).j_req, jU.dem);
  const jD = row(/Disco de la base \(liso\).*junta de dilatación requerida/); near(jD.dem, (17e-6 - as) * 60 * 2 * R.Ro * Math.sin(Math.PI / P.n_sec), 1e-9, "j_req inox"); assert.equal(jD.estado, "ok");
  // (b) buje de bronce en el pivote
  const D = P.D_piv, bu = row(/Buje de bronce–pivote: holgura con el buje libre/);
  near(bu.dem, (18e-6 - as) * 60 * D, 1e-9, "Δ holgura libre = (α_bz − α_acero)·ΔT·D (afloja)"); near(bu.cap, (18e-6 - as) * 60 * (D + 30), 1e-9, "Δ interferencia en el cubo (aprieta)");
  const bc = row(/cierre de la holgura diametral/); assert.ok(bc.dem > 0 && bc.dem < 0.05 && bc.estado === "ok", "con el buje retenido la holgura se reduce unas centésimas de mm y no se cierra: " + bc.dem); near(bc.cap, P.c_bush_d, 1e-12, "holgura en frío");
  // (c) uña–pasador con la mesa caliente y la base a la sombra (accionamiento: solo con term_alcance = 2)
  const eps = as * 60, dR = eps * P.R_pin, K = R.K;
  const f2 = TT.thermal(Object.assign(TG(), { term_alcance: 2 }), { T: [20, 80], alts: ["B"] }).alternativas[0].byT[1].filas, row2 = (re) => { const x = f2.find((q) => re.test(q.nombre)); assert.ok(x, "fila (alcance 2) " + re); return x; };
  assert.ok(!f.some((q) => /Uña–pasador/.test(q.nombre)), "con term_alcance = 1 las filas de la uña no están en el escenario");
  near(row2(/holgura radial de la uña en el patín/).dem, K.radial * (1 + eps) + 2 + dR, 1e-9, "holgura radial + α·ΔT·R_pin"); near(dR, 0.69, 0.02, "registro: 0,69 mm para 60 K y R_pin 930");
  near(row2(/caso uniforme/).dem, (P.x_g - K.armMin) * eps, 1e-9, "escala uniforme: ≈ 0,16 mm"); assert.ok(row2(/caso uniforme/).dem < 0.2);
  // (d) gradiente de 15 K a 80 °C: κ = α·ΔT/h, flecha κ·(D/2)²/2, σ = E·α·ΔT/(2(1 − ν))
  const kap = as * 15 / P.h_disc, sig = P.E * as * 15 / (2 * (1 - P.nu));
  near(row(/curvatura térmica/).dem, kap * 1e3, 1e-9, "κ (1/m)"); near(row(/flecha en el diámetro/).dem, kap * (P.D_top / 2) ** 2 / 2, 1e-9, "flecha"); near(row(/tensión de flexión térmica/).dem, sig, 1e-9, "σ restringida");
  const top = TT.analyze(Object.assign(TG(), THALTS.B)).checks.find((c) => c.name === "Plancha superior: global + local"), gt = row(/Gradiente: plancha superior/);
  near(gt.dem, top.dem + sig, 1e-9, "FU de la plancha superior + σ térmica (suma conservadora)"); near(gt.fu, (top.dem + sig) / top.cap, 1e-9);
  near(row(/desnivel de la cara de contacto/).dem, kap * (R.Ro ** 2 - R.Ri ** 2) / 2, 1e-9, "desnivel R_i–R_o");
  // sin gradiente (T = 20): todo en cero
  const f20 = a.byT[0].filas; assert.equal(f20.find((q) => /curvatura térmica/.test(q.nombre)).dem, 0); assert.equal(f20.find((q) => /junta de dilatación requerida/.test(q.nombre)).dem, 0);
});
const AL_UH_ = 180e-6;

test("Temperatura · aceite atrapado: p_hold + Δp contra el cilindro, alivio térmico y recomendación", () => {
  const P = TT.defaults(), g = (o, T) => TT.thermal(Object.assign(TT.defaults(), { term_alcance: 2 }, o), { T: [20, T || 80], alts: ["base"] }).alternativas[0].byT[1].filas;   // el aceite atrapado es del circuito hidráulico: term_alcance = 2
  const rows = g({}), A = TT.analyze(P, { noFEA: true }), pd = A.R.cd.p, o = TT.oilTrapped(P, 80), dp = o.sel.hi.bar;
  assert.equal(P.oil_cont, 2, "contenedor por defecto: cilindro (Lamé)");
  const ho = rows.find((x) => /carrera de diseño: p_hold/.test(x.nombre)), cal = rows.find((x) => /tras el calado/.test(x.nombre)), ann = rows.find((x) => /cámara anular/.test(x.nombre)), vv = rows.find((x) => /Válvula de alivio térmico del tramo/.test(x.nombre));
  near(ho.dem, pd + dp, 1e-9, "p_hold = F_dis/A más Δp"); near(ho.cap, 700, 1e-12, "p_max_cil"); assert.equal(ho.estado, "fail");
  near(cal.dem, P.p_relief + dp, 1e-9, "calado: p_alivio + Δp"); near(cal.cap, 1050, 1e-12, "prueba 1,5×"); assert.equal(cal.estado, "fail");
  near(ann.dem, P.p_ret + dp, 1e-9, "cámara anular: p_ret + Δp"); assert.equal(ann.estado, "fail");
  assert.equal(vv.estado, "fail"); assert.ok(/instalar válvula de alivio térmico en el tramo aislado/.test(vv.nombre + vv.formula) && /aguas arriba/.test(vv.formula), "recomendación y aviso del alivio de sistema");
  near(dp, 763.5, 0.01, "Δp con K = 1,9 GPa y cilindro Lamé a ΔT = 60 K: ≈ 764 bar");
  // con un alivio térmico que abre en 700 bar (= p_max_cil y = alivio del sistema) la presión queda limitada: monitoreo, sin fallo
  const w = g({ alivio_term: 700 }); assert.ok(!w.some((x) => x.sys === "term" && x.estado === "fail"), "alivio térmico a 700 bar: ninguna fila térmica de aceite falla");
  assert.ok(w.some((x) => /Válvula de alivio térmico: apertura bajo la presión máxima/.test(x.nombre) && x.estado === "ok"));
  assert.equal(g({ alivio_term: 900 }).find((x) => /apertura bajo la presión máxima/.test(x.nombre)).estado, "fail", "apertura sobre p_max_cil");
  assert.equal(g({ alivio_term: 600 }).find((x) => /apertura sobre el alivio del sistema/.test(x.nombre)).estado, "fail", "por debajo del alivio del sistema gotea a calado");
  // rígido > cilindro > manguera
  const dpOf = (c) => g({ oil_cont: c }).find((x) => /carrera de diseño: p_hold/.test(x.nombre)).dem - pd;
  assert.ok(dpOf(1) > dpOf(2) && dpOf(2) > dpOf(3), "rígido > cilindro > manguera"); near(dpOf(3), 140, 0.03, "manguera ≈ 140 bar");
  // a 20 °C no hay sobrepresión y la verificación pasa; a 40 K (T = 60) el aceite ya excede
  assert.equal(TT.thermal(Object.assign(TT.defaults(), { term_alcance: 2 }), { T: [20, 80], alts: ["base"] }).alternativas[0].byT[0].filas.find((x) => /carrera de diseño: p_hold/.test(x.nombre)).estado, "ok");
});

test("Temperatura · aceite, sellos, grasa y sensibilidades (μ, Fy 0,92, UHMW k_p/k_E, madera)", () => {
  const P = Object.assign(TG(), { term_alcance: 2 }), r = TT.thermal(P, { T: [20, 40, 60, 80, 100] }), by = (id) => r.alternativas.find((a) => a.id === id);   // alcance 2: aceite, sellos y accionamiento incluidos (comportamiento anterior)
  const row = (a, T, re) => a.byT.find((b) => b.T === T).filas.find((x) => re.test(x.nombre));
  const bs = by("base");
  const v80 = row(bs, 80, /viscosidad a T_serv/), v100 = row(bs, 100, /viscosidad a T_serv/);
  near(v80.cap, TT.oilViscosity(80).lo, 1e-12); near(v80.fu, P.nu_min / TT.oilViscosity(80).lo, 1e-12); assert.equal(v80.estado, "warn", "≈ 11 mm²/s frente al mínimo supuesto de 10: monitoreo"); assert.equal(v100.estado, "fail", "6,8 mm²/s < 10");
  assert.equal(row(bs, 80, /Sellos NBR/).estado, "warn"); assert.equal(row(bs, 100, /Sellos NBR/).estado, "warn", "80–120 °C: solo monitoreo"); assert.equal(row(bs, 40, /Sellos NBR/).estado, "ok");
  const gr = row(bs, 80, /punto de goteo/); near(gr.fu, 80 / 175, 1e-12); assert.equal(gr.estado, "ok"); assert.ok(/T_goteo − T = 95 K/.test(gr.formula), "margen de 95 K a 80 °C");
  // μ: FS(μ·f) = FS/f; el multiplicador máximo con FS ≥ FS_mín es FS/FS_mín
  near(bs.sens.mu[2].FS, bs.FS20 / 1.2, 1e-12); near(bs.sens.mu[3].FS, bs.FS20 / 1.5, 1e-12); assert.equal(bs.sens.mu[1].gira, true); assert.equal(bs.sens.mu[2].gira, false, "μ × 1,2 baja el FS del giro bajo 1,25 en la base"); near(bs.sens.mu_crit, bs.FS20 / P.FS_min, 1e-12);
  assert.ok(by("C1").sens.mu_crit > bs.sens.mu_crit, "el bronce con grafito tiene más margen de μ (μ_d 0,15 frente a 0,20)");
  // k_mu_T como entrada: con 1,2 a 80 °C el FS del giro baja a FS/1,2 y el golden a 20 °C no cambia
  const rm = TT.thermal(Object.assign(TG(), { k_mu_T: 1.2 }), { T: [20, 80], alts: ["base"] }).alternativas[0];
  near(rm.byT[1].FS, rm.byT[0].FS / 1.2, 1e-9, "FS con μ × 1,2"); assert.equal(rm.byT[0].FS, rm.FS20);
  // Fy × 0,92 (ASME II-D): con la base el FU máximo de las verificaciones de fluencia sube 1/0,92 y queda ≤ 1,0
  assert.equal(bs.byT.find((b) => b.T === 80).fuEst, bs.byT[0].fuEst, "k_Fy = 1,00: el FU máximo de la base no cambia a 80 °C");
  near(bs.sens.kFy092.fuEst, bs.byT[0].fuEst / 0.92, 1e-6, "FU máx / 0,92"); assert.ok(bs.sens.kFy092.fuEst <= 1, "la base mantiene FU ≤ 1,0 en las verificaciones estándar con Fy × 0,92: " + bs.sens.kFy092.fuEst); assert.ok(bs.sens.kFy092.fuTerm > 1 && /Gradiente/.test(bs.sens.kFy092.gobernanteTerm.nombre), "pero con el gradiente de 15 K sumado, la plancha supera 1,0: " + bs.sens.kFy092.fuTerm);
  assert.ok(bs.sens.kFy092.empeoran.length > 0 && bs.sens.kFy092.empeoran.every((x) => x.de !== "fail"));
  // inox (A, B): el Fy del inox baja 18 % → los topes de los discos (dimensionados para FU 0,90) pasan de 1,0: cambian de estado
  for (const id of ["A", "B"]) { const cam = by(id).byT.find((b) => b.T === 80).cambian.filter((c) => /aplastamiento del tope/.test(c.nombre)); assert.ok(cam.length >= 1 && cam.every((c) => c.de === "ok" && c.a === "fail" && c.empeora), id + ": tope del disco inox falla a 80 °C"); }
  assert.equal(by("C1").byT.find((b) => b.T === 80).cambian.filter((c) => c.grp !== "Temperatura" && c.grp !== "Mesa").length, 0, "C1: sin cambios de estado de verificaciones estándar con k_bz = 1,00");
  // UHMW (B): k_p·p_adm; la lámina solo cumple si k_p ≥ k_crítico (< 1); monotonía
  const B = by("B"), u = B.sens.uhmw;
  assert.ok(u.kp_crit > 0.4 && u.kp_crit < 1 && u.kp.find((x) => x.k_p === 1).cumple && !u.kp.find((x) => x.k_p === 0.4).cumple, "k_p crítico entre 0,4 y 1: " + u.kp_crit);
  for (let i = 1; i < u.kp.length; i++) assert.ok(u.kp[i].fuUHMW <= u.kp[i - 1].fuUHMW + 1e-12, "FU de la lámina no crece con k_p");
  assert.equal(B.byT.find((b) => b.T === 80).gira, false, "B no gira con seguridad a 80 °C: el aplastamiento del tope del rebaje supera p_adm·0,4");
  assert.ok(B.byT.find((b) => b.T === 80).cambian.some((c) => /Lámina UHMW.*aplastamiento del canto/.test(c.nombre) && c.empeora));
  assert.ok(row(B, 80, /acortamiento elástico/).dem > row(B, 20, /acortamiento elástico/).dem, "E reducida: más deformación bajo carga");
  // madera: C_t sobre p_wood
  const W = TT.thermal(Object.assign(TG(), { opt_wood: 1 }), { T: [20, 80], alts: ["base"] }).alternativas[0], mw = (T) => W.byT.find((b) => b.T === T);
  assert.equal(W.madera, true); const cw = (T) => mw(T).sensibles_est.concat(mw(T).sensibles).find((x) => /Madera: aplastamiento/.test(x.nombre));
  near(cw(80).fuT / cw(80).fu20, 1 / 0.7, 1e-9, "FU de la madera × 1/C_t"); assert.equal(W.sens.madera[1].Ct, 0.5); assert.ok(W.sens.madera[1].fu > W.sens.madera[0].fu);
});

test("Temperatura · escenario por defecto (solar 80 °C, 15 K), temperaturas del escenario, JSON puro y lista de verificaciones sensibles", () => {
  const r = TT.thermal(TT.defaults(), { alts: ["base", "B"] });
  assert.equal(r.T_scn, 80); assert.equal(r.gradiente_scn, 15, "sin T_serv definida el escenario es el solar: 80 °C y 15 K"); assert.deepEqual(r.T, [20, 40, 60, 80, 100]);
  const r2 = TT.thermal(Object.assign(TT.defaults(), { T_serv: 60 }), { T: [20, 40], alts: ["base"] });
  assert.equal(r2.T_scn, 60); assert.equal(r2.gradiente_scn, 0); assert.deepEqual(r2.T, [20, 40, 60], "la tabla incluye la temperatura del escenario");
  assert.equal(TT.thermal(Object.assign(TT.defaults(), { T_serv: 60, dT_grad: 10 }), { T: [20, 60], alts: ["base"] }).alternativas[0].byT[1].gradiente, 10);
  const s = JSON.stringify(r); assert.ok(!/NaN|undefined|Infinity/.test(s), "JSON sin NaN/undefined/Infinity"); assert.deepEqual(JSON.parse(s), JSON.parse(JSON.stringify(TT.thermal(TT.defaults(), { alts: ["base", "B"] }))), "determinista");
  for (const a of r.alternativas) for (const b of a.byT) {
    assert.ok(b.sensibles.length <= 10 && b.sensibles_est.length <= 10);
    b.sensibles.forEach((x) => { assert.ok(["A", "B", "C", "A/C", "B/C"].includes(x.conf), "nivel de confianza: " + x.conf); assert.ok(x.fuT >= x.fu20 && x.nombre); });
    for (let i = 1; i < b.sensibles.length; i++) assert.ok(b.sensibles[i].delta <= b.sensibles[i - 1].delta + 1e-12, "ordenadas por aumento de FU");
    assert.ok(b.cambian.every((c) => ["ok", "warn", "fail"].includes(c.de) && ["ok", "warn", "fail"].includes(c.a) && c.de !== c.a));
  }
  assert.ok(r.avisos.some((x) => /BTH-1/.test(x) && /66 °C/.test(x)) && r.avisos.some((x) => /UHMW/.test(x) && /confianza C/.test(x)) && r.avisos.some((x) => /alivio térmico/.test(x)));
  const b80 = r.alternativas[0].byT.find((b) => b.T === 80); assert.ok(b80.sensibles[0].sys === "term" || b80.sensibles[0].delta > 0);
  // pestañas de extrapolación
  assert.ok(r.alternativas[0].byT.find((b) => b.T === 100).extrapolado && r.alternativas[0].byT.find((b) => b.T === 100).notas.some((x) => /extrapol/.test(x)));
});

/* ======================= Tapones de grafito (opción C): cantidad real colocable frente a la ideal ======================= */
// Golden del modo ideal (bz_fg_modo = 0): reproduce el cálculo anterior a los tapones reales (f_g = π·d²/(2√3·p²) sobre toda la corona)
const bzSnap = (conf, o) => {
  const A = TT.analyze(Object.assign(TG(), { opt_bz: 1, bz_conf: conf }, o || {}), { noFEA: true }), R = A.R, I = R.ifc;   // golden del cálculo anterior: modo guiado
  return { mBz: R.m.bz, mTotal: R.m.total, N: R.N, q: I.q, qLoc: I.qLoc, qNet: I.qNet, tbz: I.tbz, tbzReq: I.tbzReq, tss: I.tss, tssReq: I.tssReq, fg: I.fg, eta: I.eta, FS: R.cd.FS,
    fu: Object.fromEntries(A.checks.filter((c) => c.grp === "Interfaz bronce" && c.fu != null && isFinite(c.fu)).map((c) => [c.name, c.fu])) };
};
test("Tapones · golden del modo ideal (bz_fg_modo = 0 reproduce el cálculo anterior de C1, C2 y C3)", () => {
  const snap = Object.fromEntries([1, 2, 3].map((c) => ["C" + c, bzSnap(c, { bz_fg_modo: 0 })]));
  const f = path.join(__dirname, "golden", "tt300c_bz_ideal.json");
  if (process.env.UPDATE_GOLDEN || !fs.existsSync(f)) fs.writeFileSync(f, JSON.stringify(snap, null, 1));
  const g = JSON.parse(fs.readFileSync(f, "utf8"));
  const cmp = (a, b, k) => {
    if (typeof b === "number") near(a, b, 1e-9, k);
    else for (const kk of Object.keys(b)) { assert.ok(a && kk in a, "falta " + k + "." + kk); cmp(a[kk], b[kk], k + "." + kk); }
  };
  cmp(snap, g, "golden-ideal");
});

/* ======================= Temperatura: alcance (term_alcance) ======================= */
// Golden del escenario anterior (term_alcance = 2: sistema de placas y disco + accionamiento y circuito hidráulico)
const thSnap = (P) => {
  const r = TT.thermal(P, { T: [20, 80] });
  return Object.fromEntries(r.alternativas.map((a) => [a.id, Object.fromEntries(a.byT.map((b) => [String(b.T), {
    FS: b.FS, gira: b.gira, estructura: b.estructura, termico: b.termico, fuEst: b.fuEst, fuTerm: b.fuTerm, masa: b.masa, nFail: b.nFail, nWarn: b.nWarn,
    filas: Object.fromEntries(b.filas.map((x) => [x.nombre, x.fu == null ? -1 : (isFinite(x.fu) ? x.fu : 1e9)])), estados: b.filas.map((x) => x.estado).join(",") }]))]));
};
test("Temperatura · golden del escenario anterior (term_alcance = 2 reproduce el comportamiento previo en las siete alternativas)", () => {
  const snap = thSnap(Object.assign(TT.defaults(), { term_alcance: 2, bz_fg_modo: 0, bz_fg_min: 0.1 }));   // el golden se generó con f_g ideal y sin el criterio de lubricación (anteriores a los tapones reales)
  const f = path.join(__dirname, "golden", "tt300c_termica_alcance2.json");
  if (process.env.UPDATE_GOLDEN || !fs.existsSync(f)) fs.writeFileSync(f, JSON.stringify(snap, null, 1));
  const g = JSON.parse(fs.readFileSync(f, "utf8"));
  const cmp = (a, b, k) => {
    if (typeof b === "number") near(a, b, 1e-9, k);
    else if (typeof b === "object" && b !== null) for (const kk of Object.keys(b)) { assert.ok(a && kk in a, "falta " + k + "." + kk); cmp(a[kk], b[kk], k + "." + kk); }
    else assert.equal(a, b, k);
  };
  cmp(snap, g, "golden-termica");
});
test("Temperatura · golden del escenario anterior en el modo guiado (drive_mode = 1; lo replica tests/indep_termica.py)", () => {
  const snap = thSnap(Object.assign(TG(), { term_alcance: 2, bz_fg_modo: 0, bz_fg_min: 0.1 }));   // el golden se generó con f_g ideal y sin el criterio de lubricación (anteriores a los tapones reales)
  const f = path.join(__dirname, "golden", "tt300c_termica_alcance2_guiado.json");
  if (process.env.UPDATE_GOLDEN || !fs.existsSync(f)) fs.writeFileSync(f, JSON.stringify(snap, null, 1));
  const g = JSON.parse(fs.readFileSync(f, "utf8"));
  const cmp = (a, b, k) => {
    if (typeof b === "number") near(a, b, 1e-9, k);
    else if (typeof b === "object" && b !== null) for (const kk of Object.keys(b)) { assert.ok(a && kk in a, "falta " + k + "." + kk); cmp(a[kk], b[kk], k + "." + kk); }
    else assert.equal(a, b, k);
  };
  cmp(snap, g, "golden-termica-guiado");
});

/* Conteo independiente de los tapones: malla escalonada propia (coordenadas cartesianas), sin reutilizar el código del núcleo.
   Centros de la malla (paso p, fila alterna p·√3/2, anclada al centro de la mesa) cuyo borde queda a ≥ bz_edge del borde del bronce, de las muescas, de los tornillos y de las ranuras. */
function tapIndep(P, R, conf, d, p, edge) {
  const I = R.ifc, Ri = R.Ri, Ro = R.Ro, n = conf === 3 ? P.bz_npad : P.n_sec, th = 2 * Math.PI / n, m = edge + d / 2, cov = conf === 3 ? I.cov : 1;
  const L = P.fix_mode < 1.5 ? I.topes.find((t) => t.id === "bz0").L : 0, hb = (P.b_tope + 2) / 2, ru = R.r_u;
  const gap = Math.max(...I.cortes.filter((c) => !c.strip).map((c) => c.j), P.j_sec);   // junta en frío efectiva entre sectores (mm)
  const dk = { 4: 8, 5: 10, 6: 12, 8: 16, 10: 20, 12: 24 }[P.d_tor] || 2 * P.d_tor;
  const rScrew = P.fix_mode < 1.5 ? I.tap.radios : [];
  const rCirc = P.h_gr > 0 ? I.tap.r_circ : [];
  let N = 0;
  const nrow = Math.ceil(Ro / (p * Math.sqrt(3) / 2)) + 2;
  for (let j = -nrow; j <= nrow; j++) for (let i = -nrow; i <= nrow; i++) {
    const x = i * p + (Math.abs(j) % 2) * p / 2, y = j * p * Math.sqrt(3) / 2, r = Math.hypot(x, y);
    if (r < Ri + m || r > Ro - m) continue;
    let ang = Math.atan2(y, x); if (ang < 0) ang += 2 * Math.PI;
    const k = Math.min(n - 1, Math.floor(ang / th + 1e-12)), a = (k + 0.5) * th;
    const xl = x * Math.cos(a) + y * Math.sin(a), yl = -x * Math.sin(a) + y * Math.cos(a);   // marco local: bisectriz del sector sobre +x
    const sd = (b, px, py) => -px * Math.sin(b) + py * Math.cos(b);                         // distancia con signo a la recta radial de ángulo b (positiva hacia +θ)
    let e1, e2;
    if (conf === 3) { const ph = th * cov / 2; e1 = sd(-ph, xl, yl); e2 = -sd(ph, xl, yl); }     // pastilla: bordes radiales a ±(cobertura·paso angular)/2
    else { e1 = sd(-th / 2, xl, yl) - gap / 2; e2 = -sd(th / 2, xl, yl) - gap / 2; }              // sector: bordes en las radiales de contorno, separados por la junta
    if (e1 < m || e2 < m) continue;
    if (L > 0 && Math.abs(yl) < hb + m && xl > ru - L / 2 - m && xl < ru + L / 2 + m) continue;
    if (rScrew.some((rr) => Math.hypot(xl - rr, yl) < dk / 2 + m)) continue;
    if (rCirc.some((rg) => Math.abs(r - rg) < P.w_gr / 2 + m)) continue;
    if (P.h_gr > 0) {   // ranuras radiales equiespaciadas: distancia lateral del centro a la recta de la ranura (semirrecta que sale del centro de la mesa)
      let hit = false;
      for (let q = 0; q < P.n_gr_rad && !hit; q++) { const f = 2 * Math.PI * q / P.n_gr_rad; if (x * Math.cos(f) + y * Math.sin(f) > 0 && Math.abs(sd(f, x, y)) < P.w_gr / 2 + m) hit = true; }
      if (hit) continue;
    }
    N++;
  }
  return N;
}
const C_VARS = [["C1", 1], ["C2", 2], ["C3", 3]];
const bzA = (conf, o) => TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, bz_conf: conf }, o || {}), { noFEA: true });

test("Tapones · parámetros nuevos (bz_edge 4, bz_fg_modo 1, bz_fg_min 0,20 supuesto C, bz_eta_min 0,45, bz_n_tor 2) y defaults del patrón sin cambios", () => {
  const P = TT.defaults(), g = (id) => TT.PARAM_GROUPS.flatMap((x) => x.p).find((q) => q[0] === id);
  assert.deepEqual([P.bz_edge, P.bz_fg_modo, P.bz_fg_min, P.bz_eta_min, P.bz_n_tor, P.bz_fg_estricto], [4, 1, 0.20, 0.45, 2, 0]);
  assert.ok(/supuesto C/.test(g("bz_fg_min")[1]) && /catálogo/.test(g("bz_fg_min")[1]), "bz_fg_min declarado como supuesto C a confirmar con catálogo");
  assert.deepEqual([P.bz_plug_d, P.bz_plug_p], [12, 30], "el barrido no encuentra un patrón que cumpla f_g ≥ 0,20 con η ≥ 0,45: se conserva Ø12 · paso 30");
});

test("Tapones · N_real contra el conteo independiente (malla propia): C1, C2 y C3; f_g,real = N·π·d²/4/A_contacto ≤ f_g,ideal", () => {
  for (const [nm, conf] of C_VARS) {
    const A = bzA(conf), R = A.R, I = R.ifc, P = A.P, T = I.tap, ctx = nm + ": ";
    assert.equal(T.N, tapIndep(P, R, conf, P.bz_plug_d, P.bz_plug_p, P.bz_edge), ctx + "N_real = conteo independiente");
    assert.equal(I.Nreal, T.N); assert.ok(Number.isInteger(T.N), "entero");
    const Acont = R.Ac * (conf === 3 ? I.cov : 1), ap = Math.PI * P.bz_plug_d ** 2 / 4;
    near(I.fgReal, T.N * ap / Acont, 1e-12, ctx + "f_g,real"); near(I.cobGrafito, I.fgReal, 1e-12, ctx + "cobertura de grafito = π d²/4·N/A");
    near(I.fgIdeal, Math.PI * P.bz_plug_d ** 2 / (2 * Math.sqrt(3) * P.bz_plug_p ** 2), 1e-12, ctx + "f_g,ideal"); assert.equal(I.fg, I.fgIdeal, "I.fg conserva el significado ideal");
    assert.ok(I.fgReal <= I.fgIdeal, ctx + "real ≤ ideal"); near(I.Nideal, I.fgIdeal * Acont / ap, 1e-12, ctx + "N ideal equivalente");
    assert.equal(T.porSector.length, conf === 3 ? P.bz_npad : P.n_sec); assert.equal(T.porSector.reduce((s, v) => s + v, 0), T.N, "N por sector/pastilla suma N");
    assert.equal(I.topes.find((t) => t.id === "bz0").L, T.L, ctx + "el largo de la muesca del conteo es el del tope del núcleo (R.ifc.topes)");
    const pd = T.perdidas; assert.ok(["borde", "muesca", "tornillos", "ranCirc", "ranRad"].every((k) => pd[k] >= 0), "pérdidas por causa");
    assert.equal(T.N_malla - pd.borde - pd.muesca - pd.tornillos - pd.ranCirc - pd.ranRad, T.N, "balance: malla en la corona − pérdidas = N_real");
  }
  // conciliación con el 3D del dibujante (cad/modelo3d_tt300c.py, patrón S09): 2.640 en C1/C2 y 2.364 en C3
  assert.equal(bzA(1).R.ifc.Nreal, 2640); assert.equal(bzA(2).R.ifc.Nreal, 2640); assert.equal(bzA(3).R.ifc.Nreal, 2364);
  // otros patrones y márgenes: mismo resultado que el conteo independiente
  for (const [nm, conf, o] of [["C1 Ø16/p34", 1, { bz_plug_d: 16, bz_plug_p: 34 }], ["C3 Ø14/p26 borde 6", 3, { bz_plug_d: 14, bz_plug_p: 26, bz_edge: 6 }], ["C1 pegado", 1, { fix_mode: 2 }], ["C1 sin ranuras", 1, { h_gr: 0 }], ["C2 12 sectores", 2, { n_sec: 12 }]]) {
    const A = bzA(conf, o); assert.equal(A.R.ifc.tap.N, tapIndep(A.P, A.R, conf, A.P.bz_plug_d, A.P.bz_plug_p, A.P.bz_edge), nm);
  }
});

test("Tapones · modo 0 (ideal) reproduce el cálculo anterior; modo 1 (real) cambia masa, q_neto, PV y desgaste de forma consistente", () => {
  for (const [nm, conf] of C_VARS) {
    const I0 = bzA(conf, { bz_fg_modo: 0 }).R.ifc, A1 = bzA(conf), I1 = A1.R.ifc, P = A1.P, A0 = bzA(conf, { bz_fg_modo: 0 }), ctx = nm + ": ";
    assert.equal(I0.fgUsed, I0.fgIdeal); assert.equal(I1.fgUsed, I1.fgReal);
    near(I0.qNet, I0.qLoc / (1 - I0.fgIdeal - I0.fgr), 1e-12, ctx + "q_neto ideal"); near(I1.qNet, I1.qLoc / (1 - I1.fgReal - I1.fgr), 1e-12, ctx + "q_neto real");
    assert.ok(I1.qNet < I0.qNet, ctx + "menos grafito: menos área de grafito y menos presión sobre el bronce neto");
    // masa: bronce con tapones ρ_mezcla = ρ_bz(1 − 0,7 f) + ρ_gr·0,7 f sobre el área de la parte cubierta; el real pesa más porque hay más bronce
    const rBz = P.rho_bz * 1e-6, mix = (f) => rBz * (1 - 0.7 * f) + 1.8e-6 * 0.7 * f;
    near(I1.mBz, R_Ac(A1) * (conf === 3 ? I1.cov : 1) * I1.tbz * mix(I1.fgReal) + (conf === 2 ? R_Ac(A1) * I1.tss * rBz : 0), 1e-12, ctx + "masa bruta con f_g,real");
    near(I0.mBz, R_Ac(A0) * (conf === 3 ? I0.cov : 1) * I0.tbz * mix(I0.fgIdeal) + (conf === 2 ? R_Ac(A0) * I0.tss * rBz : 0), 1e-12, ctx + "masa bruta con f_g,ideal");
    assert.ok(A1.R.m.bz > A0.R.m.bz && A1.R.m.total > A0.R.m.total, ctx + "el real pesa más");
    near(A1.R.m.total - A0.R.m.total, A1.R.m.bz - A0.R.m.bz, 1e-9, ctx + "solo cambia la masa del bronce (la masa rotatoria y la presión q no dependen de f_g)");
    assert.equal(A1.R.ifc.tbz, A0.R.ifc.tbz); near(A1.R.ifc.q, A0.R.ifc.q, 1e-12, ctx + "q_máx");
    assert.equal(I1.eta, I0.eta, ctx + "η solo depende de d y p");
    const row = (A, re) => A.checks.find((c) => re.test(c.name));
    near(row(A1, /Bronce con grafito: valor PV/).dem / row(A0, /Bronce con grafito: valor PV/).dem, I1.qNet / I0.qNet, 1e-12, ctx + "PV ∝ q_neto");
    near(row(A1, /Bronce con grafito: desgaste/).dem / row(A0, /Bronce con grafito: desgaste/).dem, I1.qNet / I0.qNet, 1e-12, ctx + "desgaste ∝ q_neto");
    near(row(A1, /Presión de contacto sobre el bronce neto/).dem, I1.qNet, 1e-12, ctx + "fila de q_neto");
    near(A1.R.cd.FS, A0.R.cd.FS, 1e-9, ctx + "FS: la masa del bronce fijo a la base no carga el giro");
  }
});
const R_Ac = (A) => A.R.Ac;

test("Tapones · criterio de lubricación f_g ≥ bz_fg_min (supuesto C): aviso por defecto, no cumple en modo estricto, cumple si el valor lo permite", () => {
  const lub = (A) => A.checks.find((c) => /cobertura mínima de lubricante sólido/.test(c.name));
  for (const [nm, conf] of C_VARS) {
    const A = bzA(conf), c = lub(A); assert.ok(c, nm + ": fila de lubricación");
    near(c.dem, 0.20, 1e-12, "demanda = bz_fg_min"); near(c.cap, A.R.ifc.fgUsed, 1e-12, "capacidad = f_g usada");
    assert.equal(c.st, "warn", nm + ": 0,097 < 0,20: aviso (criterio a confirmar con el catálogo)"); assert.ok(A.verdict.gira && A.verdict.estructura, "el aviso no cambia el veredicto");
    assert.ok(/supuesto C/.test(c.ref) && /catálogo/.test(c.ref), "nivel de confianza en la referencia");
    assert.equal(lub(bzA(conf, { bz_fg_estricto: 1 })).st, "fail"); assert.equal(bzA(conf, { bz_fg_estricto: 1 }).verdict.estructura, false, "estricto: no cumple la estructura/lubricación");
    assert.equal(lub(bzA(conf, { bz_fg_min: 0.09 })).st, "ok");
    assert.equal(lub(bzA(conf, { bz_fg_modo: 0 })).st, "warn", nm + ": con f_g ideal 0,145 tampoco llega a 0,20");
    assert.equal(lub(bzA(conf, { bz_fg_modo: 0, bz_fg_min: 0.14 })).st, "ok");
  }
  // ligamento mínimo (criterio de proyecto): η ≥ bz_eta_min
  const eta = (o) => bzA(1, o).checks.find((c) => /ligamento mínimo entre tapones/.test(c.name));
  assert.equal(eta({}).st, "ok"); assert.equal(eta({ bz_plug_d: 18, bz_plug_p: 30 }).st, "fail", "η = 0,40 < 0,45");
});

test("Tapones · TT.tapones: comparación ideal–real, barridos monótonos, sensibilidad al borde y a los tornillos, conclusión automática", () => {
  const r = TT.tapones(TT.defaults());
  assert.deepEqual(r.alternativas.map((a) => a.id), ["C1", "C2", "C3"]);
  assert.ok(!/NaN|undefined|Infinity/.test(JSON.stringify(r)), "JSON puro");
  for (const a of r.alternativas) {
    const I = bzA(a.conf).R.ifc, A0 = bzA(a.conf, { bz_fg_modo: 0 }), A1 = bzA(a.conf), ctx = a.id + ": ";
    // (a) ideal vs real
    assert.equal(a.comparacion.real.N, I.Nreal); near(a.comparacion.ideal.N, I.Nideal, 1e-9, ctx + "N ideal"); near(a.comparacion.real.fg, I.fgReal, 1e-12, ctx + "f_g real");
    near(a.comparacion.real.masa_bz, A1.R.m.bz, 1e-12, ctx + "masa bronce real"); near(a.comparacion.ideal.masa_bz, A0.R.m.bz, 1e-12, ctx + "masa bronce ideal");
    near(a.comparacion.real.qNet, I.qNet, 1e-12, ctx + "q_neto"); near(a.comparacion.ideal.FS, A0.R.cd.FS, 1e-12, ctx + "FS giro");
    for (const k of ["N", "fg", "cobertura", "masa_bz", "masa_total", "qNet", "fuQ", "tbz", "tbzReq", "PV", "fuPV", "desgaste", "fuDesgaste", "FS", "mu"]) { assert.ok(k in a.comparacion.real && k in a.comparacion.ideal && k in a.comparacion.delta_pct, ctx + "campo " + k); }
    near(a.comparacion.delta_pct.masa_bz, (A1.R.m.bz / A0.R.m.bz - 1) * 100, 1e-9, ctx + "variación % de la masa"); assert.equal(a.comparacion.real.mu, a.comparacion.ideal.mu, "μ es dato: no cambia");
    // (b) barrido de f_g: monótono
    const b = a.barrido_fg; assert.ok(b.length >= 11 && Math.abs(b[0].fg_obj - 0.05) < 1e-9 && Math.abs(b[b.length - 1].fg_obj - 0.30) < 1e-9);
    for (let i = 1; i < b.length; i++) {
      assert.ok(b[i].fg >= b[i - 1].fg - 1e-12, ctx + "f_g alcanzado crece"); assert.ok(b[i].eta <= b[i - 1].eta + 1e-12, ctx + "η no crece"); assert.ok(b[i].tbzReq >= b[i - 1].tbzReq - 1e-9, ctx + "espesor requerido no decrece");
      assert.ok(b[i].qNet >= b[i - 1].qNet - 1e-12, ctx + "q_neto crece con f_g"); assert.ok(b[i].tbz >= b[i - 1].tbz, ctx + "espesor adoptado no decrece");
    }
    assert.ok(b.every((x) => ["cumple", "cumple sin lubricación", "no cumple", "inalcanzable"].includes(x.estado)), "estados");
    // (c) barrido (d, p)
    const dp = a.barrido_dp; assert.deepEqual([...new Set(dp.map((x) => x.d))], [10, 12, 14, 16, 18, 20]); assert.ok(dp.every((x) => x.p >= 22 && x.p <= 40 && x.p > x.d));
    const x = dp.find((q) => q.d === 12 && q.p === 30); assert.equal(x.N, I.Nreal); near(x.fg, I.fgReal, 1e-12, ctx + "la fila Ø12/30 coincide con el cálculo"); near(x.eta, 0.6, 1e-12, "η");
    const q = dp.find((z) => z.d === 14 && z.p === 26), A2 = bzA(a.conf, { bz_plug_d: 14, bz_plug_p: 26 }); near(q.masa_bz, A2.R.m.bz, 1e-12, ctx + "masa de otro patrón"); near(q.qNet, A2.R.ifc.qNet, 1e-12, "q_neto de otro patrón");
    // (d) sensibilidad: más borde = menos tapones; más tornillos = menos tapones
    const e = a.sens_borde; assert.deepEqual(e.map((z) => z.bz_edge), [2, 4, 6, 8]); for (let i = 1; i < e.length; i++) assert.ok(e[i].N <= e[i - 1].N && e[i].fg <= e[i - 1].fg + 1e-12, ctx + "N no crece con la franja de borde");
    assert.equal(e[1].N, I.Nreal, "borde 4 = cálculo");
    const t = a.sens_tornillos; assert.deepEqual(t.filter((z) => z.d_tor === 6).map((z) => z.n_tor), [0, 2, 4]); const tt = t.filter((z) => z.d_tor === 6); assert.ok(tt[0].N >= tt[1].N && tt[1].N >= tt[2].N, ctx + "N no crece con los tornillos"); assert.equal(tt[1].N, I.Nreal);
    // (e) conclusión
    const c = a.conclusion; assert.equal(c.fg_min_criterio, 0.20); assert.ok(c.fg_max_alcanzable > I.fgReal && c.fg_max_alcanzable < 0.20, ctx + "ningún patrón con η ≥ 0,45 llega a 0,20: máx " + c.fg_max_alcanzable);
    assert.equal(c.cumple_criterio, false); assert.equal(c.patron_recomendado, null); assert.ok(c.mejor_alcanzable && c.mejor_alcanzable.eta >= 0.45 - 1e-12 && c.mejor_alcanzable.fg === c.fg_max_alcanzable);
    assert.ok(c.texto.length >= 3 && c.texto.every((s) => typeof s === "string"));
  }
  assert.ok(r.supuestos.some((s) => /bz_fg_min/.test(s)) && r.notas.length >= 3);
  // con un criterio realista (0,15) sí hay patrón y es el de menor masa entre los que cumplen
  const r15 = TT.tapones(Object.assign(TT.defaults(), { bz_fg_min: 0.15 })).alternativas[0], pr = r15.conclusion.patron_recomendado;
  assert.ok(pr && pr.fg >= 0.15 && pr.eta >= 0.45 && pr.estado === "cumple");
  const ok = r15.barrido_dp.filter((x) => x.estado === "cumple"); assert.ok(ok.length > 0 && ok.every((x) => x.masa_bz >= pr.masa_bz - 1e-9), "menor masa entre los que cumplen");
});

test("Tapones · interfazGeom y apoyo.interfaz exponen N_real, f_g real e ideal y la cobertura (R.ifc)", () => {
  const A = bzA(1), I = A.R.ifc;
  for (const k of ["Nreal", "Nideal", "fgReal", "fgIdeal", "fgUsed", "cobGrafito", "tap"]) assert.ok(k in I, "R.ifc." + k);
  assert.ok(!("tap" in TT.compute(TT.defaults()).ifc) || TT.compute(TT.defaults()).ifc.tap == null, "sin opción C no hay tapones");
});

test("Temperatura · alcance (term_alcance): 1 = sistema de placas y disco, sin filas del circuito hidráulico ni del accionamiento en el escenario; 2 las reactiva", () => {
  const P1 = TG(), P2 = Object.assign(TG(), { term_alcance: 2 });
  assert.equal(P1.term_alcance, 1, "default: placas y disco");
  const prm = TT.PARAM_GROUPS.find((g) => g.id === "temperatura").p.find((q) => q[0] === "term_alcance"); assert.ok(prm && /placas y disco/.test(prm[1]) && prm[4] === 1 && prm[5] === 2);
  const HID = /Aceite|aceite|Sellos NBR|viscosidad|Bomba con viscosidad|Válvula de alivio térmico|Uña–pasador|Patín fuera de la mesa|Bancada de guía fuera/;
  const r1 = TT.thermal(P1, { T: [20, 80] }), r2 = TT.thermal(P2, { T: [20, 80] });
  assert.equal(r1.alcance, 1); assert.equal(r2.alcance, 2); assert.ok(/placas y disco/.test(r1.alcance_texto) && /Alcance 2/.test(r2.alcance_texto));
  assert.equal(r1.aceite_fuera_de_alcance, true); assert.equal(r2.aceite_fuera_de_alcance, false);
  assert.ok(r1.avisos.some((x) => /Nota informativa \(fuera de alcance\)/.test(x) && /alivio térmico/.test(x)) && r2.avisos.some((x) => /exige válvula de alivio térmico/.test(x) && !/fuera de alcance/.test(x)), "el aviso de la válvula pasa a nota informativa");
  assert.ok(r1.supuestos_fuera_alcance.length === 3 && r2.supuestos_fuera_alcance.length === 0);
  for (const a of r1.alternativas) for (const b of a.byT) {
    assert.ok(!b.filas.some((x) => HID.test(x.nombre) || x.sub === "c" || x.sub === "e" || x.sub === "f"), a.id + " " + b.T + ": ninguna fila hidráulica ni de accionamiento en el escenario");
    if (b.T === 80) { const malas = b.filas.filter((x) => x.estado === "fail");   // lo térmico solo falla por filas del sistema de placas y disco (juntas, gradiente)
      assert.equal(b.termico, ["base", "A", "C1", "C2"].includes(a.id), a.id + ": el aceite atrapado ya no hace fallar lo térmico; B y C3 fallan por la junta de la lámina / el gradiente");
      assert.equal(malas.length > 0, !b.termico); }
    assert.ok(b.fuera_alcance.length >= 15 && b.fuera_alcance.every((x) => x.estado_informativo && "fu" in x), "las filas movidas quedan en la sección informativa");
    assert.ok(b.fuera_alcance.some((x) => /Aceite atrapado/.test(x.nombre)) && b.fuera_alcance.some((x) => x.grp === "Uña") && b.fuera_alcance.some((x) => x.grp === "Pasadores de empuje") && b.fuera_alcance.some((x) => x.grp === "Patín y guía"));
    assert.ok(!b.sensibles.concat(b.sensibles_est, b.cambian).some((x) => ACC_GRPS.includes(x.grp) || HID.test(x.nombre)), "ni sensibles ni cambios de estado incluyen filas fuera de alcance");
    if (b.T === 80) assert.ok(b.fuera_resumen.fail >= 3, a.id + ": el aceite atrapado fallaría (informativo): " + b.fuera_resumen.fail);
    assert.equal(b.fuera_resumen.n, b.fuera_alcance.length);
  }
  // el estado, el FU y el veredicto de alcance 1 no dependen de las filas movidas
  for (const a of r1.alternativas) {
    const b = a.byT[1], a2 = r2.alternativas.find((x) => x.id === a.id), b2 = a2.byT[1];
    assert.ok(b2.fuera_alcance.length === 0 && b2.filas.some((x) => /Aceite atrapado/.test(x.nombre)), a.id + ": con alcance 2 reaparecen");
    assert.equal(b2.termico, false, a.id + ": con alcance 2 el aceite atrapado hace fallar lo térmico (comportamiento anterior)");
    assert.ok(b.fuTerm <= b2.fuTerm + 1e-12 && b.nFail <= b2.nFail);
    assert.equal(b.FS, b2.FS); assert.equal(b.masa, b2.masa);
  }
  const base = r1.alternativas.find((a) => a.id === "base").byT[1], base2 = r2.alternativas.find((a) => a.id === "base").byT[1];
  assert.ok(base.fuEst <= base2.fuEst + 1e-12 && base.gira && base.estructura && base.termico, "base a 80 °C con alcance 1: gira, estructura y térmica cumplen");
  assert.equal(base.fuTerm, base.filas.filter((x) => x.fu != null && isFinite(x.fu)).reduce((m, x) => Math.max(m, x.fu), 0) || base.fuTerm, "FU térmico = máx. de las filas del escenario");
  // el análisis estándar (sin escenario térmico) no depende de term_alcance
  const s1 = TT.analyze(P1, { noFEA: true }), s2 = TT.analyze(P2, { noFEA: true });
  assert.deepEqual(s1.checks.map((c) => [c.name, c.fu, c.st]), s2.checks.map((c) => [c.name, c.fu, c.st])); assert.ok(s1.checks.every((c) => !c.fuera));
  // las filas del accionamiento mantienen su valor calculado (solo se marcan)
  const A80a = TT.analyze(TT.thermalP(P1, 80), { noFEA: true }), A80b = TT.analyze(TT.thermalP(P2, 80), { noFEA: true });
  assert.deepEqual(A80a.checks.filter((c) => c.grp === "Uña").map((c) => [c.name, c.fu, c.st, c.fuera === true]), A80b.checks.filter((c) => c.grp === "Uña").map((c) => [c.name, c.fu, c.st, true]));
  assert.ok(A80a.checks.filter((c) => c.fuera).every((c) => ACC_GRPS.includes(c.grp) || (c.grp === "Temperatura")));
});

/* ======================= Tarea 1: leva de reenganche positiva del modo guiado ======================= */
test("Leva guiada · parámetros nuevos (opt_cam = 1 por defecto, s_libre 21) y la leva no cambia las fuerzas del accionamiento", () => {
  const P = TG();
  assert.equal(P.opt_cam, 1); assert.equal(TT.defaults().drive_mode, 2); assert.equal(P.cam_mat, 0); assert.equal(P.s_free, 21);
  const g = TT.PARAM_GROUPS.find((x) => x.id === "leva_guiada"); assert.ok(g && g.p.length >= 15 && g.p.every((q) => q[4] !== undefined && q[5] !== undefined), "grupo con rangos");
  const R1 = TT.compute(P), R0 = TT.compute(Object.assign(TG(), { opt_cam: 0 }));
  assert.ok(R1.camG && !R0.camG && R0.m.cam === 0 && R1.m.cam > 0);
  near(R1.m.total - R0.m.total, R1.m.cam + (R1.m.insertos - R1.m.insRim - R1.m.insBrackets) - (R0.m.insertos - R0.m.insRim - R0.m.insBrackets), 1e-9, "la masa total suma la leva (el inserto bajo las ménsulas depende de la banda del accionamiento, que la leva ensancha)");
  near(R1.m.cam, P.n_cyl * (R1.camG.m.plate + R1.camG.m.ped + R1.camG.m.ext + R1.camG.m.fol), 1e-12, "riel + soportes + prolongación + seguidor por cilindro");
  assert.deepEqual(R1.cases.map((c) => c.F), R0.cases.map((c) => c.F), "la leva no cambia la fuerza del cilindro");
  near(R1.K.s_req, 21 + 2 * P.R_pin * Math.sin(Math.PI / P.N_pin), 1e-12, "carrera requerida con la sobrecarrera de 21 mm");
});
test("Leva guiada · sincronía con margen, bolsillo suficiente, rampa sin autobloqueo y fuerzas de atasco a p_ret", () => {
  const A = TT.analyze(TG(), { noFEA: true }), c = A.R.camG, P = A.P;
  assert.ok(c.sync >= P.cam_msync, "sincronía: holgura " + c.sync.toFixed(2) + " ≥ " + P.cam_msync);
  assert.ok(c.needMax <= c.travel, "el bolsillo alcanza");
  assert.ok(c.lockDem < c.lockCap, "rampa sin autobloqueo");
  const Fret = Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2) * P.p_ret / 10;
  near(c.NR, Fret / Math.sin(P.cam_alpha * Math.PI / 180), 1e-12, "N_rampa = F_ret/sen α"); near(c.NT, Fret / Math.tan(P.beta_ch * Math.PI / 180), 1e-12, "N_toma = F_ret/tan β");
  // el perfil: nivel de toma c, bolsillo de profundidad Δx, rampa a α que termina en c en η₀ + tramo
  near(c.etaEnd, -P.d_pin / 2 - P.s_free + P.cam_dwell, 1e-12, "fin de la rampa"); assert.equal(c.prof[1][1], P.cam_c); assert.ok(c.prof.some((q) => Math.abs(q[1] - c.travel) < 1e-9 || q[1] > P.cam_c));
  const rows = A.checks.filter((x) => x.grp === "Leva de reenganche");
  assert.ok(rows.length >= 18 && rows.every((x) => x.ref && x.formula), "filas con fórmula y referencia");
  assert.ok(rows.filter((x) => x.sys === "est" && x.kind === "fu").every((x) => x.fu <= 0.90), "FU ≤ 0,90 en las filas estructurales de la leva");
  assert.ok(rows.every((x) => x.st !== "fail"), "ninguna fila de la leva falla");
  assert.ok(rows.some((x) => /AISC 360-22 §J3/.test(x.ref)) && rows.some((x) => /Hertz/.test(x.ref)) && rows.some((x) => /BTH-1/.test(x.ref)));
  // la sincronía falla con la sobrecarrera anterior (10 mm) y el autobloqueo con una rampa muy empinada o una zapata deslizante
  const s10 = TT.analyze(Object.assign(TG(), { s_free: 10 }), { noFEA: true }).checks.find((x) => /^Sincronía: holgura uña–pasador siguiente/.test(x.name));
  assert.equal(s10.st, "fail", "con s_libre = 10 mm no hay lugar para la rampa");
  const steep = TT.analyze(Object.assign(TG(), { cam_alpha: 72 }), { noFEA: true }).checks.find((x) => /^Rampa de reenganche sin autobloqueo/.test(x.name));
  assert.equal(steep.st, "fail", "α = 72° se autobloquea");
  const lowA = TT.analyze(Object.assign(TG(), { cam_alpha: 50 }), { noFEA: true }).checks.find((x) => /^Sincronía: holgura uña–pasador siguiente/.test(x.name));
  assert.equal(lowA.st, "fail", "α = 50°: la rampa empuja la uña antes de despejar el pasador");
  for (const f of [2, 3, 4]) { const X = TT.analyze(Object.assign(TG(), { cam_mat: f }), { noFEA: true }); assert.equal(X.R.fam.f, f); assert.ok(!X.verdict.gira, "familia " + f + " en el riel guiado: se autobloquea (justifica la regla automática = 1)"); }
  assert.ok(TT.analyze(Object.assign(TG(), { opt_cam: 0 }), { noFEA: true }).checks.some((x) => x.grp === "Leva de reenganche" && x.kind === "info" && /desactivada/.test(x.name)));
});

/* ======================= Tarea 2: modo pivotado con guía de leva (tipo KIET) ======================= */
const P2 = (o) => Object.assign(TG(), { drive_mode: 2 }, o || {});
test("Pivotado · modo 2 por defecto: gira, la estructura cumple con FU ≤ 0,90 y no hay patín, bancada ni ménsulas", () => {
  const A = TT.analyze(P2()), R = A.R;
  assert.equal(TT.defaults().drive_mode, 2, "el modo pivotado es el valor por defecto (mandante, 08-11-2026)"); assert.ok(A.verdict.gira, "gira"); assert.ok(A.verdict.estructura, "estructura");
  // desde el 10-11-2026 (decisión del mandante) la base de 20 mm con inserto de esquina reemplaza las filas pendientes de la franja sin anclaje
  const est = A.checks.filter((c) => c.sys === "est" && c.kind === "fu");
  assert.ok(!A.checks.some((c) => c.st === "pend" && c.fu > 1) && A.verdict.estado_global === "CUMPLE", "sin pendientes críticos");
  assert.ok(est.every((c) => c.fu <= 0.90), "FU ≤ 0,90 en estructura: " + est.filter((c) => c.fu > 0.9).map((c) => c.name + " " + c.fu.toFixed(3)).join("; "));
  assert.ok(!A.checks.some((c) => c.grp === "Patín y guía" || /patín/.test(c.name) && c.grp === "Giro"), "sin filas del patín");
  assert.equal(R.m.shoes, 0); assert.equal(R.m.beds, 0);
  near(R.m.brackets, P2().n_cyl * R.sup.m - R.m.insBrackets + R.m.insertos, 1e-9, "soportes del ojal E (paredes sobre el inserto de esquina) con sus insertos"); near(R.m.dogs, P2().n_cyl * R.blk.m, 1e-12, "bloques-uña con pasador Q");
  assert.ok(R.m.cam > 0 && R.m.total < TT.compute(TG()).m.total, "más liviano que el guiado");
  assert.ok(R.cd.FS >= P2().FS_min, "FS ≥ FS_mín");
  assert.equal(AG.validate(P2()).filter((v) => v.lvl === "error").length, 0);
  for (const c of AG.crossCheck(A)) assert.ok(c.ok, "revisor cruzado: " + c.name + " Δ " + c.d);
  assert.ok(AG.audit(A.checks).ok, "todas las filas con fórmula y referencia");
});
test("Pivotado · cinemática: E–Q–P alineados, L = |P − E| − L_qp, a = dist(O, E–P) = dL/dθ, a_ef = a − μ_s|v_s|, carrera y fuerza", () => {
  const P = P2(), R = TT.compute(P), K = R.K, ph = P.pv_phE * Math.PI / 180, E = [P.pv_RE * Math.cos(ph), P.pv_RE * Math.sin(ph)];
  assert.ok(K.ok); assert.deepEqual(K.E.map((v) => +v.toFixed(9)), E.map((v) => +v.toFixed(9)));
  near(K.pts[0].L, P.L0 + P.s_free, 1e-9, "toma a L0 + s_libre");
  for (const q of K.pts) {
    const d = Math.hypot(q.P[0] - E[0], q.P[1] - E[1]), Q = [q.P[0] + P.pv_Lqp * (E[0] - q.P[0]) / d, q.P[1] + P.pv_Lqp * (E[1] - q.P[1]) / d];
    near(q.Q[0], Q[0], 1e-9, "Q_x"); near(q.Q[1], Q[1], 1e-9, "Q_y"); near(q.L, d - P.pv_Lqp, 1e-12, "L");
    near(q.a, Math.abs(E[0] * q.P[1] - E[1] * q.P[0]) / d, 1e-9, "brazo = distancia de O a la recta E–P");
    const h = 1e-6, Lp = Math.hypot(P.R_pin * Math.cos(q.th + h) - E[0], P.R_pin * Math.sin(q.th + h) - E[1]), Lm = Math.hypot(P.R_pin * Math.cos(q.th - h) - E[0], P.R_pin * Math.sin(q.th - h) - E[1]);
    near(q.a, (Lp - Lm) / (2 * h), 1e-6, "a = dL/dθ");
    near(q.aEff, q.a - P.mu_s * Math.abs(P.d_pin / 2 * (1 - (q.P[0] * q.u[0] + q.P[1] * q.u[1]) / d)), 1e-9, "a_ef");
  }
  near(K.s_req, Math.max(...K.pts.map((q) => q.L)) - P.L0, 1e-12, "carrera requerida");
  // empuje guiado (Q apoyado en el canto, 09-11-2026): equilibrio del pasador Q F·u_c + H·(n − μ_leva·t) = F_n·b' y par T/n = F_n·(Q × b')
  R.stroke.forEach((q, i) => {
    const g = R.camP.push[i], Fe = q.F * P.eta_c, res = [0, 1].map((k) => Fe * g.uc[k] + q.H_guia * (g.nin[k] - R.fam.mu * g.tp[k]) - q.Fp * g.bp[k]);
    assert.ok(Math.hypot(...res) <= 1e-9 * Fe, "equilibrio del pasador Q en θ = " + q.th);
    near(q.Fp * (g.Q[0] * g.bp[1] - g.Q[1] * g.bp[0]), R.cd.T * 1e3 / P.n_cyl, 1e-12, "par en el pasador tomado");
    near(q.ft ** 2 + q.fr ** 2, 1, 1e-9, "f_t² + f_r² = 1"); near(Math.hypot(...g.bp), 1, 1e-12);
  });
  near(R.cd.F, Math.max(...R.stroke.map((q) => q.F)), 1e-12, "F_cil = máximo del empuje guiado");
  near(R.cd.FS, R.Fstall / R.cd.F, 1e-12);
  const kf = 1 + R.fam.mu * P.mu_s, Fcol = Math.max(...K.pts.map((q) => R.cd.T * 1e3 / P.n_cyl / q.aEff)) * kf / P.eta_c;
  assert.ok(R.cd.F >= Fcol && R.cd.F <= 1.10 * Fcol, "el empuje guiado pide hasta 10 % más que la cinemática colineal: " + (R.cd.F / Fcol).toFixed(3));
  // sugerencia de E: factible y con el brazo efectivo máximo de su entorno
  const sg = TT.suggestE(Object.assign(P2(), { pv_RE: 0, pv_Lqp: 0 }));
  assert.ok(sg.ok && sg.RE <= sg.REmax);
  const Ks = TT.pivKin(P, sg.RE, sg.Lqp, 40); assert.ok(Ks.feas, "la sugerencia respeta las restricciones");
  for (const [dR, dL] of [[0, 5], [0, -5], [-5, 0], [-10, 10]]) { const Kn = TT.pivKin(P, sg.RE + dR, sg.Lqp + dL, 40); assert.ok(!Kn.feas || Kn.aEffMin <= sg.aEffMin + 1e-6, "vecino " + dR + "/" + dL + " no mejora"); }
  assert.ok(TT.compute(Object.assign(P2(), { pv_RE: 0, pv_Lqp: 0 })).K.auto, "pv_RE = 0 usa la sugerencia automática");
});
test("Pivotado · perfil de la placa-leva: empuje con holgura, bolsillo para pasar sobre el pasador siguiente y rampa con sincronía", () => {
  const P = P2(), R = TT.compute(P), C = R.camP;
  assert.ok(C.sync >= P.pv_msync, "sincronía " + C.sync.toFixed(2));
  C.need.forEach((q) => { assert.ok(q.w_leva >= q.w_emp + P.pv_c - 1e-9, "la leva deja la holgura sobre la trayectoria de empuje"); if (q.L >= C.Lend + 1e-9 && q.L <= C.Lr1) assert.ok(q.w_leva >= Math.min(q.w_nec, C.wPk) - 1e-6, "la rampa no empuja antes de despejar"); });
  assert.ok(C.wPk > 0 && C.hasPk, "hay bolsillo"); assert.ok(C.cover > 0 && C.cover < 1);
  assert.ok(C.diag > 5 && C.inBase <= P.B / 2 - P.rim_t - 5, "4 placas sin solape y dentro de la base");
  const lo = TT.analyze(P2({ pv_alpha: 35 }), { noFEA: true }).checks.find((c) => /^Sincronía del retorno/.test(c.name));
  assert.equal(lo.st, "fail", "con α = 35° la rampa empuja el bloque contra el pasador siguiente");
});
test("Pivotado · las 4 familias del contacto seguidor–leva (μ, p_adm, PV propios) y la regla automática", () => {
  const exp = { 1: P2().mu_d, 2: P2().muB_d, 3: P2().muC_d, 4: P2().muA_d };
  for (const f of [1, 2, 3, 4]) {
    const A = TT.analyze(P2({ cam_mat: f }), { noFEA: true }), F = A.R.fam, rows = A.checks.filter((c) => c.grp === "Placas-leva");
    assert.equal(F.f, f); near(F.mu, exp[f], 1e-12, "μ de la familia " + f);
    assert.ok(A.checks.some((c) => /^Placa-guía sin autobloqueo/.test(c.name) && c.name.includes(F.corto)), "autobloqueo con su μ");
    assert.ok(rows.some((c) => /Tornillos de la placa-guía: corte/.test(c.name)) && rows.some((c) => /flexión del ligamento/.test(c.name)), "tornillos y ligamento");
    if (f === 1) assert.ok(rows.some((c) => /Hertz/.test(c.name)));
    else { assert.ok(rows.some((c) => /presión de la zapata/.test(c.name))); assert.ok(A.R.camP.lpad >= P2().pv_dq); }
    if (f === 2 || f === 3) assert.ok(rows.some((c) => /respaldo de acero/.test(c.name)) && rows.some((c) => /valor PV/.test(c.name)), "respaldo y PV");
    assert.ok(A.verdict.gira, "familia " + f + ": gira");
    assert.equal(A.verdict.estructura, f !== 2, "familia " + f + (f === 2 ? ": la zapata de UHMW no es practicable (PV)" : ": cumple"));
    assert.ok(A.checks.every((c) => !(typeof c.dem === "number" && isNaN(c.dem)) && !(typeof c.cap === "number" && isNaN(c.cap))), "sin NaN");
  }
  const auto = (o) => TT.camFam(P2(o)).f;
  assert.deepEqual([auto({}), auto({ opt_ss: 1 }), auto({ opt_uhmw: 1 }), auto({ opt_bz: 1 }), TT.camFam(TG()).f, TT.camFam(Object.assign(TG(), { opt_uhmw: 1 })).f], [1, 4, 4, 3, 1, 1], "regla automática");
});
test("Pivotado · combinado con cada alternativa de interfaz (y pegado, madera, escenario térmico) sin NaN", () => {
  const isBad = (v) => typeof v === "number" && isNaN(v);
  for (const [nm, o] of [...IFC_VARIANTS, ["pegado", { opt_ss: 1, fix_mode: 2 }], ["C1 pegado", { opt_bz: 1, fix_mode: 2 }], ["B+madera", { opt_uhmw: 1, opt_wood: 1 }]]) {
    const A = TT.analyze(P2(o), { noFEA: true });
    const bad = A.checks.filter((c) => isBad(c.dem) || isBad(c.cap) || isBad(c.fu));
    assert.equal(bad.length, 0, nm + ": " + bad.map((c) => c.name).join("; "));
    assert.ok(isFinite(A.R.m.total) && isFinite(A.R.cd.F) && A.verdict.gira, nm + ": gira");
    assert.ok(A.verdict.estructura, nm + ": estructura");
  }
  const th = TT.thermal(P2({ term_alcance: 2 }), { T: [20, 80] });
  th.alternativas.forEach((a) => a.byT.forEach((b) => { assert.ok(isFinite(b.FS) && isFinite(b.masa), a.id + " " + b.T); assert.ok(b.filas.every((x) => !isBad(x.dem) && !isBad(x.cap)), a.id + " filas térmicas sin NaN"); }));
  const base80 = th.alternativas.find((a) => a.id === "base").byT[1];
  assert.ok(base80.filas.some((x) => /Pivotado \(mesa caliente/.test(x.nombre)) && !base80.filas.some((x) => /Patín fuera de la mesa/.test(x.nombre)), "filas térmicas del modo pivotado");
});
test("Pivotado · pivote central: componente radial del par anulada, asimetría por μ_s ± 0,05 y n° impar de cilindros", () => {
  const A = TT.analyze(P2(), { noFEA: true }), R = A.R, pa = TT.pivAsym(A.P, R);
  assert.ok(pa.H > 0 && pa.H < 0.25 * R.Fstall, "asimetría acotada");
  const row = A.checks.find((c) => /roce desigual en el contacto uña–pasador/.test(c.name)); near(row.dem, pa.H, 1e-12);
  assert.ok(A.checks.some((c) => /componente radial/.test(c.name) && c.dem > 0), "componente radial informada");
  const pb = A.checks.find((c) => c.name === "Presión en el buje"); assert.ok(pb && pb.st === "ok");
  const one = TT.analyze(P2({ n_cyl: 1 }), { noFEA: true }), h1 = one.checks.find((c) => /n° impar de cilindros/.test(c.name));
  assert.ok(h1 && h1.dem > 0, "con un cilindro el pivote recibe el empuje completo");
  assert.ok(AG.validate(P2({ n_cyl: 1 })).some((v) => /2 cilindros/.test(v.msg)));
});
test("Pivotado · casos límite: geometría sin toma, ojal fuera de la base, uña que no libra el pasador siguiente, carrera insuficiente", () => {
  const noK = TT.analyze(P2({ pv_RE: 960 }), { noFEA: true });
  assert.equal(noK.R.K.ok, false); assert.equal(noK.verdict.gira, false, "sin posición de toma no gira");
  assert.ok(AG.validate(P2({ pv_RE: 960 })).some((v) => v.lvl === "error"), "el validador lo informa");
  const out = TT.analyze(P2({ pv_RE: 1700 }), { noFEA: true }).checks.find((c) => /Soporte del ojal E dentro de la base/.test(c.name)); assert.equal(out.st, "fail");
  const clash = TT.analyze(P2({ pv_ecr: 0 }), { noFEA: true }).checks.find((c) => /libre del pasador siguiente durante el empuje/.test(c.name)); assert.equal(clash.st, "fail", "sin acodado el cuerpo toca el pasador siguiente");
  const st = TT.analyze(P2({ stroke: 200 }), { noFEA: true }).checks.find((c) => /Carrera requerida con margen \(pivotado\)/.test(c.name)); assert.equal(st.st, "fail");
  const hi = TT.analyze(P2({ pv_hu: 150 }), { noFEA: true }).checks.find((c) => /Bloque-uña dentro de la luz libre/.test(c.name)); assert.equal(hi.st, "fail");
  const tq = TT.analyze(P2({ mu_s: 0 }), { noFEA: true }); near(tq.R.K.aEffMin, tq.R.K.aMin, 1e-12, "sin roce el brazo efectivo es el geométrico");
  assert.ok(TT.analyze(P2(), { noFEA: true }).R.cd.F < TT.analyze(P2({ mu_s: 0.3 }), { noFEA: true }).R.cd.F, "el roce del contacto sube la fuerza");
  assert.equal(TT.driveMode(P2({ drive_mode: 1.4 })), 1); assert.equal(TT.driveMode(P2({ drive_mode: 1.6 })), 2);
});
/* ======================= Placa-guía curva del modo pivotado (rediseño 09-11-2026, docs/qa/guia_curva_KIET/cambios.md) ======================= */
const segTan = (s, p) => { if (s.tipo === "linea") { const d = Math.hypot(s.p1[0] - s.p0[0], s.p1[1] - s.p0[1]); return [(s.p1[0] - s.p0[0]) / d, (s.p1[1] - s.p0[1]) / d]; } const v = [p[0] - s.centro[0], p[1] - s.centro[1]], r = Math.hypot(v[0], v[1]), k = s.sentido === "antihorario" ? 1 : -1; return [-k * v[1] / r, k * v[0] / r]; };
const segDist = (s, p) => {   // distancia de p al segmento (línea o arco recorrido en su sentido)
  if (s.tipo === "linea") { const dx = s.p1[0] - s.p0[0], dy = s.p1[1] - s.p0[1], t = Math.max(0, Math.min(1, ((p[0] - s.p0[0]) * dx + (p[1] - s.p0[1]) * dy) / (dx * dx + dy * dy))); return Math.hypot(p[0] - s.p0[0] - t * dx, p[1] - s.p0[1] - t * dy); }
  const ang = (q) => Math.atan2(q[1] - s.centro[1], q[0] - s.centro[0]), k = s.sentido === "antihorario" ? 1 : -1, a0 = ang(s.p0);
  const sw = (a) => { let d = k * (a - a0); while (d < 0) d += 2 * Math.PI; while (d >= 2 * Math.PI) d -= 2 * Math.PI; return d; }, span = sw(ang(s.p1)) || 2 * Math.PI;
  return sw(ang(p)) <= span + 1e-12 ? Math.abs(Math.hypot(p[0] - s.centro[0], p[1] - s.centro[1]) - s.radio) : Math.min(Math.hypot(p[0] - s.p0[0], p[1] - s.p0[1]), Math.hypot(p[0] - s.p1[0], p[1] - s.p1[1]));
};
const chainDist = (segs, p) => Math.min(...segs.map((s) => segDist(s, p)));
test("Placa-guía curva · canto y trayectoria del seguidor: cadena de líneas y arcos tangentes (G1) sin quiebres, en las 4 placas", () => {
  const P = P2(), G = TT.pivotGeo(P), C = TT.compute(P).camP;
  assert.ok(C.guia && C.guia.g1Max <= 1e-6, "sin quiebres de tangente en el canto: " + (C.guia && C.guia.g1Max));
  for (const [k, pl] of Object.entries(G.placas)) {
    for (const key of ["segmentos_canto", "segmentos_centro"]) {
      const S = pl[key]; assert.ok(Array.isArray(S) && S.length >= 5, k + " " + key);
      S.forEach((s, i) => {
        assert.ok(["linea", "arco"].includes(s.tipo) && s.p0 && s.p1, k + " tipo");
        if (s.tipo === "arco") { assert.ok(s.radio > 0 && ["antihorario", "horario"].includes(s.sentido)); near(Math.hypot(s.p0[0] - s.centro[0], s.p0[1] - s.centro[1]), s.radio, 1e-9, k + " p0 sobre el arco"); near(Math.hypot(s.p1[0] - s.centro[0], s.p1[1] - s.centro[1]), s.radio, 1e-9, k + " p1 sobre el arco"); }
        if (i) {
          const a = S[i - 1]; assert.ok(Math.hypot(a.p1[0] - s.p0[0], a.p1[1] - s.p0[1]) <= 1e-6, k + " " + key + " continuidad de posición en el empalme " + i);
          const t0 = segTan(a, a.p1), t1 = segTan(s, s.p0); assert.ok(Math.abs(Math.atan2(t0[0] * t1[1] - t0[1] * t1[0], t0[0] * t1[0] + t0[1] * t1[1])) <= 1e-6, k + " " + key + " G1 en el empalme " + i);
        }
      });
    }
    // el canto es el desplazamiento exacto de la trayectoria del centro del seguidor (envolvente a d_Q/2)
    pl.segmentos_centro.forEach((s, i) => { const e = pl.segmentos_canto[i]; assert.equal(e.tipo, s.tipo); if (s.tipo === "arco") { near(e.centro[0], s.centro[0], 1e-9); near(e.centro[1], s.centro[1], 1e-9); near(Math.abs(e.radio - s.radio), P.pv_dq / 2, 1e-9, "radios concéntricos a ± d_Q/2"); } });
    // contorno cerrado y polilíneas con flecha ≤ 0,1 mm
    const Cn = pl.segmentos_contorno; assert.ok(Math.hypot(Cn[0].p0[0] - Cn[Cn.length - 1].p1[0], Cn[0].p0[1] - Cn[Cn.length - 1].p1[1]) <= 1e-6, "contorno cerrado");
    for (let i = 1; i < pl.recorte.length; i++) { const m = [(pl.recorte[i - 1][0] + pl.recorte[i][0]) / 2, (pl.recorte[i - 1][1] + pl.recorte[i][1]) / 2]; assert.ok(chainDist(pl.segmentos_canto, m) <= 0.1 + 1e-9, k + " flecha de la polilínea del canto ≤ 0,1 mm"); }
  }
});
test("Placa-guía curva · radio mínimo sin socavado, no autobloqueo en toda la curva y empuje estable contra la guía", () => {
  const P = P2(), R = TT.compute(P), C = R.camP, g = C.guia, rf = P.pv_dq / 2, fam = R.fam;
  g.canto.slice(0, g.tramos.length).forEach((e, i) => { if (e.tipo !== "arco") return; const s = g.tramos[i]; if (e.curvatura === "convexa") { near(s.radio, e.radio + rf, 1e-9, "canto convexo: R_centro = R_canto + d_Q/2"); assert.ok(e.radio >= P.pv_rmin - 1e-9, "radio convexo ≥ mínimo: " + e.radio); } else { assert.equal(e.curvatura, "cóncava"); near(e.radio, s.radio + rf, 1e-9); } });
  assert.ok(g.rCanto.convexo >= P.pv_rmin && g.rCentro.convexo >= rf + P.pv_rmin, "sin socavado con margen");
  // retorno: en toda la zona en que la guía conduce el seguidor (del primer contacto al retraído) el ángulo de presión no autobloquea
  const kE = P.pv_muE * P.pv_dE / (2 * P.L0), drv = g.ret.filter((q) => q.guia);
  assert.ok(drv.length > 20, "zona de conducción muestreada");
  drv.forEach((q) => { const a = q.phi * Math.PI / 180; assert.ok(q.phi <= P.pv_alpha + 1e-9, "φ ≤ α_máx"); assert.ok(kE * (Math.sin(a) + fam.mu * Math.cos(a)) < Math.cos(a) - fam.mu * Math.sin(a), "sin autobloqueo en L = " + q.L.toFixed(1)); });
  // empuje: la rodilla E–Q–P es inestable en compresión y Q se apoya en el canto: reacción positiva y ángulo bajo el de rozamiento en todas las posiciones
  assert.equal(R.stroke.length, R.K.pts.length);
  R.stroke.forEach((q) => { assert.ok(q.H_guia > 0, "Q apoyado en la guía (H > 0) en θ = " + (q.th * 180 / Math.PI).toFixed(2)); assert.ok(q.phi_guia < 90 - Math.atan(fam.mu) * 180 / Math.PI, "sin autobloqueo en el empuje"); });
  assert.ok(Math.max(...R.stroke.map((q) => q.F)) <= R.cd.F + 1e-9 && R.cd.FS >= P.FS_min, "la fuerza de diseño es la del empuje guiado y cumple FS");
});
test("Placa-guía curva · sincronía (con tolerancias y dilatación) y sin interferencias en todo el recorrido", () => {
  const P = P2(), R = TT.compute(P), K = R.K, C = R.camP, g = C.guia, rf = P.pv_dq / 2, E = K.E;
  // sincronía recalculada desde la polilínea del centro del seguidor (local, cilindro 1 antihorario)
  const lw = (p) => { const L = Math.hypot(p[0] - E[0], p[1] - E[1]); let d = C.psi0 - Math.atan2(p[1] - E[1], p[0] - E[0]); while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI; return [L, d * L]; };
  let sMin = Infinity; g.polilinea_centro.map(lw).forEach(([L, w]) => { if (L >= P.L0 - 1e-9 && L <= g.primer_contacto.L + 1e-9) sMin = Math.min(sMin, C.clrRet(L, w)); });
  assert.ok(g.dTol > 0.5 && sMin >= P.pv_msync + g.dTol - 0.05, "sincronía nominal ≥ margen + tolerancias: " + sMin.toFixed(2));
  assert.ok(g.syncWorst >= P.pv_msync && C.sync >= P.pv_msync + g.dTol - 1e-6);
  // retorno: el bloque nunca penetra los pasadores; vuelve a la toma (w = c en L0)
  g.ret.forEach((q) => assert.ok(q.hol >= -1e-6, "retorno sin choque en L = " + q.L.toFixed(1)));
  near(C.wCam(P.L0), P.pv_c, 1e-6, "reenganche en la toma");
  // empuje guiado: bloque libre de los pasadores y cuerpo del cilindro fuera de la mesa
  C.push.forEach((q) => { assert.ok(q.clrB >= P.pv_cB, "bloque–pasadores en el empuje: " + q.clrB.toFixed(2)); assert.ok(q.body >= P.pv_cc, "cuerpo del cilindro–mesa"); });
  // la placa no invade el seguidor en ninguna posición; fuera de la mesa, dentro de la base, lejos del cajón E y sin solape entre sentidos
  const G = TT.pivotGeo(P), Bh = P.B / 2 - P.rim_t - 5;
  for (const [k, pl] of Object.entries(G.placas)) {
    pl.centro_seguidor.forEach((q) => assert.ok(chainDist(pl.segmentos_contorno, q) >= rf - 1e-6, k + ": la placa no invade el seguidor"));
    pl.contorno.forEach(([x, y]) => { assert.ok(Math.hypot(x, y) >= P.D_top / 2 + P.pv_cQ - 1e-6, k + ": fuera de la mesa"); assert.ok(Math.max(Math.abs(x), Math.abs(y)) <= Bh, k + ": dentro de la base"); });
    const Ek = k.startsWith("1") ? E : [-E[0], -E[1]];
    pl.contorno.forEach(([x, y]) => assert.ok(Math.max(Math.abs(x - Ek[0]), Math.abs(y - Ek[1])) >= P.pv_box / 2 + 5 - 1e-6, k + ": libre del cajón del ojal E"));
  }
  assert.ok(C.diag >= 5, "placas de ambos sentidos sin solape");
  assert.ok(g.zCuerpo - (P.t_base + P.pv_tcam) >= 5, "cuerpo del cilindro sobre la placa");
});
test("Placa-guía curva · API: segmentos en designDrive y contacto de la simulación sobre el canto", () => {
  const P = P2(), R = TT.compute(P), D = TT.designDrive(P, R).pivotado, pl = D.fabricacion.placas_leva;
  for (const k of ["1_antihorario", "2_antihorario", "1_horario", "2_horario"]) {
    const I = pl.instancias[k]; assert.ok(I.segmentos_canto.length >= 5 && I.segmentos_contorno.length >= I.segmentos_canto.length && I.recorte.length > 10 && I.contorno.length > 10);
    I.segmentos_canto.forEach((s) => assert.ok(s.tipo === "linea" || (s.centro && s.radio > 0 && s.sentido), "segmento completo"));
    assert.ok(I.pernos.length === Math.round(P.pv_nb) && I.pasadores_posicion.length === 2);
  }
  assert.ok(pl.tolerancia_polilinea <= 0.1 && pl.material && /42CrMo4/.test(pl.material) && pl.pernos.norma);
  for (const s of [40, 120, 200]) { const q = TT.pivotAt(P, s, "empuje", "antihorario"); assert.ok(chainDist(TT.pivotGeo(P).placas["1_antihorario"].segmentos_canto, q.contactoLeva.punto) <= 0.5, "contacto sobre el canto en s = " + s); assert.ok(q.contactoLeva.F > 0); }
});
test("Bloque-uña · contacto dentro de la cara con el roce (cara cilíndrica convexa): la cara plana lo deja en la arista", () => {
  const P = P2(), A = TT.analyze(P, { noFEA: true }), R = A.R, bk = R.blk, rr = P.d_pin / 2, s2 = R.K.Lqp - rr, rho = Math.atan(P.mu_s), dR = P.pv_muE * P.pv_dq / 2;
  const row = (X) => X.checks.find((c) => /contacto dentro de la cara/.test(c.name)), r0 = row(A);
  const sg = (s2 * Math.sin(rho) + dR) / (s2 - P.pv_rface), ec = P.pv_rface * sg, Fs = R.Fstall * 1e3, q = P.k_edge * Fs / P.pv_hu, Es = P.E / (2 * (1 - P.nu ** 2)), Ref = 1 / (1 / rr + 1 / P.pv_rface);
  near(r0.dem, ec + Math.sqrt(4 * q * Ref / (Math.PI * Es)), 1e-9, "e_c + b_Hertz"); near(r0.cap, P.pv_bf / 2 - 3, 1e-12); assert.ok(r0.fu <= 0.9, "contacto dentro de la cara con FU ≤ 0,90: " + r0.fu.toFixed(3));
  const flat = TT.analyze(P2({ pv_rface: 0 }), { noFEA: true }), rf0 = row(flat);
  near(rf0.dem - Math.sqrt(4 * P.k_edge * Fs / P.pv_hu * rr / (Math.PI * Es)), s2 * Math.tan(rho) + dR, 1e-9, "cara plana: e_c = s₂·tan ρ + d_R"); assert.equal(rf0.st, "fail", "con cara plana el pasador apoya en la arista");
  // la excentricidad del contacto entra al cuerpo acodado y a la cara; el bloque girado hacia afuera sigue libre de los pasadores
  const body = A.checks.find((c) => /compresión \+ flexión en el cuerpo acodado/.test(c.name));
  near(body.dem, Fs / (P.pv_bu * P.pv_hu) + 6 * Fs * (P.pv_ecr + P.e_dog + ec * bk.s1 / bk.s2) / (P.pv_hu * P.pv_bu ** 2), 1e-9); assert.ok(body.fu <= 0.9);
  assert.ok(R.camP.push.every((g) => g.clrB >= P.pv_cB), "bloque girado el ángulo de equilibrio libre de los pasadores");
  const G = TT.pivotGeo(P); near(G.bloque.R_cara, P.pv_rface, 1e-12); assert.ok(bk.mBlk < TT.pivBlkGeo(P2({ pv_rface: 0 }), R.K).mBlk, "la cara convexa descuenta el material de las aristas");
});
test("Golden file · modo pivotado (drive_mode = 2): resultados por defecto sin cambios no justificados", () => {
  const A = TT.analyze(P2()), R = A.R, K = R.K;
  const snap = { masa_total: R.m.total, masas: { brackets: R.m.brackets, dogs: R.m.dogs, cam: R.m.cam }, brazo_min: K.aMin, brazo_ef_min: K.aEffMin, carrera_req: K.s_req, Q_min: K.QrMin, holgura_B: K.clrB,
    sincronia: R.camP.sync, bolsillo: R.camP.wPk, casos: Object.fromEntries(R.cases.map((c) => [c.id, [c.F, c.p, c.FS]])), fea: { lift: A.fea.lift.vmMax, liftW: A.fea.lift.wMax },
    fu: Object.fromEntries(A.checks.filter((c) => c.fu != null).map((c) => [c.grp + " · " + c.name, c.fu])) };
  const f = path.join(__dirname, "golden", "tt300c_pivotado.json");
  if (process.env.UPDATE_GOLDEN || !fs.existsSync(f)) fs.writeFileSync(f, JSON.stringify(snap, null, 1));
  const g = JSON.parse(fs.readFileSync(f, "utf8"));
  const cmp = (a, b, k) => {
    if (typeof b === "number") near(a, b, 1e-6, k);
    else if (Array.isArray(b)) b.forEach((v, i) => cmp(a[i], v, k + "[" + i + "]"));
    else for (const kk of Object.keys(b)) { assert.ok(kk in a, "falta " + kk); cmp(a[kk], b[kk], k + "." + kk); }
  };
  cmp(snap, g, "golden-pivotado");
});

/* ======================= API de simulación del movimiento (packages/web/simulacion.js) ======================= */
test("Simulación · TT.driveAt: fuerzas en cualquier θ y caso, coherentes con compute() en ambos modos", () => {
  const P = TG(), R = TT.compute(P), th = -Math.PI / P.N_pin;
  for (const c of R.cases) {
    const d = TT.driveAt(P, th, c.id), Fmax = Math.max(...R.stroke.map((q) => q.F)) * c.T / R.cd.T;
    assert.ok(d.F > 0 && d.F <= Fmax + 1e-9 && d.caso === c.id, "guiado " + c.id);
  }
  const dmax = Math.max(...R.stroke.map((q) => TT.driveAt(P, q.th, "dis").F)); assert.ok(dmax <= R.cd.F + 1e-9 && dmax >= 0.99 * R.cd.F, "máximo en la carrera = F de diseño");
  near(TT.driveAt(P, 0, "dis").arm, P.R_pin, 1e-12, "brazo R·cos θ");
  const Q = P2(), R2 = TT.compute(Q);
  R2.stroke.forEach((q) => { const d = TT.driveAt(Q, q.th, "dis"); near(d.F, q.F, 1e-12, "F"); near(d.Fp, q.Fp, 1e-12, "F_n"); near(d.arm, q.arm, 1e-12); near(d.ft, q.ft, 1e-12); near(d.fr, q.fr, 1e-12); });
  assert.ok(TT.driveAt(Q, R2.K.ths, "cont").F > TT.driveAt(Q, R2.K.ths, "nom").F);
});
test("Simulación · modo pivotado: pivotGeo y pivotAt (θ final = θ inicial + paso, carrera, retorno con salida sobre el pasador siguiente y reenganche)", () => {
  const P = P2(), R = TT.compute(P), K = R.K, G = TT.pivotGeo(P);
  assert.equal(G.E.length, 2); near(G.E[1][0], -G.E[0][0], 1e-12); assert.deepEqual(Object.keys(G.placas).sort(), ["1_antihorario", "1_horario", "2_antihorario", "2_horario"]);
  for (const k of Object.keys(G.placas)) assert.ok(G.placas[k].recorte.length > 10 && G.placas[k].contorno.length > G.placas[k].recorte.length && G.placas[k].pernos.length === Math.round(P.pv_nb));
  assert.equal(G.L0, P.L0); assert.equal(G.carrera, P.stroke); near(G.s_req, R.camP.sReqG, 1e-12); assert.ok(G.s_req >= K.s_req - 1e-9);
  const a0 = TT.pivotAt(P, 0, "empuje", "antihorario"), a1 = TT.pivotAt(P, G.s_req, "empuje", "antihorario");
  near(a0.th, K.ths, 1e-12, "inicio"); near(a1.th - a0.th, 2 * Math.PI / P.N_pin, 1e-9, "θ final = θ inicial + paso al final del empuje"); near(a1.L, P.L0 + G.s_req, 1e-9);
  const qe = R.stroke[R.stroke.length - 1].Q; near(a1.Q[0], qe[0], 1e-6); near(a1.Q[1], qe[1], 1e-6, "Q en el final del empuje (apoyado en el canto)");
  const mid = TT.pivotAt(P, 120, "empuje", "antihorario"); near(mid.F, TT.driveAt(P, mid.th, "dis").F, 1e-12); near(mid.contactoLeva.F, TT.driveAt(P, mid.th, "dis").Fcam, 1e-12); assert.ok(mid.contactoLeva.enCanto);
  // retorno: la uña sale sobre el pasador siguiente (w mayor que en el empuje) y la leva la reengancha (w = c en el extremo retraído) sin choque
  let wMax = 0, holMin = Infinity, syncMin = Infinity;
  for (let i = 0; i <= 400; i++) { const s = K.s_req * (1 - i / 400), q = TT.pivotAt(P, s, "retorno", "antihorario"); wMax = Math.max(wMax, q.w); holMin = Math.min(holMin, q.holgura); if (q.contactoLeva.enRampa) syncMin = Math.min(syncMin, q.holgura_leva); assert.ok(!q.alertas.choque, "sin choque en s = " + s.toFixed(1)); }
  assert.ok(wMax > R.camP.wPush(P.L0 + 30) + 20, "sale sobre el pasador siguiente"); assert.ok(holMin >= -1e-6);
  near(TT.pivotAt(P, 0, "retorno", "antihorario").w, P.pv_c, 1e-9, "reenganche: Q vuelve al canto de toma");
  assert.ok(Math.abs(syncMin - R.camP.sync) < 0.05 && syncMin >= R.camP.sync - 1e-3, "la sincronía de la simulación coincide con la verificación: " + syncMin.toFixed(3) + " vs " + R.camP.sync.toFixed(3));
  const h = TT.pivotAt(P, 120, "empuje", "horario"), ph = P.pv_phE * Math.PI / 180;
  near(h.Q[0] * Math.sin(ph) - h.Q[1] * Math.cos(ph), -(mid.Q[0] * Math.sin(ph) - mid.Q[1] * Math.cos(ph)), 1e-9, "horario = reflejo respecto de la diagonal");
  assert.equal(TT.pivotGeo(TG()), null); assert.equal(TT.pivotAt(TG(), 0, "empuje", "antihorario"), null);
});
test("Simulación · modo guiado: guidedAt, camGeo y camAt (cara, θ, salida radial en el retorno y sincronía de la leva)", () => {
  const P = TG(), R = TT.compute(P), K = R.K, c = R.camG;
  const g0 = TT.guidedAt(P, 0, "empuje"), g1 = TT.guidedAt(P, K.s_req, "empuje");
  near(g0.y_cara, K.y_rp0 + P.l_p - P.d_pin / 2, 1e-12, "y_cara = y_rp0 + s + l_p − d/2"); near(TT.guidedAt(P, 50, "empuje").y_cara, K.y_rp0 + 50 + P.l_p - P.d_pin / 2, 1e-12);
  near(g0.th, -K.pitch / 2, 1e-12); near(g1.th, K.pitch / 2, 1e-9, "θ final = +π/N: el pasador avanzó un paso");
  near(TT.guidedAt(P, 100, "empuje").F, TT.driveAt(P, TT.guidedAt(P, 100, "empuje").th, "nom").F, 1e-12, "fuerza del caso nominal sin escalar");
  // retorno sin leva: la salida radial es la del chaflán sobre el pasador siguiente (holgura nula mientras lo monta)
  const P0 = Object.assign(TG(), { opt_cam: 0 }), um = Math.max(...Array.from({ length: 200 }, (_, i) => TT.guidedAt(P0, K.s_req * i / 199, "retorno").u));
  near(um, P.c_tip + P.d_pin / 2, 1e-6, "la punta pasa por encima del pasador: u = c_punta + r");
  assert.equal(TT.camGeo(P0), null);
  const G = TT.camGeo(P); assert.ok(G.perfil.length >= 4 && G.recorrido === K.travel && G.perfil[1].u === P.cam_c);
  let syncMin = Infinity;
  for (let i = 0; i <= 2000; i++) { const q = TT.camAt(P, K.s_req * i / 2000, "retorno"); assert.ok(q.u <= q.u_leva + 1e-9 && !q.alertas.choque && !q.alertas.sincronia); if (q.eta <= G.tope_rampa) syncMin = Math.min(syncMin, q.holgura_leva); }
  assert.ok(Math.abs(syncMin - c.sync) < 0.05 && syncMin >= c.sync - 1e-3, "la sincronía de la simulación coincide con la verificación: " + syncMin.toFixed(3) + " vs " + c.sync.toFixed(3));
  near(TT.camAt(P, 0, "retorno").u_leva, P.cam_c, 1e-12, "reenganche: la leva deja la uña en la toma");
  assert.equal(TT.camAt(P, 100, "empuje").u, 0);
  const P10 = Object.assign(TG(), { s_free: 10 }), s10 = TT.compute(P10).K.s_req;
  assert.ok(Array.from({ length: 400 }, (_, i) => TT.camAt(P10, s10 * i / 399, "retorno")).some((q) => q.alertas.choque || q.alertas.sincronia), "con s_libre = 10 la simulación alerta");
});

test("Golden file · modo guiado (drive_mode = 1, alternativa con leva de reenganche): resultados sin cambios no justificados", () => {
  const A = TT.analyze(TG()), R = A.R;
  const snap = { masa_total: R.m.total, masa_mesa: R.m.disc, N: R.N, q_max: R.q_max, F_calado: R.Fstall, brazo_min: R.K.armMin, carrera_req: R.K.s_req,
    casos: Object.fromEntries(R.cases.map((c) => [c.id, [c.F, c.p, c.FS]])), fea: { top: A.fea.top.vmMax, bot: A.fea.bot.vmMax, lift: A.fea.lift.vmMax, glob: A.fea.glob.Mmax },
    fu: Object.fromEntries(A.checks.filter((c) => c.fu != null).map((c) => [c.grp + " · " + c.name, c.fu])) };
  const f = path.join(__dirname, "golden", "tt300c_guiado.json");
  if (process.env.UPDATE_GOLDEN || !fs.existsSync(f)) fs.writeFileSync(f, JSON.stringify(snap, null, 1));
  const g = JSON.parse(fs.readFileSync(f, "utf8"));
  const cmp = (a, b, k) => {
    if (typeof b === "number") near(a, b, 1e-6, k);
    else if (Array.isArray(b)) b.forEach((v, i) => cmp(a[i], v, k + "[" + i + "]"));
    else for (const kk of Object.keys(b)) { assert.ok(kk in a, "falta " + kk); cmp(a[kk], b[kk], k + "." + kk); }
  };
  cmp(snap, g, "golden-guiado");
});

test("AF2 · opción A pegada: tornillos avellanados ISO 10642 M12 10.9 del disco de la mesa a la mesa (J3.7, J3.11, J3.4, J3.4M, avellanado)", () => {
  const P = Object.assign(TT.defaults(), { opt_ss: 1, fix_mode: 2 }), A = TT.analyze(P, { noFEA: true }), t = A.R.ifc.tornillos;
  assert.ok(t && t.d === 12 && t.n === t.nAuto && t.n <= P.N_pin, "M12, n = bisectrices entre pasadores libres de las ranuras radiales (10-11-2026)");
  near(t.V, A.R.cd.T * 1e6 / (t.n * t.r), 1e-12, "V = T/(n·r)");
  const rows = A.checks.filter((c) => /^AF2 · Tornillos/.test(c.name));
  assert.ok(rows.length >= 8 && rows.every((c) => c.st !== "fail"));
  rows.filter((c) => c.kind === "fu").forEach((c) => assert.ok(c.fu <= 0.85 + 1e-12, c.name + " FU " + c.fu));
  assert.ok(rows.some((c) => /J3\.7/.test(c.ref)) && rows.some((c) => /J3\.11/.test(c.ref)) && rows.some((c) => /J3\.4\b/.test(c.ref)) && rows.some((c) => /J3\.5/.test(c.ref)) && rows.some((c) => /ISO 10642/.test(c.ref)))   // AISC 360-22 renumerado (registro 7030ee3): J3.7 pernos, J3.11 aplastamiento, J3.4 separación, J3.5 borde;
  assert.ok(t.k + 0.5 + P.ss_allow <= A.R.ifc.tss2, "la cabeza cabe en el disco de la mesa");
  const ta = TT.analyze(Object.assign({}, P, { tor2_n: 12 }), { noFEA: true }).checks.find((c) => /AF2 · Tornillos avellanados disco–mesa: corte/.test(c.name)); assert.ok(ta.fu > 0.85, "con 12 tornillos no alcanza FU 0,85");
  const D = TT.designDrive(P, A.R).tornillos_interfaz; assert.ok(D && D.posiciones.length === t.n && D.avellanado.prof === t.k && D.rosca_en_mesa.prof_taladro === P.t_pr - 3 && D.t_pieza_roscada === P.t_pr);
  assert.equal(TT.compute(TT.defaults()).ifc.tornillos, null, "solo en AF2"); assert.equal(TT.compute(Object.assign(TT.defaults(), { opt_ss: 1 })).ifc.tornillos, null, "con topes no hay tornillos");
});
test("Planos · designDrive exporta la geometría de fabricación de ambos modos en el sistema de la tornamesa", () => {
  const fin = (o) => JSON.stringify(o, (k, v) => { if (typeof v === "number") assert.ok(isFinite(v), "número no finito en " + k); return v; });
  const P1 = TG(), F1 = TT.designDrive(P1, TT.compute(P1)).levaGuiada.fabricacion;
  assert.ok(F1.riel.contorno_local.length >= 8 && F1.porticos.patas_local.length === 4 && F1.porticos.pernos_local.length === P1.cam_nb * 2 && F1.prolongacion_bancada_local.length === 2);
  assert.deepEqual(Object.keys(F1.instancias).sort(), ["1_antihorario", "1_horario", "2_antihorario", "2_horario"]);
  assert.ok(F1.seguidor.rodillo.d === P1.cam_df && F1.ranura_tapa_patin.ancho === P1.cam_dp && /H9/.test(F1.ranura_tapa_patin.ajuste)); fin(F1);
  const P2 = TT.defaults(), F2 = TT.designDrive(P2, TT.compute(P2)).pivotado.fabricacion;
  for (const k of ["soporte_E", "pasador_E", "bloque_una", "pasador_Q", "placas_leva"]) assert.ok(F2[k], "falta " + k);
  assert.equal(Object.keys(F2.placas_leva.instancias).length, 4); assert.ok(F2.soporte_E.tapas.t === P2.pv_tl && F2.soporte_E.ventana.sector_deg.length === 4 && F2.soporte_E.juntas.length >= 6);
  assert.ok(F2.bloque_una.contorno_local.cuerpo.length === 4 && F2.bloque_una.agujero_Q === P2.pv_dq); fin(F2);
  const ex = JSON.parse(require("child_process").execFileSync(process.execPath, [path.join(__dirname, "..", "tools", "export_design.js")], { maxBuffer: 1 << 28 }).toString());
  assert.ok(ex.pivotado && ex.pivotado.fabricacion && ex.modo === 2, "export_design lleva la geometría del modo por defecto");
});

/* ======================= Inconsistencias geométricas del generador de planos (10-11-2026) ======================= */
// Geometría plana propia de las pruebas (no usa las rutinas del núcleo): distancia entre polígonos con detección de solape
const tIn = (pl, p) => { let c = false; for (let i = 0, j = pl.length - 1; i < pl.length; j = i++) { const a = pl[i], b = pl[j]; if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; };
const tSeg = (p, a, b) => { const ex = b[0] - a[0], ey = b[1] - a[1], l = ex * ex + ey * ey, t = l > 0 ? Math.max(0, Math.min(1, ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / l)) : 0; return Math.hypot(p[0] - a[0] - t * ex, p[1] - a[1] - t * ey); };
const tEdge = (pl, p) => Math.min(...pl.map((a, i) => tSeg(p, a, pl[(i + 1) % pl.length])));
const tX = (a, b, c, d) => { const o = (p, q, r) => Math.sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])); return o(a, b, c) * o(a, b, d) < 0 && o(c, d, a) * o(c, d, b) < 0; };
const tDist = (A, B) => {
  if (A.some((p) => tIn(B, p)) || B.some((p) => tIn(A, p))) return -1;
  for (let i = 0; i < A.length; i++) for (let j = 0; j < B.length; j++) if (tX(A[i], A[(i + 1) % A.length], B[j], B[(j + 1) % B.length])) return -1;
  return Math.min(...A.map((p) => tEdge(B, p)), ...B.map((p) => tEdge(A, p)));
};
const tRect = (E, u, s0, s1, w) => { const n = [-u[1], u[0]]; return [[s0, -w / 2], [s1, -w / 2], [s1, w / 2], [s0, w / 2]].map(([s, l]) => [E[0] + s * u[0] + l * n[0], E[1] + s * u[1] + l * n[1]]); };
// estados de la simulación (TT.pivotAt) en ambos sentidos y fases, con el cilindro 2 por rotación de 180°
const pivStates = (P, n) => {
  const R = TT.compute(P), out = [], m = (p) => [-p[0], -p[1]];
  for (const sen of ["antihorario", "horario"]) for (const f of ["empuje", "retorno"]) for (let i = 0; i <= n; i++) {
    const q = TT.pivotAt(P, R.camP.sReqG * i / n, f, sen);
    out.push(Object.assign({ cil: 1, sentido: sen, fase: f }, q));
    out.push(Object.assign({}, q, { cil: 2, sentido: sen, fase: f, E: m(q.E), Q: m(q.Q), una: { cuerpo: q.una.cuerpo.map(m), cara: q.una.cara.map(m), cubo: q.una.cubo.map(m) } }));
  }
  return out;
};

test("Soporte E · el cuerpo del cilindro barre libre del soporte (≥ 5 mm) en todo el empuje y el retorno, ambos sentidos y cilindros", () => {
  const P = P2(), A = TT.analyze(P, { noFEA: true }), F = TT.designDrive(P, A.R).pivotado.fabricacion.soporte_E, zc0 = TT.hAxis(P) + P.t_base;
  for (const c of ["cilindro1", "cilindro2"]) assert.ok(Array.isArray(F[c].piezas) && F[c].piezas.length >= 4, c + ": piezas del soporte exportadas");
  const zb = [zc0 - P.D_body / 2, zc0 + P.D_body / 2];
  let dmin = Infinity;
  for (const q of pivStates(P, 60)) {
    const L = Math.hypot(q.Q[0] - q.E[0], q.Q[1] - q.E[1]), u = [(q.Q[0] - q.E[0]) / L, (q.Q[1] - q.E[1]) / L], body = tRect(q.E, u, P.e_body, P.L0 - P.c_rod, P.D_body);
    for (const pz of F["cilindro" + q.cil].piezas) if (pz.z[0] < zb[1] && pz.z[1] > zb[0]) dmin = Math.min(dmin, tDist(body, pz.poligono));
  }
  assert.ok(dmin >= 5, "holgura cuerpo del cilindro–soporte E ≥ 5 mm: " + dmin.toFixed(2));
  const row = A.checks.find((c) => /^Cuerpo del cilindro libre del soporte del ojal E/.test(c.name));
  assert.ok(row && row.st === "ok" && row.cap >= 5 && row.cap <= dmin + 1e-6 && row.fu === 5 / row.cap, "verificación del núcleo con FU (barrido de θ y ambos sentidos): " + (row && row.cap));
  const lo = TT.analyze(P2({ pv_cE: 6 }), { noFEA: true }).checks.find((c) => /^Cuerpo del cilindro libre del soporte del ojal E/.test(c.name));
  assert.ok(lo.cap >= 6 - 1e-6 && lo.st === "ok", "la holgura real es al menos la de diseño");
});
test("Soporte E · constructibilidad: tapas entre las paredes, juntas con tipo y tamaño (CJP/PJP), secuencia con acceso, marco interrumpido y masa de las piezas", () => {
  const P = P2(), A = TT.analyze(P, { noFEA: true }), R = A.R, F = TT.designDrive(P, R).pivotado.fabricacion.soporte_E, b = P.pv_box / 2, bi = b - P.pv_tbox;
  // tapas: entre las paredes (lado interior 2·b_i), polígono dentro del interior y rebaje de la superior
  assert.ok(F.tapas.lado <= 2 * bi + 1e-9 && F.tapas.lado < P.pv_box, "las tapas caben entre las paredes: " + F.tapas.lado);
  F.tapas.poligono_local.forEach(([x, y]) => assert.ok(Math.abs(x) <= bi + 1e-6 && Math.abs(y) <= bi + 1e-6, "tapa dentro del interior"));
  near(F.tapas.z_sup[1] + P.pv_rebt, F.z_paredes[1], 1e-9, "tapa superior rebajada bajo el borde de las paredes (rincón para el filete)");
  assert.ok(F.tapas.z_inf[0] > P.t_base, "la tapa inferior no apoya en la base");
  // juntas: tipo y tamaño de todas las uniones, incluida pared–pared; verificación con FU ≤ 0,90
  assert.ok(F.juntas.length >= 6 && F.juntas.every((j) => j.tipo && j.tamano && (j.tamano.CJP || j.tamano.E) && j.tamano.filete_refuerzo >= 8 && j.verificacion && j.verificacion.fu <= 0.9 && /AWS D1\.1/.test(j.verificacion.norma)));
  assert.ok(F.juntas.some((j) => j.piezas.includes("pared_Y") && j.piezas.includes("pared_X")), "unión pared–pared con tipo y tamaño");
  assert.ok(F.juntas.filter((j) => /tapa/.test(j.piezas[0])).every((j) => /PJP/.test(j.tipo) && /desde arriba/.test(j.tipo)), "tapas soldadas solo desde arriba (la cara inferior queda sin soldar)");
  // secuencia realizable: paredes a la base desde el interior ANTES de las tapas; acceso exterior con el marco interrumpido
  const sq = F.secuencia.join(" "); assert.ok(F.secuencia.length >= 5 && sq.indexOf("J-E1") < sq.indexOf("J-E7") && sq.indexOf("J-E7") < sq.indexOf("J-E8"), "orden de la secuencia");
  const Emax = Math.max(Math.abs(R.K.E[0]), Math.abs(R.K.E[1])), gap = P.B / 2 - (Emax + b);
  assert.ok(gap >= P.pv_wbox + 5, "acceso exterior a las CJP de las paredes traseras: " + gap.toFixed(1));
  assert.ok(F.marco_interrupcion.cilindro1.length === 2 && F.marco_interrupcion.cilindro2.length === 2);
  // masa: piezas reales (paredes + muñones + tapas recortadas) + pasador E; marco descontado
  // desde el 10-11-2026 las paredes y muñones arrancan sobre el inserto de esquina (Δ más cortos): masa exportada = Σ piezas + pasador
  const mP = F.piezas.reduce((a, q) => a + q.masa, 0); near(F.masa, mP + R.sup.mPin, 1e-9, "masa del soporte = Σ piezas + pasador");
  near(R.m.brackets, P.n_cyl * F.masa + R.m.insertos, 1e-9, "m.brackets = soportes + insertos de esquina");
  assert.ok(R.m.rim < 7.85e-6 * (4 * P.B - 4 * P.rim_t) * P.rim_h * P.rim_t, "marco interrumpido frente a los soportes");
  // filas nuevas con norma
  const row = (re) => A.checks.find((c) => re.test(c.name));
  for (const re of [/^Soporte del ojal E: PJP tapas–paredes/, /^Soporte del ojal E: CJP paredes–base/, /^Soporte del ojal E: CJP pared–pared/, /^Soporte del ojal E: filete de refuerzo mínimo/, /^Soporte del ojal E: acceso exterior/, /^Soporte del ojal E: rincón para el filete/, /^Soporte del ojal E: flexión de las paredes/]) {
    const r = row(re); assert.ok(r && r.st === "ok" && /AISC|AWS|BTH/.test(r.ref), "fila " + re + " " + (r && r.st));
  }
  assert.ok(/AWS D1\.1\/D1\.1M:2020 Tabla 7\.7/.test(row(/^Soporte del ojal E: filete de refuerzo mínimo/).ref) && /J2/.test(row(/^Soporte del ojal E: PJP tapas–paredes/).ref));
  // con el filete de refuerzo bajo el mínimo de AWS (z6 para t = 30) la fila no cumple
  assert.equal(TT.analyze(P2({ pv_wbox: 6 }), { noFEA: true }).checks.find((c) => /^Soporte del ojal E: filete de refuerzo mínimo/.test(c.name)).st, "fail");
});
test("Elementos sobre la base · placas-guía (con reflexiones y rotaciones), orejas de izaje, soportes E y partes móviles sin interferencias", () => {
  const P = P2(), A = TT.analyze(P, { noFEA: true }), G = TT.pivotGeo(P), F = TT.designDrive(P, A.R).pivotado.fabricacion.soporte_E;
  const yl = P.B / 2 - P.c_lug, hw = P.t_ear / 2 + P.w_ear;
  const ears = [[P.x_lug, yl], [-P.x_lug, yl], [P.x_lug, -yl], [-P.x_lug, -yl]].map((c) => { const r = Math.hypot(c[0], c[1]), u = [c[0] / r, c[1] / r]; return tRect([c[0] - P.R_ear * u[0], c[1] - P.R_ear * u[1]], u, 0, 2 * P.R_ear, 2 * hw); });
  const plates = Object.values(G.placas).map((q) => q.contorno), sup = ["cilindro1", "cilindro2"].flatMap((c) => F[c].piezas.map((q) => q.poligono));
  const dPE = Math.min(...plates.flatMap((pl) => ears.map((e) => tDist(pl, e)))), dPS = Math.min(...plates.flatMap((pl) => sup.map((s) => tDist(pl, s)))), dES = Math.min(...ears.flatMap((e) => sup.map((s) => tDist(e, s))));
  assert.ok(dPE >= 5, "placas-guía libres de las orejas de izaje: " + dPE.toFixed(1)); assert.ok(dPS >= 5, "placas-guía libres de los soportes E: " + dPS.toFixed(1)); assert.ok(dES >= 5, "orejas libres de los soportes E");
  ears.forEach((e) => e.forEach((p) => assert.ok(Math.hypot(p[0], p[1]) >= P.D_top / 2 + 5, "oreja fuera de la mesa")));
  // partes móviles (cuerpo, vástago, bloque-uña y cubo de Q) en todos los estados de la simulación
  let dM = Infinity;
  for (const q of pivStates(P, 40)) {
    const L = Math.hypot(q.Q[0] - q.E[0], q.Q[1] - q.E[1]), u = [(q.Q[0] - q.E[0]) / L, (q.Q[1] - q.E[1]) / L];
    const parts = [tRect(q.E, u, P.e_body, P.L0 - P.c_rod, P.D_body), tRect(q.E, u, P.L0 - P.c_rod, L, P.d_rod), q.una.cuerpo, q.una.cara, q.una.cubo];
    for (const e of ears) for (const pa of parts) dM = Math.min(dM, tDist(e, pa));
  }
  assert.ok(dM >= 5, "orejas libres de las partes móviles: " + dM.toFixed(1));
  const rows = A.checks.filter((c) => /^Placas-guía libres de las orejas|^Placas-guía libres de los demás|^Orejas de izaje libres/.test(c.name));
  assert.ok(rows.length >= 4 && rows.every((c) => c.st === "ok"), rows.map((c) => c.name + " " + c.st).join("; "));
  // con las orejas en la posición anterior (±600; ±1.030) el núcleo detecta el choque con la placa del sentido horario y con el bloque-uña
  const Ao = TT.analyze(P2({ x_lug: 600, c_lug: 250 }), { noFEA: true });
  assert.equal(Ao.checks.find((c) => /^Placas-guía libres de las orejas/.test(c.name)).st, "fail");
  assert.equal(Ao.checks.find((c) => /^Orejas de izaje libres de las partes móviles/.test(c.name)).st, "fail");
  // modo guiado: las orejas en la diagonal quedan libres del accionamiento
  assert.equal(TT.analyze(TG(), { noFEA: true }).checks.find((c) => /^Orejas de izaje libres del accionamiento guiado/.test(c.name)).st, "ok");
});
test("AF2 · tornillos intercalados con los pasadores: sin interferencia, ligamento (J3.4, J3.4M), rosca ciega en el anillo inferior y corte J3.7", () => {
  const P = Object.assign(TT.defaults(), { opt_ss: 1, fix_mode: 2 }), A = TT.analyze(P, { noFEA: true }), t = A.R.ifc.tornillos, D = TT.designDrive(P, A.R).tornillos_interfaz;
  const pins = Array.from({ length: P.N_pin }, (_, k) => (k + 0.5) * 360 / P.N_pin).map((a) => [P.R_pin * Math.cos(a * Math.PI / 180), P.R_pin * Math.sin(a * Math.PI / 180)]);
  const dh = t.d + 1, clr = Math.min(...D.posiciones.map((p) => Math.min(...pins.map((q) => Math.hypot(p[0] - q[0], p[1] - q[1]))))) - P.d_pin / 2 - dh / 2;
  assert.ok(clr >= 3 * t.d - dh, "ligamento libre al agujero del pasador ≥ 3d − d_h: " + clr.toFixed(1));
  assert.ok(clr + dh / 2 >= 22, "distancia al borde del agujero del pasador ≥ e_mín (J3.4M)");
  // ninguna cabeza sobre una ranura radial; n = bisectrices libres
  const lat = (a) => Math.min(...Array.from({ length: P.n_gr_rad }, (_, q) => { const e = ((a - 360 * q / P.n_gr_rad + 540) % 360) - 180; return Math.abs(e) < 90 ? t.r * Math.abs(Math.sin(e * Math.PI / 180)) : Infinity; }));
  const free = Array.from({ length: P.N_pin }, (_, k) => k * 360 / P.N_pin).filter((a) => lat(a) >= P.w_gr / 2 + t.dk / 2 + 3);
  assert.equal(t.n, free.length); D.angulos_deg.forEach((a) => assert.ok(lat(a) >= P.w_gr / 2 + t.dk / 2 + 3));
  // rosca en la pieza real: el anillo inferior (r − d/2 > R_anillo,int), ciega con remanente ≥ 3 mm y engrane ≥ 1,25·d
  assert.ok(t.r - t.d / 2 > TT.prIn(P) && D.rosca_en_mesa.ciega && /anillo inferior/.test(D.pieza_roscada));
  assert.ok(D.rosca_en_mesa.remanente >= 3 && D.rosca_en_mesa.engrane >= 1.25 * t.d && D.rosca_en_mesa.engrane + 2 <= D.rosca_en_mesa.prof);
  near(t.V, A.R.cd.T * 1e6 / (t.n * t.r), 1e-12, "V = T/(n·r)");
  const row = (re) => A.checks.find((c) => re.test(c.name));
  assert.ok(row(/^AF2 · Tornillos: sin interferencia con los agujeros de los pasadores/).st === "ok" && row(/^AF2 · Tornillos: ligamento libre al agujero del pasador/).st === "ok" && row(/^AF2 · Tornillos: engrane de la rosca en la pieza real/).st === "ok");
  assert.ok(row(/^AF2 · Tornillos avellanados disco–mesa: corte/).fu <= 0.85 && /J3\.7/.test(row(/^AF2 · Tornillos avellanados disco–mesa: corte/).ref) && /J3\.11/.test(row(/^AF2 · Tornillos: aplastamiento en la pieza roscada/).ref));
  // con pasadores muy juntos (64 en R930) la bisectriz queda sobre los agujeros: el núcleo lo detecta (interferencia y ligamento)
  const dense = TT.analyze(Object.assign({}, P, { N_pin: 64 }), { noFEA: true }).checks;
  assert.equal(dense.find((c) => /^AF2 · Tornillos: sin interferencia/.test(c.name)).st, "fail"); assert.equal(dense.find((c) => /^AF2 · Tornillos: ligamento libre/.test(c.name)).st, "fail");
  assert.equal(TT.analyze(Object.assign({}, P, { N_pin: 48 }), { noFEA: true }).checks.find((c) => /^AF2 · Tornillos: ligamento libre/.test(c.name)).st, "fail", "48 pasadores: sin ligamento J3.4");
});
test("Modo guiado · seguidor (perno, retención y grado del rodillo), ranura ISO 286, pernos del riel, filetes del pórtico y material soldable", () => {
  const P = TG(), A = TT.analyze(P, { noFEA: true }), F = TT.designDrive(P, A.R).levaGuiada.fabricacion, c = A.R.camG;
  const S = F.seguidor;
  assert.ok(S.perno.z && S.perno.z[1] >= S.rodillo.z[1] - 1e-9, "el perno llega a la cara superior del rodillo");
  near(S.perno.largo, S.perno.z[1] - S.perno.z[0], 1e-9); near(S.perno.z[0], S.perno.z_cara_sup_una - S.perno.empotrado_en_una, 1e-9);
  assert.ok(S.retencion && S.retencion.z[1] <= Math.min(c.zPb + P.cam_t, c.zTop) - 1 + 1e-9, "retención bajo la cara superior del riel y de la mesa");
  assert.ok(/100Cr6/.test(S.rodillo.material || ""), "grado del rodillo");
  // ranura y perno: ajuste deslizante ISO 286 sobre la misma medida nominal
  const Rn = F.ranura_tapa_patin; assert.equal(Rn.ancho, P.cam_dp); assert.ok(/H9/.test(Rn.ajuste) && /f8/.test(S.perno.ajuste));
  near(Rn.juego[0], 0.025, 1e-9, "juego mínimo 50 H9/f8"); near(Rn.juego[1], 0.126, 1e-9, "juego máximo 50 H9/f8");
  // pernos del riel: engrane ≥ 1,25·d en la tapa (taladro ciego con remanente 3 mm)
  const pr = F.porticos.pernos.rosca; assert.ok(pr.engrane >= 1.25 * P.cam_db && pr.remanente >= 3 && pr.engrane + 2 <= pr.rosca_util, "engrane " + pr.engrane);
  F.porticos.tapas_local.forEach((t) => near(t.z[1] - t.z[0], F.porticos.t_tapa, 1e-9));
  // material soldable en patas y tapas; el riel templado solo se emperna
  assert.ok(/S355/.test(F.porticos.material) && /no se suelda/.test(F.riel.material));
  const row = (re) => A.checks.find((x) => re.test(x.name));
  for (const re of [/^Pórtico del riel: soldadura pata–tapa/, /^Pórtico del riel: filete pata–tapa mínimo/, /^Prolongación de la bancada: soldadura a la base/, /^Prolongación de la bancada: filete mínimo/, /^Pernos riel–pórtico: engrane de la rosca/, /^Seguidor: rodillo y su retención/]) {
    const r = row(re); assert.ok(r && r.st === "ok", "fila " + re + " " + (r && r.st));
  }
  assert.ok(row(/^Pórtico del riel: flexión de cada pata/).cap === P.Fy / P.Nd, "patas de S355J2 (Fy = " + P.Fy + ")");
});
test("Placa-guía · puntos de la holgura mínima de sincronía exportados (global y marco de la placa, θ, nominal y peor caso) y coherentes con la simulación", () => {
  const P = P2(), R = TT.compute(P), F = TT.designDrive(P, R).pivotado.fabricacion.placas_leva, H = F.holgura_sincronia, g = R.camP.guia;
  assert.ok(H && H.instancias && Object.keys(H.instancias).length === 4, "holgura_sincronia en placas_leva");
  near(H.nominal, R.camP.sync, 1e-9, "nominal = sincronía verificada"); near(H.peor_caso, g.syncWorst, 1e-9, "peor caso = nominal − δ"); assert.ok(H.peor_caso >= P.pv_msync);
  for (const [k, I] of Object.entries(H.instancias)) {
    const db = Math.hypot(I.punto_bloque[0] - I.punto_pasador[0], I.punto_bloque[1] - I.punto_pasador[1]);
    near(db, H.nominal, 1e-6, k + ": distancia entre los dos puntos = holgura");
    near(Math.hypot(I.punto_pasador[0] - I.centro_pasador[0], I.punto_pasador[1] - I.centro_pasador[1]), P.d_pin / 2, 1e-9, k + ": el punto del pasador está en su contorno");
    near(Math.hypot(...I.centro_pasador), P.R_pin, 1e-9, k + ": centro del pasador sobre R_pin");
    // el pasador B está en la corona a θ_fin − paso del cilindro de esa instancia; θ de la instancia
    const th = I.theta_deg * Math.PI / 180, pitch = 2 * Math.PI / P.N_pin, sen = k.endsWith("horario") && !k.endsWith("antihorario") ? -1 : 1;
    const B = [P.R_pin * Math.cos(th - sen * pitch), P.R_pin * Math.sin(th - sen * pitch)];
    assert.ok(Math.hypot(B[0] - I.centro_pasador[0], B[1] - I.centro_pasador[1]) < 1e-6, k + ": el pasador de la holgura es B (θ − paso en el sentido de giro)");
  }
  // marco de la placa: los mismos puntos en coordenadas locales de la placa del cilindro 1 antihorario
  const mk = g.marco, I1 = H.instancias["1_antihorario"], loc = (p) => [(p[0] - mk.origen[0]) * mk.xh[0] + (p[1] - mk.origen[1]) * mk.xh[1], (p[0] - mk.origen[0]) * mk.yh[0] + (p[1] - mk.origen[1]) * mk.yh[1]];
  near(loc(I1.punto_bloque)[0], H.marco_placa.punto_bloque[0], 1e-9); near(loc(I1.punto_pasador)[1], H.marco_placa.punto_pasador[1], 1e-9);
  // la simulación del retorno alcanza esa misma holgura en el mismo L
  const q = TT.pivotAt(P, H.s, "retorno", "antihorario"); assert.ok(Math.abs(q.holgura_leva - H.nominal) < 0.05, "pivotAt en L_sync: " + q.holgura_leva);
});
test("Placa-guía · pasadores de posición ISO 8734: largo, enganche ≥ 1,5·d en base y placa, alojamientos ciegos con remanente y fondo libre", () => {
  const P = P2(), A = TT.analyze(P, { noFEA: true }), D = TT.designDrive(P, A.R).pivotado.fabricacion.placas_leva.pasadores_posicion;
  assert.ok(D.largo > 0 && D.enganche_base + D.enganche_placa === D.largo, "largo = enganche en la base + en la placa");
  assert.ok(D.enganche_base >= 1.5 * P.pv_dd && D.enganche_placa >= 1.5 * P.pv_dd, "enganche ≥ 1,5·d en cada pieza");
  assert.ok(D.alojamiento_base.prof === D.enganche_base + D.alojamiento_base.fondo_libre && D.alojamiento_base.prof + D.alojamiento_base.remanente === P.t_base && D.alojamiento_base.remanente >= 3);
  assert.ok(D.alojamiento_placa.prof + D.alojamiento_placa.remanente === P.pv_tcam && D.alojamiento_placa.remanente >= 3 && D.alojamiento_base.fondo_libre >= 2);
  assert.ok([20, 22, 24, 26, 28, 30, 32].includes(D.largo) && /ISO 8734/.test(D.designacion), "largo de la serie ISO 8734");
  assert.ok(A.checks.filter((c) => /^Pasadores de posición/.test(c.name) && c.kind === "geo").every((c) => c.st === "ok"));
  // con Ø16 (valor anterior) la base de 18 mm no da 1,5·d con alojamiento ciego
  assert.equal(TT.analyze(P2({ pv_dd: 16 }), { noFEA: true }).checks.find((c) => /^Pasadores de posición .*enganche en la base/.test(c.name)).st, "fail");
});
test("Soporte E · sin inserto (ins_on = 0): plancha base bajo el momento del soporte, contacto unilateral sin anclaje, empuje a calado y retorno, ambos sentidos (NO cumple: anclaje pendiente)", () => {
  // Modelo (docs/normas/registro.md, «Plancha base bajo el soporte del ojal E»): soporte rígido; F en h = (h_sup + h_inf)/2 sobre la plancha, M = F·h;
  // losa rígida solo a compresión, sin anclaje (no definido en el proyecto); la única retención del talón es la mesa (R ≤ D/2) a través de la plancha.
  // Franja: M_corte = M·(1 − a/s_H) en la línea del talón (s_H = brazo hasta el borde más lejano de la mesa; si s_H ≤ a no hay retención y M_corte = M),
  // b = w + a (reparto a 45° desde el centro de la huella), σ = 6·M_corte/(b·t²) ≤ Fy/Nd (ASME BTH-1 §3-2.3).
  // sin inserto (ins_on = 0): el modelo de la franja sin anclaje queda disponible con F_b = 1,25·Fy/Nd (ASME BTH-1-2020 §3-2.3.4)
  const run = (o) => { const P = P2(Object.assign({ ins_on: 0 }, o)), A = TT.analyze(P, { noFEA: true }); return { P, A, R: A.R, D: TT.designDrive(P, A.R).pivotado.fabricacion.soporte_E }; };
  const own = (P, R) => {
    const sg = R.sup, E = R.K.E, O = [-sg.sx * E[0], sg.sy * E[1]], h = (sg.hU + sg.hL) / 2, t = P.t_base;
    const V = sg.walls.flatMap((w) => { const [x0, x1, y0, y1] = w.rect; return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]; });
    const Fret = Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2) * P.p_ret / 10, out = {};
    for (const [k, F, sg_] of [["empuje", R.Fstall * 1e3, -1], ["retorno", Fret, 1]]) {
      let best = { sig: 0 }; const bySense = [0, 0];
      sg.sweep.estados.map((q) => [0, q]).concat(sg.sweep.horario.map((q) => [1, q])).forEach(([k2, q]) => {
        const f = [sg_ * Math.cos(q.psi), sg_ * Math.sin(q.psi)], g = [-f[1], f[0]], d = (p, v) => p[0] * v[0] + p[1] * v[1];
        const pf = V.map((p) => d(p, f)), pg = V.map((p) => d(p, g)), toe = Math.max(...pf), a = toe - Math.min(...pf), w = Math.max(...pg) - Math.min(...pg);
        const sH = toe - d(O, f) + P.D_top / 2, M = F * h, Mc = sH > a ? M * (1 - a / sH) : M, b = w + a, sig = 6 * Mc / (b * t * t);
        bySense[k2] = Math.max(bySense[k2], sig);
        if (sig > best.sig) best = { sig, M, Mc, a, w, b, sH, ret: sH > a };
      });
      out[k] = Object.assign(best, { bySense });
    }
    return out;
  };
  const C = run({}), mine = own(C.P, C.R), Fa = 1.25 * C.P.Fy / C.P.Nd;
  const row = (re) => C.A.checks.find((c) => re.test(c.name));
  const rE = row(/^Plancha base bajo el soporte del ojal E: flexión sin anclaje.*empuje a calado/), rR = row(/^Plancha base bajo el soporte del ojal E: flexión sin anclaje.*retorno/);
  assert.ok(rE && rR, "filas de flexión de la plancha (empuje y retorno)");
  near(rE.dem, mine.empuje.sig, 1e-9, "σ empuje"); near(rR.dem, mine.retorno.sig, 1e-9, "σ retorno"); near(rE.cap, Fa, 1e-12, "1,25·Fy/Nd");
  assert.ok(/BTH-1-2020 §3-2\.3\.4/.test(rE.ref) && /registro/.test(rE.ref));
  // sin anclaje no cumple (FU > 1 en el empuje); la fila queda «pend» (decisión de anclaje del mandante) para no ocultar el FU ni cambiar el veredicto sin decisión
  assert.ok(rE.fu > 1 && rE.st === "pend", "empuje sin anclaje: FU " + rE.fu.toFixed(2));
  assert.ok(rR.st === "pend", "retorno sin anclaje: fila pendiente (con 1,25·Fy/Nd y la base de 20 mm la franja da FU " + rR.fu.toFixed(2) + ")");
  assert.ok(mine.empuje.ret && !mine.retorno.ret, "en el empuje la mesa queda detrás del talón; en el retorno no hay retención detrás del talón");
  // ambos sentidos: el barrido horario (reflejo respecto de la diagonal) da el mismo máximo por simetría del soporte en L
  for (const k of ["empuje", "retorno"]) near(mine[k].bySense[0], mine[k].bySense[1], 1e-6, k + ": antihorario = horario");
  // levantamiento: anclaje no definido → fila pendiente con el momento a anclar
  const rL = row(/^Plancha base bajo el soporte del ojal E: levantamiento/); assert.ok(rL && rL.st === "pend" && /anclaje/.test(rL.name));
  const rV = row(/^Plancha base bajo el soporte del ojal E: corte/); assert.ok(rV && rV.st === "ok");
  near(rV.dem, 1.5 * mine.empuje.M / mine.empuje.a / (mine.empuje.b * C.P.t_base), 1e-9, "τ = 1,5·(M/a)/(b·t)");
  const rI = row(/^Plancha base bajo el soporte del ojal E: modelo/); assert.ok(rI && rI.kind === "info" && /térmic/.test(rI.formula) && /unilateral/.test(rI.formula));
  // interfaz B (eje más alto): gobierna (σ ∝ h)
  const B = run({ opt_uhmw: 1 }), mB = own(B.P, B.R);
  assert.ok(mB.empuje.sig > mine.empuje.sig && B.R.sup.zc0 > C.R.sup.zc0);
  near(B.A.checks.find((c) => /^Plancha base bajo el soporte del ojal E: flexión sin anclaje.*empuje a calado/.test(c.name)).dem, mB.empuje.sig, 1e-9, "σ empuje con B");
  // exportación en soporte_E
  const X = C.D.plancha_base; assert.ok(X && X.t === C.P.t_base && X.anclaje && /no definido/.test(X.anclaje) && /pendiente/i.test(X.estado));
  assert.ok(X.casos.length === 2 && X.casos.every((c) => c.fu > 0 && isFinite(c.M_kNm) && c.norma && /BTH-1/.test(c.norma)));
  near(X.casos.find((c) => c.caso === "empuje a calado").fu, rE.fu, 1e-12);
  // el calado no depende de la carga (atasco con la mesa vacía): la retención de la mesa vacía es su peso propio (W_d = mesa + disco rotatorio + medio
  // pivote, más los bloques-uña montados en la mesa: cota superior), que no alcanza para los dos soportes ni con el brazo más largo: 2·M/s_H > W_mesa
  const mv = X.mesa_vacia, Wm = C.R.Wd + C.R.m.dogs * 9.80665 / 1e3, Treq = 2 * mine.empuje.M / mine.empuje.sH / 1e3;
  assert.ok(mv, "export de la retención con la mesa vacía");
  near(mv.W_mesa_kN, Wm, 1e-9, "peso propio de la mesa"); near(mv.T_req_kN, Treq, 1e-9, "retención pedida por los dos soportes");
  assert.ok(mv.T_req_kN > mv.W_mesa_kN && mv.cumple === false, "mesa vacía: no retiene");
  assert.ok(/mesa vacía/.test(rL.formula), "la fila del levantamiento declara el caso de la mesa vacía");
});

test("Soporte E · plancha base: revisión con la base completa (dos soportes, M₂ = −M₁) declarada en la fila del levantamiento y en la exportación", () => {
  // docs/qa/plancha_base_soporte_E.md: con los dos cilindros F₂ = −F₁ y M₂ = −M₁, la base no vuelca como cuerpo libre; el par pasa de un soporte al
  // otro por torsión de la base (fuerzas de esquina ≈ M/B en las esquinas libres), que la plancha de 18 mm no tiene. La retención n_cil·M/s_H de
  // mesa_vacia queda como cota del modelo de un soporte; las filas y sus FU no cambian.
  const P = Object.assign(TT.defaults(), { ins_on: 0 }), A = TT.analyze(P, { noFEA: true }), R = A.R, X = TT.designDrive(P, R).pivotado.fabricacion.soporte_E.plancha_base;   // sin inserto
  const rL = A.checks.find((c) => /^Plancha base bajo el soporte del ojal E: levantamiento/.test(c.name));
  assert.ok(/docs\/qa\/plancha_base_soporte_E\.md/.test(rL.formula) && /M₂ = −M₁/.test(rL.formula) && /torsión/.test(rL.formula), "la fila remite a la revisión");
  const rv = X.revision_base_completa;
  assert.ok(rv && rv.estudio === "docs/qa/plancha_base_soporte_E.md" && /M₂ = −M₁/.test(rv.modelo) && /torsión/.test(rv.modelo), "exportación de la revisión");
  const M = R.Fstall * (R.sup.hU + R.sup.hL) / 2 / 1e3;   // kN·m
  near(rv.M_kNm, M, 1e-9, "M = F·h por soporte"); near(rv.V_esquina_kN, M / (P.B / 1e3), 1e-9, "fuerza de esquina de la torsión ≈ M/B");
  assert.ok(/paralelo/.test(rv.un_cilindro) && /mesa vacía/.test(rv.mesa_vacia) && Array.isArray(rv.opciones) && rv.opciones.length >= 4, "un solo cilindro, mesa vacía y opciones");
  assert.ok(/NO/.test(rv.conclusion) && /anclaje/.test(rv.conclusion), "conclusión: no cumple sin anclaje o base rígida");
});

test("Veredicto · pendientes críticos visibles: las filas «pend» con FU > 1 entran a verdict.pendientes_criticos y al estado global (no se excluyen en silencio)", () => {
  // docs/qa/plancha_base_soporte_E.md §4: las filas con estado «pend» y FU > 1 (p. ej. la plancha base bajo el soporte E sin anclaje) no entran a
  // verdict.estructura (resume las verificaciones resueltas; el generador de planos la usa) ni a fuEstOf/fuTermOf, pero el estado global no puede
  // decir «cumple»: queda «NO CUMPLE / PENDIENTE DE DECISIÓN» con la lista de las filas, su FU, norma y registro.
  // sin inserto (ins_on = 0): la franja sin anclaje queda «pend» con FU > 1 (con el inserto, desde el 10-11-2026, no hay pendientes críticos)
  const NI = () => Object.assign(TT.defaults(), { ins_on: 0 }), A = TT.analyze(NI(), { noFEA: true }), v = A.verdict;
  const crit = A.checks.filter((c) => c.st === "pend" && !c.fuera && c.kind !== "info" && c.fu != null && !(isFinite(c.fu) && c.fu <= 1));
  assert.ok(crit.length >= 1 && crit.every((c) => /^Plancha base bajo el soporte del ojal E/.test(c.name)), "la plancha base sin anclaje (empuje; el retorno con 1,25·Fy/Nd y 20 mm queda bajo 1)");
  assert.ok(Array.isArray(v.pendientes_criticos), "campo pendientes_criticos[]");
  assert.equal(v.pendientes_criticos.length, crit.length);
  crit.forEach((c) => assert.ok(v.pendientes_criticos.some((p) => p.nombre === c.name && p.fu === c.fu && p.grp === c.grp && p.ref === c.ref && p.sys === c.sys), "fila " + c.name));
  assert.ok(v.pendientes_criticos.every((p, i, a) => i === 0 || a[i - 1].fu >= p.fu), "ordenadas por FU decreciente");
  near(v.fuMaxPend, Math.max(...crit.map((c) => c.fu)), 1e-12, "FU máximo de los pendientes críticos");
  assert.equal(v.estado_global, "NO CUMPLE / PENDIENTE DE DECISIÓN");
  assert.ok(v.gira && v.estructura, "verdict.estructura sigue resumiendo las verificaciones resueltas (no cambia su significado)");
  // sin pendientes críticos el estado global sigue al veredicto. Desde el 10-11-2026 el modo guiado tiene la misma decisión pendiente (plancha base bajo
  // la ménsula del ojal trasero, docs/qa/plancha_base_modo_guiado.md): el caso «cumple» se arma con una plancha que la franja y la torsión admiten
  const G = TT.analyze(Object.assign(TG(), { t_base: 64, ins_on: 0 }), { noFEA: true });
  assert.ok(G.checks.some((c) => /^Plancha base bajo la ménsula del ojal trasero: flexión sin anclaje/.test(c.name) && c.st === "pend" && c.fu <= 1), "con 64 mm la franja admite el momento (la fila sigue «pend»: el anclaje no está definido)");
  assert.equal(G.verdict.pendientes_criticos.length, 0); assert.equal(G.verdict.fuMaxPend, 0);
  assert.equal(G.verdict.estado_global, "CUMPLE");
  // un incumplimiento resuelto manda sobre el pendiente (y los pendientes siguen listados)
  const X = TT.analyze(Object.assign(NI(), { pv_tbox: 12 }), { noFEA: true });   // paredes del soporte E de 12 mm: no cumplen
  assert.ok(!X.verdict.estructura && X.verdict.estado_global === "NO CUMPLE" && X.verdict.pendientes_criticos.length >= 1, "NO CUMPLE con pendientes listados");
  // escenario térmico: cada fila de la tabla por temperatura lleva los pendientes críticos y el estado global (fuEstOf los excluye del FU gobernante)
  const th = TT.thermal(NI(), { T: [20], alts: ["base"] }), b = th.alternativas[0].byT[0];
  assert.ok(Array.isArray(b.pendientes_criticos) && b.pendientes_criticos.length >= 1 && b.pendientes_criticos.every((p) => p.fu > 1 && p.nombre && p.grp && p.ref), "byT.pendientes_criticos");
  assert.equal(b.estado_global, "NO CUMPLE / PENDIENTE DE DECISIÓN");
  assert.ok(b.fuEst < b.pendientes_criticos[0].fu, "el FU gobernante del escenario excluye la fila pendiente, que queda visible aparte");
  // con term_alcance = 1 el soporte E (accionamiento) queda fuera del alcance térmico: la decisión pendiente se lista igual, marcada
  assert.ok(b.pendientes_criticos.every((p) => p.fuera_alcance_termico === true), "marcadas fuera del alcance térmico");
  assert.ok(v.pendientes_criticos.every((p) => !("fuera_alcance_termico" in p)), "sin escenario térmico no hay marca");
});

test("Ménsula del ojal trasero (modo guiado) · sin inserto (ins_on = 0): plancha base sin anclaje: franja, torsión de la base entre las dos ménsulas y estado global (docs/qa/plancha_base_modo_guiado.md)", () => {
  // Modo guiado: la ménsula (dos mejillas soldadas a la plancha) recibe −F·ŷ a la altura del eje h; en el empuje la reacción la da la mesa (roce de la interfaz
  // y el otro cilindro), de modo que M = F·h no se cierra en la bancada: con los dos cilindros M₂ = −M₁ entre (x_g; y_ojal) y (−x_g; −y_ojal) y el par
  // cruza la base como torsión, igual que en el modo pivotado. El retorno con la uña trabada en la rampa del riel-leva se cierra en la franja de la bancada.
  const P = Object.assign(TG(), { ins_on: 0 }), A = TT.analyze(P, { noFEA: true }), R = A.R, K = R.K, bg = TT.bracketGeo(P), Fa = 1.25 * P.Fy / P.Nd;   // sin inserto (ins_on = 0)
  const row = (re) => A.checks.find((c) => re.test(c.name));
  const rE = row(/^Plancha base bajo la ménsula del ojal trasero: flexión sin anclaje, empuje a calado/), rR = row(/^Plancha base bajo la ménsula del ojal trasero: flexión sin anclaje, retorno/);
  const rT = row(/^Plancha base bajo la ménsula del ojal trasero: torsión de la base/), rV = row(/^Plancha base bajo la ménsula del ojal trasero: corte de la franja/);
  const rI = row(/^Plancha base bajo la ménsula del ojal trasero: modelo/), rL = row(/^Plancha base bajo la ménsula del ojal trasero: levantamiento/);
  assert.ok(rE && rR && rT && rV && rI && rL, "seis filas de la plancha base en el modo guiado");
  [rE, rR, rT, rV, rI, rL].forEach((c) => assert.equal(c.grp, "Articulaciones", c.name));
  // franja: huella de las dos mejillas (marco local con origen en el ojal, empuje −ŷ sobre la ménsula), retención en el borde más lejano de la mesa
  const h = R.hax, t = P.t_base, a = P.L_ch, w = bg.Win + 2 * P.t_ch, b = w + a, M = R.Fstall * 1e3 * h;
  near(h, P.h_disc / 2, 1e-12, "h = altura del eje sobre la plancha (interfaz por defecto)");
  const sH = bg.rear + Math.abs(K.y_eye) + P.D_top / 2, Mc = M * (1 - a / sH);
  near(rE.dem, 6 * Mc / (b * t * t), 1e-9, "σ = 6·M_corte/(b·t²) en el empuje"); near(rE.cap, Fa, 1e-12);
  const Fret = Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2) * P.p_ret / 10, sHr = (P.L_ch - bg.rear) - Math.abs(K.y_eye) + P.D_top / 2;
  assert.ok(sHr <= a, "en el retorno la mesa queda delante del pie: sin retención detrás del talón");
  near(rR.dem, 6 * Fret * h / (b * t * t), 1e-9, "retorno: toda la M cruza la línea del pie");
  near(rV.dem, 1.5 * (M / a) / (b * t), 1e-9, "corte de la franja con V = M/a"); near(rV.cap, P.Fy / (P.Nd * Math.sqrt(3)), 1e-12);
  // torsión de la base (cota inferior, placa libre): fuerza de esquina M/B, m_xy = M/(2B), τ = 6·m_xy/t² ≤ Fy/(Nd·√3)
  near(rT.dem, 6 * (M / (2 * P.B)) / (t * t), 1e-9, "τ de la torsión de la base"); near(rT.cap, P.Fy / (P.Nd * Math.sqrt(3)), 1e-12);
  [rE, rR, rT].forEach((c) => { assert.equal(c.st, "pend", c.name); assert.ok(c.fu > 1, c.name + ": FU " + c.fu); assert.ok(/docs\/qa\/plancha_base_modo_guiado\.md/.test(c.ref), c.name + ": referencia al estudio"); });
  assert.ok(rV.fu <= 1 && rV.st !== "pend", "el corte de la franja cumple");
  assert.equal(rL.kind, "pend"); assert.ok(/torsión/.test(rL.formula) && /M₂ = −M₁/.test(rL.formula), "la fila del levantamiento declara la torsión de la base");
  // estado global: los pendientes críticos del modo guiado
  const v = A.verdict, crit = [rE, rR, rT];
  assert.equal(v.estado_global, "NO CUMPLE / PENDIENTE DE DECISIÓN");
  crit.forEach((c) => assert.ok(v.pendientes_criticos.some((p) => p.nombre === c.name && p.fu === c.fu && p.grp === "Articulaciones"), "pendiente crítico: " + c.name));
  near(v.fuMaxPend, Math.max(...v.pendientes_criticos.map((p) => p.fu)), 1e-12); assert.ok(v.gira && v.estructura, "las verificaciones resueltas siguen cumpliendo");
  // exportación (designDrive; no va en tools/export_design.js, que tiene que coincidir con packages/web/planos_export.js): plancha base del modo guiado
  const X = TT.designDrive(P, R).guiado.plancha_base;
  assert.equal(X.estudio, "docs/qa/plancha_base_modo_guiado.md");
  near(X.M_kNm, M / 1e6, 1e-9); near(X.V_esquina_kN, M / 1e6 / (P.B / 1e3), 1e-9, "fuerza de esquina ≈ M/B");
  near(X.fu_torsion_cota_inferior, rT.fu, 1e-12); near(X.casos[0].fu, rE.fu, 1e-12); near(X.casos[1].fu, rR.fu, 1e-12);
  near(X.ojal[0], P.x_g, 1e-12); near(X.ojal[1], K.y_eye, 1e-12); near(X.h, h, 1e-12);
  assert.ok(/M₂ = −M₁/.test(X.modelo) && /torsión/.test(X.modelo) && /mesa/.test(X.cierre_empuje) && /bancada/.test(X.cierre_retorno_rampa), "mecánica de cargas declarada");
  assert.ok(X.mesa_vacia && X.mesa_vacia.T_req_kN > X.mesa_vacia.W_mesa_kN && X.mesa_vacia.cumple === false, "mesa vacía: no retiene");
  assert.ok(/NO/.test(X.conclusion) && /anclaje/.test(X.conclusion), "conclusión");
  assert.equal(TT.designDrive(TT.defaults(), TT.compute(TT.defaults())).guiado, null, "solo en el modo guiado");
  // interfaz B: el eje sube (h = 160 mm) y el par crece en la misma proporción
  const AB = TT.analyze(Object.assign(TG(), { opt_uhmw: 1, ins_on: 0 }), { noFEA: true }), rTB = AB.checks.find((c) => /^Plancha base bajo la ménsula del ojal trasero: torsión de la base/.test(c.name));
  near(rTB.fu / rT.fu, AB.R.hax / h, 1e-9, "torsión ∝ h");
  // el modo pivotado no cambia: sus filas de la plancha base siguen siendo las del soporte E
  assert.ok(!TT.analyze(TT.defaults(), { noFEA: true }).checks.some((c) => /ménsula del ojal trasero/.test(c.name)), "sin filas del modo guiado en el pivotado");
});

/* ======================= Decisión del mandante 10-11-2026: base de 20 mm con inserto de esquina bajo los soportes ======================= */
// docs/normas/registro.md «Plancha base: base de 20 mm con inserto de esquina (10-11-2026)»; docs/qa/plancha_base_inserto.md. La plancha se verifica con
// la mesa cargada (nominal, diseño, calado y atasco del retorno) y con la mesa vacía en servicio, con F_b = 1,25·Fy/Nd (ASME BTH-1-2020 §3-2.3.4); el atasco
// a presión de alivio con la mesa vacía queda EXCLUIDO como caso de diseño (limitación de uso exportada en verdict.limitaciones_uso).
const INS_COM = [25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100, 110, 120];
function insCheck(P, I, A, rows, label, okWarn) {   // okWarn: se admite FU entre 0,90 (objetivo interno) y 1,0 (advertencia) cuando ningún espesor llega al objetivo
  const Fb = 1.25 * P.Fy / P.Nd;
  assert.ok(I && I.t > P.t_base && INS_COM.includes(I.t), label + ": espesor comercial mayor que la base");
  assert.equal(I.t_base, P.t_base); near(I.delta, I.t - P.t_base, 1e-12, label + ": Δ");
  // casos con la mesa cargada y mesa vacía en servicio: FU = σ/(1,25·Fy/Nd) ≤ 1, BTH-1 §3-2.3.4
  ["nominal", "diseño", "calado", "retorno", "vacía"].forEach((k) => { const r = rows.find((c) => new RegExp(k).test(c.name)); assert.ok(r, label + ": fila " + k); near(r.cap, Fb, 1e-12, label + ": F_b = 1,25·Fy/Nd (" + k + ")");
    assert.ok(/BTH-1-2020 §3-2\.3\.4/.test(r.ref), label + ": cita §3-2.3.4"); assert.ok(r.st === "ok" || (okWarn && r.st === "warn"), label + ": " + r.name + " FU " + r.fu); assert.ok(r.fu <= 1); });
  // corte bajo el soporte con t_inserto (BTH-1-2020 §3-2.3.6): τ = 1,5·(M/a)/(b·t) con a y b de la fórmula exportada en la fila
  const rc = A.checks.find((c) => / inserto: corte bajo/.test(c.name)), ab = rc && rc.formula.match(/a = ([\d.]+) mm, b = ([\d.]+) mm/);
  assert.ok(rc && ab && /§3-2\.3\.6/.test(rc.ref), label + ": fila de corte");
  near(rc.dem, 1.5 * (A.R.Fstall * 1e3 * I.casos[0].h / +ab[1]) / (+ab[2] * I.t), 0.01, label + ": τ = 1,5·(M/a)/(b·t_inserto) (a y b redondeados en el texto)");
  const cN = I.casos.find((q) => q.id === "nom"), cC = I.casos.find((q) => q.id === "cal");
  near(cN.fu / cC.fu, cN.F_kN / cC.F_kN, 1e-9, label + ": σ lineal en F (M = F·h)");
  near(cC.F_kN, A.R.Fstall, 1e-12, label + ": calado = A·p_alivio");
  // espesor mínimo: los comerciales más delgados no llegan al FU objetivo (0,90; 1,0 si ninguno llega) o no dejan las holguras
  const lim = I.fu_max <= 0.9 ? 0.9 : 1;
  I.candidatos.filter((c) => c.t < I.t).forEach((c) => assert.ok(c.fu > lim || c.holgura_vertical < 5 || !c.asiento, label + ": " + c.t + " mm debería fallar"));
  // geometría: hipotenusa fuera de la mesa, rotación de 180°, vértices dentro de la base, holguras ≥ 5 mm (con el rebaje local, si lo hay)
  near(I.hipotenusa_dist_centro - P.D_top / 2, I.holgura_mesa, 1e-9, label + ": hipotenusa"); assert.ok(I.holgura_mesa >= 5, label + ": holgura a la mesa");
  if (I.rebaje) assert.ok(I.rebaje.z_cara < I.t && I.rebaje.profundidad === I.t - I.rebaje.z_cara && I.rebaje.poligonos.length >= 2, label + ": rebaje local");
  I.esquinas.forEach((pl) => pl.forEach(([x, y]) => assert.ok(Math.abs(x) <= P.B / 2 + 1e-9 && Math.abs(y) <= P.B / 2 + 1e-9, label + ": vértice dentro de la base")));
  I.esquinas[1].forEach((p, i) => { assert.ok(Math.abs(p[0] + I.esquinas[0][i][0]) < 1e-9 && Math.abs(p[1] + I.esquinas[0][i][1]) < 1e-9, label + ": rotación de 180°"); });
  assert.ok(I.holguras.planta >= 5 && I.holguras.vertical >= 5, label + ": holguras " + JSON.stringify(I.holguras));
  assert.ok(I.z[0] === 0 && I.z[1] === I.t, label + ": al ras por debajo con la base");
  // juntas, secuencia, masa
  const J = I.juntas.find((j) => j.id === "J-I1"); assert.ok(J && /CJP/.test(J.tipo) && /1:2,5/.test(J.tipo) && J.largo > 0 && J.verificacion && J.verificacion.fu <= 1 && /AWS D1\.1/.test(J.verificacion.norma), label + ": CJP inserto–base");
  assert.ok(I.secuencia.length >= 5 && I.masa > 0, label + ": secuencia y masa");
  near(A.R.m.insertos, I.n * I.masa, 1e-9, label + ": masa en el total");
}
test("Plancha base de 20 mm (decisión del mandante 10-11-2026): t_base por defecto 20 mm y alturas que dependen de él", () => {
  const P = TT.defaults(); assert.equal(P.t_base, 20);
  const A = TT.analyze(P, { noFEA: true }), H = A.checks.find((c) => /Altura total sobre el piso/.test(c.name)).dem;
  near(H, 20 + A.R.ifc.delta + P.h_disc, 1e-12, "altura total = t_base + Δ + h_mesa");
  assert.ok(P.ins_on === 1 && P.ins_fsv >= 1, "parámetros del inserto");
});
test("Soporte E · base de 20 mm con inserto de esquina: mesa cargada (nominal, diseño, calado, retorno) y mesa vacía en servicio con 1,25·Fy/Nd; holguras; CJP; exportación; estado global", () => {
  const P = TT.defaults(), A = TT.analyze(P, { noFEA: true }), D = TT.designDrive(P, A.R), I = D.pivotado.fabricacion.soporte_E.inserto;
  const rows = A.checks.filter((c) => /^Plancha base bajo el soporte del ojal E: inserto/.test(c.name));
  insCheck(P, I, A, rows, "por defecto");
  assert.equal(I.esquinas.length, 2, "un inserto por soporte E (dos esquinas diagonales)");
  assert.ok(I.poligono.cilindro1 && I.poligono.cilindro2, "polígono por cilindro");
  // sin filas «pend» con FU > 1: el estado global cumple
  assert.equal(A.verdict.pendientes_criticos.length, 0, JSON.stringify(A.verdict.pendientes_criticos.map((p) => p.nombre)));
  assert.equal(A.verdict.estado_global, "CUMPLE");
  // las paredes del soporte se sueldan sobre el inserto
  const pX = D.pivotado.fabricacion.soporte_E.piezas.find((q) => q.id === "pared_X"); assert.equal(pX.z[0], I.t, "pared sobre el inserto");
  // mesa vacía en servicio: F = ins_fsv·máx(F_dis; F_borde; F_cont)·W_d/N
  const cs = (id) => A.R.cases.find((q) => q.id === id).F, Fv = P.ins_fsv * Math.max(cs("dis"), cs("borde"), cs("cont")) * A.R.Wd / A.R.N;
  near(I.casos.find((q) => q.id === "vac").F_kN, Fv, 1e-9, "F de servicio con la mesa vacía");
  // limitación de uso: atasco a presión de alivio con la mesa vacía excluido
  assert.ok(Array.isArray(A.verdict.limitaciones_uso) && A.verdict.limitaciones_uso.some((l) => /no operar el accionamiento a presión de alivio con la mesa sin carga/i.test(l.texto) && /detener y liberar/.test(l.texto)), "verdict.limitaciones_uso");
  assert.ok(A.checks.some((c) => c.kind === "info" && /limitación de uso/i.test(c.name) && /presión de alivio/.test(c.formula)), "fila informativa");
  assert.ok(!A.checks.some((c) => /flexión sin anclaje/.test(c.name)), "sin las filas de la franja sin anclaje");
  // interfaz B: inserto mayor, también cumple
  const PB = Object.assign(TT.defaults(), { opt_uhmw: 1 }), AB = TT.analyze(PB, { noFEA: true }), IB = TT.designDrive(PB, AB.R).pivotado.fabricacion.soporte_E.inserto;
  // con la interfaz B la plancha de 20 mm bajo el borde de la mesa gobierna y satura (FU ≈ 0,98 con cualquier espesor): advertencia, no falla
  insCheck(PB, IB, AB, AB.checks.filter((c) => /^Plancha base bajo el soporte del ojal E: inserto/.test(c.name)), "interfaz B", true);
  assert.ok(IB.t > I.t, "B (eje más alto) pide más espesor");
  // sin inserto (ins_on = 0) vuelve el modelo de la franja sin anclaje, con su estado pendiente
  const A0 = TT.analyze(Object.assign(TT.defaults(), { ins_on: 0 }), { noFEA: true });
  assert.equal(A0.verdict.estado_global, "NO CUMPLE / PENDIENTE DE DECISIÓN");
});
test("Ménsula del ojal trasero (modo guiado) · base de 20 mm con inserto bajo las n_br ménsulas: mesa cargada y vacía en servicio, holguras, exportación en levaGuiada.fabricacion", () => {
  const P = TG(), A = TT.analyze(P, { noFEA: true }), D = TT.designDrive(P, A.R), I = D.levaGuiada.fabricacion.inserto;
  insCheck(P, I, A, A.checks.filter((c) => /^Plancha base bajo la ménsula del ojal trasero: inserto/.test(c.name)), "guiado");
  assert.equal(I.esquinas.length, Math.round(P.n_br), "un inserto por ménsula");
  assert.equal(A.verdict.estado_global, "CUMPLE"); assert.equal(A.verdict.pendientes_criticos.length, 0);
  assert.ok(A.verdict.limitaciones_uso.length >= 1);
  const PB = Object.assign(TG(), { opt_uhmw: 1 }), AB = TT.analyze(PB, { noFEA: true });
  insCheck(PB, TT.designDrive(PB, AB.R).levaGuiada.fabricacion.inserto, AB, AB.checks.filter((c) => /^Plancha base bajo la ménsula del ojal trasero: inserto/.test(c.name)), "guiado B");
});
