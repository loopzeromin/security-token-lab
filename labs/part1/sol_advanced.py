"""
10–13회차(결제·대금·운영·유동성) 코드 과제 해설. 실행: python sol_advanced.py   (numpy 필요, 약 20초)
"""

import math

import numpy as np

from s03_erc20_model import expect_revert, require
from s11_atomic_dvp import AtomicDvP, setup
from s12_ops_risk import MultiSig


# ---------- 10회차(결제 지연) Table 10.1 실험
def el(L, sigma, h):
    return 0.0 if L == 0 else (1 - math.exp(-h * L)) * sigma * math.sqrt(L) / math.sqrt(2 * math.pi)


def sol_settlement():
    print("[10회차] 결제 지연 모형 실험 (명목 10억 원, 원)")
    base = dict(sigma=0.01, h=0.10 / 250)
    print(f"  기준 T+2 {el(2, **base)*1e9:,.1f} / T+1 {el(1, **base)*1e9:,.1f}")
    mmf = dict(sigma=0.0005, h=0.10 / 250)
    print(f"  ① 국채 MMF(σ 0.05%): T+2 {el(2, **mmf)*1e9:,.1f}, T+1 {el(1, **mmf)*1e9:,.1f} → σ에 정확히 비례(1/20)")
    safe = dict(sigma=0.01, h=0.005 / 250)
    r = el(2, **safe) / el(2, **base)
    print(f"  ② 부도 강도 연 0.5%: T+2 {el(2, **safe)*1e9:,.1f}, 기준 대비 {r:.4f}배 (0.005/0.10 = 0.05와 거의 같음, hL이 작기 때문)")
    for lab, L in [("1시간", 1 / 24), ("반나절", 0.5), ("1일", 1.0)]:
        print(f"  ③ DVP 대금 확인 {lab}: {el(L, **base)*1e9:,.1f}")
    print("     → 대금 확인에 1영업일이 걸리면 ibet식 DVP의 대체비용은 T+1과 같아진다.")
    rng = np.random.default_rng(1)
    n, L = 2_000_000, 2.0
    p = 1 - math.exp(-base["h"] * L)
    z_t = rng.standard_t(3, n) / math.sqrt(3)        # 분산 1로 맞춘 t(3)
    z_n = rng.standard_normal(n)
    mc_t = p * np.maximum(base["sigma"] * math.sqrt(L) * z_t, 0).mean() * 1e9
    mc_n = p * np.maximum(base["sigma"] * math.sqrt(L) * z_n, 0).mean() * 1e9
    q99_t = np.quantile(base["sigma"] * math.sqrt(L) * z_t, 0.99) * 1e9
    q99_n = np.quantile(base["sigma"] * math.sqrt(L) * z_n, 0.99) * 1e9
    print(f"  ④ 분산을 같게 맞춘 t(3): 기대손실 {mc_t:,.1f} (정규 {mc_n:,.1f}), 가격변화 99% 분위 {q99_t/1e6:,.1f}백만 (정규 {q99_n/1e6:,.1f}백만)")
    print("     → 기대손실은 약 20% 작게 나오지만 99% 분위는 더 크다. 같은 분산이라도 꼬리가 두꺼우면 큰 손실이 더 자주 난다. 기대값만 보는 모형은 꼬리위험을 드러내지 못한다.\n")


# ---------- 11회차(대금) 과제 1: 결제 기한
class AtomicDvPWithDeadline(AtomicDvP):
    def __init__(self, sec, cash):
        super().__init__(sec, cash)
        self.block = 0
        self.deadline: dict[str, int] = {}

    def offer(self, seller, qty, deadline):
        self.sec.approve(seller, self.addr, qty)
        self.deadline[seller] = deadline

    def settle(self, seller, buyer, qty, price):
        require(self.block <= self.deadline.get(seller, -1), "offer expired")
        super().settle(seller, buyer, qty, price)

    def withdraw_offer(self, seller):
        require(self.block > self.deadline.get(seller, -1), "offer still live")
        self.sec.approve(seller, self.addr, 0)


def sol_deadline():
    print("[11회차] 결제 기한")
    sec, cash = setup()
    d = AtomicDvPWithDeadline(sec, cash)
    d.offer("매도자", 10, deadline=100)
    expect_revert(lambda: d.withdraw_offer("매도자"), "offer still live")
    d.block = 101
    cash.approve("매수자", d.addr, 100_000)
    expect_revert(lambda: d.settle("매도자", "매수자", 10, 100_000), "offer expired")
    d.withdraw_offer("매도자")
    print("  기한 전에는 매도자도 철회 못 함(매수자 보호), 기한 뒤에는 결제 불가·철회 가능(매도자 보호)")
    print("  남은 승인:", sec.allowance[("매도자", d.addr)], "\n")


# ---------- 12회차(운영) 과제 1: 강제 이전에 2-of-3 다중서명
class Token:
    def __init__(self, ms: MultiSig):
        self.ms, self.bal, self.n = ms, {"민": 500}, 0

    def propose_forced(self, frm, to, amount):
        self.n += 1
        aid = f"forced#{self.n}:{frm}->{to}:{amount}"
        return aid

    def forced_transfer(self, aid, frm, to, amount):
        require(self.ms.can_execute(aid), "multisig: not enough approvals")
        require(aid.endswith(f"{frm}->{to}:{amount}"), "params do not match approval")
        self.bal[frm] -= amount
        self.bal[to] = self.bal.get(to, 0) + amount


def sol_multisig():
    print("[12회차] 강제 이전 + 2-of-3")
    ms = MultiSig(["운영팀", "준법감시", "외부수탁"], threshold=2)
    t = Token(ms)
    aid = t.propose_forced("민", "상속인", 500)
    ms.approve("운영팀", aid)
    expect_revert(lambda: t.forced_transfer(aid, "민", "상속인", 500), "multisig: not enough approvals")
    ms.approve("준법감시", aid)
    expect_revert(lambda: t.forced_transfer(aid, "민", "공격자", 500), "params do not match approval")
    t.forced_transfer(aid, "민", "상속인", 500)
    print("  승인 2개 뒤에만 실행, 승인한 내용과 다른 수신자로는 실행 불가:", t.bal)
    print("  핵심: 승인 대상에 '무엇을'까지 묶어야 한다. 승인 번호만 확인하면 승인 뒤 내용을 바꿔치기할 수 있다.\n")


# ---------- 13회차(유동성) 과제 1·2
def market(q, limit, resale_p=0.0, discount=0.0, seed=7, N=5_000, M=20, days=250, per_day=40, lot=20e6, expire=20):
    rng = np.random.default_rng(seed)
    elig = rng.random(N) < q
    net = np.zeros(N)
    b = 0.05 * (1 + 10 * discount)                 # 단순 수요곡선: 1% 할인마다 의향 10% 증가
    filled = total = 0
    queue = []
    for _ in range(days):
        aged = [w + 1 for w in queue]
        total += sum(1 for w in aged if w > expire)
        queue = [w for w in aged if w <= expire] + [0] * per_day
        still = []
        for w in queue:
            c = rng.integers(0, N, M)
            ok = elig[c] & (rng.random(M) < b)
            if limit:
                ok &= net[c] + lot <= 1e8
            hit = np.flatnonzero(ok)
            if hit.size:
                j = c[hit[0]]
                net[j] += lot
                filled += 1; total += 1
                if resale_p and rng.random() < resale_p:   # 산 사람이 나중에 되팔면 순매수가 줄어든다
                    net[j] -= lot
            else:
                still.append(w)
        queue = still
    total += len(queue)
    return filled / total


def sol_liquidity():
    print("[13회차] 자격 비율 0.2, 1억 원 한도에서")
    base = market(0.2, True)
    resale = market(0.2, True, resale_p=0.5)
    print(f"  ① 되팔기 없음 {base:.1%} → 매수자 절반이 되팔면 {resale:.1%} (순매수 기준이라 한도가 다시 생김)")
    for d in [0.0, 0.01, 0.02]:
        print(f"  ② 할인 {d:.0%}: 한도 없음 {market(0.2, False, discount=d):.1%}, 1억 한도 {market(0.2, True, discount=d):.1%}")
    print("  해석: 한도가 걸리면 할인해도 체결률이 별로 오르지 않는다. 문제는 의향이 아니라 한도에 묶인 매수 여력이기 때문이다.")


if __name__ == "__main__":
    sol_settlement(); sol_deadline(); sol_multisig(); sol_liquidity()
