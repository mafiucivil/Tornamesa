"""Modelo 3D TT300-C (CadQuery) desde cad/out/TT300-C_design.json: STEP de ensamble, GLB y control de masas.
Uso: python3 cad/modelo3d_tt300c.py [design.json]
Ejes: z vertical desde la cara inferior de la base; x, y en planta como en los planos."""
import json, math, sys, pathlib
import cadquery as cq

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "cad" / "out"
D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else OUT / "TT300-C_design.json", encoding="utf-8"))
if D["P"].get("opt_ss", 0) or D["P"].get("opt_uhmw", 0) or D["P"].get("opt_bz", 0):
    raise SystemExit("La interfaz alternativa (discos inoxidables / UHMW / bronce) aún no está dibujada en el modelo 3D ni en los planos: desactive las opciones A, B y C para emitirlos.")
P, DV = D["P"], D["derivados"]
RHO = 7.85e-6

tb, hd, tt, tbo = P["t_base"], P["h_disc"], P["t_top"], P["t_bot"]
tpr = max(P["t_pr"], tt, tbo)
Rt, prIn = P["D_top"] / 2, DV["prIn"]
hw = hd - tt - tbo
zc = tb + DV["hax"]
d_pin, R_pin = P["d_pin"], P["R_pin"]
d_bush = P["D_piv"] + 30
L_piv = tb + hd - tt + 3
cb_t = 8                                  # tapa de inspección (rebaje en la plancha superior)
cap_D = P["D_piv"] + 60
cap_t = tt - 3 - cb_t - 1                 # tapa retenedora: entre el pivote (3 sobre el cubo) y la tapa de inspección, 1 de juego
hole_top = cap_D + 20
BR = DV["bracket"]
Llug = BR["Llug"]
forkH = DV["forkH"]
KG = DV["K"]
zb = tb + P["t_bed"]                      # cara superior de la bancada
zT1 = zb - P["h_slot"]                    # cabeza de la ranura T: z ∈ [zT0, zT1]
zT0 = zT1 - P["h_tee"]
ch_dx = KG["travel"]                      # chaflán de retorno de la uña (= chamferGeo del núcleo)
ch_dy = ch_dx / math.tan(math.radians(P["beta_ch"]))
washer_D = d_pin + 30

def cyl(r, h, z0=0.0, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(h)
def ring(r0, r1, h, z0=0.0):
    return cq.Workplane("XY").workplane(offset=z0).circle(r1).circle(r0).extrude(h)
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
def place(wp, phi_deg, E):
    return wp.rotate((0, 0, 0), (0, 0, 1), phi_deg).translate((E[0], E[1], 0))
def pin_xy():
    return [(R_pin * math.cos(math.radians(a)), R_pin * math.sin(math.radians(a))) for a in D["pasadores"]]

parts = {}   # nombre: (sólido, color, es_acero_del_núcleo)

# ---------------- base ----------------
B = P["B"]
base = box(-B / 2, B / 2, -B / 2, B / 2, 0, tb).cut(cyl(P["D_piv"] / 2, tb + 2, -1))
parts["1a_plancha_base"] = (base, (0.55, 0.57, 0.6), "base")
r_t, r_h = P["rim_t"], P["rim_h"]
rim = (box(-B / 2, B / 2, -B / 2, -B / 2 + r_t, tb, tb + r_h).union(box(-B / 2, B / 2, B / 2 - r_t, B / 2, tb, tb + r_h))
       .union(box(-B / 2, -B / 2 + r_t, -B / 2 + r_t, B / 2 - r_t, tb, tb + r_h)).union(box(B / 2 - r_t, B / 2, -B / 2 + r_t, B / 2 - r_t, tb, tb + r_h)))
parts["1b_marco"] = (rim, (0.55, 0.57, 0.6), "rim")
brk = None
for grp in ("horario", "antihorario"):
    for c in D["cilindros"][grp]:
        x0, x1 = -BR["rear"], P["L_ch"] - BR["rear"]
        side = box(x0, x1, BR["Win"] / 2, BR["Wout"] / 2, tb, tb + BR["H"]).union(box(x0, x1, -BR["Wout"] / 2, -BR["Win"] / 2, tb, tb + BR["H"]))
        top = box(x0, Llug - BR["rear"], -BR["Win"] / 2, BR["Win"] / 2, tb + BR["H"] - P["t_ch"], tb + BR["H"])
        bot = box(x0, Llug - BR["rear"], -BR["Win"] / 2, BR["Win"] / 2, tb, tb + BR["spacer"] + P["t_ch"])
        b = side.union(top).union(bot).cut(cyl(P["d_pp"] / 2, BR["H"] + 2, tb - 1))
        b = place(b, c["phiMean"], c["eye"])
        brk = b if brk is None else brk.union(b)
parts["1c_menuslas"] = (brk, (0.5, 0.52, 0.55), "brackets")
cl = B / 2 - P["c_lug"]
lugs = None
for (x, y) in [(P["x_lug"], cl), (-P["x_lug"], cl), (P["x_lug"], -cl), (-P["x_lug"], -cl)]:
    l = cyl(35, 25, tb, x, y).union(cyl(20, 40, tb + 25, x, y))
    lugs = l if lugs is None else lugs.union(l)
parts["1d_puntos_izaje"] = (lugs, (0.9, 0.2, 0.15), None)
beds = None
for sx in (1, -1):
    X = sx * P["x_g"]
    # ranura T pasante en y: cuello w_slot × h_slot y cabeza w_tee × h_tee bajo el cuello (fondo t_bed − h_slot − h_tee)
    bd = box(X - P["w_bed"] / 2, X + P["w_bed"] / 2, -KG["Y_bed"], KG["Y_bed"], tb, zb).cut(
        box(X - P["w_slot"] / 2, X + P["w_slot"] / 2, -KG["Y_bed"] - 1, KG["Y_bed"] + 1, zb - P["h_slot"], zb + 1))
    if P["h_tee"] > 0:
        bd = bd.cut(box(X - P["w_tee"] / 2, X + P["w_tee"] / 2, -KG["Y_bed"] - 1, KG["Y_bed"] + 1, zT0, zT1))
    beds = bd if beds is None else beds.union(bd)
parts["1e_bancadas"] = (beds, (0.45, 0.47, 0.5), "beds")

# ---------------- mesa ----------------
z0 = tb
holes_pins = lambda wp, z, h: wp.cut(cq.Workplane("XY").workplane(offset=z - 1).pushPoints(pin_xy()).circle(d_pin / 2).extrude(h + 2))
disc_bot = ring(d_bush / 2, prIn, tbo, z0)
ring_bot = holes_pins(ring(prIn, Rt, tpr, z0), z0, tpr)
disc_top = ring(hole_top / 2, prIn, tt, z0 + hd - tt)
ring_top = holes_pins(ring(prIn, Rt, tpr, z0 + hd - tpr), z0 + hd - tpr, tpr)
webs = None
for r in D["almas"]:
    w = ring(r - P["t_web"] / 2, r + P["t_web"] / 2, hw, z0 + tbo)
    webs = w if webs is None else webs.union(w)
ribs = None
for a in D["nervios"]:
    rb = box(P["D_hub"] / 2, P["R_rib"], -P["t_rib"] / 2, P["t_rib"] / 2, z0 + tbo, z0 + tbo + hw).rotate((0, 0, 0), (0, 0, 1), a)
    ribs = rb if ribs is None else ribs.union(rb)
ribs = ribs.cut(cyl(P["D_hub"] / 2, hw + 2, z0 + tbo - 1))
for r in D["almas"]:
    ribs = ribs.cut(ring(r - P["t_web"] / 2, r + P["t_web"] / 2, hw + 2, z0 + tbo - 1))
hub = ring(d_bush / 2, P["D_hub"] / 2, hw, z0 + tbo)
mesa = disc_bot.union(ring_bot).union(disc_top).union(ring_top).union(webs).union(ribs).union(hub)
parts["2_mesa"] = (mesa, (0.22, 0.4, 0.7), "disc_struct")
pins = cq.Workplane("XY").workplane(offset=z0).pushPoints(pin_xy()).circle(d_pin / 2).extrude(hd)
parts["3_pasadores"] = (pins, (0.75, 0.75, 0.78), "pins")
wsh = cq.Workplane("XY").workplane(offset=z0 + hd).pushPoints(pin_xy()).circle(washer_D / 2).extrude(10).union(
      cq.Workplane("XY").workplane(offset=z0 + hd + 10).pushPoints(pin_xy()).circle(15).extrude(20))
parts["4_arandelas_pernos"] = (wsh, (0.3, 0.3, 0.32), None)
parts["5_pivote"] = (cyl(P["D_piv"] / 2, L_piv), (0.35, 0.35, 0.38), "pivot")
parts["6_buje"] = (ring(P["D_piv"] / 2, d_bush / 2, P["L_bush"], tb + 2), (0.8, 0.55, 0.2), None)
parts["7_tapa_retenedora"] = (cyl(cap_D / 2, cap_t, L_piv), (0.35, 0.35, 0.38), None)
parts["8_tapa_inspeccion"] = (cyl(hole_top / 2 - 1, cb_t, z0 + hd - cb_t), (0.22, 0.4, 0.7), None)

# ---------------- cilindros, patines, uñas y pasadores (sentido antihorario, al tomar el pasador) ----------------
cyls = dogs = apins = shoes = None
cl1 = 1.0                                                             # holgura de modelo entre piezas móviles
for c in D["cilindros"]["antihorario"]:
    sx, dy, X = c["side"], c["dir"], c["x"]
    ye, yr, yps = c["eye"][1], c["rodEngage"][1], c["pinStart"][1]
    srt = lambda a, b: (min(a, b), max(a, b))
    # cilindro coaxial con la guía (eje y): cuerpo fijo (geometría retraída) + vástago hasta el pasador del patín
    yb0, yb1 = srt(ye + dy * P["e_body"], c["rodRetracted"][1] - dy * P["c_rod"])
    body = cq.Workplane("XZ").workplane(offset=-yb1).center(X, zc).circle(P["D_body"] / 2).extrude(yb1 - yb0)
    yr0, yr1 = srt(c["rodRetracted"][1] - dy * P["c_rod"], yr - dy * 52.5)
    rod = cq.Workplane("XZ").workplane(offset=-yr1).center(X, zc).circle(P["d_rod"] / 2).extrude(yr1 - yr0)
    eye0 = cyl(52.5, P["b_eye"], zc - P["b_eye"] / 2, X, ye).cut(cyl(P["d_pp"] / 2, P["b_eye"] + 2, zc - P["b_eye"] / 2 - 1, X, ye))
    eye1 = cyl(52.5, P["b_eye"], zc - P["b_eye"] / 2, X, yr).cut(cyl(P["d_pp"] / 2, P["b_eye"] + 2, zc - P["b_eye"] / 2 - 1, X, yr))
    cy = body.union(rod).union(eye0).union(eye1)
    cyls = cy if cyls is None else cyls.union(cy)
    # uña: cara de empuje PLANA (normal a y) en contacto con el pasador tomado, y = y_pas − dy·d/2;
    # ocupa x ∈ [tipX, boca + L_in] e y entre la cara de empuje y la cara trasera (ancho dog_b).
    # Chaflán de retorno en la arista punta–cara trasera: Δx = recorrido de retorno, Δy = Δx/tan β.
    yF = yps - dy * d_pin / 2                                         # cara de empuje
    yB = yF - dy * P["dog_b"]                                         # cara trasera
    yd0, yd1 = srt(yB, yF)
    xT, xE = sx * KG["tipX"], sx * (KG["mouthX"] + P["L_in"])
    dog_pts = [(xT, yF), (xE, yF), (xE, yB), (xT + sx * ch_dx, yB), (xT, yB + dy * min(ch_dy, P["dog_b"]))]
    dog = cq.Workplane("XY").workplane(offset=zc - P["dog_h"] / 2).polyline(dog_pts).close().extrude(P["dog_h"])
    dogs = dog if dogs is None else dogs.union(dog)
    # patín: caja sobre la bancada + lengüeta T (cuello y cabeza) + marco de boca (paredes t_fw); huecos para ojal, pasador y uña
    ys0, ys1 = srt(yr - dy * KG["rear"], yr + dy * KG["front"])
    sh = box(X - P["w_s"] / 2, X + P["w_s"] / 2, ys0, ys1, zb, KG["shoeTop"])   # cara superior: horquilla o tapa del alojamiento (núcleo)
    # cabeza T con 1 mm de juego arriba y abajo en la cabeza de la ranura; el cuello llega desde la cabeza hasta la caja
    zh0, zh1 = (zT0 + 1, zT1 - 1) if P["h_tee"] > 0 else (zb - P["h_slot"] + 2, zb - P["h_slot"] + 2)
    sh = sh.union(box(X - P["w_slot"] / 2 + cl1, X + P["w_slot"] / 2 - cl1, ys0, ys1, zh1 if P["h_tee"] > 0 else zh0, zb))
    if P["h_tee"] > 0:
        sh = sh.union(box(X - P["w_tee"] / 2 + cl1, X + P["w_tee"] / 2 - cl1, ys0, ys1, zh0, zh1))
    mx0, mx1 = srt(sx * KG["mouthX"], sx * (P["x_g"] - P["w_s"] / 2))
    sh = sh.union(box(mx0, mx1, yd0 - P["t_fw"], yd1 + P["t_fw"], zc - P["dog_h"] / 2 - 10, zc + P["dog_h"] / 2 + 10))
    ge0, ge1 = srt(yr - dy * KG["rear"] - 1, yr + dy * (52.5 + 5))
    sh = sh.cut(box(X - 57.5, X + 57.5, ge0, ge1, zc - P["b_eye"] / 2 - P["g_ch"], zc + P["b_eye"] / 2 + P["g_ch"]))
    zpp0 = max(zb, zc - forkH / 2 - 10)                                 # agujero del pasador del vástago: ciego sobre la lengüeta
    sh = sh.cut(cyl(P["d_pp"] / 2, KG["shoeTop"] + 10 - zpp0, zpp0, X, yr))
    gr0, gr1 = srt(yr - dy * (KG["rear"] + 5), yr - dy * 40)            # ranura de paso del vástago (orejas no cargadas atrás)
    sh = sh.cut(box(X - (P["d_rod"] + 10) / 2, X + (P["d_rod"] + 10) / 2, gr0, gr1, zc - (P["d_rod"] + 10) / 2, zc + (P["d_rod"] + 10) / 2))
    px0, px1 = srt(sx * KG["mouthX"], sx * (KG["pocketEnd"] + cl1))      # alojamiento: uña + recorrido de retorno + resorte
    sh = sh.cut(box(px0 - cl1, px1, yd0 - cl1, yd1 + cl1, zc - P["dog_h"] / 2 - cl1, zc + P["dog_h"] / 2 + cl1))
    shoes = sh if shoes is None else shoes.union(sh)
    ap = cyl(P["d_pp"] / 2, KG["shoeTop"] + 10 - zpp0, zpp0, X, yr).union(cyl(P["d_pp"] / 2, BR["H"] + 15, tb, X, ye))
    apins = ap if apins is None else apins.union(ap)
parts["9_cilindros"] = (cyls, (0.95, 0.78, 0.1), None)
parts["10_unas"] = (dogs, (0.85, 0.35, 0.1), "dogs")
parts["10b_patines"] = (shoes, (0.25, 0.25, 0.28), "shoes")
parts["11_pasadores_articulacion"] = (apins, (0.3, 0.3, 0.32), None)

# ---------------- ensamble y exportación ----------------
assy = cq.Assembly(name="TT300-C")
for name, (wp, col, _) in parts.items():
    assy.add(wp, name=name, color=cq.Color(*col, 1.0))
OUT.mkdir(parents=True, exist_ok=True)
assy.save(str(OUT / "TT300-C.step"))
assy.save(str(OUT / "TT300-C.glb"))

# ---------------- control de masas: modelo 3D frente al núcleo ----------------
vol = {n: wp.val().Volume() for n, (wp, _, _) in parts.items()}
M = DV["masas"]
cmp = [("Plancha base", vol["1a_plancha_base"] * RHO, M["base"]),
       ("Marco", vol["1b_marco"] * RHO, M["rim"]),
       ("Ménsulas", vol["1c_menuslas"] * RHO, M["brackets"]),
       ("Mesa (planchas, almas, nervios, cubo)", vol["2_mesa"] * RHO, M["top"] + M["bot"] + M["webs"] + M["ribs"] + M["hub"]),
       ("Pasadores de empuje", vol["3_pasadores"] * RHO, M["pins"]),
       ("Pivote", vol["5_pivote"] * RHO, M["pivot"]),
       ("Uñas", vol["10_unas"] * RHO, M["dogs"]),
       ("Patines", vol["10b_patines"] * RHO, M["shoes"]),
       ("Bancadas de guía", vol["1e_bancadas"] * RHO, M["beds"])]
# ---------------- control de interferencias entre piezas que no deben tocarse ----------------
# todos los pares de piezas: las piezas ajustadas (pasador en agujero, buje en cubo, piezas apiladas) solo comparten caras (volumen 0)
names = list(parts)
PAIRS = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
inter = []
for a_, b_ in PAIRS:
    try:
        v = parts[a_][0].val().intersect(parts[b_][0].val()).Volume()
    except Exception as e:
        v = float("nan")
    inter.append({"a": a_, "b": b_, "vol_mm3": round(v, 1), "ok": bool(v < 1.0)})
rep = {"interferencias": inter, "partes": {n: round(v * RHO, 2) for n, v in vol.items()}, "comparacion": [{"pieza": a, "modelo3d": round(b, 1), "nucleo": round(c, 1), "dif_%": round((b - c) / c * 100, 1)} for a, b, c in cmp]}
# diferencias conocidas de la fórmula del núcleo para el patín (no se fuerzan en el modelo; se informan)
neck_dz = 0                                                                       # el núcleo ya usa el cuello real h_ranura + 1 con cabeza T
pocket_open = max(0.0, (zc + P["dog_h"] / 2 + cl1) - KG["shoeTop"])            # alojamiento más alto que la caja del patín
nuc = [{"pieza": "Patines", "causa": "cuello de la lengüeta: el núcleo usa h_ranura − 2; con cabeza T el cuello mide h_ranura + 1",
        "kg": round(P["n_cyl"] * RHO * KG["L_s"] * (P["w_slot"] - 2) * neck_dz, 2)},
       {"pieza": "Patines", "causa": f"alojamiento de la uña (alto h_uña + 2) abierto {pocket_open:.0f} mm por la cara superior de la caja: el núcleo descuenta el alto completo",
        "kg": round(P["n_cyl"] * RHO * pocket_open * (P["dog_b"] + 2) * (KG["pocketEnd"] + cl1 - (P["x_g"] - P["w_s"] / 2)), 2)}]
nuc = [r for r in nuc if abs(r["kg"]) > 0.005]
rep["diferencias_nucleo"] = nuc
json.dump(rep, open(OUT / "TT300-C_masas3d.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{'Pieza':40s} {'3D kg':>9s} {'Núcleo kg':>10s} {'Δ %':>7s}")
for r in rep["comparacion"]:
    print(f"{r['pieza']:40s} {r['modelo3d']:9.1f} {r['nucleo']:10.1f} {r['dif_%']:7.1f}")
for r in nuc:
    print(f"  Diferencia de la fórmula del núcleo: {r['pieza']} {r['kg']:+.2f} kg · {r['causa']}")
print(f"  Residual del patín sin esas diferencias: {(rep['partes']['10b_patines'] - sum(r['kg'] for r in nuc) - M['shoes']) / M['shoes'] * 100:+.2f} %")
print("\nInterferencias (volumen común, debe ser 0):")
for r in inter:
    print(f"  {'OK ' if r['ok'] else 'XX '} {r['a']:28s} × {r['b']:28s} {r['vol_mm3']:12.1f} mm³")
big = [r for r in rep["comparacion"] if abs(r["dif_%"]) > 1.0]
if big:
    print("\nDiferencias de masa > 1 % (revisar la fórmula del núcleo o la geometría):", ", ".join(f"{r['pieza']} {r['dif_%']:+.1f} %" for r in big))
print("STEP y GLB en", OUT)
if not all(r["ok"] for r in inter):
    sys.exit("Hay interferencias entre piezas: revisar geometría")
