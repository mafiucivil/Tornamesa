"""Modelo 3D del accionamiento según el modo del núcleo (D.modo):
  - modo 2 (por defecto): pivotado tipo KIET — cajón del ojal E soldado a la base (paredes completas, paredes con ventana y tapas), pasador E,
    bloque-uña acodado con horquilla, pasador Q (su extremo inferior es el seguidor), cuatro placas-leva empernadas a la base y cilindro E–Q;
  - modo 1 (alternativa): leva de reenganche del modo guiado — riel-leva, pórticos (patas y tapas soldadas a la prolongación de la bancada),
    prolongación de la bancada, seguidor (rodillo y perno) y ranura de la tapa del patín.
Toda la geometría sale de D.pivotado.fabricacion y D.levaGuiada.fabricacion (JSON del núcleo). Lo que el núcleo no entrega y el dibujo necesita
se declara en REQUIERE_NUCLEO (se imprime en GEN-009 y en el informe del paquete) y, si es una decisión de dibujo, en SUPUESTOS (S2x)."""
import math
import cadquery as cq
from geom import *

# números de pieza FIJOS (un código = una geometría en todos los juegos; H-04). Modo 1: 1…12; modo 2: 13…17. BAS: cajón del ojal E 8…11.
ACC_NUM = {"bancada": 1, "cilindro": 2, "patin": 3, "una": 4, "pasador_vastago": 5, "pasador_ojal": 6,
           "leva_riel": 7, "leva_pata": 8, "leva_tapa": 9, "leva_prolong": 10, "leva_rodillo": 11, "leva_perno": 12,
           "cilindro_pv": 13, "pasador_E": 14, "bloque_una": 15, "pasador_Q": 16, "placa_leva": 17,
           # placa-guía curva (núcleo 7dfd06a) y bloque-uña con cara R120 (3dab1ce): geometría nueva → números nuevos (17 y 18 quedan anulados)
           "placa_guia": 20, "pernos_placa_guia": 21, "pasadores_placa_guia": 22, "bloque_una_r": 23, "placa_guia_h": 24}
BAS_NUM = {"cajon_pared": 8, "cajon_ventana_a": 9, "cajon_ventana_b": 10, "cajon_tapa": 11}

EYE_WALL = 17.5          # pared del ojal comercial del cilindro (52,5 − 35 del ojal Ø70 del modelo de la Rev. B): radio exterior = d/2 + 17,5 (supuesto S21)


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _cyl(r, h, z0=0.0, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(h)


def _compound(items):
    sol = []
    for i in items:
        sol.extend(i.vals() if hasattr(i, "vals") else [i])
    return cq.Workplane("XY").newObject([cq.Compound.makeCompound(sol)])


def _poly(pts, z0, h):
    return cq.Workplane("XY").workplane(offset=z0).polyline([tuple(p) for p in pts]).close().extrude(h)


def _frame(Q, P_, O=(0.0, 0.0)):
    """Marco local del bloque-uña (núcleo): origen en Q, x hacia el pasador tomado P, y perpendicular hacia O."""
    ux, uy = P_[0] - Q[0], P_[1] - Q[1]
    n = math.hypot(ux, uy)
    ux, uy = ux / n, uy / n
    vx, vy = -uy, ux
    if vx * (O[0] - Q[0]) + vy * (O[1] - Q[1]) < 0:
        vx, vy = -vx, -vy
    return (ux, uy), (vx, vy)


def _to_global(pt, Q, u, v):
    return (Q[0] + pt[0] * u[0] + pt[1] * v[0], Q[1] + pt[0] * u[1] + pt[1] * v[1])


def cajon_paredes(F, lado_key):
    """Paredes del cajón en molinete (todas de largo lado − t): {lado: (x0, x1, y0, y1)} en coordenadas de la tornamesa."""
    S = F["soporte_E"]
    c = S[lado_key]["centro"]
    L, t = S["lado"], S["t_pared"]
    x0, x1, y0, y1 = c[0] - L / 2, c[0] + L / 2, c[1] - L / 2, c[1] + L / 2
    return {"x+": (x1 - t, x1, y0, y1 - t), "y+": (x0 + t, x1, y1 - t, y1), "x−": (x0, x0 + t, y0 + t, y1), "y−": (x0, x1 - t, y0, y0 + t)}, (x0, x1, y0, y1)


def ventana_cutter(F, lado_key):
    """Prisma de la ventana: sector angular desde E (sector_deg) entre z de la ventana."""
    S = F["soporte_E"]
    E = S[lado_key]["centro"]
    a0, a1 = S["ventana"]["sector_deg"]
    rot = 0.0 if lado_key == "cilindro1" else 180.0          # el cajón del cilindro 2 es el del cilindro 1 girado 180° (sector del núcleo para el cilindro 1)
    z0, z1 = S["ventana"]["z"]
    R = S["lado"] * 1.5
    pts = [(E[0], E[1])] + [(E[0] + R * math.cos(math.radians(a + rot)), E[1] + R * math.sin(math.radians(a + rot))) for a in [a0 + (a1 - a0) * k / 8 for k in range(9)]]
    return _poly(pts, z0, z1 - z0)


def build_pivotado(m, g, D, Part, A572, parte="acc"):
    """Piezas del modo 2 (parte = «cajon»: paredes y tapas soldadas a la base; «acc»: pasadores, bloque-uña, cilindro y placas-leva).
    Devuelve dict con información para las láminas (posiciones, marcos locales)."""
    P, F, PV = g.P, g.FPV, g.PV
    S, BU, PE, PQ, PL = F["soporte_E"], F["bloque_una"], F["pasador_E"], F["pasador_Q"], F["placas_leva"]
    info = m.info.setdefault("pivotado", {})
    if parte == "cajon":
        _cajon(m, g, Part, info)
        return info
    _acc(m, g, D, Part, info)
    return info


def _cajon(m, g, Part, info):
    P, F = g.P, g.FPV
    S = F["soporte_E"]
    t, Lc = S["t_pared"], S["lado"]
    zw0, zw1 = S["z_paredes"]
    tap = S["tapas"]
    li = Lc - 2 * t                                      # tapas dentro del cajón (lado − 2·t_pared); el JSON da lado = 260 (ver requiere núcleo)
    paredes_c, ventana_a, ventana_b, tapas = [], [], [], []
    info["cajones"] = {}
    for lk in ("cilindro1", "cilindro2"):
        W, (x0, x1, y0, y1) = cajon_paredes(F, lk)
        E = S[lk]["centro"]
        vc = ventana_cutter(F, lk)
        comp = S[lk]["paredes_completas"]
        vent = S[lk]["paredes_con_ventana"]
        for side in comp:
            a, b, c_, d_ = W[side]
            paredes_c.append(_box(a, b, c_, d_, zw0, zw1))
        for side in vent:
            a, b, c_, d_ = W[side]
            w_ = _box(a, b, c_, d_, zw0, zw1).cut(vc)
            # largo de la ventana de esta pared (molinete: la pared que cubre la esquina lleva la ventana más larga)
            (ventana_a if side in ("x−", "x+") else ventana_b).append(w_)
        for (za, zb_) in (tap["z_inf"], tap["z_sup"]):
            tapas.append(_box(x0 + t, x1 - t, y0 + t, y1 - t, za, zb_).cut(_cyl(tap["agujero_E"] / 2, zb_ - za + 2, za - 1, E[0], E[1])))
        info["cajones"][lk] = dict(E=E, box=(x0, x1, y0, y1), paredes=W, comp=comp, vent=vent)
    mS = "S355J2 (EN 10025-2), Fy ≥ 345 MPa (núcleo: «" + S["material"] + "»)"
    obs_pos = "Posición del cajón respecto de los bordes de la base con tolerancia ajustada (CON-007): holgura al marco del núcleo FU 0,999 aceptada por el mandante"
    m.add(Part("cajon_pared", "BAS", "Cajón del ojal E: pared completa", f"Plancha {f(Lc - t)}×{f(zw1 - zw0)}×{f(t)} (molinete; pared trasera de la U)", _compound(paredes_c), len(paredes_c), mS,
               "Oxicorte/plasma; cantos a escuadra; soldadura a la base (filetes a ambos lados)", core="brackets", color=(0.5, 0.52, 0.55), obs=obs_pos, num_fijo=BAS_NUM["cajon_pared"]))
    m.add(Part("cajon_ventana_a", "BAS", "Cajón del ojal E: pared con ventana (esquina)", f"Plancha {f(Lc - t)}×{f(zw1 - zw0)}×{f(t)} con ventana en el extremo (sector del ojal)", _compound(ventana_a), len(ventana_a), mS,
               "Oxicorte/plasma de la plancha y de la ventana; soldadura a la base", core="brackets", color=(0.5, 0.52, 0.55), num_fijo=BAS_NUM["cajon_ventana_a"]))
    m.add(Part("cajon_ventana_b", "BAS", "Cajón del ojal E: pared con ventana (tope)", f"Plancha {f(Lc - t)}×{f(zw1 - zw0)}×{f(t)} con ventana en el extremo (sector del ojal)", _compound(ventana_b), len(ventana_b), mS,
               "Oxicorte/plasma de la plancha y de la ventana; soldadura a la base", core="brackets", color=(0.5, 0.52, 0.55), num_fijo=BAS_NUM["cajon_ventana_b"]))
    m.add(Part("cajon_tapa", "BAS", "Cajón del ojal E: tapa (oreja del pasador E)", f"Plancha {f(li)}×{f(li)}×{f(tap['t'])}, agujero Ø{f(tap['agujero_E'])} H9 (mandrinado en línea tras soldar)", _compound(tapas), len(tapas), mS,
               "Oxicorte/plasma; soldadura a las paredes; agujero H9 mandrinado en línea con la otra tapa tras soldar y aliviar", core="brackets", color=(0.5, 0.52, 0.55), num_fijo=BAS_NUM["cajon_tapa"]))
    for k_ in ("cajon_pared", "cajon_ventana_a", "cajon_ventana_b", "cajon_tapa"):
        m.get(k_).libre = True
        m.get(k_).volteable = True


def _acc(m, g, D, Part, info):
    P, F, PV = g.P, g.FPV, g.PV
    S, BU, PE, PQ, PL = F["soporte_E"], F["bloque_una"], F["pasador_E"], F["pasador_Q"], F["placas_leva"]
    # pasador E
    pe = []
    for lk in ("cilindro1", "cilindro2"):
        E = S[lk]["centro"]
        pe.append(_cyl(PE["d"] / 2, PE["z"][1] - PE["z"][0], PE["z"][0], E[0], E[1]).faces(">Z or <Z").edges().chamfer(g.ch_pp))
    import propuestas
    m.add(Part("pasador_E", "ACC", "Pasador E del ojal trasero", f"Pasador Ø{f(PE['d'])} f8 × {f(PE['largo'])} (z {f(PE['z'][0])}–{f(PE['z'][1])}), chaflanes {fm(g.ch_pp, 0)}×45°", _compound(pe), len(pe),
               propuestas.grado(P["Fy_pp"], PE["d"], "barra"), "Barra rectificada; corte y chaflanes en torno horizontal", core="brackets", color=(0.3, 0.3, 0.32),
               tratamiento="Bonificado (QT)", num_fijo=ACC_NUM["pasador_E"]))
    # bloque-uña y pasador Q (posición de toma: primera posición del empuje, sentido antihorario)
    pos = PV["posiciones"]
    blocks, pins_q, cyls = [], [], []
    loc = BU["contorno_local"]
    z0b, z1b = BU["z"]
    hq = BU["horquilla"]
    zs0 = z0b + hq["t_mejilla"]
    zs1 = zs0 + hq["ranura_ojal"]
    Rc = hq["R_cubo"]
    cara_ = _poly(loc["cara"], z0b, z1b - z0b)
    R_f = float(BU["cara"].get("radio_planta") or 0.0)
    if R_f > 0:                                        # cara cilíndrica convexa en planta (núcleo: pv_rface), vértice en el frente de la cara
        x_f = max(q[0] for q in loc["cara"])
        cara_ = cara_.intersect(_cyl(R_f, z1b - z0b + 2, z0b - 1, x_f - R_f, 0.0))
    base_local = _poly(loc["cuerpo"], z0b, z1b - z0b).union(cara_).union(_cyl(Rc, z1b - z0b, z0b))
    base_local = base_local.cut(_cyl(BU["agujero_Q"] / 2, z1b - z0b + 2, z0b - 1))
    slot = _cyl(Rc + 1.0, zs1 - zs0, zs0).union(_box(-Rc - 10, 0, -Rc - 10, Rc + 10, zs0, zs1))
    blk_local = base_local.cut(slot)
    info["bloque_local"] = blk_local
    info["slot"] = (zs0, zs1, Rc + 1.0)
    info["frames"] = {}
    zc = g.zc
    r_eye_E = PE["d"] / 2 + EYE_WALL
    r_eye_Q = PQ["d"] / 2 + EYE_WALL
    L_qp = float(PV["L_qp"])
    ang_pins = [float(a) for a in D["pasadores"]]
    th0, th1 = float(PV["theta_ini_deg"]), float(PV["theta_fin_deg"])
    for k in ("1_antihorario", "2_antihorario"):
        ps = pos[k]
        E = ps["E"]
        # posición dibujada: el pasador de la mesa del modelo (ángulos D.pasadores) que cae dentro del empuje, el más cercano a su inicio;
        # Q = P + L_qp·(E − P)/|E − P| (cinemática del núcleo, registro «Accionamiento pivotado tipo KIET»)
        rot_ = 0.0 if k.startswith("1") else 180.0
        cand = [a for a in ang_pins if 0 <= ((a - rot_ - th0) % 360.0) <= (th1 - th0) % 360.0 + 1e-9]
        a_p = min(cand, key=lambda a: (a - rot_ - th0) % 360.0) if cand else math.degrees(math.atan2(ps["P"][0][1], ps["P"][0][0]))
        P_ = (P["R_pin"] * math.cos(math.radians(a_p)), P["R_pin"] * math.sin(math.radians(a_p)))
        dE = math.hypot(E[0] - P_[0], E[1] - P_[1])
        Q = (P_[0] + L_qp * (E[0] - P_[0]) / dE, P_[1] + L_qp * (E[1] - P_[1]) / dE)
        info.setdefault("theta_dib", {})[k] = ((a_p - rot_) % 360.0)
        u, v = _frame(Q, P_)
        ang = math.degrees(math.atan2(u[1], u[0]))
        sgn = 1 if (v[0] * -u[1] + v[1] * u[0]) > 0 else -1           # +1: v = giro +90° de u (el bloque no se espeja)
        b_ = blk_local if sgn > 0 else blk_local.mirror("XZ")
        blocks.append(b_.rotate((0, 0, 0), (0, 0, 1), ang).translate((Q[0], Q[1], 0)))
        info["frames"][k] = dict(Q=Q, P=P_, E=E, u=u, v=v, ang=ang)
        pins_q.append(_cyl(PQ["d"] / 2, PQ["z"][1] - PQ["z"][0], PQ["z"][0], Q[0], Q[1]).faces(">Z or <Z").edges().chamfer(g.ch_pp))
        # cilindro E–Q (comercial; geometría de extremos: e_body y c_rod del núcleo, ojales con pared EYE_WALL)
        ax, ay = Q[0] - E[0], Q[1] - E[1]
        L = math.hypot(ax, ay)
        a_ = math.degrees(math.atan2(ay, ax))
        loc_c = _cyl(r_eye_E, P["b_eye"], zc - P["b_eye"] / 2).cut(_cyl(PE["d"] / 2, P["b_eye"] + 2, zc - P["b_eye"] / 2 - 1))
        body = cq.Workplane("YZ").workplane(offset=P["e_body"]).center(0, zc).circle(P["D_body"] / 2).extrude(P["L0"] - P["c_rod"] - P["e_body"])
        x_rod0 = P["L0"] - P["c_rod"]
        x_neck = L - (Rc + 10.0)                    # el vástago termina antes de la horquilla del bloque; cuello del ojal de ancho b_ojal (supuesto S21)
        rod = cq.Workplane("YZ").workplane(offset=x_rod0).center(0, zc).circle(P["d_rod"] / 2).extrude(max(x_neck - x_rod0, 1.0))
        neck = _box(x_neck - 1.0, L - r_eye_Q + 5.0, -P["b_eye"] / 2, P["b_eye"] / 2, zc - P["b_eye"] / 2, zc + P["b_eye"] / 2)
        eyeq = _cyl(r_eye_Q, P["b_eye"], zc - P["b_eye"] / 2, L, 0).cut(_cyl(PQ["d"] / 2, P["b_eye"] + 2, zc - P["b_eye"] / 2 - 1, L, 0))
        neck = neck.cut(_cyl(PQ["d"] / 2, P["b_eye"] + 2, zc - P["b_eye"] / 2 - 1, L, 0))
        cl = loc_c.union(body).union(rod).union(neck).union(eyeq)
        cyls.append(cl.rotate((0, 0, 0), (0, 0, 1), a_).translate((E[0], E[1], 0)))
        info["frames"][k].update(L=L, a_cil=a_)
    gq = propuestas.grado(P["Fy_pp"], PQ["d"], "barra")
    m.add(Part("cilindro_pv", "ACC", "Cilindro hidráulico doble efecto (modo pivotado)",
               f"Ø{f(P['D_bore'])}/Ø{f(P['d_rod'])}, carrera {f(P['stroke'])}, {f(P['p_rated'])} psi ({fm(P['p_rated'] * 0.0689476, 0)} bar); ojal trasero Ø{f(PE['d'])} (pasador E) y ojal del vástago Ø{f(PQ['d'])} (pasador Q), ancho {f(P['b_eye'])}",
               _compound(cyls), len(cyls), "Comercial (acero; sellos)", "Comercial", mass_override=len(cyls) * P["m_cyl"], core="cyl", comercial=True,
               catalogo="A DEFINIR POR CATÁLOGO (largo ojal–ojal retraído, ojal del vástago para pasador Ø%s y geometría de extremos con el proveedor)" % f(PQ["d"]), color=(0.95, 0.78, 0.1),
               cert="Certificado de prueba hidráulica del fabricante", num_fijo=ACC_NUM["cilindro_pv"]))
    m.add(Part("bloque_una", "ACC", "Bloque-uña acodado",
               f"Bloque {f(BU['h'])} de alto: cuerpo {f(BU['cuerpo']['b'])} acodado {f(BU['cuerpo']['e_acodado'])}, cara {f(BU['cara']['b'])}×{f(BU['cara']['l'])} templada" + (f" cilíndrica R{fm(R_f, 0)}" if R_f > 0 else "") + f", cubo R{f(Rc)} con horquilla {f(hq['ranura_ojal'])} y agujero Ø{f(BU['agujero_Q'])}",
               _compound(blocks), len(blocks), "34CrNiMo6+QT (EN 10083-3), Re ≥ %s MPa medido en la propia forja (3.1) — núcleo: «%s»" % (f(P["Fy_dog"]), BU["material"]),
               "Forja o bloque; fresado del contorno y de la horquilla en mandrinadora/fresadora; agujero Q mandrinado; rectificado de la cara templada", core="dogs", color=(0.85, 0.35, 0.1),
               tratamiento=f"Temple por inducción de la cara {BU['cara']['templada'].replace('Fy_sup', 'límite elástico superficial')}; profundidad {g.z_hard_txt}", num_fijo=ACC_NUM["bloque_una_r"] if R_f > 0 else ACC_NUM["bloque_una"]))
    m.add(Part("pasador_Q", "ACC", "Pasador Q del vástago (seguidor de la placa-leva)", f"Pasador Ø{f(PQ['d'])} f8 × {f(PQ['largo'])} (z {f(PQ['z'][0])}–{f(PQ['z'][1])}); extremo inferior templado (seguidor)", _compound(pins_q), len(pins_q),
               gq, "Barra rectificada; corte y chaflanes en torno horizontal; temple por inducción del extremo inferior", core="dogs", color=(0.3, 0.3, 0.32),
               tratamiento="Bonificado (QT); extremo inferior templado por inducción ≥ 55 HRC (seguidor de la placa-leva)", num_fijo=ACC_NUM["pasador_Q"]))
    # placas-leva: 4 (una por cilindro y sentido); se fabrican iguales: la del sentido horario es la del antihorario volteada (imagen especular, sin rasgos asimétricos en z)
    zp0, zp1 = PL["z"]
    import contorno, re as _re
    plates = []
    holes_base, holes_pas = [], []
    dh = PL["pernos"]["agujero"]
    d_b = PL["pernos"]["d"]
    m_av = _re.search(r"Ø\s*([\d,\.]+)", str(PL["pernos"].get("avellanado", "")))
    d_av = float(m_av.group(1).replace(",", ".")) if m_av else 2.0 * d_b
    m_L = _re.search(r"M\d+\s*[×x]\s*(\d+)", str(PL["pernos"].get("norma", "")))
    Lb = int(m_L.group(1)) if m_L else _perno_len(PL["t"], g.tb, d_b)
    PP = PL.get("pasadores_posicion") or {}
    d_p = float(PP.get("d", 0) or 0)
    L_p = PL["t"] + (g.tb - 3.0)                     # pasador: espesor de la placa + base − 3 mm (supuesto S25; el núcleo no da el largo)
    h_av = (d_av - dh) / 2.0                          # avellanado de 90°
    for k in ("1_antihorario", "1_horario", "2_antihorario", "2_horario"):
        ins = PL["instancias"][k]
        pl = contorno.solido(contorno.leer(ins), zp0, zp1 - zp0)          # segmentos geométricos del núcleo (ARC/LINE exactos)
        pl = pl.cut(cq.Workplane("XY").workplane(offset=zp0 - 1).pushPoints([tuple(q) for q in ins["pernos"]]).circle(dh / 2).extrude(zp1 - zp0 + 2))
        for (x, y) in ins["pernos"]:                  # avellanado ISO 10642 a ras de la cara superior
            pl = pl.cut(cq.Workplane("XY").newObject([cq.Solid.makeCone(dh / 2, d_av / 2 + 0.5, h_av + 0.5, cq.Vector(x, y, zp1 - h_av), cq.Vector(0, 0, 1))]))
        if d_p and ins.get("pasadores_posicion"):
            pl = pl.cut(cq.Workplane("XY").workplane(offset=zp0 - 1).pushPoints([tuple(q) for q in ins["pasadores_posicion"]]).circle(d_p / 2).extrude(zp1 - zp0 + 2))
            holes_pas.extend([tuple(q) for q in ins["pasadores_posicion"]])
        plates.append(pl)
        holes_base.extend([tuple(q) for q in ins["pernos"]])
    # la placa del sentido horario es la imagen especular con los avellanados también en la cara superior: no se puede voltear (un código por geometría)
    desc_ = (f"Plancha e = {f(PL['t'])}, {fm(PL['marco']['largo'], 0)} × {fm(PL['marco']['ancho'], 0)} con recorte curvo (arcos tangentes del núcleo), "
             f"{int(PL['pernos']['n'])} avellanados M{f(d_b)} en la cara superior y {int(PP.get('n', 0))} agujeros Ø{fm(d_p, 0)} H7 de pasadores")
    for key_, nm_, idx_, num_ in (("placa_leva", "Placa-guía curva, sentido antihorario", (0, 2), ACC_NUM["placa_guia"]), ("placa_leva_h", "Placa-guía curva, sentido horario (simétrica)", (1, 3), ACC_NUM["placa_guia_h"])):
        pt = Part(key_, "ACC", nm_, desc_ + ("" if key_ == "placa_leva" else "; simétrica de ACC-020"), _compound([plates[i_] for i_ in idx_]), 2, PL["material"], PL.get("corte", "Corte láser/agua y fresado CNC del canto"),
                  core="cam", color=(0.6, 0.45, 0.25), tratamiento=(PL.get("tratamiento") or {}).get("canto", "Canto templado"), num_fijo=num_)
        pt.contorno_cnc = not contorno.geometrico(contorno.leer(PL["instancias"]["1_antihorario"]))
        m.add(pt)
    # tornillos avellanados ISO 10642 (roscados en la plancha base) y pasadores ISO 8734 de posición
    bolts = []
    for (x, y) in holes_base:
        cone = cq.Workplane("XY").newObject([cq.Solid.makeCone(d_av / 2 - 0.6, d_b / 2, (d_av - 1.2 - d_b) / 2, cq.Vector(x, y, zp1), cq.Vector(0, 0, -1))])
        bolts.append(cone.union(_cyl(d_b / 2, Lb - (d_av - 1.2 - d_b) / 2, zp1 - Lb, x, y)))
    m.add(Part("pernos_placa_guia", "ACC", f"Tornillo ISO 10642 M{f(d_b)}×{Lb} cl. {PL['pernos'].get('clase', '8.8')} (placa-guía)", f"Tornillo avellanado ISO 10642 M{f(d_b)}×{Lb} cl. {PL['pernos'].get('clase', '8.8')}, roscado en la plancha base",
               _compound(bolts), len(bolts), f"ISO 898-1 cl. {PL['pernos'].get('clase', '8.8')}", "Comercial", in_core=False, comercial=True,
               catalogo=f"ISO 10642 M{f(d_b)}×{Lb} cl. {PL['pernos'].get('clase', '8.8')} (código de catálogo: A DEFINIR POR CATÁLOGO)", color=(0.3, 0.3, 0.32), num_fijo=ACC_NUM["pernos_placa_guia"]))
    if holes_pas:
        pins = [_cyl(d_p / 2, L_p, zp1 - L_p, x, y) for (x, y) in holes_pas]
        m.add(Part("pasadores_placa_guia", "ACC", f"Pasador ISO 8734 Ø{fm(d_p, 0)} m6 × {fm(L_p, 0)} (placa-guía)", f"Pasador cilíndrico templado ISO 8734 Ø{fm(d_p, 0)} m6 × {fm(L_p, 0)}, en agujeros H7 escariados en placa y base",
                   _compound(pins), len(pins), "ISO 8734 (templado)", "Comercial", in_core=False, comercial=True, catalogo=f"ISO 8734 Ø{fm(d_p, 0)} m6 × {fm(L_p, 0)} (código de catálogo: A DEFINIR POR CATÁLOGO)",
                   color=(0.3, 0.3, 0.32), num_fijo=ACC_NUM["pasadores_placa_guia"]))
    m.info["placa_leva_holes"] = holes_base
    m.info["placa_pas_holes"] = holes_pas
    m.info["placa_pas_L"] = L_p
    m.info["perno_placa_L"] = Lb


def _perno_len(t_plate, t_base, d):
    """Largo ISO 4762 del perno de la placa-leva roscado en la base: el mayor largo comercial que no sobresale bajo la base (la base apoya en la losa)."""
    serie = [30, 35, 40, 45, 50, 55, 60]
    ok = [L for L in serie if L <= t_plate + t_base - 1.0]
    return max(ok) if ok else serie[0]


def build_leva_guiada(m, g, D, Part, A572):
    """Piezas de la leva de reenganche del modo 1 (Tarea 1 del núcleo), en la posición del sentido antihorario."""
    P, F, LG = g.P, g.FLG, g.LG
    import propuestas
    R, PO, PB, SG = F["riel"], F["porticos"], F["prolongacion_bancada_local"], F["seguidor"]
    inst = F["instancias"]
    rieles, patas, tapas, prol, rod, pern = [], [], [], [], [], []
    dh = PO["agujero"]
    for k in ("1_antihorario", "2_antihorario"):
        I = inst[k]
        sx = I["lado"]
        r_ = _poly(I["riel"], R["z"][0], R["z"][1] - R["z"][0])
        r_ = r_.cut(cq.Workplane("XY").workplane(offset=R["z"][0] - 1).pushPoints([tuple(q) for q in I["pernos"]]).circle(dh / 2).extrude(R["z"][1] - R["z"][0] + 2))
        rieles.append(r_)
        for pa in I["patas"]:
            patas.append(_box(pa["x"][0], pa["x"][1], pa["y"][0], pa["y"][1], pa["z"][0], pa["z"][1]))
        # tapas, prolongaciones: locales del lado +x (cilindro 1); el cilindro 2 es el giro de 180°
        rot = 0.0 if sx > 0 else 180.0
        for tp in PO["tapas_local"]:
            tb_ = _box(tp["x"][0], tp["x"][1], tp["y"][0], tp["y"][1], tp["z"][0], tp["z"][1])
            pts = [tuple(q) for q in PO["pernos_local"] if tp["x"][0] < q[0] < tp["x"][1] and tp["y"][0] < q[1] < tp["y"][1]]
            if pts:
                tb_ = tb_.cut(cq.Workplane("XY").workplane(offset=tp["z"][0] - 1).pushPoints(pts).circle(PO["d_perno"] / 2).extrude(tp["z"][1] - tp["z"][0] + 2))   # rosca M (Ø nominal en el modelo)
            tapas.append(tb_.rotate((0, 0, 0), (0, 0, 1), rot))
        for pr in PB:
            prol.append(_box(pr["x"][0], pr["x"][1], pr["y"][0], pr["y"][1], pr["z"][0], pr["z"][1]).rotate((0, 0, 0), (0, 0, 1), rot))
    # seguidor: perno empotrado en la uña y rodillo; posición de toma (x_eje_toma) a y del pasador del vástago + sentido·y_rel
    for c in D["cilindros"]["antihorario"]:
        sx, dy = c["side"], c["dir"]
        xs = sx * SG["x_eje_toma"]
        ys = c["rodEngage"][1] + dy * SG["y_respecto_pasador_vastago"]
        pz0 = SG["perno"]["z_cara_sup_una"] - SG["perno"]["empotrado_en_una"]
        pz1 = SG["rodillo"]["z"][1]                     # el perno llega a la cara superior del rodillo (el largo del JSON no alcanza: requiere núcleo)
        pern.append(_cyl(SG["perno"]["d"] / 2, pz1 - pz0, pz0, xs, ys))
        rz0, rz1 = SG["rodillo"]["z"]
        rod.append(_cyl(SG["rodillo"]["d"] / 2, rz1 - rz0, rz0, xs, ys).cut(_cyl(SG["perno"]["d"] / 2, rz1 - rz0 + 2, rz0 - 1, xs, ys)))
    mR = "42CrMo4+QT (EN 10083-3), Re ≥ %s MPa; canto templado ≥ 55 HRC" % f(R["Fy"])
    m.add(Part("leva_riel", "ACC", "Riel-leva", f"Pletina e = {f(R['t'])}, contorno del núcleo (toma, bolsillo y rampa en el canto interior; aletas de apoyo), {len(inst['1_antihorario']['pernos'])} agujeros Ø{f(dh)}",
               _compound(rieles), len(rieles), mR, "Oxicorte/plasma CNC desde plancha con sobremetal; canto de leva fresado y templado por inducción; agujeros taladrados", core="cam", color=(0.6, 0.45, 0.25),
               tratamiento="QT; canto templado ≥ 55 HRC", obs="Una por cilindro: se voltea para el otro sentido de giro", num_fijo=ACC_NUM["leva_riel"]))
    m.get("leva_riel").volteable = True
    m.add(Part("leva_pata", "ACC", "Pórtico del riel: pata", f"Plancha {f(PO['patas_local'][0]['x'][1] - PO['patas_local'][0]['x'][0])}×{f(PO['patas_local'][0]['y'][1] - PO['patas_local'][0]['y'][0])}×{f(PO['patas_local'][0]['z'][1] - PO['patas_local'][0]['z'][0])}",
               _compound(patas), len(patas), "42CrMo4+QT (EN 10083-3) (núcleo: «%s»)" % PO["material"], "Oxicorte y fresado de caras; soldadura a la prolongación de la bancada y a la tapa", core="cam", color=(0.5, 0.52, 0.55),
               num_fijo=ACC_NUM["leva_pata"]))
    tp0 = PO["tapas_local"][0]
    m.add(Part("leva_tapa", "ACC", "Pórtico del riel: tapa", f"Plancha {f(tp0['x'][1] - tp0['x'][0])}×{f(tp0['y'][1] - tp0['y'][0])}×{f(tp0['z'][1] - tp0['z'][0])}, 2 roscas M{f(PO['d_perno'])}",
               _compound(tapas), len(tapas), "42CrMo4+QT (EN 10083-3) (núcleo: «%s»)" % PO["material"], "Oxicorte; caras fresadas; roscas M%s tras soldar" % f(PO["d_perno"]), core="cam", color=(0.5, 0.52, 0.55),
               num_fijo=ACC_NUM["leva_tapa"]))
    pr0 = PB[0]
    m.add(Part("leva_prolong", "ACC", "Prolongación de la bancada (asiento del pórtico)", f"Plancha {f(pr0['x'][1] - pr0['x'][0])}×{f(pr0['y'][1] - pr0['y'][0])}×{f(pr0['z'][1] - pr0['z'][0])}",
               _compound(prol), len(prol), A572, "Oxicorte/plasma; soldadura a la plancha base a continuación de la bancada", core="cam", color=(0.45, 0.47, 0.5), num_fijo=ACC_NUM["leva_prolong"]))
    m.add(Part("leva_rodillo", "ACC", "Seguidor: rodillo", f"Rodillo Ø{f(SG['rodillo']['d'])}/Ø{f(SG['perno']['d'])}×{f(SG['rodillo']['b'])} templado",
               _compound(rod), len(rod), "Acero templado ≥ 55 HRC (núcleo: «rodillo de leva templado»; grado A DEFINIR POR EL CALCULISTA)", "Torneado; temple y rectificado", core="cam", color=(0.3, 0.3, 0.32),
               tratamiento="Temple ≥ 55 HRC; rectificado", num_fijo=ACC_NUM["leva_rodillo"]))
    m.add(Part("leva_perno", "ACC", "Seguidor: perno", f"Perno Ø{f(SG['perno']['d'])} × {f(SG['rodillo']['z'][1] - SG['perno']['z_cara_sup_una'] + SG['perno']['empotrado_en_una'])}, empotrado {f(SG['perno']['empotrado_en_una'])} en la uña",
               _compound(pern), len(pern), propuestas.grado(P["Fy_pp"], SG["perno"]["d"], "barra"), "Barra rectificada; torno horizontal", core="cam", color=(0.3, 0.3, 0.32),
               tratamiento="Bonificado (QT)", num_fijo=ACC_NUM["leva_perno"]))
    # pernos riel–pórtico (comerciales): roscados en la tapa del pórtico
    d_b = PO["d_perno"]
    t_tapa = tp0["z"][1] - tp0["z"][0]
    Lr = max(L for L in (40, 45, 50, 55, 60) if L <= R["t"] + t_tapa - 1.0)
    bl = []
    for k in ("1_antihorario", "2_antihorario"):
        for (x, y) in inst[k]["pernos"]:
            bl.append(_cyl(1.5 * d_b / 2, d_b, R["z"][1], x, y).union(_cyl(d_b / 2, Lr, R["z"][1] - Lr, x, y)))
    m.add(Part("leva_pernos", "ACC", f"Perno ISO 4762 M{f(d_b)}×{Lr} cl. 10.9 (riel–pórtico)", f"Perno ISO 4762 M{f(d_b)}×{Lr} cl. 10.9 roscado en la tapa del pórtico", _compound(bl), len(bl),
               "Perno ISO 898-1 cl. 10.9", "Comercial", in_core=False, comercial=True, catalogo=f"ISO 4762 M{f(d_b)}×{Lr} cl. 10.9 (código de catálogo: A DEFINIR POR CATÁLOGO)", color=(0.3, 0.3, 0.32),
               num_fijo=19))
    m.info["perno_riel_L"] = Lr
    for k_ in ("leva_pata", "leva_tapa", "leva_prolong"):
        m.get(k_).libre = True
        m.get(k_).volteable = True
    return dict(ranura=F["ranura_tapa_patin"], seguidor=SG)


def ranura_patin(g, D):
    """Cortadores de la ranura de la tapa del patín (guía del perno del seguidor) en la posición del sentido antihorario."""
    F = g.FLG
    rn = F["ranura_tapa_patin"]
    out = []
    for c in D["cilindros"]["antihorario"]:
        sx, dy = c["side"], c["dir"]
        ys = c["rodEngage"][1] + dy * rn["y_respecto_pasador_vastago"]
        x0, x1 = sorted((sx * rn["x"][0], sx * rn["x"][1]))
        w = rn["ancho"]
        # extremos redondeados (ranura de fresa Ø ancho)
        xa, xb = x0 + w / 2, x1 - w / 2
        sl = _box(xa, xb, ys - w / 2, ys + w / 2, g.pk_top - 1, g.KG["shoeTop"] + 1).union(_cyl(w / 2, g.KG["shoeTop"] - g.pk_top + 2, g.pk_top - 1, xa, ys)).union(_cyl(w / 2, g.KG["shoeTop"] - g.pk_top + 2, g.pk_top - 1, xb, ys))
        out.append(sl)
    return out
