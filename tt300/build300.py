import pymupdf, zipfile, os, draw, sheet1, sheet2, sheet3, sheet4, sheet_d02, sheet_f03
code = "TT300-B"
sets = {
    "Diseno": [("D-01", "DISEÑO – CONJUNTO GENERAL, CORTES Y DATOS", sheet1.sheet1),
               ("D-02", "DISEÑO – ACCIONAMIENTO Y VERIFICACIONES", sheet_d02.sheet_d02),
               ("D-03", None, sheet2.sheet2)],
    "Fabricacion": [("F-01", None, sheet3.sheet3), ("F-02", None, sheet4.sheet4),
                    ("F-03", "FABRICACIÓN – LISTA DE CORTE, SOLDADURAS Y LUBRICACIÓN", sheet_f03.sheet_f03)],
}
dxfs = []
for name, sheets in sets.items():
    out = pymupdf.open()
    for i, (tag, title, fn) in enumerate(sheets, 1):
        draw.OVR.clear(); draw.OVR.update({"no": i, "n": len(sheets), "plano": f"{code}-{tag}"})
        if title: draw.OVR["title"] = title
        S, v = fn("S")
        d, p = f"out/{code}-{tag}.dxf", f"out/{code}-{tag}.pdf"
        S.save(d, p); dxfs.append(d)
        out.insert_pdf(pymupdf.open(p))
        pymupdf.open(p)[0].get_pixmap(dpi=90).save(f"out/{code}-{tag}.png")
    out.set_metadata({"title": f"{code} Tornamesa 300 tf – Planos de {name}", "author": "", "subject": v["title"]})
    out.save(f"out/{code}_Tornamesa300_Planos_{name}.pdf", garbage=3, deflate=True)
with zipfile.ZipFile(f"out/{code}_Tornamesa300_DXF_STEP.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for d in dxfs: z.write(d, os.path.basename(d))
    z.write(f"out/{code}.step", f"{code}_conjunto.step")
print("ok")
