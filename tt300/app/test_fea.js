const FEA = require('./fea.js');
// SS square plate a=1000,t=10,q=0.01
const a=1000,n=20,nodes=[],elems=[];
for(let i=0;i<=n;i++)for(let j=0;j<=n;j++)nodes.push([i*a/n,j*a/n]);
const id=(i,j)=>i*(n+1)+j;
for(let i=0;i<n;i++)for(let j=0;j<n;j++)elems.push([id(i,j),id(i+1,j),id(i+1,j+1),id(i,j+1)]);
const wFix=[],betaN=[];
for(let i=0;i<=n;i++)for(let j=0;j<=n;j++){ if(i==0||i==n){wFix.push(id(i,j));betaN.push([id(i,j),0,1]);} else if(j==0||j==n){wFix.push(id(i,j));betaN.push([id(i,j),1,0]);} }
let t0=Date.now();
const r=FEA.plate({nodes,elems,t:10,E:2e5,nu:0.3,q:new Float64Array(elems.length).fill(0.01),wFix,betaN});
const D=2e5*1000/(12*0.91);
console.log('w FE',r.w[id(n/2,n/2)].toFixed(4),'Navier',(0.00406*0.01*1e12/D).toFixed(4),'ms',Date.now()-t0);
const ec=elems.findIndex(e=>e[0]==id(n/2-1,n/2-1)||false);
console.log('Mx center elem',r.el[id(n/2,n/2)-n/2-1]&&0, 'max M', Math.max(...r.el.map(e=>e.M[0])).toFixed(1),'theory 479');
console.log('Fapplied',r.Fapplied.toFixed(1),'Rsum',r.Rsum.toFixed(1));
// clamped thick check t=100 ratio
// cantilever plane stress L=1000 h=100 t=10 P=1000
const L=1000,h=100,nx=80,ny=10,N2=[],E2=[];
for(let i=0;i<=nx;i++)for(let j=0;j<=ny;j++)N2.push([i*L/nx,j*h/ny]);
const id2=(i,j)=>i*(ny+1)+j;
for(let i=0;i<nx;i++)for(let j=0;j<ny;j++)E2.push([id2(i,j),id2(i+1,j),id2(i+1,j+1),id2(i,j+1)]);
const fix=[];for(let j=0;j<=ny;j++){fix.push([id2(0,j),0],[id2(0,j),1]);}
const loads=[];for(let j=0;j<=ny;j++)loads.push([id2(nx,j),0,-1000/(ny+1)]);
const r2=FEA.planeStress({nodes:N2,elems:E2,t:10,E:2e5,nu:0.3,fix,loads});
console.log('tip',r2.u[2*id2(nx,ny/2)+1].toFixed(4),'theory -2.0(+shear ~0.026)');
console.log('max sx',Math.max(...r2.el.map(e=>Math.abs(e.sx))).toFixed(1),'theory 60 at root (elem center ~ 59)');
