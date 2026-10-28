"""
14회차 실증 2부. 일본 공모 토큰증권(ST) 발행 목록 분석.

데이터: japan_st_offerings.tsv
  출처: BOOSTRY「日本ST・RWAマーケットダッシュボード ～ リスト編」(boostry.co.jp/st-data) 공모 ST 발행 리스트.
  BOOSTRY는 기획·리서치·기사에 자유롭게 써도 된다고 밝히고 있다. 2026년 10월 28일 화면에서 옮겨 적었다.
  검산: 2026년 3월 말까지 82건·3,333억 엔, 2025회계연도 24건·1,650억 엔으로 BOOSTRY 보도자료(2026-04-02)와 같다.
열: issue_date, platform, product(상품 종류), asset(기초자산), amount_mn_jpy(발행총액, 백만 엔),
    start(START 시장 취급이면 〇), name(종목명)

질문
  J1. 해마다 얼마나 발행됐나? 일본 회계연도(4월–3월) 기준.
  J2. 어느 플랫폼(블록체인 기반)이 쓰였나? ibet for Fin(9회차 Lab A)과 Progmat의 비중은?
  J3. 무엇을 토큰으로 만들었나? 상품 종류와 기초자산.
  J4. 2차 시장(START)에서 거래되는 종목은 얼마나 되나? 상장 종목과 아닌 종목은 무엇이 다른가?
  J5. 발행에서 START 거래 시작까지 얼마나 걸리나? (start_listings.tsv: ODX 공식 '신규 취급 종목' 페이지, 2026-10-28 확인)

실행: python analyze_japan.py   (표준 라이브러리만)
"""

import csv
from collections import defaultdict
from pathlib import Path

SRC = Path(__file__).parent / "japan_st_offerings.tsv"
START = Path(__file__).parent / "start_listings.tsv"


def fy(date):
    y, m = int(date[:4]), int(date[5:7])
    return y if m >= 4 else y - 1          # 2025-04 ~ 2026-03 → FY2025


def load():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8"), delimiter="\t"))
    for r in rows:
        r["amt"] = float(r["amount_mn_jpy"]) / 1000          # 십억 엔
        r["fy"] = fy(r["issue_date"])
        r["listed"] = r["start"].strip() in ("〇", "◯")
        r["digital_transfer"] = "デジタル名義書換方式" in r["name"]
    return rows


def main():
    rows = load()
    print(f"공모 ST {len(rows)}건, {rows[0]['issue_date']} ~ {rows[-1]['issue_date']}, 합계 {sum(r['amt'] for r in rows):,.1f}십억 엔\n")

    print("J1. 회계연도별 발행 (십억 엔 = 100억 엔)")
    by = defaultdict(lambda: [0, 0.0])
    for r in rows:
        by[r["fy"]][0] += 1; by[r["fy"]][1] += r["amt"]
    cum = 0
    for y in sorted(by):
        cum += by[y][1]
        note = " (10월 27일까지)" if y == 2026 else ""
        print(f"  FY{y}{note:<14} {by[y][0]:>3}건 {by[y][1]:>7.1f}  누적 {cum:>7.1f}")

    print("\nJ2. 플랫폼별")
    plat = defaultdict(lambda: [0, 0.0])
    for r in rows:
        plat[r["platform"]][0] += 1; plat[r["platform"]][1] += r["amt"]
    tot = sum(v[1] for v in plat.values())
    for p, (n, a) in sorted(plat.items(), key=lambda x: -x[1][1]):
        print(f"  {p:<15} {n:>3}건 {a:>7.1f} ({a / tot:.0%})")
    for y in (2023, 2024, 2025, 2026):
        sub = [r for r in rows if r["fy"] == y]
        s = sum(r["amt"] for r in sub)
        ib = sum(r["amt"] for r in sub if r["platform"] == "ibet for Fin")
        pg = sum(r["amt"] for r in sub if r["platform"] == "Progmat")
        print(f"  FY{y}: ibet for Fin {ib / s:.0%}, Progmat {pg / s:.0%}")

    print("\nJ3. 상품 종류와 기초자산")
    prod = defaultdict(lambda: [0, 0.0])
    for r in rows:
        prod[r["product"]][0] += 1; prod[r["product"]][1] += r["amt"]
    for p, (n, a) in sorted(prod.items(), key=lambda x: -x[1][1]):
        print(f"  {p:<12} {n:>3}건 {a:>7.1f} ({a / tot:.0%})")
    asset = defaultdict(lambda: [0, 0.0])
    for r in rows:
        if r["product"] == "受益証券":
            asset[r["asset"]][0] += 1; asset[r["asset"]][1] += r["amt"]
    print("  수익증권(受益証券)의 기초자산:")
    for p, (n, a) in sorted(asset.items(), key=lambda x: -x[1][1]):
        print(f"    {p:<8} {n:>3}건 {a:>6.1f}")
    sizes = sorted(r["amt"] for r in rows)
    print(f"  1건 발행액 중앙값 {sizes[len(sizes) // 2] * 1000:,.0f}백만 엔, 최대 {sizes[-1] * 1000:,.0f}백만 엔")

    print("\nJ4. START(오사카디지털거래소) 2차 시장 취급")
    li = [r for r in rows if r["listed"]]
    print(f"  취급 {len(li)}건 / 전체 {len(rows)}건, 발행액 {sum(r['amt'] for r in li):,.1f}십억 엔")
    dt = [r for r in rows if r["digital_transfer"]]
    print(f"  종목명에 '디지털 명의개서 방식(デジタル名義書換方式)'이 들어간 종목 {len(dt)}건, 그중 START 취급 {sum(r['listed'] for r in dt)}건")
    print(f"  '양도제한부(譲渡制限付)' 종목 {sum('譲渡制限' in r['name'] for r in rows)}건, 그중 START 취급 {sum(r['listed'] for r in rows if '譲渡制限' in r['name'] and not r['digital_transfer'])}건")
    for r in li:
        print(f"    {r['issue_date']} {r['platform']:<13} {r['amt'] * 1000:>8,.0f}백만 엔  {r['name'][:38]}")
    med = lambda xs: sorted(xs)[len(xs) // 2]
    print(f"  발행액 중앙값: START 취급 {med([r['amt'] for r in li]) * 1000:,.0f}백만 엔, 비취급 {med([r['amt'] for r in rows if not r['listed']]) * 1000:,.0f}백만 엔")

    print("\nJ5. 발행일에서 START 거래 시작일까지 (ODX 공식 목록)")
    from datetime import date
    d = lambda x: date(int(x[:4]), int(x[5:7]), int(x[8:10]))
    lags = []
    for s in csv.DictReader(open(START, encoding="utf-8"), delimiter="\t"):
        hit = [r for r in rows if s["match"] in r["name"]]
        issued = hit[0]["issue_date"] if hit else "?"
        lag = (d(s["start_date"]) - d(issued)).days if hit else None
        if lag is not None and s["start_date"] <= "2026-10-28":
            lags.append(lag)
        tag = " (예정)" if s["start_date"] > "2026-10-28" else ""
        print(f"    발행 {issued} → START {s['start_date']}{tag:<5} {lag:>4}일  {s['platform']:<13} {s['short_name']}")
    quick = sum(1 for x in lags if x <= 7)
    print(f"  거래 중 {len(lags)}종목: {quick}종목은 발행 7일 안에, {len(lags) - quick}종목은 {min(x for x in lags if x > 7)}–{max(lags)}일 뒤에 거래 시작")
    print("  (2025-12-25 발행 오사카 레지던스는 BOOSTRY 목록에 START 표시가 없지만 ODX는 11월 2일 거래 시작을 공표했다)")


if __name__ == "__main__":
    main()
