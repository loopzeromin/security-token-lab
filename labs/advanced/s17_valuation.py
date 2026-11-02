"""
17회차 실습. 토큰증권의 가치: 현금흐름 할인(DCF), 유동성 할인, 세후 수익률.

대상: 15회차 가상 상품 '한강 오피스 신탁 수익증권 토큰'(발행 100억 원, 1토큰 5,000원, 2,000,000토큰).
아래 숫자는 모두 설명용 가정이다. 실제 건물·시장 자료로 보정하지 않았다.

  1. DCF: 순영업소득(NOI) - 신탁·운용 보수 = 배분금, 5년 뒤 매각(매각 cap rate)
  2. 발행가 5,000원일 때의 내부수익률(IRR)과 민감도(할인율 × 매각 cap rate)
  3. 유동성 할인의 상한: Longstaff(1995). 팔 수 없는 기간 T 동안의 '완벽한 매도 시점' 가치
     F/V = (2 + σ²T/2)·N(σ√T/2) + σ√(T/(2π))·exp(-σ²T/8) - 1   (무위험 이자율 0, 드리프트 0 가정)
     닫힌 해를 몬테카를로로 다시 확인한다.
  4. 세후 배분 수익률: 한국 배당소득 원천징수 15.4%, 일본 신탁 수익증권형 ST 20.315% (분리과세 가정)

실행: python3 s17_valuation.py   (numpy 필요, 5초 안팎)
"""

import math

import numpy as np

PRICE = 5_000
TOKENS = 2_000_000
V0 = PRICE * TOKENS                 # 100억 원
NOI1 = 460_000_000                  # 가정: 1년 차 순영업소득 4.6억 원 (취득 cap rate 4.6%)
GROWTH = 0.015                      # 가정: NOI 연 1.5% 증가
FEE = 0.005 * V0                    # 가정: 신탁·운용·플랫폼 보수 연 0.5% (5천만 원)
HOLD = 5
EXIT_CAP = 0.0475                   # 가정: 5년 뒤 매각 cap rate
SALE_COST = 0.02                    # 가정: 매각 비용 2%
DISC = 0.06                         # 가정: 할인율 6%


def cash_flows(noi1=NOI1, g=GROWTH, exit_cap=EXIT_CAP, hold=HOLD):
    """연도별 배분금(1..hold)과 마지막 해 매각 순수입. 원 단위."""
    noi = [noi1 * (1 + g) ** t for t in range(hold + 1)]       # noi[hold]는 매각 다음 해 NOI
    dist = [noi[t] - FEE for t in range(hold)]
    sale = noi[hold] / exit_cap * (1 - SALE_COST)
    return dist, sale


def pv(rate, dist, sale):
    return sum(d / (1 + rate) ** (t + 1) for t, d in enumerate(dist)) + sale / (1 + rate) ** len(dist)


def irr(price, dist, sale, lo=-0.5, hi=0.5):
    for _ in range(200):
        mid = (lo + hi) / 2
        if pv(mid, dist, sale) > price:
            lo = mid
        else:
            hi = mid
    return mid


def longstaff(sigma, T):
    """Longstaff(1995) 유동성 할인 상한, 가치 대비 비율."""
    s = sigma * math.sqrt(T)
    N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    return (2 + s * s / 2) * N(s / 2) + s / math.sqrt(2 * math.pi) * math.exp(-s * s / 8) - 1


def longstaff_mc(sigma, T, n=200_000, steps=500, seed=20261029):
    """같은 값을 경로 시뮬레이션으로: E[max_t V_t] / V0 - 1, 드리프트는 위험중립(r=0)."""
    # 구간 끝점만 보면 최댓값을 놓친다(이산 관측 편향). 두 끝점 사이 브라운 다리의 최댓값을
    # 정확한 분포에서 뽑아 연속 관측과 같게 만든다: M = (a + b + sqrt((b-a)^2 - 2σ²dt·ln U)) / 2
    rng = np.random.default_rng(seed)
    dt = T / steps
    logv = np.zeros(n)
    m = np.zeros(n)
    for _ in range(steps):
        nxt = logv - 0.5 * sigma ** 2 * dt + sigma * math.sqrt(dt) * rng.standard_normal(n)
        u = rng.random(n)
        bridge_max = (logv + nxt + np.sqrt((nxt - logv) ** 2 - 2 * sigma ** 2 * dt * np.log(u))) / 2
        np.maximum(m, bridge_max, out=m)
        logv = nxt
    return float(np.exp(m).mean() - 1)


def main():
    dist, sale = cash_flows()
    print("1. 현금흐름 (억 원)")
    for t, d in enumerate(dist, 1):
        print(f"   {t}년 차 배분 {d/1e8:6.3f}   배분 수익률 {d/V0:5.2%}")
    print(f"   5년 차 매각 순수입 {sale/1e8:7.2f}  (매각 cap {EXIT_CAP:.2%}, 비용 {SALE_COST:.0%})")
    value = pv(DISC, dist, sale)
    print(f"\n2. 할인율 {DISC:.0%}의 가치 {value/1e8:.2f}억 원 → 1토큰 {value/TOKENS:,.0f}원 (발행가 {PRICE:,}원)")
    r = irr(V0, dist, sale)
    print(f"   발행가 기준 IRR {r:.2%}")
    print("\n   민감도: 1토큰 가치(원), 행 = 할인율, 열 = 매각 cap rate")
    caps = [0.0425, 0.0475, 0.0525]
    print("            " + "".join(f"{c:>10.2%}" for c in caps))
    for d in [0.05, 0.06, 0.07]:
        row = []
        for c in caps:
            ds, sl = cash_flows(exit_cap=c)
            row.append(pv(d, ds, sl) / TOKENS)
        print(f"   {d:>7.0%}  " + "".join(f"{x:>10,.0f}" for x in row))

    print("\n3. 유동성 할인 상한 (Longstaff 1995), 가치 대비 %")
    print(f"   {'σ(연)':>6} {'T':>10} {'닫힌 해':>8} {'시뮬레이션':>10}")
    for sigma, T, lab in [(0.10, 4.32 / 250, "4.32영업일"), (0.10, 0.5, "6개월"), (0.10, 5.0, "5년"),
                          (0.20, 1.0, "1년"), (0.30, 1.0, "1년")]:
        cf = longstaff(sigma, T)
        mc = longstaff_mc(sigma, T, n=100_000, steps=50) if T <= 1 else float("nan")
        mcs = f"{mc:>9.2%}" if not math.isnan(mc) else "        -"
        print(f"   {sigma:>6.0%} {lab:>10} {cf:>8.2%} {mcs}")
    assert abs(longstaff(0.30, 1.0) - longstaff_mc(0.30, 1.0, n=100_000, steps=50)) < 0.005

    print("\n4. 세후 배분 수익률 (1년 차 배분 기준)")
    y = dist[0] / V0
    for name, tax in [("한국 배당소득 원천징수 15.4%", 0.154), ("일본 분리과세 20.315%", 0.20315),
                      ("한국 종합과세 35% 구간 가정(지방세 포함 38.5%)", 0.385)]:
        print(f"   {name:<34} 세전 {y:.2%} → 세후 {y*(1-tax):.2%}")
    print("\n읽을 것: 토큰은 현금흐름을 바꾸지 않는다. 바뀌는 것은 보수(F), 팔 수 있는 시간(T), 세금이다.")


if __name__ == "__main__":
    main()
