# Revisión exhaustiva de planos Rev. C (primera vuelta)

Juegos revisados: 8 casos (base, A, AF2, B, C1, C2, C3, W) generados desde el commit 2fe7950 con `cad/generar_paquete.py`; todos los controles automáticos en 0.
Revisores independientes del generador de planos; solo hallazgos, sin correcciones.

| Frente | Alcance | Críticos | Mayores | Menores | Pendiente accionamiento |
|---|---|---|---|---|---|
| A | Consistencia entre láminas, GEN y CON | 4 | 25 | 20 | lista aparte |
| B | Piezas BAS/MES/PIV/IZA | 2 | 38 | 16 | 2 |
| C | Variantes INT/MAD/CON-012/CON-030 | 3 | 22 | 17 | — |

A-02 y B-01 son el mismo hallazgo (ajuste del pivote en el buje).
Excluidas en esta vuelta: ACC-*, CON-010, CON-018 y pasos de montaje del accionamiento (se rediseñan con la leva de reenganche y el modo pivotado).
