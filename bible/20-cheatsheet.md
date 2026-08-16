# 20장. 최종 치트시트 — 시험 직전 10분 복습용

> 전 장의 핵심을 한 장에 압축했다. 전부 26.8에서 검증된 문법이다.

## A. 테이블 생성 골격

```sql
CREATE DATABASE IF NOT EXISTS shop;

CREATE TABLE shop.events (
    event_time DateTime,
    user_id    UInt32,                     -- 음수 없으면 UInt, 최소 크기
    event_type LowCardinality(String),     -- 고유값 적은 문자열
    amount     Decimal(18, 2),             -- 돈은 Decimal
    tags       Array(String)
) ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)          -- (선택) 월 단위가 표준
ORDER BY (event_type, event_time)          -- 저카디널리티 먼저, 쿼리 패턴 따라
TTL event_time + INTERVAL 90 DAY;          -- (선택)
```

## B. 타입 선택 즉답표

| 요구 | 타입 |
|------|------|
| 개수·ID (수억 이하) | UInt32 |
| 초 단위 시각 | DateTime / 밀리초 DateTime64(3) |
| 종류 적은 문자열 | LowCardinality(String) |
| 돈 | Decimal(18,2) — sum 결과는 Decimal(38,2)! |
| 상태코드(100~599) | UInt16 |
| NULL 필요 | Nullable(T) — 비용 있음, 신중히 |

## C. 삽입 3형제

```sql
INSERT INTO t VALUES (1, 'a');
INSERT INTO t SELECT * FROM other_table WHERE ...;               -- 테이블 간
INSERT INTO t SELECT id, upper(name), price/1300                 -- 변환하며
FROM file('data.csv', 'CSVWithNames');                           -- 로컬 파일
-- s3: FROM s3('https://.../*.parquet', NOSIGN)  또는 (url,KEY,SECRET,'Parquet')
-- 구조 미리 보기: DESCRIBE file('data.csv');
```

## D. 분석 필수 함수

```sql
-- 문자열: position(s,'x')>0, s LIKE '%x%', match(s,'정규식'), replaceAll, splitByChar
-- 시간:   toStartOfHour/Day/Month, toStartOfInterval(ts, INTERVAL 15 MINUTE),
--         dateDiff('day',a,b), parseDateTimeBestEffort, formatDateTime(ts,'%Y-%m-%d')
-- 집계:   count, sum, avg, min, max
--         uniq(근사) vs uniqExact(정확)
--         quantile(0.5)(x)  ← 괄호 두 쌍!
--         argMax(a, b) = "b 최대인 행의 a" (최신값 조회)
--         topK(3)(x), groupArray(x)
-- 조건부: countIf(cond), sumIf(x, cond), multiIf(c1,v1,c2,v2,else)
-- 그룹별 상위 N: ORDER BY g, v DESC LIMIT n BY g
```

## E. Materialized View 2종 세트

```sql
-- 비집계 (필터/변환)
CREATE MATERIALIZED VIEW mv TO target AS
SELECT ... FROM src WHERE ...;
-- ⚠️ 생성 이후 INSERT만 반영 → 백필: INSERT INTO target SELECT ... FROM src;

-- 집계 (AggregatingMergeTree)
CREATE TABLE daily (
    day Date,
    users AggregateFunction(uniq, UInt32),
    total SimpleAggregateFunction(sum, UInt64)
) ENGINE = AggregatingMergeTree ORDER BY day;   -- ORDER BY = GROUP BY 키!

CREATE MATERIALIZED VIEW daily_mv TO daily AS
SELECT toDate(ts) AS day, uniqState(user_id) AS users, count() AS total
FROM src GROUP BY day;

SELECT day, uniqMerge(users), sum(total) FROM daily GROUP BY day;
-- 공식: 쓰기 = xxxState / 읽기 = xxxMerge / 단순합계 = SimpleAggregateFunction
```

## F. Projection / Skipping Index

```sql
ALTER TABLE t ADD PROJECTION p (SELECT * ORDER BY user_id);
ALTER TABLE t MATERIALIZE PROJECTION p SETTINGS mutations_sync = 1;  -- 기존 데이터 필수!

ALTER TABLE t ADD INDEX i country TYPE set(100) GRANULARITY 4;       -- 또는 TYPE minmax
ALTER TABLE t MATERIALIZE INDEX i SETTINGS mutations_sync = 1;

-- 검증: EXPLAIN indexes = 1 SELECT ... → "Granules: 읽음/전체"
-- 강제: SETTINGS force_optimize_projection = 1
```

## G. 중복 제거·수정 선택표

| 상황 | 도구 | 핵심 문법 |
|------|------|-----------|
| 최신값 upsert | ReplacingMergeTree(ver) | 조회: `FINAL` 또는 `argMax(col, ver)` + GROUP BY |
| 잦은 상태 변경 | CollapsingMergeTree(sign) | 취소행(-1)+새행(+1) / `sum(x*sign) HAVING sum(sign)>0` |
| 순서 뒤섞임 | VersionedCollapsingMergeTree(sign, ver) | |
| 소량 삭제 | `DELETE FROM t WHERE ...` | projection 있으면: `MODIFY SETTING lightweight_mutation_projection_mode='rebuild'` |
| 대량 수정/삭제 | `ALTER TABLE t UPDATE/DELETE ... WHERE ...` | `SETTINGS mutations_sync = 1` |
| 기간 만료 | `TTL` / `ALTER TABLE t DROP PARTITION 'p'` | |

## H. Dictionary

```sql
CREATE DICTIONARY d (code String, name String)
PRIMARY KEY code
SOURCE(CLICKHOUSE(TABLE 'src'))
LAYOUT(COMPLEX_KEY_HASHED())     -- UInt64 키면 HASHED()/FLAT()
LIFETIME(MIN 0 MAX 300);

SELECT dictGet('d', 'name', 'KR');
SELECT dictGetOrDefault('d', 'name', 'XX', '기본값');
```

## I. 검증·디버깅 쿼리

```sql
EXPLAIN indexes = 1 SELECT ...;                        -- 인덱스 사용 확인
SELECT count(), min(x), max(x) FROM t;                 -- 과제 후 검증 습관
DESCRIBE t;  SHOW CREATE TABLE t;
SELECT * FROM system.parts WHERE table='t' AND active; -- part/크기
SELECT * FROM system.mutations WHERE NOT is_done;      -- 뮤테이션 진행
SELECT name FROM system.functions WHERE name ILIKE '%split%';  -- 함수 찾기
```

## J. 실측된 함정 리스트 (이 책에서 직접 확인한 것)

1. `toInt8(200)` → **-56** 조용한 오버플로 → `accurateCast`로 안전 변환
2. `sum(Decimal(18,2))` 결과 타입은 **Decimal(38,2)** → MV 대상 컬럼 타입 주의
3. MV는 **생성 이후 INSERT만** 반영 → 경계 시각을 정한 백필 필수 (12장)
4. projection 있는 테이블의 lightweight DELETE는 **기본 거부** → MODIFY SETTING 'rebuild'
5. `ADD PROJECTION`/`ADD INDEX`는 신규 데이터만 → 기존 데이터는 **MATERIALIZE** 필수
6. SummingMergeTree/ReplacingMergeTree는 **merge 전 중복 공존** → GROUP BY/FINAL로 조회
7. `parseDateTimeBestEffort`는 Apache 로그 형식(`16/Aug/2026:...`) 못 읽음 → `parseDateTime` + 포맷
8. LEFT JOIN 미매칭은 NULL이 아니라 **타입 기본값**(0, '') — NULL 원하면 `join_use_nulls=1`
9. 배열 인덱스는 **1부터**
10. 한글 별칭은 백틱 필수: ``AS `이름` ``
11. CSV에 헤더 있으면 `CSV`가 아니라 **`CSVWithNames`**
12. 텍스트 포맷 스키마 추론은 Nullable(Int64)로 나옴 → 테이블은 직접 작은 타입으로 선언
13. 파라미터형 집계의 Merge에도 파라미터 반복: `quantilesMerge(0.5, 0.9)(col)` — 빠뜨리면 에러
14. **MV의 GROUP BY가 대상 ORDER BY보다 세밀하면 행이 소실된다** (에러 없음) — 키 일치 필수
15. CTE는 **참조할 때마다 재실행** — 무거운 CTE는 `AS MATERIALIZED` 고려
16. Dictionary `LIFETIME(0)` = 갱신 끔 / `MIN 0 MAX 300` = 무작위 주기 갱신 (반대로 알기 쉬움)
17. ClickHouse Cloud에서는 `file()` 불가 → s3()/url()로 대체
18. `position('대상','찾을것')` vs `locate('찾을것','대상')` — 인자 순서 반대
19. LowCardinality는 고유값 **10만 초과 시 역효과** — user_id·URL에 쓰지 말 것
20. 뮤테이션은 순차 실행 — 실패한 뮤테이션 하나가 **큐 전체를 막는다** (system.mutations 확인)
