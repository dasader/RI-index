"""두 출처 접합 검증: 시간대별 승하차인원(일별) vs 개집표기 통행량(월별).

정의가 다르므로(승하차인원 vs 게이트 통행량) 겹치는 달에서 스케일이 맞는지 확인한다.
맞으면 2025년 공백 구간을 개집표기 월별로 메울 수 있다.
"""
import csv, collections

OVERLAP = "2024-12"  # 두 파일이 모두 덮는 달


def daily_month_sum(path, month, kind="승차"):
    acc = collections.Counter()
    for r in csv.DictReader(open(path)):
        if r["날짜"].startswith(month) and r["구분"] == kind:
            acc[r["역명"]] += sum(int(r[c]) for c in r if c.endswith("시"))
    return acc


def gate_month_sum(path, month, kind="승차"):
    acc = collections.Counter()
    for r in csv.DictReader(open(path)):
        if r["영업월"] == month and r["승하차 구분"] == kind:
            # ponytail: '역사' 는 '갈마역', 일별 파일 '역명' 은 '갈마'. 접미사만 떼면 22역 전부 일치
            acc[r["역사"].removesuffix("역")] += sum(int(r[c]) for c in r if c.endswith("통행량"))
    return acc


def demo():
    day = daily_month_sum("data/metro_hourly_2024.csv", OVERLAP)
    gate = gate_month_sum("data/metro_gate_monthly.csv", OVERLAP)
    assert set(day) == set(gate), set(day) ^ set(gate)
    ratio = sum(gate.values()) / sum(day.values())
    worst = max(day, key=lambda s: abs(gate[s] / day[s] - 1))
    assert 0.99 < ratio < 1.02, f"스케일 불일치 {ratio:.3f} — 접합 불가"
    print(f"{OVERLAP} 접합 검증 ok  전체비율 {ratio:.4f}  최대편차 {worst} {gate[worst]/day[worst]:.4f}")


if __name__ == "__main__":
    demo()
