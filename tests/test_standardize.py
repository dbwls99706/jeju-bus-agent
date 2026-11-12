import unittest
from datetime import date, timedelta
from fractions import Fraction
from weekday_standardize import standardize_periods
from period_compare import compare_periods, SLOTS, WEEKDAYS


def fixture(days=60):
    return [{'date':date(2024,1,1)+timedelta(days=i),
             'weekday':WEEKDAYS[(date(2024,1,1)+timedelta(days=i)).weekday()],
             'time':slot,'user_type':typ,'count':(i%7+1)*10+(20 if i>=31 else 0),'row':i*14+j*2+k+2}
            for i in range(days) for j,slot in enumerate(SLOTS) for k,typ in enumerate(('일반','경로'))]


class StandardizationTests(unittest.TestCase):
    def args(self, **kw):
        args=dict(rows=fixture(),start_a='2024-01-01',end_a='2024-01-31',start_b='2024-02-01',end_b='2024-02-29',user_types=['일반'],sha='fixture',source={'name':'fixture'})
        args.update(kw);return args
    def run_result(self, **kw):return standardize_periods(**self.args(**kw))
    def test_equal_weekday_weights(self):
        s=self.run_result()['standardization']
        self.assertTrue(s['eligible']);self.assertEqual(s['values'],[280,420]);self.assertEqual(s['difference'],140);self.assertEqual(s['percent_change'],50)
        self.assertEqual(set(s['weekday_weights'].values()),{'1/7'})
    def test_original_result_preserved(self):
        original=compare_periods(**self.args());r=self.run_result()
        for key in ('table','comparison','stats','sources','quality'):self.assertEqual(r[key],original[key])
        self.assertIsNone(r['comparison']['difference']);self.assertTrue(r['standardization']['eligible'])
    def test_missing_cell_blocks_both_values(self):
        r=self.run_result(rows=fixture()[1:]);s=r['standardization']
        self.assertFalse(s['eligible']);self.assertEqual(s['values'],[None,None]);self.assertIsNone(s['difference'])
    def test_missing_other_type_does_not_block_selected(self):
        rows=[r for r in fixture() if r['user_type']!='경로']
        self.assertTrue(self.run_result(rows=rows)['standardization']['eligible'])
    def test_all_selected_types_must_be_complete(self):
        rows=fixture()[1:]
        self.assertFalse(self.run_result(rows=rows,user_types=['일반','경로'])['standardization']['eligible'])
    def test_multiple_types_additive(self):
        s=self.run_result(user_types=['일반','경로'])['standardization']
        self.assertEqual(s['values'],[560,840]);self.assertEqual(s['percent_change'],50)
    def test_short_period_missing_weekday_blocks(self):
        s=self.run_result(start_a='2024-01-01',end_a='2024-01-06')['standardization']
        self.assertFalse(s['eligible']);self.assertFalse(s['all_weekdays_present']);self.assertEqual(s['values'],[None,None])
    def test_actual_zero_and_undefined_percent(self):
        rows=[{**r,'count':0 if r['date'].month==1 else r['count']} for r in fixture()]
        s=self.run_result(rows=rows)['standardization']
        self.assertTrue(s['eligible']);self.assertEqual(s['values'][0],0);self.assertIsNone(s['percent_change']);self.assertIn('0',s['percent_note'])
    def test_no_records_not_zero(self):
        rows=[r for r in fixture() if r['user_type']!='일반' or r['date']==date(2024,2,29)]
        s=self.run_result(rows=rows)['standardization']
        self.assertFalse(s['eligible']);self.assertIsNone(s['weekday_details'][0]['raw_total']);self.assertEqual(s['values'],[None,None])
    def test_validation_overlap(self):
        with self.assertRaises(ValueError):self.run_result(start_b='2024-01-20')
    def test_validation_duplicate(self):
        rows=fixture()
        with self.assertRaises(ValueError):self.run_result(rows=rows+[rows[0]])
    def test_json_serializable(self):
        import json
        json.dumps(self.run_result(),ensure_ascii=False)

    def test_optional_weekday_field(self):
        rows=[{k:v for k,v in r.items() if k!='weekday'} for r in fixture()]
        self.assertTrue(self.run_result(rows=rows)['standardization']['eligible'])
    def test_real_sqlite_reference_when_bundled(self):
        import csv, hashlib, sqlite3
        from pathlib import Path
        from datetime import datetime
        path=Path(__file__).resolve().parents[1]/'data/bus.csv'
        if not path.exists():self.skipTest('Original dataset not included in review-only package')
        raw=path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'acecf3fa511c68def3b68c34c29610dbda1101070f38e4be856cdcb123a4a529')
        rows=[]
        for item in csv.DictReader(raw.decode('utf-8-sig').splitlines()):
            rows.append({'date':datetime.strptime(item['base_date'],'%Y%m%d').date(),'weekday':item['day_of_week'],'time':item['base_hour'],'user_type':item['user_type'],'count':int(item['user_count'])})
        db=sqlite3.connect(':memory:')
        db.execute('CREATE TABLE records(day TEXT, weekday INTEGER, typ TEXT, n INTEGER)')
        db.executemany('INSERT INTO records VALUES (?,?,?,?)',[(str(r['date']),r['date'].weekday(),r['user_type'],r['count']) for r in rows])
        for types in [['일반'],['경로'],['일반','경로']]:
            result=self.run_result(rows=rows,user_types=types)['standardization']
            independent=[]
            for start,end in [('2024-01-01','2024-01-31'),('2024-02-01','2024-02-29')]:
                placeholders=','.join('?' for _ in types)
                value=db.execute(f'''WITH daily AS (
                    SELECT day,weekday,SUM(n) n FROM records
                    WHERE day BETWEEN ? AND ? AND typ IN ({placeholders}) GROUP BY day,weekday
                ), weekday_means AS (
                    SELECT weekday,AVG(n) mean FROM daily GROUP BY weekday
                ) SELECT SUM(mean)/7 FROM weekday_means''',[start,end]+types).fetchone()[0]
                independent.append(round(value,3))
            self.assertTrue(result['eligible']);self.assertEqual(result['values'],independent)
            if types==['일반']:self.assertEqual(result['values'],[13899.414,14274.964])
        db.close()

    def test_narrative_separates_raw_and_standardized(self):
        r=self.run_result()
        self.assertIn('원 달력일평균의 직접 비교',r['answer'])
        self.assertIn('별도의 요일 표준화 결과',r['answer'])
        self.assertFalse(any(x.startswith('다음 단계:') for x in r['insights']))
        self.assertTrue(any('별도 요일 표준화:' in x for x in r['insights']))
        self.assertIn('original_comparison_narrative',r)
