"""Figuras de la placa-guía curva del modo pivotado (docs/qa/guia_curva_KIET/): comparación original / curva / concepto KIET y cinemática.

Uso: node tools/export_design.js > /tmp/d.json && python3 tools/fig_guia_curva.py /tmp/d.json
Lee la geometría del núcleo como caja negra (export_design.js), la del estado original (docs/qa/guia_curva_KIET/original_b928552.json) y los recortes
del plano de referencia KIET (sin escala: solo concepto). Escribe comparacion.svg/png y cinematica.svg/png en docs/qa/guia_curva_KIET/."""
import json, math, pathlib, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle, Arc
import matplotlib.image as mpimg

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "qa" / "guia_curva_KIET"
D = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
O = json.loads((OUT / "original_b928552.json").read_text(encoding="utf-8"))
P, PV = D["P"], D["pivotado"]
PL, FAB = PV["placa_leva"], PV["fabricacion"]
rf = P["pv_dq"] / 2; R0 = P["R_pin"]; Rt = P["D_top"] / 2
plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans", "svg.fonttype": "none"})

def seg_pts(s, n=60):
    if s["tipo"] == "linea": return [s["p0"], s["p1"]]
    cx, cy = s["centro"]; k = 1 if s["sentido"] == "antihorario" else -1
    a0 = math.atan2(s["p0"][1] - cy, s["p0"][0] - cx); a1 = math.atan2(s["p1"][1] - cy, s["p1"][0] - cx); d = k * (a1 - a0)
    while d < 0: d += 2 * math.pi
    while d >= 2 * math.pi: d -= 2 * math.pi
    return [(cx + s["radio"] * math.cos(a0 + k * d * i / n), cy + s["radio"] * math.sin(a0 + k * d * i / n)) for i in range(n + 1)]
def xy(pl): return [p[0] for p in pl], [p[1] for p in pl]
def ring(ax, lw=0.8):
    t = [i * math.pi / 180 for i in range(0, 361)]
    ax.plot([Rt * math.cos(a) for a in t], [Rt * math.sin(a) for a in t], color="0.35", lw=lw)
    ax.plot([R0 * math.cos(a) for a in t], [R0 * math.sin(a) for a in t], color="0.7", lw=0.4, ls=(0, (6, 4)))
def pins(ax, th_deg, **kw):
    for k in range(P["N_pin"]):
        a = math.radians(th_deg) + 2 * math.pi * k / P["N_pin"]; ax.add_patch(Circle((R0 * math.cos(a), R0 * math.sin(a)), P["d_pin"] / 2, **kw))
pos = PV["posiciones"]["1_antihorario"]; E = pos["E"]
COL = {"linea": "#1f4e9c", "convexa": "#c0392b", "cóncava": "#1e8449", None: "#7f8c8d"}

# ---------------- Figura 1: comparación ----------------
fig = plt.figure(figsize=(16, 19))
gs = fig.add_gridspec(3, 3, height_ratios=[1.05, 1, 0.95])
# (a) planta nuestra completa
ax = fig.add_subplot(gs[0, 0]); ax.set_aspect("equal"); B = P["B"] / 2
ax.add_patch(Rectangle((-B, -B), 2 * B, 2 * B, fill=False, lw=1.2)); ring(ax); pins(ax, PV["theta_ini_deg"], color="0.55", lw=0)
for k, ins in FAB["placas_leva"]["instancias"].items():
    act = k.endswith("antihorario")
    ax.add_patch(Polygon(ins["contorno"], closed=True, fc="#2c2c2c" if act else "#8c8c8c", ec="k", lw=0.5, alpha=0.9 if act else 0.5))
    ax.plot(*xy(ins["recorte"]), color="#e67e22" if act else "#f5cba7", lw=1.2)
for Ek in PV["fabricacion"]["soporte_E"]["cilindro1"]["esquinas"], PV["fabricacion"]["soporte_E"]["cilindro2"]["esquinas"]:
    ax.add_patch(Polygon(Ek, closed=True, fc="#f4d03f", ec="k", lw=0.5))
for kk in ("1_antihorario", "2_antihorario"):
    pp = PV["posiciones"][kk]; q0 = pp["Q"][0]; e0 = pp["E"]
    ax.plot([e0[0], q0[0]], [e0[1], q0[1]], color="#f1c40f", lw=6, solid_capstyle="round"); ax.add_patch(Circle(q0, rf + 25, fc="#2c3e50", ec="k"))
ax.set_xlim(-B - 60, B + 60); ax.set_ylim(-B - 60, B + 60); ax.set_title("TT300-C · planta con las 4 placas-guía curvas\n(oscuras: giro antihorario; claras: horario)", fontsize=9)
ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
# (b) planta KIET (recorte del plano, sin escala)
ax = fig.add_subplot(gs[0, 1:]); ax.imshow(mpimg.imread(OUT / "kiet_planta_recorte.png"), cmap="gray"); ax.axis("off")
ax.set_title("Concepto KIET (plano de referencia KIET-1024-REF-TT-400T, recorte sin escala)\n4 placas rectangulares empernadas con recorte en media luna junto a la cabeza del vástago", fontsize=9)
# (c) tabla comparativa
ax = fig.add_subplot(gs[2, :]); ax.axis("off")
g = PL; o = O["placa_leva"]
rows = [["", "Original (b928552)", "Curva (este cambio)", "KIET (concepto)"],
        ["Perfil del canto", "poligonal: tramo, rampa 65°,\nbolsillo plano, rampa 65°", "flanco recto %.1f° + 4 arcos\ntangentes + salida (G1)" % g["alpha_deg"], "media luna curva\ncon gancho en un extremo"],
        ["Quiebre máx. de tangente", "70°", "≈ 0° (G1)" if math.degrees(g["g1_max_rad"]) < 1e-6 else "%.2f°" % math.degrees(g["g1_max_rad"]), "—"],
        ["Canto exportado", "w + d_Q/2 (no envolvente):\ninvade el seguidor 27 mm", "envolvente exacta\n(arcos concéntricos ± d_Q/2)", "—"],
        ["Sincronía (con el contorno real)", "−21 mm (choque con B)", "%.2f mm (peor caso %.2f)" % (g["sincronia"], g["sincronia_peor"]), "—"],
        ["Radios del canto", "0 (esquinas)", "convexo ≥ %.0f, cóncavo ≥ %.0f mm" % (g["radio_min_canto"]["convexo"], g["radio_min_canto"]["concavo"]), "no acotado"],
        ["Q en el empuje", "suelto en el 76 % (rodilla\nsin verificar)", "apoyado en el canto\n(rodilla inestable, H > 0)", "—"],
        ["Carga de diseño de la placa", "%.0f kN (F_ret/sen 65°)" % (o["fuerzas_N"]["diseno"] / 1e3), "%.0f kN (empuje a calado)" % (g["fuerzas_N"]["diseno"] / 1e3), "—"],
        ["Placa", "labio curvo de 80 mm\n6 pernos M20 (rosca en base 18)", "rectángulo %.0f × %.0f con recorte\n%d ISO 10642 M%d 8.8 + 2 pasadores" % (FAB["placas_leva"]["marco"]["largo"], FAB["placas_leva"]["marco"]["ancho"], FAB["placas_leva"]["pernos"]["n"], FAB["placas_leva"]["pernos"]["d"]), "rectángulo empernado\n(~6 pernos perimetrales)"],
        ["Material del canto", "S355J2 «templado» (no templable)", "42CrMo4+QT, inducción 52–56 HRC", "no indicado"],
        ["Posición (ángulo desde la diagonal del ojal)", "≈ ±22°", "±%.0f°" % abs(((math.degrees(math.atan2(*reversed([sum(p[0] for p in FAB["placas_leva"]["instancias"]["1_antihorario"]["contorno"]) / len(FAB["placas_leva"]["instancias"]["1_antihorario"]["contorno"]), sum(p[1] for p in FAB["placas_leva"]["instancias"]["1_antihorario"]["contorno"]) / len(FAB["placas_leva"]["instancias"]["1_antihorario"]["contorno"])]))) - P["pv_phE"] + 180) % 360) - 180), "±26° (medido en plano, no acotado)"]]
bq = PV["bloque_una"]
rows.append(["Cara del bloque-uña", "plana 80 mm: con el roce el contacto\nva a 58 mm del eje (arista)", "cilíndrica convexa R %.0f: contacto a\n%.1f mm del eje (≤ %.0f)" % (P["pv_rface"], bq["contacto_cara"], P["pv_bf"] / 2 - 3), "—"])
rows.append(["FS del accionamiento (diseño)", "%.3f (colineal)" % O["casos"][1]["FS"] if O["casos"][1]["id"] == "dis" else "—", "%.3f (empuje guiado)" % [c for c in D["derivados"]["casos"] if c["id"] == "dis"][0]["FS"], "—"])
dec = lambda t: re.sub(r"(?<!M16 )(?<!M20 )(\d)\.(\d)", r"\1,\2", t).replace("8,8", "8.8")
rows = [[dec(c) for c in r] for r in rows]
tb = ax.table(cellText=rows, cellLoc="left", colWidths=[0.2, 0.27, 0.3, 0.23], bbox=[0, 0, 1, 0.9]); tb.auto_set_font_size(False); tb.set_fontsize(8)
for (i, j), cl in tb.get_celld().items():
    if i == 0 or j == 0: cl.set_text_props(weight="bold")
ax.text(0.5, 0.95, "Comparación (valores por defecto, 300 tf)", transform=ax.transAxes, ha="center", va="center", fontsize=10, weight="bold")
# detalle: ventana común en el marco de la placa del cilindro 1, giro antihorario
ins = FAB["placas_leva"]["instancias"]["1_antihorario"]; cx_ = [p[0] for p in ins["contorno"]]; cy_ = [p[1] for p in ins["contorno"]]
xl = (min(cx_ + [p[0] for p in O["leva_borde_exterior"]]) - 60, max(cx_ + [p[0] for p in O["leva_borde_exterior"]]) + 60); yl = (min(cy_) - 120, max(cy_) + 60)
def detail(ax, title):
    ax.set_aspect("equal"); ring(ax); pins(ax, PV["theta_ini_deg"], color="0.75", lw=0); ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_title(title, fontsize=9); ax.set_xlabel("x (mm)")
# (d) original
ax = fig.add_subplot(gs[1, 0]); detail(ax, "Original: canto poligonal (rampa 65°, bolsillo plano)\ncírculos: seguidor Ø%.0f en w_leva — invade el canto exportado en las rampas" % P["pv_dq"])
poly = O["leva_canto"] + O["leva_borde_exterior"][::-1]
ax.add_patch(Polygon(poly, closed=True, fc="#bdc3c7", ec="k", lw=0.6)); ax.plot(*xy(O["leva_canto"]), color="#e67e22", lw=1.4)
cs = O["leva_centro_seguidor"]
for i in range(0, len(cs), 6): ax.add_patch(Circle(cs[i], rf, fill=False, ec="#8e44ad", lw=0.5))
ax.plot(*xy(cs), color="#8e44ad", lw=0.8, ls="--", label="centro del seguidor (w_leva)")
for b in O["leva_pernos"]: ax.add_patch(Circle(b, O["placa_leva"]["d_perno"] / 2, fc="w", ec="k", lw=0.5))
ax.legend(loc="lower left", fontsize=7)
# (e) curva
ax = fig.add_subplot(gs[1, 1]); detail(ax, "Curva: flanco recto + arcos tangentes (G1), canto = envolvente a d_Q/2\nrojo: convexo · verde: cóncavo · azul: recto")
ax.add_patch(Polygon(ins["contorno"], closed=True, fc="#bdc3c7", ec="k", lw=0.6))
for s in ins["segmentos_canto"]: ax.plot(*xy(seg_pts(s)), color=COL[s.get("curvatura") if s["tipo"] == "arco" else "linea"], lw=1.8)
cs = ins["centro_seguidor"]
for i in range(0, len(cs), max(1, len(cs) // 14)): ax.add_patch(Circle(cs[i], rf, fill=False, ec="#8e44ad", lw=0.5))
ax.plot(*xy(cs), color="#8e44ad", lw=0.8, ls="--", label="centro del seguidor (recorrido)")
for b in ins["pernos"]: ax.add_patch(Circle(b, P["pv_db"] / 2, fc="w", ec="k", lw=0.5))
for b in ins["pasadores_posicion"]: ax.add_patch(Circle(b, P["pv_dd"] / 2, fc="#5dade2", ec="k", lw=0.5))
ax.legend(loc="lower left", fontsize=7)
# (f) KIET detalle
ax = fig.add_subplot(gs[1, 2]); ax.imshow(mpimg.imread(OUT / "kiet_detalle_placa_cilindro1.png"), cmap="gray"); ax.axis("off")
ax.set_title("KIET: cilindro en la esquina, bloque-uña y placa con recorte curvo\n(recorte del plano, sin escala; no se trasladan dimensiones)", fontsize=9)
fig.suptitle("Placa-guía del accionamiento pivotado (drive_mode = 2): original poligonal, rediseño curvo y concepto KIET", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.97))
for ext in ("svg", "png"): fig.savefig(OUT / ("comparacion." + ext), dpi=150)
plt.close(fig)

# ---------------- Figura 2: cinemática ----------------
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 3, width_ratios=[1.35, 1, 1])
ax = fig.add_subplot(gs[:, 0]); ax.set_aspect("equal"); ring(ax)
th0, th1 = math.radians(PV["theta_ini_deg"]), math.radians(PV["theta_fin_deg"]); pit = 2 * math.pi / P["N_pin"]
for k, (a, lab, col) in enumerate([(th0, "A al tomar (θ_ini)", "#2980b9"), (th1, "A al final (θ_fin)", "#c0392b"), (th0 - pit, "siguiente B", "#7f8c8d")]):
    ax.add_patch(Circle((R0 * math.cos(a), R0 * math.sin(a)), P["d_pin"] / 2, fc=col, ec="k", lw=0.5, alpha=0.8)); ax.annotate(lab, (R0 * math.cos(a), R0 * math.sin(a)), xytext=(-95, 6 - 14 * k), textcoords="offset points", fontsize=7, color=col)
ax.add_patch(Polygon(ins["contorno"], closed=True, fc="#e5e7e9", ec="k", lw=0.6))
for i, s in enumerate(ins["segmentos_canto"]):
    pts_ = seg_pts(s); ax.plot(*xy(pts_), color=COL[s.get("curvatura") if s["tipo"] == "arco" else "linea"], lw=2)
    ax.plot(*s["p0"], "ko", ms=2.5)
    if s["tipo"] == "arco" and s.get("rol", "").find("cierre") < 0:
        m = pts_[len(pts_) // 2]; ax.plot(*s["centro"], "+", color=COL[s["curvatura"]], ms=7)
        ax.plot([s["centro"][0], m[0]], [s["centro"][1], m[1]], color=COL[s["curvatura"]], lw=0.4, ls=":")
        ax.annotate("R%.0f %s" % (s["radio"], "cx" if s["curvatura"] == "convexa" else "cc"), m, xytext=(8, 0), textcoords="offset points", fontsize=7, color=COL[s["curvatura"]])
fl = ins["segmentos_canto"][0]; ax.annotate("flanco recto %.1f°\n(pie en L0: reenganche)" % PL["alpha_deg"], ((fl["p0"][0] + fl["p1"][0]) / 2, (fl["p0"][1] + fl["p1"][1]) / 2), xytext=(25, -20), textcoords="offset points", fontsize=7, color=COL["linea"], arrowprops=dict(arrowstyle="-", lw=0.4))
Qg = pos["Q"]; Qc = pos["Q_colineal"]; Qr = [q["Q"] for q in PL["retorno"]]
ax.plot(*xy(Qc), color="#95a5a6", lw=1, ls="--", label="Q colineal E–Q–P (referencia)")
ax.plot(*xy(Qg), color="#8e44ad", lw=1.6, label="Q en el empuje (apoyado en el canto)")
ax.plot(*xy(Qr), color="#16a085", lw=1.2, ls="-.", label="Q en el retorno (sobre B y conducción al flanco)")
for q, lab in ((Qg[0], "L = %.0f" % (PV["cinematica"][0]["L"])), (Qg[-1], "L = %.0f" % PV["cinematica"][-1]["L"])):
    ax.plot([E[0], q[0]], [E[1], q[1]], color="#f1c40f", lw=4, alpha=0.6); ax.add_patch(Circle(q, rf, fill=False, ec="#8e44ad", lw=0.8))
pc = PL["primer_contacto"]; qpc = [q["Q"] for q in PL["retorno"] if abs(q["L"] - pc["L"]) < 3]
if qpc: ax.plot(*qpc[0], "s", color="#16a085", ms=5); ax.annotate("primer contacto del retorno\nφ₁ = %.1f°" % pc["phi"], qpc[0], xytext=(-120, -30), textcoords="offset points", fontsize=7, color="#16a085", arrowprops=dict(arrowstyle="-", lw=0.4))
for b in ins["pernos"]: ax.add_patch(Circle(b, P["pv_db"] / 2, fc="w", ec="k", lw=0.5))
for b in ins["pasadores_posicion"]: ax.add_patch(Circle(b, P["pv_dd"] / 2, fc="#5dade2", ec="k", lw=0.5))
ax.set_xlim(min(cx_) - 230, max(cx_) + 40); ax.set_ylim(min(cy_) - 60, max(cy_) + 160); ax.legend(loc="upper left", fontsize=7)
ax.set_title("Cinemática y curva guía (cilindro 1, giro antihorario)\n+ centros de arco · puntos: tangencias · R en mm (cx convexo, cc cóncavo)", fontsize=9)
ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
# w(L): requisitos y trayectoria
ax = fig.add_subplot(gs[0, 1:]); pf = PL["perfil"]
ax.plot([q["L"] for q in pf], [q["w_nec"] for q in pf], color="#c0392b", lw=1, label="w_nec(m + δ) retorno (sincronía)")
ax.plot([q["L"] for q in pf], [q["w_nec0"] for q in pf], color="#c0392b", lw=0.6, ls=":", label="w_nec (holgura 0)")
ax.plot([q["L"] for q in pf], [q["w_emp"] + PL["holgura"] for q in pf], color="#7f8c8d", lw=1, ls="--", label="w_emp colineal + c")
ax.plot([q["L"] for q in pf], [q["w_leva"] for q in pf], color="#8e44ad", lw=2, label="W(L) centro del seguidor (curva)")
ax.plot([q["L"] for q in O["perfil"]], [q["w_leva"] for q in O["perfil"]], color="#e67e22", lw=1, ls="-.", label="w_leva original (poligonal)")
ax.plot([q["L"] for q in PL["retorno"]], [q["w"] for q in PL["retorno"]], color="#16a085", lw=1, ls="-.", label="Q en el retorno")
ax.set_xlabel("L = |Q − E| (mm)"); ax.set_ylabel("w: desplazamiento lateral de Q hacia afuera (mm)"); ax.grid(lw=0.3); ax.legend(fontsize=7, ncol=2)
ax.set_title("Requisitos y trayectoria del seguidor en coordenadas del cilindro", fontsize=9)
# ángulo de presión y fuerzas
ax = fig.add_subplot(gs[1, 1]); cin = PV["cinematica"]
ax.plot([q["th"] for q in cin], [q["phi_presion_deg"] for q in cin], color="#8e44ad", label="φ empuje (Q en el canto)")
ax.axhline(90 - math.degrees(math.atan(PL["mu"])), color="k", lw=0.6, ls="--", label="autobloqueo 90° − atan μ")
ax2 = ax.twiny(); rt = [q for q in PL["retorno"] if q["guia"] and q["L"] <= pc["L"] + 1e-9]
ax2.plot([q["L"] for q in rt], [q["phi_deg"] for q in rt], color="#16a085", lw=1.2, label="φ retorno (conducción)"); ax2.set_xlabel("L en el retorno (mm)", fontsize=7)
ax.axhline(P["pv_alpha"], color="#16a085", lw=0.6, ls=":"); ax.set_xlabel("θ del pasador tomado (°)"); ax.set_ylabel("ángulo de presión (°)"); ax.grid(lw=0.3)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="center right")
ax = fig.add_subplot(gs[1, 2])
ax.plot([q["th"] for q in cin], [q["F_cil"] for q in cin], color="#2c3e50", label="F cilindro, empuje guiado")
ax.plot([q["th"] for q in cin], [q["F_cil_colineal"] for q in cin], color="#95a5a6", ls="--", label="F cilindro, colineal (ref.)")
ax.plot([q["th"] for q in cin], [q["F_leva"] for q in cin], color="#c0392b", label="H placa-guía (diseño)")
ax.set_xlabel("θ del pasador tomado (°)"); ax.set_ylabel("kN (caso de diseño)"); ax.grid(lw=0.3); ax.legend(fontsize=7)
ax.set_title("Fuerzas en el empuje (caso de diseño)", fontsize=9)
fig.suptitle("Placa-guía curva: trayectorias de Q (empuje y retorno), posiciones extremas, curva guía con radios, ángulo de presión y fuerzas", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.97))
for ext in ("svg", "png"): fig.savefig(OUT / ("cinematica." + ext), dpi=150)
print("figuras en", OUT)
