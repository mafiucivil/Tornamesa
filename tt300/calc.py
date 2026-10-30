"""Cálculo del accionamiento y verificaciones – tornamesa 300 tf, acero-acero con grasa grafitada."""
import math
import params as P

G = 9.80665
CAP_TF = 300.0
W = CAP_TF * G                      # kN
PHI_D = 1.10
W_DISC = 1922.0 * G / 1000          # kN, disco cajón + buje
N_F = W + W_DISC                    # carga normal en la interfaz de giro (servicio)
R_C, R_I = 1000.0, 95.0             # contacto anular (mm)
R_UNIF = 2 / 3 * (R_C ** 3 - R_I ** 3) / (R_C ** 2 - R_I ** 2) / 1000   # m
ARM = P.R_BAR * math.cos(math.radians(P.BAR_ANG0)) / 1000            # m, brazo mínimo
DELTA = (P.X_CYL - P.R_BAR * math.cos(math.radians(P.BAR_ANG0))) / 1000
LG = (P.SHOE_L - 50) / 1000         # m, separación reacciones de guía
MU_G = 0.15                         # carro / guía (bandas UHMW, con grasa)
ETA_C = 0.95                        # rendimiento del cilindro (sellos)
K_LOSS = (1 + 2 * MU_G * DELTA / LG) / ETA_C
T_PIV = 0.20 * 0.05 * W * 0.075     # kN·m, buje del pivote
A_CYL = 445e3 / 70.0                # mm² (Ø90)
P_MAX, P_OP = 700.0, 600.0          # bar
F_CYL_MAX = A_CYL * P_MAX / 10 / 1000   # kN

CASES = [
    ("Nominal: grasa grafitada limpia", 0.15, R_UNIF),
    ("DISEÑO: lubricado, límite sup. + presión cargada al borde", 0.20, 0.80),
    ("Contaminado: arena/película degradada", 0.25, 0.80),
    ("Sin lubricación (acero seco) – PROHIBIDO", 0.50, R_UNIF),
]


def case(mu, r):
    T = mu * N_F * r + T_PIV
    Fb = T / (2 * ARM)
    Fc = Fb * K_LOSS
    p = Fc * 1e3 / A_CYL * 10
    return dict(T=T, Fb=Fb, Fc=Fc, p=p, FS=F_CYL_MAX / Fc)


def mu_max(r, p_bar=P_MAX):
    Fc = A_CYL * p_bar / 10 / 1000
    T = Fc / K_LOSS * 2 * ARM
    return (T - T_PIV) / (N_F * r)


def nf(x, d=0):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


if __name__ == "__main__":
    print("W", W, "N_F", N_F, "R_unif", R_UNIF, "ARM", ARM, "DELTA", DELTA, "K_LOSS", K_LOSS, "Tpiv", T_PIV, "Fmax", F_CYL_MAX)
    for n, mu, r in CASES:
        c = case(mu, r)
        print(f"{n:55s} mu={mu} r={r:.3f} T={c['T']:.0f} Fb={c['Fb']:.0f} Fc={c['Fc']:.0f} p={c['p']:.0f} FS={c['FS']:.2f}")
    for r in (R_UNIF, 0.80, 0.94):
        print("mu_max r", round(r, 3), round(mu_max(r), 3), "@600", round(mu_max(r, 600), 3))


# ---------------- verificaciones de elementos (300 tf) ----------------
FY = 345.0                          # A572 Gr.50 / S355
F_STALL = F_CYL_MAX                 # kN: fuerza de calado (válvula de alivio 700 bar)


def verifs():
    ND = PHI_D * W + W_DISC
    A_c = math.pi * (R_C ** 2 - R_I ** 2)
    q_avg = ND * 1e3 / A_c
    q_max = q_avg * (1 + 4 * 150 / R_C * (R_C ** 2) / (R_C ** 2 + R_I ** 2))   # e = 150, anular: M/S
    # barra 4f Ø70, luz libre 100, carga en 90 central
    L, c, d = 100.0, 90.0, 70.0
    Mss = F_STALL / 4 * (L - c / 2) / 1e3          # kN·m (rotulada)
    Mfe = F_STALL * (3 * L ** 2 - c ** 2) / (24 * L) / 1e3   # kN·m (empotrada)
    Mn_bar = FY * d ** 3 / 6 / 1.67 / 1e6          # AISC F11.1, Ω = 1,67
    tau_bar = 4 * F_STALL / 2 * 1e3 / (3 * math.pi * d ** 2 / 4)
    Ew = 12.0
    tw_V = F_STALL / 2 * 1e3 / (math.pi * d * Ew)
    tw_M = Mfe * 1e6 / (math.pi * (d / 2) ** 2 * Ew)
    tw = math.hypot(tw_V, tw_M)
    Fw = 0.6 * 490 / 2.0                           # AISC J2.5, Ω = 2,0
    brg = F_STALL / 2 * 1e3 / (30 * d)             # aplastamiento en agujero de plancha
    # trinquete
    lev = (P.SHOE_X0 - P.R_BAR * math.cos(math.radians(P.BAR_ANG0)))
    Mp = F_STALL * lev / 1e3
    sp = Mp * 1e6 / (P.PAWL_H * P.PAWL_W ** 2 / 6)
    # guía embutida
    Rg = F_STALL * DELTA / LG
    brg_g = Rg * 1e3 / (10 * 150)
    Mg = Rg * 15 / 1e3
    Mn_g = FY * 150 * 40 ** 2 / 4 / 1.67 / 1e6
    # mejillas ménsula
    sc = F_STALL * (160 - 80) * 1e3 / (2 * 40 * 280 ** 2 / 6)
    # pasador Ø70 doble corte
    Ap = math.pi * 70 ** 2 / 4
    tp = F_STALL / 2 * 1e3 / Ap
    Mpin = F_STALL / 2 * (40 / 2 + 5 + 70 / 4) / 1e3   # kN·m, horquilla: a=40, holgura 5, ojal 70
    sb_pin = Mpin * 1e6 / (math.pi * 70 ** 3 / 32)
    # buje / pivote
    H = 0.055 * W
    pb = H * 1e3 / (P.D_PIV * P.L_BUJE)
    pb1 = F_STALL * 1e3 / (P.D_PIV * P.L_BUJE)
    Mpiv = H * 0.050
    spiv = Mpiv * 1e6 / (math.pi * 150 ** 3 / 32)
    # pandeo vástago
    I = math.pi * 90 ** 4 / 64
    Pcr = math.pi ** 2 * 200e3 * I / 650 ** 2 / 1e3
    rows = [
        ("Interfaz de giro: presión media / máx. (e = 150)", f"{q_avg:.2f} / {q_max:.2f} MPa", "10,0 MPa", q_max / 10, "Criterio acero/acero lubricado"),
        ("Plancha sup. 4a – flexión entre almas", "67 MPa", "207 MPa", 67 / 207, "AISC F11, Ω = 1,67"),
        ("Plancha inf. 4b – flexión entre almas", "70 MPa", "207 MPa", 70 / 207, "AISC F11, Ω = 1,67"),
        ("Almas 4d – compresión local", "13 MPa", "207 MPa", 13 / 207, "AISC J10.2"),
        ("Barra 4f Ø70 – flexión (rotulada, F calado)", f"{Mss:.2f} kN·m", f"{Mn_bar:.2f} kN·m", Mss / Mn_bar, "AISC F11.1, Ω = 1,67"),
        ("Barra 4f Ø70 – corte", f"{tau_bar:.0f} MPa", f"{0.6 * FY / 1.5:.0f} MPa", tau_bar / (0.6 * FY / 1.5), "AISC G1, Ω = 1,50"),
        ("Soldadura barra 4f – bisel 15 (E = 12), V+M", f"{tw:.0f} MPa", f"{Fw:.0f} MPa", tw / Fw, "AISC J2.5 / AWS D1.1"),
        ("Agujero Ø71 en 4a/4b – aplastamiento", f"{brg:.0f} MPa", f"{1.8 * FY / 2:.0f} MPa", brg / (0.9 * FY), "AISC J7, Ω = 2,0"),
        ("Trinquete pos 11 – flexión en boca", f"{sp:.0f} MPa", "400 MPa", sp / 400, "Fy/Nd, Nd = 2,0 (Fy 800)"),
        ("Guía pos 22 – aplastamiento en ranura", f"{brg_g:.0f} MPa", f"{0.9 * FY:.0f} MPa", brg_g / (0.9 * FY), "AISC J7, Ω = 2,0"),
        ("Guía pos 22 – flexión en raíz", f"{Mg:.2f} kN·m", f"{Mn_g:.2f} kN·m", Mg / Mn_g, "AISC F11.1, Ω = 1,67"),
        ("Mejillas ménsula pos 2 – flexión base", f"{sc:.0f} MPa", "207 MPa", sc / 207, "AISC F11 / CJP J2"),
        ("Pasador Ø70 – flexión (horquilla 40/80)", f"{sb_pin:.0f} MPa", "325 MPa", sb_pin / 325, "Fy/Nd, Nd = 2,0 (Fy 650)"),
        ("Pasador Ø70 – corte doble", f"{tp:.0f} MPa", "188 MPa", tp / 188, "ASME BTH-1 3-2.2: Fy/(Nd·√3)"),
        ("Buje pos 6 – presión (H = 5,5 % W)", f"{pb:.1f} MPa", "30 MPa", pb / 30, "Fabricante bronce-grafito"),
        ("Pivote pos 5 – flexión", f"{spiv:.1f} MPa", "325 MPa", spiv / 325, "Fy/Nd, Nd = 2,0"),
        ("Vástago Ø90 – pandeo (L = 650, rótulas)", f"{F_STALL:.0f} kN", f"{Pcr / 3:.0f} kN", F_STALL / (Pcr / 3), "Euler, FS = 3,0"),
    ]
    extra = dict(q_avg=q_avg, q_max=q_max, Mss=Mss, Mfe=Mfe, tw=tw, lev=lev, Rg=Rg, pb1=pb1, Pcr=Pcr, H=H)
    return rows, extra


if __name__ == "__main__":
    r, e = verifs()
    for x in r: print(f"{x[0]:50s} {x[1]:>18s} {x[2]:>12s} FU={x[3]:.2f}")
    print(e)
