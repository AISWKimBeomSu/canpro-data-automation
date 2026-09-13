# CAN-Pro 식이데이터 입력 자동화 파이프라인

> 연구실의 반복적인 **식이 데이터 전처리·입력** 업무를 Python·Playwright로 자동화한 프로젝트.
> 제각각인 비정형 원물 데이터를 규칙대로 정제하고, **수집 → 정제 → 입력**을 하나의 파이프라인으로 묶어
> 사람은 **검수만** 하도록 다시 설계했습니다.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?logo=playwright&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 배경

연세대학교 심리학부의 **장내미생물–정서 웰빙 종단 연구**에서, 참가자의 **24시간 식이회상 데이터**를
‘섭취 자료 코딩 규칙’에 맞춰 정제하고 한국영양학회 영양분석 프로그램 **CAN-Pro**에 입력하는
연구보조원(RA)으로 참여했습니다(약 9개월).

**문제는 “반복”이었습니다.** 입력자마다 원물(설문) 데이터의 포맷이 제각각이고, 같은 음식도 표기가 흔들리며,
입력해야 할 양은 수천 건. 기존 흐름은 `수집 → 정제 → 입력 → 수정 → 점검`이 **전부 수작업**이었습니다.

> ⚠️ 이 저장소에는 **코드만** 포함됩니다. 참가자 개인정보·원물·로그 등 모든 데이터는 `.gitignore`로 제외했습니다.

---

## 핵심 요약

| 지표 | 값 |
|---|---|
| 자동화한 단계 | **수집 · 정제 · 입력** (5단계 중 3단계) |
| 처리 참가자 | **100명 이상** |
| 음식–코드 매핑 사전 | **1,600종 이상** (누적·재사용) |
| 입력 후 재검증 일치율 | **100%** |

---

## 파이프라인

```mermaid
flowchart LR
    subgraph AUTO["자동화 · AI 파이프라인"]
        direction LR
        A["01 수집<br/>식품 DB 확보"] --> B["02 정제<br/>규칙 기반 매핑"] --> C["03 입력<br/>브라우저 자동 기입"]
    end
    subgraph HUMAN["사람 · RA 검수"]
        direction LR
        D["04 수정<br/>예외·개별 보정"] --> E["05 점검<br/>최종 확인"]
    end
    C -->|hand-off| D
```

**기존:** 다섯 단계 전부 수작업 → **개선:** 판단이 필요 없는 앞 세 단계를 자동화, 사람은 예외·검수에만 집중.

### 데이터가 흐르는 방식

1. **식품 DB → 코드 사전** — 공개된 CAN-Pro 식품 DB(약 2,988종)를 수집·정규화해
   `음식명 → 식품코드` 매핑 사전(`foodmap.py`)으로 구축. 배치마다 신규 음식을 규칙에 맞게 판정·누적해 재사용 자산으로 성장.
2. **규칙 기반 전처리** (`build_mapping.py`) — 참가자별로 다른 원물을 `pandas`·정규식으로 표준화:
   날짜/끼니 통일, 미섭취·비식품(물·보충제 등) 제외, 음식명 오타 보정 후 코드 매핑, **DB 실존 검증**.
3. **브라우저 자동 입력** (`run_input.py` + `engine.py`) — **Playwright**로 로그인된 CAN-Pro 웹앱(AngularJS)에
   CDP로 붙어 사용자·조회일·끼니를 선택하고 데이터를 순서대로 입력.
4. **입력 후 재검증** (`verify.py`) — 넣은 데이터를 **다시 조회해 원본과 대조**하고 날짜 반영을 확인해 오입력을 차단.
   이미 들어간 항목은 자동으로 건너뛰어(**멱등성**) 재실행에도 안전.

---

## 핵심 설계 결정

- **이름이 아니라 ‘코드’로 검색** — 표기가 흔들리는 음식명 대신 DB 식품번호를 6자리 코드(`zfill(6)`)로 변환해
  검색하면 결과가 **정확히 1건** → 퍼지 매칭 오류를 원천 차단.
- **날짜 오입력 방지 장치** — 조회일이 실제 반영됐는지 검증하고, 실패하면 즉시 중단(`DateSetError`).
- **누적되는 매핑 자산** — 배치가 쌓일수록 사전이 커져 신규 음식이 줄고 속도가 붙는 구조.
- **Human-in-the-loop** — 완전 자동화를 고집하지 않고, 판단이 필요한 수정·검수만 사람 몫으로 설계.

---

## 프로젝트 구조

```
canpro-data-automation/
├── src/
│   ├── lib.py             # CDP로 떠있는 크롬에 연결
│   ├── engine.py          # 입력 엔진: 그룹/사용자/날짜/끼니 선택, 코드검색·add_food, 날짜 검증
│   ├── foodmap.py         # 음식명 → 식품코드 매핑 사전(1,600+종) + 날짜/끼니 정규화 헬퍼
│   ├── build_mapping.py   # 원물(raw) → 규칙 정제 → mapped 산출 + DB 실존 검증
│   ├── candidates.py      # 신규 음식에 대한 DB 후보 추천(rapidfuzz + 부분일치)
│   ├── run_input.py       # 배치 자동입력 (기존/중복 skip, 세션·날짜 안전장치)
│   ├── verify.py          # 입력분 재조회 → 원본 대조 검증
│   └── register_users.py  # 사용자 기본정보 등록 자동화
├── data/                  # (개인정보 — 저장소 미포함, data/README.md 참고)
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 실행 방법

```bash
# 1) 의존성 설치
pip install -r requirements.txt
python -m playwright install chromium

# 2) 자동화용 크롬을 디버그 포트로 실행 (별도 프로필)
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir="./chrome-profile"
#   → 뜬 브라우저에서 CAN-Pro에 로그인

# 3) 데이터 준비 (data/README.md 참고) 후
python src/build_mapping.py     # 원물 정제 → data/mapped_rows.tsv
python src/run_input.py         # 자동 입력
python src/verify.py            # 재조회 검증
```

> 코드 상단의 `GROUP`(연구 그룹명), `data/` 경로 등은 사용 환경에 맞게 설정하세요.

---

## 개인정보 처리

- 참가자 식별자는 **가명 코드**로 다루고, 개인정보는 데이터 3법에 저촉되지 않도록 마스킹·비식별 처리 후에만 다룹니다.
- 원물 데이터·매핑 결과·사용자 정보·로그·브라우저 프로필은 **전부 `.gitignore`로 제외**되어 저장소에 포함되지 않습니다.
- 자동화 대상은 어디까지나 **규칙화된 반복 작업**이며, 민감한 판단과 최종 책임은 사람(RA)에게 남겼습니다.

---

## 기술 스택

`Python` · `pandas` · `정규식` · `Playwright` · `CDP` · `rapidfuzz`

**역량:** 데이터 전처리·표준화 · 업무 자동화(AX) · 규칙 설계 · 품질 검증 자동화 · 재현 가능한 파이프라인

---

## License

MIT © 2026 AISWKimBeomSu
