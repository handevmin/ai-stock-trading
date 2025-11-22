# 주식 자동매매 시스템

한국투자증권 KIS API를 활용한 주식 자동매매 시스템입니다. 웹 대시보드와 백엔드 서버를 포함하며, 실거래 환경을 지원하고 나중에 전략을 추가할 수 있는 확장 가능한 구조로 설계되었습니다.

## 주요 기능

- **KIS API 연동**: 한국투자증권 KIS API를 통한 실시간 시세 조회 및 주문 실행
- **웹 대시보드**: 계좌 정보, 보유 종목, 주문 내역을 실시간으로 확인
- **자동매매 전략**: 확장 가능한 전략 시스템 (기본 구조 제공)
- **토큰 관리**: KIS API 토큰 자동 갱신
- **실거래 지원**: 실거래 및 모의투자 환경 지원

## 기술 스택

### 백엔드
- FastAPI (Python)
- SQLAlchemy (데이터베이스 ORM)
- SQLite (개발 환경) / PostgreSQL (운영 환경)
- httpx (HTTP 클라이언트)

### 프론트엔드
- React 18
- TypeScript
- Vite
- Axios

## 프로젝트 구조

```
AI주식/
├── backend/              # 백엔드 서버
│   ├── app/
│   │   ├── api/         # API 라우터
│   │   ├── models/      # 데이터베이스 모델
│   │   ├── services/    # 비즈니스 로직
│   │   └── utils/       # 유틸리티
│   └── requirements.txt
├── frontend/             # 프론트엔드
│   ├── src/
│   │   ├── components/  # React 컴포넌트
│   │   └── services/   # API 클라이언트
│   └── package.json
└── README.md
```

## 설치 및 실행

### 사전 요구사항

- Python 3.8 이상
- Node.js 18 이상
- 한국투자증권 KIS 디벨로퍼스 계정 및 API 키

### 1. KIS 디벨로퍼스 가입 및 API 키 발급

1. [KIS 디벨로퍼스](https://apiportal.koreainvestment.com/)에 접속하여 회원가입
2. 앱 등록 후 `app_key`와 `app_secret` 발급
3. 계좌번호 확인

### 2. 백엔드 설정

```bash
# 백엔드 디렉토리로 이동
cd backend

# 가상 환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열어서 KIS API 키와 계좌 정보 입력
```

`.env` 파일 예시:
```env
KIS_APP_KEY=app_key
KIS_APP_SECRET=app_secret
KIS_ACCOUNT_NO=account_no
KIS_ACCOUNT_PRODUCT_CD=01  # 01: 실거래, 02: 모의투자
```

### 3. 백엔드 실행

```bash
cd backend
python -m uvicorn app.main:app --reload
```

백엔드 서버가 `http://localhost:8000`에서 실행됩니다.

### 4. 프론트엔드 설정

```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# 의존성 설치
npm install
```

### 5. 프론트엔드 실행

```bash
npm run dev
```

프론트엔드가 `http://localhost:3000`에서 실행됩니다.

## 사용 방법

### 1. 웹 대시보드 접속

브라우저에서 `http://localhost:3000`에 접속합니다.

### 2. 계좌 정보 확인

"계좌 정보" 탭에서 계좌 잔고와 보유 종목을 확인할 수 있습니다.

### 3. 주문 내역 확인

"주문 내역" 탭에서 과거 주문 내역을 확인할 수 있습니다.

### 4. 전략 설정

"전략 설정" 탭에서 자동매매 전략을 등록하고 관리할 수 있습니다.

## API 문서

백엔드 서버 실행 후 `http://localhost:8000/docs`에서 Swagger UI를 통해 API 문서를 확인할 수 있습니다.

## 주요 API 엔드포인트

### 계좌
- `GET /api/account/balance` - 계좌 잔고 조회
- `GET /api/account/holdings` - 보유 종목 조회

### 시세
- `GET /api/market/current-price/{stock_code}` - 현재가 조회
- `GET /api/market/orderbook/{stock_code}` - 호가 조회

### 주문
- `POST /api/order/place` - 주문 실행
- `POST /api/order/cancel/{order_no}` - 주문 취소
- `GET /api/order/history` - 주문 내역 조회

### 전략
- `GET /api/strategy` - 전략 목록 조회
- `POST /api/strategy` - 전략 생성
- `PUT /api/strategy/{id}` - 전략 업데이트
- `DELETE /api/strategy/{id}` - 전략 삭제

## 전략 시스템 확장

전략 시스템은 확장 가능한 구조로 설계되었습니다. 새로운 전략을 추가하려면:

1. `BaseStrategy` 클래스를 상속받아 전략 클래스 생성
2. 필수 메서드 구현:
   - `should_buy()` - 매수 조건
   - `should_sell()` - 매도 조건
   - `calculate_buy_quantity()` - 매수 수량 계산
   - `calculate_buy_price()` - 매수 가격 계산
   - `calculate_sell_price()` - 매도 가격 계산

예시:
```python
from app.services.strategy_engine import BaseStrategy

class MyStrategy(BaseStrategy):
    def should_buy(self, stock_code: str, market_data: Dict[str, Any]) -> bool:
        # 매수 조건 로직
        return market_data["current_price"] < market_data["prev_close"]
    
    # ... 나머지 메서드 구현
```

## 주의사항

⚠️ **실거래 환경 사용 시 주의사항**

- 본 시스템은 실거래 환경을 지원하지만, 충분한 테스트 없이 사용하지 마세요
- 모의투자 환경에서 충분히 테스트한 후 실거래로 전환하세요
- 자동매매는 손실 위험이 있으므로 신중하게 사용하세요
- API 키와 계좌 정보는 절대 공개하지 마세요

## 문제 해결

### 토큰 갱신 오류
- KIS API 키가 올바른지 확인
- 네트워크 연결 상태 확인
- `/api/auth/token/refresh` 엔드포인트로 수동 갱신 시도

### 주문 실행 실패
- 계좌 잔고 확인
- 종목 코드가 올바른지 확인
- 주문 유형 및 가격이 유효한지 확인

## 라이선스

이 프로젝트는 개인 사용 목적으로 제공됩니다.

## 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.



