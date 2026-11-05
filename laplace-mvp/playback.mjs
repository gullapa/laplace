import {simulate} from './physics.mjs';
function rotate(v,q){const [x,y,z,w]=q,[a,b,c]=v;const tx=2*(y*c-z*b),ty=2*(z*a-x*c),tz=2*(x*b-y*a);return [a+w*tx+y*tz-z*ty,b+w*ty+z*tx-x*tz,c+w*tz+x*ty-y*tx]}
function project(p){return [150+(p[0]-p[1])*1100,305+(p[0]+p[1])*450-p[2]*950]}
const poly=points=>points.map(p=>p.map(n=>n.toFixed(1)).join(',')).join(' ');
function renderFrame(svg,frame,objects,scene){let content='<ellipse cx="150" cy="308" rx="90" ry="21" fill="none" stroke="#6a9683" opacity=".4"/>';
 objects.forEach((item,i)=>{let [x,y,z,qx,qy,qz,qw]=frame[i],along=(item.level-1+scene.phase)%2===0,w=scene.width_mm/1000,len=scene.length_mm/1000,h=(scene.height_mm??15)/1000,sx=(along?w:len)/2,sy=(along?len:w)/2,sz=h/2,q=[qx,qy,qz,qw];let vertex=(a,b,c)=>{let p=rotate([a*sx,b*sy,c*sz],q);return project([x+p[0],y+p[1],z+p[2]])};let a=vertex(-1,-1,1),b=vertex(1,-1,1),c=vertex(1,1,1),d=vertex(-1,1,1),e=vertex(-1,1,-1),f=vertex(1,1,-1),g=vertex(1,-1,-1);content+=`<g stroke="#253f37" stroke-width=".65"><polygon points="${poly([d,c,f,e])}" fill="#988a70"/><polygon points="${poly([b,c,f,g])}" fill="#756b59"/><polygon points="${poly([a,b,c,d])}" fill="#c2b391"/></g>`});svg.innerHTML=content}
export async function playback(scene,action,svg){
 const result=simulate(scene,action,{seconds:2});let start=performance.now();
 await new Promise((resolve,reject)=>{function tick(now){try{let index=Math.max(0,Math.min(result.frames.length-1,Math.floor((now-start)/1000*30)));renderFrame(svg,result.frames[index],result.objects,scene);if(index>=result.frames.length-1)resolve();else requestAnimationFrame(tick)}catch(error){reject(error)}}requestAnimationFrame(tick)});
 return {displaced:result.displaced,max_movement_mm:result.max_movement_mm,settings:result.settings};
}
