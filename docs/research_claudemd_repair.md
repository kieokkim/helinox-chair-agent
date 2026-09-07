# research: CLAUDE.md 결함 수정 + .claude/rules 분리

## 1. 존재하지 않는 파일 참조 (결함 1)

- `CLAUDE.md:45` — `data/compat_table.csv`에 있는 값만 사용하라고 규정.
  이 파일은 없음 (`find data -iname "compat_table*"` → 0건).
- `data/` 실제 파일 6개: accessories.csv, chairs.csv, cots.csv, tables.csv,
  traps.csv, twins.csv (`ls data/`).
- ballfeet/shade_mm/groundsheet/rockingfoot/cupholder 5개 컬럼은
  `data/chairs.csv` 헤더 1행에 직접 존재함 (`head -1 data/chairs.csv`로 확인):
  `...,ballfeet,shade_mm,groundsheet,rockingfoot,cupholder,...`
- 같은 결함이 이미 `docs/plan_aiagent.md:61-67`에서 지적됨, 그리고
  `docs/plan_aiagent.md:177`에서 "compat_table.csv → chairs.csv 매핑: 그대로
  진행"으로 사용자 결정이 남. **그 결정이 CLAUDE.md 본문엔 반영 안 됨** —
  결정은 존재하는데 소스 파일이 안 고쳐진 상태.
- `docs/DECISION_LOG.md` 없음 (find 결과 0건) → CLAUDE.md가 요구하는
  "D번호"를 매길 곳 자체가 없음 (결함 4와 동일 원인).

## 2. `## 작업 프로토콜` 중복 (결함 2)

- `CLAUDE.md:17`과 `CLAUDE.md:56`에 같은 헤딩이 두 번 등장.
- 56번 아래 본문은 "(기존 5단계 — 변경 없음)" 자리표시자뿐 — 실제 5단계는
  17번 아래에만 있음.
- `← 신규`, `← 기존 금지사항에 1줄 추가` 편집 메모가 CLAUDE.md 본문에
  그대로 남아 있음 (파일을 검색하면 확인됨, grep 결과 생략).

## 3. `.claude/` 디렉토리 없음 (결함 3)

- `ls -la` → `.claude/` 없음.
- 루트 `rules.md`(17KB)는 헬리녹스 매장 호환 판정 규칙집 — Claude Code
  행동 규칙(CLAUDE.md/.claude)과 이름만 겹치는 별개 파일. 내용 확인 결과
  도메인 규칙집 맞음 (`head -5 rules.md`: "헬리녹스 매장 호환 규칙집").
  -> 프로젝트 규칙 파일명이 클로드 코드의 기본 규칙 파일명과 중복되지 않도록 변경할 필요

## 4. 커밋 1개, DECISION_LOG 없음 (결함 4)

- `git log --oneline --all` → `4cffce6` 단일 커밋.
- `find . -iname "DECISION_LOG*"` → 0건. `ROADMAP.md`, `NEXT_SESSION.md`도
  0건.

## 5. `.claude/rules/` 분리 방법 — 공식 문서 확인 (claude-code-guide 서브에이전트, https://code.claude.com/docs/en/memory, 2026-09-07 조회)

- **`.claude/rules/*.md`는 자동 스캔·로드됨.** 별도 `@import` 불필요.
  `paths:` YAML frontmatter로 특정 파일 접근 시에만 로드하게 범위 지정 가능.
- 로드 순서: 조직 정책 CLAUDE.md → 사용자 `~/.claude/CLAUDE.md` → 상위
  디렉토리 CLAUDE.md들 → 프로젝트 루트 `CLAUDE.md`/`.claude/CLAUDE.md` →
  `CLAUDE.local.md`. `.claude/rules/`는 이 중 프로젝트 레벨에서 launch 시
  로드 (path-scope 안 걸면).
- 대안으로 `CLAUDE.md` 안에 `@path/to/file` 인라인 문법으로 외부 파일을
  펼쳐 넣는 방식도 공식 지원 (최대 4단계 중첩). 단, 이 방식은 컨텍스트
  절감 없음 — 결국 다 펼쳐져 로드됨. `.claude/rules/`가 "여러 파일로
  쪼개서 관리"라는 이번 목적에 맞는 공식 권장 방식.

## 목표/종료조건 관련

- 이번 작업은 CLAUDE.md 프로토콜 기준 "비자명한 작업"(안전 규칙 텍스트
  수정 + 파일 구조 변경) → research 다음 단계는 plan 문서 작성, 코드
  작성 금지 상태 유지.
- MVP 상한 3줄(목표/종료조건/시작시각)은 사용자가 plan 문서에 직접 기입.
