import unittest
from copy import deepcopy
from datetime import date,timedelta
from fractions import Fraction
from claim_check import validate_claim,check_claim
from period_compare import compare_periods,SLOTS,WEEKDAYS
from weekday_standardize import standardize_periods


def rows(days=60):
    out=[]
    for n in range(days):
        d=date(2024,1,1)+timedelta(days=n)
        for slot in SLOTS:
            out.append({'date':d,'weekday':WEEKDAYS[d.weekday()],'time':slot,'user_type':'일반','count':10 if n<31 else 20,'row':len(out)+2})
    return out


def compare(source=None,standard=False,**kw):
    f=standardize_periods if standard else compare_periods
    args=dict(rows=rows() if source is None else source,start_a='2024-01-01',end_a='2024-01-07',start_b='2024-02-05',end_b='2024-02-11',user_types=['일반'],sha='testhash',source={'name':'fixture'})
    args.update(kw)
    return f(**args)


class ClaimTests(unittest.TestCase):
    def check(self,result=None,metric='daily_mean',direction='increase'):
        return check_claim(compare() if result is None else result,{'metric':metric,'direction':direction})
    def test_supported(self):
        r=self.check();self.assertEqual(r['verdict'],'supported');self.assertEqual(r['evidence']['values'],[70,140]);self.assertFalse(r['ai_verdict'])
    def test_contradicted(self):self.assertEqual(self.check(direction='decrease')['verdict'],'contradicted')
    def test_equal_exact(self):
        r=self.check(compare(start_b='2024-01-08',end_b='2024-01-14'),direction='equal')
        self.assertEqual(r['verdict'],'supported');self.assertEqual(r['evidence']['exact_difference'],'0')
    def test_decrease(self):
        r=self.check(compare(start_a='2024-02-05',end_a='2024-02-11',start_b='2024-01-01',end_b='2024-01-07'),direction='decrease')
        self.assertEqual(r['verdict'],'supported')
    def test_total_diff_days_warning(self):
        r=self.check(compare(end_a='2024-01-14'),metric='total',direction='equal')
        self.assertEqual(r['verdict'],'supported');self.assertTrue(any('날짜 수가 다릅니다' in x for x in r['warnings']))
    def test_missing_indeterminate(self):
        r=self.check(compare(rows()[1:]))
        self.assertEqual(r['verdict'],'indeterminate');self.assertIsNone(r['evidence']['difference'])
    def test_unobserved_total_indeterminate(self):
        source=[x for x in rows() if x['date']>date(2024,1,7)]
        # Keep original bounds supported by another population, not fake zeros.
        source += [{**x,'user_type':'경로'} for x in rows() if x['date']<=date(2024,1,7)]
        r=self.check(compare(source),metric='total')
        self.assertEqual(r['verdict'],'indeterminate');self.assertIsNone(r['evidence']['values'])
    def test_weekday_mix_raw_refused(self):
        r=self.check(compare(end_a='2024-01-31',start_b='2024-02-01',end_b='2024-02-29'))
        self.assertEqual(r['verdict'],'indeterminate')
    def test_standardized(self):
        r=self.check(compare(standard=True,end_a='2024-01-31',start_b='2024-02-01',end_b='2024-02-29'),metric='weekday_standardized')
        self.assertEqual(r['verdict'],'supported');self.assertEqual(r['evidence']['exact_values'],['70','140']);self.assertIn('1/7',r['safe_statement'])
    def test_no_auto_standardization(self):
        source=compare(standard=True,end_a='2024-01-31',start_b='2024-02-01',end_b='2024-02-29')
        self.assertEqual(self.check(source,metric='daily_mean')['verdict'],'indeterminate')
    def test_standardized_missing_evidence(self):
        source=compare(standard=True);source['standardization'].pop('weekday_details')
        self.assertEqual(self.check(source,metric='weekday_standardized')['verdict'],'indeterminate')
    def test_standardized_changed_period(self):
        source=compare(standard=True);source['standardization']['weekday_details'][0]['start_date']='2024-01-02'
        self.assertEqual(self.check(source,metric='weekday_standardized')['verdict'],'indeterminate')
    def test_standardized_changed_sum(self):
        source=compare(standard=True);source['standardization']['weekday_details'][0]['weekdays'][0]['total']+=1
        self.assertEqual(self.check(source,metric='weekday_standardized')['verdict'],'indeterminate')
    def test_display_rounding_not_equal(self):
        source=compare(standard=True)
        # Exact delta 1/7000, though both display values round to 70.000.
        for i,detail in enumerate(source['standardization']['weekday_details']):
            for w in detail['weekdays']:
                w.update(days=1000,total=70000,expected_cells=7000,observed_cells=7000)
            if i:detail['weekdays'][0]['total']+=1
            source['table'][i].update(days=7000,total=490000+i,expected_cells=49000,observed_cells=49000)
        source['standardization']['values']=[70,70]
        r=self.check(source,metric='weekday_standardized',direction='equal')
        self.assertEqual(r['verdict'],'contradicted');self.assertEqual(r['evidence']['exact_difference'],'1/7000');self.assertEqual(r['actual_direction'],'increase')
    def test_zero_baseline(self):
        source=[{**x,'count':0 if x['date']<date(2024,2,1) else x['count']} for x in rows()]
        r=self.check(compare(source));self.assertEqual(r['verdict'],'supported');self.assertIsNone(r['evidence']['percent_change']);self.assertIn('0',r['evidence']['percent_note'])
    def test_actual_zeros_equal(self):
        r=self.check(compare([{**x,'count':0} for x in rows()]),direction='equal')
        self.assertEqual(r['verdict'],'supported');self.assertEqual(r['evidence']['values'],[0,0])
    def test_schema_unknown_and_text_refused(self):
        for claim in [{'metric':'total','direction':'increase','text':'혼잡 증가'},{'metric':'crowding','direction':'increase'},{'metric':'total'},{'metric':[],'direction':'increase'},'이용이 늘었다',{'metric':'total','direction':'causal'}]:
            with self.subTest(claim=claim):
                with self.assertRaises(ValueError):validate_claim(claim)
    def test_schema_copy(self):
        claim={'metric':'total','direction':'increase'};self.assertIsNot(validate_claim(claim),claim)
    def test_source_not_mutated(self):
        source=compare(standard=True);before=deepcopy(source);self.check(source,metric='weekday_standardized');self.assertEqual(source,before)
    def test_exact_source_and_population_preserved(self):
        source=compare();r=self.check(source)
        self.assertEqual(r['evidence']['sources'],source['sources']);self.assertEqual(r['evidence']['user_types'],['일반']);self.assertEqual(r['evidence']['periods'][0]['start_date'],'2024-01-01')
    def test_single_result_refused(self):
        with self.assertRaises(ValueError):check_claim({'table':[],'plan':{'dimension':'time'}},{'metric':'total','direction':'increase'})
    def test_tampered_raw_eligibility_guard(self):
        source=compare(end_a='2024-01-31',start_b='2024-02-01',end_b='2024-02-29');source['comparison']['eligible']=True
        self.assertEqual(self.check(source)['verdict'],'indeterminate')
    def test_json_safe(self):
        import json
        json.dumps(self.check(),ensure_ascii=False)
    def test_raw_arithmetic_fact_separate_from_comparability(self):
        r=self.check(compare(end_a='2024-01-31',start_b='2024-02-01',end_b='2024-02-29'))
        self.assertEqual(r['verdict'],'indeterminate')
        self.assertEqual(r['evidence']['arithmetic_only']['values'],[70,140])
        self.assertEqual(r['evidence']['arithmetic_only']['direction'],'increase')
        self.assertIn('산술값',r['safe_statement']);self.assertIn('동등조건',r['safe_statement'])
    def test_missing_has_no_arithmetic_direction_claim(self):
        r=self.check(compare(rows()[1:]))
        self.assertNotIn('arithmetic_only',r['evidence'])
