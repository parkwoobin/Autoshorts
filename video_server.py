"""
간소화된 비디오 서버: 트랜지션 및 비디오 합치기 전용
독립적인 FastAPI 서버
"""
import uvicorn
import os
import httpx
import asyncio
import re
import time
import traceback
import shutil
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Optional

# 로컬 모듈 import
from video_models import (
    VideoGenerationInput, VideoGenerationResult, VideoMergeRequest, 
    VideoMergeResult, TransitionMergeRequest, SubtitleCustomRequest,
    BGMGenerationRequest, TTSSubtitleRequest  # BGM과 TTS 모델 추가
)

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

print("🔑 환경변수 로드 완료")
print(f"   ELEVENLABS_API_KEY: {'✅ 설정됨' if os.getenv('ELEVENLABS_API_KEY') else '❌ 없음'}")
print(f"   OPENAI_API_KEY: {'✅ 설정됨' if os.getenv('OPENAI_API_KEY') else '❌ 없음'}")
print(f"   RUNWAY_API_KEY: {'✅ 설정됨' if os.getenv('RUNWAY_API_KEY') else '❌ 없음'}")
print(f"   SUNO_API_KEY: {'✅ 설정됨' if os.getenv('SUNO_API_KEY') else '❌ 없음'}")

# 비디오 서버 유틸리티 함수들 import
from video_server_utils import (
    create_merger_instance,
    generate_output_filename,
    create_video_response,
    get_transition_description
)
from video_models import VideoMergeRequest, VideoConfig, TransitionMergeRequest, SubtitleCustomRequest

# 비디오 처리 상태 추적을 위한 글로벌 변수
video_processing_status = {
    "is_processing": False,
    "current_step": "",
    "progress": 0,
    "total_steps": 0,
    "current_file": "",
    "start_time": None,
    "estimated_completion": None
}

# TTS와 자막 관련 import는 try-except로 처리
try:
    from tts_utils import create_tts_audio, create_multiple_tts_audio, get_elevenlabs_api_key
    TTS_AVAILABLE = True
except ImportError:
    print("⚠️ TTS 모듈을 찾을 수 없습니다. TTS 기능이 비활성화됩니다.")
    TTS_AVAILABLE = False

try:
    from subtitle_utils import generate_subtitles_with_whisper, merge_video_with_subtitles, merge_video_with_tts_and_subtitles
    SUBTITLE_AVAILABLE = True
except ImportError:
    print("⚠️ 자막 모듈을 찾을 수 없습니다. 자막 기능이 비활성화됩니다.")
    SUBTITLE_AVAILABLE = False

# SUNO BGM 생성 함수들
async def generate_suno_bgm(keyword: str = "happy", duration: int = 70):
    """SUNO API를 사용한 BGM 생성 (최대 70초)"""
    # 최대 70초로 제한
    if duration > 70:
        duration = 70
        print(f"⚠️ BGM 길이가 70초로 제한됩니다.")
    
    api_key = os.getenv('SUNO_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="SUNO_API_KEY가 설정되지 않았습니다.")
    
    api_endpoint = "https://api.sunoapi.org/api/v1/generate"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Custom Mode 페이로드
    payload = {
        "prompt": f"{keyword} upbeat band music with energetic guitar riffs, uplifting drums, positive vibes",
        "style": f"{keyword} rock band",
        "title": f"Happy {keyword.title()} Band Music",
        "customMode": True,
        "instrumental": True,
        "model": "V4",
        "callBackUrl": "https://api.example.com/callback"
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(api_endpoint, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"] is not None and "taskId" in data["data"]:
                return data["data"]["taskId"]
            else:
                raise HTTPException(status_code=500, detail="태스크 ID를 받을 수 없습니다.")
        else:
            error_text = response.text
            raise HTTPException(status_code=response.status_code, detail=f"SUNO API 오류: {error_text}")

async def check_suno_task_and_download(task_id: str):
    """SUNO 태스크 상태 확인 및 BGM 다운로드"""
    api_key = os.getenv('SUNO_API_KEY')
    status_endpoint = f"https://api.sunoapi.org/api/v1/generate/record-info?taskId={task_id}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(status_endpoint, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"🔍 SUNO API 응답: {data}")
            
            if not data or "data" not in data or data["data"] is None:
                return {"success": False, "status": "pending", "message": "응답 데이터를 기다리는 중입니다..."}
            
            data_obj = data["data"]
            status = data_obj.get("status", "unknown")
            
            if "response" not in data_obj or data_obj["response"] is None:
                return {"success": False, "status": status, "message": "BGM 생성 중입니다..."}
            
            response_data = data_obj["response"]
            
            if "sunoData" not in response_data or response_data["sunoData"] is None:
                return {"success": False, "status": status, "message": "BGM 데이터를 기다리는 중입니다..."}
            
            suno_data = response_data["sunoData"]
            
            if status == "SUCCESS" and suno_data and len(suno_data) > 0:
                # 첫 번째 클립 다운로드 (두 개가 있을 경우 더 짧은 버전 선택)
                if len(suno_data) >= 2:
                    clip = suno_data[0] if suno_data[0].get('duration', 0) < suno_data[1].get('duration', 0) else suno_data[1]
                else:
                    clip = suno_data[0]
                
                audio_url = clip.get('audioUrl')
                
                if audio_url:
                    # BGM 다운로드
                    audio_response = await client.get(audio_url)
                    if audio_response.status_code == 200:
                        # 파일 저장
                        os.makedirs("static/audio", exist_ok=True)
                        bgm_filename = f"suno_bgm_{task_id[:8]}.mp3"
                        bgm_path = os.path.join("static/audio", bgm_filename)
                        
                        with open(bgm_path, "wb") as f:
                            f.write(audio_response.content)
                        
                        return {
                            "success": True,
                            "bgm_path": bgm_path,
                            "bgm_filename": bgm_filename,
                            "duration": clip.get('duration', 0),
                            "title": clip.get('title', ''),
                            "tags": clip.get('tags', '')
                        }
                    else:
                        raise HTTPException(status_code=500, detail="BGM 다운로드 실패")
                else:
                    raise HTTPException(status_code=500, detail="오디오 URL을 찾을 수 없습니다.")
            else:
                return {"success": False, "status": status, "message": "BGM 생성 중입니다..."}
                
        else:
            error_text = response.text
            raise HTTPException(status_code=response.status_code, detail=f"태스크 상태 확인 실패: {error_text}")

# FastAPI app 생성
app = FastAPI(title="Video Server", description="비디오 생성 및 합치기 서버")

# 정적 파일 서빙 설정 (절대 경로 사용)
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# client.py의 모델들과 워크플로우 함수들 import (1-4단계용)
try:
    from models import (
        TargetCustomer, PersonaData, UserVideoInput,
        ReferenceImage, SceneImagePrompt, ReferenceImageWithDescription
    )
    from workflows import (
        generate_persona, create_ad_concept,
        generate_scene_prompts, generate_images_sequentially
    )
    CLIENT_MODELS_AVAILABLE = True
    print("✅ client.py 모델들과 워크플로우 함수들 import 완료")
except ImportError as e:
    CLIENT_MODELS_AVAILABLE = False
    print(f"⚠️ client.py 모델들 import 실패: {e}")

# 전역 변수로 프로젝트 데이터 저장 (client.py와 동일)
current_project = {
    "persona": None,
    "reference_images": [],
    "analyzed_images": None,
    "ad_concept": None,
    "user_video_input": None,
    "storyboard": None,
    "images": None,
    "generated_videos": None,
    "tts_result": None
}

def check_environment_variables():
    """필수 환경변수 체크"""
    required_vars = {
        "ELEVENLABS_API_KEY": "ElevenLabs TTS 서비스용",
        "OPENAI_API_KEY": "OpenAI LLM 서비스용", 
        "RUNWAY_API_KEY": "Runway 비디오 생성용",
        "SUNO_API_KEY": "SUNO 음성 생성용"
    }
    
    missing_vars = []
    for var_name, description in required_vars.items():
        if not os.getenv(var_name):
            missing_vars.append(f"{var_name} ({description})")
    
    if missing_vars:
        print("❌ 누락된 환경변수가 있습니다:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 .env 파일에 다음과 같이 설정해주세요:")
        for var_name in required_vars.keys():
            if not os.getenv(var_name):
                print(f"   {var_name}=your_api_key_here")
    else:
        print("✅ 모든 필수 환경변수가 설정되었습니다!")

# 서버 시작 시 환경변수 체크
check_environment_variables()

# ==================================================================================
# 1-4단계: client.py 워크플로우 통합
# ==================================================================================

@app.post("/step1/target-customer")
async def submit_target_customer(customer: TargetCustomer):
    """1단계: 타겟 고객 정보를 받아 LLM으로 페르소나 생성"""
    if not CLIENT_MODELS_AVAILABLE:
        raise HTTPException(status_code=500, detail="client.py 모델들을 찾을 수 없습니다.")
    
    try:
        # LLM으로 페르소나 생성
        persona_data = await generate_persona(customer)
        # 프로젝트 상태에 저장
        current_project["persona"] = persona_data.model_dump()
        
        print(f"✅ 1단계 완료: 페르소나 생성 성공")
        print(f"   타겟 고객: {customer.country}, {customer.age_range}")
        
        return {
            "step": "1단계_페르소나_생성",
            "success": True,
            "message": "타겟 고객 분석하여 페르소나가 생성되었습니다.",
            "persona": persona_data
        }
    except Exception as e:
        print(f"❌ 1단계 오류: {e}")
        raise HTTPException(status_code=500, detail=f"1단계 페르소나 생성 실패: {str(e)}")

@app.post("/step2/generate-ad-concept-with-images")
async def generate_ad_concept_with_images(reference_images: Optional[List[ReferenceImage]] = Body(None)):
    """2단계: Reference Image 업로드 + Persona → Overall Ad Concept 생성"""
    if not CLIENT_MODELS_AVAILABLE:
        raise HTTPException(status_code=500, detail="client.py 모델들을 찾을 수 없습니다.")
    
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계를 완료해주세요.")
    
    try:
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

        # 현재 프로젝트 상태에 각각 저장
        current_project["ad_concept"] = ad_concept
        current_project["analyzed_images"] = image_analyses_result
        
        print(f"✅ 2단계 완료: 광고 컨셉 생성 성공")
        print(f"   참조 이미지: {len(processed_reference_images)}개")
        print(f"   광고 컨셉: {ad_concept[:50]}...")
        
        return {
            "step": "2단계_광고_컨셉_생성",
            "success": True,
            "message": "참조 이미지 분석 및 광고 컨셉이 생성되었습니다.",
            "ad_concept": ad_concept,
            "uploaded_images_count": len(processed_reference_images),
            "image_analyses": image_analyses_result
        }
    except Exception as e:
        print(f"❌ 2단계 오류: {e}")
        raise HTTPException(status_code=500, detail=f"2단계 광고 컨셉 생성 실패: {str(e)}")

@app.post("/step3/video-input")
async def set_user_video_input(video_input: UserVideoInput):
    """3단계: 사용자가 광고 컨셉을 수정하여 최종 확정한 비디오 내용 입력"""
    if not CLIENT_MODELS_AVAILABLE:
        raise HTTPException(status_code=500, detail="client.py 모델들을 찾을 수 없습니다.")
    
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계를 완료해주세요.")
    
    try:
        # 사용자가 입력하지 않았거나 빈 문자열인 경우, 2단계 ad_concept을 기본값으로 사용
        if not video_input.user_description or not video_input.user_description.strip():
            if current_project.get("ad_concept"):
                video_input.user_description = current_project["ad_concept"]
            else:
                raise HTTPException(status_code=400, detail="광고 컨셉이 없습니다. 먼저 2단계를 완료하거나 직접 입력해주세요.")
        
        # 사용자 입력 저장
        current_project["user_video_input"] = video_input.model_dump()
        stored_reference_images = current_project.get("analyzed_images", [])
        
        print(f"✅ 3단계 완료: 사용자 비디오 입력 저장")
        print(f"   사용자 설명: {video_input.user_description[:50]}...")
        
        return {
            "step": "3단계_사용자_비디오_입력",
            "success": True,
            "message": "광고 영상 제작을 위한 최종 프롬프트가 저장되었습니다.",
            "video_input": video_input,
            "reference_images": stored_reference_images,
        }
    except Exception as e:
        print(f"❌ 3단계 오류: {e}")
        raise HTTPException(status_code=500, detail=f"3단계 사용자 입력 저장 실패: {str(e)}")

@app.post("/step3/generate-storyboard")
async def generate_storyboard_prompts():
    """3단계: LLM이 광고 영상 제작 아이디어를 보고 장면별 프롬프트를 생성"""
    if not CLIENT_MODELS_AVAILABLE:
        raise HTTPException(status_code=500, detail="client.py 모델들을 찾을 수 없습니다.")
    
    # 필요한 데이터가 모두 있는지 확인
    if not current_project["persona"]:
        raise HTTPException(status_code=400, detail="먼저 1단계(페르소나 생성)를 완료해주세요.")
    
    if not current_project["user_video_input"]:
        raise HTTPException(status_code=400, detail="사용자로부터 광고 영상 제작 아이디어를 입력받으세요.")
    
    try:
        # 모든 필요한 데이터 수집
        persona_data = current_project.get("persona")
        ad_concept = current_project.get("ad_concept", "")
        user_input = current_project.get("user_video_input")
        analyzed_images = current_project.get("analyzed_images", [])

        # 사용자 입력 데이터 추출
        user_input_text = user_input["user_description"]
        
        print(f"🎬 3단계: 스토리보드 생성 시작...")
        print(f"   사용자 입력: {user_input_text[:50]}...")
        print(f"   참조 이미지: {len(analyzed_images)}개")
        
        # 참조 이미지 객체 변환
        enriched_images = [
            ReferenceImageWithDescription(**img_data) for img_data in analyzed_images
        ]
        
        # LLM으로 장면별 이미지 프롬프트 생성
        storyboard_prompts = await generate_scene_prompts(
            user_description=user_input_text,
            enriched_images=enriched_images,
            persona_data=persona_data,
            ad_concept=ad_concept
        )
        
        # 스토리보드 저장
        current_project["storyboard"] = storyboard_prompts.model_dump()
        
        print(f"✅ 3단계 완료: 스토리보드 생성 성공")
        print(f"   생성된 장면: {len(storyboard_prompts.scenes)}개")
        
        return {
            "step": "3단계_스토리보드_생성",
            "success": True,
            "message": "스토리보드가 성공적으로 생성되었습니다.",
            "storyboard": storyboard_prompts
        }
    except Exception as e:
        print(f"❌ 3단계 스토리보드 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"3단계 스토리보드 생성 실패: {str(e)}")

@app.post("/step4/generate-images")
async def run_image_generation(
    scenes_input: Optional[List[SceneImagePrompt]] = Body(None, alias="scenes")
):
    """4단계: 스토리보드를 바탕으로 DALL-E 3 이미지 생성"""
    if not CLIENT_MODELS_AVAILABLE:
        raise HTTPException(status_code=500, detail="client.py 모델들을 찾을 수 없습니다.")
    
    try:
        # 생성할 장면 리스트 준비
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
                    
        elif scenes_input:
            print("ℹ️ 요청 본문에서 직접 받은 장면으로 이미지 생성을 시작합니다.")
            scenes_to_process = scenes_input
        else:
            raise HTTPException(
                status_code=400, 
                detail="생성할 장면 데이터가 없습니다. 먼저 3단계(스토리보드 생성)를 완료하거나 scenes 데이터를 제공해주세요."
            )

        if not scenes_to_process:
            raise HTTPException(status_code=400, detail="생성할 장면 데이터가 없습니다.")

        # API 키 확인
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

        print(f"🎨 4단계: DALL-E 3 이미지 생성 시작...")
        
        # DALL-E 3 이미지 생성
        generated_images = await generate_images_sequentially(
            scenes=scenes_to_process,
            api_key=openai_api_key
        )
        
        # 결과 통계 계산
        successful_count = sum(1 for r in generated_images if r.get('status') == 'success')
        failed_count = len(generated_images) - successful_count
        total_scenes = len(generated_images)
        success_rate = f"{(successful_count / total_scenes) * 100:.1f}%" if total_scenes > 0 else "0%"

        # 4단계 결과를 current_project에 저장 (5단계에서 사용하기 위함)
        current_project["images"] = generated_images
        print(f"✅ 4단계 완료: DALL-E 3 이미지 생성 성공 ({successful_count}개 성공)")

        return {
            "step": "4단계_이미지_생성",
            "success": True,
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
        print(f"❌ 4단계 이미지 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"4단계 이미지 생성 실패: {str(e)}")

@app.post("/step5/generate-videos")
async def run_video_generation():
    """5단계: 4단계에서 생성된 이미지들을 Runway API로 비디오 변환"""
    return await generate_videos()

# ==================================================================================
# 기존 5-8단계 엔드포인트들
# ==================================================================================

@app.get("/tts-selector", response_class=HTMLResponse)
async def tts_voice_selector():
    """TTS 음성 선택 웹 인터페이스"""
    try:
        with open("static/tts_voice_selector.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>TTS Voice Selector not found</h1>", 
            status_code=404
        )

@app.get("/video/processing-status")
async def get_processing_status():
    """실시간 비디오 처리 상태 확인 (간단한 형태)"""
    
    processing_info = {
        "is_processing": video_processing_status["is_processing"],
        "current_step": video_processing_status["current_step"],
        "progress": video_processing_status["progress"],
        "current_file": video_processing_status["current_file"]
    }
    
    if video_processing_status["start_time"] and video_processing_status["is_processing"]:
        elapsed_time = time.time() - video_processing_status["start_time"]
        processing_info["elapsed_time_seconds"] = int(elapsed_time)
        processing_info["elapsed_time_formatted"] = f"{int(elapsed_time // 60)}분 {int(elapsed_time % 60)}초"
        
        # 남은 시간 추정 (간단한 방식)
        if video_processing_status["progress"] > 0:
            estimated_total_time = elapsed_time * (100 / video_processing_status["progress"])
            remaining_time = max(0, estimated_total_time - elapsed_time)
            processing_info["estimated_remaining_seconds"] = int(remaining_time)
            processing_info["estimated_remaining_formatted"] = f"{int(remaining_time // 60)}분 {int(remaining_time % 60)}초"
    
    return processing_info

@app.get("/video/status")
async def get_video_status():
    """비디오 기능 상태 확인"""
    
    # 현재 처리 상태 정보 계산
    processing_info = {
        "is_processing": video_processing_status["is_processing"],
        "current_step": video_processing_status["current_step"],
        "progress": video_processing_status["progress"],
        "current_file": video_processing_status["current_file"]
    }
    
    if video_processing_status["start_time"]:
        elapsed_time = time.time() - video_processing_status["start_time"]
        processing_info["elapsed_time_seconds"] = int(elapsed_time)
        processing_info["elapsed_time_formatted"] = f"{int(elapsed_time // 60)}분 {int(elapsed_time % 60)}초"
    
    return {
        "status": "active",
        "message": "🎬 ShortPilot AI 비디오 생성 파이프라인이 활성화되었습니다.",
        "processing_status": processing_info,
        "available_endpoints": {
            "GET /video/status": "🏠 현재 페이지 - 전체 시스템 상태 확인",
            "GET /video/processing-status": "⏳ 실시간 비디오 처리 상태 확인 (진행률, 남은 시간 등)",
            
            "📊 1단계: 페르소나 분석": {
                "POST /step1/target-customer": "타겟 고객 정보 → LLM 페르소나 생성"
            },
            
            "💡 2단계: 광고 컨셉 생성": {
                "POST /step2/generate-ad-concept-with-images": "페르소나 + 참조 이미지 → 광고 컨셉 생성"
            },
            
            "✏️ 3단계: 사용자 입력 & 스토리보드": {
                "POST /step3/video-input": "사용자 광고 아이디어 입력",
                "POST /step3/generate-storyboard": "사용자 아이디어 → LLM 스토리보드 생성"
            },
            
            "🎨 4단계: 이미지 생성": {
                "POST /step4/generate-images": "스토리보드 → DALL-E 3 이미지 생성"
            },
            
            "🎬 5단계: 이미지 → 비디오 변환": {
                "POST /video/generate-videos": "Runway API를 통한 4단계 이미지들 → 비디오 변환"
            },
            
            "🎵 5.5단계: BGM 생성": {
                "POST /bgm/generate-and-wait": "🆕 키워드 기반 BGM 생성 및 자동 완성 (최대 70초, 파일까지 자동 다운로드)"
            },
            
            "✂️ 6단계: 비디오 + BGM 합치기": {
                "POST /video/merge-with-transitions": "5단계 비디오들을 랜덤 트랜지션으로 합치기 (BGM on/off 선택 가능)"
            },
            
            "🎙️ 7단계: TTS 음성 생성": {
                "POST /video/create-tts-from-storyboard": "OpenAI LLM + ElevenLabs를 통한 스토리보드 기반 TTS 내레이션 자동 생성"
            },
            
            "🎵 SUNO BGM 시스템": {
                "GET /bgm/status/{task_id}": "BGM 생성 상태 확인 및 다운로드"
            },
            
            "📝 8단계: 완전한 영상 제작": {
                "POST /video/generate-subtitles": "8-1단계: TTS 오디오에서 Whisper로 자막 파일(.srt) 생성",
                "POST /video/merge-with-tts-subtitles": "8-2단계: 비디오 + TTS + 자막 완전 합치기",
                "POST /video/merge-with-custom-subtitles": "🎨 커스텀 자막: SRT 파일과 폰트 설정으로 자막 커스터마이징"
            },
            
            "🛠️ 유틸리티": {
                "GET /tts-selector": "TTS 음성 선택 웹 인터페이스"
            }
        },
        "workflow_steps": {
            "1단계": "타겟 고객 정보 → LLM 페르소나 생성",
            "2단계": "페르소나 + 참조 이미지 → 광고 컨셉 생성",
            "3단계": "사용자 아이디어 → LLM 스토리보드 생성",
            "4단계": "스토리보드 → DALL-E 3 이미지 생성",
            "5단계": "이미지 → 비디오 변환 (Runway API)",
            "5.5단계": "키워드 기반 BGM 생성 (SUNO API)",
            "6단계": "비디오 + BGM 트랜지션 합치기",
            "7단계": "TTS 내레이션 생성 (OpenAI + ElevenLabs)",
            "8단계": "최종 영상 완성 (TTS + 자막만, BGM은 6단계 포함)"
        },
        "features": [
            "🎬 완전한 AI 비디오 생성 파이프라인 (1-8단계)",
            "🤖 OpenAI GPT-4 기반 콘텐츠 생성",
            "� DALL-E 3 스토리보드 이미지 생성",
            "�🎥 Runway API 이미지→비디오 변환",
            "🎙️ ElevenLabs TTS 음성 생성",
            "📝 Whisper AI 자동 자막 생성",
            "🎵 SUNO AI API 키워드 기반 70s 음성 생성",
            "✂️ 9가지 트랜지션 효과 (랜덤 선택)",
            "🚀 스트리밍 방식 처리 (다운로드 없음)",
            "📱 브라우저에서 바로 재생 가능",
            "🎨 Frame-level animation 지원",
            "🔧 0.1초 정밀도 자막 싱크",
            "🎤 다중 오디오 트랙 믹싱 (TTS + BGM)",
            "📊 실시간 진행상황 모니터링"
        ],
        "tech_stack": {
            "AI_Models": ["OpenAI GPT-4o-mini", "DALL-E 3", "Whisper", "SUNO V4"],
            "Video_APIs": ["Runway Gen4 Turbo"],
            "Audio_APIs": ["ElevenLabs TTS"],
            "Backend": ["FastAPI", "Python", "FFmpeg"],
            "Processing": ["비동기 처리", "스트리밍", "실시간 상태 확인"]
        }
    }

@app.post("/video/create-tts-from-storyboard")
async def create_tts_from_storyboard():
    """7단계: current_project의 스토리보드 기반 장면별 TTS 생성"""
    try:
        print(f"🎙️ 7단계: 스토리보드 기반 장면별 TTS 내레이션 생성 시작...")
        
        # current_project에서 필요한 데이터 확인
        if not current_project.get("persona"):
            raise HTTPException(status_code=400, detail="1단계 페르소나 데이터가 없습니다. 먼저 1단계를 완료해주세요.")
        
        if not current_project.get("ad_concept"):
            raise HTTPException(status_code=400, detail="2단계 광고 컨셉이 없습니다. 먼저 2단계를 완료해주세요.")
        
        if not current_project.get("storyboard"):
            raise HTTPException(status_code=400, detail="3단계 스토리보드가 없습니다. 먼저 3단계를 완료해주세요.")
        
        # current_project 데이터 추출
        persona_data = current_project["persona"]
        ad_concept = current_project["ad_concept"]
        storyboard_data = current_project["storyboard"]
        
        # 페르소나 정보 추출
        persona_description = persona_data.get("persona_description", "")
        marketing_insights = persona_data.get("marketing_insights", "")
        target_customer = persona_data.get("target_customer", {})
        
        # 스토리보드 장면들 추출
        scenes = storyboard_data.get("scenes", [])
        
        if not scenes:
            raise HTTPException(status_code=400, detail="스토리보드에 장면이 없습니다.")
        
        print(f"✅ current_project 데이터 로드 완료:")
        print(f"   📊 페르소나: {persona_description[:50]}{'...' if len(persona_description) > 50 else ''}")
        print(f"   💡 광고 컨셉: {ad_concept[:50]}{'...' if len(ad_concept) > 50 else ''}")
        print(f"   🎬 스토리보드 장면 수: {len(scenes)}개")

        # 각 장면별로 TTS 스크립트 생성
        tts_scripts = []
        
        for i, scene in enumerate(scenes, 1):
            scene_description = scene.get("scene_description", "")
            scene_prompt = scene.get("prompt_text", "")
            
            print(f"\n🎤 [{i}/{len(scenes)}] 장면 {i} TTS 스크립트 생성 중...")
            print(f"   📝 장면 설명: {scene_description[:60]}...")
            
            # 각 장면에 맞는 OpenAI LLM 프롬프트 생성
            llm_prompt = f"""
당신은 전문 광고 내레이션 작가입니다. 
주어진 정보를 바탕으로 해당 장면에 딱 맞는 짧고 임팩트 있는 TTS 내레이션을 한국어로 작성해주세요.

**타겟 고객 (페르소나):**
{persona_description}

**전체 광고 컨셉:**
{ad_concept}

**현재 장면 정보 (장면 {i}):**
- 장면 설명: {scene_description}
- 이미지 프롬프트: {scene_prompt}

**TTS 요구사항:**
- 이 장면에 딱 맞는 내레이션 1문장
- 20-35자 이내 (3초 분량)
- 간결하고 임팩트 있게
- 타겟 고객에게 어필할 수 있는 톤
- 전체 광고 컨셉과 일치해야 함

**출력 형식:**
장면에 맞는 TTS 내레이션만 작성해주세요. 다른 설명은 필요 없습니다.

TTS 내레이션:"""
            
            # OpenAI API 호출
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 광고 내레이션 전문가입니다. 각 장면에 맞는 매력적이고 설득력 있는 한국어 내레이션을 작성합니다."
                    },
                    {
                        "role": "user",
                        "content": llm_prompt
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.7
            }
            
            try:
                print(f"   🌐 OpenAI API 호출 중...")
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code != 200:
                        error_text = response.text
                        print(f"   ❌ OpenAI API 오류: {error_text}")
                        generated_text = f"장면 {i} 내레이션"  # 기본값
                    else:
                        response_data = response.json()
                        generated_text = response_data["choices"][0]["message"]["content"].strip()
                        
                        # "TTS 내레이션:" 접두사 제거
                        if generated_text.startswith("TTS 내레이션:"):
                            generated_text = generated_text.replace("TTS 내레이션:", "").strip()
                        
                        # 길이 제한 (35자)
                        if len(generated_text) > 35:
                            generated_text = generated_text[:35]
                            # 마지막 공백에서 자르기
                            last_space = generated_text.rfind(' ')
                            if last_space > 25:
                                generated_text = generated_text[:last_space]
                        
                        print(f"   ✅ 장면 {i} TTS 생성 완료: {generated_text}")
                        
            except Exception as api_error:
                print(f"   ❌ 장면 {i} OpenAI API 호출 실패: {api_error}")
                generated_text = f"장면 {i} 내레이션"
            
            # TTS 스크립트 정보 저장
            tts_scripts.append({
                "scene_number": i,
                "scene_description": scene_description,
                "text": generated_text,
                "estimated_duration": min(len(generated_text) * 0.08, 3.5),
                "char_count": len(generated_text),
                "scene_data": scene
            })

        print(f"\n✅ 총 {len(tts_scripts)}개 장면별 TTS 스크립트 생성 완료:")
        for script in tts_scripts:
            duration_est = script.get('estimated_duration', 3.0)
            char_count = script.get('char_count', 0)
            print(f"   - 장면 {script['scene_number']}: {script['text']} ({char_count}자, 예상 {duration_est:.1f}초)")

        # ElevenLabs TTS 변환
        print(f"\n🎤 ElevenLabs TTS 변환 시작...")
        successful_tts = []
        failed_tts = []
        
        try:
            if TTS_AVAILABLE:
                script_texts = [script["text"] for script in tts_scripts]
                
                # TTS 오디오 생성
                api_key = get_elevenlabs_api_key()
                output_dir = os.path.abspath("static/audio")
                tts_results = await create_multiple_tts_audio(
                    text_list=script_texts,
                    voice_id='21m00Tcm4TlvDq8ikWAM',  # 기본 음성
                    api_key=api_key,
                    output_dir=output_dir
                )
                
                # 결과 처리
                for i, (script, result) in enumerate(zip(tts_scripts, tts_results)):
                    if result.success:
                        audio_filename = os.path.basename(result.audio_file_path)
                        audio_url = f"/static/audio/{audio_filename}"
                        
                        successful_tts.append({
                            "scene_number": script["scene_number"],
                            "scene_description": script["scene_description"],
                            "text": script["text"],
                            "audio_url": audio_url,
                            "audio_file_path": result.audio_file_path,
                            "audio_filename": audio_filename,
                            "duration": result.duration,
                            "file_size": result.file_size,
                            "estimated_duration": script["estimated_duration"]
                        })
                        print(f"   ✅ 장면 {script['scene_number']} TTS 완료: {audio_filename}")
                    else:
                        failed_tts.append({
                            "scene_number": script["scene_number"],
                            "scene_description": script["scene_description"],
                            "text": script["text"],
                            "error": result.error
                        })
                        print(f"   ❌ 장면 {script['scene_number']} TTS 실패: {result.error}")
            else:
                print("❌ TTS 모듈을 찾을 수 없습니다. 스크립트만 생성됩니다.")
                # TTS 모듈 없으면 스크립트만 반환
                for script in tts_scripts:
                    successful_tts.append({
                        "scene_number": script["scene_number"],
                        "scene_description": script["scene_description"],
                        "text": script["text"],
                        "audio_url": None,
                        "audio_file_path": None,
                        "note": "TTS 모듈 없음"
                    })
            
        except Exception as tts_error:
            print(f"❌ TTS 변환 중 오류 발생: {tts_error}")
            # TTS 실패 시 스크립트만 반환
            for script in tts_scripts:
                failed_tts.append({
                    "scene_number": script["scene_number"],
                    "scene_description": script["scene_description"],
                    "text": script["text"],
                    "error": str(tts_error)
                })

        # 7단계 결과를 current_project에 저장 (8단계에서 사용)
        current_project["tts_result"] = {
            "tts_scripts": tts_scripts,
            "successful_tts": successful_tts,
            "failed_tts": failed_tts,
            "total_scenes": len(scenes)
        }
        
        # 7단계 완료 후 TTS 파일명들을 TXT 파일로 저장
        print(f"📝 7단계 완료된 TTS 파일명 저장 중...")
        tts_file_list_file = "tts_file_list.txt"
        try:
            with open(tts_file_list_file, 'w', encoding='utf-8') as f:
                for tts in successful_tts:
                    if tts.get("audio_file_path"):
                        f.write(tts["audio_file_path"] + '\n')
                        f.write(f"TEXT:{tts['text']}\n")  # 원본 텍스트도 함께 저장
                        f.write(f"DURATION:{tts.get('duration', 3.0)}\n")  # 길이 정보도 저장
                        f.write("---\n")  # 구분자
            
            print(f"✅ 7단계 TTS 파일명 저장 성공!")
            print(f"   파일 위치: {os.path.abspath(tts_file_list_file)}")
            print(f"   저장된 TTS 파일: {len(successful_tts)}개")
            
        except Exception as e:
            print(f"❌ 7단계 TTS 파일명 저장 실패: {e}")
        
        print(f"\n✅ 7단계 완료: 장면별 TTS 생성 성공!")
        print(f"   📊 성공: {len(successful_tts)}개, 실패: {len(failed_tts)}개")
        print(f"   📈 성공률: {(len(successful_tts) / len(tts_scripts)) * 100:.1f}%")
        
        return {
            "step": "7단계_장면별_TTS_생성",
            "success": True,
            "message": f"스토리보드 기반 장면별 TTS 내레이션 생성 완료! {len(successful_tts)}개 장면 처리",
            "source_data": {
                "persona_description": persona_description[:100] + "..." if len(persona_description) > 100 else persona_description,
                "ad_concept": ad_concept[:100] + "..." if len(ad_concept) > 100 else ad_concept,
                "total_scenes": len(scenes)
            },
            "tts_scripts": tts_scripts,
            "successful_tts": successful_tts,
            "failed_tts": failed_tts,
            "summary": {
                "total_scenes": len(tts_scripts),
                "successful": len(successful_tts),
                "failed": len(failed_tts),
                "success_rate": f"{(len(successful_tts) / len(tts_scripts)) * 100:.1f}%" if tts_scripts else "0%"
            },
            "workflow_integration": {
                "used_step1_persona": True,
                "used_step2_ad_concept": True,
                "used_step3_storyboard": True,
                "scene_based_generation": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 7단계 장면별 TTS 생성 중 오류 발생: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"7단계 장면별 TTS 생성 중 오류 발생: {str(e)}"
        )

def _create_srt_content(self, sequence_number: int, start_time: float, end_time: float, text: str) -> str:
    """SRT 포맷으로 자막 내용 생성"""
    def seconds_to_srt_time(seconds: float) -> str:
        """초를 SRT 시간 포맷(HH:MM:SS,mmm)으로 변환"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    start_srt = seconds_to_srt_time(start_time)
    end_srt = seconds_to_srt_time(end_time)
    
    return f"""{sequence_number}
{start_srt} --> {end_srt}
{text}

"""

def create_srt_content(sequence_number: int, start_time: float, end_time: float, text: str) -> str:
    """SRT 포맷으로 자막 내용 생성"""
    def seconds_to_srt_time(seconds: float) -> str:
        """초를 SRT 시간 포맷(HH:MM:SS,mmm)으로 변환"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    start_srt = seconds_to_srt_time(start_time)
    end_srt = seconds_to_srt_time(end_time)
    
    return f"""{sequence_number}
{start_srt} --> {end_srt}
{text}

"""
async def generate_videos():
    """5단계: 4단계에서 생성된 이미지들을 비디오로 변환"""
    
    # video_server.py의 current_project에서 4단계 이미지들 가져오기
    if not current_project.get("images"):
        raise HTTPException(
            status_code=400,
            detail="4단계에서 생성된 이미지가 없습니다. 먼저 4단계를 완료해주세요."
        )
    
    # 4단계에서 생성된 이미지 URL들 추출
    image_data_list = current_project["images"]
    image_urls = []
    
    print(f"🔧 current_project['images'] 내용: {len(image_data_list)}개")
    
    for i, img_data in enumerate(image_data_list):
        print(f"🔧 이미지 {i+1} 데이터: {type(img_data)} - {str(img_data)[:100]}...")
        
        # 다양한 형태의 이미지 데이터 처리
        if isinstance(img_data, dict):
            if img_data.get("url"):
                    image_urls.append(img_data["url"])
        # 다양한 형태의 이미지 데이터 처리
        if isinstance(img_data, dict):
            if img_data.get("url"):
                image_urls.append(img_data["url"])
            elif img_data.get("image_url"):
                image_urls.append(img_data["image_url"])
            elif img_data.get("generated_image_url"):
                image_urls.append(img_data["generated_image_url"])
        elif isinstance(img_data, str):
            image_urls.append(img_data)
    
    if not image_urls:
        print(f"❌ 추출된 URL이 없습니다.")
        raise HTTPException(
            status_code=400,
            detail="4단계 이미지 데이터에서 유효한 URL을 찾을 수 없습니다."
        )
    
    print(f"✅ 4단계에서 가져온 이미지: {len(image_urls)}개")
    
    print("🎬 5단계: 4단계 이미지들 → 비디오 변환 시작...")
    
    # video_models.py 설정 사용
    from video_models import ImageToVideoRequest, VideoGenerationResult
    
    video_request = ImageToVideoRequest(
        image_urls=image_urls,
        duration_per_scene=5,
        resolution="720:1280",
        model="gen4_turbo"
    )
    
    print(f"🎬 Runway API 설정:")
    print(f"   - 모델: {video_request.model}")
    print(f"   - 해상도: {video_request.resolution}")
    print(f"   - 장면당 길이: {video_request.duration_per_scene}초")
    
    # Runway API를 통한 이미지 → 동영상 변환
    generated_videos = []
    
    try:
        runway_api_key = os.getenv("RUNWAY_API_KEY")
        
        if not runway_api_key:
            raise HTTPException(
                status_code=500,
                detail="RUNWAY_API_KEY 환경 변수가 설정되지 않았습니다."
            )
        
        print("🚀 Runway API를 통한 이미지 → 동영상 변환 시작...")
        
        headers = {
            "Authorization": f"Bearer {runway_api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06"
        }
        
        base_url = "https://api.dev.runwayml.com/v1"
        
        async with httpx.AsyncClient(timeout=300) as client:
            for i, image_url in enumerate(image_urls, 1):
                print(f"\n🎬 [{i}/{len(image_urls)}] 이미지 → 동영상 변환 중...")
                print(f"   🖼️ 소스 이미지: {image_url}")
                
                payload = {
                    "model": video_request.model,
                    "promptImage": image_url,
                    "duration": video_request.duration_per_scene,
                    "ratio": video_request.resolution,
                    "seed": 42
                }
                
                try:
                    # 동영상 생성 작업 요청
                    print(f"📤 Runway API 요청: 이미지 → 동영상 변환...")
                    response = await client.post(f"{base_url}/image_to_video", headers=headers, json=payload)
                    
                    if response.status_code != 200:
                        raise Exception(f"API 요청 실패: {response.text}")
                    
                    task_id = response.json()["id"]
                    print(f"  -> 작업 ID: {task_id}")

                    # 작업 완료까지 폴링
                    for attempt in range(60):
                        await asyncio.sleep(5)
                        
                        status_response = await client.get(f"{base_url}/tasks/{task_id}", headers=headers)
                        status_data = status_response.json()
                        
                        if status_data["status"] == "SUCCEEDED":
                            video_url = status_data["output"][0]
                            print(f"  ✅ 동영상 생성 완료: {video_url}")
                            
                            result = VideoGenerationResult(
                                scene_number=i,
                                status="success",
                                video_url=video_url,
                                duration=video_request.duration_per_scene,
                                resolution=video_request.resolution
                            )
                            generated_videos.append(result.model_dump())
                            break
                        elif status_data["status"] == "FAILED":
                            print(f"  ❌ 동영상 생성 실패: {status_data.get('failure')}")
                            result = VideoGenerationResult(
                                scene_number=i,
                                status="error",
                                error=f"생성 실패: {status_data.get('failure')}",
                                duration=video_request.duration_per_scene,
                                resolution=video_request.resolution
                            )
                            generated_videos.append(result.model_dump())
                            break
                        else:
                            print(f"  ⏳ 작업 진행 중... ({attempt + 1}/60) 상태: {status_data['status']}")
                
                except Exception as video_error:
                    print(f"  ❌ 장면 {i} 처리 중 오류: {video_error}")
                    result = VideoGenerationResult(
                        scene_number=i,
                        status="error",
                        error=str(video_error),
                        duration=video_request.duration_per_scene,
                        resolution=video_request.resolution
                    )
                    generated_videos.append(result.model_dump())
    
    except Exception as api_error:
        print(f"⚠️ Runway API 호출 실패: {api_error}")
        raise HTTPException(
            status_code=500,
            detail=f"Runway API 호출 실패: {str(api_error)}"
        )
    
    # 결과 통계 계산
    successful_count = sum(1 for v in generated_videos if v.get('status') == 'success')
    failed_count = len(generated_videos) - successful_count
    success_rate = f"{(successful_count / len(generated_videos)) * 100:.1f}%" if generated_videos else "0%"
    
    # 5단계 결과를 current_project에 저장
    current_project["generated_videos"] = generated_videos
    print(f"✅ 5단계 결과를 current_project에 저장했습니다. ({successful_count}개 성공)")
    
    return {
        "step": "5단계_비디오_생성",
        "success": True,
        "message": "이미지 → 비디오 변환이 완료되었습니다.",
        "generated_videos": generated_videos,
        "summary": {
            "total_scenes": len(generated_videos),
            "successful": successful_count,
            "failed": failed_count,
            "success_rate": success_rate
        }
    }

# 5.5단계: BGM 생성 (6단계 전에 BGM 준비)
@app.post("/bgm/generate-and-wait")
async def generate_bgm_and_wait(
    keyword: str = "happy",
    duration: int = 70,
    max_wait_minutes: int = 5
):
    """
    SUNO API를 사용한 BGM 생성 및 자동 대기 (파일까지 완전히 생성)
    """
    try:
        print(f"🎵 SUNO BGM 자동 생성 시작: 키워드='{keyword}', 길이={duration}초")
        
        if not os.getenv('SUNO_API_KEY'):
            raise HTTPException(status_code=500, detail="SUNO_API_KEY가 설정되지 않았습니다.")
        
        # 1단계: SUNO BGM 생성 요청
        task_id = await generate_suno_bgm(keyword, duration)
        print(f"✅ BGM 생성 요청 완료: task_id = {task_id}")
        
        # 2단계: 최대 max_wait_minutes분간 대기하며 상태 확인
        max_attempts = max_wait_minutes * 4  # 15초마다 체크
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            print(f"🔄 [{attempt}/{max_attempts}] BGM 생성 상태 확인 중... ({attempt * 15}초 경과)")
            
            try:
                result = await check_suno_task_and_download(task_id)
                
                if result["success"]:
                    print(f"🎉 BGM 생성 및 다운로드 완료!")
                    print(f"📁 파일 위치: {result['bgm_path']}")
                    
                    return {
                        "success": True,
                        "message": f"BGM 생성 및 다운로드 완료! ({attempt * 15}초 소요)",
                        "task_id": task_id,
                        "bgm_file": result["bgm_filename"],
                        "bgm_url": f"http://localhost:8001/static/audio/{result['bgm_filename']}",
                        "duration": result["duration"],
                        "title": result["title"],
                        "tags": result["tags"],
                        "file_path": result["bgm_path"],
                        "total_wait_time": f"{attempt * 15}초"
                    }
                else:
                    print(f"   ⏳ 아직 생성 중... (상태: {result.get('status', 'unknown')})")
                    
            except Exception as e:
                print(f"   ⚠️ 상태 확인 중 오류: {e}")
            
            # 15초 대기
            if attempt < max_attempts:
                await asyncio.sleep(15)
        
        # 시간 초과
        return {
            "success": False,
            "message": f"BGM 생성 시간 초과 ({max_wait_minutes}분). 수동으로 /bgm/status/{task_id} 를 확인해주세요.",
            "task_id": task_id,
            "status_check_url": f"/bgm/status/{task_id}",
            "retry_after": 30
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ BGM 자동 생성 오류: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"BGM 자동 생성 중 오류 발생: {str(e)}"
        )

@app.post("/video/merge-with-transitions")
async def merge_videos_with_transitions(
    enable_bgm: bool = True,        # BGM 포함 여부
    bgm_volume: float = 0.4,        # BGM 볼륨 (0.1-1.0)
    transition_duration: float = 1.0  # 트랜지션 시간 (초)
):
    """
    6단계: 5단계에서 생성된 영상들을 랜덤 트랜지션으로 합치기 (BGM 선택 가능)
    """
    
    # 처리 상태 초기화
    video_processing_status.update({
        "is_processing": True,
        "current_step": "6단계: 비디오 합치기 준비 중",
        "progress": 0,
        "total_steps": 100,
        "current_file": "",
        "start_time": time.time(),
        "estimated_completion": None
    })
    
    try:
        # 예시 영상 URL들 (5단계 영상이 없을 때 사용) - 빈 리스트로 초기화
        example_video_urls = []
        
        # 상태 업데이트: 영상 확인 중
        video_processing_status.update({
            "current_step": "6단계: 생성된 영상 확인 중",
            "progress": 10
        })
        
        # video_server.py의 현재 프로젝트 상태에서 생성된 영상 정보 가져오기
        video_urls = []
        use_example_videos = False
        
        if not current_project.get("generated_videos"):
            print("❌ 5단계에서 생성된 영상이 없습니다.")
            raise HTTPException(
                status_code=400, 
                detail="트랜지션 영상을 만들 수 없습니다. 먼저 5단계에서 영상을 생성하세요."
            )
        else:
            print("📋 6단계: 5단계에서 생성된 영상들을 확인합니다...")
            
            # 생성된 영상 URL들 추출
            generated_videos = current_project["generated_videos"]
            
            # 성공적으로 생성된 영상 URL들만 추출
            for video in generated_videos:
                if video.get("status") == "success" and video.get("video_url"):
                    video_urls.append(video["video_url"])
            
            if not video_urls:
                print("❌ 5단계에서 생성된 유효한 영상이 없습니다.")
                raise HTTPException(
                    status_code=400, 
                    detail="트랜지션 영상을 만들 수 없습니다. 5단계에서 영상을 다시 생성하세요."
                )
        
        # 상태 업데이트: 병합 준비
        video_processing_status.update({
            "current_step": "6단계: 비디오 병합 준비 중",
            "progress": 20
        })
        
        # 영상이 있는지 최종 확인
        if not video_urls:
            raise ValueError("병합할 영상이 없습니다. 5단계에서 영상을 먼저 생성하세요.")
        
        if use_example_videos:
            print(f"🎬 예시 영상 {len(video_urls)}개를 랜덤 트랜지션으로 합칩니다...")
        else:
            print(f"🎬 총 {len(video_urls)}개 실제 생성 영상을 랜덤 트랜지션으로 합칩니다...")
            
            # 실제 영상 URL들 출력
            for i, url in enumerate(video_urls, 1):
                print(f"   영상 {i}: {url}")
        
        # 상태 업데이트: 병합 시작
        video_processing_status.update({
            "current_step": "6단계: 비디오 다운로드 및 병합 중",
            "progress": 30,
            "current_file": f"{len(video_urls)}개 비디오 처리 중"
        })
        
        # SUNO BGM 파일 찾기 - request.enable_bgm에 따라 선택적 처리
        selected_bgm_file = None
        bgm_audio_dir = "static/audio"
        
        if enable_bgm:  # BGM이 활성화된 경우에만 BGM 파일 검색
            try:
                if os.path.exists(bgm_audio_dir):
                    # SUNO API로 생성된 BGM 파일만 찾기 (suno_bgm_ 접두사)
                    suno_bgm_files = [f for f in os.listdir(bgm_audio_dir) 
                                     if f.startswith('suno_bgm_') and f.endswith('.mp3')]
                    if suno_bgm_files:
                        # 가장 최근에 생성된 SUNO BGM 파일 사용
                        suno_bgm_files.sort(key=lambda x: os.path.getctime(os.path.join(bgm_audio_dir, x)), reverse=True)
                        selected_bgm_file = os.path.join(bgm_audio_dir, suno_bgm_files[0])
                        print(f"✅ SUNO BGM 파일 발견: {suno_bgm_files[0]} (BGM과 함께 합칠 예정)")
                    else:
                        print("ℹ️ SUNO BGM 파일이 없습니다. BGM 없이 트랜지션만 적용합니다.")
                else:
                    print("ℹ️ BGM 디렉토리가 없습니다. BGM 없이 트랜지션만 적용합니다.")
            except Exception as e:
                print(f"⚠️ BGM 검색 중 에러 발생: {e}. BGM 없이 진행합니다.")
                selected_bgm_file = None
        else:
            print("🔇 BGM이 비활성화되었습니다. BGM 없이 트랜지션만 적용합니다.")
            selected_bgm_file = None
        
        # 실제 영상 URL들을 사용한 트랜지션 합치기
        merger = create_merger_instance(use_static_dir=True, enable_bgm=False)  # BGM 처리는 별도로
        
        # BGM 여부에 따라 파일명 결정
        if selected_bgm_file:
            output_filename = generate_output_filename("merged_ai_videos_with_bgm")
        else:
            output_filename = generate_output_filename("merged_ai_videos")
        
        # 최종 비디오 경로 초기화
        final_video_path = None
        
        video_source = "예시 영상" if use_example_videos else "실제 생성된 영상"
        bgm_status = f"SUNO BGM 포함 (볼륨: {int(bgm_volume*100)}%)" if selected_bgm_file else "BGM 없음 (트랜지션만)"
        print(f"🚀 {video_source} URL들로 트랜지션 합치기 시작... ({bgm_status})")
        
        # 먼저 트랜지션 비디오 생성 (BGM 옵션 포함)
        print(f"🎬 트랜지션 효과로 비디오 합치는 중...")
        video_processing_status.update({
            "current_step": f"6단계: 트랜지션 효과 적용 중 ({bgm_status})",
            "progress": 50,
            "current_file": f"트랜지션: {len(video_urls)}개 영상"
        })
        
        temp_video_path = merger.merge_videos_with_frame_transitions(
            video_urls,
            output_filename,
            bgm_file=selected_bgm_file,  # BGM을 매개변수로 전달
            bgm_volume=bgm_volume  # BGM 볼륨도 전달
        )
        
        print(f"✅ 비디오 합치기 완료!")
        
        # 최종 비디오 경로 설정
        final_video_path = temp_video_path
        
        video_url = merger.get_video_url(output_filename)
        
        # 상태 업데이트: 후처리
        video_processing_status.update({
            "current_step": "6단계: 파일 저장 및 후처리 중",
            "progress": 90,
            "current_file": output_filename
        })
        
        print(f"🎉 6단계 완료: 영상이 성공적으로 합쳐졌습니다!")
        print(f"📱 브라우저에서 확인: {video_url}")
        
        # 6단계 완료 후 트랜지션 영상 로그를 TXT 파일로 저장
        print(f"📝 6단계 완료된 트랜지션 영상 로그 저장 중...")
        transition_video_log_file = "transition_video_log.txt"
        try:
            if final_video_path:
                if os.path.isabs(final_video_path):
                    actual_video_path = final_video_path
                else:
                    actual_video_path = os.path.abspath(final_video_path)
            else:
                actual_video_path = os.path.abspath(os.path.join("static", "videos", output_filename))
            
            with open(transition_video_log_file, 'w', encoding='utf-8') as f:
                f.write(f"TRANSITION_VIDEO:{actual_video_path}\n")
                f.write(f"CREATED_TIME:{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"SOURCE_VIDEOS:{len(video_urls)}\n")
                f.write(f"BGM_ENABLED:{enable_bgm}\n")
                if selected_bgm_file:
                    f.write(f"BGM_FILE:{selected_bgm_file}\n")
                    f.write(f"BGM_VOLUME:{bgm_volume}\n")
                f.write(f"OUTPUT_FILENAME:{output_filename}\n")
                f.write(f"VIDEO_URL:{video_url}\n")
                f.write("SOURCE_VIDEO_URLS:\n")
                for i, url in enumerate(video_urls, 1):
                    f.write(f"  {i}: {url}\n")
                f.write("---\n")
            
            print(f"✅ 6단계 트랜지션 영상 로그 저장 성공!")
            print(f"   파일 위치: {os.path.abspath(transition_video_log_file)}")
            print(f"   저장된 영상: {actual_video_path}")
            print(f"   소스 영상 수: {len(video_urls)}개")
            
            # 기존 merged_video_list.txt도 유지 (호환성을 위해)
            merged_video_list_file = "merged_video_list.txt"
            with open(merged_video_list_file, 'w', encoding='utf-8') as f:
                f.write(actual_video_path + '\n')
            
        except Exception as e:
            print(f"❌ 6단계 트랜지션 영상 로그 저장 실패: {e}")
        
        # 상태 업데이트: 완료
        video_processing_status.update({
            "is_processing": False,
            "current_step": "6단계: 완료",
            "progress": 100,
            "current_file": output_filename
        })
        
        return {
            "step": f"6단계_영상_{'BGM포함_' if selected_bgm_file else 'BGM없음_'}합치기",
            "status": "success",
            "message": f"{video_source}이 {'BGM과 함께 (볼륨: ' + str(int(bgm_volume*100)) + '%)' if selected_bgm_file else 'BGM 없이'} 성공적으로 합쳐졌습니다.",
            "video_source": video_source,
            "input_videos": len(video_urls),
            "bgm_settings": {
                "enabled": enable_bgm,
                "included": bool(selected_bgm_file),
                "volume_percent": int(bgm_volume*100) if selected_bgm_file else 0,
                "file": os.path.basename(selected_bgm_file) if selected_bgm_file else None
            },
            "transition_settings": {
                "duration": transition_duration
            },
            "output_file": output_filename,
            "url": video_url,
            "duration": "estimated_duration",
            "workflow_complete": True,
            "used_example_videos": use_example_videos
        }
        
    except Exception as e:
        # 에러 발생 시 상태 초기화
        video_processing_status.update({
            "is_processing": False,
            "current_step": f"6단계: 오류 발생 - {str(e)}",
            "progress": 0,
            "current_file": ""
        })
        
        print(f"❌ 6단계 비디오 병합 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"비디오 병합 실패: {str(e)}")

# 커스텀 자막 엔드포인트
@app.post("/video/merge-with-custom-subtitles")
async def merge_video_with_custom_subtitles(
    position: str = "bottom",           # 포지션
    font_size: int = 2,                 # 폰트 사이즈
    font_name: str = "Malgun Gothic",   # 폰트 이름
    font_color: str = "&Hffffff",       # 폰트색
    scale: int = 30,                    # 비율 (x, y 통합)
    outline_color: str = "&H000000",    # 아웃라인 색
    outline_width: int = 2,             # 아웃라인 굵기
    enable_bold: bool = True            # 볼드
):
    """
    커스텀 자막 적용: SRT 파일과 폰트 설정으로 자막 커스터마이징
    - 기존 비디오에 사용자 지정 SRT 파일과 폰트 설정 적용
    - 폰트 크기, 색상, 위치, 스케일 등 세부 조정 가능
    """
    try:
        print(f"🎨 커스텀 자막 적용 시작...")
        
        if not SUBTITLE_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail="자막 모듈이 사용할 수 없습니다."
            )
        
        # 필수 파일들 사전 검증
        tts_file_list_file = "tts_file_list.txt"
        if not os.path.exists(tts_file_list_file) or os.path.getsize(tts_file_list_file) == 0:
            raise HTTPException(
                status_code=400,
                detail="TTS 파일 목록이 없거나 비어있습니다. 먼저 7단계 TTS 생성을 완료해주세요."
            )
        
        transition_video_log_file = "transition_video_log.txt"
        if not os.path.exists(transition_video_log_file) or os.path.getsize(transition_video_log_file) == 0:
            raise HTTPException(
                status_code=400,
                detail="트랜지션 영상 로그가 없거나 비어있습니다. 먼저 6단계 트랜지션 영상 생성을 완료해주세요."
            )
        
        print(f"✅ 필수 파일 검증 완료 - TTS 목록과 트랜지션 로그 존재")
        
        # 1. 트랜지션 영상 로그에서 비디오 파일 찾기 (우선)
        transition_video_log_file = "transition_video_log.txt"
        video_file_path = None
        
        if os.path.exists(transition_video_log_file):
            try:
                with open(transition_video_log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    
                # 로그에서 트랜지션 영상 경로 추출
                for line in log_content.split('\n'):
                    if line.startswith('TRANSITION_VIDEO:'):
                        transition_video_path = line.split(':', 1)[1].strip()
                        if os.path.exists(transition_video_path):
                            video_file_path = transition_video_path
                            print(f"✅ 트랜지션 영상 로그에서 비디오 사용: {os.path.basename(video_file_path)}")
                            break
                            
            except Exception as e:
                print(f"⚠️ 트랜지션 영상 로그 읽기 실패: {e}")
        
        # 트랜지션 로그에서 찾지 못한 경우 기존 방식으로 폴백
        if not video_file_path:
            video_dir = "static/videos"
            video_files = []
            
            if os.path.exists(video_dir):
                for file in os.listdir(video_dir):
                    if file.endswith(".mp4") and not file.startswith("custom_subtitle_"):
                        video_path = os.path.join(video_dir, file)
                        video_files.append((video_path, os.path.getmtime(video_path)))
            
            if not video_files:
                raise HTTPException(
                    status_code=404,
                    detail="비디오 파일을 찾을 수 없습니다. 먼저 트랜지션 비디오를 생성하세요."
                )
            
            # 가장 최근 파일 선택
            video_files.sort(key=lambda x: x[1], reverse=True)
            video_file_path = video_files[0][0]
            print(f"✅ 최근 비디오 파일 사용 (폴백): {os.path.basename(video_file_path)}")
        
        print(f"📹 사용할 비디오: {os.path.basename(video_file_path)}")
        
        # video_dir 변수 정의 (TTS 파일 검색을 위해)
        video_dir = "static/videos"
        
        # 2. SRT 파일 처리 (자동 TTS 파일에서 생성)
        subtitle_file_path = None
        # 자동 생성된 SRT 파일 찾기
        from subtitle_utils import transcribe_audio_with_whisper, create_sequential_subtitle_file
        
        # TTS 파일 찾기
        tts_files = []
        for file in os.listdir(video_dir):
            if file.startswith("combined_tts_") and file.endswith(".mp3"):
                tts_path = os.path.join(video_dir, file)
                tts_files.append((tts_path, os.path.getmtime(tts_path)))
        
        if not tts_files:
            raise HTTPException(
                status_code=404,
                detail="TTS 파일을 찾을 수 없습니다. 먼저 TTS를 생성하세요."
            )
        
        # 가장 최근 TTS 파일 사용
        tts_files.sort(key=lambda x: x[1], reverse=True)
        combined_tts_path = tts_files[0][0]
        print(f"🎙️ 사용할 TTS: {os.path.basename(combined_tts_path)}")
        
        # Whisper로 자막 생성
        subtitle_result = await transcribe_audio_with_whisper(
            audio_file_path=combined_tts_path,
            language="ko",
            output_format="srt"
        )
        
        if not subtitle_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"자막 생성 실패: {subtitle_result.error}"
            )
        
        # 순차적 자막 파일 생성
        sequential_subtitle_path = subtitle_result.subtitle_file_path.replace('.srt', '_custom.srt')
        subtitle_file_path = create_sequential_subtitle_file(
            subtitle_result.subtitle_file_path,
            sequential_subtitle_path,
            max_chars=15,
            line_duration=2.0,
            gap_duration=0.5,
            words_per_line=5
        )
        print(f"✅ 자막 생성 완료: {os.path.basename(subtitle_file_path)}")
        
        # 자막 생성 완료 후 txt 파일들과 srt 파일들 정리
        print(f"🧹 커스텀 자막 생성 완료 - 파일들 정리 중...")
        txt_files_to_clean = [
            "tts_file_list.txt",
            "merged_video_list.txt",
            "transition_video_log.txt",  # 트랜지션 로그도 정리
            "subtitle_file_list.txt"     # 자막 파일 리스트도 정리
        ]
        
        # SRT 파일들도 정리 (static/videos 디렉토리에서)
        video_dir = "static/videos"
        srt_files_to_clean = []
        if os.path.exists(video_dir):
            for file in os.listdir(video_dir):
                if file.endswith(".srt"):
                    srt_files_to_clean.append(os.path.join(video_dir, file))
        
        # TXT 파일들 정리
        for txt_file in txt_files_to_clean:
            if os.path.exists(txt_file):
                try:
                    with open(txt_file, 'w', encoding='utf-8') as f:
                        f.write("")  # 파일 내용 비우기
                    print(f"   ✅ {txt_file} 내용 정리 완료")
                except Exception as e:
                    print(f"   ⚠️ {txt_file} 정리 실패: {e}")
            else:
                print(f"   📋 {txt_file} 파일 없음 (정리 불필요)")
        
        # SRT 파일들 삭제
        for srt_file in srt_files_to_clean:
            if os.path.exists(srt_file):
                try:
                    os.remove(srt_file)
                    print(f"   ✅ {os.path.basename(srt_file)} 삭제 완료")
                except Exception as e:
                    print(f"   ⚠️ {os.path.basename(srt_file)} 삭제 실패: {e}")
            else:
                print(f"   📋 {os.path.basename(srt_file)} 파일 없음 (삭제 불필요)")
        
        # 3. 커스텀 자막 스타일 생성
        def create_custom_subtitle_style():
            # 모든 위치에서 중앙 정렬 사용 (Alignment=2 = 하단 중앙)
            alignment = 2  # 항상 중앙 정렬
            
            # 위치별 여백 설정 (정렬은 항상 중앙)
            if position == "top":
                margin_v_val = 50  # 상단 여백
            elif position == "middle":
                margin_v_val = 0   # 중앙 여백
            elif position == "bottom":
                margin_v_val = 80  # 하단 여백
            else:  # custom - 기본값 사용
                margin_v_val = 80  # 기본 여백
            
            # 고정 여백값 설정
            margin_l_val = 300
            margin_r_val = 300
            
            style_options = [
                f"FontSize={font_size}",
                f"FontName={font_name}",
                f"PrimaryColour={font_color}",
                f"Alignment={alignment}",
                f"MarginV={margin_v_val}",
                f"MarginL={margin_l_val}",
                f"MarginR={margin_r_val}",
                "WrapStyle=0",
                f"ScaleX={scale}",  # 통합된 스케일 사용
                f"ScaleY={scale}",  # 통합된 스케일 사용
                f"Bold={1 if enable_bold else 0}",  # Bold 설정
                "PlayResX=1920",
                "PlayResY=1080",
            ]
            
            # 아웃라인 항상 적용 (enable_outline 제거)
            style_options.extend([
                f"OutlineColour={outline_color}",
                "BorderStyle=1",
                f"Outline={outline_width}",  # 외곽선 두께 설정
                "Shadow=0"
            ])
            
            return ",".join(style_options)
        
        # 4. 최종 비디오 생성 (TTS 오디오 포함)
        output_filename = f"custom_subtitle_video_{int(time.time())}.mp4"
        output_path = os.path.join(video_dir, output_filename)
        
        # FFmpeg 경로 설정
        ffmpeg_path = "ffmpeg"
        
        # 자막 파일 경로를 Windows 호환 형식으로 변환
        subtitle_path_fixed = subtitle_file_path.replace("\\", "/").replace(":", "\\:")
        
        # 커스텀 자막 스타일 적용
        custom_style = create_custom_subtitle_style()
        
        # TTS 파일이 있는지 확인
        tts_files = []
        for file in os.listdir(video_dir):
            if file.startswith("combined_tts_") and file.endswith(".mp3"):
                tts_path = os.path.join(video_dir, file)
                tts_files.append((tts_path, os.path.getmtime(tts_path)))
        
        # TTS 파일이 있으면 오디오와 함께 합치기
        if tts_files:
            # 가장 최근 TTS 파일 사용
            tts_files.sort(key=lambda x: x[1], reverse=True)
            combined_tts_path = tts_files[0][0]
            print(f"🎙️ TTS 오디오 추가: {os.path.basename(combined_tts_path)}")
            
            # subprocess 모듈 import
            import subprocess
            
            # 비디오에 기존 오디오가 있는지 확인
            probe_cmd = [ffmpeg_path, '-i', video_file_path, '-hide_banner', '-f', 'null', '-']
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            has_audio = 'Audio:' in probe_result.stderr
            
            if has_audio:
                # 기존 BGM + TTS 믹싱
                final_cmd = [
                    ffmpeg_path,
                    '-i', video_file_path,  # 입력 비디오 (BGM 포함)
                    '-i', combined_tts_path,  # TTS 오디오
                    '-filter_complex', f"[0:v]subtitles='{subtitle_path_fixed}':force_style='{custom_style}'[v_out]; [0:a]volume=0.4[bg_audio]; [1:a]volume=5.0[tts_audio]; [bg_audio][tts_audio]amix=inputs=2:duration=longest:dropout_transition=0[aout]",
                    '-map', '[v_out]',  # 자막이 포함된 비디오
                    '-map', '[aout]',   # 믹싱된 오디오 (BGM + TTS)
                    '-c:v', 'libx264',  # 비디오 코덱
                    '-c:a', 'aac',      # 오디오 코덱
                    '-preset', 'medium',
                    '-crf', '23',
                    output_path,
                    '-y'
                ]
                print(f"🎵 BGM + TTS 오디오 믹싱 처리")
            else:
                # TTS만 추가
                final_cmd = [
                    ffmpeg_path,
                    '-i', video_file_path,  # 입력 비디오 (오디오 없음)
                    '-i', combined_tts_path,  # TTS 오디오
                    '-filter_complex', f"[0:v]subtitles='{subtitle_path_fixed}':force_style='{custom_style}'[v_out]",
                    '-map', '[v_out]',  # 자막이 포함된 비디오
                    '-map', '1:a',      # TTS 오디오
                    '-c:v', 'libx264',  # 비디오 코덱
                    '-c:a', 'aac',      # 오디오 코덱
                    '-preset', 'medium',
                    '-crf', '23',
                    output_path,
                    '-y'
                ]
                print(f"🎙️ TTS 오디오만 추가")
        else:
            # TTS 파일이 없으면 자막만 추가 (기존 방식)
            final_cmd = [
                ffmpeg_path,
                '-i', video_file_path,  # 입력 비디오
                '-vf', f"subtitles='{subtitle_path_fixed}':force_style='{custom_style}'",  # 커스텀 자막 적용
                '-c:a', 'copy',  # 오디오 복사
                '-c:v', 'libx264',  # 비디오 코덱
                '-preset', 'medium',
                '-crf', '23',
                output_path,
                '-y'
            ]
            print(f"📝 자막만 추가 (TTS 파일 없음)")
        
        print(f"🎬 커스텀 자막 적용 중...")
        print(f"   폰트: {font_name} ({font_size}px)")
        print(f"   스케일: {scale}% x {scale}%")
        print(f"   위치: {position}")
        print(f"   Bold: {enable_bold}")
        print(f"   아웃라인: {outline_color} (굵기: {outline_width})")
        
        import subprocess
        result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            error_msg = f"FFmpeg 처리 실패:\n   반환 코드: {result.returncode}\n   표준 출력: {result.stdout}\n   표준 오류: {result.stderr}"
            print(f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail="커스텀 자막 적용 실패")
        
        # 성공 응답
        file_size = os.path.getsize(output_path)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"✅ 커스텀 자막 비디오 생성 완료!")
        print(f"📁 파일: {output_filename} ({file_size_mb:.2f} MB)")
        
        # 커스텀 자막 비디오 생성 완료 후 모든 파일들 정리
        print(f"🧹 커스텀 자막 비디오 완료 - 모든 파일들 정리 중...")
        txt_files_to_clean = [
            "tts_file_list.txt",
            "merged_video_list.txt",
            "transition_video_log.txt",  # 트랜지션 로그도 정리
            "subtitle_file_list.txt"     # 자막 파일 리스트도 정리
        ]
        
        video_dir = "static/videos"
        srt_files_to_clean = []
        
        # 타임스탬프가 포함된 TTS 리스트 파일들과 SRT 파일들도 정리
        if os.path.exists(video_dir):
            for file in os.listdir(video_dir):
                if file.startswith("tts_list_") and file.endswith(".txt"):
                    txt_files_to_clean.append(os.path.join(video_dir, file))
                elif file.endswith(".srt"):
                    srt_files_to_clean.append(os.path.join(video_dir, file))
        
        # TXT 파일들 정리
        for txt_file in txt_files_to_clean:
            if os.path.exists(txt_file):
                try:
                    with open(txt_file, 'w', encoding='utf-8') as f:
                        f.write("")  # 파일 내용 비우기
                    print(f"   ✅ {os.path.basename(txt_file)} 내용 정리 완료")
                except Exception as e:
                    print(f"   ⚠️ {os.path.basename(txt_file)} 정리 실패: {e}")
            else:
                print(f"   📋 {os.path.basename(txt_file)} 파일 없음 (정리 불필요)")
        
        # SRT 파일들 삭제
        for srt_file in srt_files_to_clean:
            if os.path.exists(srt_file):
                try:
                    os.remove(srt_file)
                    print(f"   ✅ {os.path.basename(srt_file)} 삭제 완료")
                except Exception as e:
                    print(f"   ⚠️ {os.path.basename(srt_file)} 삭제 실패: {e}")
            else:
                print(f"   📋 {os.path.basename(srt_file)} 파일 없음 (삭제 불필요)")
        
        return {
            "step": "커스텀_자막_적용",
            "success": True,
            "message": "커스텀 자막이 성공적으로 적용되었습니다.",
            "output_file": f"static/videos/{output_filename}",
            "video_url": f"http://localhost:8001/static/videos/{output_filename}",
            "file_size_mb": round(file_size_mb, 2),
            "subtitle_settings": {
                "font_name": font_name,
                "font_size": font_size,
                "font_color": font_color,
                "scale": scale,
                "position": position,
                "enable_bold": enable_bold,
                "outline_color": outline_color,
                "outline_width": outline_width,
                "srt_file": os.path.basename(subtitle_file_path) if subtitle_file_path else "자동생성"
            }
        }
        
    except Exception as e:
        error_msg = f"커스텀 자막 적용 실패: {e}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/bgm/status/{task_id}")
async def check_bgm_status(task_id: str):
    """
    SUNO BGM 생성 상태 확인 및 다운로드
    """
    try:
        print(f"🔍 SUNO BGM 상태 확인: {task_id}")
        
        if not os.getenv('SUNO_API_KEY'):
            raise HTTPException(status_code=500, detail="SUNO_API_KEY가 설정되지 않았습니다.")
        
        # 태스크 상태 확인 및 다운로드
        result = await check_suno_task_and_download(task_id)
        
        if result["success"]:
            return {
                "success": True,
                "status": "completed",
                "message": "BGM 생성 완료 및 다운로드 성공",
                "task_id": task_id,
                "bgm_file": result["bgm_filename"],
                "bgm_url": f"http://localhost:8001/static/audio/{result['bgm_filename']}",
                "duration": result["duration"],
                "title": result["title"],
                "tags": result["tags"],
                "file_path": result["bgm_path"]
            }
        else:
            return {
                "success": False,
                "status": result.get("status", "processing"),
                "message": result.get("message", "BGM 생성 중입니다..."),
                "task_id": task_id,
                "retry_after": 30
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ BGM 상태 확인 오류: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"BGM 상태 확인 중 오류 발생: {str(e)}"
        )

def start_video_server():
    """비디오 서버 시작 함수"""
    print("🚀 비디오 서버를 시작합니다...")
    
    # 서버 시작 시 기존 작업 파일들 정리
    print("🧹 서버 시작 - 기존 작업 파일들 정리 중...")
    cleanup_files = [
        "tts_file_list.txt",
        "merged_video_list.txt", 
        "transition_video_log.txt",
        "subtitle_file_list.txt"
    ]
    
    for cleanup_file in cleanup_files:
        if os.path.exists(cleanup_file):
            try:
                with open(cleanup_file, 'w', encoding='utf-8') as f:
                    f.write("")  # 파일 내용 비우기
                print(f"   ✅ {cleanup_file} 정리 완료")
            except Exception as e:
                print(f"   ⚠️ {cleanup_file} 정리 실패: {e}")
        else:
            print(f"   📋 {cleanup_file} 파일 없음")
    
    # SRT 파일들도 정리
    video_dir = "static/videos"
    if os.path.exists(video_dir):
        srt_count = 0
        for file in os.listdir(video_dir):
            if file.endswith(".srt"):
                try:
                    os.remove(os.path.join(video_dir, file))
                    srt_count += 1
                except Exception as e:
                    print(f"   ⚠️ {file} 삭제 실패: {e}")
        if srt_count > 0:
            print(f"   ✅ SRT 파일 {srt_count}개 정리 완료")
        else:
            print(f"   📋 정리할 SRT 파일 없음")
    
    print("📡 서버 정보:")
    print("   - 호스트: 0.0.0.0")
    print("   - 포트: 8004")
    print("   - 모드: 프로덕션")
    print("📱 브라우저에서 http://localhost:8004/video/status 에 접속하여 상태를 확인하세요.")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    start_video_server()
