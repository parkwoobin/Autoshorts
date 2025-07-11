"""
Whisper AI를 이용한 자막 생성 및 FFmpeg를 통한 자막 합성 유틸리티
"""
import os
import tempfile
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
import subprocess
import httpx
from tts_utils import get_elevenlabs_api_key

class SubtitleConfig:
    """자막 관련 설정값들"""
    DEFAULT_FONT_SIZE = 14
    DEFAULT_FONT_COLOR = "white"
    DEFAULT_FONT_BORDER_COLOR = "black"
    DEFAULT_FONT_BORDER_WIDTH = 2
    DEFAULT_SUBTITLE_POSITION = "bottom"  # top, bottom, center
    DEFAULT_OUTPUT_FORMAT = "srt"  # srt, vtt, ass
    
    # 언어별 폰트 설정 (Windows 시스템 폰트 경로)
    FONTS = {
        "ko": "C:/Windows/Fonts/malgun.ttf",  # 맑은 고딕 (한국어)
        "ko_alt": "C:/Windows/Fonts/gulim.ttc",  # 굴림 (대안)
        "ko_alt2": "C:/Windows/Fonts/batang.ttc",  # 바탕 (대안)
        "en": "C:/Windows/Fonts/arial.ttf",        # Arial (영어)
        "default": "C:/Windows/Fonts/arial.ttf"    # 기본 폰트
    }

class SubtitleResult:
    """자막 생성 결과를 담는 데이터 클래스"""
    def __init__(
        self,
        success: bool,
        subtitle_file_path: Optional[str] = None,
        video_with_subtitle_path: Optional[str] = None,
        transcription: Optional[str] = None,
        language: Optional[str] = None,
        duration: Optional[float] = None,
        error: Optional[str] = None
    ):
        self.success = success  # 생성 성공 여부
        self.subtitle_file_path = subtitle_file_path  # 생성된 자막 파일 경로
        self.video_with_subtitle_path = video_with_subtitle_path  # 자막이 합성된 비디오 파일 경로
        self.transcription = transcription  # 전사된 텍스트
        self.language = language  # 감지된 언어
        self.duration = duration  # 오디오/비디오 길이 (초)
        self.error = error  # 에러 메시지 (실패시)

async def transcribe_audio_with_whisper(
    audio_file_path: str,  # 오디오 파일 경로
    language: str = None,  # 언어 지정 (None이면 자동 감지)
    api_key: str = None,  # OpenAI API 키
    output_format: str = "srt"  # 출력 형식 (srt, vtt, json)
) -> SubtitleResult:
    """
    Whisper API를 사용하여 오디오 파일을 전사하고 자막 파일 생성
    
    Args:
        audio_file_path: 전사할 오디오 파일 경로
        language: 언어 코드 (ko, en 등, None이면 자동 감지)
        api_key: OpenAI API 키
        output_format: 출력 형식 (srt, vtt, json)
        
    Returns:
        SubtitleResult: 자막 생성 결과
    """
    if not api_key:
        # .env에서 OpenAI API 키 가져오기
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            return SubtitleResult(success=False, error="OpenAI API 키가 필요합니다.")
    
    if not os.path.exists(audio_file_path):
        return SubtitleResult(success=False, error=f"오디오 파일을 찾을 수 없습니다: {audio_file_path}")
    
    print(f"🎤 Whisper API로 음성 전사 시작...")
    print(f"   파일: {os.path.basename(audio_file_path)}")
    print(f"   언어: {language or '자동 감지'}")
    print(f"   형식: {output_format}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Whisper API 요청 준비
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            # 파일 업로드 데이터 준비
            with open(audio_file_path, "rb") as audio_file:
                files = {
                    "file": (os.path.basename(audio_file_path), audio_file, "audio/mpeg")
                }
                
                data = {
                    "model": "whisper-1",
                    "response_format": output_format
                }
                
                # 언어가 지정된 경우 추가
                if language:
                    data["language"] = language
                
                # Whisper API 호출
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data
                )
            
            if response.status_code != 200:
                error_msg = f"Whisper API 요청 실패: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                return SubtitleResult(success=False, error=error_msg)
            
            # 응답 처리
            if output_format == "json":
                result_data = response.json()
                transcription = result_data.get("text", "")
                detected_language = result_data.get("language", "unknown")
                subtitle_content = transcription  # JSON 형식에서는 단순 텍스트
            else:
                # SRT 또는 VTT 형식
                subtitle_content = response.text
                transcription = subtitle_content
                detected_language = language or "auto"
            
            # 자막 파일 저장
            subtitle_dir = Path(tempfile.gettempdir()) / "subtitles"
            subtitle_dir.mkdir(exist_ok=True)
            
            import time
            timestamp = int(time.time() * 1000)
            subtitle_filename = f"subtitle_{timestamp}.{output_format}"
            subtitle_file_path = subtitle_dir / subtitle_filename
            
            with open(subtitle_file_path, "w", encoding="utf-8") as subtitle_file:
                subtitle_file.write(subtitle_content)
            
            # 오디오 파일 길이 확인
            try:
                from moviepy.editor import AudioFileClip
                with AudioFileClip(audio_file_path) as audio_clip:
                    duration = audio_clip.duration
            except Exception as e:
                print(f"⚠️ 오디오 길이 확인 실패: {e}")
                duration = None
            
            print(f"✅ 음성 전사 완료!")
            print(f"   자막 파일: {subtitle_file_path}")
            print(f"   감지된 언어: {detected_language}")
            if duration:
                print(f"   길이: {duration:.2f}초")
            
            return SubtitleResult(
                success=True,
                subtitle_file_path=str(subtitle_file_path),
                transcription=transcription,
                language=detected_language,
                duration=duration
            )
            
    except Exception as e:
        error_msg = f"음성 전사 중 오류 발생: {e}"
        print(f"❌ {error_msg}")
        return SubtitleResult(success=False, error=error_msg)

def add_subtitles_to_video_ffmpeg(
    video_file_path: str,  # 원본 비디오 파일 경로
    subtitle_file_path: str,  # 자막 파일 경로 (.srt)
    output_video_path: str = None,  # 출력 비디오 파일 경로
    font_size: int = SubtitleConfig.DEFAULT_FONT_SIZE,  # 폰트 크기
    font_color: str = SubtitleConfig.DEFAULT_FONT_COLOR,  # 폰트 색상
    font_border_color: str = SubtitleConfig.DEFAULT_FONT_BORDER_COLOR,  # 테두리 색상
    font_border_width: int = SubtitleConfig.DEFAULT_FONT_BORDER_WIDTH,  # 테두리 두께
    language: str = "ko"  # 언어 (폰트 선택용)
) -> SubtitleResult:
    """
    FFmpeg를 사용하여 비디오에 자막을 합성
    
    Args:
        video_file_path: 원본 비디오 파일 경로
        subtitle_file_path: 자막 파일 경로 (.srt)
        output_video_path: 출력 비디오 파일 경로
        font_size: 폰트 크기
        font_color: 폰트 색상
        font_border_color: 테두리 색상
        font_border_width: 테두리 두께
        language: 언어 코드
        
    Returns:
        SubtitleResult: 자막 합성 결과
    """
    if not os.path.exists(video_file_path):
        return SubtitleResult(success=False, error=f"비디오 파일을 찾을 수 없습니다: {video_file_path}")
    
    if not os.path.exists(subtitle_file_path):
        return SubtitleResult(success=False, error=f"자막 파일을 찾을 수 없습니다: {subtitle_file_path}")
    
    # 출력 파일명 생성
    if not output_video_path:
        video_dir = os.path.dirname(video_file_path)
        video_name = os.path.splitext(os.path.basename(video_file_path))[0]
        import time
        timestamp = int(time.time() * 1000)
        output_video_path = os.path.join(video_dir, f"{video_name}_with_subtitles_{timestamp}.mp4")
    
    print(f"🎬 FFmpeg로 자막 합성 시작...")
    print(f"   비디오: {os.path.basename(video_file_path)}")
    print(f"   자막: {os.path.basename(subtitle_file_path)}")
    print(f"   출력: {os.path.basename(output_video_path)}")
    
    try:
        # 먼저 자막을 순차적으로 변환
        print("📝 자막을 순차적 한 줄로 변환 중...")
        subtitle_dir = os.path.dirname(subtitle_file_path)
        subtitle_name = os.path.splitext(os.path.basename(subtitle_file_path))[0]
        sequential_subtitle_path = os.path.join(subtitle_dir, f"{subtitle_name}_sequential.srt")
        
        sequential_subtitle_path = create_sequential_subtitle_file(
            subtitle_file_path,
            sequential_subtitle_path,
            max_chars=10,     # 더 짧은 줄
            line_duration=0.7, # 더 빠른 표시
            gap_duration=0.1   # 더 촘촘한 간격
        )
        
        # 폰트 선택 및 존재 확인
        font_candidates = [
            SubtitleConfig.FONTS.get(language, SubtitleConfig.FONTS["default"]),
            SubtitleConfig.FONTS.get("ko"),  # 한국어 폰트 우선
            SubtitleConfig.FONTS.get("ko_alt"),  # 대안 1
            SubtitleConfig.FONTS.get("ko_alt2"),  # 대안 2
            SubtitleConfig.FONTS.get("default")  # 최후 수단
        ]
        
        font = None
        for font_candidate in font_candidates:
            if font_candidate and os.path.exists(font_candidate):
                font = font_candidate
                print(f"✅ 사용할 폰트: {font}")
                break
        
        if not font:
            print("⚠️ 한국어 폰트를 찾을 수 없습니다. drawtext 방식으로 대체합니다.")
            # drawtext 방식으로 대체 처리
            return create_video_with_drawtext_subtitles(
                video_file_path, sequential_subtitle_path, output_video_path, font_size
            )
        
        # FFmpeg 명령어 구성
        # Windows에서 경로 이슈를 피하기 위해 절대 경로 사용하고 백슬래시를 슬래시로 변환
        subtitle_path_fixed = sequential_subtitle_path.replace("\\", "/").replace(":", "\\:")
        
        # 순차적 자막 스타일 사용
        subtitle_style = get_sequential_subtitle_style(font_size=font_size, enable_outline=True)
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", video_file_path,  # 입력 비디오
            "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{subtitle_style}'",  # 순차적 자막 필터
            "-c:a", "copy",  # 오디오 스트림 복사 (재인코딩 없음)
            "-y",  # 출력 파일 덮어쓰기
            output_video_path
        ]
        
        print(f"🔧 FFmpeg 명령어 실행 중...")
        print(f"   명령어: {' '.join(ffmpeg_cmd)}")
        
        # FFmpeg 실행
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            error_msg = f"FFmpeg 실행 실패: {result.stderr}"
            print(f"❌ {error_msg}")
            return SubtitleResult(success=False, error=error_msg)
        
        print(f"✅ 자막 합성 완료!")
        print(f"   출력 파일: {output_video_path}")
        
        return SubtitleResult(
            success=True,
            video_with_subtitle_path=output_video_path,
            subtitle_file_path=subtitle_file_path
        )
        
    except Exception as e:
        error_msg = f"자막 합성 중 오류 발생: {e}"
        print(f"❌ {error_msg}")
        return SubtitleResult(success=False, error=error_msg)

async def create_video_with_tts_and_subtitles(
    video_file_path: str,  # 원본 비디오 파일 경로
    text: str,  # TTS로 변환할 텍스트
    voice_id: str = None,  # 음성 ID
    tts_volume: float = 0.8,  # TTS 볼륨
    video_volume: float = 0.2,  # 원본 비디오 볼륨
    subtitle_language: str = None,  # 자막 언어 (None이면 자동 감지)
    elevenlabs_api_key: str = None,  # ElevenLabs API 키
    openai_api_key: str = None,  # OpenAI API 키
    output_dir: str = None  # 출력 디렉토리
) -> Dict[str, Any]:
    """
    비디오에 TTS 음성 추가 + Whisper로 자막 생성 + FFmpeg로 자막 합성하여 최종 비디오 생성
    
    Args:
        video_file_path: 원본 비디오 파일 경로
        text: TTS로 변환할 텍스트
        voice_id: 사용할 음성 ID
        tts_volume: TTS 볼륨
        video_volume: 원본 비디오 볼륨
        subtitle_language: 자막 언어
        elevenlabs_api_key: ElevenLabs API 키
        openai_api_key: OpenAI API 키
        output_dir: 출력 디렉토리
        
    Returns:
        Dict[str, Any]: 전체 처리 결과
    """
    print(f"🎬 TTS + 자막 통합 비디오 생성 시작...")
    print(f"   텍스트: {text[:100]}{'...' if len(text) > 100 else ''}")
    
    try:
        # 1단계: TTS 음성 생성
        from tts_utils import create_tts_audio, get_recommended_voice, detect_language
        
        if not elevenlabs_api_key:
            elevenlabs_api_key = get_elevenlabs_api_key()
        
        if not voice_id:
            # 텍스트 기반으로 권장 음성 자동 선택
            voice_id = get_recommended_voice(text)
        
        print(f"🎙️ 1단계: TTS 음성 생성...")
        tts_result = await create_tts_audio(
            text=text,
            voice_id=voice_id,
            api_key=elevenlabs_api_key,
            output_dir=output_dir or "./static/audio"
        )
        
        if not tts_result.success:
            return {"success": False, "error": f"TTS 생성 실패: {tts_result.error}"}
        
        # 2단계: TTS 음성을 비디오에 합성
        from video_merger import VideoTransitionMerger
        
        print(f"🎵 2단계: TTS 음성을 비디오에 합성...")
        merger = VideoTransitionMerger(use_static_dir=True)
        video_with_tts_path = await merger.add_tts_to_video(
            video_path=video_file_path,
            text=text,
            voice_id=voice_id,
            tts_volume=tts_volume,
            video_volume=video_volume,
            api_key=elevenlabs_api_key
        )
        
        # 3단계: Whisper로 TTS 음성을 전사하여 자막 생성
        print(f"📝 3단계: Whisper로 자막 생성...")
        
        # 자막 언어 자동 감지
        if not subtitle_language:
            subtitle_language = detect_language(text)
            if subtitle_language == "multilingual":
                subtitle_language = "ko"  # 기본값으로 한국어 사용
        
        subtitle_result = await transcribe_audio_with_whisper(
            audio_file_path=tts_result.audio_file_path,
            language=subtitle_language,
            api_key=openai_api_key,
            output_format="srt"
        )
        
        if not subtitle_result.success:
            return {
                "success": False,
                "error": f"자막 생성 실패: {subtitle_result.error}",
                "video_with_tts": video_with_tts_path
            }
        
        # 4단계: FFmpeg로 자막을 비디오에 합성
        print(f"🎬 4단계: FFmpeg로 자막 합성...")
        final_result = add_subtitles_to_video_ffmpeg(
            video_file_path=video_with_tts_path,
            subtitle_file_path=subtitle_result.subtitle_file_path,
            language=subtitle_language
        )
        
        if not final_result.success:
            return {
                "success": False,
                "error": f"자막 합성 실패: {final_result.error}",
                "video_with_tts": video_with_tts_path,
                "subtitle_file": subtitle_result.subtitle_file_path
            }
        
        # 임시 파일 정리
        try:
            os.remove(tts_result.audio_file_path)  # TTS 오디오 파일
            os.remove(video_with_tts_path)  # 중간 비디오 파일
        except:
            pass
        
        print(f"✅ TTS + 자막 통합 비디오 생성 완료!")
        
        return {
            "success": True,
            "final_video_path": final_result.video_with_subtitle_path,
            "subtitle_file_path": subtitle_result.subtitle_file_path,
            "transcription": subtitle_result.transcription,
            "detected_language": subtitle_result.language,
            "voice_used": voice_id,
            "tts_duration": tts_result.duration
        }
        
    except Exception as e:
        error_msg = f"TTS + 자막 통합 처리 중 오류 발생: {e}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

async def generate_subtitles_with_whisper(
    audio_path: str,
    output_dir: str = None,
    language: str = "ko",
    model_size: str = "base"
) -> Dict[str, Any]:
    """
    TTS 오디오 파일에서 Whisper를 사용하여 자막 파일 생성
    
    Args:
        audio_path: 오디오 파일 경로
        output_dir: 출력 디렉토리
        language: 언어 코드
        model_size: Whisper 모델 크기
        
    Returns:
        Dict[str, Any]: 자막 생성 결과
    """
    if not output_dir:
        output_dir = os.path.join("static", "subtitles")
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Whisper API로 자막 생성
        result = await transcribe_audio_with_whisper(
            audio_file_path=audio_path,
            language=language,
            output_format="srt"
        )
        
        if result.success:
            # 출력 디렉토리로 파일 이동
            import time
            timestamp = int(time.time() * 1000)
            filename = f"subtitle_{timestamp}.srt"
            final_path = os.path.join(output_dir, filename)
            
            # 파일 이동
            import shutil
            shutil.move(result.subtitle_file_path, final_path)
            
            return {
                "success": True,
                "subtitle_file": final_path,
                "transcription": result.transcription,
                "language": result.language,
                "confidence": 0.95  # 기본 신뢰도
            }
        else:
            return {
                "success": False,
                "error": result.error
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"자막 생성 오류: {e}"
        }

async def merge_video_with_subtitles(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    subtitle_style: str = "default"
) -> str:
    """
    비디오 파일에 자막을 합성하여 새로운 비디오 생성
    
    Args:
        video_path: 원본 비디오 파일 경로
        subtitle_path: 자막 파일 경로 (.srt)
        output_path: 출력 비디오 파일 경로
        subtitle_style: 자막 스타일
        
    Returns:
        str: 생성된 비디오 파일 경로
    """
    try:
        # FFmpeg를 사용하여 자막 합성
        result = add_subtitles_to_video_ffmpeg(
            video_file_path=video_path,
            subtitle_file_path=subtitle_path,
            output_video_path=output_path,
            language="ko"  # 기본 한국어
        )
        
        if result.success:
            return result.video_with_subtitle_path
        else:
            raise Exception(result.error)
            
    except Exception as e:
        print(f"❌ 자막 합성 실패: {e}")
        raise

async def merge_video_with_tts_and_subtitles(
    video_urls: List[str],
    tts_scripts: List[str],
    transition_type: str = "fade",
    voice_id: Optional[str] = None,
    tts_volume: float = 0.8,
    video_volume: float = 0.3,
    add_subtitles: bool = True,
    api_key: Optional[str] = None,
    enable_bgm: bool = True,
    bgm_volume: float = 0.2,
    bgm_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    비디오들에 TTS 음성과 자막을 모두 추가한 후 트랜지션과 함께 합치기
    
    Args:
        video_urls: 비디오 URL 리스트
        tts_scripts: TTS 스크립트 리스트
        transition_type: 트랜지션 타입
        voice_id: 음성 ID
        tts_volume: TTS 볼륨
        video_volume: 원본 비디오 볼륨
        add_subtitles: 자막 추가 여부
        api_key: ElevenLabs API 키
        enable_bgm: 배경 음악 사용 여부
        bgm_volume: 배경 음악 볼륨
        bgm_file: 배경 음악 파일 경로 (None이면 랜덤 선택)
        
    Returns:
        Dict[str, Any]: 처리 결과
    """
    try:
        from tts_utils import create_multiple_tts_audio
        import time
        import random
        import glob
        
        print(f"🎬 TTS + 자막 완전 합치기 시작...")
        print(f"   비디오: {len(video_urls)}개")
        print(f"   TTS 스크립트: {len(tts_scripts)}개")
        
        # BGM 파일 선택
        selected_bgm = None
        if enable_bgm:
            if bgm_file and os.path.exists(bgm_file):
                selected_bgm = bgm_file
                print(f"🎵 지정된 BGM 사용: {os.path.basename(bgm_file)}")
            else:
                # 랜덤하게 BGM 선택
                bgm_files = glob.glob("./bgm/*.mp3") + glob.glob("./bgm/*.m4a")
                if bgm_files:
                    selected_bgm = random.choice(bgm_files)
                    print(f"🎵 랜덤 BGM 선택: {os.path.basename(selected_bgm)}")
                else:
                    print("⚠️ BGM 파일을 찾을 수 없습니다.")
                    enable_bgm = False
        
        # 1단계: TTS 오디오 생성
        print("🎤 1단계: TTS 오디오 생성 중...")
        tts_results = await create_multiple_tts_audio(
            text_list=tts_scripts,
            voice_id=voice_id,
            api_key=api_key,
            output_dir="./static/audio"
        )
        
        # 성공한 TTS 파일들만 추출
        successful_tts_files = []
        for result in tts_results:
            if result.success:
                successful_tts_files.append(result.audio_file_path)
        
        print(f"✅ TTS 생성 완료: {len(successful_tts_files)}개")
        
        # 2단계: 자막 생성 (옵션)
        subtitle_files = []
        if add_subtitles and successful_tts_files:
            print("📝 2단계: 자막 생성 중...")
            for tts_file in successful_tts_files:
                try:
                    subtitle_result = await generate_subtitles_with_whisper(
                        audio_path=tts_file,
                        output_dir="./static/subtitles"
                    )
                    if subtitle_result.get("success"):
                        subtitle_files.append(subtitle_result["subtitle_file"])
                except Exception as e:
                    print(f"⚠️ 자막 생성 실패: {e}")
            
            print(f"✅ 자막 생성 완료: {len(subtitle_files)}개")
        
        # 3단계: 비디오 + TTS + 자막 실제 합치기
        print("🎬 3단계: 실제 FFmpeg로 비디오 + TTS + 자막 합치기...")
        
        # 타임스탬프를 포함한 출력 파일명 생성
        timestamp = int(time.time())
        output_filename = f"final_video_with_tts_subtitles_{timestamp}.mp4"
        output_path = os.path.join("./static/videos", output_filename)
        
        # 디렉토리 생성
        os.makedirs("./static/videos", exist_ok=True)
        
        if video_urls and successful_tts_files:
            try:
                print(f"🎥 원본 비디오: {video_urls[0]}")
                print(f"🎙️ TTS 오디오: {len(successful_tts_files)}개")
                print(f"📝 자막 파일: {len(subtitle_files)}개")
                
                # 첫 번째 비디오와 첫 번째 TTS 사용
                first_video = video_urls[0]
                # HTTP URL을 로컬 파일 경로로 변환
                if first_video.startswith("http://localhost:8000/static/videos/"):
                    first_video_local = first_video.replace("http://localhost:8000/static/videos/", "./static/videos/")
                    first_video = first_video_local
                print(f"🎬 사용할 비디오: {first_video}")
                
                first_tts = successful_tts_files[0] if successful_tts_files else None
                first_subtitle = subtitle_files[0] if subtitle_files else None
                
                if first_tts and first_subtitle and add_subtitles:
                    # 방법 1: 비디오 + TTS + 자막 + BGM 모두 합치기
                    print("🔄 FFmpeg: 비디오 + TTS + 자막 + BGM 통합 처리 중...")
                    
                    # 자막을 순차적으로 한 줄씩 나오도록 처리
                    split_subtitle_path = first_subtitle.replace('.srt', '_sequential.srt')
                    split_subtitle_path = create_sequential_subtitle_file(
                        first_subtitle, 
                        split_subtitle_path,
                        max_chars=10,     # 더 짧은 줄로 설정 (10자)
                        line_duration=0.7, # 각 줄 0.7초 표시 (빠르게)
                        gap_duration=0.1   # 줄 사이 0.1초 간격 (촘촘하게)
                    )
                    
                    # 자막 파일 경로를 Windows 호환 형식으로 변환
                    subtitle_path_fixed = split_subtitle_path.replace("\\", "/").replace(":", "\\:")
                    
                    # 한 줄씩 순차적으로 나오는 자막 스타일
                    subtitle_style = get_sequential_subtitle_style(font_size=18, enable_outline=True)
                    
                    # FFmpeg 전체 경로 사용
                    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
                    
                    if enable_bgm and selected_bgm:
                        # BGM 포함 처리 (자막 때문에 비디오 재인코딩 필요)
                        cmd = [
                            ffmpeg_exe, "-y",
                            "-i", first_video,        # 입력 비디오
                            "-i", first_tts,          # 입력 오디오 (TTS)
                            "-i", selected_bgm,       # 입력 BGM
                            "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{subtitle_style}'",  # 개선된 자막 필터
                            "-filter_complex", f"[1:a]volume={tts_volume}[tts];[2:a]volume={bgm_volume}[bgm];[tts][bgm]amix=inputs=2:duration=first:dropout_transition=3[audio]",  # 오디오 믹싱
                            "-map", "0:v:0",          # 비디오 스트림
                            "-map", "[audio]",        # 믹싱된 오디오
                            "-c:v", "libx264",        # 비디오 코덱 (재인코딩)
                            "-c:a", "aac",            # 오디오 코덱
                            "-shortest",              # 짧은 것에 맞춤
                            output_path
                        ]
                    else:
                        # BGM 없이 처리 (자막 때문에 비디오 재인코딩 필요)
                        cmd = [
                            ffmpeg_exe, "-y",
                            "-i", first_video,        # 입력 비디오
                            "-i", first_tts,          # 입력 오디오 (TTS)
                            "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{subtitle_style}'",  # 개선된 자막 필터
                            "-c:v", "libx264",        # 비디오 코덱 (재인코딩)
                            "-c:a", "aac",            # 오디오 코덱
                            "-map", "0:v:0",          # 비디오 스트림
                            "-map", "1:a:0",          # 오디오 스트림 (TTS)
                            "-shortest",              # 짧은 것에 맞춤
                            output_path
                        ]
                    
                elif first_tts:
                    # 방법 2: 비디오 + TTS + BGM 합치기 (자막 없음)
                    print("🔄 FFmpeg: 비디오 + TTS + BGM 처리 중...")
                    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
                    
                    if enable_bgm and selected_bgm:
                        # BGM 포함 처리
                        cmd = [
                            ffmpeg_exe, "-y",
                            "-i", first_video,        # 입력 비디오
                            "-i", first_tts,          # 입력 오디오 (TTS)
                            "-i", selected_bgm,       # 입력 BGM
                            "-filter_complex", f"[1:a]volume={tts_volume}[tts];[2:a]volume={bgm_volume}[bgm];[tts][bgm]amix=inputs=2:duration=first:dropout_transition=3[audio]",  # 오디오 믹싱
                            "-map", "0:v:0",          # 비디오 스트림
                            "-map", "[audio]",        # 믹싱된 오디오
                            "-c:v", "copy",           # 비디오 코덱 (복사)
                            "-c:a", "aac",            # 오디오 코덱
                            "-shortest",              # 짧은 것에 맞춤
                            output_path
                        ]
                    else:
                        # BGM 없이 처리
                        cmd = [
                            ffmpeg_exe, "-y",
                            "-i", first_video,
                            "-i", first_tts,
                            "-c:v", "copy",
                            "-c:a", "aac",
                            "-map", "0:v:0",
                            "-map", "1:a:0",
                            "-shortest",
                            output_path
                        ]
                    
                else:
                    # 방법 3: 원본 비디오 + BGM만 추가
                    print("🔄 원본 비디오 + BGM 처리 중...")
                    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
                    
                    if enable_bgm and selected_bgm:
                        # BGM 포함 처리
                        cmd = [
                            ffmpeg_exe, "-y",
                            "-i", first_video,        # 입력 비디오
                            "-i", selected_bgm,       # 입력 BGM
                            "-filter_complex", f"[1:a]volume={bgm_volume}[bgm]",  # BGM 볼륨 조절
                            "-map", "0:v:0",          # 비디오 스트림
                            "-map", "[bgm]",          # BGM 오디오
                            "-c:v", "copy",           # 비디오 코덱 (복사)
                            "-c:a", "aac",            # 오디오 코덱
                            "-shortest",              # 짧은 것에 맞춤
                            output_path
                        ]
                    else:
                        # BGM 없이 원본 복사
                        cmd = [
                            ffmpeg_exe, "-y",
                            "-i", first_video,
                            "-c", "copy",
                            output_path
                        ]
                
                print(f"🔧 FFmpeg 명령어: {' '.join(cmd)}")
                
                # FFmpeg 실행
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"❌ FFmpeg 오류: {result.stderr}")
                    raise Exception(f"FFmpeg 처리 실패: {result.stderr}")
                    
                print(f"✅ FFmpeg 처리 완료: {output_filename}")
                
                # 파일이 실제로 생성되었는지 확인
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"📁 파일 크기: {os.path.getsize(output_path)} bytes")
                else:
                    raise Exception("생성된 파일이 비어있거나 존재하지 않습니다.")
            
            except Exception as e:
                print(f"❌ 실제 비디오 처리 실패: {e}")
                # 실패 시 에러 반환
                return {
                    "success": False,
                    "error": f"비디오 처리 실패: {result.stderr}",
                    "tts_files": successful_tts_files,
                    "subtitle_files": subtitle_files
                }
        
        else:
            print("❌ 입력 데이터 부족 (비디오 또는 TTS 없음)")
            return {
                "success": False,
                "error": "비디오 URL 또는 TTS 파일이 없습니다.",
                "tts_files": successful_tts_files,
                "subtitle_files": subtitle_files
            }
        
        print(f"✅ 최종 영상 생성 완료: {output_filename}")
        
        return {
            "success": True,
            "final_video_path": output_path,
            "tts_files": successful_tts_files,
            "subtitle_files": subtitle_files,
            "subtitle_info": {
                "count": len(subtitle_files),
                "files": subtitle_files
            }
        }
        
    except Exception as e:
        print(f"❌ TTS + 자막 완전 합치기 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def create_enhanced_subtitle_file(subtitle_file_path: str, output_path: str, max_chars_per_line: int = 25) -> str:
    """
    기존 자막 파일을 읽어서 긴 텍스트를 여러 줄로 나누고 개선된 스타일을 적용한 새 자막 파일 생성
    
    Args:
        subtitle_file_path: 원본 자막 파일 경로
        output_path: 개선된 자막 파일 저장 경로
        max_chars_per_line: 한 줄당 최대 문자 수
        
    Returns:
        str: 개선된 자막 파일 경로
    """
    try:
        import re
        
        print(f"📝 자막 파일 개선 중...")
        print(f"   원본: {os.path.basename(subtitle_file_path)}")
        print(f"   한 줄당 최대 문자 수: {max_chars_per_line}")
        
        # 원본 자막 파일 읽기
        with open(subtitle_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # SRT 형식 파싱 (번호, 시간, 텍스트)
        subtitle_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\n\d+\n|\Z)'
        matches = re.findall(subtitle_pattern, content, re.DOTALL)
        
        enhanced_content = ""
        
        for i, (number, timing, text) in enumerate(matches, 1):
            # 텍스트 정리 (불필요한 공백 제거)
            text = text.strip().replace('\n', ' ')
            
            # 긴 텍스트를 여러 줄로 나누기
            lines = []
            words = text.split()
            current_line = ""
            
            for word in words:
                # 현재 줄에 단어를 추가했을 때 길이 확인
                test_line = current_line + (" " if current_line else "") + word
                
                if len(test_line) <= max_chars_per_line:
                    current_line = test_line
                else:
                    # 현재 줄이 비어있지 않으면 저장
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            # 마지막 줄 추가
            if current_line:
                lines.append(current_line)
            
            # 자막 엔트리 생성
            enhanced_content += f"{i}\n"
            enhanced_content += f"{timing}\n"
            enhanced_content += "\n".join(lines)
            enhanced_content += "\n\n"
        
        # 개선된 자막 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_content.strip())
        
        print(f"✅ 개선된 자막 파일 생성: {os.path.basename(output_path)}")
        return output_path
        
    except Exception as e:
        print(f"❌ 자막 파일 개선 실패: {e}")
        # 실패 시 원본 파일 경로 반환
        return subtitle_file_path

def get_enhanced_subtitle_style(font_size: int = 20, enable_outline: bool = True) -> str:
    """
    개선된 자막 스타일 설정 반환
    
    Args:
        font_size: 폰트 크기
        enable_outline: 외곽선 사용 여부
        
    Returns:
        str: FFmpeg용 자막 스타일 문자열
    """
    style_options = [
        f"FontSize={font_size}",
        "PrimaryColour=&Hffffff",  # 흰색 텍스트
        "Alignment=2",  # 하단 중앙 정렬
        "MarginV=30",   # 하단 여백
        "MarginL=20",   # 좌측 여백
        "MarginR=20",   # 우측 여백
        "WrapStyle=2",  # 수동 줄바꿈만 허용 (완전 한 줄 강제)
    ]
    
    if enable_outline:
        style_options.extend([
            "OutlineColour=&H000000",  # 검은색 외곽선
            "BorderStyle=1",
            "Outline=2",
            "Shadow=1"
        ])
    
    return ",".join(style_options)

def get_sequential_subtitle_style(font_size: int = 14, enable_outline: bool = True) -> str:
    """
    순차적으로 한 줄씩 나오는 자막을 위한 스타일 설정
    
    Args:
        font_size: 폰트 크기
        enable_outline: 외곽선 사용 여부
        
    Returns:
        str: FFmpeg용 자막 스타일 문자열
    """
    style_options = [
        f"FontSize={font_size}",
        "PrimaryColour=&Hffffff",  # 흰색 텍스트
        "Alignment=2",  # 하단 중앙 정렬
        "MarginV=30",   # 하단 여백 (줄임)
        "MarginL=20",   # 좌측 여백 (줄임)
        "MarginR=20",   # 우측 여백 (줄임)
        "WrapStyle=0",  # 스마트 줄바꿈 (한 줄 강제)
        "ScaleX=100",   # 가로 크기
        "ScaleY=100",   # 세로 크기
        "Bold=0",       # 굵은 글씨 해제
    ]
    
    if enable_outline:
        style_options.extend([
            "OutlineColour=&H000000",  # 검은색 외곽선
            "BorderStyle=1",
            "Outline=2",               # 더 얇은 외곽선
            "Shadow=1"                 # 적은 그림자 효과
        ])
    
    return ",".join(style_options)

# 환경변수에서 API 키들 가져오기
def get_api_keys() -> Dict[str, Optional[str]]:
    """환경변수에서 필요한 API 키들을 모두 가져오기"""
    from dotenv import load_dotenv
    load_dotenv()
    
    return {
        "elevenlabs": os.getenv("ELEVNLABS_API_KEY"),
        "openai": os.getenv("OPENAI_API_KEY"),
        "runway": os.getenv("RUNWAY_API_KEY")
    }

def create_single_line_subtitle_file(subtitle_file_path: str, output_path: str, max_chars: int = 20) -> str:
    """
    기존 자막 파일을 읽어서 짧은 한 줄 자막으로 분할하여 새 자막 파일 생성
    각 줄이 끝나면 다음 초에서 새 줄이 시작되도록 시간 조정
    
    Args:
        subtitle_file_path: 원본 자막 파일 경로
        output_path: 처리된 자막 파일 저장 경로
        max_chars: 한 줄당 최대 문자 수 (기본 20자)
        
    Returns:
        str: 처리된 자막 파일 경로
    """
    try:
        import re
        
        print(f"📝 자막을 짧은 한 줄로 분할 중...")
        print(f"   원본: {os.path.basename(subtitle_file_path)}")
        print(f"   최대 문자 수: {max_chars}")
        
        # 원본 자막 파일 읽기
        with open(subtitle_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # SRT 형식 파싱 (번호, 시간, 텍스트)
        subtitle_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\n\d+\n|\Z)'
        matches = re.findall(subtitle_pattern, content, re.DOTALL)
        
        split_content = ""
        subtitle_number = 1
        
        for i, (number, timing, text) in enumerate(matches):
            # 텍스트 정리 (불필요한 공백 제거)
            clean_text = text.strip().replace('\n', ' ').replace('\r', ' ')
            clean_text = ' '.join(clean_text.split())
            
            # 시간 정보 파싱
            start_time, end_time = timing.split(' --> ')
            start_ms = time_to_ms(start_time)
            end_ms = time_to_ms(end_time)
            total_duration = end_ms - start_ms
            
            # 텍스트를 짧은 단위로 분할
            words = clean_text.split()
            chunks = []
            current_chunk = ""
            
            for word in words:
                test_chunk = current_chunk + (" " if current_chunk else "") + word
                if len(test_chunk) <= max_chars:
                    current_chunk = test_chunk
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = word
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # 각 청크를 별도의 자막으로 만들기 (한 줄씩 순차적으로)
            if chunks:
                # 각 줄의 시작과 끝 시간 계산 (겹치지 않게)
                min_chunk_duration = 1000  # 1초 = 1000ms
                
                # 전체 시간이 청크 수보다 적으면 시간을 늘림
                if total_duration < len(chunks) * min_chunk_duration:
                    total_duration = len(chunks) * min_chunk_duration
                    end_ms = start_ms + total_duration
                
                chunk_duration = max(min_chunk_duration, total_duration // len(chunks))
                
                for j, chunk in enumerate(chunks):
                    # 각 줄의 시작과 끝 시간 계산 (겹치지 않게)
                    chunk_start_ms = start_ms + (j * chunk_duration)
                    chunk_end_ms = start_ms + ((j + 1) * chunk_duration) - 100  # 100ms 간격
                    
                    # 마지막 청크는 원본 종료 시간 사용
                    if j == len(chunks) - 1:
                        chunk_end_ms = end_ms
                    
                    chunk_start_time = ms_to_time(chunk_start_ms)
                    chunk_end_time = ms_to_time(chunk_end_ms)
                    
                    # 자막 엔트리 생성
                    split_content += f"{subtitle_number}\n"
                    split_content += f"{chunk_start_time} --> {chunk_end_time}\n"
                    split_content += chunk
                    split_content += "\n\n"
                    
                    subtitle_number += 1
        
        # 분할된 자막 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(split_content.strip())
        
        print(f"✅ 짧은 한 줄 자막 파일 생성: {os.path.basename(output_path)}")
        return output_path
        
    except Exception as e:
        print(f"❌ 자막 분할 실패: {e}")
        # 실패 시 원본 파일 경로 반환
        return subtitle_file_path

def time_to_ms(time_str: str) -> int:
    """시간 문자열을 밀리초로 변환"""
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)

def ms_to_time(ms: int) -> str:
    """밀리초를 시간 문자열로 변환"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    ms_remainder = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms_remainder:03d}"

def create_sequential_subtitle_file(subtitle_file_path: str, output_path: str, max_chars: int = 12, line_duration: float = 0.8, gap_duration: float = 0.1) -> str:
    """
    기존 자막 파일을 읽어서 한 줄씩 순차적으로 나오는 자막 파일 생성
    각 줄이 완전히 끝나고 간격을 두고 다음 줄이 시작됨
    
    Args:
        subtitle_file_path: 원본 자막 파일 경로
        output_path: 처리된 자막 파일 저장 경로
        max_chars: 한 줄당 최대 문자 수 (기본 12자)
        line_duration: 각 줄의 표시 시간 (초, 기본 0.8초)
        gap_duration: 줄 사이의 간격 시간 (초, 기본 0.1초)
        
    Returns:
        str: 처리된 자막 파일 경로
    """
    try:
        import re
        
        print(f"📝 자막을 순차적 한 줄로 변환 중...")
        print(f"   원본: {os.path.basename(subtitle_file_path)}")
        print(f"   최대 문자 수: {max_chars}")
        print(f"   줄 표시 시간: {line_duration}초")
        print(f"   줄 간격: {gap_duration}초")
        
        # 원본 자막 파일 읽기
        with open(subtitle_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # SRT 형식 파싱 (번호, 시간, 텍스트)
        subtitle_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\n\d+\n|\Z)'
        matches = re.findall(subtitle_pattern, content, re.DOTALL)
        
        sequential_content = ""
        subtitle_number = 1
        current_time_ms = 0  # 현재 시간 (밀리초)
        
        for i, (number, timing, text) in enumerate(matches):
            # 텍스트 정리 (불필요한 공백 제거)
            clean_text = text.strip().replace('\n', ' ').replace('\r', ' ')
            clean_text = ' '.join(clean_text.split())
            
            if not clean_text:
                continue
            
            # 텍스트를 짧은 단위로 분할
            words = clean_text.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if len(test_line) <= max_chars:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # 각 줄을 순차적으로 배치
            for j, line in enumerate(lines):
                # 시작 시간
                start_ms = current_time_ms
                
                # 끝 시간 (글자 수에 따라 동적 조정 - 더 빠르게)
                char_count = len(line)
                # 한 글자당 0.06초 + 기본 0.5초 (최소 표시 시간)
                display_duration = max(0.5, char_count * 0.06)  
                # 최대 0.9초를 넘지 않도록 제한
                display_duration = min(display_duration, 0.9)
                
                end_ms = start_ms + int(display_duration * 1000)
                
                start_time = ms_to_time(start_ms)
                end_time = ms_to_time(end_ms)
                
                # 자막 엔트리 생성
                sequential_content += f"{subtitle_number}\n"
                sequential_content += f"{start_time} --> {end_time}\n"
                sequential_content += line
                sequential_content += "\n\n"
                
                # 다음 줄을 위한 시간 업데이트 (더 짧은 간격)
                current_time_ms = end_ms + int(gap_duration * 1000)
                subtitle_number += 1
        
        # 순차적 자막 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sequential_content.strip())
        
        print(f"✅ 순차적 자막 파일 생성: {os.path.basename(output_path)}")
        print(f"   총 {subtitle_number - 1}개 줄 생성")
        return output_path
        
    except Exception as e:
        print(f"❌ 순차적 자막 생성 실패: {e}")
        # 실패 시 원본 파일 경로 반환
        return subtitle_file_path

def create_video_with_drawtext_subtitles(
    video_file_path: str,
    subtitle_file_path: str, 
    output_video_path: str,
    font_size: int = 20
) -> SubtitleResult:
    """
    drawtext 필터를 사용하여 한국어 자막을 비디오에 추가
    
    Args:
        video_file_path: 원본 비디오 파일 경로
        subtitle_file_path: 자막 파일 경로
        output_video_path: 출력 비디오 파일 경로
        font_size: 폰트 크기
        
    Returns:
        SubtitleResult: 자막 합성 결과
    """
    try:
        print("🎨 drawtext 방식으로 한국어 자막 처리 중...")
        
        # 자막 파일 읽기
        with open(subtitle_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # SRT 형식 파싱
        import re
        subtitle_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\n\d+\n|\Z)'
        matches = re.findall(subtitle_pattern, content, re.DOTALL)
        
        # 한국어 폰트 후보들
        korean_fonts = [
            "C:/Windows/Fonts/malgun.ttf",   # 맑은 고딕
            "C:/Windows/Fonts/gulim.ttc",    # 굴림
            "C:/Windows/Fonts/batang.ttc",   # 바탕
        ]
        
        # 사용 가능한 폰트 찾기
        korean_font = None
        for font_path in korean_fonts:
            if os.path.exists(font_path):
                korean_font = font_path
                break
        
        if not korean_font:
            print("❌ 한국어 폰트를 찾을 수 없습니다.")
            return SubtitleResult(success=False, error="한국어 폰트를 찾을 수 없습니다.")
        
        print(f"✅ 사용할 한국어 폰트: {korean_font}")
        
        # drawtext 필터 생성
        drawtext_filters = []
        for i, (number, timing, text) in enumerate(matches):
            # 시간 파싱
            start_time, end_time = timing.split(' --> ')
            start_seconds = time_to_seconds(start_time)
            end_seconds = time_to_seconds(end_time)
            
            # 텍스트 정리
            clean_text = text.strip().replace('\n', ' ').replace("'", "\\'")
            
            # drawtext 필터 생성
            drawtext_filter = (
                f"drawtext=fontfile='{korean_font}'"
                f":text='{clean_text}'"
                f":fontcolor=white"
                f":fontsize={font_size}"
                f":x=(w-text_w)/2"
                f":y=h-80"
                f":enable='between(t,{start_seconds},{end_seconds})'"
            )
            drawtext_filters.append(drawtext_filter)
        
        if not drawtext_filters:
            print("❌ 처리할 자막이 없습니다.")
            return SubtitleResult(success=False, error="처리할 자막이 없습니다.")
        
        # 모든 drawtext 필터를 체인으로 연결
        vf_chain = ",".join(drawtext_filters)
        
        # FFmpeg 명령어 실행
        ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
        
        cmd = [
            ffmpeg_exe, "-y",
            "-i", video_file_path,
            "-vf", vf_chain,
            "-c:v", "libx264",
            "-c:a", "copy",
            output_video_path
        ]
        
        print(f"🔧 drawtext FFmpeg 명령어 실행 중...")
        
        # UTF-8 인코딩 환경에서 실행
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            env=env
        )
        
        if result.returncode == 0:
            print(f"✅ drawtext 방식 자막 합성 성공!")
            return SubtitleResult(
                success=True,
                video_with_subtitle_path=output_video_path,
                subtitle_file_path=subtitle_file_path
            )
        else:
            error_msg = f"drawtext FFmpeg 실행 실패: {result.stderr}"
            print(f"❌ {error_msg}")
            return SubtitleResult(success=False, error=error_msg)
            
    except Exception as e:
        error_msg = f"drawtext 자막 처리 중 오류: {e}"
        print(f"❌ {error_msg}")
        return SubtitleResult(success=False, error=error_msg)

def time_to_seconds(time_str: str) -> float:
    """SRT 시간 형식을 초 단위로 변환"""
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
