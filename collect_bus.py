"""국토부 노선별 경유 정류장별 이용량(월별) → 노드 정류장 승하차 수집.

유성구 월 11만 행을 훑어 노드 정류장만 남긴다. numOfRows 상한이 1000 이라 월당 110 요청.
정류장 매칭은 ID 가 아니라 정류장명으로 한다. nodes.csv 의 ID 는 'DJB' 접두어가 붙은
별도 체계라 API 의 sttn_id 와 직접 안 맞는다.

사용법: python3 collect_bus.py 202606 [202607 ...]
"""
import csv, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from collections import defaultdict

URL = "https://apis.data.go.kr/1613000/RoutebyStopTripVolume/getMonthlyRoutebyStopTripVolume"
SGG = "30200"  # 유성구. 출연연과 충남대가 모두 여기 있다
OUT = "data/bus_monthly"


def targets():
    """sttn_id → 노드.

    월별 응답에는 sttn_nm 이 없고 sttn_id 만 있다(일별에는 둘 다 있다).
    그래서 build_stop_map.py 가 만든 사전을 거쳐 이름을 ID 로 바꿔 매칭한다.
    """
    id2nm = {r["sttn_id"]: r["sttn_nm"] for r in csv.DictReader(open("data/stop_id_map.csv"))}
    nm2node = {n["정류장명"]: (n["약칭"] or n["기관명"])
               for n in csv.DictReader(open("nodes.csv")) if n["유형"] != "제외" and n["정류장명"]}
    t = {sid: nm2node[nm] for sid, nm in id2nm.items() if nm in nm2node}
    if not t:
        raise SystemExit("노드 정류장 ID 를 하나도 못 찾았다. stop_id_map.csv 를 다시 만들어라")
    return t, id2nm


def fetch_page(key, ym, page, tries=5):
    """503 이 산발적으로 난다. 지수 백오프로 재시도한다."""
    q = urllib.parse.urlencode({"serviceKey": key, "pageNo": page, "numOfRows": 1000,
                                "dataType": "JSON", "ctpv_cd": "30", "sgg_cd": SGG, "opr_ym": ym})
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{URL}?{q}", timeout=120) as r:
                body = json.load(r)["Response"]["body"]
            items = body.get("items") or {}
            return items.get("item") or [], int(body["totalCount"])
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def collect(key, ym):
    path = f"{OUT}/{ym}.csv"
    if os.path.exists(path):
        print(f"{ym} 이미 있음 → 건너뜀"); return True
    tg, id2nm = targets()
    rows, base = [], defaultdict(lambda: [0, 0])  # 유성구 전체 baseline: tzon -> [승차,하차]
    page, total, seen = 1, None, 0
    while True:
        try:
            items, total = fetch_page(key, ym, page)
        except Exception as e:
            print(f"{ym} p{page} 실패: {str(e)[:80]}"); return False
        if not items:
            break
        for it in items:
            seen += 1
            # ponytail: 일부 행에 sttn_nm / tzon 이 없다. 결측은 baseline 에서도 뺀다
            tz, nm = it.get("tzon"), it.get("sttn_nm")
            if not tz:
                continue
            r, g = it.get("ride_nope", 0), it.get("goff_nope", 0)
            base[tz][0] += r; base[tz][1] += g
            node = tg.get(it.get("sttn_id"))
            if node:
                rows.append([ym, node, id2nm.get(it["sttn_id"], ""), tz, it.get("users_type_nm", ""), r, g])
        if seen >= total:
            break
        page += 1
        time.sleep(0.05)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["운행연월", "노드", "정류장명", "시간대", "이용자유형", "승차", "하차"])
        w.writerows(rows)
        for tz, (r, g) in sorted(base.items()):
            w.writerow([ym, "_유성구전체", "", tz, "전체", r, g])
    hit = len({x[2] for x in rows})
    print(f"{ym}  {seen:,}행 훑음 → 노드 {len(rows)}행 / 정류장 {hit}곳")
    return True


if __name__ == "__main__":
    key = os.environ["DATA_GO_KR_KEY"]
    for ym in sys.argv[1:]:
        if not collect(key, ym):
            print("중단"); break
