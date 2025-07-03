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
    generate_persona_with_llm, generate_example_prompts_with_llm,
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

# 이 함수는 굳이 왜 필요한가?
@app.get("/project/status")
async def get_project_status():
    """현재 프로젝트 진행 상태 확인"""
    status = {}
    for key, value in current_project.items():
        status[key] = value is not None
    return {"project_status": status, "current_data": current_project}

# 1단계 : 타겟 고객 정보 설정 및 LLM을 통한 페르소나 생성
"""
단계별 상세 과정 이해하기
사용자 정보 POST 요청 → JSON 파싱(python dict로 변환) → 데이터 검증 (앞서 설정한 데이터 구조와 일치하는지) → 객체 생성(데이터 구조 생성) → 
"""
@app.post("/step1/target-customer")
# 사용자 정보 POST 요청시 데이터 구조 검증 + 객체 생성 수행 -> customer변수에 요청된 데이터 저장
async def set_target_customer_enhanced(customer: TargetCustomer):
    # LLM으로 페르소나 생성
    persona_data = await generate_persona_with_llm(customer)
    
    current_project["target_customer"] = customer.model_dump()
    current_project["persona"] = persona_data.model_dump()
    
    return {
        "message": "타겟 고객 분석이 완료되었습니다.",
        "target_customer": customer,
        "persona": persona_data,
        "next_step": "2단계에서 제안된 테마를 참고하여 영상 아이디어를 입력해주세요."
    }

@app.get("/step2/example-prompts")
async def get_llm_example_prompts():
    """2단계: LLM 생성 예시 프롬프트들 제공"""
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계를 완료해주세요.")
    
    persona = PersonaData(**current_project["persona"])
    example_prompts = await generate_example_prompts_with_llm(persona)
    
    return {
        "message": "AI가 생성한 맞춤형 영상 예시들입니다. 참고하여 원하는 영상을 설명해주세요.",
        "persona_summary": persona.persona_description,
        "suggested_themes": persona.suggested_video_themes,
        "example_prompts": example_prompts,
        "marketing_insights": persona.marketing_insights
    }

@app.post("/step2/user-video-input")
async def process_user_video_input(user_input: UserVideoInput):
    """2단계: 사용자 영상 아이디어 입력 및 LLM 최적화"""
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계를 완료해주세요.")
    
    persona = PersonaData(**current_project["persona"])
    final_prompt = await optimize_user_prompt_with_llm(persona, user_input)
    
    current_project["final_prompt"] = final_prompt.model_dump()
    
    return {
        "message": "영상 아이디어가 전문적으로 최적화되었습니다.",
        "user_input": user_input,
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