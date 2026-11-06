"""Compatibilidad: `npm run planos` genera el paquete completo de planos de fabricación (ver cad/generar_paquete.py).
Uso: python3 cad/planos_tt300c.py [design.json] [--out DIR] [--entrega DIR]"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from generar_paquete import main

if __name__ == "__main__":
    main()
