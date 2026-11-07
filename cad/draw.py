"""Infraestructura de dibujo técnico sobre ezdxf (coordenadas de papel en mm; A1 841x594, A2 594x420, A3 420x297).

Normas: ISO 128 (tipos de línea, achurado), ISO 129 (acotado), ISO 1101 (GD&T), ISO 1302 (rugosidad), ISO 2553 (soldadura),
ISO 5457 (formatos, zonas, marcas de centro), ISO 5456-2 (método de proyección E), ISO 7200 (cajetín), ISO 3098 (letra).
Alturas de texto en el plot: normal 3,5 mm, tablas densas 3,0 mm, títulos 5 mm, mínimo absoluto 2,5 mm."""
import math
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from PIL import ImageFont

FORMATS = {"A1": (841.0, 594.0), "A2": (594.0, 420.0), "A3": (420.0, 297.0)}
W, H = FORMATS["A1"]          # alias histórico (A1)
TXT_STYLE = "STD"
T_N, T_S, T_T, T_MIN = 3.5, 3.0, 5.0, 2.5     # normal, tabla, título, mínimo (ISO 3098)
_FR = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 200)
_FB = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 200)


def tw(s, h, bold=False):
    """Ancho real (mm) de un texto de altura h (cap-height ~0,72 de la altura de fuente; se usa la altura de texto de ezdxf)."""
    return (_FB if bold else _FR).getlength(str(s)) / 200.0 * h / 0.688


def wrapw(text, width, h, bold=False):
    """Parte un texto en líneas que caben en 'width' mm (sin cortar palabras salvo que una palabra sola exceda el ancho)."""
    out = []
    for para in str(text).split("\n"):
        cur = ""
        for w_ in para.split():
            trial = (cur + " " + w_) if cur else w_
            if tw(trial, h, bold) <= width or not cur:
                cur = trial
            else:
                out.append(cur)
                cur = w_
        out.append(cur)
    # una palabra más ancha que la celda: se parte por caracteres
    res = []
    for ln in out:
        while tw(ln, h, bold) > width and len(ln) > 3:
            k = len(ln)
            while k > 1 and tw(ln[:k], h, bold) > width:
                k -= 1
            res.append(ln[:k])
            ln = ln[k:]
        res.append(ln)
    return res or [""]


def wrap(text, n):
    words, lines, cur = str(text).split(), [], ""
    for w_ in words:
        if len(cur) + len(w_) + (1 if cur else 0) > n and cur:
            lines.append(cur); cur = w_
        else:
            cur = (cur + " " + w_) if cur else w_
    if cur:
        lines.append(cur)
    return lines or [""]


def new_doc():
    doc = ezdxf.new("R2018", units=4)
    doc.styles.add(TXT_STYLE, font="LiberationSans-Regular.ttf")
    doc.styles.add("STDB", font="LiberationSans-Bold.ttf")
    lt = doc.linetypes
    lt.add("OCULTO", pattern=[6.0, 4.0, -2.0], description="__ __ __")
    lt.add("EJE", pattern=[30.0, 20.0, -4.0, 3.0, -4.0], description="__ . __")
    lt.add("FANTASMA", pattern=[30.0, 18.0, -4.0, 3.0, -3.0, 3.0, -4.0], description="__ . . __")
    # grosores ISO 128-20 (serie 0,25 / 0,35 / 0,5 / 0,7 / 1,0)
    for name, lw, ltype in [("VIS", 50, "CONTINUOUS"), ("FINA", 25, "CONTINUOUS"), ("OCU", 25, "OCULTO"),
                            ("EJE", 25, "EJE"), ("COTA", 25, "CONTINUOUS"), ("TXT", 25, "CONTINUOUS"),
                            ("ACH", 13, "CONTINUOUS"), ("MARCO", 70, "CONTINUOUS"), ("FANT", 25, "FANTASMA"),
                            ("TRAT", 50, "EJE"), ("CORTE", 70, "EJE")]:
        doc.layers.add(name, color=7, lineweight=lw, linetype=ltype)
    doc.header["$LTSCALE"] = 1.0
    doc.header["$PSLTSCALE"] = 0
    return doc


# patrones de achurado por material (ISO 128-50): (patrón, ángulo base, escala)
HATCH_MAT = {
    "acero": ("ANSI31", 0.0, 1.0),
    "inox": ("ANSI32", 0.0, 1.0),
    "bronce": ("ANSI33", 0.0, 1.0),
    "plastico": ("ANSI37", 0.0, 1.0),
    "madera": ("ANSI35", 0.0, 1.0),
    "grafito": ("SOLID", 0.0, 1.0),
    "otro": ("ANSI34", 0.0, 1.0),
}
HATCH_NAME = {"acero": "Acero al carbono / baja aleación", "inox": "Acero inoxidable", "bronce": "Bronce / aleación de cobre",
              "plastico": "UHMW-PE / plástico", "madera": "Madera", "grafito": "Grafito", "otro": "Otro material"}


class Sheet:
    def __init__(self, fmt="A1"):
        self.fmt = fmt
        self.W, self.H = FORMATS[fmt]
        self.doc = new_doc()
        self.m = self.doc.modelspace()
        self.texts = []
        self.nat = 0              # contador de entidades (diagnóstico)
        self.n_gdt = self.n_ra = self.n_weld = 0
        self.movable = []         # textos de cota y de llamada que el ordenador de textos puede deslizar a lo largo de su línea
        self.hatch_used = set()

    def reset(self):
        """Vacía la hoja (mismo objeto) para recomponerla: lo usa el compositor cuando una vista necesitó más líneas de cota que las previstas."""
        self.doc = new_doc()
        self.m = self.doc.modelspace()
        self.texts = []
        self.movable = []
        self.n_gdt = self.n_ra = self.n_weld = 0
        for k in ("views", "reserved", "footprints", "block_rects"):
            if hasattr(self, k):
                setattr(self, k, [])
        self.hatch_classes = set()

    def reformat(self, fmt):
        """Cambia el formato de una hoja aún vacía (el compositor elige A3/A2/A1 según el llenado)."""
        self.fmt = fmt
        self.W, self.H = FORMATS[fmt]

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

    def dot(self, p, r=0.8):
        self.m.add_circle(p, r, dxfattribs={"layer": "COTA"})
        self.hatch_poly([(p[0] + r * math.cos(t / 8 * math.pi * 2), p[1] + r * math.sin(t / 8 * math.pi * 2)) for t in range(8)], solid=True)

    def text(self, s, p, h=T_N, align="BOTTOM_LEFT", rot=0.0, layer="TXT", bold=False):
        h = max(h, T_MIN)
        s = str(s)
        self.texts.append(s)
        t = self.m.add_text(s, height=h, rotation=rot, dxfattribs={"layer": layer, "style": "STDB" if bold else TXT_STYLE})
        t.set_placement(p, align=TA[align])
        return t

    def mtext_w(self, text, p, width, h=T_N, ls=1.4, bold=False, align="TOP_LEFT"):
        """Párrafo con ajuste por ancho real; devuelve la y final."""
        y = p[1]
        for ln in wrapw(text, width, h, bold):
            self.text(ln, (p[0], y), h, align, bold=bold)
            y -= h * ls
        return y

    def hatch_poly(self, outer, holes=(), scale=1.0, angle=0.0, pattern="ANSI31", solid=False):
        h = self.m.add_hatch(color=7, dxfattribs={"layer": "ACH"})
        if solid or pattern == "SOLID":
            h.set_solid_fill(color=7)
        else:
            h.set_pattern_fill(pattern, scale=scale, angle=angle)
            self.hatch_used.add(pattern)
        h.paths.add_polyline_path(outer, is_closed=True, flags=1)
        for hh in holes:
            h.paths.add_polyline_path(hh, is_closed=True, flags=16)

    def centerlines(self, c, r, ext=4.0):
        self.line((c[0] - r - ext, c[1]), (c[0] + r + ext, c[1]), "EJE")
        self.line((c[0], c[1] - r - ext), (c[0], c[1] + r + ext), "EJE")

    def cross(self, c, s=2.5):
        self.line((c[0] - s, c[1]), (c[0] + s, c[1]), "FINA")
        self.line((c[0], c[1] - s), (c[0], c[1] + s), "FINA")

    # ---------- acotado (ISO 129) ----------
    def arrow(self, tip, ang, size=3.0, w=0.9):
        ca, sa = math.cos(ang), math.sin(ang)
        bx, by = tip[0] - size * ca, tip[1] - size * sa
        self.m.add_solid([tip, (bx - w * sa, by + w * ca), (bx + w * sa, by - w * ca)], dxfattribs={"layer": "COTA"})

    def dim(self, p1, p2, off, txt, orient="h", h=T_N, txt_shift=0.0, outside=False):
        """Cota lineal. orient 'h' (mide dx), 'v' (mide dy), 'a' alineada. off: distancia firmada de la línea de cota (papel)."""
        x1, y1 = p1
        x2, y2 = p2
        if orient == "h":
            yd = max(y1, y2) + off if off >= 0 else min(y1, y2) + off
            a, b = (x1, yd), (x2, yd)
            for (px, py) in (p1, p2):
                s = 1.0 if yd > py else -1.0
                self.line((px, py + s * 1.5), (px, yd + s * 2.5), "COTA")
        elif orient == "v":
            xd = max(x1, x2) + off if off >= 0 else min(x1, x2) + off
            a, b = (xd, y1), (xd, y2)
            for (px, py) in (p1, p2):
                s = 1.0 if xd > px else -1.0
                self.line((px + s * 1.5, py), (xd + s * 2.5, py), "COTA")
        else:
            ang = math.atan2(y2 - y1, x2 - x1)
            nx, ny = -math.sin(ang) * off, math.cos(ang) * off
            a, b = (x1 + nx, y1 + ny), (x2 + nx, y2 + ny)
            n = max(abs(off), 1e-9)
            for (px, py), q in ((p1, a), (p2, b)):
                self.line((px + nx / n * 1.5, py + ny / n * 1.5), (q[0] + nx / n * 2.5, q[1] + ny / n * 2.5), "COTA")
        self.line(a, b, "COTA")
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        wtxt = tw(txt, h)
        deg = math.degrees(ang)
        if deg > 90.01 or deg < -89.99:
            deg += 180
        r = math.radians(deg)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if L < 8.5 or outside:           # flechas por fuera
            self.arrow(a, ang); self.arrow(b, ang + math.pi)
            self.line(a, (a[0] - 5 * math.cos(ang), a[1] - 5 * math.sin(ang)), "COTA")
            self.line(b, (b[0] + 5 * math.cos(ang), b[1] + 5 * math.sin(ang)), "COTA")
            if wtxt + 2 > L:             # texto fuera, a continuación del extremo b
                d = 6 + wtxt / 2
                ux, uy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
                sgn = 1 if (b[0] - a[0]) * ux + (b[1] - a[1]) * uy >= 0 else -1
                mx, my = b[0] + sgn * ux * d, b[1] + sgn * uy * d
        else:
            self.arrow(a, ang + math.pi); self.arrow(b, ang)
            if wtxt + 7 > L:             # no cabe entre flechas: texto fuera
                d = 4 + wtxt / 2
                ux, uy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
                mx, my = b[0] + ux * d, b[1] + uy * d
        tx = mx - math.sin(r) * 1.0 + math.cos(r) * txt_shift
        ty = my + math.cos(r) * 1.0 + math.sin(r) * txt_shift
        t_ = self.text(txt, (tx, ty), h, "BOTTOM_CENTER", rot=deg)
        self.movable.append(dict(e=t_, base=(tx, ty), deg=deg, a=a, b=b, align="BOTTOM_CENTER"))

    def dim_dia(self, c, r, ang_deg, txt, h=T_N, ext=10.0):
        """Cota de diámetro con línea de cota por el centro y texto en el extremo (r en papel)."""
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        p1 = (c[0] + r * ca, c[1] + r * sa)
        p2 = (c[0] - r * ca, c[1] - r * sa)
        p3 = (c[0] + (r + ext) * ca, c[1] + (r + ext) * sa)
        self.line(p2, p3, "COTA")
        self.arrow(p1, a)
        self.arrow(p2, a + math.pi)
        self._tail_text(p3, txt, ca, h)

    def dim_rad(self, c, r, ang_deg, txt, h=T_N, ext=10.0):
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        p1 = (c[0] + r * ca, c[1] + r * sa)
        p3 = (c[0] + (r + ext) * ca, c[1] + (r + ext) * sa)
        self.line(c, p3, "COTA")
        self.arrow(p1, a)
        self._tail_text(p3, txt, ca, h)

    def _tail_text(self, p3, txt, ca, h):
        sh = 1 if ca >= 0 else -1
        self.line(p3, (p3[0] + sh * (tw(txt, h) + 2), p3[1]), "COTA")
        self.text(txt, (p3[0] + sh * 1.0, p3[1] + 0.9), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")

    def dim_ang(self, c, r, a0, a1, txt, h=T_N):
        """Cota angular: arco de radio r (papel) entre a0 y a1 (grados) con flechas y texto en el punto medio."""
        self.arc(c, r, min(a0, a1), max(a0, a1), "COTA")
        for ang, sgn in ((a0, -1 if a1 > a0 else 1), (a1, 1 if a1 > a0 else -1)):
            tip = (c[0] + r * math.cos(math.radians(ang)), c[1] + r * math.sin(math.radians(ang)))
            self.arrow(tip, math.radians(ang) + sgn * math.pi / 2)
        am = math.radians((a0 + a1) / 2)
        self.text(txt, (c[0] + (r + 2) * math.cos(am), c[1] + (r + 2) * math.sin(am)), h, "BOTTOM_LEFT" if math.cos(am) >= 0 else "BOTTOM_RIGHT")

    def leader(self, p, q, txt, h=T_N, dot=False, lines=None):
        """Línea de referencia: flecha (o punto) en p, codo en q, texto horizontal (varias líneas opcionales)."""
        self.line(p, q, "COTA")
        if dot:
            self.dot(p, 0.8)
        else:
            self.arrow(p, math.atan2(p[1] - q[1], p[0] - q[0]))
        sh = 1 if q[0] >= p[0] else -1
        txts = [txt] if lines is None else lines
        wmax = max(tw(t, h) for t in txts) + 2
        self.line(q, (q[0] + sh * wmax, q[1]), "COTA")
        for i, t in enumerate(txts):
            if i == 0:
                t0_ = self.text(t, (q[0] + sh * 1.0, q[1] + 0.9), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")
                if len(txts) == 1:
                    self.movable.append(dict(e=t0_, base=(q[0] + sh * 1.0, q[1] + 0.9), deg=0.0, a=q, b=(q[0] + sh * wmax, q[1]), align="BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT", leader=True))
            else:
                self.text(t, (q[0] + sh * 1.0, q[1] - 1.0 - (i - 1) * h * 1.4), h, "TOP_LEFT" if sh > 0 else "TOP_RIGHT")
        if not hasattr(self, "reserved"):
            self.reserved = []
        wmax_ = max(tw(t, h) for t in txts) + 2
        xa, xb = (q[0], q[0] + sh * wmax_) if sh > 0 else (q[0] + sh * wmax_, q[0])
        self.reserved.append((min(xa, p[0]), min(q[1] - h * 1.4 * len(txts), p[1]), max(xb, p[0]), max(q[1] + h * 1.5, p[1])))

    def balloon(self, p, q, n, r=5.0):
        """Globo de posición: círculo r en q, línea guía a p (punto en la pieza)."""
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        if d < 1e-6:
            return
        ux, uy = (q[0] - p[0]) / d, (q[1] - p[1]) / d
        self.line(p, (q[0] - ux * r, q[1] - uy * r), "COTA")
        self.dot(p, 0.8)
        self.circle(q, r, "FINA")
        s = str(n)
        self.text(s, q, T_N if len(s) < 3 else 3.0, "MIDDLE_CENTER", bold=True)

    def view_title(self, p, title, scale, h=T_T):
        self.text(title, p, h, "BOTTOM_CENTER", bold=True)
        w_ = tw(title, h, True)
        self.line((p[0] - w_ / 2, p[1] - 1.4), (p[0] + w_ / 2, p[1] - 1.4), "VIS")
        self.text(scale, (p[0], p[1] - 2.8), T_N, "TOP_CENTER")

    def section_mark(self, p, ang_deg, label, length=10.0):
        a = math.radians(ang_deg)
        q = (p[0] + length * math.cos(a), p[1] + length * math.sin(a))
        self.line(p, q, "VIS")
        self.arrow(q, a, size=4.0, w=1.4)
        self.text(label, (q[0] + 4 * math.cos(a), q[1] + 4 * math.sin(a)), T_T, "MIDDLE_CENTER", bold=True)

    def cut_line(self, p1, p2, label, look_deg, ext=14.0):
        """Plano de corte ISO 128-40: trazos gruesos en los extremos, línea fina de trazo y punto entre ellos, flechas hacia la dirección de mirada y letra."""
        L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        ux, uy = (p2[0] - p1[0]) / L, (p2[1] - p1[1]) / L
        end = min(12.0, L / 4)
        self.line(p1, (p1[0] + ux * end, p1[1] + uy * end), "CORTE"); self.line(p2, (p2[0] - ux * end, p2[1] - uy * end), "CORTE")
        self.line((p1[0] + ux * end, p1[1] + uy * end), (p2[0] - ux * end, p2[1] - uy * end), "EJE")
        a = math.radians(look_deg)
        for pt in (p1, p2):
            q = (pt[0] + 9 * math.cos(a), pt[1] + 9 * math.sin(a))
            self.line(pt, q, "VIS"); self.arrow(q, a, size=4.0, w=1.4)
            self.text(label, (q[0] + 5 * math.cos(a) - ux * 0, q[1] + 5 * math.sin(a)), T_T, "MIDDLE_CENTER", bold=True)

    def detail_circle(self, c, r, label, esc=""):
        self.circle(c, r, "FANT")
        ang = math.radians(45)
        q = (c[0] + (r + 4) * math.cos(ang), c[1] + (r + 4) * math.sin(ang))
        self.line((c[0] + r * math.cos(ang), c[1] + r * math.sin(ang)), (q[0] - 2, q[1] - 2), "FANT")
        self.text(label, q, T_T, "MIDDLE_CENTER", bold=True)

    def roughness(self, p, ra, h=T_N, mach=True, note=""):
        self.n_ra += 1
        """Símbolo de rugosidad ISO 1302 (remoción de material obligatoria, triángulo cerrado) con Ra en µm. p: vértice inferior."""
        x, y = p
        self.pline([(x - 3.5, y + 6.1), (x, y), (x + 3.5, y + 6.1)], "COTA")
        self.pline([(x + 3.5, y + 6.1), (x + 7.0, y + 12.2), (x + 7.0 + tw(ra, h) + 2.0, y + 12.2)], "COTA")
        self.line((x - 3.5, y + 6.1), (x + 7.0, y + 12.2), "COTA") if False else None
        self.text(ra, (x + 8.0, y + 12.9), h, "BOTTOM_LEFT")
        if note:
            self.text(note, (x + 8.0 + tw(ra, h) + 4, y + 12.9), h, "BOTTOM_LEFT")

    finish = roughness

    # ---------- soldadura ISO 2553 ----------
    def weld(self, p, q, kind="fillet", size="", length="", other=None, all_round=False, field=False, tail=(), L=None, sh=None, h=T_N, prep="", flip=False):
        """Símbolo ISO 2553 completo. p: punta de flecha sobre la junta; q: inicio de la línea de referencia (horizontal).
        kind del lado flecha: fillet|V|bevel|J|U|slot|plug|square|none; other: dict(kind,size,length) del otro lado (o None).
        size: texto antes del símbolo (a5, z7, s12); length: texto después (×200, 3×100(150)); prep: ángulo/abertura (60°, r3).
        all_round: soldadura en todo el contorno; field: soldadura en obra; tail: líneas del rabo (proceso, nivel, WPS, END)."""
        self.n_weld += 1
        self.line(p, q, "COTA")
        self.arrow(p, math.atan2(p[1] - q[1], p[0] - q[0]))
        sh = sh if sh in (1, -1) else (1 if q[0] >= p[0] else -1)
        texts_w = [tw(t, T_N) for t in ([size, length, prep] if True else [])]
        wl = max(34.0, 8 + sum(texts_w) + 12) if L is None else L
        r_ = (q[0] + sh * wl, q[1])
        self.line(q, r_, "COTA")
        self.line((q[0], q[1] + 1.6), (r_[0], r_[1] + 1.6), "OCU")          # línea de identificación (trazos): lado opuesto
        x_sym = q[0] + sh * (8 + tw(size, h) + 3.5)

        def sym(kd, y0, sd, sz, ln, pr, x_s):
            """sd = -1 abajo (lado flecha), +1 arriba (otro lado)."""
            if kd == "fillet":
                pts = [(x_s, y0), (x_s, y0 + sd * 5.0), (x_s + sh * 5.0, y0)]
                self.pline(pts, "COTA", closed=True)
            elif kd == "V":
                self.pline([(x_s - 2.8, y0 + sd * 5.0), (x_s, y0), (x_s + 2.8, y0 + sd * 5.0)], "COTA")
            elif kd == "bevel":
                self.pline([(x_s, y0), (x_s, y0 + sd * 5.0)], "COTA"); self.line((x_s, y0), (x_s + sh * 4.5, y0 + sd * 5.0), "COTA")
            elif kd == "J":
                self.pline([(x_s, y0), (x_s, y0 + sd * 5.0)], "COTA"); self.arc((x_s + sh * 2.5, y0 + sd * 2.5), 2.5, 180 if sh > 0 else 270, 270 if sh > 0 else 360, "COTA") if False else self.line((x_s, y0), (x_s + sh * 4.5, y0 + sd * 5.0), "COTA")
            elif kd == "U":
                self.pline([(x_s - 2.8, y0 + sd * 5.0), (x_s - 2.8, y0 + sd * 2.0), (x_s, y0), (x_s + 2.8, y0 + sd * 2.0), (x_s + 2.8, y0 + sd * 5.0)], "COTA")
            elif kd == "square":
                self.line((x_s - 1.0, y0), (x_s - 1.0, y0 + sd * 5.0), "COTA"); self.line((x_s + 1.0, y0), (x_s + 1.0, y0 + sd * 5.0), "COTA")
            elif kd in ("slot", "plug"):
                self.rect(x_s - 3.0, min(y0, y0 + sd * 4.5), x_s + 3.0, max(y0, y0 + sd * 4.5), "COTA")
            if sz:
                self.text(sz, (x_s - sh * 2.5 if kd != "V" else x_s - sh * 4.5, y0 + sd * 2.6), h, "MIDDLE_RIGHT" if sh > 0 else "MIDDLE_LEFT")
            if ln:
                self.text(ln, (x_s + sh * 7.0, y0 + sd * 2.6), h, "MIDDLE_LEFT" if sh > 0 else "MIDDLE_RIGHT")
            if pr:
                self.text(pr, (x_s + sh * 0.0, y0 + sd * 8.8), h, "MIDDLE_CENTER")

        if kind != "none":
            sym(kind, q[1], -1, size, length, prep, x_sym)
        if other:
            sym(other.get("kind", "fillet"), q[1] + 1.6, 1, other.get("size", ""), other.get("length", ""), other.get("prep", ""),
                q[0] + sh * (8 + tw(other.get("size", ""), h) + 3.5))
        if all_round:
            self.circle(q, 2.6, "COTA")
        if field:
            self.line(q, (q[0], q[1] + 8), "COTA")
            self.pline([(q[0], q[1] + 8), (q[0] + sh * 5.5, q[1] + 6.5), (q[0], q[1] + 5)], "COTA", closed=True)
            self.hatch_poly([(q[0], q[1] + 8), (q[0] + sh * 5.5, q[1] + 6.5), (q[0], q[1] + 5)], solid=True)
        if tail:
            tx = r_[0]
            self.line(r_, (tx + sh * 4, r_[1] + 4.5), "COTA"); self.line(r_, (tx + sh * 4, r_[1] - 4.5), "COTA")
            n = len(tail)
            tw_ = max(tw(t, T_S) for t in tail) + 3
            ytop = r_[1] + 4.5
            for i, t in enumerate(tail):
                self.text(t, (tx + sh * 5.5, ytop - i * (T_S * 1.35) - 0.5), T_S, "TOP_LEFT" if sh > 0 else "TOP_RIGHT")
        return r_

    # ---------- GD&T ISO 1101 ----------
    def datum(self, p, letter, up=True):
        x, y = p
        d = 1 if up else -1
        self.pline([(x - 2.8, y), (x + 2.8, y), (x, y + d * 4.8)], "COTA", closed=True)
        self.hatch_poly([(x - 2.8, y), (x + 2.8, y), (x, y + d * 4.8)], solid=True)
        self.line((x, y + d * 4.8), (x, y + d * 8))
        y0, y1 = (y + d * 8, y + d * 15) if d > 0 else (y + d * 15, y + d * 8)
        self.rect(x - 3.5, y0, x + 3.5, y1, "COTA")
        self.text(letter, (x, (y0 + y1) / 2), T_N, "MIDDLE_CENTER", bold=True)

    def gdt(self, p, sym, tol, datum=None, h=T_N, leader_to=None, leader_from="left"):
        """Recuadro ISO 1101. sym: flat, perp, par, coax, pos, cyl, run, circ, straight, prof. p: esquina inferior izquierda."""
        self.n_gdt += 1
        x, y = p
        hh, ww = 7.0, 7.0
        parts = [tol] + ([d_ for d_ in (datum if isinstance(datum, (list, tuple)) else [datum])] if datum else [])
        wt = max(14.0, tw(tol, h) + 5)
        wds = [7.0 for _ in parts[1:]]
        tot = ww + wt + sum(wds)
        self.rect(x, y, x + tot, y + hh, "COTA")
        self.line((x + ww, y), (x + ww, y + hh), "COTA")
        xx = x + ww + wt
        for wd in wds:
            self.line((xx, y), (xx, y + hh), "COTA"); xx += wd
        cx, cy = x + ww / 2, y + hh / 2
        if sym == "flat":
            self.pline([(cx - 2.6, cy - 1.2), (cx + 1.4, cy - 1.2), (cx + 2.6, cy + 1.2), (cx - 1.4, cy + 1.2)], "COTA", closed=True)
        elif sym == "perp":
            self.line((cx - 2.6, cy - 2.2), (cx + 2.6, cy - 2.2), "COTA"); self.line((cx, cy - 2.2), (cx, cy + 2.6), "COTA")
        elif sym == "par":
            self.line((cx - 2.6, cy - 2.4), (cx + 0.8, cy + 2.4), "COTA"); self.line((cx - 0.8, cy - 2.4), (cx + 2.6, cy + 2.4), "COTA")
        elif sym in ("coax", "cyl"):
            self.circle((cx, cy), 1.5, "COTA"); self.circle((cx, cy), 2.7, "COTA")
        elif sym == "pos":
            self.circle((cx, cy), 2.6, "COTA"); self.line((cx - 3.6, cy), (cx + 3.6, cy), "COTA"); self.line((cx, cy - 3.6), (cx, cy + 3.6), "COTA")
        elif sym in ("run", "circ"):
            self.line((cx - 2.4, cy - 2.4), (cx + 2.4, cy + 2.4), "COTA"); self.arrow((cx + 2.4, cy + 2.4), math.pi / 4, 2.2, 0.8)
        elif sym == "straight":
            self.line((cx - 2.6, cy), (cx + 2.6, cy), "COTA")
        elif sym == "prof":
            self.arc((cx, cy - 1.0), 2.6, 0, 180, "COTA")
        self.text(tol, (x + ww + wt / 2, cy), h, "MIDDLE_CENTER")
        xx = x + ww + wt
        for d_, wd in zip(parts[1:], wds):
            self.text(d_, (xx + wd / 2, cy), h, "MIDDLE_CENTER"); xx += wd
        if leader_to is not None:
            fx = x if leader_from == "left" else x + tot
            self.line((fx, cy), (leader_to[0], cy), "COTA") if False else None
            self.line((fx, cy), leader_to, "COTA")
            self.arrow(leader_to, math.atan2(leader_to[1] - cy, leader_to[0] - fx))
        return tot

    # ---------- bloques de texto y tablas ----------
    def notes_block(self, x, y, title, lines, h=T_N, width=200.0, ls=1.4, numbered=False):
        """Bloque de notas con título en negrita; cada nota se ajusta al ancho real. Devuelve la y final."""
        self.text(title, (x, y), T_N + 0.5, "TOP_LEFT", bold=True)
        y -= (T_N + 0.5) * 1.6
        for i, ln in enumerate(lines):
            txt = f"{i + 1}. {ln}" if numbered else ln
            wl = wrapw(txt, width, h)
            for j, l_ in enumerate(wl):
                self.text(l_ if j == 0 else "    " + l_ if numbered else l_, (x, y), h, "TOP_LEFT")
                y -= h * ls
            y -= h * 0.25
        return y

    def table(self, x0, y0, cols, rows, h=T_S, pad=1.3, header_h=None, ymin=None, bold_rows=(), title=None):
        """Tabla con celdas multilínea (ancho real). cols: [(titulo, ancho, alineación L|C|R)]. rows: listas de str.
        Devuelve (y_final, filas_no_dibujadas) — si se pasa ymin, corta antes de sobrepasarlo."""
        widths = [c[1] for c in cols]
        Wt = sum(widths)
        y = y0
        if title:
            for tl in wrapw(title, max(Wt, 60.0) - 2, T_N + 0.5, True):
                self.text(tl, (x0, y), T_N + 0.5, "TOP_LEFT", bold=True)
                y -= (T_N + 0.5) * 1.5
            y -= 0.5
        hl = max(len(wrapw(c[0], c[1] - 2 * pad, h, True)) for c in cols)
        hh = header_h or hl * h * 1.4 + 2 * pad
        ytop = y
        self.rect(x0, y - hh, x0 + Wt, y, "VIS")
        x = x0
        for (t, w_, al) in cols:
            for i, ln in enumerate(wrapw(t, w_ - 2 * pad, h, True)):
                self.text(ln, (x + w_ / 2, y - pad - h * 0.5 - i * h * 1.4), h, "MIDDLE_CENTER", bold=True)
            x += w_
        y -= hh
        left = []
        for ri, row in enumerate(rows):
            cells = [wrapw(c, w_ - 2 * pad, h, ri in bold_rows) for c, w_ in zip(row, widths)]
            n = max(len(c) for c in cells)
            rh = n * h * 1.4 + 2 * pad
            if ymin is not None and y - rh < ymin:
                left = rows[ri:]
                break
            x = x0
            self.line((x0, y), (x0 + Wt, y), "FINA")
            for lines, (t, w_, al) in zip(cells, cols):
                for i, ln in enumerate(lines):
                    yy = y - pad - h * 0.5 - i * h * 1.4
                    if al == "C":
                        self.text(ln, (x + w_ / 2, yy), h, "MIDDLE_CENTER", bold=ri in bold_rows)
                    elif al == "R":
                        self.text(ln, (x + w_ - pad, yy), h, "MIDDLE_RIGHT", bold=ri in bold_rows)
                    else:
                        self.text(ln, (x + pad, yy), h, "MIDDLE_LEFT", bold=ri in bold_rows)
                x += w_
            y -= rh
        self.line((x0, y), (x0 + Wt, y), "VIS")
        x = x0
        for w_ in widths + [0]:
            self.line((x, ytop), (x, y), "FINA" if 0 < x - x0 < Wt else "VIS")
            x += w_
        if not hasattr(self, "reserved"):
            self.reserved = []
        self.reserved.append((x0, y, x0 + Wt, y0 + 2))
        return y, left

    # ---------- formato normalizado (ISO 5457 / ISO 7200) ----------
    def block_top(self, revs):
        """Cota y superior del conjunto cajetín + revisiones + notas generales (para planificar el layout antes de dibujar el marco)."""
        rhs = [max(9.0, 4.3 * len(wrapw(r[2], 76, 3.0)) + 3.0) for r in revs]
        return 10 + 116 + 1.0 + 6.5 + sum(rhs) + 2.5 + 4.3 * 4 + 2

    def regions(self, revs):
        """Regiones útiles: main (todo el ancho sobre el cajetín) y low (franja inferior izquierda junto al cajetín); (x0,y0,x1,y1)."""
        yb = self.block_top(revs)
        top = self.H - 10 - 11 - 5
        return dict(main=(25.0, yb + 3, self.W - 15, top), low=(25.0, 15.0, self.W - 10 - 180 - 5, yb), right=(self.W - 10 - 180, yb + 3, self.W - 15, top),
                    left=(25.0, yb + 3, self.W - 10 - 180 - 5, top), all=(25.0, 15.0, self.W - 15, top))

    def projection_symbol(self, c, k=1.0):
        """Símbolo del método de proyección E (primer diedro, ISO 5456-2): tronco de cono (vista de frente) a la izquierda y sus círculos a la derecha."""
        x, y = c
        s = k
        self.pline([(x, y - 6 * s), (x + 11 * s, y - 3.5 * s), (x + 11 * s, y + 3.5 * s), (x, y + 6 * s)], "FINA", closed=True)
        self.line((x - 3 * s, y), (x + 14 * s, y), "EJE")
        cx = x + 24 * s
        self.circle((cx, y), 6 * s, "FINA"); self.circle((cx, y), 3.5 * s, "FINA")
        self.line((cx - 9 * s, y), (cx + 9 * s, y), "EJE"); self.line((cx, y - 9 * s), (cx, y + 9 * s), "EJE")

    def frame(self, info):
        """Marco, zonas, marcas de centro, banda de advertencia, cajetín ISO 7200, tabla de revisiones. Guarda self.free (esquina superior del cajetín) y self.area."""
        W, H = self.W, self.H
        self.rect(0, 0, W, H, "FINA")
        L, B, R_, T = 20, 10, W - 10, H - 10
        self.rect(L, B, R_, T, "MARCO")
        # zonas de ~50 mm (ISO 5457): números arriba/abajo, letras a izquierda/derecha
        nx, ny = max(4, round((R_ - L) / 50.0)), max(3, round((T - B) / 50.0))
        for i in range(1, nx):
            x = L + i * (R_ - L) / nx
            self.line((x, T), (x, T + 5), "FINA"); self.line((x, B), (x, B - 5), "FINA")
        for i in range(1, ny):
            y = B + i * (T - B) / ny
            self.line((L, y), (L - 5, y), "FINA"); self.line((R_, y), (R_ + 5, y), "FINA")
        for i in range(nx):
            x = L + (i + 0.5) * (R_ - L) / nx
            self.text(str(i + 1), (x, T + 2.6), T_MIN, "MIDDLE_CENTER"); self.text(str(i + 1), (x, B - 2.6), T_MIN, "MIDDLE_CENTER")
        for i in range(ny):
            y = B + (i + 0.5) * (T - B) / ny
            lab = chr(ord("A") + ny - 1 - i)
            self.text(lab, (L - 2.6, y), T_MIN, "MIDDLE_CENTER"); self.text(lab, (R_ + 2.6, y), T_MIN, "MIDDLE_CENTER")
        # marcas de centro
        mx, my = (L + R_) / 2, (B + T) / 2
        for (a, b) in (((mx, B - 5), (mx, B + 10)), ((mx, T + 5), (mx, T - 10)), ((L - 5, my), (L + 10, my)), ((R_ + 5, my), (R_ - 10, my))):
            self.line(a, b, "MARCO")
        # banda de advertencia obligatoria (arriba)
        by0 = T - 11.0
        self.rect(L, by0, R_, T, "MARCO")
        hh = min(T_T, (R_ - L - 12) / (tw(info["aviso"], 1.0, True)))
        self.text(info["aviso"], ((L + R_) / 2, by0 + 5.5), hh, "MIDDLE_CENTER", bold=True)
        # --- cajetín ---
        bw = 180.0
        x0, x1, y0 = R_ - bw, R_, B
        rows = [("pla", 13), ("esc", 15), ("fir", 24), ("mat", 22), ("tit", 21), ("proj", 17), ("estado", 11)]
        y = y0
        ys = {}
        for k, hh_ in rows:
            ys[k] = (y, y + hh_)
            y += hh_
        ytop = y
        self.rect(x0, y0, x1, ytop, "MARCO")
        for k, (a, b) in ys.items():
            self.line((x0, b), (x1, b), "FINA")

        def lab(k, cx, txt, dy=0.0):
            a, b = ys[k]
            self.text(txt, (x0 + cx + 1.5, b - 1.0 - dy), T_MIN, "TOP_LEFT")

        a, b = ys["pla"]
        for xx in (80, 135):
            self.line((x0 + xx, a), (x0 + xx, b), "FINA")
        lab("pla", 0, "PLANO N°"); self.text(info["plano"], (x0 + 40, a + 4.2), 4.2 if tw(info["plano"], 4.2, True) < 74 else 3.5, "MIDDLE_CENTER", bold=True)
        lab("pla", 80, "LÁMINA"); self.text(info["lamina"], (x0 + 107.5, a + 4.2), T_N, "MIDDLE_CENTER")
        lab("pla", 135, "REV."); self.text(info["rev"], (x0 + 157.5, a + 4.2), T_T, "MIDDLE_CENTER", bold=True)
        a, b = ys["esc"]
        for xx in (50, 90, 125):
            self.line((x0 + xx, a), (x0 + xx, b), "FINA")
        lab("esc", 0, "ESCALA"); self.text(info["escala"], (x0 + 25, a + 5.5), T_N if tw(info["escala"], T_N) < 46 else 3.0, "MIDDLE_CENTER")
        lab("esc", 50, "FECHA"); self.text(info["fecha"], (x0 + 70, a + 5.5), T_N, "MIDDLE_CENTER")
        lab("esc", 90, "FORMATO"); self.text(info["formato"], (x0 + 107.5, a + 5.5), T_N, "MIDDLE_CENTER")
        lab("esc", 125, "MÉTODO DE PROYECCIÓN E"); self.projection_symbol((x0 + 143, a + 5.0), 0.62)
        a, b = ys["fir"]
        for xx in (60, 120):
            self.line((x0 + xx, a), (x0 + xx, b), "FINA")
        for i, (nm, key) in enumerate((("DIBUJÓ", "dibujo"), ("REVISÓ", "reviso"), ("APROBÓ", "aprobo"))):
            xx = i * 60
            lab("fir", xx, nm)
            self.text(info.get(key, "A DEFINIR"), (x0 + xx + 30, b - 8.0), T_N, "MIDDLE_CENTER", bold=True)
            self.rect(x0 + xx + 3, a + 2, x0 + xx + 33, a + 12, "FINA")            # casilla de firma
            self.text("firma", (x0 + xx + 4, a + 3), T_MIN, "BOTTOM_LEFT")
            self.rect(x0 + xx + 35, a + 2, x0 + xx + 58, a + 12, "FINA")            # casilla de fecha
            self.text("fecha", (x0 + xx + 36, a + 3), T_MIN, "BOTTOM_LEFT")
        a, b = ys["mat"]
        for xx in (100, 140):
            self.line((x0 + xx, a), (x0 + xx, b), "FINA")
        lab("mat", 0, "MATERIAL")
        for i, ln in enumerate(wrapw(info["material"], 94, 3.0)[:4]):
            self.text(ln, (x0 + 2, b - 6.5 - i * 4.3), 3.0, "TOP_LEFT")
        lab("mat", 100, "MASA"); self.text(info["masa"], (x0 + 120, a + 8), 3.0 if tw(info["masa"], 3.0) < 36 else T_MIN, "MIDDLE_CENTER")
        lab("mat", 140, "TRATAMIENTO")
        for i, ln in enumerate(wrapw(info["trat"], 36, 3.0)[:4]):
            self.text(ln, (x0 + 141.5, b - 6.5 - i * 4.3), 3.0, "TOP_LEFT")
        a, b = ys["tit"]
        lab("tit", 0, "TÍTULO")
        th_ = 4.6 if len(wrapw(info["titulo"], 174, 4.6, True)) <= 2 else 3.6
        for i, ln in enumerate(wrapw(info["titulo"], 174, th_, True)[:3]):
            self.text(ln, (x0 + 3, b - 5.0 - i * (th_ * 1.2)), th_, "TOP_LEFT", bold=True)
        a, b = ys["proj"]
        lab("proj", 0, "PROYECTO")
        self.text(info["proj"], (x0 + 3, b - 5.0), T_N, "TOP_LEFT", bold=True)
        for i, ln in enumerate(wrapw(info["subproj"], 174, 3.0)[:2]):
            self.text(ln, (x0 + 3, b - 10.5 - i * 4.0), 3.0, "TOP_LEFT")
        a, b = ys["estado"]
        self.text(info["estado"], ((x0 + x1) / 2, (a + b) / 2), 3.4 if tw(info["estado"], 3.4, True) < 176 else T_MIN + 0.4, "MIDDLE_CENTER", bold=True)
        # --- tabla de revisiones sobre el cajetín ---
        rv = info["revs"]
        cols = [("REV", 10), ("FECHA", 24), ("DESCRIPCIÓN", 76), ("DIB.", 24), ("REV.", 23), ("APR.", 23)]
        rhs = [max(9.0, 4.3 * len(wrapw(r[2], 76, 3.0)) + 3.0) for r in rv]
        hh = 6.5
        yy = ytop + 1.0
        ytab = yy + hh + sum(rhs)
        self.rect(x0, yy, x1, ytab, "MARCO")
        self.line((x0, ytab - hh), (x1, ytab - hh), "FINA")
        xx = x0
        for (t, w_) in cols:
            self.text(t, (xx + w_ / 2, ytab - hh / 2), T_MIN + 0.3, "MIDDLE_CENTER", bold=True)
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
                    for i, ln in enumerate(wrapw(r[2], 74, 3.0)):
                        self.text(ln, (xx + 1.2, ycur + rh - 2.0 - i * 4.3), 3.0, "TOP_LEFT")
                else:
                    self.text(str(r[j]), (xx + w_ / 2, ycur + rh / 2), 3.0, "MIDDLE_CENTER", bold=(j == 0))
                xx += w_
        yg = ytab + 2.5
        for ln in reversed(wrapw(info["generales"] + " Cotas en mm salvo indicación. No medir sobre el plano. Proyección: método E (primer diedro).", 178, 3.0)):
            self.text(ln, (x0, yg), 3.0, "BOTTOM_LEFT")
            yg += 4.3
        self.cajetin_top = yg
        self.cajetin_x0 = x0
        self.area = (L + 5, B + 5, R_ - 5, by0 - 5)          # área útil (sin banda)

    # ---------- salida ----------
    def declutter(self, forbid=(), step=1.5, kmax=60):
        """Ordenador de textos: desliza los textos de cota/llamada que chocan con otro texto a lo largo de su propia línea (ISO 129: el valor puede
        desplazarse sobre la línea de cota prolongada) y prolonga la línea bajo el texto si sale del tramo entre flechas. forbid: rectángulos donde no
        puede quedar texto (cajetín). Devuelve el número de textos movidos."""
        from ezdxf import bbox as _bb
        import colisiones as C
        boxes = C.text_boxes(list(self.m))
        idx = {id(b[5]): i for i, b in enumerate(boxes)}
        mov = {id(m_["e"]): m_ for m_ in self.movable}
        L_, B_, R_, T_ = 20.0, 10.0, self.W - 10.0, self.H - 10.0
        moved = 0

        G = 0.9                                     # holgura mínima entre textos [mm]

        def clash(bx, skip):
            bi = [bx[0] - G, bx[1] - G, bx[2] + G, bx[3] + G]
            for j, o in enumerate(boxes):
                if j == skip:
                    continue
                if o[0] > bi[2] or o[2] < bi[0] or o[1] > bi[3] or o[3] < bi[1]:
                    continue
                ix = min(bi[2], o[2]) - max(bi[0], o[0])
                iy = min(bi[3], o[3]) - max(bi[1], o[1])
                if ix > 0.05 and iy > 0.05:
                    return True
            if bx[0] < L_ + 0.5 or bx[1] < B_ + 0.5 or bx[2] > R_ - 0.5 or bx[3] > T_ - 0.5:
                return True
            for (x0, y0, x1, y1) in forbid:
                if bx[0] < x1 and bx[2] > x0 and bx[1] < y1 and bx[3] > y0:
                    return True
            return False
        for _pass in range(4):
            changed = False
            order = sorted(range(len(boxes)), key=lambda i: boxes[i][0])
            for ii in order:
                a = boxes[ii]
                m_ = mov.get(id(a[5]))
                if not clash(a, ii):
                    continue
                # el texto choca: si no es movible se intenta mover el otro (el primero movible que choca con él)
                cand = [ii] if m_ else []
                if not cand:
                    ai = [a[0] - G, a[1] - G, a[2] + G, a[3] + G]
                    for j, o in enumerate(boxes):
                        if j != ii and id(o[5]) in mov and min(ai[2], o[2]) - max(ai[0], o[0]) > 0.05 and min(ai[3], o[3]) - max(ai[1], o[1]) > 0.05:
                            cand.append(j)
                for ci in cand:
                    bx = boxes[ci]
                    mm = mov[id(bx[5])]
                    ux, uy = math.cos(math.radians(mm["deg"])), math.sin(math.radians(mm["deg"]))
                    best = None
                    for k in range(1, kmax + 1):
                        for sg in ((1, -1) if not mm.get("leader") else ((1,) if mm["b"][0] >= mm["a"][0] else (-1,))):
                            dx, dy = sg * k * step * ux, sg * k * step * uy
                            nb = [bx[0] + dx, bx[1] + dy, bx[2] + dx, bx[3] + dy]
                            if not clash(nb, ci):
                                best = (dx, dy, nb)
                                break
                        if best:
                            break
                    if not best:
                        continue
                    dx, dy, nb = best
                    bp = mm["base"]
                    mm["base"] = (bp[0] + dx, bp[1] + dy)
                    bx[5].set_placement(mm["base"], align=TA[mm["align"]])
                    boxes[ci][0:4] = nb
                    # prolonga la línea de cota (o el rellano de la llamada) bajo el texto
                    a_, b_ = mm["a"], mm["b"]
                    Ld = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
                    if Ld > 1e-6:
                        vx, vy = (b_[0] - a_[0]) / Ld, (b_[1] - a_[1]) / Ld
                        cx, cy = (nb[0] + nb[2]) / 2, (nb[1] + nb[3]) / 2
                        t = (cx - a_[0]) * vx + (cy - a_[1]) * vy
                        half = abs((nb[2] - nb[0]) * vx) / 2 + abs((nb[3] - nb[1]) * vy) / 2 + 1.0
                        if t + half > Ld:
                            self.line(b_, (a_[0] + vx * (t + half), a_[1] + vy * (t + half)), "COTA")
                        if t - half < 0:
                            self.line(a_, (a_[0] + vx * (t - half), a_[1] + vy * (t - half)), "COTA")
                    moved += 1
                    changed = True
                    break
            if not changed:
                break
        self.n_moved = moved
        return moved

    def save(self, dxf_path, pdf_path=None):
        self.doc.saveas(dxf_path)
        if pdf_path:
            return render_pdf(self.doc, pdf_path, self.W, self.H)


def render_pdf(doc, pdf_path, Wp=W, Hp=H):
    from ezdxf.addons.drawing import Frontend, RenderContext, pymupdf, layout, config
    backend = pymupdf.PyMuPdfBackend()
    cfg = config.Configuration(color_policy=config.ColorPolicy.BLACK,
                               background_policy=config.BackgroundPolicy.WHITE,
                               lineweight_scaling=1.0,
                               min_lineweight=0.13)
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace(), finalize=True)
    page = layout.Page(Wp, Hp, layout.Units.mm, margins=layout.Margins.all(0))
    pdf = backend.get_pdf_bytes(page, settings=layout.Settings(fit_page=False, scale=1.0))
    open(pdf_path, "wb").write(pdf)
    return pdf_path
