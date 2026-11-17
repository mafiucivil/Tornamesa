"""Desviaciones ISO 286-1/-2 (µm) para los ajustes usados en TT300-C (diámetros 3–315 mm; letras f, g, h, m, p, s / F, G, H; grados IT6–IT12)."""
RANGES = [(3, 6), (6, 10), (10, 18), (18, 30), (30, 50), (50, 80), (80, 120), (120, 180), (180, 250), (250, 315)]
IT = {6: [8, 9, 11, 13, 16, 19, 22, 25, 29, 32], 7: [12, 15, 18, 21, 25, 30, 35, 40, 46, 52], 8: [18, 22, 27, 33, 39, 46, 54, 63, 72, 81],
      9: [30, 36, 43, 52, 62, 74, 87, 100, 115, 130], 10: [48, 58, 70, 84, 100, 120, 140, 160, 185, 210], 11: [75, 90, 110, 130, 160, 190, 220, 250, 290, 320],
      12: [120, 150, 180, 210, 250, 300, 350, 400, 460, 520]}
FD = {"f": [-10, -13, -16, -20, -25, -30, -36, -43, -50, -56], "g": [-4, -5, -6, -7, -9, -10, -12, -14, -15, -17], "h": [0] * 10,
      "m": [4, 6, 7, 8, 9, 11, 13, 15, 17, 20], "p": [12, 15, 18, 22, 26, 32, 37, 43, 50, 56]}
S_RANGES = [(3, 6, 19), (6, 10, 23), (10, 18, 28), (18, 30, 35), (30, 50, 43), (50, 65, 53), (65, 80, 59), (80, 100, 71), (100, 120, 79), (120, 140, 92), (140, 160, 100), (160, 180, 108),
            (180, 200, 122), (200, 225, 130), (225, 250, 140)]
P_RANGES = [(3, 6, 12), (6, 10, 15), (10, 18, 18), (18, 30, 22), (30, 50, 26), (50, 80, 32), (80, 120, 37), (120, 180, 43), (180, 250, 50), (250, 315, 56)]


def _idx(d):
    for i, (a, b) in enumerate(RANGES):
        if a < d <= b:
            return i
    raise ValueError(f"diámetro {d} fuera de 3–315 mm")


def it(d, g):
    return IT[g][_idx(d)]


def dev(d, code):
    """code: 'H7', 'p6', 'f8'... -> (inferior, superior) en µm."""
    letter, grade = code[0], int(code[1:])
    i = _idx(d)
    t = IT[grade][i]
    lo = letter.lower()
    if lo == "s":
        fd = next(v for a, b, v in S_RANGES if a < d <= b)
    elif lo == "p":
        fd = next(v for a, b, v in P_RANGES if a < d <= b)
    else:
        fd = FD[lo][i]
    if letter == "H":
        return 0, t
    if letter in ("F", "G"):
        e = -FD[lo][i]
        return e, e + t
    if lo in ("f", "g", "h"):
        return fd - t, fd
    return fd, fd + t          # m, p, s: desviación inferior fundamental


def limits(d, code):
    lo, hi = dev(d, code)
    return d + lo / 1000.0, d + hi / 1000.0


def fmt_dev(d, code):
    lo, hi = dev(d, code)
    s = lambda v: ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v) / 1000:.3f}".replace(".", ",")
    return f"{s(hi)} / {s(lo)}" if hi != 0 or lo != 0 else "0"


def fit(d, hole, shaft):
    """Ajuste agujero/eje: holgura mínima/máxima (µm), tipo."""
    hl, hh = dev(d, hole)
    sl, sh = dev(d, shaft)
    cmin, cmax = hl - sh, hh - sl
    tipo = "con juego" if cmin >= 0 else "con aprieto" if cmax <= 0 else "incierto (transición)"
    return dict(cmin=cmin, cmax=cmax, tipo=tipo)
