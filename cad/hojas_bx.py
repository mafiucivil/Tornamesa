"""Láminas de la interfaz TT300-BX (bloque «bx» del JSON de diseño): disco de la mesa en semidiscos con CJP, portador de pastillas, pastilla de
UHMW-PE, conjunto y detalle de montaje de la interfaz (reemplaza a CON-012 de las opciones A/B/C) y tabla de fabricación simplificada (GEN-026).

Se activa solo cuando el JSON trae el bloque «bx» (hojas_bx.activar(), llamado por generar_paquete.py): sin ese bloque el juego no cambia.
Fuente única: todas las magnitudes salen de D["bx"]; las cotas se verifican contra el sólido 3D (cad/bx3d.py) como en el resto del juego."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cadquery as cq
from pie_common import *
from pie_a import wd
from soldadura_det import add_prep
import bx_notas
from bx3d import bolt_groups, puck_groups, pforma, ptxt, porient, semiancho, sitios, tabla_posiciones, tabla_recortadas

ACTIVO = False
_PIEZAS = [("sheet_bx_disco", ["int_bx_disco_mesa"]), ("sheet_bx_portador", ["int_bx_portador"]), ("sheet_bx_pastilla", ["int_bx_pastilla"])]


def activar():
    """Registra las láminas BX en los planes de láminas (una sola vez) y reemplaza el conjunto de la interfaz (CON-012)."""
    global ACTIVO
    if ACTIVO:
        return
    ACTIVO = True
    import hojas_con, hojas_gen
    for nm, keys in _PIEZAS:
        PLAN.append((nm, keys, globals()[nm]))
    hojas_con.sheet_interfaz_conj = sheet_interfaz_conj_bx
    hojas_gen.sheet_bx_fabricacion = sheet_bx_fabricacion
    if "sheet_bx_fabricacion" not in hojas_gen.PLAN_GEN:
        hojas_gen.PLAN_GEN.append("sheet_bx_fabricacion")


# ------------------------------------------------------------------------------------------------ utilidades
def _ang_txt(grp):
    """Ángulos de un anillo: «a0 + paso·k (k = 0…n−1)» si es uniforme; si no, la lista."""
    angs = sorted((float(b["ang"]) % 360.0) for b in grp["bolts"]) if "bolts" in grp else sorted((math.degrees(math.atan2(q["y"], q["x"])) % 360.0) for q in grp["lista"])
    n = len(angs)
    if n > 1:
        d = [angs[i + 1] - angs[i] for i in range(n - 1)]
        if max(d) - min(d) < 0.02 and abs((360.0 - angs[-1] + angs[0]) - d[0]) < 0.02:
            return f"{fm(angs[0], 3)}° + {fm(360.0 / n, 3)}°·k (k = 0…{n - 1})"
    return ", ".join(fm(a, 2) + "°" for a in angs)


def _crop(ctx, keys, suf, cx, cy, hw, z0, z1, rot=0.0):
    """Copias locales (giradas rot° alrededor de z) de las piezas recortadas a la caja |x − cx| ≤ hw, |y − cy| ≤ hw, z0…z1 (cortes de detalle
    rápidos sobre conjuntos de cientos de sólidos)."""
    out = []
    # se gira la caja (no la pieza: el booleano de OCC falla con sólidos girados de muchos agujeros) y luego el recorte
    box = cq.Solid.makeBox(2 * hw, 2 * hw, z1 - z0, cq.Vector(cx - hw, cy - hw, z0))
    if rot:
        box = box.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -rot)
    bbx = box.BoundingBox()
    for k in keys:
        if k not in ctx.shapes:
            continue
        sh = ctx.shapes[k]
        sols = []
        if k == "int_bx_disco_mesa":
            import bx3d
            sols = bx3d.disco_recorte(ctx.g, cx, cy, hw, z0, z1, rot)
        for so in ([] if k == "int_bx_disco_mesa" else sh.Solids()):
            bb = so.BoundingBox()
            if bb.xmax < bbx.xmin or bb.xmin > bbx.xmax or bb.ymax < bbx.ymin or bb.ymin > bbx.ymax or bb.zmax < z0 or bb.zmin > z1:
                continue
            r_ = so.intersect(box)
            for x_ in r_.Solids():
                sols.append(x_.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rot) if rot else x_)
        if sols:
            nk = k + suf
            ctx.shapes[nk] = cq.Compound.makeCompound(sols)
            ctx.mat[nk] = ctx.mat.get(k, "acero")
            out.append(nk)
    return out


def _tornillo(s, V, x, z_ht, d, dk, L, sg, rim=None):
    """Tornillo avellanado ISO 10642 sin cortar (ISO 128-50) dibujado en un corte por su eje: cabeza Ø dk con su cara a z_ht, cono de 90° hasta Ø d
    y vástago hasta la punta (sg = −1: el vástago baja; +1: sube). Las cotas salen del JSON (d, dk, L)."""
    rim = 0.05 * d if rim is None else rim
    z1 = z_ht + sg * rim
    z2 = z1 + sg * (dk - d) / 2
    zt = z_ht + sg * L
    pts = [(x - dk / 2, z_ht), (x + dk / 2, z_ht), (x + dk / 2, z1), (x + d / 2, z2), (x + d / 2, zt), (x - d / 2, zt), (x - d / 2, z2), (x - dk / 2, z1)]
    s.pline([V.P(u, 0, w) for u, w in pts], "VIS", closed=True)
    s.line(V.P(x - d / 2, 0, z2), V.P(x + d / 2, 0, z2), "VIS")
    s.line(V.P(x, 0, z_ht - sg * 4), V.P(x, 0, zt + sg * 4), "EJE")


def _cc(ctx, k):
    return ctx.code(k).replace(CODE + "-", "").replace("-" + REV, "") if ctx.m.get(k) else "—"


# ------------------------------------------------------------------------------------------------ INT-016: disco de la mesa
def sheet_bx_disco(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    X = g.bx
    D = X["disco"]
    T = D["tornillos"]
    t = float(D["t"])
    Ro, Ri = float(D["R_ext"]), float(D["R_int"])
    zs = g.z0 - t                       # cara de deslizamiento (inferior)
    rec = float(T["cabeza_bajo_cara"])
    dk, dc = float(T["d_cabeza"]), float(T["agujero_disco"])
    jc = J(ctx, "Semidisco – semidisco")
    p = Pieza(ctx, ["int_bx_disco_mesa"], "INTERFAZ BX: DISCO DE LA MESA EN SEMIDISCOS INOXIDABLES CON CJP (SUBCONJUNTO SOLDADO)", fmt="A1")
    s = p.s
    on = ["int_bx_disco_mesa"]
    BG = bolt_groups(X)

    def planta(V, p):
        s.line(V.P(-Ro - 25, 0, zs), V.P(Ro + 25, 0, zs), "EJE")
        s.line(V.P(0, -Ro - 25, zs), V.P(0, Ro + 25, zs), "EJE")
        for i, gr in enumerate(BG):
            s.pline([V.P(gr["r"] * math.cos(a), gr["r"] * math.sin(a), zs) for a in [2 * math.pi * k / 160 for k in range(161)]], "EJE")
            s.text(f"A{i + 1}", V.P(gr["r"], 9, zs), T_N, "BOTTOM_CENTER")
        V.dim_dia((0, 0, zs), Ro, 128, on=on, text=f"Ø{f(2 * Ro)} (R{fm(Ro, 0)})", ext=22)
        V.dim_dia((0, 0, zs), Ri, 300, on=on, text=f"Ø{f(2 * Ri)} (R{fm(Ri, 0)})", ext=40)
        b0 = max(BG[-1]["bolts"], key=lambda b: (b["y"], -b["x"]))
        V.note_hole((float(b0["x"]), float(b0["y"]), zs), dc / 2, 60, f"{T['n']} × avellanado Ø{fm(dk, 0)}×90° + pasante Ø{fm(dc, 0)}", ext=36, on=on,
                    lines=[f"{T['n']} × avellanado Ø{fm(dk, 0)}×90° + pasante Ø{fm(dc, 0)}", f"para {T['designacion_base'].split(' (')[0]};", f"anillos A1…A{len(BG)}: tabla (detalle B)"])
        xl_ = min((Ro, -Ro), key=lambda x_: V.P(x_, 0, zs)[0])          # extremo de la CJP del lado izquierdo del papel (la vista inferior invierte x)
        w_out(p, jc, V, (xl_, 0, zs + t / 2), "left", dy=-30, extra_tail=["esmerilada a ras ambas caras"])
        p.cut_mark("planta", "A", (-Ro * 0.25, -60, zs), (-Ro * 0.25, 60, zs), 0)
    p.vs("planta", on, "bottom", lv=(1, 1, 1, 1), extra=(20, 10, 60, 10), draw=planta, hatch=False, w=2.0, auto=False,
         title=f"VISTA INFERIOR (cara de deslizamiento): {D['semidiscos']} SEMIDISCOS, CJP SOBRE EL EJE x")
    # detalle B: corte por un avellanado del anillo A1 (copia girada con el tornillo sobre +x)
    b1 = BG[0]["bolts"][0]
    a1 = math.degrees(math.atan2(float(b1["y"]), float(b1["x"])))
    r1 = float(b1["r"])
    kd = _crop(ctx, on, "_B", r1, 0.0, 45.0, zs - 2, g.z0 + 2, rot=-a1)

    def det(V, p):
        s.line(V.P(r1, 0, zs - 6), V.P(r1, 0, g.z0 + 6), "EJE")
        V.dimh((r1 - dk / 2, 0, zs), (r1 + dk / 2, 0, zs), "bottom", 0, on=kd, text=f"Ø{fm(dk, 0)} (avellanado 90°)")
        V.dimh((r1 - dc / 2, 0, g.z0), (r1 + dc / 2, 0, g.z0), "top", 0, on=kd, text=f"Ø{fm(dc, 0)}")
        V.dimv((r1 + 30, 0, zs), (r1 + 30, 0, g.z0), "right", 0, on=kd, text=f"{fm(t, 0)}")
        V.dimv((r1 - dk / 2, 0, zs), (r1 - dk / 2, 0, zs + rec), "left", 0, on=kd, text=f"{fm(rec, 1)} (cabeza bajo la cara)")
    p.gd_in("detB", "surf", "flat", "0,20", None, at=[(r1 + 28, 0, zs), (r1 - 28, 0, zs), (r1 + 20, 0, zs)], d=(0, -1))
    if kd:
        p.vs("detB", kd, "front", cut=CUT_Y, center=(r1, 0, zs + t / 2), win=(-40, -t / 2 - 10, 40, t / 2 + 10), lv=(1, 1, 1, 1), extra=(30, 0, 20, 0), draw=det, hs=0.25, w=0.9, maxs=5.0,
             auto=False, title="DETALLE B: CORTE POR UN AVELLANADO (cara de deslizamiento abajo)")
    # corte A-A transversal a la CJP
    xa = -Ro * 0.25
    ka = _crop(ctx, on, "_A", xa, 0.0, 40.0, zs - 2, g.z0 + 2)

    def corA(V, p):
        V.dimv((xa, 30, zs), (xa, 30, g.z0), "right", 0, on=ka, text=f"{fm(t, 0)}")
        w_sym(p, jc, V, (xa, 0, g.z0), (40, 22), extra_tail=["esmerilada a ras ambas caras"])
    if ka:
        p.vs("corA", ka, "right", cut=((xa, 0, 0), (-1, 0, 0)), center=(xa, 0, zs + t / 2), win=(-40, -t / 2 - 10, 40, t / 2 + 10), lv=(1, 1, 1, 1), extra=(10, 0, 60, 0), draw=corA, hs=0.25, w=0.8, maxs=5.0,
             auto=False, title="CORTE A-A: JUNTA ENTRE SEMIDISCOS (CJP a ras)")
    add_prep(p, "det_j", wd(ctx, jc), title=f"DETALLE {jc}: PREPARACIÓN DE LA CJP DE LOS SEMIDISCOS (t = {fm(t, 0)})")
    rows = []
    for i, gr in enumerate(BG):
        rosca = (f"ciega en el anillo inferior: taladro {fm(gr['prof'], 0)}, rosca útil {fm(gr['rosca'], 0)}" if (gr["anillo"] or gr["ciego"]) else f"pasante en la plancha inferior (e = {fm(gr['t_pieza'], 0)})")
        rows.append([f"A{i + 1}", fm(gr["r"], 0), str(gr["n"]), _ang_txt(gr), rosca, f"M{fm(T['d'], 0)}×{fm(gr['L'], 0)}"])
    p.table_block("PATRÓN DE AVELLANADOS POR ANILLO (ángulos desde +x, antihorario; teóricamente exactos)", [("Anillo", 12, "C"), ("R [mm]", 14, "R"), ("Cant", 10, "C"), ("Ángulos", 70, "L"),
                  ("Rosca en la mesa", 62, "L"), ("Tornillo", 18, "L")], rows)
    p.table_block("DATOS DEL DISCO (núcleo BX)", [("Dato", 70, "L"), ("Valor", 110, "L")],
                  [["Material", D["material"]], ["Espesor t (requerido)", f"{fm(t, 1)} ({fm(D['t_req'], 2)}; cabeza {fm(D['t_cabeza'], 1)})"], ["Masa del disco / semidisco", f"{f(D['masa'], 1)} / {f(D['masa_semidisco'], 1)} kg"],
                   ["Línea de la CJP", D["linea_cjp"]], ["Largo de la CJP", f"{f(D['cjp']['largo'])} mm"], ["Bordes mínimos de los tornillos", f"exterior {fm(T['e_min_ext'], 0)}, interior {fm(T['e_min_int'], 0)}"],
                   ["Malla de tornillos (paso / separación mínima)", f"{fm(T['paso_malla'], 0)} / {fm(T['s_min'], 1)} mm"]])
    p.tables([jc])
    nts = [f"{D['semidiscos']} semidiscos R{fm(Ri, 0)}…R{fm(Ro, 0)} × {fm(t, 0)} de {D['material']}: " + bx_notas.fab_txt(g, "disco") + ".",
           f"Corte de cada semidisco con plasma (ISO 9013 clase 3) con el borde de la CJP preparado en V 60° ({jc}); presentar los semidiscos sobre una mesa plana con respaldo cerámico; la CJP queda sobre el eje x (nervio de 0°/180° de la mesa).",
           f"CJP {jc}: {D['cjp']['tipo']}; {D['cjp']['norma']}; aporte {D['cjp']['aporte']}. Esmerilar a ras ambas caras: {D['cjp']['acabado']}. END: {D['cjp']['END']}.",
           f"Acabado: {D['acabado']}.",
           f"Avellanados: {T['avellanado']}; cabeza {fm(rec, 1)} bajo la cara de deslizamiento. {T['nota']}.",
           "Decapado y pasivado de la zona soldada (ASTM A380/A967); marcar el código en la cara superior (contra la mesa), nunca en la cara de deslizamiento."]
    p.notes([bx_notas.limpia(ctx, x) for x in nts], gd=[("flat", "0,20", None, "Planitud de la cara de deslizamiento una vez atornillado a la mesa (copia la cara inferior planeada de la mesa)")])
    p.build()
    return p.h


# ------------------------------------------------------------------------------------------------ INT-018: portador
def sheet_bx_portador(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    X = g.bx
    POR = X["portador"]
    t = float(POR["t"])
    Rci, Rco = float(POR["R_int"]), float(POR["R_ext"])
    F = pforma(X)
    dh = F["nom"]
    tb = g.tb
    zt = tb + t
    p = Pieza(ctx, ["int_bx_portador"], "INTERFAZ BX: PORTADOR DE PASTILLAS (PLANCHA A PLASMA HD, SOLDADA A LA BASE)", fmt="A1")
    s = p.s
    on = ["int_bx_portador"]
    tit_, cols_, rows_, AN = tabla_posiciones(X)
    SI = sitios(X)
    jE, jI = J(ctx, "borde exterior"), J(ctx, "borde interior")

    def planta(V, p):
        s.line(V.P(-Rco - 25, 0, zt), V.P(Rco + 25, 0, zt), "EJE")
        s.line(V.P(0, -Rco - 25, zt), V.P(0, Rco + 25, zt), "EJE")
        for (r_, ss_) in (AN or []):
            s.pline([V.P(r_ * math.cos(a), r_ * math.sin(a), zt) for a in [2 * math.pi * k / 160 for k in range(161)]], "EJE")
        V.dim_dia((0, 0, zt), Rco, 128, on=on, text=f"Ø{f(2 * Rco)} (R{fm(Rco, 0)})", ext=22)
        V.dim_dia((0, 0, zt), Rci, 300, on=on, text=f"Ø{f(2 * Rci)} (R{fm(Rci, 0)})", ext=40)
        S0 = max([S_ for S_ in SI if not S_["rec"]], key=lambda S_: S_["hy"] - abs(S_["hx"]))
        nr_ = sum(1 for S_ in SI if S_["rec"])
        lin_ = [f"{POR['agujeros']['n']} × {ptxt(F, dh)} ±{fm(P['bx_tol_h'], 2)} (plasma HD)", ("anillos P1…P" + str(len(AN)) + ": tabla") if AN else "centros: tabla por filas"] + \
               ([f"{nr_} recortados por R{fm(F['corona'][0], 0)}…R{fm(F['corona'][1], 0)} (tabla)"] if nr_ else [])
        if F["sq"]:
            a_ = math.radians(S0["rot"])
            V.note_pt((S0["hx"] + dh / 2 * math.cos(a_), S0["hy"] + dh / 2 * math.sin(a_), zt), (30, 30), lin_[0], on=on, lines=lin_)
        else:
            V.note_hole((S0["hx"], S0["hy"], zt), dh / 2, 60, lin_[0], ext=30, on=on, lines=lin_)
        for i, (r_, ss_) in enumerate(AN or []):
            S1 = min(ss_, key=lambda S_: abs(math.degrees(math.atan2(S_["hy"], S_["hx"])) - 90.0))
            s.text(f"P{i + 1}", V.P(S1["hx"] + dh / 2 + 6, S1["hy"], zt), T_N, "MIDDLE_LEFT")
        p.cut_mark("planta", "A", (Rci - 20, -1, zt), (Rco + 30, -1, zt), -90)
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(20, 10, 40, 10), draw=planta, hatch=False, w=2.0, auto=False, title="PLANTA (cara superior)")
    # corte A-A radial con rotura, por el eje x (agujeros de los anillos sobre +x quedan cortados)
    def corte(V, p):
        V.dimv((Rco, 0, tb), (Rco, 0, zt), "right", 0, on=on, text=f"{fm(t, 0)}")
        w_out(p, jE, V, (Rco, 0, tb + 1), "right", dy=-14)
        w_out(p, jI, V, (Rci, 0, tb + 1), "left", dy=-14)
    p.gd_in("corte", "surf", "flat", "1", None, at=[(Rco - 40, 0, zt), (Rci + 40, 0, zt), (0.5 * (Rci + Rco), 0, zt)], d=(0, 1))
    p.vs("corte", on, "front", cut=((0, -0.5, 0), (0, 1, 0)), win=(Rci - 20, tb - 10, Rco + 20, zt + 10), lv=(1, 2, 2, 1), extra=(60, 0, 60, 0), draw=corte, hs=0.5, w=1.2, auto=False,
         title="CORTE A-A (radial por el eje x)")
    for i, j_ in enumerate((jE,)):
        add_prep(p, f"det_j{i}", wd(ctx, j_), t1=t, t2=g.tb, both=False, lab1=f"{fm(t, 0)} (portador)")
    p.table_block(tit_, cols_, rows_)
    rr_ = tabla_recortadas(X)
    if rr_:
        p.table_block(f"AGUJEROS RECORTADOS: contorno = {F['forma']} ∩ corona R{fm(F['corona'][0], 0)}…R{fm(F['corona'][1], 0)} (misma forma en la pastilla)",
                      [("N.°", 10, "C"), ("Centro x; y", 40, "L"), ("Fracción", 18, "R"), ("Tornillo x; y", 40, "L")], rr_)
    PT = POR["patron"]
    p.table_block("DATOS DEL PORTADOR (núcleo BX)", [("Dato", 70, "L"), ("Valor", 110, "L")],
                  [["Material", POR["material"]], ["Espesor", f"{fm(t, 0)}"], ["Patrón", f"{PT['tipo']}, paso {fm(POR['paso'], 0)}, ligamento {fm(POR['ligamento'], 0)} mm"],
                   ["Agujeros de soldadura (tapones)", f"{POR['tapones']['n']}" + (f" × Ø{fm(POR['tapones']['d'], 0)}" if POR["tapones"]["n"] else "")],
                   ["Filetes perimetrales", f"z{fm(POR['filetes']['w'], 0)} en R{fm(POR['filetes']['exterior']['R'], 0)} y R{fm(POR['filetes']['interior']['R'], 0)}"],
                   ["Masa (plancha / filetes)", f"{f(POR['masa_plancha'], 1)} / {f(POR['masa_filetes'], 2)} kg"]])
    p.tables([w["id"] for w in ctx.welds if w["id"] in ("J31", "J32", "J33")])
    sec = bx_notas._pasos_secuencia(POR["secuencia"])
    nts = [f"Plancha {fm(t, 0)} de {POR['material']}: {POR['corte']}. " + bx_notas.fab_txt(g, "portador") + ".",
           f"Agujeros {ptxt(F, dh)} ±{fm(P['bx_tol_h'], 2)}" + (" orientados según la tabla" if F["sq"] else "") + f" cortados con plasma de alta definición (sin mecanizar); ligamento mínimo entre agujeros {fm(POR['ligamento'], 0)} mm; eliminar escoria y rebaba del borde superior de cada agujero (la pastilla entra a presión).",
           "Secuencia (núcleo): " + " ".join(f"{i + 1}) {x}" for i, x in enumerate(sec)) + ".",
           f"Filetes perimetrales {jE} (exterior) y {jI} (interior) z{fm(POR['filetes']['w'], 0)}, continuos, en tramos alternados para limitar la distorsión.",
           "Sin pintura en la cara superior ni en las paredes de los agujeros (contacto con el UHMW)."]
    p.notes([bx_notas.limpia(ctx, x) for x in nts], gd=[("flat", "1", None, "Planitud de la cara superior del portador soldado (la cara de apoyo de las pastillas es la base planeada)")])
    p.build()
    return p.h


# ------------------------------------------------------------------------------------------------ INT-019: pastilla
def sheet_bx_pastilla(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    X = g.bx
    PAS = X["pastillas"]
    TP, AJ = PAS["tornillo"], PAS["ajuste"]
    F = pforma(X)
    d, dt, H, hp = F["nom"], F["pieza"], float(PAS["H"]), float(PAS["h_p"])
    dk, dh = float(PAS["cabeza"]["d_k"]), float(PAS["agujero_tornillo"])
    rec = float(PAS["cabeza"]["cara_superior_cabeza_bajo_cara"])
    tb = g.tb
    SI = sitios(X)
    S0 = next(S_ for S_ in SI if not S_["rec"] and abs(S_["sx"] - S_["hx"]) < 1e-6 and abs(S_["sy"] - S_["hy"]) < 1e-6)     # pastilla entera (tornillo al centro)
    x0_, y0_ = S0["hx"], S0["hy"]
    nk = ctx.local("int_bx_pastilla", "int_bx_pastilla_1", near=(x0_, y0_, tb + H / 2), r=d / 4, shift=(-x0_, -y0_, -tb), rot=-S0["rot"])
    p = Pieza(ctx, ["int_bx_pastilla"], "INTERFAZ BX: PASTILLA DE UHMW-PE (DETALLE, AJUSTE, TORNILLO Y SALIENTE)", fmt="auto")
    s = p.s
    on = [nk]
    p.iso_keys = [nk]

    def corte(V, p):
        s.line(V.P(0, 0, -6), V.P(0, 0, H + 6), "EJE")
        V.dimh((-d / 2, 0, H / 2), (d / 2, 0, H / 2), "bottom", 0, on=on, text=f"{ptxt(F, dt, 2, pieza=True).split(' (')[0]} {(PAS['tolerancias'].get('d') or PAS['tolerancias'].get('lado') or '')} (agujero {ptxt(F, d).split(' (')[0]}: interferencia {fm(AJ['delta'], 2)})")
        V.dimv((d / 2 - 3, 0, 0), (d / 2 - 3, 0, H), "right", 0, on=on, text=f"{fm(H, 2)} {PAS['tolerancias']['H']}")
        V.dimh((-dk / 2, 0, H), (dk / 2, 0, H), "top", 0, on=on, text=f"Ø{fm(dk, 0)} (cabeza)")
        V.dimh((-dh / 2, 0, 0), (dh / 2, 0, 0), "bottom", 1, on=on, text=f"Ø{fm(dh, 0)} pasante")
        V.dimv((-dk / 2, 0, H - rec), (-dk / 2, 0, H), "left", 0, on=on, text=f"{fm(rec, 1)}")
    p.vs("corte", on, "front", cut=CUT_Y, lv=(2, 2, 2, 2), extra=(10, 0, 30, 0), draw=corte, hs=0.5, w=1.6, auto=False, title="CORTE A-A (pastilla terminada)")

    def planta(V, p):
        s.centerlines(V.P(0, 0, H), d / 2 * V.scale, 6)
        p.cut_mark("planta", "A", (-d / 2 - 12, 0, H), (d / 2 + 12, 0, H), 90)
        V.note_pt((d / 2 - 0.5, 0, H - 0.5), (-60, 34), f"Chaflanes {PAS['chaflan_superior']} (arriba) y {PAS['chaflan_inferior']} (abajo)", on=on)
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 40, 0), draw=planta, hatch=False, w=0.8, auto=False, title="PLANTA")
    # detalle de montaje: corte por una pastilla montada (base, portador, pastilla, tornillo y disco)
    keys = ["base_plancha", "int_bx_portador", "int_bx_pastilla", "int_bx_disco_mesa"]
    Sm = next((S_ for S_ in SI if not S_["rec"] and abs(S_["hy"]) > 1.0 and S_["sx"] == S_["hx"]), S0)          # pastilla entera fuera de la línea de la CJP (y = 0)
    am = math.degrees(math.atan2(Sm["hy"], Sm["hx"]))
    x0_, y0_ = math.hypot(Sm["hx"], Sm["hy"]), 0.0
    sw_ = semiancho(F, Sm["rot"] - am) if F["sq"] else d / 2
    km = _crop(ctx, keys, "_M", x0_, 0.0, sw_ + 30, 0, g.z0 + 1, rot=-am)
    zp = tb + float(X["portador"]["t"])

    def mont(V, p):
        _tornillo(s, V, x0_, tb + H - rec, float(TP["d"]), dk, float(TP["L"]), -1)
        V.dimv((x0_ + sw_ + 12, y0_, zp), (x0_ + sw_ - 3, y0_, tb + H), "right", 0, on=km, text=f"{fm(hp, 2)} (saliente)")
        V.dimv((x0_ + sw_ + 20, y0_, tb), (x0_ + sw_ + 20, y0_, zp), "right", 1, on=km, text=f"{fm(float(X['portador']['t']), 0)} (portador)")
    if km:
        p.vs("mont", km, "front", cut=CUT_Y, center=(x0_, y0_, (tb + g.z0) / 2), win=(-sw_ - 30, -(g.z0) / 2 - 6, sw_ + 30, g.z0 / 2 + 6),
             lv=(1, 1, 3, 1), extra=(0, 0, 40, 0), draw=mont, hs=0.25, w=1.2, auto=False,
             title="DETALLE DE MONTAJE: PASTILLA EN EL PORTADOR, TORNILLO EN LA BASE Y DISCO ENCIMA")
    p.table_block("AJUSTE Y RETENCIÓN (núcleo BX)", [("Dato", 78, "L"), ("Valor", 100, "L")],
                  [["Forma", F["forma"] + (f", esquinas R{fm(F['r_esq_p'], 1)} (agujero R{fm(F['r_esq'], 1)})" if F["r_esq"] else "")], ["Agujero del portador / pastilla terminada", f"{ptxt(F, d).split(' (')[0]} ±{fm(P['bx_tol_h'], 2)} / {ptxt(F, dt, 2, pieza=True).split(' (')[0]} {(PAS['tolerancias'].get('d') or PAS['tolerancias'].get('lado') or '')}"], ["Interferencia nominal (mín. a 20 °C)", f"{fm(AJ['delta'], 2)} ({fm(AJ['delta_min_20'], 2)}) mm"],
                   ["Rango de interferencia admitido", f"{fm(AJ['rango'][0], 2)} … {fm(AJ['rango'][1], 2)} mm"], ["Holgura en frío (−) / deformación a T máx.", f"{fm(AJ['holgura_frio'], 3)} mm / {fm(AJ['eps_caliente'] * 100, 2)} %"],
                   ["Presión de ajuste a 20 °C", f"{fm(AJ['p_ajuste_20'], 2)} MPa"], ["Saliente sobre el portador", f"{fm(hp, 2)} mm"],
                   ["Tornillo", TP["designacion"]], ["Cabeza bajo la cara", f"{fm(rec, 1)} mm (cara superior de la cabeza a z = {fm(TP['z_cara_cabeza'], 2)} desde la base)"],
                   ["Engrane / taladro ciego / rosca útil / remanente", f"{fm(TP['engrane'], 1)} / {fm(TP['taladro_ciego'], 0)} / {fm(TP['rosca_util'], 0)} / {fm(TP['remanente'], 0)} mm"],
                   ["Masa unitaria / total", f"{fm(PAS['masa_unit'], 3)} / {f(PAS['masa_total'], 1)} kg ({PAS['n']} pastillas)"], ["p máx. / PV máx.", f"{fm(PAS['p_max'], 2)} MPa / {fm(PAS['PV_max'], 3)}"]])
    if tabla_recortadas(X):
        p.table_block("PASTILLAS RECORTADAS (tipos: contorno = " + F["forma"] + f" ∩ corona R{fm(F['corona'][0], 0)}…R{fm(F['corona'][1], 0)}; tabla de centros en {_cc(ctx, 'int_bx_portador')})",
                      [("N.°", 10, "C"), ("Centro x; y", 40, "L"), ("Fracción", 18, "R"), ("Tornillo x; y", 40, "L")], tabla_recortadas(X))
    p.tables([])
    nts = [f"{PAS['n']} pastillas de {PAS['material']}: " + (PAS.get("proceso") or bx_notas.fab_txt(g, "uhmw")) + ".",
           f"Pastilla {F['forma']} {ptxt(F, dt, 2, pieza=True)} {(PAS['tolerancias'].get('d') or PAS['tolerancias'].get('lado') or '')} para el agujero {ptxt(F, d)} del portador (interferencia {fm(AJ['delta'], 2)} mm); alto {fm(H, 2)} {PAS['tolerancias']['H']}; chaflanes {PAS['chaflan_superior']} arriba y {PAS['chaflan_inferior']} abajo.",
           f"Agujero Ø{fm(dh, 0)} pasante y avellanado 90° Ø{fm(dk, 0)} con la cabeza {fm(rec, 1)} bajo la cara superior (el disco desliza sobre el UHMW, nunca sobre la cabeza).",
           f"Montaje: {AJ['montaje']}. Tornillo {TP['designacion']} en la rosca ciega de la base: {TP['apriete']}.",
           f"Taladro ciego de la base Ø de macho M{fm(TP['d'], 0)}, prof. {fm(TP['taladro_ciego'], 0)}, rosca útil {fm(TP['rosca_util'], 0)}, remanente {fm(TP['remanente'], 0)} (BAS-001).",
           "Sin tratamiento ni pintura; almacenar a la sombra; reemplazo de a una con la mesa izada."]
    p.notes([bx_notas.limpia(ctx, x) for x in nts], gd=[("par", "0,05", "A", "Caras superior e inferior paralelas (A = cara inferior, apoyo en la base)")])
    p.datum_in("corte", "surf", "A", at=[(-d / 2 + 15, 0, 0), (d / 2 - 15, 0, 0), (-d / 4, 0, 0)], d=(0, -1))
    p.gd_in("corte", "surf", "par", "0,05", "A", at=[(d / 2 - 15, 0, H), (-d / 2 + 15, 0, H), (d / 4, 0, H)], d=(0, 1))
    p.build()
    return p.h


# ------------------------------------------------------------------------------------------------ CON-012 BX: conjunto y detalle de montaje de la interfaz
def sheet_interfaz_conj_bx(ctx):
    from hojas_con import Conj, balloons_auto, alias, mats
    g, P, m = ctx.g, ctx.P, ctx.m
    X = g.bx
    D, POR, PAS = X["disco"], X["portador"], X["pastillas"]
    T, TP = D["tornillos"], PAS["tornillo"]
    ks = [p.key for p in m.parts if p.sub == "INT"]
    c = Conj(ctx, 12, ks, "CONJUNTO DE LA INTERFAZ BX: PORTADOR, PASTILLAS Y DISCO ATORNILLADO — DETALLE DE MONTAJE (CORTES)", material="Ver despiece", trat="Ver despiece")
    s = c.s
    tb, z0 = g.tb, g.z0
    zt = tb + float(POR["t"])
    base_k = ["int_bx_portador", "int_bx_pastilla"]
    sh = ctx.sh(*base_k)

    def planta(V, c):
        balloons_auto(c, V, base_k, gap=12, off=16)
        s.pline([V.P(float(D["R_ext"]) * math.cos(a), float(D["R_ext"]) * math.sin(a), zt) for a in [2 * math.pi * k / 160 for k in range(161)]], "OCU")
        s.line(V.P(-float(D["R_ext"]) - 20, 0, zt), V.P(float(D["R_ext"]) + 20, 0, zt), "EJE")
        s.text("CJP del disco (eje x)", V.P(-float(D["R_ext"]) * 0.8, 8, zt), T_N, "BOTTOM_LEFT")
    c.vs("planta", sh, "top", lv=(1, 1, 1, 1), extra=(20, 10, 20, 10), draw=planta, mat=mats(ctx, base_k), hatch=False, auto=False, w=1.6,
         title="PLANTA DEL LADO BASE: PORTADOR Y PASTILLAS (disco de la mesa en trazo oculto)")
    # corte A: por una pastilla del anillo exterior girada sobre +x (no por la CJP)
    SI = sitios(X)
    Sa = max([S_ for S_ in SI if not S_["rec"] and abs(S_["hy"]) > 1.0 and S_["sx"] == S_["hx"]], key=lambda S_: math.hypot(S_["hx"], S_["hy"]))
    aa = math.degrees(math.atan2(Sa["hy"], Sa["hx"]))
    ra = math.hypot(Sa["hx"], Sa["hy"])
    keysA = ["base_plancha", "int_bx_portador", "int_bx_pastilla", "int_bx_disco_mesa", "mesa_plancha_inf", "mesa_anillo_inf"]
    F = pforma(X)
    sw_ = semiancho(F, Sa["rot"] - aa) if F["sq"] else F["nom"] / 2
    hw = sw_ + 60
    kA = _crop(ctx, keysA, "_CA", ra, 0.0, hw, -1, z0 + g.tpr + 2, rot=-aa)
    stack = g.stack

    def corA(V, c):
        with alias(ctx, "_CA"):
            balloons_auto(c, V, [k for k in kA if not k.startswith(("base_", "mesa_"))], gap=12, off=16)
        # tornillo de la pastilla sin cortar (ISO 128-50), dibujado desde el JSON, con su globo
        Hp_, rp_ = float(PAS["H"]), float(PAS["cabeza"]["cara_superior_cabeza_bajo_cara"])
        _tornillo(s, V, ra, tb + Hp_ - rp_, float(TP["d"]), float(PAS["cabeza"]["d_k"]), float(TP["L"]), -1)
        a_ = V.P(ra + float(TP["d"]) / 2, 0, tb - 4)
        c.h.balloon(m.get("int_bx_tor_pastilla").pos, a_, (V.ext[2] + 16, a_[1] - 6))
        z = tb
        xe = ra + sw_                       # pared del agujero del portador / canto de la pastilla
        for i_, l in enumerate(stack):
            nm = {"portador": "portador", "pastilla": "saliente de la pastilla", "disco_bx": "disco inoxidable"}[l["id"]]
            pa_, pb_ = ((xe + 8, 0, z), (xe + 8, 0, z + l["t"])) if l["id"] != "pastilla" else ((xe, 0, z), (xe - 1.5, 0, z + l["t"]))
            V.dimv(pa_, pb_, "right", i_, on=kA, text=f"{fm(l['t'], 2)} ({nm})")
            z += l["t"]
        V.dimv((ra - sw_ - 8, 0, tb), (ra - sw_ - 8, 0, z0), "left", 0, on=kA, text=f"(δ = {fm(g.delta, 2)}: base–mesa)")
    if kA:
        c.vs("corA", ctx.sh(*kA), "front", cut=CUT_Y, center=(ra, 0, (tb + z0) / 2), win=(-hw, -(z0 - tb) / 2 - tb - 4, hw, (z0 - tb) / 2 + 30), lv=(2, 1, 4, 1), extra=(20, 0, 30, 0), draw=corA,
             mat={k: ctx.mat[k] for k in kA}, hs=0.25, w=1.4, auto=False,
             title=f"CORTE A-A: POR UNA PASTILLA DEL ANILLO R{fm(ra, 0)} (DETALLE DE MONTAJE)")
    # corte B: por un tornillo del disco (pasante en la plancha) y C: por uno ciego en el anillo inferior
    BG = bolt_groups(X)
    vistas_ = []
    for lab, sel in (("B", lambda gr: not (gr["anillo"] or gr["ciego"])), ("C", lambda gr: gr["anillo"] or gr["ciego"])):
        grs = [gr for gr in BG if sel(gr)]
        if not grs:
            continue
        gr = grs[-1]
        b = gr["bolts"][0]
        ab = math.degrees(math.atan2(float(b["y"]), float(b["x"])))
        rb = float(b["r"])
        kB = _crop(ctx, ["int_bx_disco_mesa", "mesa_plancha_inf", "mesa_anillo_inf", "int_bx_pastilla", "int_bx_portador"], "_C" + lab, rb, 0.0, 45.0, zt - 1, z0 + g.tpr + 2, rot=-ab)
        if not kB:
            continue

        def corB(V, c, kB=kB, lab=lab, gr=gr, rb=rb):
            with alias(ctx, "_C" + lab):
                balloons_auto(c, V, [k for k in kB if k.startswith("int_bx_disco_mesa")], gap=12, off=14)
            td_ = float(D["t"])
            _tornillo(s, V, rb, z0 - td_ + float(T["cabeza_bajo_cara"]), float(T["d"]), float(T["d_cabeza"]), float(gr["L"]), +1)
            a_ = V.P(rb + float(T["d"]) / 2, 0, z0 + 4)
            a_ = V.P(rb - float(T["d"]) / 2, 0, z0 + 4)
            c.h.balloon(m.get("int_bx_tor_mesa").pos, a_, (V.ext[0] - 14, a_[1] + 8))
        c.vs("cor" + lab, ctx.sh(*kB), "front", cut=CUT_Y, center=(rb, 0, z0), win=(-45, -12, 45, (g.tpr if (gr["anillo"] or gr["ciego"]) else g.tbo) + 12), lv=(1, 1, 1, 1), extra=(10, 0, 10, 0), draw=corB,
             mat={k: ctx.mat[k] for k in kB}, hs=0.25, w=0.8, auto=False,
             title=f"CORTE {lab}-{lab}: TORNILLO DEL DISCO EN R{fm(rb, 0)} (rosca {'ciega en el anillo inferior' if (gr['anillo'] or gr['ciego']) else 'pasante en la plancha inferior'})")
    rows = [[_cc(ctx, "int_bx_portador"), f"{POR['agujeros']['n']} agujeros {ptxt(F, F['nom'])}", f"e = {fm(POR['t'], 0)}", "base (soldado J31/J32)"],
            [_cc(ctx, "int_bx_pastilla"), f"{PAS['n']} pastillas {F['forma']}s {ptxt(F, F['pieza'], 2, pieza=True).split(' (')[0]} × {fm(PAS['H'], 2)}", f"saliente {fm(PAS['h_p'], 2)}", "base (a presión + tornillo)"],
            [_cc(ctx, "int_bx_tor_pastilla"), f"{TP['n']} × {TP['designacion'].split(' (')[0]}", f"engrane {fm(TP['engrane'], 1)}", "rosca ciega en la base"],
            [_cc(ctx, "int_bx_disco_mesa"), f"{D['semidiscos']} semidiscos R{fm(D['R_int'], 0)}…R{fm(D['R_ext'], 0)} (CJP J30)", f"e = {fm(D['t'], 0)}", "mesa (atornillado)"],
            [_cc(ctx, "int_bx_tor_mesa"), f"{T['n']} × {T['designacion_base'].split(' (')[0]}", f"{len(BG)} anillos", "roscas en la mesa (B-B, C-C)"]]
    c.table_block("COMPONENTES DE LA INTERFAZ BX", [("Código", 22, "L"), ("Elemento", 70, "L"), ("Dato", 30, "L"), ("Lado / fijación", 46, "L")], rows)
    ids = [w["id"] for w in ctx.welds if w["id"] in ("J30", "J31", "J32", "J33")]
    notes = [f"{g.interfaz_nombre}.", f"Pila de la interfaz desde la cara superior de la base: portador {fm(POR['t'], 0)} + saliente {fm(PAS['h_p'], 2)} + disco {fm(D['t'], 0)} = δ {fm(g.delta, 2)} mm (núcleo; {X['z']['nota']}).",
             f"Lado base: portador soldado ({', '.join(i for i in ids if i != 'J30')}), pastillas a presión ({PAS['ajuste']['montaje']}) y tornillos {TP['designacion']} ({TP['apriete']}).",
             f"Lado mesa: disco en {D['semidiscos']} semidiscos con CJP J30 sobre el eje x, atornillado con {T['n']} tornillos {T['designacion_base']} ({T['nota']}).",
             "Secuencia de armado: instructivo (pasos 4 y 5); piezas: INT-016 (disco), INT-018 (portador), INT-019 (pastilla); tabla de fabricación simplificada: GEN-026."]
    c.tail(ks, ids, [bx_notas.limpia(ctx, x) for x in notes])
    c.build()
    return c.h


# ------------------------------------------------------------------------------------------------ GEN-026: fabricación simplificada (antes → después) y verificaciones BX
def sheet_bx_fabricacion(ctx):
    from hojas_gen import Gen
    g = ctx.g
    X = g.bx
    c = Gen(ctx, 26, "TT300-BX: FABRICACIÓN SIMPLIFICADA (ANTES → DESPUÉS) Y VERIFICACIONES DE LA INTERFAZ")
    R = c.R["main"]
    w = R[2] - R[0]
    L = lambda t_: bx_notas.limpia(ctx, t_)
    rows = [[L(r["pieza"]), L(r["antes"]), L(r["despues"]), r["estado"], L(r["motivo"]), L(r["verificacion"])] for r in X.get("fabricacion") or []]
    out, last, y = c.table_pages([("Pieza / operación", 0.15 * w, "L"), ("Antes (opción B)", 0.18 * w, "L"), ("Después (BX)", 0.22 * w, "L"), ("Estado", 0.07 * w, "L"), ("Motivo", 0.19 * w, "L"),
                                  ("Verificación que lo respalda", 0.19 * w, "L")], rows, "TABLA DE FABRICACIÓN DEL NÚCLEO BX (bx.fabricacion): se aplica en las láminas, el despiece y las notas de proceso", "FABRICACIÓN BX", 26)
    num = lambda v_: fm(v_, 3) if isinstance(v_, (int, float)) else (str(v_) if v_ not in (None, "") else "—")
    vr = [[L(v["nombre"]), f"{num(v.get('dem'))} / {num(v.get('cap'))} {v.get('unidad') or ''}".strip(), fm(v["fu"], 2) if isinstance(v.get("fu"), (int, float)) else "—", v.get("estado", "—"), L(v.get("ref") or "")]
          for v in X.get("verificaciones") or []]
    cols = [("Verificación BX (núcleo)", 0.46 * w, "L"), ("Demanda / capacidad", 0.12 * w, "L"), ("FU", 0.05 * w, "R"), ("Estado", 0.06 * w, "L"), ("Referencia", 0.31 * w, "L")]
    _, left = last.s.table(R[0], y - 8, cols, vr, h=T_S, ymin=R[1] + 3, title="VERIFICACIONES DE LA INTERFAZ BX (estado del núcleo; «pend» = pendiente de dato o decisión)")
    n = 0
    while left:
        n += 1
        g2 = Gen(ctx, 26 + n, f"TT300-BX: VERIFICACIONES DE LA INTERFAZ (CONTINUACIÓN {n})")
        R2 = g2.R["main"]
        _, left = g2.s.table(R2[0], R2[3], cols, left, h=T_S, ymin=R2[1] + 3, title="VERIFICACIONES BX (continuación)")
        out = list(out) + [g2.h]
    return out
