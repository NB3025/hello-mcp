# client.py
import asyncio
import sys
import time
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import datetime

# to interact with MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# to interact with Amazon Bedrock
import boto3

# client.py
@dataclass
class Message:
    role: str
    content: List[Dict[str, Any]]

    @classmethod
    def user(cls, text: str) -> 'Message':
        return cls(role="user", content=[{"text": text}])

    @classmethod
    def assistant(cls, text: str) -> 'Message':
        return cls(role="assistant", content=[{"text": text}])

    @classmethod
    def tool_result(cls, tool_use_id: str, content: dict) -> 'Message':
        return cls(
            role="user",
            content=[{
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": [{"json": {"text": content[0].text}}]
                }
            }]
        )

    @classmethod
    def tool_request(cls, tool_use_id: str, name: str, input_data: dict) -> 'Message':
        return cls(
            role="assistant",
            content=[{
                "toolUse": {
                    "toolUseId": tool_use_id,
                    "name": name,
                    "input": input_data
                }
            }]
        )

    @staticmethod
    def to_bedrock_format(tools_list: List[Dict]) -> List[Dict]:
        return [{
            "toolSpec": {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": tool["input_schema"]["properties"],
                        "required": tool["input_schema"].get("required", [])
                    }
                }
            }
        } for tool in tools_list]

    
# client.py
class MCPClient:
    MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    # MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-west-2')
        self.timing_stats = {}

    # connect_to_server는 메시지 전달을 위해 표준 입출력을 사용
    async def connect_to_server(self, server_script_path: str):
        start_time = time.time()
        
        if not server_script_path.endswith(('.py', '.js')):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if server_script_path.endswith('.py') else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)

        # exit_stack은 client session의 lifetime을 관리하는데 사용됩니다.
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        response = await self.session.list_tools()
        print("\nConnected to server with tools:", [tool.name for tool in response.tools])
        
        end_time = time.time()
        self.timing_stats["server_connection"] = end_time - start_time
        print(f"서버 연결 시간: {self.timing_stats['server_connection']:.3f}초")

    async def cleanup(self):
        await self.exit_stack.aclose()

    # client.py
    def _make_bedrock_request(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        start_time = time.time()
        
        response = self.bedrock.converse(
            modelId=self.MODEL_ID,
            system=[{"text":"As an agent in charge of roaming-related work for the telecommunications company, you will be responsible for handling customers' roaming-related requests"}],
            messages=messages,
            inferenceConfig={"maxTokens": 2048, "temperature": 0, "topP": 1},
            toolConfig={"tools": tools}
        )
        
        end_time = time.time()
        request_time = end_time - start_time
        
        # 타이밍 통계 업데이트
        if "bedrock_requests" not in self.timing_stats:
            self.timing_stats["bedrock_requests"] = []
        
        self.timing_stats["bedrock_requests"].append(request_time)
        print(f"Bedrock 요청 시간: {request_time:.3f}초")
        
        return response

    async def process_query(self, query: str) -> str:
        total_start_time = time.time()
        
        # 타이밍 통계 초기화
        self.timing_stats = {
            "query_start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bedrock_requests": [],
            "tool_calls": []
        }
        
        print(f"\n쿼리 실행 시작: {self.timing_stats['query_start_time']}")
        
        # (1) 메시지 준비
        messages = [Message.user(query).__dict__]
        
        # (2) 도구 목록 가져오기
        tool_list_start = time.time()
        response = await self.session.list_tools()
        tool_list_end = time.time()
        self.timing_stats["tool_listing"] = tool_list_end - tool_list_start
        print(f"도구 목록 조회 시간: {self.timing_stats['tool_listing']:.3f}초")

        # (3) 도구 변환
        tool_convert_start = time.time()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        bedrock_tools = Message.to_bedrock_format(available_tools)
        tool_convert_end = time.time()
        self.timing_stats["tool_conversion"] = tool_convert_end - tool_convert_start
        print(f"도구 변환 시간: {self.timing_stats['tool_conversion']:.3f}초")

        # (4) 첫 요청
        response = self._make_bedrock_request(messages, bedrock_tools)

        # (6) 응답 처리
        result = await self._process_response(
          response, messages, bedrock_tools
        )
        
        total_end_time = time.time()
        self.timing_stats["total_execution_time"] = total_end_time - total_start_time
        
        # 타이밍 요약 추가
        timing_summary = self._get_timing_summary()
        
        return result + "\n\n" + timing_summary

    # 타이밍 요약 생성
    def _get_timing_summary(self) -> str:
        bedrock_total = sum(self.timing_stats["bedrock_requests"])
        bedrock_avg = bedrock_total / len(self.timing_stats["bedrock_requests"]) if self.timing_stats["bedrock_requests"] else 0
        
        tool_calls_total = sum(call["total"] for call in self.timing_stats["tool_calls"]) if self.timing_stats["tool_calls"] else 0
        tool_calls_avg = tool_calls_total / len(self.timing_stats["tool_calls"]) if self.timing_stats["tool_calls"] else 0
        
        summary = f"\n[실행 시간 측정 결과]"
        summary += f"\n• 쿼리 입력 시간: {self.timing_stats['query_start_time']}"
        summary += f"\n• 총 실행 시간: {self.timing_stats['total_execution_time']:.3f}초"
        summary += f"\n• Bedrock API 호출 횟수: {len(self.timing_stats['bedrock_requests'])}회"
        summary += f"\n• Bedrock API 총 시간: {bedrock_total:.3f}초 (평균: {bedrock_avg:.3f}초)"
        summary += f"\n• 도구 호출 횟수: {len(self.timing_stats['tool_calls'])}회"
        summary += f"\n• 도구 호출 총 시간: {tool_calls_total:.3f}초 (평균: {tool_calls_avg:.3f}초)"
        
        # 개별 도구 호출 시간 세부 정보
        if self.timing_stats["tool_calls"]:
            summary += "\n\n[도구별 호출 시간]"
            for i, call in enumerate(self.timing_stats["tool_calls"], 1):
                summary += f"\n{i}. {call['name']} → {call['total']:.3f}초"
        
        return summary

    # client.py
    async def _process_response(self, response: Dict, messages: List[Dict], bedrock_tools: List[Dict]) -> str:
        # (1)
        final_text = []
        MAX_TURNS=10
        turn_count = 0

        while True:
            # (2)
            if response['stopReason'] == 'tool_use':
                final_text.append("received toolUse request")
                for item in response['output']['message']['content']:
                    if 'text' in item:
                        final_text.append(f"[Thinking: {item['text']}]")
                        messages.append(Message.assistant(item['text']).__dict__)
                    elif 'toolUse' in item:
                        # (3)
                        tool_info = item['toolUse']
                        result = await self._handle_tool_call(tool_info, messages)
                        final_text.extend(result)
                        
                        response = self._make_bedrock_request(messages, bedrock_tools)
            # (4)
            elif response['stopReason'] == 'max_tokens':
                final_text.append("[Max tokens reached, ending conversation.]")
                break
            elif response['stopReason'] == 'stop_sequence':
                final_text.append("[Stop sequence reached, ending conversation.]")
                break
            elif response['stopReason'] == 'content_filtered':
                final_text.append("[Content filtered, ending conversation.]")
                break
            elif response['stopReason'] == 'end_turn':
                final_text.append(response['output']['message']['content'][0]['text'])
                break

            turn_count += 1

            if turn_count >= MAX_TURNS:
                final_text.append("\n[Max turns reached, ending conversation.]")
                break
        # (5)
        return "\n\n".join(final_text)

    # client.py
    async def _handle_tool_call(self, tool_info: Dict, messages: List[Dict]) -> List[str]:
        # 도구 호출 시간 측정 시작
        start_time = time.time()
        
        # (1)
        tool_name = tool_info['name']
        tool_args = tool_info['input']
        tool_use_id = tool_info['toolUseId']

        # (2)
        result = await self.session.call_tool(tool_name, tool_args)

        # (3)
        messages.append(Message.tool_request(tool_use_id, tool_name, tool_args).__dict__)
        messages.append(Message.tool_result(tool_use_id, result.content).__dict__)

        # 도구 호출 시간 측정 종료
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 타이밍 통계에 추가
        self.timing_stats["tool_calls"].append({
            "name": tool_name,
            "args": tool_args,
            "total": execution_time
        })
        
        print(f"도구 호출 {tool_name} 실행 시간: {execution_time:.3f}초")
        
        # (4)
        return [f"[Calling tool {tool_name} with args {tool_args}]"]

    # client.py
    async def chat_loop(self):
        print("\nMCP Client Started!\nType your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                
                query_start_time = time.time()
                print(f"쿼리 처리 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                
                response = await self.process_query(query)
                
                query_end_time = time.time()
                query_total_time = query_end_time - query_start_time
                print(f"\n응답 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                print(f"총 처리 시간: {query_total_time:.3f}초")
                
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")

# client.py
async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())