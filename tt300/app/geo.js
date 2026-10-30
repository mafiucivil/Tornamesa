/* Esquema de geometría: vistas 2D (planta, elevación, detalle de borde) y modelo 3D con resaltado del parámetro editado. */
const PART_OF = {
  W_tf: ["load"], e: ["load"], phi_d: ["load"], D_load: ["load"],
  D_disc: ["top", "bot"], t_top: ["top"], t_bot: ["bot"], gap: ["top", "bot", "rings", "ribs"], D_hub: ["hub"], D_bore: ["hub", "pivot"],
  rings: ["rings"], t_ring: ["rings"], N_rib: ["ribs"], t_rib: ["ribs"], R_rib: ["ribs"],
  R_bar: ["bars"], D_bar: ["bars"], N_bar: ["bars"], D_hole: ["bars"], weld_S: ["bars"],
  mu: ["iface"], r_eff: ["iface"], mu_nom: ["iface"], mu_cont: ["iface"], mu_dry: ["iface"], q_lim: ["iface"],
  D_piston: ["cyl"], D_rod: ["cyl"], p_relief: ["cyl"], p_alarm: ["cyl"], stroke: ["cyl"], free: ["cyl", "shoe"], L0: ["cyl"], eye_off: ["cyl", "shoe"],
  X_cyl: ["cyl", "rail", "bracket"], Lg: ["shoe", "rail"], mu_g: ["shoe", "rail"], eta_c: ["cyl"], mu_piv: ["pivot"], H_frac: ["pivot"],
  pawl_tip: ["pawl"], pawl_L: ["pawl"], pawl_b: ["pawl"], pawl_h: ["pawl"], seat_R: ["pawl"], shoe_x0: ["shoe"], Fy_pawl: ["pawl"],
  D_pin: ["bracket"], t_cheek: ["bracket"], gap_cheek: ["bracket"], w_eye: ["bracket"], L_cheek: ["bracket"], h_axis: ["bracket", "cyl"], Fy_pin: ["bracket", "pivot"],
  rail_w: ["rail"], rail_embed: ["rail"], rail_h: ["rail"], L_brg: ["rail"],
  D_piv: ["pivot"], L_bush: ["pivot"], p_bush: ["pivot"], H_bush: ["pivot"], lev_piv: ["pivot"],
  BX: ["base"], BY: ["base"], t_base: ["base"], Fy: ["top", "bot", "rings", "ribs", "bars", "base"], FEXX: ["bars"], Nd: ["pawl", "bracket", "pivot"],
};
const PART_NAME = { load: "carga sobre la parrilla", top: "plancha superior 4a", bot: "plancha inferior 4b", rings: "almas 4d", ribs: "nervios 4e", hub: "cubo 4c", bars: "barras 4f",
  iface: "interfaz de giro (r efectivo)", cyl: "cilindros", shoe: "carros de empuje", pawl: "trinquetes", bracket: "ménsulas y pasadores", rail: "guías", pivot: "pivote y buje", base: "placa base" };

/* ---------- vistas 2D ---------- */
function geoStyle(C, hl, part, fill) {
  const on = hl && hl.includes(part);
  return { s: on ? C.accent : C.ink, w: on ? 2.4 : 1.1, f: on ? C.band : fill || "none", on };
}
function geoPlan(R, C, hl) {
  const P = R.P, W = 620, H = 540, k = Math.min(520 / P.BX, 440 / P.BY), cx = W / 2, cy = H / 2 + 6;
  const X = (x) => cx + x * k, Y = (y) => cy - y * k;
  let s = SV.open(W, H);
  const g = (p, f) => geoStyle(C, hl, p, f);
  let st = g("base", C.fill2); s += SV.rect(X(-P.BX / 2), Y(P.BY / 2), P.BX * k, P.BY * k, st.s, st.f, st.w);
  st = g("top", C.fill); const stb = g("bot");
  s += SV.circ(cx, cy, P.D_disc / 2 * k, st.on || stb.on ? C.accent : C.ink, st.on || stb.on ? C.band : C.fill, st.on || stb.on ? 2.4 : 1.6);
  st = g("rings"); for (const r of parseRings(P.rings)) s += SV.circ(cx, cy, r * k, st.on ? C.accent : C.mute, "none", st.on ? 2.2 : 1, st.on ? null : "5 4");
  st = g("ribs");
  for (let i = 0; i < P.N_rib; i++) { const a = 2 * Math.PI * i / P.N_rib; s += SV.line(X(P.D_hub / 2 * Math.cos(a)), Y(P.D_hub / 2 * Math.sin(a)), X(P.R_rib * Math.cos(a)), Y(P.R_rib * Math.sin(a)), st.on ? C.accent : C.mute, st.on ? 2.2 : 1, st.on ? null : "5 4"); }
  st = g("bars", C.fill2);
  for (let i = 0; i < P.N_bar; i++) { const a = Math.PI / P.N_bar + 2 * Math.PI * i / P.N_bar; s += SV.circ(X(P.R_bar * Math.cos(a)), Y(P.R_bar * Math.sin(a)), P.D_bar / 2 * k, st.s, st.on ? C.accent : C.fill2, st.w); }
  st = g("hub"); s += SV.circ(cx, cy, P.D_hub / 2 * k, st.s, st.f, st.w);
  st = g("pivot", C.fill2); s += SV.circ(cx, cy, P.D_piv / 2 * k, st.s, st.f, st.w);
  st = g("load"); s += SV.circ(cx, cy, P.D_load / 2 * k, st.on ? C.accent : C.force, "none", st.on ? 2.2 : 1, "10 4 2 4");
  s += SV.circ(X(P.e), cy, 4, C.force, C.force, 1) + SV.text(X(P.e) + 6, cy - 6, "CG", C, { size: 10.5, fill: C.force });
  st = g("iface"); if (st.on) s += SV.circ(cx, cy, P.r_eff * 1000 * k, C.accent, "none", 2.2, "3 3") + SV.text(cx, Y(P.r_eff * 1000) - 4, `r ef = ${nf(P.r_eff, 2)} m`, C, { anchor: "middle", size: 11, fill: C.accent });
  for (const sx of [1, -1]) {
    const yb = -sx * P.R_bar * Math.sin(R.th), yE = yb - sx * P.eye_off, yP = -sx * R.Ybrk;
    st = g("rail", C.fill2); s += SV.rect(X(sx * P.X_cyl - P.rail_w / 2), Y(425), P.rail_w * k, 850 * k, st.s, st.f, st.w);
    st = g("bracket", C.fill2); s += SV.rect(X(sx * P.X_cyl - P.gap_cheek / 2 - P.t_cheek), Y(yP + P.L_cheek / 2), (P.gap_cheek + 2 * P.t_cheek) * k, P.L_cheek * k, st.s, st.f, st.w);
    st = g("cyl", C.cyl);
    const yb1 = yP + sx * 370;
    s += SV.rect(X(sx * P.X_cyl - 70), Y(Math.max(yP + sx * 70, yb1)), 140 * k, 300 * k, st.s, st.on ? C.band : C.cyl, st.w);
    s += SV.rect(X(sx * P.X_cyl - P.D_rod / 2), Y(Math.max(yb1, yE)), P.D_rod * k, Math.abs(yE - yb1) * k, st.s, "none", st.w);
    st = g("shoe", C.shoe); s += SV.rect(X(sx * P.shoe_x0), Y(Math.max(yb + sx * 20, yb + sx * 20 - sx * 300)), sx * 130 * k, 300 * k, st.s, st.on ? C.band : C.shoe, st.w);
    st = g("pawl", C.pawl); s += SV.rect(X(sx * P.pawl_tip), Y(Math.max(yb, yb - sx * P.pawl_b)), sx * P.pawl_L * k, P.pawl_b * k, st.s, st.on ? C.band : C.pawl, st.w);
  }
  // cotas
  const dimH = (x1, x2, y, t) => SV.line(x1, y, x2, y, C.mute, 1) + SV.line(x1, y - 4, x1, y + 4, C.mute, 1) + SV.line(x2, y - 4, x2, y + 4, C.mute, 1) + SV.text((x1 + x2) / 2, y - 4, t, C, { anchor: "middle", size: 10.5, fill: C.mute });
  s += dimH(X(-P.BX / 2), X(P.BX / 2), Y(-P.BY / 2) + 16, `${nf(P.BX)} placa base`);
  s += dimH(X(-P.X_cyl), X(P.X_cyl), Y(P.BY / 2) - 10, `${nf(2 * P.X_cyl)} entre ejes de cilindros`);
  s += SV.text(X(-P.BX / 2) - 6, cy, `${nf(P.BY)}`, C, { anchor: "middle", size: 10.5, fill: C.mute, rot: -90 });
  s += SV.text(14, 18, `PLANTA · disco Ø${nf(P.D_disc)} · ${P.N_bar} barras Ø${P.D_bar} en R${nf(P.R_bar)} · ${P.N_rib} nervios`, C, { size: 12, weight: 600 });
  return s + "</svg>";
}
function geoElev(R, C, hl) {
  const P = R.P, W = 620, H = 300, k = 480 / P.BX, cx = W / 2 - 20, zb = H - 70;
  const X = (x) => cx + x * k, Z = (z) => zb - z * k * 2.2;    // escala vertical ×2,2
  const g = (p, f) => geoStyle(C, hl, p, f), TD = R.TD, Rd = P.D_disc / 2, t0 = P.t_base, t1 = t0 + P.t_bot, t2 = t1 + P.gap, t3 = t2 + P.t_top;
  let s = SV.open(W, H), st;
  st = g("base", C.fill2); s += SV.rect(X(-P.BX / 2), Z(t0), P.BX * k, Z(0) - Z(t0), st.s, st.f, st.w);
  st = g("bot", C.fill2); s += SV.rect(X(-Rd), Z(t1), 2 * Rd * k, Z(t0) - Z(t1), st.s, st.on ? C.band : C.fill2, st.w);
  st = g("top", C.fill2); s += SV.rect(X(-Rd), Z(t3), 2 * Rd * k, Z(t2) - Z(t3), st.s, st.on ? C.band : C.fill2, st.w);
  st = g("ribs"); s += SV.rect(X(P.D_hub / 2), Z(t2), (P.R_rib - P.D_hub / 2) * k, Z(t1) - Z(t2), st.on ? C.accent : C.mute, st.on ? C.band : "none", st.on ? 2 : 0.8, "4 3") + SV.rect(X(-P.R_rib), Z(t2), (P.R_rib - P.D_hub / 2) * k, Z(t1) - Z(t2), st.on ? C.accent : C.mute, st.on ? C.band : "none", st.on ? 2 : 0.8, "4 3");
  st = g("rings"); for (const r of parseRings(P.rings)) for (const sg of [1, -1]) s += SV.rect(X(sg * r - P.t_ring / 2), Z(t2), P.t_ring * k, Z(t1) - Z(t2), st.s, st.on ? C.accent : C.ink, st.w * 0.6);
  st = g("bars"); const xb = R.a; for (const sg of [1, -1]) s += SV.rect(X(sg * xb - P.D_bar / 2), Z(t3), P.D_bar * k, Z(t0) - Z(t3), st.s, st.on ? C.band : "none", st.w, "3 2");
  st = g("hub", C.fill); s += SV.rect(X(-P.D_hub / 2), Z(t3), P.D_hub * k, Z(t0) - Z(t3), st.s, st.on ? C.band : C.fill, st.w);
  st = g("pivot"); s += SV.rect(X(-P.D_piv / 2), Z(t3 - 20), P.D_piv * k, Z(0) - Z(t3 - 20), st.s, st.on ? C.band : "none", st.w, "4 3");
  st = g("load"); s += SV.rect(X(-P.D_load / 2), Z(t3 + 40), P.D_load * k, Z(t3) - Z(t3 + 40), st.on ? C.accent : C.force, "none", st.on ? 2 : 1, "8 4");
  s += SV.arrow(X(P.e), Z(t3 + 110), X(P.e), Z(t3 + 42), C.force, 2.4) + SV.text(X(P.e) + 6, Z(t3 + 90), `W = ${nf(P.W_tf)} tf (e = ${nf(P.e)})`, C, { size: 10.5, fill: C.force });
  for (const sx of [1, -1]) {
    const za = t0 + P.h_axis;
    st = g("rail", C.fill2); s += SV.rect(X(sx * P.X_cyl - P.rail_w / 2), Z(t0 + P.rail_h), P.rail_w * k, Z(t0 - P.rail_embed) - Z(t0 + P.rail_h), st.s, st.f, st.w);
    st = g("cyl"); s += SV.circ(X(sx * P.X_cyl), Z(za), 70 * k * 1.5, st.s, st.on ? C.band : "none", st.w, "4 3");
    st = g("shoe"); s += SV.rect(X(sx * P.shoe_x0), Z(za + 70), sx * 130 * k, Z(t0) - Z(za + 70), st.s, st.on ? C.band : "none", st.w, "4 3");
    st = g("bracket"); s += SV.rect(X(sx * P.X_cyl - P.gap_cheek / 2 - P.t_cheek), Z(za + 70), (P.gap_cheek + 2 * P.t_cheek) * k, Z(t0) - Z(za + 70), st.s, "none", st.w, "2 2");
  }
  // cotas verticales (lado derecho)
  const xr = X(-P.BX / 2) - 22;
  const dimV = (z1, z2, t, x) => SV.line(x, Z(z1), x, Z(z2), C.mute, 1) + SV.line(x - 3, Z(z1), x + 3, Z(z1), C.mute, 1) + SV.line(x - 3, Z(z2), x + 3, Z(z2), C.mute, 1) + SV.text(x + 4, (Z(z1) + Z(z2)) / 2 + 4, t, C, { size: 10, fill: C.mute });
  const xd = X(P.BX / 2) + 12;
  s += dimV(0, t0, nf(P.t_base), xr) + dimV(t0, t1, nf(P.t_bot), xd) + dimV(t1, t2, nf(P.gap), xd) + dimV(t2, t3, nf(P.t_top), xd) + dimV(t0, t3, `TD ${nf(TD)}`, xd + 34);
  s += SV.text(14, 18, "ELEVACIÓN – CORTE A-A POR EL EJE X", C, { size: 12, weight: 600 }) + SV.text(14, 34, "escala vertical ×2,2 para leer espesores", C, { size: 10.5, fill: C.mute });
  return s + "</svg>";
}
function geoEdge(R, C, hl) {
  const P = R.P, rl = parseRings(P.rings), Rd = P.D_disc / 2, r0 = (rl.length ? rl[rl.length - 1] : P.R_bar - 200) - 70, r1 = Rd + 70;
  const W = 620, H = 320, k = Math.min((W - 110) / (r1 - r0), 200 / (R.TD + 50)), x0 = 40, zb = H - 50;
  const X = (r) => x0 + (r - r0) * k, Z = (z) => zb - z * k;
  const g = (p, f) => geoStyle(C, hl, p, f), t0 = 40, t1 = t0 + P.t_bot, t2 = t1 + P.gap, t3 = t2 + P.t_top;
  let s = SV.open(W, H), st;
  st = g("base", C.fill2); s += SV.rect(X(r0), Z(t0), (r1 - r0) * k, Z(0) - Z(t0), st.s, st.f, st.w);
  s += SV.text(X(r0) + 6, Z(t0 / 2) + 4, `placa base e=${P.t_base} (parcial)`, C, { size: 10.5, fill: C.mute });
  const hx0 = P.R_bar - P.D_hole / 2, hx1 = P.R_bar + P.D_hole / 2;
  for (const [p, za, zz, lab] of [["bot", t0, t1, `4b e=${P.t_bot}`], ["top", t2, t3, `4a e=${P.t_top}`]]) {
    st = g(p, C.fill2);
    s += SV.rect(X(r0), Z(zz), (hx0 - r0) * k, Z(za) - Z(zz), st.s, st.on ? C.band : C.fill2, st.w) + SV.rect(X(hx1), Z(zz), (Rd - hx1) * k, Z(za) - Z(zz), st.s, st.on ? C.band : C.fill2, st.w);
    s += SV.text(X(r0) + 6, (Z(za) + Z(zz)) / 2 + 4, lab, C, { size: 10.5, fill: st.on ? C.accent : C.ink, weight: st.on ? 600 : null });
  }
  if (rl.length) { const rr = rl[rl.length - 1]; st = g("rings", C.fill); s += SV.rect(X(rr - P.t_ring / 2), Z(t2), P.t_ring * k, Z(t1) - Z(t2), st.s, st.on ? C.band : C.fill, st.w) + SV.text(X(rr + P.t_ring / 2) + 4, Z(t1) - 8, `alma R${nf(rr)} e=${P.t_ring}`, C, { size: 10.5, fill: st.on ? C.accent : C.mute }); }
  st = g("ribs"); if (P.R_rib > r0) s += SV.rect(X(Math.max(r0, rl.length ? rl[rl.length - 1] + P.t_ring / 2 : r0)), Z(t2), (P.R_rib - Math.max(r0, rl.length ? rl[rl.length - 1] + P.t_ring / 2 : r0)) * k, Z(t1) - Z(t2), st.on ? C.accent : C.mute, st.on ? C.band : "none", st.on ? 2 : 0.8, "4 3");
  st = g("bars", C.fill);
  s += SV.rect(X(P.R_bar - P.D_bar / 2), Z(t3), P.D_bar * k, Z(t0) - Z(t3), st.s, st.on ? C.band : C.fill, st.w);
  const sb = P.weld_S * k;
  for (const [zf, sg] of [[t3, 1], [t0, -1]]) for (const xe of [X(P.R_bar - P.D_bar / 2), X(P.R_bar + P.D_bar / 2)]) { const dir = xe < X(P.R_bar) ? -1 : 1; s += SV.pgon([[xe, Z(zf)], [xe + dir * sb, Z(zf)], [xe, Z(zf) + sg * sb]], st.s, st.s, 1); }
  st = g("iface"); s += SV.line(X(r0), Z(t0), X(Rd), Z(t0), st.on ? C.accent : C.react, st.on ? 3 : 2, "6 3");
  s += SV.text(X(Rd) - 4, Z(t0) + 16, `grasa grafitada · μ ${nf(P.mu, 2)}`, C, { anchor: "end", size: 10.5, fill: st.on ? C.accent : C.react });
  const dimV = (z1, z2, t, x) => SV.line(x, Z(z1), x, Z(z2), C.mute, 1) + SV.line(x - 3, Z(z1), x + 3, Z(z1), C.mute, 1) + SV.line(x - 3, Z(z2), x + 3, Z(z2), C.mute, 1) + SV.text(x + 5, (Z(z1) + Z(z2)) / 2 + 4, t, C, { size: 10.5, fill: C.mute });
  s += dimV(t0, t1, nf(P.t_bot), X(Rd) + 8) + dimV(t1, t2, nf(P.gap), X(Rd) + 8) + dimV(t2, t3, nf(P.t_top), X(Rd) + 8) + dimV(t0, t3, nf(R.TD), X(Rd) + 40);
  s += SV.line(X(P.R_bar - P.D_bar / 2), Z(t3) - 14, X(P.R_bar + P.D_bar / 2), Z(t3) - 14, C.mute, 1) + SV.text(X(P.R_bar), Z(t3) - 18, `Ø${P.D_bar} · bisel ${P.weld_S}`, C, { anchor: "middle", size: 10.5, fill: C.mute });
  s += SV.line(X(P.R_bar), Z(t0) + 4, X(P.R_bar), Z(t3) - 4, C.mute, 0.8, "8 3 2 3");
  s += SV.text(14, 18, "DETALLE – BORDE DEL DISCO (corte por una barra)", C, { size: 12, weight: 600 });
  return s + "</svg>";
}

/* ---------- 3D (three.js r147) ---------- */
function Geo3D(host) {
  this.host = host; this.ok = !!window.THREE;
  if (!this.ok) return;
  try {
    this.ren = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  } catch (e) { this.ok = false; return; }
  this.ren.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  host.appendChild(this.ren.domElement);
  this.scene = new THREE.Scene();
  this.cam = new THREE.PerspectiveCamera(35, 1.6, 10, 40000);
  this.cam.position.set(2350, 1850, 2550);
  this.ctl = new THREE.OrbitControls(this.cam, this.ren.domElement);
  this.ctl.target.set(0, 120, 0); this.ctl.enableDamping = false; this.ctl.update();
  this.ctl.addEventListener("change", () => this.draw());
  this.scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 0.85));
  const dl = new THREE.DirectionalLight(0xffffff, 0.75); dl.position.set(2000, 4000, 1500); this.scene.add(dl);
  const dl2 = new THREE.DirectionalLight(0xffffff, 0.3); dl2.position.set(-2500, 1500, -2000); this.scene.add(dl2);
  this.grp = new THREE.Group(); this.scene.add(this.grp);
  this.parts = {}; this.topMode = "trans";
  new ResizeObserver(() => this.resize()).observe(host);
  this.resize();
}
Geo3D.prototype = {
  resize() { if (!this.ok) return; const w = this.host.clientWidth || 600, h = Math.max(280, Math.round(w * 0.62)); this.ren.setSize(w, h); this.cam.aspect = w / h; this.cam.updateProjectionMatrix(); this.draw(); },
  draw() { if (this.ok) this.ren.render(this.scene, this.cam); },
  mat(hex, part, opt) {
    const m = new THREE.MeshStandardMaterial(Object.assign({ color: hex, metalness: 0.25, roughness: 0.62 }, opt || {}));
    m.userData.base = hex; (this.parts[part] = this.parts[part] || []).push(m); return m;
  },
  add(geo, m, x, z, y) { const me = new THREE.Mesh(geo, m); me.position.set(x || 0, z || 0, -(y || 0)); this.grp.add(me); return me; },
  ringShape(ro, ri, holes) {
    const sh = new THREE.Shape(); sh.absarc(0, 0, ro, 0, Math.PI * 2, false);
    const h = new THREE.Path(); h.absarc(0, 0, ri, 0, Math.PI * 2, true); sh.holes.push(h);
    for (const [x, y, r] of holes || []) { const p = new THREE.Path(); p.absarc(x, y, r, 0, Math.PI * 2, true); sh.holes.push(p); }
    return sh;
  },
  extr(shape, depth, segs) { const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false, curveSegments: segs || 64 }); g.rotateX(-Math.PI / 2); return g; },
  build(R, C) {
    if (!this.ok) return;
    const P = R.P; this.parts = {};
    while (this.grp.children.length) { const o = this.grp.children.pop(); o.geometry && o.geometry.dispose(); }
    this.scene.background = new THREE.Color(C.bg);
    const t0 = P.t_base, t1 = t0 + P.t_bot, t2 = t1 + P.gap, t3 = t2 + P.t_top, Rd = P.D_disc / 2, rh = P.D_hub / 2;
    const holes = []; for (let i = 0; i < P.N_bar; i++) { const a = Math.PI / P.N_bar + 2 * Math.PI * i / P.N_bar; holes.push([P.R_bar * Math.cos(a), P.R_bar * Math.sin(a), P.D_hole / 2]); }
    this.add(new THREE.BoxGeometry(P.BX, P.t_base, P.BY), this.mat(0x8f9aa3, "base"), 0, t0 / 2, 0);
    this.add(this.extr(this.ringShape(Rd, rh, holes), P.t_bot), this.mat(0x6d8fb3, "bot"), 0, t0, 0);
    const mt = this.mat(0x7fa0c4, "top", { transparent: true, opacity: 0.32, depthWrite: false });
    this.topMesh = this.add(this.extr(this.ringShape(Rd, rh, holes), P.t_top), mt, 0, t2, 0);
    const mr = this.mat(0xc9a35a, "rings");
    for (const r of parseRings(P.rings)) this.add(this.extr(this.ringShape(r + P.t_ring / 2, r - P.t_ring / 2), P.gap), mr, 0, t1, 0);
    const mb = this.mat(0xd9b46e, "ribs");
    for (let i = 0; i < P.N_rib; i++) {
      const a = 2 * Math.PI * i / P.N_rib, L = P.R_rib - rh, rc = rh + L / 2;
      const me = this.add(new THREE.BoxGeometry(L, P.gap, P.t_rib), mb, rc * Math.cos(a), t1 + P.gap / 2, rc * Math.sin(a)); me.rotation.y = a;
    }
    const mbar = this.mat(0x3d4650, "bars"), gb = new THREE.CylinderGeometry(P.D_bar / 2, P.D_bar / 2, R.TD, 20);
    for (const [x, y] of holes) this.add(gb, mbar, x, t0 + R.TD / 2, y);
    this.add(new THREE.CylinderGeometry(rh, rh, R.TD, 40), this.mat(0x58626c, "hub"), 0, t0 + R.TD / 2, 0);
    this.add(new THREE.CylinderGeometry(P.D_piv / 2, P.D_piv / 2, t3 + 25, 32), this.mat(0xb8c0c7, "pivot"), 0, (t3 + 25) / 2, 0);
    // carga y radio efectivo
    const ml = this.mat(0xe06a3a, "load", { transparent: true, opacity: 0.18, depthWrite: false });
    this.add(new THREE.CylinderGeometry(P.D_load / 2, P.D_load / 2, 30, 64), ml, 0, t3 + 60, 0);
    const mcg = this.mat(0xc0392b, "load"); this.add(new THREE.SphereGeometry(35, 20, 14), mcg, P.e, t3 + 120, 0);
    const mi = this.mat(0x13a08d, "iface"), ti = new THREE.TorusGeometry(P.r_eff * 1000, 9, 8, 96); ti.rotateX(Math.PI / 2); this.add(ti, mi, 0, t0 + 2, 0);
    // accionamiento
    const za = t0 + P.h_axis;
    for (const sx of [1, -1]) {
      const yb = -sx * P.R_bar * Math.sin(R.th), yE = yb - sx * P.eye_off, yP = -sx * R.Ybrk, xc = sx * P.X_cyl;
      this.add(new THREE.BoxGeometry(P.rail_w, P.rail_h, 850), this.mat(0x9aa4ad, "rail"), xc, t0 + P.rail_h / 2, 0);
      const mbk = this.mat(0x7c8792, "bracket"), hc = za + 70 - t0;
      for (const sd of [1, -1]) this.add(new THREE.BoxGeometry(P.t_cheek, hc, P.L_cheek), mbk, xc + sd * (P.gap_cheek / 2 + P.t_cheek / 2), t0 + hc / 2, yP);
      this.add(new THREE.BoxGeometry(P.gap_cheek + 2 * P.t_cheek, hc, 40), mbk, xc, t0 + hc / 2, yP - sx * (P.L_cheek / 2 + 20));
      const pin = new THREE.CylinderGeometry(P.D_pin / 2, P.D_pin / 2, P.gap_cheek + 2 * P.t_cheek + 40, 20); pin.rotateZ(Math.PI / 2); this.add(pin, mbk, xc, za, yP);
      const mc = this.mat(0x2f5fb3, "cyl");
      const body = new THREE.CylinderGeometry(70, 70, 300, 32); body.rotateX(Math.PI / 2); this.add(body, mc, xc, za, yP + sx * 220);
      const Lr = Math.abs(yE - (yP + sx * 370)), rod = new THREE.CylinderGeometry(P.D_rod / 2, P.D_rod / 2, Lr, 24); rod.rotateX(Math.PI / 2);
      this.add(rod, this.mat(0xc9d1d8, "cyl", { metalness: 0.6, roughness: 0.3 }), xc, za, (yE + yP + sx * 370) / 2);
      const shoeH = za + 70 - t0, ys = yb + sx * 20 - sx * 150;
      this.add(new THREE.BoxGeometry(130, shoeH, 300), this.mat(0xb08a52, "shoe"), sx * (P.shoe_x0 + 65), t0 + shoeH / 2, ys);
      this.add(new THREE.BoxGeometry(P.pawl_L, P.pawl_h, P.pawl_b), this.mat(0xe0a63c, "pawl"), sx * (P.pawl_tip + P.pawl_L / 2), za, yb - sx * P.pawl_b / 2);
    }
    this.setTop(this.topMode);
    this.highlight(this.hl || []);
  },
  setTop(mode) {
    this.topMode = mode; if (!this.topMesh) return;
    this.topMesh.visible = mode !== "hide";
    const m = this.topMesh.material; m.transparent = mode === "trans"; m.opacity = mode === "trans" ? 0.32 : 1; m.depthWrite = mode !== "trans"; m.needsUpdate = true;
    this.draw();
  },
  highlight(parts) {
    this.hl = parts;
    if (!this.ok) return;
    for (const [p, ms] of Object.entries(this.parts)) for (const m of ms) {
      const on = parts.includes(p);
      m.color.setHex(on ? 0xff7a1a : m.userData.base);
      m.emissive && m.emissive.setHex(on ? 0x5a2200 : 0x000000);
    }
    this.draw();
  },
  view(name) {
    const v = { iso: [2350, 1850, 2550], top: [0, 3900, 1], front: [0, 380, 3500], side: [3500, 380, 0] }[name];
    this.cam.position.set(...v); this.ctl.target.set(0, 120, 0); this.ctl.update(); this.draw();
  },
};
