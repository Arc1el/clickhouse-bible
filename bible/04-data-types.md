# 4장. 데이터 타입 대전 — 시험 영역 1의 핵심

> 시험 채점 기준에 "**컬럼에 효율적인 데이터 타입 선택**"이 명시돼 있다.
> 핵심 원칙 하나만 기억하면 된다: **표현 범위를 만족하는 가장 작은 타입을 골라라.**
> 타입이 작을수록 → 디스크·메모리·캐시를 덜 쓰고 → 스캔이 빨라진다.

## 4.1 정수 — Int / UInt

`Int`는 부호 있음(음수 가능), `UInt`는 부호 없음(0 이상). 뒤의 숫자는 비트 수다.

| 타입 | 크기 | 범위 | 전형적 용도 |
|------|------|------|-------------|
| Int8 | 1B | -128 ~ 127 | 작은 코드값, sign(-1/1) |
| UInt8 | 1B | 0 ~ 255 | 나이, 소형 카운트, Bool 내부표현 |
| Int16 | 2B | -32,768 ~ 32,767 | |
| UInt16 | 2B | 0 ~ 65,535 | 연도, 포트 번호 |
| Int32 | 4B | 약 ±21.5억 | |
| UInt32 | 4B | 0 ~ 약 42.9억 | **user_id, 카운트 등 기본 선택지** |
| Int64 | 8B | 약 ±922경 | 금액(원 단위 큰 값), snowflake ID |
| UInt64 | 8B | 0 ~ 약 1,844경 | 이벤트 ID, 해시값 |
| Int128/256, UInt128/256 | 16/32B | 초대형 | 암호화폐 수량 등 특수 용도 |

선택 요령 (시험 그대로 적용):

1. **음수가 없으면 무조건 UInt** (범위가 2배로 늘어난다)
2. 최댓값을 추정해서 **여유 있는 최소 크기** 선택 — 사용자 수 백만 명이면 UInt32(42억)면 충분
3. 애매하면 한 단계 크게 — 오버플로가 절약보다 훨씬 비싸다

### ⚠️ 실측된 함정: 조용한 오버플로

```sql
SELECT toInt8(200);              -- 결과: -56  (에러 없이 값이 깨진다!)
SELECT accurateCast(200, 'Int8');
-- Code: 70. DB::Exception: Value ... cannot be safely converted (에러 발생)
```

`toInt8()` 같은 변환 함수는 넘치면 **조용히 잘라버린다**. 안전하게 변환하려면
`accurateCast(값, '타입')` 또는 `accurateCastOrNull(값, '타입')`을 쓴다.

## 4.2 소수 — Float vs Decimal

| 타입 | 크기 | 특징 |
|------|------|------|
| Float32 / Float64 | 4B / 8B | 빠르지만 **이진 부동소수점 오차** 존재 |
| Decimal32(S) ~ Decimal256(S) | 4~32B | 십진 고정 소수점, 오차 없음 |
| Decimal(P, S) | P에 따라 | P=전체 자릿수(최대 76), S=소수 자릿수 |

- **돈은 Decimal** (`Decimal(18, 2)` = 정수부 16자리 + 소수 2자리), 센서값·비율처럼
  오차가 허용되면 Float
- `SELECT toDecimal64(3.14159, 4)` → `3.1415`, 타입은 `Decimal(18, 4)`

### ⚠️ 실측된 함정: Decimal 집계의 타입 확장

`sum(Decimal(18,2))`의 **결과 타입은 `Decimal(38,2)`로 커진다** (오버플로 방지).
그래서 집계 결과를 저장하는 테이블(13~14장 Materialized View)을 만들 때
`SimpleAggregateFunction(sum, Decimal(18,2))`라고 쓰면 타입 불일치 에러가 난다 —
`Decimal(38,2)`로 선언해야 한다.

## 4.3 불리언 — Bool

내부적으로 UInt8(0/1)이다. `true`/`false` 리터럴을 그대로 쓸 수 있고,
`WHERE spicy` 처럼 조건에 바로 쓸 수 있다.

## 4.4 문자열 — String / FixedString

- **String**: 길이 무제한 가변 길이. **ClickHouse의 기본 선택지.**
  (다른 DB의 VARCHAR(255) 같은 길이 지정이 필요 없다 — `VARCHAR`라고 써도 String으로 처리된다)
- **FixedString(N)**: 정확히 N바이트. 국가코드(2), 해시(32) 등 길이가 항상 같을 때만.
  N보다 짧으면 널 바이트로 패딩되므로 비교 시 주의.

### LowCardinality(String) — 시험 단골 ★

**고유값 종류가 적은(대략 1만 미만) 문자열 컬럼**은 `LowCardinality(String)`으로 감싸라.
내부적으로 사전(dictionary) 인코딩되어 저장·비교가 정수 수준으로 빨라진다.

반대 방향의 상한도 있다 — 공식 문서 기준 **고유값이 10만을 넘으면 일반 String보다
오히려 느려질 수 있다.** user_id, URL 전문, 이메일, 세션 토큰 같은 고카디널리티
컬럼에는 쓰지 마라. 판정은 `SELECT uniq(col) FROM t` 한 줄이면 된다.

```sql
CREATE TABLE logs (
    level   LowCardinality(String),  -- 'INFO','WARN','ERROR' 세 종류뿐
    country LowCardinality(String),  -- 국가코드 ~250종
    message String                   -- 자유 텍스트는 그냥 String
) ENGINE = MergeTree ORDER BY level;
```

실측: 100만 행 테이블에서 3종류 값을 가진 `LowCardinality(String)` 컬럼의 압축률은
**208배**였다 (978KiB → 4.7KiB). 일반 String 대비 압도적이다.

Enum8/Enum16 (`Enum8('view' = 1, 'purchase' = 2)`)도 비슷한 목적이지만,
**새 값이 들어오면 에러가 나는 엄격한 타입**이다. 값 목록이 고정 계약이면 Enum,
유연해야 하면 LowCardinality를 쓴다 — 요즘 공식 권장은 대부분의 경우 LowCardinality다.

## 4.5 날짜와 시간 ★★ (시험 필수)

| 타입 | 크기 | 범위 | 정밀도 |
|------|------|------|--------|
| Date | 2B | 1970-01-01 ~ 2149-06-06 | 일 |
| Date32 | 4B | 0000-01-01 ~ 9999-12-31 | 일 |
| DateTime | 4B | 1970 ~ 2106 | **초** |
| DateTime64(N) | 8B | 0000 ~ 9999 (밀리초 기준) | 10⁻ᴺ초 (N=3 밀리초, 6 마이크로초) |

⚠️ DateTime64의 실제 범위는 **정밀도 N에 따라 줄어든다** — N=9(나노초)면
1677-09-21 ~ 2262-04-11로 급격히 좁아진다 (26.8 실측: `toDateTime64('2263-01-01', 9)`
→ `DECIMAL_OVERFLOW` 에러).

```sql
SELECT
    toDate('2026-08-16')                          AS d,
    toDateTime('2026-08-16 12:34:56')             AS dt,
    toDateTime64('2026-08-16 12:34:56.789', 3)    AS dt_ms,
    toDateTime('2026-08-16 12:34:56', 'Asia/Seoul') AS dt_kst;  -- 타임존 지정
```

- 내부 저장은 항상 **Unix 타임스탬프(UTC)**이고, 타임존은 "보여줄 때의 해석"이다
- 컬럼 선언에도 타임존을 박을 수 있다: `event_time DateTime('Asia/Seoul')`
- 밀리초가 필요 없으면 DateTime(4B)이 DateTime64(8B)보다 절약 — "효율적 타입 선택" 포인트

## 4.6 기타 단일 타입

| 타입 | 용도 | 예시 |
|------|------|------|
| UUID | 16B 고유 식별자 | `generateUUIDv4()` |
| IPv4 / IPv6 | IP 주소 전용 (String보다 작고 빠름) | `toIPv4('1.2.3.4')` |

## 4.7 복합 타입 — Array / Map / Tuple / Nested

```sql
SELECT
    [1, 2, 3]                 AS arr,    -- Array(UInt8)
    map('a', 1, 'b', 2)       AS m,      -- Map(String, UInt8)
    (1, 'x')                  AS tup;    -- Tuple(UInt8, String)

-- 배열 인덱스는 1부터! (0부터가 아님)
SELECT [10, 20, 30][1];   -- 10
```

- **Array(T)**: 한 행에 여러 값. 태그 목록, 방문 URL 목록 등. 10장에서 배열 함수 대전.
- **Map(K, V)**: 키-값 쌍. 자유로운 속성 백(attribute bag). `m['a']`로 접근.
- **Tuple(...)**: 서로 다른 타입 묶음. 함수 반환값 등에서 자주 만난다.
- **Nested(...)**: 구조체의 배열. 내부적으로는 "같은 길이의 Array 여러 개"다.

## 4.8 Nullable — 쓰기 전에 두 번 생각

```sql
CREATE TABLE t (score Nullable(UInt8)) ENGINE = Memory;
INSERT INTO t VALUES (NULL), (90);
```

- ClickHouse에서 NULL을 허용하려면 **명시적으로 Nullable(T)**로 감싸야 한다
  (기본은 NOT NULL — 값이 없으면 타입 기본값 0/''가 들어간다)
- **비용**: Nullable 컬럼은 NULL 여부를 기록하는 **별도 파일이 하나 더 생기며**,
  연산·압축 효율이 떨어진다. 공식 문서도 "꼭 필요할 때만" 권장.
- 대안: "0이 곧 없음"으로 약속하거나, `-1` 같은 센티널 값을 쓰는 것이 관용적이다.
- 참고: 파일 스키마 추론(9장)은 기본적으로 컬럼을 Nullable로 추론한다. 테이블을
  직접 만들 때는 Nullable을 벗겨서 선언하는 것이 좋다.

## 4.9 JSON 타입 (25.3부터 정식)

과거의 `Object('json')`은 폐기되었고, 현재는 정식 **JSON 타입**을 쓴다
(오픈소스 25.3부터 production-ready).

```sql
CREATE TABLE js (data JSON) ENGINE = Memory;
INSERT INTO js VALUES ('{"user": {"name": "kim", "age": 30}, "tags": ["a","b"]}');

-- 점(.) 경로로 바로 접근
SELECT data.user.name, data.user.age, data.tags[1] FROM js;
-- kim | 30 | a
```

⚠️ 타입을 지정하지 않은 경로의 타입은 `Dynamic`이라 **집계에 바로 못 쓴다**
(`sum(data.age)` → `Illegal type Dynamic` 에러 — 26.8 실측). 해법 두 가지:

```sql
SELECT sum(data.age.:Int64) FROM js;                 -- ① 읽을 때 타입 지정
CREATE TABLE js (data JSON(age Int64)) ENGINE = ...; -- ② 선언 시 타입 힌트 (공식 권장)
```

스키마가 유동적인 로그에 유용하다. 다만 구조가 확실히 정해져 있다면
일반 컬럼으로 펼치는 것이 항상 더 빠르다.

## 4.10 타입 변환 총정리

```sql
-- to계열: 관용적, 넘치면 조용히 깨질 수 있음
SELECT toInt32('123'), toString(456), toDate('2026-08-16'), toFloat64('3.14');

-- ::: 캐스트 연산자 (짧은 표기)
SELECT '123'::UInt32, 3.14::Decimal(10,2);

-- CAST 표준 문법
SELECT CAST('2026-08-16' AS Date);

-- 안전 변환: 실패하면 에러 대신 NULL / 기본값
SELECT toInt32OrNull('abc');   -- NULL
SELECT toInt32OrZero('abc');   -- 0
SELECT accurateCast(200, 'Int8');        -- 범위 초과 시 에러 (안전)
SELECT accurateCastOrNull(200, 'Int8');  -- 범위 초과 시 NULL
```

## 4.11 시험 대비 타입 선택 훈련

다음 요구를 보고 타입을 즉답할 수 있어야 한다:

| 데이터 | 정답 | 이유 |
|--------|------|------|
| 페이지 조회 시각 (초 단위면 충분) | `DateTime` | 4B로 충분 |
| API 응답 시간 ms (0~수만) | `UInt16` 또는 `UInt32` | 음수 없음, 작게 |
| HTTP 상태 코드 (100~599) | `UInt16` | 255 초과이므로 UInt8 불가 |
| 국가 코드 ('KR', 'US', ...) | `LowCardinality(String)` | 저카디널리티 |
| 로그 레벨 (4종) | `LowCardinality(String)` | 〃 |
| 주문 금액 (통화) | `Decimal(18, 2)` | 오차 불가 |
| 센서 온도 | `Float32` | 오차 허용 |
| 사용자 ID (최대 수억) | `UInt32` | 42억까지 커버 |
| 이벤트 고유 ID | `UUID` 또는 `UInt64` | |
| 태그 목록 | `Array(String)` | |
| 삭제 여부 플래그 | `Bool` 또는 `UInt8` | |
