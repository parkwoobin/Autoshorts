"""
FastAPI 웹사이트용 TTS + 배경음악 + 자막 통합 API
"""
import asyncio
import os
import subprocess
import glob
import random
import time
from typing import Optional, Dict, Any
from subtitle_utils import create_tts_synced_subtitle_file, get_korean_subtitle_style, create_precise_whisper_subtitles
from tts_utils import create_tts_audio, get_elevenlabs_api_key

async def create_enhanced_video_with_tts_and_subtitles(
    video_file_path: str,
    tts_text: str,
    voice_id: str = '21m00Tcm4TlvDq8ikWAM',  # Rachel 음성
    font_size: int = 32,  # 32pt로 기본 크기 증가 (0.1초 정밀도용)
    max_chars_per_line: int = 6,
    tts_volume: float = 0.8,
    bgm_volume: float = 0.3,
    enable_bgm: bool = True,
    specific_bgm: Optional[str] = None,
    output_dir: str = "./static/videos"
) -> Dict[str, Any]:
    """
    비디오에 TTS 음성, 배경음악, 동기화된 자막을 모두 추가하는 통합 함수
    
    Args:
        video_file_path: 원본 비디오 파일 경로
        tts_text: TTS로 변환할 텍스트
        voice_id: ElevenLabs 음성 ID
        font_size: 자막 폰트 크기
        max_chars_per_line: 한 줄당 최대 문자 수
        tts_volume: TTS 음성 볼륨
        bgm_volume: 배경음악 볼륨
        enable_bgm: 배경음악 사용 여부
        specific_bgm: 특정 BGM 파일 경로 (None이면 랜덤)
        output_dir: 출력 디렉토리
        
    Returns:
        Dict[str, Any]: 처리 결과
    """
    try:
        print(f"🎬 TTS + 배경음악 + 자막 통합 비디오 생성 시작...")
        print(f"   원본 비디오: {os.path.basename(video_file_path)}")
        print(f"   TTS 텍스트: {tts_text[:50]}{'...' if len(tts_text) > 50 else ''}")
        
        # 입력 파일 검증
        if not os.path.exists(video_file_path):
            return {
                "success": False,
                "error": f"비디오 파일을 찾을 수 없습니다: {video_file_path}"
            }
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs("./static/audio", exist_ok=True)
        os.makedirs("./static/subtitles", exist_ok=True)
        
        timestamp = int(time.time())
        
        # 1단계: TTS 음성 생성
        print("\n🎙️ 1단계: TTS 음성 생성 중...")
        
        api_key = get_elevenlabs_api_key()
        if not api_key:
            return {
                "success": False,
                "error": "ElevenLabs API 키를 찾을 수 없습니다."
            }
            
        tts_result = await create_tts_audio(
            text=tts_text,
            voice_id=voice_id,
            api_key=api_key,
            output_dir="./static/audio"
        )
        
        if not tts_result.success:
            return {
                "success": False,
                "error": f"TTS 생성 실패: {tts_result.error}"
            }
            
        print(f"✅ TTS 음성 생성 완료: {os.path.basename(tts_result.audio_file_path)} ({tts_result.duration:.2f}초)")
        
        # 2단계: 배경음악 선택
        selected_bgm = None
        if enable_bgm:
            print("\n🎵 2단계: 배경음악 선택 중...")
            
            if specific_bgm and os.path.exists(specific_bgm):
                selected_bgm = specific_bgm
                print(f"✅ 지정된 BGM 사용: {os.path.basename(specific_bgm)}")
            else:
                bgm_files = glob.glob("./bgm/*.mp3") + glob.glob("./bgm/*.m4a")
                if bgm_files:
                    selected_bgm = random.choice(bgm_files)
                    print(f"✅ 랜덤 BGM 선택: {os.path.basename(selected_bgm)}")
                else:
                    print("⚠️ BGM 파일을 찾을 수 없습니다. BGM 없이 진행합니다.")
                    enable_bgm = False
        
        # 3단계: Whisper AI로 0.1초 단위 정밀 자막 생성
        print("\n📝 3단계: Whisper AI로 0.1초 단위 정밀 자막 생성 중...")
        
        whisper_result = await create_precise_whisper_subtitles(
            audio_file_path=tts_result.audio_file_path,
            output_dir="./static/subtitles",
            language="ko"
        )
        
        if not whisper_result["success"]:
            print(f"⚠️ Whisper 자막 생성 실패, 기본 자막으로 대체합니다.")
            # 기본 자막 생성으로 폴백
            synced_subtitle_path = f"./static/subtitles/tts_synced_subtitle_{timestamp}.srt"
            subtitle_file = create_tts_synced_subtitle_file(
                text=tts_text,
                tts_duration=tts_result.duration,
                output_path=synced_subtitle_path,
                max_chars=max_chars_per_line,
                min_duration=0.3,
                gap_duration=0.02
            )
        else:
            subtitle_file = whisper_result["subtitle_file_path"]
            print(f"✅ Whisper 정밀 자막 생성 완료: {os.path.basename(subtitle_file)}")
            print(f"   자막 개수: {whisper_result['subtitle_count']}개")
            print(f"   타이밍: {whisper_result['first_timing']} ~ {whisper_result['last_timing']}")
            print(f"   텍스트: {whisper_result['transcription'][:50]}{'...' if len(whisper_result['transcription']) > 50 else ''}")
        
        # 4단계: FFmpeg로 모든 요소 통합
        print("\n🎬 4단계: FFmpeg로 모든 요소 통합 중...")
        
        output_filename = f"enhanced_video_{timestamp}.mp4"
        output_video_path = os.path.join(output_dir, output_filename)
        
        # FFmpeg 명령어 구성
        ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
        
        # 자막 스타일과 경로 설정
        subtitle_style = get_korean_subtitle_style(font_size=font_size, enable_outline=True)
        subtitle_path_fixed = subtitle_file.replace("\\", "/").replace(":", "\\:")
        
        if enable_bgm and selected_bgm:
            # TTS + BGM + 자막 모두 포함
            cmd = [
                ffmpeg_exe, "-y",
                "-i", video_file_path,
                "-i", tts_result.audio_file_path,
                "-i", selected_bgm,
                "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{subtitle_style}'",
                "-filter_complex", f"[1:a]volume={tts_volume}[tts];[2:a]volume={bgm_volume}[bgm];[tts][bgm]amix=inputs=2:duration=first:dropout_transition=3[audio]",
                "-map", "0:v:0",
                "-map", "[audio]",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                output_video_path
            ]
            mode = "TTS + 배경음악 + 자막"
        else:
            # TTS + 자막만
            cmd = [
                ffmpeg_exe, "-y",
                "-i", video_file_path,
                "-i", tts_result.audio_file_path,
                "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{subtitle_style}'",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                output_video_path
            ]
            mode = "TTS + 자막"
        
        print(f"🔧 FFmpeg 실행 중... ({mode})")
        
        # FFmpeg 실행
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"FFmpeg 실행 실패: {result.stderr}",
                "tts_file": tts_result.audio_file_path,
                "subtitle_file": subtitle_file
            }
        
        # 생성 완료 검증
        if not os.path.exists(output_video_path) or os.path.getsize(output_video_path) == 0:
            return {
                "success": False,
                "error": "생성된 비디오 파일이 비어있거나 존재하지 않습니다.",
                "tts_file": tts_result.audio_file_path,
                "subtitle_file": subtitle_file
            }
        
        file_size = os.path.getsize(output_video_path)
        
        print(f"✅ 통합 비디오 생성 성공!")
        print(f"   출력 파일: {output_filename}")
        print(f"   파일 크기: {file_size:,} bytes")
        print(f"   모드: {mode}")
        
        # 임시 파일 정리 (선택적)
        try:
            # TTS 파일은 보관하고 자막 파일만 정리할지 결정
            pass
        except:
            pass
        
        return {
            "success": True,
            "output_video_path": output_video_path,
            "output_filename": output_filename,
            "file_size": file_size,
            "tts_duration": tts_result.duration,
            "tts_file": tts_result.audio_file_path,
            "subtitle_file": subtitle_file,
            "bgm_file": selected_bgm if enable_bgm else None,
            "mode": mode,
            "subtitle_method": "Whisper AI (0.1초 정밀도)" if 'whisper_result' in locals() and whisper_result["success"] else "기본 TTS 동기화",
            "subtitle_count": whisper_result.get("subtitle_count", "N/A") if 'whisper_result' in locals() and whisper_result["success"] else "N/A",
            "server_url": f"http://localhost:8000/static/videos/{output_filename}"
        }
        
    except Exception as e:
        error_msg = f"TTS + 자막 통합 처리 중 오류 발생: {e}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

# FastAPI 엔드포인트용 래퍼 함수
async def api_create_enhanced_video(
    video_path: str,
    text: str,
    voice_id: Optional[str] = None,
    font_size: int = 48,  # 48pt로 기본 크기 증가
    enable_bgm: bool = True
) -> Dict[str, Any]:
    """
    FastAPI에서 호출할 수 있는 간소화된 함수
    
    Args:
        video_path: 비디오 파일 경로
        text: TTS 텍스트
        voice_id: 음성 ID (None이면 기본값 사용)
        font_size: 폰트 크기
        enable_bgm: 배경음악 사용 여부
        
    Returns:
        Dict[str, Any]: 처리 결과
    """
    return await create_enhanced_video_with_tts_and_subtitles(
        video_file_path=video_path,
        tts_text=text,
        voice_id=voice_id or '21m00Tcm4TlvDq8ikWAM',
        font_size=font_size,
        max_chars_per_line=6,
        enable_bgm=enable_bgm
    )

# 테스트용 함수
async def test_api_function():
    """API 함수 테스트"""
    test_video = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
    test_text = "안녕하세요. 오늘은 특별한 날입니다. 우리가 함께하는 이 순간이 정말 소중합니다. 새로운 기술로 영상을 만들어보겠습니다."
    
    result = await api_create_enhanced_video(
        video_path=test_video,
        text=test_text,
        font_size=48,  # 48pt 테스트
        enable_bgm=True
    )
    
    print("\n🧪 Whisper AI (0.1초 정밀도) FastAPI 테스트 결과:")
    if result["success"]:
        print(f"✅ 성공!")
        print(f"   출력 파일: {result['output_filename']}")
        print(f"   서버 URL: {result['server_url']}")
        print(f"   파일 크기: {result['file_size']:,} bytes")
        print(f"   TTS 길이: {result['tts_duration']:.2f}초")
        print(f"   모드: {result['mode']}")
        print(f"   자막 방식: {result['subtitle_method']}")
        print(f"   자막 개수: {result['subtitle_count']}개")
    else:
        print(f"❌ 실패: {result['error']}")

if __name__ == "__main__":
    asyncio.run(test_api_function())
