"""
완전한 비디오 워크플로우 사용 예시 데모
workflows.py를 건들지 않고 통합된 시스템의 실제 사용법
"""
import asyncio
import json
import httpx
from typing import Dict, Any

class WorkflowDemo:
    """워크플로우 데모 클래스"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
    
    def create_sample_storyboard_request(self) -> Dict[str, Any]:
        """샘플 스토리보드 요청 생성"""
        return {
            "storyboard": {
                "scenes": [
                    {
                        "model": "gen4_image",
                        "prompt_text": "Modern Korean coffee shop interior with warm wooden furniture and soft lighting, cozy atmosphere, customers working on laptops",
                        "ratio": "1280:720",
                        "seed": 42
                    },
                    {
                        "model": "gen4_image",
                        "prompt_text": "Close-up shot of a skilled barista making coffee, steam rising from espresso machine, professional coffee preparation",
                        "ratio": "1280:720",
                        "seed": 43
                    },
                    {
                        "model": "gen4_image",
                        "prompt_text": "Happy young Korean woman enjoying coffee, smiling while holding a warm cup, peaceful expression",
                        "ratio": "1280:720",
                        "seed": 44
                    }
                ],
                "total_scenes": 3,
                "estimated_duration": 15,
                "video_concept": "프리미엄 카페의 따뜻한 분위기와 품질을 강조한 감성적인 커피 광고"
            },
            "tts_scripts": [
                "바쁜 일상 속에서도 잠시 멈춰 서서 따뜻한 커피 한 잔의 여유를 즐겨보세요.",
                "숙련된 바리스타가 정성스럽게 내려주는 프리미엄 커피를 만나보세요.",
                "오늘도 좋은 하루, 우리 카페에서 특별한 시간을 만들어가세요."
            ],
            "voice_gender": "female",
            "voice_language": "ko",
            "transition_type": "fade",
            "add_subtitles": True
        }
    
    def create_english_sample_request(self) -> Dict[str, Any]:
        """영어 샘플 요청 생성"""
        return {
            "storyboard": {
                "scenes": [
                    {
                        "model": "gen4_image",
                        "prompt_text": "Luxurious tech startup office space with modern design, glass walls, creative team working collaboratively",
                        "ratio": "1280:720",
                        "seed": 100
                    },
                    {
                        "model": "gen4_image",
                        "prompt_text": "Professional software developer coding on multiple monitors, focused concentration, modern workspace",
                        "ratio": "1280:720",
                        "seed": 101
                    }
                ],
                "total_scenes": 2,
                "estimated_duration": 10,
                "video_concept": "Innovative technology solutions for modern businesses"
            },
            "tts_scripts": [
                "Transform your business with cutting-edge technology solutions.",
                "Join the future of innovation today."
            ],
            "voice_gender": "male",
            "voice_language": "en",
            "transition_type": "slide",
            "add_subtitles": True
        }
    
    async def demonstrate_api_usage(self):
        """API 사용법 데모"""
        print("🎬 완전한 비디오 워크플로우 API 사용 데모")
        print("=" * 60)
        
        # 1. 서버 상태 확인
        print("\n1️⃣ 서버 상태 확인")
        print("-" * 30)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/video/status")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 서버 상태: {data['status']}")
                    print(f"📋 사용 가능한 엔드포인트:")
                    for endpoint, description in data['available_endpoints'].items():
                        print(f"   - {endpoint}: {description}")
                else:
                    print(f"❌ 서버 연결 실패: {response.status_code}")
                    return
            except Exception as e:
                print(f"❌ 서버 연결 오류: {e}")
                return
        
        # 2. TTS 음성 목록 확인
        print("\n2️⃣ TTS 음성 목록 확인")
        print("-" * 30)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/tts/voices")
                if response.status_code == 200:
                    data = response.json()
                    voices = data.get('basic_voices', {})
                    print(f"✅ 사용 가능한 음성: {len(voices)}개")
                    print(f"🎤 기본 음성: {data.get('default_voice', 'N/A')}")
                    
                    # 음성 목록 일부 출력
                    print("📋 주요 음성 목록:")
                    for voice_id, voice_name in list(voices.items())[:5]:
                        print(f"   - {voice_id}: {voice_name}")
                    if len(voices) > 5:
                        print(f"   ... 그 외 {len(voices) - 5}개 음성")
                else:
                    print(f"❌ TTS 음성 조회 실패: {response.status_code}")
            except Exception as e:
                print(f"❌ TTS 음성 조회 오류: {e}")
        
        # 3. 워크플로우 상태 확인
        print("\n3️⃣ 워크플로우 상태 확인")
        print("-" * 30)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/video/workflow/status")
                if response.status_code == 200:
                    data = response.json()
                    workflow_status = data.get('workflow_status', {})
                    api_keys = workflow_status.get('api_keys_status', {})
                    
                    print(f"✅ 워크플로우 준비 상태:")
                    print(f"🔑 API 키 상태:")
                    for key, status in api_keys.items():
                        emoji = "✅" if status else "❌"
                        print(f"   {emoji} {key}: {'설정됨' if status else '없음'}")
                    
                    print(f"📁 작업 디렉토리: {workflow_status.get('temp_dir', 'N/A')}")
                    print(f"🎭 지원 언어: {', '.join(workflow_status.get('supported_languages', []))}")
                else:
                    print(f"❌ 워크플로우 상태 확인 실패: {response.status_code}")
            except Exception as e:
                print(f"❌ 워크플로우 상태 확인 오류: {e}")
        
        # 4. 실제 요청 예시 보여주기
        print("\n4️⃣ 실제 워크플로우 요청 예시")
        print("-" * 30)
        
        # 한국어 샘플 요청
        korean_request = self.create_sample_storyboard_request()
        print("📋 한국어 카페 광고 요청 예시:")
        print(json.dumps(korean_request, indent=2, ensure_ascii=False))
        
        # 영어 샘플 요청
        english_request = self.create_english_sample_request()
        print("\n📋 영어 기술 광고 요청 예시:")
        print(json.dumps(english_request, indent=2, ensure_ascii=False))
        
        # 5. 사용 방법 안내
        print("\n5️⃣ 실제 사용 방법")
        print("-" * 30)
        print("🚀 완전한 워크플로우 실행 방법:")
        print(f"   1. 서버 실행: python video_server.py")
        print(f"   2. API 호출: POST {self.base_url}/video/create-complete")
        print(f"   3. 요청 데이터: 위 예시와 같은 JSON 형식")
        print(f"   4. 응답: 최종 광고 영상 URL과 처리 정보")
        
        print("\n📝 curl 명령어 예시:")
        print(f"curl -X POST {self.base_url}/video/create-complete \\")
        print("  -H 'Content-Type: application/json' \\")
        print("  -d @korean_cafe_ad.json")
        
        print("\n🐍 Python 코드 예시:")
        print("""
import asyncio
import httpx

async def create_video():
    request_data = {
        "storyboard": {
            "scenes": [...],  # 장면 정보
            "total_scenes": 3,
            "estimated_duration": 15,
            "video_concept": "광고 컨셉"
        },
        "tts_scripts": ["음성 스크립트1", "음성 스크립트2"],
        "voice_gender": "female",
        "voice_language": "ko",
        "transition_type": "fade",
        "add_subtitles": True
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://127.0.0.1:8001/video/create-complete",
            json=request_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 성공! 최종 영상: {result['final_video_url']}")
        else:
            print(f"❌ 실패: {response.status_code}")

asyncio.run(create_video())
""")
        
        print("\n🎉 데모 완료!")
        print("이제 workflows.py를 건들지 않고도 완전한 비디오 제작이 가능합니다!")

async def main():
    """메인 데모 함수"""
    demo = WorkflowDemo()
    await demo.demonstrate_api_usage()

if __name__ == "__main__":
    asyncio.run(main())
