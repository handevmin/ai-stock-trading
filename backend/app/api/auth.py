"""인증 관련 API"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.token_manager import token_manager
from app.utils.logger import logger

router = APIRouter()


class TokenResponse(BaseModel):
    """토큰 응답 모델"""
    access_token: str
    token_type: str = "bearer"


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token():
    """KIS API 토큰 갱신"""
    try:
        token = await token_manager.refresh_token()
        return TokenResponse(access_token=token)
    except Exception as e:
        logger.error(f"토큰 갱신 실패: {e}")
        raise HTTPException(status_code=500, detail="토큰 갱신에 실패했습니다.")


@router.get("/token/status")
async def get_token_status():
    """토큰 상태 확인"""
    try:
        token = await token_manager.get_valid_token()
        return {
            "status": "valid",
            "has_token": bool(token)
        }
    except Exception as e:
        logger.error(f"토큰 상태 확인 실패: {e}")
        return {
            "status": "invalid",
            "has_token": False
        }



