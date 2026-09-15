"""대전 도시철도 시간대별 승하차 → 역별 활동 프로파일.

대조군 설계(대학상권 / 업무지구 / 주거) 가 데이터에서 실제로 분리되는지 확인용.
ponytail: stdlib csv + 산술 평균만. 통계 검정은 분리가 눈에 보이면 그때.
"""
import csv, datetime, statistics as st
from collections import defaultdict

SRC = "data/metro_hourly_2026.csv"
NIGHT = ["21-22시", "22-23시", "23-00시", "00-01시"]
MORNING = ["07-08시", "08-09시"]
EVENING = ["17-18시", "18-19시"]


def load(path=SRC):
    rows = list(csv.DictReader(open(path)))
    hours = [c for c in rows[0] if c.endswith("시")]
    out = defaultdict(dict)  # (역명, 날짜) -> {구분: {시간대: 인원}}
    for r in rows:
        out[(r["역명"], r["날짜"])][r["구분"]] = {h: int(r[h]) for h in hours}
    return out, hours


def profile(data, hours):
    """역별: 야간승차비, 주말/평일비, 아침하차 집중도, 저녁승차 집중도."""
    acc = defaultdict(lambda: defaultdict(list))
    for (station, date), kinds in data.items():
        wknd = datetime.date.fromisoformat(date).weekday() >= 5
        b, a = kinds["승차"], kinds["하차"]
        tb, ta = sum(b.values()), sum(a.values())
        if tb == 0 or ta == 0:
            continue  # ponytail: 결측/휴무일 통째로 버림. 212일 중 소수라 보간 불필요
        s = acc[station]
        s["night_board" if not wknd else "_nb_wknd"].append(sum(b[h] for h in NIGHT) / tb)
        s["morning_alight"].append(sum(a[h] for h in MORNING) / ta)
        s["evening_board"].append(sum(b[h] for h in EVENING) / tb)
        s["wknd_total" if wknd else "wday_total"].append(tb)
    res = {}
    for station, s in acc.items():
        res[station] = {
            "야간승차%": 100 * st.mean(s["night_board"]),
            "아침하차%": 100 * st.mean(s["morning_alight"]),
            "저녁승차%": 100 * st.mean(s["evening_board"]),
            "주말/평일": st.mean(s["wknd_total"]) / st.mean(s["wday_total"]),
            "일평균승차": st.mean(s["wday_total"]),
        }
    return res


def demo():
    data, hours = load()
    assert len(data) == 22 * 212, len(data)
    res = profile(data, hours)
    assert len(res) == 22
    # 정부청사(업무지구)는 아침하차가 유성온천(상권)보다 높아야 한다 — 아니면 지표가 틀렸다
    assert res["정부청사"]["아침하차%"] > res["유성온천"]["아침하차%"]
    print("self-check ok\n")
    cols = ["야간승차%", "아침하차%", "저녁승차%", "주말/평일", "일평균승차"]
    print(f"{'역명':<14}" + "".join(f"{c:>11}" for c in cols))
    for k, v in sorted(res.items(), key=lambda x: -x[1]["야간승차%"]):
        print(f"{k:<14}" + "".join(f"{v[c]:>11.2f}" for c in cols))


if __name__ == "__main__":
    demo()
