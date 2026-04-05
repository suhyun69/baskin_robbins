import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import grpc
from generated import baskinrobbins_pb2 as pb2
from generated import baskinrobbins_pb2_grpc as pb2_grpc
from client.strategy import choose_numbers

logger = logging.getLogger(__name__)


class GameClientAgent:
    """
    Game Master에 연결해 베스킨라빈스 31 게임에 참가하는 클라이언트 에이전트.

    흐름:
      1. JoinRequest 전송
      2. JoinConfirm 수신 (순서 배정 확인)
      3. GameStart 수신 (게임 시작 확인)
      4. TurnRequest 수신 → 숫자 선택 → TurnResponse 전송 (반복)
      5. GameOver 수신 → 종료
    """

    def __init__(self, player_id: str, player_name: str, master_address: str = "localhost:50051"):
        self.player_id = player_id
        self.player_name = player_name
        self.master_address = master_address

    async def run(self):
        channel = grpc.aio.insecure_channel(self.master_address)

        # Master가 완전히 준비될 때까지 대기 (Docker 환경 대비)
        logger.info(f"[{self.player_name}] Master 연결 대기 중...")
        await asyncio.wait_for(channel.channel_ready(), timeout=30)
        logger.info(f"[{self.player_name}] Master 연결 성공")

        stub = pb2_grpc.GameMasterServiceStub(channel)

        # 송신 큐: 비동기 제너레이터가 이 큐에서 메시지를 꺼내 Master로 전송
        send_queue: asyncio.Queue[pb2.PlayerMessage | None] = asyncio.Queue()

        async def _outbound():
            """send_queue → Master 스트림"""
            while True:
                msg = await send_queue.get()
                if msg is None:
                    return
                yield msg

        # JoinRequest를 제일 먼저 큐에 넣고 스트림 시작
        await send_queue.put(
            pb2.PlayerMessage(
                join_request=pb2.JoinRequest(
                    player_id=self.player_id,
                    player_name=self.player_name,
                )
            )
        )

        call = stub.JoinGame(_outbound())

        try:
            async for master_msg in call:
                which = master_msg.WhichOneof("payload")

                if which == "join_confirm":
                    conf = master_msg.join_confirm
                    logger.info(
                        f"[{self.player_name}] ← JoinConfirm: {conf.message}"
                    )

                elif which == "game_start":
                    gs = master_msg.game_start
                    logger.info(f"[{self.player_name}] ← GameStart: {gs.message}")

                elif which == "turn_request":
                    tr = master_msg.turn_request
                    logger.info(
                        f"[{self.player_name}] ← TurnRequest: "
                        f"시작={tr.start_number}, 최대={tr.max_count}개"
                    )

                    numbers = choose_numbers(tr.start_number, tr.max_count)
                    logger.info(
                        f"[{self.player_name}] → TurnResponse: {numbers} 선택"
                    )

                    await send_queue.put(
                        pb2.PlayerMessage(
                            turn_response=pb2.TurnResponse(
                                player_id=self.player_id,
                                numbers=numbers,
                            )
                        )
                    )

                elif which == "game_over":
                    go = master_msg.game_over
                    logger.info(f"[{self.player_name}] ← GameOver: {go.message}")
                    if go.loser_id == self.player_id:
                        logger.info(f"[{self.player_name}] 나(가) 졌습니다...")
                    else:
                        logger.info(f"[{self.player_name}] 살았다! 승리!")
                    # 송신 스트림 종료
                    await send_queue.put(None)
                    break

        except grpc.aio.AioRpcError as e:
            logger.error(f"[{self.player_name}] gRPC 오류: {e.code()} - {e.details()}")
        finally:
            await channel.close()
            logger.info(f"[{self.player_name}] 채널 종료")
