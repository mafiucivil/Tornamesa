"""Magnitudes derivadas del diseño TT300-C (fuente única: cad/out/TT300-C_design.json) y registro de supuestos del dibujante.

Este módulo no inventa cotas: todo sale de D['P'], D['derivados'], D['apoyo'], D['interfazGeom'] y D['verificaciones'].
Lo que el cálculo no entrega pero el dibujo necesita se declara en SUPUESTOS (con id, valor, justificación y marca
PROVISORIO) y se imprime en las láminas afectadas y en cad/out/informe_paquete.md."""
import json, math, re, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "cad" / "out"
CODE = "TT300C"
REV = "C"
RHO = 7.85e-6          # kg/mm³ (mismo valor del núcleo)
RHO_SS = 7.93e-6       # inoxidable austenítico (núcleo)
RHO_UH = 0.94e-6       # UHMW-PE (núcleo)
RHO_GR = 1.8e-6        # grafito (núcleo)
CL1 = 1.0              # holgura de modelo entre piezas móviles (ya usada en el modelo 3D de la Rev B)

WASHER_MAT = "C45 (EN 10083-2) templado y revenido a 300–370 HV"     # material ÚNICO de la arandela del perno del pasador (A-14)
BORDE_MIN = 3.0     # borde mínimo [mm] entre un avellanado/agujero y el canto de la pieza o de otro agujero (control de avellanados)
ADVERTENCIA = "ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO."
NOTA_VIENTO = "En caso de vientos fuertes no se recomienda realizar la operación."
NOTA_ANCLAJE = "Equipo sin anclaje: apoyo sobre losa/mats con la presión admisible de la losa indicada en GEN-001 (verificación del cálculo); verificar la superficie de apoyo por terceros."


def load(path=None):
    p = pathlib.Path(path) if path else OUT_DEFAULT / "TT300-C_design.json"
    return json.load(open(p, encoding="utf-8"))


RELIEF = 10.0          # alivio de borde de la cara de contacto uña–pasador: ~10 mm en cada extremo (dato del mandante, hallazgo N8)


def temple_txt(P):
    """Hallazgo N2: el contacto uña–pasador se calcula con Fy_sup = P.Fy_surf (templado); la nota «Dureza 280–330 HB» queda reemplazada por esta."""
    return (f"Pasador y uña: temple por inducción ≥ 55 HRC (límite elástico superficial supuesto en el cálculo: {f(P['Fy_surf'])} MPa), profundidad efectiva según el cálculo")


def alivio_txt(P):
    """Hallazgo N8: la concentración de borde k_edge de la fila de Hertz del núcleo presupone el alivio de borde."""
    return (f"Alivio de borde: bombeo / perfil logarítmico ~{fm(RELIEF, 0)} mm en ambos extremos de la cara de contacto uña–pasador "
            f"(concentración {fm(P['k_edge'], 2)} considerada en Hertz)")


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
        self.t_ring = float(self.IG.get("t_ring", P.get("t_ring", 10.0)))   # pletina del anillo de la madera (núcleo: P.t_ring, 4.ª pasada)
        # --- base ---
        self.B, self.tb = P["B"], P["t_base"]
        self.boss = P["h_boss"] > 0
        self.h_boss, self.D_boss = (P["h_boss"], P["D_boss"]) if self.boss else (0.0, 0.0)
        self.w_collar = float(P["w_collar"])         # filete del collar: parámetro del JSON (mínimo AWS D1.1 T5.8 y máximo AISC J2.2b verificados por el núcleo)
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
        self.z_bush0 = self.tb + self.h_boss + P["g_bush"]     # el buje arranca g_bush (2 mm) sobre el collar
        # pivote con dos zonas rectificadas (decisión de ingeniería, A-02/B-01): p6 en la zona calada en plancha base + collar (H7/p6) y f7 en la zona del buje (F7/f7);
        # transición de 1 mm entre ambas, por debajo del arranque del buje
        self.z_p6 = self.tb + self.h_boss                      # fin de la zona p6 (desde la cara inferior del pivote = cara inferior de la base)
        self.z_f7 = self.z_p6 + 1.0                            # inicio de la zona f7 (transición z_p6…z_f7)
        assert self.z_f7 <= self.z_bush0 + 1e-6, "la zona f7 del pivote debe empezar antes que el buje"
        self.washer_D = self.d_pin + 30
        self.washer_d, self.washer_t = 22.0, 10.0               # arandela del perno M20: agujero Ø22 (ISO 273 medio) y espesor 10
        self.pin_drill, self.pin_drill_L, self.pin_thr = 17.5, 45.0, 40.0   # rosca M20-6H del pasador: broca Ø17,5 prof. 45, rosca útil 40
        # tapas del pivote (PROPUESTA del dibujante, S15): 4 × M10 en PCD 2/3 D_piv (tapa retenedora) y 6 × M8 ISO 10642 en la tapa de inspección (B-02):
        # PCD tal que el avellanado quede dentro de la tapa con borde ≥ 3 mm y el agujero roscado deje pared ≥ 3 mm hacia el agujero central de la plancha superior
        self.cap_pcd = round(P["D_piv"] * 2 / 3, 0)
        self.insp_d, self.insp_drill, self.insp_clear, self.insp_csk, self.insp_L = 8.0, 6.8, 9.0, 17.0, 16   # M8: broca Ø6,8, pasante Ø9 (ISO 273), avellanado Ø17×90° (dk 16, ISO 10642), largo 16
        r_max = (self.cb_D / 2 - 1) - BORDE_MIN - self.insp_csk / 2              # tapa Ø(cb_D − 2)
        r_min = self.hole_top / 2 + BORDE_MIN + self.insp_d / 2
        assert r_max >= r_min, "la tapa de inspección no admite el patrón de tornillos con bordes ≥ 3 mm"
        self.insp_pcd = 2.0 * math.floor(r_max)
        self.tap_m10, self.clear_m10 = 8.5, 11.0       # broca de macho M10 y paso medio (ISO 273)
        self.cap_tap, self.insp_tap = 20.0, 10.0       # taladro ciego del pivote (Ø8,5 prof. 20) y rosca útil M8 en el fondo del rebaje
        self.cap_csk = 21.0                             # avellanado Ø21×90° de la tapa retenedora (dk máx. ISO 10642 M10 = 20, con holgura)
        self.cap_thr = self.cap_tap - 4.0               # rosca útil M10 del pivote (punta del taladro y salida del macho: 4 mm)
        # N-01: largo comercial del tornillo de la tapa retenedora: engrane ≥ 1,0·d y punta ≥ 2 mm antes del fin de la rosca útil (agujero ciego)
        self.cap_L = max(L for L in (8, 10, 12, 16, 20, 25, 30, 35, 40) if L - self.cap_t <= self.cap_thr - 2.0 + 1e-9)
        assert self.cap_L - self.cap_t >= 10.0 - 1e-9, "tapa retenedora: ningún largo ISO 10642 M10 da engrane ≥ 1,0·d sin tocar fondo"
        # tapa de inspección: taladro Ø6,8 PASANTE en el remanente bajo el rebaje (N-20) y rosca útil insp_tap
        self.insp_rem = self.tt - self.cb_t                # espesor remanente bajo el rebaje
        self.ch_pin, self.ch_piv, self.ch_pp = 2.0, 3.0, 2.0      # chaflanes de dibujo (1×45° mínimo ISO 13715): pasador de empuje, pivote, pasadores de articulación
        # --- accionamiento ---
        # modo del accionamiento (núcleo, D.modo): 1 = guiado (patín, uña y leva de reenganche); 2 = pivotado tipo KIET (cajón del ojal E, bloque-uña, placas-leva)
        self.modo = int(D.get("modo") or P.get("drive_mode", 1))
        self.PV = D.get("pivotado") or {}
        self.LG = D.get("levaGuiada") or {}
        self.FPV = self.PV.get("fabricacion") if self.modo == 2 else None
        self.FLG = self.LG.get("fabricacion") if (self.modo == 1 and self.LG.get("activa")) else None
        self.BR = DV["bracket"]
        self.KG = DV["K"]
        self.forkH = DV["forkH"]
        self.zb = self.tb + P["t_bed"]
        self.zT1 = self.zb - P["h_slot"]
        self.zT0 = self.zT1 - P["h_tee"]
        self.fondo = P["t_bed"] - P["h_slot"] - P["h_tee"]
        self.neck_w, self.head_w, self.head_h = P["w_slot"] - 2, P["w_tee"] - 2, P["h_tee"] - 2
        self.neck_h = P["h_slot"] + 1
        if self.modo == 1:
            self.z_shoe = self.KG["shoeTop"]
            self.Hs = self.z_shoe - self.zb
            self.ch_dx = self.KG["travel"]
            self.ch_dy = self.ch_dx / math.tan(math.radians(P["beta_ch"]))
            self.paw_L = self.KG["mouthX"] + P["L_in"] - self.KG["tipX"]
        self.pk_top = self.zc + P["dog_h"] / 2 + 1
        self.pk_bot = self.zc - P["dog_h"] / 2 - 1
        # franja de contacto con el pasador de empuje: alto de la uña (modo 1) o del bloque-uña (modo 2)
        self.h_contact = P["dog_h"] if self.modo == 1 else float(self.FPV["bloque_una"]["h"])
        zh = next((v["dem"] for v in D["verificaciones"] if v["nombre"].startswith("Profundidad mínima de temple")), None)
        self.z_hard = math.ceil(zh * 10) / 10 if zh is not None else None
        # el núcleo no entrega la profundidad mínima de temple en el modo pivotado (requiere núcleo)
        self.z_hard_txt = (f"≥ {fm(self.z_hard, 1)} mm" if self.z_hard is not None else "A DEFINIR (el núcleo no entrega la profundidad mínima de temple en el modo pivotado)")
        # --- izaje ---
        self.cl_lug = self.B / 2 - P["c_lug"]
        self.ear_pos = [(P["x_lug"], self.cl_lug), (-P["x_lug"], self.cl_lug), (P["x_lug"], -self.cl_lug), (-P["x_lug"], -self.cl_lug)]
        # --- interfaz: R_i, rebaje del collar y topes salen del JSON (interfazGeom); este módulo no los recalcula ---
        self.Ro = self.Rt
        self.Ri = float(self.IG["Ri"])               # radio interior efectivo = D_collar/2 + c_boss_r + m_ri (con collar)
        self.Ri_if = self.Ri                         # alias histórico: mismo valor
        self.m_ri = float(self.IG.get("m_ri", P.get("m_ri", 0)))
        self.c_boss_r, self.c_boss_a = float(P.get("c_boss_r", 0)), float(P.get("c_boss_a", 0))
        self.Drb = float(self.IG["D_rebaje_bot"])    # Ø del agujero pasante de la plancha inferior y del rebaje del cubo (D_boss + 2 c_boss_r)
        self.h_rebaje = float(self.IG["h_rebaje"])   # profundidad del rebaje desde la cara inferior de la mesa (h_collar − δ + c_boss_a)
        self.hPl = float(self.IG["h_rebaje_plancha"])   # parte del rebaje en la plancha inferior (agujero pasante si > 0)
        self.hHub = float(self.IG["h_rebaje_cubo"])     # parte del rebaje en el cubo
        self.rebaje = self.boss and self.hPl > 0
        self.z_techo = self.z0 + self.hPl + self.hHub   # techo del rebaje (cara inferior del cubo o fondo del rebaje del cubo)
        self.e_piv = max(P["e_piv"], P["g_bush"] + P["L_bush"] / 2)   # brazo efectivo de flexión (fila «Brazo efectivo del pivote e» del núcleo)
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

    @property
    def variante(self):
        """Código corto de la variante del juego (rótulo y título de cada lámina): BASE, A, AF2, B, C1…C3, W (+ F2 = fijación pegada, W = cubierta de madera)."""
        c = "BASE" if self.opt == 0 else {1: "A", 2: "B", 3: f"C{self.conf}"}[self.opt]
        if self.opt and not self.removable:
            c += "F2"
        if self.wood:
            c = "W" if self.opt == 0 else c + "-W"
        if self.modo == 1:
            c += "-G"                     # alternativa: accionamiento guiado con leva de reenganche (el juego por defecto es el pivotado)
        return c

    @property
    def variante_nombre(self):
        """Descripción completa de la variante: interfaz, fijación y cubierta."""
        I = self.I
        t = self.interfaz_nombre
        tor = I.get("tornillos") if isinstance(I.get("tornillos"), dict) else None
        if self.opt in (1, 2) and not self.removable and tor:
            t = t.split(":")[0] + f", fijación modo 2: discos inoxidables e{fm(I['tss'], 0)}/e{fm(I['tss2'], 0)} pegados" + (" (base liso, mesa ranurado)" if self.opt == 1 else "") + \
                f", sin topes; disco de la mesa con {int(tor['n'])} tornillos avellanados {tor['designacion'].replace(' – ', ' ')} a la mesa (no desmontable)"
        elif self.opt in (1, 2) and not self.removable:
            t = t.split(":")[0] + f", fijación modo 2: discos inoxidables e{fm(I['tss'], 0)}/e{fm(I['tss2'], 0)} pegados" + (" (base liso, mesa ranurado)" if self.opt == 1 else "") + ", sin topes ni tornillos (no desmontable)"
        elif self.opt and not self.removable:
            t += "; fijación modo 2: sectores pegados, sin topes ni tornillos (no desmontable)"
        if self.wood:
            t += f"; con cubierta de madera e = {fm(self.P['t_wood'], 0)} y anillo de contención {fm(self.t_ring, 0)}×{fm(self.P['t_wood'], 0)}"
        t += "; accionamiento pivotado tipo KIET (por defecto)" if self.modo == 2 else "; accionamiento guiado con leva de reenganche (alternativa)"
        return t

    def tope(self, which):
        """Geometría resuelta del tope (interfazGeom.topes, ya calculada por el núcleo) de la pieza 'which' ('base'|'mesa'|'uhmw'); None si no hay topes."""
        T = {t["id"]: t for t in self.IG.get("topes", [])}
        if not T:
            return None
        if which == "uhmw":
            return T.get("uhmw")
        if self.opt in (1, 2):
            return T.get("disc0") if which == "base" else T.get("disc1", T.get("disc0"))
        if self.opt == 3:
            return T.get("bz0") if which == "base" else T.get("bz1")
        return None

    def tope_L(self, which):
        """Largo del tope (mm) entregado por el núcleo para la pieza 'which'."""
        t = self.tope(which)
        return t["L"] if t else None

    def fila(self, prefijo):
        """Fila de verificación del núcleo cuyo nombre empieza con 'prefijo' (o None)."""
        return next((v for v in self.D["verificaciones"] if v["nombre"].startswith(prefijo)), None)

    def junta(self, which):
        """Junta en frío (mm) entre sectores: la mayor entre 1 mm (regla del núcleo) y la dilatación calculada."""
        if which == "uhmw" and self.IG.get("junta_uhmw") is not None:
            return float(self.IG["junta_uhmw"])           # junta en frío efectiva entregada por el núcleo (4.ª pasada)
        if which != "uhmw" and self.IG.get("junta_sector") is not None:
            return float(self.IG["junta_sector"])
        J = self.IG.get("juntas", [])
        calc = 0.0
        for j in J:
            if which == "uhmw" and "UHMW" in j["pieza"]:
                calc = max(calc, j["j"])
            if which != "uhmw" and "UHMW" not in j["pieza"]:
                calc = max(calc, j["j"])
        return math.ceil(max(1.0, calc) * 10) / 10


def supuestos(g):
    """Decisiones de dibujo que el cálculo no fija. Las adoptadas por el mandante se rotulan «ADOPTADO»; el resto, PROVISORIO en las láminas donde intervienen.
    Lo que el núcleo ya resuelve (R_i, rebaje del collar, geometría de topes) NO es un supuesto: se lee del JSON."""
    P = g.P
    S = []

    def add(id_, tema, valor, motivo):
        S.append(dict(id=id_, tema=tema, valor=valor, motivo=motivo))
    if g.opt and g.removable:                 # en la fijación pegada (AF2) no hay topes ni tornillos de posición (H-03)
        add("S01", "Tornillos de posición por sector", "2 por sector (ADOPTADO por el mandante); posición radial en la bisectriz, fuera del tope y de las ranuras (PROVISORIO)",
            f"El cálculo fija solo el diámetro d_tor = M{fm(P['d_tor'], 0)} ISO 10642 y la verificación de la cabeza; no entrega la cantidad ni la posición.")
    if g.opt and g.removable:
        add("S03", "Alojamiento del tope", f"Muesca pasante en la bisectriz del sector, ancho b_tope + 2 = {fm(P['b_tope'] + 2, 0)} mm (1 mm de holgura por lado, coherente con a_inf = w_tope + 1), centrada radialmente en r_u",
            "El cálculo fija L_tope, b_tope, w_tope, a_sup y a_inf (interfazGeom.topes) pero no dónde se aloja la barra respecto del sector.")
    if g.opt:
        add("S04", "Junta entre sectores", "Junta de ancho constante j = máx(1 mm; dilatación calculada) entre bordes paralelos a la bisectriz",
            "El núcleo exige junta en frío ≥ 1 mm y entrega la dilatación.")
    if g.opt == 1 or g.opt == 3:
        add("S05", "Posición de las ranuras de engrase",
            f"{g.n_gr_rad} radiales a k·360°/{g.n_gr_rad} de R_i a R_o (extremos abiertos: purga por el perímetro); {g.n_gr_circ} circunferenciales, la exterior a R_o − 30 y el resto equiespaciadas hasta R_i + 30 (corridas a ≥ 3 mm de la muesca del tope si la cortan)",
            "El núcleo solo usa cantidad, ancho, profundidad y largo total (área perdida y volumen de grasa).")
        add("S08", "Conducto de las graseras", "Grasera M10×1 en el canto del anillo inferior de la mesa (MES-004), sobre la bisectriz de un sector; taladro Ø6 radial hasta R_o − 30 y Ø6 axial hasta la cara deslizante",
            "El núcleo indica «taladro Ø6 hasta la ranura exterior»; trayecto y cota no se entregan.")
    if g.opt == 3:
        add("S09", "Patrón de tapones de grafito", f"Malla triangular (escalonada) de paso {fm(P['bz_plug_p'], 0)} mm, Ø{fm(P['bz_plug_d'], 0)} mm, profundidad {fm(g.IG.get('tapon_prof_frac') or 0.7, 2)}·t; se omiten los tapones a menos de 4 mm de bordes, muescas, tornillos y ranuras",
            "El núcleo usa la fracción de área f_g y la profundidad; no entrega la distribución ni el origen de la malla.")
    if g.opt == 2:
        add("S10", "Sujeción de los sectores de UHMW", "Sin tornillos: rebaje formado por las barras del núcleo (L = L_av = R_o − R_i − 100, interfazGeom.topes «uhmw») soldadas al disco de la base, y retención superior por el disco de la mesa",
            "El núcleo no define tornillos para la lámina UHMW (solo el rebaje con topes).")
    if g.opt and g.removable:
        add("S11", "Largo del tornillo de posición", "ISO 10642 con largo normalizado ≥ t − 0,55·d + 1,5·d (1,5 d de rosca en el respaldo)",
            "Criterio de engrane mínimo en acero; el núcleo verifica solo la cabeza.")
    if g.wood:
        add("S06", "Anillo de acero y tablones de la cubierta de madera", f"ADOPTADO por el mandante: pletina de {fm(g.t_ring, 0)} × {fm(P['t_wood'], 0)} mm (ancho × alto) en el borde, soldada a la plancha superior (t_ring del núcleo; en m.total); tablones de 200 mm de ancho; abertura central Ø{f(g.cb_D)} para la tapa de inspección (PROVISORIA)",
            "El núcleo incluye el anillo (m.ring) y calcula los tablones dentro de él; el espesor del anillo es P.t_ring y el ancho de tablón (200) lo fija el mandante. Bolsillos Ø(arandela + 4) × 31 sobre cada perno de pasador (PROVISORIO).")
    add("S15", "Atornillado de las tapas del pivote", f"Tapa retenedora: 4 × M10 (ISO 10642) en PCD Ø{fm(g.cap_pcd, 0)} a 45°+90°·k, roscados prof. {fm(g.cap_tap, 0)} en el pivote; tapa de inspección: 6 × M{fm(g.insp_d, 0)}×{g.insp_L} (ISO 10642) en PCD Ø{fm(g.insp_pcd, 0)} a 30°+60°·k, roscados prof. {fm(g.insp_tap, 0)} en el fondo del rebaje; avellanado y roscado con borde ≥ {fm(BORDE_MIN, 0)} mm (PROPUESTA)",
        "El cálculo no define el patrón de tornillos de las tapas; se propone uno geométricamente compatible (confirmar).")
    if g.modo == 2:
        F = g.FPV
        add("S21", "Ojales del cilindro (elemento comercial)", f"Pared de ojal 17,5 mm (Ø{fm(F['pasador_E']['d'] + 35, 0)} en E y Ø{fm(F['pasador_Q']['d'] + 35, 0)} en Q); cuello de ancho b_ojal hasta {fm(F['bloque_una']['horquilla']['R_cubo'] + 10, 0)} mm de Q (PROVISORIO)",
            "El núcleo solo exige Ø ojal ≥ d; la geometría la fija el proveedor del cilindro.")
        add("S22", "Posición dibujada del accionamiento", "Pasador de la mesa del modelo dentro del empuje, el más cercano a su inicio; Q = P + L_qp·(E − P)/|E − P| (cinemática del núcleo)", "Las láminas muestran una posición; el núcleo entrega 61.")
        add("S23", "Pernos de las placas-leva", f"ISO 4762 M{fm(F['placas_leva']['pernos']['d'], 0)}×{fm(min(45, F['placas_leva']['t'] + g.tb - 1), 0)} 10.9 roscados pasantes en la base, sin sobresalir bajo la base (PROVISORIO)",
            "El núcleo admite roscado o tuerca bajo la base; la base apoya en la losa (requiere núcleo: engrane).")
    if g.modo == 1 and g.FLG:
        add("S24", "Pasador del vástago bajo el riel-leva", "A ras de la cara superior del patín; retención por anillo elástico inferior (PROPUESTA)", "El riel-leva queda 2 mm sobre el patín (núcleo): no cabe la placa de retención superior.")
    add("S13", "Izaje de la mesa", "No se dibujan puntos de izaje de la mesa (A DEFINIR)", "El cálculo solo define las 4 orejas de izaje de la base (espesor, radio y agujero: parámetros t_ear, R_ear, d_ear); la mesa debe izarse con medios definidos por el montajista.")
    add("S14", "Retención axial del pivote", "Zona p6 del pivote calada H7/p6, sin soldadura ni tope inferior (A DEFINIR)", "El cálculo verifica asiento y flexión pero no la extracción axial del pivote.")
    return S
