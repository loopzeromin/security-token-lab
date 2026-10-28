"""
실증 실습 2단계. 받은 BUIDL Transfer 기록으로 '토큰화 펀드가 실제로 어떻게 쓰이는가'를 본다.

질문
  Q1. 발행(mint)과 상환(burn)으로 이더리움 위 BUIDL 잔액은 어떻게 변했나? 기록으로 다시 쌓은 잔액이 계약의 총발행과 맞나?
  Q2. 보유자는 몇 명이고 얼마나 집중돼 있나? (상위 5개 비중, HHI)
  Q3. 보유자끼리의 이전(2차 거래에 가까운 움직임)은 얼마나 자주, 얼마나 크게 일어나나?
  Q4. 발행 이벤트에 달마다 반복되는 패턴이 있나? (매월 초 소액 발행이 몰리는지)

주소 0x000…000에서 나오는 이전 = 발행, 그 주소로 가는 이전 = 상환(소각)이다(ERC-20 관행).
실행: python analyze_buidl.py   (numpy 필요. fetch_buidl.py, check_supply.py를 먼저 실행)
결과: 화면 출력 + data/summary_monthly.csv, data/summary_holders.csv
"""

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

DATA = Path(__file__).parent / "data"
ZERO = "0x" + "0" * 40


def load():
    rows = []
    with open(DATA / "buidl_transfers.csv") as f:
        for r in csv.DictReader(f):
            r["amount"] = float(r["amount"])
            r["ts"] = datetime.fromtimestamp(int(r["timestamp"]), tz=timezone.utc)
            rows.append(r)
    meta = json.loads((DATA / "buidl_meta.json").read_text())
    return rows, meta


def hhi(shares):
    return float(np.sum(np.square(shares)) * 10_000)   # 0–10,000. 미국 2023년 합병 지침은 1,800 초과를 고집중으로 본다


def main():
    rows, meta = load()
    print(f"기간 {rows[0]['ts']:%Y-%m-%d} ~ {rows[-1]['ts']:%Y-%m-%d}, 이벤트 {len(rows):,}건\n")

    # Q1 발행·상환과 잔액 재구성
    bal = defaultdict(float)
    monthly = defaultdict(lambda: {"mint": 0.0, "burn": 0.0, "n_mint": 0, "n_burn": 0, "n_p2p": 0, "v_p2p": 0.0})
    mint_days = defaultdict(int)
    p2p_sizes = []
    for r in rows:
        m = r["ts"].strftime("%Y-%m")
        frm, to, a = r["from"], r["to"], r["amount"]
        if frm == ZERO:
            monthly[m]["mint"] += a; monthly[m]["n_mint"] += 1
            mint_days[r["ts"].day] += 1
        elif to == ZERO:
            monthly[m]["burn"] += a; monthly[m]["n_burn"] += 1
        else:
            monthly[m]["n_p2p"] += 1; monthly[m]["v_p2p"] += a
            p2p_sizes.append(a)
        if frm != ZERO:
            bal[frm] -= a
        if to != ZERO:
            bal[to] += a

    rebuilt = sum(v for v in bal.values() if v > 1e-9)
    print("Q1. 월별 발행·상환 (백만 개, 1개 ≈ 1달러)")
    print(f"{'월':<8}{'발행':>10}{'상환':>10}{'순증':>10}{'누적':>10}{'발행 건':>8}{'이전 건':>8}")
    cum = 0.0
    out = []
    for m in sorted(monthly):
        d = monthly[m]
        cum += d["mint"] - d["burn"]
        out.append([m, d["mint"], d["burn"], d["mint"] - d["burn"], cum, d["n_mint"], d["n_burn"], d["n_p2p"], d["v_p2p"]])
        print(f"{m:<8}{d['mint']/1e6:>10.1f}{d['burn']/1e6:>10.1f}{(d['mint']-d['burn'])/1e6:>10.1f}{cum/1e6:>10.1f}{d['n_mint']:>8}{d['n_p2p']:>8}")
    gap = rebuilt - meta["total_supply_now"]
    print(f"\n  기록으로 다시 쌓은 잔액 합 {rebuilt:,.2f} / 계약의 현재 총발행 {meta['total_supply_now']:,.2f} / 차이 {gap:,.4f}")

    # Q2 보유자 집중도
    holders = sorted(((a, v) for a, v in bal.items() if v > 1e-6), key=lambda x: -x[1])
    vals = np.array([v for _, v in holders])
    shares = vals / vals.sum()
    print(f"\nQ2. 현재 보유자 {len(holders)}개 주소")
    print(f"  상위 1개 {shares[:1].sum():.1%}, 상위 5개 {shares[:5].sum():.1%}, 상위 10개 {shares[:10].sum():.1%}, HHI {hhi(shares):,.0f}")
    print(f"  보유액 중앙값 {np.median(vals)/1e6:,.2f}백만, 평균 {vals.mean()/1e6:,.2f}백만")
    ever = {r['to'] for r in rows if r['to'] != ZERO} | {r['from'] for r in rows if r['from'] != ZERO}
    print(f"  한 번이라도 보유했던 주소 {len(ever)}개")

    # Q3 보유자 간 이전
    n_p2p = len(p2p_sizes)
    print(f"\nQ3. 보유자 간 이전 {n_p2p:,}건, 전체 이벤트의 {n_p2p/len(rows):.1%}")
    if n_p2p:
        s = np.array(p2p_sizes)
        print(f"  건당 중앙값 {np.median(s):,.0f}, 평균 {s.mean():,.0f}, 최대 {s.max():,.0f}")
        pairs = defaultdict(int)
        for r in rows:
            if ZERO not in (r["from"], r["to"]):
                pairs[(r["from"], r["to"])] += 1
        top = sorted(pairs.items(), key=lambda x: -x[1])[:5]
        print(f"  가장 잦은 주소 쌍 5개의 이전 건수: {[c for _, c in top]} (전체의 {sum(c for _, c in top)/n_p2p:.0%})")

    # Q4 발행일 패턴
    total_mints = sum(mint_days.values())
    first3 = sum(mint_days[d] for d in (1, 2, 3))
    print(f"\nQ4. 발행 {total_mints:,}건 중 매월 1~3일 {first3:,}건 ({first3/max(total_mints,1):.0%})")
    small = [r["amount"] for r in rows if r["from"] == ZERO]
    print(f"  발행 1건 금액 중앙값 {np.median(small):,.0f}, 평균 {np.mean(small):,.0f}")

    with open(DATA / "summary_monthly.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "mint", "burn", "net", "cumulative", "n_mint", "n_burn", "n_p2p", "v_p2p"])
        w.writerows(out)
    with open(DATA / "summary_holders.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "address", "balance", "share"])
        for i, ((a, v), sh) in enumerate(zip(holders, shares), 1):
            w.writerow([i, a, round(v, 2), round(float(sh), 6)])
    print("\n저장: data/summary_monthly.csv, data/summary_holders.csv")


if __name__ == "__main__":
    main()
