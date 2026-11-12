"""Optional real-data integration QA; does not copy or transmit the source."""
import os
import unittest
from unittest.mock import patch
from pathlib import Path
from app import app
import agent

@unittest.skipUnless(os.getenv('TEST_REAL_CSV'), 'Set TEST_REAL_CSV to an authorized local source')
class RealModeTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'DATA_MODE': 'real'})
        self.env.start()
        self.source = patch('agent.source_path', return_value=Path(os.environ['TEST_REAL_CSV']))
        self.source.start()
        self.client = app.test_client()

    def tearDown(self):
        self.source.stop()
        self.env.stop()

    def test_catalog_is_real_and_ai_remains_disabled(self):
        response = self.client.get('/api/catalog')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['data_kind'], 'real')
        self.assertFalse(data['ai_enabled'])
        self.assertIn('37057', str(data))

    def test_home_distinguishes_real_data_from_ai(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('실제 제주 버스 승차 집계', html)
        self.assertIn('현재 AI 미사용', html)
        self.assertIn('<strong>과거 집계 37,057행 · 실시간 정보 아님</strong>', html)
        self.assertIn('<details><summary>자료와 분석 방식</summary>', html)
        self.assertIn('질문만 OpenAI로 전송', html)
        self.assertNotIn('실제 데이터·AI 없는 절차 시연', html)
        self.assertNotIn('local-csv-panel', html)
        self.assertNotIn('/static/local-csv.js', html)

    def test_raw_source_has_no_public_http_route(self):
        for path in ('/data/bus.csv', '/static/bus.csv', '/bus.csv'):
            self.assertEqual(self.client.get(path).status_code, 404)

if __name__ == '__main__':
    unittest.main()
