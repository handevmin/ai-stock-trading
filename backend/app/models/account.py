"""계좌 정보 모델"""
from sqlalchemy import Column, String, Float, DateTime, Integer
from sqlalchemy.sql import func
from app.database import Base


class Account(Base):
    """계좌 정보 테이블"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_no = Column(String, unique=True, index=True, nullable=False, comment="계좌번호")
    account_name = Column(String, comment="계좌명")
    total_balance = Column(Float, default=0.0, comment="총 자산")
    available_balance = Column(Float, default=0.0, comment="가용 자산")
    invested_amount = Column(Float, default=0.0, comment="투자 원금")
    profit_loss = Column(Float, default=0.0, comment="손익")
    profit_loss_rate = Column(Float, default=0.0, comment="손익률")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")
    
    def __repr__(self):
        return f"<Account(account_no={self.account_no}, total_balance={self.total_balance})>"



