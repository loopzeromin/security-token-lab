"""
1회차 실습. 하루 거래를 건별로 결제하면 돈이 얼마나 필요하고, 차감(netting)하면 얼마나 줄어드는가

배경: BIS(1992)는 증권결제의 DVP 방식을 셋으로 나눴다.
  Model 1: 증권과 대금을 건별(gross)로 동시에 결제
  Model 2: 증권은 건별, 대금은 차감(net)해서 마지막에 결제
  Model 3: 증권과 대금을 모두 차감해서 마지막에 결제
여기서는 "대금"만 놓고 건별 결제(Model 1)와 다자간 차감(Model 2·3)이 요구하는 현금을 비교한다.

실행: python3 s01_settlement_netting.py   (표준 라이브러리만 사용)
"""

import random
from collections import defaultdict

random.seed(1)

PARTICIPANTS = ["A증권", "B증권", "C증권", "D증권", "E증권"]
N_TRADES = 200


def make_trades():
    """임의의 하루 거래: (매수자, 매도자, 금액)"""
    trades = []
    for _ in range(N_TRADES):
        buyer, seller = random.sample(PARTICIPANTS, 2)
        amount = random.randint(1, 50) * 1_000_000  # 100만~5000만 원
        trades.append((buyer, seller, amount))
    return trades


def gross_outflow(trades):
    """건별 결제: 각 참가자가 하루 동안 내보내야 하는 대금의 합"""
    out = defaultdict(int)
    for buyer, _seller, amount in trades:
        out[buyer] += amount
    return out


def multilateral_net(trades):
    """다자간 차감: 각 참가자의 (받을 돈 - 줄 돈). 음수면 그만큼만 내면 된다."""
    net = defaultdict(int)
    for buyer, seller, amount in trades:
        net[buyer] -= amount
        net[seller] += amount
    return net


def main():
    trades = make_trades()
    gross = gross_outflow(trades)
    net = multilateral_net(trades)

    assert sum(net.values()) == 0, "차감 후 합계는 0이어야 한다 (누군가 낸 돈은 누군가 받는다)"

    print(f"거래 {N_TRADES}건, 총 거래대금 {sum(a for *_, a in trades)/1e8:,.1f}억 원\n")
    print(f"{'참가자':<6}{'건별 지급(억)':>14}{'차감 후 순지급(억)':>18}")
    total_gross = total_net_pay = 0
    for p in PARTICIPANTS:
        pay = max(0, -net[p])
        total_gross += gross[p]
        total_net_pay += pay
        print(f"{p:<6}{gross[p]/1e8:>14,.1f}{pay/1e8:>18,.1f}")
    print(f"\n필요 현금 합계: 건별 {total_gross/1e8:,.1f}억 → 차감 {total_net_pay/1e8:,.1f}억 "
          f"({total_net_pay/total_gross:.1%})")
    print("생각할 것: 차감은 현금을 아끼지만 '마지막에 한꺼번에' 결제하므로 그 사이 누가 부도나면 모두가 영향을 받는다.")


if __name__ == "__main__":
    main()
