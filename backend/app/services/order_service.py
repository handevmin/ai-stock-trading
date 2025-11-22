"""주문 처리 서비스"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.trade import Trade, OrderSide, OrderStatus
from app.services.kis_client import KISClient
from app.utils.logger import logger


class OrderService:
    """주문 처리 서비스"""
    
    def __init__(self):
        self.kis_client = KISClient()
    
    async def execute_order(
        self,
        stock_code: str,
        side: str,
        quantity: int,
        price: float,
        order_type: str = "00",
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """주문 실행"""
        try:
            result = await self.kis_client.place_order(
                stock_code=stock_code,
                side=side,
                quantity=quantity,
                price=price,
                order_type=order_type
            )
            
            # 주문 결과 파싱
            output = result.get("output", {})
            order_no = output.get("ODNO", "")
            
            if not order_no:
                logger.error("주문 번호를 받지 못했습니다.")
                return None
            
            # 데이터베이스에 저장
            if db:
                trade = Trade(
                    order_no=order_no,
                    stock_code=stock_code,
                    side=OrderSide.BUY if side.upper() == "BUY" or side == "매수" else OrderSide.SELL,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    status=OrderStatus.SUBMITTED
                )
                db.add(trade)
                db.commit()
                db.refresh(trade)
            
            logger.info(f"주문 실행 완료: {order_no} - {stock_code} {side} {quantity}주")
            
            return {
                "order_no": order_no,
                "stock_code": stock_code,
                "side": side,
                "quantity": quantity,
                "price": price,
                "status": "SUBMITTED"
            }
            
        except Exception as e:
            logger.error(f"주문 실행 실패: {e}")
            raise


# 전역 주문 서비스 인스턴스
order_service = OrderService()



