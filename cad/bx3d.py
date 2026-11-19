"""Modelo 3D de la interfaz TT300-BX (bloque «bx» del JSON de diseño, tools/export_design_bx.js): disco inoxidable de la mesa en semidiscos con
CJP, tornillos avellanados del disco roscados en la mesa, portador de acero soldado a la base con los agujeros de las pastillas, pastillas de
UHMW-PE y sus tornillos roscados en la base.

Fuente única: todas las magnitudes (radios, espesores, Ø, cantidades, posiciones, largos, profundidades, materiales, masas) se leen de D["bx"].
Nada se fija aquí salvo la representación (la pastilla se modela con el Ø nominal del agujero: la interferencia de montaje se acota en su lámina)."""
import math
import re
from types import SimpleNamespace
import cadquery as cq

from geom import fm, f, CODE


def _num(txt, default=None):
    """Primer número de un texto del JSON («1 × 45°» → 1.0)."""
    m_ = re.search(r"[\d]+(?:[.,]\d+)?", str(txt or ""))
    return float(m_.group(0).replace(",", ".")) if m_ else default


def _clase(des):
    """Clase y recubrimiento de una designación de tornillo del JSON («ISO 10642 M10 clase 10.9 (zinc laminar ISO 10683)» → «clase 10.9 (zinc laminar ISO 10683), ISO 10642»)."""
    i = des.find("clase")
    return (des[i:] + ", " + des.split(" M")[0]) if i >= 0 else des


def fab_row(g, *frags):
    """Fila de la tabla «fabricacion» del bloque bx cuya columna «pieza» contiene todos los fragmentos (minúsculas), sin nombres internos de parámetros."""
    import bx_notas
    return bx_notas.fab(g, *frags)


def pforma(X):
    """Forma de las pastillas y de los agujeros del portador según el JSON: redonda (Ø d) o cuadrada (lado, esquinas redondeadas).
    nom = medida del agujero (Ø o lado) = medida con que se modela la pastilla; pieza = medida de la pastilla terminada (con la interferencia);
    r_esq = radio de las esquinas del agujero; r_esq_p = de la pastilla; corona = (R1, R2) del contorno de las pastillas recortadas (o None);
    orient = giro fijo de los lados (°) o None (alineados con el radio)."""
    import re as _re
    PAS, POR = X["pastillas"], X["portador"]
    AG = POR["agujeros"]
    sq = str(PAS.get("forma") or AG.get("forma") or "redonda").lower().startswith("cuad")
    delta = float(PAS.get("interferencia") or (PAS.get("ajuste") or {}).get("delta") or 0.0)
    if sq:
        nom = float(AG.get("lado") or PAS.get("lado"))
        pieza = float(PAS.get("lado_corte") or PAS.get("lado_pieza") or PAS.get("lado_cortado") or (nom + delta))
        r_esq = float(AG.get("r_esquina") or PAS.get("r_esquina_agujero") or PAS.get("r_esquina") or 0.0)
        r_esq_p = float(PAS.get("r_esquina") or r_esq)
    else:
        nom = float(AG.get("d") or PAS.get("d"))
        pieza = float(PAS.get("d_torneado") or PAS.get("d_pieza") or (nom + delta))
        r_esq = r_esq_p = 0.0
    ori_txt = str(AG.get("orientacion") or PAS.get("orientacion") or "")
    orient = 0.0 if (sq and _re.search(r"paralel\w*\s+a\s+x", ori_txt)) else None
    corona = None
    for r_ in AG.get("recortadas") or []:
        m_ = _re.search(r"R(\d+(?:[.,]\d+)?)\D+R(\d+(?:[.,]\d+)?)", str(r_.get("contorno", "")))
        if m_:
            corona = (float(m_.group(1).replace(",", ".")), float(m_.group(2).replace(",", ".")))
            break
    if corona is None and AG.get("recortadas"):
        corona = (float(POR["R_int"]) + float(POR["ligamento"]), float(POR["R_ext"]) - float(POR["ligamento"]))
    return dict(sq=sq, nom=nom, pieza=pieza, r_esq=r_esq, r_esq_p=r_esq_p, delta=delta, forma=("cuadrada" if sq else "redonda"), orient=orient, corona=corona, ori_txt=ori_txt)


def ptxt(F, v, n=0, pieza=False):
    """Rótulo de la medida de una pastilla o agujero: «Ø140» o «100 × 100 (esquinas R10)»."""
    if F["sq"]:
        r_ = F["r_esq_p"] if pieza else F["r_esq"]
        return f"{fm(v, n)} × {fm(v, n)}" + (f" (esquinas R{fm(r_, 1)})" if r_ else "")
    return f"Ø{fm(v, n)}"


def porient(q, F=None):
    """Giro en planta (°) de los lados de una pastilla cuadrada: el del JSON (por pastilla o global); si no hay, alineada con el radio."""
    for k in ("rot", "ang_lado", "orient", "giro"):
        if q.get(k) is not None:
            return float(q[k])
    if F is not None and F.get("orient") is not None:
        return F["orient"]
    c = q.get("centro_agujero") or (q["x"], q["y"])
    return math.degrees(math.atan2(float(c[1]), float(c[0])))


def sitios(X):
    """Una entrada por pastilla: centro del agujero (hx, hy), giro, recortada, fracción y posición del tornillo (sx, sy): en el centro del agujero
    si la cabeza cabe con 3 mm de borde dentro del contorno recortado; si no, en el centroide de la pastilla (x, y del JSON)."""
    F = pforma(X)
    PAS = X["pastillas"]
    dk = float(PAS["cabeza"]["d_k"])
    out = []
    for q in PAS["lista"]:
        c = q.get("centro_agujero") or (q["x"], q["y"])
        hx, hy = float(c[0]), float(c[1])
        rec = bool(q.get("recortada")) and F["corona"] is not None and float(q.get("fraccion", 1)) < 0.999
        sx, sy = hx, hy
        if rec:
            rr = math.hypot(hx, hy)
            if min(rr - F["corona"][0], F["corona"][1] - rr) < dk / 2 + 3:
                sx, sy = float(q["x"]), float(q["y"])
        out.append(dict(q=q, hx=hx, hy=hy, rot=(porient(q, F) if F["sq"] else 0.0), rec=rec, f=float(q.get("fraccion", 1)), sx=sx, sy=sy))
    return out


def semiancho(F, phi_deg):
    """Semiancho de la pastilla (o del agujero, con F['nom']) a lo largo de una recta por su centro a phi° del lado (sin las esquinas)."""
    if not F["sq"]:
        return F["nom"] / 2
    c, s_ = abs(math.cos(math.radians(phi_deg))), abs(math.sin(math.radians(phi_deg)))
    return F["nom"] / 2 / max(c, s_)


def perfil(F, size, h, z0=0.0):
    """Prisma de la pastilla o del agujero (centrado en el origen, lados según x e y)."""
    if F["sq"]:
        w = cq.Workplane("XY").workplane(offset=z0).rect(size, size).extrude(h)
        if F["r_esq"] > 0:
            w = w.edges("|Z").fillet(min(F["r_esq"], size / 2 - 0.01))
        return w
    return cq.Workplane("XY").workplane(offset=z0).circle(size / 2).extrude(h)


def bolt_groups(X):
    """Tornillos del disco agrupados por anillo: [(r, [tornillos], anillo_de_pasadores, L, ciego, prof, rosca_util)] (orden de radio)."""
    T = X["disco"]["tornillos"]
    grp = {}
    for b in T["lista"]:
        grp.setdefault(round(float(b["r"]), 3), []).append(b)
    out = []
    for r in sorted(grp):
        bs = grp[r]
        b0 = bs[0]
        out.append(dict(r=r, bolts=bs, n=len(bs), anillo=bool(b0["anillo"]), L=b0["L"], ciego=bool(b0["ciego"]), prof=b0["prof"], rosca=b0["rosca_util"], t_pieza=b0["t_pieza"],
                        a0=min(((float(b["ang"]) % 360.0) for b in bs)), paso=(360.0 / len(bs)) if bs else 0.0))
    return out


def puck_groups(X):
    """Pastillas agrupadas por radio: [(r, n, ángulo inicial, paso)]."""
    grp = {}
    for q in X["pastillas"]["lista"]:
        grp.setdefault(round(float(q["r"]), 1), []).append(q)
    out = []
    for r in sorted(grp):
        qs = grp[r]
        angs = sorted((math.degrees(math.atan2(q["y"], q["x"])) % 360.0) for q in qs)
        out.append(dict(r=r, n=len(qs), a0=angs[0], paso=(360.0 / len(qs)), lista=qs, p_max=max(float(q.get("p", 0)) for q in qs)))
    return out


def lay_disco(X):
    T = X["disco"]["tornillos"]
    return SimpleNamespace(d_tor=float(T["d"]), dk=float(T["d_cabeza"]), dk_av=float(T["d_cabeza"]), d_clear=float(T["agujero_disco"]))


def lay_pastilla(X):
    Pp = X["pastillas"]
    return SimpleNamespace(d_tor=float(Pp["tornillo"]["d"]), dk=float(Pp["cabeza"]["d_k"]), dk_av=float(Pp["cabeza"]["d_k"]), d_clear=float(Pp["agujero_tornillo"]))


def build(m, g, D, log):
    """Agrega las piezas de la interfaz BX al modelo (llamado desde modelo3d_tt300c.build_interfaz)."""
    import modelo3d_tt300c as M3
    from modelo3d_tt300c import Part, cyl, ring, compound, csink_cut, screw_solid
    X = g.bx
    P = g.P
    m.layout = M3.Layout(g)              # compatibilidad con las láminas comunes (sin sectores ni topes en BX)
    DSK, POR, PAS = X["disco"], X["portador"], X["pastillas"]
    tb, z0 = g.tb, g.z0
    t_d = float(DSK["t"])
    Ri, Ro = float(DSK["R_int"]), float(DSK["R_ext"])
    zd0 = z0 - t_d                                   # cara de deslizamiento del disco (cara inferior)
    if modo_lamina(X):
        _lamina(m, g, X, Part, cyl, ring, compound)
        desc_mesa = f"lámina {fm(float(DSK['t']), 0)} soldada ({DSK['lamina']['n_paneles']} paneles, {DSK['tapones']['n']} tapones)"
    else:
        _disco_atornillado(m, g, X, Part, ring, compound, csink_cut, screw_solid)
        desc_mesa = f"disco {DSK.get('semidiscos')} semidiscos e{fm(float(DSK['t']), 0)}, {DSK['tornillos']['n']} tornillos"
    # ---- portador soldado a la base ----
    t_c = float(POR["t"])
    por = ring(float(POR["R_int"]), float(POR["R_ext"]), t_c, tb)
    F = pforma(X)
    SI = sitios(X)
    m.info["bx_forma"], m.info["bx_sitios"] = F, SI
    hp_ = [(S_["hx"], S_["hy"]) for S_ in SI]
    corona_ = ring(F["corona"][0], F["corona"][1], t_c + 4, tb - 2).val() if F["corona"] else None
    holes = []
    for S_ in SI:
        h_ = perfil(F, F["nom"], t_c + 2, tb - 1).rotate((0, 0, 0), (0, 0, 1), S_["rot"]).translate((S_["hx"], S_["hy"], 0))
        if S_["rec"]:
            h_ = cq.Workplane("XY").newObject([h_.val().intersect(corona_)])
        holes.append(h_)
    TP = POR.get("tapones") or {}
    holes += [cyl(float(TP["d"]) / 2, t_c + 2, tb - 1, float(x), float(y)) for (x, y) in (TP.get("posiciones") or [])]
    por = por.cut(compound(holes))
    fp = fab_row(g, "portador") or {}
    m.add(Part("int_bx_portador", "INT", "", f"Plancha e = {fm(t_c, 0)}, R{fm(POR['R_int'], 0)}…R{fm(POR['R_ext'], 0)}, {POR['agujeros']['n']} agujeros {ptxt(F, F['nom'])} (patrón {POR['patron']['tipo']}, paso {fm(POR['paso'], 0)}, ligamento {fm(POR['ligamento'], 0)})"
               + (f" y {TP['n']} agujeros de soldadura Ø{fm(TP['d'], 0)}" if TP.get("n") else ""), por, 1, mat_portador(X) + " — certificado EN 10204 3.1",
               fp.get("despues") or POR["corte"], core="bxPortador", color=(0.55, 0.57, 0.6),
               obs=f"{POR['corte']}; soldado a la base con filetes perimetrales z{fm(POR['filetes']['w'], 0)} exterior e interior"))
    m.info["relleno_soldadura"] = dict(m.info.get("relleno_soldadura") or {}, bxPortador=float(POR.get("masa_filetes") or 0.0))
    # ---- pastillas de UHMW-PE ----
    d_p, H = F["nom"], float(PAS["H"])
    ch_i, ch_s = _num(PAS["chaflan_inferior"], 0.0), _num(PAS["chaflan_superior"], 0.0)
    LP = lay_pastilla(X)
    rec_p = float(PAS["cabeza"]["cara_superior_cabeza_bajo_cara"])
    pk0 = perfil(F, d_p, H)                 # pastilla modelada con la medida del agujero (la interferencia se acota en su lámina)
    if ch_i > 0:
        pk0 = pk0.faces("<Z").edges().chamfer(ch_i)
    if ch_s > 0:
        pk0 = pk0.faces(">Z").edges().chamfer(ch_s)
    pks = []
    cor_p = ring(F["corona"][0], F["corona"][1], H + 4, tb - 2).val() if F["corona"] else None
    for S_ in SI:
        pk = pk0.rotate((0, 0, 0), (0, 0, 1), S_["rot"]).translate((S_["hx"], S_["hy"], tb))
        if S_["rec"]:
            pk = cq.Workplane("XY").newObject([pk.val().intersect(cor_p)])
        pk = pk.cut(compound(csink_cut(LP, S_["sx"], S_["sy"], tb + H, rec_p, -1, H)))
        pks.append(pk)
    fu = fab_row(g, "uhmw") or {}
    m.add(Part("int_bx_pastilla", "INT", "", f"Pastilla {F['forma']} {ptxt(F, F['pieza'], 2, pieza=True)} (agujero del portador {ptxt(F, d_p)}, interferencia {fm(F['delta'], 2)}) × {fm(H, 2)}, saliente {fm(PAS['h_p'], 2)}; "
               f"avellanado para {PAS['tornillo']['designacion']}", compound(pks), int(PAS["n"]), PAS["material"], PAS.get("proceso") or fu.get("despues") or "", rho=1e-9,
               mass_override=float(PAS["masa_total"]), core="uhmw", color=(0.95, 0.95, 0.85), cert="Certificado del proveedor (EN 10204 3.1)", tratamiento="Sin tratamiento; no pintar",
               obs=f"Montaje: {PAS['ajuste']['montaje']}"))
    # tornillos de las pastillas (roscan en la base, taladro ciego)
    TPp = PAS["tornillo"]
    sp = [screw_solid(LP, S_["sx"], S_["sy"], tb + H, rec_p, -1, float(TPp["L"]))[0] for S_ in SI]
    m.add(Part("int_bx_tor_pastilla", "INT", "", f"Tornillo {TPp['designacion']}, {TPp['n']} (uno por pastilla), roscado en la plancha base (taladro ciego {fm(TPp['taladro_ciego'], 0)}, rosca útil {fm(TPp['rosca_util'], 0)})",
               compound(sp), int(TPp["n"]), _clase(TPp["designacion"]), "Comercial",
               in_core=False, comercial=True, catalogo=f"{TPp['designacion']} (código de catálogo: A DEFINIR POR CATÁLOGO)", color=(0.3, 0.3, 0.32),
               obs=f"Retención de la pastilla: {TPp['apriete']}"))
    m.info["bx_holes_base"] = [(S_["sx"], S_["sy"]) for S_ in SI]
    if F["sq"] and F["r_esq"] > 0:
        m.get("int_bx_portador").radio_esquinas = F["r_esq"]
        m.get("int_bx_pastilla").radio_esquinas = F["r_esq"]
    # tabla «fabricacion» del bloque bx aplicada al proceso de las piezas comunes que cambian (despiece y fichas)
    for key, frs in (("collar", ("collar de asiento",)), ("mesa_plancha_inf", ("rebaje del collar",)), ("base_plancha", ("cara de apoyo de la base",)), ("mesa_cubo", ("rebaje del collar",))):
        import bx_notas
        p_, r_ = m.get(key), bx_notas.fab(g, *frs)
        if p_ is None or r_ is None:
            continue
        if key == "collar":
            p_.process = r_["despues"]
            p_.obs = f"{r_['motivo']} (tabla de fabricación BX: {r_['estado']})"
        else:
            p_.process = p_.process + f"; BX ({r_['estado']}): {r_['despues']}"
    log(f"  interfaz BX: {desc_mesa}; portador e{fm(t_c, 0)} con {len(hp_)} agujeros; {PAS['n']} pastillas")


def _disco_atornillado(m, g, X, Part, ring, compound, csink_cut, screw_solid):
    """Modo 0 (bx_disc_modo = 0): disco macizo en semidiscos con CJP, atornillado a la mesa con tornillos avellanados (INT-016, INT-017)."""
    DSK = X["disco"]
    t_d = float(DSK["t"])
    Ri, Ro = float(DSK["R_int"]), float(DSK["R_ext"])
    zd0 = g.z0 - t_d                                 # cara de deslizamiento del disco (cara inferior)
    LD = lay_disco(X)
    T = DSK["tornillos"]
    rec_d = float(T["cabeza_bajo_cara"])
    disc = ring(Ri, Ro, t_d, zd0)
    cuts = []
    for b in T["lista"]:
        cuts.extend(csink_cut(LD, float(b["x"]), float(b["y"]), zd0, rec_d, +1, t_d))
    disc = disc.cut(compound(cuts))
    big = 2.0 * Ro + 20.0
    halves = []
    for sgn in (1, -1):
        bx_ = cq.Workplane("XY").box(big, big / 2, t_d + 4, centered=(True, False, False)).translate((0, 0, zd0 - 2))
        if sgn < 0:
            bx_ = bx_.mirror("XZ")
        halves.append(disc.intersect(bx_))
    vol = sum(h.val().Volume() for h in halves)
    rho_d = float(DSK["masa"]) / (math.pi * (Ro ** 2 - Ri ** 2) * t_d)          # densidad implícita del núcleo (disco lleno)
    n_semi = int(DSK.get("semidiscos", 2))
    cjp = DSK["cjp"]
    fd = fab_row(g, "disco") or {}
    m.add(Part("int_bx_disco_mesa", "INT", "", f"Semidisco de {DSK['material']} e = {fm(t_d, 0)}, R{fm(Ri, 0)}…R{fm(Ro, 0)}; {n_semi} semidiscos unidos con {cjp['tipo']} ({cjp['norma']}); "
               f"{T['n']} avellanados {T['avellanado']}", compound(halves), n_semi, f"{DSK['material']} (Fy ≥ {f(DSK['Fy'])} MPa, Fu ≥ {f(DSK['Fu'])} MPa) — {DSK['fuente_material']}",
               (fd.get("despues") or "") + f"; {DSK['acabado']}", rho=rho_d, core="ss", color=(0.8, 0.82, 0.85), tratamiento="Decapado y pasivado de la CJP (ASTM A380/A967)",
               obs=f"Atornillado a la mesa ({T['n']} × {T['designacion_base']}); CJP {cjp['acabado']}"))
    m.info["bx_vol_disco"] = vol
    # tornillos del disco (roscan en la mesa): uno por posición del bloque bx
    scr = []
    for b in T["lista"]:
        w, _zt = screw_solid(LD, float(b["x"]), float(b["y"]), zd0, rec_d, +1, float(b["L"]))
        scr.append(w)
    Ls = sorted({int(b["L"]) for b in T["lista"]})
    des_ = T["designacion_base"]
    m.add(Part("int_bx_tor_mesa", "INT", "", f"Tornillo {des_} × {'/'.join(str(x) for x in Ls)}, {T['n']} en {len(T['anillos'])} anillos (malla {fm(T['paso_malla'], 0)}); cabeza {fm(rec_d, 1)} bajo la cara de deslizamiento",
               compound(scr), int(T["n"]), _clase(des_), "Comercial", in_core=False, comercial=True,
               catalogo=f"{des_} × {'/'.join(str(x) for x in Ls)} (código de catálogo: A DEFINIR POR CATÁLOGO)", color=(0.3, 0.3, 0.32),
               obs="Toman el par de la interfaz y la dilatación diferencial disco–mesa (núcleo, filas «BX · Tornillos del disco»); " + T["nota"]))
    m.info["bx_holes_mesa"] = [(float(b["x"]), float(b["y"]), bool(b["anillo"]), bool(b["ciego"]), float(b["prof"])) for b in T["lista"]]


def mat_portador(X):
    """Calidad del portador sin la nota de revisión del núcleo («ASTM A572 Gr. 50 (Fy 345, Fu 450 MPa) (rev. 6, …)» → «ASTM A572 Gr. 50 (Fy 345, Fu 450 MPa)»)."""
    return str(X["portador"]["material"]).split(" (rev.")[0].strip()


def modo_lamina(X):
    """bx_disc_modo = 1 (rev. 5 en adelante): lámina inoxidable delgada SOLDADA a la plancha inferior de la mesa (paneles, junta a tope CJP, tapones y
    costuras perimetrales; bloques disco.lamina, disco.tapones y disco.costura del JSON) en lugar del disco macizo atornillado (modo 0)."""
    return int((X.get("disco") or {}).get("modo") or 0) == 1 and bool((X["disco"].get("lamina") or {}).get("paneles"))


def tapones_por_anillo(X):
    """Tapones de la lámina agrupados por anillo: [dict(i, r, n, pista, a0, paso, lista)] en el orden del JSON (disco.tapones.anillos)."""
    TP = X["disco"]["tapones"]
    out = []
    for i, an in enumerate(TP.get("anillos") or []):
        ls = [q for q in TP["lista"] if int(q.get("anillo", -1)) == i]
        angs = sorted((math.degrees(math.atan2(float(q["y"]), float(q["x"]))) % 360.0) for q in ls)
        out.append(dict(i=i, r=float(an["r"]), n=len(ls), pista=bool(an.get("pista")), a0=(angs[0] if angs else 0.0), paso=(360.0 / len(ls) if ls else 0.0), lista=ls,
                        V=max((float(q.get("V", 0)) for q in ls), default=0.0), angs=angs))
    return out


def _lamina(m, g, X, Part, cyl, ring, compound):
    """Modo 1: lámina 304 espejo en paneles (franjas paralelas a x), agujeros Ø d de los tapones; la junta CJP entre paneles va sobre y = linea_y.
    Se modela cada panel con sus agujeros (el aporte de los tapones, la junta y las costuras es soldadura: registro de soldaduras)."""
    DSK = X["disco"]
    L, TP = DSK["lamina"], DSK["tapones"]
    t = float(L.get("espesor") or DSK["t"])
    Ri, Ro = float(L["R_int"]), float(L["R_ext"])
    zd0 = g.z0 - t
    lam = ring(Ri, Ro, t, zd0)
    hs = [cyl(float(TP["d"]) / 2, t + 2, zd0 - 1, float(q["x"]), float(q["y"])) for q in TP["lista"]]
    if hs:
        lam = lam.cut(compound(hs))
    big = 2.0 * Ro + 40.0
    pans = []
    for pn in L["paneles"]:
        y0, y1 = float(pn["y0"]), float(pn["y1"])
        bx_ = cq.Workplane("XY").box(big, y1 - y0, t + 4, centered=(True, False, False)).translate((0, y0, zd0 - 2))
        pans.append(lam.intersect(bx_))
    rho = float(DSK["masa"]) / (math.pi * (Ro ** 2 - Ri ** 2) * t)          # densidad implícita del núcleo (lámina llena)
    fl = L["formato"]
    mat = DSK["material"].split(",")[0]
    m.add(Part("int_bx_lamina", "INT", "", f"Panel de lámina {mat} e = {fm(t, 0)}, {DSK['acabado'] if DSK.get('acabado') else 'espejo'}; corona R{fm(Ri, 0)}…R{fm(Ro, 0)} en {L['n_paneles']} paneles "
               f"(formato {fm(fl[0], 0)} × {fm(fl[1], 0)}); {TP['n']} agujeros Ø{fm(TP['d'], 0)} para tapones", compound(pans), int(L["n_paneles"]),
               f"{mat} (Fy ≥ {f(DSK['Fy'])} MPa, Fu ≥ {f(DSK['Fu'])} MPa), acabado espejo — certificado EN 10204 3.1",
               f"Corte a láser o cizalla desde plancha {fm(fl[0], 0)} × {fm(fl[1], 0)} × {fm(t, 0)} con film protector; agujeros Ø{fm(TP['d'], 0)} taladrados o punzonados con plantilla; soldada a la mesa (tapones, junta y costuras)",
               rho=rho, core="ss", color=(0.82, 0.84, 0.88), tratamiento="Decapado y pasivado local de tapones, junta y costuras (ASTM A380/A967); sin pintura",
               obs=f"Soldada a la plancha inferior de la mesa: {TP['n']} tapones Ø{fm(TP['d'], 0)}, junta a tope CJP y costuras perimetrales z{fm(DSK['costura']['w'], 0)}"))
    p_ = m.get("int_bx_lamina")
    p_.volteable = False
    m.info["bx_vol_disco"] = sum(x.val().Volume() for x in pans)
    m.info["bx_holes_mesa"] = []

def holes(m):
    """Roscas de la interfaz BX en la mesa (plancha inferior pasante / anillo inferior ciego) y en la plancha base (taladros ciegos de las pastillas)."""
    from modelo3d_tt300c import cyl, compound
    g = m.g
    X = g.bx
    d_m = float(X["disco"]["tornillos"].get("d") or 0.0)
    pl, an = [], []
    for (x, y, anillo, ciego, prof) in m.info.get("bx_holes_mesa") or []:
        if anillo or ciego:
            an.append(cyl(d_m / 2, prof + 1, g.z0 - 1, x, y))
        else:
            pl.append(cyl(d_m / 2, g.tbo + 2, g.z0 - 1, x, y))
    for k_, lst in (("mesa_plancha_inf", pl), ("mesa_anillo_inf" if m.get("mesa_anillo_inf") else "mesa_plancha_inf", an)):   # rev. 7c: plancha entera (sin anillo)
        if lst:
            p_ = m.get(k_)
            p_.solid = p_.solid.cut(compound(lst))
            p_._vol = None
    TPp = X["pastillas"]["tornillo"]
    hb = [cyl(float(TPp["d"]) / 2, float(TPp["taladro_ciego"]) + 1, g.tb - float(TPp["taladro_ciego"]), x, y) for (x, y) in m.info.get("bx_holes_base") or []]
    if hb:
        b_ = m.get("base_plancha")
        b_.solid = b_.solid.cut(compound(hb))
        b_._vol = None


def disco_recorte(g, cx, cy, hw, z0, z1, rot=0.0):
    """Recorte del disco BX a la caja |x − cx| ≤ hw, |y − cy| ≤ hw, z0…z1 en el sistema girado rot° (cortes de detalle). Se reconstruye desde el
    JSON en ese sistema (la corona no cambia al girar; se giran los centros de los avellanados y la línea de la CJP) porque el booleano de OCC
    sobre el disco completo con todos los avellanados falla con cajas giradas."""
    from modelo3d_tt300c import ring, compound, csink_cut, cyl
    X = g.bx
    DSK = X["disco"]
    if modo_lamina(X):
        return _lamina_recorte(g, X, cx, cy, hw, z0, z1, rot, ring, compound, cyl)
    T = DSK["tornillos"]
    t_d, Ri, Ro = float(DSK["t"]), float(DSK["R_int"]), float(DSK["R_ext"])
    zd0 = g.z0 - t_d
    LD = lay_disco(X)
    box = cq.Solid.makeBox(2 * hw, 2 * hw, z1 - z0, cq.Vector(cx - hw, cy - hw, z0))
    loc = ring(Ri, Ro, t_d, zd0).val().intersect(box)
    if not loc.Solids():
        return []
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    cuts = []
    for b in T["lista"]:
        x, y = float(b["x"]) * ca - float(b["y"]) * sa, float(b["x"]) * sa + float(b["y"]) * ca
        if abs(x - cx) <= hw + 15 and abs(y - cy) <= hw + 15:
            cuts.extend(csink_cut(LD, x, y, zd0, float(T["cabeza_bajo_cara"]), +1, t_d))
    if cuts:
        loc = loc.cut(compound(cuts).val())
    # la línea de la CJP (eje x del equipo) queda a rot° en este sistema: se parte el recorte solo si la cruza
    nx, ny = -sa, ca
    ds = [(x_ - 0) * nx + (y_ - 0) * ny for x_ in (cx - hw, cx + hw) for y_ in (cy - hw, cy + hw)]
    if min(ds) < 0 < max(ds):
        big = 2.0 * Ro + 20.0
        out = []
        for sgn in (1, -1):
            hb = cq.Solid.makeBox(big, big / 2, t_d + 4, cq.Vector(-big / 2, 0 if sgn > 0 else -big / 2, zd0 - 2)).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rot)
            out.extend(loc.intersect(hb).Solids())
        if abs(sum(x_.Volume() for x_ in out) - loc.Volume()) <= 1e-3 * loc.Volume():
            return out
    return loc.Solids()


def _lamina_recorte(g, X, cx, cy, hw, z0, z1, rot, ring, compound, cyl):
    """Modo 1: recorte de la lámina (corona con los agujeros de los tapones, partida en las líneas de la junta) en el sistema girado rot°."""
    DSK = X["disco"]
    L, TP = DSK["lamina"], DSK["tapones"]
    t = float(L.get("espesor") or DSK["t"])
    Ri, Ro = float(L["R_int"]), float(L["R_ext"])
    zd0 = g.z0 - t
    box = cq.Solid.makeBox(2 * hw, 2 * hw, z1 - z0, cq.Vector(cx - hw, cy - hw, z0))
    loc = ring(Ri, Ro, t, zd0).val().intersect(box)
    if not loc.Solids():
        return []
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    cuts = []
    for q in TP["lista"]:
        x, y = float(q["x"]) * ca - float(q["y"]) * sa, float(q["x"]) * sa + float(q["y"]) * ca
        if abs(x - cx) <= hw + 15 and abs(y - cy) <= hw + 15:
            cuts.append(cyl(float(TP["d"]) / 2, t + 2, zd0 - 1, x, y))
    if cuts:
        loc = loc.cut(compound(cuts).val())
    nx, ny = -sa, ca
    big = 2.0 * Ro + 40.0
    for yl in (L.get("junta") or {}).get("lineas_y") or []:
        ds = [x_ * nx + y_ * ny - float(yl) for x_ in (cx - hw, cx + hw) for y_ in (cy - hw, cy + hw)]
        if min(ds) < 0 < max(ds):
            out = []
            for sgn in (1, -1):
                hb = cq.Solid.makeBox(big, big / 2, t + 4, cq.Vector(-big / 2, float(yl) + (0 if sgn > 0 else -big / 2), zd0 - 2)).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rot)
                out.extend(loc.intersect(hb).Solids())
            if abs(sum(x_.Volume() for x_ in out) - loc.Volume()) <= 1e-3 * loc.Volume():
                return out
    return loc.Solids()


def _lista_txt(vals):
    """«a…b paso s (n)» si los valores son equiespaciados; si no, la lista."""
    v = sorted(vals)
    if len(v) > 2:
        d = [v[i + 1] - v[i] for i in range(len(v) - 1)]
        if max(d) - min(d) < 0.02:
            return f"{fm(v[0], 1)} … {fm(v[-1], 1)} paso {fm(d[0], 1)}"
    return "; ".join(fm(x, 1) for x in v)


def tabla_posiciones(X):
    """Tabla de centros de los agujeros (y pastillas): por anillos (patrón radial de pastillas redondas o giradas con el radio) o por filas y
    (malla cartesiana de pastillas cuadradas). Devuelve (título, columnas, filas, anillos) con anillos = [(r, [sitios])] o None."""
    SI = sitios(X)
    F = pforma(X)
    if F["sq"] and F["orient"] is not None:
        fil = {}
        for S_ in SI:
            fil.setdefault(round(S_["hy"], 1), []).append(S_["hx"])
        rows = [[fm(y, 1), _lista_txt(xs), str(len(xs))] for y, xs in sorted(fil.items())]
        return ("CENTROS DE LOS AGUJEROS POR FILA (origen en el eje del equipo; " + F["ori_txt"] + "; teóricamente exactos)",
                [("y [mm]", 18, "R"), ("x [mm]", 120, "L"), ("Cant", 12, "C")], rows, None)
    grp = {}
    for S_ in SI:
        grp.setdefault(round(math.hypot(S_["hx"], S_["hy"]), 1), []).append(S_)
    rows, an = [], []
    for i, (r, ss) in enumerate(sorted(grp.items())):
        angs = sorted(math.degrees(math.atan2(S_["hy"], S_["hx"])) % 360.0 for S_ in ss)
        n = len(angs)
        d = [angs[k + 1] - angs[k] for k in range(n - 1)]
        at = (f"{fm(angs[0], 3)}° + {fm(360.0 / n, 3)}°·k (k = 0…{n - 1})" if n > 1 and max(d) - min(d) < 0.02 and abs(360.0 - angs[-1] + angs[0] - d[0]) < 0.02
              else ", ".join(fm(a, 2) + "°" for a in angs))
        rows.append([f"P{i + 1}", fm(r, 1), str(n), at, fm(max(float(S_["q"].get("p", 0)) for S_ in ss), 2)])
        an.append((r, ss))
    return ("AGUJEROS DE LAS PASTILLAS POR ANILLO (centros; ángulos desde +x, antihorario; teóricamente exactos)",
            [("Anillo", 12, "C"), ("R [mm]", 16, "R"), ("Cant", 10, "C"), ("Ángulos", 84, "L"), ("p máx. [MPa]", 20, "R")], rows, an)


def tabla_recortadas(X):
    """Filas de las pastillas/agujeros recortados por la corona: centro del agujero, fracción y posición del tornillo."""
    out = []
    for i, S_ in enumerate(sitios(X)):
        if S_["rec"]:
            out.append([str(i + 1), f"{fm(S_['hx'], 1)}; {fm(S_['hy'], 1)}", fm(S_["f"], 3), f"{fm(S_['sx'], 1)}; {fm(S_['sy'], 1)}"])
    return out
