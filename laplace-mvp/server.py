from __future__ import annotations
import base64, datetime, hashlib, ipaddress, json, logging, os, re, time, uuid
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv
from engine import assess

BASE=Path(__file__).resolve().parent
load_dotenv(BASE/'.env')
load_dotenv(BASE.parent/'.env')
if os.name=='nt':load_dotenv(Path.home()/'evidence-os'/'.env')
LOG=BASE/'runs'; LOG.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
API='https://api.meta.ai/v1'
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def event(kind,payload):
    item={'time':stamp(),'type':kind,'payload':payload}
    with (LOG/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(item)+'\n')
    logging.info('%s',kind)
    return item
def token():
    value=os.environ.get('MODEL_API_KEY')
    if not value:raise ValueError('MODEL_API_KEY was not found in the project environment file.')
    return value
def muse(question,scene):
    system='You are FORESIGHT, a concise assistant helping an operator inspect a block tower. Ask one clear question about missing scene information before offering an assessment. Never infer hidden blocks, imply safety, or invent numbers. The simulation is a limited static approximation. Use only provided scene facts. Respond in 1-2 sentences.'
    payload={'model':'muse-spark-1.3','input':[{'role':'user','content':[{'type':'input_text','text':system+'\nScene facts: '+json.dumps(scene)+'\nOperator: '+question}]}]}
    started=time.monotonic();r=requests.post(API+'/responses',headers={'Authorization':'Bearer '+token()},json=payload,timeout=65);r.raise_for_status(); data=r.json()
    text='\n'.join(part.get('text','') for item in data.get('output',[]) if item.get('type')=='message' for part in item.get('content',[]) if part.get('text'))
    if not text:raise ValueError('Muse returned no text response.')
    return {'text':text,'model':'muse-spark-1.3','elapsed_s':round(time.monotonic()-started,1)}
def sam(dataurl):
    prefix,raw=dataurl.split(',',1); content=base64.b64decode(raw,validate=True)
    if len(content)>12_000_000:raise ValueError('Image is too large; use a photo under 12 MB.')
    mime=prefix.split(';')[0].replace('data:','')
    if mime not in ('image/jpeg','image/png','image/webp'):raise ValueError('Use a JPEG, PNG, or WebP image.')
    headers={'Authorization':'Bearer '+token()}; start=time.monotonic()
    r=requests.post(API+'/files',headers=headers,data={'purpose':'user_data'},files={'file':('tower.jpg',content,mime)},timeout=90);r.raise_for_status();fid=r.json()['id']
    payload={'model':'sam-3.1','input':[{'type':'message','role':'user','content':[{'type':'input_text','text':'wooden block'},{'type':'input_image','file_id':fid}]}],'stream':True,'metadata':{'mask_encoding':'lossless'}}
    final=None
    with requests.post(API+'/responses',headers={**headers,'Accept':'text/event-stream'},json=payload,stream=True,timeout=180) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line.startswith(b'data: ') and line[6:]!=b'[DONE]':
                e=json.loads(line[6:]);
                if e.get('type')=='response.completed':final=e['response']
    if not final:raise ValueError('SAM did not return a completed response.')
    text='\n'.join(p.get('text','') for i in final.get('output',[]) for p in i.get('content',[]))
    boxes=[list(map(int,m)) for m in re.findall(r'<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>',text)]
    return {'boxes':boxes,'count':len(boxes),'elapsed_s':round(time.monotonic()-start,1),'model':'sam-3.1'}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(BASE),**kw)
    def do_POST(self):
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<=0 or n>20_000_000:raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(n));path=urlparse(self.path).path
            if path=='/api/assess':
                result=assess(data['scene'],data['action']);event('assessment',{'action':data['action'],'result':result});out=result
            elif path=='/api/lock':
                result=assess(data['scene'],data['action']);record={'id':uuid.uuid4().hex,'locked_at_utc':stamp(),'scene':data['scene'],'action':data['action'],'assessment':result};record['sha256']=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':')).encode()).hexdigest();event('prediction_locked',record);out=record
            elif path=='/api/outcome':
                if data.get('outcome') not in ('STOOD','FELL','UNCLEAR'):raise ValueError('Select an outcome.')
                if not data.get('prediction_id'):raise ValueError('Lock a prediction first.')
                events_path=LOG/'events.jsonl';events=[]
                if events_path.exists():
                    with events_path.open(encoding='utf-8') as f:events=[json.loads(line) for line in f if line.strip()]
                locks=[e['payload'] for e in events if e.get('type')=='prediction_locked' and e.get('payload',{}).get('id')==data['prediction_id']]
                if not locks:raise ValueError('Prediction lock not found in the evidence log.')
                if any(e.get('type')=='operator_outcome' and e.get('payload',{}).get('prediction_id')==data['prediction_id'] for e in events):raise ValueError('This prediction already has an outcome.')
                verdict=locks[-1]['assessment']['verdict'];actual=data['outcome']
                assisted=bool(data.get('assisted',False))
                comparison='NOT COMPARABLE' if assisted or actual=='UNCLEAR' or verdict=='INCONCLUSIVE' else 'MATCH' if (verdict=='PREDICTS_STAND' and actual=='STOOD') or (verdict=='PREDICTS_FALL' and actual=='FELL') else 'MISMATCH'
                out=event('operator_outcome',{'prediction_id':data['prediction_id'],'outcome':actual,'assisted':assisted,'comparison':comparison,'source':'operator-confirmed'})
            elif path=='/api/ask':
                out=muse(data.get('question','What information do you need first?'),data.get('scene',{}));event('muse_response',{'model':out['model'],'elapsed_s':out['elapsed_s'],'text':out['text']})
            elif path=='/api/physics':
                result=data.get('result',{});out=event('client_physics_replay',{'engine':'cannon-es 0.20.0','source':'browser-computed; not server-verified','scene':data.get('scene'),'action':data.get('action'),'displaced':result.get('displaced'),'settings':result.get('settings')})
            elif path=='/api/segment':
                out=sam(data['image']);prefix,raw=data['image'].split(',',1);photo=base64.b64decode(raw,validate=True);suffix={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}.get(prefix.split(';')[0].replace('data:',''),'.img');file=LOG/('sam-input-'+uuid.uuid4().hex+suffix);file.write_bytes(photo)
                event('sam_result',{'count':out['count'],'elapsed_s':out['elapsed_s'],'model':out['model'],'input_path':str(file.relative_to(BASE)),'boxes':out['boxes']})
            elif path=='/api/transcribe':
                raw=base64.b64decode(data['wav'],validate=True)
                if len(raw)>8_000_000:raise ValueError('Audio recording is too large.')
                start=time.monotonic()
                request={'model':'muse-voice-transcribe-1.0','audioEncoding':'WAV','mode':'PUSH_TO_TALK'}
                response=requests.post(API+'/asr/transcribe',headers={'Authorization':'Bearer '+token(),'Accept':'text/plain'},files={'request':(None,json.dumps(request),'application/json'),'audio':('speech.wav',raw,'audio/wav')},timeout=90)
                response.raise_for_status();transcript=response.text.strip()
                if not transcript:raise ValueError('No speech was recognized. Please try again.')
                out={'text':transcript,'model':'muse-voice-transcribe-1.0','elapsed_s':round(time.monotonic()-start,1)}
                event('voice_transcription',{'model':out['model'],'elapsed_s':out['elapsed_s'],'text':transcript})
            elif path=='/api/snapshot':
                url=urlparse(data['url'])
                if url.scheme!='http' or not url.hostname or not ipaddress.ip_address(url.hostname).is_private:raise ValueError('Camera address must be a private local IP address, such as http://192.168.1.20:8080.')
                image=requests.get(f'http://{url.netloc}/shot.jpg',timeout=10,allow_redirects=False);image.raise_for_status()
                if not image.headers.get('content-type','').lower().startswith('image/'):raise ValueError('Camera did not return an image.')
                if len(image.content)>12_000_000:raise ValueError('Camera image is too large.')
                file=LOG/('camera-'+uuid.uuid4().hex+'.jpg');file.write_bytes(image.content)
                out={'image':'data:image/jpeg;base64,'+base64.b64encode(image.content).decode()};event('camera_snapshot',{'source':'local_ip_webcam','saved_path':str(file.relative_to(BASE))})
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(out).encode())
        except Exception as e:
            logging.exception('Request failed');self.send_response(400);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps({'error':str(e)}).encode())
if __name__=='__main__':
    print('FORESIGHT running at http://127.0.0.1:8765',flush=True);ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
