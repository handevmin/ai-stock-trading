#!/bin/bash

# EC2 배포 스크립트
# 사용법: ./deploy-to-ec2.sh <PUBLIC_IP>
# 
# config.sh 파일에서 프로젝트 설정을 읽어옵니다.

set -e

if [ -z "$1" ]; then
    echo "사용법: ./deploy-to-ec2.sh <PUBLIC_IP>"
    exit 1
fi

PUBLIC_IP=$1

# 설정 파일 로드
if [ -f "./config.sh" ]; then
    source ./config.sh
    echo -e "${GREEN}설정 파일을 로드했습니다: config.sh${NC}"
else
    echo -e "${RED}설정 파일(config.sh)이 없습니다.${NC}"
    echo "먼저 config.sh 파일을 생성하고 프로젝트 설정을 입력해주세요."
    exit 1
fi

KEY_FILE="$KEY_PATH/$KEY_NAME.pem"

echo -e "${GREEN}${PROJECT_DISPLAY_NAME} 프로젝트 EC2 배포 시작${NC}"

# 키 파일 확인
if [ ! -f "$KEY_FILE" ]; then
    echo -e "${RED}키 파일을 찾을 수 없습니다: $KEY_FILE${NC}"
    exit 1
fi

# SSH 연결 테스트
echo -e "${YELLOW}EC2 인스턴스 연결 테스트...${NC}"
if ! ssh -i $KEY_FILE -o ConnectTimeout=10 -o StrictHostKeyChecking=no ubuntu@$PUBLIC_IP "echo '연결 성공'" &> /dev/null; then
    echo -e "${RED}EC2 인스턴스에 연결할 수 없습니다.${NC}"
    echo "인스턴스가 실행 중인지 확인해주세요."
    exit 1
fi

echo -e "${GREEN}EC2 인스턴스 연결 확인${NC}"

# 1. 서버 환경 설정
echo -e "${YELLOW}서버 환경 설정 중...${NC}"
ssh -i $KEY_FILE ubuntu@$PUBLIC_IP << 'EOF'
# 디스크 공간 확인
echo "=== 디스크 공간 확인 ==="
df -h

# 불필요한 파일 정리
echo "=== 불필요한 파일 정리 ==="
sudo apt-get clean
sudo apt-get autoclean
sudo apt-get autoremove -y
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

# Docker 정리 (이미 설치된 경우)
sudo docker system prune -a -f 2>/dev/null || true

# 로그 파일 정리
sudo journalctl --vacuum-time=1d 2>/dev/null || true
sudo find /var/log -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true

# 큰 파일 찾기 및 정리
echo "=== 큰 파일 찾기 ==="
sudo find / -type f -size +100M 2>/dev/null | head -10

# 시스템 업데이트
sudo apt-get update -y
sudo apt-get upgrade -y

# 스왑 메모리 추가 (2GB)
echo "=== 스왑 메모리 설정 ==="
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "스왑 메모리 설정 완료"
    free -h
else
    echo "스왑 파일이 이미 존재합니다."
fi

# Docker 설치
echo "=== Docker 설치 ==="
# 필수 패키지 설치
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Docker 공식 GPG 키 추가
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Docker 저장소 추가
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker Engine 설치
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ubuntu

# Docker Compose 설치
echo "=== Docker Compose 설치 ==="
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Node.js 설치 (React 빌드용)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18

# Python 설치 (FastAPI용)
sudo apt-get install -y python3 python3-pip python3-venv

# Git 설치
sudo apt-get install -y git

# net-tools 설치 (netstat 명령어용)
sudo apt-get install -y net-tools

echo "서버 환경 설정 완료"
EOF

# 2. 프로젝트 클론
echo -e "${YELLOW}프로젝트 클론 중...${NC}"
ssh -i $KEY_FILE ubuntu@$PUBLIC_IP << EOF
cd /home/ubuntu

# 디스크 공간 다시 확인
echo "=== 클론 전 디스크 공간 확인 ==="
df -h

if [ -d "$PROJECT_NAME" ]; then
    echo "기존 프로젝트 폴더가 존재합니다. 백업 후 새로 클론합니다."
    mv $PROJECT_NAME ${PROJECT_NAME}_backup_\$(date +%Y%m%d_%H%M%S)
fi

# GitHub 저장소 클론
echo "GitHub 저장소 클론 시도 중..."
echo "저장소 URL: $GITHUB_REPO_URL"

# Git 설정 확인
git config --global user.name "EC2-Deploy"
git config --global user.email "deploy@ec2.local"

# 클론 시도 (공간 부족 시 대안 제공)
AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_SPACE" -lt 1000000 ]; then
    echo "디스크 공간이 부족합니다. 클론을 건너뜁니다."
    echo "수동으로 클론하거나 디스크 공간을 확보한 후 다시 시도하세요."
    echo "필요한 명령어:"
    if [ -n "$GITHUB_TOKEN" ]; then
        # 토큰이 있는 경우 토큰을 사용한 URL 생성
        REPO_URL_WITH_TOKEN=$(echo $GITHUB_REPO_URL | sed "s|https://|https://$GITHUB_TOKEN@|")
        echo "git clone $REPO_URL_WITH_TOKEN $PROJECT_NAME"
    else
        echo "git clone $GITHUB_REPO_URL $PROJECT_NAME"
    fi
else
    if [ -n "$GITHUB_TOKEN" ]; then
        # 토큰이 있는 경우 토큰을 사용한 URL 생성
        REPO_URL_WITH_TOKEN=$(echo $GITHUB_REPO_URL | sed "s|https://|https://$GITHUB_TOKEN@|")
        if git clone $REPO_URL_WITH_TOKEN $PROJECT_NAME; then
            echo "Git 클론 성공!"
        else
            echo "Git 클론 실패. 수동으로 시도해보세요:"
            echo "git clone $REPO_URL_WITH_TOKEN $PROJECT_NAME"
        fi
    else
        if git clone $GITHUB_REPO_URL $PROJECT_NAME; then
            echo "Git 클론 성공!"
        else
            echo "Git 클론 실패. 수동으로 시도해보세요:"
            echo "git clone $GITHUB_REPO_URL $PROJECT_NAME"
        fi
    fi
fi
EOF

# 3. Docker Compose 및 Nginx 설정 파일 복사
echo -e "${YELLOW}Docker Compose 및 Nginx 설정 파일 복사 중...${NC}"
# 프로젝트 폴더가 존재하는지 확인 후 복사
if ssh -i $KEY_FILE ubuntu@$PUBLIC_IP "test -d /home/ubuntu/$PROJECT_NAME"; then
    # deploy 폴더 생성 및 파일 복사
    ssh -i $KEY_FILE ubuntu@$PUBLIC_IP "mkdir -p /home/ubuntu/$PROJECT_NAME/deploy"
    scp -i $KEY_FILE docker-compose.yml ubuntu@$PUBLIC_IP:/home/ubuntu/$PROJECT_NAME/deploy/
    scp -i $KEY_FILE nginx.conf ubuntu@$PUBLIC_IP:/home/ubuntu/$PROJECT_NAME/deploy/
    echo "Docker Compose 파일과 Nginx 설정 파일 복사 완료"
else
    echo "프로젝트 폴더가 없습니다. 수동으로 클론 후 다시 시도하세요."
fi

# 4. 백엔드 및 프론트엔드 배포
echo -e "${YELLOW}백엔드 및 프론트엔드 배포 중...${NC}"
ssh -i $KEY_FILE ubuntu@$PUBLIC_IP << EOF
cd /home/ubuntu/$PROJECT_NAME

# Python 가상 환경 생성 및 의존성 설치
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# React 프론트엔드 빌드
cd ../frontend
source ~/.nvm/nvm.sh
npm install
npm run build

# 시스템 Nginx 중지 및 완전 비활성화 (포트 충돌 방지)
sudo systemctl stop nginx 2>/dev/null || true
sudo systemctl disable nginx 2>/dev/null || true
sudo systemctl mask nginx 2>/dev/null || true

# 기존 컨테이너 정리
docker rm -f ${PROJECT_NAME}-backend ${PROJECT_NAME}-nginx 2>/dev/null || true

# Docker Compose로 서비스 시작
cd /home/ubuntu/$PROJECT_NAME/deploy

# .env 파일 생성 (Docker Compose가 사용)
cat > .env << ENV_EOF
# 프로젝트 설정
PROJECT_NAME=$PROJECT_NAME

# KIS API 설정
KIS_APP_KEY=$KIS_APP_KEY
KIS_APP_SECRET=$KIS_APP_SECRET
KIS_ACCOUNT_NO=$KIS_ACCOUNT_NO
KIS_ACCOUNT_PRODUCT_CD=$KIS_ACCOUNT_PRODUCT_CD
KIS_BASE_URL=$KIS_BASE_URL

# 데이터베이스 설정
DATABASE_URL=sqlite:///./trading.db

# 서버 설정
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_URL=http://$PUBLIC_IP

# 기타 설정
USE_MOCK_DATA=$USE_MOCK_DATA
ENV_EOF

echo ".env 파일 생성 완료"

# Docker Compose로 서비스 시작
docker-compose up -d --build

echo "백엔드 및 프론트엔드 서비스 시작 완료"
EOF

# 5. 서비스 상태 확인 및 로그 확인
echo -e "${YELLOW}서비스 상태 확인 중...${NC}"

ssh -i $KEY_FILE ubuntu@$PUBLIC_IP << 'EOF'
cd /home/ubuntu/$PROJECT_NAME/deploy

echo "=== Docker 서비스 상태 ==="
docker-compose ps

echo "=== Docker 로그 (최근 50줄) ==="
docker-compose logs --tail=50

echo "=== 포트 사용 현황 ==="
sudo netstat -tlnp | grep -E ':(80|8000)' || ss -tlnp | grep -E ':(80|8000)'

echo "=== 백엔드 헬스 체크 ==="
curl -s http://localhost:8000/health || echo "백엔드 연결 실패"
EOF

echo -e "${GREEN}배포 완료!${NC}"
echo -e "${GREEN}접속 정보:${NC}"
echo "  - 웹 앱: http://$PUBLIC_IP"
echo "  - API: http://$PUBLIC_IP/api"
echo "  - API 문서: http://$PUBLIC_IP/api/docs"
echo "  - 헬스 체크: http://$PUBLIC_IP/health"
echo "  - SSH: ssh -i $KEY_FILE ubuntu@$PUBLIC_IP"

# 배포 정보 저장
cat > $KEY_PATH/deployment-info.txt << EOF
${PROJECT_DISPLAY_NAME} 프로젝트 배포 정보
============================
Public IP: $PUBLIC_IP
웹 앱: http://$PUBLIC_IP
API: http://$PUBLIC_IP/api
API 문서: http://$PUBLIC_IP/api/docs
헬스 체크: http://$PUBLIC_IP/health
SSH: ssh -i $KEY_FILE ubuntu@$PUBLIC_IP
배포 시간: $(date)
EOF

echo -e "${GREEN}배포 정보가 $KEY_PATH/deployment-info.txt에 저장되었습니다.${NC}"
