"""자동매매 실행 API"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import asyncio

from app.database import get_db
from app.models.strategy import Strategy
from app.models.watchlist import Watchlist
from app.services.strategy_engine import strategy_engine
from app.services.kis_client import KISClient
from app.services.scheduler import auto_trading_scheduler
from app.utils.logger import logger
from app.utils.market_time import get_market_status

router = APIRouter()


class SchedulerConfig(BaseModel):
    """스케줄러 설정 모델"""
    interval_seconds: int = 60  # 실행 간격 (초) - schedule_type이 "interval"일 때만 사용
    schedule_type: str = "interval"  # "interval" (주기적 실행) 또는 "daily" (하루 한번)


@router.post("/execute")
async def execute_auto_trading(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    자동매매 실행
    
    모든 활성 전략에 대해:
    1. 종목 선택 모드에 따라 종목 리스트 가져오기
       - watchlist: 관심종목 사용
       - auto: 자동 선택 (등락률/거래량 기반)
       - ranking: 랭킹 기반 선택
    2. 각 종목에 대해 전략 실행
    3. 매수/매도 신호 발생 시 주문 실행
    """
    try:
        active_strategies = db.query(Strategy).filter(Strategy.is_active == True).all()
        
        if not active_strategies:
            return {"message": "활성화된 전략이 없습니다.", "signals": []}
        
        all_signals = []
        
        for strategy in active_strategies:
            # 종목 선택 모드에 따라 종목 리스트 가져오기
            stock_codes = []
            
            if strategy.stock_selection_mode == "watchlist":
                # 관심종목 사용
                watchlist_items = db.query(Watchlist).filter(Watchlist.is_active == True).all()
                stock_codes = [item.stock_code for item in watchlist_items]
                logger.info(f"전략 '{strategy.name}': 관심종목 {len(stock_codes)}개 사용")
            
            elif strategy.stock_selection_mode == "auto":
                # 자동 선택
                auto_config = strategy.auto_selection_config or {}
                selection_mode = auto_config.get("mode", "ranking")  # ranking, volume, trend
                criteria = auto_config.get("criteria", {})
                
                stock_codes = await strategy_engine.get_auto_selected_stocks(
                    selection_mode=selection_mode,
                    criteria=criteria
                )
                logger.info(f"전략 '{strategy.name}': 자동 선택 종목 {len(stock_codes)}개")
            
            elif strategy.stock_selection_mode == "ranking":
                # 랭킹 기반 선택
                auto_config = strategy.auto_selection_config or {}
                criteria = auto_config.get("criteria", {"max_stocks": 10})
                
                stock_codes = await strategy_engine.get_auto_selected_stocks(
                    selection_mode="ranking",
                    criteria=criteria
                )
                logger.info(f"전략 '{strategy.name}': 랭킹 기반 선택 종목 {len(stock_codes)}개")
            
            if not stock_codes:
                logger.warning(f"전략 '{strategy.name}': 선택된 종목이 없습니다.")
                continue
            
            # 전략 실행
            signals = await strategy_engine.run_all_strategies(stock_codes)
            
            # 신호가 있으면 주문 실행
            for signal in signals:
                try:
                    kis_client = KISClient()
                    result = await kis_client.place_order(
                        stock_code=signal["stock_code"],
                        side=signal["action"],
                        quantity=signal["quantity"],
                        price=signal["price"],
                        order_type=signal.get("order_type", "00")
                    )
                    
                    logger.info(f"자동매매 주문 실행: {signal['action']} {signal['stock_code']} {signal['quantity']}주 @ {signal['price']}원")
                    all_signals.append({
                        **signal,
                        "order_no": result.get("output", {}).get("ODNO", ""),
                        "status": "executed"
                    })
                    
                except Exception as e:
                    logger.error(f"자동매매 주문 실행 실패: {e}")
                    all_signals.append({
                        **signal,
                        "status": "failed",
                        "error": str(e)
                    })
        
        return {
            "message": f"{len(all_signals)}개의 매매 신호 처리 완료",
            "signals": all_signals
        }
        
    except Exception as e:
        logger.error(f"자동매매 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=f"자동매매 실행에 실패했습니다: {str(e)}")


@router.get("/status")
async def get_auto_trading_status(db: Session = Depends(get_db)):
    """자동매매 상태 조회"""
    active_strategies = db.query(Strategy).filter(Strategy.is_active == True).all()
    watchlist_count = db.query(Watchlist).filter(Watchlist.is_active == True).count()
    scheduler_status = auto_trading_scheduler.get_status()
    market_status = get_market_status()
    
    status = {
        "active_strategies": len(active_strategies),
        "watchlist_count": watchlist_count,
        "scheduler": scheduler_status,
        "market": market_status,
        "strategies": []
    }
    
    for strategy in active_strategies:
        status["strategies"].append({
            "id": strategy.id,
            "name": strategy.name,
            "stock_selection_mode": strategy.stock_selection_mode or "watchlist",
            "auto_selection_config": strategy.auto_selection_config
        })
    
    return status


@router.post("/scheduler/start")
async def start_scheduler(config: SchedulerConfig):
    """자동매매 스케줄러 시작"""
    try:
        if config.schedule_type not in ["interval", "daily"]:
            raise HTTPException(status_code=400, detail="schedule_type은 'interval' 또는 'daily'여야 합니다.")
        
        if config.schedule_type == "interval":
            if config.interval_seconds < 10:
                raise HTTPException(status_code=400, detail="실행 간격은 최소 10초 이상이어야 합니다.")
        
        if auto_trading_scheduler.is_running:
            # 이미 실행 중이면 설정만 업데이트
            auto_trading_scheduler.update_schedule(config.interval_seconds, config.schedule_type)
            if config.schedule_type == "daily":
                message = "스케줄러가 매일 오전 9시 5분에 실행되도록 업데이트되었습니다."
            else:
                message = f"스케줄러 실행 간격이 {config.interval_seconds}초로 업데이트되었습니다."
            return {
                "message": message,
                "status": auto_trading_scheduler.get_status()
            }
        else:
            auto_trading_scheduler.start(config.interval_seconds, config.schedule_type)
            if config.schedule_type == "daily":
                message = "자동매매 스케줄러가 시작되었습니다. (매일 오전 9시 5분 실행)"
            else:
                message = f"자동매매 스케줄러가 시작되었습니다. ({config.interval_seconds}초 간격)"
            return {
                "message": message,
                "status": auto_trading_scheduler.get_status()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"스케줄러 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=f"스케줄러 시작에 실패했습니다: {str(e)}")


@router.post("/scheduler/stop")
async def stop_scheduler():
    """자동매매 스케줄러 중지"""
    try:
        if not auto_trading_scheduler.is_running:
            return {
                "message": "실행 중인 스케줄러가 없습니다.",
                "status": auto_trading_scheduler.get_status()
            }
        
        auto_trading_scheduler.stop()
        return {
            "message": "자동매매 스케줄러가 중지되었습니다.",
            "status": auto_trading_scheduler.get_status()
        }
    except Exception as e:
        logger.error(f"스케줄러 중지 실패: {e}")
        raise HTTPException(status_code=500, detail=f"스케줄러 중지에 실패했습니다: {str(e)}")

