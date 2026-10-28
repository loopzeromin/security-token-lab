# Security Token Lab

토큰증권(STO) 16회차 스터디의 실습 저장소다. 설치 없이 브라우저에서 바로 실습할 수 있도록 GitHub Codespaces 환경을 같이 넣었다.

## 시작하기 (처음 한 번)

1. GitHub에 로그인한다. 학생이면 [GitHub Education](https://education.github.com/)에서 학생 인증을 받아 두면 무료 사용 시간이 늘어난다.
2. 이 저장소 위쪽의 초록색 **Code** 버튼 → **Codespaces** 탭 → **Create codespace on main**을 누른다.
3. 브라우저에 VS Code가 열리고, 아래 터미널에서 설치가 자동으로 진행된다. **10분 안팎** 걸린다. 끝나면 `준비 완료`가 보인다.
4. 터미널에 아래를 입력한다.

```
bash run.sh all
```

`PASS`와 `passed`, `passing`만 보이면 준비가 끝난 것이다. 2026년 10월 28일 Codespaces(2코어)에서 전체가 통과하는 것을 확인했다. Lab B 아래에 나오는 큰 표는 함수별 가스(수수료) 사용량으로, 오류가 아니다.

## 회차별 실행

| 명령 | 회차 | 내용 |
|---|---|---|
| `bash run.sh part1` | 1–6, 11–13 | 파이썬 모형과 과제 해설 |
| `bash run.sh a` | 9 | ibet-SmartContract(일본, BOOSTRY) 실제 계약 테스트 |
| `bash run.sh b` | 9 | ERC-3643(미국·유럽 기관용 표준) 실제 계약 테스트 |
| `bash run.sh c` | 10 | 결제 지연 위험 모형 |
| `bash run.sh data` | 14 | 이더리움에서 BUIDL 거래 기록을 받아 분석 (몇 분) |

실습 파일은 `labs/` 폴더에 있고, 원본 오픈소스는 `vendor/` 폴더에 내려받아진다. 교재가 인용한 줄 번호는 ibet 커밋 `8092b7c`, ERC-3643 커밋 `2f0704d`(v4.1.3) 기준이다.

## 사용 시간 아끼기

- 실습이 끝나면 왼쪽 아래 **Codespaces** 표시를 눌러 **Stop Current Codespace**를 누른다. 켜 둔 시간만큼 무료 사용량이 줄어든다.
- 아무것도 안 하면 30분 뒤 자동으로 멈춘다. 다음에는 [github.com/codespaces](https://github.com/codespaces)에서 같은 codespace를 다시 열면 된다. 처음처럼 오래 걸리지 않는다.

## 안 될 때

- `아직 설치 중이다`가 나오면: 설치가 끝날 때까지 기다린다. 터미널은 설치 중에도 열리지만 설치는 뒤에서 계속 돈다.
- 설치 중 오류: `.devcontainer/setup.log`에 전체 기록이 남는다. 이 파일을 그대로 공유한다.
- 설치를 처음부터 다시: 터미널에서 `bash .devcontainer/setup.sh`.

## 출처와 라이선스

- [BoostryJP/ibet-SmartContract](https://github.com/BoostryJP/ibet-SmartContract): Apache-2.0
- [ERC-3643/ERC-3643](https://github.com/ERC-3643/ERC-3643): GPL-3.0. `labs/lab-b-erc3643/`의 테스트는 이 저장소의 테스트 구조와 fixture를 따른다.
- 원본 저장소는 설치 때 내려받을 뿐 이 저장소에 포함하지 않는다.
