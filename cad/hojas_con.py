"""Láminas de conjunto y subconjunto con globos de posición ligados al despiece, secuencia de montaje y explosionada. Se componen con el compositor de lámina (layout.py)."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_util import *
import hojas_pie, hojas_base
from hojas_pie import CUT_X, CUT_Y, jids, w_sym, w_out, rot_key
from soldadura_det import add_prep
from pie_a import ra, wd
import propuestas

PLAN_CON = []


def con(fn):
    PLAN_CON.append(fn.__name__)
    return fn


def anchors(ctx, key, V, pred=None, maxn=80):
    sh = ctx.shapes[key]
    c = []
    for i, so in enumerate(sh.Solids()):
        if i > maxn:
            break
        q = so.Center(); c.append((q.x, q.y, q.z))
        for fc in so.Faces():
            q = fc.Center(); c.append((q.x, q.y, q.z))
    ok = []
    for pt in c:
        if pred and not pred(pt):
            continue
        u, v = V.uv(pt)
        if V.win and not (V.win[0] <= u <= V.win[2] and V.win[1] <= v <= V.win[3]):
            continue
        ok.append((pt, u, v))
    if not ok:
        return None
    mu = sum(o[1] for o in ok) / len(ok); mv = sum(o[2] for o in ok) / len(ok)
    return min(ok, key=lambda o: (o[1] - mu) ** 2 + (o[2] - mv) ** 2)[0]


def balloons_auto(p, V, keys, pred=None, gap=13.0, off=22.0, label_of=None):
    """Globos con línea guía: anclaje sobre la pieza, círculo en un anillo rectangular alrededor de la vista, sin solaparse."""
    ctx = p.ctx
    x0, y0, x1, y1 = V.ext
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bx0, by0, bx1, by1 = x0 - off, y0 - off, x1 + off, y1 + off
    items = []
    for k in keys:
        pt = anchors(ctx, k, V, pred)
        if pt is None:
            continue
        P2 = V.P(pt)
        items.append((k, P2))
    per = 2 * ((bx1 - bx0) + (by1 - by0))

    def t_of(q):
        ang = math.atan2(q[1] - cy, q[0] - cx)
        dx, dy = math.cos(ang), math.sin(ang)
        sc = min(((bx1 - cx) / dx) if dx > 1e-9 else 1e9, ((bx0 - cx) / dx) if dx < -1e-9 else 1e9, ((by1 - cy) / dy) if dy > 1e-9 else 1e9, ((by0 - cy) / dy) if dy < -1e-9 else 1e9)
        px, py = cx + dx * sc, cy + dy * sc
        if abs(py - by0) < 1e-6: return px - bx0
        if abs(px - bx1) < 1e-6: return (bx1 - bx0) + (py - by0)
        if abs(py - by1) < 1e-6: return (bx1 - bx0) + (by1 - by0) + (bx1 - px)
        return 2 * (bx1 - bx0) + (by1 - by0) + (by1 - py)

    def pos_of(t):
        t %= per
        w_, h_ = bx1 - bx0, by1 - by0
        if t < w_: return (bx0 + t, by0)
        t -= w_
        if t < h_: return (bx1, by0 + t)
        t -= h_
        if t < w_: return (bx1 - t, by1)
        t -= w_
        return (bx0, by1 - t)
    ts = sorted([(t_of(P2), k, P2) for k, P2 in items])
    tt = [t for t, _, _ in ts]
    for _ in range(40):
        for i in range(1, len(tt)):
            if tt[i] - tt[i - 1] < gap:
                m_ = (tt[i] + tt[i - 1]) / 2
                tt[i - 1], tt[i] = m_ - gap / 2, m_ + gap / 2
    for t, (_, k, P2) in zip(tt, ts):
        q = pos_of(t)
        pos = ctx.m.get(k).pos
        p.s.balloon(P2, q, pos)
        ctx.balloons[p.h.plano].add(pos)
    V.ext = (min(V.ext[0], bx0 - 6), min(V.ext[1], by0 - 6), max(V.ext[2], bx1 + 6), max(V.ext[3], by1 + 6))




class Conj(Plano):
    """Lámina de conjunto: cabecera genérica (código de lámina CON-nnn)."""

    def __init__(self, ctx, num, keys, titulo, fmt="A1", material="Ver despiece", trat="Ver notas"):
        self.keys = [k for k in keys if ctx.m.get(k)]
        self.p0 = ctx.m.get(self.keys[0]) if self.keys else None
        masa = f"{f(ctx.mass_of(*self.keys), 1)} kg (conjunto)"
        h = Hoja(ctx, f"CON-{num:03d}", titulo, "", fmt=fmt, material=material, masa=masa, trat=trat, serie="CON", items=[ctx.code(k) for k in self.keys])
        self.init_plano(ctx, h)
        self.iso_keys = [k for k in self.keys if k in ctx.shapes]
        self.fmt_try = None

    def compact_table(self, keys=None, title="DESPIECE (completo en CON-002)"):
        ctx = self.ctx
        ps = [ctx.m.get(k) for k in (keys or self.keys) if ctx.m.get(k)]
        rows = [[str(q.pos), q.code.replace(CODE + "-", ""), q.name, str(q.qty), f(q.mass_total, 1)] for q in ps]
        rows.append(["", "", "TOTAL", "", f(sum(q.mass_total for q in ps), 1)])
        self.table_block(title, [("Pos", 8, "C"), ("Código", 21, "L"), ("Denominación", 41, "L"), ("Cant", 9, "C"), ("kg tot", 16, "R")], rows, bold_rows=(len(rows) - 1,))

    def tail(self, keys, weld_ids, notes):
        """Resumen de despiece, notas y (franja inferior) tabla de soldaduras o despiece del subconjunto."""
        ctx = self.ctx
        self.compact_table(keys)
        self.note_block("NOTAS DEL SUBCONJUNTO", list(notes) + notas_gen_fab(ctx)[:2], numbered=True)
        if weld_ids:
            self.weld_block(weld_ids, title="TABLA DE SOLDADURAS DEL SUBCONJUNTO")
        else:
            self.ficha_block(keys, title="DESPIECE DEL SUBCONJUNTO (completo)")


class alias:
    """Contexto: las claves locales con sufijo se resuelven a la pieza original para los globos."""

    def __init__(self, ctx, suf):
        self.ctx, self.suf = ctx, suf

    def __enter__(self):
        self.orig = self.ctx.m.get
        suf = self.suf
        self.ctx.m.get = lambda kk, o=self.orig: o(kk[:-len(suf)] if kk.endswith(suf) else kk)

    def __exit__(self, *a):
        self.ctx.m.get = self.orig


def mats(ctx, keys):
    return {k: ctx.mat.get(k, "acero") for k in keys}


def all_keys(ctx):
    return [p.key for p in ctx.m.parts]


def mesa_keys(ctx):
    return [p.key for p in ctx.m.parts if p.sub == "MES"]


def balloon_cb(keys, pred=None, gap=12.0, off=16.0, suf=None):
    def cb(V, c):
        if suf:
            with alias(c.ctx, suf):
                balloons_auto(c, V, keys, pred=pred, gap=gap, off=off)
        else:
            balloons_auto(c, V, keys, pred=pred, gap=gap, off=off)
    return cb


def chain(*cbs):
    def cb(V, c):
        for f_ in cbs:
            f_(V, c)
    return cb


EXPL = {"base": 0, "pivote": -500, "buje": 350, "tapa_ret": 800, "interfaz_b": 120, "interfaz_m": 330, "mesa": 600, "pernos": 1100, "tapa_insp": 1250, "madera": 1100, "acc": 380}


def expl_dz(ctx, p):
    k, sub = p.key, p.sub
    if k in ("pivote",): return EXPL["pivote"]
    if k == "buje": return EXPL["buje"]
    if k == "tapa_ret": return EXPL["tapa_ret"]
    if k == "tapa_insp": return EXPL["tapa_insp"]
    if k in ("pernos_pasador",): return EXPL["pernos"]
    if k in ("madera", "madera_anillo"): return EXPL["madera"]
    if sub == "INT": return EXPL["interfaz_m"] if ("mesa" in k or k in ("int_cara", "graseras") or "uhmw" in k) else EXPL["interfaz_b"]
    if sub == "MES": return EXPL["mesa"]
    if k in ("cilindro", "patin", "una", "pasador_vastago", "pasador_ojal"): return EXPL["acc"]
    return 0




STEPS = [
    ("Base soldada", "Armar sobre caballetes nivelados: plancha base, collar, marco, ménsulas, bancadas y orejas de izaje según BAS-001; soldar en secuencia simétrica (ver tabla de soldaduras), alivio de tensiones y mandrinar Ø%s H7 en línea." ),
    ("Mesa soldada", "Armar sobre la plancha inferior: almas y nervios; cerrar con anillos y plancha superior; soldar con control de distorsión (ver tabla de soldaduras); mandrinar los %d agujeros Ø%s H7 de los pasadores en línea y el cubo H7; planear la cara inferior."),
    ("Pivote y buje", "Calar el pivote Ø%s p6 en la plancha base y el collar (prensa o hielo seco); montar el buje s6 en el cubo de la mesa."),
    ("Accionamiento", "Montar bancadas ya soldadas: introducir patines por el extremo de la ranura T, uñas con resorte, cilindros y pasadores de articulación con grasa grafitada; conectar el circuito hidráulico."),
    ("Interfaz", "Montar la interfaz de deslizamiento (según opción) sobre la base y bajo la mesa: sectores con tornillos de posición y topes soldados, grasa grafitada; verificar juntas en frío."),
    ("Izaje y asiento de la mesa", "Izar la mesa con medios definidos por el montajista (decisión del mandante: el cálculo no define puntos de izaje de la mesa) y asentarla sobre el pivote con la holgura axial c_boss_a y radial c_boss_r en el collar."),
    ("Pasadores de empuje", "Insertar los %d pasadores Ø%s m6 en los anillos, perno M20 con arandela y torque propuesto (GEN); marcar con pintura de control."),
    ("Tapas y cubierta", "Colocar tapa retenedora del pivote y tapa de inspección; cubierta de madera si corresponde (opción)."),
    ("Control final", "Giro 360° en vacío, prueba hidráulica, prueba de carga y registro de presión de despegue (plan de inspección GEN-003)."),
]




# ======================================================================================================
@con
def sheet_conjunto(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    ks = all_keys(ctx)
    c = Conj(ctx, 1, ks, "CONJUNTO GENERAL DEL EQUIPO: PLANTA, ELEVACIÓN, CORTES E ISOMÉTRICA")
    s = c.s
    sh, mm = ctx.sh(*ks), mats(ctx, ks)
    B, tb = g.B, g.tb
    top = g.z0 + g.hd

    def planta(V, c):
        V.dimh((-B / 2, -B / 2, tb), (B / 2, -B / 2, tb), "bottom", 0, on=["base_plancha"], text=f"{f(B)}")
        V.dimv((B / 2, -B / 2, tb), (B / 2, B / 2, tb), "right", 0, on=["base_plancha"], text=f"{f(B)}")
        V.dim_dia((0, 0, top), g.Rt, 135, on=["mesa_anillo_sup"], text=f"Ø{f(P['D_top'])} (mesa)", ext=24)
        c.cut_mark("planta", "A", (-B / 2 - 20, 0, tb), (B / 2 + 20, 0, tb), 90)
        c.cut_mark("planta", "B", (0, -B / 2 - 20, tb), (0, B / 2 + 20, tb), 180)
    c.vs("planta", sh, "top", lv=(1, 1, 1, 1), draw=planta, mat=mm, hatch=False, title="PLANTA", auto=False, w=1.5)

    def elev(V, c):
        V.dimv((B / 2, -B / 2, 0), (g.Rt, 0, top), "right", 0, on=["base_plancha", "mesa_anillo_sup"], text=f"{f(top)} (altura total sin cubierta)")
        V.dimv((B / 2, -B / 2, 0), (B / 2, -B / 2, tb), "right", 1, on=["base_plancha"], text=f"{f(tb)}")
        V.dimv((g.Rt, 0, g.z0), (g.Rt, 0, top), "right", 2, on=["mesa_anillo_inf", "mesa_anillo_sup"], text=f"{f(g.hd)} (h_disc)")
    c.vs("elev", sh, "front", lv=(1, 2, 3, 1), draw=elev, mat=mm, hatch=False, title="ELEVACIÓN FRONTAL", auto=False, w=1.0)
    c.vs("cA", sh, "front", cut=CUT_Y, lv=(1, 1, 2, 1), extra=(22, 22, 22, 22), mat=mm, hs=0.5, title="CORTE A-A (plano y = 0)", auto=False, w=1.2,
         draw=chain(balloon_cb([k for k in ks], pred=lambda q: q[1] >= -0.5, gap=12.0, off=16.0), lambda V, c: V.dimv((B / 2, 0, g.tb), (B / 2, 0, g.tb + P["rim_h"]), "right", 0, on=["marco_corto"], text=f"{f(P['rim_h'])}")))
    c.vs("cB", sh, "right", cut=CUT_X, lv=(1, 2, 2, 1), mat=mm, hs=0.5, title="CORTE B-B (plano x = 0)", auto=False, w=1.0,
         draw=lambda V, c: V.dimv((B / 2, B / 2, 0), (B / 2, B / 2, g.tb), "right", 0, on=["base_plancha"], text=f"{f(g.tb)}"))
    c.compact_table()
    mt, cgx = ctx.rep["masa_total_ensamble"], ctx.rep["cg"]
    c.table_block("DATOS GENERALES", [("Dato del equipo", 60, "L"), ("Valor", 110, "L")], [
        ["Masa total del ensamble (3D)", f"{f(mt, 1)} kg (piezas del núcleo + comerciales)"], ["Masa del núcleo (m.total)", f"{f(ctx.M['total'], 1)} kg"],
        ["Centro de gravedad (x, y, z)", f"({fm(cgx[0], 1)}; {fm(cgx[1], 1)}; {fm(cgx[2], 1)}) mm desde el centro de la base y la cara inferior"],
        ["Carga de diseño", f"W = {f(P['W_tf'])} tf, excentricidad e = {f(P['e'])} mm"], ["Mesa / base", f"Ø{f(P['D_top'])} / {f(B)} × {f(B)} × {f(g.tb)}"], ["Interfaz", g.interfaz_nombre]])
    c.note_block("NOTAS DE CONJUNTO", [NOTA_VIENTO, NOTA_ANCLAJE, "Cotas generales; el detalle de cada subconjunto está en CON-006 (base), CON-007 (ménsula), CON-008/009 (mesa), CON-010 (accionamiento), CON-011 (pivote) y CON-012 (interfaz).",
                                       "Despiece completo con materiales, certificados y masas en CON-002. Piezas: plano propio con el código de la pieza. Vistas adicionales y dimensiones generales: CON-003."])
    c.build()
    return c.h


@con
def sheet_vistas_conj(ctx):
    g, P = ctx.g, ctx.P
    ks = all_keys(ctx)
    c = Conj(ctx, 3, ks, "CONJUNTO GENERAL: ELEVACIONES LATERAL Y POSTERIOR, VISTA INFERIOR Y DIMENSIONES GENERALES")
    sh, mm = ctx.sh(*ks), mats(ctx, ks)
    B, tb = g.B, g.tb
    top = g.z0 + g.hd
    on = ["base_plancha", "mesa_anillo_sup", "mesa_anillo_inf", "mesa_plancha_sup", "pernos_pasador"]
    on = [k for k in on if k in sh]
    c.vs("lat", sh, "right", lv=(1, 2, 3, 1), mat=mm, hatch=False, title="ELEVACIÓN LATERAL (desde +x)", w=1.2, auto=dict(on=on, tol={}, maxn=7))
    c.vs("post", sh, "back", lv=(1, 2, 3, 1), mat=mm, hatch=False, title="ELEVACIÓN POSTERIOR", w=1.2, auto=dict(on=on, tol={}, maxn=7))
    c.vs("inf", sh, "bottom", lv=(1, 1, 1, 1), mat=mm, hatch=False, title="VISTA INFERIOR (cara de apoyo de la base)", w=1.0,
         auto=dict(on=["base_plancha"], hole_rmin=20.0))
    pk = [k for k in ("pasadores", "pernos_pasador", "mesa_anillo_sup") if k in sh]
    c.vs("det_pin", {k: ctx.shapes[k] for k in pk}, "front", cut=((0, 0, 0), (0, 1, 0)), center=(g.R_pin, 0, top - 60), win=(-90, -110, 90, 90), lv=(1, 2, 1, 1), hs=0.4, maxs=2.0,
         title="DETALLE A: PASADOR, ARANDELA Y PERNO EN EL BORDE DE LA MESA", auto=dict(on=pk), mat={k: ctx.mat.get(k, "acero") for k in pk}, w=1.0)
    rows = [["Base (plancha)", f"{f(B)} × {f(B)} × {f(tb)}"], ["Altura total del equipo sin cubierta", f"{f(top)} (z de la cara superior de la mesa desde la cara inferior de la base)"],
            ["Mesa", f"Ø{f(P['D_top'])} × {f(g.hd)}; cara inferior a z = {f(g.z0)}"], ["Eje de los cilindros", f"z = {f(g.zc)}"],
            ["Pivote", f"Ø{f(P['D_piv'])} × {fm(g.L_piv, 1)}"], ["Carrera de los cilindros", f"{f(P['stroke'])} mm"]]
    c.table_block("DIMENSIONES GENERALES", [("Elemento", 60, "L"), ("Dimensión [mm]", 110, "L")], rows)
    c.note_block("NOTAS", ["Vistas de conjunto sin globos: las posiciones están en CON-001 (corte A-A). Dimensiones de fabricación: planos de cada pieza.", NOTA_VIENTO, NOTA_ANCLAJE])
    c.ficha_block(ks[:0] or [ks[0]], title="") if False else None
    c.build()
    return c.h


@con
def sheet_bom(ctx):
    out = []
    keys = all_keys(ctx)
    pend = keys
    n = 0
    while pend:
        n += 1
        c = Conj(ctx, 2 if n == 1 else 13 + n - 2, keys, f"DESPIECE COMPLETO DEL EQUIPO (HOJA {n})")
        R = c.h.R["main"]
        y, left = tabla_despiece(ctx, c.s, R[0], R[3], pend, R[2] - R[0], ymin=R[1] + 40, title="DESPIECE COMPLETO — MATERIAL CON NORMA Y GRADO, CERTIFICADO EN 10204 3.1, DIMENSIÓN DE PARTIDA, MASAS Y PLANO", total=False)
        done = len(pend) - len(left)
        if left:
            pend = pend[done:]
        else:
            pend = []
            c.s.text(f"MASA TOTAL DEL EQUIPO (todas las posiciones): {f(sum(p.mass_total for p in ctx.m.parts), 1)} kg", (R[0], y - 6), T_N + 1, "TOP_LEFT", bold=True)
        c.h.escala = "S/E"
        c.h.zone = (R[0], R[1], R[2], R[3])
        out.append(c.h)
    return out


@con
def sheet_explosionada(ctx):
    g = ctx.g
    ex = {}
    for p in ctx.m.parts:
        ex[p.key + "_x"] = ctx.shapes[p.key].translate(cq.Vector(0, 0, expl_dz(ctx, p)))
        ctx.mat[p.key + "_x"] = ctx.mat[p.key]
    ctx.shapes.update(ex)
    keys = [p.key for p in ctx.m.parts]
    c = Conj(ctx, 4, keys, "ISOMÉTRICA EXPLOSIONADA DEL EQUIPO CON GLOBOS DE POSICIÓN")
    ctx_keys = [k + "_x" for k in keys]

    def cb(V, c):
        orig_get = ctx.m.get
        ctx.m.get = lambda kk: orig_get(kk[:-2] if kk.endswith("_x") else kk)
        try:
            balloons_auto(c, V, ctx_keys, gap=14.0, off=28.0)
        finally:
            ctx.m.get = orig_get
        c.s.text("Desplazamientos verticales ilustrativos (no a escala); el eje de montaje es z. Pernos y arandelas sobre los pasadores.", (c.h.zone[0] + 4, c.h.zone[1] + 4), T_N, "BOTTOM_LEFT")
    c.vs("expl", {k + "_x": ctx.shapes[k + "_x"] for k in keys}, "iso", iso=True, lv=(1, 1, 1, 1), extra=(50, 40, 50, 40), mat={k + "_x": ctx.mat[k] for k in keys}, hatch=False, draw=cb, title="ISOMÉTRICA EXPLOSIONADA", auto=False)
    c.compact_table(keys)
    c.iso_fill = False
    c.build()
    return c.h




@con
def sheet_secuencia(ctx):
    g, P = ctx.g, ctx.P
    c = Conj(ctx, 5, all_keys(ctx), "SECUENCIA DE MONTAJE Y FABRICACIÓN")
    s = c.s
    stage_keys = [["base_plancha", "collar", "marco_largo", "marco_corto", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "orejas", "bancada"],
                  ["mesa_plancha_inf", "mesa_anillo_inf", "mesa_alma0", "mesa_alma1", "mesa_alma2", "mesa_nervio0", "mesa_nervio1", "mesa_nervio2", "mesa_cubo", "mesa_plancha_sup", "mesa_anillo_sup"],
                  ["base_plancha", "collar", "pivote", "buje"], ["base_plancha", "bancada", "cilindro", "patin", "una", "pasador_vastago", "pasador_ojal"]]
    for i, ks in enumerate(stage_keys):
        ks = [k for k in ks if k in ctx.shapes]
        c.vs(f"e{i}", ctx.sh(*ks), "iso", iso=True, lv=(1, 1, 1, 1), mat=mats(ctx, ks), hatch=False, title=f"{i + 1}. {STEPS[i][0].upper()}", auto=False, w=1.0)
    rows = []
    for i, (t, d) in enumerate(STEPS):
        txt = d
        if "%" in d:
            vals = {"Mesa soldada": (g.N_pin, f(g.d_pin)), "Pasadores de empuje": (g.N_pin, f(g.d_pin)), "Pivote y buje": (f(P["D_piv"]),), "Base soldada": (f(P["D_piv"]),)}[t]
            txt = d % vals
        rows.append([str(i + 1), t, txt])
    zw = c.h.R["left"][2] - c.h.R["left"][0]
    c.table_block("SECUENCIA (taller sin torno vertical: gran diámetro por corte, soldadura y mandrinadora)", [("Paso", 14, "C"), ("Etapa", 50, "L"), ("Descripción", zw - 68, "L")], rows, wide=True)
    c.note_block("NOTAS", [NOTA_VIENTO, NOTA_ANCLAJE, "Peso del equipo y puntos de izaje de la base: ver CON-001 y BAS-001 (4 orejas).", "No se prevé fabricar sobre la losa del cliente; la base se entrega soldada y aliviada."])
    c.iso_fill = False
    c.build()
    return c.h


@con
def sheet_base_soldada(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    B, tb, xg = g.B, g.tb, P["x_g"]
    ks = ["base_plancha", "collar", "marco_largo", "marco_corto", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "orejas", "bancada"]
    ks = [k for k in ks if ctx.m.get(k)]
    c = Conj(ctx, 6, ks, "BASE SOLDADA: CONJUNTO (PLANTA, ELEVACIONES, CORTES Y DETALLES DE JUNTA)", material="ASTM A572 Gr.50 (Fy ≥ %s MPa); plancha base Z35" % f(P["Fy"]), trat="Alivio de tensiones 590–620 °C")
    s = c.s
    sh, mm = ctx.sh(*ks), mats(ctx, ks)
    c1 = ctx.D["cilindros"]["horario"][0]["eye"]

    def planta(V, c):
        balloons_auto(c, V, ks, gap=12, off=14)
        V.dimh((-B / 2, B / 2, tb), (B / 2, B / 2, tb), "top", 0, on=["base_plancha"], text=f"{f(B)}")
        V.dimh((-xg, B / 2, tb), (xg, B / 2, tb), "top", 1, on=["base_plancha"], text=f"{f(2 * xg)} (entre ejes de bancadas)")
        c.cut_mark("planta", "A", (-B / 2 - 20, 0, tb), (B / 2 + 20, 0, tb), 90)
        c.cut_mark("planta", "B", (c1[0], -B / 2 - 20, tb), (c1[0], B / 2 + 20, tb), 180)
    c.vs("planta", sh, "top", lv=(1, 1, 1, 2), extra=(20, 20, 20, 20), draw=planta, mat=mm, hatch=False, title="PLANTA", auto=False, w=1.5)

    def cA(V, c):
        balloons_auto(c, V, [k for k in ks if k not in ("orejas",)], pred=lambda q: q[1] >= -0.5, gap=12, off=12)
        V.dimv((B / 2, 0, 0), (B / 2, 0, tb), "right", 0, on=["base_plancha"], text=f"{f(tb)}")
        V.dimh((-B / 2, 0, 0), (B / 2, 0, 0), "bottom", 0, on=["base_plancha"], text=f"{f(B)}")
    c.vs("cA", sh, "front", cut=CUT_Y, lv=(1, 1, 1, 1), extra=(16, 16, 16, 16), draw=cA, mat=mm, hs=0.5, title="CORTE A-A", auto=False, w=1.0)

    def cB(V, c):
        V.dimv((B / 2, B / 2, 0), (B / 2, B / 2, tb), "right", 0, on=["base_plancha"], text=f"{f(tb)}")
        V.dimv((B / 2, B / 2, tb), (B / 2, B / 2, tb + P["rim_h"]), "right", 1, on=["marco_largo"], text=f"{f(P['rim_h'])}")
    c.vs("cB", sh, "right", cut=((c1[0], 0, 0), (-1, 0, 0)), lv=(1, 1, 2, 1), draw=cB, mat=mm, hs=0.5, title="CORTE B-B (plano de la ménsula)", auto=False, w=1.0)
    kD = [k for k in ("base_plancha", "marco_largo") if k in ctx.shapes]
    ids = jids(ctx, "Marco perimetral largo", "Bancada", "Collar", "Mejillas de ménsula")
    c.vs("D1", kD, "right", cut=CUT_X, center=(0, -B / 2, tb), win=(-30, -tb - 4, 60, P["rim_h"] + 10), lv=(1, 1, 1, 1), extra=(0, 0, 90, 0), hs=0.35, maxs=2.0, title="D1: MARCO–PLANCHA", auto=dict(on=kD), w=0.8,
         draw=lambda V, c: w_out(c, ids[0], V, (0, -B / 2 + P["rim_t"], tb + 3), "right", other=None, dy=14))
    kb = [k for k in ("base_plancha", "bancada") if k in ctx.shapes]
    c.vs("D2", kb, "front", cut=CUT_Y, center=(xg, 0, tb), win=(-100, -tb - 6, 100, P["t_bed"] + 10), lv=(1, 1, 1, 1), extra=(0, 0, 90, 0), hs=0.35, maxs=2.0, title="D2: BANCADA–PLANCHA", auto=dict(on=kb), w=0.8,
         draw=lambda V, c: w_out(c, ids[1], V, (xg + P["w_bed"] / 2, 0, tb + 2), "right", dy=-14))
    kc = [k for k in ("base_plancha", "collar") if k in ctx.shapes]
    if g.boss:
        c.vs("D3", kc, "front", cut=CUT_Y, center=(g.D_boss / 2, 0, tb), win=(-110, -tb - 8, 60, g.h_boss + 12), lv=(1, 1, 1, 1), extra=(0, 0, 90, 0), hs=0.35, maxs=2.0, title="D3: COLLAR–PLANCHA", auto=dict(on=kc), w=0.8,
             draw=lambda V, c: w_out(c, ids[2], V, (g.D_boss / 2, 0, tb + 2), "right", all_round=True, dy=14))
    ke = [k for k in ("base_plancha", "mensula_mejilla", "mensula_oreja_inf") if k in ctx.shapes]
    c.vs("D4", ke, "front", cut=((c1[0], c1[1] - 150, 0), (0, 1, 0)), center=(c1[0], c1[1] - 150, tb), win=(-140, -tb - 8, 140, g.BR["H"] + 12), lv=(1, 1, 1, 1), extra=(0, 0, 90, 0), hs=0.35, maxs=1.0,
         title="D4: MÉNSULA (SECCIÓN)", auto=dict(on=ke), w=0.8, draw=lambda V, c: w_out(c, ids[3], V, (c1[0] + g.BR["Win"] / 2 + P["t_ch"], c1[1] - 150, tb + 2), "right", dy=14))
    ws = [w["id"] for w in ctx.welds if any(t in w["piezas"] for t in ("BAS", "IZA", "ACC-001"))]
    c.tail(ks, ws, ["Soldar en secuencia simétrica; alivio de tensiones antes del mecanizado. Mandrinar Ø%s H7 (plancha + collar) y los ojales Ø%s H9 de las ménsulas en línea." % (f(P["D_piv"]), f(P["d_pp"])),
                    "Tamaños de filete: ver tabla (núcleo o mínimo AWS a confirmar). Todas las juntas tienen símbolo ISO 2553 en las láminas de pieza y en los detalles D1–D4.",
                    f"Posiciones: bancadas en x = ±{f(xg)}; orejas de izaje en (±{f(P['x_lug'])}, ±{f(g.cl_lug)}); ménsulas según BAS-001 (tabla de posiciones).", "Cara de apoyo de la interfaz (Ø%s): planitud 0,20, sin pintura." % f(P["D_top"] + 20)])
    c.build()
    return c.h


@con
def sheet_mensula_conj(ctx):
    g, P, BR = ctx.g, ctx.P, ctx.g.BR
    c1 = ctx.D["cilindros"]["horario"][0]
    E, ph = c1["eye"], c1["phiMean"]
    ks = ["mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf"]
    for k in ks:
        ctx.local(k, k + "_C", near=(E[0], E[1], 80), r=300, shift=(-E[0], -E[1], 0), rot=-ph)
    ctx.local("base_plancha", "base_C", shift=(-E[0], -E[1], 0), rot=-ph)
    lk = [k + "_C" for k in ks]
    c = Conj(ctx, 7, ks, "MÉNSULA DE CILINDRO: SUBCONJUNTO SOLDADO (PLANTA, ELEVACIÓN Y CORTES)", material="ASTM A572 Gr.50", trat="Alivio de tensiones")
    c.iso_keys = lk
    tb, H_, rear, Llug, Win, Wout, tc = g.tb, BR["H"], BR["rear"], BR["Llug"], BR["Win"], BR["Wout"], P["t_ch"]
    zt = tb + H_
    sh = {k: ctx.shapes[k] for k in lk}
    sh2 = dict(sh); sh2["base_C"] = ctx.shapes["base_C"]
    mm = {k: "acero" for k in sh2}
    ids = [w["id"] for w in ctx.welds if any(t in w["desc"] for t in ("Mejillas de ménsula", "Oreja superior", "Oreja inferior"))]

    def planta(V, c):
        with alias(ctx, "_C"):
            balloons_auto(c, V, lk, gap=12, off=16)
        V.dimh((-rear, Wout / 2, zt), (P["L_ch"] - rear, Wout / 2, zt), "top", 0, on=["mensula_mejilla_C"], text=f"{f(P['L_ch'])}")
        V.dimv((P["L_ch"] - rear, -Wout / 2, zt), (P["L_ch"] - rear, Wout / 2, zt), "right", 0, on=["mensula_mejilla_C"], text=f"{f(Wout)}")
        V.dimv((Llug - rear, -Win / 2, zt), (Llug - rear, Win / 2, zt), "right", 1, on=["mensula_oreja_sup_C"], text=f"{f(Win)} (luz)")
        V.dim_dia((0, 0, zt), P["d_pp"] / 2, 120, on=["mensula_oreja_sup_C"], text=tol_txt(P["d_pp"], "H9"), ext=24)
        c.cut_mark("planta", "A", (-rear - 20, 0, zt), (P["L_ch"] - rear + 20, 0, zt), 90)
    c.vs("planta", sh, "top", lv=(1, 1, 2, 2), extra=(20, 20, 20, 20), draw=planta, mat=mm, hatch=False, title="PLANTA", auto=False, w=1.4)
    c.vs("cA", sh2, "front", cut=CUT_Y, lv=(1, 1, 2, 1), mat=mm, hs=0.4, title="CORTE A-A (plano del eje)", w=1.2,
         draw=lambda V, c: V.dimv((Llug - rear, 0, tb), (Llug - rear, 0, zt), "right", 0, on=["mensula_oreja_inf_C", "mensula_oreja_sup_C"], text=f"{f(H_)} (eje a {f(g.hax)} de la cara de apoyo)"), auto=dict(on=lk, maxn=6))
    c.vs("cB", sh2, "right", cut=((0, 0, 0), (-1, 0, 0)), lv=(1, 1, 2, 1), mat=mm, hs=0.4, title="CORTE B-B (por el eje del ojal)", w=1.0, auto=dict(on=lk, maxn=6))
    if ids:
        add_prep(c, "det_j", ctx.weld_by_id(ids[0]), t1=tc, t2=tb)
    c.tail(ks, ids, [f"Armar en plantilla sobre la base: mejillas {f(tc)} × {f(H_)} a {f(Win)} de luz; orejas entre mejillas; eje del ojal a {f(g.hax)} ±0,5 de la cara de apoyo.",
                     f"Mandrinar Ø{f(P['d_pp'])} H9 de ambas orejas en línea después de soldar (coaxialidad 0,10). Se fabrican {int(P['n_br'])} ménsulas.", "Filetes: ver tabla; secuencia alternada por lados; MT 100 %."])
    c.build()
    return c.h


@con
def sheet_mesa_conj1(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    ks = mesa_keys(ctx)
    a0 = D["pasadores"][0]
    c = Conj(ctx, 8, ks, "MESA SOLDADA: PLANTA A MEDIA ALTURA, PLANTA INFERIOR, ELEVACIÓN Y CORTE POR UN PASADOR", material="ASTM A572 Gr.50 (Fy ≥ %s MPa), Z35 y UT A578 B" % f(P["Fy"]), trat="Alivio de tensiones; planear cara inferior")
    zmid = g.z0 + g.tbo + g.hw / 2
    sh, mm = ctx.sh(*ks), mats(ctx, ks)

    def media(V, c):
        balloons_auto(c, V, [k for k in ks if k not in ("pernos_pasador",)], pred=lambda q: q[2] <= zmid + 0.5, gap=11, off=16)
        V.dim_dia((0, 0, g.z0 + g.tbo), g.Rt, 35, on=["mesa_anillo_inf"], text=f"Ø{f(P['D_top'])}", ext=26)
    c.vs("media", sh, "top", cut=((0, 0, zmid), (0, 0, -1)), lv=(1, 1, 1, 1), extra=(20, 20, 20, 20), draw=media, mat=mm, hs=0.8, title="PLANTA A MEDIA ALTURA (corte a h/2)", auto=False, w=1.5)

    def inf(V, c):
        V.dim_dia((0, 0, g.z0), g.prIn, 40, on=["mesa_plancha_inf"], text=f"Ø{f(2 * g.prIn)}", ext=26)
        V.dim_dia((0, 0, g.z0), (g.Drb / 2 if g.rebaje else g.d_bush / 2), 150, on=["mesa_plancha_inf"], text=f"Ø{f((g.Drb if g.rebaje else g.d_bush))} (pasante)", ext=26)
    c.vs("inf", sh, "bottom", lv=(1, 1, 1, 1), draw=inf, mat=mm, hatch=False, title="PLANTA INFERIOR (cara de apoyo)", auto=False, w=1.2)
    c.vs("elev", sh, "front", lv=(1, 2, 2, 1), mat=mm, hatch=False, title="ELEVACIÓN", auto=dict(on=["mesa_anillo_inf", "mesa_anillo_sup", "mesa_plancha_sup", "mesa_plancha_inf"], tol={}, maxn=6), w=1.0)
    for k in ks:
        rot_key(ctx, k, k + "_R", -a0)
    rs = ctx.sh(*[k + "_R" for k in ks])
    c.vs("corte", rs, "front", cut=CUT_Y, lv=(1, 2, 2, 1), mat={k + "_R": ctx.mat[k] for k in ks}, hs=0.7, title="CORTE POR UN PASADOR (plano a %s° del eje x)" % fm(a0, 3), w=1.2,
         auto=dict(on=[k + "_R" for k in ks if k in ("mesa_anillo_inf", "mesa_anillo_sup", "mesa_plancha_sup", "mesa_plancha_inf", "mesa_cubo")], tol={}, maxn=7))
    ids = [w["id"] for w in ctx.welds if "MES" in w["piezas"] or "INT tope mesa" in w["piezas"]]
    c.tail(ks, ids, [f"Armado sobre la plancha inferior: cubo, almas (R {', '.join(f(x) for x in D['almas'])}), {int(P['N_rib'])} nervios por tramo, anillos y plancha superior; cerrar con la superior en último lugar.",
                     f"{g.N_pin} agujeros Ø{f(g.d_pin)} H7 en PCD Ø{f(2 * g.R_pin)}: mandrinar en línea con la mesa armada y aliviada (ver MES-002/004 y tabla de pasadores en CON-009).",
                     f"Cubo H7 Ø{f(g.d_bush)} y rebaje del collar Ø{f(g.Drb)}: mandrinar después de aliviar; cara inferior planeada (planitud 0,20).", "Soldaduras: ver tabla (símbolos ISO 2553 en las láminas de pieza y en CON-009)."])
    c.build()
    return c.h


@con
def sheet_mesa_conj2(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    ks = mesa_keys(ctx)
    ang = D["nervios"][0] + 0.5 * (D["nervios"][1] - D["nervios"][0])
    c = Conj(ctx, 9, ks, "MESA SOLDADA: CORTE POR ALMAS, DETALLES DE JUNTA, REBAJE DEL COLLAR Y TABLA DE PASADORES", material="ASTM A572 Gr.50", trat="Alivio de tensiones")
    for k in ks:
        rot_key(ctx, k, k + "_W", -ang)
    ws = ctx.sh(*[k + "_W" for k in ks])
    mm = {k + "_W": ctx.mat[k] for k in ks}
    zt0 = g.z0 + g.tbo + g.hw

    def cw(V, c):
        with alias(ctx, "_W"):
            balloons_auto(c, V, [k + "_W" for k in ks if k not in ("pernos_pasador", "pasadores")], pred=lambda q: q[1] >= -0.5, gap=11, off=14)
        if len(D["almas"]) > 2:
            V.dimv((D["almas"][-1], 0, g.z0 + g.tbo), (D["almas"][-1], 0, zt0), "right", 0, on=["mesa_alma2_W"], text=f"{f(g.hw)}")
        V.dimh((g.d_bush / 2, 0, zt0), (P["D_hub"] / 2, 0, zt0), "top", 0, on=["mesa_cubo_W"], text=f"{fm((P['D_hub'] - g.d_bush) / 2, 0)} (cubo)")
    c.vs("cw", ws, "front", cut=CUT_Y, lv=(1, 1, 2, 2), extra=(20, 20, 20, 20), draw=cw, mat=mm, hs=0.7, title=f"CORTE POR ALMAS (plano a {fm(ang, 2)}°, entre nervios)", auto=False, w=1.6)
    kc = [k for k in ("base_plancha", "collar", "mesa_plancha_inf", "mesa_cubo", "pivote", "buje") if k in ctx.shapes]

    def cc(V, c):
        if g.rebaje:
            V.dimh((g.D_boss / 2, 0, g.tb + g.h_boss / 2), (g.Drb / 2, 0, g.z0 + g.tbo / 2), "top", 0, on=["collar", "mesa_plancha_inf"], text=f"c_boss_r = {fm(g.c_boss_r, 0)} (radial)")
            V.dimv((g.D_boss / 2 - 6, 0, g.tb + g.h_boss), (g.D_boss / 2 - 6, 0, g.z_techo), "left", 0, on=["collar", "mesa_cubo"], text=f"c_boss_a = {fm(g.c_boss_a, 0)} (axial)")
    c.vs("cc", kc, "front", cut=CUT_Y, center=(g.D_boss / 2, 0, g.tb + 20), win=(-70, -45, 60, g.h_boss + 70), lv=(1, 1, 1, 1), draw=cc, mat=mats(ctx, kc), hs=0.3, maxs=2.0, title="REBAJE DEL COLLAR: HOLGURAS (detalle)", auto=False, w=1.0)
    jn = [w["id"] for w in ctx.welds if "MES" in w["piezas"]]
    for i, wid in enumerate(jn[:3]):
        add_prep(c, f"dj{i}", ctx.weld_by_id(wid), t1=g.tpr)
    rows = []
    for i, a in enumerate(D["pasadores"]):
        x, y = polar(g.R_pin, a)
        rows.append([str(i + 1), fm(a, 3) + "°", f(x, 1), f(y, 1)])
    half = (len(rows) + 1) // 2
    rows2 = [rows[i] + (rows[i + half] if i + half < len(rows) else ["", "", "", ""]) for i in range(half)]
    c.table_block("POSICIÓN DE LOS PASADORES (PCD Ø%s, paso %s°, arranque %s°)" % (f(2 * g.R_pin), fm(360 / g.N_pin, 3), fm(D["pasadores"][0], 3)),
                  [("N°", 9, "C"), ("Ángulo", 22, "R"), ("x [mm]", 22, "R"), ("y [mm]", 22, "R"), ("N°", 9, "C"), ("Ángulo", 22, "R"), ("x [mm]", 22, "R"), ("y [mm]", 22, "R")], rows2)
    c.tail(ks, jn, ["Los nervios se cortan entre almas; las almas son continuas; 1 empalme por alma entre nervios.", "Holguras del collar: radial c_boss_r y axial c_boss_a del núcleo; el cubo gira sin tocar el collar.",
                    f"Tabla de pasadores: ángulos desde +x, sentido antihorario; PCD Ø{f(2 * g.R_pin)} ±0,3."])
    c.build()
    return c.h


@con
def sheet_accionamiento(ctx):
    g, P, D, KG = ctx.g, ctx.P, ctx.D, ctx.g.KG
    ks = ["bancada", "cilindro", "patin", "una", "pasador_vastago", "pasador_ojal"]
    X = P["x_g"]
    for k in ks:
        ctx.local(k, k + "_A", near=(X, 0, g.tb + 80), r=1100)
    ctx.local("base_plancha", "base_A", near=(X, 0, 0), r=1e9)
    lk = [k + "_A" for k in ks if k + "_A" in ctx.shapes]
    c = Conj(ctx, 10, ks, "ACCIONAMIENTO: CILINDRO, MÉNSULA, PATÍN, BANCADA, UÑA Y PASADORES (VISTA Y CORTES)", material="Ver despiece", trat="Ver despiece")
    c.iso_keys = lk
    cc = D["cilindros"]["antihorario"][0]
    ye, yr, zc = cc["eye"][1], cc["rodEngage"][1], g.zc
    sh = {k: ctx.shapes[k] for k in lk}
    mm = {k: ctx.mat.get(k[:-2], "acero") for k in lk}
    yc = (ye + yr) / 2

    def planta(V, c):
        with alias(ctx, "_A"):
            balloons_auto(c, V, lk, gap=12, off=16)
        V.dimv((X, ye, zc), (X, yr, zc), "right", 0, on=["cilindro_A"], text=f"{fm(abs(ye - yr), 1)} (entre ejes de ojales)", virt_a=P["d_pp"] / 2, virt_b=P["d_pp"] / 2)
        V.dim_dia((X, ye, zc), P["d_pp"] / 2, 30, on=["pasador_ojal_A", "cilindro_A"], text=f"Ø{f(P['d_pp'])} f8", ext=22)
        c.cut_mark("planta", "A", (X - 160, yc, g.tb), (X + 160, yc, g.tb), 90)
    c.vs("planta", sh, "top", lv=(1, 1, 2, 2), extra=(20, 20, 20, 20), draw=planta, mat=mm, hatch=False, title="PLANTA (grupo de accionamiento, lado +x)", auto=False, w=1.6)
    c.vs("cA", sh, "front", cut=((0, yc, 0), (0, 1, 0)), center=(X, yc, zc), win=(-150, -g.zc - 20, 150, 130), lv=(1, 1, 1, 1), mat=mm, hs=0.4, title="CORTE A-A (por patín, bancada y cilindro)", auto=dict(on=lk, maxn=6), w=1.0)
    c.vs("lat", sh, "right", lv=(1, 1, 1, 1), mat=mm, hatch=False, title="ELEVACIÓN LATERAL", auto=dict(on=["base_A", "bancada_A"] if "base_A" in sh else lk, maxn=5), w=1.0)
    c.tail(ks, [], [f"Montaje: patines por el extremo de la ranura T de la bancada; uña en alojamiento con resorte; cilindro entre ménsula (ojal trasero, pasador Ø{f(P['d_pp'])} f8) y patín (vástago).",
                    f"Eje de los cilindros a {f(g.hax)} de la cara de apoyo (z = {f(g.zc)}); carrera {f(P['stroke'])}; uña toma el pasador de la mesa con la cara plana a {f(P['c_tip'])} de la punta.",
                    "Lubricar guías y pasadores con grasa grafitada; verificar holgura de patín en bancada (1 mm por lado en cabeza T).",
                    "Circuito hidráulico, bomba y válvulas: fuera del alcance de estos planos (tipo y características: GEN-008; marca/modelo por catálogo)."])
    c.build()
    return c.h


@con
def sheet_pivote_conj(ctx):
    g, P = ctx.g, ctx.P
    ks = [k for k in ("pivote", "buje", "tapa_ret", "tapa_insp", "collar", "base_plancha", "mesa_cubo", "mesa_plancha_inf", "mesa_plancha_sup") if ctx.m.get(k)]
    ks2 = ["pivote", "buje", "tapa_ret", "tapa_insp", "collar", "mesa_cubo"]
    c = Conj(ctx, 11, ks2, "PIVOTE: CUBO, COLLAR, BUJE Y TAPAS — HOLGURAS Y AJUSTES (ISO 286)", material="Ver despiece", trat="Ver despiece")
    top = g.z0 + g.hd
    sh, mm = ctx.sh(*ks), mats(ctx, ks)

    def cA(V, c):
        balloons_auto(c, V, [k for k in ks if k not in ("mesa_plancha_sup", "mesa_plancha_inf", "base_plancha")], pred=lambda q: q[1] >= -0.5, gap=12, off=18)
        V.line_axis = None
        c.s.line(V.P(0, 0, -6), V.P(0, 0, top + 14), "EJE")
        V.dimv((g.d_bush / 2, 0, g.z_bush0), (g.d_bush / 2, 0, g.z_bush0 + P["L_bush"]), "right", 0, on=["buje"], text=f"{f(P['L_bush'])} (buje)")
        V.dimv((-P["D_piv"] / 2 + g.ch_piv, 0, 0), (-P["D_piv"] / 2 + g.ch_piv, 0, g.L_piv), "left", 0, on=["pivote"], text=f"{fm(g.L_piv, 1)} (pivote)")
        V.dimh((-P["D_hub"] / 2, 0, g.z0 + g.tbo + 40), (P["D_hub"] / 2, 0, g.z0 + g.tbo + 40), "top", 0, on=["mesa_cubo"], text=f"Ø{f(P['D_hub'])} (cubo)")
        V.dimh((-g.D_boss / 2, 0, g.tb + g.h_boss - 2), (g.D_boss / 2, 0, g.tb + g.h_boss - 2), "bottom", 0, on=["collar"], text=f"Ø{f(g.D_boss)} (collar)")
        V.dimh((-P["D_piv"] / 2, 0, g.tb + 20), (P["D_piv"] / 2, 0, g.tb + 20), "bottom", 1, on=["pivote", "collar"], text=tol_txt(P["D_piv"], "p6") + " / H7") if False else None
    c.vs("cA", sh, "front", cut=CUT_Y, center=(0, 0, 0), win=(-190, -8, 190, top + 20), lv=(2, 2, 3, 2), extra=(20, 20, 40, 20), draw=cA, mat=mm, hs=0.5, title="CORTE A-A (eje del pivote)", auto=False, w=1.6)
    c.vs("det_f", [k for k in ("pivote", "buje", "mesa_cubo") if k in ctx.shapes], "front", cut=CUT_Y, center=(P["D_piv"] / 2, 0, g.z_bush0 + P["L_bush"] / 2), win=(-30, -P["L_bush"] / 2 - 10, 100, P["L_bush"] / 2 + 10), lv=(1, 1, 1, 1), hs=0.35, maxs=2.0,
         title="DETALLE A: AJUSTES DEL BUJE (F7/f7 Y s6/H7)", auto=dict(on=["pivote", "buje", "mesa_cubo"]), mat=mats(ctx, ["pivote", "buje", "mesa_cubo"]), w=1.0)
    ajs = [a for a in hojas_base.ajustes(ctx) if a[0] in ("Pivote en plancha base y collar", "Pivote en buje", "Buje en cubo de la mesa")]
    rows = []
    for (desc, d, ho, sh_, app) in ajs:
        t = hojas_base.ajuste_txt(d, ho, sh_)
        rows.append([desc, f"Ø{fm(d, 0)} {ho}/{sh_}", t["h_lim"], t["s_lim"], t["juego"], t["tipo"]])
    rows.append(["Collar en rebaje de la plancha inferior", f"Ø{f(g.D_boss)} / Ø{f(g.Drb)}", f"{fm(g.Drb, 1)}", f"{fm(g.D_boss, 1)}", f"c_boss_r = {fm(g.c_boss_r, 0)} (radial)", "sin contacto (núcleo)"])
    rows.append(["Collar – cubo (axial)", f"{fm(g.h_boss, 0)} vs {fm(g.h_rebaje, 1)}", "—", "—", f"c_boss_a = {fm(g.c_boss_a, 0)} (axial)", "sin contacto (núcleo)"])
    c.table_block("AJUSTES Y HOLGURAS DEL PIVOTE (ISO 286, límites calculados)", [("Ajuste", 40, "L"), ("Nominal", 24, "L"), ("Agujero [mm]", 24, "C"), ("Eje [mm]", 24, "C"), ("Juego [µm]", 26, "C"), ("Tipo", 30, "L")], rows)
    c.tail(ks2, [], [f"Pivote Ø{f(P['D_piv'])} p6 en plancha base y collar (H7, aprieto); en el buje F7/f7 con juego, buje s6/H7 prensado en el cubo.",
                     f"Altura de asiento del cubo: collar de {f(g.h_boss)} sobre la base; holgura radial {fm(g.c_boss_r, 0)} y axial {fm(g.c_boss_a, 0)} (núcleo): el cubo gira sin tocar el collar.",
                     f"Tapa retenedora con 4 × M10×25 ISO 10642 10.9 (PCD Ø{fm(g.cap_pcd, 0)}); tapa de inspección con 6 × M10 (PCD Ø{fm(g.insp_pcd, 0)}); torques propuestos en GEN-008, a confirmar.",
                     "Retención axial del pivote: A DEFINIR POR EL CALCULISTA (decisión del mandante)."])
    c.build()
    return c.h


@con
def sheet_interfaz_conj(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    if not g.opt:
        return None
    lay = m.layout
    ks = [p.key for p in m.parts if p.sub == "INT"]
    c = Conj(ctx, 12, ks, f"CONJUNTO DE LA INTERFAZ: {g.interfaz_nombre.upper()}", material="Ver despiece", trat="Ver despiece")
    th = 360.0 / g.n_sec
    sh, mm = ctx.sh(*ks), mats(ctx, ks)
    ztop = g.z0
    disc = [k for k in ks if k.startswith("int_disco") or k in ("int_cara", "int_bronce")]

    def planta(V, c):
        s = c.s
        V.dim_dia((0, 0, ztop), g.Ro, 3, on=disc, text=f"Ø{f(2 * g.Ro)} (R_o = {fm(g.Ro, 0)})", ext=26)
        for i in range(g.n_sec):
            a = (i + 0.5) * th
            pxy = polar(g.Ro + 12, a)
            s.text(str(i + 1), V.P(pxy[0], pxy[1], ztop), T_MIN + 0.5, "MIDDLE_CENTER")
            s.line(V.P(polar(g.Ri, i * th) + (ztop,)), V.P(polar(g.Ro + 6, i * th) + (ztop,)), "FANT")
    c.vs("planta", sh, "top", lv=(1, 1, 1, 1), extra=(10, 10, 10, 10), draw=planta, mat=mm, hatch=False, title=f"PLANTA: {g.n_sec} SECTORES DE {fm(th, 3)}° (numeración antihoraria desde +x)", auto=False, w=1.5)
    a1 = th / 2
    for k in ks + ["base_plancha", "mesa_plancha_inf"]:
        rot_key(ctx, k, k + "_I", -a1)
    isk = [k + "_I" for k in ks] + ["base_plancha_I", "mesa_plancha_inf_I"]
    ish = ctx.sh(*isk)
    tt_ = sum(l["t"] for l in g.stack)
    ints = [k for k in isk if k.startswith("int_")]

    def corte(V, c):
        with alias(ctx, "_I"):
            balloons_auto(c, V, ints, pred=lambda q: q[1] >= -0.5, gap=12, off=14)
        z = g.tb
        for l in g.stack:
            V.dimv((g.Ri + 2, 0, z), (g.Ri + 2, 0, z + l["t"]), "left", 0, on=ints, text=f"{fm(l['t'], 1)} ({l['id']})")
            z += l["t"]
    c.vs("corte", ish, "front", cut=CUT_Y, center=(g.r_u, 0, g.tb + tt_ / 2), win=(-170, -tt_ - 40, 170, tt_ + 40), lv=(2, 1, 1, 1), extra=(10, 10, 10, 10), draw=corte,
         mat={k: ctx.mat[k[:-2]] for k in isk}, hs=0.25, title="CORTE RADIAL POR LA BISECTRIZ DEL SECTOR 1", auto=False, w=1.2)
    rows = [[str(i + 1), fm((i + 0.5) * th, 3) + "°", fm(i * th, 3) + "°", fm((i + 1) * th, 3) + "°", f(polar(g.r_u, (i + 0.5) * th)[0], 1), f(polar(g.r_u, (i + 0.5) * th)[1], 1)] for i in range(g.n_sec)]
    half = (len(rows) + 1) // 2
    rows2 = [rows[i] + (rows[i + half] if i + half < len(rows) else [""] * 6) for i in range(half)]
    cols = [("Sector", 14, "C"), ("Bisectriz", 20, "R"), ("Inicio", 20, "R"), ("Fin", 20, "R"), ("x tope", 18, "R"), ("y tope", 18, "R")]
    c.table_block(f"COORDENADAS DE LOS SECTORES (tope en r_u = {fm(g.r_u, 1)} sobre la bisectriz)", cols + [(t + " ", w, a) for t, w, a in cols], rows2, wide=True)
    ids = [w["id"] for w in ctx.welds if "INT" in w["piezas"]]
    notes = [f"{g.interfaz_nombre}.", f"Juntas en frío entre sectores {fm(g.junta('disc'), 2)} mm" + (f" (UHMW {fm(g.junta('uhmw'), 2)} mm)" if g.opt == 2 else "") + "; muescas de tope en la bisectriz.",
             "Los tornillos de posición solo posicionan (no transmiten carga): el par lo toman los topes soldados.", "Ver láminas de sector, tope, tornillos y notas de la interfaz (INT)."]
    if g.opt in (1, 3):
        notes.append(f"Ranuras de engrase: {g.n_gr_rad} radiales a k·{fm(360 / g.n_gr_rad, 1)}° y {g.n_gr_circ} circunferenciales (R = {', '.join(fm(r, 0) for r in lay.r_circ)}), ancho {fm(g.w_gr, 0)}, prof. {fm(g.h_gr, 1)}; {g.n_greaser} graseras a R_o − 30.")
    c.tail(ks, ids, notes)
    c.build()
    return c.h
