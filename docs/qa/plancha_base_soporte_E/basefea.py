"""FEA de la base completa (Mindlin Q4 + vigas de emparrillado + 2 soportes rígidos + contacto unilateral con la losa rígida).
Unidades N, mm, MPa. Estudio de opciones para la plancha base bajo el soporte del ojal E."""
import json, math, sys
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl

G_ = 9.80665; RHO = 7.85e-6   # kg/mm3


class Base:
    def __init__(self, ex, hm=40.0, t=None, tfield=None):
        self.ex = ex; P = ex["P"]; self.P = P
        self.hm = hm; self.Bh = P["B"] / 2; n = int(round(P["B"] / hm)); self.n = n
        xs = np.linspace(-self.Bh, self.Bh, n + 1)
        self.X = np.repeat(xs, n + 1); self.Y = np.tile(xs, n + 1); self.nn = self.X.size
        self.els = np.array([[i * (n + 1) + j, (i + 1) * (n + 1) + j, (i + 1) * (n + 1) + j + 1, i * (n + 1) + j + 1] for i in range(n) for j in range(n)])
        self.ec = np.array([[self.X[e].mean(), self.Y[e].mean()] for e in self.els])
        self.t0 = t if t is not None else P["t_base"]
        self.te = np.full(len(self.els), float(self.t0))
        if tfield is not None: self.te = np.array([tfield(x, y, self.t0) for x, y in self.ec], float)
        self.E_, self.nu = P["E"], P["nu"]
        self.beams = []      # (n1, n2, EI, GJ, kGA, meta)
        self.rigid_extra = [[], []]   # nodos extra ligados a cada soporte
        self.nodal_mass = np.zeros(self.nn)   # kg extra por nodo (vigas, nervios)

    def node(self, x, y):
        i = int(round((x + self.Bh) / self.hm)); j = int(round((y + self.Bh) / self.hm)); return i * (self.n + 1) + j

    # ---- soportes rígidos: huella de las paredes (marco local del cilindro 1; el 2 por rotación de 180°)
    def support_nodes(self, cil):
        E = np.array(self.ex["E"]); hm = self.hm
        X, Y = (self.X, self.Y) if cil == 1 else (-self.X, -self.Y)
        Xl, Yl = X - E[0], Y - E[1]   # sx = 1, sy = -1: local = real − E (cilindro 1)
        m = np.zeros(self.nn, bool)
        for (x0, x1, y0, y1) in self.ex["walls"]:
            m |= (Xl >= x0 - hm / 2) & (Xl <= x1 + hm / 2) & (Yl >= y0 - hm / 2) & (Yl <= y1 + hm / 2)
        for k in self.rigid_extra[cil - 1]: m[k] = True
        return m

    # ---- vigas sobre líneas de la malla (EI y GJ por unidad; kGA corte)
    def add_beam_line(self, p0, p1, EI, GJ, kGA, mass_per_mm=0.0, tag=""):
        n0 = np.array(p0, float); n1 = np.array(p1, float); L = np.linalg.norm(n1 - n0); d = (n1 - n0) / L
        step = self.hm * (math.sqrt(2) if abs(abs(d[0]) - abs(d[1])) < 1e-9 else 1.0)
        ns = int(round(L / step)); pts = [n0 + (n1 - n0) * k / ns for k in range(ns + 1)]
        ids = [self.node(*p) for p in pts]
        for a, b in zip(ids[:-1], ids[1:]):
            self.beams.append((a, b, EI, GJ, kGA, tag))
            lm = mass_per_mm * math.hypot(self.X[b] - self.X[a], self.Y[b] - self.Y[a]); self.nodal_mass[a] += lm / 2; self.nodal_mass[b] += lm / 2
        return ids

    def assemble(self):
        nn, E_, nu, hm = self.nn, self.E_, self.nu, self.hm
        ah = hm / 2; gq = (-1 / math.sqrt(3), 1 / math.sqrt(3))
        def Bm(xi, et):
            sgx, sgy = (-1, 1, 1, -1), (-1, -1, 1, 1); Bb = np.zeros((3, 12)); Bs = np.zeros((2, 12))
            for k in range(4):
                N = 0.25 * (1 + xi * sgx[k]) * (1 + et * sgy[k]); dx = 0.25 * sgx[k] * (1 + et * sgy[k]) / ah; dy = 0.25 * sgy[k] * (1 + xi * sgx[k]) / ah
                Bb[0, 3 * k + 1] = dx; Bb[1, 3 * k + 2] = dy; Bb[2, 3 * k + 1] = dy; Bb[2, 3 * k + 2] = dx; Bs[0, 3 * k] = dx; Bs[0, 3 * k + 1] = -N; Bs[1, 3 * k] = dy; Bs[1, 3 * k + 2] = -N
            return Bb, Bs
        C = np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])
        Kb1 = sum(Bm(x, y)[0].T @ C @ Bm(x, y)[0] * ah * ah for x in gq for y in gq)   # × D
        B0b, B0s = Bm(0, 0); Ks1 = B0s.T @ B0s * 4 * ah * ah                          # × kGt
        self.B0b = B0b; self.C = C
        dof = np.stack([3 * self.els, 3 * self.els + 1, 3 * self.els + 2], axis=2).reshape(len(self.els), 12); self.dof = dof
        D = E_ * self.te ** 3 / (12 * (1 - nu ** 2)); Gs = 5 / 6 * E_ / (2 * (1 + nu)) * self.te
        vals = (D[:, None, None] * Kb1[None] + Gs[:, None, None] * Ks1[None]).reshape(len(self.els), 144)
        rows = np.repeat(dof, 12, axis=1).ravel(); cols = np.tile(dof, (1, 12)).ravel()
        K = sp.csr_matrix((vals.ravel(), (rows, cols)), shape=(3 * nn, 3 * nn))
        # vigas: Timoshenko (flexión w, θ_s) + torsión θ_n; θ_s = c βx + s βy, θ_n = −s βx + c βy (β = pendientes de la placa)
        R_, C_, V_ = [], [], []
        for (a, b, EI, GJ, kGA, tag) in self.beams:
            dx, dy = self.X[b] - self.X[a], self.Y[b] - self.Y[a]; L = math.hypot(dx, dy); c, s = dx / L, dy / L
            phi = 12 * EI / (kGA * L * L) if kGA > 0 else 0.0
            kb = EI / (L ** 3 * (1 + phi)) * np.array([[12, 6 * L, -12, 6 * L], [6 * L, (4 + phi) * L * L, -6 * L, (2 - phi) * L * L], [-12, -6 * L, 12, -6 * L], [6 * L, (2 - phi) * L * L, -6 * L, (4 + phi) * L * L]])
            kl = np.zeros((6, 6)); idx = [0, 1, 3, 4]   # local: [w1, θs1, θn1, w2, θs2, θn2]
            for i in range(4):
                for j in range(4): kl[idx[i], idx[j]] = kb[i, j]
            kt = GJ / L; kl[2, 2] += kt; kl[5, 5] += kt; kl[2, 5] -= kt; kl[5, 2] -= kt
            T = np.zeros((6, 6))
            for o in (0, 3): T[o, o] = 1; T[o + 1, o + 1] = c; T[o + 1, o + 2] = s; T[o + 2, o + 1] = -s; T[o + 2, o + 2] = c
            kg = T.T @ kl @ T; gd = [3 * a, 3 * a + 1, 3 * a + 2, 3 * b, 3 * b + 1, 3 * b + 2]
            for i in range(6):
                for j in range(6): R_.append(gd[i]); C_.append(gd[j]); V_.append(kg[i, j])
        if R_: K = K + sp.csr_matrix((V_, (R_, C_)), shape=(3 * nn, 3 * nn))
        self.K0 = K.tocsr()

    def weights(self, W_table, Ri, Ro, extra_master=(0.0, 0.0)):
        """cargas de gravedad (hacia abajo: −w): placa (espesor por elemento), vigas, mesa vacía uniforme en el anillo Ri..Ro"""
        f = np.zeros(self.nn); A4 = self.hm * self.hm / 4
        for e, tt in zip(self.els, self.te): f[e] -= RHO * G_ * tt * A4
        f -= self.nodal_mass * G_
        r = np.hypot(self.X, self.Y); ring = (r >= Ri) & (r <= Ro)
        # presión uniforme: reparte por área tributaria aproximada de los nodos dentro del anillo
        q = W_table / (math.pi * (Ro * Ro - Ri * Ri)); f[ring] -= q * self.hm * self.hm
        self.W_table_applied = q * self.hm * self.hm * ring.sum()
        return f

    def solve(self, moments, fz, hold=None, kc=1e7, maxit=300, masters_w=None, fext=None):
        """moments: [(Mx, My)] por soporte (N·mm); fz: fuerzas nodales verticales (N, + hacia arriba). hold: nodos bilaterales (mesa cargada).
        fext: cargas nodales adicionales (vector 3·nn: [w, β_x, β_y] por nudo; un momento (Mx, My) en un nudo libre entra como −My en β_x y Mx en β_y)."""
        nn = self.nn
        if getattr(self, "_T", None) is None:
            sup = [self.support_nodes(1), self.support_nodes(2)]
            inS = sup[0] | sup[1]
            fn = np.where(~inS)[0]; free = np.stack([3 * fn, 3 * fn + 1, 3 * fn + 2], axis=1).ravel(); nf = free.size
            Tr, Tc, Tv = [free], [np.arange(nf)], [np.ones(nf)]
            E = np.array(self.ex["E"]); cent = [E, -E]
            for si in range(2):
                k = np.where(sup[si])[0]; o = np.ones(k.size)
                Tr += [3 * k, 3 * k, 3 * k, 3 * k + 1, 3 * k + 2]; Tc += [o * (nf + 3 * si), o * (nf + 3 * si + 1), o * (nf + 3 * si + 2), o * (nf + 3 * si + 1), o * (nf + 3 * si + 2)]
                Tv += [o, self.X[k] - cent[si][0], self.Y[k] - cent[si][1], o, o]
            T = sp.csr_matrix((np.concatenate(Tv), (np.concatenate(Tr), np.concatenate(Tc).astype(int))), shape=(3 * nn, nf + 6))
            self._T = T; self._Kr = (T.T @ self.K0 @ T).tocsr(); self._nf = nf; self.inS = inS
            W = sp.csr_matrix((np.ones(nn), (np.arange(nn), 3 * np.arange(nn))), shape=(nn, 3 * nn)); self._Tw = (W @ T).tocsr()
        T, Kr, nf, inS = self._T, self._Kr, self._nf, self.inS
        fg = np.zeros(3 * nn); fg[0::3] = fz
        if fext is not None: fg = fg + fext
        rhs = T.T @ fg
        for si, (Mx, My) in enumerate(moments):
            rhs[nf + 3 * si + 1] += -My; rhs[nf + 3 * si + 2] += Mx
            if masters_w is not None: rhs[nf + 3 * si] += masters_w[si]
        hold = np.zeros(nn, bool) if hold is None else hold
        act = np.ones(nn, bool); seen = set(); partial = False; Tw = self._Tw
        for it in range(maxit):
            kv = np.where(act | hold, kc, 1e-3)
            ur = spl.spsolve((Kr + Tw.T @ sp.diags(kv) @ Tw).tocsc(), rhs); u = T @ ur; w = u[0::3]
            rel = act & ~hold & (w > 1e-9); add = ~act & (w < -1e-9)
            if not rel.any() and not add.any(): break
            new = act.copy()
            if partial:   # ciclo: solo el 10 % de los peores
                if add.any(): idx = np.where(add)[0]; k = max(1, idx.size // 10); new[idx[np.argsort(w[idx])[:k]]] = True
                if rel.any(): idx = np.where(rel)[0]; k = max(1, idx.size // 10); new[idx[np.argsort(-w[idx])[:k]]] = False
            else:
                new[rel] = False; new[add] = True
            key = hash(new.tobytes())
            if key in seen: partial = True
            seen.add(key); act = new
        self.conv = it < maxit - 1
        self.u = u; self.w = w; self.act = act; self.it = it
        self.react = np.where(act | hold, -kc * w, 0.0)
        return u

    def plate_stress(self, skip_support=True, exclude_r=None):
        """σ_vM máx en los centros de elemento (flexión, fibra extrema); devuelve (σ, x, y)"""
        u = self.u; best = (0.0, 0, 0)
        D = self.E_ * self.te ** 3 / (12 * (1 - self.nu ** 2))
        ue = u[self.dof]                      # (ne, 12)
        kap = ue @ self.B0b.T                 # (ne, 3)
        m = D[:, None] * (kap @ self.C.T)     # momentos por unidad
        s = 6 * m / self.te[:, None] ** 2
        vm = np.sqrt(s[:, 0] ** 2 - s[:, 0] * s[:, 1] + s[:, 1] ** 2 + 3 * s[:, 2] ** 2)
        mask = np.ones(len(self.els), bool)
        if skip_support: mask &= ~self.inS[self.els].all(axis=1)
        if exclude_r is not None: mask &= exclude_r(self.ec[:, 0], self.ec[:, 1])
        i = np.argmax(np.where(mask, vm, -1)); self.vm = vm; self.mplate = m
        return vm[i], self.ec[i, 0], self.ec[i, 1]

    def beam_forces(self):
        """momento flector y torsor máx por etiqueta (N·mm)"""
        out = {}
        for (a, b, EI, GJ, kGA, tag) in self.beams:
            dx, dy = self.X[b] - self.X[a], self.Y[b] - self.Y[a]; L = math.hypot(dx, dy); c, s = dx / L, dy / L
            ua = self.u[3 * a:3 * a + 3]; ub = self.u[3 * b:3 * b + 3]
            ts = lambda q: c * q[1] + s * q[2]; tn = lambda q: -s * q[1] + c * q[2]
            phi = 0.0
            # momentos de extremo (Euler-Bernoulli)
            w1, t1, w2, t2 = ua[0], ts(ua), ub[0], ts(ub)
            M1 = EI / L ** 2 * (-6 * w1 - 4 * L * t1 + 6 * w2 - 2 * L * t2)
            M2 = EI / L ** 2 * (6 * w1 + 2 * L * t1 - 6 * w2 + 4 * L * t2)
            Tq = GJ / L * (tn(ub) - tn(ua)); V = EI / L ** 3 * (12 * w1 + 6 * L * t1 - 12 * w2 + 6 * L * t2)
            o = out.setdefault(tag, {"M": 0.0, "T": 0.0, "V": 0.0, "at": None})
            mm = max(abs(M1), abs(M2))
            if mm > o["M"]: o["M"] = mm; o["at"] = (self.X[a], self.Y[a])
            o["T"] = max(o["T"], abs(Tq)); o["V"] = max(o["V"], abs(V))
        return out


def mom(ex, F, psi, sgn, cil1_only=False):
    """momentos (Mx, My) en los dos soportes: F en E a la altura h, f = sgn·u(ψ) (marco local = real en el cilindro 1); cilindro 2: −M"""
    f = np.array([sgn * math.cos(psi), sgn * math.sin(psi)]); h = ex["h"]
    Mx, My = -h * F * f[1], h * F * f[0]
    return [(Mx, My), (0.0, 0.0) if cil1_only else (-Mx, -My)]
