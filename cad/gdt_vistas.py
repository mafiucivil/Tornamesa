"""Indicaciones en las vistas (B-20, B-44, N-14): marcos de tolerancia geométrica (ISO 1101), indicadores de datum (ISO 5459) y símbolos de
rugosidad con línea de referencia (ISO 1302 / ISO 21920-1) que tocan la superficie o la cota que controlan.

Cada indicación busca su lugar libre en la lámina ya dibujada: el marco, el recuadro de datum o el símbolo no pueden pisar ningún texto ni
ninguna línea, y su línea de referencia no puede atravesar textos. Modos de anclaje:
  - «surf»: flecha (o triángulo de datum) sobre el contorno de la superficie, en el punto 3D dado, con la línea normal a la superficie (dirección d);
  - «dim»: elemento derivado (eje, plano medio): la flecha o el triángulo se apoyan en la prolongación de la línea de cota del tamaño (texto que
    empieza por el prefijo dado), alineados con ella (ISO 1101, 7.2; ISO 5459, 6.3);
  - «callout»: el marco se coloca bajo el texto de la llamada de un agujero (texto que empieza por el prefijo dado), unido a su línea de referencia."""
import math
from draw import tw, T_N

FRAME_H = 7.0


def _frame_w(tol, datum, h=T_N):
    parts = [d for d in (datum if isinstance(datum, (list, tuple)) else [datum])] if datum else []
    return 7.0 + max(14.0, tw(tol, h) + 5) + sum(max(7.0, tw(d, h) + 3.0) for d in parts)


class Libre:
    """Obstáculos de la lámina en el momento de la consulta: recuadros de texto y segmentos de línea."""

    def __init__(self, s, zone):
        import colisiones as C
        from shapely.geometry import LineString, box
        from shapely.strtree import STRtree
        self.s = s
        self.zone = zone
        ents = list(s.m)
        self.tb = [box(b[0] - 0.8, b[1] - 0.8, b[2] + 0.8, b[3] + 0.8) for b in C.text_boxes(ents)]
        segs = []
        for e in ents:
            t = e.dxftype()
            if t in ("LINE", "LWPOLYLINE"):
                for a, b in C.cota_segments(e):
                    if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1e-6:
                        segs.append(LineString([a, b]))
            elif t in ("CIRCLE", "ARC"):
                c, r = e.dxf.center, e.dxf.radius
                a0, a1 = (0.0, 360.0) if t == "CIRCLE" else (e.dxf.start_angle, e.dxf.end_angle)
                if a1 < a0:
                    a1 += 360.0
                n = max(8, int((a1 - a0) / 8))
                pts = [(c.x + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), c.y + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
                segs.append(LineString(pts))
            elif t == "HATCH":
                try:
                    for path in e.paths:
                        vs = [(v[0], v[1]) for v in getattr(path, "vertices", [])]
                        if len(vs) > 2:
                            segs.append(LineString(vs + [vs[0]]))
                except Exception:
                    pass
        self.segs = segs
        self.ts = STRtree(self.tb) if self.tb else None
        self.ss = STRtree(segs) if segs else None
        self.rects = [box(*r[:4]) for r in getattr(s, "block_rects", [])]
        self.extra = []

    def ok_rect(self, x0, y0, x1, y1, pad=1.0):
        from shapely.geometry import box
        z = self.zone
        if x0 < z[0] + 1 or y0 < z[1] + 1 or x1 > z[2] - 1 or y1 > z[3] - 1:
            return False
        r = box(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        for tree, geoms in ((self.ts, self.tb), (self.ss, self.segs)):
            if tree is not None and any(geoms[int(i)].intersects(r) for i in tree.query(r)):
                return False
        if any(q.intersects(r) for q in self.rects + self.extra):
            return False
        return True

    def ok_line(self, a, b):
        """La línea de referencia no atraviesa textos ni otras indicaciones (sí puede cruzar líneas de cota o de contorno)."""
        from shapely.geometry import LineString
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6:
            return True
        ls = LineString([a, b])
        if self.ts is not None and any(self.tb[int(i)].intersects(ls) for i in self.ts.query(ls)):
            return False
        return not any(q.intersects(ls) for q in self.extra)

    def take(self, x0, y0, x1, y1):
        from shapely.geometry import box
        self.extra.append(box(x0, y0, x1, y1))
        if not hasattr(self.s, "reserved"):
            self.s.reserved = []
        self.s.reserved.append((x0, y0, x1, y1))


def _unit(d):
    n = math.hypot(d[0], d[1]) or 1.0
    return (d[0] / n, d[1] / n)


def _find_dim(s, prefix, near=None):
    best = None
    for m in getattr(s, "movable", []):
        if m.get("leader"):
            continue
        try:
            t = m["e"].dxf.text
        except Exception:
            continue
        if t.startswith(prefix):
            a, b = m["a"], m["b"]
            d = 0.0 if near is None else min(math.hypot(a[0] - near[0], a[1] - near[1]), math.hypot(b[0] - near[0], b[1] - near[1]))
            if best is None or d < best[0]:
                best = (d, a, b)
    return None if best is None else (best[1], best[2])


def _find_callout(s, prefix):
    for m in getattr(s, "movable", []):
        if not m.get("leader"):
            continue
        try:
            t = m["e"].dxf.text
        except Exception:
            continue
        if t.startswith(prefix):
            return m
    # llamadas de varias líneas: primer texto que empiece por el prefijo
    for e in s.m:
        if e.dxftype() == "TEXT" and e.dxf.text.startswith(prefix):
            return dict(e=e)
    return None


def _draw_frame(s, x, y, sym, tol, datum):
    return s.gdt((x, y), sym, tol, datum)


def _cand_leaders(tip, u, wF, hF):
    """Recorridos de línea de referencia: tramo 1 en la dirección u (normal a la superficie o prolongación de la línea de cota), tramo 2 opcional
    perpendicular, y el marco unido por un costado (izquierdo o derecho) con un trazo horizontal. Ordenados por largo total."""
    n = (-u[1], u[0])
    out = []
    for L1 in (6.0, 10.0, 16.0, 24.0, 34.0, 46.0, 60.0, 76.0):
        e1 = (tip[0] + u[0] * L1, tip[1] + u[1] * L1)
        for dv in (0.0, 8.0, -8.0, 14.0, -14.0, 22.0, -22.0, 32.0, -32.0, 44.0, -44.0):
            e2 = (e1[0] + n[0] * dv, e1[1] + n[1] * dv)
            last = u if dv == 0 else (n[0] * (1 if dv > 0 else -1), n[1] * (1 if dv > 0 else -1))
            for side in (1, -1):
                if abs(last[0]) > 0.7 and (last[0] > 0) != (side > 0):
                    continue
                stub = 0.0 if abs(last[0]) > 0.7 else 3.0
                e3 = (e2[0] + side * stub, e2[1])
                x = e3[0] if side > 0 else e3[0] - wF
                pts = [tip, e1] + ([e2] if dv else []) + ([e3] if stub else [])
                out.append((L1 + abs(dv) + stub, x, e3[1] - hF / 2, pts))
    out.sort(key=lambda c: c[0])
    return out


def fcf(s, L, mode, sym, tol, datum=None, a=None, d=None, prefix=None):
    """Marco de tolerancia en la vista. a/d pueden ser listas de alternativas (punto de papel, dirección). Devuelve True si encontró lugar."""
    wF = _frame_w(tol, datum)
    hF = FRAME_H
    if mode == "callout":
        m = _find_callout(s, prefix)
        if m is None:
            return False
        from ezdxf import bbox
        b = bbox.extents([m["e"]], fast=False)
        x0t, y0t, x1t = b.extmin.x, b.extmin.y, b.extmax.x
        cands = []
        for dy in (1.6, 6.0, 10.5, 15.0, 19.5):
            cands += [(x0t, y0t - dy - hF), (x1t - wF, y0t - dy - hF)]
        for dy in (1.2, 5.0):
            cands += [(x0t, b.extmax.y + dy), (x1t - wF, b.extmax.y + dy)]
        for (x, y) in cands:
            if L.ok_rect(x, y, x + wF, y + hF, pad=0.4):
                _draw_frame(s, x, y, sym, tol, datum)
                yl = y + hF if y < y0t else y
                yr = y0t + 0.2 if y < y0t else b.extmax.y
                s.line((x + 3.5, yl), (x + 3.5, yr), "COTA") if abs(yr - yl) > 0.8 else None
                L.take(x, y, x + wF, y + hF)
                return True
        return False
    if mode == "dim":
        r = _find_dim(s, prefix, near=a if not isinstance(a, list) else None)
        if r is None:
            return False
        p, q = r
        u = _unit((q[0] - p[0], q[1] - p[1]))
        tips = [(q, u), (p, (-u[0], -u[1]))]
    else:
        tips = list(zip(a, d)) if isinstance(a, list) else [(a, d)]
        tips = [(t, _unit(dd)) for t, dd in tips]
    best = None
    for k, (tip, u) in enumerate(tips):
        for cost, x, y, pts in _cand_leaders(tip, u, wF, hF):
            if best is not None and cost + 10 * k >= best[0]:
                break
            if L.ok_rect(x, y, x + wF, y + hF) and all(L.ok_line(p_, q_) for p_, q_ in zip(pts, pts[1:])):
                best = (cost + 10 * k, x, y, pts, u)
                break
    if best is None:
        return False
    _, x, y, pts, u = best
    _draw_frame(s, x, y, sym, tol, datum)
    s.pline(pts, "COTA")
    tip = pts[0]
    s.arrow(tip, math.atan2(tip[1] - pts[1][1], tip[0] - pts[1][0]))
    L.take(x, y, x + wF, y + hF)
    for p_, q_ in zip(pts, pts[1:]):
        L.take(min(p_[0], q_[0]) - 0.3, min(p_[1], q_[1]) - 0.3, max(p_[0], q_[0]) + 0.3, max(p_[1], q_[1]) + 0.3)
    return True


def datum(s, L, mode, letter, a=None, d=None, prefix=None):
    """Indicador de datum ISO 5459: triángulo lleno sobre la superficie (o sobre la prolongación de la línea de cota), trazo y recuadro con la letra."""
    if mode == "dim":
        r = _find_dim(s, prefix, near=a)
        if r is None:
            return False
        p, q = r
        u = _unit((q[0] - p[0], q[1] - p[1]))
        tips = [(q, u), (p, (-u[0], -u[1]))]
    else:
        tips = list(zip(a, d)) if isinstance(a, list) else [(a, d)]
        tips = [(t, _unit(dd)) for t, dd in tips]
    for tip, u in tips:
        for L1 in (8.0, 12.0, 18.0, 26.0, 36.0, 48.0, 62.0):
            n = (-u[1], u[0])
            tri = [(tip[0] + n[0] * 2.8, tip[1] + n[1] * 2.8), (tip[0] - n[0] * 2.8, tip[1] - n[1] * 2.8), (tip[0] + u[0] * 4.8, tip[1] + u[1] * 4.8)]
            c = (tip[0] + u[0] * (L1 + 3.5), tip[1] + u[1] * (L1 + 3.5))
            bx = (c[0] - 3.5, c[1] - 3.5, c[0] + 3.5, c[1] + 3.5)
            st0 = (tip[0] + u[0] * 4.8, tip[1] + u[1] * 4.8)
            st1 = (tip[0] + u[0] * L1, tip[1] + u[1] * L1)
            if L.ok_rect(*bx) and L.ok_line(st0, st1):
                s.pline(tri, "COTA", closed=True)
                s.hatch_poly(tri, solid=True)
                s.line(st0, st1, "COTA")
                s.rect(*bx, "COTA")
                s.text(letter, c, T_N, "MIDDLE_CENTER", bold=True)
                L.take(*bx)
                L.take(min(tip[0], st1[0]) - 2.8, min(tip[1], st1[1]) - 2.8, max(tip[0], st1[0]) + 2.8, max(tip[1], st1[1]) + 2.8)
                return True
    return False


def rugosidad(s, L, ra, a, d):
    """Símbolo ISO 1302 sobre una línea de referencia cuya flecha toca la superficie en a (d: dirección hacia afuera del material).
    La línea puede quebrarse una vez (tramo normal a la superficie y tramo vertical) para salir de agujeros y cortes estrechos."""
    if isinstance(a, list):
        return any(rugosidad(s, L, ra, a_, d_) for a_, d_ in zip(a, d))
    u = _unit(d)
    wS = 4.0 + 9.0 + tw(ra, T_N) + 1.0
    cands = []
    for L1 in (8.0, 13.0, 19.0, 26.0, 34.0, 44.0, 56.0, 4.0):
        e1 = (a[0] + u[0] * L1, a[1] + u[1] * L1)
        if abs(u[1]) > 0.7:                       # superficie horizontal: tramo normal corto y codo horizontal hacia un costado
            for dh in [0.0] + [v * sg_ for v in range(10, 160, 6) for sg_ in (1, -1)]:
                e2 = (e1[0] + dh, e1[1])
                for sg in ((1, -1) if dh >= 0 else (-1,)):
                    if dh and (sg > 0) != (dh > 0):
                        continue
                    cands.append((L1 + abs(dh) * 0.6, e1, e2, sg))
            continue
        for dv in [0.0] + [v * sg_ for v in range(10, 100, 5) for sg_ in (1, -1)]:
            e2 = (e1[0], e1[1] + dv)
            for sg in ((1, -1) if u[0] >= -0.2 else (-1, 1)):
                cands.append((L1 + abs(dv), e1, e2, sg))
    cands.sort(key=lambda c: c[0])
    for _, e1, e2, sg in cands:
        x0 = e2[0] if sg > 0 else e2[0] - wS - 4
        x1 = x0 + wS + 4
        if L.ok_rect(x0, e2[1] - 0.5, x1, e2[1] + 17.0, pad=0.5) and L.ok_line(a, e1) and L.ok_line(e1, e2):
            s.line(a, e1, "COTA")
            if e2 != e1:
                s.line(e1, e2, "COTA")
            s.arrow(a, math.atan2(-u[1], -u[0]))
            s.line((x0, e2[1]), (x1, e2[1]), "COTA")
            s.roughness((x0 + 4.0 if sg > 0 else x1 - wS, e2[1]), ra)
            L.take(x0, e2[1] - 0.5, x1, e2[1] + 17.0)
            for p_, q_ in ((a, e1), (e1, e2)):
                L.take(min(p_[0], q_[0]) - 0.3, min(p_[1], q_[1]) - 0.3, max(p_[0], q_[0]) + 0.3, max(p_[1], q_[1]) + 0.3)
            return True
    return False


def rugosidad_cota(s, L, ra, prefix):
    """ISO 1302, 7.3: símbolo de rugosidad junto a la cota del elemento (sobre la línea de cota o el rellano de la llamada, a continuación del texto)."""
    from ezdxf import bbox
    cands = []
    for m in getattr(s, "movable", []):
        try:
            t = m["e"].dxf.text
        except Exception:
            continue
        if t.startswith(prefix) and abs(m["a"][1] - m["b"][1]) < 0.01:
            cands.append((m["e"], m["a"][1], min(m["a"][0], m["b"][0]), max(m["a"][0], m["b"][0])))
    if not cands:
        for e in s.m:
            if e.dxftype() == "TEXT" and e.dxf.text.startswith(prefix) and abs(e.dxf.get("rotation", 0.0) or 0.0) < 0.5:
                b = bbox.extents([e], fast=False)
                cands.append((e, b.extmin.y - 0.6, b.extmin.x - 1.0, b.extmax.x + 1.0))
    wS = 4.0 + 9.0 + tw(ra, T_N) + 1.0
    for e, y, xa, xb in cands:
        b = bbox.extents([e], fast=False)
        for x0 in (b.extmax.x + 2.0, b.extmin.x - wS - 2.0, b.extmax.x + 8.0):
            if L.ok_rect(x0 + 0.6, y + 0.6, x0 + wS, y + 17.0, pad=0.2):
                s.roughness((x0 + 3.5, y), ra)
                if x0 + 3.5 > xb:                       # la línea de cota (o el rellano) se prolonga hasta el vértice del símbolo
                    s.line((xb, y), (x0 + 3.5 + 2.0, y), "COTA")
                elif x0 + 3.5 < xa:
                    s.line((x0 + 3.5 - 2.0, y), (xa, y), "COTA")
                L.take(x0, y, x0 + wS, y + 17.0)
                return True
    return False
