"""Arma dist/TT300-C_Modelo3D.html: visor 3D autónomo con el GLB embebido (three.js 0.147.0 desde jsDelivr)."""
import base64, json, pathlib
root = pathlib.Path(__file__).resolve().parents[1]
out = root / "cad" / "out"
glb = base64.b64encode((out / "TT300-C.glb").read_bytes()).decode()
D = json.load(open(out / "TT300-C_design.json", encoding="utf-8"))
M3 = json.load(open(out / "TT300-C_masas3d.json", encoding="utf-8"))
P, DV = D["P"], D["derivados"]
dis = [c for c in DV["casos"] if c["id"] == "dis"][0]
info = {
    "Capacidad": f"{P['W_tf']:.0f} tf", "Mesa": f"Ø{P['D_top']:.0f} × {P['h_disc']:.0f} mm", "Base": f"{P['B']:.0f} × {P['B']:.0f} × {P['t_base']:.0f} mm",
    "Alto total": f"{P['t_base'] + P['h_disc']:.0f} mm", "Masa total": f"{DV['masas']['total']:.0f} kg", "FS diseño": f"{dis['FS']:.2f}".replace(".", ","),
    "Pasadores": f"{P['N_pin']:.0f} × Ø{P['d_pin']:.0f} en R{P['R_pin']:.0f}", "Cilindros": f"{P['n_cyl']:.0f} × Ø{P['D_bore']:.0f}/Ø{P['d_rod']:.0f}, carrera {P['stroke']:.0f}",
}
NAMES = {"1a_plancha_base": "1a Plancha base", "1b_marco": "1b Marco", "1c_menuslas": "1c Ménsulas", "1d_puntos_izaje": "1d Puntos de izaje", "2_mesa": "2 Mesa giratoria",
         "3_pasadores": "3 Pasadores de empuje", "4_arandelas_pernos": "4 Arandelas y pernos", "5_pivote": "5 Pivote", "6_buje": "6 Buje", "7_tapa_retenedora": "7 Tapa retenedora",
         "8_tapa_inspeccion": "8 Tapa de inspección", "9_cilindros": "9 Cilindros", "10_unas": "10 Uñas", "11_pasadores_articulacion": "11 Pasadores de articulación"}
html = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TT300-C Modelo 3D</title>
<style>
:root{--bg:#f4f5f7;--panel:#fff;--ink:#15181d;--ink2:#555e6b;--line:#d9dde3;--acc:#1f5fbf}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111418;--panel:#181c22;--ink:#e7eaee;--ink2:#a7b0bd;--line:#2c333d;--acc:#6ea8ff}}
:root[data-theme="dark"]{--bg:#111418;--panel:#181c22;--ink:#e7eaee;--ink2:#a7b0bd;--line:#2c333d;--acc:#6ea8ff}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font:14px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{display:grid;grid-template-columns:300px 1fr;height:100vh}
aside{background:var(--panel);border-right:1px solid var(--line);overflow:auto;padding:12px 14px}
h1{font-size:15px;margin:0 0 4px}.sub{color:var(--ink2);font-size:12px;margin-bottom:10px}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:var(--ink2);margin:14px 0 6px}
.kv{display:grid;grid-template-columns:1fr auto;gap:2px 10px;font-size:12.5px}.kv span:nth-child(even){font-family:ui-monospace,Menlo,Consolas,monospace;text-align:right}
label.p{display:flex;align-items:center;gap:8px;font-size:12.5px;padding:2px 0;cursor:pointer}
label.p i{width:12px;height:12px;border-radius:3px;display:inline-block;border:1px solid var(--line)}
.btns{display:flex;flex-wrap:wrap;gap:6px}
button{font:600 12px system-ui,sans-serif;padding:6px 10px;border-radius:7px;border:1px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
#v{position:relative;min-height:320px}#v canvas{display:block;width:100%;height:100%}
#msg{position:absolute;left:12px;top:10px;color:var(--ink2);font-size:12px}
table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:3px 4px;border-bottom:1px solid var(--line)}th{text-align:left;color:var(--ink2)}td.n{text-align:right;font-family:ui-monospace,Menlo,monospace}
@media (max-width:860px){.wrap{grid-template-columns:1fr;grid-template-rows:auto 70vh;height:auto}aside{border-right:0;border-bottom:1px solid var(--line)}}
</style></head><body>
<div class="wrap"><aside>
<h1>TT300-C · Modelo 3D</h1><div class="sub">Generado desde TT300-C_design.json (misma fuente que el cálculo y los planos). Cilindros en la posición de toma del pasador, giro horario.</div>
<div class="btns"><button data-v="iso" class="on">Isométrica</button><button data-v="top">Planta</button><button data-v="front">Frente</button><button data-v="side">Lateral</button></div>
<div class="btns" style="margin-top:6px"><button id="bx">Mesa transparente</button><button id="bt">◐ Tema</button></div>
<h2>Datos</h2><div class="kv">__INFO__</div>
<h2>Piezas</h2><div id="parts"></div>
<h2>Control de masas (3D frente a cálculo)</h2><table><tr><th>Pieza</th><th class="n">3D kg</th><th class="n">Cálc. kg</th><th class="n">Δ %</th></tr>__MASAS__</table>
</aside><div id="v"><div id="msg">Cargando modelo…</div></div></div>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/loaders/GLTFLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/OrbitControls.js"></script>
<script>
const NAMES = __NAMES__;
const GLB = "__GLB__";
const host = document.getElementById("v"), msg = document.getElementById("msg");
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
try { const t = localStorage.getItem("tt300c-3d-theme"); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
host.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const cam = new THREE.PerspectiveCamera(35, 1, 10, 40000);
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a95, 1.0)); scene.add(new THREE.AmbientLight(0xffffff, 0.35));
const dl = new THREE.DirectionalLight(0xffffff, 0.75); dl.position.set(2500, -3000, 5000); scene.add(dl);
const ctl = new THREE.OrbitControls(cam, renderer.domElement);
ctl.target.set(0, 0, 100); cam.up.set(0, 0, 1);
function bg() { scene.background = new THREE.Color(css("--bg") || "#f4f5f7"); }
bg();
function size() { const w = host.clientWidth, h = Math.max(320, host.clientHeight); renderer.setSize(w, h, false); renderer.domElement.style.height = h + "px"; cam.aspect = w / h; cam.updateProjectionMatrix(); }
window.addEventListener("resize", size); size();
function view(v) {
  const d = 4200, t = ctl.target;
  const pos = { iso: [d * 0.62, -d * 0.78, d * 0.62], top: [0, -1, d * 1.15], front: [0, -d * 1.1, 120], side: [d * 1.1, 0, 120] }[v];
  cam.position.set(t.x + pos[0], t.y + pos[1], t.z + pos[2]); ctl.update();
  document.querySelectorAll("[data-v]").forEach((b) => b.classList.toggle("on", b.dataset.v === v));
}
document.querySelectorAll("[data-v]").forEach((b) => b.onclick = () => view(b.dataset.v));
document.getElementById("bt").onclick = () => {
  const dark = matchMedia("(prefers-color-scheme: dark)").matches, now = document.documentElement.dataset.theme || (dark ? "dark" : "light"), nx = now === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = nx; try { localStorage.setItem("tt300c-3d-theme", nx); } catch (e) {} bg();
};
const groups = {};
const bin = Uint8Array.from(atob(GLB), (c) => c.charCodeAt(0)).buffer;
new THREE.GLTFLoader().parse(bin, "", (g) => {
  const root = g.scene;
  root.traverse((o) => {
    if (o.isMesh) {
      o.material = o.material.clone(); o.material.side = THREE.DoubleSide;
      if ("metalness" in o.material) { o.material.metalness = 0.15; o.material.roughness = 0.55; }
      let p = o, key = null;
      while (p) { for (const k of Object.keys(NAMES)) if (p.name && p.name.indexOf(k) === 0) key = k; if (key) break; p = p.parent; }
      key = key || "otros"; (groups[key] = groups[key] || []).push(o);
    }
  });
  root.rotation.x = Math.PI / 2;            // glTF (Y arriba) → planos (Z arriba)
  root.updateMatrixWorld(true);
  scene.add(root);
  const box = new THREE.Box3().setFromObject(root), c = box.getCenter(new THREE.Vector3());
  ctl.target.copy(c); view("iso");
  const el = document.getElementById("parts");
  el.innerHTML = Object.keys(NAMES).filter((k) => groups[k]).map((k) => {
    const col = "#" + groups[k][0].material.color.getHexString();
    return `<label class="p"><input type="checkbox" checked data-k="${k}"><i style="background:${col}"></i>${NAMES[k]}</label>`;
  }).join("");
  el.addEventListener("change", (e) => { const k = e.target.dataset.k; (groups[k] || []).forEach((m) => m.visible = e.target.checked); });
  msg.textContent = "Arrastre para girar · rueda para acercar · botón derecho para desplazar";
}, (err) => { msg.textContent = "No se pudo cargar el modelo: " + err; });
let transp = false;
document.getElementById("bx").onclick = (e) => {
  transp = !transp; e.target.classList.toggle("on", transp);
  ["2_mesa", "4_arandelas_pernos", "8_tapa_inspeccion"].forEach((k) => (groups[k] || []).forEach((m) => { m.material.transparent = transp; m.material.opacity = transp ? 0.25 : 1; m.material.depthWrite = !transp; }));
};
(function loop() { requestAnimationFrame(loop); renderer.render(scene, cam); })();
</script></body></html>"""
html = (html.replace("__INFO__", "".join(f"<span>{k}</span><span>{v}</span>" for k, v in info.items()))
        .replace("__MASAS__", "".join(f"<tr><td>{r['pieza']}</td><td class='n'>{r['modelo3d']:.1f}</td><td class='n'>{r['nucleo']:.1f}</td><td class='n'>{r['dif_%']:.1f}</td></tr>" for r in M3["comparacion"]).replace(".", ","))
        .replace("__NAMES__", json.dumps(NAMES, ensure_ascii=False)).replace("__GLB__", glb))
dst = root / "dist" / "TT300-C_Modelo3D.html"
dst.write_text(html, encoding="utf-8")
print(dst, round(len(html) / 1e6, 2), "MB")
