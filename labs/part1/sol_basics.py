"""
1–4회차 코드 과제 해설. 실행: python sol_basics.py
각 해설은 함수 하나이고, 마지막에 assert로 결과를 확인한다.
"""

import copy
import random
from collections import defaultdict

from s01_settlement_netting import gross_outflow, multilateral_net
from s02_hash_ledger import append_block, block_hash, verify
from s03_erc20_model import ERC20, expect_revert, require
from s04_security_token_model import SecurityToken


# ---------- 1회차 과제 2: 참가자·거래 수를 늘리면 차감 비율은?
def sol_s01():
    print("[1회차] 참가자·거래 수와 차감 후 필요 현금 비율")
    for n_part, n_trade in [(5, 200), (20, 2_000), (50, 20_000)]:
        rng = random.Random(1)
        parts = [f"P{i}" for i in range(n_part)]
        trades = []
        for _ in range(n_trade):
            b, s = rng.sample(parts, 2)
            trades.append((b, s, rng.randint(1, 50) * 1_000_000))
        g = sum(gross_outflow(trades).values())
        net = sum(max(0, -v) for v in multilateral_net(trades).values())
        print(f"  참가자 {n_part:>3}, 거래 {n_trade:>6}: 차감 후 {net / g:6.2%}")
    print("  해석: 거래가 많을수록 한 참가자의 매수와 매도가 더 많이 상쇄되어 비율이 낮아진다.")
    print("  다만 참가자 수도 같이 늘려서 줄어드는 속도는 느리다. 참가자를 5곳에 고정하고 거래만 늘리면 더 빨리 줄어드는지 직접 바꿔 본다.\n")


# ---------- 2회차 과제 1: 노드 5개 중 몇 개가 담합해야 위변조가 이기나
def sol_s02():
    print("[2회차] 노드 5개, 담합 수에 따른 다수결 결과")
    chain = []
    append_block(chain, [("발행", "민", 100)])
    append_block(chain, [("민", "지수", 30)])
    append_block(chain, [("지수", "현우", 10)])
    forged = copy.deepcopy(chain)
    forged[1]["txs"][0] = ("민", "지수", 3)
    for i in range(1, len(forged)):
        forged[i]["prev"] = block_hash(forged[i - 1])
    assert verify(forged)[0]
    for k in range(0, 6):
        nodes = [copy.deepcopy(forged) if i < k else copy.deepcopy(chain) for i in range(5)]
        tips = [block_hash(n[-1]) for n in nodes]
        winner = max(set(tips), key=tips.count)
        print(f"  담합 {k}곳 → 채택 장부: {'위조' if winner == block_hash(forged[-1]) else '원본'}")
    print("  해석: 과반(3곳 이상)이 같은 위조 장부를 내면 다수결에서 이긴다. 그래서 허가형 체인은 참여 기관 구성과")
    print("  기관 간 독립성이 핵심이다. 한국 시행령안이 '3곳 이상 물리적으로 떨어진 곳 보존'을 요구하는 것도 같은 맥락이다.\n")


# ---------- 3회차 과제 1: 발행자만 부를 수 있는 mint
class MintableERC20(ERC20):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.issuer = a[2] if len(a) > 2 else k["issuer"]
        self.total = sum(self.balance.values())

    def mint(self, sender, to, amount):
        require(sender == self.issuer, "only issuer")
        require(amount > 0, "zero amount")
        self.balance[to] = self.balance_of(to) + amount
        self.total += amount
        self.events.append(("Transfer", "0x0", to, amount))   # 표준 관행: 발행은 0 주소에서 오는 Transfer


def sol_s03():
    print("[3회차] mint 추가")
    t = MintableERC20("Study Coin", "STC", issuer="발행사", supply=1_000)
    t.mint("발행사", "민", 500)
    expect_revert(lambda: t.mint("민", "민", 1), "only issuer")
    assert t.total == 1_500 == sum(t.balance.values())
    print(f"  총량 {t.total}, 잔고 합 {sum(t.balance.values())}, 마지막 이벤트 {t.events[-1]}")
    print("  해석: 발행은 0 주소에서 오는 Transfer로 기록한다. 14회차 실증 실습이 이 관행으로 발행을 찾는다.\n")


# ---------- 4회차 과제 1: 1인당 보유 한도 100
class CappedSecurityToken(SecurityToken):
    CAP = 100

    def transfer(self, sender, to, amount):
        require(to in self.allowlist, "recipient not eligible")      # 자격을 먼저 본다
        if to != self.issuer:
            require(self.balance_of(to) + amount <= self.CAP, "holding cap exceeded")
        return super().transfer(sender, to, amount)


def sol_s04():
    print("[4회차] 1인당 보유 한도 100")
    st = CappedSecurityToken("Study Bond", "SBD", issuer="발행사", supply=1_000)
    st.add_investor("발행사", "민")
    st.transfer("발행사", "민", 100)
    expect_revert(lambda: st.transfer("발행사", "민", 1), "holding cap exceeded")
    st.transfer("민", "발행사", 50)                 # 발행자에게 돌려주는 것은 한도와 무관
    st.transfer("발행사", "민", 50)
    print("  100까지 통과, 101번째에서 revert, 발행자 반환은 예외:", st.balance)
    expect_revert(lambda: st.transfer("발행사", "익명", 500), "recipient not eligible")
    print("  자격 없는 주소에 큰 금액을 보내면 한도가 아니라 자격 메시지가 나온다.")
    print("  검사 순서가 중요하다. 한도를 먼저 보면 자격 없는 주소에도 'cap' 메시지가 나와 원인이 흐려진다.\n")


if __name__ == "__main__":
    sol_s01(); sol_s02(); sol_s03(); sol_s04()
