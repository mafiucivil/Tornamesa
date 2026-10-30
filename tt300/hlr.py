"""Proyección con líneas ocultas (HLR) y cortes desde el modelo CadQuery."""
import math
import cadquery as cq
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union, polygonize

VIEWS = {
    "top": ((0, 0, 1), (1, 0, 0)),
    "front": ((0, -1, 0), (1, 0, 0)),       # mira hacia +y, pantalla (x, z)
    "back": ((0, 1, 0), (-1, 0, 0)),
    "right": ((1, 0, 0), (0, 1, 0)),        # mira hacia -x, pantalla (y, z)
    "left": ((-1, 0, 0), (0, -1, 0)),
    "iso": ((1, -1, 1), (1, 1, 0)),
    "iso2": ((1, -1.25, 0.9), (1.25, 1, 0)),
}


def basis(view):
    d, x = VIEWS[view]
    dn = [c / math.sqrt(sum(k * k for k in d)) for k in [0] for c in d]
    n = math.sqrt(sum(c * c for c in d)); d = [c / n for c in d]
    n = math.sqrt(sum(c * c for c in x)); x = [c / n for c in x]
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
                n = max(6, min(400, int(L / tol)))
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


NOCUT = {5, 8, 9, 11, 12, 13, 16}


def section(parts, view, plane_pt, keep_dir, tol=2.0, hidden=False, only=None, nocut=NOCUT):
    """parts: [(pos, shape)] cq.Shape. Corta con plano por plane_pt normal keep_dir (se conserva lado +keep_dir).
    Devuelve (vis, hid, hatch) con hatch = [(pos, outer, holes)] en coords de pantalla."""
    big = 20000
    nx, ny, nz = keep_dir
    # semiespacio a eliminar: caja del lado -keep_dir
    c = (plane_pt[0] - nx * big / 2, plane_pt[1] - ny * big / 2, plane_pt[2] - nz * big / 2)
    cutter = cq.Solid.makeBox(big, big, big, pnt=cq.Vector(c[0] - big / 2 * (1 - abs(nx)) - (big / 2 if nx else 0) + (big / 2 if nx else 0),
                                                          c[1], c[2])) if False else None
    halfbox = cq.Solid.makeBox(big, big, big).translate(cq.Vector(-big / 2, -big / 2, -big / 2))
    halfbox = halfbox.translate(cq.Vector(plane_pt[0] - nx * big / 2, plane_pt[1] - ny * big / 2, plane_pt[2] - nz * big / 2))
    kept, hatches = [], []
    plane = cq.Face.makePlane(big, big, basePnt=cq.Vector(*plane_pt), dir=cq.Vector(*keep_dir))
    for pos, shp in parts:
        if only and pos not in only:
            continue
        if pos in nocut:
            kept.append(shp)
            continue
        try:
            k = shp.cut(halfbox)
        except Exception:
            k = shp
        if k.isValid() and k.Volume() > 1e-3:
            kept.append(k)
        try:
            sec = shp.intersect(plane)
            for f in sec.Faces():
                segs = []
                for e in f.Edges():
                    if e.geomType() == "LINE":
                        pts = [e.startPoint(), e.endPoint()]
                    else:
                        n = max(8, min(300, int(e.Length() / tol)))
                        pts = [e.positionAt(i / n) for i in range(n + 1)]
                    pp = [proj_pt((p.x, p.y, p.z), view) for p in pts]
                    pp = [(round(x * 10) / 10, round(y * 10) / 10) for x, y in pp]
                    if len(pp) > 2 and abs(pp[0][0] - pp[-1][0]) < 0.6 and abs(pp[0][1] - pp[-1][1]) < 0.6:
                        pp[-1] = pp[0]
                    segs.append(LineString(pp))
                polys = list(polygonize(unary_union(segs)))
                g = None
                for pg in polys:
                    g = pg if g is None else g.symmetric_difference(pg)
                if g is None:
                    continue
                for gg in getattr(g, "geoms", [g]):
                    if gg.geom_type == "Polygon" and gg.area > 0.5:
                        hatches.append((pos, list(gg.exterior.coords), [list(i.coords) for i in gg.interiors]))
        except Exception as ex:
            print("sec fail", pos, ex)
    comp = cq.Compound.makeCompound(kept)
    vis, hid = hlr(comp, view, tol, hidden)
    return vis, hid, hatches


def _wire_pts(w, tol):
    pts = []
    for e in w.Edges():
        if e.geomType() == "LINE":
            seg = [e.startPoint(), e.endPoint()]
        else:
            n = max(8, min(300, int(e.Length() / tol)))
            seg = [e.positionAt(i / n) for i in range(n + 1)]
        if pts and (pts[-1] - seg[0]).Length > 1e-3 and (pts[-1] - seg[-1]).Length < 1e-3:
            seg = seg[::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts


def clip_polys(polys, win):
    """win=(x0,y0,x1,y1) en coords de pantalla del modelo."""
    b = box(*win)
    out = []
    for p in polys:
        if len(p) < 2:
            continue
        g = LineString(p).intersection(b)
        if g.is_empty:
            continue
        geoms = getattr(g, "geoms", [g])
        for gg in geoms:
            if gg.geom_type == "LineString" and len(gg.coords) >= 2:
                out.append(list(gg.coords))
    return out


def clip_hatch(hatches, win):
    b = box(*win)
    out = []
    for pos, outer, holes in hatches:
        try:
            pg = Polygon(outer, holes).buffer(0)
            g = pg.intersection(b)
        except Exception:
            continue
        for gg in getattr(g, "geoms", [g]):
            if gg.geom_type == "Polygon" and gg.area > 1:
                out.append((pos, list(gg.exterior.coords), [list(i.coords) for i in gg.interiors]))
    return out
