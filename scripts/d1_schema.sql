-- Cloudflare D1 schema for 여기선 v7.0
-- 정적 JSON → 진짜 DB 마이그레이션
-- v7.0.1: D1 호환 — FOREIGN KEY 제거 (D1은 self-ref/forward-ref FK 거부)
-- 데이터 정합성은 quick_check.py로 push 전 검증

-- 1. 분리수거 룰 (765 items)
CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,                  -- snake_case key (예: notebook, pet_bottle)
  name TEXT NOT NULL,                   -- 한국어 이름
  name_en TEXT,                         -- 영어 이름 (외국인 보조)
  category TEXT NOT NULL,               -- 17 enum
  note TEXT,
  steps TEXT,                           -- JSON array
  confidence TEXT DEFAULT 'medium',
  source_url TEXT,
  source_name TEXT,
  source_grade TEXT,                    -- A / B
  feature TEXT,                         -- 환경부 부가 정보
  caution TEXT,
  last_verified TEXT,                   -- YYYY-MM-DD
  region_variation INTEGER DEFAULT 0,   -- bool
  official_classification TEXT,         -- JSON array
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);

-- 2. Alias (검색·매칭용)
CREATE TABLE IF NOT EXISTS aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id TEXT NOT NULL,                -- 앱 레벨에서 items.id 참조 (FK 제거: D1 import 호환)
  alias TEXT NOT NULL,
  alias_lower TEXT NOT NULL,            -- 검색 최적화
  source TEXT DEFAULT 'manual'          -- manual / gemini / rule / user
);

CREATE INDEX IF NOT EXISTS idx_aliases_lower ON aliases(alias_lower);
CREATE INDEX IF NOT EXISTS idx_aliases_item ON aliases(item_id);

-- 3. 시군구 (regions_meta + cityGuide)
CREATE TABLE IF NOT EXISTS regions (
  code TEXT PRIMARY KEY,                -- 5자리 행안부 코드
  name TEXT NOT NULL,
  short_name TEXT,
  parent_code TEXT,                     -- 시도 코드
  type TEXT,                            -- 시 / 구 / 군
  lat_min REAL, lat_max REAL,
  lng_min REAL, lng_max REAL,
  phone TEXT,
  official_url TEXT,
  inherits_from TEXT,                   -- 부모 코드 (덕양구 → 일산동구). FK 없음 (D1 forward-ref 거부)
  city_guide TEXT                       -- JSON (전체 cityGuide 객체)
);

CREATE INDEX IF NOT EXISTS idx_regions_parent ON regions(parent_code);
CREATE INDEX IF NOT EXISTS idx_regions_inherits ON regions(inherits_from);

-- 4. 지역 예외 룰 (region_exceptions)
CREATE TABLE IF NOT EXISTS region_exceptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  region_code TEXT NOT NULL,            -- 앱 레벨에서 regions.code 참조
  item_id TEXT NOT NULL,                -- 앱 레벨에서 items.id 참조
  category TEXT,
  note TEXT,
  steps TEXT,                           -- JSON array
  confidence TEXT,
  source_url TEXT,
  source_grade TEXT,
  UNIQUE(region_code, item_id)
);

CREATE INDEX IF NOT EXISTS idx_region_exc_region ON region_exceptions(region_code);
CREATE INDEX IF NOT EXISTS idx_region_exc_item ON region_exceptions(item_id);

-- 5. 종량제봉투 가격 (bag_prices)
CREATE TABLE IF NOT EXISTS bag_prices (
  region_code TEXT NOT NULL,
  bag_type TEXT NOT NULL,               -- general, food, recyclable
  bag_color TEXT,
  prices TEXT,                          -- JSON {3L: ..., 5L: ..., 10L: ...}
  purchase_url TEXT,
  PRIMARY KEY (region_code, bag_type)
);

-- 6. 행안부 자동 크롤링 데이터 (수거함 위치)
CREATE TABLE IF NOT EXISTS bins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  area_type TEXT NOT NULL,              -- medicine, clothes, iot, lamp, battery
  region_code TEXT,
  name TEXT,
  address TEXT,
  lat REAL,
  lng REAL,
  phone TEXT,
  last_crawled TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bins_area ON bins(area_type);
CREATE INDEX IF NOT EXISTS idx_bins_region ON bins(region_code);
CREATE INDEX IF NOT EXISTS idx_bins_location ON bins(lat, lng);

-- 7. 사용자 피드백 (Worker /feedback → D1)
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  vote TEXT NOT NULL,                   -- good / bad / wrong
  item_id TEXT,
  item_name TEXT,
  category TEXT,
  region_code TEXT,
  user_correction TEXT,
  version TEXT,
  source TEXT,
  ip_hash TEXT                          -- PII 차단, 해시만
);

CREATE INDEX IF NOT EXISTS idx_feedback_vote ON feedback(vote);
CREATE INDEX IF NOT EXISTS idx_feedback_item ON feedback(item_id);
CREATE INDEX IF NOT EXISTS idx_feedback_ts ON feedback(ts);

-- 8. 데이터 버저닝 (변경 자동 기록)
CREATE TABLE IF NOT EXISTS data_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version TEXT NOT NULL,
  changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
  area TEXT,                            -- items, regions, bins, aliases
  change_count INTEGER,
  note TEXT
);
