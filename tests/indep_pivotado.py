"""Verificación independiente del ACCIONAMIENTO PIVOTADO tipo KIET (drive_mode = 2) del núcleo TT300-C.

Regla de independencia: no lee packages/*.js. Los parámetros salen de tests/golden/params_defaults.json (con drive_mode = 2) y los
resultados del núcleo solo de la salida JSON de `node tools/export_design.js [params.json]` (caja negra). Aquí se recalcula desde la
geometría plana, el miembro de dos fuerzas, la potencia virtual y ASME BTH-1 Cat. B (Fy/Nd; corte Fy/(Nd·√3); aplastamiento 1,25Fy/Nd;
soldaduras 0,60FEXX/(1,20Nd)) y AISC 360-22 J3 (pernos: Fnv = 0,45·Fu, Ω = 2,00):

  - posición de toma: |P(θ_ini) − E| = L0 + s_libre + L_qp (ley del coseno);
  - Q = P + L_qp·(E − P)/|E − P|, L = |P − E| − L_qp, brazo a = distancia de O a la recta E–P (fórmula de la distancia punto–recta);
  - deslizamiento en el contacto por DIFERENCIAS FINITAS de puntos materiales (el pasador gira con la mesa, el bloque es un sólido alineado
    con E–P que pasa por Q); brazo efectivo por potencia virtual: F_n·(dL/dθ − μ_s·|v_s|) = T/n, con dL/dθ también numérico;
  - F_cil = máx F_n·(1 + μ_leva·μ_s)/η, T = μ·N·r + μ_buje·H_ecc·D_piv/2 (N tomado del núcleo: la masa de la mesa ya la verifica indep_tt300c.py);
  - holguras con geometría propia (bloque acodado como polígono, cuerpo del cilindro como segmento), perfil de la leva (w_nec por búsqueda propia),
  - soporte del ojal E abierto (10-11-2026): sección de rectángulos de las piezas exportadas con flexión biaxial, corte, CJP y PJP (grupo elástico de líneas propio),
    desgarro de las tapas por rayos propios y holgura cuerpo del cilindro–piezas en todos los estados (ambos sentidos); orejas de izaje frente a placas, soportes,
    mesa y partes móviles; puntos de la holgura mínima de sincronía y pasadores de posición ISO 8734 (enganche ≥ 1,5·d),
    fuerzas de la leva, verificaciones de bloque, pasadores, cajón del ojal y pernos, asimetría al pivote y la sugerencia de E (malla gruesa propia).

Ejecutar: python3 -I tests/indep_pivotado.py      Sale con 0 si todo coincide (tolerancia 0,1 % salvo indicación); 1 si hay diferencias; 2 sin node."""
import json, math, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = json.loads((ROOT / "tests" / "golden" / "params_defaults.json").read_text())
P["drive_mode"] = 2
if not shutil.which("node"):
    print("node no disponible"); sys.exit(2)
with tempfile.TemporaryDirectory() as td:
    f = pathlib.Path(td) / "p.json"; f.write_text(json.dumps({"drive_mode": 2}))
    D = json.loads(subprocess.run(["node", str(ROOT / "tools" / "export_design.js"), str(f)], capture_output=True, text=True, check=True, cwd=str(ROOT)).stdout)
    # sin inserto (ins_on = 0): el modelo de la franja sin anclaje (§5c) se replica sobre esta exportación; por defecto la base lleva el inserto de esquina
    f.write_text(json.dumps({"drive_mode": 2, "ins_on": 0}))
    D0 = json.loads(subprocess.run(["node", str(ROOT / "tools" / "export_design.js"), str(f)], capture_output=True, text=True, check=True, cwd=str(ROOT)).stdout)
PV, DV = D["pivotado"], D["derivados"]
V = {v["nombre"]: v for v in D["verificaciones"]}
V0 = {v["nombre"]: v for v in D0["verificaciones"]}
fails = []
def chk(name, mine, tool, tol=1e-3, absol=1e-6):
    ok = abs(mine - tool) <= tol * abs(tool) + absol
    print(f"{'OK ' if ok else 'XX '} {name:78s} indep {mine:13.4f}  núcleo {tool:13.4f}")
    if not ok: fails.append(name)
def row(prefix, VV_=None):
    for k, v in (VV_ or V).items():
        if k.startswith(prefix): return v
    fails.append("falta la fila: " + prefix); print("XX  falta la fila:", prefix); return {"dem": float("nan"), "cap": float("nan")}

R, r, N = P["R_pin"], P["d_pin"] / 2, P["N_pin"]
pitch = 2 * math.pi / N
ph = math.radians(P["pv_phE"]); RE, Lqp = P["pv_RE"], P["pv_Lqp"]
E = (RE * math.cos(ph), RE * math.sin(ph))
L0, sf = P["L0"], P["s_free"]
tgt = L0 + sf + Lqp
th0 = ph + math.acos((R * R + RE * RE - tgt * tgt) / (2 * R * RE))

def pin(th): return (R * math.cos(th), R * math.sin(th))
def unit(a, b):
    d = math.hypot(b[0] - a[0], b[1] - a[1]); return ((b[0] - a[0]) / d, (b[1] - a[1]) / d), d
def line_dist(o, a, b):     # distancia de o a la recta a–b
    return abs((b[0] - a[0]) * (a[1] - o[1]) - (a[0] - o[0]) * (b[1] - a[1])) / math.hypot(b[0] - a[0], b[1] - a[1])
def state(th):
    p = pin(th); u, d = unit(E, p)
    return p, u, d, (p[0] - Lqp * u[0], p[1] - Lqp * u[1]), d - Lqp

print("== 1. Cinemática (61 posiciones) ==")
mu_s, eta = P["mu_s"], P["eta_c"]
h = 1e-5
pts = []
for i in range(61):
    th = th0 + pitch * i / 60
    p, u, d, Q, L = state(th)
    a = line_dist((0, 0), E, p)
    dL = (state(th + h)[4] - state(th - h)[4]) / (2 * h)
    # puntos materiales: pasador (rota con la mesa) y bloque (sólido alineado con E–P que pasa por Q), coincidentes en el contacto
    C = (p[0] - r * u[0], p[1] - r * u[1])
    Cpin = (C[0] * math.cos(h) - C[1] * math.sin(h), C[0] * math.sin(h) + C[1] * math.cos(h))
    p1, u1, d1, Q1, L1 = state(th + h)
    Cblk = (Q1[0] + (Lqp - r) * u1[0], Q1[1] + (Lqp - r) * u1[1])
    vs = math.hypot(Cpin[0] - Cblk[0], Cpin[1] - Cblk[1]) / h
    pts.append(dict(th=th, p=p, u=u, d=d, Q=Q, L=L, a=a, dL=dL, vs=vs, aef=dL - mu_s * vs, ft=a / R, fr=(p[0] * u[0] + p[1] * u[1]) / R))
chk("Ángulo de toma θ_ini (°)", math.degrees(th0), PV["theta_ini_deg"])
chk("Brazo mínimo geométrico a (mm)", min(q["a"] for q in pts), PV["brazo_min"])
chk("dL/dθ = a en toda la carrera (máx |dL/dθ − a|, mm)", max(abs(q["dL"] - q["a"]) for q in pts), 0.0, absol=1e-3)
chk("Brazo efectivo mínimo a − μ_s·|v_s| (mm)", min(q["aef"] for q in pts), PV["brazo_ef_min"])
chk("Carrera requerida colineal L(θ_fin) − L0 (mm)", max(q["L"] for q in pts) - L0, PV["carrera_req_colineal"])
chk("Radio mínimo de Q (mm)", min(math.hypot(*q["Q"]) for q in pts), PV["Q_min"])
for i in (0, 30, 60):
    q, t = pts[i], PV["cinematica"][i]
    chk(f"  θ = {math.degrees(q['th']):7.2f}°: a colineal (mm)", q["a"], t["a_colineal"]); chk("              a_ef colineal (mm)", q["aef"], t["a_ef_colineal"])
print("== 2. Fuerzas de referencia con la cinemática colineal (la fuerza de diseño es la del empuje guiado: sección 4) ==")
Ro = P["D_top"] / 2; Ri = P["D_boss"] / 2 + P["c_boss_r"] + P["m_ri"]
NN = DV["N"]
Hecc = lambda mu: mu * NN * P["e"] * (4 / 3) * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4)
Tq = lambda mu, rr: mu * NN * rr / 1e3 + P["mu_bush"] * Hecc(mu) * P["D_piv"] / 2 / 1e3
ru = 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2)
A = math.pi / 4 * P["D_bore"] ** 2; Fst = A * P["p_relief"] / 10 / 1e3
mu_c = P["mu_d"]                     # familia 1 (acero templado–acero con grasa): cam_mat = 0 con la interfaz acero–acero
kf = 1 + mu_c * mu_s
cases = {"nom": (P["mu_nom"], ru), "dis": (P["mu_d"], P["r_ef"]), "borde": (P["mu_d"], Ro), "cont": (P["mu_cont"], P["r_ef"]), "seco": (P["mu_dry"], ru)}
Tcase = {c["id"]: Tq(*cases[c["id"]]) for c in DV["casos"]}
Tdis = Tcase["dis"]
Fcol = max(Tdis * 1e3 / P["n_cyl"] / q["aef"] for q in pts) * kf / eta
chk("Caso dis: F colineal de referencia (kN)", Fcol, max(t["F_cil_colineal"] for t in PV["cinematica"]))

print("== 3. Holguras (geometría propia) ==")
def poly_dist(poly, x, y):
    best = float("inf"); inside = True; sg = 0
    for i in range(len(poly)):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % len(poly)]; ex, ey = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * ex + (y - ay) * ey) / (ex * ex + ey * ey)))
        best = min(best, math.hypot(x - ax - t * ex, y - ay - t * ey))
        cr = ex * (y - ay) - ey * (x - ax)
        if cr: sg = sg or (1 if cr > 0 else -1); inside = inside and ((cr > 0) == (sg > 0))
    return -best if inside else best
def block_polys(Q, u):
    t = (-u[1], u[0]); eb = P["pv_dq"] / 2 + 25; s2 = Lqp - r; s1 = s2 - P["pv_lf"]
    def rect(o, s0, s1_, w):
        return [(o[0] + s * u[0] + k * w / 2 * t[0], o[1] + s * u[1] + k * w / 2 * t[1]) for s, k in ((s0, -1), (s1_, -1), (s1_, 1), (s0, 1))]
    Qs = (Q[0] - P["pv_ecr"] * t[0], Q[1] - P["pv_ecr"] * t[1])
    return [rect(Qs, -eb, s1, P["pv_bu"]), rect(Q, s1, s2, P["pv_bf"])], eb
def clr_block(Q, u, pins):
    polys, eb = block_polys(Q, u)
    return min(min(min(poly_dist(pg, x, y) for pg in polys), math.hypot(x - Q[0], y - Q[1]) - eb) for x, y in pins) - r
clrB = min(clr_block(q["Q"], q["u"], [pin(q["th"] - pitch), pin(q["th"] + pitch)]) for q in pts)
chk("Holgura bloque-uña–pasador siguiente en el empuje (mm)", clrB, PV["holgura_pasador_siguiente"])
def seg_dist(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; t = max(0, min(1, -(a[0] * dx + a[1] * dy) / (dx * dx + dy * dy))); return math.hypot(a[0] + t * dx, a[1] + t * dy)
body = min(seg_dist((E[0] + P["e_body"] * q["u"][0], E[1] + P["e_body"] * q["u"][1]), (E[0] + (L0 - P["c_rod"]) * q["u"][0], E[1] + (L0 - P["c_rod"]) * q["u"][1])) for q in pts) - P["D_body"] / 2 - P["D_top"] / 2
chk("Holgura cuerpo del cilindro–mesa (mm)", body, PV["holgura_cuerpo_mesa"])
Bh = P["B"] / 2 - P["rim_t"] - 5
chk("Soporte del ojal dentro de la base: máx(|E_x|,|E_y|) + lado/2 (mm)", max(abs(E[0]), abs(E[1])) + P["pv_box"] / 2, row("Soporte del ojal E dentro de la base")["dem"])
if not (clrB >= P["pv_cB"] and body >= P["pv_cc"] and min(math.hypot(*q["Q"]) for q in pts) - P["pv_dq"] / 2 - P["D_top"] / 2 >= P["pv_cQ"]):
    fails.append("holguras por debajo del mínimo con los valores por defecto"); print("XX  holguras por debajo del mínimo")

print("== 4. Placa-guía curva: requisitos propios, geometría exportada (caja negra), empuje guiado, retorno y sincronía ==")
PL = PV["placa_leva"]; m = P["pv_msync"]; c = P["pv_c"]; rf = P["pv_dq"] / 2
psi0 = math.atan2(pts[0]["u"][1], pts[0]["u"][0])
def Qof(L, w):
    ps = psi0 - w / L; u = (math.cos(ps), math.sin(ps)); return (E[0] + L * u[0], E[1] + L * u[1]), u
def to_lw(p):
    d = (p[0] - E[0], p[1] - E[1]); L = math.hypot(*d); a = psi0 - math.atan2(d[1], d[0])
    while a > math.pi: a -= 2 * math.pi
    while a < -math.pi: a += 2 * math.pi
    return L, a * L
retpins = [pin(th0 - pitch), pin(th0)]
def clr_ret(L, w): return clr_block(*Qof(L, w), retpins)
def wneed(L, mm):
    if clr_ret(L, 0) >= mm: return 0.0
    lo, hi = 0.0, 4.0
    while clr_ret(L, hi) < mm: lo, hi = hi, hi + 4.0
    for _ in range(30):
        mid = (lo + hi) / 2
        if clr_ret(L, mid) >= mm: hi = mid
        else: lo = mid
    return hi
# margen de diseño: m + tolerancia de posición + crecimiento del círculo de pasadores con la mesa a 80 °C (α medio 20–80 °C de EN 1993-1-2 §3.4.1.1)
dl = lambda T: 1.2e-5 * T + 0.4e-8 * T * T - 2.416e-4
alpha = (dl(80) - dl(P["T_ref"])) / (80 - P["T_ref"])
dTol = P["pv_tolg"] + alpha * (80 - P["T_ref"]) * R; md = m + dTol
chk("Tolerancias de sincronía δ = tol + α·ΔT·R_pin (mm)", dTol, PL["tolerancias_mm"])
# segmentos exportados (cilindro 1, antihorario)
def seg_at(s, f):
    if s["tipo"] == "linea": return (s["p0"][0] + (s["p1"][0] - s["p0"][0]) * f, s["p0"][1] + (s["p1"][1] - s["p0"][1]) * f)
    cx, cy = s["centro"]; k = 1 if s["sentido"] == "antihorario" else -1
    a0 = math.atan2(s["p0"][1] - cy, s["p0"][0] - cx); a1 = math.atan2(s["p1"][1] - cy, s["p1"][0] - cx); d = k * (a1 - a0)
    while d < 0: d += 2 * math.pi
    while d >= 2 * math.pi: d -= 2 * math.pi
    a = a0 + k * d * f; return (cx + s["radio"] * math.cos(a), cy + s["radio"] * math.sin(a))
def seg_tan(s, p):
    if s["tipo"] == "linea":
        dx, dy = s["p1"][0] - s["p0"][0], s["p1"][1] - s["p0"][1]; n = math.hypot(dx, dy); return (dx / n, dy / n)
    vx, vy = p[0] - s["centro"][0], p[1] - s["centro"][1]; n = math.hypot(vx, vy); k = 1 if s["sentido"] == "antihorario" else -1
    return (-k * vy / n, k * vx / n)
def seg_len(s):
    if s["tipo"] == "linea": return math.hypot(s["p1"][0] - s["p0"][0], s["p1"][1] - s["p0"][1])
    q = [seg_at(s, i / 400) for i in range(401)]; return sum(math.hypot(q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]) for i in range(1, 401))
SC, SK = PL["segmentos_centro"], PL["segmentos_canto"]
g1 = 0.0; gap = 0.0
for S in (SC, SK):
    for a, b in zip(S, S[1:]):
        gap = max(gap, math.hypot(a["p1"][0] - b["p0"][0], a["p1"][1] - b["p0"][1]))
        t0, t1 = seg_tan(a, a["p1"]), seg_tan(b, b["p0"]); g1 = max(g1, abs(math.atan2(t0[0] * t1[1] - t0[1] * t1[0], t0[0] * t1[0] + t0[1] * t1[1])))
chk("Canto y trayectoria: máximo quiebre de tangente en los empalmes (rad)", g1, 0.0, absol=1e-9); chk("  máxima separación en los empalmes (mm)", gap, 0.0, absol=1e-6)
rconv, rconc = float("inf"), float("inf")
for s, e in zip(SC, SK):
    if s["tipo"] != "arco": continue
    if abs(e["centro"][0] - s["centro"][0]) + abs(e["centro"][1] - s["centro"][1]) > 1e-6: fails.append("arco del canto no concéntrico")
    if s["sentido"] == "horario":   # trayectoria curvada hacia la placa: canto convexo R − r_f
        if abs(e["radio"] - (s["radio"] - rf)) > 1e-6: fails.append("radio convexo del canto ≠ R − d_Q/2")
        rconv = min(rconv, e["radio"])
    else:
        if abs(e["radio"] - (s["radio"] + rf)) > 1e-6: fails.append("radio cóncavo del canto ≠ R + d_Q/2")
        rconc = min(rconc, e["radio"])
chk("Radio convexo mínimo del canto (mm)", rconv, PL["radio_min_canto"]["convexo"]); chk("Radio cóncavo mínimo del canto (mm)", rconc, PL["radio_min_canto"]["concavo"])
if rconv < P["pv_rmin"]: fails.append("socavado: radio convexo bajo el mínimo")
# trayectoria W(L) densa (L creciente) y requisitos propios
dense = []
for i, s in enumerate(SC):
    n = max(2, int(seg_len(s) / 0.1)); dense += [seg_at(s, j / n) for j in range(0 if i == 0 else 1, n + 1)]
lw = [to_lw(p) for p in dense]
if any(b[0] < a[0] - 1e-6 for a, b in zip(lw, lw[1:])): fails.append("la trayectoria retrocede en L")
def W(L):
    for (a, wa), (b, wb) in zip(lw, lw[1:]):
        if a <= L <= b: return wa + (wb - wa) * (L - a) / ((b - a) or 1)
    return lw[-1][1]
chk("Reenganche: W(L0) = c (mm)", W(L0), c, tol=0, absol=0.02)
Le = max(q["L"] for q in pts); Ls_ = L0 + sf
pw = [(q["L"], -q["L"] * (math.atan2(q["u"][1], q["u"][0]) - psi0)) for q in pts]
def wemp(L):
    if L <= Ls_: return 0.0
    for (a, wa), (b, wb) in zip(pw, pw[1:]):
        if a <= L <= b: return wa + (wb - wa) * (L - a) / (b - a)
    return pw[-1][1]
lo, hi = L0, Le
for _ in range(60):
    mid = (lo + hi) / 2
    if clr_ret(mid, 0) >= md: lo = mid
    else: hi = mid
LB = hi
A1, _ = Qof(L0 + P["pv_dwell"], c); uA = Qof(L0 + P["pv_dwell"], c)[1]
phi_req = 0.0
Lx = LB + 0.001
while Lx <= LB + 60:
    q, _ = Qof(Lx, wneed(Lx, md) + 0.3); dx, dy = q[0] - A1[0], q[1] - A1[1]; n = math.hypot(dx, dy)
    phi_req = max(phi_req, math.atan2(-(uA[0] * dy - uA[1] * dx) / n, (uA[0] * dx + uA[1] * dy) / n)); Lx += 0.25
chk("Flanco: ángulo mínimo que exige la sincronía (°)", math.degrees(phi_req), PL["alpha_req_deg"], tol=0, absol=0.05)
worst = float("inf")
for k in range(0, 801):
    L = L0 + (Le - L0) * k / 800
    req = max(wneed(L, md) if L >= LB else 0.0, (wemp(L) + c) if L >= Ls_ else 0.0)
    worst = min(worst, W(L) - req)
if worst < -0.02: fails.append("W(L) bajo w_nec(m + δ)"); print("XX  W bajo w_nec:", worst)
print(f"    holgura mínima de W sobre w_nec(m + δ) propio: {worst:.3f} mm")
# empuje guiado: Q en la trayectoria con |P − Q| = L_qp; equilibrio del pasador Q y par en el pasador tomado
eps = math.asin(r * math.sin(math.atan(mu_s)) / Lqp)
def guided(th):
    p = pin(th); Lc = math.hypot(p[0] - E[0], p[1] - E[1]) - Lqp; best = None
    for i in range(1, len(dense)):
        f0 = math.hypot(p[0] - dense[i - 1][0], p[1] - dense[i - 1][1]) - Lqp; f1 = math.hypot(p[0] - dense[i][0], p[1] - dense[i][1]) - Lqp
        if f0 * f1 > 0 or f0 == f1: continue
        t = f0 / (f0 - f1); q = (dense[i - 1][0] + (dense[i][0] - dense[i - 1][0]) * t, dense[i - 1][1] + (dense[i][1] - dense[i - 1][1]) * t); L = math.hypot(q[0] - E[0], q[1] - E[1])
        if L >= Lc - 1 and (best is None or L < best[1]): best = (q, L, i)
    q, L, i = best
    tx, ty = dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]; n = math.hypot(tx, ty); tp = (tx / n, ty / n); nin = (-tp[1], tp[0])
    uc = ((q[0] - E[0]) / L, (q[1] - E[1]) / L); d = math.hypot(p[0] - q[0], p[1] - q[1]); b = ((p[0] - q[0]) / d, (p[1] - q[1]) / d)
    bp = (b[0] * math.cos(eps) - b[1] * math.sin(eps), b[0] * math.sin(eps) + b[1] * math.cos(eps))
    a2 = (-(nin[0] - mu_c * tp[0]), -(nin[1] - mu_c * tp[1])); cr = lambda u, v: u[0] * v[1] - u[1] * v[0]
    det = cr(bp, a2); fn = cr(uc, a2) / det; h = cr(bp, uc) / det; arm = cr(q, bp)
    return dict(q=q, L=L, tp=tp, nin=nin, fn=fn, h=h, arm=arm, uc=uc, b=b, phi=math.degrees(math.acos(min(1, abs(tp[0] * uc[0] + tp[1] * uc[1])))))
G_ = [guided(q["th"]) for q in pts]
for cc in DV["casos"]:
    F = max(Tcase[cc["id"]] * 1e3 / P["n_cyl"] / g["arm"] / g["fn"] for g in G_) / eta
    chk(f"Caso {cc['id']}: F por cilindro, empuje guiado (kN)", F, cc["F"], tol=2e-3); chk(f"Caso {cc['id']}: FS", Fst / F, cc["FS"], tol=2e-3); chk(f"Caso {cc['id']}: presión (bar)", F * 1e3 / A * 10, cc["p"], tol=2e-3)
    if cc["id"] == "dis": Fdis = F
chk("Carrera requerida con Q apoyado en el canto (mm)", max(g["L"] for g in G_) - L0, PV["carrera_req"], tol=1e-3)
for i in (0, 30, 60):
    g, t = G_[i], PV["cinematica"][i]
    chk(f"  θ = {math.degrees(pts[i]['th']):7.2f}°: L con Q en el canto (mm)", g["L"], t["L"], tol=2e-4); chk("              brazo de F_n respecto de O (mm)", g["arm"], t["a"], tol=2e-3)
    chk("              ángulo del cilindro ψ (°)", math.degrees(math.atan2(g["uc"][1], g["uc"][0])), t["psi_deg"], tol=2e-4)
if min(g["h"] for g in G_) <= 0: fails.append("Q se despega del canto en el empuje"); print("XX  h ≤ 0")
if max(g["phi"] for g in G_) >= 90 - math.degrees(math.atan(mu_c)): fails.append("autobloqueo en el empuje")
clrBg = min(clr_block(g["q"], g["b"], [pin(q["th"] - pitch), pin(q["th"] + pitch)]) for g, q in zip(G_, pts))
print(f"    empuje guiado: h = H/F en [{min(g['h'] for g in G_):.3f}; {max(g['h'] for g in G_):.3f}], φ máx {max(g['phi'] for g in G_):.1f}°, holgura bloque–pasadores {clrBg:.2f} mm")
if clrBg < P["pv_cB"]: fails.append("bloque contra los pasadores en el empuje guiado")
Fe_st = Fst * 1e3 * eta; Tst = max(g["h"] for g in G_) * Fe_st
chk("Placa: carga transversal a calado máx h·F_calado·η (N)", Tst, PL["fuerzas_N"]["transversal_calado"], tol=2e-3)
# retorno: Q conserva ψ salvo que el pasador lo empuje (holgura 0) y el canto lo conduce a la toma; primer contacto y atasco
wE = W(Le); ps = psi0 - wE / Le; first = None; guia_prev = True; drive = []
nR = int(2 * (Le - L0))
for k in range(nR + 1):
    L = Le - (Le - L0) * k / nR; Wv = W(L); w0 = wneed(L, 0) if L >= LB else 0.0
    w = max((psi0 - ps) * L, w0); guia = w >= Wv - 1e-9; w = min(w, Wv); ps = psi0 - w / L
    if guia and not guia_prev: first = L
    if guia: drive.append(L)
    guia_prev = guia
    if clr_ret(L, w) < -1e-3: fails.append("choque en el retorno"); print("XX  choque en el retorno L =", L); break
def phi_at(L):
    for i in range(1, len(lw)):
        if lw[i][0] >= L: break
    tx, ty = dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]; n = math.hypot(tx, ty); q = dense[i]; u = ((q[0] - E[0]), (q[1] - E[1])); un = math.hypot(*u)
    return math.degrees(math.acos(min(1, abs((tx * u[0] + ty * u[1]) / (n * un)))))
chk("Retorno: L del primer contacto con el canto (mm)", first, PL["primer_contacto"]["L"], tol=0, absol=1.0)
phi1 = phi_at(first)
chk("Retorno: ángulo de presión en el primer contacto (°)", phi1, PL["primer_contacto"]["phi"], tol=0, absol=0.5)
Fret = math.pi / 4 * (P["D_bore"] ** 2 - P["d_rod"] ** 2) * P["p_ret"] / 10
NR = Fret / math.sin(math.radians(phi1))
chk("Placa: atasco del retorno F_ret/sen φ₁ (N)", NR, PL["fuerzas_N"]["rampa_atasco"], tol=0.02)
kE = P["pv_muE"] * P["pv_dE"] / (2 * L0); lockmax = 0.0
for L in drive:
    a = math.radians(phi_at(L)); lockmax = max(lockmax, kE * (math.sin(a) + mu_c * math.cos(a)) / (math.cos(a) - mu_c * math.sin(a)))
chk("Sin autobloqueo en toda la conducción: máx dem/cap", lockmax, row("Placa-guía sin autobloqueo")["dem"] / row("Placa-guía sin autobloqueo")["cap"], tol=0.02)
sync = min(clr_ret(L, W(L)) for L in [L0 + (first - L0) * k / 4000 for k in range(4001)])
chk("Sincronía nominal: holgura mínima con Q contra el canto (mm, barrido propio)", sync, PL["sincronia"], tol=0, absol=0.05)
if sync < m + dTol - 0.05: fails.append("sincronía bajo m + δ"); print("XX  sincronía bajo el margen")
# puntos exportados de la holgura mínima de sincronía (caja negra) frente a la geometría propia: bloque en Q(L_sync) contra el canto y pasador B
HS = PV["fabricacion"]["placas_leva"]["holgura_sincronia"]; I1 = HS["instancias"]["1_antihorario"]
chk("Holgura de sincronía: distancia entre los dos puntos exportados (mm)", math.hypot(I1["punto_bloque"][0] - I1["punto_pasador"][0], I1["punto_bloque"][1] - I1["punto_pasador"][1]), sync, tol=0, absol=0.05)
chk("Holgura de sincronía: peor caso = nominal − δ (mm)", HS["nominal"] - dTol, HS["peor_caso"], tol=1e-9)
Qs_, us_ = Qof(HS["L"], W(HS["L"])); bpol, ebq = block_polys(Qs_, us_)
onb = min(min(abs(poly_dist(pg, *I1["punto_bloque"])) for pg in bpol), abs(math.hypot(I1["punto_bloque"][0] - Qs_[0], I1["punto_bloque"][1] - Qs_[1]) - ebq))
pinB = min(retpins, key=lambda q: math.hypot(q[0] - I1["centro_pasador"][0], q[1] - I1["centro_pasador"][1]))
if onb > 0.05 or math.hypot(pinB[0] - I1["centro_pasador"][0], pinB[1] - I1["centro_pasador"][1]) > 1e-6 or abs(math.hypot(I1["punto_pasador"][0] - pinB[0], I1["punto_pasador"][1] - pinB[1]) - r) > 1e-6:
    fails.append("puntos de la holgura de sincronía"); print("XX  puntos de la holgura de sincronía fuera del bloque o del pasador B")
for k_, Ik in HS["instancias"].items():   # reflexión y rotación propias
    f_ = (lambda q: q) if k_.endswith("antihorario") else (lambda q: (2 * (q[0] * math.cos(ph) + q[1] * math.sin(ph)) * math.cos(ph) - q[0], 2 * (q[0] * math.cos(ph) + q[1] * math.sin(ph)) * math.sin(ph) - q[1]))
    g_ = (lambda q: (-f_(q)[0], -f_(q)[1])) if k_.startswith("2") else f_
    if math.hypot(g_(I1["punto_bloque"])[0] - Ik["punto_bloque"][0], g_(I1["punto_bloque"])[1] - Ik["punto_bloque"][1]) > 1e-6: fails.append("holgura de sincronía " + k_); print("XX  instancia", k_)
# pasadores de posición ISO 8734: enganche ≥ 1,5·d en base y placa con alojamientos ciegos (remanente 3 mm, 2 mm de fondo libre)
PPd = PV["fabricacion"]["placas_leva"]["pasadores_posicion"]; dd_ = P["pv_dd"]
lb_ = P["t_base"] - 3 - 2; Lser = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40, 45, 50]; Ld_ = next(x for x in Lser if x - lb_ >= 1.5 * dd_)
chk("Pasadores de posición: largo ISO 8734 (mm)", Ld_, PPd["largo"]); chk("  enganche en la base (mm)", lb_, PPd["enganche_base"]); chk("  enganche en la placa (mm)", Ld_ - lb_, PPd["enganche_placa"])
if min(lb_, Ld_ - lb_) < 1.5 * dd_ or P["pv_tcam"] - (Ld_ - lb_) - 2 < 3: fails.append("pasadores de posición"); print("XX  pasadores de posición")
Ncam = max(NR, Tst)

print("== 5. Verificaciones del bloque, pasadores, ojal E y placa-leva (BTH-1 Cat. B, AISC J3) ==")
Nd, Fs, Fy = P["Nd"], Fst * 1e3, P["Fy"]
bu, hu = P["pv_bu"], P["pv_hu"]
# cara convexa del bloque: la resultante del contacto (inclinada atan μ_s) pasa a μ_Q·d_Q/2 de Q; la normal pasa por el centro de curvatura y por P
s2b = Lqp - r; Rfc = P["pv_rface"]; rho_ = math.atan(mu_s); dR_ = P["pv_muE"] * P["pv_dq"] / 2
if Rfc > 0: sg_ = (s2b * math.sin(rho_) + dR_) / (s2b - Rfc); ecb = Rfc * sg_
else: ecb = s2b * math.tan(rho_) + dR_
Es_ = P["E"] / (2 * (1 - P["nu"] ** 2)); qb = P["k_edge"] * Fs / hu; Refb = 1 / (1 / r + (1 / Rfc if Rfc > 0 else 0))
chk("Bloque: contacto dentro de la cara e_c + b_Hertz (mm)", ecb + math.sqrt(4 * qb * Refb / (math.pi * Es_)), row("Bloque-uña: contacto dentro de la cara")["dem"]); chk("  b_f/2 − 3 (mm)", P["pv_bf"] / 2 - 3, row("Bloque-uña: contacto dentro de la cara")["cap"])
chk("Bloque: Hertz cara convexa–pasador (MPa)", math.sqrt(qb * Es_ / (math.pi * Refb)), row("Bloque-uña: contacto de Hertz cara–pasador")["dem"])
s1b = s2b - P["pv_lf"]
chk("Bloque: F/(bh) + 6F(e_cr + e + e_c·s₁/s₂)/(hb²) (MPa)", Fs / (bu * hu) + 6 * Fs * (P["pv_ecr"] + P["e_dog"] + ecb * s1b / s2b) / (hu * bu * bu), row("Bloque-uña: compresión + flexión en el cuerpo acodado")["dem"])
if ecb + math.sqrt(4 * qb * Refb / (math.pi * Es_)) > P["pv_bf"] / 2 - 3: fails.append("contacto fuera de la cara del bloque"); print("XX  contacto fuera de la cara")
zc0 = P["h_disc"] / 2 + P["t_base"]                              # interfaz acero–acero: δ = 0
tq = (hu - P["b_eye"] - 2 * P["g_ch"]) / 2
lq = (zc0 - P["b_eye"] / 2 - P["g_ch"] - tq / 2) - (P["t_base"] + P["pv_tcam"] / 2)
MQ = math.hypot(Fs / 2 * (tq / 2 + P["g_ch"] + P["b_eye"] / 4), Ncam * lq)   # Ncam = máx(atasco, empuje a calado) de la sección 4
chk("Pasador Q: flexión combinada (MPa)", MQ / (math.pi * P["pv_dq"] ** 3 / 32), row("Pasador Q: flexión")["dem"])
ME = Fs / 2 * (P["pv_tl"] / 2 + P["g_ch"] + P["b_eye"] / 4)
chk("Pasador E: flexión (MPa)", ME / (math.pi * P["pv_dE"] ** 3 / 32), row("Pasador vertical E: flexión")["dem"])
# ---- soporte del ojal E (cajón abierto, 10-11-2026): piezas exportadas (caja negra) y mecánica propia (sección de rectángulos, grupo elástico de líneas)
SE = PV["fabricacion"]["soporte_E"]; ML = SE["marco_local"]; sxE, syE = ML["s_x"], ML["s_y"]; bE, biE = ML["b"], ML["b_i"]
pzs = {q["id"]: q for q in SE["piezas"]}
rects = []                                            # paredes y muñones como rectángulos [x0, x1, y0, y1] en el marco local (esquina hacia +X, −Y)
for k_, q in pzs.items():
    if k_.startswith("pared") or k_.startswith("munon"):
        xs_ = [v[0] for v in q["poligono_local"]]; ys_ = [v[1] for v in q["poligono_local"]]; rects.append((k_, (min(xs_), max(xs_), min(ys_), max(ys_))))
def sec_props(R_):
    A_ = sum((x1 - x0) * (y1 - y0) for x0, x1, y0, y1 in R_); cx = sum((x1 - x0) * (y1 - y0) * (x0 + x1) / 2 for x0, x1, y0, y1 in R_) / A_; cy = sum((x1 - x0) * (y1 - y0) * (y0 + y1) / 2 for x0, x1, y0, y1 in R_) / A_
    Ixx = sum((x1 - x0) * (y1 - y0) ** 3 / 12 + (x1 - x0) * (y1 - y0) * ((y0 + y1) / 2 - cy) ** 2 for x0, x1, y0, y1 in R_)
    Iyy = sum((y1 - y0) * (x1 - x0) ** 3 / 12 + (x1 - x0) * (y1 - y0) * ((x0 + x1) / 2 - cx) ** 2 for x0, x1, y0, y1 in R_)
    Ixy = sum((x1 - x0) * (y1 - y0) * ((x0 + x1) / 2 - cx) * ((y0 + y1) / 2 - cy) for x0, x1, y0, y1 in R_)
    return A_, cx, cy, Ixx, Iyy, Ixy
A_w, cxw, cyw, Ixx, Iyy, Ixy = sec_props([r_ for _, r_ in rects]); Dw = Ixx * Iyy - Ixy ** 2
def sigma_max(mx, my):   # equilibrio de la sección: σ = αx + βy con ∫yσ = m_x y −∫xσ = m_y
    al = -(mx * Ixy + my * Ixx) / Dw; be = (mx * Iyy + my * Ixy) / Dw
    return max(abs(al * (x - cxw) + be * (y - cyw)) for _, (x0, x1, y0, y1) in rects for x in (x0, x1) for y in (y0, y1))
def loc(v): return (sxE * v[0], -syE * v[1])          # dirección real → marco local
# estados del barrido: empuje (posiciones, Q en el canto), retorno (Q exportados) y colineal; horario = reflejo respecto de la diagonal O–E
ed = (math.cos(ph), math.sin(ph))
def refl(q):
    d_ = q[0] * ed[0] + q[1] * ed[1]; return (2 * d_ * ed[0] - q[0], 2 * d_ * ed[1] - q[1])
Qs_ah = [tuple(q) for q in PV["posiciones"]["1_antihorario"]["Q"]] + [tuple(q["Q"]) for q in PL["retorno"]] + [tuple(q) for q in PV["posiciones"]["1_antihorario"]["Q_colineal"]]
dirs = []
for Qa in Qs_ah:
    for Q_, E_ in ((Qa, E), (refl(Qa), refl(E))):
        dd = math.hypot(Q_[0] - E_[0], Q_[1] - E_[1]); dirs.append(loc(((Q_[0] - E_[0]) / dd, (Q_[1] - E_[1]) / dd)))
zc0E = P["h_disc"] / 2 + P["t_base"]; hs_ = 2 * (zc0E - P["t_base"])     # h_sup + h_inf (tapas simétricas respecto del eje)
sig_w = max(sigma_max(u_[1] * Fs / 2 * hs_, -u_[0] * Fs / 2 * hs_) for u_ in dirs)
chk("Soporte E: flexión biaxial de las paredes en la base (MPa)", sig_w, row("Soporte del ojal E: flexión de las paredes")["dem"], tol=3e-3)
def Av(f):
    a_ = 0.0
    for _, (x0, x1, y0, y1) in rects:
        lx, ly = x1 - x0, y1 - y0; a_ += min(lx, ly) * max(lx, ly) * (f[0] if lx >= ly else f[1]) ** 2
    return a_
tau_w = max(Fs / Av((-u_[0], -u_[1])) for u_ in dirs)
chk("Soporte E: corte F/A_v en las paredes (MPa)", tau_w, row("Soporte del ojal E: corte en las paredes")["dem"], tol=3e-3)
chk("Soporte E: CJP paredes–base, FU = máx(σ/σ_adm, τ/τ_adm)", max(sig_w / (Fy / Nd), tau_w / (Fy / (Nd * math.sqrt(3)))), row("Soporte del ojal E: CJP paredes–base")["dem"], tol=3e-3)
# flujo de corte en las CJP pared–pared (parte unida por la junta)
def flow(sub, f):
    Qx = sum((x1 - x0) * (y1 - y0) * ((y0 + y1) / 2 - cyw) for x0, x1, y0, y1 in sub); Qy = sum((x1 - x0) * (y1 - y0) * ((x0 + x1) / 2 - cxw) for x0, x1, y0, y1 in sub)
    dm = (-f[1] * Fs, f[0] * Fs); al = -(dm[0] * Ixy + dm[1] * Ixx) / Dw; be = (dm[0] * Iyy + dm[1] * Ixy) / Dw; return abs(al * Qy + be * Qx)
RR = dict(rects); subs = [[RR["pared_Y"]] + ([RR["munon_X"]] if "munon_X" in RR else [])] + ([[RR["munon_Y"]], [RR["munon_X"]]] if "munon_Y" in RR else [])
tau_f = max(flow(sb, (-u_[0], -u_[1])) / P["pv_tbox"] for u_ in dirs for sb in subs)
chk("Soporte E: CJP pared–pared, τ = V·Q/(I·t) (MPa)", tau_f, row("Soporte del ojal E: CJP pared–pared")["dem"], tol=3e-3)
# PJP de las tapas: líneas = cantos de la tapa sobre las caras de paredes y muñones; F/2 en E; E_pjp = (t_tapa − 8) − 3
cap_ = SE["tapas"]["poligono_local"]; lines_ = []
def on_face(pt):
    return any((min(abs(pt[0] - x0), abs(pt[0] - x1)) < 1e-6 and y0 - 1e-6 <= pt[1] <= y1 + 1e-6) or (min(abs(pt[1] - y0), abs(pt[1] - y1)) < 1e-6 and x0 - 1e-6 <= pt[0] <= x1 + 1e-6) for _, (x0, x1, y0, y1) in rects)
for i_ in range(len(cap_)):
    a_, b_ = cap_[i_], cap_[(i_ + 1) % len(cap_)]
    if math.hypot(b_[0] - a_[0], b_[1] - a_[1]) > 1e-6 and on_face(((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)): lines_.append((a_, b_))
seglen = lambda a_, b_: math.hypot(b_[0] - a_[0], b_[1] - a_[1])
Lc = sum(seglen(a_, b_) for a_, b_ in lines_)
Cc = (sum(seglen(a_, b_) * (a_[0] + b_[0]) / 2 for a_, b_ in lines_) / Lc, sum(seglen(a_, b_) * (a_[1] + b_[1]) / 2 for a_, b_ in lines_) / Lc)
Jc = sum(seglen(a_, b_) ** 3 / 12 + seglen(a_, b_) * (((a_[0] + b_[0]) / 2 - Cc[0]) ** 2 + ((a_[1] + b_[1]) / 2 - Cc[1]) ** 2) for a_, b_ in lines_)
Epj = max(6, P["pv_tl"] - 8) - 3
def qcap(f, F_):
    M_ = -Cc[0] * f[1] * F_ + Cc[1] * f[0] * F_
    return max(math.hypot(f[0] * F_ / Lc - M_ * (pt[1] - Cc[1]) / Jc, f[1] * F_ / Lc + M_ * (pt[0] - Cc[0]) / Jc) for a_, b_ in lines_ for pt in (a_, b_))
f_pjp = max(qcap((-u_[0], -u_[1]), Fs / 2) / Epj for u_ in dirs)
Fw_ = P["FEXX"] * 0.6 / (1.2 * Nd)
chk("Soporte E: PJP tapas–paredes, grupo elástico de líneas (MPa)", f_pjp, row("Soporte del ojal E: PJP tapas–paredes")["dem"], tol=3e-3); chk("  capacidad 0,60FEXX/(1,20Nd)", Fw_, row("Soporte del ojal E: PJP tapas–paredes")["cap"])
# desgarro de las tapas hacia las paredes (empuje) y hacia la nariz (retorno): rayos propios desde E
def ray(pl, dv):
    best = math.inf
    for i_ in range(len(pl)):
        a_, b_ = pl[i_], pl[(i_ + 1) % len(pl)]; e_ = (b_[0] - a_[0], b_[1] - a_[1]); den = dv[0] * e_[1] - dv[1] * e_[0]
        if abs(den) < 1e-12: continue
        tt = (a_[0] * e_[1] - a_[1] * e_[0]) / den; uu = (a_[0] * dv[1] - a_[1] * dv[0]) / den
        if tt > 0 and -1e-9 <= uu <= 1 + 1e-9: best = min(best, tt)
    return best
aR = min(ray(cap_, (-u_[0], -u_[1])) for u_ in dirs) - P["pv_dE"] / 2; aN = min(ray(cap_, u_) for u_ in dirs) - P["pv_dE"] / 2
chk("Tapas: desgarro hacia las paredes traseras (MPa)", Fs / 2 / (2 * P["pv_tl"] * aR), row("Tapas del cajón E: desgarro por corte hacia las paredes")["dem"], tol=3e-3)
Fret_ = math.pi / 4 * (P["D_bore"] ** 2 - P["d_rod"] ** 2) * P["p_ret"] / 10
chk("Tapas: desgarro hacia la nariz con la tracción del retorno (MPa)", Fret_ / 2 / (2 * P["pv_tl"] * aN), row("Tapas del cajón E: desgarro hacia la nariz")["dem"], tol=3e-3)
# holgura cuerpo del cilindro–piezas del soporte (todas las piezas comparten cota con el cuerpo: z del eje ± D/2 cubre las tapas)
def pin_poly(pl, p_):
    c_ = False
    for i_ in range(len(pl)):
        a_, b_ = pl[i_], pl[i_ - 1]
        if (a_[1] > p_[1]) != (b_[1] > p_[1]) and p_[0] < (b_[0] - a_[0]) * (p_[1] - a_[1]) / (b_[1] - a_[1]) + a_[0]: c_ = not c_
    return c_
def sdist(p_, a_, b_):
    ex, ey = b_[0] - a_[0], b_[1] - a_[1]; l_ = ex * ex + ey * ey; tt = max(0, min(1, ((p_[0] - a_[0]) * ex + (p_[1] - a_[1]) * ey) / l_)) if l_ else 0
    return math.hypot(p_[0] - a_[0] - tt * ex, p_[1] - a_[1] - tt * ey)
def crosses(a_, b_, c_, d_):
    o_ = lambda p_, q_, r_: (q_[0] - p_[0]) * (r_[1] - p_[1]) - (q_[1] - p_[1]) * (r_[0] - p_[0])
    return o_(a_, b_, c_) * o_(a_, b_, d_) < 0 and o_(c_, d_, a_) * o_(c_, d_, b_) < 0
def pdist(A_, B_):
    if any(pin_poly(B_, p_) for p_ in A_) or any(pin_poly(A_, p_) for p_ in B_): return -1.0
    if any(crosses(A_[i_], A_[(i_ + 1) % len(A_)], B_[j_], B_[(j_ + 1) % len(B_)]) for i_ in range(len(A_)) for j_ in range(len(B_))): return -1.0
    return min(min(sdist(p_, B_[j_], B_[(j_ + 1) % len(B_)]) for j_ in range(len(B_)) for p_ in A_), min(sdist(p_, A_[j_], A_[(j_ + 1) % len(A_)]) for j_ in range(len(A_)) for p_ in B_))
def rect_u(o_, u_, s0, s1, w_):
    n_ = (-u_[1], u_[0]); return [(o_[0] + s * u_[0] + k * w_ / 2 * n_[0], o_[1] + s * u_[1] + k * w_ / 2 * n_[1]) for s, k in ((s0, -1), (s1, -1), (s1, 1), (s0, 1))]
clrE = min(pdist(rect_u((0, 0), u_, P["e_body"], L0 - P["c_rod"], P["D_body"]), q["poligono_local"]) for u_ in dirs for q in SE["piezas"])
print(f"    holgura cuerpo del cilindro–soporte E (barrido propio, {len(dirs)} estados): {clrE:.2f} mm; núcleo {row('Cuerpo del cilindro libre del soporte del ojal E')['cap']:.2f} mm")
if clrE < 5 or row("Cuerpo del cilindro libre del soporte del ojal E")["cap"] > clrE + 1e-6: fails.append("holgura cuerpo del cilindro–soporte E"); print("XX  holgura cuerpo del cilindro–soporte E")
# geometría constructiva: tapas entre las paredes, rebaje, acceso exterior y filete de refuerzo mínimo (AWS D1.1 Tabla 5.8)
if not (SE["tapas"]["lado"] <= 2 * biE + 1e-9 and all(abs(v[0]) <= biE + 1e-6 and abs(v[1]) <= biE + 1e-6 for v in cap_)): fails.append("tapas fuera del interior del cajón"); print("XX  tapas fuera del interior")
chk("Soporte E: rebaje de la tapa superior bajo el borde (mm)", SE["z_paredes"][1] - SE["tapas"]["z_sup"][1], P["pv_rebt"])
wmin_ = lambda T: 3 if T <= 6 else 5 if T <= 12 else 6 if T <= 20 else 8
chk("Soporte E: filete de refuerzo mínimo AWS D1.1 Tabla 5.8 (mm)", wmin_(max(P["pv_tbox"], P["t_base"], P["pv_tl"])), row("Soporte del ojal E: filete de refuerzo mínimo")["dem"])
chk("Soporte E: distancia de la cara exterior al borde de la base (mm)", P["B"] / 2 - (max(abs(E[0]), abs(E[1])) + bE), row("Soporte del ojal E: acceso exterior")["cap"])
# pasador E (22-11-2026): 10 mm sobre la tapa superior; por debajo, al ras de la tapa inferior o hasta 10 mm, dejando 10 mm de diseño (≥ 5) sobre la cara del
# inserto de esquina (con el saliente fijo de 10 mm el extremo quedaba bajo la cara del inserto)
PE_ = PV["fabricacion"]["pasador_E"]; INS_ = SE.get("refuerzo") or SE.get("inserto"); tIns_ = INS_["t"] if INS_ else P["t_base"]   # cara superior del refuerzo (z = t_base + t_d)
zTi_ = SE["tapas"]["z_inf"][0]; zTs_ = SE["tapas"]["z_sup"][1]
z0_ = min(zTi_, max(zTi_ - 10, tIns_ + 10)); z1_ = zTs_ + 10
chk("Pasador E: extremo inferior (z, mm)", z0_, PE_["z"][0]); chk("Pasador E: extremo superior (z, mm)", z1_, PE_["z"][1]); chk("Pasador E: largo (mm)", z1_ - z0_, PE_["largo"])
if z0_ - tIns_ < 5: fails.append("pasador E bajo la cara del inserto"); print("XX  pasador E bajo la cara del inserto")
else: print(f"OK  pasador E: extremo inferior a {z0_ - tIns_:.0f} mm sobre la cara del inserto de {tIns_} mm (≥ 5)")
mPin_ = 7.85e-6 * math.pi / 4 * P["pv_dE"] ** 2 * (z1_ - z0_)
area_cap = abs(sum(cap_[i_][0] * cap_[(i_ + 1) % len(cap_)][1] - cap_[(i_ + 1) % len(cap_)][0] * cap_[i_][1] for i_ in range(len(cap_)))) / 2 - math.pi / 4 * P["pv_dE"] ** 2
hW = SE["z_paredes"][1] - SE["z_paredes"][0]
mOwn = 7.85e-6 * (sum((x1 - x0) * (y1 - y0) for _, (x0, x1, y0, y1) in rects) * hW + 2 * area_cap * P["pv_tl"]) + mPin_
chk("Soporte E: masa propia (piezas + pasador E, kg)", mOwn, PV["soporte_E"]["masa"])
# tornillos de la placa-guía: grupo elástico con la carga en el contacto (empuje a calado con roce del canto / atasco)
inst = PV["fabricacion"]["placas_leva"]["instancias"]["1_antihorario"]; Bt = inst["pernos"]; nB = len(Bt)
Gc = (sum(b[0] for b in Bt) / nB, sum(b[1] for b in Bt) / nB); J = sum((b[0] - Gc[0]) ** 2 + (b[1] - Gc[1]) ** 2 for b in Bt)
gH = max(G_, key=lambda g: g["h"]); first_i = min(range(len(lw)), key=lambda i: abs(lw[i][0] - first))
tJ = (dense[first_i + 1][0] - dense[first_i][0], dense[first_i + 1][1] - dense[first_i][1]); nt = math.hypot(*tJ); tJ = (tJ[0] / nt, tJ[1] / nt); ninJ = (-tJ[1], tJ[0])
loads = [(Tst, (gH["q"][0] - rf * gH["nin"][0], gH["q"][1] - rf * gH["nin"][1]), gH["nin"], gH["tp"], mu_c), (NR, (dense[first_i][0] - rf * ninJ[0], dense[first_i][1] - rf * ninJ[1]), ninJ, tJ, 0.0)]
def vmax(N, p, nin, tp, mu):
    Fv = (-nin[0] * N + mu * N * tp[0], -nin[1] * N + mu * N * tp[1]); M = (p[0] - Gc[0]) * Fv[1] - (p[1] - Gc[1]) * Fv[0]
    return max(math.hypot(Fv[0] / nB - (b[1] - Gc[1]) * M / J, Fv[1] / nB + (b[0] - Gc[0]) * M / J) for b in Bt)
Vb = max(vmax(*L) for L in loads); Ab = math.pi / 4 * P["pv_db"] ** 2
chk("Tornillos de la placa-guía: corte del grupo elástico (MPa)", Vb / Ab, row("Tornillos de la placa-guía: corte")["dem"], tol=5e-3); chk("  Fnv/Ω = 0,45·Fu/2", 0.45 * P["pv_Fub"] / 2, row("Tornillos de la placa-guía: corte")["cap"])
Es = P["E"] / (2 * (1 - P["nu"] ** 2)); lc = P["pv_tcam"] - 2
def seg_of(q):   # tramo de la trayectoria que contiene Q (mínima distancia) → radio del canto con signo
    best = None
    for s_ in SC:
        d = min(math.hypot(q[0] - x[0], q[1] - x[1]) for x in [seg_at(s_, k / 200) for k in range(201)])
        if best is None or d < best[0]: best = (d, s_)
    s_ = best[1]
    return float("inf") if s_["tipo"] == "linea" else (s_["radio"] - rf if s_["sentido"] == "horario" else -(s_["radio"] + rf))
p0max = 0.0
for g in G_:
    Rc = seg_of(g["q"]); Reff = 1 / (1 / rf + (0 if math.isinf(Rc) else 1 / Rc)); p0max = max(p0max, math.sqrt(g["h"] * Fe_st / lc * Es / (math.pi * Reff)))
chk("Placa-guía: Hertz con el radio real del canto, empuje a calado (MPa)", p0max, row("Placa-guía: contacto de Hertz extremo del pasador Q–canto templado, empuje")["dem"], tol=5e-3)
# vástago: flexocompresión a calado (AISC 360-22 H1-1a, E3, B1) con el roce del ojal Q y el peso
Lc_ = L0 + P["stroke"]; d_ = P["d_rod"]; Ar = math.pi / 4 * d_ ** 2; rg = d_ / 4; Fy_r = P["pv_Fyrod"]; Pr = Fst * 1e3
Fe_ = math.pi ** 2 * P["E"] / (Lc_ / rg) ** 2; Fcr = 0.658 ** (Fy_r / Fe_) * Fy_r if Fy_r / Fe_ <= 2.25 else 0.877 * Fe_
Pc = Fcr * Ar / 1.67; Mc = Fy_r * d_ ** 3 / 6 / 1.67; Pe1 = math.pi ** 2 * P["E"] * math.pi * d_ ** 4 / 64 / Lc_ ** 2
Mr = math.hypot(P["pv_muE"] * Pr * P["pv_dq"] / 2, P["m_cyl"] * 9.80665 * Lc_ / 8) / (1 - 1.6 * Pr / Pe1)
chk("Vástago: P_r/P_c + 8/9·M_r/M_c", Pr / Pc + 8 / 9 * Mr / Mc, row("Vástago: flexocompresión")["dem"])
est = [v for v in D["verificaciones"] if v["grp"] in ("Uña", "Articulaciones", "Soporte del ojal E", "Placas-leva") and v["fu"] is not None and v["estado"] not in ("info", "pend")]
print(f"    FU máximo en las filas nuevas del modo 2: {max(v['fu'] for v in est):.3f} ({len(est)} filas)")
GEO = ("holgura vertical", "holgura en planta", "holgura a la mesa", "queda sobre el inserto", "queda sobre el refuerzo", "refuerzo: filete mínimo", "refuerzo: tapones", "atiesador tangencial: holguras", "Filete", "Pasadores de posición", "filete de refuerzo", "acceso exterior", "rincón para el filete", "garganta efectiva", "largo de la zapata", "distancia al borde", "enganche de la rosca", "capa templada", "deformación del ligamento", "separación mínima")              # criterios geométricos (FU ≤ 1), no de resistencia
res = [v for v in est if not any(g in v["nombre"] for g in GEO)]
print(f"    FU máximo de resistencia: {max(v['fu'] for v in res):.3f} ({len(res)} filas)")
# excepción (12-11-2026): la flexión de la base junto al refuerzo cuadrado de 35 mm (el máximo bajo el cuerpo del cilindro) queda en FU 0,91–0,94 (advertencia, ≤ 1)
exc_ = [v for v in res if "con refuerzo de" in v["nombre"] and "flexión de la base y del refuerzo" in v["nombre"]]
if exc_: print(f"    refuerzo cuadrado (advertencia admitida, ≤ 1): FU máx. {max(v['fu'] for v in exc_):.3f}")
if any(v["fu"] > 1 for v in exc_): fails.append("refuerzo: FU > 1"); print("XX  refuerzo FU > 1")
res = [v for v in res if v not in exc_]
if max(v["fu"] for v in res) > 0.90: fails.append("FU > 0,90 en el modo 2"); print("XX  FU > 0,90")

print("== 5b. Elementos sobre la base: orejas de izaje, placas-guía (reflexiones y rotaciones), soportes E y partes móviles (geometría propia) ==")
ylg = P["B"] / 2 - P["c_lug"]; hwe = P["t_ear"] / 2 + P["w_ear"]
ears = []
for cx_, cy_ in ((P["x_lug"], ylg), (-P["x_lug"], ylg), (P["x_lug"], -ylg), (-P["x_lug"], -ylg)):
    rr_ = math.hypot(cx_, cy_); ur = (cx_ / rr_, cy_ / rr_)
    ears.append(rect_u((cx_ - P["R_ear"] * ur[0], cy_ - P["R_ear"] * ur[1]), ur, 0, 2 * P["R_ear"], 2 * hwe))
plates = [PV["fabricacion"]["placas_leva"]["instancias"][k]["contorno"] for k in ("1_antihorario", "1_horario", "2_antihorario", "2_horario")]
sups = [q["poligono"] for c_ in ("cilindro1", "cilindro2") for q in SE[c_]["piezas"]]
mesa = [(Ro * math.cos(2 * math.pi * k / 144), Ro * math.sin(2 * math.pi * k / 144)) for k in range(144)]
dPE = min(pdist(pl, e_) for pl in plates for e_ in ears); dPS = min(pdist(pl, s_) for pl in plates for s_ in sups)
dES = min(pdist(e_, s_) for e_ in ears for s_ in sups); dEM = min(sdist((0.0, 0.0), e_[i_], e_[(i_ + 1) % 4]) for e_ in ears for i_ in range(4)) - Ro   # distancia exacta al círculo R = D/2
chk("Placas-guía–orejas de izaje: holgura mínima (mm)", dPE, row("Placas-guía libres de las orejas de izaje")["cap"], tol=1e-3)
# partes móviles: empuje (Q en el canto, bloque alineado con Q–P) y retorno (bloque alineado con E–Q), cuatro instancias por rotación de 180° y reflexión
def tr_(k):
    rot = (lambda q: (-q[0], -q[1])); f1 = (lambda q: q) if k.endswith("antihorario") else refl
    return (lambda q: rot(f1(q))) if k.startswith("2") else f1
dmov = math.inf
for k in ("1_antihorario", "1_horario", "2_antihorario", "2_horario"):
    f_ = tr_(k); Ek = f_(E); st_ = [(f_(tuple(Q_)), f_(tuple(P_))) for Q_, P_ in zip(PV["posiciones"]["1_antihorario"]["Q"], PV["posiciones"]["1_antihorario"]["P"])]
    st_ += [(f_(tuple(q["Q"])), None) for q in PL["retorno"]]
    for Q_, P_ in st_:
        Lk = math.hypot(Q_[0] - Ek[0], Q_[1] - Ek[1]); u_ = ((Q_[0] - Ek[0]) / Lk, (Q_[1] - Ek[1]) / Lk)
        bb_ = u_ if P_ is None else (lambda d_: ((P_[0] - Q_[0]) / d_, (P_[1] - Q_[1]) / d_))(math.hypot(P_[0] - Q_[0], P_[1] - Q_[1]))
        if P_ is not None:   # el bloque se alinea con Q–P (y gira el ángulo de equilibrio con roce: se toma alineado, como referencia)
            pass
        polys_, ebq = block_polys(Q_, bb_)
        hub = [(Q_[0] + ebq * math.cos(k_ * math.pi / 12), Q_[1] + ebq * math.sin(k_ * math.pi / 12)) for k_ in range(24)]
        parts = [rect_u(Ek, u_, P["e_body"], L0 - P["c_rod"], P["D_body"]), rect_u(Ek, u_, L0 - P["c_rod"], Lk, P["d_rod"]), hub] + polys_
        for e_ in ears:
            cxe = sum(v[0] for v in e_) / 4; cye = sum(v[1] for v in e_) / 4
            if math.hypot(cxe - Q_[0], cye - Q_[1]) > 1500 and math.hypot(cxe - Ek[0], cye - Ek[1]) > 1500: continue
            for pa in parts: dmov = min(dmov, pdist(e_, pa))
print(f"    orejas–partes móviles: {dmov:.1f} mm (núcleo {row('Orejas de izaje libres de las partes móviles')['cap']:.1f}); placas–soportes E {dPS:.1f}; orejas–soportes E {dES:.1f}; orejas–mesa {dEM:.1f} mm")
if min(dPE, dPS, dES, dEM, dmov) < 5: fails.append("interferencia entre elementos sobre la base"); print("XX  interferencia entre elementos sobre la base")
if abs(dmov - row("Orejas de izaje libres de las partes móviles")["cap"]) > 0.02 * dmov: fails.append("holgura orejas–partes móviles difiere del núcleo"); print("XX  holgura orejas–partes móviles difiere")
chk("Orejas de izaje–placas, soportes E y mesa: holgura mínima (mm)", min(dPE, dES, dEM), row("Orejas de izaje libres de las placas-guía")["cap"], tol=2e-3)   # el núcleo aproxima la mesa con un polígono de 144 lados
print("== 5c. Plancha base bajo el soporte E SIN inserto (ins_on = 0): contacto unilateral sin anclaje (franja propia y FEA de Mindlin propia con contacto unilateral) ==")
row0 = lambda prefix: row(prefix, V0)
# Método 1 (franja, réplica): soporte rígido; M = F·h, h = altura del eje sobre la plancha; losa solo a compresión; retención solo en la mesa (R ≤ D/2);
# M_corte = M·(1 − a/s_H) si la mesa queda detrás del talón (s_H > a), si no M; b = w + a; σ = 6·M_corte/(b·t²); τ = 1,5·(M/a)/(b·t).
hE = zc0E - P["t_base"]; tB = P["t_base"]; O_loc = (-sxE * E[0], syE * E[1])
VV = [(x, y) for _, (x0, x1, y0, y1) in rects for x in (x0, x1) for y in (y0, y1)]
def strip(F_, sgn):
    best = None
    for u_ in dirs:
        f_ = (sgn * u_[0], sgn * u_[1]); g_ = (-f_[1], f_[0]); pf = [p[0] * f_[0] + p[1] * f_[1] for p in VV]; pg = [p[0] * g_[0] + p[1] * g_[1] for p in VV]
        toe = max(pf); a_ = toe - min(pf); w_ = max(pg) - min(pg); sH_ = toe - (O_loc[0] * f_[0] + O_loc[1] * f_[1]) + P["D_top"] / 2; M_ = F_ * hE
        Mc_ = M_ * (1 - a_ / sH_) if sH_ > a_ else M_; b_ = w_ + a_; s_ = 6 * Mc_ / (b_ * tB * tB)
        if best is None or s_ > best[0]: best = (s_, M_, a_, b_, u_, sH_)
    return best
stE, stR = strip(Fs, -1), strip(Fret_, 1)
chk("Plancha base: σ de la franja, empuje a calado (MPa)", stE[0], row0("Plancha base bajo el soporte del ojal E: flexión sin anclaje, empuje")["dem"], tol=3e-3)
chk("Plancha base: σ de la franja, retorno (MPa)", stR[0], row0("Plancha base bajo el soporte del ojal E: flexión sin anclaje, retorno")["dem"], tol=3e-3)
chk("Plancha base: τ = 1,5·(M/a)/(b·t), empuje (MPa)", 1.5 * stE[1] / stE[2] / (stE[3] * tB), row0("Plancha base bajo el soporte del ojal E: corte")["dem"], tol=3e-3)
for nm_, st_ in (("empuje", stE), ("retorno", stR)):
    # con 1,25·Fy/Nd y la base de 20 mm el retorno de la franja queda bajo 1 (FU ≈ 0,93); el empuje no cumple sin inserto
    if nm_ == "empuje" and st_[0] <= 1.25 * Fy / Nd: fails.append("plancha base sin anclaje (" + nm_ + "): la franja debería exceder 1,25·Fy/Nd"); print("XX  franja " + nm_)
    if row0("Plancha base bajo el soporte del ojal E: flexión sin anclaje, " + nm_).get("estado") != "pend": fails.append("estado de la fila de la plancha (" + nm_ + ")")
# Mesa vacía (el calado no depende de la carga): retención disponible = peso propio de la parte que gira (mesa + disco rotatorio + medio pivote + bloques-uña;
# masas de derivados.masas, verificadas por indep_tt300c.py) frente a la pedida por los n_cil soportes con el brazo más largo, n_cil·M/s_H.
MS_ = DV["masas"]; Wmv = (MS_["disc"] + MS_["ssTop"] + 0.5 * MS_["pivot"] + MS_["dogs"]) * 9.80665 / 1e3; Tmv = P["n_cyl"] * stE[1] / stE[5] / 1e3
MV_ = D0["pivotado"]["fabricacion"]["soporte_E"]["plancha_base"]["mesa_vacia"]
chk("Plancha base: peso propio de la mesa vacía que retiene (kN)", Wmv, MV_["W_mesa_kN"], tol=2e-3)
chk("Plancha base: retención pedida por los soportes, n_cil·M/s_H (kN)", Tmv, MV_["T_req_kN"], tol=3e-3)
if not (Tmv > Wmv and MV_["cumple"] is False): fails.append("mesa vacía: la retención debería faltar"); print("XX  mesa vacía")
# Revisión con la base completa (docs/qa/plancha_base_soporte_E.md): con M₂ = −M₁ el par pasa de un soporte al otro por torsión de la base; fuerza de
# esquina ≈ M/B y m_xy ≈ M/(2·B) (placa libre en torsión pura: τ = 6·m_xy/t², cota inferior frente a Fy/(Nd·√3))
RV_ = D0["pivotado"]["fabricacion"]["soporte_E"]["plancha_base"]["revision_base_completa"]
chk("Plancha base, base completa: fuerza de esquina de la torsión M/B (kN)", stE[1] / P["B"] / 1e3, RV_["V_esquina_kN"])
chk("Plancha base, base completa: τ de torsión 6·m_xy/t² (MPa)", 6 * stE[1] / (2 * P["B"]) / tB ** 2, RV_["tau_torsion_MPa"])
if RV_["fu_torsion_cota_inferior"] <= 1: fails.append("torsión de la base: la cota inferior debería exceder 1"); print("XX  torsión de la base")
# Estado global (docs/qa/plancha_base_soporte_E.md §4): las filas «pend» con FU > 1 no se excluyen en silencio: van a verdict.pendientes_criticos
# (ordenadas por FU) y el estado global queda «NO CUMPLE / PENDIENTE DE DECISIÓN» si el resto cumple
VD_ = D["verdict"]; pc_ = sorted([v for v in D["verificaciones"] if v["estado"] == "pend" and v.get("fu") is not None and v["fu"] > 1], key=lambda v: -v["fu"])
if [v["nombre"] for v in pc_] != [v["nombre"] for v in VD_["pendientes_criticos"]]: fails.append("pendientes críticos del veredicto"); print("XX  pendientes críticos del veredicto")
chk("Pendientes críticos: FU máximo (plancha base sin anclaje)", pc_[0]["fu"] if pc_ else 0.0, VD_["fuMaxPend"], tol=1e-9)
est_ = "NO CUMPLE" if not (VD_["gira"] and VD_["estructura"]) else ("NO CUMPLE / PENDIENTE DE DECISIÓN" if pc_ else "CUMPLE")
print(f"    estado global: {VD_['estado_global']} (propio: {est_}); {len(pc_)} pendientes críticos")
if est_ != VD_["estado_global"]: fails.append("estado global del veredicto"); print("XX  estado global")
# Método 2 (contraste): FEA propia de Mindlin (Q4 con integración selectiva: flexión 2×2, corte 1 punto) de la plancha (cuadrante del cilindro 1, malla
# de 40 mm), soporte rígido por 3 grados de libertad maestros (w₀, θ_x, θ_y) en los nudos de la huella de las paredes, momento aplicado al cuerpo rígido,
# resortes de contacto unilaterales en todos los nudos (conjunto activo: se liberan los traccionados y se reactivan los que penetran) y apoyo bilateral en
# la huella de la mesa (R ≤ D/2: la mesa cargada retiene la plancha). Se compara la conclusión (σ > Fy/Nd en ambos casos), no el valor: la FEA tiene
# picos en las esquinas de la huella rígida que dependen de la malla.
try:
    import numpy as np, scipy.sparse as sp_, scipy.sparse.linalg as spl_
    hm_ = 40.0; Bh_ = P["B"] / 2; nx_ = ny_ = int(round(Bh_ / hm_)); Es_, nu_ = P["E"], P["nu"]
    Xn = np.repeat(np.linspace(0, Bh_, nx_ + 1), ny_ + 1); Yn = np.tile(np.linspace(-Bh_, 0, ny_ + 1), nx_ + 1); nn_ = Xn.size
    els_ = np.array([[i * (ny_ + 1) + j, (i + 1) * (ny_ + 1) + j, (i + 1) * (ny_ + 1) + j + 1, i * (ny_ + 1) + j + 1] for i in range(nx_) for j in range(ny_)])
    Xl, Yl = sxE * (Xn - E[0]), -syE * (Yn - E[1])                  # marco local del soporte
    inF_ = np.zeros(nn_, bool)
    for _, (x0, x1, y0, y1) in rects: inF_ |= (Xl >= x0 - hm_ / 2) & (Xl <= x1 + hm_ / 2) & (Yl >= y0 - hm_ / 2) & (Yl <= y1 + hm_ / 2)
    hold_ = np.hypot(Xn, Yn) <= P["D_top"] / 2
    Db_ = Es_ * tB ** 3 / (12 * (1 - nu_ ** 2)) * np.array([[1, nu_, 0], [nu_, 1, 0], [0, 0, (1 - nu_) / 2]]); Ds_ = 5 / 6 * Es_ / (2 * (1 + nu_)) * tB * np.eye(2)
    def Bm(xi, et, a_):
        sgx, sgy = (-1, 1, 1, -1), (-1, -1, 1, 1); Bb_ = np.zeros((3, 12)); Bs_ = np.zeros((2, 12))
        for k in range(4):
            N_ = 0.25 * (1 + xi * sgx[k]) * (1 + et * sgy[k]); dx_ = 0.25 * sgx[k] * (1 + et * sgy[k]) / a_; dy_ = 0.25 * sgy[k] * (1 + xi * sgx[k]) / a_
            Bb_[0, 3 * k + 1] = dx_; Bb_[1, 3 * k + 2] = dy_; Bb_[2, 3 * k + 1] = dy_; Bb_[2, 3 * k + 2] = dx_; Bs_[0, 3 * k] = dx_; Bs_[0, 3 * k + 1] = -N_; Bs_[1, 3 * k] = dy_; Bs_[1, 3 * k + 2] = -N_
        return Bb_, Bs_
    ah = hm_ / 2; gq = (-1 / math.sqrt(3), 1 / math.sqrt(3)); Ke_ = sum(Bm(x_, y_, ah)[0].T @ Db_ @ Bm(x_, y_, ah)[0] * ah * ah for x_ in gq for y_ in gq)
    B0b, B0s = Bm(0, 0, ah); Ke_ = Ke_ + B0s.T @ Ds_ @ B0s * 4 * ah * ah
    dof_ = np.stack([3 * els_, 3 * els_ + 1, 3 * els_ + 2], axis=2).reshape(len(els_), 12)
    K0_ = sp_.csr_matrix((np.tile(Ke_.ravel(), len(els_)), (np.repeat(dof_, 12, axis=1).ravel(), np.tile(dof_, (1, 12)).ravel())), shape=(3 * nn_, 3 * nn_))
    fr_ = np.array([d_ for k in range(nn_) if not inF_[k] for d_ in (3 * k, 3 * k + 1, 3 * k + 2)]); nf_ = fr_.size
    Tr_, Tc_, Tv_ = list(fr_), list(range(nf_)), [1.0] * nf_
    for k in np.where(inF_)[0]:     # w = w₀ + θ₁·(x − E_x) + θ₂·(y − E_y); β_x = θ₁, β_y = θ₂ (cuerpo rígido)
        Tr_ += [3 * k, 3 * k, 3 * k, 3 * k + 1, 3 * k + 2]; Tc_ += [nf_, nf_ + 1, nf_ + 2, nf_ + 1, nf_ + 2]; Tv_ += [1.0, Xn[k] - E[0], Yn[k] - E[1], 1.0, 1.0]
    T_ = sp_.csr_matrix((Tv_, (Tr_, Tc_)), shape=(3 * nn_, nf_ + 3)); Kr_ = (T_.T @ K0_ @ T_).tocsr(); kc_ = 1e8
    def fea_(F_, u_, sgn):
        f_ = (sgn * u_[0], sgn * u_[1]); fg_ = (sxE * f_[0], -syE * f_[1]); mx_, my_ = hE * F_ * (-fg_[1]), hE * F_ * fg_[0]
        rhs_ = np.zeros(nf_ + 3); rhs_[nf_ + 1] = -my_; rhs_[nf_ + 2] = mx_; act_ = inF_.copy()
        for it_ in range(200):
            kv_ = np.where(act_ | hold_, kc_, 0.0); Kc_ = sp_.csr_matrix((kv_, (3 * np.arange(nn_), 3 * np.arange(nn_))), shape=(3 * nn_, 3 * nn_))
            uu_ = T_ @ spl_.spsolve((Kr_ + T_.T @ Kc_ @ T_).tocsc(), rhs_); w_ = uu_[0::3]
            new_ = act_.copy(); new_[(w_ > 1e-9) & ~hold_] = False; new_[w_ < -1e-9] = True
            if (new_ == act_).all(): break
            act_ = new_
        sg_ = 0.0
        for ie, e in enumerate(els_):
            if inF_[e].all(): continue
            s_ = 6 * (Db_ @ (B0b @ uu_[dof_[ie]])) / tB ** 2; sg_ = max(sg_, math.sqrt(s_[0] ** 2 - s_[0] * s_[1] + s_[1] ** 2 + 3 * s_[2] ** 2))
        return sg_, it_, float(w_.max())
    for nm_, F_, st_, sgn in (("empuje a calado", Fs, stE, -1), ("retorno (atasco)", Fret_, stR, 1)):
        sF, itF, wF = fea_(F_, st_[4], sgn)
        print(f"    {nm_:18s} franja σ = {st_[0]:8.1f} MPa (FU {st_[0] / (Fy / Nd):5.2f}); FEA unilateral σ_vm máx (malla 40) = {sF:8.1f} MPa (FU {sF / (Fy / Nd):5.2f}), levantamiento {wF:5.2f} mm, {itF} iteraciones")
        if sF <= Fy / Nd: fails.append("FEA de la plancha (" + nm_ + "): la conclusión no coincide con la franja"); print("XX  FEA " + nm_)
    # Método 3 (revisión con la base completa, docs/qa/plancha_base_soporte_E.md): plancha entera con los DOS soportes (cilindro 2 por rotación de 180°:
    # F₂ = −F₁, M₂ = −M₁), malla de 80 mm, peso propio de la plancha (ρ·g·t), mesa vacía uniforme en R_i…R_o (W_d + bloques-uña) y soportes con medio
    # cilindro en los maestros; contacto unilateral en todos los nudos (conjunto activo; ante un ciclo se cambia solo el 10 % de los peores). Se verifica la
    # conclusión: con la mesa vacía la base no tiene rigidez a torsión y queda apoyada en pocos nudos (los pies) con levantamientos de decenas de mm; con la
    # mesa cargada (huella bilateral) el levantamiento es de pocos mm junto al talón (el caso del modelo de un soporte).
    hb_ = 80.0; nb_ = int(round(P["B"] / hb_)); xs_ = np.linspace(-P["B"] / 2, P["B"] / 2, nb_ + 1)
    Xb = np.repeat(xs_, nb_ + 1); Yb = np.tile(xs_, nb_ + 1); nnb = Xb.size
    elb = np.array([[i * (nb_ + 1) + j, (i + 1) * (nb_ + 1) + j, (i + 1) * (nb_ + 1) + j + 1, i * (nb_ + 1) + j + 1] for i in range(nb_) for j in range(nb_)])
    a2_ = hb_ / 2; Kb_ = sum(Bm(x_, y_, a2_)[0].T @ Db_ @ Bm(x_, y_, a2_)[0] * a2_ * a2_ for x_ in gq for y_ in gq); _, B0s2 = Bm(0, 0, a2_); Kb_ = Kb_ + B0s2.T @ Ds_ @ B0s2 * 4 * a2_ * a2_
    dfb = np.stack([3 * elb, 3 * elb + 1, 3 * elb + 2], axis=2).reshape(len(elb), 12)
    Kf_ = sp_.csr_matrix((np.tile(Kb_.ravel(), len(elb)), (np.repeat(dfb, 12, axis=1).ravel(), np.tile(dfb, (1, 12)).ravel())), shape=(3 * nnb, 3 * nnb))
    sups_ = []
    for sg_ in (1, -1):
        Xl_, Yl_ = sxE * (sg_ * Xb - E[0]), -syE * (sg_ * Yb - E[1]); m_ = np.zeros(nnb, bool)
        for _, (x0, x1, y0, y1) in rects: m_ |= (Xl_ >= x0 - hb_ / 2) & (Xl_ <= x1 + hb_ / 2) & (Yl_ >= y0 - hb_ / 2) & (Yl_ <= y1 + hb_ / 2)
        sups_.append(m_)
    inS_ = sups_[0] | sups_[1]; fn_ = np.where(~inS_)[0]; frb = np.stack([3 * fn_, 3 * fn_ + 1, 3 * fn_ + 2], axis=1).ravel(); nfb = frb.size
    Tr_, Tc_, Tv_ = [frb], [np.arange(nfb)], [np.ones(nfb)]
    for si_, (m_, c_) in enumerate(zip(sups_, (E, (-E[0], -E[1])))):
        k_ = np.where(m_)[0]; o_ = np.ones(k_.size)
        Tr_ += [3 * k_, 3 * k_, 3 * k_, 3 * k_ + 1, 3 * k_ + 2]; Tc_ += [o_ * (nfb + 3 * si_), o_ * (nfb + 3 * si_ + 1), o_ * (nfb + 3 * si_ + 2), o_ * (nfb + 3 * si_ + 1), o_ * (nfb + 3 * si_ + 2)]
        Tv_ += [o_, Xb[k_] - c_[0], Yb[k_] - c_[1], o_, o_]
    Tb_ = sp_.csr_matrix((np.concatenate(Tv_), (np.concatenate(Tr_), np.concatenate(Tc_).astype(int))), shape=(3 * nnb, nfb + 6)); Krb = (Tb_.T @ Kf_ @ Tb_).tocsr()
    Tw_ = (sp_.csr_matrix((np.ones(nnb), (np.arange(nnb), 3 * np.arange(nnb))), shape=(nnb, 3 * nnb)) @ Tb_).tocsr()
    fz_ = np.zeros(nnb)
    for e in elb: fz_[e] -= 7.85e-6 * 9.80665 * tB * hb_ * hb_ / 4                    # peso propio de la plancha
    rb_ = np.hypot(Xb, Yb); ring_ = (rb_ >= D["apoyo"]["Ri"]) & (rb_ <= D["apoyo"]["Ro"])
    fz_[ring_] -= Wmv * 1e3 / ring_.sum()                                                 # mesa vacía, uniforme en el anillo de contacto
    rhsb = Tb_.T @ np.concatenate([np.stack([fz_, np.zeros(nnb), np.zeros(nnb)], axis=1).ravel()])
    Wsup_ = (MS_["brackets"] + MS_["cyl"] / 2) / P["n_cyl"] * 9.80665                    # soporte + medio cilindro en cada maestro (N)
    def fea_full(F_, u_, sgn, holdT):
        f_ = (sgn * u_[0], sgn * u_[1]); fg_ = (sxE * f_[0], -syE * f_[1]); mx_, my_ = hE * F_ * (-fg_[1]), hE * F_ * fg_[0]
        r_ = rhsb.copy()
        for si_, s_ in enumerate((1, -1)): r_[nfb + 3 * si_] -= Wsup_; r_[nfb + 3 * si_ + 1] += -s_ * my_; r_[nfb + 3 * si_ + 2] += s_ * mx_
        hold = (rb_ <= P["D_top"] / 2) if holdT else np.zeros(nnb, bool); act_ = np.ones(nnb, bool); seen_ = set(); part_ = False
        for it_ in range(400):
            w_ = Tw_ @ spl_.spsolve((Krb + Tw_.T @ sp_.diags(np.where(act_ | hold, 1e7, 1e-3)) @ Tw_).tocsc(), r_)
            rel_ = act_ & ~hold & (w_ > 1e-9); add_ = ~act_ & (w_ < -1e-9)
            if not rel_.any() and not add_.any(): break
            new_ = act_.copy()
            if part_:
                if add_.any(): ix_ = np.where(add_)[0]; new_[ix_[np.argsort(w_[ix_])[:max(1, ix_.size // 10)]]] = True
                if rel_.any(): ix_ = np.where(rel_)[0]; new_[ix_[np.argsort(-w_[ix_])[:max(1, ix_.size // 10)]]] = False
            else: new_[rel_] = False; new_[add_] = True
            k_ = hash(new_.tobytes()); part_ = part_ or k_ in seen_; seen_.add(k_); act_ = new_
        return float(w_.max()), int(act_.sum()), it_
    wV, nV, iV = fea_full(Fs, stE[4], -1, False); wC, nC, iC = fea_full(Fs, stE[4], -1, True)
    print(f"    base completa, dos soportes (M₂ = −M₁), malla 80: mesa vacía → levantamiento máx {wV:7.1f} mm, {nV} nudos en contacto de {nnb} ({iV} it.); mesa cargada → {wC:5.1f} mm, {nC} nudos ({iC} it.)")
    if not (wV > 50 and nV <= 20): fails.append("base completa con la mesa vacía: debería quedar apoyada solo en los pies"); print("XX  base completa, mesa vacía")
    if not (wC < 40): fails.append("base completa con la mesa cargada: levantamiento de pocos mm junto al talón"); print("XX  base completa, mesa cargada")
except ImportError:
    print("    numpy/scipy no disponibles: se omite la FEA de contraste")
print("== 6. Pivote: asimetría del par por roce desigual μ_s ± 0,05 (a calado) ==")
F0 = Fst * eta
H = 0.0
for q in pts:
    s = 1.0 if q["vs"] > 0 else -1.0                                  # el roce sobre el pasador se opone al deslizamiento del pasador respecto del bloque
    # signo del deslizamiento propio (diferencias finitas del vector, no solo del módulo)
    th = q["th"]; p, u, d, Q, L = state(th); C = (p[0] - r * u[0], p[1] - r * u[1])
    Cpin = (C[0] * math.cos(h) - C[1] * math.sin(h), C[0] * math.sin(h) + C[1] * math.cos(h)); p1, u1, d1, Q1, L1 = state(th + h)
    Cblk = (Q1[0] + (Lqp - r) * u1[0], Q1[1] + (Lqp - r) * u1[1]); tt = (-u[1], u[0])
    vsig = ((Cpin[0] - Cblk[0]) * tt[0] + (Cpin[1] - Cblk[1]) * tt[1]); s = -1.0 if vsig > 0 else 1.0
    m1, m2 = mu_s + 0.05, mu_s - 0.05; F1, F2 = F0 / (1 + mu_c * m1), F0 / (1 + mu_c * m2)
    nx = F1 * (u[0] + s * m1 * tt[0]) - F2 * (u[0] + s * m2 * tt[0]); ny = F1 * (u[1] + s * m1 * tt[1]) - F2 * (u[1] + s * m2 * tt[1])
    H = max(H, math.hypot(nx, ny))
chk("H_asim al pivote (kN)", H, row("Empuje neto al pivote por roce desigual en el contacto")["dem"])

print("== 7. Sugerencia de E (malla propia de 20 mm) ==")
def feasible_aef(RE_, Lqp_):
    tg = L0 + sf + Lqp_; ca = (R * R + RE_ * RE_ - tg * tg) / (2 * R * RE_)
    if abs(ca) > 1 or RE_ <= R + r: return None
    E_ = (RE_ * math.cos(ph), RE_ * math.sin(ph)); t0 = ph + math.acos(ca); best = float("inf"); qmin = float("inf"); cb = float("inf"); bd = float("inf"); Lmax = 0
    for i in range(21):
        th = t0 + pitch * i / 20; p = pin(th); u, d = unit(E_, p); Q = (p[0] - Lqp_ * u[0], p[1] - Lqp_ * u[1])
        a = abs(E_[0] * p[1] - E_[1] * p[0]) / d; vs = r * abs(1 - (p[0] * u[0] + p[1] * u[1]) / d)
        best = min(best, a - mu_s * vs); qmin = min(qmin, math.hypot(*Q)); Lmax = max(Lmax, d - Lqp_)
        global Lqp
        sv = Lqp; Lqp = Lqp_; cb = min(cb, clr_block(Q, u, [pin(th - pitch), pin(th + pitch)])); Lqp = sv
        bd = min(bd, seg_dist((E_[0] + P["e_body"] * u[0], E_[1] + P["e_body"] * u[1]), (E_[0] + (L0 - P["c_rod"]) * u[0], E_[1] + (L0 - P["c_rod"]) * u[1])) - P["D_body"] / 2 - P["D_top"] / 2)
    ok = qmin - P["pv_dq"] / 2 - P["D_top"] / 2 >= P["pv_cQ"] and cb >= P["pv_cB"] and bd >= P["pv_cc"] and Lmax - L0 + P["s_margin"] <= P["stroke"] and max(abs(E_[0]), abs(E_[1])) + P["pv_box"] / 2 <= Bh
    return best if ok else None
sg = PV["sugerencia"]
own = max(((feasible_aef(RE_, L_) or -1), RE_, L_) for RE_ in range(1300, int((Bh - P["pv_box"] / 2) * math.sqrt(2)) + 1, 20) for L_ in range(200, 700, 20))
print(f"    malla propia: a_ef = {own[0]:.1f} mm en R_E = {own[1]}, L_qp = {own[2]}; núcleo (malla fina): {sg['aEffMin']:.1f} mm en R_E = {sg['RE']}, L_qp = {sg['Lqp']}")
if not (own[0] <= sg["aEffMin"] + 0.5): fails.append("la malla propia encuentra un E mejor que la sugerencia")
if feasible_aef(sg["RE"], sg["Lqp"]) is None: fails.append("la sugerencia no es factible con la geometría propia")
if feasible_aef(RE, Lqp) is None: fails.append("el E por defecto no es factible con la geometría propia")

print("\nRESULTADO:", "OK" if not fails else "DIFERENCIAS: " + "; ".join(fails))
sys.exit(1 if fails else 0)
