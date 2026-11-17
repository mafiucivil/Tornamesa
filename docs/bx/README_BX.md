# TT300-BX · Tornamesa con disco inoxidable atornillado y pastillas de UHMW (módulo aparte)

Fecha: 16-11-2026. Módulo: `packages/core/tt300bx.js` (sobre el núcleo `packages/core/tt300c.js`), agentes `packages/agents/agentes_bx.js`,
exportador `tools/export_design_bx.js`, pruebas `tests/test_tt300bx.js`. El núcleo TT300-C no cambia de comportamiento: el único cambio es un
gancho aditivo `P.__bx` (opción B y solo si `P.__bx` existe); sin él el núcleo es bit-idéntico a `a67d98e` (prueba JSON de 7 configuraciones
y subconjunto golden de `tests/test_tt300c.js` en `tests/test_tt300bx.js`).

## 1. Concepto

- **Disco de la mesa**: un disco inoxidable macizo Ø 2000 (R_i = 131 mm, el agujero del collar) atornillado a la plancha inferior de la mesa
  con tornillos avellanados ISO 10642 10.9 (cabeza 0,5 mm + sobreespesor bajo la cara de deslizamiento). Se fabrica en **dos semidiscos**
  cortados con plasma y unidos con una **CJP a tope esmerilada a ras** (AWS D1.6) sobre el eje x (que coincide con el nervio de 0°/180°).
  No hay disco en la base.
- **Portador**: plancha de acero S355 cortada con plasma HD, con agujeros circulares, **soldada a la base solo por sus bordes exterior e
  interior** (filetes continuos). En cada agujero una **pastilla de UHMW-PE** torneada, a presión, apoyada en la base, que sobresale h_p y se
  retiene con un tornillo avellanado ISO 10642 8.8 roscado en la base (taladro ciego). El disco de la mesa desliza sobre las pastillas.
- Todo el resto del motor es el de TT300-C (cinemática y accionamiento pivotado, FEA de la mesa, flexión global, izaje de la base con la
  masa del portador, casos de giro, μ de la opción B, térmica, mercado, capacidad por cilindros).

## 2. Hipótesis y criterios (cada fila es una verificación de `BX.analyze`, grupo «Interfaz inox», prefijo «BX ·»)

Carga: la del núcleo, N_D = φ_d·W + peso de la mesa (con el disco), distribución lineal de Navier q = q_med·(1 + k_q·x·û/R_o) con la
excentricidad dirigida hacia cada pastilla (peor caso por pastilla). μ de la opción B (μ_máx = 0,25). Para las piezas de acero el arrastre se
toma con μ_ef = máx(μ_máx; T_calado/(N·r_u)) = 0,342 (criterio de los topes de acero del núcleo); para el UHMW con μ_máx (criterio de la lámina
B del núcleo). ΔT disco–mesa = máx(dT = 40; 80 − 20; 20 − (−10)) = 60 K. α_UHMW = 190×10⁻⁶/K (mandante).

| Elemento | Verificación | Criterio / referencia |
|---|---|---|
| Pastillas | p = ∫q dA_trib / A_p ≤ p_adm (5 MPa) | Catálogo UHMW (ASTM D4020), confianza C |
| | p + Δp por planitud ≤ p_adm; Δp = d_flat/(c_p + A_p/k_placa), c_p = h_p/E_c(S) + (t−1)/M, k_placa = 16π(D_disco + D_mesa)/s² | Módulo confinado como TT `uhConf` (Gent–Lindley); Timoshenko §19 |
| | p ≤ k_p(80 °C)·p_adm (fila «pend» con FU: dato del proveedor) | registro.md «Temperatura», k_p = 0,40 (C) |
| | PV = p_i·r_i·ω ≤ PV_adm (0,05) | Como la fila PV del núcleo |
| | h_p ≥ g_mín + planitud del portador + desgaste + fluencia + d_flat + flecha de celda | Criterio del proyecto |
| | Aplastamiento contra la pared: μ_máx·p·A_p/(d·(t−1)) ≤ p_adm | Equilibrio; criterio del núcleo para la lámina B |
| | Núcleo central del pie: μ_máx·(h_p + t/2) ≤ d/8 | Resistencia de materiales |
| | Tornillo al corte si tomara todo el arrastre (redundancia) | AISC 360-22 §J3.7 |
| | Tornillo fuera del camino: holgura del agujero del tornillo ≥ holgura en frío (−10 °C) + 0,2 | Criterio del proyecto |
| | Interferencia ≥ 0 a 20 °C; ε radial a 80 °C ≤ 2,5 % | Criterio del proyecto (el ajuste relaja; retiene el tornillo) |
| | Cabeza bajo la cara del portador con ≥ 3 mm de UHMW; engrane ≥ 1,0·d en taladro ciego (remanente 3) | ISO 10642; VDI 2230 (criterio del núcleo) |
| Portador | Ligamento local: F/(lig·t) ≤ Fy/(Nd·√3) | ASME BTH-1 §3-2.3.6 |
| | Corte por torsión en la sección neta crítica: τ = T_cruza(r)/(2πr²·t·η(r)), η exacta por cuerdas, reparto del par entre bordes por C = ∫dr/(r³η) | BTH-1 §3-2.3.6; torsión de corona |
| | Filetes perimetrales exterior e interior con su parte del par: f ≤ 0,60FEXX/(1,20Nd) | AISC 360-22 §J2.4; BTH-1 §3-3.4 |
| | Filete mín./máx.; ligamento ≥ máx(10; t) (plasma); libra el filete del collar | AWS D1.1 T7.7; AISC J2.2b; criterio de taller |
| Disco | t ≥ k + 0,5 + sobreespesor | ISO 10642; criterio del mandante (AF2) |
| | Celda anular entre pastillas (a = d/2 empotrada, b guiada): σ ≤ 0,6Fy; flecha ≤ mín(d_flat; 0,1·h_p) | Timoshenko §17; solución cerrada verificada por diferencias finitas |
| | Vacío local / pastilla faltante / mayor hueco de la malla: 3qa²/(4t²) ≤ 0,6Fy | Timoshenko §16 (como el núcleo) |
| | CJP de semidiscos: máx(σ térmica restringida; σ celda) ≤ 0,6Fy | AWS D1.6 (CJP = metal base); AISC Tabla J2.5 |
| Tornillos del disco | √(V_T² + V_th²) ≤ Fnv·A_b/Ω; V_T = T_calado·r/Σr²; V_th por cadena de resortes de Huth (mesa rígida) | AISC §J3.7; Huth (1986, ASTM STP 927) |
| | Aplastamiento/desgarro en el disco (t_e = t − k/2) y en la mesa; engrane ≥ 1,25d; separación 3d; borde J3.4M; despegue al izar | AISC §J3.11, §J3.4, §J3.5, §J3.6; VDI 2230 |
| Generales | Corrosión galvánica (pend), arranque UHMW tras reposo (pend) | Decisión del proyectista; ensayo |

## 3. Resultados con los valores por defecto (`BX.defaults()`, modo pivotado)

| Pieza | Dimensión adoptada | FU gobernante |
|---|---|---|
| Disco | **Dúplex 2205, t = 8 mm** (t_req 7,33: vacío/hueco de malla; cabeza M10 7,2), 2 semidiscos de 96 kg, masa 193 kg | vacío local 0,83; espesor 0,92 (geo); celda 0,14; CJP 0,14 |
| Tornillos del disco | **140 × ISO 10642 M10 × 25 10.9**, 5 anillos (R169…R969), malla 200 mm, libres de CJP (±30), almas, nervios y pasadores; 84 pasantes en la plancha inferior, 56 ciegos en el anillo inferior | corte combinado 0,59 (V_T 8,3 kN, V_th 6,9 kN); engrane 0,78 |
| Pastillas | **105 × Ø140 (torneado Ø140,35) × 27,5 mm**, saliente **h_p = 2,5 mm**, patrón **radial** (anillos a paso 165), interferencia 0,35 mm, 0,40 kg c/u, 42 kg; cobertura 0,52 | **PV 0,93 (aviso)**; p + Δp 0,88; pared 0,76; p 0,66 |
| Tornillo de pastilla | **ISO 10642 M10 × 35 8.8** zinc laminar, taladro ciego 17 mm en la base (remanente 3), engrane 10,5 | corte como camino alternativo **0,90 (aviso)**; engrane 0,95 (geo) |
| Portador | **S355, t = 25 mm**, R137…R995, ligamento 25, solo **filetes perimetrales z8** exterior e interior, 283 kg | torsión en la sección neta 0,78 (r = 901, η = 0,158); filete interior 0,69 |
| Interfaz | δ = 25 + 2,5 + 8 = **35,5 mm** (opción B del núcleo: 55); eje del cilindro 140,5 (B: 160) | — |
| Masa | Interfaz 518 kg (B: 850 con topes); **total 3 689 kg** (B: 4 040) | — |

Estado global: **NO CUMPLE / PENDIENTE DE DECISIÓN** solo por la fila «pend» de la presión de las pastillas a 80 °C (FU 1,66 con k_p = 0,40,
supuesto C): el diseño cumple a 20 °C (estructura y giro), con dos avisos (PV 0,93 y el tornillo de la pastilla como camino alternativo 0,90).
En el escenario térmico (`BX.thermal`) a 80 °C gobierna PV (2,31) y fallan presión, sobrepresión y pared del UHMW; k_p crítico = 0,66.

Sensibilidades útiles para decidir:
- **PV**: proporcional al caudal; con Q_bomba ≤ 9,7 L/min el FU baja de 0,90 (con 10,8 L/min llega a 1,0).
- **Planitud**: la sobrepresión llega a FU 1,0 con d_flat ≈ 0,077 mm (por defecto 0,05): se mantiene el planeado de la base bajo el portador.
- **Material del disco**: con austenítico 304 (α 17,3) la dilatación diferencial exige **1 208 tornillos M10 a 50 mm y t = 12 mm**; con
  dúplex 2205 (α 13,0) bastan 140 a 200 mm y t = 8. Se adoptó dúplex (decisión a confirmar por el mandante).
- **Patrón**: el triangular sin soldaduras interiores da torsión 1,10/0,9 y pared 1,02/0,9; con agujeros de soldadura √7 la cobertura baja y
  no cumple PV ni pared. El radial alinea el anillo exterior con el borde y da la presión más pareja.

## 4. Fabricación: antes → después (tabla completa en `BX.design(P).fabricacion` y en el JSON, bloque `bx.fabricacion`)

| Pieza | Antes | Después | Estado |
|---|---|---|---|
| Discos inox (2 × 24 sectores) | plasma/láser de 48 sectores, muescas, chaflanes, rectificado/lapeado Ra 0,4 | 1 disco en 2 semidiscos a plasma + CJP esmerilada; cara 2B (o 1D pulida), sin rectificado; 140 avellanados taladrados | simplificada |
| Lámina UHMW (24 sectores) | CNC/agua con rebajes | 105 pastillas torneadas de barra | simplificada |
| Portador | — | plancha 25 mm a plasma HD, 2 filetes perimetrales | nueva |
| Barras de tope y muescas | barras soldadas antes del rectificado | — | eliminada |
| Tornillos de posición de sectores | 72 | tornillos que trabajan (140 del disco, 105 de pastillas) por plantilla | simplificada |
| Ranuras de engrase y graseras | fresadas (opción A) | — | eliminada |
| Collar del pivote | Ø exterior torneado, caras planeadas, H7 | Ø exterior y caras de corte; solo el H7 en línea (calado p6) | simplificada |
| Rebaje del collar en la mesa | mandrinado | agujero de la plancha inferior a plasma; quedan 11 mm de rebaje en el cubo (o bajar h_collar a 50: pendiente) | simplificada |
| Cara de apoyo de la base y cara inferior de la mesa | planeadas | se mantienen (d_flat de las pastillas) | se mantiene |
| Placas-guía (42CrMo4, Hertz, ± 0,2), pasadores de posición H7 | — | sin cambio | se mantiene |
| Bloque-uña con garra (asiento fresado, horquilla H9) | — | sin cambio | se mantiene |
| Pasadores E, Q, de empuje y pivote; agujeros H7 de pasadores; tapas del soporte E (H9) | — | sin cambio (ajustes indispensables) | se mantiene |
| Orejas de izaje (agujero H12) | — | sin cambio (BTH-1, sin verificación de agujero a plasma) | se mantiene |
| Mesa, base, soporte E, refuerzos, marco | plancha + soldadura | sin cambio | se mantiene |

## 5. Verificación independiente y pruebas

- `AGBX.crossCheck`: equilibrio Σq·dA = N_D (0,002 %), momento de la celda por diferencias finitas, Σ V_T·r = T_calado, fuerza térmica de
  borde por cadena discreta de 400 resortes, masa del portador por muestreo de 2 mm (−0,004 %).
- `tests/test_tt300bx.js` (13 pruebas, ≈ 65 s): bit-identidad del núcleo, golden, gancho y masas, dimensiones y veredicto, celda frente a
  diferencias finitas, Huth/cadena, equilibrio y PV, patrón y regla de un salto, ajuste, tornillos (dúplex frente a austenítico),
  fabricación, agentes, FEA y térmica.

## 6. Pendientes y decisiones

1. Dato del proveedor de UHMW a 80 °C (k_p y PV) o limitar la operación a T con k_p ≥ 0,66; el PV a 20 °C queda en 0,93.
2. Confirmar el material dúplex 2205 (o aceptar ≈ 1 200 tornillos con austenítico) y la disponibilidad de plancha de 8 mm con acabado 2B.
3. Criterio de taller: ligamento ≥ espesor para plasma HD y tolerancia ± 0,3 mm del Ø; con broca anular el ligamento podría bajar y con él PV.
4. El optimizador de masa del núcleo no conoce las filas BX (no se ofrece en `agentes_bx.js`).
5. No se reconstruyó `Tornamesa_v*.html` (instrucción del mandante: no tocar el HTML); el gancho del núcleo es inactivo sin BX.
6. Generador de planos (`cad/`): debe leer el bloque `bx` del JSON (no implementado aquí).
7. Plancha base sin anclaje: el pendiente del núcleo (soporte E) sigue igual en BX.
