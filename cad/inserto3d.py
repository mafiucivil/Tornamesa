"""Inserto de esquina de la plancha base (núcleo e9a0eb3, decisión del mandante 10-11-2026).

Modo 2 (pivotado): un inserto bajo cada soporte del ojal E (pivotado.fabricacion.soporte_E.inserto).
Modo 1 (guiado): uno bajo cada ménsula del ojal trasero (levaGuiada.fabricacion.inserto).
Toda la geometría sale del JSON del núcleo: contorno de cada esquina («esquinas», coordenadas de la tornamesa), contorno del espesor pleno
(«esquinas_espesor_pleno»: la cara superior baja con pendiente 1:2,5 desde ese contorno hasta el contorno exterior, a la altura de la cara
superior de la base), espesor t, rebaje local de la cara superior (rebaje.poligonos a z_cara, borde a 1:2,5) y juntas (J-I1).
El inserto va al ras por debajo con la base: la plancha base lleva una ventana con el contorno «esquinas» en cada esquina."""
import math
import cadquery as cq

PEND = 2.5                      # transición 1:2,5 (núcleo: transicion.pendiente; se verifica contra el texto del JSON)


def datos(g):
    """Diccionario del inserto del núcleo para el modo del juego, o None si el núcleo no lo exporta (ins_on = 0)."""
    if g.modo == 2:
        I = ((g.FPV or {}).get("soporte_E") or {}).get("inserto")
    else:
        I = (g.FLG or {}).get("inserto")
    if not I or not I.get("esquinas"):
        return None
    pd = str((I.get("transicion") or {}).get("pendiente", "1:2,5")).replace(",", ".")
    try:
        k = float(pd.split(":")[1])
    except Exception:
        k = PEND
    I = dict(I)
    I["_k"] = k
    return I


def _wire(pts, z):
    vs = [cq.Vector(x, y, z) for x, y in pts]
    return cq.Wire.makePolygon(vs + [vs[0]])


def _prism(pts, z0, h):
    return cq.Workplane("XY").workplane(offset=z0).polyline([tuple(p) for p in pts]).close().extrude(h)


def _simplificar(pts, tol=0.05):
    """Polígono del rebaje (envolvente convexa del barrido, ~250 vértices casi alineados): se eliminan los vértices a menos de tol mm de la cuerda
    (la geometría CNC sale del JSON; el modelo 3D difiere < tol)."""
    try:
        from shapely.geometry import Polygon
        q = Polygon(pts).simplify(tol, preserve_topology=True)
        out = list(q.exterior.coords)[:-1]
        return out if len(out) >= 3 else pts
    except Exception:
        return pts


def esquina_de(I, pt):
    """Índice de la esquina (polígono «esquinas») que contiene el punto en planta, o None."""
    from shapely.geometry import Polygon, Point
    for i, pol in enumerate(I["esquinas"]):
        if Polygon(pol).buffer(0.5).contains(Point(pt)):
            return i
    return None


def rebajes_de(I, i):
    """Polígonos del rebaje que caen sobre la esquina i (asignados por intersección con su contorno)."""
    R = I.get("rebaje") or {}
    if not R.get("poligonos"):
        return []
    from shapely.geometry import Polygon
    C = Polygon(I["esquinas"][i])
    return [pl for pl in R["poligonos"] if Polygon(pl).intersects(C)]


def _semiespacio(P0, n, L=8000.0):
    """Sólido grande del lado n (normal saliente hacia el material que se quita) del plano que pasa por P0."""
    nx, ny, nz = n
    ax = (1.0, 0.0, 0.0) if abs(nx) < 0.9 else (0.0, 1.0, 0.0)
    # xDir perpendicular a n
    d = ax[0] * nx + ax[1] * ny + ax[2] * nz
    nn = math.sqrt(nx * nx + ny * ny + nz * nz)
    xd = (ax[0] - d * nx / nn ** 2, ax[1] - d * ny / nn ** 2, ax[2] - d * nz / nn ** 2)
    pl = cq.Plane(origin=P0, xDir=xd, normal=(nx, ny, nz))
    return cq.Workplane(pl).rect(2 * L, 2 * L).extrude(L)


def _canonico(I, B, tb):
    """Inserto en el marco canónico de la esquina (+B/2; −B/2) (núcleo: insPoly con los parámetros desplazados s = k·(z − t_base)):
    cara superior = t_base + mín(Δ; d/k), con d la distancia a la hipotenusa (X − Y ≥ c) y la «distancia» a cada muesca
    (lado x: máx(a − X; b − Y); lado y: máx(X − a'; Y − b')). Biseles planos: coinciden con «esquinas» a z = t_base y con «esquinas_espesor_pleno» a z = t."""
    k, t = I["_k"], float(I["t"])
    h = B / 2
    C0 = I["esquinas"][0]
    bot = _prism(C0, 0.0, tb)
    top = cq.Workplane("XY").box(B, B, t - tb, centered=(True, True, False)).translate((0, 0, tb))
    c = float(I["hipotenusa_dist_centro"]) * math.sqrt(2.0)
    top = top.cut(_semiespacio((c / 2, -c / 2, tb), (-1.0, 1.0, math.sqrt(2.0) * k)))
    M = I.get("muescas") or {}
    if M.get("lado_x"):
        a, b = M["lado_x"]["a"], M["lado_x"]["b"]
        w = _semiespacio((a, 0.0, tb), (1.0, 0.0, k)).intersect(_semiespacio((0.0, b, tb), (0.0, 1.0, k)))
        top = top.cut(w)
    if M.get("lado_y"):
        a, b = M["lado_y"]["a"], M["lado_y"]["b"]
        w = _semiespacio((a, 0.0, tb), (-1.0, 0.0, k)).intersect(_semiespacio((0.0, b, tb), (0.0, -1.0, k)))
        top = top.cut(w)
    return bot.union(top).clean()


def _transformacion(I, i):
    """Transformación que lleva la esquina canónica (0) a la esquina i: 'id', 'rot' (180°), 'esp' (simetría y → −y), 'esprot' (x → −x)."""
    C0 = [tuple(q) for q in I["esquinas"][0]]
    Ci = {(round(q[0], 3), round(q[1], 3)) for q in I["esquinas"][i]}
    for nm, fn in (("id", lambda x, y: (x, y)), ("rot", lambda x, y: (-x, -y)), ("esp", lambda x, y: (x, -y)), ("esprot", lambda x, y: (-x, y))):
        if {(round(fn(*q)[0], 3), round(fn(*q)[1], 3)) for q in C0} == Ci:
            return nm
    raise ValueError(f"inserto: la esquina {i} no es imagen de la esquina canónica")


def solido(I, i, tb, B=None, _cache={}):
    """Sólido del inserto de la esquina i (coordenadas de la tornamesa), con el rebaje local de la cara superior (borde a 1:k)."""
    if B is None:
        B = 2 * max(abs(q[0]) for q in I["esquinas"][0])
    key = (id(I), round(tb, 3))
    if key not in _cache:
        _cache.clear()
        _cache[key] = _canonico(I, B, tb)
    so = _cache[key]
    tr = _transformacion(I, i)
    if tr == "rot":
        so = so.rotate((0, 0, 0), (0, 0, 1), 180)
    elif tr == "esp":
        so = so.mirror("XZ")
    elif tr == "esprot":
        so = so.mirror("YZ")
    t = float(I["t"])
    R = I.get("rebaje") or {}
    for pl in rebajes_de(I, i):
        zc = float(R["z_cara"])
        h = t - zc + 1.0
        ang = math.degrees(math.atan(I["_k"]))
        pts = _simplificar(pl)
        try:
            cut = cq.Workplane("XY").workplane(offset=zc).polyline([tuple(p) for p in pts]).close().extrude(h, taper=-ang)
            so2 = so.cut(cut)
            if so2.val().isValid():
                so = so2
                continue
        except Exception:
            pass
        so = so.cut(_prism(pts, zc, h))          # respaldo: borde vertical
    return so.clean()


def z_cara(I, pt, tb):
    """Cota de la cara superior del inserto en planta (sin rebaje): t dentro del espesor pleno, lineal en la transición, tb fuera."""
    from shapely.geometry import Polygon, Point
    i = esquina_de(I, pt)
    if i is None:
        return tb
    Pl = Polygon(I["esquinas_espesor_pleno"][i])
    P_ = Point(pt)
    if Pl.buffer(1e-6).contains(P_):
        return float(I["t"])
    d = Pl.exterior.distance(P_)
    return max(tb, float(I["t"]) - d / I["_k"])


def apoyo(I, huella, tb):
    """Apoyo de una pieza soldada sobre el inserto: huella en planta (shapely). Devuelve (esquina, fracción sobre el espesor pleno, cota mínima de la cara
    bajo la huella, distancia máxima de la huella fuera del espesor pleno)."""
    from shapely.geometry import Polygon
    for i, pol in enumerate(I["esquinas"]):
        C = Polygon(pol)
        if not huella.intersects(C):
            continue
        Pl = Polygon(I["esquinas_espesor_pleno"][i])
        fr = huella.intersection(Pl).area / huella.area
        fuera = huella.difference(Pl)
        dmax = 0.0
        if not fuera.is_empty:
            for g_ in getattr(fuera, "geoms", [fuera]):
                for q in g_.exterior.coords:
                    dmax = max(dmax, Pl.exterior.distance(__import__("shapely.geometry", fromlist=["Point"]).Point(q)))
        zmin = max(tb, float(I["t"]) - dmax / I["_k"])
        return i, fr, zmin, dmax
    return None, 0.0, tb, 0.0


def tramos_marco(I, B, extra=50.0):
    """Tramos del borde de la base ocupados por cada inserto (más «extra» mm más allá del extremo del cateto, núcleo marco_interrupcion):
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
            # se prolonga «extra» hacia el interior del borde (el extremo en la esquina de la base queda en ±B/2)
            a = a - extra if a > -h + 1e-6 else a
            b = b + extra if b < h - 1e-6 else b
            p0 = (val, a) if idx == 0 else (a, val)
            p1 = (val, b) if idx == 0 else (b, val)
            out.append((lado, p0, p1))
    return out


def bordes_interiores(I, i, B):
    """Aristas del contorno de la esquina i que NO están sobre el borde de la base (llevan la junta J-I1 y la transición): [(p0, p1, largo)]."""
    pol = I["esquinas"][i]
    h = B / 2
    out = []
    for a, b in zip(pol, pol[1:] + pol[:1]):
        sobre = (abs(a[0] - b[0]) < 1e-6 and abs(abs(a[0]) - h) < 1e-6) or (abs(a[1] - b[1]) < 1e-6 and abs(abs(a[1]) - h) < 1e-6)
        if not sobre:
            out.append((tuple(a), tuple(b), math.dist(a, b)))
    return out
