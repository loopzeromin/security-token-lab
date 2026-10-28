"""
ibet-SmartContract 스터디용 시나리오 테스트 (회차 2~4)

코드를 읽고 세운 "예측"을 실제로 돌려서 확인하는 파일이다.
- 기준 커밋: 8092b7c (BoostryJP/ibet-SmartContract, 2026-10-26)
- 위치: ibet-SmartContract/tests/study/ 아래에 둔다 (tests/conftest.py의 fixture를 쓰기 위해)
- 실행: uv run ape test --network ethereum:local:foundry tests/study -s
  (Makefile의 make test는 항상 tests/ 전체를 같이 넘기므로 직접 실행한다)

주의: 이 파일은 작성자가 직접 실행해 보지 못했다. 실패하는 케이스가 있으면
그 줄이 "내가 코드를 잘못 읽은 곳"이므로 에러 메시지를 그대로 가져와서 다시 읽어본다.
"""

from ape import project
from ape_utils import ZERO_ADDRESS, call_view_method, reverts


def issue_bond(issuer, exchange_address, personal_info_address):
    """tests/token/test_IbetStraightBond.py의 issue_transferable_bond_token과 같은 구성."""
    deploy_args = [
        "study_bond",  # name
        "BND",  # symbol
        10000,  # total_supply (발행자 잔고로 들어간다)
        10000,  # face_value
        "JPY",
        "20291231",  # redemption_date
        100,  # redemption_value
        "JPY",
        "20291231",  # return_date
        "some_return",
        "study",  # purpose
    ]
    bond = issuer.deploy(project.IbetStraightBond, *deploy_args)  # type: ignore
    bond.setTradableExchange(exchange_address, sender=issuer)
    bond.setPersonalInfoAddress(personal_info_address, sender=issuer)
    bond.setTransferable(True, sender=issuer)
    return bond


# ---------------------------------------------------------------------------
# 시나리오 1: 개인정보 등록 게이트 (IbetStraightBond.sol 130행)
# ---------------------------------------------------------------------------
class TestScenario1PersonalInfoGate:
    def test_gate(self, users, personal_info):
        issuer = users["issuer"]
        trader = users["trader"]
        user1 = users["user1"]
        user2 = users["user2"]

        bond = issue_bond(issuer, ZERO_ADDRESS, personal_info.address)

        # 1-a. 발행자에게 개인정보를 등록하지 않은 상대에게 보내면 120202로 거절
        with reverts("120202"):
            bond.transfer(trader.address, 100, sender=issuer)
        assert bond.balanceOf(trader) == 0

        # 1-b. 등록하면 통과
        personal_info.register(issuer.address, "encrypted_message", sender=trader)
        bond.transfer(trader.address, 100, sender=issuer)
        assert bond.balanceOf(trader) == 100

        # 1-c. 발행자에게 되돌리는 전송은 검사하지 않는다 (_to == owner)
        bond.transfer(issuer.address, 10, sender=trader)
        assert bond.balanceOf(trader) == 90

        # 1-d. register()는 내용을 검증하지 않는다: 빈 문자열이어도 "등록됨"
        personal_info.register(issuer.address, "", sender=user2)
        assert personal_info.isRegistered(user2.address, issuer.address) is True
        bond.transfer(user2.address, 1, sender=issuer)
        assert bond.balanceOf(user2) == 1

        # 1-e. 발행자가 forceRegister로 대신 등록해줄 수 있다
        assert personal_info.isRegistered(user1.address, issuer.address) is False
        personal_info.forceRegister(user1.address, "issuer_filled", sender=issuer)
        assert personal_info.isRegistered(user1.address, issuer.address) is True
        bond.transfer(user1.address, 1, sender=issuer)
        assert bond.balanceOf(user1) == 1

    def test_switch_off(self, users, personal_info):
        """발행자가 스위치를 끄면 미등록 상대에게도 전송된다 (336행 setRequirePersonalInfoRegistered)."""
        issuer = users["issuer"]
        stranger = users["agent"]

        bond = issue_bond(issuer, ZERO_ADDRESS, personal_info.address)
        bond.setRequirePersonalInfoRegistered(False, sender=issuer)
        bond.transfer(stranger.address, 5, sender=issuer)
        assert bond.balanceOf(stranger) == 5


# ---------------------------------------------------------------------------
# 시나리오 2: 발행자 승인 방식 (transferApprovalRequired)
# ---------------------------------------------------------------------------
class TestScenario2ApprovalFlow:
    def test_direct_transfer_blocked_then_apply_and_approve(self, users, personal_info):
        issuer = users["issuer"]
        trader = users["trader"]

        bond = issue_bond(issuer, ZERO_ADDRESS, personal_info.address)
        personal_info.register(issuer.address, "encrypted_message", sender=trader)
        bond.setTransferApprovalRequired(True, sender=issuer)

        # 2-a. 승인 방식이 켜지면 직접 transfer는 막힌다 (발행자 본인도 예외 없음, 120201)
        with reverts("120201"):
            bond.transfer(trader.address, 100, sender=issuer)

        # 2-b. 이전 신청: 잔고에서 빠져 "보류"로 넘어간다 (미승인 상태에서는 양쪽 어디에도 안 잡힘)
        bond.applyForTransfer(trader.address, 100, "apply", sender=issuer)
        assert bond.balanceOf(issuer) == 10000 - 100
        assert bond.balanceOf(trader) == 0
        application = call_view_method(bond, "applicationsForTransfer", 0)
        print("application(from, to, amount, valid) =", application)

        # 2-c. 발행자가 승인하면 받는 쪽 잔고가 늘어난다
        bond.approveTransfer(0, "ok", sender=issuer)
        assert bond.balanceOf(trader) == 100

    def test_approve_does_not_recheck_personal_info(self, users, personal_info):
        """
        예측(코드 읽기): 개인정보 검사는 applyForTransfer(725행)에만 있고
        approveTransfer(797~838행)에는 없다. 그렇다면 신청 이후에 스위치를 켜도
        미등록 상대에게 승인으로 전달된다.
        """
        issuer = users["issuer"]
        user2 = users["user2"]

        bond = issue_bond(issuer, ZERO_ADDRESS, personal_info.address)
        bond.setTransferApprovalRequired(True, sender=issuer)

        # 스위치를 끈 상태에서 미등록 상대 앞으로 신청
        bond.setRequirePersonalInfoRegistered(False, sender=issuer)
        bond.applyForTransfer(user2.address, 100, "apply", sender=issuer)

        # 스위치를 켠다. 이제 새 신청은 120702로 막힌다.
        bond.setRequirePersonalInfoRegistered(True, sender=issuer)
        assert personal_info.isRegistered(user2.address, issuer.address) is False
        with reverts("120702"):
            bond.applyForTransfer(user2.address, 100, "apply2", sender=issuer)

        # 그런데 먼저 낸 신청은 승인된다 (예측이 맞다면)
        bond.approveTransfer(0, "ok", sender=issuer)
        assert bond.balanceOf(user2) == 100


# ---------------------------------------------------------------------------
# 시나리오 3: DVP (IbetSecurityTokenDVP.sol)
# ---------------------------------------------------------------------------
class TestScenario3Dvp:
    def test_delivery_flow_and_withdraw_gate(self, users, personal_info, st_dvp):
        """
        흐름: 예치(토큰→DVP) → createDelivery(매도자) → confirmDelivery(매수자) → finishDelivery(agent)
        예측: DVP 컨트랙트에는 PersonalInfo 참조가 없다. 그래서 finish 시점에는 미등록 매수자의
        DVP 내부 잔고가 늘어나고, 토큰 컨트랙트로 빼내는 withdraw에서 120202로 걸린다.
        """
        issuer = users["issuer"]
        buyer = users["trader"]
        agent = users["agent"]

        bond = issue_bond(issuer, st_dvp.address, personal_info.address)

        # 예치: 컨트랙트 주소로 보내는 전송은 tradableExchange만 가능 (transferToContract)
        bond.transfer(st_dvp.address, 1000, sender=issuer)
        assert st_dvp.balanceOf(issuer.address, bond.address) == 1000

        st_dvp.createDelivery(
            bond.address, buyer.address, 100, agent.address, "data", sender=issuer
        )
        delivery_id = st_dvp.latestDeliveryId()
        assert st_dvp.balanceOf(issuer.address, bond.address) == 900
        assert st_dvp.commitmentOf(issuer.address, bond.address) == 100

        st_dvp.confirmDelivery(delivery_id, sender=buyer)
        st_dvp.finishDelivery(delivery_id, sender=agent)

        # 미등록 매수자의 DVP 내부 잔고가 먼저 늘어난다
        assert st_dvp.balanceOf(buyer.address, bond.address) == 100
        assert st_dvp.commitmentOf(issuer.address, bond.address) == 0

        # 빼내는 순간 개인정보 게이트가 걸린다
        with reverts("120202"):
            st_dvp.withdraw(bond.address, sender=buyer)

        personal_info.register(issuer.address, "encrypted_message", sender=buyer)
        st_dvp.withdraw(bond.address, sender=buyer)
        assert bond.balanceOf(buyer) == 100
        assert st_dvp.balanceOf(buyer.address, bond.address) == 0

    def test_dvp_and_approval_are_exclusive(self, users, personal_info, st_dvp):
        """DVP는 transferApprovalRequired가 꺼진 토큰만 받는다 (createDelivery 4번째 체크, 260004)."""
        issuer = users["issuer"]
        buyer = users["trader"]
        agent = users["agent"]

        bond = issue_bond(issuer, st_dvp.address, personal_info.address)
        bond.transfer(st_dvp.address, 1000, sender=issuer)  # 예치(승인 방식을 켜기 전)
        bond.setTransferApprovalRequired(True, sender=issuer)

        with reverts("260004"):
            st_dvp.createDelivery(
                bond.address, buyer.address, 100, agent.address, "data", sender=issuer
            )
