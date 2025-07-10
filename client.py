from fastapi import FastAPI, HTTPException,Body
from typing import List,Optional
import os
import asyncio

# 모델들을 별도 파일에서 import
from models import (
    TargetCustomer, PersonaData, UserVideoInput,
    ReferenceImage, SceneImagePrompt, ReferenceImageWithDescription
)

# LLM 유틸리티 함수들을 별도 파일에서 import
from workflows import (
    generate_persona, create_ad_concept,
    generate_scene_prompts, generate_images_sequentially
)

# 웹 애플리케이션 객체 생성
app = FastAPI(title="Storyboard API")

# 전역 변수로 데이터 임시 저장 -> 데이터베이스로 연결 
current_project = {
    "persona": None,
    "reference_images": [],
    "analyzed_images": None,
    "ad_concept": None,
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
async def submit_target_customer(customer: TargetCustomer):
    # LLM으로 페르소나 생성
    persona_data = await generate_persona(customer)
    # model_dump() : pydantic 객체를 파이썬 딕셔너리로 변환하는 함수 (데이터베이스에 데이터만 저장하기 위함, pydantic객체는 유효성 검사가 포함된 복잡한 구조임)
    current_project["persona"] = persona_data.model_dump()
    
    return {
        "message": "타겟 고객 분석하여 페르소나 프롬프트 생성",
        "persona": persona_data
    }

# ==================================================================================

"""
2단계: (선택적) Reference Image 업로드 + Persona → Overall Ad Concept/Flow 생성
사용자는 이 단계를 건너뛰거나, reference image와 함께 전체적인 광고 컨셉을 생성할 수 있음
이미지 분석이 들어가기 때문에 돈을 좀 더 받아서 이 기능을 하게 하는것도 좋을 거 같음
"""
@app.post("/step2/generate-ad-concept-with-images")
async def generate_ad_concept_with_images(reference_images: Optional[List[ReferenceImage]] = Body(None)):
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계를 완료해주세요.")
    
    persona = PersonaData(**current_project["persona"])
    
    processed_reference_images = []
    if reference_images:
        current_project["reference_images"] = [img.model_dump() for img in reference_images]
        processed_reference_images = reference_images
    else:
        current_project["reference_images"] = []
    
    # LLM을 사용하여 광고 컨셉 생성
    concept_result = await create_ad_concept(persona, processed_reference_images)
    ad_concept = concept_result["ad_concept"]
    image_analyses_result = concept_result["image_analyses"]

    # 3. 현재 프로젝트 상태에 각각 저장
    current_project["ad_concept"] = ad_concept
    current_project["analyzed_images"] = image_analyses_result
    
    return {
        "message": "참조 이미지 분석 및 광고 컨셉이 생성되었습니다.",
        "ad_concept": ad_concept,
        "uploaded_images_count": len(processed_reference_images),
        "image_analyses": image_analyses_result
    }

# ==================================================================================
"""
사용자 입력 단계: 사용자가 최종 광고 컨셉/흐름 확정
사용자가 AI가 생성한 광고 컨셉을 보고 수정한 내용을 받음 ->사용자의 광고 아이디어
"""
@app.post("/step3/video-input")
async def set_user_video_input(video_input: UserVideoInput):
    """사용자가 광고 컨셉을 수정하여 최종 확정한 비디오 내용 입력"""
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계를 완료해주세요.")
    
    # 사용자가 입력하지 않았거나 빈 문자열인 경우, 2단계 ad_concept을 기본값으로 사용
    if not video_input.user_description or not video_input.user_description.strip():
        if current_project.get("ad_concept"):
            video_input.user_description = current_project["ad_concept"]
        else:
            raise HTTPException(status_code=400, detail="광고 컨셉이 없습니다. 먼저 2단계를 완료하거나 직접 입력해주세요.")
    
    # 사용자 입력 저장
    current_project["user_video_input"] = video_input.model_dump()
    stored_reference_images = current_project.get("analyzed_images", [])
    return {
        "message": "광고 영상 제작을 위한 최종 프롬프트가 저장되었습니다.",
        "video_input": video_input,
        "reference_images": stored_reference_images,
    }

# ==================================================================================
"""
    3단계 : LLM이 광고 영상 제작 아이디어를 보고 장면별 프롬프트를 생성
"""
@app.post("/step3/generate-storyboard")
async def generate_storyboard_prompts():
    # 사용자 입력 있는지 확인
    if not current_project["user_video_input"]:
        raise HTTPException(status_code=400, detail="사용자로부터 광고 영상 제작 아이디어를 입력받으세요.")
    
    # 사용자 입력 데이터랑 , 참조 이미지 분석 결과 가져오기
    user_input = current_project.get("user_video_input")
    analyzed_images = current_project.get("analyzed_images", [])

    # 사용자 입력 데이터만 추출
    user_input_text = user_input["user_description"]
    enriched_images = [
        ReferenceImageWithDescription(**img_data) for img_data in analyzed_images
    ]
    # LLM으로 장면별 이미지 프롬프트 생성 
    storyboard_prompts = await generate_scene_prompts(
        user_description=user_input_text,
        enriched_images=enriched_images  # 참조 이미지 분석 결과 전달
    )
    
    # StoryboardOutput 출력구조로 스토리보드 각 장면별 데이터 저장
    current_project["storyboard"] = storyboard_prompts.model_dump()
    
    return {
        "message": "스토리보드가 성공적으로 생성되었습니다.",
        "storyboard ": storyboard_prompts
    }

# ==================================================================================
"""
4단계: Runway API를 활용한 실제 이미지 생성
스토리보드의 각 장면별 프롬프트를 Runway API로 전송하여 실제 이미지 생성
"""
@app.post("/step4/generate-images")
async def run_image_generation(
    # FastAPI 표준에 맞춰 Optional과 Body를 사용하여 요청 본문을 받음
    scenes_input: Optional[List[SceneImagePrompt]] = Body(None, alias="scenes")
):  
    # --- 1. 생성할 장면 리스트 준비 ---
    scenes_to_process = []
    if scenes_input:
        # 요청 본문에 scenes가 직접 제공된 경우
        print("✅ 요청 본문에서 직접 받은 장면으로 이미지 생성을 시작합니다.")
        scenes_to_process = scenes_input
    else:
        # 요청 본문이 비어있으면, 저장된 상태(current_project)에서 가져옴
        print("ℹ️ 저장된 프로젝트 상태에서 장면을 가져와 이미지 생성을 시작합니다.")
        if not current_project.get("storyboard"):
            raise HTTPException(status_code=400, detail="생성된 스토리보드가 없습니다. 3단계를 먼저 완료해주세요.")
        
        storyboard_data = current_project["storyboard"]
        scenes_to_process = [SceneImagePrompt(**scene_data) for scene_data in storyboard_data.get("scenes", [])]

    if not scenes_to_process:
        raise HTTPException(status_code=400, detail="생성할 장면 데이터가 없습니다.")

    # --- 2. API 키 확인 ---
    runway_api_key = os.getenv("RUNWAY_API_KEY")
    if not runway_api_key:
        raise HTTPException(status_code=500, detail="RUNWAY_API_KEY 환경 변수가 설정되지 않았습니다.")

    # --- 3. 서비스 함수 호출 (단 한번만!) ---
    # try-except로 전체 작업의 예외를 처리합니다.
    try:
        # 전체 scenes 리스트를 한번에 넘겨주고, 모든 결과가 담긴 리스트를 받습니다.
        generated_images = await generate_images_sequentially(
            scenes=scenes_to_process,
            api_key=runway_api_key
        )
        
        successful_count = sum(1 for r in generated_images if r['status'] == 'success')
        failed_count = len(generated_images) - successful_count
        total_scenes = len(generated_images)
        success_rate = f"{(successful_count / total_scenes) * 100:.1f}%" if total_scenes > 0 else "0%"

        # --- 4. 최종 결과 반환 ---
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
    except Exception as e:
        # generate_images_sequentially 함수 자체에서 큰 오류가 발생한 경우
        raise HTTPException(status_code=500, detail=f"이미지 생성 중 심각한 오류 발생: {e}")


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
        "persona": None,
        "reference_images": [],
        "analyzed_images": None,
        "ad_concept": None,
        "user_video_input": None,
        "storyboard": None
    }
    
    return {
        "message": "프로젝트가 초기화되었습니다."
    }

# ==================================================================================