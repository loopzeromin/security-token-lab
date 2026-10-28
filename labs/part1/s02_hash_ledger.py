"""
2회차 실습. 해시로 이어 붙인 장부는 왜 고치기 어려운가

블록 하나 = (이전 블록의 해시, 거래 목록). 블록의 해시는 내용 전체로 계산한다.
중간 블록 하나를 고치면 그 블록의 해시가 바뀌고, 다음 블록이 기억하는 "이전 해시"와 어긋난다.

실행: python3 s02_hash_ledger.py   (표준 라이브러리만 사용)
"""

import copy
import hashlib
import json


def block_hash(block: dict) -> str:
    # 키 순서를 고정해야 같은 내용이 늘 같은 해시가 된다
    raw = json.dumps(block, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def append_block(chain: list, txs: list) -> None:
    prev = block_hash(chain[-1]) if chain else "0" * 64
    chain.append({"height": len(chain), "prev": prev, "txs": txs})


def verify(chain: list) -> tuple[bool, int | None]:
    """처음부터 다시 계산해서 어긋나는 첫 블록 번호를 돌려준다"""
    for i in range(1, len(chain)):
        if chain[i]["prev"] != block_hash(chain[i - 1]):
            return False, i
    return True, None


def balances(chain: list) -> dict:
    bal: dict = {}
    for b in chain:
        for frm, to, amt in b["txs"]:
            if frm != "발행":
                bal[frm] = bal.get(frm, 0) - amt
            bal[to] = bal.get(to, 0) + amt
    return bal


def main():
    chain: list = []
    append_block(chain, [("발행", "민", 100)])                 # 0번: 발행
    append_block(chain, [("민", "지수", 30)])                    # 1번
    append_block(chain, [("지수", "현우", 10), ("민", "현우", 5)])  # 2번
    append_block(chain, [("현우", "민", 15)])                    # 3번

    print("정상 장부 검증:", verify(chain))
    print("잔고:", balances(chain))

    # 노드 3곳이 같은 사본을 가진다
    nodes = [copy.deepcopy(chain) for _ in range(3)]

    # 노드 0에서 1번 블록의 금액을 몰래 30 → 3으로 고친다
    nodes[0][1]["txs"][0] = ("민", "지수", 3)
    ok, at = verify(nodes[0])
    print(f"\n노드 0 위변조 후 검증: {ok}, 어긋난 블록 {at}")
    print("(1번 블록 내용이 바뀌어 해시가 달라졌고, 2번 블록의 prev와 맞지 않는다)")

    # 해시까지 맞추려면 이후 블록의 prev를 전부 다시 써야 한다
    for i in range(1, len(nodes[0])):
        nodes[0][i]["prev"] = block_hash(nodes[0][i - 1])
    print("노드 0이 뒤 블록을 전부 다시 쓴 뒤 자기 검증:", verify(nodes[0]))

    # 그래도 다른 두 노드와 마지막 해시가 다르다 → 다수결에서 진다
    tips = [block_hash(n[-1])[:12] for n in nodes]
    print("세 노드의 마지막 블록 해시:", tips)
    majority = max(set(tips), key=tips.count)
    print("다수가 가진 장부:", majority, "→ 노드 0의 장부는 채택되지 않는다")

    assert verify(chain)[0]
    assert tips[1] == tips[2] != tips[0]


if __name__ == "__main__":
    main()
