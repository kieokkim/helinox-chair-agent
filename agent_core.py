"""헬리녹스 체어↔액세서리 호환 결정론적 rule 엔진.

CSV(data/*.csv)만 근거로 판정한다. LLM은 이 모듈이 반환하는 dict를 그대로
서술만 할 뿐, 여기서 계산되지 않은 수치·판정은 만들어내지 않는다
(CLAUDE.md 금지사항 1·2번).

공개 함수 4개(에이전트 tool로 그대로 노출):
    chair_lookup(query)   - 체어 1개 조회 (+ 단종/품절이면 twin 대체 안내)
    gear_to_acc(query)    - 체어 1개 -> 호환 액세서리
    acc_to_gear(query)    - 액세서리 1개 -> 호환 체어 목록
    twin_lookup(query)    - 체어 1개 -> 쌍둥이/LT 그룹 정보
"""

from __future__ import annotations

import csv
import functools
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"

# accessories.csv의 decision_axis(한글) -> chairs.csv 컬럼명.
# 범위 밖 축(디자인라인/코트등급/테이블사이즈)은 여기 없음 -> cfg 조회 실패 시
# "데이터 없음"으로 답한다(plan_aiagent.md 3번 표 그대로).
AXIS_CONFIG: dict[str, dict] = {
    "다리끝규격": {"column": "ballfeet", "multi": False, "strip_suffix": None},
    "폴직경": {"column": "shade_mm", "multi": True, "strip_suffix": "mm"},
    "풋프린트제품군": {"column": "groundsheet", "multi": False, "strip_suffix": None},
    "제품군": {"column": "rockingfoot", "multi": False, "strip_suffix": None},
}

NUMERIC_COLUMNS = [
    "weight_g", "load_kg", "seat_height_cm", "width_cm", "length_cm", "height_cm",
    "price_krw",
]


# ---------- CSV 로딩 ----------

@functools.lru_cache(maxsize=1)
def load_chairs() -> list[dict]:
    with open(_DATA_DIR / "chairs.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@functools.lru_cache(maxsize=1)
def load_accessories() -> list[dict]:
    with open(_DATA_DIR / "accessories.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@functools.lru_cache(maxsize=1)
def load_twins() -> list[dict]:
    with open(_DATA_DIR / "twins.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---------- 값 3분류 (plan 4번) ----------

def _cell_state(raw: str) -> tuple[str, str]:
    """chairs.csv 셀 값을 3분류. ("value"/"none"/"unknown", 원본값)."""
    if raw == "[미확인]":
        return "unknown", raw
    if raw == "없음":
        return "none", raw
    return "value", raw


def _required_values(acc_row: dict) -> list[str]:
    """accessories.csv required_value를 chairs.csv 셀 값과 비교 가능한 형태로 정규화."""
    cfg = AXIS_CONFIG.get(acc_row["decision_axis"])
    raw = acc_row["required_value"]
    parts = raw.split(";") if cfg and cfg["multi"] else [raw]
    suffix = cfg["strip_suffix"] if cfg else None
    out = []
    for p in parts:
        p = p.strip()
        if suffix and p.endswith(suffix):
            p = p[: -len(suffix)]
        out.append(p)
    return out


# ---------- 이름 -> id 퍼지 매칭 (plan 6번, 별도 NLU 없음) ----------

def _norm(s: str) -> str:
    # 공백·괄호 제거: 카탈로그 세대 표기가 "체어원(신형)"처럼 괄호를 쓰기 때문에
    # 괄호를 남기면 "체어원 신형"(사용자 표현, 괄호 없음) 같은 정상 질의가
    # 문자열 연속성이 끊겨 부분일치에 실패한다.
    return s.replace(" ", "").replace("(", "").replace(")", "").lower()


def _resolve_chair(query: str, chairs: list[dict]) -> dict | None:
    q = query.strip()
    for c in chairs:
        if c["id"] == q or c["name"] == q:
            return c
    nq = _norm(q)
    for c in chairs:
        if _norm(c["name"]) == nq:
            return c
    # 부분일치는 "질문이 이름의 일부"(예: "미니" -> 체어원 미니) 방향만 허용.
    # 반대 방향("이름이 질문의 일부")까지 허용하면 "홈 라인 선셋체어"처럼 존재하지
    # 않는 라인 접두어가 붙은 질문이 실존 모델(선셋체어)로 잘못 흡수된다
    # (eval Q20 실측 실패 사례) — 데이터에 없는 라인은 "데이터 없음"으로 막혀야 함.
    candidates = [c for c in chairs if nq and nq in _norm(c["name"])]
    return candidates[0] if len(candidates) == 1 else None


def _resolve_accessory(query: str, accessories: list[dict]) -> dict | None:
    q = query.strip()
    for a in accessories:
        if a["accessory"] == q:
            return a
    nq = _norm(q)
    for a in accessories:
        if _norm(a["accessory"]) == nq:
            return a
    candidates = [a for a in accessories if nq and nq in _norm(a["accessory"])]
    return candidates[0] if len(candidates) == 1 else None


_NOT_FOUND_CHAIR = "데이터 없음: 모델 '{q}'를 찾을 수 없습니다. (현재 데이터는 아웃도어 라인 30개만 수집됨)"
_NOT_FOUND_ACC = "데이터 없음: 액세서리 '{q}'를 찾을 수 없습니다."


# ---------- 수치 보조 (chair_lookup의 "전 라인업 최고" 류 판단용) ----------

def _to_number(raw: str) -> float | None:
    try:
        return float(raw)
    except ValueError:
        return None


def _pack_volume(raw: str) -> float | None:
    """'12.5x47x12' 같은 pack_size 문자열의 부피(단위 없음, 비교용)."""
    if raw in ("없음", "[미확인]"):
        return None
    try:
        vol = 1.0
        for part in raw.lower().split("x"):
            vol *= float(part)
        return vol
    except ValueError:
        return None


def _pct_diff(base_raw: str, other_raw: str) -> float | None:
    base = _to_number(base_raw)
    other = _to_number(other_raw)
    if base is None or other is None or base == 0:
        return None
    return round((other - base) / base * 100, 1)


def _diff_label(pct: float, more_word: str, less_word: str) -> str:
    """부호 있는 %를 자연어로 확정 — LLM이 +/-를 반대로 읽는 사례를 rule로 차단."""
    if pct > 0:
        return f"부모보다 {pct}% {more_word}"
    if pct < 0:
        return f"부모보다 {abs(pct)}% {less_word}"
    return "부모와 동일"


# twin_lookup 전용 축 라벨->컬럼 매핑(plan_v2.md 4-1). AXIS_CONFIG를 그대로
# 확장하지 않는 이유: AXIS_CONFIG는 gear_to_acc의 "체어 컬럼값 ==
# accessory required_value" 조인 매칭 전용 설정이고, 컵홀더는 그 조인
# 패턴이 아예 안 맞아(accessories.csv에 decision_axis="컵홀더"인 행이
# 없음) 원래부터 별도 특수 분기(gear_to_acc, 컵홀더 부분)로 처리돼왔다.
# 여기서는 5축 값을 단순 비교만 하면 되므로 AXIS_CONFIG의 컬럼값만 재사용해
# 별도 딕셔너리로 둔다(중복 하드코딩 방지, AXIS_CONFIG 책임은 그대로 유지).
_TWIN_AXIS_COLUMNS: dict[str, str] = {
    **{axis: cfg["column"] for axis, cfg in AXIS_CONFIG.items()},
    "컵홀더": "cupholder",
}

# LT2/LT3 caveat 고정 문구(rules.md:236-238 원문 전사). twins.csv에 "이 축은
# 실측/추정"을 나타내는 구조화 컬럼이 없어 자동 계산이 불가능하고, LT2/LT3
# 둘뿐인 고정 케이스라 파싱 로직 대신 문구를 그대로 하드코딩한다.
_LT_CAVEAT: dict[str, str] = {
    "LT2": "볼핏만 실측, 나머지 4축은 상속 추정",
    "LT3": "5축 전부 상속 규칙 기반",
}


def _twin_axis_agreement(
    member_ids: list[str], chairs_by_id: dict[str, dict]
) -> tuple[list[str], list[str]]:
    """진짜 쌍둥이(TWIN1/2/3) 그룹의 5축을 멤버끼리 비교.

    [미확인] 멤버는 그 축 비교에서 제외한다(사용자 지시: 데이터 없는
    제품은 비교에서 제외). 비교 가능한 멤버가 2개 미만이면 "동일"을
    단정하지 않고 unclear로 분류 — 근거 없이 판정값을 만들지 않는다는
    CLAUDE.md 금지사항과 같은 원칙.

    반환: (same 축 라벨 리스트, unclear 축 라벨 리스트). same/unclear 어디에도
    없는 축은 값이 갈린 것(다름)이다.
    """
    same: list[str] = []
    unclear: list[str] = []
    for axis, col in _TWIN_AXIS_COLUMNS.items():
        states = []
        for mid in member_ids:
            chair = chairs_by_id.get(mid)
            if chair is None:
                continue
            state, norm = _cell_state(chair[col])
            if state != "unknown":
                states.append((state, norm))
        if len(states) < 2:
            unclear.append(axis)
        elif len(set(states)) == 1:
            same.append(axis)
    return same, unclear


def _twin_caveat(
    group_id: str, member_ids: list[str], chairs_by_id: dict[str, dict]
) -> str | None:
    """twin_lookup의 caveat 필드(rules.md 3번 — 비교/추정이 들어간 결과는
    LLM이 직접 문장을 조립하게 두지 않고 rule이 완성 문장을 미리 만든다)."""
    if group_id in _LT_CAVEAT:
        return _LT_CAVEAT[group_id]
    if group_id.startswith("TWIN"):
        same, unclear = _twin_axis_agreement(member_ids, chairs_by_id)
        if len(same) == 5:
            text = "5축 전부 동일"
        elif same:
            text = f"{len(same)}개 축만 동일: {', '.join(same)}"
        else:
            text = "동일하다고 확인된 축 없음"
        if unclear:
            text += f" (데이터 부족으로 비교불가: {', '.join(unclear)})"
        return text
    return None


@functools.lru_cache(maxsize=1)
def _lineup_stats() -> dict[str, dict]:
    """숫자 스펙 컬럼별 전체 최고값 + 성격블록별 최고값. [미확인]/없음 행은 제외.

    chair_lookup이 "전 라인업 최고" 류 판단에 참조 — 매 질문마다 하드코딩된
    임계값 대신, CSV 실측값에서 매번 다시 계산한다(traps.csv T09/T11 대응).
    """
    chairs = load_chairs()
    stats: dict[str, dict] = {}
    for col in NUMERIC_COLUMNS:
        rows = []
        for c in chairs:
            v = _to_number(c[col])
            if v is not None:
                rows.append((c["id"], c["name"], c["성격블록"], v))
        if not rows:
            continue
        overall_id, overall_name, _, overall_val = max(rows, key=lambda r: r[3])
        by_group: dict[str, tuple[str, str, float]] = {}
        for cid, name, group, val in rows:
            cur = by_group.get(group)
            if cur is None or val > cur[2]:
                by_group[group] = (cid, name, val)
        stats[col] = {
            "overall_max": {"id": overall_id, "name": overall_name, "value": overall_val},
            "by_성격블록_max": {
                g: {"id": i, "name": n, "value": v} for g, (i, n, v) in by_group.items()
            },
        }
    return stats


# ---------- 4개 공개 함수 ----------

def chair_lookup(query: str) -> dict:
    chairs = load_chairs()
    chair = _resolve_chair(query, chairs)
    if chair is None:
        return {"error": _NOT_FOUND_CHAIR.format(q=query)}

    result = dict(chair)
    stats = _lineup_stats()
    spec_context = {}
    for col in NUMERIC_COLUMNS:
        val = _to_number(chair[col])
        if val is None:
            continue  # [미확인] -> 컨텍스트 자체를 안 줌(추론 재료 차단)
        entry = {"value": val}
        col_stats = stats.get(col)
        if col_stats:
            entry["overall_max"] = col_stats["overall_max"]
            entry["by_성격블록_max"] = col_stats["by_성격블록_max"]
        spec_context[col] = entry
    result["spec_context"] = spec_context

    if chair["status"] in ("단종", "품절"):
        result["twin_fallback"] = twin_lookup(chair["id"])
    return result


def gear_to_acc(query: str) -> dict:
    chairs = load_chairs()
    chair = _resolve_chair(query, chairs)
    if chair is None:
        return {"error": _NOT_FOUND_CHAIR.format(q=query)}

    accessories = load_accessories()
    axes: dict[str, dict] = {}
    for axis, cfg in AXIS_CONFIG.items():
        state, norm = _cell_state(chair[cfg["column"]])
        if state == "unknown":
            axes[axis] = {"state": "데이터 없음", "matches": []}
            continue
        if state == "none":
            axes[axis] = {"state": "미지원", "matches": []}
            continue
        matches = [
            a["accessory"] for a in accessories
            if a["decision_axis"] == axis and a["parent"] == "없음" and norm in _required_values(a)
        ]
        axes[axis] = {"state": "지원", "value": norm, "matches": matches}

    # 컵홀더: 모델별 axis, required_value=해당없음 특수 케이스(join 아님, chairs.csv 직독)
    cup_state, cup_val = _cell_state(chair["cupholder"])
    if cup_state == "unknown":
        axes["컵홀더"] = {"state": "데이터 없음", "matches": []}
    elif cup_state == "none":
        axes["컵홀더"] = {"state": "미지원", "matches": []}
    else:
        axes["컵홀더"] = {"state": "지원", "value": cup_val, "matches": ["컵홀더(플라스틱)"]}

    return {"chair_id": chair["id"], "chair_name": chair["name"], "status": chair["status"], "axes": axes}


def acc_to_gear(query: str) -> dict:
    accessories = load_accessories()
    acc = _resolve_accessory(query, accessories)
    if acc is None:
        return {"error": _NOT_FOUND_ACC.format(q=query)}

    chairs = load_chairs()

    if acc["decision_axis"] == "모델별" and acc["required_value"] == "해당없음":
        matches = [
            {"id": c["id"], "name": c["name"], "cupholder": c["cupholder"]}
            for c in chairs if _cell_state(c["cupholder"])[0] == "value"
        ]
        return {"accessory": acc["accessory"], "axis": "모델별(컵홀더)", "matches": matches}

    cfg = AXIS_CONFIG.get(acc["decision_axis"])
    if cfg is None:
        return {"error": f"데이터 없음: '{acc['decision_axis']}' 축은 이번 범위 밖입니다."}

    if acc["parent"] != "없음":
        return {
            "note": f"'{acc['accessory']}'는 '{acc['parent']}'를 거쳐야 하는 2단 체결 액세서리라 "
                    "체어에 직접 연결되지 않습니다.",
            "matches": [],
        }

    required = _required_values(acc)
    matches = []
    for c in chairs:
        state, norm = _cell_state(c[cfg["column"]])
        if state == "value" and norm in required:
            matches.append({"id": c["id"], "name": c["name"], "status": c["status"]})
    return {"accessory": acc["accessory"], "axis": acc["decision_axis"], "matches": matches}


def twin_lookup(query: str) -> dict:
    chairs = load_chairs()
    chair = _resolve_chair(query, chairs)
    if chair is None:
        return {"error": _NOT_FOUND_CHAIR.format(q=query)}

    twins = load_twins()
    group_id = next((t["group_id"] for t in twins if t["member_id"] == chair["id"]), None)
    if group_id is None:
        return {"chair_id": chair["id"], "chair_name": chair["name"], "group": None,
                "note": "쌍둥이/LT 그룹 없음"}

    members = [t for t in twins if t["group_id"] == group_id]
    chairs_by_id = {c["id"]: c for c in chairs}
    member_ids = [m["member_id"] for m in members]
    result: dict = {
        "chair_id": chair["id"],
        "chair_name": chair["name"],
        "group_id": group_id,
        "members": [{"id": m["member_id"], "note": m["note"]} for m in members],
    }
    caveat = _twin_caveat(group_id, member_ids, chairs_by_id)
    if caveat is not None:
        result["caveat"] = caveat

    # LT 그룹(부모-자식, twins.csv 순서상 항상 부모가 먼저)이면 price/무게/패킹부피
    # % 차이를 실측 CSV 값으로 직접 계산 — twins.csv note 문구에 의존하지 않음.
    if group_id.startswith("LT") and len(members) == 2:
        parent = next((c for c in chairs if c["id"] == members[0]["member_id"]), None)
        child = next((c for c in chairs if c["id"] == members[1]["member_id"]), None)
        if parent and child:
            diffs = {}
            price_d = _pct_diff(parent["price_krw"], child["price_krw"])
            weight_d = _pct_diff(parent["weight_g"], child["weight_g"])
            pv_parent, pv_child = _pack_volume(parent["pack_size"]), _pack_volume(child["pack_size"])
            pack_d = round((pv_child - pv_parent) / pv_parent * 100, 1) if pv_parent and pv_child else None
            # 부호(+/-) 해석은 LLM에 맡기지 않고 rule로 확정한다 — signed % 하나만
            # 주면 LLM이 부호를 반대로 읽는 사례가 실측됨(체어제로 LT price_pct=+32.0을
            # "32% 저렴"으로 오독, eval Q10). label을 함께 주면 그 문구를 그대로 인용.
            if price_d is not None:
                diffs["price_pct_child_vs_parent"] = {
                    "pct": price_d, "label": _diff_label(price_d, "비쌈", "저렴"),
                }
            if weight_d is not None:
                diffs["weight_pct_child_vs_parent"] = {
                    "pct": weight_d, "label": _diff_label(weight_d, "무거움", "가벼움"),
                }
            if pack_d is not None:
                diffs["pack_volume_pct_child_vs_parent"] = {
                    "pct": pack_d, "label": _diff_label(pack_d, "큼", "작음"),
                }
            if diffs:
                result["parent_child_diff"] = diffs

    return result
