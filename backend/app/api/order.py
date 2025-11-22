"""주문 API"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.trade import Trade, OrderSide, OrderStatus
from app.services.kis_client import KISClient
from app.utils.logger import logger
from app.utils.validators import validate_stock_code, validate_order_type, validate_price, validate_quantity, validate_order_side

router = APIRouter()


class OrderRequest(BaseModel):
    """주문 요청 모델"""
    stock_code: str
    side: str  # "BUY" or "SELL"
    quantity: int
    price: float
    order_type: str = "00"  # 00: 지정가, 01: 시장가


class OrderResponse(BaseModel):
    """주문 응답 모델"""
    order_no: str
    stock_code: str
    side: str
    quantity: int
    price: float
    status: str
    order_time: datetime


@router.post("/place", response_model=OrderResponse)
async def place_order(order: OrderRequest, db: Session = Depends(get_db)):
    """주문 실행"""
    # 유효성 검사
    if not validate_stock_code(order.stock_code):
        raise HTTPException(status_code=400, detail="유효하지 않은 종목 코드입니다.")
    
    if not validate_order_side(order.side):
        raise HTTPException(status_code=400, detail="유효하지 않은 주문 방향입니다. (BUY 또는 SELL)")
    
    if not validate_quantity(order.quantity):
        raise HTTPException(status_code=400, detail="주문 수량은 1 이상이어야 합니다.")
    
    if order.order_type == "00" and not validate_price(order.price):
        raise HTTPException(status_code=400, detail="유효하지 않은 주문 가격입니다.")
    
    if not validate_order_type(order.order_type):
        raise HTTPException(status_code=400, detail="유효하지 않은 주문 유형입니다.")
    
    try:
        kis_client = KISClient()
        result = await kis_client.place_order(
            stock_code=order.stock_code,
            side=order.side,
            quantity=order.quantity,
            price=order.price,
            order_type=order.order_type
        )
        
        # 주문 결과 파싱
        output = result.get("output", {})
        order_no = output.get("ODNO", "")  # 주문번호
        
        if not order_no:
            raise HTTPException(status_code=500, detail="주문 번호를 받지 못했습니다.")
        
        # 데이터베이스에 저장
        trade = Trade(
            order_no=order_no,
            stock_code=order.stock_code,
            side=OrderSide.BUY if order.side.upper() == "BUY" or order.side == "매수" else OrderSide.SELL,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            status=OrderStatus.SUBMITTED
        )
        
        db.add(trade)
        db.commit()
        db.refresh(trade)
        
        logger.info(f"주문 실행 완료: {order_no} - {order.stock_code} {order.side} {order.quantity}주")
        
        return OrderResponse(
            order_no=trade.order_no,
            stock_code=trade.stock_code,
            side=trade.side.value,
            quantity=trade.quantity,
            price=trade.price,
            status=trade.status.value,
            order_time=trade.order_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 실행에 실패했습니다: {str(e)}")


@router.post("/cancel/{order_no}")
async def cancel_order(order_no: str, stock_code: str, db: Session = Depends(get_db)):
    """주문 취소"""
    if not validate_stock_code(stock_code):
        raise HTTPException(status_code=400, detail="유효하지 않은 종목 코드입니다.")
    
    try:
        kis_client = KISClient()
        result = await kis_client.cancel_order(order_no, stock_code)
        
        # 데이터베이스 업데이트
        trade = db.query(Trade).filter(Trade.order_no == order_no).first()
        if trade:
            trade.status = OrderStatus.CANCELLED
            db.commit()
        
        return {"message": "주문이 취소되었습니다.", "order_no": order_no}
        
    except Exception as e:
        logger.error(f"주문 취소 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 취소에 실패했습니다.")


@router.get("/history")
async def get_order_history(db: Session = Depends(get_db)):
    """주문 내역 조회"""
    try:
        kis_client = KISClient()
        result = await kis_client.get_order_history()
        
        output1 = result.get("output1", [])
        
        # Mock 데이터 사용 시 로그 출력
        if output1:
            logger.info("Mock 주문 내역 데이터 사용 중 (API 연결 실패 또는 USE_MOCK_DATA 활성화)")
        
        orders = []
        for item in output1:
            orders.append({
                "order_no": item.get("odno", ""),
                "stock_code": item.get("pdno", ""),
                "stock_name": item.get("prdt_name", ""),
                "side": item.get("sll_buy_dvsn_cd_name", ""),
                "order_type": item.get("ord_dvsn_cd_name", ""),
                "quantity": int(item.get("ord_qty", 0)),
                "price": float(item.get("ord_unpr", 0)),
                "executed_quantity": int(item.get("tot_ccld_qty", 0)),
                "executed_price": float(item.get("avg_prvs", 0)),
                "status": item.get("ord_stat_cd_name", ""),
                "order_time": item.get("ord_tmd", ""),
            })
        
        return {"orders": orders}
        
    except ConnectionError as e:
        logger.error(f"주문 내역 조회 실패 (연결 오류): {e}")
        raise HTTPException(
            status_code=503,
            detail="KIS API 서버에 연결할 수 없습니다. 네트워크 연결과 API 설정을 확인해주세요."
        )
    except Exception as e:
        logger.error(f"주문 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 내역 조회에 실패했습니다: {str(e)}")


@router.get("/trades")
async def get_trades(db: Session = Depends(get_db), limit: int = 100):
    """데이터베이스의 거래 내역 조회"""
    trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()
    
    return {
        "trades": [
            {
                "id": trade.id,
                "order_no": trade.order_no,
                "stock_code": trade.stock_code,
                "stock_name": trade.stock_name,
                "side": trade.side.value,
                "quantity": trade.quantity,
                "price": trade.price,
                "executed_quantity": trade.executed_quantity,
                "executed_price": trade.executed_price,
                "status": trade.status.value,
                "order_time": trade.order_time.isoformat() if trade.order_time else None,
            }
            for trade in trades
        ]
    }

