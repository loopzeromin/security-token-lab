"""문제집(토큰증권, 문제와 해설) 계산 문제의 답을 다시 계산한다. 문제 번호는 문제집 번호."""
import math
from math import comb, exp, sqrt, pi, log

import pytest


def test_1_2_netting():
    trades = [("A", "B", 30), ("B", "C", 20), ("C", "A", 10), ("A", "C", 5), ("B", "A", 15)]
    gross = sum(x for *_, x in trades)
    net = {}
    for p, r, x in trades:
        net[p] = net.get(p, 0) - x
        net[r] = net.get(r, 0) + x
    pair = {}
    for p, r, x in trades:
        k = tuple(sorted((p, r)))
        pair[k] = pair.get(k, 0) + (x if (p, r) == k else -x)
    assert gross == 80
    assert sum(abs(v) for v in pair.values()) == 40
    assert net == {"A": -10, "B": -5, "C": 15}
    assert sum(v for v in net.values() if v > 0) / gross == 0.1875


def test_2_2_catch_up():
    assert (0.1 / 0.9) ** 5 == pytest.approx(1.69e-5, rel=1e-2)
    z = math.ceil(log(1e-3) / log(3 / 7))
    assert z == 9 and (3 / 7) ** 9 < 1e-3 < (3 / 7) ** 8


def test_2_4_bft():
    f = lambda n: (n - 1) // 3
    assert f(7) == 2 and f(4) == 1 and 3 * 3 + 1 == 10


def test_3_1_erc20_trace():
    bal, allow = {"민": 100, "지수": 0}, 0
    allow = 30
    bal["민"] -= 20; bal["지수"] += 20; allow -= 20
    assert 15 > allow                       # 3단계 revert
    bal["민"] -= 50; bal["지수"] += 50
    assert (bal["민"], bal["지수"], allow) == (30, 70, 10)


def test_5_2_japan_mean():
    assert round(4075 / 94, 1) == 43.4
    assert round(314.1 / 4075 * 100, 1) == 7.7


def test_6_2_6_3_concentration():
    s = [40, 25, 15, 10, 10]
    hhi = sum(x * x for x in s)
    assert hhi == 2650 and round(1e4 / hhi, 1) == 3.8
    x = sorted(s)
    n = len(x)
    g = sum((2 * (i + 1) - n - 1) * x[i] for i in range(n)) / (n * sum(x))
    assert g == pytest.approx(0.30)
    assert round(1e4 / 1573, 1) == 6.4


def loss(L, sigma=0.01, h=0.10 / 250, N=1e9):
    return (1 - exp(-h * L)) * N * sigma * sqrt(L) / sqrt(2 * pi)


def test_8_1_and_10_1_settlement():
    assert loss(0.5) / loss(2) == pytest.approx(0.125, abs=1e-3)
    assert round(loss(2, sigma=0.02), 1) == 9023.4
    assert round(loss(1, sigma=0.02), 1) == 3190.9


def test_10_2_elasticity():
    eps = lambda x: x / (exp(x) - 1) + 0.5
    assert eps(0.0004) == pytest.approx(1.4998, abs=1e-4)
    assert round(eps(1.0), 2) == 1.08


def test_10_3_t3_tail():
    e_abs_t3 = 2 * sqrt(3) * math.gamma(2) / (sqrt(pi) * 2 * math.gamma(1.5))
    assert e_abs_t3 / 2 / sqrt(3) == pytest.approx(1 / pi)
    assert round(4.541 / sqrt(3), 2) == 2.62


def mofn(p, M, N):
    return sum(comb(N, k) * p ** k * (1 - p) ** (N - k) for k in range(M, N + 1))


def test_12_1_multisig():
    assert mofn(0.05, 2, 3) == pytest.approx(0.00725)
    assert mofn(0.05, 3, 5) == pytest.approx(0.00116, abs=1e-5)
    assert 0.01 + 0.99 * mofn(0.05, 2, 3) == pytest.approx(0.0172, abs=1e-4)


def daily(q, M=20, B=0.05):
    return 1 - (1 - q * B) ** M


def test_13_1_13_3_liquidity():
    p = daily(0.1)
    assert round(p, 4) == 0.0954 and round((1 - (1 - p) ** 21) * 100, 1) == 87.8
    p = daily(0.2)
    ek = sum(k * p * (1 - p) ** k for k in range(21)) / (1 - (1 - p) ** 21)
    assert round(ek, 2) == 4.18 and round((1 - p) / p, 2) == 4.49


def test_13_2_cap():
    cap = lambda lots, q: min(1, lots * q * 5000 / (40 * 250))
    assert cap(5, 0.2) == 0.5 and cap(10, 0.2) == 1 and cap(10, 0.1) == 0.5
    assert 5 * 1039 / 10000 == pytest.approx(0.5195)   # s13 시드의 실제 자격자 1,039명


def test_14_1_supply():
    mint, burn = 100 + 50, 10
    bal = {"A": 100 - 30 + 20, "B": 30 - 10, "C": 50 - 20}
    assert mint - burn == sum(bal.values()) == 140


def test_15_3_distribution():
    bal = {"a": 600_000, "b": 300_000, "c": 100_001}
    cash, tot = 1_000_000, sum(bal.values())
    pay = {k: cash * v // tot for k, v in bal.items()}
    pay["a"] += cash - sum(pay.values())
    assert pay == {"a": 600_001, "b": 299_999, "c": 100_000}
