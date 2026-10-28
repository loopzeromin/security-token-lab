"""
Lab C. 결제 지연(settlement lag)에 따른 대체비용(replacement cost) 위험

질문: 체결 후 결제까지 L일이 걸릴 때, 그 사이 상대방이 부도나면
      남은 쪽은 같은 거래를 시장에서 다시 해야 한다. 기대 손실은 L에 따라 어떻게 커지나?

가정 (모두 설명용 가정값이다. 실제 데이터로 보정하지 않았다)
  - 가격 변화 ΔP ~ N(0, σ² L)  (일간 변동성 σ, 랜덤워크)
  - 결제 전 상대방 부도 확률 = 1 - exp(-h L)  (일간 부도 강도 h)
  - 부도가 나면 손실 = 명목금액 × max(0, ΔP)  (불리한 쪽으로 움직인 만큼만 손해)
  - 부도와 가격 변화는 독립

닫힌 해:  E[손실] = (1 - e^{-hL}) · σ √L / √(2π)
몬테카를로 결과가 이 값에 붙는지 확인한다. 붙지 않으면 코드가 틀린 것이다.

실행: python3 settlement_risk.py   (numpy만 필요)
"""

import csv
import math
from pathlib import Path

import numpy as np

SIGMA = 0.01  # 일간 변동성 1%
H = 0.10 / 250  # 연 10% 부도 강도를 영업일로 나눈 값 (일부러 크게 잡았다)
NOTIONAL = 1_000_000_000  # 명목금액 10억 원
N_SIM = 2_000_000
SEED = 20261027

# 비교할 결제 방식과 지연 (영업일 기준)
REGIMES = [
    ("T+2 (주식 일반 결제)", 2.0),
    ("T+1 (미국 2024년 5월 이후)", 1.0),
    ("DVP + 오프체인 대금 확인 (가정: 반나절)", 0.5),
    ("DVP + 오프체인 대금 확인 (가정: 1시간)", 1 / 24),
    ("온체인 원자적 교환", 0.0),
]


def closed_form(lag: float) -> float:
    if lag == 0:
        return 0.0
    p_default = 1 - math.exp(-H * lag)
    return p_default * SIGMA * math.sqrt(lag) / math.sqrt(2 * math.pi)


def monte_carlo(lag: float, rng: np.random.Generator) -> tuple[float, float]:
    if lag == 0:
        return 0.0, 0.0
    # 부도는 드문 사건이라 0/1로 뽑으면 잡음이 크다.
    # 부도와 가격이 독립이므로 부도는 확률로 곱하고 가격만 뽑는다 (조건부 기댓값으로 분산 줄이기).
    p_default = 1 - math.exp(-H * lag)
    dp = rng.normal(0.0, SIGMA * math.sqrt(lag), N_SIM)
    loss = p_default * np.maximum(dp, 0.0)
    return float(loss.mean()), float(loss.std(ddof=1) / math.sqrt(N_SIM))


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = []
    print(f"σ={SIGMA:.2%}/day, h={H:.6f}/day, notional={NOTIONAL:,} KRW, N={N_SIM:,}")
    print(f"{'regime':<40}{'lag(d)':>8}{'closed(KRW)':>14}{'MC(KRW)':>14}{'MC s.e.':>10}")
    for name, lag in REGIMES:
        cf = closed_form(lag) * NOTIONAL
        mc, se = monte_carlo(lag, rng)
        mc, se = mc * NOTIONAL, se * NOTIONAL
        print(f"{name:<40}{lag:>8.3f}{cf:>14.1f}{mc:>14.1f}{se:>10.1f}")
        rows.append({"regime": name, "lag_days": lag, "closed_form_krw": round(cf, 2),
                     "mc_krw": round(mc, 2), "mc_se_krw": round(se, 2)})

    # 곡선: 지연 0~2일
    curve = [{"lag_days": round(l, 4), "expected_loss_krw": round(closed_form(l) * NOTIONAL, 3)}
             for l in np.linspace(0, 2, 81)]

    out = Path(__file__).with_name("results")
    out.mkdir(exist_ok=True)
    with open(out / "regimes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    with open(out / "curve.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=curve[0].keys())
        w.writeheader()
        w.writerows(curve)
    # 탄력성: 손실은 대략 L^{3/2}에 비례 (h L가 작을 때 1-e^{-hL} ≈ hL)
    print("ratio T+2 / T+1 =", round(closed_form(2.0) / closed_form(1.0), 3), "(≈ 2^{1.5} = 2.828)")


if __name__ == "__main__":
    main()
