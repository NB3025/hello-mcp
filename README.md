# MCP 로밍 서비스

MCP(Managed Claude Protocol)를 활용한 로밍 서비스 구현 프로젝트입니다. 이 프로젝트는 로밍 요금제 추천, 이용내역 조회, 요금제 가입 등의 기능을 제공합니다.

## 설치 방법

1. 가상환경 생성 및 활성화
```bash
python3.12 -m venv .venv # 가상환경 생성, 3.12 버전 사용
source .venv/bin/activate  
```

1-1. EC2 에서 Python3.12 버전 설치
```bash
sudo dnf install python3.12
sudo dnf install python3.12-pip
```

2. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

## 실행 방법

MCP 서버와 클라이언트를 실행하려면 다음 명령어를 사용합니다:
```bash
python client.py mcp_server.py
```

## 주요 기능

- `list_roaming_plans`: 국가와 기간에 따른 로밍 요금제 추천
- `get_roaming_usage`: 고객 전화번호로 로밍 이용내역 조회
- `subscribe_roaming_plan`: 로밍 요금제 가입

## 성능 측정

클라이언트와 서버 모두 각 작업의 실행 시간을 측정하여 표시합니다. 쿼리 실행 후 결과와 함께 실행 시간 측정 결과가 표시됩니다.
