"""
API 서버를 통한 완전한 워크플로우 통합 테스트
workflows.py를 건들지 않고 API로만 테스트
"""
import asyncio
import httpx
import json
from typing import Dict, Any

class APIWorkflowTester:
    """API를 통한 워크플로우 테스트 클래스"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        
    async def test_server_status(self) -> bool:
        """서버 상태 확인"""
        print("🔍 서버 상태 확인 중...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/video/status")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 서버 정상 작동: {data['status']}")
                    print(f"   사용 가능한 엔드포인트: {len(data['available_endpoints'])}개")
                    return True
                else:
                    print(f"❌ 서버 응답 오류: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ 서버 연결 실패: {e}")
                return False
    
    async def test_tts_voices(self) -> bool:
        """TTS 음성 목록 확인"""
        print("\n🎙️ TTS 음성 목록 확인 중...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/tts/voices")
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        basic_voices = data.get('basic_voices', {})
                        print(f"✅ 사용 가능한 TTS 음성: {len(basic_voices)}개")
                        print(f"   기본 음성: {data.get('default_voice', 'N/A')}")
                        return True
                    else:
                        print(f"❌ TTS 음성 조회 실패: {data.get('message', 'Unknown error')}")
                        return False
                else:
                    print(f"❌ TTS 음성 조회 실패: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ TTS 음성 조회 오류: {e}")
                return False
    
    async def test_workflow_health(self) -> bool:
        """워크플로우 건강 상태 확인"""
        print("\n💊 워크플로우 건강 상태 확인 중...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/video/workflow/status")
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        workflow_status = data.get('workflow_status', {})
                        print(f"✅ 워크플로우 상태: healthy")
                        print(f"   상세 정보: {workflow_status}")
                        return True
                    else:
                        print(f"❌ 워크플로우 상태 확인 실패: {data.get('message', 'Unknown error')}")
                        return False
                else:
                    print(f"❌ 워크플로우 상태 확인 실패: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ 워크플로우 상태 확인 오류: {e}")
                return False
    
    async def create_test_storyboard_request(self) -> Dict[str, Any]:
        """테스트용 스토리보드 요청 생성"""
        return {
            "target_customer": {
                "country": "대한민국",
                "gender": "여성",
                "age_range": ["25-34"],
                "interests": ["커피", "카페", "힐링"],
                "pain_points": ["스트레스", "피로"],
                "preferred_tone": "따뜻하고 친근한"
            },
            "product_description": "프리미엄 원두로 만든 특별한 커피",
            "key_message": "바쁜 일상 속 따뜻한 휴식",
            "reference_images": [
                {
                    "url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085",
                    "description": "아늑한 카페 인테리어"
                }
            ],
            "video_concept": "따뜻하고 감성적인 커피 광고"
        }
    
    async def test_complete_workflow_api(self) -> bool:
        """완전한 워크플로우 API 테스트"""
        print("\n🎬 완전한 워크플로우 API 테스트 시작...")
        
        # 테스트 요청 데이터 생성 (올바른 형식)
        request_data = {
            "storyboard": {
                "scenes": [
                    {
                        "model": "gen4_image",
                        "prompt_text": "A modern coffee shop interior with warm lighting",
                        "ratio": "1280:720",
                        "seed": 42
                    },
                    {
                        "model": "gen4_image", 
                        "prompt_text": "Close-up of a steaming coffee cup",
                        "ratio": "1280:720",
                        "seed": 43
                    },
                    {
                        "model": "gen4_image",
                        "prompt_text": "Happy customer enjoying coffee",
                        "ratio": "1280:720",
                        "seed": 44
                    }
                ],
                "total_scenes": 3,
                "estimated_duration": 15,
                "video_concept": "따뜻한 커피 광고"
            },
            "tts_scripts": [
                "안녕하세요! 오늘도 좋은 하루 되세요.",
                "특별한 커피로 여러분의 하루를 시작해보세요.",
                "지금 바로 우리 카페를 방문해주세요!"
            ],
            "voice_gender": "female",
            "voice_language": "ko",
            "transition_type": "fade",
            "add_subtitles": True
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5분 타임아웃
            try:
                print("   📤 완전한 워크플로우 요청 전송 중...")
                response = await client.post(
                    f"{self.base_url}/video/create-complete",
                    json=request_data,
                    timeout=300.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 완전한 워크플로우 성공!")
                    print(f"   최종 영상: {data.get('final_video_url', 'N/A')}")
                    print(f"   처리 단계: {data.get('processing_steps', 'N/A')}")
                    print(f"   총 소요 시간: {data.get('total_duration', 'N/A')}")
                    return True
                else:
                    print(f"❌ 워크플로우 실패: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"   오류 내용: {error_data}")
                    except:
                        print(f"   응답 내용: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ 워크플로우 API 호출 오류: {e}")
                return False
    
    async def test_simple_video_merge(self) -> bool:
        """간단한 비디오 합치기 테스트"""
        print("\n🔗 간단한 비디오 합치기 테스트...")
        
        # 테스트용 샘플 비디오 URL들
        test_data = {
            "video_urls": [
                "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
                "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4"
            ],
            "transition_type": "fade",
            "transition_duration": 1.0
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/video/merge-user-videos",
                    json=test_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 비디오 합치기 성공!")
                    print(f"   결과 파일: {data.get('output_filename', 'N/A')}")
                    return True
                else:
                    print(f"❌ 비디오 합치기 실패: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ 비디오 합치기 오류: {e}")
                return False

async def main():
    """메인 테스트 함수"""
    print("🧪 API 서버를 통한 완전한 워크플로우 통합 테스트")
    print("=" * 60)
    
    tester = APIWorkflowTester()
    
    # 1. 서버 상태 확인
    if not await tester.test_server_status():
        print("❌ 서버가 실행되지 않았습니다. 먼저 서버를 시작해주세요.")
        return
    
    # 2. TTS 음성 확인
    await tester.test_tts_voices()
    
    # 3. 워크플로우 건강 상태 확인
    await tester.test_workflow_health()
    
    # 4. 간단한 비디오 합치기 테스트
    await tester.test_simple_video_merge()
    
    # 5. 완전한 워크플로우 테스트 (시간이 오래 걸릴 수 있음)
    print("\n⚠️ 완전한 워크플로우 테스트는 시간이 오래 걸릴 수 있습니다.")
    print("   실제 API 키와 Runway API 호출이 필요합니다.")
    
    user_input = input("완전한 워크플로우를 테스트하시겠습니까? (y/N): ")
    if user_input.lower() == 'y':
        await tester.test_complete_workflow_api()
    else:
        print("완전한 워크플로우 테스트를 건너뜁니다.")
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
