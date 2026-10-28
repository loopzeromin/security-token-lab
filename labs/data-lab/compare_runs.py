"""
재현성 검사. 같은 스크립트로 두 번 받은 데이터를 같은 블록까지 잘라 비교한다.
실행: python compare_runs.py 첫번째.csv 두번째.csv 기준블록
"""
import csv
import sys


def load(path, upto):
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            if int(r["block"]) <= upto:
                out[(r["tx"], int(r["log_index"]))] = r
    return out


a_path, b_path, upto = sys.argv[1], sys.argv[2], int(sys.argv[3])
a, b = load(a_path, upto), load(b_path, upto)
print(f"블록 {upto:,}까지: 첫 번째 {len(a):,}건, 두 번째 {len(b):,}건, 공통 {len(a.keys() & b.keys()):,}건")
for name, x, y in (("첫 번째에만", a, b), ("두 번째에만", b, a)):
    only = sorted(x.keys() - y.keys(), key=lambda k: int(x[k]["block"]))
    print(f"{name} 있는 기록 {len(only)}건")
    for k in only[:20]:
        r = x[k]
        print(f"  블록 {int(r['block']):,} {r['tx'][:12]}… {r['from'][:10]}… → {r['to'][:10]}… {float(r['amount']):,.2f}")
diff = [k for k in a.keys() & b.keys() if abs(float(a[k]["amount"]) - float(b[k]["amount"])) > 1e-9]
print(f"공통 기록 중 금액이 다른 것 {len(diff)}건")
