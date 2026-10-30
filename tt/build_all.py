import pymupdf, sheet1, sheet2, sheet3, sheet4, zipfile, os
names = {"U": "TT500-A_Tornamesa_UHMW", "S": "TT500-B_Tornamesa_Acero-Grafito"}
for k in ("U", "S"):
    out = pymupdf.open()
    dxfs = []
    for i, f in enumerate((sheet1.sheet1, sheet2.sheet2, sheet3.sheet3, sheet4.sheet4), 1):
        S, v = f(k)
        d, p = f"out/{v['code']}-{i:02d}.dxf", f"out/{v['code']}-{i:02d}.pdf"
        S.save(d, p); dxfs.append(d)
        out.insert_pdf(pymupdf.open(p))
    out.set_metadata({"title": f"{names[k]} – Planos mecánicos", "author": "", "subject": v["title"]})
    out.save(f"out/{names[k]}_Planos.pdf", garbage=3, deflate=True)
    with zipfile.ZipFile(f"out/{names[k]}_DXF.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for d in dxfs: z.write(d, os.path.basename(d))
        z.write(f"out/{v['code']}.step", f"{v['code']}_conjunto.step")
    print(k, "ok")
