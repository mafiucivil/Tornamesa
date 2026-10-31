# Tornamesa hidráulica TT300-C

Software de cálculo y verificación de una tornamesa de 300 tf para equipos sobredimensionados, con accionamiento por 2 cilindros pivotados y uña sobre pasadores.

## Herramienta

Abrir `dist/TT300-C_Verificacion.html` en cualquier navegador (un solo archivo, sin conexión). Permite editar todos los parámetros y muestra en vivo:
- si el sistema **gira** (FS, presiones, carrera, casos de fricción);
- si la **estructura cumple** (AISC 360-22, ASME BTH-1 Cat. B, AWS D1.1), con FEA propio de la mesa y del izaje;
- la **masa** y un optimizador que la minimiza manteniendo todas las verificaciones;
- los agentes deterministas: validador de entradas, auditor normativo, revisor cruzado y escenarios.

## Estructura

| Carpeta | Contenido |
|---|---|
| `packages/core/` | Núcleo: `fea.js` (MITC4, Q4) y `tt300c.js` (cinemática, accionamiento, masas, verificaciones) |
| `packages/agents/` | Agentes deterministas del producto |
| `packages/web/` | Interfaz (`shell.html`, `ui.js`) |
| `tools/build_tt300c.py` | Arma el HTML autónomo en `dist/` |
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
