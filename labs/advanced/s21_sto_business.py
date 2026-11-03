"""
21회차 실습. 한국 증권사의 토큰증권 실무: 규칙을 코드로 확인하고 사업 손익을 계산한다.

규칙의 근거 (2027-02-04 시행 예정, 숫자는 입법예고안이라 최종 확정 전이다)
  - 금융위원회 보도자료 (2026-10-01): 전자증권법·자본시장법 하위법규 개정안 입법예고 (2026-10-02 ~ 11-11)
      분산원장 참여자 = 전자등록기관(한국예탁결제원) + 계좌관리기관 2곳 이상,
      전자등록을 위한 분산원장 이용에 직접 대가(가스비 같은 것) 금지 (시행령안 제17조의3)
      가정: 발행인계좌관리기관도 "계좌관리기관 2곳"에 센다. 입법예고안 요약만으로는 분명하지 않다.
      발행인계좌관리기관 등록: 자기자본 40억 원, 계좌관리 1명·내부통제 1명·전산 2명
      일반투자자 한도: 장외거래소별 연간 순매수(총매수 - 총매도) 1억 원
  - 금융위원회 「토큰증권 정책방향」 (2026-09-04) 중 예탁결제원 분산원장 표준요건:
      독립 기관 3곳 이상이 합의·검증, 한 기관이 합의·검증 지분 50% 이상 금지,
      한 종목은 한 분산원장에서만 발행·유통
  - 비금전신탁 수익증권 모범규준의 1인당 청약한도 표준 예시: min(3,000만 원, 발행금액의 5%)

3부의 비용·수수료 숫자는 모두 설명용 가정이다. 실제 증권사 수치가 아니다.

실행: python3 s21_sto_business.py   (표준 라이브러리만)
"""

from dataclasses import dataclass

EOK = 100_000_000      # 1억 원


# ---------------------------------------------------------------- 1. 분산원장 요건
@dataclass
class Node:
    name: str
    kind: str          # "전자등록기관" | "계좌관리기관" | "발행인계좌관리기관" | "기타"
    stake: float       # 합의·검증 지분 (전체 합 1)


def check_ledger(nodes, fee_for_ledger_use=False, issued_elsewhere=False):
    """입법예고안과 표준요건을 검사한다. 위반 사유 목록을 돌려준다(빈 목록이면 통과)."""
    errs = []
    if abs(sum(n.stake for n in nodes) - 1) > 1e-9:
        errs.append("지분 합이 1이 아니다")
    if not any(n.kind == "전자등록기관" for n in nodes):
        errs.append("전자등록기관(예탁결제원)이 참여하지 않는다")
    accts = [n for n in nodes if n.kind in ("계좌관리기관", "발행인계좌관리기관")]
    if len(accts) < 2:
        errs.append(f"계좌관리기관이 {len(accts)}곳: 2곳 이상이어야 한다")
    if len(nodes) < 3:
        errs.append("합의·검증 참여 기관이 3곳 미만")
    big = [n for n in nodes if n.stake >= 0.5]
    if big:
        errs.append(f"{big[0].name}의 합의·검증 지분 {big[0].stake:.0%}: 50% 미만이어야 한다")
    if fee_for_ledger_use:
        errs.append("분산원장 이용에 직접 대가를 받는다(금지)")
    if issued_elsewhere:
        errs.append("같은 종목을 다른 분산원장에서도 발행·유통한다(금지)")
    return errs


LEDGERS = {
    "A. 증권사 단독 체인": ([Node("A증권", "계좌관리기관", 1.0)], False),
    "B. 예탁원 + 증권사 1곳": ([Node("예탁원", "전자등록기관", 0.5), Node("A증권", "계좌관리기관", 0.5)], False),
    "C. 예탁원 + 증권사 2곳, 한 곳이 60%": ([Node("예탁원", "전자등록기관", 0.2), Node("A증권", "계좌관리기관", 0.6),
                                      Node("B증권", "계좌관리기관", 0.2)], False),
    "D. 공동 인프라: 예탁원 + 증권사 3곳": ([Node("예탁원", "전자등록기관", 0.25), Node("A증권", "계좌관리기관", 0.25),
                                    Node("B증권", "계좌관리기관", 0.25), Node("C증권", "계좌관리기관", 0.25)], False),
    "E. D와 같지만 노드 이용료를 받는다": ([Node("예탁원", "전자등록기관", 0.25), Node("A증권", "계좌관리기관", 0.25),
                                   Node("B증권", "계좌관리기관", 0.25), Node("C증권", "계좌관리기관", 0.25)], True),
    "F. 예탁원 + 증권사 + 발행인계좌관리기관": ([Node("예탁원", "전자등록기관", 0.34), Node("A증권", "계좌관리기관", 0.33),
                                     Node("조각투자사", "발행인계좌관리기관", 0.33)], False),
}


# ---------------------------------------------------------------- 2. 투자 한도
LIMIT = 1 * EOK


def net_buy_check(trades, limit=LIMIT):
    """trades: (장외거래소, '매수'|'매도', 금액). 거래소별 연간 순매수가 한도를 넘는 매수를 막는다.
    반환: 체결 결과 목록과 거래소별 순매수."""
    net, log = {}, []
    for venue, side, amt in trades:
        cur = net.get(venue, 0)
        if side == "매수":
            if cur + amt > limit:
                log.append((venue, side, amt, "거절", cur))
                continue
            net[venue] = cur + amt
        else:
            net[venue] = cur - amt
        log.append((venue, side, amt, "체결", net[venue]))
    return log, net


def subscription_cap(issue_amount):
    """비금전신탁 수익증권 1인당 청약한도 표준 예시: min(3,000만 원, 발행금액의 5%)."""
    return min(30_000_000, 0.05 * issue_amount)


# ---------------------------------------------------------------- 3. 플랫폼 손익 (가정)
OWN = dict(fixed=60 * EOK, per_issue=0.3 * EOK)       # 독자 플랫폼: 연 고정비 60억, 건당 운영비 0.3억 (가정)
SHARED = dict(fixed=8 * EOK, per_issue=1.0 * EOK)     # 공동 인프라: 연 이용료 8억, 건당 비용 1.0억 (가정)
FEE_RATE = 0.012                                      # 발행 주선·인수 수수료 1.2% (가정)
DIST_FEE = 0.003                                      # 유통 중개 수수료 연 0.3% (발행액 대비 회전 가정 포함)
AVG_ISSUE = 100 * EOK                                 # 평균 발행 규모 100억 원 (가정)


def profit(model, n, avg=AVG_ISSUE):
    revenue = n * avg * (FEE_RATE + DIST_FEE)
    cost = model["fixed"] + n * model["per_issue"]
    return revenue - cost


def breakeven_between(a, b):
    """두 모델의 비용이 같아지는 발행 건수: (F_a - F_b) / (c_b - c_a)."""
    return (a["fixed"] - b["fixed"]) / (b["per_issue"] - a["per_issue"])


def main():
    print("1. 분산원장 요건 검사 (입법예고안 + 예탁원 표준요건)")
    for name, (nodes, fee) in LEDGERS.items():
        errs = check_ledger(nodes, fee_for_ledger_use=fee)
        print(f"   {name:<30} {'통과' if not errs else '불가: ' + '; '.join(errs)}")

    print("\n2. 일반투자자 한도: 장외거래소별 연간 순매수 1억 원")
    trades = [("KDX", "매수", 7_000_0000), ("KDX", "매수", 4_000_0000), ("KDX", "매도", 2_000_0000),
              ("KDX", "매수", 4_000_0000), ("NXT", "매수", 6_000_0000)]
    log, net = net_buy_check(trades)
    for v, s, a, r, cur in log:
        tail = f"순매수 {cur/1e4:,.0f}만 원" if r == "체결" else f"(현재 순매수 {cur/1e4:,.0f}만 원, 넘으면 거절)"
        print(f"   {v} {s} {a/1e4:>6,.0f}만 원 → {r:<3} {tail}")
    print("   → 판 만큼 한도가 다시 생기고, 거래소가 다르면 한도도 따로다.")
    for amt in (2 * EOK, 6 * EOK, 10 * EOK):
        print(f"   비금전신탁 수익증권 발행 {amt/EOK:.0f}억 원 → 1인당 청약한도 {subscription_cap(amt)/1e4:,.0f}만 원")

    print("\n3. 플랫폼 선택: 독자 대 공동 인프라 (모든 비용·수수료는 가정)")
    print(f"   독자: 연 고정비 {OWN['fixed']/EOK:.0f}억, 건당 {OWN['per_issue']/EOK:.1f}억 / "
          f"공동: 연 이용료 {SHARED['fixed']/EOK:.0f}억, 건당 {SHARED['per_issue']/EOK:.1f}억")
    print(f"   수입: 평균 발행 {AVG_ISSUE/EOK:.0f}억 원 × (주선 {FEE_RATE:.1%} + 유통 {DIST_FEE:.1%})"
          f" = 건당 {AVG_ISSUE*(FEE_RATE+DIST_FEE)/EOK:.1f}억 원")
    print(f"   {'연 발행 건수':>10}{'독자 손익(억)':>14}{'공동 손익(억)':>14}")
    for n in (5, 10, 20, 40, 80):
        print(f"   {n:>10}{profit(OWN, n)/EOK:>14,.1f}{profit(SHARED, n)/EOK:>14,.1f}")
    be_own = OWN["fixed"] / (AVG_ISSUE * (FEE_RATE + DIST_FEE) - OWN["per_issue"])
    be_sh = SHARED["fixed"] / (AVG_ISSUE * (FEE_RATE + DIST_FEE) - SHARED["per_issue"])
    cross = breakeven_between(OWN, SHARED)
    print(f"   손익분기 건수: 독자 {be_own:.1f}건, 공동 {be_sh:.1f}건. 두 방식 비용이 같아지는 건수 {cross:.1f}건")
    print(f"   → 이 가정에서는 연 {cross:.0f}건보다 적게 발행하면 공동 인프라가 싸다. 발행이 적은 초기 시장에서 공동 인프라에 몰리는 이유와 같다.")
    print("\n읽을 것: 규칙(노드 3곳, 50% 미만, 원장 이용 직접 대가 금지)이 '혼자 하는 체인'을 막고, 한도(순매수 1억)가 유통 규모를 정한다.")
    return be_own, be_sh, cross


if __name__ == "__main__":
    main()
