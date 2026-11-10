"""Inserto de t con rebaje a t_r bajo el barrido del cuerpo del cilindro. python3 pocket.py t t_r gap clr h"""
import json, math, sys, os
import numpy as np
from matplotlib.path import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(__file__))
t, tr, gap, clr, h = map(float, sys.argv[1:6])
sys.argv = [sys.argv[0], "g_def.json", "../ins_d2.json", "20", str(h), str(gap), str(clr), "50", "445.32", "40", "0", "muesca"]
import sweep, fe
U = unary_union([Polygon(o["poly"]) for o in sweep.G["mov"] if o["id"].startswith("cuerpo") and " c1 " in o["id"]])
polys = [list(g.exterior.coords) for g in (U.geoms if U.geom_type == "MultiPolygon" else [U])]
paths = [Path(np.array(p)) for p in polys] + [Path(-np.array(p)) for p in polys]
base = fe.tvec_poly([sweep.poly1, sweep.poly2], t, 20.0)
def tv(x, y):
    tt = base(x, y); pts = np.column_stack([x, y]); m = np.zeros(x.shape, bool)
    for pa in paths: m |= pa.contains_points(pts)
    tt[m] = np.minimum(tt[m], tr); return tt
psi = sweep.band[0]; u = (math.cos(math.radians(psi)), math.sin(math.radians(psi)))
r = fe.caso(445.32e3, u, sweep.E1, sweep.rects, h, sweep.B, tv, sweep.W_tab, sweep.Rt)
s = fe.summary(r, 20.0)
print(f"t {t} rebaje {tr} gap {gap} clr {clr}: lejos {s['lejos']:.1f} (FU {s['lejos'] / 143.75:.3f}) en {s['donde']}; base {s['lejos_base']:.1f} ins {s['lejos_ins']:.1f}; área del barrido {U.area / 1e6:.3f} m²")
