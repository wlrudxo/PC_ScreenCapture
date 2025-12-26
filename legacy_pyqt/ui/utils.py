"""
UI 유틸리티 함수
"""


def format_duration(seconds: float, style: str = "korean") -> str:
    """
    초를 시간 형식으로 변환

    Args:
        seconds: 초 단위 시간
        style: "korean" (5시간 30분) 또는 "short" (5h 30m)

    Returns:
        포맷된 시간 문자열
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)

    if style == "short":
        return f"{hours}h {minutes}m"
    else:
        return f"{hours}시간 {minutes}분"
