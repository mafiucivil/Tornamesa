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
    L = [
        ("Resorte de retorno de la uña (compresión)", n, f"Comercial; carrera ≥ {f(g.KG['travel'] + 5)} mm, fuerza 150–300 N", "A DEFINIR POR CATÁLOGO"),
        (f"Tornillo ISO 10642 M10×{g.cap_L:.0f} cl. 10.9 (tapa retenedora)", 4, "10.9", "A DEFINIR POR CATÁLOGO"),
        (f"Tornillo ISO 10642 M{fm(g.insp_d, 0)}×{g.insp_L} cl. 10.9 (tapa de inspección)", 6, "10.9", "A DEFINIR POR CATÁLOGO"),
        ("Placa y tornillo de retención de pasador de articulación", 2 * n, "S355J2 / 8.8", "A DEFINIR POR CATÁLOGO"),
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
    add("marco_largo", "Pletina", f"{f(P['rim_t'])}×{f(P['rim_h'])}×{f(B)}")
    add("marco_corto", "Pletina", f"{f(P['rim_t'])}×{f(P['rim_h'])}×{f(B - 2 * P['rim_t'])}")
    add("mensula_mejilla", "Plancha", f"{f(P['L_ch'])}×{f(BR['H'] + 5)}×{f(P['t_ch'])}")
    add("mensula_oreja_sup", "Plancha", f"{f(BR['Win'] + SOBRE_MEC)}×{f(BR['Llug'] + 5)}×{f(P['t_ch'])}", f"Ancho mecanizado a {f(BR['Win'])} −0,5 (sobremedida {fm(SOBRE_MEC, 0)}); agujero tras soldar")
    add("mensula_oreja_inf", "Plancha", f"{f(BR['Win'] + SOBRE_MEC)}×{f(BR['Llug'] + 5)}×{f(BR['spacer'] + P['t_ch'] + 2)}", f"Ancho mecanizado a {f(BR['Win'])} −0,5 y caras planeadas a {f(BR['spacer'] + P['t_ch'])}; agujero tras soldar")
    add("orejas", "Plancha", f"{f(2 * P['R_ear'] + 10)}×{f(P['h_ear'] + P['R_ear'] + 10)}×{f(P['t_ear'])}", "Plasma/oxicorte del perfil; agujero mecanizado H12")
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
    add("pasadores", "Barra", f"Ø{f(g.d_pin + 5)}×{f(g.hd + 6)}")
    add("arandela_pasador", "Disco", f"Ø{f(g.washer_D + 5)}×{f(g.washer_t + 2)}", f"Plancha de {f(g.washer_t + 2)}: caras rectificadas a {f(g.washer_t)}; agujero Ø{f(g.washer_d)}")
    add("pivote", "Barra", f"Ø{f(P['D_piv'] + 5)}×{f(g.L_piv + 6)}")
    add("buje", "Tubo/buje", f"Ø{f(g.d_bush + 4)}/Ø{f(P['D_piv'] - 4)}×{f(P['L_bush'] + 4)}")
    add("tapa_ret", "Disco", f"Ø{f(g.cap_D + 5)}×{f(g.cap_t + 2)}")
    add("tapa_insp", "Disco", f"Ø{f(g.cb_D + 3)}×{f(g.cb_t + 2)}")
    add("patin", "Bloque", f"{f(KG['L_s'] + 10)}×{f(P['w_s'] + KG['inset'] + 10)}×{f(max(g.z_shoe, g.zc + P['dog_h'] / 2 + 10) - (g.zT0 + 1) + 10)}", "Una pieza")
    add("una", "Forja/bloque", f"{f(g.paw_L + 10)}×{f(P['dog_b'] + 10)}×{f(P['dog_h'] + 10)}", "Cara de empuje templada")
    add("pasador_vastago", "Barra", f"Ø{f(P['d_pp'] + 5)}×{fm(m.get('pasador_vastago').solid.val().BoundingBox().zlen + 10, 0)}")
    add("pasador_ojal", "Barra", f"Ø{f(P['d_pp'] + 5)}×{fm(m.get('pasador_ojal').solid.val().BoundingBox().zlen + 10, 0)}")
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
