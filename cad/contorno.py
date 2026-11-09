"""Contorno de la placa-leva (modo pivotado) leído del JSON del núcleo.

Formato geométrico esperado (rediseño del núcleo: perfil curvo, continuo y suave tipo KIET), por instancia de placa:
  instancias[k]["segmentos"] = [
     {"tipo": "recta", "p0": [x, y], "p1": [x, y]},
     {"tipo": "arco",  "p0": [x, y], "p1": [x, y], "centro": [x, y], "r": R, "sentido": "ccw" | "cw"},
     {"tipo": "curva" | "transicion" | "clotoide" | "spline", "p0": [x, y], "p1": [x, y], "puntos": [[x, y], ...]   (puntos de paso, extremos incluidos)}
  ]  (contorno cerrado, segmentos consecutivos y tangentes; coordenadas de la tornamesa)
Sin «segmentos», se usa el polígono «contorno» actual (provisional: la lámina queda RETENIDA).
El dibujo usa entidades DXF ARC / SPLINE / LINE (no polilínea densa); las tablas dan centro, radio y puntos de tangencia."""
import math
import cadquery as cq

TIPOS_CURVA = ("curva", "transicion", "clotoide", "spline")


def leer(ins):
    segs = ins.get("segmentos")
    if segs:
        out = []
        for s in segs:
            t = s.get("tipo", "recta")
            d = dict(tipo=t, p0=tuple(s["p0"]), p1=tuple(s["p1"]))
            if t == "arco":
                d.update(centro=tuple(s["centro"]), r=float(s["r"]), sentido=s.get("sentido", "ccw"))
            elif t in TIPOS_CURVA:
                d.update(puntos=[tuple(q) for q in s.get("puntos", [s["p0"], s["p1"]])])
            out.append(d)
        return out
    return [dict(tipo="poligono", puntos=[tuple(q) for q in ins["contorno"]])]


def geometrico(segs):
    return all(s["tipo"] != "poligono" for s in segs)


def marco_placa(ins):
    """Marco local de la placa: origen en el primer perno, x hacia el último perno."""
    p0, p1 = ins["pernos"][0], ins["pernos"][-1]
    a = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    return (p0[0], p0[1], a)


def pt_local(q, T):
    x, y = q[0] - T[0], q[1] - T[1]
    c, s = math.cos(-T[2]), math.sin(-T[2])
    return (x * c - y * s, x * s + y * c)


def a_local(so, T):
    return so.translate(cq.Vector(-T[0], -T[1], 0)).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -math.degrees(T[2]))


def _ang(c, p):
    return math.degrees(math.atan2(p[1] - c[1], p[0] - c[0]))


def solido(segs, z0, h):
    """Placa extruida desde los segmentos (rectas, arcos por tres puntos, curvas por spline de puntos de paso)."""
    s0 = segs[0]
    if s0["tipo"] == "poligono":
        return cq.Workplane("XY").workplane(offset=z0).polyline(s0["puntos"]).close().extrude(h)
    w = cq.Workplane("XY").workplane(offset=z0).moveTo(*s0["p0"])
    for s in segs:
        if s["tipo"] == "recta":
            w = w.lineTo(*s["p1"])
        elif s["tipo"] == "arco":
            c, r = s["centro"], s["r"]
            a0, a1 = _ang(c, s["p0"]), _ang(c, s["p1"])
            if s["sentido"] == "ccw":
                a1 = a1 if a1 > a0 else a1 + 360
            else:
                a1 = a1 if a1 < a0 else a1 - 360
            am = math.radians((a0 + a1) / 2)
            w = w.threePointArc((c[0] + r * math.cos(am), c[1] + r * math.sin(am)), s["p1"])
        else:
            w = w.spline(s["puntos"][1:], includeCurrent=True)
    return w.close().extrude(h)


def dibujar(s, V, segs, T, z, cotas=True):
    """En una vista de planta del sólido (copia local): marcas de centro de los arcos, radios y puntos de tangencia. Las líneas del contorno las dibuja la vista."""
    if not geometrico(segs):
        return
    for i, sg in enumerate(segs):
        for q in (sg["p0"],):
            ql = pt_local(q, T)
            pp = V.P((ql[0], ql[1], z))
            s.dot(pp, 0.6)
        if sg["tipo"] == "arco" and cotas:
            c = pt_local(sg["centro"], T)
            pc = V.P((c[0], c[1], z))
            s.cross(pc, 2.0)
            a0, a1 = _ang(sg["centro"], sg["p0"]), _ang(sg["centro"], sg["p1"])
            am = (a0 + a1) / 2 - math.degrees(T[2])
            s.dim_rad(pc, sg["r"] * V.scale, am, f"R{sg['r']:.1f}".replace(".", ","))


def dibujar_custom(s, ox, oy, k, segs, T, holes, bb, layer="VIS"):
    """Planta del contorno con entidades exactas (ARC, SPLINE, LINE) en una vista «custom» del compositor: (ox, oy) esquina inferior izquierda, k escala."""
    x0, y0 = bb[0], bb[1]
    P = lambda q: (ox + (q[0] - x0) * k, oy + (q[1] - y0) * k)
    for sg in segs:
        a, b = P(pt_local(sg["p0"], T)), P(pt_local(sg["p1"], T))
        if sg["tipo"] == "recta":
            s.line(a, b, layer)
        elif sg["tipo"] == "arco":
            c = pt_local(sg["centro"], T)
            pc = P(c)
            a0 = _ang(sg["centro"], sg["p0"]) - math.degrees(T[2])
            a1 = _ang(sg["centro"], sg["p1"]) - math.degrees(T[2])
            if sg["sentido"] == "cw":
                a0, a1 = a1, a0
            s.arc(pc, sg["r"] * k, a0 % 360, a1 % 360, layer)
            s.cross(pc, 2.0)
            am = math.radians((a0 + (a1 if a1 > a0 else a1 + 360)) / 2)
            s.leader((pc[0] + sg["r"] * k * math.cos(am), pc[1] + sg["r"] * k * math.sin(am)), (pc[0] + (sg["r"] * k + 12) * math.cos(am), pc[1] + (sg["r"] * k + 12) * math.sin(am)),
                     f"R{sg['r']:.1f}".replace(".", ","))
        else:
            s.spline([P(pt_local(q, T)) for q in sg["puntos"]], layer)
        s.dot(a, 0.6)
    for (hx, hy, r) in holes:
        s.circle(P((hx, hy)), r * k, layer)
        s.centerlines(P((hx, hy)), r * k)


def caja(segs, T):
    pts = []
    for sg in segs:
        if sg["tipo"] == "poligono":
            pts += [pt_local(q, T) for q in sg["puntos"]]
            continue
        pts += [pt_local(sg["p0"], T), pt_local(sg["p1"], T)] + [pt_local(q, T) for q in sg.get("puntos", [])]
        if sg["tipo"] == "arco":
            c = pt_local(sg["centro"], T)
            pts += [(c[0] + sg["r"] * math.cos(math.radians(a)), c[1] + sg["r"] * math.sin(math.radians(a))) for a in range(0, 360, 10)
                    if _en_arco(sg, a + math.degrees(T[2]))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _en_arco(sg, a):
    a0, a1 = _ang(sg["centro"], sg["p0"]), _ang(sg["centro"], sg["p1"])
    if sg["sentido"] == "cw":
        a0, a1 = a1, a0
    span = (a1 - a0) % 360
    return (a - a0) % 360 <= span


def tabla(segs, T):
    """Filas de la tabla del contorno: tramo, tipo, punto inicial, final (= puntos de tangencia) y centro/radio."""
    rows = []
    fm_ = lambda v: f"{v:.1f}".replace(".", ",")
    pt = lambda q: f"{fm_(pt_local(q, T)[0])}; {fm_(pt_local(q, T)[1])}"
    if not geometrico(segs):
        pts = segs[0]["puntos"]
        rows.append(["—", "Polígono (provisional)", pt(pts[0]), pt(pts[-1]), f"{len(pts)} vértices en el JSON: RETENIDA hasta los segmentos geométricos del núcleo"])
        return rows
    for i, sg in enumerate(segs, 1):
        nm = {"recta": "Recta", "arco": "Arco tangente"}.get(sg["tipo"], "Curva de transición (spline)")
        ex = "—"
        if sg["tipo"] == "arco":
            ex = f"{pt(sg['centro'])} / R{fm_(sg['r'])}"
        elif sg["tipo"] in TIPOS_CURVA:
            ex = f"{len(sg['puntos'])} puntos de paso (DXF)"
        rows.append([str(i), nm, pt(sg["p0"]), pt(sg["p1"]), ex])
    return rows
