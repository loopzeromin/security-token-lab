"""
11회차 실습. 대금이 체인 위에 있을 때와 없을 때의 DVP

두 방식을 같은 거래로 비교한다.
  A. 원자적 DVP: 증권 토큰과 대금 토큰(예금토큰·스테이블코인)을 한 거래에서 맞바꾼다.
     둘 중 하나라도 실패하면 아무것도 움직이지 않는다.
  B. 체인 밖 대금 + agent 확인: ibet IbetSecurityTokenDVP처럼 증권만 체인 위에서 묶어 두고,
     대금은 은행 이체로 보낸 뒤 agent가 확인하고 완료한다 (create → confirm → finish).

실행: python3 s11_atomic_dvp.py   (같은 폴더에 s03, s04 파일 필요)
"""

from s03_erc20_model import ERC20, Revert, expect_revert, require
from s04_security_token_model import SecurityToken


class AtomicDvP:
    """증권과 대금을 transferFrom 두 번으로 한 번에 옮긴다. 검사를 먼저 다 하고 옮긴다."""

    def __init__(self, sec: SecurityToken, cash: ERC20):
        self.sec, self.cash, self.addr = sec, cash, "DvP계약"

    def settle(self, seller, buyer, qty, price):
        # 모든 조건을 먼저 확인 (Solidity라면 하나라도 실패하면 전체 revert)
        require(self.sec.allowance.get((seller, self.addr), 0) >= qty, "seller did not approve")
        require(self.cash.allowance.get((buyer, self.addr), 0) >= price, "buyer did not approve")
        require(self.sec.balance_of(seller) >= qty, "seller lacks securities")
        require(self.cash.balance_of(buyer) >= price, "buyer lacks cash")
        require(buyer in self.sec.allowlist, "recipient not eligible")
        # 이제 둘 다 옮긴다
        self.sec.allowance[(seller, self.addr)] -= qty
        self.sec._move(seller, buyer, qty)
        self.cash.transfer_from(self.addr, buyer, seller, price)


class AgentDvP:
    """ibet식: 증권은 계약에 묶고, 대금은 체인 밖. agent가 '입금 확인'을 눌러 완료한다."""

    def __init__(self, sec: SecurityToken, agent: str):
        self.sec, self.agent = sec, agent
        self.locked: dict[int, tuple] = {}
        self.n = 0

    def create(self, seller, buyer, qty):
        require(self.sec.balance_of(seller) >= qty, "seller lacks securities")
        self.sec._move(seller, "DvP보관", qty)          # commitment로 묶임
        self.n += 1
        self.locked[self.n] = (seller, buyer, qty)
        return self.n

    def finish(self, sender, did, bank_paid: bool, agent_says_paid: bool):
        require(sender == self.agent, "only agent")
        seller, buyer, qty = self.locked.pop(did)
        if agent_says_paid:                             # 체인은 agent의 판단만 안다
            self.sec._move("DvP보관", buyer, qty)
            return "delivered" if bank_paid else "delivered WITHOUT payment"
        self.sec._move("DvP보관", seller, qty)          # abort: 매도자에게 돌려줌
        return "aborted"


def setup():
    sec = SecurityToken("Study Bond", "SBD", issuer="발행사", supply=1_000)
    cash = ERC20("KRW Token", "KRWT", issuer="은행", supply=10_000_000)
    for who in ["매도자", "매수자"]:
        sec.add_investor("발행사", who)
    sec.transfer("발행사", "매도자", 100)
    cash.transfer("은행", "매수자", 1_000_000)
    return sec, cash


def main():
    print("A. 원자적 DVP")
    sec, cash = setup()
    dvp = AtomicDvP(sec, cash)
    sec.approve("매도자", dvp.addr, 10)
    cash.approve("매수자", dvp.addr, 100_000)
    dvp.settle("매도자", "매수자", 10, 100_000)
    print("  정상 결제:", {k: sec.balance_of(k) for k in ["매도자", "매수자"]},
          {k: cash.balance_of(k) for k in ["매도자", "매수자"]})

    # 매수자가 대금 승인을 덜 했으면 증권도 움직이지 않는다
    sec.approve("매도자", dvp.addr, 10)
    cash.approve("매수자", dvp.addr, 50_000)
    before = (sec.balance_of("매도자"), cash.balance_of("매도자"))
    expect_revert(lambda: dvp.settle("매도자", "매수자", 10, 100_000), "buyer did not approve")
    assert before == (sec.balance_of("매도자"), cash.balance_of("매도자"))
    print("  대금 부족: 전체 취소, 매도자 잔고 그대로", before)

    print("\nB. 체인 밖 대금 + agent 확인 (ibet식)")
    sec, _ = setup()
    a = AgentDvP(sec, agent="결제대행")
    cases = [("정상", True, True), ("매수자 미입금, agent가 정확히 abort", False, False),
             ("매수자 미입금인데 agent가 실수로 완료", False, True)]
    for label, bank_paid, says in cases:
        d = a.create("매도자", "매수자", 10)
        r = a.finish("결제대행", d, bank_paid, says)
        print(f"  {label:<32} → {r:<26} 매도자 {sec.balance_of('매도자'):>3}, 매수자 {sec.balance_of('매수자'):>3}")

    print("\n읽을 것: A에서는 '대금 없이 증권만 넘어가는' 경우가 코드상 불가능하다.")
    print("B에서는 그 경우가 agent의 판단 하나에 달려 있다. 원금 위험이 운영 위험으로 바뀐 것이다.")


if __name__ == "__main__":
    main()
