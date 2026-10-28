"""
6회차 실습. ERC-3643의 '서명된 증명(claim)' 검증을 파이썬으로 옮겨 보기

원본: github.com/ERC-3643/ERC-3643, v4.1.3 (커밋 2f0704d)
  contracts/registry/implementation/IdentityRegistry.sol   isVerified 173행
  contracts/token/Token.sol                                transfer 417행, forcedTransfer 431행, mint 454행

원본에서는 KYC 기관(ClaimIssuer)이 이더리움 키로 서명하고 체인 위에서 검증한다.
여기서는 같은 구조를 Ed25519 전자서명으로 흉내 낸다. 서명이 무엇을 보장하는지 보는 것이 목적이다.

준비: pip install cryptography
실행: python3 s06_erc3643_port.py
"""

import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from s03_erc20_model import Revert, expect_revert, require

KYC = "KYC_DONE"           # claim topic (원본에서는 정수 id)


def claim_digest(identity_id: str, topic: str, data: str) -> bytes:
    # 원본도 (identity, topic, data)를 묶어 해시한 값에 서명한다
    return hashlib.sha256(f"{identity_id}|{topic}|{data}".encode()).digest()


class ClaimIssuer:
    """KYC 기관. 비밀키로 서명하고, 공개키는 누구나 볼 수 있다"""

    def __init__(self, name: str):
        self.name = name
        self._sk = Ed25519PrivateKey.generate()
        self.pk = self._sk.public_key()
        self.revoked: set[bytes] = set()

    def sign(self, identity_id: str, topic: str, data: str) -> bytes:
        return self._sk.sign(claim_digest(identity_id, topic, data))

    def is_claim_valid(self, identity_id: str, topic: str, sig: bytes, data: str) -> bool:
        if sig in self.revoked:
            return False
        try:
            self.pk.verify(sig, claim_digest(identity_id, topic, data))
            return True
        except InvalidSignature:
            return False


class Identity:
    """ONCHAINID에 해당. 투자자 본인이 claim을 붙여 둔다"""

    def __init__(self, identity_id: str):
        self.id = identity_id
        self.claims: dict[tuple[str, str], tuple[str, bytes, str]] = {}   # (issuer, topic) → (topic, sig, data)

    def add_claim(self, issuer: ClaimIssuer, topic: str, sig: bytes, data: str) -> None:
        self.claims[(issuer.name, topic)] = (topic, sig, data)


class IdentityRegistry:
    def __init__(self):
        self.identity: dict[str, Identity] = {}       # 지갑 → 신원
        self.country: dict[str, int] = {}             # ISO-3166 숫자 코드
        self.required_topics: list[str] = [KYC]       # Claim Topics Registry
        self.trusted: dict[str, tuple[ClaimIssuer, list[str]]] = {}   # Trusted Issuers Registry

    def register_identity(self, wallet: str, ident: Identity, country: int) -> None:
        self.identity[wallet] = ident
        self.country[wallet] = country

    def is_verified(self, wallet: str) -> bool:      # 173행과 같은 순서
        ident = self.identity.get(wallet)
        if ident is None:
            return False
        if not self.required_topics:
            return True                               # 요구 topic이 없으면 등록만으로 통과
        for topic in self.required_topics:
            issuers = [iss for iss, topics in self.trusted.values() if topic in topics]
            if not issuers:
                return False
            ok = False
            for iss in issuers:
                c = ident.claims.get((iss.name, topic))
                if c and iss.is_claim_valid(ident.id, topic, c[1], c[2]):
                    ok = True
                    break
            if not ok:
                return False
        return True


class MaxHoldersModule:
    """보유자 수 상한 같은 토큰 단위 규칙 (원본의 Compliance 모듈 개념)"""

    def __init__(self, limit: int):
        self.limit = limit

    def can_transfer(self, token, frm, to, amount) -> bool:
        holders = {w for w, b in token.balances.items() if b > 0}
        return to in holders or len(holders) < self.limit


class CountryBlockModule:
    def __init__(self, blocked: set[int]):
        self.blocked = blocked

    def can_transfer(self, token, frm, to, amount) -> bool:
        return token.registry.country.get(to) not in self.blocked


class Token:
    def __init__(self, registry: IdentityRegistry, agent: str):
        self.registry, self.agent = registry, agent
        self.balances: dict[str, int] = {}
        self.frozen: set[str] = set()
        self.frozen_tokens: dict[str, int] = {}
        self.paused = False
        self.modules: list = []

    def bal(self, w): return self.balances.get(w, 0)

    def can_transfer(self, frm, to, amount) -> bool:
        return all(m.can_transfer(self, frm, to, amount) for m in self.modules)

    def mint(self, sender, to, amount):                                       # 454행
        require(sender == self.agent, "AgentRole: caller does not have the Agent role")
        require(self.registry.is_verified(to), "Identity is not verified.")
        require(self.can_transfer(None, to, amount), "Compliance not followed")
        self.balances[to] = self.bal(to) + amount

    def transfer(self, sender, to, amount):                                   # 417행
        require(not self.paused, "Pausable: paused")
        require(to not in self.frozen and sender not in self.frozen, "wallet is frozen")
        require(amount <= self.bal(sender) - self.frozen_tokens.get(sender, 0), "Insufficient Balance")
        if self.registry.is_verified(to) and self.can_transfer(sender, to, amount):
            self.balances[sender] -= amount
            self.balances[to] = self.bal(to) + amount
            return
        raise Revert("Transfer not possible")

    def forced_transfer(self, sender, frm, to, amount):                      # 431행
        require(sender == self.agent, "AgentRole: caller does not have the Agent role")
        require(self.bal(frm) >= amount, "sender balance too low")
        free = self.bal(frm) - self.frozen_tokens.get(frm, 0)
        if amount > free:
            self.frozen_tokens[frm] -= amount - free
        if self.registry.is_verified(to):                  # 규칙 모듈은 보지 않는다
            self.balances[frm] -= amount
            self.balances[to] = self.bal(to) + amount
            return
        raise Revert("Transfer not possible")


def onboard(reg: IdentityRegistry, kyc: ClaimIssuer, wallet: str, country: int, with_claim=True) -> Identity:
    ident = Identity(f"ID-{wallet}")
    reg.register_identity(wallet, ident, country)
    if with_claim:
        ident.add_claim(kyc, KYC, kyc.sign(ident.id, KYC, "KYC 통과 2026-10"), "KYC 통과 2026-10")
    return ident


def main():
    kyc = ClaimIssuer("KYC기관A")
    reg = IdentityRegistry()
    reg.trusted[kyc.name] = (kyc, [KYC])
    tok = Token(reg, agent="발행사")

    onboard(reg, kyc, "alice", 410)
    onboard(reg, kyc, "bob", 392)                    # 392 = 일본
    tok.mint("발행사", "alice", 1_000)
    tok.mint("발행사", "bob", 500)

    tok.transfer("alice", "bob", 100)
    print("1. 검증된 두 사람 사이 전송:", tok.balances)

    expect_revert(lambda: tok.transfer("alice", "charlie", 10), "Transfer not possible")
    charlie = onboard(reg, kyc, "charlie", 410, with_claim=False)
    expect_revert(lambda: tok.transfer("alice", "charlie", 10), "Transfer not possible")
    print("2. 등록만 되고 claim이 없으면 거절 (ibet의 '등록'과 다른 점)")

    # 2-b. charlie가 서명을 위조하면? 다른 키로 서명한 claim
    forger = ClaimIssuer("위조자")
    charlie.add_claim(kyc, KYC, forger.sign(charlie.id, KYC, "KYC 통과"), "KYC 통과")
    expect_revert(lambda: tok.transfer("alice", "charlie", 10), "Transfer not possible")
    print("2-b. KYC기관 이름으로 위조 서명을 붙여도 공개키 검증에서 걸린다")

    # 2-c. 남의 claim을 복사해 와도 identity id가 달라 서명이 맞지 않는다
    alice_claim = reg.identity["alice"].claims[(kyc.name, KYC)]
    charlie.add_claim(kyc, KYC, alice_claim[1], alice_claim[2])
    expect_revert(lambda: tok.transfer("alice", "charlie", 10), "Transfer not possible")
    print("2-c. alice의 claim을 복사해도 charlie의 신원과 맞지 않아 실패")

    # 3. KYC 기관의 서명을 철회하면 bob도 받을 수 없다
    bob_sig = reg.identity["bob"].claims[(kyc.name, KYC)][1]
    kyc.revoked.add(bob_sig)
    expect_revert(lambda: tok.transfer("alice", "bob", 10), "Transfer not possible")
    print("3. claim 철회 후 bob 검증:", reg.is_verified("bob"))
    kyc.revoked.clear()

    # 4. 규칙 모듈: 일본(392) 거주자에게 전송 금지
    tok.modules.append(CountryBlockModule({392}))
    expect_revert(lambda: tok.transfer("alice", "bob", 10), "Transfer not possible")
    tok.forced_transfer("발행사", "alice", "bob", 10)          # 강제 이전은 모듈을 건너뛴다
    print("4. 국가 규칙은 일반 전송만 막고 강제 이전은 통과:", tok.balances)

    # 5. 그래도 무자격 지갑으로는 강제 이전도 안 된다
    expect_revert(lambda: tok.forced_transfer("발행사", "alice", "익명", 10), "Transfer not possible")
    print("5. 무자격 지갑으로 강제 이전 불가")

    # 6. 요구 topic을 비우면 등록만으로 통과 → ibet 수준
    reg.required_topics = []
    tok.modules.clear()
    tok.transfer("alice", "charlie", 10)
    print("6. KYC 요건을 지우면 charlie도 받는다:", tok.bal("charlie"))


if __name__ == "__main__":
    main()
