# 2장. 설치와 실습 환경 — 5분 만에 시작하기

> 시험은 실기다. **오늘 안에 손으로 쿼리를 실행할 수 있는 환경**을 만드는 것이
> 이 장의 목표다. 이 저장소에는 이미 ClickHouse 26.8 바이너리가 들어 있다.

## 2.1 ClickHouse는 단일 바이너리다

ClickHouse의 남다른 점: **파일 하나에 서버·클라이언트·로컬 도구가 전부** 들어 있다.

| 실행 방법 | 역할 |
|-----------|------|
| `./clickhouse server` | 데이터베이스 서버 실행 |
| `./clickhouse client` | 실행 중인 서버에 접속하는 클라이언트 |
| `./clickhouse local` | **서버 없이** 즉석 SQL 실행 (학습 최적) |

## 2.2 설치 방법별 정리

### macOS / Linux — 공식 스크립트 (가장 간단)

```bash
curl https://clickhouse.com/ | sh   # ./clickhouse 바이너리 + 관리 도구 chctl 설치
./clickhouse local                  # 바로 실행!

# 바이너리만 받고 싶으면:
curl https://clickhouse.com/ | CLICKHOUSE_ONLY=1 sh
```

함께 설치되는 `chctl`(clickhousectl)은 버전 관리 도구다 — nvm이 Node에 해주는
일을 ClickHouse에 해준다:

```bash
chctl local use 26.8                  # 특정 버전 설치 + 기본값 지정
chctl local server start --name dev   # 로컬 서버 기동
chctl local client --name dev
```

> ⚠️ macOS에서 `brew install --cask clickhouse`는 **2026-09-01부로 비활성화**된다
> (Gatekeeper 문제로 deprecated — 2026-08 실측 확인). macOS는 위 curl 스크립트를 쓰자.

### Ubuntu/Debian — 패키지 설치 (서버 상시 운영용)

```bash
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg
curl -fsSL https://packages.clickhouse.com/rpm/lts/repodata/repomd.xml.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/clickhouse-keyring.gpg
ARCH=$(dpkg --print-architecture)
echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg arch=${ARCH}] https://packages.clickhouse.com/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/clickhouse.list
sudo apt-get update
sudo apt-get install -y clickhouse-server clickhouse-client

sudo systemctl start clickhouse-server    # 시작
clickhouse-client                          # 접속
```

### Docker

```bash
docker run -d --name my-clickhouse \
  --ulimit nofile=262144:262144 \
  -p 8123:8123 -p 9000:9000 \
  -e CLICKHOUSE_PASSWORD=changeme \
  clickhouse/clickhouse-server

# 클라이언트 접속
docker exec -it my-clickhouse clickhouse-client --password changeme
```

⚠️ `CLICKHOUSE_PASSWORD`를 지정하지 않으면 default 사용자가 비밀번호 없이 생성되는데,
그 상태에서는 **외부(호스트) 네트워크 접근이 차단**되어 `-p`로 포트를 열어도
`curl localhost:8123`이 실패한다.

### ClickHouse Cloud (관리형 — 무료 체험)

[clickhouse.com/cloud](https://clickhouse.com/cloud)에서 가입하면 무료 크레딧으로
체험할 수 있다. 브라우저 SQL 콘솔이 함께 제공되어 설치가 아예 필요 없다.
복제·백업·확장이 자동이라(17장) 실전 클러스터 감각을 익히기에 좋다.

### 설치 없이 브라우저에서

- **[sql.clickhouse.com](https://sql.clickhouse.com)** — 공식 플레이그라운드.
  수십억 행짜리 실제 데이터셋이 로드되어 있다. ⚠️ **읽기 전용**(DDL·INSERT 불가) —
  조회·함수 연습 전용이고 모델링·적재 연습은 로컬에서 해야 한다.
  CLI 접속도 된다: `clickhouse client --secure --host play.clickhouse.com --user explorer`
- **[fiddle.clickhouse.com](https://fiddle.clickhouse.com)** — 버전 골라서 DDL부터
  실험 가능 (SQL 공유용)
- **내장 웹 UI `/play`** — 로컬 서버를 띄웠다면 브라우저에서
  `http://localhost:8123/play` (쿼리 편집기 + 자동완성 내장, 26.7+에서 대폭 개선)
- **내장 오프라인 문서 `/docs`** (26.7+) — `http://localhost:8123/docs`에
  **설치된 버전과 정확히 일치하는** 검색 가능한 레퍼런스가 뜬다. 버전 불일치 없는
  문서라는 점에서 학습에 특히 유용하다

## 2.3 clickhouse local — 이 책의 기본 실습 도구

서버 프로세스 없이 SQL을 실행한다. 학습·파일 분석에 최적.

```bash
# 대화형 셸 시작
./clickhouse local

# 한 줄 실행
./clickhouse local --query "SELECT version()"

# ⚠️ 기본적으로 데이터는 임시 — 종료하면 사라진다.
# 상태를 유지하려면 --path로 데이터 디렉토리를 지정:
./clickhouse local --path ./my_data
# 다음에 같은 --path로 실행하면 만들었던 테이블이 그대로 있다

# 파일 즉석 분석 (테이블 없이!)
./clickhouse local --query "
    SELECT count() FROM file('access.log.csv', 'CSVWithNames')"
```

## 2.4 서버 + 클라이언트 모드

실제 서비스처럼 돌려보고 싶을 때:

```bash
# 터미널 1: 서버 시작
./clickhouse server

# 터미널 2: 접속
./clickhouse client
:) SELECT 1;      -- ":)"는 클라이언트 프롬프트
```

### 알아야 할 포트

| 포트 | 프로토콜 | 쓰임 |
|------|----------|------|
| **8123** | HTTP | REST API, 드라이버 다수, 헬스체크 (`curl localhost:8123/ping`) |
| **9000** | Native TCP | clickhouse-client, 고성능 드라이버 |
| 9004 / 9005 | MySQL / PostgreSQL 호환 | 기존 도구로 접속 (`mysql -P 9004 ...`) |
| 8443 / 9440 | HTTPS / Native TLS | 보안 연결 (Cloud는 이 조합) |

```bash
# HTTP로도 쿼리가 된다 — 이 단순함이 ClickHouse 인기 비결 중 하나
curl 'http://localhost:8123/?query=SELECT+version()'
```

### clickhouse-client 주요 옵션

```bash
# --secure: TLS (Cloud 필수) / --query: 비대화형 실행
clickhouse-client \
  --host my-server.clickhouse.cloud \
  --secure \
  --password '...' \
  --query "SELECT 1"

# 대화형에서 유용한 것들
--multiline        # 여러 줄 쿼리 입력 (Enter로 줄바꿈, ; 로 실행)
--format Pretty    # 기본 출력 포맷 지정
```

대화형 셸 단축키·명령 (실기 시험 환경이 바로 이 클라이언트다 — 손에 익혀두면
시험 시간이 절약된다):

| 입력 | 효과 |
|------|------|
| `\l` / `\d` / `\c mydb` | SHOW DATABASES / SHOW TABLES / USE mydb |
| `.` | 직전 쿼리 반복 |
| 위 화살표 | 직전 쿼리 수정 |
| `Ctrl+R` | 히스토리 검색 |
| `Alt+Shift+E` | 외부 에디터로 긴 쿼리 편집 |
| `exit` (또는 Ctrl+D) | 종료 |

## 2.5 서버 설정 파일 위치 (패키지 설치 기준)

| 파일 | 내용 |
|------|------|
| `/etc/clickhouse-server/config.xml` | 서버 설정 (포트, 경로, 클러스터) |
| `/etc/clickhouse-server/users.xml` | 사용자·프로필·쿼터 |
| `/etc/clickhouse-server/config.d/*.xml` | **서버 설정 덮어쓰기 조각** (직접 수정은 여기에 — 원본 보존) |
| `/etc/clickhouse-server/users.d/*.xml` | **사용자 설정 덮어쓰기 조각** (users.xml의 짝) |
| `/var/lib/clickhouse/` | 데이터 디렉토리 |
| `/var/log/clickhouse-server/` | 로그 |

## 2.6 실습 환경 최종 체크

아래가 실행되면 준비 완료다:

```bash
./clickhouse local --query "
CREATE TABLE check (id UInt32, msg String) ENGINE = MergeTree ORDER BY id;
INSERT INTO check VALUES (1, 'ready!');
SELECT * FROM check;
"
-- 1	ready!
```

> 💡 이 책의 예제는 대부분 `clickhouse local`로 충분하다. 예외는 17장(복제/클러스터)과
> 12장의 Refreshable MV 일부(Atomic DB 필요 — 해당 장에 우회법 명시)뿐이다.
