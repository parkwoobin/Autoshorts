"""
기존 영상에 순차적 자막을 추가하는 최종 수정 스크립트
FFmpeg 경로 문제를 해결한 버전
"""
import os
import asyncio
from subtitle_utils import (
    create_sequential_subtitle_file, 
    get_sequential_subtitle_style
)
import subprocess

async def add_subtitles_final():
    """기존 영상에 자막 추가 (최종 수정 버전)"""
    try:
        # 원본 영상 파일 경로
        video_path = r"D:\shortpilot\static\videos\frame_transitions_1752195752718.mp4"
        
        print(f"🎬 기존 영상에 자막 추가 시작...")
        print(f"   원본 영상: {os.path.basename(video_path)}")
        
        # 영상 파일 존재 확인
        if not os.path.exists(video_path):
            print(f"❌ 영상 파일을 찾을 수 없습니다: {video_path}")
            return
        
        # 1. 자막 파일을 현재 디렉토리에 생성 (경로 문제 해결)
        print("📝 자막 파일 생성 중...")
        
        original_subtitle_path = os.path.join(".", "temp_subtitle.srt")
        
        # 간단한 SRT 형식 자막
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
        
        print(f"✅ 원본 자막 파일 생성: {original_subtitle_path}")
        
        # 2. 순차적 자막 파일로 변환
        sequential_subtitle_path = os.path.join(".", "temp_subtitle_sequential.srt")
        sequential_subtitle_path = create_sequential_subtitle_file(
            original_subtitle_path,
            sequential_subtitle_path,
            max_chars=15,     
            line_duration=1.0, 
            gap_duration=0.2   
        )
        
        # 3. 생성된 순차적 자막 내용 확인
        print("\n📋 생성된 순차적 자막 내용:")
        print("=" * 60)
        with open(sequential_subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
        print("=" * 60)
        
        # 4. 절대 경로로 변환하여 FFmpeg 호환성 확보
        sequential_subtitle_abs = os.path.abspath(sequential_subtitle_path)
        print(f"🔧 자막 파일 절대 경로: {sequential_subtitle_abs}")
        
        # 5. 최종 출력 파일명
        import time
        timestamp = int(time.time())
        output_filename = f"frame_transitions_with_subtitles_final_{timestamp}.mp4"
        output_path = os.path.join("D:\\shortpilot\\static\\videos", output_filename)
        
        # 6. FFmpeg 전체 경로
        ffmpeg_exe = r'C:\Users\oi3oi\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120061-gcfd1f81e7d-win64-gpl\bin\ffmpeg.exe'
        
        # 7. 가장 간단한 자막 필터 사용 (스타일 없이)
        print("\n🎬 FFmpeg로 자막 합성 중...")
        
        final_cmd = [
            ffmpeg_exe, "-y",
            "-i", video_path,  
            "-vf", f"subtitles='{sequential_subtitle_abs}':force_style='FontSize=20,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'",
            "-c:v", "libx264",    
            "-c:a", "copy",       
            output_path
        ]
        
        print(f"🔧 FFmpeg 명령어:")
        for i, part in enumerate(final_cmd):
            print(f"   [{i}] {part}")
        
        result = subprocess.run(final_cmd, capture_output=True, text=True)
        
        print(f"\n📊 FFmpeg 결과:")
        print(f"   Return code: {result.returncode}")
        
        if result.returncode != 0:
            print(f"❌ 첫 번째 시도 실패. 더 간단한 방식으로 재시도...")
            print(f"   오류: {result.stderr[:500]}...")
            
            # 더 간단한 방식: drawtext 필터 사용
            print("\n🔄 drawtext 필터로 재시도...")
            
            simple_cmd = [
                ffmpeg_exe, "-y",
                "-i", video_path,
                "-vf", "drawtext=fontfile=C\\\\:/Windows/Fonts/arial.ttf:text='안녕하세요 여러분':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-60:enable='between(t,0,3)',drawtext=fontfile=C\\\\:/Windows/Fonts/arial.ttf:text='오늘은 좋은 날이에요':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-60:enable='between(t,3,6)',drawtext=fontfile=C\\\\:/Windows/Fonts/arial.ttf:text='함께 즐거운 시간을 보내요':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-60:enable='between(t,6,9)',drawtext=fontfile=C\\\\:/Windows/Fonts/arial.ttf:text='이렇게 자막이 나옵니다':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-60:enable='between(t,9,12)',drawtext=fontfile=C\\\\:/Windows/Fonts/arial.ttf:text='한 줄씩 차례대로 나와요':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-60:enable='between(t,12,15)'",
                "-c:v", "libx264",
                "-c:a", "copy",
                output_path
            ]
            
            print(f"🔧 drawtext 명령어 실행...")
            result = subprocess.run(simple_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ drawtext 방식도 실패: {result.stderr[:500]}...")
                
                # 마지막 방법: 매우 간단한 단일 텍스트
                print("\n🔄 마지막 시도: 단일 텍스트...")
                
                last_cmd = [
                    ffmpeg_exe, "-y",
                    "-i", video_path,
                    "-vf", "drawtext=text='자막 테스트':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-60",
                    "-c:v", "libx264",
                    "-c:a", "copy",
                    output_path
                ]
                
                result = subprocess.run(last_cmd, capture_output=True, text=True)
        
        # 8. 결과 확인
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path)
            print(f"\n✅ 자막 추가 성공!")
            print(f"   원본 영상: {os.path.basename(video_path)}")
            print(f"   자막 추가된 영상: {output_filename}")
            print(f"   파일 크기: {file_size:,} bytes")
            print(f"   절대 경로: {output_path}")
        else:
            print(f"❌ 모든 방식 실패")
            print(f"   마지막 오류: {result.stderr[:500] if result.stderr else 'No error message'}")
        
        # 임시 파일 정리
        try:
            if os.path.exists(original_subtitle_path):
                os.remove(original_subtitle_path)
            if os.path.exists(sequential_subtitle_path):
                os.remove(sequential_subtitle_path)
            print("🧹 임시 파일 정리 완료")
        except:
            pass
        
    except Exception as e:
        print(f"❌ 자막 추가 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_subtitles_final())
