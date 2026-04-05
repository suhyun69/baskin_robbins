import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generated import baskinrobbins_pb2 as pb2
from generated import baskinrobbins_pb2_grpc as pb2_grpc
from master.game_state import GameState, PlayerSession

logger = logging.getLogger(__name__)


class GameMasterServicer(pb2_grpc.GameMasterServiceServicer):
    """
    gRPC 서비스 구현체.
    각 클라이언트와 양방향 스트리밍을 유지하며
    게임 루프는 별도 asyncio Task로 실행된다.
    """

    def __init__(self, expected_players: int):
        self.state = GameState(expected_players)

    # ──────────────────────────────────────────────────────────────
    # gRPC 핸들러
    # ──────────────────────────────────────────────────────────────

    async def JoinGame(self, request_iterator, context):
        """
        클라이언트 연결 당 하나의 양방향 스트림을 처리한다.
        async generator(yield) 대신 context.write()를 사용해
        grpc.aio의 __anext__ 호출 타이밍에 의존하지 않는다.

        흐름:
          1. JoinRequest 수신 → PlayerSession 등록
          2. context.write(JoinConfirm) 전송
          3. 백그라운드 태스크: 클라이언트 메시지를 recv_queue에 누적
          4. send_queue에서 꺼낸 메시지를 context.write()로 전달
        """
        # 1. 첫 메시지 = JoinRequest
        try:
            first = await request_iterator.__anext__()
        except StopAsyncIteration:
            logger.warning("[Master] 스트림이 JoinRequest 없이 종료됨")
            return

        join = first.join_request
        logger.info(f"[Master] ← JoinRequest: {join.player_id} ({join.player_name})")

        # 2. 플레이어 등록
        session = await self.state.register_player(join.player_id, join.player_name)

        # 3. JoinConfirm 전송 (context.write 사용 → 즉시 전송 보장)
        await context.write(
            pb2.MasterMessage(
                join_confirm=pb2.JoinConfirm(
                    player_id=join.player_id,
                    assigned_order=session.order,
                    message=(
                        f"{join.player_name}님, {session.order}번 플레이어로 "
                        f"등록되었습니다. 다른 플레이어를 기다리는 중..."
                    ),
                )
            )
        )

        # 4. 백그라운드: 클라이언트 → recv_queue
        async def _read_client():
            try:
                async for msg in request_iterator:
                    await session.recv_queue.put(msg)
            except Exception as e:
                logger.debug(f"[Master] {join.player_name} 읽기 종료: {e}")
            finally:
                await session.recv_queue.put(None)

        asyncio.create_task(_read_client())

        # 6. send_queue → context.write() (None이 오면 스트림 종료)
        while True:
            msg = await session.send_queue.get()
            if msg is None:
                logger.info(f"[Master] {join.player_name} 스트림 종료")
                return
            await context.write(msg)

    # ──────────────────────────────────────────────────────────────
    # 게임 루프 (serve()에서 최상위 태스크로 시작됨)
    # ──────────────────────────────────────────────────────────────

    async def game_loop(self):
        """
        게임 진행을 총괄하는 루프.
        - 전체 브로드캐스트: GameStart, GameOver
        - 개별 알림: TurnRequest (해당 플레이어에게만)
        """
        await self.state.all_joined.wait()

        players = self.state.players_by_order
        names = [p.player_name for p in players]

        logger.info(f"\n{'='*50}")
        logger.info(f"[Master] 게임 시작! 참가자: {', '.join(names)}")
        logger.info(f"{'='*50}\n")

        # GameStart 브로드캐스트
        start_msg = pb2.MasterMessage(
            game_start=pb2.GameStart(
                total_players=len(players),
                player_names=names,
                message=(
                    f"베스킨라빈스 31 게임을 시작합니다! "
                    f"참가자: {', '.join(names)}"
                ),
            )
        )
        for p in players:
            await p.send_queue.put(start_msg)

        # 게임 진행
        current_number = 0
        turn_index = 0

        while True:
            player = players[turn_index]
            start = current_number + 1

            logger.info(
                f"[Master] → TurnRequest: {player.player_name} "
                f"(시작 번호: {start})"
            )

            # TurnRequest 전송 (해당 플레이어에게만)
            await player.send_queue.put(
                pb2.MasterMessage(
                    turn_request=pb2.TurnRequest(
                        player_id=player.player_id,
                        start_number=start,
                        max_count=3,
                    )
                )
            )

            # TurnResponse 대기
            msg = await player.recv_queue.get()
            if msg is None:
                logger.error(f"[Master] {player.player_name} 연결 끊김")
                break

            resp = msg.turn_response
            numbers = list(resp.numbers)
            logger.info(f"[Master] ← TurnResponse: {player.player_name} → {numbers}")

            # 유효성 검사 (잘못된 응답이면 최소 1개로 처리)
            if not self._validate(numbers, start):
                logger.warning(
                    f"[Master] 잘못된 응답 {numbers} (start={start}), "
                    f"{start}만 말한 것으로 처리"
                )
                numbers = [start]

            # 31 판정
            if 31 in numbers:
                logger.info(
                    f"\n{'='*50}\n"
                    f"[Master] {player.player_name}이(가) 31을 말했습니다! 패배!\n"
                    f"{'='*50}\n"
                )
                game_over_msg = pb2.MasterMessage(
                    game_over=pb2.GameOver(
                        loser_id=player.player_id,
                        loser_name=player.player_name,
                        losing_number=31,
                        message=(
                            f"{player.player_name}이(가) 31을 말해서 패배했습니다! "
                            f"게임 종료."
                        ),
                    )
                )
                # 전체 브로드캐스트 후 스트림 종료
                for p in players:
                    await p.send_queue.put(game_over_msg)
                    await p.send_queue.put(None)
                break

            current_number = max(numbers)
            turn_index = (turn_index + 1) % len(players)

        logger.info("[Master] 게임 루프 종료")

    # ──────────────────────────────────────────────────────────────
    # 유효성 검사
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _validate(numbers: list, start: int) -> bool:
        """숫자 목록이 start부터 연속된 1~3개인지 검사한다."""
        if not numbers or len(numbers) > 3:
            return False
        expected = list(range(start, start + len(numbers)))
        return numbers == expected
