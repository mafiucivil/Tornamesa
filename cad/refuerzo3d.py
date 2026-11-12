"""Refuerzo cuadrado soldado SOBRE la plancha base (doubler; núcleo d537dda, decisión del mandante 12-11-2026).

Reemplaza al inserto de esquina triangular a tope (BAS-018…023, CJP J-I1, ventanas en la base): la base de t_base queda ENTERA, sin ventanas,
al ras sobre la losa; en cada esquina se suelda encima una plancha cuadrada de t_d (lado a, un lado sobre cada borde de la base) con:
  - J-R1 tapones (AISC 360-22 §J2.3) en agujeros del refuerzo, relleno parcial (profundidad del núcleo);
  - J-R2 filete en los dos bordes interiores;
  - J-R3 PJP en bisel 45° (S/E) en los dos bordes exteriores, al ras de los cantos de la base;
  - J-R4 (si el núcleo lo exporta) atiesador tangencial t × h × largo a la esquina interior, soldado a la base con filete a ambos lados.
Modo pivotado: pivotado.fabricacion.soporte_E.refuerzo; modo guiado: levaGuiada.fabricacion.refuerzo («inserto» es alias en el núcleo).
Toda la geometría sale del JSON: cuadrado.vertices, t, t_d, z, tapones (d, profundidades, posiciones por esquina), filetes, atiesadores, juntas."""
import math
import cadquery as cq


def datos(g):
    """Refuerzo del núcleo para el modo del juego, o None si el núcleo no lo exporta."""
    if g.modo == 2:
        S = (g.FPV or {}).get("soporte_E") or {}
        I = S.get("refuerzo") or S.get("inserto")
    else:
        F = g.FLG or {}
        I = F.get("refuerzo") or F.get("inserto")
    if not I or not (I.get("cuadrado") or {}).get("vertices"):
        return None
    I = dict(I)
    I["esquinas"] = I["cuadrado"]["vertices"]
    return I


def _prism(pts, z0, h):
    return cq.Workplane("XY").workplane(offset=z0).polyline([tuple(p) for p in pts]).close().extrude(h)


def solido(I, i, tb):
    """Plancha del refuerzo de la esquina i (coordenadas de la tornamesa), de z = tb a z = t, con los agujeros de los tapones vacíos por encima del
    relleno (el relleno J-R1 es metal de aporte: va en el sólido como parte del refuerzo, igual que el núcleo cuenta la masa)."""
    t = float(I["t"])
    so = _prism(I["esquinas"][i], tb, t - tb)
    T = I.get("tapones") or {}
    pos = (T.get("posiciones") or [[]])[i]
    if pos:
        d = float(T["d"])
        rel = float(T.get("profundidad_relleno") or 0.0)
        h = t - tb - rel
        if h > 0.01:
            so = so.cut(cq.Workplane("XY").workplane(offset=tb + rel).pushPoints([tuple(q) for q in pos]).circle(d / 2).extrude(h + 1.0))
    S_ = bisel_S(I)
    if S_ > 0:
        # bisel 45° × S de la PJP J-R3 en la cara inferior de los cantos exteriores (la pieza tal como se corta; el cordón no se modela)
        B = 2 * max(abs(q[0]) for q in I["esquinas"][i])
        for (a_, b_, L_) in bordes_exteriores(I, i, B):
            if abs(a_[0] - b_[0]) < 1e-6:            # canto x = ±B/2
                sx = 1.0 if a_[0] > 0 else -1.0
                y0, y1 = min(a_[1], b_[1]), max(a_[1], b_[1])
                pr = (cq.Workplane("XZ").polyline([(a_[0] + sx, tb - 1), (a_[0] - sx * S_, tb - 1), (a_[0] - sx * S_, tb), (a_[0], tb + S_), (a_[0] + sx, tb + S_)]).close()
                      .extrude(-(y1 - y0 + 2)).translate((0, y0 - 1, 0)))
            else:                                       # canto y = ±B/2
                sy = 1.0 if a_[1] > 0 else -1.0
                x0, x1 = min(a_[0], b_[0]), max(a_[0], b_[0])
                pr = (cq.Workplane("YZ").polyline([(a_[1] + sy, tb - 1), (a_[1] - sy * S_, tb - 1), (a_[1] - sy * S_, tb), (a_[1], tb + S_), (a_[1] + sy, tb + S_)]).close()
                      .extrude(x1 - x0 + 2).translate((x0 - 1, 0, 0)))
            so = so.cut(pr)
    return so.clean()


def bisel_S(I):
    return float(((I.get("filetes") or {}).get("bordes_exteriores_PJP") or {}).get("S", 0.0) or 0.0)


def vol_bisel(I):
    """Volumen del bisel de la PJP por refuerzo (mm³): lo llena el cordón J-R3; el núcleo cuenta la plancha llena."""
    S_ = bisel_S(I)
    a = float(I["lado"])
    return S_ * S_ / 2 * 2 * a - S_ ** 3 / 3


def solido_atiesador(I, i):
    """Atiesador tangencial de la esquina i (polígono en planta del núcleo, de z0 a z1), o None."""
    A = I.get("atiesadores") or {}
    pe = A.get("por_esquina") or []
    if i >= len(pe):
        return None
    z0, z1 = A["z"]
    return _prism(pe[i]["poligono"], float(z0), float(z1) - float(z0))


def esquina_de(I, pt):
    """Índice de la esquina cuyo cuadrado contiene el punto en planta, o None."""
    from shapely.geometry import Polygon, Point
    for i, pol in enumerate(I["esquinas"]):
        if Polygon(pol).buffer(0.5).contains(Point(pt)):
            return i
    return None


def z_cara(I, pt, tb):
    """Cota de la cara superior en planta: t sobre el refuerzo, tb fuera."""
    return float(I["t"]) if esquina_de(I, pt) is not None else tb


def apoyo(I, huella, tb):
    """Apoyo de una pieza soldada sobre el refuerzo: huella en planta (shapely). Devuelve (esquina, fracción sobre el refuerzo, cota mínima de la cara
    bajo la huella, distancia máxima de la huella fuera del refuerzo)."""
    from shapely.geometry import Polygon, Point
    for i, pol in enumerate(I["esquinas"]):
        C = Polygon(pol)
        if not huella.intersects(C):
            continue
        fr = huella.intersection(C).area / huella.area
        fuera = huella.difference(C)
        dmax = 0.0
        if not fuera.is_empty:
            for g_ in getattr(fuera, "geoms", [fuera]):
                for q in g_.exterior.coords:
                    dmax = max(dmax, C.exterior.distance(Point(q)))
        return i, fr, (float(I["t"]) if fr > 0.999 else tb), dmax
    return None, 0.0, tb, 0.0


def tramos_marco(I, B, extra=50.0):
    """Tramos del borde de la base ocupados por cada refuerzo (más «extra» mm más allá del extremo del lado, núcleo marco_interrupcion):
    [(borde, (x0, y0), (x1, y1))] con borde en {'x+', 'x-', 'y+', 'y-'}."""
    out = []
    h = B / 2
    for pol in I["esquinas"]:
        for lado, idx, val in (("x+", 0, h), ("x-", 0, -h), ("y+", 1, h), ("y-", 1, -h)):
            on = [q for q in pol if abs(q[idx] - val) < 1e-6]
            if len(on) < 2:
                continue
            o = 1 - idx
            a, b = min(q[o] for q in on), max(q[o] for q in on)
            a = a - extra if a > -h + 1e-6 else a
            b = b + extra if b < h - 1e-6 else b
            p0 = (val, a) if idx == 0 else (a, val)
            p1 = (val, b) if idx == 0 else (b, val)
            out.append((lado, p0, p1))
    return out


def _bordes(I, i, B, sobre_borde):
    pol = I["esquinas"][i]
    h = B / 2
    out = []
    for a, b in zip(pol, pol[1:] + pol[:1]):
        sobre = (abs(a[0] - b[0]) < 1e-6 and abs(abs(a[0]) - h) < 1e-6) or (abs(a[1] - b[1]) < 1e-6 and abs(abs(a[1]) - h) < 1e-6)
        if sobre == sobre_borde:
            out.append((tuple(a), tuple(b), math.dist(a, b)))
    return out


def bordes_interiores(I, i, B):
    """Lados del cuadrado que NO están sobre el borde de la base (llevan el filete J-R2): [(p0, p1, largo)]."""
    return _bordes(I, i, B, False)


def bordes_exteriores(I, i, B):
    """Lados del cuadrado sobre los bordes de la base (llevan la PJP J-R3 en bisel, al ras): [(p0, p1, largo)]."""
    return _bordes(I, i, B, True)


def transformacion(I, i):
    """Transformación que lleva la esquina 0 a la esquina i, incluido el patrón de tapones: 'id', 'rot' (180°), 'esp' (y → −y), 'esprot' (x → −x)."""
    def key(j, fn=lambda x, y: (x, y)):
        C = {(round(fn(*q)[0], 2), round(fn(*q)[1], 2)) for q in I["esquinas"][j]}
        T = {(round(fn(*q)[0], 2), round(fn(*q)[1], 2)) for q in ((I.get("tapones") or {}).get("posiciones") or [[]] * (j + 1))[j]}
        return C, T
    Ci = key(i)
    for nm, fn in (("id", lambda x, y: (x, y)), ("rot", lambda x, y: (-x, -y)), ("esp", lambda x, y: (x, -y)), ("esprot", lambda x, y: (-x, y)),
                   ("diag", lambda x, y: (-y, -x)), ("rot90", lambda x, y: (-y, x)), ("rot270", lambda x, y: (y, -x)), ("diag2", lambda x, y: (y, x))):
        if key(0, fn) == Ci:
            return nm
    raise ValueError(f"refuerzo: la esquina {i} no es imagen de la esquina 0")
