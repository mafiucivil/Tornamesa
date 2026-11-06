"""Láminas generales: notas y normas con índice, programa de soldaduras, inspección, tolerancias y ajustes, materiales, tratamientos, torques y compras,
supuestos y brechas, lista de cortes (nesting) y lista de verificación del revisor."""
import math, sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_util import *
import lista

PLAN_GEN = []


def gen(fn):
    PLAN_GEN.append(fn.__name__)
    return fn


class Gen(Pieza):
    def __init__(self, ctx, num, titulo, fmt="A1"):
        self.ctx = ctx
        h = Hoja(ctx, f"GEN-{num:03d}", titulo, "S/E", fmt=fmt, material="No aplica (lámina de información)", masa="—", trat="—", serie="GEN")
        self.h = h
        self.s = h.begin()
        self.R = h.R
        self.scales, self.vlist = [], []
        self.dims_n0 = len(vistas.COTAS.rows)

    def table_pages(self, cols, rows, title, titulo_hoja, num0, widths=None, hh=T_S):
        """Tabla que continúa en hojas siguientes si no cabe. Devuelve lista de Hoja."""
        out = []
        n = 0
        pend = rows
        while True:
            g = self if n == 0 else Gen(self.ctx, num0 + n, f"{titulo_hoja} (HOJA {n + 1})")
            R = g.R["main"]
            y, left = g.s.table(R[0], R[3], cols, pend, h=hh, ymin=R[1] + 4, title=title + (f" — hoja {n + 1}" if n else ""))
            out.append(g.h)
            if not left:
                return out, g, y
            pend = left
            n += 1


@gen
def sheet_notas(ctx):
    g = ctx.g
    c = Gen(ctx, 1, "NOTAS GENERALES, NORMAS APLICABLES E ÍNDICE DE PLANOS")
    s = c.s
    R = c.R["main"]
    notas = [ADVERTENCIA, "ESTADO DE TODAS LAS LÁMINAS: EMITIDO PARA REVISIÓN. No fabricar hasta la aprobación por un ingeniero calculista habilitado; los campos DIBUJÓ/REVISÓ/APROBÓ están A DEFINIR.",
             NOTA_VIENTO + " (sin análisis de viento en el cálculo).", NOTA_ANCLAJE,
             "Fuente única: todos los valores salen del JSON de diseño del núcleo de cálculo (exportado por la herramienta TT300-C); si el JSON cambia, regenerar el juego completo.",
             "Unidades: mm, kg, MPa, grados. Cotas en mm salvo indicación. No medir sobre el plano. Método de proyección E (ISO 5456-2).",
             "Tolerancias generales ISO 2768-mK (lineal y angular) y ISO 13920 para piezas soldadas (clase B/F); rugosidad no indicada: Ra 12,5.",
             "Soldadura: ISO 2553 (símbolos), ISO 5817 (calidad), ISO 4063 (procesos 111/135/141), AWS D1.1 (calificación, END). WPS/PQR: A DEFINIR POR EL FABRICANTE.",
             "Materiales con certificado EN 10204 3.1; trazabilidad por colada; punzonar el código de la pieza.",
             "Aristas vivas rotas 1×45° (ISO 13715) salvo indicación. Rosca métrica ISO 262 / ISO 724; tornillería ISO 4762 / ISO 10642, clase 10.9 (ISO 898-1).",
             "Taller sin torno vertical: gran diámetro por oxicorte/plasma, soldadura y mandrinadora; ajustes largos H7 en mandrinadora.", pintura(ctx),
             "Sin viento ni anclaje (mandante): el equipo apoya sobre losa/mats con presión ≤ q_losa; la verificación de la losa es de terceros."]
    y = s.notes_block(R[0], R[3], "NOTAS GENERALES DE FABRICACIÓN", notas, h=T_N, width=0.46 * (R[2] - R[0]), numbered=True)
    nor = [("ISO 128", "Dibujo técnico: tipos de línea, vistas, cortes y achurado"), ("ISO 129-1", "Acotado"), ("ISO 1101", "Tolerancias geométricas"), ("ISO 1302", "Indicación de la textura superficial"),
           ("ISO 2553 / ISO 4063", "Símbolos de soldadura / procesos"), ("ISO 5817 / ISO 9692-1", "Niveles de calidad / preparación de juntas"), ("ISO 5457 / ISO 7200 / ISO 5456-2", "Formatos, cajetín, método de proyección"),
           ("ISO 3098", "Escritura"), ("ISO 286-1/-2", "Sistema de tolerancias y ajustes ISO"), ("ISO 2768-1", "Tolerancias generales"), ("ISO 13715", "Aristas de forma indefinida"),
           ("AWS D1.1", "Código de soldadura de acero estructural (T5.8 filete mínimo)"), ("AISC 360-22", "Especificación (J2.2b filete máximo, D5.2 orejas)"), ("BTH-1 Cat. B", "Diseño de dispositivos de izaje bajo el gancho"),
           ("ASME B30.26", "Grilletes de izaje"), ("ISO 898-1 / VDI 2230", "Propiedades de tornillos / uniones atornilladas"), ("EN 10204 3.1", "Certificados de inspección"),
           ("ASTM A572 Gr.50, A36 (ref.), A240, A578, EN 10164", "Aceros estructurales, inoxidable, UT de planchas, propiedades en espesor"), ("EN 10083-3 (34CrNiMo6+QT)", "Aceros bonificados (pasadores, uña)"),
           ("ISO 12944", "Protección anticorrosiva (referencia; sistema A DEFINIR)")]
    x2 = R[0] + 0.48 * (R[2] - R[0])
    yn, _ = s.table(x2, R[3], [("Norma", 70, "L"), ("Aplicación", 130, "L")], [list(n) for n in nor], h=T_S, title="NORMAS APLICABLES")
    c.h.indice_pos = (R[0], min(y, yn) - 10, R[2] - R[0], R[1])
    return c.h


def tabla_indice(ctx, h, hojas):
    """Índice de planos en GEN-001 (se llama al final, con todas las láminas)."""
    s = h.s
    x, y, w, ymin = h.indice_pos
    rows = [[hh.plano.replace(CODE + "-", "").replace("-" + REV, ""), hh.titulo, hh.fmt, hh.escala, REV] for hh in hojas]
    half = (len(rows) + 1) // 2
    wc = (w - 6) / 2
    sc = wc / 190.0
    cols = [("Plano", 30 * sc, "L"), ("Título", 105 * sc, "L"), ("Fmt", 12 * sc, "C"), ("Escala", 30 * sc, "L"), ("Rev", 13 * sc, "C")]
    y1, l1 = s.table(x, y, cols, rows[:half], h=T_S, ymin=ymin, title="ÍNDICE DE PLANOS")
    y2, l2 = s.table(x + wc + 6, y, cols, rows[half:], h=T_S, ymin=ymin)
    return bool(l1 or l2)


@gen
def sheet_soldaduras_global(ctx):
    c = Gen(ctx, 7, "PROGRAMA DE SOLDADURAS: TABLA GLOBAL DE JUNTAS")
    R = c.R["main"]
    sc = (R[2] - R[0]) / sum(w for _, w, _ in WELD_COLS)
    cols = [(t, w * sc, a) for t, w, a in WELD_COLS]
    out, last, y = c.table_pages(cols, weld_rows(ctx), "PROGRAMA DE SOLDADURAS (Junta N°, piezas, tipo, preparación, garganta a, cateto z, longitud, pasadas, proceso, aporte, WPS, END)", "PROGRAMA DE SOLDADURAS", 7)
    last.s.notes_block(R[0], y - 6, "NOTAS", ["Tamaños: parámetros w_* del núcleo; donde el núcleo no fija el tamaño se adopta el mínimo AWS D1.1 Tabla 5.8 por la parte más gruesa y se rotula «mínimo AWS, a confirmar».",
                                              "a = 0,707·z (filete de lados iguales). Nº de pasadas: orientativo (WPS define). Aporte compatible con FEXX = %s MPa (E70xx)." % f(ctx.P["FEXX"]),
                                              "Todas las juntas llevan símbolo ISO 2553 con su número J## en las láminas de pieza o de subconjunto; la tabla de cada lámina repite las juntas que contiene.",
                                              "END: VT 100 % de todas las juntas; MT/UT/PT según columna (AWS D1.1 y BTH-1 Cat. B). Soldadores y WPS calificados por el fabricante."], h=T_N, width=700, numbered=True)
    return out


@gen
def sheet_inspeccion(ctx):
    c = Gen(ctx, 3, "PLAN DE INSPECCIÓN Y ENSAYOS")
    R = c.R["main"]
    w = R[2] - R[0]
    rows = [[str(n), t, d, q, m_] for (n, t, d, q, m_) in inspecciones(ctx)]
    out, last, y = c.table_pages([("N°", 0.04 * w, "C"), ("Etapa", 0.09 * w, "L"), ("Verificación / criterio", 0.56 * w, "L"), ("Alcance", 0.17 * w, "L"), ("Método", 0.14 * w, "L")], rows,
                                 "PLAN DE INSPECCIÓN Y ENSAYOS (VT 100 %, MT/UT según AWS D1.1 y BTH-1 Cat. B)", "PLAN DE INSPECCIÓN", 3)
    return out


@gen
def sheet_tolerancias(ctx):
    P, g = ctx.P, ctx.g
    c = Gen(ctx, 4, "TOLERANCIAS Y AJUSTES (ISO 286) Y TOLERANCIAS GEOMÉTRICAS")
    s = c.s
    R = c.R["main"]
    w = R[2] - R[0]
    rows = []
    for (desc, d, ho, sh_, app) in ajustes(ctx):
        t = ajuste_txt(d, ho, sh_)
        rows.append([desc, f"Ø{fm(d, 0)}", ho, sh_, t["h_lim"], t["s_lim"], t["juego"], t["tipo"], app])
    rows.append(["Collar en rebaje (núcleo)", f"Ø{f(g.D_boss)}", "—", "—", f"Ø{fm(g.Drb, 1)}", f"Ø{fm(g.D_boss, 1)}", f"{fm(g.c_boss_r * 1000, 0)} (radial)", "con juego", f"c_boss_r = {fm(g.c_boss_r, 0)} y c_boss_a = {fm(g.c_boss_a, 0)} mm del núcleo"])
    y, _ = s.table(R[0], R[3], [("Ajuste", 0.17 * w, "L"), ("Nominal", 0.05 * w, "C"), ("Agujero", 0.05 * w, "C"), ("Eje", 0.05 * w, "C"), ("Límites agujero [mm]", 0.11 * w, "C"), ("Límites eje [mm]", 0.11 * w, "C"),
                                      ("Juego mín/máx [µm]", 0.10 * w, "C"), ("Tipo", 0.08 * w, "L"), ("Aplicación", 0.28 * w, "L")], rows, h=T_S, title="TABLA DE AJUSTES ISO 286-1/-2 (límites calculados)")
    gd = [["Planitud", "Cara de apoyo de la base (Ø%s)" % f(P["D_top"] + 20), "0,20", "—"], ["Planitud", "Cara inferior de la mesa", "0,20", "—"], ["Perpendicularidad", "Agujero Ø%s H7 respecto de la cara de apoyo" % f(P["D_piv"]), "0,05", "A"],
          ["Coaxialidad", "Collar – agujero de la base", "Ø0,05", "A"], ["Coaxialidad", "Ojales de ménsula (Ø%s H9)" % f(P["d_pp"]), "Ø0,10", "A"], ["Paralelismo", "Ranura T de la bancada", "0,10", "A"],
          ["Posición", "PCD de %d pasadores Ø%s" % (g.N_pin, f(g.d_pin)), "Ø0,3", "A"], ["Coaxialidad", "Agujeros de pasadores superior/inferior", "Ø0,05", "—"], ["Planitud", "Cara de empuje de la uña", "0,05", "—"],
          ["Cilindricidad", "Pasadores y pivote", "0,02", "—"]]
    y2, _ = s.table(R[0], y - 8, [("Característica (ISO 1101)", 0.16 * w, "L"), ("Elemento", 0.40 * w, "L"), ("Tolerancia [mm]", 0.10 * w, "C"), ("Datum", 0.07 * w, "C")], gd, h=T_S, title="TOLERANCIAS GEOMÉTRICAS PRINCIPALES")
    gen_t = [["0,5 a 3", "±0,1", "±0,2", "±0,3"], ["3 a 6", "±0,1", "±0,3", "±0,5"], ["6 a 30", "±0,2", "±0,5", "±1,0"], ["30 a 120", "±0,3", "±0,8", "±1,5"], ["120 a 400", "±0,5", "±1,2", "±2,5"],
             ["400 a 1.000", "±0,8", "±2,0", "±4,0"], ["1.000 a 2.000", "±1,2", "±3,0", "±6,0"], ["2.000 a 4.000", "—", "±4,0", "±8,0"]]
    s.table(R[0] + 0.62 * w, y - 8, [("Rango [mm]", 0.12 * w, "L"), ("f (fina)", 0.08 * w, "C"), ("m (media)", 0.08 * w, "C"), ("c (basta)", 0.08 * w, "C")], gen_t, h=T_S, title="ISO 2768-1 (se aplica «m»; piezas soldadas ISO 13920 clase B)")
    return c.h


@gen
def sheet_materiales(ctx):
    c = Gen(ctx, 5, "MATERIALES Y CERTIFICADOS")
    R = c.R["main"]
    w = R[2] - R[0]
    rows = []
    for p in ctx.m.parts:
        rows.append([p.code.replace(CODE + "-", ""), p.name, str(p.qty), p.material, p.cert, "Comercial" if p.comercial else ("Núcleo" if p.core else "Adoptado"), p.tratamiento if p.tratamiento != "—" else "—"])
    out, last, y = c.table_pages([("Código", 0.07 * w, "L"), ("Pieza", 0.18 * w, "L"), ("Cant", 0.04 * w, "C"), ("Material (norma, grado, Fy del cálculo)", 0.33 * w, "L"), ("Certificado", 0.14 * w, "L"),
                                  ("Origen", 0.07 * w, "L"), ("Tratamiento", 0.17 * w, "L")], rows, "MATERIALES POR PIEZA (certificado EN 10204 3.1; grados no definidos por el cálculo: «SEGÚN CÁLCULO Fy ≥ …, A DEFINIR»)", "MATERIALES Y CERTIFICADOS", 5)
    return out


@gen
def sheet_tratamientos(ctx):
    g, P = ctx.g, ctx.P
    c = Gen(ctx, 6, "TRATAMIENTOS TÉRMICOS Y SUPERFICIALES, PINTURA")
    R = c.R["main"]
    w = R[2] - R[0]
    rows = [["Base soldada, mesa soldada", "Alivio de tensiones 590–620 °C (2 h/25 mm), enfriamiento lento; antes del mecanizado final", "Fabricante (registro de horno)"],
            ["Pasadores de empuje (MES-012)", f"Bonificado + temple por inducción de la franja de contacto ≥ 55 HRC (Fy_sup {f(P['Fy_surf'])} MPa), profundidad ≥ {fm(g.z_hard, 1)} mm", "Dureza 10 % por lote; macrografía"],
            ["Uña de empuje (ACC-004)", f"34CrNiMo6+QT Re ≥ {f(P['Fy_dog'])} MPa (probeta de la forja); temple por inducción de la cara ≥ 55 HRC, prof. ≥ {fm(g.z_hard, 1)} mm; revenido; alivio de borde {fm(RELIEF, 0)} mm", "Dureza 100 %; MT cara"],
            ["Pivote (PIV-001)", f"Bonificado según Fy ≥ {f(P['Fy_piv'])} MPa (grado A DEFINIR POR EL FABRICANTE)", "Certificado 3.1"],
            ["Pasadores de articulación (ACC-005/006)", f"Bonificado según Fy ≥ {f(P['Fy_pp'])} MPa (grado A DEFINIR); 28–34 HRC de referencia", "Certificado 3.1"],
            ["Discos de interfaz inoxidables", "Decapado y pasivado; rectificado/lapeado de la cara deslizante Ra 0,4", "Rugosidad 100 % de caras"],
            ["Disco duro 17-4PH (opción C)", f"Condición H1025 o inoxidable nitrurado; ≥ {f(P['HB_cara'])} HB, Fy ≥ {f(P['Fy_cara'])} MPa", "Dureza 100 %"],
            ["Bronce C95400 con tapones de grafito (opción C)", f"≥ {f(P['HB_bz'])} HB, Fy ≥ {f(P['Fy_bz'])} MPa; tapones encastrados al {fm((g.IG.get('tapon_prof_frac') or 0.7) * 100, 0)} % del espesor", "Certificado del proveedor"],
            ["UHMW-PE (opción B)", "Sin tratamiento ni pintura; UHMW-PE (grado A DEFINIR POR CATÁLOGO según proveedor)", "Certificado del proveedor"],
            ["Estructura de acero (base, mesa, soldaduras)", pintura(ctx), "Medición de EPS y adherencia (a definir)"],
            ["Zonas sin pintura", f"Cara de apoyo de la interfaz (Ø{f(P['D_top'] + 20)}), caras deslizantes, agujeros H7/H9, ranura T, superficies de contacto de pasadores", "VT"],
            ["Tornillería", "Pernos 10.9 con recubrimiento (zincado/dacromet) A DEFINIR POR CATÁLOGO", "Certificado del lote"]]
    out, last, y = c.table_pages([("Elemento", 0.22 * w, "L"), ("Tratamiento / especificación", 0.58 * w, "L"), ("Control", 0.20 * w, "L")], rows, "TRATAMIENTOS TÉRMICOS Y SUPERFICIALES", "TRATAMIENTOS", 6)
    return out


# --------------------------------------------------------------------------- torques y compras
AS_M = {6: 20.1, 8: 36.6, 10: 58.0, 12: 84.3, 16: 157.0, 20: 245.0}


def torque_rows(ctx):
    g, P = ctx.g, ctx.P
    rows = []
    items = [("Perno ISO 4762 M20×45 cl. 10.9 (retención de pasador)", 20, 10.9, g.N_pin), ("Tornillo ISO 10642 M10×25 cl. 10.9 (tapa retenedora)", 10, 10.9, 4), ("Tornillo M10 avellanado cl. 10.9 (tapa de inspección)", 10, 10.9, 6)]
    if g.opt and g.removable:
        items.append((f"Tornillo ISO 10642 M{fm(P['d_tor'], 0)} cl. 10.9 (posición de sectores; no transmiten carga)", int(P["d_tor"]), 10.9, None))
    for nm, d, cl, n in items:
        As = AS_M.get(d, math.pi / 4 * (0.9 * d) ** 2)
        rp = 940.0 if cl == 10.9 else 640.0
        F = 0.7 * rp * As / 1000.0          # kN, precarga 70 % de la carga de prueba
        K = 0.20
        T = K * F * 1000 * d / 1000.0       # N·m
        rows.append([nm, str(n if n is not None else "según cantidad"), f"M{d}", f(As, 1), f(rp, 0), f(F, 1), fm(K, 2), f(T, 0), "PROPUESTA, A CONFIRMAR POR EL CALCULISTA"])
    return rows


@gen
def sheet_torques_compras(ctx):
    P, g = ctx.P, ctx.g
    c = Gen(ctx, 8, "TORQUES DE APRIETE (PROPUESTA) Y LISTA DE COMPRAS DE ELEMENTOS COMERCIALES")
    s = c.s
    R = c.R["main"]
    w = R[2] - R[0]
    y, _ = s.table(R[0], R[3], [("Elemento", 0.30 * w, "L"), ("Cant", 0.07 * w, "C"), ("Rosca", 0.05 * w, "C"), ("A_s [mm²]", 0.07 * w, "R"), ("Rp0,2 [MPa]", 0.07 * w, "R"), ("F_pre = 0,7·Rp0,2·A_s [kN]", 0.11 * w, "R"),
                                      ("K (lubric.)", 0.06 * w, "R"), ("T = K·F·d [N·m]", 0.09 * w, "R"), ("Estado", 0.18 * w, "L")], torque_rows(ctx), h=T_S,
                   title="TORQUES DE APRIETE ORIENTATIVOS (ISO 898-1, VDI 2230 simplificado, rosca lubricada): el núcleo no los entrega")
    y = s.notes_block(R[0], y - 5, "NOTA", ["Método simplificado: precarga al 70 % de la carga de prueba (Rp0,2 de ISO 898-1 clase 10.9 = 940 MPa), factor de torque K = 0,20 (lubricado con grasa); T = K·F·d. Sin cálculo de la unión (rigidez, asentamiento): PROPUESTA, A CONFIRMAR POR EL CALCULISTA; usar llave dinamométrica calibrada y marca de pintura de control."], h=T_N, width=w)
    rows = []
    for p in ctx.m.parts:
        if p.comercial:
            rows.append([p.code.replace(CODE + "-", ""), p.name, str(p.qty), p.desc, p.catalogo or "A DEFINIR POR CATÁLOGO", p.cert])
    for (d, q, e, cat) in lista.extras(ctx):
        rows.append(["—", d, str(q), e, cat, "A DEFINIR"])
    s.table(R[0], y - 6, [("Código", 0.07 * w, "L"), ("Elemento", 0.22 * w, "L"), ("Cant", 0.05 * w, "C"), ("Especificación", 0.36 * w, "L"), ("Catálogo / proveedor", 0.20 * w, "L"), ("Certificado", 0.10 * w, "L")], rows, h=T_S, ymin=R[1] + 3,
            title="COMPRAS DE ELEMENTOS COMERCIALES (cilindro, buje, pernos, tornillos, arandelas, graseras, grillete B30.26, resortes, grasa)")
    return c.h


# --------------------------------------------------------------------------- nesting
STOCK = [(1500, 6000), (2000, 6000), (2440, 6000), (2440, 12000), (3000, 12000)]


def shelf_pack(items, W_, H_):
    """Empaque por estantes (rectángulos w×h con rotación). Devuelve (n_planchas, posiciones[(plancha,x,y,w,h,label)])."""
    items = sorted(items, key=lambda r: -max(r[0], r[1]))
    sheets, pos = [], []
    for (w, h, lab) in items:
        placed = False
        for rot in ((w, h), (h, w)):
            if rot[0] > W_ or rot[1] > H_:
                continue
            for si, sh in enumerate(sheets):
                for shelf in sh["shelves"]:
                    if shelf["h"] >= rot[1] and shelf["x"] + rot[0] <= W_:
                        pos.append((si, shelf["x"], shelf["y"], rot[0], rot[1], lab)); shelf["x"] += rot[0]; placed = True; break
                if placed: break
                if sh["y"] + rot[1] <= H_:
                    sh["shelves"].append(dict(y=sh["y"], h=rot[1], x=rot[0])); pos.append((si, 0, sh["y"], rot[0], rot[1], lab)); sh["y"] += rot[1]; placed = True; break
            if placed: break
        if not placed:
            r = rot if rot[0] <= W_ and rot[1] <= H_ else None
            r = (w, h) if (w <= W_ and h <= H_) else (h, w) if (h <= W_ and w <= H_) else None
            if r is None:
                return None, None
            sheets.append(dict(y=r[1], shelves=[dict(y=0, h=r[1], x=r[0])])); pos.append((len(sheets) - 1, 0, 0, r[0], r[1], lab))
    return len(sheets), pos


def nest_items(ctx):
    """Piezas de plancha: (clave, etiqueta, ancho, alto, espesor, cantidad, masa neta unitaria)."""
    g, P, D, BR, KG, m = ctx.g, ctx.P, ctx.D, ctx.g.BR, ctx.g.KG, ctx.m
    B = g.B
    L = []

    def add(k, lab, w, h, t, q=None):
        p = m.get(k)
        if p:
            L.append((k, lab, w, h, t, q if q is not None else p.qty, p.mass_unit if q is None else p.mass_total / q))
    add("base_plancha", "Plancha base", B + 10, B + 10, g.tb)
    add("collar", "Collar (disco)", g.D_boss + 10, g.D_boss + 10, g.h_boss + 5)
    add("mensula_mejilla", "Mejilla", P["L_ch"], BR["H"] + 5, P["t_ch"])
    add("mensula_oreja_sup", "Oreja sup. ménsula", BR["Win"] - 1, BR["Llug"] + 5, P["t_ch"])
    add("mensula_oreja_inf", "Oreja inf. ménsula", BR["Win"] - 1, BR["Llug"] + 5, BR["spacer"] + P["t_ch"] + 2)
    add("orejas", "Oreja de izaje", 2 * P["R_ear"] + 10, P["h_ear"] + P["R_ear"] + 10, P["t_ear"])
    add("bancada", "Bancada", P["w_bed"] + 10, KG["L_bed"] + 10, P["t_bed"] + 5)
    add("mesa_plancha_sup", "Mesa: plancha superior", 2 * g.prIn + 5, 2 * g.prIn + 5, g.tt)
    add("mesa_plancha_inf", "Mesa: plancha inferior", 2 * g.prIn + 5, 2 * g.prIn + 5, g.tbo + 3)
    add("mesa_anillo_sup", "Anillo sup. (segm. 90°)", g.Rt + 10, g.Rt + 10, g.tpr + 3, 4)
    add("mesa_anillo_inf", "Anillo inf. (segm. 90°)", g.Rt + 10, g.Rt + 10, g.tpr + 3, 4)
    for p in m.parts:
        if p.key.startswith("mesa_nervio"):
            bb = p.solid.vals()[0].BoundingBox()
            L.append((p.key, p.name, max(bb.xlen, bb.ylen) + 4, g.hw + 4, P["t_rib"], p.qty, p.mass_unit))
    add("patin", "Patín (bloque)", KG["L_s"] + 10, P["w_s"] + KG["inset"] + 10, max(g.z_shoe, g.zc + P["dog_h"] / 2 + 10) - (g.zT0 + 1) + 10)
    add("tapa_ret", "Tapa retenedora", g.cap_D + 5, g.cap_D + 5, g.cap_t + 2)
    add("tapa_insp", "Tapa de inspección", g.cb_D + 3, g.cb_D + 3, g.cb_t + 2)
    if g.opt:
        env = (g.Ro - g.Ri * math.cos(math.radians(180.0 / g.n_sec)) + 10, 2 * g.Ro * math.sin(math.radians(180.0 / g.n_sec)) + 10)
        for k in ("int_disco_base", "int_disco_mesa", "int_cara", "int_bronce", "int_uhmw"):
            p = m.get(k)
            if p:
                t = p.solid.vals()[0].BoundingBox().zlen
                L.append((k, p.name, env[0], env[1], t + 1, p.qty, p.mass_unit))
    return L


@gen
def sheet_cortes(ctx):
    c = Gen(ctx, 10, "LISTA DE CORTES DE PLANCHA (NESTING SIMPLE) Y APROVECHAMIENTO")
    s = c.s
    R = c.R["main"]
    w = R[2] - R[0]
    items = nest_items(ctx)
    groups = {}
    for it in items:
        groups.setdefault(round(it[4], 1), []).append(it)
    rows, nests = [], []
    tot_buy = tot_net = 0.0
    for t in sorted(groups):
        its = groups[t]
        rects = [(a[2], a[3], f"{ctx.code(a[0]).replace(CODE + '-', '')}") for a in its for _ in range(int(a[5]))]
        best = None
        for (SW, SH) in STOCK:
            n, pos = shelf_pack(rects, SW, SH)
            if n is None:
                continue
            area = n * SW * SH
            if best is None or area < best[0]:
                best = (area, n, SW, SH, pos)
        net = sum(a[6] * a[5] for a in its)
        if best is None:
            rows.append([fm(t, 1), ", ".join(a[1] for a in its), "no cabe en plancha comercial: A DEFINIR (plancha especial)", "—", "—", f(net, 0), "—"])
            continue
        area, n, SW, SH, pos = best
        buy = n * SW * SH * t * RHO
        tot_buy += buy; tot_net += net
        rows.append([fm(t, 1), "; ".join(f"{a[1]} ×{a[5]} ({fm(a[2], 0)}×{fm(a[3], 0)})" for a in its), f"{SW}×{SH}", str(n), f(buy, 0), f(net, 0), f(net / buy * 100, 1) + " %"])
        nests.append((t, SW, SH, n, pos))
    rows.append(["", "TOTAL (planchas)", "", "", f(tot_buy, 0), f(tot_net, 0), f(tot_net / max(tot_buy, 1) * 100, 1) + " %"])
    y, _ = s.table(R[0], R[3], [("Espesor [mm]", 0.06 * w, "R"), ("Piezas (cant., rectángulo envolvente)", 0.47 * w, "L"), ("Plancha comercial [mm]", 0.12 * w, "C"), ("N° planchas", 0.07 * w, "C"),
                                ("Masa comprada [kg]", 0.10 * w, "R"), ("Masa neta [kg]", 0.09 * w, "R"), ("Aprovech.", 0.09 * w, "R")], rows, h=T_S, title="PLANCHAS: NESTING POR ESTANTES SOBRE PLANCHAS COMERCIALES (rectángulos envolventes; los discos y anillos se anidan como cuadrados)", bold_rows=(len(rows) - 1,))
    # esquema de la primera plancha de cada grupo (hasta 6)
    y -= 10
    cw = (w - 10) / 3
    for i, (t, SW, SH, n, pos) in enumerate(nests[:6]):
        col, row = i % 3, i // 3
        bx, by = R[0] + col * (cw + 5), y - row * 100
        sc = min((cw - 10) / SH, 80 / SW) if SH > SW else min((cw - 10) / SW, 80 / SH)
        Wd, Hd = SW * sc, SH * sc
        s.text(f"e = {fm(t, 1)} mm: plancha {SW}×{SH} (1.ª de {n})", (bx, by), T_N, "TOP_LEFT", bold=True)
        s.rect(bx, by - 8 - Hd, bx + Wd, by - 8, "VIS")
        for (si, px, py, pw, ph, lab) in pos:
            if si == 0:
                s.rect(bx + px * sc, by - 8 - (py + ph) * sc, bx + (px + pw) * sc, by - 8 - py * sc, "FINA")
    s.notes_block(R[0], R[1] + 24, "NOTAS", ["Nesting orientativo por estantes con rectángulos envolventes (sin kerf ni sobremetal adicional al de la tabla de partida); el fabricante optimiza con su software de anidado.",
                                              "Pletinas y barras (marco, almas, barras de topes) se compran en largos comerciales de 6 m: ver tabla de partida en el despiece."], h=T_N, width=w)
    return c.h


@gen
def sheet_supuestos(ctx):
    c = Gen(ctx, 9, "SUPUESTOS DEL DIBUJANTE Y BRECHAS CON EL CÁLCULO (GEN-009)")
    R = c.R["main"]
    w = R[2] - R[0]
    rows = [[x["id"], x["tema"], x["valor"], x["motivo"]] for x in ctx.sup]
    out, last, y = c.table_pages([("Id", 0.05 * w, "L"), ("Tema", 0.2 * w, "L"), ("Valor adoptado", 0.38 * w, "L"), ("Motivo", 0.37 * w, "L")], rows, "SUPUESTOS DEL DIBUJANTE (PROVISORIO) Y DECISIONES ADOPTADAS (ADOPTADO)", "SUPUESTOS Y BRECHAS", 9)
    rows2 = [[x["id"], x["tema"], x["desc"], x["decision"]] for x in ctx.gaps]
    y2, left = last.s.table(R[0], y - 8, [("Id", 0.05 * w, "L"), ("Tema", 0.2 * w, "L"), ("Descripción", 0.40 * w, "L"), ("Decisión requerida", 0.35 * w, "L")], rows2, h=T_S, ymin=R[1] + 3, title="BRECHAS CON EL CÁLCULO Y DECISIONES REQUERIDAS")
    pend = left
    n = 0
    while pend:
        n += 1
        g2 = Gen(ctx, 20 + n, f"BRECHAS CON EL CÁLCULO (CONTINUACIÓN {n})")
        R2 = g2.R["main"]
        _, pend = g2.s.table(R2[0], R2[3], [("Id", 0.05 * w, "L"), ("Tema", 0.2 * w, "L"), ("Descripción", 0.40 * w, "L"), ("Decisión requerida", 0.35 * w, "L")], pend, h=T_S, ymin=R2[1] + 3, title="BRECHAS (continuación)")
        out.append(g2.h)
    return out


@gen
def sheet_verificacion(ctx):
    c = Gen(ctx, 11, "LISTA DE VERIFICACIÓN DEL REVISOR")
    R = c.R["main"]
    w = R[2] - R[0]
    ver = ["Cotas de cada lámina verificadas contra el sólido 3D (chequeo_cotas.csv): 0 fallas.", "Masa 3D frente al núcleo ≤ 0,5 % y 0 interferencias (informe_paquete.md).",
           "Cada pieza del despiece tiene plano o referencia a catálogo; cada código del despiece aparece con globo en un plano de conjunto/subconjunto.",
           "Cada junta soldada J## tiene símbolo ISO 2553 y fila en la tabla de soldaduras (GEN-007).", "Cada plano de pieza trae material, dimensión de partida y masa.",
           "Tamaños de filete: confirmar los marcados «mínimo AWS, a confirmar» y el caso w_web > t − 2 (AISC J2.2b).", "Materiales «SEGÚN CÁLCULO Fy ≥ …, A DEFINIR POR EL FABRICANTE»: aprobar o fijar el grado.",
           "Torques propuestos (GEN-008): confirmar o reemplazar por cálculo VDI 2230.", "Pintura (sistema y EPS), WPS/PQR, grillete, lista de compras: A DEFINIR.", "Supuestos S## y brechas B-## (GEN-009): aceptar o corregir antes de aprobar.",
           "Texto negro sobre fondo blanco; letra ≥ 3,5 mm en el plot A1 (tablas densas 3,0 mm; mínimo absoluto 2,5 mm).", "Estado EMITIDO PARA REVISIÓN en todas las láminas hasta su aprobación; completar DIBUJÓ/REVISÓ/APROBÓ."]
    rows = [[str(i + 1), v, "", ""] for i, v in enumerate(ver)]
    c.s.table(R[0], R[3], [("N°", 0.04 * w, "C"), ("Verificación", 0.74 * w, "L"), ("Cumple (sí/no)", 0.10 * w, "C"), ("Observación", 0.12 * w, "L")], rows, h=T_S, title="VERIFICACIONES TRANSVERSALES DEL JUEGO DE PLANOS")
    return c.h
