# Baskin Robbins 31 - Distributed Game

gRPC 기반 분산 구조로 구현한 **바스킨라빈스 31** 게임입니다.
마스터 서버와 다수의 클라이언트 에이전트가 양방향 스트리밍으로 통신하며 게임을 진행합니다.

## 게임 규칙

- 플레이어들이 순서대로 1부터 숫자를 셉니다.
- 한 번에 1~3개의 연속된 숫자를 말할 수 있습니다.
- **31**을 말하는 플레이어가 집니다.

## 아키텍처

```
┌──────────────┐        gRPC (양방향 스트리밍)        ┌────────────────┐
│    Master    │ ◄──────────────────────────────────► │  Client Agent  │
│  (게임 진행) │                                       │  (전략 기반    │
│  port 50051  │ ◄──────────────────────────────────► │   자동 플레이) │
└──────────────┘                                       └────────────────┘
```

| 컴포넌트 | 설명 |
|----------|------|
| `master/` | gRPC 서버, 게임 상태 관리, 턴 진행 |
| `client/` | 클라이언트 에이전트, 최적 전략 구현 |
| `proto/` | gRPC 서비스 정의 |
| `generated/` | Protobuf 자동 생성 코드 |

### 통신 흐름

1. 클라이언트가 `JoinRequest` 전송 → 마스터가 `JoinConfirm` 응답
2. 모든 플레이어 접속 완료 시 마스터가 `GameStart` 브로드캐스트
3. 마스터가 현재 플레이어에게 `TurnRequest` 전송
4. 플레이어가 숫자를 선택하여 `TurnResponse` 전송
5. 31이 나오면 마스터가 `GameOver` 브로드캐스트

### 전략 (strategy.py)

최적 게임 이론 전략을 구현합니다.

- **안전 지점**: `[2, 6, 10, 14, 18, 22, 26, 30]`
  - 조건: `(31 - target) % 4 == 1`
  - 이 지점에 도달하면 상대방이 반드시 불리한 상황에 처함
- 안전 지점에 1~3수 안에 도달 가능하면 해당 지점으로 이동
- 그렇지 않으면 31을 피해 랜덤 선택

## 실행 방법

### Docker Compose (권장)

```bash
docker-compose up --build
```

마스터 1개 + 클라이언트 에이전트 3개가 자동으로 실행됩니다.

### 로컬 실행

**의존성 설치**

```bash
pip install -r requirements.txt
```

**Proto 파일 생성**

```bash
bash generate_proto.sh
```

**게임 실행 (스크립트)**

```bash
bash run_game.sh
```

**개별 실행**

```bash
# 터미널 1 - 마스터 시작 (3명 대기)
python run_master.py --players 3

# 터미널 2, 3, 4 - 클라이언트 접속
python run_client.py --id 1 --name 플레이어1
python run_client.py --id 2 --name 플레이어2
python run_client.py --id 3 --name 플레이어3
```

### 옵션

| 스크립트 | 옵션 | 기본값 | 설명 |
|----------|------|--------|------|
| `run_master.py` | `--players` | `3` | 참가자 수 |
| `run_client.py` | `--id` | 필수 | 플레이어 ID |
| `run_client.py` | `--name` | 필수 | 플레이어 이름 |
| `run_client.py` | `--address` | `localhost:50051` | 마스터 주소 |

## 기술 스택

- **Python 3.11**
- **gRPC / grpcio** — 양방향 스트리밍 RPC
- **asyncio** — 비동기 처리 전반
- **Protocol Buffers** — 메시지 직렬화
- **Docker / Docker Compose** — 컨테이너 오케스트레이션
- **gRPC Health Check** — 컨테이너 헬스 체크

## 프로젝트 구조

```
baskin_robbins/
├── proto/
│   └── baskinrobbins.proto        # gRPC 서비스 정의
├── generated/                     # Protobuf 자동 생성 코드
├── master/
│   ├── server.py                  # gRPC 서버 설정
│   ├── game_master_agent.py       # 게임 진행 로직
│   └── game_state.py              # 게임 상태 및 플레이어 세션
├── client/
│   ├── game_client_agent.py       # 클라이언트 에이전트
│   └── strategy.py                # 최적 전략 구현
├── run_master.py                  # 마스터 실행 진입점
├── run_client.py                  # 클라이언트 실행 진입점
├── run_game.sh                    # 로컬 테스트 스크립트
├── generate_proto.sh              # Proto 코드 생성 스크립트
├── Dockerfile
└── docker-compose.yml
```
