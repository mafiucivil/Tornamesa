"""Grilla de calibración del modo guiado (4 insertos, ménsulas en (±x_g; ∓y_ojal)). python3 gcalib.py out.jsonl gap clr"""
import json, math, sys, os
from multiprocessing import Pool
from shapely.geometry import Polygon, box
sys.path.insert(0, os.path.dirname(__file__))
import fe
OUT, gap, clr = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
B = 2560.0; Bh = B / 2; Rt = 1000.0; E1 = (1140.0, -945.1269627760763); rects = [(75, 100, -115, 210), (-100, -75, -115, 210)]
x0b, y1b = 1017.5, 682.6269627760763
c = (Rt + gap) * math.sqrt(2)
tri = Polygon([(Bh, -Bh), (Bh, Bh - c), (-Bh + c, -Bh)])
ins = tri.difference(box(x0b - clr, -y1b - clr, Bh + 1, Bh + 1))
p1 = [tuple(map(float, q)) for q in list(ins.exterior.coords)[:-1]]
polys = [p1, [(-x, -y) for x, y in p1], [(x, -y) for x, y in p1][::-1], [(-x, y) for x, y in p1][::-1]]
W_tab = 2956.0087016035322e3
Fret = math.pi / 4 * (190.0 ** 2 - 110.0 ** 2) * 0 / 10   # no usado


def job(a):
    tb, ti, kind, F = a
    tv = fe.tvec_poly(polys, ti, tb)
    if kind == "emp": r = fe.caso(F * 1e3, (0.0, 1.0), E1, rects, 105.0, B, tv, W_tab, Rt)
    elif kind == "ret": r = fe.caso(F * 1e3, (0.0, 1.0), E1, rects, 105.0, B, tv, W_tab, Rt, sense=1)
    else: r = fe.caso(F * 1e3, (0.0, 1.0), E1, rects, 105.0, B, tv, 14.0137e3, Rt, table="weight")
    s = fe.summary(r, tb); s.update(t_base=tb, t_ins=ti, kind=kind, F=F); return s


if __name__ == "__main__":
    grid = [(tb, ti, "emp", 445.32) for tb in (16, 20, 25) for ti in (30, 35, 40, 45, 50, 55, 60, 70, 80, 90, 100) if ti > tb + 5]
    grid += [(20, ti, "ret", 64.89) for ti in (35, 45, 55)] + [(20, ti, "vac", F) for ti in (35, 55) for F in (3.0, 10.0)]
    print("inserto guiado", [(round(x), round(y)) for x, y in p1], round(ins.area / 1e6, 3), flush=True)
    with Pool(4) as p, open(OUT, "w") as f:
        for s in p.imap_unordered(job, grid):
            s = {k: (float(v) if hasattr(v, "__float__") and not isinstance(v, (bool, tuple, str)) else v) for k, v in s.items()}
            s["donde"] = [float(x) for x in s["donde"]]; s["donde_base"] = [float(x) for x in s["donde_base"]]
            f.write(json.dumps(s) + "\n"); f.flush()
            print(s["kind"], s["t_base"], s["t_ins"], s["F"], round(s["lejos"], 2), s["donde"], round(s["w"], 3), s["conv"], flush=True)
