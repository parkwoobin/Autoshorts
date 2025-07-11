"""
ElevenLabs TTS와 비디오 합치기 테스트
"""
import asyncio
import os
from video_merger import VideoTransitionMerger
from tts_utils import create_tts_audio, get_elevenlabs_api_key, list_available_voices

async def test_basic_tts():
    """기본 TTS 생성 테스트"""
    print("🎙️ 기본 TTS 생성 테스트 시작...")
    
    api_key = get_elevenlabs_api_key()
    if not api_key:
        print("❌ ElevenLabs API 키가 설정되지 않았습니다.")
        return
    
    # 테스트 텍스트
    test_text = "안녕하세요! 이것은 ElevenLabs TTS 테스트입니다. 한국어와 영어를 모두 지원합니다."
    
    try:
        result = await create_tts_audio(
            text=test_text,
            api_key=api_key
        )
        
        if result.success:
            print(f"✅ TTS 생성 성공!")
            print(f"   파일: {result.audio_file_path}")
            print(f"   크기: {result.file_size:,} bytes")
            if result.duration:
                print(f"   길이: {result.duration:.2f}초")
        else:
            print(f"❌ TTS 생성 실패: {result.error}")
            
    except Exception as e:
        print(f"❌ TTS 테스트 실패: {e}")

async def test_video_with_tts():
    """비디오에 TTS 추가 테스트"""
    print("\n🎬 비디오에 TTS 추가 테스트 시작...")
    
    api_key = get_elevenlabs_api_key()
    if not api_key:
        print("❌ ElevenLabs API 키가 설정되지 않았습니다.")
        return
    
    # 테스트용 비디오 URL (Runway에서 생성된 샘플)
    test_video_url = "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A"
    
    # 테스트 텍스트 (비디오 내용에 맞춰)
    test_text = "이 영상은 AI가 생성한 놀라운 장면입니다. 최신 기술의 발전을 보여주는 멋진 예시입니다."
    
    try:
        # VideoTransitionMerger 인스턴스 생성
        merger = VideoTransitionMerger(use_static_dir=True)
        
        # 비디오 다운로드
        print("📥 테스트 비디오 다운로드 중...")
        video_path = merger._download_video(test_video_url, "test_video.mp4")
        
        # TTS 추가
        print("🎙️ 비디오에 TTS 추가 중...")
        result_video_path = await merger.add_tts_to_video(
            video_path=video_path,
            text=test_text,
            tts_volume=0.9,  # TTS 볼륨 높게
            video_volume=0.2,  # 원본 비디오 볼륨 낮게
            api_key=api_key
        )
        
        print(f"✅ TTS가 추가된 비디오 생성 완료!")
        print(f"   파일: {result_video_path}")
        
        # 웹에서 접근 가능한 URL 생성
        result_url = merger.get_video_url(os.path.basename(result_video_path))
        print(f"   URL: {result_url}")
        
    except Exception as e:
        print(f"❌ 비디오 TTS 테스트 실패: {e}")

async def test_multiple_videos_with_tts():
    """여러 비디오에 TTS 추가 후 합치기 테스트"""
    print("\n🎬 여러 비디오 TTS 합치기 테스트 시작...")
    
    api_key = get_elevenlabs_api_key()
    if not api_key:
        print("❌ ElevenLabs API 키가 설정되지 않았습니다.")
        return
    
    # 테스트용 비디오 URL들
    test_video_urls = [
        "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
        "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4"
    ]
    
    # 각 비디오에 대응하는 텍스트
    test_texts = [
        "첫 번째 장면입니다. AI가 만든 놀라운 영상을 보고 계십니다.",
        "두 번째 장면으로 넘어갑니다. 기술의 발전이 정말 놀랍습니다."
    ]
    
    try:
        # VideoTransitionMerger 인스턴스 생성
        merger = VideoTransitionMerger(use_static_dir=True)
        
        # 여러 비디오에 TTS 추가 후 합치기
        print("🔗 여러 비디오에 TTS 추가 후 합치는 중...")
        result_video_path = await merger.merge_videos_with_tts(
            video_urls=test_video_urls,
            text_list=test_texts,
            transition_type="fade",
            tts_volume=0.8,
            video_volume=0.3,
            api_key=api_key
        )
        
        print(f"✅ TTS가 추가된 여러 비디오 합치기 완료!")
        print(f"   파일: {result_video_path}")
        
        # 웹에서 접근 가능한 URL 생성
        result_url = merger.get_video_url(os.path.basename(result_video_path))
        print(f"   URL: {result_url}")
        
    except Exception as e:
        print(f"❌ 여러 비디오 TTS 합치기 테스트 실패: {e}")

async def main():
    """메인 테스트 함수"""
    print("🎙️ ElevenLabs TTS + 비디오 합치기 테스트 시작\n")
    
    # 사용 가능한 음성 목록 출력
    list_available_voices()
    print()
    
    # 테스트 실행
    await test_basic_tts()
    await test_video_with_tts()
    await test_multiple_videos_with_tts()
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
