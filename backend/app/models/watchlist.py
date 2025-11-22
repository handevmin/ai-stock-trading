"""관심종목 모델"""
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class Watchlist(Base):
    """관심종목 테이블"""
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(6), nullable=False, index=True, comment="종목코드")
    stock_name = Column(String, comment="종목명")
    notes = Column(Text, comment="메모")
    is_active = Column(Boolean, default=True, comment="활성화 여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")
    
    def __repr__(self):
        return f"<Watchlist(stock_code={self.stock_code}, stock_name={self.stock_name})>"


