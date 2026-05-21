-- D1 reset: 기존 테이블 제거 (FK 있는 구버전 정리)
-- 사용: wrangler d1 execute yeoguiseon-db --remote --file=scripts/d1_reset.sql
-- 그 후: scripts/d1_schema.sql 실행 → data/migrations/v7_initial.sql 실행

DROP TABLE IF EXISTS region_exceptions;
DROP TABLE IF EXISTS aliases;
DROP TABLE IF EXISTS bag_prices;
DROP TABLE IF EXISTS bins;
DROP TABLE IF EXISTS feedback;
DROP TABLE IF EXISTS data_versions;
DROP TABLE IF EXISTS regions;
DROP TABLE IF EXISTS items;
