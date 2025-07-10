"""
사용자 입력 -> 광고 영상 제작 전체 워크플로우에서 사용되는 주요 데이터 구조를 정의함 
pydantic 모델을 사용하여 애플리케이션에서 사용되는 데이터 모델을 정의
pydantic 데이터 모델 : 데이터의 구조 설정 + 데이터 검증
"""
from pydantic import BaseModel,Field,ConfigDict
from typing import List,Optional

# 사용자 입력 1단계 데이터 구조 정의
# 타겟 고객 정보 수집 단계
class TargetCustomer(BaseModel):
    country: str
    age_range: List[str]
    gender: str
    language: str # 언어,문화권을 위해 필요하다고 생각했었는데 구현하다보니 필요없을 수도 있음
    interests: List[str] = [] # 관심사 설정은 선택사항임 , 기본값은 빈 리스트

# LLM 생성 페르소나 데이터 
class PersonaData(BaseModel):
    target_customer: TargetCustomer  # 어떤 타겟 고객을 위한 페르소나인지
    persona_description: str  # LLM이 생성한 페르소나 설명 
    marketing_insights: str  # 타겟 고객 마케팅 인사이트
# ==================================================================================

# 광고 컨셉 생성을 위한 데이터 구조 정의
# 사용자 입력 영상 프롬프트 및 참조 이미지 통합 구조
class ReferenceImage(BaseModel):
    uri: str 
    tag: str  # 프롬프트에서 사용할 태그 (product, store, person 등 - @ 없이)

# 이미지 분석결과를 스토리보드 생성에 사용하기 위해서 데이터 구조를 하나더 생성함!!
class ReferenceImageWithDescription(ReferenceImage):
    analysis : str  # 이미지 분석 결과 (LLM이 생성한 설명)

# 사용자 입력 영상 설명 및 참조 이미지 구조
class UserVideoInput(BaseModel):
    user_description: Optional[str] = None # 사용자가 입력한 영상 설명 (llm이 생성한 광고 기획을 참고하여 작성)

# ==================================================================================

# 스토리보드 생성을 위한 프롬프트 구조 설정 
class SceneImagePrompt(BaseModel):
    """이미지 생성을 위한 프롬프트 (입력 데이터)"""
    model: str = "gen4_image"
    prompt_text: str = Field(..., alias='promptText')
    ratio: str = "1280:720"  # 기본값 5크레딧 720p, 1920:1080 8크레딧 1080p  
    reference_images: Optional[List[ReferenceImage]] = Field(None, alias="referenceImages")
    seed: int = 42  # 시드값을 잘 생각해되는게 시드값을 사용하면 동일한 프롬프트로도 매번 다른 이미지를 생성할 수 있음
    model_config = ConfigDict(populate_by_name=True)

class StoryboardOutput(BaseModel):
    """완전한 스토리보드 구조"""
    scenes: List[SceneImagePrompt]  # LLM 출력용 (프롬프트만)
    total_scenes: int  # 총 장면 수
    estimated_duration: int  # 예상 영상 길이 (초)
    video_concept: str  # 영상 컨셉 설명
