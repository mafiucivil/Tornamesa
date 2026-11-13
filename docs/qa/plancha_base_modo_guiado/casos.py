"""Modo guiado (drive_mode = 1): FEA de la base completa con las cargas del cilindro, de la guía del patín y del riel-leva (JSON por línea).
Reutiliza la placa de Mindlin, los soportes rígidos y el contacto unilateral de docs/qa/plancha_base_soporte_E/basefea.py.

Modelo (docs/qa/plancha_base_modo_guiado.md):
- Soporte rígido = ménsula del ojal trasero (dos mejillas soldadas a la base), con el origen en el ojal E = (x_g; y_ojal); el cilindro 2 por rotación de 180°.
- Bancada y su prolongación bajo los pórticos: elementos de la placa con el espesor equivalente de la sección compuesta plancha + bancada (con la ranura T),
  misma rigidez a flexión por unidad de ancho; en la malla de 20 mm los bordes de la bancada caen en líneas de la malla.
- Cargas por cilindro (cilindro 1: lado +x, empuje +y; momentos de fuerzas horizontales a la altura z sobre la cara superior de la plancha: Mx = −z·Fy, My = z·Fx):
  * empuje a calado: ménsula −F·ŷ a h (Mx = +F·h); patín sobre la bancada: reacciones laterales de la guía −R_f, −R_r a z_T (distribución triangular por mitad
    del patín, como en el núcleo), roce de la guía (F − F_pas)·ŷ a z_T y el resto del vuelco y del cabeceo del patín (lengüeta T) repartido en su largo;
    la mesa recibe F_pas·ŷ + H·x̂ a h en el pasador (con dos cilindros los pares de la mesa se anulan; con uno, la mesa cargada es una huella bilateral).
  * retorno, atasco a nivel de toma (chaflán sobre el pasador B): ménsula +F_ret·ŷ a h; el riel recibe +N_toma·x̂ a z_F (reparto a los dos pórticos por la
    regla de la palanca); el patín, el par −(z_F − h)·N_toma de la uña; la mesa toma −F_ret·ŷ − N_toma·x̂ en el pasador B: cruza la base como el empuje.
  * retorno, atasco en la rampa con la uña trabada en el alojamiento: ménsula +F_ret·ŷ a h; riel (+N_x; −F_ret) a z_F; patín el resto: se equilibra en la franja.
- Peso propio: plancha y bancadas (ρ·g·t por elemento), mesa vacía uniforme en R_i…R_o, ménsula + medio cilindro en cada maestro, patín + medio cilindro
  sobre la bancada, riel y pórticos en las prolongaciones, ménsulas del otro sentido (sin carga) en su huella.
"""
import json, math, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plancha_base_soporte_E"))
from basefea import Base, G_

RHO = 7.85e-6


def bed_section(P, w, tb=None):
    """sección compuesta plancha t_base + bancada t_bed de ancho w con la ranura (w_slot × h_slot) y la cabeza T (w_tee × h_tee) descontadas:
    flexión a lo largo de la bancada (I por unidad de ancho, fibra extrema c) y torsión de Saint-Venant de la sección real (función de Prandtl por
    diferencias finitas, malla de 1 mm: ∇²φ = −2, φ = 0 en el contorno y en la ranura abierta; J = 2∫φ dA, τ_máx = máx|∇φ| para G·θ' = 1)"""
    tb = P["t_base"] if tb is None else tb; tB = P["t_bed"]; H = tb + tB
    parts = [(w * tb, tb / 2, w * tb ** 3 / 12), (w * tB, tb + tB / 2, w * tB ** 3 / 12),
             (-P["w_slot"] * P["h_slot"], H - P["h_slot"] / 2, -P["w_slot"] * P["h_slot"] ** 3 / 12),
             (-P["w_tee"] * P["h_tee"], H - P["h_slot"] - P["h_tee"] / 2, -P["w_tee"] * P["h_tee"] ** 3 / 12)]
    A = sum(p[0] for p in parts); y = sum(p[0] * p[1] for p in parts) / A
    I = sum(p[2] + p[0] * (p[1] - y) ** 2 for p in parts)
    c = max(y, H - y)
    # Prandtl
    d = 1.0; nx, nz = int(round(w / d)), int(round(H / d))
    xc = (np.arange(nx) + 0.5) * d - w / 2; zc = (np.arange(nz) + 0.5) * d
    Xc, Zc = np.meshgrid(xc, zc, indexing="ij")
    void = ((np.abs(Xc) < P["w_slot"] / 2) & (Zc > H - P["h_slot"])) | ((np.abs(Xc) < P["w_tee"] / 2) & (Zc > H - P["h_slot"] - P["h_tee"]) & (Zc <= H - P["h_slot"]))
    ins = ~void; idx = -np.ones((nx, nz), int); idx[ins] = np.arange(ins.sum())
    rows, cols, vals = [], [], []
    for (i, j) in zip(*np.where(ins)):
        k = idx[i, j]; rows.append(k); cols.append(k); vals.append(-4.0)
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, bq = i + di, j + dj
            if 0 <= a < nx and 0 <= bq < nz and ins[a, bq]: rows.append(k); cols.append(idx[a, bq]); vals.append(1.0)
    import scipy.sparse as sp, scipy.sparse.linalg as spl
    L = sp.csr_matrix((vals, (rows, cols)), shape=(ins.sum(), ins.sum()))
    phi_v = spl.spsolve(L.tocsc(), -2.0 * d * d * np.ones(ins.sum()))
    phi = np.zeros((nx + 2, nz + 2)); phi[1:-1, 1:-1][ins] = phi_v
    J = 2 * phi.sum() * d * d
    gx = (phi[2:, 1:-1] - phi[:-2, 1:-1]) / (2 * d); gz = (phi[1:-1, 2:] - phi[1:-1, :-2]) / (2 * d)
    tmax = float(np.sqrt(gx ** 2 + gz ** 2)[ins].max())
    tx = tb + tB - P["h_slot"] - P["h_tee"]          # banda continua bajo la cabeza T (flexión transversal a la bancada)
    return dict(I_w=I / w, c=c, t_eq=(12 * I / w) ** (1 / 3), A_w=A / w, J=J, J_w=J / w, tau_hat=tmax, t_x=tx, w=w)


def assemble_ortho(b, Dm):
    """rigidez de la placa de Mindlin con matriz constitutiva de flexión por elemento Dm (ne × 3 × 3) sobre [κ_x, κ_y, γ_xy] (γ_xy = β_x,y + β_y,x)"""
    ah = b.hm / 2; gq = (-1 / math.sqrt(3), 1 / math.sqrt(3)); nu = b.nu; E_ = b.E_
    def Bm(xi, et):
        sgx, sgy = (-1, 1, 1, -1), (-1, -1, 1, 1); Bb = np.zeros((3, 12)); Bs = np.zeros((2, 12))
        for k in range(4):
            N = 0.25 * (1 + xi * sgx[k]) * (1 + et * sgy[k]); dx = 0.25 * sgx[k] * (1 + et * sgy[k]) / ah; dy = 0.25 * sgy[k] * (1 + xi * sgx[k]) / ah
            Bb[0, 3 * k + 1] = dx; Bb[1, 3 * k + 2] = dy; Bb[2, 3 * k + 1] = dy; Bb[2, 3 * k + 2] = dx; Bs[0, 3 * k] = dx; Bs[0, 3 * k + 1] = -N; Bs[1, 3 * k] = dy; Bs[1, 3 * k + 2] = -N
        return Bb, Bs
    Kab = np.zeros((3, 3, 12, 12))
    for x in gq:
        for y in gq:
            Bb, _ = Bm(x, y)
            for a in range(3):
                for c in range(3): Kab[a, c] += np.outer(Bb[a], Bb[c]) * ah * ah
    B0b, B0s = Bm(0, 0); Ks1 = B0s.T @ B0s * 4 * ah * ah
    b.B0b = B0b; b.C = np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])
    dof = np.stack([3 * b.els, 3 * b.els + 1, 3 * b.els + 2], axis=2).reshape(len(b.els), 12); b.dof = dof
    Gs = 5 / 6 * E_ / (2 * (1 + nu)) * b.te
    vals = np.einsum("eac,acij->eij", Dm, Kab) + Gs[:, None, None] * Ks1[None]
    rows = np.repeat(dof, 12, axis=1).ravel(); cols = np.tile(dof, (1, 12)).ravel()
    import scipy.sparse as sp
    b.K0 = sp.csr_matrix((vals.reshape(len(b.els), 144).ravel(), (rows, cols)), shape=(3 * b.nn, 3 * b.nn)).tocsr()
    b.Dm = Dm


class Guiado:
    def __init__(self, ex, hm, t=None, cerrar=False):
        self.ex = ex; P = ex["P"]; self.P = P; self.hm = hm
        tb = P["t_base"] if t is None else t
        self.rects = [(*ex["bancada"]["x"], *ex["bancada"]["y"])] + [(*q["x"], *q["y"]) for q in ex["prolongacion"]]   # cilindro 1; el 2 por rotación
        if cerrar:   # variante: prolongación de la bancada hasta la cara trasera de la ménsula (cierra la franja de plancha sola entre la ménsula y la bancada)
            E = ex["E"]; yb = E[1] + ex["walls"][0][2]
            for q in ex["prolongacion"]:
                x0, x1 = q["x"]; y0, y1 = q["y"]
                self.rects.append((x0, x1, yb, y0) if y0 < 0 else (x0, x1, y1, -yb))
        self.secB = bed_section(P, P["w_bed"], tb)
        def cov(x, y):   # fracción del elemento (centro x, y) cubierta por la bancada o su prolongación (cilindro 1 o 2); los rectángulos no se superponen
            f = 0.0
            for s in (1, -1):
                for (x0, x1, y0, y1) in self.rects:
                    a0, a1, b0, b1 = (x0, x1, y0, y1) if s == 1 else (-x1, -x0, -y1, -y0)
                    ox = max(0.0, min(x + hm / 2, a1) - max(x - hm / 2, a0)); oy = max(0.0, min(y + hm / 2, b1) - max(y - hm / 2, b0))
                    f += ox * oy / hm ** 2
            return min(1.0, f)
        self.cov_fn = cov
        sB = self.secB; E_, nu = P["E"], P["nu"]; Gm = E_ / (2 * (1 + nu))
        # bancada ortótropa: a lo largo (y) la sección compuesta; transversal (x) la banda continua bajo la cabeza T; torsión con el J real (Prandtl):
        # GJ = 4·b·D_xy para una franja de ancho b (placa de Kirchhoff con bordes libres) → D_xy = G·J_w/4
        Dy = E_ * sB["I_w"] / (1 - nu ** 2); Dx = E_ * sB["t_x"] ** 3 / (12 * (1 - nu ** 2)); Dxy = Gm * sB["J_w"] / 4
        DmB = np.array([[Dx, nu * math.sqrt(Dx * Dy), 0], [nu * math.sqrt(Dx * Dy), Dy, 0], [0, 0, Dxy]])
        Dp = E_ * tb ** 3 / (12 * (1 - nu ** 2)); DmP = Dp * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])
        self.b = Base(ex, hm=hm, t=tb, tfield=lambda x, y, t0: t0 + cov(x, y) * (sB["A_w"] - t0))   # peso y corte transversal con el área real
        self.cov = np.array([cov(x, y) for x, y in self.b.ec])
        c3 = self.cov[:, None, None]; Dm = c3 * DmB[None] + (1 - c3) * DmP[None]   # la sección compuesta ya incluye la plancha bajo la bancada
        assemble_ortho(self.b, Dm); self.tb = tb; self.DmB = DmB; self.DmP = DmP

    # ---- utilidades de carga
    def nodes_in(self, x0, x1, y0, y1, cil):
        b = self.b; s = 1 if cil == 1 else -1
        X, Y = s * b.X, s * b.Y; e = 1e-6
        return np.where((X >= x0 - e) & (X <= x1 + e) & (Y >= y0 - e) & (Y <= y1 + e))[0]

    def add_M(self, f, ids, Mx, My, w=None, cil=1):
        """momento (Mx, My) del cilindro 1 repartido en los nudos ids con pesos w; cilindro 2: (−Mx, −My)"""
        if len(ids) == 0: raise ValueError("sin nudos para la carga")
        s = 1 if cil == 1 else -1
        w = np.ones(len(ids)) if w is None else np.asarray(w, float)
        w = w / w.sum()
        f[3 * ids + 1] += -s * My * w; f[3 * ids + 2] += s * Mx * w

    def add_W(self, f, ids, W):
        f[3 * ids] -= W / len(ids)


def run(ex, hm, out_tag, cases, t=None, cerrar=False, anclajes=None):
    P = ex["P"]; Fa = P["Fy"] / P["Nd"]; h = ex["h"]; zT = ex["zT"]; zF = ex["zF"]
    G = Guiado(ex, hm, t=t, cerrar=cerrar); b = G.b; secB = G.secB
    anc = [b.node(x, y) for (x, y) in (anclajes or [])]
    print(json.dumps(dict(seccion_bancada={k: round(float(v), 3) for k, v in secB.items()})), flush=True)
    xb0, xb1 = ex["bancada"]["x"]; Lsp = ex["Lsp"]; ysup = ex["y_soportes_riel"]
    r = np.hypot(b.X, b.Y); E = np.array(ex["E"])
    # peso propio
    Wt = ex["Wd"] + ex["mdogs"] * G_
    fz = b.weights(Wt, ex["Ri"], ex["Ro"])
    fW = np.zeros(3 * b.nn); fW[0::3] = fz
    for cil in (1, 2):
        # ménsulas del otro sentido (sin carga): huella en y → −y del lado del cilindro
        wl = ex["walls"]; Ey = -E[1]
        ids = np.concatenate([G.nodes_in(E[0] + x0, E[0] + x1, Ey - y1, Ey - y0, cil) for (x0, x1, y0, y1) in wl])
        G.add_W(fW, ids, ex["msup"] * G_)
        for q in ex["patas"]:
            G.add_W(fW, G.nodes_in(*q["x"], *q["y"], cil), ex["mcam"] * G_ / len(ex["patas"]))
    msup = (ex["msup"] + ex["m"]["cyl"] / P["n_cyl"] / 2) * G_

    def far_mask(X, Y):
        return (np.hypot(X - E[0], Y - E[1]) > 450) & (np.hypot(X + E[0], Y + E[1]) > 450)

    def shoe_loads(f, st, cil, Fb, Fp):
        """patín sobre la bancada en el estado st (empuje): reacciones laterales triangulares por mitad, roce de guía y resto del vuelco y del cabeceo"""
        y0, y1 = st["y_ini"], st["y_fin"]; yc = (y0 + y1) / 2; Ls = y1 - y0
        ids = G.nodes_in(xb0, xb1, y0, y1, cil); Y = (b.Y if cil == 1 else -b.Y)[ids]
        Rf, Rr, Hx = st["rf"] * Fp, st["rr"] * Fp, -st["h"] * Fp      # fuerzas de la guía sobre el patín (x) y del pasador sobre la uña (x)
        wf = np.where(Y >= yc, (Y - yc) / (Ls / 2), 0.0); wr = np.where(Y < yc, (yc - Y) / (Ls / 2), 0.0)
        G.add_M(f, ids[wf > 0], 0.0, zT * (-Rf), wf[wf > 0], cil)       # la bancada recibe −R_f a z_T
        G.add_M(f, ids[wr > 0], 0.0, zT * (-Rr), wr[wr > 0], cil)
        fr = Fb - Fp                                                       # roce de la guía: el patín pierde (F − F_pas), la bancada lo recibe en +y a z_T
        G.add_M(f, ids, -zT * fr - (h - zT) * fr, (h - zT) * Hx, None, cil)   # roce a z_T + resto del cabeceo (lengüeta) y del vuelco hasta h
        G.add_W(f, ids, (ex["mshoe"] + ex["m"]["cyl"] / P["n_cyl"] / 2 + ex["mdogs"] / P["n_cyl"]) * G_)

    def portal_loads(f, cil, y_fol, Mx, My):
        """momento del riel sobre los dos pórticos: regla de la palanca con el seguidor en y_fol (riel biapoyado en ±Lsp/2)"""
        for ys in ysup:
            frac = max(0.0, min(1.0, 0.5 + math.copysign(1, ys) * y_fol / Lsp))
            ids = np.concatenate([G.nodes_in(*q["x"], *q["y"], cil) for q in ex["patas"] if (q["y"][0] + q["y"][1]) * ys > 0])
            G.add_M(f, ids, Mx * frac, My * frac, None, cil)

    for (case, st_i, mesa, ncil) in cases:
        st = ex["shoe"][st_i]; t0 = time.time()
        f = fW.copy(); moms = []
        y_fol = st["y_rp"] + P["l_p"] - P["d_pin"] / 2 - P["dog_b"] / 2
        if case == "empuje":
            F = ex["Fstall"]; Fp = P["eta_c"] * F
            for cil in (1, 2):
                sg = 1 if cil == 1 else -1                                     # cilindro 2: rotación de 180° (M₂ = −M₁)
                if cil <= ncil: moms.append((sg * h * F, 0.0)); shoe_loads(f, st, cil, F, Fp)
                else: moms.append((0.0, 0.0)); G.add_W(f, G.nodes_in(xb0, xb1, st["y_ini"], st["y_fin"], cil), (ex["mshoe"] + ex["m"]["cyl"] / P["n_cyl"] / 2 + ex["mdogs"] / P["n_cyl"]) * G_)
            M = h * F
        elif case == "retorno-toma":
            Fr, NT = ex["Fret"], ex["NT"]
            for cil in (1, 2):
                if cil <= ncil:
                    moms.append((-(1 if cil == 1 else -1) * h * Fr, 0.0)); portal_loads(f, cil, y_fol, 0.0, zF * NT)
                    ids = G.nodes_in(xb0, xb1, st["y_ini"], st["y_fin"], cil); G.add_M(f, ids, 0.0, -(zF - h) * NT, None, cil)
                else: moms.append((0.0, 0.0))
            M = h * math.hypot(Fr, NT)
        elif case == "retorno-rampa":
            Fr, Nx = ex["Fret"], ex["NRx"]
            for cil in (1, 2):
                if cil <= ncil:
                    moms.append((-(1 if cil == 1 else -1) * h * Fr, 0.0)); portal_loads(f, cil, y_fol, zF * Fr, zF * Nx)
                    ids = G.nodes_in(xb0, xb1, st["y_ini"], st["y_fin"], cil); G.add_M(f, ids, -(zF - h) * Fr, -zF * Nx, None, cil)
                else: moms.append((0.0, 0.0))
            M = h * Fr
        hold = (r <= ex["Ro"]) if mesa == "cargada" else np.zeros(b.nn, bool)
        for k in anc: hold[k] = True
        b.solve(moms, f[0::3], hold=hold, masters_w=[-msup, -msup], fext=np.where(np.arange(3 * b.nn) % 3 == 0, 0.0, f))
        # tensiones a partir de la curvatura en el centro de cada elemento: plancha (cobertura < 0,5) con su propio D; bancada (≥ 0,5) con la sección compuesta
        kap = b.u[b.dof] @ b.B0b.T; Em = P["E"] / (1 - P["nu"] ** 2); nu = P["nu"]; tb_ = G.tb
        sp_ = np.stack([Em * tb_ / 2 * (kap[:, 0] + nu * kap[:, 1]), Em * tb_ / 2 * (kap[:, 1] + nu * kap[:, 0]), Em * tb_ / 2 * (1 - nu) / 2 * kap[:, 2]], axis=1)
        vm = np.sqrt(sp_[:, 0] ** 2 - sp_[:, 0] * sp_[:, 1] + sp_[:, 1] ** 2 + 3 * sp_[:, 2] ** 2)
        Gm = P["E"] / (2 * (1 + nu)); sy = P["E"] * kap[:, 1] * secB["c"]; sx = Em * kap[:, 0] * secB["t_x"] / 2; tau = Gm * kap[:, 2] / 2 * secB["tau_hat"]
        vmb = np.sqrt(sx ** 2 - sx * sy + sy ** 2 + 3 * tau ** 2)
        inS = b.inS[b.els].all(axis=1); mp = (G.cov < 0.5) & ~inS; bd = (G.cov >= 0.5) & ~inS
        i = int(np.argmax(np.where(mp, vm, -1))); far = far_mask(b.ec[:, 0], b.ec[:, 1]) & mp; j = int(np.argmax(np.where(far, vm, -1)))
        k = int(np.argmax(np.where(bd, vmb, -1)))
        il = int(np.argmax(b.w)); rin = r <= ex["Ro"]
        cs = [(s1 * b.Bh, s2 * b.Bh) for s1 in (1, -1) for s2 in (1, -1)]
        lc = {f"({int(x)};{int(y)})": float(b.w[b.node(x, y)]) for x, y in cs}
        o = dict(caso=case, mesa=mesa, n_cil=ncil, th_deg=math.degrees(st["th"]), M_kNm=M / 1e6, t_base=G.tb,
                 s=float(vm[i]), fu=float(vm[i] / Fa), at=[float(b.ec[i, 0]), float(b.ec[i, 1])],
                 s_far=float(vm[j]), fu_far=float(vm[j] / Fa), at_far=[float(b.ec[j, 0]), float(b.ec[j, 1])],
                 s_bancada=float(vmb[k]), fu_bancada=float(vmb[k] / Fa), at_bancada=[float(b.ec[k, 0]), float(b.ec[k, 1])],
                 lift=float(b.w.max()), at_lift=[float(b.X[il]), float(b.Y[il])], lift_mesa=float(b.w[rin].max()), lift_esquinas=lc,
                 anclajes_kN=[float(-b.react[k] / 1e3) for k in anc], cerrar=cerrar,
                 ncont=int(b.act.sum()), nn=b.nn, conv=bool(b.conv), it=b.it, t=round(time.time() - t0, 1), tag=out_tag)
        print(json.dumps(o), flush=True)
    return G


if __name__ == "__main__":
    ex = json.load(open(sys.argv[1])); hm = float(sys.argv[2]); mode = sys.argv[3] if len(sys.argv) > 3 else "todos"
    opt = sys.argv[4].split(",") if len(sys.argv) > 4 else []
    t = next((float(o[2:]) for o in opt if o.startswith("t=")), None); cerrar = "cerrar" in opt
    anclajes = [(1200, 1200), (-1200, -1200)] if "anclar" in opt else None   # un perno en cada esquina libre (las que suben en el empuje)
    C = []
    if mode in ("todos", "empuje"):
        for st in (0, 1, 2):
            for mesa, n in (("vacía", 2), ("cargada", 2), ("cargada", 1), ("vacía", 1)): C.append(("empuje", st, mesa, n))
    if mode in ("todos", "retorno"):
        for st in (0, 2):
            for mesa, n in (("vacía", 2), ("cargada", 2), ("cargada", 1)): C.append(("retorno-toma", st, mesa, n))
            C.append(("retorno-rampa", st, "vacía", 2))
    if mode == "rapido":
        C = [("empuje", 1, "vacía", 2), ("empuje", 1, "cargada", 2), ("retorno-toma", 0, "vacía", 2), ("retorno-rampa", 0, "vacía", 2)]
    run(ex, hm, mode + ("+" + "+".join(opt) if opt else ""), C, t=t, cerrar=cerrar, anclajes=anclajes)
