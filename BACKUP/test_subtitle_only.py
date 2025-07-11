"""
TTS 없이 자막만 테스트
"""
import asyncio
import os
import subprocess

async def test_subtitle_only():
    """TTS 없이 자막만 테스트"""
    print("📝 자막만 테스트 시작...")
    
    # 기존 비디오 파일
    video_file = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
    
    if not os.path.exists(video_file):
        print(f"❌ 비디오 파일 없음: {video_file}")
        return
    
    # 직접 자막 파일 생성 (TTS 없이)
    subtitle_content = """1
00:00:00,000 --> 00:00:01,000
안녕하세요

2
00:00:01,100 --> 00:00:02,100
오늘은 특별한 날입니다

3
00:00:02,200 --> 00:00:03,200
우리가 함께하는

4
00:00:03,300 --> 00:00:04,300
이 순간이 정말

5
00:00:04,400 --> 00:00:05,400
소중합니다

6
00:00:05,500 --> 00:00:06,500
자막 테스트입니다
"""
    
    # 자막 파일 저장
    os.makedirs("./static/subtitles", exist_ok=True)
    import time
    timestamp = int(time.time())
    subtitle_file = f"./static/subtitles/subtitle_only_{timestamp}.srt"
    
    with open(subtitle_file, 'w', encoding='utf-8') as f:
        f.write(subtitle_content)
    
    print(f"📝 자막 파일 생성: {os.path.basename(subtitle_file)}")
    
    # 출력 비디오 경로
    output_video = f"./static/videos/subtitle_only_{timestamp}.mp4"
    
    # FFmpeg로 자막 합성 (음성 없이)
    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
    
    # Windows 경로 변환
    subtitle_file_escaped = subtitle_file.replace("\\", "\\\\").replace(":", "\\:")
    
    # 자막 스타일
    style = "FontSize=28,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=3,Shadow=2,Alignment=2,MarginV=40,Bold=1"
    
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_file,
        "-vf", f"subtitles='{subtitle_file_escaped}':force_style='{style}'",
        "-c:v", "libx264",
        "-c:a", "copy",  # 원본 오디오 유지
        output_video
    ]
    
    print(f"🔧 FFmpeg 실행 중...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 자막만 영상 생성 성공!")
            print(f"   경로: {output_video}")
            
            if os.path.exists(output_video):
                file_size = os.path.getsize(output_video)
                print(f"   파일 크기: {file_size:,} bytes")
                
                # 서버 URL
                server_url = f"http://localhost:8000/static/videos/{os.path.basename(output_video)}"
                print(f"   🌐 URL: {server_url}")
                
                print(f"\n🎉 TTS 없이 자막만으로 영상 완성!")
                print(f"   자막이 한 줄씩 1초간격으로 나타남")
            else:
                print("❌ 파일 생성 실패")
        else:
            print(f"❌ FFmpeg 실패: {result.stderr}")
    
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    asyncio.run(test_subtitle_only())
