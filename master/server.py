import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from generated import baskinrobbins_pb2_grpc as pb2_grpc
from master.game_master_agent import GameMasterServicer

logger = logging.getLogger(__name__)

HOST = "[::]:50051"


async def serve(expected_players: int):
    servicer = GameMasterServicer(expected_players)
    health_servicer = health.HealthServicer()

    server = grpc.aio.server()
    pb2_grpc.add_GameMasterServiceServicer_to_server(servicer, server)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    server.add_insecure_port(HOST)

    # 서버 시작 직후 SERVING 상태로 표시 → healthcheck 통과
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    await server.start()
    logger.info(f"[Master] gRPC 서버 시작: {HOST}")
    logger.info(f"[Master] {expected_players}명의 플레이어를 기다리는 중...")

    # 게임 루프를 서버 레벨 태스크로 시작 (all_joined 이벤트를 기다림)
    asyncio.create_task(servicer.game_loop())

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("[Master] 서버 종료")
        await server.stop(grace=3)
