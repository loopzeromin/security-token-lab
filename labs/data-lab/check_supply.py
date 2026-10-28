"""
실증 실습 1-b단계. 받은 기록이 빠짐없는지 검사한다.

기록으로 다시 쌓은 주소별 잔액을 계약의 balanceOf(주소)와 하나씩 비교한다.
어긋나는 주소가 있으면 그 주소가 보내거나 받은 Transfer만 탐색기에 다시 요청해서,
CSV에 없던 기록을 찾아 붙인다.

실행: python -u check_supply.py   (fetch_buidl.py 다음)
"""

import os
import csv
import json
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path

from fetch_buidl import EXPLORERS, RPCS, START_BLOCK, TOKEN, TRANSFER_TOPIC, h2i, http, rpc_one

DATA = Path(os.environ.get("ST_DATA_DIR", Path(__file__).parent / "data"))  # 다른 폴더에 받으려면 ST_DATA_DIR 지정
ZERO = "0x" + "0" * 40


def rebuilt():
    bal, rows = defaultdict(float), []
    with open(DATA / "buidl_transfers.csv") as f:
        for r in csv.DictReader(f):
            rows.append(r)
            a = float(r["amount"])
            if r["from"] != ZERO:
                bal[r["from"]] -= a
            if r["to"] != ZERO:
                bal[r["to"]] += a
    return bal, rows


def balance_of(addr, dec):
    data = "0x70a08231" + addr[2:].rjust(64, "0")
    for url in RPCS:
        try:
            return h2i(rpc_one(url, "eth_call", [{"to": TOKEN, "data": data}, "latest"])) / 10**dec
        except Exception:
            continue
    raise RuntimeError("balanceOf 호출 실패")


def logs_of(addr, latest, side):
    """side=1이면 보낸 기록(topic1), 2면 받은 기록(topic2)."""
    out, frm = [], START_BLOCK
    topic = "0x" + addr[2:].rjust(64, "0")
    for name, base in EXPLORERS.items():
        try:
            while True:
                q = urllib.parse.urlencode({"module": "logs", "action": "getLogs", "address": TOKEN, "topic0": TRANSFER_TOPIC,
                                            f"topic{side}": topic, "topic0_{}_opr".format(side): "and",
                                            "fromBlock": frm, "toBlock": latest, "page": 1, "offset": 1000})
                res = http(f"{base}?{q}")
                if res.get("status") != "1":
                    if "No " in str(res.get("message")):
                        return out
                    raise RuntimeError(res.get("message"))
                out += res["result"]
                if len(res["result"]) < 1000:
                    return out
                frm = max(h2i(l["blockNumber"]) for l in res["result"])
                time.sleep(1.5)
        except Exception as e:
            print(f"  {name} 실패({str(e)[:50]}), 다음 탐색기로")
            out, frm = [], START_BLOCK
            time.sleep(3)
    raise RuntimeError("주소별 기록을 받지 못했다")


def main():
    meta = json.loads((DATA / "buidl_meta.json").read_text())
    dec, latest = meta["decimals"], meta["latest_block"]
    bal, rows = rebuilt()
    print(f"검사할 주소 {len(bal)}개 (현재 블록 기준 balanceOf와 비교)")
    off = []
    for k, (a, v) in enumerate(sorted(bal.items(), key=lambda x: -x[1])):
        chain = balance_of(a, dec)
        if abs(chain - v) > 1e-3:
            off.append((a, v, chain))
            print(f"  불일치 {a}: 기록 {v:,.2f}, 체인 {chain:,.2f}, 차이 {v - chain:,.2f}")
        time.sleep(0.2)
    if not off:
        print("  모든 주소가 일치한다")
        return
    have = {(r["tx"], int(r["log_index"])) for r in rows}
    found = []
    for a, _, _ in off:
        for side in (1, 2):
            for l in logs_of(a, latest, side):
                k = (l["transactionHash"], h2i(l["logIndex"]))
                if k not in have:
                    have.add(k)
                    found.append([h2i(l["blockNumber"]), h2i(l["timeStamp"]), l["transactionHash"], k[1],
                                  "0x" + l["topics"][1][-40:], "0x" + l["topics"][2][-40:], h2i(l["data"]) / 10**dec])
    print(f"  CSV에 없던 기록 {len(found)}건")
    for f in found:
        print(f"    블록 {f[0]:,} tx {f[2][:12]}… {f[4][:10]}… → {f[5][:10]}… {f[6]:,.2f}")
    if found:
        all_rows = [[int(r["block"]), int(r["timestamp"]), r["tx"], int(r["log_index"]), r["from"], r["to"], float(r["amount"])]
                    for r in rows] + found
        all_rows.sort(key=lambda x: (x[0], x[3]))
        with open(DATA / "buidl_transfers.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["block", "timestamp", "tx", "log_index", "from", "to", "amount"])
            w.writerows(all_rows)
        meta["n_transfers"] = len(all_rows)
        meta["added_by_check"] = len(found)
        (DATA / "buidl_meta.json").write_text(json.dumps(meta, indent=2))
        bal2 = defaultdict(float)
        for r in all_rows:
            if r[4] != ZERO:
                bal2[r[4]] -= r[6]
            if r[5] != ZERO:
                bal2[r[5]] += r[6]
        print(f"  보완 후 잔액 합 {sum(v for v in bal2.values() if v > 1e-9):,.2f} / 총발행 {meta['total_supply_now']:,.2f}")


if __name__ == "__main__":
    main()
