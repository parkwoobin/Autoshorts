"""
SUNO API를 이용한 BGM 생성 (실제 엔드포인트 사용)
키워드: happy (밴드 음원)
"""
import os
import httpx
import asyncio
import time
import json
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

async def generate_suno_bgm_real(keyword: str = "happy", duration: int = 60):
    """실제 SUNO API를 사용한 BGM 생성"""
    print(f"🎵 SUNO API(실제)를 이용한 '{keyword}' 키워드 밴드 BGM 생성 시작!")
    print("=" * 60)
    
    api_key = os.getenv('SUNO_API_KEY')
    if not api_key:
        print("❌ SUNO_API_KEY가 설정되지 않았습니다.")
        return {"success": False, "error": "API Key not found"}
    
    print(f"🔑 SUNO API Key: {api_key[:10]}...")
    
    # 실제 SUNO API 엔드포인트
    api_endpoint = "https://api.sunoapi.org/api/v1/generate"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # 먼저 Custom Mode로 시도
        print(f"\n🎸 SUNO API 엔드포인트: {api_endpoint}")
        print(f"🎵 Custom Mode로 '{keyword}' 밴드 BGM 생성 시도...")
        
        custom_payload = {
            "prompt": f"{keyword} upbeat band music with energetic guitar riffs, uplifting drums, positive vibes",
            "style": f"{keyword} rock band",
            "title": f"Happy {keyword.title()} Band Music",
            "customMode": True,
            "instrumental": True,
            "model": "V4",
            "callBackUrl": "https://api.example.com/callback"  # 콜백 URL 추가
        }
        
        print(f"   📋 페이로드: {json.dumps(custom_payload, indent=2)}")
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(api_endpoint, headers=headers, json=custom_payload)
            
            print(f"   📡 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUNO BGM 생성 요청 성공!")
                print(f"   응답: {json.dumps(data, indent=2)}")
                
                if "data" in data and data["data"] is not None and "taskId" in data["data"]:
                    task_id = data["data"]["taskId"]
                    print(f"   🎯 태스크 ID: {task_id}")
                    print(f"   ⏳ 음악 생성 중... (2-3분 소요)")
                    
                    return {
                        "success": True,
                        "keyword": keyword,
                        "task_id": task_id,
                        "audio_filename": f"suno_bgm_{keyword}_{task_id}.mp3",
                        "duration": duration,
                        "type": "SUNO Band BGM",
                        "style": f"{keyword} rock band",
                        "message": f"SUNO API로 '{keyword}' BGM 생성 요청 성공! 태스크 ID: {task_id}",
                        "endpoint": api_endpoint
                    }
                else:
                    print(f"   ❌ 태스크 ID를 찾을 수 없음")
                    print(f"   전체 응답: {data}")
            
            elif response.status_code == 401:
                print(f"   ❌ 인증 실패 (401): API 키가 잘못되었거나 만료됨")
                error_text = response.text
                print(f"   오류 상세: {error_text}")
                
                return {
                    "success": False,
                    "keyword": keyword,
                    "type": "SUNO Band BGM",
                    "error": "API 키 인증 실패",
                    "details": error_text
                }
            
            elif response.status_code == 400:
                print(f"   ❌ 잘못된 요청 (400): 파라미터 오류")
                error_text = response.text
                print(f"   오류 상세: {error_text}")
                
                # Non-custom 모드로 재시도
                print(f"\n🔄 Non-custom 모드로 재시도...")
                
                simple_payload = {
                    "prompt": f"{keyword} rock band music, instrumental, upbeat, positive energy",
                    "customMode": False,
                    "instrumental": True,
                    "callBackUrl": "https://api.example.com/callback"
                }
                
                print(f"   📋 간단한 페이로드: {json.dumps(simple_payload, indent=2)}")
                
                simple_response = await client.post(api_endpoint, headers=headers, json=simple_payload)
                print(f"   📡 간단한 요청 응답: {simple_response.status_code}")
                
                if simple_response.status_code == 200:
                    simple_data = simple_response.json()
                    print(f"   ✅ Non-custom 모드 성공!")
                    print(f"   응답: {json.dumps(simple_data, indent=2)}")
                    
                    if "data" in simple_data and "taskId" in simple_data["data"]:
                        task_id = simple_data["data"]["taskId"]
                        
                        return {
                            "success": True,
                            "keyword": keyword,
                            "task_id": task_id,
                            "audio_filename": f"suno_bgm_{keyword}_{task_id}.mp3",
                            "duration": duration,
                            "type": "SUNO Band BGM (Non-custom)",
                            "style": f"{keyword} rock band",
                            "message": f"SUNO API Non-custom 모드로 '{keyword}' BGM 생성 성공! 태스크 ID: {task_id}",
                            "endpoint": api_endpoint
                        }
                else:
                    simple_error = simple_response.text
                    print(f"   ❌ Non-custom 모드도 실패: {simple_error}")
                    
                    return {
                        "success": False,
                        "keyword": keyword,
                        "type": "SUNO Band BGM",
                        "error": "Custom과 Non-custom 모드 모두 실패",
                        "custom_error": error_text,
                        "simple_error": simple_error
                    }
            
            elif response.status_code == 429:
                print(f"   ❌ 요청 한도 초과 (429): 20 requests per 10 seconds")
                error_text = response.text
                print(f"   오류 상세: {error_text}")
                
                return {
                    "success": False,
                    "keyword": keyword,
                    "type": "SUNO Band BGM",
                    "error": "API 요청 한도 초과",
                    "details": error_text
                }
            
            else:
                error_text = response.text
                print(f"   ❌ 예상치 못한 오류 ({response.status_code})")
                print(f"   오류 상세: {error_text}")
                
                return {
                    "success": False,
                    "keyword": keyword,
                    "type": "SUNO Band BGM",
                    "error": f"HTTP {response.status_code} 오류",
                    "details": error_text
                }
        
    except Exception as e:
        print(f"❌ SUNO BGM 생성 중 예외 발생: {e}")
        return {
            "success": False,
            "keyword": keyword,
            "type": "SUNO Band BGM",
            "error": f"예외 발생: {str(e)}"
        }

async def main():
    """메인 함수 - SUNO BGM 생성"""
    print("🚀 SUNO API(실제) 'happy' 키워드 밴드 BGM 생성 테스트!")
    
    # happy 키워드로 1분 밴드 BGM 생성
    result = await generate_suno_bgm_real("happy", 60)
    
    if result["success"]:
        print(f"\n🎉 성공! '{result['keyword']}' 키워드 밴드 BGM 생성 요청 완료!")
        print(f"   태스크 ID: {result['task_id']}")
        print(f"   예상 파일: {result['audio_filename']}")
        print(f"   길이: {result['duration']}초")
        print(f"   스타일: {result['style']}")
        print(f"   타입: {result['type']}")
        print(f"   엔드포인트: {result['endpoint']}")
        print(f"   메시지: {result['message']}")
        print(f"\n💡 음악 생성이 완료되면 SUNO 대시보드에서 다운로드할 수 있습니다.")
        print(f"   또는 Get Music Generation Details API로 상태를 확인하세요.")
    else:
        print(f"\n❌ '{result['keyword']}' 키워드 밴드 BGM 생성에 실패했습니다.")
        print(f"   오류: {result.get('error', '알 수 없는 오류')}")
        if "details" in result:
            print(f"   상세: {result['details']}")
        if "custom_error" in result:
            print(f"   Custom 모드 오류: {result['custom_error']}")
        if "simple_error" in result:
            print(f"   Simple 모드 오류: {result['simple_error']}")
        print(f"   타입: {result.get('type', 'SUNO Band BGM')}")

if __name__ == "__main__":
    asyncio.run(main())
