"""KIS API 연결 테스트 스크립트"""
import asyncio
import httpx
from app.config import settings

async def test_connection():
    """KIS API 연결 테스트"""
    print("=" * 60)
    print("KIS API 연결 테스트")
    print("=" * 60)
    
    # 설정 확인
    print(f"\n1. 설정 확인:")
    print(f"   KIS_BASE_URL: {settings.KIS_BASE_URL}")
    print(f"   KIS_APP_KEY: {settings.KIS_APP_KEY[:20]}...")
    print(f"   KIS_APP_SECRET: {'설정됨' if settings.KIS_APP_SECRET else '미설정'}")
    print(f"   KIS_ACCOUNT_NO: {settings.KIS_ACCOUNT_NO}")
    
    # 기본 연결 테스트
    print(f"\n2. 기본 연결 테스트:")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://openapi.koreainvestment.com")
            print(f"   ✅ 기본 연결 성공 (상태 코드: {response.status_code})")
    except Exception as e:
        print(f"   ❌ 기본 연결 실패: {e}")
    
    # 토큰 발급 테스트
    print(f"\n3. 토큰 발급 테스트:")
    endpoint = "/oauth2/tokenP"
    url = f"{settings.KIS_BASE_URL}{endpoint}"
    
    data = {
        "grant_type": "client_credentials",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
    }
    
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            print(f"   상태 코드: {response.status_code}")
            print(f"   응답 내용: {response.text[:200]}")
            
            if response.status_code == 200:
                result = response.json()
                if "access_token" in result:
                    print(f"   ✅ 토큰 발급 성공!")
                    print(f"   토큰 (일부): {result['access_token'][:20]}...")
                else:
                    print(f"   ⚠️  토큰 발급 응답은 받았지만 access_token이 없습니다.")
                    print(f"   응답: {result}")
            else:
                print(f"   ❌ 토큰 발급 실패 (상태 코드: {response.status_code})")
    except httpx.ConnectError as e:
        print(f"   ❌ 연결 오류: {e}")
        print(f"   가능한 원인:")
        print(f"   - 네트워크 연결 문제")
        print(f"   - 방화벽 또는 프록시 설정")
        print(f"   - DNS 문제")
    except httpx.TimeoutException as e:
        print(f"   ❌ 시간 초과: {e}")
    except Exception as e:
        print(f"   ❌ 오류 발생: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_connection())

