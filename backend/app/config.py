"""애플리케이션 설정 관리"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # KIS API 설정
    KIS_APP_KEY: str = ""
    KIS_APP_SECRET: str = ""
    KIS_ACCOUNT_NO: str = ""
    KIS_ACCOUNT_PRODUCT_CD: str = "01"  # 01: 실거래, 02: 모의투자
    KIS_BASE_URL: str = "https://openapi.koreainvestment.com:9443"  # 실전: 9443, 모의: 29443
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./trading.db"
    
    # 서버 설정
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    
    # 보안 설정
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Mock 모드 설정 (API 연결 실패 시 mock 데이터 사용)
    USE_MOCK_DATA: bool = True  # True: 연결 실패 시 mock 데이터 반환, False: 오류 발생
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def validate_kis_settings(self) -> bool:
        """KIS API 설정 유효성 검사"""
        return bool(self.KIS_APP_KEY and self.KIS_APP_SECRET and self.KIS_ACCOUNT_NO)


settings = Settings()

# 환경 변수 검증 (서버 시작 시 경고만 출력)
if not settings.validate_kis_settings():
    import warnings
    warnings.warn(
        "KIS API 설정이 완료되지 않았습니다. "
        "backend/.env 파일을 생성하고 KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO를 설정해주세요. "
        "서버는 시작되지만 KIS API 기능은 사용할 수 없습니다.",
        UserWarning
    )

