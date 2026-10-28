"""
9회차 과제 1 해설: ibet 이전 신청 취소(cancelTransfer) 권한
원본 IbetStraightBond.sol 754행: 신청자 본인이나 발행자만 취소 가능(120801), 이미 끝난 신청은 취소 불가(120802)
위치: ibet-SmartContract/tests/study/
"""

from ape import project
from ape_utils import ZERO_ADDRESS, reverts


def issue_bond(issuer, personal_info_address):
    args = ["study_bond", "BND", 10000, 10000, "JPY", "20291231", 100, "JPY", "20291231", "r", "study"]
    bond = issuer.deploy(project.IbetStraightBond, *args)  # type: ignore
    bond.setTradableExchange(ZERO_ADDRESS, sender=issuer)
    bond.setPersonalInfoAddress(personal_info_address, sender=issuer)
    bond.setTransferable(True, sender=issuer)
    return bond


class TestSolutionCancel:
    def test_cancel_permissions(self, users, personal_info):
        issuer, user1, user2, stranger = users["issuer"], users["user1"], users["user2"], users["agent"]
        bond = issue_bond(issuer, personal_info.address)

        personal_info.register(issuer.address, "enc", sender=user1)
        personal_info.register(issuer.address, "enc", sender=user2)
        bond.transfer(user1.address, 100, sender=issuer)
        bond.setTransferApprovalRequired(True, sender=issuer)

        bond.applyForTransfer(user2.address, 100, "apply", sender=user1)
        assert bond.balanceOf(user1) == 0                     # 보류로 넘어감

        with reverts("120801"):                               # 제3자는 취소 불가
            bond.cancelTransfer(0, "x", sender=stranger)

        bond.cancelTransfer(0, "by issuer", sender=issuer)    # 발행자는 취소 가능
        assert bond.balanceOf(user1) == 100                   # 잔고 복구

        with reverts("120802"):                               # 이미 무효가 된 신청
            bond.cancelTransfer(0, "again", sender=user1)

        bond.applyForTransfer(user2.address, 40, "apply2", sender=user1)
        bond.cancelTransfer(1, "by applicant", sender=user1)  # 신청자 본인도 취소 가능
        assert bond.balanceOf(user1) == 100
