# TT300-B, tornamesa hidráulica 300 tf: verificación independiente de la herramienta paramétrica

**Alcance:** `app/calc.js` (compute, verifs, discModel/runDisc, runPawl), `app/fea.js` (Cholesky en banda, MITC4, Q4), contraste con `calc.py`.
**Método:** re-cálculo propio en Python (`indep.py`), estudio de malla y benchmarks adicionales en JS sobre copias parametrizadas (`calc_mod.js`, `fea_mod.js`, `refine.js`, `signed.js`, `bench.js`, `pawl.js`). Todos los scripts están en `/tmp/claude-0/-home-claude/f880023e-4047-5d94-81d4-3b8b32341d04/scratchpad/`. No se modificó ningún archivo bajo `/home/claude/tt300`.

---

## 0. Resumen

- **Aritmética:** todos los valores de la corrida por defecto coinciden con mi re-cálculo. La diferencia es menor que 0,01 % en todos los casos. No hay errores de unidades.
- **Hallazgos principales.** Son de modelo e hipótesis, no de aritmética:
  - **Crítico 1.** La barra 4f y su soldadura se modelan con una luz de 100 mm, como si los apoyos estuvieran en las caras interiores. Si la soldadura de bisel está en las caras exteriores, la luz real es 160 mm. Con la holgura de 0,5 mm del agujero, la barra no apoya en el agujero en régimen elástico. En ese caso:
    - soldadura: FU = 1,31 (la herramienta da 0,83);
    - flexión de la barra rotulada: FU = 1,15 (la herramienta da 0,52).
  - **Crítico 2.** Hay incompatibilidad cinemática entre el asiento del trinquete y la trayectoria circular de la barra. El desplazamiento radial relativo es 3,58 mm y la holgura del asiento es 1,0 mm. La herramienta no lo verifica.
  - **Crítico 3.** La carrera requerida es 199,85 mm y la disponible 200 mm. El margen es 0,15 mm.
- **Hallazgos mayores:**
  - El r_eff = 0,80 m no está justificado. En la cota r = 1,0 m:
    - con μ = 0,20: FS = 1,13 y p = 619 bar, sobre la alarma;
    - con μ = 0,25: FS = 0,91, es decir, el disco no gira.
  - La fórmula de flexión global del cajón subestima unas 2,7 veces: 8,6 MPa contra 23 MPa axisimétrico.
  - Faltan verificaciones: corte en nervios, soldaduras de almas, anclaje de la guía y su volcamiento, apoyo trinquete/carro (reacción ≈ 1,8 F en el labio), fatiga, cargas laterales y sísmicas.
  - La presión sobre el suelo sale 9 % más alta con excentricidad biaxial (FU 0,99).
- **FEA:** la formulación MITC4 es correcta y está en equilibrio. Las tensiones de placa convergen alrededor de 12 % por sobre el valor por defecto: unos 28–29 MPa contra 25,6 MPa. El margen sigue siendo amplio. Las fuerzas en barras se calculan con la suma de |R|: dependen de la malla y sobrestiman 15 %.

---

## 1. Re-derivación de la corrida por defecto

| Magnitud | Herramienta | Revisor | Δ % |
|---|---|---|---|
| Masa disco (top/bot/hub/almas/nervios/barras/buje) [kg] | 689,63/689,63/50,58/195,44/123,40/174,01/8,1 | 689,6/689,6/50,6/195,4/123,4/174,0/8,1 | 0,00 |
| Masa total [kg] | 1930,80 | 1930,8 | 0,00 |
| W [kN] | 2941,995 | 2941,995 | 0,00 |
| N = W + W_d [kN] | 2960,930 | 2960,930 | 0,00 |
| N_D = φd·W + W_d [kN] | 3255,129 | 3255,129 | 0,00 |
| r_u (presión uniforme) [m] | 0,67216 | 0,67216 | 0,00 |
| a = 940·cos5° [mm] | 936,423 | 936,423 | 0,00 |
| Δ = 1085 − a [mm] | 148,577 | 148,577 | 0,00 |
| K_guía / K | 1,17829 / 1,24031 | 1,17829 / 1,24031 | 0,00 |
| A émbolo [mm²] / F_max 700 bar [kN] | 6361,73 / 445,321 | 6361,73 / 445,321 | 0,00 |
| F_alarma 600 bar [kN] | 381,704 | 381,704 | 0,00 |
| T_piv [kN·m] | 2,2065 | 2,2065 | 0,00 |
| Nominal μ 0,15, r_u: T / F_b / F_c / p / FS | 300,74 / 160,58 / 199,17 / 313,1 / 2,236 | ídem | 0,00 |
| Diseño μ 0,20, r 0,80 | 475,96 / 254,13 / 315,21 / 495,5 / 1,413 | ídem | 0,00 |
| Contaminado μ 0,25, r 0,80 | 594,39 / 317,37 / 393,64 / 618,8 / 1,131 | ídem | 0,00 |
| Seco μ 0,50, r_u | 997,32 / 532,52 / 660,48 / 1038,2 / 0,674 | ídem | 0,00 |
| μ_max a 700 bar (r_u / 0,80 / 0,94) | 0,3368 / 0,2829 / 0,2408 | 0,3368 / 0,2829 / 0,2408 | 0,00 |
| μ_max a 600 bar, r 0,80 | 0,2424 | 0,2424 | 0,00 |
| Carrera requerida [mm] | 199,853 | 199,853 | 0,00 |
| Y_brk [mm] | 817,93 | 817,93 (plano: 818) | 0,01 |
| Desglose F_c (interfaz/pivote/guía/sellos) [kN] | 252,96 / 1,18 / 45,31 / 15,76 | 252,96 / 1,18 / 45,31 / 15,76 (Σ 315,21) | 0,00 |
| Curva de carrera F_c (s = 36 / centro) [kN] | 315,21 / 312,86 | 315,21 / 312,86 | 0,00 |
| q_avg / q_max contacto [MPa] | 1,0456 / 1,6673 | 1,0456 / 1,6673 | 0,00 |
| q_top (φd·W / Ø1600) [MPa] | 1,6096 | 1,6096 | 0,00 |
| σ suelo medio / máx. [MPa] | 0,6231 / 0,9035 | 0,6231 / 0,9035 (biaxial: **0,9881**) | 0,00 (+9,4 %) |

**Verificaciones de elementos (verifs).** Todas reproducidas exactamente:

| Elemento | Valor | Capacidad | FU |
|---|---|---|---|
| Barra 4f, flexión | M_ss 6,123 kN·m | 11,81 | 0,52 |
| Barra 4f, corte | τ 77,14 MPa | 138 | 0,56 |
| Barra 4f, soldadura | τ_V 84,37, τ_M 87,99, resultante 121,9 MPa | 147 | 0,83 |
| Barra 4f, aplastamiento | 106,0 MPa | 310,5 | 0,34 |
| Trinquete (vigas) | 343,4 MPa | 400 | 0,86 |
| Guía, aplastamiento | R_g 264,66 kN, σ 176,4 MPa | 310,5 | 0,57 |
| Guía, flexión | M 3,97 kN·m | 12,40 | 0,32 |
| Mejilla | 34,08 MPa | 207 | 0,16 |
| Pasador, flexión | M 9,463 kN·m, σ 281,0 MPa | 325 | 0,86 |
| Pasador, corte | 57,86 MPa | 187,6 | 0,31 |
| Buje | 10,79 MPa | 30 | 0,36 |
| Pivote | 24,42 MPa | 325 | 0,08 |
| Vástago, P_cr/3 | 445,3 kN | 1204,2 kN | 0,37 |
| Flexión global del cajón | 8,55 MPa | 207 | 0,04 |

**Contraste con `calc.py` (versión previa):**
- calc.py usa A = 445e3/70 = 6357 mm² y la herramienta 6361,7 mm². La diferencia en F_max es −0,07 %.
- calc.py usa W_d = 1922 kg y la herramienta 1930,8 kg. La diferencia es −0,46 %, despreciable en N.
- En pandeo, calc.py usa Ø90 (el émbolo) y obtiene P_cr/3 = 5016 kN. calc.js usa el vástago Ø63 y obtiene 1204 kN, que es lo correcto. calc.py estaba errado del lado inseguro.
- calc.py fija para las planchas 67 y 70 MPa. Ese valor corresponde a una franja simplemente apoyada (q·b²/8). El FEA da 25–29 MPa. La diferencia es de concepto, no un error.

---

## 2. Hallazgos clasificados

### CRÍTICO

**C1. Barra 4f: luz y apoyos del modelo de flexión y soldadura** (`calc.js › verifs`, bloque "barra 4f")
- **Problema:** se usa L = gap = 100 mm, con rótulas o empotramientos en las caras interiores de las planchas. La barra pasa por agujeros Ø71, con 0,5 mm de holgura radial, y se suelda con bisel 15 mm. Si ese bisel está en las caras exteriores, que es lo habitual en barras pasantes:
  - el apoyo real está en la cara exterior, y la luz es TD = 160 mm;
  - la deflexión elástica de la barra en la cara interior es de unos 0,05–0,1 mm, menos que la holgura de 0,5 mm, así que el agujero no apoya;
  - con c = 90 mm, la luz de corte supuesta es de solo 5 mm por lado. La herramienta trata un pasador corto como si fuera una viga.
- **Efecto:** FU con F = 445 kN y la capacidad corregida según m1:

| Hipótesis de luz | Flexión rotulada (M_ss) | Soldadura empotrada (τ resultante) |
|---|---|---|
| L = 100 (herramienta) | 6,12 kN·m → FU 0,55 | 121,9 MPa → FU 0,83 |
| L = 130 (planos medios) | 9,46 kN·m → FU 0,85 | 156,4 MPa → **FU 1,06** |
| L = 160 (caras exteriores) | 12,80 kN·m → **FU 1,15** | 192,0 MPa → **FU 1,31** |

- Un mecanismo plástico (rótulas en extremos y centro) daría FU ≈ 0,77. Ese argumento depende de la ductilidad de una soldadura PJP, que AISC no reconoce para redistribución.
- **Corrección:**
  - Confirmar en planos dónde está la soldadura.
  - Si está en las caras exteriores, hay tres opciones:
    - soldar también las caras interiores (antes de cerrar el cajón);
    - especificar un ajuste escariado (holgura ≤ 0,1 mm) y documentar el apoyo en el agujero;
    - aumentar la garganta (CJP o bisel mayor).
  - Parametrizar la luz del modelo como L = gap + 2·t_eff, según la ubicación real del apoyo.

**C2. Compatibilidad cinemática asiento–barra no verificada** (`calc.js › compute` y `runPawl`)
- **Problema:** el carro se mueve en línea recta (Y) y la barra describe un arco. La posición x de la barra varía entre R·cos5° = 936,42 mm y 940 mm: el desplazamiento radial relativo es R(1 − cos π/N) = 3,58 mm. El asiento es R36 y la barra r35, con su centro en x = a (`Xs = R.a − pawl_tip`). La holgura radial es de 1,0 mm, así que queda una interferencia de unos 2,6 mm a media carrera.
- **Efecto:**
  - Si el trinquete no tiene libertad radial, hay trabado o contacto de borde.
  - La fuerza de contacto aparece con una componente F_x que no está modelada. Esa componente carga la guía, el carro y el pivote.
  - Cambian la flexión y la presión de contacto del trinquete: el contacto Hertz centrado da p₀ = 371 MPa, pero el contacto de borde es muy superior.
- **Corrección:** hay tres alternativas:
  - asiento ranurado radialmente, con longitud de ranura ≥ 2·R(1 − cos π/N) más tolerancia;
  - libertad radial del trinquete en el carro;
  - centrar el asiento en R(1 + cos π/N)/2, lo que reduce la interferencia a ±1,8 mm (todavía insuficiente con 1 mm de holgura).

  En cualquier caso, agregar la verificación `R_bar·(1 − cos θ) ≤ holgura_x` a verifs.

**C3. Carrera sin margen** (`verifs`, fila "Carrera requerida")
- **Problema:** s_req = 36 + 2·940·sin5° = 199,85 mm contra 200 mm. El margen es 0,15 mm (FU 0,999) y la fila se marca como `pass`.
- **Efecto:** las tolerancias pueden impedir que el trinquete caiga detrás de la barra siguiente. Las fuentes son:
  - la posición angular de las 36 barras (±0,5 mm típico);
  - las holguras de los pasadores;
  - la tolerancia de carrera del cilindro;
  - la holgura del asiento.

  El resultado sería que la punta o el chaflán del trinquete apoye sobre la barra, con una carga no considerada en el modelo.
- **Corrección:** subir la carrera a unos 210–220 mm o reducir el recorrido libre de forma justificada. Agregar una verificación con margen mínimo explícito (por ejemplo ≥ 5 mm) en vez de FU ≤ 1.

### MAYOR

**M1. r_eff = 0,80 m no es cota superior** (`PARAM_GROUPS.friccion`, `compute › cases`)
- **Problema:**
  - Con presión lineal (excentricidad e), el torque de fricción no depende de e, porque ∫q·r·dA conserva r_u = 0,672.
  - r_eff = 0,80 es un juicio por planitud o "carga al borde", y no se deriva del FEA: la presión inferior es un dato del modelo, no un resultado.
  - La deformación elástica del cajón (global ≈ 0,4–0,5 mm) concentra el contacto hacia el centro, no hacia el borde.
  - El borde solo domina por imperfecciones. Lo mismo ocurre si los cordones de las 36 barras en la cara inferior no se esmerilan a ras: en ese caso r ≈ 0,94.
- **Efecto:**

| Caso | F_c [kN] | p [bar] | FS |
|---|---|---|---|
| μ 0,20, r 0,94 | 370,1 | 582 | 1,20 |
| μ 0,20, r 1,00 | 393,6 | 619 (> alarma) | 1,13 |
| μ 0,25, r 1,00 | 491,7 | 773 | **0,91 (no gira)** |

  μ_max con r = 1,0 es 0,226 a 700 bar y 0,194 a 600 bar.
- **Corrección:**
  - Especificar planitud de las caras de contacto (disco y placa base) y esmerilado a ras de las soldaduras en la cara inferior.
  - Calcular la distribución de contacto con un modelo unilateral o Winkler del conjunto disco–placa base–grout, o adoptar r = 0,94–1,0 en el caso de diseño.

**M2. Flexión global del cajón mal modelada; faltan corte de nervios y soldaduras de almas** (`verifs`, fila "Flexión global… voladizo")
- **Problema:** se usa M = q_max·(R − R_carga)²/2 como voladizo 1D, lo que da 8,55 MPa. En un disco, la carga superior (Ø1600) y la reacción inferior (Ø2000) forman un sistema autoequilibrado que flecta el sándwich completo.
- **Efecto:**
  - Solución axisimétrica de placa con borde libre y presión inferior uniforme (`indep.py`): M_r,centro ≈ 89,7 kN·mm/mm. La tensión de membrana es σ = M/(t·130) = **23,0 MPa** (2,7 veces la de la herramienta). Sumada a la flexión local convergida (unos 29 MPa) da unos 52 MPa, FU ≈ 0,25. Pasa, pero la fórmula es incorrecta.
  - El corte vertical total en r = 800 mm es V ≈ 1153 kN. Lo toman solo los 12 nervios de 20×100: τ = 48 MPa, FU 0,35 contra 0,6F_y/1,67. No se verifica.
  - El flujo rasante nervio–plancha es de unos 0,96 kN/mm, más la reacción de línea de unos 0,25 kN/mm. Un filete doble de 6 mm da unos 1,25 kN/mm. No hay ninguna verificación de las soldaduras de almas y nervios.
- **Corrección:**
  - Reemplazar la fórmula por un modelo sándwich axisimétrico, o por un modelo 3D de cáscaras del cajón con almas.
  - Agregar el corte de nervios y las soldaduras alma/nervio–plancha.
  - Superponer la membrana global a la flexión local.

**M3. Guía: volcamiento y anclaje no verificados; L_g sin respaldo** (`verifs`, bloque "guía")
- **Problema:**
  - σ = R/(e·L) supone aplastamiento uniforme en 10 mm de empotramiento. La carga R = 264,7 kN actúa a 15 mm sobre la ranura y genera M ≈ R·(15 + 5) ≈ 5,3 kN·m por cada 150 mm. Con 10 mm de empotramiento, el aplastamiento elástico equivalente supera 2000 MPa. El riel solo funciona si está apernado o soldado, y eso no se verifica.
  - L_g = 250 mm, sobre un carro de 300 mm, supone reacciones casi puntuales en los extremos. Con distribución lineal en toda la longitud, L_g ≈ 2/3·300 = 200 mm.
- **Efecto:** con L_g = 200: K pasa de 1,240 a 1,287 (+3,8 %), F_c de diseño de 315 a 327 kN, R_g de 265 a 331 kN (+25 %) y el aplastamiento sube a FU 0,71.
- **Corrección:** definir las almohadillas del carro (posición y largo), verificar pernos o soldadura del riel a la placa base frente a volcamiento, y justificar L_g.

**M4. Interfaz trinquete–carro no verificada; indicador "vmFar" no válido** (`runPawl`, `verifs`; el UI muestra vmFar)
- **Problema:**
  - Con los apoyos del propio modelo (labio inferior de 25 mm en la boca y labio superior posterior), la reacción en la boca es **796 kN ≈ 1,8 F** y la posterior 351 kN, ambas desde el FEA. En 25×90 mm eso da un aplastamiento de unos 354 MPa. Supera 0,9F_y = 310 MPa si el carro es A572 Gr50.
  - No se verifican el cuerpo del carro, su alojamiento ni el ojal del vástago en el carro.
  - El indicador vmFar depende de la malla: 312 / 355 / 519 MPa con h = 5 / 2,5 / 1,25 mm. Es la cola de la singularidad del apoyo puntual por penalización en la esquina del labio, que en compresión llega a −878 MPa con h = 1,25.
- **Efecto:**
  - La fibra traccionada en la boca sí converge: 285 / 297 / 304 MPa, por debajo de la viga (343 MPa). El chequeo por teoría de vigas (FU 0,86) es conservador y válido.
  - El pico (942 MPa) y vmFar no deben reportarse como verificación.
- **Corrección:**
  - Agregar el aplastamiento del labio con la geometría real del carro.
  - Modelar el apoyo como contacto o base elástica distribuida.
  - Reportar tensiones linealizadas (membrana + flexión) en la sección de la boca.
  - Retirar vmFar o rotularlo como singular.

**M5. Fatiga no evaluada** (verifs completo)
- **Problema:** el trinquete, los pasadores, la soldadura de la mejilla y la del riel ven un ciclo por cada 10° de giro (36 por vuelta). Las barras ven 2 ciclos por vuelta. Con tensiones nominales de 280–340 MPa al calado y 200–240 MPa a la fuerza de diseño (en trinquete y pasador), la fatiga puede gobernar.
- **Corrección:** definir el ciclo de servicio (vueltas por año y vida útil), elegir la clase de servicio según ASME BTH-1 o AISC 360-22 Apéndice 3, y verificar.

**M6. Carga en la plancha superior: uniforme, sin excentricidad, con interfaz indefinida** (`discModel`, `compute.q_top`)
- **Problema:** para la plancha inferior se usa q_max (con e), pero para la superior se usa q medio sobre Ø1600. Con e = 150 sobre un círculo de 800 mm de radio, q_max/q_avg = 1 + 4e/R = 1,75. Además, la carga real (patines, apoyos o parrilla de vigas) produce cargas de línea o concentradas, no presión uniforme.
- **Efecto:** con presión uniforme a q_max, σ_top pasa de 24,4 a unos 43 MPa (FU 0,21). Con cargas de línea, el valor queda indeterminado.
- **Corrección:** definir la interfaz de carga y aplicar la excentricidad también en la plancha superior.

**M7. Presión bajo la placa base** (`compute.g_max`)
- **Problema:** se usa σ = N/A·(1 + 6e/B) en un solo eje. La excentricidad puede tener cualquier dirección. En el peor ángulo, σ = N/A·[1 + 6e·√(1/BX² + 1/BY²)]. Además, la fórmula supone una placa rígida de 80 mm, y el disco Ø2000 cubre todo el lado BY.
- **Efecto:**
  - Caso biaxial: 0,988 MPa (FU 0,99), contra 0,904 MPa de la herramienta (+9,4 %).
  - Sin reparto de la placa (huella Ø2000): 0,95 MPa medio y 1,52 MPa máximo.
- **Corrección:** usar la excentricidad biaxial, verificar la rigidez de la placa base (placa sobre Winkler) y la capacidad real de la losa o grout.

**M8. Cargas laterales y sísmicas ausentes** (pivote, buje, placa base, anclajes)
- **Problema:** H = 0,055·W (162 kN) solo representa la fricción excéntrica, que vale μ·N·e·(4/3)(Rc³ − Ri³)/(Rc⁴ − Ri⁴):

| μ | H [kN] | % de W |
|---|---|---|
| 0,15 | 89 | 3,0 |
| 0,20 | 118 | 4,0 |
| 0,25 | 148 | 5,0 |
| 0,50 (seco) | 296 | 10,1 |

  Una instalación permanente en Chile requiere un caso sísmico según NCh2369, con aceleración horizontal muy superior al 5 % de W. El buje admite H ≤ 30·150·100 = 450 kN ≈ 0,15·W.
- **Corrección:** agregar el caso sísmico y de impacto de carga para pivote, buje, tope o anclaje del disco y la placa base, o definir topes o retención sísmica independientes.

### MENOR

| # | Ubicación | Problema | Efecto | Corrección |
|---|---|---|---|---|
| m1 | `verifs` barra 4f | AISC 360-22 F11.1 limita M_n = F_y·Z ≤ 1,6·F_y·S. Para una sección redonda Z/S = 1,698, así que gobierna 1,6S. | M_n/Ω sobrestimado 6,1 % (11,81 contra 11,13 kN·m). FU sube de 0,52 a 0,55. | Aplicar el tope. |
| m2 | `verifs` barra corte | Ω_v = 1,50 solo aplica a G2.1(a) (almas de perfiles I laminados). Para lo demás, G1 exige Ω_v = 1,67. | FU sube de 0,56 a 0,62. | Ω_v = 1,67. |
| m3 | `runDisc` sumR | Las reacciones por grupo se suman con \|R\|. En los parches rígidos de barra hay nodos con signo opuesto. | Barra: 52,8 kN por defecto, 70,9 / 82,3 / 89,5 kN al refinar, siempre creciente. La suma con signo converge a 45,6 → 46,0 kN. Es conservador pero no tiene sentido físico. | Usar la suma con signo, o \|Σ R\|. |
| m4 | `runDisc` y `fea.plate` | La tensión se recupera en puntos de Gauss o centroide. Con Q4, la curvatura normal al apoyo es constante en el elemento, así que el pico en el apoyo converge como O(h). | Disco: 25,6 MPa (por defecto) → 27,3 → 27,9 → 28,3 MPa con h_r 10/5/3 mm. Extrapolado, unos 29 MPa: −12 % en el valor por defecto (FU 0,12 → 0,14). En el benchmark de placa empotrada el error en el borde llega a −36 % con n = 10. | Refinar junto a los apoyos, extrapolar a la línea de apoyo, o agregar un benchmark empotrado a `test_fea.js`. El existente (simplemente apoyado, centro) no ejercita los picos en apoyos. |
| m5 | `PARAM_GROUPS` | H_frac = 0,05 (T_piv) y H_bush = 0,055 (buje) son hipótesis distintas y ninguna depende de μ. | Despreciable en la fuerza (T_piv ≈ 0,5 % de T). En seco, H real ≈ 0,10·W. | Derivar H con la fórmula de M8 para cada caso. |
| m6 | `compute.Fmax` | Se usa la fuerza de calado a la presión nominal de alivio. No se incluyen la sobrepresión de la válvula (presión de apertura, acumulación) ni el impacto al tomar la barra después del recorrido libre de 36 mm. | Del orden de +5–10 % en todas las verificaciones de la cadena de empuje. | Usar 1,1·p_alivio o la presión de acumulación certificada. Especificar el acercamiento lento. |
| m7 | `verifs` | Faltan verificaciones: aplastamiento del pasador en la mejilla y en el ojal (79,5 y 90,9 MPa, pasan); placas con pasador según BTH-1 3-3.3 (mejillas); pasador del ojal del vástago en el carro; anclaje de la ménsula; metal base de la soldadura PJP (J2.5 y J4). Tampoco se considera la contrapresión del lado vástago, que con 5–10 bar vale −1,6 a −3,2 kN. | Bajo | Agregar las verificaciones. |
| m8 | `discModel` | La simetría del sector solo es válida si N_bar/N_rib es entero y el patrón de barras es simétrico respecto de los nervios. Con otros parámetros, el modelo sería incorrecto sin aviso. Hay masas fijas en el código: 3070 kg, buje de 8,1 kg y el contrataladro Ø160/260/25 del cubo. | Robustez paramétrica | Agregar validación y parametrizar. |
| m9 | `calc.py` | Pandeo con Ø90 en vez del vástago, A derivada de 445 kN, masa fija y planchas 67/70 MPa fijas. | Versión obsoleta | No usarla como respaldo. Archivarla. |

### COMENTARIO (sin observación o positivo)

- **Mecánica del accionamiento:**
  - El brazo mínimo R·cos(π/N) es correcto y conservador.
  - La curva por carrera usa a(θ) y Δ(θ) correctamente.
  - Los dos cilindros, en ±X empujando en ±Y sobre barras opuestas (5° y 185°, ambas en el patrón), forman un par puro para cualquier θ: las componentes radiales F·sinθ se anulan. La condición es un circuito en paralelo con igual presión. Con circuito en paralelo, el cilindro libre completa su recorrido antes de que suba la presión, así que el sistema se autoiguala.
  - El torque de reacción queda autoequilibrado dentro de la placa base: ménsulas por un lado, fricción de la interfaz por el otro. No se transmite torque a la fundación.
- **Factor de guía:** K = (1 + 2μ_g·Δ/L_g)/η_c es exacto para fuerzas de guía en el eje del cilindro, con R calculado desde F_b. En verifs, R se calcula con F_max, lo que es conservador.
- **Fricción:** cada carrera parte del reposo, así que corresponde el μ estático, y se usa bien. Advertencia: riesgo de stick-slip con grasa grafitada a muy baja velocidad, y μ estático creciente con el tiempo de permanencia bajo carga.
- **Criterio de calado:** verificar toda la cadena de empuje a F_max = A·p_alivio hace que la seguridad estructural no dependa de μ. Es un buen criterio.
- **Normas:**
  - J7 (1,8F_y, Ω 2,0), J2.5 PJP (0,6F_EXX, Ω 2,0), E = S − 3 mm y E3 (KL/r ≈ 6) están bien aplicados.
  - 0,6F_y frente a σ_vm, rotulado como "F11", es conservador pero no es un criterio de F11.
  - En pasador y trinquete, F_y/N_d es conservador frente a las tensiones de flexión admisibles de BTH-1 3-2.3 para secciones compactas.
  - N_d = 2,0 corresponde a la Categoría de diseño A de BTH-1. BTH-1 aplica por analogía (no es un dispositivo bajo el gancho). Conviene justificar la Categoría A frente a la B (N_d = 3,0).
  - Pandeo de Euler con el vástago en toda la longitud de 650 mm: es conservador respecto del cilindro escalonado. Se recomienda ISO/TS 13725.
- **FEA MITC4 (`fea.js › plateKe`):**
  - La formulación es correcta. Puntos de amarre de γ_ξ en (0, ±1) y de γ_η en (±1, 0). Interpolación de Bathe–Dvorkin. Transformación covariante → cartesiana con J⁻¹. Flexión integrada 2×2. k_s = 5/6.
  - El ensamblaje simétrico en banda es correcto.
  - La penalización k_p = 10⁶·max(K_ii) está bien condicionada en doble precisión.
  - La penalización de simetría k_p·n·nᵀ (β·n = 0, con normal (0,1) y (−sinα, cosα)) es correcta.
  - El equilibrio es exacto (ΣF = ΣR = 426,7 y 260,2 kN).
- **Benchmarks:**
  - Simplemente apoyada: w 2,2178 contra 2,2168 (Navier).
  - Cantiléver Q4: −1,4 %.
  - Placa empotrada (propio): w = 1,267·10⁻³ q a⁴/D contra 1,26·10⁻³.
  - Anillo sectorial empotrado/apoyado (propio, malla polar con simetría): converge a σ_borde = 64,9 MPa (Kirchhoff) con O(h). Valida la malla polar y la condición de simetría.
- **Apoyos rígidos (w = 0) en almas, nervios y barras:**
  - Son adecuados para la flexión local. Las barras tienen EA/h ≈ 7,7·10⁶ N/mm y el panel tiene w ≈ 0,02 mm.
  - El acortamiento de las almas (unos 0,005 mm) es pequeño. Los apoyos rígidos sobrestiman algo los momentos negativos, es decir, son conservadores en lo local.
  - No representan la flexión global del cajón (ver M2), que es el aspecto no conservador.
  - El empotramiento en el cubo es razonable: reacción de unos 3,5 kN, sin influencia.
- **Trinquete (Q4):**
  - El momento integrado en la boca coincide con F·lev (35,97 contra 36,94 kN·m en x = X_m − h/2).
  - La carga nodal solo en Y sobre el arco escalonado es aceptable lejos del asiento.
  - El contacto Hertz conforme Ø70/R36 da b = 8,5 mm y p₀ = 371 MPa, aceptable si el contacto está centrado (ver C2).
- **Contacto q_max:** la fórmula 1 + 4eR/(R² + r²) para el anillo es correcta. La presión local real bajo almas y barras será mayor que q_max, pero está lejos de 10 MPa.

---

## 3. Estudio de malla FEA (disco)

| Malla (h_r / Δθ) | Nodos | σ_vm inferior [MPa] | σ_vm superior [MPa] | Barra (Σ con signo) [kN] | Barra (Σ\|R\|, herramienta) [kN] |
|---|---|---|---|---|---|
| Por defecto (≈20 mm / 1,25°) | 1392 | 25,59 | 24,36 | 45,6 | 52,8 |
| 10 / 0,625° | 4895 | 27,25 | 25,60 | 45,8 | 70,9 |
| 5 / 0,3125° | 17271 | 27,85 | 26,56 | 46,0 | 82,3 |
| 3 / 0,2° | 44640 | 28,28 | 26,88 | — | 89,5 |

- El máximo está en el nervio, en r ≈ 410 mm (panel entre las almas R300 y R550).
- La reacción del alma R735 converge (244 → 240 N/mm).
- Estimación a mano para el panel empotrado de 250 × 215 mm: unos 30–33 MPa. Es coherente con el FEA convergido.

## 4. Acciones recomendadas (orden)

1. C1, C2 y C3: confirmar la ubicación de la soldadura de las barras, la libertad radial del asiento y el margen de carrera. Corregir el diseño o el modelo antes de emitir.
2. M1: especificar planitud y esmerilado a ras, y recalcular con r = 0,94–1,0, o con distribución de contacto calculada.
3. M2 a M8: agregar al menos:
   - modelo global del cajón, corte de nervios y soldaduras de almas;
   - anclaje del riel;
   - apoyo del carro;
   - fatiga;
   - plancha superior con e e interfaz real de carga;
   - suelo biaxial;
   - caso sísmico.
4. Menores: tope 1,6S, Ω_v 1,67, suma de reacciones con signo, benchmark empotrado y recuperación en apoyos, y validaciones paramétricas.
