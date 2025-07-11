"""
기존 영상에 순차적 자막을 추가하는 수정된 스크립트
자막이 제대로 나오지 않는 문제를 해결
"""
import os
import asyncio
from subtitle_utils import (
    create_sequential_subtitle_file, 
    get_sequential_subtitle_style
)
import tempfile
import subprocess

async def add_subtitles_to_existing_video_fixed():
    """기존 영상에 자막 추가 (수정된 버전)"""
    try:
        # 원본 영상 파일 경로
        video_path = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
        
        print(f"🎬 기존 영상에 자막 추가 시작...")
        print(f"   원본 영상: {os.path.basename(video_path)}")
        
        # 영상 파일 존재 확인
        if not os.path.exists(video_path):
            print(f"❌ 영상 파일을 찾을 수 없습니다: {video_path}")
            return
        
        # 1. 더 간단한 자막 텍스트 생성 (영상 길이에 맞게)
        print("📝 자막 파일 생성 중...")
        
        # 임시 자막 파일 생성
        subtitle_dir = tempfile.mkdtemp()
        original_subtitle_path = os.path.join(subtitle_dir, "video_subtitle.srt")
        
        # 더 짧고 간단한 SRT 형식 자막 (영상 길이에 맞게 조정)
        srt_content = """1
00:00:00,000 --> 00:00:03,000
안녕하세요 여러분

2
00:00:03,000 --> 00:00:06,000
오늘은 좋은 날이에요

3
00:00:06,000 --> 00:00:09,000
함께 즐거운 시간을 보내요

4
00:00:09,000 --> 00:00:12,000
이렇게 자막이 나옵니다

5
00:00:12,000 --> 00:00:15,000
한 줄씩 차례대로 나와요
"""
        
        with open(original_subtitle_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        print(f"✅ 원본 자막 파일 생성: {os.path.basename(original_subtitle_path)}")
        
        # 2. 순차적 자막 파일로 변환 (더 보수적인 설정)
        sequential_subtitle_path = os.path.join(subtitle_dir, "video_subtitle_sequential.srt")
        sequential_subtitle_path = create_sequential_subtitle_file(
            original_subtitle_path,
            sequential_subtitle_path,
            max_chars=15,     # 조금 더 긴 줄 허용
            line_duration=1.0, # 더 긴 표시 시간
            gap_duration=0.2   # 더 긴 간격
        )
        
        # 3. 생성된 순차적 자막 내용 확인
        print("\n📋 생성된 순차적 자막 내용:")
        print("=" * 60)
        with open(sequential_subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
        print("=" * 60)
        
        # 4. 더 큰 폰트와 명확한 스타일로 FFmpeg 자막 합성
        print("\n🎬 FFmpeg로 자막 합성 중...")
        
        # 더 큰 폰트 크기와 더 명확한 스타일
        subtitle_style = get_sequential_subtitle_style(font_size=18, enable_outline=True)
        print(f"🎨 사용 중인 자막 스타일: {subtitle_style}")
        
        # 자막 경로를 Unix 형식으로 변환 (FFmpeg 호환성)
        subtitle_path_unix = sequential_subtitle_path.replace("\\", "/")
        print(f"🔧 자막 파일 경로: {subtitle_path_unix}")
        
        # 최종 출력 파일명
        import time
        timestamp = int(time.time())
        output_filename = f"frame_transitions_with_subtitles_fixed_{timestamp}.mp4"
        output_path = os.path.join("D:\\shortpilot\\static\\videos", output_filename)
        
        # FFmpeg 전체 경로
        ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
        
        # 한글 폰트 문제 해결을 위한 drawtext 방식 사용
        korean_texts = [
            "안녕하세요 여러분",
            "오늘은 좋은 날이에요", 
            "함께 즐거운 시간을 보내요",
            "이렇게 자막이 나옵니다",
            "한 줄씩 차례대로 나와요"
        ]
        
        # 한글 폰트 경로 (Windows 기본 한글 폰트)
        korean_font = "C:/Windows/Fonts/malgun.ttf"  # 맑은 고딕
        
        # drawtext 필터 체인 생성 (한글 지원)
        drawtext_filters = []
        for i, text in enumerate(korean_texts):
            start_time = i * 3
            end_time = (i + 1) * 3
            drawtext_filter = f"drawtext=fontfile='{korean_font}':text='{text}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-80:enable='between(t,{start_time},{end_time})'"
            drawtext_filters.append(drawtext_filter)
        
        # 모든 drawtext 필터를 하나의 체인으로 결합
        vf_chain = ",".join(drawtext_filters)
        
        final_cmd = [
            ffmpeg_exe, "-y",
            "-i", video_path,  # 입력 비디오
            "-vf", vf_chain,   # 한글 폰트 drawtext 필터 체인
            "-c:v", "libx264",    # 비디오 코덱
            "-preset", "fast",    # 빠른 인코딩
            "-crf", "23",         # 품질 설정
            "-c:a", "copy",       # 오디오 복사
            output_path
        ]
        
        print(f"🔧 FFmpeg 명령어 실행 중...")
        print(f"   명령어: {' '.join(final_cmd)}")
        
        result = subprocess.run(final_cmd, capture_output=True, text=True)
        
        print(f"\n📊 FFmpeg 결과:")
        print(f"   Return code: {result.returncode}")
        if result.stdout:
            print(f"   STDOUT: {result.stdout}")
        if result.stderr:
            print(f"   STDERR: {result.stderr}")
        
        if result.returncode != 0:
            print(f"❌ 자막 합성 실패!")
            print(f"   오류: {result.stderr}")
            
            # 대안: 더 기본적인 자막 방식 시도
            print("\n🔄 대안 방식으로 재시도 중...")
            
            # 더 간단한 자막 스타일
            simple_style = "FontSize=20,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2"
            
            simple_cmd = [
                ffmpeg_exe, "-y",
                "-i", video_path,
                "-vf", f"subtitles='{subtitle_path_unix}':force_style='{simple_style}'",
                "-c:v", "libx264",
                "-c:a", "copy",
                output_path
            ]
            
            print(f"🔧 간단한 명령어 실행 중...")
            print(f"   명령어: {' '.join(simple_cmd)}")
            
            result = subprocess.run(simple_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ 대안 방식도 실패: {result.stderr}")
                return
        
        # 5. 결과 확인
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path)
            print(f"\n✅ 자막 추가 성공!")
            print(f"   원본 영상: {os.path.basename(video_path)}")
            print(f"   자막 추가된 영상: {output_filename}")
            print(f"   파일 크기: {file_size:,} bytes")
            print(f"   절대 경로: {output_path}")
            
            print(f"\n🎯 적용된 자막 설정:")
            print(f"   📏 폰트 크기: 18px")
            print(f"   📝 최대 글자 수: 15자")
            print(f"   ⏱️ 각 줄 표시 시간: 1.0초")
            print(f"   📏 줄 간격: 0.2초")
            print(f"   🎨 스타일: 흰색 텍스트, 검은색 외곽선")
        else:
            print(f"❌ 영상 파일 생성 실패 또는 파일이 비어있음")
            if os.path.exists(output_path):
                print(f"   파일 크기: {os.path.getsize(output_path)} bytes")
        
        # 임시 파일 정보 출력 (디버깅용)
        print(f"\n🔍 디버깅 정보:")
        print(f"   임시 자막 파일: {sequential_subtitle_path}")
        print(f"   파일 존재: {os.path.exists(sequential_subtitle_path)}")
        if os.path.exists(sequential_subtitle_path):
            print(f"   파일 크기: {os.path.getsize(sequential_subtitle_path)} bytes")
        
    except Exception as e:
        print(f"❌ 자막 추가 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_subtitles_to_existing_video_fixed())
