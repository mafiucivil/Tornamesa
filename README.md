# Tornamesa hidráulica TT300-C

Software de cálculo y verificación de una tornamesa de 300 tf para equipos sobredimensionados, con accionamiento por 2 cilindros pivotados y uña sobre pasadores.

## Herramienta

Abrir `Tornamesa_v1.2.html` (raíz del repositorio) en cualquier navegador (un solo archivo, sin conexión). Es el archivo principal; la versión sale del archivo `VERSION` y `python3 tools/build_tt300c.py` lo regenera con el número nuevo (borra el de la versión anterior; queda en el historial de git). Arriba del formulario se elige la **alternativa de interfaz de giro** (base acero-acero, A, B, C1, C2 o C3); cubierta de madera y fijación pegada se activan en el formulario. Permite editar todos los parámetros y muestra en vivo:
- si el sistema **gira** (FS, presiones, carrera, casos de fricción);
- si la **estructura cumple** (AISC 360-22, ASME BTH-1 Cat. B, AWS D1.1), con FEA propio de la mesa y del izaje;
- la **masa** y un optimizador que la minimiza manteniendo todas las verificaciones;
- los agentes deterministas: validador de entradas, auditor normativo, revisor cruzado y escenarios.
- la pestaña **Temperatura** (escenario aparte, tornamesa expuesta al sol): con T_serv (botón «Escenario solar 80 °C»: 80 °C y gradiente de 15 K) evalúa la geometría dimensionada a 20 °C, congelada, con las capacidades reducidas a la temperatura, por alternativa (base, A, B, C1–C3, con o sin madera): FS del giro y FU de la estructura a 20 °C frente a T, verificaciones que más empeoran y que cambian de estado, juntas de dilatación, holguras de pivote y buje, gradiente plancha superior–inferior, grasa, UHMW, madera y sensibilidades (μ, Fy × 0,92, k_p/k_E del UHMW). **Alcance** (`term_alcance`): por defecto 1 = el sistema de placas y disco (plancha base, mesa, interfaz con topes y juntas, madera, pivote y collar); los pistones, el aceite atrapado, las válvulas de alivio térmico, los sellos, la viscosidad, la bomba y el accionamiento mecánico (uña–pasador, patín–guía, pasadores de empuje) quedan **fuera de alcance**: se calculan y se informan en una sección aparte, sin afectar el veredicto; `term_alcance` = 2 los reactiva y reproduce el escenario anterior. Datos y niveles de confianza A/B/C en `docs/normas/registro.md`, sección «Temperatura (exposición solar, 80 °C)»; API `TT.thermal(P, {T:[20,40,60,80,100]})`, también bajo la clave `termica` del JSON de diseño.
- la pestaña **Tapones (C)** (cantidad real de tapones de grafito de la alternativa C): `N_real` = centros de la malla escalonada (paso p, fila alterna p·√3/2) que caben en el área útil (corona R_i…R_o menos la franja de borde `bz_edge`, la muesca del tope, los tornillos de posición y las ranuras de engrase), `f_g,real = N_real·π·d²/4/A_contacto` frente a la ideal `π·d²/(2√3·p²)`; `bz_fg_modo` (1 = el cálculo usa lo real: masa del bronce, q_neto, PV, desgaste, lubricación; 0 = ideal) y el criterio de lubricación `bz_fg_min` (supuesto C, aviso). Análisis de sensibilidad ideal frente a real, barridos de f_g, de (Ø, paso), de `bz_edge` y de los tornillos, y patrón recomendado; API `TT.tapones(P)`, claves `R.ifc.Nreal/fgReal/fgIdeal/cobGrafito` e `interfazGeom.tapones` en los dos exportadores
- el **paquete de dibujo**: marcando «Exportar paquete de dibujo» en el panel izquierdo se descarga un ZIP con 5 láminas DXF (planta de la base, planta de la mesa, sección radial con la interfaz A/B/C elegida, pivote y collar, orejas de izaje), las mismas en SVG y en una página de impresión (PDF desde el navegador), la lista de materiales (CSV) y el JSON de diseño para el generador completo. Lo que el núcleo no define se rotula «A DEFINIR».

## Estructura

| Carpeta | Contenido |
|---|---|
| `packages/core/` | Núcleo: `fea.js` (MITC4, Q4) y `tt300c.js` (cinemática, accionamiento, masas, verificaciones) |
| `packages/agents/` | Agentes deterministas del producto |
| `packages/web/` | Interfaz (`shell.html`, `ui.js`) y exportación del paquete de dibujo (`planos_export.js`) |
| `tools/build_tt300c.py` | Arma el HTML autónomo `Tornamesa_v<VERSION>.html` en la raíz |
| `tools/export_design.js` | Exporta el diseño (parámetros + resultados) para los planos |
| `cad/planos_tt300c.py` | Genera las 6 láminas A1 (PDF + DXF) en `cad/out/` desde el JSON exportado |
| `tests/` | Tests Node, golden file y verificación independiente en Python |
| `.claude/agents/` | Subagentes de desarrollo |
| `tt300/`, `tt/` | Proyecto anterior TT300-B (carro guiado) y TT500 |
| `docs/` | Especificación, registro normativo y análisis de la referencia KIET |

## Comandos

```bash
npm test
```

```bash
npm run build
```

```bash
npm run planos
```

Para generar planos con parámetros propios: exportar el JSON desde la herramienta HTML («Exportar JSON») y ejecutar `node tools/export_design.js parametros.json > cad/out/TT300-C_design.json && python3 cad/planos_tt300c.py`. El generador se niega a emitir si el diseño no gira o la estructura no cumple.

Requisitos de los planos: Python 3 con `ezdxf` y `pymupdf` (`pip install ezdxf pymupdf`).
