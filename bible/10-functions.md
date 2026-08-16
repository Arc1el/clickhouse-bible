# 10장. 함수 레퍼런스 ① — 문자열·날짜·조건·배열

> 시험 영역 3의 문구: "use regular functions (search for a substring,
> convert a timestamp, ...)". 이 장의 함수들은 전부 26.8에서 실행 검증되었다.
> 시험장에서는 문서를 열 수 있으니 **이름과 용도만 확실히** 기억하면 된다.

## 10.1 문자열 함수 ★ (부분 문자열 검색 = 시험 명시)

```sql
SELECT
    length('ClickHouse'),                    -- 10 (바이트 길이; 문자 수는 lengthUTF8)
    lower('ABC'), upper('abc'),              -- abc / ABC
    concat('Click', 'House'),                -- ClickHouse ('Click' || 'House'도 동일)
    substring('ClickHouse', 6, 5),           -- House (시작위치 1부터!)
    trim('  hi  '),                          -- hi
    startsWith('https://x.com', 'https'),    -- 1
    endsWith('file.csv', '.csv');            -- 1
```

### 부분 문자열 검색 세트

```sql
SELECT position('ClickHouse', 'House');      -- 6 (없으면 0) — 위치 반환
SELECT positionCaseInsensitive('ClickHouse', 'HOUSE');  -- 6 — 대소문자 무시
SELECT 'ClickHouse' LIKE '%House%';          -- 1 — 패턴 (%=아무거나, _=한 글자)
SELECT 'ClickHouse' ILIKE '%house%';         -- 1 — 대소문자 무시 LIKE
SELECT match('hello123', '^[a-z]+\d+$');     -- 1 — 정규식
SELECT multiSearchAny('ClickHouse', ['byte', 'House']); -- 1 — 여러 패턴 중 하나라도 (OR LIKE보다 빠름)
```

⚠️ `locate('찾을것', '대상')`이라는 함수도 있는데 **position과 인자 순서가 반대**다
(MySQL 호환용). 헷갈리면 position만 쓰자.

### 치환·추출·분해

```sql
SELECT replaceOne('a-b-c', '-', '_');        -- a_b-c (첫 번째만)
SELECT replaceAll('a-b-c', '-', '_');        -- a_b_c
SELECT replaceRegexpAll('a1b22c', '\d+', '#'); -- a#b#c
SELECT extract('price: 1500 won', '\d+');    -- 1500 (정규식 첫 매치)
SELECT extractAll('1a2b3', '\d');            -- ['1','2','3']
SELECT splitByChar(',', 'a,b,c');            -- ['a','b','c']
SELECT splitByString('::', 'a::b');          -- ['a','b']
```

### 사람 눈용 포맷

```sql
SELECT formatReadableSize(123456789);        -- 117.74 MiB
SELECT formatReadableQuantity(9876543);      -- 9.88 million
```

## 10.2 날짜·시간 함수 ★★ (타임스탬프 변환 = 시험 명시)

### 지금·오늘·구성 요소

```sql
SELECT now(), today(), yesterday();
SELECT
    toYear(toDate('2026-08-16')),        -- 2026
    toMonth(toDate('2026-08-16')),       -- 8
    toDayOfMonth(toDate('2026-08-16')),  -- 16
    toDayOfWeek(toDate('2026-08-16')),   -- 7 (월=1 ~ 일=7)
    toHour(now()),
    toYYYYMM(toDate('2026-08-16'));      -- 202608 (파티션 표현식 단골)
```

### 시간 버킷 만들기 (GROUP BY의 단짝 — "시간 단위 집계" 시험 문형)

```sql
SELECT toStartOfHour(ts), count() FROM events GROUP BY 1;   -- 시간별
-- 계열: toStartOfMinute / Day / Week / Month / Quarter / Year
-- 다른 DB에서 온 사람용 동의어: dateTrunc('hour', ts) = toStartOfHour(ts)
-- 임의 간격:
SELECT toStartOfInterval(ts, INTERVAL 15 MINUTE) AS bucket, count()
FROM events GROUP BY bucket;   -- 15분 버킷 (26.8 검증)
```

### 덧셈·뺄셈·차이

```sql
SELECT addDays(toDate('2026-08-16'), 10);        -- 2026-08-26
-- 계열: addHours/addMinutes/addMonths..., subtractDays/...
SELECT toDate('2026-08-16') + INTERVAL 1 MONTH;  -- 연산자 스타일
SELECT dateDiff('day', toDate('2026-08-01'), toDate('2026-08-16'));  -- 15
-- 단위: 'second','minute','hour','day','week','month','year'

-- dateDiff vs age — 시험 함정: dateDiff는 "경계를 넘은 횟수", age는 "채워진 단위 수"
SELECT dateDiff('month', toDate('2021-12-29'), toDate('2022-01-01'));  -- 1 (월 경계 넘음)
SELECT age('month',      toDate('2021-12-29'), toDate('2022-01-01'));  -- 0 (한 달이 안 참)
```

### 문자열 ↔ 시간 변환 (26.8 실측 — 함정 포함)

```sql
-- 표준 형식은 to계열로 바로
SELECT toDate('2026-08-16'), toDateTime('2026-08-16 12:34:56');

-- 제각각인 형식은 BestEffort로
SELECT parseDateTimeBestEffort('Aug 16 2026 14:30:00');        -- OK
SELECT parseDateTimeBestEffort('2026-08-16T14:30:00+09:00');   -- OK (ISO+타임존)

-- ⚠️ Apache 로그 형식은 BestEffort가 못 읽는다 (실측: 에러) → 포맷 지정 파싱
SELECT parseDateTime('16/Aug/2026:14:30:00', '%d/%b/%Y:%H:%i:%s');
-- 실패 시 NULL을 원하면: parseDateTimeBestEffortOrNull / parseDateTimeOrNull

-- 시간 → 문자열
SELECT formatDateTime(now(), '%Y-%m-%d %H:%i');   -- MySQL 스타일 포맷 문자
```

### Unix 타임스탬프와 타임존

```sql
SELECT toUnixTimestamp(toDateTime('2026-08-16 00:00:00'));
-- 1786806000 (서버 타임존이 Asia/Seoul일 때 — UTC 서버라면 1786838400)
-- 재현 가능하게 쓰려면 타임존을 고정: toDateTime('2026-08-16 00:00:00', 'UTC')
SELECT fromUnixTimestamp(1786806000);
SELECT toTimeZone(now(), 'Asia/Seoul');   -- 표시 타임존 변환
SELECT toString(now(), 'Asia/Seoul');     -- 타임존 지정 문자열화
```

## 10.3 조건 함수

```sql
SELECT if(price > 10000, 'expensive', 'cheap');            -- 3항
SELECT multiIf(p < 3, 'low', p < 7, 'mid', 'high');        -- 다단계 (검증됨)
-- CASE WHEN ... THEN ... ELSE ... END 도 동일하게 동작 (multiIf로 변환됨)

-- NULL 다루기
SELECT ifNull(nickname, '(없음)');       -- NULL이면 대체값
SELECT coalesce(a, b, c, '기본');        -- 처음 만나는 비NULL
SELECT nullIf(v, 0);                     -- v=0이면 NULL로
SELECT assumeNotNull(x);                 -- Nullable 벗기기 — ⚠️ NULL이면 결과가
                                         -- 보장되지 않는다(임의 값). NULL 없음이 확실할 때만
SELECT greatest(3, 7), least(3, 7);      -- 7, 3
```

## 10.4 배열 함수 + 람다

배열 인덱스는 **1부터**다.

```sql
SELECT
    [10,20,30][1],                        -- 10
    length([1,2,3]),                      -- 3
    has([1,2,3], 2),                      -- 1 (포함 여부)
    hasAll([1,2,3], [1,3]),               -- 1 (전부 포함?)
    hasAny([1,2], [2,9]),                 -- 1 (하나라도?)
    indexOf(['a','b'], 'b');              -- 2

-- 람다 (x -> 식) 를 받는 고차 함수 (26.8 검증)
SELECT
    arrayMap(x -> x * x, [1,2,3]),        -- [1,4,9]
    arrayFilter(x -> x > 10, [5,15,25]),  -- [15,25]
    arraySum([1,2,3]),                    -- 6
    arrayCount(x -> x % 2 = 0, [1,2,3,4]),-- 2
    arraySort([3,1,2]),                   -- [1,2,3]
    arrayReverseSort([3,1,2]),            -- [3,2,1]
    arrayDistinct([1,1,2]),               -- [1,2]
    arrayFlatten([[1,2],[3]]);            -- [1,2,3]

-- 집계와의 콤보: groupArray로 모아서 배열 함수로 가공 (검증됨)
SELECT arrayMap(x -> x * x, groupArray(number)) FROM numbers(5);
```

## 10.5 수학·기타

```sql
SELECT round(3.567, 2), floor(3.9), ceil(3.1);   -- 3.57, 3, 4
SELECT abs(-5), intDiv(7, 2), 7 % 2;             -- 5, 3(정수 나눗셈), 1
SELECT roundBankers(2.5);                        -- 2 (은행가 반올림)

SELECT toTypeName([1, 2]);       -- 값의 타입 확인 (디버깅 필수품)
SELECT generateUUIDv4();
SELECT rand() % 100;             -- 0~99 난수
SELECT version(), hostName();
```

## 10.6 함수를 "찾는" 능력이 진짜 실력

시험장에서 함수명이 기억 안 나면:

1. 공식 문서 검색창에 **하고 싶은 일의 영어 키워드** 입력 (예: "split string")
2. [SQL Reference → Functions](https://clickhouse.com/docs/sql-reference/functions) 카테고리에서 훑기
3. `system.functions` 테이블 검색: `SELECT name FROM system.functions WHERE name ILIKE '%split%'`
