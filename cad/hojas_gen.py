"""Láminas generales: notas, conjunto, explosionada, secuencia, despiece, lista de corte, soldaduras, tolerancias e inspección, supuestos."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_base import *
from hojas_fab import title_view, int_title
import lista


def wtable(s, x, y, cols, rows, h=1.8, bold_first=False, rpad=1.6):
    """Tabla con celdas de texto que se parten en varias líneas. cols: [(titulo, ancho)]. Devuelve y final."""
    cw = h * 0.72
    widths = [c[1] for c in cols]
    W_ = sum(widths)
    lines_of = []
    for r in rows:
        ls = [wrap(str(c), max(4, int((w - 2) / cw))) for c, w in zip(r, widths)]
        lines_of.append(ls)
    # encabezado
    hh = 5.0
    s.rect(x, y - hh, x + W_, y, "VIS")
    xx = x
    for (t, w) in cols:
        s.text(t, (xx + w / 2, y - hh / 2), h + 0.3, "MIDDLE_CENTER", bold=True)
        xx += w
    yy = y - hh
    ytop = y
    for r, ls in zip(rows, lines_of):
        n = max(len(l) for l in ls)
        rh = n * h * 1.25 + rpad
        s.line((x, yy), (x + W_, yy), "FINA")
        xx = x
        for l, w in zip(ls, widths):
            for i, t in enumerate(l):
                s.text(t, (xx + 1.0, yy - 1.0 - h * 0.6 - i * h * 1.25), h, "MIDDLE_LEFT")
            xx += w
        yy -= rh
    s.line((x, yy), (x + W_, yy), "VIS")
    xx = x
    for w in widths + [0]:
        s.line((xx, ytop), (xx, yy), "FINA" if 0 < xx - x < W_ else "VIS")
        xx += w
    return yy


def sheet_notas(ctx):
    g, P, DV = ctx.g, ctx.P, ctx.DV
    h = Hoja(ctx, "GEN", 1, "NOTAS GENERALES, NORMAS Y ÍNDICE DE LÁMINAS", "S/E")
    s = h.begin()
    tr = DV["tRev"]
    nt = [
        "ADVERTENCIAS",
        "1. " + ADVERTENCIA,
        "2. " + NOTA_VIENTO + " (el cálculo no considera viento: decisión del mandante).",
        f"3. {NOTA_ANCLAJE.replace('q_losa', 'q_losa = ' + fm(P['q_floor'], 1) + ' MPa')} Presión de contacto máxima de la interfaz {fm(DV['q_max'], 2)} MPa.",
        f"4. Capacidad nominal {f(P['W_tf'])} tf; excentricidad del CG ≤ {f(P['e'])} mm; carga solo sobre parrilla de reparto Ø{f(P['D_load'])} o ≥ 8 apoyos simétricos.",
        f"5. Velocidad de operación: tiempo por vuelta calculado {fm(tr, 1)} min (bomba {fm(P['Q_pump'], 1)} L/min; D['bomba']); ciclo {fm(DV['tCycle'], 2)} min." + ("" if abs(tr - 15) < 1 else " El mandante indicó 15 min/vuelta: NO coincide (ver brechas)."),
        "6. Altura libre no es restricción de diseño (decisión del mandante). Sin requerimiento sísmico (Ch = 0).",
        "NORMAS APLICABLES",
        "AISC 360-22 (ASD) · ASME BTH-1 Categoría de diseño B, Nd = 3,0 (cadena de empuje) · AWS D1.1/D1.1M:2020 · ISO 2768-m (tolerancias generales) · ISO 286 (ajustes) ·",
        "ISO 1101 (tolerancias geométricas) · ISO 1302 (rugosidad) · ISO 2553 (símbolos de soldadura) · ISO 5817 (niveles de calidad de soldaduras) · EN 10204 3.1 (certificados) · ISO 12944 (pintura).",
        "PRESIÓN Y CIRCUITO HIDRÁULICO",
        f"7. Presión máxima de trabajo del cilindro y de la bomba: {fm(P['p_rated'] * 0.0689476, 0)} bar (p_rated = {f(P['p_rated'])} psi). Alivio {f(P['p_relief'])} bar (prohibido subirlo); alarma/detención {f(P['p_alarm'])} bar; retorno {f(P['p_ret'])} bar.",
        "8. Operar siempre con ambos cilindros en par (circuito en paralelo con válvula de bloqueo). Prohibido empujar con un solo cilindro.",
        f"9. Cadena de empuje verificada a la fuerza de calado {fm(DV['Fstall'], 1)} kN. Detener y relubricar si la presión supera {f(P['p_alarm'])} bar.",
        "MATERIALES Y FABRICACIÓN",
        "10. Materiales con certificado EN 10204 3.1; planchas de la mesa con UT ASTM A578 nivel B y Z35. Soldadura con WPS/PQR calificados AWS D1.1 (WPS-xx A DEFINIR POR EL FABRICANTE).",
        f"11. Uñas y pasadores: contacto templado ≥ 55 HRC, profundidad efectiva ≥ {fm(g.z_hard, 1)} mm (verificación del núcleo).",
        "12. Taller sin torno vertical: corte a llama/plasma, soldadura, taladro radial y mandrinadora. Ajustes largos H7/p6 (pivote, buje, cubo) por mandrinadora o taladro; evitar piezas torneadas de gran diámetro.",
        "13. Sin anclaje: la base apoya sobre losa o mats; verificar la superficie de apoyo por terceros (planitud, capacidad).",
    ]
    if g.opt:
        nt += ["INTERFAZ DE GIRO", f"14. {g.interfaz_nombre}. " + ("Fijación DESMONTABLE por sectores (topes soldados al respaldo, tornillos avellanados de posición)." if g.removable else "Fijación PEGADA: NO DESMONTABLE (fix_mode = 2); no admite limpieza ni cambio.")]
        nt += ["PROCEDIMIENTO DE LIMPIEZA Y ENGRASE DE LOS DISCOS DESMONTABLES",
               "a) Despresurizar el circuito, calzar la mesa y, con medios de izaje del montajista, elevarla lo mínimo para liberar los sectores del lado mesa (el cálculo no define puntos de izaje de la mesa).",
               "b) Retirar los tornillos de posición y extraer cada sector marcado; limpiar con solvente desengrasante y paño sin pelusa; inspeccionar rayas, gripado y desgaste (reponer si el espesor baja del mínimo constructivo).",
               "c) Verificar planitud de las caras (0,05) y rugosidad Ra 0,4; relapear solo hasta el sobreespesor del cálculo.",
               "d) Recolocar cada sector en su posición, apretar tornillos (torque A DEFINIR) y reponer grasa grafitada NLGI 2 en las ranuras; engrasar por las graseras M10×1 antes de cada operación.",
               "e) Limpiar y aislar la grasa grafitada de equipos energizados (el grafito es conductor). Registrar el procedimiento y la presión de despegue."]
    else:
        nt += ["LUBRICACIÓN", "14. Interfaz acero-acero con grasa grafitada NLGI 2 (≥ 10 % grafito, EP) en ambas caras; lubricar antes de cada operación. Acero seco no gira."]
    y = s.notes_block(30, 566, "NOTAS GENERALES", nt, h=2.9, wrap_chars=195, ls=1.5)
    # índice de láminas (se completa en el empaquetado)
    ctx.indice_y = y
    h.indice_pos = (30, y - 6)
    return h


def sheet_supuestos(ctx, gaps):
    h = Hoja(ctx, "GEN", 9, "SUPUESTOS DEL DIBUJANTE Y BRECHAS CON EL CÁLCULO", "S/E")
    s = h.begin()
    rows = [[x["id"], x["tema"], x["valor"], x["motivo"]] for x in ctx.sup]
    s.text("SUPUESTOS DE DIBUJO (rotulados PROVISORIO en las láminas donde intervienen)", (30, 566), 3.0, "TOP_LEFT", bold=True)
    y = wtable(s, 30, 560, [("Id", 10), ("Tema", 55), ("Valor adoptado", 190), ("Motivo", 520)], rows, h=1.9)
    s.text("BRECHAS: DATOS QUE EL CÁLCULO DEBE ENTREGAR O CONFIRMAR", (30, y - 8), 3.0, "TOP_LEFT", bold=True)
    wtable(s, 30, y - 14, [("Id", 10), ("Tema", 55), ("Descripción", 600), ("Decisión requerida", 110)], [[x["id"], x["tema"], x["desc"], x["decision"]] for x in gaps], h=1.9)
    return h


def sheet_bom(ctx):
    rep = ctx.rep
    h = Hoja(ctx, "GEN", 5, "DESPIECE (LISTA DE MATERIALES), MASA Y CENTRO DE GRAVEDAD", "S/E", masa=f"{f(rep['masa_total_ensamble'], 1)} kg")
    s = h.begin()
    rows = []
    for r in lista.bom_rows(ctx):
        rows.append([r["pos"], r["code"].replace(CODE + "-", ""), r["desc"], r["qty"], r["material"], f(r["unit"], 2 if r["unit"] < 10 else 1), f(r["total"], 1), r["proceso"], r["obs"] or "—"])
    cols = [("Pos", 8), ("Código", 22), ("Descripción", 150), ("Cant", 10), ("Material / norma", 92), ("kg/u", 14), ("kg tot.", 16), ("Proceso", 120), ("Observación", 112)]
    s.text("DESPIECE", (30, 566), 3.0, "TOP_LEFT", bold=True)
    y = wtable(s, 30, 560, cols, rows, h=1.6)
    ms = rep["masas"]
    cg = rep["cg"]
    s.text(f"MASA TOTAL del ensamble (3D): {f(rep['masa_total_ensamble'], 1)} kg · CENTRO DE GRAVEDAD (x, y, z desde el centro de la mesa y la cara inferior de la base): ({fm(cg[0], 1)}; {fm(cg[1], 1)}; {fm(cg[2], 1)}) mm.", (30, y - 6), 2.4, "TOP_LEFT", bold=True)
    s.text(f"Comparable con el núcleo: 3D {f(ms['total_3d'], 1)} kg frente a {f(ms['total_nucleo'], 1)} kg (D['derivados'].masas.total): diferencia {fm(ms['dif'], 1)} kg ({fm(ms['dif_pct'], 2)} %); tolerancia {fm(ms['tol_pct'], 1)} %. Piezas fuera del núcleo: {f(ms['masa_fuera'], 1)} kg.", (30, y - 11), 2.0, "TOP_LEFT")
    ex = lista.extras(ctx)
    s.text("ELEMENTOS NO MODELADOS (comerciales o sin geometría en el cálculo); códigos de catálogo: A DEFINIR, no se inventan", (30, y - 18), 2.4, "TOP_LEFT", bold=True)
    wtable(s, 30, y - 22, [("Descripción", 200), ("Cant", 12), ("Especificación", 330), ("Código de catálogo", 90)], [[d, q, e, c] for (d, q, e, c) in ex], h=1.7)
    return h


def sheet_corte(ctx):
    h = Hoja(ctx, "GEN", 6, "LISTA DE CORTE", "S/E")
    s = h.begin()
    s.text("LISTA DE CORTE (dimensiones brutas con sobremetal; corte a llama/plasma/sierra)", (30, 566), 3.0, "TOP_LEFT", bold=True)
    rows = lista.cut_rows(ctx)
    wtable(s, 30, 560, [("Pos", 24), ("Pieza", 58), ("Forma", 36), ("Dimensión bruta (mm)", 70), ("Cant", 12), ("Material", 100), ("Observación", 160)], rows, h=1.8)
    return h


def sheet_soldaduras(ctx):
    h = Hoja(ctx, "GEN", 7, "PROGRAMA DE SOLDADURAS (ISO 2553 / ISO 5817 / AWS D1.1)", "S/E")
    s = h.begin()
    W_ = soldaduras(ctx)
    rows = [[w["id"], w["juntas"], w["tipo"], w["tamano"], w["nota"], w["proc"], "ISO 5817-" + w["calidad"], w["end"], w["wps"]] for w in W_]
    s.text("PROGRAMA DE SOLDADURAS (tipo, tamaño, END)", (30, 566), 3.0, "TOP_LEFT", bold=True)
    y = wtable(s, 30, 560, [("Id", 10), ("Juntas", 100), ("Tipo y preparación", 95), ("Tamaño", 20), ("Origen del tamaño", 60), ("Proceso ISO 4063", 55), ("Calidad", 22), ("END", 36), ("WPS", 86)], rows, h=1.7)
    s.notes_block(30, y - 8, "CONTROL", [
        "Precalentamiento AWS D1.1: t ≤ 20: 10 °C (se exige 50 °C mín.); 20 < t ≤ 38: 50 °C; 38 < t ≤ 65: 65 °C; interpase ≤ 250 °C. Electrodos E7018 / alambre ER70S-6 (FEXX del núcleo: %s MPa)." % f(ctx.P["FEXX"]),
        "42CrMo4 y 34CrNiMo6 (pivote, pasadores, uñas): NO se sueldan. Soldar los topes de la interfaz antes del alivio de tensiones y del rectificado de las caras.",
        "Tamaños marcados «mín. AWS» no los fija el cálculo: se adopta el mínimo de AWS D1.1 por la parte más gruesa (criterio del registro de normas del proyecto); el calculista debe confirmarlos.",
        "END propuestos por criticidad: a confirmar por el calculista. Inspección visual 100 % (ISO 17637) previa a todo END. Registro: WPS/PQR, calificación de soldadores e informes END.",
    ], h=2.0, wrap_chars=190)
    return h


def sheet_tolerancias(ctx):
    g, P = ctx.g, ctx.P
    h = Hoja(ctx, "GEN", 8, "TOLERANCIAS, AJUSTES, MATERIALES E INSPECCIÓN", "S/E")
    s = h.begin()
    s.text("TOLERANCIAS GENERALES (ISO 2768-m)", (30, 566), 3.0, "TOP_LEFT", bold=True)
    rows = [["0,5–3", "±0,1", "3–6", "±0,1", "6–30", "±0,2", "30–120", "±0,3", "120–400", "±0,5", "400–1000", "±0,8", "1000–2000", "±1,2", "2000–4000", "±2"]]
    s.table(30, 560, [(t, w, "C") for t, w in zip(["Rango", "Tol.", "Rango", "Tol.", "Rango", "Tol.", "Rango", "Tol.", "Rango", "Tol.", "Rango", "Tol.", "Rango", "Tol.", "Rango", "Tol."], [17, 11] * 8)], rows, rh=5.0, h=1.9)
    s.text("Lineales ISO 2768-m (mm). Angulares: ±1° hasta 10 mm, ±0°30' hasta 50 mm, ±0°20' hasta 120 mm. Geométricas: ISO 2768-K salvo indicación (ISO 1101) en cada plano.", (30, 543), 1.9)
    s.text("AJUSTES (ISO 286)", (30, 534), 3.0, "TOP_LEFT", bold=True)
    y = wtable(s, 30, 528, [("Unión", 130), ("Ajuste", 110), ("Tipo / método", 220), ("Norma", 40)], [list(a) for a in ajustes(ctx)], h=1.9)
    s.text("TOLERANCIAS GEOMÉTRICAS Y RUGOSIDAD PRINCIPALES", (30, y - 6), 3.0, "TOP_LEFT", bold=True)
    geo = [["Cara de apoyo de la base (zona Ø%s)" % f(P["D_top"] + 20), "Planitud 0,20", "Ra 1,6–3,2", "BAS-001"], ["Cara inferior de la mesa", "Planitud 0,20; paralelismo cara superior 0,30", "Ra 1,6–3,2", "MES-001/002"],
           ["Pivote / agujero H7", "Perpendicularidad 0,05; coaxialidad collar–base 0,05", "Ra 0,8 (pivote), Ra 1,6 (H7)", "BAS-001, PIV-001"],
           ["Agujeros de pasadores (28)", "Posición ±0,05°; coaxialidad entre anillos 0,05", "Ra 1,6", "MES-002"], ["Ranura T de la bancada", "Paralelismo 0,10; posición ±0,2", "Ra 1,6", "ACC-001"],
           ["Cara de empuje de la uña", "Planitud 0,05", "Ra 0,8", "ACC-003"], ["Caras deslizantes de la interfaz", "Planitud 0,05 por sector", "Ra 0,4", "INT-001/002"]]
    y = wtable(s, 30, y - 12, [("Elemento", 110), ("Tolerancia geométrica (ISO 1101)", 200), ("Rugosidad (ISO 1302)", 100), ("Plano", 90)], geo, h=1.9)
    s.text("MATERIALES CON CERTIFICADO (EN 10204 3.1)", (30, y - 6), 3.0, "TOP_LEFT", bold=True)
    mats = {}
    for p in ctx.m.parts:
        mats.setdefault((p.material, p.cert), []).append(p.code.replace(CODE + "-", ""))
    rows = [[m_[0], m_[1], ", ".join(v)] for m_, v in mats.items()]
    y = wtable(s, 30, y - 12, [("Material / norma", 230), ("Certificado", 80), ("Ítems", 290)], rows, h=1.8)
    s.text("PUNTOS DE INSPECCIÓN (END, dimensional, dureza, torque)", (30, y - 6), 3.0, "TOP_LEFT", bold=True)
    wtable(s, 30, y - 12, [("N°", 10), ("Tipo", 28), ("Punto de inspección", 560)], [[a, b, c] for (a, b, c) in inspecciones(ctx)], h=1.8)
    return h


# ----------------------------------------------------------------------------------------------
EXPL = {"base_plancha": 0, "collar": 0, "marco_largo": 0, "marco_corto": 0, "mensula_mejilla": 0, "mensula_oreja_sup": 0, "mensula_oreja_inf": 0, "orejas": 0, "bancada": 0,
        "int_tope_base": 100, "int_disco_base": 200, "int_bronce": 200, "int_tornillo_base": 300, "int_uhmw": 380, "int_tope_uhmw": 380, "int_tapones": 260,
        "int_disco_mesa": 520, "int_cara": 520, "int_tope_mesa": 600, "int_tornillo_mesa": 680, "graseras": 1100,
        "buje": 520, "pernos_pasador": 1250, "tapa_ret": 1450, "tapa_insp": 1550, "madera": 1750, "madera_anillo": 1750,
        "cilindro": 500, "patin": 250, "una": 420, "pasador_vastago": 650, "pasador_ojal": 650}
EXPL_DOWN = {"pivote": -450}


def expl_dz(key):
    if key.startswith("mesa_") or key == "pasadores":
        return 850
    return EXPL_DOWN.get(key, EXPL.get(key, 0))


def sheet_explosionada(ctx):
    m = ctx.m
    h = Hoja(ctx, "GEN", 3, "ISOMÉTRICA EXPLOSIONADA CON GLOBOS", "1:20", masa=f"{f(ctx.rep['masa_total_ensamble'], 1)} kg")
    s = h.begin()
    parts = {}
    for p in m.parts:
        dz = expl_dz(p.key)
        parts[p.key] = ctx.shapes[p.key].translate(cq.Vector(0, 0, dz))
    sc = 0.085
    V = View(s, parts, "iso", (320, 290), sc, center=(0, 0, 700), hidden=False, tol=3.0, label="Explosionada")
    COTAS_sh = vistas.COTAS.shapes
    V.draw()
    # globos
    ancl = []
    for p in m.parts:
        sh = parts[p.key]
        vs = sh.Vertices()
        pts = [(V.uv((v.X, v.Y, v.Z)), v) for v in vs]
        cx = V.uv(tuple(sh.Center().toTuple()))
        left = cx[0] < 0
        u, v = (min(pts, key=lambda t: t[0][0]) if left else max(pts, key=lambda t: t[0][0]))[0]
        ancl.append((p, (u, v), left))
    # columnas de globos: izquierda y derecha, ordenados por v
    for side, xcol in ((True, 70), (False, 560)):
        grp = sorted([a for a in ancl if a[2] == side], key=lambda a: -a[1][1])
        n = len(grp)
        y0, y1 = 540, 110
        for i, (p, uv, _) in enumerate(grp):
            yb = y0 - (y0 - y1) * (i / max(n - 1, 1))
            s.balloon(V.Pt2(uv), (xcol, yb), p.pos, r=4.0)
    # lista de posiciones
    rows = [[str(p.pos), p.code.replace(CODE + "-", ""), p.name, str(p.qty)] for p in m.parts]
    wtable(s, 618, 560, [("Pos", 8), ("Código", 22), ("Descripción", 108), ("Cant", 10)], rows, h=1.6)
    s.text("Cilindros, patines y uñas dibujados para giro antihorario; ménsulas de ambos sentidos.", (30, 30), 2.0)
    s.text("Desplazamientos verticales solo ilustrativos (no a escala de ensamble).", (30, 26), 2.0)
    return h


def sheet_secuencia(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    h = Hoja(ctx, "GEN", 4, "SECUENCIA DE ENSAMBLAJE", "S/E")
    s = h.begin()
    base = ["base_plancha", "collar", "marco_largo", "marco_corto", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "orejas", "bancada"]
    int_b = [k for k in ("int_tope_base", "int_disco_base", "int_bronce", "int_tapones", "int_tornillo_base", "int_uhmw", "int_tope_uhmw") if m.has(k)]
    piv = ["pivote", "buje"]
    mesa = [p.key for p in m.parts if p.key.startswith("mesa_")] + ["pasadores", "pernos_pasador"] + [k for k in ("int_tope_mesa", "int_disco_mesa", "int_cara", "int_tornillo_mesa", "graseras") if m.has(k)]
    acc = ["cilindro", "patin", "una", "pasador_vastago", "pasador_ojal"]
    top = ["tapa_ret", "tapa_insp"] + [k for k in ("madera", "madera_anillo") if m.has(k)]
    steps = [
        ("Fabricar y soldar la base (BAS-001): marco, collar, ménsulas, orejas de izaje y bancadas; alivio de tensiones; mandrinar el agujero H7 y planear la cara de apoyo.", base),
        ("Soldar los topes del lado base sobre la plancha base (antes del rectificado) y colocar los sectores de la interfaz del lado base con sus tornillos de posición." if g.opt and g.removable else
         ("Colocar/pegar la interfaz del lado base." if g.opt else "Limpiar la cara de apoyo y aplicar grasa grafitada NLGI 2."), base + int_b),
        ("Calar el pivote (p6/H7) en la plancha base y el collar; prensar el buje en el cubo de la mesa (s6/H7).", base + int_b + piv),
        ("Fabricar la mesa (MES-001…004): soldar almas, nervios, cubo y planchas; alivio; mandrinar agujeros; soldar topes del lado mesa y fijar los sectores de la interfaz del lado mesa.", mesa),
        ("Izar la mesa con medios del montajista (sin puntos definidos por el cálculo), centrarla en el pivote y bajarla sobre la interfaz; verificar giro libre a mano.", base + int_b + piv + mesa),
        ("Colocar tapa retenedora (juego vertical 3 mm) y tapa de inspección" + ("; colocar tablones y anillo de la cubierta de madera." if g.wood else "."), base + int_b + piv + mesa + top),
        ("Insertar los patines por el extremo de la ranura T de cada bancada; montar uñas con su resorte y los cilindros entre ménsula y patín con los pasadores de articulación.", base + int_b + piv + mesa + top + acc),
        ("Conectar mangueras (A: avance, B: retorno) al colector común; llenar de aceite y purgar; engrasar por las %d graseras y llenar las ranuras." % g.n_greaser if g.opt in (1, 3) else "Conectar mangueras (A: avance, B: retorno) al colector común; llenar de aceite y purgar; aplicar grasa grafitada.", None),
        ("Prueba en vacío: 2 ciclos completos con ambos cilindros; registrar presión; luego ensayo de aceptación: giro 360° con 1,0 WLL (μ real) y MT de soldaduras de ménsulas y orejas.", None),
    ]
    y = 560
    pos = [(110, 470), (290, 470), (470, 470), (110, 330), (290, 330), (470, 330), (110, 190), (290, 190), (470, 190)]
    for i, (txt, keys) in enumerate(steps):
        cx, cy = pos[i]
        s.circle((cx - 80, cy + 85), 6, "FINA"); s.text(str(i + 1), (cx - 80, cy + 85), 4.0, "MIDDLE_CENTER", bold=True)
        for j, ln in enumerate(wrap(txt, 54)):
            s.text(ln, (cx - 72, cy + 88 - j * 3.2), 2.0, "TOP_LEFT")
        if keys:
            shp = {k: ctx.shapes[k] for k in keys if k in ctx.shapes}
            V = View(s, shp, "iso", (cx, cy - 10), 0.034, center=(0, 0, 100), tol=6.0, label=f"Paso {i + 1}"); V.draw()
    s.text("Rótulos: cada sector de interfaz lleva número de posición y sentido para su reposición. Torques y tolerancias: ver GEN-008.", (30, 60), 2.0)
    s.text(NOTA_ANCLAJE, (30, 52), 2.0); s.text(NOTA_VIENTO, (30, 46), 2.0)
    return h


def sheet_conjunto(ctx):
    g, P, DV, m = ctx.g, ctx.P, ctx.DV, ctx.m
    allk = [p.key for p in m.parts if p.key not in ("madera", "madera_anillo")] if False else [p.key for p in m.parts]
    h = Hoja(ctx, "GEN", 2, "CONJUNTO GENERAL: PLANTA, CORTES Y VISTAS", "1:10 / 1:5", masa=f"{f(ctx.rep['masa_total_ensamble'], 1)} kg")
    s = h.begin()
    B, tb = g.B, g.tb
    shp = ctx.sh(*allk)
    V = View(s, shp, "top", (160, 430), 0.1, tol=3.0, label="Planta"); V.draw()
    s.line(V.P(-B / 2 - 40, 0, 0), V.P(B / 2 + 40, 0, 0), "EJE"); s.line(V.P(0, -B / 2 - 40, 0), V.P(0, B / 2 + 40, 0), "EJE")
    V.dim((-B / 2, -B / 2, 0), (B / 2, -B / 2, 0), -9, orient="h", on=["base_plancha"])
    V.dim_dia((0, 0, g.z0 + g.hd + (P["t_wood"] if g.wood else 0)), g.Rt, 130, text=f"Ø{f(P['D_top'])}", on=["mesa_anillo_sup"], ext=22) if not g.wood else None
    s.section_mark(V.P(-B / 2 - 25, 0, 0), 90, "A"); s.section_mark(V.P(B / 2 + 25, 0, 0), 90, "A")
    title_view(s, (160, 292), "PLANTA", "ESC 1:10")
    zt = g.z0 + g.hd + (P["t_wood"] if g.wood else 0)
    VA = View(s, shp, "front", (460, 400), 0.1, center=(0, 0, 0), cut=((0, 0, 0), (0, 1, 0)), tol=3.0, label="Corte A-A", hatch_scale=1.0); VA.draw()
    VA.dim((B / 2, 0, 0), (B / 2, 0, tb + P["rim_h"]), 12, orient="v", on=["marco_largo", "marco_corto", "base_plancha"], text=f"{f(tb + P['rim_h'])}") if False else None
    VA.dim((g.Rt, 0, g.z0), (g.Rt, 0, g.z0 + g.hd), 10, orient="v", on=["mesa_anillo_inf", "mesa_anillo_sup"], text=f"{f(g.hd)} (mesa)")
    VA.dim((-B / 2, 0, 0), (-B / 2, 0, tb), -8, orient="v", on=["base_plancha"], text=f"{f(tb)}", outside=True)
    title_view(s, (460, 330), "CORTE A-A (plano y = 0)", "ESC 1:10")
    VF = View(s, shp, "front", (460, 230), 0.1, tol=3.0, label="Elevación frontal"); VF.draw()
    s.text(f"Altura total sobre el piso H = {f(zt)} mm (base + interfaz {fm(g.delta, 0)} + mesa {f(g.hd)}" + (f" + madera {f(P['t_wood'])}" if g.wood else "") + ").", (390, 185), 2.0)
    title_view(s, (460, 195), "ELEVACIÓN", "ESC 1:10")
    c = {x["id"]: x for x in DV["casos"]}
    rows = [["Capacidad nominal (WLL)", f"{f(P['W_tf'])} tf ({f(DV['W'])} kN)"], ["Excentricidad máx. del CG", f"{f(P['e'])} mm"], ["Diámetro de mesa / apoyo de carga", f"Ø{f(P['D_top'])} / Ø{f(P['D_load'])}"],
            ["Base / altura total", f"{f(B)}×{f(B)} / {f(zt)} mm"], ["Masa total del ensamble (3D)", f"{f(ctx.rep['masa_total_ensamble'], 1)} kg"],
            ["Centro de gravedad (x, y, z)", f"({fm(ctx.rep['cg'][0], 1)}; {fm(ctx.rep['cg'][1], 1)}; {fm(ctx.rep['cg'][2], 1)}) mm"],
            ["Accionamiento", f"{P['n_cyl']:.0f} cil. Ø{f(P['D_bore'])}/Ø{f(P['d_rod'])}, carrera {f(P['stroke'])}, patín guiado"], ["Giro por carrera / pasadores", f"{fm(360 / g.N_pin, 2)}° / {g.N_pin}"],
            ["F diseño por cilindro (μ de diseño)", f"{fm(c['dis']['F'], 1)} kN · {f(c['dis']['p'])} bar"], ["F de calado (alivio %s bar)" % f(P["p_relief"]), f"{fm(DV['Fstall'], 1)} kN · FS {fm(c['dis']['FS'], 2)}"],
            ["Presión máxima de trabajo del cilindro", f"{fm(P['p_rated'] * 0.0689476, 0)} bar (p_rated)"], ["Presión de contacto máx. interfaz", f"{fm(DV['q_max'], 2)} MPa"],
            ["Tiempo por vuelta", f"{fm(DV['tRev'], 1)} min (bomba {fm(P['Q_pump'], 1)} L/min)"], ["Interfaz de giro", g.interfaz_nombre]]
    s.text("DATOS TÉCNICOS", (30, 270), 3.0, "TOP_LEFT", bold=True)
    s.table(30, 264, [("Ítem", 85, "L"), ("Valor", 130, "L")], rows, rh=4.8, h=1.9)
    notas = [ADVERTENCIA, NOTA_VIENTO, NOTA_ANCLAJE] + (["INTERFAZ NO DESMONTABLE (fijación pegada, fix_mode = 2)."] if g.opt and not g.removable else []) + [
             "Cilindros, patines y uñas dibujados para giro antihorario; ménsulas de ambos sentidos. Lista de posiciones: GEN-005 y GEN-003.",
             "Normas: AISC 360-22 ASD; ASME BTH-1 Cat. B Nd 3,0; AWS D1.1; ISO 2768-m, 286, 1101, 1302, 2553, 5817."]
    s.notes_block(648, 560, "NOTAS DEL CONJUNTO", notas, h=2.1, wrap_chars=95)
    s.notes_block(648, 470, "ÍNDICE DE PLANOS DE FABRICACIÓN", [f"{hh.plano} {hh.titulo[:46]}" for hh in ctx.hojas if not hh.plano.startswith(CODE + "-GEN")][:0] or ["Ver índice en TT300C-GEN-001-B."], h=2.0, wrap_chars=110)
    return h
