# 11장. 함수 레퍼런스 ② — 집계 함수와 윈도우 함수

> 시험 영역 3의 핵심: "use aggregate functions (max/min/sum/avg,
> number of unique values, quantiles)". 전부 26.8 실측 검증.

## 11.1 기본 집계 5인방

```sql
SELECT
    count(),            -- 행 수 (count(*) 동일)
    count(col),         -- col이 NULL 아닌 행 수
    sum(amount),
    avg(amount),
    min(amount), max(amount)
FROM sales;
```

## 11.2 고유값 세기 — uniq 삼형제 ★ (시험 명시)

```sql
SELECT
    uniq(user_id),        -- 근사치 (적응적 샘플링, 해시 샘플 최대 65,536) — 빠르고 메모리 상한 고정
    uniqExact(user_id),   -- 정확 — 메모리 많이 씀
    uniqCombined(user_id) -- 근사치 개선판 (메모리↓ 정확도↑, 결과가 결정론적)
FROM events;

-- count(DISTINCT x)도 쓸 수 있다 — 내부적으로 uniqExact로 실행된다 (기본 설정)
SELECT count(DISTINCT user_id) FROM events;
-- 메모리를 아끼려면: SET count_distinct_implementation = 'uniqCombined';
```

실측 (1,000만 행, 실제 고유값 10만):

| 함수 | 결과 | 오차 |
|------|------|------|
| `uniq` | 100,315 | ~0.3% |
| `uniqExact` | 100,000 | 0 |

**문제가 "정확한(exact) 고유 수"라고 하면 uniqExact, "대략/빠르게"면 uniq.**
대시보드는 uniq, 과금·정산은 uniqExact가 관례다.

## 11.3 분위수 — quantile ★ (시험 명시)

```sql
SELECT
    quantile(0.5)(duration_ms)          AS median,     -- 근사 중위값
    quantile(0.95)(duration_ms)         AS p95,
    quantileExact(0.9)(duration_ms)     AS p90_exact,  -- 정확 버전
    quantiles(0.5, 0.9, 0.99)(duration_ms) AS ps,      -- 한 번에 여러 개 → 배열
    median(duration_ms)                                 -- quantile(0.5) 별칭
FROM events;
```

**괄호 두 쌍 문법에 주의**: `quantile(레벨)(컬럼)`. 첫 괄호는 파라미터, 둘째가 인자다.

## 11.4 argMax / argMin ★★ (자격증 단골)

"B가 최대일 때의 A" — 최신값 조회의 표준 도구.

```sql
-- 가장 최근(updated_at 최대) 행의 plan 값
SELECT argMax(plan, updated_at) FROM user_profiles;

-- 가장 비싼 상품의 이름
SELECT argMax(name, price) FROM products;

-- ReplacingMergeTree 중복 제거 콤보 (14장, 검증됨)
SELECT user_id, argMax(email, updated_at), max(updated_at)
FROM user_profiles GROUP BY user_id;
```

## 11.5 그 외 자주 쓰는 집계

```sql
SELECT
    any(name),                  -- 그룹에서 아무 값 하나 (순서 비보장)
    topK(3)(product),           -- 대략적 최빈값 상위 3개 → 배열 (검증됨)
    groupArray(url),            -- 그룹의 값을 배열로 수집
    groupUniqArray(url),        -- 고유값만 배열로
    corr(x, y), stddevPop(x)    -- 통계
FROM t GROUP BY ...;
```

## 11.6 Combinator — 집계 함수의 접미사 마법 ★

ClickHouse 고유의 강력한 체계. **아무 집계 함수 뒤에 접미사를 붙여 변형**한다.

| 접미사 | 효과 | 예 |
|--------|------|----|
| `-If` | 조건 만족 행만 집계 | `countIf(status = 'error')`, `sumIf(amount, country = 'KR')` |
| `-Distinct` | 고유값만 집계 | `sumDistinct(x)` |
| `-Array` | 배열 원소를 풀어서 집계 | `sumArray(tags_lengths)` |
| `-State` | 중간 상태 반환 (12장 MV용) | `uniqState(user_id)` |
| `-Merge` | 중간 상태를 최종값으로 | `uniqMerge(users)` |
| `-OrDefault` / `-OrNull` | 빈 입력이면 기본값/NULL | `avgOrDefault(x)` → 0 (avg는 원래 nan), `sumOrNull(x)` |

여러 개를 붙일 때는 순서 규칙이 있다 — 공식 문구: **Array가 If보다 먼저**.
`uniqArrayIf(arr, cond)` ⭕ / `uniqIfArray` ❌.

`-If`는 "피벗" 쿼리의 핵심이다 (검증됨):

```sql
-- 한 쿼리로 여러 조건의 집계를 나란히 (WHERE로 나누면 3번 스캔할 것을 1번에)
SELECT
    toDate(ts)                        AS day,
    countIf(event_type = 'view')      AS views,
    countIf(event_type = 'purchase')  AS purchases,
    sumIf(amount, country = 'KR')     AS kr_revenue
FROM events
GROUP BY day;
```

## 11.7 GROUP BY 확장 (26.8 검증)

```sql
-- ROLLUP: 소계 + 총계 행 추가 (빈 문자열/0으로 표시되는 행이 합계)
SELECT region, sum(amount) FROM sales GROUP BY region WITH ROLLUP;
-- Busan | 380
-- Seoul | 350
--       | 730   ← 총계

SELECT a, b, sum(x) FROM t GROUP BY a, b WITH CUBE;    -- 모든 조합의 소계
SELECT region, sum(amount) FROM sales GROUP BY region WITH TOTALS;  -- 총계를 별도 블록으로
```

## 11.8 윈도우 함수 — 행을 유지하며 집계

GROUP BY는 행을 요약해 **줄이지만**, 윈도우 함수는 **행을 그대로 두고**
옆에 집계 결과를 붙인다.

```sql
집계함수/순위함수 OVER (
    PARTITION BY 그룹기준     -- 생략 시 전체가 한 그룹
    ORDER BY 정렬기준
    [ROWS BETWEEN ... AND ...] -- 프레임 (계산 범위)
)
```

### 순위 (26.8 검증)

```sql
SELECT
    name, score,
    row_number() OVER (ORDER BY score DESC) AS rn,     -- 1,2,3,4 (동점도 다른 번호)
    rank()       OVER (ORDER BY score DESC) AS rnk,    -- 1,2,2,4 (동점 같은 순위, 건너뜀)
    dense_rank() OVER (ORDER BY score DESC) AS drnk    -- 1,2,2,3 (건너뛰지 않음)
FROM students;

-- 그룹별 순위: PARTITION BY 추가
row_number() OVER (PARTITION BY class ORDER BY score DESC)
```

### 누적합·이동평균 (26.8 검증)

```sql
SELECT
    day, sales,
    sum(sales) OVER (ORDER BY day)  AS running_total,   -- 누적합
    avg(sales) OVER (
        ORDER BY day
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS moving_avg_3                                    -- 3일 이동평균
FROM daily_sales;
```

누적합이 "저절로" 되는 이유 — 프레임 기본값 규칙:
**ORDER BY가 있으면 기본 프레임이 `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`**
(처음~현재 행)라서 sum이 자동으로 누적이 된다. ORDER BY가 없으면 파티션 전체가 프레임.

그 외 순위·분포 함수: `first_value(x) OVER w`, `last_value(x) OVER w`,
`ntile(4) OVER (ORDER BY x)`(4분위), `percent_rank()`.

### 이전/다음 행 참조

```sql
SELECT
    day, sales,
    lagInFrame(sales, 1)  OVER w AS prev_day,   -- 이전 행 값
    leadInFrame(sales, 1) OVER w AS next_day,   -- 다음 행 값
    sales - lagInFrame(sales, 1) OVER w AS diff -- 전일 대비 증감
FROM daily_sales
WINDOW w AS (ORDER BY day ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING);
```

(`lag`/`lead`도 정식 지원되며 이쪽은 프레임을 항상 무시한다 — 프레임 지정 없이
바로 쓸 수 있다. `lagInFrame`/`leadInFrame`은 프레임을 **존중**하므로 lag처럼
쓰려면 위처럼 UNBOUNDED 프레임을 명시해야 한다. `WINDOW 절`로 공통 윈도우에
이름을 붙이면 깔끔하다.)

## 11.9 GROUP BY vs 윈도우 — 선택 기준

| 질문 | 도구 |
|------|------|
| "국가별 매출 합계는?" (요약만 필요) | GROUP BY |
| "각 주문에 그 국가의 매출 비중을 붙여라" (행 유지) | 윈도우 |
| "누적/이동/전일 대비" | 윈도우 |
| "그룹별 상위 N행" | `LIMIT n BY` (9장) 또는 row_number 필터 |
