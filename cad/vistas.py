"""Vistas ortogonales e isométricas con líneas ocultas (HLR), cortes con achurado y acotado verificado contra el modelo 3D.
Cada cota que se dibuja con View.dim / View.dim_dia queda registrada en el CHEQUEO (cad/out/chequeo_cotas.csv): se comprueba que
los puntos de cota caen sobre la superficie del sólido 3D (o, para ejes, sobre el eje de una superficie cilíndrica real) y que el
valor rotulado coincide con la distancia medida entre esos puntos. La cota nunca se escribe a mano: sale de los puntos del modelo."""
import math, sys, pathlib
import cadquery as cq
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.BRep import BRep_Tool
from OCP.Geom import Geom_CylindricalSurface
from shapely.geometry import LineString, Polygon, box as sbox

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import f, fm
import draw

HLR_CACHE = {}
STD_SCALES = [1/100, 1/50, 1/25, 1/20, 1/10, 1/5, 1/2.5, 1/2, 1/1, 2/1, 5/1]


def snap_scale(s):
    """Mayor escala normalizada (ISO 5455) que no excede s."""
    ok = [x for x in STD_SCALES if x <= s * 1.0001]
    return ok[-1] if ok else STD_SCALES[0]


def scale_txt(sc):
    if sc >= 1:
        return f"{sc:g}:1"
    return f"1:{1 / sc:g}".replace(".", ",")

VIEWS = {
    "top": ((0, 0, 1), (1, 0, 0)),
    "bottom": ((0, 0, -1), (1, 0, 0)),
    "front": ((0, -1, 0), (1, 0, 0)),
    "back": ((0, 1, 0), (-1, 0, 0)),
    "right": ((1, 0, 0), (0, 1, 0)),
    "left": ((-1, 0, 0), (0, -1, 0)),
    "iso": ((1, -1, 0.9), (1, 1, 0)),
}


def _norm(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def basis(view):
    d, x = VIEWS[view]
    d, x = _norm(d), _norm(x)
    y = [d[1] * x[2] - d[2] * x[1], d[2] * x[0] - d[0] * x[2], d[0] * x[1] - d[1] * x[0]]
    return d, x, y


def proj_pt(p, view):
    d, x, y = basis(view)
    return (sum(a * b for a, b in zip(p, x)), sum(a * b for a, b in zip(p, y)))


def _edges_to_polys(comp, tol):
    out = []
    if comp is None or comp.IsNull():
        return out
    for e in cq.Shape.cast(comp).Edges():
        try:
            if e.geomType() == "LINE":
                a, b = e.startPoint(), e.endPoint()
                out.append([(a.x, a.y), (b.x, b.y)])
            else:
                L = e.Length()
                n = max(6, min(500, int(L / tol)))
                pts = [e.positionAt(i / n) for i in range(n + 1)]
                out.append([(p.x, p.y) for p in pts])
        except Exception:
            pass
    return out


def hlr(shape, view, tol=2.0, hidden=False):
    d, x = VIEWS[view]
    ax = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*d), gp_Dir(*x))
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    algo.Projector(HLRAlgo_Projector(ax))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = _edges_to_polys(h.VCompound(), tol) + _edges_to_polys(h.OutLineVCompound(), tol)
    hid = []
    if hidden:
        hid = _edges_to_polys(h.HCompound(), tol) + _edges_to_polys(h.OutLineHCompound(), tol)
    return vis, hid


def _wire_pts(w, tol):
    """Puntos ordenados de un alambre cerrado (encadena las aristas por extremos coincidentes)."""
    segs = []
    for e in w.Edges():
        if e.geomType() == "LINE":
            seg = [e.startPoint(), e.endPoint()]
        else:
            n = max(8, min(400, int(e.Length() / tol)))
            seg = [e.positionAt(i / n) for i in range(n + 1)]
        segs.append(seg)
    if not segs:
        return []
    chain = list(segs.pop(0))
    while segs:
        end = chain[-1]
        best, bi, brev = 1e18, 0, False
        for i, sg in enumerate(segs):
            d0, d1 = (sg[0] - end).Length, (sg[-1] - end).Length
            if d0 < best:
                best, bi, brev = d0, i, False
            if d1 < best:
                best, bi, brev = d1, i, True
        sg = segs.pop(bi)
        if brev:
            sg = sg[::-1]
        chain.extend(sg[1:])
    return chain


def clip_polys(polys, win):
    b = sbox(*win)
    out = []
    for p in polys:
        if len(p) < 2:
            continue
        g = LineString(p).intersection(b)
        if g.is_empty:
            continue
        for gg in getattr(g, "geoms", [g]):
            if gg.geom_type == "LineString" and len(gg.coords) >= 2:
                out.append(list(gg.coords))
    return out


def numtxt(v, n=0):
    if n:
        return fm(v, n)
    if abs(v - round(v)) < 1e-6:
        return f(v)
    return fm(v, 1 if abs(v * 10 - round(v * 10)) < 1e-6 else 2)


# ----------------------------------------------------------------------------------------------
# registro de cotas y comprobación contra el modelo
# ----------------------------------------------------------------------------------------------
class Cotas:
    """Registro global del chequeo de cotas; se alimenta desde View.dim."""

    def __init__(self):
        self.rows = []
        self.shapes = {}          # clave de pieza -> cq.Shape (compuesto)
        self._bb = {}
        self._cyl = {}
        self.sheet = ""

    def set_shapes(self, shapes):
        self.shapes = shapes
        self._bb = {}
        self._cyl = {}

    def bbox(self, key):
        if key not in self._bb:
            b = self.shapes[key].BoundingBox()
            self._bb[key] = (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)
        return self._bb[key]

    def dist_to_surface(self, p, keys):
        best = 1e9
        v = cq.Vertex.makeVertex(*p)
        for k in keys:
            if k not in self.shapes:
                continue
            bb = self.bbox(k)
            if not (bb[0] - 0.5 <= p[0] <= bb[1] + 0.5 and bb[2] - 0.5 <= p[1] <= bb[3] + 0.5 and bb[4] - 0.5 <= p[2] <= bb[5] + 0.5):
                continue
            try:
                best = min(best, v.distance(self.shapes[k]))
            except Exception:
                pass
            if best < 0.02:
                break
        return best

    def cylinders(self, key):
        if key in self._cyl:
            return self._cyl[key]
        out = []
        for fc in self.shapes[key].Faces():
            if fc.geomType() != "CYLINDER":
                continue
            try:
                srf = BRep_Tool.Surface_s(fc.wrapped)
                cs = Geom_CylindricalSurface.DownCast(srf) if hasattr(Geom_CylindricalSurface, "DownCast") else srf
                cy = cs.Cylinder()
                loc, dr = cy.Axis().Location(), cy.Axis().Direction()
                out.append((cy.Radius(), (loc.X(), loc.Y(), loc.Z()), (dr.X(), dr.Y(), dr.Z())))
            except Exception:
                pass
        self._cyl[key] = out
        return out

    def axis_ok(self, c, r, keys, tol=0.05):
        for k in keys:
            if k not in self.shapes:
                continue
            for (rr, loc, dr) in self.cylinders(k):
                if abs(rr - r) > tol:
                    continue
                w = (c[0] - loc[0], c[1] - loc[1], c[2] - loc[2])
                cx = (w[1] * dr[2] - w[2] * dr[1], w[2] * dr[0] - w[0] * dr[2], w[0] * dr[1] - w[1] * dr[0])
                if math.sqrt(sum(a * a for a in cx)) < tol:
                    return True
        return False

    def add(self, **kw):
        kw["sheet"] = self.sheet
        self.rows.append(kw)
        return kw


COTAS = Cotas()


# ----------------------------------------------------------------------------------------------
class View:
    """Vista de un conjunto de piezas sobre una lámina.
    S: Sheet; shapes: dict clave -> cq.Shape; view: 'top','front','right','iso',…; origin: (x, y) en papel del punto 'center' del modelo;
    scale: papel/modelo; center: punto 3D del modelo que va en 'origin'."""

    def __init__(self, S, shapes, view, origin, scale, center=(0, 0, 0), win=None, cut=None, hidden=False, tol=None, nocut=(), hatch_scale=0.5,
                 only=None, label=""):
        self.S, self.shapes, self.view, self.scale = S, shapes, view, scale
        self.origin = origin
        self.cu, self.cv = proj_pt(center, view)
        self.win = win              # ventana en coordenadas de pantalla del modelo (u0, v0, u1, v1) relativas a 'center'
        self.cut, self.hidden, self.nocut, self.hatch_scale = cut, hidden, set(nocut), hatch_scale
        self.keys = list(shapes) if only is None else list(only)
        self.tol = tol or max(0.6, 1.2 / scale / 10 * 10 / 10)
        self.label = label
        self.lv = {"top": 0, "bottom": 0, "left": 0, "right": 0}
        self.ext = None
        self.mat = {}

    # -- coordenadas --
    def uv(self, p):
        u, v = proj_pt(p, self.view)
        return (u - self.cu, v - self.cv)

    def P(self, x, y=None, z=None):
        p = x if y is None else (x, y, z)
        u, v = self.uv(p)
        return (self.origin[0] + u * self.scale, self.origin[1] + v * self.scale)

    def Pt2(self, uv):
        return (self.origin[0] + uv[0] * self.scale, self.origin[1] + uv[1] * self.scale)

    # -- dibujo --
    def draw(self, layer_vis="VIS", layer_hid="OCU", hatch=True):
        S = self.S
        parts = [(k, self.shapes[k]) for k in self.keys]
        hatches = []
        kept = []
        ck = (tuple((k, id(self.shapes[k])) for k in self.keys), self.view, self.cut, tuple(sorted(self.nocut)), self.hidden, round(self.tol, 3))
        cached = HLR_CACHE.get(ck)
        if cached is None and self.cut:
            plane_pt, keep_dir = self.cut
            big = 40000
            nx, ny, nz = keep_dir
            halfbox = cq.Solid.makeBox(big, big, big).translate(cq.Vector(-big / 2, -big / 2, -big / 2)).translate(
                cq.Vector(plane_pt[0] - nx * big / 2, plane_pt[1] - ny * big / 2, plane_pt[2] - nz * big / 2))
            plane = cq.Face.makePlane(big, big, basePnt=cq.Vector(*plane_pt), dir=cq.Vector(*keep_dir))
            for k, shp in parts:
                if k in self.nocut:
                    kept.append(shp)
                    continue
                try:
                    kp = shp.cut(halfbox)
                except Exception:
                    kp = shp
                if kp.Volume() > 1e-3:
                    kept.append(kp)
                try:
                    sec = shp.intersect(plane)
                    for fc in sec.Faces():
                        outer = [self.uv((p.x, p.y, p.z)) for p in _wire_pts(fc.outerWire(), self.tol)]
                        holes = [[self.uv((p.x, p.y, p.z)) for p in _wire_pts(w, self.tol)] for w in fc.innerWires()]
                        hatches.append((k, outer, holes))
                except Exception as ex:
                    print("   sección falló", k, ex)
        elif cached is None:
            kept = [s for _, s in parts]
        if cached is None:
            comp = cq.Compound.makeCompound([cq.Compound.makeCompound(list(s.Solids())) if hasattr(s, "Solids") else s for s in kept])
            vis, hid = hlr(comp, self.view, self.tol, self.hidden)
            vis = [[(u - self.cu, v - self.cv) for (u, v) in pl] for pl in vis]
            hid = [[(u - self.cu, v - self.cv) for (u, v) in pl] for pl in hid]
            HLR_CACHE[ck] = (vis, hid, hatches)
        else:
            vis, hid, hatches = cached
        if self.win:
            vis, hid = clip_polys(vis, self.win), clip_polys(hid, self.win)
        xs, ys = [], []
        for pl in vis:
            pp = [self.Pt2(p) for p in pl]
            S.pline(pp, layer_vis)
            xs += [p[0] for p in pp]; ys += [p[1] for p in pp]
        for pl in hid:
            S.pline([self.Pt2(p) for p in pl], layer_hid)
        if xs:
            self.ext = (min(xs), min(ys), max(xs), max(ys))
            if not hasattr(S, "views"):
                S.views = []
            S.views.append(self.ext)
        if hatch:
            used = set()
            for n_, (k, outer, holes) in enumerate(hatches):
                try:
                    pg = Polygon(outer, holes).buffer(0)
                    if self.win:
                        pg = pg.intersection(sbox(*self.win))
                    cls = self.mat.get(k, "acero")
                    pat, ang0, sc0 = draw.HATCH_MAT[cls]
                    ang = ang0 + (90.0 if (self.keys.index(k) % 2) else 0.0) if cls == "acero" else ang0
                    for gg in getattr(pg, "geoms", [pg]):
                        if gg.geom_type == "Polygon" and gg.area > 0.3:
                            S.hatch_poly([self.Pt2(p) for p in list(gg.exterior.coords)[:-1]], [[self.Pt2(p) for p in list(i.coords)[:-1]] for i in gg.interiors],
                                         scale=self.hatch_scale * sc0, angle=ang, pattern=pat)
                            used.add(cls)
                except Exception:
                    pass
            S.hatch_classes = getattr(S, "hatch_classes", set()) | used
        return self

    # -- fitting automático --
    @classmethod
    def auto(cls, S, shapes, view, box, margin=(14, 14, 14, 14), cut=None, win=None, center=(0, 0, 0), max_scale=None, std=True, **kw):
        """Vista que llena la caja de papel 'box' (x0,y0,x1,y1) descontando margin=(izq,abajo,der,arriba) para cotas. Escala normalizada ISO 5455."""
        keys = kw.get("only") or list(shapes)
        if win is not None:
            u0, v0, u1, v1 = win
            u0, u1, v0, v1 = u0, u1, v0, v1
            cu = cv = 0.0
            eu0, eu1, ev0, ev1 = u0, u1, v0, v1
        else:
            eu0 = ev0 = 1e18; eu1 = ev1 = -1e18
            for k in keys:
                b = shapes[k].BoundingBox()
                for x_ in (b.xmin, b.xmax):
                    for y_ in (b.ymin, b.ymax):
                        for z_ in (b.zmin, b.zmax):
                            u, v = proj_pt((x_, y_, z_), view)
                            eu0, eu1, ev0, ev1 = min(eu0, u), max(eu1, u), min(ev0, v), max(ev1, v)
            cu, cv = proj_pt(center, view)
            eu0, eu1, ev0, ev1 = eu0 - cu, eu1 - cu, ev0 - cv, ev1 - cv
        bw = box[2] - box[0] - margin[0] - margin[2]
        bh = box[3] - box[1] - margin[1] - margin[3]
        sc = min(bw / max(eu1 - eu0, 1e-6), bh / max(ev1 - ev0, 1e-6))
        if max_scale:
            sc = min(sc, max_scale)
        sc = snap_scale(sc) if std else sc
        ox = box[0] + margin[0] + bw / 2 - (eu0 + eu1) / 2 * sc
        oy = box[1] + margin[1] + bh / 2 - (ev0 + ev1) / 2 * sc
        v = cls(S, shapes, view, (ox, oy), sc, center=center, win=win, cut=cut, **kw)
        v.box = box
        return v

    @property
    def esc(self):
        return "ESC " + scale_txt(self.scale)

    def title(self, text, dy=0.0, h=draw.T_T):
        """Título de la vista (debajo de su extensión) con escala."""
        x0, y0, x1, y1 = self.ext or (self.origin[0], self.origin[1], self.origin[0], self.origin[1])
        low = y0 - 8 * (max(self.lv["bottom"], 0) + 1) - 6 + dy
        self.S.view_title(((x0 + x1) / 2, low - 2), text, self.esc, h)
        return low

    def circles(self, keys=None, rmin=0.0, rmax=1e9, axis_tol=1e-3):
        """Cilindros cuyo eje es paralelo a la dirección de mirada: [(u, v, r)] (coordenadas del modelo relativas al centro, sin duplicados)."""
        d, _, _ = basis(self.view)
        out = {}
        for k in keys or self.keys:
            for (rr, loc, dr) in COTAS.cylinders(k):
                if abs(abs(sum(a * b for a, b in zip(dr, d))) - 1) > axis_tol or not (rmin <= rr <= rmax):
                    continue
                u, v = self.uv(loc)
                out[(round(u, 1), round(v, 1), round(rr, 2))] = (u, v, rr)
        return sorted(out.values(), key=lambda t: (t[2], t[1], t[0]))

    # -- cotas con apilado automático --
    def _lvl(self, side, level):
        if level is None:
            level = self.lv[side]
            self.lv[side] += 1
        else:
            self.lv[side] = max(self.lv[side], level + 1)
        return level

    def dimh(self, a, b, side="bottom", level=None, gap=8.0, step=8.5, **kw):
        """Cota horizontal con la línea de cota apilada fuera de la vista (side top|bottom)."""
        lv = self._lvl(side, level)
        pa, pb = self.P(a), self.P(b)
        x0, y0, x1, y1 = self.ext or (0, 0, 0, 0)
        if side == "top":
            off = (y1 + gap + lv * step) - max(pa[1], pb[1])
        else:
            off = (y0 - gap - lv * step) - min(pa[1], pb[1])
        return self.dim(a, b, off, orient="h", **kw)

    def dimv(self, a, b, side="right", level=None, gap=8.0, step=8.5, **kw):
        lv = self._lvl(side, level)
        pa, pb = self.P(a), self.P(b)
        x0, y0, x1, y1 = self.ext or (0, 0, 0, 0)
        if side == "right":
            off = (x1 + gap + lv * step) - max(pa[0], pb[0])
        else:
            off = (x0 - gap - lv * step) - min(pa[0], pb[0])
        return self.dim(a, b, off, orient="v", **kw)

    def chain_h(self, pts, side="bottom", level=None, on=None, **kw):
        """Cadena de cotas horizontales entre puntos 3D consecutivos (ordenados por u) en una misma línea de cota."""
        lv = self._lvl(side, level)
        pts = sorted(pts, key=lambda p: self.uv(p)[0])
        for a, b in zip(pts, pts[1:]):
            if abs(self.uv(b)[0] - self.uv(a)[0]) > 0.05:
                self.dimh(a, b, side, lv, on=on, **kw)

    def chain_v(self, pts, side="right", level=None, on=None, **kw):
        lv = self._lvl(side, level)
        pts = sorted(pts, key=lambda p: self.uv(p)[1])
        for a, b in zip(pts, pts[1:]):
            if abs(self.uv(b)[1] - self.uv(a)[1]) > 0.05:
                self.dimv(a, b, side, lv, on=on, **kw)

    def note_hole(self, c3, r, ang_deg, text, ext=14.0, on=None):
        """Llamada «n × Ø… » apuntando a un agujero (radio r del modelo), verificada contra el eje del cilindro."""
        ok = COTAS.axis_ok(c3, r, on or self.keys)
        COTAS.add(vista=self.label, texto=text, valor_dibujo=round(2 * r, 3), tipo="agujero", extremo_a="eje OK" if ok else "eje NO", extremo_b="", ok=bool(ok))
        if not ok:
            print(f"   AGUJERO NO VERIFICADO [{COTAS.sheet}] {text}")
        a = math.radians(ang_deg)
        c = self.P(c3)
        p1 = (c[0] + r * self.scale * math.cos(a), c[1] + r * self.scale * math.sin(a))
        q = (c[0] + (r * self.scale + ext) * math.cos(a), c[1] + (r * self.scale + ext) * math.sin(a))
        self.S.leader(p1, q, text)

    def note_pt(self, p3, off, text, on=None, lines=None, dot=False):
        """Llamada de texto con flecha hacia un punto 3D de la superficie (verificada)."""
        d = COTAS.dist_to_surface(p3, on or self.keys)
        ok = d < 0.05
        COTAS.add(vista=self.label, texto=text if lines is None else " | ".join(lines), valor_dibujo=0.0, tipo="llamada", extremo_a=f"{d:.3f}", extremo_b="", ok=bool(ok))
        if not ok:
            print(f"   LLAMADA NO SOBRE LA SUPERFICIE [{COTAS.sheet}] {text}: {d:.2f}")
        p = self.P(p3)
        self.S.leader(p, (p[0] + off[0], p[1] + off[1]), text, lines=lines, dot=dot)

    # -- acotado con verificación --
    def _check(self, p3a, p3b, value, text, on, virt_a=None, virt_b=None, tipo="lineal"):
        keys = on or self.keys
        res = {"vista": self.label, "texto": text, "valor_dibujo": round(value, 3), "tipo": tipo}
        da = COTAS.axis_ok(p3a, virt_a, keys) if virt_a else COTAS.dist_to_surface(p3a, keys)
        db = COTAS.axis_ok(p3b, virt_b, keys) if virt_b else COTAS.dist_to_surface(p3b, keys)
        ok_a = da is True or (not isinstance(da, bool) and da < 0.05)
        ok_b = db is True or (not isinstance(db, bool) and db < 0.05)
        res["extremo_a"] = "eje OK" if da is True else ("eje NO" if da is False else f"{da:.3f}")
        res["extremo_b"] = "eje OK" if db is True else ("eje NO" if db is False else f"{db:.3f}")
        res["ok"] = bool(ok_a and ok_b)
        COTAS.add(**res)
        if not res["ok"]:
            print(f"   COTA NO VERIFICADA [{COTAS.sheet}] {text}: {res['extremo_a']} / {res['extremo_b']}")

    def dim(self, p3a, p3b, off, text=None, orient="h", on=None, virt_a=None, virt_b=None, prefix="", suffix="", n=0, **kw):
        """Cota lineal entre dos puntos 3D. orient 'h' mide u, 'v' mide v, 'a' alineada. text None -> valor medido formateado (con prefix/suffix).
        virt_a/virt_b: radio r si el extremo es el centro de una superficie cilíndrica (eje)."""
        ua, va = self.uv(p3a)
        ub, vb = self.uv(p3b)
        val = abs(ub - ua) if orient == "h" else abs(vb - va) if orient == "v" else math.hypot(ub - ua, vb - va)
        # valor 3D real a lo largo de la dirección acotada (la vista no debe distorsionar: se mide en pantalla = en el modelo)
        txt = text if text is not None else f"{prefix}{numtxt(val, n)}{suffix}"
        self._check(p3a, p3b, val, txt, on, virt_a, virt_b)
        self.S.dim(self.P(p3a), self.P(p3b), off, txt, orient, **kw)
        return val

    def dim_dia(self, c3, r, ang_deg, text=None, axis_dir=None, ext=8.0, on=None, prefix="Ø", suffix="", **kw):
        """Cota de diámetro (en vista de planta: círculo centrado en c3 con radio r)."""
        txt = text if text is not None else f"{prefix}{numtxt(2 * r)}{suffix}"
        a = math.radians(ang_deg)
        keys = on or self.keys
        ok = COTAS.axis_ok(c3, r, keys)
        COTAS.add(vista=self.label, texto=txt, valor_dibujo=round(2 * r, 3), tipo="diámetro", extremo_a="eje OK" if ok else "eje NO", extremo_b="", ok=bool(ok))
        if not ok:
            print(f"   DIÁMETRO NO VERIFICADO [{COTAS.sheet}] {txt}")
        self.S.dim_dia(self.P(c3), r * self.scale, ang_deg, txt, ext=ext, **kw)

    def dim_rad(self, c3, r, ang_deg, text=None, on=None, ext=8.0, **kw):
        txt = text if text is not None else f"R{numtxt(r)}"
        ok = COTAS.axis_ok(c3, r, on or self.keys)
        COTAS.add(vista=self.label, texto=txt, valor_dibujo=round(r, 3), tipo="radio", extremo_a="eje OK" if ok else "eje NO", extremo_b="", ok=bool(ok))
        if not ok:
            print(f"   RADIO NO VERIFICADO [{COTAS.sheet}] {txt}")
        self.S.dim_rad(self.P(c3), r * self.scale, ang_deg, txt, ext=ext, **kw)
