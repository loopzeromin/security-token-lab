"""
13회차 실습. 자격 제한과 투자 한도가 유동성을 얼마나 줄이는가

단순한 매칭 시장:
  - 투자자 N명 중 비율 q만 이 토큰을 받을 자격이 있다 (KYC·적격투자자·국가 제한 등)
  - 매 거래일 매도 주문 40건이 새로 나오고, 주문마다 무작위로 M명의 매수 후보에게 호가가 닿는다
  - 후보 중 '자격이 있고, 사려는 의향이 있고(확률 b), 연간 한도가 남은' 사람이 있으면 체결
  - 체결 못 하면 다음 기간에 다시 시도하고, 20거래일이 지나면 주문을 거둔다(미체결)
한국 입법예고안의 '장외거래소별 일반투자자 연간 순매수 1억 원'을 한도로 넣어 본다.

단순화: 매수자는 다시 팔지 않으므로 순매수 = 매수 합계다. 모형은 설명용이다. N, M, B, 금액은 가정값이고 실제 시장 데이터로 보정하지 않았다.
실행: python3 s13_liquidity_sim.py   (numpy 필요)
"""

import numpy as np

RNG = np.random.default_rng(20261028)
N = 5_000          # 투자자 수
M = 20             # 한 기간에 호가가 닿는 후보 수
B = 0.05           # 후보가 살 의향이 있을 확률
LOT = 20_000_000   # 한 번 거래 금액 (2천만 원)
LIMIT = 100_000_000  # 연간 순매수 한도 1억 원
PERIODS = 250      # 1년 = 250 거래일
SELLERS_PER_DAY = 40
EXPIRE = 20         # 20거래일 안에 못 팔면 주문 취소(미체결)


def simulate(q: float, with_limit: bool) -> tuple[float, float]:
    eligible = RNG.random(N) < q
    bought = np.zeros(N)
    waits, unsold = [], 0
    queue: list[int] = []                     # 아직 못 판 매도 주문의 대기 기간
    for _day in range(PERIODS):
        aged = [w + 1 for w in queue]
        unsold += sum(1 for w in aged if w > EXPIRE)
        queue = [w for w in aged if w <= EXPIRE] + [0] * SELLERS_PER_DAY
        still = []
        for w in queue:
            cands = RNG.integers(0, N, M)
            ok = eligible[cands] & (RNG.random(M) < B)
            if with_limit:
                ok &= bought[cands] + LOT <= LIMIT
            hit = np.flatnonzero(ok)
            if hit.size:
                bought[cands[hit[0]]] += LOT
                waits.append(w)
            else:
                still.append(w)
        queue = still
    unsold += len(queue)
    total = len(waits) + unsold
    return len(waits) / total, float(np.mean(waits)) if waits else float("nan")


def main():
    print(f"N={N}, 후보 {M}명, 의향 {B:.0%}, 1회 {LOT/1e6:.0f}백만 원, 연 {PERIODS}일, 하루 매도 {SELLERS_PER_DAY}건\n")
    print(f"{'자격 비율 q':>10}{'체결률(한도 없음)':>18}{'평균 대기일':>12}{'체결률(1억 한도)':>18}{'평균 대기일':>12}")
    rows = []
    for q in [1.0, 0.5, 0.2, 0.1, 0.05]:
        f0, w0 = simulate(q, False)
        f1, w1 = simulate(q, True)
        rows.append((q, f0, w0, f1, w1))
        print(f"{q:>10.2f}{f0:>18.1%}{w0:>12.2f}{f1:>18.1%}{w1:>12.2f}")
    # 자격 비율이 낮을수록 체결률이 떨어져야 한다
    assert rows[0][1] >= rows[-1][1]
    cap = lambda q: q * N * (LIMIT // LOT)
    print(f"\n1억 한도 아래 1년 최대 매수 건수 = 자격자 수 × 5건. q=0.2이면 {cap(0.2):,.0f}건, 매도 주문은 {SELLERS_PER_DAY*PERIODS:,}건.")
    print("\n읽을 것: 자격 제한은 매수 후보 풀을 q배로 줄이고, 한도는 그 풀을 해마다 더 줄인다.")
    print("자격 비율이 낮은 상품일수록 한도의 영향이 커지는지 표에서 확인한다.")


if __name__ == "__main__":
    main()
