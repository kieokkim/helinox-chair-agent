목표:      GitHub에 이 레포를 처음 푸시한다. 민감정보(.env 등) 유출 없이,
           단일 커밋으로 private repo에 안전하게 올린다.
종료 조건: 산출물 3개(gitignore 보완 커밋 포함 단일 커밋 1건 / GitHub repo
           `helinox-chair-agent`(private) 생성 1건 / `git push` 성공 1건)
           전부 완료되면 종료.
시작 시각: (구현 진입 시 date로 기록)

# plan: GitHub 첫 푸시 (v3)

research(`docs/research_push_v3.md`) 사용자 인라인 메모 반영. 결정된 값:
repo명 `helinox-chair-agent`, 공개범위 private, gh 인증방식 브라우저,
첫 커밋 단일 커밋, README 갱신 여부는 아래 5번에서 이번 판단.

## 1. 수정 파일

- `.gitignore` (기존 파일 수정, 1줄 추가): `.DS_Store` 패턴 추가.
  근거: research 4번 — 현재 11줄 안에 `*.DS_Store` 패턴 없음, 3개 파일이
  `git check-ignore` 안 걸림. macOS Finder가 폴더 열 때마다 자동 생성하는
  뷰 설정 캐시(아이콘 위치·창크기)일 뿐 앱 동작과 무관 — 표준적으로
  gitignore 대상. 기존 `.DS_Store` 파일 자체(3개)는 삭제하지 않음(로컬
  Finder 캐시, 지워도 다음 Finder 접근 시 재생성돼 실익 없음 — ignore만
  하면 커밋 대상에서 빠짐, 그걸로 충분).
- 그 외 신규/수정 파일 없음. `docs/research_push_v3.md` 자체도 이번
  커밋에 포함(문서 산출물).

## 2. 실행 단계

### (A) GitHub 인증 — 사용자 실행 (Claude가 대신 못 함, 대화형 브라우저 인증)

```
! gh auth login --web
```

`!` 접두사로 이 세션에서 직접 실행 → 브라우저 열리고 8자리 코드 표시 →
GitHub 웹에서 승인. Claude Code는 non-TTY라 대화형 로그인 프롬프트를 못
받으므로 이 단계만 사용자가 직접 실행.

### (B) `.gitignore`에 `.DS_Store` 패턴 추가 — Claude 실행

기존 파일 1줄 추가(Edit). 근거는 위 1번.

### (C) 단일 커밋 생성 — Claude 실행 (실행 전 파일 목록 최종 확인)

`git add .` 후 아래 파일들이 스테이징됐는지 확인(research 2번 표와 동일,
`.env`/`.venv`/`__pycache__`/`.DS_Store` 미포함 확인):

```
.github/workflows/supabase-keepalive.yml
.gitignore
.python-version
202608_HelinoxChairAgent.code-workspace
CLAUDE.md
README.md
agent_core.py
data/*.csv (7개)
docs/*.md (research_push_v3.md 포함 전체)
helinox-onboarding-v1.html
main.py
pyproject.toml
rules.md
supabase/migrations/20260818000000_init.sql
tests/test_agent_core.py
uv.lock
```

커밋 메시지(단일 커밋, Conventional Commits 형식):
`chore: initial commit — helinox chair agent v3`

### (D) GitHub repo 생성 — Claude 실행 (실행 직전 최종 확인만, 이름/공개범위는 이미 확정)

```
gh repo create helinox-chair-agent --private --source=. --remote=origin
```

`--source=.` → 현재 로컬 git repo 기준으로 생성, `origin` 리모트 자동 등록.
`--push` 플래그는 안 씀 — (C)에서 이미 커밋 만들어둔 뒤 (E)에서 직접
push해 실패 시 단계 구분이 명확하게.

### (E) 푸시 — Claude 실행

```
git push -u origin main
```

## 3. 이번 범위 밖 (research 7번 판단, 사용자 조건부 위임 반영)

- **README.md 갱신**: research 5번이 지적한 실제 상태와의 불일치
  (`.env.example` 언급하나 미실존, Next.js 전제하나 실제론 Python 스택)는
  **git push 성공 여부와 무관** — GitHub은 README 내용을 검증하지 않음,
  푸시 전 필요한 절차가 아님. 판단: **이번 범위 제외, v4로 이관.**
  (사용자 조건: "푸시 전 필요한 절차로 보면 포함, 아니면 v4로 이관" — 절차성
  검토 결과 불필요로 판단)
- **GitHub Actions 시크릿 등록** (`SUPABASE_URL`/`SUPABASE_ANON_KEY`):
  GitHub 웹 UI(Settings > Secrets and variables > Actions)에서 등록하는
  수동 작업, `gh`/git 명령으로 자동화 대상 아님. 푸시 후 사용자가 직접
  등록. 이번 플랜은 "푸시 성공"까지가 종료 조건이라 범위 밖 — 안내만.

## 4. 트레이드오프

- `gh repo create --source=.`는 로컬에 커밋이 없어도 실행 가능하지만,
  이번엔 (C)를 먼저 끝내 "커밋 실패"와 "repo 생성 실패"를 단계별로 분리
  — 실패 시 어느 단계인지 바로 알 수 있음. 대신 단계가 1개 더 늘어남
  (커밋 → repo 생성 → push, 총 3 커맨드). `--push`로 한 번에 묶으면
  1커맨드로 줄지만 실패 원인 분리가 안 됨 — 이번엔 안전한 쪽 선택.
- `.DS_Store` 3개 파일 자체는 삭제 안 하고 gitignore만 함 — 삭제하면
  다음 Finder 접근 시 재생성되므로(실익 없음), ignore가 더 적은 조치로
  같은 결과(커밋 미포함)를 얻음.
