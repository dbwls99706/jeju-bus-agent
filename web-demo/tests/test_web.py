import unittest,os
from app import app
from unittest.mock import patch
class WebTests(unittest.TestCase):
 def setUp(self):
  self.env=patch.dict(os.environ,{'DATA_MODE':'synthetic'});self.env.start();self.addCleanup(self.env.stop);self.c=app.test_client()
 def test_home(self):
  r=self.c.get('/');self.assertEqual(r.status_code,200);self.assertIn('실제 데이터·AI 없는 절차 시연',r.text)
 def test_catalog(self):
  d=self.c.get('/api/catalog').json;self.assertEqual(d['data_kind'],'synthetic');self.assertFalse(d['ai_enabled']);self.assertEqual(d['rows'],840)
 def test_plan_and_analysis(self):
  d={'question':'2024년1월과2월 일반 일평균 비교'}
  p=self.c.post('/api/plan',json=d);self.assertEqual(p.status_code,200,p.text)
  r=self.c.post('/api/analyze',json={**d,'expected_plan':p.json});self.assertEqual(r.status_code,200,r.text);self.assertIn('합성',r.json['demo_notice'])
 def test_approval(self):self.assertEqual(self.c.post('/api/analyze',json={'question':'시간대별 비교'}).status_code,400)
 def test_mismatched_plan(self):self.assertEqual(self.c.post('/api/analyze',json={'question':'시간대별 비교','expected_plan':{}}).status_code,400)
 def test_origin(self):self.assertEqual(self.c.post('/api/plan',json={},headers={'Origin':'https://evil.test'}).status_code,403)
 def test_host(self):self.assertEqual(self.c.get('/',base_url='https://evil.test').status_code,403)
 def test_allowed_host(self):
  os.environ['PUBLIC_APP_HOST']='demo.vercel.app'
  self.assertEqual(self.c.get('/',base_url='https://demo.vercel.app').status_code,200)
  os.environ.pop('PUBLIC_APP_HOST')
 def test_body_limit(self):self.assertEqual(self.c.post('/api/plan',json={'question':'x'*20000}).status_code,413)
 def test_json_type(self):self.assertEqual(self.c.post('/api/plan',json=[]).status_code,400)
 def test_content_type(self):self.assertEqual(self.c.post('/api/plan',data='{}').status_code,415)
 def test_data_not_served(self):self.assertEqual(self.c.get('/data/synthetic.csv').status_code,404)
 def test_no_model(self):
  import planner
  os.environ['BUS_MODEL_DIR']='/does-not-exist'
  self.assertIsNone(planner.local_plan('시간대별 비교'));os.environ.pop('BUS_MODEL_DIR')
 def test_not_found(self):self.assertEqual(self.c.post('/api/run',json={}).status_code,404)
 def test_headers(self):self.assertIn("frame-ancestors 'none'",self.c.get('/').headers['Content-Security-Policy'])
if __name__=='__main__':unittest.main()
