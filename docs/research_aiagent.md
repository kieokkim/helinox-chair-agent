# research: AI 에이전트 연동 (다음 단계)

대상: 에이전트 구축이 직접 호출/의존할 현재 실제 동작. 개요·진행경과·계획은 미포함.

## 1. main.py — 실행 진입점 없음
- main.py:1-6, print stub 함수 1개뿐. 인자·데이터로딩·LLM호출 없음.
- pyproject.toml:7 `dependencies = []` — anthropic SDK 등 미설치. 
- pyproject.toml:6, .python-version:1 — python 3.13 고정.
## -> dependencies는 사용할 에이전트 프레임워크를 에이전트 적합도에 가장 맞는 것으로 진행. api 호출 시 사용할 llm은 OpenAI API를 할 것이고 .env에 내용 추가함.

## 2. helinox-onboarding-v1.html — 순수 정적 프론트, LLM 호출 지점 0개
- 전체 602줄, `<script>` 171~599줄. "fetch" 전수 grep 0건 — API/모델 호출 코드 자체가 없음.
- 자연어 질의응답 없음. 필터(성격블록/무게/내하중/색/상태) + 검색창(문자열 include) + 카드/상세패널만 존재 (helinox-onboarding-v1.html:360-591).
- 데이터는 CHAIRS 배열(188~326줄)에 JS 리터럴로 수기 재입력됨 — data/chairs.csv와 별도 소스. 필드 구조도 다름(csv는 weight_g 단일, html은 wU/wP 분리; 예 CHR1-OUT-RE는 chairs.csv:5, 동일 모델 html:204). 두 소스 동기화 로직 없음 → drift 위험, 에이전트가 어느 쪽을 진실로 삼을지 결정 필요. 
## -> 초기 html 구현 당시는 직접 입력했고, data내 csv 파일은 그 내용을 추출한 것으로 확인. 작업은 csv 기준으로 하고 추가 데이터도 csv로 append할 것. html은 참고용

## 3. data/chairs.csv — 30행 17열, 에이전트가 참조할 1차 소스 후보
- 헤더: data/chairs.csv:1 (id,name,status,category,성격블록,ballfeet,shade_mm,groundsheet,rockingfoot,cupholder,weight_g,load_kg,seat_height_cm,width_cm,length_cm,pack_size,price_krw).
- [미확인] 셀: 단종 4모델 전 스펙컬럼(체어원구형 3행, 비치체어 16행, 비치체어메쉬 17행, 캠프체어 20행). 플라야체어(18행)는 5축 호환값 자체도 [미확인].
- CLAUDE.md 금지사항: ballfeet/shade_mm/groundsheet/rockingfoot/cupholder는 이 CSV에 없으면 "데이터 없음" 출력, 추론 금지 — 에이전트 응답 로직에 강제할 지점.
## -> 단종된 모델은 스펙컬럼 채울 수 없음. 데이터 채우는 걸 보류. 플라야 체어는 비치체어랑 5축 호환값 동일.

## 4. data/accessories.csv — 25행, gear↔accessory 조인 로직 미구현
- decision_axis 7종 존재(accessories.csv:2-26 note 컬럼)하나, chairs.csv 각 행에 이미 축값이 직접 박혀 있어 실제 조인 함수는 코드 어디에도 없음(html·main.py 모두).
- [미해결] 그라운드시트 명칭(One/Two/XL/Sunset/Zero/Swivel, accessories.csv:7-13) ↔ 공식몰 실제 판매 인치사이즈(12.6~21.4) 매핑 없음 (rules.md:95-99, "[중요]" 태그). 매핑 없으면 에이전트가 추천해도 신입이 실제 구매 페이지에서 못 누름.
## -> 공식몰 실제 판매는 명칭으로 진행. 이 미해결 건은 삭제 필요.

## 5. data/eval_questions.csv — 20문항, 사실상 에이전트 v1 회귀테스트셋
- 컬럼: eval_questions.csv:1 (q_id,question,expected_answer,evidence_row,type).
- type 분포: trap 12건(Q01-12,eval_questions.csv:2-13) · normal_gear_to_acc 2건(Q13-14) · normal_acc_to_gear 2건(Q15-16) · normal_twin 2건(Q17-18) · normal_no_data 2건(Q19-20).
- Q19/Q20은 택티컬·HDB 미수집 상태에서 "데이터 없음" 답이 정답으로 이미 고정됨 — find 결과 data/ 안에 택티컬·HDB용 csv 없음(5개 파일뿐).

## 6. rules.md 열린 이슈 5건 — 프롬프트 설계 전 확인 필요
- rules.md:93-116. 이슈1 그라운드시트 매핑(위 4번과 동일건, [중요]) · 이슈3 twins.csv의 LT2/LT3는 실측 아닌 상속규칙 추정 → 에이전트가 이 두 그룹 답할 때 "추정" 라벨 필수(twins.csv:12-15).

## [미확인]
- accessories.csv:6 퍼스널쉐이드 가격 "143000원대(정확 미확인)" — 에이전트가 가격을 답변에 포함할지 미결정.
- 에이전트 실행 형태(main.py CLI / html에 API 연동 / 별도 서버) 자체가 코드상 아직 미결정 — 이번 리서치 범위 밖, plan 단계에서 사용자 선택 필요.
## -> 퍼스널 쉐이드 가격 115000원, 추후 악세사리 스펙 추가할 것. 