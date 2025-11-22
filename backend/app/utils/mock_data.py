"""Mock 데이터 생성 유틸리티"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random


def generate_mock_account_balance(account_no: str = "1234567890") -> Dict[str, Any]:
    """Mock 계좌 잔고 데이터 생성"""
    total_balance = random.uniform(10000000, 50000000)  # 1천만원 ~ 5천만원
    invested_amount = random.uniform(5000000, 30000000)  # 5백만원 ~ 3천만원
    available_balance = total_balance - invested_amount
    profit_loss = random.uniform(-1000000, 3000000)  # -1백만원 ~ 3백만원
    profit_loss_rate = (profit_loss / invested_amount) * 100 if invested_amount > 0 else 0
    
    return {
        "output1": [],  # 보유 종목 목록
        "output2": [{
            "dnca_tot_amt": str(int(total_balance)),  # 예수금총액
            "nrcvb_buy_amt": str(int(available_balance)),  # 가용현금
            "tot_evlu_amt": str(int(invested_amount)),  # 총평가금액
            "evlu_pfls_amt": str(int(profit_loss)),  # 평가손익금액
            "evlu_pfls_smtl_amt": str(round(profit_loss_rate, 2)),  # 평가손익률
        }]
    }


def generate_mock_holdings() -> List[Dict[str, Any]]:
    """Mock 보유 종목 데이터 생성"""
    stock_list = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "000660", "name": "SK하이닉스"},
        {"code": "035420", "name": "NAVER"},
        {"code": "005380", "name": "현대차"},
        {"code": "035720", "name": "카카오"},
    ]
    
    holdings = []
    for stock in stock_list:
        quantity = random.randint(1, 100)
        average_price = random.uniform(50000, 200000)
        current_price = average_price * random.uniform(0.8, 1.3)
        profit_loss = (current_price - average_price) * quantity
        profit_loss_rate = ((current_price - average_price) / average_price) * 100
        
        holdings.append({
            "pdno": stock["code"],
            "prdt_name": stock["name"],
            "hldg_qty": str(quantity),
            "pchs_avg_pric": str(int(average_price)),
            "prpr": str(int(current_price)),
            "evlu_pfls_amt": str(int(profit_loss)),
            "evlu_pfls_rt": str(round(profit_loss_rate, 2)),
        })
    
    return holdings


def generate_mock_current_price(stock_code: str) -> Dict[str, Any]:
    """Mock 현재가 데이터 생성"""
    base_price = random.uniform(50000, 200000)
    change_price = random.uniform(-5000, 5000)
    change_rate = (change_price / base_price) * 100
    volume = random.randint(100000, 10000000)
    
    return {
        "output": {
            "hts_kor_isnm": get_stock_name(stock_code),
            "stck_prpr": str(int(base_price)),  # 현재가
            "prdy_vrss": str(int(change_price)),  # 전일 대비
            "prdy_vrss_sign": "2" if change_price >= 0 else "5",  # 전일 대비 부호
            "prdy_ctrt": str(round(abs(change_rate), 2)),  # 전일 대비율
            "acml_vol": str(volume),  # 누적 거래량
            "stck_hgpr": str(int(base_price * 1.05)),  # 최고가
            "stck_lwpr": str(int(base_price * 0.95)),  # 최저가
            "stck_oprc": str(int(base_price * random.uniform(0.98, 1.02))),  # 시가
            "prdy_clpr": str(int(base_price - change_price)),  # 전일 종가
        }
    }


def generate_mock_orderbook(stock_code: str) -> Dict[str, Any]:
    """Mock 호가 데이터 생성"""
    base_price = random.uniform(50000, 200000)
    output = {}
    
    # 매수 호가 (1~10호가)
    for i in range(1, 11):
        price = int(base_price * (1 - i * 0.001))
        quantity = random.randint(100, 10000)
        output[f"bidp{i}"] = str(price)
        output[f"bidp_rsqn{i}"] = str(quantity)
    
    # 매도 호가 (1~10호가)
    for i in range(1, 11):
        price = int(base_price * (1 + i * 0.001))
        quantity = random.randint(100, 10000)
        output[f"askp{i}"] = str(price)
        output[f"askp_rsqn{i}"] = str(quantity)
    
    return {"output": output}


def generate_mock_order_history() -> List[Dict[str, Any]]:
    """Mock 주문 내역 데이터 생성"""
    orders = []
    stock_list = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "000660", "name": "SK하이닉스"},
        {"code": "035420", "name": "NAVER"},
    ]
    
    for i in range(10):
        stock = random.choice(stock_list)
        side = random.choice(["매수", "매도"])
        order_type = random.choice(["지정가", "시장가"])
        quantity = random.randint(1, 100)
        price = random.uniform(50000, 200000)
        executed_quantity = random.randint(0, quantity)
        executed_price = price * random.uniform(0.99, 1.01)
        status = random.choice(["접수", "체결", "부분체결", "취소"])
        
        order_time = (datetime.now() - timedelta(hours=random.randint(0, 24))).strftime("%Y%m%d%H%M%S")
        
        orders.append({
            "odno": f"{random.randint(100000, 999999)}",  # 주문번호
            "pdno": stock["code"],  # 종목코드
            "prdt_name": stock["name"],  # 종목명
            "sll_buy_dvsn_cd_name": side,  # 매수/매도
            "ord_dvsn_cd_name": order_type,  # 주문유형
            "ord_qty": str(quantity),  # 주문수량
            "ord_unpr": str(int(price)),  # 주문가격
            "tot_ccld_qty": str(executed_quantity),  # 체결수량
            "avg_prvs": str(int(executed_price)) if executed_quantity > 0 else "0",  # 평균가격
            "ord_stat_cd_name": status,  # 주문상태
            "ord_tmd": order_time,  # 주문시간
        })
    
    return orders


def get_stock_name(stock_code: str) -> str:
    """종목코드로 종목명 반환"""
    stock_names = {
        "005930": "삼성전자",
        "000660": "SK하이닉스",
        "035420": "NAVER",
        "005380": "현대차",
        "035720": "카카오",
        "051910": "LG화학",
        "006400": "삼성SDI",
        "028260": "삼성물산",
        "105560": "KB금융",
        "055550": "신한지주",
    }
    return stock_names.get(stock_code, f"종목{stock_code}")


def generate_mock_chart_data(
    stock_code: str,
    start_date: str,
    end_date: str,
    period: str = "D"
) -> Dict[str, Any]:
    """Mock 차트 데이터 생성 (일봉/주봉/월봉/년봉)"""
    from datetime import datetime, timedelta
    
    # 날짜 파싱
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    
    # 기간별 데이터 개수 계산
    if period == "D":  # 일봉
        days = (end - start).days + 1
        dates = [start + timedelta(days=i) for i in range(min(days, 100))]
    elif period == "W":  # 주봉
        weeks = (end - start).days // 7 + 1
        dates = [start + timedelta(weeks=i) for i in range(min(weeks, 100))]
    elif period == "M":  # 월봉
        months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        dates = []
        current = start
        for i in range(min(months, 100)):
            dates.append(current)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    else:  # 년봉
        years = end.year - start.year + 1
        dates = [start.replace(year=start.year + i) for i in range(min(years, 100))]
    
    base_price = random.uniform(50000, 200000)
    chart_data = []
    
    for i, date in enumerate(dates):
        # 가격 변동 시뮬레이션
        price_change = random.uniform(-0.05, 0.05)
        base_price = base_price * (1 + price_change)
        
        open_price = base_price * random.uniform(0.98, 1.02)
        high_price = max(open_price, base_price) * random.uniform(1.0, 1.03)
        low_price = min(open_price, base_price) * random.uniform(0.97, 1.0)
        close_price = base_price
        volume = random.randint(100000, 10000000)
        
        chart_data.append({
            "stck_bsop_date": date.strftime("%Y%m%d"),  # 기준일자
            "stck_oprc": str(int(open_price)),  # 시가
            "stck_hgpr": str(int(high_price)),  # 최고가
            "stck_lwpr": str(int(low_price)),  # 최저가
            "stck_clpr": str(int(close_price)),  # 종가
            "acml_vol": str(volume),  # 누적 거래량
            "acml_tr_pbmn": str(int(volume * close_price)),  # 누적 거래대금
        })
    
    return {
        "output1": {
            "stck_bsop_date": end_date,
            "stck_clpr": str(int(base_price)),
        },
        "output2": chart_data
    }


def generate_mock_price_trend(stock_code: str) -> Dict[str, Any]:
    """Mock 예상체결가 추이 데이터 생성"""
    base_price = random.uniform(50000, 200000)
    trend_data = []
    
    # 최대 30건의 추이 데이터 생성
    for i in range(30):
        price_change = random.uniform(-0.02, 0.02)
        base_price = base_price * (1 + price_change)
        volume = random.randint(1000, 100000)
        
        trend_data.append({
            "xymd": (datetime.now() - timedelta(minutes=30-i)).strftime("%Y%m%d"),  # 기준일자
            "tmd": (datetime.now() - timedelta(minutes=30-i)).strftime("%H%M%S"),  # 기준시간
            "prpr": str(int(base_price)),  # 현재가
            "cntg_vol": str(volume),  # 체결량
        })
    
    return {
        "output1": {
            "stck_prpr": str(int(base_price)),
            "prdy_vrss": str(int(base_price * 0.01)),
            "prdy_ctrt": "1.0",
        },
        "output2": trend_data
    }


def generate_mock_volume_rank() -> Dict[str, Any]:
    """Mock 거래량순위 데이터 생성"""
    stock_list = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "000660", "name": "SK하이닉스"},
        {"code": "035420", "name": "NAVER"},
        {"code": "005380", "name": "현대차"},
        {"code": "035720", "name": "카카오"},
        {"code": "051910", "name": "LG화학"},
        {"code": "006400", "name": "삼성SDI"},
        {"code": "028260", "name": "삼성물산"},
        {"code": "105560", "name": "KB금융"},
        {"code": "055550", "name": "신한지주"},
    ]
    
    rank_data = []
    for i, stock in enumerate(stock_list):
        base_price = random.uniform(50000, 200000)
        change_price = random.uniform(-5000, 5000)
        change_rate = (change_price / base_price) * 100
        volume = random.randint(1000000, 10000000)
        
        rank_data.append({
            "data_rank": str(i + 1),
            "hts_kor_isnm": stock["name"],
            "mksc_shrn_iscd": stock["code"],
            "stck_prpr": str(int(base_price)),
            "prdy_vrss_sign": "2" if change_price >= 0 else "5",
            "prdy_vrss": str(int(change_price)),
            "prdy_ctrt": str(round(abs(change_rate), 2)),
            "acml_vol": str(volume),
            "acml_tr_pbmn": str(int(volume * base_price)),
        })
    
    return {"output": rank_data}


def generate_mock_fluctuation_rank() -> Dict[str, Any]:
    """Mock 등락률순위 데이터 생성"""
    stock_list = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "000660", "name": "SK하이닉스"},
        {"code": "035420", "name": "NAVER"},
        {"code": "005380", "name": "현대차"},
        {"code": "035720", "name": "카카오"},
    ]
    
    rank_data = []
    # 상승률 상위
    for i, stock in enumerate(stock_list):
        base_price = random.uniform(50000, 200000)
        change_rate = random.uniform(5, 15)  # 5~15% 상승
        change_price = base_price * (change_rate / 100)
        volume = random.randint(1000000, 10000000)
        
        rank_data.append({
            "data_rank": str(i + 1),
            "hts_kor_isnm": stock["name"],
            "mksc_shrn_iscd": stock["code"],
            "stck_prpr": str(int(base_price)),
            "prdy_vrss_sign": "2",
            "prdy_vrss": str(int(change_price)),
            "prdy_ctrt": str(round(change_rate, 2)),
            "acml_vol": str(volume),
        })
    
    return {"output": rank_data}


def generate_mock_market_cap_rank() -> Dict[str, Any]:
    """Mock 시가총액순위 데이터 생성"""
    stock_list = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "000660", "name": "SK하이닉스"},
        {"code": "035420", "name": "NAVER"},
        {"code": "005380", "name": "현대차"},
        {"code": "035720", "name": "카카오"},
        {"code": "051910", "name": "LG화학"},
        {"code": "006400", "name": "삼성SDI"},
        {"code": "028260", "name": "삼성물산"},
        {"code": "105560", "name": "KB금융"},
        {"code": "055550", "name": "신한지주"},
    ]
    
    rank_data = []
    for i, stock in enumerate(stock_list):
        base_price = random.uniform(50000, 200000)
        market_cap = random.uniform(10000000000000, 50000000000000)  # 10조~50조
        change_price = random.uniform(-5000, 5000)
        change_rate = (change_price / base_price) * 100
        
        rank_data.append({
            "data_rank": str(i + 1),
            "hts_kor_isnm": stock["name"],
            "mksc_shrn_iscd": stock["code"],
            "stck_prpr": str(int(base_price)),
            "prdy_vrss_sign": "2" if change_price >= 0 else "5",
            "prdy_vrss": str(int(change_price)),
            "prdy_ctrt": str(round(abs(change_rate), 2)),
            "mrkt_whol_avls_rlim": str(round(market_cap / 1000000000000, 2)),  # 조 단위
        })
    
    return {"output": rank_data}


