# part1 — 1~6, 11~13, 15회차 파이썬 실습

| 파일 | 회차 | 필요한 것 |
|---|---|---|
| s01_settlement_netting.py | 1 | 표준 라이브러리 |
| s02_hash_ledger.py | 2 | 표준 라이브러리 |
| s03_erc20_model.py | 3 | 표준 라이브러리 |
| s04_security_token_model.py | 4 | s03 파일이 같은 폴더에 |
| s05_ibet_port.py | 5 | s03 파일이 같은 폴더에 |
| s06_erc3643_port.py | 6 | `pip install cryptography`, s03 파일 |
| s11_atomic_dvp.py | 11 | s03, s04 파일 |
| s12_ops_risk.py | 12 | s03 파일 |
| s13_liquidity_sim.py | 13 | numpy (실행 약 15초) |
| s15_capstone_model.py | 15 | numpy (실행 약 10초) |
| sol_basics.py | 1–4 과제 해설 | s01–s04 파일 |
| sol_markets.py | 5·6·7 과제 해설 | cryptography, s03·s05·s06 파일 |
| sol_advanced.py | 10–13 과제 해설 | numpy, s03·s11·s12 파일 (약 20초) |

실행: 이 폴더에서 `python3 s01_settlement_netting.py`처럼 하나씩 돌린다. 모든 파일은 2026년 10월 27일 Python 3.13에서 실행해 출력을 확인했다.
s05·s06은 원본 저장소(ibet-SmartContract 8092b7c, ERC-3643 v4.1.3)의 검사 순서와 실패 메시지를 옮긴 모형이다. 9회차에 실제 체인 결과와 대조한다. sol_*.py는 과제 해설이다. 출력 숫자는 저장소 맨 위의 `tests/test_labs.py`가 매번 확인한다.
