"""
3회차 실습. ERC-20을 파이썬으로 옮겨 보기

Solidity의 require가 실패하면 거래 전체가 취소(revert)된다.
파이썬에서는 예외(Revert)를 던지고, 상태를 바꾸기 전에 모든 검사를 끝내는 방식으로 흉내 낸다.
함수 이름은 ERC-20 표준(EIP-20)과 같게 맞췄다.

실행: python3 s03_erc20_model.py
"""


class Revert(Exception):
    pass


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise Revert(msg)


class ERC20:
    def __init__(self, name: str, symbol: str, issuer: str, supply: int):
        self.name, self.symbol = name, symbol
        self.balance: dict[str, int] = {issuer: supply}
        self.allowance: dict[tuple[str, str], int] = {}
        self.events: list[tuple] = []          # 체인의 이벤트 로그에 해당

    def balance_of(self, who: str) -> int:
        return self.balance.get(who, 0)

    def _move(self, frm: str, to: str, amount: int) -> None:
        self.balance[frm] = self.balance_of(frm) - amount
        self.balance[to] = self.balance_of(to) + amount
        self.events.append(("Transfer", frm, to, amount))

    # msg.sender 자리에 sender를 명시적으로 받는다
    def transfer(self, sender: str, to: str, amount: int) -> bool:
        require(self.balance_of(sender) >= amount, "Insufficient Balance")
        self._move(sender, to, amount)
        return True

    def approve(self, sender: str, spender: str, amount: int) -> bool:
        self.allowance[(sender, spender)] = amount
        self.events.append(("Approval", sender, spender, amount))
        return True

    def transfer_from(self, sender: str, frm: str, to: str, amount: int) -> bool:
        allowed = self.allowance.get((frm, sender), 0)
        require(allowed >= amount, "Insufficient Allowance")
        require(self.balance_of(frm) >= amount, "Insufficient Balance")
        self.allowance[(frm, sender)] = allowed - amount
        self._move(frm, to, amount)
        return True


def expect_revert(fn, msg):
    try:
        fn()
    except Revert as e:
        assert str(e) == msg, (str(e), msg)
        return
    raise AssertionError("revert가 나야 하는데 성공했다")


def main():
    t = ERC20("Study Coin", "STC", issuer="발행사", supply=1_000)

    t.transfer("발행사", "민", 100)
    t.transfer("민", "익명주소_0x9f", 40)           # 받는 사람이 누구든 검사하지 않는다
    print("잔고:", t.balance)

    expect_revert(lambda: t.transfer("민", "지수", 1_000), "Insufficient Balance")
    print("잔고보다 많이 보내면 revert, 잔고 변화 없음:", t.balance_of("민"))

    # 위임: 민이 거래소에게 20까지 옮길 권한을 준다
    t.approve("민", "거래소", 20)
    t.transfer_from("거래소", "민", "지수", 15)
    expect_revert(lambda: t.transfer_from("거래소", "민", "지수", 10), "Insufficient Allowance")
    print("위임 후 잔고:", t.balance, "남은 한도:", t.allowance[("민", "거래소")])

    print("\n이벤트 로그:")
    for e in t.events:
        print(" ", e)

    assert sum(t.balance.values()) == 1_000   # 이전은 총량을 바꾸지 않는다
    print("\n질문: 이 코드에서 '익명주소_0x9f'가 투자 자격이 없는 사람이라면 무엇을 막을 수 있는가? (4회차로)")


if __name__ == "__main__":
    main()
