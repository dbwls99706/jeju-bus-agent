import json
import os
import unittest
from unittest.mock import Mock, patch
import quota as q

ENV={'QUOTA_REDIS_REST_URL':'https://example.upstash.io','QUOTA_REDIS_REST_TOKEN':'test-not-secret',
     'QUOTA_NAMESPACE':'global-budget-1','QUOTA_LIFETIME_LIMIT':'1000','QUOTA_DAILY_LIMIT':'100','QUOTA_MINUTE_LIMIT':'10'}


class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,ENV,clear=True);self.env.start()
        self.patch=patch.object(q,'_post',return_value={'result':[1,1,1,1]});self.post=self.patch.start()
    def tearDown(self):self.patch.stop();self.env.stop()
    def test_configuration_does_not_call_network(self):
        c=q.QuotaConfig.from_env();q.RedisQuota(c);self.post.assert_not_called()
        self.assertNotIn('test-not-secret',repr(c))
    def test_missing_config_fail_closed(self):
        for key in ENV:
            with self.subTest(key=key),patch.dict(os.environ,{key:''}):
                with self.assertRaises(q.QuotaUnavailable):q.RedisQuota.from_env()
        self.post.assert_not_called()
    def test_bad_limits(self):
        for value in ('0','-1','1.2','1e3',' 10','2147483648','true'):
            with patch.dict(os.environ,{'QUOTA_LIFETIME_LIMIT':value}):
                with self.assertRaises(q.QuotaUnavailable):q.RedisQuota.from_env()
        with patch.dict(os.environ,{'QUOTA_MINUTE_LIMIT':'101'}):
            with self.assertRaises(q.QuotaUnavailable):q.RedisQuota.from_env()
        self.post.assert_not_called()
    def test_bad_url_namespace_and_token(self):
        for value in ('http://example.com','https://user:pass@example.com','https://example.com/path','https://example.com?key=secret',
                      'https://127.0.0.1','https://localhost','https://x.local','https://example.com:8080','https://example.com#frag'):
            with patch.dict(os.environ,{'QUOTA_REDIS_REST_URL':value}):
                with self.assertRaises(q.QuotaUnavailable):q.RedisQuota.from_env()
        for key,value in [('QUOTA_NAMESPACE','x:{reset}'),('QUOTA_REDIS_REST_TOKEN','secret\r\nextra')]:
            with patch.dict(os.environ,{key:value}):
                with self.assertRaises(q.QuotaUnavailable):q.RedisQuota.from_env()
        self.post.assert_not_called()
    def test_atomic_command_and_global_keys(self):
        adapter=q.RedisQuota.from_env();self.assertIs(adapter.reserve_call(),True)
        self.post.assert_called_once();cmd=self.post.call_args.args[1]
        self.assertEqual(cmd[0],'EVAL');self.assertEqual(cmd[2],'3');self.assertEqual(cmd[6:],['1000','100','10'])
        self.assertTrue(all('{global-budget-1}' in key for key in cmd[3:6]))
        self.assertIn("redis.call('TIME')",cmd[1]);self.assertIn("redis.call('INCR'",cmd[1])
        self.assertNotIn('EXPIRE',cmd[1]);self.assertNotIn('DEL',cmd[1])
    def test_each_limit_rejects(self):
        for reason in ('lifetime','daily','minute'):
            self.post.return_value={'result':[0,reason]};self.assertIs(q.RedisQuota.from_env().reserve_call(),False)
    def test_provider_errors_and_invalid_results(self):
        adapter=q.RedisQuota.from_env()
        for result in ({'error':'secret'}, {}, {'result':True}, {'result':[1]}, {'result':[True,1,1,1]},
                       {'result':[1,1001,1,1]}, {'result':[1,1,1,11]}, {'result':[1,1,2,1]}, {'result':[0,'other']}, None):
            self.post.return_value=result
            with self.assertRaises(q.QuotaUnavailable):adapter.reserve_call()
    def test_ambiguous_network_failure_never_retries(self):
        self.post.side_effect=RuntimeError('secret-token-and-provider-body')
        with self.assertRaises(q.QuotaUnavailable) as err:q.RedisQuota.from_env().reserve_call()
        self.assertNotIn('secret',str(err.exception));self.post.assert_called_once()
    def test_mock_http_no_real_network(self):
        self.patch.stop()
        try:
            response=Mock();response.status=200;response.read.return_value=b'{"result":[1,1,1,1]}'
            context=Mock();context.__enter__=Mock(return_value=response);context.__exit__=Mock(return_value=False)
            opener=Mock();opener.open.return_value=context
            with patch.object(q,'build_opener',return_value=opener) as build:
                self.assertIs(q.RedisQuota.from_env().reserve_call(),True)
                req=opener.open.call_args.args[0]
                self.assertEqual(req.full_url,'https://example.upstash.io');self.assertEqual(req.method,'POST')
                self.assertEqual(opener.open.call_args.kwargs,{'timeout':5})
                self.assertIsInstance(build.call_args.args[0],q._NoRedirect)
                self.assertEqual(json.loads(req.data)[0],'EVAL');response.read.assert_called_once_with(8193)
        finally:self.post=self.patch.start()


if __name__=='__main__':unittest.main()
