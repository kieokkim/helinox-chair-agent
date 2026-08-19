"""agent_core.py 4개 함수 단위 체크 (ponytail 규칙: 분기 로직엔 최소 1개
러너블 체크). eval_questions.csv 배치 채점(main.py --eval)과는 별개 —
여기는 함수 자체의 정확성만 본다. pytest로 실행: `uv run pytest`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent_core as ac


def test_gear_to_acc_정상값():
    # 체어원 라지: ballfeet=45(정상), shade_mm=13.0(퍼스널쉐이드 다중값 매칭),
    # groundsheet=Two(정상), rockingfoot=없음(미지원 확정)
    result = ac.gear_to_acc("체어원 라지")
    assert result["chair_id"] == "CHR1-OUT-LG"
    assert "볼핏 45mm" in result["axes"]["다리끝규격"]["matches"]
    assert "퍼스널쉐이드" in result["axes"]["폴직경"]["matches"]  # 13.0mm;14.5mm;15.6mm 중 13.0 매칭
    assert "그라운드시트 Two" in result["axes"]["풋프린트제품군"]["matches"]
    assert result["axes"]["제품군"]["state"] == "미지원"  # 없음 -> 확정 미지원, 데이터없음 아님


def test_gear_to_acc_미확인():
    # 플라야 체어: 5축 전부 [미확인] -> 전부 "데이터 없음", 추론 금지
    result = ac.gear_to_acc("플라야 체어")
    for axis in ("다리끝규격", "폴직경", "풋프린트제품군", "제품군", "컵홀더"):
        assert result["axes"][axis]["state"] == "데이터 없음"
        assert result["axes"][axis]["matches"] == []


def test_acc_to_gear_정상값():
    # 볼핏 55mm: ballfeet=55인 체어만, 45인 체어(미니)는 제외, 코트레그용(parent 있음)은 별도 함수
    result = ac.acc_to_gear("볼핏 55mm")
    ids = {m["id"] for m in result["matches"]}
    assert "CHR1-OUT-XL" in ids
    assert "CHR1-OUT-MINI" not in ids


def test_acc_to_gear_없음():
    result = ac.acc_to_gear("존재하지않는액세서리xyz")
    assert "error" in result
    assert result["error"].startswith("데이터 없음")


def test_chair_lookup_정상값_및_전라인업최고():
    # 벤치원: load_kg=190, 전 라인업(30개) 중 최고값이어야 함
    result = ac.chair_lookup("벤치원")
    assert result["status"] == "판매중"
    assert result["spec_context"]["load_kg"]["overall_max"]["value"] == 190
    assert result["spec_context"]["load_kg"]["value"] == 190


def test_chair_lookup_단종_트윈대체():
    # 캠프 체어: 단종 -> twin_fallback으로 선셋체어(TWIN1) 안내
    result = ac.chair_lookup("캠프 체어")
    assert result["status"] == "단종"
    assert result["twin_fallback"]["group_id"] == "TWIN1"


def test_chair_lookup_미확인_모델명():
    result = ac.chair_lookup("존재하지않는모델xyz")
    assert "error" in result
    assert result["error"].startswith("데이터 없음")


def test_twin_lookup_LT그룹_퍼센트차이():
    # LT1: 체어제로(부모) -> 체어제로LT(자식). price 32.0%, pack부피 48.1% 증가(실측 CSV 계산)
    # LT1은 5축 전수 실측 검증됨(twins.csv:10) -> caveat 없음(추정 아님)
    result = ac.twin_lookup("체어제로 LT")
    assert result["group_id"] == "LT1"
    assert "caveat" not in result
    assert result["parent_child_diff"]["price_pct_child_vs_parent"]["pct"] == 32.0
    assert result["parent_child_diff"]["price_pct_child_vs_parent"]["label"] == "부모보다 32.0% 비쌈"
    assert result["parent_child_diff"]["pack_volume_pct_child_vs_parent"]["pct"] == 48.1


def test_twin_lookup_LT추정_caveat():
    # LT2: 체어원(신형)->체어원LT, 볼핏만 실측·나머지 4축 상속 추정 -> rules.md 원문 그대로
    result = ac.twin_lookup("체어원 LT")
    assert result["group_id"] == "LT2"
    assert result["caveat"] == "볼핏만 실측, 나머지 4축은 상속 추정"


def test_twin_lookup_진짜쌍둥이_축비교():
    # TWIN1/2/3 전부 chairs.csv 실측 5축이 실제로 동일함을 직접 계산으로 확인
    # (twins.csv note 원문 "5축 동일" 주장과 일치 — plan_v2.md 4-3 초안은
    # BCH-OUT-STD/SPDS-OUT-STD의 cupholder 셀을 [미확인]으로 잘못 읽어
    # "4개 축만 동일"을 예상했으나, 이 테스트로 재확인한 실제 값은 둘 다
    # "없음"(chairs.csv:16,29) — 예상이 틀렸던 쪽은 plan 문서, 코드 아님).
    for query in ("선셋체어", "비치체어(re)", "체어원 미니"):
        result = ac.twin_lookup(query)
        assert result["caveat"] == "5축 전부 동일", (query, result)


def test_twin_axis_agreement_데이터부족_비교불가():
    # _twin_axis_agreement 자체를 합성 데이터로 직접 검증 — 실제 데이터엔
    # "비교불가" 사례가 없어(위 테스트) 이 분기는 별도로 확인해야 함.
    chairs_by_id = {
        "A": {"ballfeet": "45", "shade_mm": "없음", "groundsheet": "없음",
              "rockingfoot": "없음", "cupholder": "[미확인]"},
        "B": {"ballfeet": "45", "shade_mm": "없음", "groundsheet": "없음",
              "rockingfoot": "없음", "cupholder": "[미확인]"},
    }
    same, unclear = ac._twin_axis_agreement(["A", "B"], chairs_by_id)
    assert same == ["다리끝규격", "폴직경", "풋프린트제품군", "제품군"]
    assert unclear == ["컵홀더"]


def test_twin_lookup_그룹없음():
    # 그라운드 체어: twins.csv에 없는 독립 모델
    result = ac.twin_lookup("그라운드 체어")
    assert result["group"] is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK {name}")
    print("전부 통과")
