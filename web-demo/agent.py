"""Reproducible aggregate bus-data analysis. Missing records are never imputed."""
import csv,os,hashlib,json,calendar
from pathlib import Path
from datetime import datetime,timedelta
from collections import Counter,defaultdict
from functools import lru_cache
from planner import QuestionScopeError
from query import interpret
from data_source import source_path, get_mode, get_metadata, verify_bytes, read_raw
SLOTS={'01시-06시':6,'07시-09시':3,'10시-12시':3,'13시-15시':3,'16시-18시':3,'19시-21시':3,'22시-24시':3}
DAYS='월화수목금토일'
COMMON_WARNINGS=['승차 집계는 고유 이용자 수·차량 혼잡도·배차 부족을 뜻하지 않습니다.','이 자료에는 정류장·노선·지역 열이 없어 장소별 안내나 자료의 공간적 범위를 확정할 수 없습니다.','미기록 조합은 0으로 대체하지 않습니다. 관측률이 다른 그룹의 비교는 누락 영향을 받습니다.','분석 기간과 유형은 확인한 계획에 명시됩니다. 질문에 명시한 날짜·유형은 화면 필터보다 우선합니다.']
def source_warnings():
 m=get_metadata()
 return [m['data_notice']]+COMMON_WARNINGS+[m['license_caveat']]
@lru_cache(maxsize=2)
def read_cached(path,mtime,size,source_mode):
 raw=read_raw(path);rows=[];keys=set()
 verify_bytes(raw,source_mode)
 for n,r in enumerate(csv.DictReader(raw.decode('utf-8-sig').splitlines()),2):
  if set(r)!={'base_date','day_of_week','base_hour','user_type','user_count'}:raise ValueError('CSV schema mismatch')
  date=datetime.strptime(r['base_date'],'%Y%m%d').date();count=int(r['user_count'])
  if r['day_of_week']!=DAYS[date.weekday()] or r['base_hour'] not in SLOTS or count<0:raise ValueError('invalid data')
  key=(date,r['base_hour'],r['user_type'])
  if key in keys:raise ValueError('duplicate cell')
  keys.add(key);rows.append({'date':date,'weekday':r['day_of_week'],'time':r['base_hour'],'user_type':r['user_type'],'count':count,'row':n})
 if not rows:raise ValueError('empty CSV')
 return rows,hashlib.sha256(raw).hexdigest()
def load():
 p=source_path();s=p.stat();return read_cached(str(p.resolve()),s.st_mtime_ns,s.st_size,get_mode())
def catalog():
 rows,sha=load();dates=sorted({r['date'] for r in rows});types=sorted({r['user_type'] for r in rows},key=lambda s:(s!='일반',s));expected=len(dates)*len(SLOTS)*len(types)
 return {'min_date':str(dates[0]),'max_date':str(dates[-1]),'rows':len(rows),'dates':len(dates),'user_types':types,'time_slots':list(SLOTS),'missing_combinations':expected-len(rows),'warnings':source_warnings(),'sha256':sha,'default_user_type':'일반','planner_mode':'synthetic_rules_demo' if get_mode()=='synthetic' else 'rules',**get_metadata()}
def prepare_analysis(question,start_date=None,end_date=None,user_type='일반'):
 return interpret(question,start_date,end_date,user_type,catalog())

def analyze(question,start_date=None,end_date=None,user_type='일반',expected_plan=None):
 prepared=prepare_analysis(question,start_date,end_date,user_type)
 if expected_plan is not None and expected_plan!=prepared:raise QuestionScopeError('분석 조건이 확인한 계획과 달라졌습니다. 계획을 다시 확인하세요.')
 rows,sha=load();meta=catalog()
 if prepared['kind']=='period_compare':
  from period_compare import compare_periods
  periods=prepared['periods']
  source=get_metadata()
  comparison_tool=compare_periods
  if prepared.get('comparison_method')=='weekday_standardized':
   from weekday_standardize import standardize_periods
   comparison_tool=standardize_periods
  result=comparison_tool(rows,periods[0]['start'],periods[0]['end'],periods[1]['start'],periods[1]['end'],prepared['user_types'],sha,source)
  result['plan']={**prepared,**result.get('plan',{})};result['warnings']=prepared['notes']+result.get('warnings',[])
  return result
 a=datetime.strptime(prepared['start_date'],'%Y-%m-%d').date();b=datetime.strptime(prepared['end_date'],'%Y-%m-%d').date()
 dates=[a+timedelta(days=i) for i in range((b-a).days+1)]
 dimension=prepared['dimension'];mode=prepared['mode'];warning=None
 unsupported=any(w in question for w in ('정류장','노선','배차','혼잡','지금','실시간','어디서'))
 type_override=dimension=='user_type'
 chosen=prepared['user_types']
 selected=[r for r in rows if a<=r['date']<=b and r['user_type'] in chosen]
 if dimension=='summary':labels=['선택 유형 합산']
 elif dimension=='time':labels=list(SLOTS)
 elif dimension=='weekday':labels=['평일','주말'] if prepared.get('weekday_grouping') else list(DAYS)
 elif dimension=='month':labels=sorted({str(d)[:7] for d in dates})
 else:labels=chosen
 groups=defaultdict(list)
 for r in selected:
  label='선택 유형 합산' if dimension=='summary' else str(r['date'])[:7] if dimension=='month' else ('평일' if r['date'].weekday()<5 else '주말') if dimension=='weekday' and prepared.get('weekday_grouping') else r[dimension]
  groups[label].append(r)
 table=[]
 for label in labels:
  group=groups[label];total=sum(r['count'] for r in group) if group else None
  nd=sum((d.weekday()<5)==(label=='평일') for d in dates) if dimension=='weekday' and prepared.get('weekday_grouping') else sum(DAYS[d.weekday()]==label for d in dates) if dimension=='weekday' else sum(str(d)[:7]==label for d in dates) if dimension=='month' else len(dates)
  hours=SLOTS[label] if dimension=='time' else None
  expected=nd*(1 if dimension=='time' else len(SLOTS))*(1 if dimension=='user_type' else len(chosen))
  normalized=total/nd/(hours or 1) if nd and total is not None else None
  value=total if prepared['metric']=='total' else total/nd if prepared['metric']=='daily_mean' and nd and total is not None else normalized
  table.append({'label':label,'total':total,'observed_cells':len(group),'expected_cells':expected,'coverage':round(len(group)/expected,6) if expected else None,'hours':hours,'per_hour':round(normalized,3) if hours and normalized is not None else None,'value':round(value,3) if value is not None else None,'days':nd})
 expected=len(dates)*len(SLOTS)*len(chosen);missing=expected-len(selected)
 warnings=source_warnings()+prepared['notes']
 if warning:warnings.append(warning)
 if missing:warnings.append(f'선택 범위 {expected:,}개 날짜×시간×유형 조합 중 {missing:,}개가 미기록입니다. 표시값은 기록 합계의 환산이며 실제 평균의 추정치가 아닙니다.')
 
 if '나이' in question or '연령' in question:warnings.insert(0,'실제 나이 열은 없습니다. 아래 유형은 행정·요금상 분류이며 연령별 통계로 해석할 수 없습니다.')
 if unsupported:warnings.insert(0,'질문에 포함된 장소·실시간·혼잡·배차 사항은 이 자료로 답할 수 없습니다. 아래는 가능한 집계 분석만 제공합니다.')
 observed_total=sum(r['count'] for r in selected)
 if sum(t['total'] or 0 for t in table)!=observed_total:raise ValueError('aggregation conservation failure')
 eligible=[t for t in table if t['expected_cells']>0]
 comparable=bool(eligible) and all(t['coverage']==1 and t['value'] is not None for t in eligible)
 quality={'comparable':comparable,'reason':'선택한 각 그룹의 기대 조합이 모두 기록되어 있습니다.' if comparable else '미기록 또는 관측 없는 그룹이 있어 순위·증감 해석을 보류합니다.',
   'checks':['그룹 합계와 선택 원본 합계 일치','날짜·구간길이 분모 확인','관측 조합과 기대 조합 대조','임의 0 대체 없음']}
 insights=[]
 if dimension=='summary':
  if not selected:
   insights.append('선택한 기간·유형은 미관측입니다. 합계와 평균은 값 없음으로 표시하며 0명으로 해석하지 않습니다. 비교를 보류합니다.')
  else:
   if prepared['metric']=='daily_mean':insights.append(f"선택한 전체 시간대의 기록 일평균은 {table[0]['value']:,.3f}명/일입니다. 관측 합계를 포함일수로 나눈 값입니다.")
   insights.append(f'선택한 기간·유형의 기록된 승차 합계는 {observed_total:,}입니다. 고유 이용자 수가 아니며 미기록분을 추정하지 않았습니다.')
 elif comparable:
  lowest=prepared.get('extremum')=='min'
  top=(min if lowest else max)(t['value'] for t in eligible);names=[t['label'] for t in eligible if t['value']==top]
  insights.append('완전 관측된 선택 범위에서 표시값이 가장 '+('낮은' if lowest else '높은')+' 그룹: '+', '.join(names)+f' ({top:,.3f}). 단위와 선택 기간을 함께 읽으세요.')
 else:insights.append('관측률이 다른 그룹의 크기 차이가 실제 이용 차이인지 미기록 영향인지 이 자료만으로 분리할 수 없습니다. 순위 해석을 보류했습니다.')
 if dimension=='month':
  partial=[t['label'] for t in table if t['days']<calendar.monthrange(int(t['label'][:4]),int(t['label'][5:]))[1]]
  if partial:insights.append('부분월 포함: '+', '.join(partial)+('. 실제 포함된 날짜의 총합이므로 완전한 달의 총합과 같은 기간이 아닙니다.' if prepared['metric']=='total' else '. 실제 포함일수로 환산했으며 나머지 날짜를 추정하지 않았습니다.'))
 unit={'total':'기록된 승차 합계(명)','daily_mean':'기록값 환산 명/일','hourly_daily_mean':'기록값 환산 명/일/시간'}[prepared['metric']]
 title={'summary':'선택 유형의 승차 합산','time':'시간대별 승차 기록','weekday':'요일별 승차 기록','month':'월별 승차 기록','user_type':'이용자 유형별 승차 기록'}[dimension]
 formula={'total':'선택 기간·유형의 관측 승차 집계 합계','daily_mean':'관측된 승차 합계 ÷ 해당 그룹의 선택 날짜 수','hourly_daily_mean':'관측된 승차 합계 ÷ 선택 날짜 수 ÷ 구간 시간'}[prepared['metric']]
 if prepared['metric']=='total' and dimension in ('time','month','weekday'):warnings.append('합계 요청에 따라 정규화하지 않은 총합을 표시합니다. 그룹의 시간길이·포함일수가 다르면 합계 순위를 이용 강도나 수요 차이로 해석할 수 없습니다.')
 return {'title':title,'answer':f'{a}~{b}, 유형 '+', '.join(chosen)+f', {len(selected):,}개 기록을 분석했습니다. {formula}으로 비교하며 미기록을 0으로 채우지 않았습니다.',
  'quality':quality,'insights':insights,'mode':mode,'plan':{**prepared,'formula':formula},'chart':{'labels':labels,'values':[t['value'] for t in table],'unit':unit},'table':table,'warnings':warnings,
  'steps':[{'tool':'validate_csv','detail':'스키마·날짜요일·중복셀·음수 검사 및 파일 해시 기록'},{'tool':'plan_query','detail':f'{mode}: {dimension} 도구 선택'},{'tool':'filter_rows','detail':f'날짜 {len(dates)}일, 유형 {len(chosen)}개'},{'tool':'aggregate_counts','detail':formula},{'tool':'audit_missing','detail':f'{missing:,}/{expected:,} 조합 미기록'}, {'tool':'verify_aggregate','detail':'독립 합계 보존 확인: '+str(observed_total)}, {'tool':'assess_comparability','detail':quality['reason']}, {'tool':'summarize_evidence','detail':'검증 결과에 따라 근거 요약 또는 순위 해석 보류'}],
  'sources':[{**get_metadata(),'sha256':sha,'rows_used':len(selected),'row_number_samples':[r['row'] for r in selected[:10]]}],
  'stats':{'rows':len(selected),'total':observed_total if selected else None,'days':len(dates),'missing_combinations':missing,'observed_cells':len(selected),'expected_cells':expected,'coverage':round(len(selected)/expected,6)}}

def prepare_claim_analysis(question,start_date=None,end_date=None,user_type='일반',claim=None):
 """Prepare a bounded numerical-direction check, never a free-text truth verdict."""
 from claim_check import validate_claim
 try:schema=validate_claim(claim)
 except ValueError as exc:raise QuestionScopeError(str(exc)) from None
 prepared=prepare_analysis(question,start_date,end_date,user_type)
 if prepared['kind']!='period_compare':raise QuestionScopeError('주장 검증은 명확히 선택한 두 기간의 수치 방향만 지원합니다.')
 if schema['metric']=='weekday_standardized' and prepared.get('comparison_method')!='weekday_standardized':
  raise QuestionScopeError('요일 표준화 지표를 자동 선택하지 않습니다. 먼저 요일 표준화 계획을 명시적으로 선택하세요.')
 labels={'total':'선택 기간의 관측 승차 총합','daily_mean':'원기간의 기록 일평균','weekday_standardized':'월~일 각 1/7의 요일 표준화 일평균'}
 directions={'increase':'증가','decrease':'감소','equal':'동일'}
 return {**prepared,'claim':schema,'notes':prepared['notes']+[
  '검증할 숫자 주장: 기간 B의 '+labels[schema['metric']]+'이 기간 A보다 '+directions[schema['direction']]+'했다는 방향만 판단합니다.',
  '자유 문장 전체의 진위·차량 혼잡·정책 효과·인과관계·고유 이용자 수는 판단하지 않습니다. 지표별 관측 조건이 맞지 않으면 판단을 보류합니다.']}

def analyze_claim(question,start_date=None,end_date=None,user_type='일반',claim=None,expected_plan=None):
 from claim_check import check_claim
 prepared=prepare_claim_analysis(question,start_date,end_date,user_type,claim)
 if expected_plan is None or expected_plan!=prepared:raise QuestionScopeError('주장 지표·방향·기간을 포함한 계획을 먼저 확인하세요.')
 base=prepare_analysis(question,start_date,end_date,user_type)
 result=analyze(question,start_date,end_date,user_type,expected_plan=base)
 result['claim_verification']=check_claim(result,prepared['claim'])
 result['plan']=prepared | {'formula':result['plan'].get('formula')}
 return result
