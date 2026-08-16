# ClickHouse Bible 📒

> **ClickHouse Certified Developer** 자격증 합격을 위한 완전 입문 한국어 학습서.
> 데이터베이스 지식 0에서 출발하며, 모든 SQL 예제는 ClickHouse 26.8에서 실행 검증되었다.

## 읽는 방법

- **웹**: https://arc1el.github.io/clickhouse-bible/
- **마크다운**: [`bible/`](bible/README.md) 디렉토리에서 장별로 열람 (GitHub에서 바로 읽기 좋음)

## 구성

| 경로 | 내용 |
|------|------|
| `bible/` | 원본 마크다운 21개 장 (목차는 [bible/README.md](bible/README.md)) |
| `docs/` | GitHub Pages용 정적 사이트 (index + 장별 페이지, 빌드 산출물) |
| `tools/build.py` | `bible/*.md` → `docs/` 사이트 빌더 |
| `clickhouse_values.yaml` | Kubernetes 오퍼레이터 배포 예시 (17장 참조) |

## 사이트 다시 빌드하기

`bible/`의 마크다운을 수정한 뒤:

```bash
python3 tools/build.py
```

## 실습 환경

```bash
curl https://clickhouse.com/ | sh      # ./clickhouse 바이너리 (저장소에는 미포함)
./clickhouse local --path ./practice   # 상태가 유지되는 실습 셸
```

## 출처·검증

- 시험 정보: [clickhouse.com/learn/certification](https://clickhouse.com/learn/certification) (2026-08-16 확인)
- 모든 SQL 예제: ClickHouse 26.8.1 `clickhouse local` 실행 검증
- 작성 후 주제별 리서치 에이전트 9팀의 공식 문서 대조 검수 반영
