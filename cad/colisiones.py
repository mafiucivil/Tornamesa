"""Control de calidad de las láminas sobre el DXF (o el modelspace en memoria):
- choques de texto: dos TEXT cuyos recuadros (ezdxf bbox) se intersectan en más del 20 % del área del menor (criterio del verificador);
- salida del marco: ninguna entidad fuera del rectángulo interior del marco ISO 5457;
- invasión: ninguna entidad del cuerpo (vistas, cotas, símbolos, tablas) dentro del cajetín, y ninguna entidad dibujada en la fase de vistas sobre
  los bloques de notas/tablas de la banda lateral.
Uso como script: python3 cad/colisiones.py <dir_con_dxf>"""
import sys, glob, os, warnings
warnings.filterwarnings("ignore")
import ezdxf
from ezdxf import bbox

UMBRAL = 0.20


def text_boxes(entities):
    out = []
    for e in entities:
        if e.dxftype() != "TEXT":
            continue
        s = e.dxf.text.strip()
        if not s:
            continue
        b = bbox.extents([e], fast=False)
        if not b.has_data:
            continue
        out.append([b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y, s, e])
    return out


def overlap(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0.15 or iy <= 0.15:
        return 0.0
    ar = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return ix * iy / ar if ar > 0 else 0.0


def choques(entities, umbral=UMBRAL):
    w = text_boxes(entities)
    hits = []
    w.sort(key=lambda t: t[0])
    for i in range(len(w)):
        a = w[i]
        for j in range(i + 1, len(w)):
            b = w[j]
            if b[0] > a[2]:
                break
            if overlap(a, b) > umbral:
                hits.append((a[4][:40], b[4][:40]))
    return hits


def text_polys(entities, shrink=0.35):
    """Recuadros de los textos como polígonos (orientados si el texto está girado), reducidos 'shrink' mm por lado (negativo: ampliados)."""
    from shapely.geometry import Polygon, box
    import math
    tb = []
    for b in text_boxes(entities):
        e = b[5]
        rot = (e.dxf.get("rotation", 0.0) or 0.0) % 180.0
        if min(abs(rot), abs(rot - 90), abs(rot - 180)) > 0.5:
            th = math.radians(rot)
            c_, s_ = abs(math.cos(th)), abs(math.sin(th))
            W_, H_ = b[2] - b[0], b[3] - b[1]
            hh = e.dxf.height * 1.15
            w = (W_ - hh * s_) / c_ if c_ > 0.3 else (H_ - hh * c_) / s_
            w = max(w, hh)
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            ux, uy = math.cos(th), math.sin(th)
            vx, vy = -uy, ux
            hw, hv = w / 2 - shrink, hh / 2 - shrink
            if hw <= 0 or hv <= 0:
                continue
            poly = Polygon([(cx + sx * hw * ux + sy * hv * vx, cy + sx * hw * uy + sy * hv * vy) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        else:
            x0, y0, x1, y1 = b[0] + shrink, b[1] + shrink, b[2] - shrink, b[3] - shrink
            if not (x1 > x0 and y1 > y0):
                continue
            poly = box(x0, y0, x1, y1)
        tb.append((poly, b[4], (round(b[0], 1), round(b[1], 1), round(b[2], 1), round(b[3], 1))))
    return tb


def cota_segments(e):
    if e.dxftype() == "LINE":
        return [((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y))]
    if e.dxftype() == "LWPOLYLINE":
        pts = [(float(p[0]), float(p[1])) for p in e.get_points()]
        if e.closed and pts:
            pts.append(pts[0])
        return list(zip(pts, pts[1:]))
    return []


def lineas_sobre_texto(entities, shrink=0.35, layers=("COTA",)):
    """Líneas de cota, de extensión y de referencia (capa COTA) que atraviesan el recuadro de un texto (reducido 'shrink' mm por lado
    para no contar el contacto del texto con su propia línea de cota o su codo). Devuelve [(texto, capa, tipo, recuadro, segmento)]."""
    from shapely.geometry import LineString
    from shapely.strtree import STRtree
    tb = text_polys(entities, shrink)
    if not tb:
        return []
    tree = STRtree([t[0] for t in tb])
    hits = []
    for e in entities:
        if e.dxf.layer not in layers:
            continue
        for a, b in cota_segments(e):
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) < 1e-6:
                continue
            ls = LineString([a, b])
            for i in tree.query(ls):
                if tb[int(i)][0].intersects(ls):
                    hits.append((tb[int(i)][1][:40], e.dxf.layer, e.dxftype(), tb[int(i)][2], tuple(round(float(v), 1) for v in (a[0], a[1], b[0], b[1]))))
    return hits


def fuera_de_marco(entities, W, H, tol=0.3):
    """Entidades fuera del rectángulo interior del marco (20, 10, W−10, H−10); las marcas de zona y centrado del propio marco se excluyen."""
    L, B, R_, T = 20.0, 10.0, W - 10.0, H - 10.0
    out = []
    for e in entities:
        if e.dxf.layer in ("MARCO",) or (e.dxftype() in ("LINE", "TEXT") and e.dxf.layer == "FINA" and getattr(e, "_marco", False)):
            continue
        b = bbox.extents([e], fast=True)
        if not b.has_data:
            continue
        if b.extmin.x < L - tol or b.extmin.y < B - tol or b.extmax.x > R_ + tol or b.extmax.y > T + tol:
            out.append((e.dxftype(), (e.dxf.text[:40] if e.dxftype() == "TEXT" else e.dxf.layer), [round(v, 1) for v in (b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)]))
    return out


def invasiones(entities, rects, tol=0.3):
    """Entidades cuyo bbox se mete en alguno de los rectángulos prohibidos [(x0, y0, x1, y1, nombre)]."""
    out = []
    for e in entities:
        b = bbox.extents([e], fast=True)
        if not b.has_data:
            continue
        for (x0, y0, x1, y1, nm) in rects:
            if b.extmin.x < x1 - tol and b.extmax.x > x0 + tol and b.extmin.y < y1 - tol and b.extmax.y > y0 + tol:
                out.append((nm, e.dxftype(), (e.dxf.text[:40] if e.dxftype() == "TEXT" else e.dxf.layer)))
                break
    return out


if __name__ == "__main__":
    tot = 0
    res = []
    for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.dxf"))):
        m = ezdxf.readfile(f).modelspace()
        h = choques(list(m))
        res.append((os.path.basename(f), h))
        tot += len(h)
    for n, h in res:
        if h:
            print(f"{n:26s} choques={len(h):3d} {h[:4]}")
    print("TOTAL choques", tot, "| láminas con choque", sum(1 for r in res if r[1]), "de", len(res))
