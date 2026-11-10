# Plancha base: base de 20 mm con inserto de esquina bajo los soportes (10-11-2026)

Responde a la decisión del mandante del 10-11-2026, tomada tras la verificación independiente de la plancha base (`tests/indep_plancha_base_E.py`, 8537513). Sigue a `docs/qa/plancha_base_soporte_E.md` y a `docs/qa/plancha_base_modo_guiado.md`.

## 1. Decisión y criterio

| Punto | Adoptado |
|---|---|
| Base | `t_base` 18 → **20 mm** en toda la planta |
| Refuerzo | Un **inserto** de plancha más gruesa bajo cada soporte del cilindro: modo 2, un inserto bajo cada soporte del ojal E (2 esquinas diagonales); modo 1, uno bajo cada ménsula del ojal trasero (`n_br` = 4 esquinas). Va al ras por debajo con la base, con la cara superior más alta, y se une con CJP a tope con transición 1:2,5 en la cara superior |
| Flexión | F_b = **1,25·Fy/Nd** (ASME BTH-1-2020 §3-2.3.4, flexión respecto del eje menor de secciones rectangulares macizas; número de ecuación: verificar), Nd = 3,0 |
| Corte | F_v = Fy/(Nd·√3) (BTH-1-2020 §3-2.3.6) |
| Tensión evaluada | σ_vM en la cara a **más de 100 mm de la huella rígida del soporte**. Es el criterio de la verificación independiente: fuera de la singularidad de la esquina rígida. El pico se informa aparte |
| Casos de diseño | Mesa cargada a la fuerza nominal, de diseño y de calado (445 kN a 700 bar), atasco del retorno con la mesa cargada (F_ret = A_anular·p_ret) y mesa vacía en servicio |
| Mesa vacía en servicio | F = 1,25·máx(F_dis; F_borde; F_cont)·W_d/N. Cubre el μ de diseño y el contaminado y el contacto en el borde. El factor 1,25 es el FS de giro del proyecto (F_calado/F_diseño ≥ 1,25), usado como margen de arranque. Parámetro `ins_fsv` |
| **Excluido** | Atasco a presión de alivio con la mesa vacía. Queda como **limitación de uso**: «No operar el accionamiento a presión de alivio con la mesa sin carga; ante un atasco sin carga, detener y liberar». Se exporta en `verdict.limitaciones_uso[]` y en `inserto.limitaciones_uso[]`, y figura en una fila informativa |
| FU | Objetivo interno ≤ 0,90 (sobre ese valor la fila queda en advertencia); límite 1,0 |

## 2. Geometría del inserto (marco canónico de la esquina (+B/2; −B/2))

- **Triángulo** X − Y ≥ c, con la hipotenusa a D/2 + gap del centro.
- **Muescas rectangulares** que dejan libres, con holgura de diseño `clr`, las piezas que apoyan en la base:
  - Modo 2: las dos placas-guía del cilindro y la trayectoria del cubo y pasador Q, que baja hasta t_base + 2.
  - Modo 1: la banda del accionamiento guiado (bancada, prolongación, pórticos, patín).
  - Muesca del lado X: {X ≥ a, Y ≥ b}. Muesca del lado Y: {X ≤ a′, Y ≤ b′}.
- **Transición** 1:2,5 en el inserto a lo largo de los bordes interiores. El espesor pleno empieza a 2,5·Δ del contorno (polígono `esquinas_espesor_pleno`). Los bordes que caen sobre el borde de la base no llevan junta.
- **Rebaje local** de la cara superior bajo el barrido de las piezas móviles que no dejan 5 mm sobre el espesor pleno, hasta z = z_pieza − 5. Es la envolvente convexa del barrido de cada pieza y sentido.
- **Espesor**: el menor comercial de {25, 30, …, 80, 90, 100, 110, 120} mm que cumple, en orden:
  1. FU ≤ 0,90 en todos los casos;
  2. holgura vertical ≥ 5 mm;
  3. tapa inferior del ojal E (modo 2) o suplemento de la ménsula (modo 1) sobre el inserto.

  Si ningún espesor llega a 0,90, se toma el primero con FU ≤ 1 (advertencia).
- **Variantes calibradas**, en orden de preferencia: gap 30 / clr 10 y gap 10 / clr 8 en el modo 2; gap 10 / clr 8 en el modo 1. Manda la primera variante que cumple.
- Sobre el inserto se sueldan las paredes y los muñones del soporte E (modo 2) o las mejillas y el suplemento de la ménsula (modo 1), Δ más cortos. También la oreja de izaje de la diagonal. El marco perimetral se interrumpe a lo largo de los catetos y hasta 50 mm más allá de su extremo.

## 3. Modelo del núcleo (calibrado) y FEA del verificador

El núcleo JS no resuelve contacto unilateral y `fea.js` no se tocó. Por eso el núcleo usa σ = κ·M·S(t_base; t_inserto), con M = F·h:

- **h** es la altura del eje sobre la cara superior de la base: 105 mm por defecto y 160 mm con la interfaz B. El roce de la mesa entra a z = t_base.
- **S = σ/M** (MPa por kN·m) se tabula desde la FEA de Mindlin de la base completa: mesa cargada como cuerpo rígido con contacto unilateral, losa unilateral, dos soportes rígidos con M₂ = −M₁, inserto con su transición, malla de 40 mm. La grilla es t_base ∈ {16, 20, 25} y t_inserto 35–110 mm. La tensión es lineal en M (se verificó con F = 207, 327 y 445 kN y con h = 105 y 160 mm: diferencias < 0,5 %).
- **κ = 1,03** cubre la interpolación y la banda de ψ (los dos extremos de la banda dan lo mismo).
- **Retorno**: S_ret de la FEA. El talón queda en la esquina libre, sin la mesa detrás. Vale 13,6 MPa/(kN·m) en el modo 2 con gap 30, 13,0 con gap 10 y 11,4 en el modo 1. Es casi independiente del espesor.
- **Mesa vacía**: factor 1,8 sobre S. La FEA con la mesa vacía hasta 30 kN da 1,3–1,73.
- **Rebaje**: S(t) + φ·(S(t_r) − S(t)) con φ = 0,5. La FEA da 0,31 (60/55) y 0,35 (90/85).

Malla: con 20 mm, la tensión junto al borde de la mesa rígida sube ≈ 6 % respecto de la de 40 mm. Es una línea singular del modelo, porque la mesa real no es rígida. El criterio de referencia es el de la verificación: malla de 40 y más de 100 mm de la huella del soporte.

El verificador independiente (`tests/indep_plancha_base_E.py` §4) rearma el espesor desde los polígonos exportados (contorno, espesor pleno y rebaje). Corre la FEA en los cuatro modelos (por defecto, B, guiado y guiado B) con los cinco casos. Exige que el FU de la FEA sea ≤ 1 y que no supere al del núcleo en más del 2 %. El modo `--rapido`, que entra a `npm test`, verifica la geometría, las holguras, las masas, los casos, el criterio, la limitación y el estado global.

## 4. Resultados

| Modelo | Variante | Inserto | Catetos (mm) | Rebaje | FU núcleo (nom / dis / calado / retorno / vacía) | Masa por inserto |
|---|---|---|---|---|---|---|
| Por defecto (h = 105) | gap 30, clr 10 | **60 mm** (Δ 40) | 554 / 554 | z 55 bajo el cuerpo del cilindro (5 mm) | 0,414 / 0,653 / **0,889** / 0,664 / 0,009 | 83,0 kg × 2 |
| Interfaz B (h = 160) | gap 10, clr 8 | **90 mm** (Δ 70) | 556 / 556 | no | 0,245 / 0,724 / **0,985** / 0,967 / 0,012 (advertencia) | 138,9 kg × 2 |
| Interfaces A y C (h = 135) | gap 30, clr 10 | 90 mm (Δ 70) | 554 / 554 | z 85 (5 mm) | 0,412 / 0,649 / 0,882 / 0,854 / 0,011 | 130,6 kg × 2 |
| Guiado (h = 105) | gap 10, clr 8 | **50 mm** (Δ 30) | 589 / 1.132 | no | 0,376 / 0,593 / **0,821** / 0,557 / 0,008 | 110,6 kg × 4 |
| Guiado B (h = 160) | gap 10, clr 8 | **65 mm** (Δ 45) | 589 / 1.132 | no | 0,219 / 0,646 / **0,893** / 0,848 / 0,011 | 156,6 kg × 4 |

Con la interfaz B, la plancha de 20 mm bajo el borde de la mesa gobierna y satura: el FU del núcleo es 0,98 con 90–120 mm. El objetivo interno de 0,90 no se alcanza con base de 20 mm. Queda en **advertencia** (FU ≤ 1), con el registro de la decisión pendiente del mandante: aceptar la advertencia o una base local mayor para B. Por defecto y en el modo guiado se cumple ≤ 0,90.

Holguras (mínimo del proyecto: 5 mm):

| Modelo | En planta a placas-guía, cubo de Q o banda | Vertical (pieza) | A la mesa | Asiento |
|---|---|---|---|---|
| Por defecto | 10 mm (placa-guía 1, antihoraria) | **5,0 mm** (cuerpo del cilindro sobre el rebaje a z 55; con 55 mm sin rebaje también 5,0, pero FU 0,92) | 30 mm | tapa inferior del ojal E a z 69 ≥ 60 |
| B | 8 mm | 25 mm (cuerpo a z 115) | 10 mm | 124 ≥ 90 |
| Guiado | 8 mm (banda del accionamiento) | 10 mm (cuerpo a z 60) | 10 mm | suplemento 73 ≥ 50 |
| Guiado B | 8 mm | 50 mm | 10 mm | 128 ≥ 65 |

El bloque-uña (z 55 por defecto) pasa solo sobre la transición, con ≥ 5 mm. Las placas-guía y el seguidor Q quedan fuera del inserto en planta, por las muescas.

FEA del verificador independiente frente al núcleo (malla 40; σ a más de 100 mm de la huella rígida; FU = σ/(1,25·Fy/Nd); `resultados/verificador_completo.log`):

| Modelo | Caso | FEA | Núcleo |
|---|---|---|---|
| Por defecto | nominal / diseño / calado / retorno / vacía | 0,395 / 0,624 / **0,852** / 0,636 / 0,001 | 0,414 / 0,653 / **0,889** / 0,664 / 0,009 |
| Interfaz B | ídem | 0,237 / 0,703 / **0,956** / 0,946 / 0,002 | 0,245 / 0,724 / **0,985** / 0,967 / 0,012 |
| Guiado | ídem | 0,360 / 0,573 / **0,797** / 0,475 / 0,001 | 0,376 / 0,593 / **0,821** / 0,557 / 0,008 |
| Guiado B | ídem | 0,208 / 0,623 / **0,865** / 0,728 / 0,002 | 0,219 / 0,646 / **0,893** / 0,848 / 0,011 |
| Base de 20 mm sin inserto | calado | 3,25 | — |
| KIET medido (20 + 20 en la esquina, como referencia) | calado | 1,20 | — |

El modelo calibrado del núcleo queda del lado seguro en todos los casos.

## 5. Masas y alturas (por defecto)

| Concepto | Antes | Ahora |
|---|---|---|
| t_base | 18 mm | 20 mm |
| Altura total sobre el piso | 228 mm | 230 mm |
| Base (plancha, collar y orejas) | 958,2 kg | 1.060,9 kg |
| Insertos | — | +166,0 kg (2 × 83,0) |
| Paredes del soporte sobre el inserto | — | −14,5 kg |
| Marco interrumpido a lo largo de los catetos | — | −2,5 kg |
| Masa total | 2.779,8 kg | 3.031,7 kg (+251,9) |

La masa de los insertos se contabiliza con el soporte del cilindro (`R.m.brackets`, una pieza por inserto) para que la lista de materiales la incluya; `R.m.insertos` la informa aparte. Interfaz B: +352,8 kg. Modo guiado: +483,1 kg (4 insertos); guiado con B: +649,0 kg. Todo lo que depende de t_base se recalcula: alturas, pivote, interfaz, masas, izaje, térmica, alcance, enganche de los tornillos y pasadores de la placa-guía, y holguras.

## 6. Reproducción

```
node docs/qa/plancha_base_inserto/geo.js > g_def.json          # obstáculos en planta (placas, partes móviles, soportes)
node tools/export_design.js p2.json > d2.json                  # p2.json = {"drive_mode": 2}
python3 docs/qa/plancha_base_inserto/calib.py g_def.json d2.json cal.jsonl 30 10    # tabla S del modo 2, gap 30 (≈ 4 min con 4 núcleos)
python3 docs/qa/plancha_base_inserto/calib.py g_def.json d2.json cal.jsonl 10 8     # ídem, gap 10
python3 docs/qa/plancha_base_inserto/gcalib.py gcal.jsonl 10 8                      # modo guiado
python3 docs/qa/plancha_base_inserto/extra.py g_def.json d2.json 20 105 55,80       # retorno y mesa vacía
python3 docs/qa/plancha_base_inserto/pocket.py 60 55 30 10 105                      # rebaje bajo el barrido del cuerpo
python3 -I tests/indep_plancha_base_E.py                                            # verificación independiente completa
```

Las salidas usadas están en `docs/qa/plancha_base_inserto/resultados/`.
