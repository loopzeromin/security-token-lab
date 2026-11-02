"""
19회차 실습. 스테이블코인 준비자산의 구성과 상환 요구(런)를 견딜 수 있는가.

준비자산을 현금(은행 예금)·초단기 국채·익일물 레포·MMF로 나누고, 이틀에 걸친 상환 요구를 넣는다.
  - 은행 예금: 그 은행이 무너지면(2023년 3월 SVB처럼) 묶인다
  - 익일물 레포·MMF: 당일 현금화
  - 국채: 팔면 현금이 되지만, 한꺼번에 많이 팔면 가격이 밀린다(선형 가격 충격, 가정)
2023년 3월 10일 USDC의 준비자산 약 400억 달러 중 33억 달러가 SVB에 있었다(Circle 공시).
미국 GENIUS Act 시행 규칙(OCC 최종 규칙, 2026-10-21 공표, 2027-01-18 시행)의 숫자 일부를 넣었다:
  상대방별 집중 40% 상한, 일일 유동성 5% 하한, 상환 기한 2영업일, 24시간 안 상환 요구가 10%를 넘으면 24시간 안에 OCC에 보고.
수치는 설명용 가정이다. 실제 발행사 포트폴리오가 아니다.

실행: python3 s19_stablecoin_run.py   (표준 라이브러리만)
"""

OUT = 40_000.0              # 유통량 (백만 달러) = 400억 달러, 1토큰 = 1달러

# 구성: (이름, 비중, 당일 현금화 여부, 묶일 수 있는 은행 이름 또는 None)
SVB_LIKE = [
    ("은행 예금: A은행", 0.0825, True, "A"),    # 33억 / 400억 = 8.25%
    ("은행 예금: 기타", 0.1175, True, None),
    ("익일물 레포", 0.10, True, None),
    ("국채 3개월 이하", 0.70, False, None),
]
RULE_COMPLIANT = [
    ("은행 예금: A은행", 0.03, True, "A"),
    ("은행 예금: 기타 (여러 곳)", 0.04, True, None),
    ("익일물 레포 (중앙청산)", 0.15, True, None),
    ("정부 MMF", 0.08, True, None),
    ("국채 3개월 이하", 0.70, False, None),
]
IMPACT = 0.002      # 가정: 국채를 하루에 유통량의 10%어치 팔 때마다 가격 0.2% 하락 (선형)


def run(book, redeem_day1, redeem_day2, failed_bank=None):
    """이틀 동안 1달러씩 상환한다(먼저 온 사람부터).
    반환: 국채 매도액, 매도 손실, 남은 토큰 1개당 준비자산(묶인 예금은 0으로), 묶인 예금."""
    assert abs(sum(w for _, w, *_ in book) - 1) < 1e-9
    usable = lambda b: b is None or b != failed_bank
    liquid = sum(w * OUT for _, w, d, b in book if d and usable(b))
    frozen = sum(w * OUT for _, w, d, b in book if b is not None and b == failed_bank)
    bills = sum(w * OUT for _, w, d, b in book if not d)
    outstanding, sold_total, loss = OUT, 0.0, 0.0
    for need_frac in (redeem_day1, redeem_day2):
        need = need_frac * OUT
        pay = min(need, liquid)
        liquid -= pay
        rest = need - pay
        if rest > 0:                       # 국채를 판다. 하루에 많이 팔수록 가격이 밀린다
            price = 1 - IMPACT * (rest / OUT) / 0.10
            face = rest / price
            assert face <= bills, "국채까지 다 팔아도 모자란다"
            bills -= face
            sold_total += face
            loss += face - rest
        outstanding -= need
    nav = (liquid + bills) / outstanding
    return sold_total, loss, nav, frozen


def rule_check(book):
    """상대방 집중(국채·중앙청산 레포 제외)과 일일 유동성(예금·당일 현금화 자산)."""
    exempt = ("국채", "익일물 레포 (중앙청산)")
    worst = max(w for n, w, d, b in book if not n.startswith(exempt))
    daily = sum(w for n, w, d, b in book if d)
    return worst <= 0.40, daily >= 0.05


def main():
    print(f"유통량 {OUT/100:,.0f}억 달러, 국채 매도 가격 충격 {IMPACT:.1%} / 유통량 10%\n")
    for label, book in [("A. 2023년 3월 USDC와 비슷한 구성", SVB_LIKE), ("B. 은행 분산·레포·MMF 비중 확대", RULE_COMPLIANT)]:
        conc_ok, liq_ok = rule_check(book)
        print(label)
        for n, w, d, b in book:
            print(f"   {n:<22}{w:>7.2%}  {'당일 현금' if d else '매도 필요'}")
        print(f"   OCC 규칙: 상대방 40% 상한 {'충족' if conc_ok else '위반'}, 일일 유동성 5% {'충족' if liq_ok else '미달'}")
        for d1, d2, fail in [(0.10, 0.10, None), (0.10, 0.10, "A"), (0.25, 0.25, "A")]:
            sold, loss, nav, frozen = run(book, d1, d2, fail)
            tag = "A은행 파산" if fail else "은행 정상"
            print(f"   상환 {d1:.0%}+{d2:.0%}, {tag:<8} 국채 매도 {sold:>6,.0f}  매도 손실 {loss:>4,.0f}  "
                  f"남은 토큰당 가치 {nav:.4f}  (묶인 예금 {frozen:,.0f}, 백만$)")
        print()
    # A은행 예금이 모두 사라지는 최악의 경우 전체 토큰 가치
    worst = 1 - 0.0825
    print(f"A은행 예금이 전액 손실이면 토큰 1개당 준비자산 {worst:.4f}달러. 2023-03-11 시장가 최저는 약 0.87달러였다.")
    print("읽을 것: 손실 자체보다 '먼저 빼면 1달러, 늦으면 덜 받는다'는 기대가 런을 만든다(Diamond and Dybvig 1983).")


if __name__ == "__main__":
    main()
