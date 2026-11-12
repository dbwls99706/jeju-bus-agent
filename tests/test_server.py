import unittest,threading,json
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import test_agent
from server import Handler
class HttpTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=test_agent.Tests();cls.fixture.setUp();cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.base=f'http://127.0.0.1:{cls.server.server_port}'
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.fixture.tearDown()
 def test_catalog(self):
  with urlopen(self.base+'/api/catalog') as r:self.assertEqual(json.load(r)['rows'],27)
 def test_analyze(self):
  with urlopen(Request(self.base+'/api/analyze',data=json.dumps({'question':'시간'}).encode())) as r:self.assertEqual(json.load(r)['stats']['total'],480)
 def test_origin(self):
  with self.assertRaises(HTTPError) as c:urlopen(Request(self.base+'/api/analyze',data=b'{}',headers={'Origin':'https://other.example'}))
  self.assertEqual(c.exception.code,403)
 def test_bad_json(self):
  with self.assertRaises(HTTPError) as c:urlopen(Request(self.base+'/api/analyze',data=b'notjson'))
  self.assertEqual(c.exception.code,400)
 def test_secret(self):
  with self.assertRaises(HTTPError) as c:urlopen(self.base+'/.env')
  self.assertEqual(c.exception.code,404)
 def test_static(self):
  for path in ['/','/static/app.js','/static/styles.css']:
   with urlopen(self.base+path) as r:self.assertEqual(r.status,200)
 def test_plan(self):
  with urlopen(Request(self.base+'/api/plan',data=json.dumps({'question':'경로 시간대'}).encode())) as r:self.assertEqual(json.load(r)['user_types'],['경로'])
 def test_plan_mismatch(self):
  with self.assertRaises(HTTPError) as c:urlopen(Request(self.base+'/api/analyze',data=json.dumps({'question':'시간','expected_plan':{'wrong':'yes'}}).encode()))
  self.assertEqual(c.exception.code,400)
 def test_claim_plan_and_confirm(self):
  data={'question':'2024-01-01과2024-01-02 일반 일평균 비교','claim':{'metric':'total','direction':'equal'}}
  with urlopen(Request(self.base+'/api/claim-plan',data=json.dumps(data).encode())) as r:plan=json.load(r)
  self.assertEqual(plan['claim'],data['claim'])
  with urlopen(Request(self.base+'/api/claim-check',data=json.dumps({**data,'expected_plan':plan}).encode())) as r:result=json.load(r)
  self.assertEqual(result['claim_verification']['verdict'],'supported')
 def test_claim_check_requires_confirmation(self):
  data={'question':'2024-01-01과2024-01-02 일반 일평균 비교','claim':{'metric':'total','direction':'equal'}}
  with self.assertRaises(HTTPError) as c:urlopen(Request(self.base+'/api/claim-check',data=json.dumps(data).encode()))
  self.assertEqual(c.exception.code,400)
 def test_claim_metric_not_implicit(self):
  data={'question':'2024-01-01과2024-01-02 일반 일평균 비교','claim':{'direction':'increase'}}
  with self.assertRaises(HTTPError) as c:urlopen(Request(self.base+'/api/claim-plan',data=json.dumps(data).encode()))
  self.assertEqual(c.exception.code,400)
 def test_claim_standardization_not_automatic(self):
  data={'question':'2024-01-01과2024-01-02 일반 일평균 비교','claim':{'metric':'weekday_standardized','direction':'increase'}}
  with self.assertRaises(HTTPError) as c:urlopen(Request(self.base+'/api/claim-plan',data=json.dumps(data).encode()))
  self.assertEqual(c.exception.code,400)
 def test_claim_direction_changed_requires_new_plan(self):
  data={'question':'2024-01-01과2024-01-02 일반 일평균 비교','claim':{'metric':'total','direction':'equal'}}
  with urlopen(Request(self.base+'/api/claim-plan',data=json.dumps(data).encode())) as r:plan=json.load(r)
  data['claim']['direction']='increase'
  with self.assertRaises(HTTPError) as c:urlopen(Request(self.base+'/api/claim-check',data=json.dumps({**data,'expected_plan':plan}).encode()))
  self.assertEqual(c.exception.code,400)
