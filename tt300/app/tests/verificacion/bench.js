const FEA = require('./fea_mod.js');
const E=2e5, nu=0.3;
// 1) placa cuadrada empotrada a=1000 t=10 q=0.01: w0=0.00126 q a^4/D, M borde=-0.0513 q a^2, M centro 0.0231 q a^2
for (const n of [10,20,40]) {
  const a=1000,t=10,q=0.01,nodes=[],elems=[]; const id=(i,j)=>i*(n+1)+j;
  for(let i=0;i<=n;i++)for(let j=0;j<=n;j++)nodes.push([i*a/n,j*a/n]);
  for(let i=0;i<n;i++)for(let j=0;j<n;j++)elems.push([id(i,j),id(i+1,j),id(i+1,j+1),id(i,j+1)]);
  const clamp=[];for(let i=0;i<=n;i++)for(let j=0;j<=n;j++)if(i==0||j==0||i==n||j==n)clamp.push(id(i,j));
  const r=FEA.plate({nodes,elems,t,E,nu,q:new Float64Array(elems.length).fill(q),wFix:[],clamp});
  const D=E*t**3/(12*(1-nu*nu));
  const Mx=r.el.map(e=>e.M[0]); 
  console.log(`empotrada n=${n}: w ${(r.w[id(n/2,n/2)]/(q*a**4/D)).toExponential(4)} (teo 1.26e-3) Mmin(centro elem) ${(Math.min(...Mx)/(q*a*a)).toFixed(4)} (teo -0.0513 en borde) Mmax ${(Math.max(...Mx)/(q*a*a)).toFixed(4)} (teo 0.0231)`);
}
// 2) anular sector 30° b=150 empotrado, a=400 simplemente apoyado, t=30, q=1, con simetría β·n=0 en bordes del sector
const b=150,a=400,t=30,q=1,D=E*t**3/(12*(1-nu*nu)),al=Math.PI/6;
// solución Kirchhoff axisimétrica: w = q r^4/(64D) + A + B r^2 + C ln r + Ee r^2 ln r
function solve(){ const f=[(r)=>[1,r*r,Math.log(r),r*r*Math.log(r)],(r)=>[0,2*r,1/r,2*r*Math.log(r)+r],(r)=>[0,2,-1/(r*r),2*Math.log(r)+3]];
 const wp=(r)=>q*r**4/(64*D), wp1=(r)=>q*r**3/(16*D), wp2=(r)=>3*q*r*r/(16*D);
 const Mrow=(r)=>f[2](r).map((v,i)=>v+nu*f[1](r)[i]/r);
 const Ar=[f[0](b),f[1](b),f[0](a),Mrow(a)], rhs=[-wp(b),-wp1(b),-wp(a),-(wp2(a)+nu*wp1(a)/a)];
 // gauss
 const M=Ar.map((row,i)=>[...row,rhs[i]]); for(let i=0;i<4;i++){let p=i;for(let k=i+1;k<4;k++)if(Math.abs(M[k][i])>Math.abs(M[p][i]))p=k;[M[i],M[p]]=[M[p],M[i]];for(let k=0;k<4;k++)if(k!==i){const c=M[k][i]/M[i][i];for(let j=i;j<5;j++)M[k][j]-=c*M[i][j];}}
 const c=M.map((r,i)=>r[4]/r[i]); const w=(r)=>wp(r)+c[0]+c[1]*r*r+c[2]*Math.log(r)+c[3]*r*r*Math.log(r);
 const w1=(r)=>wp1(r)+f[1](r).reduce((s,v,i)=>s+v*c[i],0), w2=(r)=>wp2(r)+f[2](r).reduce((s,v,i)=>s+v*c[i],0);
 return {w,Mr:(r)=>-D*(w2(r)+nu*w1(r)/r),Mt:(r)=>-D*(w1(r)/r+nu*w2(r))}; }
const S=solve(); let wmax=0,rw=0; for(let r=b;r<=a;r+=0.5){if(Math.abs(S.w(r))>wmax){wmax=Math.abs(S.w(r));rw=r;}}
console.log(`anular Kirchhoff: Mr(b) ${S.Mr(b).toFixed(1)} N·mm/mm σ ${(6*Math.abs(S.Mr(b))/t/t).toFixed(2)} MPa; wmax ${wmax.toFixed(5)} at r ${rw}`);
for (const [nr,nt] of [[12,8],[25,24],[50,48]]) {
  const nodes=[],elems=[],rs=[],ts=[]; for(let i=0;i<=nr;i++)rs.push(b+(a-b)*i/nr); for(let j=0;j<=nt;j++)ts.push(al*j/nt);
  const id=(i,j)=>i*(nt+1)+j; rs.forEach(r=>ts.forEach(th=>nodes.push([r*Math.cos(th),r*Math.sin(th)])));
  for(let i=0;i<nr;i++)for(let j=0;j<nt;j++)elems.push([id(i,j),id(i+1,j),id(i+1,j+1),id(i,j+1)]);
  const clamp=[],wFix=[],betaN=[]; for(let j=0;j<=nt;j++){clamp.push(id(0,j));wFix.push(id(nr,j));}
  for(let i=1;i<=nr;i++){betaN.push([id(i,0),0,1]);betaN.push([id(i,nt),-Math.sin(al),Math.cos(al)]);}
  const r=FEA.plate({nodes,elems,t,E,nu,q:new Float64Array(elems.length).fill(q),wFix,clamp,betaN});
  let vg=0,vn=0; r.el.forEach(e=>{vg=Math.max(vg,e.vmGauss);vn=Math.max(vn,e.vmNode);}); let wm=0; for(const w of r.w)wm=Math.max(wm,Math.abs(w));
  // σvm teórico en r=b: σr=6Mr/t², σθ=ν σr (empotrado)
  const sr=6*S.Mr(b)/t/t, vmT=Math.abs(sr)*Math.sqrt(1-nu+nu*nu);
  console.log(`FE ${nr}x${nt}: vmGauss ${vg.toFixed(2)} vmCorner ${vn.toFixed(2)} (teo σvm borde ${vmT.toFixed(2)}) wmax ${wm.toFixed(5)} (Kirchhoff ${wmax.toFixed(5)}) F ${r.Fapplied.toFixed(0)} R ${(-r.Rsum).toFixed(0)}`);
}
