"""Verificación independiente: plancha base bajo el soporte del cilindro y comparación con KIET; base de 20 mm con inserto de esquina (decisión del mandante 10-11-2026).

Revisor independiente. No lee packages/*.js. Parámetros: tests/golden/params_defaults.json; resultados del núcleo solo de la salida JSON de
`node tools/export_design.js [params.json]` (caja negra): filas de verificación, veredicto y geometría exportada del soporte y del inserto.

  §1 Estática global del accionamiento (base, mesa, cilindros): el cilindro es un miembro de dos fuerzas E–Q colineal; con dos cilindros
     en E₂ = −E₁ la suma de momentos sobre la base es un par puro en z (sin vuelco); el par local M = F·h de cada soporte debe viajar
     por la plancha hasta donde se equilibra (la mesa cargada cerca de Q o el otro soporte).
  §2 Réplica de la franja del núcleo SIN inserto (ins_on = 0: M_corte = M·(1 − a/s_H), b = w + a, σ = 6·M_corte/(b·t²)) frente a sus filas.
  §3 Criterio: ASME BTH-1-2020 Cat. B (Nd = 3,0). Plancha en flexión fuera de su plano (sección rectangular maciza en flexión respecto del eje
     menor): §3-2.3.4, F_b = 1,25·Fy/Nd (registro normativo 7030ee3; número de ecuación: verificar). Corte §3-2.3.6. Referencias: Cat. A y AISC F11.
  §3b Inserto de esquina (exportado): geometría propia desde los vértices (hipotenusa, catetos, rotación de 180°, CJP), holguras propias en planta a las
     placas-guía y al cubo de Q (posiciones exportadas) y en altura al cuerpo del cilindro (con el rebaje local), masa propia (sólido con biseles planos
     1:2,5 y rebaje integrado en grilla; 22-11-2026), pie de las orejas de la diagonal, mejillas de la ménsula y pasador E sobre el espesor pleno, J-I1, casos (F de las presiones y de los casos de fricción, M = F·h), 1,25·Fy/Nd, limitación de uso en el veredicto, estado global.
  §4 FEA propia de Mindlin (Q4, flexión 2×2, corte 1 punto) de la base completa: dos soportes rígidos (3 gdl maestros cada uno, M₂ = −M₁),
     losa unilateral (conjunto activo) y mesa CARGADA como cuerpo rígido (3 gdl) apoyado en la plancha por contacto unilateral en R ≤ D/2 con
     su peso (no un empotramiento: el borde de la mesa puede despegar); mesa vacía: su peso en el anillo. Tensión en la cara σ = 6m/t² (von Mises).
     Criterio (el de esta verificación): σ a más de 100 mm de la huella rígida del soporte (fuera de la singularidad de su esquina); el pico se
     informa aparte. Espesor del inserto desde los polígonos exportados (contorno, transición 1:2,5 hasta el espesor pleno, rebaje local).
     Casos: por defecto, interfaz B y modo guiado (ménsulas), con la mesa cargada (nominal, diseño, calado, atasco del retorno) y la mesa vacía en
     servicio; el FU de la FEA debe ser ≤ 1 y no superar el del núcleo (modelo calibrado conservador) en más del 2 %. Además: sin inserto y KIET.

Ejecutar: python3 -I tests/indep_plancha_base_E.py [--rapido]     (completo ≈ 6 min con 4 núcleos; --rapido omite la §4, ≈ 1 min)
Sale con 0 si todo coincide; 1 si hay diferencias; 2 sin node."""
import json, math, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = json.loads((ROOT / "tests" / "golden" / "params_defaults.json").read_text()); P["drive_mode"] = 2
if not shutil.which("node"):
    print("node no disponible"); sys.exit(2)


def export(over):
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "p.json"; f.write_text(json.dumps(over))
        return json.loads(subprocess.run(["node", str(ROOT / "tools" / "export_design.js"), str(f)], capture_output=True, text=True, check=True, cwd=str(ROOT)).stdout)


D = export({"drive_mode": 2}); D0 = export({"drive_mode": 2, "ins_on": 0}); DB = export({"drive_mode": 2, "opt_uhmw": 1})
DG = export({"drive_mode": 1}); DGB = export({"drive_mode": 1, "opt_uhmw": 1})
PV = D["pivotado"]; SE = PV["fabricacion"]["soporte_E"]; DV = D["derivados"]
fails = []


def chk(name, mine, tool, tol=1e-3, absol=1e-9):
    ok = abs(mine - tool) <= tol * abs(tool) + absol
    print(f"{'OK ' if ok else 'XX '} {name:70s} indep {mine:11.4f}  núcleo {tool:11.4f}")
    if not ok: fails.append(name)


def need(cond, name):
    print(("OK  " if cond else "XX  ") + name)
    if not cond: fails.append(name)


def rows(Dx, prefix):
    return [v for v in Dx["verificaciones"] if v["nombre"].startswith(prefix)]


Fy, Nd, t = P["Fy"], P["Nd"], P["t_base"]
A_p = math.pi / 4 * P["D_bore"] ** 2; A_a = A_p - math.pi / 4 * P["d_rod"] ** 2
F_cal = A_p * P["p_relief"] / 10 / 1e3          # kN (bar → MPa: /10)
F_ret = A_a * P["p_ret"] / 10 / 1e3
cas = {c["id"]: c for c in DV["casos"]}
F_nom, F_dis = cas["nom"]["F"], cas["dis"]["F"]
z_inf = [p for p in SE["piezas"] if p["id"] == "tapa_inf"][0]["z"]; z_sup = [p for p in SE["piezas"] if p["id"] == "tapa_sup"][0]["z"]
h = (sum(z_inf) / 2 + sum(z_sup) / 2) / 2 - t        # eje del cilindro sobre la cara superior de la base (resultante F/2 en cada tapa)
E1 = tuple(PV["E"]); O_loc = (-E1[0], -E1[1])
rects = [(min(x for x, _ in p["poligono_local"]), max(x for x, _ in p["poligono_local"]), min(y for _, y in p["poligono_local"]), max(y for _, y in p["poligono_local"]))
         for p in SE["piezas"] if p["id"].startswith(("pared", "munon"))]
cap125 = 1.25 * Fy / Nd

print("== §1 Estática global (dos cilindros en paralelo, E₂ = −E₁) ==")
print(f"    F: nominal {F_nom:.1f} kN (μ {cas['nom']['mu']}), diseño {F_dis:.1f} kN ({cas['dis']['p']:.0f} bar), calado {F_cal:.1f} kN ({P['p_relief']} bar); retorno {F_ret:.1f} kN")
print(f"    h = eje sobre la cara superior de la base = {h:.1f} mm (t_base = {t} mm); el roce mesa–base entra a z = t_base: el brazo que lleva la plancha es h")
psi_band = SE["ventana"]["sector_deg"]
for psi in (psi_band[0], psi_band[3]):
    u = (math.cos(math.radians(psi)), math.sin(math.radians(psi)))
    Fb1 = (-F_cal * u[0], -F_cal * u[1]); Fb2 = (-Fb1[0], -Fb1[1])
    M1 = (-h * Fb1[1] / 1e3, h * Fb1[0] / 1e3); M2 = (-M1[0], -M1[1])
    Mz = (E1[0] * Fb1[1] - E1[1] * Fb1[0] + (-E1[0]) * Fb2[1] - (-E1[1]) * Fb2[0]) / 1e3
    print(f"    ψ = {psi:6.2f}°: ΣF = ({Fb1[0] + Fb2[0]:.1e}; {Fb1[1] + Fb2[1]:.1e}) kN; ΣM_horiz = ({M1[0] + M2[0]:.1e}; {M1[1] + M2[1]:.1e}); "
          f"M local = {math.hypot(*M1):.2f} kN·m por soporte; par en z de los cilindros = {Mz:.1f} kN·m (lo toma el roce)")
need(abs(h - (DV["hax"])) < 1e-6, f"h = altura del eje sobre la base = h_disc/2 + Δ_interfaz ({h:.1f} mm)")

print("== §2 Réplica de la franja del núcleo SIN inserto (ins_on = 0) frente a sus filas ==")
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
r0 = {k: rows(D0, "Plancha base bajo el soporte del ojal E: " + k)[0] for k in ("flexión sin anclaje, empuje", "flexión sin anclaje, retorno", "corte")}
chk("Franja, empuje a calado: σ (MPa)", sE["s"], r0["flexión sin anclaje, empuje"]["dem"])
chk("Franja, retorno (atasco): σ (MPa)", sR["s"], r0["flexión sin anclaje, retorno"]["dem"])
chk("Franja: F_b = 1,25·Fy/Nd (MPa)", cap125, r0["flexión sin anclaje, empuje"]["cap"])
chk("Franja, corte τ = 1,5·(M/a)/(b·t) (MPa)", 1.5 * sE["M"] / sE["a"] / (sE["b"] * t), r0["corte"]["dem"])
need(r0["flexión sin anclaje, empuje"]["estado"] == "pend" and D0["verdict"]["estado_global"] == "NO CUMPLE / PENDIENTE DE DECISIÓN", "sin inserto: la franja queda «pend» y el estado global pendiente")

print("== §3 Criterio de la flexión de la plancha (misma σ de la franja) ==")
caps = [("Fy/Nd, Nd = 3 (criterio anterior del núcleo)", Fy / Nd), ("1,25·Fy/Nd, Nd = 3 (BTH-1-2020 §3-2.3.4, eje menor)", cap125),
        ("1,25·Fy/Nd, Nd = 2 (Cat. A, solo referencia)", 1.25 * Fy / 2), ("AISC 360-22 F11: 1,5·Fy/1,67 (ASD, referencia)", 1.5 * Fy / 1.67)]
for nm, cp in caps:
    print(f"    {nm:52s} cap {cp:6.1f} MPa   franja empuje FU {sE['s'] / cp:5.2f}   retorno FU {sR['s'] / cp:5.2f}")

# ---------------------------------------------------------------- §3b Inserto exportado --------------------------------------------------
print("== §3b Inserto de esquina exportado (geometría, holguras, masa, casos y estado global) ==")
try:
    from shapely.geometry import Polygon, Point, LineString
    from shapely.ops import unary_union
except ImportError:
    Polygon = None
RHO = 7.85e-6


def ins_check(Dx, I, label, mode, nexp):
    """Refuerzo cuadrado soldado sobre la base (doubler, 12-11-2026): geometría propia desde los vértices, holguras, tapones (AISC 360-22 §J2.3), corte rasante
    propio (V = F_cal + M·6·t_d·t_b/t³ frente a tapones + filetes + PJP), masa propia, pie de las orejas, mejillas y pasador E sobre el refuerzo, casos y estado."""
    Px = Dx["P"]; Bh = Px["B"] / 2; tb = Px["t_base"]; Fyx, Ndx = Px["Fy"], Px["Nd"]; DVx = Dx["derivados"]; Fw = 0.60 * Px["FEXX"] / (1.20 * Ndx)
    need(I is not None and I["estado"] == "cumple", f"{label}: refuerzo exportado y cumple")
    if I is None: return None
    td = I["t_d"]; a = I["lado"]
    need(I["t"] == tb + td and I["z"] == [tb, I["t"]], f"{label}: refuerzo de {td} mm SOBRE la base (z = [{tb}; {I['t']}]); la base queda al ras sobre la losa")
    need(len(I["esquinas"]) == nexp, f"{label}: {nexp} refuerzos")
    for k, pl in enumerate(I["esquinas"]):
        xs = [p[0] for p in pl]; ys = [p[1] for p in pl]
        need(len(pl) == 4 and abs(max(xs) - min(xs) - a) < 1e-6 and abs(max(ys) - min(ys) - a) < 1e-6 and abs(max(abs(x) for x in xs) - Bh) < 1e-6 and abs(max(abs(y) for y in ys) - Bh) < 1e-6,
             f"{label}: esquina {k + 1}: cuadrado de {a:.0f} mm con un lado sobre cada borde de la base")
    C1 = I["esquinas"][0]
    need(all(abs(p[0] + q[0]) < 1e-9 and abs(p[1] + q[1]) < 1e-9 for p, q in zip(C1, I["esquinas"][1])), f"{label}: el segundo refuerzo es la rotación de 180°")
    need(not any(k in I for k in ("transicion", "rebaje", "muescas")) and not any(j["id"] == "J-I1" for j in I["juntas"]), f"{label}: sin transición, rebaje, muescas ni CJP J-I1")
    # holgura a la mesa: esquina interior del cuadrado
    sx = 1 if sum(x for x, _ in C1) > 0 else -1; sy = 1 if sum(y for _, y in C1) > 0 else -1
    dm = math.hypot(Bh - a, Bh - a) - Px["D_top"] / 2
    chk(f"{label}: holgura de la esquina interior a la mesa (mm)", dm, I["holgura_mesa"]); need(dm >= 5, f"{label}: esquina fuera de la mesa con ≥ 5 mm ({dm:.1f})")
    # tapones (AISC §J2.3)
    T = I["tapones"]; fill = td if td <= 16 else max(td / 2, 16)
    need(T["d"] >= td + 8 and T["d"] <= max(td + 11, 2.25 * fill) and abs(T["profundidad_relleno"] - fill) < 1e-9, f"{label}: tapón Ø{T['d']} (≥ t + 8 = {td + 8}), relleno {fill:.1f} (§J2.3a/b)")
    ok_sp = all(math.hypot(p[0] - q[0], p[1] - q[1]) >= 4 * T["d"] - 1e-6 for ps in T["posiciones"] for i, p in enumerate(ps) for q in ps[i + 1:])
    need(ok_sp, f"{label}: separación entre tapones ≥ 4·Ø = {4 * T['d']} mm")
    # corte rasante propio
    cs = {c["id"]: c for c in I["casos"]}; Fc = A_p * Px["p_relief"] / 10 / 1e3; h_ = cs["cal"]["h"]; M_ = Fc * h_ / 1e3
    V_ = Fc + M_ * 1e6 * 6 * td * tb / I["t"] ** 3 / 1e3
    cap_ = (T["n_por_esquina"] * math.pi / 4 * T["d"] ** 2 + 2 * a * 0.707 * I["filetes"]["bordes_interiores"]["tamano"] + 2 * a * (I["filetes"]["bordes_exteriores_PJP"]["S"] - 3)) * Fw / 1e3
    chk(f"{label}: corte rasante V = F + M·6·t_d·t_b/t³ (kN)", V_, I["corte_rasante"]["V_kN"]); chk(f"{label}: capacidad tapones + filetes + PJP (kN)", cap_, I["corte_rasante"]["capacidad_kN"])
    need(V_ / cap_ <= 1, f"{label}: unión base–refuerzo FU {V_ / cap_:.3f} ≤ 1")
    # masa propia
    m_ = RHO * (a * a * td - T["n_por_esquina"] * math.pi / 4 * T["d"] ** 2 * (td - fill))
    At = I.get("atiesadores")
    if At: m_ += RHO * At["t"] * At["h"] * At["largo"]
    chk(f"{label}: masa por esquina (kg)", m_, I["masa"]); chk(f"{label}: masa de los refuerzos en la masa total (kg)", I["n"] * I["masa"], DVx["masas"]["insertos"])
    if At:
        dmin = min(math.hypot(x, y) for r in At["por_esquina"] for x, y in r["poligono"]) - Px["D_top"] / 2
        need(dmin >= 5 - 1e-6 and At["fu"] <= 1 and At["fu_soldadura"] <= 1, f"{label}: atiesador tangencial {At['t']}×{At['h']}×{At['largo']} fuera de la mesa ({dmin:.1f} mm), FU {At['fu']:.2f}")
    if Polygon:
        sqs = [Polygon(pl) for pl in I["esquinas"]]
        yl = Bh - Px["c_lug"]; hwe = Px["t_ear"] / 2 + Px["w_ear"]; nOn = 0
        for cx_, cy_ in ((Px["x_lug"], yl), (-Px["x_lug"], yl), (Px["x_lug"], -yl), (-Px["x_lug"], -yl)):
            r_ = math.hypot(cx_, cy_); ux, uy = cx_ / r_, cy_ / r_
            foot = Polygon([(cx_ + a_ * Px["R_ear"] * ux - k * hwe * uy, cy_ + a_ * Px["R_ear"] * uy + k * hwe * ux) for a_, k in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            for sq in sqs:
                if not sq.contains(Point(cx_, cy_)): continue
                nOn += 1; mg = sq.exterior.distance(foot) if sq.contains(foot) else -1
                need(mg >= 5 - 1e-6, f"{label}: pie de la oreja en ({cx_:.0f}; {cy_:.0f}) sobre el refuerzo con {mg:.1f} mm (≥ 5)")
        need(nOn >= 2, f"{label}: orejas de la diagonal sobre el refuerzo ({nOn})")
        if mode == 1:
            Mx = Dx["levaGuiada"]["fabricacion"]["mensula"]
            for h2 in Mx["huellas"]:
                hp = Polygon(h2["poly"]); sq = next(s for s in sqs if s.intersects(hp)); mg = sq.exterior.distance(hp) if sq.contains(hp) else -1
                need(mg >= 5 - 1e-6, f"{label}: {h2['id']} de la ménsula {h2['mensula']} sobre el refuerzo con {mg:.1f} mm (≥ 5)")
        else:
            pe = Dx["pivotado"]["fabricacion"]["pasador_E"]
            need(pe["z"][0] - I["t"] >= 5 - 1e-9, f"{label}: pasador E de z {pe['z'][0]:.0f} sobre la cara del refuerzo ({I['t']}) con {pe['z'][0] - I['t']:.0f} mm")
            FB = Dx["pivotado"]["fabricacion"]; Rc = FB["bloque_una"]["horquilla"]["R_cubo"]
            obs = [Polygon(FB["placas_leva"]["instancias"][k]["contorno"]) for k in ("1_antihorario", "1_horario")]
            obs += [Point(q).buffer(Rc, 32) for k in ("1_antihorario", "1_horario") for q in Dx["pivotado"]["posiciones"][k]["Q"]]
            dpl = min(o.distance(sqs[0]) for o in obs) - I["filetes"]["bordes_interiores"]["tamano"]
            print(f"    {label}: holgura en planta (con el filete) a placas-guía y cubo de Q (propia) {dpl:.1f} mm; núcleo {I['holguras']['planta']:.1f} mm")
            need(dpl >= 5 - 0.5, f"{label}: holgura en planta ≥ 5 mm")
        zc = DVx["hax"] + tb; zb = zc - Px["D_body"] / 2
        print(f"    {label}: cuerpo del cilindro a z = {zb:.1f} sobre la cara del refuerzo a {I['t']} (sin rebaje): {zb - I['t']:.1f} mm; núcleo {I['holguras']['vertical']:.1f} mm")
        need(I["holguras"]["vertical"] >= 5 - 1e-9 and zb - I["t"] >= 5 - 1e-9, f"{label}: holgura vertical ≥ 5 mm")
    # casos: F, M = F·h, 1,25·Fy/Nd, linealidad
    cx = {c["id"]: c for c in DVx["casos"]}
    Fr = A_a * Px["p_ret"] / 10 / 1e3
    chk(f"{label}: F a calado (kN)", Fc, cs["cal"]["F_kN"]); chk(f"{label}: F del atasco del retorno (kN)", Fr, cs["ret"]["F_kN"])
    chk(f"{label}: F nominal = caso nominal (kN)", cx["nom"]["F"], cs["nom"]["F_kN"]); chk(f"{label}: F de diseño (kN)", cx["dis"]["F"], cs["dis"]["F_kN"])
    Wd = (DVx["masas"]["disc"] + DVx["masas"]["ssTop"] + 0.5 * DVx["masas"]["pivot"]) * 9.80665 / 1e3
    Fv = Px["ins_fsv"] * max(cx["dis"]["F"], cx["borde"]["F"], cx["cont"]["F"]) * Wd / DVx["N"]
    chk(f"{label}: F de servicio con la mesa vacía (kN)", Fv, cs["vac"]["F_kN"], tol=5e-3)
    for k in cs: chk(f"{label}: M = F·h, caso {k} (kN·m)", cs[k]["F_kN"] * DVx["hax"] / 1e3, cs[k]["M_kNm"])
    chk(f"{label}: F_b = 1,25·Fy/Nd (MPa)", 1.25 * Fyx / Ndx, I["Fb"])
    need(abs(cs["nom"]["fu"] / cs["cal"]["fu"] - cs["nom"]["F_kN"] / cs["cal"]["F_kN"]) < 1e-9, f"{label}: σ proporcional a F con la mesa cargada")
    R_ = [v for v in Dx["verificaciones"] if "con refuerzo de" in v["nombre"] and "flexión" in v["nombre"]]
    need(len(R_) == 5 and all(v["fu"] <= 1 and v["estado"] in ("ok", "warn") and "§3-2.3.4" in v["ref"] for v in R_), f"{label}: 5 filas de flexión con FU ≤ 1 y BTH-1-2020 §3-2.3.4")
    VD = Dx["verdict"]
    need(VD["estado_global"] == "CUMPLE" and not VD["pendientes_criticos"], f"{label}: estado global CUMPLE sin pendientes críticos")
    need(any("presión de alivio con la mesa sin carga" in l["texto"] and "detener y liberar" in l["texto"] for l in VD["limitaciones_uso"]), f"{label}: limitación de uso en el veredicto")
    print(f"    {label}: cuadrado {a:.0f} × {a:.0f} × {td} mm (cara a z {I['t']}), {T['n_por_esquina']} tapones Ø{T['d']}, atiesador {'h ' + str(At['h']) if At else 'no'}, "
          f"masa {I['masa']:.1f} kg × {I['n']}; FU núcleo: " + ", ".join(f"{k} {cs[k]['fu']:.3f}" for k in cs) + f"; corte rasante {V_ / cap_:.3f}")
    return I


IN = {"por defecto": (D, SE["refuerzo"], 2, 2), "interfaz B": (DB, DB["pivotado"]["fabricacion"]["soporte_E"]["refuerzo"], 2, 2),
      "guiado": (DG, DG["levaGuiada"]["fabricacion"]["refuerzo"], 1, round(DG["P"]["n_br"])), "guiado B": (DGB, DGB["levaGuiada"]["fabricacion"]["refuerzo"], 1, round(DGB["P"]["n_br"]))}
for lb, (Dx, I, md, nx) in IN.items(): ins_check(Dx, I, lb, md, nx)
# interfaces A (inserto de 90 con rebaje y chaflán en las muescas) y A en el modo guiado: solo §3b (geometría, masa, asientos), no entran a la FEA
DA = export({"drive_mode": 2, "opt_ss": 1}); DGA = export({"drive_mode": 1, "opt_ss": 1})
ins_check(DA, DA["pivotado"]["fabricacion"]["soporte_E"]["refuerzo"], "interfaz A", 2, 2)
ins_check(DGA, DGA["levaGuiada"]["fabricacion"]["refuerzo"], "guiado A", 1, round(DGA["P"]["n_br"]))
need(IN["interfaz B"][1]["t"] > IN["por defecto"][1]["t"], "la interfaz B (eje más alto) pide un refuerzo más grueso")
p0 = D0["P"]; need(p0["t_base"] == 20, "base de 20 mm por defecto")

if "--rapido" in sys.argv:
    print("\nRESULTADO:", "sin diferencias" if not fails else "DIFERENCIAS: " + "; ".join(fails)); sys.exit(1 if fails else 0)

# ---------------------------------------------------------------- §4 FEA propia ------------------------------------------------------
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
from matplotlib.path import Path
from multiprocessing import Pool
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


def solve(Kt, fr, nt):
    """Complemento de Schur de los nt gdl de la mesa rígida (densos): la placa se factoriza sola."""
    Kt = Kt.tocsr(); n = Kt.shape[0]
    if nt == 0: return spl.splu(Kt.tocsc(), permc_spec="COLAMD").solve(fr)
    A = Kt[:n - nt, :n - nt].tocsc(); b = Kt[:n - nt, n - nt:].toarray(); c = Kt[n - nt:, n - nt:].toarray()
    lu = spl.splu(A, permc_spec="COLAMD"); Y = lu.solve(b); x0 = lu.solve(fr[:n - nt])
    xt = np.linalg.solve(c - b.T @ Y, fr[n - nt:] - b.T @ x0)
    return np.concatenate([x0 - Y @ xt, xt])


def fea(Bs, hm, tvec, supports, W_tab, R_tab, table="body", Ri=140.0, kslab=100.0, ktab=100.0):
    """supports: [(mask(X,Y) vectorizada, (xc,yc), (Mx,My) N·mm, W N)]; table: 'body' (mesa cargada, cuerpo rígido con contacto unilateral) o
    'weight' (mesa vacía: W_tab uniforme en Ri…R_tab). Devuelve (w, S[xc, yc, σvm, mx, my, mxy, t], convergió)."""
    n = int(round(Bs / hm)); xs = np.linspace(-Bs / 2, Bs / 2, n + 1); X, Y = [a.ravel() for a in np.meshgrid(xs, xs, indexing="ij")]
    nn = X.size; ndof = 3 * nn; I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij"); I = I.ravel(); J = J.ravel()
    els = np.stack([I * (n + 1) + J, (I + 1) * (n + 1) + J, (I + 1) * (n + 1) + J + 1, I * (n + 1) + J + 1], 1)
    te = tvec(X[els].mean(1), Y[els].mean(1)); Kb, Ks, dxc, dyc = unit_K(hm)
    dof = (3 * els[:, :, None] + np.arange(3)).reshape(-1, 12)
    vals = (te[:, None, None] ** 3 * Kb + te[:, None, None] * Ks).reshape(-1)
    K = sp.csr_matrix((vals, (np.repeat(dof, 12, 1).ravel(), np.tile(dof, (1, 12)).ravel())), shape=(ndof, ndof))
    Ar = np.full(nn, hm * hm); ed = (np.abs(X) > Bs / 2 - 1e-6) | (np.abs(Y) > Bs / 2 - 1e-6); co = (np.abs(X) > Bs / 2 - 1e-6) & (np.abs(Y) > Bs / 2 - 1e-6)
    Ar[ed] /= 2; Ar[co] /= 2
    fv = np.zeros(ndof); fv[0::3] -= 7.7e-5 * tvec(X, Y) * Ar                                        # peso propio
    if table == "weight":
        ring = (X ** 2 + Y ** 2 <= R_tab ** 2) & (X ** 2 + Y ** 2 >= Ri ** 2); fv[0::3][ring] -= W_tab * Ar[ring] / Ar[ring].sum()
    slave = -np.ones(nn, int)
    for k, (m, _, _, _) in enumerate(supports): slave[m(X, Y)] = k
    fr_n = np.where(slave < 0)[0]; base = 3 * fr_n.size; it0 = base + 3 * len(supports); nt = 3 if table == "body" else 0; nred = it0 + nt
    r_ = np.concatenate([3 * fr_n, 3 * fr_n + 1, 3 * fr_n + 2]).tolist(); c_ = np.concatenate([3 * np.arange(fr_n.size) + d for d in range(3)]).tolist(); v_ = [1.0] * len(r_)
    for nd in np.where(slave >= 0)[0]:
        k = slave[nd]; xc, yc = supports[k][1]; m0 = base + 3 * k
        r_ += [3 * nd] * 3 + [3 * nd + 1, 3 * nd + 2]; c_ += [m0, m0 + 1, m0 + 2, m0 + 1, m0 + 2]; v_ += [1.0, -(X[nd] - xc), -(Y[nd] - yc), 1.0, 1.0]
    T = sp.csr_matrix((v_, (r_, c_)), shape=(ndof, nred)); fr = T.T @ fv
    for k, (_, _, (Mx, My), W) in enumerate(supports):
        m0 = base + 3 * k; fr[m0 + 1] += My; fr[m0 + 2] -= Mx; fr[m0] -= W                 # trabajo: My·βx − Mx·βy (u = z·βx, v = z·βy)
    Kr = (T.T @ K @ T).tocsr(); wmap = T[0::3, :].tocsr(); ks = kslab * Ar; kt = ktab * Ar
    if nt:
        fr[it0] -= W_tab
        rows_ = np.where(X ** 2 + Y ** 2 <= R_tab ** 2)[0]; m_ = rows_.size
        Tt = sp.csr_matrix((np.concatenate([np.ones(m_), -X[rows_], -Y[rows_]]), (np.tile(np.arange(m_), 3), np.repeat([it0, it0 + 1, it0 + 2], m_))), shape=(m_, nred))
        Dm = (wmap[rows_] - Tt).tocsr()                                                                  # w_plancha − w_mesa en la huella
    else:
        rows_ = np.zeros(0, int); m_ = 0; Dm = None
    act_s = np.ones(nn, bool); act_t = np.ones(m_, bool); conv = False
    for it in range(300):
        Kt = Kr + wmap.T @ sp.diags(ks * act_s) @ wmap
        if m_: Kt = Kt + Dm.T @ sp.diags(kt[rows_] * act_t) @ Dm
        ur = solve(Kt, fr, nt); u = T @ ur; w = u[0::3]; g = Dm @ ur if m_ else np.zeros(0)
        ns = w <= 0; ntt = g >= 0; cs_ = np.where(ns != act_s)[0]; ct = np.where(ntt != act_t)[0]
        if cs_.size + ct.size == 0: conv = True; break
        if it > 40:   # evita ciclos: cambia el 20 % peor
            sel = cs_[np.argsort(-np.abs(w[cs_]))][: max(1, cs_.size // 5)]; act_s[sel] = ns[sel]
            if ct.size: sel = ct[np.argsort(-np.abs(g[ct]))][: max(1, ct.size // 5)]; act_t[sel] = ntt[sel]
        else:
            act_s, act_t = ns, ntt
    bx = u[1::3][els]; by = u[2::3][els]
    kap = np.stack([bx @ dxc, by @ dyc, bx @ dyc + by @ dxc], 1)
    Db1 = Es / (12 * (1 - nu ** 2)) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])
    m = (kap @ Db1.T) * te[:, None] ** 3; s = 6 * m / te[:, None] ** 2
    vm = np.sqrt(s[:, 0] ** 2 - s[:, 0] * s[:, 1] + s[:, 1] ** 2 + 3 * s[:, 2] ** 2)
    return w, np.column_stack([X[els].mean(1), Y[els].mean(1), vm, m, te]), conv


def tvec_of(I, tb, Bh):
    """Espesor desde el refuerzo exportado (12-11-2026): t_base fuera; t_base + t_d dentro del cuadrado (sección compuesta); atiesador tangencial como franja
    de 60 mm con el espesor equivalente de la T (base 60 × t_base + atiesador t × h)."""
    if I is None: return lambda x, y: np.full(np.shape(x), float(tb))
    paths = [Path(np.array(p, float)) for p in I["esquinas"]]; At = I.get("atiesadores")
    if At:
        w = 60.0; A1 = w * tb; A2 = At["t"] * At["h"]; y1 = tb / 2; y2 = tb + At["h"] / 2; yb = (A1 * y1 + A2 * y2) / (A1 + A2)
        Iq = w * tb ** 3 / 12 + A1 * (y1 - yb) ** 2 + At["t"] * At["h"] ** 3 / 12 + A2 * (y2 - yb) ** 2; teq = (12 * Iq / w) ** (1 / 3)
        axes = [np.array(r["eje"], float) for r in At["por_esquina"]]
    def f(x, y):
        pts = np.column_stack([np.ravel(x), np.ravel(y)]); t_ = np.full(pts.shape[0], float(tb))
        for pa in paths: t_[pa.contains_points(pts, radius=1e-6)] = float(I["t"])
        if At:
            for a_, b_ in axes:
                ab = b_ - a_; tt = ((pts - a_) @ ab) / (ab @ ab); d = np.hypot(*(pts - (a_ + np.clip(tt, 0, 1)[:, None] * ab)).T)
                m = (d <= w / 2) & (tt >= 0) & (tt <= 1) & (t_ < teq); t_[m] = teq
        return t_.reshape(np.shape(x))
    return f


def caso(F_kN, u, E, rects_, h_, Bs, tvec, W_tab, R_tab, sense=-1, table="body", hm=40.0):
    def mask(sg):
        def f(x, y):
            ok = np.zeros(x.shape, bool)
            for x0, x1, y0, y1 in rects_:
                ok |= (x0 - 1 <= sg * x - E[0]) & (sg * x - E[0] <= x1 + 1) & (y0 - 1 <= sg * y - E[1]) & (sg * y - E[1] <= y1 + 1)
            return ok
        return f
    def dist(x, y):
        d = np.full(x.shape, 1e9)
        for sg in (1, -1):
            Xr = sg * x - E[0]; Yr = sg * y - E[1]
            for x0, x1, y0, y1 in rects_:
                d = np.minimum(d, np.hypot(np.maximum.reduce([x0 - Xr, np.zeros_like(Xr), Xr - x1]), np.maximum.reduce([y0 - Yr, np.zeros_like(Yr), Yr - y1])))
        return d
    Fb = (sense * F_kN * 1e3 * u[0], sense * F_kN * 1e3 * u[1]); M1 = (-h_ * Fb[1], h_ * Fb[0])
    sups = [(mask(1), E, M1, 470.0), (mask(-1), (-E[0], -E[1]), (-M1[0], -M1[1]), 470.0)]
    w, S, conv = fea(Bs, hm, tvec, sups, W_tab, R_tab, table=table)
    d = dist(S[:, 0], S[:, 1]); far = d > 100
    j = int(np.argmax(np.where(far, S[:, 2], -1)))
    return dict(M=math.hypot(*M1) / 1e6, pico=float(S[:, 2].max()), lejos=float(S[far, 2].max()), donde=(float(S[j, 0]), float(S[j, 1]), float(S[j, 6])), w=float(w.max()), conv=conv)


def geom(Dx, mode):
    """Soporte (rectángulos en el marco del ojal), ojal E1, dirección del empuje u y h."""
    Px = Dx["P"]; DVx = Dx["derivados"]
    if mode == 2:
        SEx = Dx["pivotado"]["fabricacion"]["soporte_E"]
        rc = [(min(x for x, _ in p["poligono_local"]), max(x for x, _ in p["poligono_local"]), min(y for _, y in p["poligono_local"]), max(y for _, y in p["poligono_local"])) for p in SEx["piezas"] if p["id"].startswith(("pared", "munon"))]
        ps = SEx["ventana"]["sector_deg"][0]; return rc, tuple(Dx["pivotado"]["E"]), (math.cos(math.radians(ps)), math.sin(math.radians(ps)))
    BR = DVx["bracket"]; x0 = BR["Win"] / 2; x1 = x0 + Px["t_ch"]; y0, y1 = Dx["levaGuiada"]["fabricacion"]["mensula"]["y_mejillas"]   # 22-11-2026: mejillas corridas sobre el espesor pleno
    yE = -Px["R_pin"] * math.sin(math.pi / Px["N_pin"]) - Px["l_p"] - Px["s_free"] - Px["L0"]
    return [(x0, x1, y0, y1), (-x1, -x0, y0, y1)], (Px["x_g"], yE), (0.0, 1.0)


def job(a):
    lb, kind = a; Dx, I, mode, _ = IN[lb] if lb in IN else (D0, None, 2, 2)
    Px = Dx["P"]; rc, E_, u_ = geom(Dx, mode); tv = tvec_of(I, Px["t_base"], Px["B"] / 2); N_ = Dx["derivados"]["N"] * 1e3; hx = Dx["derivados"]["hax"]
    cx = {c["id"]: c for c in (I["casos"] if I else [])}
    if kind in ("nom", "dis", "cal"): r = caso(cx[kind]["F_kN"] if I else F_cal, u_, E_, rc, hx, Px["B"], tv, N_, Px["D_top"] / 2)
    elif kind == "ret": r = caso(cx["ret"]["F_kN"], u_, E_, rc, hx, Px["B"], tv, N_, Px["D_top"] / 2, sense=1)
    else:
        Wd = (Dx["derivados"]["masas"]["disc"] + Dx["derivados"]["masas"]["ssTop"] + 0.5 * Dx["derivados"]["masas"]["pivot"]) * 9.80665
        r = caso(cx["vac"]["F_kN"], u_, E_, rc, hx, Px["B"], tv, Wd, Px["D_top"] / 2, table="weight")
    r.update(lb=lb, kind=kind, fu_core=cx[kind]["fu"] if I else None); return r


print("== §4 FEA propia (malla 40 mm; mesa cargada como cuerpo rígido con contacto unilateral; σ a más de 100 mm de la huella rígida del soporte) ==")
print(f"    {'modelo':14s} {'caso':5s} {'M kN·m':>7s} {'σ pico':>7s} {'σ >100mm':>8s} {'FU FEA':>7s} {'FU núcleo':>9s} {'w máx':>7s}  dónde (x, y, t)")
JOBS = [(lb, k) for lb in IN for k in ("nom", "dis", "cal", "ret", "vac")] + [("sin inserto", "cal")]
with Pool(4) as pool:
    RES = pool.map(job, JOBS)
for r in RES:
    fu = r["lejos"] / cap125
    print(f"    {r['lb']:14s} {r['kind']:5s} {r['M']:7.2f} {r['pico']:7.0f} {r['lejos']:8.1f} {fu:7.3f} {('%9.3f' % r['fu_core']) if r['fu_core'] is not None else '        —'} {r['w']:7.2f}  "
          f"({r['donde'][0]:.0f}; {r['donde'][1]:.0f}; {r['donde'][2]:.0f}){'' if r['conv'] else '  (sin convergencia)'}")
    if r["fu_core"] is not None:
        if not r["conv"]: fails.append(f"FEA sin convergencia: {r['lb']} {r['kind']}")
        if fu > 1: fails.append(f"FEA: {r['lb']} {r['kind']} FU {fu:.3f} > 1")
        if fu > r["fu_core"] * 1.02 + 0.005: fails.append(f"FEA: {r['lb']} {r['kind']} FU {fu:.3f} > núcleo {r['fu_core']:.3f} (el modelo calibrado no es conservador)")
r0f = [r for r in RES if r["lb"] == "sin inserto"][0]
if r0f["lejos"] <= cap125: fails.append("FEA: la plancha de 20 mm sin inserto debería exceder 1,25·Fy/Nd a calado con la mesa cargada")
print(f"    sin inserto (base de {t} mm) a calado: FU {r0f['lejos'] / cap125:.2f} > 1: el inserto hace falta")
# KIET (plano vectorial KIET-1024-REF-TT-400T, escala 1:15): base 2200 × 20; esquinas de los cilindros con plancha de ≈ 20 mm sobre la base
# (z 20 → 40) en el triángulo |x − y| ≥ 1600 (catetos 590 mm); ojal en (∓982; ±990), eje a z ≈ 106 mm del piso (86 mm sobre la base);
# cilindro casi paralelo al borde (u ≈ (−0,992; 0,128) para el ojal (982; −990)); pedestal del ojal ≈ 140 × 140; mesa Ø2000.
uK = (-0.992, 0.128); nK = math.hypot(*uK); uK = (uK[0] / nK, uK[1] / nK)
for nm, tf in (("KIET medido: 20 + 20 en la esquina", lambda x, y: np.where(np.abs(x - y) >= 1600, 40.0, 20.0)), ("KIET sin la plancha de esquina (20)", lambda x, y: np.full(np.shape(x), 20.0))):
    r = caso(F_cal, uK, (982.0, -990.0), [(-70, 70, -70, 70)], 86.0, 2200.0, tf, DV["N"] * 1e3, 1000.0)
    print(f"    {nm:44s} M {r['M']:.2f} kN·m, σ pico {r['pico']:.0f}, σ > 100 mm {r['lejos']:.0f} MPa (FU {r['lejos'] / cap125:.2f}), w {r['w']:.2f} mm")
print("\nRESULTADO:", "sin diferencias" if not fails else "DIFERENCIAS: " + "; ".join(fails))
sys.exit(1 if fails else 0)
