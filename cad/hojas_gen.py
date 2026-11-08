"""Láminas generales: notas y normas con índice, programa de soldaduras, inspección, tolerancias y ajustes, materiales, tratamientos, torques y compras,
supuestos y brechas, lista de cortes (nesting) y lista de verificación del revisor."""
import math, sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_util import *
import lista
import propuestas

PLAN_GEN = []


def gen(fn):
    PLAN_GEN.append(fn.__name__)
    return fn


class Gen(Pieza):
    def __init__(self, ctx, num, titulo, fmt="A1"):
        self.ctx = ctx
        fmt = getattr(ctx, "gen_fmt", None) or fmt
        h = Hoja(ctx, f"GEN-{num:03d}", titulo, "S/E", fmt=fmt, material="No aplica (lámina de información)", masa="—", trat="—", serie="GEN")
        self.h = h
        self.s = h.begin()
        R = dict(h.R)
        R["main"] = (R["all"][0], R["all"][1], R["left"][2], R["left"][3])      # área libre a la izquierda del cajetín, a toda la altura
        self.R = R
        h.zone = R["main"]
        self.specs, self.blocks, self.named, self.scales, self.vlist, self.post = [], [], {}, [], [], []
        self.dims_n0 = len(vistas.COTAS.rows)
        self.iso_keys = None
        self.iso_fill = False

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


def losa_txt(ctx):
    """Presión admisible sobre la losa/mats según la verificación del núcleo (valor con unidad, sin nombre de parámetro)."""
    v = ctx.g.fila("Presión sobre losa")
    return f"{fm(v['cap'], 0)} {v['unidad']}" if v else "la admisible del cálculo"


def notas_generales(ctx):
    """Notas generales del juego: se escriben UNA sola vez, en GEN-001; las demás láminas remiten a ellas (control de notas duplicadas)."""
    g = ctx.g
    return [ADVERTENCIA,
            "Estado de todas las láminas: EMITIDO PARA REVISIÓN hasta su aprobación; los campos DIBUJÓ/REVISÓ/APROBÓ del cajetín quedan A DEFINIR (firmas).",
            "Estas notas valen para todas las láminas del juego, que remiten a ellas («NOTAS GENERALES: VER GEN-001») y solo traen sus notas propias. Notas específicas por tema: GEN-003 (inspección), GEN-004 (tolerancias y ajustes), "
            "GEN-005 (materiales), GEN-006 (tratamientos, pintura y zonas sin pintura), GEN-007 y GEN-012 (soldaduras y WPS), GEN-008 (tornillería, torques y compras).",
            f"Sin anclaje ni análisis de viento (decisión del mandante): el equipo apoya sobre losa/mats con presión sobre la losa ≤ {losa_txt(ctx)} (admisible del cálculo; la verificación de la losa es de terceros). "
            + NOTA_VIENTO,
            "Fuente única: todos los valores salen del JSON de diseño del núcleo de cálculo (exportado por la herramienta TT300-C); si el JSON cambia, regenerar el juego completo.",
            "Unidades: mm, kg, MPa, grados. Cotas en mm salvo indicación. No medir sobre el plano. Método de proyección E (ISO 5456-2).",
            "Tolerancias generales ISO 2768-mK (lineales y angulares, tabla en GEN-004); piezas soldadas ISO 13920-BF; rugosidad no indicada Ra 12,5 (ISO 1302 / ISO 21920-1).",
            "Soldadura: ISO 2553 (símbolos), ISO 5817 (calidad, nivel en cada símbolo), ISO 4063 (procesos 111/135/136" + (", 141 solo en J21" if g.opt == 2 else "") + "), AWS D1.1 (calificación, precalentamiento, END). WPS pre-calificados PROPUESTOS en GEN-012 (a calificar/confirmar por el fabricante).",
            "Materiales y elementos de unión con certificado EN 10204 3.1 (incluidos pernos 10.9 y arandelas); trazabilidad por colada; punzonar el código de la pieza y la colada en zona no crítica.",
            "Aristas vivas rotas 1×45° (ISO 13715) salvo indicación. Rosca métrica ISO 261 / ISO 262 / ISO 724; tornillería ISO 4762 / ISO 10642, clase 10.9 (ISO 898-1); agujeros pasantes ISO 273.",
            "Taller sin torno vertical: gran diámetro por oxicorte/plasma (ISO 9013), soldadura y mandrinadora; ajustes largos H7 en mandrinadora.",
            propuestas.pintura_txt() + " Zonas sin pintura: lista única en GEN-006.",
            "Códigos de pieza: tienen el formato TT300C-SSS-NNN-C, o TT300C-SSS-NNN-n-C con sufijo de geometría; las piezas sin lámina propia se dibujan en la lámina indicada en la columna «Plano» del despiece (CON-002). "
            "Un código designa una sola geometría: la pieza que cambia entre variantes, o los sectores de geometría distinta de un mismo juego, llevan sufijo -n (mapa de códigos por geometría en esta lámina; control automático sobre la geometría real del modelo 3D)."]


def normas(ctx):
    """Normas citadas en el juego, filtradas por lo que la variante contiene (A-19, A-34)."""
    g = ctx.g
    N = [("ISO 128 (-20, -30, -40, -50)", "Dibujo técnico: líneas, vistas, cortes y achurado"), ("ISO 129-1", "Acotado"), ("ISO 1101 / ISO 5459", "Tolerancias geométricas / datums"),
         ("ISO 1302 / ISO 21920-1", "Indicación de la textura superficial"), ("ISO 2553 / ISO 4063", "Símbolos de soldadura / procesos"), ("ISO 5817 / ISO 9692-1", "Niveles de calidad / preparación de juntas"),
         ("ISO 5457 / ISO 7200 / ISO 5456-2", "Formatos, cajetín, método de proyección"), ("ISO 3098", "Escritura"), ("ISO 286-1/-2", "Sistema de tolerancias y ajustes ISO"),
         ("ISO 2768-1 / ISO 13920", "Tolerancias generales / tolerancias de construcciones soldadas"), ("ISO 13715", "Aristas de forma indefinida"), ("ISO 6410-1", "Representación de roscas"),
         ("ISO 9013", "Corte térmico: tolerancias"), ("ISO 261 / 262 / 724 / 273", "Roscas métricas / agujeros pasantes"), ("ISO 4762 / ISO 10642 / ISO 898-1", "Tornillos / propiedades mecánicas"),
         ("VDI 2230", "Uniones atornilladas (torques propuestos)"), ("AWS D1.1-2020", "Soldadura de acero estructural (T5.8 filete mínimo, T5.11 precalentamiento, cl. 8 END)"),
         ("AWS A5.1 / A5.18" + (" / A5.9" if g.opt == 2 else ""), "Metales de aporte"), ("ISO 9606-1 / ISO 17637", "Calificación de soldadores / inspección visual"),
         ("AISC 360-22", "Especificación (J2.2b filete máximo, D5.2 orejas)"), ("ASME BTH-1 Cat. B / ASME B30.26", "Dispositivos de izaje / grilletes"),
         ("EN 10204 3.1", "Certificados de inspección"), ("ASTM A572 Gr.50, A36 (ref.), A578, EN 10164", "Aceros estructurales, UT de planchas, propiedades en espesor"),
         ("EN 10083-3 (34CrNiMo6+QT) / EN 10228-3", "Aceros bonificados (pasadores, uña) / UT de forjas"), ("ISO 15787", "Indicación de tratamientos térmicos en los planos (pasadores)"), ("DIN 71412" if g.n_greaser and g.opt in (1, 3) else "", "Graseras"),
         ("ISO 12944-5 / ISO 8501-1 / ISO 8503 / ISO 19840 / ISO 4624", "Protección anticorrosiva (C4 alta propuesto, GEN-006), preparación, EPS y adherencia")]
    if g.opt in (1, 2):
        N.append(("ASTM A240", "Acero inoxidable (discos de la interfaz)"))
    if g.opt == 1:
        N.append(("ASTM G98", "Ensayo de excoriación (diferencia de dureza entre discos)"))
    if g.opt == 2:
        N.append(("ASTM D4020", "UHMW-PE (lámina de la interfaz)"))
    if g.opt == 3:
        N.append(("ASTM B148 / B584 / A564 (17-4PH)", "Bronce de la placa / acero del disco duro"))
    if g.wood:
        N.append(("NCh1198", "Madera (cubierta)"))
    return [list(n) for n in N if n[0]]


@gen
def sheet_notas(ctx):
    g = ctx.g
    c = Gen(ctx, 1, "NOTAS GENERALES, NORMAS APLICABLES E ÍNDICE DE PLANOS")
    s = c.s
    R = c.R["main"]
    notas = notas_generales(ctx)
    ctx.notas_generales = list(notas)
    y = s.notes_block(R[0], R[3], "NOTAS GENERALES DE FABRICACIÓN", notas, h=T_N, width=0.46 * (R[2] - R[0]), numbered=True)
    x2 = R[0] + 0.48 * (R[2] - R[0])
    yn, _ = s.table(x2, R[3], [("Norma", 70, "L"), ("Aplicación", 130, "L")], normas(ctx), h=T_S, title="NORMAS APLICABLES")
    # mapa de códigos por geometría (H-04: un código = una geometría; N-07: láminas de características emitidas)
    import modelo3d_tt300c as M3
    var = M3.variante_de(g)
    en_juego = {p.code_suf(t["suf"] if p.tipos else p.suf).replace(CODE + "-", "").rsplit("-", 1)[0] for p in ctx.m.parts for t in (p.tipos or [None])} | \
               {p.code.replace(CODE + "-", "").rsplit("-", 1)[0] for p in ctx.m.parts}
    rows = []
    por_num = {}
    for k, (n, nm, vv) in M3.INT_CODIGOS.items():
        key = k.split("/")[0]
        e = por_num.setdefault(n, dict(nm=nm, vv=vv, cl=[]))
        cl = M3.VAR_CODIGOS.get(key)
        if cl:
            o = 0
            for (vs, desc, nt) in cl:
                if M3._num_clase(key, vs) != n:
                    continue
                if not any(c_[0] == vs for c_ in e["cl"]):
                    e["cl"].append((vs, desc, o + 1, o + nt))
                o += nt
    def cods(base, cl):
        return " · ".join(f"-{a}" + (f"…-{b}" if b > a else "") + f" {'/'.join(vs)}: {desc}" for vs, desc, a, b in cl)
    for n, e in sorted(por_num.items()):
        base = f"INT-{n:03d}"
        actual = sorted({c_ for c_ in en_juego if c_.startswith(base)})
        rows.append([base, e["nm"].split(" (")[0] + (": " + cods(base, e["cl"]) if e["cl"] else ""), e["vv"], ", ".join(a_[4:] for a_ in actual) if actual else "—"])
    rows += [["INT-101", M3.INT_LAMINAS[101] + " (lámina de características)", "A, AF2, C1, C2, C3", "sí" if (g.opt in (1, 3) and g.h_gr > 0) else "—"],
             ["INT-102", M3.INT_LAMINAS[102] + " (lámina de características)", "C1, C2, C3", "sí" if g.opt == 3 else "—"]]
    vt = {103: "A, AF2", 104: "C1, C2, C3", 105: "C1, C2, C3"}
    for k_, n_ in sorted(M3.LAMINA_TIPOS.items(), key=lambda t: t[1]):
        if n_ in vt or any(getattr(p, "hoja_tipos", False) and p.key == k_ for p in ctx.m.parts):
            rows.append([f"INT-{n_:03d}", M3.INT_LAMINAS[n_] + " (lámina de tipos)", vt.get(n_, "—"), "sí" if any(getattr(p, "hoja_tipos", False) and p.key == k_ for p in ctx.m.parts) else "—"])
    if not g.opt:
        # juego sin interfaz: los códigos INT no se usan; una fila los resume (el mapa completo va en los juegos con interfaz)
        rows = [["INT-001…014, INT-101…107", "Piezas y láminas de la interfaz (sectores, topes, tornillos, graseras, UHMW, bronce, disco duro): no se emiten en este juego; "
                 "mapa completo con sus sufijos por variante en GEN-001 de las variantes A, AF2, B y C1…C3", "A, AF2, B, C1…C3", "—"]]
    for key, cl in M3.VAR_CODIGOS.items():
        if key.startswith("int_"):
            continue
        p0 = ctx.m.get(key)
        if p0 is None:
            continue
        base = f"{p0.sub}-{p0.num:03d}"
        o, cl2 = 0, []
        for (vs, desc, nt) in cl:
            cl2.append((vs, desc, o + 1, o + nt))
            o += nt
        rows.append([base, f"{p0.name}: " + cods(base, cl2), "todas", p0.code.replace(CODE + "-", "").rsplit("-", 1)[0][4:]])
    yn, _ = s.table(x2, yn - 6, [("Código", 22, "L"), ("Pieza; sufijo -n, variantes y geometría", 138, "L"), ("Variantes", 22, "L"), ("En el juego", 18, "L")], rows, h=T_S,
                    title="MAPA DE CÓDIGOS POR GEOMETRÍA (un código = una geometría; sufijo -n por variante o por tipo de sector)")
    c.h.indice_pos = (R[0], y - 10, R[2] - R[0], R[1], yn - 10)      # columna 1 bajo las notas; columna 2 bajo las normas y el mapa de códigos
    return c.h


def tabla_indice(ctx, h, hojas):
    """Índice de planos en GEN-001 (se llama al final, con todas las láminas)."""
    s = h.s
    x, y, w, ymin, yR = h.indice_pos
    suf = f" — VARIANTE {ctx.g.variante}"
    rows = [[hh.plano.replace(CODE + "-", "").replace("-" + REV, ""), hh.titulo[:-len(suf)] if hh.titulo.endswith(suf) else hh.titulo, hh.fmt, hh.escala, REV] for hh in hojas]
    wc = (w - 6) / 2
    sc = wc / 190.0
    cols = [("Plano", 30 * sc, "L"), ("Título", 105 * sc, "L"), ("Fmt", 12 * sc, "C"), ("Escala", 30 * sc, "L"), ("Rev", 13 * sc, "C")]
    tit = f"ÍNDICE DE PLANOS — VARIANTE {ctx.g.variante} (el título de cada lámina termina en «{suf.strip(' —')}»)"
    from draw import Sheet as _Sh
    hh_ = T_MIN
    for h_try in (T_S, 2.75, T_MIN):            # letra de tabla densa; mínimo absoluto 2,5 mm si el juego tiene muchas láminas
        sc_ = _Sh(h.fmt)
        _, lft = sc_.table(x, y, cols, rows, h=h_try, ymin=ymin + 12, title=tit)
        _, lft2 = sc_.table(x + wc + 6, yR, cols, lft, h=h_try, ymin=ymin + 12) if lft else (0, [])
        if not lft2:
            hh_ = h_try
            break
    y1, l1 = s.table(x, y, cols, rows, h=hh_, ymin=ymin + 12, title=tit)
    y2, l2 = s.table(x + wc + 6, yR, cols, l1, h=hh_, ymin=ymin + 12) if l1 else (y1, [])
    l1 = []
    # números de lámina no emitidos en este juego (reservados para otras variantes o anulados) y hojas de continuación
    usados = {}
    for hh in hojas:
        t = hh.plano.replace(CODE + "-", "").replace("-" + REV, "")
        sr, nn = t.split("-")[0], int(t.split("-")[1])
        usados.setdefault(sr, set()).add(nn)
    res = []
    for sr in ("CON", "GEN"):
        u = usados.get(sr, set())
        lim = 23 if sr == "CON" else 13
        falt = [n for n in range(1, lim + 1) if n not in u]
        if falt:
            res.append(f"{sr}-" + ", ".join(f"{n:03d}" for n in falt))
    txt = "Números no emitidos en este juego (reservados o anulados): " + ("; ".join(res) if res else "ninguno") + ". CON-030 y siguientes: hojas de continuación del despiece CON-002; GEN-021 y siguientes: continuación de GEN-009."
    s.notes_block(x, min(y1, y2) - 4, "NUMERACIÓN", [txt], h=T_N, width=w)
    return bool(l1 or l2)


@gen
def sheet_soldaduras_global(ctx):
    c = Gen(ctx, 7, "PROGRAMA DE SOLDADURAS: TABLA GLOBAL DE JUNTAS")
    R = c.R["main"]
    sc = (R[2] - R[0]) / sum(w for _, w, _ in WELD_COLS)
    cols = [(t, w * sc, a) for t, w, a in WELD_COLS]
    out, last, y = c.table_pages(cols, weld_rows(ctx), "PROGRAMA DE SOLDADURAS (Junta N°, piezas, tipo, preparación, garganta a, cateto z, longitud, pasadas, proceso, aporte, WPS, END)", "PROGRAMA DE SOLDADURAS", 7)
    last.s.notes_block(R[0], y - 6, "NOTAS", ["Tamaños: los calculados en la memoria; donde el núcleo no fija el tamaño se adopta el mínimo AWS D1.1 Tabla 5.8 por la parte más gruesa y se rotula «mínimo AWS, a confirmar».",
                                              "a = 0,707·z (filete de lados iguales). Nº de pasadas: orientativo (WPS define). Aporte con resistencia a tracción ≥ %s MPa (E70xx)." % f(ctx.P["FEXX"]),
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


# ISO 2768-1:1989, Tabla 1 (desviaciones admisibles para cotas lineales, excepto chaflanes): rango -> (f, m, c, v) [mm]
ISO2768_LINEAL = [("0,5 a 3", ("0,05", "0,1", "0,2", "—")), ("más de 3 a 6", ("0,05", "0,1", "0,3", "0,5")), ("más de 6 a 30", ("0,1", "0,2", "0,5", "1")),
                  ("más de 30 a 120", ("0,15", "0,3", "0,8", "1,5")), ("más de 120 a 400", ("0,2", "0,5", "1,2", "2,5")), ("más de 400 a 1.000", ("0,3", "0,8", "2", "4")),
                  ("más de 1.000 a 2.000", ("0,5", "1,2", "3", "6")), ("más de 2.000 a 4.000", ("—", "2", "4", "8"))]


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
        rows.append([desc, f"Ø{fm(d, 0)}", ho, sh_, t["h_lim"], t["s_lim"], t["juego"] + " µm", t["tipo"], app])
    rows.append(["Collar en rebaje (del cálculo)", f"Ø{f(g.D_boss)}", "—", "—", f"Ø{fm(g.Drb, 1)}", f"Ø{fm(g.D_boss, 1)}", f"{fm(g.c_boss_r, 0)} mm (radial)", "con juego", f"holgura radial {fm(g.c_boss_r, 0)} mm y axial {fm(g.c_boss_a, 0)} mm (del cálculo)"])
    y, _ = s.table(R[0], R[3], [("Ajuste", 0.17 * w, "L"), ("Nom.", 0.05 * w, "C"), ("Aguj.", 0.05 * w, "C"), ("Eje", 0.05 * w, "C"), ("Límites agujero [mm]", 0.11 * w, "C"), ("Límites eje [mm]", 0.11 * w, "C"),
                                      ("Juego mín / máx", 0.10 * w, "C"), ("Tipo", 0.08 * w, "L"), ("Aplicación", 0.28 * w, "L")], rows, h=T_S, title="TABLA DE AJUSTES ISO 286-1/-2 (límites calculados)")
    gd = [["Planitud", "Cara de apoyo de la base (Ø%s)" % f(P["D_top"] + 20), "0,20", "—"], ["Planitud", "Cara inferior de la mesa", "0,20", "—"], ["Perpendicularidad", "Agujero Ø%s H7 respecto de la cara de apoyo" % f(P["D_piv"]), "0,05", "A"],
          ["Coaxialidad", "Collar – agujero de la base", "Ø0,05", "A"], ["Coaxialidad", "Ojales de ménsula (Ø%s H9)" % f(P["d_pp"]), "Ø0,10", "A"], ["Paralelismo", "Ranura T de la bancada", "0,10", "A"],
          ["Posición", "PCD de %d pasadores Ø%s" % (g.N_pin, f(g.d_pin)), "Ø0,3", "A"], ["Coaxialidad", "Agujeros de pasadores del anillo superior respecto del eje común de cada par superior–inferior (mandrinado en línea; CON-009 n.° 5)", "Ø0,05", "eje común"], ["Planitud", "Cara de empuje de la uña", "0,05", "—"],
          ["Cilindricidad", "Pasadores y pivote", "0,02", "—"]]
    y2, _ = s.table(R[0], y - 8, [("Característica (ISO 1101)", 0.16 * w, "L"), ("Elemento", 0.40 * w, "L"), ("Tolerancia [mm]", 0.10 * w, "C"), ("Datum", 0.07 * w, "C")], gd, h=T_S, title="TOLERANCIAS GEOMÉTRICAS PRINCIPALES")
    gen_t = [[r] + [("±" + v) if v != "—" else v for v in vals] for r, vals in ISO2768_LINEAL]
    s.table(R[0], y2 - 8, [("Rango [mm]", 0.12 * w, "L"), ("f (fina)", 0.08 * w, "C"), ("m (media)", 0.08 * w, "C"), ("c (basta)", 0.08 * w, "C"), ("v (muy basta)", 0.08 * w, "C")], gen_t, h=T_S,
            title="ISO 2768-1, TABLA 1: DESVIACIONES ADMISIBLES DE COTAS LINEALES [mm] (se aplica «m»; piezas soldadas ISO 13920-BF)")
    return c.h


@gen
def sheet_materiales(ctx):
    c = Gen(ctx, 5, "MATERIALES Y CERTIFICADOS")
    R = c.R["main"]
    w = R[2] - R[0]
    rows = []
    for p in ctx.m.parts:
        rows.append([p.code.replace(CODE + "-", ""), p.name, str(p.qty), p.material, p.cert, "Comercial" if p.comercial else "PROPUESTO por Fy del cálculo", p.tratamiento if p.tratamiento != "—" else "—"])
    out, last, y = c.table_pages([("Código", 0.07 * w, "L"), ("Pieza", 0.18 * w, "L"), ("Cant", 0.04 * w, "C"), ("Material (norma, grado, Fy del cálculo)", 0.33 * w, "L"), ("Certificado", 0.14 * w, "L"),
                                  ("Estado del grado", 0.09 * w, "L"), ("Tratamiento", 0.15 * w, "L")], rows, "MATERIALES POR PIEZA (certificado EN 10204 3.1; donde el cálculo solo fija Fy el grado es PROPUESTO por Fy, a confirmar)", "MATERIALES Y CERTIFICADOS", 5)

    g, P = ctx.g, ctx.P
    gr = [["Plancha, pletinas y barras soldadas (Fy = %s MPa)" % f(P["Fy"]), propuestas.grado(P["Fy"], 20, "plancha")], ["Pivote (Ø%s)" % f(P["D_piv"]), propuestas.grado(P["Fy_piv"], P["D_piv"], "barra")],
          ["Pasadores de articulación (Ø%s)" % f(P["d_pp"]), propuestas.grado(P["Fy_pp"], P["d_pp"], "barra")], ["Patín (bloque de %s mm)" % fm(g.Hs, 0), propuestas.grado(P["Fy_shoe"], g.Hs, "barra")],
          ["Pasadores de empuje (Ø%s)" % f(g.d_pin), propuestas.grado(P["Fy_pin"], g.d_pin, "barra")], ["Uña (forja, %s mm)" % fm(P["dog_b"], 0), propuestas.grado(P["Fy_dog"], P["dog_b"], "barra")]]
    last.s.table(R[0], y - 8, [("Elemento (parámetro del cálculo)", 0.34 * w, "L"), ("Grado comercial más económico que cumple", 0.66 * w, "L")], gr, h=T_S,
                 title="GRADOS PROPUESTOS POR Fy DEL CÁLCULO (" + propuestas.ROTULO_GRADO + "); el cálculo solo fija Fy")
    return out


@gen
def sheet_tratamientos(ctx):
    g, P = ctx.g, ctx.P
    c = Gen(ctx, 6, "TRATAMIENTOS TÉRMICOS Y SUPERFICIALES, PINTURA")
    R = c.R["main"]
    w = R[2] - R[0]
    rows = [["Base soldada, mesa soldada", "Alivio de tensiones 590–620 °C (2 h/25 mm), enfriamiento lento; antes del mecanizado final", "Fabricante (registro de horno)"],
            ["Pasadores de empuje (MES-012)", f"Bonificado + temple por inducción de la franja de contacto ≥ 55 HRC (límite elástico superficial supuesto en el cálculo: {f(P['Fy_surf'])} MPa), profundidad ≥ {fm(g.z_hard, 1)} mm", "Dureza 10 % por lote; macrografía"],
            ["Uña de empuje (ACC-004)", f"34CrNiMo6+QT Re ≥ {f(P['Fy_dog'])} MPa (probeta de la forja); temple por inducción de la cara ≥ 55 HRC, prof. ≥ {fm(g.z_hard, 1)} mm; revenido; alivio de borde {fm(RELIEF, 0)} mm", "Dureza 100 %; MT cara"],
            ["Pivote (PIV-001)", f"Bonificado (QT) según Fy ≥ {f(P['Fy_piv'])} MPa: {propuestas.grado_corto(P['Fy_piv'], P['D_piv'], 'barra')} ({propuestas.ROTULO_GRADO})", "Certificado 3.1"],
            ["Pasadores de articulación (ACC-005)", f"Bonificado según Fy ≥ {f(P['Fy_pp'])} MPa: {propuestas.grado_corto(P['Fy_pp'], P['d_pp'], 'barra')} ({propuestas.ROTULO_GRADO}); 28–34 HRC de referencia", "Certificado 3.1"],
            *([["Discos de interfaz inoxidables", "Decapado y pasivado; rectificado/lapeado de la cara deslizante Ra 0,4", "Rugosidad 100 % de caras"]] if g.opt in (1, 2) else []),
            *([["Disco duro 17-4PH", f"Condición H1025 (endurecido por precipitación); ≥ {f(P['HB_cara'])} HB, Fy ≥ {f(P['Fy_cara'])} MPa", "Dureza 100 %"]] if g.opt == 3 and g.conf != 2 else []),
            *([["Bronce con tapones de grafito", f"≥ {f(P['HB_bz'])} HB, Fy ≥ {f(P['Fy_bz'])} MPa; tapones encastrados al {fm((g.IG.get('tapon_prof_frac') or 0.7) * 100, 0)} % del espesor", "Certificado del proveedor"]] if g.opt == 3 else []),
            *([["UHMW-PE", "Sin tratamiento ni pintura; UHMW-PE PE1000 (ASTM D4020), natural; certificado del proveedor", "Certificado del proveedor"]] if g.opt == 2 else []),
            ["Estructura de acero (base, mesa, soldaduras)", pintura(ctx), "EPS (ISO 19840) y adherencia (ISO 4624): 1 medición por 10 m²"],
            ["Zonas sin pintura (lista única del juego)", propuestas.zonas_sin_pintura(ctx), "VT"],
            ["Tornillería", "Pernos 10.9 con recubrimiento zincado/dacromet (tipo exigido; marca/modelo en GEN-008)", "Certificado del lote"]]
    out, last, y = c.table_pages([("Elemento", 0.22 * w, "L"), ("Tratamiento / especificación", 0.58 * w, "L"), ("Control", 0.20 * w, "L")], rows, "TRATAMIENTOS TÉRMICOS Y SUPERFICIALES", "TRATAMIENTOS", 6)
    prow = [[a, b_, cc] for a, b_, cc in propuestas.SISTEMA_PINTURA]
    last.s.table(R[0], y - 8, [("Capa", 0.18 * w, "L"), ("Producto / especificación", 0.64 * w, "L"), ("EPS", 0.18 * w, "R")], prow, h=T_S, bold_rows=(len(prow) - 1,),
                 title="SISTEMA DE PINTURA — " + propuestas.ROTULO_PINT + " (ISO 12944 C4 alta, epoxi-zinc 60 + epoxi 120 + PU 60 µm)")
    return out


# --------------------------------------------------------------------------- torques y compras
AS_M = {6: 20.1, 8: 36.6, 10: 58.0, 12: 84.3, 16: 157.0, 20: 245.0}


def torque_rows(ctx):
    g, P = ctx.g, ctx.P
    rows = []
    items = [("Perno ISO 4762 M20×45 cl. 10.9 (retención de pasador)", 20, 10.9, g.N_pin), (f"Tornillo ISO 10642 M10×{g.cap_L:.0f} cl. 10.9 (tapa retenedora)", 10, 10.9, 4), (f"Tornillo ISO 10642 M{fm(g.insp_d, 0)}×{g.insp_L} cl. 10.9 (tapa de inspección)", int(g.insp_d), 10.9, 6)]
    if g.opt and g.removable:
        items.append((f"Tornillo ISO 10642 M{fm(P['d_tor'], 0)} cl. 10.9 (posición de sectores; no transmiten carga)", int(P["d_tor"]), 10.9, None))
    for nm, d, cl, n in items:
        As = AS_M.get(d, math.pi / 4 * (0.9 * d) ** 2)
        rp = 940.0 if cl == 10.9 else 640.0
        F = 0.7 * rp * As / 1000.0          # kN, precarga 70 % de Rp0,2·A_s
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
    y = s.notes_block(R[0], y - 5, "NOTA", ["Método simplificado: precarga F = 70 % de Rp0,2·A_s (Rp0,2 mínimo ISO 898-1 clase 10.9 = 940 MPa; la carga de prueba de la clase es 830 MPa), factor de torque K = 0,20 (lubricado con grasa); T = K·F·d. Sin cálculo de la unión (rigidez, asentamiento): PROPUESTA, A CONFIRMAR POR EL CALCULISTA; usar llave dinamométrica calibrada y marca de pintura de control."], h=T_N, width=w)
    rows = propuestas.catalogo_rows(ctx)
    for (d, q, e, cat) in lista.extras(ctx):
        if not d.startswith(("Tornillo ISO 10642 M10", f"Tornillo ISO 10642 M{fm(g.insp_d, 0)}")) and not any(d.split(" (")[0][:18] in r[0] for r in rows):
            rows.append([d + f" (×{q})", e, "—", "marca/modelo A DEFINIR POR CATÁLOGO"])
    s.table(R[0], y - 6, [("Componente (tipo)", 0.20 * w, "L"), ("Características exigidas", 0.46 * w, "L"), ("Certificado / prueba", 0.16 * w, "L"), ("Marca / modelo", 0.18 * w, "L")], rows, h=T_S,
            title="COMPONENTES DE CATÁLOGO: TIPO Y CARACTERÍSTICAS EXIGIDAS (" + ", ".join(r[0].split(" (")[0].split(" DIN")[0].lower() for r in rows[:6]) + "…)")
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
    add("mensula_oreja_sup", "Oreja sup. ménsula", BR["Win"] + lista.SOBRE_MEC, BR["Llug"] + 5, P["t_ch"])
    add("mensula_oreja_inf", "Oreja inf. ménsula", BR["Win"] + lista.SOBRE_MEC, BR["Llug"] + 5, BR["spacer"] + P["t_ch"] + 2)
    add("orejas", "Oreja de izaje", 2 * P["R_ear"] + 10, P["h_ear"] + P["R_ear"] + 10, P["t_ear"])
    add("bancada", "Bancada", P["w_bed"] + 10, KG["L_bed"] + 10, P["t_bed"] + 5)
    add("mesa_plancha_sup", "Mesa: plancha superior", 2 * g.prIn + 5, 2 * g.prIn + 5, g.tt)
    add("mesa_plancha_inf", "Mesa: plancha inferior", 2 * g.prIn + 5, 2 * g.prIn + 5, g.tbo + 3)
    add("mesa_anillo_sup", "Anillo sup. (segm. 90°)", g.Rt + 10, g.Rt + 10, g.tpr + 3, 4)
    add("mesa_anillo_inf", "Anillo inf. (segm. 90°)", g.Rt + 10, g.Rt + 10, g.tpr + 3, 4)
    for p in m.parts:
        if p.key.startswith("mesa_nervio"):
            Lr = lista.rib_len(ctx, p)                   # largo terminado del tramo; partida = terminado + 2 × 2 (misma partida que la lista de cortes)
            L.append((p.key, p.name, Lr + 4, g.hw + 4, P["t_rib"], p.qty, p.mass_unit))
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


KERF = 6.0          # separación entre piezas (corte por plasma/oxicorte) [mm]
BORDE = 10.0        # borde de plancha descartado [mm]
WIDTHS = [(1500, 6000), (2000, 6000), (2440, 12000), (3000, 12000)]
PASO_L = 500.0      # largo de compra en múltiplos de 500 mm (corte a medida por el proveedor)


def strip_pack(rects, W):
    """Empaque por franjas transversales: cada franja ocupa todo el ancho W de la plancha y avanza a lo largo.
    rects: [(w, h, etiqueta)] de piezas (envolvente con sobremetal). Devuelve (largo usado, posiciones, franjas) o None.
    posiciones: (franja, x, y, w, h, etiqueta) con origen en la esquina inferior izquierda (x a lo ancho, y a lo largo)."""
    Wu = W - 2 * BORDE
    items = []
    for (w, h, lab) in rects:
        a, b = max(w, h), min(w, h)
        if a + KERF <= Wu:
            items.append((a, b, lab))
        elif b + KERF <= Wu:
            items.append((b, a, lab))
        else:
            return None
    items.sort(key=lambda r: (-r[1], -r[0]))
    shelves, pos = [], []
    for (w, h, lab) in items:
        for sh in shelves:
            if sh["x"] + w + KERF <= Wu + 1e-6 and h <= sh["h"] + 1e-6:
                pos.append((sh["i"], BORDE + sh["x"], sh["y"], w, h, lab))
                sh["x"] += w + KERF
                sh["n"].append(lab)
                break
        else:
            y = BORDE + sum(s_["h"] + KERF for s_ in shelves)
            sh = dict(i=len(shelves), y=y, h=h, x=w + KERF, n=[lab], w0=w)
            shelves.append(sh)
            pos.append((sh["i"], BORDE, y, w, h, lab))
    L = BORDE + sum(s_["h"] + KERF for s_ in shelves) + BORDE - KERF
    return L, pos, shelves


def plan_espesor(rects):
    """Mejor ancho comercial y partición en planchas de largo de compra (múltiplo de 500 mm, ≤ largo máximo del ancho)."""
    best = None
    smin = max(min(w, h) for (w, h, _) in rects) + 2 * BORDE + KERF
    custom = [(int(math.ceil(smin / 100.0) * 100 + 100 * k), 6000, True) for k in range(6)]
    for (W, Lmax, *cu) in [wl + (False,) for wl in WIDTHS] + custom:
        cu = bool(cu and cu[0])
        if cu and W >= 1500:
            continue
        paso = 100.0 if cu else PASO_L
        r = strip_pack(rects, W)
        if r is None:
            continue
        L, pos, shelves = r
        # partición por franjas en planchas de largo ≤ Lmax
        plates, cur, y0 = [], [], BORDE
        for sh in shelves:
            if cur and (sh["y"] + sh["h"] + BORDE - y0 + BORDE) > Lmax:
                plates.append((cur, y0))
                cur, y0 = [], sh["y"]
            cur.append(sh)
        plates.append((cur, y0))
        out = []
        area = 0.0
        for k, (shs, y0) in enumerate(plates):
            ids = {s_["i"] for s_ in shs}
            Lu = max(s_["y"] + s_["h"] for s_ in shs) - y0 + 2 * BORDE
            Lb = min(Lmax, math.ceil(Lu / paso) * paso)
            pp = [(i, x, y - y0 + BORDE, w, h, lab) for (i, x, y, w, h, lab) in pos if i in ids]
            sh2 = [dict(s_, y=s_["y"] - y0 + BORDE) for s_ in shs]
            out.append(dict(W=W, L=Lb, Lu=Lu, pos=pp, shelves=sh2, custom=cu))
            area += W * Lb
        if best is None or area < best[0] - 1e-6:
            best = (area, out)
    return best[1] if best else None


@gen
def sheet_cortes(ctx):
    """GEN-010: plan de corte de planchas por espesor (ancho comercial, largo de compra, franjas acotadas, aprovechamiento) y GEN-013: posiciones."""
    from vistas import snap_scale, scale_txt
    c = Gen(ctx, 10, "PLAN DE CORTE DE PLANCHAS: ANCHO COMERCIAL, LARGO DE COMPRA, FRANJAS Y APROVECHAMIENTO")
    s = c.s
    R = c.R["main"]
    w = R[2] - R[0]
    items = nest_items(ctx)
    groups = {}
    for it in items:
        groups.setdefault(round(it[4], 1), []).append(it)
    rows, nests, prow = [], [], []
    tot_buy = tot_net = 0.0
    nid = 0
    for t in sorted(groups):
        its = groups[t]
        rects = [(a[2], a[3], ctx.code(a[0]).replace(CODE + "-", "")) for a in its for _ in range(int(a[5]))]
        net = sum(a[6] * a[5] for a in its)
        pl = plan_espesor(rects)
        if pl is None:
            rows.append([fm(t, 1), "; ".join(f"{a[1]} ×{a[5]}" for a in its), "plancha especial (no cabe en 3.000 de ancho): A DEFINIR con el proveedor", "—", "—", f(net, 0), "—"])
            continue
        buy = sum(q["W"] * q["L"] for q in pl) * t * RHO
        tot_buy += buy; tot_net += net
        rows.append([fm(t, 1), "; ".join(f"{a[1]} ×{a[5]} ({fm(a[2], 0)}×{fm(a[3], 0)})" for a in its), " + ".join(f"{q['W']}×{fm(q['L'], 0)}" + (" (a medida)" if q["custom"] else "") for q in pl), str(len(pl)), f(buy, 0), f(net, 0), f(net / buy * 100, 1) + " %"])
        for k, q in enumerate(pl):
            nid += 1
            q.update(t=t, id=f"P{nid}", k=k + 1, n=len(pl))
            nests.append(q)
            for sh in q["shelves"]:
                cnt = {}
                for lab in sh["n"]:
                    cnt[lab] = cnt.get(lab, 0) + 1
                prow.append([q["id"], fm(t, 1), f"F{sh['i'] + 1}", fm(sh["y"], 0), fm(sh["h"], 0), ", ".join(f"{lb} ×{n}" for lb, n in cnt.items()),
                             fm(BORDE, 0), fm(sh["w0"] + KERF, 0) if len(sh["n"]) > 1 else "—"])
    rows.append(["", "TOTAL (planchas)", "", str(len(nests)), f(tot_buy, 0), f(tot_net, 0), f(tot_net / max(tot_buy, 1) * 100, 1) + " %"])
    y, _ = s.table(R[0], R[3], [("Espesor [mm]", 0.06 * w, "R"), ("Piezas (cant., rectángulo envolvente con sobremetal)", 0.45 * w, "L"), ("Planchas de compra ancho × largo [mm]", 0.14 * w, "C"), ("N°", 0.04 * w, "C"),
                                ("Masa comprada [kg]", 0.10 * w, "R"), ("Masa neta [kg]", 0.10 * w, "R"), ("Aprovech.", 0.11 * w, "R")], rows, h=T_S,
                   title="PLANCHAS POR ESPESOR: ANCHO COMERCIAL Y LARGO DE COMPRA A MEDIDA (múltiplo de 500 mm); aprovechamiento = masa neta / masa comprada", bold_rows=(len(rows) - 1,))
    # esquemas de corte: una celda por plancha, escala normalizada; largo de la plancha en horizontal
    y -= 8
    ytop, ybot = y, R[1] + 26
    n = len(nests)
    ncol = 4 if n > 6 else 3
    nrow = math.ceil(n / ncol)
    cw, ch = (w - 6 * (ncol - 1)) / ncol, (ytop - ybot - 6 * (nrow - 1)) / max(nrow, 1)
    for i, q in enumerate(nests):
        col, row = i % ncol, i // ncol
        bx, by1 = R[0] + col * (cw + 6), ytop - row * (ch + 6)
        sc = snap_scale(min((cw - 26) / q["L"], (ch - 38) / q["W"]))
        Ld, Wd = q["L"] * sc, q["W"] * sc
        x0, y0 = bx + 14, by1 - 12 - Wd
        s.text(f"{q['id']} · e = {fm(q['t'], 1)} mm · {q['W']} × {fm(q['L'], 0)} ({q['k']}/{q['n']}) · ESC {scale_txt(sc)}", (bx, by1), T_N, "TOP_LEFT", bold=True)
        s.rect(x0, y0, x0 + Ld, y0 + Wd, "VIS")
        for (si, px, py, pw, ph, lab) in q["pos"]:
            # plancha dibujada con el largo en horizontal: x de papel = largo (py), y de papel = ancho (px)
            ax, ay = x0 + py * sc, y0 + px * sc
            s.rect(ax, ay, ax + ph * sc, ay + pw * sc, "FINA")
            lb_ = lab.split("-")[0] + "-" + lab.split("-")[1] if "-" in lab else lab
            if ph * sc > tw(lb_, 2.5) + 1.5 and pw * sc > 4:
                s.text(lb_, (ax + ph * sc / 2, ay + pw * sc / 2), 2.5, "MIDDLE_CENTER")
        s.dim((x0, y0), (x0 + Ld, y0), -6, f"{fm(q['L'], 0)}", "h")
        s.dim((x0, y0), (x0, y0 + Wd), -6, f"{q['W']}", "v", txt_shift=(0.0 if Wd > 16 else -(Wd / 2 + 8)), outside=Wd <= 16)
        Lu = q["Lu"]
        if q["L"] - Lu > 20:
            s.line((x0 + Lu * sc, y0), (x0 + Lu * sc, y0 + Wd), "FANT")
            s.dim((x0, y0), (x0 + Lu * sc, y0), -13, f"{fm(Lu, 0)} usado", "h")
    s.notes_block(R[0], R[1] + 22, "NOTAS", [f"Empaque por franjas transversales sobre el ancho comercial; separación entre piezas {fm(KERF, 0)} mm (sangría de corte) y borde de plancha {fm(BORDE, 0)} mm. Posición de cada franja y piezas por franja: GEN-013.",
                                              "Largo de compra: corte a medida por el proveedor en múltiplos de 500 mm sobre ancho comercial; en espesores gruesos con pocas piezas, «a medida» = trozo oxicortado por el proveedor (múltiplos de 100 mm). Discos y segmentos de anillo se anidan por su rectángulo envolvente (los segmentos pueden anidarse por pares girados 180°: aprovechamiento real mayor). Pletinas y barras: largos comerciales de 6 m (despiece)."], h=T_N, width=w)
    hs = [c.h]
    # GEN-013: tabla de franjas
    c2 = Gen(ctx, 13, "PLAN DE CORTE DE PLANCHAS: POSICIÓN DE FRANJAS Y PIEZAS (ORIGEN EN LA ESQUINA DE LA PLANCHA)")
    R2 = c2.R["main"]
    w2 = R2[2] - R2[0]
    s2 = c2.s
    cols = [("Plancha", 0.07 * w2, "C"), ("e [mm]", 0.06 * w2, "R"), ("Franja", 0.06 * w2, "C"), ("y inicio [mm]", 0.09 * w2, "R"), ("Ancho de franja [mm]", 0.10 * w2, "R"),
            ("Piezas en la franja (código ×n, en orden desde x = borde)", 0.42 * w2, "L"), ("x 1.ª pieza [mm]", 0.09 * w2, "R"), ("Paso en x [mm]", 0.09 * w2, "R")]
    y2, left = s2.table(R2[0], R2[3], cols, prow, h=T_S, ymin=R2[1] + 30,
                        title="FRANJAS DE CORTE: y = posición a lo largo de la plancha desde el borde de origen; x = a lo ancho; las piezas de una franja se cortan en el orden listado")
    s2.notes_block(R2[0], R2[1] + 22, "NOTAS", [f"Borde de plancha {fm(BORDE, 0)} mm y sangría {fm(KERF, 0)} mm incluidos en las posiciones. Marcar con el código de la pieza y la colada antes de separar (trazabilidad EN 10204 3.1).",
                                                "Plan orientativo para la compra; el fabricante puede reordenar con su software de anidado manteniendo la orientación de laminación indicada en los planos de pieza."], h=T_N, width=w2)
    hs.append(c2.h)
    return hs


@gen
def sheet_supuestos(ctx):
    c = Gen(ctx, 9, "SUPUESTOS DEL DIBUJANTE Y BRECHAS CON EL CÁLCULO")
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
           "Tamaños de filete: confirmar los marcados «mínimo AWS, a confirmar» y el caso w_web > t − 2 (AISC J2.2b).", "Grados de material PROPUESTOS por Fy del cálculo (GEN-005): aprobar o fijar el grado.",
           "Torques propuestos (GEN-008): confirmar o reemplazar por cálculo VDI 2230.", "WPS-P y sistema de pintura PROPUESTOS (GEN-012, GEN-006): confirmar; marca/modelo de los componentes de catálogo (GEN-008): A DEFINIR POR CATÁLOGO.", "Supuestos S## y brechas B-## (GEN-009): aceptar o corregir antes de aprobar.",
           "Texto negro sobre fondo blanco; letra ≥ 3,5 mm en el plot A1 (tablas densas 3,0 mm; mínimo absoluto 2,5 mm).", "Estado EMITIDO PARA REVISIÓN en todas las láminas hasta su aprobación; completar DIBUJÓ/REVISÓ/APROBÓ."]
    rows = [[str(i + 1), v, "", ""] for i, v in enumerate(ver)]
    c.s.table(R[0], R[3], [("N°", 0.04 * w, "C"), ("Verificación", 0.74 * w, "L"), ("Cumple (sí/no)", 0.10 * w, "C"), ("Observación", 0.12 * w, "L")], rows, h=T_S, title="VERIFICACIONES TRANSVERSALES DEL JUEGO DE PLANOS")
    return c.h


@gen
def sheet_wps(ctx):
    c = Gen(ctx, 12, "WPS PRE-CALIFICADOS PROPUESTOS POR TIPO DE JUNTA (AWS D1.1 CL. 3) Y PRECALENTAMIENTO")
    s = c.s
    R = c.R["main"]
    w = R[2] - R[0]
    cols = [(t, a * w / sum(x[1] for x in propuestas.WPS_COLS), al) for t, a, al in propuestas.WPS_COLS]
    y, _ = s.table(R[0], R[3], cols, propuestas.wps_rows(ctx), h=T_S, title=propuestas.ROTULO_WPS)
    # N-16: el A572 Gr.50 (Grupo II) solo admite procesos de bajo hidrógeno (categoría B); la categoría A (SMAW sin bajo hidrógeno) no se aplica
    pre = [["≤ 19 (3/4 in)", "sin precalentar (T ≥ 10 °C)"], ["> 19 a 38 (1½ in)", "10 °C"], ["> 38 a 65 (2½ in)", "65 °C"], ["> 65", "110 °C"]]
    y2, _ = s.table(R[0], y - 8, [("Espesor de la parte más gruesa [mm]", 0.30 * w, "L"), ("Categoría B: E7018, ER70S-6, E71T-1 (procesos de bajo hidrógeno, los únicos admitidos)", 0.70 * w, "C")], pre, h=T_S,
                    title="PRECALENTAMIENTO MÍNIMO — AWS D1.1-2020 TABLA 5.11, acero Grupo II (ASTM A572 Gr.50), por el espesor de la parte más gruesa de la junta (no se admiten electrodos que no sean de bajo hidrógeno)")
    s.notes_block(R[0], y2 - 8, "NOTAS", [propuestas.ROTULO_WPS + ": los WPS de esta lámina son una propuesta del dibujante; el fabricante debe calificarlos o confirmarlos y emitir los PQR/WPS definitivos.",
                                       "Procesos ISO 4063: 135 (GMAW, ER70S-6, Ar 75 %% / CO₂ 25 %%), 111 (SMAW, E7018 de bajo hidrógeno, secado según el fabricante del electrodo), 136 (FCAW, E71T-1). Aporte con resistencia a tracción ≥ %s MPa." % f(ctx.P["FEXX"]),
                                       "Rangos de corriente: típicos de fabricante, a ajustar en la calificación según espesor, posición y longitud de arco; interpase máximo 250 °C (propuesta). Tamaños de filete y símbolos: GEN-007 y láminas de pieza.",
                                       *(["Soldadura de acero inoxidable 309L (barras del rebaje UHMW): sin precalentamiento; interpase ≤ 150 °C; PT 100 %."] if any("ER309L" in w["aporte"] for w in ctx.welds) else []), "Aceros bonificados (pasadores, pivote, uña) NO se sueldan.",
                                       "Soldadores calificados según AWS D1.1 cl. 4 o ISO 9606-1 para las posiciones indicadas; END según la tabla de soldaduras (VT, MT, UT, PT)."], h=T_N, width=0.9 * w, numbered=True)
    return c.h
