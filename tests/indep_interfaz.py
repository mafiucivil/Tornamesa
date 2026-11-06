"""Revisión independiente de la INTERFAZ DE GIRO TT300-C: opción 0 (acero-acero con grasa), A (dos discos de acero
inoxidable con grasa), B (dos discos inoxidables con lámina UHMW-PE entre ellos) y C (placa de bronce con tapones de grafito
sobre disco duro; bz_conf 1, 2 = dos bronces, 3 = pastillas).

Regla de independencia: no lee packages/*.js. Los resultados del núcleo se obtienen solo por su salida JSON
(node tools/export_design.js [params.json]); todo lo demás se deriva aquí desde la mecánica de placas
(Timoshenko y Woinowsky-Krieger), la estática del accionamiento (modelo ya verificado en tests/indep_accionamiento.py),
la elasticidad de láminas confinadas (Lindley / Gent), placas perforadas (Lamé / Peterson), una plancha de Mindlin MITC4 para el
izaje y AISC 360-22 (ASD, Fy/1,67 = 0,6 Fy).

Ejecutar:  python3 -I tests/indep_interfaz.py
Imprime tablas y termina con «RESULTADO: ...». Sale con 0 si no hay hallazgos críticos ni importantes; con 1 si los hay;
con 2 si no puede ejecutar el núcleo.

Unidades internas: N, mm, MPa (salvo donde se indique kN, kN·m).
"""
import json, math, pathlib, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

try:
    import numpy as np
except Exception:          # el modelo de contacto unilateral es opcional
    np = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
g0, RHO = 9.80665, 7.85e-6
RHO_SS, RHO_UH = 7.93e-6, 0.94e-6                  # kg/mm³
AL_UH, AL_S, AL_SS, E_SS = 180e-6, 11.7e-6, 17.3e-6, 193000.0
COM_SS = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
COM_UH = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50]
TOL = 1e-3


def export(over=None):
    with tempfile.TemporaryDirectory() as td:
        args = ["node", str(ROOT / "tools" / "export_design.js")]
        if over:
            f = pathlib.Path(td) / "p.json"; f.write_text(json.dumps(over)); args.append(str(f))
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


_EXP = {}


def export_c(over):
    k = json.dumps(over, sort_keys=True)
    if k not in _EXP:
        _EXP[k] = export(over)
    return _EXP[k]


def prefetch(lst):
    todo = [o for o in lst if json.dumps(o, sort_keys=True) not in _EXP]
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(export, todo))
    for o, r in zip(todo, res):
        _EXP[json.dumps(o, sort_keys=True)] = r



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
    if core is None or mine is None:
        COMP.append((prueba, name, s3(mine), s3(core), "—", "coincide" if core is None and mine is None else "discrepa")); return
    d = (mine - core) / core * 100 if core else (0.0 if abs(mine) < 1e-12 else 100.0)
    COMP.append((prueba, name, s3(mine), s3(core), f"{d:+.3f}", "coincide" if abs(d) <= tol * 100 else "discrepa"))


def com(t, lst):
    """espesor comercial inmediato (≥ t)"""
    if t is None or not math.isfinite(t):
        return math.inf
    for c in lst:
        if c >= t - 1e-9:
            return float(c)
    return math.inf


# ======================================================================================
# 0. Datos
# ======================================================================================
D0 = export()
if D0 is None:
    print("No se pudo ejecutar node tools/export_design.js"); sys.exit(2)
P = D0["P"]
DA, DB = export({"opt_ss": 1}), export({"opt_uhmw": 1})
Pg = json.loads((ROOT / "tests" / "golden" / "params_defaults.json").read_text())
nuevos = sorted(k for k in P if k not in Pg)


def mesa(P):
    """masa de la mesa (kg) sin el pivote, y densidad lineal del pivote (kg/mm)"""
    rings = sorted(float(x) for x in P["rings"].replace(";", ",").split(",") if x.strip())
    Rt = P["D_top"] / 2; hw = P["h_disc"] - P["t_top"] - P["t_bot"]
    rpr = max(P["D_hub"] / 2, P["R_pin"] - (Rt - P["R_pin"])); db = P["D_piv"] + 30
    aring = math.pi * (Rt ** 2 - rpr ** 2) - P["N_pin"] * math.pi * P["d_pin"] ** 2 / 4
    m = RHO * ((math.pi * rpr ** 2 - math.pi / 4 * (P["D_piv"] + 80) ** 2) * P["t_top"] + aring * max(P["t_pr"], P["t_top"]))
    m += RHO * ((math.pi * rpr ** 2 - math.pi / 4 * db ** 2) * P["t_bot"] + aring * max(P["t_pr"], P["t_bot"]))
    m += RHO * sum(2 * math.pi * r * hw * P["t_web"] for r in rings)
    nin = sum(1 for r in rings if P["D_hub"] / 2 < r < P["R_rib"])
    m += RHO * P["N_rib"] * (P["R_rib"] - P["D_hub"] / 2 - nin * P["t_web"]) * hw * P["t_rib"]
    m += RHO * math.pi / 4 * (P["D_hub"] ** 2 - db ** 2) * hw
    m += RHO * P["N_pin"] * math.pi / 4 * P["d_pin"] ** 2 * P["h_disc"]
    return m, RHO * math.pi / 4 * P["D_piv"] ** 2


def geom(P):
    Ro, Ri = P["D_top"] / 2, P["D_piv"] / 2 + 15
    A = math.pi * (Ro ** 2 - Ri ** 2); I = math.pi * (Ro ** 4 - Ri ** 4) / 4
    ru = 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2)
    return Ro, Ri, A, I, ru


nu_uh = 0.45


def Mcon(E, nu_u=nu_uh):
    """módulo de deformación plana unidimensional (confinamiento total): E(1−ν)/((1+ν)(1−2ν))"""
    return E * (1 - nu_u) / ((1 + nu_u) * (1 - 2 * nu_u))


def Ec(t, Dc, E, mode="coord", nu_u=nu_uh):
    """módulo efectivo de la lámina; S = D_carga/(4t).
    'coord': E[1 + (M/E − 1)·S²/(1 + S²)]  (modelo adoptado en el núcleo; E en S→0, M en S→∞)
    'inc'  : E + 1/[1/(2S²E) + 1/(M−E)]    (variante propia: E(1+2S²) de Lindley acotada por M)
    'gent' : 1/E_c = 1/[E(1+2S²)] + 1/K, K = E/(3(1−2ν))   (Gent 1994)
    'uni'  : E (módulo uniaxial, modelo anterior)"""
    S = Dc / (4 * t)
    if mode == "uni":
        return E, S
    if mode == "gent":
        K = E / (3 * (1 - 2 * nu_u)); return 1 / (1 / (E * (1 + 2 * S * S)) + 1 / K), S
    M = Mcon(E, nu_u)
    if mode == "inc":
        return E + 1 / (1 / (2 * S * S * E) + 1 / (M - E)), S
    return E * (1 + (M / E - 1) * S * S / (1 + S * S)), S


def t_conf_S(q, Dc, E, d, p=None, mode="coord", nu_u=nu_uh):
    """t = E_c(S(t))·d/(p_adm − q) resuelto por bisección (el lado derecho decrece con t)"""
    p = P["p_uhmw"] if p is None else p
    if not (p > q):
        return math.inf
    lo, hi = 1e-3, 1e4
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if Ec(mid, Dc, E, mode, nu_u)[0] * d / (p - q) > mid:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def iface(P, k):
    """Opción k ∈ {0,1,2}. Devuelve espesores, q_máx (con el peso del disco rotatorio, iterado), N, masa agregada.
    Con ranuras de engrase (A con h_gr > 0), el disco de la mesa es el ranurado: t_req2 = t_flex + sobreespesor + h_gr; el de la base queda liso.
    B es simétrico y sin ranuras. t_ss > 0 fija ambos discos."""
    Ro, Ri, A, I, ru = geom(P)
    m_mesa, rho_piv = mesa(P)
    W = P["W_tf"] * g0
    a = P["ss_void"] / 2
    sad = 0.6 * P["Fy_ss"]
    gr = P["h_gr"] if k == 1 else 0.0
    t_d = com(P["ss_tmin"], COM_SS) if k else 0.0
    t_d2 = t_d
    t_u = com(P["uh_tmin"], COM_UH) if k == 2 else 0.0
    out = None
    for _ in range(60):
        Delta = t_d + t_d2 + t_u if k else 0.0
        m_rot = RHO_SS * A * t_d2 if k else 0.0
        m_piv = rho_piv * (P["t_base"] + P["h_disc"] - P["t_top"] + 3 + Delta)
        Wd = (m_mesa + 0.5 * m_piv + m_rot) * g0 / 1e3
        N = W + Wd; ND = P["phi_d"] * W + Wd
        q = ND * 1e3 / A + ND * 1e3 * P["e"] * Ro / I
        tfl = a * math.sqrt(0.75 * q / sad)
        treq = max(tfl + P["ss_allow"], P["ss_tmin"])
        treq2 = max(tfl + P["ss_allow"] + gr, P["ss_tmin"])
        t_d_new = (P["t_ss"] if P["t_ss"] > 0 else com(treq, COM_SS)) if k else 0.0
        t_d2_new = (P["t_ss"] if P["t_ss"] > 0 else com(treq2, COM_SS)) if k else 0.0
        tconf = t_conf_S(q, P["ss_void"], P["E_uhmw"], P["d_flat"], p=P["p_uhmw"]) if k == 2 else None
        tuhreq = max(tconf, P["uh_tmin"]) if k == 2 else 0.0
        t_u_new = (P["t_uhmw"] if P["t_uhmw"] > 0 else com(tuhreq, COM_UH)) if k == 2 else 0.0
        out = dict(k=k, q=q, tflex=tfl if k else None, tssReq=treq if k else 0.0, tss2Req=treq2 if k else 0.0, tss=t_d, tss2=t_d2, tconf=tconf, tuhReq=tuhreq, tuh=t_u,
                   delta=Delta, mTop=m_rot, mUH=RHO_UH * A * t_u, N=N, ND=ND, Wd=Wd, m_piv=m_piv, gr=gr)
        if t_d_new == t_d and t_d2_new == t_d2 and t_u_new == t_u:
            break
        t_d, t_d2, t_u = t_d_new, t_d2_new, t_u_new
    out["mAdd"] = RHO_SS * A * (out["tss"] + out["tss2"]) + out["mUH"] if k else 0.0
    return out


# ---------------- accionamiento (modelo verificado en tests/indep_accionamiento.py) ----------------
R_, Np, r_p, n = P["R_pin"], int(P["N_pin"]), P["d_pin"] / 2, P["n_cyl"]
ph = math.pi / Np
x_g, eta, mu_g, mu_s = P["x_g"], P["eta_c"], P["mu_g"], P["mu_s"]
front, rear = P["l_p"] + 20 + P["f_ext"], 1.25 * P["d_pp"]
L_s = front + rear; Lg = 2 / 3 * L_s
y_r = (front - rear) / 2 - Lg / 2
y_c = P["l_p"] - r_p
A_b = math.pi / 4 * P["D_bore"] ** 2; A_ann = A_b - math.pi / 4 * P["d_rod"] ** 2
F_st = A_b * P["p_relief"] / 10                                  # N


def Fh_unit(P):
    """F_cil [N] por 1 N·mm de par por cilindro (máx. en la carrera; lineal en T)."""
    def est(th, sg=None):
        a_, yp = R_ * math.cos(th), R_ * math.sin(th)
        if sg is None:
            sg = 1 if yp > r_p else -1
        hh = sg * mu_s
        F = 1.0 / (a_ - hh * (yp - r_p)); H = hh * F
        Rf = (F * (x_g - a_) + H * (y_c - y_r)) / Lg; Rr = H - Rf
        return (F + mu_g * (abs(Rf) + abs(Rr))) / eta
    th0 = math.asin(r_p / R_)
    c = [est(-ph + 2 * ph * i / 4000) for i in range(4001)] + [est(th0, 1), est(th0, -1)]
    return max(c)


FU_ = Fh_unit(P)                                                   # N/(N·mm)
Ro, Ri, Ac, Ix, ru = geom(P)


def par(P, N_kN, mu, r):
    """T [N·mm] = μ·N·r + μ_buje·H_exc·D_piv/2; H_exc = μ·N·e·(4/3)(Ro³−Ri³)/(Ro⁴−Ri⁴)"""
    Nn = N_kN * 1e3
    H = mu * Nn * P["e"] * 4 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4)
    return mu * Nn * r + P["mu_bush"] * H * P["D_piv"] / 2


def mus(P, k):
    if k == 0:
        return dict(nom=P["mu_nom"], dis=P["mu_d"], borde=P["mu_d"], cont=P["mu_cont"], seco=P["mu_dry"])
    s = "muA_" if k == 1 else "muB_"
    return dict(nom=P[s + "nom"], dis=P[s + "d"], borde=P[s + "d"], cont=P[s + "cont"], seco=P[s + "dry"])


def casos(P, k, N_kN):
    m = mus(P, k)
    rr = dict(nom=ru, dis=P["r_ef"], borde=Ro, cont=P["r_ef"], seco=ru)
    out = {}
    for c in m:
        T = par(P, N_kN, m[c], rr[c])
        F = FU_ * T / n / 1e3                                        # kN
        out[c] = dict(mu=m[c], r=rr[c], T=T / 1e6, F=F, p=F * 1e3 / A_b * 10, FS=F_st / 1e3 / F)
    return out


Tmax = F_st * n / FU_ / 1e6                                         # kN·m: par que vencen los cilindros al alivio (F_cil = F_calado)
IF = [iface(P, k) for k in (0, 1, 2)]
ifc_core = D0["escenarios"]["ifaces"]

print("# Revisión independiente de la interfaz de giro TT300-C: opciones 0 / A / B / C")
dif = sorted(k for k in set(P) | set(Pg) if P.get(k) != Pg.get(k))
print(f"Parámetros exportados = golden: {'sí' if not dif else 'NO, difieren ' + str(dif)}")
print(f"R_o = {s3(Ro)}, R_i = {s3(Ri)}, A = {s3(Ac)} mm², r_u = {s3(ru)} mm, a = ss_void/2 = {s3(P['ss_void']/2)} mm, "
      f"σ_adm,inox = 0,6·Fy_ss = {s3(0.6*P['Fy_ss'])} MPa, F_calado = {s3(F_st/1e3)} kN, T_max (alivio) = {s3(Tmax)} kN·m")

# ======================================================================================
# 1. Espesores, q_máx, masa agregada: interfazChecks y escenarios.ifaces
# ======================================================================================
tCyc = n * (A_b + A_ann) * P["stroke"] * 1e-6 / P["Q_pump"]          # min por pasada (V_ext + V_ret)/Q
v_avg = Ro / 1000 * (2 * math.pi / P["N_pin"]) / (tCyc * 60)          # m/s, promedio del ciclo completo (modelo anterior)
a_min = R_ * math.cos(ph)
v_cil = P["Q_pump"] * 1e6 / 60 / (n * A_b)                              # mm/s, velocidad del vástago con los n cilindros en paralelo
v_edge = Ro * v_cil / a_min / 1000                                      # m/s, pico en el borde (ω = v_cil/a_mín)


def cap_ret(N_kN):
    """capacidad de retención de los discos [kN·m]: máx(fricción μ_resp·N·r_u; adhesivo τ·A_c·r_u) (A_c en mm², r_u en mm); no se suman"""
    return max(P["mu_back"] * N_kN * ru / 1e3, P.get("tau_bond", 0.0) * Ac * ru / 1e6)


def tau_th(t_disco):
    """cortante térmico en el borde del pegado: ε·√(G_ad·E_inox·t_disco/t_ad), ε = (α_inox − α_acero)·ΔT"""
    if not P.get("G_ad") or not P.get("t_ad"):
        return None
    return (AL_SS - AL_S) * P["dT"] * math.sqrt(P["G_ad"] * E_SS * t_disco / P["t_ad"])


# ---------------- fijación desmontable por sectores con topes (fix_mode = 1) y ranuras de engrase ----------------
def q_ratio(PP):
    """q_máx/q_med = 1 + e·R_o·A/I (la razón no depende de las cargas)"""
    Ro_, Ri_, A_, I_, ru_ = geom(PP)
    return 1 + PP["e"] * Ro_ * A_ / I_


def F_tope(PP, n_):
    """fuerza por tope [N] = (T_calado/r_u)/n·(q_máx/q_med)"""
    Ro_, Ri_, A_, I_, ru_ = geom(PP)
    return (Tmax * 1e3 / (ru_ / 1e3)) / n_ * q_ratio(PP)


def tope_calc(PP, F, t, Fy):
    """L = máx(L_aplastamiento; L_soldadura)/0,9 redondeado a múltiplos de 5 mm; L_tope > 0 lo fija"""
    adm = 1.25 * Fy / PP["Nd"]; Fw = 0.6 * PP["FEXX"] / (1.2 * PP["Nd"])
    Lap = F / (adm * t); Lsol = F / (2 * 0.707 * PP["w_tope"] * Fw)
    L = PP["L_tope"] if PP["L_tope"] > 0 else math.ceil(max(Lap, Lsol) / 0.9 / 5 - 1e-9) * 5
    return dict(L=L, adm=adm, Fw=Fw, sig=F / (L * t), fw=F / (2 * 0.707 * PP["w_tope"] * L), Lap=Lap, Lsol=Lsol, F=F)


def chord_of(PP, n_):
    return 2 * PP["D_top"] / 2 * math.sin(math.pi / n_)


def groove_area(PP):
    """área de las ranuras de engrase [mm²]: w·(n_rad·(R_o − R_i) + n_circ·2π·r_m)"""
    Ro_, Ri_ = geom(PP)[:2]
    return PP["w_gr"] * (PP["n_gr_rad"] * (Ro_ - Ri_) + PP["n_gr_circ"] * 2 * math.pi * (Ro_ + Ri_) / 2)


def vedge_of(PP):
    a_m = PP["R_pin"] * math.cos(math.pi / PP["N_pin"])
    return geom(PP)[0] * (PP["Q_pump"] * 1e6 / 60 / (PP["n_cyl"] * math.pi / 4 * PP["D_bore"] ** 2)) / a_m / 1000


def piece_rows(PP, R, label, n_, unit, t, Fy, allow, gr_x=0.0):
    """filas de tope (aplastamiento, largo, soldadura) y cabeza del tornillo de una pieza en sectores"""
    Ro_, Ri_ = geom(PP)[:2]; F = F_tope(PP, n_); c = tope_calc(PP, F, t, Fy); Lmax = Ro_ - Ri_ - 100
    head = f"{label} ({n_} {unit})"
    R[f"{head}: aplastamiento del tope"] = (c["sig"], c["adm"], c["sig"] / c["adm"])
    R[f"{head}: largo del tope"] = (c["L"], Lmax, c["L"] / Lmax)
    R[f"{head}: soldadura del tope"] = (c["fw"], c["Fw"], c["fw"] / c["Fw"])
    hs = 0.55 * PP["d_tor"] + 2; hc = t - allow - gr_x
    R[f"{label}: cabeza del tornillo avellanado"] = (hs, hc, hs / hc if hc > 0 else math.inf)
    return c


def grease_rows(PP, R, where):
    if PP["h_gr"] > 0:
        Ac_ = geom(PP)[2]; Ag = groove_area(PP)
        R[f"Engrase: área de las ranuras frente al área de contacto ({where})"] = (Ag / Ac_, 0.25, Ag / Ac_ / 0.25)
        R["Engrase: volumen de grasa"] = (Ag * PP["h_gr"] / 1000, PP["n_greaser"], None)


def rowsAB(PP, k):
    """Valores propios de cada fila de interfazChecks.A (k = 1) y .B (k = 2): clave (subcadena del nombre) → (dem, cap, fu). Con fix_mode 1 (sectores con topes) o 2 (pegado)."""
    r = iface(PP, k); q = r["q"]; a = PP["ss_void"] / 2; sad = 0.6 * PP["Fy_ss"]; Ro_, Ri_, A_, I_, ru_ = geom(PP)
    fu = lambda d, c: (d / c if c and c > 0 else math.inf)
    t1, t2, gr = r["tss"], r["tss2"], r["gr"]
    sig = lambda t_, ex: 3 * q * a ** 2 / (4 * (t_ - PP["ss_allow"] - ex) ** 2) if t_ - PP["ss_allow"] - ex > 0 else math.inf
    R = {}
    s1 = sig(t1, 0.0)
    R["Disco de la base (liso): flexión sobre un vacío local"] = (s1, sad, s1 / sad)
    R["Disco de la base (liso): espesor adoptado"] = (r["tssReq"], t1, r["tssReq"] / t1)
    if gr > 0:
        s2 = sig(t2, gr)
        R["Disco de la mesa (con ranuras de engrase): flexión sobre un vacío local"] = (s2, sad, s2 / sad)
        R["Disco de la mesa (con ranuras de engrase): espesor adoptado"] = (r["tss2Req"], t2, r["tss2Req"] / t2)
    R["Disco inoxidable: espesor mínimo por flexión"] = (r["tflex"], None, None)
    R["Disco inoxidable: espesor requerido / comercial adoptado"] = (r["tssReq"], t1, None)
    R["Altura que agrega"] = (r["delta"], None, None)
    R["Masa agregada"] = (r["mAdd"], None, None)
    R["Dilatación diferencial radial del disco"] = ((AL_SS - AL_S) * PP["dT"] * Ro_, None, None)
    if k == 1:
        R["Opción A: par inox–inox"] = (0.0, None, None)
    grease_rows(PP, R, "disco de la mesa")
    if PP["fix_mode"] == 1:
        ns = PP["n_sec"]
        piece_rows(PP, R, "Disco de la base (liso)", ns, "sectores", t1, PP["Fy_ss"], PP["ss_allow"])
        if gr > 0:
            piece_rows(PP, R, "Disco de la mesa (con ranuras de engrase)", ns, "sectores", t2, PP["Fy_ss"], PP["ss_allow"])
        R["Sectores de disco: crecimiento por dilatación de la cuerda"] = ((AL_SS - AL_S) * PP["dT"] * chord_of(PP, ns), None, None)
        mm = RHO_SS * A_ * max(t1, t2) / ns
        R["Disco inoxidable: masa del sector"] = (mm, 25.0, mm / 25.0)
        R["Soldar los topes antes del alivio"] = (0.0, None, None)
    else:
        Nn = r["N"]; cap = max(PP["mu_back"] * Nn * ru_ / 1e3, PP["tau_bond"] * A_ * ru_ / 1e6)
        R["Retención de los discos sobre su plancha de respaldo"] = (Tmax, cap, Tmax / cap)
        tau = (AL_SS - AL_S) * PP["dT"] * math.sqrt(PP["G_ad"] * E_SS * max(t1, t2) / PP["t_ad"])
        R["Adhesivo: cortante térmico en el borde del disco"] = (tau, PP["tau_cyc"], tau / PP["tau_cyc"])
        ds = E_SS * (AL_SS - AL_S) * PP["dT"]
        R["Dilatación diferencial inox–acero: tensión si el disco quedara restringido"] = (ds, sad, ds / sad)
        R["Fijación permanente (pegado)"] = (0.0, None, None)
    if k == 2:
        sl = PP["life"] * PP["turns_yr"] * 2 * math.pi * PP["r_ef"] / 1000
        h = PP["k_wear"] * 1e-7 * q * sl; ve = vedge_of(PP); tu = r["tuh"]
        R["Lámina UHMW: presión de contacto máxima frente a la admisible"] = (q, PP["p_uhmw"], q / PP["p_uhmw"])
        R["Lámina UHMW: espesor adoptado"] = (r["tuhReq"], tu, r["tuhReq"] / tu)
        R["Lámina UHMW: espesor por conformidad"] = (r["tconf"], tu, None)
        R["Lámina UHMW: factor de forma y módulo confinado"] = (Ec(tu, PP["ss_void"], PP["E_uhmw"])[1], Ec(tu, PP["ss_void"], PP["E_uhmw"])[0], None)
        R["Lámina UHMW: valor PV"] = (q * ve, PP["PV_uh"], q * ve / PP["PV_uh"])
        R["Lámina UHMW: desgaste en la vida"] = (h, 0.2 * tu, h / (0.2 * tu))
        R["Lámina UHMW: crecimiento radial del sector"] = ((AL_UH - AL_S) * PP["dT"] * Ro_, None, None)
        R["Lámina UHMW: junta de dilatación entre sectores"] = ((AL_UH - AL_S) * PP["dT"] * chord_of(PP, PP["n_seg"]), None, None)
        mum = max(PP["muB_d"], PP["muB_cont"], PP["muB_dry"])
        if PP["fix_mode"] == 1:
            Fs = mum * r["N"] * 1e3 / PP["n_seg"] * q_ratio(PP); Lc = Ro_ - Ri_ - 100
            R[f"Lámina UHMW ({PP['n_seg']} sectores): aplastamiento del canto contra el tope del rebaje"] = (Fs / (Lc * tu), PP["p_uhmw"], Fs / (Lc * tu) / PP["p_uhmw"])
            fw_ = Fs / (2 * 0.707 * PP["w_tope"] * Lc); Fw_ = 0.6 * PP["FEXX"] / (1.2 * PP["Nd"])
            R["Tope del rebaje del sector UHMW: soldadura"] = (fw_, Fw_, fw_ / Fw_)
            mu_ = RHO_UH * A_ * tu / PP["n_seg"]
            R["Lámina UHMW: masa del sector"] = (mu_, 25.0, mu_ / 25.0)
        else:
            R["Opción B: retención de los sectores de UHMW"] = (mum * r["N"], None, None)
    return R, r


def est_mine(fu):
    return "info" if fu is None else ("ok" if fu <= 1 + 1e-9 else "fail")


def expected_rows(P, k):
    return rowsAB(P, k)[0]


tabla1 = []
for k, DD, lab in ((1, DA, "A"), (2, DB, "B")):
    exp = expected_rows(P, k)
    for row in DD["interfazChecks"]["A" if k == 1 else "B"]:
        key = next((kk for kk in exp if kk in row["nombre"]), None)
        if key is None:
            COMP.append(("1" + lab, f"{lab} · {row['nombre'][:70]} [fila sin cálculo propio]", "—", "—", "—", "discrepa"))
            tabla1.append([lab, row["nombre"][:58], "—", "—", "—", "DISCREPA: sin fórmula propia"]); continue
        dem, cap, fu = exp[key]
        worst = 0.0; bad = False
        for nm, mine, core in (("dem", dem, row["dem"]), ("cap", cap, row.get("cap")), ("FU", fu, row.get("fu"))):
            if core is None and mine is None:
                continue
            comp("1" + lab, f"{lab} · {row['nombre'][:60]} [{nm}]", mine, core)
            if core is None or mine is None:
                bad = True
            elif core:
                dd = abs((mine - core) / core)
                worst = max(worst, dd * 100); bad = bad or dd > TOL
            elif abs(mine) > 1e-12:
                bad = True
        if row["estado"] in ("ok", "fail") and est_mine(fu) != row["estado"]:
            bad = True
        tabla1.append([lab, row["nombre"][:58], f"{s3(dem)} / {s3(cap)} / {s3(fu)}",
                       f"{s3(row['dem'])} / {s3(row.get('cap'))} / {s3(row.get('fu'))}", f"{worst:.4f}", ("DISCREPA" if bad else ("pend. (núcleo)" if row["estado"] == "pend" else "coincide")) + f" [{row['estado']}]"])
table("1a. interfazChecks A y B: dem / cap / FU (propio frente a núcleo; Δ máx en %)", ["Op.", "Fila", "Propio dem / cap / FU", "Núcleo dem / cap / FU", "Δ %", "Veredicto"], tabla1)

tabla2 = []
for k in (0, 1, 2):
    c = ifc_core[k]; r = IF[k]
    for nm, mine, core in (("q_máx (MPa)", r["q"], c["q"]), ("t_flex (mm)", r["tflex"], c.get("tFlex")), ("t_req disco (mm)", r["tssReq"] or None, c.get("tssReq") or None),
                           ("t_disco adoptado (mm)", r["tss"] or None, c["tss"] or None), ("t_req disco mesa (mm)", r["tss2Req"] or None, c.get("tss2Req") or None), ("t_disco mesa adoptado (mm)", r["tss2"] or None, c.get("tss2") or None), ("t_conf UHMW (mm)", r["tconf"], c.get("tuhConf") or None),
                           ("t_UHMW adoptado (mm)", r["tuh"] or None, c["tuh"] or None), ("Δ altura (mm)", r["delta"] or None, c["delta"] or None),
                           ("masa agregada (kg)", r["mAdd"] or None, c["mAdd"] or None)):
        if mine is None and core is None:
            continue
        comp("1i", f"op. {k} · {nm}", mine, core)
        d = (mine - core) / core * 100 if (mine is not None and core) else float("nan")
        tabla2.append([k, nm, s3(mine), s3(core), f"{d:+.4f}", "coincide" if abs(d) <= TOL * 100 else "DISCREPA"])
table("1b. escenarios.ifaces (espesores, q_máx, masa agregada)", ["Op.", "Magnitud", "Propio", "Núcleo", "Δ %", "Veredicto"], tabla2)

def soldadura_mejilla(Delta):
    aw = 0.707 * P["w_br"]; hax = P["h_disc"] / 2 + Delta
    return math.hypot(F_st / (4 * aw * P["L_ch"]), F_st * hax / (4 * aw * P["L_ch"] ** 2 / 6))


# ---------------- barridos ----------------
SW = [("ss_void", [60, 80, 100, 120, 140, 160, 180, 200], "mm"), ("Fy_ss", [170, 185, 205, 225, 250], "MPa"),
      ("E_uhmw", [200, 250, 300, 400, 500], "MPa"), ("d_flat", [0.05, 0.1, 0.15, 0.2, 0.3], "mm"), ("W_tf", [200, 240, 280, 300, 320, 360], "tf"),
      ("n_sec", [12, 18, 24, 36, 48], "sectores"), ("n_seg", [12, 16, 24, 48], "sectores UHMW"), ("w_tope", [3, 4, 6, 8, 12, 16], "mm"), ("d_tor", [4, 6, 8, 10, 12], "mm"),
      ("h_gr", [0, 0.5, 1, 2, 3, 5], "mm"), ("L_tope", [0, 100, 200, 400], "mm"), ("fix_mode", [1, 2], "")]
sw_bad = 0; sw_n = 0
SW_BADLIST = []


def row_diffs(core_rows, R, tag):
    """compara todas las filas del núcleo con las propias (dem, cap, FU, estado); las filas sin cálculo propio cuentan como discrepancia"""
    global sw_n
    bad = []
    for row in core_rows:
        key = next((kk for kk in R if kk in row["nombre"]), None)
        sw_n += 1
        if key is None:
            bad.append(f"{tag}:fila sin cálculo propio «{row['nombre'][:40]}»"); continue
        dem, cap, fu = R[key]
        for nm, mv, cv in (("dem", dem, row["dem"]), ("cap", cap, row.get("cap")), ("fu", fu, row.get("fu"))):
            if cv is None and (mv is None or not math.isfinite(mv)):
                continue
            sw_n += 1
            if cv is None or mv is None or not math.isfinite(mv) or (abs(mv - cv) > TOL * abs(cv) if cv else abs(mv) > 1e-9):
                bad.append(f"{tag}:{key[:30]}.{nm}")
        sw_n += 1
        if row["estado"] in ("ok", "fail") and est_mine(fu) != row["estado"]:
            bad.append(f"{tag}:{key[:30]}.estado")
    return bad


def cmp_sweep(over):
    """compara propio y núcleo para P+over (campos de ifaces y todas las filas de interfazChecks A y B); devuelve (DD, ra, rb, ok, malos)"""
    global sw_n, sw_bad
    DD = export_c(over)
    PP = dict(P); PP.update(over)
    ra, rb = iface(PP, 1), iface(PP, 2)
    if DD is None:
        return None, ra, rb, False, []
    ca, cb = DD["escenarios"]["ifaces"][1], DD["escenarios"]["ifaces"][2]
    bad = []
    for lab, r, c, keys in (("A", ra, ca, (("q", "q"), ("tFlex", "tflex"), ("tssReq", "tssReq"), ("tss", "tss"), ("tss2Req", "tss2Req"), ("tss2", "tss2"), ("mAdd", "mAdd"), ("delta", "delta"))),
                            ("B", rb, cb, (("q", "q"), ("tuhConf", "tconf"), ("tuhReq", "tuhReq"), ("tuh", "tuh"), ("tss2", "tss2"), ("mAdd", "mAdd"), ("delta", "delta")))):
        for kc, km in keys:
            sw_n += 1
            cv, mv = c.get(kc), r[km]
            if cv is None and (mv is None or not math.isfinite(mv)):
                continue
            if cv is None or mv is None or (not math.isfinite(mv)) or (abs(mv - cv) > TOL * abs(cv) if cv else abs(mv) > 1e-9):
                bad.append(f"{lab}.{kc}")
    # F y FS de diseño de B y A
    for lab, r, c, N_ in (("A", ra, ca, ra["N"]), ("B", rb, cb, rb["N"])):
        cs = casos(PP, 1 if lab == "A" else 2, N_)["dis"]
        for kc, mv in (("F", cs["F"]), ("FS", cs["FS"])):
            sw_n += 1
            if abs(mv - c[kc]) > TOL * abs(c[kc]):
                bad.append(f"{lab}.{kc}")
    for k_, tag in ((1, "A"), (2, "B")):
        bad += row_diffs(DD["interfazChecks"][tag], rowsAB(PP, k_)[0], tag)
    sw_bad += len(bad)
    if bad:
        SW_BADLIST.append((over, bad))
    return DD, ra, rb, not bad, bad


prefetch([{k_: v_} for k_, vals_, u_ in SW for v_ in vals_])
for key, vals, u in SW:
    rows = []
    for v in vals:
        res = cmp_sweep({key: v})
        if res[0] is None:
            rows.append([s3(v), "rechazado por el núcleo", "", "", "", "", "", "", "", ""]); continue
        DD, ra, rb, ok, bad = res
        ca, cb = DD["escenarios"]["ifaces"][1], DD["escenarios"]["ifaces"][2]
        rows.append([s3(v), s3(ra["q"]), f"{s3(ra['tflex'])} / {s3(ca['tFlex'])}", f"{s3(ra['tss'])}+{s3(ra['tss2'])} / {s3(ca['tss'])}+{s3(ca.get('tss2'))}",
                     f"{s3(rb['tconf'])} / {s3(cb['tuhConf'])}", f"{s3(rb['tuh'])} / {s3(cb['tuh'])}", f"{s3(rb['mAdd'])} / {s3(cb['mAdd'])}",
                     f"{s3(casos(dict(P, **{key: v}), 2, rb['N'])['dis']['FS'])} / {s3(cb['FS'])}", s3(soldadura_mejilla(rb['delta']) / (0.6 * P['FEXX'] / (1.2 * P['Nd']))) if math.isfinite(rb['delta']) else "—", "coincide" if ok else "DISCREPA " + ",".join(bad)])
    table(f"1c. Barrido de {key} ({u}); cada celda «propio / núcleo»", [key, "q_máx", "t_flex", "t_disco", "t_conf", "t_UHMW", "mAdd B kg", "FS dis. B", "FU sold. mejillas B", "Veredicto"], rows)
print(f"\nBarridos: {sw_n} comparaciones, {sw_bad} discrepancias (tolerancia 0,1 %)")

# ---------------- umbrales de espesor comercial ----------------


def _fails(R):
    return tuple(sorted(kk[:28] for kk, (d_, c_, f_) in R.items() if f_ is not None and f_ > 1 + 1e-9))


def thick_pair(PP):
    ra_, rb_ = iface(PP, 1), iface(PP, 2)
    return (ra_["tss"], ra_["tss2"], rb_["tuh"], _fails(rowsAB(PP, 1)[0]), _fails(rowsAB(PP, 2)[0]))


def core_pair(DD, PP):
    if DD is None:
        return None
    out = []
    for k_, tag in ((1, "A"), (2, "B")):
        R_ = rowsAB(PP, k_)[0]; fs_ = []
        for row in DD["interfazChecks"][tag]:
            kk = next((x for x in R_ if x in row["nombre"]), None)
            if kk and row.get("fu") is not None and row["fu"] > 1 + 1e-9:
                fs_.append(kk[:28])
        out.append(tuple(sorted(fs_)))
    ic = DD["escenarios"]["ifaces"]
    return (ic[1]["tss"], ic[1]["tss2"], ic[2]["tuh"], out[0], out[1])


def umbrales(key, lo, hi, npts=600):
    xs = [lo + (hi - lo) * i / npts for i in range(npts + 1)]
    out = []
    prev = thick_pair(dict(P, **{key: xs[0]}))
    for i in range(1, len(xs)):
        cur = thick_pair(dict(P, **{key: xs[i]}))
        if cur != prev:
            a_, b_ = xs[i - 1], xs[i]
            for _ in range(60):
                mid = (a_ + b_) / 2
                if thick_pair(dict(P, **{key: mid})) == prev:
                    a_ = mid
                else:
                    b_ = mid
            out.append((b_, prev, cur))
            prev = cur
    return out


def fmt_pair(t):
    return f"{s3(t[0])}+{s3(t[1])} / {s3(t[2])}" + (" ✗A:" + ",".join(x[:14] for x in t[3]) if t[3] else "") + (" ✗B:" + ",".join(x[:14] for x in t[4]) if t[4] else "")


UMB_AB = (("ss_void", 60, 200), ("Fy_ss", 170, 250), ("E_uhmw", 200, 500), ("d_flat", 0.05, 0.3), ("W_tf", 200, 360), ("h_gr", 0, 5), ("w_tope", 3, 16))
UMA = [(key, v, p0, p1) for key, lo, hi in UMB_AB for v, p0, p1 in umbrales(key, lo, hi)]
prefetch([{key: v * fac} for key, v, p0, p1 in UMA for fac in (1 - 2e-4, 1 + 2e-4)])
rows = []
for key, v, p0, p1 in UMA:
    res = [core_pair(export_c({key: v * fac}), dict(P, **{key: v * fac})) for fac in (1 - 2e-4, 1 + 2e-4)]
    ok = res[0] == p0 and res[1] == p1
    comp("1u", f"umbral {key} = {s3(v)}", 1.0 if ok else 0.0, 1.0)
    rows.append([key, s3(v), fmt_pair(p0), fmt_pair(p1), "coincide" if ok else "DISCREPA núcleo: " + (fmt_pair(res[0]) if res[0] else "—") + " | " + (fmt_pair(res[1]) if res[1] else "—")])
DD = export({"p_uhmw": 1.5}); PPd = dict(P, p_uhmw=1.5); rb_ = iface(PPd, 2)
cb_ = DD["escenarios"]["ifaces"][2] if DD else {}
ok_deg = DD is not None and cb_.get("tuh") is None and not math.isfinite(rb_["tuh"]) and cb_.get("tuhConf") is None
comp("1u", "p_uhmw = 1,5 MPa ≤ q_máx: B inviable (sin espesor)", 1.0 if ok_deg else 0.0, 1.0)
rows.append(["p_uhmw", "1.50 (≤ q_máx)", "—", "B inviable", "t_UHMW = " + str(cb_.get("tuh")) + ", FS = " + str(cb_.get("FS")) + (": coincide" if ok_deg else ": DISCREPA")])
table("1d. Umbrales donde cambian los espesores comerciales (t_disco base + t_disco mesa / t_UHMW en mm) o el cumplimiento de A y B: propio y verificación en el núcleo a ±0,02 %",
      ["Parámetro", "Valor umbral", "Debajo (propio)", "Encima (propio)", "Núcleo (±0,02 %)"], rows)

# ======================================================================================
# 2. F por cilindro, p y FS de las tres opciones
# ======================================================================================
rows = []
for k, DD, lab in ((0, D0, "0"), (1, DA, "A"), (2, DB, "B")):
    cs = casos(P, k, IF[k]["N"])
    cc = {c["id"]: c for c in DD["derivados"]["casos"]}
    for cid, c in cs.items():
        core = cc[cid]
        comp("2", f"op. {lab} · caso {cid}: F (kN)", c["F"], core["F"]); comp("2", f"op. {lab} · caso {cid}: p (bar)", c["p"], core["p"])
        comp("2", f"op. {lab} · caso {cid}: FS", c["FS"], core["FS"]); comp("2", f"op. {lab} · caso {cid}: T (kN·m)", c["T"], core["T"])
        d = (c["F"] - core["F"]) / core["F"] * 100
        rows.append([lab, cid, s3(c["mu"]), s3(c["r"]), s3(c["T"]), s3(c["F"]), s3(core["F"]), s3(c["p"]), s3(core["p"]), s3(c["FS"]), s3(core["FS"]),
                     f"{d:+.4f}", "gira" if c["F"] <= F_st / 1e3 else "NO gira", "coincide" if abs(d) <= TOL * 100 else "DISCREPA"])
    ci = ifc_core[k]
    comp("2", f"op. {lab} · ifaces F de diseño", cs["dis"]["F"], ci["F"]); comp("2", f"op. {lab} · ifaces p de diseño", cs["dis"]["p"], ci["p"])
    comp("2", f"op. {lab} · ifaces FS de diseño", cs["dis"]["FS"], ci["FS"])
    Tu = par(P, IF[k]["N"], 1.0, P["r_ef"]) / n
    mumax = F_st / (FU_ * Tu)
    comp("2", f"op. {lab} · μ máx que gira (r_ef)", mumax, ci["muMax"])
table("2. Casos de giro por opción (F por cilindro en kN, p en bar; T en kN·m)", ["Op.", "Caso", "μ", "r mm", "T", "F propio", "F núcleo", "p propio", "p núcleo", "FS propio", "FS núcleo", "Δ F %", "Gira", "Veredicto"], rows)
Tmax_core = D0["apoyo"]["Tmax"]
comp("2", "T_max al alivio (kN·m)", Tmax, Tmax_core)

# --- altura nueva del eje: efectos fuera del plano (retención T, ménsulas, soldadura de mejillas)
hd2 = P["h_disc"] / 2
z_t = P["t_base"] + P["t_bed"] - P["h_slot"] / 2
Fpc = eta * F_st


def guia_cal(th):
    a_, yp = R_ * math.cos(th), R_ * math.sin(th)
    Hh = (1 if yp > r_p else -1) * mu_s * Fpc
    Rf = (Fpc * (x_g - a_) + Hh * (y_c - y_r)) / Lg
    return Hh, Rf, Hh - Rf


GC = [guia_cal(-ph + 2 * ph * i / 4000) for i in range(4001)]
SRcal = max(abs(x[1]) + abs(x[2]) for x in GC); Hcal = mu_s * Fpc
ala = (P["w_tee"] - P["w_slot"]) / 2


def retencionT(Delta):
    dz = P["t_base"] + hd2 + Delta - z_t
    V = Hcal * dz / ((P["w_bed"] + P["w_tee"]) / 2) + mu_g * SRcal * dz / L_s
    return V / (ala * L_s)


def vv(DD, sub):
    return next(v for v in DD["verificaciones"] if sub in v["nombre"])


rows = []
for lab, DD, k in (("0", D0, 0), ("A", DA, 1), ("B", DB, 2)):
    Dl = IF[k]["delta"]
    for nm, sub, mine in (("Retención T: aplastamiento del ala", "aplastamiento en la cabeza T", retencionT(Dl)),
                          ("Soldadura mejillas–base", "Soldadura mejillas–base (4", soldadura_mejilla(Dl)),
                          ("Mejilla: flexión en la base (∝ h_eje)", "Mejilla de la ménsula", vv(D0, "Mejilla de la ménsula")["dem"] * (hd2 + Dl) / hd2)):
        core = vv(DD, sub)
        comp("2z", f"op. {lab} · {nm}", mine, core["dem"])
        d = (mine - core["dem"]) / core["dem"] * 100
        rows.append([lab, f"h_eje = {s3(hd2 + Dl)}", nm, s3(mine), s3(core["dem"]), s3(core["fu"]), f"{d:+.4f}", "coincide" if abs(d) <= TOL * 100 else "DISCREPA"])
table("2z. Altura nueva del eje de los cilindros h_eje = h_disc/2 + Δ: efectos fuera del plano", ["Op.", "h_eje", "Chequeo", "Propio MPa", "Núcleo MPa", "FU núcleo", "Δ %", "Veredicto"], rows)

# ======================================================================================
# 3. HIPÓTESIS FÍSICAS
# ======================================================================================
q = IF[1]["q"]; a = P["ss_void"] / 2; sad = 0.6 * P["Fy_ss"]; nu = 0.3
teff = IF[1]["tss"] - P["ss_allow"]
# ---- (a) placa sobre un vacío local
sig_cl = 3 * q * a ** 2 / (4 * teff ** 2)
sig_ss = 3 * (3 + nu) / 8 * q * a ** 2 / teff ** 2
tfl_cl = a * math.sqrt(0.75 * q / sad); tfl_ss = a * math.sqrt(3 * (3 + nu) / 8 * q / sad)
D_pl = E_SS * teff ** 3 / (12 * (1 - nu ** 2))
wc_cl = q * a ** 4 / (64 * D_pl)
sig_fd = None; wc_fd = None
if np is not None:
    def plate(a, t, q, dv=None, E=E_SS, nu=0.3, h=0.5):
        """Placa axisimétrica de Kirchhoff, empotrada lejos, sobre fundación rígida unilateral con un vacío r<a (profundidad dv o pasante)."""
        Dp = E * t ** 3 / (12 * (1 - nu ** 2)); Lout = a + 12 * t + 100
        N_ = int(round(Lout / h)); r = np.arange(N_ + 1) * h
        L = np.zeros((N_ + 1, N_ + 1)); L[0, 0] = -4 / h ** 2; L[0, 1] = 4 / h ** 2
        for i in range(1, N_):
            L[i, i - 1] = 1 / h ** 2 - 1 / (2 * h * r[i]); L[i, i] = -2 / h ** 2; L[i, i + 1] = 1 / h ** 2 + 1 / (2 * h * r[i])
        L[N_, N_ - 1] = 2 / h ** 2; L[N_, N_] = -2 / h ** 2
        LL = L[:N_, :] @ L[:, :N_]
        kp = 1e1 * Dp / h ** 4
        w = np.zeros(N_); inside = r[:N_] < a
        floor = np.zeros(N_) if dv is None else np.where(inside, dv, 0.0)
        for _ in range(300):
            act = ((~inside) & (w > 0)) if dv is None else (w > floor)
            wn = np.linalg.solve(Dp * LL + np.diag(np.where(act, kp, 0.0)), q * np.ones(N_) + np.where(act, kp * floor, 0.0))
            if np.max(np.abs(wn - w)) < 1e-10:
                w = wn; break
            w = wn
        wf = np.append(w, 0.0); wp = np.gradient(wf, h); wpp = np.zeros_like(wf)
        wpp[1:-1] = (wf[2:] - 2 * wf[1:-1] + wf[:-2]) / h ** 2; wpp[0] = 2 * (wf[1] - wf[0]) / h ** 2; wpp[-1] = 2 * (wf[-2] - wf[-1]) / h ** 2
        rr = np.maximum(r, 1e-9); fr = np.where(r > 0, wp / rr, wpp)
        Mr = -Dp * (wpp + nu * fr); Mt = -Dp * (fr + nu * wpp)
        return r, wf, 6 * np.maximum(np.abs(Mr), np.abs(Mt)) / t ** 2
    r_, w_, s_ = plate(a, teff, q)
    sig_fd, wc_fd = float(s_.max()), float(w_[0])
    # validación del operador contra la solución cerrada (placa empotrada en r = a)
rows = [["Empotrada (modelo del núcleo)", s3(sig_cl), s3(sig_cl / sad), s3(tfl_cl + P["ss_allow"]), s3(com(tfl_cl + P["ss_allow"], COM_SS))],
        ["Simplemente apoyada, ν = 0,3 (3(3+ν)/8·q a²/t² = 1,24·q a²/t²)", s3(sig_ss), s3(sig_ss / sad), s3(tfl_ss + P["ss_allow"]), s3(com(tfl_ss + P["ss_allow"], COM_SS))]]
if sig_fd is not None:
    tfd = tfl_cl * math.sqrt(sig_fd / sig_cl) + P["ss_allow"]
    rows.append(["Disco continuo sobre fundación unilateral con vacío pasante (diferencias finitas)", s3(sig_fd), s3(sig_fd / sad), s3(tfd), s3(com(tfd, COM_SS))])
table(f"3a. Placa circular de radio a = {s3(a)} mm, t_ef = {s3(teff)} mm, q = {s3(q)} MPa, σ_adm = {s3(sad)} MPa", ["Modelo de borde", "σ máx MPa", "FU", "t_req mm", "comercial mm"], rows)
if sig_fd is not None:
    print(f"Razón σ_unilateral/σ_empotrada = {sig_fd/sig_cl:.3f}; razón σ_apoyada/σ_empotrada = {sig_ss/sig_cl:.3f}")
    # profundidad crítica del vacío
    rows = []
    for dv in (0.01, 0.03, 0.05, 0.075, 0.10, 0.30):
        _, _, sd = plate(a, teff, q, dv=dv)
        sdelta = 4 * E_SS * teff * dv / ((1 - nu ** 2) * a ** 2)
        rows.append([s3(dv), s3(float(sd.max())), s3(min(sdelta, sig_cl)), s3(sig_fd), "gobierna el contacto de fondo" if float(sd.max()) < 0.995 * sig_fd else "gobierna la carga uniforme"])
    table("3a'. Vacío de profundidad δ_v: tensión del disco (MPa); cerrada σ_δ = 4·E·t·δ_v/((1−ν²)a²) acotada por la empotrada",
          ["δ_v mm", "σ diferencias finitas", "σ_δ cerrada (acotada)", "σ uniforme (vacío pasante)", "Gobierna"], rows)
    print(f"δ_crit (el disco deja de tocar el fondo): empotrada {s3(wc_cl)} mm = q a⁴/(64 D); modelo unilateral {s3(wc_fd)} mm")
c_ov = teff * math.sqrt(sad / (3 * q))
print(f"Voladizo en el borde del disco (sin respaldo en una franja c): σ = 3 q c²/t² → c_máx = {s3(c_ov)} mm con t_ef = {s3(teff)} mm")

# ---- (b) conformidad de la lámina UHMW con módulo confinado (modelo nuevo del núcleo)
qB = IF[2]["q"]; tconf0 = IF[2]["tconf"]; tuh0 = IF[2]["tuh"]
M_c = Mcon(P["E_uhmw"])
tcore_conf = ifc_core[2]["tuhConf"]
rows = []
for Dc, d in ((50, 0.05), (100, 0.05), (100, 0.075), (100, 0.10), (200, 0.05), (200, 0.10)):
    for E in (P["E_uhmw"], 700.0):
        tt = {m: t_conf_S(qB, Dc, E, d, mode=m) for m in ("coord", "inc", "gent", "uni")}
        Ee, S = Ec(tt["coord"], Dc, E)
        rows.append([s3(Dc), s3(d), s3(E), s3(S), s3(Ee / E), s3(tt["coord"]), s3(com(max(tt["coord"], P["uh_tmin"]), COM_UH)), s3(tt["inc"]), s3(tt["gent"]), s3(tt["uni"])])
table(f"3b. t_conf [mm] con el módulo confinado (ν_UHMW = {nu_uh}, q = {s3(qB)} MPa, p_adm = {s3(P['p_uhmw'])}): modelo del núcleo («coord») frente a mis variantes",
      ["D_carga mm", "d mm", "E MPa", "S", "E_c/E", "t_conf coord", "comercial", "t_conf «E→M»", "t_conf Gent", "t_conf uniaxial"], rows)
t_tuh = IF[2]["tuh"]
print(f"M (deformación plana) = {s3(M_c)} MPa ({s3(M_c/P['E_uhmw'])}×E). En el espesor adoptado t = {s3(t_tuh)} mm (S = {s3(P['ss_void']/(4*t_tuh))}): "
      f"E_c coord = {s3(Ec(t_tuh, P['ss_void'], P['E_uhmw'])[0])}, «E→M» = {s3(Ec(t_tuh, P['ss_void'], P['E_uhmw'], 'inc')[0])}, Gent = {s3(Ec(t_tuh, P['ss_void'], P['E_uhmw'], 'gent')[0])} MPa")
t_g = t_conf_S(qB, P["ss_void"], P["E_uhmw"], P["d_flat"], mode="gent"); t_i = t_conf_S(qB, P["ss_void"], P["E_uhmw"], P["d_flat"], mode="inc")
print(f"t_conf: núcleo {s3(tcore_conf)}; propio con el modelo del núcleo {s3(tconf0)}; «E→M» {s3(t_i)}; Gent {s3(t_g)}; uniaxial {s3(t_conf_S(qB, P['ss_void'], P['E_uhmw'], P['d_flat'], mode='uni'))} mm")
# d_flat máximo que mantiene el comercial adoptado y que mantiene la soldadura de mejillas
def d_max_for(tcom, mode="coord"):
    lo, hi = 1e-4, 2.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if t_conf_S(qB, P["ss_void"], P["E_uhmw"], mid, mode=mode) <= tcom else (lo, mid)
    return lo
cap_w = 0.6 * P["FEXX"] / (1.2 * P["Nd"])
lo_, hi_ = 0.0, 200.0
for _ in range(60):
    mid = (lo_ + hi_) / 2
    lo_, hi_ = (mid, hi_) if soldadura_mejilla(mid) <= cap_w else (lo_, mid)
Dmax_w = lo_
t_uh_wmax = Dmax_w - 2 * IF[2]["tss"]
d_adm_w = d_max_for(max(c for c in COM_UH if c <= t_uh_wmax))
print(f"Soldadura de mejillas B: Δ = {s3(IF[2]['delta'])} mm → FU {s3(soldadura_mejilla(IF[2]['delta'])/cap_w)} (núcleo {s3(vv(DB,'Soldadura mejillas–base (4')['fu'])}); Δ_máx (FU = 1) = {s3(Dmax_w)} mm "
      f"→ t_UHMW comercial ≤ {s3(max(c for c in COM_UH if c <= t_uh_wmax))} mm → d_flat ≤ {s3(d_adm_w)} mm (con D = ss_void); d_flat que mantiene {s3(tuh0)} mm: {s3(d_max_for(tuh0))} mm")
rows = []
for dd in (0.05, 0.06, 0.075, 0.10, 0.15):
    tc_ = t_conf_S(qB, P["ss_void"], P["E_uhmw"], dd); tcm = com(max(tc_, P["uh_tmin"]), COM_UH)
    Dl = 2 * IF[2]["tss"] + tcm
    rows.append([s3(dd), s3(tc_), s3(tcm), s3(Dl), s3(soldadura_mejilla(Dl) / cap_w), "no cumple" if soldadura_mejilla(Dl) > cap_w else "ok"])
table("3b'. Sensibilidad a d_flat (D = ss_void): t_UHMW y soldadura de mejillas en cascada", ["d_flat mm", "t_conf mm", "t_UHMW mm", "Δ mm", "FU soldadura mejillas", "veredicto"], rows)

# ---- (c) valores de partida y fluencia
v_ext = v_avg * tCyc * 60 / (n * A_b * P["stroke"] * 1e-6 / P["Q_pump"] * 60)     # promedio solo en carrera (informativo)
sl = P["life"] * P["turns_yr"] * 2 * math.pi * P["r_ef"] / 1000
h_w = P["k_wear"] * 1e-7 * qB * sl
mu_max_B = ifc_core[2]["muMax"]
rows = [["p_uhmw (sostenida)", s3(P["p_uhmw"]) + " MPa", "5–7 MPa (cargas estáticas continuas)", f"q_máx/p = {s3(qB/P['p_uhmw'])}", "razonable; límite de deformación"],
        ["E_uhmw", s3(P["E_uhmw"]) + " MPa", "600–800 MPa corto plazo; 100–200 MPa tras 1 año", "300 es intermedio", "el defecto del disco rotatorio ve el módulo de corto plazo (≈ 60–100 s por pasada): E = 700 daría t_conf = " + s3(t_conf_S(qB, P['ss_void'], 700.0, P['d_flat'])) + " mm"],
        ["k_wear", s3(P["k_wear"]) + "e-7 mm³/N·m", "1e-7–1e-6 (limpio); 1e-5 con arena", f"h = {s3(h_w)} mm", f"con k×100 → {s3(h_w*100)} mm ≪ 0,2 t = {s3(0.2*tuh0)} mm"],
        ["PV_uh", s3(P["PV_uh"]) + " MPa·m/s", "0,05–0,10 (seco, UHMW-PE)", f"PV pico = q·R_o·v_cil/a_mín = {s3(qB*v_edge)} (v = {s3(v_edge*1e3)} mm/s; promedio en carrera {s3(qB*v_ext)})", f"FU {s3(qB*v_edge/P['PV_uh'])}; no gobierna"],
        ["μ B (nom / dis / cont / seco)", f"{P['muB_nom']} / {P['muB_d']} / {P['muB_cont']} / {P['muB_dry']}", "UHMW sobre inox: 0,05–0,10 con grasa; 0,10–0,22 seco; estático hasta 0,25", f"μ_máx que gira {s3(mu_max_B)}: margen de {s3((mu_max_B/P['muB_cont']-1)*100)} % sobre μ_cont", "monótono (cont = seco); consistente con la literatura; arena incrustada podría pasar de 0,25"],
        ["μ A (nom / dis / cont / seco)", f"{P['muA_nom']} / {P['muA_d']} / {P['muA_cont']} / {P['muA_dry']}", "inox–inox con grasa 0,10–0,20; seco 0,5–1 (gripado)", "monótono", "razonable"]]
table("3c. Valores de partida frente a la literatura de UHMW-PE (órdenes de magnitud de fichas técnicas; confirmar con el proveedor)",
      ["Parámetro", "Núcleo", "Rango de literatura", "Resultado propio", "Comentario"], rows)
rows = []
tU = tuh0
qmin = D0["apoyo"]["q_min"]
for lab, Ecr in (("1 mes", 160.0), ("1 año", 120.0), ("25 años", 80.0)):
    s_max = qB / Ecr * tU; s_min = qmin / Ecr * tU
    rows.append([lab, s3(Ecr), s3(s_max), s3(s_max - s_min), s3((s_max - s_min) / (2 * Ro) * 1e3)])
table(f"3c'. Fluencia de la lámina (uniaxial, cota superior; E_fluencia supuesto de isócronas típicas), t = {s3(tU)} mm, q_máx = {s3(qB)}, q_mín = {s3(qmin)} MPa",
      ["Tiempo", "E_fl MPa", "asentamiento en el borde mm", "diferencial q_máx−q_mín mm", "inclinación mm/m"], rows)

# ---- (e) retención de los discos: fricción + adhesivo
rows = []
tau = P.get("tau_bond", 0.0)
cap_ad = tau * Ac * ru / 1e6
for k, lab in ((1, "A"), (2, "B")):
    N_ = IF[k]["N"]; cap_fr = P["mu_back"] * N_ * ru / 1e3; cs = casos(P, k, N_)
    for cid in ("dis", "borde", "cont", "seco"):
        c = cs[cid]
        T_int = c["mu"] * N_ * c["r"] / 1e3
        T_real = min(T_int, Tmax)
        rows.append([lab, cid, s3(c["mu"]), s3(T_real), s3(T_real / cap_fr), s3(T_real / cap_ad), s3(T_real / max(cap_fr, cap_ad))])
    rows.append([lab, "T_calado", "—", s3(Tmax), s3(Tmax / cap_fr), s3(Tmax / cap_ad), s3(Tmax / max(cap_fr, cap_ad))])
table(f"3e. (solo fix_mode = 2, pegado) Retención de los discos: capacidad por fricción {s3(P['mu_back']*IF[1]['N']*ru/1e3)} kN·m (μ_resp = {P['mu_back']}), por adhesivo {s3(cap_ad)} kN·m (τ = {s3(tau)} MPa), máx {s3(cap_ret(IF[1]['N']))} kN·m (núcleo; no se suman)",
      ["Op.", "Caso", "μ interfaz", "T discos kN·m", "FU solo fricción", "FU solo adhesivo", "FU máx (núcleo)"], rows)
f_ad_min = Tmax / cap_ad
tau_req = Tmax * 1e6 / (Ac * ru)
print(f"Adhesivo solo: τ requerido para T_calado = {s3(tau_req)} MPa; fracción mínima de área adherida (τ de diseño) = {s3(f_ad_min)}; "
      f"fricción sola con μ_resp {P['mu_back']}: FU {s3(Tmax/(P['mu_back']*IF[1]['N']*ru/1e3))}")
# cortante térmico en el borde del pegado (decaimiento de cortante / shear-lag, sustrato rígido)
eps_th = (AL_SS - AL_S) * P["dT"]
t_dsk = IF[1]["tss"]
rows = []
for nm, Ga in (("epóxico rígido", 1000.0), ("epóxico tenaz", 100.0), ("PU / MS polímero", 10.0)):
    for ta in (0.3, 1.0):
        lam = math.sqrt(Ga / (E_SS * t_dsk * ta)); tmax = eps_th * math.sqrt(Ga * E_SS * t_dsk / ta)
        rows.append([nm, s3(Ga), s3(ta), s3(tmax), s3(tmax / tau), s3(1 / lam)])
table(f"3e'. Cortante térmico en el borde del pegado, ΔT = {P['dT']} K, ε = {s3(eps_th*1e6)}e-6: τ_máx = ε·√(G_a·E·t/t_a) (disco t = {s3(t_dsk)} mm)",
      ["Adhesivo", "G_a MPa", "t_a mm", "τ_máx borde MPa", "τ_máx/τ_diseño", "longitud de transferencia 1/λ mm"], rows)

# ---- (b') arrastre de la lámina UHMW
mu_top_max = max(P["muB_cont"], P["muB_dry"], P["muB_d"])
Fdrag = mu_top_max * IF[2]["N"]
db_ = 8.0
n_bolts = Fdrag * 1e3 / (P["p_uhmw"] * db_ * IF[2]["tuh"])
print(f"\n3f'. Arrastre de la lámina UHMW: μ_máx·N = {s3(mu_top_max)}·{s3(IF[2]['N'])} = {s3(Fdrag)} kN (μ_d·N daría {s3(P['muB_d']*IF[2]['N'])} kN); "
      f"un bulón M8 resiste {s3(P['p_uhmw']*db_*IF[2]['tuh']/1e3)} kN por aplastamiento del UHMW → {s3(n_bolts)} bulones")

# ---- (f) otros
bolt = {"M6": 3.3, "M8": 4.4, "M10": 5.5}
rows = [[b_, s3(k_), s3(IF[1]["tss"] - P["ss_allow"] - k_), "ok" if IF[1]["tss"] - P["ss_allow"] - k_ >= 1.5 else "queda < 1,5 mm bajo la cabeza"] for b_, k_ in bolt.items()]
table(f"3f. Pernos avellanados (ISO 10642 / DIN 7991, altura de cabeza k) en el disco de {s3(IF[1]['tss'])} mm menos {s3(P['ss_allow'])} mm de relapeado", ["Perno", "k mm", "espesor restante bajo la cabeza mm", "veredicto"], rows)
mt = [D0["derivados"]["masas"]["total"], DA["derivados"]["masas"]["total"], DB["derivados"]["masas"]["total"]]
for k, lab in ((1, "A"), (2, "B")):
    comp("3g", f"op. {lab} · dTot (masa total − op. 0)", ifc_core[k].get("dTot"), mt[k] - mt[0])
    comp("3g", f"op. {lab} · dTot ≥ mAdd", 1.0 if ifc_core[k].get("dTot", 0) >= IF[k]["mAdd"] else 0.0, 1.0)
print(f"Masa total: {s3(mt[0])} → A {s3(mt[1])} (dTot {s3(ifc_core[1].get('dTot'))}, mAdd {s3(IF[1]['mAdd'])}) → B {s3(mt[2])} (dTot {s3(ifc_core[2].get('dTot'))}, mAdd {s3(IF[2]['mAdd'])})")



# ======================================================================================
# 4. OPCIÓN C: placa de bronce con tapones de grafito (bz_conf 1, 2 y 3)
#    Todo se deriva aquí desde el enunciado de la opción (mecánica de placas, AISC 360-22 ASD 0,6 Fy, Archard, PV).
# ======================================================================================
RHO_GR, AL_BZ, E_BZ = 1.8e-6, 18e-6, 110000.0
COM_BZ = [4, 5, 6, 8, 10, 12, 15, 20, 25, 30]
COM_CARA = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
CONF_NAME = {1: "C1 bronce + disco duro", 2: "C2 bronce + 2.ª placa de bronce", 3: "C3 pastillas + disco duro"}
def fg_of(PP):
    return math.pi * PP["bz_plug_d"] ** 2 / (2 * math.sqrt(3) * PP["bz_plug_p"] ** 2)


def eta_of(PP):
    return (PP["bz_plug_p"] - PP["bz_plug_d"]) / PP["bz_plug_p"]


def ifaceC(PP, conf):
    """Opción C: espesores (bronce y pieza rotatoria), q_máx con el peso de la pieza rotatoria (iterado), masas, Δ."""
    Ro_, Ri_, A_, I_, ru_ = geom(PP)
    m_mesa_, rho_piv_ = mesa(PP)
    W = PP["W_tf"] * g0
    a = PP["ss_void"] / 2
    cov = PP["bz_cover"] if conf == 3 else 1.0
    eta = eta_of(PP); fg = fg_of(PP); sb = 0.6 * PP["Fy_bz"]
    if conf == 2:
        Fy_r, alw, tmn, lst, rho_r = PP["Fy_bz2"], PP["bz_allow"], PP["bz_tmin"], COM_BZ, PP["rho_bz"] * 1e-6
    else:
        Fy_r, alw, tmn, lst, rho_r = PP["Fy_cara"], PP["ss_allow"], PP["cara_tmin"], COM_CARA, RHO_SS
    sr = 0.6 * Fy_r
    gr = PP["h_gr"]; fgr = groove_area(PP) / A_ if gr > 0 else 0.0           # ranuras de engrase en la placa de bronce
    t_b, t_r = com(PP["bz_tmin"], COM_BZ), com(tmn, lst)
    out = None
    for _ in range(80):
        Delta = t_b + t_r
        m_rot = rho_r * A_ * t_r
        m_piv = rho_piv_ * (PP["t_base"] + PP["h_disc"] - PP["t_top"] + 3 + Delta)
        Wd = (m_mesa_ + 0.5 * m_piv + m_rot) * g0 / 1e3
        N = W + Wd; ND = PP["phi_d"] * W + Wd
        q = ND * 1e3 / A_ + ND * 1e3 * PP["e"] * Ro_ / I_
        qloc = q / cov; qc = qloc if conf == 3 else q
        tfB = a * math.sqrt(0.75 * qloc / sb)
        tbReq = max(tfB / math.sqrt(eta) + PP["bz_allow"] + gr, PP["bz_tmin"])
        tfR = a * math.sqrt(0.75 * qc / sr)
        trReq = max(tfR + alw, tmn)
        tb_n = PP["t_bz"] if PP["t_bz"] > 0 else com(tbReq, COM_BZ)
        tr_n = PP["t_cara"] if PP["t_cara"] > 0 else com(trReq, lst)
        mBz = A_ * cov * t_b * (PP["rho_bz"] * 1e-6 * (1 - 0.7 * fg) + RHO_GR * 0.7 * fg) if math.isfinite(t_b) else math.inf
        out = dict(conf=conf, q=q, qloc=qloc, qc=qc, qnet=qloc / (1 - fg - fgr), gr=gr, fgr=fgr, cov=cov, eta=eta, fg=fg, a=a, tfB=tfB, tbReq=tbReq, tb=t_b,
                   tfR=tfR, trReq=trReq, tr=t_r, delta=Delta, N=N, ND=ND, Wd=Wd, m_rot=m_rot, mBz=mBz, mAdd=mBz + m_rot, m_piv=m_piv,
                   Fy_r=Fy_r, alw=alw, sr=sr, sb=sb)
        if tb_n == t_b and tr_n == t_r:
            break
        t_b, t_r = tb_n, tr_n
    return out


def cap_retC(r, PP):
    return max(PP["mu_back"] * r["N"] * ru / 1e3, PP["tau_bond"] * Ac * r["cov"] * ru / 1e6)


def cap_ret_mesa(r, PP):
    """retención del disco duro / 2.ª placa sobre la mesa: área completa (sin cobertura)"""
    return max(PP["mu_back"] * r["N"] * ru / 1e3, PP["tau_bond"] * Ac * ru / 1e6)


def tauC(PP, al, E_, t):
    return (al - AL_S) * PP["dT"] * math.sqrt(PP["G_ad"] * E_ * t / PP["t_ad"])


def vcil(PP):
    return PP["Q_pump"] * 1e6 / 60 / (PP["n_cyl"] * math.pi / 4 * PP["D_bore"] ** 2)


def rowsC(PP, conf):
    """Valores propios de cada fila de interfazChecks.C: clave (subcadena del nombre) → (dem, cap, fu)."""
    r = ifaceC(PP, conf); a = r["a"]; fu = lambda d, c: (d / c if c and c > 0 else math.inf)
    tb, tr = r["tb"], r["tr"]
    sigb = 3 * r["qloc"] * a ** 2 / (4 * (tb - PP["bz_allow"] - r["gr"]) ** 2 * r["eta"]) if tb > PP["bz_allow"] + r["gr"] else math.inf
    sigr = 3 * r["qc"] * a ** 2 / (4 * (tr - r["alw"]) ** 2) if tr > r["alw"] else math.inf
    Tret = Tmax; cret = cap_retC(r, PP)
    v_e = Ro * vcil(PP) / a_min / 1000
    PVv = r["qnet"] * v_e
    sl = PP["life"] * PP["turns_yr"] * 2 * math.pi * PP["r_ef"] / 1000
    hw = PP["k_bz"] * 1e-7 * r["qnet"] * sl
    reserva = tb - r["tfB"] / math.sqrt(r["eta"])
    ep = (AL_BZ - AL_S) * PP["dT"]
    R = {
        "Placa de bronce: flexión sobre un vacío local": (sigb, r["sb"], fu(sigb, r["sb"])),
        "Placa de bronce: espesor adoptado frente al requerido": (r["tbReq"], tb, fu(r["tbReq"], tb)),
        "Placa de bronce: espesor por flexión / requerido": (r["tfB"], tb, None),
        "Tapones de grafito: fracción de área": (r["fg"], r["eta"], None),
        "Presión de contacto sobre el bronce neto": (r["qnet"], PP["p_bz"], fu(r["qnet"], PP["p_bz"])),
        "valor PV en el borde": (PVv, PP["PV_bz"], fu(PVv, PP["PV_bz"])),
        "desgaste en la vida de diseño": (hw, reserva, fu(hw, reserva)),
        "profundidad restante tras el desgaste": (hw + 2, 0.7 * tb, fu(hw + 2, 0.7 * tb)),
        "Dilatación diferencial radial": (ep * Ro, None, None),
        "Altura que agrega": (r["delta"], None, None),
        "Masa agregada": (r["mAdd"], None, None),
        "Arranque con adherencia–deslizamiento": (0.0, None, None),
        "Par galvánico": (0.0, None, None),
    }
    if conf == 2:
        R["2.ª placa de bronce (maciza, aleación distinta): flexión"] = (sigr, r["sr"], fu(sigr, r["sr"]))
        R["2.ª placa de bronce: espesor adoptado"] = (r["trReq"], tr, fu(r["trReq"], tr))
        R["Bronce contra bronce"] = (0.0, None, None)
    else:
        R["Disco duro: flexión sobre un vacío local"] = (sigr, r["sr"], fu(sigr, r["sr"]))
        R["Disco duro: espesor adoptado"] = (r["trReq"], tr, fu(r["trReq"], tr))
        R["Pareja bronce–disco duro: diferencia de dureza"] = (100.0, PP["HB_cara"] - PP["HB_bz"], fu(100.0, PP["HB_cara"] - PP["HB_bz"]))
    if PP["fix_mode"] == 1:
        ns = PP["n_sec"]; nb = PP["bz_npad"] if conf == 3 else ns
        piece_rows(PP, R, "Pastillas de bronce" if conf == 3 else "Placa de bronce", nb, "pastillas" if conf == 3 else "sectores", tb, PP["Fy_bz"], PP["bz_allow"], r["gr"])
        if conf == 3 or conf == 1:
            piece_rows(PP, R, "Disco duro", ns, "sectores", tr, PP["Fy_cara"], PP["ss_allow"])
        else:
            piece_rows(PP, R, "2.ª placa de bronce", ns, "sectores", tr, PP["Fy_bz2"], PP["bz_allow"])
        if conf == 3:                      # la cabeza del tornillo de las pastillas se rotula «Placa de bronce»
            R["Placa de bronce: cabeza del tornillo avellanado"] = R.pop("Pastillas de bronce: cabeza del tornillo avellanado")
        R["Placa de bronce con grafito: masa del sector"] = (r["mBz"] / nb, 25.0, r["mBz"] / nb / 25.0)
        if conf == 2:
            R["2.ª placa de bronce: masa del sector"] = (r["m_rot"] / ns, 25.0, r["m_rot"] / ns / 25.0)
            R["Sectores de la 2.ª placa: crecimiento por dilatación de la cuerda"] = (ep * chord_of(PP, ns), None, None)
        else:
            R["Disco duro: masa del sector"] = (r["m_rot"] / ns, 25.0, r["m_rot"] / ns / 25.0)
            R["Sectores del disco duro: crecimiento por dilatación de la cuerda"] = ((AL_SS - AL_S) * PP["dT"] * chord_of(PP, ns), None, None)
        R["Sectores de bronce: crecimiento por dilatación de la cuerda"] = (ep * chord_of(PP, nb), None, None)
        if conf == 3:
            R["Pastillas de bronce: crecimiento por dilatación de la cuerda de la pastilla"] = (ep * chord_of(PP, nb), None, None)
        R["Soldar los topes antes del alivio"] = (0.0, None, None)
    else:
        R["Retención de la placa de bronce"] = (Tret, cret, fu(Tret, cret))
        R["Adhesivo de la placa de bronce: cortante"] = (tauC(PP, AL_BZ, E_BZ, tb), PP["tau_cyc"], fu(tauC(PP, AL_BZ, E_BZ, tb), PP["tau_cyc"]))
        R["Dilatación diferencial bronce–acero: tensión"] = (E_BZ * ep, 0.6 * PP["Fy_bz"], fu(E_BZ * ep, 0.6 * PP["Fy_bz"]))
        R["Fijación permanente (pegado)"] = (0.0, None, None)
        if conf == 2:
            R["Adhesivo de la 2.ª placa de bronce"] = (tauC(PP, AL_BZ, E_BZ, tr), PP["tau_cyc"], fu(tauC(PP, AL_BZ, E_BZ, tr), PP["tau_cyc"]))
            R["Dilatación diferencial bronce–acero de la 2.ª placa"] = (E_BZ * ep, 0.6 * PP["Fy_bz2"], fu(E_BZ * ep, 0.6 * PP["Fy_bz2"]))
            R["Retención de la 2.ª placa de bronce sobre la mesa"] = (Tret, cap_ret_mesa(r, PP), fu(Tret, cap_ret_mesa(r, PP)))
        else:
            R["Adhesivo del disco duro"] = (tauC(PP, AL_SS, E_SS, tr), PP["tau_cyc"], fu(tauC(PP, AL_SS, E_SS, tr), PP["tau_cyc"]))
            R["Retención del disco duro sobre la mesa"] = (Tret, cap_ret_mesa(r, PP), fu(Tret, cap_ret_mesa(r, PP)))
        if conf == 3:
            R["crecimiento por dilatación de la cuerda de la pastilla"] = (ep * chord_of(PP, PP["bz_npad"]), None, None)
            mum = max(PP["muC_d"], PP["muC_cont"], PP["muC_dry"])
            R["Retención de las pastillas"] = (mum * r["N"], None, None)
    grease_rows(PP, R, "placa de bronce")
    # plancha inferior de la mesa y losa: solo escalamiento lineal con q del FEA de referencia (conf. 1, q_c = q_máx)
    sl_, sg_ = PL_LOC1 * r["qc"], PL_GLO1 * r["q"]
    R["Plancha inferior: global + local"] = (sl_ + sg_, PL_CAP, (sl_ + sg_) / PL_CAP)
    R["Presión sobre losa"] = (r["qc"], PP["q_floor"], None)
    return R, r


def mus_c(PP):
    return dict(nom=PP["muC_nom"], dis=PP["muC_d"], borde=PP["muC_d"], cont=PP["muC_cont"], seco=PP["muC_dry"])


def casos_c(PP, N_kN):
    m = mus_c(PP); rr = dict(nom=ru, dis=PP["r_ef"], borde=Ro, cont=PP["r_ef"], seco=ru); out = {}
    for c in m:
        T = par(PP, N_kN, m[c], rr[c]); F = FU_ * T / n / 1e3
        out[c] = dict(mu=m[c], r=rr[c], T=T / 1e6, F=F, p=F * 1e3 / A_b * 10, FS=F_st / 1e3 / F)
    return out


def match_row(rows_mine, name):
    return next((k for k in rows_mine if k in name), None)


cap_w = 0.6 * P["FEXX"] / (1.2 * P["Nd"])


def fail_set(R):
    return tuple(sorted(k for k, (d, c_, f) in R.items() if f is not None and f > 1 + 1e-9))


def sold_fu(Delta):
    return soldadura_mejilla(Delta) / cap_w


# ---------------- 4.1 interfazChecks.C y escenarios.ifaces[3] con los defaults, bz_conf 1, 2, 3 ----------------
DC = {c: export_c({"opt_bz": 1, "bz_conf": c}) for c in (1, 2, 3)}
if any(v is None for v in DC.values()):
    print("El núcleo rechazó la opción C con los defaults"); sys.exit(2)
PC = {c: dict(DC[c]["P"]) for c in DC}
_vv = lambda DD, sub: next(v for v in DD["verificaciones"] if sub in v["nombre"])
_rq = ifaceC(PC[1], 1)                                              # conf. 1: q_c = q_máx (cobertura 1)
_l1, _t1 = _vv(DC[1], "Plancha inferior: σvm local"), _vv(DC[1], "Plancha inferior: global + local")
PL_LOC1 = _l1["dem"] / _rq["qc"]                                     # σ_local por unidad de q_c [MPa/MPa] (FEA ∝ q: no se replica)
PL_GLO1 = (_t1["dem"] - _l1["dem"]) / _rq["q"]                       # σ_global (momento de la placa) por unidad de q_máx
PL_CAP = _t1["cap"]


def cmp_val(prueba, name, mine, core, tol=TOL):
    """comparación con tratamiento de None/inf/0; devuelve (ok, Δ%)"""
    if core is None or (isinstance(core, float) and not math.isfinite(core)):
        ok = mine is None or not math.isfinite(mine)
        COMP.append((prueba, name, s3(mine), s3(core), "—", "coincide" if ok else "discrepa")); return ok, 0.0
    if mine is None or not math.isfinite(mine):
        COMP.append((prueba, name, s3(mine), s3(core), "—", "discrepa")); return False, float("nan")
    d = (mine - core) / core * 100 if core else (0.0 if abs(mine) < 1e-12 else 100.0)
    ok = abs(d) <= tol * 100
    COMP.append((prueba, name, s3(mine), s3(core), f"{d:+.3f}", "coincide" if ok else "discrepa")); return ok, d


tab = []
for c in (1, 2, 3):
    R, r = rowsC(PC[c], c)
    for row in DC[c]["interfazChecks"]["C"]:
        key = match_row(R, row["nombre"])
        if key is None:
            tab.append([c, row["nombre"][:56], "—", "—", "—", "sin fórmula propia"]); continue
        dem, cap, fu = R[key]
        worst = 0.0; bad = False
        for nm, mv, cv in (("dem", dem, row["dem"]), ("cap", cap, row.get("cap")), ("FU", fu, row.get("fu"))):
            if cv is None and mv is None:
                continue
            ok, d = cmp_val("4a", f"C{c} · {row['nombre'][:58]} [{nm}]", mv, cv)
            bad = bad or not ok; worst = max(worst, abs(d) if d == d else 0)
        e_m = est_mine(fu if row["estado"] not in ("pend",) else None)
        e_c = row["estado"] if row["estado"] in ("ok", "fail") else ("info" if row["estado"] in ("info", "pend") else row["estado"])
        if row["estado"] != "pend" and e_m != e_c and not (row["estado"] == "warn" and e_m == "ok"):
            bad = True
        tab.append([c, row["nombre"][:56], f"{s3(dem)} / {s3(cap)} / {s3(fu)}", f"{s3(row['dem'])} / {s3(row.get('cap'))} / {s3(row.get('fu'))}", f"{worst:.4f}",
                    ("pend. (núcleo)" if row["estado"] == "pend" and not bad else "DISCREPA" if bad else "coincide") + f" [{row['estado']}]"])
table("4a. interfazChecks.C (propio frente a núcleo): dem / cap / FU y estado", ["conf", "Fila", "Propio dem / cap / FU", "Núcleo dem / cap / FU", "Δ máx %", "Veredicto"], tab)

tab = []
for c in (1, 2, 3):
    ic = DC[c]["escenarios"]["ifaces"][3]; ia = DC[c]["apoyo"]["interfaz"]; r = ifaceC(PC[c], c)
    cs = casos_c(PC[c], r["N"])["dis"]
    for nm, mine, core in (("q_máx (MPa)", r["q"], ic["q"]), ("q_máx (apoyo.interfaz)", r["q"], ia["q"]), ("q_loc (MPa)", r["qloc"], ia["qLoc"]), ("q_neto (MPa)", r["qnet"], ia["qNet"]),
                           ("f_g", r["fg"], ia["fg"]), ("f_ranuras", r["fgr"], ia.get("fgr")), ("η", r["eta"], ia["eta"]),
                           ("t_flex bronce (mm)", r["tfB"], ic["tFlexB"]), ("t_req bronce (mm)", r["tbReq"], ic["tbzReq"]), ("t_bronce adoptado (mm)", r["tb"], ic["tbz"]),
                           ("t_flex pieza rot. (mm)", r["tfR"], ic["tFlex"]), ("t_req pieza rot. (mm)", r["trReq"], ic["tssReq"]), ("t_rot adoptado (mm)", r["tr"], ic["tss"]),
                           ("Δ altura (mm)", r["delta"], ic["delta"]), ("masa de bronce (kg; en conf. 2 el núcleo suma las dos placas)", r["mBz"] + (r["m_rot"] if c == 2 else 0.0), ia["mBz"]), ("masa pieza rot. (kg)", r["m_rot"], ia["mTop"]), ("masa agregada (kg)", r["mAdd"], ic["mAdd"]),
                           ("F de diseño (kN)", cs["F"], ic["F"]), ("p de diseño (bar)", cs["p"], ic["p"]), ("FS de diseño", cs["FS"], ic["FS"])):
        ok, d = cmp_val("4b", f"C{c} · {nm}", mine, core)
        tab.append([c, nm, s3(mine), s3(core), f"{d:+.4f}", "coincide" if ok else "DISCREPA"])
    Tu = par(PC[c], r["N"], 1.0, PC[c]["r_ef"]) / n
    cmp_val("4b", f"C{c} · μ máx que gira (r_ef)", F_st / (FU_ * Tu), ic["muMax"])
    mt0 = D0["derivados"]["masas"]["total"]; mtc = DC[c]["derivados"]["masas"]["total"]
    cmp_val("4b", f"C{c} · dTot (masa total − op. 0)", mtc - mt0, ic["dTot"])
    comp("4b", f"C{c} · dTot ≥ mAdd", 1.0 if ic["dTot"] >= r["mAdd"] else 0.0, 1.0)
    comp("4b", f"C{c} · masa total = suma de componentes", sum(DC[c]["derivados"]["masas"][k] for k in ("disc", "ss", "uhmw", "bz", "base", "rim", "brackets", "dogs", "shoes", "beds", "pivot", "cyl")), mtc)
table("4b. escenarios.ifaces[3] y apoyo.interfaz (opción C): espesores, q, masas, F/p/FS de diseño", ["conf", "Magnitud", "Propio", "Núcleo", "Δ %", "Veredicto"], tab)

# ---------------- 4.2 casos de giro de C ----------------
tab = []
for c in (1, 2, 3):
    r = ifaceC(PC[c], c); cs = casos_c(PC[c], r["N"]); cc = {x["id"]: x for x in DC[c]["derivados"]["casos"]}
    for cid, x in cs.items():
        core = cc[cid]
        okF, dF = cmp_val("4c", f"C{c} · caso {cid}: F (kN)", x["F"], core["F"]); cmp_val("4c", f"C{c} · caso {cid}: p (bar)", x["p"], core["p"])
        okS, _ = cmp_val("4c", f"C{c} · caso {cid}: FS", x["FS"], core["FS"]); cmp_val("4c", f"C{c} · caso {cid}: T (kN·m)", x["T"], core["T"])
        tab.append([c, cid, s3(x["mu"]), s3(x["r"]), s3(x["T"]), s3(x["F"]), s3(core["F"]), s3(x["p"]), s3(core["p"]), s3(x["FS"]), s3(core["FS"]), f"{dF:+.4f}", "gira" if x["F"] <= F_st / 1e3 else "NO gira", "coincide" if okF and okS else "DISCREPA"])
table("4c. Casos de giro de la opción C (F por cilindro kN, p bar, T kN·m)", ["conf", "Caso", "μ", "r mm", "T", "F propio", "F núcleo", "p propio", "p núcleo", "FS propio", "FS núcleo", "Δ F %", "Gira", "Veredicto"], tab)


# ---------------- 4.3 barridos con params.json (núcleo y propio deben coincidir en todos los puntos) ----------------
SWC = [("ss_void", [60, 80, 100, 120, 140, 160, 180, 200], (1, 2, 3)), ("Fy_bz", [97, 125, 170, 275, 415], (1, 2, 3)), ("Fy_bz2", [97, 125, 170, 275], (2,)),
       ("bz_plug_d", [6, 8, 10, 12, 14, 16, 18, 20], (1, 2, 3)), ("bz_plug_p", [18, 20, 24, 30, 36, 45, 60], (1, 2, 3)),
       ("bz_cover", [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], (3,)), ("W_tf", [200, 240, 280, 300, 320, 360], (1, 2, 3)),
       ("k_bz", [1, 5, 10, 50, 200, 500], (1, 2, 3)), ("p_bz", [5, 10, 20, 40, 60], (1, 2, 3)),
       ("n_sec", [12, 18, 24, 36, 48], (1, 2, 3)), ("bz_npad", [12, 18, 24, 36, 48], (3,)), ("w_tope", [3, 4, 6, 8, 12, 16], (1, 2, 3)), ("d_tor", [4, 6, 8, 10, 12], (1, 2, 3)),
       ("h_gr", [0, 0.5, 1, 2, 3, 5], (1, 2, 3)), ("w_gr", [3, 8, 15, 25], (1, 2, 3)), ("n_gr_rad", [0, 12, 24, 48], (1, 3)), ("L_tope", [0, 100, 200, 400], (1, 2, 3)), ("fix_mode", [2], (1, 2, 3))]
swC_n = swC_bad = 0
PLANCHA_DEV = []
swC_rej = []
prefetch([dict(opt_bz=1, bz_conf=c, **{k: v}) for k, vals, cs in SWC for c in cs for v in vals] + [dict(opt_bz=1, bz_conf=c, bz_cover=0.5) for c in (1, 2)])


def cmp_c(over, conf):
    """compara propio y núcleo en P+over; devuelve (DD, R, r, ok, malos)"""
    global swC_n, swC_bad
    o = dict(opt_bz=1, bz_conf=conf, **over)
    DD = export_c(o)
    PP = dict(PC[conf]); PP.update(over)
    if DD is None:
        return None, None, None, True, []
    R, r = rowsC(PP, conf)
    ic = DD["escenarios"]["ifaces"][3]; bad = []
    cs = casos_c(PP, r["N"])["dis"]
    pairs = [("tbz", r["tb"]), ("tbzReq", r["tbReq"]), ("tFlexB", r["tfB"]), ("tss", r["tr"]), ("tssReq", r["trReq"]), ("tss2Req", r["trReq"]), ("tss2", r["tr"]), ("tFlex", r["tfR"]), ("delta", r["delta"]), ("mAdd", r["mAdd"]),
             ("q", r["q"]), ("F", cs["F"]), ("p", cs["p"]), ("FS", cs["FS"])]
    for kc, mv in pairs:
        swC_n += 1
        cv = ic.get(kc)
        if cv is None and not math.isfinite(mv):
            continue
        if cv is None or not math.isfinite(mv) or (abs(mv - cv) > TOL * abs(cv) if cv else abs(mv) > 1e-9):
            bad.append(kc)
    for row in DD["interfazChecks"]["C"]:
        key = match_row(R, row["nombre"])
        if key is None:
            swC_n += 1; bad.append("fila?" + row["nombre"][:20]); continue
        dem, cap, fu = R[key]
        for nm, mv, cv in (("dem", dem, row["dem"]), ("cap", cap, row.get("cap")), ("fu", fu, row.get("fu"))):
            if cv is None and (mv is None or not math.isfinite(mv)):
                continue
            swC_n += 1
            if cv is None or mv is None or not math.isfinite(mv) or (abs(mv - cv) > TOL * abs(cv) if cv else abs(mv) > 1e-9):
                bad.append(f"{key[:18]}.{nm}")
        if row["estado"] in ("ok", "fail") and est_mine(fu) != row["estado"]:
            bad.append(f"{key[:18]}.estado")
        swC_n += 1
    sw = next(v for v in DD["verificaciones"] if "Soldadura mejillas–base (4" in v["nombre"])
    swC_n += 1
    if abs(sold_fu(r["delta"]) - sw["fu"]) > TOL * sw["fu"]:
        bad.append("soldadura mejillas")
    # plancha inferior (escalamiento lineal con q) y losa
    pl, lo_ = _vv(DD, "Plancha inferior: global + local"), _vv(DD, "Plancha inferior: σvm local")
    for nm, mv, cv in (("plancha inf. σ_loc", PL_LOC1 * r["qc"], lo_["dem"]), ("plancha inf. σ_tot", R["Plancha inferior: global + local"][0], pl["dem"]),
                       ("plancha inf. FU", R["Plancha inferior: global + local"][2], pl["fu"]), ("losa q", r["qc"], _vv(DD, "Presión sobre losa")["dem"])):
        swC_n += 1
        if abs(mv - cv) > TOL * abs(cv):
            bad.append(nm); PLANCHA_DEV.append((conf, over, nm, mv, cv))
    swC_n += 1
    if (R["Plancha inferior: global + local"][2] > 1 + 1e-9) != (pl["fu"] > 1 + 1e-9):
        bad.append("plancha inf. estado")
    swC_bad += len(bad)
    return DD, R, r, not bad, bad


def fu_str(R, key):
    return s3(R[key][2])


for key, vals, cs_ in SWC:
    for c in cs_:
        rows = []; wear = key in ("k_bz", "p_bz")
        for v in vals:
            DD, R, r, ok, bad = cmp_c({key: v}, c)
            if DD is None:
                swC_rej.append((c, key, v)); rows.append([s3(v), "rechazado por el núcleo"] + [""] * 8); continue
            ic = DD["escenarios"]["ifaces"][3]; fs_ = fail_set(R)
            if sold_fu(r["delta"]) > 1: fs_ = fs_ + ("soldadura mejillas",)
            est = ("; ".join(x[:22] for x in fs_) if fs_ else "cumple") + (" | " + ("coincide" if ok else "DISCREPA " + ",".join(bad)))
            if wear:
                rows.append([s3(v), s3(r["qnet"]), s3(R["Presión de contacto sobre el bronce neto"][2]), s3(R["valor PV en el borde"][2]), s3(R["desgaste en la vida de diseño"][2]),
                             s3(R["profundidad restante tras el desgaste"][2]), est])
            else:
                rows.append([s3(v), f"{s3(r['tbReq'])}→{s3(r['tb'])} / {s3(ic['tbzReq'])}→{s3(ic['tbz'])}", f"{s3(r['trReq'])}→{s3(r['tr'])} / {s3(ic['tss'])}", s3(r["delta"]), s3(r["mAdd"]),
                             s3(R["Placa de bronce: flexión sobre un vacío local"][2]), s3(max([v_[2] for k_, v_ in R.items() if "del tope" in k_] + [v_[2] for k_, v_ in R.items() if "Retención" in k_ and v_[2] is not None] or [math.nan])),
                             s3(R["Plancha inferior: global + local"][2]), s3(sold_fu(r["delta"])), est])
        if wear:
            table(f"4d. Barrido de {key} en {CONF_NAME[c]}: FU de presión neta / PV / desgaste / profundidad del tapón", [key, "q_neto MPa", "FU q_neto", "FU PV", "FU desgaste", "FU prof. tapón", "Incumple | veredicto"], rows)
        else:
            table(f"4d. Barrido de {key} en {CONF_NAME[c]}: t_bz req→adoptado (propio / núcleo), t_rot, Δ, masa agregada, FU flexión bronce / topes (o retención con fix_mode 2) / plancha inferior / soldadura mejillas",
                  [key, "t_bz propio / núcleo", "t_rot propio / núcleo", "Δ mm", "mAdd kg", "FU flex.", "FU topes (o retención)", "FU plancha inf.", "FU sold. mejillas", "Incumple | veredicto"], rows)
print(f"\nBarridos de C: {swC_n} comparaciones, {swC_bad} discrepancias (tolerancia 0,1 %); puntos rechazados por el núcleo: {len(swC_rej)}")


# ---------------- 4.4 umbrales: dónde cambian los espesores comerciales y dónde dejan de cumplir las verificaciones ----------------
def state_c(PP, conf):
    R, r = rowsC(PP, conf)
    fs_ = fail_set(R) + (("soldadura mejillas",) if sold_fu(r["delta"]) > 1 + 1e-9 else ())
    return (r["tb"], r["tr"], fs_)


def core_state(DD, conf):
    if DD is None:
        return None
    R, _ = rowsC(PC[conf], conf); fs_ = []
    for row in DD["interfazChecks"]["C"]:
        k = match_row(R, row["nombre"])
        if k and row.get("fu") is not None and row["fu"] > 1 + 1e-9:
            fs_.append(k)
    sw = next(v for v in DD["verificaciones"] if "Soldadura mejillas–base (4" in v["nombre"])
    if sw["fu"] > 1 + 1e-9: fs_.append("soldadura mejillas")
    if _vv(DD, "Plancha inferior: global + local")["fu"] > 1 + 1e-9: fs_.append("Plancha inferior: global + local")
    ic = DD["escenarios"]["ifaces"][3]
    return (ic["tbz"], ic["tss"], tuple(sorted(fs_)))


def thresholds(key, lo, hi, conf, npts=400):
    xs = [lo + (hi - lo) * i / npts for i in range(npts + 1)]
    out = []; prev = state_c(dict(PC[conf], **{key: xs[0]}), conf)
    for i in range(1, len(xs)):
        cur = state_c(dict(PC[conf], **{key: xs[i]}), conf)
        if cur != prev:
            a_, b_ = xs[i - 1], xs[i]
            for _ in range(60):
                mid = (a_ + b_) / 2
                if state_c(dict(PC[conf], **{key: mid}), conf) == prev: a_ = mid
                else: b_ = mid
            out.append((b_, prev, cur)); prev = cur
    return out


def fmt_state(s):
    return f"{s3(s[0])}/{s3(s[1])}" + (" ✗ " + ",".join(x[:14] for x in s[2]) if s[2] else "")


UMB = [("ss_void", 60, 200, (1, 2, 3)), ("Fy_bz", 97, 415, (1, 2, 3)), ("Fy_bz2", 97, 275, (2,)), ("bz_plug_d", 4, 24, (1, 2, 3)), ("bz_plug_p", 13, 60, (1, 2, 3)),
       ("bz_cover", 0.4, 1.0, (3,)), ("W_tf", 200, 360, (1, 2, 3))]
UM = []
for key, lo, hi, cs_ in UMB:
    for c in cs_:
        for v, s0, s1 in thresholds(key, lo, hi, c):
            UM.append((key, c, v, s0, s1))
prefetch([dict(opt_bz=1, bz_conf=c, **{k: v * f}) for k, c, v, s0, s1 in UM for f in (1 - 2e-4, 1 + 2e-4)])
rows = []; um_bad = 0
for key, c, v, s0, s1 in UM:
    res = []
    for f in (1 - 2e-4, 1 + 2e-4):
        res.append(core_state(export_c(dict(opt_bz=1, bz_conf=c, **{key: v * f})), c))
    ok = res[0] == s0 and res[1] == s1
    um_bad += 0 if ok else 1
    comp("4u", f"umbral {key} C{c} = {s3(v)}", 1.0 if ok else 0.0, 1.0)
    cause = "espesor comercial" if (s0[0], s0[1]) != (s1[0], s1[1]) else "incumplimiento"
    if s0[2] != s1[2]:
        cause += " + " + ("pasa a incumplir " + ",".join(sorted(set(s1[2]) - set(s0[2]))) if set(s1[2]) - set(s0[2]) else "deja de incumplir " + ",".join(sorted(set(s0[2]) - set(s1[2]))))
    rows.append([key, c, s3(v), fmt_state(s0), fmt_state(s1), cause[:60], "coincide" if ok else "DISCREPA"])
table("4u. Umbrales: t_bz/t_rot adoptados (mm) y verificaciones incumplidas, debajo y encima del valor; el núcleo se contrasta a ±0,02 %", ["Parámetro", "conf", "Valor umbral", "Debajo (propio)", "Encima (propio)", "Causa", "Núcleo (±0,02 %)"], rows)
print(f"Umbrales: {len(UM)} detectados, {um_bad} discrepan con el núcleo")


# ======================================================================================
# 5. HIPÓTESIS FÍSICAS DE LA OPCIÓN C
# ======================================================================================
rC = {c: ifaceC(PC[c], c) for c in (1, 2, 3)}
RC = {c: rowsC(PC[c], c)[0] for c in (1, 2, 3)}
NU_BZ = 0.3

# ---- (a) factor de ligamento η frente a placa perforada con concentración de tensiones y a tapones prensados
def kt_cell(f, Ei_Em, nu_i=0.2, nu_m=0.3):
    """Celda circular (radio R = 1, agujero/inclusión de radio √f) con tracción equibiaxial unitaria en el borde (tensión plana, solución de Lamé).
    Devuelve σ_θ/σ en la interfaz, lado matriz. Ei_Em = 0 → agujero vacío (Kt = 2/(1−f))."""
    a2 = f; cm = 1 / (1 - nu_m ** 2); ki = Ei_Em / (1 - nu_i)
    A = 1 / (cm * ((1 + nu_m) - (1 - nu_m) * a2 * ((cm * (1 + nu_m) - ki) / (cm * (1 - nu_m) + ki))))
    B = A * (cm * (1 + nu_m) - ki) * a2 / (cm * (1 - nu_m) + ki)
    return cm * (A * (1 + nu_m) + B * (1 - nu_m) / a2)


fgC, etaC = fg_of(P), eta_of(P)
Kt_eq0 = kt_cell(fgC, 0.0); Kt_eqg = kt_cell(fgC, 10000.0 / E_BZ)
rr_ = P["bz_plug_d"] / P["bz_plug_p"]
Kt_net_row = 3 - 3.14 * rr_ + 3.667 * rr_ ** 2 - 1.527 * rr_ ** 3          # Peterson (hilera de agujeros / placa con agujero central), referido a la sección neta
KT = [("equibiaxial, celda de Lamé, agujero vacío", Kt_eq0), ("equibiaxial, celda de Lamé, tapón de grafito (E = 10 GPa, ν = 0,2)", Kt_eqg),
      ("agujero aislado, estado 1 : ν (borde empotrado): 3 − ν", 3 - NU_BZ), ("hilera de agujeros, tracción uniaxial (Peterson, Kt_neto/η)", Kt_net_row / etaC)]
rows = []
for c in (1, 3):
    r = rC[c]; sig_core = RC[c]["Placa de bronce: flexión sobre un vacío local"][0]; sig_sol = sig_core * etaC
    for nm, kt in KT:
        rows.append([c, nm, s3(kt), s3(sig_sol), s3(sig_core), s3(kt * sig_sol), s3(kt * sig_sol / P["Fy_bz"]), s3(kt * sig_sol / sig_core)])
table(f"5a. Placa perforada: tensión del núcleo (sección neta, σ_sólido/η) frente a la tensión elástica máxima en el borde del agujero (Ø{P['bz_plug_d']:g}, paso {P['bz_plug_p']:g}, η = {s3(etaC)}, f_g = {s3(fgC)}); Fy_bz = {P['Fy_bz']:g} MPa",
      ["conf", "Modelo de Kt (sobre σ del disco sólido)", "Kt bruto", "σ_sólido MPa", "σ núcleo MPa", "σ pico MPa", "σ pico / Fy", "σ pico / σ núcleo"], rows)
rows = []
for c in (1, 3):
    r = rC[c]; ts = r["tfB"] * math.sqrt(etaC)
    for nm, kt in (("Kt = 3,0, pico ≤ Fy", 3.0), ("Kt = 3,0, pico ≤ 0,6·Fy", 3.0), ("Kt = 3,72, pico ≤ 0,6·Fy", Kt_net_row / etaC), ("núcleo (sección neta ≤ 0,6·Fy)", None)):
        if kt is None:
            treq = r["tbReq"]
        else:
            lim = P["Fy_bz"] if "≤ Fy" in nm else 0.6 * P["Fy_bz"]
            treq = r["a"] * math.sqrt(0.75 * r["qloc"] * kt / lim) + P["bz_allow"]; treq = max(treq, P["bz_tmin"])
        rows.append([c, nm, s3(treq), s3(com(treq, COM_BZ)), s3(r["tb"]), "cubre" if com(treq, COM_BZ) <= r["tb"] else f"NO cubre (pide {s3(com(treq, COM_BZ))})"])
table("5a'. Espesor de la placa de bronce con distintos criterios del borde del agujero (q_loc, a = ss_void/2, sobreespesor incluido)", ["conf", "Criterio", "t_req mm", "comercial", "adoptado núcleo", "veredicto"], rows)
rows = []
for d_ in (6, 8, 10, 12, 14, 16, 18, 20):
    PP = dict(P, bz_plug_d=d_); e_ = eta_of(PP); f_ = fg_of(PP)
    rows.append([d_, s3(e_), s3(f_), s3(kt_cell(f_, 0.0)), s3(e_ * P["bz_plug_p"]), s3(1 / e_)])
table(f"5a''. Ligamento y área de grafito con paso {P['bz_plug_p']:g} mm (η = (p−d)/p; f_g = π d²/(2√3 p²) del patrón hexagonal)", ["Ø tapón mm", "η", "f_g", "Kt celda vacía", "ligamento mm", "1/η"], rows)
print(f"Tapón de grafito prensado (E_g/E_bz = {10000/E_BZ:.3f}): Kt de la celda baja de {s3(Kt_eq0)} a {s3(Kt_eqg)} ({(Kt_eqg/Kt_eq0-1)*100:+.1f} %): el tapón casi no colabora en resistencia; sí en rigidez (módulo de membrana de la placa llena ≈ (1−f_g) + f_g·E_g/E ≈ {(1-fgC)+fgC*10000/E_BZ:.2f} frente a ≈ 0,5–0,67 de la placa vacía)")

# ---- (b) pastillas: presión local q_c = q_máx/cobertura sobre el respaldo (FEA de la plancha inferior y losa)
COVS = (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 1.0)
TBOT = (16, 18, 20, 22, 25); COVT = (0.5, 0.6, 0.7, 0.8, 0.9)
prefetch([{"opt_bz": 1, "bz_conf": 3, "bz_cover": cv_} for cv_ in COVS] + [{"opt_bz": 1, "bz_conf": 3, "bz_cover": cv_, "t_bot": tb_} for cv_ in COVT for tb_ in TBOT])
rows = []; fu_pl = []
for cv_ in COVS:
    DD = export_c({"opt_bz": 1, "bz_conf": 3, "bz_cover": cv_}); Rc, rc = rowsC(dict(PC[3], bz_cover=cv_), 3)
    pl, lo_, ls = _vv(DD, "Plancha inferior: global + local"), _vv(DD, "Plancha inferior: σvm local"), _vv(DD, "Presión sobre losa")
    mine = Rc["Plancha inferior: global + local"]
    fu_pl.append((cv_, pl["fu"], mine[2]))
    rows.append([s3(cv_), s3(rc["qc"]), s3(lo_["fu"]), s3(pl["fu"]), s3(mine[2]), f"{(mine[2] / pl['fu'] - 1) * 100:+.4f}", pl["estado"], s3(ls["dem"] / ls["cap"]),
                 s3(max(v_[2] for k_, v_ in Rc.items() if "del tope" in k_ and v_[2] is not None)), s3(rc["tb"]), "cumple" if pl["fu"] <= 1 else "NO cumple"])
table(f"5b. Opción C3: respaldo bajo pastillas con q_c = q_máx/cobertura. FU «Plancha inferior» del núcleo (FEA) frente a mi escalamiento lineal con q (σ_local ∝ q_c = {s3(PL_LOC1)}·q_c, σ_global ∝ q_máx = {s3(PL_GLO1)}·q_máx, cap {s3(PL_CAP)} MPa; calibrado con C1 a cobertura 1, no es un FEA propio)",
      ["cobertura", "q_c MPa", "FU σ_local núcleo", "FU global+local núcleo", "FU propio (escalado)", "Δ %", "estado núcleo", "q_c/q_losa", "FU máx. topes", "t_bz mm", "veredicto"], rows)
PL_AGREE = max(abs(a_[2] / a_[1] - 1) for a_ in fu_pl) <= TOL
FU_PL_VARIES = max(x[1] for x in fu_pl) - min(x[1] for x in fu_pl) > 0.05
FU_PL_DEF = next(x[1] for x in fu_pl if abs(x[0] - 0.9) < 1e-9)
q3_ = rC[3]["q"]
cov_crit = PL_LOC1 * q3_ / (PL_CAP - PL_GLO1 * q3_)
rows = []
for tb_ in TBOT:
    r_ = [tb_]
    for cv_ in COVT:
        DD = export_c({"opt_bz": 1, "bz_conf": 3, "bz_cover": cv_, "t_bot": tb_})
        r_.append(s3(_vv(DD, "Plancha inferior: global + local")["fu"]))
    rows.append(r_)
table("5b'. FU «Plancha inferior: global + local» del núcleo (C3) según t_bot (columnas: cobertura); solo datos del núcleo (el FEA no se replica)", ["t_bot mm"] + [f"cob. {c_}" for c_ in COVT], rows)
print(f"Cobertura crítica (FU = 1) por escalamiento lineal: {s3(cov_crit)}; con la cobertura de proyecto {P['bz_cover']:g}: FU núcleo {s3(FU_PL_DEF)} (escalado {s3(next(x[2] for x in fu_pl if abs(x[0]-0.9)<1e-9))}); "
      f"el término global no se divide por la cobertura (es el momento de la placa completa, que depende de la presión media q_máx)")
Apad = Ac * P["bz_cover"] / P["bz_npad"]
q3 = rC[3]["ND"] * 1e3 / (3 * Apad * (1 - fgC))
Lp = sorted(float(x) for x in P["rings"].replace(";", ",").split(",") if x.strip()); Lpan = Lp[-1] - Lp[-2]
Dpl = P["E"] * P["t_bot"] ** 3 / (12 * (1 - 0.3 ** 2)); dpan = rC[3]["qloc"] * Lpan ** 4 / (384 * Dpl)
print(f"Contacto con 3 pastillas (planitud): q_neto = N_D/(3·A_pastilla·(1−f_g)) = {s3(q3)} MPa frente a p_bz {P['p_bz']:g} (FU {s3(q3/P['p_bz'])}); compliancia por compresión del bronce+disco bajo q_loc = "
      f"{s3(rC[3]['qloc']*(rC[3]['tb']/E_BZ+rC[3]['tr']/E_SS)*1e3)} µm; flecha de un panel de la plancha inferior entre anillos (tira empotrada, L = {s3(Lpan)} mm, t = {P['t_bot']:g}) = {s3(dpan)} mm (cota) "
      f"frente a la planitud de fabricación 0,20 mm: el reparto entre pastillas lo gobierna la flexibilidad del respaldo, no la compresión del bronce")

# ---- (c) μ, adherencia–deslizamiento
rr_ = rC[1]; Nc = rr_["N"]
rows = []
for mu_ in (0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30):
    T_ = par(P, Nc, mu_, P["r_ef"]); F_ = FU_ * T_ / n / 1e3
    rows.append([mu_, s3(T_ / 1e6), s3(F_), s3(F_st / 1e3 / F_), s3(F_ * 1e3 / A_b * 10), "gira" if F_ <= F_st / 1e3 else "NO gira", "cumple FS_mín" if F_st / 1e3 / F_ >= P["FS_min"] else "FS < FS_mín"])
table(f"5c. FS de giro de C frente al μ (r_ef = {P['r_ef']:g} mm, N = {s3(Nc)} kN, FS_mín = {P['FS_min']})", ["μ", "T kN·m", "F cil kN", "FS", "p bar", "gira", "FS_mín"], rows)
mu_lim_fsmin = None
lo_, hi_ = 0.05, 0.6
for _ in range(60):
    mid = (lo_ + hi_) / 2; F_ = FU_ * par(P, Nc, mid, P["r_ef"]) / n / 1e3
    lo_, hi_ = (mid, hi_) if F_st / 1e3 / F_ >= P["FS_min"] else (lo_, mid)
mu_lim_fsmin = lo_
mu_stall = F_st / (FU_ * par(P, Nc, 1.0, P["r_ef"]) / n)
Es = 210000.0; A_rod = math.pi / 4 * P["d_rod"] ** 2
m_load = P["W_tf"] * 1000.0; R_L = P["D_load"] / 2 / 1000
J = 0.5 * m_load * R_L ** 2 + 0.5 * (D0["derivados"]["masas"]["disc"] + rr_["m_rot"]) * (Ro / 1000) ** 2        # kg·m²
r_ef_m = P["r_ef"] / 1000; m_eq = J / r_ef_m ** 2
V = 2.5e-3                                                                                                 # m/s (valor del enunciado), medido en r_ef
SC = [("vástago Ø63 solo (aceite rígido), L = stroke + c_rod", None, None, P["stroke"] + P["c_rod"]),
      ("aceite rígido (β = 1500 MPa, V = A·20 + 0,2 L) + vástago L = 345", 1500.0, P["D_bore"] and (A_b * 20 + 0.2e6), P["stroke"] + P["c_rod"]),
      ("aceite nominal (β = 1000, V = A·(carrera/2 + 20) + 0,6 L) + vástago L = 550", 1000.0, A_b * (P["stroke"] / 2 + 20) + 0.6e6, 550.0),
      ("aceite blando (β = 1000, V = A·(carrera + 20) + 1,0 L) + vástago L = 755", 1000.0, A_b * (P["stroke"] + 20) + 1.0e6, P["L0"] + P["stroke"])]
rows = []; SS_OUT = []
for nm, beta, Vol, Lr in SC:
    k_rod = Es * A_rod / Lr                                       # N/mm
    k_oil = beta * A_b ** 2 / Vol if beta else math.inf
    k_cyl = 1 / (1 / k_rod + (0 if not beta else 1 / k_oil))
    K_th = n * k_cyl * a_min ** 2 * 1e3 / 1e6                      # N·m/rad  (k N/mm → N/m ×1e3; a mm → m ×1e-6)
    k_lin = K_th / r_ef_m ** 2                                     # N/m en r_ef
    w_n = math.sqrt(K_th / J)
    sk = math.sqrt(k_lin * m_eq)
    dmc = {z: 2 * z * V * sk / (Nc * 1e3) for z in (0.1, 0.3, 0.5)}
    rs = {dc: k_lin * dc * 1e-6 / (Nc * 1e3) for dc in (10, 50)}
    jump = 2 * 0.02 * Nc * 1e3 / k_lin * 1e3
    SS_OUT.append((nm, k_cyl, k_lin, w_n, dmc, rs, jump))
    rows.append([nm[:62], s3(k_cyl), s3(k_lin / 1e6), s3(w_n / (2 * math.pi)), s3(dmc[0.1]), s3(dmc[0.3]), s3(dmc[0.5]), s3(rs[10]), s3(rs[50]), s3(jump)])
table(f"5c'. Adherencia–deslizamiento a V = 2,5 mm/s en r_ef: J = {s3(J)} kg·m² (carga {s3(m_load)} kg, Ø{P['D_load']:g}), m_eq = J/r_ef² = {s3(m_eq)} kg, N = {s3(Nc)} kN; Δμ crítico = 2ζ·V·√(k·m)/N (amortiguamiento viscoso relativo ζ) y por estado-velocidad k·D_c/N",
      ["Rigidez del cilindro", "k_cil N/mm", "k_lin(r_ef) kN/mm", "f_n Hz", "Δμ_c ζ=0,1", "Δμ_c ζ=0,3", "Δμ_c ζ=0,5", "Δμ_c D_c=10 µm", "Δμ_c D_c=50 µm", "salto 2ΔμN/k mm (Δμ=0,02)"], rows)
print(f"Cota de estabilidad: stick-slip si μ_est − μ_cin > Δμ_c. Con ζ ≤ 0,5 el sistema es inestable para Δμ > {s3(min(x[4][0.5] for x in SS_OUT))}–{s3(max(x[4][0.5] for x in SS_OUT))} "
      f"(rigidez de aceite → vástago solo). μ máx que gira {s3(mu_stall)}; μ máx con FS_mín {s3(mu_lim_fsmin)}")


# ---- (d) bronce–bronce: efecto de la aleación de la 2.ª placa sobre espesor, masa, altura y soldadura de mejillas
rows = []
for fy2 in (97, 125, 170, 275):
    PP = dict(PC[2], Fy_bz2=fy2); rr2 = ifaceC(PP, 2)
    rows.append([fy2, s3(rr2["tfR"]), s3(rr2["trReq"]), s3(rr2["tr"]), s3(rr2["delta"]), s3(rr2["mAdd"]), s3(sold_fu(rr2["delta"])), s3(rr2["qnet"]),
                 s3(tauC(PP, AL_BZ, E_BZ, rr2["tr"]) / P["tau_cyc"])])
table("5d. Configuración 2: espesor de la 2.ª placa según su límite elástico (misma aleación del par → misma dureza, el riesgo de gripado no depende de Fy)",
      ["Fy_bz2 MPa", "t_flex mm", "t_req mm", "t adoptado", "Δ mm", "mAdd kg", "FU sold. mejillas", "q_neto MPa", "FU térmico 2.ª placa"], rows)
hb_diff_c1 = P["HB_cara"] - P["HB_bz"]

# ---- (e) retención de las pastillas y del disco
rows = []
r3 = rC[3]; N3 = r3["N"]
for cv_ in (1.0, 0.8, 0.7, 0.627, 0.6, 0.5, 0.4):
    fr = P["mu_back"] * N3 * ru / 1e3; ad = P["tau_bond"] * Ac * cv_ * ru / 1e6
    tau_req = Tmax * 1e6 / (Ac * cv_ * ru)
    rows.append([s3(cv_), s3(fr), s3(ad), s3(max(fr, ad)), s3(Tmax / max(fr, ad)), s3(tau_req), s3(Tmax / (N3 * ru / 1e3)), "cumple" if Tmax <= max(fr, ad) + 1e-9 else "NO cumple"])
table(f"5e. (solo fix_mode = 2, pegado) Retención de las pastillas con T_calado = {s3(Tmax)} kN·m (μ_resp = {P['mu_back']}, τ_pegado = {P['tau_bond']} MPa, N = {s3(N3)} kN, r_u = {s3(ru)} mm)",
      ["cobertura", "fricción kN·m", "pegado kN·m", "máx (núcleo)", "FU", "τ necesaria MPa (solo pegado)", "μ_resp necesario (solo fricción)", "veredicto"], rows)
cover_min = Tmax / (P["tau_bond"] * Ac * ru / 1e6)
cover_min_core = None
Tdrag = {c_: casos_c(P, N3)[c_]["mu"] * N3 * casos_c(P, N3)[c_]["r"] / 1e3 for c_ in ("dis", "cont", "seco")}
print(f"Cobertura mínima con pegado solo = T_calado/(τ·A_c·r_u) = {s3(cover_min)}; con cobertura 0,5 FU = {s3(Tmax/max(P['mu_back']*N3*ru/1e3, P['tau_bond']*Ac*0.5*ru/1e6))} (fricción {s3(P['mu_back']*N3*ru/1e3)} kN·m ya no basta). "
      f"Par real de arrastre μ·N·r: diseño {s3(Tdrag['dis'])}, contaminado {s3(Tdrag['cont'])}, seco {s3(Tdrag['seco'])} kN·m (< fricción de respaldo {s3(P['mu_back']*N3*ru/1e3)}): "
      f"la retención por T_calado es un caso de bloqueo (el cilindro llega al alivio), no la acción normal. Fuerza de arrastre sobre las pastillas μ_máx·N = {s3(max(P['muC_d'], P['muC_cont'], P['muC_dry'])*N3)} kN; "
      f"τ de arrastre = {s3(max(P['muC_d'], P['muC_cont'], P['muC_dry'])*N3*1e3/(Ac*P['bz_cover']))} MPa sobre el área de pastillas (pegado {P['tau_bond']} MPa)")

# ---- (f) izaje: flecha de la base con y sin las piezas de la interfaz (plancha de Reissner–Mindlin con 4 puntos de izaje, MITC4)
def mitc4_K(h, E_, nu_, t_, kappa=5 / 6):
    xi_n = np.array([-1, 1, 1, -1.]); et_n = np.array([-1, -1, 1, 1.])
    D_ = E_ * t_ ** 3 / (12 * (1 - nu_ ** 2)); Db = D_ * np.array([[1, nu_, 0], [nu_, 1, 0], [0, 0, (1 - nu_) / 2]]); Ds = kappa * E_ / (2 * (1 + nu_)) * t_
    Nf = lambda xi, et: 0.25 * (1 + xi_n * xi) * (1 + et_n * et)
    dN = lambda xi, et: (0.25 * xi_n * (1 + et_n * et) * 2 / h, 0.25 * et_n * (1 + xi_n * xi) * 2 / h)
    def Bx(xi, et):
        b = np.zeros(12); dx, dy = dN(xi, et); b[0::3] = dx; b[1::3] = Nf(xi, et); return b
    def By(xi, et):
        b = np.zeros(12); dx, dy = dN(xi, et); b[0::3] = dy; b[2::3] = Nf(xi, et); return b
    gA, gC, gD, gB = Bx(0, 1), Bx(0, -1), By(1, 0), By(-1, 0); K_ = np.zeros((12, 12)); g_ = 1 / math.sqrt(3); w_ = (h / 2) ** 2
    for xi in (-g_, g_):
        for et in (-g_, g_):
            dx, dy = dN(xi, et); Bb = np.zeros((3, 12)); Bb[0, 1::3] = dx; Bb[1, 2::3] = dy; Bb[2, 1::3] = dy; Bb[2, 2::3] = dx
            K_ += Bb.T @ Db @ Bb * w_
            gx = 0.5 * (1 + et) * gA + 0.5 * (1 - et) * gC; gy = 0.5 * (1 + xi) * gD + 0.5 * (1 - xi) * gB
            K_ += Ds * (np.outer(gx, gx) + np.outer(gy, gy)) * w_
    return K_


try:
    import scipy.sparse as _sp, scipy.sparse.linalg as _spl
except Exception:
    _sp = None


def plate_lift(PP, m, nel):
    """Placa cuadrada B×B de espesor t_base, libre en el borde, apoyada en 4 puntos de izaje (x = ±x_lug, y = ±(B/2 − c_lug), apoyo rígido en w de ±75 mm); carga = φ_izaje·g·masa:
    base + marco + ménsulas + patines + bancadas uniformes en B²; mesa + pivote + uñas + cilindros + piezas de interfaz sobre el círculo Ø D_top."""
    B_ = PP["B"]; a_ = B_ / 2; Rd = PP["D_top"] / 2; h = B_ / nel; nn = nel + 1
    own = m["base"] + m["rim"] + m["brackets"] + m["shoes"] + m["beds"]
    oth = m["disc"] + m["pivot"] + m["dogs"] + m["cyl"] + m["ss"] + m["uhmw"] + m["bz"]
    qo = PP["phi_lift"] * own * g0 / B_ ** 2; qd = PP["phi_lift"] * oth * g0 / (math.pi * Rd ** 2)
    Ke = mitc4_K(h, PP["E"], PP["nu"], PP["t_base"])
    idx = np.arange(nn * nn).reshape(nn, nn)
    el = np.array([[idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]] for i in range(nel) for j in range(nel)])
    dof = np.stack([el * 3, el * 3 + 1, el * 3 + 2], axis=2).reshape(len(el), 12)
    rows_ = np.repeat(dof, 12, axis=1).ravel(); cols_ = np.tile(dof, (1, 12)).ravel(); vals_ = np.tile(Ke.ravel(), len(el)); nd = 3 * nn * nn
    xc = -a_ + h * (np.arange(nel) + 0.5); F_ = np.zeros(nd)
    for i in range(nel):
        for j in range(nel):
            q_ = (qo + (qd if math.hypot(xc[i], xc[j]) <= Rd else 0.0)) * h * h / 4
            for nd_ in el[i * nel + j]:
                F_[3 * nd_] += q_
    xs = -a_ + h * np.arange(nn); fixed = set()
    for sx in (1, -1):
        for sy in (1, -1):
            lx, ly = sx * PP["x_lug"], sy * (a_ - PP["c_lug"])
            for i in np.where(abs(xs - lx) <= 75 + 1e-9)[0]:
                for j in np.where(abs(xs - ly) <= 75 + 1e-9)[0]:
                    fixed.add(3 * idx[i, j])
    fixed = np.array(sorted(fixed)); free = np.setdiff1d(np.arange(nd), fixed); u = np.zeros(nd)
    if _sp is not None:
        K_ = _sp.csr_matrix((vals_, (rows_, cols_)), shape=(nd, nd)); u[free] = _spl.spsolve(K_[free][:, free].tocsc(), F_[free])
    else:
        K_ = np.zeros((nd, nd)); np.add.at(K_, (rows_, cols_), vals_); u[free] = np.linalg.solve(K_[np.ix_(free, free)], F_[free])
    return float(np.max(np.abs(u[0::3]))), float(F_.sum())


ALT = [("0 acero–acero", {}), ("A inox–inox", {"opt_ss": 1}), ("B inox + UHMW", {"opt_uhmw": 1}), ("C1 bronce + disco", {"opt_bz": 1, "bz_conf": 1}),
       ("C2 bronce + 2.ª placa", {"opt_bz": 1, "bz_conf": 2}), ("C3 pastillas + disco", {"opt_bz": 1, "bz_conf": 3})]
prefetch([dict(o, c_lug=cl) for _, o in ALT for cl in (50, 150)])
NEL = 96 if _sp is not None else 40
rows = []; fl_core_max = 0.0; LIFT = {}
for nm, o in ALT:
    for cl in (50, 150):
        DD = export_c(dict(o, c_lug=cl))
        fl = next(v for v in DD["verificaciones"] if "Izaje: flecha de la base" in v["nombre"])
        wm, Fsum = plate_lift(DD["P"], DD["derivados"]["masas"], NEL) if np is not None else (float("nan"), float("nan"))
        Fexp = DD["P"]["phi_lift"] * g0 * DD["derivados"]["masas"]["total"] / 1e3
        lim = DD["P"]["B"] / 300
        LIFT[(nm, cl)] = (fl["dem"], fl["fu"], wm, wm / lim)
        rows.append([nm, cl, s3(DD["derivados"]["masas"]["total"]), s3(fl["dem"]), s3(fl["fu"]), s3(wm), s3(wm / lim), f"{(wm/fl['dem']-1)*100:+.1f}", f"{(Fsum/1e3/Fexp-1)*100:+.2f}",
                     ("SOBRE B/300" if fl["fu"] > 1 else "cumple") + " (núcleo) / " + ("sobre" if wm / lim > 1 else "cumple") + " (propio)"])
table(f"5f. Izaje: flecha de la base (límite B/300 = {s3(P['B']/300)} mm) con c_lug = 50 y 150 mm; plancha de Mindlin (MITC4, {NEL}×{NEL}) propia frente a núcleo",
      ["Alternativa", "c_lug", "masa total kg", "w núcleo mm", "FU núcleo", "w propio mm", "FU propio", "Δ w %", "Σ cargas / φ g m −1 %", "Veredicto"], rows)
conv = []
for nel in ((32, 64, 96, 128) if _sp is not None else (16, 24, 32)):
    if np is None:
        break
    d0_ = export_c({}); conv.append((nel, plate_lift(d0_["P"], d0_["derivados"]["masas"], nel)[0], plate_lift(DC[1]["P"], DC[1]["derivados"]["masas"], nel)[0]))
print("Convergencia de malla (c_lug = 150): " + "; ".join(f"n = {a_}: op.0 {s3(b_)} mm, C1 {s3(c_)} mm (C1/op.0 = {c_/b_:.3f})" for a_, b_, c_ in conv)
      + f"; núcleo: op.0 {s3(LIFT[('0 acero–acero',150)][0])}, C1 {s3(LIFT[('C1 bronce + disco',150)][0])} mm (C1/op.0 = {LIFT[('C1 bronce + disco',150)][0]/LIFT[('0 acero–acero',150)][0]:.3f})")
fu_lift_c = [v[1] for k, v in LIFT.items() if k[1] == 150]
fl_all = [v["fu"] for DDx in _EXP.values() if DDx is not None and DDx["P"].get("opt_bz") == 1 and DDx["P"]["c_lug"] == 150 for v in DDx["verificaciones"] if "Izaje: flecha de la base" in v["nombre"]]
print(f"FU de «Izaje: flecha de la base» con c_lug = 150 en las 4 alternativas: 0 {s3(LIFT[('0 acero–acero',150)][1])}, A {s3(LIFT[('A inox–inox',150)][1])}, B {s3(LIFT[('B inox + UHMW',150)][1])}, "
      f"C {s3(LIFT[('C1 bronce + disco',150)][1])} (C2 {s3(LIFT[('C2 bronce + 2.ª placa',150)][1])}, C3 {s3(LIFT[('C3 pastillas + disco',150)][1])}); máximo en los {len(fl_all)} puntos de los barridos de C: {s3(max(fl_all))}")

# ---- (g) altura del eje y soldadura de mejillas, mejilla en flexión
rows = []
for nm, o in ALT:
    DD = export_c(o); ifc = DD["escenarios"]["ifaces"]
    Dl = DD["apoyo"]["interfaz"]["delta"] if DD["apoyo"]["interfaz"].get("o") == 3 else (DD["apoyo"]["interfaz"].get("delta") or 0.0)
    sw = next(v for v in DD["verificaciones"] if "Soldadura mejillas–base (4" in v["nombre"]); mj = next(v for v in DD["verificaciones"] if "Mejilla de la ménsula" in v["nombre"])
    cmp_val("5g", f"{nm} · soldadura mejillas dem", soldadura_mejilla(Dl), sw["dem"]); cmp_val("5g", f"{nm} · soldadura mejillas FU", sold_fu(Dl), sw["fu"])
    rows.append([nm, s3(Dl), s3(P["h_disc"] / 2 + Dl), s3(soldadura_mejilla(Dl)), s3(sw["dem"]), s3(sold_fu(Dl)), s3(sw["fu"]), sw["estado"], s3(mj["fu"])])
Dmax_w2 = 0.0; lo_, hi_ = 0.0, 200.0
for _ in range(60):
    mid = (lo_ + hi_) / 2; lo_, hi_ = (mid, hi_) if soldadura_mejilla(mid) <= cap_w else (lo_, mid)
Dmax_w2 = lo_
table(f"5g. Altura que agrega la interfaz y soldadura mejillas–base (cap {s3(cap_w)} MPa); Δ_máx con FU = 1: {s3(Dmax_w2)} mm", ["Alternativa", "Δ mm", "h_eje mm", "f propio MPa", "f núcleo MPa", "FU propio", "FU núcleo", "estado", "FU mejilla flexión"], rows)


# ---- límites analíticos de p_bz, k_bz, PV_bz (fuera del rango admitido por el núcleo) y sensibilidades de desgaste
rows = []; FUW = {}; KCRIT2 = {}
sl_ = P["life"] * P["turns_yr"] * 2 * math.pi * P["r_ef"] / 1000
for c in (1, 2, 3):
    r = rC[c]; reserva = r["tb"] - r["tfB"] / math.sqrt(r["eta"])
    k_res = reserva / (r["qnet"] * sl_ * 1e-7); k_dep = (0.7 * r["tb"] - 2) / (r["qnet"] * sl_ * 1e-7)
    v_e = Ro * vcil(P) / a_min / 1000
    res2 = min(r["tb"] - r["tbReq"], r["gr"] if r["gr"] > 0 else math.inf)      # reserva útil: sin sobreespesor de relapeado ni ranura (las ranuras desaparecen con h = h_gr)
    FUW[c] = P["k_bz"] * 1e-7 * r["qnet"] * sl_ * (Ro / P["r_ef"]) / res2
    KCRIT2[c] = res2 / (r["qnet"] * sl_ * 1e-7 * (Ro / P["r_ef"]))
    rows.append([c, s3(r["qnet"]), s3(r["qnet"]), s3(P["PV_bz"] / v_e), s3(min(k_res, k_dep)), s3(KCRIT2[c]), "5–60", "0,05–3", "0,1–500", s3(FUW[c])])
table("5h. Límites analíticos: valor del parámetro con FU = 1 frente al rango admitido por el núcleo (p_bz [5; 60], PV_bz [0,05; 3], k_bz [0,1; 500]); corregido = reserva t_bz − t_req (sin relapeado ni ranura; ≤ h_gr) y s medido en R_o",
      ["conf", "q_neto MPa", "p_bz crítico MPa", "PV_bz crítico MPa·m/s", "k_bz crítico núcleo (×1e-7)", "k_bz crítico corregido", "rango p_bz", "rango PV_bz", "rango k_bz", "FU desgaste corregido"], rows)

# ======================================================================================
# 5i. Fijación por sectores con topes: revisión crítica de la fuerza por tope y de los modos de falla no verificados
# ======================================================================================
try:
    import scipy.sparse as _sp2, scipy.sparse.linalg as _spl2
except Exception:
    _sp2 = None


def sector_fe(b, Lr, t, F, L, nx, ny, E_, nu_=0.3):
    """Sector rectangular b (x, circunferencial) × Lr (y, radial), tensión plana: la fricción de la cara se reparte uniforme (fuerza de volumen en x) y el tope reacciona en x = 0 en |y − Lr/2| ≤ L/2.
    Devuelve σ_vm por elemento (MPa)."""
    hx, hy = b / nx, Lr / ny
    D_ = E_ / (1 - nu_ ** 2) * np.array([[1, nu_, 0], [nu_, 1, 0], [0, 0, (1 - nu_) / 2]])
    g_ = 1 / math.sqrt(3); Ke = np.zeros((8, 8)); xi_n = np.array([-1, 1, 1, -1.]); et_n = np.array([-1, -1, 1, 1.])
    for xi in (-g_, g_):
        for et in (-g_, g_):
            dN = np.array([xi_n * (1 + et_n * et) / 4 * 2 / hx, et_n * (1 + xi_n * xi) / 4 * 2 / hy])
            B = np.zeros((3, 8)); B[0, 0::2] = dN[0]; B[1, 1::2] = dN[1]; B[2, 0::2] = dN[1]; B[2, 1::2] = dN[0]
            Ke += B.T @ D_ @ B * t * hx * hy / 4
    nn_ = (nx + 1) * (ny + 1); idx = np.arange(nn_).reshape(nx + 1, ny + 1)
    el = np.array([[idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]] for i in range(nx) for j in range(ny)])
    dof = np.stack([el * 2, el * 2 + 1], axis=2).reshape(len(el), 8)
    rows_ = np.repeat(dof, 8, axis=1).ravel(); cols_ = np.tile(dof, (1, 8)).ravel(); vals_ = np.tile(Ke.ravel(), len(el))
    f_ = np.zeros(2 * nn_)
    for e_ in el:
        for n_ in e_:
            f_[2 * n_] += -F / (nx * ny) / 4
    ys = np.arange(ny + 1) * hy
    fixed = [2 * idx[0, j] for j in range(ny + 1) if abs(ys[j] - Lr / 2) <= L / 2 + 1e-9] + [2 * idx[0, ny // 2] + 1]
    fixed = np.array(sorted(set(fixed))); free = np.setdiff1d(np.arange(2 * nn_), fixed); u = np.zeros(2 * nn_)
    if _sp2 is not None:
        K_ = _sp2.csr_matrix((vals_, (rows_, cols_)), shape=(2 * nn_, 2 * nn_)); u[free] = _spl2.spsolve(K_[free][:, free].tocsc(), f_[free])
    else:
        K_ = np.zeros((2 * nn_, 2 * nn_)); np.add.at(K_, (rows_, cols_), vals_); u[free] = np.linalg.solve(K_[np.ix_(free, free)], f_[free])
    dN0 = np.array([xi_n / 4 * 2 / hx, et_n / 4 * 2 / hy]); B0 = np.zeros((3, 8)); B0[0, 0::2] = dN0[0]; B0[1, 1::2] = dN0[1]; B0[2, 0::2] = dN0[1]; B0[2, 1::2] = dN0[0]
    vm = []
    for d_ in dof:
        s_ = D_ @ (B0 @ u[d_]); vm.append(math.sqrt(s_[0] ** 2 - s_[0] * s_[1] + s_[1] ** 2 + 3 * s_[2] ** 2))
    return np.array(vm)


rA_, rB2_, r1_, r2_, r3_ = iface(P, 1), iface(P, 2), rC[1], rC[2], rC[3]
nsec, nbz = P["n_sec"], P["bz_npad"]
# (opción, pieza, n, t, Fy, sobreespesor, respaldo, N [kN], E, α, masa del pieza completa [kg], en la mesa?)
PIEZAS = [("A", "disco de la base", nsec, rA_["tss"], P["Fy_ss"], P["ss_allow"], P["t_base"], rA_["N"], E_SS, False),
          ("A", "disco de la mesa", nsec, rA_["tss2"], P["Fy_ss"], P["ss_allow"], P["t_bot"], rA_["N"], E_SS, True),
          ("B", "disco de la base", nsec, rB2_["tss"], P["Fy_ss"], P["ss_allow"], P["t_base"], rB2_["N"], E_SS, False),
          ("B", "disco de la mesa", nsec, rB2_["tss2"], P["Fy_ss"], P["ss_allow"], P["t_bot"], rB2_["N"], E_SS, True),
          ("C1", "placa de bronce", nsec, r1_["tb"], P["Fy_bz"], P["bz_allow"], P["t_base"], r1_["N"], E_BZ, False),
          ("C1", "disco duro", nsec, r1_["tr"], P["Fy_cara"], P["ss_allow"], P["t_bot"], r1_["N"], E_SS, True),
          ("C2", "2.ª placa de bronce", nsec, r2_["tr"], P["Fy_bz2"], P["bz_allow"], P["t_bot"], r2_["N"], E_BZ, True),
          ("C3", "pastillas de bronce", nbz, r3_["tb"], P["Fy_bz"], P["bz_allow"], P["t_base"], r3_["N"], E_BZ, False)]
qr_core = q_ratio(P); Ro_p, Ri_p, A_p, I_p, ru_p = geom(P)
chord_ru = lambda n_: 2 * ru_p * math.sin(math.pi / n_)
ratio_sec = lambda n_: 1 + P["e"] * A_p / I_p * ru_p * math.sin(math.pi / n_) / (math.pi / n_)
bt_ = 2 * P["w_tope"]; aw_ = 0.707 * P["w_tope"]
rows1, rows2, rows3 = [], [], []
FU_ECC = {}; FU_HC = {}; FU_OV = {}; FU_BK = {}; FU_SC = {}
for opt, nm, n_, t_, Fy_, alw_, tb_, N_, E_, mesa_ in PIEZAS:
    F = F_tope(P, n_); c = tope_calc(P, F, t_, Fy_); cap1 = aw_ * c["Fw"]
    hc = t_ - alw_; e_ = hc / 2; v = F / (2 * c["L"]); nn1 = F * e_ / (bt_ * c["L"])
    fu_core = v / cap1; fu_ecc = math.hypot(v, nn1) / cap1
    bt_req = F * e_ / (c["L"] * math.sqrt(cap1 ** 2 - v ** 2)) if v < cap1 else math.inf
    fu_hc = F / (c["L"] * hc) / c["adm"]; fu_hc1 = F / (c["L"] * (hc - 1)) / c["adm"] if hc > 1 else math.inf
    Fsec = F / qr_core * ratio_sec(n_); mu_eq = Tmax * 1e3 / (ru_p / 1e3) / (N_ * 1e3)
    muT = {"A": P["muA_dry"], "B": max(P["muB_d"], P["muB_cont"], P["muB_dry"])}.get(opt, max(P["muC_d"], P["muC_cont"], P["muC_dry"]))
    Fmu = muT * N_ * 1e3 / n_ * ratio_sec(n_)
    qmin = {"A": rA_["ND"], "B": rB2_["ND"], "C1": r1_["ND"], "C2": r2_["ND"], "C3": r3_["ND"]}[opt] * 1e3 / A_p * (2 - qr_core)
    Mov = F * (t_ - hc / 2); Mres = qmin * (Ro_p - Ri_p) * chord_ru(n_) ** 2 / 6
    m_ = F * (hc / 2 + tb_ / 2) / (c["L"] + 2 * tb_); sig_pl = 6 * m_ / tb_ ** 2
    Pm = {1: 20.1, 4: 8.78, 5: 14.2, 6: 20.1, 8: 36.6, 10: 58.0, 12: 84.3}.get(int(P["d_tor"]), 0.7854 * (0.9 * P["d_tor"]) ** 2)
    wsec = (RHO_SS if E_ == E_SS else P["rho_bz"] * 1e-6) * A_p * t_ / n_ * g0 * P["phi_lift"]
    cap_scr = 2 * 0.75 * 800 * Pm / 2.0
    key_ = f"{opt} · {nm}"
    FU_ECC[key_] = fu_ecc; FU_HC[key_] = (fu_hc, fu_hc1); FU_OV[key_] = Mov / Mres; FU_BK[key_] = sig_pl / (0.6 * P["Fy"]); FU_SC[key_] = wsec / cap_scr if mesa_ else 0.0
    rows1.append([key_, n_, s3(F / 1e3), s3(Fsec / 1e3), s3((Fsec / F - 1) * 100), s3(Fmu / 1e3), s3(mu_eq), s3(c["L"]), s3(c["sig"]), s3(c["sig"] / c["adm"])])
    rows2.append([key_, s3(t_), s3(c["L"]), s3(fu_core), s3(fu_ecc), s3(bt_req), s3(fu_hc), s3(fu_hc1), s3(Mov / Mres), s3(sig_pl / (0.6 * P["Fy"])), s3(FU_SC[key_])])
table(f"5i.1. Fuerza por tope: F = (T_calado/r_u)/n·(q_máx/q_med) [q_máx/q_med = {s3(qr_core)}] frente a la del sector más cargado (promedio de presión en el sector: {s3(ratio_sec(nsec))}) y a μ_máx·N/n; μ_eq = T_calado/(N·r_u)",
      ["Opción · pieza", "n", "F núcleo kN", "F sector kN", "Δ %", "F μ_máx·N kN", "μ_eq calado", "L_tope mm", "σ aplast. MPa", "FU aplast."], rows1)
table(f"5i.2. Modos de falla no verificados por el núcleo (tope de barra de espesor b = 2·w = {bt_:g} mm; altura de contacto h_c = t − sobreespesor; fuerza en h_c/2): FU de la soldadura con el momento de excentricidad, espesor de barra necesario, aplastamiento con h_c (y con 1 mm más de holgura), vuelco del sector con q_mín, flexión local del respaldo, peso del sector sobre los tornillos de posición al izar",
      ["Opción · pieza", "t mm", "L mm", "FU sold. núcleo", "FU sold. con excentricidad", "b barra necesaria mm", "FU aplast. h_c", "FU aplast. h_c − 1", "FU vuelco", "FU respaldo", "FU tornillos peso"], rows2)
rows3 = []
IP = {}
for opt, nm, n_, t_, Fy_, alw_, tb_, N_, E_, mesa_ in (PIEZAS[0], PIEZAS[4], PIEZAS[6]):
    c = tope_calc(P, F_tope(P, n_), t_, Fy_); vm = sector_fe(chord_ru(n_), Ro_p - Ri_p, t_, F_tope(P, n_), c["L"], 24, 120, E_)
    p95 = float(np.percentile(vm, 95)); IP[f"{opt} · {nm}"] = p95 / Fy_
    rows3.append([f"{opt} · {nm}", s3(F_tope(P, n_) / 1e3), s3(c["L"]), s3(F_tope(P, n_) / ((Ro_p - Ri_p) * t_)), s3(float(np.median(vm))), s3(p95), s3(p95 / Fy_), s3(p95 / (0.6 * Fy_))]) if np is not None else None
if rows3:
    table("5i.3. Tensión en el plano del sector (tensión plana, fricción uniforme, tope centrado de largo L; los máximos puntuales son singulares y dependen de la malla: se informa el percentil 95)",
          ["Opción · pieza", "F kN", "L mm", "F/(L_rad·t) MPa", "σ_vm mediana", "σ_vm p95", "p95/Fy", "p95/(0,6·Fy)"], rows3)
# invariancia de la opción 0 frente a los parámetros nuevos
ok0 = True
for ov in ({"fix_mode": 2}, {"h_gr": 0, "n_sec": 48, "w_tope": 16, "n_seg": 48, "d_tor": 12, "L_tope": 400}):
    DDx = export_c(ov)
    if DDx is None:
        ok0 = False; continue
    m0 = {v["nombre"]: v for v in D0["verificaciones"]}; d_ = 0
    for v in DDx["verificaciones"]:
        o_ = m0.get(v["nombre"])
        if o_ is None or any((v.get(k_) is None) != (o_.get(k_) is None) or (v.get(k_) is not None and abs(v[k_] - o_[k_]) > 1e-12 * max(1.0, abs(o_[k_]))) for k_ in ("dem", "cap", "fu")):
            d_ += 1
    d_ += sum(1 for k_ in D0["derivados"]["masas"] if abs(D0["derivados"]["masas"][k_] - DDx["derivados"]["masas"][k_]) > 1e-9)
    comp("5i", f"opción 0 invariante frente a {list(ov)} (verificaciones y masas)", 1.0 if d_ == 0 else 0.0, 1.0)
    ok0 = ok0 and d_ == 0
print(f"Opción 0 sin cambios frente a los parámetros de fijación y ranuras (fix_mode = 2; h_gr = 0, n_sec, w_tope, n_seg, d_tor, L_tope extremos): {'sí' if ok0 else 'NO'}")
print(f"Fuerza por tope: el factor q_máx/q_med = {s3(qr_core)} sobreestima en {s3((qr_core/ratio_sec(nsec)-1)*100)} % la presión media del sector más cargado ({s3(ratio_sec(nsec))}); "
      f"T_calado/r_u equivale a μ = {s3(Tmax*1e3/(ru_p/1e3)/(rA_['N']*1e3))} en r_u frente a μ_dry de C {P['muC_dry']}: diseño por capacidad del accionamiento (válido y conservador)")

# ======================================================================================
# 6. Hallazgos de la opción C
# ======================================================================================
rr1, rr3 = rC[1], rC[3]
# --- cierres verificados (hallazgos de la revisión anterior que el núcleo ya corrigió): si la comprobación falla, reaparecen como hallazgo
CIERRES = []
rr3 = rC[3]
cl_c1 = FU_PL_VARIES and PL_AGREE
CIERRES.append(("C1", "q_c = q_máx/cobertura en FEA plancha inferior, flexión global y losa", cl_c1,
                f"FU plancha inferior C3 con cobertura 0,5–1,0: {', '.join(s3(x[1]) for x in fu_pl)}; mi escalamiento coincide ≤ 0,1 %: {PL_AGREE}"))
FIND.append(("C1", "menor" if cl_c1 else "importante",
             ("Plancha inferior de la mesa en C3: corregida (q_c = q_máx/cobertura en el FEA, en la flexión global y en la losa); el margen con cobertura 0,9 es estrecho y el FU depende de t_bot, W_tf y la cobertura"
              if cl_c1 else "Plancha inferior de la mesa en C3: el núcleo no escala con q_loc o no coincide con mi cota lineal"),
             f"FU plancha inferior {s3(FU_PL_DEF)} (cobertura {P['bz_cover']:g}, «warn»); cobertura 0,5/0,6/0,7/0,8: {', '.join(s3(x[1]) for x in fu_pl[:4])}; losa q_c/q_losa {s3(rr3['qloc']/P['q_floor'])}",
             f"cobertura crítica {s3(cov_crit)} (FU = 1); con 0,7 se necesita t_bot ≥ 20 (tabla 5b'); σ_global no se divide por la cobertura (correcto); 3 pastillas en contacto: q_neto {s3(q3)} MPa (FU {s3(q3/P['p_bz'])}); "
             "FU = 1 también con W_tf ≥ " + ", ".join(f"{s3(u[2])} tf en C{u[1]}" for u in UM if u[0] == "W_tf" and any("Plancha" in x for x in u[4][2]) and not any("Plancha" in x for x in u[3][2])) + f"; exigir rectificado en conjunto (planitud 0,20 mm ≈ flecha del panel entre anillos {s3(dpan)} mm) y no bajar la cobertura de 0,85 sin subir t_bot"))
FIND.append(("C2", "menor", "Adherencia–deslizamiento (fila «pend» del núcleo con dem = 0) y μ de arranque: no hay cota. Con la rigidez del aceite el sistema es inestable para Δμ = μ_est − μ_cin mayor que Δμ_c; no existe μ_est entre los μ de C",
             f"pend; μ = {P['muC_nom']} / {P['muC_d']} / {P['muC_cont']} / {P['muC_dry']}",
             f"Δμ_c = 2ζ·V·√(k·m)/N a 2,5 mm/s: {s3(SS_OUT[3][4][0.5])} (aceite blando) a {s3(SS_OUT[0][4][0.5])} (vástago Ø63 solo) con ζ = 0,5; {s3(SS_OUT[3][4][0.1])}–{s3(SS_OUT[0][4][0.1])} con ζ = 0,1 (J = {s3(J)} kg·m², k_lin = {s3(SS_OUT[3][2]/1e6)}–{s3(SS_OUT[0][2]/1e6)} kN/mm en r_ef); "
             f"el bronce–grafito suele dar Δμ ≈ 0,01–0,05 → adherencia–deslizamiento probable con saltos de {s3(SS_OUT[3][6])} mm (Δμ = 0,02, aceite blando). μ máx que gira {s3(mu_stall)}; con FS_mín {s3(mu_lim_fsmin)}: "
             "subir μ_d de proyecto a 0,20 (FS 1,38 ≥ 1,25; μ_cont ya es 0,20), exigir ensayo de μ_est tras reposo y a 2,5 mm/s en el prototipo, mangueras cortas y contrapresión/estrangulación en la línea de empuje"))
cs_c = casos_c(P, Nc)
cl_c3 = P["muC_nom"] <= P["muC_d"] <= P["muC_cont"] <= P["muC_dry"]
CIERRES.append(("C3", "μ de C monótonos (nom ≤ diseño ≤ contaminado ≤ seco)", cl_c3, f"μ = {P['muC_nom']} / {P['muC_d']} / {P['muC_cont']} / {P['muC_dry']}; FS cont {s3(cs_c['cont']['FS'])}, seco {s3(cs_c['seco']['FS'])}"))
FIND.append(("C3", "menor" if cl_c3 else "importante",
             ("μ de C ya monótonos (0,08 / 0,15 / 0,20 / 0,25); el caso «seco» (r_u) es ahora " + ("el más severo" if cs_c['seco']['FS'] < cs_c['cont']['FS'] else "menos exigente que el «contaminado» (r_ef)") + f" con FS {s3(cs_c['seco']['FS'])} frente a {s3(cs_c['cont']['FS'])}" if cl_c3
              else "μ de C no monótonos: μ_seco o μ_cont menores que el anterior"),
             f"FS dis {s3(cs_c['dis']['FS'])}, cont {s3(cs_c['cont']['FS'])}, seco {s3(cs_c['seco']['FS'])}; μ máx que gira {s3(F_st / (FU_ * par(P, Nc, 1.0, P['r_ef']) / n))}",
             f"con μ = 0,25 en r_ef FS {s3(F_st/1e3/(FU_*par(P, Nc, 0.25, P['r_ef'])/n/1e3))} (< FS_mín) y 0,28 no gira; el μ de arranque tras reposo sigue sin cota (C2)"))
FIND.append(("C4", "menor", "Área de grafito f_g = 14,5 % por debajo del 25–35 % usual de los bronces con insertos de grafito (confirmar con el proveedor); el μ = 0,15 depende de la película de transferencia",
             f"Ø{P['bz_plug_d']:g}, paso {P['bz_plug_p']:g}, f_g {s3(fgC)}, η {s3(etaC)}",
             f"Ø12 con paso 20: f_g {s3(fg_of(dict(P, bz_plug_p=20)))}, η {s3(eta_of(dict(P, bz_plug_p=20)))}: t_bz C1 {s3(com(ifaceC(dict(PC[1], bz_plug_p=20), 1)['tbReq'], COM_BZ))} mm (igual Δ), C3 {s3(com(ifaceC(dict(PC[3], bz_plug_p=20), 3)['tbReq'], COM_BZ))} mm (+2 mm)"))
FIND.append(("C5", "menor", "η = (p−d)/p es un criterio de sección neta (estado límite de un bronce dúctil): no cubre la tensión elástica en el borde del agujero (Kt bruto 2,0–3,7); el tapón prensado casi no ayuda a resistencia; en C3 el espesor adoptado tiene " + f"{s3((rC[3]['tb']/rC[3]['tbReq']-1)*100)} % de holgura sobre el requerido",
             f"σ núcleo {s3(RC[1]['Placa de bronce: flexión sobre un vacío local'][0])} (C1), {s3(RC[3]['Placa de bronce: flexión sobre un vacío local'][0])} MPa (C3); t_req C3 {s3(rr3['tbReq'])} → {s3(rr3['tb'])} mm",
             f"σ pico/Fy C1 {s3(Kt_eq0*RC[1]['Placa de bronce: flexión sobre un vacío local'][0]*etaC/P['Fy_bz'])}–{s3(Kt_net_row/etaC*RC[1]['Placa de bronce: flexión sobre un vacío local'][0]*etaC/P['Fy_bz'])}, C3 {s3(Kt_eq0*RC[3]['Placa de bronce: flexión sobre un vacío local'][0]*etaC/P['Fy_bz'])}–{s3(Kt_net_row/etaC*RC[3]['Placa de bronce: flexión sobre un vacío local'][0]*etaC/P['Fy_bz'])}; "
             f"pico ≤ Fy con Kt = 3: t_req {s3(rC[1]['a']*math.sqrt(0.75*rC[1]['qloc']*3/P['Fy_bz'])+P['bz_allow'])} (C1) / {s3(rC[3]['a']*math.sqrt(0.75*rC[3]['qloc']*3/P['Fy_bz'])+P['bz_allow'])} mm (C3), cubierto por el espesor adoptado; pico ≤ 0,6 Fy pediría {s3(com(rC[1]['a']*math.sqrt(0.75*rC[1]['qloc']*3/(0.6*P['Fy_bz']))+P['bz_allow'], COM_BZ))} / {s3(com(rC[3]['a']*math.sqrt(0.75*rC[3]['qloc']*3/(0.6*P['Fy_bz']))+P['bz_allow'], COM_BZ))} mm. "
             "razonable con Ø12 y paso 30 (η = 0,6); mantener d/p ≤ 0,4; en C3 el espesor comercial sube con " + "; ".join((f"{k_} ≥ {s3(v_)}" if v_ == v_ else f"{k_}: sin cambio en el rango barrido") for k_ in ("W_tf", "ss_void") for v_ in [min([u[2] for u in UM if u[0] == k_ and u[1] == 3 and u[4][0] > u[3][0] and u[2] > P[k_]] or [math.nan])])))
FIND.append(("C6", "menor", "Soldadura mejillas–base cerca del límite con la altura agregada Δ (la altura del eje h_disc/2 + Δ sube el momento de las mejillas); en conf. 2 con ss_void ≥ 191 mm incumple",
             f"FU {s3(sold_fu(rr1['delta']))} (C1, C3, Δ = 16), {s3(sold_fu(rC[2]['delta']))} (C2, Δ = 20), «warn»",
             f"Δ_máx con FU = 1: {s3(Dmax_w2)} mm; op. 0 {s3(sold_fu(0))}, A {s3(sold_fu(IF[1]['delta']))} (Δ = {s3(IF[1]['delta'])}), B {s3(sold_fu(IF[2]['delta']))} (Δ = {s3(IF[2]['delta'])}); reforzar los filetes de las mejillas o limitar Δ ≤ 26 mm (ss_void ≤ 180 en C1/C3)"))
FIND.append(("C7", "menor", "Conf. 2: sigue sin verificación de dureza ni de desgaste de la 2.ª placa maciza (bronce–bronce «pend»)",
             "sin fila de dureza ni de desgaste de la 2.ª placa",
             f"aleaciones con ≥ 50 HB de diferencia (placa con tapones la más dura, p. ej. bronce al aluminio/manganeso; placa maciza reemplazable de bronce al plomo-estaño), Ra ≤ 0,4–0,8 µm, rodaje con grafito; "
             f"una 2.ª placa de Fy ≥ 275 MPa reduce a 6 mm (Δ {s3(ifaceC(dict(PC[2], Fy_bz2=275), 2)['delta'])} mm, −{s3(rC[2]['mAdd']-ifaceC(dict(PC[2], Fy_bz2=275), 2)['mAdd'])} kg)"))
FIND.append(("C8", "menor", "HB_bz es un dato independiente de Fy_bz: con Fy_bz = 415 MPa (HB real ≈ 200–225) la fila de dureza sigue en 330 − 100",
             f"HB_cara − HB_bz = {s3(hb_diff_c1)} (cap) frente a 100", f"con HB_bz = 225: {s3(P['HB_cara']-225)} (límite 100); ligar HB_bz a la aleación; un disco de Ø2000 × 6 mm templado a 330 HB se deforma: segmentar o usar tratamiento superficial"))
FIND.append(("C10", "menor", "Desgaste: la reserva t_bz − t_flex/√η no descuenta el sobreespesor de relapeado ni la ranura de engrase (que desaparece con h = h_gr) y s se mide en r_ef, no en R_o; el k_bz crítico queda dentro del rango admitido [0,1; 500]",
             f"FU desgaste {s3(RC[1]['desgaste en la vida de diseño'][2])} (C1), {s3(RC[3]['desgaste en la vida de diseño'][2])} (C3); k_bz crítico núcleo > 500",
             f"con corrección FU {s3(FUW[1])} (C1)/{s3(FUW[3])} (C3); k_bz crítico ≈ {s3(KCRIT2[1])} (C1) / {s3(KCRIT2[3])} (C3) (×1e-7) frente a 500; p_bz crítico = q_neto = {s3(rr1['qnet'])}–{s3(rr3['qnet'])} MPa (< 5 MPa mínimo del rango)"))
nm_j = next(r_["nombre"] for r_ in DC[3]["interfazChecks"]["C"] if "pastilla" in r_["nombre"] and "dilatación" in r_["nombre"])
cl_c11 = "≥ 1 mm" in nm_j
CIERRES.append(("C11", "texto de la junta entre pastillas (≥ 1 mm en frío)", cl_c11, f"junta térmica {s3((AL_BZ-AL_S)*P['dT']*2*Ro*math.sin(math.pi/P['bz_npad']))} mm; fila: «{nm_j[:90]}…»"))
FIND.append(("C11", "menor", "Junta entre pastillas: el texto exige ≥ 1 mm, pero el cálculo sigue dando solo la dilatación (0,066 mm) y no descuenta la junta de la cobertura; galvánico y gripado siguen «pend» (el grafito es el cátodo más noble del par)",
             f"junta térmica {s3((AL_BZ-AL_S)*P['dT']*2*Ro*math.sin(math.pi/P['bz_npad']))} mm, bz_npad = {P['bz_npad']}; texto «≥ 1 mm» presente: {cl_c11}",
             f"24 juntas de 1 mm × 925 mm = {s3(P['bz_npad']*1.0*(Ro-Ri)/Ac*100)} % del área: compatible con cobertura 0,9; biselar bordes, sellar el perímetro y la grasa, aislar tornillería inoxidable y pintar el respaldo con imprimante de zinc"))
FIND.append(("C12", "menor", "c_lug 50 → 150: la corrección es necesaria (A, B y C pasan de ≈ 1,00–1,05 a 0,67–0,70); mi plancha de Mindlin converge a una flecha ≈ 5 % menor que la del núcleo (el núcleo es conservador y su malla influye)",
             f"FU flecha c_lug 150: 0 {s3(LIFT[('0 acero–acero',150)][1])}, A {s3(LIFT[('A inox–inox',150)][1])}, B {s3(LIFT[('B inox + UHMW',150)][1])}, C {s3(LIFT[('C1 bronce + disco',150)][1])}/{s3(LIFT[('C2 bronce + 2.ª placa',150)][1])}/{s3(LIFT[('C3 pastillas + disco',150)][1])}",
             f"c_lug 50: A {s3(LIFT[('A inox–inox',50)][1])}, B {s3(LIFT[('B inox + UHMW',50)][1])}, C {s3(LIFT[('C1 bronce + disco',50)][1])}/{s3(LIFT[('C2 bronce + 2.ª placa',50)][1])}/{s3(LIFT[('C3 pastillas + disco',50)][1])} (núcleo, sobre B/300); propio converge a {s3(LIFT[('A inox–inox',50)][3])}–{s3(LIFT[('C2 bronce + 2.ª placa',50)][3])}; sin cambios necesarios con c_lug = 150"))

# ---- hallazgos de la fijación por sectores con topes
mx = lambda d: max(d.items(), key=lambda kv: kv[1])
k_e, v_e_ = mx(FU_ECC)
n_over = [k_ for k_, v_ in FU_ECC.items() if v_ > 1 + 1e-9]
FIND.append(("T1", "menor", "Fuerza por tope F = (T_calado/r_u)/n·(q_máx/q_med): válida como diseño por capacidad del accionamiento y conservadora; con r_u el par equivale a μ = " + f"{s3(Tmax*1e3/(ru_p/1e3)/(rA_['N']*1e3))}" + ", mayor que el μ_máx de C",
             f"F = {s3(F_tope(P, nsec)/1e3)} kN por tope (n = {nsec})",
             f"el sector más cargado tiene presión media {s3(ratio_sec(nsec))}·q_med y no {s3(qr_core)} (q_máx del borde exterior): F real {s3((ratio_sec(nsec)/qr_core-1)*100)} %; con μ_máx·N (C {s3(max(P['muC_d'], P['muC_cont'], P['muC_dry']))}) sería {s3(max(P['muC_d'], P['muC_cont'], P['muC_dry'])*r1_['N']*1e3/nsec*ratio_sec(nsec)/1e3)} kN; "
             "si la interfaz se gripa, T_calado llega íntegro a los topes, por lo que conviene mantenerlo; falta el tope en ambos sentidos de giro (un tope compartido entre sectores vecinos o dos por sector) y centrarlo radialmente en el sector (guiñada)"))
FIND.append(("T2", "importante" if n_over else "menor",
             "Soldadura del tope al respaldo: el núcleo verifica solo el corte de dos filetes (f = F/(2·0,707·w·L)); falta el momento de excentricidad entre la fuerza de apoyo (a h_c/2 sobre el respaldo) y la soldadura, que tracciona el filete trasero",
             f"FU corte (núcleo) máx {s3(max(float(r_[3]) for r_ in rows2))}",
             f"con barra de espesor b = 2·w = {bt_:g} mm y h_c = t − sobreespesor: FU combinado hasta {s3(v_e_)} ({k_e}); incumplen: {', '.join(n_over) if n_over else 'ninguna'}; "
             "espesor de barra necesario (tabla 5i.2) hasta " + s3(max(float(r_[5]) for r_ in rows2 if r_[5] not in ('inf', '—'))) + " mm; corregir con barra ≥ 20 mm de espesor, filetes de 8 mm o L mayor, o con tope bajo (h_c ≤ 3 mm)"))
FIND.append(("T3", "menor", "Aplastamiento del tope: el núcleo usa el espesor completo t del canto; el tope no puede alcanzar la cara de deslizamiento, así que la altura de apoyo es h_c = t − sobreespesor de relapeado (y menos con una holgura)",
             "σ_aplast. con t completo: FU " + f"{s3(max(float(r_[9]) for r_ in rows1))} máx",
             "con h_c = t − sobreespesor: FU " + ", ".join(f"{k_.split(' · ')[0]} {k_.split(' · ')[1][:10]} {s3(v_[0])}" for k_, v_ in FU_HC.items() if v_[0] > 0.9) + "; con 1 mm más de holgura: " + ", ".join(f"{k_.split(' · ')[0]} {k_.split(' · ')[1][:10]} {s3(v_[1])}" for k_, v_ in FU_HC.items() if v_[1] > 1) + ": subir L_tope o espesor del canto"))
FIND.append(("T4", "menor", "Modos de falla del sector suelto sin fila en el núcleo (vuelco por el tope, flexión local del respaldo, tensión en el plano del sector, peso sobre los tornillos de posición): cubiertos con mis cotas, sin que haya fila de verificación",
             "sin filas",
             f"vuelco FU máx {s3(max(FU_OV.values()))} (q_mín); respaldo (flexión local con dispersión 45°) {s3(max(FU_BK.values()))}; tornillos de posición al izar {s3(max(FU_SC.values()))}; tensión en el plano p95/Fy " + ", ".join(f"{s3(v_)}" for v_ in IP.values()) + "; levantamiento por succión no gobierna con N > 0 (q_mín = " + s3(r1_['ND']*1e3/A_p*(2-qr_core)) + " MPa)"))
FIND.append(("T5", "menor", "Fila de la cabeza del tornillo avellanado: en el disco ranurado de A no se descuenta la ranura (t − sobreespesor) y en la placa de bronce sí (t − sobreespesor − h_gr); las graseras de C se describen en la plancha inferior de la mesa, pero la placa ranurada de C va en la base",
             f"A mesa: cap {s3(P['ss_allow'] and rA_['tss2'] - P['ss_allow'])} mm; bronce: cap {s3(rC[1]['tb'] - P['bz_allow'] - P['h_gr'])} mm",
             "unificar el criterio (cabeza fuera de la ranura: no descontar) y ubicar las graseras de C en el borde de la plancha base"))


# ======================================================================================
# Hallazgos
# ======================================================================================
has_pend = {"A": any(r["estado"] == "pend" and "Opción A" in r["nombre"] for r in DA["interfazChecks"]["A"]),
            "B": any(r["estado"] == "pend" and "Opción B" in r["nombre"] for r in DB["interfazChecks"]["B"])}
if np is not None and sig_fd is not None and sig_fd > sig_cl * 1.001:
    FIND.append(("H0", "importante", "El modelo empotrado no acota al de fundación unilateral", f"σ {s3(sig_cl)}", f"σ {s3(sig_fd)}"))
if tuh0 < com(max(t_g, P["uh_tmin"]), COM_UH):
    FIND.append(("H1", "importante", "t_UHMW por debajo del requerido con la variante de Gent", f"{s3(tuh0)} mm", f"{s3(com(t_g, COM_UH))} mm"))
if P["muB_d"] < 0.20 or P["muB_cont"] < P["muB_dry"]:
    FIND.append(("H2", "importante", "μ de B por debajo del rango seco o contaminado menor que el seco", f"μ_d {P['muB_d']}", "μ_d ≥ 0,20; μ_cont ≥ μ_seco"))
lab_d = next((x["lab"] for g_ in D0["grupos"] for x in g_["p"] if x["id"] == "d_flat"), "")
d_def_ok = "hueco" in lab_d.lower() and "espesor" in lab_d.lower()
FIND.append(("N1", "menor" if d_def_ok else "importante",
             "d_flat gobierna a B (t_conf ∝ d) y no se verifica en el cálculo; " + ("su definición ya es el hueco relativo entre las dos caras con la tolerancia de espesor de la lámina, pero queda por exigir y medir en obra" if d_def_ok else "debe ser la variación del hueco relativo entre las dos caras (suma de las planitudes y del espesor de la lámina)"),
             f"t_UHMW {s3(tuh0)} mm, Δ {s3(IF[2]['delta'])} mm, soldadura de mejillas FU {s3(soldadura_mejilla(IF[2]['delta'])/cap_w)}",
             f"d_flat ≤ {s3(d_adm_w)} mm mantiene t_UHMW = {s3(tuh0)} mm; con d = 0,06 mm → 20 mm y soldadura FU 1,01 (margen de la soldadura 2,3 %). Planos: «variación máxima del hueco ≤ 0,05 mm en Ø100» con rectificado in situ y medición; reforzar el filete de mejillas si se quiere holgura"))
has_th = any("cortante térmico" in r["nombre"] for r in DA["interfazChecks"]["A"])
tau_t = tau_th(IF[1]["tss"])
FIND.append(("N2", "menor" if has_th and cap_ad >= Tmax else "importante",
             "Retención de los discos descansa en el adhesivo (la fricción sola con μ_resp = 0,30 no cumple); su durabilidad depende de G_ad = 100 MPa y t_ad = 1 mm, que son supuestos de diseño a especificar y ensayar",
             f"máx(fricción; adhesivo) = {s3(cap_ret(IF[1]['N']))} kN·m, FU {s3(Tmax/cap_ret(IF[1]['N']))}; τ_borde {s3(tau_t) if tau_t else '—'} / {s3(P.get('tau_cyc'))} MPa",
             f"solo fricción FU {s3(Tmax/(P['mu_back']*IF[1]['N']*ru/1e3))}; área adherida mínima {s3(f_ad_min*100)} %; sensibilidad del cortante de borde: epóxico rígido 0,3 mm {s3(eps_th*math.sqrt(1000*E_SS*IF[1]['tss']/0.3))} MPa (> τ_cyc), tenaz 1 mm {s3(eps_th*math.sqrt(100*E_SS*IF[1]['tss']/1.0))} MPa; ensayo de arrancamiento y de fatiga térmica"))
FIND.append(("N3", "menor" if has_pend["B"] else "importante", "Opción B: retención de los sectores UHMW contra el arrastre sigue pendiente (fila «pend» del núcleo)",
             f"{s3(Fdrag)} kN (μ_máx = {s3(mu_top_max)})", f"fila pendiente del núcleo: {s3(next((r['dem'] for r in DB['interfazChecks']['B'] if 'retención de los sectores' in r['nombre']), 0))} kN; {s3(n_bolts)} bulones M8 por aplastamiento del UHMW: resolver con rebaje perimetral/cola de milano o pegado antes de emitir"))
FIND.append(("N4", "menor" if has_pend["A"] else "importante", "Opción A: gripado inox–inox pendiente (fila «pend» del núcleo)", f"presión {s3(q)} MPa; caso seco FS {s3(casos(P,1,IF[1]['N'])['seco']['FS'])}",
             "exigir aleaciones o durezas distintas (≥ 50 HB) o recubrimiento; la presión nominal es ≈ 1/8 de los umbrales ASTM G98 publicados para 304/304 (confirmar), pero la grasa puede expulsarse tras reposo largo"))
FIND.append(("N5", "menor", "μ de B: μ_cont = μ_seco = 0,25 sin margen para arena incrustada", f"μ_máx que gira {s3(mu_max_B)}", f"margen {s3((mu_max_B/P['muB_cont']-1)*100)} %; con μ = 0,30 no gira"))
FIND.append(("H6", "menor", "Modelo de la placa: empotrada es adecuada y conservadora (≈ 11 %) para un vacío interior con q > 0 alrededor; la apoyada daría t = 8 mm; no cubre un vacío contiguo al borde del disco",
             f"σ empotrada {s3(sig_cl)} MPa", f"unilateral {s3(sig_fd) if sig_fd else '—'} MPa (−11 %); apoyada {s3(sig_ss)} MPa (t_req {s3(tfl_ss + P['ss_allow'])} → {s3(com(tfl_ss + P['ss_allow'], COM_SS))} mm); la carga uniforme gobierna para δ_v ≥ {s3(wc_fd if wc_fd else wc_cl)} mm (empotrada {s3(wc_cl)}); voladizo máx. c = {s3(c_ov)} mm (cantear el respaldo ≤ 3 mm). σ_δ cerrada subestima ≈ 2× a δ_v = 0,01 mm y 8 % a 0,03 mm: no usarla para reducir t"))
FIND.append(("H8", "menor", "Fluencia de la lámina: asentamiento y diferencia de borde pequeños; sin efecto sobre la verticalidad, pero relaja bulones y desplaza material a las juntas",
             "no evaluada", f"≈ 0,2–0,4 mm de asentamiento y ≈ 0,1–0,3 mm de diferencia con t = {s3(tU)} mm (≈ 0,05–0,15 mm/m); arandelas elásticas y rebajes con holgura"))
_hd = [r_ for r_ in DA["interfazChecks"]["A"] if "cabeza del tornillo" in r_["nombre"]]
FIND.append(("H10", "menor", "Pernos avellanados: el núcleo ya verifica la cabeza (0,55·d + 2 ≤ t − sobreespesor) con M" + str(int(P["d_tor"])) + (f" (FU {s3(max(r_['fu'] for r_ in _hd))} en el disco de {s3(IF[1]['tss'])} mm: poca holgura); " if _hd else ": sin fila; ") + "corrosión galvánica y de resquicio inox/acero al carbono sin verificación",
             f"cabeza M{int(P['d_tor'])}: {s3(0.55*P['d_tor']+2)} mm frente a {s3(IF[1]['tss']-P['ss_allow'])} mm útiles", "usar M6 (k = 3,3 mm) o discos de 8 mm si se sube d_tor; sellar el perímetro y proteger el respaldo con imprimante de zinc"))

# ======================================================================================
# Resumen
# ======================================================================================
bad = [c for c in COMP if c[5] == "discrepa"]
nco = sum(1 for c in COMP if c[5] == "coincide")
table("Discrepancias numéricas entre el cálculo propio y el núcleo", ["Prueba", "Magnitud", "Propio", "Núcleo", "Δ %", "Veredicto"], bad if bad else [["—", "ninguna", "", "", "", ""]])
if P["fix_mode"] == 1:
    FIND[:] = [f_ for f_ in FIND if f_[0] not in ("N2", "N3")]
    CIERRES.append(("N2/N3", "retención por topes (sin adhesivo) y filas del rebaje del UHMW", True,
                    "B: σ canto UHMW " + s3(rowsAB(P, 2)[0]["Lámina UHMW (" + str(P["n_seg"]) + " sectores): aplastamiento del canto contra el tope del rebaje"][0]) + f" MPa (cap {P['p_uhmw']}); topes en A, B y C"))
table("Cierres de la revisión anterior verificados contra el núcleo actual", ["Id", "Cambio del núcleo", "Cerrado", "Evidencia"], [[a_, b_, "sí" if c_ else "NO", d_] for a_, b_, c_, d_ in CIERRES])
table("Hallazgos", ["Id", "Severidad", "Hallazgo", "Núcleo", "Corregido / efecto"], FIND)
if bad or sw_bad or swC_bad or um_bad:
    FIND.append(("D0", "crítica", "Discrepancias numéricas entre el cálculo propio y el núcleo (tolerancia 0,1 %)",
                 f"{len(bad)} comparaciones, {sw_bad} en barridos A/B, {swC_bad} en barridos de C, {um_bad} umbrales", "revisar la tabla «Discrepancias numéricas»"))
sev = {k_: sum(1 for f in FIND if f[1] == k_) for k_ in ("crítica", "importante", "menor")}
print(f"\nRESULTADO: {nco} coincidencias, {len(bad)} discrepancias numéricas; barridos A/B {sw_n} comparaciones, {sw_bad} discrepancias; barridos de C {swC_n} comparaciones, {swC_bad} discrepancias; umbrales de C {len(UM)}, {um_bad} discrepancias; hallazgos: "
      f"{sev['crítica']} críticos, {sev['importante']} importantes, {sev['menor']} menores")
sys.exit(1 if sev["crítica"] or sev["importante"] else 0)
