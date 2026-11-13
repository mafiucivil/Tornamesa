"""Control automático de completitud dimensional por pieza, leído del sólido 3D.

Para cada pieza fabricable de una lámina de pieza (serie FAB) se extraen del B-rep, en el sistema propio de la pieza
(normal de su cara plana mayor y arista recta más larga perpendicular a ella):
  - extensión total en los tres ejes;
  - cada nivel de cara plana perpendicular a un eje (escalón);
  - cada superficie cilíndrica: diámetro (o radio, si es un arco parcial) y la posición de su eje en los otros dos ejes;
  - caras inclinadas o cónicas (chaflanes / biseles).
Cada requisito se da por cubierto si su valor figura como número en algún texto de la lámina (cota, llamada o fila de tabla),
con la precisión con que está escrito. Para las posiciones de eje se admiten: coordenada desde el centro, desde cualquiera de
los dos bordes, eje sobre la línea de simetría (coordenada 0), o el radio/diámetro del círculo de paso desde el centro de la pieza.
En sectores y anillos (arcos con centro en el eje del equipo) la forma en planta la fijan los radios, los ángulos y las posiciones de ejes:
no se exigen extensiones ni escalones en planta. Una pieza documentada en dos láminas se controla con los textos de ambas.
Las piezas comerciales quedan justificadas («definido por elemento comercial»)."""
import math
import re

NUM = re.compile(r"(?<![\d.,HhfgmpsknjJ])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)")


def numeros(texts):
    """[(valor, decimales)] de todos los números escritos en la lámina (formato 1.140 / 22,5)."""
    out = []
    for t in texts:
        for m in NUM.findall(str(t)):
            s = m.replace(".", "")
            dec = len(s.split(",")[1]) if "," in s else 0
            try:
                out.append((float(s.replace(",", ".")), dec))
            except ValueError:
                pass
    return out


def _hay(nums, v, tol_int=0.51, tol_dec=0.051):
    v = abs(v)
    for n, dec in nums:
        if abs(n - v) <= (tol_int if dec == 0 else tol_dec * (10 ** (1 - dec)) if dec <= 1 else 0.0051 + 1e-6):
            return True
    return False


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def marco(so):
    """Sistema propio de la pieza: (e1, e2, n1)."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder
    best, bcyl = None, None
    for fc in so.Faces():
        ad = BRepAdaptor_Surface(fc.wrapped)
        if ad.GetType() == GeomAbs_Plane:
            a = fc.Area()
            if best is None or a > best[0]:
                n = fc.normalAt()
                best = (a, (n.x, n.y, n.z))
        elif ad.GetType() == GeomAbs_Cylinder:
            a = fc.Area()
            if bcyl is None or a > bcyl[0]:
                d = ad.Cylinder().Axis().Direction()
                bcyl = (a, (d.X(), d.Y(), d.Z()))
    n1 = _unit((best or bcyl or (0, (0, 0, 1)))[1])
    e1, lmax = None, 0.0
    for e in so.Edges():
        if e.geomType() != "LINE":
            continue
        a, b = e.startPoint(), e.endPoint()
        d = (b.x - a.x, b.y - a.y, b.z - a.z)
        L = math.sqrt(_dot(d, d))
        if L > lmax and abs(_dot(_unit(d), n1)) < 1e-3:
            e1, lmax = _unit(d), L
    if e1 is None:
        t = (1, 0, 0) if abs(n1[0]) < 0.9 else (0, 1, 0)
        e1 = _unit(_cross(n1, t))
    e2 = _unit(_cross(n1, e1))
    return e1, e2, n1


def requisitos(so):
    """Lista de requisitos dimensionales del sólido: dicts con tipo, descripción y valores aceptables."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone
    E = marco(so)
    nombres = ("x", "y", "z")
    pts = [(v.X, v.Y, v.Z) for v in so.Vertices()]
    for e in so.Edges():
        for t in (0.25, 0.5, 0.75):
            try:
                q = e.positionAt(t)
                pts.append((q.x, q.y, q.z))
            except Exception:
                pass
    lo = [min(_dot(p, a) for p in pts) for a in E]
    hi = [max(_dot(p, a) for p in pts) for a in E]
    ctr = [(l + h) / 2 for l, h in zip(lo, hi)]
    R = []
    ext_req = [dict(tipo="extensión", desc=f"extensión total en {nombres[i]} = {hi[i] - lo[i]:.1f}", vals=[hi[i] - lo[i]], eje=i) for i in range(3)]
    levels = [{}, {}, {}]
    cyls = {}
    inclinadas = 0
    amax = max((fc.Area() for fc in so.Faces()), default=1.0)
    for fc in so.Faces():
        ad = BRepAdaptor_Surface(fc.wrapped)
        ty = ad.GetType()
        if ty == GeomAbs_Plane:
            n = fc.normalAt()
            n = (n.x, n.y, n.z)
            c = fc.Center()
            c = (c.x, c.y, c.z)
            ax = [i for i in range(3) if abs(abs(_dot(n, E[i])) - 1) < 1e-4]
            if ax:
                v_ = _dot(c, E[ax[0]])
                levels[ax[0]].setdefault(round(v_, 2), v_)
            else:
                inclinadas += 1
        elif ty == GeomAbs_Cylinder:
            cy = ad.Cylinder()
            r = cy.Radius()
            d = cy.Axis().Direction()
            d = (d.X(), d.Y(), d.Z())
            l0 = cy.Axis().Location()
            l0 = (l0.X(), l0.Y(), l0.Z())
            u0, u1 = ad.FirstUParameter(), ad.LastUParameter()
            full = (u1 - u0) > 2 * math.pi - 1e-3
            ax = [i for i in range(3) if abs(abs(_dot(d, E[i])) - 1) < 1e-4]
            if not ax:
                continue
            a = ax[0]
            others = [i for i in range(3) if i != a]
            co = tuple(round(_dot(l0, E[i]), 1) for i in others)
            key = (round(r, 2), a, co)
            if key in cyls:
                cyls[key]["full"] = cyls[key]["full"] or full
                continue
            zg = abs(abs(d[2]) - 1) < 1e-4
            cyls[key] = dict(r=r, a=a, others=others, co=[_dot(l0, E[i]) for i in others], full=full, rho_g=(math.hypot(l0[0], l0[1]) if zg else None))
        elif ty == GeomAbs_Cone:
            inclinadas += 1
    ext_pl = max([hi[i] - lo[i] for i in range(3) if abs(E[i][2]) < 1e-3] or [0.0])
    sector = any(c["rho_g"] is not None and c["rho_g"] < 0.05 and c["r"] >= 0.3 * ext_pl for c in cyls.values())
    for i in range(3):
        if sector and abs(E[i][2]) < 1e-3:
            continue            # sector/anillo: la forma en planta la fijan radios, ángulos y ejes (se controlan aparte)
        L = sorted(levels[i].values())
        for j, z in enumerate(L):
            if j == 0:
                continue
            cands = [z - L[0], L[-1] - z, z - L[j - 1]] + ([L[j + 1] - z] if j + 1 < len(L) else [])
            cands = [c for c in cands if c > 0.05]
            if cands:
                R.append(dict(tipo="escalón", desc=f"escalón en {nombres[i]} a {z - L[0]:.1f} de la cara {nombres[i]} mínima", vals=cands))
    pcd_r = {}
    for k, c in cyls.items():
        r = c["r"]
        R.append(dict(tipo="diámetro" if c["full"] else "radio", desc=(f"Ø{2 * r:.1f}" if c["full"] else f"R{r:.1f}") + f" (eje ∥ {nombres[c['a']]})", vals=[2 * r, r], rosca=2 * r))
        # posición del eje en los otros dos ejes
        rho = math.hypot(c["co"][0] - ctr[c["others"][0]], c["co"][1] - ctr[c["others"][1]])
        for j, i in enumerate(c["others"]):
            v = c["co"][j]
            cands = [abs(v - ctr[i]), v - lo[i], hi[i] - v]
            if min(abs(v - ctr[i]), abs(v - lo[i]), abs(hi[i] - v)) < 0.06:
                continue           # sobre el eje de simetría o en el borde: implícito
            rg = [c["rho_g"], 2 * c["rho_g"]] if c["rho_g"] else []       # radio del círculo de paso desde el eje del equipo (piezas en sectores)
            R.append(dict(tipo="posición de eje", desc=f"posición del eje de Ø{2 * r:.1f} en {nombres[i]} ({v - lo[i]:.1f} desde el borde)", vals=cands + [rho, 2 * rho] + rg))
    # extensión: cubierta por el diámetro exterior cuando la pieza es de revolución en ese plano
    dfull = [2 * c["r"] for c in cyls.values() if c["full"]]
    # sector o anillo: un arco con eje en el eje del equipo define la forma en planta (radios y ángulo); la extensión en planta no se pide
    for q in ext_req:
        if sector and abs(E[q["eje"]][2]) < 1e-3:
            continue
        if not any(abs(d - q["vals"][0]) < 0.05 for d in dfull):
            R.insert(0, q)
    if inclinadas:
        R.append(dict(tipo="chaflán/inclinada", desc=f"{inclinadas} cara(s) inclinada(s) o cónica(s): ángulo o chaflán", vals=[], angulo=True))
    return R


def faltantes(texts, so):
    nums = numeros(texts)
    NV = r"(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
    lst = lambda pre: [x for t in texts for m in re.findall(pre + r"\s?=?\s?(" + NV + r"(?:,\s" + NV + r")*)", str(t)) for x in m.split(", ")]
    dnums = numeros(lst("Ø"))
    rnums = numeros(lst(r"(?<![A-Za-z])R(?:_[io])?"))
    anchos = [n for n, d in nums if 0 < n <= 40]
    has_ang = any(("°" in str(t)) or ("×45" in str(t)) or ("chafl" in str(t).lower()) or ("bisel" in str(t).lower()) for t in texts)
    roscas = [float(m) for t in texts for m in re.findall(r"\bM(\d+(?:,\d+)?)", str(t).replace(",", "."))] if texts else []
    out, n = [], 0
    for q in requisitos(so):
        n += 1
        if q.get("angulo"):
            if not has_ang:
                out.append(q["desc"])
            continue
        if q["tipo"] in ("diámetro", "radio"):
            # diámetros y radios: el número debe estar rotulado como Ø… o R… (o como rosca M…)
            if _hay(dnums, q["vals"][0]) or _hay(rnums, q["vals"][1]):
                continue
            # pared de una ranura: radio del eje de la ranura ± medio ancho
            r_ = q["vals"][1]
            if any(abs(R_ + sg * w / 2 - r_) < 0.06 for R_ in [n for n, _ in rnums] + [n / 2 for n, _ in dnums] for w in anchos for sg in (1, -1)):
                continue
        elif any(_hay(nums, v) for v in q["vals"]):
            continue
        if q.get("rosca") and any(0.74 * d <= q["rosca"] <= 1.001 * d for d in roscas):
            continue
        out.append(q["desc"])
    return n, out


def control_lamina(ctx, h, union=None, hechos=None):
    """(n_requisitos, [(pieza, faltante)], justificadas) para una lámina de pieza. Comerciales: justificadas.
    union: {código: textos de TODAS las láminas que documentan la pieza} (una pieza puede repartirse en dos láminas, p. ej. sector y ranuras);
    hechos: conjunto de códigos ya controlados (cada pieza se cuenta una sola vez, en la primera lámina donde aparece)."""
    keys = [p.key for p in ctx.m.parts if p.code in h.items]
    tot, miss, just = 0, [], []
    for k in keys:
        p = ctx.m.get(k)
        if p is None or k not in ctx.shapes:
            continue
        if hechos is not None:
            if p.code in hechos:
                continue
            hechos.add(p.code)
        if p.comercial:
            just.append((p.code, "definido por elemento comercial"))
            continue
        sols = ctx.shapes[k].Solids()
        if not sols:
            continue
        txt = (union or {}).get(p.code) or h.s.texts
        n, fl = faltantes(txt, sols[0])
        if getattr(p, "contorno_cnc", False):
            # contorno poligonal provisional del núcleo (placa-leva RETENIDA): las facetas del polígono no se acotan, salen del programa CNC
            cnc = [x for x in fl if "inclinada" in x]
            fl = [x for x in fl if "inclinada" not in x]
            if cnc:
                just.append((p.code, "contorno poligonal provisional del núcleo (programa CNC desde el JSON; lámina RETENIDA)"))
        tot += n
        miss += [(p.code, x) for x in fl]
    return tot, miss, just
