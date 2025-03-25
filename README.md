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


## 실행 예시

```bash
$ python client.py mcp_server.py

Connected to server with tools: ['list_roaming_plans', 'get_roaming_usage', 'subscribe_roaming_plan']
서버 연결 시간: 0.443초

MCP Client Started!
Type your queries or 'quit' to exit.

Query: 로밍 요금제 보여줘
쿼리 처리 시작: 2025-03-25 10:55:19.802

쿼리 실행 시작: 2025-03-25 10:55:19
도구 목록 조회 시간: 0.002초
도구 변환 시간: 0.000초
Bedrock 요청 시간: 4.572초

응답 완료: 2025-03-25 10:55:24.376
총 처리 시간: 4.574초

로밍 요금제를 조회하기 위해서는 어느 국가로 여행하시는지와 몇 일 동안 체류하실 예정인지 알아야 합니다.

다음 정보를 알려주시면 최적의 요금제를 추천해드리겠습니다:
1. 여행하실 국가
2. 체류 기간(일수)

예를 들어, "일본으로 5일 동안 여행갈 예정입니다"와 같이 말씀해 주시면 됩니다.


[실행 시간 측정 결과]
• 쿼리 입력 시간: 2025-03-25 10:55:19
• 총 실행 시간: 4.574초
• Bedrock API 호출 횟수: 1회
• Bedrock API 총 시간: 4.572초 (평균: 4.572초)
• 도구 호출 횟수: 0회
• 도구 호출 총 시간: 0.000초 (평균: 0.000초)
```