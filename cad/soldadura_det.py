"""Esquemas ampliados de juntas soldadas: preparación de junta a tope (V, bisel) con ángulo, abertura de raíz, talón y respaldo (ISO 9692-1 / AWS D1.1:2020 cláusula 5),
cordón de filete en T con catetos z y garganta a, y ranura de cierre. Se dibujan a escala normalizada elegida por el compositor y se acotan en papel."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from draw import T_N, T_S, tw
from geom import fm, f

BACKING = (6.0, 40.0)        # respaldo de acero propuesto: espesor × ancho (AWS D1.1:2020 cláusula 5, a confirmar)


def _poly(s, pts, ang=0.0, solid=False, layer="VIS", scale=0.35):
    s.pline(pts, layer, closed=True)
    if solid:
        s.hatch_poly(pts, solid=True)
    else:
        s.hatch_poly(pts, scale=scale, angle=ang, pattern="ANSI31")


def butt_size(t, kind="V", t_thick=None, land=None):
    Lh = max(30.0, 1.6 * t)
    if t_thick and t_thick > t:
        Lh = max(Lh, math.tan(math.radians(30)) * t_thick + min(4 * (t_thick - t), land or 99.0) + 12.0)
        return (2 * Lh + 3.0, t_thick + BACKING[0] + 22.0), Lh
    return (2 * Lh + 3.0, t + BACKING[0] + 8.0), Lh


def prep_butt(s, ox, oy, k, t, jid=None, plano=None, kind="V", angle=60.0, root=3.0, face=2.0, backing=True, tag="", transition=None, t_thick=None, land=None, backing_txt=None):
    """Junta a tope con preparación. (ox, oy): esquina inferior izquierda del recuadro natural; k: escala de papel/mm.
    t_thick: espesor de la pieza gruesa (derecha) si hay transición de espesores 1:4 (A-10, B-04): chaflán 1:4 en la pieza gruesa limitado a 'land' mm
    (p. ej. hasta 3 mm del agujero de pasador) y el resto de la diferencia con la pendiente 1:4 del cordón sobre la pieza delgada. Cara a ras: la del respaldo."""
    (Wn, Hn), Lh = butt_size(t, kind, t_thick, land)
    bt = BACKING[0] if backing else 0.0
    xr0, xr1 = Lh, Lh + root          # caras de raíz (modelo)
    y0, y1 = bt, bt + t
    P = lambda x, y: (ox + x * k, oy + y * k)
    half = math.tan(math.radians(angle / 2)) * (t - face)
    left = [P(0, y0), P(xr0, y0), P(xr0, y0 + face), P(xr0 - half, y1), P(0, y1)]
    tp = t
    Lc = 0.0
    if kind == "bevel":
        hb = math.tan(math.radians(angle)) * (t - face)       # bisel a 45° solo en la plancha izquierda
        left = [P(0, y0), P(xr0, y0), P(xr0, y0 + face), P(xr0 - min(hb, Lh - 4), y1), P(0, y1)]
        right = [P(xr1, y0), P(xr1 + Lh, y0), P(xr1 + Lh, y1), P(xr1, y1)]
    elif t_thick and t_thick > t + 0.1:
        dT = t_thick - t
        Lc = min(4.0 * dT, land if land else 4.0 * dT)
        tp = t_thick - Lc / 4.0                                 # espesor de la pieza gruesa en el borde de la junta
        hp = math.tan(math.radians(angle / 2)) * (tp - face)
        right = [P(xr1, y0), P(xr1 + Lh, y0), P(xr1 + Lh, y0 + t_thick), P(xr1 + hp + Lc, y0 + t_thick), P(xr1 + hp, y0 + tp), P(xr1, y0 + face)]
    else:
        right = [P(xr1, y0), P(xr1 + Lh, y0), P(xr1 + Lh, y1), P(xr1 + half, y1), P(xr1, y0 + face)]
    _poly(s, left, 0.0)
    _poly(s, right, 90.0)
    if backing:
        bw = BACKING[1]
        _poly(s, [P(xr0 + root / 2 - bw / 2, 0), P(xr0 + root / 2 + bw / 2, 0), P(xr0 + root / 2 + bw / 2, bt), P(xr0 + root / 2 - bw / 2, bt)], 45.0, scale=0.3)
    # cotas
    s.dim(P(0, y0), P(0, y1), -10, f"t = {fm(t, 0)}", "v")
    if t_thick and t_thick > t + 0.1 and kind != "bevel":
        s.dim(P(xr1 + Lh, y0), P(xr1 + Lh, y0 + t_thick), 8, f"t = {fm(t_thick, 0)}", "v")
        hp = math.tan(math.radians(angle / 2)) * (tp - face)
        s.dim(P(xr1 + hp, y0 + t_thick), P(xr1 + hp + Lc, y0 + t_thick), 6, f"{fm(Lc, 0)} (chaflán 1:4)", "h", outside=Lc * k < 22)
        if tp > t + 0.05:                     # resto de la transición: pendiente 1:4 del cordón sobre la pieza delgada
            x_end = xr0 - half - 4.0 * (tp - t)
            s.line(P(xr1 + hp, y0 + tp), P(max(x_end, 2.0), y1), "FINA")
            resto = f"resto: pendiente 1:4 del cordón sobre la pieza delgada ({fm(tp - t, 1)} mm)"
    if backing:
        s.dim(P(xr0, y0 + face * 0.5), P(xr1, y0 + face * 0.5), 9 + face * k, f"b = {fm(root, 0)}", "h", outside=True)
    else:
        s.dim(P(xr0, y0), P(xr1, y0), -9, f"abertura de raíz b = {fm(root, 0)}", "h", outside=True)
    # ángulo
    apex = P((xr0 + xr1) / 2, y0 + face)
    rr = (t - face) * k * 0.55
    a_half = angle / 2
    s.dim_ang(apex, rr, 90 - (a_half if kind != "bevel" else angle), 90 + (a_half if kind != "bevel" else 0), f"{fm(angle, 0)}°")
    s.leader(P(xr0, y0 + face * 0.5), (P(xr0, y0)[0] - 26, P(xr0, y0)[1] - 8 - (10 if backing else 0)), f"talón c = {fm(face, 0)}", dot=True)
    if backing:
        s.leader(P(xr0 + root / 2 + BACKING[1] / 2 - 4, bt / 2), (P(xr0 + root / 2 + BACKING[1] / 2, 0)[0] + 14, P(0, 0)[1] - 10), backing_txt or f"respaldo {fm(BACKING[0], 0)}×{fm(BACKING[1], 0)} (PROPUESTA)", dot=True)
    if transition:
        if not t_thick:
            s.text(transition, (P(0, y1)[0], P(0, y1)[1] + 3), T_N, "BOTTOM_LEFT")

    if jid and plano is not None:
        a = P(xr0 + root / 2 + 1, y1 - 0.5)
        if t_thick and t_thick > t + 0.1 and kind != "bevel":      # el chaflán y su cota van arriba a la derecha: el símbolo sube por encima
            plano.h.weld(jid, a, (ox + Wn * k + 12, a[1] + 50), sh=1, prep=f"{fm(angle, 0)}°")
        else:
            plano.h.weld(jid, a, (ox + Wn * k + 12, a[1] + 26), sh=1, prep=f"{fm(angle, 0)}°")


def tee_size(t, tw_):
    L = max(30.0, 1.6 * t)
    return (2 * L + min(tw_, 40.0), t + max(36.0, 1.8 * t) + 12.0), L


def prep_tee(s, ox, oy, k, t, tw_, jid=None, plano=None, root=2.0, angle=45.0):
    """Unión en T con bisel (B-07): plancha horizontal pasante de espesor t; pieza que apoya (cubo, pared tw_) vertical con bisel 45° en su canto
    exterior hasta la profundidad t, raíz y respaldo del lado interior. Se dibuja una porción de la pared (rotura) y de la plancha."""
    (Wn, Hn), L = tee_size(t, tw_)
    w_ = min(tw_, 40.0)
    P = lambda x, y: (ox + x * k, oy + y * k)
    H = max(36.0, 1.8 * t)
    _poly(s, [P(0, 0), P(Wn, 0), P(Wn, t), P(0, t)], 0.0)
    xr = L + w_                                    # cara exterior del cubo (derecha)
    hb = math.tan(math.radians(angle)) * (t - root)
    web = [P(L, t), P(xr, t), P(xr, t + root), P(xr - 0.0, t + root), P(xr, t + root), P(xr, t + root + 0.0)]
    web = [P(L, t), P(xr - hb, t), P(xr - hb, t + root), P(xr, t + root + hb), P(xr, t + H), P(L, t + H)]
    _poly(s, web, 90.0)
    _poly(s, [P(L - 8, t), P(L, t), P(L, t + 6), P(L - 8, t + 6)], 45.0, scale=0.3)          # respaldo interior
    s.dim(P(0, 0), P(0, t), -9, f"t = {fm(t, 0)} (plancha)", "v")
    s.dim(P(xr - hb, t), P(xr, t), -7, f"{fm(hb, 0)}", "h", outside=True)
    s.dim(P(xr, t), P(xr, t + root + hb), 9, f"{fm(t, 0)} (profundidad de la preparación = t)", "v")
    ap = P(xr, t + root)
    s.dim_ang(ap, (hb * k) * 0.55, 180 - angle - 0.0 + 0.0 if False else 90 + 0.0, 90 + angle, f"{fm(angle, 0)}°") if False else None
    s.leader(P(xr - hb, t + root * 0.5), (P(xr, 0)[0] + 10, P(0, -6)[1]), f"raíz {fm(root, 0)} mm", dot=True)
    s.leader(P(L - 4, t + 3), (P(L - 4, 0)[0] + 6, P(0, -6)[1] - 9), "respaldo interior (PROPUESTA)", dot=True)
    xa_, xb_, ym_ = P(L - 2, 0)[0], P(xr + 2, 0)[0], P(0, t + H)[1]
    xm_ = (xa_ + xb_) / 2
    s.pline([(xa_, ym_), (xm_ - 2.5, ym_), (xm_ - 0.8, ym_ + 2.2), (xm_ + 0.8, ym_ - 2.2), (xm_ + 2.5, ym_), (xb_, ym_)], "FINA")
    s.text("cubo (pared " + fm(tw_, 0) + ")", (P(L + w_ / 2, 0)[0], P(0, t + H * 0.6)[1]), T_N, "MIDDLE_CENTER")
    if jid and plano is not None:
        a = P(xr - hb * 0.4, t + root + hb * 0.4)
        plano.h.weld(jid, a, (ox + Wn * k + 12, a[1] + 26), sh=1, prep=f"{fm(angle, 0)}°")


def fillet_size(z, t1, t2):
    L = max(24.0, 3.0 * z)
    return (2 * L + t1, t2 + max(26.0, 4.5 * z) + 4.0), L


def prep_fillet(s, ox, oy, k, z, t1, t2, jid=None, plano=None, both=True, tag="", lab1=None, edge=False):
    """Filete en T: plancha vertical t1 sobre plancha horizontal t2, catetos z, garganta a = 0,707 z.
    edge=True: la plancha vertical queda a ras del canto de la horizontal (cara exterior coplanar, B-08): la horizontal solo se dibuja del lado del filete."""
    (Wn, Hn), L = fillet_size(z, t1, t2)
    Hh = max(26.0, 4.5 * z)
    xc = L + t1 / 2
    P = lambda x, y: (ox + x * k, oy + y * k)
    x_b0 = xc - t1 / 2 if edge else 0.0
    base = [P(x_b0, 0), P(Wn, 0), P(Wn, t2), P(x_b0, t2)]
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
    # garganta: trazo fino desde la raíz hasta la cara del cordón y llamada fuera del contorno y del achurado (B-48)
    gm = P(xe + z / 2, t2 + z / 2)
    s.line(P(xe, t2), gm, "FINA")
    qa = (P(xe + z, 0)[0] + 9 + 12, gm[1])
    s.leader(gm, qa, f"a = {fm(z * 0.7071, 1)}", dot=True)
    s.dim(P(x_b0, 0), P(x_b0, t2), -9, f"t = {fm(t2, 0)}", "v")
    if edge:
        s.text("canto de la plancha (cara exterior coplanar)", (P(x_b0, 0)[0] - 3, P(0, -3)[1]), T_N, "TOP_LEFT")
    s.dim(P(xc - t1 / 2, t2 + Hh), P(xc + t1 / 2, t2 + Hh), 8, lab1 or f"t = {fm(t1, 0)}", "h", outside=True)
    # rotura de la pieza vertical dibujada parcialmente (ISO 128-30)
    xa_, xb_, ym_ = P(xc - t1 / 2 - 2, 0)[0], P(xc + t1 / 2 + 2, 0)[0], P(0, t2 + Hh)[1]
    xm_ = (xa_ + xb_) / 2
    s.pline([(xa_, ym_), (xm_ - 2.5, ym_), (xm_ - 0.8, ym_ + 2.2), (xm_ + 0.8, ym_ - 2.2), (xm_ + 2.5, ym_), (xb_, ym_)], "FINA")
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


def tc_size(w):
    t, tp = w["t_alma"], w["t_plancha"]
    if w.get("pjp"):
        return (w["t_plancha"] + 50.0 + 20.0, w["t_alma"] + 46.0)
    return (2 * max(30.0, 1.4 * t) + t, tp + t + 3.0 + 42.0)


def prep_tc(s, ox, oy, k, w, jid=None, plano=None, angle=45.0):
    """Juntas del soporte del ojal E (núcleo: soporte_E.juntas). CJP TC-U4b (AWS D1.1:2020 Figura 5.1): pieza vertical de espesor t sobre la plancha de espesor tp,
    bisel simple 45° en todo el espesor del lado interior, abertura de raíz 3, resanado de raíz y pasada de cierre del lado exterior, filete de refuerzo z
    en el rincón interior. PJP TC-P4 (Fig. 5.2): tapa horizontal entre las paredes con bisel 45° de profundidad S desde arriba (garganta E), filete de
    refuerzo z sobre el bisel y sin soldadura por debajo."""
    P = lambda x, y: (ox + x * k, oy + y * k)
    t, tp, zr = w["t_alma"], w["t_plancha"], w.get("refuerzo", 0.0)
    Wn, Hn = tc_size(w)
    if w.get("pjp"):
        S_, E_ = w["pjp"]
        t, tp = w["t_plancha"], w["t_alma"]               # pared vertical (t) y tapa biselada (tp)
        xw = 50.0                                         # cara de la pared (a la derecha la pared vertical de espesor t)
        yb = 20.0                                         # cara inferior de la tapa
        _poly(s, [P(xw, 0), P(xw + t, 0), P(xw + t, Hn), P(xw, Hn)], 90.0)
        tapa = [P(0, yb), P(xw, yb), P(xw, yb + tp - S_), P(xw - S_, yb + tp), P(0, yb + tp)]
        _poly(s, tapa, 0.0)
        s.dim(P(0, yb), P(0, yb + tp), -8, f"{fm(tp, 0)} (tapa)", "v")
        s.dim(P(xw, yb + tp - S_), P(xw, yb + tp), 8, f"S = {fm(S_, 0)}", "v", outside=True)
        xr_ = ox + Wn * k + 4
        s.leader(P(xw - S_ * 0.5, yb + tp - S_ * 0.5), (xr_, oy + Hn * k * 0.55), f"bisel {fm(angle, 0)}°; garganta E = {fm(E_, 0)}", dot=True)
        s.leader(P(xw - zr * 0.3, yb + tp + zr * 0.3), (xr_, oy + Hn * k * 0.35), f"filete de refuerzo z{fm(zr, 0)}", dot=True)
        s.leader(P(xw - 6, yb), (xr_, oy + Hn * k * 0.15), "sin soldadura por debajo", dot=True)
        s.text(f"pared (t = {fm(t, 0)})", (P(xw + t / 2, 0)[0], P(0, Hn - 4)[1]), T_N, "TOP_CENTER")
        if jid and plano is not None:
            a = P(xw - S_ * 0.3, yb + tp - S_ * 0.3)
            plano.h.weld(jid, a, (ox + Wn * k + 10, oy + Hn * k + 14), sh=1, prep=f"{fm(angle, 0)}°")
        return
    L = max(30.0, 1.4 * t)
    R = 3.0
    _poly(s, [P(0, 0), P(Wn, 0), P(Wn, tp), P(0, tp)], 0.0)
    x0, x1 = L, L + t                                     # cara interior (izquierda) y exterior (derecha) de la pieza vertical
    web = [P(x1, tp + R), P(x1, tp + R + t + 30), P(x0, tp + R + t + 30), P(x0, tp + R + t)]
    _poly(s, web, 90.0)
    s.dim(P(0, 0), P(0, tp), -8, f"{fm(tp, 0)}", "v")
    s.dim(P(x0, tp + R + t + 30), P(x1, tp + R + t + 30), 6, f"t = {fm(t, 0)}", "h")
    s.dim(P(x1, tp), P(x1, tp + R), 8, f"{fm(R, 0)} (raíz)", "v", outside=True)
    xr_ = ox + Wn * k + 4
    s.leader(P(x0 + t * 0.5, tp + R + t * 0.5), (xr_, oy + Hn * k * 0.55), f"bisel {fm(angle, 0)}° en todo el espesor (interior)", dot=True)
    s.leader(P(x0 - zr * 0.3, tp + zr * 0.3), (xr_, oy + Hn * k * 0.35), f"filete de refuerzo z{fm(zr, 0)} (interior)", dot=True)
    s.leader(P(x1 + 1, tp + 1), (xr_, oy + Hn * k * 0.15), "resanado + pasada de cierre (exterior)", dot=True)
    if jid and plano is not None:
        a = P(x0 + t * 0.35, tp + R + t * 0.65)
        plano.h.weld(jid, a, (ox + Wn * k + 10, oy + Hn * k + 14), sh=1, prep=f"{fm(angle, 0)}°")




def ref_size(R):
    """Recuadro natural del detalle combinado del refuerzo (modelo, mm): base + refuerzo con la PJP exterior, un tapón y el filete interior."""
    d, S_, z = R["d"], R["S"], R["z"]
    xh = S_ + 28.0 + d / 2
    xi = xh + d / 2 + 34.0
    return (xi + z + 34.0, R["tb"] + R["td"] + 16.0), (xh, xi)


def prep_refuerzo(s, ox, oy, k, R, plano=None, ids=()):
    """Refuerzo cuadrado soldado sobre la base (núcleo d537dda): sección perpendicular a un canto exterior por la fila de tapones. A la izquierda el canto
    exterior (al ras del canto de la base) con la PJP J-R3 en bisel 45° (S/E) esmerilada al ras; al centro un tapón J-R1 (agujero Ø d, relleno parcial);
    a la derecha el borde interior con el filete J-R2 z. La base de t_base sigue entera (rotura a la derecha)."""
    tb, td, d, rel, S_, E_, z = R["tb"], R["td"], R["d"], R["rel"], R["S"], R["E"], R["z"]
    (Wn, Hn), (xh, xi) = ref_size(R)
    P = lambda x, y: (ox + x * k, oy + y * k)
    y0 = 4.0
    yb, yt = y0 + tb, y0 + tb + td
    _poly(s, [P(0, y0), P(Wn, y0), P(Wn, yb), P(0, yb)], 0.0)
    _poly(s, [P(S_, yb), P(xh - d / 2, yb), P(xh - d / 2, yt), P(0, yt), P(0, yb + S_)], 90.0)
    _poly(s, [P(xh + d / 2, yb), P(xi, yb), P(xi, yt), P(xh + d / 2, yt)], 90.0)
    pjp = [P(0, yb), P(S_, yb), P(0, yb + S_)]
    _poly(s, pjp, solid=True); s.pline(pjp, "VIS", closed=True)
    tap = [P(xh - d / 2, yb), P(xh + d / 2, yb), P(xh + d / 2, yb + rel), P(xh - d / 2, yb + rel)]
    _poly(s, tap, solid=True); s.pline(tap, "VIS", closed=True)
    fil = [P(xi, yb), P(xi + z, yb), P(xi, yb + z)]
    _poly(s, fil, solid=True); s.pline(fil, "VIS", closed=True)
    s.line(P(xh, y0 - 3), P(xh, yt + 4), "EJE")
    # rotura de la base a la derecha (ISO 128-30)
    xa_, ya_, yb_ = P(Wn, 0)[0], P(0, y0 - 1)[1], P(0, yb + 1)[1]
    ym_ = (ya_ + yb_) / 2
    s.pline([(xa_, ya_), (xa_, ym_ - 2.5), (xa_ + 2.2, ym_ - 0.8), (xa_ - 2.2, ym_ + 0.8), (xa_, ym_ + 2.5), (xa_, yb_)], "FINA")
    # cotas
    s.dim(P(0, y0), P(0, yb), -9, f"{fm(tb, 0)}", "v")
    s.dim(P(0, yb), P(0, yt), -9, f"{fm(td, 0)}", "v")
    s.dim(P(xh - d / 2, yt), P(xh + d / 2, yt), 7, f"Ø{fm(d, 0)}", "h")
    s.dim(P(S_, yb), P(S_, yb + S_), 6, f"S = {fm(S_, 0)}", "v", outside=True)
    s.dim(P(xi + z, yb), P(xi + z, yb + z), 8, f"z = {fm(z, 0)}", "v", outside=True)
    s.leader(P(S_ * 0.5, yb + S_ * 0.2), (P(S_, 0)[0] + 6, oy - 6), f"PJP bisel 45° × {fm(S_, 0)}, E = {fm(E_, 0)}: canto al ras del canto de la base, esmerilado", dot=True)
    s.leader(P(xh, yb + rel * 0.5), (P(xh, 0)[0] + 10, oy - 16), f"tapón: relleno {fm(rel, 1)} de {fm(td, 0)}, por capas", dot=True)
    if plano is not None:
        idmap = dict(ids)
        if idmap.get("J-R3"):
            a = P(S_ * 0.25, yb + S_ * 0.25)
            plano.h.weld("J-R3", a, (ox - 8, oy + (yt + 14) * k), sh=-1, prep="45°")
        if idmap.get("J-R1"):
            a = P(xh - d / 4, yb + rel)
            plano.h.weld("J-R1", a, (P(xh, 0)[0] - d / 2 * k - 8, oy + (yt + 14) * k + 26), sh=-1)
        if idmap.get("J-R2"):
            a = P(xi + z * 0.35, yb + z * 0.35)
            plano.h.weld("J-R2", a, (ox + Wn * k + 10, oy + (yt + 4) * k), sh=1)


def pin_size(R):
    return (R["d"] / 2 + R["S"] + 46.0, R["tpr"] + 24.0)


def prep_pasador(s, ox, oy, k, R, jid=None, plano=None):
    """J-P1 (núcleo pasadores_empuje.union): pasador Ø d a ras de la cara exterior del anillo, PJP con bisel 45° × S en el borde del agujero del anillo
    (toda la circunferencia), esmerilada a ras. Se dibuja el anillo superior (cara superior del disco); el anillo inferior es el espejo (cara inferior)."""
    r, S_, E_, tpr = R["d"] / 2, R["S"], R["E"], R["tpr"]
    Wn, Hn = pin_size(R)
    P = lambda x, y: (ox + x * k, oy + y * k)
    y0, y1 = 6.0, 6.0 + tpr
    xp = r                                  # pared del agujero (eje del pasador en x = 0)
    _poly(s, [P(0, y0 - 4), P(xp, y0 - 4), P(xp, y1), P(0, y1)], 0.0)
    _poly(s, [P(xp, y0), P(Wn, y0), P(Wn, y1), P(xp + S_, y1), P(xp, y1 - S_)], 90.0)
    tri = [P(xp, y1 - S_), P(xp + S_, y1), P(xp, y1)]
    _poly(s, tri, solid=True); s.pline(tri, "VIS", closed=True)
    s.line(P(0, y0 - 8), P(0, y1 + 6), "EJE")
    xa_ = P(0, 0)[0]
    s.pline([(xa_ - 1, P(0, y0 - 4)[1]), (P(xp + 1, 0)[0], P(0, y0 - 4)[1])], "FINA")
    s.dim(P(Wn, y0), P(Wn, y1), 8, f"{fm(tpr, 0)} (anillo)", "v")
    s.dim(P(xp, y1 - S_), P(xp, y1), -6, f"S = {fm(S_, 0)}", "v", outside=True)
    s.dim(P(0, y1), P(xp, y1), 6, f"R{fm(r, 1)} (Ø{fm(2 * r, 0)} m6)", "h")
    s.leader(P(xp + S_ * 0.3, y1 - S_ * 0.2), (ox + Wn * k + 6, oy + (y1 - S_ - 6) * k), f"E = {fm(E_, 0)}; esmerilada a ras", dot=True)
    s.text("pasador a ras de la cara superior del disco; ídem en el anillo inferior", (P(0, 0)[0], oy - 1), T_N, "TOP_LEFT")
    s.text("(cara inferior de la mesa, espejo), sin filete", (P(0, 0)[0], oy - 1 - T_N * 1.6), T_N, "TOP_LEFT")
    if jid and plano is not None:
        a = P(xp + S_ * 0.25, y1 - S_ * 0.25)
        plano.h.weld(jid, a, (ox + Wn * k + 12, a[1] + 22), sh=1, prep="45°", all_round=True)


# ------------------------------------------------------------------------------------------------
def add_prep(p, name, w, title=None, lv=(1, 1, 1, 1), t1=None, t2=None, both=True, mins=None, maxs=None, lab1=None, edge=False):
    """Agrega a la lámina p un esquema de junta correspondiente al registro de soldaduras w (dict de ctx.welds). Devuelve la especificación."""
    jid = w["id"]
    if w.get("en_T"):
        (Wn, Hn), _ = tee_size(w["t"], w["t_alma"])
        return p.vs(name, [], "top", nat=(Wn, Hn), lv=(2, 3, 2, 2), extra=(0, 0, 112, 0), mins=1.0, maxs=5.0, title=title or f"DETALLE {jid}: UNIÓN EN T CUBO–PLANCHA (bisel 45°, t = {fm(w['t'], 0)})",
                    custom=lambda s, ox, oy, k, pl: prep_tee(s, ox, oy, k, w["t"], w["t_alma"], jid, pl))
    if w.get("soporte_E") is not None:
        Wn, Hn = tc_size(w)
        tit = (f"DETALLE {jid}: PREPARACIÓN DE JUNTA (PJP TC-P4, S{fm(w['pjp'][0], 0)}/E{fm(w['pjp'][1], 0)} + z{fm(w['refuerzo'], 0)})" if w.get("pjp") else
               f"DETALLE {jid}: PREPARACIÓN DE JUNTA (CJP TC-U4b + z{fm(w['refuerzo'], 0)})")
        return p.vs(name, [], "top", nat=(Wn, Hn), lv=(2, 3, 2, 2), extra=(0, 0, 112, 0), mins=mins or 1.0, maxs=maxs or 5.0, title=title or tit,
                    custom=lambda s, ox, oy, k, pl: prep_tc(s, ox, oy, k, w, jid, pl))
    if w.get("pasador_j"):
        R = dict(w["pasador_j"], d=w["pasador_j"].get("d", 85.0), tpr=w["pasador_j"].get("tpr", 40.0))
        Wn, Hn = pin_size(R)
        return p.vs(name, [], "top", nat=(Wn, Hn), lv=(2, 3, 2, 2), extra=(0, 0, 112, 0), mins=mins or 1.0, maxs=maxs or 3.0,
                    title=title or f"DETALLE {jid}: PASADOR A RAS SOLDADO AL ANILLO (PJP BISEL 45° S{fm(R['S'], 0)}/E{fm(R['E'], 0)}, ESMERILADA A RAS)",
                    custom=lambda s, ox, oy, k, pl: prep_pasador(s, ox, oy, k, R, jid, pl))
    if w["groove"] and w["sym"] in ("V", "bevel"):
        t = w["t"]
        kind = "V" if w["sym"] == "V" else "bevel"
        ang = 60.0 if kind == "V" else 45.0
        root = 3.0 if "raíz 3" in w["prep"] else 2.0
        tT = w.get("t_thick")
        land = w.get("land")
        (Wn, Hn), _ = butt_size(t, kind, tT, land)
        tr = (f"transición 1:4 de {fm(t, 0)} a {fm(tT, 0)}; cara a ras del lado del respaldo" if tT else None)
        bk = w.get("backing_txt")
        nm = f"{jid}: junta {'a tope en V 60°' if kind == 'V' else 'con bisel 45°'}"
        return p.vs(name, [], "top", nat=(Wn, Hn), lv=(2, 3, 2, 2), extra=(0, 0, 112, 0), mins=1.0, maxs=5.0, title=title or f"DETALLE {jid}: PREPARACIÓN DE JUNTA ({'V 60°' if kind == 'V' else 'bisel 45°'}, t = {fm(t, 0)}" + (f" / {fm(tT, 0)}" if tT else "") + ")",
                    custom=lambda s, ox, oy, k, pl: prep_butt(s, ox, oy, k, t, jid, pl, kind, ang, root, 2.0, True, transition=tr, t_thick=tT, land=land, backing_txt=bk))
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
                custom=lambda s, ox, oy, k, pl: prep_fillet(s, ox, oy, k, z, t1, t2, jid, pl, both, lab1=lab1, edge=edge))
