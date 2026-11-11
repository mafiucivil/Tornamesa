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




def x_size(w):
    I = w["inserto"]
    Lh = 40.0
    return (Lh + 3.0 + I["ancho"] + 40.0, I["t"] + 34.0), Lh


def prep_x(s, ox, oy, k, w, jid=None, plano=None, angle=60.0, root=3.0, face=3.0):
    """J-I1 (núcleo: inserto.juntas): CJP a tope en doble V (X) entre la plancha base (t_base, izquierda) y el inserto de esquina (derecha), al ras por
    debajo. La X se reparte en el espesor de la base (los dos al ras abajo; en el borde de la junta el inserto también tiene t_base: allí arranca la
    transición 1:k de la cara superior, que llega al espesor pleno t a k·Δ del borde). Resanado de raíz por la cara inferior y amolado al ras."""
    I = w["inserto"]
    tb, T, kk, A = I["tb"], I["t"], I["k"], I["ancho"]
    # preparación del núcleo (inserto.juntas[].preparacion, B-U3b): raíz, talón y ángulo; los argumentos quedan como respaldo
    angle, root, face = I.get("alfa", angle), I.get("raiz", root), I.get("talon", face)
    (Wn, Hn), Lh = x_size(w)
    P = lambda x, y: (ox + x * k, oy + y * k)
    y0 = 8.0
    d = (tb - face) / 2.0                     # profundidad de cada V
    hb = math.tan(math.radians(angle / 2)) * d
    xr0, xr1 = Lh, Lh + root
    left = [P(0, y0), P(xr0 - hb, y0), P(xr0, y0 + d), P(xr0, y0 + d + face), P(xr0 - hb, y0 + tb), P(0, y0 + tb)]
    xe = xr1 + A + 40.0
    # cara superior del inserto: del borde de la junta (z = tb) al espesor pleno (z = T) en A = k·Δ
    tau = math.tan(math.radians(angle / 2))
    u = d * tau / (1.0 - tau / kk)              # el bisel superior corta la pendiente de la transición
    right = [P(xr1 + hb, y0), P(xe, y0), P(xe, y0 + T), P(xr1 + A, y0 + T), P(xr1 + u, y0 + tb + u / kk), P(xr1, y0 + d + face), P(xr1, y0 + d)]
    _poly(s, left, 0.0)
    _poly(s, right, 90.0)
    s.line(P(0, y0), P(xe, y0), "FINA")
    s.dim(P(0, y0), P(0, y0 + tb), -9, f"t = {fm(tb, 0)} (base)", "v")
    s.dim(P(xe, y0), P(xe, y0 + T), 8, f"t = {fm(T, 0)} (inserto)", "v")
    s.dim(P(xr1, y0 + T), P(xr1 + A, y0 + T), 8, f"{fm(A, 0)} = {fm(kk, 1)}·Δ (transición 1:{fm(kk, 1)})", "h")
    s.dim(P(xr0, y0 + tb + 2), P(xr1, y0 + tb + 2), 10, f"R = 0–{fm(root, 0)}", "h", outside=True)
    apex = P((xr0 + xr1) / 2, y0 + d + face)
    s.dim_ang(apex, d * k * 0.6, 90 - angle / 2, 90 + angle / 2, f"α = {fm(angle, 0)}°")
    apex2 = P((xr0 + xr1) / 2, y0 + d)
    s.dim_ang(apex2, d * k * 0.6, 270 - angle / 2, 270 + angle / 2, f"β = {fm(I.get('beta', angle), 0)}°")
    xl_ = ox - 4
    s.leader(P(xr0, y0 + d + face / 2), (xl_ - 30, oy + (y0 + tb / 2) * k - 18), f"talón f = 0–{fm(face, 0)}", dot=True)
    s.leader(P((xr0 + xr1) / 2, y0), (P(xr0, 0)[0] + 20, oy - 6), "resanado de raíz por la cara inferior; amolar al ras (apoyo en la losa)", dot=True)
    s.leader(P(xr1 + A * 0.3, y0 + tb + A * 0.3 / kk), (P(xr1 + A * 0.3, 0)[0] + 25, oy + (y0 + T) * k + 22), f"cara superior del inserto: pendiente 1:{fm(kk, 1)} desde el borde de la junta", dot=True)
    if jid and plano is not None:
        a = P(xr0 + root / 2, y0 + tb - 0.5)
        plano.h.weld(jid, a, (ox + 10, oy + (y0 + T + 12) * k), sh=-1, prep=f"{fm(angle, 0)}°")

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
    if w.get("inserto"):
        (Wn, Hn), _ = x_size(w)
        return p.vs(name, [], "top", nat=(Wn, Hn), lv=(2, 3, 2, 2), extra=(0, 0, 112, 0), mins=mins or 0.5, maxs=maxs or 2.0,
                    title=title or f"DETALLE {jid}" + (f" ({w['inserto']['designacion']})" if w["inserto"].get("designacion") else "") + f": CJP A TOPE EN DOBLE V, BASE {fm(w['inserto']['tb'], 0)} / INSERTO {fm(w['inserto']['t'], 0)} (TRANSICIÓN 1:{fm(w['inserto']['k'], 1)})",
                    custom=lambda s, ox, oy, k, pl: prep_x(s, ox, oy, k, w, jid, pl))
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
