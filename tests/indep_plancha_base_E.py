"""Verificación independiente: plancha base bajo el soporte del ojal E (modo pivotado, drive_mode = 2) y comparación con KIET.

Revisor independiente. No lee packages/*.js. Parámetros: tests/golden/params_defaults.json; golden: tests/golden/tt300c_defaults.json
(tolerancia 0,1 %); geometría del soporte y de los casos: salida JSON de `node tools/export_design.js` (caja negra).

  §1 Estática global del accionamiento (base, mesa, cilindros): el cilindro es un miembro de dos fuerzas E–Q colineal; con dos cilindros
     en E₂ = −E₁ la suma de momentos sobre la base es un par puro en z (sin vuelco); el par local M = F·h de cada soporte debe viajar
     por la plancha hasta donde se equilibra (la mesa cargada cerca de Q o el otro soporte).
  §2 Réplica de la franja del núcleo (M_corte = M·(1 − a/s_H), b = w + a, σ = 6·M_corte/(b·t²)) frente al golden.
  §3 Criterio: ASME BTH-1 Cat. B (Nd = 3,0, decisión del mandante 30-10-2026). Para una plancha en flexión fuera de su plano (sección
     rectangular maciza en flexión respecto del eje menor) BTH-1 §3-2.3.5 da F_b = 1,25·Fy/Nd (cita de memoria: confirmar con el texto);
     el núcleo usa Fy/Nd (§3-2.3). Se informan ambos y, como referencia, Nd = 2,0 (Cat. A) y AISC 360-22 F11 (M_n = Fy·Z, Ω = 1,67).
  §4 FEA propia de Mindlin (Q4, flexión 2×2, corte 1 punto) de la base completa: dos soportes rígidos (3 gdl maestros cada uno, M₂ = −M₁),
     losa unilateral (conjunto activo) y mesa CARGADA como cuerpo rígido (3 gdl) apoyado en la plancha por contacto unilateral en
     R ≤ D/2 con su peso (no un empotramiento: el borde de la mesa puede despegar). Tensión en la cara σ = 6m/t² (von Mises).
     Se informan el pico (en la esquina de la huella rígida: singular, depende de la malla) y el máximo a > 100 mm de la huella.
     Casos: diseño actual (18 mm), solución tipo KIET (inserto de esquina) y geometría KIET medida en el plano vectorial.

Ejecutar: python3 -I tests/indep_plancha_base_E.py [--rapido]     (completo ≈ 12 min por la FEA con contacto; --rapido omite la §4, ≈ 25 s)
Sale con 0 si la réplica coincide con el golden; 1 si hay diferencias; 2 sin node."""
import json, math, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = json.loads((ROOT / "tests" / "golden" / "params_defaults.json").read_text()); P["drive_mode"] = 2
G = json.loads((ROOT / "tests" / "golden" / "tt300c_defaults.json").read_text())
if not shutil.which("node"):
    print("node no disponible"); sys.exit(2)
with tempfile.TemporaryDirectory() as td:
    f = pathlib.Path(td) / "p.json"; f.write_text(json.dumps({"drive_mode": 2}))
    D = json.loads(subprocess.run(["node", str(ROOT / "tools" / "export_design.js"), str(f)], capture_output=True, text=True, check=True, cwd=str(ROOT)).stdout)
PV = D["pivotado"]; SE = PV["fabricacion"]["soporte_E"]; DV = D["derivados"]
fails = []


def chk(name, mine, tool, tol=1e-3):
    ok = abs(mine - tool) <= tol * abs(tool)
    print(f"{'OK ' if ok else 'XX '} {name:66s} indep {mine:11.4f}  golden {tool:11.4f}  Δ {(mine - tool) / tool * 100:+.4f} %")
    if not ok: fails.append(name)


Fy, Nd, t = P["Fy"], P["Nd"], P["t_base"]
A_p = math.pi / 4 * P["D_bore"] ** 2; A_a = A_p - math.pi / 4 * P["d_rod"] ** 2
F_cal = A_p * P["p_relief"] / 10 / 1e3          # kN (bar → MPa: /10)
F_ret = A_a * P["p_ret"] / 10 / 1e3
cas = {c["id"]: c for c in DV["casos"]}
F_nom, F_dis = cas["nom"]["F"], cas["dis"]["F"]
z_inf = [p for p in SE["piezas"] if p["id"] == "tapa_inf"][0]["z"]; z_sup = [p for p in SE["piezas"] if p["id"] == "tapa_sup"][0]["z"]
h = (sum(z_inf) / 2 + sum(z_sup) / 2) / 2 - t        # eje del cilindro sobre la cara superior de la plancha (resultante F/2 en cada tapa)
E1 = tuple(PV["E"]); O_loc = (-E1[0], -E1[1])
rects = [(min(x for x, _ in p["poligono_local"]), max(x for x, _ in p["poligono_local"]), min(y for _, y in p["poligono_local"]), max(y for _, y in p["poligono_local"]))
         for p in SE["piezas"] if p["id"].startswith(("pared", "munon"))]

print("== §1 Estática global (dos cilindros en paralelo, E₂ = −E₁) ==")
print(f"    F: nominal {F_nom:.1f} kN (μ {cas['nom']['mu']}), diseño {F_dis:.1f} kN ({cas['dis']['p']:.0f} bar), calado {F_cal:.1f} kN ({P['p_relief']} bar); retorno {F_ret:.1f} kN")
print(f"    h = eje sobre la plancha = {h:.1f} mm; el roce mesa–base y la fuerza del soporte entran en la misma cara (z = t): el brazo que lleva la plancha es h")
psi_band = SE["ventana"]["sector_deg"]
for psi in (psi_band[0], psi_band[3]):
    u = (math.cos(math.radians(psi)), math.sin(math.radians(psi)))
    Fb1 = (-F_cal * u[0], -F_cal * u[1]); Fb2 = (-Fb1[0], -Fb1[1])           # sobre la base (empuje: el cilindro empuja E alejándolo de Q)
    M1 = (-h * Fb1[1] / 1e3, h * Fb1[0] / 1e3); M2 = (-M1[0], -M1[1])         # kN·m, par local de cada soporte
    Mz = (E1[0] * Fb1[1] - E1[1] * Fb1[0] + (-E1[0]) * Fb2[1] - (-E1[1]) * Fb2[0]) / 1e3
    print(f"    ψ = {psi:6.2f}°: ΣF = ({Fb1[0] + Fb2[0]:.1e}; {Fb1[1] + Fb2[1]:.1e}) kN; ΣM_horiz = ({M1[0] + M2[0]:.1e}; {M1[1] + M2[1]:.1e}); "
          f"M local = {math.hypot(*M1):.2f} kN·m por soporte; par en z de los cilindros = {Mz:.1f} kN·m (lo toma el roce)")
print("    Mesa: recibe −F en Q a la misma altura (miembro de dos fuerzas colineal): par local −M en Q. Con la mesa cargada, el par de E se cierra")
print("    con el de Q por la plancha (E → borde de la mesa) y la redistribución de presión bajo la mesa; con la mesa vacía no hay precarga y el par")
print("    va de E₁ a E₂ por la plancha (torsión de la base). En los dos caminos el tramo de plancha entre el soporte y la mesa lleva ≈ M.")

print("== §2 Réplica de la franja del núcleo frente al golden ==")
VV = [(x, y) for (x0, x1, y0, y1) in rects for x in (x0, x1) for y in (y0, y1)]


def strip(F_, sgn):
    best = None
    for psi in psi_band:
        u_ = (math.cos(math.radians(psi)), math.sin(math.radians(psi))); f_ = (sgn * u_[0], sgn * u_[1]); g_ = (-f_[1], f_[0])
        pf = [p[0] * f_[0] + p[1] * f_[1] for p in VV]; pg = [p[0] * g_[0] + p[1] * g_[1] for p in VV]
        toe = max(pf); a_ = toe - min(pf); w_ = max(pg) - min(pg); sH = toe - (O_loc[0] * f_[0] + O_loc[1] * f_[1]) + P["D_top"] / 2
        M_ = F_ * 1e3 * h; Mc = M_ * (1 - a_ / sH) if sH > a_ else M_; b_ = w_ + a_; s_ = 6 * Mc / (b_ * t * t)
        if best is None or s_ > best["s"]: best = dict(s=s_, M=M_, a=a_, b=b_, sH=sH, psi=psi)
    return best


sE, sR = strip(F_cal, -1), strip(F_ret, 1)
gk = {k.split(" — ")[0]: v for k, v in G["fu"].items()}
kE = "Soporte del ojal E · Plancha base bajo el soporte del ojal E: flexión sin anclaje, empuje a calado"
kR = "Soporte del ojal E · Plancha base bajo el soporte del ojal E: flexión sin anclaje, retorno (atasco)"
kC = "Soporte del ojal E · Plancha base bajo el soporte del ojal E: corte de la franja (empuje a calado)"
chk("Franja, empuje a calado: FU = σ/(Fy/Nd)", sE["s"] / (Fy / Nd), gk[kE])
chk("Franja, retorno (atasco): FU", sR["s"] / (Fy / Nd), gk[kR])
chk("Franja, corte τ = 1,5·(M/a)/(b·t) / (Fy/(Nd·√3))", 1.5 * sE["M"] / sE["a"] / (sE["b"] * t) / (Fy / (Nd * math.sqrt(3))), gk[kC])

print("== §3 Criterio de la flexión de la plancha (misma σ de la franja) ==")
caps = [("Fy/Nd, Nd = 3 (núcleo, BTH-1 §3-2.3)", Fy / Nd), ("1,25·Fy/Nd, Nd = 3 (BTH-1 §3-2.3.5, eje menor)", 1.25 * Fy / Nd),
        ("1,25·Fy/Nd, Nd = 2 (Cat. A, solo referencia)", 1.25 * Fy / 2), ("AISC 360-22 F11: 1,5·Fy/1,67 (ASD, referencia)", 1.5 * Fy / 1.67)]
for nm, cp in caps:
    print(f"    {nm:52s} cap {cp:6.1f} MPa   franja empuje FU {sE['s'] / cp:5.2f}   retorno FU {sR['s'] / cp:5.2f}")

if "--rapido" in sys.argv:
    print("\nRESULTADO:", "sin diferencias" if not fails else "DIFERENCIAS: " + "; ".join(fails)); sys.exit(1 if fails else 0)

# ---------------------------------------------------------------- §4 FEA propia ------------------------------------------------------
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
Es, nu = P["E"], P["nu"]


def unit_K(hm):
    """Rigidez de un elemento cuadrado de lado hm: K = t³·Kb1 + t·Ks1 (Mindlin, flexión 2×2, corte 1 punto)."""
    xi_n = np.array([-1, 1, 1, -1]); et_n = np.array([-1, -1, 1, 1]); a = hm / 2; Kb = np.zeros((12, 12)); Ks = np.zeros((12, 12))
    Db1 = Es / (12 * (1 - nu ** 2)) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]]); Ds1 = 5 / 6 * Es / (2 * (1 + nu)) * np.eye(2)
    for xi in (-1 / math.sqrt(3), 1 / math.sqrt(3)):
        for et in (-1 / math.sqrt(3), 1 / math.sqrt(3)):
            dx = 0.25 * xi_n * (1 + et_n * et) / a; dy = 0.25 * et_n * (1 + xi_n * xi) / a; B = np.zeros((3, 12))
            B[0, 1::3] = dx; B[1, 2::3] = dy; B[2, 1::3] = dy; B[2, 2::3] = dx; Kb += B.T @ Db1 @ B * a * a
    N = np.full(4, 0.25); dx = 0.25 * xi_n / a; dy = 0.25 * et_n / a; B = np.zeros((2, 12))
    B[0, 0::3] = dx; B[0, 1::3] = N; B[1, 0::3] = dy; B[1, 2::3] = N; Ks += B.T @ Ds1 @ B * 4 * a * a
    return Kb, Ks, dx, dy


def fea(Bs, hm, tfun, supports, W_tab, R_tab, kslab=100.0, ktab=100.0):
    """supports: [(mask(x,y), (xc,yc), (Mx,My) N·mm, W N)]. Devuelve (X, Y, w, S[xc,yc,σvm,mx,my,mxy,t], convergió)."""
    n = int(round(Bs / hm)); xs = np.linspace(-Bs / 2, Bs / 2, n + 1); X, Y = [a.ravel() for a in np.meshgrid(xs, xs, indexing="ij")]
    nn = X.size; ndof = 3 * nn; I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij"); I = I.ravel(); J = J.ravel()
    els = np.stack([I * (n + 1) + J, (I + 1) * (n + 1) + J, (I + 1) * (n + 1) + J + 1, I * (n + 1) + J + 1], 1)
    te = np.array([tfun(x, y) for x, y in zip(X[els].mean(1), Y[els].mean(1))]); Kb, Ks, dxc, dyc = unit_K(hm)
    dof = (3 * els[:, :, None] + np.arange(3)).reshape(-1, 12)
    vals = (te[:, None, None] ** 3 * Kb + te[:, None, None] * Ks).reshape(-1)
    K = sp.csr_matrix((vals, (np.repeat(dof, 12, 1).ravel(), np.tile(dof, (1, 12)).ravel())), shape=(ndof, ndof))
    Ar = np.full(nn, hm * hm); ed = (np.abs(X) > Bs / 2 - 1e-6) | (np.abs(Y) > Bs / 2 - 1e-6); co = (np.abs(X) > Bs / 2 - 1e-6) & (np.abs(Y) > Bs / 2 - 1e-6)
    Ar[ed] /= 2; Ar[co] /= 2
    tn = np.array([tfun(x, y) for x, y in zip(X, Y)]); fv = np.zeros(ndof); fv[0::3] -= 7.7e-5 * tn * Ar          # peso propio
    slave = -np.ones(nn, int)
    for k, (m, _, _, _) in enumerate(supports): slave[np.array([m(x, y) for x, y in zip(X, Y)])] = k
    fr_n = np.where(slave < 0)[0]; base = 3 * fr_n.size; it0 = base + 3 * len(supports); nred = it0 + 3
    r_, c_, v_ = [], [], []
    for i, nd in enumerate(fr_n): r_ += [3 * nd, 3 * nd + 1, 3 * nd + 2]; c_ += [3 * i, 3 * i + 1, 3 * i + 2]; v_ += [1.0] * 3
    for nd in np.where(slave >= 0)[0]:
        k = slave[nd]; xc, yc = supports[k][1]; m0 = base + 3 * k
        r_ += [3 * nd] * 3 + [3 * nd + 1, 3 * nd + 2]; c_ += [m0, m0 + 1, m0 + 2, m0 + 1, m0 + 2]; v_ += [1.0, -(X[nd] - xc), -(Y[nd] - yc), 1.0, 1.0]
    T = sp.csr_matrix((v_, (r_, c_)), shape=(ndof, nred)); fr = T.T @ fv
    for k, (_, _, (Mx, My), W) in enumerate(supports):
        m0 = base + 3 * k; fr[m0 + 1] += My; fr[m0 + 2] -= Mx; fr[m0] -= W                 # trabajo: My·βx − Mx·βy (u = z·βx, v = z·βy)
    fr[it0] -= W_tab
    Kr = (T.T @ K @ T).tocsr(); wmap = T[0::3, :].tocsr(); ks = kslab * Ar; kt = ktab * Ar
    rows = np.where(X ** 2 + Y ** 2 <= R_tab ** 2)[0]; m_ = rows.size
    Tt = sp.csr_matrix((np.concatenate([np.ones(m_), -X[rows], -Y[rows]]), (np.tile(np.arange(m_), 3), np.repeat([it0, it0 + 1, it0 + 2], m_))), shape=(m_, nred))
    Dm = (wmap[rows] - Tt).tocsr()                                                                       # w_plancha − w_mesa en la huella
    act_s = np.ones(nn, bool); act_t = np.ones(m_, bool); conv = False
    for it in range(300):
        Kt = Kr + wmap.T @ sp.diags(ks * act_s) @ wmap + Dm.T @ sp.diags(kt[rows] * act_t) @ Dm
        ur = spl.spsolve(Kt.tocsc(), fr); u = T @ ur; w = u[0::3]; g = Dm @ ur
        ns = w <= 0; nt = g >= 0; cs = np.where(ns != act_s)[0]; ct = np.where(nt != act_t)[0]
        if cs.size + ct.size == 0: conv = True; break
        if it > 40:   # evita ciclos: cambia el 20 % peor
            sel = cs[np.argsort(-np.abs(w[cs]))][: max(1, cs.size // 5)]; act_s[sel] = ns[sel]
            sel = ct[np.argsort(-np.abs(g[ct]))][: max(1, ct.size // 5)]; act_t[sel] = nt[sel]
        else:
            act_s, act_t = ns, nt
    bx = u[1::3][els]; by = u[2::3][els]
    kap = np.stack([bx @ dxc, by @ dyc, bx @ dyc + by @ dxc], 1)
    Db1 = Es / (12 * (1 - nu ** 2)) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])
    m = (kap @ Db1.T) * te[:, None] ** 3; s = 6 * m / te[:, None] ** 2
    vm = np.sqrt(s[:, 0] ** 2 - s[:, 0] * s[:, 1] + s[:, 1] ** 2 + 3 * s[:, 2] ** 2)
    S = np.column_stack([X[els].mean(1), Y[els].mean(1), vm, m, te])
    return X, Y, w, S, conv


def caso(F_kN, u, E, rects_, h_, Bs, tfun, W_tab, R_tab, ncyl=2, hm=40.0):
    def mask(sg): return lambda x, y: any(x0 - 1 <= sg * x - E[0] <= x1 + 1 and y0 - 1 <= sg * y - E[1] <= y1 + 1 for x0, x1, y0, y1 in rects_)
    def dist(x, y):
        return min(math.hypot(max(x0 - (sg * x - E[0]), 0, sg * x - E[0] - x1), max(y0 - (sg * y - E[1]), 0, sg * y - E[1] - y1))
                   for sg in (1, -1) for x0, x1, y0, y1 in rects_)
    Fb = (-F_kN * 1e3 * u[0], -F_kN * 1e3 * u[1]); M1 = (-h_ * Fb[1], h_ * Fb[0])
    sups = [(mask(1), E, M1, 470.0), (mask(-1), (-E[0], -E[1]), (-M1[0], -M1[1]) if ncyl == 2 else (0.0, 0.0), 470.0)]
    X, Y, w, S, conv = fea(Bs, hm, tfun, sups, W_tab, R_tab)
    d = np.array([dist(x, y) for x, y in S[:, :2]]); far = d > 100
    j = int(np.argmax(np.where(far, S[:, 2], -1)))
    return dict(M=math.hypot(*M1) / 1e6, pico=S[:, 2].max(), lejos=S[far, 2].max(), donde=(S[j, 0], S[j, 1], S[j, 6]), w=w.max(), conv=conv, S=S, d=d)


W_tab = DV["N"] * 1e3                         # mesa cargada: W + W_mesa (N)
psi0 = psi_band[0]; u0 = (math.cos(math.radians(psi0)), math.sin(math.radians(psi0)))
cap3, cap125 = Fy / Nd, 1.25 * Fy / Nd
print(f"== §4 FEA propia (malla 40 mm; mesa cargada {W_tab / 1e3:.0f} kN como cuerpo rígido con contacto unilateral; ψ = {psi0:.2f}°) ==")
print(f"    {'modelo':44s} {'F kN':>6s} {'M kN·m':>7s} {'σ pico':>7s} {'σ >100mm':>8s} {'FU Fy/Nd':>8s} {'FU 1,25Fy/Nd':>12s} {'w máx mm':>8s}  dónde (x, y, t)")
res = {}
c_ins = (P["D_top"] / 2 + 30) * math.sqrt(2)                       # inserto de esquina: |x − y| ≥ c, a 30 mm del borde de la mesa
t_ins = 48.0
mods = [("Actual: plancha 18", lambda x, y: t, E1, rects, h, P["B"]),
        (f"Inserto de esquina {t_ins:.0f} mm CJP (|x−y| ≥ {c_ins:.0f})", lambda x, y: t_ins if abs(x - y) >= c_ins else t, E1, rects, h, P["B"])]
for nm, tf, E_, R_, h_, Bs in mods:
    for Fk in (F_nom, F_dis, F_cal):
        r = caso(Fk, u0, E_, R_, h_, Bs, tf, W_tab, P["D_top"] / 2); res[(nm, round(Fk))] = r
        print(f"    {nm:44s} {Fk:6.1f} {r['M']:7.2f} {r['pico']:7.0f} {r['lejos']:8.0f} {r['lejos'] / cap3:8.2f} {r['lejos'] / cap125:12.2f} {r['w']:8.2f}  "
              f"({r['donde'][0]:.0f}; {r['donde'][1]:.0f}; {r['donde'][2]:.0f}){'' if r['conv'] else '  (sin convergencia)'}")
# KIET (plano vectorial KIET-1024-REF-TT-400T, escala 1:15): base 2200 × 20; esquinas de los cilindros con plancha de ≈ 20 mm sobre la base
# (z 20 → 40) en el triángulo |x − y| ≥ 1600 (catetos 590 mm); ojal en (∓982; ±990), eje a z ≈ 106 mm del piso (86 mm sobre la base);
# cilindro casi paralelo al borde (u ≈ (−0,992; 0,128) para el ojal (982; −990)); pedestal del ojal ≈ 140 × 140; mesa Ø2000.
uK = (-0.992, 0.128); nK = math.hypot(*uK); uK = (uK[0] / nK, uK[1] / nK)
for nm, tf in (("KIET medido: 20 + 20 en la esquina", lambda x, y: 40.0 if abs(x - y) >= 1600 else 20.0), ("KIET sin la plancha de esquina (20)", lambda x, y: 20.0)):
    r = caso(F_cal, uK, (982.0, -990.0), [(-70, 70, -70, 70)], 86.0, 2200.0, tf, W_tab, 1000.0); res[(nm, round(F_cal))] = r
    print(f"    {nm:44s} {F_cal:6.1f} {r['M']:7.2f} {r['pico']:7.0f} {r['lejos']:8.0f} {r['lejos'] / cap3:8.2f} {r['lejos'] / cap125:12.2f} {r['w']:8.2f}  "
          f"({r['donde'][0]:.0f}; {r['donde'][1]:.0f}; {r['donde'][2]:.0f})")
r0 = res[("Actual: plancha 18", round(F_cal))]
if r0["lejos"] <= cap125: fails.append("FEA: la plancha de 18 mm debería exceder 1,25·Fy/Nd a calado con la mesa cargada"); print("XX  FEA plancha actual")
ri = res[(mods[1][0], round(F_cal))]
S_, d_ = ri["S"], ri["d"]; z18 = (S_[:, 6] < t + 0.5) & (d_ > 100); zin = (S_[:, 6] > t + 0.5) & (d_ > 100)
print(f"    Inserto a calado: σ máx en la plancha de 18 fuera del inserto {S_[z18, 2].max():.0f} MPa; en el inserto (a > 100 mm de la huella) {S_[zin, 2].max():.0f} MPa")
leg = P["B"] - c_ins; m_ins = 2 * leg ** 2 / 2 * (t_ins - t) * 7.85e-6
print(f"    Inserto: catetos {leg:.0f} mm, hipotenusa a {c_ins / math.sqrt(2):.0f} mm del centro; masa añadida (dos esquinas) {m_ins:.0f} kg")
print("\nRESULTADO:", "sin diferencias" if not fails else "DIFERENCIAS: " + "; ".join(fails))
sys.exit(1 if fails else 0)
