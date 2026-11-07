"""Revisión independiente de los CÁLCULOS NUEVOS del núcleo TT300-C:
  1. Bomba y retorno rápido (tiempo por vuelta, velocidades, potencia, caudal para un tiempo objetivo)
  2. Cubierta de madera dura (masa, aplastamiento, espesor mínimo, altura total, enrase)
  3. Capacidad de giro (W máx. que gira con μ, r y FS dados)
  4. Capacidad según el número de cilindros (giro y pivote) y revisión del modelo de reacción del pivote
  5. μ implícito y coherencia de los datos de equipos comerciales

Regla de independencia: no lee packages/*.js. Los resultados del núcleo salen solo de
`node tools/export_design.js [params.json]` y de tests/golden/*.json. Todo lo demás se deriva aquí
(equilibrio de la mesa y del patín de indep_accionamiento.py, Navier, hidráulica elemental, ASME BTH-1 Cat. B).

Ejecutar:  python3 -I tests/indep_nuevas.py
Imprime tablas y termina con «RESULTADO: ...». Sale con 0 si no hay hallazgos críticos ni importantes; con 1 si los hay.

Convenciones: N, mm, MPa, kN (fuerzas de cilindro), tf = 9,80665 kN. Giro antihorario, cilindro en x = +x_g, empuje +y.
  Pasador en θ: a = R cosθ, y_p = R sinθ; cara plana normal a y, fricción en la cara H = s·μ_s·F (s = signo(y_p − r)).
  Mesa: T/n = a·F − (y_p − r)·H.  Patín: R_f = [F·(x_g − a) + H·(y_c − y_r)]/L_g, R_r = H − R_f.
  F_cil = [F + μ_g(|R_f| + |R_r|)]/η.  Todo es proporcional a T/n: F_cil = k·T/n con k = máx_θ(...).
"""
import json, math, os, pathlib, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLD = ROOT / "tests" / "golden"
g0, RHO = 9.80665, 7.85e-6
TOL = 1e-3


# ======================================================================================
# Utilidades
# ======================================================================================
def export(over=None):
    fd, name = tempfile.mkstemp(suffix=".json")
    try:
        args = ["node", str(ROOT / "tools" / "export_design.js")]
        if over:
            with os.fdopen(fd, "w") as f:
                json.dump(over, f)
            args.append(name)
        else:
            os.close(fd)
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    finally:
        os.unlink(name)
    return json.loads(r.stdout) if r.returncode == 0 else None


def s3(x):
    if x is None:
        return "—"
    if isinstance(x, str):
        return x
    if x == 0 or not math.isfinite(x):
        return f"{x:g}"
    return f"{x:.{max(0, 2 - int(math.floor(math.log10(abs(x)))))}f}" if abs(x) >= 1e-3 else f"{x:.3g}"


def table(title, head, rows):
    print(f"\n### {title}")
    w = [max([len(str(h))] + [len(str(r[i])) for r in rows]) for i, h in enumerate(head)]
    print("| " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(head)) + " |")
    print("|" + "|".join("-" * (x + 2) for x in w) + "|")
    for r in rows:
        print("| " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) + " |")


COMP, FIND = [], []


def comp(prueba, name, mine, core, tol=TOL):
    if core is None:
        COMP.append((prueba, name, s3(mine), "—", "—", "el núcleo omite")); return
    d = (mine - core) / core * 100 if core else (0.0 if abs(mine) < 1e-12 else 100.0)
    COMP.append((prueba, name, s3(mine), s3(core), f"{d:+.3f}", "coincide" if abs(d) <= tol * 100 else "discrepa"))


def finding(i, sev, txt, core, corr):
    FIND.append((i, sev, txt, core, corr))


# ======================================================================================
# 0. Datos
# ======================================================================================
D0 = export()
if D0 is None:
    print("No se pudo ejecutar node tools/export_design.js"); sys.exit(2)
P = D0["P"]
Pg = json.loads((GOLD / "params_defaults.json").read_text())
dif = sorted(k for k in set(P) | set(Pg) if P.get(k) != Pg.get(k))


def ver(D, sub, grp=None):
    for v in D["verificaciones"]:
        if sub in v["nombre"] and (grp is None or v["grp"] == grp):
            return v
    return None


def ver_exact(D, nombre):
    for v in D["verificaciones"]:
        if v["nombre"] == nombre:
            return v
    return None


def estado_core(D, sub, grp=None):
    v = ver(D, sub, grp)
    return None if v is None else v["estado"]


# ======================================================================================
# Modelo propio (todo en función del diccionario de parámetros PP)
# ======================================================================================
def masa_mesa(PP):
    rings = sorted(float(x) for x in PP["rings"].replace(";", ",").split(",") if x.strip())
    Rt = PP["D_top"] / 2; hw = PP["h_disc"] - PP["t_top"] - PP["t_bot"]
    rpr = max(PP["D_hub"] / 2, PP["R_pin"] - (Rt - PP["R_pin"])); db = PP["D_piv"] + 30
    aring = math.pi * (Rt ** 2 - rpr ** 2) - PP["N_pin"] * math.pi * PP["d_pin"] ** 2 / 4
    m = RHO * ((math.pi * rpr ** 2 - math.pi / 4 * (PP["D_piv"] + 80) ** 2) * PP["t_top"] + aring * max(PP["t_pr"], PP["t_top"]))
    m += RHO * ((math.pi * rpr ** 2 - math.pi / 4 * db ** 2) * PP["t_bot"] + aring * max(PP["t_pr"], PP["t_bot"]))
    m += RHO * sum(2 * math.pi * r * hw * PP["t_web"] for r in rings)
    nin = sum(1 for r in rings if PP["D_hub"] / 2 < r < PP["R_rib"])
    m += RHO * PP["N_rib"] * (PP["R_rib"] - PP["D_hub"] / 2 - nin * PP["t_web"]) * hw * PP["t_rib"]
    m += RHO * math.pi / 4 * (PP["D_hub"] ** 2 - db ** 2) * hw
    m += RHO * PP["N_pin"] * math.pi / 4 * PP["d_pin"] ** 2 * PP["h_disc"]
    m_piv = RHO * math.pi / 4 * PP["D_piv"] ** 2 * (PP["t_base"] + PP["h_disc"] - PP["t_top"] + 3)
    return m + 0.5 * m_piv


def m_wood(PP):
    """Masa de la cubierta [kg] = ρ(kg/m³)·1e-9·π/4·(D_top² − (D_piv+80)²)·t."""
    return PP["rho_wood"] * 1e-9 * math.pi / 4 * (PP["D_top"] ** 2 - (PP["D_piv"] + 80) ** 2) * PP["t_wood"]


def Wd_kN(PP):
    m = masa_mesa(PP) + (m_wood(PP) if PP.get("opt_wood") == 1 else 0.0)
    return m * g0 / 1e3


def kappa(PP):
    Ro, Ri = PP["D_top"] / 2, PP["D_piv"] / 2 + 15
    return 4 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4)


def casos(PP):
    Ro, Ri = PP["D_top"] / 2, PP["D_piv"] / 2 + 15
    ru = 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2)
    return {"nom": (PP["mu_nom"], ru), "dis": (PP["mu_d"], PP["r_ef"]), "borde": (PP["mu_d"], Ro),
            "cont": (PP["mu_cont"], PP["r_ef"]), "seco": (PP["mu_dry"], ru)}


def Nkn(PP, W_tf=None):
    return (PP["W_tf"] if W_tf is None else W_tf) * g0 + Wd_kN(PP)


def cfric(PP, mu, r):
    """Par de fricción por kN de N [mm]: T = N·c;  c = μ·r + μ_buje·μ·e·κ·D_piv/2."""
    return mu * r + PP["mu_bush"] * mu * PP["e"] * kappa(PP) * PP["D_piv"] / 2


def Fst_kN(PP):
    return math.pi / 4 * PP["D_bore"] ** 2 * PP["p_relief"] / 10 / 1e3


def A_bore(PP):
    return math.pi / 4 * PP["D_bore"] ** 2


def A_ann(PP):
    return A_bore(PP) - math.pi / 4 * PP["d_rod"] ** 2


GEO_KEYS = ("R_pin", "N_pin", "d_pin", "x_g", "l_p", "f_ext", "d_pp", "mu_g", "mu_s", "eta_c")


@lru_cache(maxsize=None)
def _tabla(key):
    R, Np, dpin, xg, lp, fext, dpp, mug, mus, eta = key
    Np = int(Np); rp = dpin / 2; ph = math.pi / Np
    front, rear = lp + 20 + fext, 1.25 * dpp
    Ls = front + rear; Lg = 2 / 3 * Ls
    yr = (front - rear) / 2 - Lg / 2; yc = lp - rp

    def est(th, sg=None):
        a, yp = R * math.cos(th), R * math.sin(th)
        if sg is None:
            sg = 1 if yp > rp else -1
        hh = sg * mus
        F = 1.0 / (a - hh * (yp - rp)); H = hh * F
        Rf = (F * (xg - a) + H * (yc - yr)) / Lg; Rr = H - Rf
        Fh = (F + mug * (abs(Rf) + abs(Rr))) / eta
        return dict(th=th, F=F, H=H, Rf=Rf, Rr=Rr, Fh=Fh, sig=(abs(Rf) + abs(Rr)) / F)

    pts = [est(-ph + 2 * ph * i / 2000) for i in range(2001)]
    th0 = math.asin(rp / R)
    pts += [est(th0, +1), est(th0, -1)]
    return pts, est, ph


def tabla(PP):
    return _tabla(tuple(PP[k] for k in GEO_KEYS))


def kcil(PP):
    """k = F_cil / (T/n): máximo en la carrera [1/mm]."""
    return max(e["Fh"] for e in tabla(PP)[0])


def Fcil(PP, Tn):
    return kcil(PP) * Tn


def case_F(PP, W_tf, n, cid):
    mu, r = casos(PP)[cid]
    T = Nkn(PP, W_tf) * cfric(PP, mu, r)
    return Fcil(PP, T / n)


def Hasim_kN(PP):
    pts = tabla(PP)[0]; mg = PP["mu_g"]
    return Fst_kN(PP) * PP["eta_c"] * max(abs(1 / (1 + (mg - 0.05) * e["sig"]) - 1 / (1 + (mg + 0.05) * e["sig"])) for e in pts)


def W_giro(PP, n, FS, mu, r):
    """W máx. [tf] con FS = F_calado/F_cil = FS_req:  N* = n·F_st/(FS·k·c); W = (N* − W_mesa)/g."""
    Nstar = n * Fst_kN(PP) / (FS * kcil(PP) * cfric(PP, mu, r))
    return (Nstar - Wd_kN(PP)) / g0


# ---- pivote: modelo del núcleo (H_cil = F_pas) --------------------------------------
def hecc_kN(PP, N, mu=None):
    mu = PP["mu_d"] if mu is None else mu
    return max(mu * N * PP["e"] * kappa(PP), PP["Ch"] * N)


def pivot_core(PP, W_tf, n, opcion="F_en_Fcilmax"):
    """Criterio NUEVO del núcleo (P1): H_cil = F_pas·√(1+μ_s²) con n impar (diseño y calado).
    Devuelve (p_buje MPa, σ_flex MPa, H_cil_dis, H_cil_cal)."""
    N = Nkn(PP, W_tf); Hec = hecc_kN(PP, N); Has = Hasim_kN(PP)
    Hd = Hc = 0.0
    if n % 2 == 1:
        Tn = N * cfric(PP, PP["mu_d"], PP["r_ef"]) / n
        pts = tabla(PP)[0]
        e = max(pts, key=lambda q: q["Fh"]) if opcion == "F_en_Fcilmax" else max(pts, key=lambda q: q["F"])
        sr = math.sqrt(1 + PP["mu_s"] ** 2)
        Hd = sr * e["F"] * Tn; Hc = sr * PP["eta_c"] * Fst_kN(PP)
    p = (Hec + Has + Hd) * 1e3 / (PP["D_piv"] * PP["L_bush"])
    sg = (Hec + Has + Hc) * 1e3 * PP["e_piv"] / (math.pi * PP["D_piv"] ** 3 / 32)
    return p, sg, Hd, Hc


def bisect(f, lo=0.0, hi=5000.0, it=60):
    """Mayor x en [lo, hi] con f(x) verdadero (f monótona: verdadera hasta un límite)."""
    if not f(lo):
        return 0.0
    if f(hi):
        return hi
    for _ in range(it):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if f(m) else (lo, m)
    return lo


def pivot_all(PP, W_tf, n):
    """Las 4 verificaciones del grupo Pivote que dependen de W: (p_buje, σ_flex, σ_base, σ_cubo) con
    H_calado = (H_ecc o Ch·N) + H_asim + H_cil,cal para base y cubo (P4)."""
    p, sg, Hd, Hc = pivot_core(PP, W_tf, n)
    N = Nkn(PP, W_tf); Hcal = hecc_kN(PP, N) + Hasim_kN(PP) + Hc
    sb = Hcal * 1e3 / (PP["D_piv"] * PP["t_base"])
    sh = Hcal * 1e3 / ((PP["D_piv"] + 30) * PP["L_bush"])
    return p, sg, sb, sh, Hcal


def seat_sigma(PP, W_tf, n, L=None):
    """Asiento del pivote con momento: σ = H/(D·L)·(1 + 6(e_piv + L/2)/L), H = H de calado; momento respecto del centro del asiento
    (reacción lineal rígida: el brazo desde el centro es e_piv + L/2, con e_piv medido desde la cara superior de la base)."""
    L = PP["t_base"] if L is None else L
    H = pivot_all(PP, W_tf, n)[4]
    return H * 1e3 / (PP["D_piv"] * L) * (1 + 6 * (PP["e_piv"] + L / 2) / L)


def seat_Lmin(PP, W_tf, n):
    cap = 1.25 * PP["Fy"] / PP["Nd"]
    if seat_sigma(PP, W_tf, n, 5000.0) > cap:
        return float("inf")
    lo, hi = 1.0, 5000.0
    for _ in range(80):
        m = (lo + hi) / 2
        lo, hi = (lo, m) if seat_sigma(PP, W_tf, n, m) <= cap else (m, hi)
    return hi


def W_wood(PP):
    """wWood: límite de la madera (tf): q es ∝ W, así que W·cap/dem = p_wood·f·A/(φd(1+4e/R))."""
    RL = PP["D_load"] / 2
    A = math.pi * (RL ** 2 - ((PP["D_piv"] + 80) / 2) ** 2)
    return PP["p_wood"] * PP["f_apoyo"] * A / (PP["phi_d"] * (1 + 4 * PP["e"] / RL)) / 1e3 / g0


def pivot_ok(PP, W_tf, n):
    p, sg, sb, sh, _ = pivot_all(PP, W_tf, n)
    cap = 1.25 * PP["Fy"] / PP["Nd"]
    return p <= PP["p_bush"] and sg <= PP["Fy_piv"] / PP["Nd"] and sb <= cap and sh <= cap


def W_piv_core(PP, n):
    """wPiv NUEVO (P5): solo el grupo Pivote, búsqueda hasta 1500 tf."""
    return bisect(lambda W: pivot_ok(PP, W, n), 0.0, 1500.0)


def W_piv_lim(PP, n, which):
    idx = {"p": 0, "sg": 1, "sb": 2, "sh": 3}[which]
    cap = {"p": PP["p_bush"], "sg": PP["Fy_piv"] / PP["Nd"], "sb": 1.25 * PP["Fy"] / PP["Nd"], "sh": 1.25 * PP["Fy"] / PP["Nd"]}[which]
    return bisect(lambda W: pivot_all(PP, W, n)[idx] <= cap, 0.0, 1500.0)


def W_cap_core_like(PP, n):
    """wCap = mín(wGiro, wPiv, wWood) (wWood solo con opt_wood = 1)."""
    w = min(W_giro(PP, n, PP["FS_min"], *casos(PP)["dis"]), W_piv_core(PP, n))
    return min(w, W_wood(PP)) if PP.get("opt_wood") == 1 else w


# ---- modelo completo del pivote (resultante vectorial + par de fricción del buje) -------
def s_res(PP):
    return math.sqrt(1 + PP["mu_s"] ** 2)


def Rbush_service(PP, W_tf, n, variante, mu=None):
    """Reacción de servicio del buje [kN] con n impar (n = 1): resultante √(F²+H²) = s·F del pasador, MÁS la fricción
    excéntrica H_ecc (peor alineación), MÁS (variante 'V1','V2') H_asim·s. 'V2' y 'V3' realimentan el par de fricción
    del buje (μ_b·R·D/2) en el par T que debe vencer el cilindro. Devuelve (R_buje, F_cil_max)."""
    mu = PP["mu_d"] if mu is None else mu
    N = Nkn(PP, W_tf); Hec = hecc_kN(PP, N, mu); s = s_res(PP)
    Tb0 = N * mu * PP["r_ef"]
    m_b = PP["mu_bush"] * PP["D_piv"] / 2
    pts = tabla(PP)[0]
    best = (0.0, 0.0)
    for q in pts:
        phi = q["F"]                                    # F_pas por unidad de T/n (T/n = T cuando n = 1)
        if variante == "V1":
            Tn = N * cfric(PP, mu, PP["r_ef"]) / n          # par del núcleo (sin realimentar el buje)
        else:
            Tn = (Tb0 + m_b * Hec) / (1 - m_b * s * phi) / n   # T = T_base + μ_b·(s·F + H_ecc)·D/2  con F = φ·T/n
        R = s * phi * Tn + Hec
        FF = q["Fh"] * Tn
        best = (max(best[0], R), max(best[1], FF))
    return best


def pivot_full(PP, W_tf, n, variante, mu=None):
    """(p_buje, σ_flex, FS_giro) del modelo completo. n par: pareja simétrica; reacción = H_ecc + s·H_asim."""
    s = s_res(PP); Has = Hasim_kN(PP) * s
    N = Nkn(PP, W_tf); Hec = hecc_kN(PP, N, mu)
    if n % 2 == 0:
        Rs = Hec + Has; Rc = Hec + Has
        Fc = case_F(PP, W_tf, n, "dis")
    else:
        Rs0, Fc = Rbush_service(PP, W_tf, n, variante, mu)
        Rs = Rs0 + (Has if variante in ("V1", "V2") else 0.0)
        Rc = s * PP["eta_c"] * Fst_kN(PP) + Hec + Has
    p = Rs * 1e3 / (PP["D_piv"] * PP["L_bush"])
    sg = Rc * 1e3 * PP["e_piv"] / (math.pi * PP["D_piv"] ** 3 / 32)
    return p, sg, Fst_kN(PP) / Fc


def W_piv_full(PP, n, variante, con_giro=False, mu=None):
    fy = PP["Fy_piv"] / PP["Nd"]

    def f(W):
        p, sg, fs = pivot_full(PP, W, n, variante, mu)
        return p <= PP["p_bush"] and sg <= fy and (not con_giro or fs >= PP["FS_min"])
    return bisect(f)


# ---- cubierta de madera ---------------------------------------------------------------
def q_wood_core(PP, f=None):
    """q = φd·W/(f_apoyo·A)·(1+4e/R), A = π(R² − ((D_piv+80)/2)²), R = D_carga/2 (criterio nuevo M1/M3)."""
    RL = PP["D_load"] / 2; f = PP["f_apoyo"] if f is None else f
    A = math.pi * (RL ** 2 - ((PP["D_piv"] + 80) / 2) ** 2)
    return PP["phi_d"] * PP["W_tf"] * g0 * 1e3 / (f * A) * (1 + 4 * PP["e"] / RL)


def q_wood_nt(Pn, RL, e, hueco=0.0):
    """Presión máx. [MPa] bajo huella circular de radio RL con carga Pn [N] excéntrica e, SIN tracción
    (distribución lineal sobre la zona comprimida). Con e ≤ RL/4 coincide con la ley lineal completa.
    hueco = radio del agujero del pivote (sin madera): se descuenta del área (anillo)."""
    if hueco > 0:
        A = math.pi * (RL ** 2 - hueco ** 2)
        return Pn / A * (1 + 4 * e * RL / (RL ** 2 + hueco ** 2))
    if e <= RL / 4:
        return Pn / (math.pi * RL ** 2) * (1 + 4 * e / RL)
    if e >= RL:
        return float("inf")

    def mom(x0):
        t0 = math.asin(max(-1.0, min(1.0, x0 / RL))); nn = 2000; dt = (math.pi / 2 - t0) / nn
        Nn = Mm = 0.0
        for i in range(nn):
            t = t0 + (i + 0.5) * dt; x = RL * math.sin(t); w = 2 * RL * RL * math.cos(t) ** 2 * dt
            Nn += (x - x0) * w; Mm += (x - x0) * x * w
        return Mm / Nn, Nn
    lo, hi = -RL, RL * 0.999999
    for _ in range(70):
        mid = (lo + hi) / 2
        if mom(mid)[0] > e:                              # e(x0) crece con x0: x0 demasiado grande
            hi = mid
        else:
            lo = mid
    x0 = (lo + hi) / 2
    return Pn / mom(x0)[1] * (RL - x0)


def H_total(PP):
    return PP["t_base"] + 0.0 + PP["h_disc"] + (PP["t_wood"] if PP.get("opt_wood") == 1 else 0.0)


# ---- bomba ------------------------------------------------------------------------------
def pump(PP, n, F_dis_kN):
    Ab, Aa = A_bore(PP), A_ann(PP)
    Vext = n * Ab * PP["stroke"] / 1e6; Vret = n * Aa * PP["stroke"] / 1e6          # L
    Q = PP["Q_pump"]; Qr = PP["Q_ret"] if PP["Q_ret"] > 0 else Q
    tExt, tRet = Vext / Q, Vret / Qr
    tC = tExt + tRet; tRev = tC * int(PP["N_pin"])
    p_dis = F_dis_kN * 1e3 / Ab * 10
    PhE, PhR = p_dis * Q / 600, PP["p_ret"] * Qr / 600
    out = dict(Qr=Qr, tExt=tExt, tRet=tRet, tCycle=tC, tRev=tRev, vExt=Q * 1e6 / 60 / (n * Ab) / 1000,
               vRet=Qr * 1e6 / 60 / (n * Aa) / 1000, PhExt=PhE, PhRet=PhR, Pmotor=max(PhE, PhR) / PP["eta_pump"],
               PmotorAlarm=max(PP["p_alarm"] * Q / 600, PhR) / PP["eta_pump"], p_dis=p_dis, Vext=Vext, Vret=Vret)
    out["Qreq"] = (Vext + Vret) / (PP["t_vuelta_obj"] / int(PP["N_pin"])) if PP["t_vuelta_obj"] > 0 else 0.0
    return out


# ======================================================================================
# Registro de barridos
# ======================================================================================
class Sweep:
    def __init__(self, name):
        self.name, self.vals, self.n, self.dis, self.maxd, self.verd, self.rej, self.vm = name, [], 0, [], 0.0, {}, [], []

    def add_cmp(self, label, mine, core, tol=TOL):
        self.n += 1
        if core is None:
            return
        d = abs(mine - core) / abs(core) * 100 if core else (0.0 if abs(mine) < 1e-9 else 100.0)
        self.maxd = max(self.maxd, d)
        if d > tol * 100:
            self.dis.append((label, mine, core))

    def add_ceil(self, label, mine, core):
        """El núcleo redondea hacia arriba al mm entero: core ∈ [mine − 0,001; mine + 1)."""
        self.n += 1
        if not (-1e-3 <= core - mine < 1.0):
            self.dis.append((label, mine, core))

    def add_ver(self, v, key, mine_ok, core_st):
        """mine_ok: bool; core_st: 'ok' | 'fail' | None."""
        if core_st is None:
            return
        self.n += 1
        core_ok = core_st != "fail"
        if mine_ok != core_ok:
            self.vm.append((v, key, mine_ok, core_ok))
        self.verd.setdefault(key, []).append((v, core_ok))


def run_point(PP_over):
    D = export(PP_over)
    return D


def sweep_points(key, values, base=None):
    base = base or {}
    jobs = [dict(base, **{key: v}) for v in values]
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(export, jobs))
    return res


def eval_point(S, v, over, D):
    """Compara todo lo nuevo del núcleo con el modelo propio en un punto de barrido."""
    if D is None:
        S.rej.append(v); return
    PP = D["P"]; n = int(PP["n_cyl"]); S.vals.append(v)
    Fd = case_F(PP, PP["W_tf"], n, "dis")
    # --- casos de giro
    for c in D["derivados"]["casos"]:
        mu, r = casos(PP)[c["id"]]
        F = case_F(PP, PP["W_tf"], n, c["id"])
        S.add_cmp(f"F caso {c['id']}", F, c["F"])
        S.add_cmp(f"FS caso {c['id']}", Fst_kN(PP) / F, c["FS"])
        S.add_ver(v, f"gira {c['id']}", Fst_kN(PP) / F >= 1, "ok" if c["gira"] else "fail")
    S.add_ver(v, "FS_dis ≥ FS_min", Fst_kN(PP) / Fd >= PP["FS_min"], estado_core(D, "FS del accionamiento"))
    S.add_ver(v, "p_dis ≤ alarma", Fd * 1e3 / A_bore(PP) * 10 <= PP["p_alarm"], estado_core(D, "Presión de diseño frente a la alarma"))
    # --- bomba
    pm = pump(PP, n, Fd); b = D["bomba"]
    for k in ("Qr", "tExt", "tRet", "PhExt", "PhRet", "vExt", "vRet", "Pmotor", "PmotorAlarm", "Qreq"):
        S.add_cmp("bomba." + k, pm[k], b[k])
    S.add_cmp("tCycle", pm["tCycle"], D["derivados"]["tCycle"]); S.add_cmp("tRev", pm["tRev"], D["derivados"]["tRev"])
    S.add_ver(v, "v_ret ≤ máx", pm["vRet"] <= PP["v_ret_max"], estado_core(D, "Velocidad de retorno"))
    if PP["t_vuelta_obj"] > 0:
        S.add_ver(v, "t_vuelta ≤ objetivo", pm["tRev"] <= PP["t_vuelta_obj"], estado_core(D, "Tiempo por vuelta frente al objetivo"))
    S.add_cmp("P motor (check dem)", pm["Pmotor"], ver(D, "Potencia del motor")["dem"]); S.add_cmp("P motor alarma (check cap)", pm["PmotorAlarm"], ver(D, "Potencia del motor")["cap"])
    S.add_cmp("t vuelta (check info)", pm["tRev"], ver_exact(D, "Tiempo por vuelta")["dem"])
    # --- masa y presión de contacto
    Wd = Wd_kN(PP)
    S.add_cmp("Wd (kN)", Wd, D["apoyo"]["Wd"])
    S.add_cmp("N (kN)", Nkn(PP), D["derivados"]["N"])
    ND = PP["phi_d"] * PP["W_tf"] * g0 + Wd
    Ro, Ri = PP["D_top"] / 2, PP["D_piv"] / 2 + 15
    S.add_cmp("q_max interfaz", ND * 1e3 / (math.pi * (Ro ** 2 - Ri ** 2)) * (1 + 4 * PP["e"] * Ro / (Ro ** 2 + Ri ** 2)), D["derivados"]["q_max"])
    # --- cubierta
    cub = D["cubierta"]
    S.add_cmp("mWood", m_wood(PP), cub["mWood"]); S.add_cmp("dMasa", m_wood(PP), cub["dMasa"])
    q = [c for c in cub["checks"] if c["nombre"].startswith("Madera: aplastamiento")][0]
    S.add_cmp("q madera", q_wood_core(PP), q["dem"]); S.add_cmp("FU madera", q_wood_core(PP) / PP["p_wood"], q["fu"])
    S.add_ver(v, "madera: q ≤ p_wood", q_wood_core(PP) <= PP["p_wood"], q["estado"])
    k2 = [c for c in cub["checks"] if c["nombre"].startswith("Madera: la ley lineal")][0]
    S.add_cmp("4e/R_carga", 4 * PP["e"] / (PP["D_load"] / 2), k2["dem"] if k2["dem"] else 1e-12) if k2["dem"] else S.add_cmp("4e/R_carga", 4 * PP["e"] / (PP["D_load"] / 2) + 1, 1.0)
    S.add_ver(v, "madera: 4e/R ≤ 1", 4 * PP["e"] / (PP["D_load"] / 2) <= 1, k2["estado"])
    t = [c for c in cub["checks"] if c["nombre"].startswith("Madera: espesor")][0]
    S.add_ver(v, "madera: t ≥ 30", PP["t_wood"] >= 30, t["estado"])
    S.add_cmp("H total", H_total(PP), ver(D, "Altura total sobre el piso")["dem"])
    en = ver(D, "Enrase de la superficie")
    if en is not None:
        S.add_cmp("|H − h_riel|", abs(H_total(PP) - PP["h_skid"]), en["dem"])
        S.add_ver(v, "enrase", abs(H_total(PP) - PP["h_skid"]) <= PP["tol_skid"], en["estado"])
    elif PP["h_skid"] > 0:
        S.dis.append(("enrase ausente con h_skid > 0", 0, 1))
    # --- capacidades (núcleo: mercado.capacity para n del caso; capCil para n = 1, 2)
    cap = D["mercado"]["capacity"]
    S.add_cmp("W_giro diseño (FS_min)", W_giro(PP, n, PP["FS_min"], *casos(PP)["dis"]), cap["design"])
    S.add_cmp("W_giro diseño FS=1", W_giro(PP, n, 1.0, *casos(PP)["dis"]), cap["designFS1"])
    S.add_cmp("W_giro nominal FS=1", W_giro(PP, n, 1.0, *casos(PP)["nom"]), cap["nominal"])
    S.add_cmp("W_giro nominal FS_min", W_giro(PP, n, PP["FS_min"], *casos(PP)["nom"]), cap["nominalFS"])
    for cc in D["capCil"]:
        m = cc["n"]
        S.add_cmp(f"wGiro n={m}", W_giro(PP, m, PP["FS_min"], *casos(PP)["dis"]), cc["wGiro"])
        S.add_cmp(f"wNom n={m}", W_giro(PP, m, 1.0, *casos(PP)["nom"]), cc["wNom"])
        mine_g = W_giro(PP, m, PP["FS_min"], *casos(PP)["dis"])
        mine_pv = W_piv_core(PP, m)                       # solo grupo Pivote, hasta 1500 tf (P5)
        mine_cap = W_cap_core_like(PP, m)
        if PP.get("opt_wood") == 1:
            S.add_cmp(f"wWood n={m}", W_wood(PP), cc["wWood"])
        else:
            S.n += 1
            if cc["wWood"] is not None:
                S.dis.append((f"wWood n={m} debe ser null con opt_wood = 0", 0, cc["wWood"]))
        for lab, mine, core in ((f"wPiv n={m}", mine_pv, cc["wPiv"]), (f"wCap n={m}", mine_cap, cc["wCap"])):
            if core > 0 and mine > 0:
                S.add_cmp(lab, mine, core)
            else:
                S.n += 1
                if (core > 0) != (mine > 0):
                    S.dis.append((lab + " (cero / no cero)", mine, core))
    # --- pivote (réplica del núcleo)
    p, sg, sb, sh, Hcal = pivot_all(PP, PP["W_tf"], n)
    Hd, Hc = pivot_core(PP, PP["W_tf"], n)[2:]
    pb = ver(D, "Presión en el buje"); fx = ver(D, "Flexión del pivote")
    S.add_cmp("p buje", p, pb["dem"]); S.add_cmp("σ flexión pivote", sg, fx["dem"])
    vb = ver(D, "Aplastamiento del pivote en el agujero"); vh = ver(D, "Aplastamiento del buje en el cubo")
    capb = 1.25 * PP["Fy"] / PP["Nd"]
    S.add_cmp("σ aplast. agujero base", sb, vb["dem"]); S.add_cmp("σ aplast. buje en cubo", sh, vh["dem"])
    S.add_cmp("cap aplast. 1,25Fy/Nd", capb, vb["cap"])
    sv = ver(D, "Asiento del pivote en la base con momento")
    ss = seat_sigma(PP, PP["W_tf"], n); Lm = seat_Lmin(PP, PP["W_tf"], n)
    S.add_cmp("σ asiento con momento", ss, sv["dem"]); S.add_cmp("cap asiento", capb, sv["cap"])
    S.n += 1
    if sv["estado"] != "pend":
        S.dis.append(("asiento: estado distinto de pend", 0, 1))
    S.add_ver(v, "asiento: σ ≤ cap (estructura; núcleo pend)", ss <= capb, "fail" if "NO CUMPLE" in sv["nombre"] else "ok")
    mm = re.search(r"mínima ([0-9.,]+) mm", sv["nombre"])
    if mm:
        S.add_ceil("profundidad mínima del asiento (mm, el rótulo redondea hacia arriba)", Lm, float(mm.group(1).replace(",", ".")))
    S.add_ver(v, "base: σ ≤ 1,25Fy/Nd", sb <= capb, vb["estado"]); S.add_ver(v, "cubo: σ ≤ 1,25Fy/Nd", sh <= capb, vh["estado"])
    S.add_ver(v, "buje p ≤ p_bush", p <= PP["p_bush"], pb["estado"]); S.add_ver(v, "pivote σ ≤ Fy/Nd", sg <= PP["Fy_piv"] / PP["Nd"], fx["estado"])
    S.add_cmp("H_asim", Hasim_kN(PP), ver(D, "Empuje neto al pivote")["dem"])
    if n % 2 == 1:
        hc = ver(D, "Reacción del pivote por empuje no equilibrado")
        S.add_cmp("H_cil diseño", Hd, hc["dem"]); S.add_cmp("H_cil calado", Hc, hc["cap"])


# ======================================================================================
# PRUEBA 0 – Línea base
# ======================================================================================
print("# Revisión independiente de los cálculos nuevos del núcleo TT300-C (bomba, cubierta de madera, capacidades)")
print(f"Parámetros exportados = golden: {'sí' if not dif else 'NO, difieren ' + str(dif)}")
n0 = int(P["n_cyl"])
Fd0 = case_F(P, P["W_tf"], n0, "dis")
cd = [c for c in D0["derivados"]["casos"] if c["id"] == "dis"][0]
comp("0", "F_cil de diseño (kN)", Fd0, cd["F"]); comp("0", "p_dis (bar)", Fd0 * 1e3 / A_bore(P) * 10, cd["p"])
comp("0", "W_mesa (kN)", Wd_kN(P), D0["apoyo"]["Wd"])

# ======================================================================================
# 1. BOMBA Y RETORNO RÁPIDO
# ======================================================================================
pm = pump(P, n0, Fd0); b = D0["bomba"]
rows = []
for k, lab, u in (("tExt", "t avance", "min"), ("tRet", "t retorno", "min"), ("vExt", "v avance", "m/s"), ("vRet", "v retorno", "m/s"),
                  ("PhExt", "P hid. avance", "kW"), ("PhRet", "P hid. retorno", "kW"), ("Pmotor", "P motor", "kW"), ("Qr", "Q retorno efectivo", "L/min")):
    comp("1", f"{lab} ({u})", pm[k], b[k]); rows.append([lab, u, s3(pm[k]), s3(b[k])])
comp("1", "tCycle (min)", pm["tCycle"], D0["derivados"]["tCycle"]); comp("1", "tRev (min)", pm["tRev"], D0["derivados"]["tRev"])
comp("1", "V avance (L) = t·Q", pm["Vext"], b["tExt"] * P["Q_pump"]); comp("1", "V retorno (L) = t·Q", pm["Vret"], b["tRet"] * pm["Qr"])
vv = ver(D0, "Velocidad de retorno"); comp("1", "v_ret (check)", pm["vRet"], vv["dem"]); comp("1", "FU v_ret", pm["vRet"] / P["v_ret_max"], vv["fu"])
comp("1", "Potencia motor (check)", pm["Pmotor"], ver(D0, "Potencia del motor")["dem"])
comp("1", "Tiempo por vuelta (check)", pm["tRev"], ver_exact(D0, "Tiempo por vuelta")["dem"])
# barrido fijo del export (bombaBarrido): usa el mismo F_dis del caso base
for bb in D0["bombaBarrido"]:
    PQ = dict(P, Q_pump=bb["Q"], Q_ret=bb["Qr"] if bb["Qr"] != bb["Q"] else 0)
    pq = pump(PQ, n0, Fd0)
    for k, kk in (("Qr", "Qr"), ("tRev", "tRev"), ("tCycle", "tCycle"), ("Pmotor", "Pmotor"), ("vRet", "vRet")):
        comp("1", f"bombaBarrido Q={bb['Q']}/Qr={bb['Qr']}: {k}", pq[k], bb[kk])
table("Prueba 1 – Bomba, caso base (Q_pump = %s, Q_ret = %s ⇒ igual al de avance)" % (P["Q_pump"], P["Q_ret"]), ["Magnitud", "Unid.", "Propio", "Núcleo"], rows)
print(f"V avance = n·A·carrera = {n0}·{s3(A_bore(P))}·{P['stroke']} = {s3(pm['Vext'])} L; V retorno = {s3(pm['Vret'])} L; t vuelta = {s3(pm['tRev'])} min con N = {int(P['N_pin'])} pasadores")
# revisión crítica de la potencia
p_al, p_rel = P["p_alarm"], P["p_relief"]
Pm_al = max(p_al * P["Q_pump"] / 600, pm["PhRet"]) / P["eta_pump"]
Pm_rel = max(p_rel * P["Q_pump"] / 600, pm["PhRet"]) / P["eta_pump"]
Qcap = pm["Qr"] * A_bore(P) / A_ann(P)
table("Prueba 1b – Potencia del motor: presión de dimensionamiento (revisión crítica)", ["Criterio", "p (bar)", "P motor (kW)", "frente al núcleo"],
      [["Núcleo: presión de diseño (caso dis)", s3(pm["p_dis"]), s3(pm["Pmotor"]), "—"],
       ["Alarma (máx. presión de operación permitida) = PmotorAlarm del núcleo", s3(p_al), s3(Pm_al), f"{(Pm_al / pm['Pmotor'] - 1) * 100:+.1f} %"],
       ["Alivio (calado, intermitente)", s3(p_rel), s3(Pm_rel), f"{(Pm_rel / pm['Pmotor'] - 1) * 100:+.1f} %"]])
print(f"Caudal de descarga del lado émbolo durante el retorno = Q_ret·A/A_anular = {s3(Qcap)} L/min ({Qcap / pm['Qr']:.2f}× Q_ret); el núcleo no lo verifica (válvula y manguera de retorno)")
comp("1", "P motor a presión de alarma (kW)", Pm_al, b["PmotorAlarm"]); comp("1", "Potencia motor (check): cap = P a alarma", Pm_al, ver(D0, "Potencia del motor")["cap"])
print(f"B1 resuelto en el núcleo: PmotorAlarm = {s3(b['PmotorAlarm'])} kW (propio {s3(Pm_al)}); a p_alivio (700 bar, calado) harían falta {s3(Pm_rel)} kW si no se limita la potencia")
finding("B2", "menor", "tiempo por vuelta ideal: usa la carrera nominal completa (%s mm; la requerida es %s mm, −%.0f %%), sin compresibilidad del aceite (≈ +%.1f %% de t avance como cota), sin conmutación de válvulas ni aceleración; los efectos se compensan en parte"
        % (s3(P["stroke"]), s3(D0["derivados"]["K"]["s_req"]), (1 - D0["derivados"]["K"]["s_req"] / P["stroke"]) * 100, 7e-5 * pm["p_dis"] * 100),
        f"t vuelta = {s3(pm['tRev'])} min", "≈ ±5 %: informar como mínimo teórico")
# tiempo objetivo: caudal requerido vs. tiempo logrado
tq = pump(dict(P, t_vuelta_obj=40.0), n0, Fd0)
comp("1", "Q requerido para t_obj = 40 min (L/min)", tq["Qreq"], export({"t_vuelta_obj": 40})["bomba"]["Qreq"])
# Compresibilidad y tiempos muertos (cota)
beta_oil = 7e-5                                        # 1/bar (aceite mineral, ≈ 0,7 %/100 bar)
dV = beta_oil * pm["p_dis"] * pm["Vext"]
print(f"Cota de compresibilidad (β = 7e-5/bar) del volumen barrido a p_dis: ΔV = {s3(dV)} L por carrera ⇒ +{dV / P['Q_pump'] * 60:.1f} s por carrera "
      f"({dV / pm['Vext'] * 100:.1f} % de t avance); no incluida en el núcleo (solo ideal, sin tiempos muertos ni líneas)")

# ======================================================================================
# 2. CUBIERTA DE MADERA DURA
# ======================================================================================
PW = dict(P, opt_wood=1)
DW = export({"opt_wood": 1})
PWc = DW["P"]
cub = DW["cubierta"]
comp("2", "Masa de la cubierta (kg)", m_wood(PWc), cub["mWood"]); comp("2", "Δ masa total con cubierta (kg)", m_wood(PWc), cub["dMasa"])
comp("2", "Masa de la mesa con cubierta: W_mesa (kN)", Wd_kN(PWc), DW["apoyo"]["Wd"])
ND = PWc["phi_d"] * PWc["W_tf"] * g0 + Wd_kN(PWc); Ro, Ri = PWc["D_top"] / 2, PWc["D_piv"] / 2 + 15
qmax_w = ND * 1e3 / (math.pi * (Ro ** 2 - Ri ** 2)) * (1 + 4 * PWc["e"] * Ro / (Ro ** 2 + Ri ** 2))
comp("2", "q_max interfaz con la cubierta (MPa)", qmax_w, DW["derivados"]["q_max"])
ND_nw = P["phi_d"] * P["W_tf"] * g0 + Wd_kN(P)
dq = qmax_w / (ND_nw * 1e3 / (math.pi * (Ro ** 2 - Ri ** 2)) * (1 + 4 * P["e"] * Ro / (Ro ** 2 + Ri ** 2))) - 1
qk = [c for c in cub["checks"] if c["nombre"].startswith("Madera: aplastamiento")][0]
tk = [c for c in cub["checks"] if c["nombre"].startswith("Madera: espesor")][0]
comp("2", "Aplastamiento de la madera q (MPa)", q_wood_core(PWc), qk["dem"]); comp("2", "FU madera", q_wood_core(PWc) / PWc["p_wood"], qk["fu"])
comp("2", "Espesor mínimo: FU = 30/t", 30 / PWc["t_wood"], tk["fu"])
comp("2", "Altura total H (mm), t_wood = 0 (sin cubierta)", H_total(P), ver(D0, "Altura total sobre el piso")["dem"])
comp("2", "Altura total H (mm) con cubierta", H_total(PWc), ver(DW, "Altura total sobre el piso")["dem"])
DS = export({"opt_wood": 1, "h_skid": 280}); DS2 = export({"opt_wood": 1, "h_skid": 240})
comp("2", "Enrase con h_riel = 280: |H − h| (mm)", abs(H_total(PWc) - 280), ver(DS, "Enrase")["dem"])
comp("2", "Enrase con h_riel = 240: |H − h| (mm)", abs(H_total(PWc) - 240), ver(DS2, "Enrase")["dem"])

# ---- revisión crítica del aplastamiento (criterio nuevo: f_apoyo, A con agujero, verificación 4e/R ≤ 1)
R_L = PWc["D_load"] / 2; hueco = (PWc["D_piv"] + 80) / 2
PL = PWc["phi_d"] * PWc["W_tf"] * g0 * 1e3
fa = PWc["f_apoyo"]
q_core = q_wood_core(PWc); qf1 = q_wood_core(PWc, 1.0)
k2 = [c for c in cub["checks"] if c["nombre"].startswith("Madera: la ley lineal")][0]
comp("2", "Verificación M2: 4e/R_carga", 4 * PWc["e"] / R_L, k2["dem"]); comp("2", "Verificación M2: FU", 4 * PWc["e"] / R_L / 1.0, k2["fu"])
A_ann_w = math.pi * (R_L ** 2 - hueco ** 2)
q_exact = PL / (fa * A_ann_w) * (1 + 4 * PWc["e"] * R_L / (R_L ** 2 + hueco ** 2))      # Navier exacto del anillo (carga centrada en la huella)
q_nt = q_wood_nt(PL, R_L, PWc["e"]) / fa
rows = []
for f in (1.0, 0.8, 0.6, fa, qf1 / PWc["p_wood"], 0.4, 0.3, 0.2, 0.1):
    qq = qf1 / f
    rows.append([f"{f * 100:.1f} %" + (" (f_apoyo)" if f == fa else (" (f crítico)" if abs(f - qf1 / PWc["p_wood"]) < 1e-12 else "")), s3(qq), s3(qq / PWc["p_wood"]), "cumple" if qq <= PWc["p_wood"] else "NO CUMPLE"])
table("Prueba 2b – Aplastamiento de la madera según la fracción real f de apoyo (q = q(f=1)/f; el núcleo usa f_apoyo = %s)" % s3(fa),
      ["f = A_contacto/A_anillo", "q (MPa)", "FU", "veredicto"], rows)
f_crit = qf1 / PWc["p_wood"]
A_req = f_crit * A_ann_w / 1e6
print(f"Fracción crítica de apoyo f_crít = q(f=1)/p_wood = {f_crit * 100:.1f} % (A_contacto = {A_req:.3f} m²); con f_apoyo = {fa} el margen es {(1 - q_core / PWc['p_wood']) * 100:.1f} % (FU {q_core / PWc['p_wood']:.3f}).")
table("Prueba 2c – Efectos residuales sobre q de la madera (D_load = %s, e = %s, f_apoyo = %s)" % (s3(PWc["D_load"]), s3(PWc["e"]), s3(fa)),
      ["Variante", "q (MPa)", "Δ frente al núcleo"],
      [["Núcleo: A del anillo × (1 + 4e/R_carga)", s3(q_core), "—"],
       ["Navier exacto del anillo: 1 + 4eR/(R² + r²)", s3(q_exact), f"{(q_exact / q_core - 1) * 100:+.2f} %"],
       [f"Sin tracción (solo difiere si 4e/R > 1, que el núcleo ya rechaza)", s3(q_nt), f"{(q_nt / q_core - 1) * 100:+.2f} %"]])
rows = []
for dl in (800, 1000, 1200, 1600, 2000):
    for ee in (100, 150, 200, 250, 300):
        RR = dl / 2
        if 4 * ee / RR <= 1 or ee >= RR:
            continue
        PPt = dict(PWc, D_load=dl, e=ee)
        qa = q_wood_core(PPt); qb = q_wood_nt(PL, RR, ee) / fa
        rows.append([dl, ee, f"{4 * ee / RR:.2f}", s3(qa), s3(qb), f"{(qb / qa - 1) * 100:+.1f} %", "M2 falla (rechazado)"])
table("Prueba 2d – Combinaciones con 4e/R > 1: la ley lineal subestima q, pero la verificación M2 del núcleo las rechaza", ["D_carga", "e", "4e/R", "q lineal", "q sin tracción", "Δ", "núcleo"], rows)
finding("M1", "menor", "f_apoyo = %s es un SUPUESTO por defecto (resuelve la crítica: ya hay factor de contacto), sin respaldo geométrico: con f = %s el FU es %.3f («warn») y el margen es %.1f %%; falla si el apoyo real es < %.1f %% del anillo (A_contacto < %.2f m²). "
        "El factor 1/f supone parches de apoyo repartidos uniformemente en la huella; con patines asimétricos o cargas concentradas q local será mayor" % (s3(fa), s3(fa), q_core / PWc["p_wood"], (1 - q_core / PWc["p_wood"]) * 100, f_crit * 100, A_req),
        f"q = {s3(q_core)} MPa, FU {s3(q_core / PWc['p_wood'])}", f"el proyectista debe fijar f_apoyo con la geometría real de patines/vigas; f = 0,4 ⇒ q = {s3(qf1 / 0.4)} MPa (FU {s3(qf1 / 0.4 / PWc['p_wood'])})")
finding("M3", "menor", "q usa A del anillo con el factor (1 + 4e/R_carga) de la huella completa; el Navier exacto del anillo (1 + 4eR/(R²+r²)) da un factor menor: el núcleo es conservador",
        f"q = {s3(q_core)} MPa", f"{s3(q_exact)} MPa ({(q_exact / q_core - 1) * 100:+.2f} %)")
finding("M4", "menor", "p_wood = %s MPa (dato de proveedor) se usa como tensión ADMISIBLE sin factor de duración de carga (fluencia en madera bajo carga permanente) ni de humedad. "
        "Los valores admisibles de compresión normal NCh 1198 / de fichas de especies duras deben confirmarse; si 6 MPa es el límite de proporcionalidad, el admisible es menor" % s3(PWc["p_wood"]),
        f"FU {s3(q_core / PWc['p_wood'])}", "confirmar la base de p_wood (admisible, no ruptura) o agregar factor KD; con FU 0,95 no hay margen para un KD < 1")
print(f"Cubierta: +{s3(m_wood(PWc))} kg ({m_wood(PWc) / (masa_mesa(P)) * 100:.1f} % de la mesa), N +{s3(m_wood(PWc) * g0 / 1e3)} kN, q_max interfaz {dq * 100:+.3f} %")

# ======================================================================================
# 3. CAPACIDAD DE GIRO
# ======================================================================================
cap = D0["mercado"]["capacity"]
muN, ruN = casos(P)["nom"]
W_des = W_giro(P, n0, P["FS_min"], *casos(P)["dis"]); W_des1 = W_giro(P, n0, 1.0, *casos(P)["dis"])
W_nom1 = W_giro(P, n0, 1.0, *casos(P)["nom"]); W_nomFS = W_giro(P, n0, P["FS_min"], *casos(P)["nom"])
for lab, mine, key in (("W diseño (FS ≥ FS_min, μ_d, r_ef)", W_des, "design"), ("W diseño FS = 1", W_des1, "designFS1"),
                       ("W nominal (FS = 1, μ_nom, r_u)", W_nom1, "nominal"), ("W nominal con FS_min", W_nomFS, "nominalFS")):
    comp("3", lab + " (tf)", mine, cap[key])
# bucle cerrado: exportar con W = mi capacidad y leer el FS del núcleo
def lazo(W, cid, n=None):
    over = {"W_tf": W}
    if n is not None:
        over["n_cyl"] = n
    D = export(over)
    return [c for c in D["derivados"]["casos"] if c["id"] == cid][0] if D else None
c1 = lazo(W_des, "dis"); c2 = lazo(W_des1, "dis"); c3 = lazo(W_nom1, "nom"); c4 = lazo(W_nomFS, "nom")
comp("3", "Lazo cerrado: FS del núcleo en W = W_diseño (esperado FS_min)", c1["FS"], P["FS_min"], tol=2e-3)
comp("3", "Lazo cerrado: FS del núcleo en W = W_diseño,FS1 (esperado 1)", c2["FS"], 1.0, tol=2e-3)
comp("3", "Lazo cerrado: FS nominal del núcleo en W = W_nominal (esperado 1)", c3["FS"], 1.0, tol=2e-3)
comp("3", "Lazo cerrado: FS nominal del núcleo en W = W_nominal,FS (esperado FS_min)", c4["FS"], P["FS_min"], tol=2e-3)
# bordes: ±0,3 % de W cambia el veredicto «gira»/FS
flips = []
for lab, W, cid, key in (("diseño FS_min", W_des, "dis", None), ("diseño FS=1", W_des1, "dis", "gira"), ("nominal FS=1", W_nom1, "nom", "gira")):
    for fac in (0.997, 1.003):
        c = lazo(W * fac, cid)
        if key == "gira":
            ok = c["gira"]
        else:
            ok = c["FS"] >= P["FS_min"]
        flips.append((lab, W * fac, ok))
rowsf = []
for i in range(0, len(flips), 2):
    a_, b_ = flips[i], flips[i + 1]
    exp_ = (a_[2] is True and b_[2] is False)
    rowsf.append([a_[0], s3(a_[1]), "cumple" if a_[2] else "no cumple", s3(b_[1]), "cumple" if b_[2] else "no cumple", "cambia en el W propio" if exp_ else "NO cambia"])
    comp("3", f"Veredicto cambia en W propio: {a_[0]}", 1.0 if exp_ else 0.0, 1.0)
table("Prueba 3a – Capacidad de giro: el veredicto del núcleo cambia en mi W (±0,3 %)", ["Capacidad", "W − 0,3 %", "veredicto", "W + 0,3 %", "veredicto", "conclusión"], rowsf)
kc = kcil(P); cdis = cfric(P, *casos(P)["dis"])
table("Prueba 3b – Capacidad de giro (tf), n = %d" % n0, ["Criterio", "μ", "r (mm)", "FS", "W propio", "W núcleo", "Δ %"],
      [["Diseño", s3(P["mu_d"]), s3(P["r_ef"]), s3(P["FS_min"]), s3(W_des), s3(cap["design"]), f"{(W_des / cap['design'] - 1) * 100:+.3f}"],
       ["Diseño, FS = 1 (límite de calado)", s3(P["mu_d"]), s3(P["r_ef"]), "1", s3(W_des1), s3(cap["designFS1"]), f"{(W_des1 / cap['designFS1'] - 1) * 100:+.3f}"],
       ["Nominal, FS = 1", s3(muN), s3(ruN), "1", s3(W_nom1), s3(cap["nominal"]), f"{(W_nom1 / cap['nominal'] - 1) * 100:+.3f}"],
       ["Nominal con FS_min", s3(muN), s3(ruN), s3(P["FS_min"]), s3(W_nomFS), s3(cap["nominalFS"]), f"{(W_nomFS / cap['nominalFS'] - 1) * 100:+.3f}"]])
print(f"k = F_cil/(T/n) = {kc:.6e} 1/mm; c(μ_d, r_ef) = {cdis:.3f} mm; F_cil = k·c·N/n ⇒ lineal en N = W + W_mesa; W_mesa = {s3(Wd_kN(P))} kN ⇒ F no es ∝ W (la mesa suma {Wd_kN(P) / (P['W_tf'] * g0) * 100:.2f} % de N)")
# otras restricciones que el W de «capacidad» NO incluye
Wal = bisect(lambda W: case_F(P, W, n0, "dis") * 1e3 / A_bore(P) * 10 <= P["p_alarm"])
Wcont = bisect(lambda W: case_F(P, W, n0, "cont") <= Fst_kN(P))
Wbor = bisect(lambda W: case_F(P, W, n0, "borde") <= Fst_kN(P))
Wwood = PWc["p_wood"] * PWc["f_apoyo"] * math.pi * (R_L ** 2 - hueco ** 2) / (PWc["phi_d"] * (1 + 4 * PWc["e"] / R_L)) / 1e3 / g0     # tf
Wint = bisect(lambda W: ((PWc["phi_d"] * W * g0 + Wd_kN(P)) * 1e3 / (math.pi * (Ro ** 2 - Ri ** 2)) * (1 + 4 * P["e"] * Ro / (Ro ** 2 + Ri ** 2))) <= P["q_adm"])
Wal450 = bisect(lambda W: case_F(P, W, n0, "dis") * 1e3 / A_bore(P) * 10 <= 450)
table("Prueba 3c – Otros límites de W en el modelo (el «capacity» del núcleo solo considera FS)", ["Límite", "W (tf)", "frente a W_diseño"],
      [["FS ≥ FS_min (capacity.design)", s3(W_des), "—"], ["p_dis ≤ p_alarma", s3(Wal), f"{(Wal / W_des - 1) * 100:+.1f} %"],
       ["Gira con grasa contaminada (F_cont ≤ F_calado)", s3(Wcont), f"{(Wcont / W_des - 1) * 100:+.1f} %"],
       ["Gira con contacto en el borde", s3(Wbor), f"{(Wbor / W_des - 1) * 100:+.1f} %"],
       ["Presión de contacto q_max ≤ q_adm", s3(Wint), f"{(Wint / W_des - 1) * 100:+.1f} %"],
       ["Aplastamiento de la madera ≤ p_wood (con la cubierta)", s3(Wwood), f"{(Wwood / W_des - 1) * 100:+.1f} %"]])
Wmin_other = min(Wal, Wcont, Wbor, Wint)
# primera verificación NO de giro que falla en el núcleo al subir W (bisección con el exportador)
def fallas(W):
    D = export({"W_tf": W})
    return [v for v in D["verificaciones"] if v["estado"] == "fail" and v["grp"] != "Giro"] if D else []
lo, hi = P["W_tf"], 1500.0
if not fallas(lo):
    for _ in range(14):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if not fallas(mid) else (lo, mid)
    W_struct = lo; nm_struct = "; ".join(v["grp"] + ": " + v["nombre"][:45] for v in fallas(hi))
else:
    W_struct, nm_struct = 0.0, "falla en la línea base"
print(f"Primera verificación no-giro que falla al subir W (núcleo): W = {s3(W_struct)} tf → {nm_struct}")
Dw_cap = DW["mercado"]["capacity"]["design"]; Dw_cc = DW["capCil"][1]
comp("3", "Con cubierta: wWood (tf) = p_wood·f·A/(φd(1+4e/R))", Wwood, Dw_cc["wWood"])
comp("3", "Con cubierta: wCap(n=2) = mín(wGiro, wPiv, wWood) (tf)", W_cap_core_like(PWc, 2), Dw_cc["wCap"])
comp("3", "Sin cubierta: wWood es null (1 = sí)", 1.0 if D0["capCil"][1]["wWood"] is None else 0.0, 1.0)
print(f"C1 resuelto en el núcleo: wWood = {s3(Dw_cc['wWood'])} tf, wCap(n=2) con cubierta = {s3(Dw_cc['wCap'])} tf (capacity.design, solo giro: {s3(Dw_cap)} tf)")
if Dw_cap > Dw_cc["wCap"] * 1.001:
    finding("C1", "menor", "C1 incorporado en capCil (wWood, wCap = mín(giro, pivote, madera)); queda `mercado.capacity` (design, designFS1, nominal) solo de giro: con la cubierta muestra %s tf frente a wCap = %s tf" % (s3(Dw_cap), s3(Dw_cc["wCap"])),
            f"capacity.design = {s3(Dw_cap)} tf", f"{s3(Dw_cc['wCap'])} tf con cubierta")
if Wmin_other < W_des * 0.999 and Wmin_other != Wwood or W_struct < W_des * 0.999:
    finding("C2", "importante", "El capacity es mayor que otro límite del propio modelo (alarma, contaminado, q_adm o estructura)", f"capacity.design = {s3(W_des)} tf", f"mín. de otros límites = {s3(min(Wmin_other, W_struct if W_struct > 0 else 1e9))} tf")
else:
    finding("C2", "menor", "El «capacity»/capCil mide solo la capacidad de GIRO (FS) y del pivote, no la de carga: no incluye la alarma (con p_alarma = 450 bar el límite sería %s tf y wCap seguiría en %s tf; antes wPiv lo captaba, ahora no), contaminado, q_adm ni la estructura. Primer fallo estructural del núcleo (%s) en W = %s tf, apenas por encima de la capacidad de giro de %s tf; la capacidad nominal (%s tf, FS = 1, μ_nom) es solo de giro y no es capacidad de carga" % (s3(Wal450), s3(W_des), nm_struct.split(";")[0], s3(W_struct), s3(W_des), s3(W_nom1)),
            f"capacity.design = {s3(W_des)} tf; nominal = {s3(W_nom1)} tf", f"capacidad de carga = mín(giro, estructura) = {s3(min(W_des, W_struct))} tf; el «nominal» no debe publicarse como capacidad")

# ======================================================================================
# 4. CAPACIDAD SEGÚN N.º DE CILINDROS Y PIVOTE
# ======================================================================================
rows = []
cap_b = 1.25 * P["Fy"] / P["Nd"]
for cc in D0["capCil"]:
    m = cc["n"]
    wg = W_giro(P, m, P["FS_min"], *casos(P)["dis"]); wn = W_giro(P, m, 1.0, *casos(P)["nom"])
    wpc = W_piv_core(P, m); wcp = W_cap_core_like(P, m)
    comp("4", f"n = {m}: wGiro (tf)", wg, cc["wGiro"]); comp("4", f"n = {m}: wNom (tf)", wn, cc["wNom"])
    if cc["wPiv"] > 0 and wpc > 0:
        comp("4", f"n = {m}: wPiv, solo Pivote hasta 1500 tf (tf)", wpc, cc["wPiv"])
        comp("4", f"n = {m}: wCap = mín(wGiro, wPiv) (tf)", wcp, cc["wCap"])
    else:
        comp("4", f"n = {m}: wPiv = 0 (la base no cumple a ninguna W; 1 = sí)", 1.0 if wpc == 0 else 0.0, 1.0 if cc["wPiv"] == 0 else 0.0)
        comp("4", f"n = {m}: wCap = 0 (1 = sí)", 1.0 if wcp == 0 else 0.0, 1.0 if cc["wCap"] == 0 else 0.0)
    lim = {"buje": W_piv_lim(P, m, "p"), "flexión": W_piv_lim(P, m, "sg"), "base": W_piv_lim(P, m, "sb"), "cubo": W_piv_lim(P, m, "sh")}
    rows.append([m, s3(wg), s3(cc["wGiro"]), s3(wpc), s3(cc["wPiv"]), s3(wcp), s3(cc["wCap"])] + [s3(lim[k]) for k in ("buje", "flexión", "base", "cubo")])
table("Prueba 4a – Capacidad por n.º de cilindros (tf); límites individuales del grupo Pivote (0 = no cumple ni sin carga, tope 1500)",
      ["n", "wGiro propio", "wGiro núcleo", "wPiv propio", "wPiv núcleo", "wCap propio", "wCap núcleo", "buje", "flexión", "agujero base", "buje en cubo"], rows)
t_req = {}
for Wq in (50, 100, 116, 165):
    Hc_q = pivot_all(P, Wq, 1)[4]
    t_req[Wq] = Hc_q * 1e3 / (P["D_piv"] * cap_b)
print("t_base mínimo para que el agujero de la base cumpla con n = 1: " + "; ".join(f"W = {k} tf → {s3(v)} mm" for k, v in t_req.items()) + f" (t_base = {P['t_base']} mm)")
# H_cil del núcleo: ¿en qué posición se toma F_pas de diseño?
D1 = export({"n_cyl": 1, "W_tf": 100}); P1 = D1["P"]
hc = ver(D1, "Reacción del pivote por empuje no equilibrado")
for opt in ("F_en_Fcilmax", "F_max"):
    p_, s_, Hd_, Hc_ = pivot_core(P1, 100, 1, opt)
    comp("4", f"n = 1, W = 100: H_cil de diseño, F_pas en {'la posición de F_cil máx.' if opt == 'F_en_Fcilmax' else 'F_pas máx.'} (kN)", Hd_, hc["dem"])
p_, s_, Hd_, Hc_ = pivot_core(P1, 100, 1)
comp("4", "n = 1, W = 100: H_cil de calado = η·F_calado (kN)", Hc_, hc["cap"])
pb1, fx1 = ver(D1, "Presión en el buje"), ver(D1, "Flexión del pivote")
comp("4", "n = 1, W = 100: p buje (MPa)", p_, pb1["dem"]); comp("4", "n = 1, W = 100: σ flexión pivote (MPa)", s_, fx1["dem"])
comp("4", "H_asim (kN)", Hasim_kN(P), ver(D0, "Empuje neto al pivote")["dem"])
comp("4", "n = 2, W = 300: p buje (MPa)", pivot_core(P, 300, 2)[0], ver(D0, "Presión en el buje")["dem"])
comp("4", "n = 2, W = 300: σ flexión pivote (MPa)", pivot_core(P, 300, 2)[1], ver(D0, "Flexión del pivote")["dem"])

# ---- Revisión crítica: modelo completo del pivote con n = 1
s = s_res(P)
pts = tabla(P)[0]
e_max_F = max(pts, key=lambda q: q["F"]); e_max_Fh = max(pts, key=lambda q: q["Fh"])
fy_p = P["Fy_piv"] / P["Nd"]
w_core1 = bisect(lambda W: pivot_core(P, W, 1)[0] <= P["p_bush"] and pivot_core(P, W, 1)[1] <= fy_p, 0.0, 1500.0)   # buje + flexión (criterio nuevo)
w_V1 = W_piv_full(P, 1, "V1"); w_V2 = W_piv_full(P, 1, "V2"); w_V3 = W_piv_full(P, 1, "V3")
Wc = w_core1
Nn = Nkn(P, Wc); Hec = hecc_kN(P, Nn); Tn1 = Nn * cfric(P, P["mu_d"], P["r_ef"])
F_des = e_max_Fh["F"] * Tn1; F_des_max = e_max_F["F"] * Tn1
Has = Hasim_kN(P)
rows = [["F_pas (normal a la cara) en la posición de F_cil máx.", s3(F_des), "—"],
        ["F_pas máx. de la carrera (otra posición)", s3(F_des_max), f"{(F_des_max / F_des - 1) * 100:+.2f} %"],
        ["H = μ_s·F (fricción en la cara, en x)", s3(P["mu_s"] * F_des), "incluida desde P1 vía la resultante"],
        ["Resultante √(F²+H²) = H_cil del núcleo nuevo", s3(s * F_des), f"{(s - 1) * 100:+.2f} % sobre F"],
        ["H_ecc (fricción excéntrica de la mesa, μ_d)", s3(Hec), "peor alineación con el pasador"],
        ["H_asim (fricción desigual de patines)", s3(Has), "en servicio no aplica con n = 1 (F_pas lo fija el par); sí a calado"],
        ["Reacción de servicio, núcleo nuevo: s·F + H_ecc + H_asim", s3(s * F_des + Hec + Has), "p = %s MPa" % s3((s * F_des + Hec + Has) * 1e3 / (P["D_piv"] * P["L_bush"]))]]
table("Prueba 4b – Reacción del pivote con n = 1 en W = %s tf (límite de buje del núcleo), componentes en kN" % s3(Wc), ["Componente", "kN", "Observación"], rows)
Rb, Ffb = Rbush_service(P, Wc, 1, "V2")
print(f"Par de fricción del buje con n = 1: el núcleo usa μ_b·H_ecc·D/2 = {s3(P['mu_bush'] * Hec * P['D_piv'] / 2 / 1e3)} kN·m; con la reacción completa "
      f"μ_b·R·D/2 = {s3(P['mu_bush'] * Rb * P['D_piv'] / 2 / 1e3)} kN·m ({(P['mu_bush'] * (Rb - Hec) * P['D_piv'] / 2) / (Nn * cfric(P, P['mu_d'], P['r_ef'])) * 100:.2f} % de T); F_cil máx. sube {(Ffb / (Fcil(P, Tn1)) - 1) * 100:+.2f} %")
w_V2c = W_piv_full(P, 1, "V2", mu=P["mu_cont"]); w2c_c = W_piv_full(P, 2, "V1", mu=P["mu_cont"])
rows = [["Núcleo nuevo (H_cil = s·F_pas + H_ecc + H_asim; buje y flexión)", s3(w_core1), "—"],
        ["V1: igual con s también en H_asim", s3(w_V1), f"{(w_V1 / w_core1 - 1) * 100:+.2f} %"],
        ["V2: V1 + par de fricción del buje con la reacción completa (realimentado)", s3(w_V2), f"{(w_V2 / w_core1 - 1) * 100:+.2f} %"],
        ["V3: V2 sin H_asim en servicio (físico: F_pas lo fija el par)", s3(w_V3), f"{(w_V3 / w_core1 - 1) * 100:+.2f} %"],
        ["V2 con grasa contaminada (μ_cont = %s, mismo r_ef)" % s3(P["mu_cont"]), s3(w_V2c), f"{(w_V2c / w_core1 - 1) * 100:+.2f} %"],
        ["Núcleo nuevo con todas las verificaciones del grupo (incl. agujero de la base)", s3(W_piv_core(P, 1)), "n = 1 no cumple a ninguna W con t_base = %s" % P["t_base"]]]
table("Prueba 4c – Capacidad con n = 1 (tf): residuos del modelo del pivote tras P1", ["Modelo", "wPiv (tf)", "Δ vs núcleo nuevo"], rows)
w2c = W_piv_core(P, 2)
w2f = W_piv_full(P, 2, "V1")
print(f"n = 2: wPiv (núcleo nuevo, solo Pivote) = {s3(w2c)} tf; modelo completo (H_ecc + s·H_asim) = {s3(w2f)} tf ({(w2f / w2c - 1) * 100:+.2f} %); con μ_cont {s3(w2c_c)} tf ({(w2c_c / w2c - 1) * 100:+.1f} %)")
Rc1 = s * P["eta_c"] * Fst_kN(P) + Hec + Has
R2 = hecc_kN(P, Nkn(P)) + Has
print(f"Reparto buje–pivote: la MISMA reacción R atraviesa ambos en serie (buje: p = R/(D·L) en servicio; pivote: M = R·e_piv a calado). "
      f"A calado con n = 1 (W = {s3(Wc)} tf): R = {s3(Rc1)} kN, M = {s3(Rc1 * P['e_piv'] / 1e3)} kN·m, σ = {s3(Rc1 * 1e3 * P['e_piv'] / (math.pi * P['D_piv'] ** 3 / 32))} MPa (FU {s3(Rc1 * 1e3 * P['e_piv'] / (math.pi * P['D_piv'] ** 3 / 32) / fy_p)}); "
      f"con n = 2: R = {s3(R2)} kN, M = {s3(R2 * P['e_piv'] / 1e3)} kN·m")
delta_pct = (w_V2 / w_core1 - 1) * 100
delta3 = (w_V3 / w_core1 - 1) * 100
finding("P1", "importante" if abs(delta_pct) > 5 else "menor", "P1 incorporado (H_cil = s·F_pas verificado, lo comprueban las comparaciones). Residuo: el par de fricción del buje usa solo H_ecc, no la reacción completa del pasador",
        f"wPiv(n=1, buje+flexión) = {s3(w_core1)} tf", f"con realimentación (V2) {s3(w_V2)} tf ({delta_pct:+.2f} %); con μ_cont {s3(w_V2c)} tf ({(w_V2c / w_core1 - 1) * 100:+.1f} %)")
finding("P2", "menor", "H_asim se suma a H_cil en servicio con n = 1, pero el empuje desigual por μ_g solo existe a calado (en servicio F_pas lo fija el par): conservador",
        f"H_asim = {s3(Has)} kN en p buje", f"V3: {s3(w_V3)} tf frente a V2 {s3(w_V2)} tf")
D3 = export({"n_cyl": 3, "W_tf": 100}); D3d = export({"n_cyl": 3})
if D3:
    h3 = ver(D3, "Reacción del pivote por empuje no equilibrado")
    finding("P3", "menor", "n = 3: el núcleo trata cualquier n impar como 1 cilindro sin par (H_cil = s·F_pas). Con 3 cilindros a 120° y pasadores en fase la resultante vectorial es ≈ 0; "
            "con la geometría de guía paralela a y solo existen parejas ±x, así que n = 3 no está definido geométricamente (conservador, no verificado)",
            f"H_cil = {s3(h3['dem'])} kN a W = 100; con W = 300 el buje {s3(ver(D3d, 'Presión en el buje')['dem'])} MPa ({ver(D3d, 'Presión en el buje')['estado']})",
            f"resultante ≈ 0: buje {s3(pivot_core(dict(P, n_cyl=3), 300, 4)[0])} MPa (como n par); definir la disposición de 3 cilindros o limitar n a {1, 2, 4}")
# P4: resultado de diseño y residuo (momento en la raíz del pivote)
H2 = pivot_all(P, P["W_tf"], 2)[4]; H1 = pivot_all(dict(P, n_cyl=1), 100, 1)[4]
fac_old = 1 + 6 * P["e_piv"] / P["t_base"]                       # mi fórmula anterior: momento respecto de la cara superior (INCORRECTA)
fac_M = 1 + 6 * (P["e_piv"] + P["t_base"] / 2) / P["t_base"]      # correcta: momento respecto del centro del asiento
sd = lambda H, f: H * 1e3 / (P["D_piv"] * P["t_base"]) * f
Lm2 = seat_Lmin(P, P["W_tf"], 2); Lm1 = seat_Lmin(dict(P, n_cyl=1), 100, 1)
sv0 = ver(D0, "Asiento del pivote en la base con momento")
comp("4", "Asiento del pivote con momento, n = 2 W = 300: σ (MPa)", seat_sigma(P, P["W_tf"], 2), sv0["dem"])
comp("4", "Asiento del pivote con momento: cap 1,25Fy/Nd (MPa)", cap_b, sv0["cap"])
comp("4", "Asiento del pivote con momento: profundidad mínima L (mm, rótulo redondeado hacia arriba)", math.ceil(Lm2), float(re.search(r"mínima ([0-9.,]+) mm", sv0["nombre"]).group(1)))
comp("4", "Asiento del pivote: estado pendiente (1 = pend)", 1.0 if sv0["estado"] == "pend" else 0.0, 1.0)
table("Prueba 4d – Asiento del pivote en la base: presión media del agujero frente al asiento con momento (brazo = e_piv + L/2 desde el centro del asiento)",
      ["Caso", "H calado (kN)", "σ media H/(D·L)", "σ (1 + 6e/L) [mi fórmula anterior]", "σ (1 + 6(e + L/2)/L) [núcleo]", "adm.", "FU", "L mínimo (mm)"],
      [["n = 2, W = %s tf" % s3(P["W_tf"]), s3(H2), s3(sd(H2, 1)), s3(sd(H2, fac_old)), s3(sd(H2, fac_M)), s3(cap_b), s3(sd(H2, fac_M) / cap_b), s3(Lm2)],
       ["n = 1, W = 100 tf", s3(H1), s3(sd(H1, 1)), s3(sd(H1, fac_old)), s3(sd(H1, fac_M)), s3(cap_b), s3(sd(H1, fac_M) / cap_b), s3(Lm1)]])
print(f"Brazo del momento: el núcleo (e + L/2) es el correcto. La reacción lineal rígida es σ(z) = R/(D·L) + 12·M_c·z/(D·L³), con M_c el momento respecto del CENTRO del asiento = R·(e_piv + L/2) (e_piv se mide desde la cara superior de la base: el buje arranca a t_base + 2 mm y mide 80 mm). "
      f"Mi 1 + 6e/L tomaba el momento respecto de la cara superior y subestimaba el factor ({fac_old:.1f} frente a {fac_M:.1f}, −{(1 - fac_old / fac_M) * 100:.0f} %). El signo de σ cambia a lo largo de la profundidad (arriba y abajo del asiento empujan en lados opuestos), así que no hay tracción en un mismo punto.")
finding("P4", "menor", "RESULTADO DE DISEÑO (el núcleo ya lo informa): con n = 1 y t_base = %s mm el agujero de la base no cumple a ninguna W (wPiv = wCap = 0); exige t_base ≥ %s mm a W = 100 tf" % (s3(P["t_base"]), s3(t_req[100])),
        f"wPiv(n=1) = {s3(D0['capCil'][0]['wPiv'])} tf", f"t_base ≥ {s3(t_req[100])} mm (W = 100) / {s3(t_req[165])} mm (W = 165)")
finding("P6", "importante", "ABIERTO por decisión de diseño (el núcleo lo marca «pendiente»): el asiento del pivote Ø%s en una base de %s mm no resiste el momento M = H·e. Con la fórmula del núcleo σ = H/(D·L)(1 + 6(e + L/2)/L) = ×%.1f la presión es %s MPa frente a %s MPa admisible (FU %.1f); profundidad mínima de asiento %s mm (n = 2). "
        "Corrijo mi propia fórmula: el brazo correcto es e + L/2, no e (×%.1f, no ×%.1f)" % (s3(P["D_piv"]), s3(P["t_base"]), fac_M, s3(sd(H2, fac_M)), s3(cap_b), sd(H2, fac_M) / cap_b, s3(Lm2), fac_M, fac_old),
        f"n = 2: FU {sd(H2, fac_M) / cap_b:.1f} (pendiente, sin FU en la tabla de estado)", f"collar o cubo soldado, brida o pivote pasante con tuerca; L ≥ {s3(Lm2)} mm si solo trabaja por contacto. n = 1: FU {sd(H1, fac_M) / cap_b:.1f}, L ≥ {s3(Lm1)} mm")
D40 = export({"t_vuelta_obj": 40})
comp("4", "Con t_obj = 40 min incumplido: wPiv(n=2) ya NO se anula (P5)", W_piv_core(P, 2), D40["capCil"][1]["wPiv"])
comp("4", "Con t_obj = 40 min incumplido: wCap(n=2) = wGiro", W_cap_core_like(P, 2), D40["capCil"][1]["wCap"])

# ======================================================================================
# 5. MERCADO: μ implícito y coherencia de datos
# ======================================================================================
mk = D0["mercado"]
ours = mk["ours"]
comp("5", "TT300-C: kg/kN", D0["derivados"]["masas"]["total"] / (P["W_tf"] * g0), ours["massPerKN"])
comp("5", "TT300-C: kN de cilindro por tf", n0 * Fst_kN(P) / P["W_tf"], ours["FcylPerTon"])
comp("5", "TT300-C: μ implícito = n·F·a/(N·r_u)", n0 * Fst_kN(P) * ours["arm"] / ((P["W_tf"] * g0) * ours["ru"]), ours["muImpl"])
comp("5", "TT300-C: brazo = R cos(π/N) (m)", P["R_pin"] * math.cos(math.pi / P["N_pin"]) / 1e3, ours["arm"])
comp("5", "TT300-C: F_cil = F_calado (kN)", Fst_kN(P), ours["Fcyl"])
comp("5", "TT300-C: giro por carrera 360/N (°)", 360 / P["N_pin"], ours["rot"])
comp("5", "TT300-C: r_u (m)", casos(P)["nom"][1] / 1e3, ours["ru"])
comp("5", "TT300-C: altura h (mm) sin cubierta", H_total(P), ours["h"])
oursW = DW["mercado"]["ours"]
comp("5", "TT300-C con cubierta: altura h (mm)", H_total(PWc), oursW["h"])
comp("5", "TT300-C con cubierta: kg/kN", DW["derivados"]["masas"]["total"] / (PWc["W_tf"] * g0), oursW["massPerKN"])
comp("5", "TT300-C con cubierta: Δ masa total (kg)", DW["derivados"]["masas"]["total"] - D0["derivados"]["masas"]["total"], m_wood(PWc))
rows = []
for rf in mk["refs"]:
    if rf["capKN"] is None:
        continue
    mpk = rf["mass"] / rf["capKN"]; fpt = rf["nCyl"] * rf["Fcyl"] / (rf["capKN"] / g0); mui = rf["nCyl"] * rf["Fcyl"] * rf["arm"] / (rf["capKN"] * rf["ru"])
    comp("5", f"{rf['id']}: kg/kN", mpk, rf["massPerKN"]); comp("5", f"{rf['id']}: kN de cilindro por tf", fpt, rf["FcylPerTon"])
    comp("5", f"{rf['id']}: μ implícito", mui, rf["muImpl"])
    ru_teo = 2 / 3 * (rf["D"] / 2) / 1e3 if rf["id"] != "kiet" else 2 / 3 * (rf["D"] / 2) / 1e3
    s_util = 2 * rf["arm"] * 1e3 * math.sin(math.radians(rf["rot"]) / 2)
    rows.append([rf["name"], s3(mpk), s3(fpt), s3(mui), s3(rf["ru"]), s3(ru_teo), f"{(rf['ru'] / ru_teo - 1) * 100:+.2f} %",
                 s3(360 / rf["rot"]), s3(s_util), s3(rf["arm"] * 1e3 / (rf["D"] / 2))])
table("Prueba 5a – Referencias: aritmética y coherencia geométrica", ["Equipo", "kg/kN", "kN cil/tf", "μ impl.", "r_u dato (m)", "2/3·D/2 (m)", "Δ r_u", "N pasadores = 360/giro", "carrera útil 2a·sin(giro/2) (mm)", "brazo/(D/2)"], rows)
ett = [r for r in mk["refs"] if r["id"] == "ett200"][0]; ett4 = [r for r in mk["refs"] if r["id"] == "ett400"][0]; kiet = [r for r in mk["refs"] if r["id"] == "kiet"][0]
R_stroke250 = 250 / (2 * math.sin(math.radians(ett["rot"]) / 2))
mu_arm = lambda arm: ett["nCyl"] * ett["Fcyl"] * arm / (ett["capKN"] * ett["ru"])
mu_k500 = kiet["nCyl"] * kiet["Fcyl"] * kiet["arm"] / (500 * g0 * kiet["ru"])
mu_k = kiet["nCyl"] * kiet["Fcyl"] * kiet["arm"] / (kiet["capKN"] * (2 / 3 * kiet["D"] / 2 / 1e3))
mu_e200_t = ett["nCyl"] * ett["Fcyl"] * ett["arm"] / (200 * g0 * ett["ru"])
m_tab = D0["derivados"]["masas"]["disc"] / (P["W_tf"] * g0)
rows = [["ETT: carrera útil con brazo 0,895 m y 12,5°", s3(2 * ett["arm"] * 1e3 * math.sin(math.radians(ett["rot"]) / 2)) + " mm", "una carrera de ≈ 250 mm incluye ≈ %s mm (%.0f %%) de recorrido no útil (toma/retorno)" % (s3(250 - 2 * ett["arm"] * 1e3 * math.sin(math.radians(ett["rot"]) / 2)), (250 / (2 * ett["arm"] * 1e3 * math.sin(math.radians(ett["rot"]) / 2)) - 1) * 100)],
        ["ETT: radio de pasadores que daría 250 mm útiles a 12,5°", s3(R_stroke250) + " mm", f"> D/2 = {s3(ett['D'] / 2)} mm: imposible; la carrera de 250 mm NO puede ser toda útil"],
        ["ETT: 360°/12,5° (n.º de pasadores)", s3(360 / ett["rot"]), "no entero: 12,5° es nominal/redondeado, no el paso real"],
        ["ETT: brazo 0,895 = D/2 (brazo máximo posible)", s3(ett["arm"]), f"μ implícito = {mu_arm(ett['arm']):.3f}; con brazo −10 % ⇒ {mu_arm(ett['arm'] * 0.9):.3f}; cota superior de μ"],
        ["ETT200 y ETT400: misma masa (±1,5 %), mismo Ø, cap. ×2", s3(ett4["mass"] / ett["mass"]), f"mismo μ implícito {ett['muImpl']:.4f}: la capacidad ∝ n.º de cilindros ⇒ kg/kN no mide eficiencia estructural"],
        ["ETT 2.000 kN vs 200 tf·g", s3(200 * g0), f"μ implícito con 200 tf = {mu_e200_t:.4f} ({(mu_e200_t / ett['muImpl'] - 1) * 100:+.1f} %); kN/tf con 200 tf: {ett['nCyl'] * ett['Fcyl'] / 200:.4f}"],
        ["KIET: r_u dato 0,67 vs 2/3·D/2", s3(kiet["ru"]), f"μ implícito con 0,6667 = {mu_k:.4f} ({(mu_k / kiet['muImpl'] - 1) * 100:+.2f} %)"],
        ["KIET: capacidad 500 t (manual) en vez de 400 t", s3(500 * g0), f"μ implícito = {mu_k500:.4f} ({(mu_k500 / kiet['muImpl'] - 1) * 100:+.1f} %)"],
        ["KIET: R_pasadores = brazo/cos(π/28)", s3(kiet["arm"] / math.cos(math.pi / 28)) + " m", f"carrera útil {s3(2 * kiet['arm'] / math.cos(math.pi / 28) * 1e3 * math.sin(math.pi / 28))} mm (TT300-C: {s3(2 * P['R_pin'] * math.sin(math.pi / P['N_pin']))} mm)"],
        ["Masa comparable: TT300-C solo mesa (disco) kg/kN", s3(m_tab), f"vs total {s3(ours['massPerKN'])}: la masa «ours» incluye base, ménsulas, patines y cilindros; no se sabe si las referencias incluyen base"]]
table("Prueba 5b – Coherencia de datos de referencia (revisión crítica)", ["Verificación", "Valor", "Conclusión"], rows)
rot_ok = abs(360 / ett["rot"] - round(360 / ett["rot"])) < 1e-6
if not rot_ok:
    finding("K1", "menor", "ETT: 12,5°/carrera no corresponde a un n.º entero de pasadores (28,8) y el brazo 0,895 m es D/2 (brazo máximo): μ implícito del ETT (0,167) es una cota superior; "
            "la carrera de ≈ 250 mm solo es coherente si ≈ 55 mm (28 %) son recorrido no útil",
            f"μ impl. ETT = {ett['muImpl']:.4f}", f"≤ {ett['muImpl']:.3f}; con brazo −10 %: {mu_arm(ett['arm'] * 0.9):.3f}")
finding("K2", "menor", "Masa: «ours» (3.285 kg) incluye base, ménsulas, patines, bancadas y cilindros; con solo mesa y pasadores es %s kg/kN, comparable con KIET (0,55) y ETT (0,43–0,85). Comparar kg/kN sin igualar el alcance sobreestima el peso propio ×2" % s3(m_tab),
        f"{s3(ours['massPerKN'])} kg/kN", f"{s3(m_tab)} kg/kN (solo mesa)")
finding("K3", "menor", "Unidades de capacidad: ETT 2.000/4.000 kN se tratan como capacidad exacta (≈ 203,9/407,9 tf); si la capacidad nominal es 200/400 tf (1.961/3.923 kN) el μ implícito sube %+.1f %% y kN cil/tf %+.1f %%; KIET declara 400 t en el plano y 500 t en el manual (μ implícito %.3f con 500 t)" % ((mu_e200_t / ett["muImpl"] - 1) * 100, (200 / (ett["capKN"] / g0) - 1) * 100 * -1, mu_k500),
        f"μ impl. ETT {ett['muImpl']:.4f}, KIET {kiet['muImpl']:.4f}", f"ETT {mu_e200_t:.4f} (200 tf), KIET {mu_k500:.4f} (500 t)")
finding("K4", "menor", "r_u de las referencias está redondeado (KIET 0,67 vs 2/3·D/2 = 0,6667: %+.2f %% en μ implícito); μ implícito de «ours» usa F_calado y brazo mínimo (conservador), el de las referencias el brazo declarado (0,869 m, definición no indicada)" % ((mu_k / kiet["muImpl"] - 1) * 100),
        f"KIET {kiet['muImpl']:.4f}", f"{mu_k:.4f}")

# ======================================================================================
# 6. BARRIDOS
# ======================================================================================
SWEEPS = [
    ("Q_pump", [0.5, 1, 1.8, 3, 5, 10, 20, 30], {}),
    ("Q_ret", [0, 1, 1.8, 3, 5, 10, 20, 40, 60, 99, 100], {}),
    ("n_cyl", [1, 2, 3, 4], {}),
    ("W_tf", [50, 100, 116, 150, 200, 250, 300, 330, 332, 334, 350, 400], {}),
    ("t_wood", [20, 29, 30, 50, 100, 150], {"opt_wood": 1}),
    ("rho_wood", [600, 800, 900, 1000, 1200], {"opt_wood": 1}),
    ("p_wood", [1, 2, 2.8, 2.82, 4, 6, 10], {"opt_wood": 1}),
    ("D_load", [800, 1000, 1200, 1600, 2000], {"opt_wood": 1}),
    ("e", [0, 50, 100, 150, 200, 250, 300], {"opt_wood": 1}),
    ("t_vuelta_obj", [30, 60, 70, 71, 100], {}),
    ("h_skid", [230, 270, 280, 285, 300], {"opt_wood": 1}),
    ("W_tf", [60, 100, 116, 117, 120], {"n_cyl": 1}),
    ("f_apoyo", [0.2, 0.3, 0.4, 0.47, 0.48, 0.5, 0.6, 0.8, 1.0], {"opt_wood": 1}),
    ("t_base", [16, 20, 24, 28, 30, 32], {"n_cyl": 1, "W_tf": 100}),
    ("t_base", [16, 20, 24], {}),
    ("p_alarm", [600, 500, 450, 400], {}),
    ("mu_cont", [0.25, 0.3, 0.35, 0.4], {}),
    ("p_bush", [10, 14, 20, 30], {}),
    ("p_bush", [10, 14, 20, 30], {"n_cyl": 1, "W_tf": 100}),
    ("mu_bush", [0.1, 0.2, 0.4], {"n_cyl": 1, "W_tf": 100}),
    ("e", [0, 100, 150, 250, 300], {"n_cyl": 1, "W_tf": 100}),
]
ALL = []
for key, vals, base in SWEEPS:
    ds = sweep_points(key, vals, base)
    nm = key + (f" ({', '.join(f'{k}={v}' for k, v in base.items())})" if base else "")
    S = Sweep(nm)
    for v, D in zip(vals, ds):
        eval_point(S, v, dict(base, **{key: v}), D)
    ALL.append(S)
rows = []
for S in ALL:
    flips = []
    for k, lst in S.verd.items():
        lst = sorted(lst, key=lambda t: t[0])
        for (v1, o1), (v2, o2) in zip(lst, lst[1:]):
            if o1 != o2:
                flips.append(f"{k}: {'ok' if o1 else 'falla'}→{'ok' if o2 else 'falla'} entre {v1} y {v2}")
    rows.append([S.name, f"{S.vals[0]}…{S.vals[-1]} ({len(S.vals)} pts)" if S.vals else "—", S.n, f"{S.maxd:.4f}", len(S.dis) + len(S.vm), "; ".join(flips) if flips else "sin cambios"])
table("Prueba 6 – Barridos (núcleo vs. modelo propio, todas las magnitudes nuevas y los veredictos)",
      ["Barrido", "Rango", "N.º de comparaciones", "máx. |Δ| %", "discrepancias", "Cambios de veredicto"], rows)
for S in ALL:
    for d in S.dis[:8]:
        print(f"  DISCREPANCIA {S.name}: {d[0]} propio {s3(d[1])} núcleo {s3(d[2])}")
    for d in S.vm[:8]:
        print(f"  VEREDICTO DISTINTO {S.name}: valor {d[0]} {d[1]} propio {'ok' if d[2] else 'falla'}, núcleo {'ok' if d[3] else 'falla'}")
    if S.rej:
        print(f"  (rechazados por validación en {S.name}: {S.rej})")
nsw = sum(S.n for S in ALL); ndis = sum(len(S.dis) + len(S.vm) for S in ALL)
# Veredicto combinado de la madera (q ≤ p_wood Y 4e/R ≤ 1) frente a la ley sin tracción (propia)
mal = []
for dl in (800, 1000, 1200, 1600, 2000):
    for ee in (0, 50, 100, 150, 200, 250, 300):
        if ee >= dl / 2:
            continue
        PPt = dict(PWc, D_load=dl, e=ee)
        nucleo_ok = q_wood_core(PPt) <= PWc["p_wood"] and 4 * ee / (dl / 2) <= 1
        propio_ok = q_wood_nt(PL, dl / 2, ee) * (dl / 2) ** 2 / ((dl / 2) ** 2 - hueco ** 2) / PWc["f_apoyo"] <= PWc["p_wood"]
        if nucleo_ok and not propio_ok:
            mal.append((dl, ee))
print(f"\nPrueba 6b – Malla D_carga × e (35 combinaciones): combinaciones aceptadas por el núcleo (q y 4e/R ≤ 1) pero rechazadas sin tracción y con el agujero: {mal if mal else 'ninguna'}")
if ndis:
    finding("S1", "crítica", f"{ndis} discrepancias entre el núcleo y la réplica propia en los barridos", "—", "ver detalle de barridos")

# ======================================================================================
# Resumen
# ======================================================================================
table("Comparación con el núcleo en la línea base (tolerancia 0,1 % salvo indicación)", ["Prueba", "Magnitud", "Propio", "Núcleo", "Δ %", "Veredicto"], COMP)
FIND2 = [f for f in FIND if f]
table("Hallazgos", ["Id", "Severidad", "Hallazgo", "Núcleo", "Corregido"], FIND2)
nco = sum(1 for c in COMP if c[5] == "coincide"); ndi = sum(1 for c in COMP if c[5] == "discrepa"); nom = sum(1 for c in COMP if c[5] == "el núcleo omite")
if ndi:
    for c in COMP:
        if c[5] == "discrepa":
            finding("D" + c[0], "crítica" if abs(float(c[4])) > 1 else "importante", f"Discrepancia numérica en línea base: {c[1]}", c[3], c[2])
sev = {k: sum(1 for f in FIND if f and f[1] == k) for k in ("crítica", "importante", "menor")}
print(f"\nRESULTADO: {nco} coincidencias en línea base, {ndi} discrepancias; {nsw} comparaciones en {len(ALL)} barridos, {ndis} discrepancias; "
      f"hallazgos: {sev['crítica']} críticos, {sev['importante']} importantes, {sev['menor']} menores")
sys.exit(1 if sev["crítica"] or sev["importante"] else 0)
