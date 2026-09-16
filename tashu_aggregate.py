"""타슈 대여이력 zip → 노드별 일별 야간 대여 집계.

원본 2.5GB 는 저장소에 넣지 않는다. zip 에서 스트리밍하며 집계만 남긴다.
버스 정류장이 없어 제외했던 한의학연구원과, 노드에 없던 기초과학연구원이 여기서 살아난다.

사용법: python3 tashu_aggregate.py <zip경로>
"""
import csv, io, sys, zipfile
from collections import defaultdict

# 대여소ID → 노드. tashu_stations.csv 에서 골랐다
NODES = {
    "ST0399": "etri", "ST0188": "kribb", "ST0186": "kier", "ST0760": "krict",
    "ST1442": "kasi", "ST0884": "kiom", "ST1351": "ibs",
    "ST1145": "단지_연구단지네거리", "ST0185": "단지_연구단지운동장",
    "ST0183": "단지_한화솔루션", "ST0759": "단지_KTG중앙연구원", "ST0761": "단지_LG생활건강",
}
CNU = {"ST0367", "ST0366", "ST0368", "ST1015", "ST1014", "ST1016",
       "ST1052", "ST0765", "ST0193", "ST1017", "ST0330", "ST0369"}
NODES.update({s: "대조_충남대" for s in CNU})
NIGHT = range(21, 24)  # 21:00~23:59 대여. 이후는 심야라 표본이 급감한다


def run(zpath, out="data/tashu_daily.csv"):
    z = zipfile.ZipFile(zpath)
    # (날짜, 노드) -> [전체, 야간]
    acc = defaultdict(lambda: [0, 0])
    city = defaultdict(lambda: [0, 0])  # 대전 전체 baseline
    total = 0
    # 배포 오류 대응: 25년12월 파일 내용이 25년01월과 같다(행 수까지 동일).
    # 파일명이 아니라 첫 행의 실제 연월로 중복을 판정해 건너뛴다. 결과적으로 2025-12 는 결측.
    seen_months = set()
    for info in sorted(z.infolist(), key=lambda i: i.filename):
        # ponytail: 월마다 cp949 와 utf-8-sig 가 섞여 있다. BOM 으로 가른다
        enc = "utf-8-sig" if z.open(info).read(3) == b"\xef\xbb\xbf" else "cp949"
        with z.open(info) as fh:
            rd = csv.reader(io.TextIOWrapper(fh, encoding=enc, errors="replace", newline=""))
            head = next(rd)
            i_st, i_dt = head.index("대여_대여소ID"), head.index("대여일시")
            first = next(rd, None)
            if first is None:
                continue
            ym = first[i_dt][:7]
            if ym in seen_months:
                print(f"  {info.filename[-12:-4]} 내용이 {ym} 중복 → 건너뜀", file=sys.stderr)
                continue
            seen_months.add(ym)
            for row in [first, *rd]:
                try:
                    dt = row[i_dt]
                    d, h = dt[:10], int(dt[11:13])
                except (IndexError, ValueError):
                    continue  # ponytail: 깨진 행은 버린다. 1000만 행 중 소수라 집계에 영향 없음
                total += 1
                night = h in NIGHT
                city[d][0] += 1
                if night:
                    city[d][1] += 1
                node = NODES.get(row[i_st])
                if node:
                    acc[(d, node)][0] += 1
                    if night:
                        acc[(d, node)][1] += 1
        print(f"  {info.filename[-12:-4]} {enc:<11} 누적 {total:,}행", file=sys.stderr)

    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["날짜", "노드", "대여", "야간대여", "시전체대여", "시전체야간"])
        for (d, node), (t, n) in sorted(acc.items()):
            w.writerow([d, node, t, n, city[d][0], city[d][1]])
    print(f"\n원본 {total:,}행 → {out} {len(acc):,}행")
    print(f"기간 {min(d for d, _ in acc)} ~ {max(d for d, _ in acc)}")


if __name__ == "__main__":
    run(sys.argv[1])
