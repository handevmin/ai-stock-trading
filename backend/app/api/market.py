"""시세 조회 API"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services.kis_client import KISClient
from app.utils.logger import logger
from app.utils.validators import validate_stock_code

router = APIRouter()


class CurrentPriceResponse(BaseModel):
    """현재가 응답 모델"""
    stock_code: str
    stock_name: str
    current_price: float
    change_price: float
    change_rate: float
    volume: int
    high_price: float
    low_price: float
    open_price: float
    prev_close: float


class OrderbookResponse(BaseModel):
    """호가 응답 모델"""
    stock_code: str
    bid_prices: list[float]  # 매수 호가
    bid_quantities: list[int]  # 매수 수량
    ask_prices: list[float]  # 매도 호가
    ask_quantities: list[int]  # 매도 수량


@router.get("/current-price/{stock_code}", response_model=CurrentPriceResponse)
async def get_current_price(stock_code: str):
    """현재가 조회"""
    if not validate_stock_code(stock_code):
        raise HTTPException(status_code=400, detail="유효하지 않은 종목 코드입니다.")
    
    try:
        kis_client = KISClient()
        result = await kis_client.get_current_price(stock_code)
        
        output = result.get("output", {})
        
        return CurrentPriceResponse(
            stock_code=stock_code,
            stock_name=output.get("hts_kor_isnm", ""),
            current_price=float(output.get("stck_prpr", 0)),
            change_price=float(output.get("prdy_vrss", 0)),
            change_rate=float(output.get("prdy_vrss_sign", 0)) * float(output.get("prdy_ctrt", 0)),
            volume=int(output.get("acml_vol", 0)),
            high_price=float(output.get("stck_hgpr", 0)),
            low_price=float(output.get("stck_lwpr", 0)),
            open_price=float(output.get("stck_oprc", 0)),
            prev_close=float(output.get("prdy_clpr", 0))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"현재가 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="현재가 조회에 실패했습니다.")


@router.get("/orderbook/{stock_code}", response_model=OrderbookResponse)
async def get_orderbook(stock_code: str):
    """호가 조회"""
    if not validate_stock_code(stock_code):
        raise HTTPException(status_code=400, detail="유효하지 않은 종목 코드입니다.")
    
    try:
        kis_client = KISClient()
        result = await kis_client.get_orderbook(stock_code)
        
        output = result.get("output", {})
        
        # 매수 호가 (1~10호가)
        bid_prices = []
        bid_quantities = []
        for i in range(1, 11):
            price_key = f"bidp{i}"
            qty_key = f"bidp_rsqn{i}"
            if price_key in output:
                bid_prices.append(float(output.get(price_key, 0)))
                bid_quantities.append(int(output.get(qty_key, 0)))
        
        # 매도 호가 (1~10호가)
        ask_prices = []
        ask_quantities = []
        for i in range(1, 11):
            price_key = f"askp{i}"
            qty_key = f"askp_rsqn{i}"
            if price_key in output:
                ask_prices.append(float(output.get(price_key, 0)))
                ask_quantities.append(int(output.get(qty_key, 0)))
        
        return OrderbookResponse(
            stock_code=stock_code,
            bid_prices=bid_prices,
            bid_quantities=bid_quantities,
            ask_prices=ask_prices,
            ask_quantities=ask_quantities
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"호가 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="호가 조회에 실패했습니다.")


@router.get("/stock-info/{stock_code}")
async def get_stock_info(stock_code: str):
    """종목 기본 정보 조회"""
    if not validate_stock_code(stock_code):
        raise HTTPException(status_code=400, detail="유효하지 않은 종목 코드입니다.")
    
    try:
        kis_client = KISClient()
        result = await kis_client.search_stock_info(stock_code)
        
        output = result.get("output", [])
        if not output:
            raise HTTPException(status_code=404, detail="종목 정보를 찾을 수 없습니다.")
        
        stock_info = output[0] if isinstance(output, list) else output
        
        return {
            "stock_code": stock_code,
            "stock_name": stock_info.get("prdt_name", ""),
            "stock_name_abbr": stock_info.get("prdt_abrv_name", ""),
            "stock_name_eng": stock_info.get("prdt_eng_name", ""),
            "market_code": stock_info.get("mrkt_ctg", ""),
            "market_name": stock_info.get("mrkt_ctg_name", ""),
            "stock_type": stock_info.get("prdt_type_cd", ""),
            "stock_type_name": stock_info.get("prdt_type_cd_name", ""),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="종목 정보 조회에 실패했습니다.")


@router.get("/chart/{stock_code}")
async def get_chart(
    stock_code: str,
    start_date: str = Query(..., description="조회 시작일자 (YYYYMMDD)"),
    end_date: str = Query(..., description="조회 종료일자 (YYYYMMDD)"),
    period: str = Query("D", description="기간분류코드 (D:일봉, W:주봉, M:월봉, Y:년봉)")
):
    """차트 데이터 조회 (일봉/주봉/월봉/년봉)"""
    if not validate_stock_code(stock_code):
        raise HTTPException(status_code=400, detail="유효하지 않은 종목 코드입니다.")
    
    if period not in ["D", "W", "M", "Y"]:
        raise HTTPException(status_code=400, detail="기간분류코드는 D, W, M, Y 중 하나여야 합니다.")
    
    try:
        kis_client = KISClient()
        result = await kis_client.get_daily_chart(stock_code, start_date, end_date, period)
        
        output1 = result.get("output1", {})
        output2 = result.get("output2", [])
        
        chart_data = []
        for item in output2:
            chart_data.append({
                "date": item.get("stck_bsop_date", ""),
                "open": float(item.get("stck_oprc", 0)),
                "high": float(item.get("stck_hgpr", 0)),
                "low": float(item.get("stck_lwpr", 0)),
                "close": float(item.get("stck_clpr", 0)),
                "volume": int(item.get("acml_vol", 0)),
                "amount": int(item.get("acml_tr_pbmn", 0)),
            })
        
        return {
            "stock_code": stock_code,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "current_price": float(output1.get("stck_clpr", 0)) if output1 else 0,
            "chart_data": chart_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"차트 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="차트 데이터 조회에 실패했습니다.")


@router.get("/trend/{stock_code}")
async def get_price_trend(stock_code: str):
    """예상체결가 추이 조회"""
    if not validate_stock_code(stock_code):
        raise HTTPException(status_code=400, detail="유효하지 않은 종목 코드입니다.")
    
    try:
        kis_client = KISClient()
        result = await kis_client.get_price_trend(stock_code)
        
        output1 = result.get("output1", {})
        output2 = result.get("output2", [])
        
        trend_data = []
        for item in output2:
            trend_data.append({
                "date": item.get("xymd", ""),
                "time": item.get("tmd", ""),
                "price": float(item.get("prpr", 0)),
                "volume": int(item.get("cntg_vol", 0)),
            })
        
        return {
            "stock_code": stock_code,
            "current_price": float(output1.get("stck_prpr", 0)) if output1 else 0,
            "change_price": float(output1.get("prdy_vrss", 0)) if output1 else 0,
            "change_rate": float(output1.get("prdy_ctrt", 0)) if output1 else 0,
            "trend_data": trend_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"추세 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="추세 데이터 조회에 실패했습니다.")


@router.get("/ranking/volume")
async def get_volume_rank(
    market_code: str = Query("J", description="시장코드 (J:KRX, NX:NXT, UN:통합)"),
    sort_type: str = Query("0", description="정렬기준 (0:평균거래량, 1:거래증가율, 2:평균거래회전율, 3:거래금액순, 4:평균거래금액회전율)")
):
    """거래량순위 조회"""
    try:
        kis_client = KISClient()
        result = await kis_client.get_volume_rank(market_code, sort_type)
        
        output = result.get("output", [])
        
        rank_data = []
        for item in output:
            rank_data.append({
                "rank": int(item.get("data_rank", 0)),
                "stock_code": item.get("mksc_shrn_iscd", ""),
                "stock_name": item.get("hts_kor_isnm", ""),
                "current_price": float(item.get("stck_prpr", 0)),
                "change_price": float(item.get("prdy_vrss", 0)),
                "change_rate": float(item.get("prdy_ctrt", 0)),
                "change_sign": item.get("prdy_vrss_sign", "2"),
                "volume": int(item.get("acml_vol", 0)),
                "amount": int(item.get("acml_tr_pbmn", 0)),
            })
        
        return {
            "market_code": market_code,
            "sort_type": sort_type,
            "rankings": rank_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"거래량순위 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="거래량순위 조회에 실패했습니다.")


@router.get("/ranking/fluctuation")
async def get_fluctuation_rank(
    market_code: str = Query("J", description="시장코드 (J:KRX, Q:코스닥)"),
    sort_type: str = Query("0000", description="정렬기준 (0000:등락률순)")
):
    """등락률순위 조회"""
    try:
        kis_client = KISClient()
        result = await kis_client.get_fluctuation_rank(market_code, sort_type)
        
        output = result.get("output", [])
        
        rank_data = []
        for item in output:
            rank_data.append({
                "rank": int(item.get("data_rank", 0)),
                "stock_code": item.get("mksc_shrn_iscd", ""),
                "stock_name": item.get("hts_kor_isnm", ""),
                "current_price": float(item.get("stck_prpr", 0)),
                "change_price": float(item.get("prdy_vrss", 0)),
                "change_rate": float(item.get("prdy_ctrt", 0)),
                "change_sign": item.get("prdy_vrss_sign", "2"),
                "volume": int(item.get("acml_vol", 0)),
            })
        
        return {
            "market_code": market_code,
            "sort_type": sort_type,
            "rankings": rank_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"등락률순위 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="등락률순위 조회에 실패했습니다.")


@router.get("/ranking/market-cap")
async def get_market_cap_rank(
    market_code: str = Query("J", description="시장코드 (J:KRX)")
):
    """시가총액순위 조회"""
    try:
        kis_client = KISClient()
        result = await kis_client.get_market_cap_rank(market_code)
        
        output = result.get("output", [])
        
        rank_data = []
        for item in output:
            rank_data.append({
                "rank": int(item.get("data_rank", 0)),
                "stock_code": item.get("mksc_shrn_iscd", ""),
                "stock_name": item.get("hts_kor_isnm", ""),
                "current_price": float(item.get("stck_prpr", 0)),
                "change_price": float(item.get("prdy_vrss", 0)),
                "change_rate": float(item.get("prdy_ctrt", 0)),
                "change_sign": item.get("prdy_vrss_sign", "2"),
                "market_cap": float(item.get("mrkt_whol_avls_rlim", 0)),
            })
        
        return {
            "market_code": market_code,
            "rankings": rank_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"시가총액순위 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="시가총액순위 조회에 실패했습니다.")


