"""Barrido del inserto: python3 sweep.py geo.json design.json t_base h gap clr 'tins1,tins2' 'F1,F2' [mesh] [psi idx] [forma]"""
import json, math, sys, os
import numpy as np
from multiprocessing import Pool
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(__file__))
import fe

G = json.load(open(sys.argv[1])); D = json.load(open(sys.argv[2]))
tb, h, gap, clr = map(float, sys.argv[3:7]); tins_l = [float(v) for v in sys.argv[7].split(",")]; F_l = [float(v) for v in sys.argv[8].split(",")]
hm = float(sys.argv[9]) if len(sys.argv) > 9 else 40.0
psi_i = [int(v) for v in sys.argv[10].split(",")] if len(sys.argv) > 10 else [0]
forma = sys.argv[11] if len(sys.argv) > 11 else "muesca"
PV = D["pivotado"]; SE = PV["fabricacion"]["soporte_E"]; E1 = tuple(PV["E"]); B = D["P"]["B"]; Bh = B / 2; Rt = D["P"]["D_top"] / 2
rects = [(min(x for x, _ in p["poligono_local"]), max(x for x, _ in p["poligono_local"]), min(y for _, y in p["poligono_local"]), max(y for _, y in p["poligono_local"])) for p in SE["piezas"] if p["id"].startswith(("pared", "munon"))]
c = (Rt + gap) * math.sqrt(2)
tri = Polygon([(Bh, -Bh), (Bh, Bh - c), (-Bh + c, -Bh)])
ob_a = unary_union([Polygon(o["poly"]) for o in G["plates"] if o["id"].endswith("1_antihorario")] + [Polygon(o["poly"]) for o in G["mov"] if o["id"].startswith("cubo") and " c1 antihorario" in o["id"]])
ob_h = unary_union([Polygon(o["poly"]) for o in G["plates"] if o["id"].endswith("1_horario")] + [Polygon(o["poly"]) for o in G["mov"] if o["id"].startswith("cubo") and " c1 horario" in o["id"]])
if forma == "muesca":
    xa, ya = ob_a.bounds[0] - clr, ob_a.bounds[1] - clr; xh, yh = ob_h.bounds[2] + clr, ob_h.bounds[3] + clr
    ins = tri.difference(box(xa, ya, Bh + 1, Bh + 1)).difference(box(-Bh - 1, -Bh - 1, xh, yh))
elif forma == "exacta":
    ins = tri.difference(ob_a.buffer(clr)).difference(ob_h.buffer(clr))
else:
    ins = tri
if ins.geom_type != "Polygon": ins = max(ins.geoms, key=lambda g: g.area)
poly1 = [tuple(map(float, q)) for q in list(ins.exterior.coords)[:-1]]; poly2 = [(-x, -y) for x, y in poly1]
W_tab = D["derivados"]["N"] * 1e3
band = SE["ventana"]["sector_deg"]


def job(a):
    t_ins, F, ip = a; psi = band[ip]; u = (math.cos(math.radians(psi)), math.sin(math.radians(psi)))
    tv = fe.tvec_poly([poly1, poly2], t_ins, tb)
    r = fe.caso(F * 1e3, u, E1, rects, h, B, tv, W_tab, Rt, hm=hm)
    s = fe.summary(r, tb); s.update(t_ins=t_ins, F=F, psi=psi); return s


if __name__ == "__main__":
    print(f"inserto ({forma}): área {ins.area / 1e6:.3f} m², vértices {[(round(x), round(y)) for x, y in poly1]}")
    cap = 1.25 * 345 / 3
    jobs = [(t, F, ip) for t in tins_l for F in F_l for ip in psi_i]
    with Pool(4) as p:
        for s in p.imap(job, jobs):
            print(f"t_ins {s['t_ins']:5.0f} F {s['F']:6.1f} ψ {s['psi']:6.1f} M {s['M']:6.2f}  pico {s['pico']:6.0f}  >100: {s['lejos']:6.1f} (FU {s['lejos'] / cap:5.2f}) en {s['donde']}; base {s['lejos_base']:6.1f} (FU {s['lejos_base'] / cap:5.2f}) en {s['donde_base']}; inserto {s['lejos_ins']:6.1f} (FU {s['lejos_ins'] / cap:5.2f}); w {s['w']:5.2f} {'ok' if s['conv'] else 'NC'}", flush=True)
