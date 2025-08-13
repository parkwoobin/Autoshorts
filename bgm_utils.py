"""
BGM 처리를 위한 유틸리티 함수들 - SUNO BGM 전용
"""
import os
from typing import Optional
from video_models import VideoConfig

try:
    from moviepy.editor import AudioFileClip, CompositeAudioClip, concatenate_audioclips
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MoviePy import 실패: {e}")
    MOVIEPY_AVAILABLE = False

class SunoBGMProcessor:
    """SUNO BGM 처리 전용 클래스"""
    
    def __init__(self):
        if not MOVIEPY_AVAILABLE:
            raise ImportError("MoviePy가 설치되지 않았거나 import할 수 없습니다.")
    
    def process_suno_bgm_for_video(self, bgm_path: str, video_duration: float, 
                                 volume_adjustment: float = VideoConfig.BGM_VOLUME) -> AudioFileClip:
        """
        SUNO BGM을 영상 길이에 맞게 처리
        
        Args:
            bgm_path: SUNO BGM 파일 경로
            video_duration: 영상 길이 (초)
            volume_adjustment: 음량 조절 (dB)
            
        Returns:
            처리된 오디오 클립
        """
        try:
            # BGM 파일 로드
            bgm_audio = AudioFileClip(bgm_path)
            print(f"🎵 BGM 원본 길이: {bgm_audio.duration:.2f}초")
            print(f"🎬 영상 길이: {video_duration:.2f}초")
            
            # BGM 길이 조정
            if bgm_audio.duration > video_duration:
                # BGM이 영상보다 길면 자르기
                bgm_audio = bgm_audio.subclip(0, video_duration)
                print(f"✂️ BGM을 {video_duration:.2f}초로 자릅니다.")
            elif bgm_audio.duration < video_duration:
                # BGM이 영상보다 짧으면 반복
                repeat_count = int(video_duration / bgm_audio.duration) + 1
                bgm_clips = [bgm_audio] * repeat_count
                try:
                    bgm_audio = concatenate_audioclips(bgm_clips).subclip(0, video_duration)
                    print(f"🔄 BGM을 {repeat_count}번 반복하여 {video_duration:.2f}초로 맞춥니다.")
                except Exception as e:
                    print(f"⚠️ BGM 반복 처리 실패, 원본 사용: {e}")
                    # 반복 실패 시 원본 BGM 사용
                    bgm_audio = bgm_audio.subclip(0, min(bgm_audio.duration, video_duration))
            
            # 음량 조절 (dB 단위)
            if volume_adjustment != 0:
                try:
                    # dB를 선형 스케일로 변환: 10^(dB/20)
                    volume_factor = 10 ** (volume_adjustment / 20)
                    bgm_audio = bgm_audio.volumex(volume_factor)
                    print(f"🔊 BGM 음량을 {volume_adjustment}dB 조절합니다.")
                except Exception as e:
                    print(f"⚠️ BGM 음량 조절 실패, 원본 음량 사용: {e}")
            
            return bgm_audio
            
        except Exception as e:
            print(f"❌ SUNO BGM 처리 실패: {e}")
            raise

# SUNO BGM 전용 편의 함수
def process_suno_bgm_simple(bgm_path: str, video_duration: float, 
                           volume_db: float = VideoConfig.BGM_VOLUME) -> AudioFileClip:
    """SUNO BGM 간단 처리 함수"""
    processor = SunoBGMProcessor()
    return processor.process_suno_bgm_for_video(bgm_path, video_duration, volume_db)
