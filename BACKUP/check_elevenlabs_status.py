"""
ElevenLabs TTS API 상태 확인 및 테스트 스크립트
"""
import os
import asyncio
import httpx
from dotenv import load_dotenv

async def check_elevenlabs_status():
    """ElevenLabs API 상태 확인"""
    try:
        load_dotenv()
        api_key = os.getenv("ELEVNLABS_API_KEY")
        
        if not api_key:
            print("❌ ElevenLabs API 키를 찾을 수 없습니다.")
            return
        
        print(f"🔑 API 키 확인: {api_key[:10]}...")
        
        # API 키 유효성 확인
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Accept": "application/json",
                "xi-api-key": api_key
            }
            
            print("📊 사용자 정보 조회 중...")
            
            # 사용자 정보 조회
            user_response = await client.get(
                "https://api.elevenlabs.io/v1/user",
                headers=headers
            )
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                print(f"✅ 사용자 정보 조회 성공")
                print(f"   사용자: {user_data.get('first_name', 'Unknown')} {user_data.get('last_name', '')}")
                
                # 구독 정보 확인
                subscription = user_data.get('subscription', {})
                print(f"   구독 티어: {subscription.get('tier', 'Unknown')}")
                print(f"   문자 한도: {subscription.get('character_limit', 'Unknown')}")
                print(f"   사용된 문자: {subscription.get('character_count', 'Unknown')}")
                
                remaining = subscription.get('character_limit', 0) - subscription.get('character_count', 0)
                print(f"   남은 문자: {remaining}")
                
            else:
                print(f"❌ 사용자 정보 조회 실패: {user_response.status_code}")
                print(f"   응답: {user_response.text}")
                return
            
            # 사용 가능한 음성 조회
            print("\n🎙️ 사용 가능한 음성 조회 중...")
            
            voices_response = await client.get(
                "https://api.elevenlabs.io/v1/voices",
                headers=headers
            )
            
            if voices_response.status_code == 200:
                voices_data = voices_response.json()
                voices = voices_data.get('voices', [])
                print(f"✅ 음성 조회 성공: {len(voices)}개 음성 사용 가능")
                
                # 처음 5개 음성 출력
                for i, voice in enumerate(voices[:5]):
                    print(f"   [{i+1}] {voice.get('name', 'Unknown')} - {voice.get('voice_id', 'Unknown')}")
                
            else:
                print(f"❌ 음성 조회 실패: {voices_response.status_code}")
                print(f"   응답: {voices_response.text}")
                return
            
            # 간단한 TTS 테스트
            print("\n🧪 간단한 TTS 테스트 중...")
            
            test_text = "안녕하세요 테스트입니다"
            test_voice_id = voices[0]['voice_id'] if voices else "21m00Tcm4TlvDq8ikWAM"
            
            tts_data = {
                "text": test_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.75
                }
            }
            
            tts_response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{test_voice_id}",
                headers=headers,
                json=tts_data
            )
            
            if tts_response.status_code == 200:
                print("✅ TTS 테스트 성공! API가 정상 작동합니다.")
                
                # 테스트 오디오 파일 저장
                test_audio_path = os.path.join(".", "test_tts.mp3")
                with open(test_audio_path, "wb") as f:
                    f.write(tts_response.content)
                
                print(f"   테스트 오디오 저장: {test_audio_path}")
                print(f"   파일 크기: {len(tts_response.content)} bytes")
                
            else:
                print(f"❌ TTS 테스트 실패: {tts_response.status_code}")
                print(f"   응답: {tts_response.text}")
                
                # 에러 분석
                if tts_response.status_code == 401:
                    print("   → API 키가 유효하지 않거나 만료됨")
                elif tts_response.status_code == 429:
                    print("   → 요청 한도 초과 (Rate Limit)")
                elif tts_response.status_code == 422:
                    print("   → 요청 데이터 형식 오류")
                else:
                    print(f"   → 알 수 없는 오류: {tts_response.status_code}")
        
    except Exception as e:
        print(f"❌ ElevenLabs API 상태 확인 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_elevenlabs_status())
