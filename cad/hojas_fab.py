"""Láminas de fabricación por elemento (A1). Las vistas salen del modelo 3D (HLR/cortes) y las cotas se verifican contra él."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_base import *


def title_view(s, p, t, esc):
    s.view_title(p, t, esc)


def despiece_tabla(ctx, s, x, y, keys, title="DESPIECE"):
    s.text(title, (x, y), 3.2, "TOP_LEFT", bold=True)
    rows = []
    for k in keys:
        p = ctx.m.get(k)
        if not p:
            continue
        rows.append([str(p.pos), p.code.replace(f"{CODE}-", ""), p.desc[:60], str(p.qty), p.material[:36], f(p.mass_unit, 1), ""])
    return s.table(x, y - 6, [("Pos", 7, "C"), ("Código", 23, "L"), ("Descripción", 78, "L"), ("Cant", 8, "C"), ("Material", 46, "L"), ("kg/u", 14, "R")], [r[:6] for r in rows], rh=4.6, h=1.8)


def procesos_tabla(ctx, s, x, y, keys):
    s.text("PROCESO DE FABRICACIÓN POR PIEZA (taller sin torno vertical)", (x, y), 3.0, "TOP_LEFT", bold=True)
    yy = y - 6
    for k in keys:
        p = ctx.m.get(k)
        if not p:
            continue
        lines = wrap(f"{p.code.replace(CODE + '-', '')} {p.name}: {p.process}" + (f" · {p.obs}" if p.obs else ""), 128)
        for ln in lines:
            s.text(ln, (x, yy), 1.9, "TOP_LEFT")
            yy -= 3.0
        yy -= 0.8
    return yy


def sheet_base(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    keys = ["base_plancha", "collar", "marco_largo", "marco_corto", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "orejas", "bancada"]
    keys = [k for k in keys if k in ctx.shapes]
    h = Hoja(ctx, "BAS", 1, "BASE SOLDADA: PLANCHA, COLLAR, MARCO, MÉNSULAS Y BANCADAS", "1:10 / 1:5 / 1:2",
             material="ASTM A572 Gr.50 (plancha base con Z35)", masa=f"{f(ctx.mass_of(*keys), 1)} kg (conj.)", trat="Alivio de tensiones 590–620 °C; Sa 2½")
    s = h.begin()
    B, tb, xg = g.B, g.tb, P["x_g"]
    V = View(s, ctx.sh(*keys), "top", (160, 428), 0.1, label="Planta")
    V.draw()
    s.line(V.P(-B / 2 - 60, 0, 0), V.P(B / 2 + 60, 0, 0), "EJE"); s.line(V.P(0, -B / 2 - 60, 0), V.P(0, B / 2 + 60, 0), "EJE")
    V.dim((-B / 2, -B / 2, 0), (B / 2, -B / 2, 0), -9, orient="h")
    V.dim((B / 2, -B / 2, 0), (B / 2, B / 2, 0), 12, orient="v")
    V.dim_dia((0, 0, 0), P["D_piv"] / 2, 215, text=f"Ø{f(P['D_piv'])} H7 (pasante)", ext=14)
    if g.boss:
        V.dim_dia((0, 0, tb), g.D_boss / 2, 40, text=f"Ø{f(g.D_boss)} (collar)", ext=14)
    s.text(f"Orejas de izaje IZA-001: centros en (±{f(P['x_lug'])}, ±{f(g.cl_lug)}), plano vertical radial hacia el centro.", (30, 268), 2.1)
    s.text(f"Ejes de guía en x = ±{f(xg)}; ménsulas de ambos sentidos de giro; marco {f(P['rim_t'])}×{f(P['rim_h'])}; cilindros, patines y uñas: ACC-001…005.", (30, 264), 2.1)
    title_view(s, (160, 278), "PLANTA DE LA BASE", "ESC 1:10")
    s.section_mark(V.P(-B / 2 - 40, 0, 0), 90, "A"); s.section_mark(V.P(B / 2 + 40, 0, 0), 90, "A")
    sec_keys = [k for k in ("base_plancha", "collar", "marco_largo", "marco_corto", "bancada") if k in ctx.shapes]
    VA = View(s, ctx.sh(*sec_keys), "front", (370, 500), 0.2, cut=((0, 0, 0), (0, 1, 0)), win=(-170, -40, 1300, 150), label="Corte A-A", hatch_scale=0.6)
    VA.draw()
    s.line(VA.P(0, 0, -15), VA.P(0, 0, 100), "EJE")
    VA.dim((900, 0, 0), (900, 0, tb), 8, orient="v", on=["base_plancha"])
    VA.dim((B / 2 - P["rim_t"], 0, tb + P["rim_h"]), (B / 2, 0, tb + P["rim_h"]), 10, orient="h", on=["marco_largo", "marco_corto"])
    VA.dim((B / 2, 0, tb), (B / 2, 0, tb + P["rim_h"]), 12, orient="v", on=["marco_largo", "marco_corto"])
    VA.dim((xg - P["w_bed"] / 2, 0, g.zb), (xg + P["w_bed"] / 2, 0, g.zb), 12, orient="h", on=["bancada"])
    VA.dim((xg + P["w_bed"] / 2, 0, tb), (xg + P["w_bed"] / 2, 0, g.zb), 8, orient="v", on=["bancada"])
    s.weld_iso(VA.P(B / 2 - P["rim_t"], 0, tb + 3), VA.P(B / 2 - 330, 0, 120), "fillet", f"z{fm(weld_by(ctx, 'Marco perimetral – plancha')['size'], 0)}", other=True, tail=["111/135 · ISO 5817-C", "WPS-01 A DEFINIR POR EL FABRICANTE"])
    s.weld_iso(VA.P(xg - P["w_bed"] / 2, 0, tb + 2), VA.P(xg - 460, 0, 70), "fillet", f"z{fm(P['w_bed_f'], 0)}", other=True, tail=["111/135 · ISO 5817-B", "WPS-03 A DEFINIR POR EL FABRICANTE"])
    s.finish((VA.P(xg - P["w_slot"] / 2 - 22, 0, g.zb)[0], VA.P(0, 0, g.zb)[1] + 6), "Ra 1,6")
    s.text(f"Cara superior de la plancha: planitud 0,20 en Ø{f(P['D_top'] + 20)} (ISO 1101)", (VA.P(-150, 0, 0)[0], VA.P(0, 0, -34)[1]), 2.1)
    title_view(s, (500, 462), "CORTE A-A (plano y = 0)", "ESC 1:5")
    VC = View(s, ctx.sh("base_plancha", "collar"), "front", (260, 190), 0.5, cut=((0, 0, 0), (0, 1, 0)), win=(-190, -22, 190, 95), label="Detalle collar", hatch_scale=0.4)
    VC.draw()
    s.line(VC.P(0, 0, -12), VC.P(0, 0, tb + g.h_boss + 14), "EJE")
    if g.boss:
        VC.dim((g.D_boss / 2, 0, tb + g.h_boss), (-g.D_boss / 2, 0, tb + g.h_boss), 10, orient="h", on=["collar"], prefix="Ø")
        VC.dim((P["D_piv"] / 2, 0, 0), (-P["D_piv"] / 2, 0, 0), -8, orient="h", on=["base_plancha"], text=f"Ø{f(P['D_piv'])} H7")
        VC.dim((g.D_boss / 2, 0, tb), (g.D_boss / 2, 0, tb + g.h_boss), 8, orient="v", on=["collar"])
        VC.dim((-g.D_boss / 2, 0, 0), (-g.D_boss / 2, 0, tb), -8, orient="v", on=["base_plancha"], outside=True)
        s.weld_iso(VC.P(g.D_boss / 2, 0, tb + 2), VC.P(g.D_boss / 2 + 50, 0, tb + 80), "fillet", f"z{fm(g.w_collar, 0)}", all_round=True, tail=["111/135 · ISO 5817-B", "WPS-04 A DEFINIR POR EL FABRICANTE"])
        s.finish((VC.P(0, 0, tb + g.h_boss)[0] + 14, VC.P(0, 0, tb + g.h_boss)[1] + 6), "Ra 1,6")
        s.gdt((60, 150), "perp", "0,05", "A")
        s.text("Agujero H7 pasante, mandrinado en línea (plancha + collar). Asiento del pivote = t_base + h_collar.", (60, 143), 2.0)
    title_view(s, (260, 128), "DETALLE DEL COLLAR DEL PIVOTE", "ESC 1:2")
    y = despiece_tabla(ctx, s, 648, 560, keys, "DESPIECE DE LA BASE (soldado)")
    y = procesos_tabla(ctx, s, 648, y - 8, keys)
    s.notes_block(648, y - 6, "NOTAS DE FABRICACIÓN", [
        "1. Soldar marco, collar, ménsulas, orejas y bancadas; alivio de tensiones; luego mecanizar.",
        f"2. Cara de apoyo de la interfaz (Ø{f(P['D_top'] + 20)}): planitud 0,20, Ra 1,6–3,2, sin pintura.",
        f"3. Agujero Ø{f(P['D_piv'])} H7: mandrinar plancha y collar en un montaje; perpendicularidad 0,05.",
        f"4. Orejas de ménsula: Ø{f(P['d_pp'])} H9 en línea tras soldar, coaxialidad 0,10; eje a {f(g.hax)} ±0,5 de la cara de apoyo.",
        f"5. Bancadas: filete {f(P['w_bed_f'])} continuo (precalentar 65 °C); ranura T mecanizada después de soldar y relevar.",
        "6. Pintura Sa 2½ + epóxico Zn 75 µm + epóxico 125 µm + PU 50 µm (ISO 12944 C4), salvo cara de apoyo, agujeros y orejas.",
        "7. END y tamaños de soldadura: programa de soldaduras TT300C-GEN-007-B.",
    ], h=1.9, wrap_chars=118)
    return h


# ======================================================================================================
def right_col(ctx, s, keys, y0=560, notas=(), titulo="DESPIECE", extra_proc=True, hn=1.9):
    y = despiece_tabla(ctx, s, 648, y0, keys, titulo)
    if extra_proc:
        y = procesos_tabla(ctx, s, 648, y - 8, keys)
    return s.notes_block(648, y - 6, "NOTAS DE FABRICACIÓN", list(notas) + notas_fab(ctx)[:4], h=hn, wrap_chars=118)


def sheet_mensula(ctx):
    g, P, BR, m = ctx.g, ctx.P, ctx.g.BR, ctx.m
    c = ctx.D["cilindros"]["horario"][0]
    E, ph = c["eye"], c["phiMean"]
    for k in ("mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf"):
        ctx.local(k, k + "_L", near=(E[0], E[1], 80), r=300, shift=(-E[0], -E[1], 0), rot=-ph)
    keys = ["mensula_mejilla_L", "mensula_oreja_sup_L", "mensula_oreja_inf_L"]
    h = Hoja(ctx, "BAS", 5, "MÉNSULA DE CILINDRO (CONJUNTO SOLDADO)", "1:1,25", material="ASTM A572 Gr.50", masa=f"{f(ctx.mass_of('mensula_mejilla', 'mensula_oreja_sup', 'mensula_oreja_inf') / m.get('mensula_oreja_sup').qty, 1)} kg c/u",
             trat="Alivio de tensiones")
    s = h.begin()
    tb, H_, rear, Llug, Win, Wout = g.tb, BR["H"], BR["rear"], BR["Llug"], BR["Win"], BR["Wout"]
    zt = tb + H_
    V = View(s, ctx.sh(*keys), "top", (170, 480), 0.8, center=(0, 0, 0), label="Planta"); V.draw()
    s.line(V.P(-rear - 20, 0, zt), V.P(P["L_ch"] - rear + 25, 0, zt), "EJE")
    V.dim((-rear, Wout / 2, zt), (P["L_ch"] - rear, Wout / 2, zt), 10, orient="h", on=["mensula_mejilla_L"])
    V.dim((-rear, Wout / 2, zt), (0, Wout / 2, zt), 18, orient="h", on=["mensula_mejilla_L"], text=f"{f(rear)}")
    V.dim((-rear, -Win / 2, zt), (Llug - rear, -Win / 2, zt), -9, orient="h", on=["mensula_oreja_sup_L"])
    V.dim((P["L_ch"] - rear, -Wout / 2, zt), (P["L_ch"] - rear, Wout / 2, zt), 10, orient="v", on=["mensula_mejilla_L"])
    V.dim((Llug - rear, -Win / 2, zt), (Llug - rear, Win / 2, zt), 8, orient="v", on=["mensula_oreja_sup_L"])
    V.dim_dia((0, 0, zt), P["d_pp"] / 2, 120, text=f"Ø{f(P['d_pp'])} H9", on=["mensula_oreja_sup_L"], ext=18)
    s.weld_iso(V.P(P["L_ch"] - rear - 30, Wout / 2, zt), V.P(P["L_ch"] - rear + 60, Wout / 2 + 110, zt), "fillet", f"z{fm(P['w_br'], 0)}", other=True, tail=["111/135 · ISO 5817-B", "WPS-02 A DEFINIR POR EL FABRICANTE"])
    title_view(s, (170, 380), "PLANTA", "ESC 1:1,25")
    VS = View(s, ctx.sh(*keys), "front", (170, 225), 0.8, cut=((0, 0, 0), (0, 1, 0)), label="Elevación", hatch_scale=0.35); VS.draw()
    s.line(VS.P(0, 0, tb - 10), VS.P(0, 0, zt + 15), "EJE")
    VS.dim((Llug - rear, 0, tb), (Llug - rear, 0, zt), 12, orient="v", on=["mensula_oreja_sup_L", "mensula_oreja_inf_L"])
    VS.dim((Llug - rear, 0, zt - P["t_ch"]), (Llug - rear, 0, zt), 24, orient="v", on=["mensula_oreja_sup_L"])
    VS.dim((Llug - rear, 0, tb), (Llug - rear, 0, tb + BR["spacer"] + P["t_ch"]), 24, orient="v", on=["mensula_oreja_inf_L"])
    VS.dim((-rear, 0, tb), (Llug - rear, 0, tb), -8, orient="h", on=["mensula_oreja_inf_L"])
    s.text(f"Eje del cilindro a {f(g.hax)} sobre la cara de apoyo (z = {f(g.zc)} desde la cara inferior de la base)", (30, 190), 2.1)
    title_view(s, (170, 200), "ELEVACIÓN (corte por el eje del ojal)", "ESC 1:1,25")
    VE = View(s, ctx.sh(*keys), "right", (480, 225), 0.8, label="Vista frontal"); VE.draw()
    VE.dim((0, -Wout / 2, tb), (0, Wout / 2, tb), -8, orient="h", on=["mensula_mejilla_L"])
    VE.dim((0, -Win / 2, zt), (0, Win / 2, zt), 8, orient="h", on=["mensula_oreja_sup_L"], text=f"{f(Win)}")
    VE.dim((0, Wout / 2, tb), (0, Wout / 2, zt), 10, orient="v", on=["mensula_mejilla_L"])
    VE.dim((0, Win / 2, zt - P["t_ch"]), (0, Wout / 2, zt - P["t_ch"]), -3, orient="h", on=["mensula_mejilla_L", "mensula_oreja_sup_L"], text=f"{f(P['t_ch'])}", outside=True) if False else None
    title_view(s, (480, 200), "VISTA FRONTAL", "ESC 1:1,25")
    s.gdt((250, 130), "coax", "Ø0,10", "A"); s.text("Agujeros Ø70 H9 de ambas orejas coaxiales entre sí (mecanizar en un mismo montaje tras soldar).", (250, 122), 2.0)
    s.gdt((250, 108), "par", "0,10", "B"); s.text("Eje del ojal paralelo a la guía de la bancada (referencia B = eje de la ranura T).", (250, 100), 2.0)
    s.finish((250, 75), "Ra 3,2 (agujeros H9)")
    right_col(ctx, s, ["mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf"], notas=[
        f"Se fabrican {P['n_br']:.0f} ménsulas (2 por sentido de giro). Mejillas {f(P['t_ch'])}; luz interior {f(Win)} para el cuerpo Ø{f(P['D_body'])}.",
        f"Saliente trasera {f(rear)} (desgarro de la oreja a calado). Holgura mejilla–ojal {fm(P['g_ch'], 1)}."])
    return h


def sheet_oreja(ctx):
    g, P = ctx.g, ctx.P
    x, y = g.ear_pos[0]
    ang = math.degrees(math.atan2(y, x))
    ctx.local("orejas", "oreja_L", near=(x, y, g.tb + 50), r=200, shift=(-x, -y, 0), rot=-ang)
    h = Hoja(ctx, "IZA", 1, "OREJA DE IZAJE (4 UNIDADES)", "1:1 / 1:10", material=f"ASTM A572 Gr.50, e = {fm(P['t_ear'], 0)}", masa=f"{f(ctx.m.get('orejas').mass_unit, 1)} kg c/u", trat="Sin tratamiento; protegida como la base")
    s = h.begin()
    tb, R, hE, tE, dE = g.tb, P["R_ear"], P["h_ear"], P["t_ear"], P["d_ear"]
    V = View(s, ctx.sh("oreja_L"), "front", (140, 340), 1.0, center=(0, 0, tb), label="Perfil"); V.draw()
    s.line(V.P(0, 0, tb - 10), V.P(0, 0, tb + hE + R + 15), "EJE"); s.line(V.P(-R - 15, 0, tb + hE), V.P(R + 15, 0, tb + hE), "EJE")
    V.dim((-R, tE / 2, tb), (R, tE / 2, tb), -10, orient="h", on=["oreja_L"], text=f"{f(2 * R)} (= 2R)")
    V.dim((R, tE / 2, tb), (R, tE / 2, tb + hE), 12, orient="v", on=["oreja_L"], text=f"{f(hE)} (centro del agujero)")
    V.dim_dia((0, tE / 2, tb + hE), dE / 2, 35, text=f"Ø{f(dE)}", on=["oreja_L"], ext=20)
    V.dim_rad((0, tE / 2, tb + hE), R, 125, text=f"R{f(R)}", on=["oreja_L"], ext=14)
    V.dim((0, tE / 2, tb), (0, tE / 2, tb + hE + R), -62, orient="v", on=["oreja_L"], text=f"{f(hE + R)} (altura total)", ) if False else None
    s.weld_iso(V.P(R - 2, tE / 2, tb + 2), V.P(R + 40, tE / 2, tb + 60), "fillet", f"z{fm(P['w_ear'], 0)}", other=True, tail=["111/135 · ISO 5817-B", "WPS-05 A DEFINIR POR EL FABRICANTE"])
    title_view(s, (140, 305), "PERFIL DE LA OREJA", "ESC 1:1")
    VT = View(s, ctx.sh("oreja_L"), "top", (140, 250), 1.0, center=(0, 0, tb), label="Planta"); VT.draw()
    VT.dim((0, -tE / 2, tb + hE), (0, tE / 2, tb + hE), 10, orient="v", on=["oreja_L"], text=f"{f(tE)}", outside=True) if False else None
    VT.dim((R, -tE / 2, tb + hE), (R, tE / 2, tb + hE), 12, orient="v", on=["oreja_L"], text=f"e = {f(tE)}")
    title_view(s, (140, 215), "PLANTA (espesor)", "ESC 1:1")
    keys = ["base_plancha", "orejas"]
    VB = View(s, ctx.sh(*keys), "top", (470, 400), 0.1, center=(g.B / 2 - 700, g.B / 2 - 700, 0), win=(-300, -300, 700, 700), label="Esquina de la base"); VB.draw()
    for (ex, ey) in g.ear_pos[:1]:
        s.line(VB.P(0, 0, tb), VB.P(ex, ey, tb), "FANT")
    cl = g.cl_lug
    VB.dim((x, g.B / 2, tb), (x, cl, tb), 12, orient="v", on=["base_plancha"], text=f"{f(P['c_lug'])} (al borde)")
    VB.dim((0, cl, tb), (x, cl, tb), -9 if False else 14, orient="h", on=["base_plancha"], text=f"{f(P['x_lug'])} (al eje y)")
    title_view(s, (470, 305), "UBICACIÓN (esquina de la base)", "ESC 1:10")
    s.text(f"Plano de la oreja vertical y radial hacia el centro de la base (ángulo atan(±{f(cl)}/±{f(x)}) = {fm(ang, 2)}° respecto de x en la oreja 1).", (300, 285), 2.1)
    s.text("Orejas en (±x_lug, ±(B/2 − c_lug)); distancia al borde c_lug; fuera del círculo de la mesa y dentro del marco.", (300, 281), 2.1)
    s.notes_block(300, 260, "PROCESO Y CONTROL", [
        "1. Corte a llama o plasma del perfil y del agujero Ø{0} (tolerancia ISO 2768-m; agujero H12 de corte, sin mecanizado: grillete con pasador ≤ d − 3).".format(fm(dE, 0)),
        "2. Biselado de la base de apoyo según WPS (preparación A DEFINIR POR EL FABRICANTE) y esmerilado de bordes del agujero.",
        f"3. Soldadura a la plancha base con filete z{fm(P['w_ear'], 0)} a ambos lados, longitud 2R = {f(2 * R)}; nivel ISO 5817-B.",
        "4. END: MT 100 % de la soldadura y UT 100 % antes de la prueba; MT de nuevo tras la prueba de carga (ver GEN-008).",
        f"5. Altura del centro del agujero {f(hE)} ±1 sobre la cara superior de la base; posición ±2.",
        f"6. Uso: eslinga de 4 ramales con grillete (WLL del núcleo: ver D['verificaciones'] «Orejas de izaje»); factor dinámico {fm(P['phi_lift'], 2)}.",
        "7. Rugosidad de corte Ra 12,5 (ISO 1302) aceptable; sin pintura en el agujero.",
    ], h=2.0, wrap_chars=110)
    right_col(ctx, s, ["orejas"], notas=["Las 4 orejas se sueldan sobre la plancha base; no hay otro punto de izaje de la base."], extra_proc=True)
    return h


def sheet_bancada(ctx):
    g, P, KG = ctx.g, ctx.P, ctx.g.KG
    X = P["x_g"]
    ctx.local("bancada", "bancada_L", near=(X, 0, 40), r=800, shift=(-X, 0, 0))
    h = Hoja(ctx, "ACC", 1, "BANCADA DE GUÍA CON RANURA T", "1:5 / 1:1", material="ASTM A572 Gr.50", masa=f"{f(ctx.m.get('bancada').mass_unit, 1)} kg c/u", trat="Alivio de tensiones antes de la ranura")
    s = h.begin()
    tb, zb = g.tb, g.zb
    V = View(s, ctx.sh("bancada_L"), "top", (110, 330), 0.2, center=(0, 0, zb), label="Planta"); V.draw()
    V.dim((P["w_bed"] / 2, -KG["Y_bed"], zb), (P["w_bed"] / 2, KG["Y_bed"], zb), 14, orient="v", on=["bancada_L"], n=2)
    V.dim((-P["w_bed"] / 2, -KG["Y_bed"], zb), (P["w_bed"] / 2, -KG["Y_bed"], zb), -9, orient="h", on=["bancada_L"])
    for wq in (P["w_slot"], P["w_tee"]):
        pass
    title_view(s, (110, 205), "PLANTA (ranura T pasante)", "ESC 1:5")
    VA = View(s, ctx.sh("bancada_L"), "front", (390, 400), 1.0, center=(0, 0, zb), cut=((0, 0, 0), (0, 1, 0)), win=(-100, -g.zb, 100, 20), label="Corte transversal", hatch_scale=0.35); VA.draw()
    s.line(VA.P(0, 0, tb - 6), VA.P(0, 0, zb + 14), "EJE")
    VA.dim((-P["w_bed"] / 2, 0, zb), (P["w_bed"] / 2, 0, zb), 22, orient="h", on=["bancada_L"])
    VA.dim((-P["w_slot"] / 2, 0, zb), (P["w_slot"] / 2, 0, zb), 10, orient="h", on=["bancada_L"], text=f"{f(P['w_slot'])} H8")
    VA.dim((-P["w_tee"] / 2, 0, g.zT0), (P["w_tee"] / 2, 0, g.zT0), -12, orient="h", on=["bancada_L"], text=f"{f(P['w_tee'])} +0,2/0")
    VA.dim((P["w_bed"] / 2, 0, tb), (P["w_bed"] / 2, 0, zb), 14, orient="v", on=["bancada_L"])
    VA.dim((P["w_slot"] / 2, 0, g.zT1), (P["w_slot"] / 2, 0, zb), 20 + (P["w_bed"] - P["w_slot"]) / 2 * 0, orient="v", on=["bancada_L"], text=f"{f(P['h_slot'])} +0,1/0") if False else None
    VA.dim((P["w_tee"] / 2, 0, g.zT0), (P["w_tee"] / 2, 0, g.zT1), 8, orient="v", on=["bancada_L"], text=f"{f(P['h_tee'])} +0,2/0")
    VA.dim((0, 0, tb), (0, 0, g.zT0), -22 if False else 4, orient="v", on=["bancada_L"], text=f"fondo {f(g.fondo)}", outside=True)
    s.weld_iso(VA.P(-P["w_bed"] / 2, 0, tb + 2), VA.P(-P["w_bed"] / 2 - 55, 0, tb - 40), "fillet", f"z{fm(P['w_bed_f'], 0)}", other=True, tail=["111/135 · ISO 5817-B", "WPS-03 A DEFINIR POR EL FABRICANTE"])
    s.finish((VA.P(P["w_slot"] / 2 + 3, 0, zb)[0], VA.P(0, 0, zb)[1] + 6), "Ra 1,6")
    s.gdt((300, 330), "par", "0,10", "A"); s.text("Ranura T paralela al eje Y en todo el largo (referencia A = eje de la bancada).", (300, 321), 2.0)
    s.gdt((300, 305), "pos", "Ø0,2", "A"); s.text("Posición de la ranura respecto del ojal de la ménsula (coaxial ±0,2).", (300, 296), 2.0)
    title_view(s, (390, 340), "CORTE TRANSVERSAL (ranura T)", "ESC 1:1")
    s.text(f"Ranura pasante: el patín entra por el extremo; lengüeta del patín: cuello {f(g.neck_w)} f7, cabeza {f(g.head_w)}×{f(g.head_h)} (ACC-002).", (300, 280), 2.0)
    right_col(ctx, s, ["bancada"], notas=[f"Largo {f(KG['L_bed'], 2)} = largo de carrera del patín; ranura mecanizada (fresado/cepillo) después de soldar y relevar; flancos con grasa grafitada."])
    return h


def sheet_patin(ctx):
    g, P, KG = ctx.g, ctx.P, ctx.g.KG
    c = ctx.D["cilindros"]["antihorario"][0]
    X, yr = c["x"], c["rodEngage"][1]
    ctx.local("patin", "patin_L", near=(X, yr + 200, g.zc), r=600, shift=(-X, -yr, 0))
    h = Hoja(ctx, "ACC", 2, "PATÍN GUIADO CON LENGÜETA T Y MARCO DE BOCA", "1:4 / 1:2,5", material=f"S460 (EN 10025-3) o 34CrNiMo6+QT, Fy ≥ {f(P['Fy_shoe'])} MPa",
             masa=f"{f(ctx.m.get('patin').mass_unit, 1)} kg c/u", trat="Sin soldadura; sin tratamiento (o QT del material)")
    s = h.begin()
    ws, rear, front, zsh, zb, zc = P["w_s"], KG["rear"], KG["front"], g.z_shoe, g.zb, g.zc
    yF = P["l_p"] - g.d_pin / 2           # cara de empuje de la uña (local)
    V = View(s, ctx.sh("patin_L"), "top", (150, 330), 0.4, center=(0, 100, zsh), hidden=True, label="Planta"); V.draw()
    s.line(V.P(0, -rear - 20, zsh), V.P(0, front + 20, zsh), "EJE")
    V.dim((ws / 2, -rear, zsh), (ws / 2, front, zsh), 14, orient="v", on=["patin_L"])
    V.dim((ws / 2, -rear, zsh), (ws / 2, 0, zsh), 30, orient="v", on=["patin_L"], text=f"{fm(rear, 1)}")
    V.dim((-ws / 2, -rear, zsh), (ws / 2, -rear, zsh), -8, orient="h", on=["patin_L"])
    V.dim_dia((0, 0, zsh), P["d_pp"] / 2, 20, text=f"Ø{f(P['d_pp'])} H9 (pasador del vástago)", on=["patin_L"], ext=40)
    s.text("Hacia el centro de la mesa: −x (izquierda).", (30, 120), 2.1)
    title_view(s, (150, 118), "PLANTA (alojamiento y ojal en trazo)", "ESC 1:2,5")
    yc = yF - P["dog_b"] / 2
    VF = View(s, ctx.sh("patin_L"), "front", (460, 400), 0.8, center=(0, 0, zb), cut=((0, yc, 0), (0, 1, 0)), win=(-190, -45, 130, 150), label="Corte F-F", hatch_scale=0.4); VF.draw()
    s.line(VF.P(0, yc, g.zT0 - 6), VF.P(0, yc, zsh + 14), "EJE")
    xm = KG["mouthX"] - X
    VF.dim((-ws / 2, yc, zsh), (ws / 2, yc, zsh), 12, orient="h", on=["patin_L"])
    VF.dim((ws / 2, yc, zb), (ws / 2, yc, zsh), 10, orient="v", on=["patin_L"], text=f"{f(g.Hs)} (sobre la bancada)")
    VF.dim((-g.neck_w / 2, yc, zb - 3), (g.neck_w / 2, yc, zb - 3), -10, orient="h", on=["patin_L"], text=f"{f(g.neck_w)} f7")
    VF.dim((-g.head_w / 2, yc, g.zT0 + 1), (g.head_w / 2, yc, g.zT0 + 1), -22, orient="h", on=["patin_L"], text=f"{f(g.head_w)} h11")
    VF.dim((g.head_w / 2, yc, g.zT0 + 1), (g.head_w / 2, yc, g.zT1 - 1), 10, orient="v", on=["patin_L"], text=f"{f(g.head_h)}", outside=True)
    VF.dim((g.neck_w / 2, yc, g.zT1 - 1), (g.neck_w / 2, yc, zb), 18, orient="v", on=["patin_L"], text=f"{f(g.neck_h)}", outside=True)
    pe = KG["pocketEnd"] - X
    VF.dim((pe + CL1, yc, g.pk_bot), (pe + CL1, yc, g.pk_top), 8, orient="v", on=["patin_L"], text=f"{f(P['dog_h'] + 2)} (alojamiento)")
    s.finish((VF.P(-ws / 2 + 10, yc, zsh)[0], VF.P(0, yc, zsh)[1] + 14), "Ra 1,6 (alojamiento y lengüeta)")
    title_view(s, (460, 300), "CORTE F-F (por el alojamiento de la uña)", "ESC 1:1,25")
    s.gdt((330, 250), "par", "0,05", "A"); s.text("Cara inferior de la lengüeta paralela a la cara de apoyo del patín (A = cara inferior de la caja).", (330, 242), 2.0)
    s.gdt((330, 228), "perp", "0,05", "A"); s.text("Alojamiento de la uña perpendicular a la cara de empuje.", (330, 220), 2.0)
    s.notes_block(330, 205, "ESPECIFICACIÓN", [
        f"Pieza única sin soldadura. Lengüeta T: cuello {f(g.neck_w)} f7 en ranura {f(P['w_slot'])} H8; cabeza {f(g.head_w)}×{f(g.head_h)} en {f(P['w_tee'])}×{f(P['h_tee'])}, juego 1 por lado.",
        f"Alojamiento de la uña {f(P['dog_b'] + 2)} H9 × {f(P['dog_h'] + 2)}; tapa {f(zsh - g.pk_top)} y fondo {f(g.pk_bot - zb)} sobre la bancada (mín. {f(P['t_pk'])}).",
        f"Marco de boca e = {f(P['t_fw'])} (paredes laterales); inset {f(KG['inset'])}; boca en x = {f(KG['mouthX'] - X)} desde el eje de la guía.",
        "Fabricación sin torno vertical: bloque de plancha gruesa a llama con sobremetal, desbaste y alojamientos en mandrinadora/fresado, Ø70 H9 en taladro radial.",
        "Dimensión de masa del núcleo: diferencias de fórmula declaradas en el informe de masas.",
    ], h=1.9, wrap_chars=95)
    right_col(ctx, s, ["patin"], notas=[f"Reacción de guía a calado {f(ctx.DV['Rguide'], 1)} kN (D['derivados'].Rguide); K guiado {fm(ctx.DV['Kguide'], 3)}."])
    return h


def sheet_una(ctx):
    g, P, KG = ctx.g, ctx.P, ctx.g.KG
    c = ctx.D["cilindros"]["antihorario"][0]
    yF = c["pinStart"][1] - c["dir"] * g.d_pin / 2
    ctx.local("una", "una_L", near=(KG["tipX"] + 100, yF - 40, g.zc), r=300, shift=(-KG["tipX"], -yF, 0))
    h = Hoja(ctx, "ACC", 3, "UÑA DE EMPUJE (CARA PLANA TEMPLADA, CHAFLÁN DE RETORNO)", "1:2,5", material=f"34CrNiMo6+QT (EN 10083-3), Re ≥ {f(P['Fy_dog'])} MPa (3.1)",
             masa=f"{f(ctx.m.get('una').mass_unit, 1)} kg c/u", trat=f"Temple inducción cara ≥ 55 HRC, prof. ≥ {fm(g.z_hard, 1)} mm")
    s = h.begin()
    L, b, hd_, zc = g.paw_L, P["dog_b"], P["dog_h"], g.zc
    zt = zc + hd_ / 2
    V = View(s, ctx.sh("una_L"), "top", (90, 450), 0.8, center=(0, -b / 2, zt), label="Planta"); V.draw()
    s.line(V.P(-15, -b / 2, zt), V.P(L + 15, -b / 2, zt), "EJE")
    V.dim((0, 0, zt), (L, 0, zt), 10, orient="h", on=["una_L"])
    V.dim((L, -b, zt), (L, 0, zt), 12, orient="v", on=["una_L"], text=f"{f(b)} f8")
    V.dim((0, -b + g.ch_dy, zt), (g.ch_dx, -b, zt), -10, orient="h", on=["una_L"], text=f"Δx {fm(g.ch_dx, 1)}")
    V.dim((g.ch_dx, -b, zt), (g.ch_dx, -b + g.ch_dy, zt), -22 if False else 8, orient="v", on=["una_L"], text=f"Δy {fm(g.ch_dy, 1)}", outside=True) if False else None
    V.dim((0, -b + g.ch_dy, zt), (0, 0, zt), -12, orient="v", on=["una_L"], text=f"{fm(b - g.ch_dy, 1)} (punta)")
    V.dim((0, -b, zt), (0, -b + g.ch_dy, zt), -26, orient="v", on=["una_L"], text=f"Δy {fm(g.ch_dy, 1)}", outside=True) if False else None
    s.text(f"Chaflán de retorno β = {fm(P['beta_ch'], 0)}° (normal respecto del eje radial). Pasador Ø{f(g.d_pin)} toma la cara plana a {f(P['c_tip'])} de la punta.", (30, 372), 2.1)
    s.finish((V.P(L * 0.5, 0, zt)[0], V.P(0, 0, zt)[1] + 4), "Ra 0,8 (cara de empuje)")
    s.gdt((30, 355), "flat", "0,05"); s.text("Cara de empuje plana: planitud 0,05; alivio de borde (bombeo) 10 mm en ambos extremos, caída 0,02–0,03 (ISO 1101).", (62, 357), 2.0)
    s.line(V.P(0, 5, zt), V.P(L, 5, zt), "TRAT")
    s.text(f"Zona templada por inducción (trazo-punto grueso): cara de empuje completa, ≥ 55 HRC, prof. efectiva ≥ {fm(g.z_hard, 1)} mm", (30, 345), 2.0)
    title_view(s, (130, 395), "UÑA – PLANTA", "ESC 1:1,25")
    VE = View(s, ctx.sh("una_L"), "front", (90, 270), 0.8, center=(0, 0, zc), label="Elevación"); VE.draw()
    VE.dim((L, 0, zc - hd_ / 2), (L, 0, zc + hd_ / 2), 12, orient="v", on=["una_L"], text=f"{f(hd_)} f8")
    VE.dim((0, 0, zc + hd_ / 2), (L, 0, zc + hd_ / 2), 10, orient="h", on=["una_L"], text=f"{fm(L, 1)}")
    title_view(s, (130, 215), "UÑA – ELEVACIÓN (cara de empuje)", "ESC 1:1,25")
    s.notes_block(330, 440, "ESPECIFICACIÓN", [
        f"34CrNiMo6+QT, Re ≥ {f(P['Fy_dog'])} MPa en probeta de la propia forja, certificado 3.1; núcleo 280–330 HB; UT EN 10228-3 clase 3.",
        f"Temple por inducción de la cara de empuje ≥ 55 HRC (Fy superficial ≥ {f(P['Fy_surf'])} MPa), profundidad efectiva ≥ {fm(g.z_hard, 1)} mm (550 HV); revenido 180 °C; MT de la cara.",
        "Rectificar la cara templada después del temple (rectificadora plana o esmerilado de precisión; sin torno).",
        f"Ajuste en el alojamiento del patín: {f(b)} H9/f8 × {f(hd_)} H9/f8; retorno radial {fm(KG['travel'], 1)} mm.",
        f"Resorte de retorno: compresión, carrera ≥ {f(KG['travel'] + 5)} mm, fuerza 150–300 N; comercial (A DEFINIR POR CATÁLOGO).",
        "Aristas 1×45° salvo la cara de empuje (0,5×45°). Tolerancias ISO 2768-m. Proceso: bloque forjado, fresado en mandrinadora/fresadora.",
    ], h=1.9, wrap_chars=110)
    right_col(ctx, s, ["una"], notas=[f"Dureza y profundidad de temple: control 100 % de las uñas (GEN-008, punto 12)."])
    return h


def sheet_art(ctx):
    g, P, BR, KG = ctx.g, ctx.P, ctx.g.BR, ctx.g.KG
    c = ctx.D["cilindros"]["antihorario"][0]
    X, ye, yr = c["x"], c["eye"][1], c["rodEngage"][1]
    ctx.local("pasador_vastago", "pv_L", near=(X, yr, g.zc), r=100, shift=(-X, -yr, 0))
    ctx.local("pasador_ojal", "po_L", near=(X, ye, g.zc), r=100, shift=(-X, -ye, 0))
    ctx.local("cilindro", "cil_L", near=(X, (ye + yr) / 2, g.zc), r=700, shift=(-X, -ye, 0))
    h = Hoja(ctx, "ACC", 4, "PASADORES DE ARTICULACIÓN, CILINDRO HIDRÁULICO Y ESPECIFICACIÓN", "1:2 / 1:5", material=f"42CrMo4+QT (pasadores); cilindro comercial", masa=f"{f(ctx.mass_of('cilindro'), 1)} kg (2 cil.)", trat="Bonificado 28–34 HRC (pasadores)")
    s = h.begin()
    zb, d_pp = g.zb, P["d_pp"]
    Lv = ctx.m.get("pasador_vastago").solid.val().BoundingBox().zlen
    Lo = ctx.m.get("pasador_ojal").solid.val().BoundingBox().zlen
    z0v = max(zb, g.zc - g.forkH / 2 - 10)
    for i, (key, nm, z0, L) in enumerate((("pv_L", "PASADOR DEL VÁSTAGO (PATÍN)", z0v, Lv), ("po_L", "PASADOR DEL OJAL TRASERO (MÉNSULA)", g.tb, Lo))):
        ox = 80 + i * 130
        V = View(s, ctx.sh(key), "front", (ox, 430), 0.7, center=(0, 0, z0), label=nm); V.draw()
        s.line(V.P(0, 0, z0 - 8), V.P(0, 0, z0 + L + 8), "EJE")
        V.dim((-d_pp / 2, 0, z0), (d_pp / 2, 0, z0), -8, orient="h", on=[key], text=f"Ø{f(d_pp)} f8")
        V.dim((d_pp / 2, 0, z0), (d_pp / 2, 0, z0 + L), 8, orient="v", on=[key], text=f"{fm(L, 1)}")
        title_view(s, (ox, 330 if False else 345), nm.split("(")[0].strip(), "ESC 1:1,5")
    s.text("Ambos: Ra 0,8 en Ø; chaflanes 2×45°; retención con placa y tornillo (A DEFINIR POR CATÁLOGO).", (30, 315), 2.0)
    s.finish((200, 300), "Ra 0,8")
    # cilindro
    V = View(s, ctx.sh("cil_L"), "top", (110, 200), 0.25, center=(0, (yr - ye) / 2, g.zc), label="Cilindro"); V.draw()
    s.line(V.P(0, -80, g.zc), V.P(0, yr - ye + 80, g.zc), "EJE")
    V.dim((-P["D_body"] / 2, 220, g.zc), (P["D_body"] / 2, 220, g.zc), 12 if False else -14, orient="h", on=["cil_L"], text=f"Ø{f(P['D_body'])} (cuerpo)") if False else None
    V.dim((0, 0, g.zc), (0, yr - ye, g.zc), 70, orient="v", on=["cil_L"], virt_a=d_pp / 2, virt_b=d_pp / 2, text=f"{fm(yr - ye, 1)} (ojal–ojal en toma)") if False else None
    title_view(s, (110, 105), "CILINDRO (vista en planta, posición de toma)", "ESC 1:4")
    spec = [["Cilindros", f"{P['n_cyl']:.0f} × doble efecto, Ø{f(P['D_bore'])}/Ø{f(P['d_rod'])}, carrera {f(P['stroke'])}, clase {f(P['p_rated'])} psi"],
            ["Presión máxima de trabajo", f"{fm(P['p_rated'] * 0.0689476, 0)} bar (p_rated {f(P['p_rated'])} psi); alivio {f(P['p_relief'])} bar; alarma {f(P['p_alarm'])} bar; retorno {f(P['p_ret'])} bar"],
            ["Largo ojal–ojal retraído", f"{f(P['L0'])} mm (A CONFIRMAR con el proveedor)"], ["Ojales", f"rótula esférica, pasador Ø{f(d_pp)}, ancho {f(P['b_eye'])}"],
            ["Masa por cilindro", f"{f(P['m_cyl'])} kg (catálogo A DEFINIR)"], ["Fuerza a calado / área", f"{f(ctx.DV['Fstall'], 1)} kN / {f(ctx.DV['A'])} mm²"],
            ["Bomba", f"{fm(P['Q_pump'], 1)} L/min; tiempo por vuelta {fm(ctx.DV['tRev'], 1)} min (D['derivados'].tRev); ciclo {fm(ctx.DV['tCycle'], 2)} min"],
            ["Circuito", "paralelo con colector común y válvula de bloqueo; prohibido operar con un solo cilindro"],
            ["Código de catálogo", "A DEFINIR POR CATÁLOGO (no se inventan códigos)"]]
    s.table(330, 330, [("Ítem", 60, "L"), ("Valor", 250, "L")], spec, rh=5.2, h=2.0)
    right_col(ctx, s, ["pasador_vastago", "pasador_ojal", "cilindro"], notas=["Pasadores de articulación comerciales rectificados f8; no se sueldan (42CrMo4)."])
    return h
