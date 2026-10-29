"""노트북 세 개를 만든다. 실행: python _build.py && jupyter nbconvert --to notebook --execute --inplace *.ipynb"""
import nbformat as nbf

SETUP = r'''import sys, pathlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
LABS = pathlib.Path.cwd().parent / "labs"
for f in ["Noto Sans CJK KR", "AppleGothic", "Malgun Gothic", "NanumGothic"]:
    if any(f == x.name for x in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = f; break
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 110,
                     "axes.unicode_minus": False})
ACC, GREY = "#2F5D8C", "#8E8C87"'''

def nb(cells):
    n = nbf.v4.new_notebook()
    n.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    n.cells = [nbf.v4.new_markdown_cell(c[1]) if c[0] == "md" else nbf.v4.new_code_cell(c[1]) for c in cells]
    return n

# ---------------------------------------------------------------- 01
c1 = [
("md", "# 결제 지연 위험 (10회차)\n\n식 (10.1) $\\mathbb{E}[\\text{손실}](L)=(1-e^{-hL})\\,N\\sigma\\sqrt L/\\sqrt{2\\pi}$를 Lab C 코드로 다시 계산하고, 몬테카를로·탄력성·두꺼운 꼬리를 그림으로 본다. 가정은 Lab C와 같다: $N=10$억 원, $\\sigma=1\\%$/일, $h=0.10/250$."),
("code", SETUP + "\nsys.path.insert(0, str(LABS / 'lab-c-settlement'))\nimport settlement_risk as lc\nprint(lc.SIGMA, lc.H, lc.NOTIONAL)"),
("md", "## 1. 닫힌 해와 몬테카를로\n\n`closed_form`은 식 (10.1)을 그대로 옮긴 함수다. 같은 가정으로 부도 여부와 가격 변동을 직접 뽑아 평균을 내면(시드 고정) 같은 값 근처가 나와야 한다."),
("code", """rng = np.random.default_rng(20261028)
rows = []
for L in [2, 1, 0.5, 1/24]:
    cf = lc.closed_form(L) * lc.NOTIONAL
    mc, se = lc.monte_carlo(L, rng)
    rows.append((L, cf, mc * lc.NOTIONAL, se * lc.NOTIONAL))
    print(f"L={L:6.3f}일  닫힌 해 {cf:9.1f}원   MC {mc*lc.NOTIONAL:9.1f}원 (표준오차 {se*lc.NOTIONAL:.1f})")"""),
("md", "## 2. 곡선: $L^{1.5}$\n\n로그 축에서 기울기 1.5인 직선이 된다. T+2 → T+1이 $2^{1.5}\\approx2.83$배인 이유다."),
("code", """L = np.logspace(np.log10(1/48), np.log10(5), 200)
E = np.array([lc.closed_form(x) for x in L]) * lc.NOTIONAL
fig, ax = plt.subplots(figsize=(6.4, 3.6))
ax.loglog(L, E, color=ACC)
for x, lab in [(2, "T+2"), (1, "T+1"), (0.5, "반나절"), (1/24, "1시간")]:
    y = lc.closed_form(x) * lc.NOTIONAL
    ax.plot(x, y, "o", color=ACC); ax.annotate(f"{lab}\\n{y:,.1f}원", (x, y), textcoords="offset points", xytext=(6, -14), fontsize=8)
ax.set_xlabel("결제 지연 L (영업일, 로그)"); ax.set_ylabel("기대 대체비용 (원, 로그)")
ax.set_title("10억 원 한 건의 기대 대체비용", fontsize=10); plt.tight_layout()"""),
("md", "## 3. 탄력성 $\\varepsilon = x/(e^x-1)+1/2$\n\n$x=hL$이 작으면 1.5, 부도 확률이 커지면 0.5 쪽으로 내려간다(문제집 10.2)."),
("code", """x = np.logspace(-4, 1.3, 200)
eps = x / np.expm1(x) + 0.5
fig, ax = plt.subplots(figsize=(6.4, 3.2))
ax.semilogx(x, eps, color=ACC); ax.axhline(1.5, color=GREY, lw=.6, ls="--"); ax.axhline(0.5, color=GREY, lw=.6, ls="--")
ax.plot(lc.H, 0.5 + lc.H/np.expm1(lc.H), "o", color=ACC); ax.annotate("Lab C 가정 (x=0.0004)", (lc.H, 1.5), xytext=(4, -16), textcoords="offset points", fontsize=8)
ax.set_xlabel("x = hL"); ax.set_ylabel("탄력성 ε"); plt.tight_layout()
print("x=1일 때 ε =", round(1/np.expm1(1) + 0.5, 3))"""),
("md", "## 4. 꼬리가 두꺼우면\n\n분산을 1로 맞춘 $t_3$와 정규분포. 양의 부분의 평균은 $t_3$가 더 작지만(0.318 대 0.399), 99% 분위수는 더 크다(2.62 대 2.33)."),
("code", """rng = np.random.default_rng(7)
z = rng.standard_normal(2_000_000)
t = rng.standard_t(3, 2_000_000) / np.sqrt(3)
for name, s in [("정규", z), ("t3 (분산 1)", t)]:
    print(f"{name:10s}  E[X+] = {np.maximum(s, 0).mean():.3f}   99% 분위수 = {np.quantile(s, .99):.2f}")
print("이론값: 1/sqrt(2π) =", round(1/np.sqrt(2*np.pi), 3), ", 1/π =", round(1/np.pi, 3), ", 4.541/sqrt(3) =", round(4.541/np.sqrt(3), 2))"""),
("md", "**읽을 것.** 기대손실만 보면 꼬리가 두꺼운 상품이 더 안전해 보인다. 결제 방식을 고를 때는 분위수(한 번의 큰 손실)를 함께 봐야 한다.\n\n출처: Lab C `settlement_risk.py`; Duffie and Singleton (2003) *Credit Risk*; Mandelbrot (1963)."),
]

# ---------------------------------------------------------------- 02
c2 = [
("md", "# 유동성: 식과 시뮬레이션 (13회차)\n\n자격 비율 $q$와 연간 순매수 한도가 체결률을 얼마나 줄이는지, 식 (13.1)·(13.2)와 `s13_liquidity_sim.py`의 시뮬레이션을 같은 그림에 놓는다. 모형의 숫자는 가정($N=5{,}000$, $M=20$, $B=5\\%$, 1회 2천만 원)에서 나온 것이고 실제 시장으로 보정하지 않았다."),
("code", SETUP + "\nsys.path.insert(0, str(LABS / 'part1'))\nimport s13_liquidity_sim as s13\nprint(s13.N, s13.M, s13.B, s13.LOT, s13.LIMIT)"),
("md", "## 1. 식 (13.1): 한도가 없을 때\n\n하루에 적어도 한 명의 자격·의향 있는 후보를 만날 확률 $p=1-(1-qB)^M$, 21번(0–20일) 안에 체결될 확률 $1-(1-p)^{21}$."),
("code", """qs = np.array([1.0, 0.5, 0.2, 0.1, 0.05])
p = 1 - (1 - qs * s13.B) ** s13.M
fill_formula = 1 - (1 - p) ** 21
cap = np.minimum(1, (s13.LIMIT // s13.LOT) * qs * s13.N / (s13.SELLERS_PER_DAY * s13.PERIODS))
for q, a, b in zip(qs, fill_formula, cap):
    print(f"q={q:4.2f}  식(13.1) {a:6.1%}   한도 상한(13.2) {b:6.1%}")"""),
("md", "## 2. 시뮬레이션\n\n`s13.simulate`를 그대로 부른다(시드 고정, 1–2분). 한도가 있는 경우는 식 (13.2)의 상한에 붙는다."),
("code", """sim = [(q, *s13.simulate(q, False), *s13.simulate(q, True)) for q in qs]
for q, f0, w0, f1, w1 in sim:
    print(f"q={q:4.2f}  한도 없음 {f0:6.1%} (평균 대기 {w0:4.2f}일)   1억 한도 {f1:6.1%} (평균 대기 {w1:4.2f}일)")"""),
("code", """fig, ax = plt.subplots(figsize=(6.4, 3.8))
ax.plot(qs, fill_formula * 100, "--", color=GREY, label="식 (13.1) 한도 없음")
ax.plot(qs, cap * 100, ":", color=ACC, label="식 (13.2) 한도 상한")
ax.plot(qs, [r[1] * 100 for r in sim], "o-", color=GREY, label="시뮬레이션 한도 없음")
ax.plot(qs, [r[3] * 100 for r in sim], "s-", color=ACC, label="시뮬레이션 1억 한도")
ax.set_xscale("log"); ax.set_xticks(qs); ax.set_xticklabels([str(q) for q in qs])
ax.set_xlabel("자격 비율 q (로그)"); ax.set_ylabel("1년 체결률 (%)"); ax.legend(fontsize=8, frameon=False)
plt.tight_layout()"""),
("md", "## 3. 한도를 바꾸면\n\n상한 식에서 한도만 바꿔 본다(문제집 13.2). 한도가 2억이면 $q=0.2$의 상한이 1에 닿아, 그때부터는 탐색 마찰이 체결률을 정한다."),
("code", """for limit in [1e8, 2e8, 3e8]:
    lots = int(limit // s13.LOT)
    c = np.minimum(1, lots * qs * s13.N / (s13.SELLERS_PER_DAY * s13.PERIODS))
    print(f"한도 {limit/1e8:.0f}억 (1인 연 {lots}건): " + ", ".join(f"q={q}: {x:.0%}" for q, x in zip(qs, c)))"""),
("md", "출처: `labs/part1/s13_liquidity_sim.py`; Duffie, Gârleanu and Pedersen (2005); 금융위원회 시행령 입법예고(2026-10-01)의 장외거래소별 일반투자자 연간 순매수 1억 원."),
]

# ---------------------------------------------------------------- 03
c3 = [
("md", "# 일본 공모 ST 94건 (5·14회차)\n\n`labs/data-lab/japan_st_offerings.tsv`(BOOSTRY 공모 ST 목록, 2021-04-27 ~ 2026-10-27)와 `start_listings.tsv`(ODX START 취급 종목)를 읽어 슬라이드의 숫자를 다시 만든다. 금액 단위는 백만 엔."),
("code", SETUP + """\nimport csv
from collections import Counter, defaultdict
rows = list(csv.DictReader(open(LABS / "data-lab" / "japan_st_offerings.tsv", encoding="utf-8"), delimiter="\\t"))
amt = np.array([float(r["amount_mn_jpy"]) for r in rows])
print(len(rows), "건, 합계", round(amt.sum()/100, 1), "억 엔")
print("평균", round(amt.mean()/100, 1), "억 엔 / 중앙값", round(np.median(amt)/100, 1), "억 엔 / 최대", round(amt.max()/100, 1), "억 엔")"""),
("md", "## 1. 회계연도별 발행\n\n일본 회계연도는 4월에 시작한다. FY2026은 10월 27일까지다."),
("code", """def fy(d):
    y, m = int(d[:4]), int(d[5:7]); return y if m >= 4 else y - 1
by = defaultdict(float)
for r, a in zip(rows, amt): by[fy(r["issue_date"])] += a
ys = sorted(by); vals = [by[y]/100 for y in ys]
fig, ax = plt.subplots(figsize=(6.4, 3.4))
bars = ax.bar([f"FY{str(y)[2:]}" for y in ys], vals, color=[GREY]*(len(ys)-1) + [ACC])
ax.bar_label(bars, fmt="%.0f", fontsize=8); ax.set_ylabel("발행액 (억 엔)")
ax.set_title("회계연도별 공모 ST 발행액", fontsize=10); plt.tight_layout()"""),
("md", "## 2. 플랫폼 집중\n\n발행액 기준 플랫폼 비중과 HHI. 두 플랫폼(Progmat, ibet for Fin)이 96%다."),
("code", """plat = defaultdict(float)
for r, a in zip(rows, amt): plat[r["platform"]] += a
tot = sum(plat.values())
share = sorted(((k, v/tot) for k, v in plat.items()), key=lambda x: -x[1])
for k, s in share: print(f"{k:16s} {s:6.1%}")
hhi = sum((100*s)**2 for _, s in share)
print("HHI", round(hhi), " 등가 플랫폼 수", round(1e4/hhi, 2))"""),
("md", "## 3. 크기 분포\n\n평균이 중앙값의 두 배 가까이 된다. 오른쪽으로 긴 꼬리다(문제집 5.2)."),
("code", """fig, ax = plt.subplots(figsize=(6.4, 3.2))
ax.hist(amt/100, bins=np.arange(0, 330, 10), color=GREY)
ax.axvline(np.median(amt)/100, color=ACC, lw=1.2); ax.axvline(amt.mean()/100, color=ACC, lw=1.2, ls="--")
ax.text(np.median(amt)/100 + 2, ax.get_ylim()[1]*.9, "중앙값", color=ACC, fontsize=8)
ax.text(amt.mean()/100 + 2, ax.get_ylim()[1]*.8, "평균", color=ACC, fontsize=8)
ax.set_xlabel("1건 발행액 (억 엔)"); ax.set_ylabel("건수"); plt.tight_layout()"""),
("md", "## 4. 2차 시장: START\n\n94건 중 START에서 거래되는 것은 10건이다. 발행일부터 거래 시작일까지의 기간(일)도 본다."),
("code", """from datetime import date
st = list(csv.DictReader(open(LABS / "data-lab" / "start_listings.tsv", encoding="utf-8"), delimiter="\\t"))
later = [x for x in st if x["start_date"] > "2026-10-28"]
print(len(st), "건 START 목록, 그중", len(later), "건은 2026-10-28 이후 시작 예정")
listed = [r for r in rows if r["start"].strip() in ("〇", "◯")]
print("목록에서 START 표시:", len(listed), "건, 발행액", round(sum(float(r['amount_mn_jpy']) for r in listed)/100, 1), "억 엔")
for s in st[:12]: print(s["start_date"], s["short_name"], s["platform"])"""),
("md", "출처: BOOSTRY 일본 시큐리티 토큰 시장 대시보드(2026-10-28 열람), ODX START 신규 취급 종목 페이지(2026-10-28 확인). 집계 코드는 `labs/data-lab/analyze_japan.py`와 같다."),
]

for name, cells in [("01_결제지연위험.ipynb", c1), ("02_유동성.ipynb", c2), ("03_일본공모ST.ipynb", c3)]:
    nbf.write(nb(cells), name)
print("ok")
