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
from bx3d import bolt_groups, puck_groups, pforma, ptxt, porient, semiancho, sitios, tabla_posiciones, tabla_recortadas, modo_lamina, tapones_por_anillo, mat_portador

ACTIVO = False
# la lámina de la pieza de la mesa sale solo si la pieza existe: disco atornillado (modo 0, INT-016) o lámina soldada (modo 1, INT-021)
_PIEZAS = [("sheet_bx_disco", ["int_bx_disco_mesa"]), ("sheet_bx_lamina", ["int_bx_lamina"]), ("sheet_bx_portador", ["int_bx_portador"]), ("sheet_bx_pastilla", ["int_bx_pastilla"])]
_MESA_BX = ("int_bx_disco_mesa", "int_bx_lamina")          # piezas de la interfaz del lado mesa que se recortan reconstruidas desde el JSON (bx3d.disco_recorte)


def km_bx(ctx):
    """Clave de la pieza de la interfaz BX del lado mesa: lámina soldada (modo 1) o disco atornillado (modo 0)."""
    return "int_bx_lamina" if ctx.m.get("int_bx_lamina") else "int_bx_disco_mesa"


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
    import propuestas
    # textos de familia WPS sin la equivalencia S355 (el juego BX usa la calidad del núcleo: ASTM A572 Gr. 50)
    fam_ = propuestas.FAM_TXT.get("PJP-PASADOR")
    if fam_ and "S355/A572" in fam_[0]:
        propuestas.FAM_TXT["PJP-PASADOR"] = (fam_[0].replace("S355/A572", "ASTM A572 Gr. 50"), fam_[1])
    hojas_gen.sheet_bx_fabricacion = sheet_bx_fabricacion
    if "sheet_bx_fabricacion" not in hojas_gen.PLAN_GEN:
        hojas_gen.PLAN_GEN.append("sheet_bx_fabricacion")


# TT300-BX rev. 7c (mesa de plancha entera): los textos del núcleo sobre los pasadores de empuje (bloque pasadores_empuje del JSON, que el núcleo
# escribe para el disco + anillo) se adaptan a las planchas enteras. Solo con bx.mesa.plancha_entera (el núcleo y su JSON no cambian).
_ME_TXT = [("soldado a ambos anillos", "soldado a ambas planchas de la mesa"), ("agujero H7 de los anillos", "agujero H7 de las planchas enteras"),
           ("borde del agujero del anillo", "borde del agujero de la plancha"), ("caras interiores de los anillos", "caras interiores de las planchas"),
           ("entre anillos", "entre planchas"), ("en los anillos", "en las planchas"), ("de los anillos", "de las planchas"), ("del anillo", "de la plancha"), ("a anillo ", "a plancha ")]


def textos_mesa_entera(D):
    """Reemplaza «anillo» por «plancha» en los textos de pasadores_empuje del JSON (mesa de plancha entera); devuelve D."""
    if not ((D.get("bx") or {}).get("mesa") or {}).get("plancha_entera"):
        return D

    def tx(v):
        if isinstance(v, str):
            for a, b in _ME_TXT:
                v = v.replace(a, b)
            return v
        if isinstance(v, list):
            return [tx(x) for x in v]
        if isinstance(v, dict):
            return {k: tx(x) for k, x in v.items()}
        return v
    if D.get("pasadores_empuje"):
        D["pasadores_empuje"] = tx(D["pasadores_empuje"])
    import propuestas
    fam_ = propuestas.FAM_TXT.get("PJP-PASADOR")
    if fam_:
        propuestas.FAM_TXT["PJP-PASADOR"] = (tx(fam_[0]), fam_[1])
    return D


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
        if k in _MESA_BX:
            import bx3d
            sols = bx3d.disco_recorte(ctx.g, cx, cy, hw, z0, z1, rot)
        for so in ([] if k in _MESA_BX else sh.Solids()):
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


# ------------------------------------------------------------------------------------------------ INT-021: lámina inoxidable soldada (modo 1)
def _hatch(s, pts, ang=45.0, solid=False):
    s.pline(pts, "VIS", closed=True)
    if solid:
        s.hatch_poly(pts, solid=True)
    else:
        s.hatch_poly(pts, scale=0.35, angle=ang, pattern="ANSI31")


def _rotura(s, x, ya, yb):
    """Línea de rotura vertical (ISO 128-30) en x entre ya y yb (coordenadas de papel)."""
    ym = (ya + yb) / 2
    s.pline([(x, ya), (x, ym - 2.5), (x + 2.2, ym - 0.8), (x - 2.2, ym + 0.8), (x, ym + 2.5), (x, yb)], "FINA")


def _det_tapon(s, ox, oy, k, R, plano=None, jid=None):
    """Tapón de la lámina: sección por el eje con la mesa invertida (lámina arriba, cara espejo hacia arriba), agujero Ø d relleno en todo el
    espesor y fundido a la plancha, esmerilado a ras y pulido. Medidas del JSON (disco.tapones, disco.lamina) y de la plancha inferior (t_bot)."""
    d, t, hp, W = R["d"], R["t"], R["hp"], R["W"]
    P = lambda x, y: (ox + x * k, oy + y * k)
    y0 = 4.0
    yb, yt = y0 + hp, y0 + hp + t
    xc = W / 2
    _hatch(s, [P(0, y0), P(W, y0), P(W, yb), P(0, yb)], 0.0)
    _hatch(s, [P(0, yb), P(xc - d / 2, yb), P(xc - d / 2, yt), P(0, yt)], 90.0)
    _hatch(s, [P(xc + d / 2, yb), P(W, yb), P(W, yt), P(xc + d / 2, yt)], 90.0)
    fus = [P(xc - d / 2, yb), P(xc + d / 2, yb), P(xc + d / 2, yt), P(xc - d / 2, yt)]
    _hatch(s, fus, solid=True)
    pen = [P(xc - d / 2, yb), P(xc - d / 2 + 1.0, yb - 0.8), P(xc + d / 2 - 1.0, yb - 0.8), P(xc + d / 2, yb)]
    _hatch(s, pen, solid=True)
    s.line(P(xc, y0 - 2), P(xc, yt + 5), "EJE")
    _rotura(s, P(0, 0)[0], P(0, y0 - 1)[1], P(0, yb)[1])
    _rotura(s, P(W, 0)[0], P(0, y0 - 1)[1], P(0, yb)[1])
    s.dim(P(xc - d / 2, yt), P(xc + d / 2, yt), 8, f"Ø{fm(d, 0)}", "h")
    s.dim(P(W, yb), P(W, yt), 7, f"t = {fm(t, 0)}", "v")
    s.leader(P(xc + d / 4, yt), (P(W, 0)[0] + 6, P(0, yt)[1] + 2), "cara espejo: a ras ± 0,05, pulido Ra ≤ 0,4", dot=True)
    s.leader(P(xc, yb + t / 2), (P(W, 0)[0] + 6, P(0, yb)[1] - 6), f"relleno = t = {fm(R['rel'], 1)}, fundido a la plancha", dot=True)
    s.leader(P(W * 0.2, y0 + hp / 2), (P(W, 0)[0] + 6, P(0, y0)[1] - 4), f"plancha inferior e = {fm(R['tbo'], 0)} ({R['cM']})", dot=True)
    if plano is not None and jid:
        a = P(xc - d / 4, yt)
        plano.h.weld(jid, a, (P(W, 0)[0] + 8, P(0, yt)[1] + 14), sh=1)


def _det_costura(s, ox, oy, k, R, plano=None, jid=None, jid2=None):
    """Costura perimetral exterior: canto de la lámina retirado e del canto de la plancha, filete z de la lámina a la plancha (mesa invertida)."""
    t, z, e, hp, W = R["t"], R["z"], R["e"], R["hp"], R["W"]
    P = lambda x, y: (ox + x * k, oy + y * k)
    y0 = 4.0
    yb, yt = y0 + hp, y0 + hp + t
    xl = W - e - 4.0                 # canto de la lámina
    xp = W - 4.0                     # canto de la plancha (borde de la mesa)
    _hatch(s, [P(0, y0), P(xp, y0), P(xp, yb), P(0, yb)], 0.0)
    _hatch(s, [P(0, yb), P(xl, yb), P(xl, yt), P(0, yt)], 90.0)
    fil = [P(xl, yb), P(xl + z, yb), P(xl, yb + z)]
    _hatch(s, fil, solid=True)
    _rotura(s, P(0, 0)[0], P(0, y0 - 1)[1], P(0, yt + 1)[1])
    s.dim(P(xl, yt), P(xp, yt), 9, f"{fm(e, 0)} (retiro)", "h")
    s.dim(P(xl + z, yb), P(xl + z, yb + z), 6, f"z = {fm(z, 0)}", "v", outside=True)
    s.dim(P(0, yb), P(0, yt), -6, f"t = {fm(t, 0)}", "v")
    s.leader(P(xl + z * 0.3, yb + z * 0.3), (P(W, 0)[0] + 6, P(0, y0)[1] - 4), "por retroceso, tramos ≤ 150; a ras de la cara espejo", dot=True)
    if plano is not None and jid:
        a = P(xl + z * 0.35, yb + z * 0.35)
        plano.h.weld(jid, a, (P(W, 0)[0] + 8, P(0, yt)[1] + 14), sh=1, extra_tail=[f"exterior R{fm(R['Ro'], 0)}"])
    if plano is not None and jid2:
        a = P(xl + z * 0.2, yb + z * 0.6)
        plano.h.weld(jid2, a, (P(W, 0)[0] + 8, P(0, yt)[1] + 32), sh=1, extra_tail=[f"interior R{fm(R['Ri'], 0)} (ídem)"])


def _det_junta(s, ox, oy, k, R, plano=None, jid=None):
    """Junta a tope entre paneles: borde recto, separación de raíz 0–1, sobre la plancha (respaldo permanente), CJP esmerilada a ras."""
    t, hp, W, gap = R["t"], R["hp"], R["W"], 1.0
    P = lambda x, y: (ox + x * k, oy + y * k)
    y0 = 4.0
    yb, yt = y0 + hp, y0 + hp + t
    xc = W / 2
    _hatch(s, [P(0, y0), P(W, y0), P(W, yb), P(0, yb)], 0.0)
    _hatch(s, [P(0, yb), P(xc - gap / 2, yb), P(xc - gap / 2, yt), P(0, yt)], 90.0)
    _hatch(s, [P(xc + gap / 2, yb), P(W, yb), P(W, yt), P(xc + gap / 2, yt)], 90.0)
    cj = [P(xc - gap / 2 - 1.2, yt), P(xc - gap / 2, yb), P(xc + gap / 2, yb), P(xc + gap / 2 + 1.2, yt)]
    _hatch(s, cj, solid=True)
    pen = [P(xc - gap / 2, yb), P(xc - gap / 2 + 0.2, yb - 0.7), P(xc + gap / 2 - 0.2, yb - 0.7), P(xc + gap / 2, yb)]
    _hatch(s, pen, solid=True)
    s.line(P(xc, y0 - 2), P(xc, yt + 5), "EJE")
    _rotura(s, P(0, 0)[0], P(0, y0 - 1)[1], P(0, yt + 1)[1])
    _rotura(s, P(W, 0)[0], P(0, y0 - 1)[1], P(0, yt + 1)[1])
    s.dim(P(0, yb), P(0, yt), -7, f"t = {fm(t, 0)}", "v")
    s.leader(P(xc, yb + t * 0.5), (P(W, 0)[0] + 6, P(0, y0)[1] - 4), "raíz 0–1; CJP sobre la plancha (respaldo)", dot=True)
    s.leader(P(xc + 0.6, yt), (P(W, 0)[0] + 6, P(0, yt)[1] + 2), "a ras ± 0,05, pulida al grano del espejo", dot=True)
    if plano is not None and jid:
        a = P(xc - 0.5, yt)
        plano.h.weld(jid, a, (P(W, 0)[0] + 8, P(0, yt)[1] + 14), sh=1)


def sheet_bx_lamina(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    X = g.bx
    D = X["disco"]
    L, TP, CO = D["lamina"], D["tapones"], D["costura"]
    t = float(L.get("espesor") or D["t"])
    Ro, Ri = float(L["R_ext"]), float(L["R_int"])
    zs = g.z0 - t                       # cara de deslizamiento (espejo, inferior en servicio)
    d = float(TP["d"])
    jJ, jT = J(ctx, "Panel – panel"), J(ctx, "tapones Ø")
    jE, jI = J(ctx, "costura perimetral exterior"), J(ctx, "costura perimetral interior")
    g0 = float((D.get("despegue_panel") or {}).get("g0") or 0.2)
    p = Pieza(ctx, ["int_bx_lamina"], "INTERFAZ BX: LÁMINA INOXIDABLE ESPEJO SOLDADA A LA MESA (PANELES, JUNTA CJP, TAPONES Y COSTURAS)", fmt="A1")
    s = p.s
    on = ["int_bx_lamina"]
    AN = tapones_por_anillo(X)
    cM = _cc(ctx, "mesa_plancha_inf")

    def planta(V, p):
        s.line(V.P(-Ro - 25, 0, zs), V.P(Ro + 25, 0, zs), "EJE")
        s.line(V.P(0, -Ro - 25, zs), V.P(0, Ro + 25, zs), "EJE")
        for an in AN:
            s.pline([V.P(an["r"] * math.cos(a), an["r"] * math.sin(a), zs) for a in [2 * math.pi * k / 160 for k in range(161)]], "EJE")
            a_t = math.radians(263.0)
            s.text(f"T{an['i'] + 1}", V.P(an["r"] * math.cos(a_t), an["r"] * math.sin(a_t) + 12, zs), T_N, "BOTTOM_CENTER")
        V.dim_dia((0, 0, zs), Ro, 128, on=on, text=f"Ø{f(2 * Ro)} (R{fm(Ro, 0)})", ext=22)
        V.dim_dia((0, 0, zs), Ri, 300, on=on, text=f"Ø{f(2 * Ri)} (R{fm(Ri, 0)})", ext=40)
        # agujero de tapón acotado: el del anillo exterior más a la derecha y abajo en el papel (lejos de las cotas de Ø)
        q0 = max(AN[-1]["lista"], key=lambda q: V.P(float(q["x"]), float(q["y"]), zs)[0] - V.P(float(q["x"]), float(q["y"]), zs)[1])
        lin_ = [f"{TP['n']} × Ø{fm(d, 0)} para tapones {jT}", f"anillos T1…T{len(AN)}: tabla", "taladrados o punzonados, sin rebaba"]
        V.note_hole((float(q0["x"]), float(q0["y"]), zs), d / 2, -40, lin_[0], ext=30, on=on, lines=lin_)
        # juntas: los símbolos ISO 2553 van en los detalles de soldadura (escala 2:1); en la planta, referencias cortas
        xr_ = max((Ro * 0.5, -Ro * 0.5), key=lambda x_: V.P(x_, 0, zs)[0])
        a_ = V.P(xr_, 0, zs)
        s.leader(a_, (a_[0] + 14, a_[1] + 12), f"{jJ}: junta a tope CJP (detalle)", dot=True)
        a_ = V.P(Ro * math.cos(math.radians(-140)), Ro * math.sin(math.radians(-140)), zs)
        s.leader(a_, (a_[0] - 8 if a_[0] < V.P(0, 0, zs)[0] else a_[0] + 8, a_[1] - 10), f"{jE}: costura exterior (detalle)", dot=True)
        a_ = V.P(Ri * math.cos(math.radians(-140)), Ri * math.sin(math.radians(-140)), zs)
        s.leader(a_, (a_[0] + 12, a_[1] - 20), f"{jI}: costura interior", dot=True)
        for pn in L["paneles"]:
            ym = (float(pn["y0"]) + float(pn["y1"])) / 2
            s.text(f"PANEL {pn['id']}", V.P(-Ro * 0.42, ym, zs), T_N + 0.5, "MIDDLE_CENTER")
    p.vs("planta", on, "bottom", lv=(1, 0, 1, 0), extra=(30, 0, 60, 0), draw=planta, hatch=False, w=4.0, mins=0.1, auto=False,
         title=f"VISTA INFERIOR (cara espejo de deslizamiento): {L['n_paneles']} PANELES, JUNTA A TOPE CJP SOBRE y = " + ", ".join(fm(v, 0) for v in L["junta"].get("lineas_y") or [0]))
    # planitud de la cara espejo: marco sobre la cara (vista inferior), fuera de los anillos de tapones
    a_g = math.radians(-60.0)
    rg = 0.5 * (AN[0]["r"] + AN[1]["r"]) if len(AN) > 1 else 0.5 * (Ri + Ro)
    # candidatos: entre los dos primeros anillos de tapones y entre el 2.º y el 3.º, cada 15° (con menos pastillas la planta cambia y el primer lugar puede quedar ocupado)
    rgs = [rg] + ([0.5 * (AN[1]["r"] + AN[2]["r"])] if len(AN) > 2 else []) + [0.5 * (Ri + Ro)]
    cand = [(r_ * math.cos(a_g + math.radians(k)), r_ * math.sin(a_g + math.radians(k)), zs) for r_ in rgs for k in (0, 15, -15, 30, -30, 45, -45, 90, -90, 135, -135, 180)]
    p.gd_in("planta", "surf", "flat", "0,20", None, at=cand, d=(0, -1))
    Rd = dict(d=d, t=t, rel=float(TP.get("relleno") or t), hp=10.0, W=4.0 * d, tbo=float(g.tbo), cM=cM)
    Rc = dict(t=t, z=float(CO["w"]), e=float(L.get("retiro_borde") or 0.0), hp=10.0, W=4.0 * d, Ri=Ri, Ro=Ro)
    Rj = dict(t=t, hp=10.0, W=4.0 * d)
    H_row, GAP_ = 10.0 + t + 4.0, 20.0
    filas = [(_det_costura, Rc, (jE, jI), f"{jE}: costura perimetral exterior z{fm(Rc['z'], 0)} en R{fm(Ro, 0)} (ídem {jI} en R{fm(Ri, 0)})"),
             (_det_tapon, Rd, (jT,), f"{jT}: tapón Ø{fm(d, 0)}, relleno = t, esmerilado a ras"),
             (_det_junta, Rj, (jJ,), f"{jJ}: junta a tope CJP entre paneles, sobre la plancha")]

    def _dets(s_, ox, oy, k, pl):
        for n_, (fn_, R_, ids_, tit_) in enumerate(filas):
            oy_ = oy + n_ * (H_row + GAP_) * k
            fn_(s_, ox, oy_, k, R_, pl, *ids_)
            s_.text(tit_, (ox + R_["W"] / 2 * k, oy_ + 1.0 * k - 1.5), T_N, "TOP_CENTER")
    p.vs("det_w", [], "top", nat=(Rd["W"], 3 * H_row + 2 * GAP_), lv=(2, 3, 2, 2), extra=(0, 0, 100, 0), mins=2.0, maxs=2.0, w=0.8,
         title="DETALLES DE SOLDADURA DE LA LÁMINA (mesa invertida: cara espejo arriba)", custom=_dets)
    rows = []
    for an in AN:
        n_ = an["n"]
        dd = [an["angs"][i + 1] - an["angs"][i] for i in range(n_ - 1)]
        at = (f"{fm(an['angs'][0], 3)}° + {fm(360.0 / n_, 3)}°·k (k = 0…{n_ - 1})" if n_ > 1 and max(dd) - min(dd) < 0.02 else ", ".join(fm(a, 2) + "°" for a in an["angs"]))
        rows.append([f"T{an['i'] + 1}", fm(an["r"], 1), str(n_), at, fm(2 * math.pi * an["r"] / max(n_, 1), 1), fm(an["V"] / 1000.0, 2), "pista" if an["pista"] else "banda libre"])
    p.table_block("PATRÓN DE TAPONES POR ANILLO (centros; ángulos desde +x, antihorario; teóricamente exactos)",
                  [("Anillo", 12, "C"), ("R [mm]", 16, "R"), ("Cant", 10, "C"), ("Ángulos", 66, "L"), ("Paso [mm]", 16, "R"), ("V máx. [kN]", 18, "R"), ("Ubicación", 22, "L")], rows)
    fl = L["formato"]
    p.table_block("PANELES DE LA LÁMINA (franjas paralelas a x)", [("Panel", 12, "C"), ("Franja y [mm]", 30, "L"), ("Ancho × largo [mm]", 34, "L"), ("Formato", 28, "L"), ("Masa [kg]", 16, "R")],
                  [[pn["id"], f"{fm(pn['y0'], 0)} … {fm(pn['y1'], 0)}", f"{fm(pn['ancho'], 0)} × {fm(pn['largo'], 0)}", f"{fm(fl[0], 0)} × {fm(fl[1], 0)} × {fm(t, 0)}", fm(pn["masa"], 1)] for pn in L["paneles"]])
    p.table_block("DATOS DE LA LÁMINA Y DE SUS SOLDADURAS (núcleo BX)", [("Dato", 70, "L"), ("Valor", 110, "L")],
                  [["Material", D["material"]], ["Espesor t / efectivo t_e (sobreespesor de desgaste)", f"{fm(t, 1)} / {fm(D['t_e'], 2)} mm"],
                   ["Corona / retiro del borde", f"R{fm(Ri, 0)} … R{fm(Ro, 0)} / {fm(L.get('retiro_borde') or 0, 0)} mm"],
                   ["Tapones: Ø / relleno / paso / separación mín. / borde mín. (req.)", f"Ø{fm(d, 0)} / {fm(TP.get('relleno') or t, 1)} / {fm(TP['paso'], 0)} / {fm(TP['s_min'], 1)} / {fm(TP['e_min'], 1)} ({fm(TP['e_req'], 0)}) mm"],
                   ["Tapón: corte máx. / capacidad (aporte; lámina)", f"{fm(float(TP['V_max']) / 1000, 2)} / {fm(float(TP['cap']) / 1000, 2)} kN ({fm(float(TP['cap_soldadura']) / 1000, 2)}; {fm(float(TP['cap_lamina']) / 1000, 2)})"],
                   ["Costura z: flujo par + térmico / capacidad", f"z{fm(CO['w'], 0)}: {fm(CO['q_par'], 1)} + {fm(CO['q_termica'], 1)} / {fm(CO['cap_soldadura'], 1)} N/mm"],
                   ["Separación lámina–plancha admitida g₀", f"≤ {fm(g0, 2)} mm (galga)"], ["Masa total de la lámina", f"{f(D['masa'], 1)} kg"]])
    p.tables([w["id"] for w in ctx.welds if w["id"] in (jJ, jT, jE, jI)])
    sec = bx_notas._pasos_secuencia(D["fabricacion"])
    nts = [f"Lámina {D['material']}, e = {fm(t, 0)} mm: certificado EN 10204 3.1 (ASTM A240, colada identificada); film protector hasta el montaje (se retira solo en tapones, junta y costuras).",
           f"Corte: {L['n_paneles']} paneles del formato {fm(fl[0], 0)} × {fm(fl[1], 0)} (tabla) a láser o cizalla, margen {fm(L['margen_corte'], 0)} mm al borde del formato; contorno R{fm(Ri, 0)}…R{fm(Ro, 0)} ± 1; "
           f"borde de la junta recto y sin rebaba. {TP['n']} agujeros Ø{fm(d, 0)} (+0,3/0) taladrados o punzonados con plantilla, posición ± 1 (tabla de anillos).",
           "Secuencia de soldadura por zonas (núcleo): " + " ".join(f"{i + 1}) {x}" for i, x in enumerate(sec)) + ".",
           f"WPS: unión disímil 304 / ASTM A572 Gr. 50 con aporte {D['aporte'].split(':')[0]}: WPS y PQR CALIFICADOS según AWS D1.6/D1.6M:2017 (no precalificada); "
           "AWS D1.3/D1.3M:2018 como referencia del detalle de tapones en lámina ≤ 4,8 mm. Proceso 141 (o 135 pulsado) PROPUESTO; sin precalentar el inoxidable; interpase ≤ 150 °C.",
           f"Probeta de tapón ANTES de producción: lámina de {fm(t, 0)} sobre plancha de {fm(g.tbo, 0)} de la misma calidad, ≥ 3 tapones Ø{fm(d, 0)} con la WPS y la secuencia de producción; "
           f"macrografía (fusión a la plancha sin falta de fusión; ISO 5817-B) y ensayo de corte o arrancamiento ≥ {fm(float(TP['cap']) / 1000, 1)} kN por tapón (capacidad del cálculo); registrar en el PQR.",
           f"Planitud: separación lámina–plancha g₀ ≤ {fm(g0, 2)} mm con galga en todo el contorno de los paneles y entre tapones (golpeteo y galga) después de soldar; "
           "si se supera, retirar el tramo y volver a soldar (no se rellena con aporte).",
           f"Acabado: tapones ({jT}), junta ({jJ}) y costuras ({jE}, {jI}) esmerilados a ras ± 0,05 y pulidos al grano del espejo (Ra ≤ 0,4 µm). END: VT 100 % y PT 100 % después de esmerilar.",
           "Decapado y pasivado local (ASTM A380/A967); marcar el código en la cara contra la mesa antes de presentar, nunca en la cara espejo. Sin roscas ni tornillos en la mesa "
           "(la lámina reemplaza al disco atornillado INT-016/INT-017 del modo 0)."]
    p.notes([bx_notas.limpia(ctx, x) for x in nts], gd=[("flat", "0,20", None, "Planitud de la cara espejo una vez soldada (copia la cara inferior planeada de la mesa)")])
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
                  [["Material", mat_portador(X)], ["Espesor", f"{fm(t, 0)}"], ["Patrón", f"{PT['tipo']}, paso {fm(POR['paso'], 0)}, ligamento {fm(POR['ligamento'], 0)} mm"],
                   ["Agujeros de soldadura (tapones)", f"{POR['tapones']['n']}" + (f" × Ø{fm(POR['tapones']['d'], 0)}" if POR["tapones"]["n"] else "")],
                   ["Filetes perimetrales", f"z{fm(POR['filetes']['w'], 0)} en R{fm(POR['filetes']['exterior']['R'], 0)} y R{fm(POR['filetes']['interior']['R'], 0)}"],
                   ["Masa (plancha / filetes)", f"{f(POR['masa_plancha'], 1)} / {f(POR['masa_filetes'], 2)} kg"]])
    p.tables([w["id"] for w in ctx.welds if w["id"] in ("J31", "J32", "J33")])
    sec = bx_notas._pasos_secuencia(POR["secuencia"])
    nts = [f"Plancha {fm(t, 0)} de {mat_portador(X)}: {POR['corte']}. " + bx_notas.fab_txt(g, "portador") + ".",
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
    keys = ["base_plancha", "int_bx_portador", "int_bx_pastilla", km_bx(ctx)]
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
             title="DETALLE DE MONTAJE: PASTILLA EN EL PORTADOR, TORNILLO EN LA BASE Y " + ("LÁMINA DE LA MESA ENCIMA" if km_bx(ctx) == "int_bx_lamina" else "DISCO ENCIMA"))
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
           f"Agujero Ø{fm(dh, 0)} pasante y avellanado 90° Ø{fm(dk, 0)} con la cabeza {fm(rec, 1)} bajo la cara superior (" + ("la lámina de la mesa" if km_bx(ctx) == "int_bx_lamina" else "el disco") + " desliza sobre el UHMW, nunca sobre la cabeza).",
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
    LAM = km_bx(ctx) == "int_bx_lamina"
    c = Conj(ctx, 12, ks, "CONJUNTO DE LA INTERFAZ BX: PORTADOR, PASTILLAS Y " + ("LÁMINA SOLDADA A LA MESA" if LAM else "DISCO ATORNILLADO") + " — DETALLE DE MONTAJE (CORTES)", material="Ver despiece", trat="Ver despiece")
    s = c.s
    tb, z0 = g.tb, g.z0
    zt = tb + float(POR["t"])
    base_k = ["int_bx_portador", "int_bx_pastilla"]
    sh = ctx.sh(*base_k)

    def planta(V, c):
        balloons_auto(c, V, base_k, gap=12, off=16)
        s.pline([V.P(float(D["R_ext"]) * math.cos(a), float(D["R_ext"]) * math.sin(a), zt) for a in [2 * math.pi * k / 160 for k in range(161)]], "OCU")
        s.line(V.P(-float(D["R_ext"]) - 20, 0, zt), V.P(float(D["R_ext"]) + 20, 0, zt), "EJE")
        s.text("junta CJP de la lámina (eje x)" if LAM else "CJP del disco (eje x)", V.P(-float(D["R_ext"]) * 0.8, 8, zt), T_N, "BOTTOM_LEFT")
    c.vs("planta", sh, "top", lv=(1, 1, 1, 1), extra=(20, 10, 20, 10), draw=planta, mat=mats(ctx, base_k), hatch=False, auto=False, w=1.6,
         title="PLANTA DEL LADO BASE: PORTADOR Y PASTILLAS (" + ("lámina" if LAM else "disco") + " de la mesa en trazo oculto)")
    # corte A: por una pastilla del anillo exterior girada sobre +x (no por la CJP)
    SI = sitios(X)
    Sa = max([S_ for S_ in SI if not S_["rec"] and abs(S_["hy"]) > 1.0 and S_["sx"] == S_["hx"]], key=lambda S_: math.hypot(S_["hx"], S_["hy"]))
    aa = math.degrees(math.atan2(Sa["hy"], Sa["hx"]))
    ra = math.hypot(Sa["hx"], Sa["hy"])
    keysA = ["base_plancha", "int_bx_portador", "int_bx_pastilla", km_bx(ctx), "mesa_plancha_inf", "mesa_anillo_inf"]
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
            nm = {"portador": "portador", "pastilla": "saliente de la pastilla", "disco_bx": "lámina inoxidable" if LAM else "disco inoxidable"}[l["id"]]
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
    if LAM:
        AN = tapones_por_anillo(X)
        TPl = D["tapones"]
        qb = AN[0]["lista"][0]
        ab = math.degrees(math.atan2(float(qb["y"]), float(qb["x"])))
        rb = math.hypot(float(qb["x"]), float(qb["y"]))
        kB = _crop(ctx, ["int_bx_lamina", "mesa_plancha_inf"], "_CB", rb, 0.0, 40.0, z0 - float(D["t"]) - 1, z0 + g.tbo + 2, rot=-ab)
        if kB:
            def corBl(V, c, kB=kB, rb=rb):
                with alias(ctx, "_CB"):
                    balloons_auto(c, V, [k for k in kB if k.startswith("int_bx_lamina")], gap=12, off=14)
                w_out(c, J(ctx, "tapones Ø"), V, (rb - float(TPl["d"]) / 4, 0, z0 - float(D["t"])), "right", dy=12)
            c.vs("corB", ctx.sh(*kB), "front", cut=CUT_Y, center=(rb, 0, z0), win=(-40, -12, 40, g.tbo + 12), lv=(1, 1, 1, 1), extra=(10, 0, 40, 0), draw=corBl,
                 mat={k: ctx.mat[k] for k in kB}, hs=0.25, w=0.8, auto=False,
                 title=f"CORTE B-B: TAPÓN DE LA LÁMINA EN R{fm(rb, 0)} (agujero Ø{fm(TPl['d'], 0)} antes de soldar; banda libre entre pistas de pastillas)")
    rows = [[_cc(ctx, "int_bx_portador"), f"{POR['agujeros']['n']} agujeros {ptxt(F, F['nom'])}", f"e = {fm(POR['t'], 0)}", "base (soldado J31/J32)"],
            [_cc(ctx, "int_bx_pastilla"), f"{PAS['n']} pastillas {F['forma']}s {ptxt(F, F['pieza'], 2, pieza=True).split(' (')[0]} × {fm(PAS['H'], 2)}", f"saliente {fm(PAS['h_p'], 2)}", "base (a presión + tornillo)"],
            [_cc(ctx, "int_bx_tor_pastilla"), f"{TP['n']} × {TP['designacion'].split(' (')[0]}", f"engrane {fm(TP['engrane'], 1)}", "rosca ciega en la base"]] + \
           ([[_cc(ctx, "int_bx_lamina"), f"lámina {D['material'].split(',')[0]} R{fm(D['R_int'], 0)}…R{fm(D['R_ext'], 0)}, {D['lamina']['n_paneles']} paneles (junta CJP J30)", f"e = {fm(D['t'], 0)}",
              f"mesa (soldada: {D['tapones']['n']} tapones J34, costuras J35/J36; B-B)"]] if LAM else
             [[_cc(ctx, "int_bx_disco_mesa"), f"{D['semidiscos']} semidiscos R{fm(D['R_int'], 0)}…R{fm(D['R_ext'], 0)} (CJP J30)", f"e = {fm(D['t'], 0)}", "mesa (atornillado)"],
              [_cc(ctx, "int_bx_tor_mesa"), f"{T['n']} × {T['designacion_base'].split(' (')[0]}", f"{len(BG)} anillos", "roscas en la mesa (B-B, C-C)"]])
    c.table_block("COMPONENTES DE LA INTERFAZ BX", [("Código", 22, "L"), ("Elemento", 70, "L"), ("Dato", 30, "L"), ("Lado / fijación", 46, "L")], rows)
    ids = [w["id"] for w in ctx.welds if w["id"] in ("J30", "J31", "J32", "J33", "J34", "J35", "J36")]
    notes = [f"{g.interfaz_nombre}.", f"Pila de la interfaz desde la cara superior de la base: portador {fm(POR['t'], 0)} + saliente {fm(PAS['h_p'], 2)} + " + ("lámina" if LAM else "disco") + f" {fm(D['t'], 0)} = δ {fm(g.delta, 2)} mm (núcleo; {X['z']['nota'].replace('disco_sup', 'cara superior de la lámina' if LAM else 'disco_sup')}).",
             f"Lado base: portador soldado ({', '.join(i for i in ids if i in ('J31', 'J32', 'J33'))}), pastillas a presión ({PAS['ajuste']['montaje']}) y tornillos {TP['designacion']} ({TP['apriete']}).",
             (f"Lado mesa: lámina en {D['lamina']['n_paneles']} paneles soldada a la plancha inferior de la mesa (junta a tope CJP J30 sobre el eje x, {D['tapones']['n']} tapones Ø{fm(D['tapones']['d'], 0)} J34, costuras J35/J36; "
              f"WPS disímil calificada, AWS D1.6), esmerilada a ras; separación lámina–plancha ≤ {fm(float((D.get('despegue_panel') or {}).get('g0') or 0.2), 2)} mm. Sin tornillos ni roscas en la mesa." if LAM else
              f"Lado mesa: disco en {D['semidiscos']} semidiscos con CJP J30 sobre el eje x, atornillado con {T['n']} tornillos {T['designacion_base']} ({T['nota']})."),
             "Secuencia de armado: instructivo (pasos 4 y 5); piezas: " + (f"{_cc(ctx, 'int_bx_lamina')} (lámina)" if LAM else "INT-016 (disco)") + ", INT-018 (portador), INT-019 (pastilla); tabla de fabricación simplificada: GEN-026."]
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
    vr = [[L(v["nombre"]), f"{num(v.get('dem'))} / {num(v.get('cap'))} {L(v.get('unidad') or '')}".strip(), fm(v["fu"], 2) if isinstance(v.get("fu"), (int, float)) else "—", v.get("estado", "—"), L(v.get("ref") or "")]
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
