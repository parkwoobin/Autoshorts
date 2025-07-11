"""
한 줄씩 빠르고 촘촘한 자막 최종 버전
"""
import asyncio
import os
import subprocess

async def create_final_sequential_subtitle():
    """한 줄씩 빠르고 촘촘한 자막 최종 생성"""
    print("🎬 한 줄씩 빠르고 촘촘한 자막 최종 생성...")
    
    # 기존 비디오 파일
    video_file = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
    
    # 한 줄씩 빠르게 나오는 자막 생성
    subtitle_content = """1
00:00:00,000 --> 00:00:00,500
안녕하세요

2
00:00:00,600 --> 00:00:01,100
오늘은 특별한

3
00:00:01,200 --> 00:00:01,700
날입니다

4
00:00:01,800 --> 00:00:02,300
우리가 함께

5
00:00:02,400 --> 00:00:02,900
하는 이 순간이

6
00:00:03,000 --> 00:00:03,500
정말 소중합니다

7
00:00:03,600 --> 00:00:04,100
새로운 기술로

8
00:00:04,200 --> 00:00:04,700
영상을 만들어

9
00:00:04,800 --> 00:00:05,300
보겠습니다

10
00:00:05,400 --> 00:00:05,900
자막이 한 줄씩

11
00:00:06,000 --> 00:00:06,500
나타나는 것을

12
00:00:06,600 --> 00:00:07,100
확인해보세요
"""
    
    # 자막 파일 저장
    os.makedirs("./static/subtitles", exist_ok=True)
    import time
    timestamp = int(time.time())
    subtitle_file = f"./static/subtitles/final_sequential_{timestamp}.srt"
    
    with open(subtitle_file, 'w', encoding='utf-8') as f:
        f.write(subtitle_content)
    
    print(f"📝 한 줄씩 빠른 자막 생성: {os.path.basename(subtitle_file)}")
    
    # 출력 비디오 경로
    output_video = f"./static/videos/final_sequential_{timestamp}.mp4"
    
    # FFmpeg 실행
    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
    
    # Windows 경로 변환
    subtitle_file_escaped = subtitle_file.replace("\\", "\\\\").replace(":", "\\:")
    
    # 크고 굵은 자막 스타일
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_file,
        "-vf", f"subtitles='{subtitle_file_escaped}':force_style='FontSize=28,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=3,Shadow=2,Alignment=2,MarginV=40,Bold=1'",
        "-c:v", "libx264",
        "-c:a", "copy",
        output_video
    ]
    
    print(f"🔧 FFmpeg로 한 줄씩 자막 처리 중...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 한 줄씩 자막 영상 완성!")
            print(f"   경로: {output_video}")
            
            if os.path.exists(output_video):
                file_size = os.path.getsize(output_video)
                print(f"   파일 크기: {file_size:,} bytes")
                
                # 서버 URL
                server_url = f"http://localhost:8000/static/videos/{os.path.basename(output_video)}"
                print(f"   🌐 URL: {server_url}")
                
                print(f"\n🎉 이제 자막이 한 줄씩 빠르고 촘촘하게 나옵니다!")
                print(f"   - 각 줄이 0.5초씩 표시")
                print(f"   - 0.1초 간격으로 다음 줄 등장")
                print(f"   - 총 12개 라인 순차 표시")
            else:
                print("❌ 파일 생성 실패")
        else:
            print(f"❌ FFmpeg 실패: {result.stderr}")
    
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    asyncio.run(create_final_sequential_subtitle())
