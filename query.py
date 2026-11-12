"""Explicit, bounded condition extraction. Dates and populations never disappear silently."""
import re,calendar
from datetime import date
from planner import QuestionScopeError,validate_scope,plan,dimension_tags

def extract_types(q,known):
 remaining=q;found=[]
 for name in sorted(known,key=len,reverse=True):
  pattern=re.escape(name)+r'(?=$|[\s은는의와과을를에가,·]|이용|승차|사용|기록|유형|들|만|으로|로|대상|한정)'
  if re.search(pattern,remaining):found.append(name);remaining=re.sub(pattern,' ',remaining)
 return sorted(found,key=known.index)

SUM_WORDS=('합산','합쳐','합해','합계','총합','총계')
def requests_population_sum(q):return any(w in q for w in SUM_WORDS)

def month_range(y,m):
 try:return str(date(y,m,1)),str(date(y,m,calendar.monthrange(y,m)[1]))
 except (ValueError,calendar.IllegalMonthError):raise QuestionScopeError('올바른 연도와 월을 입력하세요.')

def interpret(q,start,end,user_type,meta):
 if not isinstance(q,str) or not q.strip() or len(q)>500:raise QuestionScopeError('질문을 1~500자로 입력하세요.')
 if user_type not in meta['user_types']+['전체']:raise QuestionScopeError('화면에서 이용자 유형을 선택하세요.')
 if re.search(r'지난달|지난해|올해|작년|최근',q):raise QuestionScopeError('상대 날짜 대신 자료 범위 안의 연도·월 또는 시작일과 종료일을 입력하세요.')
 if re.search(r'제외|빼|말고|아니|아닌|이외|외의|외에|않',q):raise QuestionScopeError('제외·부정 조건은 자동 적용하지 않습니다. 포함할 정확한 유형과 기간을 긍정형으로 지정해 주세요.')
 if re.search(r'상반기|하반기|분기|상순|중순|하순|첫주|첫 주|마지막 주|마지막주|주차|첫째|둘째|셋째|넷째',q):raise QuestionScopeError('반기·분기·월 일부 표현은 자동 확장하지 않습니다. 정확한 시작일과 종료일을 YYYY-MM-DD로 입력하세요.')
 if re.search(r'이후|이전|직전|직후|전후',q):raise QuestionScopeError('이후·이전은 시작과 끝 및 경계 포함 여부가 불명확합니다. 포함할 시작일과 종료일을 명시하세요.')
 if re.search(r'공휴일|휴일|명절|비오는|비 오는|날씨|강수|폭설|여름|겨울|봄철|가을|맑은|맑을|흐린|흐릴|눈오는|눈 오는|더운|추운|폭염|우천|강우|기온',q):raise QuestionScopeError('공휴일·날씨·계절 조건은 현재 자료만으로 자동 필터링하지 않습니다. 확인한 정확한 날짜 범위를 직접 지정하세요.')
 if re.search(r'하루\s*마다|날\s*마다|(?<!요)일별|날짜\s*별|매일',q):raise QuestionScopeError('하루마다의 일별 시계열은 현재 지원하지 않습니다. 날짜 범위를 지정한 시간대·요일·월별 분석 또는 두 기간 일평균 비교를 요청하세요.')
 if re.search(r'낮은|적은|최저|최소',q) and re.search(r'높은|많은|최고|최대',q):raise QuestionScopeError('최고와 최저의 동시 요약은 현재 지원하지 않습니다. 원하는 순위 하나를 지정하세요. 전체 그룹 값은 결과 표에서 확인할 수 있습니다.')
 if '순서' in q and re.search(r'많|높|낮|적|큰|작|최대|최소|최고|최저',q):raise QuestionScopeError('값의 크기에 따른 정렬은 현재 지원하지 않습니다. 표는 시간·요일·월의 기본 순서입니다. 최고 또는 최저 하나를 질문하면 근거 요약으로 안내합니다.')
 if re.search(r'(월|화|수|목|금|토|일)요일부터.*순서',q):raise QuestionScopeError('요일 시작점을 지정하는 정렬 문법은 지원하지 않습니다. 요일별 비교로 질문하면 월요일부터 일요일까지 기본 순서로 표시합니다.')
 comparison_method='weekday_standardized' if re.search(r'요일\s*표준화',q) else 'raw'
 notes=[];clean=q;periods=[];kind='single';continuous_months=False
 matches=list(re.finditer(r'(20\d{2})[-./](\d{1,2})[-./](\d{1,2})|(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일',q))
 if matches:
  if len(matches)==1 and any(w in q for w in ('부터','까지')):raise QuestionScopeError('시작일과 종료일을 모두 명시하세요. 한 날짜를 전체 기간으로 대신 계산하지 않습니다.')
  dates=[]
  for m in matches:
   try:dates.append(str(date(*map(int,m.groups()[:3] if m.group(1) else m.groups()[3:]))))
   except ValueError:raise QuestionScopeError('유효하지 않은 날짜입니다.')
   clean=clean.replace(m.group(),' ')
  if len(dates)==4:
   if any(not re.search(r'~|∼|부터|[-–—]|(?i:to)',q[matches[i].end():matches[i+1].start()]) for i in (0,2)):raise QuestionScopeError('각 비교 기간을 시작일~종료일 형태로 명확히 표시하세요. 나열한 날짜를 임의로 연속 기간으로 바꾸지 않습니다.')
   if not any(w in q for w in ('비교','대비','차이','vs')):raise QuestionScopeError('네 날짜는 두 기간 비교에만 사용할 수 있습니다. A시작~A종료와 B시작~B종료 비교로 입력하세요.')
   kind='period_compare';periods=[{'start':dates[0],'end':dates[1],'label':'기간 A'},{'start':dates[2],'end':dates[3],'label':'기간 B'}]
  elif len(dates)==2:
   middle=q[matches[0].end():matches[1].start()]
   if re.search('과|와|대비|vs',middle) and any(w in q for w in ('비교','대비','차이')):
    kind='period_compare';periods=[{'start':d,'end':d,'label':'기간 '+x} for d,x in zip(dates,'AB')]
   elif re.search(r'~|∼|부터|[-–—]|(?i:to)',middle):start,end=dates
   else:raise QuestionScopeError('두 날짜를 연속 범위로 볼지 특정 두 날로 볼지 불명확합니다. 시작일~종료일 또는 두 날짜 비교라고 명시하세요.')
  elif len(dates)==1:start=end=dates[0]
  else:raise QuestionScopeError('날짜는 한 날짜, 한 기간의 두 날짜, 또는 비교할 두 기간의 네 날짜로 입력하세요.')
  notes.append('질문에 명시한 날짜를 화면 날짜보다 우선 적용합니다.')
 else:
  months=list(re.finditer(r'(20\d{2})년\s*(\d{1,2})월',q))
  if months:
   ranges=[month_range(int(m.group(1)),int(m.group(2))) for m in months]
   for m in months:clean=clean.replace(m.group(),' ')
   # Single-year shorthand, e.g. 2024년 1월과 2월 비교.
   trailing=re.search(r'(과|와|~|∼|부터)\s*(\d{1,2})월',clean)
   if len(ranges)==1 and trailing:
    ranges.append(month_range(int(months[0].group(1)),int(trailing.group(2))));clean=clean.replace(trailing.group(),' ')
   if len(ranges)==1:
    if re.search(r'부터|까지|~|∼',clean):raise QuestionScopeError('월 범위의 시작과 끝을 모두 지정하세요. 열린 범위를 한 달로 대신 계산하지 않습니다.')
    start,end=ranges[0]
   elif len(ranges)==2:
    connector=q[months[0].end():months[1].start()] if len(months)==2 else trailing.group(1)
    if re.search(r'~|∼|부터|[-–—]|(?i:to)',connector):start,end=ranges[0][0],ranges[1][1];continuous_months=True
    elif re.search(r'과|와|대비|(?i:vs)',connector) and any(w in q for w in ('비교','대비','차이')):
     kind='period_compare';periods=[{'start':r[0],'end':r[1],'label':'기간 '+x} for r,x in zip(ranges,'AB')]
    else:raise QuestionScopeError('두 달은 시작월~종료월의 연속 범위인지, A월과B월 비교인지 명확히 입력하세요.')
   else:raise QuestionScopeError('한 달 또는 두 달 비교만 해석할 수 있습니다. 시작일·종료일로 범위를 명확히 해주세요.')
   notes.append('질문에 명시한 달의 전체 달력기간을 적용합니다.')
  else:
   years=re.findall(r'(20\d{2})년',q)
   if len(years)==1:
    start=f'{years[0]}-01-01';end=f'{years[0]}-12-31';clean=clean.replace(years[0]+'년',' ')
    if re.search(r'부터|까지|~|∼',clean):raise QuestionScopeError('연도 범위의 시작과 끝을 모두 지정하세요.')
    notes.append('질문에 명시한 연도의 전체 달력기간을 적용합니다.')
   elif years:raise QuestionScopeError('여러 연도는 시작일·종료일의 두 기간으로 명확히 입력하세요.')
 if re.search(r'\d{1,2}\s*월|\d{1,2}\s*일|20\d{2}[-./]',clean):raise QuestionScopeError('해석하지 못한 날짜 표현이 있습니다. YYYY-MM-DD 형식으로 입력하세요.')
 if re.search(r'노인|어르신|고령|성인|학생|장애인|국가유공자|청년|유아|나이|연령',q):raise QuestionScopeError('질문의 인구집단을 원본 요금·행정 유형과 동일하다고 단정할 수 없습니다. 화면에 있는 정확한 유형(예: 일반·청소년·경로·장애 일반)을 지정하세요.')
 if re.search(r'경로.*(추천|안내|찾)|어떻게.*가|가려면|가는\s*법',q):raise QuestionScopeError('이 자료에는 노선·경로 정보가 없습니다. 시간·요일·월·이용자 유형별 승차 집계 질문만 지원합니다.')
 specified=extract_types(q,meta['user_types'])
 residual=q.replace('일반적인',' ')
 for name in specified:residual=residual.replace(name,' ')
 if any(name in residual for name in meta['user_types']):raise QuestionScopeError('이용자 유형 표현의 범위를 확실히 해석하지 못했습니다. 정확한 유형명과 분석 기준을 분리해 입력하세요.')
 explicit_all=bool(re.search(r'(전체|모든)\s*(이용자|유형|승객|승차자|집단|승차량|승차|이용량|기록)',q))
 if explicit_all and specified:raise QuestionScopeError('전체 이용자와 특정 유형이 함께 지정되었습니다. 전체 또는 특정 유형 중 하나로 명확히 질문하세요.')
 chosen=meta['user_types'] if explicit_all else specified or (meta['user_types'] if user_type=='전체' else [user_type])
 if explicit_all:notes.append('질문에 명시한 전체 이용자 유형을 적용합니다.')
 if specified:notes.append('질문에 명시한 이용자 유형을 우선 적용: '+', '.join(chosen))
 if comparison_method=='weekday_standardized':
  if kind!='period_compare':raise QuestionScopeError('요일 표준화는 원기간을 보존하는 두 기간 일평균 비교에만 지원합니다. 비교할 두 기간을 명시하세요.')
  clean=re.sub(r'요일\s*표준화',' ',clean)
 ensure_supported_remainder(clean,meta['user_types'])
 start=start or meta['min_date'];end=end or meta['max_date']
 for a,b in [(p['start'],p['end']) for p in periods] if periods else [(start,end)]:
  try:da=date.fromisoformat(a);db=date.fromisoformat(b)
  except (ValueError,TypeError):raise QuestionScopeError('날짜는 YYYY-MM-DD 형식이어야 합니다.')
  if da>db:raise QuestionScopeError('시작일이 종료일보다 늦습니다.')
  if a<meta['min_date'] or b>meta['max_date']:raise QuestionScopeError(f"요청 기간이 자료 범위({meta['min_date']}~{meta['max_date']})를 벗어납니다. 일부만 잘라 계산하지 않았습니다.")
 if kind=='period_compare':
  if requests_population_sum(clean) and not re.search(r'일평균|하루\s*평균',clean):raise QuestionScopeError('두 기간 비교에서 합산이 총합 지표인지 유형 결합인지 불명확합니다. 이 기능은 일평균 비교만 지원합니다. 일평균이라고 명시하거나 총합은 한 기간씩 분석하세요.')
  if len(specified)>1 and not requests_population_sum(q):raise QuestionScopeError('두 기간 비교에서 여러 유형을 합칠지 개별 비교할지 불분명합니다. 유형 하나를 선택하거나 합산이라고 명시하세요.')
  # A period comparison is a separate tool, not a shortcut around scope validation.
  # It only compares aggregate daily means for the selected population. Never
  # discard an additional grouping/time filter just because two periods exist.
  if re.search(r'낮은|적은|최저|최소|높은|최고|최대|가장',clean):raise QuestionScopeError('두 기간 비교는 일평균 차이만 제공합니다. 그룹의 최고·최저는 한 기간의 시간대·요일·월·유형별 분석으로 요청하세요.')
  compact=re.sub(r'\s+','',clean)
  period_groups=('시간','구간','요일','주말','평일','일주일','아침','저녁','새벽','오후','출근','퇴근','밤','하루중','매달','월별','월마다','월간','연중','월단위','한달씩','추이','추세','유형별','유형비교','유형간','이용자구분')
  if any(w in compact for w in period_groups):raise QuestionScopeError('두 기간 비교는 선택한 유형의 전체 날짜·시간을 합친 일평균만 비교합니다. 시간·요일·월·유형별 세부 비교나 특정 시간 조건은 함께 지원하지 않습니다. 해당 조건을 유지하려면 한 기간씩 분석하세요.')
  validate_scope(clean)
  if max(p['start'] for p in periods)<=min(p['end'] for p in periods):raise QuestionScopeError('두 비교 기간은 겹치지 않아야 합니다.')
  dimension='period_compare';mode='rules';notes.append('두 기간의 일평균을 계산하고 관측률과 요일 구성비가 같을 때만 차이를 해석합니다.')
  start=min(p['start'] for p in periods);end=max(p['end'] for p in periods)
 else:
  if any(w in clean for w in ('아침','저녁','새벽','오후','출근','퇴근','밤')):raise QuestionScopeError('아침·저녁 등 특정 시간의 경계가 명확하지 않습니다. 현재는 시간대 전체 비교를 지원하므로 시간대별 분석으로 질문하세요.')
  named_day=any(w in clean for w in ('월요일','화요일','수요일','목요일','금요일','토요일','일요일'))
  if named_day and not re.search(r'요일을\s*월요일부터\s*순서대로',clean):raise QuestionScopeError('특정 요일만 거르는 조건은 지원하지 않습니다. 요일별 전체 비교 또는 평일과 주말 비교로 질문하세요.')
  if ('평일' in clean)!=('주말' in clean):raise QuestionScopeError('평일 또는 주말만 선택하는 필터는 지원하지 않습니다. 평일과 주말 비교라고 질문하면 두 그룹을 명시적으로 비교합니다.')
  validate_scope(clean)
  dimension,mode,warning=plan(clean)
  if warning:notes.append(warning)
  group_expression=clean
  for name in specified:group_expression=group_expression.replace(name,' ')
  explicit_group=bool(dimension_tags(group_expression))
  if continuous_months and not explicit_group and not requests_population_sum(clean):
   dimension='month';notes.append('연속 월 범위의 비교이므로 포함된 모든 달의 월별 기록을 분석합니다.')
   if mode=='local_ai':mode='rules_guarded'
  sum_requested=requests_population_sum(clean)
  compact=re.sub(r'\s+','',clean)
  # Shared dimension tags prevent summary/range defaults from erasing a group.
  overview_total=explicit_all and not explicit_group and not any(w in compact for w in ('언제','어느','일주일','하루중'))
  daily_overview=bool(re.search(r'하루\s*평균|일평균',clean))
  if (sum_requested or overview_total or daily_overview) and not explicit_group:
   dimension='summary';notes.append('선택한 유형과 모든 시간대를 합쳐 하나의 집계로 계산합니다.')
   if mode=='local_ai':mode='rules_guarded'
  if len(specified)>1 and dimension not in ('user_type','summary') and not sum_requested:raise QuestionScopeError('여러 유형의 기간별 교차 비교는 아직 지원하지 않습니다. 유형 하나를 선택하거나 유형별 비교로 질문하세요.')
  if dimension=='user_type' and not specified:chosen=meta['user_types'];notes.append('이용자 유형 비교이므로 전체 유형을 나란히 분석합니다.')
 total_requested=bool(re.search(r'합계|총합|총계',clean))
 if total_requested and ('평균' in clean or '시간당' in clean):raise QuestionScopeError('합계와 평균을 한 표시값으로 동시에 계산하지 않습니다. 원하는 지표 하나를 지정하세요.')
 if kind=='period_compare' and '시간당' in clean:raise QuestionScopeError('두 기간 비교는 일평균 지표만 지원합니다. 시간당 조건을 무시하지 않았으므로 일평균 비교로 다시 질문하세요.')
 if kind=='period_compare' and total_requested:raise QuestionScopeError('두 기간의 공정 비교는 일평균 지표를 사용합니다. 총합만 원하면 한 기간씩 합계 분석을 요청하거나 일평균 비교로 질문하세요.')
 # In a single analysis, an unqualified sum request is a total metric,
 # including grouped analyses. Explicit averages still override population sums.
 unqualified_sum=kind=='single' and requests_population_sum(clean) and '평균' not in clean and '시간당' not in clean
 metric='total' if total_requested or unqualified_sum else 'hourly_daily_mean' if '시간당' in clean else 'daily_mean' if re.search(r'일평균|하루\s*평균',clean) or (dimension=='summary' and '평균' in clean) else 'total' if dimension=='summary' else 'hourly_daily_mean' if dimension=='time' else 'daily_mean'
 notes.append('표시 지표: '+{'total':'관측 승차 합계','daily_mean':'포함일수로 나눈 기록 일평균','hourly_daily_mean':'포함일수와 구간시간으로 나눈 기록 시간당 일평균'}[metric])
 if comparison_method=='weekday_standardized':notes.append('원래 두 기간을 유지하고, 각 기간의 요일별 기록 일평균에 월~일 각각 1/7을 적용한 값을 별도로 계산합니다. 모든 조합 완전 관측과 7요일 포함이 필요하며 공휴일·계절·인과관계는 통제하지 않습니다. 원합계·실일평균도 그대로 보존합니다.')
 weekday_grouping='weekday_vs_weekend' if kind=='single' and '평일' in clean and '주말' in clean else None
 if weekday_grouping:notes.append('평일은 월~금, 주말은 토~일로 묶어 '+('각 그룹의 관측 합계를 비교합니다. 포함 날짜 수가 달라 이용 강도 차이로 해석할 수 없습니다.' if metric=='total' else '해당 날짜수로 나눈 기록 일평균을 비교합니다.'))
 extremum='min' if re.search(r'낮은|적은|최저|최소',clean) else 'max'
 if extremum=='min':notes.append('관측률 검증 후 표시값이 가장 낮은 그룹을 근거 요약합니다.')
 return {'comparison_method':comparison_method,'extremum':extremum,'metric':metric,'weekday_grouping':weekday_grouping,'kind':kind,'dimension':dimension,'start_date':start,'end_date':end,'user_types':chosen,'periods':periods,'notes':notes,'question':q,'mode':mode}

# Bounded request vocabulary, not a blacklist of every possible hidden condition.
# Dates and exact fare types are consumed first. Any semantic remainder fails closed.
# Multiword expressions are handled after whitespace removal; single particles are
# stripped only after the content vocabulary so they cannot conceal unknown nouns.
SAFE_CONTENT=[
 '시간대별','시간별','시간대','시간당','시간','구간마다','구간','요일별','요일','일주일','하루','날','자료','데이터','간','매달','월별','월마다','월간','연중','월단위','한달씩',
 '유형별','유형','이용자','구분','이용객','승객','승차자','집단','승차량','승차','인원수','인원','이용량','이용','기록량','기록','관측된','관측','값','전체','모든','기준','일평균','평균','총합','총계','합계','합산','합쳐서','합쳐','합해','추이','추세','변화','분포','흐름','분석','비교','차이','대비','통계','집계','그래프','표','기간','날짜','결과','현황','패턴','동안','나란히','순서대로','묶어서','묶은',
 '보고싶습니다','보고싶어요','보고싶어','확인하고싶습니다','확인하고싶어요','확인하고싶어','보여주세요','보여줘','알려주세요','알려줘','확인해주세요','확인해줘','분석해주세요','분석해줘','비교해주세요','비교해줘','그려주세요','그려줘','궁금합니다','궁금해요','궁금해','궁금한','어떻게','언제','어느','무슨','얼마나','타나요','타요','탔나요','많이','많은','많았나요','많나요','높았나요','높나요','높아','높은','적은','최저','최소','최고','최대','큽니까','큰','낮은','가장','더','차이가','있어요','있나요','있어','인가요','달라졌나요','달라졌어','달라','무엇일까','무엇인가','부탁해','해주세요','해줘','했나요','해봐','주세요','줘',
 '평일','주말','토요일','일요일','월요일','화요일','수요일','목요일','금요일','아침','저녁','출근','퇴근','밤','오후','새벽','중'
]
def ensure_supported_remainder(clean,types):
 remaining=re.sub(r'\s+','',clean).replace('일반적인','')
 for name in sorted(types,key=len,reverse=True):remaining=remaining.replace(name.replace(' ',''),'')
 remaining=remaining.replace('일반적인','')
 for word in sorted(set(SAFE_CONTENT),key=len,reverse=True):remaining=remaining.replace(word,'')
 for particle in ('와의','과의','에서','으로','부터','까지','마다','의','은','는','이','가','을','를','에','로','과','와','및','만','들','도'):
  remaining=remaining.replace(particle,'')
 remaining=re.sub(r'[?？!！.,，~∼\-–—:;·"\'()\[\]]','',remaining)
 remaining=re.sub(r'(?i)vs','',remaining)
 if remaining:raise QuestionScopeError('지원 범위 밖의 조건이나 표현이 남았습니다: '+remaining[:32]+'. 정확한 유형명·절대 날짜 범위와 시간대/요일/월/유형 분석 또는 두 기간 비교로 입력하세요.')
