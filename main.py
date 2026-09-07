"""헬리녹스 체어↔액세서리 호환 CLI 에이전트.

실행:
    uv run main.py          REPL 모드 (질문 -> 답변 반복, exit로 종료)
    uv run main.py --eval   eval_questions.csv 22문항 배치 채점
"""

import argparse
import csv
import json
from pathlib import Path

from openai import OpenAI

import agent_core as ac

MODEL = "gpt-5.2"

SYSTEM_PROMPT = """당신은 헬리녹스 매장 신입 직원을 돕는 체어-액세서리 호환 안내 에이전트입니다.

## 축(axis) 이름 <-> 액세서리 용어 대응표 (tool 결과 읽을 때 반드시 이 매핑으로 해석하세요)

tool 결과의 axes/spec_context 키는 아래처럼 대응합니다. 사용자가 "락킹풋 되나요?"라고
물으면 반드시 `제품군` 축을 보세요 — `다리끝규격`(볼핏류) 축을 보고 답하면 다른
액세서리를 판정하는 것이므로 틀린 답입니다.

| 축(axis) 키           | 대응 액세서리 종류      |
|-----------------------|--------------------------|
| 다리끝규격             | 볼핏 / 비브람 볼핏        |
| 폴직경                 | 퍼스널쉐이드              |
| 풋프린트제품군         | 그라운드시트              |
| 제품군                 | 락킹풋                    |
| 컵홀더                 | 컵홀더(플라스틱)          |

## tool 선택 규칙 (질문 패턴별로 반드시 이 순서를 따르세요)

0. 질문에 제품명이 2개 나왔는데 그중 하나가 accessories.csv 액세서리 목록(볼핏/
   비브람 볼핏/퍼스널쉐이드/그라운드시트/락킹풋/컵홀더/사이드스토리지/코트레그/
   코트텐트/테이블탑/헤드레스트)에 속한 이름이 아니라면, 그건 액세서리가 아니라
   체어 모델일 가능성이 큽니다("스피드스툴 S/M", "벤치원", "카페 체어"처럼 이름만
   보면 액세서리 같아도 실제로는 체어 30종에 포함된 이름). 이 경우 twin_lookup(첫
   번째 체어)을 호출해 두 번째 이름이 같은 group의 members에 있는지 확인하세요.
   예: "체어원 미니용 액세서리 스피드스툴 S에도 맞아요?" -> "스피드스툴 S"는
   액세서리 목록에 없으므로 체어로 의심 -> twin_lookup("체어원 미니") 호출.
1. "이 체어에 이 액세서리 되나요/맞나요/써도 되나요" (체어 1개 + 액세서리 1개 언급,
   0번에서 체어 모델로 의심되지 않은 경우)
   -> 그 체어로 gear_to_acc를 호출하세요. acc_to_gear로 액세서리 이름부터 검색하지
   마세요 — 액세서리 이름이 틀렸을 수도 있는 게 함정 질문의 핵심입니다. gear_to_acc가
   돌려주는 axes의 실제 matches와 비교해서 맞는지 판단하세요.
   체어 이름에 "LT"가 포함돼 있으면(예: "체어원 LT", "선셋체어 LT") 같은 턴에
   twin_lookup도 함께 호출하세요 — LT 모델은 일부/전체 축이 실측이 아니라 상속
   추정이라, 그 사실은 gear_to_acc가 아니라 twin_lookup의 caveat 필드에만
   담겨 있습니다.
2. "이 액세서리 어떤 체어에 맞아요" (체어 언급 없이 액세서리만) -> acc_to_gear를 호출하세요.
3. 체어 1개의 재고/스펙/성격블록/"약한가요·최고인가요" 질문 -> chair_lookup을 호출하세요.
   "최고/최저/약함/강함"류 판단은 절대 이름으로 추측하지 말고 spec_context의
   overall_max, by_성격블록_max 값과 이 체어의 실제 value를 직접 비교해서 판단하세요.
   성격블록 이름(하이백/로우백/경량/스툴)은 목받침 유무 등 구조 분류일 뿐 실제
   치수 크기와 무관합니다 — 로우백이라고 무조건 낮다고 판단하지 마세요.
4. "가격/무게/사이즈가 보급형인가요·비싼가요·저렴한가요" 같은 LT 변형 비교 질문
   -> twin_lookup을 호출하세요. parent_child_diff에 정확한 %가 이미 계산되어 있으니
   그 숫자를 그대로 인용하세요. chair_lookup만으로는 비교 기준이 없어 답할 수 없습니다.
5. "두 모델이 같나요/쌍둥이인가요/A 모델 액세서리를 B 모델에도 쓸 수 있나요"
   -> twin_lookup을 호출하세요 (B가 A와 같은 group_id의 members에 있는지로 판단).
   액세서리 이름으로 착각해 acc_to_gear를 부르지 마세요 — B는 체어 모델명입니다.
6. "체어원(re) 쓰는데 신형 액세서리도 되나요"처럼 두 체어 모델을 비교하는 질문
   -> 언급된 각 모델마다 gear_to_acc를 각각 호출해(한 턴에 병렬 호출 가능) 축별로
   직접 비교하세요. 한쪽만 조회하고 "같을 것"이라고 넘겨짚지 마세요.
   주의: "구형"/"신형"/"(re)"는 카탈로그 상 모델명의 일부입니다(예: 체어원(구형),
   체어원(신형), 체어원(re)는 서로 다른 3개 모델). query를 만들 때 "신형"만
   따로 떼지 말고 반드시 기준 모델명과 합쳐서 넘기세요(예: "체어원 신형").
   "체어원"처럼 세대 표기 없이 넘기면 8개 모델과 겹쳐 조회에 실패합니다.
7. 질문에 등장한 모델/라인 이름이 tool에서 못 찾겠다는 error를 반환하면(예:
   "택티컬", "홈 라인" 등 데이터에 없는 라인) 절대 다른 모델로 대체 추측하지 말고
   "데이터 없음"이라고 답하세요.

## 답변 규칙

- tool 호출 결과(dict)에 없는 수치나 판정을 절대 만들어내지 마세요. tool 결과만 근거로 답하세요.
- tool 결과의 state가 "미지원"이면 확정된 사실입니다. "안 됩니다"라고 명확히 답하세요.
- tool 결과의 state가 "데이터 없음"이거나 tool이 error를 반환하면 반드시 "데이터 없음"이라고
  답하고 추측하지 마세요.
- tool 결과에 caveat 필드가 있으면, 그 문장을 답변에 그대로 포함시키세요. 요약하거나 생략하지 마세요.
- parent_child_diff의 각 항목은 {"pct": 숫자, "label": "부모보다 N% 비쌈/저렴/무거움/가벼움/큼/작음"}
  형태입니다. 부호(+/-)를 직접 해석하지 말고 label 문구를 그대로 인용하세요.
- chair_lookup 결과에 twin_fallback이 있으면(단종/품절 모델) 그 안의 members 이름과
  note를 반드시 답변에 포함해 대체 모델을 안내하세요.
- "안 됩니다"/"됩니다" 한 단어로 끝내지 말고, tool 결과의 구체적 근거(축 이름·값·숫자)를
  최소 1개 인용해서 신입 직원이 왜 그런지 이해하도록 설명하세요.
- 한국어로 간결하게 답하세요.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "chair_lookup",
            "description": "체어 모델 1개를 조회한다. 스펙, 5개 호환축 원본값, 단종/품절 시 대체 모델 안내를 포함한다.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "체어 모델명 또는 id"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gear_to_acc",
            "description": "체어 모델 1개가 어떤 액세서리와 호환되는지 축별로 조회한다.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "체어 모델명 또는 id"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "acc_to_gear",
            "description": "액세서리 1개가 어떤 체어 모델과 호환되는지 조회한다.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "액세서리명"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "twin_lookup",
            "description": "체어 모델 1개의 쌍둥이/LT 그룹(동일 호환축을 공유하는 다른 모델)을 조회한다.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "체어 모델명 또는 id"}},
                "required": ["query"],
            },
        },
    },
]

TOOL_FUNCS = {
    "chair_lookup": ac.chair_lookup,
    "gear_to_acc": ac.gear_to_acc,
    "acc_to_gear": ac.acc_to_gear,
    "twin_lookup": ac.twin_lookup,
}


def _load_api_key() -> str:
    env_path = Path(__file__).resolve().parent / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "OPENAI_API_KEY":
            return value.strip()
    raise RuntimeError(".env에 OPENAI_API_KEY 없음")


def ask(client: OpenAI, question: str) -> str:
    """1왕복 tool-calling: LLM이 tool 1개 선택 -> agent_core 실행 -> LLM이 그 결과로 답변 작성."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    first = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
    msg = first.choices[0].message

    if not msg.tool_calls:
        return msg.content or ""

    messages.append(msg.model_dump(exclude_none=True))
    for call in msg.tool_calls:
        func = TOOL_FUNCS.get(call.function.name)
        args = json.loads(call.function.arguments or "{}")
        result = func(args.get("query", "")) if func else {"error": f"알 수 없는 tool: {call.function.name}"}
        messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": json.dumps(result, ensure_ascii=False),
        })

    final = client.chat.completions.create(model=MODEL, messages=messages)
    return final.choices[0].message.content or ""


def repl(client: OpenAI) -> None:
    print("헬리녹스 체어 호환 안내 에이전트. 'exit' 입력 시 종료.")
    while True:
        try:
            question = input("\n질문> ").strip()
        except EOFError:
            break
        if question.lower() == "exit":
            break
        if not question:
            continue
        print(ask(client, question))


# eval_questions.csv 22문항 채점 기준. "include_groups"는 expected_answer
# 원문에서 옮긴 핵심 사실 각각에 대해 "동의어 중 최소 1개"를 요구하는
# AND-of-OR 목록(plan_aiagent.md 8번 취지 유지, 실제 LLM 응답 문구 변동에
# 맞춰 동의어를 추가함 — 최초 1회 실행 결과 실측 후 보강, main.py 회고 참조).
# "must_exclude"는 traps.csv wrong_answer가 유도하는 오답 패턴에서 뽑음.
#
# Q09(v2 정정, plan_v2.md 작업2): traps.csv/eval_questions.csv가 T09를
# "체어투(84cm)보다 높다, 사바나(110cm)보다 낮다"로 정정(둘 다 chairs.csv
# height_cm 실측값, plan_v2.md 3번). 새 expected_answer 문구 자체에
# "사바나보다는 낮습니다"가 들어있어 must_exclude=["낮습니다"]로 두면
# 정답까지 FAIL 처리됨 — 실제로 막아야 할 반대 결론("체어투보다 낮다")
# 문구로 좁힘. Q01~Q20 전체 must_exclude를 expected_answer와 전수 대조한
# 결과 이 collision은 Q09 하나뿐(plan_v2.md 작업2 확인 완료).
EVAL_CRITERIA: dict[str, dict[str, list]] = {
    "Q01": {"include_groups": [["안 됩니다", "미지원", "호환되지 않"]], "must_exclude": ["가능합니다"]},
    "Q02": {"include_groups": [["안 됩니다", "지원하지 않", "안 되는", "미지원", "수 없"]], "must_exclude": ["가능합니다"]},
    "Q03": {"include_groups": [["Two"]], "must_exclude": ["One 사"]},
    "Q04": {"include_groups": [["One"]], "must_exclude": ["Zero입니다"]},
    "Q05": {"include_groups": [["XL"]], "must_exclude": ["Sunset입니다"]},
    "Q06": {"include_groups": [["안 됩니다", "미지원", "호환되지 않"]], "must_exclude": ["가능합니다"]},
    "Q07": {"include_groups": [["선셋체어"]], "must_exclude": ["단종이라 데이터", "단종이므로 데이터"]},
    "Q08": {"include_groups": [["다릅니다", "달라서", "갈립니다", "불가"]],
            "must_exclude": ["전부 동일", "완전히 동일", "모두 동일", "전체가 동일"]},
    "Q09": {"include_groups": [["높습니다", "낮은 편이 아니", "최상단", "높은",
                                "최댓값", "낮다고 볼 수 없", "낮은 건 아니"]],
            "must_exclude": ["체어투보다 낮", "84cm보다 낮"]},
    "Q10": {"include_groups": [["32"]], "must_exclude": ["저렴한 편", "보급형입니다"]},
    "Q11": {"include_groups": [["190"]], "must_exclude": ["약합니다"]},
    "Q12": {"include_groups": [["안 됩니다", "미지원", "호환되지 않"]], "must_exclude": ["가능합니다"]},
    "Q13": {"include_groups": [["Two"]], "must_exclude": ["락킹풋 XL"]},
    "Q14": {"include_groups": [["Zero"]], "must_exclude": ["락킹풋 One"]},
    "Q15": {"include_groups": [["체어원 엑스라지"]], "must_exclude": ["체어원 미니"]},
    "Q16": {"include_groups": [["사바나"]], "must_exclude": ["체어원 라지"]},
    "Q17": {"include_groups": [["동일", "됩니다", "돼요", "가능합니다", "맞습니다"]],
            "must_exclude": ["데이터 없음", "안 됩니다", "쓰는 건 안 되고", "쓰면 안 되"]},
    "Q18": {"include_groups": [["45"]], "must_exclude": ["데이터 없음"]},
    "Q19": {"include_groups": [["데이터 없음"]], "must_exclude": []},
    "Q20": {"include_groups": [["데이터 없음"]], "must_exclude": []},
    # Q21/Q22(v2 신설, plan_v2.md 작업4) — LT2/LT3 caveat가 실제로 답변에
    # 뜨는지 첫 검증. twin_lookup의 caveat 문구는 helinox_compat_policy.md 원문 그대로
    # 고정("볼핏만 실측, 나머지 4축은 상속 추정" / "5축 전부 상속 규칙
    # 기반")이라 expected_answer 원문과 표현이 다를 수 있어 "추정"/"상속"
    # 공통어로 느슨하게 묶음(회고 5번 동의어 그룹화 방식).
    "Q21": {"include_groups": [["One"], ["추정", "상속"]],
            "must_exclude": ["Two", "XL", "Zero"]},
    "Q22": {"include_groups": [["됩니다", "가능"], ["추정", "상속"]],
            "must_exclude": ["안 됩니다", "미지원", "호환되지 않"]},
}

# 22문항 중 20개(90.9%, 반올림 20/22) — helinox_compat_policy.md:274 권고치. run_eval()이
# 채점 후 이 기준 충족 여부를 판정용 1줄로 추가 출력한다(기존엔 게이트
# 자체가 없었음, plan_v2.md 작업4).
EVAL_PASS_THRESHOLD = 20


def run_eval(client: OpenAI) -> None:
    data_path = Path(__file__).resolve().parent / "data" / "eval_questions.csv"
    with open(data_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    passed = 0
    print(f"{'q_id':<5} {'결과':<6} question")
    print("-" * 70)
    for row in rows:
        q_id = row["q_id"]
        answer = ask(client, row["question"])
        criteria = EVAL_CRITERIA.get(q_id, {"include_groups": [], "must_exclude": []})
        ok = all(any(kw in answer for kw in group) for group in criteria["include_groups"]) and \
            not any(kw in answer for kw in criteria["must_exclude"])
        passed += int(ok)
        status = "PASS" if ok else "FAIL"
        print(f"{q_id:<5} {status:<6} {row['question']}")
        if not ok:
            print(f"      -> 답변: {answer}")
    print("-" * 70)
    print(f"{passed}/{len(rows)} PASS")
    status = "충족" if passed >= EVAL_PASS_THRESHOLD else "미달"
    print(f"기준 {EVAL_PASS_THRESHOLD}/{len(rows)} 이상 -> {status}")


def main() -> None:
    parser = argparse.ArgumentParser(description="헬리녹스 체어 호환 CLI 에이전트")
    parser.add_argument("--eval", action="store_true", help="eval_questions.csv 22문항 배치 채점")
    args = parser.parse_args()

    client = OpenAI(api_key=_load_api_key())
    if args.eval:
        run_eval(client)
    else:
        repl(client)


if __name__ == "__main__":
    main()
