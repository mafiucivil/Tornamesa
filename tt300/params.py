"""Parámetros geométricos tornamesa 300 tf. Unidades: mm. z=0 cara inferior placa base."""
import math

PROJ = "TORNAMESA HIDRÁULICA 300 tf"

# ---------------- comunes ----------------
B = 2000.0          # placa base, lado en Y
BX = 2400.0         # placa base, lado en X (cilindros)
TB = 80.0           # espesor placa base
D_DISC = 2000.0     # disco
TD = 160.0          # altura total disco cajón
TP_TOP = 30.0
TP_BOT = 30.0
GAP = TD - TP_TOP - TP_BOT   # 100 entre planchas
HUB_D = 300.0
RING_T = 25.0
RING_R = [300.0, 550.0, 735.0]
RIB_T = 20.0
N_RIB = 12
RIB_R1 = 880.0

# pivote / buje / tapa
D_PIV = 150.0
D_BUJE_EXT = 190.0
L_BUJE = 100.0
D_CB = 260.0        # contrataladro superior disco
H_CB = 25.0
D_TAPA = 240.0
T_TAPA = 20.0
PIV_UP = 3.0        # sobresale pivote sobre fondo contrataladro
BOLT_PCD = 100.0
N_BOLT = 6

# barras de empuje (perimetrales, entre planchas)
R_BAR = 940.0
D_BAR = 70.0
N_BAR = 36
BAR_ANG0 = 5.0      # 5° + 10°k
R_IDX = R_BAR
D_IDX_HOLE = 71.0
N_IDX = N_BAR
IDX_ANG0 = BAR_ANG0

# izaje disco (M30) y sello
R_M30 = 600.0
M30_ANG = [45, 135, 225, 315]
N_SEAL_BOLT = 36    # M8 radiales en canto plancha inferior a 0°+10°k

# cilindros
F_CYL = 445.0       # kN mín a 700 bar
STROKE = 200.0
L0_CYL = 450.0      # ojal-ojal retraído
D_CYL = 140.0
D_ROD = 90.0
EYE_W = 70.0
EYE_D = 120.0
D_PIN_CYL = 70.0
X_CYL = 1085.0      # eje cilindro / carro / guía
Y_BRK = 818.0       # pasador ménsula (±X_CYL, ±Y_BRK)

# carro de empuje y trinquete
SHOE_X0 = 1020.0    # cara interior del carro
SHOE_X1 = 1150.0
SHOE_L = 300.0
SHOE_FRONT = 20.0   # cara frontal del carro sobre centro de barra
EYE_OFF = 250.0     # centro barra -> pasador ojal vástago (retraído)
PAWL_W = 85.0       # ancho (Y)
PAWL_H = 90.0       # alto (Z)
PAWL_TIP = 905.0    # x de la punta
PAWL_L = 245.0      # largo (X)
SEAT_R = 36.0
RAIL_W, RAIL_H, RAIL_L = 40.0, 30.0, 850.0
FREE = 36.0         # recorrido libre antes de tomar la barra

# ménsula
CHEEK_T = 40.0
CHEEK_GAP = 80.0
CHEEK_L = 280.0
BACK_T = 40.0

# orejas de izaje base
LUG_T = 40.0
LUG_L = 150.0
LUG_H = 170.0
LUG_X = 600.0
LUG_HOLE = 32.0

# sello
SEAL_T = 5.0
BAR_W, BAR_T = 25.0, 6.0

# pastillas UHMW
D_PAD = 170.0
T_PAD = 10.0
D_POCKET = 170.6
H_POCKET = 5.0
RINGS = [(300.0, 6, 30.0), (550.0, 12, 15.0), (735.0, 16, 0.0)]
INOX_T = 3.0
INOX_A = (390.0, 810.0)
INOX_B = (880.0, 1680.0)


def variant(kind):
    """kind: 'U' (UHMW) o 'S' (acero-acero grafito)."""
    g = (H_POCKET + INOX_T) if kind == "U" else 0.0
    v = dict(kind=kind, g=g)
    v["z_base_top"] = TB
    v["z_disc_bot"] = TB + g
    v["z_disc_top"] = TB + g + TD
    v["z_axis"] = v["z_disc_bot"] + TP_BOT + GAP / 2
    v["z_cb_floor"] = v["z_disc_top"] - H_CB
    v["z_piv_top"] = v["z_cb_floor"] + PIV_UP
    v["L_piv"] = v["z_piv_top"]           # desde z=0
    v["z_buje_top"] = v["z_disc_bot"] + L_BUJE
    v["H_cheek"] = v["z_axis"] - TB + 70.0  # sobre cara superior base
    v["shoe_top"] = v["z_axis"] + 70.0
    v["title"] = ("SOLUCIÓN A – PASTILLAS UHMW-PE SOBRE PISTA INOX" if kind == "U"
                  else "SOLUCIÓN B – ACERO-ACERO CON GRASA GRAFITADA")
    v["code"] = "TT300-A" if kind == "U" else "TT300-B"
    return v


def pad_positions():
    out = []
    for r, n, a0 in RINGS:
        for k in range(n):
            a = math.radians(a0 + k * 360.0 / n)
            out.append((r, a0 + k * 360.0 / n, r * math.cos(a), r * math.sin(a)))
    return out


def idx_positions():
    return [(IDX_ANG0 + 10 * k, R_IDX * math.cos(math.radians(IDX_ANG0 + 10 * k)),
             R_IDX * math.sin(math.radians(IDX_ANG0 + 10 * k))) for k in range(N_IDX)]
