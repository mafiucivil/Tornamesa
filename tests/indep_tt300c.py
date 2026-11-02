"""Verificación independiente TT300-C (agente verificador-independiente).
Recalcula desde el enunciado (params_defaults.json) sin leer el código JS y compara con el golden file.
Ejecutar: python3 -I tests/indep_tt300c.py"""
import json, math, pathlib, sys
d = pathlib.Path(__file__).resolve().parent / "golden"
P = json.loads((d / "params_defaults.json").read_text())
G = json.loads((d / "tt300c_defaults.json").read_text())
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
m_bot = rho * ((math.pi * rpr**2 - math.pi / 4 * db**2) * P["t_bot"] + aring * max(P["t_pr"], P["t_bot"]))
m_webs = rho * sum(2 * math.pi * r * hw * P["t_web"] for r in rings)
nin = sum(1 for r in rings if P["D_hub"] / 2 < r < P["R_rib"])
m_ribs = rho * P["N_rib"] * (P["R_rib"] - P["D_hub"] / 2 - nin * P["t_web"]) * hw * P["t_rib"]
m_hub = rho * math.pi / 4 * (P["D_hub"]**2 - db**2) * hw
m_pins = rho * P["N_pin"] * math.pi / 4 * P["d_pin"]**2 * P["h_disc"]
m_disc = m_top + m_bot + m_webs + m_ribs + m_hub + m_pins
chk("Masa de la mesa (kg)", m_disc, G["masa_mesa"])
m_piv = rho * math.pi / 4 * P["D_piv"]**2 * (P["t_base"] + P["h_disc"] - P["t_top"] + 3)
W = P["W_tf"] * g; Wd = (m_disc + 0.5 * m_piv) * g / 1e3; N = W + Wd; ND = P["phi_d"] * W + Wd
chk("N = W + W_mesa (kN)", N, G["N"])
Ro, Ri = Rt, P["D_piv"] / 2 + 15
A = math.pi * (Ro**2 - Ri**2); I = math.pi * (Ro**4 - Ri**4) / 4
chk("q_max interfaz (MPa) — Navier", ND * 1e3 / A + ND * 1e3 * P["e"] * Ro / I, G["q_max"])

# --- cinemática del accionamiento guiado (pasador entre −π/N y +π/N, empuje paralelo a la guía) ---
pitch = 2 * math.pi / P["N_pin"]
ys = [P["R_pin"] * math.sin(-pitch / 2 + pitch * i / 2000) for i in range(2001)]
chk("Carrera requerida (mm)", P["s_free"] + ys[-1] - ys[0], G["carrera_req"])
armmin = min(P["R_pin"] * math.cos(-pitch / 2 + pitch * i / 2000) for i in range(2001))
chk("Brazo mínimo (mm)", armmin, G["brazo_min"])
front = P["l_p"] + 20; rear = 1.25 * P["d_pp"]; Lg = 2 / 3 * (front + rear)
Kg = (1 + 2 * P["mu_g"] * (P["x_g"] - armmin) / Lg) / P["eta_c"]

# --- accionamiento ---
Ab = math.pi / 4 * P["D_bore"]**2
Fst = Ab * P["p_relief"] / 10 / 1e3
chk("Fuerza de calado (kN)", Fst, G["F_calado"])
def H(mu): return mu * N * P["e"] * 4 / 3 * (Ro**3 - Ri**3) / (Ro**4 - Ri**4)
r_u = 2 / 3 * (Ro**3 - Ri**3) / (Ro**2 - Ri**2)
cases = {"nom": (P["mu_nom"], r_u), "dis": (P["mu_d"], P["r_ef"]), "borde": (P["mu_d"], Ro), "cont": (P["mu_cont"], P["r_ef"]), "seco": (P["mu_dry"], r_u)}
for k, (mu, r) in cases.items():
    T = mu * N * r / 1e3 + P["mu_bush"] * H(mu) * P["D_piv"] / 2 / 1e3
    F = T * 1e3 / (P["n_cyl"] * armmin) * Kg
    chk(f"Caso {k}: F por cilindro (kN)", F, G["casos"][k][0])
    chk(f"Caso {k}: FS", Fst / F, G["casos"][k][2])

# --- cadena de empuje (BTH-1, Nd) ---
Nd = P["Nd"]; tpr = max(P["t_pr"], P["t_top"], P["t_bot"])
Ls = P["h_disc"] - tpr
sig = Fst * 1e3 * Ls / 4 / (math.pi * P["d_pin"]**3 / 32)
chk("Pasador de empuje: FU flexión", sig / (P["Fy_pin"] / Nd), G["fu"]["Pasadores de empuje · Flexión (biapoyado entre planchas, carga al centro)"])
chk("Pasador de empuje: FU aplastamiento", Fst * 1e3 / (P["d_pin"] * tpr) / (1.25 * P["Fy"] / Nd), G["fu"]["Pasadores de empuje · Aplastamiento en el agujero de la plancha"])
Mpp = Fst / 2 * (P["t_ch"] / 2 + P["g_ch"] + P["b_eye"] / 4) * 1e3
chk("Pasador articulación: FU flexión", Mpp / (math.pi * P["d_pp"]**3 / 32) / (P["Fy_pp"] / Nd), G["fu"]["Articulaciones · Pasador: flexión (horquilla)"])
hax = P["h_disc"] / 2; aw = 0.707 * P["w_br"]
f = math.hypot(Fst * 1e3 / (4 * aw * P["L_ch"]), Fst * 1e3 * hax / (4 * aw * P["L_ch"]**2 / 6))
chk("Soldadura mejillas–base: FU", f / (0.6 * P["FEXX"] / (1.2 * Nd)), G["fu"]["Articulaciones · Soldadura mejillas–base (4 filetes)"])
Pcr = math.pi**2 * P["E"] * math.pi * P["d_rod"]**4 / 64 / (P["L0"] + P["stroke"])**2 / 1e3
chk("Pandeo del vástago: FU", Fst / (Pcr / 3), G["fu"]["Giro · Pandeo del vástago (biarticulado, longitud extendida)"])
mouth = min(P["x_g"] - P["w_s"] / 2, P["R_pin"] + P["d_pin"] / 2 + 10)
lev = mouth - armmin + P["e_dog"]
chk("Uña: FU flexión en la boca del patín", Fst * 1e3 * lev / (P["dog_h"] * P["dog_b"]**2 / 6) / (P["Fy_dog"] / Nd), G["fu"]["Uña · Flexión en la boca del patín (voladizo)"])
Rg = Fst * (P["x_g"] - armmin) / Lg
chk("Ranura de guía: FU aplastamiento", Rg * 1e3 / (P["h_slot"] * (front + rear) / 3) / (1.25 * P["Fy"] / Nd), G["fu"]["Patín y guía · Aplastamiento de la lengüeta en la ranura de la bancada"])
print("\nRESULTADO:", "sin diferencias" if not fails else "DIFERENCIAS en " + ", ".join(fails))
sys.exit(1 if fails else 0)
