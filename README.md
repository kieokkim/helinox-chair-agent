# helinox-name-traps — 0단계 (스택 맛보기)

## 지금 이 폴더에 있는 것 (3개 파일)
1. `supabase/migrations/20260818000000_init.sql` — 테이블 3개(skus, compatibility, name_trap_tests)
2. `.github/workflows/supabase-keepalive.yml` — 7일 무활동 정지 방지 크론
3. `.env.example` — 키 넣을 빈칸

## 실행 순서

### 1. Supabase 프로젝트 만들기
supabase.com 에서 새 프로젝트 생성 (무료 한도: 프로젝트 2개, DB 500MB/프로젝트 — 이번 건으로 1개 씀, 1개 남음)

### 2. 마이그레이션 적용
로컬에 Supabase CLI가 있으면:
```
supabase link --project-ref <프로젝트 ref>
supabase db push
```
CLI 없이 빠르게 하려면: Supabase 대시보드 > SQL Editor 에 `20260818000000_init.sql` 내용을 그대로 붙여넣고 Run.

### 3. 키 채우기
Supabase 대시보드 > Settings > API 에서 `Project URL`, `anon public` 키 복사 →
- 로컬 `.env.example`을 `.env.local`로 복사해서 채우기 (Next.js 실행용)
- GitHub 저장소 Settings > Secrets and variables > Actions 에 `SUPABASE_URL`, `SUPABASE_ANON_KEY` 로 똑같이 등록 (크론 실행용)

### 4. 크론 확인
저장소 Actions 탭 > supabase-keepalive > Run workflow 눌러서 수동 1회 실행 → `status=200` 나오면 정상.
평소엔 월/금 자동 실행이라 손댈 일 없음.

## 이번 단계에서 일부러 안 넣은 것 (컷 리스트)
로그인 / RLS 정책 / AI 메모 층 / 승인 게이트 / 디자인 / 결제
→ `tenant_id`, `status` 칸은 있지만 지금은 강제하는 코드가 없다 (자리만 파둔 상태).

## 아직 비어 있는 것
`name_trap_tests` 테이블에 이름 함정 11건이 0건 들어있음.
통과 조건(11/11 정답)을 확인하려면 이 11건 + `skus` 실제 제품 데이터를 채워야 함 — 다음 단계에서.
