#!/usr/bin/env bash
# proto 파일로부터 gRPC Python 스텁을 생성한다.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "gRPC 스텁 생성 중..."
python -m grpc_tools.protoc \
  -I proto \
  --python_out=generated \
  --grpc_python_out=generated \
  proto/baskinrobbins.proto

echo "완료: generated/ 디렉토리에 스텁이 생성되었습니다."
