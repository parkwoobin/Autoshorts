"""
자막이 확실히 나오는 테스트 영상 만들기
"""
import asyncio
import os
import subprocess

async def create_working_subtitle_video():
    """자막이 확실히 나오는 테스트 영상 생성"""
    print("🎬 자막이 확실히 나오는 영상 만들기...")
    
    # 기존 비디오 파일
    video_file = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
    
    if not os.path.exists(video_file):
        print(f"❌ 비디오 파일 없음: {video_file}")
        return
    
    # 더 간단한 자막 생성
    subtitle_content = """1
00:00:00,000 --> 00:00:02,000
안녕하세요! 첫 번째 자막입니다

2
00:00:02,100 --> 00:00:04,000
두 번째 자막이 나타났습니다

3
00:00:04,100 --> 00:00:06,000
세 번째 자막입니다

4
00:00:06,100 --> 00:00:08,000
네 번째 자막이 보입니다

5
00:00:08,100 --> 00:00:10,000
다섯 번째 마지막 자막입니다
"""
    
    # 자막 파일 저장
    os.makedirs("./static/subtitles", exist_ok=True)
    import time
    timestamp = int(time.time())
    subtitle_file = f"./static/subtitles/test_subtitle_{timestamp}.srt"
    
    with open(subtitle_file, 'w', encoding='utf-8') as f:
        f.write(subtitle_content)
    
    print(f"📝 간단한 자막 파일 생성: {os.path.basename(subtitle_file)}")
    
    # 출력 비디오 경로
    output_video = f"./static/videos/working_subtitle_{timestamp}.mp4"
    
    # FFmpeg 실행 (더 간단한 명령어)
    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
    
    # Windows 경로 변환
    subtitle_file_escaped = subtitle_file.replace("\\", "\\\\").replace(":", "\\:")
    
    # 기본 자막 스타일로 시도
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_file,
        "-vf", f"subtitles='{subtitle_file_escaped}':force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=30'",
        "-c:v", "libx264",
        "-c:a", "copy",
        output_video
    ]
    
    print(f"🔧 FFmpeg 실행: {' '.join(cmd[:5])}...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 자막 영상 생성 성공!")
            print(f"   경로: {output_video}")
            
            if os.path.exists(output_video):
                file_size = os.path.getsize(output_video)
                print(f"   파일 크기: {file_size:,} bytes")
                
                # 서버 URL
                server_url = f"http://localhost:8000/static/videos/{os.path.basename(output_video)}"
                print(f"   🌐 URL: {server_url}")
                
                print(f"\n🎉 이번엔 자막이 확실히 나올 겁니다!")
            else:
                print("❌ 파일이 생성되지 않았습니다.")
        else:
            print(f"❌ FFmpeg 실행 실패:")
            print(f"   Error: {result.stderr}")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(create_working_subtitle_video())
