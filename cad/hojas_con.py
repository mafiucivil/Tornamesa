"""Láminas de conjunto y subconjunto con globos de posición ligados al despiece, secuencia de montaje y explosionada."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_util import *
import hojas_pie
from hojas_pie import CUT_X, CUT_Y, jids, w_sym, rot_key, gd_column

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


class Conj(Pieza):
    """Lámina de conjunto: cabecera genérica (código de lámina CON-nnn)."""

    def __init__(self, ctx, num, keys, titulo, fmt="A1", material="Ver despiece", trat="Ver notas"):
        self.ctx = ctx
        self.keys = [k for k in keys if ctx.m.get(k)]
        self.p0 = ctx.m.get(self.keys[0]) if self.keys else None
        masa = f"{f(ctx.mass_of(*self.keys), 1)} kg (conjunto)"
        h = Hoja(ctx, f"CON-{num:03d}", titulo, "", fmt=fmt, material=material, masa=masa, trat=trat, serie="CON", items=[ctx.code(k) for k in self.keys])
        self.h = h
        self.s = h.begin()
        R = h.R
        self.views = R["left"]
        self.right = R["right"]
        self.low = R["low"]
        self.scales, self.vlist = [], []
        self.dims_n0 = len(vistas.COTAS.rows)

    def compact_table(self, keys=None, x=None, y=None, w=None):
        ctx, s = self.ctx, self.s
        r = self.right
        x = x if x is not None else r[0]
        y = y if y is not None else r[3]
        w = w if w is not None else r[2] - r[0]
        ps = [ctx.m.get(k) for k in (keys or self.keys) if ctx.m.get(k)]
        rows = [[str(q.pos), q.code.replace(CODE + "-", ""), q.name, str(q.qty), f(q.mass_total, 1)] for q in ps]
        rows.append(["", "", "TOTAL", "", f(sum(q.mass_total for q in ps), 1)])
        sc = w / 100.0
        return s.table(x, y, [("Pos", 8 * sc, "C"), ("Código", 21 * sc, "L"), ("Denominación", 41 * sc, "L"), ("Cant", 9 * sc, "C"), ("kg tot", 16 * sc, "R")], rows, h=T_S, title="DESPIECE (completo en CON-002/003)",
                       bold_rows=(len(rows) - 1,), ymin=self.low[1] if False else r[1])


def mats(ctx, keys):
    return {k: ctx.mat.get(k, "acero") for k in keys}


def all_keys(ctx):
    return [p.key for p in ctx.m.parts]


# ======================================================================================================
@con
def sheet_conjunto(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    ks = [k for k in all_keys(ctx) if k not in ("int_tapones",)]
    c = Conj(ctx, 1, all_keys(ctx), "CONJUNTO GENERAL DEL EQUIPO: PLANTA, ELEVACIÓN, CORTES E ISOMÉTRICA")
    s = c.s
    x0, y0, x1, y1 = c.views
    Wd, Ht = x1 - x0, y1 - y0
    xs = x0 + 0.44 * Wd
    sh = ctx.sh(*ks)
    mm = mats(ctx, ks)
    B = g.B
    Vp = c.V(sh, "top", (x0, y0 + 0.40 * Ht, xs, y1), label="Planta", margin=(26, 26, 26, 26), mat=mm, hatch=False)
    Vp.dimh((-B / 2, -B / 2, g.tb), (B / 2, -B / 2, g.tb), "bottom", 0, on=["base_plancha"], text=f"{f(B)}")
    Vp.dimv((B / 2, -B / 2, g.tb), (B / 2, B / 2, g.tb), "right", 0, on=["base_plancha"], text=f"{f(B)}")
    Vp.dim_dia((0, 0, g.z0 + g.hd), g.Rt, 135, on=["mesa_anillo_sup"], text=f"Ø{f(P['D_top'])} (mesa)", ext=24)
    s.cut_line(Vp.P(-B / 2 - 20, 0, g.tb), Vp.P(B / 2 + 20, 0, g.tb), "A", 90)
    s.cut_line(Vp.P(0, -B / 2 - 20, g.tb), Vp.P(0, B / 2 + 20, g.tb), "B", -180 if False else 180)
    Vp.title("PLANTA")
    Vi = c.V(sh, "iso", (x0, y0, xs, y0 + 0.40 * Ht), label="Isométrica", margin=(26, 26, 26, 26), mat=mm, hatch=False)
    Vi.title("ISOMÉTRICA")
    xr = xs + 6
    Vf = c.V(sh, "front", (xr, y0 + 0.78 * Ht, x1, y1), label="Elevación", margin=(26, 24, 26, 20), mat=mm, hatch=False)
    Vf.dimv((B / 2, -B / 2, 0), (B / 2, -B / 2, g.tb), "right", 0, on=["base_plancha"], text=f"{f(g.tb)}")
    Vf.dimv((g.Rt, 0, g.z0 + g.hd - g.tpr), (g.Rt, 0, g.z0 + g.hd), "right", 1, on=["mesa_anillo_sup"], text=f"{f(g.tpr)}") if False else None
    Vf.title("ELEVACIÓN FRONTAL")
    VA = c.V(sh, "front", (xr, y0 + 0.53 * Ht, x1, y0 + 0.78 * Ht), label="Corte A-A", cut=CUT_Y, margin=(26, 24, 26, 20), mat=mm, hatch_scale=0.5)
    balloons_auto(c, VA, [k for k in ks if m.get(k).sub not in ("INT",) or True], pred=lambda q: q[1] >= -0.5, gap=12.0, off=16.0)
    VA.dimv((B / 2, 0, g.tb), (B / 2, 0, g.tb + P["rim_h"]), "right", 0, on=["marco_corto"], text=f"{f(P['rim_h'])}")
    VA.title("CORTE A-A (plano y = 0)")
    VB = c.V(sh, "right", (xr, y0, x1, y0 + 0.53 * Ht), label="Corte B-B", cut=CUT_X, margin=(26, 30, 26, 20), mat=mm, hatch_scale=0.5)
    VB.dimv((B / 2, B / 2, 0), (B / 2, B / 2, g.tb), "right", 0, on=["base_plancha"], text=f"{f(g.tb)}")
    VB.dimv((g.Rt, 0, g.z0), (g.Rt, 0, g.z0 + g.hd), "right", 1, on=["mesa_anillo_sup", "mesa_anillo_inf"], text=f"{f(g.hd)} (h_disc)") if False else None
    VB.title("CORTE B-B (plano x = 0)")
    c.compact_table()
    # bloque inferior: masa, CG, notas
    mt, cgx = ctx.rep["masa_total_ensamble"], ctx.rep["cg"]
    x, y = c.low[0], c.low[3]
    s.table(x, y, [("Dato del equipo", 90, "L"), ("Valor", 170, "L")], [
        ["Masa total del ensamble (3D)", f"{f(mt, 1)} kg (piezas del núcleo + comerciales)"], ["Masa del núcleo (m.total)", f"{f(ctx.M['total'], 1)} kg"],
        ["Centro de gravedad (x, y, z)", f"({fm(cgx[0], 1)}; {fm(cgx[1], 1)}; {fm(cgx[2], 1)}) mm desde el centro de la base y la cara inferior"],
        ["Carga de diseño", f"W = {f(P['W_tf'])} tf, excentricidad e = {f(P['e'])} mm"], ["Mesa / base", f"Ø{f(P['D_top'])} / {f(B)} × {f(B)} × {f(g.tb)}"],
        ["Interfaz", g.interfaz_nombre]], h=T_S, title="DATOS GENERALES")
    s.notes_block(x + 285, y, "NOTAS DE CONJUNTO", [NOTA_VIENTO, NOTA_ANCLAJE, "Cotas generales; el detalle de cada subconjunto está en CON-006 (base), CON-008/009 (mesa), CON-010 (accionamiento), CON-011 (pivote) y CON-012 (interfaz).",
                                                       "Despiece completo con materiales, certificados y masas en CON-002/003. Piezas: plano propio con el código de la pieza."], h=T_N, width=330)
    c.finish_scale()
    return c.h


@con
def sheet_bom(ctx):
    out = []
    keys = all_keys(ctx)
    pend = keys
    n = 0
    while pend:
        n += 1
        c = Conj(ctx, 2 + n - 1, keys, f"DESPIECE COMPLETO DEL EQUIPO (HOJA {n})")
        R = c.h.R["main"]
        rows_before = pend
        y, left = tabla_despiece(ctx, c.s, R[0], R[3], pend, R[2] - R[0], ymin=R[1] + 40, title="DESPIECE COMPLETO — MATERIAL CON NORMA Y GRADO, CERTIFICADO EN 10204 3.1, DIMENSIÓN DE PARTIDA, MASAS Y PLANO", total=False)
        done = len(pend) - len(left)
        if left:
            pend = pend[done:]
        else:
            pend = []
            c.s.text(f"MASA TOTAL DEL EQUIPO (todas las posiciones): {f(sum(p.mass_total for p in ctx.m.parts), 1)} kg", (R[0], y - 6), T_N + 1, "TOP_LEFT", bold=True)
        c.h.escala = "S/E"
        out.append(c.h)
    return out


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
    s = c.s
    x0, y0, x1, y1 = c.views
    V = c.V({k + "_x": ctx.shapes[k + "_x"] for k in keys}, "iso", (x0, y0, x1, y1), label="Explosionada", margin=(60, 50, 60, 50), mat={k + "_x": ctx.mat[k] for k in keys}, hatch=False)
    # globos: ancla en la pieza desplazada
    ctx_keys = [k + "_x" for k in keys]
    xs0, ys0, xs1, ys1 = V.ext
    pos_by = {}
    for k in keys:
        ctx.m.get(k)
    old = ctx.m.parts
    # reutiliza balloons_auto sobre las claves desplazadas, con el número de posición de la pieza original
    class Alias:
        pass
    from types import SimpleNamespace
    orig_get = ctx.m.get
    ctx.m.get = lambda kk: orig_get(kk[:-2] if kk.endswith("_x") else kk)
    try:
        balloons_auto(c, V, ctx_keys, gap=14.0, off=28.0)
    finally:
        ctx.m.get = orig_get
    s.text("Desplazamientos verticales ilustrativos (no a escala); el eje de montaje es z. Pernos y arandelas sobre los pasadores.", (x0, y0 + 2), T_N, "BOTTOM_LEFT")
    V.title("ISOMÉTRICA EXPLOSIONADA")
    c.compact_table(keys)
    c.finish_scale()
    return c.h


STEPS = [
    ("Base soldada", "Armar sobre caballetes nivelados: plancha base, collar, marco, ménsulas, bancadas y orejas de izaje según BAS-001; soldar en secuencia simétrica (J01…J09), alivio de tensiones y mandrinar Ø%s H7 en línea." ),
    ("Mesa soldada", "Armar sobre la plancha inferior: almas y nervios; cerrar con anillos y plancha superior; soldar con control de distorsión (J10…J16); mandrinar los %d agujeros Ø%s H7 de los pasadores en línea y el cubo H7; planear la cara inferior."),
    ("Pivote y buje", "Calar el pivote Ø%s p6 en la plancha base y el collar (prensa o hielo seco); montar el buje s6 en el cubo de la mesa."),
    ("Accionamiento", "Montar bancadas ya soldadas: introducir patines por el extremo de la ranura T, uñas con resorte, cilindros y pasadores de articulación con grasa grafitada; conectar el circuito hidráulico."),
    ("Interfaz", "Montar la interfaz de deslizamiento (según opción) sobre la base y bajo la mesa: sectores con tornillos de posición y topes soldados, grasa grafitada; verificar juntas en frío."),
    ("Izaje y asiento de la mesa", "Izar la mesa con medios definidos por el montajista (A DEFINIR; el cálculo no define puntos de izaje de la mesa) y asentarla sobre el pivote con la holgura axial c_boss_a y radial c_boss_r en el collar."),
    ("Pasadores de empuje", "Insertar los %d pasadores Ø%s m6 en los anillos, perno M20 con arandela y torque propuesto (GEN); marcar con pintura de control."),
    ("Tapas y cubierta", "Colocar tapa retenedora del pivote y tapa de inspección; cubierta de madera si corresponde (opción)."),
    ("Control final", "Giro 360° en vacío, prueba hidráulica, prueba de carga y registro de presión de despegue (plan de inspección GEN-003)."),
]


@con
def sheet_secuencia(ctx):
    g, P = ctx.g, ctx.P
    c = Conj(ctx, 5, all_keys(ctx), "SECUENCIA DE MONTAJE Y FABRICACIÓN")
    s = c.s
    x0, y0, x1, y1 = c.views
    stage_keys = [["base_plancha", "collar", "marco_largo", "marco_corto", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "orejas", "bancada"],
                  ["mesa_plancha_inf", "mesa_anillo_inf", "mesa_alma0", "mesa_alma1", "mesa_alma2", "mesa_nervio0", "mesa_nervio1", "mesa_nervio2", "mesa_cubo", "mesa_plancha_sup", "mesa_anillo_sup"],
                  ["base_plancha", "collar", "pivote", "buje"], ["base_plancha", "bancada", "cilindro", "patin", "una", "pasador_vastago", "pasador_ojal"]]
    stage_keys[1] = [k for k in stage_keys[1] if k in ctx.shapes]
    cw = (x1 - x0) / 4
    for i, ks in enumerate(stage_keys):
        ks = [k for k in ks if k in ctx.shapes]
        V = c.V(ctx.sh(*ks), "iso", (x0 + i * cw, y0 + 0.55 * (y1 - y0), x0 + (i + 1) * cw, y1), label=f"Etapa {i + 1}", margin=(10, 22, 10, 14), mat=mats(ctx, ks), hatch=False)
        V.title(f"{i + 1}. {STEPS[[0, 1, 2, 3][i]][0].upper()}", h=T_N + 0.5)
    rows = []
    for i, (t, d) in enumerate(STEPS):
        txt = d
        if "%" in d:
            vals = {"Mesa soldada": (g.N_pin, f(g.d_pin)), "Pasadores de empuje": (g.N_pin, f(g.d_pin)), "Pivote y buje": (f(P["D_piv"]),), "Base soldada": (f(P["D_piv"]),)}[t]
            txt = d % vals
        rows.append([str(i + 1), t, txt])
    s.table(x0, y0 + 0.5 * (y1 - y0), [("Paso", 14, "C"), ("Etapa", 50, "L"), ("Descripción", x1 - x0 - 68, "L")], rows, h=T_S, title="SECUENCIA (taller sin torno vertical: gran diámetro por corte, soldadura y mandrinadora)")
    s.notes_block(c.low[0], c.low[3], "NOTAS", [NOTA_VIENTO, NOTA_ANCLAJE, "Peso del equipo y puntos de izaje de la base: ver CON-001 y BAS-001 (4 orejas).", "No se prevé fabricar sobre la losa del cliente; la base se entrega soldada y aliviada."], h=T_N, width=500)
    c.h.escala = "S/E"
    return c.h


def sub_sheet_tail(c, keys, weld_ids, notes, comp=False):
    """Resumen de despiece (columna derecha) + notas; tabla de soldaduras completa (franja inferior)."""
    ctx, s = c.ctx, c.s
    r = c.right
    y, _ = c.compact_table(keys)
    s.notes_block(r[0], y - 6, "NOTAS DEL SUBCONJUNTO", notes + notas_gen_fab(ctx)[:2], h=T_N, width=r[2] - r[0] - 2, numbered=True)
    x0, y0, x1, y1 = c.low
    if weld_ids:
        tabla_soldaduras(ctx, s, x0, y1 - 1, weld_ids, x1 - x0, ymin=y0 - 2, title="TABLA DE SOLDADURAS DEL SUBCONJUNTO")
    else:
        y2, _ = tabla_despiece(ctx, s, x0, y1 - 1, keys, x1 - x0, ymin=y0, title="DESPIECE DEL SUBCONJUNTO (completo)", total=True)


@con
def sheet_base_soldada(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    B, tb, xg = g.B, g.tb, P["x_g"]
    ks = ["base_plancha", "collar", "marco_largo", "marco_corto", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "orejas", "bancada"]
    ks = [k for k in ks if ctx.m.get(k)]
    c = Conj(ctx, 6, ks, "BASE SOLDADA: CONJUNTO (PLANTA, ELEVACIONES, CORTES Y DETALLES DE JUNTA)", material="ASTM A572 Gr.50 (Fy ≥ %s MPa); plancha base Z35" % f(P["Fy"]), trat="Alivio de tensiones 590–620 °C")
    s = c.s
    x0, y0, x1, y1 = c.views
    Wd, Ht = x1 - x0, y1 - y0
    sh, mm = ctx.sh(*ks), mats(ctx, ks)
    xs = x0 + 0.40 * Wd
    Vp = c.V(sh, "top", (x0, y0 + 0.38 * Ht, xs, y1), label="Planta", margin=(30, 26, 26, 26), mat=mm, hatch=False)
    balloons_auto(c, Vp, ks, gap=12, off=14)
    Vp.dimh((-B / 2, B / 2, tb), (B / 2, B / 2, tb), "top", 0, on=["base_plancha"], text=f"{f(B)}")
    Vp.chain_h([(-xg, -B / 2, tb), (0, -B / 2, tb), (xg, -B / 2, tb)], "bottom", 0, on=["base_plancha"]) if False else None
    Vp.dimh((-xg, B / 2, tb), (xg, B / 2, tb), "top", 1, on=["base_plancha"], text=f"{f(2 * xg)} (entre ejes de bancadas)")
    s.cut_line(Vp.P(-B / 2 - 20, 0, tb), Vp.P(B / 2 + 20, 0, tb), "A", 90)
    c1 = ctx.D["cilindros"]["horario"][0]["eye"]
    s.cut_line(Vp.P(c1[0], -B / 2 - 20, tb), Vp.P(c1[0], B / 2 + 20, tb), "B", 180)
    Vp.title("PLANTA")
    xr = xs + 6
    VA = c.V(sh, "front", (xr, y0 + 0.66 * Ht, x1, y1), label="Corte A-A", cut=CUT_Y, margin=(24, 26, 24, 22), mat=mm, hatch_scale=0.5)
    balloons_auto(c, VA, [k for k in ks if k not in ("orejas",)], pred=lambda q: q[1] >= -0.5, gap=12, off=12)
    VA.dimv((B / 2, 0, 0), (B / 2, 0, tb), "right", 0, on=["base_plancha"], text=f"{f(tb)}")
    VA.dimh((-B / 2, 0, 0), (B / 2, 0, 0), "bottom", 0, on=["base_plancha"], text=f"{f(B)}")
    VA.title("CORTE A-A")
    VB = c.V(sh, "right", (xr, y0 + 0.36 * Ht, x1, y0 + 0.66 * Ht), label="Corte B-B", cut=((c1[0], 0, 0), (-1, 0, 0)), margin=(24, 26, 24, 22), mat=mm, hatch_scale=0.5)
    VB.dimv((B / 2, B / 2, 0), (B / 2, B / 2, tb), "right", 0, on=["base_plancha"], text=f"{f(tb)}")
    VB.dimv((-B / 2 + 5, g.BR["H"] and 0, tb) if False else (B / 2, B / 2, tb), (B / 2, B / 2, tb + P["rim_h"]), "right", 1, on=["marco_largo"], text=f"{f(P['rim_h'])}")
    VB.title("CORTE B-B (plano de la ménsula)")
    # detalles de junta (1:2 / 1:1)
    cells = [(x0 + i * Wd / 4, y0, x0 + (i + 1) * Wd / 4, y0 + 0.36 * Ht) for i in range(4)]
    kD = [k for k in ("base_plancha", "marco_largo") if k in ctx.shapes]
    ids = {w["desc"]: w["id"] for w in ctx.welds}
    D1 = c.V(kD, "right", cells[0], label="Detalle D1", cut=CUT_X, center=(0, -B / 2, tb), win=(-30, -tb - 4, 60, P["rim_h"] + 10), margin=(10, 22, 70, 12), hatch_scale=0.35)
    w_sym(c, jids(ctx, "Marco perimetral largo")[0], D1, (0, -B / 2 + P["rim_t"], tb + 3), (22, 24), other=None)
    D1.title("D1: MARCO–PLANCHA", h=T_N + 1.5)
    kb = [k for k in ("base_plancha", "bancada") if k in ctx.shapes]
    D2 = c.V(kb, "front", cells[1], label="Detalle D2", cut=CUT_Y, center=(xg, 0, tb), win=(-100, -tb - 6, 100, P["t_bed"] + 10), margin=(10, 22, 10, 12), hatch_scale=0.35)
    D2.dimh((xg - P["w_bed"] / 2, 0, g.zb), (xg + P["w_bed"] / 2, 0, g.zb), "top", 0, on=["bancada"], text=f"{f(P['w_bed'])}")
    w_sym(c, jids(ctx, "Bancada")[0], D2, (xg - P["w_bed"] / 2, 0, tb + 2), (-18, -26), sh=-1) if False else w_sym(c, jids(ctx, "Bancada")[0], D2, (xg + P["w_bed"] / 2, 0, tb + 2), (14, -30))
    D2.title("D2: BANCADA–PLANCHA", dy=-20, h=T_N + 1.5)
    kc = [k for k in ("base_plancha", "collar") if k in ctx.shapes]
    D3 = c.V(kc, "front", cells[2], label="Detalle D3", cut=CUT_Y, center=(g.D_boss / 2, 0, tb), win=(-110, -tb - 8, 60, g.h_boss + 12), margin=(10, 22, 10, 12), hatch_scale=0.35)
    if g.boss:
        D3.dimv((g.D_boss / 2, 0, tb), (g.D_boss / 2, 0, tb + g.h_boss), "right", 0, on=["collar"], text=f"{f(g.h_boss)}")
        w_sym(c, jids(ctx, "Collar")[0], D3, (g.D_boss / 2, 0, tb + 2), (20, 34), all_round=True)
    D3.title("D3: COLLAR–PLANCHA", h=T_N + 1.5)
    ke = [k for k in ("base_plancha", "mensula_mejilla", "mensula_oreja_inf") if k in ctx.shapes]
    D4 = c.V(ke, "front", cells[3], label="Detalle D4", cut=((c1[0] + 0.0, c1[1] - 150, 0), (0, 1, 0)), center=(c1[0], c1[1] - 150, tb), win=(-140, -tb - 8, 140, g.BR["H"] + 12), margin=(10, 22, 10, 12), hatch_scale=0.35)
    mj = jids(ctx, "Mejillas de ménsula")
    if mj:
        w_sym(c, mj[0], D4, (c1[0] - 0 - g.BR["Wout"] / 2 + 0 if False else c1[0] + g.BR["Win"] / 2 + P["t_ch"], c1[1] - 150, tb + 2), (-5, 40)) if False else None
    D4.title("D4: MÉNSULA (SECCIÓN)", h=T_N + 1.5)
    # esquema de marcado de soldaduras de la oreja de izaje y orejas de ménsula (símbolos en planta)
    ow = jids(ctx, "Orejas de izaje")
    if ow:
        ex, ey = g.ear_pos[0]
        a = Vp.P(ex, ey, tb)
        c.h.weld(ow[0], a, (a[0] - 20, a[1] + 20), sh=-1, L=44) if False else None
    ws = [w["id"] for w in ctx.welds if any(t in w["piezas"] for t in ("BAS", "IZA", "ACC-001"))]
    for w in ws:
        ctx.weld_by_id(w)["sheets"].add(c.h.plano)           # las juntas BAS se indican en detalles D1…D4 y en las láminas de pieza
    sub_sheet_tail(c, ks, ws, ["Soldar en secuencia simétrica; alivio de tensiones antes del mecanizado. Mandrinar Ø%s H7 (plancha + collar) y los ojales Ø%s H9 de las ménsulas en línea." % (f(P["D_piv"]), f(P["d_pp"])),
                               "Tamaños de filete: ver tabla (núcleo o mínimo AWS a confirmar). Todas las juntas tienen símbolo ISO 2553 en las láminas de pieza y en los detalles D1–D3.",
                               f"Posiciones: bancadas en x = ±{f(xg)}; orejas de izaje en (±{f(P['x_lug'])}, ±{f(g.cl_lug)}); ménsulas según BAS-001 (tabla de posiciones).", "Cara de apoyo de la interfaz (Ø%s): planitud 0,20, sin pintura." % f(P["D_top"] + 20)])
    c.finish_scale()
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
    s = c.s
    x0, y0, x1, y1 = c.views
    Wd, Ht = x1 - x0, y1 - y0
    tb, H_, rear, Llug, Win, Wout, tc = g.tb, BR["H"], BR["rear"], BR["Llug"], BR["Win"], BR["Wout"], P["t_ch"]
    zt = tb + H_
    sh = {k: ctx.shapes[k] for k in lk}
    sh2 = dict(sh); sh2["base_C"] = ctx.shapes["base_C"]
    mm = {k: "acero" for k in sh2}
    class Al:
        pass
    # globos: las claves locales se alias a las originales
    orig = ctx.m.get
    ctx.m.get = lambda kk: orig(kk[:-2] if kk.endswith("_C") else kk)
    try:
        Vp = c.V(sh, "top", (x0, y0 + 0.5 * Ht, x0 + 0.55 * Wd, y1), label="Planta", margin=(30, 30, 30, 26), mat=mm, hatch=False)
        balloons_auto(c, Vp, lk, gap=12, off=16)
        Vp.dimh((-rear, Wout / 2, zt), (P["L_ch"] - rear, Wout / 2, zt), "top", 0, on=["mensula_mejilla_C"], text=f"{f(P['L_ch'])}")
        Vp.dimv((P["L_ch"] - rear, -Wout / 2, zt), (P["L_ch"] - rear, Wout / 2, zt), "right", 0, on=["mensula_mejilla_C"], text=f"{f(Wout)}")
        Vp.dimv((Llug - rear, -Win / 2, zt), (Llug - rear, Win / 2, zt), "right", 1, on=["mensula_oreja_sup_C"], text=f"{f(Win)} (luz)")
        Vp.dim_dia((0, 0, zt), P["d_pp"] / 2, 120, on=["mensula_oreja_sup_C"], text=hojas_pie.tol_txt(P["d_pp"], "H9"), ext=24)
        s.cut_line(Vp.P(-rear - 20, 0, zt), Vp.P(P["L_ch"] - rear + 20, 0, zt), "A", 90)
        Vp.title("PLANTA")
        VA = c.V(sh2, "front", (x0, y0, x0 + 0.55 * Wd, y0 + 0.5 * Ht), label="Corte A-A", cut=CUT_Y, margin=(30, 30, 30, 26), mat=mm, hatch_scale=0.4)
        VA.dimv((Llug - rear, 0, tb), (Llug - rear, 0, zt), "right", 0, on=["mensula_oreja_inf_C", "mensula_oreja_sup_C"], text=f"{f(H_)} (eje a {f(g.hax)} de la cara de apoyo)", )
        VA.dimv((Llug - rear, 0, zt - tc), (Llug - rear, 0, zt), "right", 1, on=["mensula_oreja_sup_C"], text=f"{f(tc)}")
        VA.dimv((Llug - rear, 0, tb), (Llug - rear, 0, tb + BR["spacer"] + tc), "left", 0, on=["mensula_oreja_inf_C"], text=f"{f(BR['spacer'] + tc)}") if False else None
        VA.title("CORTE A-A (plano del eje)")
        VR = c.V(sh2, "right", (x0 + 0.57 * Wd, y0, x1, y0 + 0.5 * Ht), label="Corte B-B", cut=((0, 0, 0), (-1, 0, 0)), margin=(30, 30, 30, 26), mat=mm, hatch_scale=0.4)
        VR.dimh((0, -Wout / 2, tb), (0, Wout / 2, tb), "bottom", 0, on=["mensula_mejilla_C"], text=f"{f(Wout)}")
        VR.dimh((0, -Win / 2, zt), (0, Win / 2, zt), "top", 0, on=["mensula_oreja_sup_C"], text=f"{f(Win)}")
        VR.dimv((0, Wout / 2, tb), (0, Wout / 2, zt), "right", 0, on=["mensula_mejilla_C"], text=f"{f(H_)}")
        VR.title("CORTE B-B (por el eje del ojal)")
        ids = [w["id"] for w in ctx.welds if any(t in w["desc"] for t in ("Mejillas de ménsula", "Oreja superior", "Oreja inferior"))]
        for jid, off in zip(ids, ((-60, 0), (60, 12), (60, -30), (-60, -40))):
            w_sym(c, jid, VR, (Win / 2 + 3 if jid != ids[0] else Wout / 2, 0, tb + H_ / 3 if jid == ids[0] else zt - tc / 2), (off[0] + 35, 28), sh=1) if False else None
        w_sym(c, ids[0], VR, (Wout / 2, 100 * 0 + 0, tb + 2), (30, -30)) if False else None
        c.compact_table(ks) if False else None
    finally:
        ctx.m.get = orig
    for jid in ids:
        ctx.weld_by_id(jid)["sheets"].add(c.h.plano)
    sub_sheet_tail(c, ks, ids, [f"Armar en plantilla sobre la base: mejillas {f(tc)} × {f(H_)} a {f(Win)} de luz; orejas entre mejillas; eje del ojal a {f(g.hax)} ±0,5 de la cara de apoyo.",
                                f"Mandrinar Ø{f(P['d_pp'])} H9 de ambas orejas en línea después de soldar (coaxialidad 0,10). Se fabrican {int(P['n_br'])} ménsulas.",
                                "Filetes: ver tabla; secuencia alternada por lados; MT 100 %."])
    c.finish_scale()
    return c.h
