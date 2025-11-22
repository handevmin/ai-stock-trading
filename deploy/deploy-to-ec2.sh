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
ssh -i $KEY_FILE ubuntu@$PUBLIC_IP << 'SETUP_EOF'
# 환경 변수 초기화 (EC2 서버 기준)
export HOME="/home/ubuntu"
export USER="ubuntu"
unset NVM_DIR
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
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
export NVM_DIR="/home/ubuntu/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install 18
nvm use 18

# Python 설치 (FastAPI용)
sudo apt-get install -y python3 python3-pip python3-venv

# Git 설치
sudo apt-get install -y git

# net-tools 설치 (netstat 명령어용)
sudo apt-get install -y net-tools

echo "서버 환경 설정 완료"
SETUP_EOF

# 2. 프로젝트 클론
echo -e "${YELLOW}프로젝트 클론 중...${NC}"
ssh -i $KEY_FILE ubuntu@$PUBLIC_IP << CLONE_EOF
# 환경 변수 초기화 (EC2 서버 기준)
export HOME="/home/ubuntu"
export USER="ubuntu"
unset NVM_DIR
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

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

# 클론 시도 (Public 저장소는 토큰 없이 먼저 시도)
CLONE_SUCCESS=false
CLONE_ERROR=""

# 먼저 토큰 없이 시도 (Public 저장소)
echo "Public 저장소로 클론 시도 중..."
if git clone $GITHUB_REPO_URL $PROJECT_NAME 2>&1; then
    echo "Git 클론 성공! (Public 저장소)"
    CLONE_SUCCESS=true
else
    CLONE_ERROR=$(git clone $GITHUB_REPO_URL $PROJECT_NAME 2>&1)
    echo "Public 클론 실패, 토큰을 사용하여 재시도..."
    
    # 토큰이 있는 경우 토큰을 사용한 URL로 재시도
    if [ -n "$GITHUB_TOKEN" ]; then
        REPO_URL_WITH_TOKEN=$(echo $GITHUB_REPO_URL | sed "s|https://|https://$GITHUB_TOKEN@|")
        echo "토큰을 사용하여 클론 시도 중..."
        if git clone $REPO_URL_WITH_TOKEN $PROJECT_NAME 2>&1; then
            echo "Git 클론 성공! (토큰 사용)"
            CLONE_SUCCESS=true
        else
            CLONE_ERROR=$(git clone $REPO_URL_WITH_TOKEN $PROJECT_NAME 2>&1)
            echo "토큰을 사용한 클론도 실패했습니다."
            echo "에러 메시지: $CLONE_ERROR"
        fi
    else
        echo "토큰이 설정되지 않았습니다."
        echo "에러 메시지: $CLONE_ERROR"
    fi
fi

if [ "$CLONE_SUCCESS" = false ]; then
    echo "=========================================="
    echo "Git 클론 실패!"
    echo "저장소 URL: $GITHUB_REPO_URL"
    echo "에러: $CLONE_ERROR"
    echo "=========================================="
    echo "수동으로 클론하려면:"
    if [ -n "$GITHUB_TOKEN" ]; then
        REPO_URL_WITH_TOKEN=$(echo $GITHUB_REPO_URL | sed "s|https://|https://$GITHUB_TOKEN@|")
        echo "git clone $REPO_URL_WITH_TOKEN $PROJECT_NAME"
    else
        echo "git clone $GITHUB_REPO_URL $PROJECT_NAME"
    fi
    echo "=========================================="
    exit 1
fi
CLONE_EOF

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
    echo -e "${RED}프로젝트 폴더가 없습니다: /home/ubuntu/$PROJECT_NAME${NC}"
    echo "Git 클론이 실패했거나 프로젝트가 아직 GitHub에 푸시되지 않았을 수 있습니다."
    echo "다음 단계:"
    echo "1. GitHub 저장소가 존재하는지 확인: $GITHUB_REPO_URL"
    echo "2. 프로젝트를 GitHub에 푸시했는지 확인"
    echo "3. 수동으로 클론: ssh -i $KEY_FILE ubuntu@$PUBLIC_IP 'cd /home/ubuntu && git clone $GITHUB_REPO_URL $PROJECT_NAME'"
    echo "4. 그 다음 다시 배포 스크립트 실행"
    exit 1
fi

# 4. 백엔드 및 프론트엔드 배포
echo -e "${YELLOW}백엔드 및 프론트엔드 배포 중...${NC}"
ssh -i $KEY_FILE ubuntu@$PUBLIC_IP << DEPLOY_EOF
# 환경 변수 초기화 (EC2 서버 기준)
export HOME="/home/ubuntu"
export USER="ubuntu"
unset NVM_DIR
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# 프로젝트 폴더 존재 확인
if [ ! -d "/home/ubuntu/$PROJECT_NAME" ]; then
    echo "에러: 프로젝트 폴더가 없습니다: /home/ubuntu/$PROJECT_NAME"
    echo "Git 클론을 먼저 실행하세요."
    exit 1
fi

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

# 환경 변수 명시적 설정 (EC2 서버 기준)
export HOME="/home/ubuntu"
export NVM_DIR="/home/ubuntu/.nvm"

# NVM 설치 확인 및 재설치
if [ ! -d "/home/ubuntu/.nvm" ]; then
    echo "NVM이 설치되지 않았습니다. 설치 중..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
    export NVM_DIR="/home/ubuntu/.nvm"
fi

# NVM 강제 로드
if [ -s "/home/ubuntu/.nvm/nvm.sh" ]; then
    \. "/home/ubuntu/.nvm/nvm.sh"
    [ -s "/home/ubuntu/.nvm/bash_completion" ] && \. "/home/ubuntu/.nvm/bash_completion"
else
    echo "NVM 스크립트를 찾을 수 없습니다. 재설치 중..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
    export NVM_DIR="/home/ubuntu/.nvm"
    [ -s "/home/ubuntu/.nvm/nvm.sh" ] && \. "/home/ubuntu/.nvm/nvm.sh"
fi

# Node.js 설치 확인 및 설치
if ! command -v node &> /dev/null; then
    echo "Node.js가 설치되지 않았습니다. NVM으로 설치 중..."
    nvm install 18
    nvm use 18
    nvm alias default 18
fi

# NVM으로 설치된 Node.js 경로를 PATH에 명시적으로 추가
if [ -d "/home/ubuntu/.nvm/versions/node" ]; then
    # 모든 Node.js 버전의 bin 디렉토리를 PATH에 추가
    for NODE_DIR in /home/ubuntu/.nvm/versions/node/*/bin; do
        if [ -d "$NODE_DIR" ]; then
            export PATH="$NODE_DIR:$PATH"
        fi
    done
fi

# 최종 확인 - 직접 경로로도 시도
if ! command -v node &> /dev/null; then
    # 직접 경로로 찾기
    NODE_PATH=$(find /home/ubuntu/.nvm/versions/node -name "node" -type f 2>/dev/null | head -1)
    NPM_PATH=$(find /home/ubuntu/.nvm/versions/node -name "npm" -type f 2>/dev/null | head -1)
    
    if [ -n "$NODE_PATH" ] && [ -n "$NPM_PATH" ]; then
        NODE_BIN_DIR=$(dirname "$NODE_PATH")
        export PATH="$NODE_BIN_DIR:$PATH"
        echo "Node.js 경로를 직접 추가: $NODE_BIN_DIR"
    else
        echo "에러: Node.js 또는 npm을 찾을 수 없습니다."
        echo "NVM 디렉토리: /home/ubuntu/.nvm"
        echo "NVM 설치 확인:"
        ls -la /home/ubuntu/.nvm 2>/dev/null || echo "NVM 디렉토리가 없습니다"
        echo "Node.js 버전 디렉토리:"
        ls -la /home/ubuntu/.nvm/versions/node 2>/dev/null || echo "Node.js 버전이 없습니다"
        exit 1
    fi
fi

# Node.js 및 npm 버전 확인
echo "Node.js 버전: $(node --version)"
echo "npm 버전: $(npm --version)"
echo "Node.js 경로: $(which node)"
echo "npm 경로: $(which npm)"

echo "프론트엔드 의존성 설치 중..."
if ! npm install; then
    echo "에러: npm install 실패"
    exit 1
fi

echo "프론트엔드 빌드 중..."
if ! npm run build; then
    echo "에러: npm run build 실패"
    exit 1
fi

# 빌드 결과 확인
if [ ! -d "dist" ]; then
    echo "에러: dist 폴더가 생성되지 않았습니다."
    exit 1
fi

echo "프론트엔드 빌드 완료: dist 폴더 확인됨"
ls -la dist/ | head -10

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

# 프론트엔드 dist 폴더 존재 확인
if [ ! -d "../frontend/dist" ]; then
    echo "에러: 프론트엔드 dist 폴더가 없습니다: ../frontend/dist"
    echo "프론트엔드 빌드를 먼저 실행하세요."
    exit 1
fi

echo "프론트엔드 빌드 파일 확인:"
ls -la ../frontend/dist/ | head -5

# Docker Compose로 서비스 시작
echo "Docker Compose로 서비스 시작 중..."
if ! docker-compose up -d --build; then
    echo "에러: Docker Compose 시작 실패"
    docker-compose logs
    exit 1
fi

echo "백엔드 및 프론트엔드 서비스 시작 완료"
DEPLOY_EOF

# 5. 서비스 상태 확인 및 로그 확인
echo -e "${YELLOW}서비스 상태 확인 중...${NC}"

ssh -i $KEY_FILE ubuntu@$PUBLIC_IP << STATUS_EOF
# 환경 변수 초기화 (EC2 서버 기준)
export HOME="/home/ubuntu"
export USER="ubuntu"
unset NVM_DIR
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# 프로젝트 폴더 존재 확인
if [ ! -d "/home/ubuntu/$PROJECT_NAME/deploy" ]; then
    echo "에러: deploy 폴더가 없습니다: /home/ubuntu/$PROJECT_NAME/deploy"
    exit 1
fi

cd /home/ubuntu/$PROJECT_NAME/deploy

echo "=== Docker 서비스 상태 ==="
docker-compose ps 2>/dev/null || echo "Docker Compose 파일을 찾을 수 없습니다."

echo "=== Docker 로그 (최근 50줄) ==="
docker-compose logs --tail=50 2>/dev/null || echo "Docker Compose가 실행 중이지 않습니다."

echo "=== 포트 사용 현황 ==="
sudo netstat -tlnp 2>/dev/null | grep -E ':(80|8000)' || sudo ss -tlnp 2>/dev/null | grep -E ':(80|8000)' || echo "포트 80, 8000이 사용 중이지 않습니다."

echo "=== 백엔드 헬스 체크 ==="
curl -s http://localhost:8000/health 2>/dev/null || echo "백엔드 연결 실패 (서비스가 실행 중이지 않을 수 있습니다)"
STATUS_EOF

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
