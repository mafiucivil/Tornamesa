"""Utilidades para armar láminas: regiones, ficha de pieza, notas, bloques GD&T y cotas repetidas."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_base import *
from layout import Plano, VS
import autodim


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


class Pieza(Plano):
    """Lámina de fabricación de una pieza (o grupo de piezas iguales). Las vistas se declaran con p.vs(...) y se componen en build()."""

    def __init__(self, ctx, keys, titulo, fmt="A2", mat_override=None, grupo="", code=None):
        self.keys = [k for k in keys if ctx.m.get(k)]
        self.p0 = ctx.m.get(self.keys[0])
        self.lead = self.p0.code
        masa = " + ".join(f"{f(ctx.m.get(k).mass_unit, 1)}" for k in self.keys[:3]) + " kg c/u"
        h = Hoja(ctx, code or self.lead, titulo, "", fmt=("A1" if fmt in ("auto", "auto3") else fmt), material=mat_override or self.p0.material, masa=(masa if len(masa) <= 24 else "ver ficha (kg c/u)") if len(self.keys) > 1 else f"{f(self.p0.mass_unit, 1)} kg c/u",
                 trat=self.p0.tratamiento if self.p0.tratamiento != "—" else "Ninguno (ver notas)", serie="FAB", items=[ctx.m.get(k).code for k in self.keys], grupo=grupo)
        self.init_plano(ctx, h)
        self.iso_keys = list(self.keys)
        self.fmt_try = ["A2", "A1"] if fmt == "auto" else (["A3", "A2", "A1"] if fmt == "auto3" else None)
        self.W_right = 172.0

    def tables(self, weld_ids=None, extra_rows=None, ficha_h=None):
        """Ficha (despiece de la pieza) y tabla de soldaduras: bloques anchos de la franja inferior."""
        self.ficha_block(self.keys)
        if weld_ids:
            self.weld_block(weld_ids)

    def notes(self, specific, gd=(), inspect=None, y_top=None):
        """Notas: fabricación específica + generales + inspección (bloques de la banda lateral)."""
        ctx = self.ctx
        self.note_block("NOTAS DE FABRICACIÓN", list(specific), numbered=True)
        if gd:
            self.gd(list(gd))
        self.note_block("GENERALES", notas_gen_fab(ctx))
        insp = inspect or "VT 100 % de toda soldadura; MT/UT según la tabla de soldaduras (AWS D1.1 y BTH-1 Cat. B); control dimensional 100 % de cotas con tolerancia."
        self.note_block("PLAN DE INSPECCIÓN", [insp, "Punzonar código de la pieza y marca de colada (trazabilidad EN 10204 3.1)."])

    def finish_scale(self):
        self.build()


def gd_column(s, x, y, items, step=14.0):
    """Columna de recuadros GD&T con su leyenda; items = [(sym, tol, datum, texto)]; devuelve y final."""
    for sym, tol, datum, txt in items:
        if not hasattr(s, "views"):
            s.views = []
        s.views.append((x, y - 7 - 6, x + 14 + 7 + tw(txt, T_N) + 3, y))
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
