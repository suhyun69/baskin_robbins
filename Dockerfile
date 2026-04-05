FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# proto 컴파일 (빌드 타임에 stubs 생성)
COPY proto/ proto/
RUN mkdir -p generated && \
    python -m grpc_tools.protoc \
      -I proto \
      --python_out=generated \
      --grpc_python_out=generated \
      proto/baskinrobbins.proto && \
    # protoc가 생성한 절대 import를 패키지 상대 import로 교정
    sed -i \
      's/^import baskinrobbins_pb2/from generated import baskinrobbins_pb2/' \
      generated/baskinrobbins_pb2_grpc.py && \
    touch generated/__init__.py

# 소스 복사 (generated는 위에서 이미 생성되었으므로 제외)
COPY master/ master/
COPY client/ client/
COPY run_master.py run_client.py ./
RUN touch master/__init__.py client/__init__.py

ENV PYTHONUNBUFFERED=1
