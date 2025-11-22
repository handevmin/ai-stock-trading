#!/bin/bash

# AWS CLI 자동 설정 스크립트
# 사용법: ./setup-aws-cli.sh
# 
# 설정 파일이 없으면 기본값으로 설정하거나 사용자 입력을 받습니다.

set -e

# 설정 파일 로드
if [ -f "./config.sh" ]; then
    source ./config.sh
    echo -e "${GREEN}설정 파일을 로드했습니다: config.sh${NC}"
else
    echo -e "${YELLOW}설정 파일(config.sh)이 없습니다. 기본값을 사용하거나 수동으로 입력해주세요.${NC}"
    
    # 기본값 설정
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
    
    # 사용자 입력 받기
    read -p "AWS Account ID: " AWS_ACCOUNT_ID
    read -p "IAM Username: " AWS_IAM_USERNAME
    read -p "Access Key ID: " AWS_ACCESS_KEY_ID
    read -s -p "Secret Access Key: " AWS_SECRET_ACCESS_KEY
    echo
    read -p "Region (기본값: ap-northeast-2): " AWS_REGION
    AWS_REGION=${AWS_REGION:-ap-northeast-2}
    AWS_OUTPUT_FORMAT="json"
fi

echo -e "${GREEN}AWS CLI 자동 설정 시작${NC}"

echo -e "${YELLOW}계정 정보:${NC}"
echo "  - Account ID: $AWS_ACCOUNT_ID"
echo "  - IAM User: $AWS_IAM_USERNAME"
echo "  - Region: $AWS_REGION"
echo "  - Console URL: https://$AWS_ACCOUNT_ID.signin.aws.amazon.com/console"

# 1. AWS CLI 설치 확인 및 설치
echo -e "${YELLOW}AWS CLI 설치 확인 중...${NC}"
if ! command -v aws &> /dev/null; then
    echo -e "${YELLOW}AWS CLI가 설치되지 않았습니다. 설치를 시작합니다...${NC}"
    
    # 운영체제 확인
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            # Ubuntu/Debian
            sudo apt-get update
            sudo apt-get install -y awscli
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL
            sudo yum install -y awscli
        else
            # pip 사용
            pip3 install awscli
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install awscli
        else
            pip3 install awscli
        fi
    else
        # Windows 또는 기타
        echo -e "${RED}지원되지 않는 운영체제입니다. 수동으로 AWS CLI를 설치해주세요.${NC}"
        echo "설치 방법: pip install awscli"
        exit 1
    fi
    
    echo -e "${GREEN}AWS CLI 설치 완료${NC}"
else
    echo -e "${GREEN}AWS CLI가 이미 설치되어 있습니다.${NC}"
fi

# 2. AWS CLI 버전 확인
echo -e "${YELLOW}AWS CLI 버전 확인...${NC}"
aws --version

# 3. AWS 자격 증명 설정
echo -e "${YELLOW}AWS 자격 증명 설정 중...${NC}"

# AWS 디렉토리 생성
mkdir -p ~/.aws

# credentials 파일 생성
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
EOF

# config 파일 생성
cat > ~/.aws/config << EOF
[default]
region = $AWS_REGION
output = $AWS_OUTPUT_FORMAT
EOF

echo -e "${GREEN}AWS 자격 증명 설정 완료${NC}"

# 4. 설정 확인
echo -e "${YELLOW}설정 확인 중...${NC}"

# 자격 증명 확인
echo -e "${YELLOW}자격 증명 확인:${NC}"
if aws sts get-caller-identity &> /dev/null; then
    aws sts get-caller-identity
    echo -e "${GREEN}자격 증명이 올바르게 설정되었습니다.${NC}"
else
    echo -e "${RED}자격 증명 설정에 실패했습니다.${NC}"
    exit 1
fi

# 리전 확인
echo -e "${YELLOW}리전 확인:${NC}"
aws configure get region

# 출력 형식 확인
echo -e "${YELLOW}출력 형식 확인:${NC}"
aws configure get output

# 5. EC2 권한 테스트
echo -e "${YELLOW}EC2 권한 테스트 중...${NC}"
if aws ec2 describe-instances --max-items 1 &> /dev/null; then
    echo -e "${GREEN}EC2 권한이 올바르게 설정되었습니다.${NC}"
else
    echo -e "${RED}EC2 권한이 없습니다. IAM 사용자에 EC2 권한을 추가해주세요.${NC}"
    exit 1
fi

# 6. 설정 정보 출력
echo -e "${GREEN}AWS CLI 설정 완료!${NC}"
echo -e "${GREEN}설정 정보:${NC}"
echo "  - Access Key ID: $AWS_ACCESS_KEY_ID"
echo "  - Region: $AWS_REGION"
echo "  - Output Format: $AWS_OUTPUT_FORMAT"
echo "  - Config File: ~/.aws/config"
echo "  - Credentials File: ~/.aws/credentials"

echo -e "${YELLOW}다음 단계:${NC}"
echo "  1. config.sh 파일을 수정하여 프로젝트 설정을 변경하세요"
echo "  2. EC2 인스턴스 생성: ./aws-ec2-setup.sh"
echo "  3. 프로젝트 배포: ./deploy-to-ec2.sh <PUBLIC_IP>"

echo -e "${GREEN}AWS CLI 설정이 완료되었습니다!${NC}"