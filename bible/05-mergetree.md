# 5장. MergeTree — ClickHouse의 심장

> ClickHouse의 실전 테이블은 사실상 전부 MergeTree 계열이다. 시험의 모든 과제가
> MergeTree 위에서 벌어진다. **이 장을 이해하면 ClickHouse의 절반을 이해한 것이다.**

## 5.1 기본 문법

```sql
CREATE TABLE events (
    event_time DateTime,
    user_id    UInt32,
    event_type LowCardinality(String),
    url        String
) ENGINE = MergeTree
ORDER BY (event_type, event_time);   -- MergeTree는 ORDER BY가 사실상 필수
```

- `ENGINE = MergeTree` — 기본이자 대표 엔진
- `ORDER BY (...)` — **디스크에 데이터를 어떤 순서로 정렬해 둘지**. 성능의 90%가 여기서 결정된다(6장)
- 정렬이 정말 필요 없으면 `ORDER BY tuple()` (빈 정렬)

## 5.2 이름의 의미: "Merge" + "Tree"

MergeTree의 동작 원리는 세 문장으로 요약된다:

1. **INSERT 한 번 = 디스크에 part(조각) 하나 생성.** part는 ORDER BY 순서로 정렬된,
   **불변(immutable)** 데이터 묶음이다.
2. part가 쌓이면 백그라운드에서 여러 part를 **병합(merge)**해 더 큰 part 하나로 만든다
   (이때도 정렬 유지).
3. 쿼리는 활성 part들을 병렬로 읽는다.

직접 확인해 보자 (실측 결과):

```sql
CREATE TABLE events (id UInt32, msg String) ENGINE = MergeTree ORDER BY id;
INSERT INTO events VALUES (1, 'a');   -- part 1 생성
INSERT INTO events VALUES (2, 'b');   -- part 2 생성
INSERT INTO events VALUES (3, 'c');   -- part 3 생성

SELECT name, rows FROM system.parts
WHERE table = 'events' AND active;
-- all_1_1_0 | 1
-- all_2_2_0 | 1      ← INSERT마다 part가 하나씩 생겼다
-- all_3_3_0 | 1

OPTIMIZE TABLE events FINAL;   -- merge를 즉시 강제 (실전에서는 남용 금지)

SELECT name, rows FROM system.parts
WHERE table = 'events' AND active;
-- all_1_3_1 | 3      ← 세 part가 하나로 합쳐졌다
```

part 이름 `all_1_3_1`의 의미: `파티션ID_시작블록_끝블록_병합레벨`.
블록 1~3을 담은 레벨 1(한 번 병합된) part라는 뜻이다.

이 구조에서 세 가지 성질이 따라 나온다:

- **INSERT가 빠르다** — 기존 데이터를 건드리지 않고 새 조각만 쓴다
- **UPDATE/DELETE가 어렵다** — part가 불변이므로, 수정하려면 part를 다시 써야 한다(16장)
- **작은 INSERT를 남발하면 안 된다** — part가 폭증해 "too many parts" 에러.
  기본 한도(26.8 실측): 파티션당 **1,000개부터 삽입 지연**(parts_to_delay_insert),
  **3,000개에서 차단**(parts_to_throw_insert). **수천~수만 행씩 묶어서 넣는 것**이 원칙

## 5.3 Sparse Primary Index — 10억 행을 1초에 찾는 비결

일반 DB의 인덱스는 "모든 행"의 위치를 기록한다(B-tree). ClickHouse는 다르다.

- part 안의 데이터는 **granule(그래뉼)**이라는 8,192행 단위 블록으로 나뉜다
  (`index_granularity` 설정, 기본 8192)
- primary index(`primary.idx`)에는 **각 granule의 첫 행 값만** 기록한다 → "sparse(희소)" 인덱스
- 10억 행이어도 인덱스 엔트리는 12만 개뿐 → **통째로 메모리에 상주**

쿼리가 오면:

1. 메모리의 sparse index를 **이진 탐색**해 조건에 걸릴 가능성이 있는 granule만 고른다
2. 고른 granule만 디스크에서 읽는다 (mark 파일 `.mrk`가 granule → 디스크 위치를 알려줌)

`EXPLAIN indexes = 1`로 직접 확인할 수 있다 (실측):

```sql
CREATE TABLE hits (user_id UInt32, url String, ts DateTime)
ENGINE = MergeTree ORDER BY (user_id, ts);
INSERT INTO hits SELECT number % 100, '/p', now() - number FROM numbers(100000);

EXPLAIN indexes = 1
SELECT count() FROM hits WHERE user_id = 42;
```

```text
ReadFromMergeTree (default.hits)
  Indexes:
    PrimaryKey
      Keys: user_id
      Condition: (user_id in [42, 42])
      Parts: 1/1
      Granules: 1/12        ← 12개 granule 중 1개만 읽었다!
      Search Algorithm: binary search
```

**`Granules: 읽은수/전체수`가 시험과 실무 모두에서 최적화 확인의 기준이다.**
ORDER BY 키로 필터하지 않으면 이 값이 `12/12`(풀스캔)가 된다.

## 5.4 ORDER BY vs PRIMARY KEY

```sql
CREATE TABLE t (...)
ENGINE = MergeTree
PRIMARY KEY (a)        -- 생략 가능
ORDER BY (a, b);       -- 필수
```

- `ORDER BY` = 디스크 정렬 순서. `PRIMARY KEY`를 생략하면 **ORDER BY 전체가 primary key**가 된다 (대부분 이렇게 쓴다)
- 둘을 따로 쓰는 경우: primary key는 ORDER BY의 **접두사(prefix)**여야 한다.
  대표 용례는 SummingMergeTree/AggregatingMergeTree — 집계 단위를 맞추려면 모든
  차원(dimension)을 ORDER BY에 넣어야 하지만, 인덱스에는 앞 몇 개만 두는 경우다
- 긴 primary key는 **INSERT 성능과 메모리에는 부담**이지만, 공식 문서 기준
  **SELECT 성능에는 악영향이 없다** — "키가 길면 조회가 느려진다"는 OLTP 직관은
  여기서 틀린다 (시험 함정 포인트)
- ⚠️ 다른 DB와 결정적 차이: **ClickHouse의 primary key는 유일성(unique)을 보장하지 않는다.**
  같은 키의 행이 얼마든지 공존한다 (중복 제거는 14장의 ReplacingMergeTree 담당)

## 5.5 PARTITION BY — 데이터 관리의 단위 (성능 도구가 아니다!)

```sql
CREATE TABLE sales (
    sale_date Date,
    amount    UInt32
) ENGINE = MergeTree
PARTITION BY toYYYYMM(sale_date)   -- 월 단위 파티션
ORDER BY sale_date;
```

파티션은 part들의 논리적 그룹이다. merge는 **파티션 안에서만** 일어난다.

실측 — 파티션별로 part가 따로 만들어진다:

```sql
INSERT INTO sales VALUES
    ('2026-06-15', 100), ('2026-07-01', 200),
    ('2026-07-20', 300), ('2026-08-05', 400);

SELECT partition, name, rows FROM system.parts
WHERE table = 'sales' AND active;
-- 202606 | 202606_1_1_0 | 1
-- 202607 | 202607_2_2_0 | 2
-- 202608 | 202608_3_3_0 | 1

-- 파티션 통째로 삭제 (매우 빠름 — 디렉토리 삭제 수준)
ALTER TABLE sales DROP PARTITION '202606';
SELECT count() FROM sales;   -- 3
```

**공식 가이드의 핵심 주의사항:**

- 파티션의 목적은 **데이터 수명 관리**다 (오래된 달 삭제, 이동, 백업). 쿼리 가속은
  부수 효과일 뿐, 그걸 노리고 파티션을 잘게 쪼개면 안 된다. 공식 문서의 실측 반례:
  같은 데이터·같은 쿼리에서 파티션 있는 테이블이 **0.090초(431개 part에 분산)**,
  없는 테이블이 **0.012초(1개 part)** — 파티션 키와 무관한 쿼리는 오히려 느려진다
- **너무 잘게 나누지 마라** (일 단위 이하, 고카디널리티 컬럼 파티션 금지).
  파티션이 많으면 part 수가 폭증해 "too many parts"로 이어진다
- 월 단위 `toYYYYMM(date)`가 가장 흔한 패턴. 총 파티션 수는 100~1,000개 이내 권장
- 필요 없으면 **아예 파티션을 안 만드는 것**도 정답이다

파티션 관리 명령 모음 (26.8 실측: `202606`처럼 따옴표 없는 표기와 `'202606'`
문자열 표기 둘 다 동작한다 — 공식 문서는 따옴표 없는 쪽을 쓴다):

```sql
ALTER TABLE sales DROP PARTITION 202606;              -- 삭제
ALTER TABLE sales DETACH PARTITION 202607;            -- 분리 (보관)
ALTER TABLE sales ATTACH PARTITION 202607;            -- 재부착
-- 다른 테이블로 복사/이동
ALTER TABLE sales_backup ATTACH PARTITION 202608 FROM sales;
```

## 5.6 그 외 알아둘 문법

```sql
-- 테이블 설정은 SETTINGS로
CREATE TABLE t (...) ENGINE = MergeTree ORDER BY id
SETTINGS index_granularity = 8192;

-- 샘플링 (대략적 통계를 빠르게)
CREATE TABLE t2 (user_id UInt64, ...) ENGINE = MergeTree
ORDER BY (user_id, intHash32(user_id))
SAMPLE BY intHash32(user_id);
-- SELECT count() * 10 FROM t2 SAMPLE 0.1;   -- 10% 표본
```

## 5.7 이 장의 시험 포인트 요약

1. INSERT마다 part가 생기고, 백그라운드 merge로 합쳐진다 — **배치로 삽입하라**
2. sparse index는 granule(8192행) 단위로 스킵한다 — `EXPLAIN indexes=1`에서
   `Granules: x/y` 확인
3. ORDER BY가 곧 primary key (생략 시) — **유일성 보장 없음**
4. 파티션은 관리 도구 — 월 단위가 표준, 남용 금지
5. `OPTIMIZE TABLE ... FINAL`은 수동 merge — 실무에서 상시 사용 금지 (I/O 폭탄)
