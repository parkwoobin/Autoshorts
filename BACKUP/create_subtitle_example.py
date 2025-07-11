"""
기존 비디오로 TTS + 배경음악 + 자막 통합 비디오 만들기
"""
import asyncio
import os
import subprocess
import glob
import random
from subtitle_utils import create_precise_whisper_subtitles, get_korean_subtitle_style
from tts_utils import create_tts_audio, get_elevenlabs_api_key

async def create_tts_bgm_subtitle_video():
    """기존 비디오 파일에 TTS + 배경음악 + 자막 통합"""
    print("🎬 TTS + 배경음악 + 자막 통합 비디오 생성 시작...")
    
    # 기존 비디오 파일
    video_file = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
    
    if not os.path.exists(video_file):
        print(f"❌ 비디오 파일을 찾을 수 없습니다: {video_file}")
        return
    
    print(f"✅ 사용할 비디오: {os.path.basename(video_file)}")
    
    # TTS 텍스트
    tts_text = "안녕하세요. 오늘은 특별한 날입니다. 우리가 함께하는 이 순간이 정말 소중합니다. 새로운 기술로 영상을 만들어보겠습니다. TTS 음성과 자막이 함께 나타나는 것을 확인해보세요."
    
    print(f"🎙️ TTS 텍스트: {tts_text}")
    
    # 1단계: TTS 음성 생성
    print("\n🎙️ 1단계: TTS 음성 생성 중...")
    
    try:
        api_key = get_elevenlabs_api_key()
        if not api_key:
            print("❌ ElevenLabs API 키를 찾을 수 없습니다.")
            return
            
        tts_result = await create_tts_audio(
            text=tts_text,
            voice_id='21m00Tcm4TlvDq8ikWAM',  # Rachel 음성
            api_key=api_key,
            output_dir="./static/audio"
        )
        
        if not tts_result.success:
            print(f"❌ TTS 생성 실패: {tts_result.error}")
            return
            
        print(f"✅ TTS 음성 생성 완료: {os.path.basename(tts_result.audio_file_path)}")
        
    except Exception as e:
        print(f"❌ TTS 생성 중 오류: {e}")
        return
    
    # 2단계: 배경음악 선택
    print("\n🎵 2단계: 배경음악 선택 중...")
    
    bgm_files = glob.glob("./bgm/*.mp3") + glob.glob("./bgm/*.m4a")
    if bgm_files:
        selected_bgm = random.choice(bgm_files)
        print(f"✅ 선택된 BGM: {os.path.basename(selected_bgm)}")
    else:
        print("⚠️ BGM 파일을 찾을 수 없습니다. BGM 없이 진행합니다.")
        selected_bgm = None
    
    
    # 3단계: Whisper AI로 정확한 타이밍 자막 생성
    print("\n📝 3단계: Whisper AI로 정밀 타이밍 자막 생성 중...")
    
    # 자막 파일 저장
    os.makedirs("./static/subtitles", exist_ok=True)
    
    # Whisper API로 정확한 타이밍의 SRT 자막 생성
    whisper_result = await create_precise_whisper_subtitles(
        audio_file_path=tts_result.audio_file_path,
        output_dir="./static/subtitles",
        language="ko"
    )
    
    if not whisper_result["success"]:
        print(f"❌ Whisper 자막 생성 실패: {whisper_result['error']}")
        return
    
    result_file = whisper_result["subtitle_file_path"]
    
    print(f"📝 Whisper 정밀 자막 생성 완료: {whisper_result['subtitle_filename']}")
    print(f"   자막 개수: {whisper_result['subtitle_count']}개")
    print(f"   실제 텍스트: {whisper_result['transcription'][:100]}...")
    
    # 4단계: FFmpeg로 모든 요소 통합
    print("\n🎬 4단계: FFmpeg로 TTS + 배경음악 + Whisper 자막 통합 중...")
    
    # 최종 출력 비디오 경로
    import time
    timestamp = int(time.time())
    output_video = f"./static/videos/final_whisper_tts_bgm_{timestamp}.mp4"
    
    # FFmpeg 명령어 구성
    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
    
    # 자막 스타일과 경로 설정 (훨씬 큰 폰트 크기 사용)
    subtitle_style = get_korean_subtitle_style(font_size=48, enable_outline=True)
    subtitle_path_fixed = result_file.replace("\\", "/").replace(":", "\\:")
    
    if selected_bgm:
        # TTS + BGM + 자막 모두 포함
        cmd = [
            ffmpeg_exe, "-y",
            "-i", video_file,        # 원본 비디오
            "-i", tts_result.audio_file_path,  # TTS 음성
            "-i", selected_bgm,      # 배경음악
            "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{subtitle_style}'",  # 자막
            "-filter_complex", "[1:a]volume=0.8[tts];[2:a]volume=0.3[bgm];[tts][bgm]amix=inputs=2:duration=first:dropout_transition=3[audio]",  # 오디오 믹싱
            "-map", "0:v:0",         # 비디오 스트림
            "-map", "[audio]",       # 믹싱된 오디오
            "-c:v", "libx264",       # 비디오 재인코딩 (자막 때문에)
            "-c:a", "aac",           # 오디오 코덱
            "-shortest",             # 짧은 것에 맞춤
            output_video
        ]
        print(f"🎵 TTS + 배경음악 + Whisper 자막 모드")
    else:
        # TTS + 자막만
        cmd = [
            ffmpeg_exe, "-y",
            "-i", video_file,        # 원본 비디오
            "-i", tts_result.audio_file_path,  # TTS 음성
            "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{subtitle_style}'",  # 자막
            "-map", "0:v:0",         # 비디오 스트림
            "-map", "1:a:0",         # TTS 오디오
            "-c:v", "libx264",       # 비디오 재인코딩
            "-c:a", "aac",           # 오디오 코덱
            "-shortest",
            output_video
        ]
        print(f"🎙️ TTS + Whisper 자막 모드")
    
    print(f"🔧 FFmpeg 실행 중...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 통합 비디오 생성 성공!")
            print(f"   경로: {output_video}")
            
            if os.path.exists(output_video):
                file_size = os.path.getsize(output_video)
                print(f"   파일 크기: {file_size:,} bytes")
                print(f"\n🎉 TTS + 배경음악 + Whisper 자막 통합 완료!")
                print(f"   🎙️ TTS 음성: 포함")
                print(f"   🎵 배경음악: {'포함' if selected_bgm else '없음'}")
                print(f"   📝 Whisper AI 자막: 포함 ({whisper_result['subtitle_count']}개)")
                
                # 서버 URL로 접근 가능한 경로 생성
                server_url = f"http://localhost:8000/static/videos/{os.path.basename(output_video)}"
                print(f"   🌐 서버 URL: {server_url}")
                return output_video
        else:
            print(f"❌ FFmpeg 실행 실패:")
            print(f"   stderr: {result.stderr}")
    
    except Exception as e:
        print(f"❌ 비디오 생성 중 오류: {e}")

if __name__ == "__main__":
    asyncio.run(create_tts_bgm_subtitle_video())
