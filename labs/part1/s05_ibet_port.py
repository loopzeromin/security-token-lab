"""
5회차 실습. 일본 ibet 채권 토큰의 전송 규칙을 파이썬으로 옮겨 읽기

원본: github.com/BoostryJP/ibet-SmartContract, 커밋 8092b7c
  contracts/ledger/PersonalInfo.sol          (register 53행, forceRegister 99행, isRegistered 117행)
  contracts/token/IbetStraightBond.sol       (transferToAddress 114행, transfer 179행,
                                              applyForTransfer 702행, cancelTransfer 754행, approveTransfer 797행)
에러 코드 문자열은 contracts/utils/Errors.sol과 같다.

이 파일은 원본의 '검사 순서와 실패 코드'만 옮겼다. 컨트랙트 주소로 보내는 경로(transferToContract),
잠금(lock), 이자·상환 같은 기능은 뺐다. 9회차에 실제 체인에서 같은 시나리오를 돌려 비교한다.

실행: python3 s05_ibet_port.py
"""

from s03_erc20_model import Revert, expect_revert, require

ZERO = "0x0"


class PersonalInfo:
    """personal_info[투자자][발행자] = (account_address, link_address, encrypted_info)"""

    def __init__(self):
        self.info: dict[tuple[str, str], tuple[str, str, str]] = {}

    def register(self, sender: str, link: str, encrypted: str) -> None:       # 53행
        self.info[(sender, link)] = (sender, link, encrypted)

    def force_register(self, sender: str, account: str, encrypted: str) -> None:   # 99행
        # 호출자(발행자)가 link 자리에 들어간다. 권한 검사는 없다.
        self.info[(account, sender)] = (account, sender, encrypted)

    def is_registered(self, account: str, link: str) -> bool:                 # 117행
        rec = self.info.get((account, link))
        return rec is not None and rec[0] != ZERO      # 내용(encrypted)은 보지 않는다


class IbetStraightBond:
    def __init__(self, owner: str, total_supply: int, personal_info: PersonalInfo):
        self.owner = owner
        self.balances = {owner: total_supply}
        self.personal_info = personal_info
        self.tradable_exchange = ZERO
        self.transferable = False                      # 생성자에서 켜지 않는다 → setTransferable 필요
        self.transfer_approval_required = False
        self.require_personal_info_registered = True   # 96행: 기본값 true
        self.pending: dict[str, int] = {}
        self.applications: list[dict] = []

    def bal(self, who: str) -> int:
        return self.balances.get(who, 0)

    def _only_owner(self, sender: str) -> None:
        require(sender == self.owner, "500001")         # Ownable.sol 42행

    # setter들 (모두 onlyOwner)
    def set_transferable(self, sender, v): self._only_owner(sender); self.transferable = v
    def set_transfer_approval_required(self, sender, v): self._only_owner(sender); self.transfer_approval_required = v
    def set_require_personal_info_registered(self, sender, v): self._only_owner(sender); self.require_personal_info_registered = v

    def transfer(self, sender: str, to: str, value: int) -> None:            # 179행
        require(self.bal(sender) >= value, "120401")
        require(self.transferable, "120402")
        # transferToAddress (114행)
        if sender != self.tradable_exchange and self.transfer_approval_required:
            raise Revert("120201")
        if to != self.owner and self.require_personal_info_registered:
            require(self.personal_info.is_registered(to, self.owner), "120202")
        self.balances[sender] = self.bal(sender) - value
        self.balances[to] = self.bal(to) + value

    def apply_for_transfer(self, sender: str, to: str, value: int) -> int:   # 702행
        if (not self.transfer_approval_required) or (not self.transferable) or self.bal(sender) < value:
            raise Revert("120701")
        if to != self.owner and self.require_personal_info_registered:
            require(self.personal_info.is_registered(to, self.owner), "120702")
        self.balances[sender] -= value
        self.pending[sender] = self.pending.get(sender, 0) + value
        self.applications.append({"from": sender, "to": to, "amount": value, "valid": True})
        return len(self.applications) - 1

    def cancel_transfer(self, sender: str, index: int) -> None:              # 754행
        app = self.applications[index]
        if app["from"] != sender and sender != self.owner:
            raise Revert("120801")
        if not app["valid"]:
            raise Revert("120802")
        self.balances[app["from"]] += app["amount"]
        self.pending[app["from"]] -= app["amount"]
        app["valid"] = False

    def approve_transfer(self, sender: str, index: int) -> None:             # 797행
        self._only_owner(sender)
        if not self.transferable:
            raise Revert("120901")
        app = self.applications[index]
        if not app["valid"]:
            raise Revert("120902")
        # 여기서는 개인정보를 다시 보지 않는다
        self.balances[app["to"]] = self.bal(app["to"]) + app["amount"]
        self.pending[app["from"]] -= app["amount"]
        app["valid"] = False


def fresh():
    pi = PersonalInfo()
    bond = IbetStraightBond("발행사", 10_000, pi)
    bond.set_transferable("발행사", True)
    return pi, bond


def main():
    # 시나리오 1: 개인정보 등록 관문
    pi, bond = fresh()
    expect_revert(lambda: bond.transfer("발행사", "민", 100), "120202")
    pi.register("민", "발행사", "enc(민의 이름·주소)")
    bond.transfer("발행사", "민", 100)
    bond.transfer("민", "발행사", 10)                        # 발행자에게는 검사 생략
    pi.register("지수", "발행사", "")                         # 빈 문자열도 등록으로 친다
    bond.transfer("발행사", "지수", 1)
    pi.force_register("발행사", "현우", "발행사가 대신 입력")
    bond.transfer("발행사", "현우", 1)
    print("1. 개인정보 관문:", bond.balances)

    # 시나리오 2: 승인 방식
    pi, bond = fresh()
    pi.register("민", "발행사", "enc")
    bond.set_transfer_approval_required("발행사", True)
    expect_revert(lambda: bond.transfer("발행사", "민", 100), "120201")     # 발행자도 직접 전송 불가
    i = bond.apply_for_transfer("발행사", "민", 100)
    assert bond.bal("발행사") == 9_900 and bond.bal("민") == 0              # 보류 상태
    bond.approve_transfer("발행사", i)
    print("2-a. 신청 → 승인 후:", bond.balances, "보류:", bond.pending)

    # 2-b. 신청 이후 등록 요구를 켜도 승인은 통과한다
    pi, bond = fresh()
    bond.set_transfer_approval_required("발행사", True)
    bond.set_require_personal_info_registered("발행사", False)
    i = bond.apply_for_transfer("발행사", "미등록자", 100)
    bond.set_require_personal_info_registered("발행사", True)
    expect_revert(lambda: bond.apply_for_transfer("발행사", "미등록자", 100), "120702")
    bond.approve_transfer("발행사", i)
    print("2-b. 미등록자 잔고(먼저 낸 신청이 승인됨):", bond.bal("미등록자"))

    # 2-c. 취소 권한
    pi, bond = fresh()
    pi.register("민", "발행사", "enc")
    bond.transfer("발행사", "민", 500)
    bond.set_transfer_approval_required("발행사", True)
    i = bond.apply_for_transfer("민", "발행사", 50)
    expect_revert(lambda: bond.cancel_transfer("제3자", i), "120801")
    bond.cancel_transfer("민", i)
    expect_revert(lambda: bond.cancel_transfer("발행사", i), "120802")
    print("2-c. 취소 후 민의 잔고:", bond.bal("민"))

    print("\n질문: register()가 내용을 보지 않는다면, 일본 ST에서 '자격 있는 투자자'는 누가 어디서 판단하는가?")


if __name__ == "__main__":
    main()
