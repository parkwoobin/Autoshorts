from fastapi import FastAPI, HTTPException
from typing import List

# 모델들을 별도 파일에서 import
from models import (
    TargetCustomer, PersonaData, ExamplePrompt, UserVideoInput, 
    FinalVideoPrompt, DetailedStoryboardScene, EnhancedStoryboard,
    VideoPrompt, StoryboardScene, Storyboard
)

# LLM 유틸리티 함수들을 별도 파일에서 import
from persona_utils import (
    generate_persona_with_llm, create_ad_example,
    optimize_user_prompt_with_llm, generate_detailed_storyboard_with_llm,
    # 기존 호환성 함수들
    generate_persona, generate_example_prompt, combine_persona_and_prompt, 
    create_basic_storyboard
)

# 웹 애플리케이션 객체(서버) 생성
app = FastAPI(title="Storyboard API")

# 전역 변수로 데이터 임시 저장 -> 데이터베이스로 연결 
current_project = {
    "target_customer": None,
    "persona": None,
    "example_prompts": None,
    "user_video_input": None,
    "final_prompt": None,
    "enhanced_storyboard": None,
    # 기존 호환성
    "video_prompt": None,
    "storyboard": None
}

# 웹 브라우저가 서버로 GET 요청 
@app.get("/")
# 서버의 기본 주소로 GET 요청 보냈을때 실행할 비동기 root 함수 정의
async def root():
    # 요청에 대한 응답으로 서버가 잘 작동하고 있다는 메시지 출력
    return {"message": "Storyboard API", "status": "running"}

# 이 함수는 굳이 왜 필요한가? -> 일단 두자
@app.get("/project/status")
async def get_project_status():
    """현재 프로젝트 진행 상태 확인"""
    status = {}
    for key, value in current_project.items():
        status[key] = value is not None
    return {"project_status": status, "current_data": current_project}

# ==================================================================================

"""
1단계 : 타겟 고객 정보 설정 및 LLM을 통한 페르소나 생성
단계별 상세 과정 이해하기
사용자 정보 POST 요청 → JSON 파싱(python dict로 변환) : 이 과정에서 데이터 유효성 검사 및 변환이 수행됨
→ 객체 생성(데이터 구조 생성) → 함수 인자로 넣어서 객체를 호출함
"""
@app.post("/step1/target-customer")
# 사용자 정보 POST 요청시 데이터 구조 검증 + 객체 생성 수행 -> customer변수에 요청된 데이터 저장
async def set_target_customer_enhanced(customer: TargetCustomer):
    # LLM으로 페르소나 생성
    persona_data = await generate_persona_with_llm(customer)
    """
    현재 프로젝트 상태에 타겟 고객과 페르소나 정보 저장
    pydantic 객체를 파이썬 딕셔너리로 변환하는 함수 model_dump() : 데이터베이스에 데이터만 저장하기 위함, pydantic객체는 유효성 검사가 포함된 복잡한 구조임
    """
    current_project["target_customer"] = customer.model_dump()
    current_project["persona"] = persona_data.model_dump()
    
    return {
        "message": "타겟 고객 분석하여 페르소나 프롬프트 생성",
        "target_customer": customer,
        "persona": persona_data
    }

# ==================================================================================
"""
사용자 입력 2단계 : 원하는 광고 컨셉 입력 받기
1단계에서 생성된 페르소나와 최신 트렌드 데이터를 기반으로, LLM이 맞춤형 광고 영상 생성을 위한 예시 프롬프트를 생성함
"""
@app.get("/step2/example-prompts")
async def get_llm_example_prompts():
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계를 완료해주세요.")
    
    persona = PersonaData(**current_project["persona"])
    # LLM을 사용하여 페르소나 기반 예시 광고 제작 프롬프트 생성
    example_prompts = await create_ad_example(persona)
    # 현재 프로젝트 상태에 예시 프롬프트 저장
    current_project["example_prompts"] = example_prompts
    return {
        "message": "AI가 생성한 맞춤형 광고 영상 프롬프트예시들입니다. 참고하여 원하는 영상을 설명해주세요.",
        "persona_summary": persona.persona_description,
        "example_prompts": example_prompts,
        "marketing_insights": persona.marketing_insights
    }

# ==================================================================================

@app.post("/step2/user-video-input")
async def submit_video_concept(user_input: UserVideoInput):
    """2단계: 사용자가 예시 프롬프트를 참고해서 작성한 영상 아이디어 입력 및 최적화"""
    if not current_project["example_prompts"]:
        raise HTTPException(status_code=400, detail="먼저 2-1단계(예시 프롬프트 생성)를 완료해주세요.")
    
    # 페르소나 정보도 필요 (최적화 시 타겟 정보 활용)
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계를 완료해주세요.")
    
    persona = PersonaData(**current_project["persona"])
    example_prompts = current_project["example_prompts"]  # 이전 단계에서 생성된 예시 프롬프트
    
    # 예시 프롬프트와 사용자 입력을 함께 전달하여 최적화
    final_prompt = await optimize_user_prompt_with_llm(persona, user_input, example_prompts)
    
    current_project["final_prompt"] = final_prompt.model_dump()
    
    return {
        "message": "예시 프롬프트를 기반으로 한 영상 아이디어가 전문적으로 최적화되었습니다.",
        "user_input": user_input,
        "based_on_example": example_prompts,  # 어떤 예시를 기반으로 했는지 표시
        "optimized_prompt": final_prompt.optimized_prompt,
        "key_scenes": final_prompt.key_scenes,
        "target_duration": final_prompt.target_duration
    }

@app.post("/step3/generate-enhanced-storyboard")
async def generate_enhanced_storyboard():
    """3단계: LLM 기반 상세 스토리보드 생성"""
    if not current_project["final_prompt"]:
        raise HTTPException(status_code=400, detail="먼저 1-2단계를 완료해주세요.")
    
    final_prompt = FinalVideoPrompt(**current_project["final_prompt"])
    storyboard = await generate_detailed_storyboard_with_llm(final_prompt)
    
    current_project["enhanced_storyboard"] = storyboard.model_dump()
    
    return {
        "message": "전문적인 상세 스토리보드가 생성되었습니다.",
        "storyboard": storyboard
    }

# ==================================================================================
# 기존 호환성을 위한 API 엔드포인트들

@app.post("/target-customer")
async def set_target_customer(customer: TargetCustomer):
    """기존 호환성: 타겟 고객 정보 설정"""
    persona = generate_persona(customer)
    current_project["target_customer"] = customer.model_dump()
    current_project["persona"] = {
        "target_customer": customer.model_dump(),
        "persona_description": persona,
        "marketing_insights": ""
    }
    
    return {
        "message": "타겟 고객 정보가 설정되었습니다.",
        "target_customer": customer,
        "persona": persona
    }

@app.get("/example-prompts")
async def get_example_prompts():
    """기존 호환성: 예시 프롬프트 생성"""
    if not current_project["target_customer"]:
        raise HTTPException(status_code=400, detail="먼저 타겟 고객을 설정해주세요.")
    
    customer_dict = current_project["target_customer"]
    example_prompt = generate_example_prompt(customer_dict)
    
    current_project["example_prompts"] = example_prompt
    
    return {
        "message": "예시 프롬프트가 생성되었습니다.",
        "example_prompt": example_prompt
    }

@app.post("/video-prompt")
async def create_video_prompt(user_input: UserVideoInput):
    """기존 호환성: 영상 프롬프트 생성"""
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 타겟 고객을 설정해주세요.")
    
    combined_prompt = combine_persona_and_prompt(
        current_project["persona"], 
        user_input.user_description
    )
    
    video_prompt = VideoPrompt(
        description=combined_prompt,
        persona=current_project["persona"],
        target_duration=60,
        key_scenes=["오프닝", "문제 제시", "솔루션", "혜택", "클로징"]
    )
    
    current_project["video_prompt"] = video_prompt.model_dump()
    
    return {
        "message": "영상 프롬프트가 생성되었습니다.",
        "video_prompt": video_prompt
    }

@app.post("/generate-storyboard")
async def generate_storyboard():
    """기존 호환성: 스토리보드 생성"""
    if not current_project["video_prompt"]:
        raise HTTPException(status_code=400, detail="먼저 영상 프롬프트를 생성해주세요.")
    
    scenes = create_basic_storyboard(current_project["video_prompt"])
    
    storyboard = Storyboard(
        video_prompt=VideoPrompt(**current_project["video_prompt"]),
        scenes=[StoryboardScene(**scene) for scene in scenes],
        total_duration=sum(scene["duration_seconds"] for scene in scenes)
    )
    
    current_project["storyboard"] = storyboard.model_dump()
    
    return {
        "message": "스토리보드가 생성되었습니다.",
        "storyboard": storyboard
    }

@app.get("/project")
async def get_current_project():
    """현재 프로젝트의 모든 데이터 반환"""
    return {
        "message": "현재 프로젝트 상태입니다.",
        "project": current_project
    }

@app.delete("/project/reset")
async def reset_project():
    """프로젝트 초기화"""
    global current_project
    current_project = {
        "target_customer": None,
        "persona": None,
        "example_prompts": None,
        "user_video_input": None,
        "final_prompt": None,
        "enhanced_storyboard": None,
        "video_prompt": None,
        "storyboard": None
    }
    
    return {
        "message": "프로젝트가 초기화되었습니다."
    }