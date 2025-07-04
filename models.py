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


# 이미지 생성용 데이터 구조
class ReferenceImage(BaseModel):
    uri: str
    tag: str
# 스토리보드 생성을 위한 프롬프트 구조 설정 
class SceneImagePrompt(BaseModel):
    model: str = "gen4_image"  # 기본값
    promptText: str
    ratio: str = "1280:720"  # 기본값 5크레딧 720p, 1920:1080 8크레딧 1080p  
    referenceImages: List[ReferenceImage] = [] # 기본값은 빈 리스트
    seed: int # 시드값을 잘 생각해되는게 시드값을 사용하면 동일한 프롬프트로도 매번 다른 이미지를 생성할 수 있음
    publicFigureModeration: str = "auto"  # 기본값, low와,off가 있음

class SceneData(BaseModel):
    """단일 장면 데이터"""
    scene_number: int
    scene_title: str
    scene_description: str
    duration_seconds: int
    prompt_text: str

class VideoStoryboardData(BaseModel):
    """LLM 출력용 비디오 스토리보드 데이터"""
    video_concept: str
    total_duration: int
    scenes: List[SceneData]

class SceneStoryboard(BaseModel):
    scene_number: int
    scene_title: str
    scene_description: str
    duration_seconds: int
    image_prompt: SceneImagePrompt

class VideoStoryboard(BaseModel):
    user_input: UserVideoInput
    scenes: List[SceneStoryboard]
    total_duration: int
    video_concept: str
