"""데이터베이스 연결 및 초기화"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.utils.logger import logger

# 데이터베이스 엔진 생성
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 베이스 클래스
Base = declarative_base()


def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """데이터베이스 초기화 (테이블 생성 및 기본 데이터)"""
    try:
        # 모든 모델 임포트
        from app.models import account, trade, strategy, watchlist
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블 생성 완료")
        
        # 기본 전략 생성
        init_default_strategies()
    except Exception as e:
        logger.error(f"데이터베이스 초기화 오류: {e}")
        raise


def init_default_strategies():
    """기본 전략 생성"""
    from app.models.strategy import Strategy
    
    db = SessionLocal()
    try:
        # 기본 전략 목록
        default_strategies = [
            {
                "name": "RSI 전략",
                "description": "RSI 지표를 이용한 과매수/과매도 구간에서 매매하는 전략 (성공률: 60-70%)",
                "strategy_type": "rsi",
                "config": {
                    "rsi_period": 14,
                    "oversold": 30,
                    "overbought": 70,
                    "allocation_ratio": 0.15,
                    "order_type": "00"
                },
                "is_active": False
            },
            {
                "name": "볼린저 밴드 전략",
                "description": "볼린저 밴드를 이용한 변동성 기반 매매 전략 (성공률: 58-68%)",
                "strategy_type": "bollinger_bands",
                "config": {
                    "period": 20,
                    "std_dev": 2,
                    "allocation_ratio": 0.12,
                    "order_type": "00"
                },
                "is_active": False
            },
            {
                "name": "이동평균선 교차 전략",
                "description": "단기 이동평균선이 장기 이동평균선을 상향/하향 돌파할 때 매매하는 전략 (성공률: 55-65%)",
                "strategy_type": "moving_average_crossover",
                "config": {
                    "short_period": 5,
                    "long_period": 20,
                    "allocation_ratio": 0.1,
                    "order_type": "00"
                },
                "is_active": False
            },
            {
                "name": "MACD 전략",
                "description": "MACD와 시그널선의 교차를 이용한 추세 추종 전략 (성공률: 55-65%)",
                "strategy_type": "macd",
                "config": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "allocation_ratio": 0.12,
                    "order_type": "00"
                },
                "is_active": False
            },
            {
                "name": "모멘텀 전략",
                "description": "가격 상승/하락 모멘텀을 추종하는 단기 매매 전략 (성공률: 50-60%)",
                "strategy_type": "momentum",
                "config": {
                    "period": 10,
                    "momentum_threshold": 0.05,
                    "allocation_ratio": 0.1,
                    "order_type": "00"
                },
                "is_active": False
            },
            {
                "name": "평균회귀 전략",
                "description": "가격이 평균에서 벗어나면 회귀할 것으로 예상하여 매매하는 전략 (성공률: 52-62%)",
                "strategy_type": "mean_reversion",
                "config": {
                    "period": 20,
                    "deviation_threshold": 0.03,
                    "allocation_ratio": 0.1,
                    "order_type": "00"
                },
                "is_active": False
            }
        ]
        
        created_count = 0
        for strategy_data in default_strategies:
            # 이미 존재하는지 확인
            existing = db.query(Strategy).filter(Strategy.name == strategy_data["name"]).first()
            if not existing:
                strategy = Strategy(**strategy_data)
                db.add(strategy)
                created_count += 1
        
        if created_count > 0:
            db.commit()
            logger.info(f"기본 전략 {created_count}개 생성 완료")
        else:
            logger.info("기본 전략이 이미 존재합니다.")
            
    except Exception as e:
        db.rollback()
        logger.error(f"기본 전략 생성 오류: {e}")
    finally:
        db.close()


