import re
s=open('shell.html').read()
for tag,f in [('FEA','fea.js'),('CALC','calc.js'),('DIAG','diag.js'),('EXPORT','export.js'),('GEO','geo.js'),('UI','ui.js')]:
    code=open(f).read().replace('if (typeof module !== "undefined") module.exports','if (false) module.exports')
    s=s.replace('/*@@%s@@*/'%tag, code)
open('tornamesa.html','w').write(s)
print(len(s))
sk='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'
open('TT300-B_Verificacion_Tornamesa.html','w').write(sk+s+'</body></html>')
import os, shutil
os.makedirs('site/planos', exist_ok=True)
shutil.copy('TT300-B_Verificacion_Tornamesa.html','site/index.html')
for f in ['TT300-B_Tornamesa300_Planos_Diseno.pdf','TT300-B_Tornamesa300_Planos_Fabricacion.pdf','TT300-B_Tornamesa300_DXF_STEP.zip']:
    shutil.copy('../out/'+f,'site/planos/'+f)
