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


# ======================================================================================================
MESA_KEYS = ["mesa_plancha_sup", "mesa_anillo_sup", "mesa_plancha_inf", "mesa_anillo_inf", "mesa_cubo", "pasadores"]


def mesa_keys(ctx):
    k = ["mesa_plancha_sup", "mesa_anillo_sup", "mesa_plancha_inf", "mesa_anillo_inf"] + [p.key for p in ctx.m.parts if p.key.startswith("mesa_alma")] + \
        [p.key for p in ctx.m.parts if p.key.startswith("mesa_nervio")] + ["mesa_cubo", "pasadores"]
    return [x for x in k if x in ctx.shapes]


def sheet_mesa(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    keys = mesa_keys(ctx)
    h = Hoja(ctx, "MES", 1, "MESA GIRATORIA: CONJUNTO SOLDADO (PLANTA Y CORTE RADIAL)", "1:10 / 1:4 / 1:2", material="ASTM A572 Gr.50 Z35 (planchas); pasadores 34CrNiMo6+QT",
             masa=f"{f(ctx.mass_of(*keys), 1)} kg", trat="Alivio de tensiones; temple de pasadores")
    s = h.begin()
    z0, hd, tb = g.z0, g.hd, g.tb
    zmid = z0 + g.tbo + g.hw / 2
    V = View(s, ctx.sh(*keys), "top", (160, 440), 0.1, center=(0, 0, zmid), cut=((0, 0, zmid), (0, 0, -1)), label="Planta (corte horizontal)", hatch_scale=0.8); V.draw()
    s.line(V.P(-g.Rt - 50, 0, zmid), V.P(g.Rt + 50, 0, zmid), "EJE"); s.line(V.P(0, -g.Rt - 50, zmid), V.P(0, g.Rt + 50, zmid), "EJE")
    V.dim_dia((0, 0, z0), g.Rt, 130, text=f"Ø{f(P['D_top'])}", on=["mesa_anillo_inf"], ext=20)
    V.dim_dia((0, 0, z0), g.prIn, 215, text=f"Ø{f(2 * g.prIn)} (límite de anillos)", on=["mesa_anillo_inf"], ext=20)
    a0 = D["pasadores"][0]
    pa = polar(g.R_pin, a0)
    V.dim((0, 0, z0), (pa[0], pa[1], z0), 20 if False else 0.01, orient="a", on=["mesa_cubo", "pasadores"], virt_a=g.d_bush / 2, virt_b=g.d_pin / 2, text=f"R{f(g.R_pin)}") if False else None
    s.text(f"{g.N_pin} pasadores Ø{f(g.d_pin)} m6 en R{f(g.R_pin)} (PCD Ø{f(2 * g.R_pin)} ±0,3); el primero a {fm(a0, 3)}° del eje x; paso {fm(360 / g.N_pin, 3)}° (±0,05°).", (30, 288), 2.1)
    s.text(f"{int(P['N_rib'])} nervios e={f(P['t_rib'])} a {fm(360 / P['N_rib'], 2)}°; almas anulares e={f(P['t_web'])} en R " + " / ".join(f(r) for r in D["almas"]) + f"; cubo Ø{f(P['D_hub'])}/Ø{f(g.d_bush)}.", (30, 284), 2.1)
    title_view(s, (160, 296), "PLANTA (corte a media altura de las almas)", "ESC 1:10")
    # corte radial por un pasador (mesa girada para llevarlo al eje x)
    rk = ctx.rotated(keys, -a0)
    VR = View(s, ctx.sh(*rk), "front", (60, 190), 0.25, center=(0, 0, z0), cut=((0, 0, 0), (0, 1, 0)), win=(-10, -10, g.Rt + 20, hd + 20), label="Corte radial", hatch_scale=0.5); VR.draw()
    s.line(VR.P(0, 0, z0 - 8), VR.P(0, 0, z0 + hd + 15), "EJE")
    VR.dim((g.Rt, 0, z0), (g.Rt, 0, z0 + hd), 8, orient="v", on=[k + "_r" for k in keys])
    VR.dim((g.prIn, 0, z0 + hd), (g.Rt, 0, z0 + hd), 10, orient="h", on=[k + "_r" for k in keys])
    VR.dim((g.Rt - 5, 0, z0), (g.Rt - 5, 0, z0 + g.tpr), -8 if False else 14, orient="v", on=["mesa_anillo_inf_r"], text=f"{f(g.tpr)}", outside=True) if False else None
    VR.dim((g.prIn - 20, 0, z0), (g.prIn - 20, 0, z0 + g.tbo), -10, orient="v", on=["mesa_plancha_inf_r"], text=f"{f(g.tbo)}", outside=True)
    VR.dim((g.cb_D / 2 + 10, 0, z0 + hd - g.tt), (g.cb_D / 2 + 10, 0, z0 + hd), 12, orient="v", on=["mesa_plancha_sup_r"], text=f"{f(g.tt)}", outside=True)
    s.weld_iso(VR.P(g.prIn, 0, z0 + g.tbo), VR.P(g.prIn - 120, 0, z0 - 20), "cjp", f"t={fm(g.tbo, 0)}", tail=["111/135 · ISO 5817-B · UT", "WPS-06 A DEFINIR POR EL FABRICANTE"])
    title_view(s, (140, 100), "CORTE RADIAL (por un pasador)", "ESC 1:4")
    VP = View(s, ctx.sh(*rk), "front", (480, 190), 0.8, center=(g.R_pin, 0, z0), cut=((0, 0, 0), (0, 1, 0)), win=(-80, -12, 80, hd + 40), label="Detalle pasador", hatch_scale=0.35,
              nocut=()); VP.draw()
    VP.dim((g.R_pin - g.d_pin / 2, 0, z0), (g.R_pin + g.d_pin / 2, 0, z0), -8, orient="h", on=["pasadores_r"], text=f"Ø{f(g.d_pin)} m6 / H7")
    VP.dim((g.R_pin + g.d_pin / 2, 0, z0), (g.R_pin + g.d_pin / 2, 0, z0 + hd), 10, orient="v", on=["pasadores_r"], text=f"{f(hd)} −0,5/0")
    VP.dim((g.R_pin + g.d_pin / 2, 0, z0 + g.tpr), (g.R_pin + g.d_pin / 2, 0, z0 + hd - g.tpr), 24, orient="v", on=["pasadores_r"], text=f"{f(g.pinClear if hasattr(g, 'pinClear') else hd - 2 * g.tpr)} (luz entre anillos)") if False else None
    s.finish((VP.P(g.R_pin - 60, 0, z0)[0], VP.P(0, 0, z0)[1] - 18), "Ra 1,6 (cara inferior)")
    title_view(s, (480, 105), "DETALLE: PASADOR DE EMPUJE", "ESC 1:1,25")
    y = despiece_tabla(ctx, s, 648, 560, [k for k in keys if not k.startswith("mesa_nervio")][:12] + [k for k in keys if k.startswith("mesa_nervio")], "DESPIECE DE LA MESA")
    s.notes_block(648, y - 8, "NOTAS DE FABRICACIÓN", [
        "1. Secuencia: almas y nervios sobre la plancha inferior → cubo → anillo inferior → plancha superior por cuadrantes opuestos → anillo superior.",
        "2. Alivio de tensiones 590–620 °C antes del mecanizado final.",
        f"3. Cara inferior (plancha + anillo): planeado en mandrinadora (fresa de planear) o esmerilado, planitud 0,20 en Ø{f(P['D_top'])}, Ra 1,6–3,2; paralelismo cara superior 0,30.",
        f"4. Cubo Ø{f(g.d_bush)} H7 y rebaje Ø{f(g.D_boss)} en mandrinadora, perpendicular a la cara inferior 0,05; buje con ajuste s6/H7.",
        f"5. {g.N_pin} agujeros Ø{f(g.d_pin)} H7 en ambos anillos en un solo montaje (taladro radial Ø80 + mandrinado), PCD ±0,3, paso ±0,05°.",
        "6. Planchas UT ASTM A578 nivel B antes de cortar. Sin pintura en la cara inferior, agujeros y alojamientos.",
        "7. Puntos de izaje de la mesa: NO definidos en el cálculo (supuesto S13): izar con medios del montajista.",
        "8. Programa de soldaduras: GEN-007. Lista de corte: GEN-006.",
    ], h=1.9, wrap_chars=118)
    return h


def sheet_mesa_plan(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    h = Hoja(ctx, "MES", 2, "PLANCHAS Y ANILLOS DE LA MESA (SUPERIOR E INFERIOR)", "1:10 / 1:2", material="ASTM A572 Gr.50 Z35, UT A578 B",
             masa=f"{f(ctx.mass_of('mesa_plancha_sup', 'mesa_anillo_sup', 'mesa_plancha_inf', 'mesa_anillo_inf'), 1)} kg", trat="Alivio de tensiones")
    s = h.begin()
    z0, hd = g.z0, g.hd
    ztop = z0 + hd
    ya = 430
    V1 = View(s, ctx.sh("mesa_plancha_sup", "mesa_anillo_sup"), "top", (130, ya), 0.1, center=(0, 0, ztop), label="Superior"); V1.draw()
    V1.dim_dia((0, 0, ztop), g.Rt, 130, text=f"Ø{f(P['D_top'])}", on=["mesa_anillo_sup"], ext=18)
    V1.dim_dia((0, 0, ztop), g.hole_top / 2, 60, text=f"Ø{f(g.hole_top)}", on=["mesa_plancha_sup"], ext=40)
    V1.dim_dia((0, 0, ztop), g.cb_D / 2, 20, text=f"Ø{f(g.cb_D)}×{f(g.cb_t)} (rebaje)", on=["mesa_plancha_sup"], ext=60)
    for k in range(4):
        a = math.radians(90 * k)
        s.line(V1.P(g.prIn * math.cos(a), g.prIn * math.sin(a), ztop), V1.P(g.Rt * math.cos(a), g.Rt * math.sin(a), ztop), "FANT")
    title_view(s, (130, ya - 118), "PLANCHA SUPERIOR + ANILLO", "ESC 1:10")
    V2 = View(s, ctx.sh("mesa_plancha_inf", "mesa_anillo_inf"), "bottom", (400, ya), 0.1, center=(0, 0, z0), label="Inferior"); V2.draw()
    V2.dim_dia((0, 0, z0), g.prIn, 40, text=f"Ø{f(2 * g.prIn)}", on=["mesa_plancha_inf"], ext=22)
    if g.boss:
        V2.dim_dia((0, 0, z0), g.D_boss / 2, 120, text=f"Ø{f(g.D_boss)} (rebaje del collar)", on=["mesa_plancha_inf"], ext=40)
    title_view(s, (400, ya - 118), "PLANCHA INFERIOR + ANILLO (vista desde abajo)", "ESC 1:10")
    a0 = D["pasadores"][0]
    rk = ctx.rotated(["mesa_plancha_sup", "mesa_anillo_sup", "mesa_plancha_inf", "mesa_anillo_inf", "pasadores"], -a0)
    VR = View(s, ctx.sh(*rk), "front", (120, 175), 0.5, center=(g.prIn + 40, 0, z0), cut=((0, 0, 0), (0, 1, 0)), win=(-160, -12, 200, hd + 20), label="Empalme anillo-plancha", hatch_scale=0.4); VR.draw()
    VR.dim((g.prIn, 0, z0), (g.Rt, 0, z0), -9 if False else -10, orient="h", on=["mesa_anillo_inf_r"], text=f"{fm(g.Rt - g.prIn, 0)} (ancho del anillo)") if False else None
    VR.dim((g.prIn - 30, 0, z0), (g.prIn - 30, 0, z0 + g.tbo), -6, orient="v", on=["mesa_plancha_inf_r"], text=f"{f(g.tbo)}", outside=True)
    VR.dim((g.prIn + 10, 0, z0), (g.prIn + 10, 0, z0 + g.tpr), 8, orient="v", on=["mesa_anillo_inf_r"], text=f"{f(g.tpr)}", outside=True)
    VR.dim((g.prIn - 30, 0, z0 + g.hd - g.tt), (g.prIn - 30, 0, z0 + g.hd), -6, orient="v", on=["mesa_plancha_sup_r"], text=f"{f(g.tt)}", outside=True)
    s.weld_iso(VR.P(g.prIn, 0, z0 + g.tbo), VR.P(g.prIn - 100, 0, z0 - 25), "cjp", f"t={fm(g.tbo, 0)}", tail=["111/135 · ISO 5817-B · UT 100 %", "WPS-06 A DEFINIR POR EL FABRICANTE"])
    s.text(f"Transición de espesor {f(g.tbo)} → {f(g.tpr)}: rebajar el anillo 1:4 en la unión con la plancha (CJP en V 60°, raíz 3, con respaldo).", (30, 110), 2.0)
    title_view(s, (120, 125), "CORTE: EMPALME ANILLO–PLANCHA (inferior)", "ESC 1:2")
    s.gdt((310, 150), "flat", "0,20"); s.text(f"Cara inferior de la mesa: planitud 0,20 en Ø{f(P['D_top'])}", (342, 152), 2.0)
    s.gdt((310, 135), "par", "0,30", "A"); s.text("Cara superior paralela a la inferior (A = cara inferior)", (342, 137), 2.0)
    s.gdt((310, 120), "pos", "Ø0,10", "A"); s.text(f"Agujeros Ø{f(g.d_pin)} H7 de ambos anillos: posición ±0,05° y coaxialidad entre anillos 0,05", (342, 122), 2.0)
    s.finish((310, 95), "Ra 1,6")
    right_col(ctx, s, ["mesa_plancha_sup", "mesa_anillo_sup", "mesa_plancha_inf", "mesa_anillo_inf"], notas=["Los anillos se cortan en 4 segmentos de 90° con empalmes CJP (UT 100 %), alineados 45° respecto de los nervios."])
    return h


def sheet_mesa_cubo(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    nk = [p.key for p in ctx.m.parts if p.key.startswith("mesa_nervio") or p.key.startswith("mesa_alma")]
    keys = ["mesa_cubo"] + nk
    h = Hoja(ctx, "MES", 3, "CUBO, ALMAS ANULARES Y NERVIOS RADIALES", "1:2 / 1:5", material="S355J2+N (cubo); ASTM A572 Gr.50 (almas, nervios)", masa=f"{f(ctx.mass_of(*keys), 1)} kg", trat="Alivio de tensiones tras soldar la mesa")
    s = h.begin()
    z0, tbo, hw = g.z0, g.tbo, g.hw
    zh = z0 + tbo + hw
    V = View(s, ctx.sh("mesa_cubo"), "top", (110, 470), 0.5, center=(0, 0, zh), label="Cubo planta"); V.draw()
    V.dim_dia((0, 0, zh), P["D_hub"] / 2, 120, text=f"Ø{f(P['D_hub'])}", on=["mesa_cubo"], ext=16)
    V.dim_dia((0, 0, zh), g.d_bush / 2, 30, text=f"Ø{f(g.d_bush)} H7", on=["mesa_cubo"], ext=22)
    title_view(s, (110, 385), "CUBO – PLANTA", "ESC 1:2")
    VS = View(s, ctx.sh("mesa_cubo"), "front", (330, 440), 0.5, center=(0, 0, z0 + tbo), cut=((0, 0, 0), (0, 1, 0)), label="Cubo corte", hatch_scale=0.35); VS.draw()
    s.line(VS.P(0, 0, z0 + tbo - 8), VS.P(0, 0, zh + 8), "EJE")
    VS.dim((P["D_hub"] / 2, 0, z0 + tbo), (P["D_hub"] / 2, 0, zh), 10, orient="v", on=["mesa_cubo"])
    if g.boss:
        VS.dim((g.D_boss / 2, 0, z0 + tbo), (-g.D_boss / 2, 0, z0 + tbo), -8 if False else -20, orient="h", on=["mesa_cubo"], prefix="Ø", text=f"Ø{f(g.D_boss)} (rebaje)")
        VS.dim((137, 0, z0 + tbo), (100, 0, z0 + g.h_boss), -4, orient="v", on=["mesa_cubo"], text=f"{fm(g.h_boss - tbo, 0)} (rebaje sobre la plancha)", outside=True)
    s.finish((VS.P(-100, 0, zh)[0], VS.P(0, 0, zh)[1] + 5), "Ra 1,6 (H7)")
    s.text(f"Rebaje medido desde la cara inferior de la mesa: {f(g.h_boss)} (atraviesa la plancha inferior de {f(tbo)}): ver S12.", (230, 340), 2.0)
    title_view(s, (330, 355), "CUBO – CORTE", "ESC 1:2")
    # nervios: tramos
    a = 0.0
    segs = [p for p in ctx.m.parts if p.key.startswith("mesa_nervio")]
    y = 300
    s.text("NERVIOS RADIALES (tramos entre almas)", (30, y), 3.0, "TOP_LEFT", bold=True)
    rows = []
    for p in segs:
        bb = p.solid.val().BoundingBox()
        rows.append([p.code.replace(CODE + "-", ""), p.desc.split(",", 1)[1].strip() if "," in p.desc else p.desc, str(p.qty), f(p.mass_unit, 2)])
    s.table(30, y - 6, [("Código", 26, "L"), ("Pletina e × h × L (tramo)", 130, "L"), ("Cant", 12, "C"), ("kg/u", 18, "R")], rows, rh=5.0, h=2.0)
    rows = []
    for r_i, r in enumerate(D["almas"]):
        p = ctx.m.get(f"mesa_alma{r_i}")
        rows.append([p.code.replace(CODE + "-", ""), f"R{f(r)} (eje) · Ø int. {f(2 * (r - P['t_web'] / 2))} · e={f(P['t_web'])} · h={f(hw)} · desarrollo ≈ {f(2 * math.pi * r)}", "1", f(p.mass_unit, 1)])
    s.text("ALMAS ANULARES", (30, 235), 3.0, "TOP_LEFT", bold=True)
    s.table(30, 229, [("Código", 26, "L"), ("Alma (rolada a radio; 1 empalme CJP)", 130, "L"), ("Cant", 12, "C"), ("kg/u", 18, "R")], rows, rh=5.0, h=2.0)
    # nervio, vista lateral de un tramo (primer nervio en ángulo 0)
    if segs:
        p0 = segs[0]
        ctx.local(p0.key, "nervio0_L", near=(P["D_hub"] / 2 + 80, 0, z0 + tbo + hw / 2), r=150)
        r0 = D["almas"][0]
        VN = View(s, ctx.sh("nervio0_L"), "front", (470, 250), 0.5, center=(P["D_hub"] / 2, 0, z0 + tbo), label="Nervio"); VN.draw()
        a0_, a1_ = P["D_hub"] / 2, r0 - P["t_web"] / 2
        VN.dim((a0_, -P["t_rib"] / 2, z0 + tbo), (a1_, -P["t_rib"] / 2, z0 + tbo), -8, orient="h", on=["nervio0_L"], n=1)
        VN.dim((a1_, -P["t_rib"] / 2, z0 + tbo), (a1_, -P["t_rib"] / 2, z0 + tbo + hw), 8, orient="v", on=["nervio0_L"])
        title_view(s, (470, 190), "NERVIO – TRAMO 1 (elevación)", "ESC 1:2")
        s.text(f"Espesor {f(P['t_rib'])}; cortar a plasma; soldar con filete z{fm(P['w_web'], 0)} ambos lados a planchas, almas y cubo.", (400, 175), 2.0)
    s.weld_iso((470, 330), (520, 360), "fillet", f"z{fm(P['w_web'], 0)}", other=True, tail=["111/135 · ISO 5817-B · MT 100 %", "WPS-07 A DEFINIR POR EL FABRICANTE"])
    s.text("Soldadura de almas y nervios a las planchas (típica).", (470, 322), 2.0)
    right_col(ctx, s, keys[:1] + nk[:6], notas=["Cubo: anillo cortado a llama de plancha gruesa o tubo, sin torno vertical; Ø150 H7 y rebaje en mandrinadora."], extra_proc=False)
    return h


def sheet_pasador(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    a0 = D["pasadores"][0]
    pa = polar(g.R_pin, a0)
    ctx.local("pasadores", "pas_L", near=(pa[0], pa[1], g.z0 + 100), r=60, shift=(-pa[0], -pa[1], -g.z0))
    ctx.local("pernos_pasador", "pern_L", near=(pa[0], pa[1], g.z0 + g.hd + 10), r=80, shift=(-pa[0], -pa[1], -g.z0))
    h = Hoja(ctx, "MES", 4, "PASADOR DE EMPUJE Y PERNO DE RETENCIÓN", "1:1", material=f"34CrNiMo6+QT (EN 10083-3), Fy ≥ {f(P['Fy_pin'])} MPa", masa=f"{f(ctx.m.get('pasadores').mass_unit, 2)} kg c/u",
             trat=f"Temple por inducción franja ≥ 55 HRC, prof. ≥ {fm(g.z_hard, 1)} mm")
    s = h.begin()
    hd, d = g.hd, g.d_pin
    V = View(s, ctx.sh("pas_L", "pern_L"), "front", (160, 280), 1.0, center=(0, 0, 0), label="Pasador"); V.draw()
    s.line(V.P(0, 0, -12), V.P(0, 0, hd + 40), "EJE")
    V.dim((-d / 2, 0, 0), (d / 2, 0, 0), -10, orient="h", on=["pas_L"], text=f"Ø{f(d)} m6")
    V.dim((d / 2, 0, 0), (d / 2, 0, hd), 12, orient="v", on=["pas_L"], text=f"{f(hd)} −0,5/0")
    V.dim((-g.washer_D / 2, 0, hd + 10), (g.washer_D / 2, 0, hd + 10), 12 if False else 24, orient="h", on=["pern_L"], text=f"Ø{f(g.washer_D)} (arandela ×10)")
    zh0 = max(g.tpr, hd / 2 - P["dog_h"] / 2 - 5)
    zh1 = min(hd - g.tpr, hd / 2 + P["dog_h"] / 2 + 5)
    for sg in (-1, 1):
        s.line(V.P(sg * (d / 2 + 4), 0, zh0), V.P(sg * (d / 2 + 4), 0, zh1), "TRAT")
    s.text(f"Franja templada z = {f(zh0)}–{f(zh1)} desde la cara inferior (toda la circunferencia)", (200, 350), 2.0)
    s.text(f"≥ 55 HRC, profundidad efectiva ≥ {fm(g.z_hard, 1)} mm (control 10 % de los pasadores)", (200, 346), 2.0)
    s.text("Rosca M20, prof. 40, en el extremo superior (perno ISO 4762 M20×45 10.9 + arandela)", (200, 340), 2.0)
    s.finish((250, 300), "Ra 0,8 (Ø)")
    s.gdt((250, 320), "cyl", "0,02"); s.text("Cilindricidad del Ø", (282, 322), 2.0)
    title_view(s, (160, 200), "PASADOR DE EMPUJE", "ESC 1:1")
    s.notes_block(300, 250, "NOTAS", [
        f"Pasador a ras con la cara inferior de la mesa (−0,5/0). Sin soldadura: desmontable. Fabricación: barra comercial Ø{f(d)} m6 (laminada y pelada o rectificada); sin torno vertical.",
        "Núcleo QT 280–330 HB; certificado 3.1 por colada. Chaflanes 2×45°.",
        f"Perno M20×45 10.9 con arandela Ø{f(g.washer_D)}×10 S355J2 sobre cada pasador ({g.N_pin} juegos); torque A DEFINIR.",
    ], h=2.0, wrap_chars=110)
    right_col(ctx, s, ["pasadores", "pernos_pasador"], notas=[])
    return h


def sheet_pivote(ctx):
    g, P = ctx.g, ctx.P
    keys = [k for k in ("base_plancha", "collar", "pivote", "buje", "mesa_cubo", "mesa_plancha_inf", "mesa_plancha_sup", "tapa_ret", "tapa_insp") if k in ctx.shapes]
    h = Hoja(ctx, "PIV", 1, "PIVOTE, BUJE, TAPA RETENEDORA Y TAPA DE INSPECCIÓN", "1:1,4", material=f"42CrMo4+QT (pivote); CuAl10Ni5Fe4 (buje); S355J2 (tapas)",
             masa=f"{f(ctx.mass_of('pivote', 'buje', 'tapa_ret', 'tapa_insp'), 1)} kg", trat="Pivote bonificado (QT)")
    s = h.begin()
    tb, z0 = g.tb, g.z0
    V = View(s, ctx.sh(*keys), "front", (200, 270), 0.7, center=(0, 0, 0), cut=((0, 0, 0), (0, 1, 0)), win=(-170, -12, 170, z0 + g.hd + 25), label="Conjunto del pivote", hatch_scale=0.5); V.draw()
    s.line(V.P(0, 0, -10), V.P(0, 0, z0 + g.hd + 22), "EJE")
    V.dim((-P["D_piv"] / 2, 0, 0), (P["D_piv"] / 2, 0, 0), -9, orient="h", on=["pivote"], text=f"Ø{f(P['D_piv'])} p6 (asiento) / f7 (buje)")
    V.dim((P["D_piv"] / 2, 0, 0), (P["D_piv"] / 2, 0, g.L_piv), 60, orient="v", on=["pivote"], text=f"{f(g.L_piv)}")
    V.dim((g.d_bush / 2, 0, g.z_bush0), (g.d_bush / 2, 0, g.z_bush0 + P["L_bush"]), 22, orient="v", on=["buje"], text=f"{f(P['L_bush'])} (buje)")
    V.dim((-g.d_bush / 2, 0, g.z_bush0 + P["L_bush"]), (g.d_bush / 2, 0, g.z_bush0 + P["L_bush"]), 14, orient="h", on=["buje"], text=f"Ø{f(g.d_bush)} s6")
    V.dim((-g.cap_D / 2, 0, g.L_piv + g.cap_t), (g.cap_D / 2, 0, g.L_piv + g.cap_t), 12, orient="h", on=["tapa_ret"], text=f"Ø{f(g.cap_D)}×{f(g.cap_t)}")
    V.dim((-g.cb_D / 2 + 1, 0, z0 + g.hd), (g.cb_D / 2 - 1, 0, z0 + g.hd), 22 if False else 34, orient="h", on=["tapa_insp"], text=f"Ø{f(g.cb_D - 2)}×{f(g.cb_t)} (tapa de inspección)")
    if g.boss:
        V.dim((g.D_boss / 2, 0, tb), (g.D_boss / 2, 0, tb + g.h_boss), 8, orient="v", on=["collar"], text=f"{f(g.h_boss)} (collar)")
        V.dim((-g.D_boss / 2, 0, tb + g.h_boss), (g.D_boss / 2, 0, tb + g.h_boss), -50 if False else 0.01, orient="h", on=["collar"], text="") if False else None
    s.text(f"Asiento del pivote en plancha base + collar: {f(tb + g.h_boss)} (t_base + h_collar). Buje desde z = {f(g.z_bush0)} (2 mm sobre el collar).", (30, 535 - 330 + 40), 2.0) if False else None
    s.text(f"Asiento del pivote = t_base + h_collar = {f(tb + g.h_boss)}. Buje desde z = {f(g.z_bush0)} (2 mm sobre el collar). Pivote 3 mm sobre el cubo; tapa con juego vertical 3 mm.", (30, 195), 2.0)
    s.text("Tapa retenedora: 4 × M10×25 ISO 10642 10.9 avellanados en el pivote. Tapa de inspección: 6 × M10 avellanados en el rebaje de la plancha superior.", (30, 190), 2.0)
    s.gdt((30, 170), "perp", "0,05", "A"); s.text("Pivote perpendicular a la cara de apoyo de la base (A).", (62, 172), 2.0)
    s.gdt((30, 155), "coax", "Ø0,05", "A"); s.text("Collar y plancha base coaxiales (agujero H7 mandrinado en línea).", (62, 157), 2.0)
    s.finish((300, 160), "Ra 0,8 (pivote)")
    title_view(s, (200, 218), "CORTE POR EL EJE DEL PIVOTE", "ESC 1:1,4")
    right_col(ctx, s, ["pivote", "buje", "tapa_ret", "tapa_insp"], notas=[
        "Pivote: barra Ø120 de 42CrMo4+QT, rectificada o torneada en torno horizontal; zona de asiento p6 y zona del buje f7; sin torno vertical.",
        "El buje se corta de tubo fundido autolubricado o se pide a medida; Ø interior en mandrinadora."])
    return h
