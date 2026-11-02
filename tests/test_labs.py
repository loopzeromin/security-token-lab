"""실습 스크립트 회귀 테스트.

슬라이드와 문제집이 인용한 출력 숫자가 그대로 나오는지 확인한다.
스크립트를 고친 뒤 이 테스트가 깨지면, 교재의 숫자도 같이 고쳐야 한다는 뜻이다.
"""
import importlib.util
import math

import pytest

from conftest import LABS


def test_s01_netting(run):
    out = run("part1/s01_settlement_netting.py")
    assert "건별 53.1억 → 차감 3.2억 (6.1%)" in out


def test_s02_hash_ledger(run):
    out = run("part1/s02_hash_ledger.py")
    assert "정상 장부 검증: (True, None)" in out
    assert "노드 0 위변조 후 검증: False, 어긋난 블록 2" in out
    assert "다수가 가진 장부: 786a7ae68a7d" in out


def test_s03_erc20(run):
    out = run("part1/s03_erc20_model.py")
    assert "('Transfer', '민', '익명주소_0x9f', 40)" in out


def test_s04_security_token(run):
    out = run("part1/s04_security_token_model.py")
    assert "{'발행사': 900, '민': 70, '지수': 30}" in out
    assert "{'발행사': 900, '민': 100, '지수': 0}" in out


def test_s05_ibet_port(run):
    out = run("part1/s05_ibet_port.py")
    assert "2-b. 미등록자 잔고(먼저 낸 신청이 승인됨): 100" in out
    assert "2-c. 취소 후 민의 잔고: 500" in out


def test_s06_erc3643_port(run):
    out = run("part1/s06_erc3643_port.py")
    assert "{'alice': 900, 'bob': 600}" in out
    assert "{'alice': 890, 'bob': 610}" in out
    assert "charlie도 받는다: 10" in out


def test_s11_atomic_dvp(run):
    out = run("part1/s11_atomic_dvp.py")
    assert "delivered WITHOUT payment" in out


def test_s12_ops_risk(run):
    out = run("part1/s12_ops_risk.py")
    assert "탈취된 운영팀 키 하나로 실행 가능? False" in out
    assert "두 번째 서명 후 실행 가능? True" in out


@pytest.mark.parametrize("name", ["sol_basics.py", "sol_markets.py"])
def test_solutions_run(run, name):
    run(f"part1/{name}")


@pytest.mark.slow
def test_sol_advanced(run):
    out = run("part1/sol_advanced.py")
    assert "1억 한도 49.1%" in out


@pytest.mark.slow
def test_s13_liquidity(run):
    out = run("part1/s13_liquidity_sim.py")
    row = next(l for l in out.splitlines() if l.strip().startswith("0.20"))
    assert "96.5%" in row and "51.9%" in row


@pytest.mark.slow
def test_s15_capstone(run):
    out = run("part1/s15_capstone_model.py")
    assert "15/15 시나리오가 기대와 같다" in out
    assert "보유 수량 합 1,200,000" in out
    assert "2,255.9원" in out and "282.1원" in out


def _load(relpath, name):
    spec = importlib.util.spec_from_file_location(name, LABS / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_lab_c_closed_form():
    m = _load("lab-c-settlement/settlement_risk.py", "settlement_risk")
    won = {L: m.closed_form(L) * m.NOTIONAL for L in (2, 1, 0.5, 1 / 24)}
    assert round(won[2], 1) == 4511.7
    assert round(won[1], 1) == 1595.5
    assert round(won[0.5], 1) == 564.1
    assert round(won[1 / 24], 1) == 13.6
    assert won[2] / won[1] == pytest.approx(2 ** 1.5, rel=1e-3)


def test_japan_offerings(run):
    out = run("data-lab/analyze_japan.py")
    assert "공모 ST 94건" in out and "합계 407.5십억 엔" in out
    assert "1건 발행액 중앙값 2,230백만 엔, 최대 31,414백만 엔" in out
    assert "취급 10건 / 전체 94건" in out


# ---------------------------------------------------------------- 17–20회차 (심화)

def test_s17_valuation(run):
    out = run("advanced/s17_valuation.py")
    assert "1토큰 4,711원 (발행가 5,000원)" in out
    assert "발행가 기준 IRR 4.64%" in out
    assert "5,393" in out and "4,165" in out
    assert "1.05%" in out and "19.13%" in out and "26.28%" in out
    assert "세후 3.47%" in out and "세후 3.27%" in out and "세후 2.52%" in out


def test_s18_basel(run):
    out = run("advanced/s18_basel_capital.py")
    for x in ("434.8억", "504.8억", "134.8억", "2,204.8억", "기본자본의 2.18%"):
        assert x in out


def test_s19_stablecoin(run):
    out = run("advanced/s19_stablecoin_run.py")
    for x in ("0.8969", "0.8324", "0.9625", "0.9379", "11,351", "9,243", "0.9175"):
        assert x in out


def test_s20_collateral(run):
    out = run("advanced/s20_collateral.py")
    for x in ("0.086%", "0.067%", "0.066%", "0.062%", "4.047%", "8.441%", "372백만$", "186백만$", "93백만$"):
        assert x in out


def test_sol_deep(run):
    out = run("advanced/sol_deep.py")
    for x in ("4,753원", "IRR 4.64% → 4.84%", "4,165원, 기본 대비 -11.6%", "합계 필요자본 42.8억",
              "A은행 비중 1.41% 이하", "0.8083", "0.9178", "14.40%", "125백만$"):
        assert x in out
