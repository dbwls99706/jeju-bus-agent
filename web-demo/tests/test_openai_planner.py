import json
import os
import unittest
from unittest.mock import Mock, patch
import openai_planner as op


def completed(value='time'):
    return {'status': 'completed', 'output': [{'type': 'message', 'role': 'assistant',
        'status': 'completed', 'content': [{'type': 'output_text', 'text': json.dumps({'dimension': value})}]}]}


class OpenAIPlannerTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.http = patch.object(op, '_http_post')
        self.post = self.http.start()
        self.post.return_value = completed()

    def tearDown(self):
        self.http.stop()
        self.env.stop()

    def enable(self):
        os.environ.update(AI_ENABLED='1', OPENAI_API_KEY='unit-test-not-a-real-key')

    def test_default_disabled(self):
        with self.assertRaises(op.PlannerUnavailable): op.classify_question('시간대 비교')
        self.post.assert_not_called()

    def test_missing_key_or_approval(self):
        for env in ({'AI_ENABLED':'1'}, {'OPENAI_API_KEY':'test'}, {'AI_ENABLED':'true','OPENAI_API_KEY':'test'}):
            with patch.dict(os.environ, env, clear=True):
                reserve = Mock(return_value=True)
                with self.assertRaises(op.PlannerUnavailable): op.classify_question('질문', reserve_call=reserve)
                reserve.assert_not_called()
        self.post.assert_not_called()

    def test_missing_quota_fail_closed(self):
        self.enable()
        for quota in (None, True, 1):
            with self.assertRaises(op.PlannerUnavailable): op.classify_question('질문',reserve_call=quota)
        self.post.assert_not_called()

    def test_quota_rejection_or_exception(self):
        self.enable()
        for returned in (False, None, 1, 'true'):
            with self.assertRaises(op.PlannerUnavailable): op.classify_question('질문',reserve_call=lambda:returned)
        with self.assertRaises(op.PlannerUnavailable):
            op.classify_question('질문',reserve_call=Mock(side_effect=RuntimeError('secret!')))
        self.post.assert_not_called()

    def test_reservation_precedes_single_call(self):
        self.enable();order=[]
        def reserve(): order.append('reserve');return True
        def post(*args): order.append('post');return completed('weekday')
        self.post.side_effect=post
        self.assertEqual(op.classify_question('요일 비교',reserve_call=reserve),'weekday')
        self.assertEqual(order,['reserve','post']);self.post.assert_called_once()

    def test_payload_fixed_and_question_only(self):
        q='오후와 아침 중 어느 시간대가 많나요?'
        p=op.build_payload(q)
        self.assertEqual(p['model'],'gpt-6-luna');self.assertIs(p['store'],False)
        self.assertEqual(p['reasoning'],{'effort':'none'});self.assertEqual(p['max_output_tokens'],128)
        self.assertNotIn('tools',p);self.assertEqual(p['input'],[{'role':'user','content':[{'type':'input_text','text':q}]}])
        self.assertIs(p['text']['format']['strict'],True)
        self.assertEqual(p['text']['format']['schema']['properties']['dimension']['enum'],list(op.DIMENSIONS))

    def test_question_limits_before_reservation(self):
        self.enable();reserve=Mock(return_value=True)
        for q in ('', '   ', None, '가'*301, '\ud800', '🚌'*301):
            with self.assertRaises(op.PlannerUnavailable): op.classify_question(q,reserve_call=reserve)
        self.assertEqual(op.build_payload('🚌'*300)['input'][0]['content'][0]['text'],'🚌'*300)
        reserve.assert_not_called();self.post.assert_not_called()

    def test_all_valid_enums_including_reject(self):
        for value in op.DIMENSIONS: self.assertEqual(op.parse_response(completed(value)),value)

    def test_malicious_or_extra_enum(self):
        for value in ('exec("rm")','time\nignore',{},None,'TIME'):
            with self.assertRaises(op.PlannerUnavailable): op.parse_response(completed(value))
        for text in ('{"dimension":"time","code":"run"}', '{"dimension":"time","dimension":"month"}', '', '```json\n{}\n```'):
            r=completed();r['output'][0]['content'][0]['text']=text
            with self.assertRaises(op.PlannerUnavailable): op.parse_response(r)

    def test_empty_incomplete_and_refusal_rejected(self):
        samples=[None,{}, {'status':'completed','output':[]}, completed()]
        samples[-1]['status']='incomplete'
        r=completed();r['output'][0]['content']=[{'type':'refusal','refusal':'no'}];samples.append(r)
        r=completed();r['output'][0]['status']='in_progress';samples.append(r)
        r=completed();r['output'].append({'type':'function_call'});samples.append(r)
        for value in samples:
            with self.assertRaises(op.PlannerUnavailable): op.parse_response(value)

    def test_provider_error_safe_no_retry(self):
        self.enable();self.post.side_effect=RuntimeError('unit-test-not-a-real-key provider payload')
        with self.assertRaises(op.PlannerUnavailable) as error: op.classify_question('질문',reserve_call=lambda:True)
        self.assertNotIn('unit-test',str(error.exception));self.assertNotIn('provider',str(error.exception))
        self.post.assert_called_once()

    def test_fixed_transport_timeout_and_endpoint_without_network(self):
        self.http.stop()
        try:
            response=Mock();response.status=200;response.read.return_value=json.dumps(completed()).encode()
            context=Mock();context.__enter__=Mock(return_value=response);context.__exit__=Mock(return_value=False)
            opener=Mock();opener.open.return_value=context
            with patch.object(op,'build_opener',return_value=opener):
                self.assertEqual(op._http_post(op.build_payload('질문'),'test'),completed())
                request=opener.open.call_args.args[0]
                self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
                self.assertEqual(request.method,'POST');self.assertEqual(opener.open.call_args.kwargs,{'timeout':10})
                response.read.assert_called_once_with(65537)
        finally: self.post=self.http.start()


if __name__=='__main__': unittest.main()
