"""전략 설정 모델"""
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class Strategy(Base):
    """전략 설정 테이블"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True, comment="전략명")
    description = Column(Text, comment="전략 설명")
    strategy_type = Column(String, comment="전략 유형")
    is_active = Column(Boolean, default=False, comment="활성화 여부")
    config = Column(JSON, comment="전략 설정 (JSON)")
    stock_selection_mode = Column(String, default="watchlist", comment="종목 선택 모드: watchlist(관심종목), auto(자동선택), ranking(랭킹기반)")
    auto_selection_config = Column(JSON, comment="자동 종목 선택 설정 (JSON) - stock_selection_mode가 auto일 때 사용")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")
    
    def __repr__(self):
        return f"<Strategy(name={self.name}, is_active={self.is_active})>"


