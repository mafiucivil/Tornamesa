"""Lámina de fabricación del inserto de esquina de la plancha base (núcleo e9a0eb3).

Modo pivotado: un inserto bajo cada soporte del ojal E (pivotado.fabricacion.soporte_E.inserto); modo guiado: uno bajo cada ménsula del ojal
trasero (levaGuiada.fabricacion.inserto). Un número de pieza por espesor (cada espesor es otra geometría; acc3d.BAS_NUM «inserto_E<t>» /
«inserto_G<t>»). Todo sale del JSON: contorno («esquinas»), espesor pleno, muescas, transición, rebaje, juntas, secuencia y holguras."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *
from pie_a import wd
from soldadura_det import add_prep


def _local(ctx, I, nk, rot=0.0):
    """Copia local del inserto de la esquina 0 (canónica, (+B/2; −B/2)): origen en la esquina de la base, girada rot grados alrededor de z."""
    import inserto3d
    g = ctx.g
    so = inserto3d.solido(I, 0, g.tb, g.B).val()
    sh = so.translate(cq.Vector(-g.B / 2, g.B / 2, 0))
    if rot:
        sh = sh.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rot)
    ctx.shapes[nk] = cq.Compound.makeCompound([sh])
    ctx.mat[nk] = "acero"
    return nk


def _loc_pt(g, q):
    """Coordenadas de la tornamesa → marco local de la lámina (origen en la esquina (+B/2; −B/2))."""
    return (q[0] - g.B / 2, q[1] + g.B / 2)


@pieza("inserto")
def sheet_inserto(ctx):
    import inserto3d
    from shapely.geometry import Polygon, LineString
    g, P = ctx.g, ctx.P
    I = ctx.m.info["inserto"]
    B, tb, t, k = g.B, g.tb, float(I["t"]), I["_k"]
    piv = g.modo == 2
    pI = ctx.m.get("inserto")
    cod = ctx.code("inserto").replace(CODE + "-", "")
    bajo = "BAJO EL SOPORTE DEL OJAL E" if piv else "BAJO LA MÉNSULA DEL OJAL TRASERO"
    p = Pieza(ctx, ["inserto"], f"INSERTO DE ESQUINA t = {f(t)} {bajo} ({pI.qty} U.): CONTORNO, MUESCAS, TRANSICIÓN 1:{fm(k, 1)}"
              + (", REBAJE" if I.get("rebaje") else "") + " Y BISEL J-I1", fmt="auto")
    s = p.s
    L = _local(ctx, I, "ins_L")
    # sección por la bisectriz de la esquina (perpendicular a la hipotenusa): copia girada 135° (la bisectriz hacia el centro queda sobre +x)
    LR = _local(ctx, I, "ins_R", rot=-135.0)
    p.iso_keys = ["ins_L"]
    C0 = [_loc_pt(g, q) for q in I["esquinas"][0]]
    F0 = [_loc_pt(g, q) for q in I["esquinas_espesor_pleno"][0]]
    RB = [[_loc_pt(g, q) for q in pl] for pl in inserto3d.rebajes_de(I, 0)]
    R_ = I.get("rebaje") or {}
    jI = [w["id"] for w in ctx.welds if w.get("inserto")]
    c_leg = I["catetos"]
    hyp_c = B / math.sqrt(2) - float(I["hipotenusa_dist_centro"])        # distancia de la esquina de la base a la hipotenusa
    xs, ys = [q[0] for q in C0], [q[1] for q in C0]
    # vértices sobre los bordes de la base (x = 0 / y = 0 en el marco local) y extremos de los catetos
    ex = min(q[0] for q in C0 if abs(q[1]) < 1e-6)        # extremo del cateto sobre el borde y = −B/2
    ey = max(q[1] for q in C0 if abs(q[0]) < 1e-6)        # extremo del cateto sobre el borde x = +B/2

    def planta(V, p_):
        from shapely.ops import unary_union
        s.pline([V.P(q[0], q[1], t) for q in F0] + [V.P(F0[0][0], F0[0][1], t)], "FINA")
        zr_ = Polygon(F0).buffer(-2)
        uR = unary_union([Polygon(pl).buffer(20) for pl in RB]) if RB else None
        if uR is not None:
            zr_ = zr_.difference(uR)
        if not zr_.is_empty:
            cF = zr_.representative_point()
            pass
        for i_, pl in enumerate(RB):
            s.pline([V.P(q[0], q[1], R_["z_cara"]) for q in pl] + [V.P(pl[0][0], pl[0][1], R_["z_cara"])], "OCU")
        if RB:
            zq_ = unary_union([Polygon(pl).buffer(-20) for pl in RB]).intersection(Polygon(F0).buffer(-2))
            if not zq_.is_empty:
                cR = zq_.representative_point()
                pass
        # catetos sobre los bordes de la base y ancho total paralelo a la hipotenusa
        V.dimh((ex, 0, 0), (0, 0, 0), "bottom", 0, on=["ins_L"], text=f"{fm(-ex, 1)} ±2 (cateto)")
        V.dimv((0, 0, 0), (0, ey, 0), "right", 0, on=["ins_L"], text=f"{fm(ey, 1)} ±2 (cateto)")
        qx_ = min(C0, key=lambda q: q[0])
        qy_ = max(C0, key=lambda q: q[1])
        if -qx_[0] > -ex + 0.5:
            V.dimh((qx_[0], qx_[1], 0), (0, 0, 0), "bottom", 1, on=["ins_L"], text=f"{fm(-qx_[0], 1)}")
        if qy_[1] > ey + 0.5:
            V.dimv((0, 0, 0), (qy_[0], qy_[1], 0), "right", 1, on=["ins_L"], text=f"{fm(qy_[1], 1)}")
        # hipotenusa: distancia desde la esquina (perpendicular) y largo de la cara (vértices en la tabla)
        e45 = sorted([(a, b) for a, b in zip(C0, C0[1:] + C0[:1]) if abs(abs(b[0] - a[0]) - abs(b[1] - a[1])) < 1e-6 and abs(b[0] - a[0]) > 1], key=lambda e: -math.dist(*e))
        hyp = e45[:1]                       # la hipotenusa es la arista a 45° más larga; las demás son los chaflanes de las muescas (núcleo f2dc2b5)
        chf = e45[1:]
        if len(chf) == 2:
            m1 = ((chf[0][0][0] + chf[0][1][0]) / 2, (chf[0][0][1] + chf[0][1][1]) / 2)
            m2 = ((chf[1][0][0] + chf[1][1][0]) / 2, (chf[1][0][1] + chf[1][1][1]) / 2)
            V.dim((m1[0], m1[1], tb / 2), (m2[0], m2[1], tb / 2), 30, text=f"{fm(math.dist(m1, m2), 1)} (entre chaflanes 45°)", orient="a", on=["ins_L"], txt_shift=-45)   # texto fuera de la bisectriz (marca del corte A-A)
        for a_, b_ in chf:
            V.dim((a_[0], a_[1], tb / 2), (b_[0], b_[1], tb / 2), -18, text=f"{fm(math.dist(a_, b_), 1)} (chaflán 45°)", orient="a", on=["ins_L"])
        if hyp:
            a_, b_ = hyp[0]
            V.dim((a_[0], a_[1], tb), (b_[0], b_[1], tb), 36, text=f"{fm(math.dist(a_, b_), 1)} (hipotenusa)", orient="a", on=["ins_L"])

        p_.cut_mark("planta", "A", (12, -12, t), (-hyp_c / math.sqrt(2) - 50, hyp_c / math.sqrt(2) + 50, t), 225)
        if jI:
            if hyp:
                mx_, my_ = (hyp[0][0][0] + hyp[0][1][0]) / 2, (hyp[0][0][1] + hyp[0][1][1]) / 2
                w_out(p_, jI[0], V, (mx_, my_, tb), "top", dy=18)
    p.vs("planta", ["ins_L"], "top", lv=(2, 2, 2, 3), extra=(30, 30, 40, 30), draw=planta, auto=False, hatch=False, w=4.0, mins=0.2,
         title=f"PLANTA DEL INSERTO {cod.rsplit('-', 1)[0]} (origen en la esquina de la base; vértices en la tabla; línea fina: inicio del espesor pleno t = {f(t)}"
         + (f"; trazo oculto: rebaje a z = {f(R_['z_cara'])}" if RB else "") + ")")

    def corte(V, p_):
        V.dimv((2, 0, 0), (2, 0, t), "left", 0, on=["ins_R"], text=f"{f(t)} ±0,5 (t)")
    p.vs("corte", ["ins_R"], "front", cut=((0, 0, 0), (0, 1, 0)), lv=(2, 2, 2, 2), extra=(0, 0, 20, 0), mat={"ins_R": "acero"}, hs=0.6, draw=corte,
         title=f"CORTE A-A (por la bisectriz de la esquina, perpendicular a la hipotenusa: transición 1:{fm(k, 1)}" + (" y rebaje" if RB else "") + ")",
         auto=dict(on=["ins_R"], maxn=10, tol={}), w=1.6, mins=0.1)
    for jid in jI[:1]:
        add_prep(p, "det_ji1", wd(ctx, jid), maxs=0.5, mins=0.4)
    # tablas de vértices (programa CNC desde el JSON)
    rows = []
    z0_ = lambda v: fm(0.0 if abs(v) < 0.05 else v, 1)
    for i_, (q, qf) in enumerate(zip(C0, F0 + [None] * (len(C0) - len(F0)))):
        rows.append([str(i_ + 1), z0_(-q[0]), z0_(q[1]), z0_(-qf[0]) if qf else "—", z0_(qf[1]) if qf else "—"])
    for i_ in range(len(C0), len(F0)):
        rows.append([str(i_ + 1), "—", "—", z0_(-F0[i_][0]), z0_(F0[i_][1])])
    p.table_block("VÉRTICES (mm desde la esquina de la base: X = distancia al borde x = +B/2, Y = distancia al borde y = −B/2; núcleo «esquinas» / «esquinas_espesor_pleno»)",
                  [("N°", 8, "C"), ("Contorno X", 20, "R"), ("Contorno Y", 20, "R"), ("Espesor pleno X", 22, "R"), ("Espesor pleno Y", 22, "R")], rows)
    M = I.get("muescas") or {}
    H = I.get("holguras") or {}
    dat = [["Espesor del inserto t / de la base / Δ", f"{f(t)} / {f(tb)} / {f(I['delta'])} mm"],
           ["Catetos sobre los bordes de la base", f"{fm(c_leg[0], 1)} / {fm(c_leg[1], 1)} mm"],
           ["Hipotenusa: distancia al centro de la tornamesa / a la esquina", f"{fm(I['hipotenusa_dist_centro'], 1)} / {fm(hyp_c, 1)} mm"],
           ["Ancho paralelo a la hipotenusa (entre los extremos de los catetos)", f"{fm(math.hypot(ex, ey), 1)} mm"],
           ["Muesca lado x (placa-guía / banda del accionamiento)" if M.get("lado_x") else "Muesca lado x", (f"zona libre: a ≤ {fm(B / 2 - M['lado_x']['a'], 1)} del borde x y a ≥ {fm(M['lado_x']['b'] + B / 2, 1)} del borde y" + (f"; esquina con chaflán 45° de {fm(M['lado_x']['chaflan'], 1)} mm (núcleo)" if M['lado_x'].get('chaflan') else "") if M.get("lado_x") else "no lleva")],
           ["Muesca lado y (placa-guía / paso de Q)" if M.get("lado_y") else "Muesca lado y", (f"zona libre: a ≤ {fm(M['lado_y']['b'] + B / 2, 1)} del borde y y a ≥ {fm(B / 2 - M['lado_y']['a'], 1)} del borde x" + (f"; esquina con chaflán 45° de {fm(M['lado_y']['chaflan'], 1)} mm (núcleo)" if M['lado_y'].get('chaflan') else "") if M.get("lado_y") else "no lleva")],
           ["Transición de la cara superior", f"1:{fm(k, 1)}, ancho {fm(I['transicion']['ancho'], 0)} mm desde los bordes interiores (los bordes sobre el borde de la base no llevan junta ni transición)"],
           ["Rebaje local", (f"z = {f(R_['z_cara'])} (prof. {f(R_['profundidad'])}) bajo: {', '.join(R_.get('bajo', []))}; borde 1:{fm(k, 1)}; {len(RB)} polígonos (envolvente convexa del barrido), "
                             f"coordenadas en el JSON (programa CNC); mecanizar después de soldar J-I1" if RB else "no lleva")],
           ["Holguras (núcleo)", f"planta {fm(H.get('planta', 0), 0)} mm ({H.get('planta_a', '—')}); vertical {fm(H.get('vertical', 0), 0)} mm ({H.get('vertical_a', '—')}); a la mesa {fm(H.get('mesa', 0), 0)} mm; exigida {fm(H.get('exigida', 0), 0)} mm"],
           ["Verificación del núcleo", f"FU máx. {fm(I.get('fu_max', 0), 3)} (F_b = 1,25·Fy/Nd = {fm(I.get('Fb', 0), 1)} MPa, ASME BTH-1-2020 §3-2.3.4); estado «{I.get('estado', '—')}»"
                                       + (" — sobre el objetivo interno 0,90: advertencia, pendiente de aceptación del mandante" if (I.get("fu_max") or 0) > 0.9 else "")],
           ["Masa (núcleo, excedente sobre la base / 3D, mismo excedente / 3D, pieza completa)",
            (lambda me_: f"{fm(I['masa'], 1)} kg / {fm(me_, 1)} kg ({fm((me_ / I['masa'] - 1) * 100, 2)} %) / {fm(pI.mass_unit, 1)} kg por inserto")(pI.mass_unit - __import__('shapely.geometry', fromlist=['Polygon']).Polygon(I['esquinas'][0]).area * tb * pI.rho)]]
    p.table_block("DATOS DEL INSERTO (núcleo: " + ("pivotado.fabricacion.soporte_E.inserto" if piv else "levaGuiada.fabricacion.inserto") + ")", [("Concepto", 44, "L"), ("Valor", 96, "L")], dat)
    p.tables(jI)
    tipos = getattr(pI, "tipos", []) or []
    sec = [x for x in (I.get("secuencia") or [])]
    lim = [x["texto"] for x in (I.get("limitaciones_uso") or []) if x.get("texto")]
    p.notes([f"Plancha de {f(t)} mm de {I['material']}, con certificado EN 10204 3.1 (trazabilidad por colada); calidad Z35 (EN 10164) y UT ASTM A578 nivel B PROPUESTOS: "
             f"{'las paredes del soporte del ojal E' if piv else 'las mejillas y el suplemento de la ménsula'} se sueldan sobre su cara superior.",
             f"Contorno por oxicorte/plasma CNC desde los vértices del JSON (tabla), tolerancia ISO 9013 clase 3 (±2 en catetos); la plancha base lleva la ventana con el mismo contorno (BAS-001).",
             f"Transición 1:{fm(k, 1)} en la cara superior a lo largo de los bordes interiores, del borde de la junta (z = {f(tb)}) al contorno de espesor pleno (z = {f(t)}); biseles planos entre ambos contornos (corte A-A).",
             f"Junta {', '.join(jI)} con la base: CJP a tope en doble V (detalle), al ras por debajo; soldar desde arriba, voltear, resanar la raíz y soldar por abajo; amolar al ras la cara inferior "
             "(con la base: escalón ≤ 0,5 mm y planitud 1,0 mm en el inserto, apoyo en la losa); VT 100 % y UT 100 %.",
             *([f"Rebaje local de la cara superior a z = {f(R_['z_cara'])} después de soldar J-I1 (fresado o cepillado, borde 1:{fm(k, 1)}); el modelo 3D simplifica el polígono del JSON a ≤ 0,05 mm."] if RB else []),
             (f"Se fabrican {pI.qty} insertos: " + ("el del cilindro 2 es el mismo, girado 180°." if piv else
                                                     ("tipos " + " y ".join(f"{cod.rsplit('-', 1)[0]}-{t_['suf']} ({t_['n']} u.)" for t_ in tipos) + ": el -2 es el simétrico del -1 (espejo respecto del eje x); misma tabla con Y cambiada de signo." if len(tipos) > 1 else "todos iguales."))),
             "Secuencia del núcleo: " + " ".join(sec),
             *[f"Limitación de uso del núcleo (GEN-001): {x}" for x in lim]])
    p.build()
    return p.h
