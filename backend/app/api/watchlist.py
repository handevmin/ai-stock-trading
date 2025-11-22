"""관심종목 관리 API"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.watchlist import Watchlist
from app.utils.logger import logger
from app.utils.validators import validate_stock_code

router = APIRouter()


class WatchlistCreate(BaseModel):
    """관심종목 생성 모델"""
    stock_code: str
    stock_name: Optional[str] = None
    notes: Optional[str] = None


class WatchlistResponse(BaseModel):
    """관심종목 응답 모델"""
    id: int
    stock_code: str
    stock_name: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[WatchlistResponse])
async def get_watchlist(db: Session = Depends(get_db)):
    """관심종목 목록 조회"""
    watchlist_items = db.query(Watchlist).filter(Watchlist.is_active == True).all()
    return [WatchlistResponse.model_validate(item) for item in watchlist_items]


@router.post("", response_model=WatchlistResponse)
async def add_to_watchlist(watchlist_item: WatchlistCreate, db: Session = Depends(get_db)):
    """관심종목 추가"""
    if not validate_stock_code(watchlist_item.stock_code):
        raise HTTPException(status_code=400, detail="유효하지 않은 종목 코드입니다.")
    
    # 중복 확인
    existing = db.query(Watchlist).filter(
        Watchlist.stock_code == watchlist_item.stock_code,
        Watchlist.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="이미 관심종목에 추가된 종목입니다.")
    
    try:
        new_item = Watchlist(
            stock_code=watchlist_item.stock_code,
            stock_name=watchlist_item.stock_name,
            notes=watchlist_item.notes,
            is_active=True
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        logger.info(f"관심종목 추가: {new_item.stock_code}")
        
        return WatchlistResponse.model_validate(new_item)
        
    except Exception as e:
        db.rollback()
        logger.error(f"관심종목 추가 실패: {e}")
        raise HTTPException(status_code=500, detail="관심종목 추가에 실패했습니다.")


@router.delete("/{watchlist_id}")
async def remove_from_watchlist(watchlist_id: int, db: Session = Depends(get_db)):
    """관심종목 제거"""
    watchlist_item = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    
    if not watchlist_item:
        raise HTTPException(status_code=404, detail="관심종목을 찾을 수 없습니다.")
    
    try:
        watchlist_item.is_active = False
        db.commit()
        
        logger.info(f"관심종목 제거: {watchlist_item.stock_code}")
        
        return {"message": "관심종목에서 제거되었습니다.", "id": watchlist_id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"관심종목 제거 실패: {e}")
        raise HTTPException(status_code=500, detail="관심종목 제거에 실패했습니다.")


@router.get("/stock-codes")
async def get_watchlist_stock_codes(db: Session = Depends(get_db)):
    """관심종목 코드 목록만 조회 (전략 실행용)"""
    watchlist_items = db.query(Watchlist).filter(Watchlist.is_active == True).all()
    return {
        "stock_codes": [item.stock_code for item in watchlist_items],
        "count": len(watchlist_items)
    }


