# Placa-guía curva del accionamiento pivotado tipo KIET (drive_mode = 2) — registro del cambio

Fecha: 09-11-2026. Capacidad nominal: 300 tf. Núcleo: `packages/core/tt300c.js` (`camPivRaw`, `GV`, `compute`, `pivotGeo`, `pivotAt`, `pivotFab`, `designDrive`, filas «Giro», «Placas-leva», «Articulaciones», «Fatiga»). Estado original: commit `b928552` (rama `claude/dreamy-allen-r5dzqu`); extracto de su geometría en `original_b928552.json`.

Figuras: `comparacion.svg/png` (original poligonal, curva y concepto KIET, con tabla) y `cinematica.svg/png` (trayectorias de Q en empuje y retorno, posiciones extremas, curva con radios, centros y tangencias, ángulo de presión y fuerzas). Se regeneran con `node tools/export_design.js > d.json && python3 tools/fig_guia_curva.py d.json`.

## 1. Configuración original reconstruida (b928552, valores por defecto)

| Elemento | Valor |
|---|---|
| Ojal E | (1.134; −1.134) mm, R_E = 1.604 mm a 315° (cilindro 2 a 135°) |
| Bloque-uña | L_qp = 432 mm, e_cr = 35 mm, cara 80 × 60 mm, libre en Q (Ø90) |
| Pasadores | 28 × Ø85 en R930, paso 12,857°; toma en θ_ini = 348,39°, fin θ_fin = 361,25° |
| Carrera | L0 = 520, toma en L0 + s_libre = 541, L_fin = 740,4 → s_req = 220,4 + 5 ≤ 235 mm |
| Perfil (centro del seguidor, w lateral) | tramo a nivel c = 3 mm (L 520–522), rampa recta a 65° hasta w = 57,9 (L 547,6), bolsillo plano w = 57,9 hasta L 683,2, rampa a 65° de bajada, luego w_emp + 3 hasta L_fin |
| Canto exportado | trayectoria desplazada d_Q/2 = 45 mm **en w** (no en la normal); labio de 80 mm; 6 pernos M20 en el eje del labio, roscados en la base de 18 mm |
| Cargas | T = μ_s·F_n = 61,6 kN (calado), atasco F_ret/sen 65° = 71,6 kN → N = 71,6 kN |
| Material | S355J2 «con canto templado ≥ 55 HRC» |

## 2. Inconsistencias encontradas

| # | Inconsistencia | Cuantificación |
|---|---|---|
| I1 | Quiebres de tangente en el canto (pie de rampa, tope de rampa, salida del bolsillo, fin de bajada) | quiebre máximo 70,2°; 4 vértices; impacto del seguidor en cada vértice (velocidad lateral de 0 a 2,1·v instantánea) |
| I2 | Canto exportado = trayectoria desplazada en w, no la envolvente del círculo del seguidor | en las rampas de 65° la distancia normal entre canto y centro es 45·cos 65° = 19 mm < 45: **el contorno exportado invade el seguidor 27,1 mm** |
| I3 | Sincronía declarada (7,07 mm) calculada con Q en w_leva, que el contorno exportado no permite | con el seguidor tangente al contorno exportado, la holgura bloque–pasador B baja a **−21,0 mm en L = 562,5 (choque)** |
| I4 | Estabilidad del empuje no verificada: la rodilla E–Q–P es inestable en compresión (rigidez lateral −F·(1/L + 1/L_qp)) y el roce de la cara empuja el bloque hacia afuera | en el 76 % del empuje (fracción retenida 0,24) el canto está hasta 56 mm afuera; con Q apoyado en el canto declarado, H llega a 0,37·F_n (no 0,15) y en la rampa de bajada de 65° la fuerza del cilindro sube **34 %** |
| I5 | Ángulo de presión de la rampa constante 65° solo en el tramo recto; en los vértices la normal salta (no definido) | — |
| I6 | Pernos roscados en una base de 18 mm: M20 10.9 pide enganche ≥ 1,25·d = 25 mm; pasantes con tuerca no caben (la base apoya en la losa) | enganche 18 < 25 mm |
| I7 | S355J2 no admite temple superficial a 55 HRC (C ≈ 0,2 %): la fila de Hertz con Fy_sup = 1.500 MPa no corresponde al material | — |
| I8 | Esquinas cóncavas del bolsillo con radio 0 (concentración de tensiones, no fabricables) | — |
| I9 (fuera de alcance, informado) | Bloque-uña: con μ_s = 0,15 y la resultante pasando por Q, el contacto en la cara queda a μ_s·(L_qp − r) = 58 mm del eje del bloque y la cara mide ± 40 mm: el pasador apoya en la arista de la cara | contacto de arista; revisar ancho de cara (≥ 2·(58 + margen)) o cara cilíndrica. No se cambia en esta tarea (pieza del bloque) |

## 3. Solución

### 3.1 Cinemática

| Fase | Modelo |
|---|---|
| Aproximación (L0 → toma) | Q en el nivel de toma w = c, sin carga, hasta que la cara toca el pasador A (θ_ini) |
| Apertura de la rodilla (θ_ini) | con la mesa quieta, la rodilla se abre hacia afuera (|Q − E| = L, |P − Q| = L_qp) hasta que Q apoya en el canto (L 541 → 545,2) |
| Empuje guiado | para cada θ, Q en la trayectoria con |P(θ) − Q| = L_qp; equilibrio del pasador Q: F·u_c + H·(n − μ_leva·t) = F_n·b', b' = Q→P girada asin(r·sen(atan μ_s)/L_qp) = 0,84° (círculo de rozamiento); par T/n = F_n·(Q × b') |
| Retorno (mesa en θ_fin) | Q sale del canto en L_fin y conserva ψ salvo que el pasador lo empuje hacia afuera (holgura 0); desde el primer contacto (L₁ = 546,5 mm, φ₁ = 40,3°) el canto lo conduce por el flanco a la toma w = c en L0 |
| Liberación y reenganche | la cara queda detrás de B con holgura ≥ m + δ en toda la conducción; en L0 Q está en w = c |
| Carga transversal al vástago | el cilindro es biarticulado (miembro de dos fuerzas): la reacción de la placa entra al pasador Q y al bloque, no al vástago; al vástago solo llegan el roce de los ojales (V = μ·F·(d_E + d_Q)/(2L) = 9,4 kN a calado, M = μ·F·d_Q/2 = 4,0 kN·m) y el peso (0,27 kN por apoyo) |

Tabla por θ (caso de diseño, cilindro 1 antihorario):

| θ (°) | L (mm) | Q (mm) | w (mm) | sep. colineal (mm) | φ empuje (°) | holgura bloque–pasadores (mm) | F cil. (kN) | F colineal (kN) | F_n (kN) | H guía (kN) | p (bar) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 348,39 | 545,2 | (1053,3; −595,0) | 45,0 | 45,0 | 43,8 | 64,3 | 271 | 308 | 302 | 70,3 | 426 |
| 349,68 | 565,2 | (1058,4; −574,1) | 54,8 | 50,0 | 0,1 | 63,2 | 321 | 304 | 299 | 64,8 | 504 |
| 350,96 | 583,5 | (1054,4; −556,1) | 55,0 | 45,5 | 1,6 | 61,1 | 315 | 300 | 292 | 57,6 | 495 |
| 352,25 | 602,7 | (1052,7; −537,0) | 57,8 | 43,6 | 7,2 | 59,6 | 300 | 296 | 287 | 52,6 | 472 |
| 353,53 | 622,2 | (1051,7; −517,4) | 61,3 | 42,7 | 0,3 | 58,4 | 303 | 293 | 282 | 51,1 | 477 |
| 354,82 | 641,5 | (1047,4; −498,6) | 61,4 | 38,4 | 10,6 | 54,9 | 308 | 291 | 278 | 47,6 | 483 |
| 356,10 | 660,5 | (1039,4; −480,5) | 57,8 | 30,6 | 20,8 | 46,5 | 308 | 289 | 273 | 41,5 | 485 |
| 357,39 | 679,7 | (1027,8; −462,9) | 50,4 | 19,4 | 23,9 | 36,3 | 299 | 287 | 268 | 28,2 | 469 |
| 358,68 | 699,5 | (1017,9; −444,4) | 45,1 | 10,2 | 13,7 | 27,1 | 285 | 285 | 265 | 15,1 | 448 |
| 359,96 | 719,9 | (1011,3; −424,9) | 43,1 | 4,8 | 4,0 | 19,5 | 278 | 283 | 262 | 8,6 | 438 |
| 361,25 | 740,4 | (1008,1; −404,6) | 44,6 | 3,0 | 5,4 | 13,6 | 275 | 282 | 261 | 6,6 | 433 |

### 3.2 Curva

Trayectoria W(L) del centro del seguidor (extremo inferior del pasador Q, r_f = 45 mm) con los requisitos:

1. retorno: W ≥ w_nec(L; m + δ), m = 5 mm, δ = 0,40 (tolerancia de posición: corte CNC ± 0,2 + pasadores de posición ± 0,2) + α·ΔT·R_pin = 12,4×10⁻⁶·60·930 = 0,69 mm → m + δ = 6,09 mm;
2. empuje: W ≥ w_emp + c (Q apoyado, h > 0);
3. reenganche: W(L0 + tramo) = c = 3 mm.

Construcción (cilindro 1, antihorario; los otros tres por rotación de 180° y reflexión respecto de la diagonal O–E): flanco recto por (L0, c) con el ángulo mínimo que deja W ≥ w_nec (61,50°, límite α_máx = 65°), dos biarcos de brazos iguales (hombro–cresta y bajada–empalme) cuyos nodos se eligen por búsqueda en malla con W ≥ requisito, y salida tangente. El tope del flanco se elige para hacer mínima la mayor carga de la placa (empuje a calado o atasco del retorno). El canto es el desplazamiento exacto a d_Q/2 hacia la placa: los arcos del canto son concéntricos con los de la trayectoria (convexo R_c = R − 45, cóncavo R_c = R + 45), de modo que es G1 por construcción y es la envolvente exacta del seguidor. Tolerancia de la polilínea de exportación: flecha ≤ 0,1 mm; DXF con ARC exactos desde `segmentos_canto`.

Segmentos del canto (sistema de la tornamesa, cilindro 1, giro antihorario; mm):

| # | Rol | Tipo | Curvatura (vista del seguidor) | R trayectoria | R canto | Centro | Inicio (tangencia) | Fin (tangencia) |
|---|---|---|---|---|---|---|---|---|
| 1 | flanco de reenganche (con entrada tangente) | recta 61,5° | — | — | — | — | (1040,2; −667,6) | (1078,5; −633,8) |
| 2 | hombro | arco antihorario | cóncava | 29,3 | 74,3 | (1029,4; −578,1) | (1078,5; −633,8) | (1100,8; −557,6) |
| 3 | cresta | arco horario | convexa | 123,8 | 78,8 | (1176,6; −535,9) | (1100,8; −557,6) | (1097,7; −534,5) |
| 4 | bajada | arco antihorario | cóncava | 105,9 | 150,9 | (946,8; −532,0) | (1097,7; −534,5) | (1068,3; −442,4) |
| 5 | empalme de empuje | arco horario | convexa | 124,9 | 79,9 | (1132,5; −395,0) | (1068,3; −442,4) | (1052,9; −401,2) |
| 6 | salida tangente | recta (65 mm) | — | — | — | — | (1052,9; −401,2) | (1047,9; −336,4) |
| 7 | cierre del bolsillo (sin contacto) | arco antihorario | cóncava | — | 60,0 | (988,1; −341,0) | (1047,9; −336,4) | (1023,8; −292,7) |

Saltos de curvatura en los empalmes ≤ 0,026 1/mm; quiebre de tangente 7×10⁻¹³°.

### 3.3 Placas

| Dato | Valor |
|---|---|
| Configuración | placa rectangular empernada a la base junto a la cabeza del vástago, con recorte en media luna abierto hacia la mesa (concepto KIET); 4 placas: 2 por cilindro (una por sentido, simétricas respecto de la diagonal) |
| Marco | 471 × 147 × 30 mm, eje x' a lo largo de la cuerda del canto (dirección (−0,044; 0,999) en el cilindro 1 antihorario), origen en Q(L0, c) = (1017,8; −627,4) |
| Esquinas (cilindro 1, antihorario) | (1021,7; −244,8), (1168,9; −238,3), (1189,5; −709,1), (1042,3; −715,6); el lado interior queda a R ≥ 1.050,6 mm (mesa R 1.000 + 10) |
| Posición | centro de la placa a 335,9° (20,9° de la diagonal del ojal), R 1.179 mm |
| Espesor | 30 mm; z de 18 a 48 mm; el bloque (z ≥ 53) y el cuerpo del cilindro (z ≥ 58) pasan sobre ella |
| Material | 42CrMo4+QT (EN 10083-3; Re ≥ 750, Rm ≥ 1.000, se toma Fu = 900 MPa) |
| Tratamiento del canto | temple por inducción 52–56 HRC, capa efectiva ≥ 4 mm (EN 10328, 550 HV), revenido 180 °C; Ra ≤ 1,6 µm; chaflanes 1 × 45° |
| Corte | láser/agua con 1 mm de sobreespesor y fresado CNC final por arcos; tolerancia de perfil ± 0,2 mm (ISO 1101) |
| Fijación | 8 tornillos ISO 10642 M16 × 46 8.8 avellanados a ras, roscados en la base (enganche 18 ≥ 1,0·d); 4 en las esquinas, 4 en la fila exterior. 2 pasadores de posición ISO 8734 Ø16 m6 en H7 escariado (placa y base), montados con plantilla al círculo de pasadores |
| Tornillos (cilindro 1, antihorario) | (1164,5; −686,2), (1160,8; −601,6), (1157,1; −517,1), (1153,4; −432,5), (1149,7; −347,9), (1146,0; −263,3), (1065,3; −690,6), (1046,7; −267,7) |
| Pasadores de posición | (1114,9; −688,4), (1096,3; −265,5) |
| Masa | 12,7 kg por placa; 51,0 kg las 4 (antes 34,4 kg) |
| Otras instancias | cilindro 2: rotación de 180°; giro horario: reflexión respecto de la diagonal O–E (`pivotGeo().placas[k].segmentos_*`, `designDrive().pivotado.fabricacion.placas_leva.instancias`) |

### 3.4 Verificaciones (valores por defecto)

| Grupo | Verificación | dem | cap | FU | Norma |
|---|---|---|---|---|---|
| A | Hertz, empuje a calado, R_c = +78,8 (convexo) | 1.954 MPa | 2.505 MPa | 0,78 | Hertz lineal; p₀ ≤ 1,67·Fy_sup (Tresca) |
| A | Hertz, atasco del retorno, R_c = −74,3 (cóncavo) | 1.048 MPa | 2.505 MPa | 0,42 | Hertz lineal |
| A | Capa templada ≥ 2·0,786·b | 3,42 mm | 4,0 mm | 0,86 | Hertz; EN 10328 |
| A | Flexión del ligamento (113 mm) | 39,3 MPa | 250 MPa | 0,16 | ASME BTH-1 §3-2.3 (Nd 3,0, Cat. B) |
| A | Corte del ligamento | 23,9 MPa | 144 MPa | 0,17 | ASME BTH-1 §3-2.2 |
| A | K_t·σ_nom sin fluencia local (K_t = 2,8) | 109 MPa | 750 MPa | 0,15 | Pilkey (Peterson) Ec. 4.3 |
| A | Deformación del ligamento | 0,014 mm | 0,1 mm | 0,14 | Timoshenko |
| A | Fatiga, recorte R ≥ 25 (cat. C, 35.000 ciclos) | 23,9 MPa | 345 MPa | 0,07 | AISC 360-22 Ap. 3 |
| A | Fatiga, sección neta en agujeros (cat. D) | 11,1 MPa | 274 MPa | 0,04 | AISC 360-22 Ap. 3 |
| B | Tornillos: corte del grupo elástico | 158 MPa | 180 MPa | 0,88 | AISC 360-22 §J3.6; Manual Parte 7 |
| B | Aplastamiento en la placa (t_e = t − k/2) | 31,8 kN | 214 kN | 0,15 | AISC §J3.10; EN 1993-1-8 T. 3.4 |
| B | Tracción por vuelco + corte | 47,4 MPa | 127 MPa | 0,37 | AISC §J3.7 |
| B | Enganche de rosca en la base | 16 mm | 18 mm | 0,89 | VDI 2230-1 (orientativo) |
| B | Distancia al borde | 22 mm | 24 mm | 0,92 | AISC §J3.4 (T. J3.4M) |
| B | Separación | 48 mm | 84,7 mm | 0,57 | AISC §J3.3 |
| C | FS del accionamiento (caso de diseño) | 1,25 | 1,362 | 0,92 | Criterio del proyecto |
| C | Presión de diseño frente a la alarma | 514 bar | 600 bar | 0,86 | Criterio de operación |
| C | Carrera requerida con margen | 225,4 mm | 235 mm | 0,96 | Cinemática |
| C | Vástago: flexocompresión a calado (Fy 520 hipótesis) | 0,965 | 1 | 0,97 | AISC §H1.1, §E3, Ap. 8 |
| C | Pandeo del vástago (sin cambio) | 445 kN | 893 kN | 0,50 | Euler, FS 3 |
| C | Pasador Q: flexión con la reacción de la placa (N = 115 kN) | 130 MPa | 217 MPa | 0,60 | ASME BTH-1 §3-3.3 |
| D | Aplastamiento de los tornillos en la base (t = 18, Fu 450) | 31,8 kN | 156 kN | 0,20 | AISC §J3.10 |
| Geo | Sincronía nominal / peor caso | 6,09 / 5,00 mm | 6,26 / 5,17 mm | 0,97 / 0,97 | Geometría |
| Geo | Ángulo del flanco ≤ α_máx | 61,5° | 65° | 0,95 | — |
| Geo | Sin autobloqueo en toda la conducción (peor punto φ = 61,5°) | 0,013 | 0,301 | 0,04 | Equilibrio con fricción |
| Geo | Empuje: φ máx ≤ 90° − atan μ | 43,8° | 78,7° | 0,56 | Equilibrio del pasador Q |
| Geo | Empuje: H/F ≥ 0,005 | 0,005 | 0,025 | 0,20 | — |
| Geo | Radio convexo sin socavado | 10 mm | 78,8 mm | 0,13 | — |
| Geo | Bloque–pasadores en el empuje guiado | 10 mm | 13,6 mm | 0,74 | — |
| Geo | Placa dentro de la base / fuera de la mesa / del cajón E / diagonal | — | 1.189,5 ≤ 1.265; 1.050,6 ≥ 1.010; 288,6 ≥ 5; 231 ≥ 5 | ≤ 0,96 | — |
| Geo | Cuerpo del cilindro sobre la placa | 53 mm | 58 mm | 0,91 | — |

Cargas de la placa: N_atasco = F_ret/sen φ₁ = 64,9/sen 40,3° = 100,4 kN; H a calado = 0,273·F_calado·η = 115,4 kN (gobierna); H de diseño = 70,3 kN.

## 4. Antes y después

| Valor | Original (b928552) | Curva |
|---|---|---|
| Perfil | poligonal (4 vértices, quiebre 70°) | recta + 4 arcos + recta, G1 |
| Ángulo de presión en el reenganche | 65° (vértices sin definir) | 61,5° (máximo, en el pie del flanco) |
| Canto exportado | desplazamiento en w (invade 27 mm) | envolvente exacta |
| Sincronía nominal (declarada) | 7,07 mm | 6,26 mm (margen 6,09 con tolerancias) |
| Sincronía con el contorno fabricado | −21,0 mm | 6,26 mm (peor caso 5,17) |
| Bolsillo (máx W) | 57,9 mm | 61,8 mm |
| Carga de diseño de la placa | 71,6 kN (atasco) | 115,4 kN (empuje a calado) |
| F cilindro, caso de diseño | 308,1 kN | 326,9 kN (+6,1 %; colineal 308,1 como referencia) |
| Presión de diseño | 484 bar | 514 bar |
| FS diseño / contaminado / borde | 1,446 / 1,157 / 1,157 | 1,362 / 1,090 / 1,091 |
| Carrera requerida | 220,41 mm | 220,43 mm |
| Placa | labio de 80 mm, 6 pernos M20 | rectángulo 471 × 147, 8 ISO 10642 M16 8.8 + 2 pasadores |
| Material | S355J2 | 42CrMo4+QT, canto templado por inducción |
| Masa de las 4 placas / total | 34,4 / 2.770,8 kg | 51,0 / 2.787,5 kg |
| Pasador Q (FU flexión) | 0,551 | 0,602 |

Parámetros nuevos o con valor por defecto cambiado (tests/golden/params_defaults.json): `pv_dwell` 2 → 0, `Fy_camP` 355 → 750, `Fu_camP` 470 → 900, `pv_nb` 6 → 8, `pv_db` 20 → 16; nuevos `pv_rmin` 10, `pv_tolg` 0,4, `pv_Fub` 800, `pv_dd` 16, `pv_Fyrod` 520. `pv_alpha` pasa a ser el ángulo máximo admisible del flanco.

## 5. Concepto KIET (medido en plano de referencia KIET, no acotado)

| Aspecto | KIET (plano KIET-1024-REF-TT-400T) | TT300-C (este diseño) |
|---|---|---|
| Disposición | 2 cilindros en esquinas opuestas (ojal a 134,9° y 315,1°); 2 placas por cilindro, una por sentido | igual (ojales a 135° y 315°) |
| Posición angular de las placas respecto de la diagonal del ojal | −26,0° y +25,1° (cilindro 1); +26,3° y −26,1° (cilindro 2) | ± 20,9° |
| Radio del centro de la placa / radio del anillo | 1,02–1,08 | 1,18 (sobre R = D/2 = 1.000) |
| Placa | rectangular, ~6 pernos en el perímetro | rectangular, 8 tornillos + 2 pasadores de posición |
| Perfil | media luna con arco continuo y gancho en un extremo (en el extremo de carrera extendida) | media luna: flanco recto de reenganche en el extremo retraído (el «gancho» que vuelve el seguidor a la toma), cresta curva y empalme tangente en el extremo extendido |

Recortes y medición: `pdftoppm -r 400 -png KIET-1024-REF-TT-400T.pdf k && python3 -I tools/kiet_recortes.py k-1.png docs/qa/guia_curva_KIET` (centro y radio del anillo Ø2000 y centros de placas y ojales tomados sobre la imagen; resultado solo como proporción relativa).

La posición del flanco empinado difiere de la del gancho de KIET porque la sincronía con el pasador B (s_libre 21 mm, margen 5 + 1,09 mm) lo exige en el extremo retraído; la geometría del bloque-uña KIET (chaflán, giro libre) no está documentada y no se supuso. Recortes del plano en `kiet_planta_recorte.png`, `kiet_detalle_placa_cilindro1.png` y `kiet_detalle_placa_cilindro1_otro_sentido.png`.

## 6. Datos faltantes e hipótesis

| Dato | Estado | Hipótesis usada | Efecto |
|---|---|---|---|
| Fy del vástago, tipo de ojal (rótula o casquillo) y μ de los ojales (proveedor del cilindro) | FALTA | Fy = 520 MPa (acero templado y cromado), μ = 0,20 (pv_muE), K = 1 con L = L0 + carrera | flexocompresión a calado FU 0,965: confirmar; con rótula autolubricada μ ≈ 0,1 el FU baja a ≈ 0,8 |
| Diámetro del vástago y longitud real entre ojales | parámetros del proyecto (d_rod 63, L0 520) a confirmar con la ficha | — | pandeo y flexocompresión |
| Geometría de la cara del bloque-uña frente al roce (ancho para el desplazamiento μ_s·s₂ = 58 mm) | FUERA DE ALCANCE | se mantiene la cara de 80 mm y el modelo de bloque alineado con Q–P | ver I9 |
| Forma de la zapata para familias 2–4 sobre el canto curvo | PENDIENTE (fila «pend») | p = H/(l·t) con apoyo completo | flecha l²/(8R) = 13 mm con R = 74 mm: la zapata plana no apoya |
| Bloque alineado con el vástago en el retorno | hipótesis del modelo original (conservadora) | — | w_nec |
| Profundidad de temple real y dureza del canto | especificación (≥ 4 mm, 52–56 HRC) | Fy_sup = 1.500 MPa | Hertz |
| Rugosidad y grasa del contacto | μ_leva = μ_d = 0,20 (familia 1) | — | fuerza del cilindro, autobloqueo |
| Dilatación | mesa a 80 °C y base a 20 °C (crecimiento del círculo de pasadores 0,69 mm) | α medio EN 1993-1-2 | margen de sincronía |
| Dimensiones de KIET | NO se trasladan | solo concepto | — |

## 7. Pruebas y verificación independiente

| Prueba | Antes del cambio | Después |
|---|---|---|
| `Placa-guía curva · canto y trayectoria del seguidor: G1 en las 4 placas` | falla (no hay segmentos) | pasa |
| `Placa-guía curva · radio mínimo sin socavado, no autobloqueo en toda la curva y empuje estable` | falla | pasa |
| `Placa-guía curva · sincronía (con tolerancias y dilatación) y sin interferencias en todo el recorrido` | falla | pasa |
| `Placa-guía curva · API: segmentos en designDrive y contacto de la simulación sobre el canto` | falla | pasa |
| `Pivotado · cinemática`, `Simulación · modo pivotado`, familias | ajustadas al empuje guiado (equilibrio del pasador Q verificado punto a punto) | pasan |
| `tests/indep_pivotado.py` | — | replica requisitos (w_nec con m + δ, ángulo del flanco), G1, radios, empuje guiado (fuerzas de los 5 casos, carrera, L, brazo, ψ), retorno (primer contacto, atasco, autobloqueo, sincronía), tornillos (grupo elástico), Hertz con radio real y vástago, sin leer el JS |
| Revisor cruzado (`agentes.js`) | — | fuerza del empuje guiado por potencia virtual (diferencias finitas de L, deslizamiento y roce del canto) frente al equilibrio: Δ 0,06 % |

## 8. Diferencias de los archivos golden

`tests/golden/tt300c_pivotado.json` y `tt300c_defaults.json` (mismo caso, drive_mode = 2 por defecto):

| Clave | Antes | Después | Justificación |
|---|---|---|---|
| casos.dis F / p / FS | 308,05 kN / 484,2 bar / 1,4456 | 326,86 / 513,8 / 1,3624 | empuje guiado (Q apoyado en el canto: rodilla inestable) |
| casos nom, borde, cont, seco | F × 1,061 | | ídem (todos escalan con el mismo máximo) |
| sincronia | 7,07 | 6,26 | flanco tangente a w_nec(m + δ); la anterior no era alcanzable con el contorno exportado (−21 mm) |
| bolsillo | 57,88 | 61,80 | máximo de W(L) con los biarcos |
| masas.cam / masa_total | 34,35 / 2.770,82 | 50,99 / 2.787,45 | placas rectangulares de 42CrMo4 (12,7 kg cada una) |
| fea.lift, fea.liftW y filas de izaje | +0,5 % | | masa total mayor |
| FU «FS del accionamiento», «Gira con grasa contaminada», «borde», «Presión de diseño» | 0,865 / 0,865 / 0,864 / 0,807 | 0,918 / 0,918 / 0,917 / 0,856 | fuerza del empuje guiado |
| FU fatiga del bloque, pasadores y soldadura del cajón | +6,1 % | | F de operación del empuje guiado |
| FU «Pasador Q: flexión» | 0,551 | 0,602 | reacción de la placa 115 kN (antes 71,6) |
| filas de la placa | eliminadas: «Rampa …», «Placa-leva: …», «Pernos de la placa-leva …»; nuevas: «Placa-guía …», «Tornillos de la placa-guía …», «Canto …», «Empuje con Q apoyado …», «Vástago: flexocompresión …», fatiga de la placa | | rediseño |

`tests/golden/tt300c_termica_alcance2.json`: las mismas causas en el escenario térmico del modo 2. `tests/golden/params_defaults.json`: parámetros de la sección 4. `tests/golden/tt300c_guiado.json` sin cambios (el modo guiado no se tocó).
