import sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
import os,csv,sqlite3,json,math
from pathlib import Path
import agent
rows=list(csv.DictReader(open(agent.source_path(),encoding='utf-8-sig')))
db=sqlite3.connect(':memory:');db.execute('create table records(date text,weekday text,time text,type text,count integer)');db.executemany('insert into records values(?,?,?,?,?)',[(r['base_date'],r['day_of_week'],r['base_hour'],r['user_type'],int(r['user_count'])) for r in rows])
checks=[]
for question,column in [('시간대','time'),('요일','weekday'),('이용자 유형','type')]:
 result=agent.analyze(question);sql=f'select {column},sum(count),count(*) from records'+('' if column=='type' else " where type='일반'")+f' group by {column}'
 expected={r[0]:(r[1],r[2]) for r in db.execute(sql)}
 ok=all(expected[r['label']]==(r['total'],r['observed_cells']) for r in result['table']);checks.append({'dimension':column,'independent_sql_match':ok});assert ok
result=agent.analyze('월별');expected={r[0]:(r[1],r[2]) for r in db.execute("select substr(date,1,4)||'-'||substr(date,5,2),sum(count),count(*) from records where type='일반' group by 1")};assert all(expected[r['label']]==(r['total'],r['observed_cells']) for r in result['table']);checks.append({'dimension':'month','independent_sql_match':True})
Path('research/calculation-audit.json').write_text(json.dumps({'checks':checks,'rows':len(rows),'sha256':agent.catalog()['sha256']},ensure_ascii=False,indent=2));print(checks)
