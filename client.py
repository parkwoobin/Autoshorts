from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
# 웹 애플리케이션 객체 생성
app = FastAPI(title="Storyboard API")

# 데이터 모델 정의
class TargetCustomer(BaseModel):
    country: str
    age_range: str
    gender: str
    language: str
    interests: List[str]

class PersonaData(BaseModel):
    target_customer: TargetCustomer
    persona_description: str

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

# 전역 변수로 데이터 저장
current_project = {
    "target_customer": None,
    "persona": None,
    "video_prompt": None,
    "storyboard": None
}

@app.get("/")
async def root():
    return {"message": "Video Generation API", "status": "running"}

@app.get("/project/status")
async def get_project_status():
    """현재 프로젝트 진행 상태 확인"""
    status = {}
    for key, value in current_project.items():
        status[key] = value is not None
    return {"project_status": status, "current_data": current_project}

@app.post("/step1/target-customer")
async def set_target_customer(customer: TargetCustomer):
    """1단계: 타겟 고객 정보 설정"""
    current_project["target_customer"] = customer.dict()
    
    # 페르소나 생성 (임시로 간단한 텍스트 생성)
    persona_description = generate_persona(customer)
    current_project["persona"] = {
        "target_customer": customer.dict(),
        "persona_description": persona_description
    }
    
    return {
        "message": "타겟 고객 정보가 설정되었습니다.",
        "target_customer": customer,
        "generated_persona": persona_description
    }

def generate_persona(customer: TargetCustomer) -> str:
    """타겟 고객 정보를 바탕으로 페르소나 생성"""
    interests_str = ", ".join(customer.interests)
    
    persona = f"""
타겟 페르소나:
- 국가: {customer.country}
- 연령대: {customer.age_range}
- 성별: {customer.gender}
- 언어: {customer.language}
- 관심사: {interests_str}

이 페르소나는 {customer.age_range} {customer.gender}로 {customer.country}에 거주하며 {customer.language}를 사용합니다.
주요 관심사는 {interests_str}이며, 이러한 요소들을 고려한 콘텐츠에 높은 관심을 보일 것으로 예상됩니다.
"""
    return persona.strip()

@app.get("/step2/example-prompt")
async def get_example_prompt():
    """2단계: 페르소나 기반 예시 프롬프트 제공"""
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계 타겟 고객 설정을 완료해주세요.")
    
    persona_data = current_project["persona"]
    customer = persona_data["target_customer"]
    
    # 페르소나 기반 예시 프롬프트 생성
    example_prompt = generate_example_prompt(customer)
    
    return {
        "message": "페르소나 기반 예시 프롬프트입니다. 이를 참고하여 원하는 광고 영상을 설명해주세요.",
        "persona": persona_data["persona_description"],
        "example_prompt": example_prompt
    }

def generate_example_prompt(customer: dict) -> str:
    """페르소나 기반 예시 프롬프트 생성"""
    interests_str = ", ".join(customer["interests"])
    
    example = f"""
예시 광고 영상 프롬프트:

"{customer['age_range']} {customer['gender']} 타겟을 위한 {interests_str}와 관련된 제품/서비스 광고영상을 제작합니다.

영상 구성:
1. 오프닝: 타겟의 일상적인 고민이나 니즈를 보여주는 장면
2. 문제 제시: 현재 상황의 불편함이나 해결이 필요한 부분 강조
3. 솔루션 소개: 제품/서비스가 어떻게 문제를 해결하는지 시연
4. 혜택 강조: 사용 후 달라진 생활이나 얻을 수 있는 이점들
5. 클로징: 행동 유도와 함께 마무리

전체 톤앤매너: {customer['language']} 언어로 {customer['country']} 문화에 맞는 친근하고 신뢰감 있는 분위기
영상 길이: 30-60초 내외"

이 예시를 참고하여 원하는 광고 영상의 구체적인 내용을 작성해주세요.
"""
    return example.strip()

@app.post("/step2/video-prompt")
async def set_video_prompt(prompt_data: dict):
    """2단계: 사용자가 작성한 광고 영상 프롬프트 설정"""
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계 타겟 고객 설정을 완료해주세요.")
    
    description = prompt_data.get("description", "")
    if not description:
        raise HTTPException(status_code=400, detail="광고 영상 설명을 입력해주세요.")
    
    # 페르소나와 사용자 입력을 결합한 최종 프롬프트 생성
    final_prompt = combine_persona_and_prompt(current_project["persona"], description)
    
    current_project["video_prompt"] = {
        "persona": current_project["persona"],
        "description": description,
        "final_prompt": final_prompt
    }
    
    return {
        "message": "광고 영상 프롬프트가 설정되었습니다.",
        "description": description,
        "final_prompt": final_prompt
    }

def combine_persona_and_prompt(persona_data: dict, user_description: str) -> str:
    """페르소나와 사용자 프롬프트를 결합"""
    customer = persona_data["target_customer"]
    persona_desc = persona_data["persona_description"]
    
    final_prompt = f"""
타겟 페르소나:
{persona_desc}

광고 영상 요청사항:
{user_description}

최종 영상 제작 가이드라인:
- 타겟: {customer['age_range']} {customer['gender']} ({customer['country']})
- 언어: {customer['language']}
- 관심사 연계: {', '.join(customer['interests'])}
- 문화적 맥락: {customer['country']} 현지 문화와 트렌드 반영
- 콘텐츠 방향: 위 페르소나의 특성과 관심사를 고려한 맞춤형 접근
"""
    return final_prompt.strip()

@app.post("/step3/generate-storyboard")
async def generate_storyboard():
    """3단계: 스토리보드 생성"""
    if not current_project["video_prompt"]:
        raise HTTPException(status_code=400, detail="먼저 1-2단계를 완료해주세요.")
    
    # 간단한 스토리보드 생성 (나중에 LLM으로 교체)
    storyboard_scenes = create_basic_storyboard(current_project["video_prompt"])
    
    total_duration = sum(scene["duration_seconds"] for scene in storyboard_scenes)
    
    storyboard = {
        "video_prompt": current_project["video_prompt"],
        "scenes": storyboard_scenes,
        "total_duration": total_duration
    }
    
    current_project["storyboard"] = storyboard
    
    return {
        "message": "스토리보드가 생성되었습니다.",
        "storyboard": storyboard
    }

def create_basic_storyboard(video_prompt_data: dict) -> List[dict]:
    """기본 스토리보드 생성 (추후 LLM으로 대체)"""
    description = video_prompt_data["description"]
    customer = video_prompt_data["persona"]["target_customer"]
    
    scenes = [
        {
            "scene_number": 1,
            "description": f"{customer['age_range']} {customer['gender']}의 일상적인 고민 상황을 보여주는 오프닝 장면",
            "visual_elements": "자연스러운 일상 배경, 고민하는 표정, 부드러운 조명",
            "duration_seconds": 8
        },
        {
            "scene_number": 2,
            "description": "현재 상황의 문제점이나 불편함을 강조하는 장면",
            "visual_elements": "문제 상황 클로즈업, 대비되는 색감, 긴장감 있는 구도",
            "duration_seconds": 10
        },
        {
            "scene_number": 3,
            "description": "제품/서비스 소개 및 솔루션 제시 장면",
            "visual_elements": "제품 등장, 밝은 조명, 희망적인 분위기, 브랜드 컬러",
            "duration_seconds": 15
        },
        {
            "scene_number": 4,
            "description": "사용 후 개선된 모습과 만족스러운 결과를 보여주는 장면",
            "visual_elements": "만족스러운 표정, 밝은 배경, 성과 시각화",
            "duration_seconds": 12
        },
        {
            "scene_number": 5,
            "description": f"행동 유도와 브랜드 메시지로 마무리하는 클로징 ({customer['language']})",
            "visual_elements": "브랜드 로고, CTA 텍스트, 기억에 남는 비주얼",
            "duration_seconds": 10
        }
    ]
    
    return scenes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)