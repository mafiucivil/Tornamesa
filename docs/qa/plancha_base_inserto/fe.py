"""FEA de Mindlin (copiada de tests/indep_plancha_base_E.py, vectorizada) para dimensionar el inserto de esquina.
tfun por polígono (matplotlib.path). Unidades N, mm, MPa."""
import json, math, sys
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
from matplotlib.path import Path

Es, nu = 2e5, 0.3


def unit_K(hm):
    xi_n = np.array([-1, 1, 1, -1]); et_n = np.array([-1, -1, 1, 1]); a = hm / 2; Kb = np.zeros((12, 12)); Ks = np.zeros((12, 12))
    Db1 = Es / (12 * (1 - nu ** 2)) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]]); Ds1 = 5 / 6 * Es / (2 * (1 + nu)) * np.eye(2)
    for xi in (-1 / math.sqrt(3), 1 / math.sqrt(3)):
        for et in (-1 / math.sqrt(3), 1 / math.sqrt(3)):
            dx = 0.25 * xi_n * (1 + et_n * et) / a; dy = 0.25 * et_n * (1 + xi_n * xi) / a; B = np.zeros((3, 12))
            B[0, 1::3] = dx; B[1, 2::3] = dy; B[2, 1::3] = dy; B[2, 2::3] = dx; Kb += B.T @ Db1 @ B * a * a
    N = np.full(4, 0.25); dx = 0.25 * xi_n / a; dy = 0.25 * et_n / a; B = np.zeros((2, 12))
    B[0, 0::3] = dx; B[0, 1::3] = N; B[1, 0::3] = dy; B[1, 2::3] = N; Ks += B.T @ Ds1 @ B * 4 * a * a
    return Kb, Ks, dx, dy


def fea(Bs, hm, tvec, supports, W_tab, R_tab, table="body", Ri=140.0, kslab=100.0, ktab=100.0):
    """tvec(X, Y) -> array de espesores. table: 'body' (mesa cargada, cuerpo rígido con contacto unilateral) o 'weight' (mesa vacía: W_tab uniforme en Ri..R_tab)."""
    n = int(round(Bs / hm)); xs = np.linspace(-Bs / 2, Bs / 2, n + 1); X, Y = [a.ravel() for a in np.meshgrid(xs, xs, indexing="ij")]
    nn = X.size; ndof = 3 * nn; I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij"); I = I.ravel(); J = J.ravel()
    els = np.stack([I * (n + 1) + J, (I + 1) * (n + 1) + J, (I + 1) * (n + 1) + J + 1, I * (n + 1) + J + 1], 1)
    te = tvec(X[els].mean(1), Y[els].mean(1)); Kb, Ks, dxc, dyc = unit_K(hm)
    dof = (3 * els[:, :, None] + np.arange(3)).reshape(-1, 12)
    vals = (te[:, None, None] ** 3 * Kb + te[:, None, None] * Ks).reshape(-1)
    K = sp.csr_matrix((vals, (np.repeat(dof, 12, 1).ravel(), np.tile(dof, (1, 12)).ravel())), shape=(ndof, ndof))
    Ar = np.full(nn, hm * hm); ed = (np.abs(X) > Bs / 2 - 1e-6) | (np.abs(Y) > Bs / 2 - 1e-6); co = (np.abs(X) > Bs / 2 - 1e-6) & (np.abs(Y) > Bs / 2 - 1e-6)
    Ar[ed] /= 2; Ar[co] /= 2
    tn = tvec(X, Y); fv = np.zeros(ndof); fv[0::3] -= 7.7e-5 * tn * Ar
    if table == "weight":
        ring = (X ** 2 + Y ** 2 <= R_tab ** 2) & (X ** 2 + Y ** 2 >= Ri ** 2); fv[0::3][ring] -= W_tab * Ar[ring] / Ar[ring].sum()
    slave = -np.ones(nn, int)
    for k, (m, _, _, _) in enumerate(supports): slave[m(X, Y)] = k
    fr_n = np.where(slave < 0)[0]; base = 3 * fr_n.size; it0 = base + 3 * len(supports); nred = it0 + (3 if table == "body" else 0)
    r_, c_, v_ = [], [], []
    r_ = np.concatenate([3 * fr_n, 3 * fr_n + 1, 3 * fr_n + 2]).tolist(); c_ = np.concatenate([3 * np.arange(fr_n.size), 3 * np.arange(fr_n.size) + 1, 3 * np.arange(fr_n.size) + 2]).tolist(); v_ = [1.0] * len(r_)
    for nd in np.where(slave >= 0)[0]:
        k = slave[nd]; xc, yc = supports[k][1]; m0 = base + 3 * k
        r_ += [3 * nd] * 3 + [3 * nd + 1, 3 * nd + 2]; c_ += [m0, m0 + 1, m0 + 2, m0 + 1, m0 + 2]; v_ += [1.0, -(X[nd] - xc), -(Y[nd] - yc), 1.0, 1.0]
    T = sp.csr_matrix((v_, (r_, c_)), shape=(ndof, nred)); fr = T.T @ fv
    for k, (_, _, (Mx, My), W) in enumerate(supports):
        m0 = base + 3 * k; fr[m0 + 1] += My; fr[m0 + 2] -= Mx; fr[m0] -= W
    Kr = (T.T @ K @ T).tocsr(); wmap = T[0::3, :].tocsr(); ks = kslab * Ar; kt = ktab * Ar
    if table == "body":
        fr[it0] -= W_tab
        rows = np.where(X ** 2 + Y ** 2 <= R_tab ** 2)[0]; m_ = rows.size
        Tt = sp.csr_matrix((np.concatenate([np.ones(m_), -X[rows], -Y[rows]]), (np.tile(np.arange(m_), 3), np.repeat([it0, it0 + 1, it0 + 2], m_))), shape=(m_, nred))
        Dm = (wmap[rows] - Tt).tocsr()
    else:
        rows = np.zeros(0, int); m_ = 0; Dm = sp.csr_matrix((0, nred))
    act_s = np.ones(nn, bool); act_t = np.ones(m_, bool); conv = False
    for it in range(300):
        Kt = Kr + wmap.T @ sp.diags(ks * act_s) @ wmap
        if m_: Kt = Kt + Dm.T @ sp.diags(kt[rows] * act_t) @ Dm
        ur = SOLVE(Kt, fr, 3 if table == "body" else 0); u = T @ ur; w = u[0::3]; g = Dm @ ur if m_ else np.zeros(0)
        ns = w <= 0; nt = g >= 0; cs = np.where(ns != act_s)[0]; ct = np.where(nt != act_t)[0]
        if cs.size + ct.size == 0: conv = True; break
        if it > 40:
            sel = cs[np.argsort(-np.abs(w[cs]))][: max(1, cs.size // 5)]; act_s[sel] = ns[sel]
            if ct.size: sel = ct[np.argsort(-np.abs(g[ct]))][: max(1, ct.size // 5)]; act_t[sel] = nt[sel]
        else:
            act_s, act_t = ns, nt
    bx = u[1::3][els]; by = u[2::3][els]
    kap = np.stack([bx @ dxc, by @ dyc, bx @ dyc + by @ dxc], 1)
    Db1 = Es / (12 * (1 - nu ** 2)) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])
    m = (kap @ Db1.T) * te[:, None] ** 3; s = 6 * m / te[:, None] ** 2
    vm = np.sqrt(s[:, 0] ** 2 - s[:, 0] * s[:, 1] + s[:, 1] ** 2 + 3 * s[:, 2] ** 2)
    S = np.column_stack([X[els].mean(1), Y[els].mean(1), vm, m, te])
    return X, Y, w, S, conv


def SOLVE(Kt, fr, nt=3):
    """Complemento de Schur de los nt gdl densos del final (mesa rígida): la placa se factoriza sola (COLAMD)."""
    Kt = Kt.tocsr(); n = Kt.shape[0]
    if nt == 0: return spl.splu(Kt.tocsc(), permc_spec="COLAMD").solve(fr)
    A = Kt[:n - nt, :n - nt].tocsc(); b = Kt[:n - nt, n - nt:].toarray(); c = Kt[n - nt:, n - nt:].toarray()
    lu = spl.splu(A, permc_spec="COLAMD"); Y = lu.solve(b); xp0 = lu.solve(fr[:n - nt])
    xt = np.linalg.solve(c - b.T @ Y, fr[n - nt:] - b.T @ xp0)
    return np.concatenate([xp0 - Y @ xt, xt])


def caso(F_N, u, E, rects, h, Bs, tvec, W_tab, R_tab, ncyl=2, hm=40.0, sense=-1, table="body"):
    def mask(sg):
        def f(x, y):
            ok = np.zeros(x.shape, bool)
            for x0, x1, y0, y1 in rects:
                ok |= (x0 - 1 <= sg * x - E[0]) & (sg * x - E[0] <= x1 + 1) & (y0 - 1 <= sg * y - E[1]) & (sg * y - E[1] <= y1 + 1)
            return ok
        return f
    def dist(x, y):
        d = np.full(x.shape, 1e9)
        for sg in (1, -1):
            Xr = sg * x - E[0]; Yr = sg * y - E[1]
            for x0, x1, y0, y1 in rects:
                d = np.minimum(d, np.hypot(np.maximum.reduce([x0 - Xr, np.zeros_like(Xr), Xr - x1]), np.maximum.reduce([y0 - Yr, np.zeros_like(Yr), Yr - y1])))
        return d
    Fb = (sense * F_N * u[0], sense * F_N * u[1]); M1 = (-h * Fb[1], h * Fb[0])
    sups = [(mask(1), E, M1, 470.0), (mask(-1), (-E[0], -E[1]), (-M1[0], -M1[1]) if ncyl == 2 else (0.0, 0.0), 470.0)]
    X, Y, w, S, conv = fea(Bs, hm, tvec, sups, W_tab, R_tab, table=table)
    d = dist(S[:, 0], S[:, 1])
    return dict(M=math.hypot(*M1) / 1e6, S=S, d=d, w=w.max(), conv=conv)


def tvec_poly(polys, t_ins, t_base, slope=2.5, Bh=1280.0):
    """Espesor t_ins dentro de cada polígono, con transición lineal 1:slope en la cara superior a lo largo de los bordes interiores
    (los que no están sobre el borde de la base): t = t_base + Δ·mín(1, d/(slope·Δ))."""
    paths = [Path(np.array(p)) for p in polys]; D = t_ins - t_base
    segs = []
    for p in polys:
        for a, b in zip(p, p[1:] + p[:1]):
            on_edge = (abs(a[0] - b[0]) < 1e-6 and abs(abs(a[0]) - Bh) < 1e-6) or (abs(a[1] - b[1]) < 1e-6 and abs(abs(a[1]) - Bh) < 1e-6)
            if not on_edge and math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-9: segs.append((np.array(a, float), np.array(b, float)))
    def dseg(P_):
        d = np.full(P_.shape[0], 1e18)
        for a, b in segs:
            ab = b - a; tt = np.clip(((P_ - a) @ ab) / (ab @ ab), 0, 1); d = np.minimum(d, np.hypot(*(P_ - (a + tt[:, None] * ab)).T))
        return d
    def f(x, y):
        pts = np.column_stack([x, y]); t = np.full(x.shape, float(t_base))
        inside = np.zeros(x.shape, bool)
        for pa in paths: inside |= pa.contains_points(pts, radius=1e-6)
        if slope > 0 and D > 0: t[inside] = t_base + D * np.minimum(1.0, dseg(pts[inside]) / (slope * D))
        else: t[inside] = t_ins
        return t
    return f


def summary(r, t_base, far=100.0):
    S, d = r["S"], r["d"]; m = d > far; tb = S[:, 6] < t_base + 0.5
    out = dict(M=r["M"], pico=S[:, 2].max(), lejos=S[m, 2].max(), lejos_base=S[m & tb, 2].max() if (m & tb).any() else 0, lejos_ins=S[m & ~tb, 2].max() if (m & ~tb).any() else 0, w=r["w"], conv=r["conv"])
    j = int(np.argmax(np.where(m, S[:, 2], -1))); out["donde"] = (round(S[j, 0]), round(S[j, 1]), S[j, 6])
    jb = int(np.argmax(np.where(m & tb, S[:, 2], -1))); out["donde_base"] = (round(S[jb, 0]), round(S[jb, 1]))
    return out
