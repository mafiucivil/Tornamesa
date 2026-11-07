"""Registro de láminas de pieza y utilidades comunes (símbolos de soldadura, claves de junta, giro de piezas locales)."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_util import *

PLAN = []          # (nombre_función, [claves de pieza]) — se llena con @pieza


NOGROUP = set()     # láminas de características (ranuras, patrón de tapones, tablones): no «poseen» ninguna pieza del despiece


def pieza(*keys, nogroup=False):
    def deco(fn):
        PLAN.append((fn.__name__, list(keys), fn))
        if nogroup:
            NOGROUP.add(fn.__name__)
        return fn
    return deco


def register(ctx):
    """Asigna a cada pieza la lámina que la dibuja (para la columna «Plano» del despiece) antes de dibujar cualquier lámina."""
    ctx.group_of = {}
    for name, keys, fn in PLAN:
        if name in NOGROUP:
            continue
        ks = [k for k in keys if ctx.m.get(k)]
        for k in ks:
            ctx.group_of[k] = ctx.m.get(ks[0]).code


def ghost(p, V, keys, hatch=False):
    sh = p.ctx.sh(*[k for k in keys if k in p.ctx.shapes])
    if not sh:
        return
    G = View(p.s, sh, V.view, V.origin, V.scale, center=V.center if hasattr(V, "center") else (0, 0, 0), win=V.win, cut=V.cut, label="fantasma")
    G.draw(layer_vis="FANT", hatch=False)


def rough_note(s, x, y, ra, txt):
    s.roughness((x, y), ra)
    s.text(txt, (x + 12 + tw(ra, T_N) + 4, y + 6), T_N, "MIDDLE_LEFT")


def pos_table(p, x, y, title, cols, rows, width):
    sc = width / sum(c[1] for c in cols)
    return p.s.table(x, y, [(t, w * sc, a) for t, w, a in cols], rows, h=T_S, title=title)[0]


# ---------------------------------------------------------------------------------------------- helpers de sección
CUT_Y = ((0, 0, 0), (0, 1, 0))
CUT_X = ((0, 0, 0), (-1, 0, 0))


def tol_dim(V, a, b, code, d, **kw):
    """Cota de diámetro/longitud con ajuste ISO 286 en el texto (límites calculados)."""
    return V.dim(a, b, kw.pop("off", 10), text=tol_txt(d, code), **kw)


def w_sym(p, jid, V, pt3, off, **kw):
    """Símbolo de soldadura de la junta jid apuntando a un punto 3D de la vista V."""
    a = V.P(pt3)
    if "sh" not in kw:
        z_ = getattr(p.h, "zone", p.h.R["left"])
        kw["sh"] = 1 if a[0] < z_[2] - 190 else -1
    sg = kw["sh"]
    p.h.weld(jid, a, (a[0] + abs(off[0]) * sg, a[1] + off[1]), **kw)


def J(ctx, frag):
    w = ctx.weld_find(frag)
    return w["id"] if w else "J??"


def jids(ctx, *frags):
    out = []
    for fr in frags:
        w = ctx.weld_find(fr)
        if w:
            out.append(w["id"])
    return out


# ======================================================================================================
def rot_key(ctx, key, new, deg):
    ctx.shapes[new] = ctx.shapes[key].rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), deg)
    ctx.mat[new] = ctx.mat.get(key, "acero")
    return new




def ramales_txt_short(ctx):
    g = ctx.g
    v = g.fila("Ramales: longitud mínima")
    d = math.hypot(ctx.P["x_lug"], g.cl_lug)
    L = v["dem"] if v else 2 * d
    return f"Ramales de eslinga a ≥ 60° sobre la horizontal: longitud ≥ {fm(L, 0)} mm por ramal (núcleo, fila «Ramales: longitud mínima»; distancia oreja–eje {fm(d, 0)} mm)."




def w_out(p, jid, V, pt3, side="right", dy=12.0, **kw):
    """Símbolo de soldadura cuya línea de referencia nace fuera de la pila de cotas de la vista (lado right|left|top|bottom): no pisa cotas ni geometría."""
    a = V.P(pt3)
    x0, y0, x1, y1 = V.ext
    if side == "right":
        q = (x1 + 8 + 8.5 * V.lv["right"] + 6, a[1] + dy); sh = 1
    elif side == "left":
        q = (x0 - 8 - 8.5 * V.lv["left"] - 6, a[1] + dy); sh = -1
    elif side == "top":
        q = (a[0] + 6, y1 + 10 + 8.5 * V.lv["top"] + 6); sh = 1
    else:
        q = (a[0] + 6, y0 - 10 - 8.5 * V.lv["bottom"] - 14); sh = 1
    p.h.weld(jid, a, q, sh=sh, **kw)
