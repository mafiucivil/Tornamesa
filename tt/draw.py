"""Mini-librería de dibujo técnico sobre ezdxf (coordenadas de papel en mm, A1 841x594)."""
import math
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

W, H = 841.0, 594.0
TXT_STYLE = "STD"


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
                            ("ACH", 13, "CONTINUOUS"), ("MARCO", 70, "CONTINUOUS"), ("FANT", 18, "FANTASMA")]:
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

    # ---------- formato ----------
    def frame(self, v, sheet_no, n_sheets, title2, scale_txt, rev="B"):
        self.rect(0, 0, W, H, "FINA")
        self.rect(20, 10, W - 10, H - 10, "MARCO")
        # zonas
        for i in range(1, 8):
            x = 20 + i * (W - 30) / 8
            self.line((x, H - 10), (x, H - 5), "FINA"); self.line((x, 10), (x, 5), "FINA")
        for i in range(8):
            self.text(str(i + 1), (20 + (i + 0.5) * (W - 30) / 8, H - 7.5), 2.5, "MIDDLE_CENTER")
        for i, L in enumerate("FEDCBA"):
            y = 10 + (i + 0.5) * (H - 20) / 6
            self.text(L, (15, y), 2.5, "MIDDLE_CENTER")
        # rótulo 180 x 62
        x0, y0, x1 = W - 10 - 180, 10, W - 10
        y1 = y0 + 62
        self.rect(x0, y0, x1, y1, "MARCO")
        rows = [y0 + 10, y0 + 20, y0 + 30, y0 + 44]
        for yy in rows:
            self.line((x0, yy), (x1, yy), "FINA")
        self.line((x0 + 60, y0), (x0 + 60, y0 + 30), "FINA")
        self.line((x0 + 120, y0), (x0 + 120, y0 + 30), "FINA")
        self.text(f"PROYECTO: {v['proj']}", (x0 + 2, y1 - 3), 3.2, "TOP_LEFT", bold=True)
        self.text(v["title"], (x0 + 2, y1 - 9.5), 2.6, "TOP_LEFT")
        self.text(title2, (x0 + 2, y0 + 41.5), 3.6, "TOP_LEFT", bold=True)
        self.text("EMITIDO PARA REVISIÓN – NO APTO PARA FABRICACIÓN HASTA APROBACIÓN", (x0 + 2, y0 + 32), 2.2, "BOTTOM_LEFT", bold=True)
        cells = [("ELABORÓ", "—", 0, 2), ("REVISÓ", "—", 1, 2), ("APROBÓ", "—", 2, 2),
                 ("ESCALA", scale_txt, 0, 1), ("FECHA", "16-10-2026", 1, 1), ("FORMATO", "A1", 2, 1),
                 ("PLANO N°", f"{v['code']}-{sheet_no:02d}", 0, 0), ("LÁMINA", f"{sheet_no} de {n_sheets}", 1, 0), ("REV.", rev, 2, 0)]
        for lab, val, cx, ry in cells:
            xx = x0 + cx * 60
            yy = y0 + ry * 10
            self.text(lab, (xx + 1.5, yy + 8.6), 1.8, "TOP_LEFT")
            self.text(val, (xx + 30, yy + 3.2), 3.0 if ry == 0 else 2.6, "MIDDLE_CENTER", bold=(ry == 0))
        self.text("Cotas en mm salvo indicación. No medir sobre el plano.", (x0, y1 + 1.5), 2.0, "BOTTOM_LEFT")
        self.text("Rev. B (16-10-2026): disco cajón con barras perimetrales; empuje directo con carro y trinquete.", (20, 6.5), 2.0, "BOTTOM_LEFT")

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
