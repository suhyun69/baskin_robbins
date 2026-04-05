#!/usr/bin/env python3
"""
Game Client Agent 실행 진입점

사용법:
  python run_client.py --id agent1 --name "에이전트1"
  python run_client.py --id agent2 --name "에이전트2" --address localhost:50051
"""
import argparse
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)

from client.game_client_agent import GameClientAgent


def main():
    parser = argparse.ArgumentParser(description="베스킨라빈스 31 - Game Client Agent")
    parser.add_argument("--id",      required=True,              help="에이전트 고유 ID")
    parser.add_argument("--name",    required=True,              help="에이전트 표시 이름")
    parser.add_argument("--address", default="localhost:50051",  help="Master 주소 (기본: localhost:50051)")
    args = parser.parse_args()

    print(f"\n[{args.name}] Game Master({args.address})에 접속 시도...\n")
    agent = GameClientAgent(args.id, args.name, args.address)
    asyncio.run(agent.run())


if __name__ == "__main__":
    main()
