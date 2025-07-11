"""
자막 폰트 크기를 작게 만들기
"""
import asyncio
import os
import subprocess

async def test_small_font_subtitle():
    """작은 폰트 자막 테스트"""
    print("📝 작은 폰트 자막 테스트...")
    
    # 기존 비디오 파일
    video_file = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
    
    if not os.path.exists(video_file):
        print(f"❌ 비디오 파일 없음: {video_file}")
        return
    
    # 작은 자막 테스트
    subtitle_content = """1
00:00:01,000 --> 00:00:02,000
작은 자막

2
00:00:02,100 --> 00:00:03,100
이제 작아요

3
00:00:03,200 --> 00:00:04,200
적당한 크기

4
00:00:04,300 --> 00:00:05,300
깔끔하죠?
"""
    
    # 자막 파일 저장
    os.makedirs("./static/subtitles", exist_ok=True)
    import time
    timestamp = int(time.time())
    subtitle_file = f"./static/subtitles/tiny_subtitle_{timestamp}.srt"
    
    with open(subtitle_file, 'w', encoding='utf-8') as f:
        f.write(subtitle_content)
    
    print(f"📝 작은 자막 파일 생성: {os.path.basename(subtitle_file)}")
    
    # 출력 비디오 경로
    output_video = f"./static/videos/tiny_subtitle_{timestamp}.mp4"
    
    # FFmpeg로 작은 자막 합성
    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
    
    # Windows 경로 변환
    subtitle_file_escaped = subtitle_file.replace("\\", "\\\\").replace(":", "\\:")
    
    # 작은 자막 스타일 (12 폰트)
    tiny_style = "FontSize=12,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=1,Shadow=1,Alignment=2,MarginV=20,Bold=0"
    
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_file,
        "-vf", f"subtitles='{subtitle_file_escaped}':force_style='{tiny_style}'",
        "-c:v", "libx264",
        "-c:a", "copy",
        output_video
    ]
    
    print(f"🔧 FFmpeg로 작은 자막 처리 중...")
    print(f"   폰트 크기: 12 (작게)")
    print(f"   굵기: 일반")
    print(f"   외곽선: 얇게")
    print(f"   여백: 최소화")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 작은 자막 영상 생성 성공!")
            print(f"   경로: {output_video}")
            
            if os.path.exists(output_video):
                file_size = os.path.getsize(output_video)
                print(f"   파일 크기: {file_size:,} bytes")
                
                # 서버 URL
                server_url = f"http://localhost:8000/static/videos/{os.path.basename(output_video)}"
                print(f"   🌐 URL: {server_url}")
                
                print(f"\n🎉 이제 자막이 작고 깔끔합니다!")
                print(f"   - 폰트 크기: 12 (작음)")
                print(f"   - 일반 굵기")
                print(f"   - 얇은 외곽선")
                print(f"   - 최소 여백")
            else:
                print("❌ 파일 생성 실패")
        else:
            print(f"❌ FFmpeg 실패: {result.stderr}")
    
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    asyncio.run(test_small_font_subtitle())
