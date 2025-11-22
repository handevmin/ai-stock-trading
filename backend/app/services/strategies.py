"""검증된 고성공률 주식 매매 전략들"""
from typing import Dict, Any, Optional
import math

from app.services.strategy_engine import BaseStrategy
from app.utils.logger import logger


class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    이동평균선 교차 전략 (Moving Average Crossover)
    - 단기 이동평균선이 장기 이동평균선을 상향 돌파하면 매수
    - 단기 이동평균선이 장기 이동평균선을 하향 돌파하면 매도
    - 가장 기본적이고 검증된 추세 추종 전략
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("이동평균선 교차", config)
        self.short_period = config.get("short_period", 5)  # 단기 이동평균 (기본 5일)
        self.long_period = config.get("long_period", 20)  # 장기 이동평균 (기본 20일)
        self.price_history = []  # 가격 이력 (실제로는 과거 데이터 조회 필요)
    
    def should_buy(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매수 조건: 단기 이동평균 > 장기 이동평균"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        # 가격 이력 업데이트 (실제로는 과거 데이터 조회 필요)
        self.price_history.append(current_price)
        if len(self.price_history) > self.long_period:
            self.price_history.pop(0)
        
        if len(self.price_history) < self.long_period:
            return False
        
        # 이동평균 계산
        short_ma = sum(self.price_history[-self.short_period:]) / self.short_period
        long_ma = sum(self.price_history[-self.long_period:]) / self.long_period
        
        # 이전 상태 확인 (실제로는 저장 필요)
        prev_short_ma = sum(self.price_history[-self.short_period-1:-1]) / self.short_period if len(self.price_history) > self.short_period else short_ma
        prev_long_ma = sum(self.price_history[-self.long_period-1:-1]) / self.long_period if len(self.price_history) > self.long_period else long_ma
        
        # 골든 크로스: 단기선이 장기선을 상향 돌파
        return short_ma > long_ma and prev_short_ma <= prev_long_ma
    
    def should_sell(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매도 조건: 단기 이동평균 < 장기 이동평균"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        if len(self.price_history) < self.long_period:
            return False
        
        short_ma = sum(self.price_history[-self.short_period:]) / self.short_period
        long_ma = sum(self.price_history[-self.long_period:]) / self.long_period
        
        prev_short_ma = sum(self.price_history[-self.short_period-1:-1]) / self.short_period if len(self.price_history) > self.short_period else short_ma
        prev_long_ma = sum(self.price_history[-self.long_period-1:-1]) / self.long_period if len(self.price_history) > self.long_period else long_ma
        
        # 데드 크로스: 단기선이 장기선을 하향 돌파
        return short_ma < long_ma and prev_short_ma >= prev_long_ma
    
    def calculate_buy_quantity(self, stock_code: str, available_balance: float, current_price: float) -> int:
        """매수 수량 계산: 가용 자금의 일정 비율 사용"""
        allocation_ratio = self.config.get("allocation_ratio", 0.1)  # 기본 10%
        invest_amount = available_balance * allocation_ratio
        quantity = int(invest_amount / current_price)
        return max(1, quantity)
    
    def calculate_buy_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        """매수 가격: 현재가 사용"""
        return market_data.get("current_price", 0)
    
    def calculate_sell_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        """매도 가격: 현재가 사용"""
        return market_data.get("current_price", 0)


class RSIStrategy(BaseStrategy):
    """
    RSI (Relative Strength Index) 전략
    - RSI < 30 (과매도): 매수 신호
    - RSI > 70 (과매수): 매도 신호
    - 모멘텀 기반 전략으로 단기 매매에 효과적
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("RSI 전략", config)
        self.period = config.get("rsi_period", 14)  # RSI 계산 기간
        self.oversold = config.get("oversold", 30)  # 과매도 기준
        self.overbought = config.get("overbought", 70)  # 과매수 기준
        self.price_changes = []  # 가격 변화 이력
        self._initialized_stocks = set()  # 초기화된 종목 추적
    
    def calculate_rsi(self, prices: list) -> float:
        """RSI 계산"""
        if len(prices) < self.period + 1:
            return 50.0  # 기본값
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < self.period:
            return 50.0
        
        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    async def _initialize_price_history(self, stock_code: str):
        """과거 가격 데이터로 초기화"""
        if stock_code in self._initialized_stocks:
            return  # 이미 초기화됨
        
        try:
            from datetime import datetime, timedelta
            from app.services.kis_client import KISClient
            
            # 최근 30일 데이터 요청 (RSI 계산에 충분)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")
            
            logger.info(f"[RSI전략] {stock_code}: 과거 가격 데이터 조회 시작 ({start_date_str} ~ {end_date_str})")
            
            kis_client = KISClient()
            chart_data = await kis_client.get_daily_chart(
                stock_code=stock_code,
                start_date=start_date_str,
                end_date=end_date_str,
                period="D"
            )
            
            logger.info(f"[RSI전략] {stock_code}: API 응답 수신 완료")
            
            if chart_data:
                # KIS API는 output1(현재가 정보)와 output2(차트 데이터 배열)를 반환
                output2 = chart_data.get("output2")
                if output2 and isinstance(output2, list) and len(output2) > 0:
                    # 종가 데이터 추출 (최신순으로 정렬되어 있으므로 역순으로 처리)
                    prices = []
                    for item in reversed(output2):
                        close_price = float(item.get("stck_clpr", 0))
                        if close_price > 0:
                            prices.append(close_price)
                    
                    logger.info(f"[RSI전략] {stock_code}: 추출된 가격 데이터 {len(prices)}개")
                    
                    if len(prices) >= self.period + 1:
                        # 종목별로 가격 이력 저장 (stock_code를 키로 사용)
                        if not hasattr(self, '_price_history_by_stock'):
                            self._price_history_by_stock = {}
                        self._price_history_by_stock[stock_code] = prices
                        self._initialized_stocks.add(stock_code)
                        logger.info(f"[RSI전략] {stock_code}: 과거 가격 데이터 {len(prices)}개 로드 완료")
                    else:
                        logger.warning(f"[RSI전략] {stock_code}: 충분한 과거 데이터가 없습니다 ({len(prices)}/{self.period + 1}개 필요)")
                else:
                    logger.warning(f"[RSI전략] {stock_code}: API 응답에 output2 데이터가 없습니다. 응답 키: {list(chart_data.keys()) if chart_data else 'None'}")
            else:
                logger.warning(f"[RSI전략] {stock_code}: API 응답이 None입니다")
        except Exception as e:
            logger.error(f"[RSI전략] {stock_code}: 과거 가격 데이터 초기화 실패: {e}", exc_info=True)
    
    def should_buy(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매수 조건: RSI < 과매도 기준"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            logger.warning(f"[RSI전략] {stock_code}: 유효하지 않은 현재가 ({current_price})")
            return False
        
        # 종목별 가격 이력 가져오기
        if not hasattr(self, '_price_history_by_stock'):
            self._price_history_by_stock = {}
        
        if stock_code not in self._price_history_by_stock:
            self._price_history_by_stock[stock_code] = []
        
        price_list = self._price_history_by_stock[stock_code]
        
        # 현재가 추가
        price_list.append(current_price)
        if len(price_list) > self.period * 2:
            price_list.pop(0)
        
        if len(price_list) < self.period + 1:
            logger.info(f"[RSI전략] {stock_code}: 가격 데이터 부족 ({len(price_list)}/{self.period + 1}개 필요). RSI 계산 불가")
            return False
        
        rsi = self.calculate_rsi(price_list)
        logger.info(f"[RSI전략] {stock_code}: RSI={rsi:.2f}, 과매도기준={self.oversold}, 매수조건={rsi < self.oversold}")
        return rsi < self.oversold
    
    def should_sell(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매도 조건: RSI > 과매수 기준"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            logger.warning(f"[RSI전략] {stock_code}: 유효하지 않은 현재가 ({current_price})")
            return False
        
        # 종목별 가격 이력 가져오기
        if not hasattr(self, '_price_history_by_stock'):
            self._price_history_by_stock = {}
        
        if stock_code not in self._price_history_by_stock:
            self._price_history_by_stock[stock_code] = []
        
        price_list = self._price_history_by_stock[stock_code]
        
        if len(price_list) < self.period + 1:
            logger.info(f"[RSI전략] {stock_code}: 가격 데이터 부족 ({len(price_list)}/{self.period + 1}개 필요). RSI 계산 불가")
            return False
        
        rsi = self.calculate_rsi(price_list)
        logger.info(f"[RSI전략] {stock_code}: RSI={rsi:.2f}, 과매수기준={self.overbought}, 매도조건={rsi > self.overbought}")
        return rsi > self.overbought
    
    def calculate_buy_quantity(self, stock_code: str, available_balance: float, current_price: float) -> int:
        allocation_ratio = self.config.get("allocation_ratio", 0.15)
        invest_amount = available_balance * allocation_ratio
        quantity = int(invest_amount / current_price)
        return max(1, quantity)
    
    def calculate_buy_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)
    
    def calculate_sell_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)


class BollingerBandsStrategy(BaseStrategy):
    """
    볼린저 밴드 전략
    - 가격이 하단 밴드 근처에서 반등하면 매수
    - 가격이 상단 밴드 근처에서 저항받으면 매도
    - 변동성 기반 전략으로 횡보장에서 효과적
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("볼린저 밴드 전략", config)
        self.period = config.get("period", 20)  # 이동평균 기간
        self.std_dev = config.get("std_dev", 2)  # 표준편차 배수
        self.price_history = []
    
    def calculate_bollinger_bands(self, prices: list) -> tuple:
        """볼린저 밴드 계산 (중간선, 상단, 하단)"""
        if len(prices) < self.period:
            return None, None, None
        
        recent_prices = prices[-self.period:]
        sma = sum(recent_prices) / self.period
        
        variance = sum((p - sma) ** 2 for p in recent_prices) / self.period
        std = math.sqrt(variance)
        
        upper_band = sma + (self.std_dev * std)
        lower_band = sma - (self.std_dev * std)
        
        return sma, upper_band, lower_band
    
    def should_buy(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매수 조건: 가격이 하단 밴드 근처"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        self.price_history.append(current_price)
        if len(self.price_history) > self.period * 2:
            self.price_history.pop(0)
        
        if len(self.price_history) < self.period:
            return False
        
        sma, upper_band, lower_band = self.calculate_bollinger_bands(self.price_history)
        if lower_band is None:
            return False
        
        # 하단 밴드 근처에서 반등 신호
        return current_price <= lower_band * 1.02  # 하단 밴드의 2% 이내
    
    def should_sell(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매도 조건: 가격이 상단 밴드 근처"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        if len(self.price_history) < self.period:
            return False
        
        sma, upper_band, lower_band = self.calculate_bollinger_bands(self.price_history)
        if upper_band is None:
            return False
        
        # 상단 밴드 근처에서 저항 신호
        return current_price >= upper_band * 0.98  # 상단 밴드의 2% 이내
    
    def calculate_buy_quantity(self, stock_code: str, available_balance: float, current_price: float) -> int:
        allocation_ratio = self.config.get("allocation_ratio", 0.12)
        invest_amount = available_balance * allocation_ratio
        quantity = int(invest_amount / current_price)
        return max(1, quantity)
    
    def calculate_buy_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)
    
    def calculate_sell_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)


class MACDStrategy(BaseStrategy):
    """
    MACD (Moving Average Convergence Divergence) 전략
    - MACD선이 시그널선을 상향 돌파하면 매수
    - MACD선이 시그널선을 하향 돌파하면 매도
    - 추세와 모멘텀을 동시에 분석하는 전략
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("MACD 전략", config)
        self.fast_period = config.get("fast_period", 12)
        self.slow_period = config.get("slow_period", 26)
        self.signal_period = config.get("signal_period", 9)
        self.price_history = []
        self.macd_history = []
        self.signal_history = []
    
    def calculate_ema(self, prices: list, period: int) -> float:
        """지수이동평균 계산"""
        if len(prices) < period:
            return sum(prices) / len(prices) if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_macd(self, prices: list) -> tuple:
        """MACD 계산"""
        if len(prices) < self.slow_period:
            return None, None
        
        fast_ema = self.calculate_ema(prices, self.fast_period)
        slow_ema = self.calculate_ema(prices, self.slow_period)
        macd = fast_ema - slow_ema
        
        self.macd_history.append(macd)
        if len(self.macd_history) > self.signal_period * 2:
            self.macd_history.pop(0)
        
        if len(self.macd_history) < self.signal_period:
            return macd, None
        
        signal = self.calculate_ema(self.macd_history, self.signal_period)
        return macd, signal
    
    def should_buy(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매수 조건: MACD > Signal (골든 크로스)"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        self.price_history.append(current_price)
        if len(self.price_history) > self.slow_period * 2:
            self.price_history.pop(0)
        
        if len(self.price_history) < self.slow_period:
            return False
        
        macd, signal = self.calculate_macd(self.price_history)
        if macd is None or signal is None:
            return False
        
        # 이전 MACD/Signal 값 확인
        if len(self.macd_history) < 2:
            return False
        
        prev_macd = self.macd_history[-2] if len(self.macd_history) >= 2 else macd
        prev_signal = self.signal_history[-1] if self.signal_history else signal
        self.signal_history.append(signal)
        if len(self.signal_history) > self.signal_period * 2:
            self.signal_history.pop(0)
        
        # 골든 크로스: MACD가 Signal을 상향 돌파
        return macd > signal and prev_macd <= prev_signal
    
    def should_sell(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매도 조건: MACD < Signal (데드 크로스)"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        if len(self.price_history) < self.slow_period:
            return False
        
        macd, signal = self.calculate_macd(self.price_history)
        if macd is None or signal is None:
            return False
        
        if len(self.macd_history) < 2:
            return False
        
        prev_macd = self.macd_history[-2] if len(self.macd_history) >= 2 else macd
        prev_signal = self.signal_history[-1] if self.signal_history else signal
        
        # 데드 크로스: MACD가 Signal을 하향 돌파
        return macd < signal and prev_macd >= prev_signal
    
    def calculate_buy_quantity(self, stock_code: str, available_balance: float, current_price: float) -> int:
        allocation_ratio = self.config.get("allocation_ratio", 0.12)
        invest_amount = available_balance * allocation_ratio
        quantity = int(invest_amount / current_price)
        return max(1, quantity)
    
    def calculate_buy_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)
    
    def calculate_sell_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)


class MomentumStrategy(BaseStrategy):
    """
    모멘텀 전략
    - 가격 상승 모멘텀이 강할 때 매수
    - 가격 하락 모멘텀이 강할 때 매도
    - 단기 매매에 효과적
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("모멘텀 전략", config)
        self.period = config.get("period", 10)  # 모멘텀 계산 기간
        self.momentum_threshold = config.get("momentum_threshold", 0.05)  # 모멘텀 임계값 (5%)
        self.price_history = []
    
    def calculate_momentum(self, prices: list) -> float:
        """모멘텀 계산 (가격 변화율)"""
        if len(prices) < self.period + 1:
            return 0.0
        
        current_price = prices[-1]
        past_price = prices[-self.period - 1]
        
        if past_price == 0:
            return 0.0
        
        momentum = (current_price - past_price) / past_price
        return momentum
    
    def should_buy(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매수 조건: 강한 상승 모멘텀"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        self.price_history.append(current_price)
        if len(self.price_history) > self.period * 2:
            self.price_history.pop(0)
        
        if len(self.price_history) < self.period + 1:
            return False
        
        momentum = self.calculate_momentum(self.price_history)
        volume = market_data.get("volume", 0)
        avg_volume = sum(self.price_history) / len(self.price_history) if self.price_history else 0
        
        # 상승 모멘텀 + 거래량 증가
        return momentum > self.momentum_threshold and volume > avg_volume * 0.8
    
    def should_sell(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매도 조건: 강한 하락 모멘텀"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        if len(self.price_history) < self.period + 1:
            return False
        
        momentum = self.calculate_momentum(self.price_history)
        
        # 하락 모멘텀
        return momentum < -self.momentum_threshold
    
    def calculate_buy_quantity(self, stock_code: str, available_balance: float, current_price: float) -> int:
        allocation_ratio = self.config.get("allocation_ratio", 0.1)
        invest_amount = available_balance * allocation_ratio
        quantity = int(invest_amount / current_price)
        return max(1, quantity)
    
    def calculate_buy_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)
    
    def calculate_sell_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)


class MeanReversionStrategy(BaseStrategy):
    """
    평균회귀 전략
    - 가격이 평균에서 크게 벗어나면 평균으로 회귀할 것으로 예상하여 매매
    - 횡보장에서 효과적
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("평균회귀 전략", config)
        self.period = config.get("period", 20)  # 평균 계산 기간
        self.deviation_threshold = config.get("deviation_threshold", 0.03)  # 편차 임계값 (3%)
        self.price_history = []
    
    def should_buy(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매수 조건: 가격이 평균보다 크게 낮음 (회귀 예상)"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        self.price_history.append(current_price)
        if len(self.price_history) > self.period * 2:
            self.price_history.pop(0)
        
        if len(self.price_history) < self.period:
            return False
        
        avg_price = sum(self.price_history[-self.period:]) / self.period
        deviation = (avg_price - current_price) / avg_price
        
        # 평균보다 3% 이상 낮으면 매수 (회귀 예상)
        return deviation > self.deviation_threshold
    
    def should_sell(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        """매도 조건: 가격이 평균보다 크게 높음 (회귀 예상)"""
        current_price = market_data.get("current_price", 0)
        if current_price <= 0:
            return False
        
        if len(self.price_history) < self.period:
            return False
        
        avg_price = sum(self.price_history[-self.period:]) / self.period
        deviation = (current_price - avg_price) / avg_price
        
        # 평균보다 3% 이상 높으면 매도 (회귀 예상)
        return deviation > self.deviation_threshold
    
    def calculate_buy_quantity(self, stock_code: str, available_balance: float, current_price: float) -> int:
        allocation_ratio = self.config.get("allocation_ratio", 0.1)
        invest_amount = available_balance * allocation_ratio
        quantity = int(invest_amount / current_price)
        return max(1, quantity)
    
    def calculate_buy_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)
    
    def calculate_sell_price(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        return market_data.get("current_price", 0)


# 전략 팩토리 함수
def create_strategy(strategy_type: str, config: Dict[str, Any]) -> BaseStrategy:
    """전략 타입에 따라 전략 인스턴스 생성"""
    strategy_map = {
        "moving_average_crossover": MovingAverageCrossoverStrategy,
        "rsi": RSIStrategy,
        "bollinger_bands": BollingerBandsStrategy,
        "macd": MACDStrategy,
        "momentum": MomentumStrategy,
        "mean_reversion": MeanReversionStrategy,
    }
    
    strategy_class = strategy_map.get(strategy_type)
    if not strategy_class:
        raise ValueError(f"알 수 없는 전략 타입: {strategy_type}")
    
    return strategy_class(config)

