# Tornamesa hidráulica TT300-C

Software de cálculo y verificación de una tornamesa de 300 tf para equipos sobredimensionados, con accionamiento por 2 cilindros pivotados y uña sobre pasadores.

## Herramienta

Abrir `dist/TT300-C_Verificacion.html` en cualquier navegador (un solo archivo, sin conexión). Permite editar todos los parámetros y muestra en vivo:
- si el sistema **gira** (FS, presiones, carrera, casos de fricción);
- si la **estructura cumple** (AISC 360-22, ASME BTH-1 Cat. B, AWS D1.1), con FEA propio de la mesa y del izaje;
- la **masa** y un optimizador que la minimiza manteniendo todas las verificaciones;
- los agentes deterministas: validador de entradas, auditor normativo, revisor cruzado y escenarios.
- el **paquete de dibujo**: marcando «Exportar paquete de dibujo» en el panel izquierdo se descarga un ZIP con 5 láminas DXF (planta de la base, planta de la mesa, sección radial con la interfaz A/B/C elegida, pivote y collar, orejas de izaje), las mismas en SVG y en una página de impresión (PDF desde el navegador), la lista de materiales (CSV) y el JSON de diseño para el generador completo. Lo que el núcleo no define se rotula «A DEFINIR».

## Estructura

| Carpeta | Contenido |
|---|---|
| `packages/core/` | Núcleo: `fea.js` (MITC4, Q4) y `tt300c.js` (cinemática, accionamiento, masas, verificaciones) |
| `packages/agents/` | Agentes deterministas del producto |
| `packages/web/` | Interfaz (`shell.html`, `ui.js`) y exportación del paquete de dibujo (`planos_export.js`) |
| `tools/build_tt300c.py` | Arma el HTML autónomo en `dist/` |
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
