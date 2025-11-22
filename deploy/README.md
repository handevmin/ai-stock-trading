# AWS EC2 배포 스크립트 템플릿

이 템플릿은 AWS EC2에 프로젝트를 자동으로 배포하기 위한 스크립트 모음입니다.

## 파일 구성

- `config.sh` - 프로젝트별 설정 파일
- `setup-aws-cli.sh` - AWS CLI 설정 스크립트
- `aws-ec2-setup.sh` - EC2 인스턴스 생성 스크립트
- `deploy-to-ec2.sh` - 프로젝트 배포 스크립트

## 사용 방법

### 1. 설정 파일 수정

먼저 `config.sh` 파일을 수정하여 프로젝트별 설정을 입력하세요:

```bash
# 프로젝트 기본 정보
PROJECT_NAME="project-name"
PROJECT_DISPLAY_NAME="Project Name"

# AWS 설정
AWS_ACCOUNT_ID="account-id"
AWS_ACCESS_KEY_ID="access-key-id"
AWS_SECRET_ACCESS_KEY="secret-access-key"

# GitHub 저장소 설정
GITHUB_REPO_URL="https://github.com/handevmin/ai-stock-trading.git"
GITHUB_TOKEN="github-token"

# 기타 설정들...
```

### 2. AWS CLI 설정 (PC당 최초 1회)

```bash
chmod +x setup-aws-cli.sh
./setup-aws-cli.sh
```

### 3. EC2 인스턴스 생성

```bash
chmod +x aws-ec2-setup.sh
./aws-ec2-setup.sh
```

### 4. 프로젝트 배포

```bash
chmod +x deploy-to-ec2.sh
./deploy-to-ec2.sh <PUBLIC_IP>
```

## Windows 환경에서의 실행 방법

Windows PowerShell에서는 `.sh` 파일을 직접 실행할 수 없습니다. 다음 방법 중 하나를 사용하세요:

### 방법 1: Git Bash 사용 (권장)

1. **파일 탐색기 사용**
   - 파일 탐색기에서 `deploy` 폴더를 엽니다
   - 우클릭 → "Git Bash Here" 선택
   - 터미널에서 스크립트 실행:
   ```bash
   ./aws-ec2-setup.sh
   ```

2. **VS Code 사용**
   - VS Code에서 터미널 메뉴 선택
   - "새 터미널" → 터미널 오른쪽 상단의 "새 터미널" 드롭다운
   - "Git Bash" 선택
   - 스크립트 실행:
   ```bash
   cd deploy
   chmod +x *.sh
   ./aws-ec2-setup.sh
   ```

### 방법 2: WSL 사용

WSL(Windows Subsystem for Linux)이 설치되어 있는 경우:
```powershell
cd deploy
wsl bash ./aws-ec2-setup.sh
```

### 방법 3: Git Bash 직접 실행

Git Bash가 설치되어 있다면:
```powershell
"C:\Program Files\Git\bin\bash.exe" ./aws-ec2-setup.sh
```

### Git 설치 확인

Git Bash가 설치되어 있지 않은 경우:
```powershell
# 설치 확인
where.exe git-bash
```

설치되지 않았다면 [Git for Windows](https://git-scm.com/downloads)를 다운로드하여 설치하세요.

## 설정 파일 상세 설명

### 필수 설정

- `PROJECT_NAME`: 프로젝트명 (소문자, 하이픈 사용)
- `PROJECT_DISPLAY_NAME`: 표시용 프로젝트명
- `AWS_ACCOUNT_ID`: AWS 계정 ID
- `AWS_ACCESS_KEY_ID`: AWS 액세스 키 ID
- `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 액세스 키
- `GITHUB_REPO_URL`: GitHub 저장소 URL
- `KIS_APP_KEY`: KIS 디벨로퍼스에서 발급받은 app_key
- `KIS_APP_SECRET`: KIS 디벨로퍼스에서 발급받은 app_secret
- `KIS_ACCOUNT_NO`: 계좌번호
- `KIS_ACCOUNT_PRODUCT_CD`: 계좌 상품 코드 (01: 실거래, 02: 모의투자)
- `KIS_BASE_URL`: KIS API Base URL

### 선택적 설정

- `INSTANCE_TYPE`: EC2 인스턴스 타입 (기본값: t3.medium)
- `EBS_VOLUME_SIZE`: EBS 볼륨 크기 (기본값: 30GB)
- `REQUIRED_PORTS`: 필요한 포트 목록
- `DOMAIN_NAME`: 도메인명 (있는 경우)
- `USE_MOCK_DATA`: Mock 데이터 사용 여부 (기본값: False)

## 지원하는 서비스

- **웹 서버**: Nginx
- **백엔드**: FastAPI (Python)
- **데이터베이스**: SQLite (개발), PostgreSQL (운영)
- **프론트엔드**: React + TypeScript + Vite
- **컨테이너**: Docker, Docker Compose

## 보안 그룹 포트

기본적으로 다음 포트들이 열립니다:

- 22: SSH
- 80: HTTP
- 443: HTTPS
- 8000: FastAPI 백엔드 서버

## 주의사항

1. **보안**: AWS 자격 증명을 안전하게 보관하세요
2. **비용**: EC2 인스턴스 사용에 따른 비용이 발생합니다
3. **리전**: 기본적으로 서울 리전(ap-northeast-2)을 사용합니다
4. **GitHub 토큰**: Private 저장소의 경우 Personal Access Token이 필요합니다

## 문제 해결

### Windows에서 스크립트가 실행되지 않음
- PowerShell에서는 `.sh` 파일을 직접 실행할 수 없습니다
- Git Bash 또는 WSL을 사용하세요
- 참고: [Windows 환경에서의 실행 방법](#windows-환경에서의-실행-방법)

### AWS CLI 설치 오류
```bash
pip install awscli
```

### AWS 자격 증명 설정
```bash
aws configure
```
또는 `config.sh`에 직접 입력한 후:
```bash
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

### 권한 오류
Linux/Mac:
```bash
chmod +x *.sh
```
Windows (Git Bash):
```bash
chmod +x *.sh
```

### 연결 오류
- EC2 인스턴스가 실행 중인지 확인
- 보안 그룹에서 SSH 포트(22)가 열려있는지 확인
- 키 파일 권한이 올바른지 확인 (400)
- Elastic IP가 할당되었는지 확인

## 라이선스

이 템플릿은 MIT 라이선스 하에 제공됩니다.
