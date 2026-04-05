#!/usr/bin/env bash
# 베스킨라빈스 31 게임을 한 번에 실행한다.
# Master 1개 + Client 3개를 별도 터미널 탭으로 띄운다.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PLAYERS=3
DELAY=1  # 클라이언트 실행 간격(초)

# 이전에 남은 서버 프로세스 정리
pkill -f "run_master.py" 2>/dev/null || true
sleep 0.3

echo "=== 베스킨라빈스 31 게임 시작 ==="
echo "Master 서버를 시작합니다..."

# Master를 백그라운드로 실행 (로그 언버퍼링)
PYTHONUNBUFFERED=1 python3 run_master.py --players $PLAYERS &
MASTER_PID=$!
echo "Master PID: $MASTER_PID"

sleep $DELAY

# Client 순차 실행 (각각 백그라운드)
for i in $(seq 1 $PLAYERS); do
  echo "에이전트 $i 연결..."
  PYTHONUNBUFFERED=1 python3 run_client.py --id "agent$i" --name "에이전트$i" &
  sleep 0.3
done

# Master가 종료될 때까지 대기
wait $MASTER_PID
echo "=== 게임 종료 ==="
