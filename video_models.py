"""
영상 생성을 위한 데이터 모델들
"""
from pydantic import BaseModel
from typing import List, Optional

class VideoConfig:
    """비디오 생성 및 처리를 위한 설정값들"""
    # 해상도 설정
    RESOLUTION_WIDTH = 768
    RESOLUTION_HEIGHT = 1280
    
    # FPS 설정
    FPS = 24
    DEFAULT_FPS = 24
    
    # 길이 설정
    DEFAULT_DURATION = 5  # 기본 비디오 길이 (초)
    TRANSITION_DURATION = 1.0  # 트랜지션 길이 (초)
    
    # 코덱 설정
    VIDEO_CODEC = 'libx264'
    AUDIO_CODEC = 'aac'

class VideoGenerationInput(BaseModel):
    """영상 생성 요청 데이터"""
    image_url: str  # 소스 이미지 URL
    duration: int = 5  # 영상 길이 (초), 기본값 10초
    resolution: str = "768:1280"  # 해상도, 기본값 720p
    model: str = "gen4_video"  # Runway 영상 모델
    seed: Optional[int] = None  # 시드값 (선택사항)

class VideoGenerationResult(BaseModel):
    """영상 생성 결과"""
    scene_number: int  # 장면 번호
    status: str  # 성공/실패 상태
    video_url: Optional[str] = None  # 생성된 영상 URL
    error: Optional[str] = None  # 오류 메시지
    duration: int = 5  # 영상 길이
    resolution: str = "768:1280"  # 해상도

class ImageToVideoRequest(BaseModel):
    """이미지 URL 목록을 영상으로 변환하는 요청"""
    image_urls: List[str]  # 이미지 URL 목록
    duration_per_scene: int = 5  # 장면당 영상 길이 (초)
    resolution: str = "768:1280"  # 해상도 (720p)
    model: str = "gen3a_turbo"  # Runway 영상 모델

class StoryboardVideoOutput(BaseModel):
    """전체 스토리보드 영상 생성 결과"""
    message: str  # 완료 메시지
    generated_videos: List[VideoGenerationResult]  # 각 장면별 영상 결과
    summary: dict  # 생성 통계 (성공/실패 개수, 성공률 등)

class VideoMergeRequest(BaseModel):
    """영상 합치기 요청"""
    video_urls: List[str]  # 합칠 영상 URL 목록
    output_filename: Optional[str] = None  # 출력 파일명 (기본값: 타임스탬프)
    transition_duration: float = 1.0  # 트랜지션 효과 시간 (초)

class VideoMergeResult(BaseModel):
    """영상 합치기 결과"""
    message: str  # 완료 메시지
    final_video: dict  # 최종 영상 정보
    summary: dict  # 합치기 통계
    source_videos: List[dict]  # 원본 영상들 정보
