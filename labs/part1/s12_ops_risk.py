"""
12회차 실습. 운영 위험: 키 분실, 권한 집중, 업그레이드

1) 키 분실과 복구: ERC-3643 Token.sol recoveryAddress(297행)의 조건을 옮겼다.
   새 지갑이 투자자 신원(ONCHAINID)에 등록된 키여야 하고, 아니면 "Recovery not possible".
2) 권한 집중: agent 한 명이 강제 이전을 할 수 있으면 그 키 하나가 털릴 때 모든 증권이 위험하다.
   2-of-3 다중서명으로 바꾸면 무엇이 달라지는가.
3) 업그레이드: 프록시 구조에서는 '로직 교체 = 규칙 교체'다. 시간 지연(timelock)을 두면 투자자가 미리 볼 수 있다.

실행: python3 s12_ops_risk.py   (같은 폴더에 s03 파일 필요)
"""

from s03_erc20_model import Revert, expect_revert, require


# ---------------------------------------------------------------- 1. 복구
class Identity:
    def __init__(self, owner_wallet):
        self.keys = {owner_wallet}          # 원본: keyHasPurpose(key, 1) — MANAGEMENT 키

class Token:
    def __init__(self, agent):
        self.agent = agent
        self.bal: dict[str, int] = {}
        self.identity_of: dict[str, Identity] = {}
        self.frozen: set[str] = set()

    def recovery_address(self, sender, lost, new, ident: Identity):      # 297행
        require(sender == self.agent, "AgentRole: caller does not have the Agent role")
        require(self.bal.get(lost, 0) != 0, "no tokens to recover")
        if new in ident.keys:
            self.identity_of[new] = ident
            self.bal[new] = self.bal.get(new, 0) + self.bal.pop(lost)
            if lost in self.frozen:
                self.frozen.add(new)                                       # 동결 상태도 따라간다
            del self.identity_of[lost]
            return
        raise Revert("Recovery not possible")


# ---------------------------------------------------------------- 2. 다중서명
class MultiSig:
    def __init__(self, signers, threshold):
        self.signers, self.threshold = set(signers), threshold
        self.approvals: dict[str, set] = {}

    def approve(self, signer, action_id):
        require(signer in self.signers, "not a signer")
        self.approvals.setdefault(action_id, set()).add(signer)

    def can_execute(self, action_id):
        return len(self.approvals.get(action_id, set())) >= self.threshold


# ---------------------------------------------------------------- 3. 프록시와 timelock
class LogicV1:
    @staticmethod
    def transfer(state, frm, to, amt):
        require(to in state["allowlist"], "recipient not eligible")
        state["bal"][frm] -= amt
        state["bal"][to] = state["bal"].get(to, 0) + amt

class LogicV2NoCheck:
    @staticmethod
    def transfer(state, frm, to, amt):
        state["bal"][frm] -= amt
        state["bal"][to] = state["bal"].get(to, 0) + amt

class Proxy:
    """상태(잔고)는 프록시에, 규칙(로직)은 교체 가능한 구현에. 원본의 delegatecall 구조를 단순화했다."""

    def __init__(self, owner, logic, delay_blocks=0):
        self.owner, self.logic, self.delay = owner, logic, delay_blocks
        self.state = {"bal": {"A": 100}, "allowlist": {"A", "B"}}
        self.block, self.pending = 0, None

    def propose_upgrade(self, sender, new_logic):
        require(sender == self.owner, "only owner")
        self.pending = (new_logic, self.block + self.delay)

    def execute_upgrade(self):
        require(self.pending is not None, "nothing pending")
        logic, ready = self.pending
        require(self.block >= ready, "timelock")
        self.logic, self.pending = logic, None

    def transfer(self, frm, to, amt):
        self.logic.transfer(self.state, frm, to, amt)


def main():
    print("1. 키 분실과 복구")
    t = Token(agent="발행사")
    ident = Identity("민_옛지갑")
    t.identity_of["민_옛지갑"] = ident
    t.bal["민_옛지갑"] = 500
    t.frozen.add("민_옛지갑")
    expect_revert(lambda: t.recovery_address("발행사", "민_옛지갑", "민_새지갑", ident), "Recovery not possible")
    print("  새 지갑이 신원에 등록되지 않으면 복구 불가 (남의 지갑으로 빼돌리기 방지)")
    ident.keys.add("민_새지갑")              # 투자자가 본인 신원에 새 키를 추가
    t.recovery_address("발행사", "민_옛지갑", "민_새지갑", ident)
    print("  등록 후 복구:", t.bal, "동결 유지:", "민_새지갑" in t.frozen)

    print("\n2. 권한 집중")
    ms = MultiSig(["운영팀", "준법감시", "외부수탁"], threshold=2)
    ms.approve("운영팀", "강제이전#1")
    print("  탈취된 운영팀 키 하나로 실행 가능?", ms.can_execute("강제이전#1"))
    ms.approve("준법감시", "강제이전#1")
    print("  두 번째 서명 후 실행 가능?", ms.can_execute("강제이전#1"))
    expect_revert(lambda: ms.approve("공격자", "강제이전#2"), "not a signer")

    print("\n3. 업그레이드 = 규칙 교체")
    p = Proxy(owner="발행사", logic=LogicV1, delay_blocks=0)
    expect_revert(lambda: p.transfer("A", "익명", 10), "recipient not eligible")
    p.propose_upgrade("발행사", LogicV2NoCheck)
    p.execute_upgrade()
    p.transfer("A", "익명", 10)
    print("  지연 없이 로직을 바꾸자 자격 검사가 사라졌다:", p.state["bal"])

    p2 = Proxy(owner="발행사", logic=LogicV1, delay_blocks=7_200)    # 약 하루 (12초 블록 가정)
    p2.propose_upgrade("발행사", LogicV2NoCheck)
    expect_revert(p2.execute_upgrade, "timelock")
    print("  timelock이 있으면 즉시 교체 불가. 투자자는 그 사이 공지를 보고 대응할 수 있다.")


if __name__ == "__main__":
    main()
