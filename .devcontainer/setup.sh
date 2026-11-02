#!/usr/bin/env bash
# Codespace를 처음 만들 때 한 번 자동으로 실행된다. 10분 안팎 걸린다.
# 결과 기록: .devcontainer/setup.log
set -euo pipefail
WS="$(pwd)"
VENDOR="$WS/vendor"
IBET_COMMIT=8092b7c      # 교재가 인용한 줄 번호의 기준 커밋
ERC_COMMIT=2f0704d       # ERC-3643 v4.1.3
export PATH="$HOME/.local/bin:$HOME/.foundry/bin:$PATH"
step() { echo; echo "======== $1"; }

step "1. 도구: uv, Foundry"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
command -v anvil >/dev/null || { curl -L https://foundry.paradigm.xyz | bash; "$HOME/.foundry/bin/foundryup"; }
uv --version; anvil --version | head -1; node -v; npm -v

step "2. 실습용 파이썬 환경 (part1, Lab C, data-lab)"
uv venv "$WS/.venv" --python 3.12 --allow-existing
uv pip install --python "$WS/.venv/bin/python" -r "$WS/requirements-notebooks.txt"
# 그림의 한글 글꼴 (노트북)
sudo apt-get install -y -qq fonts-noto-cjk >/dev/null 2>&1 || echo "한글 글꼴 설치 생략(그림의 한글이 네모로 보일 수 있음)"

step "3. ibet-SmartContract (Lab A)"
mkdir -p "$VENDOR"
[ -d "$VENDOR/ibet-SmartContract" ] || git clone https://github.com/BoostryJP/ibet-SmartContract "$VENDOR/ibet-SmartContract"
cd "$VENDOR/ibet-SmartContract"
git checkout -q "$IBET_COMMIT"
UV_MALWARE_CHECK=1 uv sync --frozen --no-install-project
npm install --no-audit --no-fund
uv run ape pm install
uv run ape compile
mkdir -p tests/study
cp "$WS"/labs/lab-a-ibet/*.py tests/study/

step "4. ERC-3643 (Lab B)"
cd "$WS"
[ -d "$VENDOR/ERC-3643" ] || git clone https://github.com/ERC-3643/ERC-3643 "$VENDOR/ERC-3643"
cd "$VENDOR/ERC-3643"
git checkout -q "$ERC_COMMIT"
npm install --no-audit --no-fund     # 저장소 README의 npm ci는 잠금 파일 불일치로 거부된다
npx hardhat compile
mkdir -p test/study
cp "$WS"/labs/lab-b-erc3643/*.test.ts test/study/

step "끝"
echo "준비 완료. 터미널에서 bash run.sh 로 실습을 시작한다."
