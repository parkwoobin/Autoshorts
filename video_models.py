"""
영상 생성을 위한 데이터 모델들
    # BGM 설정
    BGM_FOLDER = "bgm"  # BGM 폴더 경로
    BGM_VOLUME = -5  # BGM 음량 조절 (dB)
    BGM_ENABLED = False  # BGM 사용 여부 (임시로 비활성화)"""
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
    
    # BGM 설정
    BGM_FOLDER = "bgm"  # BGM 폴더 경로
    BGM_VOLUME = -10  # BGM 음량 조절 (dB)
    BGM_ENABLED = True  # BGM 사용 여부

class VideoGenerationInput(BaseModel):
    """영상 생성 요청 데이터"""
    image_url: str  # 소스 이미지 URL
    duration: int = 5  # 영상 길이 (초), 기본값 10초
    resolution: str = "720:1280"  # 해상도, 기본값 720p
    model: str = "gen4_turbo"  # Runway 영상 모델
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
    resolution: str = "720:1280"  # 해상도 (세로형)
    model: str = "gen4_turbo"  # Runway 이미지→비디오 모델

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
    enable_bgm: bool = True  # BGM 사용 여부
    bgm_volume: float = -5.0  # BGM 음량 조절 (dB)

class VideoMergeResult(BaseModel):
    """영상 합치기 결과"""
    message: str  # 완료 메시지
    final_video: dict  # 최종 영상 정보
    summary: dict  # 합치기 통계
    source_videos: List[dict]  # 원본 영상들 정보

class TransitionMergeRequest(BaseModel):
    """트랜지션과 BGM을 포함한 영상 합치기 요청"""
    enable_bgm: bool = True  # BGM 사용 여부 (기본값: True)
    bgm_volume: float = 0.4  # BGM 음량 (0.0~1.0, 기본값: 40%)
    transition_duration: float = 1.0  # 트랜지션 효과 시간 (초)

class BGMGenerationRequest(BaseModel):
    """SUNO API BGM 생성 요청 (이미지와 동일한 파라미터 구조)"""
    keyword: str = "happy"  # BGM 키워드 (기본값: "happy")
    duration: int = 70  # BGM 길이 (초, 기본값: 70초)
    max_wait_minutes: int = 5  # 최대 대기 시간 (분, 기본값: 5분)

class SubtitleCustomRequest(BaseModel):
    """커스텀 자막 적용 요청"""
    srt_file_path: Optional[str] = None  # SRT 파일 경로 (선택사항, 없으면 자동 생성)
    font_size: int = 2  # 폰트 크기 (기본값: 2)
    font_name: str = "Malgun Gothic"  # 폰트 이름 (기본값: 맑은 고딕)
    font_color: str = "&Hffffff"  # 폰트 색상 (기본값: 흰색)
    scale_x: int = 30  # 가로 스케일 (기본값: 30%)
    scale_y: int = 30  # 세로 스케일 (기본값: 30%)
    position: str = "bottom"  # 자막 위치 라벨: "top", "middle", "bottom" (기본값: bottom)
    margin_v: int = 80  # 세로 여백 (기본값: 80)
    margin_l: int = 300  # 좌측 여백 (기본값: 300)
    margin_r: int = 300  # 우측 여백 (기본값: 300)
    enable_outline: bool = True  # 외곽선 사용 여부 (기본값: True)
    outline_color: str = "&H000000"  # 외곽선 색상 (기본값: 검은색)
    outline_width: int = 2  # 외곽선 두께 (기본값: 2)
    enable_bold: bool = True  # Bold체 사용 여부 (기본값: True)

class TTSSubtitleRequest(BaseModel):
    """8단계: TTS와 자막 완전 합치기 요청"""
    tts_volume: float = 5.0  # TTS 음성 볼륨 (배수, 기본값: 500% = 5.0)
    position: str = "bottom"  # 자막 위치 라벨: "top", "middle", "bottom" (기본값: bottom)
    include_bgm: str = "false"  # BGM 포함 라벨: "true" 또는 "false" (기본값: "false")
    font_size: int = 16  # 폰트 크기 (기본값: 16)
    font_name: str = "Malgun Gothic"  # 폰트 이름 (기본값: 맑은 고딕)
    font_color: str = "&Hffffff"  # 폰트 색상 (기본값: 흰색)
    scale_x: int = 50  # 가로 스케일 (기본값: 50%)
    scale_y: int = 50  # 세로 스케일 (기본값: 50%)
    enable_outline: bool = True  # 외곽선 사용 여부 (기본값: True)
