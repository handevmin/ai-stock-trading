#!/bin/bash

# EC2 인스턴스 생성 스크립트
# 사용법: ./aws-ec2-setup.sh
# 
# config.sh 파일에서 프로젝트 설정을 읽어옵니다.

set -e

# 설정 파일 로드
if [ -f "./config.sh" ]; then
    source ./config.sh
    echo -e "${GREEN}설정 파일을 로드했습니다: config.sh${NC}"
else
    echo -e "${RED}설정 파일(config.sh)이 없습니다.${NC}"
    echo "먼저 config.sh 파일을 생성하고 프로젝트 설정을 입력해주세요."
    echo "예시: cp config.sh.example config.sh"
    exit 1
fi

echo -e "${GREEN}${PROJECT_DISPLAY_NAME} 프로젝트 EC2 인스턴스 생성 시작${NC}"

# AWS CLI 설치 확인
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI가 설치되지 않았습니다.${NC}"
    echo "설치 방법: pip install awscli"
    exit 1
fi

# AWS 자격 증명 확인
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}AWS 자격 증명이 설정되지 않았습니다.${NC}"
    echo "aws configure 명령어로 설정해주세요."
    exit 1
fi

# 키 디렉토리 생성
mkdir -p $KEY_PATH

# 1. 키 페어 생성
echo -e "${YELLOW}키 페어 생성 중...${NC}"
if aws ec2 describe-key-pairs --key-names $KEY_NAME &> /dev/null; then
    echo -e "${YELLOW}키 페어가 이미 존재합니다: $KEY_NAME${NC}"
else
    aws ec2 create-key-pair \
        --key-name $KEY_NAME \
        --query 'KeyMaterial' \
        --output text > $KEY_PATH/$KEY_NAME.pem
    chmod 400 $KEY_PATH/$KEY_NAME.pem
    echo -e "${GREEN}키 페어 생성 완료: $KEY_PATH/$KEY_NAME.pem${NC}"
fi

# 2. 보안 그룹 생성
echo -e "${YELLOW}보안 그룹 생성 중...${NC}"
SG_ID=$(aws ec2 create-security-group \
    --group-name $SECURITY_GROUP \
    --description "Security group for $PROJECT_NAME app" \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
    --group-names $SECURITY_GROUP \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

echo -e "${GREEN}보안 그룹 ID: $SG_ID${NC}"

# 3. 인바운드 규칙 추가
echo -e "${YELLOW}인바운드 규칙 설정 중...${NC}"

# 설정된 포트들에 대해 인바운드 규칙 추가
for port in "${REQUIRED_PORTS[@]}"; do
    case $port in
        22)
            port_name="SSH"
            ;;
        80)
            port_name="HTTP"
            ;;
        443)
            port_name="HTTPS"
            ;;
        3000)
            port_name="API"
            ;;
        8000)
            port_name="AI API"
            ;;
        5432)
            port_name="PostgreSQL"
            ;;
        *)
            port_name="Port $port"
            ;;
    esac
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port $port \
        --cidr 0.0.0.0/0 &> /dev/null || echo "$port_name 규칙이 이미 존재합니다."
done

echo -e "${GREEN}보안 그룹 규칙 설정 완료${NC}"

# 4. EC2 인스턴스 생성
echo -e "${YELLOW}EC2 인스턴스 생성 중...${NC}"
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":$EBS_VOLUME_SIZE,\"VolumeType\":\"$EBS_VOLUME_TYPE\",\"DeleteOnTermination\":true}}]" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$PROJECT_NAME-server},{Key=Project,Value=$PROJECT_NAME}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo -e "${GREEN}인스턴스 생성 완료: $INSTANCE_ID${NC}"

# 5. 인스턴스 상태 대기
echo -e "${YELLOW}인스턴스가 실행될 때까지 대기 중...${NC}"
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# 6. Elastic IP 할당
echo -e "${YELLOW}Elastic IP 할당 중...${NC}"
ALLOCATION_ID=$(aws ec2 allocate-address \
    --domain vpc \
    --query 'AllocationId' \
    --output text)

# Elastic IP를 인스턴스에 연결
aws ec2 associate-address \
    --instance-id $INSTANCE_ID \
    --allocation-id $ALLOCATION_ID

# Elastic IP에 태그 추가 (정리 시 식별용)
aws ec2 create-tags \
    --resources $ALLOCATION_ID \
    --tags Key=Project,Value=$PROJECT_NAME Key=Name,Value=$PROJECT_NAME-elastic-ip

# Public IP 확인 (Elastic IP)
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo -e "${GREEN}Elastic IP 할당 완료: $PUBLIC_IP${NC}"

echo -e "${GREEN}인스턴스 생성 완료!${NC}"
echo -e "${GREEN}인스턴스 정보:${NC}"
echo "  - Instance ID: $INSTANCE_ID"
echo "  - Public IP: $PUBLIC_IP (Elastic IP)"
echo "  - SSH 접속: ssh -i $KEY_PATH/$KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo "  - 보안 그룹: $SECURITY_GROUP ($SG_ID)"
echo "  - Elastic IP Allocation ID: $ALLOCATION_ID"

# 7. 연결 정보를 파일로 저장
cat > $KEY_PATH/connection-info.txt << EOF
${PROJECT_DISPLAY_NAME} 프로젝트 EC2 인스턴스 정보
=====================================
Instance ID: $INSTANCE_ID
Public IP: $PUBLIC_IP (Elastic IP)
Elastic IP Allocation ID: $ALLOCATION_ID
SSH 접속: ssh -i $KEY_PATH/$KEY_NAME.pem ubuntu@$PUBLIC_IP
보안 그룹: $SECURITY_GROUP ($SG_ID)
생성 시간: $(date)
EOF

echo -e "${GREEN}연결 정보가 $KEY_PATH/connection-info.txt에 저장되었습니다.${NC}"
echo -e "${YELLOW}다음 단계: ./deploy-to-ec2.sh $PUBLIC_IP${NC}"
