"""
ElevenLabs TTS 기능 테스트 및 영상에 적용
"""
import os
import asyncio
from tts_utils import create_tts_audio, get_elevenlabs_api_key
import subprocess

async def test_tts_with_video():
    """TTS 생성 후 영상에 적용 테스트"""
    try:
        print("🎙️ ElevenLabs TTS 테스트 시작...")
        
        # API 키 확인
        api_key = get_elevenlabs_api_key()
        if not api_key:
            print("❌ ElevenLabs API 키를 찾을 수 없습니다.")
            return
        
        print(f"✅ API 키 확인: {api_key[:10]}...")
        
        # 1. TTS 오디오 생성
        test_text = "안녕하세요 여러분! 오늘은 정말 좋은 날이네요. 함께 즐거운 시간을 보내봅시다."
        
        print(f"📝 TTS 생성 중...")
        print(f"   텍스트: {test_text}")
        
        tts_result = await create_tts_audio(
            text=test_text,
            voice_id="9BWtsMINqrJLrRacOk9x",  # Aria 음성
            api_key=api_key,
            output_dir="./static/audio"
        )
        
        if tts_result.success:
            print(f"✅ TTS 생성 성공!")
            print(f"   오디오 파일: {tts_result.audio_file_path}")
            print(f"   지속 시간: {tts_result.duration}초")
            
            # 2. 원본 영상에 TTS 오디오 추가
            video_path = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
            
            if not os.path.exists(video_path):
                print(f"❌ 원본 영상을 찾을 수 없습니다: {video_path}")
                return
            
            print(f"\n🎬 TTS 오디오를 영상에 추가 중...")
            
            import time
            timestamp = int(time.time())
            output_filename = f"frame_transitions_with_tts_{timestamp}.mp4"
            output_path = os.path.join("D:\\shortpilot\\static\\videos", output_filename)
            
            # FFmpeg로 TTS 오디오를 영상에 추가
            ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
            
            tts_cmd = [
                ffmpeg_exe, "-y",
                "-i", video_path,           # 입력 비디오
                "-i", tts_result.audio_file_path,  # 입력 오디오 (TTS)
                "-c:v", "copy",             # 비디오 복사
                "-c:a", "aac",              # 오디오 코덱
                "-map", "0:v:0",            # 비디오 스트림
                "-map", "1:a:0",            # 오디오 스트림 (TTS)
                "-shortest",                # 짧은 것에 맞춤
                output_path
            ]
            
            print(f"🔧 FFmpeg 명령어 실행 중...")
            
            result = subprocess.run(tts_cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✅ TTS 오디오 추가 성공!")
                print(f"   출력 파일: {output_filename}")
                print(f"   파일 크기: {file_size:,} bytes")
                print(f"   절대 경로: {output_path}")
                
                # 3. TTS가 추가된 영상에 영어 자막도 추가
                print(f"\n📝 TTS 영상에 자막도 추가 중...")
                
                subtitle_output = output_path.replace(".mp4", "_with_subtitles.mp4")
                
                subtitle_cmd = [
                    ffmpeg_exe, "-y",
                    "-i", output_path,
                    "-vf", (
                        "drawtext=text='Hello Everyone':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-80:enable='between(t,0,3)',"
                        "drawtext=text='Today is a good day':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-80:enable='between(t,3,6)',"
                        "drawtext=text='Let us have fun together':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-80:enable='between(t,6,9)'"
                    ),
                    "-c:v", "libx264",
                    "-c:a", "copy",
                    subtitle_output
                ]
                
                subtitle_result = subprocess.run(subtitle_cmd, capture_output=True, text=True)
                
                if subtitle_result.returncode == 0:
                    print(f"✅ TTS + 자막 완성!")
                    print(f"   최종 파일: {os.path.basename(subtitle_output)}")
                    print(f"   파일 크기: {os.path.getsize(subtitle_output):,} bytes")
                else:
                    print(f"⚠️ 자막 추가는 실패했지만 TTS는 성공")
                
            else:
                print(f"❌ TTS 오디오 추가 실패")
                if result.stderr:
                    print(f"   오류: {result.stderr[:200]}...")
        
        else:
            print(f"❌ TTS 생성 실패: {tts_result.error}")
        
    except Exception as e:
        print(f"❌ TTS 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tts_with_video())
