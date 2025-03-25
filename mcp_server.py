from typing import Any, Dict, List, Optional
import requests
from datetime import datetime
import time
import functools
from mcp.server.fastmcp import FastMCP

# 실행 시간 측정 데코레이터
def measure_execution_time(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            print(f"[성능측정] {func.__name__} 실행 시간: {execution_time:.3f}초")
    return wrapper

# Initialize FastMCP server
mcp = FastMCP("roaming")

# API 기본 URL 설정
API_BASE_URL = "https://eippdmnpvr.us-west-2.awsapprunner.com"

@mcp.tool()
@measure_execution_time
async def list_roaming_plans(country: str, duration: int) -> str:
    """국가와 기간에 따른 요금제 리스트를 보여주며 가장 최적의 요금제를 추천합니다.
    
    Args:
        country: 여행할 국가명 (예: 일본, 미국, 프랑스 등)
        duration: 여행 일수
    """
    try:
        # 기간 검증
        if duration <= 0:
            return "여행 기간은 1일 이상이어야 합니다."
            
        # API에서 요금제 목록 조회
        api_start_time = time.time()
        response = requests.get(f"{API_BASE_URL}/roaming/plans")
        api_end_time = time.time()
        print(f"[성능측정] 요금제 목록 API 호출 시간: {api_end_time - api_start_time:.3f}초")
        
        if response.status_code != 200:
            return "요금제 정보 조회 실패"
        
        plans = response.json()
        
        # 국가 지원 여부 확인 및 필터링
        filter_start_time = time.time()
        available_plans = [
            plan for plan in plans 
            if country in plan['supported_countries']
        ]
        filter_end_time = time.time()
        print(f"[성능측정] 요금제 필터링 시간: {filter_end_time - filter_start_time:.3f}초")
        
        if not available_plans:
            return f"죄송합니다. {country}는 현재 서비스가 지원되지 않는 국가입니다."
        
        # 최적 요금제 선택
        select_start_time = time.time()
        recommended_plans = select_best_plan(available_plans, duration)
        select_end_time = time.time()
        print(f"[성능측정] 최적 요금제 선택 시간: {select_end_time - select_start_time:.3f}초")
        
        # 응답 메시지 생성
        format_start_time = time.time()
        message = format_recommendation_message(recommended_plans, country, duration)
        format_end_time = time.time()
        print(f"[성능측정] 응답 메시지 생성 시간: {format_end_time - format_start_time:.3f}초")
        
        return message
        
    except Exception as e:
        return f"요금제 조회 중 오류가 발생했습니다: {str(e)}"

@mcp.tool()
@measure_execution_time
async def get_roaming_usage(phone_number: str) -> str:
    """로밍 이용내역을 조회합니다.
    
    Args:
        phone_number: 고객 전화번호
    """
    try:
        api_start_time = time.time()
        response = requests.get(f"{API_BASE_URL}/roaming/subscription/{phone_number}")
        api_end_time = time.time()
        print(f"[성능측정] 이용내역 API 호출 시간: {api_end_time - api_start_time:.3f}초")
        
        if response.status_code != 200:
            return "이용내역 조회 중 오류가 발생했습니다."
        
        usages = response.json()  # 배열 형태로 응답 받음
        
        if not usages:  # 이용내역이 없는 경우
            return f"로밍 이용내역이 없습니다. (전화번호: {phone_number})"
        
        # 모든 이용내역을 포맷팅하여 표시
        format_start_time = time.time()
        message = f"\n로밍 이용내역 (전화번호: {phone_number})"
        
        for usage in usages:
            subscription_date = datetime.fromisoformat(usage['subscription_date'].replace('Z', '+00:00'))
            start_date = datetime.fromisoformat(usage['start_date'].replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(usage['end_date'].replace('Z', '+00:00'))
            
            message += f"""
\n[{usage['plan_name']}]
• 이용 국가: {usage['roaming_country']}
• 가입일시: {subscription_date.strftime('%Y-%m-%d %H:%M')}
• 시작일시: {start_date.strftime('%Y-%m-%d')} {usage['start_time']} ({usage['time_standard']})
• 종료일시: {end_date.strftime('%Y-%m-%d')}"""
        
        format_end_time = time.time()
        print(f"[성능측정] 이용내역 포맷팅 시간: {format_end_time - format_start_time:.3f}초")
        
        return message

    except Exception as e:
        return f"이용내역 조회 중 오류가 발생했습니다: {str(e)}"

@mcp.tool()
@measure_execution_time
async def subscribe_roaming_plan(phone_number: str, plan_code: str, roaming_country: str, 
                                start_date: str, start_time: str) -> str:
    """해외 로밍 요금제를 가입합니다. 가입자의 전화번호, 요금제 코드, 이용 국가, 시작일시 정보가 필요합니다.
    
    Args:
        phone_number: 가입자 전화번호 (예: 01012345678)
        plan_code: 요금제 코드 (예: ZERO_PREMIUM_001, ZERO_LITE_8GB)
        roaming_country: 로밍 이용 국가 (예: 일본, 미국, 중국)
        start_date: 로밍 시작일 (YYYY-MM-DDT00:00:00 형식)
        start_time: 로밍 시작 시간 (HH:mm 형식)
    """
    try:
        # API 요청 데이터 구성
        request_data = {
            "phone_number": phone_number,
            "plan_code": plan_code,
            "roaming_country": roaming_country,
            "start_date": start_date,
            "start_time": start_time,
            "time_standard": "LOCAL"
        }
        
        # API 호출
        api_start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/roaming/subscribe",
            json=request_data
        )
        api_end_time = time.time()
        print(f"[성능측정] 요금제 가입 API 호출 시간: {api_end_time - api_start_time:.3f}초")
        
        if response.status_code != 200:
            return "요금제 가입 중 오류가 발생했습니다."
            
        subscription_data = response.json()
        
        format_start_time = time.time()
        result = f"""
로밍 요금제 가입이 완료되었습니다.

[가입 정보]
• 전화번호: {phone_number}
• 요금제: {subscription_data.get('plan_name', '정보 없음')}
• 이용 국가: {roaming_country}
• 시작일: {start_date.split('T')[0]} {start_time}
"""
        format_end_time = time.time()
        print(f"[성능측정] 응답 포맷팅 시간: {format_end_time - format_start_time:.3f}초")
        
        return result
        
    except Exception as e:
        return f"요금제 가입 중 오류가 발생했습니다: {str(e)}"

# 유틸리티 함수들
def select_best_plan(plans: List[Dict[str, Any]], duration: int) -> List[Dict[str, Any]]:
    """최적 요금제 선택"""
    if not plans:
        raise ValueError("해당 지역에 사용 가능한 요금제가 없습니다.")

    duration_hours = duration * 24

    for plan in plans:
        plan_duration_hours = (
            plan['duration'] * 24 if plan['duration_unit'] == 'days'
            else plan['duration'] if plan['duration_unit'] == 'hours'
            else plan['duration'] * 24
        )
        
        purchases_needed = -(-duration_hours // plan_duration_hours)
        total_price = plan['price'] * purchases_needed
        
        plan['total_price'] = total_price
        plan['purchases_needed'] = purchases_needed

    return sorted(plans, key=lambda x: x['total_price'])[:5]

def format_recommendation_message(plans: List[Dict[str, Any]], country: str, duration: int) -> str:
    """추천 요금제 응답 메시지 포맷팅"""
    if not plans:
        return f"{country}에 대한 적합한 요금제를 찾을 수 없습니다."
        
    details = f"\n{country} 여행 {duration}일을 위한 추천 요금제 TOP 5입니다:\n"
    
    for i, plan in enumerate(plans, 1):
        duration_unit_text = "일" if plan['duration_unit'] == 'days' else "시간"
        details += f"""
{i}. [{plan['plan_name']}]
• 이용기간: {plan['duration']}{duration_unit_text}
• 데이터: {plan['data_amount']}
• 음성 수신: {'무료' if plan['voice_incoming_fee'] == 0 else f"{plan['voice_incoming_fee']}원/분"}
• 음성 발신: {'무료' if plan['voice_outgoing_fee'] == 0 else f"{plan['voice_outgoing_fee']}원/분"}
• 1회 이용료: {plan['price']:,}원
• {duration}일 총 요금: {plan['total_price']:,}원 ({plan['purchases_needed']}회 이용)
• 요금제 코드: {plan['plan_code']}
"""
    
    best_plan = plans[0]
    duration_unit_text = "일" if best_plan['duration_unit'] == 'days' else "시간"
    summary = f"{country} {duration}일 여행을 위해 '{best_plan['plan_name']}' 요금제를 추천드립니다. 코드는 {best_plan['plan_code']}입니다."
    summary += f" {best_plan['duration']}{duration_unit_text} 이용권 {best_plan['purchases_needed']}회 사용으로 "
    summary += f"총 {best_plan['total_price']:,}원으로 가장 경제적입니다. "
    
    voice_info = ""
    if best_plan['voice_incoming_fee'] == 0 and best_plan['voice_outgoing_fee'] == 0:
        voice_info += "음성 통화는 수신/발신 모두 무료입니다."
    else:
        if best_plan['voice_incoming_fee'] == 0:
            voice_info += "음성 수신은 무료이며, "
        else:
            voice_info += f"음성 수신은 분당 {best_plan['voice_incoming_fee']}원, "
        if best_plan['voice_outgoing_fee'] == 0:
            voice_info += "발신은 무료입니다."
        else:
            voice_info += f"발신은 분당 {best_plan['voice_outgoing_fee']}원입니다."
    
    return f"{summary}{voice_info}\n\n{details}"

if __name__ == "__main__":
    print("[성능측정] MCP 서버 시작 시간:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    # Initialize and run the server
    mcp.run(transport='stdio') 