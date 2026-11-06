"""Magnitudes derivadas del diseño TT300-C (fuente única: cad/out/TT300-C_design.json) y registro de supuestos del dibujante.

Este módulo no inventa cotas: todo sale de D['P'], D['derivados'], D['apoyo'], D['interfazGeom'] y D['verificaciones'].
Lo que el cálculo no entrega pero el dibujo necesita se declara en SUPUESTOS (con id, valor, justificación y marca
PROVISORIO) y se imprime en las láminas afectadas y en cad/out/informe_paquete.md."""
import json, math, re, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "cad" / "out"
CODE = "TT300C"
REV = "B"
RHO = 7.85e-6          # kg/mm³ (mismo valor del núcleo)
RHO_SS = 7.93e-6       # inoxidable austenítico (núcleo)
RHO_UH = 0.94e-6       # UHMW-PE (núcleo)
RHO_GR = 1.8e-6        # grafito (núcleo)
CL1 = 1.0              # holgura de modelo entre piezas móviles (ya usada en el modelo 3D de la Rev B)

ADVERTENCIA = "ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO."
NOTA_VIENTO = "En caso de vientos fuertes no se recomienda realizar la operación."
NOTA_ANCLAJE = "Equipo sin anclaje: apoyo sobre losa/mats con presión ≤ q_losa; verificar superficie de apoyo por terceros."


def load(path=None):
    p = pathlib.Path(path) if path else OUT_DEFAULT / "TT300-C_design.json"
    return json.load(open(p, encoding="utf-8"))


def f(v, n=0):
    """Formato numérico chileno: miles con punto, decimales con coma."""
    return f"{v:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def f1(v):
    return f(v, 1)


def fm(v, n=1):
    """Número con coma decimal sin separador de miles, recorta ceros finales."""
    s = f"{v:.{n}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",")


class G:
    """Geometría y datos derivados. Todas las longitudes en mm, masas en kg."""

    def __init__(self, D):
        self.D = D
        P = self.P = D["P"]
        DV = self.DV = D["derivados"]
        self.M = DV["masas"]
        self.I = D["apoyo"]["interfaz"]
        self.IG = D.get("interfazGeom", {})
        self.fecha = datetime.date.fromisoformat(D["fecha"])
        self.FECHA = self.fecha.strftime("%d-%m-%Y")
        # --- opción de interfaz ---
        I = self.I
        self.opt = int(I["o"])                      # 0 acero-acero, 1 A, 2 B, 3 C
        self.conf = int(I.get("conf", 1)) if self.opt == 3 else 0
        self.removable = P["fix_mode"] < 1.5
        self.delta = float(I["delta"])
        self.wood = P["opt_wood"] > 0.5
        # --- base ---
        self.B, self.tb = P["B"], P["t_base"]
        self.boss = P["h_boss"] > 0
        self.h_boss, self.D_boss = (P["h_boss"], P["D_boss"]) if self.boss else (0.0, 0.0)
        self.w_collar = 10.0                         # filete del collar: el núcleo lo fija en 10 mm (texto de la verificación)
        for v in D["verificaciones"]:
            if v["nombre"].startswith("Soldadura del collar a la base"):
                m = re.search(r"w = (\d+) mm", v["formula"])
                if m:
                    self.w_collar = float(m.group(1))
        # --- mesa ---
        self.hd, self.tt, self.tbo = P["h_disc"], P["t_top"], P["t_bot"]
        self.tpr = max(P["t_pr"], self.tt, self.tbo)
        self.Rt = P["D_top"] / 2
        self.prIn = DV["prIn"]
        self.hw = self.hd - self.tt - self.tbo
        self.hax = DV["hax"]
        self.z0 = self.tb + self.delta               # cara inferior de la mesa
        self.zc = self.tb + self.hax                 # eje de los cilindros
        self.d_pin, self.R_pin, self.N_pin = P["d_pin"], P["R_pin"], int(P["N_pin"])
        self.d_bush = P["D_piv"] + 30
        self.hole_top = self.IG.get("hole_top", P["D_piv"] + 80)
        self.cap_D = P["D_piv"] + 60
        self.cb_t = 8.0
        self.cb_D = self.cap_D + 60
        self.cap_t = self.tt - 3 - self.cb_t - 1
        self.L_piv = self.tb + self.delta + self.hd - self.tt + 3
        self.z_bush0 = self.tb + self.h_boss + 2     # el buje arranca 2 mm sobre el collar
        self.washer_D = self.d_pin + 30
        # --- accionamiento ---
        self.BR = DV["bracket"]
        self.KG = DV["K"]
        self.forkH = DV["forkH"]
        self.zb = self.tb + P["t_bed"]
        self.zT1 = self.zb - P["h_slot"]
        self.zT0 = self.zT1 - P["h_tee"]
        self.fondo = P["t_bed"] - P["h_slot"] - P["h_tee"]
        self.neck_w, self.head_w, self.head_h = P["w_slot"] - 2, P["w_tee"] - 2, P["h_tee"] - 2
        self.neck_h = P["h_slot"] + 1
        self.z_shoe = self.KG["shoeTop"]
        self.Hs = self.z_shoe - self.zb
        self.ch_dx = self.KG["travel"]
        self.ch_dy = self.ch_dx / math.tan(math.radians(P["beta_ch"]))
        self.paw_L = self.KG["mouthX"] + P["L_in"] - self.KG["tipX"]
        self.pk_top = self.zc + P["dog_h"] / 2 + 1
        self.pk_bot = self.zc - P["dog_h"] / 2 - 1
        zh = next(v["dem"] for v in D["verificaciones"] if v["nombre"].startswith("Profundidad mínima de temple"))
        self.z_hard = math.ceil(zh * 10) / 10
        # --- izaje ---
        self.cl_lug = self.B / 2 - P["c_lug"]
        self.ear_pos = [(P["x_lug"], self.cl_lug), (-P["x_lug"], self.cl_lug), (P["x_lug"], -self.cl_lug), (-P["x_lug"], -self.cl_lug)]
        # --- interfaz ---
        self.Ri_core = P["D_piv"] / 2 + 15
        self.Ro = self.Rt
        self.Ri_if = max(self.Ri_core, self.D_boss / 2 + CL1) if self.boss else self.Ri_core   # el collar Ø D_boss obliga a un agujero central mayor
        self.r_u = D["apoyo"]["r_u"]
        self.n_sec = int(P["n_sec"])
        self.n_seg = int(P["n_seg"])
        self.h_gr, self.w_gr = P["h_gr"], P["w_gr"]
        self.n_gr_rad, self.n_gr_circ, self.n_greaser = int(P["n_gr_rad"]), int(P["n_gr_circ"]), int(P["n_greaser"])
        self.stack = self._stack()

    # ------------------------------------------------------------------
    def _stack(self):
        """Capas de la interfaz, de abajo hacia arriba, desde la cara superior de la plancha base. Cada capa: dict(id, z0, t, lado)."""
        I, tb = self.I, self.tb
        L = []
        if self.opt == 0:
            return L
        if self.opt in (1, 2):
            t1, t2 = I["tss"], I["tss2"]
            L.append(dict(id="disc_base", z0=tb, t=t1, lado="base"))
            z = tb + t1
            if self.opt == 2:
                L.append(dict(id="uhmw", z0=z, t=I["tuh"], lado="base"))
                z += I["tuh"]
            L.append(dict(id="disc_mesa", z0=z, t=t2, lado="mesa"))
        else:
            tB, tC = I["tbz"], I["tss2"]
            L.append(dict(id="bronce", z0=tb, t=tB, lado="base"))
            L.append(dict(id="cara", z0=tb + tB, t=tC, lado="mesa"))
        return L

    def layer(self, id_):
        return next((l for l in self.stack if l["id"] == id_), None)

    # ------------------------------------------------------------------
    @property
    def interfaz_nombre(self):
        return {0: "Acero-acero con grasa grafitada (sin interfaz alternativa)",
                1: "Opción A: dos discos de acero inoxidable con grasa (base liso, mesa ranurado)",
                2: "Opción B: dos discos de acero inoxidable con lámina de UHMW por sectores",
                3: {1: "Opción C-1: placa de bronce con tapones de grafito + disco duro",
                    2: "Opción C-2: dos placas de bronce de aleaciones distintas",
                    3: "Opción C-3: pastillas de bronce con tapones de grafito + disco duro"}.get(self.conf, "Opción C")}[self.opt]

    def tope_L(self, which):
        """Largo del tope (mm) entregado por el núcleo para la pieza 'which' ('base'|'mesa'|'uhmw')."""
        T = self.IG.get("topes", [])
        if which == "uhmw":
            return self.Ro - self.Ri_if - 100.0
        if not T:
            return None
        if self.opt in (1, 2):
            if which == "base":
                return T[0]["L"]
            return T[1]["L"] if len(T) > 1 else T[0]["L"]
        if self.opt == 3:
            return T[0]["L"] if which == "base" else T[1]["L"]
        return None

    def junta(self, which):
        """Junta en frío (mm) entre sectores: la mayor entre 1 mm (regla del núcleo) y la dilatación calculada."""
        J = self.IG.get("juntas", [])
        calc = 0.0
        for j in J:
            if which == "uhmw" and "UHMW" in j["pieza"]:
                calc = max(calc, j["j"])
            if which != "uhmw" and "UHMW" not in j["pieza"]:
                calc = max(calc, j["j"])
        return math.ceil(max(1.0, calc) * 10) / 10


def supuestos(g):
    """Decisiones de dibujo que el cálculo no fija. Cada una se rotula PROVISORIO en las láminas donde interviene."""
    P = g.P
    S = []

    def add(id_, tema, valor, motivo):
        S.append(dict(id=id_, tema=tema, valor=valor, motivo=motivo))
    if g.opt:
        add("S01", "Tornillos de posición por sector", "2 por sector (en la bisectriz, fuera del tope y de las ranuras)",
            f"El cálculo fija solo el diámetro d_tor = M{fm(P['d_tor'], 0)} ISO 10642 y la verificación de la cabeza; no entrega la cantidad ni la posición.")
        add("S02", "Altura de la barra del tope", "h_tope = t_pieza − 1 mm (cara superior 1 mm bajo la cara deslizante)",
            "El cálculo usa el espesor completo t como altura de contacto; una barra enrasada rozaría la pieza contraria. Se informa el FU recalculado con la altura dibujada.")
        add("S03", "Alojamiento del tope", "Muesca pasante en la bisectriz del sector, ancho b_tope + 2 mm, centrada radialmente en r_u",
            "El cálculo fija L_tope, b_tope y w_tope pero no dónde se aloja la barra respecto del sector.")
        add("S04", "Junta entre sectores", "Junta de ancho constante j = máx(1 mm; dilatación calculada) entre bordes paralelos a la bisectriz",
            "El núcleo exige junta en frío ≥ 1 mm y entrega la dilatación.")
        add("S07", "Diámetro interior de los discos/placas", f"Ø{f(2 * g.Ri_if)} (collar Ø{f(g.D_boss)} + holgura) en lugar de Ø{f(2 * g.Ri_core)} del núcleo" if g.boss else f"Ø{f(2 * g.Ri_core)} (igual al núcleo)",
            "El collar del pivote atraviesa el plano de la interfaz; el núcleo calcula el área y la masa con R_i = D_piv/2 + 15.")
    if g.opt == 1 or g.opt == 3:
        add("S05", "Posición de las ranuras de engrase",
            f"{g.n_gr_rad} radiales a k·360°/{g.n_gr_rad} de R_i a R_o (extremos abiertos: purga por el perímetro); {g.n_gr_circ} circunferenciales, la exterior a R_o − 30 y el resto equiespaciadas hasta R_i + 30",
            "El núcleo solo usa cantidad, ancho, profundidad y largo total (área perdida y volumen de grasa).")
        add("S08", "Conducto de las graseras", "Grasera M10×1 en el canto de la plancha inferior; taladro Ø6 radial hasta R_o − 30 y Ø6 axial hasta la cara deslizante",
            "El núcleo indica «taladro Ø6 hasta la ranura exterior»; trayecto y cota no se entregan.")
    if g.opt == 3:
        add("S09", "Patrón de tapones de grafito", f"Malla triangular (escalonada) de paso {fm(P['bz_plug_p'], 0)} mm, Ø{fm(P['bz_plug_d'], 0)} mm, profundidad {fm(g.IG.get('tapon_prof_frac') or 0.7, 2)}·t; se omiten los tapones a menos de 4 mm de bordes, muescas, tornillos y ranuras",
            "El núcleo usa la fracción de área f_g y la profundidad; no entrega la distribución ni el origen de la malla.")
    if g.opt == 2:
        add("S10", "Sujeción de los sectores de UHMW", "Sin tornillos: rebaje formado por barras (largo R_o − R_i − 100) soldadas al disco de la base, y retención superior por el disco de la mesa",
            "El núcleo no define tornillos para la lámina UHMW (solo el rebaje con topes).")
    if g.opt:
        add("S11", "Largo del tornillo de posición", "ISO 10642 con largo normalizado ≥ t − 0,55·d + 1,5·d (1,5 d de rosca en el respaldo)",
            "Criterio de engrane mínimo en acero; el núcleo verifica solo la cabeza.")
    if g.wood:
        add("S06", "Anillo de acero de la cubierta de madera", f"Pletina de 10 × {fm(P['t_wood'], 0)} mm (ancho × alto) en el borde, soldada a la plancha superior; tablones de 200 mm de ancho; abertura central Ø{f(g.cb_D)} para la tapa de inspección",
            "El núcleo calcula la madera como anulo Ø D_top / Ø(D_piv + 80) sin anillo; ancho del anillo, ancho de tablón y abertura no se entregan. Bolsillos Ø(arandela + 4) × 31 sobre cada perno de pasador.")
    add("S12", "Collar y mesa con interfaz", "Rebaje inferior de la mesa Ø D_boss × h_boss medido desde la cara inferior de la mesa (atraviesa la plancha inferior y el cubo)",
        "La masa total coincide con la del núcleo (la parte del rebaje en la plancha inferior se descuenta allí en lugar de en el cubo).") if g.boss else None
    add("S13", "Izaje de la mesa", "No se dibujan puntos de izaje de la mesa", "El cálculo solo define las 4 orejas de la base (P.t_ear…); la mesa debe izarse con medios definidos por el montajista.")
    add("S14", "Retención axial del pivote", "Ajuste H7/p6 sin soldadura ni tope inferior", "El cálculo verifica asiento y flexión pero no la extracción axial del pivote.")
    return [s for s in S if s]
