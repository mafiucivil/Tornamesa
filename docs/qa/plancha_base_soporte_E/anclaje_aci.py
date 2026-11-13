"""Opción A2: requisitos mínimos ORIENTATIVOS del anclaje según ACI 318-19 cap. 17 (docs/qa/plancha_base_soporte_E.md §5).
No es un diseño: f'c, espesor, armadura, fisuración y distancias a los bordes de la losa no se conocen; se declaran como hipótesis.
Uso: python3 anclaje_aci.py [f'c en MPa]   (por defecto 25)
Unidades: N, mm, MPa."""
import math, sys

fc = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0
LF = 1.6                                  # hipótesis: la fuerza a calado se trata como carga variable L (ACI 318-19 §5.3.1: U = 1,2D + 1,6L; el peso propio no se descuenta)
phi_s, phi_c, phi_a = 0.75, 0.65, 0.65    # Tabla 17.5.3: acero dúctil en tracción; arrancamiento del hormigón y adherencia, condición B, anclaje posinstalado categoría 1
kc, lam = 7.0, 1.0                        # §17.6.2.2.1 (SI): k_c = 7 para anclajes posinstalados (10 si van hormigonados); hormigón de peso normal
Ase = {16: 157.0, 20: 245.0, 24: 353.0, 30: 561.0}   # área resistente a tracción, ISO 898-1 (rosca métrica gruesa)
futa = min(800.0, 1.9 * 640.0, 860.0)                 # 8.8: f_u = 800, f_y = 640 (§17.6.1.2: f_uta ≤ mín(1,9·f_ya; 860 MPa))
print(f"f'c = {fc:.0f} MPa (hipótesis), hormigón fisurado (ψ_c,N = 1,0), anclaje aislado y lejos de los bordes (A_Nc = A_Nco, ψ_ed,N = 1,0), varilla ISO 898-1 8.8")
for nm, Nk in (("por defecto", 48.2e3), ("interfaz B", 75.1e3)):
    Nua = LF * Nk
    d_s = next(d for d in sorted(Ase) if phi_s * Ase[d] * futa >= Nua)
    hef = (Nua / phi_c / (kc * lam * math.sqrt(fc))) ** (2 / 3)        # φ·k_c·λ·√f'c·h_ef^1,5 ≥ N_ua
    print(f"\n{nm}: N_k = {Nk / 1e3:.1f} kN por perno (a calado, sin factor; envolvente de los marcos ≥ 200×20), N_ua = {LF}·N_k = {Nua / 1e3:.1f} kN")
    for d in [x for x in sorted(Ase) if x >= d_s][:3]:
        Ns = phi_s * Ase[d] * futa
        for h in sorted({math.ceil(hef / 10) * 10, 250, 300, 350} - {x for x in (250, 300, 350) if x < hef}):
            tau = Nua / phi_a / (lam * math.pi * d * h)                   # φ·λ_a·τ_cr·π·d_a·h_ef ≥ N_ua (§17.6.5, anclaje aislado)
            print(f"   M{d}: φN_sa = {Ns / 1e3:6.1f} kN (FU {Nua / Ns:4.2f}); h_ef ≥ {hef:4.0f} mm por arrancamiento; con h_ef = {h} mm la adherencia pide τ_cr ≥ {tau:4.1f} MPa (fisurado)")
print("\nTabla 17.6.5.2.5 (valores mínimos sin informe del producto): τ_cr = 1,4 MPa (exterior, fisurado) o 2,1 MPa (interior, fisurado): no hay solución práctica con")
print("esos valores; el producto tiene que estar calificado según ACI 355.4 (adhesivos) y su informe dar τ_cr y las distancias mínimas a los bordes y entre anclajes.")
