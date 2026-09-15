"""정류장 목록에서 nodes.csv 기관별 후보 정류장을 찾는다.

대덕은 정류장명에 기관명이 그대로 들어간다. 지오코딩 없이 이름 포함 매칭으로 붙인다.
출력은 확정본이 아니라 후보 목록이다. nodes.csv 의 정류장ID/정류장명 칸은 사람이 채운다.

사용법:
    python3 match_stops.py data/bus_stops.csv
"""
import csv, sys, unicodedata

NODES = "nodes.csv"
REGION = ("대전", "유성")  # 정류장 파일이 전국이면 이 말이 든 행만 본다


def norm(s):
    """공백·괄호 제거, 전각 정규화. '한국 전자통신 연구원(정문)' 과 '전자통신연구원' 을 같이 본다."""
    s = unicodedata.normalize("NFKC", s)
    return "".join(c for c in s if not c.isspace() and c not in "()[]·.-")


def load_stops(path):
    """컬럼명이 출처마다 다르므로 이름/번호/좌표 칸을 추론한다."""
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    cols = rows[0].keys()
    pick = lambda *pats: next((c for c in cols if any(p in c for p in pats)), None)
    return rows, {
        "name": pick("정류장명", "정류소명", "명칭"),
        "id": pick("정류장번호", "정류소번호", "정류장ID", "정류소ID", "ARS"),
        "lat": pick("위도", "lat"),
        "lon": pick("경도", "lon", "lng"),
        "region": pick("지자체", "시도", "시군구", "주소"),
    }


def match(stops, cols, nodes):
    out = {}
    for n in nodes:
        kw = norm(n["매칭키워드"])
        hits = []
        for s in stops:
            nm = s.get(cols["name"]) or ""
            if kw and kw in norm(nm):
                hits.append(s)
        out[n["node_id"]] = hits
    return out


def demo():
    """입력 파일 없이도 매칭 규칙만 검증한다."""
    assert norm("한국 전자통신 연구원(정문)") == "한국전자통신연구원정문"
    assert norm("전자통신연구원") in norm("한국전자통신연구원 정문")
    # 원자력연구원 키워드가 원자력안전기술원을 잘못 잡지 않아야 한다
    assert norm("원자력연구원") not in norm("한국원자력안전기술원")
    print("매칭 규칙 self-check ok")


if __name__ == "__main__":
    demo()
    if len(sys.argv) < 2:
        print("\n정류장 파일 없음. 사용법: python3 match_stops.py data/bus_stops.csv")
        sys.exit(0)
    nodes = list(csv.DictReader(open(NODES)))
    stops, cols = load_stops(sys.argv[1])
    print(f"\n컬럼 추론: {cols}")
    stops = [s for s in stops if not cols["region"] or any(r in (s.get(cols["region"]) or "") for r in REGION)]
    print(f"대상 정류장 {len(stops)}건\n")
    for n in nodes:
        hits = match(stops, cols, [n])[n["node_id"]]
        mark = "  " if len(hits) == 1 else "??"
        print(f"{mark} {n['약칭'] or n['기관명']:<8} ({len(hits)}건)")
        for s in hits[:6]:
            loc = f"  {s.get(cols['lat'],'')},{s.get(cols['lon'],'')}" if cols["lat"] else ""
            print(f"      {s.get(cols['id'],''):<12} {s.get(cols['name'],'')}{loc}")
