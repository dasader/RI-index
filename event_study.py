"""6월 마감 이벤트 스터디 (지하철 한정).

주의: 지하철은 출연연에 닿지 않는다. 이건 기관 신호 검증이 아니라 방법 검증이다.
업무지구(정부청사)에 6월 상승이 보이고 상권(중앙로)에 안 보이면 지표가 작동하는 것이다.

야간지표 = 21시 이후 승차 / 전일 승차. 평일만. 비율이라 역 규모 차이에 영향받지 않는다.
"""
import csv, datetime, statistics as st
from collections import defaultdict

NIGHT = ["21-22시", "22-23시", "23-00시", "00-01시"]
# ponytail: 공휴일 API 가 아직 없어 6월 공휴일만 손으로 뺀다. 전체 기간 통제는 특일정보 받으면
HOLIDAYS = {"2024-06-06", "2026-06-06", "2024-05-05", "2024-05-06", "2024-05-15", "2026-05-05", "2026-05-25"}


def night_ratio_by_month(paths):
    """{역명: {연-월: [일별 야간승차비]}}  평일·비공휴일만."""
    out = defaultdict(lambda: defaultdict(list))
    for p in paths:
        for r in csv.DictReader(open(p)):
            if r["구분"] != "승차":
                continue
            d = r["날짜"]
            if d in HOLIDAYS or datetime.date.fromisoformat(d).weekday() >= 5:
                continue
            tot = sum(int(r[c]) for c in r if c.endswith("시"))
            if tot < 100:
                continue  # ponytail: 표본 너무 작은 날 버림. 갑천 같은 소규모역 노이즈 차단
            out[r["역명"]][d[:7]].append(sum(int(r[c]) for c in NIGHT) / tot)
    return out


def june_effect(data, year):
    """6월 평균 - (5·7월 평균). 인접월 대비라 계절 추세를 자연히 뺀다."""
    res = {}
    for station, months in data.items():
        get = lambda m: st.mean(months[f"{year}-{m}"]) if months.get(f"{year}-{m}") else None
        jun, may, jul = get("06"), get("05"), get("07")
        if None in (jun, may, jul):
            continue
        res[station] = (jun - (may + jul) / 2) * 100  # 퍼센트포인트
    return res


def demo():
    d24 = night_ratio_by_month(["data/metro_hourly_2024.csv"])
    d26 = night_ratio_by_month(["data/metro_hourly_2026.csv"])
    assert len(d24) == 22 and len(d26) == 22
    assert 15 <= len(d24["시청"]["2024-06"]) <= 22, len(d24["시청"]["2024-06"])
    e24, e26 = june_effect(d24, 2024), june_effect(d26, 2026)
    common = set(e24) & set(e26)
    assert len(common) == 22

    allmean24 = st.mean(e24.values())
    allmean26 = st.mean(e26.values())
    print(f"전역 평균 6월 효과   2024 {allmean24:+.3f}%p   2026 {allmean26:+.3f}%p")
    print(f"(전역 평균을 뺀 값이 그 역 고유의 6월 효과)\n")
    print(f"{'역명':<12}{'2024':>9}{'2026':>9}{'평균':>9}   {'일관성'}")
    rows = []
    for s in common:
        a, b = e24[s] - allmean24, e26[s] - allmean26
        rows.append((s, a, b, (a + b) / 2, "O" if a * b > 0 else "-"))
    for s, a, b, m, c in sorted(rows, key=lambda x: -x[3]):
        print(f"{s:<12}{a:>+9.3f}{b:>+9.3f}{m:>+9.3f}   {c}")


if __name__ == "__main__":
    demo()
