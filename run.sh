#!/usr/bin/env bash
# 실습 실행. 사용법:
#   bash run.sh part1      1–6, 11–13, 15회차 파이썬 실습과 해설
#   bash run.sh a          Lab A (ibet) 실습·해설 테스트
#   bash run.sh b          Lab B (ERC-3643) 실습·해설 테스트
#   bash run.sh c          Lab C 결제 지연 위험 모형
#   bash run.sh data       14회차 BUIDL 데이터 받기·검사·분석 (몇 분)
#   bash run.sh japan      14회차 일본 공모 ST 94건 분석 (몇 초)
#   bash run.sh design     15회차 완성 사례 모형 (시나리오 15개, 3초)
#   bash run.sh test       교재 숫자 회귀 테스트 (pytest, 약 30초)
#   bash run.sh nb         노트북 3개를 다시 실행해 출력 갱신 (2분 안팎)
#   bash run.sh all        part1, a, b, c 전부
WS="$(cd "$(dirname "$0")" && pwd)"
PY="$WS/.venv/bin/python"
export PATH="$HOME/.local/bin:$HOME/.foundry/bin:$PATH" CI=true HARDHAT_DISABLE_TELEMETRY_PROMPT=true

[ -x "$PY" ] || PY="$(command -v python3)"   # Codespaces 밖(내 컴퓨터)에서는 시스템 python3

# Lab A, B는 설치가 끝나야 vendor/ 폴더가 생긴다
need_setup() {
  if ! grep -q "준비 완료" "$WS/.devcontainer/setup.log" 2>/dev/null; then
    echo "Lab A·B는 설치가 끝나야 돌릴 수 있다. 끝나면 '준비 완료'가 보인다. 진행 상황 보기:"
    echo "  tail -f .devcontainer/setup.log"
    echo "설치가 오류로 멈췄으면 처음부터 다시: bash .devcontainer/setup.sh"
    exit 1
  fi
}

part1() {
  cd "$WS/labs/part1"
  for f in s0*.py s1*.py sol_*.py; do
    if "$PY" "$f" > /tmp/out.txt 2>&1; then echo "PASS  $f"; else echo "FAIL  $f"; cat /tmp/out.txt; fi
  done
}
lab_a() {
  need_setup
  cp "$WS"/labs/lab-a-ibet/*.py "$WS/vendor/ibet-SmartContract/tests/study/"
  cd "$WS/vendor/ibet-SmartContract" && uv run ape test --network ethereum:local:foundry tests/study -v
}
lab_b() {
  need_setup
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
  japan) cd "$WS/labs/data-lab" && "$PY" analyze_japan.py ;;
  design) cd "$WS/labs/part1" && "$PY" s15_capstone_model.py ;;
  test) cd "$WS" && "$PY" -m pytest -q ;;
  nb) cd "$WS/notebooks" && "$PY" -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 0*.ipynb ;;
  all) part1; echo; lab_a; echo; lab_b; echo; lab_c ;;
  *) sed -n '2,12p' "$0" ;;
esac
