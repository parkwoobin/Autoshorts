from pydantic import BaseModel
from typing import List, Optional

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

# 이미지 생성용 데이터 구조
class ReferenceImage(BaseModel):
    uri: str
    tag: str

# 스토리보드 생성을 위한 프롬프트 구조 설정 
class SceneImagePrompt(BaseModel):
    """이미지 생성을 위한 프롬프트 (입력 데이터)"""
    model: str = "gen4_image"
    promptText: str
    ratio: str = "1280:720"  # 기본값 5크레딧 720p, 1920:1080 8크레딧 1080p  
    referenceImages: List[ReferenceImage] = [] # 기본값은 빈 리스트
    seed: int = 42  # 시드값을 잘 생각해되는게 시드값을 사용하면 동일한 프롬프트로도 매번 다른 이미지를 생성할 수 있음
    publicFigureModeration: str = "auto"  # 기본값, low와,off가 있음

class StoryboardScene(BaseModel):
    """전체 스토리보드 구조 (여러 장면들을 포함)"""
    scenes: List[SceneImagePrompt]  # 개별 장면들
    total_scenes: int  # 총 장면 수
    estimated_duration: int  # 예상 영상 길이 (초)
    video_concept: str  # 영상 컨셉 설명

class StoryboardOutput(BaseModel):
    """완전한 스토리보드 구조"""
    scenes: List[SceneImagePrompt]  # LLM 출력용 (프롬프트만)
    total_scenes: int  # 총 장면 수
    estimated_duration: int  # 예상 영상 길이 (초)
    video_concept: str  # 영상 컨셉 설명
