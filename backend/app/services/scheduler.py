"""자동매매 스케줄러 서비스"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from typing import Optional
import asyncio

from app.database import SessionLocal
from app.models.strategy import Strategy
from app.models.watchlist import Watchlist
from app.services.strategy_engine import strategy_engine
from app.services.kis_client import KISClient
from app.utils.logger import logger
from app.utils.market_time import is_market_open, get_next_market_open_time
from datetime import datetime
import pytz

class AutoTradingScheduler:
    """자동매매 스케줄러"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        self.interval_seconds = 60  # 기본 1분
        self.schedule_type = "interval"  # "interval" 또는 "daily"
        self.korea_tz = pytz.timezone('Asia/Seoul')
    
    def start(self, interval_seconds: int = 60, schedule_type: str = "interval"):
        """
        스케줄러 시작
        
        Args:
            interval_seconds: 실행 간격 (초) - schedule_type이 "interval"일 때만 사용
            schedule_type: "interval" (주기적 실행) 또는 "daily" (하루 한번)
        """
        if self.is_running:
            logger.warning("스케줄러가 이미 실행 중입니다.")
            return
        
        self.interval_seconds = interval_seconds
        self.schedule_type = schedule_type
        self.scheduler = AsyncIOScheduler(timezone='Asia/Seoul')
        
        if schedule_type == "daily":
            # 하루 한번 실행: 매일 오전 9시 5분 (시장 오픈 직후)
            trigger = CronTrigger(hour=9, minute=5, timezone='Asia/Seoul')
            logger.info("자동매매 스케줄러 시작: 매일 오전 9시 5분 실행")
        else:
            # 주기적 실행
            trigger = IntervalTrigger(seconds=interval_seconds)
            logger.info(f"자동매매 스케줄러 시작: {interval_seconds}초 간격")
        
        # 주기적 실행 작업 등록
        self.scheduler.add_job(
            self._execute_auto_trading,
            trigger=trigger,
            id="auto_trading_job",
            replace_existing=True,
            max_instances=1  # 동시 실행 방지
        )
        
        self.scheduler.start()
        self.is_running = True
    
    def stop(self):
        """스케줄러 중지"""
        if not self.is_running or not self.scheduler:
            logger.warning("실행 중인 스케줄러가 없습니다.")
            return
        
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("자동매매 스케줄러 중지")
    
    def update_schedule(self, interval_seconds: int, schedule_type: str):
        """실행 간격 및 타입 업데이트"""
        if not self.is_running or not self.scheduler:
            logger.warning("실행 중인 스케줄러가 없습니다.")
            return
        
        self.interval_seconds = interval_seconds
        self.schedule_type = schedule_type
        
        if schedule_type == "daily":
            trigger = CronTrigger(hour=9, minute=5, timezone='Asia/Seoul')
            logger.info("자동매매 실행 간격 업데이트: 매일 오전 9시 5분")
        else:
            trigger = IntervalTrigger(seconds=interval_seconds)
            logger.info(f"자동매매 실행 간격 업데이트: {interval_seconds}초")
        
        self.scheduler.reschedule_job(
            "auto_trading_job",
            trigger=trigger
        )
    
    async def _execute_auto_trading(self):
        """자동매매 실행 (스케줄러에서 호출)"""
        logger.info("[자동매매] 스케줄러 실행 시작")
        
        # 시장 시간 체크
        current_time = datetime.now(self.korea_tz)
        market_status = is_market_open(current_time)
        
        if not market_status:
            logger.info(f"[자동매매] 시장이 열려있지 않아 건너뜁니다. (현재 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')})")
            return
        
        logger.info(f"[자동매매] 시장 개장 중 - 실행 진행 (현재 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        try:
            db = SessionLocal()
            try:
                active_strategies = db.query(Strategy).filter(Strategy.is_active == True).all()
                
                if not active_strategies:
                    logger.info("[자동매매] 활성화된 전략이 없어 건너뜁니다.")
                    return
                
                logger.info(f"[자동매매] 활성화된 전략 {len(active_strategies)}개 발견")
                
                all_signals = []
                
                for strategy in active_strategies:
                    # 종목 선택 모드에 따라 종목 리스트 가져오기
                    stock_codes = []
                    
                    if strategy.stock_selection_mode == "watchlist":
                        # 관심종목 사용
                        watchlist_items = db.query(Watchlist).filter(Watchlist.is_active == True).all()
                        stock_codes = [item.stock_code for item in watchlist_items]
                        logger.info(f"[자동매매] 전략 '{strategy.name}': 관심종목 {len(stock_codes)}개 사용")
                    
                    elif strategy.stock_selection_mode == "auto" or strategy.stock_selection_mode == "ranking":
                        # 자동 선택 (랭킹 기반)
                        auto_config = strategy.auto_selection_config or {}
                        kis_client = KISClient()
                        
                        # 랭킹 유형에 따라 API 호출
                        ranking_type = auto_config.get("ranking_type", "volume")
                        market_code = auto_config.get("market_code", "J")
                        sort_type = auto_config.get("sort_type", "0")
                        limit = auto_config.get("limit", 10)
                        
                        try:
                            if ranking_type == "volume":
                                rank_data = await kis_client.get_volume_rank(
                                    fid_cond_mrkt_div_code=market_code,
                                    fid_cond_scr_div_code="20171",
                                    fid_input_iscd="0000",
                                    fid_div_cls_code="0",
                                    fid_blng_cls_code=sort_type,
                                    fid_trgt_cls_code="000000000",
                                    fid_trgt_exls_cls_code="0000000000",
                                    fid_input_price_1="", fid_input_price_2="", fid_vol_cnt="", fid_input_date_1=""
                                )
                            elif ranking_type == "fluctuation":
                                rank_data = await kis_client.get_fluctuation_rank(
                                    fid_cond_mrkt_div_code=market_code,
                                    fid_cond_scr_div_code="20170",
                                    fid_input_iscd="0000",
                                    fid_rank_sort_cls_code=sort_type,
                                    fid_input_cnt_1=str(limit),
                                    fid_prc_cls_code="0", fid_input_price_1="", fid_input_price_2="",
                                    fid_vol_cnt="", fid_trgt_cls_code="0", fid_trgt_exls_cls_code="0",
                                    fid_div_cls_code="0", fid_rsfl_rate1="", fid_rsfl_rate2=""
                                )
                            elif ranking_type == "market_cap":
                                rank_data = await kis_client.get_market_cap_rank(
                                    fid_cond_mrkt_div_code=market_code,
                                    fid_cond_scr_div_code="20174",
                                    fid_input_iscd="0000",
                                    fid_div_cls_code="0",
                                    fid_trgt_cls_code="0", fid_trgt_exls_cls_code="0",
                                    fid_input_price_1="", fid_input_price_2="", fid_vol_cnt=""
                                )
                            else:
                                logger.warning(f"알 수 없는 랭킹 유형: {ranking_type}")
                                continue
                            
                            if rank_data and rank_data.get("output"):
                                stock_codes = [item.get("mksc_shrn_iscd", "") for item in rank_data["output"][:limit]]
                                stock_codes = [code for code in stock_codes if code]  # 빈 문자열 제거
                                logger.info(f"[자동매매] 전략 '{strategy.name}': {ranking_type} 랭킹 기반 선택 종목 {len(stock_codes)}개")
                            else:
                                logger.warning(f"[자동매매] 전략 '{strategy.name}': 랭킹 데이터가 없습니다.")
                                continue
                        except Exception as e:
                            logger.error(f"랭킹 기반 종목 가져오기 실패: {e}")
                            continue
                    
                    if not stock_codes:
                        logger.info(f"[자동매매] 전략 '{strategy.name}': 선택된 종목이 없습니다.")
                        continue
                    
                    logger.info(f"[자동매매] 전략 '{strategy.name}': {len(stock_codes)}개 종목에 대해 전략 실행 시작")
                    
                    # 전략이 엔진에 등록되어 있는지 확인하고, 없으면 등록
                    if not strategy_engine.get_strategy(strategy.name):
                        logger.info(f"[자동매매] 전략 '{strategy.name}'이 엔진에 등록되지 않음. 자동 등록 시도...")
                        try:
                            from app.services.strategies import create_strategy
                            config = strategy.config or {}
                            strategy_instance = create_strategy(strategy.strategy_type, config)
                            strategy_instance.name = strategy.name
                            strategy_instance.is_active = True
                            strategy_engine.register_strategy(strategy_instance)
                            logger.info(f"[자동매매] 전략 '{strategy.name}' 자동 등록 완료")
                        except Exception as e:
                            logger.error(f"[자동매매] 전략 '{strategy.name}' 자동 등록 실패: {e}")
                            continue
                    
                    # 전략 실행
                    for stock_code in stock_codes:
                        signal = await strategy_engine.execute_strategy(strategy.name, stock_code)
                        if signal:
                            logger.info(f"[자동매매] 전략 '{strategy.name}' - 종목 {stock_code}: {signal['action']} 신호 발생")
                            all_signals.append(signal)
                    
                    # 신호가 있으면 주문 실행
                    for signal in all_signals:
                        try:
                            kis_client = KISClient()
                            result = await kis_client.place_order(
                                stock_code=signal["stock_code"],
                                side=signal["action"],
                                quantity=signal["quantity"],
                                price=signal["price"],
                                order_type=signal.get("order_type", "00")
                            )
                            
                            logger.info(f"[자동매매] 주문 실행: {signal['action']} {signal['stock_code']} {signal['quantity']}주 @ {signal['price']}원")
                            
                        except Exception as e:
                            logger.error(f"[자동매매] 주문 실행 실패 ({signal['stock_code']}): {e}")
                
                if all_signals:
                    logger.info(f"[자동매매] {len(all_signals)}개의 매매 신호 처리 완료")
                else:
                    logger.info("[자동매매] 매매 신호 없음 - 모든 전략 실행 완료")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"[자동매매] 실행 중 오류 발생: {e}", exc_info=True)
    
    def get_status(self) -> dict:
        """스케줄러 상태 조회"""
        current_time = datetime.now(self.korea_tz)
        market_is_open = is_market_open(current_time)
        next_open_time = get_next_market_open_time(current_time)
        
        return {
            "is_running": self.is_running,
            "interval_seconds": self.interval_seconds if self.is_running else None,
            "schedule_type": self.schedule_type if self.is_running else None,
            "market": {
                "is_open": market_is_open,
                "current_time": current_time.isoformat(),
                "next_open_time": next_open_time.isoformat() if next_open_time else None
            }
        }


# 전역 스케줄러 인스턴스
auto_trading_scheduler = AutoTradingScheduler()

