from pydantic import BaseModel
from typing import List

# 사용자 입력 1단계 데이터 구조 정의
# 타겟 고객 정보 수집 단계
class TargetCustomer(BaseModel):
    country: str
    age_range: List[str]
    gender: str
    language: str
    interests: List[str] = [] # 관심사 설정은 선택사항임 , 기본값은 빈 리스트

# LLM 생성 페르소나 데이터 
class PersonaData(BaseModel):
    target_customer: TargetCustomer
    persona_description: str  # LLM이 생성한 페르소나 설명
    marketing_insights: str = ""  # 타겟 고객 마케팅 인사이트

# 사용자 입력 영상 프롬프트 
class UserVideoInput(BaseModel):
    user_description: str  # 사용자가 입력한 영상 설명
    selected_themes: List[str] = []  # 선택한 테마들
    additional_requirements: str = ""  # 추가 요구사항

# LLM 생성 최종 프롬프트 (개선)
class FinalVideoPrompt(BaseModel):
    persona: PersonaData
    user_input: UserVideoInput
    optimized_prompt: str  # LLM이 최적화한 최종 프롬프트
    target_duration: int  # 목표 영상 길이(초)
    key_scenes: List[str]  # 주요 장면 리스트

# LLM 생성 상세 장면 (대폭 개선)
class DetailedStoryboardScene(BaseModel):
    scene_number: int
    title: str  # 장면 제목
    description: str  # 상세 장면 설명
    visual_elements: str  # 시각적 요소
    audio_elements: str  # 오디오 요소 (BGM, 효과음, 내레이션)
    camera_work: str  # 카메라 워크 및 앵글
    lighting: str  # 조명 설정
    props_and_costumes: List[str]  # 필요한 소품 및 의상
    dialogue_or_narration: str = ""  # 대사 또는 내레이션
    duration_seconds: int
    transition_to_next: str = ""  # 다음 장면으로의 전환 방식

# 최종 스토리보드 (개선)
class EnhancedStoryboard(BaseModel):
    final_prompt: FinalVideoPrompt
    scenes: List[DetailedStoryboardScene]
    total_duration: int
    production_notes: str  # 제작 시 주의사항
    budget_estimate: str = ""  # 예상 제작비용 범위
    target_platforms: List[str]  # 최적화된 플랫폼들

# 기존 호환성을 위한 간단한 구조도 유지
class VideoPrompt(BaseModel):
    persona: PersonaData
    description: str
    final_prompt: str

class StoryboardScene(BaseModel):
    scene_number: int
    description: str
    visual_elements: str
    duration_seconds: int

class Storyboard(BaseModel):
    video_prompt: VideoPrompt
    scenes: List[StoryboardScene]
    total_duration: int
