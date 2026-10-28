"""
4회차 실습. ERC-20에 세 질문(자격, 통제, 결제)의 답을 붙여 '증권 토큰'으로 만들기

s03_erc20_model.py의 ERC20을 상속해서 transfer 앞에 검사를 붙인다.
  Eligibility: 발행자가 관리하는 투자자 명부(allowlist)에 있는 사람만 받을 수 있다
  Control:     일시정지, 지갑 동결, 강제 이전
  Settlement:  이 모형에는 없다 (대금은 토큰 밖에서 오간다). 9~11회차에서 다룬다

실행: python3 s04_security_token_model.py   (같은 폴더에 s03_erc20_model.py 필요)
"""

from s03_erc20_model import ERC20, Revert, expect_revert, require


class SecurityToken(ERC20):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.issuer = args[2] if len(args) > 2 else kwargs["issuer"]
        self.allowlist: set[str] = {self.issuer}
        self.paused = False
        self.frozen: set[str] = set()

    # --- 발행자만 부를 수 있는 함수 (Solidity의 onlyOwner) ---
    def _only_issuer(self, sender: str) -> None:
        require(sender == self.issuer, "only issuer")

    def add_investor(self, sender: str, who: str) -> None:
        self._only_issuer(sender)
        self.allowlist.add(who)

    def set_paused(self, sender: str, value: bool) -> None:
        self._only_issuer(sender)
        self.paused = value

    def set_frozen(self, sender: str, who: str, value: bool) -> None:
        self._only_issuer(sender)
        (self.frozen.add if value else self.frozen.discard)(who)

    def forced_transfer(self, sender: str, frm: str, to: str, amount: int) -> None:
        """법원 명령, 상속 같은 경우. 일시정지·동결은 무시하지만 받는 사람 자격은 본다"""
        self._only_issuer(sender)
        require(to in self.allowlist, "recipient not eligible")
        require(self.balance_of(frm) >= amount, "Insufficient Balance")
        self._move(frm, to, amount)

    # --- 검사가 붙은 전송 ---
    def transfer(self, sender: str, to: str, amount: int) -> bool:
        require(not self.paused, "paused")
        require(sender not in self.frozen and to not in self.frozen, "wallet is frozen")
        require(to in self.allowlist, "recipient not eligible")
        return super().transfer(sender, to, amount)


def main():
    st = SecurityToken("Study Bond", "SBD", issuer="발행사", supply=1_000)
    st.add_investor("발행사", "민")
    st.transfer("발행사", "민", 100)

    expect_revert(lambda: st.transfer("민", "익명주소_0x9f", 10), "recipient not eligible")
    print("1. 명부에 없는 주소로는 못 보낸다")

    expect_revert(lambda: st.add_investor("민", "지수"), "only issuer")
    st.add_investor("발행사", "지수")
    st.transfer("민", "지수", 30)
    print("2. 명부 관리는 발행자만, 등록 후 전송 성공:", st.balance)

    st.set_frozen("발행사", "지수", True)
    expect_revert(lambda: st.transfer("지수", "민", 5), "wallet is frozen")
    print("3. 동결된 지갑은 못 보낸다")

    st.forced_transfer("발행사", "지수", "민", 30)
    print("4. 강제 이전은 동결과 상관없이 실행된다:", st.balance)

    st.set_paused("발행사", True)
    expect_revert(lambda: st.transfer("민", "지수", 1), "paused")
    print("5. 일시정지 중에는 모든 전송이 멈춘다")

    assert sum(st.balance.values()) == 1_000
    print("\n질문: 이 모형에서 '명부에 있다'는 것은 무엇으로 증명되는가? 누가 그 판단을 하는가? (5·6회차로)")


if __name__ == "__main__":
    main()
