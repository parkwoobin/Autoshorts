"""
자막이 확실히 보이는 테스트
"""
import asyncio
import os
import subprocess

async def test_visible_subtitle():
    """자막이 확실히 보이는 테스트"""
    print("📝 자막 확실히 보이게 테스트...")
    
    # 기존 비디오 파일
    video_file = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
    
    if not os.path.exists(video_file):
        print(f"❌ 비디오 파일 없음: {video_file}")
        return
    
    # 더 큰 자막으로 테스트
    subtitle_content = """1
00:00:01,000 --> 00:00:03,000
큰 자막 테스트

2
00:00:03,500 --> 00:00:05,500
이제 보이나요?

3
00:00:06,000 --> 00:00:08,000
확실히 보이는 자막

4
00:00:08,500 --> 00:00:10,500
마지막 테스트
"""
    
    # 자막 파일 저장
    os.makedirs("./static/subtitles", exist_ok=True)
    import time
    timestamp = int(time.time())
    subtitle_file = f"./static/subtitles/visible_subtitle_{timestamp}.srt"
    
    with open(subtitle_file, 'w', encoding='utf-8') as f:
        f.write(subtitle_content)
    
    print(f"📝 큰 자막 파일 생성: {os.path.basename(subtitle_file)}")
    
    # 출력 비디오 경로
    output_video = f"./static/videos/visible_subtitle_{timestamp}.mp4"
    
    # FFmpeg로 큰 자막 합성
    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
    
    # Windows 경로 변환
    subtitle_file_escaped = subtitle_file.replace("\\", "\\\\").replace(":", "\\:")
    
    # 큰 자막 스타일 (확실히 보이게)
    big_style = "FontSize=32,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=4,Shadow=3,Alignment=2,MarginV=50,Bold=1"
    
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_file,
        "-vf", f"subtitles='{subtitle_file_escaped}':force_style='{big_style}'",
        "-c:v", "libx264",
        "-c:a", "copy",
        output_video
    ]
    
    print(f"🔧 FFmpeg로 큰 자막 처리 중...")
    print(f"   폰트 크기: 32")
    print(f"   굵기: 굵게")
    print(f"   외곽선: 두껍게")
    print(f"   그림자: 강하게")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 큰 자막 영상 생성 성공!")
            print(f"   경로: {output_video}")
            
            if os.path.exists(output_video):
                file_size = os.path.getsize(output_video)
                print(f"   파일 크기: {file_size:,} bytes")
                
                # 서버 URL
                server_url = f"http://localhost:8000/static/videos/{os.path.basename(output_video)}"
                print(f"   🌐 URL: {server_url}")
                
                print(f"\n🎉 이번엔 자막이 확실히 보일 겁니다!")
                print(f"   - 폰트 크기: 32 (매우 큼)")
                print(f"   - 굵은 글씨 + 두꺼운 외곽선")
                print(f"   - 강한 그림자 효과")
                print(f"   - 2초씩 충분히 표시")
            else:
                print("❌ 파일 생성 실패")
        else:
            print(f"❌ FFmpeg 실패: {result.stderr}")
    
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    asyncio.run(test_visible_subtitle())
