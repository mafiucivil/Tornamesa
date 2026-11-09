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
PV, DV = D["pivotado"], D["derivados"]
V = {v["nombre"]: v for v in D["verificaciones"]}
fails = []
def chk(name, mine, tool, tol=1e-3, absol=1e-6):
    ok = abs(mine - tool) <= tol * abs(tool) + absol
    print(f"{'OK ' if ok else 'XX '} {name:78s} indep {mine:13.4f}  núcleo {tool:13.4f}")
    if not ok: fails.append(name)
def row(prefix):
    for k, v in V.items():
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
b, t = P["pv_box"], P["pv_tbox"]
yc = (b * t * t / 2 + 2 * t * b * b / 2) / (3 * b * t)                 # sección en U: pared trasera + 2 laterales
I = b * t ** 3 / 12 + b * t * (yc - t / 2) ** 2 + 2 * (t * b ** 3 / 12 + t * b * (b / 2 - yc) ** 2)
S = I / max(yc, b - yc)
hsum = 2 * (zc0 - P["t_base"])                                        # h_sup + h_inf (tapas simétricas respecto del eje)
chk("Cajón del ojal: flexión F/2·(h_sup + h_inf)/S_U (MPa)", Fs / 2 * hsum / S, row("Cajón del ojal E: flexión")["dem"])
aw = 0.707 * P["pv_wbox"]
chk("Soldadura cajón–base (MPa)", math.hypot(Fs / (4 * b * aw), Fs / 2 * hsum / (aw * b * b)), row("Soldadura cajón del ojal E–base")["dem"])
chk("  capacidad 0,60FEXX/(1,20Nd)", P["FEXX"] * 0.6 / (1.2 * Nd), row("Soldadura cajón del ojal E–base")["cap"])
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
GEO = ("Filete", "largo de la zapata", "distancia al borde", "enganche de la rosca", "capa templada", "deformación del ligamento", "separación mínima")              # criterios geométricos (FU ≤ 1), no de resistencia
res = [v for v in est if not any(g in v["nombre"] for g in GEO)]
print(f"    FU máximo de resistencia: {max(v['fu'] for v in res):.3f} ({len(res)} filas)")
if max(v["fu"] for v in res) > 0.90: fails.append("FU > 0,90 en el modo 2"); print("XX  FU > 0,90")

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
