/* Plano paramétrico (SVG / DXF / PDF) y memoria de verificación (PDF). Coordenadas de papel en mm, y hacia arriba. */
const LAYERS = {
  VIS: { w: 0.5, dash: null, color: 7 }, FINA: { w: 0.18, dash: null, color: 8 }, EJE: { w: 0.18, dash: [10, 2, 1.5, 2], color: 1 },
  OCU: { w: 0.25, dash: [3, 1.5], color: 3 }, COTA: { w: 0.18, dash: null, color: 4 }, TXT: { w: 0.25, dash: null, color: 7 },
  MARCO: { w: 0.7, dash: null, color: 7 }, FUERZA: { w: 0.5, dash: null, color: 1 },
};
function Sheet() { this.it = []; }
Sheet.prototype = {
  L(x1, y1, x2, y2, ly = "VIS") { this.it.push({ k: "L", x1, y1, x2, y2, ly }); },
  R(x0, y0, x1, y1, ly = "VIS") { this.L(x0, y0, x1, y0, ly); this.L(x1, y0, x1, y1, ly); this.L(x1, y1, x0, y1, ly); this.L(x0, y1, x0, y0, ly); },
  P(pts, closed, ly = "VIS") { for (let i = 0; i < pts.length - 1; i++) this.L(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], ly); if (closed) this.L(pts[pts.length - 1][0], pts[pts.length - 1][1], pts[0][0], pts[0][1], ly); },
  C(x, y, r, ly = "VIS") { this.it.push({ k: "C", x, y, r, ly }); },
  A(x, y, r, a0, a1, ly = "VIS") { this.it.push({ k: "A", x, y, r, a0, a1, ly }); },
  T(s, x, y, h = 2.5, al = "l", ly = "TXT", bold = false) { this.it.push({ k: "T", s: String(s), x, y, h, al, ly, bold }); },
  S(pts, ly = "COTA") { this.it.push({ k: "S", pts, ly }); },
  arrow(x, y, ang, size = 2.6, ly = "COTA") {
    const w = size * 0.33, bx = x - size * Math.cos(ang), by = y - size * Math.sin(ang);
    this.S([[x, y], [bx + w * Math.sin(ang), by - w * Math.cos(ang)], [bx - w * Math.sin(ang), by + w * Math.cos(ang)]], ly);
  },
  force(x1, y1, x2, y2, label, h = 2.4) {
    this.L(x1, y1, x2, y2, "FUERZA"); this.arrow(x2, y2, Math.atan2(y2 - y1, x2 - x1), 4, "FUERZA");
    if (label) this.T(label, x1 + 1.5, y1 + (y1 > y2 ? 1.5 : -4), h, "l", "TXT", true);
  },
  dim(x1, y1, x2, y2, off, txt, orient = "h", h = 2.3) {
    if (orient === "h") {
      const y = y1 + off; this.L(x1, y1, x1, y + Math.sign(off) * 1.5, "COTA"); this.L(x2, y2, x2, y + Math.sign(off) * 1.5, "COTA");
      this.L(x1, y, x2, y, "COTA"); this.arrow(x1, y, Math.PI); this.arrow(x2, y, 0); this.T(txt, (x1 + x2) / 2, y + 0.8, h, "c", "COTA");
    } else {
      const x = x1 + off; this.L(x1, y1, x + Math.sign(off) * 1.5, y1, "COTA"); this.L(x2, y2, x + Math.sign(off) * 1.5, y2, "COTA");
      this.L(x, y1, x, y2, "COTA"); this.arrow(x, y1, y1 < y2 ? -Math.PI / 2 : Math.PI / 2); this.arrow(x, y2, y2 > y1 ? Math.PI / 2 : -Math.PI / 2);
      this.it.push({ k: "T", s: txt, x: x - 0.8, y: (y1 + y2) / 2, h, al: "c", ly: "COTA", rot: 90 });
    }
  },
  table(x0, y0, cols, rows, rh = 4.2, h = 2.0) {
    const Wt = cols.reduce((s, c) => s + c[1], 0); let y = y0;
    const all = [cols.map((c) => c[0])].concat(rows);
    all.forEach((row, i) => {
      this.L(x0, y, x0 + Wt, y, i <= 1 ? "VIS" : "FINA"); let x = x0;
      row.forEach((cell, j) => {
        const al = i === 0 ? "c" : cols[j][2];
        const tx = al === "c" ? x + cols[j][1] / 2 : al === "r" ? x + cols[j][1] - 1 : x + 1;
        this.T(cell, tx, y - rh + (rh - h) / 2 + 0.2, h, al, "TXT", i === 0); x += cols[j][1];
      });
      y -= rh;
    });
    this.L(x0, y, x0 + Wt, y, "VIS"); let x = x0;
    for (const c of cols.concat([[0, 0]])) { this.L(x, y0, x, y, x === x0 || x >= x0 + Wt - 0.01 ? "VIS" : "FINA"); x += c[1]; }
    return y;
  },
};

function buildSheet(R, V, fea) {
  const P = R.P, S = new Sheet(), W = 841, H = 594;
  S.R(0, 0, W, H, "FINA"); S.R(20, 10, W - 10, H - 10, "MARCO");
  // rótulo
  const x0 = W - 190, y1 = 72;
  S.R(x0, 10, W - 10, y1, "MARCO");
  [20, 30, 44].forEach((yy) => S.L(x0, 10 + yy - 10, W - 10, 10 + yy - 10, "FINA"));
  S.L(x0 + 60, 10, x0 + 60, 30, "FINA"); S.L(x0 + 120, 10, x0 + 120, 30, "FINA");
  S.T("PROYECTO: TORNAMESA HIDRÁULICA " + nf(P.W_tf) + " tf", x0 + 2, y1 - 5, 3.2, "l", "TXT", true);
  S.T("SOLUCIÓN B – ACERO-ACERO CON GRASA GRAFITADA", x0 + 2, y1 - 10.5, 2.4);
  S.T("PLANO DE VERIFICACIÓN PARAMÉTRICO", x0 + 2, y1 - 19, 3.6, "l", "TXT", true);
  S.T("Generado desde la herramienta de verificación con los parámetros indicados.", x0 + 2, 31.5, 2.0);
  const today = new Date().toLocaleDateString("es-CL");
  [["ESCALA", "INDICADA", 0, 1], ["FECHA", today, 1, 1], ["FORMATO", "A1", 2, 1], ["PLANO N°", "TT300-B-P-01", 0, 0], ["LÁMINA", "1 de 1", 1, 0], ["REV.", "P", 2, 0]]
    .forEach(([l, v, c, r]) => { S.T(l, x0 + c * 60 + 1.5, 10 + r * 10 + 7.2, 1.8); S.T(v, x0 + c * 60 + 30, 10 + r * 10 + 2.2, r === 0 ? 3.0 : 2.6, "c", "TXT", r === 0); });

  // ---- VISTA 1: planta 1:10 ----
  const k1 = 0.1, cx = 195, cy = 420, X = (x) => cx + x * k1, Y = (y) => cy + y * k1;
  S.R(X(-P.BX / 2), Y(-P.BY / 2), X(P.BX / 2), Y(P.BY / 2));
  S.C(cx, cy, P.D_disc / 2 * k1);
  parseRings(P.rings).forEach((r) => S.C(cx, cy, r * k1, "OCU"));
  for (let i = 0; i < P.N_rib; i++) { const a = 2 * Math.PI * i / P.N_rib; S.L(X(P.D_hub / 2 * Math.cos(a)), Y(P.D_hub / 2 * Math.sin(a)), X(P.R_rib * Math.cos(a)), Y(P.R_rib * Math.sin(a)), "OCU"); }
  for (let i = 0; i < P.N_bar; i++) { const a = Math.PI / P.N_bar + 2 * Math.PI * i / P.N_bar; S.C(X(P.R_bar * Math.cos(a)), Y(P.R_bar * Math.sin(a)), P.D_bar / 2 * k1); }
  S.C(cx, cy, P.D_hub / 2 * k1); S.C(cx, cy, P.D_piv / 2 * k1, "FINA");
  S.L(X(-P.BX / 2 - 30), cy, X(P.BX / 2 + 30), cy, "EJE"); S.L(cx, Y(-P.BY / 2 - 30), cx, Y(P.BY / 2 + 30), "EJE");
  for (const sx of [1, -1]) {
    const yb = -sx * P.R_bar * Math.sin(R.th), yE = yb - sx * P.eye_off, yP = -sx * R.Ybrk;
    S.R(X(sx * P.X_cyl - P.rail_w / 2), Y(-425), X(sx * P.X_cyl + P.rail_w / 2), Y(425), "OCU");
    S.R(X(sx * P.X_cyl - P.gap_cheek / 2 - P.t_cheek), Y(yP - P.L_cheek / 2), X(sx * P.X_cyl + P.gap_cheek / 2 + P.t_cheek), Y(yP + P.L_cheek / 2));
    S.R(X(sx * P.X_cyl - 70), Y(yP + sx * 70), X(sx * P.X_cyl + 70), Y(yP + sx * 370));
    S.R(X(sx * P.X_cyl - P.D_rod / 2), Y(yP + sx * 370), X(sx * P.X_cyl + P.D_rod / 2), Y(yE));
    S.R(X(sx * P.shoe_x0), Y(yb + sx * 20), X(sx * (P.shoe_x0 + 130)), Y(yb + sx * 20 - sx * 300));
    S.R(X(sx * P.pawl_tip), Y(yb), X(sx * (P.pawl_tip + P.pawl_L)), Y(yb - sx * P.pawl_b));
    S.force(X(sx * R.a), Y(yb - sx * 360), X(sx * R.a), Y(yb), sx > 0 ? `F barra ${nf(R.d.Fb)} kN` : null);
  }
  S.dim(X(-P.BX / 2), Y(-P.BY / 2), X(P.BX / 2), Y(-P.BY / 2), -10, nf(P.BX));
  S.dim(X(-P.BX / 2), Y(-P.BY / 2), X(-P.BX / 2), Y(P.BY / 2), -10, nf(P.BY), "v");
  S.dim(X(-P.X_cyl), Y(P.BY / 2), X(P.X_cyl), Y(P.BY / 2), 8, `${nf(2 * P.X_cyl)} (ejes cilindros)`);
  S.T(`Ø${nf(P.D_disc)} disco · ${P.N_bar} barras Ø${P.D_bar} en R${nf(P.R_bar)}`, X(-P.D_disc / 2), Y(P.D_disc / 2) + 3, 2.4);
  S.T("VISTA 1 – PLANTA", cx, Y(-P.BY / 2) - 22, 4, "c", "TXT", true); S.T("ESC. 1:10", cx, Y(-P.BY / 2) - 27, 2.8, "c");

  // ---- VISTA 2: corte diametral 1:10 ----
  const zb = 215;
  const Z = (z) => zb + z * k1, TD = R.TD;
  S.R(X(-P.BX / 2), Z(0), X(P.BX / 2), Z(P.t_base));
  S.R(X(-P.D_disc / 2), Z(P.t_base), X(P.D_disc / 2), Z(P.t_base + P.t_bot));
  S.R(X(-P.D_disc / 2), Z(P.t_base + P.t_bot + P.gap), X(P.D_disc / 2), Z(P.t_base + TD));
  for (const r of parseRings(P.rings)) for (const sg of [1, -1]) S.R(X(sg * r - P.t_ring / 2), Z(P.t_base + P.t_bot), X(sg * r + P.t_ring / 2), Z(P.t_base + P.t_bot + P.gap), "FINA");
  S.R(X(-P.D_hub / 2), Z(P.t_base), X(P.D_hub / 2), Z(P.t_base + TD), "VIS");
  S.L(cx, Z(-15), cx, Z(P.t_base + TD + 25), "EJE");
  S.dim(X(P.BX / 2), Z(0), X(P.BX / 2), Z(P.t_base), 6, nf(P.t_base), "v");
  S.dim(X(P.D_disc / 2), Z(P.t_base), X(P.D_disc / 2), Z(P.t_base + TD), 14, nf(TD), "v");
  S.T("VISTA 2 – CORTE DIAMETRAL", cx, zb - 12, 4, "c", "TXT", true); S.T("ESC. 1:10", cx, zb - 17, 2.8, "c");

  // ---- DETALLE 1: borde del disco 1:2,5 (sección por una barra) ----
  const k2 = 0.4, rl = parseRings(P.rings), r0 = (rl.length ? rl[rl.length - 1] : P.R_bar - 200) - 60, rx = P.D_disc / 2 + 60;
  const ox = 345, oz = 360, XR = (r) => ox + (r - r0) * k2, ZR = (z) => oz + z * k2;
  S.L(XR(r0), ZR(0), XR(rx), ZR(0)); S.L(XR(r0), ZR(P.t_base), XR(rx), ZR(P.t_base));
  S.L(XR(rx), ZR(-5), XR(rx), ZR(P.t_base + 5), "FINA"); S.L(XR(r0), ZR(-5), XR(r0), ZR(P.t_base + TD + 10), "FINA");
  const zt0 = P.t_base, zt1 = P.t_base + P.t_bot, zt2 = zt1 + P.gap, zt3 = zt2 + P.t_top, Rd = P.D_disc / 2;
  const bx0 = P.R_bar - P.D_hole / 2, bx1 = P.R_bar + P.D_hole / 2;
  for (const [za, zz] of [[zt0, zt1], [zt2, zt3]]) { S.P([[XR(r0), ZR(za)], [XR(bx0), ZR(za)], [XR(bx0), ZR(zz)], [XR(r0), ZR(zz)]], false); S.P([[XR(bx1), ZR(za)], [XR(Rd), ZR(za)], [XR(Rd), ZR(zz)], [XR(bx1), ZR(zz)]], false); }
  S.R(XR(P.R_bar - P.D_bar / 2), ZR(zt0), XR(P.R_bar + P.D_bar / 2), ZR(zt3));
  S.L(XR(P.R_bar), ZR(zt0 - 8), XR(P.R_bar), ZR(zt3 + 8), "EJE");
  if (rl.length) { const rr = rl[rl.length - 1]; S.R(XR(rr - P.t_ring / 2), ZR(zt1), XR(rr + P.t_ring / 2), ZR(zt2)); S.L(XR(rr), ZR(zt1 - 6), XR(rr), ZR(zt2 + 6), "EJE"); S.T(`Alma 4d R${nf(rr)} e=${P.t_ring}`, XR(rr) + 3, ZR(zt2) - 6, 2.2); }
  // biseles de soldadura
  const sb = P.weld_S * k2;
  for (const [zf, sgn] of [[zt3, -1], [zt0, 1]]) for (const xe of [XR(P.R_bar - P.D_bar / 2), XR(P.R_bar + P.D_bar / 2)]) {
    const dir = xe < XR(P.R_bar) ? -1 : 1; S.S([[xe, ZR(zf)], [xe + dir * sb, ZR(zf)], [xe, ZR(zf) + sgn * sb]], "VIS");
  }
  S.dim(XR(Rd), ZR(zt0), XR(Rd), ZR(zt1), 8, nf(P.t_bot), "v"); S.dim(XR(Rd), ZR(zt1), XR(Rd), ZR(zt2), 8, nf(P.gap), "v");
  S.dim(XR(Rd), ZR(zt2), XR(Rd), ZR(zt3), 8, nf(P.t_top), "v"); S.dim(XR(Rd), ZR(zt0), XR(Rd), ZR(zt3), 18, nf(TD), "v");
  S.dim(XR(r0), ZR(0), XR(r0), ZR(P.t_base), -6, nf(P.t_base), "v");
  S.dim(XR(P.R_bar - P.D_bar / 2), ZR(zt3), XR(P.R_bar + P.D_bar / 2), ZR(zt3), 8, `Ø${P.D_bar} (agujero Ø${P.D_hole})`);
  S.T(`4a plancha sup. e=${P.t_top}`, XR(r0) + 2, ZR(zt3) + 2, 2.2); S.T(`4b plancha inf. e=${P.t_bot}`, XR(r0) + 2, ZR(zt0) + 1.0 + P.t_bot * k2 * 0.15, 2.2);
  S.T(`Placa base pos 1 e=${P.t_base}`, XR(r0) + 2, ZR(P.t_base / 2) - 1, 2.2);
  S.T(`Bisel ${P.weld_S} (E = ${P.weld_S - 3}) a ras, ambas caras`, XR(P.R_bar) - 16, ZR(zt3) + 16, 2.2);
  S.T(`Grasa grafitada en interfaz (μ diseño ${nf(P.mu, 2)})`, XR(r0) + 2, ZR(zt0) - 4.5, 2.2);
  S.T("DETALLE 1 – BORDE DEL DISCO (corte por barra 4f)", (XR(r0) + XR(rx)) / 2, oz - 18, 3.6, "c", "TXT", true);
  S.T("ESC. 1:2,5", (XR(r0) + XR(rx)) / 2, oz - 23, 2.8, "c");

  // ---- DETALLE 2: carro y trinquete 1:4 ----
  const k3 = 0.25, xm0 = 840, ox3 = 350, oy3 = 270, X3 = (x) => ox3 + (x - xm0) * k3, Y3 = (y) => oy3 + y * k3;
  const yb = -P.R_bar * Math.sin(R.th), yE = yb - P.eye_off;
  const angA = Math.asin(Math.max(-1, -560 / P.R_bar)), angB = Math.asin(Math.min(1, 60 / P.R_bar));
  const arcPts = (rr) => { const p = []; for (let i = 0; i <= 30; i++) { const t = angA + (angB - angA) * i / 30; p.push([X3(rr * Math.cos(t)), Y3(rr * Math.sin(t))]); } return p; };
  S.P(arcPts(P.D_disc / 2), false, "VIS"); S.P(arcPts(P.R_bar), false, "EJE");
  for (let i = -3; i <= 0; i++) { const a = -R.th + i * 2 * R.th; if (P.R_bar * Math.sin(a) < -560) continue; S.C(X3(P.R_bar * Math.cos(a)), Y3(P.R_bar * Math.sin(a)), P.D_bar / 2 * k3); }
  S.R(X3(P.pawl_tip), Y3(yb), X3(P.pawl_tip + P.pawl_L), Y3(yb - P.pawl_b));
  S.R(X3(P.shoe_x0), Y3(yb + 20), X3(P.shoe_x0 + 130), Y3(yb + 20 - 300));
  S.R(X3(P.X_cyl - P.rail_w / 2), Y3(yb + 60), X3(P.X_cyl + P.rail_w / 2), Y3(yb - 360), "OCU");
  S.L(X3(P.X_cyl), Y3(yb + 80), X3(P.X_cyl), Y3(yE - 120), "EJE"); S.L(X3(R.a), Y3(yb + 80), X3(R.a), Y3(yb - 360), "EJE");
  S.C(X3(P.X_cyl), Y3(yE), 35 * k3 * 1.5); S.R(X3(P.X_cyl - P.D_rod / 2), Y3(yE - 20), X3(P.X_cyl + P.D_rod / 2), Y3(yE - 110));
  S.force(X3(R.a) - 0, Y3(yb - 230), X3(R.a), Y3(yb - 2), null);
  S.T(`F barra = ${nf(R.d.Fb)} kN`, X3(R.a) - 2, Y3(yb - 160), 2.3, "r", "TXT", true);
  S.force(X3(P.X_cyl), Y3(yE - 230), X3(P.X_cyl), Y3(yE - 40), null);
  S.T(`F cil = ${nf(R.d.Fc)} kN (${nf(R.d.p)} bar)`, X3(P.X_cyl) + 3, Y3(yE - 200), 2.3, "l", "TXT", true);
  S.dim(X3(R.a), Y3(yb + 40), X3(P.X_cyl), Y3(yb + 40), 4, `Δ = ${nf(R.Delta, 1)}`);
  S.dim(X3(R.a), Y3(yb - P.pawl_b), X3(P.shoe_x0), Y3(yb - P.pawl_b), -6, `${nf(P.shoe_x0 - R.a, 1)}`);
  S.dim(X3(P.pawl_tip), Y3(yb), X3(P.pawl_tip), Y3(yb - P.pawl_b), -5, nf(P.pawl_b), "v");
  S.dim(X3(P.shoe_x0 + 130), Y3(yb + 20 - 25), X3(P.shoe_x0 + 130), Y3(yb + 20 - 25 - P.Lg), 6, `Lg ${nf(P.Lg)}`, "v");
  S.T(`a = R·cos(${nf(180 / P.N_bar, 1)}°) = ${nf(R.a, 1)} mm desde el eje del disco`, X3(xm0) + 2, Y3(yb + 95), 2.2);
  S.T("DETALLE 2 – CARRO, TRINQUETE Y BARRA (planta)", (X3(xm0) + X3(1250)) / 2, Y3(yE - 290), 3.6, "c", "TXT", true);
  S.T("ESC. 1:4", (X3(xm0) + X3(1250)) / 2, Y3(yE - 290) - 5, 2.8, "c");

  // ---- notas ----
  const notes = [
    "BASES DE CÁLCULO",
    `1. Carga WLL ${nf(P.W_tf)} tf = ${nf(R.W)} kN; disco ${nf(R.mass.total)} kg; N = ${nf(R.N, 1)} kN; e ≤ ${nf(P.e)} mm; φd = ${nf(P.phi_d, 2)}.`,
    `2. Fricción estática de diseño μ = ${nf(P.mu, 2)} con r_ef = ${nf(P.r_eff, 2)} m (uniforme ${nf(R.r_u, 3)} m).`,
    `3. Empuje en par: F barra = T/(2a); K = (1 + 2μg·Δ/Lg)/ηc = ${nf(R.K, 3)}; F cil = K·F barra.`,
    `4. Cadena de empuje verificada a la fuerza de calado ${nf(R.Fmax)} kN (alivio ${nf(P.p_relief)} bar).`,
    "5. Placas 4a/4b: FEA Mindlin (MITC4) de un sector entre nervios con almas, nervios y barras como apoyos.",
    "6. Trinquete: FEA tensión plana Q4. Normas: AISC 360-22 (ASD), ASME BTH-1, AWS D1.1.",
    "7. Plano de verificación. No reemplaza los planos de fabricación emitidos (TT300-B-D/F).",
  ];
  notes.forEach((t, i) => S.T(t, 26, 185 - i * 4.4, 2.3, "l", "TXT", i === 0));

  // ---- tablas (columna derecha) ----
  const tx = 610;
  S.T("PARÁMETROS DE ENTRADA", tx, 578, 3.0, "l", "TXT", true);
  const prow = [];
  for (const g of PARAM_GROUPS) for (const it of g.items) prow.push([it[1], String(typeof P[it[0]] === "number" ? nf(P[it[0]], it[4] && it[4] < 1 ? (it[4] < 0.01 ? 3 : 2) : 0) : P[it[0]]), it[2]]);
  const half = Math.ceil(prow.length / 2);
  S.table(tx, 574, [["Parámetro", 54, "l"], ["Valor", 22, "r"], ["Unid.", 13, "l"]], prow.slice(0, half), 3.6, 1.8);
  S.table(tx + 91, 574, [["Parámetro", 54, "l"], ["Valor", 22, "r"], ["Unid.", 13, "l"]], prow.slice(half), 3.6, 1.8);
  let yy = 574 - (half + 1) * 3.6 - 9;
  S.T("ACCIONAMIENTO – FUERZA POR CILINDRO", tx, yy + 4, 3.0, "l", "TXT", true);
  yy = S.table(tx, yy, [["Caso", 50, "l"], ["μ", 12, "c"], ["r m", 14, "c"], ["F cil kN", 20, "r"], ["p bar", 18, "r"], ["FS", 14, "r"], ["", 52, "l"]],
    R.cases.map((c) => [c.name.split(" – ")[0], nf(c.mu, 2), nf(c.r, 3), nf(c.Fc), nf(c.p), nf(c.FS, 2), c.FS >= 1 ? "gira" : "NO GIRA"]), 4.0, 2.0);
  S.T(`μ máximo vencible a ${nf(P.p_relief)} bar: ${nf(R.muMax(R.r_eff, P.p_relief), 3)} (r ${nf(R.r_eff, 2)}) / ${nf(R.muMax(R.r_max, P.p_relief), 3)} (r ${nf(R.r_max, 2)})`, tx, yy - 4, 2.1);
  yy -= 18;
  S.T("VERIFICACIONES – FACTOR DE UTILIZACIÓN", tx, yy + 4, 3.0, "l", "TXT", true);
  S.table(tx, yy, [["Elemento", 108, "l"], ["Demanda", 22, "r"], ["Capac.", 22, "r"], ["FU", 13, "r"], ["", 15, "c"]],
    V.map((v) => [`${v.grp}: ${v.el}`.slice(0, 70), nf(v.dem, v.dem < 20 ? 2 : 0), nf(v.cap, v.cap < 20 ? 2 : 0), nf(v.fu, 2), (v.kind === "pass" ? v.fu <= 1 : v.fu <= 0.9) ? "OK" : v.fu <= 1 ? "MON." : "NO"]), 3.5, 1.75);
  return S;
}

/* ---------- salidas ---------- */
function sheetSVG(S, C) {
  const H = 594;
  let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 841 594" class="sheet">` + `<rect x="0" y="0" width="841" height="594" fill="${C.paper}"/>`;
  for (const e of S.it) {
    const L = LAYERS[e.ly] || LAYERS.VIS, col = e.ly === "FUERZA" ? C.force : C.ink, dash = L.dash ? ` stroke-dasharray="${L.dash.join(" ")}"` : "";
    if (e.k === "L") s += `<line x1="${e.x1.toFixed(2)}" y1="${(H - e.y1).toFixed(2)}" x2="${e.x2.toFixed(2)}" y2="${(H - e.y2).toFixed(2)}" stroke="${col}" stroke-width="${L.w}"${dash}/>`;
    else if (e.k === "C") s += `<circle cx="${e.x.toFixed(2)}" cy="${(H - e.y).toFixed(2)}" r="${e.r.toFixed(2)}" stroke="${col}" stroke-width="${L.w}" fill="none"${dash}/>`;
    else if (e.k === "S") s += `<polygon points="${e.pts.map((p) => p[0].toFixed(2) + "," + (H - p[1]).toFixed(2)).join(" ")}" fill="${col}"/>`;
    else if (e.k === "T") {
      const an = e.al === "c" ? "middle" : e.al === "r" ? "end" : "start", x = e.x, y = H - e.y;
      s += `<text x="${x.toFixed(2)}" y="${y.toFixed(2)}" font-family="Helvetica, Arial, sans-serif" font-size="${(e.h * 1.38).toFixed(2)}" text-anchor="${an}" fill="${C.ink}"${e.bold ? ' font-weight="700"' : ""}${e.rot ? ` transform="rotate(${-e.rot} ${x.toFixed(2)} ${y.toFixed(2)})"` : ""}>${e.s.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</text>`;
    }
  }
  return s + "</svg>";
}

function dxfText(s) {
  let o = "";
  for (const ch of s) {
    const c = ch.codePointAt(0);
    if (ch === "Ø") o += "%%c"; else if (ch === "°") o += "%%d"; else if (ch === "±") o += "%%p";
    else if (c < 128) o += ch; else o += "\\U+" + c.toString(16).toUpperCase().padStart(4, "0");
  }
  return o;
}
function sheetDXF(S) {
  const out = [];
  const g = (code, val) => { out.push(String(code)); out.push(String(val)); };
  g(0, "SECTION"); g(2, "HEADER"); g(9, "$ACADVER"); g(1, "AC1009"); g(9, "$INSUNITS"); g(70, 4); g(9, "$LTSCALE"); g(40, 1.0); g(0, "ENDSEC");
  g(0, "SECTION"); g(2, "TABLES");
  g(0, "TABLE"); g(2, "LTYPE"); g(70, 3);
  const lt = [["CONTINUOUS", "Solid", []], ["DASHED", "__ __", [3, -1.5]], ["CENTER", "__ . __", [10, -2, 1.5, -2]]];
  for (const [n, d, pat] of lt) { g(0, "LTYPE"); g(2, n); g(70, 0); g(3, d); g(72, 65); g(73, pat.length); g(40, pat.reduce((s, v) => s + Math.abs(v), 0)); for (const v of pat) g(49, v); }
  g(0, "ENDTAB");
  g(0, "TABLE"); g(2, "LAYER"); g(70, Object.keys(LAYERS).length);
  for (const [n, L] of Object.entries(LAYERS)) { g(0, "LAYER"); g(2, n); g(70, 0); g(62, L.color); g(6, n === "EJE" ? "CENTER" : n === "OCU" ? "DASHED" : "CONTINUOUS"); }
  g(0, "ENDTAB"); g(0, "ENDSEC");
  g(0, "SECTION"); g(2, "ENTITIES");
  for (const e of S.it) {
    if (e.k === "L") { g(0, "LINE"); g(8, e.ly); g(10, e.x1.toFixed(3)); g(20, e.y1.toFixed(3)); g(30, 0); g(11, e.x2.toFixed(3)); g(21, e.y2.toFixed(3)); g(31, 0); }
    else if (e.k === "C") { g(0, "CIRCLE"); g(8, e.ly); g(10, e.x.toFixed(3)); g(20, e.y.toFixed(3)); g(30, 0); g(40, e.r.toFixed(3)); }
    else if (e.k === "S") { const p = e.pts; g(0, "SOLID"); g(8, e.ly); g(10, p[0][0].toFixed(3)); g(20, p[0][1].toFixed(3)); g(30, 0); g(11, p[1][0].toFixed(3)); g(21, p[1][1].toFixed(3)); g(31, 0); g(12, p[2][0].toFixed(3)); g(22, p[2][1].toFixed(3)); g(32, 0); g(13, p[2][0].toFixed(3)); g(23, p[2][1].toFixed(3)); g(33, 0); }
    else if (e.k === "T") {
      g(0, "TEXT"); g(8, e.ly); g(10, e.x.toFixed(3)); g(20, e.y.toFixed(3)); g(30, 0); g(40, e.h); g(1, dxfText(e.s));
      if (e.rot) g(50, e.rot);
      const ha = e.al === "c" ? 1 : e.al === "r" ? 2 : 0;
      if (ha) { g(72, ha); g(11, e.x.toFixed(3)); g(21, e.y.toFixed(3)); g(31, 0); }
    }
  }
  g(0, "ENDSEC"); g(0, "EOF");
  return out.join("\r\n") + "\r\n";
}
function pdfText(s) {
  const map = { "μ": "µ", "≤": "<=", "≥": ">=", "φ": "phi", "Δ": "Delta ", "σ": "sigma", "τ": "tau", "η": "eta", "π": "pi", "√": "raiz", "−": "-", "→": "->", "≈": "~", "Ω": "Omega", "ν": "nu", "γ": "gamma", "β": "beta", "…": "...", "✓": "OK" };
  map["∫"] = "int "; map["Σ"] = "Sum "; map["θ"] = "theta"; map["κ"] = "kappa"; map["·"] = "·";
  return String(s).replace(/[μ≤≥φΔστηπ√−→≈Ωνγβ…✓∫Σθκ]/g, (m) => map[m]).replace(/[^\x00-\xFF\u2013\u2014\u2018\u2019\u201C\u201D\u2022\u2026\u20AC]/g, "");
}
function sheetPDF(S) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: [841, 594] });
  const H = 594;
  for (const e of S.it) {
    const L = LAYERS[e.ly] || LAYERS.VIS;
    doc.setDrawColor(0); doc.setFillColor(0); doc.setTextColor(0);
    doc.setLineWidth(L.w); doc.setLineDashPattern(L.dash || [], 0);
    if (e.k === "L") doc.line(e.x1, H - e.y1, e.x2, H - e.y2);
    else if (e.k === "C") doc.circle(e.x, H - e.y, e.r, "S");
    else if (e.k === "S") doc.triangle(e.pts[0][0], H - e.pts[0][1], e.pts[1][0], H - e.pts[1][1], e.pts[2][0], H - e.pts[2][1], "F");
    else if (e.k === "T") {
      doc.setFont("helvetica", e.bold ? "bold" : "normal"); doc.setFontSize(e.h * 4.0);
      const str = pdfText(e.s);
      if (e.rot) { const w = doc.getTextWidth(str); doc.text(str, e.x, H - (e.y - w / 2), { angle: 90 }); }
      else doc.text(str, e.x, H - e.y, { align: e.al === "c" ? "center" : e.al === "r" ? "right" : "left" });
    }
  }
  doc.setLineDashPattern([], 0);
  return doc.output("blob");
}

/* ---------- memoria de verificación A4 ---------- */
async function svgToPng(svg, scale = 2) {
  const img = new Image();
  const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  await new Promise((res, rej) => { img.onload = res; img.onerror = () => rej(new Error("svg")); img.src = url; });
  const c = document.createElement("canvas"); c.width = img.width * scale; c.height = img.height * scale;
  const x = c.getContext("2d"); x.fillStyle = "#ffffff"; x.fillRect(0, 0, c.width, c.height); x.drawImage(img, 0, 0, c.width, c.height);
  return { data: c.toDataURL("image/png"), w: img.width, h: img.height };
}
async function memoriaPDF(R, V, fea, Cp, images) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const P = R.P, M = 16, PW = 210 - 2 * M;
  let y = 18;
  const T = (s, size = 9.5, bold = false, x = M) => { doc.setFont("helvetica", bold ? "bold" : "normal"); doc.setFontSize(size); doc.setTextColor(0); const lines = doc.splitTextToSize(pdfText(s), PW - (x - M)); for (const l of lines) { if (y > 280) { doc.addPage(); y = 18; } doc.text(l, x, y); y += size * 0.43; } };
  const H1 = (s) => { y += 3; if (y > 262) { doc.addPage(); y = 18; } T(s, 12.5, true); y += 1.5; doc.setDrawColor(0); doc.setLineWidth(0.3); doc.line(M, y - 3.2, M + PW, y - 3.2); y += 1; };
  const tbl = (head, body, colStyles) => { doc.autoTable({ startY: y, head: [head.map(pdfText)], body: body.map((r) => r.map(pdfText)), margin: { left: M, right: M }, styles: { fontSize: 8, textColor: 0, lineColor: 120, lineWidth: 0.1, cellPadding: 1.2 }, headStyles: { fillColor: [235, 235, 235], textColor: 0, fontStyle: "bold" }, columnStyles: colStyles || {}, theme: "grid" }); y = doc.lastAutoTable.finalY + 5; };
  const img = (im, wmm) => { const h = wmm * im.h / im.w; if (y + h > 282) { doc.addPage(); y = 18; } doc.addImage(im.data, "PNG", M + (PW - wmm) / 2, y, wmm, h); y += h + 4; };
  T("MEMORIA DE VERIFICACIÓN – TORNAMESA HIDRÁULICA " + nf(P.W_tf) + " tf (TT300-B)", 14, true);
  T("Solución B: interfaz acero-acero con grasa grafitada. Accionamiento por 2 cilindros en par sobre barras verticales.", 9.5);
  T(`Fecha: ${new Date().toLocaleDateString("es-CL")} · Generada con la herramienta de verificación paramétrica · Rev. P`, 8.5);
  y += 2;
  const VV = V.filter((v) => v.kind !== "pass"), worst = VV.reduce((a, b) => (b.fu > a.fu ? b : a));
  H1("1. RESULTADO");
  tbl(["Concepto", "Valor"], [
    ["Fuerza de diseño por cilindro", `${nf(R.d.Fc, 1)} kN (${nf(R.d.tf, 1)} tf) a ${nf(R.d.p)} bar`],
    ["Fuerza disponible por cilindro", `${nf(R.Fmax, 1)} kN a ${nf(P.p_relief)} bar (alivio)`],
    ["Factor de seguridad del accionamiento", nf(R.d.FS, 2)],
    ["μ máximo vencible (r diseño / r máx.)", `${nf(R.muMax(R.r_eff, P.p_relief), 3)} / ${nf(R.muMax(R.r_max, P.p_relief), 3)}`],
    ["Factor de utilización máximo", `${nf(worst.fu, 2)} – ${worst.grp}: ${worst.el}`],
    ["Acero seco (μ " + nf(P.mu_dry, 2) + ")", R.cases[3].FS < 1 ? `No gira (requiere ${nf(R.cases[3].p)} bar)` : `Gira (FS ${nf(R.cases[3].FS, 2)})`],
  ], { 0: { cellWidth: 70 } });
  H1("2. HIPÓTESIS");
  [
    `H1 Carga WLL ${nf(P.W_tf)} tf = ${nf(R.W, 1)} kN; peso disco ${nf(R.mass.total)} kg (${nf(R.Wd, 2)} kN); N = ${nf(R.N, 1)} kN. Excentricidad e ≤ ${nf(P.e)} mm. φd = ${nf(P.phi_d, 2)} sólo en resistencias.`,
    `H2 Interfaz plana anular acero/acero, R = ${nf(P.D_disc / 2)} mm, r = ${nf(P.D_bore / 2)} mm, grasa grafitada NLGI 2 (≥10 % grafito).`,
    `H3 μ estático de diseño = ${nf(P.mu, 2)} (límite superior del rango acero/acero engrasado 0,10–0,20). Nominal ${nf(P.mu_nom, 2)}; contaminado ${nf(P.mu_cont, 2)}; seco ${nf(P.mu_dry, 2)}.`,
    `H4 r uniforme = 2/3·(R³−r³)/(R²−r²) = ${nf(R.r_u, 3)} m; la distribución lineal por excentricidad no lo cambia (∫x·r dA = 0). Diseño r_ef = ${nf(P.r_eff, 2)} m por concentración al borde.`,
    `H5 Dos cilindros en par sobre barras en R${nf(P.R_bar)}; brazo mínimo a = R·cos(180°/N) = ${nf(R.a, 1)} mm.`,
    `H6 Pérdidas: μg = ${nf(P.mu_g, 2)} con Δ = ${nf(R.Delta, 1)} mm y Lg = ${nf(P.Lg)} mm; ηc = ${nf(P.eta_c, 2)}; K = ${nf(R.K, 3)}. T piv = ${nf(R.Tpiv, 2)} kN·m.`,
    `H7 Elementos de la cadena de empuje verificados a la fuerza de calado ${nf(R.Fmax, 1)} kN (alivio ${nf(P.p_relief)} bar).`,
  ].forEach((t) => { T(t, 8.8, false); y += 0.8; });
  H1("3. PARÁMETROS");
  const prm = []; for (const g of PARAM_GROUPS) for (const it of g.items) prm.push([g.t, it[1], typeof P[it[0]] === "number" ? nf(P[it[0]], it[4] && it[4] < 1 ? (it[4] < 0.01 ? 3 : 2) : 0) : P[it[0]], it[2]]);
  tbl(["Grupo", "Parámetro", "Valor", "Unidad"], prm, { 2: { halign: "right" } });
  H1("4. ACCIONAMIENTO");
  ["(1) T = μ·N·r_ef + T_piv", "(2) F_barra = T/(2a)", "(3) K = (1 + 2·μg·Δ/Lg)/ηc", "(4) F_cil = K·F_barra ;  p = F_cil/A ;  FS = F_max/F_cil", "(5) μ_max = (F_max/K·2a − T_piv)/(N·r_ef)"].forEach((t) => T(t, 9));
  y += 1;
  T(`Caso de diseño: T = ${nf(P.mu, 2)} × ${nf(R.N, 1)} × ${nf(P.r_eff, 3)} + ${nf(R.Tpiv, 2)} = ${nf(R.d.T, 1)} kN·m → F_barra = ${nf(R.d.Fb, 1)} kN → F_cil = ${nf(R.d.Fc, 1)} kN → p = ${nf(R.d.p)} bar → FS = ${nf(R.d.FS, 2)}.`, 9);
  y += 1;
  tbl(["Caso", "μ", "r_ef m", "T kN·m", "F barra kN", "F cil kN", "p bar", "FS", "Resultado"], R.cases.map((c) => [c.name, nf(c.mu, 2), nf(c.r, 3), nf(c.T), nf(c.Fb), nf(c.Fc), nf(c.p), nf(c.FS, 2), c.FS >= 1.25 ? "Gira" : c.FS >= 1 ? "Gira (límite)" : "NO GIRA"]));
  tbl(["Componente de F_cil (diseño)", "kN", "%"], R.breakdown.map(([t, v]) => [t, nf(v, 1), nf(v / R.d.Fc * 100, 1)]));
  for (const k of ["plan", "mu", "stroke", "breakdown"]) if (images[k]) img(images[k], k === "breakdown" ? 130 : 170);
  H1("5. DIAGRAMAS DE CARGA DE ELEMENTOS");
  for (const k of ["shoe", "bar", "pin"]) if (images[k]) img(images[k], 140);
  H1("6. VERIFICACIONES");
  tbl(["Grupo", "Elemento", "Demanda", "Capacidad", "Unid.", "FU", "Estado", "Referencia"], V.map((v) => [v.grp, v.el, nf(v.dem, v.dem < 20 ? 2 : 1), nf(v.cap, v.cap < 20 ? 2 : 1), v.unit, nf(v.fu, 2), v.kind === "pass" ? (v.fu <= 1 ? "Cumple" : "No cumple") : v.fu <= 0.9 ? "Aceptable" : v.fu <= 1 ? "Monitoreo" : "No cumple", v.ref]),
    { 2: { halign: "right" }, 3: { halign: "right" }, 5: { halign: "right" } });
  H1("7. ANÁLISIS POR ELEMENTOS FINITOS");
  if (fea && fea.bot) {
    T(`Disco: sector de ${nf(360 / P.N_rib, 1)}° entre nervios, placa Mindlin MITC4 (${fea.bot.model.elems.length} elementos, ${fea.bot.res.ndof} GDL). Apoyos: cubo empotrado; almas 4d y nervios 4e como apoyos lineales (w = 0); barras 4f como apoyos de área; simetría en los bordes del sector. Plancha inferior con q_max = ${nf(R.q_max, 2)} MPa uniforme (conservador); superior con q = ${nf(R.q_top, 2)} MPa en Ø${nf(P.D_load)}.`, 8.8);
    tbl(["Plancha", "σvm máx MPa", "w máx mm", "Reacción almas N/mm", "Reacción barra kN", "Σ cargas / Σ reacciones kN"], ["bot", "top"].map((k) => { const f = fea[k]; return [k === "bot" ? "4b inferior" : "4a superior", nf(f.vmMax, 1), nf(f.wMax, 3), f.ringLine.map((v) => nf(v)).join(" / "), nf(f.barMax, 1), `${nf(f.Fapp, 1)} / ${nf(f.Rsum, 1)}`]; }));
    for (const k of ["feaBot", "feaTop"]) if (images[k]) img(images[k], 110);
  }
  if (fea && fea.pawl) {
    T(`Trinquete: tensión plana Q4 h = 2,5 mm, espesor ${P.pawl_h} mm, carga F = ${nf(R.Fmax, 1)} kN en el asiento R${P.seat_R}; apoyo en la boca del carro (25 mm inferiores) y labio posterior. σ boca FEA = ${nf(fea.pawl.vmMouth)} MPa; teoría de vigas = ${nf(fea.pawl.beam)} MPa; máximo fuera de zonas de contacto = ${nf(fea.pawl.vmFar)} MPa; pico local en contacto = ${nf(fea.pawl.vmMax)} MPa (singularidad del modelo de apoyo).`, 8.8);
    if (images.feaPawl) img(images.feaPawl, 170);
  }
  H1("8. CONCLUSIÓN");
  T(R.d.FS >= 1.25 && worst.fu <= 1 ? `Con los parámetros indicados el accionamiento vence la fricción de diseño con FS = ${nf(R.d.FS, 2)} y todos los elementos verificados quedan con FU ≤ ${nf(worst.fu, 2)}. La lubricación con grasa grafitada es obligatoria.` : `Con los parámetros indicados NO se cumple al menos un criterio (FS accionamiento ${nf(R.d.FS, 2)}; FU máx ${nf(worst.fu, 2)}). Revisar antes de aprobar.`, 9.5);
  const n = doc.getNumberOfPages();
  for (let i = 1; i <= n; i++) { doc.setPage(i); doc.setFontSize(7.5); doc.setFont("helvetica", "normal"); doc.text(pdfText(`TT300-B · Memoria de verificación paramétrica · pág. ${i} de ${n}`), M, 290); }
  return doc.output("blob");
}
