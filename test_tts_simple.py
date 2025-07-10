"""
간단한 TTS 전용 테스트 (비디오 다운로드 없이)
"""
import asyncio
import os
from tts_utils import create_tts_audio, get_elevenlabs_api_key, list_available_voices

async def test_tts_only():
    """TTS 기본 기능만 테스트"""
    print("🎙️ TTS 기본 기능 테스트 시작...")
    
    api_key = get_elevenlabs_api_key()
    if not api_key:
        print("❌ ElevenLabs API 키가 설정되지 않았습니다.")
        return
    
    # 여러 테스트 텍스트
    test_texts = [
        "안녕하세요! 이것은 한국어 TTS 테스트입니다.",
        "Hello! This is an English TTS test.",
        "AI가 생성한 놀라운 영상을 소개합니다. 최신 기술의 발전을 확인해보세요.",
        "Welcome to our amazing AI-generated video showcase. Experience the future of content creation."
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n🎙️ 테스트 {i}/{len(test_texts)}")
        try:
            result = await create_tts_audio(
                text=text,
                api_key=api_key,
                output_dir="./static/audio"  # static 폴더에 저장
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

async def test_different_voices():
    """다양한 음성으로 TTS 테스트"""
    print("\n🎭 다양한 음성으로 TTS 테스트...")
    
    api_key = get_elevenlabs_api_key()
    if not api_key:
        print("❌ ElevenLabs API 키가 설정되지 않았습니다.")
        return
    
    from tts_utils import TTSConfig
    
    test_text = "안녕하세요! 저는 AI 음성입니다. 다양한 목소리로 말할 수 있어요."
    
    # 몇 가지 음성으로 테스트
    test_voices = [
        ("21m00Tcm4TlvDq8ikWAM", "Rachel (여성, 영어)"),
        ("ErXwobaYiN019PkySvjV", "Antoni (남성, 영어)"),
        ("TxGEqnHWrfWFTfGW9XjX", "Josh (남성, 영어)")
    ]
    
    for voice_id, voice_name in test_voices:
        print(f"\n🎙️ 음성 테스트: {voice_name}")
        try:
            result = await create_tts_audio(
                text=test_text,
                voice_id=voice_id,
                api_key=api_key,
                output_dir="./static/audio"
            )
            
            if result.success:
                filename = os.path.basename(result.audio_file_path)
                print(f"✅ {voice_name} 음성 생성 완료: {filename}")
            else:
                print(f"❌ {voice_name} 음성 생성 실패: {result.error}")
                
        except Exception as e:
            print(f"❌ {voice_name} 테스트 실패: {e}")

async def main():
    """메인 테스트 함수"""
    print("🎙️ ElevenLabs TTS 전용 테스트 시작\n")
    
    # 사용 가능한 음성 목록 출력
    list_available_voices()
    
    # 테스트 실행
    await test_tts_only()
    await test_different_voices()
    
    print("\n🎉 TTS 테스트 완료!")
    print("📁 생성된 오디오 파일들은 ./static/audio 폴더에서 확인할 수 있습니다.")

if __name__ == "__main__":
    asyncio.run(main())
