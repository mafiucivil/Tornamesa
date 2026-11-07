"""Esquemas ampliados de juntas soldadas: preparación de junta a tope (V, bisel) con ángulo, abertura de raíz, talón y respaldo (ISO 9692-1 / AWS D1.1 cl. 3),
cordón de filete en T con catetos z y garganta a, y ranura de cierre. Se dibujan a escala normalizada elegida por el compositor y se acotan en papel."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from draw import T_N, T_S, tw
from geom import fm, f

BACKING = (6.0, 40.0)        # respaldo de acero propuesto: espesor × ancho (AWS D1.1 cl. 3, a confirmar)


def _poly(s, pts, ang=0.0, solid=False, layer="VIS", scale=0.35):
    s.pline(pts, layer, closed=True)
    if solid:
        s.hatch_poly(pts, solid=True)
    else:
        s.hatch_poly(pts, scale=scale, angle=ang, pattern="ANSI31")


def butt_size(t, kind="V"):
    Lh = max(30.0, 1.6 * t)
    return (2 * Lh + 3.0, t + BACKING[0] + 8.0), Lh


def prep_butt(s, ox, oy, k, t, jid=None, plano=None, kind="V", angle=60.0, root=3.0, face=2.0, backing=True, tag="", transition=None):
    """Junta a tope con preparación. (ox, oy): esquina inferior izquierda del recuadro natural; k: escala de papel/mm."""
    (Wn, Hn), Lh = butt_size(t, kind)
    bt = BACKING[0] if backing else 0.0
    xr0, xr1 = Lh, Lh + root          # caras de raíz (modelo)
    y0, y1 = bt, bt + t
    P = lambda x, y: (ox + x * k, oy + y * k)
    half = math.tan(math.radians(angle / 2)) * (t - face)
    left = [P(0, y0), P(xr0, y0), P(xr0, y0 + face), P(xr0 - half, y1), P(0, y1)]
    if kind == "bevel":
        hb = math.tan(math.radians(angle)) * (t - face)       # bisel a 45° solo en la plancha izquierda
        left = [P(0, y0), P(xr0, y0), P(xr0, y0 + face), P(xr0 - min(hb, Lh - 4), y1), P(0, y1)]
        right = [P(xr1, y0), P(xr1 + Lh, y0), P(xr1 + Lh, y1), P(xr1, y1)]
    else:
        right = [P(xr1, y0), P(xr1 + Lh, y0), P(xr1 + Lh, y1), P(xr1 + half, y1), P(xr1, y0 + face)]
    _poly(s, left, 0.0)
    _poly(s, right, 90.0)
    if backing:
        bw = BACKING[1]
        _poly(s, [P(xr0 + root / 2 - bw / 2, 0), P(xr0 + root / 2 + bw / 2, 0), P(xr0 + root / 2 + bw / 2, bt), P(xr0 + root / 2 - bw / 2, bt)], 45.0, scale=0.3)
    # cotas
    xm = P(xr0 + root / 2, 0)[0]
    s.dim(P(0, y0), P(0, y1), -10, f"t = {fm(t, 0)}", "v")
    s.dim(P(xr0, y0 - 0.0 + bt * 0 + 0.0), P(xr1, y0), -13 if backing else -9, f"abertura de raíz r = {fm(root, 0)}", "h", outside=True) if not backing else \
        s.dim(P(xr0, y0 + face * 0.5), P(xr1, y0 + face * 0.5), 9 + face * k, f"r = {fm(root, 0)}", "h", outside=True)
    s.dim(P(xr0, y0), P(xr0, y0 + face), -7 - (Lh - 8) * k * 0.0, f"talón c = {fm(face, 0)}", "v", outside=True) if False else None
    s.leader(P(xr0, y0 + face / 2), (P(xr0, y0)[0] - 18 - tw("talón 2", T_N) * 0, P(xr0, y0)[1] + (t + 10) * k * 0.0 - 12), f"talón c = {fm(face, 0)}", dot=True) if False else None
    # ángulo
    apex = P((xr0 + xr1) / 2, y0 + face)
    rr = (t - face) * k * 0.55
    a_half = angle / 2
    s.arc(apex, rr, 90 - a_half if kind != "bevel" else 90 - angle, 90 + (a_half if kind != "bevel" else 0), "COTA") if False else None
    s.dim_ang(apex, rr, 90 - (a_half if kind != "bevel" else angle), 90 + (a_half if kind != "bevel" else 0), f"{fm(angle, 0)}°")
    s.leader(P(xr0, y0 + face * 0.5), (P(xr0, y0)[0] - 26, P(xr0, y0)[1] - 8 - (10 if backing else 0)), f"talón c = {fm(face, 0)}", dot=True)
    if backing:
        s.leader(P(xr0 + root / 2 + BACKING[1] / 2 - 4, bt / 2), (P(xr0 + root / 2 + BACKING[1] / 2, 0)[0] + 14, P(0, 0)[1] - 10), f"respaldo {fm(BACKING[0], 0)}×{fm(BACKING[1], 0)} (PROPUESTA)", dot=True)
    if transition:
        s.text(transition, (P(0, y1)[0], P(0, y1)[1] + 3), T_N, "BOTTOM_LEFT")
    if jid and plano is not None:
        a = P(xr0 + root / 2 + 1, y1 - 0.5)
        plano.h.weld(jid, a, (ox + Wn * k + 12, a[1] + 26), sh=1, prep=f"{fm(angle, 0)}°")


def fillet_size(z, t1, t2):
    L = max(24.0, 3.0 * z)
    return (2 * L + t1, t2 + max(26.0, 4.5 * z) + 4.0), L


def prep_fillet(s, ox, oy, k, z, t1, t2, jid=None, plano=None, both=True, tag=""):
    """Filete en T: plancha vertical t1 sobre plancha horizontal t2, catetos z, garganta a = 0,707 z."""
    (Wn, Hn), L = fillet_size(z, t1, t2)
    Hh = max(26.0, 4.5 * z)
    xc = L + t1 / 2
    P = lambda x, y: (ox + x * k, oy + y * k)
    base = [P(0, 0), P(Wn, 0), P(Wn, t2), P(0, t2)]
    web = [P(xc - t1 / 2, t2), P(xc + t1 / 2, t2), P(xc + t1 / 2, t2 + Hh), P(xc - t1 / 2, t2 + Hh)]
    _poly(s, base, 0.0)
    _poly(s, web, 90.0)
    sides = (-1, 1) if both else (1,)
    for sd in sides:
        xe = xc + sd * t1 / 2
        tri = [P(xe, t2), P(xe + sd * z, t2), P(xe, t2 + z)]
        _poly(s, tri, solid=True)
        s.pline(tri, "VIS", closed=True)
    # cotas: catetos y garganta
    xe = xc + t1 / 2
    s.dim(P(xe, t2), P(xe + z, t2), -4 - 0, f"z = {fm(z, 0)}", "h", outside=True) if False else None
    s.dim(P(xe, t2 + z), P(xe + z, t2 + z), 7 * 1, f"z = {fm(z, 0)}", "h", outside=True) if False else None
    s.dim(P(xe, t2), P(xe + z, t2), 10 + 0, f"z = {fm(z, 0)}", "h", outside=True) if False else None
    s.dim(P(xe + z, t2 - 0), P(xe + z, t2 + z), 9, f"z = {fm(z, 0)}", "v", outside=True)
    s.dim(P(xe, t2 + z), P(xe + z, t2), 7, f"a = {fm(z * 0.7071, 1)}", "a", outside=True)
    s.dim(P(0, 0), P(0, t2), -9, f"t = {fm(t2, 0)}", "v")
    s.dim(P(xc - t1 / 2, t2 + Hh), P(xc + t1 / 2, t2 + Hh), 8, f"t = {fm(t1, 0)}", "h", outside=True)
    if jid and plano is not None:
        a = P(xe + z * 0.35, t2 + z * 0.35)
        plano.h.weld(jid, a, (ox + Wn * k + 12, a[1] + 30), sh=1)


def slot_size(w=22.0, L=80.0, t=20.0):
    return (L + 40.0, w + t + 46.0)


def prep_slot(s, ox, oy, k, w, L, t, jid=None, plano=None, pitch=250.0):
    """Ranura de cierre (soldadura de ranura): planta de la ranura obonga y sección con relleno completo."""
    P = lambda x, y: (ox + x * k, oy + y * k)
    yb = t + 36.0
    # planta
    r = w / 2
    cx0, cx1 = 20 + r, 20 + L - r
    pts = []
    n = 16
    for i in range(n + 1):
        a = -math.pi / 2 + math.pi * i / n
        pts.append(P(cx1 + r * math.cos(a), yb + r + r * math.sin(a)))
    for i in range(n + 1):
        a = math.pi / 2 + math.pi * i / n
        pts.append(P(cx0 + r * math.cos(a), yb + r + r * math.sin(a)))
    s.pline(pts, "VIS", closed=True)
    s.dim(P(20, yb + w), P(20 + L, yb + w), 6, f"L = {fm(L, 0)}", "h")
    s.dim(P(20 + L, yb), P(20 + L, yb + w), 6, f"ancho {fm(w, 0)}", "v")
    s.text(f"paso c/{fm(pitch, 0)}", (P(20 + L / 2, yb - 2)[0], P(0, yb - 2)[1]), T_N, "TOP_CENTER")
    # sección longitudinal
    y0 = 0.0
    pl = [P(0, y0), P(L + 40, y0), P(L + 40, y0 + t), P(0, y0 + t)]
    s.hatch_poly([P(0, y0), P(20, y0), P(20, y0 + t), P(0, y0 + t)], scale=0.35, angle=0.0, pattern="ANSI31")
    s.hatch_poly([P(20 + L, y0), P(L + 40, y0), P(L + 40, y0 + t), P(20 + L, y0 + t)], scale=0.35, angle=0.0, pattern="ANSI31")
    s.hatch_poly([P(20, y0), P(20 + L, y0), P(20 + L, y0 + t), P(20, y0 + t)], solid=True)
    s.pline(pl, "VIS", closed=True)
    s.dim(P(0, y0), P(0, y0 + t), -8, f"t = {fm(t, 0)}", "v")
    s.text("relleno completo de la ranura (sobre el alma/nervio)", (P(20 + L / 2, y0 - 2)[0], P(0, y0 - 2)[1]), T_N, "TOP_CENTER")
    if jid and plano is not None:
        a = P(20 + L * 0.3, y0 + t)
        plano.h.weld(jid, a, (ox + (L + 40) * k + 12, a[1] + 20), sh=1)


# ------------------------------------------------------------------------------------------------
def add_prep(p, name, w, title=None, lv=(1, 1, 1, 1), t1=None, t2=None, both=True, mins=None, maxs=None):
    """Agrega a la lámina p un esquema de junta correspondiente al registro de soldaduras w (dict de ctx.welds). Devuelve la especificación."""
    jid = w["id"]
    if w["groove"] and w["sym"] in ("V", "bevel"):
        t = w["t"]
        kind = "V" if w["sym"] == "V" else "bevel"
        ang = 60.0 if kind == "V" else 45.0
        root = 3.0 if "raíz 3" in w["prep"] else 2.0
        (Wn, Hn), _ = butt_size(t, kind)
        tr = "transición de espesores 1:4" if "1:4" in w["prep"] else None
        nm = f"{jid}: junta {'a tope en V 60°' if kind == 'V' else 'con bisel 45°'}"
        return p.vs(name, [], "top", nat=(Wn, Hn), lv=(2, 3, 2, 2), extra=(0, 0, 112, 0), mins=1.0, maxs=5.0, title=title or f"DETALLE {jid}: PREPARACIÓN DE JUNTA ({'V 60°' if kind == 'V' else 'bisel 45°'}, t = {fm(t, 0)})",
                    custom=lambda s, ox, oy, k, pl: prep_butt(s, ox, oy, k, t, jid, pl, kind, ang, root, 2.0, True, transition=tr))
    if w["groove"] and w["sym"] == "slot":
        wd, L = 22.0, 80.0
        Wn, Hn = slot_size(wd, L, w["t"])
        return p.vs(name, [], "top", nat=(Wn, Hn), lv=(2, 3, 2, 2), extra=(0, 0, 112, 0), mins=1.0, maxs=2.0, title=title or f"DETALLE {jid}: SOLDADURA DE RANURA",
                    custom=lambda s, ox, oy, k, pl: prep_slot(s, ox, oy, k, wd, L, w["t"], jid, pl))
    # filete
    z = w["z"]
    t2 = t2 or max(w["t"] or 10.0, 6.0)
    t1 = t1 or max(min(w["t"] or 10.0, 20.0), 6.0)
    (Wn, Hn), _ = fillet_size(z, t1, t2)
    return p.vs(name, [], "top", nat=(Wn, Hn), lv=(2, 1, 2, 2), extra=(0, 0, 112, 0), mins=mins or 2.0, maxs=maxs or 5.0, title=title or f"DETALLE {jid}: FILETE EN T z{fm(z, 0)} (a = {fm(z * 0.7071, 1)})",
                custom=lambda s, ox, oy, k, pl: prep_fillet(s, ox, oy, k, z, t1, t2, jid, pl, both))
