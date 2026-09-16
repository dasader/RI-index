"""노드 반경 500m 상가업소 수집 → N4(심야업종 밀도) 원지표.

소상공인시장진흥공단 반경내 상가업소정보 API. 노드 좌표는 nodes.csv 의 정류장 좌표
평균을 쓴다. 기관 정문이 곧 정류장이라 기관 좌표를 따로 지오코딩할 필요가 없다.
"""
import csv, json, os, sys, time, urllib.parse, urllib.request
from collections import Counter

API = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeListInRadius"
RADIUS = 500
# ponytail: 심야업종은 중분류 이름으로 고른다. 소분류 247개까지 안 내려가도 충분히 갈린다
LATE = {"주점", "유흥주점", "기타주점"}


def node_coords():
    stops = {s["정류장번호"]: (float(s["위도"]), float(s["경도"]))
             for s in csv.DictReader(open("data/bus_stops.csv")) if s["도시명"] == "대전광역시"}
    out = []
    for n in csv.DictReader(open("nodes.csv")):
        if n["유형"] == "제외" or not n["정류장ID"]:
            continue
        pts = [stops[i] for i in n["정류장ID"].split(";") if i in stops]
        if not pts:
            print(f"  경고: {n['node_id']} 정류장 좌표 없음", file=sys.stderr)
            continue
        out.append((n["node_id"], n["약칭"] or n["기관명"],
                    sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    return out


def fetch(key, lat, lon):
    rows, page = [], 1
    while True:
        q = urllib.parse.urlencode({"serviceKey": key, "radius": RADIUS, "cx": lon, "cy": lat,
                                    "numOfRows": 1000, "pageNo": page, "type": "json"})
        with urllib.request.urlopen(f"{API}?{q}", timeout=60) as r:
            body = json.load(r)["body"]
        rows += body.get("items") or []
        if len(rows) >= int(body.get("totalCount", 0)) or not body.get("items"):
            return rows
        page += 1
        time.sleep(0.2)


def main():
    key = os.environ["DATA_GO_KR_KEY"]
    all_rows = []
    print(f"{'노드':<10}{'전체':>6}{'음식':>6}{'심야':>6}{'심야%':>7}  상위업종")
    for nid, nm, lat, lon in node_coords():
        rows = fetch(key, lat, lon)
        food = [r for r in rows if r["indsLclsNm"] == "음식"]
        late = [r for r in food if r["indsMclsNm"].strip() in LATE]
        top = ", ".join(f"{k}{v}" for k, v in Counter(r["indsMclsNm"].strip() for r in food).most_common(3))
        pct = 100 * len(late) / len(food) if food else 0
        print(f"{nm:<10}{len(rows):>6}{len(food):>6}{len(late):>6}{pct:>7.1f}  {top}")
        for r in rows:
            r["node_id"] = nid
        all_rows += rows
    if all_rows:
        cols = list(all_rows[0].keys())
        with open("data/stores_500m.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader(); w.writerows(all_rows)
        print(f"\ndata/stores_500m.csv  {len(all_rows)}건")


if __name__ == "__main__":
    main()
