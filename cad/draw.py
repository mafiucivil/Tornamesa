"""Mini-librería de dibujo técnico sobre ezdxf (coordenadas de papel en mm, A1 841x594). Tomada de tt300/draw.py."""
import math
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

W, H = 841.0, 594.0
OVR = {}
TXT_STYLE = "STD"


def wrap(text, n):
    """Parte un texto en líneas de a lo más n caracteres, sin cortar palabras."""
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) > n and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w) if cur else w
    if cur:
        lines.append(cur)
    return lines or [""]


def new_doc():
    doc = ezdxf.new("R2018", units=4)
    doc.styles.add(TXT_STYLE, font="LiberationSans-Regular.ttf")
    doc.styles.add("STDB", font="LiberationSans-Bold.ttf")
    lt = doc.linetypes
    lt.add("OCULTO", pattern=[4.5, 3.0, -1.5], description="__ __ __")
    lt.add("EJE", pattern=[22.0, 14.0, -3.0, 2.0, -3.0], description="__ . __")
    lt.add("FANTASMA", pattern=[26.0, 14.0, -3.0, 2.0, -2.0, 2.0, -3.0], description="__ . . __")
    for name, lw, ltype in [("VIS", 50, "CONTINUOUS"), ("FINA", 18, "CONTINUOUS"), ("OCU", 25, "OCULTO"),
                            ("EJE", 18, "EJE"), ("COTA", 18, "CONTINUOUS"), ("TXT", 25, "CONTINUOUS"),
                            ("ACH", 13, "CONTINUOUS"), ("MARCO", 70, "CONTINUOUS"), ("FANT", 18, "FANTASMA"),
                            ("TRAT", 50, "EJE")]:   # TRAT: línea gruesa de trazo y punto (zona con tratamiento superficial, ISO 128)
        doc.layers.add(name, color=7, lineweight=lw, linetype=ltype)
    doc.header["$LTSCALE"] = 1.0
    doc.header["$PSLTSCALE"] = 0
    return doc


class Sheet:
    def __init__(self):
        self.doc = new_doc()
        self.m = self.doc.modelspace()

    # ---------- primitivas ----------
    def line(self, p1, p2, layer="VIS"):
        self.m.add_line(p1, p2, dxfattribs={"layer": layer})

    def pline(self, pts, layer="VIS", closed=False):
        self.m.add_lwpolyline(pts, close=closed, dxfattribs={"layer": layer})

    def rect(self, x0, y0, x1, y1, layer="VIS"):
        self.pline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, closed=True)

    def circle(self, c, r, layer="VIS"):
        self.m.add_circle(c, r, dxfattribs={"layer": layer})

    def arc(self, c, r, a0, a1, layer="VIS"):
        self.m.add_arc(c, r, a0, a1, dxfattribs={"layer": layer})

    def text(self, s, p, h=2.5, align="BOTTOM_LEFT", rot=0.0, layer="TXT", bold=False):
        t = self.m.add_text(s, height=h, rotation=rot,
                            dxfattribs={"layer": layer, "style": "STDB" if bold else TXT_STYLE})
        t.set_placement(p, align=TA[align])
        return t

    def mtext(self, lines, p, h=2.5, ls=1.6, bold_first=False, width=None):
        y = p[1]
        for i, s in enumerate(lines):
            self.text(s, (p[0], y), h, "TOP_LEFT", bold=(bold_first and i == 0))
            y -= h * ls
        return y

    def hatch_poly(self, outer, holes=(), scale=0.9, angle=0.0, pattern="ANSI31", solid=False):
        h = self.m.add_hatch(color=7, dxfattribs={"layer": "ACH"})
        if solid:
            h.set_solid_fill(color=7)
        else:
            h.set_pattern_fill(pattern, scale=scale, angle=angle)
        h.paths.add_polyline_path(outer, is_closed=True, flags=1)
        for hh in holes:
            h.paths.add_polyline_path(hh, is_closed=True, flags=16)

    def centerlines(self, c, r, ext=3.0):
        self.line((c[0] - r - ext, c[1]), (c[0] + r + ext, c[1]), "EJE")
        self.line((c[0], c[1] - r - ext), (c[0], c[1] + r + ext), "EJE")

    def cross(self, c, s=2.0):
        self.line((c[0] - s, c[1]), (c[0] + s, c[1]), "FINA")
        self.line((c[0], c[1] - s), (c[0], c[1] + s), "FINA")

    # ---------- acotado ----------
    def arrow(self, tip, ang, size=2.8, w=0.9):
        ca, sa = math.cos(ang), math.sin(ang)
        bx, by = tip[0] - size * ca, tip[1] - size * sa
        p1 = (bx - w * sa, by + w * ca)
        p2 = (bx + w * sa, by - w * ca)
        self.m.add_solid([tip, p1, p2], dxfattribs={"layer": "COTA"})

    def dim(self, p1, p2, off, txt, orient="h", h=2.5, txt_shift=0.0, outside=False):
        """Cota lineal. orient 'h' (mide dx), 'v' (mide dy), 'a' alineada. off: distancia firmada de la línea de cota."""
        x1, y1 = p1
        x2, y2 = p2
        if orient == "h":
            yd = (y1 if off >= 0 and y1 >= y2 else y2 if off >= 0 else min(y1, y2)) + off
            yd = max(y1, y2) + off if off >= 0 else min(y1, y2) + off
            a, b = (x1, yd), (x2, yd)
            for (px, py) in (p1, p2):
                s = 1.0 if yd > py else -1.0
                self.line((px, py + s * 1.0), (px, yd + s * 2.0), "COTA")
        elif orient == "v":
            xd = max(x1, x2) + off if off >= 0 else min(x1, x2) + off
            a, b = (xd, y1), (xd, y2)
            for (px, py) in (p1, p2):
                s = 1.0 if xd > px else -1.0
                self.line((px + s * 1.0, py), (xd + s * 2.0, py), "COTA")
        else:
            ang = math.atan2(y2 - y1, x2 - x1)
            nx, ny = -math.sin(ang) * off, math.cos(ang) * off
            a, b = (x1 + nx, y1 + ny), (x2 + nx, y2 + ny)
            for (px, py), q in ((p1, a), (p2, b)):
                self.line((px, py), (q[0] + nx / max(abs(off), 1e-9) * 2, q[1] + ny / max(abs(off), 1e-9) * 2), "COTA")
        self.line(a, b, "COTA")
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if outside or L < 7:
            self.arrow(a, ang); self.arrow(b, ang + math.pi)
            self.line(a, (a[0] - 5 * math.cos(ang), a[1] - 5 * math.sin(ang)), "COTA")
            self.line(b, (b[0] + 5 * math.cos(ang), b[1] + 5 * math.sin(ang)), "COTA")
        else:
            self.arrow(a, ang + math.pi); self.arrow(b, ang)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        deg = math.degrees(ang)
        if deg > 90.01 or deg < -89.99:
            deg += 180
        r = math.radians(deg)
        tx = mx - math.sin(r) * 1.0 + math.cos(r) * txt_shift
        ty = my + math.cos(r) * 1.0 + math.sin(r) * txt_shift
        self.text(txt, (tx, ty), h, "BOTTOM_CENTER", rot=deg)

    def dim_dia(self, c, r, ang_deg, txt, h=2.5, ext=8.0):
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        p1 = (c[0] + r * ca, c[1] + r * sa)
        p2 = (c[0] - r * ca, c[1] - r * sa)
        p3 = (c[0] + (r + ext) * ca, c[1] + (r + ext) * sa)
        self.line(p2, p3, "COTA")
        self.arrow(p1, a)
        self.arrow(p2, a + math.pi)
        sh = 1 if ca >= 0 else -1
        p4 = (p3[0] + sh * (len(txt) * h * 0.62 + 1), p3[1])
        self.line(p3, p4, "COTA")
        self.text(txt, (p3[0] + sh * 0.5, p3[1] + 0.8), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")

    def dim_rad(self, c, r, ang_deg, txt, h=2.5, ext=8.0):
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        p1 = (c[0] + r * ca, c[1] + r * sa)
        p3 = (c[0] + (r + ext) * ca, c[1] + (r + ext) * sa)
        self.line(c, p3, "COTA")
        self.arrow(p1, a)
        sh = 1 if ca >= 0 else -1
        p4 = (p3[0] + sh * (len(txt) * h * 0.62 + 1), p3[1])
        self.line(p3, p4, "COTA")
        self.text(txt, (p3[0] + sh * 0.5, p3[1] + 0.8), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")

    def leader(self, p, q, txt, h=2.5, dot=False, lines=None):
        """Flecha en p, codo en q, texto horizontal."""
        self.line(p, q, "COTA")
        if dot:
            self.m.add_circle(p, 0.6, dxfattribs={"layer": "COTA"})
            self.hatch_poly([(p[0] + 0.6 * math.cos(t / 8 * math.pi * 2), p[1] + 0.6 * math.sin(t / 8 * math.pi * 2)) for t in range(8)], solid=True)
        else:
            self.arrow(p, math.atan2(p[1] - q[1], p[0] - q[0]))
        sh = 1 if q[0] >= p[0] else -1
        txts = [txt] if lines is None else lines
        wmax = max(len(t) for t in txts) * h * 0.58 + 1
        self.line(q, (q[0] + sh * wmax, q[1]), "COTA")
        y = q[1] + 0.8
        for i, t in enumerate(txts):
            if i == 0:
                self.text(t, (q[0] + sh * 0.5, y), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")
            else:
                self.text(t, (q[0] + sh * 0.5, q[1] - 1.0 - (i - 1) * h * 1.5), h, "TOP_LEFT" if sh > 0 else "TOP_RIGHT")

    def balloon(self, p, q, n, r=4.5):
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        ux, uy = (q[0] - p[0]) / d, (q[1] - p[1]) / d
        self.line(p, (q[0] - ux * r, q[1] - uy * r), "COTA")
        self.m.add_circle(p, 0.7, dxfattribs={"layer": "COTA"})
        self.hatch_poly([(p[0] + 0.7 * math.cos(t / 10 * math.pi * 2), p[1] + 0.7 * math.sin(t / 10 * math.pi * 2)) for t in range(10)], solid=True)
        self.circle(q, r, "FINA")
        self.text(str(n), q, 3.2, "MIDDLE_CENTER", bold=True)

    def view_title(self, p, title, scale, h=4.0):
        self.text(title, p, h, "BOTTOM_CENTER", bold=True)
        w = len(title) * h * 0.62
        self.line((p[0] - w / 2, p[1] - 1.2), (p[0] + w / 2, p[1] - 1.2), "VIS")
        self.text(scale, (p[0], p[1] - 2.5), 2.8, "TOP_CENTER")

    def section_mark(self, p, ang_deg, label, length=8.0):
        """Flecha de corte en p, apuntando ang (dirección de mirada)."""
        a = math.radians(ang_deg)
        q = (p[0] + length * math.cos(a), p[1] + length * math.sin(a))
        self.line(p, q, "VIS")
        self.arrow(q, a, size=3.5, w=1.3)
        self.text(label, (q[0] + 3 * math.cos(a), q[1] + 3 * math.sin(a)), 5.0, "MIDDLE_CENTER", bold=True)

    def detail_circle(self, c, r, label):
        self.circle(c, r, "FANT")
        self.text(label, (c[0] + r * 0.72 + 2, c[1] + r * 0.72 + 2), 5.0, "BOTTOM_LEFT", bold=True)

    def finish(self, p, ra, h=2.5):
        """Símbolo de rugosidad (ISO 1302) con Ra."""
        x, y = p
        self.pline([(x - 2.2, y + 3.8), (x, y), (x + 4.4, y + 7.6), (x + 12, y + 7.6)], "COTA")
        self.line((x - 2.2, y + 3.8), (x + 2.2, y + 3.8), "COTA")
        self.text(ra, (x + 4.6, y + 8.2), h, "BOTTOM_LEFT")

    def weld(self, p, q, kind, size, other=False, all_round=False, note="", h=2.5):
        """Símbolo de soldadura AWS A2.4 simplificado. kind 'fillet' | 'cjp' | 'bevel'."""
        self.line(p, q, "COTA")
        self.arrow(p, math.atan2(p[1] - q[1], p[0] - q[0]))
        sh = 1 if q[0] >= p[0] else -1
        L = 26.0
        r = (q[0] + sh * L, q[1])
        self.line(q, r, "COTA")
        mx = q[0] + sh * L * 0.45
        ys = [-1] + ([1] if other else [])
        for side in ys:
            if kind == "fillet":
                self.pline([(mx - 2.2, q[1]), (mx - 2.2, q[1] + side * 4.4), (mx + 2.2, q[1])], "COTA")
            else:
                self.pline([(mx - 2.4, q[1] + side * 4.6), (mx, q[1]), (mx + 2.4, q[1] + side * 4.6)] if kind == "cjp"
                           else [(mx - 2.2, q[1]), (mx - 2.2, q[1] + side * 4.6), (mx + 2.4, q[1] + side * 4.6)], "COTA")
            self.text(size, (mx - sh * 4.0, q[1] + side * 2.6), h, ("MIDDLE_RIGHT" if sh > 0 else "MIDDLE_LEFT"))
        if all_round:
            self.circle(q, 1.6, "COTA")
        if note:
            self.pline([(r[0], r[1]), (r[0] + sh * 3, r[1] + 3), ], "COTA")
            self.pline([(r[0], r[1]), (r[0] + sh * 3, r[1] - 3), ], "COTA")
            self.text(note, (r[0] + sh * 4, r[1]), h, "MIDDLE_LEFT" if sh > 0 else "MIDDLE_RIGHT")

    def table(self, x0, y0, cols, rows, rh=6.0, h=2.3, header_h=None, bold_header=True):
        """cols: lista de (titulo, ancho, align). rows: lista de listas. Dibuja desde y0 hacia abajo. Retorna y final."""
        header_h = header_h or rh * 1.3
        widths = [c[1] for c in cols]
        Wt = sum(widths)
        y = y0
        allrows = [[c[0] for c in cols]] + rows
        for i, row in enumerate(allrows):
            rhh = header_h if i == 0 else rh
            self.line((x0, y), (x0 + Wt, y), "VIS" if i <= 1 else "FINA")
            x = x0
            for j, cell in enumerate(row):
                al = cols[j][2] if i else "C"
                if al == "C":
                    self.text(str(cell), (x + widths[j] / 2, y - rhh / 2), h, "MIDDLE_CENTER", bold=(i == 0 and bold_header))
                elif al == "R":
                    self.text(str(cell), (x + widths[j] - 1.2, y - rhh / 2), h, "MIDDLE_RIGHT")
                else:
                    self.text(str(cell), (x + 1.2, y - rhh / 2), h, "MIDDLE_LEFT", bold=(i == 0 and bold_header))
                x += widths[j]
            y -= rhh
        self.line((x0, y), (x0 + Wt, y), "VIS")
        x = x0
        for wv in widths + [0]:
            self.line((x, y0), (x, y), "FINA" if 0 < x - x0 < Wt else "VIS")
            x += wv
        return y

    # ---------- símbolos adicionales ----------
    def weld_iso(self, p, q, kind="fillet", size="z6", other=False, all_round=False, field=False, tail=(), h=2.2, L=34.0, sh=None):
        """Símbolo de soldadura ISO 2553: línea de flecha (p → q), línea de referencia continua con línea de identificación a trazos,
        símbolo en el lado de la flecha (bajo la línea de referencia) y, si other, también en el lado opuesto. tail: textos de la cola
        (proceso ISO 4063, nivel de calidad ISO 5817, WPS)."""
        self.line(p, q, "COTA")
        self.arrow(p, math.atan2(p[1] - q[1], p[0] - q[0]))
        sh = sh if sh in (1, -1) else (1 if q[0] >= p[0] else -1)       # sentido de la línea de referencia (por defecto, hacia donde apunta la flecha)
        r = (q[0] + sh * L, q[1])
        self.line(q, r, "COTA")
        self.line((q[0], q[1] + 0.9), (r[0], r[1] + 0.9), "OCU")           # línea de identificación (trazos)
        mx = q[0] + sh * L * 0.4
        sides = [-1] + ([1] if other else [])
        for side in sides:
            if kind == "fillet":
                self.pline([(mx - 2.2, q[1]), (mx - 2.2, q[1] + side * 4.4), (mx + 2.2, q[1])], "COTA", closed=True)
            elif kind == "cjp":
                self.pline([(mx - 2.4, q[1] + side * 4.6), (mx, q[1]), (mx + 2.4, q[1] + side * 4.6)], "COTA")
            else:
                self.pline([(mx - 2.2, q[1]), (mx - 2.2, q[1] + side * 4.6), (mx + 2.4, q[1] + side * 4.6)], "COTA")
            self.text(size, (mx - sh * 4.0, q[1] + side * 2.6), h, ("MIDDLE_RIGHT" if sh > 0 else "MIDDLE_LEFT"))
        if all_round:
            self.circle(q, 1.7, "COTA")
        if field:
            self.line(q, (q[0], q[1] + 5), "COTA"); self.pline([(q[0], q[1] + 5), (q[0] + sh * 3.5, q[1] + 4), (q[0], q[1] + 3)], "COTA", closed=True)
        if tail:
            self.line(r, (r[0] + sh * 3, r[1] + 3), "COTA"); self.line(r, (r[0] + sh * 3, r[1] - 3), "COTA")
            for i, t in enumerate(tail):
                self.text(t, (r[0] + sh * 4.5, r[1] + 2.0 - i * h * 1.35), h, "MIDDLE_LEFT" if sh > 0 else "MIDDLE_RIGHT")

    def datum(self, p, letter, up=True):
        """Referencia de tolerancia geométrica (triángulo + recuadro con letra), ISO 1101."""
        x, y = p
        d = 1 if up else -1
        self.pline([(x - 2.2, y), (x + 2.2, y), (x, y + d * 3.8)], "COTA", closed=True)
        self.line((x, y + d * 3.8), (x, y + d * 7))
        self.rect(x - 2.6, y + d * 7 if d > 0 else y + d * 12.2, x + 2.6, y + d * 12.2 if d > 0 else y + d * 7, "COTA")
        self.text(letter, (x, y + d * 9.6), 2.8, "MIDDLE_CENTER", bold=True)

    def gdt(self, p, sym, tol, datum=None, h=2.4, leader_to=None):
        """Recuadro de tolerancia geométrica ISO 1101. sym: 'flat','perp','par','coax','pos','cyl','run','circ'. p: esquina inferior izquierda."""
        x, y = p
        hh, ww = 6.0, 6.0
        wt = max(14.0, len(tol) * h * 0.62 + 4)
        wd = (ww if datum else 0)
        self.rect(x, y, x + ww + wt + wd, y + hh, "COTA")
        self.line((x + ww, y), (x + ww, y + hh), "COTA")
        self.line((x + ww + wt, y), (x + ww + wt, y + hh), "COTA") if datum else None
        cx, cy = x + ww / 2, y + hh / 2
        if sym == "flat":
            self.pline([(cx - 2.2, cy - 1), (cx + 1.2, cy - 1), (cx + 2.2, cy + 1), (cx - 1.2, cy + 1)], "COTA", closed=True)
        elif sym == "perp":
            self.line((cx - 2.2, cy - 1.8), (cx + 2.2, cy - 1.8), "COTA"); self.line((cx, cy - 1.8), (cx, cy + 2.2), "COTA")
        elif sym == "par":
            self.line((cx - 2.2, cy - 2), (cx + 0.6, cy + 2), "COTA"); self.line((cx - 0.6, cy - 2), (cx + 2.2, cy + 2), "COTA")
        elif sym in ("coax", "cyl"):
            self.circle((cx, cy), 1.3, "COTA"); self.circle((cx, cy), 2.3, "COTA")
        elif sym == "pos":
            self.circle((cx, cy), 2.2, "COTA"); self.line((cx - 3.2, cy), (cx + 3.2, cy), "COTA"); self.line((cx, cy - 3.2), (cx, cy + 3.2), "COTA")
        elif sym in ("run", "circ"):
            self.line((cx - 2, cy - 2), (cx + 2, cy + 2), "COTA"); self.arrow((cx + 2, cy + 2), math.pi / 4, 1.8, 0.7)
        self.text(tol, (x + ww + wt / 2, cy), h, "MIDDLE_CENTER")
        if datum:
            self.text(datum, (x + ww + wt + wd / 2, cy), h, "MIDDLE_CENTER")
        if leader_to is not None:
            self.line((x, cy), (x - 4, cy), "COTA"); self.line((x - 4, cy), leader_to, "COTA")
            self.arrow(leader_to, math.atan2(leader_to[1] - cy, leader_to[0] - x + 4))

    def notes_block(self, x, y, title, lines, h=2.2, wrap_chars=0, ls=1.55):
        """Bloque de notas con título en negrita; devuelve la y final."""
        self.text(title, (x, y), h + 0.8, "TOP_LEFT", bold=True)
        y -= (h + 0.8) * 1.7
        out = []
        for ln in lines:
            out.extend(wrap(ln, wrap_chars) if wrap_chars else [ln])
        for ln in out:
            self.text(ln, (x, y), h, "TOP_LEFT")
            y -= h * ls
        return y

    # ---------- formato normalizado ----------
    def frame(self, info):
        """Marco, banner de advertencia, tabla de revisiones y cajetín normalizado. info: dict con proj, titulo, plano, lamina, escala, formato,
        material, masa, trat, rev, fecha, revs (lista de (rev, fecha, descripción, dibujó, revisó, aprobó)), aviso (texto obligatorio),
        estado, generales."""
        self.rect(0, 0, W, H, "FINA")
        self.rect(20, 10, W - 10, H - 10, "MARCO")
        for i in range(1, 8):
            x = 20 + i * (W - 30) / 8
            self.line((x, H - 10), (x, H - 5), "FINA"); self.line((x, 10), (x, 5), "FINA")
        for i in range(8):
            self.text(str(i + 1), (20 + (i + 0.5) * (W - 30) / 8, H - 7.5), 2.5, "MIDDLE_CENTER")
        for i, L in enumerate("FEDCBA"):
            self.text(L, (15, 10 + (i + 0.5) * (H - 20) / 6), 2.5, "MIDDLE_CENTER")
        # banner de advertencia obligatoria (visible en la parte superior de toda lámina)
        by0 = H - 10 - 9.5
        self.rect(20, by0, W - 10, H - 10, "MARCO")
        self.text(info["aviso"], ((20 + W - 10) / 2, by0 + 4.75), 4.2 if len(info["aviso"]) < 130 else 3.6, "MIDDLE_CENTER", bold=True)
        # cajetín
        x0, x1, y0 = W - 10 - 180, W - 10, 10
        rows = [("estado", 10), ("proj", 14), ("tit", 12), ("mat", 10), ("fir", 10), ("esc", 10), ("pla", 10)]
        y = y0
        ys = {}
        for k, hh in reversed(rows):
            ys[k] = (y, y + hh)
            y += hh
        ytop = y
        self.rect(x0, y0, x1, ytop, "MARCO")
        for k, (a, b) in ys.items():
            self.line((x0, b), (x1, b), "FINA")

        def cell(k, cx, cw, lab, val, h=2.7, bold=False, wrapn=0):
            a, b = ys[k]
            xx = x0 + cx
            self.text(lab, (xx + 1.2, b - 1.0), 1.7, "TOP_LEFT")
            if wrapn:
                for i, ln in enumerate(wrap(val, wrapn)[:2]):
                    self.text(ln, (xx + 1.2, b - 4.2 - i * 3.0), h, "TOP_LEFT", bold=bold)
            else:
                self.text(val, (xx + cw / 2, a + (b - a) * 0.38), h, "MIDDLE_CENTER", bold=bold)
        a, b = ys["pla"]
        for xx in (70, 130):
            self.line((x0 + xx, a), (x0 + xx, b), "FINA")
        cell("pla", 0, 70, "PLANO N°", info["plano"], 3.4, True)
        cell("pla", 70, 60, "LÁMINA", info["lamina"], 3.0)
        cell("pla", 130, 50, "REVISIÓN", info["rev"], 3.4, True)
        a, b = ys["esc"]
        for xx in (70, 130):
            self.line((x0 + xx, a), (x0 + xx, b), "FINA")
        cell("esc", 0, 70, "ESCALA", info["escala"])
        cell("esc", 70, 60, "FECHA", info["fecha"])
        cell("esc", 130, 50, "FORMATO", info["formato"])
        a, b = ys["fir"]
        for xx in (60, 120):
            self.line((x0 + xx, a), (x0 + xx, b), "FINA")
        cell("fir", 0, 60, "DIBUJÓ", info.get("dibujo", "A DEFINIR"), 2.4)
        cell("fir", 60, 60, "REVISÓ", info.get("reviso", "A DEFINIR"), 2.4)
        cell("fir", 120, 60, "APROBÓ", info.get("aprobo", "A DEFINIR"), 2.4)
        a, b = ys["mat"]
        for xx in (95, 135):
            self.line((x0 + xx, a), (x0 + xx, b), "FINA")
        cell("mat", 0, 95, "MATERIAL", info["material"], 1.9, wrapn=58)
        cell("mat", 95, 40, "MASA", info["masa"], 2.4)
        cell("mat", 135, 45, "TRATAMIENTO", info["trat"], 1.7, wrapn=32)
        a, b = ys["tit"]
        self.text("TÍTULO", (x0 + 1.2, b - 1.0), 1.7, "TOP_LEFT")
        for i, ln in enumerate(wrap(info["titulo"], 62)[:2]):
            self.text(ln, (x0 + 2, b - 4.0 - i * 4.4), 3.3, "TOP_LEFT", bold=True)
        a, b = ys["proj"]
        self.text("PROYECTO", (x0 + 1.2, b - 1.0), 1.7, "TOP_LEFT")
        self.text(info["proj"], (x0 + 2, b - 4.0), 3.0, "TOP_LEFT", bold=True)
        for i, ln in enumerate(wrap(info["subproj"], 100)[:2]):
            self.text(ln, (x0 + 2, b - 8.2 - i * 2.8), 2.2, "TOP_LEFT")
        a, b = ys["estado"]
        self.text(info["estado"], ((x0 + x1) / 2, (a + b) / 2), 2.6, "MIDDLE_CENTER", bold=True)
        # tabla de revisiones sobre el cajetín
        rv = info["revs"]
        cols = [("REV", 10), ("FECHA", 20), ("DESCRIPCIÓN", 98), ("DIB.", 17), ("REV.", 17), ("APR.", 18)]
        yy = ytop + 1
        rhs = [max(6.0, 3.0 * len(wrap(r[2], 66)) + 2.0) for r in rv]
        hh = 5.0
        ytab = yy + hh + sum(rhs)
        self.rect(x0, yy, x1, ytab, "MARCO")
        # encabezado arriba
        self.line((x0, ytab - hh), (x1, ytab - hh), "FINA")
        xx = x0
        for (t, w_) in cols:
            self.text(t, (xx + w_ / 2, ytab - hh / 2), 2.0, "MIDDLE_CENTER", bold=True)
            xx += w_
            if xx < x1 - 0.1:
                self.line((xx, yy), (xx, ytab), "FINA")
        ycur = ytab - hh
        for r, rh in zip(rv, rhs):
            ycur -= rh
            self.line((x0, ycur), (x1, ycur), "FINA")
            xx = x0
            for j, (t, w_) in enumerate(cols):
                if j == 2:
                    for i, ln in enumerate(wrap(r[2], 66)):
                        self.text(ln, (xx + 1.0, ycur + rh - 2.2 - i * 3.0), 1.9, "TOP_LEFT")
                else:
                    self.text(str(r[j]), (xx + w_ / 2, ycur + rh / 2), 2.2, "MIDDLE_CENTER", bold=(j == 0))
                xx += w_
        self.text(info["generales"], (x0, ytab + 1.5), 2.0, "BOTTOM_LEFT")
        self.text("Cotas en mm salvo indicación. No medir sobre el plano.", (x0, ytab + 4.6), 2.0, "BOTTOM_LEFT")
        self.cajetin_top = ytab + 8

    # ---------- salida ----------
    def save(self, dxf_path, pdf_path=None):
        self.doc.saveas(dxf_path)
        if pdf_path:
            return render_pdf(self.doc, pdf_path)


def render_pdf(doc, pdf_path):
    from ezdxf.addons.drawing import Frontend, RenderContext, pymupdf, layout, config
    backend = pymupdf.PyMuPdfBackend()
    cfg = config.Configuration(color_policy=config.ColorPolicy.BLACK,
                               background_policy=config.BackgroundPolicy.WHITE,
                               lineweight_scaling=1.0,
                               min_lineweight=0.13)
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace(), finalize=True)
    page = layout.Page(W, H, layout.Units.mm, margins=layout.Margins.all(0))
    pdf = backend.get_pdf_bytes(page, settings=layout.Settings(fit_page=False, scale=1.0))
    open(pdf_path, "wb").write(pdf)
    return pdf_path
