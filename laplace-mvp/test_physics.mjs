import {simulate} from './physics.mjs';
import assert from 'node:assert/strict';
const tower=()=>({levels:Array.from({length:18},()=>['present','present','present']),width_mm:25,length_mm:75,phase:1});
for(const kind of ['stand','fall']){
 const s=tower();if(kind==='fall')s.levels[3][1]='empty';const before=Date.now(),result=simulate(s,{level:4,slot:kind==='fall'?0:1});
 console.log(kind,JSON.stringify({displaced:result.displaced,frames:result.frames.length,time_ms:Date.now()-before}));
 assert.equal(result.frames.length,61);
 assert.ok(Number.isFinite(result.max_movement_mm) && result.max_movement_mm >= 0);
 assert.match(result.settings.displacement_rule,/final position/);
 if(kind==='stand')assert.equal(result.displaced,0,'idealized reference case should remain together in this engine');
 if(kind==='fall')assert.ok(result.displaced>0,'unsupported reference case should displace blocks in this engine');
}
