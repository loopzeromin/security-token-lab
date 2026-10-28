#!/usr/bin/env bash
# 실습 실행. 사용법:
#   bash run.sh part1      1–6, 11–13회차 파이썬 실습과 해설
#   bash run.sh a          Lab A (ibet) 실습·해설 테스트
#   bash run.sh b          Lab B (ERC-3643) 실습·해설 테스트
#   bash run.sh c          Lab C 결제 지연 위험 모형
#   bash run.sh data       14회차 BUIDL 데이터 받기·검사·분석 (몇 분)
#   bash run.sh all        part1, a, b, c 전부
WS="$(cd "$(dirname "$0")" && pwd)"
PY="$WS/.venv/bin/python"
export PATH="$HOME/.local/bin:$HOME/.foundry/bin:$PATH" CI=true HARDHAT_DISABLE_TELEMETRY_PROMPT=true

# 설치가 끝나기 전에 실행하면 Lab A, B 폴더가 아직 없다
if ! grep -q "준비 완료" "$WS/.devcontainer/setup.log" 2>/dev/null; then
  echo "아직 설치 중이다. 끝나면 '준비 완료'가 보인다. 진행 상황 보기:"
  echo "  tail -f .devcontainer/setup.log"
  echo "설치가 오류로 멈췄으면 처음부터 다시: bash .devcontainer/setup.sh"
  exit 1
fi

part1() {
  cd "$WS/labs/part1"
  for f in s0*.py s1*.py sol_*.py; do
    if "$PY" "$f" > /tmp/out.txt 2>&1; then echo "PASS  $f"; else echo "FAIL  $f"; cat /tmp/out.txt; fi
  done
}
lab_a() {
  cp "$WS"/labs/lab-a-ibet/*.py "$WS/vendor/ibet-SmartContract/tests/study/"
  cd "$WS/vendor/ibet-SmartContract" && uv run ape test --network ethereum:local:foundry tests/study -v
}
lab_b() {
  cp "$WS"/labs/lab-b-erc3643/*.test.ts "$WS/vendor/ERC-3643/test/study/"
  cd "$WS/vendor/ERC-3643" && npx hardhat test test/study/study-transfer-gate.test.ts test/study/solution-country.test.ts
}
lab_c() { cd "$WS/labs/lab-c-settlement" && "$PY" settlement_risk.py; }
data() {
  cd "$WS/labs/data-lab"
  "$PY" -u fetch_buidl.py && "$PY" -u check_supply.py && "$PY" -u analyze_buidl.py && "$PY" -u sol_data.py
}

case "${1:-}" in
  part1) part1 ;; a) lab_a ;; b) lab_b ;; c) lab_c ;; data) data ;;
  all) part1; echo; lab_a; echo; lab_b; echo; lab_c ;;
  *) sed -n '2,9p' "$0" ;;
esac
