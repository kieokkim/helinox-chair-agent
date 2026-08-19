# research: GitHub 첫 푸시 (v3 커밋) 준비

대상: 현재 워킹 디렉터리 전체(커밋 0건, untracked 상태)를 GitHub에 처음
푸시하기 위해 필요한 파일 분류·gitignore 보완·계정/리모트 설정. 코드
변경은 포함하지 않음(협의사항 없음, 확인만).

## 1. 현재 저장소 상태

- 커밋 0건 (`git log` → "does not have any commits yet"), 로컬 브랜치 `main`.
- `git remote -v` 출력 없음 → 원격 저장소 미연결.
- `gh auth status` → 로그인 안 됨 ("not logged into any GitHub hosts").
- 즉 푸시 전 3가지가 순서대로 막혀 있음: ① GitHub 인증 ② 원격 저장소
  생성/연결 ③ 첫 커밋.

## 2. 커밋 가능 (문제 없음)

| 파일/디렉터리 | 확인 내용 |
|---|---|
| `agent_core.py`, `main.py` | grep(`api_key\|secret\|token\|password\|SUPABASE\|ANTHROPIC\|OPENAI`) 결과 코드/함수명(`_load_api_key`)만 걸림, 실제 키 문자열 없음 |
| `data/*.csv` (7개) | 제품 스펙·평가 문항 데이터, 개인정보·키 없음 |
| `rules.md`, `README.md`, `CLAUDE.md` | 문서, 민감정보 없음 (단 README는 3번 항목 참조) |
| `docs/*.md` (4개) | research/plan 문서, 민감정보 없음 |
| `tests/test_agent_core.py` | 단위 테스트, 민감정보 없음 |
| `supabase/migrations/20260818000000_init.sql` | 스키마 DDL만, 키/URL 없음 |
| `.github/workflows/supabase-keepalive.yml` | `${{ secrets.SUPABASE_URL }}` 등 GitHub Actions 시크릿 참조만, 값 자체는 없음 — **단 GitHub 저장소 Settings에 `SUPABASE_URL`/`SUPABASE_ANON_KEY` 시크릿을 미리 등록 안 하면 크론이 실패함(6번 참조)** |
| `pyproject.toml`, `uv.lock`, `.python-version` | 의존성 정의, 민감정보 없음 |
| `helinox-onboarding-v1.html` | 정적 HTML/CSS(601행), `<script>` 태그 1개 있으나 fetch/API 호출 없음(grep 확인) — 하드코딩 목업 페이지 |
| `202608_HelinoxChairAgent.code-workspace` | `{folders:["."], settings:{}}` 뿐, 절대경로·개인정보 없음 |

## 3. 커밋 절대 금지 (이미 `.gitignore`로 차단됨, 확인만)

| 파일 | 근거 |
|---|---|
| `.env` | `OPENAI_API_KEY=sk-proj-...` 실키 179바이트 그대로 있음(xxd 확인). `git check-ignore -v .env` → `.gitignore:11:.env` 매치, 정상 차단 중 |
| `.venv/` | 31MB, 로컬 가상환경. `.gitignore:10:.venv` 매치, 정상 차단 |
| `__pycache__/` | 36KB. `.gitignore:2:__pycache__/` 매치, 정상 차단 |

이 3개는 지금도 `git add .` 해도 안 걸림 — 별도 조치 불필요.

## 4. gitignore 미보완 상태 (조치 필요)

- `.DS_Store` 3개 발견: `./`, `./supabase/`, `./.git/`(이건 git 내부라 무관).
  `git check-ignore -v .DS_Store` → 매치 없음, **현재 패턴 없음 → `git add .`
  하면 그대로 커밋됨.**
- `.gitignore` 현재 내용(전체 11줄): `__pycache__/`, `*.py[oc]`, `build/`,
  `dist/`, `wheels/`, `*.egg-info`, `.venv`, `.env` 뿐 — `*.DS_Store` 패턴 없음.

## 5. README.md와 실제 저장소 상태 불일치 (판단 필요, 코드 아님)

`README.md`가 서술하는 "지금 이 폴더에 있는 것 (3개 파일)"과 실제 저장소가
어긋남:
- README는 `.env.example`을 3번째 파일로 언급하나 **저장소에 실존하지
  않음**(`find . -maxdepth 1 -name ".env*"` → `.env`만 나옴).
- README는 Next.js 로컬 실행(`.env.local`)을 전제하나, 저장소엔 Next.js
  코드가 없고 Python(`agent_core.py`/`main.py`/`uv`) 스택만 있음.
- README가 작성된 시점(0단계, supabase 스캐폴딩만 있던 때) 이후
  `agent_core.py`/`main.py`/`data/`/`rules.md`/`docs/`/`tests/`/
  `helinox-onboarding-v1.html`이 전부 추가됐는데 README는 갱신 안 된
  상태로 보임 — [미확인: README가 의도적으로 "0단계" 스냅샷만 남긴 것인지,
  단순 갱신 누락인지는 커밋 히스토리가 없어 판단 불가].

## 6. GitHub Actions 시크릿 (푸시 후 별도 조치, 코드 아님)

`.github/workflows/supabase-keepalive.yml`은 리포지토리 시크릿
`SUPABASE_URL`, `SUPABASE_ANON_KEY`를 참조(워크플로 파일:11-12). 이 값들은
**리포지토리 자체엔 없고 GitHub 웹 UI(Settings > Secrets and variables >
Actions)에서 별도 등록해야 함** — 푸시 자체는 이 등록 여부와 무관하게
성공하지만, 등록 전엔 월/금 크론이 실패함.

## 7. 확인 필요 (플랜 단계 전 사용자 판단)

1. 원격 저장소: 신규 GitHub repo 생성 필요(`gh repo create` 또는 웹에서
   생성) — 이름/공개(public)·비공개(private) 여부 미정.
   ## gh repo create 로 생성 클로드 코드에서 가능한지 확인 필요
2. `gh auth login` 미실행 상태 — 브라우저 인증 또는 토큰 중 방식 선택 필요.
  ## 브라우저 인증으로 실행
3. `.gitignore`에 `.DS_Store` 패턴 추가 여부 — 사실상 불필요 파일이라
   추가 안 할 이유는 없어 보이나, 최종 결정은 플랜에서.
   ## .DS_Store의 역할 뭔지 설명 필요
4. README.md 갱신을 이번 푸시 범위에 포함할지, 별도 세션으로 미룰지
   (CLAUDE.md "세션당 한 트랙만" 원칙과 관련 — README 갱신은 "푸시 준비"와
   다른 트랙일 수 있음).
   ## readme.md 갱신이 푸시 전 필요한 절차로 보면 범위에 포함, 아니라면 v4로 이관.
5. 첫 커밋을 단일 커밋으로 할지, CLAUDE.md 커밋 규율(feat/fix/refactor/
   docs/chore 분리)을 첫 커밋에도 적용해 여러 개로 쪼갤지 — 참고로 이
   레포는 `/Users/kieokkim/Desktop/CLAUDE.md`(상위 폴더, 다른 프로젝트용)의
   "eval 회귀 확인 후 분리 커밋" 규율과는 무관, 이 프로젝트 자체
   CLAUDE.md엔 첫 커밋 단위에 대한 명시 규칙 없음.
  ## 단일 커밋으로 진행.
