"""Generador local de planos TT300-C (Modo 2 del módulo «Planos» de la herramienta HTML).

Uso:  python tools/servidor_planos.py [--puerto 8765] [--no-abrir]
      (en Windows: Generar_planos_Tornamesa.bat, después de instalar una vez con Instalar_generador_planos.bat)

Sirve la raíz del repositorio en http://127.0.0.1:8765/ (solo esta máquina), abre la herramienta Tornamesa_v<versión>.html y expone:
  GET  /api/ping              → {"ok": true, "version", "python", "trabajo": último trabajo o null}
  POST /api/generar           → recibe el JSON de diseño (el mismo esquema que `node tools/export_design.js`, botón «JSON de diseño»
                                 o «Generar planos» de la herramienta), verifica su estructura y lanza en segundo plano
                                   python cad/generar_paquete.py <design.json> --out <tmp> --entrega salidas/<fecha-hora>_<alternativa>/
                                 (vía tools/lanzar_generador.py) y luego tools/indice_planos.py sobre esa carpeta.
  GET  /api/estado?id=ID      → estado del trabajo: en_curso | listo | error, fase, progreso (estimado), registro, mensaje de error
                                 tal cual lo imprime el generador, carpeta y el índice de planos (enlaces relativos a la raíz).
Responde CORS a la página abierta como archivo (origen «null») y a 127.0.0.1/localhost. Solo biblioteca estándar."""
import argparse
import collections
import datetime
import http.server
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parents[1]
SALIDAS = ROOT / "salidas"
REF_DESIGN = ROOT / "entregables" / "RevC" / "TT300-C_design.json"
MAX_BODY = 50 * 1024 * 1024
DUR_ESTIMADA = 300.0          # s; se corrige con la duración de los trabajos anteriores
ORIGENES = {"null", "file://"}


def version():
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def html_principal():
    hs = sorted(ROOT.glob("Tornamesa_v*.html"))
    return hs[-1].name if hs else ""


# ---------------------------------------------------------------- estructura del JSON de diseño
_REF = {}


def referencia():
    """Claves de referencia del JSON de diseño: `node tools/export_design.js` si hay Node; si no, el diseño del juego Base entregado."""
    if _REF:
        return _REF
    D, fuente = None, ""
    node = shutil.which("node")
    if node and (ROOT / "tools" / "export_design.js").exists():
        try:
            r = subprocess.run([node, str(ROOT / "tools" / "export_design.js")], capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT), timeout=300)
            if r.returncode == 0:
                D, fuente = json.loads(r.stdout), "node tools/export_design.js"
        except (OSError, ValueError, subprocess.SubprocessError):
            D = None
    if D is None and REF_DESIGN.exists():
        D, fuente = json.loads(REF_DESIGN.read_text(encoding="utf-8")), str(REF_DESIGN.relative_to(ROOT).as_posix())
    if D is None:
        raise RuntimeError("No hay JSON de diseño de referencia (ni Node ni entregables/RevC/TT300-C_design.json).")
    _REF.update(fuente=fuente, top=set(D), P=set(D["P"]), sub={k: set(v) for k, v in D.items() if isinstance(v, dict) and k != "P"})
    return _REF


def verificar_estructura(D):
    """Lista de diferencias de estructura con el JSON de `node tools/export_design.js` (vacía = misma estructura)."""
    if not isinstance(D, dict):
        return ["el contenido no es un objeto JSON"]
    ref, err = referencia(), []
    falt, sobr = sorted(ref["top"] - set(D)), sorted(set(D) - ref["top"])
    if falt:
        err.append("faltan claves de primer nivel: " + ", ".join(falt))
    if sobr:
        err.append("claves de primer nivel desconocidas: " + ", ".join(sobr))
    if not isinstance(D.get("P"), dict):
        err.append("falta el objeto P (parámetros)")
    else:
        fp, sp = sorted(ref["P"] - set(D["P"])), sorted(set(D["P"]) - ref["P"])
        if fp:
            err.append("faltan parámetros en P: " + ", ".join(fp))
        if sp:
            err.append("parámetros desconocidos en P: " + ", ".join(sp))
    for k, ks in ref["sub"].items():
        if k in D and isinstance(D[k], dict) and ks - set(D[k]):
            err.append(f"faltan claves en {k}: " + ", ".join(sorted(ks - set(D[k]))))
    if isinstance(D.get("verdict"), dict) and not {"gira", "estructura"} <= set(D["verdict"]):
        err.append("verdict sin gira/estructura")
    return err


def alternativa(P):
    a = "A" if P.get("opt_ss") else "B" if P.get("opt_uhmw") else ("C%d" % min(3, max(1, round(P.get("bz_conf") or 1)))) if P.get("opt_bz") else "base"
    if P.get("opt_ss") and P.get("fix_mode") == 2:
        a += "F2"
    if (P.get("opt_wood") or 0) > 0.5:
        a += "_madera"
    return a


# ---------------------------------------------------------------- trabajos en segundo plano
class Trabajo:
    def __init__(self, design_txt, P):
        ahora = datetime.datetime.now()
        self.alt = alternativa(P)
        self.P = P
        self.id = ahora.strftime("%Y-%m-%d_%H%M%S") + "_" + self.alt
        self.carpeta = SALIDAS / self.id
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="tt300c_"))
        self.design = self.tmp / "TT300-C_design.json"
        self.design.write_text(design_txt, encoding="utf-8")
        self.estado, self.fase, self.codigo, self.mensaje, self.indice = "en_curso", "Iniciando", None, "", None
        self.log = collections.deque(maxlen=400)
        self.err = collections.deque(maxlen=60)
        self.t0, self.t1 = time.time(), None
        self.lock = threading.Lock()

    def _linea(self, s, err=False):
        s = s.rstrip("\r\n")
        with self.lock:
            self.log.append(s)
            if err:
                self.err.append(s)
            low = s.lower()
            for clave, fase in (("3d vs", "Modelo 3D listo; dibujando láminas"), ("interferencias", "Dibujando láminas"), ("globos faltantes", "Despiece y listas"),
                                ("cadenas:", "Controles de cotas"), ("qc gráfico", "Control de calidad gráfico"), ("paquete listo", "Copiando la entrega")):
                if clave in low:
                    self.fase = fase

    def _leer(self, stream, err):
        for ln in iter(stream.readline, ""):
            self._linea(ln, err)
        stream.close()

    def _correr(self, args, fase):
        self.fase = fase
        self._linea("$ " + " ".join(str(a) for a in args))
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        p = subprocess.Popen([str(a) for a in args], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", env=env)
        hs = [threading.Thread(target=self._leer, args=(p.stdout, False), daemon=True), threading.Thread(target=self._leer, args=(p.stderr, True), daemon=True)]
        for h in hs:
            h.start()
        rc = p.wait()
        for h in hs:
            h.join()
        return rc

    def correr(self):
        global DUR_ESTIMADA
        try:
            SALIDAS.mkdir(exist_ok=True)
            out = self.tmp / "out"
            rc = self._correr([sys.executable, "-u", ROOT / "tools" / "lanzar_generador.py", self.design, "--out", out, "--entrega", self.carpeta], "Modelo 3D y láminas")
            self.codigo = rc
            if rc != 0:
                self.mensaje = "\n".join(self.err) or "\n".join(list(self.log)[-15:])
            if (self.carpeta / "informe_paquete.md").exists():
                rc2 = self._correr([sys.executable, "-u", ROOT / "tools" / "indice_planos.py", self.carpeta], "Índice y PDF por grupo")
                ip = self.carpeta / "indice_planos.json"
                if rc2 == 0 and ip.exists():
                    self.indice = json.loads(ip.read_text(encoding="utf-8"))
                elif rc == 0:
                    self.codigo, self.mensaje = rc2, "Falló tools/indice_planos.py:\n" + "\n".join(self.err)
            elif rc == 0:
                self.codigo, self.mensaje = -1, "El generador terminó sin dejar la entrega en " + str(self.carpeta)
            self.estado = "listo" if self.codigo == 0 else "error"
            if self.estado == "listo":
                shutil.rmtree(self.tmp, ignore_errors=True)
                DUR_ESTIMADA = 0.5 * DUR_ESTIMADA + 0.5 * (time.time() - self.t0)
            else:
                self._linea(f"(archivos de trabajo conservados en {self.tmp})")
        except Exception as ex:  # error del propio servidor
            self.estado, self.mensaje = "error", f"{type(ex).__name__}: {ex}"
        finally:
            self.t1 = time.time()
            self.fase = "Terminado" if self.estado == "listo" else "Terminado con error"

    def json(self):
        with self.lock:
            dur = (self.t1 or time.time()) - self.t0
            if self.estado == "en_curso":
                prog = min(0.95, dur / DUR_ESTIMADA) if self.fase != "Índice y PDF por grupo" else 0.97
            else:
                prog = 1.0
            return {"id": self.id, "alternativa": self.alt, "estado": self.estado, "fase": self.fase, "progreso": round(prog, 3), "duracion_s": round(dur, 1),
                    "codigo": self.codigo, "mensaje": self.mensaje, "P": self.P, "carpeta": self.carpeta.relative_to(ROOT).as_posix(), "indice": self.indice, "log": list(self.log)[-200:]}


TRABAJOS = {}
ULTIMO = [None]
LOCK = threading.Lock()


# ---------------------------------------------------------------- HTTP
class Manejador(http.server.SimpleHTTPRequestHandler):
    server_version = "TT300C-planos/1.0"

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/estado"):
            return
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

    def _origen_ok(self):
        o = self.headers.get("Origin")
        if o is None:
            return True, None
        host = urllib.parse.urlsplit(o).hostname if o not in ORIGENES else None
        return (o in ORIGENES or host in ("127.0.0.1", "localhost")), o

    def _cors(self):
        ok, o = self._origen_ok()
        if ok and o:
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(b)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_OPTIONS(self):
        ok, _ = self._origen_ok()
        self.send_response(204 if ok else 403)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        if u.path == "/api/ping":
            t = ULTIMO[0]
            return self._json(200, {"ok": True, "servicio": "generador de planos TT300-C", "version": version(), "html": html_principal(),
                                    "python": sys.version.split()[0], "servidor": "%s:%d" % self.server.server_address[:2], "trabajo": t.json() if t else None})
        if u.path == "/api/estado":
            q = urllib.parse.parse_qs(u.query)
            tid = (q.get("id") or [""])[0]
            t = TRABAJOS.get(tid) if tid else ULTIMO[0]
            if not t:
                return self._json(404, {"error": "No existe el trabajo «%s»." % tid})
            return self._json(200, t.json())
        if u.path.startswith("/api/"):
            return self._json(404, {"error": "Ruta desconocida"})
        if u.path in ("", "/"):
            self.send_response(302)
            self.send_header("Location", "/" + html_principal())
            self.end_headers()
            return
        return super().do_GET()

    def do_POST(self):
        u = urllib.parse.urlsplit(self.path)
        ok, o = self._origen_ok()
        if not ok:
            return self._json(403, {"error": "Origen no permitido: %s" % o})
        if u.path != "/api/generar":
            return self._json(404, {"error": "Ruta desconocida"})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._json(400, {"error": "Envíe el JSON de diseño en el cuerpo (máximo %d MB)." % (MAX_BODY // 2**20)})
        txt = self.rfile.read(n).decode("utf-8", errors="replace")
        try:
            D = json.loads(txt)
        except ValueError as ex:
            return self._json(400, {"error": "JSON no válido: %s" % ex})
        try:
            dif = verificar_estructura(D)
        except Exception as ex:
            return self._json(500, {"error": str(ex)})
        if dif:
            return self._json(400, {"error": "El JSON no tiene la estructura de tools/export_design.js (" + referencia()["fuente"] + "): " + "; ".join(dif), "diferencias": dif})
        with LOCK:
            t = ULTIMO[0]
            if t and t.estado == "en_curso":
                return self._json(409, {"error": "Ya hay una generación en curso (%s); espere a que termine." % t.id, "trabajo": t.json()})
            t = Trabajo(txt, D["P"])
            TRABAJOS[t.id] = ULTIMO[0] = t
        threading.Thread(target=t.correr, daemon=True).start()
        print(f"Generando planos: {t.id} → {t.carpeta.relative_to(ROOT).as_posix()}/", flush=True)
        return self._json(202, t.json())


class Servidor(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != "nt"     # en Linux/macOS permite reabrir el puerto tras cerrar; en Windows SO_REUSEADDR dejaría dos servidores en el mismo puerto


def main():
    ap = argparse.ArgumentParser(description="Generador local de planos TT300-C")
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--no-abrir", action="store_true", help="no abrir el navegador")
    a = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    url = "http://127.0.0.1:%d/%s" % (a.puerto, html_principal())
    try:
        srv = Servidor(("127.0.0.1", a.puerto), Manejador)
    except OSError:
        print(f"El puerto {a.puerto} ya está en uso: probablemente el generador ya está abierto. Abriendo {url}", flush=True)
        if not a.no_abrir:
            webbrowser.open(url)
        return 0
    try:
        referencia()
    except Exception as ex:
        print("AVISO:", ex, flush=True)
    print(f"Generador de planos TT300-C activo en {url}", flush=True)
    print("Deje esta ventana abierta mientras use la herramienta; para detenerlo, ciérrela o pulse Ctrl+C.", flush=True)
    if not a.no_abrir:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nGenerador detenido.", flush=True)
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
