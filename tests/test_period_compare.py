import unittest
from datetime import date,timedelta
from period_compare import compare_periods,SLOTS,WEEKDAYS

def fixture(days=28):
    rows=[]
    for n in range(days):
        d=date(2024,1,1)+timedelta(days=n)
        for slot in SLOTS:
            for typ in ('일반','경로'):
                rows.append({'date':d,'weekday':WEEKDAYS[d.weekday()],'time':slot,'user_type':typ,'count':10 if n<7 else 20,'row':len(rows)+2})
    return rows

class PeriodTests(unittest.TestCase):
    def setUp(self):self.rows=fixture()
    def compare(self,**kw):
        args=dict(rows=self.rows,start_a='2024-01-01',end_a='2024-01-07',start_b='2024-01-08',end_b='2024-01-14',user_types=['일반'],sha='testhash',source={'name':'test'})
        args.update(kw);return compare_periods(**args)
    def test_equal_weekday_complete(self):
        r=self.compare();self.assertTrue(r['quality']['comparable']);self.assertEqual(r['comparison']['difference'],70);self.assertEqual(r['comparison']['percent_change'],100)
    def test_conservation(self):
        r=self.compare();self.assertEqual(sum(x['total'] for x in r['table']),r['stats']['total']);self.assertEqual(r['stats']['rows'],98)
    def test_different_duration_equal_mix(self):
        r=self.compare(end_b='2024-01-21');self.assertTrue(r['quality']['comparable']);self.assertEqual(r['table'][1]['days'],14);self.assertEqual(r['comparison']['difference'],70)
    def test_weekday_mismatch_no_delta(self):
        r=self.compare(end_b='2024-01-13');self.assertFalse(r['quality']['comparable']);self.assertIsNone(r['comparison']['difference']);self.assertIsNone(r['comparison']['percent_change'])
    def test_missing_not_zero(self):
        r=self.compare(rows=self.rows[1:]);self.assertFalse(r['quality']['comparable']);self.assertEqual(r['table'][0]['missing_combinations'],1)
    def test_entire_period_unobserved_null(self):
        rows=[x for x in self.rows if not(x['user_type']=='일반' and x['date']<=date(2024,1,7))]
        r=self.compare(rows=rows);self.assertIsNone(r['table'][0]['total']);self.assertIsNone(r['table'][0]['value']);self.assertIsNone(r['comparison']['difference'])
    def test_actual_zero_distinct(self):
        rows=[{**x,'count':0 if x['date']<=date(2024,1,7) else x['count']} for x in self.rows]
        r=self.compare(rows=rows);self.assertEqual(r['table'][0]['total'],0);self.assertEqual(r['table'][0]['value'],0);self.assertTrue(r['quality']['comparable']);self.assertIsNone(r['comparison']['percent_change']);self.assertIn('0',r['comparison']['percent_note'])
    def test_both_zero(self):
        r=self.compare(rows=[{**x,'count':0} for x in self.rows]);self.assertEqual(r['comparison']['difference'],0);self.assertIsNone(r['comparison']['percent_change'])
    def test_overlap(self):
        with self.assertRaises(ValueError):self.compare(start_b='2024-01-07')
    def test_range(self):
        with self.assertRaises(ValueError):self.compare(start_a='2023-12-31')
    def test_reverse(self):
        with self.assertRaises(ValueError):self.compare(start_a='2024-01-08')
    def test_bad_date(self):
        with self.assertRaises(ValueError):self.compare(start_a='2024-02-31')
    def test_unknown_type(self):
        with self.assertRaises(ValueError):self.compare(user_types=['없는유형'])
    def test_empty_types(self):
        with self.assertRaises(ValueError):self.compare(user_types=[])
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):self.compare(rows=self.rows+[self.rows[0]])
    def test_negative_rejected(self):
        with self.assertRaises(ValueError):self.compare(rows=[{**self.rows[0],'count':-1}]+self.rows[1:])
    def test_multiple_types(self):
        r=self.compare(user_types=['일반','경로']);self.assertEqual(r['comparison']['difference'],140);self.assertEqual(r['table'][0]['expected_cells'],98)
    def test_source_not_mutated(self):
        src={'name':'test'};r=self.compare(source=src);self.assertEqual(src,{'name':'test'});self.assertEqual(r['sources'][0]['sha256'],'testhash')
    def test_weekday_counts(self):
        r=self.compare();self.assertEqual(r['table'][0]['weekday_counts'],dict.fromkeys(WEEKDAYS,1))
    def test_json_serializable(self):
        import json
        json.dumps(self.compare(),ensure_ascii=False)
    def test_repair_months_preserves_original(self):
        r=self.compare(rows=fixture(60),start_a='2024-01-01',end_a='2024-01-31',start_b='2024-02-01',end_b='2024-02-29')
        self.assertFalse(r['quality']['comparable']);self.assertIsNone(r['comparison']['difference'])
        self.assertEqual(r['table'][0]['end_date'],'2024-01-31')
        p=r['repair_proposal'];self.assertTrue(p['requires_confirmation'])
        self.assertEqual([(x['start'],x['end']) for x in p['periods']],[('2024-01-01','2024-01-07'),('2024-02-05','2024-02-11')])
    def test_repair_skips_missing_week(self):
        rows=[r for r in fixture(60) if not(r['date']==date(2024,1,1) and r['user_type']=='일반')]
        r=self.compare(rows=rows,start_a='2024-01-01',end_a='2024-01-31',start_b='2024-02-01',end_b='2024-02-29')
        self.assertEqual(r['repair_proposal']['periods'][0]['start'],'2024-01-08')
    def test_repair_absent_when_no_complete_week(self):
        rows=[r for r in fixture(60) if not(r['date'].weekday()==0 and r['user_type']=='일반')]
        r=self.compare(rows=rows,start_a='2024-01-01',end_a='2024-01-31',start_b='2024-02-01',end_b='2024-02-29')
        self.assertIsNone(r['repair_proposal'])
    def test_no_repair_when_comparable(self):self.assertIsNone(self.compare()['repair_proposal'])

    def test_both_periods_unobserved_stats_null(self):
        rows=[r for r in self.rows if r['user_type']!='일반' or r['date']>date(2024,1,14)]
        r=self.compare(rows=rows)
        self.assertIsNone(r['stats']['total']);self.assertEqual(r['stats']['rows'],0)
        self.assertTrue(all(x['total'] is None and x['value'] is None for x in r['table']))
        self.assertIsNone(r['comparison']['difference']);self.assertFalse(r['quality']['comparable'])
