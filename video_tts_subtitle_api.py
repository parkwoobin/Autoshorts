"""
FastAPI 웹사이트용 TTS + 배경음악 + 자막 통합 API
"""
import asyncio
import os
import subprocess
import glob
import random
import time
from typing import Optional, Dict, Any, List
from subtitle_utils import (
    create_tts_synced_subtitle_file, 
    get_korean_subtitle_style, 
    create_precise_whisper_subtitles,
    create_srt_list_file,
    read_srt_list_file,
    merge_srt_files_sequentially,
    cleanup_srt_list_file
)
from tts_utils import create_tts_audio, get_elevenlabs_api_key

async def create_multiple_videos_with_sequential_subtitles(
    video_files: List[str],
    tts_texts: List[str],
    voice_id: str = '21m00Tcm4TlvDq8ikWAM',
    font_size: int = 30,
    max_chars_per_line: int = 6,
    tts_volume: float = 0.8,
    bgm_volume: float = 0.4,
    enable_bgm: bool = True,
    specific_bgm: Optional[str] = None,
    output_dir: str = "./static/videos",
    enable_subtitle_outline: bool = True,  # 자막 외곽선 사용 여부
    subtitle_font_name: str = "Malgun Gothic"  # 자막 폰트명 (subtitle_utils.py와 동일)
) -> Dict[str, Any]:
    """
    여러 비디오에 대해 TTS와 자막을 생성하고, srt_list.txt로 관리하여 순서대로 합치는 함수
    자막 스타일은 subtitle_utils.py의 get_korean_subtitle_style()과 동일하게 설정됩니다.
    
    Args:
        video_files: 비디오 파일 경로 리스트
        tts_texts: TTS 텍스트 리스트
        voice_id: ElevenLabs 음성 ID
        font_size: 자막 폰트 크기 (기본 30pt, subtitle_utils.py와 동일)
        max_chars_per_line: 한 줄당 최대 문자 수
        tts_volume: TTS 음성 볼륨
        bgm_volume: 배경음악 볼륨
        enable_bgm: 배경음악 사용 여부
        specific_bgm: 특정 BGM 파일 경로
        output_dir: 출력 디렉토리
        enable_subtitle_outline: 자막 외곽선 사용 여부 (기본 True)
        subtitle_font_name: 자막 폰트명 (기본 "Malgun Gothic")
        
    Returns:
        Dict[str, Any]: 처리 결과
    """
    try:
        print(f"🎬 다중 비디오 TTS + 자막 처리 시작...")
        print(f"   비디오 파일: {len(video_files)}개")
        print(f"   TTS 텍스트: {len(tts_texts)}개")
        
        if len(video_files) != len(tts_texts):
            return {
                "success": False,
                "error": f"비디오 파일 개수({len(video_files)})와 TTS 텍스트 개수({len(tts_texts)})가 일치하지 않습니다."
            }
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs("./static/audio", exist_ok=True)
        os.makedirs("./static/subtitles", exist_ok=True)
        
        timestamp = int(time.time())
        
        # 1단계: 모든 TTS 음성 생성
        print("\n🎙️ 1단계: 모든 TTS 음성 생성 중...")
        
        api_key = get_elevenlabs_api_key()
        if not api_key:
            return {
                "success": False,
                "error": "ElevenLabs API 키를 찾을 수 없습니다."
            }
        
        tts_results = []
        for i, text in enumerate(tts_texts):
            print(f"   TTS {i+1}/{len(tts_texts)}: {text[:30]}{'...' if len(text) > 30 else ''}")
            
            tts_result = await create_tts_audio(
                text=text,
                voice_id=voice_id,
                api_key=api_key,
                output_dir="./static/audio"
            )
            
            if not tts_result.success:
                return {
                    "success": False,
                    "error": f"TTS {i+1} 생성 실패: {tts_result.error}"
                }
            
            tts_results.append(tts_result)
            print(f"   ✅ TTS {i+1} 완료: {os.path.basename(tts_result.audio_file_path)} ({tts_result.duration:.2f}초)")
        
        # 2단계: 모든 자막 생성 및 srt_list.txt 생성
        print("\n📝 2단계: 모든 자막 생성 및 SRT 목록 생성 중...")
        
        srt_files = []
        for i, (text, tts_result) in enumerate(zip(tts_texts, tts_results)):
            print(f"   자막 {i+1}/{len(tts_texts)} 생성 중...")
            
            # Whisper AI로 정밀 자막 생성 시도
            whisper_result = await create_precise_whisper_subtitles(
                audio_file_path=tts_result.audio_file_path,
                output_dir="./static/subtitles",
                language="ko"
            )
            
            if whisper_result["success"]:
                subtitle_file = whisper_result["subtitle_file_path"]
                print(f"   ✅ Whisper 자막 {i+1} 완료: {os.path.basename(subtitle_file)}")
            else:
                # 기본 자막 생성으로 폴백
                synced_subtitle_path = f"./static/subtitles/tts_synced_subtitle_{timestamp}_{i+1}.srt"
                subtitle_file = create_tts_synced_subtitle_file(
                    text=text,
                    tts_duration=tts_result.duration,
                    output_path=synced_subtitle_path,
                    max_chars=max_chars_per_line,
                    min_duration=0.3,
                    gap_duration=0.02
                )
                print(f"   ✅ 기본 자막 {i+1} 완료: {os.path.basename(subtitle_file)}")
            
            srt_files.append(subtitle_file)
        
        # SRT 목록 파일 생성
        srt_list_file = "srt_list.txt"
        create_srt_list_file(srt_files, srt_list_file)
        
        # 3단계: SRT 파일들을 순서대로 합치기
        print("\n🔄 3단계: SRT 파일들을 순서대로 합치는 중...")
        
        merged_subtitle_file = merge_srt_files_sequentially(
            srt_list_file=srt_list_file,
            output_path=f"./static/subtitles/merged_subtitles_{timestamp}.srt"
        )
        
        # 4단계: 배경음악 선택
        selected_bgm = None
        if enable_bgm:
            print("\n🎵 4단계: 배경음악 선택 중...")
            
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
        
        # 5단계: 첫 번째 비디오에 모든 요소 통합 (예시)
        print("\n🎬 5단계: 첫 번째 비디오에 모든 요소 통합 중...")
        
        # 첫 번째 비디오 파일 사용
        primary_video = video_files[0]
        
        output_filename = f"enhanced_multiple_video_{timestamp}.mp4"
        output_video_path = os.path.join(output_dir, output_filename)
        
        # FFmpeg 명령어 구성
        ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
        
        # 자막 스타일과 경로 설정 (subtitle_utils.py와 동일한 설정 사용)
        subtitle_style = get_korean_subtitle_style(
            font_size=font_size, 
            enable_outline=enable_subtitle_outline
        )
        subtitle_path_fixed = merged_subtitle_file.replace("\\", "/").replace(":", "\\:")
        
        print(f"📝 자막 스타일 설정:")
        print(f"   폰트 크기: {font_size}pt")
        print(f"   폰트: {subtitle_font_name}")
        print(f"   외곽선: {'사용' if enable_subtitle_outline else '미사용'}")
        if enable_subtitle_outline:
            print(f"   외곽선: 검은색, 두께 4px, 그림자 3px")
        
        # 첫 번째 TTS 파일 사용
        primary_tts = tts_results[0].audio_file_path
        
        if enable_bgm and selected_bgm:
            # TTS + BGM + 자막 모두 포함
            cmd = [
                ffmpeg_exe, "-y",
                "-i", primary_video,
                "-i", primary_tts,
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
            mode = "다중 TTS + 배경음악 + 순차 자막"
        else:
            # TTS + 자막만
            cmd = [
                ffmpeg_exe, "-y",
                "-i", primary_video,
                "-i", primary_tts,
                "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{subtitle_style}'",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                output_video_path
            ]
            mode = "다중 TTS + 순차 자막"
        
        print(f"🔧 FFmpeg 실행 중... ({mode})")
        
        # FFmpeg 실행
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"FFmpeg 실행 실패: {result.stderr}",
                "tts_files": [tts.audio_file_path for tts in tts_results],
                "srt_files": srt_files,
                "merged_subtitle_file": merged_subtitle_file
            }
        
        # 생성 완료 검증
        if not os.path.exists(output_video_path) or os.path.getsize(output_video_path) == 0:
            return {
                "success": False,
                "error": "생성된 비디오 파일이 비어있거나 존재하지 않습니다.",
                "tts_files": [tts.audio_file_path for tts in tts_results],
                "srt_files": srt_files,
                "merged_subtitle_file": merged_subtitle_file
            }
        
        file_size = os.path.getsize(output_video_path)
        
        # 6단계: srt_list.txt 파일 정리
        print("\n🗑️ 6단계: SRT 목록 파일 정리 중...")
        cleanup_srt_list_file(srt_list_file)
        
        print(f"✅ 다중 비디오 TTS + 자막 처리 성공!")
        print(f"   출력 파일: {output_filename}")
        print(f"   파일 크기: {file_size:,} bytes")
        print(f"   모드: {mode}")
        print(f"   처리된 TTS: {len(tts_results)}개")
        print(f"   처리된 자막: {len(srt_files)}개")
        
        return {
            "success": True,
            "output_video_path": output_video_path,
            "output_filename": output_filename,
            "file_size": file_size,
            "total_tts_count": len(tts_results),
            "total_subtitle_count": len(srt_files),
            "tts_files": [tts.audio_file_path for tts in tts_results],
            "individual_srt_files": srt_files,
            "merged_subtitle_file": merged_subtitle_file,
            "bgm_file": selected_bgm if enable_bgm else None,
            "mode": mode,
            "server_url": f"http://localhost:8000/static/videos/{output_filename}",
            "srt_list_cleaned": True
        }
        
    except Exception as e:
        # 오류 발생 시에도 srt_list.txt 정리
        try:
            cleanup_srt_list_file("srt_list.txt")
        except:
            pass
            
        error_msg = f"다중 비디오 TTS + 자막 처리 중 오류 발생: {e}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

async def create_enhanced_video_with_tts_and_subtitles(
    video_file_path: str,
    tts_text: str,
    voice_id: str = '21m00Tcm4TlvDq8ikWAM',  # Rachel 음성
    font_size: int = 30,  # 30pt로 기본 크기 (subtitle_utils.py와 동일)
    max_chars_per_line: int = 6,
    tts_volume: float = 0.8,
    bgm_volume: float = 0.4,
    enable_bgm: bool = True,
    specific_bgm: Optional[str] = None,
    output_dir: str = "./static/videos",
    enable_subtitle_outline: bool = True,  # 자막 외곽선 사용 여부
    subtitle_font_name: str = "Malgun Gothic"  # 자막 폰트명 (subtitle_utils.py와 동일)
) -> Dict[str, Any]:
    """
    비디오에 TTS 음성, 배경음악, 동기화된 자막을 모두 추가하는 통합 함수
    자막 스타일은 subtitle_utils.py의 get_korean_subtitle_style()과 동일하게 설정됩니다.
    
    Args:
        video_file_path: 원본 비디오 파일 경로
        tts_text: TTS로 변환할 텍스트
        voice_id: ElevenLabs 음성 ID
        font_size: 자막 폰트 크기 (기본 30pt, subtitle_utils.py와 동일)
        max_chars_per_line: 한 줄당 최대 문자 수
        tts_volume: TTS 음성 볼륨
        bgm_volume: 배경음악 볼륨
        enable_bgm: 배경음악 사용 여부
        specific_bgm: 특정 BGM 파일 경로 (None이면 랜덤)
        output_dir: 출력 디렉토리
        enable_subtitle_outline: 자막 외곽선 사용 여부 (기본 True)
        subtitle_font_name: 자막 폰트명 (기본 "Malgun Gothic")
        
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
        
        # 3.5단계: SRT 목록 파일 생성 (단일 자막이지만 통일성을 위해)
        print("\n📝 3.5단계: SRT 목록 파일 생성 중...")
        srt_list_file = "srt_list.txt"
        create_srt_list_file([subtitle_file], srt_list_file)
        
        # 4단계: FFmpeg로 모든 요소 통합
        print("\n🎬 4단계: FFmpeg로 모든 요소 통합 중...")
        
        output_filename = f"enhanced_video_{timestamp}.mp4"
        output_video_path = os.path.join(output_dir, output_filename)
        
        # FFmpeg 명령어 구성
        ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
        
        # 자막 스타일과 경로 설정 (subtitle_utils.py와 동일한 설정 사용)
        subtitle_style = get_korean_subtitle_style(
            font_size=font_size, 
            enable_outline=enable_subtitle_outline
        )
        subtitle_path_fixed = subtitle_file.replace("\\", "/").replace(":", "\\:")
        
        print(f"📝 자막 스타일 설정:")
        print(f"   폰트 크기: {font_size}pt")
        print(f"   폰트: {subtitle_font_name}")
        print(f"   외곽선: {'사용' if enable_subtitle_outline else '미사용'}")
        if enable_subtitle_outline:
            print(f"   외곽선: 검은색, 두께 4px, 그림자 3px")
        
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
        
        # 5단계: srt_list.txt 파일 정리
        print("\n🗑️ 5단계: SRT 목록 파일 정리 중...")
        cleanup_srt_list_file(srt_list_file)
        
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
            "server_url": f"http://localhost:8000/static/videos/{output_filename}",
            "srt_list_cleaned": True
        }
        
    except Exception as e:
        # 오류 발생 시에도 srt_list.txt 정리
        try:
            cleanup_srt_list_file("srt_list.txt")
        except:
            pass
            
        error_msg = f"TTS + 자막 통합 처리 중 오류 발생: {e}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

# FastAPI 엔드포인트용 래퍼 함수들
async def api_create_enhanced_video(
    video_path: str,
    text: str,
    voice_id: Optional[str] = None,
    font_size: int = 30,  # subtitle_utils.py와 동일한 기본값으로 변경
    enable_bgm: bool = True
) -> Dict[str, Any]:
    """
    FastAPI에서 호출할 수 있는 간소화된 함수 (단일 비디오)
    자막 스타일은 subtitle_utils.py와 완전히 동일하게 설정됩니다.
    
    Args:
        video_path: 비디오 파일 경로
        text: TTS 텍스트
        voice_id: 음성 ID (None이면 기본값 사용)
        font_size: 폰트 크기 (기본 30pt, subtitle_utils.py와 동일)
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
        enable_bgm=enable_bgm,
        enable_subtitle_outline=True,  # subtitle_utils.py와 동일
        subtitle_font_name="Malgun Gothic"  # subtitle_utils.py와 동일
    )

async def api_create_multiple_enhanced_videos(
    video_paths: List[str],
    texts: List[str],
    voice_id: Optional[str] = None,
    font_size: int = 30,  # subtitle_utils.py와 동일한 기본값으로 변경
    enable_bgm: bool = True
) -> Dict[str, Any]:
    """
    FastAPI에서 호출할 수 있는 간소화된 함수 (다중 비디오)
    자막 스타일은 subtitle_utils.py와 완전히 동일하게 설정됩니다.
    
    Args:
        video_paths: 비디오 파일 경로 리스트
        texts: TTS 텍스트 리스트
        voice_id: 음성 ID (None이면 기본값 사용)
        font_size: 폰트 크기 (기본 30pt, subtitle_utils.py와 동일)
        enable_bgm: 배경음악 사용 여부
        
    Returns:
        Dict[str, Any]: 처리 결과
    """
    return await create_multiple_videos_with_sequential_subtitles(
        video_files=video_paths,
        tts_texts=texts,
        voice_id=voice_id or '21m00Tcm4TlvDq8ikWAM',
        font_size=font_size,
        max_chars_per_line=6,
        enable_bgm=enable_bgm,
        enable_subtitle_outline=True,  # subtitle_utils.py와 동일
        subtitle_font_name="Malgun Gothic"  # subtitle_utils.py와 동일
    )
