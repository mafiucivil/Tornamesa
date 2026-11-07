/* FEA engine: banded Cholesky, Mindlin plate MITC4, plane-stress Q4. Units N, mm, MPa. */
const FEA = (() => {
  const GP = [-1 / Math.sqrt(3), 1 / Math.sqrt(3)];
  const XI = [-1, 1, 1, -1], ETA = [-1, -1, 1, 1];

  function Band(n, bw) { this.n = n; this.bw = bw; this.W = bw + 1; this.a = new Float64Array(n * (bw + 1)); }
  Band.prototype.add = function (i, j, v) {
    if (j < i) { const t = i; i = j; j = t; }
    const d = j - i;
    if (d > this.bw) throw new Error("bandwidth " + d + ">" + this.bw);
    this.a[i * this.W + d] += v;
  };
  Band.prototype.diag = function (i) { return this.a[i * this.W]; };

  function cholSolve(B, f) {
    const n = B.n, w = B.bw, W = B.W, a = B.a;
    for (let i = 0; i < n; i++) {
      let s = a[i * W];
      for (let k = Math.max(0, i - w); k < i; k++) { const u = a[k * W + (i - k)]; s -= u * u; }
      if (!(s > 0)) throw new Error("Matriz no definida positiva en GDL " + i + " (modelo inestable)");
      const d = Math.sqrt(s); a[i * W] = d;
      const jmax = Math.min(n - 1, i + w);
      for (let j = i + 1; j <= jmax; j++) {
        let t = a[i * W + (j - i)];
        for (let k = Math.max(0, j - w); k < i; k++) t -= a[k * W + (i - k)] * a[k * W + (j - k)];
        a[i * W + (j - i)] = t / d;
      }
    }
    const y = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      let s = f[i];
      for (let k = Math.max(0, i - w); k < i; k++) s -= a[k * W + (i - k)] * y[k];
      y[i] = s / a[i * W];
    }
    const x = new Float64Array(n);
    for (let i = n - 1; i >= 0; i--) {
      let s = y[i];
      const jmax = Math.min(n - 1, i + w);
      for (let j = i + 1; j <= jmax; j++) s -= a[i * W + (j - i)] * x[j];
      x[i] = s / a[i * W];
    }
    return x;
  }

  function shape(xi, eta) {
    const N = [], dxi = [], deta = [];
    for (let i = 0; i < 4; i++) {
      N.push(0.25 * (1 + xi * XI[i]) * (1 + eta * ETA[i]));
      dxi.push(0.25 * XI[i] * (1 + eta * ETA[i]));
      deta.push(0.25 * ETA[i] * (1 + xi * XI[i]));
    }
    return { N, dxi, deta };
  }
  function jac(X, Y, s) {
    let xx = 0, xy = 0, yx = 0, yy = 0;
    for (let i = 0; i < 4; i++) { xx += s.dxi[i] * X[i]; xy += s.dxi[i] * Y[i]; yx += s.deta[i] * X[i]; yy += s.deta[i] * Y[i]; }
    const det = xx * yy - xy * yx;
    const inv = [[yy / det, -xy / det], [-yx / det, xx / det]];
    const dx = [], dy = [];
    for (let i = 0; i < 4; i++) { dx.push(inv[0][0] * s.dxi[i] + inv[0][1] * s.deta[i]); dy.push(inv[1][0] * s.dxi[i] + inv[1][1] * s.deta[i]); }
    return { det, inv, dx, dy, J: [[xx, xy], [yx, yy]] };
  }
  function addBtDB(K, B, D, f, nd) {
    const nr = B.length;
    const DB = [];
    for (let r = 0; r < nr; r++) { DB.push(new Float64Array(nd)); for (let c = 0; c < nd; c++) { let s = 0; for (let k = 0; k < nr; k++) s += D[r][k] * B[k][c]; DB[r][c] = s; } }
    for (let i = 0; i < nd; i++) for (let j = 0; j < nd; j++) { let s = 0; for (let r = 0; r < nr; r++) s += B[r][i] * DB[r][j]; K[i][j] += s * f; }
  }
  const zeros = (n) => Array.from({ length: n }, () => new Float64Array(n));

  /* ---------------- Mindlin plate (MITC4). DOF/node: w, bx, by ---------------- */
  function plateDb(t, E, nu) {
    const D = E * t ** 3 / (12 * (1 - nu * nu));
    return [[D, nu * D, 0], [nu * D, D, 0], [0, 0, D * (1 - nu) / 2]];
  }
  function plateBb(jj) {
    const B = [new Float64Array(12), new Float64Array(12), new Float64Array(12)];
    for (let i = 0; i < 4; i++) {
      B[0][3 * i + 1] = jj.dx[i];
      B[1][3 * i + 2] = jj.dy[i];
      B[2][3 * i + 1] = jj.dy[i]; B[2][3 * i + 2] = jj.dx[i];
    }
    return B;
  }
  function plateKe(X, Y, t, E, nu) {
    const Db = plateDb(t, E, nu);
    const ks = 5 / 6 * E / (2 * (1 + nu)) * t;
    const K = zeros(12);
    for (const xi of GP) for (const eta of GP) {
      const s = shape(xi, eta), jj = jac(X, Y, s);
      addBtDB(K, plateBb(jj), Db, jj.det, 12);
    }
    const row = (xi, eta, dir) => {
      const s = shape(xi, eta);
      const d = dir === 0 ? s.dxi : s.deta;
      let tx = 0, ty = 0;
      for (let i = 0; i < 4; i++) { tx += d[i] * X[i]; ty += d[i] * Y[i]; }
      const r = new Float64Array(12);
      for (let i = 0; i < 4; i++) { r[3 * i] = d[i]; r[3 * i + 1] = s.N[i] * tx; r[3 * i + 2] = s.N[i] * ty; }
      return r;
    };
    const rA = row(0, 1, 0), rC = row(0, -1, 0), rB = row(-1, 0, 1), rD = row(1, 0, 1);
    const Ds = [[ks, 0], [0, ks]];
    for (const xi of GP) for (const eta of GP) {
      const s = shape(xi, eta), jj = jac(X, Y, s);
      const gx = new Float64Array(12), ge = new Float64Array(12);
      for (let c = 0; c < 12; c++) {
        gx[c] = 0.5 * (1 + eta) * rA[c] + 0.5 * (1 - eta) * rC[c];
        ge[c] = 0.5 * (1 + xi) * rD[c] + 0.5 * (1 - xi) * rB[c];
      }
      const Bs = [new Float64Array(12), new Float64Array(12)];
      for (let c = 0; c < 12; c++) {
        Bs[0][c] = jj.inv[0][0] * gx[c] + jj.inv[0][1] * ge[c];
        Bs[1][c] = jj.inv[1][0] * gx[c] + jj.inv[1][1] * ge[c];
      }
      addBtDB(K, Bs, Ds, jj.det, 12);
    }
    return K;
  }

  function bandwidth(elems, ndof) {
    let bw = 0;
    for (const e of elems) { const mn = Math.min(...e), mx = Math.max(...e); bw = Math.max(bw, (mx - mn + 1) * ndof - 1); }
    return bw;
  }

  /* model: {nodes:[[x,y]], elems:[[n1..n4]], t,E,nu, q:Float64Array per elem (MPa, +z),
     wFix:[node], clamp:[node], betaN:[[node,nx,ny]]} */
  function plate(m) {
    const nn = m.nodes.length, n = 3 * nn;
    const bw = bandwidth(m.elems, 3);
    const K = new Band(n, bw), f = new Float64Array(n);
    let maxd = 0;
    for (let e = 0; e < m.elems.length; e++) {
      const en = m.elems[e];
      const X = en.map((k) => m.nodes[k][0]), Y = en.map((k) => m.nodes[k][1]);
      const ke = plateKe(X, Y, m.t, m.E, m.nu);
      const dofs = [];
      for (const k of en) dofs.push(3 * k, 3 * k + 1, 3 * k + 2);
      for (let i = 0; i < 12; i++) for (let j = i; j < 12; j++) {
        const gi = dofs[i], gj = dofs[j];
        if (gi === gj) K.add(gi, gj, ke[i][j]);
        else if (gi < gj) K.add(gi, gj, ke[i][j]);
        else K.add(gj, gi, ke[i][j]);
        if (i === j) maxd = Math.max(maxd, ke[i][i]);
      }
      const q = m.q[e];
      if (q) for (const xi of GP) for (const eta of GP) {
        const s = shape(xi, eta), jj = jac(X, Y, s);
        for (let i = 0; i < 4; i++) f[3 * en[i]] += s.N[i] * q * jj.det;
      }
    }
    // symmetric fill: ensure lower duplicates added only once (handled by i<=j loop with symmetric storage)
    const kp = maxd * 1e6;
    const used = new Uint8Array(nn);
    for (const en of m.elems) for (const k of en) used[k] = 1;
    for (let k = 0; k < nn; k++) if (!used[k]) { K.add(3 * k, 3 * k, 1); K.add(3 * k + 1, 3 * k + 1, 1); K.add(3 * k + 2, 3 * k + 2, 1); }
    for (const k of m.wFix) K.add(3 * k, 3 * k, kp);
    for (const k of (m.clamp || [])) { K.add(3 * k, 3 * k, kp); K.add(3 * k + 1, 3 * k + 1, kp); K.add(3 * k + 2, 3 * k + 2, kp); }
    for (const [k, nx, ny] of (m.betaN || [])) {
      K.add(3 * k + 1, 3 * k + 1, kp * nx * nx); K.add(3 * k + 2, 3 * k + 2, kp * ny * ny); K.add(3 * k + 1, 3 * k + 2, kp * nx * ny);
    }
    const u = cholSolve(K, f);
    const w = new Float64Array(nn);
    for (let k = 0; k < nn; k++) w[k] = u[3 * k];
    const reac = new Float64Array(nn);
    const fixed = new Set([...m.wFix, ...(m.clamp || [])]);
    for (const k of fixed) reac[k] = -kp * u[3 * k];
    const Db = plateDb(m.t, m.E, m.nu);
    const el = [];
    const pts = [[0, 0]].concat(GP.flatMap((a) => GP.map((b) => [a, b])));
    for (let e = 0; e < m.elems.length; e++) {
      const en = m.elems[e];
      const X = en.map((k) => m.nodes[k][0]), Y = en.map((k) => m.nodes[k][1]);
      const ue = []; for (const k of en) ue.push(u[3 * k], u[3 * k + 1], u[3 * k + 2]);
      let vmc = 0, vmx = 0, Mc = null;
      for (let p = 0; p < pts.length; p++) {
        const s = shape(pts[p][0], pts[p][1]), jj = jac(X, Y, s), B = plateBb(jj);
        const kap = [0, 0, 0];
        for (let r = 0; r < 3; r++) for (let c = 0; c < 12; c++) kap[r] += B[r][c] * ue[c];
        const M = [0, 0, 0];
        for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) M[r] += Db[r][c] * kap[c];
        const k6 = 6 / (m.t * m.t);
        const sx = M[0] * k6, sy = M[1] * k6, txy = M[2] * k6;
        const vm = Math.sqrt(sx * sx - sx * sy + sy * sy + 3 * txy * txy);
        if (p === 0) { vmc = vm; Mc = M; } else vmx = Math.max(vmx, vm);
      }
      el.push({ vm: vmc, vmGauss: vmx, M: Mc });
    }
    let F = 0; for (let k = 0; k < nn; k++) F += f[3 * k];
    let R = 0; for (const k of fixed) R += reac[k];
    return { w, reac, el, Fapplied: F, Rsum: R, ndof: n, bw };
  }

  /* ---------------- Plane stress Q4. DOF/node: ux, uy ---------------- */
  function psD(E, nu) { const c = E / (1 - nu * nu); return [[c, c * nu, 0], [c * nu, c, 0], [0, 0, c * (1 - nu) / 2]]; }
  function psB(jj) {
    const B = [new Float64Array(8), new Float64Array(8), new Float64Array(8)];
    for (let i = 0; i < 4; i++) { B[0][2 * i] = jj.dx[i]; B[1][2 * i + 1] = jj.dy[i]; B[2][2 * i] = jj.dy[i]; B[2][2 * i + 1] = jj.dx[i]; }
    return B;
  }
  /* m: {nodes, elems, t, E, nu, fix:[[node,dof]], loads:[[node,fx,fy]]} */
  function planeStress(m) {
    const nn = m.nodes.length, n = 2 * nn, bw = bandwidth(m.elems, 2);
    const K = new Band(n, bw), f = new Float64Array(n), D = psD(m.E, m.nu);
    let maxd = 0;
    for (const en of m.elems) {
      const X = en.map((k) => m.nodes[k][0]), Y = en.map((k) => m.nodes[k][1]);
      const ke = zeros(8);
      for (const xi of GP) for (const eta of GP) { const s = shape(xi, eta), jj = jac(X, Y, s); addBtDB(ke, psB(jj), D, jj.det * m.t, 8); }
      const dofs = []; for (const k of en) dofs.push(2 * k, 2 * k + 1);
      for (let i = 0; i < 8; i++) for (let j = i; j < 8; j++) K.add(dofs[i], dofs[j], ke[i][j]);
      for (let i = 0; i < 8; i++) maxd = Math.max(maxd, ke[i][i]);
    }
    const used = new Uint8Array(nn);
    for (const en of m.elems) for (const k of en) used[k] = 1;
    for (let k = 0; k < nn; k++) if (!used[k]) { K.add(2 * k, 2 * k, 1); K.add(2 * k + 1, 2 * k + 1, 1); }
    const kp = maxd * 1e6;
    for (const [k, d] of m.fix) K.add(2 * k + d, 2 * k + d, kp);
    for (const [k, fx, fy] of m.loads) { f[2 * k] += fx; f[2 * k + 1] += fy; }
    const u = cholSolve(K, f);
    const el = [];
    for (const en of m.elems) {
      const X = en.map((k) => m.nodes[k][0]), Y = en.map((k) => m.nodes[k][1]);
      const ue = []; for (const k of en) ue.push(u[2 * k], u[2 * k + 1]);
      const s = shape(0, 0), jj = jac(X, Y, s), B = psB(jj);
      const eps = [0, 0, 0];
      for (let r = 0; r < 3; r++) for (let c = 0; c < 8; c++) eps[r] += B[r][c] * ue[c];
      const sg = [0, 0, 0];
      for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) sg[r] += D[r][c] * eps[c];
      const vm = Math.sqrt(sg[0] ** 2 - sg[0] * sg[1] + sg[1] ** 2 + 3 * sg[2] ** 2);
      el.push({ sx: sg[0], sy: sg[1], txy: sg[2], vm });
    }
    const reac = [];
    for (const [k, d] of m.fix) reac.push([k, d, -kp * u[2 * k + d]]);
    return { u, el, reac, ndof: n, bw };
  }

  return { plate, planeStress, cholSolve, Band };
})();
if (typeof module !== "undefined") module.exports = FEA;
