# 0장. ClickHouse Certified Developer 시험 완전 안내

> 최종 확인: 2026년 8월 16일, 출처: [clickhouse.com/learn/certification](https://clickhouse.com/learn/certification)

## 0.1 이 자격증은 무엇인가

**ClickHouse Certified Developer**는 ClickHouse, Inc.가 운영하는 유일한 공식 자격증이다.
객관식 시험이 아니라 **실기(hands-on) 시험**이다. 실제 ClickHouse 환경에 접속해서
테이블을 만들고, 데이터를 넣고, 쿼리를 짜는 **과제 10~12개**를 직접 수행한다.

합격하면 Credly 디지털 배지가 발급되며, **유효기간은 없다** ("Once certified, always certified").

## 0.2 시험 개요 한눈에 보기

| 항목 | 내용 |
|------|------|
| 형식 | 실기(performance-based) — 실제 클러스터에서 과제 수행 |
| 플랫폼 | HackerRank (브라우저 기반) |
| 시간 | 2시간 (환경 준비 포함 약 2시간 10~15분) |
| 과제 수 | 10~12개 (과제별 배점 다름) |
| 합격 기준 | **70% 이상** (자동 채점 + 수동 검토 병행) |
| 결과 통지 | 최대 5영업일 |
| 비용 | **$200 USD** / 1회 응시 (환불 불가) |
| 재응시 | 횟수 무제한, 단 직전 응시 후 **7일 대기**, 매회 $200 |
| 응시 기한 | 구매 후 **365일 이내** 아무 때나 응시 가능 |
| 사전 요건 | 없음 (권장: 무료 공식 교육 "Real-time Analytics with ClickHouse") |
| 자격 유효기간 | 없음 (영구) |

### 시험 환경 요구사항과 규정

- 작동하는 **웹캠 필수** (AI 프록터링 — 시험 내내 동일인인지 확인)
- 조명이 밝은 조용한 공간
- **외부 모니터 사용 불가**
- **시험 중 clickhouse.com 도메인 전체 열람 허용** (공식 문서 + 블로그 + 아티클) ← 매우 중요!
- ⚠️ **AI 도구는 전면 금지** — 문서 사이트에 내장된 "Ask AI" 기능도 시험 중에는
  쓰면 안 된다. 과제별로 화면이 녹화되며, AI 생성 답안 탐지도 수행된다

> 💡 문서 열람이 허용되므로, 문법을 통째로 암기하는 것보다
> **"어떤 기능이 존재하는지 알고, 문서에서 빨리 찾는 능력"**이 훨씬 중요하다.
> 이 바이블의 목표도 정확히 그것이다.

## 0.3 시험 범위 (공식 Exam Objectives)

공식 페이지에 명시된 5개 영역이다. 이 바이블의 구성도 이 순서를 따른다.

### 영역 1 — 데이터 모델링 (Modeling data)

- 새 데이터베이스 생성
- 요구 조건/파일 형식에 맞는 테이블 생성
- 컬럼에 **효율적인 데이터 타입** 선택 (가장 작은 타입 고르기)
- 쿼리 패턴에 맞는 **MergeTree Primary Key** 정의
- **Dictionary** 정의 및 조회

→ 이 책의 4~8장

### 영역 2 — 데이터 삽입 (Inserting data)

- 로컬 파일을 테이블에 삽입
- 클라우드 스토리지(S3 등)의 파일을 테이블에 삽입
- **Parquet, CSV, TSV** 파일 삽입
- **삽입 중 컬럼 변환** (이름 변경, 타입 변환, 계산)
- 테이블 간 데이터 복사

→ 이 책의 9장

### 영역 3 — 데이터 분석 (Analyzing data)

- 조건에 맞는 SELECT 쿼리 작성
- 일반 함수 사용 (부분 문자열 검색, 타임스탬프 변환 등)
- 집계 함수 사용 (max/min/sum/avg, 고유값 개수, 분위수 등)
- **GROUP BY**로 시간 단위/그룹 단위 집계

→ 이 책의 10~12장

### 영역 4 — 쿼리 성능 최적화 (Optimizing query performance)

- 비집계 쿼리 결과의 **Materialized View** 정의
- **AggregatingMergeTree / SummingMergeTree**에 집계 결과 저장
- 테이블 **Projection** 정의
- **set / minmax skipping index** 정의

→ 이 책의 13~15장

### 영역 5 — 중복 제거와 변경 (Deduplication and mutations)

- **Lightweight DELETE** 수행
- **ReplacingMergeTree**를 이용한 upsert 전략
- **CollapsingMergeTree**를 이용한 빈번한 업데이트 전략

→ 이 책의 16장

## 0.4 응시 절차

1. [clickhouse.com/learn/certification](https://clickhouse.com/learn/certification) 접속
2. 응시권 구매 ($200) → 365일 내 아무 때나 응시 가능
3. HackerRank 링크로 시험 시작 (예약 불필요, 24/7 가능)
4. 웹캠·환경 확인 (플랫폼 안내에 따를 것) → 2시간 실기
5. 최대 5영업일 내 결과 메일 수신 → 합격 시 Credly 배지 발급

## 0.5 공식 권장 학습 자료

| 자료 | 내용 | 비용 |
|------|------|------|
| [Real-time Analytics with ClickHouse](https://clickhouse.com/learn/real-time-analytics) | 시험 범위 전체를 다루는 공식 교육. On-demand(녹화) 또는 강사 주도(라이브) | **무료** |
| [ClickHouse Academy](https://clickhouse.com/learn) | 주제별 무료 온라인 코스 모음 | 무료 |
| [공식 문서](https://clickhouse.com/docs) | 시험 중에도 열람 가능. 구조를 미리 익혀둘 것 | 무료 |
| [Example Datasets](https://clickhouse.com/docs/getting-started/example-datasets) | 실습용 공개 데이터셋 (UK 부동산, NYC 택시 등) | 무료 |

## 0.6 학습 로드맵 (지식 0에서 합격까지)

DB를 한 번도 다뤄본 적 없는 사람 기준, **하루 1~2시간씩 4주** 플랜이다.
(참고: 공개된 합격 후기들의 실제 준비 기간은 6~8주가 많았다 — 이 플랜은 빡빡한
편이니, 여유가 있다면 각 주차를 1.5주로 늘려 잡아도 좋다.)

| 주차 | 목표 | 해당 장 |
|------|------|---------|
| 1주차 | DB 개념 + 실습 환경 구축 + SQL 첫걸음 + 데이터 타입 | 1~4장 |
| 2주차 | MergeTree 완전 이해 + 테이블 설계 + Dictionary + 데이터 삽입 | 5~9장 |
| 3주차 | SELECT 심화 + 함수 + 집계 + Materialized View | 10~14장 |
| 4주차 | 성능 최적화 + 중복 제거 + 모의 과제 반복 | 15~17장, 19~20장 |

각 장의 예시는 **전부 복사해서 바로 실행 가능**하며, 이 저장소에 있는
`./clickhouse local` (v26.8) 로 검증되었다. 읽지만 말고 반드시 직접 실행할 것 —
실기 시험이므로 손이 기억해야 한다.
