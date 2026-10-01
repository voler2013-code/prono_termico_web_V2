/* Port de la geometría y fórmulas identificadas en el APK com.ajw.skewt.
   Referencia: GraphCoordConverter, MyUtils y Artist. Unidades públicas: °C, hPa, m.
   No depende de Android ni de bibliotecas de gráficos. */
(function(root) {
'use strict';
const P0=1013.25;
const valid=x=>typeof x==='number'&&Number.isFinite(x);
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const altitude=p=>(1-Math.pow(p/P0,.190284))*145366.45*.3048;
const pressure=z=>P0*Math.pow(1-z/.3048/145366.45,1/.190284);
const esat=t=>Math.exp(17.2693882*t/(t+237.3))*6.1078;
const mixing=(t,p)=>621.97*esat(t)/(p-esat(t));
const os=(t,p)=>Math.pow(1000/p,.286)*(t+273.16)/Math.exp(mixing(t,p)*-2.6518986/(t+273.16))-273.16;
function tsa(theta,p){
 let step=120,t=253.16;
 for(let i=1;i<=12;i++){
  step/=2;
  const e=Math.exp(mixing(t-273.16,p)*-2.6518986/t)*(theta+273.16)-Math.pow(1000/p,.286)*t;
  if(Math.abs(e)<.01)break;
  t+=e>=0?step:-step;
 }
 return t-273.16;
}
function tmr(w,p){
 const a=Math.log10(p*w/(w+622));
 return Math.pow(10,.0498646455*a+2.4082965)-7.07475+38.9114*Math.pow(Math.pow(10,.0915*a)-1.2035,2)-273.16;
}
class Transform {
 constructor(scale=2,originX=0,originY=0){this.s=scale;this.ox=originX;this.oy=originY;}
 project(p,t){const u=400*this.s*Math.log(P0/p);return [10*this.s*t-this.ox+u,800-this.oy-u];}
 inverse(x,y){const u=800-this.oy-y;return {p:Math.exp(Math.log(P0)-u/(400*this.s)),t:(x+this.ox-u)/(10*this.s)};}
 zoom(f,x=400,y=400){const q=this.inverse(x,y);this.s=Math.max(.5,Math.min(12,this.s*f));const u=400*this.s*Math.log(P0/q.p);this.ox=10*this.s*q.t+u-x;this.oy=800-u-y;}
}
let chartCounter = 0;
class SkewT {
 constructor(svg,readout){
  this.svg=svg;svg._skewt=this;this.readout=readout;this.clipId="skewt-clip-"+(++chartCounter);this.tr=new Transform();this.points=[];
  this.layers={dry:true,moist:true,mix:false,altitude:false};
  svg.setAttribute('viewBox','0 0 1000 950');svg.setAttribute('role','img');
  svg.setAttribute('aria-label','Diagrama Skew-T: temperatura roja y punto de rocío azul');
  svg.setAttribute('tabindex','0');
  svg.addEventListener('keydown',e=>{if(['+','=','-','0'].includes(e.key)){e.preventDefault();if(e.key==='0')this.fit();else{this.tr.zoom(e.key==='-'?.8:1.25);this.draw();}}});
  this.drag=null;this.pointers=new Map();
  svg.addEventListener('wheel',e=>{e.preventDefault();const p=this.local(e);this.tr.zoom(Math.exp(-e.deltaY*.001),...p);this.draw();},{passive:false});
  svg.addEventListener('pointerdown',e=>{svg.setPointerCapture(e.pointerId);this.pointers.set(e.pointerId,this.local(e));this.drag=this.local(e);this.inspect(this.drag);});
  const end=e=>{this.pointers.delete(e.pointerId);this.drag=null;};
  svg.addEventListener('pointerup',end);svg.addEventListener('pointercancel',end);
  svg.addEventListener('pointermove',e=>{
   const p=this.local(e);
   if(this.pointers.has(e.pointerId)){
    if(this.pointers.size===2){
     const old=[...this.pointers.values()];const d0=Math.hypot(old[0][0]-old[1][0],old[0][1]-old[1][1]);
     this.pointers.set(e.pointerId,p);const now=[...this.pointers.values()];const d1=Math.hypot(now[0][0]-now[1][0],now[0][1]-now[1][1]);
     if(d0>5)this.tr.zoom(d1/d0,(now[0][0]+now[1][0])/2,(now[0][1]+now[1][1])/2);
    } else if(this.drag){this.tr.ox-=p[0]-this.drag[0];this.tr.oy-=p[1]-this.drag[1];}
    this.pointers.set(e.pointerId,p);this.drag=p;this.draw();
   }
   this.inspect(p);
  });
 }
 local(e){const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(this.svg.getScreenCTM().inverse());return [p.x-90,p.y-50];}
 setData(points,reset=true){this.points=points.filter(x=>valid(x.p)&&x.p>0&&valid(x.t)&&valid(x.td)).sort((a,b)=>b.p-a.p);if(reset)this.fit();else this.draw();}
 fit(){
  const fitPoints=this.fitPoints||this.points;
  if(!fitPoints.length){this.draw();return;}
  const xx=fitPoints.flatMap(v=>[v.t,v.td].map(t=>10*t+400*Math.log(P0/v.p))), yy=fitPoints.map(v=>400*Math.log(P0/v.p));
  const s=Math.min(6,750/Math.max(120,Math.max(...xx)-Math.min(...xx)),740/Math.max(100,Math.max(...yy)-Math.min(...yy)));
  this.tr=new Transform(s,s*(Math.min(...xx)+Math.max(...xx))/2-400,40-s*Math.min(...yy));this.draw();
 }
 path(points,color,width=1,dash=''){
  const xy=points.filter(a=>valid(a[0])&&valid(a[1])&&a[0]>0).map(a=>this.tr.project(...a));
  if(xy.length<2)return '';
  return `<path d="${xy.map((v,i)=>(i?'L':'M')+v.map(x=>x.toFixed(2)).join(' ')).join(' ')}" fill="none" stroke="${color}" stroke-width="${width}" ${dash?`stroke-dasharray="${dash}"`:''}/>`;
 }
 draw(){
  const displayWidth=this.svg.clientWidth||Math.min(1050,(globalThis.innerWidth||1000)-26);
  const compact=displayWidth<600,labelSize=Math.min(32,Math.max(16,11000/displayWidth));
  let body='',labels='';const line=(x1,y1,x2,y2,c,w=1)=>`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${w}"/>`;
  const text=(x,y,t,anchor='middle',fill='#596579')=>`<text x="${x}" y="${y}" text-anchor="${anchor}" fill="${fill}" font-size="${labelSize}" font-family="system-ui">${esc(t)}</text>`;
  for(let t=-160;t<=100;t+=10){body+=this.path([[1100,t],[150,t]],'#f0bebe',t%20===0?1.4:.8);const u=-this.tr.oy,x=10*this.tr.s*t-this.tr.ox+u;if(x>=0&&x<=800)labels+=text(x,830,t);}
  for(let p=100;p<=1050;p+=50){const y=this.tr.project(p,0)[1];if(y<0||y>800)continue;body+=line(0,y,800,y,'#cbd7e2',p%100===0?1.3:.6);if(!compact||p%100===0||p===250)labels+=text(-12,y+6,p,'end');}
  if(this.layers.altitude)for(let z=compact?1000:500;z<=15000;z+=compact?1000:500){const y=this.tr.project(pressure(z),0)[1];if(y<8||y>790)continue;body+=line(0,y,800,y,'#bcbcf1',.8);labels+=text(810,y+5,(z/1000).toFixed(1),'start','#6666aa');}
  if(this.layers.dry)for(let t=-30;t<=100;t+=10){let pts=[];const z0=altitude(1000)/.3048;for(let f=z0;f<50000;f+=1000)pts.push([pressure(f*.3048),t-(f-z0)/1000*2.9870399044147233]);body+=this.path(pts,'#b7dfb6',1);}
  if(this.layers.moist)for(let t=-30;t<=50;t+=10){let pts=[];const th=os(t,1000);for(let p=1000;p>=200;p-=20)pts.push([p,tsa(th,p)]);body+=this.path(pts,'#929c9c',.9);}
  if(this.layers.mix)for(const w of [.1,.4,1,2,4,7,10,16,24,32,40]){let pts=[];for(let p=1100;p>=200;p-=20)pts.push([p,tmr(w,p)]);body+=this.path(pts,'#a6a6a6',1,'5 5');}
  body+=this.path(this.points.map(v=>[v.p,v.t]),'#df363c',3.2);
  body+=this.path(this.points.map(v=>[v.p,v.td]),'#275ce6',3.2);
  for(const v of this.points){for(const [key,color] of [['t','#df363c'],['td','#275ce6']]){const [x,y]=this.tr.project(v.p,v[key]);body+=`<circle cx="${x}" cy="${y}" r="3.4" fill="${v.interpolado?'#fff':color}" stroke="${color}" stroke-width="1.4"/>`;}}
  this.svg.innerHTML=`<defs><clipPath id="${this.clipId}"><rect width="800" height="800"/></clipPath></defs><rect width="1000" height="950" fill="white"/><g transform="translate(90 50)"><rect width="800" height="800" fill="#fffde9"/><g clip-path="url(#${this.clipId})">${body}</g><rect width="800" height="800" fill="none" stroke="#3b4858" stroke-width="1.5"/>${labels}${text(400,870,'Temperatura (°C) · isotermas inclinadas')}${text(-10,-18,'hPa','end')}${this.layers.altitude?text(810,-18,'km ISA','start'):''}</g>`;
 }
 inspect([x,y]){
  if(!this.points.length||x<0||x>800||y<0||y>800)return;
  const p=this.tr.inverse(x,y).p;
  const v=this.points.reduce((a,b)=>Math.abs(Math.log(b.p/p))<Math.abs(Math.log(a.p/p))?b:a);
  const h=valid(v.z)?`${Math.round(v.z)} m s.n.m.`:`≈ ${Math.round(v.z_ref)} m (referencia)`;
  this.readout.textContent=`Nivel próximo: ${v.p.toFixed(0)} hPa · ${h} · T ${v.t.toFixed(1)} °C · Td ${v.td.toFixed(1)} °C${v.interpolado?' · incluye interpolación local':''}${v.presion_estimada?' · presión estimada':''}`;
 }
}
root.SkewTCore={Transform,altitude,pressure,esat,mixing,os,tsa,tmr};root.SkewT=SkewT;
if(typeof module!=='undefined')module.exports=root.SkewTCore;
})(typeof window!=='undefined'?window:globalThis);
