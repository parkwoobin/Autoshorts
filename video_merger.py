"""
영상 합치기 및 고급 A→B 트랜지션 효과를 위한 VideoTransitionMerger 클래스
"""
import os
import random
import tempfile
import time
from typing import List
import httpx

# transitions 모듈 import
from transitions import VideoTransitions
from video_models import VideoConfig
from bgm_utils import BGMManager

try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MoviePy import 실패: {e}")
    MOVIEPY_AVAILABLE = False

class VideoTransitionMerger:
    """영상 합치기 및 고급 A→B 트랜지션 효과 클래스"""
    
    def __init__(self, use_static_dir=False, enable_bgm=True):
        if not MOVIEPY_AVAILABLE:
            raise ImportError("MoviePy가 설치되지 않았거나 import할 수 없습니다.")
        self.transition_duration = VideoConfig.TRANSITION_DURATION  # 트랜지션 효과 시간
        
        # BGM 관리자 초기화
        self.enable_bgm = enable_bgm and VideoConfig.BGM_ENABLED
        if self.enable_bgm:
            try:
                self.bgm_manager = BGMManager()
                print("🎵 BGM 관리자 초기화 완료")
            except Exception as e:
                print(f"⚠️ BGM 관리자 초기화 실패: {e}")
                self.enable_bgm = False
                self.bgm_manager = None
        else:
            self.bgm_manager = None
        
        # 정적 파일 디렉토리 사용 여부
        if use_static_dir:
            import os
            self.temp_dir = os.path.join(os.getcwd(), "static", "videos")
            os.makedirs(self.temp_dir, exist_ok=True)
            self.is_static = True
        else:
            self.temp_dir = tempfile.mkdtemp()  # 임시 파일 저장 디렉토리
            self.is_static = False
    
    def get_video_url(self, filename: str) -> str:
        """정적 파일 URL 생성"""
        if self.is_static:
            return f"http://localhost:8000/static/videos/{filename}"
        else:
            return f"file://{os.path.join(self.temp_dir, filename)}"
    
    def create_sequential_showcase(self, sample_videos=None, output_filename="all_transitions_showcase.mp4"):
        """모든 트랜지션을 순차적으로 보여주는 영상 생성"""
        if sample_videos is None:
            sample_videos = [
                "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
                "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4",
                "https://dnznrvs05pmza.cloudfront.net/606e42bf-f1c8-4e72-bcd6-58bb3510a83c.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk4ZDU5OTA4MTFmMmUwNCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.__LNtAR_id8J-SlQsxobOGiDLAWgJiESavXTqLlZvSQ"
            ]
        
        # 모든 트랜지션 타입 가져오기
        transitions = VideoTransitions.get_available_transitions()
        
        # 타임스탬프 추가
        timestamp = int(time.time() * 1000)
        output_filename = f"all_transitions_showcase_{timestamp}.mp4"
        
        print(f"🎬 {len(transitions)}개 트랜지션으로 쇼케이스 영상 생성: {output_filename}")
        
        try:
            # 영상들을 다운로드하고 클립으로 변환
            video_clips = []
            for i, video_url in enumerate(sample_videos):
                print(f"📥 영상 {i+1} 다운로드 중: {video_url[:50]}...")
                temp_path = self._download_video(video_url, f"temp_video_{i}.mp4")
                clip = VideoFileClip(temp_path)
                
                # 표준 해상도로 리사이즈
                clip = clip.resize(newsize=(VideoConfig.RESOLUTION_WIDTH, VideoConfig.RESOLUTION_HEIGHT))
                # 영상 길이를 5초로 제한 (데모용)
                clip = clip.subclip(0, min(5, clip.duration))
                video_clips.append(clip)
            
            print(f"✅ {len(video_clips)}개 영상 준비 완료")
            
            # 트랜지션이 있는 클립들 생성
            final_clips = []
            
            for i, (transition_type, transition_name) in enumerate(transitions):
                print(f"🎨 트랜지션 {i+1}/{len(transitions)} 생성: {transition_name}")
                
                # 영상 클립들을 순환 사용
                clip_a = video_clips[i % len(video_clips)]
                clip_b = video_clips[(i + 1) % len(video_clips)]
                
                # 첫 번째 비디오의 전체 길이에서 트랜지션 길이만큼 뺀 부분을 먼저 추가
                if i == 0:
                    # 첫 번째 클립은 전체 길이로 추가
                    main_part_a = clip_a.subclip(0, clip_a.duration - self.transition_duration)
                    final_clips.append(main_part_a)
                
                # 트랜지션 적용
                transitioned_clip = VideoTransitions.create_transition(
                    clip_a=clip_a,
                    clip_b=clip_b,
                    transition_type=transition_type,
                    duration=self.transition_duration
                )
                final_clips.append(transitioned_clip)
                
                # 두 번째 비디오의 트랜지션 이후 부분 추가 (마지막이 아닌 경우)
                if i < len(transitions) - 1:
                    main_part_b = clip_b.subclip(self.transition_duration, clip_b.duration - self.transition_duration)
                    final_clips.append(main_part_b)
                else:
                    # 마지막 클립은 트랜지션 이후 끝까지 추가
                    main_part_b = clip_b.subclip(self.transition_duration, clip_b.duration)
                    final_clips.append(main_part_b)
            
            print("🔗 모든 클립 연결 중...")
            # 모든 클립을 하나로 연결
            final_video = concatenate_videoclips(final_clips, method="compose")
            
            # BGM 추가
            if self.enable_bgm and self.bgm_manager:
                print("🎵 BGM 추가 중...")
                final_video = self.bgm_manager.add_bgm_to_video(
                    final_video, 
                    volume_adjustment=VideoConfig.BGM_VOLUME
                )
            
            # 출력 파일 경로
            output_path = os.path.join(self.temp_dir, output_filename)
            
            print(f"💾 최종 영상 저장 중: {output_path}")
            # 영상 저장
            final_video.write_videofile(
                output_path,
                fps=VideoConfig.FPS,
                audio_codec='aac',
                codec='libx264',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            # 메모리 정리
            for clip in video_clips:
                clip.close()
            for clip in final_clips:
                clip.close()
            final_video.close()
            
            # 임시 파일 정리
            temp_files = self._collect_temp_files("temp_video_")
            if temp_files:
                print("🧹 임시 파일 정리 중...")
                self._cleanup_temp_files(temp_files)
            
            print(f"✅ 쇼케이스 영상 생성 완료: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 쇼케이스 영상 생성 실패: {e}")
            raise
    
    def merge_videos_streaming(self, video_urls: List[str], output_filename: str = "merged_video.mp4") -> str:
        """스트리밍 URL들을 다운로드하고 합치기"""
        print(f"🎬 {len(video_urls)}개 영상 스트리밍 합치기 시작...")
        
        try:
            # 영상들을 다운로드하고 클립으로 변환
            video_clips = []
            for i, video_url in enumerate(video_urls):
                print(f"📥 영상 {i+1} 다운로드 중...")
                temp_path = self._download_video(video_url, f"temp_video_{i}.mp4")
                clip = VideoFileClip(temp_path)
                
                # 표준 해상도로 리사이즈
                clip = clip.resize(newsize=(VideoConfig.RESOLUTION_WIDTH, VideoConfig.RESOLUTION_HEIGHT))
                video_clips.append(clip)
            
            print("🔗 모든 클립 연결 중...")
            # 모든 클립을 하나로 연결
            final_video = concatenate_videoclips(video_clips, method="compose")
            
            # BGM 추가
            if self.enable_bgm and self.bgm_manager:
                print("🎵 BGM 추가 중...")
                final_video = self.bgm_manager.add_bgm_to_video(
                    final_video, 
                    volume_adjustment=VideoConfig.BGM_VOLUME
                )
            
            # 출력 파일 경로
            output_path = os.path.join(self.temp_dir, output_filename)
            
            print(f"💾 최종 영상 저장 중: {output_path}")
            # 영상 저장
            final_video.write_videofile(
                output_path,
                fps=VideoConfig.FPS,
                audio_codec='aac',
                codec='libx264',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            # 메모리 정리
            for clip in video_clips:
                clip.close()
            final_video.close()
            
            # 임시 파일 정리
            temp_files = self._collect_temp_files("temp_video_")
            if temp_files:
                print("🧹 임시 파일 정리 중...")
                self._cleanup_temp_files(temp_files)
            
            print(f"✅ 영상 합치기 완료: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 영상 합치기 실패: {e}")
            raise
    
    def merge_videos_with_transitions(self, video_urls: List[str], output_filename: str = "merged_with_transitions.mp4") -> str:
        """영상들을 랜덤 트랜지션으로 합치기 (통합된 메서드)"""
        timestamp = int(time.time() * 1000)
        output_filename = f"frame_transitions_{timestamp}.mp4"
        
        print(f"� {len(video_urls)}개 영상을 랜덤 트랜지션으로 합치기 시작...")
        
        try:
            # 영상들을 다운로드하고 클립으로 변환
            video_clips = []
            temp_files = []  # 임시 파일 추적용
            
            for i, video_url in enumerate(video_urls):
                print(f"📥 영상 {i+1} 다운로드 중...")
                temp_path = self._download_video(video_url, f"temp_video_{i}.mp4")
                temp_files.append(temp_path)  # 임시 파일 목록에 추가
                
                clip = VideoFileClip(temp_path)
                # 표준 해상도로 리사이즈
                clip = clip.resize(newsize=(VideoConfig.RESOLUTION_WIDTH, VideoConfig.RESOLUTION_HEIGHT))
                video_clips.append(clip)
            
            print(f"✅ {len(video_clips)}개 영상 준비 완료")
            
            if len(video_clips) < 2:
                print("⚠️ 트랜지션을 위해서는 최소 2개의 영상이 필요합니다.")
                # 단순 연결로 처리
                final_video = concatenate_videoclips(video_clips, method="compose")
            else:
                # 랜덤 트랜지션으로 영상들 사이에 전환 효과 생성
                final_clips = []
                
                # 가능한 트랜지션 타입들
                available_transitions = [
                    'zoom_in', 'zoom_out', 'pan_right', 'pan_left', 
                    'pan_up', 'pan_down', 'rotate_clockwise', 'rotate_counter_clockwise', 'fade'
                ]
                
                for i in range(len(video_clips)):
                    # 현재 영상의 메인 부분 추가
                    if i == 0:
                        # 첫 번째 영상: 전체 길이에서 트랜지션 길이만큼 빼고 사용
                        main_part = video_clips[i].subclip(0, video_clips[i].duration - self.transition_duration)
                        final_clips.append(main_part)
                    
                    # 다음 영상이 있으면 트랜지션 생성
                    if i < len(video_clips) - 1:
                        # 랜덤 트랜지션 선택
                        transition_type = random.choice(available_transitions)
                        print(f"🎨 트랜지션 {i+1}: {transition_type}")
                        
                        # 트랜지션 적용
                        transitioned_clip = VideoTransitions.create_transition(
                            clip_a=video_clips[i],
                            clip_b=video_clips[i + 1],
                            transition_type=transition_type,
                            duration=self.transition_duration
                        )
                        final_clips.append(transitioned_clip)
                        
                        # 다음 영상의 메인 부분 (마지막이 아닌 경우)
                        if i < len(video_clips) - 2:
                            main_part = video_clips[i + 1].subclip(
                                self.transition_duration, 
                                video_clips[i + 1].duration - self.transition_duration
                            )
                            final_clips.append(main_part)
                        else:
                            # 마지막 영상: 트랜지션 이후 끝까지
                            main_part = video_clips[i + 1].subclip(
                                self.transition_duration, 
                                video_clips[i + 1].duration
                            )
                            final_clips.append(main_part)
                
                print("🔗 모든 클립 연결 중...")
                # 모든 클립을 하나로 연결
                final_video = concatenate_videoclips(final_clips, method="compose")
            
            # BGM 추가
            if self.enable_bgm and self.bgm_manager:
                print("🎵 BGM 추가 중...")
                final_video = self.bgm_manager.add_bgm_to_video(
                    final_video, 
                    volume_adjustment=VideoConfig.BGM_VOLUME
                )
            
            # 출력 파일 경로
            output_path = os.path.join(self.temp_dir, output_filename)
            
            print(f"💾 최종 영상 저장 중: {output_path}")
            # 영상 저장
            final_video.write_videofile(
                output_path,
                fps=VideoConfig.FPS,
                audio_codec='aac',
                codec='libx264',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            # 메모리 정리
            for clip in video_clips:
                clip.close()
            if 'final_clips' in locals():
                for clip in final_clips:
                    clip.close()
            final_video.close()
            
            # 임시 파일 정리
            if temp_files:
                print("🧹 임시 파일 정리 중...")
                self._cleanup_temp_files(temp_files)
            
            print(f"✅ 트랜지션 영상 합치기 완료: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 트랜지션 영상 합치기 실패: {e}")
            raise
    
    # merge_videos_with_frame_transitions는 기존 메서드와 동일하므로 alias로 처리
    def merge_videos_with_frame_transitions(self, video_urls: List[str], output_filename: str = "merged_frame_transitions.mp4") -> str:
        """Frame-level animation 랜덤 트랜지션으로 합치기 (alias 메서드)"""
        return self.merge_videos_with_transitions(video_urls, output_filename)
    
    def _download_video(self, video_url: str, filename: str) -> str:
        """영상을 다운로드하고 임시 파일 경로 반환"""
        temp_path = os.path.join(self.temp_dir, filename)
        
        try:
            with httpx.stream("GET", video_url, timeout=30.0) as response:
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            
            return temp_path
        except Exception as e:
            print(f"❌ 영상 다운로드 실패 {video_url}: {e}")
            raise

    def _cleanup_temp_files(self, temp_files: List[str]):
        """임시 파일들 정리"""
        cleaned_count = 0
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    cleaned_count += 1
                    print(f"🗑️ 임시 파일 삭제: {os.path.basename(temp_file)}")
            except Exception as e:
                print(f"⚠️ 임시 파일 삭제 실패 {os.path.basename(temp_file)}: {e}")
        
        if cleaned_count > 0:
            print(f"✅ {cleaned_count}개 임시 파일 정리 완료")
    
    def _collect_temp_files(self, pattern: str = "temp_video_") -> List[str]:
        """임시 파일 경로들 수집"""
        temp_files = []
        if os.path.exists(self.temp_dir):
            for filename in os.listdir(self.temp_dir):
                if filename.startswith(pattern) and filename.endswith('.mp4'):
                    temp_files.append(os.path.join(self.temp_dir, filename))
        return temp_files
