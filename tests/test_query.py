import unittest
from unittest.mock import patch
from query import interpret
from planner import QuestionScopeError
META={'min_date':'2023-12-25','max_date':'2025-10-26','user_types':['일반','경로','기타','어린이','유공 동반','유공 일반','장애 동반','장애 일반','청소년']}
class QueryTests(unittest.TestCase):
 def q(self,s):
  with patch('planner.local_plan',return_value=None):return interpret(s,None,None,'일반',META)
 def test_senior(self):self.assertEqual(self.q('경로 이용객은 언제 많이 타나요?')['user_types'],['경로'])
 def test_youth(self):self.assertEqual(self.q('청소년의 시간대별 승차')['user_types'],['청소년'])
 def test_longest_type(self):self.assertEqual(self.q('장애 일반의 시간대별 승차')['user_types'],['장애 일반'])
 def test_generic_not_type(self):self.assertEqual(self.q('일반적인 시간대 분석')['user_types'],['일반'])
 def test_iso_range(self):
  p=self.q('2024-01-01부터 2024-01-31까지 시간대 비교');self.assertEqual((p['start_date'],p['end_date']),('2024-01-01','2024-01-31'))
 def test_korean_month(self):
  p=self.q('2024년 2월 시간대');self.assertEqual((p['start_date'],p['end_date']),('2024-02-01','2024-02-29'))
 def test_year(self):self.assertEqual(self.q('2024년 월별 추이')['end_date'],'2024-12-31')
 def test_four_dates(self):
  p=self.q('2024-01-01~2024-01-07과 2024-02-05~2024-02-11 비교');self.assertEqual(p['kind'],'period_compare');self.assertEqual(len(p['periods']),2)
 def test_two_months(self):self.assertEqual(self.q('2024년 1월과 2월 비교')['periods'][1]['end'],'2024-02-29')
 def test_outside_not_truncated(self):
  with self.assertRaises(QuestionScopeError):self.q('2025년 월별 추이')
 def test_invalid_date(self):
  with self.assertRaises(QuestionScopeError):self.q('2024-02-31 시간대')
 def test_ambiguous_relative(self):
  with self.assertRaises(QuestionScopeError):self.q('지난달 시간대')
 def test_overlapping(self):
  with self.assertRaises(QuestionScopeError):self.q('2024-01-01~2024-01-10과 2024-01-05~2024-01-15 비교')
 def test_multiple_types_within_type_dimension(self):
  self.assertEqual(self.q('일반과 경로 비교')['user_types'],['일반','경로'])

 def test_period_types_not_silently_merged(self):
  with self.assertRaises(QuestionScopeError):self.q('일반과 경로의 2024년 1월과 2월 비교')
 def test_period_time_condition_not_dropped(self):
  with self.assertRaises(QuestionScopeError):self.q('2024년 1월과 2월 주말 비교')

 def test_plural_type(self):self.assertEqual(self.q('청소년들의 시간대별 기록')['user_types'],['청소년'])
 def test_ambiguous_demographic_not_defaulted(self):
  with self.assertRaises(QuestionScopeError):self.q('학생들은 언제 많이 타나요?')

 def test_half_year_not_full_year(self):
  with self.assertRaises(QuestionScopeError):self.q('2024년 상반기 시간대별 분석')
 def test_exclusion_not_inclusion(self):
  with self.assertRaises(QuestionScopeError):self.q('경로를 제외하고 시간대별 분석')
 def test_all_users_not_default(self):self.assertEqual(self.q('전체 이용자의 시간대별 분석')['user_types'],META['user_types'])
 def test_after_not_single_day(self):
  with self.assertRaises(QuestionScopeError):self.q('2024년1월1일 이후')
 def test_open_from_not_single_day(self):
  with self.assertRaises(QuestionScopeError):self.q('2024-01-01부터 시간대별 분석')
 def test_all_and_specific_ambiguous(self):
  with self.assertRaises(QuestionScopeError):self.q('전체 이용자와 경로의 시간대 비교')

 def test_unsupported_conditions_do_not_disappear(self):
  for q in ['일반은 빼주세요 시간대','경로 아니고 일반의 시간대','2024년1월 첫주 분석','2024-01-01 전후 비교','공휴일 승차량','비 오는 날 시간대']:
   with self.subTest(question=q):
    with self.assertRaises(QuestionScopeError):self.q(q)

 def test_age_not_fare_type(self):
  with self.assertRaises(QuestionScopeError):self.q('나이대별 승차 비교')

 def test_only_type_particle(self):
  self.assertEqual(self.q('경로만 시간대별로 보여줘')['user_types'],['경로'])
  self.assertEqual(self.q('청소년만 시간대 비교')['user_types'],['청소년'])
 def test_short_date_tail_not_dropped(self):
  with self.assertRaises(QuestionScopeError):self.q('2024년 1월 1일~7일 시간대 비교')
 def test_unsupported_weather_and_recent(self):
  for q in ['맑은 날의 승차량','최근 승차량이 증가했어?']:
   with self.subTest(question=q):
    with self.assertRaises(QuestionScopeError):self.q(q)
 def test_unparsed_type_suffix_not_ignored(self):
  with self.assertRaises(QuestionScopeError):self.q('청소년계층 시간대')
 def test_route_not_senior_fare(self):
  with self.assertRaises(QuestionScopeError):self.q('경로를 추천해줘')

 def test_closed_grammar_unknown_conditions_refused(self):
  for q in ['지난주 시간대별 승차','이번 달 승차량','일반과 경로가 아닌 어린이 비교','2024-01-01 및 2024-01-07 시간대 분석','승차 인원이1000명 넘는 시간대','1000명 이상 시간대','특정 행사일 시간대']:
   with self.subTest(question=q):
    with self.assertRaises(QuestionScopeError):self.q(q)

 def test_supported_synonyms_no_wrong_default(self):
  for q,expected in [('일주일 중 어느 날의 기록이 높아?','weekday'),('한 달씩 묶어서 변화 그래프를 그려 주세요','month'),('월 단위로 묶은 평균이 궁금합니다','month'),('이 자료에서 이용자 구분 간 차이를 보고 싶어요','user_type')]:
   with self.subTest(question=q):self.assertEqual(self.q(q)['dimension'],expected)

 def test_four_list_dates_not_ranges(self):
  with self.assertRaises(QuestionScopeError):self.q('2024-01-01 및 2024-01-07과 2024-02-01 및 2024-02-07 비교')

 def test_all_boardings_not_general(self):self.assertEqual(self.q('전체 승차량')['user_types'],META['user_types'])
 def test_single_group_conditions_not_dropped(self):
  for q in ['월요일 승차량','평일 승차량','아침 승차량']:
   with self.subTest(question=q):
    with self.assertRaises(QuestionScopeError):self.q(q)
 def test_weekday_weekend_grouping(self):self.assertEqual(self.q('평일과 주말 비교')['weekday_grouping'],'weekday_vs_weekend')

 def test_month_range_not_two_month_comparison(self):
  p=self.q('2024년 1월부터 2024년 3월까지 비교')
  self.assertEqual(p['kind'],'single');self.assertEqual(p['start_date'],'2024-01-01');self.assertEqual(p['end_date'],'2024-03-31')
 def test_compact_month_synonyms(self):
  for q in ['월단위로 분석해줘','한달씩 비교해줘']:self.assertEqual(self.q(q)['dimension'],'month')
 def test_explicit_sum_not_type_comparison(self):self.assertEqual(self.q('일반과 경로 합산')['dimension'],'summary')

 def test_open_month_and_year_refused(self):
  for q in ['2024년 1월부터 시간대별 분석','2024년 1월까지 시간대별 분석','2024년부터 시간대 분석']:
   with self.subTest(question=q):
    with self.assertRaises(QuestionScopeError):self.q(q)
 def test_explicit_totals_metric(self):
  for q in ['2024년 월별 합계','시간대별 승차 합계']:self.assertEqual(self.q(q)['metric'],'total')
 def test_explicit_daily_mean(self):self.assertEqual(self.q('시간대별 일평균')['metric'],'daily_mean')
 def test_mixed_metric_refused(self):
  with self.assertRaises(QuestionScopeError):self.q('월별 합계와 평균')

 def test_overall_boardings_summary(self):self.assertEqual(self.q('전체 승차량 알려줘')['dimension'],'summary')
 def test_hourly_request(self):self.assertEqual(self.q('시간대별 시간당 평균')['metric'],'hourly_daily_mean')

 def test_sum_population_daily_metric(self):
  for q in ['일반과 경로 합산 일평균','일반과 경로 하루 평균 합산','일반과 경로 합산 평균']:
   with self.subTest(question=q):self.assertEqual(self.q(q)['metric'],'daily_mean')
 def test_period_hourly_metric_not_dropped(self):
  with self.assertRaises(QuestionScopeError):self.q('2024년1월과2월 시간당 평균 비교')

 def test_explicit_group_not_collapsed_by_total(self):
  for q,expected in [('평일과 주말 합계','weekday'),('월마다 합계','month'),('연중 추이 합계','month')]:
   with self.subTest(question=q):self.assertEqual(self.q(q)['dimension'],expected)
 def test_hourly_daily_unit(self):self.assertEqual(self.q('시간대별 시간당 일평균')['metric'],'hourly_daily_mean')
 def test_total_hourly_conflict(self):
  with self.assertRaises(QuestionScopeError):self.q('시간대별 시간당 합계')

 def test_period_extra_grouping_not_silently_dropped(self):
  for condition in ['요일별','유형별','시간별','출근 기록','밤 기록','시간대별','평일과 주말','월별','구간마다','이용자 구분']:
   with self.subTest(condition=condition):
    with self.assertRaises(QuestionScopeError):self.q('2024년 1월과 2월 '+condition+' 비교')
 def test_period_supported_population_preserved(self):
  p=self.q('2024년 1월과 2월 경로 일평균 비교')
  self.assertEqual(p['kind'],'period_compare');self.assertEqual(p['user_types'],['경로']);self.assertEqual(p['metric'],'daily_mean')
 def test_period_all_population_preserved(self):
  p=self.q('2024년 1월과 2월 전체 이용자 비교')
  self.assertEqual(p['kind'],'period_compare');self.assertEqual(p['user_types'],META['user_types'])
 def test_four_date_period_night_not_eligible(self):
  with self.assertRaises(QuestionScopeError):self.q('2024-01-01~2024-01-07과 2024-02-05~2024-02-11 밤 기록 비교')

 def test_daily_series_not_time_bins(self):
  for wording in ['하루마다','날마다','일별','날짜별','매일']:
   with self.subTest(wording=wording):
    with self.assertRaises(QuestionScopeError):self.q('2024년 1월 기록 '+wording+' 비교')
 def test_period_daily_series_not_aggregate(self):
  with self.assertRaises(QuestionScopeError):self.q('2024-01-01~2024-01-07과 2024-02-05~2024-02-11 하루마다 비교')
 def test_population_sum_synonyms(self):
  for wording in ['합산','합쳐','합쳐서','합해']:
   with self.subTest(wording=wording):
    p=self.q('일반과 경로 '+wording+' 보여줘')
    self.assertEqual(p['dimension'],'summary');self.assertEqual(p['metric'],'total');self.assertEqual(p['user_types'],['일반','경로'])
 def test_population_sum_synonym_daily_mean(self):
  p=self.q('일반과 경로 합해 일평균 보여줘')
  self.assertEqual(p['dimension'],'summary');self.assertEqual(p['metric'],'daily_mean')

 def test_weekday_not_confused_with_daily(self):self.assertEqual(self.q('요일별 비교')['dimension'],'weekday')

 def test_daily_overview_all_time(self):
  p=self.q('2024년 1월 일반 하루 평균 알려줘')
  self.assertEqual(p['dimension'],'summary');self.assertEqual(p['metric'],'daily_mean')
 def test_lowest_intent_preserved(self):
  for dimension in ['요일별','시간대별']:
   p=self.q('2024년 1월 일반 '+dimension+' 가장 낮은 기록 알려줘')
   self.assertEqual(p['extremum'],'min')

 def test_total_synonyms_are_summary(self):
  for term in ['총합','총계','합계']:
   p=self.q('2024년 1월 일반 '+term+' 알려줘')
   self.assertEqual(p['dimension'],'summary');self.assertEqual(p['metric'],'total')
 def test_both_extrema_explicit_refusal(self):
  with self.assertRaises(QuestionScopeError):self.q('시간대별 최고와 최저')

 def test_cross_dimension_synonyms_fail_closed(self):
  for q in ['2024년 1월 일반 시간대별 추이','2024년 1월 일반 유형별 추이','하루 중 요일별 비교']:
   with self.subTest(question=q):
    with self.assertRaises(QuestionScopeError):self.q(q)
 def test_dimension_cues_same_in_router_and_guard(self):
  from planner import DIMENSION_CUES,dimension_tags,rule_plan,validate_scope
  for dim,cues in DIMENSION_CUES.items():
   for cue in cues:
    with self.subTest(cue=cue):
     self.assertIn(dim,dimension_tags(cue));self.assertEqual(rule_plan(cue),dim);validate_scope(cue)
 def test_all_cross_dimension_cue_pairs_rejected(self):
  from planner import DIMENSION_CUES,validate_scope
  from itertools import combinations
  for (a,cues_a),(b,cues_b) in combinations(DIMENSION_CUES.items(),2):
   for ca in cues_a:
    for cb in cues_b:
     with self.subTest(a=ca,b=cb):
      with self.assertRaises(QuestionScopeError):validate_scope(ca+' '+cb+' 비교')

 def test_time_group_survives_range_and_sum_defaults(self):
  for wording in ['하루 중','구간마다','시간대별']:
   for prefix in ['2024년 1월 일반 ','2024년 1월부터 3월까지 일반 ']:
    for metric in ['비교','합계']:
     with self.subTest(wording=wording,prefix=prefix,metric=metric):
      p=self.q(prefix+wording+' '+metric)
      self.assertEqual(p['dimension'],'time')
      self.assertEqual(p['metric'],'total' if metric=='합계' else 'hourly_daily_mean')
 def test_weekday_group_survives_continuous_month_range(self):
  for wording in ['평일과 주말','일주일']:
   p=self.q('2024년 1월부터 3월까지 일반 '+wording+' 비교')
   self.assertEqual(p['dimension'],'weekday')
  self.assertEqual(self.q('2024년 1월부터 3월까지 일반 평일과 주말 비교')['weekday_grouping'],'weekday_vs_weekend')
 def test_slot_weekday_cross_group_refused(self):
  with self.assertRaises(QuestionScopeError):self.q('2024년 1월부터 3월까지 일반 구간마다 요일별 비교')
 def test_guided_goal_metric_matrix(self):
  for dim,word in [('time','시간대별'),('weekday','요일별'),('month','월별'),('user_type','유형별'),('summary','')]:
   for metric,term in [('total','합계'),('daily_mean','일평균')]+([('hourly_daily_mean','시간당 평균')] if dim=='time' else []):
    with self.subTest(goal=dim,metric=metric):
     p=self.q('전체 이용자 '+word+' '+term)
     self.assertEqual(p['dimension'],dim);self.assertEqual(p['metric'],metric);self.assertEqual(p['user_types'],META['user_types'])

 def test_static_example_buttons_supported(self):
  import re
  from pathlib import Path
  html=(Path(__file__).resolve().parents[1]/'static/index.html').read_text()
  for q in re.findall(r'class="example">([^<]+)</button>',html):
   with self.subTest(question=q):self.q(q)

 def test_grouped_sum_synonyms_use_total(self):
  for axis in ['시간대별','요일별','월별','유형별']:
   for term in ['합산','합쳐','합해','합계','총합','총계']:
    with self.subTest(axis=axis,term=term):
     p=self.q('2024년 1월 일반 '+axis+' '+term)
     self.assertEqual(p['metric'],'total')
 def test_grouped_population_sum_explicit_mean_preserved(self):
  for term in ['합산','합쳐','합해']:
   p=self.q('시간대별 '+term+' 일평균')
   self.assertEqual(p['metric'],'daily_mean')

 def test_value_sorted_request_refused(self):
  for q in ['많은 요일 순서대로','시간대별 낮은 순서대로','유형별 큰 순서대로']:
   with self.subTest(question=q):
    with self.assertRaises(QuestionScopeError):self.q(q)

 def test_period_sum_requires_explicit_daily_metric(self):
  for term in ['합산','합쳐','합해','합계','총합','총계']:
   with self.subTest(term=term):
    with self.assertRaises(QuestionScopeError):self.q('2024년 1월과 2월 일반 '+term+' 비교')
 def test_period_population_sum_daily_mean_supported(self):
  p=self.q('2024년 1월과 2월 일반과 경로 합산 일평균 비교')
  self.assertEqual(p['kind'],'period_compare');self.assertEqual(p['metric'],'daily_mean');self.assertEqual(p['user_types'],['일반','경로'])
 def test_weekday_start_order_clear_message(self):
  with self.assertRaisesRegex(QuestionScopeError,'요일 시작점'):self.q('2024년 1월 일반 월요일부터 순서대로 요일 비교')

 def test_weekday_group_note_matches_metric(self):
  total=self.q('2024년 1월 일반 평일과 주말 합계 비교')
  self.assertEqual(total['metric'],'total');self.assertTrue(any('각 그룹의 관측 합계' in n for n in total['notes']))
  self.assertFalse(any('나눈' in n for n in total['notes']))
  mean=self.q('2024년 1월 일반 평일과 주말 일평균 비교')
  self.assertEqual(mean['metric'],'daily_mean');self.assertTrue(any('해당 날짜수로 나눈 기록 일평균' in n for n in mean['notes']))

 def test_standardization_explicit_plan(self):
  p=self.q('2024년1월과2월 일반 요일 표준화 일평균 비교')
  self.assertEqual(p['comparison_method'],'weekday_standardized');self.assertEqual(p['kind'],'period_compare')
  self.assertEqual(p['periods'][0]['end'],'2024-01-31');self.assertIn('1/7',' '.join(p['notes']))
 def test_standardization_single_period_refused(self):
  with self.assertRaises(QuestionScopeError):self.q('2024년1월 요일 표준화 일평균')
 def test_standardization_cross_conditions_refused(self):
  with self.assertRaises(QuestionScopeError):self.q('2024년1월과2월 일반 요일 표준화 시간대별 비교')
 def test_standardization_total_refused(self):
  with self.assertRaises(QuestionScopeError):self.q('2024년1월과2월 일반 요일 표준화 합계 비교')
