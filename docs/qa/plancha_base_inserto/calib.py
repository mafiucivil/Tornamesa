"""Grilla de calibración: python3 calib.py geo.json design.json out.jsonl gap clr"""
import json, math, sys, os, itertools
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], "20", "105", sys.argv[4], sys.argv[5], "50", "445.32", "40", "0", "muesca", sys.argv[3]]
import sweep, fe

OUT = sys.argv[12]


def job(a):
    tb, ti, h, F = a; psi = sweep.band[0]; u = (math.cos(math.radians(psi)), math.sin(math.radians(psi)))
    tv = fe.tvec_poly([sweep.poly1, sweep.poly2], ti, tb)
    r = fe.caso(F * 1e3, u, sweep.E1, sweep.rects, h, sweep.B, tv, sweep.W_tab, sweep.Rt, hm=40.0)
    s = fe.summary(r, tb); s.update(t_base=tb, t_ins=ti, h=h, F=F); return s


if __name__ == "__main__":
    grid = [(tb, ti, h, 445.32) for tb in (16, 20, 25) for ti in (40, 45, 50, 55, 60, 70, 80, 90, 100, 110) for h in (105,) if ti > tb + 5] + [(20, ti, 160, 445.32) for ti in (60, 80, 100)]
    grid += [(20, 55, 105, F) for F in (207.5,)]
    print("inserto", [(round(x), round(y)) for x, y in sweep.poly1], flush=True)
    with Pool(4) as p, open(OUT, "w") as f:
        for s in p.imap_unordered(job, grid):
            s = {k: (float(v) if hasattr(v, "__float__") and not isinstance(v, (bool, tuple)) else v) for k, v in s.items()}
            s["donde"] = [float(x) for x in s["donde"]]; s["donde_base"] = [float(x) for x in s["donde_base"]]
            f.write(json.dumps(s) + "\n"); f.flush()
            print(s["t_base"], s["t_ins"], s["h"], s["F"], round(s["lejos_ins"], 1), round(s["lejos_base"], 1), flush=True)
