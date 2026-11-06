"""Fachada de las láminas de pieza: registra y reexporta lo que usan generar_paquete y hojas_con. Las láminas viven en pie_*.py (se importan en orden de lámina)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *
import pie_a
from pie_a import *
import pie_b
from pie_b import *
import pie_c
from pie_c import *
