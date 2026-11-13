# Plancha base en el modo guiado (drive_mode = 1): ¿tiene el mismo problema que el soporte E? (10-11-2026)

Seguimiento de 4a96335 (`docs/qa/plancha_base_soporte_E.md`). Modo guiado: cilindros paralelos a y en x = ±x_g = ±1.140 mm, ménsula del ojal trasero soldada a la base, patín sobre una bancada de 160 × 40 con ranura T, riel-leva sobre dos pórticos en la prolongación de la bancada. Base de 2.560 × 2.560 × 18 mm, sin anclaje.

## Resumen

1. **Sí, el modo guiado tiene el mismo mecanismo.** En el empuje a calado la ménsula recibe −F·ŷ a la altura del eje (h = 105 mm por defecto, 160 mm con la interfaz B), y la reacción la da la mesa, no la bancada. El par M = F·h = 46,8 kN·m (71,3 con B) es el mismo que el del soporte E. Con los dos cilindros, M₂ = −M₁ entre (1.140; −945) y (−1.140; 945), y el tramo en x lleva el vector a lo largo de su eje: es **torsión de la base**. Las bancadas corren en y y son secciones abiertas, de modo que no aportan rigidez a torsión.
2. **El retorno con la uña trabada en la rampa sí se cierra localmente** (par cilindro–riel sobre la misma bancada): ménsula, patín y pórticos están en la franja x ≈ x_g y los pares por cilindro suman cero. El atasco a nivel de toma (chaflán sobre el pasador siguiente) cruza la base como el empuje, con 8,4 kN·m (12,8 con B).
3. **FEA de la base completa** (malla de 40 mm, por defecto / B): con la mesa vacía y los dos cilindros a calado, la plancha lejos de las ménsulas queda en FU 2,0 / 3,5 y la bancada en 4,7 / 7,6. Las esquinas libres suben 0,13 / 0,23 m (cálculo lineal: no hay equilibrio con desplazamientos pequeños). Junto a la esquina de las mejillas el pico depende de la malla: 8,5 con 40 mm y 21 con 20 mm. Con la mesa cargada: 3,9 / 6,0 junto a las mejillas, 2,2 / 3,4 lejos y 1,8 / 2,8 en la bancada. Con un cilindro y la mesa vacía no hay equilibrio. Los valores son menores que en el modo pivotado (lejos: 7,4 / 11,5 con la mesa vacía), pero **no cumple**.
4. **No hay un refuerzo menor que lo resuelva.** Cerrar la franja de plancha sola entre la ménsula y la prolongación de la bancada baja la plancha pero deja la bancada en FU ≈ 4 con la mesa vacía. Agregar un perno en cada esquina libre pide ≈ 75 kN por perno (126 kN con B) y la bancada sigue en 3,7 (B 5,8). El modo guiado queda con la misma decisión pendiente que el pivotado.
5. **Implementado.** Filas de la plancha base bajo la ménsula en el grupo «Articulaciones» del modo guiado, con FU y estado «pend»: franja (12,1 empuje, 2,09 retorno), corte (0,34) y torsión de la base (cota inferior 2,55). Con eso, `verdict.estado_global` del modo guiado pasa de «CUMPLE» a «NO CUMPLE / PENDIENTE DE DECISIÓN», con `fuMaxPend` = 12,1. Además: exportación `designDrive().guiado.plancha_base`, verificador `tests/indep_accionamiento.py` (prueba 9) y golden del modo guiado (solo filas nuevas).

## 1. Mecánica de cargas del modo guiado

### 1.1 Dónde y a qué altura entran las fuerzas a la base

Coordenadas del cilindro 1 (lado +x, empuje +y, giro antihorario). El cilindro 2 se obtiene por rotación de 180°, y el giro horario por simetría en y. Las alturas z se miden sobre la cara superior de la plancha.

| Elemento | Dónde (planta) | Altura z | Qué recibe | Fuente en el núcleo |
|---|---|---|---|---|
| Ménsula del ojal trasero (dos mejillas de 25 × 325, separadas 150 mm, soldadas a la plancha con 4 filetes) | Ojal en (x_g; y_ojal) = (1.140; −945); mejillas en x = 1.040…1.065 y 1.215…1.240, y = −1.060…−735 | h = h_eje = h_disco/2 + Δ_interfaz = 105 (B: 160) | Empuje: −F·ŷ; retorno: +F_ret·ŷ | `bracketGeo`, `guideGeo().y_eye`, filas «Articulaciones» |
| Patín sobre la bancada (lengüeta en la ranura) | Bancada x = 1.060…1.220, y = ±523; patín de 572 mm entre y = −492 y 289 según θ | Reacciones laterales R_f, R_r a z_T = t_bancada − h_ranura/2 = 31; vuelco y cabeceo por la cabeza T | Reacciones de guía (± 190…280 kN, par en planta por la excentricidad x_g − a), roce μ_g·ΣR, vuelco H·Δz | `driveAtG`, `stallMax`, filas «Patín y guía» |
| Riel-leva sobre dos pórticos | Pórticos en y = ±603 (luz 1.205), patas en x = 1.030…1.070 y 1.210…1.250, sobre la prolongación ensanchada de la bancada (x = 1.030…1.250, y = ±523…±683) | Seguidor a z_F = 188 (B: 243) | Retorno: N_rampa = F_ret/sen α o N_toma = F_ret/tan β, con reparto por la regla de la palanca | `camGuidedRaw` (`portico`, `Lsp`, `zF`, `kR`), `levaGuiada.fabricacion.porticos`, `prolongacion_bancada_local` |
| Mesa (interfaz) | R_i…R_o = 131…1.000 | Roce a z ≈ 0; pasador a h | F_pas·ŷ ± H·x̂ en el pasador, que se cierra con el roce de la interfaz y el otro cilindro | `compute` (casos de giro) |

Separaciones: entre el extremo delantero de las mejillas (y = −735) y el extremo de la prolongación de la bancada (y = −683) quedan **52 mm de plancha sola** (franja crítica de la FEA).

### 1.2 Cómo se cierran las fuerzas

- **Empuje a calado.** El cilindro empuja el patín con F y la uña lleva F_pas = η·F al pasador de la mesa, en línea con el eje (la uña y el pasador están a la altura h). La guía de la bancada solo toma las reacciones laterales (el par en planta F_pas·(x_g − a)), el roce y el vuelco del roce H = μ_s·F_pas. La mesa reacciona con el roce de la interfaz (a nivel de la plancha) y con el otro cilindro, que empuja en −y desde x = −x_g. **El par F·h de la ménsula no se cierra en la bancada**: la bancada no toma fuerza en y (salvo el roce), y la otra mitad del par está en la mesa. Con dos cilindros los pares de la mesa se anulan (en ella F₂ = −F₁ a la misma altura), y lo que queda sobre la base es M₁ en la ménsula 1 y M₂ = −M₁ en la ménsula 2.
- **Retorno con la uña trabada en la rampa.** El cilindro tira del patín con F_ret y el seguidor apoya en la rampa del riel. El riel recibe −F_ret·ŷ y +N_x·x̂ a z_F, y lo pasa a los pórticos, que están en la prolongación de la misma bancada. La ménsula recibe +F_ret·ŷ a h, y el patín pasa a la bancada el resto (el cabeceo (z_F − h)·F_ret y el vuelco z_F·N_x). **La suma por cilindro es cero**: el par se cierra en la franja de la bancada (ménsula–plancha–bancada–pórticos), sin cruzar la base.
- **Retorno, atasco a nivel de toma.** Es el caso N_toma = F_ret/tan β del núcleo. El chaflán de la uña apoya en el pasador siguiente: la mesa toma F_ret y N_toma, y el riel (a nivel de toma) toma N_toma a z_F. La suma por cilindro sobre la base es h·(−F_ret; N_toma), igual y opuesta a la de la mesa, y cruza la base como el empuje: 8,4 kN·m (12,8 con B).

### 1.3 Pares sobre la base en cada apoyo (kN·m; Mx = −z·Fy, My = z·Fx)

Salida de `cargas.py` (por defecto; θ = 0, los otros estados difieren < 3 %):

| Apoyo | Empuje Mx | Empuje My | Retorno, rampa Mx | Retorno, rampa My | Retorno, toma Mx | Retorno, toma My |
|---|---|---|---|---|---|---|
| Ménsula | **+46,76** | 0 | −6,81 | 0 | −6,81 | 0 |
| Bancada: reacción delantera de la guía (z_T) | 0 | −5,93 | — | — | — | — |
| Bancada: reacción trasera de la guía (z_T) | 0 | +7,90 | — | — | — | — |
| Bancada: roce y cabeceo del patín | −2,34 | +4,70 | −5,39 | −6,49 | 0 | −3,91 |
| Pórticos del riel (z_F) | — | — | +12,20 | +6,49 | 0 | +8,86 |
| **Suma por cilindro** | **+44,42** | **+6,66** | **0** | **0** | **−6,81** | **+4,95** |
| ¿Autoequilibrio local? | No: \|M\| = 44,9 cruza la base | | Sí: se cierra en la bancada | | No: \|M\| = 8,4 cruza la base | |

Con la interfaz B: empuje 71,25 kN·m en la ménsula (suma 67,8; 6,7 en My); retorno-rampa local (ménsula −10,38, pórticos +15,77 / +8,38); retorno-toma \|M\| = 12,8.

El par del empuje en la ménsula (46,8 kN·m) es igual al del soporte E del modo pivotado: la fuerza y la altura del eje son las mismas. La diferencia es la geometría: el vector va exactamente en x y las ménsulas están a 945 mm de la línea media (en el modo pivotado, a 1.134). En el modo guiado hay además bancadas de 55 mm de espesor equivalente a lo largo de los bordes ±x.

### 1.4 Observación fuera del alcance

Por defecto, el cuerpo del cilindro (Ø 130 con el eje a 105 mm) llega a z = 40 mm sobre la plancha, que es la cara superior de la prolongación de la bancada (t = 40). Además, entre y = −870 y −510 pasa sobre la prolongación con **0 mm de holgura**. No hay una fila del núcleo que lo verifique («Cuerpo del cilindro libre sobre la base» compara con la plancha y no con la bancada). Con B (h = 160) la holgura es de 55 mm. No se tocó la geometría: queda informado para quien revise el modo guiado.

## 2. FEA de la base completa

Archivos en `docs/qa/plancha_base_modo_guiado/`: `exportar.js` (entrada con la API pública), `cargas.py` (tabla 1.3) y `casos.py` (FEA). La FEA reutiliza `docs/qa/plancha_base_soporte_E/basefea.py`, que ahora admite cargas nodales adicionales (`fext`) sin cambiar los resultados del estudio anterior.

- **Placa:** Mindlin Q4 de toda la base, con mallas de 40 y 20 mm, peso propio y contacto unilateral con la losa rígida en todos los nudos (conjunto activo), como en 4a96335.
- **Ménsulas:** cuerpos rígidos ligados a los nudos de la huella de las dos mejillas. M = ±F·h en el maestro.
- **Bancada y prolongación:** elementos ortótropos con la sección compuesta plancha + bancada, descontadas la ranura y la cabeza T.
  - A lo largo de la bancada: I = 13.898 mm⁴/mm (t_eq = 55 mm).
  - En sentido transversal: la banda continua bajo la cabeza T, de 30 mm.
  - Torsión: el J de Saint-Venant de la sección real con la ranura abierta, calculado con la función de Prandtl por diferencias finitas (J = 3,55·10⁶ mm⁴, τ_máx = 71,9·G·θ'). Una placa de 55 mm le daría 8,9·10⁶ mm⁴, es decir, 2,5 veces más. Con ese valor la mesa vacía daba FU 4,5 en lugar de 7,9.
  - Tensión en la bancada: √(σ_y² − σ_yσ_x + σ_x² + 3τ²), con σ_y = E·κ_y·c y τ = G·θ'·τ̂.
- **Cargas:** las de la tabla 1.3, repartidas en la huella de cada apoyo:
  - Reacciones laterales de la guía con distribución triangular por mitad del patín.
  - Pórticos por la regla de la palanca con el seguidor en su posición.
  - Peso propio de la plancha y las bancadas, la mesa vacía en el anillo R_i…R_o (14,0 kN; B 17,8), ménsula y medio cilindro en el maestro, patín, uña y medio cilindro sobre la bancada, riel y pórticos en las prolongaciones, y las ménsulas del otro sentido (sin carga) en su huella.
- **Casos:** tres posiciones del pasador (θ = −6,4°, 0 y +6,4°).
  - Empuje a calado con dos cilindros y con uno, con la mesa vacía y con la mesa cargada (huella R ≤ D/2 bilateral).
  - Retorno a nivel de toma, con dos cilindros (mesa vacía y cargada) y con uno (mesa cargada).
  - Retorno en la rampa (local), con la mesa vacía.
- **Criterio:** σ_vM ≤ Fy/Nd = 115 MPa (ASME BTH-1 §3-2.3; la torsión pura da σ_vM = √3·τ, equivalente al §3-2.2) en la plancha de 18 mm y en la bancada.
  - «Junto a la ménsula» es el máximo de la plancha. Cae en la esquina de las mejillas rígidas, en la franja de 52 mm, y depende de la malla: es una singularidad de la huella rígida, como en el soporte E. Con 20 mm se duplica o más, mientras que «lejos» y la bancada cambian menos del 30 %.
  - «Lejos» es el máximo a más de 450 mm de los ojales.
  - Los elementos dentro de la huella rígida no se cuentan.
- **Control:** con t = 300 mm la base no se levanta (ver `resultados/control_t300_def_malla40.jsonl`). La FEA propia del verificador (malla 80, bancada isótropa de 55 mm) da la misma conclusión: con la mesa vacía, 136 mm de levantamiento y FU 3,4 en la plancha; con la mesa cargada, 1,2.

## 3. Resultados (malla 40; máximo de las tres posiciones del pasador)

FU = σ_vM/(Fy/Nd), ASME BTH-1 §3-2 con Nd = 3,0 (categoría B). Los levantamientos son del cálculo lineal: cientos de mm indican que no hay equilibrio con desplazamientos pequeños.

| Caso | M por cilindro (kN·m) | Plancha junto a la ménsula | Plancha lejos (> 450 mm) | Bancada | Levantamiento máx. y dónde | Contacto (nudos) |
|---|---|---|---|---|---|---|
| **Por defecto (h = 105)** | | | | | | |
| Empuje, dos cilindros, mesa vacía | 46,8 | 8,5 (malla 20: 20,8) | 2,0 (malla 20: 2,5) | 4,7 (malla 20: 4,4) | **134 mm** en las esquinas libres (±1.280; ±1.280) | 4 |
| Empuje, dos cilindros, mesa cargada | 46,8 | 3,9 (malla 20: 9,2) | 2,2 (malla 20: 2,8) | 1,8 (malla 20: 1,9) | 3,4 mm en el borde junto a la ménsula | huella de la mesa |
| Empuje, un cilindro, mesa cargada | 46,8 | 3,9 | 2,2 | 1,8 | 3,4 mm | huella de la mesa |
| Empuje, un cilindro, mesa vacía | 46,8 | 8,6 | 2,6 | 5,0 | sin equilibrio (1,0 m lineal) | 11 |
| Retorno a nivel de toma, mesa vacía | 8,4 | 1,49 (malla 20: 3,8) | 0,57 (malla 20: 0,73) | 1,44 (malla 20: 1,42) | 6,8 mm en la esquina de la ménsula | 63 |
| Retorno a nivel de toma, mesa cargada (uno o dos) | 8,4 | 1,28 | 0,51 | 1,28 | 3,0 mm | huella de la mesa |
| Retorno en la rampa (local), mesa vacía | 6,8 | 1,70 (malla 20: 3,7) | 0,53 (malla 20: 0,59) | 1,52 (malla 20: 1,43) | 3,2 mm | 379 |
| **Interfaz B (h = 160)** | | | | | | |
| Empuje, dos cilindros, mesa vacía | 71,3 | 13,5 | 3,5 | 7,6 | **230 mm** en las esquinas libres | 2 |
| Empuje, dos cilindros, mesa cargada | 71,3 | 6,0 | 3,4 | 2,8 | 5,6 mm | huella de la mesa |
| Empuje, un cilindro, mesa cargada | 71,3 | 6,0 | 3,4 | 2,8 | 5,6 mm | huella de la mesa |
| Empuje, un cilindro, mesa vacía | 71,3 | 13,3 | 4,0 | 7,7 | sin equilibrio | 9 |
| Retorno a nivel de toma, mesa vacía | 12,8 | 2,25 | 0,76 | 1,97 | 12,3 mm | 27 |
| Retorno a nivel de toma, mesa cargada | 12,8 | 1,96 | 0,79 | 1,76 | 4,9 mm | huella de la mesa |
| Retorno en la rampa (local), mesa vacía | 10,4 | 2,56 | 0,68 | 2,01 | 5,2 mm | 171 |

Elementos críticos:

1. **Plancha de 18 mm en la franja de 52 mm entre el extremo delantero de las mejillas y la prolongación de la bancada** (por ejemplo (±1.060; ∓700)). Ahí entra el par de la ménsula a la bancada. Gobierna con la mesa cargada y en el retorno (también en el retorno en la rampa, que es local).
2. **Bancada, en el borde exterior junto a la prolongación** ((±1.220; ∓500…580)): flexión a lo largo y torsión de la sección abierta.
3. **Plancha lejos** (torsión de la base: (∓1.020; ∓700), entre la prolongación del otro lado y la mesa).
4. **Esquinas libres** (+1.280; +1.280) y (−1.280; −1.280): se levantan con la mesa vacía. Son las mismas esquinas que en el modo pivotado.

### Comparación con el modo pivotado (misma malla, por defecto)

| | Modo pivotado (4a96335) | Modo guiado |
|---|---|---|
| M por apoyo (empuje) | 46,8 kN·m, vector casi paralelo a x | 46,8 kN·m, vector en x |
| Mesa vacía: plancha junto / lejos | 21,1 / 7,4 | 8,5 / 2,0 (y bancada 4,7) |
| Mesa vacía: levantamiento | 279 mm | 134 mm |
| Mesa cargada: plancha | 13,8 | 3,9 (lejos 2,2; bancada 1,8) |
| Retorno, mesa vacía | 3,2 | 1,5 (rampa: 1,7, local) |

Las bancadas, de 55 mm equivalentes a lo largo de los bordes, reducen las tensiones y el levantamiento a la mitad o menos. Pero no cierran el camino de la torsión (son abiertas) y la bancada misma queda sobrecargada.

## 4. ¿Un refuerzo menor?

Variantes (malla 40, θ = 0 para el empuje y θ = −6,4° para el retorno; `resultados/variante_*`):

| Variante | Masa añadida (orden) | Empuje, mesa vacía: plancha junto / lejos / bancada / levantamiento | Empuje, mesa cargada: plancha / bancada | Retorno (toma / rampa): plancha / bancada | Anclaje |
|---|---|---|---|---|---|
| Actual | — | 7,9 / 2,0 / 3,9 / 123 mm | 3,5 / 1,7 | 1,49 / 1,70; 1,44 / 1,52 | — |
| **Cerrar la franja**: prolongación de la bancada hasta la cara trasera de la ménsula, con las mejillas soldadas sobre ella | ≈ 4 × 22 kg (las dos ménsulas de cada lado) | 2,4 / 1,4 / **4,0** / 111 mm | 1,15 / **1,9** | 0,54 / 0,34; **1,33 / 1,36** | — |
| Cerrar la franja + 1 perno en cada esquina libre (±1.200; ±1.200) | ídem + pernos | 2,6 / 2,4 / **3,7** / 17 mm | 1,15 / 1,9 | 0,53 / 0,34; 1,32 / 1,37 | **75 kN** por perno (empuje), 6 kN (retorno) |
| Interfaz B: cerrar la franja | ídem | 4,0 / 2,4 / **6,6** / 198 mm | 1,8 / **3,0** | 0,72 / 0,42; **1,82 / 1,77** | — |
| Interfaz B: cerrar la franja + 1 perno en cada esquina libre | ídem + pernos | 4,1 / 4,1 / **5,8** / 28 mm | 1,8 / 3,0 | 0,71 / 0,42; 1,82 / 1,77 | **126 kN** por perno (empuje), 10 kN (retorno) |

Lectura:

- Cerrar la franja resuelve el pico local de la plancha entre la ménsula y la bancada, incluido el retorno en la rampa, que es local. Pero el par sigue llegando a la bancada, y la bancada (sección abierta de 160 × 40 con la ranura T) no tiene ni la resistencia a flexión (FU 1,9 con la mesa cargada) ni la rigidez a torsión para llevarlo. Con la mesa vacía la base sigue flotando (111 mm). Además, la prolongación bajo el cuerpo del cilindro no tiene lugar por defecto (0 mm de holgura, §1.4): habría que hacerla más delgada o bajar el cuerpo.
- Bajo los pórticos del riel, la bancada queda en 1,3–1,5 (B 1,8–2,0) con el retorno, también con la franja cerrada y con la malla de 20 mm: el vuelco del riel, z_F·N, sobre la prolongación ranurada. Esta verificación no existía en el núcleo (solo se verificaba la soldadura prolongación–base). Queda dentro de la misma decisión, porque cualquier refuerzo de la bancada la cambia.
- Con el anclaje en las esquinas libres el levantamiento baja a 17 mm (B 28), pero el perno pide 75 kN (B 126; más que los 48 / 75 kN de A2 en el modo pivotado, porque no hay marco) y la bancada sigue en 3,7 (B 5,8).
- Una solución que cumpla necesita lo mismo que en el modo pivotado: un camino cerrado a torsión entre las dos ménsulas, o una base rígida, o anclaje. En el modo guiado, además, el tramo en y del camino pasa por la bancada, que tendría que crecer a una sección del orden de S ≥ M/(Fy/Nd) = 4,1·10⁵ mm³ (B 6,2·10⁵). Junto a la bancada no hay lugar: la mesa está a 60 mm de la bancada a mitad de lado y el patín llega a 8 mm del marco perimetral.

**Veredicto: el modo guiado NO cumple sin anclaje ni base rígida, y no hay un refuerzo menor que lo haga cumplir.** Los valores son menores que en el modo pivotado, pero el mecanismo es el mismo (torsión de la base entre las dos ménsulas con la mesa vacía) y la decisión pendiente también (anclaje con datos de la losa, base rígida o restricción del calado con la mesa vacía).

## 5. Implementado en el núcleo

`packages/core/tt300c.js`:

- `guidedBasePlate(P, R)`: mismo modelo de franja que `pivBasePlate`, aplicado a la huella de las mejillas con el ojal en (x_g; y_ojal). La retención está en el borde más lejano de la mesa y el modelo no cuenta la bancada. Calcula también la retención con la mesa vacía y la cota inferior de la torsión, τ = 6·m_xy/t² con m_xy = M/(2·B).
- `guidedBasePlateRows` agrega seis filas en «Articulaciones» (modo guiado):

| Fila | Por defecto | Interfaz B | Norma | Estado |
|---|---|---|---|---|
| Modelo de la transferencia de carga y casos | M = 46,8 / 6,8 kN·m | 71,3 / 10,4 | — | info |
| Flexión sin anclaje, empuje a calado (franja, σ = 6·M_corte/(b·t²)) | **12,1** | 18,4 | ASME BTH-1 §3-2.3 | pend |
| Flexión sin anclaje, retorno (sin retención detrás del talón) | **2,09** | 3,18 | ASME BTH-1 §3-2.3 | pend |
| Corte de la franja | 0,34 | 0,52 | ASME BTH-1 §3-2.2 | ok |
| Torsión de la base entre las dos ménsulas (cota inferior, placa libre) | **2,55** | 3,88 | ASME BTH-1 §3-2.2 | pend |
| Levantamiento (anclaje no definido) | M a anclar 46,8 kN·m | 71,3 | — | pend |

  La franja no cuenta la bancada y queda del orden del pico de la FEA junto a la ménsula con malla fina (12,1 frente a 8,5–21). La torsión es la cota inferior del mecanismo global (la FEA lejos da 2,0).
- `verdict` (sin cambios de código): las tres filas «pend» con FU > 1 entran a `pendientes_criticos`. El modo guiado pasa de «CUMPLE» a **«NO CUMPLE / PENDIENTE DE DECISIÓN»** con `fuMaxPend` = 12,08. `verdict.estructura` y `gira` no cambian.
- `designDrive(P, R).guiado.plancha_base` contiene lo siguiente. No se agrega a `tools/export_design.js`, cuyo JSON tiene que coincidir con el de `packages/web/planos_export.js` (que no se toca); el verificador usa las filas y el veredicto:
  - el estudio, el modelo, el ojal, h y la huella;
  - el cierre de las fuerzas (`cierre_empuje`, `cierre_retorno_rampa`, `cierre_retorno_toma`);
  - los dos casos de la franja y la mesa vacía;
  - la torsión (`M_kNm`, `V_esquina_kN`, `m_xy_kNm_m`, `tau_torsion_MPa`, `fu_torsion_cota_inferior`);
  - el resumen de la FEA y la conclusión.

  En el modo pivotado vale `null`.

Pruebas (TDD): «Ménsula del ojal trasero (modo guiado) · plancha base de 18 mm sin anclaje…». En «Veredicto · pendientes críticos visibles…», el caso «CUMPLE» pasa a ser el modo guiado con una plancha de 64 mm, porque el modo guiado por defecto ya no está libre de pendientes. Verificador independiente: `tests/indep_accionamiento.py`, prueba 9. Réplica sin leer el JS:
- ojal, franja (empuje, retorno, corte), torsión, fuerza de esquina, retención con la mesa vacía, estado de las filas y estado global;
- FEA propia de contraste de la base completa (malla 80).

`tests/indep_termica.py`, que replica el escenario térmico del modo guiado, aplica ahora el criterio del registro para las filas «pend»: no entran al FU gobernante ni al conteo de fallas, y las de decisión sin FU no van al bloque «fuera de alcance». Antes no hacía falta, porque el modo guiado no tenía filas «pend».

Golden: `tests/golden/tt300c_guiado.json` agrega las cuatro filas nuevas con FU y no cambia ningún valor existente. `tt300c_termica_alcance2_guiado.json` no cambia, porque la tabla térmica no lista estas filas.

## Reproducción

```
node docs/qa/plancha_base_modo_guiado/exportar.js '{}' /tmp/g_def.json
node docs/qa/plancha_base_modo_guiado/exportar.js '{"opt_uhmw":1}' /tmp/g_B.json
python3 docs/qa/plancha_base_modo_guiado/cargas.py /tmp/g_def.json                 # tabla 1.3
python3 docs/qa/plancha_base_modo_guiado/casos.py /tmp/g_def.json 40 todos          # tabla 3 (≈ 10 min)
python3 docs/qa/plancha_base_modo_guiado/casos.py /tmp/g_def.json 20 rapido         # malla 20 (≈ 15 min)
python3 docs/qa/plancha_base_modo_guiado/casos.py /tmp/g_def.json 40 rapido cerrar          # variante «cerrar la franja»
python3 docs/qa/plancha_base_modo_guiado/casos.py /tmp/g_def.json 40 rapido cerrar,anclar   # + perno en cada esquina libre
python3 docs/qa/plancha_base_modo_guiado/casos.py /tmp/g_def.json 40 rapido t=300           # control
```

Salidas en `docs/qa/plancha_base_modo_guiado/resultados/`.
