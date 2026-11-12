"""Bounded, deterministic claim checking over a verified two-period result.

Not a truth oracle: only the selected metric, ranges and population are checked.
No generated code, free-text allegations, causal or crowding claims are accepted.
"""
from copy import deepcopy
from fractions import Fraction

METRICS = {'total', 'daily_mean', 'weekday_standardized'}
DIRECTIONS = {'increase', 'decrease', 'equal'}
WEEKDAYS = '월화수목금토일'


def validate_claim(claim):
    if not isinstance(claim, dict) or set(claim) != {'metric', 'direction'}:
        raise ValueError('주장은 metric과 direction 두 항목으로만 지정하세요. 자유문장·혼잡·인과·복합 주장은 지원하지 않습니다.')
    if not isinstance(claim['metric'],str) or not isinstance(claim['direction'],str) or claim['metric'] not in METRICS or claim['direction'] not in DIRECTIONS:
        raise ValueError('지표는 total/daily_mean/weekday_standardized, 방향은 increase/decrease/equal 중 하나여야 합니다.')
    return dict(claim)


def _integer(value, positive=False):
    return isinstance(value, int) and not isinstance(value, bool) and value >= (1 if positive else 0)


def _complete(row):
    return (_integer(row.get('total')) and _integer(row.get('days'), True)
            and _integer(row.get('expected_cells'), True)
            and row.get('observed_cells') == row['expected_cells'])


def _exact_standardized(result, table):
    std = result.get('standardization', {})
    if std.get('eligible') is not True:
        return None, std.get('reason', '요일 표준화의 검증 조건을 충족하지 못했습니다.')
    if std.get('method') != 'equal_weekday_daily_mean':
        return None, '지원하는 동일 1/7 요일 가중 방식이 아닙니다.'
    details = std.get('weekday_details')
    if not isinstance(details, list) or len(details) != 2:
        return None, '정확한 판정에 필요한 요일별 합계·날짜 수 근거가 없습니다. 반올림된 표시값만으로 동률을 판단하지 않습니다.'
    values = []
    for row, detail in zip(table, details):
        weekdays = detail.get('weekdays', [])
        if len(weekdays) != 7 or {d.get('weekday') for d in weekdays} != set(WEEKDAYS):
            return None, '각 기간의 7개 요일 근거가 필요합니다.'
        if (detail.get('start_date'), detail.get('end_date')) != (row.get('start_date'), row.get('end_date')):
            return None, '요일 표준화 근거의 기간이 원기간과 다릅니다.'
        if any(not _complete(d) or d.get('complete') is not True or d.get('weight') != '1/7' for d in weekdays):
            return None, '요일별 완전관측·동일 1/7 가중 조건을 확인할 수 없습니다.'
        if sum(d['days'] for d in weekdays) != row['days'] or sum(d['total'] for d in weekdays) != row['total']:
            return None, '요일별 합계·날짜 수가 원기간 집계와 일치하지 않습니다.'
        values.append(sum((Fraction(d['total'], d['days']) for d in weekdays), Fraction(0)) / 7)
    return values, None


def check_claim(result, claim):
    """Return supported/contradicted/indeterminate with exact numeric evidence.

    ``result`` is the already verified two-period result; this function never
    changes its range, population, values or comparison method. Call only after
    the user confirms the claim plan. Display precision never decides equality.
    """
    claim = validate_claim(claim)
    if not isinstance(result, dict):
        raise ValueError('검증된 두 기간 분석 결과가 필요합니다.')
    table = result.get('table', [])
    plan = result.get('plan', {})
    if len(table) != 2 or plan.get('dimension') != 'period_compare':
        raise ValueError('두 기간 분석 결과에서만 주장을 검증할 수 있습니다.')
    periods = [{k: row.get(k) for k in ('label', 'start_date', 'end_date', 'days', 'total', 'observed_cells', 'expected_cells')} for row in table]
    warnings = [
        '판정 범위는 확인한 두 기간·이용자 유형·지표에 한정됩니다. 자료 밖의 사실을 검증하지 않습니다.',
        '승차 기록은 고유 이용자 수·차량 혼잡도·배차 부족을 뜻하지 않습니다. 원인·정책 효과·통계적 유의성을 판단하지 않습니다.',
        '요일 구성의 일치나 표준화도 공휴일·계절·행사·서비스 변경을 통제하지 않습니다.',
    ]
    metric = claim['metric']
    labels = {'total':'관측 승차 합계', 'daily_mean':'기록 일평균', 'weekday_standardized':'요일 표준화 기록 일평균'}
    units = {'total':'기록 명', 'daily_mean':'기록 명/일', 'weekday_standardized':'요일 표준화 기록 명/일'}
    evidence = {'metric':metric, 'metric_label':labels[metric], 'unit':units[metric],
                'periods':deepcopy(periods), 'user_types':deepcopy(plan.get('user_types', [])),
                'values':None, 'exact_values':None, 'difference':None, 'exact_difference':None,
                'percent_change':None, 'percent_note':None,
                'sources':deepcopy(result.get('sources', [])),
                'conditions':{'complete_observation':all(_complete(row) for row in table),
                              'same_weekday_proportions':result.get('comparison',{}).get('same_weekday_proportions'),
                              'raw_daily_mean_eligible':result.get('comparison',{}).get('eligible') is True,
                              'standardization_eligible':result.get('standardization',{}).get('eligible') is True,
                              'selected_periods_and_types_preserved':True,
                              'decision_uses_unrounded_fractions':True}}
    values, reason = None, None
    if not all(_complete(row) for row in table):
        reason = '선택한 두 기간의 모든 날짜×시간×유형이 완전 관측되지 않아 증가·감소·동률을 판단할 수 없습니다. 미관측을 0으로 간주하지 않았습니다.'
    elif metric == 'total':
        values = [Fraction(row['total']) for row in table]
        if table[0]['days'] != table[1]['days']:
            warnings.append('두 기간의 날짜 수가 다릅니다. 총합 방향은 기록 건수 차이만 뜻하며 일평균·이용 강도 변화가 아닙니다.')
    elif metric == 'daily_mean':
        comparison = result.get('comparison', {})
        if comparison.get('eligible') is not True:
            arithmetic = [Fraction(row['total'],row['days']) for row in table]
            arithmetic_delta = arithmetic[1]-arithmetic[0]
            evidence['arithmetic_only'] = {
                'values':[round(float(v),3) for v in arithmetic],
                'exact_values':[str(v) for v in arithmetic],
                'direction':'increase' if arithmetic_delta>0 else 'decrease' if arithmetic_delta<0 else 'equal',
                'difference':round(float(arithmetic_delta),3),
                'percent_change':round(float(arithmetic_delta/arithmetic[0]*100),3) if arithmetic[0] else None,
                'interpretation':'기록된 산술값의 방향이며 동등한 요일 조건의 비교나 원인 추론이 아닙니다.'}
            reason = comparison.get('reason', '원기간 일평균 비교 조건을 충족하지 못했습니다.')
        else:
            counts = [row.get('weekday_counts', {}) for row in table]
            if (any(set(c) != set(WEEKDAYS) or not all(_integer(v) for v in c.values()) for c in counts)
                or any(sum(c.values()) != row['days'] for c,row in zip(counts,table))
                or any(counts[0][d]*table[1]['days'] != counts[1][d]*table[0]['days'] for d in WEEKDAYS)):
                reason = '두 기간의 요일 구성 비율 일치를 정확한 근거로 확인할 수 없습니다.'
            else:
                values = [Fraction(row['total'], row['days']) for row in table]
    else:
        values, reason = _exact_standardized(result, table)
    if values is None:
        safe_statement=f"선택 범위의 {labels[metric]} 증가·감소 주장은 현재 비교 조건으로 판단을 보류합니다. {reason}"
        if evidence.get('arithmetic_only'):
            arithmetic=evidence['arithmetic_only'];a,b=arithmetic['values']
            direction={'increase':'증가','decrease':'감소','equal':'동일'}[arithmetic['direction']]
            safe_statement=f'기록된 원기간 일평균의 산술값은 {a:,.3f}→{b:,.3f}명/일로 {direction}합니다. 다만 요일 구성 등 비교 조건이 불균형하여 동등조건의 변화 판단은 보류합니다. 산술적 방향을 모른다는 뜻이 아니며 원인 추론도 아닙니다.'
        return {'claim':claim, 'verdict':'indeterminate', 'verdict_label':'판단 보류',
                'reason':reason, 'evidence':evidence, 'safe_statement':safe_statement,
                'warnings':warnings, 'method':'deterministic_metric_check', 'ai_verdict':False}
    delta = values[1]-values[0]
    actual = 'increase' if delta > 0 else 'decrease' if delta < 0 else 'equal'
    verdict = 'supported' if actual == claim['direction'] else 'contradicted'
    percent = delta/values[0]*100 if values[0] else None
    evidence.update(values=[int(v) if metric=='total' else round(float(v),3) for v in values], exact_values=[str(v) for v in values],
                    difference=round(float(delta),3), exact_difference=str(delta),
                    percent_change=round(float(percent),3) if percent is not None else None,
                    percent_note=None if percent is not None else '기간 A 값이 0이므로 백분율 변화는 정의하지 않습니다.')
    direction_text = {'increase':'높습니다', 'decrease':'낮습니다', 'equal':'같습니다'}[actual]
    population = ', '.join(plan.get('user_types', [])) or '선택 유형'
    ranges = f"{table[0].get('start_date')}~{table[0].get('end_date')} 대비 {table[1].get('start_date')}~{table[1].get('end_date')}"
    relation = '기간 B가 기간 A와 같습니다' if actual == 'equal' else f'기간 B가 기간 A보다 {direction_text}'
    safe = f"{ranges}, {population}의 {labels[metric]} 기준으로 {relation}."
    safe += f" 표시값은 A {float(values[0]):,.3f}, B {float(values[1]):,.3f} {units[metric]}입니다. 판정은 반올림 전 정확값을 사용했습니다."
    if delta and round(float(delta),3)==0:safe += f' 차이가 표시 정밀도보다 작으며 정확한 B-A 차이는 {delta}입니다.'
    if metric == 'total':safe += ' 관측 총합의 방향일 뿐 이용 강도 변화는 아닙니다.'
    if metric == 'weekday_standardized':safe += ' 월~일의 일평균에 각각 1/7을 적용한 별도 지표이며 실제 달력일평균이 아닙니다.'
    return {'claim':claim, 'verdict':verdict, 'verdict_label':'근거와 일치' if verdict=='supported' else '근거와 불일치',
            'actual_direction':actual, 'reason':'완전관측 및 선택 지표의 비교 조건 안에서 반올림 전 수치의 방향을 확인했습니다.',
            'evidence':evidence, 'safe_statement':safe, 'warnings':warnings,
            'method':'deterministic_metric_check', 'ai_verdict':False}
