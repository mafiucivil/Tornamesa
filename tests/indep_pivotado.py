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
chk("Carrera requerida L(θ_fin) − L0 (mm)", max(q["L"] for q in pts) - L0, PV["carrera_req"])
chk("Radio mínimo de Q (mm)", min(math.hypot(*q["Q"]) for q in pts), PV["Q_min"])
for i in (0, 30, 60):
    q, t = pts[i], PV["cinematica"][i]
    chk(f"  θ = {math.degrees(q['th']):7.2f}°: L (mm)", q["L"], t["L"]); chk("              a (mm)", q["a"], t["a"]); chk("              a_ef (mm)", q["aef"], t["a_ef"])
    chk("              fracción tangencial", q["ft"], t["f_tang"]); chk("              fracción radial", q["fr"], t["f_rad"])
    chk("              ángulo del cilindro ψ (°)", math.degrees(math.atan2(q["u"][1], q["u"][0])), t["psi_deg"])

print("== 2. Fuerzas, presión y FS (mismos casos de fricción que el modo guiado) ==")
Ro = P["D_top"] / 2; Ri = P["D_boss"] / 2 + P["c_boss_r"] + P["m_ri"]
NN = DV["N"]
Hecc = lambda mu: mu * NN * P["e"] * (4 / 3) * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4)
Tq = lambda mu, rr: mu * NN * rr / 1e3 + P["mu_bush"] * Hecc(mu) * P["D_piv"] / 2 / 1e3
ru = 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2)
A = math.pi / 4 * P["D_bore"] ** 2; Fst = A * P["p_relief"] / 10 / 1e3
mu_c = P["mu_d"]                     # familia 1 (acero templado–acero con grasa): cam_mat = 0 con la interfaz acero–acero
kf = 1 + mu_c * mu_s
cases = {"nom": (P["mu_nom"], ru), "dis": (P["mu_d"], P["r_ef"]), "borde": (P["mu_d"], Ro), "cont": (P["mu_cont"], P["r_ef"]), "seco": (P["mu_dry"], ru)}
Fdis = None
for c in DV["casos"]:
    mu, rr = cases[c["id"]]; T = Tq(mu, rr)
    F = max(T * 1e3 / P["n_cyl"] / q["aef"] for q in pts) * kf / eta
    chk(f"Caso {c['id']}: F por cilindro (kN)", F, c["F"]); chk(f"Caso {c['id']}: FS", Fst / F, c["FS"]); chk(f"Caso {c['id']}: presión (bar)", F * 1e3 / A * 10, c["p"])
    if c["id"] == "dis": Fdis, Tdis = F, T
Fn_d = [Tdis * 1e3 / P["n_cyl"] / q["aef"] for q in pts]
chk("Fuerza transversal en la leva en el diseño, máx μ_s·F_n (kN)", mu_s * max(Fn_d), max(t["F_leva"] for t in PV["cinematica"]))

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

print("== 4. Placa-leva: perfil (w_nec propio en el retorno) y sincronía ==")
psi0 = math.atan2(pts[0]["u"][1], pts[0]["u"][0])
def Qof(L, w):
    ps = psi0 - w / L; u = (math.cos(ps), math.sin(ps)); return (E[0] + L * u[0], E[1] + L * u[1]), u
retpins = [pin(th0 - pitch), pin(th0)]
def wneed(L, m):
    if clr_block(*Qof(L, 0), retpins) >= m: return 0.0
    w = 0.0
    while w < 400 and clr_block(*Qof(L, w), retpins) < m: w += 0.05
    return w
PL = PV["placa_leva"]; m = PL["margen_sincronia"]
for q in PL["perfil"][::40]:
    chk(f"  w_nec(L = {q['L']:.1f})", wneed(q["L"], m), q["w_nec"], tol=0, absol=0.06)
prf = PL["perfil"]
def wleva(L):                                    # canto de la leva interpolado linealmente entre los puntos exportados (tramos rectos o casi)
    for a, b in zip(prf, prf[1:]):
        if a["L"] <= L <= b["L"]: return a["w_leva"] + (b["w_leva"] - a["w_leva"]) * (L - a["L"]) / (b["L"] - a["L"])
    return prf[-1]["w_leva"]
Ls_ = [prf[0]["L"] + (PL["L_tope_rampa"] - prf[0]["L"]) * i / 3000 for i in range(3001)]
sync = min(clr_block(*Qof(L, wleva(L)), retpins) for L in Ls_)
chk("Sincronía: holgura mínima con Q contra la rampa (mm, barrido fino propio)", sync, PL["sincronia"], tol=0, absol=0.03)
if sync < m: fails.append("sincronía bajo el margen"); print("XX  sincronía bajo el margen")
Fret = math.pi / 4 * (P["D_bore"] ** 2 - P["d_rod"] ** 2) * P["p_ret"] / 10
NR = Fret / math.sin(math.radians(P["pv_alpha"]))
Fn_st = Fst * 1e3 * eta / kf
chk("Leva: atasco en la rampa F_ret/sen α (N)", NR, PL["fuerzas_N"]["rampa_atasco"]); chk("Leva: transversal a calado μ_s·F_n (N)", mu_s * Fn_st, PL["fuerzas_N"]["transversal_calado"])
Ncam = max(NR, mu_s * Fn_st)

print("== 5. Verificaciones del bloque, pasadores, ojal E y placa-leva (BTH-1 Cat. B, AISC J3) ==")
Nd, Fs, Fy = P["Nd"], Fst * 1e3, P["Fy"]
bu, hu = P["pv_bu"], P["pv_hu"]
chk("Bloque: F/(bh) + 6F(e_cr + e)/(hb²) (MPa)", Fs / (bu * hu) + 6 * Fs * (P["pv_ecr"] + P["e_dog"]) / (hu * bu * bu), row("Bloque-uña: compresión + flexión en el cuerpo acodado")["dem"])
zc0 = P["h_disc"] / 2 + P["t_base"]                              # interfaz acero–acero: δ = 0
tq = (hu - P["b_eye"] - 2 * P["g_ch"]) / 2
lq = (zc0 - P["b_eye"] / 2 - P["g_ch"] - tq / 2) - (P["t_base"] + P["pv_tcam"] / 2)
MQ = math.hypot(Fs / 2 * (tq / 2 + P["g_ch"] + P["b_eye"] / 4), Ncam * lq)
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
Ab = math.pi / 4 * P["pv_db"] ** 2
chk("Pernos de la placa-leva: (N/2)/A_b (MPa)", Ncam / 2 / Ab, row("Pernos de la placa-leva: corte")["dem"]); chk("  Fnv/Ω = 0,45·Fu/2", 0.45 * P["Fu_bolt"] / 2, row("Pernos de la placa-leva: corte")["cap"])
Es = P["E"] / (2 * (1 - P["nu"] ** 2))
chk("Placa-leva: Hertz extremo de Q–canto (MPa)", math.sqrt(Ncam / P["pv_tcam"] * Es / (math.pi * P["pv_dq"] / 2)), row("Placa-leva: contacto de Hertz")["dem"])
al = math.radians(P["pv_alpha"])
chk("Rampa sin autobloqueo: μ_E·d_E/(2L0)·(sen α + μ cos α)", P["pv_muE"] * P["pv_dE"] / (2 * L0) * (math.sin(al) + mu_c * math.cos(al)), row("Rampa de la placa-leva sin autobloqueo")["dem"])
est = [v for v in D["verificaciones"] if v["grp"] in ("Uña", "Articulaciones", "Soporte del ojal E", "Placas-leva") and v["fu"] is not None and v["estado"] not in ("info", "pend")]
print(f"    FU máximo en las filas nuevas del modo 2: {max(v['fu'] for v in est):.3f} ({len(est)} filas)")
GEO = ("Filete", "largo de la zapata", "distancia al borde")              # criterios geométricos (FU ≤ 1), no de resistencia
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
