"""KIS API 토큰 관리 서비스"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.services.kis_client import KISClient
from app.utils.logger import logger


class TokenManager:
    """토큰 관리 서비스"""
    
    def __init__(self):
        self.kis_client = KISClient()
        self._token_cache: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    async def get_valid_token(self) -> str:
        """유효한 토큰 반환 (필요시 자동 갱신)"""
        # 토큰이 없거나 만료되었으면 갱신
        if not self._token_cache or not self._is_token_valid():
            logger.info("토큰 갱신 필요 - 새 토큰 발급 중...")
            await self.refresh_token()
        
        return self._token_cache
    
    async def refresh_token(self) -> str:
        """토큰 갱신"""
        try:
            token = await self.kis_client.get_access_token()
            self._token_cache = token
            # 토큰 만료 시간 설정 (일반적으로 24시간, 여유있게 23시간으로 설정)
            self._token_expires_at = datetime.now() + timedelta(hours=23)
            logger.info("토큰 갱신 완료")
            return token
        except Exception as e:
            logger.error(f"토큰 갱신 실패: {e}")
            raise
    
    def _is_token_valid(self) -> bool:
        """토큰 유효성 확인"""
        if not self._token_cache or not self._token_expires_at:
            return False
        
        # 만료 5분 전이면 갱신 필요로 간주
        buffer_time = timedelta(minutes=5)
        return datetime.now() < (self._token_expires_at - buffer_time)
    
    async def ensure_token(self) -> str:
        """토큰 보장 (유효하지 않으면 갱신)"""
        return await self.get_valid_token()


# 전역 토큰 매니저 인스턴스
token_manager = TokenManager()



