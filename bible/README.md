# ClickHouse Bible — 자격증 취득 완전 정복

> **ClickHouse Certified Developer** 합격을 목표로, 데이터베이스 지식 0에서
> 출발하는 한국어 학습서. 모든 예제는 **ClickHouse 26.8** (`clickhouse local`)에서
> 실행 검증되었다. 작성 기준일: 2026-08-16.

## 사용법

1. 이 저장소 루트의 `./clickhouse` 바이너리로 모든 예제를 직접 실행하면서 읽는다
2. 순서대로 읽되, DB 경험자는 1장을 건너뛰고 4장부터 가속해도 된다
3. 각 장 끝의 시험 포인트/함정 목록은 시험 직전에 다시 본다
4. 마지막에 19장 모의고사를 시간 재고 풀어본다

## 목차

### 시작

| 장 | 제목 | 내용 |
|----|------|------|
| [0장](00-exam-guide.md) | 시험 완전 안내 | 형식·비용·범위·응시 절차·학습 로드맵 (4주 플랜) |
| [1장](01-database-basics.md) | 데이터베이스 첫걸음 | DB란, SQL이란, OLTP vs OLAP, 컬럼 지향 원리 |
| [2장](02-setup.md) | 설치와 실습 환경 | 단일 바이너리, local/server/client, Docker, Cloud, 포트 |
| [3장](03-sql-first-steps.md) | SQL 첫걸음 | SELECT/INSERT/CREATE, WHERE·GROUP BY·ORDER BY |

### 시험 영역 1 — 데이터 모델링

| 장 | 제목 | 내용 |
|----|------|------|
| [4장](04-data-types.md) | 데이터 타입 대전 | 효율적 타입 선택, LowCardinality, 오버플로 함정 |
| [5장](05-mergetree.md) | MergeTree | part와 merge, sparse index, granule, 파티션 |
| [6장](06-table-design.md) | 테이블 설계 | ORDER BY 키 설계(실측 비교), TTL, 압축 codec |
| [7장](07-dictionary.md) | Dictionary | CREATE DICTIONARY, LAYOUT, dictGet |

### 시험 영역 2 — 데이터 삽입

| 장 | 제목 | 내용 |
|----|------|------|
| [8장](08-inserting-data.md) | 데이터 삽입 | file/url/s3, 포맷, 스키마 추론, 삽입 중 변환 |

### 시험 영역 3 — 데이터 분석

| 장 | 제목 | 내용 |
|----|------|------|
| [9장](09-select-deep-dive.md) | SELECT 심화 | JOIN 전종, ASOF, ARRAY JOIN, CTE, LIMIT BY |
| [10장](10-functions.md) | 함수 ① | 문자열·날짜·조건·배열 (+람다) |
| [11장](11-aggregation-window.md) | 함수 ② | 집계(uniq/quantile/argMax), combinator, 윈도우 |

### 시험 영역 4 — 쿼리 성능 최적화

| 장 | 제목 | 내용 |
|----|------|------|
| [12장](12-materialized-views.md) | Materialized View | 트리거 원리, State/Merge, Refreshable MV |
| [13장](13-projections-skipping-indexes.md) | Projection·Skipping Index | 문법, MATERIALIZE, 선택 기준 |

### 시험 영역 5 — 중복 제거와 뮤테이션

| 장 | 제목 | 내용 |
|----|------|------|
| [14장](14-dedup-mutations.md) | 중복 제거·뮤테이션 | Replacing/Collapsing, DELETE, ALTER 뮤테이션 |

### 심화·실무

| 장 | 제목 | 내용 |
|----|------|------|
| [15장](15-other-engines-kafka.md) | 기타 엔진·Kafka | Null 트릭, Kafka 3단 패턴, 외부 DB 연동 |
| [16장](16-performance.md) | 성능 분석 | EXPLAIN indexes=1, system 테이블, 설정 |
| [17장](17-replication-scaling.md) | 복제와 샤딩 | Keeper, ReplicatedMergeTree, Distributed, K8s, Cloud |

### 마무리

| 장 | 제목 | 내용 |
|----|------|------|
| [18장](18-exam-strategy.md) | 시험 준비 전략 | 공식 교육, 문서 내비게이션, 실전 데이터셋, 당일 운영 |
| [19장](19-mock-exam.md) | 모의고사 | 실전 형식 12과제 + 검증된 해답 |
| [20장](20-cheatsheet.md) | 치트시트 | 직전 10분 복습 + 실측 함정 12선 |

## 빠른 시작

```bash
cd /Users/jayden/Documents/clickhouse-study
./clickhouse local --path ./practice    # 상태 유지되는 실습 셸
```

```sql
CREATE TABLE hello (id UInt32, msg String) ENGINE = MergeTree ORDER BY id;
INSERT INTO hello VALUES (1, '합격을 향해!');
SELECT * FROM hello;
```

## 출처

- 시험 정보: [clickhouse.com/learn/certification](https://clickhouse.com/learn/certification) (2026-08-16 확인)
- 공식 문서: [clickhouse.com/docs](https://clickhouse.com/docs)
- 합격 후기: [OpenMeter 팀 블로그](https://clickhouse.com/blog/how-to-learn-clickhouse-and-become-a-certified-clickhouse-developer)
- 모든 SQL 예제: ClickHouse 26.8.1 로컬 검증
