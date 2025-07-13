from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Body
from typing import List, Optional
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

# TTS 관련 함수들을 별도 파일에서 import
from storyboard_to_tts import generate_complete_tts_from_scratch

# 웹 애플리케이션 객체 생성
app = FastAPI(title="Storyboard API", version="1.0.0")

# 전역 변수로 데이터 임시 저장
current_project = {
    "persona": None,
    "reference_images": [],
    "analyzed_images": None,
    "ad_concept": None,
    "user_video_input": None,
    "storyboard": None
}

@app.get("/")
async def root():
    """서버 상태 확인"""
    return {"message": "Storyboard API", "status": "running", "version": "1.0.0"}

# ==================================================================================
# 1단계: 타겟 고객 정보 → 페르소나 생성
# ==================================================================================

@app.post("/step1/target-customer")
async def submit_target_customer(customer: TargetCustomer):
    """타겟 고객 정보를 받아 LLM으로 페르소나 생성"""
    # LLM으로 페르소나 생성
    persona_data = await generate_persona(customer)
    # 프로젝트 상태에 저장
    current_project["persona"] = persona_data.model_dump()
    
    return {
        "message": "타겟 고객 분석하여 페르소나가 생성되었습니다.",
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
    # 필요한 데이터가 모두 있는지 확인
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계(페르소나 생성)를 완료해주세요.")
    
    if not current_project["user_video_input"]:
        raise HTTPException(status_code=400, detail="사용자로부터 광고 영상 제작 아이디어를 입력받으세요.")
    
    # 모든 필요한 데이터 수집
    persona_data = current_project.get("persona")
    ad_concept = current_project.get("ad_concept", "")
    user_input = current_project.get("user_video_input")
    analyzed_images = current_project.get("analyzed_images", [])

    # 사용자 입력 데이터 추출
    user_input_text = user_input["user_description"]
    
    # 🚨 사용자 입력 검증
    if user_input_text in ["string", ""]:
        print("⚠️ 경고: 더미 데이터나 빈 값이 감지되었습니다!")
        print(f"   입력값: '{user_input_text}'")
        print("   실제 광고 아이디어를 입력해주세요.")
    
    # 🚨 핵심 디버깅: 전체 워크플로우 데이터 확인
    print("\n" + "="*80)
    print("🔍 [STEP3 전체 워크플로우 데이터 확인]")
    print("="*80)
    print(f"🎯 Step1 페르소나 데이터 존재: {bool(persona_data)}")
    if persona_data:
        print(f"   - 타겟 고객 국가: {persona_data.get('target_customer', {}).get('country', 'N/A')}")
        print(f"   - 타겟 고객 관심사: {persona_data.get('target_customer', {}).get('interests', 'N/A')}")
        print(f"   - 페르소나 설명: {persona_data.get('persona_description', 'N/A')[:100]}...")
    
    print(f"💡 Step2 광고 컨셉 존재: {bool(ad_concept)}")
    if ad_concept:
        print(f"   - 광고 컨셉: {ad_concept[:100]}...")
    
    print(f"✏️ Step3 사용자 입력: '{user_input_text}'")
    print(f"   - 입력 타입: {type(user_input_text)}")
    print(f"   - 입력 길이: {len(user_input_text)} 글자")
    
    print(f"📸 참조 이미지 개수: {len(analyzed_images)}")
    print("="*80 + "\n")
    
    # 참조 이미지 객체 변환
    enriched_images = [
        ReferenceImageWithDescription(**img_data) for img_data in analyzed_images
    ]
    
    # LLM으로 장면별 이미지 프롬프트 생성 - 모든 컨텍스트 정보 전달
    storyboard_prompts = await generate_scene_prompts(
        user_description=user_input_text,
        enriched_images=enriched_images,
        persona_data=persona_data,  # 페르소나 정보 추가
        ad_concept=ad_concept       # 광고 컨셉 정보 추가
    )
    
    # StoryboardOutput 출력구조로 스토리보드 각 장면별 데이터 저장
    current_project["storyboard"] = storyboard_prompts.model_dump()
    
    return {
        "message": "스토리보드가 성공적으로 생성되었습니다.",
        "storyboard": storyboard_prompts
    }

# ==================================================================================
# 4단계: 스토리보드 → Runway API 이미지 생성
# ==================================================================================

@app.post("/step4/generate-images")
async def run_image_generation(
    scenes_input: Optional[List[SceneImagePrompt]] = Body(None, alias="scenes")
):
    """스토리보드를 바탕으로 Runway API로 이미지 생성"""
    
    # --- 1. 생성할 장면 리스트 준비 ---
    scenes_to_process = []
    
    # 우선순위: 저장된 스토리보드 > 요청 본문
    if current_project.get("storyboard"):
        print("✅ 저장된 스토리보드에서 장면을 가져와 이미지 생성을 시작합니다.")
        storyboard_data = current_project["storyboard"]
        scenes_to_process = [SceneImagePrompt(**scene_data) for scene_data in storyboard_data.get("scenes", [])]
        print(f"📊 총 {len(scenes_to_process)}개 장면을 처리합니다.")
        
        # Runway API 호환성을 위한 ratio 값 검증 및 수정
        valid_ratios = ["1280:720", "720:1280", "1024:1024"]
        for scene in scenes_to_process:
            if scene.ratio not in valid_ratios:
                old_ratio = scene.ratio
                scene.ratio = "1280:720"  # 기본값으로 변경
                print(f"🔄 ratio 수정: {old_ratio} → {scene.ratio}")
        
        # 각 장면 미리보기
        for i, scene in enumerate(scenes_to_process, 1):
            print(f"   장면 {i}: {scene.prompt_text[:60]}...")
            
    elif scenes_input:
        # 직접 입력된 장면 사용
        print("ℹ️ 요청 본문에서 직접 받은 장면으로 이미지 생성을 시작합니다.")
        scenes_to_process = scenes_input
        
        # Runway API 호환성을 위한 ratio 값 검증 및 수정
        valid_ratios = ["1280:720", "720:1280", "1024:1024"]
        for scene in scenes_to_process:
            if scene.ratio not in valid_ratios:
                old_ratio = scene.ratio
                scene.ratio = "1280:720"
                print(f"🔄 ratio 수정: {old_ratio} → {scene.ratio}")
    else:
        # 둘 다 없으면 에러
        raise HTTPException(
            status_code=400, 
            detail="생성할 장면 데이터가 없습니다. 먼저 3단계(스토리보드 생성)를 완료하거나 scenes 데이터를 제공해주세요."
        )

    if not scenes_to_process:
        raise HTTPException(status_code=400, detail="생성할 장면 데이터가 없습니다.")

    # --- 2. API 키 확인 ---
    runway_api_key = os.getenv("RUNWAY_API_KEY")
    if not runway_api_key:
        raise HTTPException(status_code=500, detail="RUNWAY_API_KEY 환경 변수가 설정되지 않았습니다.")

    # --- 3. Runway API 호출 ---
    try:
        generated_images = await generate_images_sequentially(
            scenes=scenes_to_process,
            api_key=runway_api_key
        )
        
        # 결과 통계 계산
        successful_count = sum(1 for r in generated_images if r.get('status') == 'success')
        failed_count = len(generated_images) - successful_count
        total_scenes = len(generated_images)
        success_rate = f"{(successful_count / total_scenes) * 100:.1f}%" if total_scenes > 0 else "0%"

        # 🔥 4단계 결과를 current_project에 저장 (5단계에서 사용하기 위함)
        current_project["images"] = generated_images
        print(f"✅ 4단계 결과를 current_project에 저장했습니다. ({successful_count}개 성공)")

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
        raise HTTPException(status_code=500, detail=f"이미지 생성 중 오류 발생: {e}")

# ==================================================================================
"""
5단계: 스토리보드 → TTS 대본 및 오디오 생성
새로운 단계: 사용자가 생성한 스토리보드를 기반으로 TTS 대본과 오디오 파일을 생성
"""
@app.post("/video/create-tts-from-storyboard")
async def create_tts_from_storyboard():
    """스토리보드를 기반으로 TTS 대본 및 오디오 생성"""
    
    # 필요한 데이터가 모두 있는지 확인
    if not current_project.get("persona"):
        raise HTTPException(status_code=400, detail="먼저 1단계(페르소나 생성)를 완료해주세요.")
    
    if not current_project.get("storyboard"):
        raise HTTPException(status_code=400, detail="먼저 스토리보드를 생성해주세요.")
    
    try:
        # current_project에서 필요한 데이터 추출
        persona_data = current_project.get("persona", {})
        storyboard_data = current_project.get("storyboard", {})
        
        # 페르소나 정보 추출
        persona_description = persona_data.get("persona_description", "")
        marketing_insights = persona_data.get("marketing_insights", "")
        
        # 광고 컨셉 추출 (2단계에서 생성된 것 또는 기본값)
        ad_concept = current_project.get("ad_concept", "효과적인 광고 컨셉")
        
        # 스토리보드 장면 추출
        storyboard_scenes = storyboard_data.get("scenes", [])
        
        if not storyboard_scenes:
            raise HTTPException(status_code=400, detail="스토리보드에 장면 데이터가 없습니다.")
        
        print(f"🎵 TTS 생성 시작...")
        print(f"   페르소나: {len(persona_description)} 글자")
        print(f"   마케팅 인사이트: {len(marketing_insights)} 글자")
        print(f"   광고 컨셉: {len(ad_concept)} 글자")
        print(f"   스토리보드 장면: {len(storyboard_scenes)}개")
        
        # TTS 생성 함수 호출
        tts_result = await generate_complete_tts_from_scratch(
            persona_description=persona_description,
            marketing_insights=marketing_insights,
            ad_concept=ad_concept,
            storyboard_scenes=storyboard_scenes
        )
        
        # 결과를 current_project에 저장
        current_project["tts_result"] = tts_result
        
        return {
            "message": "TTS 대본 및 오디오 생성이 완료되었습니다.",
            "success": tts_result.get("success", False),
            "successful_count": tts_result.get("successful_count", 0),
            "failed_count": tts_result.get("failed_count", 0),
            "success_rate": tts_result.get("success_rate", "0%"),
            "results": tts_result.get("results", []),
            "processing_info": tts_result.get("processing_info", {})
        }
        
    except Exception as e:
        print(f"❌ TTS 생성 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"TTS 생성 실패: {str(e)}")

# ==================================================================================
# 유틸리티 엔드포인트들
# ==================================================================================

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
# 서버 정보
# ==================================================================================

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "message": "Storyboard API is running",
        "endpoints": {
            "step1": "POST /step1/target-customer - 타겟 고객 정보 입력",
            "step2": "POST /step2/ad-concept - 광고 컨셉 생성",  
            "step3": "POST /step3/user-video-input - 사용자 아이디어 입력 및 스토리보드 생성",
            "step4": "POST /step4/generate-images - 이미지 생성",
            "step5": "POST /video/generate-videos - 개별 영상 생성",
            "step6": "POST /video/merge-with-transitions - 영상 합치기",
            "step7": "POST /video/create-tts-from-storyboard - TTS 대본 및 오디오 생성",
            "step8": "POST /video/generate-subtitles + merge-with-tts-subtitles - 자막 생성 및 최종 합치기"
        }
    }

# 테스트용 current_project 설정 엔드포인트 (비활성화됨)
# @app.post("/set-project-images")
# async def set_project_images(request: dict):
#     """테스트용: current_project에 이미지 데이터 설정"""
#     images = request.get("images", [])
#     current_project["images"] = images
#     print(f"🔧 테스트용: current_project에 {len(images)}개 이미지 설정됨")
#     return {"message": f"{len(images)}개 이미지가 current_project에 설정되었습니다.", "images": images}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
