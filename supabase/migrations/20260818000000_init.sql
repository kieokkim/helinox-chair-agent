-- helinox-name-traps / 0단계 (스택 맛보기)
-- 이 파일 하나로 테이블 3개를 만든다: skus, compatibility, name_trap_tests
-- 컷 리스트에 따라 이번 단계에서 안 하는 것: RLS 정책, AI 메모 층, 승인 게이트(5상태 전환 로직)
--   -> 그래서 아래 status 칸은 값만 있고 상태를 바꾸는 기능/제약조건은 없다.

-- uuid 생성 함수(gen_random_uuid)를 쓰려면 이 확장이 켜져 있어야 한다.
-- Supabase 프로젝트는 기본으로 켜져 있는 경우가 많지만, 안전하게 한 번 더 켠다.
create extension if not exists pgcrypto;

-- ── 1. skus : 제품 4층 계층(플랫폼→디자인라인→스펙그룹→SKU) 그 자체 ──
create table if not exists skus (
  id            uuid primary key default gen_random_uuid(),

  -- 아래 3칸: 지금 이 단계에서는 안 쓴다. 나중을 위해 칸만 파둔다.
  source_id     text,               -- L0(원본 창고) 문서/페이지 연결용. 지금은 전부 NULL
  tenant_id     uuid,               -- "매장A/매장B" 구분용. 지금은 전부 NULL (컷: RLS 정책)
  status        text default 'confirmed',
                                    -- 원래는 pending/confirmed/revised/rejected/hold 5상태
                                    -- (PRODUCT_FRAMEWORK.md 4장). 지금은 승인 게이트를 안 쓰므로
                                    -- 넣는 순간 전부 'confirmed'로 고정.

  platform      text not null,      -- 4층 계층 1층
  design_line   text not null,      -- 2층
  spec_group    text not null,      -- 3층
  sku_code      text not null unique, -- 4층 (예: HLX-TC-001)
  display_name  text not null,
  aliases       text[] default '{}', -- 헷갈리는 다른 이름들. 이름 함정 11건의 재료가 되는 칸
  created_at    timestamptz default now()
);

-- ── 2. compatibility : 두 SKU가 서로 맞는지/안 맞는지 ──
create table if not exists compatibility (
  id            uuid primary key default gen_random_uuid(),

  source_id     text,
  tenant_id     uuid,
  status        text default 'confirmed',

  sku_a_id      uuid not null references skus(id),
  sku_b_id      uuid not null references skus(id),
  compatible    boolean not null,
  reason        text,               -- "왜 맞는지/안 맞는지" 한 줄 근거
  created_at    timestamptz default now()
);

-- ── 3. name_trap_tests : 정답지 시험(골든셋) 11건이 들어갈 자리 ──
-- 통과 조건 "11/11 정답"을 자동으로 채점하기 위한 테이블.
-- 지금은 구조만 만들고, 실제 11건 내용은 비어 있다 (내가 갖고 있지 않은 데이터라 임의로 채우지 않았다).
create table if not exists name_trap_tests (
  id                serial primary key,
  query_text        text not null,       -- 검색창에 넣을 문장 (예: "우드랜드 폴대")
  expected_sku_id   uuid references skus(id), -- 정답 SKU
  trap_description  text,                -- 왜 헷갈리는지 (이름 함정의 정체)
  created_at        timestamptz default now()
);

-- 검색창 1개가 sku_code / display_name / aliases 로 찾을 수 있게 인덱스만 걸어둔다.
create index if not exists idx_skus_sku_code on skus (sku_code);
create index if not exists idx_skus_aliases on skus using gin (aliases);
