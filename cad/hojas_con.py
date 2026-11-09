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
    if fn.__name__ == "sheet_bom":            # el despiece se arma primero: CON-001 cita cuántas hojas tiene
        PLAN_CON.insert(0, PLAN_CON.pop())
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
            return (0.35 * d + pen + 1.0 * lat) if side else (d + pen)
        best = min(vp, key=score)
        return best[0], best[1]
    pt = anchors(ctx, key, V, pred)
    return (pt, V.P(pt)) if pt is not None else None


def _seg_pt(a, b, c):
    """Distancia del punto c al segmento ab (papel)."""
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy or 1e-9
    t = max(0.0, min(1.0, ((c[0] - a[0]) * vx + (c[1] - a[1]) * vy) / L2))
    return math.hypot(a[0] + t * vx - c[0], a[1] + t * vy - c[1])


def _cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) * o(a, b, d) < 0) and (o(c, d, a) * o(c, d, b) < 0)


def balloons_auto(p, V, keys, pred=None, gap=12.0, off=22.0, label_of=None, sides="lr", hug=False):
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
        if hug and not hor and len(sides) == 2:
            # anclaje en el extremo de la pieza hacia el lado más cercano: líneas de referencia cortas
            aL = visible_anchor(ctx, k, V, pred, "l", avoid, cand[pos])
            aR = visible_anchor(ctx, k, V, pred, "r", avoid, cand[pos])
            if aL and aR:
                a, sd = (aL, "l") if (aL[1][0] - A_[1]) <= (B_[1] - aR[1][0]) else (aR, "r")
                items[pos] = (sd, a[1])
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
            a = visible_anchor(ctx, kof[k], V, pred, (other if hug else None), [v[1] for kk, v in items.items() if kk != k], cand[k])
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
        Cs = [C] * n
        if hug and not hor:
            # cada globo junto a la silueta de la vista a su altura (líneas cortas), nunca más afuera que la columna
            from shapely.geometry import box as _bx
            tr = _vis_tree(V)
            for i_, y in enumerate(ys):
                bnd = _bx(x0 - 1e4, y - g_ / 2, x1 + 1e4, y + g_ / 2)
                xs_ = []
                if tr:
                    for ii in tr.query(bnd):
                        it_ = V._psegs[int(ii)].intersection(bnd)
                        if not it_.is_empty:
                            xs_.append(it_.bounds[0] if side == "l" else it_.bounds[2])
                if xs_:
                    Cs[i_] = max(C, min(xs_) - 10.0) if side == "l" else min(C, max(xs_) + 10.0)
        segs = [[a, ((y, C) if hor else (Cs[i_], y)), k] for i_, ((a, k), y) in enumerate(zip(its, ys))]

        def _near(a, b, c, r=5.6):
            vx, vy = b[0] - a[0], b[1] - a[1]
            L2 = vx * vx + vy * vy or 1e-9
            t = max(0.0, min(1.0, ((c[0] - a[0]) * vx + (c[1] - a[1]) * vy) / L2))
            return math.hypot(a[0] + t * vx - c[0], a[1] + t * vy - c[1]) < r

        def _bad(i_, j_):
            A1, Q1, A2, Q2 = segs[i_][0], segs[i_][1], segs[j_][0], segs[j_][1]
            return _cross(A1, Q1, A2, Q2) or _near(A1, Q1, Q2) or _near(A2, Q2, Q1)
        def _untangle():
            for _ in range(4 * n * n):
                sw = False
                for i_ in range(n):
                    for j_ in range(i_ + 1, n):
                        if _bad(i_, j_):
                            segs[i_][1], segs[j_][1] = segs[j_][1], segs[i_][1]
                            sw = True
                if not sw:
                    return True
            return False
        _untangle()
        anybad = lambda: any(_bad(i_, j_) for i_ in range(n) for j_ in range(i_ + 1, n))
        if anybad():
            # con la columna ajustada a la silueta no se pudo destrabar: columna recta
            segs = [[a, ((y, C) if hor else (C, y)), k] for (a, k), y in zip(its, ys)]
            _untangle()
        if anybad():
            # último recurso: línea quebrada; tramo oblicuo hasta un quiebre a 14 mm de la columna y tramo recto al globo
            # (con los anclajes ordenados como los globos, los tramos oblicuos llegan a una misma recta y no se cruzan)
            sg = (1 if side in ("l", "b") else -1)
            tg = [(((y, C) if hor else (C, y)), ((y, C + sg * 16) if hor else (C + sg * 16, y))) for y in ys]
            segs = [[a, tg[i_][0], k, tg[i_][1]] for i_, (a, k) in enumerate(its)]
            # 2-opt: intercambiar destinos de tramos oblicuos que se cruzan (cada intercambio acorta el total: termina sin cruces)
            for _ in range(8 * n * n):
                sw = False
                for i_ in range(n):
                    for j_ in range(i_ + 1, n):
                        if _cross(segs[i_][0], segs[i_][3], segs[j_][0], segs[j_][3]):
                            segs[i_][1], segs[j_][1] = segs[j_][1], segs[i_][1]
                            segs[i_][3], segs[j_][3] = segs[j_][3], segs[i_][3]
                            sw = True
                if not sw:
                    break
        placed += segs
    # control: cruces entre líneas de referencia de la vista (debe ser 0)
    pieces = [([(sg_[0], sg_[3]), (sg_[3], sg_[1])] if len(sg_) > 3 else [(sg_[0], sg_[1])]) for sg_ in placed]
    nx = 0
    for i_ in range(len(placed)):
        for j_ in range(len(placed)):
            if i_ == j_:
                continue
            if j_ > i_ and any(_cross(a1, b1, a2, b2) for (a1, b1) in pieces[i_] for (a2, b2) in pieces[j_]):
                nx += 1
            if any(_seg_pt(a1, b1, placed[j_][1]) < 5.4 for (a1, b1) in pieces[i_]):
                nx += 1
    p.h.cruces_globos = getattr(p.h, "cruces_globos", 0) + nx
    import os as _os
    if nx and _os.environ.get("PLANDBG"):
        for i_ in range(len(placed)):
            for j_ in range(len(placed)):
                if i_ != j_ and (any(_cross(a1, b1, a2, b2) for (a1, b1) in pieces[i_] for (a2, b2) in pieces[j_]) or any(_seg_pt(a1, b1, placed[j_][1]) < 5.4 for (a1, b1) in pieces[i_])):
                    print("CRUCE", p.h.plano, placed[i_][2], [tuple(round(v, 1) for v in q_) for q_ in (placed[i_][0], placed[i_][1])], len(placed[i_]), "|", placed[j_][2], [tuple(round(v, 1) for v in q_) for q_ in (placed[j_][0], placed[j_][1])])
    for sg_ in placed:
        a, q, pos = sg_[0], sg_[1], sg_[2]
        if len(sg_) > 3:
            p.s.line(a, sg_[3], "COTA")
            p.s.dot(a, 0.8)
            p.s.balloon(sg_[3], q, pos, dot=False)
        else:
            p.s.balloon(a, q, pos)
        ctx.balloons[p.h.plano].add(pos)
    if placed:
        qs = [sg_[1] for sg_ in placed]
        V.ext = (min(V.ext[0], min(q[0] for q in qs) - 7), min(V.ext[1], min(q[1] for q in qs) - 7), max(V.ext[2], max(q[0] for q in qs) + 7), max(V.ext[3], max(q[1] for q in qs) + 7))


class Conj(Plano):
    """Lámina de conjunto: cabecera genérica (código de lámina CON-nnn)."""

    def __init__(self, ctx, num, keys, titulo, fmt="A1", material="Ver despiece", trat="Ver notas", masa=None):
        self.keys = [k for k in keys if ctx.m.get(k)]
        self.p0 = ctx.m.get(self.keys[0]) if self.keys else None
        masa = masa or f"{f(ctx.mass_of(*self.keys), 1)} kg (conjunto)"
        h = Hoja(ctx, f"CON-{num:03d}", titulo, "", fmt=fmt, material=material, masa=masa, trat=trat, serie="CON", items=[ctx.code(k) for k in self.keys])
        self.init_plano(ctx, h)
        self.iso_keys = [k for k in self.keys if k in ctx.shapes]
        self.fmt_try = None

    def compact_table(self, keys=None, title="DESPIECE (completo en CON-002)"):
        ctx = self.ctx
        ps = sorted({id(q): q for q in (ctx.m.get(k) for k in (keys or self.keys)) if q}.values(), key=lambda q: q.pos)
        rows = [[str(q.pos), q.code.replace(CODE + "-", ""), q.name, str(q.qty), f(q.mass_total, 1)] for q in ps]
        rows.append(["", "", "TOTAL", "", f(sum(q.mass_total for q in ps), 1)])
        self.table_block(title, [("Pos", 8, "C"), ("Código", 21, "L"), ("Denominación", 41, "L"), ("Cant", 9, "C"), ("kg tot", 16, "R")], rows, bold_rows=(len(rows) - 1,))

    def tail(self, keys, weld_ids, notes, compact=True):
        """Resumen de despiece (una sola tabla por lámina), notas y (franja inferior) tabla de soldaduras del subconjunto (A-38)."""
        ctx = self.ctx
        if compact:
            self.compact_table(keys)
        self.note_block("NOTAS DEL SUBCONJUNTO", list(notes), numbered=True)
        self.note_block(REF_GEN_TIT, [REF_GEN])
        if weld_ids:
            self.weld_block(weld_ids, title="TABLA DE SOLDADURAS DEL SUBCONJUNTO")


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


def cortadas_y0(ctx, ks):
    """Piezas que el plano y = 0 corta de verdad: solo ellas llevan globo en un corte por ese plano (A-05); el resto se identifica en otras láminas."""
    out = []
    for k in ks:
        if k not in ctx.shapes:
            continue
        if any(so.BoundingBox().ymin < -0.5 and so.BoundingBox().ymax > 0.5 for so in ctx.shapes[k].Solids()):
            out.append(k)
    return out


def masa_mesa(ctx, ks):
    """Masa del rótulo de la mesa soldada: sin y con pasadores y pernos (A-26)."""
    sold = [k for k in ks if k not in ("pasadores", "pernos_pasador", "arandela_pasador")]
    return f"{f(ctx.mass_of(*sold), 1)} / {f(ctx.mass_of(*ks), 1)} kg"


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
    if k in ("pernos_pasador", "arandela_pasador"): return EXPL["pernos"]
    if k in ("madera", "madera_anillo"): return EXPL["madera"]
    if sub == "INT": return EXPL["interfaz_m"] if ("mesa" in k or k in ("int_cara", "graseras") or "uhmw" in k) else EXPL["interfaz_b"]
    if sub == "MES": return EXPL["mesa"]
    if k in ("cilindro", "patin", "una", "pasador_vastago", "pasador_ojal"): return EXPL["acc"]
    return 0




STEPS = [
    ("Base soldada", "Armar sobre caballetes nivelados: plancha base, collar, marco, ménsulas, bancadas y orejas de izaje según BAS-001; soldar en secuencia simétrica (ver tabla de soldaduras), alivio de tensiones y mandrinar Ø%s H7 en línea." ),
    ("Mesa soldada", "Armar sobre la plancha inferior: almas y nervios; cerrar con anillos y plancha superior; soldar con control de distorsión (ver tabla de soldaduras); mandrinar los %d agujeros Ø%s H7 de los pasadores en línea y el cubo H7; planear la cara inferior."),
    ("Pivote y buje", "Calar la zona p6 del pivote Ø%s en la plancha base y el collar (prensa o hielo seco); montar el buje s6 en el cubo de la mesa (F7/f7 sobre la zona f7 del pivote)."),
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
                   ("cajones del ojal E", list(CAJON_KEYS)), ("placas-leva", ["placa_leva"]), ("riel-leva y pórticos", ["leva_riel", "leva_pata", "leva_tapa"]),
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
    piv_ = g.modo == 2
    cyl0 = ctx.D["cilindros"]["antihorario"][0]
    ye = abs(cyl0["eye"][1])
    bbp = ctx.shapes["pivote"].BoundingBox()
    zp = (bbp.zmin + bbp.zmax) / 2
    a0 = ctx.D["pasadores"][0]
    pin = polar(g.R_pin, a0)
    cgx = ctx.rep["cg"]
    kcyl = "cilindro_pv" if piv_ else "cilindro"
    bc = ctx.shapes[kcyl].BoundingBox()
    Epv = g.FPV["soporte_E"]["cilindro1"]["centro"] if piv_ else None

    def planta(V, c):
        V.dimh((-B / 2, -B / 2, tb), (B / 2, -B / 2, tb), "bottom", 1, on=["base_plancha"], text=f"{f(B)} (huella de apoyo)")
        V.dimv((B / 2, -B / 2, tb), (B / 2, B / 2, tb), "right", 1, on=["base_plancha"], text=f"{f(B)}")
        if piv_:
            # ojales E (eje de los pasadores E): coordenadas desde el eje del pivote; R_E y φ_E del núcleo en la tabla de datos
            zE = g.FPV["soporte_E"]["z_paredes"][1]
            V.dimh((0, 0, zp), (Epv[0], Epv[1], zE), "bottom", 0, on=["pivote", "cajon_tapa"], virt_a=P["D_piv"] / 2, virt_b=g.FPV["pasador_E"]["d"] / 2, text=f"{fm(Epv[0], 1)} (ojal E)")
            V.dimv((0, 0, zp), (Epv[0], Epv[1], zE), "right", 0, on=["pivote", "cajon_tapa"], virt_a=P["D_piv"] / 2, virt_b=g.FPV["pasador_E"]["d"] / 2, text=f"{fm(abs(Epv[1]), 1)} (ojal E)")
        else:
            V.dimh((0, 0, zp), (X, 0, g.zc), "bottom", 0, on=["pivote", "cilindro"], virt_a=P["D_piv"] / 2, virt_b=P["D_body"] / 2, text=f"{f(X)} (ejes de guía y cilindro)")
            V.dimh((-X, 0, g.zc), (0, 0, zp), "bottom", 0, on=["pivote", "cilindro"], virt_a=P["D_body"] / 2, virt_b=P["D_piv"] / 2, text=f"{f(X)}")
            V.dimv((0, 0, zp), (X, ye, g.zc), "right", 0, on=["pivote", "mensula_oreja_sup"], virt_a=P["D_piv"] / 2, virt_b=P["d_pp"] / 2, text=f"{fm(ye, 0)} (ojal de ménsula)")
        V.dim_dia((0, 0, top), g.Rt, 250, on=["mesa_anillo_sup"], text=f"Ø{f(P['D_top'])} (mesa)", ext=24)
        k135 = min(range(g.N_pin), key=lambda k_: abs(ctx.D["pasadores"][k_] - 135.0))
        pin = polar(g.R_pin, ctx.D["pasadores"][k135])        # pasador a ~135°: la cota no queda sobre el eje A-A ni junto a las cotas de la derecha (A-40)
        t_r = f"R{fm(g.R_pin, 0)} (círculo de pasadores)" if V.scale >= 0.075 else f"R{fm(g.R_pin, 0)}"      # a 1:20 solo el radio (tabla de datos)
        sh_r = max(0.0, 0.5 * (g.R_pin - P["D_piv"] / 2 - g.d_pin / 2) * V.scale - tw(t_r, T_N) / 2 - 4.0)     # N-06: texto junto al pasador, fuera del cubo y del CG
        V.dim((0, 0, zp), (pin[0], pin[1], top), 0, orient="a", on=["pivote", "pasadores"], virt_a=P["D_piv"] / 2, virt_b=g.d_pin / 2, text=t_r, txt_shift=-sh_r)
        ex, ey = g.ear_pos[1]
        so = min(ctx.shapes["orejas"].Solids(), key=lambda q: math.hypot(q.Center().x - ex, q.Center().y - ey))
        vx = max(so.Vertices(), key=lambda q: (round(q.Z, 1), -q.X + q.Y))
        V.note_pt((vx.X, vx.Y, vx.Z), (-12, 22), f"4 orejas de izaje en (±{f(abs(ex))}; ±{fm(ey, 0)})", on=["orejas"],
                  lines=[f"4 orejas de izaje en (±{f(abs(ex))}; ±{fm(ey, 0)})", f"agujero Ø{f(P['d_ear'])} a {f(P['h_ear'])} de la base"])
        pc = V.P((cgx[0], cgx[1], top))
        s.circle(pc, 3.0, "FINA"); s.line((pc[0] - 4.5, pc[1]), (pc[0] + 4.5, pc[1]), "FINA"); s.line((pc[0], pc[1] - 4.5), (pc[0], pc[1] + 4.5), "FINA")
        s.leader((pc[0] + 2.2, pc[1] - 2.2), (pc[0] + 12, pc[1] - 12), "CG")
        c.cut_mark("planta", "A", (-B / 2 - 20, 0, tb), (B / 2 + 20, 0, tb), 90)
        c.cut_mark("planta", "B", (0, -B / 2 - 20, tb), (0, B / 2 + 20, tb), 180)
        a0x = ctx.D["pasadores"][0]                     # A-08: traza del corte X-X de CON-003 (plano radial por el eje del pasador n.° 1)
        c.cut_mark("planta", "X", polar(g.R_pin - 170, a0x) + (top,), polar(g.Rt + 60, a0x) + (top,), (a0x - 90) % 360)
    c.vs("planta", sh, "top", lv=(1, 2, 2, 1), draw=planta, mat=mm, hatch=False, title="PLANTA (cotas de instalación desde el eje del pivote)", auto=False, w=1.6, extra=(0, 0, 0, 0), maxs=0.1)

    ycb = (bc.ymin + bc.ymax) / 2

    def cAdims(V, c):
        V.dimv((B / 2, 0, 0), (B / 2, 0, g.tb), "right", 0, on=["base_plancha"], text=f"{f(tb)}")
        V.dimv((B / 2, 0, g.tb), (B / 2, 0, g.tb + P["rim_h"]), "right", 1, on=["marco_corto"], text=f"{f(P['rim_h'])}")
        V.dimv((B / 2, 0, 0), (g.Rt, 0, top), "right", 2, on=["base_plancha", "mesa_anillo_sup"], text=(f"({f(top)})" if abs(g.delta) < 0.01 else f"{f(top)}"))   # sin interfaz: t_base + h_mesa = total (auxiliar)
        V.dimv((-g.Rt, 0, g.z0), (-g.Rt, 0, top), "left", 0, on=["mesa_anillo_inf", "mesa_anillo_sup"], text=f"{f(g.hd)}")
        if not piv_:
            V.dimv((-B / 2, 0, tb), (-cyl0["x"], ycb, g.zc), "left", 1, on=["base_plancha", "cilindro"], virt_b=P["D_body"] / 2, text=f"{f(g.hax)}")
        pc = V.P((cgx[0], 0, cgx[2]))
        s.circle(pc, 2.5, "FINA"); s.line((pc[0] - 4, pc[1]), (pc[0] + 4, pc[1]), "FINA"); s.line((pc[0], pc[1] - 4), (pc[0], pc[1] + 4), "FINA")
    c.vs("cA", sh, "front", cut=CUT_Y, lv=(2, 1, 3, 1), extra=(0, 22, 0, 22), mat=mm, hs=0.5, title="CORTE A-A (plano y = 0) CON GLOBOS DE POSICIÓN; CG: cruz en círculo", auto=False, w=1.3, mins=0.2,
         draw=chain(cAdims, balloon_cb(cortadas_y0(ctx, ks), pred=lambda q: abs(q[1]) < 0.6, gap=11.0, off=20.0, sides="tb")))
    c.iso_fill = False
    if len(ctx.m.parts) <= 44:                 # con más ítems la tabla resumida desplaza las vistas: el despiece queda solo en CON-002
        c.compact_table()
    mt = ctx.rep["masa_total_ensamble"]
    hol = holguras_base_mesa(ctx)
    area = (B / 1000) ** 2
    gcam = next((x for x in ctx.gaps if x["tema"].startswith("Masa del accionamiento sin dibujar")), None)
    rows = [["Masa total del ensamble (3D)", f"{f(mt, 1)} kg (piezas del núcleo + comerciales); según el cálculo {f(ctx.M['total'], 1)} kg" + (f"; la diferencia incluye la leva de reenganche ({f(ctx.M['cam'], 1)} kg) aún no dibujada: brecha {gcam['id']} (GEN-009)" if gcam else "")],
            ["Centro de gravedad (x; y; z)", "(" + "; ".join(fm(0.0 if abs(v) < 0.05 else v, 1) for v in cgx) + ") mm desde el eje del pivote y la cara inferior de la base (cruz en círculo en planta y corte A-A)"],
            ["Huella de apoyo", f"cara inferior de la plancha base {f(B)} × {f(B)} ({fm(area, 2)} m²); presión media del peso propio {fm(mt * 9.81 / area / 1000, 2)} kPa"],
            (["Accionamiento pivotado (ojales E)", f"E en ({fm(Epv[0], 1)}; {fm(Epv[1], 1)}) y ({fm(-Epv[0], 1)}; {fm(-Epv[1], 1)}): R_E = {f(g.PV['R_E'])}, φ_E = {fm(g.PV['phi_E'], 0)}° y +180°; L_qp = {f(g.PV['L_qp'])}; eje de cilindros a z = {f(g.zc)} ({f(g.hax)} sobre la base); placas-leva: CON-010"] if piv_ else
             ["Ejes de guías y cilindros", f"x = ±{f(X)}; eje de cilindros a z = {f(g.zc)} ({f(g.hax)} sobre la base); ojales de ménsula en y = ±{fm(ye, 0)}"]),
            ["Círculo de pasadores", f"{g.N_pin} × Ø{f(g.d_pin)} en R{fm(g.R_pin, 0)}"],
            ["Alturas", f"base {f(tb)}; mesa {f(g.hd)} (cara inferior a z = {f(g.z0)}); total {'sin cubierta ' if g.wood else ''}{f(top)}"],
            ["Holguras cubo–collar", f"radial {fm(g.c_boss_r, 0)} mm; axial {fm(g.c_boss_a, 0)} mm"]]
    rows += [["Holguras mesa–base (mínimas, 3D)", "; ".join(f"{nm} {fm(d, 1)} mm" for nm, d in hol)]]
    rows += [["Carga de diseño / variante", f"W = {f(P['W_tf'])} tf, excentricidad e = {f(P['e'])} mm / variante {g.variante}: {g.variante_nombre}"]]
    c.table_block("DATOS Y COTAS DE INSTALACIÓN", [("Dato", 50, "L"), ("Valor", 190, "L")], rows, wide=True)
    subs = "CON-006/023 (base), CON-007 (" + ("cajón del ojal E" if piv_ else "ménsula") + "), CON-008/009 (mesa), CON-010 (accionamiento" + (" pivotado" if piv_ else "") + "), CON-011 (pivote)" + (", CON-012 (interfaz)" if g.opt else "") + \
        (", MAD-001/002 (cubierta de madera)" if g.wood else "") + ". Corte B-B y vistas complementarias: CON-003."
    hojas_bom = "CON-002" + (" y CON-030 (hoja 2)" if getattr(ctx, "bom_hojas", 1) > 1 else "")
    c.note_block("NOTAS DE CONJUNTO", ["Subconjuntos: " + subs, f"Despiece completo en {hojas_bom}; explosionadas CON-004 y CON-018; instructivo de armado CON-005, CON-014 a CON-017 y CON-019 a CON-022.",
                                       REF_GEN_TIT + " (apoyo sin anclaje y viento: nota 4)."])
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
    on = ["base_plancha", "mesa_anillo_sup", "mesa_anillo_inf", "mesa_plancha_sup", "pernos_pasador", "arandela_pasador"]
    on = [k for k in on if k in sh]
    c.vs("elev", sh, "front", lv=(1, 1, 1, 1), mat=mm, hatch=False, title="ELEVACIÓN FRONTAL (cotas de altura en CON-001, corte A-A)", w=1.0, auto=False)
    pk = [k for k in ("pasadores", "pernos_pasador", "arandela_pasador", "mesa_anillo_sup", "mesa_anillo_inf", "mesa_plancha_sup", "mesa_plancha_inf") if k in sh]
    a0_ = ctx.D["pasadores"][0]
    for k in pk:
        rot_key(ctx, k, k + "_P", -a0_)               # el plano del corte pasa por el eje del 1.er pasador (A-09)
    pkp = [k + "_P" for k in pk]

    def dpin(V, c):
        with alias(ctx, "_P"):
            balloons_auto(c, V, [k for k in pkp if not k.startswith("mesa_plancha")], gap=11.0, off=16.0)
        r_ = g.d_pin / 2
        V.dimh((g.R_pin - r_, 0, g.z0 + g.tpr / 2), (g.R_pin + r_, 0, g.z0 + g.tpr / 2), "bottom", 0, on=["mesa_anillo_inf_P"], text=f"Ø{f(g.d_pin)} H7/m6")
        V.dimv((g.R_pin + r_, 0, g.z0), (g.R_pin + r_, 0, g.z0 + g.tpr), "right", 0, on=["mesa_anillo_inf_P"], text=f"{f(g.tpr)}")
        V.dimv((g.R_pin + r_, 0, g.z0 + g.tpr), (g.R_pin + r_, 0, top - g.tpr), "right", 0, on=["mesa_anillo_inf_P", "mesa_anillo_sup_P"], text=f"{f(g.hd - 2 * g.tpr)}")
        V.dimv((g.R_pin + r_, 0, top - g.tpr), (g.R_pin + r_, 0, top), "right", 0, on=["mesa_anillo_sup_P"], text=f"{f(g.tpr)}")
    c.vs("det_pin", {k: ctx.shapes[k] for k in pkp}, "front", cut=((0, 0, 0), (0, 1, 0)), center=(g.R_pin, 0, top - 100), win=(-90, -130, 90, 138), lv=(1, 2, 2, 1), hs=0.4, maxs=2.0,
         title="CORTE X-X POR EL EJE DEL PASADOR N.° 1 (traza en la planta de CON-001; plano a %s° de +x)" % fm(a0_, 3), auto=False, mat={k + "_P": ctx.mat.get(k, "acero") for k in pk}, w=1.0,
         draw=dpin, nocut=("pasadores_P", "pernos_pasador_P"))         # A-09: pasador y perno sin rayar (ISO 128-50)
    c.note_block("NOTAS", ["Cotas de instalación, centro de gravedad, huella y holguras: CON-001. Dimensiones de fabricación: planos de cada pieza.", REF_GEN_TIT + " (apoyo sin anclaje y viento: nota 4)."])
    c.build()
    return c.h


@con
def sheet_bom(ctx):
    """CON-002 (y CON-030 = hoja 2 si hace falta): despiece completo con las posiciones con plano y los elementos comerciales sin plano propio (GEN-008).
    Se corta por bloques lógicos completos (serie de piezas o comerciales), nunca a mitad de un bloque (A-17, A-31)."""
    import lista
    from draw import Sheet
    keys = all_keys(ctx)
    dpart = partida_dict(ctx)
    blocks, cur = [], None
    for p in ctx.m.parts:
        if cur is None or cur[0] != p.sub:
            cur = (p.sub, [])
            blocks.append(cur)
        cur[1].extend(hojas_base.bom_rows_part(ctx, p, dpart))
    ext = [["—", "—", d, str(q), e, "Comercial", "—", "—", cat, "GEN-008"] for (d, q, e, cat) in lista.extras(ctx)]
    blocks.append(("COMERCIAL", ext))
    sc0 = None

    def cols_for(w):
        sc = w / sum(c_[1] for c_ in BOM_COLS)
        return [(t, ww * sc, a_) for t, ww, a_ in BOM_COLS]

    def alto(rows, w, fmt):
        sh = Sheet(fmt)
        y0 = 5000.0
        return y0 - sh.table(0.0, y0, cols_for(w), rows, h=T_S, title="X")[0]
    TIT = "DESPIECE COMPLETO — MATERIAL CON NORMA Y GRADO, CERTIFICADO EN 10204 3.1, DIMENSIÓN DE PARTIDA, MASAS Y PLANO (comerciales sin plano propio: GEN-008)"
    probe = Conj(ctx, 2, keys, "DESPIECE COMPLETO DEL EQUIPO")
    R = probe.h.R["main"]
    avail = (R[3] - R[1]) - 40
    pages, pg = [], []
    for blk in blocks:
        rows_ = [r for b_ in pg for r in b_[1]] + blk[1]
        if pg and alto(rows_, R[2] - R[0], probe.h.fmt) > avail:
            pages.append(pg)
            pg = []
        pg.append(blk)
    pages.append(pg)
    ctx.bom_hojas = len(pages)
    ctx.hojas.remove(probe.h)
    out = []
    for n, pg in enumerate(pages, 1):
        tit = "DESPIECE COMPLETO DEL EQUIPO" + (f" (HOJA {n} DE {len(pages)}" + (", CONTINUACIÓN DE CON-002)" if n > 1 else ")") if len(pages) > 1 else "")
        c = Conj(ctx, 2 if n == 1 else 30 + n - 2, keys, tit)
        R = c.h.R["main"]
        rows = [r for b_ in pg for r in b_[1]]
        y, left = c.s.table(R[0], R[3], cols_for(R[2] - R[0]), rows, h=T_S, ymin=R[1] + 4, title=TIT)
        assert not left, "el despiece no cabe en la hoja"
        if n == len(pages):
            c.s.text(f"MASA TOTAL DEL EQUIPO (todas las posiciones con masa): {f(sum(p.mass_total for p in ctx.m.parts), 1)} kg", (R[0], y - 6), T_N + 1, "TOP_LEFT", bold=True)
        c.h.escala = "S/E"
        c.h.zone = (R[0], R[1], R[2], R[3])
        out.append(c.h)
    return out


# ====================================================================================================== ARMADO
ACC_KEYS = ("cilindro", "patin", "una", "pasador_vastago", "pasador_ojal", "leva_riel", "leva_pata", "leva_tapa", "leva_prolong", "leva_rodillo", "leva_perno", "leva_pernos",
            "cilindro_pv", "pasador_E", "bloque_una", "pasador_Q", "placa_leva", "pernos_placa_leva")
PIV_KEYS = ("pivote", "buje", "tapa_ret")


def int_side(k):
    """Lado de la interfaz: 'mesa' (fijado bajo la mesa) o 'base' (sobre la plancha base)."""
    return "mesa" if ("mesa" in k or k in ("int_cara", "graseras")) else "base"


def grupos(ctx):
    """Grupos de montaje (claves presentes en el modelo). La bancada va soldada a la base."""
    m = ctx.m
    has = lambda k: m.get(k) is not None and k in ctx.shapes
    base = [p.key for p in m.parts if p.sub in ("BAS", "IZA") and has(p.key)]
    for k_ in ("bancada", "leva_prolong", "leva_pata", "leva_tapa"):          # soldadas a la base (subconjunto BAS)
        if has(k_) and k_ not in base:
            base.append(k_)
    intb = [p.key for p in m.parts if p.sub == "INT" and int_side(p.key) == "base" and has(p.key) and p.key != "int_tapones"]
    intm = [p.key for p in m.parts if p.sub == "INT" and int_side(p.key) == "mesa" and has(p.key) and p.key != "int_tapones"]
    mesa = [p.key for p in m.parts if p.sub == "MES" and p.key not in ("pasadores", "pernos_pasador", "arandela_pasador", "tapa_insp") and has(p.key)]
    return dict(base=base, intb=intb, intm=intm, mesa=mesa, piv=[k for k in PIV_KEYS if has(k)], pins=[k for k in ("pasadores",) if has(k)],
                pernos=[k for k in ("arandela_pasador", "pernos_pasador") if has(k)], insp=[k for k in ("tapa_insp",) if has(k)], mad=[p.key for p in m.parts if p.sub == "MAD" and has(p.key)],
                acc=[k for k in ACC_KEYS if has(k) and k not in ("leva_prolong", "leva_pata", "leva_tapa")])


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
    c = Conj(ctx, 4, [k[:-2] for k in keys], "ISOMÉTRICA EXPLOSIONADA POR GRUPOS DE MONTAJE (PIVOTE, BUJE Y TAPAS INCLUIDOS; ACCIONAMIENTO EN CON-018)")
    zt = g.z0 + g.hd

    def cb(V, c):
        s = c.s
        top = max(dz_of.values()) + zt + 150
        _arrow(s, V.P((0, 0, top)), V.P((0, 0, g.tb + 5)))
        a = ctx.D["pasadores"][0] if isinstance(ctx.D.get("pasadores"), list) else 0.0
        xy = polar(g.R_pin, a)
        _arrow(s, V.P((xy[0], xy[1], 2700 + zt + 80)), V.P((xy[0], xy[1], 1400 + zt + 5)))
        with alias(ctx, "_x"):
            balloons_auto(c, V, keys, gap=12.0, off=26.0, hug=True)
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
    if ctx.g.modo == 2:
        return sheet_explosion_acc_pv(ctx)
    g, P = ctx.g, ctx.P
    G = grupos(ctx)
    X = P["x_g"]
    ks = [k for k in ["collar"] + G["piv"] + ["mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "bancada", "leva_prolong", "leva_pata", "leva_tapa"] + G["acc"] if ctx.m.get(k) and k in ctx.shapes]
    c = Conj(ctx, 18, ks, "ISOMÉTRICAS EXPLOSIONADAS: PIVOTE CON BUJE Y TAPA RETENEDORA; ACCIONAMIENTO (UN LADO)")
    pk, pz = [], {}
    c.fmt_try = ["A2", "A1"]
    for k, dz in (("collar", 0), ("pivote", 300), ("buje", 600), ("tapa_ret", 820)):
        if k in ctx.shapes:
            ctx.local(k, k + "_P", near=(0, 0, 0), r=260, shift=(0, 0, dz))
            if ctx.shapes[k + "_P"].Solids():
                pk.append(k + "_P")
            pz[k] = dz

    def cbp(V, c):
        bb = _bb(ctx, pk)
        _arrow(c.s, V.P((0, 0, bb.zmax + 60)), V.P((0, 0, g.tb + 3)))
        with alias(ctx, "_P"):
            balloons_auto(c, V, pk, gap=12.0, off=22.0, hug=True)
    c.vs("piv", {k: ctx.shapes[k] for k in pk}, "iso", iso=True, lv=(1, 1, 1, 1), extra=(30, 20, 30, 20), mat=mats(ctx, pk), hatch=False, draw=cbp,
         title="PIVOTE, BUJE Y TAPA RETENEDORA (sobre el collar de la base)", auto=False, w=1.0)
    c0 = ctx.D["cilindros"]["antihorario"][0]
    ym = (c0["eye"][1] + c0["rodEngage"][1]) / 2          # centro del accionamiento de un lado (ménsula → patín)
    ak, plan = [], (("mensula_mejilla", 0), ("mensula_oreja_inf", 0), ("mensula_oreja_sup", 0), ("bancada", 0), ("leva_prolong", 0), ("leva_pata", 0), ("leva_tapa", 0), ("patin", 260), ("una", 470),
                    ("leva_perno", 560), ("leva_rodillo", 620), ("pasador_vastago", 640), ("cilindro", 840), ("pasador_ojal", 1060), ("leva_riel", 1250), ("leva_pernos", 1400))
    for k, dz in plan:
        if k in ctx.shapes:
            ctx.local(k, k + "_E", near=(c0["x"], ym, g.tb + 80), r=800, shift=(0, 0, dz))
            if ctx.shapes[k + "_E"].Solids():
                ak.append(k + "_E")

    def cba(V, c):
        for k, dz in plan:
            if k + "_E" in ctx.shapes and dz > 0:
                bb = ctx.shapes[k + "_E"].BoundingBox()
                cx_, cy_ = (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2
                _arrow(c.s, V.P((cx_, cy_, bb.zmin)), V.P((cx_, cy_, bb.zmin - dz + 15)))
        with alias(ctx, "_E"):
            balloons_auto(c, V, ak, gap=12.0, off=24.0, hug=True)
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
    if g.modo == 2:
        rows1 = [[pq(*G["base"]), "Armar sobre caballetes nivelados: plancha base, collar, marco, cajones del ojal E (paredes en molinete y tapas) y orejas de izaje; soldar en secuencia simétrica (GEN-007; secuencia del cajón en CON-007)",
                  "Posiciones ±1 (BAS-001); cajones: caras exteriores y eje E en posición 1 / Ø1 respecto de los bordes de la base (CON-007)", "Plantilla, estación total", insp("CONTROL DIMENSIONAL DEL CAJÓN")],
                 ["—", f"Alivio de tensiones; mandrinar Ø{f(P['D_piv'])} H7 (plancha + collar) y las tapas de los cajones Ø{f(g.FPV['pasador_E']['d'])} H9 en línea; roscar las {len(ctx.m.info.get('placa_leva_holes', []))} M{f(g.FPV['placas_leva']['pernos']['d'])} de las placas-leva; planear la zona de apoyo",
                  f"Planitud 0,20 en Ø{f(P['D_top'] + 20)}; coaxialidad de las tapas Ø0,10; roscas en posición Ø0,5", "Mandrinadora, regla", insp("Planitud de la cara de apoyo")]]
    else:
        rows1 = [[pq(*G["base"]), "Armar sobre caballetes nivelados: plancha base, collar, marco, ménsulas, orejas de izaje y bancadas" + (" con sus prolongaciones y los pórticos de la leva" if g.FLG else "") + "; soldar en secuencia simétrica (GEN-007)",
                  f"Posiciones ±1 (BAS-001); eje de bancadas x = ±{f(P['x_g'])} ±0,5", "Plantilla, nivel láser", insp("Posiciones de las piezas soldadas")],
                 ["—", f"Alivio de tensiones; mandrinar Ø{f(P['D_piv'])} H7 (plancha + collar) y ojales Ø{f(P['d_pp'])} H9 en línea; planear la zona de apoyo",
                  f"Planitud 0,20 en Ø{f(P['D_top'] + 20)}; perpendicularidad 0,05", "Mandrinadora, regla", insp("Planitud de la cara de apoyo")]]
    S.append(("1. BASE SOLDADA", ["base_plancha"], [k for k in G["base"] if k != "base_plancha"], (0, 0, 250), None, rows1, dict(mark=["base_plancha"])))
    S.append(("2. MESA SOLDADA", ["mesa_plancha_inf"], [k for k in G["mesa"] if k != "mesa_plancha_inf"], (0, 0, 350), None, [
        [pq(*G["mesa"]), f"Armar sobre la plancha inferior ({fm(g.tbo + 3, 0)}): cubo, almas, nervios, anillo inferior en {fm(g.tpr + 3, 0)} y anillo superior ya planeado a {fm(g.tpr, 0)}; cerrar con la plancha superior; soldar (GEN-007)",
         f"Altura {f(g.hd)} ±0,5; posición angular de nervios ±0,1°", "Plantilla angular", insp("cara inferior de la mesa")],
        ["—", f"Alivio; planear la cara inferior 3 mm (plancha a {fm(g.tbo, 0)}, anillo inferior a {fm(g.tpr, 0)}); mandrinar {g.N_pin} × Ø{f(g.d_pin)} H7 en PCD Ø{f(2 * g.R_pin)} y el cubo Ø{f(g.d_bush)} H7",
         f"Agujeros en posición Ø0,3 respecto del eje de la mesa (PCD Ø{f(2 * g.R_pin)} y paso {fm(360 / g.N_pin, 3)}° teóricamente exactos, MES-002); planitud 0,20", "Mandrinadora, CMM", insp("Pasadores de empuje")]], dict(mark=["mesa_plancha_inf"])))
    # vista local del paso 3: plancha base recortada alrededor del collar (el pivote es chico frente a la base)
    import cadquery as _cq
    if "base_plancha" in ctx.shapes:
        rc = g.D_boss / 2 + 250
        ctx.shapes["base_crop"] = ctx.shapes["base_plancha"].intersect(_cq.Solid.makeBox(2 * rc, 2 * rc, g.tb + 2, _cq.Vector(-rc, -rc, -1)))
        ctx.mat["base_crop"] = ctx.mat.get("base_plancha", "acero")
    S.append(("3. PIVOTE EN LA BASE (vista local: plancha base recortada alrededor del collar)", [k for k in ("base_crop", "collar") if k in ctx.shapes], [k for k in G["piv"] if k == "pivote"], (0, 0, 300), None, [
        [pq("pivote"), f"Calar la zona p6 del pivote Ø{f(P['D_piv'])} (z = 0 a {fm(g.z_p6, 0)}, PIV-001) en la plancha base y el collar (H7): con prensa, o enfriando el pivote con hielo seco (≈ −78 °C)",
         f"{a_piv['juego'].capitalize()} (agujero {a_piv['h_lim']}; eje {a_piv['s_lim']})", "Prensa hidráulica o hielo seco; guía de centrado", insp("Pivote:")],
        ["—", "Verificar la perpendicularidad del pivote respecto de la cara de apoyo", "≤ 0,05", "Escuadra, comparador", insp("Pivote:")]]))
    prev4 = G["base"] + G["piv"][:1]
    if G["intb"]:
        rows = [[pq(*G["intb"]), (f"Colocar los {g.n_sec} sectores de la base (muesca en la bisectriz) contra las barras de tope soldadas" if g.removable else
                                  (f"PEGAR los {g.n_sec} sectores de la base sobre la cara planeada (fijación NO desmontable; en AF2 no hay topes): adhesivo estructural con la preparación de superficie, espesor de capa y curado de la hoja técnica del proveedor"
                                   if ctx.m.get("int_tornillo_af2") else
                                   f"PEGAR los {g.n_sec} sectores de la base sobre la cara planeada (fijación NO desmontable, sin topes ni tornillos): adhesivo estructural, preparación de superficie, espesor de capa y curado A DEFINIR POR EL CALCULISTA con el proveedor del adhesivo")),
                 f"Junta en frío entre sectores {fm(g.junta('disc'), 1)} mm (galga)", "Galgas, plantilla angular", insp("Interfaz y engrase")]]
        if any("tornillo" in k for k in G["intb"]):
            rows.append(["—", f"Tornillos de posición ISO 10642 M{fm(P['d_tor'], 0)} con fijarroscas (solo posicionan)", f"Par {T(int(P['d_tor']))} N·m (propuesta GEN-008); cabeza bajo la cara", "Torquímetro", insp("torques propuestos")])
        if ctx.m.get("int_tapones"):
            rows.append([pq("int_tapones"), "Tapones de grafito: llegan insertados en los sectores de bronce (taller, INT-102); no se desmontan en obra", "Al ras ±0,05 con la cara deslizante; sin tapones flojos", "Regla, galgas", insp("Planitud de la cara de apoyo")])
        if any("uhmw" in k for k in G["intb"]):
            rows.append(["—", "Colocar los sectores de UHMW en el rebaje entre barras", f"Junta en frío UHMW {fm(g.junta('uhmw'), 1)} mm", "Galgas", insp("Interfaz y engrase")])
        rows.append(["—", "Limpiar; engrasar la cara deslizante con grasa grafitada NLGI 2" if g.opt != 2 else "Limpiar las caras de deslizamiento (sin partículas)",
                     "Película 0,3–0,5 mm; sin partículas" if g.opt != 2 else "Sin partículas", "Espátula, paño", insp("Interfaz y engrase")])
        S.append(("4. INTERFAZ, LADO BASE (" + g.interfaz_nombre.split(":")[0] + ("" if g.removable else ", sectores pegados") + ")", prev4, G["intb"], (0, 0, 350), None, rows))
    else:
        S.append(("4. INTERFAZ ACERO–ACERO: ENGRASE DE LAS CARAS", prev4, [], (0, 0, 0), None, [
            ["—", f"Limpiar y engrasar la zona de apoyo Ø{f(P['D_top'] + 20)} de la base y la cara inferior de la mesa con grasa grafitada NLGI 2",
             "Película 0,3–0,5 mm por cara; sin partículas", "Espátula, paño", insp("Interfaz y engrase")]],
            dict(zona=((P["D_top"] + 20) / 2, g.D_boss / 2 + 2, g.tb, [f"Zona de engrase Ø{f(P['D_top'] + 20)} (cara de apoyo de la base)", "grasa grafitada NLGI 2, película 0,3–0,5 mm"]),
                 mark=["base_plancha"])))
    new5 = G["mesa"] + G["intm"] + [k for k in G["piv"] if k == "buje"]
    lf7 = iso286.limits(P["D_piv"], "F7")
    rows5 = [[pq("buje"), f"Prensar el buje en el cubo de la mesa (Ø{f(g.d_bush)} H7/s6); luego escariar o mandrinar el Ø interior a {f(P['D_piv'])} F7 con el buje ya calado (PIV-002)", a_bu["juego"].capitalize(), "Prensa; escariador o mandrinadora", insp("Buje (PIV-002)")],
             ["—", f"Verificar el Ø interior del buje DESPUÉS del calado: {fm(lf7[0], 3)} / {fm(lf7[1], 3)} (F7) en 3 secciones × 2 direcciones; registrar", f"Juego F7/f7 con la zona f7 del pivote {iso286.fit(P['D_piv'], 'F7', 'f7')['cmin']:+d}/{iso286.fit(P['D_piv'], 'F7', 'f7')['cmax']:+d} µm", "Micrómetro de interiores", insp("Buje (PIV-002)")]]
    if G["intm"]:
        gr_ = " y montar las graseras" if any("graser" in k for k in G["intm"]) else ""
        rows5.append([pq(*G["intm"]), ("Con la mesa invertida: fijar los sectores bajo la plancha inferior (tornillos de posición)" + gr_ if g.removable else
                                       ((f"Con la mesa invertida: PEGAR los sectores bajo la mesa y fijarlos con los {int(g.I['tornillos']['n'])} tornillos {g.I['tornillos']['designacion']} (toman el par de la interfaz; NO desmontable)" + gr_)
                                        if ctx.m.get("int_tornillo_af2") else "Con la mesa invertida: PEGAR los sectores bajo la plancha inferior (NO desmontable; adhesivo y curado A DEFINIR POR EL CALCULISTA)" + gr_)),
                      f"Junta en frío {fm(g.junta('disc'), 1)} mm" + ("; pares según GEN-008" if (g.removable or ctx.m.get("int_tornillo_af2")) else "; planitud del conjunto pegado 0,20"),
                      "Torquímetro, galgas" if (g.removable or ctx.m.get("int_tornillo_af2")) else "Galgas, regla", insp("torques propuestos") if (g.removable or ctx.m.get("int_tornillo_af2")) else insp("Planitud de la cara de apoyo")])
    rows5.append([pq(*G["mesa"]), "Izar la mesa con los medios del montajista (el cálculo no define puntos de izaje de la mesa), girarla y bajarla sobre el pivote",
                  f"Holgura radial del cubo {fm(g.c_boss_r, 0)} mm y axial {fm(g.c_boss_a, 0)} mm (sin contacto); giro libre a mano", "Medios del montajista; galgas", insp("Holguras cubo")])
    S.append(("5. BUJE Y MESA SOBRE EL PIVOTE", prev4 + G["intb"], new5, (0, 0, 600), None, rows5))
    S.append(("6. PASADORES DE EMPUJE Y PERNOS", G["base"] + G["mesa"], G["pins"] + G["pernos"], (0, 0, 350), None, [
        [pq("pasadores"), f"Insertar los {g.N_pin} pasadores Ø{f(g.d_pin)} m6 en los anillos (H7) con grasa", f"H7/m6: {a_pin['juego']}", "Martillo de nylon, extractor", insp("Pasadores de empuje")],
        [pq("pernos_pasador", "arandela_pasador"), "Perno ISO 4762 M20×45 cl. 10.9 con su arandela en cada pasador; marca de pintura de control", f"Par {T(20)} N·m (propuesta GEN-008)", "Torquímetro", insp("torques propuestos")]]))
    if g.modo == 2:
        F_ = g.FPV
        aE, aQ = ajuste_txt(F_["pasador_E"]["d"], "H9", "f8"), ajuste_txt(F_["pasador_Q"]["d"], "H9", "f8")
        for a_ in (aE, aQ):
            fz = iso286.fit(a_["d"], a_["hole"], a_["shaft"])
            a_["juego"] = f"juego {fz['cmin']} a {fz['cmax']} µm"
        rows7 = [[pq("placa_leva", "pernos_placa_leva"), f"Empernar las 4 placas-leva a la base (las del sentido horario volteadas): pernos ISO 4762 M{f(F_['placas_leva']['pernos']['d'])}×{ctx.m.info.get('perno_placa_L', '—')} 10.9 en las roscas de BAS-001",
                  f"Par {T(int(F_['placas_leva']['pernos']['d']))} N·m (propuesta GEN-008); canto de contacto libre de rebabas", "Torquímetro", insp("Placas-leva")],
                 [pq("bloque_una", "pasador_Q"), f"Montar el bloque-uña sobre el ojal del vástago con el pasador Q Ø{f(F_['pasador_Q']['d'])} f8 engrasado (extremo templado hacia abajo) y su retención; para el sentido horario el bloque va volteado",
                  f"H9/f8: {aQ['juego']}; el extremo de Q queda {fm(F_['pasador_Q']['z'][0] - g.tb, 0)} mm sobre la base, junto al canto de la placa-leva", "Manual, galgas", insp("Placas-leva")],
                 [pq("cilindro_pv", "pasador_E"), f"Montar el cilindro con el ojal trasero entre las tapas del cajón y el pasador E Ø{f(F_['pasador_E']['d'])} f8 engrasado con su retención; conectar mangueras",
                  f"H9/f8: {aE['juego']}; eje del cilindro a z = {f(g.zc)}; giro libre del cilindro en E hacia ambos lados", "Aparejo de taller", insp("Prueba hidráulica")],
                 ["—", "Verificar a baja presión el recorrido completo: el pie de Q sigue el canto de la placa-leva, el bloque pasa sobre la placa y los pernos y libra el pasador siguiente",
                  f"Holgura bloque–pasador siguiente ≥ {fm(P['pv_cB'], 0)} mm (núcleo); holgura bloque–placa {fm(F_['bloque_una']['z'][0] - F_['placas_leva']['z'][1], 0)} mm", "Galgas", insp("Giro 360°")]]
        S.append(("7. ACCIONAMIENTO PIVOTADO (dos lados)", G["base"] + G["mesa"], G["acc"], (0, 0, 300), None, rows7))
    else:
        rows7 = [
        [pq("patin"), "Introducir cada patín por el extremo de la ranura T de su bancada, con grasa grafitada",
         f"Juego del cuello {fm((P['w_slot'] - g.neck_w) / 2, 1)} mm por lado (galga); deslizamiento libre en toda la carrera", "Galgas", insp("Ranura T")],
        [pq("una"), "Montar la uña con su resorte de retorno en el alojamiento del patín", f"Ajuste {f(P['dog_b'])} H9/f8; retorno libre del resorte", "Manual", insp("Ranura T")],
        [pq("cilindro", "pasador_vastago", "pasador_ojal"), f"Montar el cilindro entre la ménsula y el patín; pasadores Ø{f(P['d_pp'])} f8 engrasados con su retención; conectar mangueras",
         f"H9/f8: {a_pp['juego']}; eje del cilindro a z = {f(g.zc)}", "Aparejo de taller", insp("Prueba hidráulica")]
        ]
        if g.FLG:
            rows7 += [[pq("leva_perno", "leva_rodillo"), "Montar el perno del seguidor en la uña (por la ranura de la tapa del patín) y el rodillo sobre el perno", f"Perno Ø{f(g.FLG['seguidor']['perno']['d'])} libre en la ranura de {f(g.FLG['ranura_tapa_patin']['ancho'])}", "Manual", insp("Riel-leva")],
                      [pq("leva_riel", "leva_pernos"), f"Empernar el riel-leva a las tapas de los pórticos (pernos M{f(g.FLG['porticos']['d_perno'])}); para el otro sentido de giro se voltea", f"Holgura riel–patín ≥ 2 mm; holgura de toma {fm(g.LG['holgura_toma'], 0)} mm (núcleo)", "Torquímetro, galgas", insp("Riel-leva")]]
        S.append(("7. ACCIONAMIENTO (dos lados)", G["base"] + G["mesa"], G["acc"], (0, 0, 300), None, rows7))
    tap = [k for k in G["piv"] if k == "tapa_ret"] + G["insp"] + G["mad"]
    rows8 = [[pq("tapa_ret"), f"Tapa retenedora sobre el extremo del pivote: 4 tornillos M10×{g.cap_L:.0f} ISO 10642", f"Par {T(10)} N·m (propuesta GEN-008)", "Torquímetro", insp("torques propuestos")],
             [pq("tapa_insp"), f"Tapa de inspección en el rebaje de la plancha superior: 6 tornillos ISO 10642 M{fm(g.insp_d, 0)}×{g.insp_L} 10.9", f"Par {T(int(g.insp_d))} N·m", "Torquímetro", insp("torques propuestos")]]
    if G["mad"]:
        rows8.append([pq(*G["mad"]), "Tablones de madera dentro del anillo (bolsillos sobre los pernos); fijación según MAD-001", "Holgura de montaje contra el anillo según MAD-001", "Manual", "MAD-001"])
    S.append(("8. TAPAS" + (" Y CUBIERTA DE MADERA" if G["mad"] else ""), G["base"] + G["mesa"] + G["pins"] + G["pernos"], tap, (0, 0, 250), None, rows8))
    S.append(("9. PRUEBA EN VACÍO Y RECEPCIÓN", G["base"] + G["mesa"] + G["pins"] + G["pernos"] + G["acc"] + tap, [], (0, 0, 0), None, [
        ["—", "Giro 360° en vacío y luego con carga; registrar la presión de despegue", "Sin agarrotamiento ni ruido; presión ≤ la esperada", "Manómetro", insp("Giro 360°")],
        ["—", "Prueba hidráulica de cilindros y circuito", "Sin fugas", "Bomba de prueba", insp("Prueba hidráulica")],
        ["—", "Control final de pares y marcas de pintura; nivelación con apoyo continuo sobre la losa (grout o mats en toda la huella; no se admiten cuñas puntuales salvo verificación del calculista)", "Marcas intactas; nivel ≤ 1 mm/m", "Torquímetro, nivel", insp("torques propuestos")]],
        dict(giro=True)))
    return S


SEQ_NUMS = [5, 14, 15, 16, 17, 19, 20, 21, 22]


def _seq_sheet(ctx, num, steps, hoja, ntot, acum=None):
    g, P = ctx.g, ctx.P
    keys_all = sorted({k for st in steps for k in st[1] + st[2] if ctx.m.get(k)}, key=lambda k: ctx.m.get(k).pos)
    tt = " · ".join(st[0].split(". ", 1)[1].split(" (")[0] for st in steps)
    # masa del rótulo: conjunto acumulado al terminar el paso (A-25); en la última hoja coincide con la masa total del equipo
    masa = f"{f(ctx.mass_of(*acum), 1)} kg (acumulado al terminar el paso)" if acum else None
    c = Conj(ctx, num, keys_all or all_keys(ctx), f"INSTRUCTIVO DE ARMADO, HOJA {hoja} DE {ntot}: {tt}", masa=masa)
    for si, st_ in enumerate(steps):
        title, prev, new, d, win, rows = st_[:6]
        ex_ = st_[6] if len(st_) > 6 else {}
        prev = [k for k in prev if k in ctx.shapes]
        suf = f"_s{num}{si}"
        nk = [_xkey(ctx, k, d, suf) for k in new if k in ctx.shapes]
        allk = prev + nk
        kw = {}
        if win:
            kw = dict(center=(0, 0, g.tb), win=win)

        def cb(V, c, nk=nk, d=d, suf=suf, prev=prev, ex_=ex_):
            if ex_.get("zona"):
                ro, ri, zz, txt = ex_["zona"]
                circ = lambda r: [V.P((r * math.cos(math.radians(t)), r * math.sin(math.radians(t)), zz)) for t in range(0, 360, 4)]
                from shapely.geometry import MultiPoint
                po = circ(ro)
                # hueco: silueta proyectada del collar y del pivote (el achurado no pasa por detrás de ellos)
                zp_ = ctx.shapes["pivote"].BoundingBox().zmax if "pivote" in ctx.shapes else zz
                hull = MultiPoint(circ(ri) + [V.P((P["D_piv"] / 2 * math.cos(math.radians(t)), P["D_piv"] / 2 * math.sin(math.radians(t)), zp_)) for t in range(0, 360, 6)]).convex_hull
                pi = [tuple(q) for q in hull.exterior.coords][:-1]
                c.s.hatch_poly(po, holes=[pi], scale=4.0, pattern="ANSI31")
                c.s.pline(po, "FINA", closed=True)
                pa = max(po, key=lambda q: q[1])
                c.s.leader(pa, (pa[0] + 32, V.ext[3] + 8), txt[0], lines=txt)

            if ex_.get("giro"):
                zt_ = g.z0 + g.hd + 5
                r_ = g.R_pin * 0.55
                pts = [V.P((r_ * math.cos(math.radians(t)), r_ * math.sin(math.radians(t)), zt_)) for t in range(200, 341, 4)]
                c.s.pline(pts, "COTA")
                a_, b_ = pts[-2], pts[-1]
                c.s.arrow(b_, math.atan2(b_[1] - a_[1], b_[0] - a_[0]), size=5.0, w=1.8)
                pm_ = pts[len(pts) // 2]
                c.s.leader(pm_, (pm_[0] + 40, V.ext[3] + 8), "Giro 360° en vacío (sentido antihorario y horario)",
                           lines=["Giro 360° en vacío, en ambos sentidos;", "registrar la presión de despegue (GEN-003)"])
            if nk and prev:
                Vn = View(c.s, {k: ctx.shapes[k] for k in nk}, "iso", V.origin, V.scale, center=V.center, win=V.win, label="nuevas", free=True)
                Vn.draw(layer_vis="VIS", hatch=False)
            if nk and d[2] > 0:
                sol = ctx.shapes[nk[0]].Solids()
                bb = sol[0].BoundingBox() if len(sol) > 1 else _bb(ctx, nk)
                cx_, cy_ = (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2
                _arrow(c.s, V.P((cx_, cy_, bb.zmin - 10)), V.P((cx_, cy_, bb.zmin - d[2] + 10)))
            mk_ = [k for k in ex_.get("mark", []) if k in ctx.shapes]
            if nk or mk_:
                with alias(ctx, suf):
                    balloons_auto(c, V, nk + mk_, gap=11.0, off=20.0, hug=True)
        lay = "FINA" if (prev and nk) else "VIS"
        leyenda = " (piezas del paso en trazo grueso; lo ya montado en trazo fino)" if lay == "FINA" else ""
        c.vs(f"p{si}", {k: ctx.shapes[k] for k in allk}, "iso", iso=True, lv=(1, 1, 1, 1), extra=(30, 12, 30, 12), mat=mats(ctx, allk), hatch=False, draw=cb, layer=lay,
             title=title + leyenda, auto=False, w=1.0, **kw)
        c.table_block(f"PASO {title}", [("Pos (cant)", 24, "L"), ("Operación", 74, "L"), ("Ajuste / holgura / par a verificar", 56, "L"), ("Herramienta", 30, "L"), ("Control", 22, "L")], rows, wide=True)
    c.note_block("NOTAS", ["Pares de apriete: PROPUESTA (GEN-008), a confirmar por el calculista. Controles: plan de inspección GEN-003.",
                           "Izaje de la mesa: medios del montajista (el cálculo no define puntos de izaje de la mesa). Izaje de la base: 4 orejas (IZA).", REF_GEN_TIT + "."])
    c.iso_fill = False
    c.build()
    return c.h


@con
def sheet_secuencia(ctx):
    """CON-005, CON-014…017 y CON-019…022: instructivo de armado por pasos (vista del paso, flecha de inserción, globos y tabla de operación, ajuste, herramienta y control)."""
    S = pasos(ctx)
    grp = [[x] for x in S]      # un paso por lámina: la vista del paso a la mayor escala posible
    out, acum = [], []
    for n, (num, st) in enumerate(zip(SEQ_NUMS, grp), 1):
        for s_ in st:
            acum += [k for k in list(s_[1]) + list(s_[2]) if ctx.m.get(k) and k not in acum]
        if n == len(grp):
            acum = [p.key for p in ctx.m.parts]
        out.append(_seq_sheet(ctx, num, st, n, len(grp), acum=list(acum)))
    return out


@con
def sheet_base_soldada(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    B, tb, xg = g.B, g.tb, P["x_g"]
    ks = ["base_plancha", "collar", "marco_largo", "marco_corto", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", *CAJON_KEYS, "orejas", "bancada", "leva_prolong", "leva_pata", "leva_tapa"]
    ks = [k for k in ks if ctx.m.get(k)]
    piv_ = g.modo == 2
    c = Conj(ctx, 6, ks, "BASE SOLDADA: CONJUNTO (PLANTA Y CORTES A-A / B-B; DETALLES EN CON-023)", material="ASTM A572 Gr.50 (Fy ≥ %s MPa) — PROPUESTO; plancha base Z35" % f(P["Fy"]), trat="Alivio de tensiones 590–620 °C")
    s = c.s
    sh, mm = ctx.sh(*ks), mats(ctx, ks)
    c1 = ctx.D["cilindros"]["horario"][0]["eye"] if not piv_ else g.FPV["soporte_E"]["cilindro2"]["centro"]

    def planta(V, c):
        balloons_auto(c, V, [k for k in ks if not k.startswith(("leva_", "cajon_"))], gap=12, off=14, hug=True)      # leva y cajón del ojal E: globos en CON-010 / CON-007
        V.dimh((-B / 2, B / 2, tb), (B / 2, B / 2, tb), "top", 0, on=["base_plancha"], text=f"{f(B)}")
        if not piv_:
            V.dimh((-xg, B / 2, tb), (xg, B / 2, tb), "top", 1, on=["base_plancha"], text=f"{f(2 * xg)} (entre ejes de bancadas)")
        c.cut_mark("planta", "A", (-B / 2 - 20, 0, tb), (B / 2 + 20, 0, tb), 90)
        c.cut_mark("planta", "B", (c1[0], -B / 2 - 20, tb), (c1[0], B / 2 + 20, tb), 180)
        # llamadas de los detalles D1–D4 (dibujados en CON-023), A-07
        for lab, p3 in (("D1", (-B / 4, -B / 2 + P["rim_t"], tb)), ("D2", (xg + P["w_bed"] / 2, -B / 4, tb)), ("D3", (g.D_boss / 2 * 0.7071, -g.D_boss / 2 * 0.7071, tb)),
                        ("D4", (c1[0], c1[1] - 150, tb) if not piv_ else (c1[0], c1[1], tb))):
            if (lab == "D3" and not g.boss) or (lab == "D2" and piv_):
                continue
            q = V.P(p3)
            s.circle(q, 7.0, "FINA")
            s.leader((q[0] + 5.0, q[1] + 5.0), (q[0] + 14, q[1] + 14), f"{lab} (CON-023)")
    c.vs("planta", sh, "top", lv=(1, 1, 1, 2), extra=(20, 20, 20, 20), draw=planta, mat=mm, hatch=False, title="PLANTA (llamadas D1–D4: detalles en CON-023" + ("; roscas de las placas-leva en BAS-001)" if piv_ else ")"), auto=False, w=4.0, mins=0.1)

    def cA(V, c):
        balloons_auto(c, V, [k for k in ks if k not in ("orejas",) and not k.startswith(("leva_", "cajon_"))], pred=lambda q: q[1] >= -0.5, gap=12, off=12, hug=True)
        V.dimv((B / 2, 0, 0), (B / 2, 0, tb), "right", 0, on=["base_plancha"], text=f"{f(tb)}")
        V.dimh((-B / 2, 0, 0), (B / 2, 0, 0), "bottom", 0, on=["base_plancha"], text=f"{f(B)}")
    c.vs("cA", sh, "front", cut=CUT_Y, lv=(1, 1, 1, 1), extra=(16, 4, 16, 4), draw=cA, mat=mm, hs=0.5, title="CORTE A-A", auto=False, w=1.0, mins=0.1)

    def cB(V, c):
        V.dimv((B / 2, B / 2, 0), (B / 2, B / 2, tb), "right", 0, on=["base_plancha"], text=f"{f(tb)}")
        V.dimv((B / 2, B / 2, tb), (B / 2, B / 2, tb + P["rim_h"]), "right", 1, on=["marco_largo"], text=f"{f(P['rim_h'])}")
    c.vs("cB", sh, "right", cut=((c1[0], 0, 0), (-1, 0, 0)), lv=(1, 1, 2, 1), draw=cB, mat=mm, hs=0.5, title="CORTE B-B (plano " + ("del ojal E del cilindro 2)" if piv_ else "de la ménsula)"), auto=False, w=1.0, mins=0.1)
    ws = [w["id"] for w in ctx.welds if any(t in w["piezas"] for t in ("BAS", "IZA", "ACC-001", "ACC-008", "ACC-010"))]
    c.compact_table(ks)
    pos_txt = (f"Posiciones: cajones del ojal E con tolerancia de posición ajustada respecto de los bordes de la base (CON-007); orejas de izaje en (±{f(P['x_lug'])}, ±{f(g.cl_lug)}); placas-leva: roscas en BAS-001." if piv_ else
               f"Posiciones: bancadas en x = ±{f(xg)}; orejas de izaje en (±{f(P['x_lug'])}, ±{f(g.cl_lug)}); ménsulas según BAS-001 (tabla de posiciones)." + (" Prolongaciones y pórticos de la leva: CON-010." if g.FLG else ""))
    c.note_block("NOTAS DEL SUBCONJUNTO", ["Detalles de junta D1–D4 y tabla de soldaduras del subconjunto: CON-023.", pos_txt,
                                           "Soldar en secuencia simétrica; alivio de tensiones 590–620 °C antes del mecanizado."], numbered=True)
    c.note_block(REF_GEN_TIT, [REF_GEN])
    c.build()
    out_h = c.h
    # segunda lámina: detalles de junta y tabla de soldaduras (la planta queda a 1:10 en CON-006)
    c = Conj(ctx, 23, ks, "BASE SOLDADA: DETALLES DE JUNTA D1–D4 Y TABLA DE SOLDADURAS DEL SUBCONJUNTO", material="ASTM A572 Gr.50 (Fy ≥ %s MPa) — PROPUESTO; plancha base Z35" % f(P["Fy"]), trat="Alivio de tensiones 590–620 °C")
    h1 = out_h
    kD = [k for k in ("base_plancha", "marco_largo") if k in ctx.shapes]
    ids = [(ctx.weld_find(fr_) or {}).get("id", "J??") for fr_ in ("Marco perimetral largo", "Bancada", "Collar", "Mejillas de ménsula" if not piv_ else "Paredes del cajón")]
    c.vs("D1", kD, "right", cut=CUT_X, center=(0, -B / 2, tb), win=(-30, -tb - 4, 60, P["rim_h"] + 10), lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), hs=0.35, maxs=2.0, title="D1: MARCO–PLANCHA", auto=dict(on=kD), w=0.8,
         draw=lambda V, c: w_out(c, ids[0], V, (0, -B / 2 + P["rim_t"], tb + 3), "right", other=None, dy=14))
    kb = [k for k in ("base_plancha", "bancada") if k in ctx.shapes]
    if not piv_:
     c.vs("D2", kb, "front", cut=CUT_Y, center=(xg, 0, tb), win=(-100, -tb - 6, 100, P["t_bed"] + 10), lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), hs=0.35, maxs=2.0, title="D2: BANCADA–PLANCHA", auto=dict(on=kb), w=0.8,
         draw=lambda V, c: w_out(c, ids[1], V, (xg + P["w_bed"] / 2, 0, tb + 2), "right", dy=-14))
    kc = [k for k in ("base_plancha", "collar") if k in ctx.shapes]
    if g.boss:
        c.vs("D3", kc, "front", cut=CUT_Y, center=(g.D_boss / 2, 0, tb), win=(-110, -tb - 8, 60, g.h_boss + 12), lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), hs=0.35, maxs=2.0, title="D3: COLLAR–PLANCHA", auto=dict(on=kc), w=0.8,
             draw=lambda V, c: w_out(c, ids[2], V, (g.D_boss / 2, 0, tb + 2), "right", all_round=True, dy=14))
    if not piv_:
        ke = [k for k in ("base_plancha", "mensula_mejilla", "mensula_oreja_inf") if k in ctx.shapes]
        c.vs("D4", ke, "front", cut=((c1[0], c1[1] - 150, 0), (0, 1, 0)), center=(c1[0], c1[1] - 150, tb), win=(-140, -tb - 8, 140, g.BR["H"] + 12), lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), hs=0.35, maxs=1.0,
             title="D4: MÉNSULA (SECCIÓN)", auto=dict(on=ke), w=0.8, draw=lambda V, c: w_out(c, ids[3], V, (c1[0] + g.BR["Win"] / 2 + P["t_ch"], c1[1] - 150, tb + 2), "right", dy=14))
    else:
        S_ = g.FPV["soporte_E"]
        ke = [k for k in ("base_plancha", *CAJON_KEYS) if k in ctx.shapes]
        L2 = S_["lado"] / 2
        c.vs("D4", ke, "front", cut=((c1[0], c1[1], 0), (0, 1, 0)), center=(c1[0], c1[1], tb), win=(-L2 - 40, -tb - 8, L2 + 40, S_["alto_paredes"] + 12), lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), hs=0.35, maxs=1.0,
             title="D4: CAJÓN DEL OJAL E (SECCIÓN; detalle completo en CON-007)", auto=dict(on=ke, maxn=6), w=0.8,
             draw=lambda V, c: w_out(c, ids[3], V, (c1[0] - L2, c1[1], tb + 1), "right", dy=14) if len(ids) > 3 else None)
    c.tail(ks, ws, ["Soldar en secuencia simétrica; alivio de tensiones antes del mecanizado. Mandrinar Ø%s H7 (plancha + collar) y " % f(P["D_piv"]) + ("los agujeros Ø%s H9 de las tapas de los cajones en línea." % f(g.FPV["pasador_E"]["d"]) if piv_ else "los ojales Ø%s H9 de las ménsulas en línea." % f(P["d_pp"])),
                    "Tamaños de filete: ver tabla (núcleo o mínimo AWS a confirmar). Todas las juntas tienen símbolo ISO 2553 en las láminas de pieza y en los detalles D1–D4.",
                    pos_txt, "Cara de apoyo de la interfaz (Ø%s): planitud 0,20, sin pintura." % f(P["D_top"] + 20),
                    "Ubicación de los detalles: llamadas D1–D4 en la planta de CON-006."])
    c.build()
    return [h1, c.h]


@con
def sheet_mensula_conj(ctx):
    if ctx.g.modo == 2:
        return sheet_cajon_conj(ctx)
    g, P, BR = ctx.g, ctx.P, ctx.g.BR
    c1 = ctx.D["cilindros"]["horario"][0]
    E, ph = c1["eye"], c1["phiMean"]
    ks = ["mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf"]
    for k in ks:
        ctx.local(k, k + "_C", near=(E[0], E[1], 80), r=300, shift=(-E[0], -E[1], 0), rot=-ph)
    ctx.local("base_plancha", "base_C", shift=(-E[0], -E[1], 0), rot=-ph)
    lk = [k + "_C" for k in ks]
    c = Conj(ctx, 7, ks, "MÉNSULA DE CILINDRO: SUBCONJUNTO SOLDADO (PLANTA, CORTES Y DETALLE)", material="ASTM A572 Gr.50", trat="Alivio de tensiones")
    c.iso_keys = lk
    tb, H_, rear, Llug, Win, Wout, tc = g.tb, BR["H"], BR["rear"], BR["Llug"], BR["Win"], BR["Wout"], P["t_ch"]
    zt = tb + H_
    sh = {k: ctx.shapes[k] for k in lk}
    sh2 = dict(sh); sh2["base_C"] = ctx.shapes["base_C"]
    mm = {k: "acero" for k in sh2}
    ids = [w["id"] for w in ctx.welds if any(t in w["desc"] for t in ("Mejillas de ménsula", "Oreja superior", "Oreja inferior"))]

    def planta(V, c):
        V.dimh((-rear, Wout / 2, zt), (P["L_ch"] - rear, Wout / 2, zt), "top", 0, on=["mensula_mejilla_C"], text=f"{f(P['L_ch'])}")
        V.dimv((P["L_ch"] - rear, -Wout / 2, zt), (P["L_ch"] - rear, Wout / 2, zt), "right", 0, on=["mensula_mejilla_C"], text=f"{f(Wout)}", txt_shift=-30)
        V.dimv((Llug - rear, -Win / 2, zt), (Llug - rear, Win / 2, zt), "right", 1, on=["mensula_oreja_sup_C"], text=f"{f(Win)} (luz)", txt_shift=30)
        V.dim_dia((0, 0, zt), P["d_pp"] / 2, 60, on=["mensula_oreja_sup_C"], text=tol_txt(P["d_pp"], "H9"), ext=24)
        c.cut_mark("planta", "A", (-rear - 20, 0, zt), (P["L_ch"] - rear + 42, 0, zt), 90)
        with alias(ctx, "_C"):
            # globos a la izquierda, fuera de la marca de corte; anclajes fuera del eje (la línea del eje es la del corte)
            balloons_auto(c, V, lk, pred=lambda q: (22 < q[1] < Win / 2 - 3) or q[1] > Win / 2 + 3, gap=12, off=34, sides="l")
    c.vs("planta", sh, "top", lv=(1, 1, 2, 2), extra=(20, 20, 30, 20), draw=planta, mat=mm, hatch=False, title="PLANTA", auto=False, w=1.4)
    c.vs("cA", sh2, "front", cut=CUT_Y, lv=(1, 1, 2, 1), mat=mm, hs=0.4, title="CORTE A-A (plano del eje; base parcial)", w=1.2,
         center=(P["L_ch"] / 2 - rear, 0, tb), win=(-P["L_ch"] / 2 - 60, -tb - 4, P["L_ch"] / 2 + 60, H_ + 8),
         draw=lambda V, c: V.dimv((Llug - rear, 0, tb), (Llug - rear, 0, zt), "right", 0, on=["mensula_oreja_inf_C", "mensula_oreja_sup_C"], text=f"({f(H_)})"), auto=dict(on=lk, maxn=6))
    c.vs("cB", sh2, "right", cut=((0, 0, 0), (-1, 0, 0)), lv=(1, 1, 2, 1), mat=mm, hs=0.4, title="CORTE B-B (por el eje del ojal; base parcial)", w=1.0, auto=dict(on=lk, maxn=6),
         center=(0, 0, tb), win=(-Wout / 2 - 60, -tb - 4, Wout / 2 + 60, H_ + 8))
    if ids:
        add_prep(c, "det_j", ctx.weld_by_id(ids[0]), t1=tc, t2=tb, mins=1.0, maxs=1.0)
    c.tail(ks, ids, [f"Armar en plantilla sobre la base: mejillas {f(tc)} × {f(H_)} a {f(Win)} de luz; orejas entre mejillas; centro de la luz entre orejas (eje del cilindro) a {f(g.hax)} ±0,5 de la cara de apoyo.",
                     f"Mandrinar Ø{f(P['d_pp'])} H9 de ambas orejas en línea después de soldar (coaxialidad 0,10). Se fabrican {int(P['n_br'])} ménsulas.", "Filetes: ver tabla; secuencia alternada por lados; MT 100 %."])
    c.build()
    return c.h


@con
def sheet_mesa_conj1(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    ks = mesa_keys(ctx)
    a0 = D["pasadores"][0]
    c = Conj(ctx, 8, ks, "MESA SOLDADA: PLANTA A MEDIA ALTURA, PLANTA INFERIOR, ELEVACIÓN Y CORTE POR UN PASADOR", material="ASTM A572 Gr.50 (Fy ≥ %s MPa) — PROPUESTO; planchas Z35 y UT A578 B (ver despiece)" % f(P["Fy"]), trat="Alivio de tensiones; planear cara inferior", masa=masa_mesa(ctx, ks))
    zmid = g.z0 + g.tbo + g.hw / 2
    sh, mm = ctx.sh(*ks), mats(ctx, ks)

    def media(V, c):
        balloons_auto(c, V, [k for k in ks if k not in ("pernos_pasador", "arandela_pasador")], pred=lambda q: q[2] <= zmid + 0.5, gap=11, off=16)
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
         auto=dict(on=[k + "_R" for k in ks if k in ("mesa_anillo_inf", "mesa_anillo_sup", "mesa_plancha_sup", "mesa_plancha_inf", "mesa_cubo")], tol={}, maxn=9))
    c.tail(ks, [], compact=False, notes=["Despiece y tabla de soldaduras del subconjunto: CON-009 (no se repiten aquí); programa completo en GEN-007.", "Masa del rótulo: mesa soldada / con pasadores y pernos (para izar la mesa, la segunda).",f"Armado sobre la plancha inferior: cubo, almas (R {', '.join(f(x) for x in D['almas'])}), {int(P['N_rib'])} nervios por tramo, anillos y plancha superior; cerrar con la superior en último lugar.",
                     f"{g.N_pin} agujeros Ø{f(g.d_pin)} H7 en PCD Ø{f(2 * g.R_pin)}: mandrinar en línea con la mesa armada y aliviada (ver MES-002/004 y tabla de pasadores en CON-009).",
                     f"Cubo H7 Ø{f(g.d_bush)} y rebaje del collar Ø{f(g.Drb)}: mandrinar después de aliviar; cara inferior planeada (planitud 0,20)."])
    c.build()
    return c.h


@con
def sheet_mesa_conj2(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    ks = mesa_keys(ctx)
    ang = D["nervios"][0] + 0.5 * (D["nervios"][1] - D["nervios"][0])
    c = Conj(ctx, 9, ks, "MESA SOLDADA: CORTE POR ALMAS, DETALLES DE JUNTA, REBAJE DEL COLLAR Y TABLA DE PASADORES", material="ASTM A572 Gr.50 (Fy ≥ %s MPa) — PROPUESTO; planchas Z35 y UT A578 B (ver despiece)" % f(P["Fy"]), trat="Alivio de tensiones; planear cara inferior", masa=masa_mesa(ctx, ks))
    for k in ks:
        rot_key(ctx, k, k + "_W", -ang)
    ws = ctx.sh(*[k + "_W" for k in ks])
    mm = {k + "_W": ctx.mat[k] for k in ks}
    zt0 = g.z0 + g.tbo + g.hw

    def cw(V, c):
        with alias(ctx, "_W"):
            balloons_auto(c, V, [k + "_W" for k in ks if k not in ("pernos_pasador", "arandela_pasador", "pasadores")], pred=lambda q: q[1] >= -0.5, gap=11, off=14)
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
    jn = [w["id"] for w in ctx.welds if "MES" in w["piezas"] or "INT tope mesa" in w["piezas"]]
    for i, wid in enumerate([w["id"] for w in ctx.welds if "MES" in w["piezas"]][:3]):
        add_prep(c, f"dj{i}", ctx.weld_by_id(wid), t1=g.tpr)
    rows = []
    for i, a in enumerate(D["pasadores"]):
        x, y = polar(g.R_pin, a)
        rows.append([str(i + 1), fm(a, 3) + "°", f(x, 1), f(y, 1)])
    half = (len(rows) + 1) // 2
    rows2 = [rows[i] + (rows[i + half] if i + half < len(rows) else ["", "", "", ""]) for i in range(half)]
    c.table_block("POSICIÓN DE LOS PASADORES (PCD Ø%s, paso %s°, arranque %s°)" % (f(2 * g.R_pin), fm(360 / g.N_pin, 3), fm(D["pasadores"][0], 3)),
                  [("N°", 9, "C"), ("Ángulo", 22, "R"), ("x [mm]", 22, "R"), ("y [mm]", 22, "R"), ("N°", 9, "C"), ("Ángulo", 22, "R"), ("x [mm]", 22, "R"), ("y [mm]", 22, "R")], rows2)
    c.tail(ks, jn, ["Los nervios se cortan entre almas; las almas son continuas; 1 empalme por alma entre nervios.", "Masa del rótulo: mesa soldada / con pasadores y pernos.", f"Holguras del collar: radial {fm(g.c_boss_r, 0)} mm y axial {fm(g.c_boss_a, 0)} mm (del cálculo); el cubo gira sin tocar el collar.",
                    f"Tabla de pasadores: ángulos desde +x, sentido antihorario; PCD Ø{f(2 * g.R_pin)} y ángulos teóricamente exactos; agujeros en posición Ø0,3 respecto del eje de la mesa (MES-002).",
                    f"Mesa armada (datum A = cara inferior planeada): cara superior paralela a A dentro de 0,5; agujeros Ø{f(g.d_pin)} H7 de los anillos superior e inferior coaxiales Ø0,05 (eje común, mandrinado en línea).",
                    f"Secuencia de espesores (N-03): anillos de partida {fm(g.tpr + 3, 0)} con los empalmes soldados en la partida; MES-002 planeado a {fm(g.tpr, 0)} antes de soldarlo a la plancha superior (t = {fm(g.tt, 0)} / {fm(g.tpr, 0)}); "
                    f"MES-004 soldado en {fm(g.tpr + 3, 0)} a la plancha inferior de {fm(g.tbo + 3, 0)} (caras inferiores a ras); después del alivio se planea la cara inferior de la mesa 3 mm: plancha {fm(g.tbo, 0)} y anillo {fm(g.tpr, 0)}."])
    c.build()
    return c.h


@con
def sheet_accionamiento(ctx):
    if ctx.g.modo == 2:
        return sheet_accionamiento_pv(ctx)
    g, P, D, KG = ctx.g, ctx.P, ctx.D, ctx.g.KG
    ks = [k for k in ("bancada", "cilindro", "patin", "una", "pasador_vastago", "pasador_ojal", "leva_riel", "leva_pata", "leva_tapa", "leva_prolong", "leva_rodillo", "leva_perno", "leva_pernos") if ctx.m.get(k)]
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
            balloons_auto(c, V, lk, gap=12, off=34, sides="l")
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
        balloons_auto(c, V, [k for k in ks if k not in ("mesa_plancha_sup", "mesa_plancha_inf", "base_plancha", "tapa_ret")], pred=lambda q: q[1] >= -0.5, gap=12, off=18)
        # N-21: el globo de la tapa retenedora va arriba, con su propia línea inclinada (no comparte recta con el del pivote)
        if ctx.m.get("tapa_ret"):
            a_ = V.P(g.cap_D / 2 - 10, 0, g.L_piv + g.cap_t / 2)
            q_ = (a_[0] + 34, V.ext[3] + 16)
            c.s.balloon(a_, q_, ctx.m.get("tapa_ret").pos)
            ctx.balloons[c.h.plano].add(ctx.m.get("tapa_ret").pos)
            V.ext = (V.ext[0], V.ext[1], V.ext[2], max(V.ext[3], q_[1] + 7))
        V.line_axis = None
        c.s.line(V.P(0, 0, -6), V.P(0, 0, top + 14), "EJE")
        V.dimv((g.d_bush / 2, 0, g.z_bush0), (g.d_bush / 2, 0, g.z_bush0 + P["L_bush"]), "right", 0, on=["buje"], text=f"{f(P['L_bush'])} (buje)")
        V.dimv((-P["D_piv"] / 2 + g.ch_piv, 0, 0), (-P["D_piv"] / 2 + g.ch_piv, 0, g.L_piv), "left", 0, on=["pivote"], text=f"{fm(g.L_piv, 1)} (pivote)")
        V.dimh((-P["D_hub"] / 2, 0, g.z0 + g.tbo + 40), (P["D_hub"] / 2, 0, g.z0 + g.tbo + 40), "top", 0, on=["mesa_cubo"], text=f"Ø{f(P['D_hub'])} (cubo)")
        V.dimh((-g.D_boss / 2, 0, g.tb + g.h_boss - 2), (g.D_boss / 2, 0, g.tb + g.h_boss - 2), "bottom", 0, on=["collar"], text=f"Ø{f(g.D_boss)} (collar)")
        V.dimh((-P["D_piv"] / 2, 0, g.tb + 20), (P["D_piv"] / 2, 0, g.tb + 20), "bottom", 1, on=["pivote", "collar"], text=tol_txt(P["D_piv"], "p6") + " / H7") if False else None
    c.vs("cA", sh, "front", cut=CUT_Y, center=(0, 0, 0), win=(-190, -8, 190, top + 20), lv=(2, 2, 3, 2), extra=(20, 20, 40, 20), draw=cA, mat=mm, hs=0.5, title="CORTE POR EL EJE DEL PIVOTE (plano y = 0)", auto=False, w=3.0, mins=1.0)
    # A-08: detalle Y con su llamada en el corte (círculo y letra) y escala mayor que la del corte
    zc_ = g.z_bush0 + P["L_bush"] / 2
    rD = (g.d_bush - P["D_piv"]) / 2

    def detY(V, c):
        aL, aR = V.P(P["D_piv"] / 2, 0, zc_ + P["L_bush"] * 0.25), V.P(g.d_bush / 2, 0, zc_ - P["L_bush"] * 0.25)
        xl_, xr_ = V.Pt2((V.win[0], 0))[0], V.Pt2((V.win[2], 0))[0]
        V.note_pt((P["D_piv"] / 2, 0, zc_ + P["L_bush"] * 0.25), (min(xl_, V.ext[0]) - 6 - aL[0], 10), f"Ø{f(P['D_piv'])} F7/f7 (buje / zona f7 del pivote): juego {iso286.fit(P['D_piv'], 'F7', 'f7')['cmin']:+d}/{iso286.fit(P['D_piv'], 'F7', 'f7')['cmax']:+d} µm", on=["buje"],
                  lines=[f"Ø{f(P['D_piv'])} F7/f7 (buje / pivote)", f"juego {iso286.fit(P['D_piv'], 'F7', 'f7')['cmin']:+d}/{iso286.fit(P['D_piv'], 'F7', 'f7')['cmax']:+d} µm; F7 después del calado"])
        V.note_pt((g.d_bush / 2, 0, zc_ - P["L_bush"] * 0.25), (max(xr_, V.ext[2]) + 6 - aR[0], -10), f"Ø{f(g.d_bush)} H7/s6 (cubo / buje): aprieto", on=["buje"],
                  lines=[f"Ø{f(g.d_bush)} H7/s6 (cubo / buje)", f"aprieto {-iso286.fit(g.d_bush, 'H7', 's6')['cmax']}…{-iso286.fit(g.d_bush, 'H7', 's6')['cmin']} µm (prensado)"])
    c.detail("det_f", "cA", (P["D_piv"] / 2 + rD / 2, 0, zc_), 30.0, "Y", keys=[k for k in ("pivote", "buje", "mesa_cubo") if k in ctx.shapes], lv=(1, 1, 1, 2), hs=0.35, maxs=2.0, mins=2.0,
             title="DETALLE Y: AJUSTES DEL BUJE", mat=mats(ctx, ["pivote", "buje", "mesa_cubo"]), w=0.6, auto=False, draw=detY, extra=(50, 0, 50, 0))
    ajs = [a for a in hojas_base.ajustes(ctx) if a[0] in ("Pivote en plancha base y collar", "Pivote en buje", "Buje en cubo de la mesa")]
    rows = []
    for (desc, d, ho, sh_, app) in ajs:
        t = hojas_base.ajuste_txt(d, ho, sh_)
        rows.append([desc, f"Ø{fm(d, 0)} {ho}/{sh_}", t["h_lim"], t["s_lim"], t["juego"] + " µm", t["tipo"]])
    rows.append(["Collar en rebaje de la plancha inferior", f"Ø{f(g.D_boss)} / Ø{f(g.Drb)}", f"{fm(g.Drb, 1)}", f"{fm(g.D_boss, 1)}", f"{fm(g.c_boss_r, 0)} mm (radial)", "sin contacto (del cálculo)"])
    rows.append(["Collar – cubo (axial)", f"{fm(g.h_boss, 0)} vs {fm(g.h_rebaje, 1)}", "—", "—", f"{fm(g.c_boss_a, 0)} mm (axial)", "sin contacto (del cálculo)"])
    c.table_block("AJUSTES Y HOLGURAS DEL PIVOTE (ISO 286, límites calculados)", [("Ajuste", 40, "L"), ("Nominal", 24, "L"), ("Agujero [mm]", 24, "C"), ("Eje [mm]", 24, "C"), ("Juego / holgura", 26, "C"), ("Tipo", 30, "L")], rows)
    c.tail(ks2, [], [f"Pivote Ø{f(P['D_piv'])} con dos zonas (PIV-001): zona p6 (z = 0 a {fm(g.z_p6, 0)}) calada en plancha base y collar H7/p6 (aprieto); zona f7 (z = {fm(g.z_f7, 0)} a {fm(g.L_piv, 0)}) en el buje F7/f7 (juego); buje s6/H7 prensado en el cubo.",
                     f"Altura de asiento del cubo: collar de {f(g.h_boss)} sobre la base; holgura radial {fm(g.c_boss_r, 0)} mm y axial {fm(g.c_boss_a, 0)} mm (del cálculo): el cubo gira sin tocar el collar.",
                     f"Tapa retenedora con 4 × M10×{g.cap_L:.0f} ISO 10642 10.9 (PCD Ø{fm(g.cap_pcd, 0)}); tapa de inspección con 6 × M{fm(g.insp_d, 0)}×{g.insp_L} ISO 10642 10.9 (PCD Ø{fm(g.insp_pcd, 0)}); torques propuestos en GEN-008, a confirmar.",
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
        if m.get("int_tope_uhmw"):
            # barras del rebaje UHMW (ocultas bajo el disco de la mesa): en la junta entre sectores de UHMW, nunca sobre la bisectriz (H-01)
            nb_ = m.get("int_tope_uhmw").qty
            r0b, Lb_, bb_ = g.Ri + 50, m.info["uhmw_bar_L"], P["b_tope"]
            for k_ in range(nb_):
                a_ = m.info.get("uhmw_off", 0.0) + 360.0 * k_ / nb_
                ca, sa = math.cos(math.radians(a_)), math.sin(math.radians(a_))
                P2 = lambda u, w: V.P(u * ca - w * sa, u * sa + w * ca, ztop)
                s.pline([P2(r0b, -bb_ / 2), P2(r0b + Lb_, -bb_ / 2), P2(r0b + Lb_, bb_ / 2), P2(r0b, bb_ / 2)], "OCU", closed=True)
            a1_ = m.info.get("uhmw_off", 0.0)
            c.nota_barras = f"Barras del rebaje UHMW (trazo oculto en la planta, corte C-C): {nb_}, una en cada junta entre sectores de UHMW, a {fm(a1_, 2)}° + {fm(360.0 / nb_, 2)}°·k desde +x; r = {fm(r0b, 0)} a {fm(r0b + Lb_, 0)}; soldadas al disco de la base (INT-001)."
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
        nom = {"disc_base": "disco inox, base", "uhmw": "UHMW", "disc_mesa": "disco inox, mesa", "bronce": "bronce, base", "cara": "2.ª placa de bronce, mesa" if g.conf == 2 else "disco duro, mesa"}
        for i_, l in enumerate(g.stack):
            V.dimv((g.Ri + 2, 0, z), (g.Ri + 2, 0, z + l["t"]), "left", i_ % 2, on=ints, text=f"{fm(l['t'], 1)} ({nom.get(l['id'], l['id'])})")
            z += l["t"]
    c.vs("corte", ish, "front", cut=CUT_Y, center=(g.r_u, 0, g.tb + tt_ / 2), win=(-170, -tt_ - 40, 170, tt_ + 40), lv=(2, 1, 1, 1), extra=(10, 10, 10, 10), draw=corte,
         mat={k: ctx.mat[k[:-2]] for k in isk}, hs=0.25, title="CORTE RADIAL POR LA BISECTRIZ DEL SECTOR 1", auto=False, w=1.2)
    if m.get("int_tope_uhmw"):
        a_b = m.info.get("uhmw_off", 0.0)
        for k in ks + ["base_plancha"]:
            rot_key(ctx, k, k + "_C", -a_b)
        ksc = [k + "_C" for k in ks + ["base_plancha"]]
        rC = g.r_u
        intc = [k for k in ksc if k.startswith("int_")]

        def corteC(V, c):
            with alias(ctx, "_C"):
                balloons_auto(c, V, [k for k in intc if k.startswith("int_tope_uhmw")], gap=12, off=14)
            V.dimh((rC, -P["b_tope"] / 2, g.tb + g.I["tss"] + m.info["uhmw_bar_h"]), (rC, P["b_tope"] / 2, g.tb + g.I["tss"] + m.info["uhmw_bar_h"]), "top", 0, on=["int_tope_uhmw_C"], text=f"{fm(P['b_tope'], 0)} (barra)")
        c.vs("corteC", ctx.sh(*ksc), "right", cut=((rC, 0, 0), (-1, 0, 0)), center=(rC, 0, g.tb + tt_ / 2), win=(-70, -tt_ - 30, 70, tt_ + 30), lv=(1, 1, 2, 1), extra=(10, 10, 10, 10), draw=corteC,
             mat={k: ctx.mat[k[:-2]] for k in ksc}, hs=0.25, title=f"CORTE C-C (tangencial a r = {fm(rC, 0)}) POR UNA BARRA DEL REBAJE UHMW (junta entre sectores)", auto=False, w=1.0)
    rows = [[str(i + 1), fm((i + 0.5) * th, 3) + "°", fm(i * th, 3) + "°", fm((i + 1) * th, 3) + "°", f(polar(g.r_u, (i + 0.5) * th)[0], 1), f(polar(g.r_u, (i + 0.5) * th)[1], 1)] for i in range(g.n_sec)]
    half = (len(rows) + 1) // 2
    rows2 = [rows[i] + (rows[i + half] if i + half < len(rows) else [""] * 6) for i in range(half)]
    if g.removable:
        cols = [("Sector", 14, "C"), ("Bisectriz", 20, "R"), ("Inicio", 20, "R"), ("Fin", 20, "R"), ("x tope", 18, "R"), ("y tope", 18, "R")]
        c.table_block(f"COORDENADAS DE LOS SECTORES (tope en r_u = {fm(g.r_u, 1)} sobre la bisectriz)", cols + [(t + " ", w, a) for t, w, a in cols], rows2, wide=True)
    else:
        rows2 = [r[:4] + (rows[i + half][:4] if i + half < len(rows) else [""] * 4) for i, r in enumerate(rows[:half])]
        cols = [("Sector", 14, "C"), ("Bisectriz", 20, "R"), ("Inicio", 20, "R"), ("Fin", 20, "R")]
        c.table_block("COORDENADAS DE LOS SECTORES (sin topes: fijación modo 2)" if ctx.m.get("int_tornillo_af2") else "COORDENADAS DE LOS SECTORES (sin topes ni tornillos: fijación modo 2)", cols + [(t + " ", w, a) for t, w, a in cols], rows2, wide=True)
    ids = [w["id"] for w in ctx.welds if "INT" in w["piezas"]]
    notes = [f"{g.variante_nombre}.", f"Juntas en frío entre sectores {fm(g.junta('disc'), 2)} mm" + (f" (UHMW {fm(g.junta('uhmw'), 2)} mm)" if g.opt == 2 else "") + ("; muescas de tope en la bisectriz." if g.removable else ".")]
    if g.removable:
        notes += ["Los tornillos de posición solo posicionan (no transmiten carga): el par lo toman los topes soldados.", "Ver láminas de sector, tope, tornillos y notas de la interfaz (INT)."]
    else:
        TA_ = g.I.get("tornillos") if isinstance(g.I.get("tornillos"), dict) else None
        if TA_ and ctx.m.get("int_tornillo_af2"):
            notes += [f"Fijación modo 2 (decisión del mandante 08-11-2026): sectores pegados, sin topes (no existen en AF2). El par de la interfaz pasa del disco de la mesa a la mesa por {int(TA_['n'])} tornillos {TA_['designacion']} "
                      f"en R{fm(TA_['r'], 0)} ({ctx.code('int_tornillo_af2').replace(CODE + '-', '')}; avellanados en INT-002, roscas en MES-004).", "Ver láminas de sector de la interfaz (INT) y el conflicto declarado de los tornillos con los pasadores (GEN-009)."]
        else:
            notes += ["Fijación modo 2: sectores pegados, sin topes ni tornillos. La transmisión del par sin topes queda PENDIENTE de la decisión del cliente (adhesivo y su verificación: GEN-009).", "Ver láminas de sector de la interfaz (INT)."]
    if m.get("int_tope_uhmw"):
        nb_ = m.get("int_tope_uhmw").qty
        notes.append(f"Barras del rebaje UHMW ({ctx.code('int_tope_uhmw').replace(CODE + '-', '')}, trazo oculto en la planta y corte C-C): {nb_}, una en cada junta entre sectores de UHMW, a {fm(m.info.get('uhmw_off', 0.0), 2)}° + {fm(360.0 / nb_, 2)}°·k desde +x, "
                     f"r = {fm(g.Ri + 50, 0)} a {fm(g.Ri + 50 + m.info['uhmw_bar_L'], 0)}; soldadas al disco de la base (INT-001).")
    if g.opt in (1, 3):
        notes.append(f"Ranuras de engrase: {g.n_gr_rad} radiales a k·{fm(360 / g.n_gr_rad, 1)}° y {g.n_gr_circ} circunferenciales (R = {', '.join(fm(r, 0) for r in lay.r_circ)}), ancho {fm(g.w_gr, 0)}, prof. {fm(g.h_gr, 1)}; {g.n_greaser} graseras a R_o − 30.")
    c.tail(ks, ids, notes)
    c.build()
    return c.h


# ======================================================================================================
# Accionamiento pivotado (modo 2): subconjunto del cajón del ojal E (CON-007), accionamiento (CON-010), explosionada (CON-018)
# ======================================================================================================
CAJON_KEYS = ("cajon_pared", "cajon_ventana_a", "cajon_ventana_b", "cajon_tapa")
PV_ACC_KEYS = ("cilindro_pv", "pasador_E", "bloque_una", "pasador_Q", "placa_leva", "pernos_placa_leva")


def _crop(ctx, key, nk, x0, x1, y0, y1, z0=-1.0, z1=400.0):
    b = cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))
    ctx.shapes[nk] = ctx.shapes[key].intersect(b)
    ctx.mat[nk] = ctx.mat.get(key, "acero")
    return nk


def sheet_cajon_conj(ctx):
    """CON-007 (modo 2): cajón del ojal E soldado a la base, con la posición del cajón respecto de los bordes de la base con tolerancia ajustada (ISO 1101,
    datums en los bordes de la base): decisión del mandante (holgura «cajón dentro de la base» aceptada con B del núcleo)."""
    g, P = ctx.g, ctx.P
    S = g.FPV["soporte_E"]
    C = S["cilindro1"]
    E = C["centro"]
    B, tb = g.B, g.tb
    xs = [q[0] for q in C["esquinas"]]
    ys = [q[1] for q in C["esquinas"]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    zt = S["z_paredes"][1]
    ks = [k for k in CAJON_KEYS if ctx.m.get(k)] + ["pasador_E"]
    lk = []
    for k in ks:
        ctx.local(k, k + "_K", near=(E[0], E[1], 100), r=260)
        lk.append(k + "_K")
    _crop(ctx, "base_plancha", "base_K", x0 - 140, B / 2, -B / 2, y1 + 140, -1, tb + 1)
    _crop(ctx, "marco_largo", "ml_K", x0 - 140, B / 2, -B / 2, y1 + 140)
    _crop(ctx, "marco_corto", "mc_K", x0 - 140, B / 2, -B / 2, y1 + 140)
    allk = ["base_K", "ml_K", "mc_K"] + lk
    c = Conj(ctx, 7, ks, "CAJÓN DEL OJAL E: SUBCONJUNTO SOLDADO A LA BASE, POSICIÓN CON TOLERANCIA AJUSTADA Y SOLDADURAS", material=S["material"], trat="Alivio de tensiones (con la base)")
    c.iso_keys = lk
    s = c.s
    sh = {k: ctx.shapes[k] for k in allk}
    mm = {k: ctx.mat.get(k, "acero") for k in allk}
    ids = jids(ctx, "Paredes del cajón", "Tapas del cajón", "Esquinas del cajón")
    dEb = B / 2 - E[0]

    def planta(V, c):
        with alias(ctx, "_K"):
            balloons_auto(c, V, lk, gap=12, off=26, sides="l")
        # TED desde los bordes de la base (datums B = borde x+, C = borde y−) a las caras exteriores y al eje E
        V.dim((x1, y1 + 60, tb), (B / 2, y1 + 60, tb), 0, orient="h", on=["cajon_pared_K", "base_K"], text=f"{fm(B / 2 - x1, 1)}", ted=True)
        V.dim((E[0], y1 + 90, tb), (B / 2, y1 + 90, tb), 0, orient="h", on=["base_K"], text=f"{fm(dEb, 1)}", ted=True, virt_a=None) if False else None
        V.dimh((E[0], E[1], zt), (B / 2, E[1], tb), "top", 0, on=["cajon_tapa_K", "base_K"], virt_a=S["tapas"]["agujero_E"] / 2, text=f"{fm(dEb, 1)}", ted=True)
        V.dimv((x0, -B / 2, tb), (x0, y0, zt), "left", 0, on=["base_K", "cajon_pared_K"], text=f"{fm(y0 + B / 2, 1)}", ted=True)
        V.dimv((E[0], -B / 2, tb), (E[0], E[1], zt), "left", 1, on=["base_K", "cajon_tapa_K"], virt_b=S["tapas"]["agujero_E"] / 2, text=f"{fm(E[1] + B / 2, 1)}", ted=True)
        V.dimh((x0, y1, zt), (x1, y1, zt), "bottom", 0, on=lk, text=f"{f(S['lado'])} ±0,5")
        if len(ids) > 2:
            w_out(c, ids[2], V, (x0 + S["t_pared"], y0 + S["t_pared"], zt - 1), "left", dy=-20)
        c.cut_mark("planta", "A", (E[0], y0 - 50, zt), (E[0], y1 + 50, zt), 0)
    c.datum_in("planta", "surf", "B", at=[(B / 2, y1 + 100, tb), (B / 2, y0 - 60, tb)], d=(1, 0, 0))
    c.datum_in("planta", "surf", "C", at=[(x0 - 100, -B / 2, tb), (x1 - 20, -B / 2, tb)], d=(0, -1, 0))
    c.gd_in("planta", "surf", "pos", "1", ["A", "B", "C"], at=[(x1, (y0 + y1) / 2, zt), (x1, y0 + 40, zt)], d=(1, 0, 0))
    c.gd_in("planta", "surf", "pos", "1", ["A", "B", "C"], at=[((x0 + x1) / 2, y0, zt), (x0 + 40, y0, zt)], d=(0, -1, 0))
    c.gd_in("planta", "surf", "pos", "Ø1", ["A", "B", "C"], at=[(E[0] + S["tapas"]["agujero_E"] / 2, E[1], zt)], d=(1, 1, 0))
    c.vs("planta", sh, "top", lv=(2, 2, 2, 2), extra=(30, 20, 20, 20), draw=planta, mat=mm, hatch=False, title="PLANTA (esquina de la base; cotas teóricamente exactas desde los bordes B y C)", auto=False, w=2.0)

    def cA(V, c):
        if ids:
            w_out(c, ids[0], V, (E[0], y0, tb + 0.5), "left", dy=10)
        if len(ids) > 1:
            w_out(c, ids[1], V, (E[0], y0 + S["t_pared"], S["tapas"]["z_inf"][1] + 0.5), "right", dy=14)
        V.dimv((E[0], y1, 0), (E[0], y1, zt), "right", 0, on=["base_K", "cajon_ventana_b_K", "cajon_pared_K", "cajon_ventana_a_K"], text=f"{f(zt)}")
    c.datum_in("cA", "surf", "A", at=[(E[0], y0 - 80, tb), (E[0], y0 - 40, tb)], d=(0, 0, 1))
    c.vs("cA", sh, "right", cut=((E[0], 0, 0), (-1, 0, 0)), center=(E[0], E[1], 90), win=(-S["lado"] / 2 - 110, -95, S["lado"] / 2 + 110, 120), lv=(2, 2, 2, 2), mat=mm, hs=0.4,
         title="CORTE A-A (por el eje E; tapas, ventana y pasador)", w=1.4, auto=dict(on=lk, maxn=8, tol={}), nocut=("pasador_E_K",))
    if ids:
        add_prep(c, "det_j23", ctx.weld_by_id(ids[0]), t1=S["t_pared"], t2=tb)
    lado_m = B / 2 - P["rim_t"] - x1
    c.tail(ks, ids, [
        f"Decisión del mandante (08-11-2026): se acepta la holgura «cajón del ojal E dentro de la base» (FU {fm(g.fila('Soporte del ojal E dentro de la base')['fu'], 3) if g.fila('Soporte del ojal E dentro de la base') else '—'}) con B = {f(B)}: "
        f"la posición de las caras exteriores y del eje E respecto de los bordes de la base lleva tolerancia de posición ajustada (marcos ISO 1101, datums A cara superior de la base, B y C bordes); control dimensional en GEN-003.",
        f"Holgura nominal cara exterior–cara interior del marco {fm(lado_m, 1)} mm. A DECIDIR POR EL CALCULISTA (requiere núcleo, GEN-009): el filete exterior z{fm(S['soldadura']['filete'], 0)} de las paredes completas no cabe en esa holgura (filete J01 del marco); "
        "la cara inferior de la tapa inferior y los filetes interiores pared–base quedan en una cavidad cerrada; la tapa superior queda a ras del borde de las paredes.",
        "Secuencia propuesta: (1) paredes en molinete punteadas sobre la base en plantilla (posición con estación total); (2) filetes pared–base y de esquinas; (3) tapa inferior y sus filetes; (4) tapa superior; "
        f"(5) alivio de tensiones con la base; (6) mandrinar Ø{f(S['tapas']['agujero_E'])} H9 de ambas tapas en línea (coaxialidad Ø0,10, perpendicular a A).",
        "RETENIDA (requiere núcleo): el cuerpo del cilindro entra en el cajón con la geometría del núcleo (conflicto declarado, GEN-009); no fabricar hasta su corrección.",
        f"Cajón del cilindro 2: el mismo, girado 180° respecto del eje de la mesa (E en {fm(-E[0], 1)}; {fm(-E[1], 1)}); datums en los bordes opuestos de la base."])
    c.build()
    return c.h


def sheet_accionamiento_pv(ctx):
    """CON-010 (modo 2): accionamiento pivotado de un lado (cilindro 1, sentido antihorario dibujado; el horario es la imagen especular respecto de la diagonal)."""
    g, P, D = ctx.g, ctx.P, ctx.D
    F, PV = g.FPV, g.PV
    fr = ctx.m.info["pivotado"]["frames"]["1_antihorario"]
    E, Q, P_ = fr["E"], fr["Q"], fr["P"]
    ks = ["cajon_pared", "cajon_ventana_a", "cajon_ventana_b", "cajon_tapa", "pasador_E", "cilindro_pv", "bloque_una", "pasador_Q", "placa_leva", "pernos_placa_leva"]
    ks = [k for k in ks if ctx.m.get(k)]
    cx, cy = (E[0] + P_[0]) / 2, (E[1] + P_[1]) / 2
    lk = []
    for k in ks:
        ctx.local(k, k + "_V", near=(E[0] * 0.75, E[1] * 0.75, 100), r=1050)
        if ctx.shapes[k + "_V"].Solids():
            lk.append(k + "_V")
    a_p = math.degrees(math.atan2(P_[1], P_[0]))
    ctx.local("pasadores", "pasadores_V", near=(P_[0], P_[1], g.z0 + g.hd / 2), r=200)
    _crop(ctx, "base_plancha", "base_V", 200, g.B / 2, -g.B / 2, 200, -1, g.tb + 1)
    allk = ["base_V", "pasadores_V"] + lk
    c = Conj(ctx, 10, ks, "ACCIONAMIENTO PIVOTADO TIPO KIET (LADO DEL CILINDRO 1): CAJÓN, CILINDRO, BLOQUE-UÑA, PASADORES Y PLACAS-LEVA", material="Ver despiece", trat="Ver despiece")
    c.iso_keys = lk
    sh = {k: ctx.shapes[k] for k in allk}
    mm = {k: ctx.mat.get(k[:-2], "acero") for k in allk}
    s = c.s

    def planta(V, c):
        with alias(ctx, "_V"):
            balloons_auto(c, V, lk, gap=12, off=30, sides="lr")
        s.line(V.P((0, 0, g.zc)), V.P((E[0], E[1], g.zc)), "EJE")
        pe, pq, pp = V.P((E[0], E[1], g.zc)), V.P((Q[0], Q[1], g.zc)), V.P((P_[0], P_[1], g.zc))
        s.line(pe, pp, "EJE")
        for q_, t_ in ((pe, "E"), (pq, "Q"), (pp, "P (pasador tomado)")):
            s.text(t_, (q_[0] + 4, q_[1] + 3), T_N, "BOTTOM_LEFT")
        V.dim((E[0], E[1], g.zc), (Q[0], Q[1], g.zc), 14, orient="a", on=["cilindro_pv_V"], virt_a=F["pasador_E"]["d"] / 2, virt_b=F["pasador_Q"]["d"] / 2, text=f"{fm(fr['L'], 1)} (L en la posición dibujada)")
        V.dim((Q[0], Q[1], g.zc), (P_[0], P_[1], g.zc), -14, orient="a", on=["bloque_una_V", "pasadores_V"], virt_a=F["bloque_una"]["agujero_Q"] / 2, virt_b=g.d_pin / 2, text=f"{fm(PV['L_qp'], 0)} (L_qp)")
    c.vs("planta", sh, "top", lv=(1, 1, 1, 1), extra=(30, 20, 30, 20), draw=planta, mat=mm, hatch=False, title=f"PLANTA (sentido antihorario dibujado; pasador tomado a {fm(a_p, 3)}° de +x)", auto=False, w=2.2)
    # corte vertical por el eje del cilindro E–Q: copias giradas con el eje E–Q sobre +x (origen en E)
    wk = []
    for k in allk:
        nk = k[:-2] + "_W"
        ctx.shapes[nk] = ctx.shapes[k].translate(cq.Vector(-E[0], -E[1], 0)).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -fr["a_cil"])
        ctx.mat[nk] = ctx.mat.get(k, "acero")
        wk.append(nk)
    shw = {k: ctx.shapes[k] for k in wk}

    def cAd(V, c):
        F_ = g.FPV
        V.dimv((fr["L"] + 60, 0, g.tb), (fr["L"] + 60, 0, F_["placas_leva"]["z"][1]), "right", 0, on=["placa_leva_W"], text=f"{fm(F_['placas_leva']['t'], 0)} (placa-leva)") if False else None
        _niveles_pv(ctx, V, c)
    c.vs("cA", shw, "front", cut=((0, 0, 0), (0, 1, 0)), center=(fr["L"] / 2, 0, 100), win=(-fr["L"] / 2 - 180, -110, fr["L"] / 2 + 160, 130), lv=(1, 2, 2, 1), mat={k: ctx.mat.get(k, "acero") for k in wk}, hs=0.4,
         title="CORTE A-A POR EL EJE E–Q (cajón, cilindro, bloque-uña, pasador Q y placa-leva)", w=1.6, auto=dict(on=[k for k in wk if not k.startswith(("base", "cilindro"))], maxn=6, tol={}),
         nocut=("pasador_E_W", "pasador_Q_W", "pernos_placa_leva_W", "pasadores_W", "cilindro_pv_W"), draw=cAd)
    rows = [["E (eje del ojal trasero)", fm(E[0], 1), fm(E[1], 1), f"R_E = {f(PV['R_E'])}; φ_E = {fm(PV['phi_E'], 0)}°"],
            ["Cajón del cilindro 2", fm(-E[0], 1), fm(-E[1], 1), "giro de 180° del cilindro 1"]]
    for k_, ins in F["placas_leva"]["instancias"].items():
        p1, p6 = ins["pernos"][0], ins["pernos"][-1]
        rows.append([f"Placa-leva {k_.replace('_', ' ')}: agujeros P1 / P{len(ins['pernos'])}", f"{fm(p1[0], 1)} / {fm(p6[0], 1)}", f"{fm(p1[1], 1)} / {fm(p6[1], 1)}", "las del sentido horario, volteadas"])
    c.table_block("POSICIONES EN PLANTA (núcleo; origen en el eje de la mesa)", [("Elemento", 64, "L"), ("x [mm]", 26, "R"), ("y [mm]", 26, "R"), ("Observación", 50, "L")], rows)
    c.tail(ks, [], [
        f"Cinemática (núcleo): Q = P + L_qp·(E − P)/|E − P|; toma con el cilindro en el largo retraído + recorrido libre; empuje entre θ = {fm(PV['theta_ini_deg'], 2)}° y {fm(PV['theta_fin_deg'], 2)}° (brazo efectivo mínimo {fm(PV['brazo_ef_min'], 1)} mm).",
        "Inversión del giro: el cilindro pivota en el mismo ojal E hacia el otro lado de la diagonal; el bloque-uña se monta volteado y el pasador Q trabaja en la placa-leva del otro sentido (las 4 placas quedan fijas en la base).",
        f"El extremo inferior del pasador Q corre contra el canto templado de la placa-leva (holgura {fm(PV['placa_leva']['holgura'], 0)} mm en el empuje); el bloque-uña pasa sobre la placa ({fm(F['bloque_una']['z'][0] - F['placas_leva']['z'][1], 0)} mm) y sobre las cabezas de los pernos.",
        "Placas-leva RETENIDAS: perfil curvo continuo en rediseño en el núcleo (ACC-017). Las del sentido horario chocan con las orejas de izaje (conflicto declarado, GEN-009).",
        "Circuito hidráulico, bomba y válvulas: fuera del alcance de estos planos (GEN-008)."])
    c.build()
    return c.h


def _niveles_pv(ctx, V, c):
    g = ctx.g
    a = V.P((0, 0, g.zc))
    c.s.line((V.ext[0], a[1]), (V.ext[2], a[1]), "EJE")
    c.s.text(f"eje de los cilindros z = {f(g.zc)}", (V.ext[0] - 2, a[1] + 1.5), T_N, "BOTTOM_RIGHT")


def sheet_explosion_acc_pv(ctx):
    """CON-018 (modo 2): pivote, buje y tapa; accionamiento pivotado de un lado explotado en z."""
    g, P = ctx.g, ctx.P
    G = grupos(ctx)
    fr = ctx.m.info["pivotado"]["frames"]["1_antihorario"]
    E, Q = fr["E"], fr["Q"]
    ks = [k for k in ["collar"] + G["piv"] + list(CAJON_KEYS) + list(PV_ACC_KEYS) if ctx.m.get(k) and k in ctx.shapes]
    c = Conj(ctx, 18, ks, "ISOMÉTRICAS EXPLOSIONADAS: PIVOTE CON BUJE Y TAPA RETENEDORA; ACCIONAMIENTO PIVOTADO (UN LADO)")
    c.fmt_try = ["A2", "A1"]
    pk = []
    for k, dz in (("collar", 0), ("pivote", 300), ("buje", 600), ("tapa_ret", 820)):
        if k in ctx.shapes:
            ctx.local(k, k + "_P", near=(0, 0, 0), r=260, shift=(0, 0, dz))
            if ctx.shapes[k + "_P"].Solids():
                pk.append(k + "_P")

    def cbp(V, c):
        bb = _bb(ctx, pk)
        _arrow(c.s, V.P((0, 0, bb.zmax + 60)), V.P((0, 0, g.tb + 3)))
        with alias(ctx, "_P"):
            balloons_auto(c, V, pk, gap=12.0, off=22.0, hug=True)
    c.vs("piv", {k: ctx.shapes[k] for k in pk}, "iso", iso=True, lv=(1, 1, 1, 1), extra=(30, 20, 30, 20), mat=mats(ctx, pk), hatch=False, draw=cbp, title="PIVOTE, BUJE Y TAPA RETENEDORA (sobre el collar de la base)", auto=False, w=1.0)
    plan = [(k, 0) for k in CAJON_KEYS] + [("placa_leva", 0), ("pernos_placa_leva", 150), ("pasador_E", 700), ("cilindro_pv", 420), ("bloque_una", 260), ("pasador_Q", 560)]
    ak = []
    for k, dz in plan:
        if k in ctx.shapes:
            ctx.local(k, k + "_E", near=(E[0] * 0.8, E[1] * 0.8, 100), r=750, shift=(0, 0, dz))
            if ctx.shapes[k + "_E"].Solids():
                ak.append(k + "_E")

    def cba(V, c):
        for k, dz in plan:
            if k + "_E" in ctx.shapes and dz > 0:
                bb = ctx.shapes[k + "_E"].BoundingBox()
                cx_, cy_ = (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2
                _arrow(c.s, V.P((cx_, cy_, bb.zmin)), V.P((cx_, cy_, bb.zmin - dz + 15)))
        with alias(ctx, "_E"):
            balloons_auto(c, V, ak, gap=12.0, off=24.0, hug=True)
    c.vs("acc", {k: ctx.shapes[k] for k in ak}, "iso", iso=True, lv=(1, 1, 1, 1), extra=(30, 20, 30, 20), mat=mats(ctx, ak), hatch=False, draw=cba, title="ACCIONAMIENTO PIVOTADO DEL CILINDRO 1 (cajón soldado a la base)", auto=False, w=2.0)
    c.compact_table(ks)
    c.note_block("NOTAS", ["El cajón del ojal E va soldado a la base (subconjunto CON-007); las placas-leva se empernan a la base (roscas en BAS-001).",
                           "Instrucciones, ajustes y pares: pasos 1, 3 y 7 del instructivo (CON-005, CON-014, CON-019).", "Cilindro 2: el mismo conjunto girado 180°; la explosión en z es ilustrativa."])
    c.iso_fill = False
    c.build()
    return c.h
