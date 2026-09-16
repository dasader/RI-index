"""일별 API 한 날치로 sttn_id ↔ sttn_nm 사전을 만든다.

월별 응답에는 sttn_nm 이 없고 sttn_id 만 있다. 일별에는 둘 다 있으므로 하루만 훑어
사전을 만들어 두고, 이후 월별 수집은 ID 로 매칭한다.
"""
import csv, json, os, sys, time, urllib.parse, urllib.request

URL = "https://apis.data.go.kr/1613000/RoutebyStopTripVolume/getDailyRoutebyStopTripVolume"
OUT = "data/stop_id_map.csv"


def page(key, ymd, p, tries=5):
    q = urllib.parse.urlencode({"serviceKey": key, "pageNo": p, "numOfRows": 1000,
                                "dataType": "JSON", "ctpv_cd": "30", "sgg_cd": "30200", "opr_ymd": ymd})
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{URL}?{q}", timeout=120) as r:
                b = json.load(r)["Response"]["body"]
            return (b.get("items") or {}).get("item") or [], int(b["totalCount"])
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def main(ymd):
    key = os.environ["DATA_GO_KR_KEY"]
    m, p, seen, total = {}, 1, 0, None
    while True:
        items, total = page(key, ymd, p)
        if not items:
            break
        for it in items:
            seen += 1
            if it.get("sttn_id") and it.get("sttn_nm"):
                m[it["sttn_id"]] = it["sttn_nm"]
        if seen >= total:
            break
        p += 1
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["sttn_id", "sttn_nm"])
        w.writerows(sorted(m.items()))
    print(f"{seen:,}행 → 정류장 {len(m)}개 → {OUT}")

    want = {n["정류장명"]: (n["약칭"] or n["기관명"])
            for n in csv.DictReader(open("nodes.csv")) if n["유형"] != "제외" and n["정류장명"]}
    print("\n노드 매칭:")
    for nm, node in want.items():
        ids = [i for i, v in m.items() if v == nm]
        print(f"  {node:<10}{nm:<20}{ids if ids else '없음'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "20260601")
