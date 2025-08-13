"""
비디오 서버를 위한 유틸리티 함수들
"""
import time  # 타임스탬프 생성용
import os  # 운영체제 관련 기능 (파일 경로 등)
import requests  # HTTP 요청용
from typing import List  # 타입 힌트용 (리스트 타입 명시)

# 테스트용 샘플 영상 URL들 (Runway API로 생성된 실제 영상들)
SAMPLE_VIDEO_URLS = [
    "https://dnznrvs05pmza.cloudfront.net/c55791da-e8dd-4857-a8ec-a6566295f83f.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiNTg3NDEzM2YyMzlkNDlmMCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1NTEyOTYwMH0.Poh0ul8pDhbH5RHdZwwcD7zJyt6zh0en-jCXXsBu0Z0",
    "https://dnznrvs05pmza.cloudfront.net/ecac18f0-2a45-489a-8238-da3fe14340dd.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOGJjMWE4NmFkOGU0YmQ2NSIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1NTEyOTYwMH0.TwwsG9uAe5H7u_fzFKBKhL0jqfBrFGF7vGnEhHHS6ak",
    "https://dnznrvs05pmza.cloudfront.net/d620c568-f91d-4e22-a3bd-081ff32fc87a.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTIzNWJlMTI5ZTEzM2YyNSIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1NTEyOTYwMH0.QLhqi_LFiPmQjZG_GfqU-Bl3ZhucMjfWmUvvUB1wvgw",
    "https://dnznrvs05pmza.cloudfront.net/fcc70d6b-ed34-4b97-b9d8-e6f1cd2c66b5.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk3ZWM1MDg4MzFiYWQzMSIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1NTEyOTYwMH0.-YCgC7xWhLJ5-gfh4WlUctSFtEDYJvA7uSkzNNWQgI4",
    "https://dnznrvs05pmza.cloudfront.net/047fca3d-f43d-44e7-af9e-a9d4ce61d4a1.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiZDZlZmEzYzBiYTZlMTVjMyIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1NTEyOTYwMH0.1wq8OftDJY0ftTVMOKaOZEyXs8LWuAUdPDjgRgi0sFI",
    "https://dnznrvs05pmza.cloudfront.net/12b1cad2-cc87-46d1-a5fc-3e2d86b6781f.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiYzA0NjEwZDUzOTllOTQxYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1NTEyOTYwMH0._Lhww_iLj4ck3eh5VN52_8D6qAdKqklmuvNJez9lLJ0"
]

def create_merger_instance(use_static_dir: bool = True, enable_bgm: bool = True):
    """VideoTransitionMerger 인스턴스 생성 또는 대안 처리기 반환"""
    try:
        # moviepy가 있으면 실제 VideoTransitionMerger 사용
        from video_merger import VideoTransitionMerger
        print("✅ VideoTransitionMerger 모듈 로드 성공")
        return VideoTransitionMerger(use_static_dir=use_static_dir, enable_bgm=enable_bgm)
    except ImportError:
        print("⚠️ VideoTransitionMerger는 moviepy 의존성으로 인해 비활성화됨")
        # 대안으로 간단한 비디오 처리기 반환
        return SimplVideoMerger(use_static_dir=use_static_dir)

class SimplVideoMerger:
    """moviepy 없이 사용할 수 있는 간단한 비디오 합치기 클래스"""
    
    def __init__(self, use_static_dir: bool = True):
        self.use_static_dir = use_static_dir
        self.output_dir = "static/videos" if use_static_dir else "output_videos"
        
        # 출력 디렉토리 생성
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"📁 비디오 출력 디렉토리: {os.path.abspath(self.output_dir)}")
    
    def update_status(self, step_name: str, progress: int, current_file: str = ""):
        """외부에서 상태를 업데이트할 수 있도록 하는 함수 (선택적)"""
        try:
            # video_server에서 video_processing_status가 있으면 업데이트
            import video_server
            if hasattr(video_server, 'video_processing_status'):
                video_server.video_processing_status.update({
                    "current_step": step_name,
                    "progress": progress,
                    "current_file": current_file
                })
        except:
            # import 실패하거나 video_processing_status가 없으면 무시
            pass
    
    def _get_video_info(self, video_path: str, ffmpeg_path: str):
        """비디오 정보 (해상도, fps) 추출 - 다중 fallback 방식"""
        import subprocess
        import json
        import os
        
        try:
            # 1단계: ffprobe 우선 시도 (가장 안정적)
            ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
            
            if os.path.exists(ffprobe_path):
                print(f"   🔍 ffprobe로 비디오 정보 추출 시도: {ffprobe_path}")
                
                cmd = [
                    ffprobe_path,
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    '-show_streams',
                    video_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    
                    # 비디오 스트림 찾기
                    for stream in data.get('streams', []):
                        if stream.get('codec_type') == 'video':
                            width = int(stream.get('width', 0))
                            height = int(stream.get('height', 0))
                            
                            # fps 계산
                            fps_str = stream.get('r_frame_rate', '30/1')
                            if '/' in fps_str:
                                num, den = fps_str.split('/')
                                fps = float(num) / float(den) if float(den) != 0 else 30.0
                            else:
                                fps = float(fps_str) if fps_str else 30.0
                            
                            # 유효성 검증
                            if 100 <= width <= 4000 and 100 <= height <= 4000 and 1.0 <= fps <= 120.0:
                                print(f"   ✅ ffprobe로 추출한 정보: {width}x{height} @ {fps:.2f}fps")
                                return {"width": width, "height": height, "fps": fps}
                            else:
                                print(f"   ⚠️ ffprobe 정보가 비정상적: {width}x{height} @ {fps}fps")
                
                print(f"   ⚠️ ffprobe 결과 처리 실패, fallback 시도...")
            
            # ffprobe 없거나 실패시 fallback으로 ffmpeg 사용
            print("   ⚠️ ffprobe 사용 불가, ffmpeg stderr 파싱 시도...")
            cmd = [
                ffmpeg_path,
                '-i', video_path,
                '-f', 'null',
                '-'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # stderr에서 해상도와 fps 추출 (더 정확한 패턴 사용)
            output = result.stderr
            print(f"   🔍 FFmpeg stderr 출력 (처음 200자): {output[:200]}...")
            
            # 해상도 추출 - 더 정확한 패턴으로 Video 스트림에서만 추출
            import re
            # 'Video:' 뒤에 오는 해상도 패턴만 매칭
            resolution_match = re.search(r'Video:.*?(\d{2,4})x(\d{2,4})', output)
            # fps 패턴도 더 정확하게
            fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', output)
            
            if resolution_match:
                width, height = int(resolution_match.group(1)), int(resolution_match.group(2))
                # 해상도 유효성 검증 추가
                if 100 <= width <= 4000 and 100 <= height <= 4000:
                    print(f"   📊 stderr에서 추출한 해상도: {width}x{height}")
                else:
                    print(f"   ⚠️ 비정상적인 해상도 감지: {width}x{height}, 기본값 사용")
                    width, height = 1280, 720
            else:
                width, height = 1280, 720  # 기본값
                print(f"   ⚠️ 해상도 추출 실패, 기본값 사용: {width}x{height}")
                
            if fps_match:
                fps_value = float(fps_match.group(1))
                # fps 유효성 검증 추가
                if 1.0 <= fps_value <= 120.0:
                    fps = fps_value
                    print(f"   📊 stderr에서 추출한 fps: {fps}")
                else:
                    print(f"   ⚠️ 비정상적인 fps 감지: {fps_value}, 기본값 사용")
                    fps = 30.0
            else:
                fps = 30.0  # 기본값
                print(f"   ⚠️ fps 추출 실패, 기본값 사용: {fps}")
            
            return {"width": width, "height": height, "fps": fps}
            
        except subprocess.TimeoutExpired:
            print(f"   ⚠️ 비디오 정보 추출 시간 초과")
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON 파싱 오류: {e}")
        except Exception as e:
            print(f"   ❌ 비디오 정보 추출 중 오류: {e}")
        
        # 모든 방법이 실패한 경우 안전한 기본값 반환
        print(f"   🔄 모든 방법 실패, 안전한 기본값 사용: 1280x720 @ 30fps")
        return {"width": 1280, "height": 720, "fps": 30.0}

    def merge_videos_with_frame_transitions(self, video_urls: List[str], output_filename: str, bgm_file: str = None, subtitle_file: str = None, bgm_volume: float = 0.4):
        """FFmpeg를 사용한 비디오 합치기 + BGM + 자막 처리 통합"""
        import subprocess
        import tempfile
        import shutil
        
        print(f"🔗 {len(video_urls)}개 비디오를 합치기 시작...")
        if bgm_file:
            print(f"🎵 BGM과 함께 처리: {os.path.basename(bgm_file)}")
        if subtitle_file:
            print(f"📝 자막과 함께 처리: {os.path.basename(subtitle_file)}")
        if not bgm_file and not subtitle_file:
            print(f"🎬 비디오만 처리")
        
        if not video_urls:
            raise Exception("합칠 비디오 URL이 없습니다.")
        
        # FFmpeg 경로 확인
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            possible_paths = [
                'ffmpeg.exe',
                'C:\\ffmpeg\\bin\\ffmpeg.exe',
                'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
                'C:\\Users\\Public\\ffmpeg\\bin\\ffmpeg.exe'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    ffmpeg_path = path
                    break
            
            if not ffmpeg_path:
                raise Exception("FFmpeg가 설치되지 않았습니다.")
        
        print(f"✅ FFmpeg 경로: {ffmpeg_path}")
        
        # 진행 상황 추적
        total_steps = len(video_urls) + (2 if bgm_file else 1)
        current_step = 0
        
        def update_progress(step_name: str):
            nonlocal current_step
            current_step += 1
            progress = (current_step / total_steps) * 100
            print(f"📊 진행률: {progress:.1f}% - {step_name}")
            self.update_status(f"6단계: {step_name}", int(30 + (progress * 0.6)), step_name)
        
        # 임시 디렉토리에 비디오 다운로드
        temp_dir = tempfile.mkdtemp()
        temp_files = []
        
        try:
            # 각 비디오 다운로드
            for i, url in enumerate(video_urls):
                print(f"📥 [{i+1}/{len(video_urls)}] 비디오 다운로드 중: {url[:60]}...")
                
                try:
                    response = requests.get(url, timeout=120)
                    if response.status_code == 200:
                        temp_file = os.path.join(temp_dir, f"video_{i+1}.mp4")
                        with open(temp_file, 'wb') as f:
                            f.write(response.content)
                        
                        # 다운로드된 파일 검증
                        check_cmd = [ffmpeg_path, '-i', temp_file, '-t', '1', '-f', 'null', '-']
                        subprocess.run(check_cmd, check=True, capture_output=True, text=True)
                        
                        temp_files.append(temp_file)
                        print(f"   ✅ 비디오 {i+1} 다운로드 완료")
                        update_progress(f"비디오 {i+1} 다운로드 완료")
                        
                    else:
                        print(f"   ❌ 다운로드 실패: HTTP {response.status_code}")
                except Exception as e:
                    print(f"   ❌ 다운로드 오류: {e}")
            
            if not temp_files:
                raise Exception("다운로드된 비디오가 없습니다.")
            
            # 비디오 합치기 (concat 방식)
            output_path = os.path.join(self.output_dir, output_filename)
            
            if len(temp_files) == 1:
                print(f"📋 비디오가 1개뿐이므로 단순 처리합니다...")
                if bgm_file or subtitle_file:
                    # BGM 및/또는 자막과 함께 처리
                    self._merge_single_video_with_bgm_and_subtitle(temp_files[0], output_path, ffmpeg_path, bgm_file, subtitle_file, bgm_volume)
                else:
                    # BGM, 자막 없이 처리
                    subprocess.run([
                        ffmpeg_path, '-i', temp_files[0], 
                        '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p',
                        output_path, '-y'
                    ], check=True, capture_output=True, text=True)
                update_progress("비디오 처리 완료")
            else:
                print(f"🔗 {len(temp_files)}개 비디오를 트랜지션으로 합치는 중...")
                if bgm_file or subtitle_file:
                    # BGM 및/또는 자막과 함께 처리
                    self._merge_with_transitions_bgm_and_subtitle(temp_files, output_path, ffmpeg_path, bgm_file, subtitle_file, bgm_volume)
                else:
                    # BGM, 자막 없이 트랜지션 처리
                    self._merge_with_transitions_only(temp_files, output_path, ffmpeg_path)
                update_progress("비디오 합치기 완료")
            
            # 최종 파일 확인
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                file_size_mb = file_size / (1024 * 1024)
                print(f"✅ 비디오 합치기 완료: {output_filename}")
                print(f"📁 파일 위치: {os.path.abspath(output_path)}")
                print(f"📊 파일 크기: {file_size_mb:.2f} MB")
                if bgm_file:
                    print(f"� BGM 포함 완료")
            else:
                raise Exception("최종 비디오 파일이 생성되지 않았습니다.")
            
            return output_path
            
        except Exception as e:
            print(f"❌ 비디오 처리 중 오류: {e}")
            raise
            
        finally:
            # 임시 파일 정리
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    print(f"⚠️ 임시 파일 삭제 실패: {temp_file} - {e}")
            
            try:
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                print(f"⚠️ 임시 디렉토리 삭제 실패: {e}")
    
    def _merge_single_video_with_bgm_and_subtitle(self, video_file: str, output_path: str, ffmpeg_path: str, bgm_file: str = None, subtitle_file: str = None, bgm_volume: float = 0.4):
        """단일 비디오에 BGM 및/또는 자막 추가 - 통합 처리"""
        import subprocess
        
        print(f"🎬 단일 비디오 통합 처리 중...")
        if bgm_file:
            print(f"   🎵 BGM: {os.path.basename(bgm_file)}")
        if subtitle_file:
            print(f"   📝 자막: {os.path.basename(subtitle_file)}")
        
        # 자막 파일 경로 처리 (FFmpeg 호환 형식)
        subtitle_path_fixed = None
        if subtitle_file and os.path.exists(subtitle_file):
            subtitle_path_fixed = subtitle_file.replace("\\", "/").replace(":", "\\:")
        
        # 자막 스타일 설정
        subtitle_style = "fontfile=C\\:/Windows/Fonts/malgun.ttf:fontsize=30:fontcolor=white:bordercolor=black:borderw=2:x=(w-text_w)/2:y=h-80"
        
        try:
            # 케이스 1: BGM + 자막 모두 있음
            if bgm_file and os.path.exists(bgm_file) and subtitle_path_fixed:
                print("🔄 방법1: BGM + 자막 통합 처리...")
                cmd = [
                    ffmpeg_path,
                    '-i', video_file,  # 비디오 입력
                    '-i', bgm_file,    # BGM 입력
                    '-vf', f"subtitles='{subtitle_path_fixed}'",  # 자막 필터
                    '-filter_complex', f'[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first[audio]',
                    '-map', '0:v',
                    '-map', '[audio]',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-shortest',
                    output_path, '-y'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print("✅ BGM + 자막 통합 처리 완료")
                    return
                else:
                    print(f"⚠️ BGM + 자막 통합 실패: {result.stderr}")
            
            # 케이스 2: 자막만 있음
            elif subtitle_path_fixed:
                print("🔄 방법2: 자막만 추가...")
                cmd = [
                    ffmpeg_path,
                    '-i', video_file,
                    '-vf', f"subtitles='{subtitle_path_fixed}'",
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'copy',
                    output_path, '-y'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print("✅ 자막 추가 완료")
                    return
                else:
                    print(f"⚠️ 자막 추가 실패: {result.stderr}")
            
            # 케이스 3: BGM만 있음 (기존 함수 호출)
            elif bgm_file and os.path.exists(bgm_file):
                print("🔄 방법3: BGM만 추가...")
                self._merge_single_video_with_bgm(video_file, output_path, ffmpeg_path, bgm_file, bgm_volume)
                return
            
            # 케이스 4: Fallback - 비디오만 처리
            print("🔄 Fallback: 비디오만 처리...")
            cmd = [ffmpeg_path, '-i', video_file, '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p', output_path, '-y']
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ 비디오만 처리 완료")
            
        except Exception as e:
            print(f"❌ 단일 비디오 처리 실패: {e}")
            # 최종 fallback
            cmd = [ffmpeg_path, '-i', video_file, '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p', output_path, '-y']
            subprocess.run(cmd, check=True, capture_output=True, text=True)
    
    def _merge_single_video_with_bgm(self, video_file: str, output_path: str, ffmpeg_path: str, bgm_file: str, bgm_volume: float = 0.4):
        """단일 비디오에 BGM 추가 - 강화된 오류 처리"""
        import subprocess
        
        print(f"🎵 단일 비디오에 BGM 추가 중: {os.path.basename(bgm_file)}")
        
        # BGM 파일 존재 확인
        if not os.path.exists(bgm_file):
            print(f"⚠️ BGM 파일이 없음: {bgm_file}, BGM 없이 처리")
            # BGM 없이 처리
            cmd = [ffmpeg_path, '-i', video_file, '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p', output_path, '-y']
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return
        
        # 방법 1: 기본 BGM 합치기 시도
        try:
            cmd = [
                ffmpeg_path,
                '-i', video_file,  # 비디오 입력
                '-i', bgm_file,    # BGM 입력
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                '-filter_complex', f'[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first[audio]',
                '-map', '0:v',
                '-map', '[audio]',
                '-shortest',
                output_path, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print("✅ 단일 비디오 + BGM 합치기 완료")
                return
            else:
                print(f"⚠️ BGM 합치기 실패 (방법1): {result.stderr}")
        except Exception as e:
            print(f"⚠️ BGM 합치기 예외 (방법1): {e}")
        
        # 방법 2: 비디오에 오디오가 없는 경우 대비
        try:
            print("🔄 비디오 오디오 없음 가정하고 BGM만 추가 시도...")
            cmd = [
                ffmpeg_path,
                '-i', video_file,
                '-i', bgm_file,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v',
                '-map', '1:a',
                '-shortest',
                output_path, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print("✅ 단일 비디오 + BGM 합치기 완료 (방법2)")
                return
            else:
                print(f"⚠️ BGM 합치기 실패 (방법2): {result.stderr}")
        except Exception as e:
            print(f"⚠️ BGM 합치기 예외 (방법2): {e}")
        
        # 방법 3: BGM 없이 비디오만 처리
        try:
            print("🔄 BGM 처리 실패, 비디오만 처리...")
            cmd = [ffmpeg_path, '-i', video_file, '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p', output_path, '-y']
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ 비디오만 처리 완료 (BGM 없음)")
        except Exception as e:
            print(f"❌ 비디오 처리 최종 실패: {e}")
            raise
    
    def _concat_videos_with_bgm(self, temp_files: List[str], output_path: str, ffmpeg_path: str, bgm_file: str, bgm_volume: float = 0.4):
        """여러 비디오 concat + BGM 추가 - 강화된 오류 처리"""
        import subprocess
        import tempfile
        import time
        
        print(f"🎵 {len(temp_files)}개 비디오 concat + BGM 추가 중")
        
        # BGM 파일 존재 확인
        if not os.path.exists(bgm_file):
            print(f"⚠️ BGM 파일이 없음: {bgm_file}, BGM 없이 처리")
            self._simple_concat_only(temp_files, output_path, ffmpeg_path)
            return
        
        # 먼저 비디오들을 concat
        temp_concat_file = os.path.join(tempfile.gettempdir(), f"temp_concat_{int(time.time())}.mp4")
        
        try:
            # 1단계: 비디오 concat
            self._simple_concat_only(temp_files, temp_concat_file, ffmpeg_path)
            
            # 2단계: BGM 추가 - 여러 방법 시도
            bgm_success = False
            
            # 방법 1: 기본 오디오 믹싱
            if not bgm_success:
                try:
                    print("🔄 방법1: 기본 오디오 믹싱 시도...")
                    cmd = [
                        ffmpeg_path,
                        '-i', temp_concat_file,  # concat된 비디오
                        '-i', bgm_file,          # BGM
                        '-c:v', 'copy',          # 비디오 복사 (재인코딩 안함)
                        '-c:a', 'aac',
                        '-filter_complex', f'[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first[audio]',
                        '-map', '0:v',
                        '-map', '[audio]',
                        '-shortest',
                        output_path, '-y'
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        print("✅ 멀티 비디오 concat + BGM 합치기 완료 (방법1)")
                        bgm_success = True
                    else:
                        print(f"⚠️ 방법1 실패: {result.stderr}")
                except Exception as e:
                    print(f"⚠️ 방법1 예외: {e}")
            
            # 방법 2: 비디오 오디오 없음 가정
            if not bgm_success:
                try:
                    print("🔄 방법2: 비디오 오디오 없음 가정하고 BGM만 추가...")
                    cmd = [
                        ffmpeg_path,
                        '-i', temp_concat_file,
                        '-i', bgm_file,
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-map', '0:v',
                        '-map', '1:a',
                        '-shortest',
                        output_path, '-y'
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        print("✅ 멀티 비디오 concat + BGM 합치기 완료 (방법2)")
                        bgm_success = True
                    else:
                        print(f"⚠️ 방법2 실패: {result.stderr}")
                except Exception as e:
                    print(f"⚠️ 방법2 예외: {e}")
            
            # 방법 3: BGM 처리 포기하고 비디오만
            if not bgm_success:
                print("🔄 방법3: BGM 처리 실패, concat된 비디오만 사용...")
                import shutil
                shutil.move(temp_concat_file, output_path)
                print("✅ BGM 없이 concat 비디오 완료")
                bgm_success = True
            
        finally:
            if os.path.exists(temp_concat_file):
                try:
                    os.remove(temp_concat_file)
                except:
                    pass
    
    def _merge_with_transitions_only(self, temp_files: List[str], output_path: str, ffmpeg_path: str):
        """BGM 없이 트랜지션 효과만 적용"""
        import subprocess
        import tempfile
        import time
        import random
        
        print(f"🎬 {len(temp_files)}개 비디오에 트랜지션 효과 적용 중...")
        
        if len(temp_files) == 1:
            # 비디오가 1개면 트랜지션 없이 처리
            cmd = [ffmpeg_path, '-i', temp_files[0], '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p', output_path, '-y']
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return
        
        # 트랜지션 효과 목록 - FFmpeg xfade 필터에서 지원하는 실제 트랜지션들
        transitions = [
            'fade',           # 기본 페이드
            'fadeblack',      # 검은색 페이드
            'fadewhite',      # 흰색 페이드
            'distance',       # 거리감 효과
            'wipeleft',       # 왼쪽 와이프
            'wiperight',      # 오른쪽 와이프
            'wipeup',         # 위쪽 와이프
            'wipedown',       # 아래쪽 와이프
            'slideleft',      # 왼쪽 슬라이드
            'slideright',     # 오른쪽 슬라이드
            'slideup',        # 위쪽 슬라이드
            'slidedown',      # 아래쪽 슬라이드
            'smoothleft',     # 부드러운 왼쪽
            'smoothright',    # 부드러운 오른쪽
            'smoothup',       # 부드러운 위쪽
            'smoothdown',     # 부드러운 아래쪽
            'circleopen',     # 원형 열기
            'circleclose',    # 원형 닫기
            'vertopen',       # 세로 열기
            'vertclose',      # 세로 닫기
            'horzopen',       # 가로 열기
            'horzclose',      # 가로 닫기
            'dissolve',       # 디졸브
            'pixelize',       # 픽셀화
            'radial',         # 방사형
            'hblur',          # 수평 블러
            'wipetl',         # 왼쪽 위 와이프
            'wipetr',         # 오른쪽 위 와이프
            'wipebl',         # 왼쪽 아래 와이프
            'wipebr'          # 오른쪽 아래 와이프
        ]
        
        print(f"🎲 사용 가능한 트랜지션: {len(transitions)}개")
        
        try:
            # 복잡한 filter_complex 구성
            inputs = []
            filter_parts = []
            
            # 모든 입력 파일 추가
            for i, temp_file in enumerate(temp_files):
                inputs.extend(['-i', temp_file])
            
            # 트랜지션 필터 체인 구성
            used_transitions = []  # 사용된 트랜지션 추적
            last_transition = None  # 마지막 사용된 트랜지션 (연속 방지)
            
            for i in range(len(temp_files) - 1):
                # 연속으로 같은 트랜지션 방지
                available_transitions = [t for t in transitions if t != last_transition]
                if not available_transitions:  # 혹시 모를 경우를 대비
                    available_transitions = transitions
                
                transition = random.choice(available_transitions)
                used_transitions.append(transition)
                last_transition = transition
                transition_duration = 1.0  # 1초 트랜지션
                
                print(f"   🎬 비디오 {i+1} → {i+2}: {transition} 트랜지션 적용")
                
                if i == 0:
                    # 첫 번째 트랜지션
                    filter_parts.append(f"[{i}:v][{i+1}:v]xfade=transition={transition}:duration={transition_duration}:offset=4[v{i}]")
                else:
                    # 연속 트랜지션
                    filter_parts.append(f"[v{i-1}][{i+1}:v]xfade=transition={transition}:duration={transition_duration}:offset={4+i*4}[v{i}]")
            
            print(f"🎯 적용된 트랜지션 목록: {', '.join(used_transitions)}")
            
            # 최종 필터 구성
            filter_complex = ';'.join(filter_parts)
            final_output = f"v{len(temp_files)-2}" if len(temp_files) > 2 else "v0"
            
            print(f"🔧 트랜지션 필터: {filter_complex}")
            
            # FFmpeg 명령 실행
            cmd = inputs + [
                '-filter_complex', filter_complex,
                '-map', f'[{final_output}]',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                output_path, '-y'
            ]
            cmd.insert(0, ffmpeg_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ 트랜지션 효과 적용 완료!")
            else:
                print(f"⚠️ 트랜지션 실패, 간단한 concat으로 fallback: {result.stderr}")
                self._simple_concat_only(temp_files, output_path, ffmpeg_path)
                
        except Exception as e:
            print(f"⚠️ 트랜지션 처리 중 오류: {e}")
            print("🔄 간단한 concat으로 fallback...")
            self._simple_concat_only(temp_files, output_path, ffmpeg_path)
    
    def _merge_with_transitions_bgm_and_subtitle(self, temp_files: List[str], output_path: str, ffmpeg_path: str, bgm_file: str = None, subtitle_file: str = None, bgm_volume: float = 0.4):
        """트랜지션 효과 + BGM + 자막 통합 처리"""
        import subprocess
        import tempfile
        import time
        
        print(f"🎬 {len(temp_files)}개 비디오 트랜지션 + BGM + 자막 통합 처리 중...")
        
        # 자막 파일 경로 처리 (FFmpeg 호환 형식)
        subtitle_path_fixed = None
        if subtitle_file and os.path.exists(subtitle_file):
            subtitle_path_fixed = subtitle_file.replace("\\", "/").replace(":", "\\:")
            print(f"📝 자막 파일 준비: {subtitle_file}")
        
        # BGM 파일 확인
        bgm_available = bgm_file and os.path.exists(bgm_file)
        if bgm_available:
            print(f"🎵 BGM 파일 준비: {bgm_file}")
        
        try:
            # 방법 1: 트랜지션 + BGM + 자막 한 번에 처리 시도
            if bgm_available and subtitle_path_fixed:
                print("🔄 방법1: 트랜지션 + BGM + 자막 통합 처리...")
                success = self._try_complex_merge_with_all(temp_files, output_path, ffmpeg_path, bgm_file, subtitle_path_fixed, bgm_volume)
                if success:
                    return
            
            # 방법 2: 트랜지션 먼저, 그 다음 BGM + 자막 처리
            print("🔄 방법2: 2단계 처리 (트랜지션 → BGM + 자막)")
            temp_transition_file = os.path.join(tempfile.gettempdir(), f"temp_transitions_{int(time.time())}.mp4")
            
            try:
                # 1단계: 트랜지션만 적용
                self._merge_with_transitions_only(temp_files, temp_transition_file, ffmpeg_path)
                
                # 2단계: BGM + 자막 추가
                self._merge_single_video_with_bgm_and_subtitle(temp_transition_file, output_path, ffmpeg_path, bgm_file, subtitle_file, bgm_volume)
                
                print("✅ 2단계 트랜지션 + BGM + 자막 처리 완료!")
                
            finally:
                if os.path.exists(temp_transition_file):
                    try:
                        os.remove(temp_transition_file)
                    except:
                        pass
            
        except Exception as e:
            print(f"⚠️ 통합 처리 실패: {e}")
            print("🔄 최종 fallback: 간단한 concat + BGM + 자막")
            
            # 최종 fallback: concat + BGM/자막 처리
            temp_concat_file = os.path.join(tempfile.gettempdir(), f"temp_concat_fallback_{int(time.time())}.mp4")
            
            try:
                self._simple_concat_only(temp_files, temp_concat_file, ffmpeg_path)
                self._merge_single_video_with_bgm_and_subtitle(temp_concat_file, output_path, ffmpeg_path, bgm_file, subtitle_file, bgm_volume)
            finally:
                if os.path.exists(temp_concat_file):
                    try:
                        os.remove(temp_concat_file)
                    except:
                        pass
    
    def _try_complex_merge_with_all(self, temp_files: List[str], output_path: str, ffmpeg_path: str, bgm_file: str, subtitle_path_fixed: str, bgm_volume: float = 0.4):
        """복잡한 통합 처리 시도 (트랜지션 + BGM + 자막)"""
        import subprocess
        import random
        
        try:
            # 트랜지션 효과 목록
            transitions = [
                'fade', 'fadeblack', 'fadewhite', 'distance', 'wipeleft', 'wiperight', 
                'wipeup', 'wipedown', 'slideleft', 'slideright', 'slideup', 'slidedown',
                'smoothleft', 'smoothright', 'smoothup', 'smoothdown', 'circleopen', 
                'circleclose', 'vertopen', 'vertclose', 'horzopen', 'horzclose',
                'dissolve', 'pixelize', 'radial', 'hblur'
            ]
            
            inputs = []
            filter_parts = []
            
            # 비디오 입력들
            for i, temp_file in enumerate(temp_files):
                inputs.extend(['-i', temp_file])
            
            # BGM 입력
            inputs.extend(['-i', bgm_file])
            bgm_index = len(temp_files)
            
            # 트랜지션 필터 체인 구성
            last_transition = None
            for i in range(len(temp_files) - 1):
                available_transitions = [t for t in transitions if t != last_transition]
                if not available_transitions:
                    available_transitions = transitions
                
                transition = random.choice(available_transitions)
                last_transition = transition
                transition_duration = 1.0
                
                print(f"   🎬 비디오 {i+1} → {i+2}: {transition} 트랜지션 (BGM+자막)")
                
                if i == 0:
                    filter_parts.append(f"[{i}:v][{i+1}:v]xfade=transition={transition}:duration={transition_duration}:offset=4[v{i}]")
                else:
                    filter_parts.append(f"[v{i-1}][{i+1}:v]xfade=transition={transition}:duration={transition_duration}:offset={4+i*4}[v{i}]")
            
            # BGM 오디오 처리
            filter_parts.append(f"[{bgm_index}:a]volume={bgm_volume}[bgm]")
            filter_parts.append(f"[0:a][bgm]amix=inputs=2:duration=first[audio]")
            
            filter_complex = ';'.join(filter_parts)
            final_video = f"v{len(temp_files)-2}" if len(temp_files) > 2 else "v0"
            
            # FFmpeg 명령 실행
            cmd = inputs + [
                '-filter_complex', filter_complex,
                '-vf', f"subtitles='{subtitle_path_fixed}'",  # 자막 추가
                '-map', f'[{final_video}]',
                '-map', '[audio]',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-shortest',
                output_path, '-y'
            ]
            cmd.insert(0, ffmpeg_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ 트랜지션 + BGM + 자막 통합 처리 완료!")
                return True
            else:
                print(f"⚠️ 통합 처리 실패: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"⚠️ 복잡한 통합 처리 중 오류: {e}")
            return False
    
    def _merge_with_transitions_and_bgm(self, temp_files: List[str], output_path: str, ffmpeg_path: str, bgm_file: str, bgm_volume: float = 0.4):
        """트랜지션 효과 + BGM 통합 처리"""
        import subprocess
        import tempfile
        import time
        import random
        
        print(f"🎬🎵 {len(temp_files)}개 비디오에 트랜지션 + BGM 적용 중...")
        
        # BGM 파일 존재 확인
        if not os.path.exists(bgm_file):
            print(f"⚠️ BGM 파일이 없음: {bgm_file}, 트랜지션만 적용")
            self._merge_with_transitions_only(temp_files, output_path, ffmpeg_path)
            return
        
        if len(temp_files) == 1:
            # 비디오가 1개면 BGM만 추가
            self._merge_single_video_with_bgm(temp_files[0], output_path, ffmpeg_path, bgm_file, bgm_volume)
            return
        
        # 트랜지션 효과 목록 - 더 다양한 효과들
        transitions = [
            'fade',           # 기본 페이드
            'fadeblack',      # 검은색 페이드
            'fadewhite',      # 흰색 페이드
            'distance',       # 거리감 효과
            'wipeleft',       # 왼쪽 와이프
            'wiperight',      # 오른쪽 와이프
            'wipeup',         # 위쪽 와이프
            'wipedown',       # 아래쪽 와이프
            'slideleft',      # 왼쪽 슬라이드
            'slideright',     # 오른쪽 슬라이드
            'slideup',        # 위쪽 슬라이드
            'slidedown',      # 아래쪽 슬라이드
            'smoothleft',     # 부드러운 왼쪽
            'smoothright',    # 부드러운 오른쪽
            'smoothup',       # 부드러운 위쪽
            'smoothdown',     # 부드러운 아래쪽
            'circleopen',     # 원형 열기
            'circleclose',    # 원형 닫기
            'vertopen',       # 세로 열기
            'vertclose',      # 세로 닫기
            'horzopen',       # 가로 열기
            'horzclose',      # 가로 닫기
            'dissolve',       # 디졸브
            'pixelize',       # 픽셀화
            'radial',         # 방사형
            'hblur'           # 수평 블러
        ]
        
        try:
            # 방법 1: 트랜지션 + BGM 한 번에 처리
            inputs = []
            filter_parts = []
            
            # 비디오 입력들
            for i, temp_file in enumerate(temp_files):
                inputs.extend(['-i', temp_file])
            
            # BGM 입력
            inputs.extend(['-i', bgm_file])
            bgm_index = len(temp_files)
            
            # 트랜지션 필터 체인 구성
            used_transitions_bgm = []  # BGM 버전에서 사용된 트랜지션 추적
            last_transition_bgm = None  # 마지막 사용된 트랜지션 (연속 방지)
            
            for i in range(len(temp_files) - 1):
                # 연속으로 같은 트랜지션 방지
                available_transitions = [t for t in transitions if t != last_transition_bgm]
                if not available_transitions:
                    available_transitions = transitions
                
                transition = random.choice(available_transitions)
                used_transitions_bgm.append(transition)
                last_transition_bgm = transition
                transition_duration = 1.0
                
                print(f"   🎬🎵 비디오 {i+1} → {i+2}: {transition} 트랜지션 적용 (BGM 포함)")
                
                if i == 0:
                    filter_parts.append(f"[{i}:v][{i+1}:v]xfade=transition={transition}:duration={transition_duration}:offset=4[v{i}]")
                else:
                    filter_parts.append(f"[v{i-1}][{i+1}:v]xfade=transition={transition}:duration={transition_duration}:offset={4+i*4}[v{i}]")
            
            print(f"🎯 BGM 포함 적용된 트랜지션: {', '.join(used_transitions_bgm)}")
            
            # BGM 오디오 처리
            filter_parts.append(f"[{bgm_index}:a]volume={bgm_volume}[bgm]")
            
            # 비디오 오디오와 BGM 믹싱 (첫 번째 비디오의 오디오 사용)
            filter_parts.append(f"[0:a][bgm]amix=inputs=2:duration=first[audio]")
            
            filter_complex = ';'.join(filter_parts)
            final_video = f"v{len(temp_files)-2}" if len(temp_files) > 2 else "v0"
            
            print(f"🔧 트랜지션+BGM 필터: {filter_complex}")
            
            cmd = inputs + [
                '-filter_complex', filter_complex,
                '-map', f'[{final_video}]',
                '-map', '[audio]',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-shortest',
                output_path, '-y'
            ]
            cmd.insert(0, ffmpeg_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ 트랜지션 + BGM 통합 처리 완료!")
                return
            else:
                print(f"⚠️ 통합 처리 실패: {result.stderr}")
                
        except Exception as e:
            print(f"⚠️ 트랜지션+BGM 통합 처리 중 오류: {e}")
        
        # 방법 2: 트랜지션 먼저, BGM 나중에
        print("🔄 2단계 처리: 트랜지션 → BGM")
        temp_transition_file = os.path.join(tempfile.gettempdir(), f"temp_transitions_{int(time.time())}.mp4")
        
        try:
            # 1단계: 트랜지션만 적용
            self._merge_with_transitions_only(temp_files, temp_transition_file, ffmpeg_path)
            
            # 2단계: BGM 추가
            self._merge_single_video_with_bgm(temp_transition_file, output_path, ffmpeg_path, bgm_file, bgm_volume)
            
            print("✅ 2단계 트랜지션 + BGM 처리 완료!")
            
        except Exception as e:
            print(f"⚠️ 2단계 처리도 실패: {e}")
            print("🔄 최종 fallback: concat + BGM")
            self._concat_videos_with_bgm(temp_files, output_path, ffmpeg_path, bgm_file, bgm_volume)
            
        finally:
            if os.path.exists(temp_transition_file):
                try:
                    os.remove(temp_transition_file)
                except:
                    pass
    
    def _simple_concat_only(self, temp_files: List[str], output_path: str, ffmpeg_path: str):
        """BGM 없이 비디오들만 concat"""
        import subprocess
        import tempfile
        import time
        
        concat_file = os.path.join(tempfile.gettempdir(), f"concat_list_{int(time.time())}.txt")
        
        try:
            with open(concat_file, 'w') as f:
                for temp_file in temp_files:
                    f.write(f"file '{os.path.abspath(temp_file)}'\n")
            
            cmd = [
                ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                output_path, '-y'
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ {len(temp_files)}개 비디오 concat 완료")
            
        finally:
            if os.path.exists(concat_file):
                os.remove(concat_file)
    
    def _merge_with_transitions(self, temp_files: List[str], output_path: str, ffmpeg_path: str, target_width: int, target_height: int, target_fps: float):
        """트랜지션 효과와 함께 비디오 합치기 - 비디오 길이 보존"""
        import subprocess
        import random
        import os
        
        # 해상도 유효성 검사
        if target_width <= 0 or target_height <= 0:
            print(f"❌ 잘못된 해상도: {target_width}x{target_height}. 기본값 사용...")
            target_width, target_height = 1280, 720
            
        if target_fps <= 0 or target_fps > 60:
            print(f"❌ 잘못된 fps: {target_fps}. 기본값 사용...")
            target_fps = 30.0
        
        print(f"🎯 검증된 해상도: {target_width}x{target_height} @ {target_fps}fps")
        
        # 더 안전한 트랜지션 목록
        safe_transitions = ['fade', 'wipeleft', 'wiperight', 'slidedown', 'slideup']
        
        print(f"🎬 {len(temp_files)}개 비디오를 트랜지션으로 합치기 시작")
        
        if len(temp_files) == 1:
            # 파일이 1개면 트랜지션 없이 처리
            print("📹 비디오가 1개뿐이므로 트랜지션 없이 처리합니다.")
            cmd = [
                ffmpeg_path,
                '-i', temp_files[0],
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                output_path, '-y'
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return
        
        # 모든 비디오를 간단한 concat으로 합치기 (트랜지션 없이)
        print("� 모든 비디오를 순서대로 concat으로 합치는 중...")
        
        # concat 리스트 파일 생성
        import tempfile
        import time
        concat_file = os.path.join(tempfile.gettempdir(), f"transition_concat_{int(time.time())}.txt")
        
        try:
            with open(concat_file, 'w') as f:
                for temp_file in temp_files:
                    f.write(f"file '{os.path.abspath(temp_file)}'\n")
            
            # 단순 concat으로 모든 비디오 합치기 (각 비디오 전체 길이 보존)
            cmd = [
                ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                '-r', str(int(target_fps)),
                output_path, '-y'
            ]
            
            print(f"🔧 FFmpeg concat 명령 실행 중...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"❌ Concat 실패: {result.stderr}")
                raise Exception(f"비디오 concat 실패: {result.stderr}")
            
            print(f"✅ {len(temp_files)}개 비디오 concat 완료!")
            
        finally:
            # 임시 파일 정리
            if os.path.exists(concat_file):
                os.remove(concat_file)
    
    def _simple_original_concat(self, temp_files: List[str], output_path: str, ffmpeg_path: str):
        """원본 파일들을 그대로 이어 붙이기 (스케일링 없음)"""
        import subprocess
        import tempfile
        import os
        import time
        
        try:
            print(f"🔗 {len(temp_files)}개 비디오를 원본 그대로 concat 방식으로 합치는 중...")
            
            # concat 리스트 파일 생성
            concat_file = os.path.join(tempfile.gettempdir(), f"original_concat_{int(time.time())}.txt")
            with open(concat_file, 'w') as f:
                for temp_file in temp_files:
                    f.write(f"file '{os.path.abspath(temp_file)}'\n")
            
            # 원본 파일들을 그대로 concat으로 합치기
            cmd = [
                ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',  # 코덱 복사 (재인코딩 없음)
                output_path, '-y'
            ]
            
            print("🔧 원본 파일 concat 명령 실행 중...")
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ {len(temp_files)}개 비디오 원본 그대로 concat 완료")
            
            # 임시 파일 정리
            if os.path.exists(concat_file):
                os.remove(concat_file)
                
        except Exception as e:
            print(f"❌ 원본 concat 처리 실패: {e}")
            print("🔄 호환성을 위한 재인코딩 concat 시도...")
            
            # 재인코딩으로 호환성 확보
            concat_file = os.path.join(tempfile.gettempdir(), f"reencoded_concat_{int(time.time())}.txt")
            with open(concat_file, 'w') as f:
                for temp_file in temp_files:
                    f.write(f"file '{os.path.abspath(temp_file)}'\n")
            
            cmd = [
                ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',  # 재인코딩
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                output_path, '-y'
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ 재인코딩 concat 완료")
            
            if os.path.exists(concat_file):
                os.remove(concat_file)
    
    def _simple_concat(self, temp_files: List[str], output_path: str, ffmpeg_path: str, target_width: int, target_height: int, target_fps: float):
        """간단한 concat으로 비디오 합치기 (fallback) - 원본 비율 유지"""
        import subprocess
        import tempfile
        import os
        import time
        
        # 해상도 유효성 검사
        if target_width <= 0 or target_height <= 0:
            print(f"❌ 잘못된 해상도: {target_width}x{target_height}. 기본값 사용...")
            target_width, target_height = 1280, 720
            
        if target_fps <= 0 or target_fps > 60:
            print(f"❌ 잘못된 fps: {target_fps}. 기본값 사용...")
            target_fps = 30.0
        
        print(f"🎯 검증된 해상도: {target_width}x{target_height} @ {target_fps}fps")
        
        try:
            print(f"🔗 {len(temp_files)}개 비디오를 원본 비율 유지 concat 방식으로 합치는 중...")
            
            # 모든 비디오를 동일한 포맷으로 정규화 (원본 비율 유지)
            normalized_files = []
            for i, temp_file in enumerate(temp_files):
                normalized_file = os.path.join(tempfile.gettempdir(), f"normalized_{i}_{int(time.time())}.mp4")
                normalize_cmd = [
                    ffmpeg_path,
                    '-i', temp_file,
                    # 원본 비율 유지하면서 목표 해상도에 맞추기 (패딩 없음)
                    '-vf', f'scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,fps={target_fps}',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-pix_fmt', 'yuv420p',
                    '-r', str(int(target_fps)),
                    normalized_file, '-y'
                ]
                subprocess.run(normalize_cmd, check=True, capture_output=True, text=True)
                normalized_files.append(normalized_file)
            
            # concat 리스트 파일 생성
            concat_file = os.path.join(tempfile.gettempdir(), f"concat_list_{int(time.time())}.txt")
            with open(concat_file, 'w') as f:
                for normalized_file in normalized_files:
                    f.write(f"file '{os.path.abspath(normalized_file)}'\n")
            
            # concat으로 합치기
            cmd = [
                ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                output_path, '-y'
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ {len(temp_files)}개 비디오 원본 비율 유지 concat 합치기 완료")
            
            # 임시 파일들 정리
            for normalized_file in normalized_files:
                if os.path.exists(normalized_file):
                    os.remove(normalized_file)
            if os.path.exists(concat_file):
                os.remove(concat_file)
                
        except Exception as e:
            print(f"❌ 정규화된 concat 처리 실패: {e}")
            # 최후의 수단으로 기본 concat 시도
            concat_file = os.path.join(tempfile.gettempdir(), "concat_list.txt")
            with open(concat_file, 'w') as f:
                for temp_file in temp_files:
                    f.write(f"file '{temp_file}'\n")
            
            subprocess.run([
                ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', concat_file,
                '-c', 'copy', output_path, '-y'
            ], check=True, capture_output=True, text=True)
            
            os.remove(concat_file)
            print("✅ 기본 concat 합치기 완료")
    
    def get_video_url(self, filename: str) -> str:
        """비디오 URL 생성"""
        if self.use_static_dir:
            return f"/static/videos/{filename}"
        else:
            return f"/output_videos/{filename}"

def generate_output_filename(prefix: str) -> str:
    """타임스탬프를 포함한 출력 파일명 생성"""
    timestamp = int(time.time())  # 현재 시간을 유닉스 타임스탬프로 변환 (정수형)
    return f"{prefix}_{timestamp}.mp4"  # "접두사_타임스탬프.mp4" 형식으로 파일명 생성

def create_video_response(message: str, filename: str, video_url: str, 
                         local_path: str, video_count: int, method: str = None):
    """비디오 응답 객체 생성"""
    timestamp = int(time.time())  # 응답 생성 시간을 타임스탬프로 기록
    response = {  # API 응답으로 보낼 딕셔너리 객체 생성
        "message": message,  # 처리 완료 메시지
        "video_url": video_url,  # 생성된 영상에 접근할 수 있는 URL
        "final_video": {  # 최종 영상에 대한 상세 정보
            "filename": filename,  # 저장된 파일명
            "url": video_url,  # 웹에서 접근 가능한 URL
            "local_path": local_path,  # 서버 내 파일 경로
            "source_videos_count": video_count,  # 원본 영상 개수
            "created_at": timestamp  # 생성 시간 (유닉스 타임스탬프)
        },
        "summary": {  # 처리 결과 요약 정보
            "total_source_videos": video_count,  # 합쳐진 원본 영상 총 개수
            "output_filename": filename,  # 출력 파일명
            "video_url": video_url  # 접근 URL (중복이지만 편의를 위해 포함)
        },
        "access": {  # 영상 접근 방법 안내
            "direct_url": video_url,  # 직접 접근 URL
            "browser_view": f"브라우저에서 {video_url} 접속하여 영상 재생 가능"  # 사용법 안내 메시지
        }
    }
    
    if method:  # 처리 방법이 지정된 경우
        response["method"] = method  # 응답에 처리 방법 정보 추가
        response["summary"]["processing_method"] = method  # 요약에도 처리 방법 추가
    
    return response  # 완성된 응답 객체 반환

def get_transition_description(transition: str) -> str:
    """트랜지션 설명 반환"""
    descriptions = {  # 각 트랜지션 효과에 대한 한국어 설명 딕셔너리
        'zoom_in': '줌 인 - 확대에서 원본으로',  # 확대된 상태에서 원본 크기로 줄어드는 효과
        'zoom_out': '줌 아웃 - 원본에서 확대로',  # 원본 크기에서 확대되는 효과
        'pan_right': '팬 우측 - 왼쪽에서 오른쪽으로',  # 왼쪽에서 시작해서 오른쪽으로 이동하는 효과
        'pan_left': '팬 좌측 - 오른쪽에서 왼쪽으로',  # 오른쪽에서 시작해서 왼쪽으로 이동하는 효과
        'pan_up': '팬 상단 - 아래에서 위로',  # 아래에서 시작해서 위로 이동하는 효과
        'pan_down': '팬 하단 - 위에서 아래로',  # 위에서 시작해서 아래로 이동하는 효과
        'rotate_clockwise': '시계방향 회전',  # 시계 방향으로 회전하는 효과
        'rotate_counter_clockwise': '반시계방향 회전',  # 반시계 방향으로 회전하는 효과
        'fade': '페이드 - 기본 페이드 인/아웃'  # 서서히 나타나거나 사라지는 기본 효과
    }
    return descriptions.get(transition, transition)  # 딕셔너리에서 설명 찾기, 없으면 원본 이름 반환
