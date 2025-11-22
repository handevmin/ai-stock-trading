"""FastAPI 애플리케이션 진입점"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.logger import logger
from app.database import init_db
from app.api import auth, account, market, order, strategy, watchlist, auto_trading


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    logger.info("애플리케이션 시작 중...")
    init_db()
    logger.info("데이터베이스 초기화 완료")
    
    # 스케줄러는 사용자가 수동으로 시작하도록 설정 (자동 시작 안 함)
    # 필요시 여기서 자동 시작 가능:
    # from app.services.scheduler import auto_trading_scheduler
    # auto_trading_scheduler.start(interval_seconds=60)
    
    yield
    # 종료 시
    logger.info("애플리케이션 종료 중...")
    # 스케줄러 정리
    from app.services.scheduler import auto_trading_scheduler
    if auto_trading_scheduler.is_running:
        auto_trading_scheduler.stop()
        logger.info("자동매매 스케줄러 중지 완료")


app = FastAPI(
    title="주식 자동매매 시스템",
    description="한국투자증권 KIS API를 활용한 주식 자동매매 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix="/api/auth", tags=["인증"])
app.include_router(account.router, prefix="/api/account", tags=["계좌"])
app.include_router(market.router, prefix="/api/market", tags=["시세"])
app.include_router(order.router, prefix="/api/order", tags=["주문"])
app.include_router(strategy.router, prefix="/api/strategy", tags=["전략"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["관심종목"])
app.include_router(auto_trading.router, prefix="/api/auto-trading", tags=["자동매매"])


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "주식 자동매매 시스템 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 예외 핸들러"""
    logger.error(f"예외 발생: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "내부 서버 오류가 발생했습니다."}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )


