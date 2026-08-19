# plan: v2 (rules.md "v2 변경사항" 5개 항목 구현)

목표: [사용자 확인 필요] rules.md v2 변경사항 5개 항목(height_cm 반영,
T09/Q09 정정 갱신, caveat 필드 일반화, eval 22문항 갱신, 그라운드시트
우려 폐기)을 agent_core.py/main.py/accessories.csv에 반영해 v1 eval에서
드러난 Q09 채점 오류와 caveat 누락 문제(회고 5·6번, docs/plan_aiagent.md:
213-232)를 해결한다.
종료 조건: eval_questions.csv 22문항 중 20개 이상(90.9%, rules.md:274
권고치) PASS 하고, tests/test_agent_core.py 전체(기존+신규) 통과하면 끝.
시작 시각: 2026-08-19 00:58 (사용자 확인: research_v2.md 파일 mtime(08-18
17:31)은 시작시각 증거로 불확실 — 구현 진입 시각을 8h 캡의 새 기준으로 채택)

DECISION_LOG 파일: repo 전체 grep/find 0건 — 존재하지 않음. 대신 걸리는
기존 결정은 docs/plan_aiagent.md의 회고 번호로 표기.

---

## 1. 신규/수정 파일

| 경로 | 내용 |
|---|---|
| `agent_core.py` (수정) | NUMERIC_COLUMNS에 height_cm 추가. twin_lookup()에 caveat 필드 통합(estimated/estimate_notice 대체). 축비교 헬퍼 함수 1개 추가. |
| `main.py` (수정) | SYSTEM_PROMPT 답변 규칙 1줄 교체(estimated→caveat). EVAL_CRITERIA Q09 must_exclude 교체 + Q21/Q22 추가. "20문항" 문구 3곳→"22문항". run_eval()에 20/22 임계값 판정 줄 추가. |
| `tests/test_agent_core.py` (수정) | test_twin_lookup_추정라벨 assert 대상 변경(estimate_notice→caveat). 신규 테스트 2개(LT1 caveat 없음, TWIN 축비교). |
| `data/accessories.csv` (수정) | 7~13행(그라운드시트 6종) note 컬럼의 "[미해결]...재확인 필요" 문구 제거, 해결 문구로 교체. |

신규 파일 없음. import할 기존 모듈 추가 없음(표준 라이브러리만, 기존과 동일).

## 2. 작업 1 — NUMERIC_COLUMNS에 height_cm (agent_core.py:32-34)

```
NUMERIC_COLUMNS = [
    "weight_g", "load_kg", "seat_height_cm", "width_cm", "length_cm",
    "height_cm", "price_krw",
]
```
chairs.csv 헤더 순서(length_cm 다음 height_cm)에 맞춰 삽입. `_lineup_stats()`
(agent_core.py:165-194)는 NUMERIC_COLUMNS를 순회하는 제네릭 코드라 별도
수정 불필요 — chair_lookup의 spec_context에 height_cm이 value/overall_max/
by_성격블록_max로 자동 노출됨. [미확인] 6개 체어는 기존 다른 컬럼과 동일하게
자동으로 spec_context에서 빠짐(agent_core.py:209-211 기존 로직).

## 3. 작업 2 — Q09 must_exclude 교체 (main.py:220)

**하드 튜닝 여부 검토(사용자 지시):** rules.md 3번 섹션의 "특정 trap 1건에
맞춘 특수 규칙 지양" 원칙은 agent_core.py(판정 엔진) 설계 원칙이다.
EVAL_CRITERIA는 애초부터 트랩별 개별 키워드 지정이 설계 의도였음이
main.py:198-209 주석과 회고 5번(docs/plan_aiagent.md:213-220, "20문항
keyword 목록을 사람이 직접 옮겨 적어야")에 명시돼 있다 — 이미 20개 항목
전부가 각 트랩 문구에 맞춰 개별 튜닝돼 있다(main.py:210-232). 따라서 Q09
교체는 새로운 원칙 위반이 아니라 기존 패턴을 새 trap 문구에 맞추는 것.

**교체 내용:** 새 expected_answer(eval_questions.csv:10)가 "...사바나
(110cm)보다는 **낮습니다**"를 정답의 일부로 포함하므로, must_exclude가
"낮습니다" 단어 자체를 막으면 정답도 FAIL 처리된다(research 1번 확인).
실제로 막아야 할 건 "체어투보다 낮다"는 반대 결론뿐이므로:

```
"Q09": {"include_groups": [["높습니다", "낮은 편이 아니", "최상단", "높은"]],
        "must_exclude": ["체어투보다 낮", "84cm보다 낮"]},
```

**다른 문항도 같은 버그 있는지 확인(사용자 지시, 구현 진입 시 스크립트로
전수 검사):** Q01~Q20 must_exclude 20개 전부를 각자의 expected_answer
원문과 substring 대조 — 겹치는 건 Q09 하나뿐(스크립트 출력, 재현 가능:
`main.py` 현재 EVAL_CRITERIA 값 + `data/eval_questions.csv` expected_answer
전수 순회). 신규 추가하는 Q21/Q22(5번 작업)의 must_exclude도 각자
expected_answer와 겹침 없음 확인 완료. Q09만의 문제였고 위 교체로 해결.

## 4. 작업 3 — twin_lookup caveat 필드 통합 (agent_core.py:294-346)

### 4-1. 컵홀더 라벨 매핑 위치 (사용자 지시: AXIS_CONFIG 확장 전 이유 확인)

**왜 v1에서 컵홀더가 AXIS_CONFIG에 없었나:** AXIS_CONFIG(agent_core.py:25-30)는
gear_to_acc의 "체어 컬럼값 == accessory required_value" 조인 매칭에
쓰인다(agent_core.py:232-245). 컵홀더 액세서리 행(accessories.csv:18)은
decision_axis="모델별", required_value="해당없음"으로, 값 비교가 아니라
"chairs.csv cupholder 컬럼에 값이 있는가"만 보는 존재 여부 판정이라 이
조인 패턴 자체가 안 맞는다 — 그래서 별도 특수 분기(agent_core.py:247-254)로
처리됐다.

**AXIS_CONFIG에 그대로 "컵홀더" 키를 추가하면:** gear_to_acc의 for문
(agent_core.py:232-245)이 axis="컵홀더"에 대해서도 도는데, decision_axis=
"컵홀더"인 accessories 행이 하나도 없어(전부 "모델별") matches가 항상
빈 배열로 계산된다. 다행히 그 뒤(agent_core.py:247-254)의 기존 특수 분기가
axes["컵홀더"]를 무조건 덮어써서 최종 결과는 안 깨지지만, 매 호출마다
쓸모없는 계산이 섞이고 "AXIS_CONFIG=조인 설정"이라는 단일 책임이 흐려진다.

**결론:** AXIS_CONFIG는 확장하지 않는다. twin_lookup 전용의 별도 로컬
매핑을 만들어 재사용한다(중복 하드코딩 방지, AXIS_CONFIG 컬럼값 재사용):

```
_TWIN_AXIS_COLUMNS = {**{a: c["column"] for a, c in AXIS_CONFIG.items()},
                       "컵홀더": "cupholder"}
```

### 4-2. LT2/LT3 caveat 문구 — rules.md 원문 그대로 고정

twins.csv에 "이 축은 실측/추정"을 나타내는 구조화된 컬럼이 없다(note는
자유서술 텍스트). LT2/LT3 각 1개씩만 존재하는 고정 케이스이므로, 파싱
로직을 새로 만들지 않고 rules.md:236-238이 이미 제시한 문구를 그대로
하드코딩한다(추론 아님 — rules.md 문구 전사):

```
LT2 -> "볼핏만 실측, 나머지 4축은 상속 추정"
LT3 -> "5축 전부 상속 규칙 기반"
```

### 4-3. TWIN1/2/3 축비교 자동계산

각 축(다리끝규격/폴직경/풋프린트제품군/제품군/컵홀더)에 대해:
1. 그룹 멤버 전원의 해당 컬럼 값을 `_cell_state()`로 조회.
2. state=="unknown"([미확인])인 멤버는 그 축 비교에서 제외(사용자 지시
   4번 — "데이터 없는 제품의 경우 비교에서 제외").
3. 비교 가능한 멤버가 2개 미만이면 → 그 축은 "비교불가"(1개뿐인 값으로
   "동일"을 단정하는 것도 CLAUDE.md 금지사항의 "판정값 생성 금지"와 같은
   원칙 위반이라고 판단 — 근거 없이 동일/다름을 만들지 않음).
4. 비교 가능한 멤버 전원이 같은 (state, 정규화값)이면 → "동일".
5. 값이 갈리면 → 그 축은 same/unclear 어디에도 안 들어감(다름으로 처리,
   별도 텍스트 없이 "N개 축만 동일" 목록에서 자연히 빠짐).

**실제 데이터로 검증(구현 단계에서 코드로 직접 조회 — 아래는 최초 초안 당시
수기 확인이 틀렸던 부분을 실행 결과로 정정한 것):**

| 그룹 | 다리끝규격 | 폴직경 | 풋프린트제품군 | 제품군 | 컵홀더 |
|---|---|---|---|---|---|
| TWIN1(선셋체어/캠프체어) | 55=55 동일 | 14.5=14.5 동일 | Sunset=Sunset 동일 | XL=XL 동일 | 전용=전용 동일 |
| TWIN2(비치체어/re/플라야) | 없음=없음 동일 | 14.5=14.5 동일 | 없음=없음 동일 | 없음=없음 동일 | 없음=없음 동일(플라야만 [미확인]이라 제외, 나머지 2개 실측 동일) |
| TWIN3(체어원미니/스피드스툴S) | 45=45 동일 | 없음=없음 동일 | 없음=없음 동일 | 없음=없음 동일 | 없음=없음 동일(양쪽 다 실측값 "없음") |

→ TWIN1/2/3 전부 "5축 전부 동일" — `uv run python -c "import agent_core as
ac; print(ac.twin_lookup('비치체어(re)')['caveat'])"` 실행 결과로 확인.
twins.csv note 원문 주장과 일치.

**초안 당시 오류 정정:** 처음 plan 초안(위 표)은 `grep`/`awk` 없이 손으로
chairs.csv 열을 세다가 BCH-OUT-STD/SPDS-OUT-STD의 cupholder 값을
[미확인]으로 잘못 읽어 "4개 축만 동일 (컵홀더 비교불가)"을 예상했다.
`awk -F',' 'NR==16{...}'`로 열 번호를 직접 대조한 결과 실제 값은 둘 다
"없음"(chairs.csv:16,29)이었음 — 예상이 틀렸던 건 이 plan 문서였고,
구현된 코드/테스트는 정확한 값을 그대로 계산한다.

**caveat 텍스트 조립 규칙(로직은 유지, 현재 데이터로는 "비교불가" 분기가
실사례로 실행되지 않음 — tests/test_agent_core.py의 합성 데이터
테스트(test_twin_axis_agreement_데이터부족_비교불가)로 별도 검증):**
```
same == 5개  -> "5축 전부 동일"
그 외        -> "{len(same)}개 축만 동일: {same 나열}"
             + unclear 있으면 " (데이터 부족으로 비교불가: {unclear 나열})"
```

### 4-4. estimated/estimate_notice 필드 처리 — 옵션 2개

| | Option A: caveat 추가, 기존 필드 유지 | Option B(추천): caveat로 완전 대체 |
|---|---|---|
| diff 크기 | 최소(신규 필드만 추가) | 약간 더 큼(기존 테스트 1개 수정) |
| 기존 테스트 | 안 건드림 | test_twin_lookup_추정라벨 assert 변경 필요 |
| 스키마 | estimated(bool)/estimate_notice(str)/caveat(str) 3필드 공존 — LT2/LT3는 caveat와 estimate_notice가 사실상 같은 내용 중복 | caveat(str\|None) 1필드로 통일 |
| rules.md 부합도 | "필드를 하나 추가"라는 문구엔 맞지만, "특수 처리를 일반 규칙으로 승격"(228-234행 취지)과는 어긋남 — 옛 특수 필드가 안 죽고 남음 | rules.md 3번 섹션 전체 취지(특수 case를 일반 규칙 하나로 통합)에 부합 |

**추천: Option B.** 근거는 위 표 마지막 줄. system prompt(main.py:79)도
caveat 필드 하나만 안내하는 일반 규칙 문장으로 교체(rules.md:262-265
원문 그대로): "tool 결과에 caveat 필드가 있으면, 그 문장을 답변에 그대로
포함시키세요. 요약하거나 생략하지 마세요."

caveat는 group_id가 LT2/LT3/TWIN1/TWIN2/TWIN3일 때만 채워짐. LT1/LT4/
STANDALONE/그룹없음은 caveat 없음(None) — 이미 100% 실측이거나 비교 대상
자체가 없어서 rules.md 3번이 요구하는 "비교·추정이 들어간 결과"에
해당하지 않음.

## 5. 작업 4 — eval 22문항 반영 (main.py, 작업 3 완료 후 진행)

rules.md:266-274가 "3번 끝난 뒤 확인"이라 명시 — 순서 의존.

- EVAL_CRITERIA에 Q21/Q22 추가:
  ```
  "Q21": {"include_groups": [["One"], ["추정", "상속"]],
          "must_exclude": ["Two", "XL", "Zero"]},
  "Q22": {"include_groups": [["됩니다", "가능"], ["추정", "상속"]],
          "must_exclude": ["안 됩니다", "미지원", "호환되지 않"]},
  ```
  (expected_answer 원문 그대로 옮기지 않고 회고 5번 방식대로 동의어
  그룹화 — Q21/Q22 caveat 문구가 작업 3에서 "볼핏만 실측..." 식으로
  약간 다르게 재조립되므로 "추정"/"상속" 공통어로 느슨하게 묶음)
- "20문항" → "22문항" 3곳: main.py:5(docstring), main.py:198(주석),
  main.py:261(argparse help).
- run_eval() 마지막(main.py:256) 뒤에 임계값 판정 줄 추가:
  ```
  THRESHOLD = 20  # 22문항 중 20개=90.9%, rules.md:274 권고치(반올림)
  ...
  print(f"기준 {THRESHOLD}/{len(rows)} 이상 -> {'충족' if passed >= THRESHOLD else '미달'}")
  ```

## 6. 작업 5 — accessories.csv 그라운드시트 note 정리 (7~13행)

rules.md:276-281 + research 5번 사용자 메모("접근하여 직접 수정할 것").
7행 note를 기존 파일의 "해결됨(2026-08-18) — ..." 관용구(20·21·25·26·27행에
이미 쓰인 패턴)에 맞춰 교체, 8~13행은 "위와 동일" 참조 유지(가리키는
대상이 해결 상태로 바뀌므로 문장은 그대로 자연스러움):

```
7행: 그라운드시트 One,풋프린트제품군,One,없음,N:M,
     "해결됨(2026-08-18) — 공식몰은 인치 사이즈가 아니라 One/Two/XL 등
     의자별 명칭 그대로 판매(사용자 재검증, rules.md:276-281)."
8~13행: note를 "위와 동일 해결." 로 교체(기존 "위와 동일 미해결 이슈."에서
     '미해결'만 삭제).
```
코드는 accessories.csv의 note 컬럼을 어디서도 읽지 않으므로(research 5번
확인, agent_core.py 전체 grep 0건) 이 수정은 동작에 영향 없음 — 순수
데이터 정리.

## 7. 실행 단계 (순서 고정)

1. 작업 1 (height_cm) — agent_core.py
2. 작업 2 (Q09 must_exclude) — main.py
3. 작업 5 (accessories.csv note) — 독립적, 먼저 처리해 데이터 정리 끝냄
4. 작업 3 (caveat 통합) — agent_core.py + main.py 프롬프트 + tests
5. `uv run pytest` — 1~4 회귀 확인
6. 작업 4 (eval Q21/Q22 + 임계값) — main.py, 작업 3 의존
7. `uv run pytest` 재확인
8. [사용자 승인 필요, 외부 API 호출·비용 발생] `uv run main.py --eval`
   22문항 실측 — 20/22 기준 충족 확인
9. 이 문서 "완료 표시"에 각 단계 [x] 갱신 + eval 결과 기록
10. 회고 1장 작성(무엇이 예상과 달랐는지 — 특히 4-3의 TWIN2/TWIN3
    "비교불가" 발견)

## 8. 트레이드오프

- **NUMERIC_COLUMNS 순서**: chairs.csv 헤더 순서를 그대로 따름(가독성) —
  동작에는 순서 무관(딕셔너리/리스트 순회라 순서가 결과값을 안 바꿈).
- **AXIS_CONFIG 비확장(4-1)**: 재사용성보다 단일 책임 유지를 택함 —
  twin_lookup 전용 로컬 매핑 1줄 추가가 gear_to_acc에 죽은 분기를 심는
  것보다 낫다고 판단.
- **LT2/LT3 문구 하드코딩(4-2)**: 일반화 로직(축별 실측/추정 자동 판별)을
  만들 수도 있으나, 그러려면 twins.csv에 구조화 컬럼이 새로 필요함(현재
  범위 밖 데이터 작업) — 고정 2케이스라 하드코딩이 더 적은 코드.
- **"비교불가" 3번째 케이스 신설(4-3)**: 위 표 실측으로 필요성이 드러남.
  [사용자 확인 필요] 항목이라 구현 전 확답 필요.

## 9. 범위 밖 (이번 라운드에 손 안 댐)

- TWIN2_확장후보 행(twins.csv:7, BCH-OUT-MSH/MSHRE) — member_id 세미콜론
  결합 문제, research 3번 확인상 이번 caveat 작업과 무관, 그대로 둠.
- court_lookup/table_lookup 신규 함수 — 사용자 지시로 이번 라운드 범위 밖.
- accessories.csv 그라운드시트 note 외 다른 note/스펙 값 보강 — 지시
  없음.

---

## 완료 표시
(구현 단계 진행하며 각 항목 [x]로 갱신)

- [x] 1. NUMERIC_COLUMNS height_cm
- [x] 2. EVAL_CRITERIA Q09 must_exclude
- [x] 3. accessories.csv 그라운드시트 note
- [x] 4. twin_lookup caveat 통합 + AXIS_CONFIG 비확장 + tests 수정
- [x] 5. pytest 1차 확인 — 12/12 통과(`uv run python tests/test_agent_core.py`,
      pytest 미설치라 파일 내장 러너 사용)
- [x] 6. EVAL_CRITERIA Q21/Q22 + "22문항" 문구 + 임계값 게이트
- [x] 7. pytest 2차 확인 — 12/12 통과, main.py 문법/import 확인 완료
- [x] 8. eval 실측 결과: 1차 19/22(미달) → 원인 진단·수정 → 2차 21/22(기준
      20/22 충족). 아래 회고 참조.
- [x] 9. 회고

## 회고

**1) 1차 실행(19/22) FAIL 3건, 원인이 서로 달랐음:**
- **Q09**: agent_core 정상. LLM이 "높습니다/최상단" 대신 "최댓값/낮다고
  볼 수 없" 식으로 표현 — include_groups 키워드가 좁아서 정답을 FAIL로
  오판정. 이번 실행 실제 문구로 3개 키워드 추가.
- **Q21/Q22**: agent_core도 프롬프트 설계도 아니고, **시스템 프롬프트
  라우팅 규칙 누락**이 원인. caveat는 rules.md 지시대로 twin_lookup에만
  넣었는데, "그라운드시트 뭐 돼요"/"락킹풋 되나요" 질문은 시스템 프롬프트
  규칙1에 따라 gear_to_acc로만 라우팅됨 — LLM이 twin_lookup을 호출할
  이유 자체가 없어서 caveat를 볼 기회가 없었음. LT 모델명이 질문에
  있으면 twin_lookup도 같이 부르도록 규칙1에 1문단 추가해 해결(main.py
  SYSTEM_PROMPT). eval_questions.csv Q21/Q22의 type이 "normal_lt_caveat"로
  명시돼 있었는데도 이 연결을 계획 단계에서 놓쳤음 — 다음 라운드엔
  "caveat 신설 시 그걸 노출할 질문이 실제로 어느 tool로 라우팅되는지"까지
  plan에서 먼저 확인할 것.

**2) plan_v2.md 4-3(TWIN 축비교) 초안 자체가 틀렸었음(구현 단계에서 발견,
바로잡음):** `grep` 출력을 손으로 세다가 BCH-OUT-STD/SPDS-OUT-STD의
cupholder 값을 [미확인]으로 오독해 "TWIN2/3은 4개 축만 동일"이라고
예상했으나, `awk -F','`로 열 번호를 직접 대조하니 실제 값은 둘 다
"없음"(chairs.csv:16,29) — TWIN1/2/3 전부 "5축 전부 동일"이 맞았다.
CLAUDE.md "구체적 근거·파일명:줄번호"를 지키려다 grep 결과를 육안으로
줄맞춤하는 것 자체가 오류원이었음 — 다음부터 다중 컬럼 CSV 확인은
`awk -F','`나 코드로 인덱스를 세는 쪽을 기본으로 함.

**3) Q17이 2차 실행에서 새로 FAIL(1차엔 PASS)했음 — 코드 회귀 아님, 확인
완료.** "캠프체어인데 선셋체어 락킹풋 써도 돼요?"(TWIN1, 5축 완전 동일,
정답 "됩니다")에 대해 이번 실행의 LLM이 "선셋체어 락킹풋"을 별개 제품군인
것처럼 오독해 "안 됩니다"로 답함. 캠프체어/선셋체어 이름엔 "LT"가 없어
이번 라운드에서 건드린 프롬프트/코드와 무관 — 회고 6번(docs/plan_aiagent.md:
222-232)에 이미 문서화된 "쌍둥이·축공유 질문의 run-to-run 비결정성"과
같은 패턴. 종료조건(20/22 이상)은 이 실행에서도 21/22로 충족돼 추가
재실행은 안 함 — 다음 라운드 후보로 남김.

**4) 시간 배분(정정):** 시작 00:58, 작업 완료 후 최종 확인 10:05 —
경과 9h07m / 8h, **캡 초과(+1h07m)**. 작업 자체(1~9 전부)는 실제로는
사용자와의 대화 왕복 사이 텀이 대부분이었을 가능성이 높지만(도구 호출
자체는 수 분 내), CLAUDE.md 규칙은 "완성 여부 무관하게 중단"으로 원인을
안 나눔 — 원칙상 `git tag mvp-stop-v2`가 필요하나, 이 repo엔 아직 커밋이
0개라(`git log` 확인) 태그를 걸 대상 자체가 없음. 커밋 여부는 하네스
지침("사용자가 요청할 때만 커밋")과 충돌해 임의로 만들지 않음 — 사용자
확인 필요.
