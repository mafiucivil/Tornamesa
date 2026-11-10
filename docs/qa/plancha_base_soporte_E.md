# Plancha base bajo el soporte del ojal E: revisión con la base completa y estudio de opciones (10-11-2026)

Seguimiento de d94d7c4 («Plancha base bajo el soporte del ojal E (10-11-2026)» en `docs/normas/registro.md`). Modo pivotado (`drive_mode = 2`), base de 2.560 × 2.560 × 18 mm, mesa Ø2.000, ojales E en (±1.134; ∓1.134).

## Resumen

1. **La observación sobre el modelo es correcta en la estática**: los dos cilindros están en ojales diagonalmente opuestos y trabajan en paralelo, F₂ = −F₁ y M₂ = −M₁. La base, como cuerpo libre, no tiene momento de vuelco neto y la losa no necesita retención global.
2. **La conclusión de d94d7c4 no cambia, pero el mecanismo es otro.** El par M = F·h de un soporte solo puede llegar al otro rodeando la mesa, y el vector momento (casi paralelo a un borde de la base) tiene que trasladarse en las dos direcciones del plano. Eso es **torsión de la base**: fuerzas de esquina ≈ M/B, con las esquinas libres hacia arriba, y m_xy ≈ M/(2·B) en toda la plancha. La plancha de 18 mm casi no tiene rigidez a torsión. Con la mesa vacía y los dos cilindros a calado, la base queda apoyada solo en los dos pies y el resto se levanta: 279 mm en el cálculo lineal, por defecto. Con la mesa cargada, la huella de la mesa queda fija y el caso es el del modelo de un soporte: FU 13,8, igual a la FEA de d94d7c4 (13,9).
3. **Ni C (marco perimetral) ni D (nervios) resuelven la mesa vacía.** Son secciones abiertas sin rigidez a torsión. El marco en cajón cerrado, de 70 mm de ancho (lo que queda libre junto a los bordes), cumple por defecto con la mesa vacía desde ≈ 730 kg, pero no cumple con la mesa cargada (el marco toma FU 1,4) ni con la interfaz B. Con plancha gruesa (B) hacen falta ≈ 64 mm por defecto (+2,4 t). Con la interfaz B, ninguna opción sin anclaje cumple dentro de los tamaños estudiados.
4. **No se implementó ninguna solución**, porque la recomendada no es claramente C ni D. Queda la decisión del mandante: anclaje con datos de la losa, base rígida o restricción del calado con la mesa vacía. Se implementó el punto 4: `verdict.pendientes_criticos[]`, `verdict.fuMaxPend` y `verdict.estado_global = «NO CUMPLE / PENDIENTE DE DECISIÓN»`, más la revisión en la exportación (`plancha_base.revision_base_completa`).

## 1. Revisión del modelo

### 1.1 Circuito hidráulico: ¿puede actuar un solo cilindro?

El núcleo modela los dos cilindros como un par alimentado en paralelo por una bomba (`Q_pump`), con un solo alivio de sistema (`p_relief`) y sin divisor de caudal ni válvulas por cilindro. El validador solo exige válvula de bloqueo con `n_cyl = 1`, y el módulo térmico menciona tramos aislados con retenciones como hipótesis de aceite atrapado. Con alimentación en paralelo la presión es la misma en los dos. **Un calado de un solo cilindro sí es posible** si uno no tiene reacción exterior: su bloque-uña no tomó el pasador (falla de sincronía), o su émbolo llegó a fin de carrera, donde la fuerza queda interna al cilindro. El otro llega entonces solo a la presión de alivio. Casos:

| Caso | Cilindros a calado | Mesa | Qué retiene la plancha | Credibilidad |
|---|---|---|---|---|
| S-vacía | los dos (M₂ = −M₁) | vacía: peso propio uniforme en R_i…R_o | nada fuera del peso propio | atasco con la mesa vacía (d94d7c4: el calado no depende de la carga) |
| S-cargada | los dos | cargada: huella R ≤ D/2 bilateral | la mesa | calado normal con carga |
| U-cargada | uno | cargada | la mesa | falla de sincronía con carga |
| U-vacía | uno | vacía | nada | doble falla (sincronía y atasco con la mesa vacía) |

### 1.2 Estática con los dos soportes

- F₁ actúa en E₁ a la altura h del eje sobre la plancha (105 mm por defecto, 160 con B); F₂ = −F₁ en E₂ = −E₁. Entonces M₁ = h·ẑ×F₁ y M₂ = −M₁. La suma de fuerzas y momentos que los cilindros aplican a la base es cero: no hay vuelco neto.
- En el empuje del sentido antihorario (ψ ≈ 98–103°), F₁ va hacia −y y M₁ ≈ M·x̂. En el horario (ψ ≈ 167–172°), M₁ ≈ M·ŷ. El vector momento es casi paralelo a un borde de la base.
- Para llevar M·x̂ de E₁ (+x, −y) a E₂ (−x, +y), un tramo del camino corre en y (flexión) y otro en x (torsión, porque el vector va a lo largo del eje del tramo). El camino diagonal pasa por el centro y está ocupado por la mesa. Con secciones abiertas (marco, nervios), la torsión solo la toma la plancha. En una placa cuadrada eso equivale a fuerzas de esquina alternadas V ≈ M/B, que bajan en las esquinas de los soportes y suben en las esquinas libres, y a un momento torsor uniforme m_xy = V/2.
- Valores: V = 18,3 kN y m_xy = 9,1 kN·m/m por defecto; con B, 27,8 kN y 13,9 kN·m/m. En 18 mm, τ = 6·m_xy/t² = 169 MPa (FU 2,55 frente a Fy/(Nd·√3) = 66,4 MPa) por defecto y 258 MPa (FU 3,9) con B. Esto es una **cota inferior**: es la placa libre en torsión pura, sin el peso ni el contacto. Se exporta en `plancha_base.revision_base_completa`.
- Rigidez: la placa libre de 18 mm giraría ≈ 0,4 m entre esquinas con ese m_xy. El peso propio de la base y de la mesa vacía (≈ 25 kN) equivale a ≈ 3 kN en las esquinas libres, lejos de los 18–28 kN pedidos. El peso no frena la torsión.

### 1.3 FEA de la base completa

Archivos en `docs/qa/plancha_base_soporte_E/`: `basefea.py`, `opciones.py`, `casos.py` y `exportar.js`.

- **Placa:** Mindlin Q4 con integración selectiva, de toda la base (2.560 × 2.560). Malla de 40 mm (4.225 nudos) para la plancha sola y de 80 mm para la comparación de opciones.
- **Soportes:** los dos son cuerpos rígidos ligados a los nudos de la huella de las paredes, con 3 grados de libertad maestros cada uno. M₁ va en el soporte 1 y −M₁ en el soporte 2.
- **Contacto:** losa rígida solo a compresión en todos los nudos, con resortes de 10⁷ N/mm y conjunto activo. Si el conjunto activo cicla, se cambia solo el 10 % de los peores nudos.
- **Cargas de gravedad:** peso propio de la plancha (ρ·g·t), mesa vacía uniforme en el anillo R_i…R_o (W_d + bloques-uña: 15,0 kN por defecto, 18,8 kN con B) y soporte más medio cilindro en cada maestro. La presión uniforme es conservadora: una mesa rígida sobre una base que se levanta concentra su peso en la zona levantada.
- **Mesa cargada:** huella R ≤ D/2 bilateral, como en d94d7c4.
- **Marcos y nervios:** vigas de Timoshenko sobre las líneas de la malla, con flexión y torsión. Sección compuesta con un ancho efectivo de plancha de 12·t, con un máximo de 200 mm. Torsión de Saint-Venant en la sección abierta y de Bredt en el cajón. La cartela de esquina se modela ligando al soporte los nudos del marco a lo largo de las paredes traseras y 280 mm más allá.
- **Verificación:** σ_vM ≤ Fy/Nd = 115 MPa (ASME BTH-1 §3-2.3; la torsión pura da σ_vM = √3·τ, equivalente al §3-2.2). En la plancha se informa el máximo junto al soporte, que en la esquina rígida de la huella depende de la malla, y el máximo «lejos», a más de 450 mm de los ojales. En los marcos se usa √(σ_b² + 3τ_t²)/(Fy/Nd).
- **Comprobación:** con espesor muy grande (t = 300) y M a calado, el levantamiento es de 0,01 mm. Con la mesa cargada, la plancha sola reproduce la FEA de cuadrante de d94d7c4 (13,8 frente a 13,9 en el empuje y 3,15 frente a 3,2 en el retorno).

### 1.4 Resultados con la plancha de 18 mm (malla 40, ψ = 97,6°; el otro extremo de la banda difiere < 2 %)

| Caso | M por soporte (kN·m) | FU junto al soporte | FU a > 450 mm | Levantamiento máx. y dónde | Contacto |
|---|---|---|---|---|---|
| **Por defecto (h = 105)** | | | | | |
| S-vacía, empuje | 46,8 | 21,1 | 7,4 | **279 mm** en el borde (−1.280; −280); 258 bajo la mesa | 2 nudos (los pies) |
| U-vacía, empuje | 46,8 | 20,7 | 6,9 | sin equilibrio (3,9 m lineal) | 4 nudos |
| S-cargada / U-cargada, empuje | 46,8 | 13,8 | 4,8 | 20,5 mm junto al talón (1.280; −800) | huella de la mesa |
| S-vacía, retorno (atasco) | 6,8 | 3,2 | 1,1 | 34 mm en la esquina del soporte (−1.280; 1.280) | 159 nudos |
| S-cargada, retorno | 6,8 | 3,15 | 1,07 | 17 mm en la esquina del soporte | huella de la mesa |
| **Interfaz B (h = 160)** | | | | | |
| S-vacía, empuje | 71,3 | 32,7 | 11,5 | **462 mm** en el borde; 430 bajo la mesa | 2 nudos |
| U-vacía, empuje | 71,3 | 31,6 | 10,5 | sin equilibrio | 4 nudos |
| S-cargada / U-cargada, empuje | 71,3 | 21,1 | 7,3 | 31 mm junto al talón | huella de la mesa |
| S-vacía, retorno | 10,4 | 4,9 | 1,8 | 58 mm en la esquina del soporte | 67 nudos |

Con la mesa vacía, la base de 18 mm flota sobre los dos pies. En el empuje se levantan los bordes y las esquinas libres; en el retorno se levanta la esquina de cada soporte, porque ahí está el talón. Los valores de cientos de mm salen del cálculo lineal: indican que no hay equilibrio con desplazamientos pequeños, no son una predicción. Con un solo cilindro y la mesa vacía no hay equilibrio sin anclaje.

### 1.5 Diferencia con d94d7c4

| Aspecto | d94d7c4 | Base completa |
|---|---|---|
| Modelo | Un soporte; retención solo por la mesa (franja hasta el borde lejano; FEA de cuadrante con la huella bilateral) | Dos soportes con M₂ = −M₁; mesa vacía como carga o mesa cargada como huella bilateral; peso propio |
| Mesa cargada | Franja 8,37 (B 12,8); FEA 13,9 | 13,8 (B 21,1); idéntico con uno o dos cilindros, porque la huella fija desacopla los soportes |
| Mesa vacía | Retención n_cil·M/s_H = 38,6 kN frente a 15,0 kN de peso: «no retiene» | Los dos pedidos no se suman: los momentos se anulan. Falta rigidez y resistencia a torsión de la base: fuerzas de esquina ≈ M/B = 18,3 kN (B 27,8), y la base flota sobre los pies |
| Remedio que sugiere | Retención del talón (anclaje) o base rígida | Rigidez a torsión de la base entre los soportes (base rígida o cajón cerrado) o anclaje: con el marco, dos pernos en las esquinas libres bastan |

La franja de d94d7c4 sigue valiendo como demanda local con la mesa cargada. El chequeo `mesa_vacia` (n_cil·M/s_H ≤ W) queda como cota del modelo de un soporte, y la conclusión «no cumple sin anclaje» se mantiene. Las filas y sus FU no cambian, y el golden tampoco.

## 2. Opciones

Criterio común:

- σ_vM ≤ Fy/Nd con Nd = 3,0 (ASME BTH-1 §3-2, categoría B) en la plancha y en los elementos nuevos.
- Soldaduras según AWS D1.1 (filetes y CJP; mínimos de la Tabla 5.8) y la resistencia 0,60·F_EXX/(1,20·Nd) del núcleo. Secciones y pandeo local según AISC 360-22.
- Malla de 80 mm. La columna «junto al soporte» depende de la malla: en la plancha sola, la malla de 80 da 13,5 frente a 21,1 con la de 40.

Interferencias medidas con la geometría del núcleo (por defecto):

- Cuerpo del cilindro: a 91 mm del borde más cercano. Placas-guía: a 90 mm. Bloques-uña: a 113 mm.
- Paredes traseras del soporte E: a **16 mm** del borde.
- Orejas de izaje en (±850; ±850): a 353 mm del borde.
- Mesa: a 280 mm del borde a mitad de lado y a 810 mm en la diagonal.

Una franja de ≤ 80 mm junto a cada borde está libre en toda la altura. Lo que vaya más adentro choca con el barrido del cilindro en las mitades de lado contiguas a cada soporte.

### 2.1 Tabla comparativa (por defecto / interfaz B)

FU = σ_vM/(Fy/Nd). La columna «elemento» es el marco, el cajón o el nervio. Los levantamientos son del caso S-vacía.

| Opción | Masa añadida | S-vacía: plancha junto / lejos | S-vacía: elemento | S-vacía: levantamiento | Mesa cargada: plancha / elemento | Interferencias | Fabricación | ¿Cumple? |
|---|---|---|---|---|---|---|---|---|
| 18 mm actual | 0 | 13,5 / 7,9 (B 21 / 12,5) | — | 268 mm (B 445) | 7,7 (B 11,7) | — | — | No |
| **C** marco abierto 150×10, continuo, con cartelas | 121 kg | 4,0 / 2,8 | 11,0 | 250 mm | 1,32 / 7,2 | Marco a ≥ 90 mm del cilindro; se suelda a la cara exterior de las paredes traseras del soporte (16 mm del borde) | Sencilla; se pierde el acceso exterior a las CJP pared–base del soporte (respaldo con barra o pared = marco) | No |
| **C** marco abierto 200×20 | 322 kg | 2,6 / 1,8 | 4,1 | 175 mm | 0,85 / 2,9 | Ídem | Ídem | No |
| **C** marco abierto 300×25 | 603 kg | 1,6 / 1,1 (B 2,9 / 2,0) | 2,1 (B 3,8) | 104 mm (B 203) | 0,62 / 1,7 (B 1,0 / 2,6) | Ídem | Ídem | No |
| **C** cajón cerrado 70 × 200, t 12 | 453 kg | 0,37 / 0,27 (B 0,56 / 0,38) | 1,41 (B 2,03) | 17 mm (B 30) | 0,54 / 2,2 (B 0,84 / 3,4) | Alma interior a 10–20 mm del cuerpo del cilindro y de las placas-guía; el cajón tiene que rodear el soporte (paredes a 16 mm del borde) | Soldadura de un solo lado (interior inaccesible; filetes o PJP de un lado en T, AWS D1.1 §2/§5); corrosión interior | No |
| **C** cajón cerrado 70 × 250, t 16 | 733 kg | 0,25 / 0,24 (B 0,37 / 0,31) | **0,92** (B 1,31) | 9,9 mm (B 17,4) | 0,43 / 1,40 (B 0,67 / 2,1) | Ídem | Ídem | No (masa > 600 kg; con la mesa cargada y con B no cumple) |
| **C** cajón cerrado 70 × 300, t 20 (solo B) | 1.077 kg | (B 0,29 / 0,29) | (B 0,95) | (B 11,2 mm) | (B 0,59 / 1,5) | Ídem | Ídem | No |
| **D** 2 nervios diagonales 150×15 del soporte hacia la mesa (hasta R ≈ 1.020) | 26 kg | 7,6 / 7,6 (B 12,0) | 11,4 (B 18) | 212 mm (B 350) | 1,7 / 6,5 (B 2,6 / 10) | El nervio cruza la zona de la oreja de la diagonal (850; −850) y llega al barrido del bloque-uña junto a la mesa | Sencilla | No: no da torsión; con la mesa cargada haría falta una sección que no cabe |
| **C + D** 200×20 + nervios | 348 kg | 3,5 / 3,5 (B 6,4) | marco 2,7 (B 4,8), nervio 6,1 (B 11) | 128 mm (B 247) | 0,58 / 2,1 (B 0,90 / 3,2) | Ídem C y D | Ídem | No |
| **B** plancha de 30 mm | +617 kg | 4,8 / 2,7 | — | 54 mm | 2,8 | Sube toda la tornamesa 12 mm | Plancha única de 2,56 m (o empalme CJP) | No |
| **B** plancha de 52 mm | +1.749 kg | 1,58 / 0,85 (B 2,56 / 1,35) | — | 8,7 mm (B 16) | 0,98 (B 1,50) | Sube 34 mm | Plancha gruesa, planitud | No |
| **B** plancha de 64 mm | +2.366 kg | **1,03** / 0,54 (B 1,66 / 0,86) | — | 4,3 mm (B 8,2) | 0,67 (B 1,03) | Sube 46 mm | Plancha gruesa, planitud | Por defecto en el límite; con B no |
| **A1** anclaje: 2 pernos por soporte detrás de las paredes traseras, (115; 320) y (−320; −115) en el marco local | pernos + placas | 3,0 / 0,68 (B 4,6 / 1,04) | — | 1,1 mm (B 1,7) | — | Fuera del barrido | Pide datos de la losa | Pernos: **116 kN** (B 177) en el empuje y 31 kN (B 50) en el retorno; con un cilindro, igual. Además hace falta refuerzo local del soporte y de la plancha |
| **A2** anclaje: marco 200×20 y 1 perno en cada esquina libre (±1.200; ±1.200) | 322 kg + 2 pernos | 0,57 / 0,23 (B 0,89 / 0,36) | marco 2,6 (B 4,0) | 2,0 mm (B 3,2) | — | Esquinas libres, sin barrido | Pide datos de la losa | Pernos: **48 kN** (B 75) en el empuje y 4 kN (B 12) en el retorno. El marco tiene que crecer (≈ 300×25 por defecto) |

Notas:

- **C abierto.** Marco y plancha forman una bandeja abierta: la torsión solo la toma la plancha. Al subir el marco de 150 a 300 mm, el levantamiento baja de 250 a 104 mm pero no desaparece, y el marco queda con FU 2,1 (torsión de Saint-Venant de una plancha de 25 mm). La altura disponible no limita, porque el marco va a R ≥ 1.270, fuera de la mesa y a ≥ 90 mm del barrido. El límite es la falta de celda cerrada. Con la mesa cargada, el marco toma momentos mayores que M (113 kN·m con 300×25): la esquina rígida del soporte gira contra la plancha retenida por la mesa a 280 mm.
- **C en cajón.** Es la única opción tipo C que da rigidez a torsión. El ancho está limitado a ≈ 70 mm por el cuerpo del cilindro y las placas-guía, y el cajón tiene que pasar frente a los soportes, que están a 16 mm del borde: eso obliga a rediseñar las paredes traseras como parte del cajón. Con 733 kg cumple el caso de la mesa vacía por defecto (0,92) con 10 mm de levantamiento de las esquinas libres. No cumple con la mesa cargada (1,40), y con B haría falta más de 1 t.
- **D.** Los nervios hacia la mesa no crean retención: la mesa solo comprime y con la mesa vacía no hay nada que los sujete. Tampoco dan torsión. Con la mesa cargada trabajan, pero el nervio toma ≈ 87 kN·m por defecto (FU 6,5 con 150×15): haría falta un nervio de ≈ 300 × 30 en la diagonal, justo donde está la oreja de izaje.
- **B.** El espesor actúa en toda la base (torsión y flexión local). Con 64 mm la tornamesa sube 46 mm y pesa 2,4 t más. Con la interfaz B no alcanza: FU 1,66 junto al soporte con la mesa vacía.
- **A.** Las fuerzas son por perno y a calado, sin factor. El perno, su placa y el cono en la losa se dimensionan con f'c, espesor, armadura y distancia a los bordes, que el proyecto no tiene, por lo que no se diseñan aquí. A2 es la disposición de menor fuerza: el marco lleva la flexión y los dos pernos de las esquinas libres toman la torsión.

## 3. Recomendación

| Pregunta | Respuesta |
|---|---|
| ¿Hay una solución C o D fabricable, de < 600 kg y sin interferencias? | **No.** Las opciones abiertas no dan torsión y no cumplen con la mesa vacía en ningún tamaño probado. El cajón cerrado cumple por defecto desde ≈ 730 kg, pero no con la mesa cargada ni con la interfaz B. Además, roza el barrido (10–20 mm) y obliga a rehacer las paredes traseras del soporte |
| ¿Cuál es la de menor masa que cumple sin datos de losa? | Por defecto, B con 64 mm de plancha (+2,4 t; FU ≈ 1,0 junto al soporte con la mesa vacía, 0,67 con la mesa cargada; la tornamesa sube 46 mm). Con la interfaz B, ninguna de las estudiadas |
| ¿Cuál es la técnicamente más eficiente? | A2: marco continuo con cartelas y un perno por esquina libre, de 48 kN (75 kN con B). Requiere los datos de la losa. Dimensionado en §5: pletina de 420 × 30 o cajón de 80 × 200 t 25 (≈ 1,0 t; B ≈ 1,6–1,8 t) y rediseño de las paredes traseras del soporte E |
| ¿Qué alternativa operativa existe? | Impedir el calado con la mesa vacía, por ejemplo con un alivio reducido mientras la mesa no está cargada (decisión hidráulica del mandante). Así gobierna la mesa cargada, y la solución pasa a ser local: C abierto de 300×25 deja la plancha en FU 0,62, pero el marco sigue en 1,7 y hay que redimensionarlo |

No se implementó ninguna geometría. Las filas de la plancha siguen con su FU y el estado «pend», ahora visibles en el estado global (punto 4).

## 4. Estado global visible (implementado)

Antes, `fuEstOf` y `fuTermOf` (TT.thermal) excluían las filas «pend» del FU gobernante. `verdict.estructura` solo mira las filas «fail», y la UI arma su insignia con `verdict.estructura`, `warnEst` y la cantidad `verdict.pend`. Con eso, el diseño por defecto se mostraba como «✓ ESTRUCTURA CUMPLE» con «3 pendiente», y el FU 8,37 solo aparecía en el FU máximo calculado por la UI.

Cambio mínimo en el núcleo (`analyze()`, `packages/core/tt300c.js`):

- `verdict.pendientes_criticos[]`: filas con estado «pend» y FU > 1 (también las no finitas), con `{grp, nombre, fu, sys, ref}`, ordenadas por FU. Las filas fuera del alcance térmico llevan `fuera_alcance_termico: true`: una decisión pendiente del diseño lo es en cualquier escenario.
- `verdict.fuMaxPend`: FU máximo de esas filas (0 si no hay).
- `verdict.estado_global`: «NO CUMPLE» si no gira o la estructura no cumple; «NO CUMPLE / PENDIENTE DE DECISIÓN» si hay pendientes críticos; «CUMPLE» en otro caso.
- `TT.thermal(...).alternativas[].byT[]`: se agregan `pendientes_criticos` y `estado_global`. `fuEst` sigue excluyéndolas, pero quedan a la vista.
- `verdict.estructura` no cambia de significado: resume las verificaciones resueltas, y el generador de planos la usa para negarse a emitir.

Por defecto: `estado_global = "NO CUMPLE / PENDIENTE DE DECISIÓN"`, `fuMaxPend = 8,37`, con 2 filas (empuje 8,37 y retorno 1,43). Lo que falta en la UI (otro agente): mostrar `estado_global` en la insignia y la tarjeta «Estructura», y listar `pendientes_criticos` con su FU y su referencia. La memoria puede leerlos de `verdict` en `cad/out/TT300-C_design.json`.

## 5. Estimación de A2 para la decisión del mandante (10-11-2026; no implementada)

Pedido: dimensionar el marco de A2 (marco perimetral continuo con cartelas y un perno en cada esquina libre), que en §2.1 quedó con FU 2,6 en el marco 200×20, e indicar la masa y los requisitos mínimos de anclaje a especificar. **No se cambió la geometría por defecto.**

### 5.1 Modelo

Es el de §2 (malla de 80 mm, `a2.py`):

- Marco continuo en los cuatro bordes, sobre las líneas de borde de la malla, como viga de Timoshenko con flexión y torsión. La sección es compuesta, con un ancho efectivo de plancha de 12·t (máximo 200 mm).
- Cartelas ligadas al soporte rígido hasta 280 mm.
- Un perno bilateral en cada esquina libre, (1.200; 1.200) y (−1.200; −1.200).
- Casos: empuje a calado con dos y con un cilindro, con la mesa vacía y con la mesa cargada; retorno con la mesa vacía. Se toman los dos extremos de la banda de ψ.
- Criterio:
  - Marco: √(σ_b² + 3τ_t²) ≤ Fy/Nd, con σ_b = M·c/I de la sección compuesta (ASME BTH-1 §3-2.3 y §3-2.2; Nd = 3,0).
  - Plancha: σ_vM ≤ Fy/Nd.
- Reproduce §2.1: con el marco 200×20 da 48,2 kN por perno y FU 2,61 en el marco con la mesa vacía. Con la mesa cargada el marco llega a 2,83 y el perno a 32 kN.

En el marco el momento es de flexión a lo largo del borde del soporte. El máximo está al final de la cartela y baja casi linealmente hasta la esquina anclada: con 300×25, de 97 a 55 kN·m. Por eso un acartelamiento local no alcanza: el marco necesita casi toda su sección en todo el borde. Al rigidizar el marco el momento crece (el marco atrae el par que antes llevaba la plancha) y el perno se descarga.

### 5.2 Marcos probados (máximo de todos los casos; masa del marco en los cuatro bordes)

| Marco | Masa | Por defecto: marco / plancha / perno / levantamiento | Interfaz B: marco / plancha / perno |
|---|---|---|---|
| 200×20 (A2 de §2.1) | 322 kg | 2,83 / 0,62 / 48 kN / 2,1 mm | 4,31 / 0,96 / 75 kN |
| 300×25 | 603 kg | 1,55 / 0,26 / 22 kN / 0,7 mm | — |
| 350×30 | 844 kg | 1,14 / 0,20 / 19 kN | — |
| 400×30 | 965 kg | 1,03 / 0,19 / 19 kN | — |
| **420×30** | **1.013 kg** | **0,99** / 0,19 / 19 kN / 0,25 mm | 1,51 / 0,32 / 30 kN |
| 400×35 | 1.125 kg | 0,88 / 0,18 / 18 kN | — |
| 500×35 | 1.407 kg | — | 1,15 / 0,30 / 30 kN |
| **550×40** | **1.768 kg** | — | **0,95** / 0,28 / 29 kN |
| T: alma 200×25 + ala 80×30 | 595 kg | 1,59 / 0,33 / 28 kN | — |
| T: alma 200×25 + ala 80×40 | 659 kg | 1,53 / 0,29 / 26 kN | — |
| Cajón 80 × 200, t 20 | 772 kg | 1,23 / 0,40 / 41 kN | — |
| **Cajón 80 × 200, t 25** | **965 kg** | **1,00** / 0,35 / 36 kN / 0,7 mm | — |
| Cajón 80 × 200, t 30 | 1.158 kg | 0,84 / 0,32 / 32 kN | — |
| Cajón 80 × 250, t 25 | 1.166 kg | 0,83 / 0,23 / 24 kN | — |
| **Cajón 80 × 200, t 40** | **1.543 kg** | — | **1,00** / 0,41 / 42 kN |
| **Cajón 80 × 250, t 35** | **1.632 kg** | — | **0,92** / 0,30 / 31 kN |
| Cajón 80 × 300, t 30 | 1.640 kg | — | 0,91 / 0,23 / 27 kN |

Salidas: `resultados/a2_marcos_def_malla80.jsonl` y `resultados/a2_marcos_B_malla80.jsonl`. En el retorno los pernos piden ≤ 4 kN (B 12 kN) con cualquier marco.

### 5.3 Marco que haría falta y masa

| | Por defecto (h = 105) | Interfaz B (h = 160) |
|---|---|---|
| Pletina de canto (marco abierto) | **420 × 30**: FU 0,99, ≈ **1,0 t** | **550 × 40**: FU 0,95, ≈ **1,8 t** |
| Con la altura limitada bajo la cara superior de la mesa (210 mm por defecto, 265 con B, sobre la plancha) | **Cajón 80 × 200, t 25**: FU 1,00, ≈ **1,0 t** | **Cajón 80 × 250, t 35**: FU 0,92, ≈ 1,6 t (u 80 × 200, t 40: FU 1,00, 1,5 t) |
| Masa neta de A2 | ≈ +1,0 t (el marco reemplaza el perimetral de 45 × 10, de 30 kg) más los 2 pernos y sus placas | ≈ +1,6 a 1,8 t |

Condiciones y consecuencias que hay que confirmar antes de adoptarlo:

- **Altura.** La pletina de 420 mm (550 con B) sobresale unos 210 mm (285) sobre la cara superior de la mesa. Si la carga puede volar sobre el borde de la mesa, que es una hipótesis a confirmar con el mandante, la pletina no sirve y queda el cajón, que no sobresale de la cara superior de la mesa.
- **Ancho.** Junto a cada borde hay una franja libre de unos 80 mm (§2: cuerpo del cilindro a 91 mm, placas-guía a 90 mm). El cajón de 80 mm la ocupa entera y queda a unos 10 mm del barrido del cilindro y de las placas-guía. Las pletinas de 30–40 mm entran con holgura.
- **Soportes E.** Las paredes traseras están a 16 mm del borde: ningún marco de 30–80 mm pasa por fuera de ellas.
  - El marco se interrumpe y se une con CJP a las paredes traseras, que pasan a ser parte del marco. La cartela del modelo es esa unión rígida, hasta 280 mm.
  - El soporte E tiene que tomar el momento del marco en ese punto: 84–141 kN·m por defecto con los marcos que cumplen, más que los 47 kN·m del cilindro. **Esto no se verificó**: hay que rediseñar las paredes traseras (espesor, unión con el marco) y revisar sus CJP con la base.
  - Se pierde el acceso exterior a las CJP pared–base (§2.1).
- **Comparación de masas.** A2 pesa algo más que el cajón sin anclaje (733 kg, que no cumple con la mesa cargada ni con B) y menos que la plancha de 64 mm (+2,4 t, que con B tampoco cumple). Es la única opción estudiada que cumple también con la interfaz B, a costa de los pernos.

### 5.4 Requisitos mínimos de anclaje a especificar a terceros

Los datos de la losa no existen en el proyecto: f'c, espesor, armadura, fisuración, distancia de los pernos a bordes, juntas y aberturas. Todo lo que sigue es **orientativo** y lo tiene que verificar quien diseñe el anclaje con esos datos (`anclaje_aci.py`, salida en `resultados/a2_anclaje_aci_fc25.txt`).

| Requisito | Por defecto | Interfaz B | Nota |
|---|---|---|---|
| Ubicación | 1 perno en cada esquina libre: (1.200; 1.200) y (−1.200; −1.200), a 80 mm de los dos bordes de la base | ídem | Las esquinas que suben en el empuje con los ojales E en (1.134; −1.134) y (−1.134; 1.134). Fuera del barrido |
| Fuerza característica por perno (a calado, sin factor) | **N_k = 48 kN de tracción** | **N_k = 75 kN** | Envolvente de los marcos ≥ 200×20: con el marco que cumple baja a 19–36 kN (B 29–42), pero se especifica la envolvente para no atar el anclaje al marco final. Retorno ≤ 4 kN (B 12) |
| Corte por perno | ≈ 0 (hipótesis) | ≈ 0 | En planta las fuerzas se cierran dentro de la tornamesa (§1.2): la losa no toma corte. Si el mandante quiere un corte accidental (por ejemplo, para el montaje), hay que declararlo |
| Fuerza de diseño | **N_ua = 1,6·N_k = 77 kN** | **N_ua = 120 kN** | Hipótesis: la fuerza a calado se toma como carga variable L (ACI 318-19 §5.3.1, U = 1,2D + 1,6L) y no se descuenta el peso propio |
| Tipo sugerido | **Químico (adhesivo)** calificado según **ACI 355.4** para hormigón fisurado y tracción sostenida; si la losa es nueva, perno hormigonado con cabeza | ídem | Frente al expansivo (ACI 355.2): la tracción se repite en cada calado y, con menos fuerza, en la operación normal. El adhesivo no depende de la precarga ni de la expansión, admite menores distancias a los bordes según su informe y se coloca después de posicionar la base |
| Varilla | **M20, ISO 898-1 8.8** (por acero alcanzaría M16: φN_sa = 0,75·A_se·f_uta = 94 kN ≥ 77) | **M24, 8.8** (φN_sa = 212 kN; M20 da 147) | ACI 318-19 §17.6.1 y Tabla 17.5.3 (φ = 0,75, acero dúctil). El diámetro mayor que el estrictamente necesario da área de adherencia |
| Profundidad efectiva | **h_ef ≥ 230–250 mm** | **h_ef ≥ 310 mm** | Arrancamiento del hormigón, perno aislado y lejos de los bordes: φ·k_c·λ·√f'c·h_ef^1,5 ≥ N_ua con k_c = 7 (posinstalado; 10 si se hormigona), φ = 0,65 (condición B, categoría 1), **f'c = 25 MPa y hormigón fisurado (hipótesis)**. Con f'c = 30 MPa: 212 y 285 mm (ACI 318-19 §17.6.2) |
| Adherencia | τ_cr ≥ 7,6 MPa (M20, h_ef 250, fisurado) | τ_cr ≥ 7,9 MPa (M24, h_ef 310) | φ·τ_cr·π·d·h_ef ≥ N_ua (§17.6.5). Con los valores mínimos de la Tabla 17.6.5.2.5 (1,4–2,1 MPa fisurado) no hay solución práctica: el producto tiene que tener informe de evaluación (ACI 355.4) con su τ_cr |
| Distancias | Al borde de la losa, a juntas y a aberturas: ≥ 1,5·h_ef ≈ 375 mm (B 465) para no reducir el cono, y no menos que lo que pida el informe del producto. Espesor de la losa del orden de h_ef + 100 mm o más (§17.9 e informe del producto) | ídem | Si los pernos quedan más cerca de un borde, la capacidad baja (ψ_ed,N, A_Nc) y hay que rehacer el cálculo |
| Fatiga | La tracción se repite: con la mesa cargada el perno lleva 32 kN a calado con el marco 200×20, y menos en la operación normal | ídem | ACI 318-19 cap. 17 no cubre cargas predominantemente de fatiga de alto ciclo ni de impacto (§17.1). Si el número de ciclos de calado o de operación con tracción es alto, hay que usar un producto con datos de fatiga (por ejemplo, EN 1992-4 con su evaluación técnica) |
| Pieza de la base | Placa de anclaje en la esquina del marco (arandela de placa y agujero sobredimensionado según el producto). La tracción entra al marco por la esquina | ídem | A verificar con el marco elegido |

En resumen, a terceros se les especifica: **2 anclajes, uno en cada esquina libre, de 48 kN de tracción característica a calado (75 kN con la interfaz B), sin corte, con tracción repetida, en hormigón fisurado de f'c y espesor a informar.** Como orientación: químico M20 8.8 con h_ef ≈ 250 mm (M24 con h_ef ≈ 310 mm con B). El diseño final del anclaje (ACI 318-19 cap. 17, o EN 1992-4) lo hace quien tenga los datos de la losa.

## Reproducción

```
node docs/qa/plancha_base_soporte_E/exportar.js '{}' /tmp/e_def.json
node docs/qa/plancha_base_soporte_E/exportar.js '{"opt_uhmw":1}' /tmp/e_B.json
python3 docs/qa/plancha_base_soporte_E/casos.py /tmp/e_def.json 40 placa         # tabla 1.4 (≈ 10 min)
python3 docs/qa/plancha_base_soporte_E/casos.py /tmp/e_def.json 80 anclajes      # A1 y A2
python3 docs/qa/plancha_base_soporte_E/opciones.py /tmp/e_def.json 80 placa,B52,B64,C300x25,Cbox250,D   # tabla 2.1
python3 docs/qa/plancha_base_soporte_E/a2.py /tmp/e_def.json 80 C200x20,C300x25,C420x30,K200+80x25   # tabla 5.2 (C: pletina h×t; T<h>+<b>x<t>; K<h>+<b>x<t>: cajón)
python3 docs/qa/plancha_base_soporte_E/anclaje_aci.py 25                                                # §5.4 (f'c en MPa, hipótesis)
```

El modo guiado (drive_mode = 1) tiene el mismo mecanismo con valores menores: `docs/qa/plancha_base_modo_guiado.md`.

Las salidas usadas están en `docs/qa/plancha_base_soporte_E/resultados/`. El verificador independiente (`tests/indep_pivotado.py` §5c) replica con código propio la base completa en malla de 80 mm (mesa vacía: queda apoyada en los pies; mesa cargada: pocos mm), la fuerza de esquina M/B, el τ de torsión y el estado global.
