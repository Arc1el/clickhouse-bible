# 19장. 모의고사 — 실전 형식 12과제

> 실제 시험과 동일하게 **과제 수행형**이다. 2시간 타이머를 켜고, 공식 문서만 참고하며
> 풀어볼 것. 모든 해답은 ClickHouse 26.8 `clickhouse local`에서 검증되었다.

## 준비: 실습 데이터 만들기

작업 폴더에 아래 CSV 파일을 만든다 (`events.csv`):

```csv
event_time,user_id,event_type,page_url,duration_ms,country
2026-08-01 09:00:00,101,view,/home,340,KR
2026-08-01 09:01:12,101,view,/products/1,1200,KR
2026-08-01 09:02:30,102,view,/home,220,US
2026-08-01 09:05:00,102,purchase,/checkout,4500,US
2026-08-01 10:00:00,103,view,/products/2,800,JP
2026-08-02 11:00:00,101,purchase,/checkout,3200,KR
2026-08-02 11:30:00,104,view,/home,150,US
2026-08-02 12:00:00,104,view,/products/1,950,US
```

세션을 유지하려면(테이블이 사라지지 않게) `--path`로 데이터 디렉토리를 지정해 실행한다:

```bash
./clickhouse local --path ./mock_exam_data
```

---

## 과제 (먼저 풀어보기)

**[과제 1 — 데이터 모델링]** `shop` 데이터베이스를 만들고, 위 CSV 구조에 맞는
`shop.events` 테이블을 만들어라. 조건: ① 각 컬럼에 가장 효율적인 타입을 쓸 것
(`event_type`과 `country`는 종류가 적은 문자열이다) ② 주요 쿼리가
"특정 event_type의 시간 범위 조회"이므로 이에 맞는 ORDER BY를 정할 것.

**[과제 2 — 파일 삽입]** `events.csv`를 `shop.events`에 삽입하라. (헤더 있음에 주의)

**[과제 3 — 삽입 중 변환]** `shop.events_clean` 테이블을 만들되 `duration_ms` 대신
초 단위 `duration_sec Float32` 컬럼을 두고, CSV에서 읽으며 ① ms→초 변환
② `page_url` 소문자화를 적용해 삽입하라.

**[과제 4 — 분석: 문자열/시간]** URL이 `/products/`로 시작하는 조회(view)를
**시간(hour) 단위**로 집계하라.

**[과제 5 — 분석: 집계]** 국가별로 ① 정확한 고유 사용자 수 ② 체류시간 중위값(p50)을 구하라.

**[과제 6 — 비집계 MV]** `purchase` 이벤트만 실시간으로 복사되는 Materialized View와
대상 테이블 `shop.purchases`를 만들어라. 새 purchase를 INSERT해서 자동 반영을 확인하라.

**[과제 7 — 집계 MV]** 일자별 ① 고유 사용자 수 ② 이벤트 수를 저장하는
`AggregatingMergeTree` 테이블 + MV를 만들어라. 조회 쿼리까지 작성할 것.

**[과제 8 — Projection]** `shop.events`는 `event_type` 기준으로 정렬돼 있어
`user_id` 검색이 느리다. `user_id`로 정렬된 projection을 추가하고 기존 데이터에
적용(materialize)하라.

**[과제 9 — Skipping Index]** `country` 컬럼에 `set` 타입 skipping index를 추가하고
기존 데이터에 적용하라.

**[과제 10 — Lightweight DELETE]** 사용자 104의 이벤트를 lightweight delete로 지워라.
(힌트: 과제 8에서 projection을 만들었다면 그냥은 안 된다 — 왜 안 되는지, 어떻게
해결하는지가 진짜 문제다.)

**[과제 11 — ReplacingMergeTree]** 사용자 프로필(`user_id, email, plan, updated_at`)을
upsert 방식으로 관리하는 테이블을 만들어라. 같은 user_id로 두 번 INSERT한 뒤
**최신 값만** 조회하는 쿼리를 두 가지 방법(FINAL, argMax)으로 작성하라.

**[과제 12 — CollapsingMergeTree]** 장바구니 현재 상태(`user_id, item_count, total`)를
CollapsingMergeTree로 관리하라. 상태 변경(2개 15,000원 → 3개 22,000원) 시나리오를
수행하고 현재 상태를 올바르게 집계하는 쿼리를 작성하라.

---

## 해답

### 과제 1 — 데이터베이스와 테이블

```sql
CREATE DATABASE shop;

CREATE TABLE shop.events (
    event_time  DateTime,
    user_id     UInt32,
    event_type  LowCardinality(String),
    page_url    String,
    duration_ms UInt32,
    country     LowCardinality(String)
) ENGINE = MergeTree
ORDER BY (event_type, event_time);
```

채점 포인트:
- `user_id`, `duration_ms`: 음수가 없으므로 **UInt** 계열. 42억까지 충분하면 UInt32.
- `event_type`, `country`: 고유값이 적은 문자열 → **LowCardinality(String)**.
- ORDER BY는 쿼리 패턴("특정 event_type의 시간 범위") 그대로 `(event_type, event_time)` —
  **카디널리티 낮은 컬럼을 앞에**.

### 과제 2 — CSV 삽입

```sql
INSERT INTO shop.events
SELECT * FROM file('events.csv', 'CSVWithNames');

SELECT count() FROM shop.events;   -- 8
```

헤더가 있으므로 포맷은 `CSV`가 아니라 **`CSVWithNames`**. (clickhouse local에서는
현재 디렉토리 기준 상대 경로, 서버에서는 `user_files` 디렉토리 기준이다.)

### 과제 3 — 삽입 중 변환

```sql
CREATE TABLE shop.events_clean (
    event_time   DateTime,
    user_id      UInt32,
    event_type   LowCardinality(String),
    page_url     String,
    duration_sec Float32,
    country      LowCardinality(String)
) ENGINE = MergeTree
ORDER BY event_time;

INSERT INTO shop.events_clean
SELECT
    event_time,
    user_id,
    event_type,
    lower(page_url),
    duration_ms / 1000,
    country
FROM file('events.csv', 'CSVWithNames');
```

`INSERT INTO ... SELECT`가 "삽입 중 변환"의 표준 패턴이다. SELECT 절에서
이름 변경·타입 변환·계산을 전부 처리한다.

### 과제 4 — 문자열 검색 + 시간 버킷

```sql
SELECT
    toStartOfHour(event_time) AS hour,
    count() AS product_views
FROM shop.events
WHERE page_url LIKE '/products/%'
  AND event_type = 'view'
GROUP BY hour
ORDER BY hour;
```

```text
2026-08-01 09:00:00 | 1
2026-08-01 10:00:00 | 1
2026-08-02 12:00:00 | 1
```

`LIKE '/products/%'` 대신 `startsWith(page_url, '/products/')`도 정답.

### 과제 5 — 집계

```sql
SELECT
    country,
    uniqExact(user_id)          AS users,
    quantile(0.5)(duration_ms)  AS median_ms
FROM shop.events
GROUP BY country
ORDER BY users DESC;
```

```text
US | 2 | 585
KR | 1 | 1200
JP | 1 | 800
```

"정확한" 고유 수를 요구하면 `uniq`(근사)가 아니라 **`uniqExact`**.
분위수 함수의 문법은 `quantile(0.5)(컬럼)` — 괄호가 두 쌍이다.

### 과제 6 — 비집계 Materialized View

```sql
CREATE TABLE shop.purchases (
    event_time DateTime,
    user_id    UInt32,
    page_url   String
) ENGINE = MergeTree
ORDER BY event_time;

CREATE MATERIALIZED VIEW shop.purchases_mv
TO shop.purchases AS
SELECT event_time, user_id, page_url
FROM shop.events
WHERE event_type = 'purchase';

-- 확인: 새 purchase 삽입 → 자동 반영
INSERT INTO shop.events VALUES
    ('2026-08-03 09:00:00', 105, 'purchase', '/checkout', 2100, 'KR');

SELECT count() FROM shop.purchases;   -- 1
```

⚠️ **MV는 생성 이후의 INSERT에만 반응한다.** 기존 8행의 purchase 2건은 자동으로
들어가지 않는다. 기존 데이터까지 채우려면(백필):

```sql
INSERT INTO shop.purchases
SELECT event_time, user_id, page_url
FROM shop.events WHERE event_type = 'purchase';
```

### 과제 7 — 집계 MV (AggregatingMergeTree)

```sql
CREATE TABLE shop.daily_users (
    day          Date,
    users        AggregateFunction(uniq, UInt32),
    events_count SimpleAggregateFunction(sum, UInt64)
) ENGINE = AggregatingMergeTree
ORDER BY day;

CREATE MATERIALIZED VIEW shop.daily_users_mv
TO shop.daily_users AS
SELECT
    toDate(event_time) AS day,
    uniqState(user_id) AS users,
    count()            AS events_count
FROM shop.events
GROUP BY day;

-- 조회: State로 저장한 것은 반드시 Merge로 읽는다
SELECT
    day,
    uniqMerge(users)  AS unique_users,
    sum(events_count) AS total_events
FROM shop.daily_users
GROUP BY day
ORDER BY day;
```

채점 포인트:
- 쓰기: `uniqState(...)` / 읽기: `uniqMerge(...)` — **State↔Merge 쌍**.
- 단순 합계는 `SimpleAggregateFunction(sum, UInt64)`로 충분 (조회 시 그냥 `sum()`).
- 대상 테이블의 `ORDER BY day` = MV의 `GROUP BY day` (일치해야 병합 시 올바르게 합쳐진다).

### 과제 8 — Projection

```sql
ALTER TABLE shop.events
    ADD PROJECTION by_user (SELECT * ORDER BY user_id);

-- 기존 데이터에 적용 (mutations_sync=1: 완료까지 대기)
ALTER TABLE shop.events
    MATERIALIZE PROJECTION by_user
    SETTINGS mutations_sync = 1;

-- projection이 실제 쓰이는지 강제 확인
SELECT count() FROM shop.events
WHERE user_id = 101
SETTINGS force_optimize_projection = 1;
```

`ADD PROJECTION`은 **이후 삽입분에만** 적용된다. 기존 part에 소급하려면
`MATERIALIZE PROJECTION`이 필수 — 시험 단골 함정.

### 과제 9 — Skipping Index

```sql
ALTER TABLE shop.events
    ADD INDEX country_idx country TYPE set(100) GRANULARITY 4;

ALTER TABLE shop.events
    MATERIALIZE INDEX country_idx
    SETTINGS mutations_sync = 1;

SELECT count() FROM shop.events WHERE country = 'JP';
```

`set(100)`: granule마다 고유값을 최대 100개까지 저장, 초과 시 그 granule은 스킵 불가.
projection과 마찬가지로 기존 데이터에는 `MATERIALIZE INDEX`가 필요하다.

### 과제 10 — Lightweight DELETE (+ 함정)

```sql
DELETE FROM shop.events WHERE user_id = 104;
```

과제 8의 projection이 있으면 이 쿼리는 **에러가 난다**:

```text
Code: 344. DB::Exception: DELETE query is not allowed for table shop.events
because as it has projections and setting lightweight_mutation_projection_mode
is set to THROW.
```

해결(택1):

```sql
-- ① 테이블 설정을 바꾼다 (rebuild: 삭제 후 projection 재구축, drop: projection 폐기)
ALTER TABLE shop.events
    MODIFY SETTING lightweight_mutation_projection_mode = 'rebuild';
DELETE FROM shop.events WHERE user_id = 104;

-- ② 뮤테이션 방식 DELETE를 쓴다 (projection 있어도 동작)
ALTER TABLE shop.events DELETE WHERE user_id = 104
SETTINGS mutations_sync = 1;
```

### 과제 11 — ReplacingMergeTree upsert

```sql
CREATE TABLE shop.user_profiles (
    user_id    UInt32,
    email      String,
    plan       LowCardinality(String),
    updated_at DateTime
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY user_id;

INSERT INTO shop.user_profiles VALUES
    (101, 'a@x.com', 'free', '2026-08-01 00:00:00');
INSERT INTO shop.user_profiles VALUES
    (101, 'a@x.com', 'pro',  '2026-08-05 00:00:00');

-- 방법 1: FINAL (간편, 소규모에 적합)
SELECT * FROM shop.user_profiles FINAL;

-- 방법 2: argMax (대규모에서 더 예측 가능)
SELECT
    user_id,
    argMax(email, updated_at) AS email,
    argMax(plan,  updated_at) AS plan,
    max(updated_at)           AS updated_at
FROM shop.user_profiles
GROUP BY user_id;
```

두 방법 모두 `plan = 'pro'`(2026-08-05 버전)를 돌려준다. 핵심 이해:
**중복 제거는 백그라운드 merge 시점에 일어나므로, merge 전에는 두 행이 공존한다.**
그래서 조회 시 FINAL 또는 argMax로 "읽기 시점 중복 제거"를 해야 한다.

### 과제 12 — CollapsingMergeTree

```sql
CREATE TABLE shop.cart_state (
    user_id    UInt32,
    item_count UInt32,
    total      UInt32,
    sign       Int8
) ENGINE = CollapsingMergeTree(sign)
ORDER BY user_id;

-- 최초 상태: 2개 15,000원
INSERT INTO shop.cart_state VALUES (201, 2, 15000, 1);

-- 상태 변경: 이전 상태 취소(-1) + 새 상태(+1)를 한 번에
INSERT INTO shop.cart_state VALUES
    (201, 2, 15000, -1),
    (201, 3, 22000, 1);

-- 현재 상태 조회: sign을 곱해서 집계
SELECT
    user_id,
    sum(item_count * sign) AS item_count,
    sum(total * sign)      AS total
FROM shop.cart_state
GROUP BY user_id
HAVING sum(sign) > 0;
```

```text
201 | 3 | 22000
```

채점 포인트: ① 취소 행은 **원본과 완전히 같은 값 + sign=-1** ② 조회는
`sum(값 * sign)` + `HAVING sum(sign) > 0` 패턴 ③ merge 전에도 결과가 정확하다.

---

## 자기 채점 기준

| 점수 | 판정 |
|------|------|
| 12개 중 9개 이상을 문서만 보고 완주 | 실전 응시 준비 완료 |
| 6~8개 | 13~16장(최적화·중복제거) 복습 후 재도전 |
| 5개 이하 | 5~12장부터 손으로 다시 실습 |

실전 팁: 시험도 이 모의고사처럼 **앞 과제의 결과물(테이블) 위에 뒤 과제가 쌓이는**
구조일 수 있다. 과제 순서대로 차분히, 각 과제 후 `SELECT count()`로 검증하는 습관을 들일 것.
