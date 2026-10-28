"""
실증 실습 1단계. BUIDL 토큰의 Transfer 기록을 이더리움에서 직접 받아 CSV로 저장한다.

- 대상: BlackRock USD Institutional Digital Liquidity Fund (BUIDL), 이더리움 계약
        0x7712c34205737192402172409a8f7ccef8aa2aec
- 방법: ERC-20 Transfer 이벤트 로그(3회차)를 공개 서비스에서 받는다.
    1순위  Blockscout(오픈소스 블록 탐색기)·Routescan 공개 API. 키 불필요. 1,000건씩 끊어 받는다.
    2순위  공개 이더리움 노드에 JSON-RPC eth_getLogs. 노드마다 허용 블록 범위가 달라 범위를 줄여 가며 시도한다.
- 필요: 표준 라이브러리만. 인터넷 연결.
- 실행: python -u fetch_buidl.py
- 결과: data/buidl_transfers.csv, data/buidl_meta.json
"""

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN = "0x7712c34205737192402172409a8f7ccef8aa2aec"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
START_BLOCK = 19_300_000          # 2024년 2월 말. BUIDL 발행(2024년 3월) 이전
EXPLORERS = {   # Etherscan과 같은 형식(module=logs&action=getLogs)을 키 없이 여는 공개 탐색기
    "blockscout": "https://eth.blockscout.com/api",
    "routescan": "https://api.routescan.io/v2/network/mainnet/evm/1/etherscan/api",
}
RPCS = ["https://ethereum-rpc.publicnode.com", "https://eth.drpc.org", "https://eth.llamarpc.com",
        "https://eth.merkle.io", "https://1rpc.io/eth"]
OUT = Path(__file__).parent / "data"
UA = {"content-type": "application/json", "user-agent": "st-lab/1.1"}


def http(url, payload=None, timeout=60):
    """JSON을 주고받는다. HTTP 오류여도 본문이 JSON이면 그대로 돌려준다."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return json.loads(body)
        except Exception:
            raise RuntimeError(f"HTTP {e.code}: {body[:120]!r}")


def h2i(x):
    return int(x, 16) if x and x != "0x" else 0


# ---------------------------------------------------------------- 1순위: Blockscout
def from_explorer(name, latest):
    """1,000건씩 받는다. 요청이 많다고 거절하면 기다렸다 다시 하고, 받은 만큼 data/partial.json에 저장해 둔다."""
    part = OUT / "partial.json"
    logs = json.loads(part.read_text()) if part.exists() else []
    seen = {(l["tx"], l["li"]) for l in logs}
    frm = max((l["block"] for l in logs), default=START_BLOCK)
    if logs:
        print(f"  이전에 받은 {len(logs):,}건에 이어서 블록 {frm:,}부터 받는다")
    while True:
        q = urllib.parse.urlencode({"module": "logs", "action": "getLogs", "address": TOKEN,
                                    "topic0": TRANSFER_TOPIC, "fromBlock": frm, "toBlock": latest,
                                    "page": 1, "offset": 1000})
        for t in range(5):                # 최대 2분 반 기다리고 안 되면 다음 탐색기로
            try:
                res = http(f"{EXPLORERS[name]}?{q}")
            except Exception as e:
                res = {"status": "0", "message": f"network: {str(e)[:60]}"}
            msg = str(res.get("message"))
            if res.get("status") == "1" or "No logs" in msg or "No records" in msg:
                break
            wait = 10 * (t + 1)
            print(f"  잠시 대기 {wait}초 ({msg[:50]})")
            time.sleep(wait)
        else:
            raise RuntimeError(f"{name} 응답: {msg}")
        batch = res.get("result") or []
        if not batch:
            break
        new = 0
        for l in batch:
            k = (l["transactionHash"], h2i(l["logIndex"]))
            if k not in seen:
                seen.add(k)
                logs.append({"block": h2i(l["blockNumber"]), "ts": h2i(l["timeStamp"]), "tx": l["transactionHash"],
                             "li": h2i(l["logIndex"]), "topics": l["topics"], "data": l["data"]})
                new += 1
        last = max(h2i(l["blockNumber"]) for l in batch)
        print(f"  [{name}] 블록 {frm:,}부터: {len(batch)}건 받음, 새 {new}건 (누적 {len(logs):,}, 마지막 블록 {last:,})")
        part.write_text(json.dumps(logs))
        if len(batch) < 1000:
            break
        if new == 0:                      # 한 블록에 1,000건이 넘는 경우는 없다고 보고 다음 블록으로
            last += 1
        frm = last                        # 마지막 블록은 다시 받아 중복 제거
        time.sleep(1.5)
    return logs


# ---------------------------------------------------------------- 2순위: JSON-RPC
def rpc_one(url, method, params):
    res = http(url, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if "error" in res:
        raise ValueError(str(res["error"])[:120])
    return res["result"]


def from_rpc(latest):
    logs, frm = [], START_BLOCK
    step = {u: 10_000 for u in RPCS}     # 노드별로 통하는 범위를 따로 기억한다
    i = 0
    while frm <= latest:
        url = RPCS[i % len(RPCS)]
        to = min(frm + step[url] - 1, latest)
        try:
            part = rpc_one(url, "eth_getLogs", [{"address": TOKEN, "topics": [TRANSFER_TOPIC],
                                                 "fromBlock": hex(frm), "toBlock": hex(to)}])
        except Exception as e:
            step[url] //= 2
            print(f"  {url.split('//')[1]} 거부 → 이 노드 범위 {step[url]:,}블록 ({str(e)[:70]})")
            if step[url] < 500:                 # 너무 좁게만 허용하는 노드는 뺀다
                RPCS.remove(url)
                if not RPCS:
                    raise RuntimeError("모든 노드가 거부")
            i += 1
            time.sleep(1)
            continue
        for l in part:
            logs.append({"block": h2i(l["blockNumber"]), "ts": None, "tx": l["transactionHash"],
                         "li": h2i(l["logIndex"]), "topics": l["topics"], "data": l["data"]})
        print(f"  블록 {frm:,}–{to:,}: {len(part)}건 (누적 {len(logs):,}) via {url.split('//')[1]}")
        frm = to + 1
    url = RPCS[0]
    blocks = sorted({l["block"] for l in logs})
    times = {}
    for k in range(0, len(blocks), 40):
        res = http(url, [{"jsonrpc": "2.0", "id": b, "method": "eth_getBlockByNumber", "params": [hex(b), False]}
                         for b in blocks[k:k + 40]])
        for r in res if isinstance(res, list) else []:
            if r.get("result"):
                times[int(r["id"])] = h2i(r["result"]["timestamp"])
        for b in blocks[k:k + 40]:
            if b not in times:
                times[b] = h2i(rpc_one(url, "eth_getBlockByNumber", [hex(b), False])["timestamp"])
    for l in logs:
        l["ts"] = times[l["block"]]
    return logs


def chain_state():
    """최신 블록, decimals, 현재 총발행. 노드를 차례로 시도한다."""
    for url in RPCS:
        try:
            latest = h2i(rpc_one(url, "eth_blockNumber", []))
            dec = h2i(rpc_one(url, "eth_call", [{"to": TOKEN, "data": "0x313ce567"}, "latest"]))
            sup = h2i(rpc_one(url, "eth_call", [{"to": TOKEN, "data": "0x18160ddd"}, "latest"]))
            return latest, dec, sup
        except Exception as e:
            print(f"  {url.split('//')[1]} 실패: {str(e)[:60]}")
    raise RuntimeError("노드에 접속하지 못했다")


def main():
    OUT.mkdir(exist_ok=True)
    latest, decimals, supply_raw = chain_state()
    print(f"최신 블록 {latest:,}, decimals {decimals}, 현재 총발행 {supply_raw / 10**decimals:,.2f}")
    logs = None
    for name in EXPLORERS:
        try:
            logs, source = from_explorer(name, latest), name
            break
        except Exception as e:
            print(f"{name} 실패({str(e)[:70]}). 받은 만큼은 data/partial.json에 있다.")
    if logs is None:
        # 2026년 10월 확인: 무료 공개 노드는 대부분 넓은 구간의 eth_getLogs를 거부한다. 개인 키가 있는 노드면 통한다.
        print("공개 노드로도 시도한다.")
        logs, source = from_rpc(latest), "json-rpc"
    logs = [l for l in logs if l["block"] <= latest and len(l["topics"]) >= 3]

    path = OUT / "buidl_transfers.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block", "timestamp", "tx", "log_index", "from", "to", "amount"])
        for l in sorted(logs, key=lambda x: (x["block"], x["li"])):
            w.writerow([l["block"], l["ts"], l["tx"], l["li"], "0x" + l["topics"][1][-40:],
                        "0x" + l["topics"][2][-40:], h2i(l["data"]) / 10**decimals])
    meta = {"token": TOKEN, "decimals": decimals, "latest_block": latest, "start_block": START_BLOCK,
            "total_supply_now": supply_raw / 10**decimals, "n_transfers": len(logs), "source": source,
            "fetched_at_unix": int(time.time())}
    (OUT / "buidl_meta.json").write_text(json.dumps(meta, indent=2))
    (OUT / "partial.json").unlink(missing_ok=True)
    print(f"저장: {path} ({len(logs):,}건, 출처 {source})")


if __name__ == "__main__":
    main()
