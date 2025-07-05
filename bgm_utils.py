"""
BGM 처리를 위한 유틸리티 함수들
"""
import os
import random
import glob
from typing import Optional, List
from video_models import VideoConfig

try:
    from moviepy.editor import AudioFileClip, CompositeAudioClip
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MoviePy import 실패: {e}")
    MOVIEPY_AVAILABLE = False

class BGMManager:
    """BGM 관리 및 처리 클래스"""
    
    def __init__(self, bgm_folder: str = None):
        if not MOVIEPY_AVAILABLE:
            raise ImportError("MoviePy가 설치되지 않았거나 import할 수 없습니다.")
        
        self.bgm_folder = bgm_folder or VideoConfig.BGM_FOLDER
        self.supported_formats = ['.mp3', '.m4a', '.wav', '.aac', '.flac']
        
    def get_available_bgm_files(self) -> List[str]:
        """사용 가능한 BGM 파일 목록 반환"""
        bgm_files = []
        
        if not os.path.exists(self.bgm_folder):
            print(f"⚠️ BGM 폴더가 존재하지 않습니다: {self.bgm_folder}")
            return bgm_files
        
        for ext in self.supported_formats:
            pattern = os.path.join(self.bgm_folder, f"*{ext}")
            files = glob.glob(pattern)
            bgm_files.extend(files)
        
        return bgm_files
    
    def select_random_bgm(self) -> Optional[str]:
        """랜덤으로 BGM 파일 선택"""
        bgm_files = self.get_available_bgm_files()
        
        if not bgm_files:
            print("⚠️ 사용 가능한 BGM 파일이 없습니다.")
            return None
        
        selected_bgm = random.choice(bgm_files)
        print(f"🎵 선택된 BGM: {os.path.basename(selected_bgm)}")
        return selected_bgm
    
    def process_bgm_for_video(self, bgm_path: str, video_duration: float, 
                            volume_adjustment: float = VideoConfig.BGM_VOLUME) -> AudioFileClip:
        """
        영상 길이에 맞게 BGM 처리
        
        Args:
            bgm_path: BGM 파일 경로
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
            print(f"❌ BGM 처리 실패: {e}")
            raise
    
    def add_bgm_to_video(self, video_clip, bgm_path: str = None, 
                        volume_adjustment: float = VideoConfig.BGM_VOLUME):
        """
        영상에 BGM 추가
        
        Args:
            video_clip: MoviePy VideoFileClip 객체
            bgm_path: BGM 파일 경로 (None이면 랜덤 선택)
            volume_adjustment: 음량 조절 (dB)
            
        Returns:
            BGM이 추가된 영상 클립
        """
        try:
            # BGM 파일 선택
            if bgm_path is None:
                bgm_path = self.select_random_bgm()
                if bgm_path is None:
                    print("⚠️ BGM을 추가할 수 없습니다. 원본 영상 반환.")
                    return video_clip
            
            # BGM 처리
            bgm_audio = self.process_bgm_for_video(
                bgm_path, 
                video_clip.duration, 
                volume_adjustment
            )
            
            # 원본 오디오와 BGM 합성
            if video_clip.audio is not None:
                # 원본 오디오가 있으면 합성
                try:
                    final_audio = CompositeAudioClip([video_clip.audio, bgm_audio])
                    print("🎵 원본 오디오와 BGM을 합성합니다.")
                except Exception as e:
                    print(f"⚠️ 오디오 합성 실패, BGM만 사용: {e}")
                    final_audio = bgm_audio
            else:
                # 원본 오디오가 없으면 BGM만 사용
                final_audio = bgm_audio
                print("🎵 BGM을 배경음악으로 추가합니다.")
            
            # 영상에 오디오 적용
            video_with_bgm = video_clip.set_audio(final_audio)
            
            print(f"✅ BGM 추가 완료: {os.path.basename(bgm_path)}")
            return video_with_bgm
            
        except Exception as e:
            print(f"❌ BGM 추가 실패: {e}")
            print("⚠️ BGM 없이 원본 영상을 반환합니다.")
            return video_clip
    
    def list_bgm_files(self) -> List[dict]:
        """BGM 파일 목록과 정보 반환"""
        bgm_files = self.get_available_bgm_files()
        bgm_info = []
        
        for bgm_path in bgm_files:
            try:
                audio = AudioFileClip(bgm_path)
                info = {
                    "filename": os.path.basename(bgm_path),
                    "path": bgm_path,
                    "duration": round(audio.duration, 2),
                    "size": os.path.getsize(bgm_path)
                }
                bgm_info.append(info)
                audio.close()
            except Exception as e:
                print(f"⚠️ BGM 파일 정보 읽기 실패 {bgm_path}: {e}")
        
        return bgm_info

# 편의 함수들
def get_random_bgm_path(bgm_folder: str = None) -> Optional[str]:
    """랜덤 BGM 파일 경로 반환"""
    manager = BGMManager(bgm_folder)
    return manager.select_random_bgm()

def add_bgm_to_video_simple(video_clip, bgm_folder: str = None, 
                           volume_db: float = VideoConfig.BGM_VOLUME):
    """간단한 BGM 추가 함수"""
    manager = BGMManager(bgm_folder)
    return manager.add_bgm_to_video(video_clip, volume_adjustment=volume_db)

# MoviePy concatenate_audioclips import
try:
    from moviepy.editor import concatenate_audioclips
except ImportError:
    print("⚠️ concatenate_audioclips import 실패")
