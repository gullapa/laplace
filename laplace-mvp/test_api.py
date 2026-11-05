import json, tempfile, threading, unittest, urllib.error, urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import server

class EvidenceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.original_log=server.LOG;server.LOG=Path(cls.tmp.name)
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.http.server_port)+'/api/'
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();server.LOG=cls.original_log;cls.tmp.cleanup()
    def post(self,path,payload):
        req=urllib.request.Request(self.url+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=10) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    def test_assisted_outcome_not_comparable_and_not_overwritten(self):
        scene={'levels':[['present']*3 for _ in range(4)],'width_mm':25,'length_mm':75,'phase':1}
        status,lock=self.post('lock',{'scene':scene,'action':{'level':2,'slot':1}})
        self.assertEqual(status,200);self.assertEqual(lock['assessment']['verdict'],'PREDICTS_STAND')
        status,result=self.post('outcome',{'prediction_id':lock['id'],'outcome':'STOOD','assisted':True})
        self.assertEqual(status,200);self.assertEqual(result['payload']['comparison'],'NOT COMPARABLE')
        status,_=self.post('outcome',{'prediction_id':lock['id'],'outcome':'FELL'})
        self.assertEqual(status,400)
    def test_outcome_requires_real_lock(self):
        status,_=self.post('outcome',{'prediction_id':'unknown','outcome':'STOOD'})
        self.assertEqual(status,400)
if __name__=='__main__':unittest.main()
