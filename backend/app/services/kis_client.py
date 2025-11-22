"""KIS API 클라이언트"""
import httpx
import os
import asyncio
import yaml
from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.utils.logger import logger
from app.utils.validators import sanitize_error_message
from app.utils.mock_data import (
    generate_mock_account_balance,
    generate_mock_holdings,
    generate_mock_current_price,
    generate_mock_orderbook,
    generate_mock_order_history,
)


class KISClient:
    """한국투자증권 KIS API 클라이언트"""
    
    # 클래스 레벨 락 (동시 요청 방지)
    _token_lock = asyncio.Lock()
    
    def __init__(self):
        self.base_url = settings.KIS_BASE_URL
        self.app_key = settings.KIS_APP_KEY
        self.app_secret = settings.KIS_APP_SECRET
        self.account_no = settings.KIS_ACCOUNT_NO
        self.account_product_cd = settings.KIS_ACCOUNT_PRODUCT_CD
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        # 토큰 파일 경로 설정 (공식 코드 방식)
        config_root = Path(os.path.expanduser("~")) / "KIS" / "config"
        config_root.mkdir(parents=True, exist_ok=True)
        self.token_file = config_root / f"KIS{datetime.today().strftime('%Y%m%d')}.yaml"
        
        # KIS API 설정 검증
        if not settings.validate_kis_settings():
            logger.warning("KIS API 설정이 완료되지 않았습니다. API 기능을 사용할 수 없습니다.")
        
        # 서버 시작 시 저장된 토큰 로드
        self._load_token_from_file()
    
    def _parse_account_no(self) -> tuple:
        """계좌번호를 CANO와 ACNT_PRDT_CD로 분리"""
        account_no = self.account_no.strip()
        
        # 계좌번호가 10자리인 경우 (앞 8자리 + 뒤 2자리)
        if len(account_no) == 10:
            return account_no[:8], account_no[8:]
        
        # 계좌번호가 10자리 미만인 경우
        # KIS_ACCOUNT_PRODUCT_CD를 사용하여 구성
        if len(account_no) < 10:
            # 앞부분을 0으로 패딩하여 8자리로 만들고, 뒤에 상품코드 추가
            cano = account_no.zfill(8)[:8]  # 최대 8자리
            acnt_prdt_cd = self.account_product_cd.zfill(2)[:2]  # 최대 2자리
            logger.info(f"계좌번호 파싱: {account_no} -> CANO={cano}, ACNT_PRDT_CD={acnt_prdt_cd}")
            return cano, acnt_prdt_cd
        
        # 계좌번호가 10자리 초과인 경우 앞 10자리만 사용
        if len(account_no) > 10:
            logger.warning(f"계좌번호가 10자리를 초과합니다. 앞 10자리만 사용합니다: {account_no}")
            return account_no[:8], account_no[8:10]
        
        return account_no[:8], account_no[8:]
    
    def _save_token_to_file(self, token: str, expires_at: datetime):
        """토큰을 파일에 저장 (공식 코드 방식)"""
        try:
            with open(self.token_file, "w", encoding="utf-8") as f:
                yaml.dump({
                    "token": token,
                    "valid-date": expires_at.strftime("%Y-%m-%d %H:%M:%S")
                }, f, default_flow_style=False, allow_unicode=True)
            logger.debug(f"토큰을 파일에 저장했습니다: {self.token_file}")
        except Exception as e:
            logger.warning(f"토큰 파일 저장 실패: {e}")
    
    def _load_token_from_file(self) -> Optional[str]:
        """파일에서 토큰 로드 (공식 코드 방식)"""
        try:
            if not self.token_file.exists():
                return None
            
            with open(self.token_file, "r", encoding="UTF-8") as f:
                token_data = yaml.safe_load(f)
            
            if not token_data or "token" not in token_data:
                return None
            
            token = token_data["token"]
            valid_date_str = token_data.get("valid-date", "")
            
            if valid_date_str:
                try:
                    valid_date = datetime.strptime(valid_date_str, "%Y-%m-%d %H:%M:%S")
                    now = datetime.now()
                    
                    # 토큰이 아직 유효한 경우
                    if valid_date > now:
                        self.access_token = token
                        self.token_expires_at = valid_date
                        logger.info(f"파일에서 유효한 토큰을 로드했습니다. 만료일시: {valid_date_str}")
                        return token
                    else:
                        logger.info(f"파일에 저장된 토큰이 만료되었습니다. 만료일시: {valid_date_str}")
                        return None
                except ValueError as e:
                    logger.warning(f"토큰 만료일시 파싱 실패: {e}")
                    return None
            
            return token
        except Exception as e:
            logger.debug(f"토큰 파일 로드 실패 (정상): {e}")
            return None
        
    def _get_headers(self, include_token: bool = True, tr_id: Optional[str] = None) -> Dict[str, str]:
        """API 요청 헤더 생성 (공식 코드 방식)"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "charset": "UTF-8",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        
        if include_token and self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"
        
        if tr_id:
            headers["tr_id"] = tr_id  # 공식 코드 방식: tr_id 사용
        
        headers["custtype"] = "P"  # 일반(개인고객,법인고객) "P", 제휴사 "B"
        headers["tr_cont"] = ""  # 연속 거래 여부 (공식 코드 방식)
        
        return headers
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        tr_id: Optional[str] = None,
        tr_cont: str = "",
        retry: bool = True,
        include_token: bool = True
    ) -> Dict[str, Any]:
        """API 요청 실행 (공식 코드 방식)"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(include_token=include_token, tr_id=tr_id)
        
        if tr_cont:
            headers["tr_cont"] = tr_cont
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=data, params=params)
                else:
                    raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
                
                response.raise_for_status()
                result = response.json()
                
                # KIS API 응답 형식 확인
                if "rt_cd" in result:
                    rt_cd = result.get("rt_cd", "")
                    if rt_cd != "0":
                        error_msg = result.get("msg1", "알 수 없는 오류")
                        msg_cd = result.get("msg_cd", "")
                        logger.error("=" * 60)
                        logger.error("KIS API 호출 실패")
                        logger.error(f"응답 코드 (rt_cd): {rt_cd}")
                        logger.error(f"오류 코드 (msg_cd): {msg_cd}")
                        logger.error(f"오류 메시지 (msg1): {error_msg}")
                        logger.error(f"요청 URL: {url}")
                        logger.error(f"요청 파라미터: {params if params else data}")
                        logger.error("=" * 60)
                        raise Exception(f"KIS API 오류: {error_msg} (코드: {msg_cd})")
                    else:
                        # 성공 응답 로그 (상세 로그는 각 메서드에서 처리)
                        logger.debug(f"KIS API 호출 성공: {url} (rt_cd: {rt_cd})")
                
                return result
                
        except httpx.ConnectError as e:
            error_msg = sanitize_error_message(str(e))
            logger.error("=" * 60)
            logger.error("KIS API 연결 실패")
            logger.error(f"오류 메시지: {error_msg}")
            logger.error(f"연결 시도 URL: {url}")
            logger.error(f"요청 메서드: {method}")
            logger.error(f"요청 파라미터: {params if params else data}")
            logger.error("가능한 원인:")
            logger.error("1. 네트워크 연결 문제")
            logger.error("2. KIS API 서버 장애")
            logger.error("3. 방화벽 또는 프록시 설정 문제")
            logger.error(f"4. KIS_BASE_URL 확인 필요: {self.base_url}")
            logger.error("=" * 60)
            raise ConnectionError(f"KIS API 서버에 연결할 수 없습니다. 네트워크 연결과 API 엔드포인트를 확인해주세요. URL: {url}")
        except httpx.TimeoutException as e:
            error_msg = sanitize_error_message(str(e))
            logger.error("=" * 60)
            logger.error("KIS API 요청 시간 초과")
            logger.error(f"오류 메시지: {error_msg}")
            logger.error(f"요청 URL: {url}")
            logger.error(f"요청 메서드: {method}")
            logger.error(f"요청 파라미터: {params if params else data}")
            logger.error("=" * 60)
            raise TimeoutError(f"KIS API 요청이 시간 초과되었습니다. 네트워크 상태를 확인해주세요.")
        except httpx.HTTPStatusError as e:
            error_msg = sanitize_error_message(str(e))
            logger.error("=" * 60)
            logger.error("HTTP 오류 발생")
            logger.error(f"응답 상태 코드: {e.response.status_code}")
            logger.error(f"요청 URL: {url}")
            logger.error(f"요청 메서드: {method}")
            logger.error(f"요청 파라미터: {params if params else data}")
            
            # 응답 내용 파싱 시도
            try:
                error_response = e.response.json()
                logger.error("응답 내용 (JSON):")
                if "msg1" in error_response:
                    logger.error(f"  오류 메시지 (msg1): {error_response.get('msg1')}")
                if "msg_cd" in error_response:
                    logger.error(f"  오류 코드 (msg_cd): {error_response.get('msg_cd')}")
                if "rt_cd" in error_response:
                    logger.error(f"  응답 코드 (rt_cd): {error_response.get('rt_cd')}")
                logger.error(f"  전체 응답: {error_response}")
            except:
                logger.error(f"응답 내용 (텍스트): {e.response.text[:500]}")
            logger.error("=" * 60)
            
            # 토큰 만료 시 재시도
            if retry and e.response.status_code == 401:
                logger.info("토큰 만료로 인한 재인증 시도")
                await self.refresh_token()
                return await self._request(method, endpoint, data, params, tr_id, retry=False, include_token=include_token)
            
            raise
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            logger.error("=" * 60)
            logger.error("API 요청 오류")
            logger.error(f"오류 타입: {type(e).__name__}")
            logger.error(f"오류 메시지: {error_msg}")
            logger.error(f"요청 URL: {url}")
            logger.error(f"요청 메서드: {method}")
            logger.error(f"요청 파라미터: {params if params else data}")
            logger.error("=" * 60)
            raise
    
    async def get_access_token(self) -> str:
        """액세스 토큰 발급 (동시 요청 방지 및 파일 저장)"""
        # 락을 사용하여 동시 요청 방지
        async with KISClient._token_lock:
            # 파일에서 토큰 로드 시도
            saved_token = self._load_token_from_file()
            if saved_token and self.is_token_valid():
                logger.info("파일에서 유효한 토큰을 사용합니다.")
                return saved_token
            
            # KIS API 설정 검증
            if not self.app_key or not self.app_secret:
                raise ValueError("KIS API 키가 설정되지 않았습니다. .env 파일에서 KIS_APP_KEY와 KIS_APP_SECRET을 확인해주세요.")
            
            endpoint = "/oauth2/tokenP"
            data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            }
            
            try:
                logger.info(f"토큰 발급 시도: {self.base_url}{endpoint}")
                # 토큰 발급은 특별한 헤더 필요 (공식 코드 방식)
                url = f"{self.base_url}{endpoint}"
                headers = {
                    "Content-Type": "application/json",
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=data)
                    
                    # 403 오류 시 상세 정보 로깅
                    if response.status_code == 403:
                        error_detail = response.text
                        logger.error(f"토큰 발급 403 오류 - 응답 내용: {error_detail}")
                        
                        # 응답 파싱 시도
                        try:
                            error_json = response.json()
                            error_code = error_json.get("error_code", "")
                            error_desc = error_json.get("error_description", "")
                            
                            # 1분당 1회 제한 오류인 경우
                            if "EGW00133" in error_code or "1분당 1회" in error_desc:
                                logger.warning("토큰 발급 요청 제한 (1분당 1회). 파일에서 토큰을 확인합니다.")
                                # 파일에서 토큰 로드 시도
                                saved_token = self._load_token_from_file()
                                if saved_token:
                                    self.access_token = saved_token
                                    logger.info("파일에서 토큰을 로드하여 재사용합니다.")
                                    return saved_token
                                elif self.access_token:
                                    logger.warning("기존 메모리 토큰을 재사용합니다.")
                                    return self.access_token
                                else:
                                    # 토큰이 전혀 없는 경우 Mock 데이터 사용 안내
                                    logger.error("기존 토큰이 없어 재사용할 수 없습니다. 1분 후 다시 시도하거나 Mock 데이터를 사용하세요.")
                                    if settings.USE_MOCK_DATA:
                                        logger.warning("USE_MOCK_DATA가 활성화되어 있습니다. Mock 데이터를 사용할 수 있습니다.")
                                    raise ValueError("토큰 발급 요청 제한. 기존 토큰이 없어 1분 후 다시 시도하세요.")
                            else:
                                logger.error("가능한 원인:")
                                logger.error("1. API 키가 잘못되었거나 만료됨")
                                logger.error("2. API 키에 해당 기능 권한이 없음")
                                logger.error("3. 모의투자 키를 실거래 환경에서 사용하거나 그 반대")
                                logger.error("4. 계정이 비활성화되었거나 제한됨")
                        except ValueError:
                            raise  # ValueError는 다시 발생시킴
                        except:
                            pass
                    
                    response.raise_for_status()
                    result = response.json()
                
                self.access_token = result.get("access_token")
                
                if not self.access_token:
                    raise ValueError("토큰 발급 응답에 access_token이 없습니다.")
                
                # 토큰 만료 시간 설정 (일반적으로 24시간)
                expires_in = result.get("expires_in", 86400)
                from datetime import timedelta
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                access_token_token_expired = result.get("access_token_token_expired", "")
                
                # 토큰을 파일에 저장
                if access_token_token_expired:
                    try:
                        expires_at = datetime.strptime(access_token_token_expired, "%Y-%m-%d %H:%M:%S")
                        self._save_token_to_file(self.access_token, expires_at)
                    except ValueError:
                        # 파싱 실패 시 계산된 만료 시간 사용
                        self._save_token_to_file(self.access_token, self.token_expires_at)
                else:
                    self._save_token_to_file(self.access_token, self.token_expires_at)
                
                logger.info(f"액세스 토큰 발급 완료 (유효기간: {expires_in}초, 만료일시: {access_token_token_expired})")
                return self.access_token
                
            except httpx.HTTPStatusError as e:
                # 403 오류 처리
                if e.response.status_code == 403:
                    error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
                    
                    # 응답 파싱 시도
                    try:
                        error_json = e.response.json()
                        error_code = error_json.get("error_code", "")
                        error_desc = error_json.get("error_description", "")
                        
                        # 1분당 1회 제한 오류인 경우
                        if "EGW00133" in error_code or "1분당 1회" in error_desc:
                            # 기존 토큰이 있으면 재사용 (유효성과 관계없이)
                            if self.access_token:
                                if self.is_token_valid():
                                    logger.warning("토큰 발급 제한으로 인해 기존 유효한 토큰을 재사용합니다.")
                                else:
                                    logger.warning("토큰 발급 제한. 기존 토큰이 만료되었지만 재사용을 시도합니다.")
                                return self.access_token
                            else:
                                # 토큰이 전혀 없는 경우에만 에러 발생
                                logger.error("기존 토큰이 없어 재사용할 수 없습니다. 1분 후 다시 시도하세요.")
                                raise ValueError("토큰 발급 요청 제한 (1분당 1회). 기존 토큰이 없어 1분 후 다시 시도하세요.")
                    except ValueError:
                        raise  # ValueError는 다시 발생시킴
                    except:
                        pass
                    
                    logger.error(f"토큰 발급 실패 (403 Forbidden): {error_detail}")
                    logger.error("API 키 인증 실패. 다음을 확인하세요:")
                    logger.error("1. KIS 디벨로퍼스에서 API 키가 활성화되어 있는지")
                    logger.error("2. API 키와 Secret이 올바른지")
                    logger.error("3. 모의투자/실거래 환경이 올바른지")
                    if settings.USE_MOCK_DATA:
                        logger.warning("USE_MOCK_DATA가 활성화되어 있지만, 403 오류는 API 키 문제이므로 Mock 데이터로 폴백하지 않습니다.")
                    raise ValueError("API 키 인증 실패. KIS 디벨로퍼스에서 API 키 상태를 확인하세요.")
                raise
            except ConnectionError as e:
                logger.error(f"토큰 발급 실패 (연결 오류): {e}")
                if settings.USE_MOCK_DATA:
                    logger.warning("연결 오류로 인해 Mock 데이터를 사용할 수 없습니다. 토큰이 필요합니다.")
                raise
            except Exception as e:
                logger.error(f"토큰 발급 실패: {e}")
                logger.error(f"API 키 확인: app_key={self.app_key[:10]}... (일부만 표시)")
                raise
    
    async def refresh_token(self) -> str:
        """토큰 갱신"""
        logger.info("토큰 갱신 중...")
        return await self.get_access_token()
    
    def is_token_valid(self) -> bool:
        """토큰 유효성 확인"""
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at
    
    async def ensure_token(self) -> str:
        """토큰이 유효한지 확인하고 필요시 갱신"""
        # 토큰이 유효하면 재사용 (불필요한 요청 방지)
        if self.is_token_valid() and self.access_token:
            return self.access_token
        
        # 파일에서 토큰 로드 시도
        saved_token = self._load_token_from_file()
        if saved_token and self.is_token_valid():
            logger.info("파일에서 유효한 토큰을 로드했습니다.")
            return saved_token
        
        # 토큰이 만료되었지만 기존 토큰이 있으면 재사용 시도
        # (토큰 발급 제한을 피하기 위해)
        if self.access_token:
            logger.info("토큰이 만료되었지만 기존 토큰을 재사용합니다. API 호출 시 필요하면 자동 갱신됩니다.")
            return self.access_token
        
        # 토큰이 전혀 없는 경우에만 새로 발급
        try:
            await self.refresh_token()
        except ValueError as e:
            # 요청 제한 오류인 경우 파일에서 토큰 로드 시도
            if "1분당 1회" in str(e) or "요청 제한" in str(e):
                saved_token = self._load_token_from_file()
                if saved_token:
                    logger.warning("토큰 발급 제한으로 인해 파일에서 토큰을 재사용합니다.")
                    self.access_token = saved_token
                    return saved_token
                elif self.access_token:
                    logger.warning("토큰 발급 제한으로 인해 기존 토큰을 재사용합니다.")
                    return self.access_token
            raise
        
        return self.access_token
    
    # 계좌 정보 조회
    async def get_account_balance(self) -> Dict[str, Any]:
        """계좌 잔고 조회"""
        try:
            await self.ensure_token()
            
            endpoint = "/uapi/domestic-stock/v1/trading/inquire-balance"
            tr_id = "TTTC8434R"  # 계좌 잔고 조회 (공식 코드: 실전투자용)
            
            # 계좌번호 파싱 (공식 코드 방식: 8자리 + 2자리)
            cano, acnt_prdt_cd = self._parse_account_no()
            
            params = {
                "CANO": cano,  # 종합계좌번호 앞 8자리
                "ACNT_PRDT_CD": acnt_prdt_cd,  # 계좌상품코드 뒤 2자리
                "AFHR_FLPR_YN": "N",  # 시간외단일가여부
                "OFL_YN": "",  # 오프라인여부
                "INQR_DVSN": "02",  # 조회구분 (01:대출일별, 02:종목별)
                "UNPR_DVSN": "01",  # 단가구분
                "FUND_STTL_ICLD_YN": "N",  # 펀드결제분포함여부
                "FNCG_AMT_AUTO_RDPT_YN": "N",  # 융자금액자동상환여부
                "PRCS_DVSN": "01",  # 처리구분
                "CTX_AREA_FK100": "",  # 연속조회검색조건100
                "CTX_AREA_NK100": "",  # 연속조회키100
            }
            
            logger.info("=" * 60)
            logger.info("계좌 잔고 조회 API 호출 시작")
            logger.info(f"요청 URL: {self.base_url}{endpoint}")
            logger.info(f"요청 파라미터: {params}")
            logger.info("=" * 60)
            
            result = await self._request("GET", endpoint, params=params, tr_id=tr_id)
            
            # API 호출 성공 로그
            logger.info("=" * 60)
            logger.info("계좌 잔고 조회 API 호출 성공")
            rt_cd = result.get("rt_cd", "")
            msg1 = result.get("msg1", "")
            output1_count = len(result.get("output1", []))
            output2_count = len(result.get("output2", []))
            logger.info(f"응답 코드 (rt_cd): {rt_cd}")
            logger.info(f"응답 메시지 (msg1): {msg1}")
            logger.info(f"보유 종목 수 (output1): {output1_count}")
            logger.info(f"계좌 정보 수 (output2): {output2_count}")
            if output1_count == 0:
                logger.warning("보유 종목이 없거나 API 응답에 output1이 없습니다.")
            if output2_count == 0:
                logger.warning("계좌 정보가 없거나 API 응답에 output2가 없습니다.")
            logger.info("=" * 60)
            
            return result
        except httpx.HTTPStatusError as e:
            # 500 오류 처리 (계좌번호 문제 등)
            if e.response.status_code == 500:
                try:
                    error_response = e.response.json()
                    msg_cd = error_response.get("msg_cd", "")
                    msg1 = error_response.get("msg1", "")
                    rt_cd = error_response.get("rt_cd", "")
                    
                    logger.error("=" * 60)
                    logger.error("계좌 조회 500 오류 발생")
                    logger.error(f"응답 코드 (rt_cd): {rt_cd}")
                    logger.error(f"오류 코드 (msg_cd): {msg_cd}")
                    logger.error(f"오류 메시지 (msg1): {msg1}")
                    logger.error(f"현재 계좌번호: {self.account_no}")
                    cano, acnt_prdt_cd = self._parse_account_no()
                    logger.error(f"파싱된 계좌번호: CANO={cano}, ACNT_PRDT_CD={acnt_prdt_cd}")
                    logger.error("전체 응답:")
                    logger.error(f"  {error_response}")
                    
                    # OPS 라우팅 오류는 계좌번호 문제일 가능성이 높음
                    if "EGW00203" in msg_cd or "OPS라우팅" in msg1:
                        logger.error("")
                        logger.error("원인 분석:")
                        logger.error("  - 계좌번호가 올바르지 않거나 계좌가 API에 등록되지 않았을 수 있습니다.")
                        logger.error("  - KIS 디벨로퍼스에서 실제 계좌번호를 확인하세요.")
                        logger.error("  - 계좌가 API 사용 신청이 완료되었는지 확인하세요.")
                    
                    logger.error("=" * 60)
                    
                    if settings.USE_MOCK_DATA:
                        logger.warning("계좌 조회 실패로 Mock 데이터를 사용합니다.")
                        return generate_mock_account_balance(self.account_no)
                except Exception as parse_error:
                    logger.error(f"오류 응답 파싱 실패: {parse_error}")
                    logger.error(f"응답 텍스트: {e.response.text[:500]}")
            raise
        except (ConnectionError, TimeoutError) as e:
            if settings.USE_MOCK_DATA:
                logger.warning(f"API 연결 실패, Mock 데이터 사용: {e}")
                return generate_mock_account_balance(self.account_no)
            raise
    
    # 시세 조회
    async def get_current_price(self, stock_code: str) -> Dict[str, Any]:
        """현재가 조회"""
        await self.ensure_token()
        
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
        tr_id = "FHKST01010100"  # 주식현재가 시세
        
        params = {
            "fid_cond_mrkt_div_code": "J",  # 시장분류코드 (J: 주식)
            "fid_input_iscd": stock_code,  # 종목코드
        }
        
        return await self._request("GET", endpoint, params=params, tr_id=tr_id)
    
    async def get_orderbook(self, stock_code: str) -> Dict[str, Any]:
        """호가 조회"""
        try:
            await self.ensure_token()
            
            endpoint = "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
            tr_id = "FHKST01010200"  # 주식호가
            
            params = {
                "fid_cond_mrkt_div_code": "J",  # 시장분류코드
                "fid_input_iscd": stock_code,  # 종목코드
            }
            
            return await self._request("GET", endpoint, params=params, tr_id=tr_id)
        except (ConnectionError, TimeoutError) as e:
            if settings.USE_MOCK_DATA:
                logger.warning(f"API 연결 실패, Mock 데이터 사용: {e}")
                return generate_mock_orderbook(stock_code)
            raise
    
    async def search_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """종목 기본 정보 조회"""
        try:
            await self.ensure_token()
            
            endpoint = "/uapi/domestic-stock/v1/quotations/search-stock-info"
            tr_id = "CTPF1002R"  # 주식기본조회
            
            params = {
                "PRDT_TYPE_CD": "300",  # 300: 주식, ETF, ETN, ELW
                "PDNO": stock_code,  # 종목번호
            }
            
            return await self._request("GET", endpoint, params=params, tr_id=tr_id)
        except (ConnectionError, TimeoutError) as e:
            if settings.USE_MOCK_DATA:
                logger.warning(f"API 연결 실패, Mock 데이터 사용: {e}")
                # Mock 종목 정보 반환
                return {
                    "output": [{
                        "pdno": stock_code,
                        "prdt_name": f"종목{stock_code}",
                        "prdt_abrv_name": f"종목{stock_code}",
                        "prdt_eng_name": f"Stock{stock_code}",
                    }]
                }
            raise
    
    async def get_daily_chart(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        period: str = "D"  # D:일봉, W:주봉, M:월봉, Y:년봉
    ) -> Dict[str, Any]:
        """일봉/주봉/월봉/년봉 차트 데이터 조회"""
        try:
            await self.ensure_token()
            
            endpoint = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
            tr_id = "FHKST03010100"  # 국내주식기간별시세
            
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # 시장분류코드 (J:KRX)
                "FID_INPUT_ISCD": stock_code,  # 종목코드
                "FID_INPUT_DATE_1": start_date,  # 조회 시작일자 (YYYYMMDD)
                "FID_INPUT_DATE_2": end_date,  # 조회 종료일자 (YYYYMMDD)
                "FID_PERIOD_DIV_CODE": period,  # 기간분류코드 (D:일봉, W:주봉, M:월봉, Y:년봉)
                "FID_ORG_ADJ_PRC": "0",  # 수정주가 (0:수정주가, 1:원주가)
            }
            
            return await self._request("GET", endpoint, params=params, tr_id=tr_id)
        except (ConnectionError, TimeoutError) as e:
            if settings.USE_MOCK_DATA:
                logger.warning(f"API 연결 실패, Mock 데이터 사용: {e}")
                # Mock 차트 데이터 생성
                from app.utils.mock_data import generate_mock_chart_data
                return generate_mock_chart_data(stock_code, start_date, end_date, period)
            raise
    
    async def get_price_trend(self, stock_code: str) -> Dict[str, Any]:
        """예상체결가 추이 조회"""
        try:
            await self.ensure_token()
            
            endpoint = "/uapi/domestic-stock/v1/quotations/exp-price-trend"
            tr_id = "FHPST01810000"  # 국내주식 예상체결가 추이
            
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # 시장분류코드
                "FID_INPUT_ISCD": stock_code,  # 종목코드
                "FID_MKOP_CLS_CODE": "0",  # 0:전체, 4:체결량 0 제외
            }
            
            return await self._request("GET", endpoint, params=params, tr_id=tr_id)
        except (ConnectionError, TimeoutError) as e:
            if settings.USE_MOCK_DATA:
                logger.warning(f"API 연결 실패, Mock 데이터 사용: {e}")
                # Mock 추세 데이터 생성
                from app.utils.mock_data import generate_mock_price_trend
                return generate_mock_price_trend(stock_code)
            raise
    
    async def get_volume_rank(
        self,
        market_code: str = "J",  # J:KRX, NX:NXT, UN:통합
        sort_type: str = "0"  # 0:평균거래량, 1:거래증가율, 2:평균거래회전율, 3:거래금액순, 4:평균거래금액회전율
    ) -> Dict[str, Any]:
        """거래량순위 조회"""
        try:
            await self.ensure_token()
            
            endpoint = "/uapi/domestic-stock/v1/quotations/volume-rank"
            tr_id = "FHPST01710000"  # 거래량순위
            
            params = {
                "FID_COND_MRKT_DIV_CODE": market_code,
                "FID_COND_SCR_DIV_CODE": "20171",  # 거래량순위 화면코드
                "FID_INPUT_ISCD": "0000",  # 전체
                "FID_DIV_CLS_CODE": "0",  # 전체
                "FID_BLNG_CLS_CODE": sort_type,  # 정렬 기준
                "FID_TRGT_CLS_CODE": "000000000",  # 대상 구분 코드
                "FID_TRGT_EXLS_CLS_CODE": "0000000000",  # 대상 제외 구분 코드
                "FID_INPUT_PRICE_1": "",  # 가격 하한
                "FID_INPUT_PRICE_2": "",  # 가격 상한
                "FID_VOL_CNT": "",  # 거래량 필터
                "FID_INPUT_DATE_1": "",  # 날짜
            }
            
            return await self._request("GET", endpoint, params=params, tr_id=tr_id)
        except (ConnectionError, TimeoutError) as e:
            if settings.USE_MOCK_DATA:
                logger.warning(f"API 연결 실패, Mock 데이터 사용: {e}")
                from app.utils.mock_data import generate_mock_volume_rank
                return generate_mock_volume_rank()
            raise
    
    async def get_fluctuation_rank(
        self,
        market_code: str = "J",  # J:KRX, Q:코스닥
        sort_type: str = "0000"  # 0000:등락률순
    ) -> Dict[str, Any]:
        """등락률순위 조회"""
        try:
            await self.ensure_token()
            
            endpoint = "/uapi/domestic-stock/v1/ranking/fluctuation"
            tr_id = "FHPST01700000"  # 등락률 순위
            
            params = {
                "fid_cond_mrkt_div_code": market_code,
                "fid_cond_scr_div_code": "20170",  # 등락률 화면코드
                "fid_input_iscd": "0000",  # 전체
                "fid_rank_sort_cls_code": sort_type,
                "fid_input_cnt_1": "100",  # 조회 개수
                "fid_prc_cls_code": "0",  # 가격 구분 (0:전체)
                "fid_input_price_1": "",  # 가격 하한
                "fid_input_price_2": "",  # 가격 상한
                "fid_vol_cnt": "",  # 거래량 필터
                "fid_trgt_cls_code": "0",  # 대상 구분 코드
                "fid_trgt_exls_cls_code": "0",  # 대상 제외 구분 코드
                "fid_div_cls_code": "0",  # 분류 구분 코드
                "fid_rsfl_rate1": "",  # 등락 비율1
                "fid_rsfl_rate2": "",  # 등락 비율2
            }
            
            return await self._request("GET", endpoint, params=params, tr_id=tr_id)
        except (ConnectionError, TimeoutError) as e:
            if settings.USE_MOCK_DATA:
                logger.warning(f"API 연결 실패, Mock 데이터 사용: {e}")
                from app.utils.mock_data import generate_mock_fluctuation_rank
                return generate_mock_fluctuation_rank()
            raise
    
    async def get_market_cap_rank(
        self,
        market_code: str = "J"  # J:KRX
    ) -> Dict[str, Any]:
        """시가총액순위 조회"""
        try:
            await self.ensure_token()
            
            endpoint = "/uapi/domestic-stock/v1/ranking/market-cap"
            tr_id = "FHPST01740000"  # 시가총액 상위
            
            params = {
                "fid_cond_mrkt_div_code": market_code,
                "fid_cond_scr_div_code": "20174",  # 시가총액 화면코드
                "fid_div_cls_code": "0",  # 전체
                "fid_input_iscd": "0000",  # 전체
                "fid_trgt_cls_code": "0",  # 대상 구분 코드
                "fid_trgt_exls_cls_code": "0",  # 대상 제외 구분 코드
                "fid_input_price_1": "",  # 가격 하한
                "fid_input_price_2": "",  # 가격 상한
                "fid_vol_cnt": "",  # 거래량 필터
            }
            
            return await self._request("GET", endpoint, params=params, tr_id=tr_id)
        except (ConnectionError, TimeoutError) as e:
            if settings.USE_MOCK_DATA:
                logger.warning(f"API 연결 실패, Mock 데이터 사용: {e}")
                from app.utils.mock_data import generate_mock_market_cap_rank
                return generate_mock_market_cap_rank()
            raise
    
    # 주문
    async def place_order(
        self,
        stock_code: str,
        side: str,  # "BUY" or "SELL"
        quantity: int,
        price: float,
        order_type: str = "00"  # 00: 지정가, 01: 시장가
    ) -> Dict[str, Any]:
        """주문 실행"""
        await self.ensure_token()
        
        endpoint = "/uapi/domestic-stock/v1/trading/order-cash"
        tr_id = "TTTC0802U"  # 현금주문
        
        # 매수/매도 구분
        sll_buy_dvsn_cd = "02" if side.upper() == "BUY" or side == "매수" else "01"
        
        # 계좌번호 파싱
        cano, acnt_prdt_cd = self._parse_account_no()
        
        data = {
            "CANO": cano,  # 종합계좌번호 앞 8자리
            "ACNT_PRDT_CD": acnt_prdt_cd,  # 계좌상품코드 뒤 2자리
            "PDNO": stock_code,  # 종목코드
            "ORD_DVSN": order_type,  # 주문구분 (00: 지정가, 01: 시장가)
            "ORD_QTY": str(quantity),  # 주문수량
            "ORD_UNPR": str(int(price)),  # 주문단가
            "SLL_BUY_DVSN_CD": sll_buy_dvsn_cd,  # 매도매수구분코드
        }
        
        return await self._request("POST", endpoint, data=data, tr_id=tr_id)
    
    async def cancel_order(self, order_no: str, stock_code: str) -> Dict[str, Any]:
        """주문 취소"""
        await self.ensure_token()
        
        endpoint = "/uapi/domestic-stock/v1/trading/order-rvsecncl"
        tr_id = "TTTC0803U"  # 주문취소
        
        # 계좌번호 파싱
        cano, acnt_prdt_cd = self._parse_account_no()
        
        data = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "KRX_FWDG_ORD_ORGNO": "",  # 한국거래소전송주문조직번호
            "ORGN_ODNO": order_no,  # 원주문번호
            "ORD_DVSN": "00",  # 주문구분
            "RVSE_CNCL_DVSN_CD": "02",  # 정정취소구분코드 (02: 취소)
            "ORD_QTY": "0",  # 주문수량
            "ORD_UNPR": "0",  # 주문단가
            "QTY_ALL_ORD_YN": "Y",  # 전량주문여부
        }
        
        return await self._request("POST", endpoint, data=data, tr_id=tr_id)
    
    async def get_order_history(self) -> Dict[str, Any]:
        """주문 내역 조회"""
        await self.ensure_token()
        
        endpoint = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        tr_id = "TTTC8001R"  # 일별주문체결조회
        
        # 계좌번호 파싱
        cano, acnt_prdt_cd = self._parse_account_no()
        
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "INQR_STRT_DT": "",  # 조회시작일자
            "INQR_END_DT": "",  # 조회종료일자
            "SLL_BUY_DVSN_CD": "00",  # 매도매수구분코드 (00: 전체)
            "INQR_DVSN": "00",  # 조회구분 (00: 역순)
            "PDNO": "",  # 종목코드
            "CCLD_DVSN": "00",  # 체결구분 (00: 전체)
            "ORD_GNO_BRNO": "",  # 주문채번지점번호
            "ODNO": "",  # 주문번호
            "INQR_DVSN_3": "00",  # 조회구분3
            "INQR_DVSN_1": "",  # 조회구분1
            "CTX_AREA_FK100": "",  # 연속조회검색조건100
            "CTX_AREA_NK100": "",  # 연속조회키100
        }
        
        return await self._request("GET", endpoint, params=params, tr_id=tr_id)

