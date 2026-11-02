"""Modelo 3D TT300-C (CadQuery) desde cad/out/TT300-C_design.json: STEP de ensamble, GLB y control de masas.
Uso: python3 cad/modelo3d_tt300c.py [design.json]
Ejes: z vertical desde la cara inferior de la base; x, y en planta como en los planos."""
import json, math, sys, pathlib
import cadquery as cq

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "cad" / "out"
D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else OUT / "TT300-C_design.json", encoding="utf-8"))
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
cap_D, cap_t = P["D_piv"] + 60, 15
hole_top = cap_D + 20
BR = DV["bracket"]
Llug = 2.5 * P["d_pp"]
forkH = DV["forkH"]
fork_w = 2.4 * P["d_pp"]
nose_R = d_pin / 2 + 1
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
for (x, y) in [(cl, 0), (-cl, 0), (0, cl), (0, -cl)]:
    l = cyl(35, 25, tb, x, y).union(cyl(20, 40, tb + 25, x, y))
    lugs = l if lugs is None else lugs.union(l)
parts["1d_puntos_izaje"] = (lugs, (0.9, 0.2, 0.15), None)

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
parts["8_tapa_inspeccion"] = (cyl(hole_top / 2 - 1, 8, z0 + hd - 8), (0.22, 0.4, 0.7), None)

# ---------------- cilindros, uñas y pasadores de articulación (giro horario, al tomar el pasador) ----------------
cyls = dogs = apins = None
for c in D["cilindros"]["horario"]:
    E, g = c["eye"], c["engage"]
    u = g["u"]; ph = math.degrees(math.atan2(u[1], u[0]))
    Lr = math.hypot(g["rod"][0] - E[0], g["rod"][1] - E[1])        # ojal → pasador del vástago
    Lb = P["L0"] - 75
    def along(wp):
        return place(wp, ph, E)
    body = cq.Workplane("YZ").workplane(offset=55).center(0, zc).circle(P["D_body"] / 2).extrude(Lb - 55)
    rod = cq.Workplane("YZ").workplane(offset=Lb).center(0, zc).circle(P["d_rod"] / 2).extrude(Lr - 52 - Lb)
    eye0 = cyl(52.5, P["b_eye"], zc - P["b_eye"] / 2, 0, 0)
    eye1 = cyl(52.5, P["b_eye"], zc - P["b_eye"] / 2, Lr, 0)
    cy = along(body.union(rod).union(eye0).union(eye1))
    cyls = cy if cyls is None else cyls.union(cy)
    # uña: horquilla + cuerpo + asiento
    Ld = P["d_dog"]
    fork = box(Lr - fork_w / 2, Lr + fork_w / 2, -fork_w / 2, fork_w / 2, zc - forkH / 2, zc + forkH / 2).cut(
        box(Lr - fork_w / 2 - 1, Lr + fork_w / 2 + 1, -fork_w / 2 - 1, fork_w / 2 + 1, zc - P["b_eye"] / 2 - P["g_ch"], zc + P["b_eye"] / 2 + P["g_ch"]))
    bodyd = box(Lr + fork_w / 2 - 5, Lr + Ld, -P["dog_b"] / 2, P["dog_b"] / 2, zc - P["dog_h"] / 2, zc + P["dog_h"] / 2)
    dog = fork.union(bodyd).cut(cyl(nose_R, forkH + 10, zc - forkH / 2 - 5, Lr + Ld, 0)).cut(cyl(P["d_pp"] / 2, forkH + 10, zc - forkH / 2 - 5, Lr, 0))
    dg = along(dog)
    dogs = dg if dogs is None else dogs.union(dg)
    ap = along(cyl(P["d_pp"] / 2, forkH + 30, zc - forkH / 2 - 15, Lr, 0)).union(cyl(P["d_pp"] / 2, BR["H"] + 20, tb - 5, E[0], E[1]))
    apins = ap if apins is None else apins.union(ap)
parts["9_cilindros"] = (cyls, (0.95, 0.78, 0.1), None)
parts["10_unas"] = (dogs, (0.85, 0.35, 0.1), "dogs")
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
       ("Uñas", vol["10_unas"] * RHO, M["dogs"])]
# ---------------- control de interferencias entre piezas que no deben tocarse ----------------
PAIRS = [("2_mesa", "10_unas"), ("3_pasadores", "10_unas"), ("2_mesa", "9_cilindros"), ("3_pasadores", "9_cilindros"),
         ("2_mesa", "1c_menuslas"), ("1c_menuslas", "9_cilindros"), ("1b_marco", "1c_menuslas"), ("2_mesa", "1d_puntos_izaje"),
         ("1b_marco", "1d_puntos_izaje"), ("1c_menuslas", "10_unas"), ("2_mesa", "11_pasadores_articulacion"), ("3_pasadores", "11_pasadores_articulacion"),
         ("4_arandelas_pernos", "10_unas"), ("4_arandelas_pernos", "9_cilindros")]
inter = []
for a_, b_ in PAIRS:
    try:
        v = parts[a_][0].val().intersect(parts[b_][0].val()).Volume()
    except Exception as e:
        v = float("nan")
    inter.append({"a": a_, "b": b_, "vol_mm3": round(v, 1), "ok": bool(v < 1.0)})
rep = {"interferencias": inter, "partes": {n: round(v * RHO, 2) for n, v in vol.items()}, "comparacion": [{"pieza": a, "modelo3d": round(b, 1), "nucleo": round(c, 1), "dif_%": round((b - c) / c * 100, 1)} for a, b, c in cmp]}
json.dump(rep, open(OUT / "TT300-C_masas3d.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{'Pieza':40s} {'3D kg':>9s} {'Núcleo kg':>10s} {'Δ %':>7s}")
for r in rep["comparacion"]:
    print(f"{r['pieza']:40s} {r['modelo3d']:9.1f} {r['nucleo']:10.1f} {r['dif_%']:7.1f}")
print("\nInterferencias (volumen común, debe ser 0):")
for r in inter:
    print(f"  {'OK ' if r['ok'] else 'XX '} {r['a']:28s} × {r['b']:28s} {r['vol_mm3']:12.1f} mm³")
print("STEP y GLB en", OUT)
if not all(r["ok"] for r in inter):
    sys.exit("Hay interferencias entre piezas: revisar geometría")
