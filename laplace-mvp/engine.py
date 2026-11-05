"""An explicitly limited, quasi-static model of a block tower."""
from __future__ import annotations
import itertools, math

def hull(points):
    p=sorted(set(points))
    if len(p)<3:return p
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]
    for v in p:
        while len(lower)>=2 and cross(lower[-2],lower[-1],v)<=0:lower.pop()
        lower.append(v)
    upper=[]
    for v in reversed(p):
        while len(upper)>=2 and cross(upper[-2],upper[-1],v)<=0:upper.pop()
        upper.append(v)
    return lower[:-1]+upper[:-1]

def margin(point,poly):
    if len(poly)<3:return -1000.0
    vals=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        vals.append((dx*(point[1]-a[1])-dy*(point[0]-a[0]))/math.hypot(dx,dy))
    return min(vals)

def rect(level,slot,width,length,phase):
    offset=(slot-1)*width
    if (level+phase)%2==0:return (offset-width/2,-length/2,offset+width/2,length/2)
    return (-length/2,offset-width/2,length/2,offset+width/2)

def assess(scene,action):
    levels=scene['levels']; width=float(scene['width_mm']); length=float(scene['length_mm']); phase=int(scene.get('phase',0))
    if not (1<=len(levels)<=30 and 1<=width<=100 and width<=length<=400):raise ValueError('Check tower dimensions and levels.')
    lev=int(action['level'])-1; slot=int(action['slot'])
    if not 0<=lev<len(levels) or slot not in (0,1,2):raise ValueError('Select a valid block.')
    if any(len(row)!=3 or any(v not in ('present','empty','unknown') for v in row) for row in levels):raise ValueError('Every level must contain three valid slot states.')
    if levels[lev][slot]!='present':raise ValueError('Confirm that the selected block is present before assessment.')
    unknown=[(l,s) for l,row in enumerate(levels) for s,v in enumerate(row) if v=='unknown']
    if len(unknown)>8:return {'verdict':'INCONCLUSIVE','reason':f'{len(unknown)} slots are unknown; confirm more blocks before a meaningful assessment.','unknown':unknown,'cases_checked':0}
    results=[]
    for values in itertools.product(('empty','present'),repeat=len(unknown)):
        rows=[row[:] for row in levels]
        for (l,s),v in zip(unknown,values):rows[l][s]=v
        rows[lev][slot]='empty'
        worst=1000.; critical=0
        for level in range(len(rows)-1):
            below=[rect(level,s,width,length,phase) for s,v in enumerate(rows[level]) if v=='present']
            above=[rect(level+1,s,width,length,phase) for s,v in enumerate(rows[level+1]) if v=='present']
            loads=[rect(l,s,width,length,phase) for l in range(level+1,len(rows)) for s,v in enumerate(rows[l]) if v=='present']
            if not loads:continue
            contacts=[]
            for a in below:
                for b in above:
                    x1,y1=max(a[0],b[0]),max(a[1],b[1]); x2,y2=min(a[2],b[2]),min(a[3],b[3])
                    if x2-x1>1e-6 and y2-y1>1e-6:contacts.extend([(x1,y1),(x1,y2),(x2,y1),(x2,y2)])
            center=(sum((a[0]+a[2])/2 for a in loads)/len(loads),sum((a[1]+a[3])/2 for a in loads)/len(loads))
            m=margin(center,hull(contacts))
            if m<worst:worst,critical=m,level+1
        result='PREDICTS_STAND' if worst>=4 else 'PREDICTS_FALL' if worst<=-1 else 'INCONCLUSIVE'
        results.append({'verdict':result,'margin_mm':round(worst,2),'critical_level':critical,'assumed':dict((f'{l+1}:{s}',v) for (l,s),v in zip(unknown,values))})
    verdicts={r['verdict'] for r in results}
    if len(verdicts)!=1:return {'verdict':'INCONCLUSIVE','reason':'Different possible values for the unknown blocks lead to different model results. Please confirm the highlighted unknowns.','unknown':unknown,'cases_checked':len(results),'alternatives':results[:4]}
    chosen=min(results,key=lambda x:abs(x['margin_mm']))
    return {**chosen,'reason':f"Idealized static model: smallest aggregate support margin is {chosen['margin_mm']} mm at the interface above level {chosen['critical_level']}.",'unknown':unknown,'cases_checked':len(results),'limitations':'Aligned, equally weighted rigid blocks; estimates aggregate support only. Does not model individual load paths, pulling forces, friction, offsets, or motion. Not a structural safety assessment.'}
