"""Utilidades para armar láminas: regiones, ficha de pieza, notas, bloques GD&T y cotas repetidas."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_base import *


def split(rect, nx=1, ny=1, i=0, j=0, gap=6.0):
    """Subcelda (i,j) de la rejilla nx×ny dentro del rectángulo (i: columna desde la izquierda; j: fila desde arriba)."""
    x0, y0, x1, y1 = rect
    cw, ch = (x1 - x0) / nx, (y1 - y0) / ny
    return (x0 + i * cw + gap / 2, y1 - (j + 1) * ch + gap / 2, x0 + (i + 1) * cw - gap / 2, y1 - j * ch - gap / 2)


def vspan(rect, f0, f1):
    """Franja vertical del rectángulo entre las fracciones f0 y f1 (0 = arriba)."""
    x0, y0, x1, y1 = rect
    H = y1 - y0
    return (x0, y1 - f1 * H, x1, y1 - f0 * H)


def hspan(rect, f0, f1):
    x0, y0, x1, y1 = rect
    Wd = x1 - x0
    return (x0 + f0 * Wd, y0, x0 + f1 * Wd, y1)


class Pieza:
    """Lámina de fabricación de una pieza (o grupo de piezas iguales). Regiones: views (izq., sobre el cajetín), right (columna de notas), low (tablas)."""

    def __init__(self, ctx, keys, titulo, fmt="A2", mat_override=None, grupo=""):
        self.ctx = ctx
        self.keys = [k for k in keys if ctx.m.get(k)]
        self.p0 = ctx.m.get(self.keys[0])
        self.lead = self.p0.code
        masa = " + ".join(f"{f(ctx.m.get(k).mass_unit, 1)} kg" for k in self.keys[:3]) + (" c/u" if True else "")
        h = Hoja(ctx, self.lead, titulo, "", fmt=fmt, material=mat_override or self.p0.material, masa=masa if len(self.keys) > 1 else f"{f(self.p0.mass_unit, 1)} kg c/u",
                 trat=self.p0.tratamiento if self.p0.tratamiento != "—" else "Ninguno (ver notas)", serie="FAB", items=[ctx.m.get(k).code for k in self.keys], grupo=grupo)
        self.h = h
        self.s = h.begin()
        R = h.R
        self.W_right = 172.0
        x0, y0, x1, y1 = R["left"]
        self.views = (x0, y0, x1, y1)
        self.right = (R["right"][0], R["right"][1], R["right"][2], R["right"][3])
        self.low = R["low"]
        self.scales = []
        self.vlist = []
        self.dims_n0 = len(vistas.COTAS.rows)

    def view(self, shapes, view, box, **kw):
        V = View.auto(self.s, shapes if isinstance(shapes, dict) else self.ctx.sh(*shapes), view, box, mat=None, **{k: v for k, v in kw.items() if k != "mat"}) if False else None
        return V

    def V(self, keys, view, box, label="", margin=(16, 16, 16, 16), mat=None, **kw):
        sh = keys if isinstance(keys, dict) else self.ctx.sh(*keys)
        V = View.auto(self.s, sh, view, box, margin=margin, label=label or view, **kw)
        V.mat = mat or {k: self.ctx.mat.get(k, "acero") for k in sh}
        V.draw()
        self.scales.append(V.scale)
        self.vlist.append(V)
        return V

    def fit_scale_txt(self):
        sc = sorted(set(self.scales), reverse=True)
        return " / ".join(vistas.scale_txt(x) for x in sc) if sc else ""

    def tables(self, weld_ids=None, extra_rows=None, ficha_h=None):
        """Ficha (despiece de la pieza) y tabla de soldaduras en la franja inferior izquierda. Devuelve la y inferior."""
        x0, y0, x1, y1 = self.low
        y, _ = tabla_despiece(self.ctx, self.s, x0, y1 - 1, self.keys, x1 - x0, ymin=y0, title="FICHA DE LA PIEZA (despiece)", total=len(self.keys) > 1)
        if weld_ids:
            y, _ = tabla_soldaduras(self.ctx, self.s, x0, y - 5, weld_ids, x1 - x0, ymin=y0, title="SOLDADURAS DE ESTA LÁMINA")
        self.y_low = y
        return y

    def notes(self, specific, gd=(), inspect=None, y_top=None):
        """Columna de notas: fabricación específica + generales + inspección + punzonado + pintura."""
        ctx, s = self.ctx, self.s
        x0, y0, x1, y1 = self.right
        wdt = x1 - x0 - 2
        y = (y_top or y1) - 1
        y = s.notes_block(x0, y, "NOTAS DE FABRICACIÓN", list(specific), h=T_N, width=wdt, numbered=True)
        y = s.notes_block(x0, y - 2, "GENERALES", notas_gen_fab(ctx), h=T_N, width=wdt)
        insp = inspect or "VT 100 % de toda soldadura; MT/UT según la tabla de soldaduras (AWS D1.1 y BTH-1 Cat. B); control dimensional 100 % de cotas con tolerancia."
        y = s.notes_block(x0, y - 2, "PLAN DE INSPECCIÓN", [insp, "Punzonar código de la pieza y marca de colada (trazabilidad EN 10204 3.1)."], h=T_N, width=wdt)
        return y

    def finish_scale(self):
        self.h.escala = self.fit_scale_txt() or "S/E"


def gd_column(s, x, y, items, step=14.0):
    """Columna de recuadros GD&T con su leyenda; items = [(sym, tol, datum, texto)]; devuelve y final."""
    for sym, tol, datum, txt in items:
        wd = s.gdt((x, y - 7), sym, tol, datum)
        s.text(txt, (x + wd + 3, y - 3.5), T_N, "MIDDLE_LEFT")
        y -= step
    return y


def thread_txt(d, pitch=None, L=None):
    return f"M{fm(d, 0)}" + (f"×{fm(pitch, 2)}" if pitch else "") + (f" prof. {fm(L, 0)}" if L else "")


def diam_dims(V, c3, rs, ang=35, keys=None, texts=None, ext=12.0, step=7.0):
    """Cotas de varios diámetros concéntricos (lista de radios) con llamadas apiladas."""
    for i, r in enumerate(rs):
        V.dim_dia(c3, r, ang + i * 24, text=(texts[i] if texts else None), on=keys, ext=ext + step * i)
