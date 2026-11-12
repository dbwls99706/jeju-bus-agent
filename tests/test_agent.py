import unittest,os,csv,tempfile
from pathlib import Path
from unittest.mock import patch
import agent,planner
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'bus.csv'
  with self.p.open('w') as f:
   w=csv.writer(f);w.writerow(['base_date','day_of_week','base_hour','user_type','user_count'])
   for day,weekday in [('20240101','월'),('20240102','화')]:
    for slot in agent.SLOTS:
     w.writerow([day,weekday,slot,'일반',60 if slot=='01시-06시' else 30])
     if not(day=='20240102' and slot=='22시-24시'):w.writerow([day,weekday,slot,'경로',10])
  self.env=patch.dict(os.environ,{'BUS_DATA_PATH':str(self.p),'BUS_MODEL_DIR':''});self.env.start();self.h=patch('agent.EXPECTED_SHA256','');self.h.start();agent.read_cached.cache_clear()
 def tearDown(self):self.env.stop();self.h.stop();self.tmp.cleanup();agent.read_cached.cache_clear()
 def test_catalog(self):self.assertEqual(agent.catalog()['missing_combinations'],1)
 def test_total(self):self.assertEqual(agent.analyze('시간')['stats']['total'],480)
 def test_normalization(self):self.assertEqual([r['value'] for r in agent.analyze('시간')['table']],[10]*7)
 def test_general_complete(self):self.assertEqual(agent.analyze('시간')['stats']['coverage'],1)
 def test_missing(self):
  r=agent.analyze('시간',user_type='전체');self.assertEqual(r['stats']['missing_combinations'],1);self.assertTrue(any('실제 평균의 추정치가 아닙니다' in w for w in r['warnings']))
 def test_date_filter(self):self.assertEqual(agent.analyze('시간','2024-01-01','2024-01-01')['stats']['rows'],7)
 def test_invalid_dates(self):
  with self.assertRaises(ValueError):agent.analyze('시간','2024-01-02','2024-01-01')
 def test_range_outside(self):
  with self.assertRaises(ValueError):agent.analyze('시간','2023-01-01')
 def test_invalid_type(self):
  with self.assertRaises(ValueError):agent.analyze('시간',user_type='unknown')
 def test_empty(self):
  with self.assertRaises(ValueError):agent.analyze('')
 def test_type_comparison(self):self.assertEqual(len(agent.analyze('유형 비교')['table']),2)
 def test_weekday_missing_days_not_zero(self):
  r=agent.analyze('요일');self.assertIsNone(r['table'][2]['value'])
 def test_unsupported(self):
  with self.assertRaises(planner.QuestionScopeError):agent.analyze('혼잡한 정류장')
 def test_repeat(self):self.assertEqual(agent.analyze('시간'),agent.analyze('시간'))
 def test_bad_hash(self):
  agent.read_cached.cache_clear()
  with patch('agent.EXPECTED_SHA256','wrong'):
   with self.assertRaises(ValueError):agent.load()
 def test_duplicate(self):
  with self.p.open('a') as f:f.write('20240101,월,01시-06시,일반,60\n')
  with self.assertRaises(ValueError):agent.load()
 def test_guard(self):
  with patch('planner.local_plan',return_value='month'):self.assertEqual(planner.plan('시간 비교')[:2],('time','rules_guarded'))
 def test_ai_route(self):
  with patch('planner.local_plan',return_value='weekday'):self.assertEqual(planner.plan('일주일 중 언제?')[:2],('weekday','local_ai'))
 def test_ai_error(self):
  with patch('planner.local_plan',side_effect=ValueError()):self.assertEqual(planner.plan('요일 비교')[1],'rules')

 def test_unobserved_group_null(self):
  r=agent.analyze('시간','2024-01-02','2024-01-02','경로')['table'][-1]
  self.assertEqual(r['observed_cells'],0)
  self.assertEqual(r['coverage'],0)
  self.assertIsNone(r['total']);self.assertIsNone(r['value']);self.assertIsNone(r['per_hour'])
 def test_combined_scope_refused(self):
  with self.assertRaises(planner.QuestionScopeError):agent.analyze('주말과 평일의 아침 시간 비교')
 def test_unhandled_filter_refused(self):
  with self.assertRaises(planner.QuestionScopeError):agent.analyze('아침만 알려줘')

 def test_comparability_gate(self):
  self.assertTrue(agent.analyze('시간')['quality']['comparable'])
  self.assertFalse(agent.analyze('시간',user_type='전체')['quality']['comparable'])
 def test_partial_month(self):
  self.assertTrue(any('부분월' in x for x in agent.analyze('월별')['insights']))
 def test_date_text_refused(self):
  with self.assertRaises(planner.QuestionScopeError):agent.analyze('2024년 월별 추이')
 def test_multi_type_month_refused(self):
  with self.assertRaises(planner.QuestionScopeError):agent.analyze('일반과 경로의 월별 추이')

 def test_weekday_weekend_aggregation(self):
  r=agent.analyze('평일과 주말 비교')
  self.assertEqual([x['label'] for x in r['table']],['평일','주말'])
  self.assertEqual(r['table'][0]['total'],480)
  self.assertEqual(r['table'][0]['value'],240)
  self.assertIsNone(r['table'][1]['value'])

 def test_explicit_sum_bucket(self):
  r=agent.analyze('일반과 경로 합산')
  self.assertEqual(len(r['table']),1);self.assertEqual(r['table'][0]['total'],610);self.assertEqual(r['chart']['values'],[610]);self.assertEqual(r['chart']['unit'],'기록된 승차 합계(명)')

 def test_total_metric_not_normalized(self):
  r=agent.analyze('시간대별 승차 합계');self.assertEqual(r['chart']['values'][0],120);self.assertEqual(r['table'][0]['per_hour'],10);self.assertEqual(r['chart']['unit'],'기록된 승차 합계(명)')
 def test_daily_mean_not_hourly(self):self.assertEqual(agent.analyze('시간대별 일평균')['chart']['values'][0],60)

 def test_combined_population_daily_average(self):
  r=agent.analyze('일반과 경로 합산 일평균');self.assertEqual(r['chart']['values'],[305]);self.assertEqual(r['chart']['unit'],'기록값 환산 명/일')

 def test_lowest_insight(self):
  for q in ['요일별 가장 낮은 기록','시간대별 가장 낮은 기록']:
   r=agent.analyze(q);self.assertIn('가장 낮은 그룹',r['insights'][0]);self.assertNotIn('높은 그룹',r['insights'][0])
 def test_daily_overview_mean(self):
  r=agent.analyze('일반 하루 평균 알려줘')
  self.assertEqual(len(r['table']),1);self.assertEqual(r['table'][0]['value'],240);self.assertIn('240.000명/일',r['insights'][0])

 def test_unobserved_summary_is_null_not_zero(self):
  with self.p.open('a') as f:f.write('20240102,화,01시-06시,기타,10\n')
  agent.read_cached.cache_clear()
  for metric in ['하루 평균','총합','총계','합계']:
   with self.subTest(metric=metric):
    r=agent.analyze('2024-01-01 기타 '+metric+' 알려줘')
    self.assertIsNone(r['stats']['total']);self.assertIsNone(r['table'][0]['value']);self.assertIsNone(r['table'][0]['total']);self.assertFalse(r['quality']['comparable']);self.assertIn('미관측',r['insights'][0])
 def test_observed_zero_summary_still_zero(self):
  with self.p.open('a') as f:
   for slot in agent.SLOTS:f.write('20240101,월,'+slot+',기타,0\n')
  agent.read_cached.cache_clear()
  r=agent.analyze('2024-01-01 기타 하루 평균 알려줘')
  self.assertEqual(r['stats']['total'],0);self.assertEqual(r['table'][0]['value'],0);self.assertTrue(r['quality']['comparable'])
