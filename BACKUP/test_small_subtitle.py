"""
작은 자막으로 테스트
"""
import asyncio
import os
import subprocess
from subtitle_utils import get_sequential_subtitle_style

async def test_small_subtitle():
    """작은 자막으로 테스트"""
    print("📝 작은 자막 테스트 시작...")
    
    # 기존 비디오 파일
    video_file = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
    
    if not os.path.exists(video_file):
        print(f"❌ 비디오 파일 없음: {video_file}")
        return
    
    # 작은 자막 파일 생성
    subtitle_content = """1
00:00:00,000 --> 00:00:01,000
작은 자막

2
00:00:01,100 --> 00:00:02,100
테스트입니다

3
00:00:02,200 --> 00:00:03,200
이제 크기가

4
00:00:03,300 --> 00:00:04,300
작아졌습니다

5
00:00:04,400 --> 00:00:05,400
확인해보세요
"""
    
    # 자막 파일 저장
    os.makedirs("./static/subtitles", exist_ok=True)
    import time
    timestamp = int(time.time())
    subtitle_file = f"./static/subtitles/small_subtitle_{timestamp}.srt"
    
    with open(subtitle_file, 'w', encoding='utf-8') as f:
        f.write(subtitle_content)
    
    print(f"📝 작은 자막 파일 생성: {os.path.basename(subtitle_file)}")
    
    # 출력 비디오 경로
    output_video = f"./static/videos/small_subtitle_{timestamp}.mp4"
    
    # FFmpeg로 작은 자막 합성
    ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
    
    # Windows 경로 변환
    subtitle_file_escaped = subtitle_file.replace("\\", "\\\\").replace(":", "\\:")
    
    # 작은 자막 스타일 (개선된 버전)
    small_style = get_sequential_subtitle_style(font_size=14, enable_outline=True)
    
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_file,
        "-vf", f"subtitles='{subtitle_file_escaped}':force_style='{small_style}'",
        "-c:v", "libx264",
        "-c:a", "copy",
        output_video
    ]
    
    print(f"🔧 FFmpeg로 작은 자막 처리 중...")
    print(f"   폰트 크기: 14")
    print(f"   굵기: 일반")
    print(f"   여백: 줄임")
    
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
                
                print(f"\n🎉 작은 자막으로 영상 완성!")
                print(f"   - 폰트 크기: 18 → 14로 줄임")
                print(f"   - 굵기: 굵게 → 일반으로 변경")
                print(f"   - 여백: 줄여서 더 깔끔하게")
                print(f"   - 외곽선: 얇게 조정")
            else:
                print("❌ 파일 생성 실패")
        else:
            print(f"❌ FFmpeg 실패: {result.stderr}")
    
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    asyncio.run(test_small_subtitle())
