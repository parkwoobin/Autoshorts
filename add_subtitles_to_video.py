"""
기존 영상에 순차적 자막을 추가하는 스크립트
"""
import os
import asyncio
from subtitle_utils import (
    create_sequential_subtitle_file, 
    get_sequential_subtitle_style
)
import tempfile
import subprocess

async def add_subtitles_to_existing_video():
    """기존 영상에 자막 추가"""
    try:
        # 원본 영상 파일 경로
        video_path = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
        
        print(f"🎬 기존 영상에 자막 추가 시작...")
        print(f"   원본 영상: {os.path.basename(video_path)}")
        
        # 영상 파일 존재 확인
        if not os.path.exists(video_path):
            print(f"❌ 영상 파일을 찾을 수 없습니다: {video_path}")
            return
        
        # 1. 테스트용 자막 텍스트 생성
        subtitle_text = """안녕하세요 여러분! 오늘 이 영상을 통해 정말 멋진 이야기를 들려드리고 싶습니다.
        
함께 즐거운 시간을 보내면서 새로운 것들을 배워보도록 하겠습니다.

이렇게 한 줄씩 순차적으로 나오는 자막이 어떤 느낌인지 확인해보세요.

각 줄이 완전히 끝나고 나서 다음 줄이 나타나는 방식입니다.

정말 깔끔하고 읽기 좋은 자막이 완성되었네요!"""
        
        # 2. 임시 자막 파일 생성
        subtitle_dir = tempfile.mkdtemp()
        original_subtitle_path = os.path.join(subtitle_dir, "video_subtitle.srt")
        
        # SRT 형식으로 자막 파일 생성 (약 20초 영상으로 가정)
        srt_content = """1
00:00:00,000 --> 00:00:04,000
안녕하세요 여러분! 오늘 이 영상을 통해 정말 멋진 이야기를 들려드리고 싶습니다.

2
00:00:04,000 --> 00:00:08,000
함께 즐거운 시간을 보내면서 새로운 것들을 배워보도록 하겠습니다.

3
00:00:08,000 --> 00:00:12,000
이렇게 한 줄씩 순차적으로 나오는 자막이 어떤 느낌인지 확인해보세요.

4
00:00:12,000 --> 00:00:16,000
각 줄이 완전히 끝나고 나서 다음 줄이 나타나는 방식입니다.

5
00:00:16,000 --> 00:00:20,000
정말 깔끔하고 읽기 좋은 자막이 완성되었네요!
"""
        
        with open(original_subtitle_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        print(f"📝 자막 파일 생성: {original_subtitle_path}")
        
        # 3. 순차적 자막 파일로 변환
        sequential_subtitle_path = os.path.join(subtitle_dir, "video_subtitle_sequential.srt")
        sequential_subtitle_path = create_sequential_subtitle_file(
            original_subtitle_path,
            sequential_subtitle_path,
            max_chars=12,     # 현재 설정: 12자
            line_duration=0.8, # 현재 설정: 0.8초
            gap_duration=0.1   # 현재 설정: 0.1초 간격
        )
        
        # 4. 생성된 순차적 자막 내용 확인
        print("\n📋 생성된 순차적 자막 내용:")
        print("=" * 50)
        with open(sequential_subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content[:500] + "..." if len(content) > 500 else content)
        print("=" * 50)
        
        # 5. FFmpeg로 자막을 영상에 합성
        print("\n🎬 FFmpeg로 자막 합성 중...")
        
        # 현재 설정된 폰트 크기 (14px)와 스타일 사용
        current_style = get_sequential_subtitle_style(font_size=14, enable_outline=True)
        print(f"🎨 사용 중인 자막 스타일: {current_style}")
        
        # 자막 경로를 Windows 호환 형식으로 변환
        subtitle_path_fixed = sequential_subtitle_path.replace("\\", "/").replace(":", "\\:")
        
        # 최종 출력 파일명
        import time
        timestamp = int(time.time())
        output_filename = f"frame_transitions_with_subtitles_{timestamp}.mp4"
        output_path = os.path.join("D:\\shortpilot\\static\\videos", output_filename)
        
        # FFmpeg 전체 경로
        ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
        
        # FFmpeg로 자막 합성
        final_cmd = [
            ffmpeg_exe, "-y",
            "-i", video_path,  # 입력 비디오
            "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{current_style}'",  # 현재 자막 스타일
            "-c:v", "libx264",      # 비디오 코덱
            "-c:a", "copy",         # 오디오 복사 (재인코딩 없음)
            output_path
        ]
        
        print(f"🔧 FFmpeg 명령어 실행 중...")
        print(f"   명령어: {' '.join(final_cmd)}")
        
        result = subprocess.run(final_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ 자막 합성 실패: {result.stderr}")
            return
        
        # 6. 결과 확인
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path)
            print(f"\n✅ 자막 추가 완료!")
            print(f"   원본 영상: {os.path.basename(video_path)}")
            print(f"   자막 추가된 영상: {output_filename}")
            print(f"   파일 크기: {file_size:,} bytes")
            print(f"   절대 경로: {output_path}")
            
            print(f"\n🎯 적용된 자막 설정:")
            print(f"   📏 폰트 크기: 14px")
            print(f"   📝 최대 글자 수: 12자")
            print(f"   ⏱️ 각 줄 표시 시간: 0.8초")
            print(f"   📏 줄 간격: 0.1초")
            print(f"   🎨 스타일: 흰색 텍스트, 검은색 외곽선, 하단 중앙 정렬")
            
            print(f"\n✨ 자막이 한 줄씩 순차적으로 표시됩니다!")
            print(f"   각 줄이 완전히 끝나고 0.1초 간격 후 다음 줄이 나타납니다.")
        else:
            print(f"❌ 영상 파일 생성 실패")
        
    except Exception as e:
        print(f"❌ 자막 추가 실패: {e}")

if __name__ == "__main__":
    asyncio.run(add_subtitles_to_existing_video())
