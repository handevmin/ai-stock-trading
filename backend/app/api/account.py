"""계좌 정보 API"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.account import Account
from app.services.kis_client import KISClient
from app.utils.logger import logger
from app.config import settings

router = APIRouter()


class AccountBalanceResponse(BaseModel):
    """계좌 잔고 응답 모델"""
    account_no: str
    total_balance: float
    available_balance: float
    invested_amount: float
    profit_loss: float
    profit_loss_rate: float


@router.get("/balance", response_model=AccountBalanceResponse)
async def get_account_balance(db: Session = Depends(get_db)):
    """계좌 잔고 조회"""
    try:
        kis_client = KISClient()
        result = await kis_client.get_account_balance()
        
        # KIS API 응답 파싱
        output1 = result.get("output1", [])
        output2 = result.get("output2", [])
        rt_cd = result.get("rt_cd", "")
        msg1 = result.get("msg1", "")
        
        logger.info("=" * 60)
        logger.info("계좌 잔고 조회 결과 확인")
        logger.info(f"응답 코드 (rt_cd): {rt_cd}")
        logger.info(f"응답 메시지 (msg1): {msg1}")
        logger.info(f"보유 종목 수 (output1): {len(output1)}")
        logger.info(f"계좌 정보 수 (output2): {len(output2)}")
        
        # API 응답 성공 여부 확인
        is_api_success = rt_cd == "0" or rt_cd == 0
        
        if not output2:
            if is_api_success:
                logger.warning("=" * 60)
                logger.warning("API 호출은 성공했지만 계좌 정보 (output2)가 없습니다.")
                logger.warning(f"응답 코드: {rt_cd}, 메시지: {msg1}")
                logger.warning("=" * 60)
            else:
                logger.error("=" * 60)
                logger.error("계좌 정보 (output2)가 없습니다.")
                logger.error(f"응답 코드: {rt_cd}, 메시지: {msg1}")
                logger.error("=" * 60)
            raise HTTPException(status_code=404, detail="계좌 정보를 찾을 수 없습니다.")
        
        # 실제 API 응답인지 확인
        if is_api_success:
            logger.info("=" * 60)
            logger.info("✅ 실제 KIS API 응답을 사용합니다.")
            logger.info(f"보유 종목: {len(output1)}개")
            if len(output1) == 0:
                logger.info("보유 종목이 없습니다. (정상적인 응답)")
            logger.info("=" * 60)
        else:
            # Mock 데이터인 경우
            logger.warning("=" * 60)
            logger.warning("⚠️ Mock 데이터 사용 중 (API 연결 실패 또는 USE_MOCK_DATA 활성화)")
            logger.warning("=" * 60)
        
        # 계좌 정보 추출
        account_info = output2[0]
        total_balance = float(account_info.get("dnca_tot_amt", 0))  # 예수금총액
        available_balance = float(account_info.get("nrcvb_buy_amt", 0))  # 가용현금
        invested_amount = float(account_info.get("tot_evlu_amt", 0))  # 총평가금액
        profit_loss = float(account_info.get("evlu_pfls_amt", 0))  # 평가손익금액
        profit_loss_rate = float(account_info.get("evlu_pfls_smtl_amt", 0))  # 평가손익률
        
        # 데이터베이스에 저장 또는 업데이트
        account = db.query(Account).filter(Account.account_no == kis_client.account_no).first()
        if account:
            account.total_balance = total_balance
            account.available_balance = available_balance
            account.invested_amount = invested_amount
            account.profit_loss = profit_loss
            account.profit_loss_rate = profit_loss_rate
        else:
            account = Account(
                account_no=kis_client.account_no,
                total_balance=total_balance,
                available_balance=available_balance,
                invested_amount=invested_amount,
                profit_loss=profit_loss,
                profit_loss_rate=profit_loss_rate
            )
            db.add(account)
        
        db.commit()
        db.refresh(account)
        
        return AccountBalanceResponse(
            account_no=account.account_no,
            total_balance=account.total_balance,
            available_balance=account.available_balance,
            invested_amount=account.invested_amount,
            profit_loss=account.profit_loss,
            profit_loss_rate=account.profit_loss_rate
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        # API 키 인증 실패 등
        error_msg = str(e)
        logger.error(f"계좌 잔고 조회 실패 (설정 오류): {error_msg}")
        if "API 키 인증 실패" in error_msg or "403" in error_msg:
            raise HTTPException(
                status_code=401,
                detail="KIS API 키 인증에 실패했습니다. KIS 디벨로퍼스에서 API 키 상태를 확인하세요."
            )
        raise HTTPException(status_code=400, detail=error_msg)
    except ConnectionError as e:
        logger.error(f"계좌 잔고 조회 실패 (연결 오류): {e}")
        if settings.USE_MOCK_DATA:
            logger.warning("연결 오류로 인해 Mock 데이터를 사용합니다.")
            # Mock 데이터 반환
            from app.utils.mock_data import generate_mock_account_balance
            mock_result = generate_mock_account_balance(kis_client.account_no)
            output2 = mock_result.get("output2", [])
            if output2:
                account_info = output2[0]
                return AccountBalanceResponse(
                    account_no=kis_client.account_no,
                    total_balance=float(account_info.get("dnca_tot_amt", 0)),
                    available_balance=float(account_info.get("nrcvb_buy_amt", 0)),
                    invested_amount=float(account_info.get("tot_evlu_amt", 0)),
                    profit_loss=float(account_info.get("evlu_pfls_amt", 0)),
                    profit_loss_rate=float(account_info.get("evlu_pfls_smtl_amt", 0))
                )
        raise HTTPException(
            status_code=503,
            detail="KIS API 서버에 연결할 수 없습니다. 네트워크 연결과 API 설정을 확인해주세요."
        )
    except Exception as e:
        logger.error(f"계좌 잔고 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"계좌 잔고 조회에 실패했습니다: {str(e)}")


@router.get("/holdings")
async def get_holdings(db: Session = Depends(get_db)):
    """보유 종목 조회"""
    try:
        kis_client = KISClient()
        result = await kis_client.get_account_balance()
        
        output1 = result.get("output1", [])
        rt_cd = result.get("rt_cd", "")
        msg1 = result.get("msg1", "")
        
        # API 응답 확인
        logger.info("=" * 60)
        logger.info("보유 종목 조회 결과 확인")
        logger.info(f"응답 코드 (rt_cd): {rt_cd}")
        logger.info(f"응답 메시지 (msg1): {msg1}")
        logger.info(f"보유 종목 수 (output1): {len(output1)}")
        
        # API 응답 성공 여부 확인
        is_api_success = rt_cd == "0" or rt_cd == 0
        
        # Mock 데이터 사용 시 (API 실패한 경우만)
        if not output1 and not is_api_success:
            logger.warning("=" * 60)
            logger.warning("⚠️ 보유 종목 데이터가 없어 Mock 데이터를 사용합니다.")
            logger.warning(f"원인: API 호출 실패 (응답 코드: {rt_cd}, 메시지: {msg1})")
            logger.warning("=" * 60)
            from app.utils.mock_data import generate_mock_holdings
            output1 = generate_mock_holdings()
            logger.info("Mock 보유 종목 데이터 사용 중")
        elif not output1 and is_api_success:
            # API 성공했지만 보유 종목이 없는 경우 (정상)
            logger.info("=" * 60)
            logger.info("✅ 실제 KIS API 응답: 보유 종목이 없습니다. (정상)")
            logger.info("=" * 60)
        
        holdings = []
        for item in output1:
            holdings.append({
                "stock_code": item.get("pdno", ""),
                "stock_name": item.get("prdt_name", ""),
                "quantity": int(item.get("hldg_qty", 0)),
                "average_price": float(item.get("pchs_avg_pric", 0)),
                "current_price": float(item.get("prpr", 0)),
                "profit_loss": float(item.get("evlu_pfls_amt", 0)),
                "profit_loss_rate": float(item.get("evlu_pfls_rt", 0)),
            })
        
        return {"holdings": holdings}
        
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"보유 종목 조회 실패 (설정 오류): {error_msg}")
        if "API 키 인증 실패" in error_msg or "403" in error_msg:
            raise HTTPException(
                status_code=401,
                detail="KIS API 키 인증에 실패했습니다. KIS 디벨로퍼스에서 API 키 상태를 확인하세요."
            )
        raise HTTPException(status_code=400, detail=error_msg)
    except ConnectionError as e:
        logger.error(f"보유 종목 조회 실패 (연결 오류): {e}")
        if settings.USE_MOCK_DATA:
            logger.warning("연결 오류로 인해 Mock 데이터를 사용합니다.")
            from app.utils.mock_data import generate_mock_holdings
            holdings_data = generate_mock_holdings()
            holdings = []
            for item in holdings_data:
                holdings.append({
                    "stock_code": item.get("pdno", ""),
                    "stock_name": item.get("prdt_name", ""),
                    "quantity": int(item.get("hldg_qty", 0)),
                    "average_price": float(item.get("pchs_avg_pric", 0)),
                    "current_price": float(item.get("prpr", 0)),
                    "profit_loss": float(item.get("evlu_pfls_amt", 0)),
                    "profit_loss_rate": float(item.get("evlu_pfls_rt", 0)),
                })
            return {"holdings": holdings}
        raise HTTPException(
            status_code=503,
            detail="KIS API 서버에 연결할 수 없습니다. 네트워크 연결과 API 설정을 확인해주세요."
        )
    except Exception as e:
        logger.error(f"보유 종목 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"보유 종목 조회에 실패했습니다: {str(e)}")

