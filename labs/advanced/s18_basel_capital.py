"""
18회차 실습. 은행이 토큰증권·스테이블코인·암호자산을 들고 있으면 자본이 얼마나 드나 (바젤 SCO60).

SCO60(2026년 1월 1일 시행 기준)의 큰 틀만 옮긴 단순 모형이다. 실제 계산은 신용·시장위험 세부 규정을 따라야 한다.
  Group 1a  토큰화된 전통 자산: 기초자산과 같은 위험가중치 (+ 인프라 위험 가산, 현재 0)
  Group 1b  안정화 장치가 검증된 스테이블코인: 상환 주체에 대한 청구로 보고 그 위험가중치
  Group 2a  헤지 인정 기준을 충족한 암호자산: 순포지션의 100% 자본 (단순화)
  Group 2b  나머지: 롱·숏 중 큰 쪽에 위험가중치 1250% (= 노출의 100% 자본)
  Group 2 노출 한도: 기본자본(Tier 1)의 1% 이하 권고, 2% 초과 금지. 1%를 넘는 부분은 2b, 2%를 넘으면 전부 2b.
  현행 기준은 퍼블릭(무허가형) 체인 위 자산을 Group 1로 인정하지 않는다(2024년 재확인). 2025년 11월부터 이 부분을 포함한 표적 재검토 중.

실행: python3 s18_basel_capital.py   (표준 라이브러리만)
"""

MIN_RATIO = 0.08          # 최저 자본비율 8% (완충자본 제외)
TIER1 = 10_0000_0000_0000  # 가정: 기본자본 10조 원

# (이름, 금액(원), 그룹, 기초 위험가중치 또는 None, 롱(+)/숏(-))
BOOK = [
    ("토큰화 국고채 (허가형 체인)", 2_000_0000_0000, "1a", 0.00),
    ("토큰화 A등급 회사채 (허가형)", 500_0000_0000, "1a", 0.50),
    ("토큰화 MMF (퍼블릭 체인)", 300_0000_0000, "2b", None),
    ("원화 스테이블코인 (허가형, 은행 발행)", 200_0000_0000, "1b", 0.30),   # A등급 은행 청구 가정
    ("달러 스테이블코인 (퍼블릭 체인)", 100_0000_0000, "2b", None),
]
BTC_LONG, BTC_SHORT = 80_0000_0000, -70_0000_0000   # 비트코인 현물 롱, 선물 숏


def rwa_row(amount, group, rw):
    if group in ("1a", "1b"):
        return amount * rw
    if group == "2b":
        return amount * 12.5          # 1250%
    raise ValueError(group)


def group2(long_, short_, hedge_ok):
    """Group 2a(헤지 인정)면 순포지션의 100%, 아니면 2b로 max(|롱|, |숏|)의 100%를 자본으로."""
    if hedge_ok:
        return "2a", abs(long_ + short_)
    return "2b", max(abs(long_), abs(short_))


def report(hedge_ok, book=BOOK, tier1=TIER1, btc=(BTC_LONG, BTC_SHORT)):
    print(f"\n[{'헤지 인정(2a)' if hedge_ok else '헤지 불인정(2b)'}]  기본자본 {tier1/1e12:.0f}조 원")
    print(f"  {'노출':<26}{'금액(억)':>10}{'그룹':>6}{'RWA(억)':>12}{'필요자본(억)':>12}")
    total_cap = 0.0
    g2_exposure = 0.0
    for name, amt, g, rw in book:
        rwa = rwa_row(amt, g, rw)
        cap = rwa * MIN_RATIO
        total_cap += cap
        if g.startswith("2"):
            g2_exposure += amt
        print(f"  {name:<26}{amt/1e8:>10,.0f}{g:>6}{rwa/1e8:>12,.0f}{cap/1e8:>12,.1f}")
    long_, short_ = btc
    gross = max(abs(long_), abs(short_))
    g2_exposure += gross
    ratio = g2_exposure / tier1
    g, cap = group2(long_, short_, hedge_ok)
    if g == "2a" and ratio > 0.02:                      # 2% 초과: Group 2 전부 2b
        g, cap = "2b", gross
    elif g == "2a" and ratio > 0.01:                    # 1% 초과분은 2b (초과분을 헤지 포지션에 배정, 단순화)
        excess = min(gross, g2_exposure - 0.01 * tier1)
        cap = cap * (1 - excess / gross) + excess
        g = "2a+2b"
    total_cap += cap
    print(f"  {'비트코인 롱 + 선물 숏':<26}{gross/1e8:>10,.0f}{g:>6}{cap*12.5/1e8:>12,.0f}{cap/1e8:>12,.1f}")
    status = "1% 이내" if ratio <= 0.01 else ("1% 초과분은 2b" if ratio <= 0.02 else "2% 초과: 한도 위반, Group 2 전부 2b")
    print(f"  합계 필요자본 {total_cap/1e8:,.1f}억 원   Group 2 노출 {g2_exposure/1e8:,.0f}억 = 기본자본의 {ratio:.2%} ({status})")
    return total_cap


def main():
    print("비트코인: 현물 롱 80억, 선물 숏 70억")
    a = report(hedge_ok=True)
    b = report(hedge_ok=False)
    # 같은 MMF를 허가형 체인에서 Group 1a로 인정받는다면 (기초자산: 단기 국채 → 위험가중치 0%로 가정)
    alt = [(n.replace("퍼블릭 체인", "허가형 체인"), x, "1a", 0.0) if "MMF" in n else (n, x, g, rw)
           for n, x, g, rw in BOOK]
    c = report(hedge_ok=True, book=alt)
    # 퍼블릭 체인 MMF를 2,000억으로 늘리면 Group 2가 기본자본의 2%를 넘는다
    big = [(n, 2_000_0000_0000, g, rw) if "MMF" in n else (n, x, g, rw) for n, x, g, rw in BOOK]
    d = report(hedge_ok=True, book=big)
    print(f"\n읽을 것 1: 같은 MMF 300억이 퍼블릭 체인이면 2b(전액 자본), 허가형이면 1a(0원). 차이 {(a-c)/1e8:,.0f}억 원.")
    print(f"읽을 것 2: 헤지를 인정받지 못하면 비트코인 쪽 자본이 {(b-a)/1e8:,.0f}억 원 늘어난다.")
    print(f"읽을 것 3: Group 2가 기본자본의 2%를 넘으면 헤지 인정도 사라진다(비트코인 자본 10억 → 80억). 합계 {d/1e8:,.1f}억 원.")
    return a, b, c, d


if __name__ == "__main__":
    main()
