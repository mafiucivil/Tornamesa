"""Lista de materiales (despiece), elementos no modelados y lista de corte, a partir del modelo 3D y del JSON de diseño."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import *


def bom_rows(ctx):
    from hojas_base import tipos_txt
    out = []
    for p in ctx.m.parts:
        base = dict(pos=p.pos, code=p.code, nombre=p.name, desc=p.desc, qty=p.qty, material=p.material, norma=p.cert, unit=p.mass_unit, total=p.mass_total, proceso=p.process,
                    obs=((p.obs + "; ") if p.obs else "") + (f"Tratamiento: {p.tratamiento}" if p.tratamiento and p.tratamiento != "—" else "").strip("; "),
                    comercial=p.comercial, catalogo=p.catalogo or "", en_nucleo=bool(p.core), sub=p.sub)
        if not p.tipos:
            out.append(base)
            continue
        for i, t in enumerate(p.tipos, 1):               # H-04: una fila por tipo de geometría, con su código
            out.append(dict(base, pos=f"{p.pos}.{i}", code=p.code_suf(t["suf"]), desc=f"{p.desc}. {tipos_txt(p, t)}", qty=t["n"], unit=t["masa_unit"], total=t["masa_unit"] * t["n"]))
    return out


def extras(ctx):
    """Elementos que el modelo no dibuja (comerciales o sin geometría definida en el cálculo)."""
    g, P = ctx.g, ctx.P
    n = int(P["n_cyl"])
    L = ([("Resorte de retorno de la uña (compresión)", n, f"Comercial; carrera ≥ {f(g.KG['travel'] + 5)} mm, fuerza 150–300 N", "A DEFINIR POR CATÁLOGO")] if g.modo == 1 else []) + [
        (f"Tornillo ISO 10642 M10×{g.cap_L:.0f} cl. 10.9 (tapa retenedora)", 4, "10.9", "A DEFINIR POR CATÁLOGO"),
        (f"Tornillo ISO 10642 M{fm(g.insp_d, 0)}×{g.insp_L} cl. 10.9 (tapa de inspección)", 6, "10.9", "A DEFINIR POR CATÁLOGO"),
        ("Placa y tornillo de retención de pasador de articulación" if g.modo == 1 else "Placa y tornillo de retención de los pasadores E y Q (PROPUESTA)", 2 * n, "S355J2 / 8.8", "A DEFINIR POR CATÁLOGO"),
        ("Grillete de izaje (pasador de Ø ≤ %s mm)" % fm(P["d_ear"] - P["g_ear"], 0), 4, "ASME B30.26, WLL ≥ requerido por el núcleo (verificación «Orejas de izaje»)", "A DEFINIR POR CATÁLOGO"),
        ("Faldón de sello perimetral (opcional) y fleje", 1, "NBR 70 / S235 galvanizado; dimensiones por el proveedor (opcional)", "A DEFINIR POR CATÁLOGO"),
        ("Grasa grafitada NLGI 2 (≥ 10 % grafito, EP)", 1, ("Cantidad: llenado de ranuras + película de 0,3–0,5 mm por cara" if g.opt in (1, 3) and g.h_gr > 0 else "Cantidad: película de 0,3–0,5 mm sobre la cara de apoyo de la base y la cara inferior de la mesa"), "A DEFINIR POR CATÁLOGO"),
        ("Bomba, válvulas, mangueras y manómetro (circuito hidráulico)", 1, f"Fuera de los planos mecánicos: ver especificación en {CODE}-ACC-002-{REV}", "A DEFINIR POR CATÁLOGO"),
    ]
    if g.opt == 1:
        L.append(("Pasta de contacto/limpieza para discos inoxidables (opcional)", 1, "Cantidad según el proveedor", "A DEFINIR POR CATÁLOGO"))
    return L


SOBRE_MEC = 5.0     # sobremedida de mecanizado por cara/ancho mecanizado a cota [mm]


def rib_len(ctx, p):
    """Largo radial real de un tramo de nervio (proyección de sus vértices sobre la dirección radial del primer nervio)."""
    sol = ctx.shapes[p.key].Solids()[0] if p.key in ctx.shapes else p.solid.vals()[0].Solids()[0]
    cc = sol.Center()
    nr = math.hypot(cc.x, cc.y) or 1.0
    ur = (cc.x / nr, cc.y / nr)
    pr = [v.X * ur[0] + v.Y * ur[1] for v in sol.Vertices()]
    return max(pr) - min(pr)


def _env_plano(so):
    """Rectángulo envolvente mínimo (largo, ancho) de un sólido plano en planta (rotaciones de 1° y refinamiento de 0,1°)."""
    import cadquery as cq
    pts = [(v.X, v.Y) for v in so.Vertices()]
    best = None
    def ext(a):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        us = [x * ca + y * sa for x, y in pts]
        vs = [-x * sa + y * ca for x, y in pts]
        return (max(us) - min(us)) * (max(vs) - min(vs)), max(us) - min(us), max(vs) - min(vs)
    a0 = min(range(0, 180), key=lambda a: ext(a)[0])
    a1 = min([a0 + k / 10 for k in range(-10, 11)], key=lambda a: ext(a)[0])
    _, L, W = ext(a1)
    return (max(L, W), min(L, W))


def cut_rows(ctx):
    g, P, D, BR, KG = ctx.g, ctx.P, ctx.D, ctx.g.BR, ctx.g.KG
    m = ctx.m
    R = []

    def add(key, forma, dim, nota="", qty=None, mat=None):
        p = m.get(key)
        if p:
            R.append([p.code.replace(CODE + "-", ""), p.name[:34], forma, dim, str(qty if qty is not None else p.qty), (mat or p.material)[:44], nota])
    B, tb = g.B, g.tb
    add("base_plancha", "Plancha", f"{f(B + 10)}×{f(B + 10)}×{f(tb)}", "Sobremetal 5 por borde; planitud/planeado tras soldar")
    add("collar", "Disco", f"Ø{f(g.D_boss + 10)}×{f(g.h_boss + 5)}", f"De plancha de {f(g.h_boss + 5)}: caras planeadas a {f(g.h_boss)} y Ø{f(g.D_boss)} torneado; agujero tras soldar")
    L_ml, L_mc = ctx.m.info.get("marco_long") or (B, B - 2 * P["rim_t"])
    add("marco_largo", "Pletina", f"{f(P['rim_t'])}×{f(P['rim_h'])}×{fm(L_ml, 1)}")
    add("marco_corto", "Pletina", f"{f(P['rim_t'])}×{f(P['rim_h'])}×{fm(L_mc, 1)}")
    I = m.info.get("refuerzo")
    if I:
        T_ = I.get("tapones") or {}
        S_ = ((I.get("filetes") or {}).get("bordes_exteriores_PJP") or {}).get("S", 0)
        add("refuerzo", "Plancha", f"{fm(I['lado'], 0)}×{fm(I['lado'], 0)}×{f(I['t_d'])}",
            f"Corte CNC a medida (ISO 9013 clase 3, ±2; sin sobremetal: los cantos exteriores van al ras de la base); {T_.get('n_por_esquina', 0)} agujeros Ø{f(T_.get('d', 0))} taladrados; bisel 45° × {f(S_)} en 2 cantos (cara inferior)")
        AT_ = I.get("atiesadores") or {}
        if AT_.get("por_esquina"):
            add("refuerzo_ati", "Plancha", f"{f(AT_['largo'])}×{f(AT_['h'])}×{f(AT_['t'])}", "Corte CNC a medida; cantos a escuadra")
    zi_ = float(I["t"]) if (I and g.modo == 1) else tb
    if g.modo == 1:
        add("mensula_mejilla", "Plancha", f"{f(P['L_ch'])}×{f(tb + BR['H'] - zi_ + 5)}×{f(P['t_ch'])}")
        add("mensula_oreja_sup", "Plancha", f"{f(BR['Win'] + SOBRE_MEC)}×{f(BR['Llug'] + 5)}×{f(P['t_ch'])}", f"Ancho mecanizado a {f(BR['Win'])} −0,5 (sobremedida {fm(SOBRE_MEC, 0)}); agujero tras soldar")
        add("mensula_oreja_inf", "Plancha", f"{f(BR['Win'] + SOBRE_MEC)}×{f(BR['Llug'] + 5)}×{f(tb + BR['spacer'] + P['t_ch'] - zi_ + 2)}", f"Ancho mecanizado a {f(BR['Win'])} −0,5 y caras planeadas a {f(tb + BR['spacer'] + P['t_ch'] - zi_)}; agujero tras soldar")
    if g.modo == 2:
        S = g.FPV["soporte_E"]
        t_, L_, h_ = S["t_pared"], S["lado"], S["alto_paredes"]
        li_ = L_ - 2 * t_
        loc_ = {pz["id"]: pz for pz in S["piezas"]}

        def _d(pid):
            pz = loc_[pid]
            xs, ys = [q[0] for q in pz["poligono_local"]], [q[1] for q in pz["poligono_local"]]
            a, b = max(xs) - min(xs), max(ys) - min(ys)
            return max(a, b), min(a, b), pz["z"][1] - pz["z"][0]
        for k_, pid_ in (("cajon_pared_x", "pared_X"), ("cajon_pared_y", "pared_Y"), ("cajon_munon", "munon_X")):
            L_, t_, h_ = _d(pid_)
            add(k_, "Plancha", f"{fm(L_ + 5, 1)}×{f(h_ + 5)}×{f(t_)}", "Oxicorte; biseles 45° de las CJP (TC-U4b) según CON-007")
        add("cajon_tapa", "Plancha", f"{f(S['tapas']['lado'] + 5)}×{f(S['tapas']['lado'] + 5)}×{f(S['tapas']['t'])}", f"Corte CNC del polígono del núcleo (nariz); bisel 45° de la PJP; agujero Ø{f(S['tapas']['agujero_E'])} H9 en línea tras soldar")
    add("orejas", "Plancha", f"{f(2 * P['R_ear'] + 10)}×{f(P['h_ear'] + P['R_ear'] + 10)}×{f(P['t_ear'])}", "Plasma/oxicorte del perfil; agujero mecanizado H12")
    if g.modo == 1:
        add("bancada", "Plancha", f"{f(P['w_bed'] + 10)}×{f(P['t_bed'] + 5)}×{f(KG['L_bed'] + 10)}", "Ranura T tras soldar")
    add("mesa_plancha_sup", "Disco", f"Ø{f(2 * g.prIn + 5)}×{f(g.tt)}", "Plasma; rebaje tras soldar")
    add("mesa_anillo_sup", "4 × segm. de anillo 90°", f"Ø{f(P['D_top'] + 10)}/Ø{f(2 * g.prIn - 10)}×{f(g.tpr + 3)}", f"4 segmentos por anillo, empalmes CJP en la partida; caras planeadas a {f(g.tpr)} ANTES de soldar a la plancha superior", qty=4)
    add("mesa_plancha_inf", "Disco", f"Ø{f(2 * g.prIn + 5)}×{f(g.tbo + 3)}", "Cara de giro planeada" + (f"; agujero pasante Ø{f(g.Drb)} (rebaje del collar)" if g.rebaje else ""))
    add("mesa_anillo_inf", "4 × segm. de anillo 90°", f"Ø{f(P['D_top'] + 10)}/Ø{f(2 * g.prIn - 10)}×{f(g.tpr + 3)}", f"4 segmentos por anillo, empalmes CJP en la partida; se suelda en {f(g.tpr + 3)} y la cara inferior se planea a {f(g.tpr)} DESPUÉS de soldar (con la plancha inferior)", qty=4)
    for i, r in enumerate(D["almas"]):
        add(f"mesa_alma{i}", "Pletina rolada", f"{f(g.hw)}×{f(P['t_web'])}×{f(2 * math.pi * r + 20)}", f"R{f(r)}; 1 empalme CJP")
    for p in m.parts:
        if p.key.startswith("mesa_nervio"):
            L_ = rib_len(ctx, p)
            i_ = int(p.key[-1])
            hol = (m.info.get("nervio_holgura") or [2.0] * 9)[i_]
            R.append([p.code.replace(CODE + "-", ""), p.name, "Plancha e = %s (anidado GEN-010/013)" % f(P["t_rib"]), f"{fm(L_ + 4, 0)}×{f(g.hw + 4)}×{f(P['t_rib'])}", str(p.qty), p.material[:44],
                      f"largo de corte {fm(L_ + 4, 0)} = terminado {fm(L_, 0)} (entre caras del nervio; = entre caras de cubo/almas {fm(L_ + hol, 0)} − {fm(hol, 0)} de holgura) + 2 × 2 de sobremetal; destijeres 15 × 15"])
    add("mesa_cubo", "Anillo", f"Ø{f(P['D_hub'] + 10)}/Ø{f(g.d_bush - 10)}×{f(g.hw + 5)}")
    add("pasadores", "Barra", f"Ø{f(g.d_pin + 5)}×{f(g.hd + 6)}", ("Largo terminado = alto del disco (a ras, se esmerila después de soldar); sin rosca (núcleo pasadores_empuje)" if m.info.get("pasadores_empuje") else ""))
    add("arandela_pasador", "Disco", f"Ø{f(g.washer_D + 5)}×{f(g.washer_t + 2)}", f"Plancha de {f(g.washer_t + 2)}: caras rectificadas a {f(g.washer_t)}; agujero Ø{f(g.washer_d)}")
    add("pivote", "Barra", f"Ø{f(P['D_piv'] + 5)}×{f(g.L_piv + 6)}")
    add("buje", "Tubo/buje", f"Ø{f(g.d_bush + 4)}/Ø{f(P['D_piv'] - 4)}×{f(P['L_bush'] + 4)}")
    add("tapa_ret", "Disco", f"Ø{f(g.cap_D + 5)}×{f(g.cap_t + 2)}")
    add("tapa_insp", "Disco", f"Ø{f(g.cb_D + 3)}×{f(g.cb_t + 2)}")
    if g.modo == 1:
        add("patin", "Bloque", f"{f(KG['L_s'] + 10)}×{f(P['w_s'] + KG['inset'] + 10)}×{f(max(g.z_shoe, g.zc + P['dog_h'] / 2 + 10) - (g.zT0 + 1) + 10)}", "Una pieza")
        add("una", "Forja/bloque", f"{f(g.paw_L + 10)}×{f(P['dog_b'] + 10)}×{f(P['dog_h'] + 10)}", "Cara de empuje templada")
        add("pasador_vastago", "Barra", f"Ø{f(P['d_pp'] + 5)}×{fm(m.get('pasador_vastago').solid.val().BoundingBox().zlen + 10, 0)}")
        add("pasador_ojal", "Barra", f"Ø{f(P['d_pp'] + 5)}×{fm(m.get('pasador_ojal').solid.val().BoundingBox().zlen + 10, 0)}")
    for k_, forma_, nota_ in (("leva_riel", "Plancha", "42CrMo4+QT; contorno CNC con sobremetal 5; canto de leva fresado y templado"), ("leva_pata", "Plancha", "Caras fresadas"),
                              ("leva_tapa", "Plancha", "Caras fresadas; roscas tras soldar"), ("leva_prolong", "Plancha", "Oxicorte"), ("placa_leva_h", "Plancha", "Contorno CNC simétrico de ACC-020 (programa desde el JSON)"), ("placa_leva", "Plancha", "Contorno CNC (programa desde el JSON) con sobremetal 5 en el canto de contacto")):
        if m.get(k_):
            bb_ = m.get(k_).solid.vals()[0].Solids()[0].BoundingBox()
            dims_ = sorted([bb_.xlen, bb_.ylen, bb_.zlen], reverse=True)
            if k_ in ("leva_riel", "placa_leva", "placa_leva_h"):
                ss_ = m.get(k_).solid.vals()[0].Solids()[0]
                import cadquery as _cq
                c_ = ss_.Center()
                # envolvente del contorno en su propio plano (el sólido gira al rectángulo mínimo por el eje mayor de inercia)
                env_ = _env_plano(ss_)
                dims_ = [env_[0], env_[1], bb_.zlen]
            add(k_, forma_, f"{fm(dims_[0] + 10, 0)}×{fm(dims_[1] + 10, 0)}×{fm(dims_[2], 0)}", nota_)
    for k_, d_key in (("pasador_E", None), ("pasador_Q", None), ("leva_perno", None)):
        if m.get(k_):
            bb_ = m.get(k_).solid.vals()[0].Solids()[0].BoundingBox()
            add(k_, "Barra", f"Ø{fm(bb_.xlen + 5, 0)}×{fm(bb_.zlen + 6, 0)}", "Barra rectificada; corte y chaflanes en torno horizontal")
    if m.get("leva_rodillo"):
        bb_ = m.get("leva_rodillo").solid.vals()[0].Solids()[0].BoundingBox()
        add("leva_rodillo", "Barra", f"Ø{fm(bb_.xlen + 5, 0)}×{fm(bb_.zlen + 6, 0)}", "Torneado; temple y rectificado")
    if m.get("leva_arandela"):
        bb_ = m.get("leva_arandela").solid.vals()[0].Solids()[0].BoundingBox()
        add("leva_arandela", "Barra", f"Ø{fm(bb_.xlen + 5, 0)}×{fm(bb_.zlen + 4, 0)}", "Torneado; caras planas; agujero pasante")
    if m.get("bloque_una"):
        BU = g.FPV["bloque_una"]
        xs_ = [q[0] for k__ in ("cuerpo", "cara") for q in BU["contorno_local"][k__]] + [-BU["horquilla"]["R_cubo"], BU["horquilla"]["R_cubo"]]
        ys_ = [q[1] for k__ in ("cuerpo", "cara") for q in BU["contorno_local"][k__]] + [-BU["horquilla"]["R_cubo"], BU["horquilla"]["R_cubo"]]
        add("bloque_una", "Forja/bloque", f"{fm(max(xs_) - min(xs_) + 10, 0)}×{fm(max(ys_) - min(ys_) + 10, 0)}×{fm(BU['h'] + 10, 0)}", "Forja con certificado 3.1 (Re en la propia forja); cara templada y rectificada")
    if g.opt:
        th = 360.0 / g.n_sec
        env = f"{f(g.Ro - g.Ri * math.cos(math.radians(th / 2)) + 10)}×{f(2 * g.Ro * math.sin(math.radians(th / 2)) + 10)}"
        for k, nm in (("int_disco_base", "Sector (bruto rectangular envolvente)"), ("int_disco_mesa", "Sector (bruto rectangular envolvente)"), ("int_cara", "Sector (bruto rectangular envolvente)"), ("int_bronce", "Sector/pastilla (bruto envolvente)")):
            p = m.get(k)
            if p:
                t = p.solid.vals()[0].BoundingBox().zlen
                add(k, "Sector anular", f"{env}×{fm(t + 1, 1)}", "Corte por plasma de agua/láser; rectificado de caras (subcontrato)")
        lay = m.layout
        if m.has("int_tope_base") and "tope_h" in m.info:
            add("int_tope_base", "Barra", f"{fm(P['b_tope'], 0)}×{f(lay.L_base)}×{fm(m.info['tope_h'][0], 0)}", "altura = espesor del sector − retiro (cálculo); soldada con 2 filetes")
            add("int_tope_mesa", "Barra", f"{fm(P['b_tope'], 0)}×{f(lay.L_mesa)}×{fm(m.info['tope_h'][1], 0)}", "altura = espesor del sector − retiro (cálculo); soldada con 2 filetes")
        if m.has("int_tope_uhmw"):
            add("int_tope_uhmw", "Barra", f"{fm(P['b_tope'], 0)}×{f(m.info['uhmw_bar_L'])}×{fm(m.info['uhmw_bar_h'], 0)}", "largo = ancho radial − 100; altura = espesor de la lámina − retiro; inoxidable; 2 filetes")
        add("int_uhmw", "Sector", f"{env}×{fm(g.I['tuh'] + 1, 0)}", "CNC/plasma de agua")
    if g.wood:
        add("madera_anillo", "Pletina rolada", f"{fm(g.t_ring, 0)}×{f(P['t_wood'])}×{f(math.pi * (P['D_top'] - g.t_ring) + 20)}", "Adoptado por el mandante (S06); 1 empalme CJP")
    return R
