"""Láminas de fabricación del accionamiento según el modo del núcleo.
Modo 2 (pivotado tipo KIET, por defecto): soporte abierto del ojal E (BAS-012…015), cilindro (ACC-013), pasadores E y Q (ACC-014), bloque-uña con garra (ACC-027; ACC-023 con cara R120 anulado), placa-guía (ACC-020/024).
Modo 1 (guiado, alternativa): riel-leva (ACC-007), pórtico y prolongación de la bancada (ACC-008), seguidor (ACC-011).
Toda la geometría viene del JSON del núcleo (D.pivotado.fabricacion, D.levaGuiada.fabricacion) a través del modelo 3D."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *
from pie_a import ra, wd
from soldadura_det import add_prep
import contorno


def loc1(ctx, key, nk, idx=0, rot=None, z0=None):
    """Copia local de un sólido de la pieza: centrado en planta, eje largo sobre x (rot en grados; None = automático)."""
    sols = ctx.shapes[key].Solids()
    so = sols[idx]
    c = so.Center()
    bb = so.BoundingBox()
    if rot is None:
        rot = 0.0 if bb.xlen >= bb.ylen else -90.0
    sh = so.translate(cq.Vector(-c.x, -c.y, 0)).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rot)
    ctx.shapes[nk] = cq.Compound.makeCompound([sh])
    ctx.mat[nk] = ctx.mat.get(key, "acero")
    return nk


# ====================================================================================================== MODO 2
def soporte_ids(ctx, piezas=None):
    """Juntas del soporte del ojal E (registro de soldaduras, una por junta del núcleo); piezas: filtra por id de pieza del núcleo."""
    return [w["id"] for w in ctx.welds if w.get("soporte_E") is not None and (piezas is None or all(x in w["soporte_E"]["piezas"] for x in piezas))]


@pieza("cajon_pared_x", "cajon_pared_y", "cajon_munon", "cajon_tapa")
def sheet_cajon_piezas(ctx):
    """Piezas del soporte abierto del ojal E (núcleo: pivotado.fabricacion.soporte_E.piezas): paredes traseras X e Y, muñones y tapas recortadas en nariz.
    Medidas de cada pieza desde su polígono local (origen en E); juntas y secuencia en CON-007."""
    g, P = ctx.g, ctx.P
    S = g.FPV["soporte_E"]
    tap = S["tapas"]
    loc = {pz["id"]: pz for pz in S["piezas"]}
    ks = ["cajon_pared_x", "cajon_pared_y", "cajon_munon", "cajon_tapa"]
    loc1(ctx, "cajon_pared_x", "cpx_L")
    loc1(ctx, "cajon_pared_y", "cpy_L")
    loc1(ctx, "cajon_munon", "cmu_L")
    loc1(ctx, "cajon_tapa", "ct_L", idx=0, rot=0.0)
    p = Pieza(ctx, ks, "SOPORTE DEL OJAL E (ABIERTO): PAREDES TRASERAS, MUÑONES Y TAPAS (PIEZAS, MODO PIVOTADO)", fmt="auto")
    s = p.s
    p.iso_keys = ["ct_L"]
    ids = soporte_ids(ctx)
    sc = lambda k_: ctx.code(k_).replace(CODE + "-", "")

    def dims(pid):
        pz = loc[pid]
        xs, ys = [q[0] for q in pz["poligono_local"]], [q[1] for q in pz["poligono_local"]]
        a, b = max(xs) - min(xs), max(ys) - min(ys)
        return max(a, b), min(a, b), pz["z"][1] - pz["z"][0]
    tol = lambda *v: {round(x, 1): " ±0,5" for x in v}
    for key_, lk_, pid_, nm_ in (("cajon_pared_x", "cpx_L", "pared_X", "PARED TRASERA X"), ("cajon_pared_y", "cpy_L", "pared_Y", "PARED TRASERA Y"), ("cajon_munon", "cmu_L", "munon_X", "MUÑÓN DELANTERO")):
        L_, t_, h_ = dims(pid_)
        p.vs(lk_ + "_el", [lk_], "front", lv=(1, 2, 1, 1), title=f"{sc(key_).rsplit('-', 1)[0]} {nm_} ({ctx.m.get(key_).qty} u.)", auto=dict(tol=tol(L_, h_)), w=(1.0 if L_ > 200 else 0.5), mins=0.2)
        p.vs(lk_ + "_pl", [lk_], "top", lv=(1, 1, 1, 1), extra=(10, 20, 10, 20), title=f"{sc(key_).rsplit('-', 2)[0]} — PLANTA", auto=dict(tol=tol(t_)), w=(0.5 if L_ > 200 else 0.3), hatch=False, mins=0.2)
    Lx, tx, hx = dims("pared_X")
    zt = loc["pared_X"]["z"][1]
    fr_ = (-0.4, -0.25, -0.1, 0.1, 0.25, 0.4)
    p.datum_in("cpx_L_pl", "surf", "A", at=[(Lx * a_, tx / 2, zt) for a_ in fr_], d=[(0, 1, 0)] * len(fr_))
    p.gd_in("cpx_L_pl", "surf", "flat", "0,5", None, at=[(Lx * a_, -tx / 2, zt) for a_ in fr_], d=[(0, -1, 0)] * len(fr_))
    p.gd_in("cpx_L_pl", "surf", "perp", "0,5", "A", at=[(Lx / 2, 0, zt), (-Lx / 2, 0, zt), (Lx / 2, tx / 4, zt), (-Lx / 2, -tx / 4, zt)], d=[(1, 0, 0), (-1, 0, 0), (1, 0, 0), (-1, 0, 0)])
    # tapa: polígono del núcleo (nariz recortada), agujero en E
    so = ctx.shapes["ct_L"].Solids()[0]
    bb = so.BoundingBox()
    Et = [pz for pz in S["cilindro1"]["piezas"] if pz["id"] == "tapa_inf"][0]
    E1 = S["cilindro1"]["centro"]
    c0 = ctx.shapes["cajon_tapa"].Solids()[0].Center()
    sh_ = (E1[0] - c0.x, E1[1] - c0.y)                    # posición de E en la copia local (centrada en el baricentro)

    def tp(V, p_):
        if ids:
            w_out(p_, soporte_ids(ctx, ["tapa_inf"])[0] if soporte_ids(ctx, ["tapa_inf"]) else ids[0], V, (bb.xmax, bb.ymax - 0.1 * (bb.ymax - bb.ymin), bb.zmax), "top")      # sobre la vista: la línea de referencia no cruza la pieza
    p.vs("ct_pl", ["ct_L"], "top", lv=(2, 2, 2, 2), extra=(0, 0, 60, 0), draw=tp, title=f"{sc('cajon_tapa').rsplit('-', 1)[0]} TAPA RECORTADA EN NARIZ ({ctx.m.get('cajon_tapa').qty} u.: 2 inf. y 2 sup.)",
         auto=dict(fits={tap["agujero_E"]: "H9"}, tol=tol(tap["lado"])), w=2.0, hatch=False, mins=0.4)
    p.vs("ct_c", ["ct_L"], "front", cut=((sh_[0], sh_[1], 0), (0, 1, 0)), lv=(1, 1, 1, 1), title="TAPA — CORTE A-A (por E)", auto=dict(tol=tol(tap["t"]), hole_notes=False, holes=False, axes="v"), w=0.6, hs=0.4)
    rows = [[str(i + 1), fm(q[0], 2), fm(q[1], 2)] for i, q in enumerate(tap["poligono_local"])]
    p.table_block("TAPA: VÉRTICES DEL CONTORNO (núcleo, soporte_E.tapas.poligono_local; origen en E = centro del agujero, X e Y paralelos a los bordes de la base)",
                  [("N°", 9, "C"), ("X [mm]", 22, "R"), ("Y [mm]", 22, "R")], rows)
    if ids:
        add_prep(p, "det_tc", wd(ctx, ids[0]), maxs=0.5, mins=0.5, title=f"DETALLE {ids[0]}: PREPARACIÓN DE JUNTA")
    p.tables()                  # tabla de soldaduras del soporte (8 juntas del núcleo) en CON-007; aquí solo la preparación de la pieza
    Ly, ty, hy = dims("pared_Y")
    Lm, tm, hm = dims("munon_X")
    p.notes([f"Pared trasera X: plancha {fm(Lx, 1)} × {fm(hx, 0)} × {fm(tx, 0)}; pared trasera Y: {fm(Ly, 1)} × {fm(hy, 0)} × {fm(ty, 0)}; muñón: {fm(Lm, 2)} × {fm(hm, 0)} × {fm(tm, 0)} ({S['material']}); "
             f"las paredes traseras se prolongan hacia la mesa (núcleo: {S['tipo']}).",
             f"Tapas: plancha {f(tap['lado'])} × {f(tap['lado'])} × {f(tap['t'])} recortada en nariz con el polígono del núcleo (tabla; holgura de diseño {fm(S['barrido']['holgura_diseno'], 0)} mm al cuerpo del cilindro, "
             f"mínima verificada {fm(S['barrido']['holgura_minima'], 1)} ≥ {fm(S['barrido']['holgura_exigida'], 0)} mm en {int(S['barrido']['n_estados'])} estados); corte CNC desde el JSON; agujero Ø{f(tap['agujero_E'])} {tap['ajuste']}.",
             f"Preparaciones de soldadura (biseles 45° de las CJP TC-U4b {', '.join(ids[:6])} y de la PJP TC-P4 de las tapas {', '.join(ids[6:])}): detalle y tabla de soldaduras de CON-007; la tapa superior va {fm(tap.get('rebaje_sup', 0), 0)} mm bajo el borde de las paredes.",
             "Corte térmico con radio de rincón ≥ 5 mm en los quiebres interiores de la nariz; cantos libres sin rebabas."],
            gd=[("flat", "0,5", None, "Planitud de las caras de cada pieza"), ("perp", "0,5", "A", "Cantos extremos perpendiculares a la cara de la pared (A)")])
    p.build()
    return p.h


@pieza("cilindro_pv")
def sheet_cilindro_pv(ctx):
    g, P = ctx.g, ctx.P
    F = g.FPV
    fr = ctx.m.info["pivotado"]["frames"]["1_antihorario"]
    E, Q, a_ = fr["E"], fr["Q"], fr["a_cil"]
    ctx.local("cilindro_pv", "cpv_L", near=((E[0] + Q[0]) / 2, (E[1] + Q[1]) / 2, g.zc), r=400, shift=(-E[0], -E[1], 0), rot=-a_)
    p = Pieza(ctx, ["cilindro_pv"], "CILINDRO HIDRÁULICO DE DOBLE EFECTO, MODO PIVOTADO (ELEMENTO COMERCIAL — DIMENSIONES DE INTERFAZ)", fmt="auto")
    p.iso_keys = ["cpv_L"]
    on = ["cpv_L"]
    dE, dQ = F["pasador_E"]["d"], F["pasador_Q"]["d"]

    def pl(V, p):
        V.dimh((0, 0, g.zc), (fr["L"], 0, g.zc), "bottom", 1, on=on, text=f"({fm(fr['L'], 1)}: entre ejes en la posición dibujada; retraído {f(P['L0'])})", virt_a=dE / 2, virt_b=dQ / 2)
    p.vs("planta", on, "top", lv=(1, 2, 2, 1), draw=pl, title="PLANTA (posición de toma dibujada en CON-010)", hatch=False, w=1.5, auto=dict(fits={dE: "H9", dQ: "H9"}, hole_rmin=10))
    p.vs("lat", on, "front", lv=(1, 2, 2, 1), title="ELEVACIÓN", hatch=False, w=1.2, auto=dict())
    zc_ = g.zc
    rE = dE / 2 + 17.5
    p.datum_in("lat", "surf", "A", at=[(0, 0, zc_ + P["b_eye"] / 2), (0, 0, zc_ - P["b_eye"] / 2)], d=[(0, 0, 1), (0, 0, -1)])
    p.gd_in("lat", "surf", "par", "0,10", "A", at=[(fr["L"], 0, zc_ + P["b_eye"] / 2), (fr["L"], 0, zc_ - P["b_eye"] / 2)], d=[(0, 0, 1), (0, 0, -1)])
    rows = [["Diámetro de camisa / vástago", f"{f(P['D_bore'])} / {f(P['d_rod'])} mm"], ["Carrera", f"{f(P['stroke'])} mm (requerida {fm(g.PV['carrera_req'], 1)} mm, núcleo)"],
            ["Largo ojal–ojal retraído", f"{f(P['L0'])} mm"], ["Cuerpo: Ø exterior / inicio desde el ojal trasero", f"{f(P['D_body'])} mm / {f(P['e_body'])} mm (núcleo)"],
            ["Presión nominal / alivio", f"{f(P['p_rated'])} psi = {fm(P['p_rated'] * 0.0689476, 0)} bar / {f(P['p_relief'])} bar"],
            ["Ojal trasero (pasador E)", f"Ø{f(dE)} H9 con rótula; ancho {f(P['b_eye'])} mm (entre tapas del cajón, juego {fm(P['g_ch'], 0)} mm por lado)"],
            ["Ojal del vástago (pasador Q)", f"Ø{f(dQ)} H9 con rótula; ancho {f(P['b_eye'])} mm (horquilla del bloque-uña {f(F['bloque_una']['horquilla']['ranura_ojal'])}); Ø exterior ≤ {f(2 * F['bloque_una']['horquilla']['R_cubo'] - 2 * P['g_ch'])} (A CONFIRMAR, supuesto S21)"],
            ["Masa de catálogo", f"{fm(P['m_cyl'], 0)} kg c/u"], ["Fabricante / código", "marca/modelo A DEFINIR POR CATÁLOGO"]]
    p.table_block("ESPECIFICACIÓN DE COMPRA", [("Característica requerida", 70, "L"), ("Valor (del cálculo)", 110, "L")], rows)
    p.tables()
    p.notes(["Elemento comercial: este plano fija solo las dimensiones de interfaz que el cálculo exige; el diseño interno es del fabricante.",
             f"Prueba hidráulica a 1,5 × {f(P['p_relief'])} bar con certificado de fábrica. Pandeo biarticulado E–Q con el vástago al largo retraído + carrera: dato del proveedor (núcleo, ISO/TS 13725).",
             "El mismo cilindro trabaja en ambos sentidos: para invertir el giro pivota en el mismo ojal E hacia el otro lado de la diagonal (CON-010)."],
            gd=[("par", "0,10", "A", "Caras del ojal del vástago paralelas a las del ojal trasero (A)")])
    p.build()
    return p.h


@pieza("pasador_E", "pasador_Q")
def sheet_pasadores_pv(ctx):
    g, P = ctx.g, ctx.P
    F = g.FPV
    loc1(ctx, "pasador_E", "pE_L", rot=0.0)
    loc1(ctx, "pasador_Q", "pQ_L", rot=0.0)
    p = Pieza(ctx, ["pasador_E", "pasador_Q"], f"PASADORES E (Ø{f(F['pasador_E']['d'])}) Y Q (Ø{f(F['pasador_Q']['d'])}) DEL ACCIONAMIENTO PIVOTADO", fmt="auto")
    s = p.s
    p.iso_keys = ["pE_L", "pQ_L"]
    rows = []
    for i, (kk, kl, nm) in enumerate((("pasador_E", "pE_L", "E"), ("pasador_Q", "pQ_L", "Q"))):
        d = F[kk]["d"]
        bb = ctx.shapes[kl].BoundingBox()
        z0_, z1_ = bb.zmin, bb.zmax
        rows.append([ctx.code(kk).replace(CODE + "-", ""), "Ojal trasero (cajón)" if nm == "E" else "Vástago (bloque-uña); extremo inferior = seguidor", f"Ø{f(d)} f8", fm(z1_ - z0_, 1), f"z {fm(F[kk]['z'][0], 0)}–{fm(F[kk]['z'][1], 0)}", str(ctx.m.get(kk).qty)])

        def el(V, p, z0_=z0_, z1_=z1_, d=d, nm=nm):
            s.line(V.P(0, 0, z0_ - 6), V.P(0, 0, z1_ + 6), "EJE")
            if nm == "Q":
                zc_ = F["placas_leva"]["z"][1]
                s.line(V.P(-d / 2 - 6, 0, zc_), V.P(-d / 2 + 6, 0, zc_), "TRAT"); s.line(V.P(d / 2 - 6, 0, zc_), V.P(d / 2 + 6, 0, zc_), "TRAT")
                V.dimv((-d / 2 + g.ch_pp, 0, z0_), (-d / 2, 0, zc_), "left", 0, on=[kl], text=f"{fm(zc_ - z0_, 0)} (extremo templado: seguidor)")
        p.vs(f"el{i}", [kl], "front", lv=(2, 2, 2, 2), extra=(0, 0, 30, 0), draw=el, hatch=False, w=1.2, title=f"{ctx.code(kk).replace(CODE + '-', '')} — PASADOR {nm}",
             auto=dict(rev=(0, 0), fits={d: "f8"}, rev_side="top", tol={round(z1_ - z0_, 1): " ±0,2"}, hole_notes=False))
    rE_, bbE = F["pasador_E"]["d"] / 2, ctx.shapes["pE_L"].BoundingBox()
    p.datum_in("el0", "dim", "A", prefix=f"Ø{f(F['pasador_E']['d'])} f8")
    p.gd_in("el0", "surf", "cyl", "0,02", None, at=[(rE_, 0, bbE.zmin + (bbE.zmax - bbE.zmin) * f_) for f_ in (0.3, 0.7, 0.5)], d=(1, 0, 0))
    p.gd_in("el0", "surf", "perp", "0,05", "A", at=[(-rE_ * 0.5, 0, bbE.zmin), (rE_ * 0.5, 0, bbE.zmin)], d=(0, 0, -1))
    p.detail("det_ch", "el0", (F["pasador_E"]["d"] / 2 - 1, 0, ctx.shapes["pE_L"].BoundingBox().zmax - 1), 8, "B", lv=(1, 1, 1, 1), title=f"DETALLE B: CHAFLÁN {fm(g.ch_pp, 0)}×45° (5:1)", maxs=5.0, hatch=False)
    p.table_block("PASADORES DEL ACCIONAMIENTO PIVOTADO", [("Pieza", 16, "C"), ("Aplicación", 52, "L"), ("Diámetro", 20, "L"), ("Largo [mm]", 18, "R"), ("Posición", 22, "L"), ("Cant", 10, "C")], rows)
    p.tables()
    p.notes([f"Barra rectificada; corte y chaflanes {fm(g.ch_pp, 0)}×45° en torno horizontal; Ø f8 ({iso286.fmt_dev(F['pasador_E']['d'], 'f8')} / {iso286.fmt_dev(F['pasador_Q']['d'], 'f8')} mm), Ra 0,8.",
             f"Material: {propuestas.grado(P['Fy_pp'], F['pasador_Q']['d'], 'barra')} (núcleo: Fy {f(P['Fy_pp'])} MPa); certificado 3.1.",
             f"Pasador Q: extremo inferior templado por inducción ≥ 55 HRC en {fm(F['placas_leva']['z'][1] - F['pasador_Q']['z'][0], 0)} mm (seguidor de la placa-leva), profundidad {g.z_hard_txt}.",
             f"Ajustes: E en las tapas del cajón H9/f8 (núcleo); Q en el bloque-uña H9/f8 (PROPUESTA, requiere núcleo). Montaje con grasa grafitada.",
             "Retención axial: placa y tornillo de catálogo en el extremo superior (PROPUESTA, como en el modo guiado; requiere núcleo)."],
            gd=[("cyl", "0,02", None, "Cilindricidad de los Ø f8"), ("perp", "0,05", "A", "Caras extremas perpendiculares al eje")])
    p.build()
    return p.h


@pieza("bloque_una")
def sheet_bloque(ctx):
    g, P = ctx.g, ctx.P
    F = g.FPV
    BU = F["bloque_una"]
    if BU.get("contorno"):
        return _sheet_bloque_garra(ctx)
    info = ctx.m.info["pivotado"]
    ctx.shapes["blk_L"] = cq.Compound.makeCompound(list(info["bloque_local"].vals()))
    ctx.mat["blk_L"] = "acero"
    p = Pieza(ctx, ["bloque_una"], "BLOQUE-UÑA ACODADO CON HORQUILLA (2 UNIDADES; SE MONTA VOLTEADO PARA EL SENTIDO HORARIO)", fmt="auto")
    s = p.s
    p.iso_keys = ["blk_L"]
    on = ["blk_L"]
    z0b, z1b = BU["z"]
    zs0, zs1, _ = info["slot"]
    hq = BU["horquilla"]
    xc0, xc1 = BU["contorno_local"]["cara"][0][0], BU["contorno_local"]["cara"][1][0]

    def planta(V, p):
        s.line(V.P(-90, 0, z1b), V.P(xc1 + 20, 0, z1b), "EJE")
        s.line(V.P(xc0, BU["cara"]["b"] / 2 + 3, z1b), V.P(xc1, BU["cara"]["b"] / 2 + 3, z1b), "TRAT")
        s.text("Cara de empuje templada ≥ 55 HRC", (V.P(xc0, 0, z1b)[0] - 40, V.P(0, BU["cara"]["b"] / 2 + 10, z1b)[1]), T_N, "BOTTOM_LEFT")
    R_f = float(BU["cara"].get("radio_planta") or 0.0)

    def planta2(V, p):
        planta(V, p)
        if R_f > 0:                                  # cara cilíndrica convexa en planta (núcleo: radio_planta)
            V.dim_rad((xc1 - R_f, 0, z1b), R_f, 18, on=on, text=f"R{fm(R_f, 0)}", ext=14)
            V.dimh((-hq["R_cubo"], 0, z1b), (xc1, 0, z1b), "top", 1, on=on, text=f"{fm(xc1 + hq['R_cubo'], 1)} ±0,2 (al vértice de la cara R{fm(R_f, 0)})")
    p.vs("planta", on, "top", lv=(2, 3, 2, 2), draw=planta2, hatch=False, title="PLANTA (origen en el eje de Q; x hacia el pasador tomado)", w=1.6,
         auto=dict(fits={BU["agujero_Q"]: "H9"}, hole_rmin=10, tol={round(xc1 + hq["R_cubo"], 1): " ±0,2"}))
    p.vs("elev", on, "front", lv=(1, 2, 2, 2), title="ELEVACIÓN (horquilla del ojal del vástago)", hatch=False, w=1.2, auto=dict(tol={round(BU["h"], 1): " ±0,2", round(hq["ranura_ojal"], 1): " +0,5/0"}))
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 2, 2, 2), title="CORTE A-A (por el eje de Q)", hs=0.5, w=1.2, auto=dict(tol={round(hq["t_mejilla"], 1): " ±0,2"}, hole_notes=False, text={round(BU["agujero_Q"], 1): tol_txt(BU["agujero_Q"], "H9")}))
    p.vs("extremo", on, "right", lv=(1, 2, 1, 1), title="VISTA DESDE LA CARA DE EMPUJE", hatch=False, w=0.5, maxs=0.5, auto=dict(tol={round(BU["cara"]["b"], 1): " ±0,2"}))
    p.datum_in("elev", "surf", "A", at=[(150, -70, z1b), (250, -70, z1b), (100, -70, z1b)], d=(0, 0, 1))
    p.gd_in("corte", "surf", "flat", "0,05", None, at=[(xc1, 0, z0b + BU["h"] * 0.3), (xc1, 0, z0b + BU["h"] * 0.6)], d=(1, 0, 0))
    p.gd_in("elev", "surf", "perp", "0,05", "A", at=[(xc1, -40, z0b + BU["h"] * 0.7), (xc1, -40, z0b + BU["h"] * 0.3)], d=(1, 0, 0))
    p.gd_in("corte", "dim", "perp", "0,05", "A", prefix=f"Ø{f(BU['agujero_Q'])} H9", alt=("planta", "dim", None, None, f"Ø{f(BU['agujero_Q'])} H9"))
    p.tables()
    p.notes([f"Forja o bloque; {ctx.m.get('bloque_una').material}; UT EN 10228-3.",
             f"Contorno del núcleo (marco local: origen en Q, x hacia el pasador tomado, y hacia O): cuerpo b = {f(BU['cuerpo']['b'])} desplazado {f(BU['cuerpo']['e_acodado'])} hacia −y; cara {f(BU['cara']['b'])} × {f(BU['cara']['l'])}; cubo R{f(hq['R_cubo'])}.",
             f"Cara de empuje cilíndrica convexa R{fm(BU['cara'].get('radio_planta', 0), 0)} en planta (flecha {fm(BU['cara'].get('flecha_arista', 0), 2)} en la arista; aristas con chaflán 3 × 45°); ancho total del bloque {fm(BU['cuerpo']['b'] + BU['horquilla']['R_cubo'], 0)}." if BU["cara"].get("radio_planta") else "",
             f"Horquilla: ranura {f(hq['ranura_ojal'])} +0,5/0 (ojal del vástago {f(P['b_eye'])} + 2 × {fm(P['g_ch'], 0)}), mejillas {f(hq['t_mejilla'])}; agujero Ø{f(BU['agujero_Q'])} H9 en ambas mejillas en un solo montaje.",
             f"Cara de empuje: temple por inducción {BU['cara']['templada'].replace('Fy_sup', 'límite elástico superficial')}, profundidad {g.z_hard_txt}; rectificada (planitud 0,05, Ra 0,8) y perpendicular a la base A.",
             "Para el sentido horario el mismo bloque se monta volteado (la pieza es simétrica en altura respecto de la ranura)."],
            gd=[("flat", "0,05", None, "Cara de empuje plana"), ("perp", "0,05", "A", "Cara de empuje perpendicular a la cara superior (A)"), ("perp", "0,05", "A", f"Agujero Ø{f(BU['agujero_Q'])} H9 perpendicular a A")])
    p.build()
    return p.h


def bu_polys(BU):
    """Polilíneas del bloque-uña en el marco local para las vistas de posición: con la garra «cuerpo» ya es el contorno completo (la «cara» es solo la
    garra, contenida en él); con la cara convexa heredada, cuerpo + cara."""
    L = BU["contorno_local"]
    return [L["cuerpo"]] if BU.get("contorno") else [L["cuerpo"], L["cara"]]


def _sheet_bloque_garra(ctx):
    """Bloque-uña con garra (núcleo 61fff06): planta con el contorno exacto (LINE/ARC de bloque_una.contorno), asiento cóncavo, labio, nariz y rampa
    acotados; zona templada del asiento; elevación, corte por el eje de Q y vista desde la garra proyectadas del sólido 3D."""
    import acc3d
    g, P = ctx.g, ctx.P
    F = g.FPV
    BU = F["bloque_una"]
    AS, LB, NZ, RP = BU["asiento"], BU["labio"], BU["nariz"], BU["rampa"]
    info = ctx.m.info["pivotado"]
    ctx.shapes["blk_L"] = cq.Compound.makeCompound(list(info["bloque_local"].vals()))
    ctx.mat["blk_L"] = "acero"
    segs = contorno.leer({"segmentos_contorno": BU["contorno"]})
    T0 = (0.0, 0.0, 0.0)
    capa = acc3d.garra_capa(BU)
    p = Pieza(ctx, ["bloque_una"], "BLOQUE-UÑA ACODADO CON GARRA Y HORQUILLA (2 UNIDADES; SE MONTA VOLTEADO PARA EL SENTIDO HORARIO)", fmt="auto")
    p.h.trat = "Asiento templado (ver nota 4)"
    s = p.s
    p.iso_keys = ["blk_L"]
    on = ["blk_L"]
    z0b, z1b = BU["z"]
    hq = BU["horquilla"]
    Rc = hq["R_cubo"]
    Cs, Rs = AS["centro"], AS["radio"]
    x0, x1 = contorno.caja(segs, T0)[0], contorno.caja(segs, T0)[2]
    y0, y1 = contorno.caja(segs, T0)[1], max(contorno.caja(segs, T0)[3], Rc)
    a_lab = -90.0                                                     # extremo del asiento del lado del labio (tangente a la cara del labio)
    a_abi = math.degrees(math.atan2(AS["extremo_abierto"][1] - Cs[1], AS["extremo_abierto"][0] - Cs[0]))
    drawn = []

    # ventana del detalle D (garra): del pie de la rampa a la punta del labio, del borde del cuerpo a la nariz
    wx0, wx1 = RP["hasta"][0] - 14, LB["punta_x"] + 10
    wy0, wy1 = y0 - 10, NZ["y_max"] + 10

    def contorno_win(s_, P_, win):
        """Contorno exacto recortado a una ventana (x0, y0, x1, y1): rectas recortadas, arcos completos (los de la garra caen dentro)."""
        from shapely.geometry import LineString as _LS, box as _bx
        bx = _bx(*win)
        for sg in segs:
            if sg["tipo"] == "recta":
                c_ = _LS([sg["p0"], sg["p1"]]).intersection(bx)
                if not c_.is_empty and c_.geom_type == "LineString":
                    s_.line(P_(c_.coords[0]), P_(c_.coords[-1]), "VIS")
            elif win[0] <= sg["centro"][0] - sg["r"] and sg["centro"][0] + sg["r"] <= win[2] + sg["r"]:
                a0 = contorno._ang(sg["centro"], sg["p0"]); a1 = contorno._ang(sg["centro"], sg["p1"])
                if sg["sentido"] == "cw":
                    a0, a1 = a1, a0
                s_.arc(P_(sg["centro"]), sg["r"] * kk[0], a0 % 360, a1 % 360, "VIS")
    kk = [1.0]

    def planta(s_, ox, oy, k, pl):
        P_ = lambda q: (ox + (q[0] - x0) * k, oy + (q[1] - y0) * k)
        contorno.dibujar_custom(s_, ox, oy, k, segs, T0, [], (x0, y0, x1, y1), layer="VIS", cotas=False)
        drawn.extend(contorno.muestras(segs, T0, n=40))
        s_.circle(P_((0, 0)), BU["agujero_Q"] / 2 * k, "VIS")
        s_.centerlines(P_((0, 0)), BU["agujero_Q"] / 2 * k)
        s_.line(P_((x0 - 8, 0)), P_((x1 + 10, 0)), "EJE")
        s_.line(P_((Cs[0], Cs[1] - Rs - 20)), P_((Cs[0], Cs[1] + Rs + 8)), "EJE")
        s_.cross(P_(Cs), 2.0)
        # centro del asiento respecto de Q (teóricamente exacta: la gobierna el perfil 0,1 del asiento) y medidas totales
        s_.dim(P_((0, 0)), P_((Cs[0], Cs[1])), (y1 - 0) * k + 12, f"{fm(Cs[0], 1)}", "h", ted=True)
        s_.text(f"centro del asiento desde Q (= L_qp {fm(g.PV['L_qp'], 0)} + R_s − r_pasador)", (P_((Cs[0] * 0.55, 0))[0], P_((0, y1))[1] + 22), T_N, "BOTTOM_CENTER")
        s_.dim(P_((x0, y0)), P_((x1, LB["dorso_y"] + 8)), -14, f"{fm(x1 - x0, 1)}", "h")
        s_.dim(P_((x0, 0)), P_((x0, y0)), -10, f"{fm(-y0, 0)}", "v")
        s_.dim(P_((0, y1)), P_((x0, y0)), -22, f"{fm(y1 - y0, 0)}", "v")
        s_.dim_rad(P_((0, 0)), Rc * k, 60.0, f"R{fm(Rc, 0)}", ext=10)
        s_.dim_dia(P_((0, 0)), BU["agujero_Q"] / 2 * k, 300.0, tol_txt(BU["agujero_Q"], "H9"), ext=16)
        s_.datum((P_((0, 0))[0] - BU["agujero_Q"] / 2 * k * 0.71, P_((0, 0))[1] - BU["agujero_Q"] / 2 * k * 0.71 - 1), "B", up=False)
        # perfil del contorno de oxicorte (cuerpo)
        pb = P_((200, 0))
        s_.gdt((pb[0] - 20, pb[1] + 10), "prof", "1", ["A", "B"])
        s_.line((pb[0], pb[1] + 10), pb, "COTA")
        s_.arrow(pb, -math.pi / 2, size=3.0)
        # detalle D: garra
        cx_, cy_ = (wx0 + wx1) / 2, (wy0 + wy1) / 2
        s_.detail_circle(P_((cx_, cy_)), math.hypot(wx1 - wx0, wy1 - wy0) / 2 * k * 0.92, "D")
    nat = (x1 - x0, y1 - y0)
    p.vs("planta", [], "top", nat=nat, lv=(2, 3, 2, 3), extra=(30, 30, 40, 40), w=1.8, maxs=1.0, mins=0.4, custom=planta,
         title="PLANTA (origen en el eje de Q; x hacia el pasador tomado; contorno con ARC y LINE exactos del núcleo)")

    def det_garra(s_, ox, oy, k, pl):
        kk[0] = k
        P_ = lambda q: (ox + (q[0] - wx0) * k, oy + (q[1] - wy0) * k)
        contorno_win(s_, P_, (wx0, wy0, wx1, wy1))
        s_.line(P_((wx0, 0)), P_((wx1, 0)), "EJE")
        s_.line(P_((Cs[0], wy0 + 2)), P_((Cs[0], NZ["y_max"] + 4)), "EJE")
        s_.cross(P_(Cs), 2.0)
        s_.cross(P_(NZ["centro"]), 1.5)
        for sg in segs:
            if wx0 <= sg["p0"][0] <= wx1 and wy0 <= sg["p0"][1] <= wy1:
                s_.dot(P_(sg["p0"]), 0.5)
        # zona templada del asiento (trazo y punto grueso ISO 128 a la profundidad de capa, del lado del material)
        if capa:
            s_.arc(P_(Cs), (Rs + capa) * k, a_abi % 360, a_lab % 360, "TRAT")
            am = math.radians(200.0)
            q_ = (Cs[0] + (Rs + capa) * math.cos(am), Cs[1] + (Rs + capa) * math.sin(am))
            s_.leader(P_(q_), P_((wx0 + 6, -52)), "zona templada (nota 4)")
        # asiento: radio, abrazo (90° hacia el labio + 25° hacia el lado abierto), perfil 0,1 y Ra 1,6
        s_.dim_rad(P_(Cs), Rs * k, 225.0, f"R{fm(Rs, 1)} asiento", ext=18)
        rA = Rs * k * 0.62
        s_.line(P_(Cs), (P_(Cs)[0] + Rs * k * math.cos(math.radians(a_abi)), P_(Cs)[1] + Rs * k * math.sin(math.radians(a_abi))), "COTA")
        s_.dim_ang(P_(Cs), rA, 180.0, 270.0, f"{fm(AS['abrazo_lado_labio_deg'], 0)}°")
        s_.dim_ang(P_(Cs), rA * 1.25, a_abi, 180.0, f"{fm(AS['abrazo_lado_abierto_deg'], 0)}°")
        s_.text(f"abrazo {fm(AS['abrazo_total_deg'], 0)}° ({fm(AS['abrazo_lado_labio_deg'], 0)}° + {fm(AS['abrazo_lado_abierto_deg'], 0)}°)", P_((wx0 + 4, -68)), T_N, "BOTTOM_LEFT")
        s_.text(f"holgura radial {fm(AS['holgura_radial'], 0)} al pasador Ø{fm(g.d_pin, 0)}", P_((wx0 + 4, -76)), T_N, "BOTTOM_LEFT")
        pa = P_((Cs[0] - Rs * math.cos(math.radians(35)), -Rs * math.sin(math.radians(35))))
        fq = P_((wx0 + 4, -38))
        s_.gdt(fq, "prof", "0,1", ["A", "B"])
        s_.line((fq[0] + 30, fq[1] + 7), pa, "COTA")
        s_.arrow(pa, math.atan2(pa[1] - fq[1] - 7, pa[0] - fq[0] - 30), size=3.0)
        pr_ = P_((Cs[0] - Rs * math.cos(math.radians(-10)), -Rs * math.sin(math.radians(-10))))
        s_.roughness((pr_[0] + 3, pr_[1] - 2), "Ra 1,6")
        # labio: sobrepaso, espesor, cara (tangente al asiento) y chaflanes
        s_.dim(P_((Cs[0], LB["dorso_y"])), P_((LB["punta_x"], LB["dorso_y"] + LB["chaflan_exterior"])), -14, f"{fm(LB['saliente_sobre_centro'], 0)}", "h")
        s_.text("sobrepaso del labio", (P_((LB["punta_x"], 0))[0] + 2, P_((0, LB["dorso_y"]))[1] - 14 - 6), T_N, "TOP_LEFT")
        s_.dim(P_((LB["punta_x"] - LB["chaflan_exterior"], LB["dorso_y"])), P_((LB["punta_x"] - LB["chaflan_exterior"], LB["cara_y"])), LB["chaflan_exterior"] * k + 10, f"{fm(LB['espesor'], 0)}", "v")
        s_.dim(P_((LB["punta_x"] - LB["chaflan_exterior"], LB["cara_y"])), P_((Cs[0], Cs[1])), LB["chaflan_exterior"] * k + 10, f"{fm(-LB['cara_y'], 1)}", "v")
        q_ch = (LB["punta_x"] - LB["chaflan_interior"] / 2, LB["cara_y"] - LB["chaflan_interior"] / 2)
        s_.leader(P_(q_ch), (P_(q_ch)[0] + 26, P_(q_ch)[1] + 34), f"2 × chaflán {fm(LB['chaflan_exterior'], 0)} × 45°")
        tr = next(sg for sg in segs if sg.get("rol") == "transicion_labio")
        q_tr = ((tr["p0"][0] + tr["p1"][0]) / 2, (tr["p0"][1] + tr["p1"][1]) / 2)
        s_.leader(P_(q_tr), (P_(q_tr)[0] - 30, P_((0, y0))[1] - 16), f"{fm(tr['p1'][0] - tr['p0'][0], 1)} × 45°")
        # nariz R8: radio y centro (teóricamente exactos desde la punta del labio y desde el borde del cuerpo)
        s_.dim_rad(P_(NZ["centro"]), NZ["radio"] * k, 115.0, f"R{fm(NZ['radio'], 0)} nariz", ext=12)
        s_.dim(P_(NZ["centro"]), P_((LB["punta_x"], LB["cara_y"] + 6)), (NZ["y_max"] - NZ["centro"][1]) * k + 22, f"{fm(LB['punta_x'] - NZ['centro'][0], 1)}", "h", ted=True)
        s_.dim(P_(NZ["centro"]), P_((RP["hasta"][0] - 6, y0)), -(NZ["centro"][0] - RP["hasta"][0] + 6) * k - 10, f"{fm(NZ['centro'][1] - y0, 1)}", "v", ted=True)
        # rampa del dorso a 30° respecto del eje
        r0 = RP["hasta"]
        s_.dim_ang(P_(r0), 34.0, 0.0, RP["angulo_deg"], f"{fm(RP['angulo_deg'], 0)}°")
        qm = ((RP["desde"][0] + r0[0]) / 2, (RP["desde"][1] + r0[1]) / 2)
        s_.leader(P_(qm), (P_(qm)[0] - 22, P_(qm)[1] + 16), "rampa del dorso")
    p.vs("det_garra", [], "top", nat=(wx1 - wx0, wy1 - wy0), lv=(2, 2, 3, 2), extra=(30, 30, 50, 40), w=1.4, maxs=2.0, mins=1.0, custom=det_garra,
         title="DETALLE D: GARRA (asiento, labio de retención, nariz y rampa)")
    p.vs("elev", on, "front", lv=(1, 2, 2, 2), title="ELEVACIÓN (horquilla del ojal del vástago)", hatch=False, w=1.2, auto=dict(tol={round(BU["h"], 1): " ±0,2", round(hq["ranura_ojal"], 1): " +0,5/0"}))
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 2, 2, 2), title="CORTE A-A (por el eje de Q)", hs=0.5, w=1.2, auto=dict(tol={round(hq["t_mejilla"], 1): " ±0,2"}, hole_notes=False, text={round(BU["agujero_Q"], 1): tol_txt(BU["agujero_Q"], "H9")}))
    p.vs("extremo", on, "right", lv=(1, 2, 1, 1), title="VISTA DESDE LA GARRA", hatch=False, w=0.5, maxs=0.5)
    p.datum_in("elev", "surf", "A", at=[(150, -70, z1b), (250, -70, z1b), (100, -70, z1b)], d=(0, 0, 1))
    xb = AS["fondo_x"]
    p.gd_in("corte", "surf", "perp", "0,05", "A", at=[(xb, 0, z0b + BU["h"] * 0.3), (xb, 0, z0b + BU["h"] * 0.6)], d=(1, 0, 0))
    p.gd_in("corte", "dim", "perp", "0,05", "A", prefix=f"Ø{f(BU['agujero_Q'])} H9", alt=("elev", "dim", None, None, f"Ø{f(BU['agujero_Q'])} H9"))
    rows_c = []
    for i, sg in enumerate(segs, 1):
        ex = "—"
        if sg["tipo"] == "arco":
            ex = f"{fm(sg['centro'][0], 1)}; {fm(sg['centro'][1], 1)} / R{fm(sg['r'], 1)} ({'antihorario' if sg['sentido'] == 'ccw' else 'horario'})"
        rows_c.append([str(i), sg.get("rol", "").replace("_", " "), "Arco" if sg["tipo"] == "arco" else "Recta", f"{fm(sg['p0'][0], 1)}; {fm(sg['p0'][1], 1)}", f"{fm(sg['p1'][0], 1)}; {fm(sg['p1'][1], 1)}", ex])
    p.table_block("CONTORNO (núcleo, bloque_una.contorno; marco local: origen en Q): inicio y fin = puntos de tangencia (G1); centro y radio de cada arco",
                  [("N°", 7, "C"), ("Tramo", 30, "L"), ("Tipo", 15, "L"), ("Inicio x; y", 28, "L"), ("Fin x; y", 28, "L"), ("Centro x; y / R", 48, "L")], rows_c)
    VR = BU.get("verificacion") or {}
    p.table_block("GARRA: DATOS DEL NÚCLEO (verificación de toma, salida y retorno)", [("Dato", 70, "L"), ("Valor", 60, "L")], [
        ["Asiento: centro / radio / holgura radial al pasador", f"x {fm(Cs[0], 1)}; y {fm(Cs[1], 1)} / R{fm(Rs, 1)} / {fm(AS['holgura_radial'], 1)} mm"],
        ["Abrazo total (labio + lado abierto)", f"{fm(AS['abrazo_total_deg'], 0)}° ({fm(AS['abrazo_lado_labio_deg'], 0)}° + {fm(AS['abrazo_lado_abierto_deg'], 0)}°)"],
        ["Labio: sobrepaso / espesor / chaflanes", f"{fm(LB['saliente_sobre_centro'], 0)} / {fm(LB['espesor'], 0)} / {fm(LB['chaflan_exterior'], 0)} × 45°"],
        ["Nariz / rampa del dorso", f"R{fm(NZ['radio'], 0)} / {fm(RP['angulo_deg'], 0)}° (autobloqueo {fm(RP['autobloqueo_deg'], 1)}° < {fm(RP['limite_deg'], 0)}°)"],
        ["Toma: primer contacto / holgura al labio", f"{(VR.get('toma') or {}).get('primer_contacto', '—')} / {fm((VR.get('toma') or {}).get('holgura_labio', 0), 1)} mm" + (" — cumple" if (VR.get("toma") or {}).get("cumple") else "")],
        ["Salida al fin del empuje: holgura mínima", f"{fm((VR.get('salida') or {}).get('holgura', 0), 2)} mm en «{(VR.get('salida') or {}).get('minimo_en', '—')}»" + (" — cumple" if (VR.get("salida") or {}).get("cumple") else "")],
        ["Masa bloque + pasador Q (núcleo)", f"{fm(BU.get('masa_bloque', 0), 2)} + {fm(BU.get('masa_pasador_Q', 0), 2)} = {fm(BU.get('masa', 0), 2)} kg por cilindro"]])
    p.tables()
    p.notes([f"Forja o bloque; {ctx.m.get('bloque_una').material}; UT EN 10228-3.",
             f"Contorno del núcleo (marco local: origen en Q, x hacia el pasador tomado, y hacia O): cuerpo b = {f(BU['cuerpo']['b'])} desplazado {f(BU['cuerpo']['e_acodado'])} hacia −y; garra en el extremo; cubo R{f(Rc)}. El DXF lleva el contorno con ARC y LINE exactos (G1; control «bloque_una»).",
             f"Mecanizado: ASIENTO MECANIZADO (fresado a R{fm(Rs, 1)}, perfil 0,1 respecto de A|B, Ra 1,6) y cara del labio con sobreespesor de 2 mm en el oxicorte; RESTO DEL CONTORNO POR OXICORTE CNC (perfil 1 respecto de A|B, ISO 9013 clase 2).",
             f"Asiento: temple por inducción {AS['templado'].replace('Fy_sup', 'límite elástico superficial')}, capa ≥ {fm(capa or 0, 0)} mm (zona templada en la planta); el fresado final del asiento va antes del temple; MT 100 % del asiento después del temple.",
             f"Horquilla: ranura {f(hq['ranura_ojal'])} +0,5/0 (ojal del vástago {f(P['b_eye'])} + 2 × {fm(P['g_ch'], 0)}), mejillas {f(hq['t_mejilla'])}; agujero Ø{f(BU['agujero_Q'])} H9 en ambas mejillas en un solo montaje.",
             "Aristas del asiento y de la nariz con chaflán 1 × 45° (sin filo vivo en el contacto con el pasador).",
             "Para el sentido horario el mismo bloque se monta volteado (la pieza es simétrica en altura respecto de la ranura)."],
            gd=[("prof", "0,1", ["A", "B"], f"Perfil del asiento R{fm(Rs, 1)} y de la cara del labio respecto de A y del agujero de Q (B)"), ("prof", "1", ["A", "B"], "Perfil del resto del contorno (oxicorte CNC)"),
                ("perp", "0,05", "A", "Fondo del asiento perpendicular a la cara superior (A)"), ("perp", "0,05", "A", f"Agujero Ø{f(BU['agujero_Q'])} H9 perpendicular a A")])
    p.build()
    p.h.blk_dxf_pts = drawn
    p.h.indic_ok = list(getattr(p.h, "indic_ok", [])) + [("fcf", "prof", "0,1", ("A", "B")), ("fcf", "prof", "1", ("A", "B")), ("datum", "B")]
    return p.h


@pieza("placa_leva", "placa_leva_h")
def sheet_placa_leva(ctx):
    """Placa-guía curva del modo pivotado: contorno desde pivotado.fabricacion.placas_leva[*].segmentos_contorno / segmentos_canto (núcleo) con
    entidades DXF exactas (ARC y LINE, contorno.py); radios, centros y puntos de tangencia acotados en el marco de la placa; zona templada;
    avellanados ISO 10642 y pasadores ISO 8734; vista de posiciones del pasador Q y del bloque-uña sobre el canto (toma, calado, fin)."""
    g, P = ctx.g, ctx.P
    F, PV = g.FPV, g.PV
    PL = F["placas_leva"]
    ins = PL["instancias"]["1_antihorario"]
    segs = contorno.leer(ins)
    canto = contorno.leer(ins, "segmentos_canto") if ins.get("segmentos_canto") else [s_ for s_ in segs if not s_.get("rol", "").startswith("contorno")]
    so = ctx.shapes["placa_leva"].Solids()[0]
    import completitud
    e1, e2, n1 = completitud.marco(so)
    a_ = math.atan2(e1[1], e1[0])
    us = [v.X * math.cos(a_) + v.Y * math.sin(a_) for v in so.Vertices()]
    vs_ = [-v.X * math.sin(a_) + v.Y * math.cos(a_) for v in so.Vertices()]
    u0, v0 = min(us), min(vs_)
    T = (u0 * math.cos(a_) - v0 * math.sin(a_), u0 * math.sin(a_) + v0 * math.cos(a_), a_)
    env = (max(us) - u0, max(vs_) - v0)
    ctx.shapes["pl_L"] = cq.Compound.makeCompound([contorno.a_local(so, T)])
    ctx.mat["pl_L"] = "acero"
    geo = contorno.geometrico(segs)
    p = Pieza(ctx, ["placa_leva", "placa_leva_h"], "PLACA-GUÍA CURVA: ACC-020 (SENTIDO ANTIHORARIO) Y ACC-024 SIMÉTRICA (SENTIDO HORARIO)", fmt="auto",
              mat_override="42CrMo4+QT, canto templado (ver nota 3)")
    p.h.trat = "Canto templado (ver nota 3)"
    s = p.s
    p.iso_keys = ["pl_L"]
    on = ["pl_L"]
    z0p, zt = PL["z"]
    pern = [contorno.pt_local(q, T) for q in ins["pernos"]]
    pasd = [contorno.pt_local(q, T) for q in (ins.get("pasadores_posicion") or [])]
    dh = PL["pernos"]["agujero"]
    import re as _re
    m_av = _re.search(r"Ø\s*([\d,\.]+)", str(PL["pernos"].get("avellanado", "")))
    d_av = float(m_av.group(1).replace(",", ".")) if m_av else 2 * dh
    d_p = float((PL.get("pasadores_posicion") or {}).get("d", 0) or 0)
    # lado del material respecto del canto (para la capa templada): se prueba un punto a 1 mm a la izquierda del primer tramo
    from shapely.geometry import Polygon as _Pg, Point as _Pt
    poly_ = _Pg(ins["contorno"])
    t0 = contorno.tangente(canto[0], False)
    mid0 = ((canto[0]["p0"][0] + canto[0]["p1"][0]) / 2, (canto[0]["p0"][1] + canto[0]["p1"][1]) / 2)
    izq = poly_.contains(_Pt(mid0[0] - t0[1], mid0[1] + t0[0]))
    capa = 4.0
    m_c = _re.search(r"capa[^\d≥]*≥\s*([\d,\.]+)\s*mm", str(PL["material"]) + " " + str((PL.get("tratamiento") or {}).get("canto", "")))
    if m_c:
        capa = float(m_c.group(1).replace(",", "."))
    temple = [contorno.offset(sg, capa if izq else -capa) for sg in canto if "sin contacto" not in sg.get("rol", "")]
    drawn = []

    def planta_c(s_, ox, oy, k, pl):
        bb = (0.0, 0.0)
        P_ = lambda q: (ox + q[0] * k, oy + q[1] * k)
        holes = [(x, y, dh / 2) for x, y in pern] + [(x, y, d_av / 2) for x, y in pern] + [(x, y, d_p / 2) for x, y in pasd]
        contorno.dibujar_custom(s_, ox, oy, k, segs, T, holes, (0.0, 0.0, env[0], env[1]))
        drawn.extend(contorno.muestras(segs, T, n=40))
        for sg in temple:                       # capa templada: línea gruesa de trazo y punto (ISO 128, tipo 04.2) a la profundidad de capa
            a, b = P_(contorno.pt_local(sg["p0"], T)), P_(contorno.pt_local(sg["p1"], T))
            if sg["tipo"] == "arco":
                c = contorno.pt_local(sg["centro"], T)
                a0 = contorno._ang(sg["centro"], sg["p0"]) - math.degrees(T[2]); a1 = contorno._ang(sg["centro"], sg["p1"]) - math.degrees(T[2])
                if sg["sentido"] == "cw":
                    a0, a1 = a1, a0
                s_.arc(P_(c), sg["r"] * k, a0 % 360, a1 % 360, "TRAT")
            else:
                s_.line(a, b, "TRAT")
        # envolvente
        s_.dim(P_((0, 0)), P_((env[0], 0)), -10, f"{fm(env[0], 1)}", "h")
        s_.dim(P_((env[0], 0)), P_((env[0], env[1])), 10, f"{fm(env[1], 1)}", "v")
        # ángulo del flanco (núcleo: α) respecto del borde recto mayor (x de la placa)
        fl = canto[0]
        q0, q1 = contorno.pt_local(fl["p0"], T), contorno.pt_local(fl["p1"], T)
        ang = math.degrees(math.atan2(q1[1] - q0[1], q1[0] - q0[0]))
        ang_n = abs(((ang + 90) % 180) - 90)
        pc = P_(q0)
        # arco de cota entre el flanco y la prolongación del borde recto (el ángulo agudo, igual al rotulado)
        ref_ = 0.0 if abs(ang) <= 90 else (180.0 if ang > 0 else -180.0)
        a0_, a1_ = sorted((ang, ref_))
        s_.arc(pc, 22, a0_ % 360, a1_ % 360, "COTA")
        s_.line(pc, (pc[0] + 26 * math.cos(math.radians(ref_)), pc[1]), "COTA")
        am_ = math.radians((a0_ + a1_) / 2)
        s_.text(f"{fm(ang_n, 1)}°", (pc[0] + 30 * math.cos(am_), pc[1] + 30 * math.sin(am_)), T_N, "MIDDLE_CENTER")
        s_.leader(P_(contorno.pt_local(((temple[1]["p0"][0] + temple[1]["p1"][0]) / 2, (temple[1]["p0"][1] + temple[1]["p1"][1]) / 2), T)) if len(temple) > 1 else pc,
                  (pc[0] - 30, pc[1] + 40), f"capa templada ≥ {fm(capa, 0)} mm (detalle B)")
        # datums y marcos (ISO 5459 / 1101): B = agujero de pasador 1, C = agujero de pasador 2 (o tornillos extremos); perfil del canto respecto de A|B|C
        refB = pasd[0] if pasd else pern[0]
        refC = pasd[-1] if len(pasd) > 1 else pern[-1]
        rB = (d_p if pasd else dh) / 2
        for q_, L_ in ((refB, "B"), (refC, "C")):
            pp = P_(q_)
            s_.datum((pp[0], pp[1] + rB * k), L_, up=True)
        cm = contorno.pt_local(((canto[2]["p0"][0] + canto[2]["p1"][0]) / 2, (canto[2]["p0"][1] + canto[2]["p1"][1]) / 2), T)
        pcm = P_(cm)
        s_.gdt((pcm[0] - 70, pcm[1] - 22), "prof", "0,2", ["A", "B", "C"])
        s_.line((pcm[0] - 70 + 30, pcm[1] - 15), pcm, "COTA")
        s_.arrow(pcm, math.atan2(pcm[1] - (pcm[1] - 15), pcm[0] - (pcm[0] - 40)), size=3.0)
        php = P_(pern[1])
        s_.gdt((php[0] + 14, php[1] + 10), "pos", "Ø0,2", ["A", "B", "C"])
        s_.line((php[0] + 14, php[1] + 13.5), (php[0] + dh / 2 * k, php[1]), "COTA")
        for i_, (x, y) in enumerate(pern):
            q = P_((x, y)); s_.text(f"T{i_ + 1}", (q[0] + d_av / 2 * k + 1, q[1] + 1), T_N, "BOTTOM_LEFT")
        for i_, (x, y) in enumerate(pasd):
            q = P_((x, y)); s_.text(f"D{i_ + 1}", (q[0] + d_p / 2 * k + 1, q[1] + 1), T_N, "BOTTOM_LEFT")
    p.vs("planta", [], "top", nat=(env[0], env[1]), lv=(2, 2, 3, 2), extra=(20, 20, 60, 30), title="PLANTA (marco de la placa: origen en la esquina de la envolvente, x a lo largo del borde recto mayor; ARC y LINE exactos)",
         w=2.2, maxs=0.5, mins=0.4, custom=planta_c)
    # vista de posiciones del pasador Q y del bloque-uña sobre el canto (toma, calado y fin del empuje)
    pos = PV["posiciones"]["1_antihorario"]
    cin = PV.get("cinematica") or []
    kc = max(range(len(cin)), key=lambda i_: cin[i_].get("F_cil", 0)) if cin else len(pos["Q"]) // 2
    sel = [(0, "toma"), (min(kc, len(pos["Q"]) - 1), "calado (F máx.)"), (len(pos["Q"]) - 1, "fin del empuje")]
    BU = F["bloque_una"]
    rq = F["pasador_Q"]["d"] / 2

    # holgura de sincronía (núcleo c4e12af: placas_leva.holgura_sincronia): estado de retorno con el bloque alineado con E–Q y el pasador B siguiente de la mesa
    HS = PL.get("holgura_sincronia") or {}
    hs1 = (HS.get("instancias") or {}).get("1_antihorario")
    E1 = F["soporte_E"]["cilindro1"]["centro"]
    rpin = g.d_pin / 2

    def _bloque_ret():
        Qg = hs1["Q"]
        ux, uy = Qg[0] - E1[0], Qg[1] - E1[1]; n_ = math.hypot(ux, uy); ux, uy = ux / n_, uy / n_
        vx, vy = -uy, ux
        if vx * (-Qg[0]) + vy * (-Qg[1]) < 0:
            vx, vy = -vx, -vy
        return [[contorno.pt_local((Qg[0] + a * ux + b * vx, Qg[1] + a * uy + b * vy), T) for a, b in poly_] for poly_ in bu_polys(BU)]

    def sincr(s_, ox, oy, k):
        P_ = lambda q: (ox + q[0] * k, oy + q[1] * k)
        for poly in _bloque_ret():
            s_.pline([P_(q) for q in poly], "FANT", closed=True)
        qd = contorno.pt_local(hs1["Q"], T)
        s_.circle(P_(qd), rq * k, "FANT")
        cp = contorno.pt_local(hs1["centro_pasador"], T)
        s_.circle(P_(cp), rpin * k, "FANT")
        s_.cross(P_(cp), 2.0)
        pb, pp = P_(contorno.pt_local(hs1["punto_bloque"], T)), P_(contorno.pt_local(hs1["punto_pasador"], T))
        s_.dot(pb, 0.6); s_.dot(pp, 0.6)
        return pb, pp

    def posic(s_, ox, oy, k, pl):
        P_ = lambda q: (ox + q[0] * k, oy + q[1] * k)
        if hs1:
            pb, pp = sincr(s_, ox, oy, k)
            s_.leader(pb, (pb[0] - 34, pb[1] + 30), f"holgura de sincronía {fm(HS['nominal'], 2)} (detalle C)")
            s_.text("R (retorno)", (P_(contorno.pt_local(hs1["Q"], T))[0] + rq * k + 1.5, P_(contorno.pt_local(hs1["Q"], T))[1] - 1.5), T_N, "TOP_LEFT")
        contorno.dibujar_custom(s_, ox, oy, k, segs, T, [], (0.0, 0.0, env[0], env[1]), layer="VIS", cotas=False)
        for i_, lab in sel:
            Qg, Pg = pos["Q"][i_], pos["P"][i_]
            ql = contorno.pt_local(Qg, T)
            s_.circle(P_(ql), rq * k, "VIS")
            s_.cross(P_(ql), 2.0)
            ux, uy = Pg[0] - Qg[0], Pg[1] - Qg[1]; n_ = math.hypot(ux, uy); ux, uy = ux / n_, uy / n_
            vx, vy = -uy, ux
            if vx * (-Qg[0]) + vy * (-Qg[1]) < 0:
                vx, vy = -vx, -vy
            for poly in bu_polys(BU):
                pts = [P_(contorno.pt_local((Qg[0] + a * ux + b * vx, Qg[1] + a * uy + b * vy), T)) for a, b in poly]
                s_.pline(pts, "FANT", closed=True)
            s_.circle(P_(ql), BU["horquilla"]["R_cubo"] * k, "FANT")
            q_ = P_(ql)
            s_.text(f"{sel.index((i_, lab)) + 1}", (q_[0] - 1.5, q_[1] + rq * k + 1.5), T_N, "BOTTOM_LEFT")
    # envolvente de lo que dibuja la vista de posiciones (canto, Q y bloque en las posiciones), en el marco de la placa
    pts_ = [(0.0, 0.0), (env[0], env[1])]
    for i_, lab in sel:
        Qg, Pg = pos["Q"][i_], pos["P"][i_]
        ux, uy = Pg[0] - Qg[0], Pg[1] - Qg[1]; n_ = math.hypot(ux, uy); ux, uy = ux / n_, uy / n_
        vx, vy = -uy, ux
        if vx * (-Qg[0]) + vy * (-Qg[1]) < 0:
            vx, vy = -vx, -vy
        R_ = BU["horquilla"]["R_cubo"]
        for a, b in [q_ for poly_ in bu_polys(BU) for q_ in poly_] + [(R_, R_), (-R_, -R_), (R_, -R_), (-R_, R_)]:
            pts_.append(contorno.pt_local((Qg[0] + a * ux + b * vx, Qg[1] + a * uy + b * vy), T))
    if hs1:
        for poly in _bloque_ret():
            pts_.extend(poly)
        cp_ = contorno.pt_local(hs1["centro_pasador"], T)
        pts_ += [(cp_[0] - rpin, cp_[1] - rpin), (cp_[0] + rpin, cp_[1] + rpin)]
    bx0, by0 = min(q[0] for q in pts_), min(q[1] for q in pts_)
    bx1, by1 = max(q[0] for q in pts_), max(q[1] for q in pts_)
    p.vs("posic", [], "top", nat=(bx1 - bx0, by1 - by0), lv=(1, 1, 1, 1), extra=(6, 6, 6, 6), title="POSICIONES 1–3 DEL PASADOR Q Y DEL BLOQUE-UÑA SOBRE EL CANTO",
         w=1.8, maxs=0.4, mins=0.4, custom=lambda s_, ox, oy, k, pl: posic(s_, ox - bx0 * k, oy - by0 * k, k, pl))
    if hs1:
        pbl, ppl = contorno.pt_local(hs1["punto_bloque"], T), contorno.pt_local(hs1["punto_pasador"], T)
        cx_, cy_ = (pbl[0] + ppl[0]) / 2, (pbl[1] + ppl[1]) / 2
        Wd = 70.0

        def det_sinc(s_, ox, oy, k, pl):
            # ventana de Wd × Wd mm alrededor de los dos puntos: se recortan el bloque, Q y el pasador B al recuadro del detalle
            from shapely.geometry import Polygon as _Pg2, Point as _Pt2, box as _bx
            win_ = _bx(cx_ - Wd / 2, cy_ - Wd / 2, cx_ + Wd / 2, cy_ + Wd / 2)
            P_ = lambda q: (ox + (q[0] - cx_ + Wd / 2) * k, oy + (q[1] - cy_ + Wd / 2) * k)
            geoms = [(_Pg2(poly).exterior, "FANT") for poly in _bloque_ret()]
            geoms.append((_Pt2(contorno.pt_local(hs1["centro_pasador"], T)).buffer(rpin, 128).exterior, "FANT"))
            geoms.append((_Pt2(contorno.pt_local(hs1["Q"], T)).buffer(rq, 128).exterior, "FANT"))
            for gm, ly in geoms:
                c_ = gm.intersection(win_)
                parts = getattr(c_, "geoms", [c_])
                for ln in parts:
                    if ln.is_empty or ln.geom_type != "LineString":
                        continue
                    s_.pline([P_(q) for q in ln.coords], ly)
            s_.rect(*P_((cx_ - Wd / 2, cy_ - Wd / 2)), *P_((cx_ + Wd / 2, cy_ + Wd / 2)), "FINA")
            a, b = P_(pbl), P_(ppl)
            s_.dot(a, 0.6); s_.dot(b, 0.6)
            s_.dim(a, b, 9, f"{fm(HS['nominal'], 2)}", "a", outside=True)
            s_.text("bloque-uña (garra)" if BU.get("contorno") else "bloque-uña (cara R)", (P_((cx_ - Wd / 2 + 2, 0))[0], P_((0, cy_ + Wd / 2 - 4))[1]), T_N, "TOP_LEFT")
            s_.text(f"pasador B de la mesa (Ø{fm(g.d_pin, 0)})", (P_((cx_ - Wd / 2 + 2, 0))[0], P_((0, cy_ - Wd / 2 + 3))[1]), T_N, "BOTTOM_LEFT")
        p.vs("det_sinc", [], "top", nat=(Wd, Wd), lv=(1, 1, 2, 2), extra=(10, 10, 10, 10), w=0.9, maxs=2.0, mins=1.0, custom=det_sinc,
             title=f"DETALLE C: HOLGURA DE SINCRONÍA EN EL RETORNO ({fm(HS['nominal'], 2)} nominal; peor caso {fm(HS['peor_caso'], 2)} ≥ {fm(HS['margen_exigido'], 0)})")
    p.table_block("POSICIONES DEL EMPUJE (núcleo, sentido antihorario)", [("N°", 8, "C"), ("Posición", 40, "L"), ("θ [°]", 18, "R"), ("Q x; y (marco de la placa)", 40, "L")],
                  [[str(n_ + 1), lab, fm(cin[i_]["th"], 2) if cin else "—", "; ".join(fm(v, 1) for v in contorno.pt_local(pos["Q"][i_], T))] for n_, (i_, lab) in enumerate(sel)] +
                  ([["R", f"retorno: holgura de sincronía {fm(HS['nominal'], 2)} mm (peor caso {fm(HS['peor_caso'], 2)}, tolerancias {fm(HS['tolerancias'], 2)}; exigida ≥ {fm(HS['margen_exigido'], 0)})", fm(hs1["theta_deg"], 2),
                     "; ".join(fm(v, 1) for v in contorno.pt_local(hs1["Q"], T))]] if hs1 else []) +
                  [["—", f"Holgura de empuje {fm(PV['placa_leva']['holgura'], 0)} mm (Q contra el canto)" + ("" if hs1 else f"; sincronía {fm(PV['placa_leva']['sincronia'], 2)} mm"), "", ""]])

    def det_capa(s_, ox, oy, k, pl):
        t_ = PL["t"]
        Pq = lambda x, y: (ox + x * k, oy + y * k)
        s_.pline([Pq(0, 0), Pq(40, 0), Pq(40, t_), Pq(0, t_)], "VIS", closed=True)
        s_.hatch_poly([Pq(0, 0), Pq(40, 0), Pq(40, t_), Pq(0, t_)], scale=0.4, pattern="ANSI31")
        s_.pline([Pq(40 - capa, 1), Pq(40 - capa, t_ - 1)], "TRAT")
        s_.dim(Pq(40 - capa, t_), Pq(40, t_), 8, f"≥ {fm(capa, 0)}", "h")
        s_.dim(Pq(40, 0), Pq(40, t_), 10, f"{fm(t_, 0)}", "v")
        s_.roughness((Pq(40, t_ / 2)[0] + 2, Pq(40, t_ / 2)[1] + 2), "Ra 1,6")
        s_.text("canto guía: temple por inducción 52–56 HRC" if "52" in str(PL["material"]) else "canto guía templado", (Pq(0, -6)[0], Pq(0, -6)[1]), T_N, "TOP_LEFT")
    p.vs("det_capa", [], "front", nat=(40.0, PL["t"]), lv=(1, 1, 2, 2), extra=(10, 20, 20, 10), title="DETALLE B: CAPA TEMPLADA DEL CANTO (corte normal al canto)", w=0.6, maxs=2.0, mins=1.0, custom=det_capa)
    h_av = (d_av - dh) / 2

    def corte_d(V, p_):
        x1_ = pern[0][0]
        V.dimv((x1_ + dh / 2, pern[0][1], zt - h_av), (x1_ + d_av / 2, pern[0][1], zt), "right", 0, on=on, text=f"{fm(h_av, 1)} (avellanado 90° Ø{fm(d_av, 1)})")
        V.dimv((x1_ - 40, pern[0][1], z0p), (x1_ - 40, pern[0][1], zt), "left", 0, on=on, text=f"{fm(PL['t'], 0)} ±0,5")
    p.vs("corte", on, "front", cut=((0, pern[0][1], 0), (0, 1, 0)), center=(pern[0][0], pern[0][1], (z0p + zt) / 2), win=(-60, -(zt - z0p) / 2 - 4, 60, (zt - z0p) / 2 + 4), lv=(1, 1, 2, 1), extra=(20, 30, 20, 30),
         title="CORTE A-A (por el tornillo T1: avellanado y espesor; posiciones en la tabla)", hs=0.5, w=1.0, maxs=2.0, draw=corte_d,
         auto=False)
    p.datum_in("corte", "surf", "A", at=[(pern[0][0] - d_av / 2 - 12, pern[0][1], zt), (pern[0][0] - d_av / 2 - 30, pern[0][1], zt), (pern[0][0] + d_av / 2 + 25, pern[0][1], zt)], d=(0, 0, 1))
    rows = [[f"T{i + 1}", fm(x, 1), fm(y, 1), f"Ø{fm(dh, 0)} + avellanado 90° Ø{fm(d_av, 1)} (ISO 10642 M{fm(PL['pernos']['d'], 0)})"] for i, (x, y) in enumerate(pern)]
    AP_ = (PL.get("pasadores_posicion") or {}).get("alojamiento_placa") or {}
    rows += [[f"D{i + 1}", fm(x, 1), fm(y, 1), f"Ø{fm(d_p, 0)} H7 escariado" + (f", ciego prof. {fm(AP_['prof'], 0)} desde la cara inferior" if AP_.get("prof") and AP_["prof"] < PL["t"] else "") + " (pasador ISO 8734 m6)"] for i, (x, y) in enumerate(pasd)]
    rows.append(["Envolvente", fm(env[0], 1), fm(env[1], 1), "—"])
    p.table_block("AGUJEROS (coordenadas teóricamente exactas en el marco de la placa)", [("Ag.", 16, "C"), ("x [mm]", 20, "R"), ("y [mm]", 20, "R"), ("Tipo", 70, "L")], rows)
    rows_c = []
    for i, sg in enumerate(segs, 1):
        q0, q1 = contorno.pt_local(sg["p0"], T), contorno.pt_local(sg["p1"], T)
        ex = "—"
        if sg["tipo"] == "arco":
            c = contorno.pt_local(sg["centro"], T)
            ex = f"{fm(c[0], 1)}; {fm(c[1], 1)} / R{fm(sg['r'], 1)} ({'antihorario' if sg['sentido'] == 'ccw' else 'horario'})"
        z_ = lambda v: 0.0 if abs(v) < 0.05 else v          # sin «-0» en la tabla
        rows_c.append([str(i), (sg.get("rol") or ""), "Arco" if sg["tipo"] == "arco" else "Recta", f"{fm(z_(q0[0]), 1)}; {fm(z_(q0[1]), 1)}", f"{fm(z_(q1[0]), 1)}; {fm(z_(q1[1]), 1)}", ex])
    p.table_block("CONTORNO (núcleo, segmentos_contorno): inicio y fin = puntos de tangencia; centro y radio de cada arco", [("N°", 7, "C"), ("Tramo", 48, "L"), ("Tipo", 15, "L"), ("Inicio x; y", 28, "L"), ("Fin x; y", 28, "L"), ("Centro x; y / R", 48, "L")], rows_c)
    p.tables()
    tr = PL.get("tratamiento") or {}
    p.notes(([] if geo else ["RETENIDA — A DEFINIR (REQUIERE NÚCLEO): el JSON no trae segmentos geométricos; no fabricar."]) +
            [f"Plancha e = {f(PL['t'])}; material: {PL['material']}.",
             f"Corte: {PL.get('corte', 'láser/agua y fresado CNC')}. El DXF de esta lámina tiene el canto con ARC y LINE exactos del núcleo (G1, quiebre ≤ 0,01°; desviación ≤ {fm(PL.get('tolerancia_polilinea', 0.1), 1)} mm: control «placa_guia»).",
             f"Canto: {tr.get('canto', 'templado')}; rugosidad: {tr.get('rugosidad_canto', 'Ra ≤ 1,6')}; aristas: {tr.get('bordes', '1 × 45°')}.",
             f"{int(PL['pernos']['n'])} tornillos {PL['pernos'].get('norma', '')}; {int((PL.get('pasadores_posicion') or {}).get('n', 0))} pasadores {(PL.get('pasadores_posicion') or {}).get('norma', '')}: {(PL.get('pasadores_posicion') or {}).get('ajuste', '')}.",
             f"Ángulo del flanco acotado respecto del borde recto mayor (el α = {fm(PV['placa_leva']['alpha_deg'], 1)}° del núcleo se mide respecto de la trayectoria de Q); su tolerancia la gobierna el perfil 0,2 del canto.",
             "ACC-024 (horario): simétrica de ACC-020 respecto del eje x (y → ancho − y), avellanados en la cara superior; no se voltean."],
            gd=[("prof", "0,2", ["A", "B", "C"], "Perfil del canto guía respecto de la cara superior (A) y de los pasadores D1 (B) y D2 (C)"), ("pos", "Ø0,2", ["A", "B", "C"], "Agujeros de tornillos y pasadores en posición")])
    p.build()
    p.h.placa_dxf_pts = drawn
    # indicaciones dibujadas en la vista «custom» (no pasan por el colocador de gdt_vistas): se registran para el control
    p.h.indic_ok = list(getattr(p.h, "indic_ok", [])) + [("fcf", "prof", "0,2", ("A", "B", "C")), ("fcf", "pos", "Ø0,2", ("A", "B", "C")), ("datum", "B"), ("datum", "C")]
    return p.h


# ====================================================================================================== MODO 1: leva de reenganche
@pieza("leva_riel")
def sheet_riel(ctx):
    g, P = ctx.g, ctx.P
    F = g.FLG
    R = F["riel"]
    loc1(ctx, "leva_riel", "riel_L", rot=0.0)
    p = Pieza(ctx, ["leva_riel"], "RIEL-LEVA DE REENGANCHE (MODO GUIADO; UNO POR CILINDRO, SE VOLTEA PARA EL OTRO SENTIDO)", fmt="auto")
    s = p.s
    p.iso_keys = ["riel_L"]
    on = ["riel_L"]
    zt = R["z"][1]
    c = ctx.shapes["leva_riel"].Solids()[0].Center()
    p.vs("planta", on, "top", lv=(2, 3, 2, 2), extra=(30, 10, 30, 10), title="PLANTA (canto de leva: toma, bolsillo y rampa)", hatch=False, w=3.0, mins=0.2,
         auto=dict(fits={}, hole_rmin=5, tol={}))
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 1, 1, 1), title="CORTE A-A", hs=0.5, w=0.6, maxs=1.0, auto=dict(tol={round(R["t"], 1): " ±0,5"}))
    xin = max(q[0] for q in R["contorno_local"]) - c.x - 30
    p.datum_in("corte", "surf", "A", at=[(xin, 0, R["z"][0]), (xin - 25, 0, R["z"][0])], d=(0, 0, -1))
    hx, hy = F["porticos"]["pernos_local"][0][0] - c.x, F["porticos"]["pernos_local"][0][1] - c.y
    rh = F["porticos"]["agujero"] / 2
    # datum B: agujero del primer perno; varias posiciones candidatas alrededor del agujero (el colocador elige la libre)
    cand_ = [(math.cos(math.radians(a_)), math.sin(math.radians(a_))) for a_ in (45, 135, 225, 315, 0, 90, 180, 270)]
    p.datum_in("planta", "surf", "B", at=[(hx + rh * cx_, hy + rh * cy_, zt) for cx_, cy_ in cand_], d=[(cx_, cy_, 0) for cx_, cy_ in cand_])
    cq_ = R["contorno_local"][4]
    p.gd_in("planta", "surf", "prof", "0,3", ["A", "B"], at=[(cq_[0] - c.x, (cq_[1] + R["contorno_local"][5][1]) / 2 - c.y, zt)], d=(-1, 0, 0))
    rows = [[str(i + 1), fm(x - c.x, 1), fm(y - c.y, 1)] for i, (x, y) in enumerate(R["contorno_local"])]
    p.table_block("VÉRTICES DEL CONTORNO (núcleo; origen en el centro de la pieza)", [("N°", 10, "C"), ("x [mm]", 24, "R"), ("y [mm]", 24, "R")], rows)
    bbr = ctx.shapes["riel_L"].BoundingBox()
    rows_h = [[f"A{i + 1}", fm(x - c.x - bbr.xmin, 1), fm(y - c.y - bbr.ymin, 1), f"Ø{f(F['porticos']['agujero'])}"] for i, (x, y) in enumerate(F["porticos"]["pernos_local"])]
    p.table_block("AGUJEROS (desde los bordes x mín. / y mín. de la envolvente)", [("Ag.", 10, "C"), ("x [mm]", 24, "R"), ("y [mm]", 24, "R"), ("Ø", 16, "C")], rows_h)
    p.tables()
    p.notes([f"Pletina e = {f(R['t'])} de {ctx.m.get('leva_riel').material}.", "Canto interior (leva): fresado a cota y templado por inducción ≥ 55 HRC (rodillo de leva templado); resto oxicorte.",
             f"{len(F['instancias']['1_antihorario']['pernos'])} agujeros Ø{f(F['porticos']['agujero'])} para pernos M{f(F['porticos']['d_perno'])} a las tapas de los pórticos (ACC-008).",
             "Se monta con el canto de leva hacia el eje de la mesa; para el otro sentido de giro se voltea (simetría en y)."],
            gd=[("prof", "0,3", ["A", "B"], "Perfil del canto de leva respecto de la cara inferior (A) y de los agujeros (B)")])
    p.build()
    return p.h


@pieza("leva_pata", "leva_tapa", "leva_prolong")
def sheet_portico(ctx):
    g, P = ctx.g, ctx.P
    F = g.FLG
    loc1(ctx, "leva_pata", "pata_L", rot=0.0)
    loc1(ctx, "leva_tapa", "tapa_L", rot=0.0)
    loc1(ctx, "leva_prolong", "prol_L", rot=0.0)
    p = Pieza(ctx, ["leva_pata", "leva_tapa", "leva_prolong"], "PÓRTICO DEL RIEL-LEVA: PATA, TAPA Y PROLONGACIÓN DE LA BANCADA (MODO GUIADO)", fmt="auto")
    p.iso_keys = ["pata_L", "tapa_L", "prol_L"]
    ids = jids(ctx, "Patas del pórtico – prolongación", "Patas del pórtico – tapa", "Prolongación de la bancada")

    def dp(V, p):
        if ids:
            w_out(p, ids[0], V, (0, -1, F["porticos"]["patas_local"][0]["z"][0] + 1), "right", dy=18)
    p.vs("pata", ["pata_L"], "front", lv=(1, 2, 1, 1), extra=(0, 0, 115, 0), draw=dp, title=f"{ctx.code('leva_pata').replace(CODE + '-', '')} PATA", auto=dict(tol={}), w=1.0)
    p.vs("pata_l", ["pata_L"], "right", lv=(1, 2, 1, 1), title="PATA — LATERAL", auto=dict(), w=0.8, hatch=False)
    RSt = (F["porticos"].get("pernos") or {}).get("rosca") or {}

    def dtp(V, p_):
        cs_ = V.circles(["tapa_L"], F["porticos"]["d_perno"] / 2 - 0.1, F["porticos"]["d_perno"] / 2 + 0.1)
        if cs_ and RSt.get("ciega"):
            u, v, r = cs_[0]
            V.note_hole((u, v, F["porticos"]["tapas_local"][0]["z"][1]), r, 135, f"{len(cs_)} × M{fm(F['porticos']['d_perno'], 0)}-6H ciegas", ext=24, on=["tapa_L"],
                        lines=[f"{len(cs_)} × M{fm(F['porticos']['d_perno'], 0)}-6H ciegas, rosca útil {fm(RSt['rosca_util'], 0)}", f"taladro Ø{fm(RSt['d_broca'], 1)} prof. {fm(RSt['prof_taladro'], 0)} (núcleo)"])
    p.vs("tapa", ["tapa_L"], "top", lv=(1, 2, 1, 1), title=f"{ctx.code('leva_tapa').replace(CODE + '-', '')} TAPA — PLANTA", auto=dict(hole_rmin=5, hole_notes=not RSt.get("ciega")), w=0.8, hatch=False, draw=dtp)
    def dte(V, p_):
        if len(ids) > 1:
            bb_ = ctx.shapes["tapa_L"].BoundingBox()
            w_out(p_, ids[1], V, ((bb_.xmin + bb_.xmax) / 2, bb_.ymin, bb_.zmin), "right", dy=-14)
    p.vs("tapa_e", ["tapa_L"], "front", lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), title="TAPA — ELEVACIÓN", auto=dict(), w=0.6, hatch=False, draw=dte)
    tpz = F["porticos"]["tapas_local"][0]["z"]
    bbt = ctx.shapes["tapa_L"].BoundingBox()
    p.gd_in("tapa_e", "surf", "flat", "0,1", None, at=[(bbt.xmax - 8, bbt.ymin, tpz[1]), (bbt.xmin + 8, bbt.ymin, tpz[1]), ((bbt.xmin + bbt.xmax) / 2, bbt.ymin, tpz[1])], d=(0, 0, 1))

    def dpr(V, p):
        if len(ids) > 2:
            w_out(p, ids[2], V, (0, -1, F["prolongacion_bancada_local"][0]["z"][0] + 1), "right", dy=18)
    p.vs("prol", ["prol_L"], "front", lv=(1, 2, 1, 1), extra=(0, 0, 115, 0), draw=dpr, title=f"{ctx.code('leva_prolong').replace(CODE + '-', '')} PROLONGACIÓN DE LA BANCADA", auto=dict(), w=0.8)
    p.vs("prol_p", ["prol_L"], "top", lv=(1, 2, 1, 1), title="PROLONGACIÓN — PLANTA", auto=dict(), w=0.8, hatch=False)
    if ids:
        add_prep(p, "det_j26", wd(ctx, ids[0]), t1=30, t2=40)
    p.tables(ids)
    RSp = (F["porticos"].get("pernos") or {}).get("rosca") or {}
    s355 = "S355" in F["porticos"]["material"]
    p.notes([f"Patas y tapas: {F['porticos']['material']}" + ("" if s355 else " (soldadas: WPS calificado con PQR, requiere núcleo)") + f"; prolongación: {ctx.m.get('leva_prolong').material}.",
             (f"Tapas: 2 roscas M{f(F['porticos']['d_perno'])} ciegas desde la cara superior tras soldar: taladro Ø{fm(RSp['d_broca'], 1)} prof. {fm(RSp['prof_taladro'], 0)}, rosca útil {fm(RSp['rosca_util'], 0)}, remanente {fm(RSp['remanente'], 0)} mm "
              f"(engrane {fm(RSp['engrane'], 0)} mm, núcleo); pernos {F['porticos']['pernos']['norma']} del riel." if RSp.get("ciega") else
              f"Tapas: 2 roscas M{f(F['porticos']['d_perno'])} pasantes tras soldar (pernos ISO 4762 M{f(F['porticos']['d_perno'])}×{ctx.m.info.get('perno_riel_L', '—')} 10.9 del riel)."),
             "Posiciones de patas, tapas y prolongaciones: tabla de CON-010 (coordenadas del núcleo, lado +x; el lado −x es el giro de 180°).",
             f"Filete pata–asiento z{fm(F['porticos']['filete_pata_asiento'], 0)} (núcleo); pata–tapa " + (f"z{fm(F['porticos']['filete_pata_tapa'], 0)} (núcleo)" if F['porticos'].get('filete_pata_tapa') is not None else "mínimo AWS (requiere núcleo)") +
             (f"; prolongación–base z{fm(F['prolongacion_soldadura']['filete'], 0)} perimetral (núcleo)." if (F.get('prolongacion_soldadura') or {}).get('filete') else ".")],
            gd=[("flat", "0,1", None, "Planitud de la cara superior de la tapa (apoyo del riel)")])
    p.build()
    return p.h


@pieza("leva_rodillo", "leva_perno", "leva_arandela")
def sheet_seguidor(ctx):
    g, P = ctx.g, ctx.P
    SG = g.FLG["seguidor"]
    RT = SG.get("retencion") or {}
    RN_ = g.FLG["ranura_tapa_patin"]
    ks = [k for k in ("leva_rodillo", "leva_perno", "leva_arandela") if ctx.m.get(k)]
    loc1(ctx, "leva_rodillo", "rod_L", rot=0.0)
    loc1(ctx, "leva_perno", "per_L", rot=0.0)
    if ctx.m.get("leva_arandela"):
        loc1(ctx, "leva_arandela", "ara_L", rot=0.0)
    p = Pieza(ctx, ks, "SEGUIDOR DE LA LEVA: RODILLO, PERNO Y ARANDELA DE TOPE (MODO GUIADO)", fmt="auto")
    p.iso_keys = ["rod_L", "per_L"]
    fit_p = (SG["perno"].get("ajuste") or "f8").split()[1] if len((SG["perno"].get("ajuste") or "").split()) > 1 else "f8"
    p.vs("rod", ["rod_L"], "front", cut=CUT_Y, lv=(1, 2, 2, 1), title=f"{ctx.code('leva_rodillo').replace(CODE + '-', '')} RODILLO — CORTE", hs=0.5, w=1.0,
         auto=dict(rev=(0, 0), rev_side="top", hole_notes=False, fits={SG["perno"]["d"]: "H7"}))
    import re as _re
    m_r = _re.search(r"M(\d+)", str(RT.get("tornillo", "")))
    d_r = float(m_r.group(1)) if m_r else 0.0
    p.vs("per", ["per_L"], "front", cut=CUT_Y, lv=(1, 2, 2, 1), title=f"{ctx.code('leva_perno').replace(CODE + '-', '')} PERNO — CORTE", hs=0.5, w=1.0, maxs=2.0,
         auto=dict(rev=(0, 0), rev_side="top", hole_notes=False, fits={SG["perno"]["d"]: fit_p}, text=({round(d_r, 1): f"M{fm(d_r, 0)}-6H (rosca útil {fm(2 * d_r, 0)})"} if d_r else {})))
    if ctx.m.get("leva_arandela"):
        p.vs("ara", ["ara_L"], "front", cut=CUT_Y, lv=(1, 1, 1, 1), title=f"{ctx.code('leva_arandela').replace(CODE + '-', '')} ARANDELA DE TOPE — CORTE", hs=0.5, w=0.6, auto=dict(rev=(0, 0), rev_side="top", hole_notes=False))
    bbp_ = ctx.shapes["per_L"].BoundingBox()
    p.gd_in("per", "surf", "cyl", "0,02", None, at=[(SG["perno"]["d"] / 2, 0, bbp_.zmin + bbp_.zlen * f_) for f_ in (0.6, 0.8)], d=(1, 0, 0))
    p.tables()
    Lpe = (SG["perno"]["z"][1] - SG["perno"]["z"][0]) if SG["perno"].get("z") else SG["perno"]["largo"]
    p.notes([f"Rodillo Ø{f(SG['rodillo']['d'])}/Ø{f(SG['perno']['d'])} × {f(SG['rodillo']['b'])}: {SG['rodillo'].get('material', 'templado ≥ 55 HRC')}; rectificado; agujero Ø{f(SG['perno']['d'])} H7 sobre el perno {fit_p} (H7/{fit_p}, giro libre). "
             f"Cojinete: {SG['rodillo'].get('cojinete', 'A DEFINIR')}.",
             f"Perno Ø{f(SG['perno']['d'])} × {f(Lpe)} (núcleo, z {fm(SG['perno']['z'][0], 0) if SG['perno'].get('z') else '—'}–{fm(SG['perno']['z'][1], 0) if SG['perno'].get('z') else '—'}): empotrado {f(SG['perno']['empotrado_en_una'])} en la uña "
             f"({SG['perno'].get('fijacion_en_una', 'ajuste A DEFINIR')}; zona empotrada Ø{f(SG['perno']['d'])} p6 PROPUESTA para el prensado) y Ø{f(SG['perno']['d'])} {fit_p} en la ranura y el rodillo.",
             f"Ranura de la tapa del patín (ACC-003): {RN_.get('ajuste', f(RN_['ancho']))} con el perno {SG['perno'].get('ajuste', '')}: juego {fm(RN_['juego'][0], 3)}…{fm(RN_['juego'][1], 3)} mm (ISO 286-2, núcleo)." if RN_.get("juego") else
             f"Perno guiado en y por la ranura de la tapa del patín (ancho {f(RN_['ancho'])}, ACC-003)."] +
            ([f"Retención axial del rodillo (núcleo): {RT['tipo']}: arandela Ø{f(RT['d_arandela'])} × {f(RT['t_arandela'])} (z {fm(RT['z'][0], 0)}–{fm(RT['z'][1], 0)}) y {RT['tornillo']} roscado en el extremo del perno (rosca axial, prof. {fm(2 * float(__import__('re').search(r'M(\d+)', RT['tornillo']).group(1)) + 3, 0)})."] if RT else []),
            gd=[("cyl", "0,02", None, "Cilindricidad del perno")])
    p.build()
    return p.h
