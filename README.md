# Security Token Lab

[![tests](https://github.com/loopzeromin/security-token-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/loopzeromin/security-token-lab/actions/workflows/tests.yml)

토큰증권(STO) 16회차 스터디와 심화 5회차(17–21)의 실습 저장소다. 교육용 파이썬 모형, 실제 오픈소스 계약(일본 ibet-SmartContract, 미국·유럽 ERC-3643) 테스트, 공개 데이터 분석이 들어 있다. 슬라이드와 문제집에 나오는 숫자는 모두 이 저장소의 코드로 다시 만들 수 있다.

## 시작하기

**브라우저에서 (설치 없음, 권장)**

1. GitHub에 로그인한다. 학생이면 [GitHub Education](https://education.github.com/) 인증을 받아 두면 무료 사용 시간이 늘어난다.
2. 위쪽 초록색 **Code** 버튼 → **Codespaces** → **Create codespace on main**.
3. VS Code가 열리고 설치가 자동으로 돈다(10분 안팎). 끝나면 터미널에 `준비 완료`가 보인다.
4. `bash run.sh all`을 친다. `PASS`, `passed`, `passing`만 보이면 된다. 설치가 덜 끝났으면 Lab A·B는 `SKIP`으로 건너뛰고 나머지는 돈다. 원본 테스트(ibet 3 passed, ERC-3643 31 passing)가 먼저 돌고, 실습 테스트(6 passed, 5 passing)가 뒤따른다.

**내 컴퓨터에서 (파이썬 실습만)**

```
git clone https://github.com/loopzeromin/security-token-lab
cd security-token-lab
python3 -m pip install -r requirements.txt
bash run.sh part1
bash run.sh test
```

Lab A·B(실제 계약)는 Foundry·Node 22 등이 필요해 Codespaces를 권한다. 직접 설치하려면 `.devcontainer/setup.sh`의 순서를 따른다.

## 회차별 지도

| 회차 | 주제 | 파일 | 명령 | 문제집 |
|---|---|---|---|---|
| 1 | 증권 명부와 결제 | `labs/part1/s01_settlement_netting.py` | `bash run.sh part1` | 1.1–1.4 |
| 2 | 해시로 이은 장부 | `labs/part1/s02_hash_ledger.py` | 〃 | 2.1–2.5 |
| 3 | 스마트 계약과 ERC-20 | `labs/part1/s03_erc20_model.py` | 〃 | 3.1–3.4 |
| 4 | 세 질문: 자격·통제·결제 | `labs/part1/s04_security_token_model.py` | 〃 | 4.1–4.4 |
| 5 | 일본: ibet for Fin | `labs/part1/s05_ibet_port.py` | 〃 | 5.1–5.4 |
| 6 | 미국: BUIDL과 ERC-3643 | `labs/part1/s06_erc3643_port.py` | 〃 | 6.1–6.5 |
| 7 | 한국: 조각투자에서 법제화까지 | (코드 없음) | | 7.1–7.3 |
| 8 | 중간 점검 | 1–7회차 해설 `sol_basics.py`, `sol_markets.py`; 설치 확인 | `bash run.sh part1`, `bash run.sh check` | 8.1–8.2 |
| 9 | 실제 코드 실행과 예측 대조 | `labs/lab-a-ibet/`, `labs/lab-b-erc3643/` | `bash run.sh a`, `bash run.sh b`, 해설 `bash run.sh sol` | 9.1–9.3 |
| 10 | DVP와 결제 지연 위험 | `labs/lab-c-settlement/settlement_risk.py`, `notebooks/01_결제지연위험.ipynb` | `bash run.sh c` | 10.1–10.4 |
| 11 | 대금은 어디에: 체인 위의 돈 | `labs/part1/s11_atomic_dvp.py` | `bash run.sh part1` | 11.1–11.4 |
| 12 | 운영 위험과 권한 | `labs/part1/s12_ops_risk.py` | 〃 | 12.1–12.4 |
| 13 | 유통시장과 유동성 | `labs/part1/s13_liquidity_sim.py`, `notebooks/02_유동성.ipynb` | 〃 | 13.1–13.4 |
| 14 | 실증: BUIDL 기록과 일본 공모 ST | `labs/data-lab/`, `notebooks/03_일본공모ST.ipynb` | `bash run.sh data`, `bash run.sh japan` | 14.1–14.3 |
| 15 | 완성 사례: 한국형 부동산 토큰증권 | `labs/part1/s15_capstone_model.py` | `bash run.sh design` | 15.1–15.4 |
| 16 | 종합 정리 | 전부 | `bash run.sh test` | 16.1–16.2 |
| 17 (심화) | 가치평가·회계·세무 | `labs/advanced/s17_valuation.py` | `bash run.sh adv` | 17.1–17.3 |
| 18 (심화) | 은행 자본: 바젤 암호자산 기준 | `labs/advanced/s18_basel_capital.py` | 〃 | 18.1–18.3 |
| 19 (심화) | 스테이블코인·예금토큰 | `labs/advanced/s19_stablecoin_run.py` | 〃 | 19.1–19.3 |
| 20 (심화) | 토큰화 MMF와 담보 | `labs/advanced/s20_collateral.py` | 〃 | 20.1–20.3 |
| 21 (심화) | 한국 증권사의 토큰증권 실무 | `labs/advanced/s21_sto_business.py` | 〃 | 21.1–21.4 |

10–13회차 과제 해설은 `labs/part1/sol_advanced.py`, 14회차 해설은 `labs/data-lab/sol_data.py`, 17–21회차 해설은 `labs/advanced/sol_deep.py`다.

## 폴더

```
labs/
  part1/              1–6, 11–13, 15회차 교육용 모형과 해설 (파이썬)
  lab-a-ibet/         9회차: ibet-SmartContract 원본에 붙이는 테스트 (Ape)
  lab-b-erc3643/      9회차: ERC-3643 원본에 붙이는 테스트 (Hardhat)
  lab-c-settlement/   10회차: 결제 지연 기대손실 (닫힌 해 + 몬테카를로)
  data-lab/           14회차: BUIDL 이더리움 기록 수집·검산·분석, 일본 공모 ST 목록
  advanced/           17–21회차 심화: DCF·Longstaff, 바젤 SCO60, 스테이블코인 런, 담보 헤어컷, 분산원장 요건·증권사 손익
notebooks/            그림으로 보는 10·13·14회차 (출력 포함, _build.py로 다시 생성)
tests/                교재 숫자 회귀 테스트와 문제집 계산 검산 (pytest)
vendor/               설치 때 내려받는 원본 저장소 (커밋 고정, 저장소에는 없음)
run.sh                모든 실습의 진입점
```

## 숫자 검증

`bash run.sh test`(또는 `python3 -m pytest`)는 두 가지를 확인한다.

- `tests/test_labs.py`: 실습 스크립트를 실제로 돌려 슬라이드가 인용한 출력이 그대로 나오는지. 예: 차감 결제 6.1%, T+2 기대손실 4,511.7원, 15회차 시나리오 15/15, 일본 공모 ST 94건·중앙값 22.3억 엔.
- `tests/test_workbook.py`: 문제집 계산 문제의 답을 다시 계산.

스크립트를 고쳐서 테스트가 깨지면 교재 숫자도 같이 고쳐야 한다는 뜻이다. GitHub에 올릴 때마다 Actions가 같은 테스트를 돌린다. 시뮬레이션 세 개(`s13`, `s15`, `sol_advanced`)는 `slow` 표시가 있어 `pytest -m "not slow"`로 뺄 수 있다.

교재가 인용한 원본 줄 번호는 ibet 커밋 `8092b7c`, ERC-3643 커밋 `2f0704d`(v4.1.3) 기준이다.

## 검증 상태 (2026년 10월)

- part1 모든 스크립트·해설, Lab C, 일본 분석, 심화 17–21: 실행해서 출력 확인, 테스트 44개 통과(Python 3.13).
- 2026-11-03 Codespaces에서 `bash run.sh all` 재확인: 파이썬 19개 PASS, Lab C 출력 일치, 원본 테스트 ibet 3 passed·ERC-3643 31 passing, Lab A 6 passed, Lab B 5 passing. `bash run.sh sol`: 9회차 해설 1 passed·2 passing.
- Lab A: 실습 테스트 6개 통과, 해설 테스트 `test_solution_cancel.py` 1개 통과.
- Lab B: 원본 테스트 31개, 실습 테스트 5개, 해설 테스트 `solution-country.test.ts` 2개 통과.
- data-lab: 2024년 3월–2026년 10월 BUIDL Transfer를 두 번 받아 금액 0 기록을 빼면 17,149건으로 일치. 공개 노드는 넓은 구간 조회를 거부하므로 탐색기 API(Blockscout, Routescan)를 쓴다.

## 사용 시간 아끼기

- 실습이 끝나면 왼쪽 아래 **Codespaces** → **Stop Current Codespace**. 켜 둔 시간만큼 무료 사용량이 준다.
- 30분 동안 아무것도 안 하면 자동으로 멈춘다. 다음에는 [github.com/codespaces](https://github.com/codespaces)에서 같은 codespace를 다시 연다.

## 안 될 때

- `Lab A·B는 설치가 끝나야`가 나오면: 설치가 끝날 때까지 기다린다. 터미널은 먼저 열리고 설치는 뒤에서 계속 돈다.
- 설치 중 오류: `.devcontainer/setup.log`에 전체 기록이 남는다. 이 파일을 그대로 공유한다.
- 설치를 처음부터 다시: `bash .devcontainer/setup.sh`. 단, 자동 설치가 아직 도는 중에 다시 실행하면 두 설치가 같은 폴더를 건드려 `npm error ENOTEMPTY`가 난다. `tail -f .devcontainer/setup.log`로 끝났는지 먼저 본다.
- Lab B를 직접 설치할 때 README의 `npm ci`는 잠금 파일 불일치로 거부된다. `npm install`을 쓴다. Hardhat 2.x(잠금 파일 2.24.2)는 Node 26에서 HH502가 나므로 Node 22로 돌린다.
- 노트북 그림의 한글이 네모로 보이면 한글 글꼴(Noto Sans CJK KR, 맥은 AppleGothic)이 없는 것이다.
- zsh에 명령을 붙여 넣을 때 줄 끝의 `# 주석`은 지운다(`unknown file attribute` 오류).

## 출처와 라이선스

- [BoostryJP/ibet-SmartContract](https://github.com/BoostryJP/ibet-SmartContract): Apache-2.0
- [ERC-3643/ERC-3643](https://github.com/ERC-3643/ERC-3643): GPL-3.0. `labs/lab-b-erc3643/`의 테스트는 이 저장소의 테스트 구조와 fixture를 따른다.
- 원본 저장소는 설치 때 내려받을 뿐 이 저장소에 포함하지 않는다.
- 일본 공모 ST 목록: BOOSTRY 공개 대시보드(2026-10-28 열람). START 취급 종목: ODX 공식 신규 취급 종목 페이지(2026-10-28 확인).
- BUIDL 기록: 이더리움 공개 기록(BUIDL 계약 Transfer 이벤트), Blockscout·Routescan API.
