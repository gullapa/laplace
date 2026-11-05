/** Experimental rigid-body replay, separate from the static assessment.
 * The selected block is absent at t=0; this does not simulate pushing it.
 */
import * as CANNON from './node_modules/cannon-es/dist/cannon-es.js';

export function simulate(scene,action,options={}){
  const dt=1/120, steps=Math.max(1,Math.round((options.seconds??2)*120));
  const width=Number(scene.width_mm)/1000,length=Number(scene.length_mm)/1000,height=Number(scene.height_mm??15)/1000,mass=Number(scene.mass_g??15)/1000,friction=Number(scene.friction??0.5);
  const world=new CANNON.World({gravity:new CANNON.Vec3(0,0,-9.81)});
  world.solver.iterations=100;world.solver.tolerance=1e-7;world.defaultContactMaterial.friction=friction;world.defaultContactMaterial.restitution=0;
  const floor=new CANNON.Body({mass:0,shape:new CANNON.Box(new CANNON.Vec3(.4,.4,.01)),position:new CANNON.Vec3(0,0,-.01)});world.addBody(floor);
  const objects=[];
  scene.levels.forEach((row,level)=>row.forEach((state,slot)=>{
    if(state!=='present'||(action.level===level+1&&action.slot===slot))return;
    const alongY=(level+scene.phase)%2===0,offset=(slot-1)*width;
    let sx=alongY?width:length,sy=alongY?length:width,x=alongY?offset:0,y=alongY?0:offset;
    const body=new CANNON.Body({mass,shape:new CANNON.Box(new CANNON.Vec3(sx/2,sy/2,height/2)),position:new CANNON.Vec3(x,y,height*(level+.5))});
    body.linearDamping=.08;body.angularDamping=.15;world.addBody(body);objects.push({level:level+1,slot,body,start:[x,y,height*(level+.5)]});
  }));
  const frames=[];
  let maxMovement=0;
  for(let i=0;i<=steps;i++){
    maxMovement=Math.max(maxMovement,...objects.map(o=>Math.hypot(o.body.position.x-o.start[0],o.body.position.y-o.start[1],o.body.position.z-o.start[2])));
    if(i%4===0)frames.push(objects.map(o=>[+o.body.position.x.toFixed(5),+o.body.position.y.toFixed(5),+o.body.position.z.toFixed(5),+o.body.quaternion.x.toFixed(5),+o.body.quaternion.y.toFixed(5),+o.body.quaternion.z.toFixed(5),+o.body.quaternion.w.toFixed(5)]));
    if(i<steps)world.step(dt);
  }
  const displaced=objects.filter(o=>Math.abs(o.body.position.z-o.start[2])>height*1.5||Math.hypot(o.body.position.x-o.start[0],o.body.position.y-o.start[1])>width*1.5).length;
  return {frames,max_movement_mm:+(maxMovement*1000).toFixed(1),objects:objects.map(o=>({level:o.level,slot:o.slot,start:o.start})),displaced,settings:{seconds:steps*dt,friction,mass_g:mass*1000,height_mm:height*1000,solver_iterations:100,displacement_rule:'final position: vertical > 1.5 block heights OR horizontal > 1.5 block widths',method:'instant removal; does not model pulling or real contact measurements'}};
}
