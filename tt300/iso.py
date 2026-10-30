import sys, cadquery as cq, model3d as M
from cadquery.occ_impl.exporters.svg import getSVG
def iso_svg(kind, path, explode=0.0, dirn=(1.0,-1.6,1.1), w=900, h=650, hidden=False, only=None):
    v, parts = M.build(kind)
    shapes=[]
    for pos,name,shp,col in parts:
        if only and pos not in only: continue
        s = shp.val()
        if explode:
            dz = {1:0,2:0,3:0,19:0.4,20:1.4,21:1.4,4:1.6,6:1.6,14:1.6,15:1.6,5:0.0,7:3.2,8:3.6,9:2.6,10:2.6,11:3.0,12:2.6}.get(pos,0)
            s = s.translate(cq.Vector(0,0,dz*explode))
        shapes.append(s)
    comp = cq.Compound.makeCompound(shapes)
    svg = getSVG(comp, opts=dict(width=w, height=h, marginLeft=10, marginTop=10, projectionDir=dirn, showAxes=False, showHidden=hidden, strokeWidth=-1.0, strokeColor=(0,0,0), hiddenColor=(120,120,120)))
    open(path,'w').write(svg)
if __name__=='__main__':
    import time
    for k in ('U','S'):
        t=time.time(); iso_svg(k, f'out/iso_{k}.svg'); iso_svg(k, f'out/isoexp_{k}.svg', explode=250); print(k, time.time()-t)
