from fastapi import FastAPI, HTTPException
from typing import List
import os
import asyncio

# 모델들을 별도 파일에서 import
from models import (
    TargetCustomer, PersonaData, UserVideoInput,
    ReferenceImage, SceneImagePrompt, StoryboardOutput
)

# LLM 유틸리티 함수들을 별도 파일에서 import
from persona_utils import (
    generate_persona, create_ad_example,
    generate_scene_image_prompts_with_llm, generate_images_with_runway,
    create_image_with_runway
)

# 웹 애플리케이션 객체(서버) 생성
app = FastAPI(title="Storyboard API")

# 전역 변수로 데이터 임시 저장 -> 데이터베이스로 연결 
current_project = {
    "target_customer": None,
    "persona": None,
    "example_prompts": None,
    "user_video_input": None,
    "storyboard": None
}

# 웹 브라우저가 서버로 GET 요청 
@app.get("/")
# 서버의 기본 주소로 GET 요청 보냈을때 실행할 비동기 root 함수 정의
async def root():
    # 요청에 대한 응답으로 서버가 잘 작동하고 있다는 메시지 출력
    return {"message": "Storyboard API", "status": "running"}

# ==================================================================================

"""
1단계 : LLM이 타겟 고객 정보와 최신 트렌드 데이터를 종합적으로 분석하여, 맞춤형 페르소나를 생성
단계별 상세 과정 이해하기
사용자 정보 POST 요청 → JSON 파싱(python dict로 변환) : 이 과정에서 데이터 유효성 검사 및 변환이 수행됨
→ 객체 생성(데이터 구조 생성) → 함수 인자로 넣어서 객체를 호출함 (customer)
"""
@app.post("/step1/target-customer")
# 사용자 정보 POST 요청시 데이터 구조 검증 + 객체 생성 수행 -> customer변수에 요청된 데이터 저장
async def set_target_customer_enhanced(customer: TargetCustomer):
    # LLM으로 페르소나 생성
    persona_data = await generate_persona(customer)
    # model_dump() : pydantic 객체를 파이썬 딕셔너리로 변환하는 함수 (데이터베이스에 데이터만 저장하기 위함, pydantic객체는 유효성 검사가 포함된 복잡한 구조임)
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
"""
2단계: 사용자 비디오 입력 받기
사용자가 예시 프롬프트를 보고 수정한 내용을 받음
"""
@app.post("/step2/video-input")
async def set_user_video_input(video_input: UserVideoInput):
    """사용자가 원하는 비디오 내용 입력"""
    if not current_project["example_prompts"]:
        raise HTTPException(status_code=400, detail="먼저 1-2단계(예시 프롬프트)를 완료해주세요.")
    
    # 사용자 입력 저장
    current_project["user_video_input"] = video_input.model_dump()
    
    return {
        "message": "사용자 비디오 입력이 저장되었습니다.",
        "video_input": video_input
    }

# ==================================================================================
"""
3단계: LLM 기반 장면별 이미지 프롬프트 생성
사용자 입력을 바탕으로 장면을 나누고 각 장면별 이미지 프롬프트 생성
"""
@app.post("/step3/generate-storyboard")
async def generate_storyboard():
    """3단계: LLM 기반 스토리보드 생성 (참조 이미지 없음)"""
    if not current_project["user_video_input"]:
        raise HTTPException(status_code=400, detail="먼저 1-2단계를 완료해주세요.")
    
    # 사용자 입력 가져오기
    user_input = UserVideoInput(**current_project["user_video_input"])
    
    # LLM으로 장면별 이미지 프롬프트 생성 (기존 방식)
    storyboard = await generate_scene_image_prompts_with_llm(user_input.user_description)
    
    # SceneImagePrompt 그대로 저장 (복잡한 변환 없이)
    current_project["storyboard"] = {
        "scenes": [scene.model_dump() for scene in storyboard.scenes],
        "total_scenes": len(storyboard.scenes),
        "estimated_duration": storyboard.estimated_duration,
        "video_concept": storyboard.video_concept
    }
    
    return {
        "message": "스토리보드가 성공적으로 생성되었습니다.",
        "storyboard": {
            "scenes": storyboard.scenes,
            "total_scenes": len(storyboard.scenes),
            "estimated_duration": storyboard.estimated_duration,
            "video_concept": storyboard.video_concept
        }
    }

# ==================================================================================
"""
4단계: Runway API를 활용한 실제 이미지 생성
스토리보드의 각 장면별 프롬프트를 Runway API로 전송하여 실제 이미지 생성
"""
@app.post("/step4/generate-images")
async def generate_storyboard_images():
    """4단계: Runway API를 사용하여 스토리보드의 모든 장면을 실제 이미지로 생성"""
    if not current_project["storyboard"]:
        raise HTTPException(status_code=400, detail="먼저 1-3단계를 완료해주세요.")
    
    # 저장된 스토리보드 데이터에서 SceneImagePrompt 객체들 복원
    storyboard_data = current_project["storyboard"]
    scenes = [SceneImagePrompt(**scene_data) for scene_data in storyboard_data["scenes"]]
    
    if not scenes:
        raise HTTPException(status_code=400, detail="생성할 장면이 없습니다.")
    
    runway_api_key = os.getenv("Runway_API_KEY")
    if not runway_api_key:
        # raise HTTPException(status_code=500, detail="Runway_API_KEY 환경 변수가 설정되지 않았습니다.")
        # 로컬 테스트를 위해 임시로 에러 대신 ValueError 발생
        raise ValueError("Runway_API_KEY 환경 변수가 설정되지 않았습니다.")

    # 결과 처리를 위한 리스트 초기화
    generated_images = []
    successful_count = 0
    failed_count = 0

    # 모든 장면을 순차적으로 하나씩 처리
    for i, scene in enumerate(scenes):
        scene_num = i + 1
        print(f"⏳ 장면 {scene_num}/{len(scenes)} 이미지 생성 시작...")
        try:
            # 각 장면의 이미지를 하나씩 생성하고 완료될 때까지 대기
            result = await create_image_with_runway(
                prompt_text=scene.promptText,
                ratio=scene.ratio,
                seed=scene.seed,
                model=scene.model,
                reference_images=[ref.model_dump() for ref in scene.referenceImages],
                public_figure_moderation=scene.publicFigureModeration,
                api_key=runway_api_key
            )
            
            # 작업 성공 시
            print(f"✅ 장면 {scene_num} 이미지 생성 완료: {result}")
            generated_images.append({
                "scene_number": scene_num,
                "status": "success",
                "image_url": result,
                "error": None
            })
            successful_count += 1

        except Exception as e:
            # 작업 실행 중 예외 발생 시
            print(f"❌ 장면 {scene_num} 이미지 생성 실패: {e}")
            generated_images.append({
                "scene_number": scene_num,
                "status": "failed",
                "error": str(e),
                "image_url": None
            })
            failed_count += 1
    
    total_scenes = len(scenes)
    success_rate = f"{(successful_count / total_scenes) * 100:.1f}%" if total_scenes > 0 else "0%"

    return {
        "message": "스토리보드 이미지 생성이 완료되었습니다.",
        "generated_images": generated_images,
        "summary": {
            "total_scenes": total_scenes,
            "successful": successful_count,
            "failed": failed_count,
            "success_rate": success_rate
        }
    }

# ==================================================================================
# 기존 호환성을 위한 API 엔드포인트들

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
        "storyboard": None
    }
    
    return {
        "message": "프로젝트가 초기화되었습니다."
    }