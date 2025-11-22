"""시장 시간 유틸리티"""
from datetime import datetime, time
from typing import Optional
import pytz

# 한국 시간대
KOREA_TZ = pytz.timezone('Asia/Seoul')


def is_market_open(current_time: Optional[datetime] = None) -> bool:
    """
    주식시장이 열려있는지 확인
    
    한국 주식시장 시간:
    - 정규장: 09:00 ~ 15:30
    - 장전시간외: 08:00 ~ 09:00
    - 장후시간외: 15:30 ~ 16:00
    
    Args:
        current_time: 확인할 시간 (None이면 현재 시간)
    
    Returns:
        시장이 열려있으면 True
    """
    if current_time is None:
        current_time = datetime.now(KOREA_TZ)
    else:
        # timezone이 없으면 한국 시간으로 가정
        if current_time.tzinfo is None:
            current_time = KOREA_TZ.localize(current_time)
    
    # 주말 체크 (토요일=5, 일요일=6)
    weekday = current_time.weekday()
    if weekday >= 5:  # 토요일 또는 일요일
        return False
    
    # 공휴일 체크 (간단한 버전 - 실제로는 공휴일 API를 사용해야 함)
    # 여기서는 주말만 체크하고, 공휴일은 별도로 처리 필요
    
    current_time_only = current_time.time()
    
    # 정규장 시간: 09:00 ~ 15:30
    market_open = time(9, 0)
    market_close = time(15, 30)
    
    return market_open <= current_time_only <= market_close


def get_next_market_open_time(current_time: Optional[datetime] = None) -> datetime:
    """
    다음 시장 오픈 시간 반환
    
    Args:
        current_time: 기준 시간 (None이면 현재 시간)
    
    Returns:
        다음 시장 오픈 시간
    """
    if current_time is None:
        current_time = datetime.now(KOREA_TZ)
    else:
        if current_time.tzinfo is None:
            current_time = KOREA_TZ.localize(current_time)
    
    # 오늘 날짜로 9시 설정
    next_open = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # 이미 오늘 9시가 지났으면 내일 9시
    if current_time.time() >= time(9, 0):
        from datetime import timedelta
        next_open = next_open + timedelta(days=1)
    
    # 주말이면 다음 월요일로
    while next_open.weekday() >= 5:
        from datetime import timedelta
        next_open = next_open + timedelta(days=1)
    
    return next_open


def get_market_status() -> dict:
    """
    현재 시장 상태 반환
    
    Returns:
        {
            "is_open": bool,
            "current_time": str,
            "next_open_time": str
        }
    """
    now = datetime.now(KOREA_TZ)
    is_open = is_market_open(now)
    next_open = get_next_market_open_time(now)
    
    return {
        "is_open": is_open,
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "next_open_time": next_open.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "market_hours": "09:00 ~ 15:30"
    }


