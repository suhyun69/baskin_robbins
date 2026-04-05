#!/usr/bin/env python3
"""
Game Master 실행 진입점

사용법:
  python run_master.py [--players N]

  --players N : 참가 플레이어 수 (기본값 3)
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

from master.server import serve


def main():
    parser = argparse.ArgumentParser(description="베스킨라빈스 31 - Game Master")
    parser.add_argument("--players", type=int, default=3, help="참가 플레이어 수 (기본: 3)")
    args = parser.parse_args()

    print(f"\n베스킨라빈스 31 - Game Master 시작 (플레이어 수: {args.players})\n")
    asyncio.run(serve(args.players))


if __name__ == "__main__":
    main()
