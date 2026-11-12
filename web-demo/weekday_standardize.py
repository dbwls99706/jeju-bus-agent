"""Descriptive weekday standardization, never imputation or causal adjustment.

Each period retains its full original range. Equal weights of 1/7 are applied to
its seven weekday-specific daily means only when both ranges are fully observed.
"""
from collections import Counter
from fractions import Fraction
from period_compare import compare_periods, _validated_rows, _date, SLOTS, WEEKDAYS


def standardize_periods(rows, start_a, end_a, start_b, end_b, user_types, sha, source):
    """Original result contract plus an independent ``standardization`` field.

    ``table``, ``comparison``, raw totals and raw daily means are unchanged.
    The extra estimand is an equal-weekday-weighted descriptive daily mean.
    Missing cells are not zero; every date/time/type cell and all 7 weekdays
    must exist in BOTH periods. Full-precision Fraction arithmetic precedes
    rounding of display values and deltas.
    """
    rows = _validated_rows(rows)
    result = compare_periods(rows, start_a, end_a, start_b, end_b, user_types, sha, source)
    types = result['plan']['user_types']
    bounds = [(_date(start_a), _date(end_a)), (_date(start_b), _date(end_b))]
    complete = all(t['observed_cells'] == t['expected_cells'] for t in result['table'])
    all_weekdays = all(all(t['weekday_counts'][d] > 0 for d in WEEKDAYS) for t in result['table'])
    eligible = complete and all_weekdays
    reasons = []
    if not complete:
        reasons.append('선택한 모든 날짜×시간구간×유형이 완전 관측되지 않아 요일 표준화 값을 계산하지 않습니다.')
    if not all_weekdays:
        reasons.append('두 기간 각각에 월요일부터 일요일까지 모두 있어야 하며 없는 요일을 추정하지 않습니다.')
    reason = ('두 원기간을 그대로 유지하고 각 요일의 기록 일평균에 동일한 1/7 가중치를 적용했습니다.'
              if eligible else ' '.join(reasons))
    details, exact_values = [], []
    for (a, b), raw in zip(bounds, result['table']):
        selected = [r for r in rows if a <= r['date'] <= b and r['user_type'] in types]
        by_day = {d: [r for r in selected if WEEKDAYS[r['date'].weekday()] == d] for d in WEEKDAYS}
        weekday_rows, means = [], []
        for day in WEEKDAYS:
            group = by_day[day]
            days = raw['weekday_counts'][day]
            expected = days * len(SLOTS) * len(types)
            total = sum(r['count'] for r in group) if group else None
            day_complete = days > 0 and len(group) == expected
            avg = Fraction(total, days) if day_complete else None
            means.append(avg)
            weekday_rows.append({'weekday': day, 'days': days, 'total': total,
                                 'observed_cells': len(group), 'expected_cells': expected,
                                 'complete': day_complete,
                                 'daily_mean': round(float(avg), 3) if avg is not None else None,
                                 'weight': '1/7'})
        value = sum(means, Fraction(0)) / 7 if eligible else None
        exact_values.append(value)
        details.append({'label': raw['label'], 'start_date': raw['start_date'],
                        'end_date': raw['end_date'], 'days': raw['days'],
                        'raw_total': raw['total'], 'raw_daily_mean': raw['value'],
                        'standardized_daily_mean': round(float(value), 3) if value is not None else None,
                        'weekdays': weekday_rows})
    difference = percent = None
    percent_note = None
    if eligible:
        delta = exact_values[1] - exact_values[0]
        difference = round(float(delta), 3)
        if exact_values[0]:
            percent = round(float(delta / exact_values[0] * 100), 3)
        else:
            percent_note = '기간 A의 요일 표준화 일평균이 0이므로 백분율 변화는 정의하지 않습니다.'
    warnings = [
        '요일 표준화값은 실제 기간의 관측 합계나 실제 달력일평균이 아닙니다. 모든 요일을 같은 비중으로 본 기술적 지표입니다.',
        '요일 구성만 동일하게 가중하며 공휴일·계절·행사·서비스 변경·인구구성은 통제하지 않습니다. 인과효과나 통계적 유의성을 뜻하지 않습니다.',
        '원기간·유형·관측 기록을 줄이거나 바꾸지 않았으며, 미관측 값을 0 또는 추정값으로 채우지 않았습니다.',
    ]
    result['standardization'] = {
        'method': 'equal_weekday_daily_mean', 'eligible': eligible, 'reason': reason,
        'complete_observation': complete, 'all_weekdays_present': all_weekdays,
        'values': [round(float(x), 3) if x is not None else None for x in exact_values],
        'difference': difference, 'percent_change': percent, 'percent_note': percent_note,
        'direction': '기간 B - 기간 A', 'unit': '요일 표준화 기록 명/일',
        'weekday_weights': {d: '1/7' for d in WEEKDAYS},
        'weekday_details': details,
        'formula': '(월 일평균 + 화 일평균 + 수 일평균 + 목 일평균 + 금 일평균 + 토 일평균 + 일 일평균) ÷ 7',
        'warnings': warnings, 'original_periods_preserved': True,
    }
    # Preserve numerical originals but label narratives by their metric scope.
    result['original_comparison_narrative'] = {'answer':result['answer'], 'insights':list(result['insights'])}
    result['answer'] = '원 달력일평균의 직접 비교: ' + result['answer'] + ' 별도의 요일 표준화 결과: ' + reason
    result['insights'] = ['원 달력일평균 직접 비교: ' + text for text in result['insights']
                          if not text.startswith('다음 단계:')]
    result['insights'].append('별도 요일 표준화: '+(f'일평균 차이 {difference:,.3f}명/일을 산출했습니다. 원지표의 직접 비교 판정과 구분하세요.' if eligible else reason))
    result['warnings'] = ['원지표 직접 비교에 대한 보류·주의와 요일 표준화의 별도 결과는 서로 다른 지표입니다.'] + result['warnings'] + warnings
    result['plan']['comparison_method'] = 'weekday_standardized'
    result['steps'].append({'tool': 'standardize_weekday_mix', 'detail': reason})
    return result
