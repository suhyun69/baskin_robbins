"""
베스킨라빈스 31 숫자 선택 전략

최적 전략:
  safe_targets = [2, 6, 10, 14, 18, 22, 26, 30]
  → (31 - target) % 4 == 1 인 번호

  이 번호에서 턴을 마치면 상대가 어떤 선택을 해도
  다음 safe_target에 도달할 수 있다.

  30을 말하면 상대는 반드시 31을 말해야 하므로 승리 확정.
"""
import random


# (31 - t) % 4 == 1 인 t: 2, 6, 10, 14, 18, 22, 26, 30
SAFE_TARGETS = [t for t in range(2, 31) if (31 - t) % 4 == 1]


def choose_numbers(start: int, max_count: int = 3) -> list[int]:
    """
    start부터 시작해 말할 숫자 목록을 반환한다.

    1. safe_target에 도달 가능하면 그 번호까지 말한다.
    2. 불가능하면 31을 피하면서 랜덤하게 1~3개 말한다.
    3. start가 이미 31이면 [31]을 반환한다 (패배).
    """
    if start == 31:
        return [31]

    # safe_target에 1~max_count 범위 내에서 도달 가능한지 확인
    for count in range(1, max_count + 1):
        end = start + count - 1
        if end > 31:
            break
        if end in SAFE_TARGETS:
            return list(range(start, end + 1))

    # safe_target 불가 → 31을 피하면서 선택
    available_counts = []
    for count in range(1, max_count + 1):
        end = start + count - 1
        if end > 31:
            break
        if end < 31:
            available_counts.append(count)

    if not available_counts:
        # 어떻게 해도 31을 말해야 하는 상황
        return [31]

    count = random.choice(available_counts)
    return list(range(start, start + count))
