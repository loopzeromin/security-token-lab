"""
5·6회차와 법률 비교의 코드 과제 해설. 실행: python sol_markets.py   (cryptography 필요)
"""

from s03_erc20_model import expect_revert, require
from s05_ibet_port import fresh
from s06_erc3643_port import ClaimIssuer, IdentityRegistry, MaxHoldersModule, Token, onboard


# ---------- 5회차 과제 1: 등록 요구를 끈 상태에서 미등록자에게 직접 전송
def sol_s05():
    print("[5회차] 등록 요구 off + 미등록자")
    pi, bond = fresh()
    expect_revert(lambda: bond.transfer("발행사", "미등록자", 10), "120202")     # 기본값(on)에서는 거절
    bond.set_require_personal_info_registered("발행사", False)
    bond.transfer("발행사", "미등록자", 10)
    print("  끄면 통과:", bond.bal("미등록자"))
    expect_revert(lambda: bond.set_require_personal_info_registered("미등록자", True), "500001")
    print("  스위치는 발행자만 바꿀 수 있다(500001). 즉 자격 관문의 존재 자체가 발행자 재량이다.\n")


# ---------- 6회차 과제 1: 보유자 수 상한 3
def sol_s06():
    print("[6회차] MaxHoldersModule(3)")
    kyc = ClaimIssuer("KYC기관A")
    reg = IdentityRegistry(); reg.trusted[kyc.name] = (kyc, ["KYC_DONE"])
    tok = Token(reg, agent="발행사")
    for w in ["a", "b", "c", "d"]:
        onboard(reg, kyc, w, 410)
    tok.mint("발행사", "a", 100)
    tok.modules.append(MaxHoldersModule(3))
    tok.transfer("a", "b", 10); tok.transfer("a", "c", 10)
    expect_revert(lambda: tok.transfer("a", "d", 10), "Transfer not possible")
    tok.transfer("b", "c", 5)                                  # 기존 보유자끼리는 통과
    tok.transfer("b", "c", 5)                                  # b가 0이 되면 보유자 수가 2로 줄어든다
    tok.transfer("a", "d", 10)                                 # 이제 d가 들어올 자리가 생겼다
    print("  잔고:", tok.balances)
    print("  해석: 한 사람이 전량을 넘기면 자리가 빈다. 원본 모듈도 보유자 수를 이전 후 상태로 세는지 확인해 볼 만하다.\n")


# ---------- 법률 비교 과제 1: 한국 일반투자자 연간 순매수 1억 원 (1토큰 = 1만 원 가정)
class KoreaRetailLimitModule:
    LIMIT_TOKENS = 100_000_000 // 10_000          # 1억 원 / 1만 원 = 10,000토큰

    def __init__(self, professional: set[str]):
        self.pro = professional
        self.net: dict[tuple[str, int], int] = {}  # (지갑, 연도) → 순매수
        self.year = 2027

    def can_transfer(self, token, frm, to, amount):
        if to in self.pro:
            return True
        return self.net.get((to, self.year), 0) + amount <= self.LIMIT_TOKENS

    def transferred(self, frm, to, amount):
        if frm is not None:
            self.net[(frm, self.year)] = self.net.get((frm, self.year), 0) - amount
        self.net[(to, self.year)] = self.net.get((to, self.year), 0) + amount


class TokenWithHooks(Token):
    """원본 Token.sol처럼 전송 뒤 모듈의 transferred()를 부른다"""

    def transfer(self, sender, to, amount):
        super().transfer(sender, to, amount)
        for m in self.modules:
            if hasattr(m, "transferred"):
                m.transferred(sender, to, amount)


def sol_law():
    print("[법률 비교] 연간 순매수 1억 원 한도")
    kyc = ClaimIssuer("KYC기관A")
    reg = IdentityRegistry(); reg.trusted[kyc.name] = (kyc, ["KYC_DONE"])
    tok = TokenWithHooks(reg, agent="발행사")
    for w in ["시장조성자", "민", "기관"]:
        onboard(reg, kyc, w, 410)
    tok.mint("발행사", "시장조성자", 100_000)
    mod = KoreaRetailLimitModule(professional={"기관"})
    tok.modules.append(mod)
    tok.transfer("시장조성자", "민", 6_000)           # 6천만 원
    tok.transfer("시장조성자", "민", 4_000)           # 누적 1억 원
    expect_revert(lambda: tok.transfer("시장조성자", "민", 1), "Transfer not possible")
    tok.transfer("민", "시장조성자", 3_000)           # 3천만 원 매도 → 순매수 7천만
    tok.transfer("시장조성자", "민", 3_000)           # 다시 살 수 있다 (순매수 기준)
    tok.transfer("시장조성자", "기관", 50_000)        # 전문투자자는 한도 없음
    mod.year = 2028
    tok.transfer("시장조성자", "민", 1_000)           # 해가 바뀌면 한도가 새로 생긴다
    print("  잔고:", tok.balances)
    print("  해석: 순매수 기준이라 팔면 한도가 다시 생긴다. 한도는 '장외거래소별'이므로 실제로는 거래소 주소마다 따로 세야 한다.\n")


if __name__ == "__main__":
    sol_s05(); sol_s06(); sol_law()
