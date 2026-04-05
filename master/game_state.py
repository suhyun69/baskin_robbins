import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlayerSession:
    player_id: str
    player_name: str
    order: int
    send_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    recv_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class GameState:
    def __init__(self, expected_players: int):
        self.expected_players = expected_players
        self.sessions: dict[str, PlayerSession] = {}
        self.players_by_order: List[PlayerSession] = []
        self.current_number: int = 0
        self.game_active: bool = False
        self.all_joined: asyncio.Event = asyncio.Event()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def register_player(self, player_id: str, player_name: str) -> PlayerSession:
        async with self._lock:
            if player_id in self.sessions:
                return self.sessions[player_id]

            order = len(self.sessions) + 1
            session = PlayerSession(player_id, player_name, order)
            self.sessions[player_id] = session

            logger.info(
                f"[Master] 플레이어 등록: {player_name} "
                f"({order}/{self.expected_players})"
            )

            if len(self.sessions) == self.expected_players:
                self.players_by_order = sorted(
                    self.sessions.values(), key=lambda s: s.order
                )
                self.all_joined.set()
                logger.info("[Master] 모든 플레이어 등록 완료 → 게임 시작 대기")

            return session
