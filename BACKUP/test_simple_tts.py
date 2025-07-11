"""
TTS만 단순 테스트
"""
import asyncio
import os
from tts_utils import create_tts_audio, get_elevenlabs_api_key

async def test_simple_tts():
    """단순 TTS 테스트"""
    print("🎤 단순 TTS 테스트 시작...")
    
    # API 키 확인
    api_key = get_elevenlabs_api_key()
    if not api_key:
        print("❌ ElevenLabs API 키가 없습니다!")
        return
    
    print(f"✅ API 키 확인됨: {api_key[:20]}...")
    
    # 간단한 텍스트로 TTS 생성
    test_text = "안녕하세요. TTS 테스트입니다."
    
    print(f"🎙️ TTS 생성 중...")
    print(f"   텍스트: {test_text}")
    
    try:
        result = await create_tts_audio(
            text=test_text,
            voice_id="21m00Tcm4TlvDq8ikWAM",  # 기본 음성
            api_key=api_key,
            output_dir="./static/audio"
        )
        
        if result.success:
            print(f"✅ TTS 생성 성공!")
            print(f"   파일: {result.audio_file_path}")
            print(f"   크기: {os.path.getsize(result.audio_file_path):,} bytes")
            print(f"   길이: {result.duration:.2f}초")
        else:
            print(f"❌ TTS 생성 실패: {result.error}")
    
    except Exception as e:
        print(f"❌ TTS 오류: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_tts())
