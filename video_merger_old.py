"""
5단계에서 생성된 영상들을 moviepy로 합치면서 고급 A→B 트랜지션 효과 추가
모든 트랜지션은 A 영상에서 B 영상으로 자연스럽게 전환되는 진정한 A→B 트랜지션
트랜지션 시간: 1초, 부드러운 ease-in-out 곡선 적용
"""
import os
import random
import tempfile
from typing import List, Tuple
import httpx

# transitions 모듈 import
from transitions import VideoTransitions
from video_models import VideoConfig

try:
    from moviepy.editor import (
        VideoFileClip, concatenate_videoclips, CompositeVideoClip,
        ImageClip, ColorClip, VideoClip
    )
    from moviepy.video.fx import resize, fadein, fadeout
    import numpy as np
    import cv2
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MoviePy import 실패: {e}")
    MOVIEPY_AVAILABLE = False

class VideoTransitionMerger:
    """영상 합치기 및 고급 A→B 트랜지션 효과 클래스"""
    
    def __init__(self, use_static_dir=False):
        if not MOVIEPY_AVAILABLE:
            raise ImportError("MoviePy가 설치되지 않았거나 import할 수 없습니다.")
        self.transition_duration = VideoConfig.TRANSITION_DURATION  # 트랜지션 효과 시간
        
        # 정적 파일 디렉토리 사용 여부
        if use_static_dir:
            import os
            self.temp_dir = os.path.join(os.getcwd(), "static", "videos")
            os.makedirs(self.temp_dir, exist_ok=True)
            self.is_static = True
        else:
            self.temp_dir = tempfile.mkdtemp()  # 임시 파일 저장 디렉토리
            self.is_static = False
    
    def create_sequential_showcase(self, sample_videos=None, output_filename="all_transitions_showcase.mp4"):
        """모든 트랜지션을 순차적으로 보여주는 영상 생성"""
        if sample_videos is None:
            sample_videos = [
                "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
                "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4",
                "https://dnznrvs05pmza.cloudfront.net/606e42bf-f1c8-4e72-bcd6-58bb3510a83c.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk4ZDU5OTA4MTFmMmUwNCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.__LNtAR_id8J-SlQsxobOGiDLAWgJiESavXTqLlZvSQ"
            ]
        
        print(f"🎬 모든 트랜지션 쇼케이스 영상 생성 시작...")
        
        try:
            # 샘플 영상들 로드
            clips = []
            for i, url in enumerate(sample_videos):
                try:
                    print(f"📹 샘플 영상 {i+1} 로딩 중...")
                    clip = VideoFileClip(url)
                    # VideoConfig의 설정에 맞게 영상 처리
                    # 해상도 통일
                    clip = clip.resize((VideoConfig.RESOLUTION_WIDTH, VideoConfig.RESOLUTION_HEIGHT))
                    # FPS 통일
                    clip = clip.set_fps(VideoConfig.DEFAULT_FPS)
                    # 기본 길이로 자르기
                    if clip.duration > VideoConfig.DEFAULT_DURATION:
                        clip = clip.subclip(0, VideoConfig.DEFAULT_DURATION)
                    clips.append(clip)
                    print(f"✅ 샘플 영상 {i+1} 로드 완료 (길이: {clip.duration:.2f}초, 해상도: {VideoConfig.RESOLUTION_WIDTH}x{VideoConfig.RESOLUTION_HEIGHT}, FPS: {VideoConfig.DEFAULT_FPS})")
                except Exception as e:
                    print(f"❌ 샘플 영상 {i+1} 로드 실패: {e}")
                    continue
            
            if len(clips) < 2:
                raise ValueError("최소 2개의 영상이 필요합니다.")
            
            # 트랜지션 리스트 (VideoTransitions에서 가져옴)
            transitions = VideoTransitions.get_available_transitions()
            
            final_clips = []
            
            # 트랜지션 시작 시점을 동적으로 계산하는 함수
            def get_transition_start_offset(clip_duration):
                return min(clip_duration * 0.2, 1.5)  # 최대 1.5초, 영상 길이의 20%
            
            # 사용할 클립 인덱스 (3개 클립을 순차적으로 사용)
            current_clip_index = 0
            
            # 첫 번째 영상은 전체 재생 (트랜지션 오버랩 제외)
            first_clip = clips[current_clip_index]
            first_transition_offset = get_transition_start_offset(first_clip.duration)
            first_clip_main = first_clip.subclip(0, first_clip.duration - first_transition_offset)
            final_clips.append(first_clip_main)
            print(f"✅ 첫 번째 영상 추가: {first_clip.duration - first_transition_offset:.2f}초")
            
            # 각 트랜지션 생성 (9개 트랜지션을 3개 클립으로 순환)
            for i, (transition_type, transition_name) in enumerate(transitions):
                print(f"🎭 트랜지션 {i+1}/{len(transitions)}: {transition_name}")
                
                # 현재 클립과 다음 클립 선택 (3개 클립 순환)
                clip_a = clips[current_clip_index % len(clips)]
                next_clip_index = (current_clip_index + 1) % len(clips)
                clip_b = clips[next_clip_index]
                
                try:
                    # 각 클립에 대해 동적으로 트랜지션 오프셋 계산
                    clip_a_offset = get_transition_start_offset(clip_a.duration)
                    clip_b_offset = get_transition_start_offset(clip_b.duration)
                    
                    # 트랜지션 부분: 클립 A의 마지막 부분과 클립 B의 첫 부분
                    clip_a_for_transition = clip_a.subclip(
                        clip_a.duration - clip_a_offset - self.transition_duration,
                        clip_a.duration
                    )
                    clip_b_for_transition = clip_b.subclip(0, self.transition_duration)
                    
                    # 트랜지션 생성
                    transition_clip = VideoTransitions.create_transition(
                        clip_a_for_transition, clip_b_for_transition, transition_type, self.transition_duration
                    )
                    
                    final_clips.append(transition_clip)
                    print(f"✅ {transition_name} 트랜지션 생성 완료")
                    
                    # 클립 B의 나머지 부분 추가 (트랜지션에서 이미 사용된 부분 제외)
                    # 트랜지션에서 클립 B의 첫 1초를 이미 사용했으므로, 1초 이후부터 시작
                    if i < len(transitions) - 1:  # 마지막이 아니면
                        # 다음 트랜지션을 위해 마지막 부분은 제외
                        if clip_b.duration > (self.transition_duration + clip_b_offset):
                            clip_b_remaining = clip_b.subclip(
                                self.transition_duration, 
                                clip_b.duration - clip_b_offset
                            )
                            final_clips.append(clip_b_remaining)
                            print(f"✅ 영상 {next_clip_index + 1} 나머지 부분 추가: {clip_b_remaining.duration:.1f}초")
                        else:
                            print(f"⚠️ 영상 {next_clip_index + 1}이 너무 짧아서 나머지 부분을 추가할 수 없습니다.")
                    else:  # 마지막 트랜지션이면 클립 B 전체 나머지
                        if clip_b.duration > self.transition_duration:
                            clip_b_remaining = clip_b.subclip(self.transition_duration, clip_b.duration)
                            final_clips.append(clip_b_remaining)
                            print(f"✅ 마지막 영상 나머지 부분 추가: {clip_b_remaining.duration:.1f}초")
                        else:
                            print(f"⚠️ 마지막 영상이 너무 짧아서 나머지 부분을 추가할 수 없습니다.")
                    
                    # 다음 트랜지션을 위해 클립 인덱스 업데이트
                    current_clip_index = next_clip_index
                    
                except Exception as e:
                    print(f"❌ {transition_name} 트랜지션 생성 실패: {e}")
                    continue
            
            if not final_clips:
                raise ValueError("생성된 트랜지션이 없습니다.")
            
            # 최종 영상 합치기
            print(f"🎬 최종 영상 합치기... ({len(final_clips)}개 트랜지션)")
            final_video = concatenate_videoclips(final_clips)
            
            # 출력 파일 경로
            import time
            timestamp = int(time.time() * 1000)
            output_filename = f"all_transitions_showcase_{timestamp}.mp4"
            output_path = os.path.join(self.temp_dir, output_filename)
            
            # 영상 저장
            print(f"💾 영상 저장 중: {output_path}")
            final_video.write_videofile(
                output_path,
                codec=VideoConfig.VIDEO_CODEC,
                audio_codec=VideoConfig.AUDIO_CODEC,
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=VideoConfig.DEFAULT_FPS
            )
            
            # 리소스 정리
            for clip in clips:
                clip.close()
            for clip in final_clips:
                clip.close()
            final_video.close()
            
            print(f"✅ 트랜지션 쇼케이스 영상 생성 완료: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 트랜지션 쇼케이스 영상 생성 실패: {e}")
            raise

    def merge_videos_basic(self, video_urls: List[str], output_filename: str = "merged_video.mp4") -> str:
        """기본 영상 합치기 (트랜지션 없음)"""
        print(f"🎬 {len(video_urls)}개 영상을 기본 방식으로 합칩니다...")
        
        try:
            clips = []
            
            # 각 URL에서 영상 로드
            for i, url in enumerate(video_urls):
                print(f"📹 로딩 중: 영상 {i+1}/{len(video_urls)}")
                try:
                    clip = VideoFileClip(url)
                    # VideoConfig의 설정에 맞게 영상 처리
                    # 해상도 통일
                    clip = clip.resize((VideoConfig.RESOLUTION_WIDTH, VideoConfig.RESOLUTION_HEIGHT))
                    # FPS 통일
                    clip = clip.set_fps(VideoConfig.DEFAULT_FPS)
                    clips.append(clip)
                    print(f"✅ 로드 완료: 영상 {i+1} (길이: {clip.duration:.1f}초, 해상도: {VideoConfig.RESOLUTION_WIDTH}x{VideoConfig.RESOLUTION_HEIGHT}, FPS: {VideoConfig.DEFAULT_FPS})")
                except Exception as e:
                    print(f"❌ 영상 {i+1} 로드 실패: {e}")
                    continue
            
            if not clips:
                raise ValueError("로드할 수 있는 영상이 없습니다.")
            
            # 영상 합치기
            final_clip = concatenate_videoclips(clips)
            
            # 출력 파일 경로
            import time
            timestamp = int(time.time() * 1000)
            output_filename = f"merged_{timestamp}.mp4"
            output_path = os.path.join(self.temp_dir, output_filename)
            
            # 영상 저장
            print(f"💾 영상 저장 중: {output_path}")
            final_clip.write_videofile(
                output_path,
                codec=VideoConfig.VIDEO_CODEC,
                audio_codec=VideoConfig.AUDIO_CODEC,
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=VideoConfig.DEFAULT_FPS
            )
            
            # 리소스 정리
            for clip in clips:
                clip.close()
            final_clip.close()
            
            return output_path
            
        except Exception as e:
            print(f"❌ 기본 영상 합치기 실패: {e}")
            raise

    def get_temp_dir(self) -> str:
        """임시 디렉토리 경로 반환"""
        return self.temp_dir
    
    def get_video_url(self, filename: str) -> str:
        """생성된 영상의 URL 반환"""
        if self.is_static:
            # 정적 파일 서빙을 위한 URL
            return f"/static/videos/{filename}"
        else:
            # 임시 파일의 경우 전체 경로 반환
            return os.path.join(self.temp_dir, filename)

    def merge_videos_with_transitions(self, video_urls: List[str], output_filename: str = "merged_with_transitions.mp4") -> str:
        """트랜지션을 사용해서 영상 합치기"""
        print(f"🎬 {len(video_urls)}개 영상을 랜덤 트랜지션과 함께 합칩니다...")
        
        try:
            clips = []
            
            # 각 URL에서 영상 로드
            for i, url in enumerate(video_urls):
                print(f"📹 로딩 중: 영상 {i+1}/{len(video_urls)}")
                try:
                    clip = VideoFileClip(url)
                    # VideoConfig의 설정에 맞게 영상 처리
                    # 해상도 통일
                    clip = clip.resize((VideoConfig.RESOLUTION_WIDTH, VideoConfig.RESOLUTION_HEIGHT))
                    # FPS 통일
                    clip = clip.set_fps(VideoConfig.DEFAULT_FPS)
                    clips.append(clip)
                    print(f"✅ 로드 완료: 영상 {i+1} (길이: {clip.duration:.1f}초, 해상도: {VideoConfig.RESOLUTION_WIDTH}x{VideoConfig.RESOLUTION_HEIGHT}, FPS: {VideoConfig.DEFAULT_FPS})")
                except Exception as e:
                    print(f"❌ 영상 {i+1} 로드 실패: {e}")
                    continue
            
            if len(clips) < 2:
                # 트랜지션을 위해 최소 2개 영상 필요
                return self.merge_videos_basic(video_urls, output_filename)
            
            # 사용 가능한 트랜지션
            transitions = VideoTransitions.get_available_transitions()
            final_clips = []
            
            # 트랜지션 시작 시점을 동적으로 계산하는 함수
            def get_transition_start_offset(clip_duration):
                return min(clip_duration * 0.2, 1.5)  # 최대 1.5초, 영상 길이의 20%
            
            # 첫 번째 영상은 전체 재생 (트랜지션 오버랩 제외)
            if clips:
                first_clip = clips[0]
                first_transition_offset = get_transition_start_offset(first_clip.duration)
                first_clip_main = first_clip.subclip(0, first_clip.duration - first_transition_offset)
                final_clips.append(first_clip_main)
                print(f"✅ 첫 번째 영상 추가: {first_clip.duration - first_transition_offset:.1f}초")
            
            # 각 트랜지션 생성
            for i in range(len(clips) - 1):
                clip_a = clips[i]
                clip_b = clips[i + 1]
                
                # 랜덤 트랜지션 선택
                transition_type, transition_name = random.choice(transitions)
                print(f"🎭 트랜지션 {i+1}/{len(clips)-1}: {transition_name}")
                
                try:
                    # 각 클립에 대해 동적으로 트랜지션 오프셋 계산
                    clip_a_offset = get_transition_start_offset(clip_a.duration)
                    clip_b_offset = get_transition_start_offset(clip_b.duration)
                    
                    # 트랜지션 부분: 클립 A의 마지막 부분과 클립 B의 첫 부분
                    clip_a_for_transition = clip_a.subclip(
                        clip_a.duration - clip_a_offset - self.transition_duration,
                        clip_a.duration
                    )
                    clip_b_for_transition = clip_b.subclip(0, self.transition_duration)
                    
                    # 트랜지션 생성
                    transition_clip = VideoTransitions.create_transition(
                        clip_a_for_transition, clip_b_for_transition, transition_type, self.transition_duration
                    )
                    
                    final_clips.append(transition_clip)
                    print(f"✅ {transition_name} 트랜지션 생성 완료")
                    
                    # 클립 B의 나머지 부분 추가 (트랜지션에서 이미 사용된 부분 제외)
                    if i < len(clips) - 2:  # 마지막이 아니면
                        # 다음 트랜지션을 위해 마지막 부분은 제외
                        if clip_b.duration > (self.transition_duration + clip_b_offset):
                            clip_b_remaining = clip_b.subclip(
                                self.transition_duration, 
                                clip_b.duration - clip_b_offset
                            )
                            final_clips.append(clip_b_remaining)
                            print(f"✅ 영상 {i+2} 나머지 부분 추가: {clip_b_remaining.duration:.1f}초")
                        else:
                            print(f"⚠️ 영상 {i+2}이 너무 짧아서 나머지 부분을 추가할 수 없습니다.")
                    else:  # 마지막 트랜지션이면 클립 B 전체 나머지
                        if clip_b.duration > self.transition_duration:
                            clip_b_remaining = clip_b.subclip(self.transition_duration, clip_b.duration)
                            final_clips.append(clip_b_remaining)
                            print(f"✅ 마지막 영상 나머지 부분 추가: {clip_b_remaining.duration:.1f}초")
                        else:
                            print(f"⚠️ 마지막 영상이 너무 짧아서 나머지 부분을 추가할 수 없습니다.")
                    
                except Exception as e:
                    print(f"❌ 트랜지션 생성 실패: {e}, 기본 연결 사용")
                    # 트랜지션 실패 시 기본 연결
                    if not final_clips:  # 첫 번째 클립이 아직 추가되지 않았다면
                        final_clips.append(clip_a)
                    final_clips.append(clip_b)
            
            # 최종 영상 합치기
            if final_clips:
                print(f"🎬 최종 영상 합치기... ({len(final_clips)}개 클립)")
                final_video = concatenate_videoclips(final_clips)
            else:
                # 트랜지션이 모두 실패한 경우 기본 합치기
                final_video = concatenate_videoclips(clips)
            
            # 출력 파일 경로
            import time
            timestamp = int(time.time() * 1000)
            output_filename = f"merged_transitions_{timestamp}.mp4"
            output_path = os.path.join(self.temp_dir, output_filename)
            
            # 영상 저장
            print(f"💾 영상 저장 중: {output_path}")
            final_video.write_videofile(
                output_path,
                codec=VideoConfig.VIDEO_CODEC,
                audio_codec=VideoConfig.AUDIO_CODEC,
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=VideoConfig.DEFAULT_FPS
            )
            
            # 리소스 정리
            for clip in clips:
                clip.close()
            for clip in final_clips:
                clip.close()
            final_video.close()
            
            return output_path
            
        except Exception as e:
            print(f"❌ 트랜지션 영상 합치기 실패: {e}")
            raise

    def cleanup(self):
        """리소스 정리"""
        try:
            if not self.is_static and hasattr(self, 'temp_dir'):
                import shutil
                if os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir)
                    print(f"🧹 임시 디렉토리 정리 완료: {self.temp_dir}")
        except Exception as e:
            print(f"⚠️ 리소스 정리 중 오류: {e}")

async def merge_storyboard_videos(video_urls: List[str], output_filename: str = "merged_storyboard.mp4", use_transitions: bool = True) -> str:
    """스토리보드 영상들을 합치는 함수 (async wrapper)"""
    merger = VideoTransitionMerger(use_static_dir=True)
    
    if use_transitions:
        # 트랜지션을 사용한 고급 합치기
        print(f"🎬 {len(video_urls)}개 영상을 트랜지션과 함께 합칩니다...")
        
        try:
            clips = []
            
            # 각 URL에서 영상 로드
            for i, url in enumerate(video_urls):
                print(f"📹 로딩 중: 영상 {i+1}/{len(video_urls)}")
                try:
                    clip = VideoFileClip(url)
                    # VideoConfig의 설정에 맞게 영상 처리
                    # 해상도 통일
                    clip = clip.resize((VideoConfig.RESOLUTION_WIDTH, VideoConfig.RESOLUTION_HEIGHT))
                    # FPS 통일
                    clip = clip.set_fps(VideoConfig.DEFAULT_FPS)
                    clips.append(clip)
                    print(f"✅ 로드 완료: 영상 {i+1} (길이: {clip.duration:.1f}초, 해상도: {VideoConfig.RESOLUTION_WIDTH}x{VideoConfig.RESOLUTION_HEIGHT}, FPS: {VideoConfig.DEFAULT_FPS})")
                except Exception as e:
                    print(f"❌ 영상 {i+1} 로드 실패: {e}")
                    continue
            
            if len(clips) < 2:
                # 트랜지션을 위해 최소 2개 영상 필요
                return merger.merge_videos_basic(video_urls, output_filename)
            
            # 사용 가능한 트랜지션
            transitions = VideoTransitions.get_available_transitions()
            final_clips = []
            
            # 트랜지션 시작 시점을 동적으로 계산하는 함수
            def get_transition_start_offset(clip_duration):
                return min(clip_duration * 0.2, 1.5)  # 최대 1.5초, 영상 길이의 20%
            
            transition_duration = VideoConfig.TRANSITION_DURATION
            
            # 첫 번째 영상은 전체 재생 (트랜지션 오버랩 제외)
            if clips:
                first_clip = clips[0]
                first_transition_offset = get_transition_start_offset(first_clip.duration)
                first_clip_main = first_clip.subclip(0, first_clip.duration - first_transition_offset)
                final_clips.append(first_clip_main)
                print(f"✅ 첫 번째 영상 추가: {first_clip.duration - first_transition_offset:.1f}초")
            
            # 각 트랜지션 생성
            for i in range(len(clips) - 1):
                clip_a = clips[i]
                clip_b = clips[i + 1]
                
                # 순차적으로 트랜지션 선택
                transition_type, transition_name = transitions[i % len(transitions)]
                print(f"🎭 트랜지션 {i+1}/{len(clips)-1}: {transition_name}")
                
                try:
                    # 각 클립에 대해 동적으로 트랜지션 오프셋 계산
                    clip_a_offset = get_transition_start_offset(clip_a.duration)
                    clip_b_offset = get_transition_start_offset(clip_b.duration)
                    
                    # 트랜지션 부분: 클립 A의 마지막 부분과 클립 B의 첫 부분
                    clip_a_for_transition = clip_a.subclip(
                        clip_a.duration - clip_a_offset - transition_duration,
                        clip_a.duration
                    )
                    clip_b_for_transition = clip_b.subclip(0, transition_duration)
                    
                    # 트랜지션 생성
                    transition_clip = VideoTransitions.create_transition(
                        clip_a_for_transition, clip_b_for_transition, transition_type, transition_duration
                    )
                    
                    final_clips.append(transition_clip)
                    print(f"✅ {transition_name} 트랜지션 생성 완료")
                    
                    # 클립 B의 나머지 부분 추가 (트랜지션에서 이미 사용된 부분 제외)
                    if i < len(clips) - 2:  # 마지막이 아니면
                        # 다음 트랜지션을 위해 마지막 부분은 제외
                        if clip_b.duration > (transition_duration + clip_b_offset):
                            clip_b_remaining = clip_b.subclip(
                                transition_duration, 
                                clip_b.duration - clip_b_offset
                            )
                            final_clips.append(clip_b_remaining)
                            print(f"✅ 영상 {i+2} 나머지 부분 추가: {clip_b_remaining.duration:.1f}초")
                        else:
                            print(f"⚠️ 영상 {i+2}이 너무 짧아서 나머지 부분을 추가할 수 없습니다.")
                    else:  # 마지막 트랜지션이면 클립 B 전체 나머지
                        if clip_b.duration > transition_duration:
                            clip_b_remaining = clip_b.subclip(transition_duration, clip_b.duration)
                            final_clips.append(clip_b_remaining)
                            print(f"✅ 마지막 영상 나머지 부분 추가: {clip_b_remaining.duration:.1f}초")
                        else:
                            print(f"⚠️ 마지막 영상이 너무 짧아서 나머지 부분을 추가할 수 없습니다.")
                    
                except Exception as e:
                    print(f"❌ 트랜지션 생성 실패: {e}, 기본 연결 사용")
                    # 트랜지션 실패 시 기본 연결
                    if not final_clips:  # 첫 번째 클립이 아직 추가되지 않았다면
                        final_clips.append(clip_a)
                    final_clips.append(clip_b)
            
            # 최종 영상 합치기
            if final_clips:
                print(f"🎬 최종 영상 합치기... ({len(final_clips)}개 클립)")
                final_video = concatenate_videoclips(final_clips)
            else:
                # 트랜지션이 모두 실패한 경우 기본 합치기
                final_video = concatenate_videoclips(clips)
            
            # 출력 파일 경로
            import time
            timestamp = int(time.time() * 1000)
            output_filename = f"merged_storyboard_{timestamp}.mp4"
            output_path = os.path.join(merger.get_temp_dir(), output_filename)
            
            # 영상 저장
            print(f"💾 영상 저장 중: {output_path}")
            final_video.write_videofile(
                output_path,
                codec=VideoConfig.VIDEO_CODEC,
                audio_codec=VideoConfig.AUDIO_CODEC,
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=VideoConfig.DEFAULT_FPS
            )
            
            # 리소스 정리
            for clip in clips:
                clip.close()
            for clip in final_clips:
                clip.close()
            final_video.close()
            
            return output_path
            
        except Exception as e:
            print(f"❌ 트랜지션 합치기 실패: {e}, 기본 방식으로 시도")
            return merger.merge_videos_basic(video_urls, output_filename)
    else:
        # 기본 합치기
        return merger.merge_videos_basic(video_urls, output_filename)
