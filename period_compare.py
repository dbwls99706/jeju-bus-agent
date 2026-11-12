"""Bounded two-period analysis. Never imputes missing cells or causal effects."""
from collections import Counter
from datetime import date, datetime, timedelta
from fractions import Fraction

SLOTS = ('01시-06시','07시-09시','10시-12시','13시-15시','16시-18시','19시-21시','22시-24시')
WEEKDAYS = '월화수목금토일'


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError('기간은 YYYY-MM-DD 형식의 유효한 날짜여야 합니다.') from None


def _validated_rows(rows):
    result = []
    seen = set()
    for row in rows:
        d = _date(row['date'])
        typ = row['user_type']
        count = row['count']
        slot = row['time']
        if not isinstance(typ, str) or not typ or slot not in SLOTS:
            raise ValueError('원본의 유형 또는 시간 구간이 올바르지 않습니다.')
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError('승차 집계는 비음수 정수여야 합니다.')
        if row.get('weekday', WEEKDAYS[d.weekday()]) != WEEKDAYS[d.weekday()]:
            raise ValueError('원본 날짜와 요일이 일치하지 않습니다.')
        key = (d, slot, typ)
        if key in seen:
            raise ValueError('날짜·시간·유형 조합이 중복되어 있습니다.')
        seen.add(key)
        result.append({**row, 'date': d})
    if not result:
        raise ValueError('비교할 원본 기록이 없습니다.')
    return result


def _first_complete_week(start, end, user_types, observed_keys):
    """Find, but never execute, the first complete Monday-Sunday window."""
    candidate = start + timedelta(days=(7-start.weekday()) % 7)
    while candidate + timedelta(days=6) <= end:
        complete = all(
            (candidate + timedelta(days=offset), slot, typ) in observed_keys
            for offset in range(7) for slot in SLOTS for typ in user_types
        )
        if complete:
            return candidate, candidate + timedelta(days=6)
        candidate += timedelta(days=7)
    return None


def compare_periods(rows, start_a, end_a, start_b, end_b, user_types, sha, source):
    """Return the app result contract plus comparison and period-specific fields.

    Only complete observations AND identical weekday proportions allow a numeric
    B-minus-A mean comparison. This is descriptive, not a significance/causality test.
    source is an optional metadata dict; the caller supplies the verified file hash.
    """
    rows = _validated_rows(rows)
    bounds = [(_date(start_a), _date(end_a)), (_date(start_b), _date(end_b))]
    lo, hi = min(r['date'] for r in rows), max(r['date'] for r in rows)
    for a, b in bounds:
        if a > b:
            raise ValueError('시작일이 종료일보다 늦습니다.')
        if a < lo or b > hi:
            raise ValueError(f'비교 기간은 원본 범위 {lo}~{hi} 안에서 선택하세요. 자동으로 잘라내지 않습니다.')
    if max(bounds[0][0], bounds[1][0]) <= min(bounds[0][1], bounds[1][1]):
        raise ValueError('두 기간이 겹칩니다. 중복되지 않는 기간을 선택하세요.')
    if isinstance(user_types, str):
        user_types = [user_types]
    if not isinstance(user_types, (list, tuple)) or not user_types or any(not isinstance(t,str) for t in user_types):
        raise ValueError('비교할 이용자 유형을 선택하세요.')
    user_types = list(dict.fromkeys(user_types))
    if set(user_types) - {r['user_type'] for r in rows}:
        raise ValueError('원본에 없는 이용자 유형입니다.')

    table, selected = [], []
    for label, (a, b) in zip(('기간 A','기간 B'), bounds):
        days = (b - a).days + 1
        counts = Counter(WEEKDAYS[(a + timedelta(days=i)).weekday()] for i in range(days))
        group = [r for r in rows if a <= r['date'] <= b and r['user_type'] in user_types]
        selected.extend(group)
        expected = days * len(SLOTS) * len(user_types)
        total = sum(r['count'] for r in group) if group else None
        avg = Fraction(total, days) if total is not None else None
        table.append({
            'label':label, 'start_date':str(a), 'end_date':str(b),
            'total':total, 'observed_cells':len(group), 'expected_cells':expected,
            'coverage':round(len(group)/expected,6), 'missing_combinations':expected-len(group),
            'days':days, 'hours':None, 'per_hour':None,
            'value':round(float(avg),3) if avg is not None else None,
            'weekday_counts':{d:counts[d] for d in WEEKDAYS},
            'weekday_proportions':{d:round(counts[d]/days,6) for d in WEEKDAYS},
            'observation_status':'미관측' if not group else '완전 관측' if len(group)==expected else '부분 관측',
        })
    pa, pb = table
    complete = all(t['observed_cells'] == t['expected_cells'] for t in table)
    same_weekdays = all(pa['weekday_counts'][d]*pb['days'] == pb['weekday_counts'][d]*pa['days'] for d in WEEKDAYS)
    comparable = complete and same_weekdays
    reasons = []
    if not complete:
        reasons.append('미기록 조합이 있어 실제 일평균 차이를 확정할 수 없습니다.')
    if not same_weekdays:
        reasons.append('두 기간의 요일 구성 비율이 달라 같은 조건의 단순 증감 비교를 보류합니다.')
    reason = '두 기간이 완전 관측이고 요일 구성 비율이 같아 기술적 일평균 차이를 계산했습니다.' if comparable else ' '.join(reasons)
    difference = percent = None
    percent_note = None
    if comparable:
        avg_a, avg_b = Fraction(pa['total'],pa['days']), Fraction(pb['total'],pb['days'])
        delta = avg_b-avg_a
        difference = round(float(delta),3)
        if avg_a:
            percent = round(float(delta/avg_a*100),3)
        else:
            percent_note = '기간 A 일평균이 0이므로 백분율 변화는 정의하지 않습니다.'
    comparison = {'direction':'기간 B - 기간 A', 'difference':difference, 'percent_change':percent,
                  'unit':'기록 명/일', 'eligible':comparable, 'complete_observation':complete,
                  'same_weekday_proportions':same_weekdays, 'reason':reason, 'percent_note':percent_note}
    warnings = [
        '승차 기록은 고유 이용자 수·차량 혼잡도·배차 부족을 뜻하지 않습니다.',
        '요일 구성 일치는 기초 비교 조건일 뿐, 계절·공휴일·행사·서비스 변경을 통제하지 않습니다. 원인이나 통계적 유의성을 주장하지 않습니다.',
        '미기록은 0으로 대체하지 않았습니다. 부분 관측 기간의 표시값은 기록 합계의 환산값이며 실제 일평균 추정치가 아닙니다.',
        '자료에 정류장·노선·지역 열이 없어 공간적 범위나 노선별 상황을 확정하지 않습니다.',
    ]
    if not comparable:
        warnings.insert(0, reason)
    if percent_note:
        warnings.append(percent_note)
    if comparable:
        insights = [f'기간 B - 기간 A의 기록 일평균 차이는 {difference:,.3f}명/일입니다.' +
                    (f' 기간 A 대비 {percent:,.3f}%입니다.' if percent is not None else ' 백분율 변화는 계산하지 않았습니다.')]
    else:
        insights = ['두 기간의 기록을 그대로 보여주되 차이·증감률·순위 결론은 생성하지 않았습니다.', reason]
    if not same_weekdays:
        insights.append('다음 단계: 같은 요일 구성의 겹치지 않는 7일 배수 기간을 선택하거나, 별도의 요일 표준화 방법을 검토하세요. 자동으로 기간을 바꾸지 않았습니다.')
    repair_proposal = None
    if not comparable:
        observed_keys = {(r['date'], r['time'], r['user_type']) for r in rows}
        candidates = [_first_complete_week(a,b,user_types,observed_keys) for a,b in bounds]
        if all(candidates) and max(candidates[0][0], candidates[1][0]) > min(candidates[0][1], candidates[1][1]):
            repair_proposal = {
                'periods':[{'label':label, 'start':str(window[0]), 'end':str(window[1])}
                           for label,window in zip(('기간 A','기간 B'),candidates)],
                'user_types':list(user_types),
                'reason':'각 원기간 안에서 선택 유형의 기록이 모두 있는 첫 월~일 7일 후보를 찾았습니다. 원래 기간 전체와는 다른 축소 범위이므로 확인 후에만 적용합니다. 계절·공휴일·행사는 통제하지 않습니다.',
                'requires_confirmation':True,
            }
            insights.append('대안 계획: 각 원기간 내의 완전관측 월~일 7일을 제안합니다. 원결과와 원기간은 변경하지 않았고, 대안 비교도 아직 계산하지 않았습니다. 적용 전 확인이 필요합니다.')
        else:
            absent = [label for label,window in zip(('기간 A','기간 B'),candidates) if window is None]
            why = ', '.join(absent) + ' 안에 선택 유형이 완전관측된 월~일 7일이 없습니다.' if absent else '두 완전관측 주간 후보가 겹쳐 대안으로 제시하지 않습니다.'
            insights.append('대안 계획 없음: '+why+' 기간 밖 기록이나 다른 유형으로 자동 대체하지 않았습니다.')
    expected = sum(t['expected_cells'] for t in table)
    total = sum(r['count'] for r in selected)
    if sum(t['total'] or 0 for t in table) != total:
        raise ValueError('기간별 집계 합계와 원본 선택 합계가 다릅니다.')
    src = dict(source or {})
    src.update(sha256=sha, rows_used=len(selected), row_number_samples=[r.get('row') for r in selected[:10]])
    formula = '각 기간의 관측 승차 합계 ÷ 각 기간의 달력일수; 완전 관측·요일 비율 일치 시에만 B-A와 (B-A)/A×100 계산'
    return {
        'title':'두 기간의 승차 기록 비교',
        'answer':f"기간 A {pa['start_date']}~{pa['end_date']}({pa['days']}일), 기간 B {pb['start_date']}~{pb['end_date']}({pb['days']}일), 유형 {', '.join(user_types)}. {reason}",
        'mode':'rules',
        'plan':{'dimension':'period_compare','start_date':str(min(a for a,b in bounds)), 'end_date':str(max(b for a,b in bounds)),
                'periods':[{'label':t['label'],'start_date':t['start_date'],'end_date':t['end_date']} for t in table],
                'user_types':user_types,'formula':formula},
        'chart':{'labels':[t['label'] for t in table], 'values':[t['value'] for t in table], 'unit':'기록값 환산 명/일'},
        'table':table, 'comparison':comparison, 'repair_proposal':repair_proposal,
        'quality':{'comparable':comparable,'reason':reason,'checks':['기간 범위·비중첩 확인','각 기간의 7시간구간×유형×날짜 관측률 대조','요일 구성 비율을 정확한 정수 교차곱으로 대조','기간별 합계 보존 확인','미기록 0 대체 없음']},
        'insights':insights,'warnings':warnings,
        'steps':[{'tool':'validate_periods','detail':'원본 범위 내 비중첩 두 기간과 유형 확인'},
                 {'tool':'aggregate_periods','detail':'각 기간의 합계·달력일수·관측 조합 계산'},
                 {'tool':'audit_missing','detail':f'{expected-len(selected):,}/{expected:,} 조합 미기록'},
                 {'tool':'compare_weekday_mix','detail':'요일 비율 일치' if same_weekdays else '요일 비율 불일치'},
                 {'tool':'gate_comparison','detail':reason},
                 {'tool':'verify_aggregate','detail':f'기간별 합계와 선택 원본 합계 {total:,} 일치' if selected else '선택된 관측 기록이 없어 합계는 미관측으로 표시'},
                 {'tool':'report_evidence','detail':'조건 충족 시에만 차이·증감률 산출, 불충족 사유와 후속 질문 제공'}],
        'sources':[src],
        'stats':{'rows':len(selected),'total':total if selected else None,'days':pa['days']+pb['days'],'missing_combinations':expected-len(selected),
                 'observed_cells':len(selected),'expected_cells':expected,'coverage':round(len(selected)/expected,6)},
    }
