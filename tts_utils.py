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
    
    # 지원되는 음성 목록 (음성 ID와 이름, 언어 포함)
    VOICES = {
        # 영어 음성들
        "21m00Tcm4TlvDq8ikWAM": "Rachel (여성, 영어)",
        "AZnzlk1XvdvUeBnXmlld": "Domi (여성, 영어)", 
        "EXAVITQu4vr4xnSDxMaL": "Bella (여성, 영어)",
        "ErXwobaYiN019PkySvjV": "Antoni (남성, 영어)",
        "MF3mGyEYCl7XYWbV9V6O": "Elli (여성, 영어)",
        "TxGEqnHWrfWFTfGW9XjX": "Josh (남성, 영어)",
        "VR6AewLTigWG4xSOukaG": "Arnold (남성, 영어)",
        "pNInz6obpgDQGcFmaJgB": "Adam (남성, 영어)",
        "yoZ06aMxZJJ28mfd3POQ": "Sam (남성, 영어)",
        
        # 다국어 지원 음성들
        "Xb7hH8MSUJpSbSDYk0k2": "Alice (여성, 다국어)",
        "ThT5KcBeYPX3keUQqHPh": "Dorothy (여성, 다국어)",
        "JBFqnCBsd6RMkjVDRZzb": "George (남성, 다국어)",
        "N2lVS1w4EtoT3dr4eOWO": "Callum (남성, 다국어)",
        "IKne3meq5aSn9XLyUdCD": "Charlie (남성, 다국어)",
        "oWAxZDx7w5VEj9dCyTzz": "Grace (여성, 다국어)"
    }
    
    # 언어별 권장 음성
    RECOMMENDED_VOICES = {
        "ko": ["Xb7hH8MSUJpSbSDYk0k2", "ThT5KcBeYPX3keUQqHPh"],  # 한국어 권장
        "en": ["21m00Tcm4TlvDq8ikWAM", "ErXwobaYiN019PkySvjV"],  # 영어 권장
        "multilingual": ["Xb7hH8MSUJpSbSDYk0k2", "JBFqnCBsd6RMkjVDRZzb"]  # 다국어 권장
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

def detect_language(text: str) -> str:
    """
    텍스트의 언어를 자동 감지
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        str: 언어 코드 ('ko', 'en', 'multilingual')
    """
    import re
    
    # 한국어 문자 패턴 (한글)
    korean_pattern = re.compile(r'[가-힣]')
    # 영어 문자 패턴
    english_pattern = re.compile(r'[a-zA-Z]')
    
    korean_chars = len(korean_pattern.findall(text))
    english_chars = len(english_pattern.findall(text))
    total_chars = korean_chars + english_chars
    
    if total_chars == 0:
        return "en"  # 기본값
    
    korean_ratio = korean_chars / total_chars
    english_ratio = english_chars / total_chars
    
    if korean_ratio > 0.7:
        return "ko"
    elif english_ratio > 0.7:
        return "en"
    else:
        return "multilingual"

def get_recommended_voice(text: str, gender: str = None) -> str:
    """
    텍스트와 선호 성별에 따라 권장 음성 ID 반환
    
    Args:
        text: TTS로 변환할 텍스트
        gender: 선호 성별 ('male', 'female', None)
        
    Returns:
        str: 권장 음성 ID
    """
    language = detect_language(text)
    recommended_voices = TTSConfig.RECOMMENDED_VOICES.get(language, TTSConfig.RECOMMENDED_VOICES["multilingual"])
    
    if gender:
        # 성별에 따른 필터링
        filtered_voices = []
        for voice_id in recommended_voices:
            voice_name = TTSConfig.VOICES.get(voice_id, "")
            if gender == "female" and "여성" in voice_name:
                filtered_voices.append(voice_id)
            elif gender == "male" and "남성" in voice_name:
                filtered_voices.append(voice_id)
        
        if filtered_voices:
            return filtered_voices[0]
    
    return recommended_voices[0]

def get_voices_by_language(language: str = None) -> Dict[str, str]:
    """
    언어별 음성 목록 반환
    
    Args:
        language: 언어 코드 ('ko', 'en', 'multilingual', None)
        
    Returns:
        Dict[str, str]: 음성 ID와 이름 딕셔너리
    """
    if language == "ko":
        # 한국어에 적합한 다국어 음성들
        return {k: v for k, v in TTSConfig.VOICES.items() if "다국어" in v}
    elif language == "en":
        # 영어 전용 음성들
        return {k: v for k, v in TTSConfig.VOICES.items() if "영어" in v}
    else:
        # 모든 음성
        return TTSConfig.VOICES

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

async def create_voice_sample(
    voice_id: str,
    sample_text: str = "안녕하세요! 이것은 음성 샘플입니다. 이 목소리가 마음에 드시나요?",
    api_key: str = None,
    output_dir: str = None
) -> TTSResult:
    """
    특정 음성으로 샘플 오디오 생성 (음성 선택을 위한 미리보기)
    
    Args:
        voice_id: 테스트할 음성 ID
        sample_text: 샘플로 읽을 텍스트
        api_key: ElevenLabs API 키
        output_dir: 출력 디렉토리
        
    Returns:
        TTSResult: 샘플 TTS 생성 결과
    """
    if not api_key:
        api_key = get_elevenlabs_api_key()
        if not api_key:
            return TTSResult(success=False, error="ElevenLabs API 키가 필요합니다.")
    
    print(f"🎤 음성 샘플 생성: {TTSConfig.VOICES.get(voice_id, voice_id)}")
    
    # 샘플용 짧은 설정
    result = await create_tts_audio(
        text=sample_text,
        voice_id=voice_id,
        model_id=TTSConfig.DEFAULT_MODEL_ID,
        stability=TTSConfig.DEFAULT_STABILITY,
        similarity_boost=TTSConfig.DEFAULT_SIMILARITY_BOOST,
        style=TTSConfig.DEFAULT_STYLE,
        use_speaker_boost=TTSConfig.DEFAULT_USE_SPEAKER_BOOST,
        api_key=api_key,
        output_dir=output_dir
    )
    
    if result.success:
        print(f"✅ 음성 샘플 생성 완료: {result.audio_file_path}")
    else:
        print(f"❌ 음성 샘플 생성 실패: {result.error}")
    
    return result

async def create_voice_samples_by_language(
    sample_text: str = None,
    language: str = "ko",
    gender_preference: str = None,  # 'male', 'female', None
    api_key: str = None,
    output_dir: str = None,
    max_samples: int = 5
) -> Dict[str, TTSResult]:
    """
    언어별로 추천 음성들의 샘플 생성
    
    Args:
        sample_text: 샘플 텍스트 (None이면 언어별 기본 텍스트 사용)
        language: 언어 코드 ('ko', 'en', 'multilingual')
        gender_preference: 성별 선호도
        api_key: ElevenLabs API 키
        output_dir: 출력 디렉토리
        max_samples: 최대 샘플 수
        
    Returns:
        Dict[str, TTSResult]: 음성 ID별 샘플 결과
    """
    if not api_key:
        api_key = get_elevenlabs_api_key()
        if not api_key:
            return {"error": TTSResult(success=False, error="ElevenLabs API 키가 필요합니다.")}
    
    # 언어별 기본 샘플 텍스트
    default_texts = {
        "ko": "안녕하세요! 오늘 하루는 어떠셨나요? 이 목소리로 광고를 만들어보시겠어요?",
        "en": "Hello! How was your day today? Would you like to create an advertisement with this voice?",
        "multilingual": "안녕하세요! Hello! This voice supports multiple languages. 여러 언어를 지원하는 음성입니다."
    }
    
    if not sample_text:
        sample_text = default_texts.get(language, default_texts["ko"])
    
    # 언어별 음성 필터링
    voices_to_test = get_voices_by_language(language)
    
    # 성별 필터링
    if gender_preference:
        filtered_voices = {}
        for voice_id, voice_name in voices_to_test.items():
            if gender_preference == "female" and "여성" in voice_name:
                filtered_voices[voice_id] = voice_name
            elif gender_preference == "male" and "남성" in voice_name:
                filtered_voices[voice_id] = voice_name
        
        if filtered_voices:
            voices_to_test = filtered_voices
    
    # 최대 샘플 수 제한
    if len(voices_to_test) > max_samples:
        print(f"⚠️ 너무 많은 음성({len(voices_to_test)})입니다. 상위 {max_samples}개만 생성합니다.")
        voices_to_test = dict(list(voices_to_test.items())[:max_samples])
    
    print(f"🎙️ {len(voices_to_test)}개 음성으로 샘플 생성 시작...")
    print(f"   언어: {language}")
    print(f"   성별: {gender_preference or '전체'}")
    print(f"   샘플 텍스트: {sample_text[:50]}...")
    
    results = {}
    for i, (voice_id, voice_name) in enumerate(voices_to_test.items(), 1):
        print(f"\n🔊 [{i}/{len(voices_to_test)}] {voice_name} 샘플 생성 중...")
        
        result = await create_voice_sample(
            voice_id=voice_id,
            sample_text=sample_text,
            api_key=api_key,
            output_dir=output_dir
        )
        
        results[voice_id] = result
        
        if result.success:
            print(f"✅ {voice_name} 샘플 완료")
        else:
            print(f"❌ {voice_name} 샘플 실패: {result.error}")
        
        # API 호출 간격 (과도한 요청 방지)
        await asyncio.sleep(1)
    
    successful_count = len([r for r in results.values() if r.success])
    print(f"\n🎉 음성 샘플 생성 완료! 총 {successful_count}/{len(voices_to_test)}개 성공")
    
    return results

def play_audio_sample(audio_file_path: str) -> bool:
    """
    오디오 파일을 시스템 기본 플레이어로 재생
    
    Args:
        audio_file_path: 재생할 오디오 파일 경로
        
    Returns:
        bool: 재생 성공 여부
    """
    try:
        import os
        import platform
        
        if not os.path.exists(audio_file_path):
            print(f"❌ 파일을 찾을 수 없습니다: {audio_file_path}")
            return False
        
        system = platform.system()
        
        if system == "Windows":
            # Windows에서 기본 음악 플레이어로 재생
            os.startfile(audio_file_path)
        elif system == "Darwin":  # macOS
            os.system(f"open '{audio_file_path}'")
        elif system == "Linux":
            os.system(f"xdg-open '{audio_file_path}'")
        else:
            print(f"⚠️ 지원하지 않는 운영체제: {system}")
            return False
        
        print(f"🔊 오디오 재생 시작: {os.path.basename(audio_file_path)}")
        return True
        
    except Exception as e:
        print(f"❌ 오디오 재생 실패: {e}")
        return False

def list_voice_samples_with_info(results: Dict[str, TTSResult]) -> None:
    """생성된 음성 샘플들의 정보를 보기 좋게 출력"""
    print("\n🎤 생성된 음성 샘플 목록:")
    print("=" * 80)
    
    successful_results = {k: v for k, v in results.items() if v.success}
    
    if not successful_results:
        print("생성된 샘플이 없습니다.")
        return
    
    for i, (voice_id, result) in enumerate(successful_results.items(), 1):
        voice_name = TTSConfig.VOICES.get(voice_id, voice_id)
        print(f"\n{i}. {voice_name}")
        print(f"   음성 ID: {voice_id}")
        print(f"   파일 경로: {result.audio_file_path}")
        print(f"   파일 크기: {result.file_size:,} bytes" if result.file_size else "   파일 크기: N/A")
        print(f"   재생 길이: {result.duration:.2f}초" if result.duration else "   재생 길이: N/A")
        print(f"   재생 명령: play_audio_sample(r'{result.audio_file_path}')")

async def interactive_voice_selection(
    sample_text: str = None,
    language: str = "ko",
    gender_preference: str = None
) -> Optional[str]:
    """
    대화형 음성 선택 인터페이스
    
    Args:
        sample_text: 테스트할 샘플 텍스트
        language: 언어 ('ko', 'en', 'multilingual')
        gender_preference: 성별 선호도 ('male', 'female', None)
        
    Returns:
        Optional[str]: 선택된 음성 ID (None이면 취소)
    """
    print("🎤 TTS 음성 선택 도우미")
    print("=" * 50)
    
    # 샘플 생성
    print("샘플 음성들을 생성합니다...")
    results = await create_voice_samples_by_language(
        sample_text=sample_text,
        language=language,
        gender_preference=gender_preference,
        output_dir="./static/audio"
    )
    
    if "error" in results:
        print(f"❌ 샘플 생성 실패: {results['error'].error}")
        return None
    
    successful_results = {k: v for k, v in results.items() if v.success}
    
    if not successful_results:
        print("❌ 생성된 샘플이 없습니다.")
        return None
    
    # 샘플 목록 출력
    list_voice_samples_with_info(results)
    
    print("\n🔊 각 음성을 듣고 선택해주세요:")
    print("1. 위 목록에서 원하는 음성의 파일을 직접 재생하세요")
    print("2. 또는 아래 명령어를 복사해서 실행하세요:")
    
    for i, (voice_id, result) in enumerate(successful_results.items(), 1):
        voice_name = TTSConfig.VOICES.get(voice_id, voice_id)
        print(f"   {i}번 재생: play_audio_sample(r'{result.audio_file_path}')")
    
    print("\n선택 완료 후 음성 ID를 입력하거나 'q'를 입력해 종료하세요.")
    
    # 사용자 입력 대기
    while True:
        try:
            user_input = input("\n선택할 음성 ID 또는 번호 (q=종료): ").strip()
            
            if user_input.lower() == 'q':
                print("음성 선택을 취소했습니다.")
                return None
            
            # 번호로 선택
            if user_input.isdigit():
                choice_num = int(user_input)
                voice_list = list(successful_results.keys())
                if 1 <= choice_num <= len(voice_list):
                    selected_voice_id = voice_list[choice_num - 1]
                    selected_voice_name = TTSConfig.VOICES.get(selected_voice_id, selected_voice_id)
                    print(f"✅ 선택된 음성: {selected_voice_name} ({selected_voice_id})")
                    return selected_voice_id
                else:
                    print(f"❌ 유효하지 않은 번호입니다. 1-{len(voice_list)} 사이의 번호를 입력하세요.")
                    continue
            
            # 음성 ID로 직접 선택
            if user_input in successful_results:
                selected_voice_name = TTSConfig.VOICES.get(user_input, user_input)
                print(f"✅ 선택된 음성: {selected_voice_name} ({user_input})")
                return user_input
            else:
                print(f"❌ 유효하지 않은 음성 ID입니다.")
                continue
                
        except KeyboardInterrupt:
            print("\n음성 선택을 취소했습니다.")
            return None
        except Exception as e:
            print(f"❌ 입력 오류: {e}")
            continue
