"""
집중 모드 시간대 유틸리티
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

DEFAULT_BLOCK_START = "09:00"
DEFAULT_BLOCK_END = "18:00"


def is_in_block_time(start_time: Optional[str], end_time: Optional[str], now: Optional[datetime] = None) -> bool:
    """현재 시간이 차단 시간대 내인지 확인 (자정 넘김 지원)."""
    if not start_time or not end_time:
        return False  # 시간 미설정 = 차단 안 함 (설정 잠금 방지)

    try:
        now = now or datetime.now()
        current_minutes = now.hour * 60 + now.minute

        start_h, start_m = map(int, start_time.split(":"))
        end_h, end_m = map(int, end_time.split(":"))
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        if start_minutes <= end_minutes:
            return start_minutes <= current_minutes < end_minutes
        return current_minutes >= start_minutes or current_minutes < end_minutes
    except Exception:
        return False  # 파싱 실패 시에도 차단 안 함 (오류 시 해제 방향)
