"""유효성 검사 유틸리티"""
from typing import Optional
import re


def validate_stock_code(code: str) -> bool:
    """종목 코드 유효성 검사 (6자리 숫자)"""
    if not code:
        return False
    return bool(re.match(r"^\d{6}$", code))


def validate_order_type(order_type: str) -> bool:
    """주문 유형 유효성 검사"""
    valid_types = ["00", "01", "02", "03", "05", "06", "07", "10", "13", "16"]
    return order_type in valid_types


def validate_order_side(side: str) -> bool:
    """매수/매도 유효성 검사"""
    return side.upper() in ["BUY", "SELL"] or side in ["매수", "매도"]


def validate_price(price: float, min_price: float = 0.0) -> bool:
    """가격 유효성 검사"""
    return price >= min_price


def validate_quantity(quantity: int, min_quantity: int = 1) -> bool:
    """수량 유효성 검사"""
    return isinstance(quantity, int) and quantity >= min_quantity


def sanitize_error_message(message: str) -> str:
    """에러 메시지에서 민감 정보 제거"""
    # API 키나 계좌번호 같은 민감 정보 제거
    patterns = [
        (r'app_key["\']?\s*[:=]\s*["\']?[^"\']+', "app_key=***"),
        (r'app_secret["\']?\s*[:=]\s*["\']?[^"\']+', "app_secret=***"),
        (r'account_no["\']?\s*[:=]\s*["\']?[^"\']+', "account_no=***"),
    ]
    
    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized

