"""Láminas de fabricación del accionamiento según el modo del núcleo.
Modo 2 (pivotado tipo KIET, por defecto): cajón del ojal E (BAS-008), cilindro (ACC-013), pasadores E y Q (ACC-014), bloque-uña (ACC-015), placa-leva (ACC-017).
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
@pieza("cajon_pared", "cajon_ventana_a", "cajon_ventana_b", "cajon_tapa")
def sheet_cajon_piezas(ctx):
    g, P = ctx.g, ctx.P
    S = g.FPV["soporte_E"]
    t, L, h = S["t_pared"], S["lado"], S["alto_paredes"]
    tap = S["tapas"]
    li = L - 2 * t
    zv0, zv1 = S["ventana"]["z"]
    ks = ["cajon_pared", "cajon_ventana_a", "cajon_ventana_b", "cajon_tapa"]
    loc1(ctx, "cajon_pared", "cp_L")
    loc1(ctx, "cajon_ventana_a", "cva_L")
    loc1(ctx, "cajon_ventana_b", "cvb_L")
    loc1(ctx, "cajon_tapa", "ct_L", idx=0, rot=0.0)
    p = Pieza(ctx, ks, "CAJÓN DEL OJAL E: PAREDES Y TAPAS (PIEZAS, MODO PIVOTADO)", fmt="auto")
    s = p.s
    p.iso_keys = ["cva_L"]
    ids = jids(ctx, "Paredes del cajón", "Tapas del cajón", "Esquinas del cajón")
    zt = S["z_paredes"][1]

    def el_p(V, p):
        if ids:
            w_out(p, ids[0], V, ((L - t) / 2 * 0.4, -t / 2, S["z_paredes"][0] + 0.5), "right", dy=22)
    tolp = {round(L - t, 1): " ±0,5", round(h, 1): " ±0,5"}
    p.vs("cp_el", ["cp_L"], "front", lv=(1, 2, 1, 1), extra=(0, 0, 115, 0), draw=el_p, title=f"{ctx.code('cajon_pared').replace(CODE + '-', '')} PARED COMPLETA — ELEVACIÓN ({ctx.m.get('cajon_pared').qty} en total)", auto=dict(tol=tolp), w=1.2)
    p.vs("cp_pl", ["cp_L"], "top", lv=(1, 1, 1, 1), extra=(20, 30, 20, 30), title="PARED COMPLETA — PLANTA (espesor)", auto=dict(tol={round(t, 1): " ±0,5"}), w=0.6, hatch=False)
    p.vs("cva_el", ["cva_L"], "front", lv=(1, 2, 2, 2), title=f"{ctx.code('cajon_ventana_a').replace(CODE + '-', '')} PARED CON VENTANA (ESQUINA) — ELEVACIÓN", auto=dict(tol=tolp), w=1.2)
    p.vs("cvb_el", ["cvb_L"], "front", lv=(1, 2, 2, 2), title=f"{ctx.code('cajon_ventana_b').replace(CODE + '-', '')} PARED CON VENTANA (TOPE) — ELEVACIÓN", auto=dict(tol=tolp), w=1.2)

    def tp(V, p):
        if len(ids) > 1:
            w_out(p, ids[1], V, (li / 2, 0, tap["z_inf"][1]), "right", dy=-18)
    p.vs("ct_pl", ["ct_L"], "top", lv=(1, 2, 2, 1), extra=(0, 0, 90, 0), draw=tp, title=f"{ctx.code('cajon_tapa').replace(CODE + '-', '')} TAPA — PLANTA ({ctx.m.get('cajon_tapa').qty} en total)",
         auto=dict(fits={tap["agujero_E"]: "H9"}, tol={round(li, 1): " −0,5"}), w=1.0, hatch=False)
    p.vs("ct_c", ["ct_L"], "front", cut=CUT_Y, lv=(1, 1, 1, 1), title="TAPA — CORTE A-A", auto=dict(tol={round(tap["t"], 1): " ±0,5"}, hole_notes=False, holes=False, axes="v"), w=0.6, hs=0.4)
    z0w = S["z_paredes"][0]
    Lw = (L - t) / 2
    p.datum_in("cp_pl", "surf", "A", at=[(-Lw * 0.6, t / 2, zt), (Lw * 0.6, t / 2, zt), (-Lw * 0.85, t / 2, zt), (Lw * 0.85, t / 2, zt), (-Lw * 0.6, -t / 2, zt), (Lw * 0.6, -t / 2, zt)],
               d=[(0, 1, 0)] * 4 + [(0, -1, 0)] * 2)
    p.gd_in("cp_pl", "surf", "flat", "0,5", None, at=[(Lw * 0.1, -t / 2, zt), (-Lw * 0.2, -t / 2, zt), (Lw * 0.3, -t / 2, zt)], d=(0, -1, 0))
    p.gd_in("cp_el", "surf", "perp", "0,5", "A", at=[(Lw, -t / 2, z0w + h * 0.6), (-Lw, -t / 2, z0w + h * 0.6)], d=[(1, 0, 0), (-1, 0, 0)])
    if ids:
        add_prep(p, "det_j23", wd(ctx, ids[0]), t1=t, t2=g.tb)
    p.tables(ids)
    p.notes([f"Paredes: plancha {f(t)} × {f(h)} × {f(L - t)} ({S['material']}); disposición en molinete: cada pared apoya su extremo contra la cara interior de la siguiente (CON-007).",
             f"Ventana para el giro del ojal: z {fm(zv0, 0)}–{fm(zv1, 0)} desde la cara inferior de la base, en el sector {fm(S['ventana']['sector_deg'][0], 2)}°–{fm(S['ventana']['sector_deg'][1], 2)}° desde E (núcleo); "
             "la pared que cubre la esquina lleva la ventana más larga (BAS-009) y la que apoya contra ella la más corta (BAS-010). Oxicorte con radio de rincón ≥ 5 mm.",
             f"Tapas: {f(li)} × {f(li)} × {f(tap['t'])}, mecanizadas a {f(li)} −0,5 para entrar entre paredes (el núcleo da lado = {fm(tap['lado'], 0)}: requiere núcleo, GEN-009); agujero Ø{f(tap['agujero_E'])} H9 mandrinado en línea en el cajón soldado y aliviado (CON-007).",
             "Soldaduras: ver la tabla y CON-007 (secuencia de armado y accesibilidad de los filetes, A DECIDIR POR EL CALCULISTA)."],
            gd=[("flat", "0,5", None, "Planitud de las caras de cada pared y de cada tapa"), ("perp", "0,5", "A", "Cantos extremos perpendiculares a la cara de la pared (A)")])
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
             "RETENIDA (requiere núcleo): con e_cuerpo del núcleo el cuerpo del cilindro entra en el cajón del ojal E (conflicto declarado, GEN-009).",
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


@pieza("placa_leva")
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
    p = Pieza(ctx, ["placa_leva"], "PLACA-GUÍA CURVA DEL MODO PIVOTADO (4 IGUALES; LAS DEL SENTIDO HORARIO SE MONTAN VOLTEADAS)", fmt="auto")
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
         w=2.2, maxs=1.0, mins=0.4, custom=planta_c)
    # vista de posiciones del pasador Q y del bloque-uña sobre el canto (toma, calado y fin del empuje)
    pos = PV["posiciones"]["1_antihorario"]
    cin = PV.get("cinematica") or []
    kc = max(range(len(cin)), key=lambda i_: cin[i_].get("F_cil", 0)) if cin else len(pos["Q"]) // 2
    sel = [(0, "toma"), (min(kc, len(pos["Q"]) - 1), "calado (F máx.)"), (len(pos["Q"]) - 1, "fin del empuje")]
    BU = F["bloque_una"]
    rq = F["pasador_Q"]["d"] / 2

    def posic(s_, ox, oy, k, pl):
        P_ = lambda q: (ox + q[0] * k, oy + q[1] * k)
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
            for poly in (BU["contorno_local"]["cuerpo"], BU["contorno_local"]["cara"]):
                pts = [P_(contorno.pt_local((Qg[0] + a * ux + b * vx, Qg[1] + a * uy + b * vy), T)) for a, b in poly]
                s_.pline(pts, "FANT", closed=True)
            s_.circle(P_(ql), BU["horquilla"]["R_cubo"] * k, "FANT")
            q_ = P_(ql)
            s_.text(f"{sel.index((i_, lab)) + 1}", (q_[0] - 1.5, q_[1] + rq * k + 1.5), T_N, "BOTTOM_LEFT")
    # envolvente de lo que dibuja la vista de posiciones (canto, Q y bloque en las 3 posiciones), en el marco de la placa
    pts_ = [(0.0, 0.0), (env[0], env[1])]
    for i_, lab in sel:
        Qg, Pg = pos["Q"][i_], pos["P"][i_]
        ux, uy = Pg[0] - Qg[0], Pg[1] - Qg[1]; n_ = math.hypot(ux, uy); ux, uy = ux / n_, uy / n_
        vx, vy = -uy, ux
        if vx * (-Qg[0]) + vy * (-Qg[1]) < 0:
            vx, vy = -vx, -vy
        R_ = BU["horquilla"]["R_cubo"]
        for a, b in BU["contorno_local"]["cuerpo"] + BU["contorno_local"]["cara"] + [(R_, R_), (-R_, -R_), (R_, -R_), (-R_, R_)]:
            pts_.append(contorno.pt_local((Qg[0] + a * ux + b * vx, Qg[1] + a * uy + b * vy), T))
    bx0, by0 = min(q[0] for q in pts_), min(q[1] for q in pts_)
    bx1, by1 = max(q[0] for q in pts_), max(q[1] for q in pts_)
    p.vs("posic", [], "top", nat=(bx1 - bx0, by1 - by0), lv=(1, 1, 1, 1), extra=(6, 6, 6, 6), title="POSICIONES 1–3 DEL PASADOR Q Y DEL BLOQUE-UÑA SOBRE EL CANTO",
         w=1.8, maxs=0.4, mins=0.2, custom=lambda s_, ox, oy, k, pl: posic(s_, ox - bx0 * k, oy - by0 * k, k, pl))
    p.table_block("POSICIONES DEL EMPUJE (núcleo, sentido antihorario)", [("N°", 8, "C"), ("Posición", 40, "L"), ("θ [°]", 18, "R"), ("Q x; y (marco de la placa)", 40, "L")],
                  [[str(n_ + 1), lab, fm(cin[i_]["th"], 2) if cin else "—", "; ".join(fm(v, 1) for v in contorno.pt_local(pos["Q"][i_], T))] for n_, (i_, lab) in enumerate(sel)] +
                  [["—", f"Holgura de sincronía {fm(PV['placa_leva']['sincronia'], 2)} mm (peor {fm(PV['placa_leva'].get('sincronia_peor', PV['placa_leva']['sincronia']), 2)}); holgura de empuje {fm(PV['placa_leva']['holgura'], 0)} mm", "", ""]])

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
    p.vs("corte", on, "front", cut=((0, pern[0][1], 0), (0, 1, 0)), lv=(1, 1, 1, 1), extra=(20, 30, 20, 30), title="CORTE A-A (por el tornillo T1: avellanado y espesor)", hs=0.5, w=1.0,
         auto=dict(tol={round(PL["t"], 1): " ±0,5"}, hole_notes=False))
    p.datum_in("corte", "surf", "A", at=[(pern[0][0] + d_av / 2 + 12, pern[0][1], zt), (pern[0][0] - d_av / 2 - 12, pern[0][1], zt), (pern[0][0] + d_av / 2 + 40, pern[0][1], zt)], d=(0, 0, 1))
    rows = [[f"T{i + 1}", fm(x, 1), fm(y, 1), f"Ø{fm(dh, 0)} + avellanado 90° Ø{fm(d_av, 1)} (ISO 10642 M{fm(PL['pernos']['d'], 0)})"] for i, (x, y) in enumerate(pern)]
    rows += [[f"D{i + 1}", fm(x, 1), fm(y, 1), f"Ø{fm(d_p, 0)} H7 escariado (pasador ISO 8734 m6)"] for i, (x, y) in enumerate(pasd)]
    rows.append(["Envolvente", fm(env[0], 1), fm(env[1], 1), "—"])
    p.table_block("AGUJEROS (coordenadas teóricamente exactas en el marco de la placa)", [("Ag.", 16, "C"), ("x [mm]", 20, "R"), ("y [mm]", 20, "R"), ("Tipo", 70, "L")], rows)
    rows_c = []
    for i, sg in enumerate(segs, 1):
        q0, q1 = contorno.pt_local(sg["p0"], T), contorno.pt_local(sg["p1"], T)
        ex = "—"
        if sg["tipo"] == "arco":
            c = contorno.pt_local(sg["centro"], T)
            ex = f"{fm(c[0], 1)}; {fm(c[1], 1)} / R{fm(sg['r'], 1)} ({'antihorario' if sg['sentido'] == 'ccw' else 'horario'})"
        rows_c.append([str(i), (sg.get("rol") or ""), "Arco" if sg["tipo"] == "arco" else "Recta", f"{fm(q0[0], 1)}; {fm(q0[1], 1)}", f"{fm(q1[0], 1)}; {fm(q1[1], 1)}", ex])
    p.table_block("CONTORNO (núcleo, segmentos_contorno): inicio y fin = puntos de tangencia; centro y radio de cada arco", [("N°", 7, "C"), ("Tramo", 48, "L"), ("Tipo", 15, "L"), ("Inicio x; y", 28, "L"), ("Fin x; y", 28, "L"), ("Centro x; y / R", 48, "L")], rows_c)
    p.tables()
    tr = PL.get("tratamiento") or {}
    p.notes(([] if geo else ["RETENIDA — A DEFINIR (REQUIERE NÚCLEO): el JSON no trae segmentos geométricos; no fabricar."]) +
            [f"Plancha e = {f(PL['t'])}; material: {PL['material']}.",
             f"Corte: {PL.get('corte', 'láser/agua y fresado CNC')}. El DXF de esta lámina tiene el canto con ARC y LINE exactos del núcleo (G1, quiebre ≤ 0,01°; desviación ≤ {fm(PL.get('tolerancia_polilinea', 0.1), 1)} mm: control «placa_guia»).",
             f"Canto: {tr.get('canto', 'templado')}; rugosidad: {tr.get('rugosidad_canto', 'Ra ≤ 1,6')}; aristas: {tr.get('bordes', '1 × 45°')}.",
             f"{int(PL['pernos']['n'])} tornillos {PL['pernos'].get('norma', '')}; {int((PL.get('pasadores_posicion') or {}).get('n', 0))} pasadores {(PL.get('pasadores_posicion') or {}).get('norma', '')}: {(PL.get('pasadores_posicion') or {}).get('ajuste', '')}.",
             f"Ángulo del flanco acotado respecto del borde recto mayor; el α = {fm(PV['placa_leva']['alpha_deg'], 1)}° del núcleo se mide respecto de la trayectoria de Q.",
             "Las 4 placas son iguales: las del sentido horario son la imagen especular y se montan volteadas."],
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
    p.vs("planta", on, "top", lv=(2, 3, 2, 2), title="PLANTA (canto de leva: toma, bolsillo y rampa)", hatch=False, w=2.0,
         auto=dict(fits={}, hole_rmin=5, tol={}))
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 1, 1, 1), title="CORTE A-A", hs=0.5, w=0.6, maxs=1.0, auto=dict(tol={round(R["t"], 1): " ±0,5"}))
    xin = max(q[0] for q in R["contorno_local"]) - c.x - 30
    p.datum_in("corte", "surf", "A", at=[(xin, 0, R["z"][0]), (xin - 25, 0, R["z"][0])], d=(0, 0, -1))
    hx, hy = F["porticos"]["pernos_local"][0][0] - c.x, F["porticos"]["pernos_local"][0][1] - c.y
    rh = F["porticos"]["agujero"] / 2
    p.datum_in("planta", "surf", "B", at=[(hx + rh * 0.7071, hy + rh * 0.7071, zt)], d=(1, 1, 0))
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
    p.vs("tapa", ["tapa_L"], "top", lv=(1, 2, 1, 1), title=f"{ctx.code('leva_tapa').replace(CODE + '-', '')} TAPA — PLANTA", auto=dict(hole_rmin=5), w=0.8, hatch=False)
    p.vs("tapa_e", ["tapa_L"], "front", lv=(1, 1, 1, 1), title="TAPA — ELEVACIÓN", auto=dict(), w=0.6, hatch=False)
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
    p.notes([f"Patas y tapas: {F['porticos']['material']} (soldadas: WPS calificado con PQR, requiere núcleo); prolongación: {ctx.m.get('leva_prolong').material}.",
             f"Tapas: 2 roscas M{f(F['porticos']['d_perno'])} pasantes tras soldar (pernos ISO 4762 M{f(F['porticos']['d_perno'])}×{ctx.m.info.get('perno_riel_L', '—')} 10.9 del riel).",
             "Posiciones de patas, tapas y prolongaciones: tabla de CON-010 (coordenadas del núcleo, lado +x; el lado −x es el giro de 180°).",
             f"Filete pata–asiento z{fm(F['porticos']['filete_pata_asiento'], 0)} (núcleo); pata–tapa: mínimo AWS (requiere núcleo)."],
            gd=[("flat", "0,1", None, "Planitud de la cara superior de la tapa (apoyo del riel)")])
    p.build()
    return p.h


@pieza("leva_rodillo", "leva_perno")
def sheet_seguidor(ctx):
    g, P = ctx.g, ctx.P
    SG = g.FLG["seguidor"]
    loc1(ctx, "leva_rodillo", "rod_L", rot=0.0)
    loc1(ctx, "leva_perno", "per_L", rot=0.0)
    p = Pieza(ctx, ["leva_rodillo", "leva_perno"], "SEGUIDOR DE LA LEVA: RODILLO Y PERNO (MODO GUIADO)", fmt="auto")
    p.iso_keys = ["rod_L", "per_L"]
    p.vs("rod", ["rod_L"], "front", cut=CUT_Y, lv=(1, 2, 2, 1), title=f"{ctx.code('leva_rodillo').replace(CODE + '-', '')} RODILLO — CORTE", hs=0.5, w=1.0,
         auto=dict(rev=(0, 0), rev_side="top", hole_notes=False, fits={SG["perno"]["d"]: "H7"}))
    p.vs("per", ["per_L"], "front", lv=(1, 2, 2, 1), title=f"{ctx.code('leva_perno').replace(CODE + '-', '')} PERNO", hatch=False, w=1.0,
         auto=dict(rev=(0, 0), rev_side="top", hole_notes=False, fits={SG["perno"]["d"]: "g6"}))
    bbp_ = ctx.shapes["per_L"].BoundingBox()
    p.gd_in("per", "surf", "cyl", "0,02", None, at=[(SG["perno"]["d"] / 2, 0, bbp_.zmin + bbp_.zlen * f_) for f_ in (0.6, 0.3, 0.8)], d=(1, 0, 0))
    p.tables()
    p.notes([f"Rodillo Ø{f(SG['rodillo']['d'])}/Ø{f(SG['perno']['d'])} × {f(SG['rodillo']['b'])}, templado ≥ 55 HRC y rectificado (grado A DEFINIR, requiere núcleo); ajuste en el perno H7/g6 (PROPUESTA).",
             f"Perno Ø{f(SG['perno']['d'])}: empotrado {f(SG['perno']['empotrado_en_una'])} en la uña (ACC-004, agujero H7 PROPUESTA) y voladizo hasta la cara superior del rodillo; "
             f"el largo del JSON ({f(SG['perno']['largo'])}) no alcanza el rodillo: requiere núcleo (GEN-009). Retención axial del rodillo A DEFINIR.",
             f"Perno guiado en y por la ranura de la tapa del patín (ancho {f(g.FLG['ranura_tapa_patin']['ancho'])}, ACC-003)."],
            gd=[("cyl", "0,02", None, "Cilindricidad del perno")])
    p.build()
    return p.h
