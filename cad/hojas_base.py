"""Marco común de las láminas: contexto, hoja con cajetín diferido, programa de soldaduras, ajustes, inspección y notas."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cadquery as cq
import draw
from draw import Sheet, W, H, wrap
from geom import *
import vistas
from vistas import View, COTAS

A1 = "A1 (841×594)"


def circ(c, r, n=96, a0=0.0, a1=360.0):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


class Ctx:
    def __init__(self, m):
        self.m, self.g, self.D, self.P = m, m.g, m.D, m.g.P
        self.sup = supuestos(m.g)
        self.DV = m.g.DV
        self.shapes = {p.key: cq.Compound.makeCompound(list(p.solid.vals())) for p in m.parts}
        COTAS.set_shapes(self.shapes)
        self.hojas = []
        g = self.g
        self.revs = [
            ("B", g.FECHA, "VIGENTE – EMITIDO PARA REVISIÓN. Cambios de la actualización C del cálculo respecto de la Rev. B anterior: paquete de reducción de masa "
             f"(t_pr {fm(self.P['t_pr'], 0)}, t_web {fm(self.P['t_web'], 0)}, t_rib {fm(self.P['t_rib'], 0)}, t_base {fm(self.P['t_base'], 0)}, w_bed {fm(self.P['w_bed'], 0)}, w_s {fm(self.P['w_s'], 0)}); "
             f"collar soldado de asiento del pivote (h {fm(g.h_boss, 0)}, Ø{fm(g.D_boss, 0)}) y rebaje del cubo; 4 orejas de izaje de la base; interfaz según alternativa elegida ({g.interfaz_nombre}); "
             f"f_apoyo {fm(self.P['f_apoyo'], 2)} de la cubierta de madera. Sin consideración de viento ni anclaje (decisión del mandante).", "A DEFINIR", "A DEFINIR", "A DEFINIR"),
            ("B ant.", "—", "Emisión Rev. B anterior (uña guiada de cara plana, patín con lengüeta T, 6 láminas); reemplazada por esta emisión.", "—", "—", "—"),
        ]

    def local(self, key, newkey, near=None, r=1e9, shift=(0, 0, 0), rot=0.0):
        """Copia local de las piezas 'key' cuyo centro está a menos de r de 'near'; se traslada 'shift' y se gira 'rot' grados en torno a z."""
        sol = [x for x in self.shapes[key].Solids() if near is None or math.dist((x.Center().x, x.Center().y, x.Center().z), near) < r]
        c = cq.Compound.makeCompound(sol).translate(cq.Vector(*shift))
        if rot:
            c = c.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rot)
        self.shapes[newkey] = c
        return newkey

    def rotated(self, keys, deg, suffix="_r"):
        out = []
        for k in keys:
            if k in self.shapes:
                self.shapes[k + suffix] = self.shapes[k].rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), deg)
                out.append(k + suffix)
        return out

    def parts(self, *keys):
        return [self.m.get(k) for k in keys if self.m.get(k)]

    def sh(self, *keys):
        return {k: self.shapes[k] for k in keys if k in self.shapes}

    def mass_of(self, *keys):
        return sum(p.mass_total for p in self.parts(*keys))

    def code(self, key):
        return self.m.get(key).code


class Hoja:
    def __init__(self, ctx, plano_sub, plano_num, titulo, escala, material="Ver despiece", masa="—", trat="Ver notas", ids=""):
        self.ctx = ctx
        self.s = Sheet()
        self.plano = f"{CODE}-{plano_sub}-{plano_num:03d}-{REV}"
        self.titulo, self.escala, self.material, self.masa, self.trat, self.ids = titulo, escala, material, masa, trat, ids
        self.tag = f"{plano_sub}-{plano_num:03d}"
        ctx.hojas.append(self)
        COTAS.sheet = self.plano

    def begin(self):
        COTAS.sheet = self.plano
        return self.s

    def finish(self, n, total):
        g = self.ctx.g
        info = dict(proj="TT300-C · TORNAMESA HIDRÁULICA 300 tf", subproj=f"Interfaz: {g.interfaz_nombre}", titulo=self.titulo, plano=self.plano, lamina=f"{n} de {total}", escala=self.escala,
                    formato=A1, material=self.material, masa=self.masa, trat=self.trat, rev=REV, fecha=g.FECHA, revs=self.ctx.revs, aviso=ADVERTENCIA,
                    estado="EMITIDO PARA REVISIÓN – NO APTO PARA FABRICACIÓN HASTA SU APROBACIÓN", generales="Tolerancias generales ISO 2768-m; soldadura ISO 2553 / ISO 5817; rugosidad ISO 1302.")
        self.s.frame(info)
        return self.s


# ----------------------------------------------------------------------------------------------
# datos normativos y de fabricación comunes
# ----------------------------------------------------------------------------------------------
def fillet_min(t):
    """Tamaño mínimo de filete según la parte más gruesa (registro de criterios del proyecto; AWS D1.1 Tabla 5.8)."""
    return 3 if t <= 6 else 5 if t <= 12 else 6 if t <= 20 else 8


def soldaduras(ctx):
    """Programa de soldaduras: lista de dicts (id, juntas, tipo, tamaño, proceso, calidad, END, nota). Los tamaños salen de P; donde el núcleo no fija
    un tamaño se adopta el mínimo AWS D1.1 por la parte más gruesa y se rotula así."""
    P, g = ctx.P, ctx.g
    W = []
    ws = lambda n: f"WPS-{n:02d} A DEFINIR POR EL FABRICANTE"
    proc = "135 (GMAW, ER70S-6) / 111 (SMAW, E7018)"
    tb = g.tb
    add = lambda **k: W.append(dict(id=f"W{len(W) + 1:02d}", **k))
    add(juntas="Marco perimetral – plancha base", tipo="Filete ambos lados, continuo", size=fillet_min(max(P["rim_t"], tb)), nota="mín. AWS por parte más gruesa (el cálculo no fija)", calidad="C", end="MT 10 %", wps=ws(1), proc=proc)
    add(juntas="Marco largo – marco corto (esquinas)", tipo="Filete en ángulo exterior, continuo", size=fillet_min(P["rim_t"]), nota="mín. AWS", calidad="C", end="MT 10 %", wps=ws(1), proc=proc)
    add(juntas="Mejilla de ménsula – plancha base", tipo="Filete ambos lados, 4 líneas por ménsula", size=P["w_br"], nota="w_br (P)", calidad="B", end="MT 100 %", wps=ws(2), proc=proc)
    add(juntas="Orejas sup./inf. de ménsula – mejillas", tipo="Filete ambos lados", size=fillet_min(P["t_ch"]), nota="mín. AWS (t = t_ch)", calidad="B", end="MT 100 %", wps=ws(2), proc=proc)
    add(juntas="Oreja inferior (bloque) – plancha base", tipo="Filete todo alrededor", size=fillet_min(P["t_ch"]), nota="mín. AWS", calidad="B", end="MT 100 %", wps=ws(2), proc=proc)
    add(juntas="Bancada – plancha base", tipo="Filete ambos lados, continuo, precalentar 65 °C", size=P["w_bed_f"], nota="w_bed_f (P)", calidad="B", end="MT 100 %", wps=ws(3), proc=proc)
    if g.boss:
        add(juntas="Collar del pivote – plancha base", tipo="Filete perimetral continuo", size=g.w_collar, nota="10 mm: dato de la verificación del núcleo", calidad="B", end="MT 100 % + UT de la unión", wps=ws(4), proc=proc)
    add(juntas="Orejas de izaje – plancha base", tipo="Filete ambos lados (L = 2R), biselar la base de la oreja", size=P["w_ear"], nota="w_ear (P)", calidad="B", end="MT 100 % + UT 100 %", wps=ws(5), proc=proc)
    add(juntas="Segmentos de los anillos de la mesa (4 × 90°)", tipo="CJP a tope en V 60°, raíz 3, con respaldo", size=f"t = {fm(g.tpr, 0)}", nota="empalme", calidad="B", end="UT 100 %", wps=ws(6), proc=proc)
    add(juntas="Discos centrales – anillos de la mesa", tipo="CJP a tope en V 60°, raíz 3, con respaldo", size=f"t = {fm(g.tbo, 0)}–{fm(g.tt, 0)}", nota="a tope de planchas de distinto espesor (transición 1:4)", calidad="B", end="UT 100 %", wps=ws(6), proc=proc)
    add(juntas="Almas anulares – planchas superior e inferior", tipo="Filete ambos lados, continuo", size=P["w_web"], nota="w_web (P)", calidad="B", end="MT 100 %", wps=ws(7), proc=proc)
    add(juntas="Nervios – planchas y almas", tipo="Filete ambos lados, continuo", size=P["w_web"], nota="w_web (P)", calidad="B", end="MT 100 %", wps=ws(7), proc=proc)
    add(juntas="Empalme de almas anulares", tipo="CJP a tope en V 60°", size=f"t = {fm(P['t_web'], 0)}", nota="1 por anillo", calidad="B", end="UT 100 %", wps=ws(6), proc=proc)
    add(juntas="Cubo – planchas inferior y superior", tipo="CJP bisel 45° con respaldo", size=f"t = {fm(g.tt, 0)}", nota="cierre de la mesa", calidad="B", end="UT 100 %", wps=ws(6), proc=proc)
    add(juntas="Cierre de la plancha superior (ranuras de tapón)", tipo="Soldadura en ranura 22×80 c/250, relleno completo", size="c/250", nota="tapones sobre almas/nervios", calidad="C", end="MT 100 %", wps=ws(7), proc=proc)
    if g.opt and g.removable:
        if g.opt in (1, 2, 3):
            add(juntas="Topes de sector – plancha base y plancha inferior de la mesa", tipo="2 filetes (frente y dorso de la barra b_tope), continuos", size=P["w_tope"], nota="w_tope (P); soldar antes del alivio y del rectificado de las caras", calidad="B", end="MT 100 %", wps=ws(8), proc=proc)
        if g.opt == 2:
            add(juntas="Barras del rebaje UHMW – disco inoxidable de la base", tipo="2 filetes, electrodo inoxidable (309L), continuos", size=P["w_tope"], nota="w_tope (P)", calidad="B", end="PT 100 %", wps=ws(9), proc="135 (GMAW) / 141 (GTAW), ER309L")
    if g.wood:
        add(juntas="Anillo de contención – plancha superior de la mesa", tipo="Filete ambos lados, continuo", size=P["w_web"], nota="PROVISORIO (S06)", calidad="C", end="MT 10 %", wps=ws(10), proc=proc)
    for w in W:
        w["tamano"] = (f"z{fm(w['size'], 0)}" if isinstance(w["size"], (int, float)) else w["size"])
    return W


def weld_by(ctx, frag):
    return next((w for w in soldaduras(ctx) if frag in w["juntas"]), None)


def ajustes(ctx):
    P, g = ctx.P, ctx.g
    return [
        ("Pivote en plancha base y collar", f"Ø{f(P['D_piv'])} p6 / H7", "Prensado o contracción (hielo seco); agujero mandrinado en línea (mandrinadora)", "ISO 286-2"),
        ("Pivote en buje", f"Ø{f(P['D_piv'])} f7 / F7 (zona del buje)", "Deslizante lubricado (buje autolubricado)", "ISO 286-2"),
        ("Buje en cubo de la mesa", f"Ø{f(g.d_bush)} s6 / H7", "Prensado", "ISO 286-2"),
        ("Pasador de empuje en anillos", f"Ø{f(g.d_pin)} m6 / H7", "Transición, desmontable (sin soldadura)", "ISO 286-2"),
        ("Pasador de articulación en ojales", f"Ø{f(P['d_pp'])} f8 / H9", "Deslizante, grasa grafitada", "ISO 286-2"),
        ("Lengüeta del patín (cuello) en ranura", f"{f(g.neck_w)} f7 / {f(P['w_slot'])} H8", "Deslizante guiado, 1 mm de holgura por lado en cabeza T", "ISO 286-2"),
        ("Cabeza T del patín", f"{f(g.head_w)} h11 / {f(P['w_tee'])} +0,2/0", "Retención vertical con juego", "ISO 286-1"),
        ("Uña en alojamiento del patín", f"{f(P['dog_b'])} f8 / H9 × {f(P['dog_h'])} f8 / H9", "Deslizante con retorno de resorte", "ISO 286-2"),
        ("Collar en rebaje del cubo", f"Ø{f(g.D_boss)} con holgura radial ≥ 25 mm", "Sin contacto", "Criterio del núcleo"),
    ]


def inspecciones(ctx):
    g, P = ctx.g, ctx.P
    L = [
        ("Recepción", "Certificados EN 10204 3.1 de todas las planchas, barras y forjas; trazabilidad por colada; UT ASTM A578 nivel B de las planchas de la mesa."),
        ("Recepción", f"Dureza del núcleo QT de pasadores y uñas 280–330 HB; Re ≥ {f(P['Fy_dog'])} MPa en probeta de la forja (uñas)."),
        ("Soldadura", "WPS/PQR calificados AWS D1.1 y calificación de soldadores; registro de precalentamiento e interpase (≤ 250 °C)."),
        ("Soldadura", "Inspección visual 100 % (ISO 17637) antes de cualquier END; niveles de calidad ISO 5817 según el programa de soldaduras."),
        ("END", "MT 100 % en filetes críticos (ménsulas, collar, orejas, bancadas, topes, almas y nervios) según el programa; PT en uniones inoxidables."),
        ("END", "UT 100 % en uniones CJP (anillos, discos, cubo) según AWS D1.1; UT de las orejas de izaje y del collar."),
        ("Dimensional", f"Planitud de la cara de apoyo de la base (zona Ø{f(P['D_top'] + 20)}) ≤ 0,20 mm y de la cara inferior de la mesa ≤ 0,20 mm antes de montar la interfaz."),
        ("Dimensional", f"Pasadores: PCD Ø{f(2 * g.R_pin)} ±0,3; paso {fm(360 / g.N_pin, 3)}° ±0,05°; agujeros Ø{f(g.d_pin)} H7 coaxiales en ambos anillos (0,05)."),
        ("Dimensional", f"Pivote: perpendicularidad ≤ 0,05 respecto de la cara de apoyo; coaxialidad collar–plancha base 0,05; altura del eje de ménsulas {f(g.hax)} ±0,5."),
        ("Dimensional", f"Ranura T de bancadas: ancho {f(P['w_slot'])} H8, paralelismo ±0,10 en todo el largo, coaxial con el ojal de la ménsula ±0,2."),
        ("Dimensional", f"Orejas de izaje: posición (±{f(P['x_lug'])}, ±{f(g.cl_lug)}) ±2; plano vertical radial; agujero Ø{f(P['d_ear'])} a {f(P['h_ear'])} sobre la base ±1."),
        ("Dureza", f"Uñas: dureza superficial 100 % (≥ 55 HRC) y profundidad de temple ≥ {fm(g.z_hard, 1)} mm en probeta testigo por lote; MT de caras templadas; pasadores: 10 % de la franja."),
        ("Torque", f"Pernos M20×45 de los {g.N_pin} pasadores: torque de apriete A DEFINIR POR EL CALCULISTA/proveedor (ISO 898-1, VDI 2230); registro por perno."),
        ("Torque", "Tornillos de posición, tapas retenedora e inspección: torque según catálogo del tornillo (A DEFINIR); marcar con pintura de control."),
        ("Prueba", f"Prueba hidráulica de cilindros y circuito a 1,5·{f(P['p_relief'])} bar según certificado del fabricante; presión máxima de trabajo {fm(P['p_rated'] * 0.0689476, 0)} bar (p_rated)."),
        ("Prueba", f"Prueba de carga de izaje de la base a 1,25·WLL de las orejas con grillete y eslinga certificados; MT de soldaduras de orejas después de la prueba."),
        ("Aceptación", f"Giro 360° con 1,0 WLL registrando la presión de despegue; μ real ≤ {fm(P['mu_d'] if g.opt == 0 else ctx.D['apoyo']['mu']['d'], 2)} (diseño de la interfaz elegida)."),
    ]
    return [(i + 1,) + x for i, x in enumerate(L)]


def notas_fab(ctx, extra=()):
    g = ctx.g
    base = ["Tolerancias generales ISO 2768-m (lineal y angular); geométricas ISO 1101; rugosidad ISO 1302; ajustes ISO 286.",
            "Soldadura ISO 2553; nivel de calidad ISO 5817 indicado en cada símbolo; procesos AWS D1.1; WPS «WPS-xx A DEFINIR POR EL FABRICANTE».",
            "Materiales con certificado EN 10204 3.1. Aristas vivas rotas 1×45° salvo indicación.",
            f"Taller sin torno vertical: piezas de gran diámetro por corte a llama/plasma y soldadura; ajustes largos H7 por mandrinadora o taladro radial.",
            "Estado: EMITIDO PARA REVISIÓN. No fabricar hasta aprobación por ingeniero calculista habilitado."]
    return base + list(extra)
