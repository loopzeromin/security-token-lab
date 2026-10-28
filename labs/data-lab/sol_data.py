"""
14회차 과제 해설. fetch_buidl.py로 받은 data/buidl_transfers.csv를 그대로 쓴다.

A1. 가장 큰 주소 하나를 빼면 집중도는 얼마나 달라지나?
A2. '매달 배당을 새 토큰으로 준다'는 설명이 기록과 맞나?
    배당이라면 매달 초 발행 건수가 그 시점 보유자 수와 비슷해야 한다.
A3. 보유자 간 이전은 거래량으로 보면 발행에 비해 얼마나 되나?

실행: python sol_data.py
"""

import os
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(os.environ.get("ST_DATA_DIR", Path(__file__).parent / "data"))  # 다른 폴더에 받으려면 ST_DATA_DIR 지정
ZERO = "0x" + "0" * 40


def load():
    rows = []
    with open(DATA / "buidl_transfers.csv") as f:
        for r in csv.DictReader(f):
            r["amount"] = float(r["amount"])
            r["ts"] = datetime.fromtimestamp(int(r["timestamp"]), tz=timezone.utc)
            rows.append(r)
    return [r for r in rows if r["amount"] > 0]      # 금액 0 기록 제외 (analyze_buidl.py와 같음)


def balances(rows):
    bal = defaultdict(float)
    for r in rows:
        if r["from"] != ZERO:
            bal[r["from"]] -= r["amount"]
        if r["to"] != ZERO:
            bal[r["to"]] += r["amount"]
    return {a: v for a, v in bal.items() if v > 1e-6}


def concentration(vals):
    tot = sum(vals)
    sh = sorted((v / tot for v in vals), reverse=True)
    return sum(sh[:5]), sum(s * s for s in sh) * 10_000


def a1(rows):
    print("A1. 가장 큰 주소를 뺀 집중도")
    bal = balances(rows)
    vals = sorted(bal.values(), reverse=True)
    t5, h = concentration(vals)
    t5x, hx = concentration(vals[1:])
    print(f"  전체 {len(vals)}개 주소: 상위 5개 {t5:.1%}, HHI {h:,.0f}")
    print(f"  1위 제외 {len(vals) - 1}개 주소: 상위 5개 {t5x:.1%}, HHI {hx:,.0f}")
    print(f"  1위 주소 보유 비중 {vals[0] / sum(vals):.1%}")


def a2(rows):
    print("\nA2. 매달 1~3일 발행 건수와 그 직전 보유자 수")
    print(f"  {'월':<8}{'1~3일 발행 건':>14}{'직전 보유자':>12}{'비율':>8}{'1~3일 발행액(백만)':>20}")
    bal = defaultdict(float)
    months = sorted({r["ts"].strftime("%Y-%m") for r in rows})
    i = 0
    ratios = []
    for m in months:
        # 그 달 1일 0시(UTC) 전까지의 기록으로 보유자 수를 센다
        start = datetime.strptime(m + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
        while i < len(rows) and rows[i]["ts"] < start:
            r = rows[i]
            if r["from"] != ZERO:
                bal[r["from"]] -= r["amount"]
            if r["to"] != ZERO:
                bal[r["to"]] += r["amount"]
            i += 1
        holders = sum(1 for v in bal.values() if v > 1e-6)
        early = [r for r in rows if r["from"] == ZERO and r["ts"].strftime("%Y-%m") == m and r["ts"].day <= 3]
        if holders == 0:
            continue
        ratio = len(early) / holders
        ratios.append(ratio)
        print(f"  {m:<8}{len(early):>14}{holders:>12}{ratio:>8.2f}{sum(r['amount'] for r in early) / 1e6:>20.2f}")
    if ratios:
        ratios.sort()
        print(f"  비율 중앙값 {ratios[len(ratios) // 2]:.2f} (1에 가까우면 '보유자마다 매달 한 번 발행'과 맞는다)")


def a3(rows):
    print("\nA3. 거래량 비교 (백만 개)")
    mint = sum(r["amount"] for r in rows if r["from"] == ZERO)
    burn = sum(r["amount"] for r in rows if r["to"] == ZERO)
    p2p = sum(r["amount"] for r in rows if ZERO not in (r["from"], r["to"]))
    print(f"  발행 {mint / 1e6:,.1f}, 상환 {burn / 1e6:,.1f}, 보유자 간 이전 {p2p / 1e6:,.1f}")
    print(f"  보유자 간 이전 / 발행 = {p2p / mint:.2f}")


if __name__ == "__main__":
    rows = load()
    a1(rows)
    a2(rows)
    a3(rows)
