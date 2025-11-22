"""거래 내역 모델"""
from sqlalchemy import Column, String, Float, DateTime, Integer, Enum as SQLEnum
from sqlalchemy.sql import func
from enum import Enum
from app.database import Base


class OrderSide(str, Enum):
    """주문 방향"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """주문 상태"""
    PENDING = "PENDING"  # 대기
    SUBMITTED = "SUBMITTED"  # 접수
    FILLED = "FILLED"  # 체결
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 부분체결
    CANCELLED = "CANCELLED"  # 취소
    REJECTED = "REJECTED"  # 거부


class Trade(Base):
    """거래 내역 테이블"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String, unique=True, index=True, nullable=False, comment="주문번호")
    stock_code = Column(String, nullable=False, index=True, comment="종목코드")
    stock_name = Column(String, comment="종목명")
    side = Column(SQLEnum(OrderSide), nullable=False, comment="매수/매도")
    order_type = Column(String, comment="주문유형")
    quantity = Column(Integer, nullable=False, comment="주문수량")
    price = Column(Float, nullable=False, comment="주문가격")
    executed_quantity = Column(Integer, default=0, comment="체결수량")
    executed_price = Column(Float, comment="체결가격")
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, comment="주문상태")
    order_time = Column(DateTime(timezone=True), server_default=func.now(), comment="주문시간")
    executed_time = Column(DateTime(timezone=True), comment="체결시간")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")
    
    def __repr__(self):
        return f"<Trade(order_no={self.order_no}, stock_code={self.stock_code}, side={self.side}, status={self.status})>"



