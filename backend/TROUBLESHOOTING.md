# 문제 해결 가이드

## 연결 오류 (All connection attempts failed)

### 증상
```
ERROR - API 요청 오류: All connection attempts failed
ERROR - 토큰 발급 실패: All connection attempts failed
```

### 가능한 원인 및 해결 방법

#### 1. KIS API 키가 설정되지 않음
**확인 사항:**
- `backend/.env` 파일이 존재하는지 확인
- `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_NO`가 올바르게 설정되었는지 확인

**해결 방법:**
```bash
# backend/.env 파일 확인
cd backend
cat .env  # 또는 Windows에서 type .env
```

`.env` 파일에 다음이 올바르게 설정되어 있어야 합니다:
```env
KIS_APP_KEY=실제_앱_키
KIS_APP_SECRET=실제_앱_시크릿
KIS_ACCOUNT_NO=실제_계좌번호
```

#### 2. 네트워크 연결 문제
**확인 사항:**
- 인터넷 연결 상태 확인
- 방화벽이나 프록시가 KIS API 서버 접근을 차단하는지 확인

**해결 방법:**
```bash
# KIS API 서버 연결 테스트
curl https://openapi.koreainvestment.com/oauth2/tokenP
```

#### 3. KIS API 엔드포인트 URL 오류
**확인 사항:**
- `KIS_BASE_URL`이 올바른지 확인
- 한국투자증권 API 문서에서 최신 엔드포인트 확인

**해결 방법:**
- [KIS 디벨로퍼스](https://apiportal.koreainvestment.com/)에서 최신 API 문서 확인
- `backend/.env`의 `KIS_BASE_URL` 확인

#### 4. KIS API 키가 유효하지 않음
**확인 사항:**
- KIS 디벨로퍼스에서 발급받은 키가 올바른지 확인
- 키가 만료되었는지 확인

**해결 방법:**
1. [KIS 디벨로퍼스](https://apiportal.koreainvestment.com/)에 로그인
2. 앱 관리에서 키 확인
3. 필요시 새로 발급

#### 5. 모의투자 vs 실거래 환경
**확인 사항:**
- `KIS_ACCOUNT_PRODUCT_CD` 설정 확인
  - `01`: 실거래
  - `02`: 모의투자

**해결 방법:**
```env
# 모의투자 환경 사용 시
KIS_ACCOUNT_PRODUCT_CD=02
```

## 토큰 발급 실패

### 증상
```
ERROR - 토큰 발급 실패: ...
```

### 해결 방법

1. **API 키 확인**
   - `.env` 파일의 `KIS_APP_KEY`와 `KIS_APP_SECRET` 확인
   - 키에 공백이나 따옴표가 포함되지 않았는지 확인

2. **KIS 디벨로퍼스 확인**
   - 앱이 활성화되어 있는지 확인
   - API 사용 권한이 있는지 확인

3. **로그 확인**
   - 서버 로그에서 더 자세한 오류 메시지 확인
   - KIS API 응답 내용 확인

## 계좌 정보 조회 실패

### 증상
```
ERROR - 계좌 잔고 조회 실패: ...
```

### 해결 방법

1. **계좌번호 확인**
   - `.env` 파일의 `KIS_ACCOUNT_NO` 확인
   - 계좌번호가 올바른 형식인지 확인 (10자리)

2. **계좌 권한 확인**
   - 해당 계좌에 API 접근 권한이 있는지 확인
   - KIS 디벨로퍼스에서 계좌 연결 확인

## 일반적인 디버깅 방법

### 1. 로그 레벨 확인
서버 로그에서 상세한 오류 메시지 확인

### 2. API 직접 테스트
```bash
# 토큰 발급 테스트
curl -X POST https://openapi.koreainvestment.com/oauth2/tokenP \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "appkey": "YOUR_APP_KEY",
    "appsecret": "YOUR_APP_SECRET"
  }'
```

### 3. 환경 변수 확인
```python
# Python에서 확인
from app.config import settings
print(f"KIS_APP_KEY: {settings.KIS_APP_KEY[:10]}...")
print(f"KIS_BASE_URL: {settings.KIS_BASE_URL}")
```

### 4. 네트워크 진단
```bash
# DNS 확인
nslookup openapi.koreainvestment.com

# 연결 테스트
ping openapi.koreainvestment.com
```

## 추가 도움말

- [KIS 디벨로퍼스 문서](https://apiportal.koreainvestment.com/)
- [KIS API 가이드](https://apiportal.koreainvestment.com/apiservice)



