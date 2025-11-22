# AI 주식 자동매매 시스템 배포 가이드

이 가이드는 AWS EC2에 AI 주식 자동매매 시스템을 배포하는 방법을 설명합니다.

## 사전 준비사항

1. **AWS 계정 및 자격 증명**
   - AWS 계정 ID
   - AWS Access Key ID
   - AWS Secret Access Key
   - EC2 권한이 있는 IAM 사용자

2. **KIS API 자격 증명**
   - KIS 디벨로퍼스 계정
   - App Key
   - App Secret
   - 계좌번호

3. **GitHub 저장소**
   - 프로젝트가 GitHub에 푸시되어 있어야 합니다
   - Private 저장소인 경우 Personal Access Token 필요

## 배포 단계

### 1. 설정 파일 수정

`deploy/config.sh` 파일을 열어 다음 정보를 입력하세요:

```bash
# 프로젝트 기본 정보
PROJECT_NAME="ai-stock-trading"
PROJECT_DISPLAY_NAME="AI 주식 자동매매 시스템"

# AWS 설정
AWS_ACCOUNT_ID="your-aws-account-id"
AWS_ACCESS_KEY_ID="your-access-key-id"
AWS_SECRET_ACCESS_KEY="your-secret-access-key"

# GitHub 저장소 설정
GITHUB_REPO_URL="https://github.com/your-username/your-repo.git"
GITHUB_TOKEN="your-github-token"  # Private 저장소인 경우만 필요

# KIS API 설정
KIS_APP_KEY="your-kis-app-key"
KIS_APP_SECRET="your-kis-app-secret"
KIS_ACCOUNT_NO="your-account-number"
KIS_ACCOUNT_PRODUCT_CD="02"  # 01: 실거래, 02: 모의투자
KIS_BASE_URL="https://openapivts.koreainvestment.com:29443"  # 모의투자
# 실거래: https://openapi.koreainvestment.com:9443

# 기타 설정
USE_MOCK_DATA="False"
```

### 2. AWS CLI 설정 (최초 1회)

```bash
cd deploy
chmod +x setup-aws-cli.sh
./setup-aws-cli.sh
```

이 스크립트는:
- AWS CLI 설치 확인 및 설치
- AWS 자격 증명 설정
- EC2 권한 테스트

### 3. EC2 인스턴스 생성

```bash
chmod +x aws-ec2-setup.sh
./aws-ec2-setup.sh
```

이 스크립트는:
- EC2 키 페어 생성
- 보안 그룹 생성 및 포트 설정
- EC2 인스턴스 생성
- Elastic IP 할당

생성 완료 후 Public IP가 출력됩니다. 이 IP를 다음 단계에서 사용합니다.

### 4. 프로젝트 배포

```bash
chmod +x deploy-to-ec2.sh
./deploy-to-ec2.sh <PUBLIC_IP>
```

예시:
```bash
./deploy-to-ec2.sh 3.35.86.197
```

이 스크립트는:
1. 서버 환경 설정 (Docker, Node.js, Python 등)
2. 프로젝트 클론
3. Docker Compose 및 Nginx 설정 파일 복사
4. 백엔드 및 프론트엔드 빌드
5. Docker Compose로 서비스 시작
6. 서비스 상태 확인

## 배포 후 확인

배포가 완료되면 다음 URL로 접속할 수 있습니다:

- **웹 앱**: `http://<PUBLIC_IP>`
- **API 문서**: `http://<PUBLIC_IP>/api/docs`
- **헬스 체크**: `http://<PUBLIC_IP>/health`

## 서비스 관리

### 로그 확인

```bash
ssh -i keys/ai-stock-trading-key.pem ubuntu@<PUBLIC_IP>
cd ai-stock-trading/deploy
docker-compose logs -f
```

### 서비스 재시작

```bash
cd ai-stock-trading/deploy
docker-compose restart
```

### 서비스 중지

```bash
cd ai-stock-trading/deploy
docker-compose down
```

### 서비스 시작

```bash
cd ai-stock-trading/deploy
docker-compose up -d
```

## 문제 해결

### 배포 실패 시

1. **로그 확인**
   ```bash
   ssh -i keys/ai-stock-trading-key.pem ubuntu@<PUBLIC_IP>
   cd ai-stock-trading/deploy
   docker-compose logs
   ```

2. **수동 배포**
   ```bash
   ssh -i keys/ai-stock-trading-key.pem ubuntu@<PUBLIC_IP>
   cd ai-stock-trading
   
   # 백엔드
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # 프론트엔드
   cd ../frontend
   npm install
   npm run build
   
   # Docker Compose
   cd ../deploy
   docker-compose up -d --build
   ```

### 포트 충돌

포트가 이미 사용 중인 경우:
```bash
sudo netstat -tlnp | grep -E ':(80|8000)'
# 또는
sudo ss -tlnp | grep -E ':(80|8000)'
```

### 디스크 공간 부족

```bash
# 디스크 공간 확인
df -h

# 불필요한 파일 정리
sudo docker system prune -a -f
sudo apt-get clean
sudo apt-get autoremove -y
```

## 보안 권장사항

1. **환경 변수 보호**
   - `config.sh` 파일에 민감한 정보가 포함되어 있습니다
   - Git에 커밋하지 마세요 (`.gitignore`에 추가)
   - 배포 후 `config.sh` 파일을 안전한 곳에 백업하세요

2. **SSH 키 보호**
   - 키 파일(`*.pem`)은 절대 공유하지 마세요
   - 키 파일 권한: `chmod 400 keys/*.pem`

3. **방화벽 설정**
   - 필요한 포트만 열어두세요
   - SSH(22) 포트는 특정 IP에서만 접근 가능하도록 제한하는 것을 권장합니다

4. **HTTPS 설정**
   - Let's Encrypt를 사용하여 SSL 인증서 발급
   - Nginx에 HTTPS 설정 추가

## 비용 관리

- EC2 인스턴스는 사용 시간에 따라 비용이 발생합니다
- 사용하지 않을 때는 인스턴스를 중지하세요
- Elastic IP는 인스턴스에 연결되어 있지 않으면 비용이 발생합니다

## 다음 단계

1. **도메인 연결**: Route 53 또는 다른 DNS 서비스를 사용하여 도메인 연결
2. **SSL 인증서**: Let's Encrypt를 사용하여 HTTPS 설정
3. **모니터링**: CloudWatch를 사용하여 서비스 모니터링
4. **백업**: 데이터베이스 정기 백업 설정

