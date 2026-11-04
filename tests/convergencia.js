#!/usr/bin/env node
/* TT300-C · Auditoría numérica del núcleo: convergencia de malla, consistencia, interfaces, optimizador, reproducibilidad.
   Ejecutar:  node tests/convergencia.js            (≈ 3 min; mallas hasta h/4)
              node tests/convergencia.js --quick    (sin FEA en el barrido de parámetros; ≈ 1,7 min)
              node tests/convergencia.js --full     (agrega la malla h/8 de las planchas de la mesa: +2 min y ≈ 1,3 GB de RAM)
              node tests/convergencia.js --only=A,B (secciones: A bench, B mesh, C núcleo, D interfaces, E optimizador, F repro, G aceptación)
   Imprime tablas «prueba → criterio → resultado → veredicto», la lista de hallazgos y «RESULTADO: …».
   Código de salida 0 si no hay hallazgos críticos ni importantes; 1 en caso contrario.
   Solo lee packages/ y tests/golden; no escribe nada.  Unidades: N, mm, MPa (salidas en kN, kg, bar como la herramienta). */
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const FEA = require("../packages/core/fea.js"), TT = require("../packages/core/tt300c.js"), AG = require("../packages/agents/agentes.js");

const ARGV = process.argv.slice(2), QUICK = ARGV.includes("--quick"), FULL = ARGV.includes("--full");
const ONLY = (ARGV.find((a) => a.startsWith("--only=")) || "").slice(7).split(",").filter(Boolean);
const want = (s) => !ONLY.length || ONLY.includes(s);
const D2R = Math.PI / 180, G = 9.80665;
const T_START = Date.now();

/* ------------------------------------------------------------------ registro de resultados ------------------------------------------------------------------ */
const rows = [], hall = [];
let curSec = "";
const f = (x, d = 2) => (typeof x !== "number" || !isFinite(x)) ? String(x) : x.toFixed(d).replace(".", ",");
const pct = (x, d = 2) => f(x * 100, d) + " %";
const sci = (x) => (typeof x !== "number" || !isFinite(x)) ? String(x) : x.toExponential(1).replace(".", ",");
/* st: "OK" | "obs" | "falla".  h = {sev:"crítica"|"importante"|"menor", id, titulo, correccion} se registra si st ≠ OK */
function chk(prueba, criterio, resultado, st, h) {
  rows.push({ sec: curSec, prueba, criterio, resultado, st });
  if (st !== "OK" && h) {
    if (!hall.some((x) => x.id === h.id)) hall.push(Object.assign({ detalle: prueba + " — " + resultado }, h));
  } else if (st === "falla" && !h) {
    hall.push({ sev: "importante", id: "auto:" + prueba, titulo: prueba, detalle: resultado, correccion: "(revisar)" });
  }
}
const V = (ok, obsOnly) => ok ? "OK" : (obsOnly ? "obs" : "falla");
function section(code, title) { curSec = code + " · " + title; console.log("\n## " + curSec); }
function printTable(from) {
  console.log("| Prueba | Criterio | Resultado | Veredicto |\n|---|---|---|---|");
  for (let i = from; i < rows.length; i++) { const r = rows[i]; console.log(`| ${r.prueba} | ${r.criterio} | ${r.resultado} | ${r.st === "OK" ? "OK" : r.st === "obs" ? "observación" : "FALLA"} |`); }
}
function table(headers, data) {
  console.log("| " + headers.join(" | ") + " |\n|" + headers.map(() => "---").join("|") + "|");
  data.forEach((r) => console.log("| " + r.join(" | ") + " |"));
}
const rel = (a, b) => Math.abs(a - b) / Math.max(Math.abs(b), 1e-300);
const maxOf = (a) => a.reduce((m, x) => Math.max(m, x), -Infinity);
const minOf = (a) => a.reduce((m, x) => Math.min(m, x), Infinity);
function runSection(code, title, fn) {
  if (!want(code)) return;
  section(code, title);
  const i0 = rows.length, t0 = Date.now();
  try { fn(); } catch (e) { chk("Excepción en la sección " + code, "sin excepciones", e.stack.split("\n").slice(0, 3).join(" / "), "falla", { sev: "importante", id: "exc:" + code, titulo: "Excepción no controlada en la sección " + code, correccion: "ver traza" }); }
  console.log("\nVeredictos de la sección " + code + " (" + ((Date.now() - t0) / 1000).toFixed(1) + " s):");
  printTable(i0);
}

/* orden observado y Richardson con tres niveles (h decreciente; razón de h no necesariamente 2) */
function obsOrder(h, v) {
  const n = h.length, [h1, h2, h3] = h.slice(n - 3), [v1, v2, v3] = v.slice(n - 3);
  const d12 = v1 - v2, d23 = v2 - v3;
  if (!(d12 * d23 > 0)) return { p: NaN, vinf: NaN, mono: false, ratio: Math.abs(d23 / d12) };
  const g = (p) => d12 / d23 - (h1 ** p - h2 ** p) / (h2 ** p - h3 ** p);
  let lo = 0.02, hi = 8;
  if (g(lo) * g(hi) > 0) return { p: NaN, vinf: NaN, mono: true, ratio: Math.abs(d23 / d12) };
  for (let i = 0; i < 80; i++) { const m = (lo + hi) / 2; if (g(lo) * g(m) <= 0) hi = m; else lo = m; }
  const p = (lo + hi) / 2, C = (v2 - v3) / (h2 ** p - h3 ** p);
  return { p, vinf: v3 - C * h3 ** p, mono: true, ratio: Math.abs(d23 / d12) };
}
const richardsonP = (h, v, p) => { const n = v.length, a = h[n - 2] ** p, b = h[n - 1] ** p; return v[n - 1] - (v[n - 2] - v[n - 1]) / (a - b) * b; };

/* =================================================================================================================================================
   A · BENCHMARKS DEL MOTOR FEA
   ================================================================================================================================================= */
function plateSq(n, bc, o) {
  o = Object.assign({ a: 1000, t: 10, E: 2e5, nu: 0.3, q: 0.01, unit: 1 }, o || {});
  const nodes = [], elems = [], u = o.unit;
  for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) nodes.push([i * o.a / n * u, j * o.a / n * u]);
  const id = (i, j) => i * (n + 1) + j;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
  const wFix = [], betaN = [], clamp = [];
  for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) {
    if (!(i === 0 || i === n || j === 0 || j === n)) continue;
    if (bc === "C") clamp.push(id(i, j));
    else {
      wFix.push(id(i, j));
      if (o.testCorners) betaN.push(i === 0 || i === n ? [id(i, j), 0, 1] : [id(i, j), 1, 0]);   // como tests/test_tt300c.js: en las esquinas solo una rotación (asimetría ≈ 1e-5)
      else { if (i === 0 || i === n) betaN.push([id(i, j), 0, 1]); if (j === 0 || j === n) betaN.push([id(i, j), 1, 0]); }   // apoyo duro simétrico: ambas rotaciones tangenciales en las esquinas
    }
  }
  return { id, m: { nodes, elems, t: o.t * u, E: o.E / u / u, nu: o.nu, q: new Float64Array(elems.length).fill(o.q / u / u), wFix, betaN, clamp }, o };
}
/* Navier para placa cuadrada simplemente apoyada: Kirchhoff y Reissner–Mindlin (apoyo "duro": w = 0, β_t = 0, M_n = 0), k_s = 5/6 */
function navier(a, t, E, nu, q) {
  const D = E * t ** 3 / (12 * (1 - nu * nu)), G_ = E / (2 * (1 + nu)), ks = 5 / 6;
  let wK = 0, wM = 0, Mx = 0, My = 0, Mxy = 0;
  for (let m = 1; m <= 399; m += 2) for (let n = 1; n <= 399; n += 2) {
    const qmn = 16 * q / (Math.PI ** 2 * m * n), k2 = (Math.PI / a) ** 2 * (m * m + n * n), s = Math.sin(m * Math.PI / 2) * Math.sin(n * Math.PI / 2);
    const w1 = qmn / (D * k2 * k2);
    wK += w1 * s; wM += (w1 + qmn / (ks * G_ * t * k2)) * s;
    Mx += D * w1 * (Math.PI / a) ** 2 * (m * m + nu * n * n) * s; My += D * w1 * (Math.PI / a) ** 2 * (n * n + nu * m * m) * s;
  }
  return { D, wK, wM, Mx, My };
}
function cantilever(ny, ratio, consistent) {
  const L = 1000, h = 100, nx = ny * ratio, N = [], E = [];
  for (let i = 0; i <= nx; i++) for (let j = 0; j <= ny; j++) N.push([i * L / nx, j * h / ny]);
  const id = (i, j) => i * (ny + 1) + j;
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) E.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
  const fix = []; for (let j = 0; j <= ny; j++) fix.push([id(0, j), 0], [id(0, j), 1]);
  const loads = []; for (let j = 0; j <= ny; j++) loads.push([id(nx, j), 0, -1000 * (consistent ? ((j === 0 || j === ny) ? 0.5 : 1) / ny : 1 / (ny + 1))]);
  const r = FEA.planeStress({ nodes: N, elems: E, t: 10, E: 2e5, nu: 0.3, fix, loads });
  // tensión en la fila superior de elementos, a media luz (x = L/2): la sección es regular (lejos del empotramiento singular)
  const iMid = nx / 2 - 1, eTop = r.el[iMid * ny + ny - 1];
  const xc = (iMid + 0.5) * L / nx, yc = h - h / ny / 2, I = 10 * h ** 3 / 12;
  return { r, tip: -r.u[2 * id(nx, ny / 2) + 1], sxMid: eTop.sx, sxBeam: 1000 * (L - xc) * (yc - h / 2) / I, vmRoot: maxOf(r.el.slice(0, ny).map((e) => e.vm)), nx };
}

runSection("A", "Benchmarks del motor FEA (fea.js: MITC4 y Q4)", () => {
  // ---- A0: reproducir los tres benchmarks obligatorios de tests/test_tt300c.js
  { const { id, m } = plateSq(20, "SS", { testCorners: true }), r = FEA.plate(m), D = 2e5 * 1000 / (12 * 0.91);
    const e = rel(r.w[id(10, 10)], 0.00406 * 0.01 * 1e12 / D);
    chk("A0 · Placa SS 20×20, flecha central vs 0,00406·qa⁴/D (test obligatorio)", "error < 0,5 %", pct(e, 3), V(e < 0.005));
    chk("A0 · Equilibrio ΣF = ΣR (placa SS 20×20)", "< 0,5 %", sci(rel(Math.abs(r.Rsum), r.Fapplied)), V(rel(Math.abs(r.Rsum), r.Fapplied) < 0.005)); }
  { const L = 1000, h = 100, nx = 80, ny = 10, N = [], E = [];
    for (let i = 0; i <= nx; i++) for (let j = 0; j <= ny; j++) N.push([i * L / nx, j * h / ny]);
    const id = (i, j) => i * (ny + 1) + j;
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) E.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
    const fix = [], loads = []; for (let j = 0; j <= ny; j++) { fix.push([id(0, j), 0], [id(0, j), 1]); loads.push([id(nx, j), 0, -1000 / (ny + 1)]); }
    const r = FEA.planeStress({ nodes: N, elems: E, t: 10, E: 2e5, nu: 0.3, fix, loads }), tip = -r.u[2 * id(nx, ny / 2) + 1];
    chk("A0 · Voladizo Q4 80×10, flecha de punta vs 2,026 mm (test obligatorio)", "error < 2 %", `${f(tip, 4)} mm; ${pct(rel(tip, 2.026), 2)}`, V(rel(tip, 2.026) < 0.02));
    const sumR = r.reac.filter(([, d]) => d === 1).reduce((s, x) => s + x[2], 0);
    chk("A0 · Equilibrio ΣF = ΣR (voladizo Q4)", "< 0,5 %", sci(rel(Math.abs(sumR), 1000)), V(rel(Math.abs(sumR), 1000) < 0.005)); }

  // ---- A1: placa SS: convergencia vs Navier (Kirchhoff y Mindlin)
  const ns = [4, 8, 16, 32, 64], A1 = [];
  const nav = navier(1000, 10, 2e5, 0.3, 0.01);
  for (const n of ns) {
    const { id, m } = plateSq(n, "SS"), r = FEA.plate(m), c = id(n / 2, n / 2);
    // momento en el centro: media de los 4 elementos que comparten el nodo central (error O(h²))
    const els = [[n / 2 - 1, n / 2 - 1], [n / 2, n / 2 - 1], [n / 2 - 1, n / 2], [n / 2, n / 2]].map(([i, j]) => r.el[i * n + j].M);
    const Mc = els.reduce((s, M) => s + (M[0] + M[1]) / 2, 0) / 4;
    A1.push({ n, h: 1000 / n, w: r.w[c], Mc, eq: rel(Math.abs(r.Rsum), r.Fapplied), sym: maxOf(Array.from(r.w).map((w, k) => { const i = Math.floor(k / (n + 1)), j = k % (n + 1); return Math.abs(w - r.w[id(j, i)]); })) / maxOf(Array.from(r.w)) });
  }
  const eW = A1.map((a) => Math.abs(a.w - nav.wM) / nav.wM), eM = A1.map((a) => Math.abs(a.Mc - nav.Mx) / nav.Mx);
  const pW = Math.log(eW[2] / eW[3]) / Math.log(2), pW2 = Math.log(eW[3] / eW[4]) / Math.log(2), pM = Math.log(eM[2] / eM[3]) / Math.log(2);
  console.log("\nA1 · Placa cuadrada simplemente apoyada, a = 1000, t = 10, ν = 0,3, q = 0,01 MPa. Navier: w_Kirchhoff = " + f(nav.wK, 5) + " mm (0,00406 qa⁴/D → " + f(0.00406 * 0.01 * 1e12 / nav.D, 5) + "), w_Mindlin = " + f(nav.wM, 5) + " mm, M_c = " + f(nav.Mx, 2) + " N·mm/mm (0,0479 qa² = " + f(0.0479 * 0.01 * 1e6, 2) + ")");
  table(["n", "h [mm]", "w_c [mm]", "error vs Mindlin", "error vs Kirchhoff", "M_c [N·mm/mm]", "error M_c", "|ΣR/ΣF − 1|", "asimetría w(i,j)−w(j,i)"],
    A1.map((a, i) => [a.n, f(a.h, 1), f(a.w, 5), pct(eW[i], 3), pct(Math.abs(a.w - nav.wK) / nav.wK, 3), f(a.Mc, 2), pct(eM[i], 3), sci(a.eq), sci(a.sym)]));
  chk("A1 · Placa SS: orden de convergencia de la flecha (n = 16→32→64)", "p ≥ 1,8 (teórico 2)", `p = ${f(pW, 2)} (16→32), ${f(pW2, 2)} (32→64); error n = 32: ${pct(eW[3], 3)}`, V(pW >= 1.8 && pW2 >= 1.8));
  chk("A1 · Placa SS: error de la flecha con n = 32 vs Navier-Mindlin", "< 0,5 %", pct(eW[3], 3), V(eW[3] < 0.005));
  chk("A1 · Placa SS: momento central, orden y error (n = 32)", "p ≥ 1,8; error < 1 %", `p = ${f(pM, 2)}; ${pct(eM[3], 3)}`, V(pM >= 1.8 && eM[3] < 0.01));
  chk("A1 · Placa SS: simetría de la solución (w(i,j) = w(j,i)) y equilibrio", "asimetría < 1e-9; ΣR/ΣF dentro de 1e-6", `asim. máx ${sci(maxOf(A1.map((a) => a.sym)))}; |ΣR/ΣF−1| máx ${sci(maxOf(A1.map((a) => a.eq)))}`, V(maxOf(A1.map((a) => a.sym)) < 1e-9 && maxOf(A1.map((a) => a.eq)) < 1e-6));
  // bloqueo por cortante: placa delgada (a/t = 1000)
  { const out = [1, 4].map((t) => { const { id, m } = plateSq(16, "SS", { t }), r = FEA.plate(m), nv = navier(1000, t, 2e5, 0.3, 0.01); return Math.abs(r.w[id(8, 8)] - nv.wM) / nv.wM; });
    chk("A1 · Libre de bloqueo por cortante (n = 16; t = 1, a/t = 1000, y t = 4)", "error(t = 1) ≤ 2 × error(t = 10) = " + pct(2 * eW[2], 2), `t = 1: ${pct(out[0], 3)}; t = 4: ${pct(out[1], 3)}`, V(out[0] <= 2 * eW[2])); }

  // ---- A2: placa empotrada
  const A2 = [];
  for (const n of ns) {
    const { id, m } = plateSq(n, "C"), r = FEA.plate(m);
    A2.push({ n, h: 1000 / n, w: r.w[id(n / 2, n / 2)], vm: maxOf(r.el.map((e) => e.vmGauss)), eq: rel(Math.abs(r.Rsum), r.Fapplied) });
  }
  const wT = 0.00126 * 0.01 * 1e12 / nav.D, vmEdge = 6 * 0.0513 * 0.01 * 1e6 / 100 * Math.sqrt(1 - 0.3 + 0.09);
  const oW = obsOrder(A2.map((a) => a.h), A2.map((a) => a.w)), oV = obsOrder(A2.map((a) => a.h), A2.map((a) => a.vm));
  console.log("\nA2 · Placa cuadrada empotrada (mismos datos). Timoshenko y Woinowsky-Krieger: w_c = 0,00126 qa⁴/D = " + f(wT, 5) + " mm; M_borde = 0,0513 qa² → σ_vm borde = 6M/t²·√(1−ν+ν²) = " + f(vmEdge, 2) + " MPa");
  table(["n", "h [mm]", "w_c [mm]", "error vs T&WK", "σ_vm máx (Gauss) [MPa]", "error σ_vm vs borde exacto"], A2.map((a) => [a.n, f(a.h, 1), f(a.w, 5), pct(rel(a.w, wT), 3), f(a.vm, 3), pct(rel(a.vm, vmEdge), 2)]));
  chk("A2 · Placa empotrada: flecha central (n = 32) vs T&WK 0,00126", "error < 1 % (el coeficiente tabulado tiene 3 cifras: ±0,4 %)", pct(rel(A2[3].w, wT), 3), V(rel(A2[3].w, wT) < 0.01));
  chk("A2 · Placa empotrada: orden de convergencia de la flecha (16→32→64)", "p ≥ 1,8", `p = ${f(oW.p, 2)}; límite de Richardson ${f(oW.vinf, 5)} mm (${pct(rel(oW.vinf, wT), 2)} sobre T&WK, cortante de Mindlin)`, V(oW.p >= 1.8));
  chk("A2 · Placa empotrada: σ_vm máx en puntos de Gauss junto al borde empotrado", "orden observado ≈ 1 (la tensión se evalúa a 0,21 h del borde); Richardson dentro de 3 % del valor exacto", `p = ${f(oV.p, 2)}; Richardson ${f(oV.vinf, 2)} vs ${f(vmEdge, 2)} (${pct(rel(oV.vinf, vmEdge), 1)}); error n = 32: ${pct(rel(A2[3].vm, vmEdge), 1)}; n = 64: ${pct(rel(A2[4].vm, vmEdge), 1)}`, V(oV.p > 0.7 && rel(oV.vinf, vmEdge) < 0.03));
  chk("A2 · Equilibrio ΣF = ΣR (empotrada, 5 mallas)", "< 0,5 %", sci(maxOf(A2.map((a) => a.eq))), V(maxOf(A2.map((a) => a.eq)) < 0.005));

  // ---- A3: voladizo Q4
  const A3 = [2, 4, 8, 16, 32].map((ny) => { const c = cantilever(ny, 10, true); return Object.assign({ ny, h: 100 / ny }, c); });
  const refEB = 2.0, refTim = 1000 * 1000 ** 3 / (3 * 2e5 * 10 * 100 ** 3 / 12) + 1000 * 1000 / (5 / 6 * 76923.0769 * 1000), refTG = 2.0 + 1000 * 1000 * 100 ** 2 / (8 * 76923.0769 * 10 * 100 ** 3 / 12);
  const o3 = obsOrder(A3.map((a) => a.h), A3.map((a) => a.tip)), o3s = obsOrder(A3.map((a) => a.h), A3.map((a) => a.sxMid));
  console.log("\nA3 · Voladizo Q4 (L = 1000, h = 100, t = 10, P = 1 kN, ν = 0,3), elementos h × 1,0·h·(10:1 en x/y → relación de aspecto 1), cargas nodales consistentes. Referencias de la punta: viga Bernoulli " + f(refEB, 4) + "; Timoshenko (k = 5/6) " + f(refTim, 4) + "; elasticidad T&G (eje neutro) " + f(refTG, 4) + " mm");
  table(["elem. en h", "nodos de h", "δ punta [mm]", "error vs Timoshenko", "σ_x a media luz, fibra superior [MPa]", "error vs viga", "σ_vm máx en la raíz [MPa] (singular)"],
    A3.map((a) => [a.ny, f(a.h, 2), f(a.tip, 5), pct(rel(a.tip, refTim), 3), f(a.sxMid, 3), pct(rel(a.sxMid, a.sxBeam), 2), f(a.vmRoot, 1)]));
  chk("A3 · Voladizo: orden de convergencia de la flecha (8→16→32)", "p ≥ 1,8", `p = ${f(o3.p, 2)}; Richardson ${f(o3.vinf, 5)} mm`, V(o3.p >= 1.8));
  chk("A3 · Voladizo: flecha con ny = 32 vs Timoshenko / T&G", "error < 2 % (mandatorio)", `${pct(rel(A3[4].tip, refTim), 2)} / ${pct(rel(A3[4].tip, refTG), 2)} (el límite FE queda ≈ 0,2–0,4 % por debajo: empotramiento total impide el alabeo de la raíz)`, V(rel(A3[4].tip, refTim) < 0.02 && rel(A3[4].tip, refTG) < 0.02));
  chk("A3 · Referencia 2,026 mm del test obligatorio vs solución convergida", "referencia dentro de 0,3 % de la solución exacta (T&G 2,0195) o del límite FE", `2,026 es ${pct(2.026 / o3.vinf - 1, 2)} sobre el límite de Richardson (${f(o3.vinf, 4)} mm) y ${pct(2.026 / refTG - 1, 2)} sobre T&G; la malla 80×10 con cargas nodales iguales da 1,9970 mm (−${pct(1 - 1.997 / o3.vinf, 2)} del límite): el 1,43 % del test mezcla error de malla y de referencia`, V(Math.abs(2.026 / o3.vinf - 1) < 0.003, true), { sev: "menor", id: "ref-voladizo", titulo: "La referencia 2,026 mm del test del voladizo no es una solución exacta (límite FE 2,012 mm; T&G 2,0195 mm)", correccion: "tests/test_tt300c.js · test «voladizo»: usar 2.0156 (Timoshenko, k = 5/6) o 2.012 (límite FE) y tolerancia 1 %; cargas consistentes (½ en los nodos de esquina)" });
  chk("A3 · Voladizo: σ_x a media luz (zona regular) vs teoría de vigas", "error < 3 % con ny = 32", pct(rel(A3[4].sxMid, A3[4].sxBeam), 2), V(rel(A3[4].sxMid, A3[4].sxBeam) < 0.03));
  const rv = A3.map((a) => a.vmRoot);
  chk("A3 · Tensión en la raíz del voladizo (nodos totalmente empotrados)", "debe señalarse como singular (esquina empotrado–libre): crece con la malla; no usar como verificación", `σ_vm raíz = ${rv.map((x) => f(x, 1)).join(" → ")} MPa (teoría de vigas 60); diferencias crecientes: no converge`, "OK");

  // ---- A4: invariancia de unidades y cholesky
  { const a = plateSq(10, "SS"), b = plateSq(10, "SS", { unit: 1e-3, a: 1000 }), c = plateSq(10, "SS", { unit: 1e-3 });
    // (N, mm, MPa) vs (N, m, Pa): E→E·1e6, q→q·1e6, longitudes/1000
    const rA = FEA.plate(a.m), rB = FEA.plate(b.m);
    const dw = Math.abs(rA.w[a.id(5, 5)] * 1e-3 - rB.w[b.id(5, 5)]) / Math.abs(rB.w[b.id(5, 5)]);
    // tensión: M [N·mm/mm → N·m/m]: σ_vm [MPa → Pa]
    const sA = maxOf(rA.el.map((e) => e.vmGauss)) * 1e6, sB = maxOf(rB.el.map((e) => e.vmGauss));
    chk("A4 · Escala de unidades del FEA de placas: mm·N·MPa vs m·N·Pa (×1000)", "w y σ_vm idénticas (< 1e-6; la penalización 1e6·k_máx amplifica el redondeo)", `Δw = ${sci(dw)}; Δσ_vm = ${sci(Math.abs(sA - sB) / sB)}`, V(dw < 1e-6 && Math.abs(sA - sB) / sB < 1e-6));
    void c; }
  { const mk = (u) => { const n = 12, nodes = [], elems = [], N = []; for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) nodes.push([i * 1000 / n * u, j * 250 / n * u]);
      const id = (i, j) => i * (n + 1) + j; for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
      const fix = []; for (let j = 0; j <= n; j++) fix.push([id(0, j), 0], [id(0, j), 1]); const loads = [[id(n, n / 2), 0, -1000]];
      void N; return FEA.planeStress({ nodes, elems, t: 10 * u, E: 2e5 / u / u, nu: 0.3, fix, loads }); };
    const a = mk(1), b = mk(1e-3), k = 2 * (12 * 13 + 6) + 1;
    const dd = Math.abs(a.u[k] * 1e-3 - b.u[k]) / Math.abs(b.u[k]);
    chk("A4 · Escala de unidades del Q4: mm vs m", "desplazamientos idénticos (< 1e-8)", sci(dd), V(dd < 1e-8)); }
  { // Cholesky de banda vs eliminación densa en una matriz SPD aleatoria
    let s = 12345; const rnd = () => (s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296;
    const n = 120, bw = 9, B = new FEA.Band(n, bw), Dn = Array.from({ length: n }, () => new Float64Array(n));
    for (let i = 0; i < n; i++) { let rs = 0; for (let d = 1; d <= bw && i + d < n; d++) { const v = rnd() - 0.5; B.add(i, i + d, v); Dn[i][i + d] = v; Dn[i + d][i] = v; rs += Math.abs(v); }
      const dg = 4 + rnd(); B.add(i, i, dg); Dn[i][i] = dg; }
    const x0 = Array.from({ length: n }, (_, i) => Math.sin(i)), fv = new Float64Array(n);
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) fv[i] += Dn[i][j] * x0[j];
    const x = FEA.cholSolve(B, fv); let e = 0; for (let i = 0; i < n; i++) e = Math.max(e, Math.abs(x[i] - x0[i]));
    chk("A4 · Cholesky de banda vs solución conocida (SPD aleatoria, n = 120, bw = 9)", "error máx < 1e-10", sci(e), V(e < 1e-10)); }
  { let thrown = false; try { FEA.plate({ nodes: [[0, 0], [1, 0], [1, 1], [0, 1]], elems: [[0, 1, 2, 3]], t: 1, E: 1, nu: 0.3, q: new Float64Array([1]), wFix: [], betaN: [] }); } catch (e) { thrown = /no definida positiva/.test(e.message); }
    chk("A4 · Modelo sin apoyos (mecanismo de sólido rígido)", "debe fallar con error explícito, no devolver NaN", thrown ? "lanza «Matriz no definida positiva»" : "no lanza", V(thrown)); }
});

/* =================================================================================================================================================
   B · CONVERGENCIA DE MALLA DE LOS MODELOS DE tt300c.js
   ================================================================================================================================================= */
/* réplica parametrizada de discModel (hr y dth explícitos). Se valida contra TT.runDisc con la malla por defecto y la «coarse». */
function linspaceKeys(keys, h) { const out = [keys[0]]; for (let i = 1; i < keys.length; i++) { const a = keys[i - 1], b = keys[i], n = Math.max(1, Math.ceil((b - a) / h)); for (let k = 1; k <= n; k++) out.push(a + (b - a) * k / n); } return out; }
function uniqSorted(arr, tol) { const s = arr.slice().sort((a, b) => a - b), o = []; for (const v of s) if (!o.length || v - o[o.length - 1] > tol) o.push(v); return o; }
function meshParams(P, coarse) { const alpha = 2 * Math.PI / P.N_rib, r0 = P.D_hub / 2, Rd = P.D_top / 2; return { hr: Math.max(coarse ? 30 : 18, (Rd - r0) / (coarse ? 28 : 48)), dth: Math.max((coarse ? 2.5 : 1.25) * D2R, alpha / (coarse ? 16 : 30)) }; }
function discRep(P, R, which, hr, dth) {
  const alpha = 2 * Math.PI / P.N_rib, r0 = P.D_hub / 2, Rd = P.D_top / 2;
  const rings = TT.parseRings(P.rings).filter((r) => r > r0 && r < Rd), RL = Math.min(P.D_load / 2, Rd);
  const keyR = uniqSorted([r0, ...rings, Math.min(P.R_rib, Rd), P.R_pin - P.d_pin / 2, P.R_pin, P.R_pin + P.d_pin / 2, Rd, which === "top" ? RL : r0].filter((r) => r >= r0 && r <= Rd), 2);
  const rs = linspaceKeys(keyR, hr), pinAng = [];
  for (let k = 0; k < P.N_pin; k++) { const a = Math.PI / P.N_pin + 2 * Math.PI * k / P.N_pin; if (a >= -1e-9 && a <= alpha + 1e-9) pinAng.push(a); }
  const db = (P.d_pin / 2) / P.R_pin;
  const keyT = uniqSorted([0, alpha, ...pinAng, ...pinAng.map((a) => a - db), ...pinAng.map((a) => a + db)].filter((a) => a >= 0 && a <= alpha), 1e-4);
  const ts = linspaceKeys(keyT, dth), nT = ts.length, nodes = [], elems = [], q = [];
  for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) nodes.push([rs[i] * Math.cos(ts[j]), rs[i] * Math.sin(ts[j])]);
  const id = (i, j) => i * nT + j, t = which === "top" ? P.t_top : P.t_bot;
  const q_top = P.phi_d * R.W * 1e3 / (Math.PI * RL * RL) * (1 + 4 * P.e / RL);
  for (let i = 0; i < rs.length - 1; i++) for (let j = 0; j < nT - 1; j++) { elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]); const rc = (rs[i] + rs[i + 1]) / 2; q.push(which === "top" ? (rc <= RL ? q_top : 0) : R.q_max); }
  const wFix = new Set(), clamp = [], betaN = [], groups = { ring: rings.map(() => []), rib: [], pin: pinAng.map(() => []) };
  const near = (a, b, tol) => Math.abs(a - b) < tol;
  for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) {
    const k = id(i, j), r = rs[i], th = ts[j];
    if (i === 0) { clamp.push(k); continue; }
    rings.forEach((rr, ri) => { if (near(r, rr, 0.5)) { wFix.add(k); groups.ring[ri].push(k); } });
    if ((j === 0 || j === nT - 1) && r <= P.R_rib + 0.5) { if (!wFix.has(k)) groups.rib.push(k); wFix.add(k); }
    pinAng.forEach((ba, bi) => { const x = r * Math.cos(th) - P.R_pin * Math.cos(ba), y = r * Math.sin(th) - P.R_pin * Math.sin(ba); if (Math.hypot(x, y) <= P.d_pin / 2 + 0.5) { if (!wFix.has(k)) groups.pin[bi].push(k); wFix.add(k); } });
    if (j === 0) betaN.push([k, 0, 1]);
    if (j === nT - 1) betaN.push([k, -Math.sin(alpha), Math.cos(alpha)]);
  }
  return { nodes, elems, t, E: P.E, nu: P.nu, q: Float64Array.from(q), wFix: [...wFix], clamp, betaN, groups, rings, pinAng, alpha, rs, ts, nT, r0, Rd, RL, q_top, which };
}
function discSolve(P, R, which, hr, dth) {
  const m = discRep(P, R, which, hr, dth), t0 = Date.now(), r = FEA.plate(m), ms = Date.now() - t0;
  let vm = 0, im = 0; r.el.forEach((e, i) => { if (e.vmGauss > vm) { vm = e.vmGauss; im = i; } });
  let w = 0; for (const x of r.w) w = Math.max(w, Math.abs(x));
  const sumS = (arr) => Math.abs(arr.reduce((s, k) => s + r.reac[k], 0));
  const ringLine = m.rings.map((rr, i) => sumS(m.groups.ring[i]) / (rr * m.alpha)), ribLine = sumS(m.groups.rib) / (2 * Math.max(1, P.R_rib - P.D_hub / 2));
  const lineMax = Math.max(0, ribLine, ...ringLine), pinF = m.groups.pin.map((g) => sumS(g) / 1e3);
  const area = m.alpha / 2 * (m.Rd ** 2 - m.r0 ** 2);
  const ec = m.elems[im].map((k) => m.nodes[k]), cx = ec.reduce((s, p) => s + p[0], 0) / 4, cy = ec.reduce((s, p) => s + p[1], 0) / 4;
  // zonas: la tensión máxima por zona permite distinguir singularidades (divergen) de gradientes locales (convergen)
  const zone = { pin: 0, ring: 0, rib: 0, libre: 0 }, pins = m.pinAng;
  r.el.forEach((e, i) => {
    const c = m.elems[i].map((k) => m.nodes[k]), x = c.reduce((s, p) => s + p[0], 0) / 4, y = c.reduce((s, p) => s + p[1], 0) / 4, rc = Math.hypot(x, y), th = Math.atan2(y, x);
    const dp = pins.length ? Math.min(...pins.map((a) => Math.hypot(x - P.R_pin * Math.cos(a), y - P.R_pin * Math.sin(a)))) : 1e9;
    const z = dp < 1.5 * P.d_pin ? "pin" : m.rings.some((x2) => Math.abs(rc - x2) < 30) ? "ring" : rc * Math.min(th, m.alpha - th) < 30 ? "rib" : "libre";
    zone[z] = Math.max(zone[z], e.vmGauss);
  });
  // aspecto y orientación
  let arMax = 0, detMin = Infinity;
  m.elems.forEach((en) => { const p = en.map((k) => m.nodes[k]), L = [0, 1, 2, 3].map((a) => Math.hypot(p[a][0] - p[(a + 1) % 4][0], p[a][1] - p[(a + 1) % 4][1])); arMax = Math.max(arMax, maxOf(L) / minOf(L));
    const det = (p[1][0] - p[0][0]) * (p[3][1] - p[0][1]) - (p[1][1] - p[0][1]) * (p[3][0] - p[0][0]); detMin = Math.min(detMin, det); });
  // simetría respecto de la bisectriz del sector (θ → α − θ): w nodal y σ_vm por elemento
  let sw = 0, sv = 0; const wm = maxOf(Array.from(r.w).map(Math.abs)), nT = m.nT;
  for (let i = 0; i < m.rs.length; i++) for (let j = 0; j < nT; j++) sw = Math.max(sw, Math.abs(r.w[i * nT + j] - r.w[i * nT + (nT - 1 - j)]));
  for (let i = 0; i < m.rs.length - 1; i++) for (let j = 0; j < nT - 1; j++) sv = Math.max(sv, Math.abs(r.el[i * (nT - 1) + j].vmGauss - r.el[i * (nT - 1) + (nT - 2 - j)].vmGauss));
  return { m, hr, dth, n: m.nodes.length, nel: m.elems.length, h: Math.sqrt(area / m.elems.length), vm, w, lineMax, ringLine, ribLine, pinF, ms, zone, arMax, detMin,
    eq: Math.abs(r.Rsum) / r.Fapplied, Fapp: r.Fapplied / 1e3, symW: sw / wm, symVm: sv / vm, at: [Math.hypot(cx, cy), Math.atan2(cy, cx) / D2R] };
}
/* réplica parametrizada de runLift (n celdas por semilado); {full:true} modela la placa completa con los 4 puntos de izaje */
function liftRep(P, R, n, o) {
  o = o || {};
  const a = P.B / 2, h = a / n, N = o.full ? 2 * n : n, x0 = o.full ? -a : 0, nodes = [], elems = [];
  for (let i = 0; i <= N; i++) for (let j = 0; j <= N; j++) nodes.push([x0 + i * h, x0 + j * h]);
  const id = (i, j) => i * (N + 1) + j, Rd = P.D_top / 2;
  const mOther = R.m.disc + R.m.pivot + R.m.dogs + R.m.cyl + R.m.ss + R.m.uhmw, qDisc = mOther * G / (Math.PI * Rd * Rd), qOwn = (R.m.base + R.m.rim + R.m.brackets + R.m.shoes + R.m.beds) * G / (P.B * P.B);   // masa total (versión corregida de runLift)
  const q = [];
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) { elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]); q.push(P.phi_lift * (qOwn + (Math.hypot(x0 + (i + 0.5) * h, x0 + (j + 0.5) * h) <= Rd ? qDisc : 0))); }
  const xl = Math.min(P.x_lug, a - 1), yl = a - P.c_lug, pad = Math.max(75, 1.01 * h), wFix = [], betaN = [];
  for (let i = 0; i <= N; i++) for (let j = 0; j <= N; j++) {
    const k = id(i, j), x = x0 + i * h, y = x0 + j * h;
    const hit = o.full ? [[xl, yl], [-xl, yl], [xl, -yl], [-xl, -yl]].some(([cx, cy]) => Math.abs(x - cx) <= pad + 1e-6 && Math.abs(y - cy) <= pad + 1e-6) : (Math.abs(x - xl) <= pad + 1e-6 && Math.abs(y - yl) <= pad + 1e-6);
    if (hit) wFix.push(k);
    if (!o.full) { if (i === 0) betaN.push([k, 1, 0]); if (j === 0) betaN.push([k, 0, 1]); }
  }
  const m = { nodes, elems, t: P.t_base, E: P.E, nu: P.nu, q: Float64Array.from(q), wFix, betaN };
  const t0 = Date.now(), r = FEA.plate(m);
  let vmAll = 0, wm = 0, im = 0; r.el.forEach((e, i) => { if (e.vmGauss > vmAll) { vmAll = e.vmGauss; im = i; } }); for (const w of r.w) wm = Math.max(wm, Math.abs(w));
  const cen = (i) => { const c = elems[i].map((k) => nodes[k]); return [c.reduce((s, p) => s + p[0], 0) / 4, c.reduce((s, p) => s + p[1], 0) / 4]; };
  // como runLift corregido: máximo en elementos con max(|Δx|, |Δy|) ≥ 2·pad del punto de izaje (cuarto de placa)
  let vm = 0; r.el.forEach((e, i) => { const [x, y] = cen(i); if (Math.max(Math.abs(x - xl), Math.abs(y - yl)) >= 2 * pad && e.vmGauss > vm) vm = e.vmGauss; });
  const vmExcl = (rho) => { let v = 0; r.el.forEach((e, i) => { const [x, y] = cen(i); if (Math.hypot(x - xl, y - yl) >= rho && e.vmGauss > v) v = e.vmGauss; }); return v; };
  const fac = o.full ? 1 : 4;
  return { n, h, nfix: wFix.length, vm, vmAll, wMax: wm, at: cen(im), vmExcl, Fapp: fac * r.Fapplied / 1e3, Rsum: fac * Math.abs(r.Rsum) / 1e3, ms: Date.now() - t0, pad, xl, yl };
}
/* réplica parametrizada de globalBending (n puntos) */
function globRep(P, R, n) {
  const Rd = P.D_top / 2, RL = Math.min(P.D_load / 2, Rd), Ri = R.Ri;
  const qt = P.phi_d * R.W * 1e3 / (Math.PI * RL * RL), qd = R.Wd * 1e3 / (Math.PI * Rd * Rd), qb = R.ND * 1e3 / (Math.PI * (Rd * Rd - Ri * Ri));
  const r = new Float64Array(n), p = new Float64Array(n);
  for (let i = 0; i < n; i++) { r[i] = 1e-6 + Rd * i / (n - 1); p[i] = (r[i] >= Ri ? qb : 0) - (r[i] <= RL ? qt : 0) - qd; }
  const cum = new Float64Array(n), Q = new Float64Array(n), Iq = new Float64Array(n), J = new Float64Array(n);
  for (let i = 1; i < n; i++) cum[i] = cum[i - 1] + 0.5 * (p[i] * r[i] + p[i - 1] * r[i - 1]) * (r[i] - r[i - 1]);
  for (let i = 0; i < n; i++) Q[i] = cum[i] / r[i];
  for (let i = 1; i < n; i++) Iq[i] = Iq[i - 1] + 0.5 * (Q[i] + Q[i - 1]) * (r[i] - r[i - 1]);
  for (let i = 1; i < n; i++) J[i] = J[i - 1] + 0.5 * (Iq[i] * r[i] + Iq[i - 1] * r[i - 1]) * (r[i] - r[i - 1]);
  const psi = new Float64Array(n), dps = new Float64Array(n);
  for (let i = 0; i < n; i++) psi[i] = J[i] / r[i];
  for (let i = 1; i < n - 1; i++) dps[i] = (psi[i + 1] - psi[i - 1]) / (r[i + 1] - r[i - 1]);
  dps[0] = dps[1]; dps[n - 1] = dps[n - 2];
  const C = -(dps[n - 1] + P.nu * psi[n - 1] / Rd) / (1 + P.nu);
  let Mmax = 0, rM = 0;
  for (let i = 5; i < n - 5; i++) { const ps = psi[i] + C * r[i], dp = dps[i] + C, Mr = dp + P.nu * ps / r[i], Mt = ps / r[i] + P.nu * dp, M = Math.max(Math.abs(Mr), Math.abs(Mt)); if (M > Mmax) { Mmax = M; rM = r[i]; } }
  return { Mmax, rM, imb: Q[n - 1] * 2 * Math.PI * Rd / 1e3, at: (x) => { const i = Math.round((x - 1e-6) / Rd * (n - 1)); const ps = psi[i] + C * r[i], dp = dps[i] + C; return { Mr: dp + P.nu * ps / r[i], Mt: ps / r[i] + P.nu * dp }; }, pf: (x) => (x >= Ri ? qb : 0) - (x <= RL ? qt : 0) - qd };
}

const SCALES = FULL ? [2, 1, 0.5, 0.25, 0.125] : [2, 1, 0.5, 0.25];
const MESH_CACHE = {};
runSection("B", "Convergencia de malla de los modelos de la herramienta (mesa, izaje, flexión global)", () => {
  const P = TT.defaults(), R = TT.compute(P), mp = meshParams(P, false), mpc = meshParams(P, true);
  const kF = P.kFEA, kreq = {};
  // ---- B1/B2: planchas superior e inferior del sector de mesa
  for (const which of ["top", "bot"]) {
    const nombre = which === "top" ? "plancha superior (t = " + P.t_top + ")" : "plancha inferior (t = " + P.t_bot + ")";
    const tool = TT.runDisc(P, R, which, false), toolC = TT.runDisc(P, R, which, true);
    const lv = SCALES.map((s) => discSolve(P, R, which, mp.hr * s, mp.dth * s));
    const rep1 = lv[SCALES.indexOf(1)], repC = discSolve(P, R, which, mpc.hr, mpc.dth);
    chk(`B1 · Réplica de discModel vs herramienta (${which}), malla por defecto y coarse`, "σ_vm, flecha y nodos idénticos (< 1e-9)", `por defecto: σ ${sci(rel(rep1.vm, tool.vmMax))}, nodos ${rep1.n}/${tool.n}; coarse: σ ${sci(rel(repC.vm, toolC.vmMax))}, nodos ${repC.n}/${toolC.n}`, V(rel(rep1.vm, tool.vmMax) < 1e-9 && rel(repC.vm, toolC.vmMax) < 1e-9 && rep1.n === tool.n && repC.n === toolC.n));
    console.log(`\nB · ${nombre}: sector de ${f(360 / P.N_rib, 2)}°, nervios (θ = 0, α) empotrados por simetría, almas anulares y pasadores con w = 0, cubo empotrado. Factor de escala s sobre (h_r = ${f(mp.hr, 1)} mm, Δθ = ${f(mp.dth / D2R, 3)}°) de la malla por defecto.`);
    table(["s", "nodos", "h_ef [mm]", "σ_vm máx [MPa]", "ubicación r [mm]; θ [°]", "w máx [mm]", "q_línea máx [N/mm]", "ΣR/ΣF − 1", "t [s]"],
      lv.map((a, i) => [SCALES[i], a.n, f(a.h, 2), f(a.vm, 3), f(a.at[0], 0) + "; " + f(a.at[1], 2), f(a.w, 4), f(a.lineMax, 2), sci(a.eq - 1), f(a.ms / 1e3, 1)]));
    const hh = lv.map((a) => a.h), vv = lv.map((a) => a.vm), oV = obsOrder(hh, vv), oW = obsOrder(hh, lv.map((a) => a.w));
    const vinf = oV.vinf, vinfSafe = isFinite(vinf) ? Math.max(vinf, vv[vv.length - 1]) : NaN;
    const e1 = (vinfSafe - tool.vmMax) / vinfSafe, eC = (vinfSafe - toolC.vmMax) / vinfSafe;
    const kreqD = vinfSafe / tool.vmMax, kreqC = vinfSafe / toolC.vmMax, kHalf = vinfSafe / lv[SCALES.indexOf(0.5)].vm;
    kreq[which] = { kreqD, kreqC, kHalf, vinf: vinfSafe, vDef: tool.vmMax, vC: toolC.vmMax };
    // banda de confianza: p = 1 (Richardson de primer orden) y p observado
    const v1 = richardsonP(hh, vv, 1), v2 = richardsonP(hh, vv, 2);
    console.log(`  σ_vm: orden observado p = ${f(oV.p, 2)} (razón de diferencias ${f(oV.ratio, 2)}); Richardson (p obs.) = ${f(vinf, 1)} MPa; con p = 1: ${f(v1, 1)}; con p = 2: ${f(v2, 1)}. Flecha: ${isFinite(oW.p) ? `p = ${f(oW.p, 2)}, límite ${f(oW.vinf, 4)} mm` : `no monótona (${lv.map((a) => f(a.w, 4)).join(" → ")} mm)`}. Línea de carga máx. (reacciones en nervio/almas): ${lv.map((a) => f(a.lineMax, 1)).join(" → ")} N/mm (oscila ±${pct((maxOf(lv.map((a) => a.lineMax)) - minOf(lv.map((a) => a.lineMax))) / 2 / lv[lv.length - 1].lineMax, 1)}).`);
    chk(`B1 · ${which}: convergencia de σ_vm máx (monótona, orden observado)`, "monótona; p ∈ [0,5; 2,5]", `p = ${f(oV.p, 2)}; ${vv.map((x) => f(x, 1)).join(" → ")} MPa`, V(oV.mono && oV.p >= 0.5 && oV.p <= 2.5));
    chk(`B1 · ${which}: error de σ_vm de la malla por defecto respecto del límite (Richardson ${f(vinfSafe, 1)} MPa)`, "informar; la malla por defecto debe estar bajo el error cubierto por k_FEA − 1 = " + pct(kF - 1, 0), `${pct(e1, 1)} (por defecto, σ = ${f(tool.vmMax, 1)}); ${pct(eC, 1)} (coarse, σ = ${f(toolC.vmMax, 1)}); h/2: ${pct(1 - 1 / kHalf, 1)}`, "OK");
    chk(`B1 · ${which}: k_FEA = ${f(kF, 2)} cubre el error de malla por defecto`, `k_req = σ∞/σ_defecto ≤ k_FEA`, `k_req = ${f(kreqD, 3)} (por defecto), ${f(kreqC, 3)} (coarse), ${f(kHalf, 3)} (malla h/2)`, V(kreqD <= kF + 1e-9), { sev: "importante", id: "kFEA", titulo: `k_FEA = ${f(kF, 2)} no cubre el error de discretización de la malla por defecto (${nombre})`,
      correccion: `tt300c.js · PARAM_GROUPS «kFEA»: subir el valor por defecto a ${f(Math.ceil((kreqD + 0.03) * 20) / 20, 2)} (k_req = σ∞/σ_defecto = ${f(kreqD, 3)}); o refinar discModel a la mitad: hr = Math.max(coarse ? 30 : 9, (Rd−r0)/(coarse ? 28 : 96)) y paso angular Math.max((coarse ? 2.5 : 0.625)·D2R, alpha/(coarse ? 16 : 60)) → k_req ≈ ${f(kHalf, 2)}; la tensión máxima converge con orden ≈ ${f(oV.p, 1)} (< 1, independiente de t: 8, 20 y 40 mm dan la misma razón de diferencias 0,64) porque se toma en puntos de Gauss a 0,21·h del borde empotrado del nervio (error O(h)); la placa empotrada de referencia sin singularidades (A2) da el mismo comportamiento (p ≈ 0,85); σ_máx converge desde abajo, nunca por exceso` });
    chk(`B1 · ${which}: k_FEA cubre el error de la malla coarse (usada en tests y con {coarse:true})`, "k_req(coarse) ≤ k_FEA, o declarar que coarse no sirve para verificar", `k_req = ${f(kreqC, 3)}`, V(kreqC <= kF + 1e-9, true), { sev: "menor", id: "coarse", titulo: "La malla {coarse:true} subestima σ_vm más de lo que cubre k_FEA", correccion: "no usar {coarse:true} para verificar (solo para barridos); documentarlo en analyze(); el optimizador NO usa coarse (usa la malla por defecto con caché escalada, agentes.js línea 195)" });
    chk(`B1 · ${which}: flecha y reacciones convergen (malla por defecto vs límite)`, "error de w < 5 %; q_línea < 10 %", `w: ${pct(rel(tool.wMax, lv[lv.length - 1].w), 2)}; q_línea (vs malla más fina): ${pct(rel(tool.lineMax, lv[lv.length - 1].lineMax), 2)}`, V(rel(tool.wMax, lv[lv.length - 1].w) < 0.05 && rel(tool.lineMax, lv[lv.length - 1].lineMax) < 0.1, true));
    chk(`B1 · ${which}: equilibrio ΣF = ΣR en todas las mallas`, "< 0,5 %", `máx |ΣR/ΣF − 1| = ${sci(maxOf(lv.map((a) => Math.abs(a.eq - 1))))}`, V(maxOf(lv.map((a) => Math.abs(a.eq - 1))) < 0.005));
    chk(`B1 · ${which}: simetría de la solución respecto de la bisectriz del sector`, "Δw/w y Δσ/σ < 1e-6", `Δw/w = ${sci(maxOf(lv.map((a) => a.symW)))}; Δσ/σ = ${sci(maxOf(lv.map((a) => a.symVm)))}`, V(maxOf(lv.map((a) => a.symW)) < 1e-6 && maxOf(lv.map((a) => a.symVm)) < 1e-6));
    chk(`B1 · ${which}: calidad de malla (malla por defecto)`, "det J > 0; relación de aspecto máx ≤ 10", `relación de aspecto ${f(rep1.arMax, 1)} (cerca del cubo); det J mín ${f(rep1.detMin, 2)}`, V(rep1.detMin > 0 && rep1.arMax <= 10, true), { sev: "menor", id: "aspecto", titulo: "Elementos con relación de aspecto > 10 en la malla por defecto", correccion: "discModel: refinar angularmente cerca del cubo" });
    // zonas
    const zr = lv.map((a) => a.zone);
    console.log("  σ_vm máx por zona [MPa] (s = " + SCALES.join(" → ") + "):");
    for (const z of ["pin", "ring", "rib", "libre"]) {
      const zz = zr.map((x) => x[z]), oz = obsOrder(hh, zz);
      console.log(`    zona ${z.padEnd(5)}: ${zz.map((x) => f(x, 1)).join(" → ")}  (razón de diferencias ${f(oz.ratio, 2)}${oz.ratio >= 0.9 ? " — NO converge: singular" : ""})`);
    }
    const sing = ["pin", "ring", "rib", "libre"].filter((z) => obsOrder(hh, zr.map((x) => x[z])).ratio >= 0.9);
    chk(`B1 · ${which}: ¿σ_vm máx depende de la malla por singularidad (apoyos de pasador, anillos, nervios)?`, "razón de diferencias sucesivas < 0,9 en todas las zonas (convergencia, no singularidad)", sing.length ? "singular en: " + sing.join(", ") : "ninguna zona diverge; el máximo está junto al nervio (borde empotrado) y converge con orden < 1", V(!sing.length), { sev: "importante", id: "sing", titulo: "σ_vm de la mesa diverge con la malla en " + sing.join(", "), correccion: "excluir la zona singular de la verificación" });
    MESH_CACHE[which] = { lv, tool };
  }
  const kT = kreq.top, kB = kreq.bot;
  { const hk = hall.find((x) => x.id === "kFEA"); if (hk) { hk.titulo = `k_FEA = ${f(P.kFEA, 2)} no cubre el error de discretización de la malla por defecto de las planchas de la mesa (k_req = ${f(kT.kreqD, 3)} superior, ${f(kB.kreqD, 3)} inferior)`; hk.detalle = `σ_vm máx por defecto ${f(kT.vDef, 1)} / ${f(kB.vDef, 1)} MPa frente al límite de Richardson ${f(kT.vinf, 1)} / ${f(kB.vinf, 1)} MPa (error de malla ${pct(1 - kT.vDef / kT.vinf, 1)} / ${pct(1 - kB.vDef / kB.vinf, 1)}; coarse: ${pct(1 - kT.vC / kT.vinf, 1)} / ${pct(1 - kB.vC / kB.vinf, 1)}); k_req = ${f(kT.kreqD, 3)} / ${f(kB.kreqD, 3)}`; } }
  { // efecto en la verificación: FU con σ∞ en vez de σ·k
    const A = TT.analyze(P), sAll = 0.6 * P.Fy, g = A.fea.glob;
    const fuT = (g.sigTop + kT.vinf) / sAll, fuB = (g.sigBot + kB.vinf) / sAll;
    const fu0T = A.checks.find((c) => c.name === "Plancha superior: global + local").fu, fu0B = A.checks.find((c) => c.name === "Plancha inferior: global + local").fu;
    chk("B1 · Efecto en la verificación «global + local» (σ∞ sin k_FEA vs herramienta)", "FU con σ∞ ≤ 0,90 (el veredicto no cambia)", `superior ${f(fu0T, 3)} → ${f(fuT, 3)}; inferior ${f(fu0B, 3)} → ${f(fuB, 3)}`, V(fuT <= 0.9 && fuB <= 0.9, true)); }

  // ---- B3: izaje de la base
  const liftNs = [6, 12, 24, 48, 96], toolL = TT.runLift(P, R, false), toolLC = TT.runLift(P, R, true);
  const L = liftNs.map((n) => liftRep(P, R, n));
  const gl = L[2], glC = liftRep(P, R, 14);
  const hasAll = typeof toolL.vmAll === "number";
  chk("B3 · Réplica de runLift (versión con masa total y exclusión 2·pad) vs herramienta (n = 24 y coarse n = 14)", "vmMax, vmAll y flecha idénticos (< 1e-9)", `vmMax ${sci(rel(gl.vm, toolL.vmMax))}, ${sci(rel(glC.vm, toolLC.vmMax))}; vmAll ${hasAll ? sci(rel(gl.vmAll, toolL.vmAll)) : "la herramienta no devuelve vmAll"}; w ${sci(rel(gl.wMax, toolL.wMax))}`, V(rel(gl.vm, toolL.vmMax) < 1e-9 && rel(glC.vm, toolLC.vmMax) < 1e-9 && hasAll && rel(gl.vmAll, toolL.vmAll) < 1e-9 && rel(gl.wMax, toolL.wMax) < 1e-9));
  console.log(`\nB · Izaje del cuarto de base (B = ${P.B}, t = ${P.t_base}, lug en x = ${gl.xl}, y = ${f(gl.yl, 0)}; apoyo rígido de ±${f(gl.pad, 0)} mm por lado = placa de 150 × 150). vmAll = máximo global (singular); vmMax = el de la herramienta (a ≥ 2·pad del cáncamo, norma máx.); excl. ρ = fuera de un radio euclídeo ρ.`);
  const rhoList = [150, 225];
  table(["n", "h [mm]", "pad [mm]", "nodos fijos", "vmAll [MPa]", "ubicación de vmAll (x; y)", "vmMax herramienta", "excl. ρ=150", "excl. ρ=225", "w máx [mm]", "ΣF [kN]", "ΣR/ΣF − 1"],
    L.map((a) => [a.n, f(a.h, 1), f(a.pad, 0), a.nfix, f(a.vmAll, 2), f(a.at[0], 0) + "; " + f(a.at[1], 0), f(a.vm, 2), ...rhoList.map((rho) => f(a.vmExcl(rho), 2)), f(a.wMax, 3), f(a.Fapp, 3), sci(a.Rsum / a.Fapp - 1)]));
  const vA = L.map((a) => a.vmAll), dA = [vA[2] - vA[1], vA[3] - vA[2], vA[4] - vA[3]];
  const vT = L.slice(2).map((a) => a.vm);      // n = 24, 48, 96 (pad constante = 75 mm)
  chk("B3 · Izaje: vmAll (máximo global) frente a la malla", "informar: singular (diferencias crecientes); no debe usarse como verificación", `${vA.map((x) => f(x, 1)).join(" → ")} MPa; diferencias ${dA.map((x) => f(x, 1)).join(", ")}; ubicado en la esquina de la placa de apoyo (${f(L[4].at[0], 0)}; ${f(L[4].at[1], 0)})`, "OK");
  chk("B3 · Izaje: vmMax de la herramienta (a ≥ 2·pad del cáncamo) frente a la malla (n = 24→48→96, pad = 75 mm)", "converge: variación entre n = 48 y 96 < 5 % y diferencias decrecientes", `${vT.map((x) => f(x, 1)).join(" → ")} MPa; Δ(48→96) = ${pct(rel(vT[2], vT[1]), 1)}; en la malla por defecto ${f(toolL.vmMax, 1)} MPa (límite ≈ ${f(vT[2], 1)}: ${pct(toolL.vmMax / vT[2] - 1, 1)})`, V(rel(vT[2], vT[1]) < 0.05 && Math.abs(vT[2] - vT[1]) <= Math.abs(vT[1] - vT[0]) + 1e-9), { sev: "importante", id: "lift-sing", titulo: "Izaje: vmMax de la plancha base sigue dependiendo de la malla", correccion: "revisar la exclusión 2·pad en runLift()" });
  const wL = L.map((a) => a.wMax);
  chk("B3 · Izaje: flecha máx. frente a la malla", "informar (la flecha depende del tamaño efectivo del apoyo, que varía con h)", `${wL.map((x) => f(x, 2)).join(" → ")} mm; la malla por defecto da ${f(toolL.wMax, 2)} (conservadora)`, "OK");
  chk("B3 · Izaje: equilibrio ΣF = ΣR", "< 0,5 %", sci(maxOf(L.map((a) => Math.abs(a.Rsum / a.Fapp - 1)))), V(maxOf(L.map((a) => Math.abs(a.Rsum / a.Fapp - 1))) < 0.005));
  // carga aplicada vs masa total real
  const Fexp = P.phi_lift * G * R.m.total / 1e3, mSum = ["disc", "ss", "uhmw", "base", "rim", "brackets", "dogs", "shoes", "beds", "pivot", "cyl"].reduce((t, k) => t + R.m[k], 0);
  chk("B3 · Izaje: la carga aplicada en el FEA es φ_izaje · g · masa total real", "|ΣF − φ·g·m_total| < 1 % (equilibrio físico, no solo numérico); m_total = suma de los 11 componentes", `ΣF = ${f(toolL.Fapp, 2)} kN vs ${f(Fexp, 2)} kN → ${pct((toolL.Fapp - Fexp) / Fexp, 2)} (m_total = ${f(R.m.total, 1)} kg; suma de componentes ${f(mSum, 1)} kg)`, V(Math.abs(toolL.Fapp - Fexp) / Fexp < 0.01 && rel(mSum, R.m.total) < 1e-12), { sev: "importante", id: "lift-masa", titulo: "Izaje: el FEA no aplica la masa total", correccion: "runLift(): qOwn y mOther deben sumar los 11 componentes de R.m" });
  // la misma prueba con las interfaces A y B (masa de discos y UHMW)
  { const out = [1, 2].map((k) => { const Q = Object.assign(TT.defaults(), { opt_ss: k === 1 ? 1 : 0, opt_uhmw: k === 2 ? 1 : 0 }), RQ = TT.compute(Q), lq = TT.runLift(Q, RQ, false); return (lq.Fapp - Q.phi_lift * G * RQ.m.total / 1e3) / (Q.phi_lift * G * RQ.m.total / 1e3); });
    chk("B3 · Izaje: ΣF = φ·g·m_total también con la interfaz A y B", "|Δ| < 1 %", `A ${pct(out[0], 2)}; B ${pct(out[1], 2)}`, V(Math.abs(out[0]) < 0.01 && Math.abs(out[1]) < 0.01)); }
  // simetría: cuarto vs placa completa
  { const q = liftRep(P, R, 24), fl = liftRep(P, R, 24, { full: true });
    chk("B3 · Izaje: cuarto de placa con simetría vs placa completa con 4 cáncamos (misma h)", "vmAll, flecha y ΣF idénticos (< 1e-6)", `Δσ ${sci(rel(q.vmAll, fl.vmAll))}; Δw ${sci(rel(q.wMax, fl.wMax))}; ΔF ${sci(rel(q.Fapp, fl.Fapp))}`, V(rel(q.vmAll, fl.vmAll) < 1e-6 && rel(q.wMax, fl.wMax) < 1e-6 && rel(q.Fapp, fl.Fapp) < 1e-6)); }
  // discretización en escalera del círculo de la mesa: elementos con centro dentro de R
  { const e = L.map((a) => (a.Fapp - Fexp) / Fexp), Rd = P.D_top / 2, Ae = (n) => { const h = P.B / 2 / n; let c = 0; for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (Math.hypot((i + 0.5) * h, (j + 0.5) * h) <= Rd) c++; return 4 * c * h * h; };
    chk("B3 · Izaje: carga sobre la huella circular de la mesa (escalera de elementos con centro dentro de R)", "|ΣF/(φ·g·m_total) − 1| < 1 % en la malla por defecto (el error debe ser de la escalera: área discreta/πR² − 1)", `n = 6, 12, 24, 48, 96: ${e.map((x) => pct(x, 2)).join(", ")}; área de la escalera/πR² − 1 en n = 24: ${pct(Ae(24) / (Math.PI * Rd * Rd) - 1, 2)} (la carga de la mesa es ${pct((R.m.disc + R.m.pivot + R.m.dogs + R.m.cyl + R.m.ss + R.m.uhmw) / R.m.total, 0)} de la masa total, de ahí ΣF/ΣF_exacta − 1 ≈ la mitad de ese error)`, V(Math.abs(e[2]) < 0.01)); }

  // ---- B4: flexión global axisimétrica
  const gT = TT.globalBending(P, R);
  const nsG = [500, 1000, 2000, 4000, 8000, 16000, 64000, 256000], GG = nsG.map((n) => globRep(P, R, n));
  chk("B4 · Réplica de globalBending (n = 4000) vs herramienta", "M_máx idéntico", sci(rel(GG[3].Mmax, gT.Mmax)), V(rel(GG[3].Mmax, gT.Mmax) < 1e-12));
  console.log("\nB · Flexión global axisimétrica (integración trapezoidal en n puntos radiales; la herramienta usa n = 4000):");
  table(["n", "Δr [mm]", "M_máx [N·mm/mm]", "error vs n = 256000", "desequilibrio [kN]"], GG.map((a, i) => [nsG[i], f(P.D_top / 2 / (nsG[i] - 1), 3), f(a.Mmax, 1), pct(rel(a.Mmax, GG[7].Mmax), 4), f(a.imb, 4)]));
  const o4 = obsOrder(nsG.slice(0, 7).map((n) => 1 / n), GG.slice(0, 7).map((a) => a.Mmax));
  chk("B4 · Flexión global: error de integración con n = 4000", "< 0,1 % y orden ≈ 1", `${pct(rel(GG[3].Mmax, GG[7].Mmax), 4)}; p = ${f(o4.p, 2)}; desequilibrio ${f(gT.imbalance, 3)} kN de ${f(R.ND, 0)} kN`, V(rel(GG[3].Mmax, GG[7].Mmax) < 0.001 && Math.abs(gT.imbalance) < 1e-3 * R.ND));
  // verificación independiente con el FEA de placas: sector anular con bordes libres (momentos de una placa libre no dependen de D)
  { const Rd = P.D_top / 2, g = GG[6], r0 = 5, hr = 10, dd = 0.75, alpha = 2 * Math.PI / 14, nr = Math.ceil((Rd - r0) / hr), nT = Math.ceil(alpha / (dd * D2R));
    const nodes = [], elems = [], q = [], rs = Array.from({ length: nr + 1 }, (_, i) => r0 + (Rd - r0) * i / nr);
    for (let i = 0; i <= nr; i++) for (let j = 0; j <= nT; j++) { const th = alpha * j / nT; nodes.push([rs[i] * Math.cos(th), rs[i] * Math.sin(th)]); }
    const id = (i, j) => i * (nT + 1) + j, betaN = [];
    for (let i = 0; i < nr; i++) for (let j = 0; j < nT; j++) { elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]); q.push(g.pf((rs[i] + rs[i + 1]) / 2)); }
    for (let i = 0; i <= nr; i++) { betaN.push([id(i, 0), 0, 1]); betaN.push([id(i, nT), -Math.sin(alpha), Math.cos(alpha)]); }
    const rr = FEA.plate({ nodes, elems, t: 100, E: P.E, nu: P.nu, q: Float64Array.from(q), wFix: [id(Math.floor(nr / 2), 0)], betaN });
    let worst = 0; const det = [];
    for (const rt of [100, 300, 500, 700, 900]) {
      let best = null;
      elems.forEach((en, i) => { const c = en.map((k) => nodes[k]), cx = c.reduce((s, p) => s + p[0], 0) / 4, cy = c.reduce((s, p) => s + p[1], 0) / 4, rc = Math.hypot(cx, cy), th = Math.atan2(cy, cx);
        if (Math.abs(rc - rt) < hr / 2 + 1 && Math.abs(th - alpha / 2) < 0.06) { const M = rr.el[i].M, c2 = Math.cos(th), s2 = Math.sin(th), Mr = M[0] * c2 * c2 + M[1] * s2 * s2 + 2 * M[2] * s2 * c2, Mt = M[0] * s2 * s2 + M[1] * c2 * c2 - 2 * M[2] * s2 * c2; if (!best || Math.abs(rc - rt) < best.d) best = { d: Math.abs(rc - rt), rc, Mr, Mt }; } });
      const ex = g.at(best.rc), eM = Math.abs(Math.abs(best.Mt) - Math.abs(ex.Mt)) / Math.abs(ex.Mt), eR = Math.abs(Math.abs(best.Mr) - Math.abs(ex.Mr)) / Math.max(Math.abs(ex.Mr), 0.15 * Math.abs(ex.Mt));
      worst = Math.max(worst, eM, rt < 800 ? eR : 0); det.push(`r = ${f(best.rc, 0)}: M_t ${f(Math.abs(best.Mt) / 1e3, 1)} vs ${f(Math.abs(ex.Mt) / 1e3, 1)}, M_r ${f(Math.abs(best.Mr) / 1e3, 1)} vs ${f(Math.abs(ex.Mr) / 1e3, 1)} kN·mm/mm`);
    }
    chk("B4 · Flexión global axisimétrica vs FEA MITC4 independiente (sector anular libre, r₀ = 5 mm)", "M_r y M_t coinciden dentro de 1,5 % (r = 100…900 mm)", `máx ${pct(worst, 2)}; ` + det.join("; "), V(worst < 0.015)); }
  // ---- B5: invariancia del FEA de mesa con B, n_cyl, t_base (no deben influir)
  { const A0 = TT.analyze(P, { coarse: true }), A1 = TT.analyze(Object.assign({}, P, { B: 3000, n_cyl: 4 }), { coarse: true });
    const dTop = rel(A0.fea.top.vmMax, A1.fea.top.vmMax), dGlob = rel(A0.fea.glob.Mmax, A1.fea.glob.Mmax);
    chk("B5 · FEA de la mesa independiente de B y n_cyl", "Δσ_vm(top) y ΔM(glob) < 1e-9", `${sci(dTop)}; ${sci(dGlob)}`, V(dTop < 1e-9 && dGlob < 1e-9)); }
});

/* =================================================================================================================================================
   C · CONSISTENCIA DEL NÚCLEO
   ================================================================================================================================================= */
/* Solución independiente del equilibrio del patín: eliminación de Gauss con pivoteo parcial y potencia virtual (ω = 1) */
function gaussSolve(M, v) {
  const n = v.length, a = M.map((row, i) => [...row, v[i]]);
  for (let c = 0; c < n; c++) {
    let pv = c; for (let i = c + 1; i < n; i++) if (Math.abs(a[i][c]) > Math.abs(a[pv][c])) pv = i;
    [a[c], a[pv]] = [a[pv], a[c]];
    for (let i = c + 1; i < n; i++) { const k = a[i][c] / a[c][c]; for (let j = c; j <= n; j++) a[i][j] -= k * a[c][j]; }
  }
  const x = new Array(n).fill(0);
  for (let i = n - 1; i >= 0; i--) { let s = a[i][n]; for (let j = i + 1; j < n; j++) s -= a[i][j] * x[j]; x[i] = s / a[i][i]; }
  return x;
}
function shoeIndep(P, K, T /* kN·m */, th, sgn) {
  const R_ = P.R_pin, r = P.d_pin / 2, Tn = T * 1e3 / P.n_cyl;                                // kN·mm por cilindro (F_pas resulta en kN)
  const xc = R_ * Math.cos(th), yc = R_ * Math.sin(th) - r;                                    // punto de contacto de la cara con el pasador
  const s = sgn !== undefined ? sgn : (yc >= 0 ? 1 : -1), H = s * P.mu_s;                      // sentido de la fricción: opuesto al deslizamiento −ω·yc del pasador
  const yrp = R_ * Math.sin(th) - P.l_p, yr = yrp + (K.front - K.rear) / 2 - K.Lg / 2;
  const [Fp, Rf, Rr] = gaussSolve([[xc - H * yc, 0, 0], [(P.x_g - xc) + H * (yc - yr), -K.Lg, 0], [-H, 1, 1]], [Tn, 0, 0]);
  const Fvp = (Tn + P.mu_s * Fp * Math.abs(yc) + P.mu_g * (Math.abs(Rf) + Math.abs(Rr)) * xc) / (P.eta_c * xc);   // potencia virtual: η·F·v = T/n·ω + μ_s·F_pas·|v_desl| + μ_g·ΣR·v
  return { Fp, Rf, Rr, F: (Fp + P.mu_g * (Math.abs(Rf) + Math.abs(Rr))) / P.eta_c, Fvp, xc, yc, den: xc - H * yc };
}
function strokeScan(P, R, N) {            // F(θ) con la solución independiente en N+1 puntos; separa el salto de fricción
  const K = R.K, pts = [], thX = Math.asin(Math.min(1, P.d_pin / 2 / P.R_pin));
  for (let i = 0; i <= N; i++) { const th = -K.pitch / 2 + K.pitch * i / N; pts.push(Object.assign({ th }, shoeIndep(P, K, R.cd.T, th))); }
  let jump = 0, jumpAt = null, nonPos = 0, minDen = Infinity;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i], cross = (a.th < thX && b.th >= thX) || (a.th >= thX && b.th < thX);
    minDen = Math.min(minDen, a.den, b.den); if (!(a.F > 0) || !isFinite(a.F)) nonPos++;
    if (!cross) { const d = Math.abs(b.F - a.F) / Math.max(a.F, 1e-30); if (d > jump) { jump = d; jumpAt = b.th; } }
  }
  const atX = [shoeIndep(P, K, R.cd.T, thX, -1).F, shoeIndep(P, K, R.cd.T, thX, 1).F];
  return { pts, jump, jumpAt, nonPos, minDen, atX, Fmax: maxOf(pts.map((p) => p.F)) };
}

let SWEEP = null;   // resumen del barrido de parámetros (reutilizado por G)
runSection("C", "Consistencia del núcleo: invariancia, linealidad, monotonía, unidades, equilibrio del patín, barrido de parámetros", () => {
  const base = TT.defaults(), R0 = TT.compute(base);

  // ---- C1 invariancia
  { const RB = TT.compute(Object.assign({}, base, { B: 3000 })), keys = ["F", "p", "FS", "T"];
    let d = 0; R0.cases.forEach((c, i) => keys.forEach((k) => { d = Math.max(d, rel(c[k], RB.cases[i][k])); }));
    d = Math.max(d, rel(R0.q_max, RB.q_max), rel(R0.Fstall, RB.Fstall), rel(R0.Kguide, RB.Kguide), rel(R0.K.s_req, RB.K.s_req), rel(R0.m.disc, RB.m.disc));
    chk("C1 · Invariancia: B = 2560 → 3000", "casos F/p/FS/T, q_máx, F_calado, K, masa de la mesa idénticos; solo cambian base y g_rigid", `Δmáx = ${sci(d)}; m_base ${f(R0.m.base, 0)} → ${f(RB.m.base, 0)} kg`, V(d < 1e-12 && RB.m.base > R0.m.base)); }
  { const R4 = TT.compute(Object.assign({}, base, { n_cyl: 4 })), d1 = rel(R0.cd.F * 2, R4.cd.F * 4), d2 = rel(R0.Fstall, R4.Fstall), d3 = rel(R0.cd.FS * 2, R4.cd.FS), d4 = rel(R0.N, R4.N);
    const dm = Math.max(rel(R4.m.dogs, 2 * R0.m.dogs), rel(R4.m.shoes, 2 * R0.m.shoes), rel(R4.m.beds, 2 * R0.m.beds), rel(R4.m.cyl, 2 * R0.m.cyl));
    chk("C1 · Invariancia: n_cyl = 2 → 4 con el mismo par", "n·F, F_calado, N idénticos; FS ×2; masas de uñas, patines, bancadas y cilindros ×2", `Δ(n·F) ${sci(d1)}; ΔF_calado ${sci(d2)}; ΔFS×2 ${sci(d3)}; ΔN ${sci(d4)}; Δmasas ${sci(dm)}`, V(Math.max(d1, d2, d3, d4, dm) < 1e-12)); }
  { const RD = TT.compute(Object.assign({}, base, { D_top: 2200 })), keys = ["pitch", "a_min", "chord", "L_s", "Lg", "y_eye", "pocketEnd", "s_req"];
    const d = Math.max(...keys.map((k) => rel(RD.K[k], R0.K[k])), rel(RD.Fstall, R0.Fstall), rel(RD.Kguide, R0.Kguide), rel(RD.Fret, R0.Fret), rel(RD.tCycle, R0.tCycle));
    chk("C1 · Invariancia: D_top = 2000 → 2200", "cinemática, F_calado, K de guía, F_retorno y tiempo de ciclo idénticos (no dependen del diámetro)", `Δmáx = ${sci(d)}; F_dis cambia solo por la masa: ${pct(rel(RD.cd.F, R0.cd.F), 3)}`, V(d < 1e-12)); }
  { const a = TT.analyze(Object.assign({}, base, { rings: "840 300 580" }), { noFEA: true }), b = TT.analyze(Object.assign({}, base, { rings: "300;580,840" }), { noFEA: true }), c = TT.analyze(base, { noFEA: true });
    chk("C1 · Invariancia: orden y separadores de los radios de almas anulares", "masa y resultados idénticos", `Δm = ${sci(Math.abs(a.R.m.total - c.R.m.total) + Math.abs(b.R.m.total - c.R.m.total))}`, V(a.R.m.total === c.R.m.total && b.R.m.total === c.R.m.total));
    const dup = TT.masses(Object.assign({}, base, { rings: "300, 580, 840, 840" }));
    chk("C1 · Radios de almas duplicados (840 dos veces)", "no debe duplicar la masa del alma (deduplicar o advertir)", `la masa de almas sube ${f(dup.webs - R0.m.webs, 1)} kg (${pct(dup.webs / R0.m.webs - 1, 1)}) y validate() no avisa: ${AG.validate(Object.assign({}, base, { rings: "300, 580, 840, 840" })).length} mensajes`, V(Math.abs(dup.webs - R0.m.webs) < 1e-9, true), { sev: "menor", id: "rings-dup", titulo: "Radios de alma duplicados se suman dos veces en la masa y en el FEA", correccion: "tt300c.js · parseRings(): eliminar duplicados (|Δr| < 1 mm) tras ordenar: .filter((v, i, a) => i === 0 || v - a[i - 1] > 1)" }); }

  // ---- C2 linealidad
  { const T = R0.cd.T, r1 = R0.Fcyl(T), r2 = R0.Fcyl(2 * T), r3 = R0.Fcyl(3.7 * T);
    chk("C2 · Linealidad: F(2T) = 2·F(T) y F(3,7T) = 3,7·F(T)", "error relativo < 1e-12", sci(Math.max(rel(r2, 2 * r1), rel(r3, 3.7 * r1))), V(Math.max(rel(r2, 2 * r1), rel(r3, 3.7 * r1)) < 1e-12)); }
  { const Fs = (D, p) => TT.compute(Object.assign({}, base, { D_bore: D, p_relief: p })).Fstall, F0 = Fs(90, 700);
    const si = Math.PI / 4 * (90e-3) ** 2 * 700e5 / 1e3;     // SI: m², Pa → kN
    chk("C2 · Fuerza de calado = A·p: escalas con D² y p y coincide con el cálculo en SI", "ΔSI < 1e-12; razones exactas", `ΔSI ${sci(rel(F0, si))}; D×1,5 → ${f(Fs(135, 700) / F0, 6)} (2,25); p×0,5 → ${f(Fs(90, 350) / F0, 6)} (0,5)`, V(rel(F0, si) < 1e-12 && rel(Fs(135, 700) / F0, 2.25) < 1e-12 && rel(Fs(90, 350) / F0, 0.5) < 1e-12)); }
  { const Fw = [100, 300, 600].map((w) => TT.compute(Object.assign({}, base, { W_tf: w })).cd.F), c = (Fw[1] - Fw[0]) / 200, res = Math.abs(Fw[2] - (Fw[1] + c * 300)) / Fw[2];
    chk("C2 · F(W) afín en W (N = W + W_d con W_d fijo): tres puntos 100, 300, 600 tf", "colinealidad < 1e-12", sci(res), V(res < 1e-12)); }
  { const A1 = TT.analyze(base, { coarse: true }), A2 = TT.analyze(Object.assign({}, base, { W_tf: 600 }), { coarse: true }), A3 = TT.analyze(Object.assign({}, base, { W_tf: 150 }), { coarse: true });
    chk("C2 · FEA de la plancha superior lineal en la carga (σ_vm ∝ W a igual geometría)", "razón σ(600)/σ(300) = 2 y σ(150)/σ(300) = 0,5 (< 1e-9)", `${f(A2.fea.top.vmMax / A1.fea.top.vmMax, 9)}; ${f(A3.fea.top.vmMax / A1.fea.top.vmMax, 9)}`, V(Math.abs(A2.fea.top.vmMax / A1.fea.top.vmMax - 2) < 1e-9 && Math.abs(A3.fea.top.vmMax / A1.fea.top.vmMax - 0.5) < 1e-9));
    const RL = Math.min(base.D_load / 2, base.D_top / 2), qT = base.phi_d * R0.W * 1e3 / (Math.PI * RL * RL) * (1 + 4 * base.e / RL), Ftop = A1.fea.top.Fapp * base.N_rib, Fexp = qT * Math.PI * (RL * RL - (base.D_hub / 2) ** 2) / 1e3;
    chk("C2 · Carga del FEA de la plancha superior = q_top·área de la huella (sin cubo)", "error < 5e-4 (los elementos rectos aproximan el sector circular: error ≈ Δθ²/6)", `${f(Ftop, 1)} kN vs ${f(Fexp, 1)} kN (${sci(rel(Ftop, Fexp))}); ΣF = ${f(Ftop / (base.phi_d * R0.W), 3)}·φW por aplicar la presión máxima sobre todo el círculo (conservador)`, V(rel(Ftop, Fexp) < 5e-4)); }

  // ---- C3 monotonía
  { const mono = []; let bad = 0, total = 0;
    const sweep = (param, vals, get, dir, label, opts) => {
      const xs = vals.map((v) => get(TT.compute(Object.assign({}, base, { [param]: v }), opts)));
      let ok = true; for (let i = 1; i < xs.length; i++) { const d = xs[i] - xs[i - 1]; if (dir > 0 ? d < -1e-9 * Math.abs(xs[i]) : d > 1e-9 * Math.abs(xs[i])) ok = false; if (opts && opts.strict && Math.abs(d) < 1e-12) ok = false; }
      total++; if (!ok) { bad++; mono.push(label + " (" + param + "): " + xs.map((x) => f(x, 3)).join(", ")); }
    };
    const steps = (a, b, n) => Array.from({ length: n + 1 }, (_, i) => a + (b - a) * i / n);
    const FS = (R) => R.cd.FS, Fd = (R) => R.cd.F, M = (R) => R.m.total, q = (R) => R.q_max;
    for (const p of ["mu_d", "r_ef", "e", "W_tf", "mu_s", "mu_g", "phi_d"]) {
      const [mn, mx] = TT.PARAM_GROUPS.flatMap((g) => g.p).find((x) => x[0] === p).slice(4, 6), rng = p === "W_tf" ? [50, 1000] : p === "e" ? [0, 250] : [mn, mx];
      sweep(p, steps(rng[0], rng[1], 12), FS, -1, "FS decrece");
      if (p !== "phi_d" || true) sweep(p, steps(rng[0], rng[1], 12), Fd, +1, "F crece");
    }
    sweep("eta_c", steps(0.8, 1, 10), FS, +1, "FS crece con el rendimiento");
    for (const p of ["t_top", "t_bot", "t_web", "t_rib", "t_base", "h_disc", "D_top", "B", "d_pin", "N_rib", "L_ch", "w_bed", "rim_h"]) {
      const [mn, mx] = TT.PARAM_GROUPS.flatMap((g) => g.p).find((x) => x[0] === p).slice(4, 6);
      const lo = p === "D_top" ? 2000 : p === "h_disc" ? 120 : p === "N_rib" ? 7 : mn, hi = p === "D_top" ? 3000 : p === "B" ? 4500 : p === "N_rib" ? 28 : p === "h_disc" ? 300 : mx;
      const vs = p === "N_rib" ? [7, 14, 28] : steps(lo, hi, 8).map((v) => Math.round(v));
      sweep(p, vs, M, p === "N_rib" ? +1 : +1, "masa crece");
    }
    sweep("t_pr", steps(10, 80, 14).map(Math.round), M, +1, "masa no decrece con t_pr");
    sweep("W_tf", steps(100, 600, 10), q, +1, "q_máx crece con W"); sweep("e", steps(0, 400, 10), q, +1, "q_máx crece con e");
    chk(`C3 · Monotonía (${total} barridos: FS↓ con μ_d, r_ef, e, W, μ_s, μ_g, φ_d; F↑; masa↑ con espesores y dimensiones; q_máx↑)`, "0 violaciones", bad ? `${bad} violaciones: ${mono.join(" | ")}` : "0 violaciones", V(!bad), { sev: "importante", id: "monotonia", titulo: "Violaciones de monotonía en el núcleo", correccion: "(ver detalle)" });
    // masa estrictamente creciente con t_top (el anillo usa máx(t_pr, t_top): no estricta), con t_web y t_rib
    const tm = [10, 15, 20, 25, 30, 40].map((t) => TT.masses(Object.assign({}, base, { t_top: t })).top);
    chk("C3 · Masa de la plancha superior estrictamente creciente con t_top (6 valores)", "Δ > 0 en cada paso", tm.map((x) => f(x, 1)).join(", ") + " kg", V(tm.every((x, i) => i === 0 || x > tm[i - 1]))); }

  // ---- C4 unidades
  { const R = R0, A = Math.PI / 4 * (90e-3) ** 2;                                         // SI
    const mBaseSI = 7850 * (2.56 ** 2 - Math.PI / 4 * 0.12 ** 2) * 0.020;                 // kg
    const pBar = R.cd.F * 1e3 / A / 1e5;                                       // F[N]/A[m²]/1e5
    const qSI = R.ND * 1e3 / (Math.PI * ((1.0) ** 2 - (0.075) ** 2)) * (1 + 4 * 0.15 * 1.0 / (1.0 ** 2 + 0.075 ** 2)) / 1e6;
    const dd = [rel(R.m.base, mBaseSI), rel(R.cd.p, pBar), rel(R.q_max, qSI)];
    chk("C4 · Unidades: recálculo en SI (m, kg, Pa) de masa de la base, presión de diseño [bar] y q_máx [MPa]", "< 1e-9", `Δ = ${dd.map(sci).join("; ")}`, V(Math.max(...dd) < 1e-9)); }
  { const exact = 10000 * 0.0689476, conv = TT.PSI_CAT * 10000;
    chk("C4 · Conversión psi → bar del catálogo (PSI_CAT = 0,07 bar/psi)", "factor exacto 0,0689476; 10 000 psi = 689,5 bar", `con la convención de catálogo 700 bar ≙ 10 000 psi (+${pct(conv / exact - 1, 2)} sobre el valor exacto); el alivio por defecto 700 bar es 1,5 % mayor que 10 000 psi reales`, V(false, true), { sev: "menor", id: "psi", titulo: "Convención 10 000 psi ≙ 700 bar sobreestima 1,5 % la presión nominal del cilindro", correccion: "tt300c.js · PSI_CAT = 0.0689476 y, si el catálogo es de 700 bar, expresar p_rated en bar; o dejar la convención rotulada en la etiqueta (ya lo está)" }); }

  // ---- C5 equilibrio del patín: analítico vs Gauss
  { const Rr = R0, sc = strokeScan(base, Rr, 2000);
    let dF = 0, dFp = 0, dRf = 0, dRr = 0, dV = 0;
    Rr.stroke.forEach((s) => { const ind = shoeIndep(base, Rr.K, Rr.cd.T, s.th, s.H >= 0 ? 1 : -1);
      dF = Math.max(dF, rel(ind.F, s.F)); dFp = Math.max(dFp, rel(ind.Fp, s.Fp)); dRf = Math.max(dRf, Math.abs(ind.Rf - s.Rf) / Math.abs(s.Fp)); dRr = Math.max(dRr, Math.abs(ind.Rr - s.Rr) / Math.abs(s.Fp)); dV = Math.max(dV, rel(ind.Fvp, s.F)); });
    const dig = (x) => x <= 0 ? 16 : Math.min(16, -Math.log10(x));
    chk("C5 · Equilibrio del patín: fórmula cerrada (drive/atPt) vs eliminación de Gauss, en los 63 puntos de la carrera", "coincidencia a ≥ 5 cifras (rel. < 1e-5)", `F: ${sci(dF)} (${f(dig(dF), 1)} cifras); F_pas ${sci(dFp)}; R_f/F_pas ${sci(dRf)}; R_r/F_pas ${sci(dRr)}`, V(Math.max(dF, dFp, dRf, dRr) < 1e-5));
    chk("C5 · Equilibrio del patín: potencia virtual (η·F·v = T·ω/n + μ_s·F_pas·|v_desl| + μ_g·ΣR·v) vs fórmula cerrada", "< 1e-5 (4 y 5 cifras)", `${sci(dV)} (${f(dig(dV), 1)} cifras)`, V(dV < 1e-5));
    chk("C5 · Barrido de la carrera F(θ) con 2001 puntos: continuidad", "salto relativo entre puntos contiguos < 0,05 % salvo en y_p = r", `salto máx ${pct(sc.jump, 4)} en θ = ${f(sc.jumpAt / D2R, 2)}°; escalón de fricción en y_p = r: ${f(sc.atX[0], 2)} → ${f(sc.atX[1], 2)} kN (${pct(sc.atX[1] / sc.atX[0] - 1, 2)}); F máx ${f(sc.Fmax, 3)} kN vs cd.F ${f(R0.cd.F, 3)} kN (${sci(rel(sc.Fmax, R0.cd.F))})`, V(sc.jump < 5e-4 && rel(sc.Fmax, R0.cd.F) < 1e-3));
    chk("C5 · Sin división por cero ni F negativa en la carrera (denominador x_c − h·y_c)", "mín (x_c − h·y_c) > 0; F > 0", `den mín = ${f(sc.minDen, 1)} mm; puntos con F ≤ 0 o no finita: ${sc.nonPos}`, V(sc.minDen > 0 && sc.nonPos === 0));
    // curva de la UI: R.curve usa Fcyl(T, arm) = máx(F(−θ), F(+θ)): es la envolvente simétrica
    const th0 = R0.K.pts, dif = R0.curve.map((c, i) => { const s = R0.stroke.find((q) => Math.abs(q.th - th0[i].th) < 1e-12 && Math.abs(q.s - c.s) < 1e-9); return s ? (c.F - s.F) / s.F : 0; });
    chk("C5 · R.curve (F vs carrera mostrada) coincide con F(θ)", "Δ < 1e-6 o declarar que es la envolvente", `máx Δ = ${pct(maxOf(dif), 2)} (curve = máx(F(−θ), F(+θ)) por brazo: es la envolvente conservadora, no F(θ))`, V(maxOf(dif) < 1e-6, true), { sev: "menor", id: "curve", titulo: "R.curve muestra la envolvente simétrica máx(F(−θ), F(+θ)) y no F(θ)", correccion: "tt300c.js · compute(): curve = dpts.filter(d => d.s === ... ) → usar curve = K.pts.map(q => ({ s: q.s, arm: q.arm, F: atPt(drive(q.th, R_pin·sin(q.th) ≥ d_pin/2 ? 1 : −1), cd.T).F })) o rotular la gráfica «envolvente»" }); }
  // equilibrio con parámetros aleatorios (μ_s, μ_g, x_g, l_p, R_pin, N_pin)
  { let seed = 777; const rnd = () => (seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296; let dmax = 0, n = 0;
    for (let k = 0; k < 40; k++) { const Q = Object.assign({}, base, { mu_s: 0.05 + 0.5 * rnd(), mu_g: 0.05 + 0.5 * rnd(), x_g: 1100 + 300 * rnd(), l_p: 200 + 400 * rnd(), R_pin: 900 + 40 * rnd(), eta_c: 0.85 + 0.15 * rnd() });
      const RQ = TT.compute(Q); RQ.stroke.forEach((s) => { const ind = shoeIndep(Q, RQ.K, RQ.cd.T, s.th, s.H >= 0 ? 1 : -1); dmax = Math.max(dmax, rel(ind.F, s.F), rel(ind.Fvp, s.F)); n++; }); }
    chk("C5 · Equilibrio del patín con 40 combinaciones aleatorias de μ_s, μ_g, x_g, l_p, R_pin, η", "coincidencia a ≥ 5 cifras", `${n} puntos; Δ máx ${sci(dmax)}`, V(dmax < 1e-5)); }

  // ---- C6 barrido de todos los parámetros de PARAM_GROUPS
  { const t0 = Date.now(), res = { n: 0, exc: [], nan: [], neg: [], falseOk: [], verdictWrong: [], stroke: [], eq: [], tuhInf: 0 };
    const scan = (obj, p, out, depth) => { if (typeof obj === "number") { if (!isFinite(obj)) out.push(p); return; } if (!obj || typeof obj !== "object" || ArrayBuffer.isView(obj) || depth > 4) return; if (Array.isArray(obj)) { if (obj.length > 400) return; obj.forEach((v, i) => scan(v, p + "[" + i + "]", out, depth + 1)); } else for (const k of Object.keys(obj)) if (typeof obj[k] !== "function") scan(obj[k], p + "." + k, out, depth + 1); };
    for (const g of TT.PARAM_GROUPS) for (const [id, , , , mn, mx] of g.p) {
      if (mn === undefined) continue;
      const vals = [mn, mx]; for (let k = 1; k <= 5; k++) vals.push(mn + (mx - mn) * k / 6);
      for (const v0 of vals) {
        const v = +v0.toFixed(6), P = Object.assign({}, base, { [id]: v }); res.n++;
        const valid = AG.validate(P).filter((x) => x.lvl === "error").length === 0;
        let A; try { A = TT.analyze(P, QUICK ? { noFEA: true } : { coarse: true }); } catch (e) { res.exc.push({ id, v, valid, msg: e.message.slice(0, 80) }); continue; }
        const bad = []; scan(A.R, "R", bad, 0); if (A.fea) scan(A.fea, "fea", bad, 0);
        const real = bad;
        const badChecks = A.checks.filter((c) => c.kind !== "info" && c.kind !== "pend" && !isFinite(c.fu) && !(c.fu === Infinity && c.st === "fail")).map((c) => c.name);
        res.infFail = (res.infFail || 0) + A.checks.filter((c) => c.fu === Infinity && c.st === "fail").length; res.infFailBad = (res.infFailBad || 0) + A.checks.filter((c) => c.fu === Infinity && c.st !== "fail").length;
        if (real.length || badChecks.length) res.nan.push({ id, v, valid, what: real.slice(0, 3).concat(badChecks.slice(0, 2)) });
        const negm = Object.entries(A.R.m).filter(([, x]) => x < -1e-9).map(([k]) => k);
        const negq = ["Fstall", "q_max", "ND", "N"].filter((k) => A.R[k] < 0);
        if (negm.length || negq.length) res.neg.push({ id, v, valid, what: negm.concat(negq) });
        const sus = A.checks.filter((c) => c.st === "ok" && c.kind !== "info" && ((c.fu != null && c.fu < 0) || (c.cap != null && c.cap <= 0 && c.dem > 0)));
        if (sus.length) { res.falseOk.push({ id, v, valid, names: sus.map((c) => c.name), verdictOk: A.verdict.gira && A.verdict.estructura }); }
        if (A.fea && A.R.K.ok) { const e = [["top", A.fea.top], ["bot", A.fea.bot], ["lift", A.fea.lift]].filter(([, m]) => Math.abs(m.Rsum - m.Fapp) > 5e-3 * Math.abs(m.Fapp)); if (e.length) res.eq.push({ id, v, valid, m: e.map((x) => x[0]) }); }
        if (A.R.K.ok && A.R.cd) { const sc = strokeScan(P, A.R, 400); if (sc.jump > 0.02 || sc.nonPos || !(sc.minDen > 0)) res.stroke.push({ id, v, valid, jump: sc.jump, nonPos: sc.nonPos, minDen: sc.minDen }); }
      }
    }
    SWEEP = res;
    const nv = (arr) => arr.filter((x) => x.valid).length;
    console.log(`\nBarrido: ${res.n} casos (${QUICK ? "sin FEA" : "con FEA coarse"}), ${((Date.now() - t0) / 1000).toFixed(0)} s. Casos «válidos» = validate() sin errores.`);
    chk(`C6 · Barrido de PARAM_GROUPS (mín, máx y 5 intermedios; ${res.n} casos): excepciones`, "0", res.exc.length ? res.exc.slice(0, 4).map((x) => `${x.id}=${x.v}${x.valid ? "" : " (inválido)"}: ${x.msg}`).join(" | ") : "0", V(res.exc.length === 0));
    const nanV = res.nan.filter((x) => x.valid);
    chk("C6 · NaN / Infinity en R, FEA o en el FU de las verificaciones (FU = Infinity solo se acepta con estado «fail»)", "0 en entradas válidas (validate() sin errores); toda verificación con FU = Infinity debe estar en «fail"+"»", `${res.nan.length} casos (${nanV.length} válidos): ` + (res.nan.slice(0, 5).map((x) => `${x.id}=${x.v}${x.valid ? "" : "*"} ${x.what.join(",")}`).join(" | ") || "ninguno") + ` · verificaciones con FU = Infinity (no cumple): ${res.infFail || 0} (${res.infFailBad || 0} con estado distinto de fail)`, V(nanV.length === 0 && !res.infFailBad), { sev: "importante", id: "nan", titulo: "NaN/Infinity en entradas válidas", correccion: "(ver detalle)" });
    if (res.tuhInf) chk("C6 · R.ifc.tuhConf = Infinity cuando opt_ss = 1 (valor de relleno)", "no exportar Infinity (JSON lo convierte en null)", `${res.tuhInf} casos`, "obs", { sev: "menor", id: "tuhConf", titulo: "ifaceDesign() devuelve tuhConf = Infinity para la opción A", correccion: "tt300c.js · ifaceDesign(): let tuhConf = 0 (o NaN) cuando o ≠ 2; mostrar «–» en la UI" });
    res.neg.sort((a, b) => b.valid - a.valid); const negV = res.neg.filter((x) => x.valid);
    chk("C6 · Valores negativos imposibles (masas de componentes, F_calado, q_máx)", "0 en entradas válidas", `${res.neg.length} casos (${negV.length} válidos): ` + (res.neg.slice(0, 5).map((x) => `${x.id}=${x.v}${x.valid ? "" : "*"} ${x.what.join(",")}`).join(" | ") || "ninguno"), V(negV.length === 0, true), { sev: "menor", id: "neg-masa", titulo: "Masas de componentes negativas con geometrías imposibles pero «válidas» para validate()", correccion: "tt300c.js · masses(): Math.max(0, ·) en m.dogs y m.hub; agentes.js · validate(): errores para x_g − w_s/2 < D_top/2 y D_piv + 30 ≥ D_hub" });
    const fo = res.falseOk, foV = fo.filter((x) => x.valid), foVerd = fo.filter((x) => x.verdictOk);
    chk("C6 · Verificaciones con FU negativo (capacidad ≤ 0) clasificadas «ok» (falso aprobado)", "0 casos", `${fo.length} casos (${foV.length} válidos; ${foVerd.length} con veredicto global OK): ` + (foVerd.slice(0, 4).map((x) => `${x.id}=${x.v}: ${x.names[0].slice(0, 45)}`).join(" | ") || "ninguno"), V(fo.length === 0), { sev: "importante", id: "fu-negativo", titulo: "Una verificación con capacidad ≤ 0 (o demanda < 0) da FU negativo y se marca «ok» (falso aprobado; p. ej. β_ch = 80° con μ_ret = 0,2: el chaflán se autobloquea y el veredicto dice «gira»)",
      correccion: "tt300c.js · verifs() → add(): reemplazar `fu: o.fu != null ? o.fu : o.dem / o.cap` por `fu: o.fu != null ? o.fu : ((o.cap > 0 && o.dem >= 0) ? o.dem / o.cap : Infinity)`; el bloque final ya clasifica `!isFinite(c.fu)` como «fail». Con esto fallan «Retorno sin autobloqueo» (β ≥ 76°), «Fondo de la ranura de la bancada» (t_bed < h_slot + h_tee), «Uña dentro de la luz libre», etc." });
    chk("C6 · Equilibrio ΣF = ΣR de los tres modelos FEA en el barrido", "< 0,5 % salvo geometrías inválidas", `${res.eq.length} casos fuera (${res.eq.filter((x) => x.valid).length} válidos)${res.eq.length ? ": " + res.eq.slice(0, 3).map((x) => `${x.id}=${x.v}${x.valid ? "" : "*"} ${x.m}`).join(" | ") : ""}`, V(res.eq.filter((x) => x.valid).length === 0));
    const stV = res.stroke.filter((x) => x.valid);
    chk("C6 · F(θ) continua, finita y positiva en todo el barrido (salto > 2 % entre puntos de 1/400 de la carrera, denominador ≤ 0)", "0 casos en entradas válidas", `${res.stroke.length} casos (${stV.length} válidos)` + (res.stroke.length ? ": " + res.stroke.slice(0, 3).map((x) => `${x.id}=${x.v}: salto ${pct(x.jump, 1)}, den mín ${f(x.minDen, 1)}`).join(" | ") : ""), V(stV.length === 0)); }
});

/* =================================================================================================================================================
   D · INTERFACES (opt_ss, opt_uhmw)
   ================================================================================================================================================= */
runSection("D", "Las tres interfaces: acero–acero, A (discos inoxidables), B (discos + UHMW)", () => {
  const OPT = [["acero–acero", 0, 0], ["A inox", 1, 0], ["B UHMW", 0, 1]], one = (o, extra) => { const P = Object.assign(TT.defaults(), { opt_ss: OPT[o][1], opt_uhmw: OPT[o][2] }, extra || {}); const A = TT.analyze(P, { noFEA: true }); return { P, A, R: A.R }; };
  // masas y consistencia de las tres opciones con el diseño por defecto
  const d0 = one(0), dA = one(1), dB = one(2), rows_ = [d0, dA, dB];
  table(["opción", "t_disco [mm]", "t_UHMW [mm]", "Δ [mm]", "μ_d", "m_discos [kg]", "m_UHMW [kg]", "m_total [kg]", "h_eje [mm]", "F_dis [kN]", "FS", "q_máx [MPa]", "gira", "estructura"],
    rows_.map((x, i) => [OPT[i][0], x.R.ifc.tss, x.R.ifc.tuh, x.R.ifc.delta, x.R.mu.d, f(x.R.m.ss, 1), f(x.R.m.uhmw, 1), f(x.R.m.total, 1), f(x.R.hax, 1), f(x.R.cd.F, 2), f(x.R.cd.FS, 3), f(x.R.q_max, 3), x.A.verdict.gira, x.A.verdict.estructura]));
  { const Ao = Math.PI * ((dA.P.D_top / 2) ** 2 - (dA.P.D_piv / 2 + 15) ** 2), e = [];
    e.push(rel(dA.R.m.ss, 2 * 7.93e-6 * Ao * dA.R.ifc.tss), rel(dB.R.m.uhmw, 0.94e-6 * Ao * dB.R.ifc.tuh), rel(dA.R.hax, dA.P.h_disc / 2 + 2 * dA.R.ifc.tss), rel(dB.R.hax, dB.P.h_disc / 2 + 2 * dB.R.ifc.tss + dB.R.ifc.tuh));
    const sum = (x) => x.R.m.disc + x.R.m.ss + x.R.m.uhmw + x.R.m.base + x.R.m.rim + x.R.m.brackets + x.R.m.dogs + x.R.m.shoes + x.R.m.beds + x.R.m.pivot + x.R.m.cyl;
    e.push(rel(sum(d0), d0.R.m.total), rel(sum(dA), dA.R.m.total), rel(sum(dB), dB.R.m.total));
    chk("D1 · Masas: m_disco = 2ρ_inox·A·t; m_UHMW = ρ·A·t; h_eje = h/2 + Δ; suma de componentes = total", "< 1e-12", sci(maxOf(e)), V(maxOf(e) < 1e-12)); }
  { const wr = rows_.map((x, i) => `${OPT[i][0]}: ` + (x.A.checks.filter((c) => c.st === "warn").map((c) => `${c.name.slice(0, 40)} FU ${f(c.fu, 3)}`).join(", ") || "sin advertencias") + `; FU est. máx ${f(maxOf(x.A.checks.filter((c) => c.sys === "est" && c.kind === "fu" && c.fu != null).map((c) => c.fu)), 3)} (sin FEA)`);
    chk("D1 · Advertencias (FU 0,90–1,00) que introduce cada interfaz (sin FEA; la altura Δ sube el eje de los cilindros y el brazo de las ménsulas)", "informar", wr.join(" | "), "OK"); }
  { const sets = [[d0.R.mu, TT.defaults(), ["mu_nom", "mu_d", "mu_cont", "mu_dry"]], [dA.R.mu, TT.defaults(), ["muA_nom", "muA_d", "muA_cont", "muA_dry"]], [dB.R.mu, TT.defaults(), ["muB_nom", "muB_d", "muB_cont", "muB_dry"]]];
    const ok = sets.every(([m, P, k]) => m.nom === P[k[0]] && m.d === P[k[1]] && m.cont === P[k[2]] && m.dry === P[k[3]]);
    chk("D1 · μ de cada opción (nominal, diseño, contaminado, seco)", "coinciden con el conjunto de parámetros de la opción", ok ? "coinciden" : "no coinciden", V(ok)); }
  { const t = [dA.R.ifc.tss, dB.R.ifc.tss], u = dB.R.ifc.tuh, ok = t.every((x) => [3, 4, 5, 6, 8, 10, 12, 15, 20, 25].includes(x)) && [3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50].includes(u) && dA.R.ifc.tss >= dA.R.ifc.tssReq && dB.R.ifc.tuh >= dB.R.ifc.tuhReq;
    chk("D1 · Espesores comerciales ≥ requeridos (discos y UHMW por defecto)", "t ∈ lista comercial y ≥ t_req", `disco ${t.join(", ")} mm (req. ${f(dA.R.ifc.tssReq, 2)}); UHMW ${u} mm (req. ${f(dB.R.ifc.tuhReq, 2)})`, V(ok)); }
  { let thrown = false; try { TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, opt_uhmw: 1 }), { noFEA: true }); } catch (e) { thrown = /excluyentes/.test(e.message); }
    const vErr = AG.validate(Object.assign(TT.defaults(), { opt_ss: 1, opt_uhmw: 1 })).some((v) => v.lvl === "error");
    chk("D1 · opt_ss = opt_uhmw = 1 (excluyentes)", "validate() da error y analyze() lanza error explícito", `validate: ${vErr ? "error" : "sin error"}; analyze(): ${thrown ? "lanza «excluyentes»" : "calcula en silencio"}`, V(vErr && thrown), { sev: "menor", id: "excl", titulo: "analyze() acepta opt_ss = opt_uhmw = 1 sin avisar", correccion: "tt300c.js · analyze(): lanzar error si ambas opciones están activas" }); }

  // barridos W y e
  const Ws = Array.from({ length: 21 }, (_, i) => 100 + 25 * i), Es = Array.from({ length: 13 }, (_, i) => 25 * i);
  const grab = (o, ex) => { const x = one(o, ex), R = x.R; return { m: R.m.total, tss: R.ifc.tss, tuh: R.ifc.tuh, d: R.ifc.delta, hax: R.hax, q: R.q_max, F: R.cd.F, FS: R.cd.FS, N: R.N, gira: x.A.verdict.gira, est: x.A.verdict.estructura, bad: x.A.checks.filter((c) => c.st === "fail").map((c) => c.name) }; };
  const mono = (arr, key, dir, tol) => { for (let i = 1; i < arr.length; i++) { const d = arr[i][key] - arr[i - 1][key]; if (dir * d < -(tol || 1e-9) * Math.abs(arr[i][key])) return false; } return true; };
  for (const [name, vals, mk] of [["W_tf", Ws, (v) => ({ W_tf: v })], ["e", Es, (v) => ({ e: v })]]) {
    const data = OPT.map((_, o) => vals.map((v) => Object.assign({ v }, grab(o, mk(v)))));
    console.log(`\nBarrido de ${name} (${vals[0]}…${vals[vals.length - 1]}), resultados de las 3 opciones:`);
    const hdr = ["v"]; OPT.forEach((o) => hdr.push(`${o[0]}: m [kg]`, "t_disco", "t_UHMW", "F [kN]", "FS", "q [MPa]", "gira/est"));
    table(hdr, vals.map((v, i) => { const r = [v]; data.forEach((d) => r.push(f(d[i].m, 0), d[i].tss, d[i].tuh, f(d[i].F, 1), f(d[i].FS, 3), f(d[i].q, 3), (d[i].gira ? "G" : "–") + "/" + (d[i].est ? "E" : "–"))); return r; }));
    OPT.forEach((o, k) => {
      const d = data[k], monoOk = mono(d, "m", 1) && mono(d, "tss", 1) && mono(d, "tuh", 1) && mono(d, "d", 1) && mono(d, "hax", 1) && mono(d, "q", 1) && mono(d, "F", 1) && mono(d, "FS", -1) && mono(d, "N", 1);
      // saltos: la masa solo puede cambiar cuando cambia un espesor comercial; F debe estar a < 0,5 % de la recta que une los extremos (efecto de la masa del disco rotatorio)
      const stepsBad = [], stepsOk = []; for (let i = 1; i < d.length; i++) { const dm = d[i].m - d[i - 1].m, chg = d[i].tss !== d[i - 1].tss || d[i].tuh !== d[i - 1].tuh; if (chg) stepsOk.push(`${vals[i]}: +${f(dm, 0)} kg (${pct(dm / d[i - 1].m, 1)}), Δ ${d[i - 1].d}→${d[i].d} mm`); if (!chg && Math.abs(dm) > 1e-9) stepsBad.push(vals[i]); }
      const lin = d.map((x, i) => x.F - (d[0].F + (d[d.length - 1].F - d[0].F) * (vals[i] - vals[0]) / (vals[vals.length - 1] - vals[0]))), devF = maxOf(lin.map((x, i) => Math.abs(x) / d[i].F));
      
      chk(`D2 · ${o[0]}, barrido de ${name}: monotonía de m, t, Δ, h_eje, q, F, N (↑) y FS (↓)`, "monótono (sin retrocesos)", monoOk ? "monótono" : "NO monótono", V(monoOk));
      chk(`D2 · ${o[0]}, barrido de ${name}: saltos de masa solo en cambios de espesor comercial; F sin saltos`, "masa constante entre cambios de t; F(" + name + ") afín: desvío de la recta de los extremos < 0,5 % (los escalones de t no la perturban)", `${stepsOk.length ? "escalones: " + stepsOk.join("; ") : "sin escalones"}; masa cambia sin cambio de espesor: ${stepsBad.length ? stepsBad.join(",") : "nunca"}; desvío de F respecto de la recta ${pct(devF, 3)}`, V(!stepsBad.length && devF < 0.005));
      const flip = d.findIndex((x, i) => i > 0 && (x.gira !== d[i - 1].gira || x.est !== d[i - 1].est));
      if (flip > 0) console.log(`  · ${o[0]}: cambia el veredicto (gira/estructura) en ${name} = ${vals[flip]} (de ${d[flip - 1].gira}/${d[flip - 1].est} a ${d[flip].gira}/${d[flip].est}); verificaciones que fallan: ${d[flip].bad.filter((b) => !d[flip - 1].bad.includes(b)).map((b) => b.slice(0, 60)).join(" | ")}`);
      const infinite = d.filter((x) => !isFinite(x.d) || !isFinite(x.m) || !isFinite(x.F));
      chk(`D2 · ${o[0]}, barrido de ${name}: sin Infinity/NaN`, "0", infinite.length + " puntos", V(!infinite.length), { sev: "importante", id: "ifc-inf-" + o[1] + o[2] + name, titulo: `Infinity/NaN en la interfaz ${o[0]} al barrer ${name}`, correccion: "ifaceDesign(): si p_uhmw ≤ q devuelve Infinity; propagar como falla explícita" });
    });
  }
  // escalón combinado: ΔF/F de cada cambio de espesor
  { const x1 = grab(1, { W_tf: 300 }), x2 = grab(1, { W_tf: 600 });
    chk("D3 · Δ de la interfaz sube el eje de los cilindros; la cinemática y F no dependen de Δ", "F(opción A) − F(acero–acero) debido solo a la masa agregada (< 0,5 %)", `F: ${f(d0.R.cd.F, 2)} (acero) vs ${f(dA.R.cd.F, 2)} (A) → ${pct(dA.R.cd.F / d0.R.cd.F - 1, 3)}; W 300→600: t_disco ${x1.tss} → ${x2.tss} mm`, V(Math.abs(dA.R.cd.F / d0.R.cd.F - 1) < 0.005)); }
});

/* =================================================================================================================================================
   E · OPTIMIZADOR DE PESO
   ================================================================================================================================================= */
runSection("E", "Optimizador de peso (agentes.js: optimize / optimizeGen)", () => {
  const starts = [["defecto", TT.defaults()], ["t = 30 mm", Object.assign(TT.defaults(), { t_top: 30, t_bot: 30, t_base: 30 })]];
  const keyOf = (P) => JSON.stringify(P), out = [];
  for (const [nm, P0] of starts) {
    const m0 = TT.masses(P0).total, t0 = Date.now(), mon = [], s1 = [];
    let o1; for (const s of AG.optimizeGen(P0)) { if (s.phase === "descenso") mon.push(s.A.R.m.total); s1.push(s); o1 = s; }
    const dt = Date.now() - t0, o2 = AG.optimize(P0);
    const same = keyOf(o1.P) === keyOf(o2.P) && o1.A.R.m.total === o2.A.R.m.total && o1.evals === o2.evals;
    const A = TT.analyze(o1.P), fe = AG.feasible(A, 0.90), val = AG.validate(o1.P).filter((x) => x.lvl === "error");
    const incr = mon.some((x, i) => i > 0 && x > mon[i - 1] + 1e-6), diff = Object.keys(P0).filter((k) => o1.P[k] !== P0[k]).map((k) => `${k}: ${P0[k]}→${o1.P[k]}`);
    const fuEst = A.checks.filter((c) => c.sys === "est" && c.kind === "fu" && c.fu != null).map((c) => c.fu);
    // caché escalada vs FEA completo (3 %)
    const cache = new Map(); TT.analyze(P0, { cache }); const As = TT.analyze(o1.P, { cache }), Af = A;
    const dv = [["σ_vm sup.", As.fea.top.vmMax, Af.fea.top.vmMax], ["σ_vm inf.", As.fea.bot.vmMax, Af.fea.bot.vmMax], ["q_línea sup.", As.fea.top.lineMax, Af.fea.top.lineMax], ["q_línea inf.", As.fea.bot.lineMax, Af.fea.bot.lineMax]].map(([n, a, b]) => [n, Math.abs(a - b) / b]);
    const chkFu = ["Plancha superior: global + local", "Plancha inferior: global + local", "Soldadura alma/nervio–plancha (2 filetes)"].map((n) => [n, Math.abs(As.checks.find((c) => c.name === n).fu / Af.checks.find((c) => c.name === n).fu - 1)]);
    out.push({ nm, o1, m0, dt, same, A, fe, val, incr, diff });
    console.log(`\nInicio «${nm}»: m₀ = ${f(m0, 1)} kg → m_opt = ${f(o1.A.R.m.total, 1)} kg (${pct(o1.A.R.m.total / m0 - 1, 1)}), ${o1.evals} evaluaciones, ${f(dt / 1e3, 1)} s. Cambios: ${diff.join(", ")}`);
    chk(`E1 · Determinismo (2 corridas desde ${nm})`, "mismo diseño, masa y número de evaluaciones, bit a bit", same ? `idénticos (m = ${o1.A.R.m.total}, ${o1.evals} evals)` : "DIFIEREN", V(same));
    chk(`E1 · Factibilidad del resultado con analyze completo (malla por defecto), desde ${nm}`, "feasible(A, 0,90): sin «fail», FU estructural ≤ 0,90; veredicto gira y estructura", `${fe ? "factible" : "NO factible"}; FU est. máx = ${f(maxOf(fuEst), 3)}; gira ${A.verdict.gira}, est. ${A.verdict.estructura}; o.ok = ${o1.ok}`, V(fe && o1.ok && A.verdict.gira && A.verdict.estructura));
    chk(`E1 · Resultado válido según validate() (desde ${nm})`, "0 errores", val.length ? val.map((x) => x.msg).join("; ") : "0 errores", V(val.length === 0));
    chk(`E1 · La masa no sube (final ≤ inicial; pasos de descenso no crecientes), desde ${nm}`, "m_opt ≤ m₀", `${f(o1.A.R.m.total, 1)} ≤ ${f(m0, 1)} kg; descenso monótono: ${!incr}`, V(o1.A.R.m.total <= m0 + 1e-6 && !incr));
    chk(`E1 · Caché FEA escalada vs FEA completo al final (desde ${nm})`, "|Δ| < 3 % en σ_vm y q_línea de las dos planchas", dv.map(([n, d]) => `${n} ${pct(d, 2)}`).join("; ") + `; FU global+local/soldadura: ${chkFu.map(([, d]) => pct(d, 2)).join(", ")}`, V(maxOf(dv.map((x) => x[1])) < 0.03));
  }
  chk("E1 · Resultado del optimizador idéntico desde ambos puntos de partida", "informar", out[0].o1.A.R.m.total === out[1].o1.A.R.m.total ? `misma masa ${f(out[0].o1.A.R.m.total, 1)} kg` : `${f(out[0].o1.A.R.m.total, 1)} vs ${f(out[1].o1.A.R.m.total, 1)} kg`, "OK");
  // malla usada por el optimizador
  chk("E1 · Malla que usa el optimizador", "informar (el enunciado supone «coarse»)", "agentes.js:195 llama analyze(Q, {cache}) sin coarse: usa la malla por defecto con caché escalada y confirma el final con analyze(Q) nuevo", "OK");
  // sensibilidad de la caché (rango de espesores) — informativo
  { const b = TT.defaults(), cache = new Map(); TT.analyze(b, { cache }); const rows2 = []; let worst = 0, worstLine = 0;
    for (const [k, vals] of [["t_top", [10, 12, 16, 25, 30, 40, 50]], ["t_bot", [10, 12, 20, 25, 30, 40, 50]]]) for (const v of vals) { const P = Object.assign({}, b, { [k]: v }), a = TT.analyze(P, { cache }), fr = TT.analyze(P);
      const w = k === "t_top" ? rel(a.fea.top.vmMax, fr.fea.top.vmMax) : rel(a.fea.bot.vmMax, fr.fea.bot.vmMax), wl = k === "t_top" ? rel(a.fea.top.lineMax, fr.fea.top.lineMax) : rel(a.fea.bot.lineMax, fr.fea.bot.lineMax);
      worst = Math.max(worst, w); worstLine = Math.max(worstLine, wl); rows2.push(`${k}=${v}: σ ${pct(w, 1)}, q ${pct(wl, 1)}`); }
    chk("E2 · Caché escalada: σ ∝ q/t² frente a FEA nuevo para t = 10…50 mm (base t_top = 20, t_bot = 16)", "σ_vm < 3 %; q_línea < 3 % (el optimizador confirma el final con FEA nuevo)", `σ máx ${pct(worst, 2)}; q_línea máx ${pct(worstLine, 2)} (${rows2.filter((x, i) => i % 3 === 0).join("; ")})`, V(worst < 0.03 && worstLine < 0.03, true), { sev: "menor", id: "cache-q", titulo: "La caché escalada del optimizador subestima/sobreestima q_línea de la plancha inferior hasta ≈ 3 % al cambiar t_bot (el reparto de reacciones depende de t por el cortante de Mindlin)", correccion: "agentes.js/tt300c.js · discCached(): incluir t en la clave de la caché para t_bot (key += t) o aplicar la corrección solo a σ; el final ya se confirma con analyze(Q) nuevo (fase 3), así que no afecta el resultado" }); }

  // búsqueda aleatoria
  { const Mopt = out[0].o1.A.R.m.total, VARS = AG.VARS; let seed = 20260410; const rnd = () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const base = TT.defaults(), cache = new Map(); TT.analyze(base, { cache });
    const sample = (span) => { const Q = Object.assign({}, base); for (const [k, list] of VARS) { if (rnd() > 0.35) continue; const i0 = Math.max(0, list.findIndex((v) => v >= base[k] - 1e-9)), i = Math.min(list.length - 1, Math.max(0, i0 + Math.round((rnd() * 2 - 1) * span))); Q[k] = list[i]; } return Q; };
    // (a) 200 puntos factibles (muestreo por rechazo: cribado sin FEA y luego analyze con caché)
    const feas = []; let tries = 0, scr = 0; const tt0 = Date.now();
    while (feas.length < 200 && Date.now() - tt0 < 90000 && tries < 400000) {
      const Q = sample(3); tries++;
      if (AG.validate(Q).some((v) => v.lvl === "error")) continue;
      const a0 = TT.analyze(Q, { noFEA: true }); if (!AG.feasible(a0, 0.9)) continue; scr++;
      const A = TT.analyze(Q, { cache }); if (AG.feasible(A, 0.9)) feas.push({ m: TT.masses(Q).total, Q });
    }
    const mb = feas.length ? minOf(feas.map((x) => x.m)) : NaN, better = feas.filter((x) => x.m < Mopt - 1e-6);
    // (b) intento dirigido: 60 000 muestras (±4 pasos); solo se evalúan las de masa < óptimo
    let cand = 0, found = [], tries2 = 0; const t1 = Date.now();
    while (tries2 < 60000 && Date.now() - t1 < 60000) { const Q = sample(4); tries2++; const m = TT.masses(Q).total; if (m >= Mopt - 1e-6) continue; cand++; if (AG.validate(Q).some((v) => v.lvl === "error")) continue; const a0 = TT.analyze(Q, { noFEA: true }); if (!AG.feasible(a0, 0.9)) continue; const A = TT.analyze(Q); if (AG.feasible(A, 0.9)) found.push({ m, Q, falseOk: A.checks.filter((c) => c.st === "ok" && c.fu != null && c.fu < 0).map((c) => c.name) }); }
    chk("E3 · Búsqueda aleatoria de 200 puntos factibles (±3 pasos de la lista de tamaños alrededor del diseño por defecto; solo informar)", "informar: ¿hay algún factible más liviano que el óptimo?", `${feas.length} factibles en ${tries} muestras (${((Date.now() - tt0) / 1e3).toFixed(0)} s); mejor masa aleatoria ${f(mb, 1)} kg vs óptimo ${f(Mopt, 1)} kg; más livianos que el óptimo: ${better.length}`, "OK");
    found.sort((a, b) => a.m - b.m);
    chk("E3 · Búsqueda aleatoria dirigida (60 000 muestras ±4 pasos; solo se evalúan las de masa < óptimo)", "informar: puntos factibles más livianos que el óptimo", `${cand} candidatas más livianas que ${f(Mopt, 1)} kg; «factibles» según analyze completo: ${found.length}${found.length ? "; mejor " + f(found[0].m, 1) + " kg (" + Object.keys(base).filter((k) => found[0].Q[k] !== base[k]).map((k) => k + "→" + found[0].Q[k]).join(", ") + "); de ellas con una verificación de FU negativo aprobada en falso: " + found.filter((x) => x.falseOk.length).length + (found[0].falseOk.length ? " (la mejor: " + found[0].falseOk.join(", ") + ")" : "") : ""}`, found.length ? "obs" : "OK"); }
  { const A = TT.analyze(out[0].o1.P), top = A.checks.filter((c) => c.fu != null && c.kind === "fu" && c.sys === "est").sort((a, b) => b.fu - a.fu).slice(0, 4);
    chk("E4 · FU más altos del diseño optimizado (el optimizador llena hasta FU = 0,90 con k_FEA = 1,15)", "informar", top.map((c) => `${c.name.slice(0, 42)} ${f(c.fu, 3)}`).join("; "), "OK"); }
});

/* =================================================================================================================================================
   F · REPRODUCIBILIDAD Y GOLDEN
   ================================================================================================================================================= */
runSection("F", "Redondeo, reproducibilidad y golden file", () => {
  const strip = (o) => JSON.stringify(o, (k, v) => k === "ms" ? undefined : ArrayBuffer.isView(v) ? Array.from(v) : typeof v === "function" ? undefined : (typeof v === "number" && !isFinite(v)) ? String(v) : v);
  const runs = [0, 1, 2].map(() => TT.analyze(TT.defaults())), s = runs.map(strip), h = s.map((x) => crypto.createHash("sha256").update(x).digest("hex").slice(0, 16));
  const eq = s[0] === s[1] && s[1] === s[2];
  chk("F1 · analyze() ×3 con los valores por defecto: salida completa (R, FEA con desplazamientos nodales, verificaciones)", "idéntica bit a bit", `${eq ? "idénticas" : "DIFIEREN"}; SHA-256 ${h.join(" / ")}; ${(s[0].length / 1e6).toFixed(1)} MB`, V(eq));
  { const a = TT.analyze(TT.defaults(), { noFEA: true }), b = TT.analyze(TT.defaults(), { noFEA: true });
    chk("F1 · analyze() ×2 sin FEA", "idéntica bit a bit", strip(a) === strip(b) ? "idénticas" : "DIFIEREN", V(strip(a) === strip(b))); }
  // golden
  const A = runs[0], R = A.R, snap = { masa_total: R.m.total, masa_mesa: R.m.disc, N: R.N, q_max: R.q_max, F_calado: R.Fstall, brazo_min: R.K.armMin, carrera_req: R.K.s_req,
    casos: Object.fromEntries(R.cases.map((c) => [c.id, [c.F, c.p, c.FS]])), fea: { top: A.fea.top.vmMax, bot: A.fea.bot.vmMax, lift: A.fea.lift.vmMax, glob: A.fea.glob.Mmax }, fu: Object.fromEntries(A.checks.filter((c) => c.fu != null).map((c) => [c.grp + " · " + c.name, c.fu])) };
  const gf = path.join(__dirname, "golden", "tt300c_defaults.json");
  if (!fs.existsSync(gf)) chk("F2 · Golden file", "existe", "no existe", "falla");
  else {
    const g = JSON.parse(fs.readFileSync(gf, "utf8")); let maxd = 0, n = 0, miss = 0;
    const cmp = (a, b) => { if (typeof b === "number") { n++; maxd = Math.max(maxd, rel(a, b)); } else if (Array.isArray(b)) b.forEach((v, i) => cmp(a[i], v)); else for (const k of Object.keys(b)) { if (!(k in a)) miss++; else cmp(a[k], b[k]); } };
    cmp(snap, g);
    chk("F2 · Resultados por defecto vs tests/golden/tt300c_defaults.json (solo lectura)", "desviación relativa < 1e-6 en todos los valores", `${n} valores; desviación máx ${sci(maxd)}; claves ausentes ${miss}; claves nuevas en el cálculo no cubiertas: ${Object.keys(snap.fu).filter((k) => !(k in g.fu)).length}`, V(maxd < 1e-6 && !miss)); }
  { const gp = path.join(__dirname, "golden", "params_defaults.json"); if (fs.existsSync(gp)) { const g = JSON.parse(fs.readFileSync(gp, "utf8")), P = TT.defaults(); const d = Object.keys(P).filter((k) => g[k] !== P[k]).concat(Object.keys(g).filter((k) => !(k in P)));
      chk("F2 · Parámetros por defecto vs tests/golden/params_defaults.json", "idénticos", d.length ? "difieren: " + d.join(", ") : `${Object.keys(P).length} parámetros idénticos`, V(!d.length)); } }
  // redondeo: el resultado no depende del orden de las claves ni de la forma de pasar P
  { const P = TT.defaults(), Q = {}; Object.keys(P).reverse().forEach((k) => { Q[k] = P[k]; });
    const a = strip(TT.analyze(P, { noFEA: true })), b = strip(TT.analyze(Q, { noFEA: true }));
    chk("F3 · Orden de las claves de P (reverso)", "resultado idéntico", a.replace(/"P":\{.*?\},"R"/, "") === b.replace(/"P":\{.*?\},"R"/, "") ? "idéntico" : "DIFIERE", V(a.replace(/"P":\{.*?\},"R"/, "") === b.replace(/"P":\{.*?\},"R"/, ""))); }
  { const P0 = TT.defaults(), P1 = Object.assign({}, P0, { W_tf: 300.00000000001 }), a = TT.analyze(P0, { noFEA: true }), b = TT.analyze(P1, { noFEA: true });
    chk("F3 · Estabilidad frente a perturbaciones de 1e-13 en W_tf (sin saltos por redondeo en los espesores comerciales)", "m_total y F_dis dentro de 1e-9", `Δm ${sci(rel(a.R.m.total, b.R.m.total))}; ΔF ${sci(rel(a.R.cd.F, b.R.cd.F))}`, V(rel(a.R.m.total, b.R.m.total) < 1e-9 && rel(a.R.cd.F, b.R.cd.F) < 1e-9)); }
});

/* =================================================================================================================================================
   G · VERIFICACIONES DE ACEPTACIÓN DEL DISEÑO POR DEFECTO
   ================================================================================================================================================= */
runSection("G", "Verificaciones de aceptación del diseño por defecto", () => {
  const A = TT.analyze(TT.defaults()), fails = A.checks.filter((c) => c.st === "fail"), warns = A.checks.filter((c) => c.st === "warn");
  chk("G1 · Ninguna verificación del diseño por defecto en «fail»", "0 fail", `${fails.length} fail, ${warns.length} warn, ${A.checks.length} verificaciones; gira ${A.verdict.gira}, estructura ${A.verdict.estructura}, pendientes ${A.verdict.pend}`, V(fails.length === 0 && A.verdict.gira && A.verdict.estructura));
  const hi = A.checks.filter((c) => c.fu != null && isFinite(c.fu) && c.fu >= 0.95).sort((a, b) => b.fu - a.fu);
  const zeroAll = hi.filter((c) => Math.abs(c.fu - 1) < 1e-9), zero = zeroAll.filter((c) => c.kind === "geo");
  console.log("\nVerificaciones con FU ≥ 0,95 (margen ≤ 5 %):");
  table(["FU", "tipo", "grupo · verificación", "demanda", "capacidad", "unidad", "holgura"], hi.map((c) => [f(c.fu, 4), c.kind + (c.sys === "giro" ? "/giro" : ""), c.grp + " · " + c.name, f(c.dem, 3), f(c.cap, 3), c.unit, f(c.cap - c.dem, 3) + " " + c.unit]));
  console.log("\nGeométricas con FU = 1,00 (holgura cero, dem = cap): " + zero.map((c) => c.name).join(" | ") + "\nNo geométricas con FU = 1,00: " + zeroAll.filter((c) => c.kind !== "geo").map((c) => c.name + " (" + c.dem + " " + c.unit + " frente a " + f(c.cap, 3) + ")").join(" | "));
  chk("G2 · Verificaciones con FU ≥ 0,95", "listar (el usuario decide)", `${hi.length}: ` + hi.map((c) => `${c.name.slice(0, 40)} (${f(c.fu, 3)})`).join("; "), "OK");
  chk("G2 · Geométricas con holgura cero (FU = 1,00)", "listar; las de seguridad no deben tener holgura cero", `${zero.length}: ` + zero.map((c) => c.name.slice(0, 55)).join("; ") + `; más el alivio 700 bar = 10 000 psi (convención)`, zero.length ? "obs" : "OK", zero.length ? { sev: "menor", id: "holgura-cero", titulo: `${zero.length} verificaciones geométricas del diseño por defecto (y el alivio de presión) cumplen con holgura exactamente cero (FU = 1,00)`, correccion: "Son restricciones activas del diseño (mínimos de fabricación o ajustes), no errores: boca del alojamiento 140 = 140 mm, patín fuera de la mesa 1015 = 1015, cilindro/ménsula dentro de la base 1265 = 1265, filete mínimo 6 = 6, fondo de la ranura de la bancada 12 = 12 mm; confirmar en plano. Cualquier cambio de 1 mm hacia el lado desfavorable las pone en «fail»" } : undefined);
  const alivio = A.checks.find((c) => /Alivio dentro/.test(c.name));
  chk("G2 · Alivio 700 bar vs presión nominal 10 000 psi", "FU < 1,00 con el factor exacto 0,0689476 bar/psi", `con la convención del proyecto FU = ${f(alivio.fu, 4)}; con el factor exacto FU = ${f(700 / (10000 * 0.0689476), 4)}`, V(700 / (10000 * 0.0689476) <= 1 + 1e-9, true));
  const fuMesa = A.checks.filter((c) => c.sys === "est" && c.kind === "fu" && c.fu != null).sort((a, b) => b.fu - a.fu).slice(0, 5);
  chk("G3 · Estructura: FU máximo de las verificaciones con FU (kind = fu)", "≤ 0,90 (veredicto «ok», sin advertencias)", fuMesa.map((c) => `${c.name.slice(0, 38)} ${f(c.fu, 3)}`).join("; "), V(fuMesa[0].fu <= 0.9));
  const lift = A.checks.find((c) => /Izaje del conjunto/.test(c.name));
  chk("G3 · Verificación de izaje (σ_vm × k_FEA en la plancha base)", "no usar tensiones singulares como verificación", `FU = ${f(lift.fu, 3)} con el máximo global en la esquina del apoyo (ver B3)`, "OK");
});

/* =================================================================================================================================================
   RESUMEN
   ================================================================================================================================================= */
console.log("\n# RESUMEN GENERAL");
const nOK = rows.filter((r) => r.st === "OK").length, nObs = rows.filter((r) => r.st === "obs").length, nF = rows.filter((r) => r.st === "falla").length;
console.log(`Pruebas: ${rows.length} (${nOK} OK, ${nObs} observaciones, ${nF} fallas)${QUICK ? " [modo --quick: barrido sin FEA]" : ""}${FULL ? " [modo --full]" : ""}`);
const order = { "crítica": 0, "importante": 1, "menor": 2 };
hall.sort((a, b) => order[a.sev] - order[b.sev]);
console.log("\n## HALLAZGOS");
hall.forEach((h, i) => console.log(`${i + 1}. [${h.sev.toUpperCase()}] ${h.titulo}\n   Evidencia: ${h.detalle}\n   Corrección: ${h.correccion}`));
const nC = hall.filter((h) => h.sev === "crítica").length, nI = hall.filter((h) => h.sev === "importante").length, nM = hall.filter((h) => h.sev === "menor").length;
console.log(`\nTiempo total: ${((Date.now() - T_START) / 1000).toFixed(0)} s`);
const okAll = nC === 0 && nI === 0;
console.log(`RESULTADO: ${okAll ? "APTO" : "NO APTO"} — ${rows.length} pruebas (${nOK} OK, ${nObs} obs., ${nF} fallas); hallazgos: ${nC} críticos, ${nI} importantes, ${nM} menores`);
process.exit(okAll ? 0 : 1);
