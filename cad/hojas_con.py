"""Láminas de conjunto y subconjunto con globos de posición ligados al despiece, secuencia de montaje y explosionada. Se componen con el compositor de lámina (layout.py)."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_util import *
import hojas_pie, hojas_base
from hojas_pie import CUT_X, CUT_Y, jids, w_sym, w_out, rot_key
from soldadura_det import add_prep
from pie_a import ra, wd
import propuestas
import iso286
from vistas import View

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


def _vis_tree(V):
    """Segmentos visibles de la vista en coordenadas de papel (para anclar globos sobre líneas realmente dibujadas)."""
    t = getattr(V, "_ptree", None)
    if t is None:
        from shapely.geometry import LineString
        from shapely.strtree import STRtree
        segs = []
        for pl in V.vis:
            pp = [V.Pt2(q) for q in pl]
            for a, b in zip(pp, pp[1:]):
                if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6:
                    segs.append(LineString([a, b]))
        V._psegs = segs
        V._ptree = t = (STRtree(segs) if segs else False)
    return t


def visible_points(ctx, key, V, pred=None):
    """Puntos de la pieza (vértices y puntos sobre sus aristas) que caen sobre una línea VISIBLE dibujada: [(p3, P2)]."""
    from shapely.geometry import Point
    tree = _vis_tree(V)
    sh = ctx.shapes.get(key)
    if sh is None:
        return []
    pts = [(v.X, v.Y, v.Z) for v in sh.Vertices()]
    eds = sh.Edges()
    nper = max(2, min(16, 6000 // max(len(eds), 1)))
    for e in eds:
        for t in range(1, nper):
            try:
                q = e.positionAt(t / nper)
            except Exception:
                continue
            pts.append((q.x, q.y, q.z))
    if len(pts) > 8000:
        pts = pts[::max(1, len(pts) // 8000)]
    out = []
    for p3 in pts:
        if pred and not pred(p3):
            continue
        u, v = V.uv(p3)
        if V.win and not (V.win[0] <= u <= V.win[2] and V.win[1] <= v <= V.win[3]):
            continue
        P2 = V.P(p3)
        if tree:
            q = Point(P2)
            near = [V._psegs[int(i)] for i in tree.query(q.buffer(0.35))]
            if not any(sg.distance(q) <= 0.35 for sg in near):
                continue
        out.append((p3, P2))
    return out


def visible_anchor(ctx, key, V, pred=None, side=None, avoid=(), cands=None):
    """Punto de anclaje del globo sobre una línea VISIBLE de la pieza: el representativo (cerca de la mediana de sus puntos visibles),
    alejado de los anclajes ya usados (avoid) y, a igualdad, hacia el lado del globo. Si no hay puntos visibles, el centro de una cara."""
    vp = cands if cands is not None else visible_points(ctx, key, V, pred)
    if vp:
        xs = sorted(q[1][0] for q in vp); ys = sorted(q[1][1] for q in vp)
        mx, my = xs[len(xs) // 2], ys[len(ys) // 2]
        ext = (xs[-1] - xs[0]) + 1e-6

        def score(q):
            P2 = q[1]
            d = math.hypot(P2[0] - mx, P2[1] - my)
            dmin = min((math.hypot(P2[0] - a[0], P2[1] - a[1]) for a in avoid), default=99.0)
            pen = 400.0 if dmin < 4.0 else (60.0 if dmin < 8.0 else 0.0)
            lat = (P2[0] - xs[0]) if side == "l" else (xs[-1] - P2[0]) if side == "r" else 0.0
            return d + pen + 0.25 * lat
        best = min(vp, key=score)
        return best[0], best[1]
    pt = anchors(ctx, key, V, pred)
    return (pt, V.P(pt)) if pt is not None else None


def _cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) * o(a, b, d) < 0) and (o(c, d, a) * o(c, d, b) < 0)


def balloons_auto(p, V, keys, pred=None, gap=12.0, off=22.0, label_of=None, sides="lr"):
    """Globos en dos columnas (sides="lr": izquierda y derecha) o dos filas (sides="tb": arriba y abajo) en la periferia de la vista;
    las líneas de referencia no se cruzan entre sí (intercambio de globos hasta eliminar cruces) y cada una termina en un punto
    visible de su pieza. Un globo por número de posición."""
    ctx = p.ctx
    x0, y0, x1, y1 = V.ext
    hor = sides in ("tb", "t", "b")
    A_, B_ = (("b", y0 - off), ("t", y1 + off)) if hor else (("l", x0 - off), ("r", x1 + off))
    ax = 1 if hor else 0          # coordenada que decide el lado
    al = 0 if hor else 1          # coordenada a lo largo de la fila/columna
    items, kof, cand = {}, {}, {}
    for k in keys:
        part = ctx.m.get(k)
        if part is None or k not in ctx.shapes:
            continue
        pos = part.pos
        if pos in items:
            continue
        kof[pos] = k
        cand[pos] = visible_points(ctx, k, V, pred)
        avoid = [v[1] for v in items.values()]
        a = visible_anchor(ctx, k, V, pred, None, avoid, cand[pos])
        if a is None:
            continue
        if len(sides) == 2:
            sd = A_[0] if abs(a[1][ax] - A_[1]) <= abs(B_[1] - a[1][ax]) else B_[0]
        else:
            sd = sides
        items[pos] = (sd, a[1])
    if len(sides) == 2:
        for _ in range(60):
            L = [k for k, v in items.items() if v[0] == A_[0]]; R = [k for k, v in items.items() if v[0] == B_[0]]
            if abs(len(L) - len(R)) <= 2:
                break
            big, other = (L, B_[0]) if len(L) > len(R) else (R, A_[0])
            k = max(big, key=lambda kk: items[kk][1][ax] if other == B_[0] else -items[kk][1][ax])
            a = visible_anchor(ctx, kof[k], V, pred, None, [v[1] for kk, v in items.items() if kk != k], cand[k])
            if a is None:
                break
            items[k] = (other, a[1])
    placed = []
    lo0, hi0 = ((x0 - off + 6, x1 + off - 6) if hor else (y0 - off + 6, y1 + off - 6))
    for side, C in (A_, B_):
        its = sorted([(v[1], k) for k, v in items.items() if v[0] == side], key=lambda t: t[0][al])
        if not its:
            continue
        n = len(its)
        lo, hi = lo0, hi0
        g_ = gap if (hi - lo) / max(n - 1, 1) >= gap else max(10.5, (hi - lo) / max(n - 1, 1))
        ys = [a[al] for a, _ in its]
        for i_ in range(1, n):
            ys[i_] = max(ys[i_], ys[i_ - 1] + g_)
        if ys[-1] > hi:
            ys[-1] = hi
            for i_ in range(n - 2, -1, -1):
                ys[i_] = min(ys[i_], ys[i_ + 1] - g_)
        if ys[0] < lo and not hor:
            pass
        segs = [[a, ((y, C) if hor else (C, y)), k] for (a, k), y in zip(its, ys)]
        for _ in range(4 * n * n):
            sw = False
            for i_ in range(n):
                for j_ in range(i_ + 1, n):
                    if _cross(segs[i_][0], segs[i_][1], segs[j_][0], segs[j_][1]):
                        segs[i_][1], segs[j_][1] = segs[j_][1], segs[i_][1]
                        sw = True
            if not sw:
                break
        placed += segs
    # control: cruces entre líneas de referencia de la vista (debe ser 0)
    nx = sum(1 for i_ in range(len(placed)) for j_ in range(i_ + 1, len(placed)) if _cross(placed[i_][0], placed[i_][1], placed[j_][0], placed[j_][1]))
    p.h.cruces_globos = getattr(p.h, "cruces_globos", 0) + nx
    for a, q, pos in placed:
        p.s.balloon(a, q, pos)
        ctx.balloons[p.h.plano].add(pos)
    if placed:
        qs = [q for _, q, _ in placed]
        V.ext = (min(V.ext[0], min(q[0] for q in qs) - 7), min(V.ext[1], min(q[1] for q in qs) - 7), max(V.ext[2], max(q[0] for q in qs) + 7), max(V.ext[3], max(q[1] for q in qs) + 7))


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


def balloon_cb(keys, pred=None, gap=12.0, off=16.0, suf=None, sides="lr"):
    def cb(V, c):
        if suf:
            with alias(c.ctx, suf):
                balloons_auto(c, V, keys, pred=pred, gap=gap, off=off, sides=sides)
        else:
            balloons_auto(c, V, keys, pred=pred, gap=gap, off=off, sides=sides)
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
    ("Izaje y asiento de la mesa", "Izar la mesa con medios definidos por el montajista (decisión del mandante: el cálculo no define puntos de izaje de la mesa) y asentarla sobre el pivote con las holguras axial y radial del collar indicadas en CON-011."),
    ("Pasadores de empuje", "Insertar los %d pasadores Ø%s m6 en los anillos, perno M20 con arandela y torque propuesto (GEN); marcar con pintura de control."),
    ("Tapas y cubierta", "Colocar tapa retenedora del pivote y tapa de inspección; cubierta de madera si corresponde (opción)."),
    ("Control final", "Giro 360° en vacío, prueba hidráulica, prueba de carga y registro de presión de despegue (plan de inspección GEN-003)."),
]




# ======================================================================================================
def holguras_base_mesa(ctx):
    """Holguras reales base–mesa medidas en el modelo 3D (distancia mínima entre sólidos), sin contar la interfaz ni el pivote."""
    G = grupos(ctx)
    mesa = [k for k in G["mesa"] if k in ctx.shapes]
    out = []
    for nm, ks in (("marco perimetral", ["marco_largo", "marco_corto"]), ("ménsulas de cilindro", ["mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf"]),
                   ("bancadas de guía", ["bancada"]), ("orejas de izaje", ["orejas"]), ("collar del pivote", ["collar"])):
        ks = [k for k in ks if k in ctx.shapes]
        if not ks:
            continue
        d = min(ctx.shapes[a].distance(ctx.shapes[b]) for a in mesa for b in ks)
        out.append((nm, d))
    return out


@con
def sheet_conjunto(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    ks = all_keys(ctx)
    c = Conj(ctx, 1, ks, "CONJUNTO GENERAL DEL EQUIPO: PLANTA Y CORTE A-A CON COTAS DE INSTALACIÓN")
    s = c.s
    sh, mm = ctx.sh(*ks), mats(ctx, ks)
    B, tb = g.B, g.tb
    top = g.z0 + g.hd
    X = P["x_g"]
    cyl0 = ctx.D["cilindros"]["antihorario"][0]
    ye = abs(cyl0["eye"][1])
    bbp = ctx.shapes["pivote"].BoundingBox()
    zp = (bbp.zmin + bbp.zmax) / 2
    a0 = ctx.D["pasadores"][0]
    pin = polar(g.R_pin, a0)
    cgx = ctx.rep["cg"]
    bc = ctx.shapes["cilindro"].BoundingBox()

    def planta(V, c):
        V.dimh((-B / 2, -B / 2, tb), (B / 2, -B / 2, tb), "bottom", 1, on=["base_plancha"], text=f"{f(B)} (huella de apoyo)")
        V.dimv((B / 2, -B / 2, tb), (B / 2, B / 2, tb), "right", 1, on=["base_plancha"], text=f"{f(B)}")
        V.dimh((0, 0, zp), (X, 0, g.zc), "bottom", 0, on=["pivote", "cilindro"], virt_a=P["D_piv"] / 2, virt_b=P["D_body"] / 2, text=f"{f(X)} (ejes de guía y cilindro)")
        V.dimh((-X, 0, g.zc), (0, 0, zp), "bottom", 0, on=["pivote", "cilindro"], virt_a=P["D_body"] / 2, virt_b=P["D_piv"] / 2, text=f"{f(X)}")
        V.dimv((0, 0, zp), (X, ye, g.zc), "right", 0, on=["pivote", "mensula_oreja_sup"], virt_a=P["D_piv"] / 2, virt_b=P["d_pp"] / 2, text=f"{fm(ye, 0)} (ojal de ménsula)")
        V.dim_dia((0, 0, top), g.Rt, 135, on=["mesa_anillo_sup"], text=f"Ø{f(P['D_top'])} (mesa)", ext=24)
        V.dim((0, 0, zp), (pin[0], pin[1], top), 0, orient="a", on=["pivote", "pasadores"], virt_a=P["D_piv"] / 2, virt_b=g.d_pin / 2, text=f"R{fm(g.R_pin, 0)} (círculo de pasadores)")
        ex, ey = g.ear_pos[0]
        so = min(ctx.shapes["orejas"].Solids(), key=lambda q: math.hypot(q.Center().x - ex, q.Center().y - ey))
        vx = max(so.Vertices(), key=lambda q: (round(q.Z, 1), q.X + q.Y))
        V.note_pt((vx.X, vx.Y, vx.Z), (30, 18), f"4 orejas de izaje en (±{f(ex)}; ±{fm(ey, 0)})", on=["orejas"],
                  lines=[f"4 orejas de izaje en (±{f(ex)}; ±{fm(ey, 0)})", f"agujero Ø{f(P['d_ear'])} a {f(P['h_ear'])} de la base"])
        pc = V.P((cgx[0], cgx[1], top))
        s.circle(pc, 3.0, "FINA"); s.line((pc[0] - 4.5, pc[1]), (pc[0] + 4.5, pc[1]), "FINA"); s.line((pc[0], pc[1] - 4.5), (pc[0], pc[1] + 4.5), "FINA")
        s.leader((pc[0] + 2.2, pc[1] - 2.2), (pc[0] + 12, pc[1] - 12), "CG")
        c.cut_mark("planta", "A", (-B / 2 - 20, 0, tb), (B / 2 + 20, 0, tb), 90)
        c.cut_mark("planta", "B", (0, -B / 2 - 20, tb), (0, B / 2 + 20, tb), 180)
    c.vs("planta", sh, "top", lv=(1, 2, 2, 1), draw=planta, mat=mm, hatch=False, title="PLANTA (cotas de instalación desde el eje del pivote)", auto=False, w=1.6, extra=(0, 0, 0, 0))

    ycb = (bc.ymin + bc.ymax) / 2

    def cAdims(V, c):
        V.dimv((B / 2, 0, 0), (B / 2, 0, g.tb), "right", 0, on=["base_plancha"], text=f"{f(tb)}")
        V.dimv((B / 2, 0, g.tb), (B / 2, 0, g.tb + P["rim_h"]), "right", 1, on=["marco_corto"], text=f"{f(P['rim_h'])}")
        V.dimv((B / 2, 0, 0), (g.Rt, 0, top), "right", 2, on=["base_plancha", "mesa_anillo_sup"], text=f"{f(top)}")
        V.dimv((-g.Rt, 0, g.z0), (-g.Rt, 0, top), "left", 0, on=["mesa_anillo_inf", "mesa_anillo_sup"], text=f"{f(g.hd)}")
        V.dimv((-B / 2, 0, tb), (-cyl0["x"], ycb, g.zc), "left", 1, on=["base_plancha", "cilindro"], virt_b=P["D_body"] / 2, text=f"{f(g.hax)}")
        pc = V.P((cgx[0], 0, cgx[2]))
        s.circle(pc, 2.5, "FINA"); s.line((pc[0] - 4, pc[1]), (pc[0] + 4, pc[1]), "FINA"); s.line((pc[0], pc[1] - 4), (pc[0], pc[1] + 4), "FINA")
    c.vs("cA", sh, "front", cut=CUT_Y, lv=(2, 1, 3, 1), extra=(0, 22, 0, 22), mat=mm, hs=0.5, title="CORTE A-A (plano y = 0) CON GLOBOS DE POSICIÓN; CG: cruz en círculo", auto=False, w=1.3, mins=0.2,
         draw=chain(cAdims, balloon_cb([k for k in ks], pred=lambda q: q[1] >= -0.5, gap=11.0, off=20.0, sides="tb")))
    c.iso_fill = False
    c.compact_table()
    mt = ctx.rep["masa_total_ensamble"]
    hol = holguras_base_mesa(ctx)
    area = (B / 1000) ** 2
    rows = [["Masa total del ensamble (3D)", f"{f(mt, 1)} kg (piezas del núcleo + comerciales); según el cálculo {f(ctx.M['total'], 1)} kg"],
            ["Centro de gravedad (x; y; z)", "(" + "; ".join(fm(0.0 if abs(v) < 0.05 else v, 1) for v in cgx) + ") mm desde el eje del pivote y la cara inferior de la base (cruz en círculo en planta y corte A-A)"],
            ["Huella de apoyo", f"cara inferior de la plancha base {f(B)} × {f(B)} ({fm(area, 2)} m²); presión media del peso propio {fm(mt * 9.81 / area / 1000, 2)} kPa"],
            ["Ejes de guías y cilindros", f"x = ±{f(X)}; eje de cilindros a z = {f(g.zc)} ({f(g.hax)} sobre la base); ojales de ménsula en y = ±{fm(ye, 0)}"],
            ["Círculo de pasadores", f"{g.N_pin} × Ø{f(g.d_pin)} en R{fm(g.R_pin, 0)}"],
            ["Alturas", f"base {f(tb)}; mesa {f(g.hd)} (cara inferior a z = {f(g.z0)}); total sin cubierta {f(top)}"],
            ["Holguras cubo–collar", f"radial {fm(g.c_boss_r, 0)} mm; axial {fm(g.c_boss_a, 0)} mm"]]
    rows += [["Holguras mesa–base (mínimas, 3D)", "; ".join(f"{nm} {fm(d, 1)} mm" for nm, d in hol)]]
    rows += [["Carga de diseño / interfaz", f"W = {f(P['W_tf'])} tf, excentricidad e = {f(P['e'])} mm / {g.interfaz_nombre}"]]
    c.table_block("DATOS Y COTAS DE INSTALACIÓN", [("Dato", 50, "L"), ("Valor", 190, "L")], rows, wide=True)
    c.note_block("NOTAS DE CONJUNTO", [NOTA_VIENTO, nota_anclaje(ctx), "Subconjuntos: CON-006 (base), CON-007 (ménsula), CON-008/009 (mesa), CON-010 (accionamiento), CON-011 (pivote), CON-012 (interfaz). Corte B-B y vistas complementarias: CON-003.",
                                       "Despiece completo en CON-002; explosionadas CON-004 y CON-018; instructivo de armado CON-005, CON-014 a CON-017 y CON-019 a CON-022."])
    c.build()
    return c.h


@con
def sheet_vistas_conj(ctx):
    g, P = ctx.g, ctx.P
    ks = all_keys(ctx)
    c = Conj(ctx, 3, ks, "CONJUNTO GENERAL: CORTE B-B, ELEVACIÓN FRONTAL Y DETALLE DEL PASADOR")
    sh, mm = ctx.sh(*ks), mats(ctx, ks)
    B, tb = g.B, g.tb
    top = g.z0 + g.hd
    c.vs("cB", sh, "right", cut=CUT_X, lv=(1, 2, 2, 1), mat=mm, hs=0.5, title="CORTE B-B (plano x = 0)", auto=False, w=1.3,
         draw=lambda V, c: V.dimv((B / 2, B / 2, 0), (B / 2, B / 2, g.tb), "right", 0, on=["base_plancha"], text=f"{f(g.tb)}"))
    on = ["base_plancha", "mesa_anillo_sup", "mesa_anillo_inf", "mesa_plancha_sup", "pernos_pasador"]
    on = [k for k in on if k in sh]
    c.vs("elev", sh, "front", lv=(1, 1, 1, 1), mat=mm, hatch=False, title="ELEVACIÓN FRONTAL (cotas de altura en CON-001, corte A-A)", w=1.0, auto=False)
    pk = [k for k in ("pasadores", "pernos_pasador", "mesa_anillo_sup", "mesa_anillo_inf") if k in sh]
    c.vs("det_pin", {k: ctx.shapes[k] for k in pk}, "front", cut=((0, 0, 0), (0, 1, 0)), center=(g.R_pin, 0, top - 100), win=(-90, -130, 90, 110), lv=(1, 2, 1, 1), hs=0.4, maxs=2.0,
         title="DETALLE A: PASADOR, ARANDELA Y PERNO EN EL BORDE DE LA MESA", auto=False, mat={k: ctx.mat.get(k, "acero") for k in pk}, w=1.0,
         draw=balloon_cb(pk, gap=11.0, off=16.0))
    c.note_block("NOTAS", ["Cotas de instalación, centro de gravedad, huella y holguras: CON-001. Dimensiones de fabricación: planos de cada pieza.", NOTA_VIENTO, nota_anclaje(ctx)])
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
        c = Conj(ctx, 2 if n == 1 else 30 + n - 2, keys, f"DESPIECE COMPLETO DEL EQUIPO (HOJA {n})")
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


# ====================================================================================================== ARMADO
ACC_KEYS = ("cilindro", "patin", "una", "pasador_vastago", "pasador_ojal")
PIV_KEYS = ("pivote", "buje", "tapa_ret")


def int_side(k):
    """Lado de la interfaz: 'mesa' (fijado bajo la mesa) o 'base' (sobre la plancha base)."""
    return "mesa" if ("mesa" in k or k in ("int_cara", "graseras")) else "base"


def grupos(ctx):
    """Grupos de montaje (claves presentes en el modelo). La bancada va soldada a la base."""
    m = ctx.m
    has = lambda k: m.get(k) is not None and k in ctx.shapes
    base = [p.key for p in m.parts if p.sub in ("BAS", "IZA") and has(p.key)]
    if has("bancada") and "bancada" not in base:
        base.append("bancada")
    intb = [p.key for p in m.parts if p.sub == "INT" and int_side(p.key) == "base" and has(p.key) and p.key != "int_tapones"]
    intm = [p.key for p in m.parts if p.sub == "INT" and int_side(p.key) == "mesa" and has(p.key) and p.key != "int_tapones"]
    mesa = [p.key for p in m.parts if p.sub == "MES" and p.key not in ("pasadores", "pernos_pasador", "tapa_insp") and has(p.key)]
    return dict(base=base, intb=intb, intm=intm, mesa=mesa, piv=[k for k in PIV_KEYS if has(k)], pins=[k for k in ("pasadores",) if has(k)],
                pernos=[k for k in ("pernos_pasador",) if has(k)], insp=[k for k in ("tapa_insp",) if has(k)], mad=[p.key for p in m.parts if p.sub == "MAD" and has(p.key)],
                acc=[k for k in ACC_KEYS if has(k)])


def _xkey(ctx, k, d, suf):
    nk = k + suf
    ctx.shapes[nk] = ctx.shapes[k].translate(cq.Vector(*d))
    ctx.mat[nk] = ctx.mat.get(k, "acero")
    return nk


def _arrow(s, a, b):
    """Trayectoria de montaje (trazo y punto fino) de a hacia b, con punta de flecha en b (papel)."""
    s.line(a, b, "EJE")
    s.arrow(b, math.atan2(b[1] - a[1], b[0] - a[0]), size=4.0, w=1.4)


def _bb(ctx, keys):
    bb = None
    for k in keys:
        b_ = ctx.shapes[k].BoundingBox()
        bb = b_ if bb is None else bb.add(b_)
    return bb


@con
def sheet_explosionada(ctx):
    """CON-004: explosión real en z por grupos de montaje (base, pivote, interfaz, buje, mesa, pasadores, pernos, tapas, madera), con trayectorias."""
    g = ctx.g
    G = grupos(ctx)
    lo = ("mesa_plancha_inf", "mesa_anillo_inf")
    hi = ("mesa_plancha_sup", "mesa_anillo_sup")
    plan = [(G["base"], 0), ([k for k in G["piv"] if k == "pivote"], 450), ([k for k in G["piv"] if k == "tapa_ret"], 600), (G["intb"], 850), (G["intm"], 1050),
            ([k for k in G["piv"] if k == "buje"], 1200), ([k for k in G["mesa"] if k in lo], 1400), ([k for k in G["mesa"] if k not in lo + hi], 1700),
            ([k for k in G["mesa"] if k in hi], 2000), (G["pins"], 2350), (G["insp"], 2350), (G["pernos"], 2700), (G["mad"], 3100)]
    keys, dz_of = [], {}
    for ks, dz in plan:
        for k in ks:
            nk = _xkey(ctx, k, (0, 0, dz), "_x")
            keys.append(nk)
            dz_of[nk] = dz
    c = Conj(ctx, 4, [k[:-2] for k in keys], "ISOMÉTRICA EXPLOSIONADA POR GRUPOS DE MONTAJE (ACCIONAMIENTO, PIVOTE Y BUJE EN CON-018)")
    zt = g.z0 + g.hd

    def cb(V, c):
        s = c.s
        top = max(dz_of.values()) + zt + 150
        _arrow(s, V.P((0, 0, top)), V.P((0, 0, g.tb + 5)))
        a = ctx.D["pasadores"][0] if isinstance(ctx.D.get("pasadores"), list) else 0.0
        xy = polar(g.R_pin, a)
        _arrow(s, V.P((xy[0], xy[1], 2700 + zt + 80)), V.P((xy[0], xy[1], 1400 + zt + 5)))
        with alias(ctx, "_x"):
            balloons_auto(c, V, keys, gap=12.0, off=26.0)
    c.vs("expl", {k: ctx.shapes[k] for k in keys}, "iso", iso=True, lv=(1, 1, 1, 1), extra=(40, 30, 40, 30), mat=mats(ctx, keys), hatch=False, draw=cb,
         title="ISOMÉTRICA EXPLOSIONADA (desplazamientos en z ilustrativos; trazo y punto: eje de montaje)", auto=False, w=3.0)
    c.compact_table([k[:-2] for k in keys])
    c.note_block("NOTAS", ["Orden de montaje e instrucciones de cada paso: CON-005, CON-014 a CON-017 y CON-019 a CON-022.", "Accionamiento (patín, uña, cilindro, pasadores), pivote, buje y tapa retenedora explotados en CON-018.",
                           "La bancada va soldada a la base (subconjunto BAS)."])
    c.iso_fill = False
    c.build()
    return c.h


@con
def sheet_explosion_acc(ctx):
    """CON-018: pivote, buje y tapa sobre el collar; accionamiento de un lado (bancada, patín, uña, cilindro, pasadores), explotados con trayectorias."""
    g, P = ctx.g, ctx.P
    G = grupos(ctx)
    X = P["x_g"]
    ks = [k for k in ["collar"] + G["piv"] + ["bancada"] + G["acc"] if ctx.m.get(k) and k in ctx.shapes]
    c = Conj(ctx, 18, ks, "ISOMÉTRICAS EXPLOSIONADAS: PIVOTE CON BUJE Y TAPA RETENEDORA; ACCIONAMIENTO (UN LADO)")
    pk, pz = [], {}
    c.fmt_try = ["A2", "A1"]
    for k, dz in (("collar", 0), ("pivote", 300), ("buje", 600), ("tapa_ret", 820)):
        if k in ctx.shapes:
            ctx.local(k, k + "_P", near=(0, 0, 0), r=260, shift=(0, 0, dz))
            pk.append(k + "_P")
            pz[k] = dz

    def cbp(V, c):
        bb = _bb(ctx, pk)
        _arrow(c.s, V.P((0, 0, bb.zmax + 60)), V.P((0, 0, g.tb + 3)))
        with alias(ctx, "_P"):
            balloons_auto(c, V, pk, gap=12.0, off=22.0)
    c.vs("piv", {k: ctx.shapes[k] for k in pk}, "iso", iso=True, lv=(1, 1, 1, 1), extra=(30, 20, 30, 20), mat=mats(ctx, pk), hatch=False, draw=cbp,
         title="PIVOTE, BUJE Y TAPA RETENEDORA (sobre el collar de la base)", auto=False, w=1.0)
    ak, plan = [], (("bancada", 0), ("patin", 260), ("una", 470), ("pasador_vastago", 640), ("cilindro", 840), ("pasador_ojal", 1060))
    for k, dz in plan:
        if k in ctx.shapes:
            ctx.local(k, k + "_E", near=(X, 0, g.tb + 80), r=1100, shift=(0, 0, dz))
            ak.append(k + "_E")

    def cba(V, c):
        for k, dz in plan:
            if k + "_E" in ctx.shapes and dz > 0:
                bb = ctx.shapes[k + "_E"].BoundingBox()
                cx_, cy_ = (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2
                _arrow(c.s, V.P((cx_, cy_, bb.zmin)), V.P((cx_, cy_, bb.zmin - dz + 15)))
        with alias(ctx, "_E"):
            balloons_auto(c, V, ak, gap=12.0, off=24.0)
    c.vs("acc", {k: ctx.shapes[k] for k in ak}, "iso", iso=True, lv=(1, 1, 1, 1), extra=(30, 20, 30, 20), mat=mats(ctx, ak), hatch=False, draw=cba,
         title=f"ACCIONAMIENTO DEL LADO +x (eje de la guía a x = {f(X)} del centro)", auto=False, w=2.0)
    c.compact_table(ks)
    c.note_block("NOTAS", ["El patín entra en la ranura T de la bancada por su extremo (desplazamiento horizontal); la explosión en z es ilustrativa.",
                           "Instrucciones, ajustes y pares: pasos 3 (CON-014), 5 (CON-016), 7 (CON-019) y 8 (CON-020) del instructivo.", "Lado −x: simétrico respecto del eje y."])
    c.iso_fill = False
    c.build()
    return c.h


def pasos(ctx):
    """Pasos del instructivo: (título, previas, nuevas, desplazamiento de inserción, ventana, filas de la tabla del paso)."""
    g, P, m = ctx.g, ctx.P, ctx.m
    G = grupos(ctx)
    import hojas_gen
    IN = inspecciones(ctx)
    insp = lambda frag: next((f"GEN-003 n.° {r[0]}" for r in IN if frag in r[2]), "GEN-003")
    tq = {}
    for r in hojas_gen.torque_rows(ctx):
        tq.setdefault(r[2], r)
    pq = lambda *ks: ", ".join(f"{m.get(k).pos} ({m.get(k).qty})" for k in ks if m.get(k))
    a_piv, a_bu, a_pin, a_pp = ajuste_txt(P["D_piv"], "H7", "p6"), ajuste_txt(g.d_bush, "H7", "s6"), ajuste_txt(g.d_pin, "H7", "m6"), ajuste_txt(P["d_pp"], "H9", "f8")
    for a_ in (a_piv, a_bu, a_pin, a_pp):
        fz = iso286.fit(a_["d"], a_["hole"], a_["shaft"])
        lo, hi = fz["cmin"], fz["cmax"]
        a_["juego"] = (f"aprieto {-hi} a {-lo} µm" if hi <= 0 else f"juego {lo} a {hi} µm" if lo >= 0 else f"aprieto máx. {-lo} µm / juego máx. {hi} µm")
    T = lambda d: (tq.get(f"M{d}") or [None] * 8)[7] or "—"
    S = []
    S.append(("1. BASE SOLDADA", [], G["base"], (0, 0, 0), None, [
        [pq(*G["base"]), "Armar sobre caballetes nivelados: plancha base, collar, marco, ménsulas, orejas de izaje y bancadas; soldar en secuencia simétrica (GEN-007)",
         f"Posiciones ±1 (BAS-001); eje de bancadas x = ±{f(P['x_g'])} ±0,5", "Plantilla, nivel láser", insp("Orejas de izaje")],
        ["—", f"Alivio de tensiones; mandrinar Ø{f(P['D_piv'])} H7 (plancha + collar) y ojales Ø{f(P['d_pp'])} H9 en línea; planear la zona de apoyo",
         f"Planitud 0,20 en Ø{f(P['D_top'] + 20)}; perpendicularidad 0,05", "Mandrinadora, regla", insp("Planitud de la cara de apoyo")]]))
    S.append(("2. MESA SOLDADA", [], G["mesa"], (0, 0, 0), None, [
        [pq(*G["mesa"]), "Armar sobre la plancha inferior: cubo, almas, nervios y anillos; cerrar con la plancha superior; soldar (GEN-007)",
         f"Altura {f(g.hd)} ±0,5; posición angular de nervios ±0,1°", "Plantilla angular", insp("Pasadores de empuje")],
        ["—", f"Alivio; mandrinar {g.N_pin} × Ø{f(g.d_pin)} H7 en PCD Ø{f(2 * g.R_pin)} y el cubo Ø{f(g.d_bush)} H7; planear la cara inferior",
         f"PCD ±0,3; paso {fm(360 / g.N_pin, 3)}° ±0,05°; planitud 0,20", "Mandrinadora, CMM", insp("Pasadores de empuje")]]))
    S.append(("3. PIVOTE EN LA BASE", G["base"], [k for k in G["piv"] if k == "pivote"], (0, 0, 300), (-480, -260, 480, 640), [
        [pq("pivote"), f"Calar el pivote Ø{f(P['D_piv'])} p6 en la plancha base y el collar (H7): con prensa, o enfriando el pivote con hielo seco (≈ −78 °C)",
         f"{a_piv['juego'].capitalize()} (agujero {a_piv['h_lim']}; eje {a_piv['s_lim']})", "Prensa hidráulica o hielo seco; guía de centrado", insp("Pivote:")],
        ["—", "Verificar la perpendicularidad del pivote respecto de la cara de apoyo", "≤ 0,05", "Escuadra, comparador", insp("Pivote:")]]))
    prev4 = G["base"] + G["piv"][:1]
    if G["intb"]:
        rows = [[pq(*G["intb"]), f"Colocar los {g.n_sec} sectores de la base (muesca en la bisectriz) contra las barras de tope soldadas" if "int_tornillo_base" not in G["intb"] or True else "",
                 f"Junta en frío entre sectores {fm(g.junta('disc'), 1)} mm (galga)", "Galgas, plantilla angular", insp("Planitud de la cara de apoyo")]]
        if any("tornillo" in k for k in G["intb"]):
            rows.append(["—", f"Tornillos de posición ISO 10642 M{fm(P['d_tor'], 0)} con fijarroscas (solo posicionan)", f"Par {T(int(P['d_tor']))} N·m (propuesta GEN-008); cabeza bajo la cara", "Torquímetro", insp("Torque")])
        if ctx.m.get("int_tapones"):
            rows.append([pq("int_tapones"), "Tapones de grafito: llegan insertados en los sectores de bronce (taller, INT-102); no se desmontan en obra", "Al ras ±0,05 con la cara deslizante; sin tapones flojos", "Regla, galgas", insp("Planitud de la cara de apoyo")])
        if any("uhmw" in k for k in G["intb"]):
            rows.append(["—", "Colocar los sectores de UHMW en el rebaje entre barras", f"Junta en frío UHMW {fm(g.junta('uhmw'), 1)} mm", "Galgas", insp("Planitud de la cara de apoyo")])
        rows.append(["—", "Limpiar; engrasar la cara deslizante con grasa grafitada NLGI 2" if g.opt != 2 else "Limpiar las caras de deslizamiento (sin partículas)",
                     "Película 0,3–0,5 mm; sin partículas" if g.opt != 2 else "Sin partículas", "Espátula, paño", insp("Giro 360°")])
        S.append(("4. INTERFAZ, LADO BASE (" + g.interfaz_nombre.split(":")[0] + ")", prev4, G["intb"], (0, 0, 350), None, rows))
    else:
        S.append(("4. INTERFAZ ACERO–ACERO: ENGRASE DE LAS CARAS", prev4, [], (0, 0, 0), None, [
            ["—", f"Limpiar y engrasar la zona de apoyo Ø{f(P['D_top'] + 20)} de la base y la cara inferior de la mesa con grasa grafitada NLGI 2",
             "Película 0,3–0,5 mm por cara; sin partículas", "Espátula, paño", insp("Giro 360°")]]))
    new5 = G["mesa"] + G["intm"] + [k for k in G["piv"] if k == "buje"]
    rows5 = [[pq("buje"), f"Prensar el buje en el cubo de la mesa (Ø{f(g.d_bush)} H7/s6)", a_bu["juego"].capitalize(), "Prensa", insp("Pivote:")]]
    if G["intm"]:
        rows5.append([pq(*G["intm"]), "Con la mesa invertida: fijar los sectores bajo la plancha inferior (tornillos de posición) y las graseras",
                      f"Junta en frío {fm(g.junta('disc'), 1)} mm; pares según GEN-008", "Torquímetro, galgas", insp("Torque")])
    rows5.append([pq(*G["mesa"]), "Izar la mesa con los medios del montajista (el cálculo no define puntos de izaje de la mesa), girarla y bajarla sobre el pivote",
                  f"Holgura radial del cubo {fm(g.c_boss_r, 0)} mm y axial {fm(g.c_boss_a, 0)} mm (sin contacto); giro libre a mano", "Medios del montajista; galgas", insp("Pivote:")])
    S.append(("5. BUJE Y MESA SOBRE EL PIVOTE", prev4 + G["intb"], new5, (0, 0, 600), None, rows5))
    S.append(("6. PASADORES DE EMPUJE Y PERNOS", G["base"] + G["mesa"], G["pins"] + G["pernos"], (0, 0, 350), None, [
        [pq("pasadores"), f"Insertar los {g.N_pin} pasadores Ø{f(g.d_pin)} m6 en los anillos (H7) con grasa", f"H7/m6: {a_pin['juego']}", "Martillo de nylon, extractor", insp("Pasadores de empuje")],
        [pq("pernos_pasador"), "Perno ISO 4762 M20×45 cl. 10.9 con arandela en cada pasador; marca de pintura de control", f"Par {T(20)} N·m (propuesta GEN-008)", "Torquímetro", insp("Torque")]]))
    S.append(("7. ACCIONAMIENTO (dos lados)", G["base"] + G["mesa"], G["acc"], (0, 0, 300), None, [
        [pq("patin"), "Introducir cada patín por el extremo de la ranura T de su bancada, con grasa grafitada",
         f"Juego del cuello {fm((P['w_slot'] - g.neck_w) / 2, 1)} mm por lado (galga); deslizamiento libre en toda la carrera", "Galgas", insp("Ranura T")],
        [pq("una"), "Montar la uña con su resorte de retorno en el alojamiento del patín", f"Ajuste {f(P['dog_b'])} H9/f8; retorno libre del resorte", "Manual", insp("Ranura T")],
        [pq("cilindro", "pasador_vastago", "pasador_ojal"), f"Montar el cilindro entre la ménsula y el patín; pasadores Ø{f(P['d_pp'])} f8 engrasados con su retención; conectar mangueras",
         f"H9/f8: {a_pp['juego']}; eje del cilindro a z = {f(g.zc)}", "Aparejo de taller", insp("Prueba hidráulica")]]))
    tap = [k for k in G["piv"] if k == "tapa_ret"] + G["insp"] + G["mad"]
    rows8 = [[pq("tapa_ret"), "Tapa retenedora sobre el extremo del pivote: 4 tornillos M10×25 ISO 10642", f"Par {T(10)} N·m (propuesta GEN-008)", "Torquímetro", insp("Torque")],
             [pq("tapa_insp"), "Tapa de inspección en el rebaje de la plancha superior: 6 tornillos M10 avellanados", f"Par {T(10)} N·m", "Torquímetro", insp("Torque")]]
    if G["mad"]:
        rows8.append([pq(*G["mad"]), "Tablones de madera dentro del anillo (bolsillos sobre los pernos); fijación según MAD-001", "Holgura de montaje contra el anillo según MAD-001", "Manual", "MAD-001"])
    S.append(("8. TAPAS" + (" Y CUBIERTA DE MADERA" if G["mad"] else ""), G["base"] + G["mesa"] + G["pins"] + G["pernos"], tap, (0, 0, 250), None, rows8))
    S.append(("9. PRUEBA EN VACÍO Y RECEPCIÓN", G["base"] + G["mesa"] + G["pins"] + G["pernos"] + G["acc"] + tap, [], (0, 0, 0), None, [
        ["—", "Giro 360° en vacío y luego con carga; registrar la presión de despegue", "Sin agarrotamiento ni ruido; presión ≤ la esperada", "Manómetro", insp("Giro 360°")],
        ["—", "Prueba hidráulica de cilindros y circuito", "Sin fugas", "Bomba de prueba", insp("Prueba hidráulica")],
        ["—", "Control final de pares y marcas de pintura; nivelación sobre la losa con cuñas metálicas si hace falta", "Marcas intactas; nivel ≤ 1 mm/m", "Torquímetro, nivel", insp("Torque")]]))
    return S


SEQ_NUMS = [5, 14, 15, 16, 17, 19, 20, 21, 22]


def _seq_sheet(ctx, num, steps, hoja, ntot):
    g = ctx.g
    keys_all = sorted({k for st in steps for k in st[1] + st[2] if ctx.m.get(k)}, key=lambda k: ctx.m.get(k).pos)
    tt = " · ".join(st[0].split(". ", 1)[1].split(" (")[0] for st in steps)
    c = Conj(ctx, num, keys_all or all_keys(ctx), f"INSTRUCTIVO DE ARMADO, HOJA {hoja} DE {ntot}: {tt}")
    for si, (title, prev, new, d, win, rows) in enumerate(steps):
        prev = [k for k in prev if k in ctx.shapes]
        suf = f"_s{num}{si}"
        nk = [_xkey(ctx, k, d, suf) for k in new if k in ctx.shapes]
        allk = prev + nk
        kw = {}
        if win:
            kw = dict(center=(0, 0, g.tb), win=win)

        def cb(V, c, nk=nk, d=d, suf=suf, prev=prev):
            if nk and prev:
                Vn = View(c.s, {k: ctx.shapes[k] for k in nk}, "iso", V.origin, V.scale, center=V.center, win=V.win, label="nuevas", free=True)
                Vn.draw(layer_vis="VIS", hatch=False)
            if nk and d[2] > 0:
                sol = ctx.shapes[nk[0]].Solids()
                bb = sol[0].BoundingBox() if len(sol) > 1 else _bb(ctx, nk)
                cx_, cy_ = (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2
                _arrow(c.s, V.P((cx_, cy_, bb.zmin - 10)), V.P((cx_, cy_, bb.zmin - d[2] + 10)))
            if nk:
                with alias(ctx, suf):
                    balloons_auto(c, V, nk, gap=11.0, off=20.0)
        lay = "FINA" if (prev and nk) else "VIS"
        leyenda = " (piezas del paso en trazo grueso; lo ya montado en trazo fino)" if lay == "FINA" else ""
        c.vs(f"p{si}", {k: ctx.shapes[k] for k in allk}, "iso", iso=True, lv=(1, 1, 1, 1), extra=(30, 12, 30, 12), mat=mats(ctx, allk), hatch=False, draw=cb, layer=lay,
             title=title + leyenda, auto=False, w=1.0, **kw)
        c.table_block(f"PASO {title}", [("Pos (cant)", 24, "L"), ("Operación", 74, "L"), ("Ajuste / holgura / par a verificar", 56, "L"), ("Herramienta", 30, "L"), ("Control", 22, "L")], rows, wide=True)
    c.note_block("NOTAS", ["Pares de apriete: PROPUESTA (GEN-008), a confirmar por el calculista. Controles: plan de inspección GEN-003.",
                           "Izaje de la mesa: medios del montajista (el cálculo no define puntos de izaje de la mesa). Izaje de la base: 4 orejas (IZA).", nota_anclaje(ctx)])
    c.iso_fill = False
    c.build()
    return c.h


@con
def sheet_secuencia(ctx):
    """CON-005, CON-014…017 y CON-019…022: instructivo de armado por pasos (vista del paso, flecha de inserción, globos y tabla de operación, ajuste, herramienta y control)."""
    S = pasos(ctx)
    grp = [[x] for x in S]      # un paso por lámina: la vista del paso a la mayor escala posible
    return [_seq_sheet(ctx, num, st, n, len(grp)) for n, (num, st) in enumerate(zip(SEQ_NUMS, grp), 1)]


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
    c.vs("planta", sh, "top", lv=(1, 1, 1, 2), extra=(20, 20, 20, 20), draw=planta, mat=mm, hatch=False, title="PLANTA", auto=False, w=4.0)

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
    c.vs("D1", kD, "right", cut=CUT_X, center=(0, -B / 2, tb), win=(-30, -tb - 4, 60, P["rim_h"] + 10), lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), hs=0.35, maxs=2.0, title="D1: MARCO–PLANCHA", auto=dict(on=kD), w=0.8,
         draw=lambda V, c: w_out(c, ids[0], V, (0, -B / 2 + P["rim_t"], tb + 3), "right", other=None, dy=14))
    kb = [k for k in ("base_plancha", "bancada") if k in ctx.shapes]
    c.vs("D2", kb, "front", cut=CUT_Y, center=(xg, 0, tb), win=(-100, -tb - 6, 100, P["t_bed"] + 10), lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), hs=0.35, maxs=2.0, title="D2: BANCADA–PLANCHA", auto=dict(on=kb), w=0.8,
         draw=lambda V, c: w_out(c, ids[1], V, (xg + P["w_bed"] / 2, 0, tb + 2), "right", dy=-14))
    kc = [k for k in ("base_plancha", "collar") if k in ctx.shapes]
    if g.boss:
        c.vs("D3", kc, "front", cut=CUT_Y, center=(g.D_boss / 2, 0, tb), win=(-110, -tb - 8, 60, g.h_boss + 12), lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), hs=0.35, maxs=2.0, title="D3: COLLAR–PLANCHA", auto=dict(on=kc), w=0.8,
             draw=lambda V, c: w_out(c, ids[2], V, (g.D_boss / 2, 0, tb + 2), "right", all_round=True, dy=14))
    ke = [k for k in ("base_plancha", "mensula_mejilla", "mensula_oreja_inf") if k in ctx.shapes]
    c.vs("D4", ke, "front", cut=((c1[0], c1[1] - 150, 0), (0, 1, 0)), center=(c1[0], c1[1] - 150, tb), win=(-140, -tb - 8, 140, g.BR["H"] + 12), lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), hs=0.35, maxs=1.0,
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
        V.dim_dia((0, 0, zt), P["d_pp"] / 2, 60, on=["mensula_oreja_sup_C"], text=tol_txt(P["d_pp"], "H9"), ext=24)
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
    c.vs("elev", sh, "front", lv=(1, 2, 2, 1), mat=mm, hatch=False, title="ELEVACIÓN", auto=dict(on=["mesa_anillo_inf", "mesa_anillo_sup", "mesa_plancha_sup", "mesa_plancha_inf"], tol={}, maxn=6, axes="v"), w=1.0,
         draw=lambda V, c: V.dimh((-g.Rt, 0, g.z0 + g.tpr), (g.Rt, 0, g.z0 + g.tpr), "bottom", 0, on=["mesa_anillo_inf"], text=f"Ø{f(2 * g.Rt)}"))
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
    c.vs("cw", ws, "front", cut=CUT_Y, lv=(1, 1, 2, 2), extra=(20, 20, 20, 20), draw=cw, mat=mm, hs=0.7, title=f"CORTE POR ALMAS (plano a {fm(ang, 2)}°, entre nervios)", auto=False, w=4.0)
    kc = [k for k in ("base_plancha", "collar", "mesa_plancha_inf", "mesa_cubo", "pivote", "buje") if k in ctx.shapes]

    def cc(V, c):
        if g.rebaje:
            V.dimh((g.D_boss / 2, 0, g.tb + g.h_boss / 2), (g.Drb / 2, 0, g.z0 + g.tbo / 2), "top", 0, on=["collar", "mesa_plancha_inf"], text=f"{fm(g.c_boss_r, 0)} (holgura radial)")
            V.dimv((g.D_boss / 2 - 6, 0, g.tb + g.h_boss), (g.D_boss / 2 - 6, 0, g.z_techo), "left", 0, on=["collar", "mesa_cubo"], text=f"{fm(g.c_boss_a, 0)} (holgura axial)")
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
    c.tail(ks, jn, ["Los nervios se cortan entre almas; las almas son continuas; 1 empalme por alma entre nervios.", f"Holguras del collar: radial {fm(g.c_boss_r, 0)} mm y axial {fm(g.c_boss_a, 0)} mm (del cálculo); el cubo gira sin tocar el collar.",
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
    c.vs("cA", sh, "front", cut=CUT_Y, center=(0, 0, 0), win=(-190, -8, 190, top + 20), lv=(2, 2, 3, 2), extra=(20, 20, 40, 20), draw=cA, mat=mm, hs=0.5, title="CORTE A-A (eje del pivote)", auto=False, w=3.0)
    c.vs("det_f", [k for k in ("pivote", "buje", "mesa_cubo") if k in ctx.shapes], "front", cut=CUT_Y, center=(P["D_piv"] / 2, 0, g.z_bush0 + P["L_bush"] / 2), win=(-30, -P["L_bush"] / 2 - 10, 100, P["L_bush"] / 2 + 10), lv=(1, 1, 1, 1), hs=0.35, maxs=2.0,
         title="DETALLE A: AJUSTES DEL BUJE (F7/f7 Y s6/H7)", auto=dict(on=["pivote", "buje", "mesa_cubo"]), mat=mats(ctx, ["pivote", "buje", "mesa_cubo"]), w=1.0)
    ajs = [a for a in hojas_base.ajustes(ctx) if a[0] in ("Pivote en plancha base y collar", "Pivote en buje", "Buje en cubo de la mesa")]
    rows = []
    for (desc, d, ho, sh_, app) in ajs:
        t = hojas_base.ajuste_txt(d, ho, sh_)
        rows.append([desc, f"Ø{fm(d, 0)} {ho}/{sh_}", t["h_lim"], t["s_lim"], t["juego"], t["tipo"]])
    rows.append(["Collar en rebaje de la plancha inferior", f"Ø{f(g.D_boss)} / Ø{f(g.Drb)}", f"{fm(g.Drb, 1)}", f"{fm(g.D_boss, 1)}", f"{fm(g.c_boss_r, 0)} mm (radial)", "sin contacto (del cálculo)"])
    rows.append(["Collar – cubo (axial)", f"{fm(g.h_boss, 0)} vs {fm(g.h_rebaje, 1)}", "—", "—", f"{fm(g.c_boss_a, 0)} mm (axial)", "sin contacto (del cálculo)"])
    c.table_block("AJUSTES Y HOLGURAS DEL PIVOTE (ISO 286, límites calculados)", [("Ajuste", 40, "L"), ("Nominal", 24, "L"), ("Agujero [mm]", 24, "C"), ("Eje [mm]", 24, "C"), ("Juego [µm]", 26, "C"), ("Tipo", 30, "L")], rows)
    c.tail(ks2, [], [f"Pivote Ø{f(P['D_piv'])} p6 en plancha base y collar (H7, aprieto); en el buje F7/f7 con juego, buje s6/H7 prensado en el cubo.",
                     f"Altura de asiento del cubo: collar de {f(g.h_boss)} sobre la base; holgura radial {fm(g.c_boss_r, 0)} mm y axial {fm(g.c_boss_a, 0)} mm (del cálculo): el cubo gira sin tocar el collar.",
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
