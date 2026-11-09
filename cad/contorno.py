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


def leer(ins, clave=None):
    """Segmentos del contorno: «segmentos_contorno» del núcleo (tipo linea/arco, radio, sentido antihorario/horario, rol) o «segmentos»."""
    segs = ins.get(clave) if clave else (ins.get("segmentos_contorno") or ins.get("segmentos"))
    if segs:
        out = []
        for s in segs:
            t = {"linea": "recta", "línea": "recta"}.get(s.get("tipo", "recta"), s.get("tipo", "recta"))
            d = dict(tipo=t, p0=tuple(s["p0"]), p1=tuple(s["p1"]), rol=s.get("rol", ""))
            if t == "arco":
                sen = s.get("sentido", "ccw")
                d.update(centro=tuple(s["centro"]), r=float(s.get("r", s.get("radio"))), sentido={"antihorario": "ccw", "horario": "cw"}.get(sen, sen))
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


def dibujar_custom(s, ox, oy, k, segs, T, holes, bb, layer="VIS", cotas=True):
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
            if not cotas:
                s.dot(a, 0.6)
                continue
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


def tangente(sg, fin):
    """Dirección (unitaria) de avance del segmento en su inicio (fin=False) o en su final (fin=True)."""
    if sg["tipo"] == "arco":
        c = sg["centro"]
        q = sg["p1"] if fin else sg["p0"]
        rx, ry = q[0] - c[0], q[1] - c[1]
        t = (-ry, rx) if sg["sentido"] == "ccw" else (ry, -rx)
    elif sg["tipo"] in TIPOS_CURVA:
        a, b = (sg["puntos"][-2], sg["puntos"][-1]) if fin else (sg["puntos"][0], sg["puntos"][1])
        t = (b[0] - a[0], b[1] - a[1])
    else:
        t = (sg["p1"][0] - sg["p0"][0], sg["p1"][1] - sg["p0"][1])
    n = math.hypot(*t) or 1.0
    return (t[0] / n, t[1] / n)


def quiebres(segs):
    """[(i, ángulo de quiebre en grados, salto de posición mm)] en cada unión de segmentos consecutivos (G0/G1)."""
    out = []
    for i, (a, b) in enumerate(zip(segs, segs[1:])):
        ta, tb = tangente(a, True), tangente(b, False)
        ang = math.degrees(math.acos(max(-1.0, min(1.0, ta[0] * tb[0] + ta[1] * tb[1]))))
        out.append((i + 1, ang, math.hypot(a["p1"][0] - b["p0"][0], a["p1"][1] - b["p0"][1])))
    return out


def dist_segmento(sg, q):
    """Distancia de un punto al segmento (recta o arco)."""
    if sg["tipo"] == "arco":
        c, r = sg["centro"], sg["r"]
        a = math.degrees(math.atan2(q[1] - c[1], q[0] - c[0]))
        if _en_arco(sg, a):
            return abs(math.hypot(q[0] - c[0], q[1] - c[1]) - r)
        return min(math.hypot(q[0] - sg["p0"][0], q[1] - sg["p0"][1]), math.hypot(q[0] - sg["p1"][0], q[1] - sg["p1"][1]))
    a, b = sg["p0"], sg["p1"]
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy or 1e-12
    t = max(0.0, min(1.0, ((q[0] - a[0]) * vx + (q[1] - a[1]) * vy) / L2))
    return math.hypot(q[0] - a[0] - t * vx, q[1] - a[1] - t * vy)


def desviacion(segs, puntos):
    """Máxima distancia de una nube de puntos (muestreo del DXF o del sólido) al contorno del núcleo."""
    return max((min(dist_segmento(sg, q) for sg in segs) for q in puntos), default=0.0)


def offset(sg, d):
    """Segmento paralelo a distancia d hacia la izquierda del sentido de avance (para la línea de la capa templada)."""
    if sg["tipo"] == "arco":
        k = -1 if sg["sentido"] == "ccw" else 1          # izquierda del avance: hacia el centro en un arco antihorario
        r2 = sg["r"] + k * d
        c = sg["centro"]
        f = lambda q: (c[0] + (q[0] - c[0]) * r2 / sg["r"], c[1] + (q[1] - c[1]) * r2 / sg["r"])
        return dict(sg, r=r2, p0=f(sg["p0"]), p1=f(sg["p1"]))
    t = tangente(sg, False)
    n = (-t[1] * d, t[0] * d)
    return dict(sg, p0=(sg["p0"][0] + n[0], sg["p0"][1] + n[1]), p1=(sg["p1"][0] + n[0], sg["p1"][1] + n[1]))


def muestras(segs, T, n=40):
    """Puntos de muestreo de las entidades dibujadas (marco de la placa) → vuelta al sistema de la tornamesa, para el control de desviación."""
    out = []
    c_, s_ = math.cos(T[2]), math.sin(T[2])
    back = lambda q: (T[0] + q[0] * c_ - q[1] * s_, T[1] + q[0] * s_ + q[1] * c_)
    for sg in segs:
        if sg["tipo"] == "arco":
            c = pt_local(sg["centro"], T)
            a0, a1 = _ang(sg["centro"], sg["p0"]), _ang(sg["centro"], sg["p1"])
            span = ((a1 - a0) % 360) if sg["sentido"] == "ccw" else -((a0 - a1) % 360)
            for i in range(n + 1):
                a = math.radians(a0 + span * i / n - math.degrees(T[2]))
                out.append(back((c[0] + sg["r"] * math.cos(a), c[1] + sg["r"] * math.sin(a))))
        else:
            q0, q1 = pt_local(sg["p0"], T), pt_local(sg["p1"], T)
            out += [back((q0[0] + (q1[0] - q0[0]) * i / n, q0[1] + (q1[1] - q0[1]) * i / n)) for i in range(n + 1)]
    return out
