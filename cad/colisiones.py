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
