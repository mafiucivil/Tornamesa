"""Re-cálculo independiente TT300-B (revisor). Unidades N, mm, MPa salvo indicación."""
import math
g = 9.80665; rho = 7.85e-6
pi = math.pi
# ---- parámetros de diseño (enunciado) ----
W = 300 * g                     # kN
e = 150.0; phid = 1.10
Rd = 1000.0; rh = 150.0; tt = tb = 30.0; gap = 100.0; TD = tt + tb + gap
rings = [300, 550, 735]; tr = 25; Nrib = 12; trib = 20; Rrib = 880
Rb = 940.0; db = 70.0; Nb = 36; dh = 71.0
Ri = 95.0
# ---- masa ----
Ap = pi * (Rd**2 - rh**2) - Nb * pi * (dh / 2)**2
m_top = Ap * tt * rho; m_bot = Ap * tb * rho
m_hub = rho * pi / 4 * (300**2 * TD - 190**2 * 100 - 160**2 * (TD - 100) - (260**2 - 160**2) * 25)
m_ring = sum(2 * pi * r * tr * gap * rho for r in rings)
m_rib = Nrib * trib * gap * (Rrib - rh - 3 * tr) * rho
m_bar = Nb * pi * db**2 / 4 * TD * rho
m_tot = m_top + m_bot + m_hub + m_ring + m_rib + m_bar + 8.1
print(f"masa: top {m_top:.1f} bot {m_bot:.1f} hub {m_hub:.1f} rings {m_ring:.1f} ribs {m_rib:.1f} bars {m_bar:.1f} total {m_tot:.1f} kg")
Wd = m_tot * g / 1000
N = W + Wd; ND = phid * W + Wd
r_u = 2 / 3 * (Rd**3 - Ri**3) / (Rd**2 - Ri**2) / 1000
th = pi / Nb
a = Rb * math.cos(th)
useful = 2 * Rb * math.sin(th); sreq = 36 + useful
Delta = 1085 - a; Kg = 1 + 2 * 0.15 * Delta / 250; K = Kg / 0.95
A = pi * 90**2 / 4; Fmax = A * 700 / 10 / 1000; Falarm = A * 600 / 10 / 1000
Tpiv = 0.20 * 0.05 * W * 0.075
print(f"W {W:.3f} Wd {Wd:.3f} N {N:.3f} ND {ND:.3f} r_u {r_u:.5f} a {a:.3f} useful {useful:.3f} sreq {sreq:.3f}")
print(f"Delta {Delta:.3f} Kg {Kg:.5f} K {K:.5f} A {A:.2f} Fmax {Fmax:.3f} Falarm {Falarm:.3f} Tpiv {Tpiv:.4f}")
print(f"Ybrk {Rb*math.sin(th)+250+450+36:.2f}")

def case(mu, r):
    Tf = mu * N * r; T = Tf + Tpiv; Fb = T / (2 * a / 1000); Fc = K * Fb
    return dict(Tf=Tf, T=T, Fb=Fb, Fc=Fc, p=Fc * 1e3 / A * 10, FS=Fmax / Fc)
cases = [("nom", 0.15, r_u), ("dis", 0.20, 0.80), ("con", 0.25, 0.80), ("dry", 0.50, r_u),
         ("dis r=0.94", 0.20, 0.94), ("dis r=1.00", 0.20, 1.00), ("con r=1.00", 0.25, 1.00)]
for k, mu, r in cases:
    c = case(mu, r)
    print(f"{k:12s} mu {mu} r {r:.4f} Tf {c['Tf']:.2f} T {c['T']:.2f} Fb {c['Fb']:.2f} Fc {c['Fc']:.2f} p {c['p']:.1f} FS {c['FS']:.3f}")
def mumax(r, p):
    return ((A * p / 10 / 1000) / K * (2 * a / 1000) - Tpiv) / (N * r)
for r in (r_u, 0.8, 0.94, 1.0):
    print(f"mumax r {r:.3f}: 700 bar {mumax(r,700):.4f}  600 bar {mumax(r,600):.4f}")
d = case(0.2, 0.8); a2 = 2 * a / 1000
bd = [d['Tf'] / a2, Tpiv / a2, d['Fb'] * (Kg - 1), d['Fc'] - d['Fb'] * Kg]
print("breakdown", [round(x, 3) for x in bd], "sum", round(sum(bd), 3))
# exact guide-friction alternative: Lg = 2/3 Ls (linear distribution over 300 mm shoe)
for Lg in (250, 200, 150):
    Kx = (1 + 2 * 0.15 * Delta / Lg) / 0.95
    print(f"Lg {Lg}: K {Kx:.4f} Fc_dis {Kx*d['Fb']:.1f} kN  Rg(Fmax) {Fmax*Delta/Lg:.1f} kN")
# ---- contacto ----
Ac = pi * (Rd**2 - Ri**2)
q_avg = ND * 1e3 / Ac; q_max = q_avg * (1 + 4 * e * Rd / (Rd**2 + Ri**2))
q_top = phid * W * 1e3 / (pi * 800**2)
print(f"Ac {Ac:.0f} q_avg {q_avg:.4f} q_max {q_max:.4f} q_top {q_top:.4f}")
# fuerza lateral por fricción con presión lineal (excentricidad e)
Ix = pi * (Rd**4 - Ri**4) / 4
k_lin = N * 1e3 * e / Ix            # q = q0 + k x (N/mm^3)
for mu in (0.15, 0.2, 0.25, 0.5):
    Flat = mu * k_lin * pi * (Rd**3 - Ri**3) / 3 / 1e3
    print(f"H friccion mu {mu}: {Flat:.1f} kN = {Flat/W*100:.2f}% W")
# ---- suelo ----
Wtot = W + (m_tot + 3070) * g / 1000
gavg = Wtot * 1e3 / (2400 * 2000); gmax = gavg * (1 + 6 * e / 2000)
gbi = gavg * (1 + 6 * e * math.hypot(1 / 2400, 1 / 2000))
print(f"Wtot {Wtot:.2f} g_avg {gavg:.4f} g_max(uniax) {gmax:.4f} g_max(biax, peor ángulo) {gbi:.4f}")
gcirc = Wtot * 1e3 / (pi * Rd**2); print(f"presión bajo huella del disco Ø2000 (sin reparto de placa): {gcirc:.3f} med, {gcirc*(1+4*e/Rd):.3f} máx")
# ---- verificaciones ----
F = Fmax; Fy = 345
print("\n--- verifs ---")
ov = 200; lever = 130
Mov = q_max * ov**2 / 2; print(f"global voladizo σ {Mov/(30*lever):.3f}")
L = 100; c = 90
Mss = F / 4 * (L - c / 2) / 1e3; Mfe = F * (3 * L * L - c * c) / (24 * L) / 1e3
Z = db**3 / 6; S = pi * db**3 / 32
Mn_tool = Fy * Z / 1.67 / 1e6; Mn_F11 = min(Fy * Z, 1.6 * Fy * S) / 1.67 / 1e6
print(f"barra Mss {Mss:.4f} Mfe {Mfe:.4f} Mn/Ω tool {Mn_tool:.3f} F11 (cap 1.6S) {Mn_F11:.3f}  Z/S {Z/S:.3f}")
tau = 4 * (F / 2) * 1e3 / (3 * pi * db**2 / 4); print(f"tau barra {tau:.2f}")
Ew = 12
tv = F / 2 * 1e3 / (pi * db * Ew); tm = Mfe * 1e6 / (pi * (db / 2)**2 * Ew)
print(f"sold tv {tv:.2f} tm {tm:.2f} res {math.hypot(tv,tm):.2f} cap {0.6*490/2}")
print(f"aplast agujero {(F/2)*1e3/(30*db):.2f}")
# alternativas: luz entre planos medios (130) y entre caras exteriores (160)
for Ls in (100, 130, 160):
    Ms = F / 4 * (Ls - c / 2) / 1e3; Mf = F * (3 * Ls * Ls - c * c) / (24 * Ls) / 1e3
    tmx = Mf * 1e6 / (pi * (db / 2)**2 * Ew)
    print(f" L={Ls}: Mss {Ms:.2f} (FU {Ms/Mn_F11:.2f}) Mfe {Mf:.2f} sold res {math.hypot(tv,tmx):.1f} FU {math.hypot(tv,tmx)/147:.2f}")
lev = 1020 - a
sp = F * lev * 1e3 / (90 * 85**2 / 6); print(f"trinquete lev {lev:.3f} σ {sp:.2f}")
Rg = F * Delta / 250; print(f"guia Rg {Rg:.3f} σb {Rg*1e3/(10*150):.2f} Mg {Rg*15/1e3:.4f} Mng {Fy*150*40**2/4/1.67/1e6:.3f}")
print(f"mejilla σ {F*80*1e3/(2*40*280**2/6):.3f}")
Mpin = F / 2 * (20 + 5 + 17.5) / 1e3
print(f"pasador M {Mpin:.4f} σ {Mpin*1e6/(pi*70**3/32):.2f} τ {(F/2)*1e3/(pi*70**2/4):.2f} adm τ {650/(2*math.sqrt(3)):.2f}")
print(f"pasador aplast. mejilla {(F/2)*1e3/(40*70):.1f} ojal {F*1e3/(70*70):.1f}")
H = 0.055 * W
print(f"pivote H {H:.3f} p {H*1e3/(150*100):.3f} σ {H*50*1e3/(pi*150**3/32):.3f}")
I = pi * 63**4 / 64; Pcr = pi**2 * 2e5 * I / 650**2 / 1e3
print(f"pandeo Pcr {Pcr:.1f} Pcr/3 {Pcr/3:.2f}")
# reacción en boca del carro del trinquete (modelo de apoyos del FEA)
Xs = a - 905; x1 = 115 + 12.5; x2 = 245 - 12.5
R2 = F * (x1 - Xs) / (x2 - x1); R1 = F + R2
print(f"trinquete: reacción boca {R1:.1f} kN, labio post {R2:.1f} kN; aplast. boca (25x90) {R1*1e3/(25*90):.0f} MPa")
# Hertz asiento R36 / barra r35
Rs = 1 / (1 / 35 - 1 / 36); q = F * 1e3 / 90; Es = 2e5 / (2 * (1 - 0.09))
bH = math.sqrt(4 * q * Rs / (pi * Es)); p0 = 2 * q / (pi * bH)
print(f"Hertz conforme: b {bH:.2f} mm p0 {p0:.0f} MPa")
print(f"desplazamiento radial relativo barra/asiento en carrera: {Rb-a:.3f} mm vs holgura radial {36-35} mm")

# ---- flexión global axisimétrica del cajón (placa sándwich, borde libre) ----
import numpy as np
n = 20001; r = np.linspace(1e-6, Rd, n)
qb = ND * 1e3 / (pi * Rd**2)        # reparto uniforme inferior (aprox. sin agujero central)
p = np.where(r <= 800, -q_top, 0.0) + qb    # neto hacia arriba
# corte por unidad de longitud Q(r) = (1/r)∫ p ρ dρ
cum = np.concatenate([[0], np.cumsum(0.5 * (p[1:] * r[1:] + p[:-1] * r[:-1]) * np.diff(r))])
Q = cum / r
print(f"\nGlobal: desequilibrio Q(R)·2πR = {Q[-1]*2*pi*Rd/1e3:.1f} kN (≈0)")
nu = 0.3
# ψ'' + ψ'/r − ψ/r² = Q/D  => (1/r (rψ)')' = Q/D ; trabajar con D=1 (momentos independientes de D)
Iq = np.concatenate([[0], np.cumsum(0.5 * (Q[1:] + Q[:-1]) * np.diff(r))])  # ∫Q dr
J = np.concatenate([[0], np.cumsum(0.5 * (Iq[1:] * r[1:] + Iq[:-1] * r[:-1]) * np.diff(r))])
psi_p = J / r
dpsi_p = np.gradient(psi_p, r)
# ψ = ψp + C r ; Mr = ψ' + ν ψ/r → Mr(R) = dψp(R) + ν ψp(R)/R + C(1+ν) = 0
C = -(dpsi_p[-1] + nu * psi_p[-1] / Rd) / (1 + nu)
psi = psi_p + C * r; dpsi = dpsi_p + C
Mr = dpsi + nu * psi / r; Mt = psi / r + nu * dpsi
i = slice(5, n - 5)
Mmax = max(abs(Mr[i]).max(), abs(Mt[i]).max())
print(f"Mr centro {Mr[50]:.0f}  Mr(800) {Mr[np.searchsorted(r,800)]:.0f}  Mθ(R) {Mt[-6]:.0f}  |M|max {Mmax:.0f} N·mm/mm")
print(f"σ membrana global = M/(t·130) = {Mmax/(30*130):.2f} MPa (herramienta 8,55)")
for rr in (735, 800, 880):
    k = np.searchsorted(r, rr); V = abs(Q[k]) * 2 * pi * rr
    print(f" corte total en r={rr}: {V/1e3:.0f} kN → τ nervios 12x20x100 = {V/(12*20*100):.1f} MPa")
