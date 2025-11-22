"""전략 실행 엔진 (확장 가능한 기본 구조)"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from app.utils.logger import logger
from app.services.kis_client import KISClient


class BaseStrategy(ABC):
    """전략 기본 클래스 (인터페이스)"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        # KISClient는 필요할 때만 생성 (초기화 시점에 생성하지 않음)
        self._kis_client: Optional[KISClient] = None
        self.is_active = False
    
    @property
    def kis_client(self) -> KISClient:
        """KISClient 지연 로딩"""
        if self._kis_client is None:
            self._kis_client = KISClient()
        return self._kis_client
    
    @abstractmethod
    def should_buy(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매수 조건 확인"""
        pass
    
    @abstractmethod
    def should_sell(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매도 조건 확인"""
        pass
    
    @abstractmethod
    def calculate_buy_quantity(self, stock_code: str, available_balance: float, current_price: float) -> int:
        """매수 수량 계산"""
        pass
    
    @abstractmethod
    def calculate_buy_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        """매수 가격 계산"""
        pass
    
    @abstractmethod
    def calculate_sell_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        """매도 가격 계산"""
        pass
    
    def validate_config(self) -> bool:
        """전략 설정 유효성 검사"""
        return True
    
    def on_buy_signal(self, stock_code: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """매수 신호 발생 시 처리"""
        if not self.should_buy(stock_code, market_data):
            return None
        
        try:
            current_price = market_data.get("current_price", 0)
            if current_price <= 0:
                logger.warning(f"{stock_code}: 유효하지 않은 현재가")
                return None
            
            # 매수 수량 및 가격 계산
            # 실제 구현에서는 계좌 잔고를 조회해야 함
            available_balance = self.config.get("available_balance", 0)
            quantity = self.calculate_buy_quantity(stock_code, available_balance, current_price)
            price = self.calculate_buy_price(stock_code, market_data)
            
            if quantity <= 0:
                logger.warning(f"{stock_code}: 매수 수량이 0 이하")
                return None
            
            return {
                "action": "BUY",
                "stock_code": stock_code,
                "quantity": quantity,
                "price": price,
                "order_type": self.config.get("order_type", "00"),  # 00: 지정가
            }
        except Exception as e:
            logger.error(f"{stock_code} 매수 신호 처리 오류: {e}")
            return None
    
    def on_sell_signal(self, stock_code: str, market_data: Dict[str, Any], holding_quantity: int) -> Optional[Dict[str, Any]]:
        """매도 신호 발생 시 처리"""
        if not self.should_sell(stock_code, market_data):
            return None
        
        if holding_quantity <= 0:
            logger.warning(f"{stock_code}: 보유 수량이 없음")
            return None
        
        try:
            price = self.calculate_sell_price(stock_code, market_data)
            quantity = min(holding_quantity, self.config.get("max_sell_quantity", holding_quantity))
            
            return {
                "action": "SELL",
                "stock_code": stock_code,
                "quantity": quantity,
                "price": price,
                "order_type": self.config.get("order_type", "00"),
            }
        except Exception as e:
            logger.error(f"{stock_code} 매도 신호 처리 오류: {e}")
            return None


class StrategyEngine:
    """전략 실행 엔진"""
    
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.is_running = False
    
    def register_strategy(self, strategy: BaseStrategy):
        """전략 등록"""
        if not strategy.validate_config():
            raise ValueError(f"전략 '{strategy.name}'의 설정이 유효하지 않습니다.")
        
        self.strategies[strategy.name] = strategy
        logger.info(f"전략 등록: {strategy.name}")
    
    def unregister_strategy(self, strategy_name: str):
        """전략 제거"""
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            logger.info(f"전략 제거: {strategy_name}")
    
    def get_strategy(self, strategy_name: str) -> Optional[BaseStrategy]:
        """전략 조회"""
        return self.strategies.get(strategy_name)
    
    def get_active_strategies(self) -> list[BaseStrategy]:
        """활성화된 전략 목록"""
        return [s for s in self.strategies.values() if s.is_active]
    
    async def execute_strategy(self, strategy_name: str, stock_code: str) -> Optional[Dict[str, Any]]:
        """전략 실행"""
        strategy = self.get_strategy(strategy_name)
        if not strategy or not strategy.is_active:
            logger.warning(f"[전략실행] 전략 '{strategy_name}'이 활성화되지 않았거나 존재하지 않습니다.")
            return None
        
        try:
            # RSI 전략인 경우 과거 데이터 초기화
            if hasattr(strategy, '_initialize_price_history'):
                await strategy._initialize_price_history(stock_code)
            
            # 시장 데이터 조회
            logger.info(f"[전략실행] 종목 {stock_code} 시장 데이터 조회 중...")
            market_data = await self._get_market_data(stock_code)
            if not market_data:
                logger.warning(f"[전략실행] 종목 {stock_code} 시장 데이터 조회 실패")
                return None
            
            current_price = market_data.get("current_price", 0)
            logger.info(f"[전략실행] 종목 {stock_code} 현재가: {current_price}원")
            
            # 매수/매도 신호 확인
            logger.info(f"[전략실행] 종목 {stock_code} 매수 조건 확인 중...")
            buy_signal = strategy.on_buy_signal(stock_code, market_data)
            if buy_signal:
                logger.info(f"[전략실행] 매수 신호 발생: {strategy_name} - {stock_code} (수량: {buy_signal.get('quantity')}, 가격: {buy_signal.get('price')}원)")
                return buy_signal
            else:
                logger.info(f"[전략실행] 종목 {stock_code} 매수 조건 미충족")
            
            # 매도 신호는 보유 종목에 대해서만 확인
            # 실제 구현에서는 보유 종목 정보를 조회해야 함
            logger.info(f"[전략실행] 종목 {stock_code} 매도 조건 확인 중...")
            sell_signal = strategy.on_sell_signal(stock_code, market_data, 0)
            if sell_signal:
                logger.info(f"[전략실행] 매도 신호 발생: {strategy_name} - {stock_code} (수량: {sell_signal.get('quantity')}, 가격: {sell_signal.get('price')}원)")
                return sell_signal
            else:
                logger.info(f"[전략실행] 종목 {stock_code} 매도 조건 미충족 (보유 수량: 0)")
            
            logger.info(f"[전략실행] 종목 {stock_code} 매매 신호 없음")
            return None
            
        except Exception as e:
            logger.error(f"[전략실행] 전략 실행 오류 ({strategy_name} - {stock_code}): {e}", exc_info=True)
            return None
    
    async def _get_market_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """시장 데이터 조회"""
        try:
            kis_client = KISClient()
            price_data = await kis_client.get_current_price(stock_code)
            
            output = price_data.get("output", {})
            return {
                "current_price": float(output.get("stck_prpr", 0)),
                "change_price": float(output.get("prdy_vrss", 0)),
                "change_rate": float(output.get("prdy_ctrt", 0)),
                "volume": int(output.get("acml_vol", 0)),
                "high_price": float(output.get("stck_hgpr", 0)),
                "low_price": float(output.get("stck_lwpr", 0)),
                "open_price": float(output.get("stck_oprc", 0)),
                "prev_close": float(output.get("prdy_clpr", 0)),
            }
        except Exception as e:
            logger.error(f"시장 데이터 조회 실패 ({stock_code}): {e}")
            return None
    
    async def run_all_strategies(self, stock_codes: list[str]) -> list[Dict[str, Any]]:
        """모든 활성 전략 실행"""
        signals = []
        
        for strategy in self.get_active_strategies():
            for stock_code in stock_codes:
                signal = await self.execute_strategy(strategy.name, stock_code)
                if signal:
                    signals.append(signal)
        
        return signals
    
    async def get_auto_selected_stocks(
        self,
        selection_mode: str = "ranking",
        criteria: Optional[Dict[str, Any]] = None
    ) -> list[str]:
        """
        자동 종목 선택
        
        Args:
            selection_mode: 선택 모드
                - "ranking": 랭킹 기반 선택 (등락률, 거래량 등)
                - "trend": 추세 기반 선택
                - "volume": 거래량 기반 선택
            criteria: 선택 기준
                - max_stocks: 최대 선택 종목 수
                - min_change_rate: 최소 등락률
                - min_volume: 최소 거래량
        """
        from app.services.kis_client import KISClient
        
        if not criteria:
            criteria = {
                "max_stocks": 10,
                "min_change_rate": 3.0,  # 최소 3% 등락률
                "min_volume": 1000000,  # 최소 거래량
            }
        
        selected_stocks = []
        
        try:
            kis_client = KISClient()
            
            if selection_mode == "ranking":
                # 등락률순위에서 상위 종목 선택
                result = await kis_client.get_fluctuation_rank("J", "0000")
                output = result.get("output", [])
                
                for item in output[:criteria.get("max_stocks", 10)]:
                    stock_code = item.get("mksc_shrn_iscd", "")
                    change_rate = float(item.get("prdy_ctrt", 0))
                    volume = int(item.get("acml_vol", 0))
                    
                    if (stock_code and 
                        abs(change_rate) >= criteria.get("min_change_rate", 3.0) and
                        volume >= criteria.get("min_volume", 1000000)):
                        selected_stocks.append(stock_code)
            
            elif selection_mode == "volume":
                # 거래량순위에서 상위 종목 선택
                result = await kis_client.get_volume_rank("J", "0")
                output = result.get("output", [])
                
                for item in output[:criteria.get("max_stocks", 10)]:
                    stock_code = item.get("mksc_shrn_iscd", "")
                    volume = int(item.get("acml_vol", 0))
                    
                    if stock_code and volume >= criteria.get("min_volume", 1000000):
                        selected_stocks.append(stock_code)
            
            logger.info(f"자동 종목 선택 완료: {len(selected_stocks)}개 종목 ({selection_mode} 모드)")
            
        except Exception as e:
            logger.error(f"자동 종목 선택 실패: {e}")
        
        return selected_stocks


# 전역 전략 엔진 인스턴스
strategy_engine = StrategyEngine()


