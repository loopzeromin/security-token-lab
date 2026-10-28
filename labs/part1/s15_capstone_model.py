"""
15회차 완성 사례. 가상 상품 '한강 오피스 신탁 수익증권 토큰'의 규칙 모형과 위험 수치.

상품(가상): 서울의 오피스 빌딩 한 동을 신탁하고, 그 수익권(비금전신탁 수익증권)을 토큰으로 발행한다.
  발행총액 100억 원, 1토큰 = 5,000원, 2,000,000토큰. 임대 수익을 분기마다 현금으로 배분한다.
  2027년 2월 시행 개정 전자증권법·자본시장법과 2026년 10월 입법예고된 시행령안을 전제로 한다.

이 파일이 구현하는 상품 규칙 (설명서 Table 15.2와 같은 번호)
  R1 계좌관리기관(증권사)이 신원을 확인해 등록한 지갑만 보유할 수 있다
  R2 일반투자자는 장외거래소별로 같은 해 순매수(산 금액 − 판 금액)가 1억 원을 넘을 수 없다. 전문투자자는 예외
  R3 강제 이전(상속·압류)은 3명 중 2명이 '같은 내용'을 승인해야 실행되고, 받는 지갑도 R1을 통과해야 한다
  R4 지갑 분실 복구는 그 투자자를 등록한 계좌관리기관만 할 수 있고, 새 지갑은 같은 투자자로 등록되어 있어야 한다
  R5 배분은 기준일 보유 수량에 비례하고, 배분 합계는 배분할 현금과 같아야 한다
  R6 규칙(로직) 변경은 공지 후 7일이 지나야 실행된다
뒤쪽은 결제 방식 세 가지의 기대손실(Lab C 식)과 이 상품 조건의 유동성 시뮬레이션(13회차 모형)이다.
수치 가정은 모두 설명용이며 실제 시장 데이터로 보정하지 않았다.

실행: python3 s15_capstone_model.py   (numpy 필요, 10초 안팎)
"""

import hashlib
import math
from collections import defaultdict

import numpy as np

PRICE = 5_000                  # 원/토큰
RETAIL_LIMIT = 100_000_000     # 장외거래소별 연간 순매수 한도 (입법예고안)
TIMELOCK_DAYS = 7


class Revert(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise Revert(msg)


class HangangToken:
    def __init__(self, issuer, managers, signers):
        self.issuer = issuer
        self.managers = set(managers)          # 계좌관리기관(증권사)
        self.signers = set(signers)            # 강제 이전 승인자 3명
        self.investor_of = {}                  # 지갑 → 투자자 번호
        self.kind = {}                         # 투자자 번호 → '일반' | '전문'
        self.manager_of = {}                   # 투자자 번호 → 등록한 계좌관리기관
        self.bal = defaultdict(int)
        self.net = defaultdict(int)            # (투자자, 거래소, 연도) → 순매수 금액(원)
        self.approvals = defaultdict(set)      # 승인 대상 해시 → 승인자 집합
        self.pending_logic = None              # (새 로직 이름, 공지일)
        self.logic = "v1"
        self.paused = False

    # R1 ----------------------------------------------------------------
    def register(self, manager, wallet, investor, kind="일반"):
        require(manager in self.managers, "only account manager")
        require(self.manager_of.get(investor, manager) == manager, "investor managed elsewhere")
        self.investor_of[wallet] = investor
        self.kind[investor] = kind
        self.manager_of[investor] = manager

    def issue(self, sender, to, amount):
        require(sender == self.issuer, "only issuer")
        require(to in self.investor_of, "R1 recipient not registered")
        self.bal[to] += amount

    # R1 + R2 -----------------------------------------------------------
    def trade(self, venue, year, seller, buyer, amount):
        require(not self.paused, "paused")
        require(buyer in self.investor_of, "R1 recipient not registered")
        require(self.bal[seller] >= amount, "insufficient balance")
        value = amount * PRICE
        b, s = self.investor_of[buyer], self.investor_of[seller]
        if self.kind[b] == "일반":
            require(self.net[(b, venue, year)] + value <= RETAIL_LIMIT, "R2 retail annual net purchase limit")
        self.bal[seller] -= amount
        self.bal[buyer] += amount
        self.net[(b, venue, year)] += value
        self.net[(s, venue, year)] -= value

    # R3 ----------------------------------------------------------------
    @staticmethod
    def _action_id(frm, to, amount, reason):
        return hashlib.sha256(f"{frm}|{to}|{amount}|{reason}".encode()).hexdigest()[:16]

    def approve_forced(self, signer, frm, to, amount, reason):
        require(signer in self.signers, "not a signer")
        self.approvals[self._action_id(frm, to, amount, reason)].add(signer)

    def forced_transfer(self, frm, to, amount, reason):
        aid = self._action_id(frm, to, amount, reason)
        require(len(self.approvals[aid]) >= 2, "R3 needs 2-of-3 approvals for this exact transfer")
        require(to in self.investor_of, "R1 recipient not registered")
        require(self.bal[frm] >= amount, "insufficient balance")
        self.bal[frm] -= amount
        self.bal[to] += amount
        del self.approvals[aid]

    # R4 ----------------------------------------------------------------
    def recover(self, manager, lost, new):
        inv = self.investor_of.get(lost)
        require(inv is not None, "unknown wallet")
        require(self.manager_of[inv] == manager, "R4 only the investor's own account manager")
        require(self.investor_of.get(new) == inv, "R4 new wallet must belong to the same investor")
        self.bal[new] += self.bal[lost]
        self.bal[lost] = 0

    # R5 ----------------------------------------------------------------
    def distribute(self, cash):
        holders = {w: b for w, b in self.bal.items() if b > 0}
        total = sum(holders.values())
        pay = {w: cash * b // total for w, b in holders.items()}
        rest = cash - sum(pay.values())            # 나눗셈 나머지는 가장 많이 가진 지갑에
        pay[max(holders, key=holders.get)] += rest
        require(sum(pay.values()) == cash, "R5 payout must equal cash")
        return pay

    # R6 ----------------------------------------------------------------
    def propose_logic(self, sender, name, day):
        require(sender == self.issuer, "only issuer")
        self.pending_logic = (name, day)

    def execute_logic(self, day):
        require(self.pending_logic is not None, "nothing proposed")
        name, at = self.pending_logic
        require(day - at >= TIMELOCK_DAYS, "R6 timelock: 7 days after notice")
        self.logic, self.pending_logic = name, None


def scenarios():
    t = HangangToken("한강신탁", ["증권사A", "증권사B"], ["준법감시인", "신탁사 임원", "외부 감사인"])
    t.register("증권사A", "민_지갑", "민")
    t.register("증권사A", "민_새지갑", "민")
    t.register("증권사B", "지수_지갑", "지수")
    t.register("증권사B", "연금_지갑", "연금기금", kind="전문")
    t.register("증권사A", "상속인_지갑", "상속인")
    t.issue("한강신탁", "연금_지갑", 1_000_000)
    t.issue("한강신탁", "지수_지갑", 200_000)

    def run(name, rule, expect_ok, fn):
        try:
            fn()
            got = "통과"
        except Revert as e:
            got = f"거절: {e}"
        ok = (got == "통과") == expect_ok
        print(f"  {'PASS' if ok else 'FAIL'}  [{rule}] {name}\n        기대 {'통과' if expect_ok else '거절'} / 결과 {got}")
        return ok

    print("상품 규칙 시나리오")
    results = [
        run("등록된 민이 장외거래소에서 4천만 원어치 매수", "R1·R2", True,
            lambda: t.trade("KDX", 2027, "연금_지갑", "민_지갑", 8_000)),
        run("등록 안 된 지갑이 매수", "R1", False,
            lambda: t.trade("KDX", 2027, "연금_지갑", "익명_지갑", 100)),
        run("민이 같은 해 같은 거래소에서 7천만 원 더 매수 (누적 1억 1천만)", "R2", False,
            lambda: t.trade("KDX", 2027, "연금_지갑", "민_지갑", 14_000)),
        run("민이 2천만 원어치를 판 뒤 다시 7천만 원 매수 (순매수 9천만)", "R2", True,
            lambda: (t.trade("KDX", 2027, "민_지갑", "지수_지갑", 4_000),
                     t.trade("KDX", 2027, "연금_지갑", "민_지갑", 14_000))),
        run("민이 다른 거래소(NXT)에서 3천만 원 매수 (거래소별 한도)", "R2", True,
            lambda: t.trade("NXT", 2027, "연금_지갑", "민_지갑", 6_000)),
        run("전문투자자 연금기금이 5억 원어치 매수", "R2", True,
            lambda: t.trade("KDX", 2027, "지수_지갑", "연금_지갑", 100_000)),
    ]
    # R3: 지수 지갑을 상속인에게
    t.approve_forced("준법감시인", "지수_지갑", "상속인_지갑", 50_000, "상속")
    results.append(run("승인 1개로 강제 이전", "R3", False,
                       lambda: t.forced_transfer("지수_지갑", "상속인_지갑", 50_000, "상속")))
    t.approve_forced("외부 감사인", "지수_지갑", "상속인_지갑", 50_000, "상속")
    results.append(run("승인된 내용과 다른 지갑으로 강제 이전 (바꿔치기)", "R3", False,
                       lambda: t.forced_transfer("지수_지갑", "민_지갑", 50_000, "상속")))
    results.append(run("같은 내용 2-of-3 승인 뒤 강제 이전", "R3", True,
                       lambda: t.forced_transfer("지수_지갑", "상속인_지갑", 50_000, "상속")))
    results.append(run("다른 증권사가 민의 지갑을 복구", "R4", False,
                       lambda: t.recover("증권사B", "민_지갑", "민_새지갑")))
    results.append(run("민의 지갑을 지수의 지갑으로 '복구'", "R4", False,
                       lambda: t.recover("증권사A", "민_지갑", "지수_지갑")))
    results.append(run("증권사A가 민의 새 지갑으로 복구", "R4", True,
                       lambda: t.recover("증권사A", "민_지갑", "민_새지갑")))
    pay = {}
    results.append(run("분기 배분 1억 2,345만 6,789원", "R5", True,
                       lambda: pay.update(t.distribute(123_456_789))))
    t.propose_logic("한강신탁", "v2", day=0)
    results.append(run("규칙 변경 공지 3일 뒤 실행", "R6", False, lambda: t.execute_logic(day=3)))
    results.append(run("규칙 변경 공지 7일 뒤 실행", "R6", True, lambda: t.execute_logic(day=7)))

    print(f"\n  {sum(results)}/{len(results)} 시나리오가 기대와 같다")
    print("  배분 결과:", {w: f"{v:,}" for w, v in sorted(pay.items(), key=lambda x: -x[1])})
    print(f"  보유 수량 합 {sum(t.bal.values()):,} (발행 1,200,000과 같아야 함)")
    return all(results)


# ---------------------------------------------------------------- 위험 수치
def settlement_table():
    sigma = 0.005                 # 가정: 토큰 가격 일간 변동성 0.5% (상장 주식 1%의 절반)
    notional = 1_000_000_000      # 10억 원 거래 한 건
    print("\n결제 방식별 기대 대체비용 (Lab C 식 (5.1), 10억 원 한 건, σ=0.5%/일)")
    print(f"  {'결제 방식':<34}{'L(영업일)':>9}{'연 부도율 10%':>15}{'연 부도율 0.5%':>15}")
    rows = [("A. 장외거래소 체결 후 T+2 (일본 START와 같음)", 2.0),
            ("B. DvP + 은행 이체 확인 (반나절 가정)", 0.5),
            ("C. DvP + 은행 이체 확인 (1시간 가정)", 1 / 24),
            ("D. 예금토큰 원자적 DvP (같은 원장, 미래)", 0.0)]
    for name, L in rows:
        out = []
        for pd in (0.10, 0.005):
            h = pd / 250
            out.append(notional * (1 - math.exp(-h * L)) * sigma * math.sqrt(L) / math.sqrt(2 * math.pi))
        print(f"  {name:<34}{L:>9.3f}{out[0]:>13,.1f}원{out[1]:>13,.2f}원")


def liquidity_table():
    rng = np.random.default_rng(20261028)
    N, M, B, PERIODS, SELLERS, EXPIRE = 5_000, 20, 0.05, 250, 40, 20

    def sim(q, lot, limit):
        eligible = rng.random(N) < q
        bought = np.zeros(N)
        queue, done, unsold = [], 0, 0
        for _ in range(PERIODS):
            aged = [w + 1 for w in queue]
            unsold += sum(1 for w in aged if w > EXPIRE)
            queue = [w for w in aged if w <= EXPIRE] + [0] * SELLERS
            still = []
            for w in queue:
                c = rng.integers(0, N, M)
                ok = eligible[c] & (rng.random(M) < B)
                if limit:
                    ok &= bought[c] + lot <= limit
                if ok.any():
                    bought[c[np.argmax(ok)]] += lot
                    done += 1
                else:
                    still.append(w)
            queue = still
        return done / (done + unsold + len(queue))

    print("\n유동성: 1년 체결률 (13회차 모형, 투자자 5,000명, 하루 매도 40건, 20거래일 안 팔리면 철회)")
    print(f"  {'설계':<40}{'한도 없음':>10}{'1억 한도':>10}")
    for label, q, lot in (("자격 비율 0.6, 1회 500만 원 (이 상품)", 0.6, 5_000_000),
                          ("자격 비율 0.6, 1회 2,000만 원", 0.6, 20_000_000),
                          ("자격 비율 0.2, 1회 2,000만 원 (13회차)", 0.2, 20_000_000)):
        a, b = sim(q, lot, None), sim(q, lot, RETAIL_LIMIT)
        print(f"  {label:<40}{a:>10.1%}{b:>10.1%}")


if __name__ == "__main__":
    ok = scenarios()
    settlement_table()
    liquidity_table()
    raise SystemExit(0 if ok else 1)
