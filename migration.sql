-- ==========================================
-- ScreenCapture 데이터베이스 마이그레이션
-- ==========================================

-- 1. 백업 테이블 생성
CREATE TABLE captures_backup AS SELECT * FROM captures;
CREATE TABLE tags_backup AS SELECT * FROM tags;

-- 2. captures 테이블 변경
-- SQLite는 컬럼 변경 불가, 테이블 재생성 필요

-- 2-1. 새 테이블 생성
CREATE TABLE captures_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    monitor_num INTEGER NOT NULL,
    filepath TEXT,  -- NOT NULL 제거
    deleted_at DATETIME  -- 추가
);

-- 2-2. 데이터 복사 ('DELETED'를 NULL로 변환)
INSERT INTO captures_new (id, timestamp, monitor_num, filepath, deleted_at)
SELECT
    id,
    timestamp,
    monitor_num,
    CASE WHEN filepath = 'DELETED' THEN NULL ELSE filepath END,
    CASE WHEN filepath = 'DELETED' THEN CURRENT_TIMESTAMP ELSE NULL END
FROM captures;

-- 2-3. 테이블 교체
DROP TABLE captures;
ALTER TABLE captures_new RENAME TO captures;

-- 2-4. 인덱스 재생성
CREATE INDEX idx_captures_timestamp ON captures(timestamp);
CREATE INDEX idx_captures_deleted_at ON captures(deleted_at);
CREATE UNIQUE INDEX idx_captures_unique ON captures(timestamp, monitor_num);

-- 3. tags 테이블 변경

-- 3-1. 새 테이블 생성
CREATE TABLE tags_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    category TEXT NOT NULL,
    activity TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    capture_id INTEGER  -- 추가
);

-- 3-2. 데이터 복사 및 capture_id 매칭
INSERT INTO tags_new (id, timestamp, category, activity, duration_min, capture_id)
SELECT
    t.id,
    t.timestamp,
    t.category,
    t.activity,
    t.duration_min,
    (
        SELECT c.id FROM captures c
        WHERE datetime(c.timestamp) = datetime(t.timestamp)
        AND c.monitor_num = 1
        LIMIT 1
    ) as capture_id
FROM tags t;

-- 3-3. capture_id가 NULL인 레코드 확인 (orphan tags)
SELECT COUNT(*) as orphan_count FROM tags_new WHERE capture_id IS NULL;
-- 참고: NULL이 있으면 해당 레코드 수동 처리 필요

-- 3-4. 테이블 교체
DROP TABLE tags;
ALTER TABLE tags_new RENAME TO tags;

-- 3-5. 인덱스 재생성
CREATE INDEX idx_tags_timestamp ON tags(timestamp);
CREATE INDEX idx_tags_capture_id ON tags(capture_id);

-- 4. 마이그레이션 검증
SELECT 'Captures count:', COUNT(*) FROM captures;
SELECT 'Tags count:', COUNT(*) FROM tags;
SELECT 'Orphan tags:', COUNT(*) FROM tags WHERE capture_id IS NULL;
SELECT 'Deleted captures:', COUNT(*) FROM captures WHERE deleted_at IS NOT NULL;

-- 5. 백업 테이블 보관 (수동 삭제)
-- DROP TABLE captures_backup;
-- DROP TABLE tags_backup;
