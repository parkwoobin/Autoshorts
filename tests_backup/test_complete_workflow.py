"""
완전한 비디오 제작 워크플로우 테스트
스토리보드 → Runway 영상 → TTS → 자막 → 최종 영상
"""
import asyncio
import json
from models import StoryboardOutput, SceneImagePrompt, ReferenceImage
from complete_video_workflow import create_complete_video, create_video_workflow

async def test_complete_workflow():
    """완전한 워크플로우 테스트"""
    print("🎬 완전한 비디오 제작 워크플로우 테스트 시작")
    
    # 테스트용 스토리보드 생성
    test_scenes = [
        SceneImagePrompt(
            model="gen4_image",
            prompt_text="A modern cafe interior with warm lighting and cozy atmosphere",
            ratio="1280:720",
            seed=42
        ),
        SceneImagePrompt(
            model="gen4_image", 
            prompt_text="Close-up of a delicious coffee cup with steam rising",
            ratio="1280:720",
            seed=43
        ),
        SceneImagePrompt(
            model="gen4_image",
            prompt_text="Happy customer enjoying coffee with a smile",
            ratio="1280:720", 
            seed=44
        )
    ]
    
    test_storyboard = StoryboardOutput(
        scenes=test_scenes,
        total_scenes=3,
        estimated_duration=15,
        video_concept="따뜻하고 아늑한 카페의 분위기를 담은 커피 광고"
    )
    
    # 테스트용 TTS 스크립트
    test_tts_scripts = [
        "안녕하세요! 따뜻한 커피 한 잔으로 하루를 시작해보세요.",
        "우리 카페의 특별한 커피를 만나보세요.",
        "지금 바로 방문해서 맛있는 커피를 즐겨보세요!"
    ]
    
    try:
        # 완전한 워크플로우 실행
        result = await create_complete_video(
            storyboard=test_storyboard,
            tts_scripts=test_tts_scripts,
            voice_gender="female",
            voice_language="ko",
            transition_type="fade",
            add_subtitles=True
        )
        
        if result["success"]:
            print(f"\n✅ 완전한 비디오 제작 워크플로우 성공!")
            print(f"   최종 영상: {result['final_video_url']}")
            print(f"   컨셉: {result['video_concept']}")
            print(f"   장면 수: {result['total_scenes']}")
            print(f"   사용된 음성: {result['voice_used']}")
            print(f"   자막 포함: {result['has_subtitles']}")
            print(f"   처리 요약: {json.dumps(result['processing_summary'], indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 워크플로우 실패: {result['error']}")
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")

async def test_workflow_status():
    """워크플로우 상태 테스트"""
    print("\n📊 워크플로우 상태 확인 테스트")
    
    try:
        workflow = create_video_workflow()
        status = workflow.get_workflow_status()
        
        print("✅ 워크플로우 상태:")
        print(f"   API 키 상태: {status['api_keys_status']}")
        print(f"   임시 디렉토리: {status['temp_dir']}")
        print(f"   사용 가능한 음성: {status['available_voices']}개")
        print(f"   지원 언어: {status['supported_languages']}")
        
    except Exception as e:
        print(f"❌ 상태 확인 실패: {e}")

async def test_api_keys():
    """API 키 확인 테스트"""
    print("\n🔑 API 키 확인 테스트")
    
    from subtitle_utils import get_api_keys
    
    api_keys = get_api_keys()
    
    print("API 키 상태:")
    for key_name, key_value in api_keys.items():
        status = "✅ 설정됨" if key_value else "❌ 없음"
        print(f"   {key_name}: {status}")

async def main():
    """메인 테스트 함수"""
    print("🧪 완전한 비디오 제작 워크플로우 통합 테스트\n")
    
    # API 키 확인
    await test_api_keys()
    
    # 워크플로우 상태 확인
    await test_workflow_status()
    
    # 실제 워크플로우 테스트 (API 키가 모두 있는 경우에만)
    from subtitle_utils import get_api_keys
    api_keys = get_api_keys()
    
    if all(api_keys.values()):
        print("\n🚀 모든 API 키가 설정되어 있어 완전한 워크플로우를 테스트합니다...")
        await test_complete_workflow()
    else:
        print("\n⚠️ 일부 API 키가 누락되어 완전한 워크플로우 테스트를 건너뜁니다.")
        print("   필요한 API 키: ElevenLabs, OpenAI, Runway")
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
