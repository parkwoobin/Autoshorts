"""
ElevenLabs TTS를 이용한 음성 생성 유틸리티
"""
import asyncio  # 비동기 처리를 위한 모듈
import os  # 환경변수 읽기용
import tempfile  # 임시 파일 생성용
from typing import List, Optional, Dict, Any  # 타입 힌트용
import httpx  # HTTP 클라이언트 라이브러리
from pathlib import Path  # 파일 경로 처리용

class TTSConfig:
    """TTS 관련 설정값들"""
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel 음성 (기본값)
    DEFAULT_MODEL_ID = "eleven_multilingual_v2"  # 다국어 지원 모델
    DEFAULT_STABILITY = 0.5  # 음성 안정성 (0.0-1.0)
    DEFAULT_SIMILARITY_BOOST = 0.8  # 음성 유사도 (0.0-1.0)
    DEFAULT_STYLE = 0.0  # 음성 스타일 (0.0-1.0)
    DEFAULT_USE_SPEAKER_BOOST = True  # 화자 부스트 사용 여부
    
    # 지원되는 음성 목록 (음성 ID와 이름)
    VOICES = {
        "21m00Tcm4TlvDq8ikWAM": "Rachel (여성, 영어)",
        "AZnzlk1XvdvUeBnXmlld": "Domi (여성, 영어)", 
        "EXAVITQu4vr4xnSDxMaL": "Bella (여성, 영어)",
        "ErXwobaYiN019PkySvjV": "Antoni (남성, 영어)",
        "MF3mGyEYCl7XYWbV9V6O": "Elli (여성, 영어)",
        "TxGEqnHWrfWFTfGW9XjX": "Josh (남성, 영어)",
        "VR6AewLTigWG4xSOukaG": "Arnold (남성, 영어)",
        "pNInz6obpgDQGcFmaJgB": "Adam (남성, 영어)",
        "yoZ06aMxZJJ28mfd3POQ": "Sam (남성, 영어)"
    }

class TTSResult:
    """TTS 생성 결과를 담는 데이터 클래스"""
    def __init__(
        self,
        success: bool,
        audio_file_path: Optional[str] = None,
        text: Optional[str] = None,
        voice_id: Optional[str] = None,
        duration: Optional[float] = None,
        file_size: Optional[int] = None,
        error: Optional[str] = None
    ):
        self.success = success  # 생성 성공 여부
        self.audio_file_path = audio_file_path  # 생성된 오디오 파일 경로
        self.text = text  # 변환된 텍스트
        self.voice_id = voice_id  # 사용된 음성 ID
        self.duration = duration  # 오디오 길이 (초)
        self.file_size = file_size  # 파일 크기 (바이트)
        self.error = error  # 에러 메시지 (실패시)

async def get_available_voices(api_key: str) -> Dict[str, Any]:
    """
    ElevenLabs에서 사용 가능한 음성 목록을 가져옴
    
    Args:
        api_key: ElevenLabs API 키
        
    Returns:
        Dict: 음성 목록과 정보
    """
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://api.elevenlabs.io/v1/voices",
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"음성 목록 조회 실패: {response.status_code} - {response.text}")
            
            voices_data = response.json()
            print(f"✅ 사용 가능한 음성 {len(voices_data.get('voices', []))}개 조회 완료")
            
            return voices_data
            
        except Exception as e:
            print(f"❌ 음성 목록 조회 실패: {e}")
            raise

async def create_tts_audio(
    text: str,  # 변환할 텍스트
    voice_id: str = TTSConfig.DEFAULT_VOICE_ID,  # 사용할 음성 ID
    model_id: str = TTSConfig.DEFAULT_MODEL_ID,  # 사용할 모델 ID
    stability: float = TTSConfig.DEFAULT_STABILITY,  # 음성 안정성
    similarity_boost: float = TTSConfig.DEFAULT_SIMILARITY_BOOST,  # 음성 유사도
    style: float = TTSConfig.DEFAULT_STYLE,  # 음성 스타일
    use_speaker_boost: bool = TTSConfig.DEFAULT_USE_SPEAKER_BOOST,  # 화자 부스트
    api_key: str = None,  # ElevenLabs API 키
    output_dir: str = None  # 출력 디렉토리 (None이면 임시 디렉토리 사용)
) -> TTSResult:
    """
    ElevenLabs API를 사용하여 텍스트를 음성으로 변환
    
    Args:
        text: 변환할 텍스트
        voice_id: 사용할 음성 ID (기본값: Rachel)
        model_id: 사용할 모델 ID (기본값: eleven_multilingual_v2)
        stability: 음성 안정성 (0.0-1.0)
        similarity_boost: 음성 유사도 (0.0-1.0)
        style: 음성 스타일 (0.0-1.0)
        use_speaker_boost: 화자 부스트 사용 여부
        api_key: ElevenLabs API 키
        output_dir: 출력 디렉토리
        
    Returns:
        TTSResult: TTS 생성 결과
    """
    if not api_key:  # API 키가 없으면 에러 발생
        return TTSResult(success=False, error="ElevenLabs API 키가 필요합니다.")
    
    if not text or not text.strip():  # 텍스트가 비어있으면 에러 발생
        return TTSResult(success=False, error="변환할 텍스트가 필요합니다.")
    
    # 텍스트 길이 확인 (ElevenLabs 제한: 5000자)
    if len(text) > 5000:
        return TTSResult(success=False, error="텍스트가 너무 깁니다. (최대 5000자)")
    
    print(f"🎙️ TTS 생성 시작...")
    print(f"   텍스트: {text[:100]}{'...' if len(text) > 100 else ''}")  # 첫 100자만 출력
    print(f"   음성: {TTSConfig.VOICES.get(voice_id, voice_id)}")
    print(f"   모델: {model_id}")
    
    # HTTP 헤더 설정
    headers = {
        "Accept": "audio/mpeg",  # MP3 형식으로 요청
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    # 요청 데이터 구성
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # 60초 타임아웃
            # TTS 생성 API 호출
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                error_msg = f"TTS 생성 실패: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                return TTSResult(success=False, error=error_msg)
            
            # 출력 디렉토리 설정
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                output_path = Path(tempfile.gettempdir()) / "tts_audio"
                output_path.mkdir(parents=True, exist_ok=True)
            
            # 고유한 파일명 생성 (타임스탬프 기반)
            import time
            timestamp = int(time.time() * 1000)
            audio_filename = f"tts_{timestamp}.mp3"
            audio_file_path = output_path / audio_filename
            
            # 오디오 데이터를 파일로 저장
            with open(audio_file_path, "wb") as audio_file:
                audio_file.write(response.content)
            
            # 파일 크기 확인
            file_size = audio_file_path.stat().st_size
            
            # 오디오 길이 확인 (moviepy 사용)
            try:
                from moviepy.editor import AudioFileClip
                with AudioFileClip(str(audio_file_path)) as audio_clip:
                    duration = audio_clip.duration
            except Exception as e:
                print(f"⚠️ 오디오 길이 확인 실패: {e}")
                duration = None
            
            print(f"✅ TTS 생성 완료!")
            print(f"   파일: {audio_file_path}")
            print(f"   크기: {file_size:,} bytes")
            if duration:
                print(f"   길이: {duration:.2f}초")
            
            return TTSResult(
                success=True,
                audio_file_path=str(audio_file_path),
                text=text,
                voice_id=voice_id,
                duration=duration,
                file_size=file_size
            )
            
    except Exception as e:
        error_msg = f"TTS 생성 중 오류 발생: {e}"
        print(f"❌ {error_msg}")
        return TTSResult(success=False, error=error_msg)

async def create_multiple_tts_audio(
    text_list: List[str],  # 변환할 텍스트 리스트
    voice_id: str = TTSConfig.DEFAULT_VOICE_ID,  # 사용할 음성 ID
    model_id: str = TTSConfig.DEFAULT_MODEL_ID,  # 사용할 모델 ID
    api_key: str = None,  # ElevenLabs API 키
    output_dir: str = None  # 출력 디렉토리
) -> List[TTSResult]:
    """
    여러 텍스트를 순차적으로 음성으로 변환
    
    Args:
        text_list: 변환할 텍스트 리스트
        voice_id: 사용할 음성 ID
        model_id: 사용할 모델 ID  
        api_key: ElevenLabs API 키
        output_dir: 출력 디렉토리
        
    Returns:
        List[TTSResult]: 각 TTS 생성 결과 리스트
    """
    if not text_list:
        return []
    
    print(f"🎙️ 총 {len(text_list)}개 텍스트를 음성으로 변환 시작...")
    
    results = []
    successful_count = 0
    failed_count = 0
    
    for i, text in enumerate(text_list):
        scene_num = i + 1
        print(f"\n⏳ 음성 {scene_num}/{len(text_list)} 생성 중...")
        
        result = await create_tts_audio(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            api_key=api_key,
            output_dir=output_dir
        )
        
        results.append(result)
        
        if result.success:
            successful_count += 1
            print(f"✅ 음성 {scene_num} 생성 완료!")
        else:
            failed_count += 1
            print(f"❌ 음성 {scene_num} 생성 실패: {result.error}")
    
    print(f"\n🎉 음성 생성 완료!")
    print(f"   성공: {successful_count}/{len(text_list)}")
    print(f"   실패: {failed_count}/{len(text_list)}")
    
    return results

def get_voice_by_name(name: str) -> Optional[str]:
    """
    음성 이름으로 음성 ID 찾기
    
    Args:
        name: 음성 이름 (예: "Rachel", "Antoni" 등)
        
    Returns:
        Optional[str]: 음성 ID (찾지 못하면 None)
    """
    for voice_id, voice_name in TTSConfig.VOICES.items():
        if name.lower() in voice_name.lower():
            return voice_id
    return None

def list_available_voices() -> None:
    """사용 가능한 음성 목록을 출력"""
    print("🎙️ 사용 가능한 음성 목록:")
    for voice_id, voice_name in TTSConfig.VOICES.items():
        print(f"   {voice_id}: {voice_name}")

# 환경변수에서 API 키 가져오기
def get_elevenlabs_api_key() -> Optional[str]:
    """환경변수에서 ElevenLabs API 키 가져오기"""
    import os
    from dotenv import load_dotenv
    
    # .env 파일 로드
    load_dotenv()
    
    return os.getenv("ELEVNLABS_API_KEY")
