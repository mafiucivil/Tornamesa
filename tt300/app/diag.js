/* Diagramas SVG (fuerzas, vigas, gráficos). Paleta C explícita para poder exportar a PNG/PDF. */
const nf = (x, d = 0) => (isFinite(x) ? Number(x).toLocaleString("es-CL", { minimumFractionDigits: d, maximumFractionDigits: d }) : "–");

const SV = {
  open: (w, h, extra) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" class="dg" style="max-width:${w}px" ${extra || ""}>`,
  line: (x1, y1, x2, y2, c, w = 1, dash) => `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${c}" stroke-width="${w}"${dash ? ` stroke-dasharray="${dash}"` : ""} fill="none"/>`,
  rect: (x, y, w, h, c, fill = "none", sw = 1, dash) => `<rect x="${Math.min(x, x + w).toFixed(1)}" y="${Math.min(y, y + h).toFixed(1)}" width="${Math.abs(w).toFixed(1)}" height="${Math.abs(h).toFixed(1)}" stroke="${c}" stroke-width="${sw}" fill="${fill}"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`,
  circ: (x, y, r, c, fill = "none", sw = 1, dash) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${Math.max(0.5, r).toFixed(1)}" stroke="${c}" stroke-width="${sw}" fill="${fill}"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`,
  poly: (pts, c, fill = "none", sw = 1, dash) => `<polyline points="${pts.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}" stroke="${c}" stroke-width="${sw}" fill="${fill}"${dash ? ` stroke-dasharray="${dash}"` : ""} stroke-linejoin="round"/>`,
  pgon: (pts, c, fill, sw = 1, op = 1) => `<polygon points="${pts.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}" stroke="${c}" stroke-width="${sw}" fill="${fill}" fill-opacity="${op}"/>`,
  text: (x, y, s, C, o = {}) => `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" font-family="${C.font}" font-size="${o.size || 12}" fill="${o.fill || C.ink}" text-anchor="${o.anchor || "start"}"${o.weight ? ` font-weight="${o.weight}"` : ""}${o.rot ? ` transform="rotate(${o.rot} ${x.toFixed(1)} ${y.toFixed(1)})"` : ""}${o.base ? ` dominant-baseline="${o.base}"` : ""}>${String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")}</text>`,
  arrow: (x1, y1, x2, y2, c, w = 2.2, head = 9) => {
    const a = Math.atan2(y2 - y1, x2 - x1), hx = x2 - head * Math.cos(a), hy = y2 - head * Math.sin(a);
    const p1 = [hx + head * 0.42 * Math.sin(a), hy - head * 0.42 * Math.cos(a)], p2 = [hx - head * 0.42 * Math.sin(a), hy + head * 0.42 * Math.cos(a)];
    return SV.line(x1, y1, hx, hy, c, w) + SV.pgon([[x2, y2], p1, p2], c, c, 1);
  },
  arcArrow: (cx, cy, r, a0, a1, c, w = 1.8) => {
    const P = (a) => [cx + r * Math.cos(a), cy - r * Math.sin(a)];
    const p0 = P(a0), p1 = P(a1), large = Math.abs(a1 - a0) > Math.PI ? 1 : 0, sweep = a1 > a0 ? 0 : 1;
    const tang = a1 > a0 ? a1 + Math.PI / 2 : a1 - Math.PI / 2;
    const tip = p1, back = [tip[0] - 9 * Math.cos(-tang), tip[1] - 9 * Math.sin(-tang)];
    return `<path d="M${p0[0].toFixed(1)},${p0[1].toFixed(1)} A${r},${r} 0 ${large} ${sweep} ${p1[0].toFixed(1)},${p1[1].toFixed(1)}" stroke="${c}" stroke-width="${w}" fill="none"/>` + SV.arrow(back[0], back[1], tip[0], tip[1], c, w, 9);
  },
  label: (x, y, lines, C, o = {}) => {
    const size = o.size || 12, lh = size * 1.3, w = Math.max(...lines.map((l) => l.length)) * size * 0.56 + 12, h = lines.length * lh + 8;
    const x0 = o.anchor === "end" ? x - w : o.anchor === "middle" ? x - w / 2 : x;
    let s = `<rect x="${x0.toFixed(1)}" y="${(y - size - 3).toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" rx="3" fill="${C.bg}" fill-opacity="0.92" stroke="${o.stroke || C.line}" stroke-width="1"/>`;
    lines.forEach((l, i) => { s += SV.text(x0 + 6, y + i * lh, l, C, { size, weight: i === 0 && o.boldFirst ? 600 : null, fill: i === 0 && o.color ? o.color : C.ink }); });
    return s;
  },
};

/* ---------- D1: planta con fuerzas ---------- */
function dgPlan(R, C) {
  const P = R.P, W = 860, H = 560, k = Math.min(0.2, 460 / Math.max(P.BX, P.BY, P.D_disc)), cx = W / 2, cy = H / 2 + 4;
  const X = (x) => cx + x * k, Y = (y) => cy - y * k;
  let s = SV.open(W, H);
  s += SV.rect(X(-P.BX / 2), Y(P.BY / 2), P.BX * k, P.BY * k, C.mute, C.fill2, 1);
  s += SV.circ(cx, cy, P.D_disc / 2 * k, C.ink, C.fill, 1.6);
  for (const r of parseRings(P.rings)) s += SV.circ(cx, cy, r * k, C.mute, "none", 1, "5 4");
  for (let i = 0; i < P.N_rib; i++) { const a = 2 * Math.PI * i / P.N_rib; s += SV.line(X(P.D_hub / 2 * Math.cos(a)), Y(P.D_hub / 2 * Math.sin(a)), X(P.R_rib * Math.cos(a)), Y(P.R_rib * Math.sin(a)), C.mute, 1, "5 4"); }
  for (let i = 0; i < P.N_bar; i++) { const a = Math.PI / P.N_bar + 2 * Math.PI * i / P.N_bar; s += SV.circ(X(P.R_bar * Math.cos(a)), Y(P.R_bar * Math.sin(a)), P.D_bar / 2 * k, C.ink, C.fill2, 1); }
  s += SV.circ(cx, cy, P.D_hub / 2 * k, C.ink, "none", 1.2) + SV.circ(cx, cy, P.D_piv / 2 * k, C.ink, C.fill2, 1);
  const d = R.d, Fs = 330 / Math.max(R.Fmax, d.Fc);   // mm modelo por kN
  const Rg = d.Fb * R.Delta / P.Lg;
  for (const sx of [1, -1]) {
    const yb = -sx * P.R_bar * Math.sin(R.th), xa = sx * R.a;
    const yE = yb - sx * P.eye_off, yP = -sx * R.Ybrk;
    // guía
    s += SV.rect(X(sx * P.X_cyl - P.rail_w / 2), Y(425), P.rail_w * k, 850 * k, C.mute, C.fill2, 1);
    // ménsula
    s += SV.rect(X(sx * P.X_cyl - P.gap_cheek / 2 - P.t_cheek), Y(yP + P.L_cheek / 2), (P.gap_cheek + 2 * P.t_cheek) * k, P.L_cheek * k, C.ink, C.fill2, 1.2);
    // cilindro
    const yb0 = yP + sx * 70, yb1 = yP + sx * 370;
    s += SV.rect(X(sx * P.X_cyl - 70), Y(Math.max(yb0, yb1)), 140 * k, 300 * k, C.ink, C.cyl, 1.2);
    s += SV.rect(X(sx * P.X_cyl - P.D_rod / 2), Y(Math.max(yb1, yE)), P.D_rod * k, Math.abs(yE - yb1) * k, C.ink, C.fill, 1);
    s += SV.circ(X(sx * P.X_cyl), Y(yP), 35 * k * 1.5, C.ink, C.bg, 1.2) + SV.circ(X(sx * P.X_cyl), Y(yE), 35 * k * 1.5, C.ink, C.bg, 1.2);
    // carro y trinquete
    const yf = yb + sx * 20, yr = yb + sx * 20 - sx * 300;
    s += SV.rect(X(sx * P.shoe_x0), Y(Math.max(yf, yr)), sx * 130 * k, 300 * k, C.ink, C.shoe, 1.2);
    s += SV.rect(X(sx * P.pawl_tip), Y(Math.max(yb, yb - sx * P.pawl_b)), sx * P.pawl_L * k, P.pawl_b * k, C.ink, C.pawl, 1.2);
    // fuerzas
    const Lb = d.Fb * Fs, Lc = d.Fc * Fs, Lr = Rg * Fs * 1.0;
    s += SV.arrow(X(xa), Y(yb - sx * Lb), X(xa), Y(yb), C.force, 3);
    s += SV.arrow(X(sx * P.X_cyl), Y(yE - sx * Lc * 0.55), X(sx * P.X_cyl), Y(yE), C.force, 3);
    s += SV.arrow(X(sx * P.X_cyl), Y(yP), X(sx * P.X_cyl), Y(yP - sx * Lc * 0.55), C.react, 2.6);
    s += SV.arrow(X(sx * (P.X_cyl + 25) + sx * Lr * 0.6), Y(yf - sx * 12), X(sx * (P.X_cyl + 25)), Y(yf - sx * 12), C.react, 2.2);
    s += SV.arrow(X(sx * (P.X_cyl - 25) - sx * Lr * 0.6), Y(yr + sx * 12), X(sx * (P.X_cyl - 25)), Y(yr + sx * 12), C.react, 2.2);
    const lx = sx > 0 ? X(xa) - 12 : X(xa) + 12, an = sx > 0 ? "end" : "start";
    s += SV.label(lx, Y(yb - sx * Lb * 0.55), [`F barra = ${nf(d.Fb)} kN`], C, { anchor: an, color: C.force, boldFirst: true });
    s += SV.label(sx > 0 ? X(sx * P.X_cyl) + 30 : X(sx * P.X_cyl) - 30, Y((yE + yb1) / 2), [`F cil = ${nf(d.Fc)} kN`, `p = ${nf(d.p)} bar`], C, { anchor: sx > 0 ? "start" : "end", color: C.force, boldFirst: true });
    s += SV.label(sx > 0 ? X(sx * P.X_cyl) + 30 : X(sx * P.X_cyl) - 30, Y(yP - sx * 40), [`Reacción ménsula`, `${nf(d.Fc)} kN`], C, { anchor: sx > 0 ? "start" : "end", color: C.react, boldFirst: true });
    s += SV.label(sx > 0 ? X(sx * (P.X_cyl + 25) + sx * Lr * 0.6) + 6 : X(sx * (P.X_cyl + 25) + sx * Lr * 0.6) - 6, Y(yf - sx * 12) + 4, [`R guía = ${nf(Rg)} kN`], C, { anchor: sx > 0 ? "start" : "end", color: C.react, size: 11 });
  }
  s += SV.arcArrow(cx, cy, 70, Math.PI * 0.15, Math.PI * 0.85, C.accent, 2);
  s += SV.text(cx, cy - 78, "giro", C, { anchor: "middle", size: 11, fill: C.accent });
  s += SV.arcArrow(cx, cy, 120, -Math.PI * 0.25, -Math.PI * 0.75, C.react, 2);
  s += SV.label(cx, cy + 150, [`T resistente = ${nf(d.T)} kN·m`, `μ = ${nf(d.mu, 2)} · N = ${nf(R.N)} kN · r = ${nf(d.r, 3)} m`], C, { anchor: "middle", color: C.react, boldFirst: true, size: 11.5 });
  s += SV.line(cx, cy, X(R.a), cy, C.mute, 1, "3 3") + SV.text((cx + X(R.a)) / 2, cy - 6, `a = ${nf(R.a, 1)} mm`, C, { anchor: "middle", size: 11 });
  s += SV.text(14, 22, "PLANTA – FUERZAS EN EL CASO DE DISEÑO (escala de flechas común)", C, { size: 12, weight: 600 });
  s += SV.text(14, H - 12, `Par motor = 2 · F barra · a = ${nf(2 * d.Fb * R.a / 1000)} kN·m   |   Resultante sobre el pivote = 0 (par puro)`, C, { size: 11.5, fill: C.mute });
  return s + "</svg>";
}

/* ---------- D2: diagrama de cuerpo libre del carro ---------- */
function dgShoe(R, C, F) {
  const P = R.P, W = 560, H = 420;
  F = F || R.d.Fb;
  const Fc = F * R.K, Rg = F * R.Delta / P.Lg, fr = P.mu_g * Rg;
  let s = SV.open(W, H);
  const x0 = 210, x1 = 360, y0 = 100, y1 = 320;
  s += SV.rect(x0, y0, x1 - x0, y1 - y0, C.ink, C.shoe, 1.6);
  s += SV.rect(110, y0 - 2, x0 - 110 + 60, 46, C.ink, C.pawl, 1.4);
  s += SV.circ(110, y0 - 2, 22, C.ink, C.fill2, 1.4);
  const xc = 320, xb = 110;
  s += SV.line(xc, 56, xc, H - 40, C.mute, 1, "8 4 2 4");
  s += SV.line(xb, 56, xb, H - 40, C.mute, 1, "8 4 2 4");
  s += SV.text(xc + 4, H - 30, "eje cilindro / guía", C, { size: 10.5, fill: C.mute });
  s += SV.text(xb - 4, H - 30, "línea de la barra", C, { size: 10.5, fill: C.mute, anchor: "end" });
  s += SV.arrow(xc, H - 44, xc, y1 + 2, C.force, 3);
  s += SV.label(xc + 10, y1 + 30, [`F cil·ηc = ${nf(Fc * P.eta_c)} kN`, `(F cil = ${nf(Fc)} kN)`], C, { color: C.force, boldFirst: true, size: 11.5 });
  s += SV.arrow(xb, y0 - 26, xb, y0 + 46, C.react, 3);
  s += SV.label(xb - 6, y0 + 74, [`F barra = ${nf(F)} kN`], C, { anchor: "middle", color: C.react, boldFirst: true, size: 11.5 });
  // reacciones de guía
  s += SV.arrow(x1 + 70, y0 + 20, x1 + 2, y0 + 20, C.react, 2.4);
  s += SV.arrow(x0 - 70, y1 - 20, x0 - 2, y1 - 20, C.react, 2.4);
  s += SV.label(x1 + 74, y0 + 24, [`R1 = ${nf(Rg)} kN`, `μg·R1 = ${nf(fr)} kN`], C, { color: C.react, size: 11 });
  s += SV.label(x0 - 74, y1 - 16, [`R2 = ${nf(Rg)} kN`, `μg·R2 = ${nf(fr)} kN`], C, { anchor: "end", color: C.react, size: 11 });
  s += SV.arrow(x1 + 8, y0 + 24, x1 + 8, y0 + 54, C.mute, 1.8, 7);
  s += SV.arrow(x0 - 8, y1 - 54, x0 - 8, y1 - 24, C.mute, 1.8, 7);
  s += SV.line(xb, 48, xc, 48, C.ink, 1) + SV.text((xb + xc) / 2, 43, `Δ = ${nf(R.Delta, 1)} mm`, C, { anchor: "middle", size: 11 });
  s += SV.line(x1 + 40, y0 + 20, x1 + 40, y1 - 20, C.mute, 1, "3 3") + SV.text(x1 + 46, (y0 + y1) / 2, `Lg = ${nf(P.Lg)} mm`, C, { size: 11, fill: C.mute });
  s += SV.text(14, 18, "CUERPO LIBRE DEL CARRO (planta, sin escala)", C, { size: 12, weight: 600 });
  s += SV.text(14, H - 8, `R = F·Δ/Lg ;  F cil·ηc = F barra + 2·μg·R  →  K = ${nf(R.K, 3)}`, C, { size: 11.5 });
  return s + "</svg>";
}

/* ---------- D3: barra 4f como viga entre planchas ---------- */
function dgBar(R, C) {
  const P = R.P, F = R.Fmax, L = P.gap, c = Math.min(P.pawl_h, L), W = 560, H = 430;
  const x0 = 90, x1 = 470, sc = (x1 - x0) / L, X = (x) => x0 + x * sc;
  const Mss = F / 4 * (L - c / 2), Mfe = F * (3 * L * L - c * c) / (24 * L), Mmidf = Mss - Mfe;
  let s = SV.open(W, H);
  s += SV.text(14, 18, `BARRA 4f Ø${P.D_bar} – VIGA ENTRE PLANCHAS (F calado = ${nf(F)} kN)`, C, { size: 12, weight: 600 });
  const yb = 92;
  s += SV.rect(x0 - 26, yb - 40, 26, 80, C.ink, C.fill2, 1.2) + SV.rect(x1, yb - 40, 26, 80, C.ink, C.fill2, 1.2);
  s += SV.text(x0 - 13, yb + 56, "4b", C, { anchor: "middle", size: 11 }) + SV.text(x1 + 13, yb + 56, "4a", C, { anchor: "middle", size: 11 });
  s += SV.rect(x0, yb - 10, x1 - x0, 20, C.ink, C.fill, 1.4);
  const xa = X((L - c) / 2), xb2 = X((L + c) / 2);
  for (let i = 0; i <= 8; i++) { const x = xa + (xb2 - xa) * i / 8; s += SV.arrow(x, yb - 44, x, yb - 11, C.force, 1.4, 6); }
  s += SV.line(xa, yb - 44, xb2, yb - 44, C.force, 1.4);
  s += SV.text((xa + xb2) / 2, yb - 50, `F = ${nf(F)} kN en c = ${nf(c)} mm (alto trinquete)`, C, { anchor: "middle", size: 11, fill: C.force });
  s += SV.text((x0 + x1) / 2, yb + 30, `L = ${nf(L)} mm (luz libre entre planchas)`, C, { anchor: "middle", size: 11, fill: C.mute });
  // corte
  const yV = 190, vs = 40 / (F / 2);
  s += SV.line(x0, yV, x1, yV, C.mute, 1);
  s += SV.pgon([[x0, yV], [x0, yV - F / 2 * vs], [xa, yV - F / 2 * vs], [xb2, yV + F / 2 * vs], [x1, yV + F / 2 * vs], [x1, yV]], C.accent, C.accent, 1.4, 0.18);
  s += SV.text(14, yV + 4, "V (kN)", C, { size: 11, weight: 600 });
  s += SV.text(x0 + 4, yV - F / 2 * vs - 5, `+${nf(F / 2)}`, C, { size: 11 }) + SV.text(x1 - 4, yV + F / 2 * vs + 14, `−${nf(F / 2)}`, C, { size: 11, anchor: "end" });
  // momento
  const yM = 320, ms = 70 / Math.max(Mss, Mfe);
  const Mpin = (x) => (x <= (L - c) / 2 ? F / 2 * x : x >= (L + c) / 2 ? F / 2 * (L - x) : F / 2 * x - F / c * (x - (L - c) / 2) ** 2 / 2);
  const pts = [], ptsF = [];
  for (let i = 0; i <= 60; i++) { const x = L * i / 60; pts.push([X(x), yM + Mpin(x) * ms]); ptsF.push([X(x), yM + (Mpin(x) - Mfe) * ms]); }
  s += SV.line(x0, yM, x1, yM, C.mute, 1);
  s += SV.pgon([[x0, yM], ...pts, [x1, yM]], C.force, C.force, 1.6, 0.14);
  s += SV.poly(ptsF, C.react, "none", 1.8, "6 4");
  s += SV.text(14, yM + 4, "M (kN·m)", C, { size: 11, weight: 600 });
  s += SV.label(X(L / 2) + 50, yM + Mss * ms - 4, [`Rotulada: M máx = ${nf(Mss / 1e3, 2)} kN·m`], C, { color: C.force, size: 11 });
  s += SV.label(x0 + 8, yM - Mfe * ms - 12, [`Empotrada: M extremo = ${nf(Mfe / 1e3, 2)} kN·m`, `M centro = ${nf(Mmidf / 1e3, 2)} kN·m`], C, { color: C.react, size: 11 });
  s += SV.text(14, H - 8, "Barra: se verifica con M rotulado. Soldadura bisel: con M empotrado + V.", C, { size: 11, fill: C.mute });
  return s + "</svg>";
}

/* ---------- D4: pasador en horquilla ---------- */
function dgPin(R, C) {
  const P = R.P, F = R.Fmax, W = 560, H = 360;
  const t = P.t_cheek, g = (P.gap_cheek - P.w_eye) / 2, b = P.w_eye, tot = 2 * t + P.gap_cheek;
  const x0 = 110, sc = 340 / tot, X = (x) => x0 + x * sc;
  let s = SV.open(W, H);
  s += SV.text(14, 18, `PASADOR Ø${P.D_pin} EN HORQUILLA DE LA MÉNSULA (F = ${nf(F)} kN)`, C, { size: 12, weight: 600 });
  const yp = 110;
  s += SV.rect(X(0), yp - 60, t * sc, 50, C.ink, C.fill2, 1.2) + SV.rect(X(tot - t), yp - 60, t * sc, 50, C.ink, C.fill2, 1.2);
  s += SV.rect(X(t + g), yp + 10, b * sc, 50, C.ink, C.cyl, 1.2);
  s += SV.rect(X(-10), yp - 9, (tot + 20) * sc, 18, C.ink, C.fill, 1.4);
  s += SV.arrow(X(t / 2), yp - 70, X(t / 2), yp - 10, C.react, 2.4) + SV.arrow(X(tot - t / 2), yp - 70, X(tot - t / 2), yp - 10, C.react, 2.4);
  s += SV.arrow(X(tot / 2), yp + 75, X(tot / 2), yp + 10, C.force, 3);
  s += SV.text(X(t / 2), yp - 76, `F/2 = ${nf(F / 2)}`, C, { anchor: "middle", size: 11, fill: C.react });
  s += SV.text(X(tot - t / 2), yp - 76, `F/2 = ${nf(F / 2)}`, C, { anchor: "middle", size: 11, fill: C.react });
  s += SV.text(X(tot / 2), yp + 92, `F = ${nf(F)} kN (ojal GE${P.D_pin})`, C, { anchor: "middle", size: 11, fill: C.force });
  const M = R.extra ? R.extra.Mpin : F / 2 * (t / 2 + g + b / 4) / 1e3;
  const yM = 250, ms = 60 / M;
  const xs = [0, t / 2, t + g, tot / 2, tot - t - g, tot - t / 2, tot].map(X);
  s += SV.line(xs[0], yM, xs[6], yM, C.mute, 1);
  s += SV.pgon([[xs[1], yM], [xs[2], yM + (F / 2 * (t / 2 + g) / 1e3) * ms], [xs[3], yM + M * ms], [xs[4], yM + (F / 2 * (t / 2 + g) / 1e3) * ms], [xs[5], yM]], C.force, C.force, 1.6, 0.15);
  s += SV.text(14, yM + 4, "M (kN·m)", C, { size: 11, weight: 600 });
  s += SV.label(xs[3] + 14, yM + M * ms + 4, [`M máx = F/2·(t/2 + g + b/4) = ${nf(M, 2)} kN·m`, `σ = ${nf(M * 1e6 / (Math.PI * P.D_pin ** 3 / 32))} MPa`], C, { color: C.force, size: 11 });
  s += SV.text(14, H - 8, `t = ${t} mejilla · g = ${nf(g, 1)} holgura · b = ${b} ojal`, C, { size: 11, fill: C.mute });
  return s + "</svg>";
}

/* ---------- gráfico genérico ---------- */
function dgChart(o, C) {
  const W = o.w || 560, H = o.h || 340, m = { l: 58, r: o.y2 ? 58 : 18, t: 34, b: 46 };
  const pw = W - m.l - m.r, ph = H - m.t - m.b;
  const X = (x) => m.l + (x - o.xr[0]) / (o.xr[1] - o.xr[0]) * pw, Y = (y) => m.t + ph - (y - o.yr[0]) / (o.yr[1] - o.yr[0]) * ph;
  let s = SV.open(W, H);
  s += SV.text(14, 18, o.title, C, { size: 12, weight: 600 });
  for (const b of o.bands || []) s += SV.rect(X(b[0]), m.t, X(b[1]) - X(b[0]), ph, "none", C.band, 0) + SV.text((X(b[0]) + X(b[1])) / 2, m.t + 14, b[2], C, { anchor: "middle", size: 10.5, fill: C.mute });
  for (const t of o.xt) { s += SV.line(X(t), m.t, X(t), m.t + ph, C.grid, 1) + SV.text(X(t), m.t + ph + 16, o.xf ? o.xf(t) : nf(t, 2), C, { anchor: "middle", size: 10.5, fill: C.mute }); }
  for (const t of o.yt) { s += SV.line(m.l, Y(t), m.l + pw, Y(t), C.grid, 1) + SV.text(m.l - 6, Y(t) + 4, nf(t), C, { anchor: "end", size: 10.5, fill: C.mute }); }
  if (o.y2) for (const t of o.yt) s += SV.text(m.l + pw + 6, Y(t) + 4, nf(o.y2(t)), C, { size: 10.5, fill: C.mute });
  s += SV.rect(m.l, m.t, pw, ph, C.line, "none", 1);
  s += SV.text(m.l + pw / 2, H - 8, o.xl, C, { anchor: "middle", size: 11 });
  s += SV.text(14, m.t + ph / 2, o.yl, C, { anchor: "middle", size: 11, rot: -90 });
  if (o.y2l) s += SV.text(W - 12, m.t + ph / 2, o.y2l, C, { anchor: "middle", size: 11, rot: 90 });
  for (const h of o.hl || []) { s += SV.line(m.l, Y(h.y), m.l + pw, Y(h.y), h.c, h.w || 1.6, h.dash) + SV.text(m.l + 6, Y(h.y) - 5, h.t, C, { size: 10.5, fill: h.c, weight: 600 }); }
  const clip = `cp${Math.random().toString(36).slice(2, 8)}`;
  s += `<defs><clipPath id="${clip}"><rect x="${m.l}" y="${m.t}" width="${pw}" height="${ph}"/></clipPath></defs><g clip-path="url(#${clip})">`;
  for (const se of o.series) s += SV.poly(se.pts.map((p) => [X(p[0]), Y(p[1])]), se.c, "none", se.w || 2, se.dash);
  s += "</g>";
  for (const se of o.series) if (se.lab) { const p = se.lab.at; s += SV.text(X(p[0]), Y(p[1]), se.lab.t, C, { size: 10.5, fill: se.c, anchor: se.lab.anchor || "start", weight: 600 }); }
  if (o.legend) {
    const lx = m.l + pw - 170, ly = m.t + ph - 14 - o.legend.length * 17;
    s += `<rect x="${lx - 8}" y="${ly - 14}" width="174" height="${o.legend.length * 17 + 10}" rx="3" fill="${C.bg}" fill-opacity="0.92" stroke="${C.line}"/>`;
    o.legend.forEach(([c, w, dash, t], i) => { const y = ly + i * 17; s += SV.line(lx, y - 4, lx + 22, y - 4, c, w, dash) + SV.text(lx + 28, y, t, C, { size: 10.5 }); });
  }
  for (const mk of o.markers || []) {
    s += SV.circ(X(mk.x), Y(Math.min(mk.y, o.yr[1])), 4.5, mk.c, mk.c, 1);
    s += SV.text(X(mk.x) + (mk.dx || 7), Y(Math.min(mk.y, o.yr[1])) + (mk.dy || -7), mk.t, C, { size: 10.5, fill: C.ink, anchor: mk.anchor || "start" });
  }
  return s + "</svg>";
}
function niceTicks(lo, hi, n) {
  const span = hi - lo, step0 = span / n, mag = 10 ** Math.floor(Math.log10(step0)), r = step0 / mag;
  const step = (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * mag, t = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) t.push(+v.toFixed(10));
  return t;
}
function dgMu(R, C) {
  const P = R.P, xmax = Math.max(0.6, P.mu_dry + 0.05), Fc = (mu, r) => R.cs(mu, r).Fc;
  const ymax = Math.max(R.Fmax * 1.35, Fc(xmax, R.r_eff) * 0.8);
  const curve = (r) => { const pts = []; for (let i = 0; i <= 60; i++) { const mu = xmax * i / 60; pts.push([mu, Fc(mu, r)]); } return pts; };
  const lab = (r, t) => { let mu = xmax; const f = Fc(xmax, r); if (f > ymax) mu = (ymax * 0.97 / R.K * 2 * R.a / 1000 - R.Tpiv) / (R.N * r); return { at: [mu, Fc(mu, r)], t, anchor: "end" }; };
  return dgChart({
    title: "FUERZA POR CILINDRO vs COEFICIENTE DE FRICCIÓN", xr: [0, xmax], yr: [0, ymax], xt: niceTicks(0, xmax, 6), yt: niceTicks(0, ymax, 6),
    xl: "μ estático en la interfaz de giro", yl: "F por cilindro (kN)", y2: (F) => F * 1e3 / R.A * 10, y2l: "presión (bar)",
    bands: [[0.10, 0.20, "acero/acero engrasado"], [0.5, Math.min(0.8, xmax), "acero seco"]],
    hl: [{ y: R.Fmax, c: C.bad, t: `alivio ${nf(P.p_relief)} bar = ${nf(R.Fmax)} kN` }, { y: R.Falarm, c: C.warn, t: `alarma ${nf(P.p_alarm)} bar = ${nf(R.Falarm)} kN`, dash: "6 4" }],
    series: [
      { pts: curve(R.r_u), c: C.mute, w: 1.6 },
      { pts: curve(R.r_eff), c: C.accent, w: 2.6 },
      { pts: curve(R.r_max), c: C.mute, w: 1.4, dash: "5 4" },
    ],
    legend: [[C.accent, 2.6, null, `r ${nf(R.r_eff, 2)} m (diseño)`], [C.mute, 1.6, null, `r ${nf(R.r_u, 3)} m (uniforme)`], [C.mute, 1.4, "5 4", `r ${nf(R.r_max, 2)} m (cota física)`]],
    markers: R.cases.map((c) => ({ x: c.mu, y: c.Fc, c: c.FS >= 1 ? C.good : C.bad, t: `${nf(c.Fc)} kN`, dx: 7, dy: c.key === "nom" ? 14 : -7 })),
  }, C);
}
function dgStroke(R, C) {
  const P = R.P, d = R.stroke, ymax = Math.max(R.Fmax * 1.15, ...d.map((r) => r.con) ) * 1.05;
  const ser = (k, c, w, dash, t) => ({ pts: [[0, 0], [P.free, 0], ...d.map((r) => [r.s, r[k]])], c, w, dash, lab: { at: [d[d.length - 1].s, d[d.length - 1][k]], t, anchor: "end" } });
  return dgChart({
    title: "FUERZA EN CADA CILINDRO A LO LARGO DE LA CARRERA", xr: [0, P.stroke], yr: [0, ymax], xt: niceTicks(0, P.stroke, 8), yt: niceTicks(0, ymax, 6), xf: (t) => nf(t),
    xl: `carrera del vástago (mm) – libre 0–${nf(P.free)}, toma barra a −${nf(180 / P.N_bar, 1)}° y suelta a +${nf(180 / P.N_bar, 1)}°`, yl: "F por cilindro (kN)", y2: (F) => F * 1e3 / R.A * 10, y2l: "presión (bar)",
    hl: [{ y: R.Fmax, c: C.bad, t: "alivio" }, { y: R.Falarm, c: C.warn, t: "alarma", dash: "6 4" }],
    series: [ser("nom", C.good, 1.8, null, "nominal"), ser("dis", C.accent, 2.6, null, "diseño"), ser("con", C.warn, 1.8, "6 4", "contaminado")],
  }, C);
}
function dgBreak(R, C) {
  const W = 900, H = 150, tot = R.d.Fc, x0 = 20, x1 = W - 20, sc = (x1 - x0) / tot;
  let s = SV.open(W, H) + SV.text(14, 18, `DESGLOSE DE LA FUERZA DE DISEÑO POR CILINDRO (${nf(tot)} kN)`, C, { size: 12, weight: 600 });
  const cols = [C.accent, C.react, C.warn, C.mute];
  let x = x0;
  R.breakdown.forEach(([t, v], i) => {
    const w = v * sc;
    s += SV.rect(x, 40, w, 34, C.bg, cols[i], 1.5);
    if (w > 46) s += SV.text(x + w / 2, 62, nf(v), C, { anchor: "middle", size: 11.5, weight: 600, fill: C.bg });
    x += w;
  });
  R.breakdown.forEach(([t, v], i) => {
    const yy = 102 + (i % 2) * 22, xx = 20 + Math.floor(i / 2) * 440;
    s += SV.rect(xx, yy - 10, 12, 12, cols[i], cols[i], 1) + SV.text(xx + 18, yy, `${t}: ${nf(v, 1)} kN (${nf(v / tot * 100, 1)} %)`, C, { size: 11 });
  });
  return s + "</svg>";
}
