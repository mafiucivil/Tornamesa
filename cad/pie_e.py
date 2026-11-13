"""Lámina de fabricación del refuerzo cuadrado soldado sobre la plancha base (núcleo d537dda; reemplaza al inserto de esquina BAS-018…023).

Modo pivotado: un refuerzo bajo cada soporte del ojal E (pivotado.fabricacion.soporte_E.refuerzo); modo guiado: uno bajo cada ménsula del ojal
trasero (levaGuiada.fabricacion.refuerzo). Un número de pieza por espesor t_d (acc3d.BAS_NUM «refuerzo_E<t_d>» / «refuerzo_G<t_d>») y, si el núcleo
lo pide, el atiesador tangencial (BAS_NUM «refuerzo_ati_h<h>») en la misma lámina. Todo sale del JSON: cuadrado, t, t_d, tapones (Ø, relleno,
posiciones), filetes, PJP, atiesadores, juntas J-R1…J-R4, secuencia y masa."""
import math, sys, pathlib
from collections import Counter
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *
from pie_a import wd
from soldadura_det import add_prep, ref_size, prep_refuerzo


def _pieza_local(ctx, I, nk, g):
    """Refuerzo de la esquina 0 tal como se corta (antes de soldar): plancha a × a × t_d con los agujeros pasantes de los tapones y el bisel 45° × S de
    la PJP en la cara inferior de los dos cantos exteriores. Marco local = traslación del marco de la tornamesa (sin espejo: el patrón de tapones no es
    simétrico): origen en la esquina (+B/2; −B/2) de la base, x = x_real − B/2 ≤ 0, y = y_real + B/2 ≥ 0; z desde la cara inferior del refuerzo."""
    B = g.B
    td = float(I["t_d"])
    a = float(I["lado"])
    S_ = float(((I.get("filetes") or {}).get("bordes_exteriores_PJP") or {}).get("S", 0.0))
    so = cq.Workplane("XY").box(a, a, td, centered=False).translate((-a, 0, 0))
    T = I.get("tapones") or {}
    loc = [(q[0] - B / 2, q[1] + B / 2) for q in (T.get("posiciones") or [[]])[0]]
    if loc:
        so = so.cut(cq.Workplane("XY").workplane(offset=-1).pushPoints(loc).circle(float(T["d"]) / 2).extrude(td + 2))
    if S_ > 0:
        # canto exterior x = 0 (borde x = +B/2) y canto y = 0 (borde y = −B/2): prisma triangular en la cara inferior
        tri_x = cq.Workplane("XZ").polyline([(1, -1), (-S_, -1), (-S_, 0), (0, S_), (1, S_)]).close().extrude(-(a + 2)).translate((0, -1, 0))
        tri_y = cq.Workplane("YZ").polyline([(-1, -1), (S_, -1), (S_, 0), (0, S_), (-1, S_)]).close().extrude(a + 2).translate((-a - 1, 0, 0))
        so = so.cut(tri_x).cut(tri_y)
    ctx.shapes[nk] = cq.Compound.makeCompound([so.val()])
    ctx.mat[nk] = "acero"
    return loc


def _ati_local(ctx, I, nk):
    A = I.get("atiesadores") or {}
    t, h, L = float(A["t"]), float(A["h"]), float(A["largo"])
    so = cq.Workplane("XY").box(L, t, h, centered=False)
    ctx.shapes[nk] = cq.Compound.makeCompound([so.val()])
    ctx.mat[nk] = "acero"
    return t, h, L


@pieza("refuerzo", "refuerzo_ati")
def sheet_refuerzo(ctx):
    g, P = ctx.g, ctx.P
    I = ctx.m.info.get("refuerzo")
    if not I or not ctx.m.get("refuerzo"):
        return None
    B, tb = g.B, float(g.tb)
    td, t, a = float(I["t_d"]), float(I["t"]), float(I["lado"])
    piv = g.modo == 2
    pI = ctx.m.get("refuerzo")
    pA = ctx.m.get("refuerzo_ati")
    T = I.get("tapones") or {}
    FL = I.get("filetes") or {}
    PJ = FL.get("bordes_exteriores_PJP") or {}
    S_, E_ = float(PJ.get("S", 0)), float(PJ.get("E", 0))
    zf = float((FL.get("bordes_interiores") or {}).get("tamano", 0))
    d, rel = float(T.get("d", 0)), float(T.get("profundidad_relleno", 0))
    cod = ctx.code("refuerzo").replace(CODE + "-", "")
    keys = ["refuerzo"] + (["refuerzo_ati"] if pA else [])
    p = Pieza(ctx, keys, f"REFUERZO DE ESQUINA {fm(a, 0)} × {fm(a, 0)} × {f(td)} SOBRE LA BASE ({pI.qty} U.)"
              + (f" Y ATIESADOR {f(pA and I['atiesadores']['t'])} × {f(pA and I['atiesadores']['h'])} × {f(pA and I['atiesadores']['largo'])}" if pA else ""), fmt="auto")
    s = p.s
    loc = _pieza_local(ctx, I, "ref_L", g)
    p.iso_keys = ["ref_L"]
    jR = [w["id"] for w in ctx.welds if w.get("refuerzo_j")]
    # fila de tapones para el corte A-A: la coordenada y' más repetida (pasa por al menos un tapón)
    yc = Counter(round(q[1], 1) for q in loc).most_common(1)[0][0] if loc else a / 2
    xs_t = sorted({round(-q[0], 1) for q in loc})
    ys_t = sorted({round(q[1], 1) for q in loc})

    def planta(V, p_):
        # cotas del contorno, posición de los tapones desde los cantos exteriores (tabla) y bisel oculto
        V.dimh((-a, 0, td), (0, 0, td), "bottom", 0, on=["ref_L"], text=f"{fm(a, 0)} ±2")
        V.dimv((-a, 0, td), (-a, a, td), "left", 0, on=["ref_L"], text=f"{fm(a, 0)} ±2")
        for i_, x_ in enumerate(xs_t):
            V.dimh((-x_, a, td), (0, a, td), "top", i_, on=["ref_L"], text=f"{fm(x_, 1)}")
        for i_, y_ in enumerate(ys_t):
            V.dimv((0, 0, td), (0, y_, td), "right", i_, on=["ref_L"], text=f"{fm(y_, 1)}")
        if loc:
            q0 = max(loc, key=lambda q: -q[0] + q[1])
            V.note_hole((q0[0], q0[1], td), d / 2, 45, f"{len(loc)} × Ø{f(d)} +1/0 pasantes (tapones)", ext=24, on=["ref_L"],
                        lines=[f"{len(loc)} × Ø{f(d)} +1/0 pasantes", f"(tapones {', '.join(j for j in jR if j == 'J-R1')}; tabla)"])
        if S_ > 0:
            s.line(V.P(-S_, 0, td), V.P(-S_, a, td), "OCU")
            s.line(V.P(-a, S_, td), V.P(0, S_, td), "OCU")
        p_.cut_mark("planta", "A", (-a - 30, yc, td), (30, yc, td), 0)
        s.text("esquina de la base", (V.P(0, 0, td)[0] + 4, V.P(0, 0, td)[1] - 4), T_N, "TOP_LEFT")
    p.vs("planta", ["ref_L"], "top", lv=(2, 2, 2, 3), extra=(30, 30, 40, 30), draw=planta, auto=False, hatch=False, w=2.0, mins=0.2,
         title=f"PLANTA DEL REFUERZO {cod.rsplit('-', 1)[0]} (origen en la esquina de la base; cantos exteriores sobre los bordes de la base; trazo oculto: bisel 45° × {f(S_)} de la PJP)")

    def corte(V, p_):
        V.dimv((-a, yc, 0), (-a, yc, td), "left", 0, on=["ref_L"], text=f"{f(td)} ±0,5 (t_d)")
        if S_ > 0:
            V.dimv((-S_, yc, 0), (0, yc, S_), "right", 0, on=["ref_L"], text=f"{f(S_)} × 45° (bisel PJP)")
    p.vs("corte", ["ref_L"], "front", cut=((0, yc, 0), (0, 1, 0)), lv=(2, 2, 2, 2), extra=(0, 0, 20, 0), mat={"ref_L": "acero"}, hs=0.6, draw=corte, auto=False,
         title=f"CORTE A-A (por la fila de tapones a {fm(yc, 1)} del canto exterior; antes de soldar)", w=1.6, mins=0.1)
    R = dict(tb=tb, td=td, d=d, rel=rel, S=S_, E=E_, z=zf)
    (Wn, Hn), _ = ref_size(R)
    p.vs("det_ref", [], "top", nat=(Wn, Hn), lv=(2, 3, 2, 2), extra=(0, 0, 112, 0), mins=1.0, maxs=2.0, w=3.0,
         title=f"DETALLE {' / '.join(j for j in jR if j in ('J-R1', 'J-R2', 'J-R3'))}: TAPÓN Ø{f(d)} (RELLENO {fm(rel, 1)}), FILETE z{f(zf)} INTERIOR Y PJP S{f(S_)}/E{f(E_)} EXTERIOR AL RAS",
         custom=lambda s_, ox, oy, k, pl: prep_refuerzo(s_, ox, oy, k, R, pl, [(j, True) for j in jR]))
    AT = I.get("atiesadores") or {}
    if pA:
        ta, ha, La = _ati_local(ctx, I, "ati_L")
        p.iso_keys = ["ref_L", "ati_L"]

        def ati(V, p_):
            V.dimh((0, 0, ha), (La, 0, ha), "top", 0, on=["ati_L"], text=f"{f(La)} ±2")
            V.dimv((La, 0, 0), (La, 0, ha), "right", 0, on=["ati_L"], text=f"{f(ha)} ±1 (h)")
        p.vs("ati", ["ati_L"], "front", lv=(1, 2, 1, 2), extra=(0, 0, 30, 0), draw=ati, auto=False, hatch=False, w=1.0, mins=0.1,
             title=f"ATIESADOR TANGENCIAL {ctx.code('refuerzo_ati').replace(CODE + '-', '').rsplit('-', 1)[0]}: {f(ta)} × {f(ha)} × {f(La)} (VISTA FRONTAL; espesor {f(ta)})")
        if "J-R4" in jR:
            add_prep(p, "det_r4", wd(ctx, "J-R4"), t1=ta, t2=tb, mins=1.0, maxs=3.0)
    rows = []
    for i_, q in enumerate(loc):
        rows.append([f"T{i_ + 1}", fm(-q[0], 1), fm(a + q[0], 1), fm(q[1], 1), fm(a - q[1], 1)])
    p.table_block(f"TAPONES ({len(loc)} × Ø{f(d)} pasantes; mm desde los cantos del refuerzo: X' desde el canto sobre el borde x = +B/2, Y' desde el canto sobre el borde y = −B/2; núcleo tapones.posiciones)",
                  [("N°", 8, "C"), ("X' (canto ext.)", 22, "R"), ("X' (borde int.)", 22, "R"), ("Y' (canto ext.)", 22, "R"), ("Y' (borde int.)", 22, "R")], rows)
    CR = I.get("corte_rasante") or {}
    tipos = getattr(pI, "tipos", []) or []
    dat = [["Plancha / base / cara superior", f"{fm(a, 0)} × {fm(a, 0)} × {f(td)} mm sobre la base de {f(tb)} (entera, sin ventanas); cara superior a z = {f(t)}"],
           ["Tapones J-R1", f"{T.get('n_por_esquina', 0)} por refuerzo, Ø{f(d)}, agujero {f(T.get('profundidad_agujero', td))}, relleno {fm(rel, 1)} mm; separación ≥ {fm(T.get('separacion_min', 0), 0)}, borde ≥ {fm(T.get('borde_min', 0), 0)} "
                            f"(AISC 360-22 §J2.3); R = {fm(T.get('R_tapon_kN', 0), 1)} kN por tapón"],
           ["Filete J-R2 (bordes interiores)", f"z{f(zf)}, {fm((FL.get('bordes_interiores') or {}).get('largo_por_esquina', 0), 0)} mm por refuerzo"],
           ["PJP J-R3 (cantos exteriores)", f"bisel 45° S{f(S_)} / E{f(E_)}, {fm(PJ.get('largo_por_esquina', 0), 0)} mm por refuerzo; esmerilada al ras del canto de la base"],
           *([["Atiesador J-R4", f"{f(AT['t'])} × {f(AT['h'])} × {f(AT['largo'])}, {len(AT.get('por_esquina') or [])} u., tangente a la esquina interior del refuerzo (eje a {fm(AT.get('d_eje_centro', 0), 1)} del centro; "
                                 f"holgura a la mesa {fm(AT.get('holgura_mesa', 0), 1)}); filete z{f(AT.get('filete', 0))} a ambos lados"]] if pA else []),
           ["Corte rasante (núcleo)", f"V = {fm(CR.get('V_kN', 0), 0)} kN frente a {fm(CR.get('capacidad_kN', 0), 0)} kN (tapones + filetes + PJP): FU {fm(CR.get('fu', 0), 3)}; "
                                      f"levantamiento del talón FU {fm(CR.get('fu_levantamiento', 0), 3)}"],
           ["Verificación del núcleo", f"FU máx. {fm(I.get('fu_max', 0), 3)} (F_b = {fm(I.get('Fb', 0), 1)} MPa, ASME BTH-1-2020 §3-2.3.4); estado «{I.get('estado', '—')}»"
                                       + (" — sobre el objetivo interno 0,90: advertencia del núcleo" if (I.get("fu_max") or 0) > 0.9 else "")],
           ["Masa (núcleo / 3D)", f"{fm(I.get('masa_plancha', I.get('masa', 0)), 1)} / {fm(pI.mass_unit + __import__('refuerzo3d').vol_bisel(I) * pI.rho, 1)} kg por refuerzo (agujeros vacíos sobre el relleno; bisel lleno por J-R3; "
                                  f"pieza cortada {fm(pI.mass_unit, 1)} kg)" + (f"; atiesador {fm(AT.get('masa', 0), 1)} / {fm(pA.mass_unit, 1)} kg" if pA else "")]]
    p.table_block("DATOS DEL REFUERZO (núcleo: " + ("pivotado.fabricacion.soporte_E.refuerzo" if piv else "levaGuiada.fabricacion.refuerzo") + ")", [("Concepto", 44, "L"), ("Valor", 100, "L")], dat)
    p.tables(jR)
    sec = [x for x in (I.get("secuencia") or [])]
    lim = [x["texto"] for x in (I.get("limitaciones_uso") or []) if x.get("texto")]
    tr_ = {"id": "igual", "rot": "girado 180°", "esp": "simétrico (espejo respecto del eje x)", "esprot": "simétrico (espejo respecto del eje y)"}
    p.notes([f"Plancha de {f(td)} mm de {I['material']}, con certificado EN 10204 3.1 (trazabilidad por colada); UT ASTM A578 nivel B PROPUESTO "
             f"({'las paredes del soporte del ojal E y la oreja de la diagonal' if piv else 'las mejillas y el suplemento de la ménsula'} se sueldan sobre su cara superior, z = {f(t)}).",
             f"Contorno por oxicorte/plasma CNC, tolerancia ISO 9013 clase 3 (±2 en el lado); agujeros Ø{f(d)} +1/0 taladrados (pared recta); bisel 45° × {f(S_)} en la cara inferior de los dos cantos exteriores.",
             f"Montaje: cantos exteriores al ras de los bordes de la base (±1); prensar contra la base (contacto ≤ 1 mm, galga) y puntear. La base de {f(tb)} queda ENTERA (sin ventanas) y al ras sobre la losa.",
             f"Soldadura: tapones J-R1 (relleno {fm(rel, 1)} mm por capas, limpiando la escoria), filete J-R2 z{f(zf)} en los bordes interiores, PJP J-R3 S{f(S_)}/E{f(E_)} en los cantos exteriores "
             "esmerilada al ras" + (f"; atiesador con filete J-R4 z{f(AT.get('filete', 0))} a ambos lados y retorno en los extremos" if pA else "") + ". VT 100 %; MT de tapones y PJP (AWS D1.1:2020 cláusula 8).",
             (f"Se fabrican {pI.qty} refuerzos: " + (f"{cod.rsplit('-', 1)[0]}-{tipos[0]['suf']} ({tipos[0]['n']} u.) y {cod.rsplit('-', 1)[0]}-{tipos[1]['suf']} ({tipos[1]['n']} u., espejo del primero respecto del eje x: tabla con Y' en el otro canto)"
                                                     if len(tipos) > 1 else ("el del cilindro 2 es el mismo, girado 180°." if piv else "todos iguales."))),
             "Eliminado por el núcleo (12-11-2026): " + str(I.get("eliminado", "inserto triangular a tope, CJP J-I1 y ventanas de la base")) + ".",
             "Secuencia del núcleo: " + " ".join(sec),
             *[f"Limitación de uso del núcleo (GEN-001): {x}" for x in lim]])
    p.build()
    return p.h
