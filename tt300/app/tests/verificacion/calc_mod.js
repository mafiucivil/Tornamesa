/* Modelo paramétrico TT300-B: parámetros, cálculo del accionamiento, verificaciones y modelos FEA. */
const G = 9.80665, RHO = 7.85e-6;

const PARAM_GROUPS = [
  { id: "carga", t: "Carga", items: [
    ["W_tf", "Capacidad nominal W", "tf", 300, 10],
    ["e", "Excentricidad del CG", "mm", 150, 10],
    ["phi_d", "Factor dinámico φd", "–", 1.10, 0.05],
    ["D_load", "Zona de carga (parrilla)", "mm Ø", 1600, 50],
  ]},
  { id: "disco", t: "Disco cajón", items: [
    ["D_disc", "Diámetro del disco", "mm", 2000, 50],
    ["t_top", "Plancha superior 4a", "mm", 30, 2],
    ["t_bot", "Plancha inferior 4b", "mm", 30, 2],
    ["gap", "Separación entre planchas", "mm", 100, 5],
    ["D_hub", "Cubo 4c, Ø exterior", "mm", 300, 10],
    ["D_bore", "Buje / contacto interior Ø", "mm", 190, 5],
    ["rings", "Almas 4d, radios (coma)", "mm", "300, 550, 735", null],
    ["t_ring", "Espesor almas 4d", "mm", 25, 1],
    ["N_rib", "N° nervios radiales 4e", "un", 12, 1],
    ["t_rib", "Espesor nervios 4e", "mm", 20, 1],
    ["R_rib", "Radio final nervios", "mm", 880, 10],
  ]},
  { id: "barras", t: "Barras de empuje 4f", items: [
    ["R_bar", "Radio de barras", "mm", 940, 5],
    ["D_bar", "Diámetro barra", "mm", 70, 2],
    ["N_bar", "N° de barras", "un", 36, 1],
    ["D_hole", "Agujero en planchas Ø", "mm", 71, 1],
    ["weld_S", "Bisel soldadura barra S", "mm", 15, 1],
  ]},
  { id: "friccion", t: "Interfaz de giro", items: [
    ["mu", "μ estático de diseño", "–", 0.20, 0.01],
    ["r_eff", "Radio efectivo de diseño", "m", 0.80, 0.01],
    ["mu_nom", "μ nominal (grasa limpia)", "–", 0.15, 0.01],
    ["mu_cont", "μ contaminado", "–", 0.25, 0.01],
    ["mu_dry", "μ acero seco", "–", 0.50, 0.05],
    ["q_lim", "Presión admisible contacto", "MPa", 10, 0.5],
  ]},
  { id: "act", t: "Accionamiento", items: [
    ["D_piston", "Ø émbolo (área efectiva)", "mm", 90, 1],
    ["D_rod", "Ø vástago (pandeo)", "mm", 63, 1],
    ["p_relief", "Presión de alivio", "bar", 700, 10],
    ["p_alarm", "Presión de alarma", "bar", 600, 10],
    ["stroke", "Carrera cilindro", "mm", 200, 5],
    ["free", "Recorrido libre", "mm", 36, 1],
    ["L0", "L0 entre ojales (retraído)", "mm", 450, 5],
    ["eye_off", "Barra → ojal vástago", "mm", 250, 5],
    ["X_cyl", "Eje cilindro / guía (x)", "mm", 1085, 5],
    ["Lg", "Separación reacciones guía", "mm", 250, 5],
    ["mu_g", "μ carro/guía", "–", 0.15, 0.01],
    ["eta_c", "Rendimiento sellos ηc", "–", 0.95, 0.01],
    ["mu_piv", "μ buje pivote", "–", 0.20, 0.01],
    ["H_frac", "Fuerza lateral pivote / W", "–", 0.05, 0.005],
  ]},
  { id: "trinq", t: "Trinquete y carro", items: [
    ["pawl_tip", "Punta trinquete (x)", "mm", 905, 5],
    ["pawl_L", "Largo trinquete", "mm", 245, 5],
    ["pawl_b", "Ancho trinquete (flexión)", "mm", 85, 1],
    ["pawl_h", "Alto trinquete", "mm", 90, 1],
    ["seat_R", "Radio asiento", "mm", 36, 1],
    ["shoe_x0", "Boca del carro (x)", "mm", 1020, 5],
    ["Fy_pawl", "Fy trinquete (34CrNiMo6+QT)", "MPa", 800, 10],
  ]},
  { id: "pasador", t: "Pasador, ménsula y guía", items: [
    ["D_pin", "Ø pasador", "mm", 70, 1],
    ["t_cheek", "Espesor mejilla", "mm", 40, 1],
    ["gap_cheek", "Luz entre mejillas", "mm", 80, 1],
    ["w_eye", "Ancho ojal", "mm", 70, 1],
    ["L_cheek", "Largo mejilla", "mm", 280, 5],
    ["h_axis", "Altura eje sobre base", "mm", 80, 1],
    ["Fy_pin", "Fy pasador/pivote (42CrMo4+QT)", "MPa", 650, 10],
    ["rail_w", "Ancho guía", "mm", 40, 1],
    ["rail_embed", "Empotramiento guía en ranura", "mm", 10, 1],
    ["rail_h", "Altura libre guía", "mm", 30, 1],
    ["L_brg", "Largo de apoyo por reacción", "mm", 150, 5],
  ]},
  { id: "pivote", t: "Pivote, buje y base", items: [
    ["D_piv", "Ø pivote", "mm", 150, 5],
    ["L_bush", "Largo buje", "mm", 100, 5],
    ["p_bush", "Presión admisible buje", "MPa", 30, 1],
    ["H_bush", "Fuerza lateral buje / W", "–", 0.055, 0.005],
    ["lev_piv", "Brazo flexión pivote", "mm", 50, 5],
    ["BX", "Placa base X", "mm", 2400, 50],
    ["BY", "Placa base Y", "mm", 2000, 50],
    ["t_base", "Espesor placa base", "mm", 80, 5],
  ]},
  { id: "mat", t: "Materiales y factores", items: [
    ["Fy", "Fy planchas (A572 Gr.50)", "MPa", 345, 5],
    ["FEXX", "FEXX electrodo", "MPa", 490, 10],
    ["E", "Módulo E", "MPa", 200000, 1000],
    ["nu", "Poisson ν", "–", 0.3, 0.01],
    ["Nd", "Factor Nd (ASME BTH-1)", "–", 2.0, 0.1],
  ]},
];

function defaults() {
  const P = {};
  for (const g of PARAM_GROUPS) for (const it of g.items) P[it[0]] = it[3];
  return P;
}
function parseRings(s) {
  return String(s).split(/[,; ]+/).map(Number).filter((x) => isFinite(x) && x > 0).sort((a, b) => a - b);
}

function discMass(P) {
  const TD = P.t_top + P.t_bot + P.gap, Rd = P.D_disc / 2, rh = P.D_hub / 2;
  const rings = parseRings(P.rings);
  const plateA = Math.PI * (Rd * Rd - rh * rh) - P.N_bar * Math.PI * (P.D_hole / 2) ** 2;
  const m = {};
  m.top = plateA * P.t_top * RHO;
  m.bot = plateA * P.t_bot * RHO;
  m.hub = RHO * Math.PI / 4 * (P.D_hub ** 2 * TD - P.D_bore ** 2 * P.L_bush - 160 ** 2 * Math.max(0, TD - P.L_bush) - (260 ** 2 - 160 ** 2) * 25);
  m.rings = rings.reduce((s, r) => s + 2 * Math.PI * r * P.t_ring * P.gap * RHO, 0);
  const crossed = rings.filter((r) => r < P.R_rib).length * P.t_ring;
  m.ribs = P.N_rib * P.t_rib * P.gap * Math.max(0, P.R_rib - rh - crossed) * RHO;
  m.bars = P.N_bar * Math.PI * P.D_bar ** 2 / 4 * TD * RHO;
  m.bush = 8.1;
  m.total = m.top + m.bot + m.hub + m.rings + m.ribs + m.bars + m.bush;
  return m;
}

function compute(P) {
  const R = { P };
  R.W = P.W_tf * G;                                   // kN
  R.TD = P.t_top + P.t_bot + P.gap;
  R.mass = discMass(P);
  R.Wd = R.mass.total * G / 1000;
  R.N = R.W + R.Wd;
  R.ND = P.phi_d * R.W + R.Wd;
  const Rc = P.D_disc / 2, Ri = P.D_bore / 2;
  R.Ac = Math.PI * (Rc * Rc - Ri * Ri);
  R.r_u = 2 / 3 * (Rc ** 3 - Ri ** 3) / (Rc ** 2 - Ri ** 2) / 1000;
  R.r_max = P.R_bar / 1000;
  R.r_eff = P.r_eff;
  R.th = Math.PI / P.N_bar;                           // media separación angular (rad)
  R.a = P.R_bar * Math.cos(R.th);                     // mm, brazo mínimo
  R.useful = 2 * P.R_bar * Math.sin(R.th);
  R.strokeReq = P.free + R.useful;
  R.Delta = P.X_cyl - R.a;
  R.Kguide = 1 + 2 * P.mu_g * R.Delta / P.Lg;
  R.K = R.Kguide / P.eta_c;
  R.A = Math.PI * P.D_piston ** 2 / 4;                 // mm²
  R.Fmax = R.A * P.p_relief / 10 / 1000;               // kN
  R.Falarm = R.A * P.p_alarm / 10 / 1000;
  R.Tpiv = P.mu_piv * P.H_frac * R.W * (P.D_piv / 2 / 1000);
  R.Ybrk = P.R_bar * Math.sin(R.th) + P.eye_off + P.L0 + P.free;
  const cs = (mu, r) => {
    const Tf = mu * R.N * r, T = Tf + R.Tpiv, Fb = T / (2 * R.a / 1000), Fc = R.K * Fb;
    const p = Fc * 1e3 / R.A * 10;
    return { mu, r, Tf, T, Fb, Fc, p, FS: R.Fmax / Fc, tf: Fc / G };
  };
  R.cs = cs;
  R.cases = [
    Object.assign(cs(P.mu_nom, R.r_u), { name: "Nominal – grasa grafitada limpia", key: "nom" }),
    Object.assign(cs(P.mu, R.r_eff), { name: "DISEÑO – μ límite sup., carga al borde", key: "dis" }),
    Object.assign(cs(P.mu_cont, R.r_eff), { name: "Contaminado – arena / película degradada", key: "con" }),
    Object.assign(cs(P.mu_dry, R.r_u), { name: "Sin lubricación (acero seco)", key: "dry" }),
  ];
  R.d = R.cases[1];
  R.muMax = (r, p) => ((R.A * p / 10 / 1000) / R.K * (2 * R.a / 1000) - R.Tpiv) / (R.N * r);
  // curva por carrera
  R.stroke = [];
  for (let i = 0; i <= 40; i++) {
    const t = -R.th + 2 * R.th * i / 40;
    const at = P.R_bar * Math.cos(t), Dt = P.X_cyl - at, Kt = (1 + 2 * P.mu_g * Dt / P.Lg) / P.eta_c;
    const s = P.free + P.R_bar * (Math.sin(t) + Math.sin(R.th));
    const row = { t: t * 180 / Math.PI, s };
    for (const c of R.cases.slice(0, 3)) { const Fb = c.T / (2 * at / 1000); row[c.key] = Kt * Fb; }
    R.stroke.push(row);
  }
  // desglose de la fuerza de diseño
  const d = R.d, a2 = 2 * R.a / 1000;
  R.breakdown = [
    ["Fricción interfaz μ·N·r", d.Tf / a2],
    ["Buje del pivote", R.Tpiv / a2],
    ["Fricción carro/guía", d.Fb * (R.Kguide - 1)],
    ["Sellos del cilindro", d.Fc - d.Fb * R.Kguide],
  ];
  // contacto
  R.q_avg = R.ND * 1e3 / R.Ac;
  R.q_max = R.q_avg * (1 + 4 * P.e * Rc / (Rc * Rc + Ri * Ri));
  R.q_top = P.phi_d * R.W * 1e3 / (Math.PI * (P.D_load / 2) ** 2);
  // suelo
  R.Wtot = R.W + (R.mass.total + 3070) * G / 1000;   // + base y accesorios ≈ 3,07 t
  R.g_avg = R.Wtot * 1e3 / (P.BX * P.BY);
  R.g_max = R.g_avg * (1 + 6 * P.e / P.BY);
  return R;
}

/* ---------- verificaciones (requieren resultados FEA opcionales) ---------- */
function verifs(R, fea) {
  const P = R.P, F = R.Fmax, Fy = P.Fy, rows = [];
  const add = (grp, el, dem, cap, unit, ref, formula, note) => rows.push({ grp, el, dem, cap, unit, fu: dem / cap, ref, formula, note });
  // accionamiento
  add("Accionamiento", "Fuerza de diseño vs capacidad del cilindro", R.d.Fc, R.Fmax, "kN", "Ec. (5) / 700 bar", "F_cil = K·T/(2a)  ≤  A·p_alivio");
  add("Accionamiento", "Presión de diseño vs alarma", R.d.p, P.p_alarm, "bar", "Criterio operación", "p = F_cil / A  ≤  p_alarma");
  rows[rows.length - 1].kind = "pass";
  add("Accionamiento", "Carrera requerida (libre + útil)", R.strokeReq, P.stroke, "mm", "Cinemática", "s = libre + 2·R_b·sin(180°/N_b)");
  rows[rows.length - 1].kind = "pass";
  // interfaz
  add("Interfaz", "Presión de contacto máx. (e)", R.q_max, P.q_lim, "MPa", "Criterio acero/acero lubricado", "q = N_D/A·(1 + 4eR/(R²+r²))");
  // disco (FEA)
  if (fea && fea.bot) {
    add("Disco (FEA)", "Plancha inf. 4b – σvm máx. (contacto q_max)", fea.bot.vmMax, 0.6 * Fy, "MPa", "AISC 360-22 F11 (elástico 0,6Fy)", "FEA Mindlin MITC4, sector 360°/N_nerv");
    add("Disco (FEA)", "Plancha sup. 4a – σvm máx. (carga en parrilla)", fea.top.vmMax, 0.6 * Fy, "MPa", "AISC 360-22 F11 (elástico 0,6Fy)", "FEA Mindlin MITC4, q = φd·W/A_parrilla");
    const rw = Math.max(fea.bot.ringMax, fea.top.ringMax);
    add("Disco (FEA)", "Almas 4d – compresión por reacción de línea", rw / P.t_ring, 0.6 * Fy, "MPa", "AISC 360-22 J10.2 / E3", "σ = r_línea / t_alma");
    const rb = Math.max(fea.bot.barMax, fea.top.barMax) * 1e3;
    add("Disco (FEA)", "Barra 4f – compresión axial (columna)", rb / (Math.PI * P.D_bar ** 2 / 4), 0.6 * Fy, "MPa", "AISC 360-22 E3", "σ = R_barra / A_barra");
  }
  // flexión global del cajón: anillo exterior fuera de la zona de carga
  const ov = Math.max(0, P.D_disc / 2 - P.D_load / 2), lever = R.TD - (P.t_top + P.t_bot) / 2;
  const Mov = R.q_max * ov * ov / 2, Sov = Math.min(P.t_top, P.t_bot) * lever;
  add("Disco", "Flexión global del cajón en el anillo exterior (voladizo)", Mov / Sov, 0.6 * Fy, "MPa", "AISC 360-22 F11 (elástico)", "M = q_max·(R − R_carga)²/2; S = t·(TD − t)");
  // barra 4f
  const L = P.gap, c = Math.min(P.pawl_h, P.gap), d = P.D_bar;
  const Mss = F / 4 * (L - c / 2) / 1e3, Mfe = F * (3 * L * L - c * c) / (24 * L) / 1e3;
  const Mn = Fy * d ** 3 / 6 / 1.67 / 1e6;
  add("Barra 4f", "Flexión (rotulada, F calado)", Mss, Mn, "kN·m", "AISC 360-22 F11.1, Ω = 1,67", "M = F/4·(L − c/2); Mn = Fy·d³/6");
  const tau = 4 * (F / 2) * 1e3 / (3 * Math.PI * d * d / 4);
  add("Barra 4f", "Corte", tau, 0.6 * Fy / 1.5, "MPa", "AISC 360-22 G1, Ω = 1,50", "τ = 4V/(3A), V = F/2");
  const Ew = P.weld_S - 3, tv = (F / 2) * 1e3 / (Math.PI * d * Ew), tm = Mfe * 1e6 / (Math.PI * (d / 2) ** 2 * Ew);
  add("Barra 4f", `Soldadura bisel ${P.weld_S} (E = ${Ew})`, Math.hypot(tv, tm), 0.6 * P.FEXX / 2, "MPa", "AISC 360-22 J2.5, Ω = 2,0", "√(τV² + τM²); M empotrada = F(3L²−c²)/(24L)");
  add("Barra 4f", "Aplastamiento en agujero de plancha", (F / 2) * 1e3 / (Math.min(P.t_top, P.t_bot) * d), 0.9 * Fy, "MPa", "AISC 360-22 J7, Ω = 2,0", "σ = (F/2)/(t·d)");
  // trinquete
  const lev = P.shoe_x0 - R.a;
  const sp = F * lev * 1e3 / (P.pawl_h * P.pawl_b ** 2 / 6);
  add("Trinquete", "Flexión en boca del carro (teoría de vigas)", sp, P.Fy_pawl / P.Nd, "MPa", "ASME BTH-1 (Fy/Nd)", "σ = F·(x_boca − a)/(h·b²/6)");
  if (fea && fea.pawl) add("Trinquete", "Flexión en boca (FEA tensión plana)", fea.pawl.vmMouth, P.Fy_pawl / P.Nd, "MPa", "ASME BTH-1 (Fy/Nd)", "FEA Q4, h_malla 2,5 mm");
  // guía
  const Rg = F * R.Delta / P.Lg;
  add("Guía 22", "Aplastamiento en ranura", Rg * 1e3 / (P.rail_embed * P.L_brg), 0.9 * Fy, "MPa", "AISC 360-22 J7, Ω = 2,0", "R = F·Δ/Lg; σ = R/(e·L)");
  const Mg = Rg * P.rail_h / 2 / 1e3, Mng = Fy * P.L_brg * P.rail_w ** 2 / 4 / 1.67 / 1e6;
  add("Guía 22", "Flexión en raíz", Mg, Mng, "kN·m", "AISC 360-22 F11.1, Ω = 1,67", "M = R·h/2");
  // ménsula y pasador
  add("Ménsula 2", "Flexión de mejillas en la base", F * P.h_axis * 1e3 / (2 * P.t_cheek * P.L_cheek ** 2 / 6), 0.6 * Fy, "MPa", "AISC 360-22 F11 / CJP J2", "σ = F·h/(2·t·L²/6)");
  const Mpin = F / 2 * (P.t_cheek / 2 + (P.gap_cheek - P.w_eye) / 2 + P.w_eye / 4) / 1e3;
  add("Pasador 12", "Flexión (horquilla)", Mpin * 1e6 / (Math.PI * P.D_pin ** 3 / 32), P.Fy_pin / P.Nd, "MPa", "ASME BTH-1 (Fy/Nd)", "M = F/2·(t/2 + g + b/4)");
  add("Pasador 12", "Corte doble", (F / 2) * 1e3 / (Math.PI * P.D_pin ** 2 / 4), P.Fy_pin / (P.Nd * Math.sqrt(3)), "MPa", "ASME BTH-1 3-2.2", "τ = (F/2)/A ≤ Fy/(Nd·√3)");
  // pivote
  const H = P.H_bush * R.W;
  add("Pivote", "Presión en buje (H)", H * 1e3 / (P.D_piv * P.L_bush), P.p_bush, "MPa", "Fabricante bronce-grafito", "p = H/(D·L)");
  add("Pivote", "Flexión del pivote", H * P.lev_piv * 1e3 / (Math.PI * P.D_piv ** 3 / 32), P.Fy_pin / P.Nd, "MPa", "Fy/Nd", "σ = H·e/(πD³/32)");
  // vástago
  const I = Math.PI * P.D_rod ** 4 / 64, Lc = P.L0 + P.stroke, Pcr = Math.PI ** 2 * P.E * I / Lc ** 2 / 1e3;
  add("Cilindro", "Pandeo del vástago (rótulas)", F, Pcr / 3, "kN", "Euler, FS = 3", "Pcr = π²EI/L², L = L0 + carrera");
  // suelo
  add("Apoyo", "Presión bajo placa base (máx.)", R.g_max, 1.0, "MPa", "Referencial – verificar losa", "σ = N/A·(1 + 6e/B)", "Capacidad referencial");
  rows[rows.length - 1].kind = "pass";
  R.extra = { Mss, Mfe, lev, Rg, Mpin, H, Pcr, Ew, tv, tm };
  return rows;
}

/* ---------- FEA del disco: sector entre nervios ---------- */
function linspaceKeys(keys, h) {
  const out = [keys[0]];
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1], b = keys[i], n = Math.max(1, Math.ceil((b - a) / h));
    for (let k = 1; k <= n; k++) out.push(a + (b - a) * k / n);
  }
  return out;
}
function uniqSorted(arr, tol) {
  const s = arr.slice().sort((a, b) => a - b), o = [];
  for (const v of s) if (!o.length || v - o[o.length - 1] > tol) o.push(v);
  return o;
}
function discModel(P, which, hr, dth) {
  const alpha = 2 * Math.PI / P.N_rib, r0 = P.D_hub / 2, Rd = P.D_disc / 2;
  hr = hr || Math.max(20, (Rd - r0) / 45);
  const rings = parseRings(P.rings).filter((r) => r > r0 && r < Rd);
  const keyR = uniqSorted([r0, ...rings, P.R_rib, P.R_bar - P.D_bar / 2, P.R_bar, P.R_bar + P.D_bar / 2, Rd, which === "top" ? P.D_load / 2 : r0]
    .filter((r) => r >= r0 && r <= Rd), 2);
  const rs = linspaceKeys(keyR, hr);
  const barAng = [];
  for (let k = 0; k < P.N_bar; k++) {
    let a = Math.PI / P.N_bar + 2 * Math.PI * k / P.N_bar;
    if (a >= -1e-9 && a <= alpha + 1e-9) barAng.push(a);
  }
  const db = (P.D_bar / 2) / P.R_bar;
  const keyT = uniqSorted([0, alpha, ...barAng, ...barAng.map((a) => a - db), ...barAng.map((a) => a + db)].filter((a) => a >= 0 && a <= alpha), 1e-4);
  const ts = linspaceKeys(keyT, dth || Math.max(1.25 * Math.PI / 180, alpha / 36));
  const nT = ts.length, nodes = [], elems = [], pol = [];
  for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) { nodes.push([rs[i] * Math.cos(ts[j]), rs[i] * Math.sin(ts[j])]); pol.push([rs[i], ts[j]]); }
  const id = (i, j) => i * nT + j;
  const q = [], t = which === "top" ? P.t_top : P.t_bot;
  const R = compute(P);
  for (let i = 0; i < rs.length - 1; i++) for (let j = 0; j < nT - 1; j++) {
    elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
    const rc = (rs[i] + rs[i + 1]) / 2;
    q.push(which === "top" ? (rc <= P.D_load / 2 ? R.q_top : 0) : R.q_max);
  }
  const wFix = new Set(), clamp = [], betaN = [], groups = { ring: rings.map(() => []), rib: [], bar: barAng.map(() => []), hub: [] };
  const near = (a, b, tol) => Math.abs(a - b) < tol;
  for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) {
    const k = id(i, j), r = rs[i], th = ts[j];
    if (i === 0) { clamp.push(k); groups.hub.push(k); continue; }
    rings.forEach((rr, ri) => { if (near(r, rr, 0.5)) { wFix.add(k); groups.ring[ri].push(k); } });
    if ((j === 0 || j === nT - 1) && r <= P.R_rib + 0.5) { if (!wFix.has(k)) groups.rib.push(k); wFix.add(k); }
    barAng.forEach((ba, bi) => {
      const x = r * Math.cos(th) - P.R_bar * Math.cos(ba), y = r * Math.sin(th) - P.R_bar * Math.sin(ba);
      if (Math.hypot(x, y) <= P.D_bar / 2 + 0.5) { if (!wFix.has(k)) groups.bar[bi].push(k); wFix.add(k); }
    });
    if (j === 0) betaN.push([k, 0, 1]);
    if (j === nT - 1) betaN.push([k, -Math.sin(alpha), Math.cos(alpha)]);
  }
  return { nodes, pol, elems, q: Float64Array.from(q), t, E: P.E, nu: P.nu, wFix: [...wFix], clamp, betaN, groups, rings, barAng, alpha, rs, ts, which };
}
function runDisc(P, which, hr, dth) {
  const m = discModel(P, which, hr, dth);
  const t0 = performance.now();
  const r = FEA.plate(m);
  const ms = performance.now() - t0;
  let vmMax = 0, vmC = 0, imax = 0;
  r.el.forEach((e, i) => { if (e.vmGauss > vmMax) { vmMax = e.vmGauss; imax = i; } vmC = Math.max(vmC, e.vm); });
  let wMax = 0; for (const w of r.w) wMax = Math.max(wMax, Math.abs(w));
  const sumR = (arr) => arr.reduce((s, k) => s + Math.abs(r.reac[k]), 0);
  const ringLine = m.rings.map((rr, i) => sumR(m.groups.ring[i]) / (rr * m.alpha));   // N/mm
  const barF = m.groups.bar.map((g) => sumR(g) / 1e3);                                 // kN
  const ribF = sumR(m.groups.rib) / 1e3, hubF = sumR(m.groups.hub) / 1e3;
  const ec = m.elems[imax].map((k) => m.nodes[k]);
  const cx = ec.reduce((s, p) => s + p[0], 0) / 4, cy = ec.reduce((s, p) => s + p[1], 0) / 4;
  return {
    model: m, res: r, ms, vmMax, vmC, wMax, ringLine, barF, ribF, hubF,
    ringMax: Math.max(0, ...ringLine), barMax: Math.max(0, ...barF),
    Fapp: r.Fapplied / 1e3, Rsum: Math.abs(r.Rsum) / 1e3, maxAt: [Math.hypot(cx, cy), Math.atan2(cy, cx) * 180 / Math.PI],
  };
}

/* ---------- FEA del trinquete: tensión plana ---------- */
function runPawl(P, R) {
  const h = P._h || 2.5, L = P.pawl_L, b = P.pawl_b;
  const nx = Math.round(L / h), ny = Math.round(b / h), hx = L / nx, hy = b / ny;
  const Xs = R.a - P.pawl_tip, Ys = b, Rs = P.seat_R, Xm = P.shoe_x0 - P.pawl_tip;
  const nodes = [], elems = [], cent = [];
  for (let i = 0; i <= nx; i++) for (let j = 0; j <= ny; j++) nodes.push([i * hx, j * hy]);
  const id = (i, j) => i * (ny + 1) + j;
  const wx = 60 * (b / 85), wy = 36 * (b / 85);
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
    const cx = (i + 0.5) * hx, cy = (j + 0.5) * hy;
    if (Math.hypot(cx - Xs, cy - Ys) < Rs) continue;
    if (cx / wx + cy / wy < 1) continue;
    elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]); cent.push([cx, cy]);
  }
  const used = new Set(); elems.forEach((e) => e.forEach((k) => used.add(k)));
  const fix = [], sup = [];
  for (let i = 0; i <= nx; i++) {
    const x = i * hx;
    if (x >= Xm - 1e-6 && x <= Xm + 25) { fix.push([id(i, 0), 1]); sup.push(id(i, 0)); }
    if (x >= L - 25 - 1e-6) { fix.push([id(i, ny), 1]); sup.push(id(i, ny)); }
  }
  fix.push([id(nx, Math.round(ny / 2)), 0]);
  const F = R.Fmax * 1e3, cand = [];
  for (const k of used) {
    const [x, y] = nodes[k], d = Math.hypot(x - Xs, y - Ys);
    if (d >= Rs - 0.01 && d <= Rs + 1.6 * h) {
      const ph = Math.atan2(y - Ys, x - Xs);
      const w = Math.cos(ph + Math.PI / 2);   // máximo en φ = −90°
      if (w > 0.05 && y < Ys) cand.push([k, ph, w]);
    }
  }
  // un nodo por dirección: conservar el más cercano al arco por sector angular de 3°
  const bins = new Map();
  for (const c of cand) {
    const key = Math.round(c[1] * 180 / Math.PI / 3);
    const d = Math.hypot(nodes[c[0]][0] - Xs, nodes[c[0]][1] - Ys);
    if (!bins.has(key) || d < bins.get(key).d) bins.set(key, { c, d });
  }
  const ld = [...bins.values()].map((v) => v.c);
  const sw = ld.reduce((s, [, , w]) => s + w, 0);
  const loads = ld.map(([k, , w]) => [k, 0, -F * w / sw]);
  const t0 = performance.now();
  const r = FEA.planeStress({ nodes, elems, t: P.pawl_h, E: P.E, nu: P.nu, fix, loads });
  const ms = performance.now() - t0;
  let vmMax = 0, vmMouth = 0, vmFar = 0;
  const loadSet = new Set(ld.map((l) => l[0])), supSet = new Set(sup);
  r.el.forEach((e, i) => {
    vmMax = Math.max(vmMax, e.vm);
    const [cx, cy] = cent[i];
    if (Math.abs(cx - Xm) <= hx && cy > b / 2) vmMouth = Math.max(vmMouth, e.vm);
    const nearLoad = Math.hypot(cx - Xs, cy - Ys) < Rs + 4 * h;
    const nearSup = sup.some((k) => Math.hypot(cx - nodes[k][0], cy - nodes[k][1]) < 4 * h);
    if (!nearLoad && !nearSup) vmFar = Math.max(vmFar, e.vm);
  });
  let dmax = 0; for (let k = 0; k < nodes.length; k++) if (used.has(k)) dmax = Math.max(dmax, Math.hypot(r.u[2 * k], r.u[2 * k + 1]));
  const beam = F * (Xm - Xs) / (P.pawl_h * b * b / 6);
  return { nodes, elems, cent, res: r, ms, vmMax, vmMouth, vmFar, dmax, beam, Xs, Ys, Rs, Xm, L, b, loads, sup, nx, ny };
}

if (typeof module !== "undefined") module.exports = { PARAM_GROUPS, defaults, compute, verifs, discModel, runDisc, runPawl, parseRings };
