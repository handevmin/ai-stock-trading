"""전략 관리 API"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.database import get_db
from app.models.strategy import Strategy
from app.utils.logger import logger
from app.services.strategies import create_strategy
from app.services.strategy_engine import strategy_engine

router = APIRouter()


class StrategyCreate(BaseModel):
    """전략 생성 모델"""
    name: str
    description: Optional[str] = None
    strategy_type: Optional[str] = None
    config: Optional[dict] = None
    stock_selection_mode: Optional[str] = "watchlist"  # watchlist, auto, ranking
    auto_selection_config: Optional[dict] = None


class StrategyUpdate(BaseModel):
    """전략 업데이트 모델"""
    name: Optional[str] = None
    description: Optional[str] = None
    strategy_type: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[dict] = None
    stock_selection_mode: Optional[str] = None
    auto_selection_config: Optional[dict] = None


class StrategyResponse(BaseModel):
    """전략 응답 모델"""
    id: int
    name: str
    description: Optional[str]
    strategy_type: Optional[str]
    is_active: bool
    config: Optional[dict]
    stock_selection_mode: Optional[str]
    auto_selection_config: Optional[dict]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("", response_model=StrategyResponse)
async def create_strategy_endpoint(strategy: StrategyCreate, db: Session = Depends(get_db)):
    """전략 생성"""
    # 중복 이름 확인
    existing = db.query(Strategy).filter(Strategy.name == strategy.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 전략 이름입니다.")
    
    try:
        new_strategy = Strategy(
            name=strategy.name,
            description=strategy.description,
            strategy_type=strategy.strategy_type,
            config=strategy.config,
            stock_selection_mode=strategy.stock_selection_mode or "watchlist",
            auto_selection_config=strategy.auto_selection_config,
            is_active=False
        )
        
        db.add(new_strategy)
        db.commit()
        db.refresh(new_strategy)
        
        logger.info(f"전략 생성 완료: {new_strategy.name}")
        
        return StrategyResponse.model_validate(new_strategy)
        
    except Exception as e:
        logger.error(f"전략 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="전략 생성에 실패했습니다.")


@router.get("", response_model=List[StrategyResponse])
async def get_strategies(db: Session = Depends(get_db)):
    """전략 목록 조회"""
    strategies = db.query(Strategy).all()
    return [StrategyResponse.model_validate(s) for s in strategies]


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """전략 상세 조회"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다.")
    
    return StrategyResponse.model_validate(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    strategy_update: StrategyUpdate,
    db: Session = Depends(get_db)
):
    """전략 업데이트"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다.")
    
    try:
        if strategy_update.name is not None:
            # 이름 변경 시 중복 확인
            if strategy_update.name != strategy.name:
                existing = db.query(Strategy).filter(Strategy.name == strategy_update.name).first()
                if existing:
                    raise HTTPException(status_code=400, detail="이미 존재하는 전략 이름입니다.")
            strategy.name = strategy_update.name
        
        if strategy_update.description is not None:
            strategy.description = strategy_update.description
        
        if strategy_update.strategy_type is not None:
            strategy.strategy_type = strategy_update.strategy_type
        
        if strategy_update.is_active is not None:
            strategy.is_active = strategy_update.is_active
        
        if strategy_update.config is not None:
            strategy.config = strategy_update.config
        
        if strategy_update.stock_selection_mode is not None:
            strategy.stock_selection_mode = strategy_update.stock_selection_mode
        
        if strategy_update.auto_selection_config is not None:
            strategy.auto_selection_config = strategy_update.auto_selection_config
        
        db.commit()
        db.refresh(strategy)
        
        logger.info(f"전략 업데이트 완료: {strategy.name}")
        
        return StrategyResponse.model_validate(strategy)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"전략 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail="전략 업데이트에 실패했습니다.")


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """전략 삭제"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다.")
    
    try:
        # 전략 엔진에서도 제거
        strategy_engine.unregister_strategy(strategy.name)
        
        db.delete(strategy)
        db.commit()
        
        logger.info(f"전략 삭제 완료: {strategy_id}")
        
        return {"message": "전략이 삭제되었습니다."}
        
    except Exception as e:
        logger.error(f"전략 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="전략 삭제에 실패했습니다.")


@router.get("/types/list")
async def get_strategy_types():
    """사용 가능한 전략 타입 목록 조회"""
    strategy_types = [
        {
            "type": "moving_average_crossover",
            "name": "이동평균선 교차",
            "description": "단기 이동평균선이 장기 이동평균선을 상향/하향 돌파할 때 매매하는 전략",
            "best_for": "추세장 (상승/하락 추세가 명확한 시장)",
            "risk_level": "중간",
            "recommended": True,
            "performance_note": "가장 검증된 전략 중 하나. 추세가 명확할 때 높은 성공률",
            "default_config": {
                "short_period": 5,
                "long_period": 20,
                "allocation_ratio": 0.1,
                "order_type": "00"
            }
        },
        {
            "type": "rsi",
            "name": "RSI 전략",
            "description": "RSI 지표를 이용한 과매수/과매도 구간에서 매매하는 전략",
            "best_for": "횡보장 (변동성이 큰 시장)",
            "risk_level": "중간",
            "recommended": True,
            "performance_note": "과매수/과매도 구간 포착에 효과적. 단기 매매에 적합",
            "default_config": {
                "rsi_period": 14,
                "oversold": 30,
                "overbought": 70,
                "allocation_ratio": 0.15,
                "order_type": "00"
            }
        },
        {
            "type": "bollinger_bands",
            "name": "볼린저 밴드 전략",
            "description": "볼린저 밴드를 이용한 변동성 기반 매매 전략",
            "best_for": "횡보장 (변동성이 있는 시장)",
            "risk_level": "중간",
            "recommended": True,
            "performance_note": "변동성 기반 전략으로 횡보장에서 효과적",
            "default_config": {
                "period": 20,
                "std_dev": 2,
                "allocation_ratio": 0.12,
                "order_type": "00"
            }
        },
        {
            "type": "macd",
            "name": "MACD 전략",
            "description": "MACD와 시그널선의 교차를 이용한 추세 추종 전략",
            "best_for": "추세장 (중장기 추세가 있는 시장)",
            "risk_level": "중간",
            "recommended": True,
            "performance_note": "추세와 모멘텀을 동시에 분석. 신호가 명확함",
            "default_config": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "allocation_ratio": 0.12,
                "order_type": "00"
            }
        },
        {
            "type": "momentum",
            "name": "모멘텀 전략",
            "description": "가격 상승/하락 모멘텀을 추종하는 단기 매매 전략",
            "best_for": "강세장 (상승 모멘텀이 강한 시장)",
            "risk_level": "높음",
            "recommended": False,
            "performance_note": "단기 매매에 적합하나 변동성이 큼. 신중한 사용 권장",
            "default_config": {
                "period": 10,
                "momentum_threshold": 0.05,
                "allocation_ratio": 0.1,
                "order_type": "00"
            }
        },
        {
            "type": "mean_reversion",
            "name": "평균회귀 전략",
            "description": "가격이 평균에서 벗어나면 회귀할 것으로 예상하여 매매하는 전략",
            "best_for": "횡보장 (명확한 추세가 없는 시장)",
            "risk_level": "중간",
            "recommended": False,
            "performance_note": "횡보장에서 효과적이나 강한 추세장에서는 손실 가능",
            "default_config": {
                "period": 20,
                "deviation_threshold": 0.03,
                "allocation_ratio": 0.1,
                "order_type": "00"
            }
        }
    ]
    
    return {"strategy_types": strategy_types}


@router.post("/{strategy_id}/activate")
async def activate_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """전략 활성화 및 전략 엔진에 등록"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다.")
    
    try:
        # 전략 타입과 설정으로 전략 인스턴스 생성
        if not strategy.strategy_type:
            raise HTTPException(status_code=400, detail="전략 타입이 설정되지 않았습니다.")
        
        config = strategy.config or {}
        
        # 전략 인스턴스 생성
        try:
            strategy_instance = create_strategy(strategy.strategy_type, config)
            logger.info(f"전략 인스턴스 생성 완료: {type(strategy_instance)}")
            
            # 전략 인스턴스 타입 확인
            if not hasattr(strategy_instance, 'name'):
                logger.error(f"전략 인스턴스에 name 속성이 없습니다. 타입: {type(strategy_instance)}")
                raise HTTPException(status_code=500, detail="전략 인스턴스 생성 오류: name 속성이 없습니다.")
            
            # 전략 인스턴스의 name을 데이터베이스의 name으로 설정
            strategy_instance.name = strategy.name
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"전략 인스턴스 생성 실패: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"전략 인스턴스 생성 실패: {str(e)}")
        
        # 전략 인스턴스 활성화
        strategy_instance.is_active = True
        
        # 전략 엔진에 등록
        strategy_engine.register_strategy(strategy_instance)
        
        # 데이터베이스 업데이트
        strategy.is_active = True
        db.commit()
        db.refresh(strategy)
        
        logger.info(f"전략 활성화 완료: {strategy.name}")
        
        return StrategyResponse.model_validate(strategy)
        
    except ValueError as e:
        logger.error(f"전략 활성화 실패: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"전략 활성화 실패: {e}")
        raise HTTPException(status_code=500, detail="전략 활성화에 실패했습니다.")


@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """전략 비활성화"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다.")
    
    try:
        # 전략 엔진에서 제거
        strategy_engine.unregister_strategy(strategy.name)
        
        # 데이터베이스 업데이트
        strategy.is_active = False
        db.commit()
        db.refresh(strategy)
        
        logger.info(f"전략 비활성화 완료: {strategy.name}")
        
        return StrategyResponse.model_validate(strategy)
        
    except Exception as e:
        logger.error(f"전략 비활성화 실패: {e}")
        raise HTTPException(status_code=500, detail="전략 비활성화에 실패했습니다.")

