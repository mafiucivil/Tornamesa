# Referencia KIET "液压转盘400T" (KIET-1024-REF-TT-400T-00, V01): análisis

Fuentes: plano de conjunto KIET (PDF vectorial, 1 lámina), manual "Electric Hydraulic Pump for Hydro-Turn Table" (25 p.) y 3 fotos del equipo del cliente. Fecha del análisis: 30-10-2026.

Método: las cotas no indicadas en el plano se midieron sobre el vector del PDF. Escala calibrada con el contorno de 2200 mm y el anillo de Ø1840 (5,292 mm/pt; error estimado ±2 mm). Los valores medidos van marcados con (m).

## 1. Datos declarados

| Dato | Plano | Manual | Observación |
|---|---|---|---|
| Capacidad | 400 t | 500 t ("total assembly weight") | **Inconsistente**: confirmar con el cliente |
| Diámetro de mesa | Ø2000 | Ø2000 / Ø1840 | |
| Dimensiones | 2200 × 2200 × 200 | idem | |
| Peso propio | ≈ 2158 kg | 2158 kg | TT300-B: ≈ 5354 kg |
| Giro | izquierda/derecha, 360° | Cambio de sentido reubicando el gato | Igual que TT300-B |
| Cilindros | — | 2 × Ø85/Ø55, 0–70 MPa, carrera 235, "2 × 40 T" | No extender a fondo de carrera |
| Bomba | — | 70 MPa, 1,8 L/min, 2,2 kW, 55 L, válvula J 4 vías con bloqueo hidráulico, puerto A 0–70 MPa, puerto B 20 MPa | El manual también dice "315 bar" en seguridad (texto genérico) |

## 2. Geometría medida (m)

| Elemento | Valor | Nota |
|---|---|---|
| Pasadores de empuje | **28 × Ø50**, en R950 (PCD 1900), paso 12,857° | Ajuste de las 4 primeras posiciones en alzado: R = 950,1–950,3 |
| Altura libre de pasadores | z 65 → 178 (≈ 113 mm) | Entre faldón inferior y anillo superior |
| Anillo superior | Ø2000, z ≈ 178–197 (≈ 20 mm) | Agujeros sobre cada pasador: 14 × Ø20 en R≈955 y 14 roscados en R900, alternados |
| Cubierta | Plancha diamantada en 2 mitades, empalme diametral con 3 pares de pernos (R280/520/760) | Fotos: plancha estriada sobre el anillo |
| Faldón inferior | Ø≈2067, z ≈ 65–76 | Interpretación a confirmar |
| Base | Bandeja 2200 × 2200, plancha inferior ≈ 20, nivel superior z ≈ 65 | Cajas de cilindro rebajadas (z 28–48) |
| Ojal de cilindro (base) | R1390 a 135° y 315° (esquinas diagonales), rótula Ø90 ext. | Pasador vertical |
| Uña de empuje | Pivotada en el extremo del vástago, punta con chaflán | Sin carro ni guía; libertad radial por giro de la uña |
| Ojal–pasador de vástago | **493 retraído / 728 extendido** (Δ = 235 = carrera) | Las dos posiciones dibujadas confirman la carrera |
| Brazo de la fuerza | **869 mm** al inicio de carrera, ≈ 975 al final | Mínimo al tomar el pasador |
| Cuerda entre pasadores | 212,7 mm → libre 22,3 mm por carrera | Un pasador por carrera, 28 carreras por vuelta |
| Puntos de izaje | 4 cáncamos giratorios | |

## 3. Capacidad del accionamiento (2 × 397 kN a 700 bar, brazo 0,869 m)

| Carga | μ_max r 0,672 | μ_max r 0,80 | FS nominal (μ 0,15; r 0,672) | FS criterio TT300-B (μ 0,20; r 0,80) |
|---|---|---|---|---|
| 300 t | 0,348 | 0,293 | 2,32 | 1,46 |
| 400 t | 0,261 | 0,220 | 1,74 | 1,10 |
| 500 t | 0,209 | 0,176 | 1,39 | **0,88** |

Sin pérdidas en el cilindro; con η = 0,95 los FS bajan 5 %. Con 400 t el equipo cumple en condición nominal; con 500 t no cumple el criterio de diseño de TT300-B.

## 4. Verificación preliminar de los pasadores Ø50 (fuerza de calado 397 kN, carga a z ≈ 106)

| Modelo | M (kN·m) | σ (MPa) |
|---|---|---|
| Biapoyado, L 113 | 10,4 | 843 |
| Biempotrado | 6,59 | 537 |
| Corte (biempotrado) | V = 278 kN | τ = 189 |

Con 400 t y grasa nominal (F ≈ 228 kN por cilindro): σ ≈ 308 MPa biempotrado. Con BTH-1 Cat. B (Nd 3,0) el pasador Ø50 no cumple a calado ni con aceros QT. Material y fijación de los pasadores no indicados: confirmar.

## 5. Lecciones para el diseño nuevo

| Característica KIET | Efecto | Hallazgo TT300-B que resuelve |
|---|---|---|
| Cilindro pivotado en la base + uña pivotada en el vástago | Elimina carro y guía (K = 1,24 → ≈ 1,0); la uña acompaña el arco del pasador | C2, M3, M4 |
| Carrera 235 con 22 mm libres para cuerda 213 | Margen explícito | C3 |
| Paso 12,86° (28 pasadores) | Menos ciclos que TT300-B (36) | — |
| Altura 200, peso 2158 kg | Mesa más baja y liviana | — |
| Cubierta en 2 mitades apernadas | Acceso a la estructura interna | — |
| Pasadores Ø50 con luz 113 | Insuficientes con el criterio de este proyecto | Requiere Ø mayor o luz menor |
