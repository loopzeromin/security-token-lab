"""
17–20회차(심화) 과제 해설. 각 회차 실습 파일의 함수를 그대로 불러 가정만 바꿔 계산한다.

실행: python3 sol_deep.py   (numpy 필요, 몇 초)
"""

import math

import s17_valuation as v
import s18_basel_capital as b
import s19_stablecoin_run as st
import s20_collateral as c


def hw17():
    print("== 17회차")
    # 과제 1: 보수 0.5% → 0.3%. 배분금이 매년 2천만 원 늘어난다.
    base_d, base_s = v.cash_flows()
    base_val = v.pv(v.DISC, base_d, base_s) / v.TOKENS
    base_irr = v.irr(v.V0, base_d, base_s)
    old_fee = v.FEE
    v.FEE = 0.003 * v.V0
    d, s = v.cash_flows()
    val, r = v.pv(v.DISC, d, s) / v.TOKENS, v.irr(v.V0, d, s)
    v.FEE = old_fee
    print(f"1. 보수 0.3%: 1토큰 {base_val:,.0f}원 → {val:,.0f}원 (+{val-base_val:,.0f}원), "
          f"IRR {base_irr:.2%} → {r:.2%} (+{(r-base_irr)*1e4:.0f}bp)")
    # 과제 2: 금리 +1%p → 할인율 7%, 매각 cap 5.25%
    d2, s2 = v.cash_flows(exit_cap=v.EXIT_CAP + 0.005)
    up = v.pv(v.DISC + 0.01, d2, s2) / v.TOKENS
    print(f"2. 할인율 7%·매각 cap 5.25%: 1토큰 {up:,.0f}원, 기본 대비 {up/base_val-1:.1%}")
    return val, r, up


def hw18():
    print("\n== 18회차")
    # 과제 1: 숏을 -80억으로 → 순포지션 0
    q = {}
    for ok in (True, False):
        g, k = b.group2(b.BTC_LONG, -b.BTC_LONG, ok)
        q[g] = k
        print(f"1. 롱 80억·숏 80억, {g}: 비트코인 필요자본 {k/1e8:,.0f}억 원")
    # 과제 2: 퍼블릭 체인 자산도 Group 1을 받는다고 가정
    #   MMF 300억 → 1a, 기초자산(단기 국채) 0%
    #   달러 스테이블코인 100억 → 1b, 발행사(무등급 일반 법인) 청구로 보고 100% (가정)
    book = []
    for n, x, g, rw in b.BOOK:
        if "MMF" in n:
            book.append((n, x, "1a", 0.0))
        elif "달러 스테이블코인" in n:
            book.append((n, x, "1b", 1.0))
        else:
            book.append((n, x, g, rw))
    print("2. 퍼블릭 체인 자산이 Group 1을 받는다면 (달러 스테이블코인 위험가중치 100% 가정)")
    total = b.report(hedge_ok=True, book=book)
    return q, total


def hw19():
    print("\n== 19회차")
    # 과제 1: A형에서 A은행 비중을 줄이고 줄인 만큼 '기타 예금'으로 옮긴다. v ≥ 0.97이 되는 최대 비중은?
    def book_with(w_a):
        return [("은행 예금: A은행", w_a, True, "A"),
                ("은행 예금: 기타", 0.2 - w_a, True, None),
                ("익일물 레포", 0.10, True, None),
                ("국채 3개월 이하", 0.70, False, None)]
    lo, hi = 0.0, 0.0825
    for _ in range(60):
        mid = (lo + hi) / 2
        nav = st.run(book_with(mid), 0.25, 0.25, "A")[2]
        lo, hi = (mid, hi) if nav >= 0.97 else (lo, mid)
    print(f"1. A은행 비중 {lo:.2%} 이하면 '25%+25%, A은행 파산' 뒤에도 v ≥ 0.97 "
          f"(검산 v = {st.run(book_with(lo), 0.25, 0.25, 'A')[2]:.4f})")
    # 과제 2: 가격 충격 0.2% → 2%
    old = st.IMPACT
    res = {}
    for imp in (0.002, 0.02):
        st.IMPACT = imp
        for name, book in (("A형", st.SVB_LIKE), ("B형", st.RULE_COMPLIANT)):
            sold, loss, nav, _ = st.run(book, 0.25, 0.25, "A")
            res[(imp, name)] = nav
            print(f"2. 충격 {imp:.1%}, {name}: 국채 매도 {sold:,.0f}, 매도 손실 {loss:,.0f} (백만$), 남은 토큰당 {nav:.4f}")
    st.IMPACT = old
    return lo, res


def hw20():
    print("\n== 20회차")
    sg, cost = 0.035, 0.003
    h1, h3 = c.haircut(sg, cost, 1), c.haircut(sg, cost, 3)
    print(f"1. 비트코인 헤어컷: 24시간 이전(MPOR 1일) {h1:.2%}, 주말 정지(MPOR 3일) {h3:.2%} (차이 {h3-h1:.2%}p)")
    flow = 10_000                        # 백만 달러
    tied8, tied05 = flow * 8 / 24, flow * 0.5 / 24
    freed = tied8 - tied05
    print(f"2. 묶이는 담보 {tied8:,.0f} → {tied05:,.0f}백만$, 풀리는 담보 {freed:,.0f}백만$, "
          f"연 4%면 이자 {freed*0.04:,.0f}백만$ (= {freed*0.04/100:,.2f}억 달러)")
    return h1, h3, freed


if __name__ == "__main__":
    hw17()
    hw18()
    hw19()
    hw20()
