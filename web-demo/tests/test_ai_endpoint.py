import os
import unittest
from unittest.mock import Mock, patch
import app as web
from openai_planner import PlannerUnavailable


class AIEndpointTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'DATA_MODE':'synthetic','AI_ENABLED':'0'},clear=True);self.env.start()
        self.client=web.app.test_client()
        self.patcher=patch.object(web,'classify_question',return_value='weekday');self.classifier=self.patcher.start()
        self.payload={'question':'이번달 일반만 요일별로 보고 싶어','start_date':'2024-01-01','end_date':'2024-02-29','user_type':'일반','metric':'daily','scope_ack':True}
    def tearDown(self):self.patcher.stop();self.env.stop()
    def post(self,payload=None):return self.client.post('/api/ai-plan',json=self.payload if payload is None else payload)
    def test_disabled_does_not_call(self):
        self.assertEqual(self.post().status_code,503);self.classifier.assert_not_called()
        self.assertFalse(self.client.get('/api/catalog').json['ai_enabled'])
    def test_scope_ack_mandatory(self):
        for value in (None,False,1,'true'):
            self.assertEqual(self.post({**self.payload,'scope_ack':value}).status_code,400)
        self.classifier.assert_not_called()
    def test_invalid_question_or_filters_before_call(self):
        cases=[{'question':'x'*301},{'start_date':'2023-01-01'},{'end_date':'2024-02-30'},
               {'user_type':'unknown'},{'metric':'bad'},{'start_date':'2024-02-29','end_date':'2024-01-01'}]
        with patch.object(web,'ai_ready',return_value=True):
            for bad in cases:self.assertEqual(self.post({**self.payload,**bad}).status_code,400)
        self.classifier.assert_not_called()
    def test_success_returns_approvable_plan_without_second_ai_call(self):
        with patch.object(web,'ai_ready',return_value=True),patch.object(web.RedisQuota,'from_env',return_value=Mock(reserve_call=Mock(return_value=True))):
            response=self.post()
        self.assertEqual(response.status_code,200,response.text)
        data=response.json;self.assertIs(data['ai_executed'],True)
        self.assertEqual(data['plan']['start_date'],'2024-01-01')
        self.assertEqual(data['plan']['end_date'],'2024-02-29')
        self.assertEqual(data['plan']['dimension'],'weekday')
        self.classifier.assert_called_once()
        self.assertEqual(self.classifier.call_args.args,(self.payload['question'],))
        self.assertEqual(set(self.classifier.call_args.kwargs),{'reserve_call'})
        analysis=self.client.post('/api/analyze',json={**data['canonical_request'],'expected_plan':data['plan']})
        self.assertEqual(analysis.status_code,200,analysis.text)
        self.classifier.assert_called_once()
    def test_reject_and_unsupported_metric(self):
        with patch.object(web,'ai_ready',return_value=True),patch.object(web.RedisQuota,'from_env',return_value=Mock()):
            self.classifier.return_value='reject';self.assertEqual(self.post().status_code,422)
            self.classifier.return_value='weekday';self.assertEqual(self.post({**self.payload,'metric':'hourly'}).status_code,422)
    def test_provider_fail_safe(self):
        self.classifier.side_effect=PlannerUnavailable('DO_NOT_LEAK')
        with patch.object(web,'ai_ready',return_value=True),patch.object(web.RedisQuota,'from_env',return_value=Mock()):r=self.post()
        self.assertEqual(r.status_code,503);self.assertNotIn('DO_NOT_LEAK',r.text);self.classifier.assert_called_once()
    def test_html_has_optin_and_privacy_notice(self):
        html=self.client.get('/').text
        self.assertIn('id="ai-scope-ack"',html);self.assertIn('질문만 OpenAI로 전송',html)
        self.assertIn('질문 속 날짜·유형·기타 조건은 적용하지 않고',html)


if __name__=='__main__':unittest.main()
