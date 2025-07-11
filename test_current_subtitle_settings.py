"""
현재 설정된 순차적 자막 시스템을 테스트하는 스크립트
한 줄씩 순차적으로 나오는 자막이 어떻게 표시되는지 확인
"""
import os
import asyncio
from subtitle_utils import (
    create_sequential_subtitle_file, 
    get_sequential_subtitle_style,
    add_subtitles_to_video_ffmpeg
)
import tempfile
import subprocess

async def test_current_subtitle_settings():
    """현재 자막 설정으로 테스트 영상 생성"""
    try:
        print("🎬 현재 자막 설정 테스트 시작...")
        
        # 1. 테스트용 자막 파일 생성
        test_subtitle_content = """1
00:00:00,000 --> 00:00:05,000
안녕하세요 여러분! 오늘은 정말 좋은 날이네요. 함께 즐거운 시간을 보내봅시다.

2
00:00:05,000 --> 00:00:10,000
이 영상에서는 한 줄씩 순차적으로 나오는 자막을 테스트해보겠습니다.

3
00:00:10,000 --> 00:00:15,000
각 줄이 완전히 끝나고 나서 다음 줄이 표시되는 방식입니다.
"""
        
        # 임시 자막 파일 생성
        subtitle_dir = tempfile.mkdtemp()
        original_subtitle_path = os.path.join(subtitle_dir, "test_original.srt")
        
        with open(original_subtitle_path, 'w', encoding='utf-8') as f:
            f.write(test_subtitle_content)
        
        print(f"📝 테스트 자막 파일 생성: {original_subtitle_path}")
        
        # 2. 순차적 자막 파일로 변환 (현재 설정 사용)
        sequential_subtitle_path = os.path.join(subtitle_dir, "test_sequential.srt")
        sequential_subtitle_path = create_sequential_subtitle_file(
            original_subtitle_path,
            sequential_subtitle_path,
            max_chars=12,     # 현재 설정: 12자
            line_duration=0.8, # 현재 설정: 0.8초
            gap_duration=0.1   # 현재 설정: 0.1초 간격
        )
        
        # 3. 생성된 순차적 자막 내용 확인
        print("\n📋 생성된 순차적 자막 내용:")
        print("=" * 50)
        with open(sequential_subtitle_path, 'r', encoding='utf-8') as f:
            print(f.read())
        print("=" * 50)
        
        # 4. 테스트용 단색 영상 생성 (FFmpeg 사용)
        print("\n🎥 테스트용 배경 영상 생성 중...")
        test_video_path = os.path.join(".", "test_background_video.mp4")
        
        # FFmpeg 전체 경로
        ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
        
        # 20초짜리 파란색 배경 영상 생성
        bg_cmd = [
            ffmpeg_exe, "-y",
            "-f", "lavfi",
            "-i", "color=c=blue:size=1280x720:duration=20",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            test_video_path
        ]
        
        result = subprocess.run(bg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 배경 영상 생성 실패: {result.stderr}")
            return
        
        print(f"✅ 배경 영상 생성 완료: {test_video_path}")
        
        # 5. 현재 자막 스타일 설정으로 영상에 자막 합성
        print("\n🎬 현재 자막 설정으로 영상 생성 중...")
        
        # 현재 설정된 폰트 크기 (14px)와 스타일 사용
        current_style = get_sequential_subtitle_style(font_size=14, enable_outline=True)
        print(f"🎨 사용 중인 자막 스타일: {current_style}")
        
        # 자막 경로를 Windows 호환 형식으로 변환
        subtitle_path_fixed = sequential_subtitle_path.replace("\\", "/").replace(":", "\\:")
        
        # 최종 출력 파일명
        import time
        timestamp = int(time.time())
        output_filename = f"current_subtitle_test_{timestamp}.mp4"
        output_path = os.path.join(".", output_filename)
        
        # FFmpeg로 자막 합성
        final_cmd = [
            ffmpeg_exe, "-y",
            "-i", test_video_path,  # 입력 비디오
            "-vf", f"subtitles='{subtitle_path_fixed}':force_style='{current_style}'",  # 현재 자막 스타일
            "-c:v", "libx264",      # 비디오 코덱
            "-c:a", "aac",          # 오디오 코덱 (없어도 됨)
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
            print(f"\n✅ 현재 설정 테스트 영상 생성 완료!")
            print(f"   파일명: {output_filename}")
            print(f"   파일 크기: {file_size:,} bytes")
            print(f"   절대 경로: {os.path.abspath(output_path)}")
            
            print(f"\n🎯 현재 자막 설정:")
            print(f"   📏 폰트 크기: 14px")
            print(f"   📝 최대 글자 수: 12자")
            print(f"   ⏱️ 각 줄 표시 시간: 0.8초")
            print(f"   📏 줄 간격: 0.1초")
            print(f"   🎨 스타일: 흰색 텍스트, 검은색 외곽선, 하단 중앙 정렬")
            
            print(f"\n✨ 이 설정으로 한 줄씩 순차적으로 자막이 표시됩니다!")
            print(f"   각 줄이 완전히 끝나고 0.1초 간격 후 다음 줄이 나타납니다.")
        else:
            print(f"❌ 영상 파일 생성 실패")
        
        # 임시 파일들 정리
        try:
            os.remove(test_video_path)
            print(f"🧹 임시 배경 영상 삭제")
        except:
            pass
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_current_subtitle_settings())
