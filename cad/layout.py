"""Compositor de lámina: reparte vistas, cortes y detalles en la zona libre de la hoja eligiendo, para cada vista, la escala normalizada
más grande que quepa (1:1, 1:2, 1:2,5, 1:5, 1:10, 1:20, 1:25, 1:50, 1:100; ampliaciones 2:1 y 5:1 en detalles). Notas, tablas y ficha se mueven a la
banda lateral (junto al cajetín) y a una franja inferior de altura medida, de modo que no queden huecos. Si sobra un rectángulo libre se
rellena con una isométrica de la pieza (escala libre, rotulada «sin escala») o con un detalle útil.

Uso (desde una función de lámina):
    p = Pieza(ctx, keys, titulo, fmt="A1")
    p.vs("planta", ["base_plancha"], "top", lv=(2, 2, 1, 1), draw=lambda V, p: ...)
    p.vs("corte", [...], "front", cut=CUT_Y, win=(...), ...)
    p.notes([...]); p.tables(ids)
    p.build()
"""
import math, sys, pathlib, itertools
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vistas
from vistas import View, COTAS, STD_SCALES, scale_txt, snap_scale
import draw as dr
from draw import Sheet, tw, wrapw, T_N, T_S, T_T
import autodim

MAIN_BOOST = 1.0
GAP = 4.0       # separación entre celdas [mm de papel]
DIMSTEP = 8.5   # paso entre líneas de cota apiladas
TITLE_H = 17.0  # altura reservada para el título de la vista y su escala


class VS:
    """Especificación de una vista (la lámina la dibuja el compositor cuando conoce su zona)."""

    def __init__(self, name, keys, view, cut=None, win=None, center=(0, 0, 0), lv=(1, 2, 2, 1), extra=(0, 0, 0, 0), mat=None, hatch=True, title=None, w=1.0, maxs=None, mins=None,
                 draw=None, auto=None, iso=False, hidden=False, breaks=None, hs=0.5, label=None, only=None, tag=None, min_cell=(40, 30), detail=None, at=None, nat=None, custom=None, layer="VIS"):
        self.name, self.keys, self.view, self.cut, self.win, self.center = name, keys, view, cut, win, center
        self.lv, self.extra, self.mat, self.hatch, self.title, self.w = lv, extra, mat, hatch, title, w
        self.maxs, self.mins, self.draw, self.auto, self.iso = maxs, mins, draw, auto, iso
        self.hidden, self.breaks, self.hs, self.label, self.only = hidden, breaks, hs, label or name, only
        self.detail = detail    # (nombre_vista_padre, centro3d, radio_modelo, letra)
        self.nat, self.custom = nat, custom
        self.layer = layer   # vista dibujada por una función (esquema de junta): nat = tamaño natural en mm del modelo
        self.V = None

    # extensión natural de la vista en el modelo
    def natural(self, shapes):
        if self.nat is not None:
            return self.nat
        if self.win is not None:
            u0, v0, u1, v1 = self.win
            return (u1 - u0, v1 - v0)
        keys = self.only or list(shapes)
        eu0 = ev0 = 1e18; eu1 = ev1 = -1e18
        for k in keys:
            b = shapes[k].BoundingBox()
            for x_ in (b.xmin, b.xmax):
                for y_ in (b.ymin, b.ymax):
                    for z_ in (b.zmin, b.zmax):
                        u, v = vistas.proj_pt((x_, y_, z_), self.view)
                        eu0, eu1, ev0, ev1 = min(eu0, u), max(eu1, u), min(ev0, v), max(ev1, v)
        a = eu1 - eu0 - sum(ub - ua for ua, ub in (self.breaks or []))
        return (max(a, 1e-3), max(ev1 - ev0, 1e-3))

    def margins(self):
        """(izq, abajo, der, arriba) en papel: líneas de cota apiladas + título + extra."""
        l, b, r, t = self.lv
        ex = self.extra
        gaps = 12.0 * len(self.breaks or [])
        return (8 + DIMSTEP * l + ex[0] + gaps, 8 + DIMSTEP * b + ex[1] + (TITLE_H if self.title else 4), 8 + DIMSTEP * r + ex[2], 8 + DIMSTEP * t + ex[3])


class Block:
    def __init__(self, kind, draw, wide=False, name=""):
        self.kind, self.draw, self.wide, self.name = kind, draw, wide, name
        self.h = 0.0


# ----------------------------------------------------------------------------------------------
# planificador de escalas y zonas
# ----------------------------------------------------------------------------------------------
def _max_scale_fit(a, b, mw, mh, W, H, cap=None):
    s = min((W - mw) / a, (H - mh) / b) if W > mw and H > mh else 0
    if cap:
        s = min(s, cap)
    ok = [x for x in STD_SCALES if x <= s * 1.0001]
    return ok[-1] if ok else STD_SCALES[0]


def _lower(s):
    lo = [x for x in STD_SCALES if x < s * 0.9999]
    return lo[-1] if lo else None


def _solve(groups, mode, zone, nat, mar, caps, wts, iso_flags, mins):
    """groups: lista de listas de índices (filas o columnas). Devuelve (score, escalas, geometría) o None."""
    W = zone[2] - zone[0]
    H = zone[3] - zone[1]
    n = sum(len(g) for g in groups)
    sc = {}
    for g in groups:
        for i in g:
            a, b = nat[i]
            mw, mh = mar[i][0] + mar[i][2], mar[i][1] + mar[i][3]
            sc[i] = _max_scale_fit(a, b, mw, mh, W, H, caps[i])
            if iso_flags[i]:
                # isométrica: se dibuja a escala libre, el reparto usa la escala continua (no la normalizada inmediata inferior)
                sc[i] = max(sc[i], min((W - mw) / a, (H - mh) / b, caps[i] or 1e9))

    def need(i):
        a, b = nat[i]
        return (a * sc[i] + mar[i][0] + mar[i][2], b * sc[i] + mar[i][1] + mar[i][3])

    def metrics():
        # rows: width_j = sum w; height = sum max h ; cols: transposed
        lines = []
        for g in groups:
            if mode == "rows":
                lines.append((sum(need(i)[0] for i in g) + GAP * (len(g) - 1), max(need(i)[1] for i in g)))
            else:
                lines.append((sum(need(i)[1] for i in g) + GAP * (len(g) - 1), max(need(i)[0] for i in g)))
        return lines
    for _ in range(200):
        lines = metrics()
        along = W if mode == "rows" else H
        across = H if mode == "rows" else W
        tot_across = sum(l[1] for l in lines) + GAP * (len(lines) - 1)
        bad = None
        for gi, (la, lc) in enumerate(lines):
            if la > along + 0.01:
                bad = ("along", gi)
                break
        if bad is None and tot_across > across + 0.01:
            # reduce el elemento que más ocupa del grupo más alto/ancho
            gi = max(range(len(lines)), key=lambda k: lines[k][1])
            bad = ("across", gi)
        if bad is None:
            break
        gi = bad[1]
        g = groups[gi]
        cands = []
        floor_ok = [i for i in g if _lower(sc[i]) is not None and (mins[i] is None or _lower(sc[i]) >= mins[i] - 1e-9)]
        for i in (floor_ok or g):
            lo = _lower(sc[i])
            if lo is None:
                continue
            a, b = nat[i]
            nd = need(i)
            # ganancia de la dimensión que viola y pérdida relativa de área
            if bad[0] == "along":
                gain = (a * (sc[i] - lo)) if mode == "rows" else (b * (sc[i] - lo))
            else:
                gain = (b * (sc[i] - lo)) if mode == "rows" else (a * (sc[i] - lo))
                if bad[0] == "across":
                    # sólo ayuda si es el que fija la altura del grupo
                    dim = nd[1] if mode == "rows" else nd[0]
                    if dim < lines[gi][1] - 0.01:
                        continue
            loss = wts[i] * math.log(sc[i] / lo)
            cands.append((loss / max(gain, 1e-6), i))
        if not cands:
            return None
        cands.sort()
        i = cands[0][1]
        sc[i] = _lower(sc[i])
    else:
        return None
    lines = metrics()
    along = W if mode == "rows" else H
    across = H if mode == "rows" else W
    tot_across = sum(l[1] for l in lines) + GAP * (len(lines) - 1)
    if tot_across > across + 0.01 or any(l[0] > along + 0.01 for l in lines):
        return None
    zarea = W * H
    score = sum(wts[i] * (math.log(sc[i] / STD_SCALES[0]) + 3.0 * nat[i][0] * nat[i][1] * sc[i] ** 2 / zarea) for i in sc)
    return score, sc, lines


def _compositions(n):
    for mask in range(2 ** (n - 1)):
        cuts = [i + 1 for i in range(n - 1) if mask >> i & 1]
        edges = [0] + cuts + [n]
        yield [list(range(edges[k], edges[k + 1])) for k in range(len(edges) - 1)]


def plan_cells(specs, shapes, zone):
    """Devuelve {índice: (x0, y0, x1, y1)} (celdas) para las vistas, y el esquema elegido. Máximo de área de vistas en papel."""
    n = len(specs)
    nat = [sp.natural(sp_shapes(sp, shapes)) for sp in specs]
    mar = [sp.margins() for sp in specs]
    caps = [sp.maxs for sp in specs]
    wts = [sp.w for sp in specs]
    iso = [sp.iso for sp in specs]
    import random
    rnd = random.Random(7)
    mins_ = [sp.mins for sp in specs]
    idx = list(range(n))

    def groups_of(perm, mask):
        cuts = [i + 1 for i in range(n - 1) if mask >> i & 1]
        edges = [0] + cuts + [n]
        return [[perm[i] for i in range(edges[k], edges[k + 1])] for k in range(len(edges) - 1)]

    cache = {}

    def evaluate(perm, mask, mode):
        key = (perm, mask, mode)
        if key in cache:
            return cache[key]
        groups = groups_of(perm, mask)
        res = None
        if not (max(len(g) for g in groups) > 4 or len(groups) > 4 or (mode == "cols" and len(groups) == 1 and n > 1)):
            r = _solve(groups, mode, zone, nat, mar, caps, wts, iso, mins_)
            if r is not None:
                score, sc, lines = r
                for i, sp in enumerate(specs):
                    if sp.mins and sc[i] < sp.mins - 1e-9:
                        score -= 4.0 * wts[i] * math.log(sp.mins / sc[i])
                res = (score, mode, groups, sc, lines)
        cache[key] = res
        return res
    best = None
    if n <= 4:
        for perm in itertools.permutations(idx):
            for mask in range(2 ** (n - 1)):
                for mode in ("rows", "cols"):
                    r = evaluate(perm, mask, mode)
                    if r and (best is None or r[0] > best[0]):
                        best = r
    else:
        starts = [tuple(idx)]
        for keyf in (lambda i: -wts[i], lambda i: -nat[i][0] * nat[i][1] * wts[i], lambda i: -nat[i][1], lambda i: -nat[i][0], lambda i: nat[i][0] * nat[i][1]):
            starts.append(tuple(sorted(idx, key=keyf)))
        for _ in range(6):
            q = idx[:]
            rnd.shuffle(q)
            starts.append(tuple(q))
        cands = []
        for perm in starts:
            for mask in range(2 ** (n - 1)):
                cnt = bin(mask).count("1") + 1
                if cnt > 4:
                    continue
                for mode in ("rows", "cols"):
                    r = evaluate(perm, mask, mode)
                    if r:
                        cands.append((r[0], perm, mask, mode))
        cands.sort(key=lambda t: -t[0])
        for score0, perm, mask, mode in cands[:6]:
            cur = (score0, perm, mask, mode)
            for _ in range(260):
                p2, m2, md2 = list(cur[1]), cur[2], cur[3]
                mv = rnd.random()
                if mv < 0.6:
                    i, j = rnd.sample(range(n), 2)
                    p2[i], p2[j] = p2[j], p2[i]
                elif mv < 0.9:
                    m2 ^= 1 << rnd.randrange(n - 1)
                else:
                    md2 = "cols" if md2 == "rows" else "rows"
                r = evaluate(tuple(p2), m2, md2)
                if r and r[0] > cur[0]:
                    cur = (r[0], tuple(p2), m2, md2)
            r = evaluate(cur[1], cur[2], cur[3])
            if r and (best is None or r[0] > best[0]):
                best = r
        for score0, perm, mask, mode in cands[:1]:
            r = evaluate(perm, mask, mode)
            if r and (best is None or r[0] > best[0]):
                best = r
    if best is None:
        raise RuntimeError("ninguna disposición cabe en la zona de vistas: " + str([sp.name for sp in specs]))
    score, mode, groups, sc, lines = best
    W = zone[2] - zone[0]
    H = zone[3] - zone[1]
    cells = {}
    along_tot = W if mode == "rows" else H
    across_tot = H if mode == "rows" else W
    extra_across = across_tot - (sum(l[1] for l in lines) + GAP * (len(lines) - 1))
    tot_need = sum(l[1] for l in lines)
    pos_across = 0.0
    for gi, g in enumerate(groups):
        la, lc = lines[gi]
        hh = lc + extra_across * lc / tot_need
        extra_along = along_tot - la
        tot_i = 0.0
        needs = []
        for i in g:
            a, b = nat[i]
            nd = (a * sc[i] + mar[i][0] + mar[i][2], b * sc[i] + mar[i][1] + mar[i][3])
            needs.append(nd[0] if mode == "rows" else nd[1])
        tot_i = sum(needs)
        pos_along = 0.0
        for i, nd in zip(g, needs):
            ww = nd + extra_along * nd / tot_i
            if mode == "rows":
                x0 = zone[0] + pos_along
                y1 = zone[3] - pos_across
                cells[i] = (x0, y1 - hh, x0 + ww, y1)
            else:
                y1 = zone[3] - pos_along
                x0 = zone[0] + pos_across
                cells[i] = (x0, y1 - ww, x0 + hh, y1)
            pos_along += ww + GAP
        pos_across += hh + GAP
    return cells, sc, (mode, groups)


def sp_shapes(sp, shapes):
    return sp.keys if isinstance(sp.keys, dict) else {k: shapes[k] for k in sp.keys if k in shapes}


# ----------------------------------------------------------------------------------------------
class Plano:
    """Base de las láminas con vistas: administra especificaciones de vista, bloques de texto/tabla y las compone."""

    def init_plano(self, ctx, hoja):
        self.ctx = ctx
        self.h = hoja
        self.s = hoja.begin()
        self.R = hoja.R
        self.specs = []
        self.blocks = []
        self.named = {}
        self.scales = []
        self.vlist = []
        self.dims_n0 = len(COTAS.rows)
        self.iso_keys = None
        self.iso_fill = True
        self.post = []      # callbacks tras construir (marcas de corte, globos)
        self.indic = []     # indicaciones en las vistas (B-20): marcos ISO 1101, datums ISO 5459, rugosidad ISO 1302 con referencia
        self.gd_items = []

    # ---------------- indicaciones en las vistas (gdt_vistas) ----------------
    def gd_in(self, view, mode, sym, tol, datum=None, at=None, d=None, prefix=None):
        self.indic.append(("fcf", view, mode, dict(sym=sym, tol=tol, datum=datum, at=at, d=d, prefix=prefix)))

    def datum_in(self, view, mode, letter, at=None, d=None, prefix=None):
        self.indic.append(("datum", view, mode, dict(letter=letter, at=at, d=d, prefix=prefix)))

    def ra_in(self, view, ra, at=None, d=None, prefix=None):
        self.indic.append(("ra", view, "dim" if prefix else "surf", dict(ra=ra, at=at, d=d, prefix=prefix)))

    def _draw_indic(self):
        import gdt_vistas as GV
        h, s = self.h, self.s
        h.indic_ok, h.indic_fallo = [], []
        if not self.indic:
            return
        Lb = GV.Libre(s, getattr(h, "zone", None) or h.R["main"])
        orden = {"datum": 0, "fcf": 2, "ra": 3}
        for kind, view, mode, a in sorted(self.indic, key=lambda t: 1 if (t[0] == "ra" and t[2] == "dim") else orden[t[0]]):
            V = self.named.get(view)
            if V is None:
                h.indic_fallo.append((kind, view, "vista inexistente"))
                continue
            at_ = a.get("at")
            pt = None if at_ is None else ([V.P(q) for q in at_] if isinstance(at_, list) else V.P(at_))
            if isinstance(at_, list) and not isinstance(a.get("d"), list):
                a = dict(a, d=[a["d"]] * len(at_))
            # dirección dada en 3D (modelo): se proyecta en la vista
            def _d2(q3, d3):
                if d3 is None or len(d3) != 3:
                    return d3
                p0, p1 = V.P(q3), V.P((q3[0] + d3[0], q3[1] + d3[1], q3[2] + d3[2]))
                return (p1[0] - p0[0], p1[1] - p0[1])
            if isinstance(at_, list):
                a = dict(a, d=[_d2(q, dd) for q, dd in zip(at_, a["d"])])
            elif at_ is not None:
                a = dict(a, d=_d2(at_, a.get("d")))
            if kind == "fcf":
                ok = GV.fcf(s, Lb, mode, a["sym"], a["tol"], a["datum"], a=pt, d=a["d"], prefix=a["prefix"])
                tag = ("fcf", a["sym"], a["tol"], a["datum"] if not isinstance(a["datum"], list) else tuple(a["datum"]))
            elif kind == "datum":
                ok = GV.datum(s, Lb, mode, a["letter"], a=pt, d=a["d"], prefix=a["prefix"])
                tag = ("datum", a["letter"])
            elif mode == "dim":
                ok = GV.rugosidad_cota(s, Lb, a["ra"], a["prefix"])
                tag = ("ra", a["ra"])
            else:
                ok = GV.rugosidad(s, Lb, a["ra"], pt, a["d"])
                tag = ("ra", a["ra"])
            (h.indic_ok if ok else h.indic_fallo).append(tag if ok else tag + (view,))

    # ---------------- declaración ----------------
    def vs(self, name, keys, view, **kw):
        if isinstance(keys, str):
            keys = [keys]
        if not self.specs and "w" in kw:
            kw["w"] = kw["w"] * MAIN_BOOST      # la primera vista declarada es la principal: mayor peso en el reparto de escalas
        sp = VS(name, keys, view, **kw)
        self.specs.append(sp)
        return sp

    def detail(self, name, parent, center3, r, letter, keys=None, lv=(1, 1, 1, 1), **kw):
        """Detalle ampliado: ventana cuadrada de radio r (mm del modelo) alrededor de center3 en la misma proyección (y corte) de la vista padre."""
        par = next(sp for sp in self.specs if sp.name == parent)
        u, v = vistas.proj_pt(center3, par.view)
        cu, cv = vistas.proj_pt(par.center, par.view)
        sp = VS(name, keys or par.keys, par.view, cut=par.cut, center=center3, win=(-r, -r, r, r), lv=lv, mat=kw.pop("mat", par.mat), title=kw.pop("title", f"DETALLE {letter}"), hatch=kw.pop("hatch", True),
                maxs=kw.pop("maxs", 5.0), **kw)
        sp.detail = (parent, center3, r, letter)
        self.specs.append(sp)
        return sp

    def block(self, kind, draw, wide=False, name=""):
        b = Block(kind, draw, wide, name)
        self.blocks.append(b)
        return b

    def note_block(self, title, lines, numbered=False):
        """Las notas se parten en bloques de 1–2 líneas (átomos) para llenar la banda lateral sin huecos."""
        lines = list(lines)
        if not hasattr(self.h, "notas_reg"):
            self.h.notas_reg = []
        self.h.notas_reg.extend(lines)
        i0 = 0
        first = True
        while i0 < len(lines):
            chunk = lines[i0:i0 + 2]
            ttl = title if first else title + " (cont.)"
            base = i0
            blk_ref = []
            def d(s, x, y, w, ttl=ttl, chunk=chunk, base=base, first=first, blk_ref=blk_ref):
                show = first or (blk_ref and getattr(blk_ref[0], "cont_title", False))
                if numbered:
                    s_lines = chunk
                    yy = y
                    if show:
                        s.text(ttl, (x, yy), T_N + 0.5, "TOP_LEFT", bold=True)
                        yy -= (T_N + 0.5) * 1.6
                    for j, ln in enumerate(s_lines):
                        wl = wrapw(f"{base + j + 1}. {ln}", w - 2, T_N)
                        for jj, l_ in enumerate(wl):
                            s.text(l_ if jj == 0 else "    " + l_, (x, yy), T_N, "TOP_LEFT")
                            yy -= T_N * 1.4
                        yy -= T_N * 0.25
                    return yy
                if not show:
                    yy = y
                    for ln in chunk:
                        for l_ in wrapw(ln, w - 2, T_N):
                            s.text(l_, (x, yy), T_N, "TOP_LEFT")
                            yy -= T_N * 1.4
                        yy -= T_N * 0.25
                    return yy
                return s.notes_block(x, y, ttl, chunk, h=T_N, width=w - 2, numbered=False, reg=False)
            blk_ref.append(self.block("notas", d, name=ttl))
            i0 += 2
            first = False

    def table_block(self, title, cols, rows, wide=False, bold_rows=(), h=T_S):
        def d(s, x, y, w):
            sc = w / sum(c[1] for c in cols)
            r = s.table(x, y, [(t, ww * sc, a) for t, ww, a in cols], rows, h=h, title=title, bold_rows=bold_rows)
            return r[0]
        self.block("tabla", d, wide=wide, name=title)

    def gd(self, items, title="TOLERANCIAS GEOMÉTRICAS (ISO 1101)"):
        """items = [(sym, tol, datum, texto)]. Si la lámina indica las tolerancias en las vistas (gd_in), la tabla es solo el resumen."""
        self.gd_items = list(items)
        self.h.gd_items = self.gd_items
        def d(s, x, y, w):
            ttl = "TOLERANCIAS GEOMÉTRICAS (ISO 1101): RESUMEN (MARCOS EN LAS VISTAS)" if self.indic else title
            for l_ in wrapw(ttl, w - 2, T_N + 0.5, True):
                s.text(l_, (x, y), T_N + 0.5, "TOP_LEFT", bold=True)
                y -= (T_N + 0.5) * 1.5
            y += (T_N + 0.5) * 1.5
            y -= (T_N + 0.5) * 1.7
            for sym, tol, datum, txt in items:
                wd = s.gdt((x, y - 6), sym, tol, datum)
                lines = wrapw(txt, w - wd - 6, T_N)
                for i, l_ in enumerate(lines):
                    s.text(l_, (x + wd + 3, y - 3.5 - i * T_N * 1.4), T_N, "MIDDLE_LEFT")
                y -= max(13.0, 4 + len(lines) * T_N * 1.4 + 3)
            return y
        self.block("gd", d, name=title)

    def ficha_block(self, keys, title="FICHA DE LA PIEZA (despiece)"):
        from hojas_base import tabla_despiece
        self.block("ficha", lambda s, x, y, w: tabla_despiece(self.ctx, s, x, y, keys, w, title=title, total=len(keys) > 1)[0], wide=True, name="ficha")

    def weld_block(self, ids, title="SOLDADURAS DE ESTA LÁMINA"):
        from hojas_base import tabla_soldaduras
        if ids:
            self.block("soldaduras", lambda s, x, y, w: tabla_soldaduras(self.ctx, s, x, y, ids, w, title=title)[0], wide=True, name="soldaduras")

    # ---------------- medición y empaque ----------------
    def _measure(self, b, w, fmt):
        sc = Sheet(fmt)
        y0 = 5000.0
        y = b.draw(sc, 0.0, y0, w)
        return y0 - y

    def pack(self, fmt, R):
        bx0, by0, bx1, by1 = R["right"]
        bw = bx1 - bx0 - 2
        Wl = R["left"][2] - R["left"][0]
        gap = 5.0
        narrow = [b for b in self.blocks if not b.wide]
        wide = [b for b in self.blocks if b.wide]
        for b in narrow:
            b.cont_title = False
            b.h = self._measure(b, bw, fmt)
        for b in wide:
            b.h = self._measure(b, Wl, fmt)
        placed, over = [], []
        y = by1 - 1
        for b in narrow:
            if y - b.h >= by0 + 2 and not over:
                placed.append((b, bx0, y))
                y -= b.h + gap
            else:
                over.append(b)
        band_end = y
        ncol = max(1, int((Wl + gap) // (bw + gap)))
        col_h = 0.0
        if over:
            lo = max(b.h for b in over)
            hi = sum(b.h for b in over) + gap * len(over)
            col_h = hi
            hh = lo
            while hh <= hi:
                hs_ = [0.0] * ncol
                k = 0
                ok = True
                for b in over:
                    while k < ncol and hs_[k] + b.h > hh + 0.01 and hs_[k] > 0:
                        k += 1
                    if k >= ncol:
                        ok = False
                        break
                    hs_[k] += b.h + gap
                if ok:
                    col_h = hh
                    break
                hh += 6
            else:
                col_h = hi
        strip_wide = sum(b.h + gap for b in wide)
        strip_h = strip_wide + (col_h + gap if over else 0)
        return dict(placed=placed, over=over, ncol=ncol, col_h=col_h, wide=wide, strip_h=strip_h, band_end=band_end, bw=bw, gap=gap, Wl=Wl, R=R)

    def draw_blocks(self, pk):
        s, R = self.s, pk["R"]
        if not hasattr(s, "reserved"):
            s.reserved = []
        s.block_rects = []
        for b, x, y in pk["placed"]:
            y1 = b.draw(s, x, y, pk["bw"])
            s.reserved.append((x, y1, x + pk["bw"], y))
            s.block_rects.append((x, y1, x + pk["bw"], y))
        x0 = R["left"][0]
        yy = 15.0 + pk["strip_h"]
        gap = pk["gap"]
        if pk["over"]:
            ytop = yy
            ncol = pk["ncol"]
            cols = [[] for _ in range(ncol)]
            hs_ = [0.0] * ncol
            k = 0
            for b in pk["over"]:
                while k < ncol - 1 and hs_[k] + b.h > pk["col_h"] + 0.01 and hs_[k] > 0:
                    k += 1
                cols[k].append(b)
                hs_[k] += b.h + gap
            for ci, col in enumerate(cols):
                xx = x0 + ci * (pk["bw"] + gap)
                yc = ytop
                for bi, b in enumerate(col):
                    b.cont_title = (bi == 0)      # al iniciar columna/zona nueva se repite el título con «(cont.)»
                    y1 = b.draw(s, xx, yc, pk["bw"])
                    s.reserved.append((xx, y1, xx + pk["bw"], yc))
                    s.block_rects.append((xx, y1, xx + pk["bw"], yc))
                    yc -= b.h + gap
            yy = ytop - pk["col_h"] - gap
        for b in pk["wide"]:
            y1 = b.draw(s, x0, yy, pk["Wl"])
            s.reserved.append((x0, y1, x0 + pk["Wl"], yy))
            s.block_rects.append((x0, y1, x0 + pk["Wl"], yy))
            yy -= b.h + gap

    def _try_format(self, fmt):
        ctx = self.ctx
        R = Sheet(fmt).regions(ctx.revs)
        pk = self.pack(fmt, R)
        zone = (R["left"][0], 15.0 + pk["strip_h"] + 2, R["left"][2], R["left"][3])
        if zone[3] - zone[1] < 60:
            return None
        if not self.specs:
            return dict(fmt=fmt, R=R, pk=pk, zone=zone, plan=None, fill=0.0)
        try:
            cells, sc, scheme = plan_cells(self.specs, ctx.shapes, zone)
        except RuntimeError:
            return None
        za = (zone[2] - zone[0]) * (zone[3] - zone[1])
        fill = 0.0
        for i, sp in enumerate(self.specs):
            a, b = sp.natural(sp_shapes(sp, ctx.shapes))
            fill += a * b * sc[i] ** 2
        return dict(fmt=fmt, R=R, pk=pk, zone=zone, plan=(cells, sc, scheme), fill=fill / za)

    # ---------------- construcción ----------------
    def build(self, iso_fill=None):
        """Compone la lámina; si alguna vista usó más líneas de cota (o un título más bajo) que las reservadas, corrige la reserva y recompone (máx. 3 veces)."""
        for it in range(4):
            self._build_once(iso_fill)
            grow = False
            for sp in self.specs:
                V = sp.V
                if V is None:
                    continue
                need = (V.lv["left"], V.lv["bottom"], V.lv["right"], V.lv["top"])
                if any(n_ > l_ for n_, l_ in zip(need, sp.lv)):
                    sp.lv = tuple(max(n_, l_) for n_, l_ in zip(need, sp.lv))
                    grow = True
            if not grow or it == 3:
                return
            h, s, ctx = self.h, self.s, self.ctx
            s.reset()
            COTAS.rows[:] = [r for r in COTAS.rows if r["sheet"] != h.plano]
            autodim.CADENAS[:] = [c for c in autodim.CADENAS if c["sheet"] != h.plano]
            ctx.balloons[h.plano] = set()
            h.welds_here = []
            self.named, self.scales, self.vlist = {}, [], []
            for sp in self.specs:
                sp.V = None

    def _build_once(self, iso_fill=None):
        h, s, ctx = self.h, self.s, self.ctx
        tries = getattr(self, "fmt_try", None) or [h.fmt]
        cands = [c for c in (self._try_format(f_) for f_ in tries) if c]
        if not cands:
            raise RuntimeError("ningún formato admite la disposición de " + h.plano)
        # vista principal a la escala normalizada siguiente (ISO 5455) si cabe y la lámina gana área de vistas
        sp0 = self.specs[0] if self.specs else None
        if getattr(self, "boost_main", False) and sp0 is not None and not sp0.iso and not sp0.custom and not getattr(self, "_boosted", False):
            self._boosted = True
            for _ in range(3):
                c0 = max(cands, key=lambda c: c["fill"])
                s0 = c0["plan"][1][0]
                up = [x for x in STD_SCALES if x > s0 * 1.0001]
                if not up or (sp0.maxs and up[0] > sp0.maxs * 1.0001):
                    break
                m0 = sp0.mins
                sp0.mins = up[0]
                c2 = [c for c in (self._try_format(f_) for f_ in tries) if c]
                import os as _os
                if _os.environ.get("PLANDBG"):
                    print("BOOST", h.plano, s0, "->", up[0], [(c["fmt"], c["plan"][1], round(c["fill"], 3)) for c in c2], "antes", c0["plan"][1], round(c0["fill"], 3))
                ok = [c for c in c2 if c["plan"][1][0] >= up[0] * 0.9999 and c["fill"] >= c0["fill"] * 0.9
                      and all(c["plan"][1][i] >= c0["plan"][1][i] * 0.49 for i in range(1, len(self.specs)))]
                if not ok:
                    sp0.mins = m0
                    break
                cands = ok
        elif getattr(self, "_boosted", False):
            pass
        bestf = max(c["fill"] for c in cands)
        # el formato más pequeño cuyo llenado alcanza el 85 % del mejor
        ch = next(c for c in sorted(cands, key=lambda c: ("A3", "A2", "A1").index(c["fmt"])) if c["fill"] >= 0.999 * bestf)
        if ch["fmt"] != h.fmt:
            h.fmt = ch["fmt"]
            s.reformat(ch["fmt"])
        h.R = ch["R"]
        self.R = h.R
        pk, zone = ch["pk"], ch["zone"]
        h.zone = zone
        h.strip_h = pk["strip_h"]
        specs = list(self.specs)
        shapes = ctx.shapes
        if specs:
            cells, sc, scheme = ch["plan"]
        else:
            cells, sc, scheme = {}, {}, None
        h.scheme = scheme
        import os as _os
        if _os.environ.get("PLANDBG"):
            print("PLAN", h.plano, h.fmt, zone, scheme, {i: (round(c[0]), round(c[1]), round(c[2]), round(c[3])) for i, c in cells.items()}, sc,
                  [sp.natural(sp_shapes(sp, shapes)) for sp in specs], [sp.margins() for sp in specs])
        COTAS.sheet = h.plano
        self.draw_blocks(pk)
        s.n_views0 = len(s.m)
        for i in range(len(specs)):
            sp = specs[i]
            cell = cells[i]
            r0_ = len(getattr(s, "reserved", []))
            if sp.custom:
                a, b = sp.nat
                mg = sp.margins()
                sc_ = _max_scale_fit(a, b, mg[0] + mg[2], mg[1] + mg[3], cell[2] - cell[0], cell[3] - cell[1], sp.maxs)
                ox = cell[0] + mg[0] + (cell[2] - cell[0] - mg[0] - mg[2] - a * sc_) / 2
                oy = cell[1] + mg[1] + (cell[3] - cell[1] - mg[1] - mg[3] - b * sc_) / 2
                sp.custom(s, ox, oy, sc_, self)
                if not hasattr(s, "views"):
                    s.views = []
                s.views.append((ox, oy, ox + a * sc_, oy + b * sc_))
                self.scales.append(sc_)
                if sp.title:
                    t_, esc_, h_ = sp.title, "ESC " + scale_txt(sc_), dr.T_T
                    wmax_ = cell[2] - cell[0] - 2
                    while h_ > 3.5 and dr.tw(t_, h_, True) > wmax_:
                        h_ -= 0.5
                    if dr.tw(t_, h_, True) > wmax_ and " (" in t_:
                        i_ = t_.index(" (")
                        t_, esc_ = t_[:i_], t_[i_:].strip() + "  " + esc_
                    wt_ = dr.tw(t_, h_, True)
                    cx_ = min(max(ox + a * sc_ / 2, cell[0] + 1 + wt_ / 2), cell[2] - 1 - wt_ / 2)
                    s.view_title((cx_, oy - 8 * (sp.lv[1] + 1) - 6), t_, esc_, h_)
                self._footprint(s, (ox, oy, ox + a * sc_, oy + b * sc_), sp, r0_, custom=True)
                continue
            shp = sp_shapes(sp, shapes)
            if not shp:
                continue
            kw = {}
            if sp.breaks:
                kw["breaks"] = sp.breaks
            if sp.iso:
                kw["free"] = True
            V = View.auto(s, shp, sp.view, cell, margin=sp.margins(), cut=sp.cut, win=sp.win, center=sp.center, std=not sp.iso, label=sp.label, hidden=sp.hidden, hatch_scale=sp.hs,
                          max_scale=sp.maxs if not sp.iso else None, only=sp.only, **kw)
            V.mat = sp.mat or {k: ctx.mat.get(k, "acero") for k in shp}
            V.draw(hatch=sp.hatch, layer_vis=sp.layer)
            sp.V = V
            self.named[sp.name] = V
            if not sp.iso:
                self.scales.append(V.scale)
            self.vlist.append(V)
            if sp.detail:
                par = self.named.get(sp.detail[0])
                if par is not None:
                    c = par.P(sp.detail[1])
                    s.detail_circle(c, sp.detail[2] * par.scale, sp.detail[3])
            if sp.auto is not False:
                try:
                    autodim.auto_dims(V, **(sp.auto or {}))
                except Exception as ex:
                    import traceback
                    print("   auto_dims falló", h.plano, sp.name, repr(ex))
                    traceback.print_exc()
            if sp.draw:
                sp.draw(V, self)
            if sp.title:
                V.title(sp.title)
            self._footprint(s, V.ext, sp, r0_, V=V)
        for cb in self.post:
            cb(self)
        self._draw_indic()
        if (iso_fill if iso_fill is not None else self.iso_fill):
            self.fill_free(zone)
        s.n_views1 = len(s.m)
        h.escala = self.fit_scale_txt() or "S/E"

    def _footprint(self, s, ext, sp, r0, V=None, custom=False):
        """Huella de la vista: geometría + pila de cotas usada + título + símbolos y llamadas dibujados en ella."""
        x0, y0, x1, y1 = ext
        if V is not None:
            lv = V.lv
            fx0, fy0, fx1, fy1 = x0 - 8 - 8.5 * lv["left"], y0 - 8 - 8.5 * lv["bottom"] - (TITLE_H if sp.title else 0), x1 + 8 + 8.5 * lv["right"], y1 + 8 + 8.5 * lv["top"]
        else:
            fx0, fy0, fx1, fy1 = x0 - 8, y0 - 8 - (TITLE_H if sp.title else 0) - 8 * sp.lv[1], x1 + 8, y1 + 8
        if sp.title:
            wt = min(tw(sp.title, dr.T_T, True), (sp.V.box[2] - sp.V.box[0]) if (V is not None and getattr(V, "box", None)) else 1e9)
            cx = (x0 + x1) / 2
            fx0, fx1 = min(fx0, cx - wt / 2 - 2), max(fx1, cx + wt / 2 + 2)
        for q in getattr(s, "reserved", [])[r0:]:
            if q[2] - q[0] < 200 and q[3] - q[1] < 200:
                fx0, fy0, fx1, fy1 = min(fx0, q[0]), min(fy0, q[1]), max(fx1, q[2]), max(fy1, q[3])
        if not hasattr(s, "footprints"):
            s.footprints = []
        s.footprints.append((fx0, fy0, fx1, fy1))

    def fit_scale_txt(self):
        sc = sorted(set(self.scales), reverse=True)
        return " / ".join(vistas.scale_txt(x) for x in sc) if sc else ""

    # ---------------- relleno ----------------
    def free_rect(self, zone, infl=14.0, st=4.0):
        x0, y0, x1, y1 = zone
        nx, ny = int((x1 - x0) / st), int((y1 - y0) / st)
        occ = [[False] * ny for _ in range(nx)]
        s = self.s
        rects = list(getattr(s, "views", [])) + list(getattr(s, "reserved", [])) + list(getattr(s, "footprints", []))
        for (a, b, c, d) in rects:
            for i in range(max(0, int((a - infl - x0) / st)), min(nx, int((c + infl - x0) / st) + 1)):
                for j in range(max(0, int((b - infl - y0) / st)), min(ny, int((d + infl - y0) / st) + 1)):
                    occ[i][j] = True
        best = (0, None)
        hist = [0] * nx
        for j in range(ny):
            for i in range(nx):
                hist[i] = 0 if occ[i][j] else hist[i] + 1
            stack = []
            for i in range(nx + 1):
                hcur = hist[i] if i < nx else 0
                start = i
                while stack and stack[-1][1] >= hcur:
                    s_, hh = stack.pop()
                    area = (i - s_) * hh
                    if area > best[0]:
                        best = (area, (s_, j - hh + 1, i, j + 1))
                    start = s_
                stack.append((start, hcur))
        if not best[1]:
            return None
        a, b, c, d = best[1]
        return (x0 + a * st, y0 + b * st, x0 + c * st, y0 + d * st)

    def fill_free(self, zone, min_size=95.0, max_n=2):
        """Rellena rectángulos libres con la isométrica de la pieza (escala libre) cuando sobra espacio: nunca decorativa."""
        ctx = self.ctx
        keys = [k for k in (self.iso_keys or getattr(self, "keys", [])) if k in ctx.shapes]
        if not keys:
            return
        done = 0
        for rect_zone in (zone, self.h.R["right"]):
            for _ in range(max_n):
                box = self.free_rect(rect_zone)
                if not box or box[2] - box[0] < min_size or box[3] - box[1] < min_size:
                    break
                sh = ctx.sh(*keys)
                V = View.auto(self.s, sh, "iso", box, margin=(10, 26, 10, 10), std=False, free=True, label="Isométrica")
                V.mat = {k: ctx.mat.get(k, "acero") for k in sh}
                V.draw(hatch=False)
                self.vlist.append(V)
                V.title("VISTA ISOMÉTRICA", h=T_N + 1.0)
                done += 1
                break
            if done:
                break

    # ---------------- utilidades de lámina ----------------
    def cut_mark(self, parent, label, p1, p2, look_deg, ext=14.0):
        V = self.named[parent]
        self.s.cut_line(V.P(p1), V.P(p2), label, look_deg, ext)
