"""Verificación independiente de la cubierta de madera W (rebaje) del núcleo TT300-C.
Decisión del mandante (08-11-2026): la mesa conserva el anillo superior R_reb…R (plancha superior actual en esa zona, con los pasadores), dentro de R_reb
una plancha rebajada continua bajada t_madera, una pared cilíndrica en R_reb y los tablones enrasados con el anillo; sin anillo de contención 10×50.

Recalcula desde los parámetros (P del JSON de tools/export_design.js; NO lee el código JS) y compara con lo que exporta el núcleo:
  1. geometría del rebaje (radios, alturas, cotas), almas y nervios recortados;
  2. masas (anillo, pared, plancha rebajada, almas, nervios, cubo, pivote, tablones por franjas con Simpson);
  3. tablones (disposición simétrica, cortes por la abertura de la tapa), fijación ISO 4762 (largo comercial, engrane, taladro ciego);
  4. flexión global axisimétrica con solución cerrada de Kirchhoff (no la integración numérica del núcleo): h_c, σ global, M_r en R_reb;
  5. verificaciones nuevas: aplastamiento y apoyo lateral de la madera, pared (flexión, corte), soldaduras J1 y J2, filetes AWS, geométricas, buje;
  6. validación del modelo escalonado desarrollado: solución cerrada axisimétrica de la piel superior (plancha rebajada + pared + anillo con apoyo lineal)
     con la pared como viga (lo que hace el modelo desarrollado) frente a la pared como cáscara cilíndrica (con rigidez circunferencial): acota el error
     de despreciar la rigidez circunferencial de la pared.
Ejecutar: python3 -I tests/indep_madera.py    (código de salida 1 si alguna comparación discrepa)"""
import json, math, pathlib, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
RHO, g0 = 7.85e-6, 9.80665
COMP = []


def export(over):
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "p.json"; f.write_text(json.dumps(over))
        r = subprocess.run(["node", str(ROOT / "tools" / "export_design.js"), str(f)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr); sys.exit(2)
    return json.loads(r.stdout)


def comp(name, mine, core, tol=1e-6):
    d = (mine - core) / core if core else (0.0 if abs(mine) < 1e-12 else 1.0)
    ok = abs(d) <= tol
    COMP.append(ok)
    print(f"{'OK ' if ok else 'XX '} {name:88s} indep {mine:14.5f}  núcleo {core:14.5f}  Δ {d * 100:+.4f} %")


def check(name, cond, txt=""):
    COMP.append(bool(cond)); print(f"{'OK ' if cond else 'XX '} {name} {txt}")


def ver(D, sub):
    for v in D["verificaciones"]:
        if v["nombre"].startswith(sub):
            return v
    raise KeyError(sub)


# ---------------------------------------------------------------- geometría y masas propias
def geo(P):
    tW, tT, tB = P["t_wood"], P["t_top"], P["t_bot"]
    tR = P["t_reb"] or tT; tP = P["t_pared"] or tT; tA = max(P["t_pr"], tT)
    Rr = P["R_reb"]; Rp = Rr + tP; Rq = Rp + P["w_pared"] + 5
    hw = P["h_disc"] - tT - tB
    return dict(tR=tR, tP=tP, tA=tA, Rr=Rr, Rp=Rp, Rq=Rq, hp=tW - tA, hc=tW + tR / 2 - tA / 2, drec=tW + tR - tT, hw=hw, hwr=P["h_disc"] - tB - tW - tR,
                Rw=Rr - P["c_mad"], Rab=(P["D_piv"] + 120) / 2 + P["c_mad"], hole=P["D_piv"] + 80)


def simpson(f, a, b, n=600):
    h = (b - a) / n
    return h / 3 * (f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n)))


def planks(P, G):
    Rw, Rab, b, j = G["Rw"], G["Rab"], P["b_tab"], P["j_tab"]

    def strips(odd):
        y00 = -b / 2 if odd else j / 2; out = []
        for k in range(-50, 51):
            y0 = y00 + k * (b + j); a0, a1 = max(y0, -Rw), min(y0 + b, Rw)
            if a1 - a0 > 1e-9:
                out.append((a0, a1))
        return out
    L1, L0 = strips(True), strips(False)
    w = lambda L: min(L[0][1] - L[0][0], L[-1][1] - L[-1][0])
    L = L1 if w(L1) >= w(L0) else L0
    ch = lambda R, y: 2 * math.sqrt(max(0.0, R * R - y * y))
    out = []
    for (y0, y1) in L:
        ymin = 0.0 if y0 <= 0 <= y1 else min(abs(y0), abs(y1)); ymax = max(abs(y0), abs(y1))
        corte = "abertura" if ymax <= Rab else ("muesca" if ymin < Rab else None)
        area = simpson(lambda y: ch(Rw, y) - ch(Rab, y), y0, y1)
        # tornillos: filas a ≥ 7d de los extremos (borde más corto), ≤ s_max entre filas; 2 por fila si el ancho ≥ 2·máx(4d, 40) + 4d
        d = P["d_tmad"]; eE, eB = 7 * d, max(4 * d, 40)
        xe = math.sqrt(max(0.0, Rw * Rw - ymax * ymax)); xi = math.sqrt(max(0.0, Rab * Rab - ymin * ymin)) if corte else 0.0
        segs = [(-xe, -xi), (xi, xe)] if corte else [(-xe, xe)]
        nrow = sum(1 if (u1 - u0) - 2 * eE <= 0 else max(2, math.ceil(((u1 - u0) - 2 * eE) / P["s_tmad"]) + 1) for u0, u1 in segs)
        out.append(dict(y0=y0, y1=y1, corte=corte, area=area, n_pz=2 if corte == "abertura" else 1, n_t=nrow * (2 if (y1 - y0) >= 2 * eB + 4 * d else 1)))
    return out


def fijacion(P, G):
    d = P["d_tmad"]; aw = {6: (18, 1.6), 8: (24, 2), 10: (30, 2.5), 12: (37, 3), 14: (44, 3), 16: (50, 3)}.get(d, (3 * d, 0.25 * d))
    hcaj = d + aw[1] + 3; trest = P["t_wood"] - hcaj; pt = G["tR"] - 3; lr = pt - 4
    Ls = [L for L in (16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100) if d - 1e-9 <= L - trest <= lr - 2 + 1e-9]
    L = max(Ls) if Ls else None
    return dict(L=L, le=(L - trest) if L else float("nan"), hcaj=hcaj, pt=pt, lr=lr)


def masas(P, G, tabl):
    Rt = P["D_top"] / 2; ap = P["N_pin"] * math.pi / 4 * P["d_pin"] ** 2
    an = RHO * (math.pi * (Rt ** 2 - G["Rr"] ** 2) - ap) * G["tA"]
    pa = RHO * math.pi * (G["Rp"] ** 2 - G["Rr"] ** 2) * G["hp"]
    pr = RHO * math.pi * (G["Rq"] ** 2 - (G["hole"] / 2) ** 2) * G["tR"]
    rings = sorted(float(x) for x in P["rings"].replace(";", ",").split(",") if x.strip())
    webs = RHO * sum(2 * math.pi * r * (G["hwr"] if r <= G["Rp"] + 0.5 else P["h_disc"] - G["tA"] - P["t_bot"]) * P["t_web"] for r in rings)
    nin = sum(1 for r in rings if P["D_hub"] / 2 < r < min(P["R_rib"], G["Rp"]))
    ribs = RHO * P["N_rib"] * max(0.0, min(P["R_rib"], G["Rp"]) - P["D_hub"] / 2 - nin * P["t_web"]) * G["hwr"] * P["t_rib"]
    piv = RHO * math.pi / 4 * P["D_piv"] ** 2 * (P["t_base"] + P["h_disc"] - P["t_wood"] - G["tR"] + 3)   # interfaz acero–acero (δ = 0)
    wood = P["rho_wood"] * 1e-9 * P["t_wood"] * sum(t["area"] for t in tabl)
    return dict(anillo=an, pared=pa, reb=pr, top=an + pa + pr, webs=webs, ribs=ribs, pivot=piv, wood=wood)


# ---------------------------------------------------------------- placas axisimétricas de Kirchhoff (solución cerrada por tramos)
class Seg:
    """tramo r ∈ [a, b]: 'plate' (w = C1 + C2 r² + C3 ln r + C4 r² ln r + q r⁴/64D), 'beam' (w = c0 + c1 x + c2 x² + c3 x³, x = r − a)
    o 'shell' (viga sobre fundación elástica 4β⁴: base e^{±βx}·{cos, sin} βx; x = r − a; pared cilíndrica con rigidez circunferencial)"""
    def __init__(s, a, b, D, kind="plate", q=0.0, nu=0.3, beta=0.0, center=False):
        s.a, s.b, s.D, s.kind, s.q, s.nu, s.beta, s.center = a, b, D, kind, q, nu, beta, center

    def basis(s, r, n):
        """derivada n (0…3) de las 4 funciones base y de la solución particular en r"""
        if s.kind == "plate":
            L = math.log(r)
            F = [[1, r * r, L, r * r * L], [0, 2 * r, 1 / r, 2 * r * L + r], [0, 2, -1 / r ** 2, 2 * L + 3], [0, 0, 2 / r ** 3, 2 / r]][n]
            Pp = [s.q * r ** 4 / (64 * s.D), s.q * r ** 3 / (16 * s.D), 3 * s.q * r * r / (16 * s.D), 6 * s.q * r / (16 * s.D)][n]
            return F, Pp
        x = r - s.a
        if s.kind == "beam":
            return [[1, x, x * x, x ** 3], [0, 1, 2 * x, 3 * x * x], [0, 0, 2, 6 * x], [0, 0, 0, 6]][n], 0.0
        out = []
        for lam in (s.beta * (1 + 1j), s.beta * (-1 + 1j)):
            v = lam ** n * np.exp(lam * x)
            out += [v.real, v.imag]
        return out, 0.0

    def M(s, r):   # M_r (placa) o M_x (viga/cáscara), por unidad de largo
        F1, p1 = s.basis(r, 1); F2, p2 = s.basis(r, 2)
        if s.kind == "plate":
            return [-s.D * (F2[i] + s.nu * F1[i] / r) for i in range(4)], -s.D * (p2 + s.nu * p1 / r)
        return [-s.D * F2[i] for i in range(4)], -s.D * p2

    def Q(s, r):
        F1, p1 = s.basis(r, 1); F2, p2 = s.basis(r, 2); F3, p3 = s.basis(r, 3)
        if s.kind == "plate":
            return [-s.D * (F3[i] + F2[i] / r - F1[i] / r ** 2) for i in range(4)], -s.D * (p3 + p2 / r - p1 / r ** 2)
        return [-s.D * F3[i] for i in range(4)], -s.D * p3


def solve(segs, conds):
    """conds: lista de (tipo, datos). Ecuaciones lineales en los 4·n coeficientes."""
    N = 4 * len(segs); A = np.zeros((N, N)); b = np.zeros(N); row = 0

    def put(si, coef, part, sign=1.0):
        A[row, 4 * si:4 * si + 4] += sign * np.array(coef, float); b[row] -= sign * part
    for c in conds:
        t = c[0]
        if t == "w0":   # w = 0 en el extremo e del tramo si
            si, r = c[1], c[2]; F, p = segs[si].basis(r, 0); put(si, F, p); row += 1
        elif t == "dw0":
            si, r = c[1], c[2]; F, p = segs[si].basis(r, 1); put(si, F, p); row += 1
        elif t in ("cont_dw", "cont_w"):   # continuidad entre si (en su extremo b) y sj (en su extremo a)
            si, sj = c[1], c[2]; n = 1 if t == "cont_dw" else 0
            F, p = segs[si].basis(segs[si].b, n); put(si, F, p)
            F, p = segs[sj].basis(segs[sj].a, n); put(sj, F, p, -1.0); row += 1
        elif t == "cont_M":
            si, sj = c[1], c[2]
            F, p = segs[si].M(segs[si].b); put(si, F, p)
            F, p = segs[sj].M(segs[sj].a); put(sj, F, p, -1.0); row += 1
        elif t == "cont_Q":
            si, sj = c[1], c[2]
            F, p = segs[si].Q(segs[si].b); put(si, F, p)
            F, p = segs[sj].Q(segs[sj].a); put(sj, F, p, -1.0); row += 1
        elif t == "M0":
            si, r = c[1], c[2]; F, p = segs[si].M(r); put(si, F, p); row += 1
        elif t == "Q0":
            si, r = c[1], c[2]; F, p = segs[si].Q(r); put(si, F, p); row += 1
        elif t == "coef0":   # coeficiente k del tramo si = 0 (centro regular)
            si, k = c[1], c[2]; A[row, 4 * si + k] = 1.0; row += 1
    assert row == N, (row, N)
    return np.linalg.solve(A, b)


def evalM(segs, C, si, r):
    F, p = segs[si].M(r); return float(np.dot(F, C[4 * si:4 * si + 4]) + p)


def evalW(segs, C, si, r):
    F, p = segs[si].basis(r, 0); return float(np.dot(F, C[4 * si:4 * si + 4]) + p)


def piel_axisimetrica(P, G, q, wall="beam"):
    """Piel superior escalonada axisimétrica (sin nervios): plancha rebajada r0…R_reb empotrada en el cubo con apoyos en las almas (w = 0),
    carga q en r ≤ R_carga; pared de largo h_c (viga, o cáscara cilíndrica con 4β⁴ = 12(1 − ν²)/(R² t²)); anillo R_reb…R (t_anillo) con apoyo lineal
    en R_pin (pasadores) y borde libre. Devuelve M en la base de la pared, M_r máximo en el vano exterior de la plancha rebajada y flecha máxima."""
    E, nu = P["E"], P["nu"]; Dp = lambda t: E * t ** 3 / (12 * (1 - nu * nu))
    r0 = P["D_hub"] / 2; Rr = G["Rr"]; RL = P["D_load"] / 2; Rt = P["D_top"] / 2
    rings = [r for r in sorted(float(x) for x in P["rings"].replace(";", ",").split(",") if x.strip()) if r0 < r < Rr - 0.5]
    cuts = sorted(set([r0] + rings + [min(RL, Rr), Rr]))
    segs, conds = [], []
    for i in range(len(cuts) - 1):
        a, b = cuts[i], cuts[i + 1]
        segs.append(Seg(a, b, Dp(G["tR"]), "plate", q if b <= RL + 1e-9 else 0.0, nu))
    nP = len(segs)
    beta = (3 * (1 - nu * nu) / ((Rr + G["tP"] / 2) ** 2 * G["tP"] ** 2)) ** 0.25
    segs.append(Seg(0.0, G["hc"], Dp(G["tP"]), "shell" if wall == "shell" else "beam", 0.0, nu, beta))
    segs.append(Seg(Rr, P["R_pin"], Dp(G["tA"]), "plate", 0.0, nu)); segs.append(Seg(P["R_pin"], Rt, Dp(G["tA"]), "plate", 0.0, nu))
    conds += [("w0", 0, r0), ("dw0", 0, r0)]
    for i in range(nP - 1):
        b = segs[i].b
        if any(abs(b - r) < 1e-9 for r in rings):
            conds += [("w0", i, b), ("w0", i + 1, b), ("cont_dw", i, i + 1), ("cont_M", i, i + 1)]
        else:   # límite de la carga: continuidad completa
            conds += [("cont_w", i, i + 1), ("cont_dw", i, i + 1), ("cont_M", i, i + 1), ("cont_Q", i, i + 1)]
    iw, ia, ib = nP, nP + 1, nP + 2
    conds += [("w0", nP - 1, Rr), ("w0", iw, 0.0), ("cont_dw", nP - 1, iw), ("cont_M", nP - 1, iw)]
    conds += [("w0", iw, G["hc"]), ("w0", ia, Rr), ("cont_dw", iw, ia), ("cont_M", iw, ia)]
    conds += [("w0", ia, P["R_pin"]), ("w0", ib, P["R_pin"]), ("cont_dw", ia, ib), ("cont_M", ia, ib), ("M0", ib, Rt), ("Q0", ib, Rt)]
    C = solve(segs, conds)
    Mbase = abs(evalM(segs, C, iw, 0.0)); Mtop = abs(evalM(segs, C, iw, G["hc"]))
    lo = rings[-1] if rings else r0
    span = [abs(evalM(segs, C, next(i for i in range(nP) if segs[i].a - 1e-9 <= r <= segs[i].b + 1e-9), r)) for r in np.linspace(lo + 1, Rr - 1, 400)]
    wmax = max(abs(evalW(segs, C, next(i for i in range(nP) if segs[i].a - 1e-9 <= r <= segs[i].b + 1e-9), r)) for r in np.linspace(r0 + 1, Rr - 1, 600))
    return dict(Mbase=Mbase, Mtop=Mtop, Mspan=max(span), wmax=wmax, beta=beta)


def global_axi(P, W, Wd, ND, Ri):
    """Flexión global del cajón (placa sándwich axisimétrica, borde libre) por solución cerrada: centro regular, tramos [0, R_i], [R_i, R_carga], [R_carga, R]."""
    Rd, RL = P["D_top"] / 2, min(P["D_load"] / 2, P["D_top"] / 2)
    qt = P["phi_d"] * W * 1e3 / (math.pi * RL * RL); qd = Wd * 1e3 / (math.pi * Rd * Rd); qb = ND * 1e3 / (math.pi * (Rd * Rd - Ri * Ri))
    cuts = sorted([1e-3, Ri, RL, Rd]); D = 1.0
    segs = []
    for i in range(3):
        a, b = cuts[i], cuts[i + 1]; m = (a + b) / 2
        segs.append(Seg(a, b, D, "plate", -((qb if m >= Ri else 0) - (qt if m <= RL else 0) - qd), 0.3))   # w hacia abajo positivo con la carga hacia abajo
    conds = [("coef0", 0, 2), ("coef0", 0, 3), ("coef0", 0, 0)]
    for i in range(2):
        conds += [("cont_w", i, i + 1), ("cont_dw", i, i + 1), ("cont_M", i, i + 1), ("cont_Q", i, i + 1)]
    conds += [("M0", 2, Rd)]
    C = solve(segs, conds)
    best = 0.0
    for r in np.linspace(1.0, Rd - 1, 3000):
        si = next(i for i in range(3) if segs[i].a - 1e-9 <= r <= segs[i].b + 1e-9)
        F1, p1 = segs[si].basis(r, 1); F2, p2 = segs[si].basis(r, 2)
        wp = float(np.dot(F1, C[4 * si:4 * si + 4]) + p1); wpp = float(np.dot(F2, C[4 * si:4 * si + 4]) + p2)
        best = max(best, abs(-(wpp + 0.3 * wp / r)), abs(-(wp / r + 0.3 * wpp)))
    Mr = lambda r: abs(evalM(segs, C, next(i for i in range(3) if segs[i].a - 1e-9 <= r <= segs[i].b + 1e-9), r))
    return best, Mr


# ================================================================ casos
CASOS = [{"opt_wood": 1}, {"opt_wood": 1, "t_wood": 50}, {"opt_wood": 1, "opt_uhmw": 1}]
with ThreadPoolExecutor(max_workers=3) as ex:
    DS = list(ex.map(export, CASOS))

for over, D in zip(CASOS, DS):
    P = D["P"]; MJ = D["madera"]; M = D["derivados"]["masas"]; G = geo(P)
    tag = ",".join(f"{k}={v}" for k, v in over.items() if k != "opt_wood") or "defecto"
    print(f"\n## Cubierta W · {tag}  (t_madera {P['t_wood']}, R_reb {P['R_reb']}, t_reb {G['tR']}, t_pared {G['tP']}, t_anillo {G['tA']})")
    # 1. geometría
    for k, mine in (("R_pared_ext", G["Rp"]), ("R_reb_ext", G["Rq"]), ("h_pared", G["hp"]), ("h_c", G["hc"]), ("d_rebaje", G["drec"]), ("hw_reb", G["hwr"]),
                    ("R_tablones", G["Rw"]), ("R_abertura", G["Rab"]), ("t_anillo", G["tA"])):
        comp("geometría · " + k + " (mm)", mine, MJ[k])
    comp("geometría · cota de la cara superior de la plancha rebajada (mm)", P["h_disc"] - P["t_wood"], MJ["z"]["reb_sup"])
    check("geometría · almas dentro de R_pared con h = hw_reb", all(abs(a["h"] - G["hwr"]) < 1e-9 for a in MJ["almas"] if a["r"] <= G["Rp"]))
    # 2-3. tablones, fijación y masas
    T = planks(P, G)
    comp("tablones · cantidad", len(T), MJ["tablones"]["n"])
    comp("tablones · piezas", sum(t["n_pz"] for t in T), MJ["tablones"]["n_piezas"])
    comp("tablones · área neta (mm²)", sum(t["area"] for t in T), MJ["tablones"]["area_neta"], 1e-5)   # Simpson junto al borde del círculo (raíz): error ≈ 1e-6
    check("tablones · cortes por la abertura y muescas", [t["corte"] for t in T] == [t["corte"] for t in MJ["tablones"]["lista"]])
    comp("fijación · tornillos (cantidad)", sum(t["n_t"] for t in T), MJ["fijacion"]["n_total"])
    F = fijacion(P, G)
    comp("fijación · largo comercial ISO 4762 (mm)", F["L"], MJ["fijacion"]["L"]); comp("fijación · engrane (mm)", F["le"], MJ["fijacion"]["engrane"])
    mm = masas(P, G, T)
    comp("masa · anillo (kg)", mm["anillo"], MJ["masas"]["anillo"]); comp("masa · pared (kg)", mm["pared"], MJ["masas"]["pared"])
    comp("masa · plancha rebajada (kg)", mm["reb"], MJ["masas"]["plancha_rebajada"]); comp("masa · m.top (kg)", mm["top"], M["top"])
    comp("masa · almas (kg)", mm["webs"], M["webs"]); comp("masa · nervios (kg)", mm["ribs"], M["ribs"]); comp("masa · tablones (kg)", mm["wood"], M["wood"], 1e-5)
    comp("masa · m.ring (sin anillo de contención)", 0.0, M["ring"])
    if not (P["opt_ss"] or P["opt_uhmw"] or P["opt_bz"]):
        comp("masa · pivote hasta la plancha rebajada (kg)", mm["pivot"], M["pivot"])
    # 4. flexión global (solución cerrada)
    W, ND, Wd, Ri = D["derivados"]["W"], D["derivados"]["ND"], D["apoyo"]["Wd"], D["apoyo"]["Ri"]
    Mmax, Mr = global_axi(P, W, Wd, ND, Ri)
    hc = P["h_disc"] - P["t_wood"] - G["tR"] / 2 - P["t_bot"] / 2
    sup, inf, loc_s, loc_i = ver(D, "Plancha superior: global + local"), ver(D, "Plancha inferior: global + local"), ver(D, "Plancha superior: σvm local"), ver(D, "Plancha inferior: σvm local")
    comp("global · σ plancha rebajada = M/(t_reb·h_c) (MPa)", Mmax / (G["tR"] * hc), sup["dem"] - loc_s["dem"], 2e-3)
    comp("global · σ plancha inferior = M/(t_bot·h_c) (MPa)", Mmax / (P["t_bot"] * hc), inf["dem"] - loc_i["dem"], 2e-3)
    comp("global · M_r en R_reb (N·mm/mm)", Mr(P["R_reb"]), MJ["fea"]["Mr_glob_reb"], 5e-3)
    # 5. verificaciones nuevas
    RL = P["D_load"] / 2; Aw = math.pi * (min(RL, G["Rw"]) ** 2 - G["Rab"] ** 2)
    comp("madera · aplastamiento q (MPa)", P["phi_d"] * W * 1e3 / (P["f_apoyo"] * Aw) * (1 + 4 * P["e"] / RL), ver(D, "Madera: aplastamiento")["dem"])
    H = P["k_hmad"] * P["phi_d"] * W * 1e3; Lc = 2 * min(RL, G["Rw"])
    comp("madera · apoyo lateral contra la pared (MPa)", H / (Lc * P["t_wood"]), ver(D, "Madera: apoyo lateral")["dem"])
    Nr = Mr(P["R_reb"]) / hc; Mlat = 3 * (H / Lc) * G["hc"] / 16; sF = MJ["fea"]["s_pared"]
    sP = P["kFEA"] * sF + 6 * (Nr * G["hc"] + Mlat) / G["tP"] ** 2
    comp("pared · flexión σ (MPa)", sP, ver(D, "Pared del rebaje: flexión")["dem"], 5e-3)
    V = Nr + 11 / 16 * H / Lc
    comp("pared · corte τ (MPa)", 1.5 * V / G["tP"], ver(D, "Pared del rebaje: corte")["dem"], 5e-3)
    a = 0.707 * P["w_pared"]; Mb = sP * G["tP"] ** 2 / 6; E1 = math.ceil(G["tP"] / 2) - 3
    comp("soldadura J2 pared–plancha rebajada (MPa)", math.hypot(Mb / (G["tP"] * a), V / (2 * a)), ver(D, "Soldadura pared–plancha rebajada")["dem"], 5e-3)
    comp("soldadura J1 anillo–pared PJP + filete (MPa)", math.hypot(Mb / (G["tP"] * min(a, E1)), V / (a + E1)), ver(D, "Soldadura anillo–pared")["dem"], 5e-3)
    wmin = lambda T: 3 if T <= 6 else 5 if T <= 12 else 6 if T <= 20 else 8
    comp("filete mínimo AWS D1.1 T5.8 (mm)", max(min(wmin(max(G["tP"], G["tR"])), G["tP"], G["tR"]), min(wmin(max(G["tP"], G["tA"])), G["tP"], G["tA"])), ver(D, "Rebaje: filete mínimo")["dem"])
    comp("buje bajo la plancha rebajada: capacidad (mm)", D["apoyo"]["interfaz"]["delta"] + P["h_disc"] - P["t_wood"] - G["tR"], ver(D, "Buje sobre el collar")["cap"])
    comp("altura total sin cambio (mm)", P["t_base"] + D["apoyo"]["interfaz"]["delta"] + P["h_disc"], ver(D, "Altura total sobre el piso")["dem"])
    st = {v["nombre"][:40]: v["estado"] for v in D["verificaciones"] if v["grp"] in ("Cubierta", "Mesa", "Mesa (FEA)", "Pivote")}
    if tag == "t_wood=50":
        check("t_madera = 50: el buje no cabe y la plancha inferior pasa de FU 0,90 (motivo del ajuste a 45)",
              ver(D, "Buje sobre el collar")["estado"] == "fail" and ver(D, "Plancha inferior: global + local")["estado"] == "warn")
    else:
        check("todas las verificaciones de la cubierta, la mesa y el pivote cumplen (sin avisos)", all(s in ("ok", "info", "pend") for s in st.values()),
              str({k: s for k, s in st.items() if s not in ("ok", "info", "pend")}))
    # térmica: gradiente con h = h_mesa − d_rebaje y holgura de los tablones a 80 °C
    alt = next(a_ for a_ in D["termica"]["alternativas"] if a_["madera"])
    b80 = next(b_ for b_ in alt["byT"] if b_["T"] == 80)
    hol = next(f for f in b80["filas"] if f["nombre"].startswith("Madera: holgura perimetral frente a la dilatación transversal a T"))
    comp("térmica · holgura de los tablones a 80 °C (mm)", (30e-6 - 12.4e-6) * 60 * 2 * G["Rw"], hol["dem"], 1e-6)   # α_acero medio 20–80 °C = 12,4×10⁻⁶ (EN 1993-1-2 §3.4.1.1)
    if tag == "defecto":
        # 6. validación del modelo escalonado: pared como viga (modelo desarrollado) frente a pared como cáscara cilíndrica
        RLq = min(P["D_load"] / 2, P["D_top"] / 2); q = P["phi_d"] * W * 1e3 / (math.pi * RLq * RLq) * (1 + 4 * P["e"] / RLq)
        bm, sh = piel_axisimetrica(P, G, q, "beam"), piel_axisimetrica(P, G, q, "shell")
        print(f"   validación axisimétrica (sin nervios): pared viga  M_base {bm['Mbase']:.3f}  M_vano {bm['Mspan']:.3f}  w {bm['wmax']:.6f} mm")
        print(f"                                         pared cáscara M_base {sh['Mbase']:.3f}  M_vano {sh['Mspan']:.3f}  w {sh['wmax']:.6f} mm  (β = {sh['beta']:.5f} 1/mm, β·h = {sh['beta'] * G['hc']:.3f};")
        print("                                         con la pared fija radialmente en sus dos extremos la rigidez circunferencial solo actúa sobre la flecha interior: efecto ∝ (βh)⁴)")
        dv, db_ = sh["Mspan"] / bm["Mspan"] - 1, sh["Mbase"] / bm["Mbase"] - 1
        check("despreciar la rigidez circunferencial de la pared cambia el M del vano de la plancha rebajada < 2 % (el modelo desarrollado es conservador o equivalente)", abs(dv) < 0.02, f"({dv * 100:+.2f} %)")
        check("… y el momento en la base de la pared < 5 %", abs(db_) < 0.05, f"({db_ * 100:+.2f} %)")
        sFEA = MJ["fea"]["s_pared"]; sAx = 6 * bm["Mbase"] / G["tP"] ** 2
        check("σ_pared del FEA escalonado (con nervios) del mismo orden que el axisimétrico sin nervios (razón 0,5–2)", 0.5 < sFEA / sAx < 2.0, f"FEA {sFEA:.1f} / axisimétrico {sAx:.1f} MPa")

nok = sum(1 for c in COMP if not c)
print(f"\nindep_madera: {len(COMP) - nok}/{len(COMP)} comparaciones coinciden")
sys.exit(1 if nok else 0)
