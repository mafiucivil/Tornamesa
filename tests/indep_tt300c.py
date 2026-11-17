"""Verificación independiente TT300-C (agente verificador-independiente).
Recalcula desde el enunciado (params_defaults.json) sin leer el código JS y compara con el golden file.
Ejecutar: python3 -I tests/indep_tt300c.py"""
import json, math, pathlib, sys
d = pathlib.Path(__file__).resolve().parent / "golden"
P = json.loads((d / "params_defaults.json").read_text()); P["drive_mode"] = 1   # este verificador modela el accionamiento guiado
G = json.loads((d / "tt300c_guiado.json").read_text())   # golden del modo guiado (drive_mode = 1)
g, rho = 9.80665, 7.85e-6
fails = []
def chk(name, mine, tool, tol=1e-3):
    ok = abs(mine - tool) <= tol * abs(tool)
    print(f"{'OK ' if ok else 'XX '} {name:52s} indep {mine:12.4f}  herramienta {tool:12.4f}  Δ {(mine-tool)/tool*100:+.4f} %")
    if not ok: fails.append(name)

# --- geometría y masas de la mesa ---
rings = sorted(float(x) for x in P["rings"].replace(";", ",").split(",") if x.strip())
Rt = P["D_top"] / 2; hw = P["h_disc"] - P["t_top"] - P["t_bot"]
rpr = max(P["D_hub"] / 2, P["R_pin"] - (Rt - P["R_pin"]))
db = P["D_piv"] + 30
aring = math.pi * (Rt**2 - rpr**2) - P["N_pin"] * math.pi * P["d_pin"]**2 / 4
m_top = rho * ((math.pi * rpr**2 - math.pi / 4 * (P["D_piv"] + 80)**2) * P["t_top"] + aring * max(P["t_pr"], P["t_top"]))
# Collar del pivote (cambios 2 y 3 del núcleo): rebaje del cubo con holguras radial c_boss_r y axial c_boss_a.
# La plancha inferior lleva agujero pasante Ø(D_boss+2·c_boss_r); desde la cara inferior la profundidad de rebaje es
# h_boss − δ + c_boss_a (δ = espesor de interfaz; 0 por defecto), y el cubo solo se rebaja lo que excede t_bot.
collar = P["h_boss"] > 0
D_rec = P["D_boss"] + 2 * P["c_boss_r"] if collar else db
delta_if = 0.0 if not (P["opt_ss"] or P["opt_uhmw"] or P["opt_bz"]) else None
assert delta_if is not None, "este script cubre el caso por defecto (sin interfaz); las variantes A/B/C están en indep_interfaz.py"
dep_rec = P["h_boss"] - delta_if + P["c_boss_a"] if collar else 0.0
m_bot = rho * ((math.pi * rpr**2 - math.pi / 4 * D_rec**2) * P["t_bot"] + aring * max(P["t_pr"], P["t_bot"]))
m_webs = rho * sum(2 * math.pi * r * hw * P["t_web"] for r in rings)
nin = sum(1 for r in rings if P["D_hub"] / 2 < r < P["R_rib"])
m_ribs = rho * P["N_rib"] * (P["R_rib"] - P["D_hub"] / 2 - nin * P["t_web"]) * hw * P["t_rib"]
m_hub = rho * math.pi / 4 * ((P["D_hub"]**2 - db**2) * hw - ((D_rec**2 - db**2) * max(dep_rec - P["t_bot"], 0) if collar else 0))   # rebaje solo por encima de la plancha inferior
m_pins = rho * P["N_pin"] * math.pi / 4 * P["d_pin"]**2 * P["h_disc"]
m_disc = m_top + m_bot + m_webs + m_ribs + m_hub + m_pins
chk("Masa de la mesa (kg)", m_disc, G["masa_mesa"])
m_piv = rho * math.pi / 4 * P["D_piv"]**2 * (P["t_base"] + P["h_disc"] - P["t_top"] + 3)
W = P["W_tf"] * g; Wd = (m_disc + 0.5 * m_piv) * g / 1e3; N = W + Wd; ND = P["phi_d"] * W + Wd
chk("N = W + W_mesa (kN)", N, G["N"])
# R_i real de la interfaz (cambio 2): con collar = D_boss/2 + c_boss_r + m_ri; sin collar = D_piv/2 + 15
Ro = Rt
Ri = P["D_boss"] / 2 + P["c_boss_r"] + P["m_ri"] if collar else P["D_piv"] / 2 + 15
A = math.pi * (Ro**2 - Ri**2); I = math.pi * (Ro**4 - Ri**4) / 4
chk("q_max interfaz (MPa) — Navier", ND * 1e3 / A + ND * 1e3 * P["e"] * Ro / I, G["q_max"])

# --- cinemática del accionamiento guiado (pasador entre −π/N y +π/N, empuje paralelo a la guía) ---
pitch = 2 * math.pi / P["N_pin"]
ys = [P["R_pin"] * math.sin(-pitch / 2 + pitch * i / 2000) for i in range(2001)]
chk("Carrera requerida (mm)", P["s_free"] + ys[-1] - ys[0], G["carrera_req"])
armmin = min(P["R_pin"] * math.cos(-pitch / 2 + pitch * i / 2000) for i in range(2001))
chk("Brazo mínimo (mm)", armmin, G["brazo_min"])
# patín: frente = l_p + 20 + f_ext; trasera = 1,25 d_pp; Lg = 2/3 L_s; reacciones en (front−rear)/2 ± Lg/2
front = P["l_p"] + 20 + P["f_ext"]; rear = 1.25 * P["d_pp"]; Lsh = front + rear; Lg = 2 / 3 * Lsh
y_r = (front - rear) / 2 - Lg / 2
rp = P["d_pin"] / 2; y_c = P["l_p"] - rp            # cara plana de la uña en la superficie del pasador
mu_s, mu_g, eta = P["mu_s"], P["mu_g"], P["eta_c"]

def estado(th, Tn, sg=None, mug=None):
    """Cara plana normal a y. Fricción en la cara: H (sobre el pasador, en x) = s·μ_s·F, s = signo(y_p − r).
    Mesa: T/n = a·F − (y_p − r)·H.  Patín: R_f = [F·Δ + H(y_c − y_r)]/Lg, R_r = H − R_f.
    F_cil = [F + μg(|R_f| + |R_r|)]/η."""
    mug = mu_g if mug is None else mug
    a, yp = P["R_pin"] * math.cos(th), P["R_pin"] * math.sin(th)
    if sg is None:
        sg = 1 if yp > rp else -1
    F = Tn / (a + sg * mu_s * (rp - yp))
    H = sg * mu_s * F
    Rf = (F * (P["x_g"] - a) + H * (y_c - y_r)) / Lg
    Rr = H - Rf
    return F, H, Rf, Rr, (F + mug * (abs(Rf) + abs(Rr))) / eta

def fmax(Tn, mug=None):
    ths = [-pitch / 2 + pitch * i / 4000 for i in range(4001)]
    t0 = math.asin(rp / P["R_pin"])
    cands = [estado(t, Tn, mug=mug) for t in ths] + [estado(t0, Tn, s, mug) for s in (1, -1)]
    return max(cands, key=lambda e: e[4])

# --- accionamiento ---
Ab = math.pi / 4 * P["D_bore"]**2
Fst = Ab * P["p_relief"] / 10 / 1e3
chk("Fuerza de calado (kN)", Fst, G["F_calado"])
def H(mu): return mu * N * P["e"] * 4 / 3 * (Ro**3 - Ri**3) / (Ro**4 - Ri**4)
r_u = 2 / 3 * (Ro**3 - Ri**3) / (Ro**2 - Ri**2)
cases = {"nom": (P["mu_nom"], r_u), "dis": (P["mu_d"], P["r_ef"]), "borde": (P["mu_d"], Ro), "cont": (P["mu_cont"], P["r_ef"]), "seco": (P["mu_dry"], r_u)}
for k, (mu, r) in cases.items():
    T = mu * N * r / 1e3 + P["mu_bush"] * H(mu) * P["D_piv"] / 2 / 1e3     # kN·m
    F = fmax(T * 1e3 / P["n_cyl"])[4]                                         # kN (T en kN·mm / mm)
    chk(f"Caso {k}: F por cilindro (kN)", F, G["casos"][k][0])
    chk(f"Caso {k}: FS", Fst / F, G["casos"][k][2])
FU = G["fu"]
class _FU(dict):
    def __getitem__(self, k):
        if k in FU: return FU[k]
        m = [v for kk, v in FU.items() if kk.startswith(k.split(" (")[0])]
        if len(m) == 1: return m[0]
        raise KeyError(k)
fu = _FU()
Td = P["mu_d"] * N * P["r_ef"] / 1e3 + P["mu_bush"] * H(P["mu_d"]) * P["D_piv"] / 2 / 1e3
eM = fmax(Td * 1e3 / P["n_cyl"])
# calado en la guía: F_pas = η·F_calado (la fricción de guía puede ser nula en reposo); R_f máx en θ = +π/N
Fpc = eta * Fst                                        # kN
def guia_cal(th):
    a, yp = P["R_pin"] * math.cos(th), P["R_pin"] * math.sin(th)
    Hh = (1 if yp > rp else -1) * mu_s * Fpc
    Rf = (Fpc * (P["x_g"] - a) + Hh * (y_c - y_r)) / Lg
    return Hh, Rf, Hh - Rf
gc = [guia_cal(-pitch / 2 + pitch * i / 4000) for i in range(4001)]
Rcal = max(abs(g[1]) for g in gc)                      # kN
SRcal = max(abs(g[1]) + abs(g[2]) for g in gc)

# --- bomba (cambio 1: Q_pump 10, Q_ret 20 L/min, t_vuelta_obj 15 min) ---
# Avance y retorno por paso con los n cilindros en paralelo: t = n·A·carrera/Q; una vuelta = N_pin pasos (el patín recorre la carrera completa en cada paso).
Ann = Ab - math.pi / 4 * P["d_rod"]**2
tRev = P["N_pin"] * P["n_cyl"] * P["stroke"] * (Ab / P["Q_pump"] + Ann / P["Q_ret"]) / 1e6            # min (mm³ → L)
chk("Tiempo por vuelta: FU = t_vuelta/t_obj (Q_pump 10, Q_ret 20)", tRev / P["t_vuelta_obj"], G["fu"]["Giro · Tiempo por vuelta frente al objetivo"])
v_ret = P["Q_ret"] * 1e6 / 60 / (P["n_cyl"] * Ann) / 1000                                              # m/s del vástago en el retorno
chk("Velocidad de retorno del vástago: FU = v/v_max", v_ret / P["v_ret_max"], G["fu"]["Giro · Velocidad de retorno del vástago frente al máximo (rebote de la uña sobre el pasador)"])

# --- cadena de empuje (BTH-1, Nd) ---
Nd = P["Nd"]; tpr = max(P["t_pr"], P["t_top"], P["t_bot"])
Ls = P["h_disc"] - tpr                                  # luz entre planos medios de los anillos
Fr = Fst * math.sqrt(1 + mu_s**2)                      # kN, resultante normal + fricción de la cara
c = P["dog_h"]                                         # carga repartida en la altura de la uña, centrada
M_p = Fr * 1e3 * (Ls - c / 2) / 4                      # = F(2L − c)/8, viga biapoyada con carga parcial centrada
S_p = math.pi * P["d_pin"]**3 / 32; A_p = math.pi / 4 * P["d_pin"]**2
chk("Pasador de empuje: FU flexión (repartida en h_uña)", M_p / S_p / (P["Fy_pin"] / Nd), fu["Pasadores de empuje · Flexión (biapoyado entre anillos"])
V_p = Fr * 1e3 * (0.5 + P["e_dog"] / Ls)               # reacción máx. con excentricidad accidental e
chk("Pasador de empuje: FU corte en el apoyo", 4 * V_p / (3 * A_p) / (P["Fy_pin"] / (Nd * 3**.5)), fu["Pasadores de empuje · Corte en el apoyo"])
chk("Pasador de empuje: FU aplastamiento en el anillo", V_p / (P["d_pin"] * tpr) / (1.25 * P["Fy"] / Nd), fu["Pasadores de empuje · Aplastamiento en el agujero del anillo"])
chk("Pasador–uña: FU aplastamiento", Fst * 1e3 / (P["d_pin"] * P["dog_h"]) / (1.25 * min(P["Fy_pin"], P["Fy_dog"]) / Nd), fu["Pasadores de empuje · Aplastamiento pasador–uña"])
Mpp = Fst / 2 * (P["t_ch"] / 2 + P["g_ch"] + P["b_eye"] / 4) * 1e3
chk("Pasador articulación: FU flexión", Mpp / (math.pi * P["d_pp"]**3 / 32) / (P["Fy_pp"] / Nd), fu["Articulaciones · Pasador: flexión (horquilla)"])
hax = P["h_disc"] / 2; aw = 0.707 * P["w_br"]
f = math.hypot(Fst * 1e3 / (4 * aw * P["L_ch"]), Fst * 1e3 * hax / (4 * aw * P["L_ch"]**2 / 6))
chk("Soldadura mejillas–base: FU", f / (0.6 * P["FEXX"] / (1.2 * Nd)), fu["Articulaciones · Soldadura mejillas–base (4 filetes)"])
Pcr = math.pi**2 * P["E"] * math.pi * P["d_rod"]**4 / 64 / (P["L0"] + P["stroke"])**2 / 1e3
chk("Pandeo del vástago: FU", Fst / (Pcr / 3), fu["Giro · Pandeo del vástago (biarticulado, longitud extendida)"])

# --- uña (cara plana) a F_calado ---
F1 = Fst * 1e3; b, hd = P["dog_b"], P["dog_h"]; fa, fv = P["Fy_dog"] / Nd, P["Fy_dog"] / (Nd * 3**.5)
mouth = min(P["x_g"] - P["w_s"] / 2, P["R_pin"] + rp + 10)
lev = mouth - armmin
chk("Uña: FU flexión en la boca + μ_s·F (axial y excéntrica b/2)", (F1 * (lev + P["e_dog"]) / (hd * b**2 / 6) + mu_s * F1 * (b / 2) / (hd * b**2 / 6) + mu_s * F1 / (hd * b)) / fa,
    fu["Uña · Flexión en la boca del patín (voladizo) con fricción radial"])
chk("Uña: FU corte en la boca", 1.5 * F1 / (hd * b) / fv, fu["Uña · Corte en la boca del patín"])
Es = P["E"] / (2 * (1 - P["nu"]**2))
chk("Uña: FU Hertz cara plana–pasador (ambas caras templadas)", math.sqrt(P.get("k_edge", 1.0) * F1 / hd * Es / (math.pi * rp)) / (1.67 * P["Fy_surf"]), fu["Uña · Contacto de Hertz cara plana–pasador"])  # carga lineal de borde k·F/h (N8)
tip = armmin - P["c_tip"]
travel = (P["R_pin"] + rp + 5) - tip                  # punta retraída 5 mm fuera del pasador en a = R (cota del núcleo)
beta = math.radians(P["beta_ch"])
dy = travel / math.tan(beta)
chk("Uña: FU chaflán (Δy + b_punta ≤ b)", (dy + P["b_tip"]) / b, fu["Uña · Chaflán de retorno: cabe en la uña dejando la punta"])
wc = b - dy * (1 - P["c_tip"] / travel)
chk("Uña: FU corte en la sección de contacto", 1.5 * F1 / (hd * wc) / fv, fu["Uña · Corte en la sección del contacto (punta achaflanada)"])
smax, x = 0.0, P["c_tip"]
while x <= travel:
    w = b - dy * (1 - x / travel); smax = max(smax, 6 * F1 * (x - P["c_tip"]) / (hd * w * w)); x += 0.01
chk("Uña: FU flexión en la zona del chaflán", smax / fa, fu["Uña · Flexión en la zona del chaflán"], tol=2e-3)
mur = P["mu_ret"]; kk = 1 + 2 * (mouth - (tip + travel / 2)) / P["L_in"]
chk("Retorno: FU autobloqueo (contacto en el medio del chaflán)", mur * kk * (math.sin(beta) + mur * math.cos(beta)) / (math.cos(beta) - mur * math.sin(beta)),
    fu["Giro · Retorno sin autobloqueo de la uña (chaflán contra el pasador siguiente)"])
l = lev + P["e_dog"]; Lin = P["L_in"]
c = -l + math.sqrt(l * l + l * Lin + Lin * Lin / 2)
sal = F1 / (hd * (2 * c - Lin))
fb_sh = 1.25 * P["Fy_shoe"] / Nd
chk("Alojamiento: FU bloque rígido-plástico", sal / fb_sh, fu["Patín y guía · Aplastamiento del alojamiento de la uña (bloque rígido-plástico)"])
inset = (P["x_g"] - P["w_s"] / 2) - mouth
V = min(F1, sal * hd * min(inset, c))
chk("Marco de boca: FU flexión", 6 * V * inset / 2 / ((hd + 20) * P["t_fw"]**2) / (P["Fy_shoe"] / Nd), fu["Patín y guía · Pared del marco de boca: flexión (voladizo del marco)"])
chk("Marco de boca: FU corte", 1.5 * V / ((hd + 20) * P["t_fw"]) / (P["Fy_shoe"] / (Nd * 3**.5)), fu["Patín y guía · Pared del marco de boca: corte"])

# --- guía y bancada con ranura T ---
ht = P["h_slot"] - 2
chk("Lengüeta: FU pico 4R/((h−2)L_s)", 4 * Rcal * 1e3 / (ht * Lsh) / (1.25 * P["Fy"] / Nd), fu["Patín y guía · Aplastamiento de la lengüeta en la ranura (pico de la distribución lineal)"])
troot = (P["w_bed"] - P["w_tee"]) / 2
lev_w = ht / 2 + 2 + P["h_tee"]                       # centroide del contacto en el cuello → fondo de la cabeza T (raíz de t_raíz)
chk("Pared de la ranura: FU flexión en la raíz de t_raíz (brazo hasta el fondo de la cabeza T)",
    6 * (4 * Rcal * 1e3 / Lsh) * lev_w / troot**2 / (P["Fy"] / Nd), fu["Patín y guía · Pared de la ranura: flexión en la raíz"])
chk("Soldadura bancada–base: FU", Rcal * 1e3 / (2 * 0.707 * P["w_bed_f"] * (Lsh + 2 * P["w_bed"])) / (0.6 * P["FEXX"] / (1.2 * Nd)),
    fu["Patín y guía · Soldadura bancada–base (2 filetes longitudinales)"])
chk("Fondo de la ranura (FU = 12/fondo)", 12 / (P["t_bed"] - P["h_slot"] - P["h_tee"]), fu["Patín y guía · Fondo de la ranura de la bancada"])
# retención vertical por la cabeza T (definición declarada: contacto a h_ranura/2 bajo la cara superior)
z_eje = P["h_disc"] / 2 + P["t_base"]; z_t = P["t_base"] + P["t_bed"] - P["h_slot"] / 2; dz = z_eje - z_t
Mv = mu_s * Fpc * 1e3 * dz; Mc = mu_g * SRcal * 1e3 * dz
Vt = Mv / ((P["w_bed"] + P["w_tee"]) / 2) + Mc / Lsh
ala = (P["w_tee"] - P["w_slot"]) / 2
chk("Retención T: FU aplastamiento del ala", Vt / (ala * Lsh) / (1.25 * P["Fy"] / Nd), fu["Patín y guía · Retención vertical del patín: aplastamiento en la cabeza T"])
chk("Retención T: FU flexión del ala", 6 * Vt * (ala / 2) / (Lsh * P["h_tee"]**2) / (P["Fy"] / Nd), fu["Patín y guía · Retención vertical: flexión del ala de la cabeza T"])
chk("Retención T: FU flexión del labio de la bancada", 6 * Vt * (ala / 2) / (Lsh * P["h_slot"]**2) / (P["Fy"] / Nd), fu["Patín y guía · Retención vertical: flexión del labio de la bancada sobre la cabeza T"])
print("\nRESULTADO:", "sin diferencias" if not fails else "DIFERENCIAS en " + ", ".join(fails))
sys.exit(1 if fails else 0)
