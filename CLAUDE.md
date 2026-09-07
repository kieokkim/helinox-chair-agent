# Helinox Chair Agent — Claude Code 프로젝트 규칙

상세 규칙(응답 스타일/문서 규칙/MVP 상한)은 `.claude/rules/`에 있음.
CLAUDE.md와 별개로 자동 로드됨 (`.claude/rules/*.md`) — 이 파일은 최소
핵심(작업 프로토콜 진입점 + 안전 금지사항)만 유지한다.

## 작업 프로토콜
전문: `.claude/rules/workflow-protocol.md`

## 금지사항

- **호환 판정값 생성 금지.** ballfeet/shade_mm/groundsheet/rockingfoot/
  cupholder 값은 data/chairs.csv에 있는 것만 사용한다. 5개 컬럼 모두
  chairs.csv 헤더에 실존함(`head -1 data/chairs.csv`로 확인 가능).
  파일에 없으면 "데이터 없음"을 출력한다. 추론하지 않는다.
- **스펙 수치 생성 금지.** 무게·내하중·좌고·가격은 CSV에 없으면 비워둔다.
- 사용자 승인 전 코드 작성 금지.
- git push는 명시적 지시가 있을 때만.
- "계획이 충분하다"는 판단은 사용자만 한다.
