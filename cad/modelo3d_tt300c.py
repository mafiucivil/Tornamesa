"""Modelo 3D TT300-C (CadQuery) desde cad/out/TT300-C_design.json: piezas con código de ítem, STEP de ensamble, GLB,
masas y centro de gravedad frente al núcleo, y control de interferencias.
Uso: python3 cad/modelo3d_tt300c.py [design.json] [--out DIR]
Ejes: z vertical desde la cara inferior de la base; x, y en planta como en los planos.
Se dibujan las alternativas de interfaz del cálculo (P.opt_ss, P.opt_uhmw, P.opt_bz con bz_conf 1/2/3), la fijación
desmontable por sectores (fix_mode = 1) o pegada (fix_mode = 2, sin topes ni tornillos), el collar del pivote, las orejas de
izaje y la cubierta de madera con su anillo (opt_wood)."""
import json, math, sys, pathlib, time
import cadquery as cq

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import *
import propuestas

# ----------------------------------------------------------------------------------------------
# primitivas
# ----------------------------------------------------------------------------------------------
def cyl(r, h, z0=0.0, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(h)


def ring(r0, r1, h, z0=0.0):
    w = cq.Workplane("XY").workplane(offset=z0).circle(r1)
    if r0 > 0:
        w = w.circle(r0)
    return w.extrude(h)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def rotz(wp, deg):
    return wp.rotate((0, 0, 0), (0, 0, 1), deg)


def place(wp, phi_deg, E):
    return wp.rotate((0, 0, 0), (0, 0, 1), phi_deg).translate((E[0], E[1], 0))


def union_all(items):
    it = [i for i in items if i is not None]
    r = it[0]
    for x in it[1:]:
        r = r.union(x)
    return r


def compound(items):
    """Agrupa sólidos disjuntos sin operación booleana."""
    sol = []
    for i in items:
        sol.extend(i.vals() if hasattr(i, "vals") else [i])
    return cq.Workplane("XY").newObject([cq.Compound.makeCompound([s if isinstance(s, cq.Shape) else s for s in sol])])


def polar(r, deg):
    return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))


ISO273 = {4: 4.5, 5: 5.5, 6: 6.6, 8: 9.0, 10: 11.0, 12: 13.5}       # agujero pasante medio
ISO10642_DK = {4: 8.0, 5: 10.0, 6: 12.0, 8: 16.0, 10: 20.0, 12: 24.0}  # Ø de la cabeza avellanada
ISO10642_L = [8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50]


class Part:
    def __init__(self, key, sub, name, desc, solid, qty=1, material="", process="", rho=RHO, mass_override=None, core=None,
                 comercial=False, obs="", color=(0.6, 0.6, 0.62), tratamiento="—", cert="EN 10204 3.1", catalogo=None, in_core=True):
        self.key, self.sub, self.name, self.desc, self.solid, self.qty = key, sub, name, desc, solid, qty
        self.material, self.process, self.rho, self.mass_override, self.core = material, process, rho, mass_override, core
        self.comercial, self.obs, self.color, self.tratamiento, self.cert, self.catalogo = comercial, obs, color, tratamiento, cert, catalogo
        self.in_core = in_core
        self.num = 0
        self.pos = 0
        self._vol = None

    @property
    def code(self):
        return f"{CODE}-{self.sub}-{self.num:03d}-{REV}"

    @property
    def volume(self):
        if self._vol is None:
            self._vol = sum(s.Volume() for s in self.solid.vals())
        return self._vol

    @property
    def mass_total(self):
        return self.mass_override if self.mass_override is not None else self.volume * self.rho

    @property
    def mass_unit(self):
        return self.mass_total / self.qty

    def center(self):
        c = cq.Compound.makeCompound(list(self.solid.vals())).Center()
        return (c.x, c.y, c.z)


class Model:
    def __init__(self, D, g):
        self.D, self.g, self.parts = D, g, []
        self.info = {}
        self.sub_count = {}

    def add(self, p):
        self.sub_count[p.sub] = self.sub_count.get(p.sub, 0) + 1
        p.num = self.sub_count[p.sub]
        self.parts.append(p)
        p.pos = len(self.parts)
        return p

    def get(self, key):
        return next((p for p in self.parts if p.key == key), None)

    def has(self, key):
        return self.get(key) is not None


# ----------------------------------------------------------------------------------------------
# sectores de interfaz
# ----------------------------------------------------------------------------------------------
def ring_sector_local(r0, r1, span_deg, gap, z0, t, mode="parallel"):
    """Sector anular con la bisectriz sobre +x. mode 'parallel': bordes paralelos a las radiales de contorno, separados 'gap'
    entre sectores vecinos (junta de ancho constante); 'radial': bordes radiales con ángulo total span_deg."""
    h = math.radians(span_deg / 2)
    far = 2.0 * r1
    if mode == "parallel":
        ax = (gap / 2) / math.sin(h)
        pts = [(ax, 0), (ax + far * math.cos(h), far * math.sin(h)), (ax + far * math.cos(h), -far * math.sin(h))]
    else:
        pts = [(0, 0), (far * math.cos(h), far * math.sin(h)), (far * math.cos(h), -far * math.sin(h))]
    wedge = cq.Workplane("XY").workplane(offset=z0 - 1).polyline(pts).close().extrude(t + 2)
    return ring(r0, r1, t, z0).intersect(wedge), pts


class Layout:
    """Distribución de fijaciones, ranuras y topes de la interfaz (coordenadas polares en el sistema de la mesa)."""

    def __init__(self, g):
        self.g = g
        P = g.P
        self.th = 360.0 / g.n_sec
        self.b_tope, self.w_tope = P["b_tope"], P["w_tope"]
        self.d_tor = P["d_tor"]
        self.L_base = g.tope_L("base")
        self.L_mesa = g.tope_L("mesa")
        self.tp_base, self.tp_mesa, self.tp_uhmw = g.tope("base"), g.tope("mesa"), g.tope("uhmw")   # geometría resuelta por el núcleo (interfazGeom.topes)
        self.a_inf = (self.tp_base or {}).get("a_inf", 0.0)
        self.a_sup = (self.tp_base or {}).get("a_sup", 0.0)
        # ranuras circunferenciales (S05)
        n = g.n_gr_circ
        rg = []
        if n >= 1:
            rg.append(g.Ro - 30.0)
        if n >= 2:
            r_in = g.Ri + 30.0
            rg += [g.Ro - 30.0 - k * (g.Ro - 30.0 - r_in) / (n - 1) for k in range(1, n)]
        self.r_circ = rg
        self.phi_rad = [k * 360.0 / g.n_gr_rad for k in range(g.n_gr_rad)]
        self.dk = ISO10642_DK.get(int(self.d_tor), 2 * self.d_tor)
        self.d_clear = ISO273.get(int(self.d_tor), self.d_tor * 1.1)

    def screw_len(self, t, rec):
        need = t - rec + 1.5 * self.d_tor
        return next((L for L in ISO10642_L if L >= need), math.ceil(need))

    def screw_radii(self, L_notch, grooves=True):
        """Dos radios sobre la bisectriz, entre la muesca y cada borde, libres de ranuras circunferenciales."""
        g = self.g
        a, b = g.r_u - L_notch / 2, g.r_u + L_notch / 2
        c1, c2 = (g.Ri + a) / 2, (b + g.Ro) / 2
        out = []
        r_lim = g.R_pin - g.d_pin / 2 - self.dk / 2 - 4.0                 # el tornillo exterior no debe caer sobre los pasadores de empuje (Ø d_pin en R_pin) de la plancha inferior de la mesa
        c2 = min(c2, r_lim) if r_lim > b + self.dk else c2
        for c, step in ((c1, -8.0), (c2, -8.0 if c2 >= r_lim - 1e-9 else 8.0)):
            r = c
            for _ in range(60):
                if not grooves or all(abs(r - rg) > g.w_gr / 2 + self.dk / 2 + 3 for rg in self.r_circ):
                    break
                r += step
            out.append(r)
        return out


def chamfer_cutters(x0, x1, hw, a, z_back, sgn, sides=(1, -1)):
    """Cuñas que dejan en el canto del sector el chaflán 45° de a_inf = w_tope + 1 mm que libra el filete del tope (núcleo: stopsOf).
    Marco local: la barra va sobre el eje x, entre x0 y x1; el canto (pared de la muesca) está a la distancia hw del eje; z_back = cara del respaldo; sgn = +1 si
    el sector está sobre el respaldo (cuña hacia +z), −1 si está bajo él. Sección triangular (hw, z_back)-(hw + a, z_back)-(hw, z_back + sgn·a), con 1 mm de sobrecorte."""
    out = []
    e = 1.0
    for sd in sides:
        pts = [(hw - 0.5, -e), (hw + a + e, -e), (hw - 0.5, a + 0.5)]
        pts = [(sd * y, sgn * z + z_back) for (y, z) in pts]
        w = cq.Workplane("YZ").workplane(offset=x0).polyline(pts).close().extrude(x1 - x0)
        out.append(w)
    return out


def sector_features(g, lay, idx, a_deg, t, z_face, face, L_notch, grooves, plugs=None, rec=0.0, span=None, with_notch=True):
    """Cortes de un sector (ya en el sistema local con la bisectriz en +x). face: 'top' (cara deslizante arriba) o 'bot'."""
    cuts = []
    zs = z_face
    # muesca pasante del tope
    if with_notch and L_notch:
        cuts.append(box(g.r_u - L_notch / 2, g.r_u + L_notch / 2, -(lay.b_tope + 2) / 2, (lay.b_tope + 2) / 2, zs - t - 1, zs + 1))
    return cuts


def csink_cut(lay, x, y, z_slide, rec, s, t):
    """Corte del disco/placa para un tornillo avellanado ISO 10642: contraperforado hasta la cabeza, cono de 90° y agujero pasante.
    s = −1 si el material está bajo la cara deslizante (cara arriba), +1 si está sobre ella."""
    d, dk, dc = lay.d_tor, lay.dk, lay.d_clear
    z_ht = z_slide + s * (-rec) if False else z_slide + (-s) * rec          # cara superior de la cabeza (recesada rec dentro del material)
    z_ht = z_slide + s * rec
    rim = 0.05 * d
    zc0 = z_ht + s * rim                                                     # inicio del cono (radio dk/2)
    hcone = (dk - dc) / 2
    cuts = []
    zlo, zhi = (min(z_slide - s * 1.0, zc0), max(z_slide - s * 1.0, zc0))
    cuts.append(cyl(dk / 2, zhi - zlo, zlo, x, y))                           # contraperforado (desde la cara hasta el cono)
    cone = cq.Solid.makeCone(dk / 2, dc / 2, hcone, pnt=cq.Vector(x, y, zc0), dir=cq.Vector(0, 0, s))
    cuts.append(cq.Workplane("XY").newObject([cone]))
    z_end = z_slide + s * t
    zlo, zhi = min(zc0, z_end) - (1 if s > 0 else 0), max(zc0, z_end) + (0 if s > 0 else 1)
    cuts.append(cyl(dc / 2, abs(z_end - zc0) + 2, min(zc0, z_end) - 1, x, y))
    return cuts


def screw_solid(lay, x, y, z_slide, rec, s, L):
    d, dk = lay.d_tor, lay.dk
    z_ht = z_slide + s * rec
    rim = 0.05 * d
    cs = (dk - d) / 2
    z1 = z_ht + s * rim
    z2 = z1 + s * cs
    rimc = cq.Solid.makeCylinder(dk / 2, rim, pnt=cq.Vector(x, y, min(z_ht, z1)), dir=cq.Vector(0, 0, 1))
    cone = cq.Solid.makeCone(dk / 2, d / 2, cs, pnt=cq.Vector(x, y, z1), dir=cq.Vector(0, 0, s))
    ztip = z_ht + s * L
    shank = cq.Solid.makeCylinder(d / 2, abs(ztip - z2), pnt=cq.Vector(x, y, min(z2, ztip)), dir=cq.Vector(0, 0, 1))
    w = cq.Workplane("XY").newObject([rimc]).union(cq.Workplane("XY").newObject([cone])).union(cq.Workplane("XY").newObject([shank]))
    return w, ztip


def make_sector_set(g, lay, M, key_prefix, r0, r1, n, t, z_base, face, L_notch, rho, groove_depth=0.0, plug=None, mode="parallel", span_deg=None,
                    gap=None, screw_rec=0.0, with_screws=True, angle0=0.0, notch=True, greaser=False, chamfer=0.0):
    """Genera n sectores, devuelve (compuesto_de_sectores, lista_de_sectores_locales_info, tornillos, topes).
    face: cara deslizante 'top' (z = z_base + t) o 'bot' (z = z_base)."""
    th = 360.0 / n
    span = span_deg if span_deg else th
    sectors, screws, holes_resp = [], [], []
    z_slide = z_base + t if face == "top" else z_base
    radii = lay.screw_radii(L_notch or 0, grooves=groove_depth > 0) if with_screws else []
    base_sec, pts = ring_sector_local(r0, r1, span, gap or 0, z_base, t, mode)
    for i in range(n):
        a = angle0 + (i + 0.5) * th
        s = base_sec
        cuts = []
        if notch and L_notch:
            cuts.append(box(g.r_u - L_notch / 2, g.r_u + L_notch / 2, -(lay.b_tope + 2) / 2, (lay.b_tope + 2) / 2, z_base - 1, z_base + t + 1))
            if chamfer > 0:                                    # alivio inferior del canto: chaflán 45° a_inf en el lado del respaldo (base: abajo; mesa: arriba)
                cuts.extend(chamfer_cutters(g.r_u - L_notch / 2, g.r_u + L_notch / 2, (lay.b_tope + 2) / 2, chamfer, z_base if face == "top" else z_base + t, +1 if face == "top" else -1))
        # tornillos de posición (S01): agujero pasante con avellanado
        if with_screws and g.removable:
            sg = -1 if face == "top" else 1
            for r in radii:
                cuts.extend(csink_cut(lay, r, 0.0, z_slide, screw_rec, sg, t))
        # ranuras de engrase en la cara deslizante
        if groove_depth > 0:
            zg0 = z_slide - groove_depth if face == "top" else z_slide
            for phi in lay.phi_rad:
                d = ((phi - a + 180) % 360) - 180
                if abs(d) < span / 2 + 3:
                    gx = box(r0 - 1, r1 + 1, -g.w_gr / 2, g.w_gr / 2, zg0, zg0 + groove_depth + (1 if face == "top" else 0))
                    cuts.append(rotz(gx, d))
            for rg in lay.r_circ:
                gr = ring(rg - g.w_gr / 2, rg + g.w_gr / 2, groove_depth + 1, zg0 if face == "top" else z_slide - 1)
                cuts.append(gr)
        if plug is not None and plug.get(i):
            cuts.append(plug[i]["holes"])
        for c in cuts:
            s = s.cut(c)
        sectors.append(rotz(s, a))
    return sectors, radii


# ----------------------------------------------------------------------------------------------
# construcción del modelo
# ----------------------------------------------------------------------------------------------
def build(D, verbose=True):
    g = G(D)
    P, DV, M = g.P, g.DV, g.M
    m = Model(D, g)
    m.G = g
    t0 = time.time()
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    tb, hd, tt, tbo, tpr, Rt, prIn, hw = g.tb, g.hd, g.tt, g.tbo, g.tpr, g.Rt, g.prIn, g.hw
    z0, zc, zb = g.z0, g.zc, g.zb
    d_pin, R_pin, d_bush = g.d_pin, g.R_pin, g.d_bush
    BR, KG = g.BR, g.KG
    Llug = BR["Llug"]
    pin_xy = [polar(R_pin, a) for a in D["pasadores"]]
    A572 = f"ASTM A572 Gr.50 (Fy ≥ {f(P['Fy'])} MPa)"
    A572Z = A572 + ", Z35 (EN 10164), UT ASTM A578 nivel B"

    # ===================== BAS: base =====================
    B = g.B
    base = box(-B / 2, B / 2, -B / 2, B / 2, 0, tb).cut(cyl(P["D_piv"] / 2, tb + 2, -1))
    screw_base = []            # agujeros roscados de los tornillos de posición en la plancha base
    base_plate_holes = None
    m.add(Part("base_plancha", "BAS", "Plancha base", f"Plancha {f(B)}×{f(B)}×{f(tb)}, agujero central Ø{f(P['D_piv'])} H7 (mandrinado en línea con el collar)",
               base, 1, A572Z, "Oxicorte/plasma de la plancha, soldadura del conjunto, alivio de tensiones, mandrinado del agujero H7 en mandrinadora y planeado de la cara de apoyo de la interfaz",
               core="base", color=(0.55, 0.57, 0.6), obs=f"Planitud {fm(0.20, 2)} mm en la zona Ø{f(P['D_top'] + 20)} (cara de apoyo de la interfaz); sin pintura en esa zona"))
    if g.boss:
        collar = ring(0, g.D_boss / 2, g.h_boss, tb).cut(cyl(P["D_piv"] / 2, g.h_boss + 2, tb - 1))
        m.add(Part("collar", "BAS", "Collar de asiento del pivote", f"Disco Ø{f(g.D_boss)}×{f(g.h_boss)} con agujero Ø{f(P['D_piv'])} H7, soldado a la plancha base (filete perimetral {fm(g.w_collar, 0)})",
                   collar, 1, A572, "Oxicorte/plasma de disco desde plancha de 60 mm, soldadura a la base, mandrinado H7 en línea con la plancha base (mandrinadora)", core="base", color=(0.5, 0.52, 0.55),
                   obs="Sin torno vertical: se corta a llama el disco y se mandrina el agujero; el diámetro exterior queda en bruto de corte (tolerancia ISO 2768-m)"))
    r_t, r_h = P["rim_t"], P["rim_h"]
    rim_l = [box(-B / 2, B / 2, -B / 2, -B / 2 + r_t, tb, tb + r_h), box(-B / 2, B / 2, B / 2 - r_t, B / 2, tb, tb + r_h)]
    rim_s = [box(-B / 2, -B / 2 + r_t, -B / 2 + r_t, B / 2 - r_t, tb, tb + r_h), box(B / 2 - r_t, B / 2, -B / 2 + r_t, B / 2 - r_t, tb, tb + r_h)]
    m.add(Part("marco_largo", "BAS", "Marco perimetral largo", f"Pletina {f(r_t)}×{f(r_h)}×{f(B)}", compound(rim_l), 2, A572, "Corte a sierra/plasma; soldadura a la plancha base", core="rim", color=(0.55, 0.57, 0.6)))
    m.add(Part("marco_corto", "BAS", "Marco perimetral corto", f"Pletina {f(r_t)}×{f(r_h)}×{f(B - 2 * r_t)}", compound(rim_s), 2, A572, "Corte a sierra/plasma; soldadura a la plancha base y a las largas", core="rim", color=(0.55, 0.57, 0.6)))
    mej, osup, oinf = [], [], []
    for grp in ("horario", "antihorario"):
        for c in D["cilindros"][grp]:
            x0, x1 = -BR["rear"], P["L_ch"] - BR["rear"]
            mej.append(place(box(x0, x1, BR["Win"] / 2, BR["Wout"] / 2, tb, tb + BR["H"]).union(box(x0, x1, -BR["Wout"] / 2, -BR["Win"] / 2, tb, tb + BR["H"])), c["phiMean"], c["eye"]))
            osup.append(place(box(x0, Llug - BR["rear"], -BR["Win"] / 2, BR["Win"] / 2, tb + BR["H"] - P["t_ch"], tb + BR["H"]).cut(cyl(P["d_pp"] / 2, BR["H"] + 2, tb - 1)), c["phiMean"], c["eye"]))
            oinf.append(place(box(x0, Llug - BR["rear"], -BR["Win"] / 2, BR["Win"] / 2, tb, tb + BR["spacer"] + P["t_ch"]).cut(cyl(P["d_pp"] / 2, BR["H"] + 2, tb - 1)), c["phiMean"], c["eye"]))
    nb = len(osup)
    m.add(Part("mensula_mejilla", "BAS", "Mejilla de ménsula", f"Plancha {f(P['L_ch'])}×{f(BR['H'])}×{f(P['t_ch'])}", compound(mej), 2 * nb, A572, "Plasma; soldadura a la base (filete 4 líneas por ménsula)", core="brackets", color=(0.5, 0.52, 0.55)))
    m.add(Part("mensula_oreja_sup", "BAS", "Oreja superior de ménsula", f"Plancha {f(BR['Win'])}×{f(Llug)}×{f(P['t_ch'])}, agujero Ø{f(P['d_pp'])} H9 (mandrinado después de soldar)", compound(osup), nb, A572,
               "Plasma; soldadura a las mejillas; agujero H9 en línea en taladro radial/mandrinadora tras soldar", core="brackets", color=(0.5, 0.52, 0.55)))
    m.add(Part("mensula_oreja_inf", "BAS", "Oreja inferior (bloque) de ménsula", f"Plancha {f(BR['Win'])}×{f(Llug)}×{f(BR['spacer'] + P['t_ch'])}, agujero Ø{f(P['d_pp'])} H9", compound(oinf), nb, A572,
               "Plasma (o pletinas apiladas); soldadura a mejillas y base; agujero H9 en línea tras soldar", core="brackets", color=(0.5, 0.52, 0.55)))
    # ===================== IZA: orejas de izaje =====================
    Rr, hE, tE, dE = P["R_ear"], P["h_ear"], P["t_ear"], P["d_ear"]
    ear_prof = (cq.Workplane("XZ").moveTo(-Rr, 0).lineTo(Rr, 0).lineTo(Rr, hE).threePointArc((0, hE + Rr), (-Rr, hE)).close().extrude(tE / 2, both=True)
                .cut(cq.Workplane("XZ").center(0, hE).circle(dE / 2).extrude(tE, both=True)))
    ears = []
    for (x, y) in g.ear_pos:
        ears.append(ear_prof.rotate((0, 0, 0), (0, 0, 1), math.degrees(math.atan2(y, x))).translate((x, y, tb)))
    m.add(Part("orejas", "IZA", "Oreja de izaje", f"Plancha e={f(tE)}: base {f(2 * Rr)} × altura {f(hE)} + semicírculo R{f(Rr)}, agujero Ø{f(dE)} a {f(hE)} sobre la base",
               compound(ears), 4, A572, "Oxicorte/plasma (perfil y agujero), biselado de la base de apoyo, soldadura a la base con filete a ambos lados; plano de la oreja en el plano radial hacia el centro",
               core="base", color=(0.9, 0.35, 0.2), obs="Agujero de oreja a cota exacta de plantilla; grillete con pasador ≤ d − 3"))
    # ===================== ACC: bancadas =====================
    beds = []
    for sx in (1, -1):
        X = sx * P["x_g"]
        bd = box(X - P["w_bed"] / 2, X + P["w_bed"] / 2, -KG["Y_bed"], KG["Y_bed"], tb, zb).cut(
            box(X - P["w_slot"] / 2, X + P["w_slot"] / 2, -KG["Y_bed"] - 1, KG["Y_bed"] + 1, zb - P["h_slot"], zb + 1))
        if P["h_tee"] > 0:
            bd = bd.cut(box(X - P["w_tee"] / 2, X + P["w_tee"] / 2, -KG["Y_bed"] - 1, KG["Y_bed"] + 1, g.zT0, g.zT1))
        beds.append(bd)
    m.add(Part("bancada", "ACC", "Bancada de guía con ranura T", f"Plancha {f(P['w_bed'])}×{f(P['t_bed'])}×{f(KG['L_bed'])}; ranura T: cuello {f(P['w_slot'])} H8 × {f(P['h_slot'])}, cabeza {f(P['w_tee'])}×{f(P['h_tee'])}, fondo {f(g.fondo)}",
               compound(beds), P["n_cyl"], A572, "Plasma/sierra; soldadura a la base; ranura T pasante fresada en mandrinadora o cepillo tras soldar y relevar; flancos Ra 1,6", core="beds", color=(0.45, 0.47, 0.5),
               obs="Ranura T pasante: el patín entra por el extremo"))

    # ===================== MES: mesa =====================
    pins_cut = lambda wp, z, h: wp.cut(cq.Workplane("XY").workplane(offset=z - 1).pushPoints(pin_xy).circle(d_pin / 2).extrude(h + 2))
    ri_bot = g.Drb / 2 if g.rebaje else d_bush / 2                       # agujero pasante Ø D_rebaje_bot (= D_boss + 2 c_boss_r) en la plancha inferior en TODOS los casos con collar y rebaje (núcleo: hPl)
    disc_bot = ring(ri_bot, prIn, tbo, z0)
    ring_bot = pins_cut(ring(prIn, Rt, tpr, z0), z0, tpr)
    disc_top = ring(g.hole_top / 2, prIn, tt, z0 + hd - tt).cut(cyl(g.cb_D / 2, g.cb_t + 1, z0 + hd - g.cb_t)) if False else None
    top_plate = ring(g.hole_top / 2, prIn, tt, z0 + hd - tt)
    top_plate = top_plate.cut(ring(0, g.cb_D / 2, g.cb_t + 1, z0 + hd - g.cb_t))             # rebaje de la tapa de inspección
    insp_xy = [(g.insp_pcd / 2 * math.cos(math.radians(30 + 60 * i)), g.insp_pcd / 2 * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
    top_plate = top_plate.cut(cq.Workplane("XY").workplane(offset=z0 + hd - g.cb_t - g.insp_tap).pushPoints(insp_xy).circle(g.tap_m10 / 2).extrude(g.insp_tap + 0.5))   # 6 × M10 (broca Ø8,5) prof. 10 desde el fondo del rebaje
    ring_top = pins_cut(ring(prIn, Rt, tpr, z0 + hd - tpr), z0 + hd - tpr, tpr)
    m.add(Part("mesa_plancha_sup", "MES", "Plancha superior de la mesa", f"Disco Ø{f(2 * prIn)}×{f(tt)} con agujero Ø{f(g.hole_top)} y rebaje Ø{f(g.cb_D)}×{f(g.cb_t)} para la tapa de inspección",
               top_plate, 1, A572Z, "Oxicorte/plasma desde plancha (o 2 mitades con empalme CJP); rebaje fresado en mandrinadora; soldadura", core="top", color=(0.22, 0.4, 0.7)))
    m.add(Part("mesa_anillo_sup", "MES", "Anillo superior de pasadores", f"Anillo Ø{f(P['D_top'])}/Ø{f(2 * prIn)}×{f(tpr)}, {g.N_pin} agujeros Ø{f(d_pin)} H7 (4 segmentos de 90°, empalmes CJP)", ring_top, 1, A572Z,
               "Plasma por segmentos de 90°; soldadura CJP de empalmes (UT 100 %); agujeros Ø80 en taladro radial y mandrinado a Ø85 H7 en línea con el anillo inferior", core="top", color=(0.22, 0.4, 0.7)))
    m.add(Part("mesa_plancha_inf", "MES", "Plancha inferior de la mesa", f"Disco Ø{f(2 * prIn)}×{f(tbo)}, agujero central Ø{f(2 * ri_bot)}" + (f" PASANTE (rebaje del collar: Ø{f(g.D_boss)} + 2×{fm(g.c_boss_r, 0)} de holgura radial)" if g.rebaje else ""), disc_bot, 1, A572Z,
               "Oxicorte/plasma; cara inferior de apoyo de la interfaz planeada en mandrinadora (fresa de planear) o esmerilada; planitud 0,20", core="bot", color=(0.22, 0.4, 0.7)))
    m.add(Part("mesa_anillo_inf", "MES", "Anillo inferior de pasadores", f"Anillo Ø{f(P['D_top'])}/Ø{f(2 * prIn)}×{f(tpr)}, {g.N_pin} agujeros Ø{f(d_pin)} H7 (4 segmentos de 90°)", ring_bot, 1, A572Z,
               "Plasma por segmentos; soldadura CJP de empalmes (UT); agujeros como el anillo superior (en línea)", core="bot", color=(0.22, 0.4, 0.7)))
    for k, r in enumerate(D["almas"]):
        w = ring(r - P["t_web"] / 2, r + P["t_web"] / 2, hw, z0 + tbo)
        m.add(Part(f"mesa_alma{k}", "MES", f"Alma anular R{f(r)}", f"Pletina rolada e={f(P['t_web'])}, h={f(hw)}, eje en R{f(r)}", w, 1, A572, "Corte de pletina a plasma; rolado a radio; 1 empalme CJP (UT)", core="webs", color=(0.3, 0.45, 0.7),
                   obs=f"Desarrollo ≈ {f(2 * math.pi * r)} mm"))
    # nervios: tramos entre almas
    rr = [P["D_hub"] / 2] + [r for r in D["almas"] if P["D_hub"] / 2 < r < P["R_rib"]] + [P["R_rib"]]
    tw = P["t_web"]
    segs = []
    for i in range(len(rr) - 1):
        a0 = rr[i] + (tw / 2 if i > 0 else 0)
        a1 = rr[i + 1] - (tw / 2 if (i < len(rr) - 2 or rr[i + 1] in D["almas"]) else 0)
        segs.append((a0, a1))
    for i, (a0, a1) in enumerate(segs):
        rb = None
        for a in D["nervios"]:
            b_ = box(a0, a1, -P["t_rib"] / 2, P["t_rib"] / 2, z0 + tbo, z0 + tbo + hw).rotate((0, 0, 0), (0, 0, 1), a)
            rb = b_ if rb is None else rb.union(b_)
        for r_ in D["almas"]:
            rb = rb.cut(ring(r_ - tw / 2, r_ + tw / 2, hw + 2, z0 + tbo - 1))
        m.add(Part(f"mesa_nervio{i}", "MES", f"Nervio radial, tramo {i + 1}", f"Pletina e={f(P['t_rib'])}, h={f(hw)}, L={f(a1 - a0, 1)} (R{f(a0, 1)}–R{f(a1, 1)})", rb, int(P["N_rib"]), A572, "Plasma (anidado en plancha)", core="ribs", color=(0.3, 0.45, 0.7)))
    hub = ring(d_bush / 2, P["D_hub"] / 2, hw, z0 + tbo)
    if g.rebaje and g.hHub > 0:
        hub = hub.cut(ring(0, g.Drb / 2, g.hHub + 1, z0 + tbo - 1))                 # rebaje del cubo Ø D_rebaje: de la cara inferior del cubo hasta z0 + h_rebaje (h_collar − δ + c_boss_a)
    m.add(Part("mesa_cubo", "MES", "Cubo de la mesa", f"Anillo Ø{f(P['D_hub'])}/Ø{f(d_bush)} H7 × {f(hw)}" + (f", rebaje inferior Ø{f(g.Drb)} × {f(g.hHub)} sobre la plancha (fondo del rebaje a {f(g.h_rebaje)} mm de la cara inferior de la mesa)" if g.rebaje and g.hHub > 0 else ""),
               hub, 1, A572, "Anillo cortado a llama de plancha gruesa o tubo; Ø150 H7 y rebaje en mandrinadora (sin torno vertical)", core="hub", color=(0.3, 0.45, 0.7), cert="EN 10204 3.1"))
    pins = cq.Workplane("XY").workplane(offset=z0).pushPoints(pin_xy).circle(d_pin / 2).extrude(hd).faces(">Z or <Z").edges().chamfer(g.ch_pin)
    m.add(Part("pasadores", "MES", "Pasador de empuje", f"Barra Ø{f(d_pin)} m6 × {f(hd)}, rosca M20 prof. 40 en un extremo", pins, g.N_pin, f"34CrNiMo6+QT (EN 10083-3), Fy ≥ {f(P['Fy_pin'])} MPa",
               "Corte de barra; mecanizado en torno horizontal o rectificado externo (Ø85 m6 es de barra, sin torno vertical); temple por inducción de la franja de contacto", core="pins", color=(0.75, 0.75, 0.78),
               tratamiento=f"Temple por inducción ≥ 55 HRC (límite elástico superficial supuesto en el cálculo: {f(P['Fy_surf'])} MPa), profundidad efectiva según el cálculo (≥ {fm(g.z_hard, 1)} mm)"))
    wsh = cq.Workplane("XY").workplane(offset=z0 + hd).pushPoints(pin_xy).circle(g.washer_D / 2).extrude(10).union(
        cq.Workplane("XY").workplane(offset=z0 + hd + 10).pushPoints(pin_xy).circle(15).extrude(20))
    m.add(Part("pernos_pasador", "MES", "Perno ISO 4762 M20×45 con arandela", f"Perno M20×45 10.9 + arandela Ø{f(g.washer_D)}×10 (S355J2) por pasador", wsh, g.N_pin, f"Perno ISO 898-1 cl. 10.9 / arandela {A572}", "Comercial (perno); arandela por plasma",
               in_core=False, comercial=True, catalogo="ISO 4762 M20×45 cl. 10.9 (código de catálogo: A DEFINIR POR CATÁLOGO)", color=(0.3, 0.3, 0.32)))

    # ===================== PIV: pivote, buje, tapas =====================
    cap_xy = [(g.cap_pcd / 2 * math.cos(math.radians(45 + 90 * i)), g.cap_pcd / 2 * math.sin(math.radians(45 + 90 * i))) for i in range(4)]
    m.add(Part("pivote", "PIV", "Pivote", f"Barra Ø{f(P['D_piv'])} p6 × {f(g.L_piv)}, chaflanes {fm(g.ch_piv, 0)}×45°", cyl(P["D_piv"] / 2, g.L_piv).faces(">Z or <Z").edges().chamfer(g.ch_piv).cut(cq.Workplane("XY").workplane(offset=g.L_piv - g.cap_tap).pushPoints(cap_xy).circle(g.tap_m10 / 2).extrude(g.cap_tap + 0.5)), 1, propuestas.grado(P['Fy_piv'], P['D_piv'], 'barra'),
               "Corte de barra redonda laminada/rectificada Ø120 con sobrematerial; extremos y Ø p6 en torno horizontal o rectificado externo; sin torno vertical", core="pivot", color=(0.35, 0.35, 0.38),
               tratamiento="Bonificado (QT)", obs="Calado Ø120 p6 en el agujero H7 de la plancha base y el collar (prensa o contracción con hielo seco)"))
    bush = ring(P["D_piv"] / 2, d_bush / 2, P["L_bush"], g.z_bush0)
    m.add(Part("buje", "PIV", "Buje autolubricado", f"Buje Ø{f(d_bush)}/Ø{f(P['D_piv'])}×{f(P['L_bush'])}", bush, 1, f"Buje autolubricado: bronce con lubricante sólido (presión ≤ {fm(P['p_bush'], 0)} MPa, μ ≤ {fm(P['mu_bush'], 2)} según el cálculo); marca/modelo por catálogo (GEN-008)", "Buje comercial o cortado de tubo fundido; Ø exterior s6 y Ø interior en mandrinadora", rho=7.6e-6, in_core=False,
               comercial=True, catalogo="A DEFINIR POR CATÁLOGO (buje autolubricado a medida)", color=(0.8, 0.55, 0.2), cert="EN 10204 3.1"))
    m.add(Part("tapa_ret", "PIV", "Tapa retenedora", f"Disco Ø{f(g.cap_D)}×{f(g.cap_t)} + 4 × M10×25 ISO 10642 10.9", cyl(g.cap_D / 2, g.cap_t, g.L_piv).cut(cq.Workplane("XY").workplane(offset=g.L_piv - 1).pushPoints(cap_xy).circle(g.clear_m10 / 2).extrude(g.cap_t + 2)), 1, A572, "Oxicorte/plasma y mecanizado de agujeros en taladro radial", in_core=False, color=(0.35, 0.35, 0.38)))
    m.add(Part("tapa_insp", "PIV", "Tapa de inspección", f"Disco Ø{f(g.cb_D - 2)}×{f(g.cb_t)} + 6 × M10 avellanados", cyl(g.cb_D / 2 - 1, g.cb_t, z0 + hd - g.cb_t).cut(cq.Workplane("XY").workplane(offset=z0 + hd - g.cb_t - 1).pushPoints(insp_xy).circle(g.clear_m10 / 2).extrude(g.cb_t + 2)), 1, A572, "Oxicorte/plasma; agujeros en taladro radial", in_core=False, color=(0.22, 0.4, 0.7)))

    # ===================== ACC: cilindros, patines, uñas, pasadores =====================
    cyls, dogs, apins_b, apins_s, shoes = [], [], [], [], []
    srt = lambda a, b: (min(a, b), max(a, b))
    for c in D["cilindros"]["antihorario"]:
        sx, dy, X = c["side"], c["dir"], c["x"]
        ye, yr, yps = c["eye"][1], c["rodEngage"][1], c["pinStart"][1]
        yb0, yb1 = srt(ye + dy * P["e_body"], c["rodRetracted"][1] - dy * P["c_rod"])
        body = cq.Workplane("XZ").workplane(offset=-yb1).center(X, zc).circle(P["D_body"] / 2).extrude(yb1 - yb0)
        yr0, yr1 = srt(c["rodRetracted"][1] - dy * P["c_rod"], yr - dy * 52.5)
        rod = cq.Workplane("XZ").workplane(offset=-yr1).center(X, zc).circle(P["d_rod"] / 2).extrude(yr1 - yr0)
        eye0 = cyl(52.5, P["b_eye"], zc - P["b_eye"] / 2, X, ye).cut(cyl(P["d_pp"] / 2, P["b_eye"] + 2, zc - P["b_eye"] / 2 - 1, X, ye))
        eye1 = cyl(52.5, P["b_eye"], zc - P["b_eye"] / 2, X, yr).cut(cyl(P["d_pp"] / 2, P["b_eye"] + 2, zc - P["b_eye"] / 2 - 1, X, yr))
        cyls.append(body.union(rod).union(eye0).union(eye1))
        yF = yps - dy * d_pin / 2
        yB = yF - dy * P["dog_b"]
        xT, xE = sx * KG["tipX"], sx * (KG["mouthX"] + P["L_in"])
        dog_pts = [(xT, yF), (xE, yF), (xE, yB), (xT + sx * g.ch_dx, yB), (xT, yB + dy * min(g.ch_dy, P["dog_b"]))]
        dogs.append(cq.Workplane("XY").workplane(offset=zc - P["dog_h"] / 2).polyline(dog_pts).close().extrude(P["dog_h"]))
        yd0, yd1 = srt(yB, yF)
        ys0, ys1 = srt(yr - dy * KG["rear"], yr + dy * KG["front"])
        sh = box(X - P["w_s"] / 2, X + P["w_s"] / 2, ys0, ys1, zb, KG["shoeTop"])
        zh0, zh1 = (g.zT0 + 1, g.zT1 - 1) if P["h_tee"] > 0 else (zb - P["h_slot"] + 2, zb - P["h_slot"] + 2)
        sh = sh.union(box(X - P["w_slot"] / 2 + CL1, X + P["w_slot"] / 2 - CL1, ys0, ys1, zh1 if P["h_tee"] > 0 else zh0, zb))
        if P["h_tee"] > 0:
            sh = sh.union(box(X - P["w_tee"] / 2 + CL1, X + P["w_tee"] / 2 - CL1, ys0, ys1, zh0, zh1))
        mx0, mx1 = srt(sx * KG["mouthX"], sx * (P["x_g"] - P["w_s"] / 2))
        sh = sh.union(box(mx0, mx1, yd0 - P["t_fw"], yd1 + P["t_fw"], zc - P["dog_h"] / 2 - 10, zc + P["dog_h"] / 2 + 10))
        ge0, ge1 = srt(yr - dy * KG["rear"] - 1, yr + dy * (52.5 + 5))
        sh = sh.cut(box(X - 57.5, X + 57.5, ge0, ge1, zc - P["b_eye"] / 2 - P["g_ch"], zc + P["b_eye"] / 2 + P["g_ch"]))
        zpp0 = max(zb, zc - g.forkH / 2 - 10)
        sh = sh.cut(cyl(P["d_pp"] / 2, KG["shoeTop"] + 10 - zpp0, zpp0, X, yr))
        gr0, gr1 = srt(yr - dy * (KG["rear"] + 5), yr - dy * 40)
        sh = sh.cut(box(X - (P["d_rod"] + 10) / 2, X + (P["d_rod"] + 10) / 2, gr0, gr1, zc - (P["d_rod"] + 10) / 2, zc + (P["d_rod"] + 10) / 2))
        px0, px1 = srt(sx * KG["mouthX"], sx * (KG["pocketEnd"] + CL1))
        sh = sh.cut(box(px0 - CL1, px1, yd0 - CL1, yd1 + CL1, zc - P["dog_h"] / 2 - CL1, zc + P["dog_h"] / 2 + CL1))
        shoes.append(sh)
        apins_s.append(cyl(P["d_pp"] / 2, KG["shoeTop"] + 10 - zpp0, zpp0, X, yr).faces(">Z or <Z").edges().chamfer(g.ch_pp))
        apins_b.append(cyl(P["d_pp"] / 2, BR["H"] + 15, tb, X, ye).faces(">Z or <Z").edges().chamfer(g.ch_pp))
    nc = len(cyls)
    m.add(Part("cilindro", "ACC", "Cilindro hidráulico doble efecto", f"Ø{f(P['D_bore'])}/Ø{f(P['d_rod'])}, carrera {f(P['stroke'])}, {f(P['p_rated'])} psi ({fm(P['p_rated'] * 0.0689476, 0)} bar), ojales con rótula Ø{f(P['d_pp'])}",
               compound(cyls), nc, "Comercial (acero; sellos)", "Comercial", mass_override=nc * P["m_cyl"], core="cyl", comercial=True,
               catalogo="A DEFINIR POR CATÁLOGO (confirmar el largo ojal–ojal retraído y la geometría de extremos con el proveedor)", color=(0.95, 0.78, 0.1), cert="Certificado de prueba hidráulica del fabricante"))
    m.add(Part("patin", "ACC", "Patín guiado", f"Pieza única {f(KG['L_s'])}×{f(P['w_s'])}, lengüeta T (cuello {f(g.neck_w)} f7, cabeza {f(g.head_w)}×{f(g.head_h)}), marco de boca e={f(P['t_fw'])}", compound(shoes), nc,
               propuestas.grado(P['Fy_shoe'], g.Hs, 'barra'), "Bloque de plancha gruesa cortado a llama con sobremetal; fresado del alojamiento, lengüeta T y ojales en mandrinadora; taladros con radial; sin soldadura", core="shoes", color=(0.25, 0.25, 0.28)))
    m.add(Part("una", "ACC", "Uña de empuje", f"Forja/bloque {f(g.paw_L)}×{f(P['dog_b'])}×{f(P['dog_h'])}, cara de empuje plana templada, chaflán de retorno {fm(P['beta_ch'], 0)}° ({fm(g.ch_dx, 1)}×{fm(g.ch_dy, 1)})", compound(dogs), nc,
               f"34CrNiMo6+QT (EN 10083-3), Re ≥ {f(P['Fy_dog'])} MPa medido en la propia forja (3.1)", "Corte de bloque forjado; fresado en mandrinadora/fresadora; rectificado de la cara templada", core="dogs", color=(0.85, 0.35, 0.1),
               tratamiento=f"Temple por inducción ≥ 55 HRC (límite elástico superficial supuesto en el cálculo: {f(P['Fy_surf'])} MPa), profundidad efectiva según el cálculo (≥ {fm(g.z_hard, 1)} mm); alivio de borde 10 mm (factor de concentración de borde {fm(P['k_edge'], 2)} considerado en el cálculo)"))
    m.add(Part("pasador_vastago", "ACC", "Pasador del vástago (patín)", f"Pasador Ø{f(P['d_pp'])} f8 × {f(KG['shoeTop'] + 10 - max(zb, zc - g.forkH / 2 - 10))}, placa de retención", compound(apins_s), nc, propuestas.grado(P['Fy_pp'], P['d_pp'], 'barra'),
               "Barra rectificada Ø70 f8 (comercial), corte y chaflanes en torno horizontal", in_core=False, color=(0.3, 0.3, 0.32), tratamiento="Bonificado 28–34 HRC"))
    m.add(Part("pasador_ojal", "ACC", "Pasador del ojal trasero (ménsula)", f"Pasador Ø{f(P['d_pp'])} f8 × {f(BR['H'] + 15)}, placa de retención", compound(apins_b), nc, propuestas.grado(P['Fy_pp'], P['d_pp'], 'barra'),
               "Barra rectificada Ø70 f8 (comercial), corte y chaflanes en torno horizontal", in_core=False, color=(0.3, 0.3, 0.32), tratamiento="Bonificado 28–34 HRC"))

    # ===================== INT: interfaz =====================
    build_interfaz(m, g, D, log)
    # ===================== MAD: cubierta de madera =====================
    if g.wood:
        zw0 = z0 + hd
        tW = P["t_wood"]
        w_ring = float(g.IG.get("t_ring", P.get("t_ring", 10.0)))          # espesor de la pletina: P.t_ring (núcleo, 4.ª pasada)
        ring_st = ring(Rt - w_ring, Rt, tW, zw0)
        wood = ring(g.cb_D / 2, Rt - w_ring, tW, zw0)
        for (x, y) in pin_xy:                                                  # bolsillos sobre perno y arandela de cada pasador (S06)
            wood = wood.cut(cyl(g.washer_D / 2 + 2, 31, zw0 - 0.5, x, y))
        m.add(Part("madera", "MAD", "Tablones de madera dura", f"Tablones contiguos e={f(tW)}, ancho 200 (adoptado por el mandante), dentro del anillo; conjunto Ø{f(2 * (Rt - w_ring))} con abertura central Ø{f(g.cb_D)}; {g.N_pin} bolsillos Ø{f(g.washer_D + 4)}×31",
                   wood, 1, f"Madera dura seca al aire, ρ ≥ {f(P['rho_wood'])} kg/m³, p adm. {fm(P['p_wood'], 1)} MPa (NCh1198; confirmar con el proveedor)", "Aserrado y cepillado de tablones; corte a medida; bolsillos con fresa; fijación con tornillos avellanados (a definir)",
                   rho=P["rho_wood"] * 1e-9, core="wood", color=(0.6, 0.4, 0.2), cert="Certificado de clasificación estructural del proveedor", obs="Ancho de tablón 200 adoptado por el mandante (S06); fijación PROPUESTA en MAD-001 (confirmar)"))
        m.add(Part("madera_anillo", "MAD", "Anillo de acero de contención", f"Pletina {fm(w_ring, 0)}×{f(tW)} rolada a Ø{f(P['D_top'])}, soldada a la plancha superior (filete {f(P['w_web'])} a ambos lados)", ring_st, 1, A572,
                   "Corte de pletina a plasma; rolado; empalme CJP; soldadura a la mesa", core="ring", color=(0.4, 0.4, 0.45), obs=f"Pletina {fm(w_ring, 0)} × {fm(tW, 0)} adoptada por el mandante (S06); incluida en la masa del cálculo"))
    log(f"  modelo construido en {time.time() - t0:.0f} s, {len(m.parts)} ítems")
    return m


# ----------------------------------------------------------------------------------------------
def build_interfaz(m, g, D, log):
    P, I = g.P, g.I
    if g.opt == 0:
        return
    A572 = f"ASTM A572 Gr.50 (Fy ≥ {f(P['Fy'])} MPa)"
    lay = Layout(g)
    m.layout = lay
    th = lay.th
    z0, tb = g.z0, g.tb
    n = g.n_sec
    ss_mat = f"Acero inoxidable austenítico ASTM A240 (Fy ≥ {f(P['Fy_ss'])} MPa)"
    jb = g.junta("disc")
    gap = jb
    tor_note = "Fijación desmontable por sectores" if g.removable else "NO desmontable (sectores pegados)"
    bars_base, bars_mesa = [], []
    screws = []                  # (cq solid) cabezas+vástagos
    holes_base, holes_mesa = [], []   # agujeros roscados en respaldo

    def make_screws(radii, a_list, t, z_slide, face, rec):
        L = lay.screw_len(t, rec)
        sg = -1 if face == "top" else 1
        out, holes = [], []
        for a in a_list:
            for r in radii:
                x, y = polar(r, a)
                w, ztip = screw_solid(lay, x, y, z_slide, rec, sg, L)
                out.append(w)
                zback = z_slide + sg * t                                   # superficie del respaldo
                hh = abs(ztip - zback) + 2
                holes.append(cyl(lay.d_tor / 2, hh, min(zback, ztip) - (2 if sg < 0 else 0), x, y))
        return out, holes, L

    def stop_bars(a_list, L_t, h, z_attach, direction):
        """Barras b_tope × L_tope × h_barra (h_barra = t − a_sup, del núcleo) centradas en r_u sobre el respaldo. direction +1: crecen hacia +z desde z_attach; −1: hacia −z."""
        out = []
        for a in a_list:
            b_ = box(g.r_u - L_t / 2, g.r_u + L_t / 2, -lay.b_tope / 2, lay.b_tope / 2, z_attach if direction > 0 else z_attach - h, z_attach + h if direction > 0 else z_attach)
            out.append(rotz(b_, a))
        return out

    a_list = [(i + 0.5) * th for i in range(n)]
    secs_info = {}
    # ---------------------------------------------------------------- opciones A y B
    if g.opt in (1, 2):
        t1, t2 = I["tss"], I["tss2"]
        rec = P["ss_allow"]
        # disco de la base (liso)
        zb0 = tb
        sec_b, radii = make_sector_set(g, lay, m, "db", g.Ri, g.Ro, n, t1, zb0, "top", lay.L_base if g.removable else None, RHO_SS, gap=gap, with_screws=g.removable, screw_rec=rec,
                                       notch=g.removable, chamfer=lay.a_inf if g.removable else 0.0)
        # disco de la mesa
        zm0 = z0 - t2
        gr = g.h_gr if g.opt == 1 else 0.0
        sec_m, radii_m = make_sector_set(g, lay, m, "dm", g.Ri, g.Ro, n, t2, zm0, "bot", lay.L_mesa if g.removable else None, RHO_SS, groove_depth=gr, gap=gap, with_screws=g.removable, screw_rec=rec,
                                         notch=g.removable, chamfer=lay.a_inf if g.removable else 0.0)
        # conductos de engrase: Ø6 axial en el disco de la mesa (opción A)
        grease_pts = []
        if g.opt == 1 and g.n_greaser > 0:
            for k in range(g.n_greaser):
                grease_pts.append(polar(g.Ro - 30, 360.0 / g.n_greaser * (k + 0.5) + 360.0 / g.n_greaser / 2 * 0))
            hole = cq.Workplane("XY").workplane(offset=zm0 - 1).pushPoints(grease_pts).circle(3).extrude(t2 + 2)
            sec_m = [s.cut(hole) for s in sec_m]
        m.info["grease_pts"] = grease_pts
        m.add(Part("int_disco_base", "INT", "Disco de la base (sector liso)" if n > 1 else "Disco de la base", f"Sector de disco de acero inoxidable e={f(t1)}, {n} sectores de {fm(th, 2)}°, junta {fm(jb, 1)}" + (f", muesca {fm(lay.b_tope + 2, 0)}×{f(lay.L_base)} para el tope, {len(radii)} agujeros avellanados M{fm(lay.d_tor, 0)}" if g.removable else ""),
                   compound(sec_b), n, ss_mat, "Corte por plasma/láser (subcontrato) del sector; rectificado/lapeado de la cara deslizante en rectificadora plana (subcontrato); avellanado en taladro radial", rho=RHO_SS,
                   core="ss", color=(0.8, 0.82, 0.85), obs=tor_note + f"; rugosidad Ra 0,4 en la cara deslizante; sobreespesor {fm(rec, 1)} mm (relapeado)", tratamiento="Decapado y pasivado"))
        m.add(Part("int_disco_mesa", "INT", "Disco de la mesa (sector ranurado)" if g.opt == 1 else "Disco de la mesa (sector liso)", f"Sector de disco de acero inoxidable e={f(t2)}, {n} sectores de {fm(th, 2)}°, junta {fm(jb, 1)}" + (f", ranuras de engrase {fm(g.w_gr, 0)}×{fm(g.h_gr, 1)}" if g.opt == 1 and gr > 0 else "") + (f", muesca para el tope, avellanados M{fm(lay.d_tor, 0)}" if g.removable else ""),
                   compound(sec_m), n, ss_mat, "Corte por plasma/láser (subcontrato); ranuras fresadas en mandrinadora/fresadora; rectificado/lapeado de la cara deslizante (subcontrato)", rho=RHO_SS, core="ss",
                   color=(0.8, 0.82, 0.85), obs=tor_note + "; rugosidad Ra 0,4 en la cara deslizante", tratamiento="Decapado y pasivado; dureza distinta del disco de la base (≥ 50 HB de diferencia, ASTM G98)" if g.opt == 1 else "Decapado y pasivado"))
        if g.removable:
            tpb, tpm = lay.tp_base, lay.tp_mesa
            assert abs(tpb["t"] - t1) < 1e-6 and abs(tpm["t"] - t2) < 1e-6, "espesor de sector distinto del de interfazGeom.topes"
            bb = stop_bars(a_list, tpb["L"], tpb["h_barra"], tb, +1)
            m.add(Part("int_tope_base", "INT", "Barra de tope (disco de la base)", f"Barra {fm(lay.b_tope, 0)}×{f(tpb['L'])}×{fm(tpb['h_barra'], 0)} (altura = espesor del sector − retiro), soldada a la plancha base con filetes z{fm(lay.w_tope, 0)} frente y dorso", compound(bb), n, A572,
                       "Corte de barra a sierra; soldadura a la plancha base antes del rectificado", core="stopBars", color=(0.55, 0.57, 0.6),
                       obs=f"Cara superior {fm(tpb['a_sup'], 0)} mm bajo la cara deslizante; contacto útil {fm(tpb['h_c'], 0)} mm; chaflán {fm(tpb['a_inf'], 0)}×45° en el canto del sector"))
            bm = stop_bars(a_list, tpm["L"], tpm["h_barra"], z0, -1)
            m.add(Part("int_tope_mesa", "INT", "Barra de tope (disco de la mesa)", f"Barra {fm(lay.b_tope, 0)}×{f(tpm['L'])}×{fm(tpm['h_barra'], 0)} (altura = espesor del sector − retiro), soldada a la plancha inferior de la mesa con filetes z{fm(lay.w_tope, 0)} frente y dorso", compound(bm), n, A572,
                       "Corte de barra; soldadura a la plancha inferior de la mesa", core="stopBars", color=(0.55, 0.57, 0.6),
                       obs=f"Cara inferior {fm(tpm['a_sup'], 0)} mm sobre la cara deslizante; contacto útil {fm(tpm['h_c'], 0)} mm; chaflán {fm(tpm['a_inf'], 0)}×45° en el canto del sector"))
            sb, hb, Lb = make_screws(radii, a_list, t1, tb + t1, "top", rec)
            sm, hm, Lm = make_screws(radii_m, a_list, t2, zm0, "bot", rec)
            for nm, sol, qty, L, t_ in (("int_tornillo_base", sb, len(sb), Lb, t1), ("int_tornillo_mesa", sm, len(sm), Lm, t2)):
                m.add(Part(nm, "INT", f"Tornillo avellanado de posición M{fm(lay.d_tor, 0)}×{L}", f"Tornillo ISO 10642 M{fm(lay.d_tor, 0)}×{L} cl. 10.9, cabeza {fm(rec, 1)} bajo la cara deslizante", compound(sol), qty, "10.9 (ISO 10642), inoxidable A4-80 si se exige contacto con grasa y humedad (opción a confirmar)",
                           "Comercial", in_core=False, comercial=True, catalogo=f"ISO 10642 M{fm(lay.d_tor, 0)}×{L} (código de catálogo: A DEFINIR POR CATÁLOGO)", color=(0.3, 0.3, 0.32), obs="Solo posición: el par lo toman los topes"))
            m.info["screw_L"] = (Lb, Lm)
            m.info["holes_base"], m.info["holes_mesa"] = hb, hm
        m.info["radii_screw"] = radii
        m.info["radii_screw_m"] = radii_m
        m.info["tope_h"] = ((lay.tp_base or {}).get("h_barra", 0.0), (lay.tp_mesa or {}).get("h_barra", 0.0))
        # UHMW (opción B)
        if g.opt == 2:
            tuh = I["tuh"]
            ju = g.junta("uhmw")
            tpu = lay.tp_uhmw if g.removable else None
            L_u = tpu["L"] if tpu else None
            zu0 = tb + t1
            n_u = g.n_seg
            th_u = 360.0 / n_u
            off_u = (th / 4.0) if n_u == n else 0.0
            sec_u = []
            base_u, _ = ring_sector_local(g.Ri, g.Ro, th_u, (lay.b_tope + ju) if g.removable else ju, zu0, tuh, "parallel")
            if tpu:                                                    # alivio inferior del canto del sector de UHMW sobre el filete de la barra (chaflán 45° a_inf)
                r_in = g.Ri + 50
                hu = math.radians(th_u / 2)
                hw_u = (lay.b_tope + ju) / 2
                for sd, ang in ((-1, th_u / 2), (1, -th_u / 2)):
                    for cu in chamfer_cutters(r_in, r_in + L_u, hw_u, tpu["a_inf"], zu0, +1, sides=(sd,)):
                        base_u = base_u.cut(rotz(cu, ang))
            a_u = [off_u + k * th_u for k in range(n_u)]               # líneas de las barras (frontera entre sectores de UHMW)
            for k in range(n_u):
                sec_u.append(rotz(base_u, a_u[k] + th_u / 2))
            m.add(Part("int_uhmw", "INT", "Sector de lámina UHMW", f"Sector de UHMW-PE e={f(tuh)}, {n_u} sectores de {fm(th_u, 2)}°, junta en frío {fm(ju, 1)} mm" + (f" + barra de {fm(lay.b_tope, 0)}" if g.removable else ""),
                       compound(sec_u), n_u, "UHMW-PE PE1000 (ASTM D4020), natural", "Corte por CNC/ruteador o plasma de agua (subcontrato) desde plancha; sin mecanizado de precisión (taller sin torno vertical)", rho=RHO_UH, core="uhmw",
                       color=(0.95, 0.95, 0.85), cert="Certificado del proveedor (EN 10204 2.1/3.1)", tratamiento="Sin tratamiento; no pintar", obs="Sin tornillos: rebaje por barras (S10)"))
            if g.removable:
                h_u = tpu["h_barra"]
                bars = []
                r_in = g.Ri + 50
                for a in a_u:
                    bars.append(rotz(box(r_in, r_in + L_u, -lay.b_tope / 2, lay.b_tope / 2, zu0, zu0 + h_u), a))
                m.add(Part("int_tope_uhmw", "INT", "Barra de rebaje del sector UHMW", f"Barra inoxidable {fm(lay.b_tope, 0)}×{f(L_u)}×{fm(h_u, 0)} (altura = espesor de la lámina − retiro), soldada al disco de la base con filetes z{fm(lay.w_tope, 0)} frente y dorso", compound(bars), n_u,
                           ss_mat, "Corte de barra; soldadura con electrodo inoxidable al disco de la base antes del rectificado", rho=RHO_SS, core="stopBars", color=(0.8, 0.82, 0.85),
                           obs=f"largo = ancho radial − 100 mm (cálculo); cara superior {fm(tpu['a_sup'], 0)} mm bajo la cara de la lámina; contacto útil {fm(tpu['h_c'], 0)} mm; chaflán {fm(tpu['a_inf'], 0)}×45° en el canto de la lámina"))
                m.info["uhmw_bar_L"] = L_u
                m.info["uhmw_bar_h"] = h_u
            m.info["uhmw_off"] = off_u
    # ---------------------------------------------------------------- opción C
    if g.opt == 3:
        conf = g.conf
        tB, tC = I["tbz"], I["tss2"]
        rec_b, rec_c = P["bz_allow"], (P["bz_allow"] if conf == 2 else P["ss_allow"])
        cov = I["cov"] if conf == 3 else 1.0
        rho_bz = P["rho_bz"] * 1e-6
        gap_b = gap
        nB = int(P["bz_npad"]) if conf == 3 else n
        th_b = 360.0 / nB
        a_b = [(i + 0.5) * th_b for i in range(nB)]
        # 1) placa de bronce (sobre la base)
        r_plug = P["bz_plug_d"] / 2
        prof_t = (g.IG.get("tapon_prof_frac") or 0.7) * tB
        mode = "radial" if conf == 3 else "parallel"
        span_b = th_b * cov if conf == 3 else th_b
        L_b = lay.L_base
        radii_b = lay.screw_radii(L_b, grooves=g.h_gr > 0) if g.removable else []
        m_ = 4.0 + r_plug                                                    # margen de tapones (S09)
        # malla de tapones global (triangular), filtrada por sector
        pl = P["bz_plug_p"]
        pts = []
        rows = int(g.Ro / (pl * math.sqrt(3) / 2)) + 2
        for j in range(-rows, rows + 1):
            for i in range(-rows, rows + 1):
                x = i * pl + (j % 2) * pl / 2
                y = j * pl * math.sqrt(3) / 2
                r = math.hypot(x, y)
                if g.Ri + m_ <= r <= g.Ro - m_:
                    pts.append((x, y, r, math.degrees(math.atan2(y, x)) % 360))
        plug_sets = {}
        total_plugs = 0
        h_half = math.radians(span_b / 2)
        ax = (gap_b / 2) / math.sin(h_half) if mode == "parallel" else 0.0
        for i in range(nB):
            a = a_b[i]
            loc = []
            for (x, y, r, ph) in pts:
                d = ((ph - a + 180) % 360) - 180
                if abs(d) > span_b / 2 + 1:
                    continue
                xl, yl = r * math.cos(math.radians(d)), r * math.sin(math.radians(d))
                if mode == "parallel":
                    d1 = (xl - ax) * math.sin(h_half) - yl * math.cos(h_half)
                    d2 = (xl - ax) * math.sin(h_half) + yl * math.cos(h_half)
                else:
                    d1 = r * math.sin(h_half - math.radians(d))
                    d2 = r * math.sin(h_half + math.radians(d))
                if d1 < m_ or d2 < m_:
                    continue
                if g.removable and abs(yl) < (lay.b_tope + 2) / 2 + m_ and (g.r_u - L_b / 2 - m_) < xl < (g.r_u + L_b / 2 + m_):
                    continue
                if any(math.hypot(xl - rr_, yl) < lay.dk / 2 + m_ for rr_ in radii_b):
                    continue
                if g.h_gr > 0:
                    if any(abs(r - rg) < g.w_gr / 2 + m_ for rg in lay.r_circ):
                        continue
                    # ranuras radiales (hallazgo del verificador): la distancia del tapón a la ranura se mide con el ángulo del TAPÓN (ph), no con el de la bisectriz del sector
                    if any(r * abs(math.sin(math.radians(((phi - ph + 180) % 360) - 180))) < g.w_gr / 2 + m_ and abs(((phi - ph + 180) % 360) - 180) < 90 for phi in lay.phi_rad):
                        continue
                loc.append((xl, yl))
            total_plugs += len(loc)
            plug_sets[i] = {"pts": loc}
        plug_sets_h = {}
        for i, ps in plug_sets.items():
            if ps["pts"]:
                plug_sets_h[i] = {"holes": cq.Workplane("XY").workplane(offset=tb + tB - prof_t).pushPoints(ps["pts"]).circle(r_plug).extrude(prof_t + 1), "pts": ps["pts"]}
        sec_bz, _ = make_sector_set(g, lay, m, "bz", g.Ri, g.Ro, nB, tB, tb, "top", L_b if g.removable else None, rho_bz, groove_depth=g.h_gr, plug=plug_sets_h, mode=mode, span_deg=span_b,
                                    gap=gap_b, with_screws=g.removable, screw_rec=rec_b, notch=g.removable, chamfer=lay.a_inf if g.removable else 0.0)
        plugs = []
        for i, ps in plug_sets_h.items():
            plugs.append(rotz(cq.Workplane("XY").workplane(offset=tb + tB - prof_t).pushPoints(ps["pts"]).circle(r_plug).extrude(prof_t), a_b[i]))
        mat_bz = f"Bronce con tapones de grafito, Fy ≥ {f(P['Fy_bz'])} MPa, ≥ {f(P['HB_bz'])} HB (ASTM B148 C95400 / B584; confirmar con el proveedor)"
        mat_cara = (f"17-4PH H1025 o inoxidable nitrurado, Fy ≥ {f(P['Fy_cara'])} MPa, ≥ {f(P['HB_cara'])} HB" if conf != 2 else f"Bronce de aleación distinta del de la placa 1 (p. ej. C93200), Fy ≥ {f(P['Fy_bz2'])} MPa")
        m.add(Part("int_bronce", "INT", "Pastilla de bronce con tapones de grafito" if conf == 3 else "Sector de placa de bronce con tapones de grafito",
                   f"{nB} {'pastillas' if conf == 3 else 'sectores'} de bronce e={f(tB)} (cubrimiento {fm(cov, 2)}), tapones Ø{fm(P['bz_plug_d'], 0)} × {fm(prof_t, 1)} a paso {fm(pl, 0)}, ranuras {fm(g.w_gr, 0)}×{fm(g.h_gr, 1)}", compound(sec_bz), nB, mat_bz,
                   "Plancha/barra de bronce con tapones comercial (suministrada con tapones); corte por plasma de agua/aserrado y fresado de ranuras (subcontrato); sin torneado de gran diámetro", rho=rho_bz, core="bz", color=(0.8, 0.55, 0.2),
                   cert="EN 10204 3.1", obs=tor_note + f"; {total_plugs} tapones (S09)"))
        m.add(Part("int_tapones", "INT", "Tapón de grafito", f"Tapón de grafito Ø{fm(P['bz_plug_d'], 0)} × {fm(prof_t, 1)} (encastrado en el bronce)", compound(plugs), total_plugs, "Grafito (ρ 1,8 g/cm³)", "Comercial: viene colocado en la placa de bronce", rho=RHO_GR, core="bz",
                   comercial=True, catalogo="A DEFINIR POR CATÁLOGO (se suministra con la placa)", color=(0.1, 0.1, 0.1), cert="Certificado del proveedor"))
        m.info["n_plugs"] = total_plugs
        m.info["plug_prof"] = prof_t
        # 2) disco duro / 2.ª placa de bronce (sobre la mesa)
        zm0 = z0 - tC
        L_m = lay.L_mesa
        sec_c, radii_c = make_sector_set(g, lay, m, "dc", g.Ri, g.Ro, n, tC, zm0, "bot", L_m if g.removable else None, RHO_SS, gap=gap, with_screws=g.removable, screw_rec=rec_c, notch=g.removable, chamfer=lay.a_inf if g.removable else 0.0)
        grease_pts = []
        if g.n_greaser > 0:
            for k in range(g.n_greaser):
                grease_pts.append(polar(g.Ro - 30, 360.0 / g.n_greaser * (k + 0.5)))
            hole = cq.Workplane("XY").workplane(offset=zm0 - 1).pushPoints(grease_pts).circle(3).extrude(tC + 2)
            sec_c = [s.cut(hole) for s in sec_c]
        m.info["grease_pts"] = grease_pts
        m.add(Part("int_cara", "INT", "Disco duro (sector)" if conf != 2 else "2.ª placa de bronce (sector)", f"{n} sectores de {fm(th, 2)}°, e={f(tC)}, junta {fm(jb, 1)}" + (f", muesca para el tope, avellanados M{fm(lay.d_tor, 0)}" if g.removable else "") + ", orificio Ø6 de engrase",
                   compound(sec_c), n, mat_cara, "Corte por plasma de agua/láser (subcontrato); tratamiento térmico; rectificado/lapeado de la cara deslizante (subcontrato)" if conf != 2 else "Corte por plasma de agua/aserrado; rectificado de la cara deslizante (subcontrato)",
                   rho=(RHO_SS if conf != 2 else rho_bz), core="ss" if conf != 2 else "bz", color=(0.7, 0.72, 0.78), obs=tor_note + "; Ra 0,4 en la cara deslizante", tratamiento=("Temple y revenido a ≥ HB indicado; nitrurado si es inoxidable" if conf != 2 else "—")))
        if g.removable:
            tpb, tpm = lay.tp_base, lay.tp_mesa
            assert abs(tpb["t"] - tB) < 1e-6 and abs(tpm["t"] - tC) < 1e-6, "espesor de sector distinto del de interfazGeom.topes"
            bbz = stop_bars(a_b, L_b, tpb["h_barra"], tb, +1)
            m.add(Part("int_tope_base", "INT", "Barra de tope (placa de bronce)", f"Barra {fm(lay.b_tope, 0)}×{f(L_b)}×{fm(tpb['h_barra'], 0)} (altura = espesor del sector − retiro), soldada a la plancha base con filetes z{fm(lay.w_tope, 0)} frente y dorso", compound(bbz), nB, A572, "Corte de barra; soldadura a la plancha base antes del rectificado",
                       core="stopBars", color=(0.55, 0.57, 0.6), obs=f"Cara superior {fm(tpb['a_sup'], 0)} mm bajo la cara deslizante; contacto útil {fm(tpb['h_c'], 0)} mm; chaflán {fm(tpb['a_inf'], 0)}×45° en el canto del sector"))
            bmc = stop_bars(a_list, L_m, tpm["h_barra"], z0, -1)
            m.add(Part("int_tope_mesa", "INT", "Barra de tope (disco duro / 2.ª placa)", f"Barra {fm(lay.b_tope, 0)}×{f(L_m)}×{fm(tpm['h_barra'], 0)} (altura = espesor del sector − retiro), soldada a la plancha inferior de la mesa con filetes z{fm(lay.w_tope, 0)} frente y dorso", compound(bmc), n, A572, "Corte de barra; soldadura a la mesa",
                       core="stopBars", color=(0.55, 0.57, 0.6), obs=f"Cara inferior {fm(tpm['a_sup'], 0)} mm sobre la cara deslizante; contacto útil {fm(tpm['h_c'], 0)} mm; chaflán {fm(tpm['a_inf'], 0)}×45° en el canto del sector"))
            sb, hb, Lb = make_screws(radii_b, a_b, tB, tb + tB, "top", rec_b)
            sm, hm, Lm = make_screws(radii_c, a_list, tC, zm0, "bot", rec_c)
            for nm, sol, qty, L in (("int_tornillo_base", sb, len(sb), Lb), ("int_tornillo_mesa", sm, len(sm), Lm)):
                m.add(Part(nm, "INT", f"Tornillo avellanado de posición M{fm(lay.d_tor, 0)}×{L}", f"Tornillo ISO 10642 M{fm(lay.d_tor, 0)}×{L} cl. 10.9", compound(sol), qty, "10.9 (ISO 10642)", "Comercial", in_core=False, comercial=True,
                           catalogo=f"ISO 10642 M{fm(lay.d_tor, 0)}×{L} (código de catálogo: A DEFINIR POR CATÁLOGO)", color=(0.3, 0.3, 0.32), obs="Solo posición: el par lo toman los topes"))
            m.info["screw_L"] = (Lb, Lm)
            m.info["holes_base"], m.info["holes_mesa"] = hb, hm
        m.info["radii_screw"] = radii_b
        m.info["radii_screw_m"] = radii_c
        m.info["tope_h"] = ((lay.tp_base or {}).get("h_barra", 0.0), (lay.tp_mesa or {}).get("h_barra", 0.0))
    # --- ductos de engrase (graseras) ---
    if g.opt in (1, 3) and g.n_greaser > 0:
        pts = m.info["grease_pts"]
        gs = []
        for (x, y) in pts:
            a = math.degrees(math.atan2(y, x))
            gs.append(rotz(cyl(5, 12, 0, 0, 0).rotate((0, 0, 0), (0, 1, 0), 90).translate((g.Rt - 12, 0, g.z0 + g.tpr / 2)), a))
        m.add(Part("graseras", "INT", "Grasera recta M10×1", f"Grasera DIN 71412 M10×1 recta, en el canto de la plancha inferior de la mesa; taladro Ø6 radial hasta R{f(g.Ro - 30)} y axial hasta la cara deslizante", compound(gs), g.n_greaser,
                   "Acero zincado", "Comercial", in_core=False, comercial=True, catalogo="DIN 71412 M10×1 recta (código de catálogo: A DEFINIR POR CATÁLOGO)", color=(0.5, 0.5, 0.2), obs="S08"))


# ----------------------------------------------------------------------------------------------
# agujeros roscados en el respaldo (plancha base y plancha inferior de la mesa) para los tornillos de posición
# ----------------------------------------------------------------------------------------------
def apply_backing_holes(m):
    """Corta en las planchas base y inferior de la mesa los agujeros roscados de los tornillos y los conductos de engrase."""
    g = m.g
    if not g.opt or not g.removable and not m.info.get("grease_pts"):
        return
    base = m.get("base_plancha")
    inf = m.get("mesa_plancha_inf")
    hb = m.info.get("holes_base")
    hm = m.info.get("holes_mesa")
    if hb:
        cut = compound(hb)
        base.solid = base.solid.cut(cut)
        base._vol = None
    gp = m.info.get("grease_pts")
    if hm or gp:
        sol = inf.solid
        ring_inf = m.get("mesa_anillo_inf")
        if hm:
            hmc = compound(hm)
            sol = sol.cut(hmc)
            ring_inf.solid = ring_inf.solid.cut(hmc)
        if gp:
            axial = cq.Workplane("XY").workplane(offset=g.z0 - 1).pushPoints(gp).circle(3).extrude(g.tpr / 2 + 1)
            ring_inf.solid = ring_inf.solid.cut(axial)
            for (x, y) in gp:
                a = math.degrees(math.atan2(y, x))
                ring_inf.solid = ring_inf.solid.cut(rotz(cyl(5, 12, 0, 0, 0).rotate((0, 0, 0), (0, 1, 0), 90).translate((g.Rt - 12, 0, g.z0 + g.tpr / 2)), a))
            for (x, y) in gp:
                a = math.degrees(math.atan2(y, x))
                rad = rotz(cyl(3, 30, 0, 0, 0).rotate((0, 0, 0), (0, 1, 0), 90).translate((g.Ro - 30, 0, g.z0 + g.tpr / 2)), a)
                ring_inf.solid = ring_inf.solid.cut(rad)
            ring_inf._vol = None
        inf.solid = sol
        inf._vol = None


# ----------------------------------------------------------------------------------------------
# masas, centro de gravedad e interferencias
# ----------------------------------------------------------------------------------------------
def masas(m, tol_pct=0.5):
    D, g = m.D, m.g
    M = D["derivados"]["masas"]
    core_keys = {"base": ["base"], "rim": ["rim"], "brackets": ["brackets"], "beds": ["beds"], "dogs": ["dogs"], "shoes": ["shoes"], "pivot": ["pivot"], "cyl": ["cyl"],
                 "mesa": ["top", "bot", "webs", "ribs", "hub", "pins"], "ss": ["ss"], "uhmw": ["uhmw"], "bz": ["bz"], "wood": ["wood"], "ring": ["ring"], "stopBars": ["stopBars"]}
    groups = {"base": "base", "rim": "rim", "brackets": "brackets", "beds": "beds", "dogs": "dogs", "shoes": "shoes", "pivot": "pivot", "cyl": "cyl",
              "top": "mesa", "bot": "mesa", "webs": "mesa", "ribs": "mesa", "hub": "mesa", "pins": "mesa", "ss": "ss", "uhmw": "uhmw", "bz": "bz", "wood": "wood", "ring": "ring", "stopBars": "stopBars"}
    nombres = {"base": "Plancha base + collar + orejas de izaje", "rim": "Marco perimetral", "brackets": "Ménsulas de cilindro", "beds": "Bancadas de guía", "dogs": "Uñas", "shoes": "Patines",
               "pivot": "Pivote", "cyl": "Cilindros (masa de catálogo)", "mesa": "Mesa (planchas, almas, nervios, cubo, pasadores)", "ss": "Discos de interfaz (inox / duro)", "uhmw": "Lámina UHMW",
               "bz": "Bronce con grafito (o 2.ª placa)", "wood": "Cubierta de madera (tablones)", "ring": "Anillo de acero de la madera", "stopBars": "Barras de los topes (m.stopBars)"}
    mod = {}
    for p in m.parts:
        if p.core:
            grp = groups[p.core]
            mod[grp] = mod.get(grp, 0.0) + p.mass_total
    comp = []
    for grp, kg in mod.items():
        ref = sum(M[k] for k in core_keys[grp])
        comp.append(dict(grupo=grp, pieza=nombres[grp], modelo3d=kg, nucleo=ref, dif=kg - ref, dif_pct=(kg - ref) / ref * 100 if ref else 0.0))
    for grp in core_keys:                       # grupos del núcleo sin pieza (debe ser 0)
        if grp not in mod and sum(M[k] for k in core_keys[grp]) > 1e-6:
            comp.append(dict(grupo=grp, pieza=nombres[grp] + " (sin pieza en el modelo)", modelo3d=0.0, nucleo=sum(M[k] for k in core_keys[grp]), dif=-sum(M[k] for k in core_keys[grp]), dif_pct=-100.0))
    tot3d = sum(p.mass_total for p in m.parts if p.core)
    tot_n = M["total"]
    fuera = [(p.code, p.name, p.mass_total) for p in m.parts if not p.core]
    return dict(comp=comp, total_3d=tot3d, total_nucleo=tot_n, dif=tot3d - tot_n, dif_pct=(tot3d - tot_n) / tot_n * 100, fuera=fuera, masa_fuera=sum(x[2] for x in fuera),
                masa_ensamble=tot3d + sum(x[2] for x in fuera), tol_pct=tol_pct)


def cog(m):
    mt, cx, cy, cz = 0.0, 0.0, 0.0, 0.0
    for p in m.parts:
        c = p.center()
        w = p.mass_total
        mt += w
        cx += w * c[0]
        cy += w * c[1]
        cz += w * c[2]
    return mt, (cx / mt, cy / mt, cz / mt)


def bbox(p):
    bb = cq.Compound.makeCompound(list(p.solid.vals())).BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def interferencias(m, log=None):
    names = [p for p in m.parts]
    bbs = [bbox(p) for p in names]
    res = []
    n_chk = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = bbs[i], bbs[j]
            if a[1] < b[0] - 0.01 or b[1] < a[0] - 0.01 or a[3] < b[2] - 0.01 or b[3] < a[2] - 0.01 or a[5] < b[4] - 0.01 or b[5] < a[4] - 0.01:
                continue
            n_chk += 1
            try:
                v = cq.Compound.makeCompound(list(names[i].solid.vals())).intersect(cq.Compound.makeCompound(list(names[j].solid.vals()))).Volume()
            except Exception:
                v = float("nan")
            res.append(dict(a=names[i].code, b=names[j].code, na=names[i].name, nb=names[j].name, vol_mm3=round(v, 1), ok=bool(v < 1.0)))
    return res, n_chk, len(names) * (len(names) - 1) // 2


def export_step_glb(m, out):
    assy = cq.Assembly(name="TT300-C")
    for p in m.parts:
        assy.add(cq.Workplane("XY").newObject([cq.Compound.makeCompound(list(p.solid.vals()))]), name=f"{p.code} {p.name}", color=cq.Color(*p.color, 1.0))
    out.mkdir(parents=True, exist_ok=True)
    assy.save(str(out / "TT300-C.step"))
    assy.save(str(out / "TT300-C.glb"))


def run(D, out, verbose=True):
    m = build(D, verbose)
    apply_backing_holes(m)
    if verbose:
        print("  exportando STEP/GLB...", flush=True)
    export_step_glb(m, out)
    ms = masas(m)
    mt, c = cog(m)
    inter, nchk, ntot = interferencias(m)
    rep = dict(masas=ms, masa_total_ensamble=mt, cg=c, interferencias=inter, pares_evaluados=nchk, pares_totales=ntot,
               partes={p.code: dict(nombre=p.name, qty=p.qty, masa_unit=p.mass_unit, masa_total=p.mass_total) for p in m.parts})
    json.dump(rep, open(out / "TT300-C_masas3d.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return m, rep


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = OUT_DEFAULT
    if "--out" in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
        args = [a for a in args if a != str(out)]
    D = load(args[0] if args else None)
    m, rep = run(D, out)
    ms = rep["masas"]
    print(f"{'Grupo':52s} {'3D kg':>9s} {'Núcleo kg':>10s} {'Δ %':>7s}")
    for r in ms["comp"]:
        print(f"{r['pieza']:52s} {r['modelo3d']:9.1f} {r['nucleo']:10.1f} {r['dif_pct']:7.2f}")
    print(f"TOTAL comparable: 3D {ms['total_3d']:.1f} kg · núcleo {ms['total_nucleo']:.1f} kg · Δ {ms['dif_pct']:+.2f} % (tolerancia {ms['tol_pct']} %)")
    print(f"Piezas fuera del núcleo: {ms['masa_fuera']:.1f} kg; masa del ensamble {rep['masa_total_ensamble']:.1f} kg; CG = ({rep['cg'][0]:.1f}, {rep['cg'][1]:.1f}, {rep['cg'][2]:.1f}) mm")
    bad = [r for r in rep["interferencias"] if not r["ok"]]
    print(f"Interferencias: {len(bad)} con volumen > 1 mm³ de {rep['pares_evaluados']} pares evaluados (de {rep['pares_totales']})")
    for r in bad:
        print("  XX", r["a"], r["b"], r["vol_mm3"])
    if bad:
        sys.exit("Hay interferencias entre piezas: revisar geometría")
