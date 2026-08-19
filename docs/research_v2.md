# research: v2 (rules.md "v2 변경사항" 5개 항목)

대상: rules.md:191-281 5개 항목이 실제로 호출/의존할 agent_core.py·main.py
현재 동작. 개요·진행경과·계획은 미포함. 범위: 체어 에이전트 코드만
(cots.csv/tables.csv는 데이터 반영 여부만 확인, court_lookup/table_lookup
신규 함수 미검토 — 사용자 지시).

## 1. chairs.csv height_cm 컬럼

- data/chairs.csv:1 헤더에 이미 `height_cm` 존재(width_cm/length_cm 다음,
  pack_size 앞) — 데이터 반영 완료 확인. 24개 실측값, 단종 6개(구형체어원/
  비치체어/비치메쉬/플라야/캠프/스피드스툴S) `[미확인]`(chairs.csv:3,16-18,20,29).
- agent_core.py:39-42 `load_chairs()`는 `csv.DictReader` — 컬럼 위치 무관,
  이름으로 읽음. `row[숫자]` 인덱스 하드코딩 전수 grep 0건(agent_core.py,
  main.py 전체). rules.md가 우려한 "로더 깨짐"은 없음.
- 다만 agent_core.py:32-34 `NUMERIC_COLUMNS`엔 `height_cm`이 없음 →
  chair_lookup()(agent_core.py:199-222)의 `spec_context`에 height_cm의
  `overall_max`/`by_성격블록_max`가 안 잡힘. `dict(chair)`(agent_core.py:205)로
  원본 문자열 값(예: "89")은 result에 그대로 남지만, "최고/최저" 비교는
  system prompt(main.py:51-53)가 "spec_context 값으로만 비교"를 지시하므로
  height_cm은 그 rule 밖에 있음. rules.md 원문은 "로더만 확인"이라 명시적
  지시는 아님 — 플랜 단계 확인 필요.

  ## height_cm 보다 seat_height_cm가 더 중요함. 의자 자체의 높이보다 앉았을 때의 높이가 가치 있는 데이터임. 다만 height_cm를 통해서 의자 간 그룹핑이나 카테고리 분류에 쓰이는 기준이 된다면 사용 고려해볼 것.

## 2. T09/Q09 정정

- traps.csv:10(T09)·eval_questions.csv:10(Q09) 둘 다 "체어투(84cm)보다
  높다, 사바나(110cm)보다 낮다"로 이미 정정됨. evidence_row도
  `height_cm`으로 바뀜(traps.csv:10) — 데이터 반영 완료 확인.
- main.py:220 `EVAL_CRITERIA["Q09"]`는 `must_exclude: ["낮습니다"]`인데,
  새 expected_answer 자체에 "...사바나(110cm)보다는 **낮습니다**"가
  포함됨(eval_questions.csv:10) → 새 정답 문구를 그대로 답해도 must_exclude에
  걸려 FAIL 처리됨. 옛 근거("81"/"체어제로")는 이미 안 남아있음(확인 완료,
  grep 0건) — 남은 문제는 must_exclude 충돌 하나.

## 3. caveat 필드 일반화

- 현재 twin_lookup()(agent_core.py:294-346)은 `estimated`/`estimate_notice`
  필드만 있고(agent_core.py:312-315), LT2·LT3에 동일 문구 하나만 반환 —
  rules.md가 요구하는 "LT2는 볼핏만 실측·나머지 4축 추정" 같은 축별 세분화
  없음. `caveat` 필드는 코드 전체에 0건(grep 확인, .py + data/*.csv).
- 진짜 쌍둥이(TWIN1/2/3) 축 비교 로직 자체가 없음 — 지금은 twins.csv의
  `note` 원문 텍스트만 그대로 반환(agent_core.py:311), "N개 축만 동일"
  자동 계산 없음.
- 축→한글 라벨 매핑이 4개뿐(AXIS_CONFIG, agent_core.py:25-30: 다리끝규격/
  폴직경/풋프린트제품군/제품군). 컵홀더는 gear_to_acc 안에서만 하드코딩된
  별도 분기(agent_core.py:247-254)로 처리되고 AXIS_CONFIG엔 없음 — 5축
  전체를 비교하려면 컵홀더 라벨 매핑이 twin_lookup 쪽에도 필요.
- twins.csv:7 `TWIN2_확장후보` 행은 group_id 문자열 자체가 다르고
  member_id가 `"BCH-OUT-MSH;BCH-OUT-MSHRE"`(세미콜론 결합 1셀)라 현재
  `group_id = next(... t["member_id"] == chair["id"] ...)`(agent_core.py:301)
  방식으로는 두 모델 다 매칭 안 됨 — 기존에도 그룹 없음으로 처리되던
  부분, 이번 caveat 계산과 무관하게 그대로.
- twins.csv:6 TWIN2 멤버 중 `PLYA-OUT-STD`는 5축 전부 `[미확인]`
  (chairs.csv:18) — "N개 축만 동일" 자동 계산 시 미확인 멤버를 어떻게
  처리할지(비교 제외 vs 불일치 처리) 규칙이 rules.md에 명시 안 됨.

## 4. eval_questions.csv 22문항

- data/eval_questions.csv:1-23 이미 22행(Q01-Q22), Q21/Q22 각각 twins.csv:LT2/
  LT3 캡션 질문으로 존재 — 데이터 반영 완료 확인.
- main.py:210-233 `EVAL_CRITERIA` dict는 Q01~Q20까지만 있음. Q21/Q22 키
  없음 → run_eval()(main.py:236-256)이 `EVAL_CRITERIA.get(q_id, {...})`
  (main.py:247) 기본값(빈 include/exclude)으로 채점해 사실상 항상 PASS
  처리됨(3번 caveat 일반화가 실제 동작하는지 검증 못 함).
- "20문항" 하드코딩 문구 3곳: main.py:5(모듈 docstring), main.py:198(주석),
  main.py:261(argparse help). 실제 배치 크기는 `len(rows)`(main.py:256)로
  동적 계산이라 코드 동작 자체는 22문항으로도 정상 작동 — 문구만 stale.
- rules.md:274 "20/22(90.9%, 반올림 20/22)를 새 기준으로 삼을 것을 권한다"
  — run_eval()엔애초 pass/fail 임계값 게이트 자체가 없음(마지막 줄
  `{passed}/{len(rows)} PASS` 출력만, main.py:256). 임계값 적용 여부는
  플랜 단계 확인 필요.

## 5. 그라운드시트 인치 매핑 우려 폐기

- rules.md:98-102 "해결됨" + rules.md:276-281 "코드에 반영된 우려 있으면
  지울 것" — SYSTEM_PROMPT(main.py:19-87) 및 agent_core.py 전체 grep 결과
  "인치"/"미해결"/"재확인 필요" 0건. 코드·프롬프트 쪽엔 애초에 반영된 적
  없음 확인 — 이 항목은 조치 불필요.
- [범위 밖 관찰] data/accessories.csv:7-13(그라운드시트 One~Swivel 6행)
  note 컬럼엔 여전히 `[미해결] ... 인치 사이즈 ... 매핑 미확보 ... 재확인
  필요` 문구가 남아있음(accessories.csv:7). 코드가 이 note 컬럼을 읽지
  않으므로(agent_core.py 어디서도 accessories `note` 필드 미사용) 동작에
  영향 없음 — 이번 라운드 지시("에이전트 코드만") 밖이라 손 안 댐, 존재만
  기록.

  ## accessories.csv 접근하여 직접 수정할 것.

## cots.csv / tables.csv 스코프 확인

- data/cots.csv(8행=7코트+헤더), data/tables.csv(9행=8테이블+헤더) 이미
  존재, rules.md:123-186 서술과 행수 일치 — 데이터 반영 완료 확인.
- agent_core.py 공개 함수는 여전히 4개뿐(chair_lookup/gear_to_acc/
  acc_to_gear/twin_lookup, agent_core.py:7-11 docstring 그대로) —
  court_lookup/table_lookup 미생성 확인, 사용자 지시("새 기능 만들지 마")와
  현재 상태 일치.

## [확인 필요] (플랜 단계에서 결정)

1. NUMERIC_COLUMNS에 height_cm 추가 여부(1번) — 추가 안 하면 T09류
   "최고/최저" 판단을 spec_context가 아닌 원본값 직접 비교로 처리해야 함.
   ## NUMERIC_COLUMNS에 seat_height_cm 있는 것 확인, height_cm만 없다면 추가할 것. 높이만 제외할 수 없음.
2. EVAL_CRITERIA Q09 must_exclude "낮습니다" 제거/교체 방식(2번).
  ## 새로 바뀐 trap.csv의 문구를 걸리지 않게 교체할 것. 그 전에 trap과 그에 맞는 대처법을 직접 지정하는게 하드 튜닝의 일부는 아닌지 깊게 고려 필요.
3. caveat 필드 스키마 — LT2/LT3 세분화 문구 + TWIN 축비교 자동계산 로직
   설계, 컵홀더 축 라벨 매핑 위치(AXIS_CONFIG 확장 vs 별도 dict)(3번).
   ## 내 생각은 축확장인데, 그 전에 v1 설계 당시 컵홀더가 왜 축에 추가되지 않았는지, 하지 말아야 할 이유가 있었는지 짚고 넘어갈 것.
4. TWIN2의 PLYA-OUT-STD([미확인] 멤버) 축비교 처리 방식(3번).
  ## 데이터가 없는 제품의 경우 비교에서 제외할 것
5. EVAL_CRITERIA Q21/Q22 신설 + "20문항" 문구 3곳 갱신 + 임계값 게이트
   신설 여부(20/22 권고치 반영할지)(4번).
   ## 반영할 것
