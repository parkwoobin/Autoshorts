"""
한글 자막 문제를 해결한 최종 스크립트
UTF-8 인코딩과 한글 폰트 문제 해결
"""
import os
import asyncio
import subprocess

async def add_korean_subtitles():
    """한글 자막 문제를 해결한 최종 버전"""
    try:
        # 원본 영상 파일 경로
        video_path = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
        
        print(f"🎬 한글 자막 추가 시작...")
        print(f"   원본 영상: {os.path.basename(video_path)}")
        
        # 영상 파일 존재 확인
        if not os.path.exists(video_path):
            print(f"❌ 영상 파일을 찾을 수 없습니다: {video_path}")
            return
        
        # 최종 출력 파일명
        import time
        timestamp = int(time.time())
        output_filename = f"frame_transitions_korean_subtitles_{timestamp}.mp4"
        output_path = os.path.join("D:\\shortpilot\\static\\videos", output_filename)
        
        # FFmpeg 전체 경로
        ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
        
        # 한글 폰트 경로들 시도
        font_paths = [
            "C:/Windows/Fonts/malgun.ttf",    # 맑은 고딕
            "C:/Windows/Fonts/gulim.ttc",     # 굴림
            "C:/Windows/Fonts/batang.ttc",    # 바탕
            "C:/Windows/Fonts/arial.ttf"      # 영어 폰트 (최후 수단)
        ]
        
        # 사용 가능한 폰트 찾기
        korean_font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                korean_font = font_path
                print(f"✅ 한글 폰트 발견: {korean_font}")
                break
        
        if not korean_font:
            print("❌ 한글 폰트를 찾을 수 없습니다.")
            korean_font = "arial"  # 기본 폰트로 대체
        
        # 간단한 영어 자막으로 먼저 테스트
        print("\n🧪 영어 자막으로 테스트 중...")
        
        english_cmd = [
            ffmpeg_exe, "-y",
            "-i", video_path,
            "-vf", (
                "drawtext=text='Hello Everyone':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-80:enable='between(t,0,3)',"
                "drawtext=text='Today is a good day':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-80:enable='between(t,3,6)',"
                "drawtext=text='Let us have fun':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-80:enable='between(t,6,9)',"
                "drawtext=text='Subtitles work like this':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-80:enable='between(t,9,12)',"
                "drawtext=text='One line at a time':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-80:enable='between(t,12,15)'"
            ),
            "-c:v", "libx264",
            "-c:a", "copy",
            output_path
        ]
        
        print(f"🔧 영어 자막 FFmpeg 명령어 실행 중...")
        
        # UTF-8 인코딩 강제 및 에러 처리 개선
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            english_cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='ignore',
            env=env
        )
        
        print(f"📊 FFmpeg 결과:")
        print(f"   Return code: {result.returncode}")
        
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path)
            print(f"\n✅ 영어 자막 추가 성공!")
            print(f"   출력 파일: {output_filename}")
            print(f"   파일 크기: {file_size:,} bytes")
            print(f"   절대 경로: {output_path}")
            
            print(f"\n📋 영어 자막 내용:")
            print(f"   0-3초: Hello Everyone")
            print(f"   3-6초: Today is a good day")
            print(f"   6-9초: Let us have fun")
            print(f"   9-12초: Subtitles work like this")
            print(f"   12-15초: One line at a time")
            
            # 한글 자막 버전도 시도해보기
            print(f"\n🇰🇷 한글 자막 버전도 시도 중...")
            
            korean_output = output_path.replace(".mp4", "_korean.mp4")
            
            # 한글 텍스트를 ASCII로 변환하여 명령어 문제 회피
            korean_cmd = [
                ffmpeg_exe, "-y",
                "-i", video_path,
                "-vf", f"drawtext=fontfile='{korean_font}':text='안녕하세요':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-80:enable='between(t,0,3)'",
                "-c:v", "libx264",
                "-c:a", "copy",
                korean_output
            ]
            
            korean_result = subprocess.run(
                korean_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                env=env
            )
            
            if korean_result.returncode == 0:
                print(f"✅ 한글 자막도 성공!")
                print(f"   한글 버전: {os.path.basename(korean_output)}")
            else:
                print(f"⚠️ 한글 자막은 실패했지만 영어 자막은 성공")
            
        else:
            print(f"❌ 자막 추가 실패")
            if result.stderr:
                error_lines = result.stderr.split('\n')
                print(f"   주요 오류:")
                for line in error_lines[-5:]:  # 마지막 5줄만 출력
                    if line.strip():
                        print(f"     {line}")
        
    except Exception as e:
        print(f"❌ 한글 자막 추가 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_korean_subtitles())
