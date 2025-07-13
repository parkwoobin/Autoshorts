"""
간소화된 비디오 서버: 트랜지션 및 비디오 합치기 전용
기존 client.py 서버에 비디오 합치기 기능만 추가
"""
import uvicorn  # ASGI 서버 (FastAPI 실행용)
import os  # 운영체제 기능 (파일 경로 등)
import httpx  # HTTP 클라이언트 (비동기 요청용)
from fastapi import FastAPI, HTTPException  # 웹 프레임워크와 예외 처리
from fastapi.staticfiles import StaticFiles  # 정적 파일 서빙용 (CSS, JS, 이미지 등)
from fastapi.responses import HTMLResponse
from typing import List  # 타입 힌트용 (리스트 타입 명시)

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()  # .env 파일 로드

print("🔑 환경변수 로드 완료")
print(f"   ELEVENLABS_API_KEY: {'✅ 설정됨' if os.getenv('ELEVENLABS_API_KEY') else '❌ 없음'}")
print(f"   OPENAI_API_KEY: {'✅ 설정됨' if os.getenv('OPENAI_API_KEY') else '❌ 없음'}")
print(f"   RUNWAY_API_KEY: {'✅ 설정됨' if os.getenv('RUNWAY_API_KEY') else '❌ 없음'}")

# 비디오 서버 유틸리티 함수들 import
from video_server_utils import (
    SAMPLE_VIDEO_URLS,  # 테스트용 샘플 영상 URL들
    create_merger_instance,  # 영상 합치기 객체 생성 함수
    generate_output_filename,  # 타임스탬프 포함 파일명 생성 함수
    create_video_response,  # API 응답 객체 생성 함수
    get_transition_description  # 트랜지션 설명 반환 함수
)
from video_models import VideoMergeRequest, VideoConfig  # 데이터 모델 클래스들
from tts_utils import create_tts_audio, create_multiple_tts_audio, get_elevenlabs_api_key  # TTS 유틸리티
from subtitle_utils import generate_subtitles_with_whisper, merge_video_with_subtitles  # 자막 유틸리티

# 독립적인 FastAPI app 생성 (테스트용)
app = FastAPI(title="Video Server", description="비디오 생성 및 합치기 서버")

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

def check_environment_variables():
    """필수 환경변수 체크"""
    required_vars = {
        "ELEVENLABS_API_KEY": "ElevenLabs TTS 서비스용",
        "OPENAI_API_KEY": "OpenAI LLM 서비스용", 
        "RUNWAY_API_KEY": "Runway 비디오 생성용"
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

def add_video_features_to_server():
    """기존 client.py 서버에 비디오 합치기 기능 추가"""
    try:
        # 기존 client.py의 FastAPI app 객체를 import
        from client import app  # client.py에서 생성된 FastAPI 인스턴스 가져오기
        
        # 정적 파일 서빙 설정 (HTML, CSS, JS, 영상 파일 등을 웹에서 접근 가능하게 함)
        app.mount("/static", StaticFiles(directory="static"), name="static")  # /static 경로로 static 폴더 내용 서빙
        
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

        print("🎬 비디오 합치기 및 트랜지션 기능을 추가합니다...")  # 기능 추가 시작 알림
        print("📁 정적 파일 서빙 활성화: /static")  # 정적 파일 서빙 활성화 알림

        # === 비디오 상태 확인 API 엔드포인트 ===
        @app.get("/video/status")  # GET 요청으로 /video/status 경로에 접근 시 실행
        async def get_video_status():  # 비동기 함수로 비디오 기능 상태 확인
            """비디오 기능 상태 확인"""
            return {  # JSON 형태로 상태 정보 반환
                "status": "active",  # 현재 상태: 활성화됨
                "message": "비디오 합치기 및 트랜지션 기능이 활성화되었습니다.",  # 상태 메시지
                "available_endpoints": {  # 사용 가능한 API 엔드포인트 목록
                    "GET /video/status": "현재 페이지 - 비디오 기능 상태 확인",  # 상태 확인 API
                    "POST /video/generate-videos": "5단계: 4단계 이미지들 → Runway API 비디오 생성",  # AI 비디오 생성 API
                    "POST /video/merge-with-transitions": "6단계: 생성된 비디오들을 랜덤 트랜지션으로 합치기",  # 생성된 비디오 합치기 API
                    "POST /video/create-tts-from-storyboard": "7단계: 스토리보드 기반 TTS 내레이션 생성",  # TTS 생성 API
                    "POST /video/generate-subtitles": "8-1단계: TTS 오디오에서 자막 파일(.srt) 생성",  # 자막 생성 API
                    "POST /video/merge-with-tts-subtitles": "8-2단계: 비디오 + TTS + 자막 완전 합치기",  # TTS와 자막 포함 완전 합치기
                    "POST /video/merge-custom": "사용자 비디오 URL로 합치기",  # 사용자 비디오 합치기 API
                    "POST /video/create-complete": "🆕 완전한 비디오 제작: 스토리보드 → 비디오 → TTS → 자막",  # 완전한 워크플로우 API
                    "POST /video/create-simple-tts": "� 간단한 텍스트 TTS 생성"  # 간단한 TTS 생성
                },
                "features": [  # 제공하는 주요 기능 목록
                    "🎬 9가지 트랜지션 효과 (랜덤 선택)",  # 다양한 트랜지션 효과
                    "🚀 스트리밍 방식 처리 (다운로드 없음)",  # 스트리밍 처리
                    "📱 브라우저에서 바로 재생 가능",  # 웹 브라우저 호환성
                    "🎨 Frame-level animation 지원",  # 프레임 단위 애니메이션
                    "🤖 AI 워크플로우 연동 (1-6단계)",  # AI 워크플로우 통합
                    "🎥 Runway API 비디오 생성 (이미지 → 비디오)",  # Runway API 연동
                    "🎙️ ElevenLabs TTS 음성 생성",  # TTS 음성 생성
                    "📝 Whisper 자동 자막 생성",  # 자막 생성
                    "🎵 스토리보드 기반 내레이션 추가",  # 스토리보드 내레이션
                    "🧠 OpenAI LLM 기반 TTS 스크립트 자동 생성",  # LLM 기반 스크립트 생성
                    "🔧 0.1초 정밀도 Whisper AI 자막",  # 정밀 자막
                    "🎤 간단한 텍스트 → TTS 변환"  # 간단한 TTS
                ]
            }

        # ==================================================================================
        # 5단계: 스토리보드 이미지들로 개별 비디오 생성 (Runway API)
        # ==================================================================================
        @app.post("/video/generate-videos")  # POST 요청으로 /video/generate-videos 경로에 접근 시 실행
        async def generate_videos():  # 비동기 함수로 AI 영상 생성 처리
            """5단계: 4단계에서 생성된 이미지들을 비디오로 변환"""
            
            # client.py의 current_project에서 4단계 이미지들 가져오기
            try:
                from client import current_project
                
                if not current_project.get("images"):
                    raise HTTPException(
                        status_code=400,
                        detail="4단계에서 생성된 이미지가 없습니다. 먼저 4단계를 완료해주세요."
                    )
                
                # 4단계에서 생성된 이미지 URL들 추출
                image_data_list = current_project["images"]
                image_urls = []
                
                print(f"🔧 current_project['images'] 내용: {len(image_data_list)}개")
                print(f"🔧 이미지 데이터 타입: {type(image_data_list)}")
                
                for i, img_data in enumerate(image_data_list):
                    print(f"🔧 이미지 {i+1} 데이터: {type(img_data)} - {str(img_data)[:100]}...")
                    
                    # 다양한 형태의 이미지 데이터 처리
                    if isinstance(img_data, dict):
                        # dict 형태: {"url": "...", "status": "success", ...}
                        if img_data.get("url"):
                            image_urls.append(img_data["url"])
                        elif img_data.get("image_url"):
                            image_urls.append(img_data["image_url"])
                        elif img_data.get("generated_image_url"):
                            image_urls.append(img_data["generated_image_url"])
                    elif isinstance(img_data, str):
                        # string 형태: 직접 URL
                        image_urls.append(img_data)
                
                if not image_urls:
                    print(f"❌ 추출된 URL이 없습니다. 원본 데이터:")
                    for i, img_data in enumerate(image_data_list):
                        print(f"   데이터 {i+1}: {img_data}")
                    raise HTTPException(
                        status_code=400,
                        detail="4단계 이미지 데이터에서 유효한 URL을 찾을 수 없습니다."
                    )
                
                print(f"✅ 4단계에서 가져온 이미지: {len(image_urls)}개")
                for i, url in enumerate(image_urls, 1):
                    print(f"   이미지 {i}: {url[:80]}...")
                
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="client.py를 찾을 수 없습니다. 워크플로우를 먼저 실행해주세요."
                )
            
            print("🎬 5단계: 4단계 이미지들 → 비디오 변환 시작...")
            print(f"🖼️ 총 {len(image_urls)}개의 이미지를 비디오로 변환합니다...")
            
            # video_models.py 설정 사용
            from video_models import ImageToVideoRequest, VideoGenerationResult, VideoConfig
            
            # 비디오 생성 설정
            video_request = ImageToVideoRequest(
                image_urls=image_urls,
                duration_per_scene=5,  # 5초
                resolution="720:1280",  # 세로형
                model="gen4_turbo"  # 이미지→비디오 모델
            )
            
            print(f"🎬 Runway API 설정 (video_models.py 기반):")
            print(f"   - 모델: {video_request.model}")
            print(f"   - 해상도: {video_request.resolution}")
            print(f"   - 장면당 길이: {video_request.duration_per_scene}초")
            
            # Runway API를 통한 이미지 → 동영상 변환
            generated_videos = []  # 결과 저장용 리스트 초기화
            
            try:
                import asyncio
                
                # API 인증 설정
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
                        
                        # 이미지 → 동영상 변환 페이로드 (video_models.py 설정 활용)
                        payload = {
                            "model": video_request.model,
                            "promptImage": image_url,  # 소스 이미지 URL
                            "duration": video_request.duration_per_scene,
                            "ratio": video_request.resolution,
                            "seed": 42  # 고정 시드값
                        }
                        
                        try:
                            # 1. 동영상 생성 작업 요청
                            print(f"📤 Runway API 요청: 이미지 → 동영상 변환...")
                            response = await client.post(f"{base_url}/image_to_video", headers=headers, json=payload)
                            
                            if response.status_code != 200:
                                raise Exception(f"API 요청 실패: {response.text}")
                            
                            task_id = response.json()["id"]
                            print(f"  -> 작업 ID: {task_id}")

                            # 2. 작업 완료까지 폴링
                            for attempt in range(60):  # 최대 5분 대기
                                await asyncio.sleep(5)  # 5초 대기
                                
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
            try:
                from client import current_project
                current_project["generated_videos"] = generated_videos
                print(f"✅ 5단계 결과를 current_project에 저장했습니다. ({successful_count}개 성공)")
            except Exception as save_error:
                print(f"⚠️ current_project 저장 실패: {save_error}")
            
            return {
                "message": "이미지 → 비디오 변환이 완료되었습니다.",
                "generated_videos": generated_videos,
                "summary": {
                    "total_scenes": len(generated_videos),
                    "successful": successful_count,
                    "failed": failed_count,
                    "success_rate": success_rate
                }
            }

        # ==================================================================================
        # 6단계: 트랜지션 적용 영상 합치기 (개별 영상 생성 후)
        # ==================================================================================
        @app.post("/video/merge-with-transitions")  # POST 요청으로 /video/merge-with-transitions 경로에 접근 시 실행
        async def merge_videos_with_transitions():  # 비동기 함수로 영상 합치기 처리
            """6단계: 5단계에서 생성된 영상들을 랜덤 트랜지션으로 합치기"""
            
            # client.py의 현재 프로젝트 상태에서 생성된 영상 정보 가져오기
            try:
                from client import current_project  # client.py에서 관리하는 프로젝트 상태 import
                
                if not current_project.get("generated_videos"):  # 생성된 영상이 없으면 에러
                    raise HTTPException(  # HTTP 400 에러 발생
                        status_code=400,  # 잘못된 요청 상태 코드
                        detail="먼저 5단계(/video/generate-videos)를 완료하여 영상을 생성해주세요."  # 에러 메시지
                    )
                
                print("📋 6단계: 5단계에서 생성된 영상들을 확인합니다...")  # 작업 시작 알림
                
                # 생성된 영상 URL들 추출
                generated_videos = current_project["generated_videos"]  # 5단계에서 생성된 영상 리스트 가져오기
                video_urls = []  # 실제 영상 URL들을 저장할 리스트
                
                # 성공적으로 생성된 영상 URL들만 추출
                for video in generated_videos:
                    if video.get("status") == "success" and video.get("video_url"):
                        video_urls.append(video["video_url"])
                
                if not video_urls:
                    raise HTTPException(
                        status_code=400,
                        detail="생성된 영상이 없습니다. 5단계에서 영상 생성이 실패했을 수 있습니다."
                    )
                
                print(f"🎬 총 {len(video_urls)}개 실제 생성 영상을 랜덤 트랜지션으로 합칩니다...")  # 합칠 영상 개수 출력
                
                # 실제 영상 URL들 출력
                for i, url in enumerate(video_urls, 1):
                    print(f"   영상 {i}: {url}")
                
                # 실제 영상 URL들을 사용한 트랜지션 합치기
                merger = create_merger_instance(use_static_dir=True)  # 영상 합치기 객체 생성 (static 디렉토리 사용)
                output_filename = generate_output_filename("merged_ai_videos")  # 타임스탬프 포함 출력 파일명 생성
                
                print("🚀 실제 생성된 영상 URL들로 트랜지션 합치기 시작...")
                final_video_path = merger.merge_videos_with_frame_transitions(  # 프레임 단위 트랜지션으로 영상 합치기 실행
                    video_urls,  # 실제 생성된 영상 URL 리스트
                    output_filename  # 출력 파일명
                )
                video_url = merger.get_video_url(output_filename)  # 웹에서 접근 가능한 URL 생성
                
                print(f"🎉 6단계 완료: 영상이 성공적으로 합쳐졌습니다!")  # 완료 메시지
                print(f"📱 브라우저에서 확인: {video_url}")  # 접근 URL 출력
                
                return {  # API 응답 반환
                    "step": "6단계_영상_합치기",  # 현재 단계
                    "status": "success",  # 처리 상태: 성공
                    "message": "영상이 랜덤 트랜지션으로 성공적으로 합쳐졌습니다.",  # 성공 메시지
                    "input_videos": len(video_urls),  # 입력 영상 개수
                    "transitions_used": "random_transitions",  # 사용된 트랜지션 타입
                    "output_file": output_filename,  # 출력 파일명
                    "url": video_url,  # 접근 URL
                    "duration": "estimated_duration",  # 예상 영상 길이
                    "workflow_complete": True  # 워크플로우 완료 여부
                }
                
            except ImportError:  # client.py 파일을 찾을 수 없는 경우
                raise HTTPException(  # HTTP 500 에러 발생
                    status_code=500,  # 서버 내부 오류 상태 코드
                    detail="client.py를 찾을 수 없습니다. 워크플로우를 먼저 실행해주세요."  # 에러 메시지
                )
            except Exception as e:  # 기타 모든 예외 처리
                raise HTTPException(  # HTTP 500 에러 발생
                    status_code=500,  # 서버 내부 오류 상태 코드
                    detail=f"6단계 영상 합치기 중 오류 발생: {str(e)}"  # 구체적인 에러 메시지 포함
                )

        # ==================================================================================
        # 7단계: OpenAI LLM 기반 TTS 내레이션 생성 (영상 합치기 후)
        # ==================================================================================
        @app.post("/video/create-tts-from-storyboard")  # POST 요청으로 스토리보드 기반 TTS 생성
        async def create_tts_from_storyboard(request: dict):  # 스토리보드 기반 TTS 생성 요청 처리
            """7단계: persona_description, marketing_insights, ad_concept를 OpenAI LLM으로 TTS 내레이션 자동 생성"""
            try:
                print(f"🎙️ 7단계: OpenAI LLM 기반 TTS 내레이션 자동 생성 시작...")
                
                # 요청 데이터 추출
                persona_description = request.get("persona_description", "")  # 페르소나 설명
                marketing_insights = request.get("marketing_insights", "")  # 마케팅 인사이트
                ad_concept = request.get("ad_concept", "")  # 광고 컨셉
                storyboard_scenes = request.get("storyboard_scenes", [])  # 스토리보드 장면들 (선택사항)
                voice_id = request.get("voice_id")  # 음성 ID (선택사항)
                voice_gender = request.get("voice_gender", "female")  # 음성 성별
                voice_language = request.get("voice_language", "ko")  # 음성 언어
                product_name = request.get("product_name", "상품")  # 상품명
                brand_name = request.get("brand_name", "브랜드")  # 브랜드명
                
                print(f"   페르소나: {persona_description[:50]}{'...' if len(persona_description) > 50 else ''}")
                print(f"   마케팅 인사이트: {marketing_insights[:50]}{'...' if len(marketing_insights) > 50 else ''}")
                print(f"   광고 컨셉: {ad_concept[:50]}{'...' if len(ad_concept) > 50 else ''}")
                print(f"   스토리보드 장면: {len(storyboard_scenes)}개")
                print(f"   상품명: {product_name}")
                print(f"   브랜드명: {brand_name}")
                print(f"   음성 설정: {voice_gender} ({voice_language})")

                # client.py의 현재 프로젝트에서 데이터 가져오기 시도
                if not any([persona_description, marketing_insights, ad_concept, storyboard_scenes]):
                    try:
                        from client import current_project
                        if current_project.get("persona"):
                            persona_data = current_project["persona"]
                            if isinstance(persona_data, dict):
                                persona_description = str(persona_data)
                                product_name = persona_data.get("product_name", product_name)
                                brand_name = persona_data.get("brand_name", brand_name)
                            print("📋 client.py에서 페르소나 데이터를 가져왔습니다.")
                        
                        if current_project.get("ad_concept"):
                            ad_concept = current_project["ad_concept"]
                            print("📋 client.py에서 광고 컨셉을 가져왔습니다.")
                        
                        if current_project.get("storyboard"):
                            storyboard_data = current_project["storyboard"]
                            if isinstance(storyboard_data, dict) and storyboard_data.get("scenes"):
                                storyboard_scenes = storyboard_data["scenes"]
                                print("📋 client.py에서 스토리보드 장면들을 가져왔습니다.")
                    except Exception as e:
                        print(f"⚠️ client.py에서 데이터 가져오기 실패: {e}")
                
                # 기본 정보가 없으면 더미 데이터 생성
                if not any([persona_description, marketing_insights, ad_concept, storyboard_scenes]):
                    # 기본 더미 데이터 생성
                    persona_description = f"{product_name}을 사용하는 타겟 고객 페르소나"
                    ad_concept = f"{brand_name}의 {product_name}을 소개하는 매력적인 광고"
                    print("📝 기본 더미 데이터를 생성했습니다.")

                # 1단계: OpenAI LLM으로 TTS 스크립트 자동 생성
                print(f"🤖 OpenAI GPT로 TTS 스크립트 자동 생성 중...")
                
                # LLM 프롬프트 구성
                llm_prompt = f"""
당신은 광고 영상용 TTS 내레이션 전문가입니다. 
다음 정보를 바탕으로 매력적이고 설득력 있는 광고 내레이션 스크립트를 한국어로 작성해주세요.

**상품/브랜드 정보:**
- 상품명: {product_name}
- 브랜드명: {brand_name}

**타겟 고객 (페르소나):**
{persona_description if persona_description else "일반 소비자"}

**마케팅 포인트:**
{marketing_insights if marketing_insights else "품질과 가치를 중시하는 고객층"}

**광고 컨셉:**
{ad_concept if ad_concept else "신뢰할 수 있는 브랜드"}

**스토리보드 장면 정보:**
{storyboard_scenes if storyboard_scenes else "제품을 소개하는 일반적인 광고"}

**요구사항:**
1. 총 3-5개의 짧은 문장으로 구성 (각 문장은 5-10초 분량)
2. 자연스럽고 친근한 톤
3. 제품의 핵심 가치 강조
4. 감정적으로 어필할 수 있는 내용
5. 마지막은 행동 유도 문구 포함

**출력 형식:**
각 문장을 번호와 함께 나열해주세요.
예시:
1. 안녕하세요, {brand_name}입니다.
2. ...
3. ...

스크립트만 작성해주세요:
"""
                
                # OpenAI API 호출
                import httpx
                
                headers = {
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 광고 내레이션 전문가입니다. 매력적이고 설득력 있는 한국어 광고 스크립트를 작성합니다."
                        },
                        {
                            "role": "user",
                            "content": llm_prompt
                        }
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
                
                try:
                    print("🌐 OpenAI API 호출 시작...")
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers=headers,
                            json=payload
                        )
                        
                        print(f"📡 OpenAI 응답 상태: {response.status_code}")
                        
                        if response.status_code != 200:
                            error_text = response.text
                            print(f"❌ OpenAI API 오류 응답: {error_text}")
                            raise Exception(f"OpenAI API 요청 실패: {response.status_code} - {error_text}")
                        
                        response_data = response.json()
                        generated_script = response_data["choices"][0]["message"]["content"]
                        
                        print(f"✅ OpenAI LLM 스크립트 생성 완료:")
                        print(f"   생성된 스크립트 길이: {len(generated_script)}자")
                        print(f"   전체 생성 스크립트:")
                        print(f"   {'-'*50}")
                        print(generated_script)
                        print(f"   {'-'*50}")
                        
                except Exception as llm_error:
                    print(f"❌ OpenAI LLM 호출 실패: {llm_error}")
                    print(f"   오류 타입: {type(llm_error).__name__}")
                    print(f"   상세 오류: {str(llm_error)}")
                    # LLM 실패 시 기본 스크립트 생성
                    generated_script = f"""1. 안녕하세요, {brand_name}와 함께하세요.
2. {product_name}는 {persona_description if persona_description else '고객'}을 위한 특별한 제품입니다.
3. {marketing_insights if marketing_insights else '최고의 품질과 가치'}를 제공합니다.
4. {ad_concept if ad_concept else '신뢰할 수 있는 브랜드'}로 여러분과 함께하겠습니다.
5. 지금 바로 {product_name}를 만나보세요."""
                    print(f"🔄 기본 스크립트로 대체:")
                    print(f"   {generated_script}")

                # 2단계: 생성된 스크립트를 문장별로 파싱
                tts_scripts = []
                
                # 생성된 스크립트에서 번호가 있는 문장들 추출
                import re
                
                # 번호로 시작하는 문장들 찾기 (1. 2. 3. 형태)
                numbered_sentences = re.findall(r'(\d+)\.\s*([^0-9]+?)(?=\d+\.|$)', generated_script, re.DOTALL)
                
                if numbered_sentences:
                    for i, (number, text) in enumerate(numbered_sentences):
                        clean_text = text.strip().replace('\n', ' ').replace('  ', ' ')
                        if clean_text:
                            tts_scripts.append({
                                "scene_number": int(number),
                                "script_type": "generated",
                                "text": clean_text,
                                "description": f"LLM 생성 스크립트 {number}",
                                "duration": 7  # 기본 7초
                            })
                else:
                    # 번호가 없으면 문장 단위로 분할
                    sentences = re.split(r'[.!?]\s+', generated_script)
                    for i, sentence in enumerate(sentences):
                        clean_sentence = sentence.strip()
                        if clean_sentence and len(clean_sentence) > 10:
                            tts_scripts.append({
                                "scene_number": i + 1,
                                "script_type": "generated",
                                "text": clean_sentence,
                                "description": f"LLM 생성 문장 {i + 1}",
                                "duration": 7
                            })
                
                print(f"✅ 총 {len(tts_scripts)}개의 TTS 스크립트 생성 완료:")
                for script in tts_scripts:
                    print(f"   - {script['description']}: {script['text'][:50]}...")

                # 3단계: ElevenLabs TTS 변환 시작
                print("🎤 TTS 변환 모듈 import 중...")
                from tts_utils import get_elevenlabs_api_key, create_multiple_tts_audio
                
                # 스크립트 텍스트만 추출
                script_texts = [script["text"] for script in tts_scripts]
                
                print(f"🎤 TTS 변환 프로세스 시작:")
                print(f"   변환할 스크립트 수: {len(script_texts)}개")
                print(f"   사용할 음성 ID: {voice_id or '21m00Tcm4TlvDq8ikWAM'} (기본값: Rachel)")
                print(f"   출력 디렉토리: D:\\shortpilot\\static\\audio")
                
                # 각 스크립트 내용 미리보기
                for i, text in enumerate(script_texts):
                    print(f"   스크립트 {i+1}: {text[:50]}{'...' if len(text) > 50 else ''}")
                
                # 다중 TTS 오디오 생성 (voice_id가 None이면 기본값 사용)
                print("🎵 ElevenLabs TTS API 호출 시작...")
                try:
                    api_key = get_elevenlabs_api_key()  # API 키 가져오기 (이미 체크됨)
                    # 절대 경로로 static/audio 지정
                    output_dir = os.path.abspath("static/audio")
                    tts_results = await create_multiple_tts_audio(
                        text_list=script_texts,
                        voice_id=voice_id or '21m00Tcm4TlvDq8ikWAM',  # 기본값 보장
                        api_key=api_key,
                        output_dir=output_dir
                    )
                    print(f"✅ TTS 변환 요청 완료, 결과 처리 중...")
                except Exception as tts_error:
                    print(f"❌ TTS 변환 중 오류 발생: {tts_error}")
                    print(f"   오류 타입: {type(tts_error).__name__}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"TTS 변환 실패: {str(tts_error)}"
                    )

                # 3단계: 결과 정리
                successful_tts = []
                failed_tts = []
                
                for i, (script, result) in enumerate(zip(tts_scripts, tts_results)):
                    if result.success:
                        # 파일명만 추출
                        audio_filename = os.path.basename(result.audio_file_path)
                        
                        # static/audio 경로로 통일 (이미 tts_utils에서 생성됨)
                        correct_audio_path = result.audio_file_path
                        audio_url = f"/static/audio/{audio_filename}"
                        
                        print(f"✅ TTS {i+1} 생성 완료: {audio_filename}")
                        if os.path.exists(correct_audio_path):
                            file_size = os.path.getsize(correct_audio_path) / (1024 * 1024)
                            print(f"   파일 크기: {file_size:.1f}MB")
                        
                        successful_tts.append({
                            "scene_number": script["scene_number"],
                            "script_type": script["script_type"],
                            "description": script["description"],
                            "text": script["text"],
                            "audio_url": audio_url,
                            "audio_file_path": correct_audio_path,  # 올바른 경로로 통일
                            "audio_filename": audio_filename,  # 파일명만 별도 저장 (자막 생성용)
                            "duration": result.duration,
                            "file_size": result.file_size
                        })
                    else:
                        failed_tts.append({
                            "scene_number": script["scene_number"],
                            "script_type": script["script_type"],
                            "description": script["description"],
                            "text": script["text"],
                            "error": result.error
                        })
                
                print(f"✅ TTS 변환 완료: {len(successful_tts)}개 성공, {len(failed_tts)}개 실패")
                
                # 🔥 TTS 파일명들을 변수로 수집하고 tts_list.txt 생성
                print(f"📝 TTS 파일명 수집 중...")
                tts_file_paths = []
                
                # successful_tts에서 파일 경로 수집
                for tts in successful_tts:
                    if "audio_file_path" in tts and tts["audio_file_path"]:
                        tts_file_paths.append(tts["audio_file_path"])
                        print(f"   수집: {os.path.basename(tts['audio_file_path'])}")
                
                print(f"📋 총 {len(tts_file_paths)}개 TTS 파일 경로 수집 완료")
                
                # tts_list.txt 파일 생성 시도
                tts_list_file = "tts_list.txt"
                try:
                    with open(tts_list_file, 'w', encoding='utf-8') as f:
                        for file_path in tts_file_paths:
                            f.write(file_path + '\n')
                    
                    print(f"✅ tts_list.txt 파일 생성 성공!")
                    print(f"   파일 위치: {os.path.abspath(tts_list_file)}")
                    print(f"   저장된 파일 수: {len(tts_file_paths)}")
                    
                    # 파일 생성 확인
                    if os.path.exists(tts_list_file):
                        file_size = os.path.getsize(tts_list_file)
                        print(f"   파일 크기: {file_size} bytes")
                    
                except Exception as e:
                    print(f"❌ tts_list.txt 파일 생성 실패!")
                    print(f"   오류: {e}")
                    import traceback
                    traceback.print_exc()
                # 5단계: 응답 생성 (새로 생성된 TTS 파일 목록 포함)
                tts_audio_files = tts_file_paths
                tts_filenames = [os.path.basename(f) for f in tts_file_paths]
                
                # 5단계: 응답 생성
                
                # 🔥 응답 반환 직전에 txt 파일 생성 (실제 생성된 TTS 파일들 확인)
                print(f"📝 실제 생성된 TTS 파일 확인 중...")
                
                # static/audio 폴더에서 방금 생성된 mp3 파일들 찾기
                audio_dir = "static/audio"
                current_tts_files = []
                
                if os.path.exists(audio_dir):
                    # 방금 생성된 파일들만 찾기 (최근 1분 내)
                    import time
                    current_time = time.time()
                    
                    for filename in os.listdir(audio_dir):
                        if filename.endswith('.mp3'):
                            file_path = os.path.join(audio_dir, filename)
                            file_time = os.path.getmtime(file_path)
                            # 최근 1분 내에 생성된 파일만
                            if current_time - file_time < 60:
                                current_tts_files.append(file_path)
                                print(f"   발견: {filename}")
                
                print(f"📋 방금 생성된 TTS 파일: {len(current_tts_files)}개")
                
                # tts_list.txt 파일 생성
                tts_list_file = "tts_list.txt"
                try:
                    with open(tts_list_file, 'w', encoding='utf-8') as f:
                        for file_path in current_tts_files:
                            f.write(file_path + '\n')
                    
                    print(f"✅ tts_list.txt 파일 생성 성공!")
                    print(f"   파일 위치: {os.path.abspath(tts_list_file)}")
                    print(f"   저장된 파일 수: {len(current_tts_files)}")
                    
                    if os.path.exists(tts_list_file):
                        file_size = os.path.getsize(tts_list_file)
                        print(f"   파일 크기: {file_size} bytes")
                    
                except Exception as e:
                    print(f"❌ tts_list.txt 파일 생성 실패!")
                    print(f"   오류: {e}")
                
                
                # 🔥🔥🔥 TTS 생성 완료 후 무조건 tts_list.txt 파일 생성! 🔥🔥🔥
                print(f"📝 tts_list.txt 파일 생성 시작...")
                
                tts_list_file = "tts_list.txt"
                generated_files = []
                
                # static/audio 폴더에서 최근 생성된 mp3 파일들 찾기
                audio_dir = "static/audio"
                if os.path.exists(audio_dir):
                    import time
                    current_time = time.time()
                    
                    for filename in os.listdir(audio_dir):
                        if filename.endswith('.mp3'):
                            file_path = os.path.join(audio_dir, filename)
                            # 최근 2분 내에 생성된 파일만
                            if os.path.exists(file_path):
                                file_time = os.path.getmtime(file_path)
                                if current_time - file_time < 120:  # 2분
                                    generated_files.append(file_path)
                                    print(f"   추가: {filename}")
                
                # txt 파일에 저장
                try:
                    with open(tts_list_file, 'w', encoding='utf-8') as f:
                        for file_path in generated_files:
                            f.write(file_path + '\n')
                    
                    print(f"✅✅✅ tts_list.txt 파일 생성 성공! ✅✅✅")
                    print(f"   파일 위치: {os.path.abspath(tts_list_file)}")
                    print(f"   저장된 TTS 파일 수: {len(generated_files)}")
                    
                    if os.path.exists(tts_list_file):
                        with open(tts_list_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            print(f"   파일 내용 확인: {len(content)} 글자")
                            print(f"   첫 번째 줄: {content.split()[0] if content.split() else 'None'}")
                    
                except Exception as e:
                    print(f"❌❌❌ tts_list.txt 파일 생성 실패! ❌❌❌")
                    print(f"   오류: {e}")
                    import traceback
                    traceback.print_exc()
                
                return {
                    "step": "7단계_TTS_생성",
                    "success": True,
                    "message": f"OpenAI LLM으로 TTS 내레이션 자동 생성 완료! {len(successful_tts)}개 오디오 파일 생성",
                    "generated_script": generated_script,
                    "tts_scripts": tts_scripts,
                    "successful_tts": successful_tts,
                    "failed_tts": failed_tts,
                    "tts_audio_files": tts_audio_files,  # 8단계에서 사용할 파일 목록
                    "tts_filenames": tts_filenames,  # 파일명만 별도 목록
                    "summary": {
                        "total_scripts": len(tts_scripts),
                        "successful": len(successful_tts),
                        "failed": len(failed_tts),
                        "success_rate": f"{(len(successful_tts) / len(tts_scripts)) * 100:.1f}%" if tts_scripts else "0%"
                    },
                    "next_step_info": {
                        "next_step": "8-1단계: 생성된 TTS에서 자막 생성",
                        "endpoint": "POST /video/generate-subtitles",
                        "tts_files_count": len(tts_audio_files),
                        "usage_tip": "이 응답의 'tts_audio_files' 배열을 8단계 요청에 그대로 전달하세요."
                    },
                    "process_details": {
                        "llm_script_generation": "✅ OpenAI로 대본 생성 완료",
                        "tts_conversion": "✅ ElevenLabs로 음성 변환 완료",
                        "scenes_processed": len(storyboard_scenes) if storyboard_scenes else len(tts_scripts),
                        "product_name": product_name,
                        "brand_name": brand_name
                    }
                }
                    
            except ImportError as import_error:
                print(f"❌ 모듈 import 오류: {import_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"필요한 모듈을 불러올 수 없습니다: {str(import_error)}"
                )
            except Exception as e:
                print(f"❌ TTS 생성 중 오류 발생: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"7단계 TTS 생성 중 오류 발생: {str(e)}"
                )

        # ==================================================================================
        # ==================================================================================
        # 8단계: 자막 생성 및 최종 영상 합치기 (TTS 생성 후)
        # ==================================================================================
        @app.post("/video/generate-subtitles")  # POST 요청으로 자막 생성
        async def generate_subtitles_from_tts(request: dict):  # TTS 오디오에서 자막 생성 요청 처리
            """8-1단계: TTS 오디오 파일들에서 자막(.srt) 파일 생성
            
            요청 예시:
            {
                "tts_audio_files": [  // 7단계에서 받은 파일 목록을 그대로 전달
                    "./static/audio/scene_01_20250714_015400.mp3",
                    "./static/audio/scene_02_20250714_015403.mp3"
                ]
            }
            """
            try:
                print(f"� 8-1단계: TTS 오디오에서 자막 생성 시작...")
                
                # 요청 데이터 추출
                tts_audio_files = request.get("tts_audio_files", [])  # TTS 오디오 파일 경로들
                
                # tts_audio_files가 없으면 7단계에서 저장한 txt 파일에서 가져오기
                if not tts_audio_files:
                    print("🔍 7단계에서 저장된 TTS 파일명 txt에서 가져오는 중...")
                    
                    tts_list_file = "tts_list.txt"
                    
                    if os.path.exists(tts_list_file):
                        with open(tts_list_file, 'r', encoding='utf-8') as f:
                            tts_audio_files = [line.strip() for line in f.readlines() if line.strip()]
                        
                        print(f"✅ 7단계에서 생성된 TTS 파일 {len(tts_audio_files)}개 사용:")
                        for i, file_path in enumerate(tts_audio_files):
                            filename = os.path.basename(file_path)
                            if os.path.exists(file_path):
                                file_size = os.path.getsize(file_path) / (1024 * 1024)
                                print(f"   {i+1}. {filename} ({file_size:.1f}MB)")
                            else:
                                print(f"   {i+1}. {filename} (파일 없음)")
                    else:
                        print("❌ 7단계에서 저장된 TTS 파일명이 없습니다.")
                        print("❌ 먼저 7단계에서 TTS를 생성해주세요.")
                
                # 입력 검증
                if not tts_audio_files:
                    raise HTTPException(
                        status_code=400, 
                        detail="TTS 파일이 없습니다. 먼저 7단계에서 TTS를 생성해주세요."
                    )
                
                print(f"📝 자막 생성 프로세스 시작:")
                print(f"   처리할 오디오 파일 수: {len(tts_audio_files)}")
                print(f"   받은 TTS 파일들:")
                for i, file_path in enumerate(tts_audio_files):
                    print(f"   {i+1}. {os.path.basename(file_path)}")
                print(f"   출력 디렉토리: ./static/subtitles")
                
                # 자막 디렉토리 생성
                os.makedirs("./static/subtitles", exist_ok=True)
                
                # 자막 생성
                from subtitle_utils import transcribe_audio_with_whisper
                
                subtitle_results = []
                
                for i, audio_file in enumerate(tts_audio_files, 1):
                    audio_filename = os.path.basename(audio_file)
                    print(f"📝 [{i}/{len(tts_audio_files)}] 자막 생성 중: {audio_filename}")
                    
                    try:
                        # TTS 파일명을 기반으로 .srt 파일명 생성
                        base_name = os.path.splitext(audio_filename)[0]
                        subtitle_filename = f"{base_name}.srt"
                        subtitle_path = os.path.join("./static/subtitles", subtitle_filename)
                        
                        print(f"   🎯 TTS 파일: {audio_filename}")
                        print(f"   📝 생성될 자막 파일: {subtitle_filename}")
                        
                        subtitle_result = await transcribe_audio_with_whisper(
                            audio_file_path=audio_file,
                            language="ko",
                            output_format="srt"
                        )
                        
                        if subtitle_result.success:
                            # 생성된 자막 파일을 static/subtitles 디렉토리로 복사
                            import shutil
                            shutil.copy2(subtitle_result.subtitle_file_path, subtitle_path)
                            
                            subtitle_results.append({
                                "scene_number": i,
                                "audio_file": audio_file,
                                "audio_filename": audio_filename,
                                "tts_filename_param": audio_filename,  # TTS 파일명 매개변수
                                "subtitle_file": subtitle_path,
                                "subtitle_filename": subtitle_filename,
                                "subtitle_url": f"/static/subtitles/{subtitle_filename}",
                                "duration": subtitle_result.duration,
                                "transcript": subtitle_result.transcription,
                                "word_count": len(subtitle_result.transcription.split()) if subtitle_result.transcription else 0,
                                "tts_based_name": True  # TTS 파일명 기반으로 생성됨
                            })
                            print(f"   ✅ 성공: {subtitle_filename} ({subtitle_result.duration:.1f}초)")
                            print(f"   📊 전사 내용: {subtitle_result.transcription[:100]}{'...' if len(subtitle_result.transcription) > 100 else ''}")
                        else:
                            print(f"   ❌ 실패: {subtitle_result.error}")
                            subtitle_results.append({
                                "scene_number": i,
                                "audio_file": audio_file,
                                "audio_filename": audio_filename,
                                "error": subtitle_result.error
                            })
                    
                    except Exception as e:
                        print(f"   ❌ 오류 발생: {e}")
                        subtitle_results.append({
                            "scene_number": i,
                            "audio_file": audio_file,
                            "audio_filename": audio_filename,
                            "error": str(e)
                        })
                
                # 성공/실패 통계
                successful_subtitles = [r for r in subtitle_results if "subtitle_file" in r]
                failed_subtitles = [r for r in subtitle_results if "error" in r]
                
                print(f"✅ 자막 생성 완료:")
                print(f"   성공: {len(successful_subtitles)}개")
                print(f"   실패: {len(failed_subtitles)}개")
                print(f"   성공률: {(len(successful_subtitles) / len(tts_audio_files)) * 100:.1f}%")
                
                # 자막 생성 완료 후 TTS 파일 목록 txt 파일 삭제
                tts_list_file = "tts_list.txt"
                if os.path.exists(tts_list_file):
                    os.remove(tts_list_file)
                    print(f"🗑️ TTS 파일 목록 삭제: {tts_list_file}")
                
                # 성공한 자막들의 순서 정보 생성 (다음 단계에서 영상 합치기용)
                if successful_subtitles:
                    print("📋 생성된 자막 파일 순서:")
                    for subtitle in successful_subtitles:
                        print(f"   {subtitle['scene_number']}. {subtitle['subtitle_filename']} ({subtitle.get('duration', 0):.1f}초)")
                
                return {
                    "step": "8-1단계_자막_생성",
                    "success": True,
                    "message": f"7단계에서 방금 생성된 TTS 파일들만 자막 변환 완료! {len(successful_subtitles)}개 .srt 파일 생성",
                    "subtitle_results": subtitle_results,
                    "successful_subtitles": successful_subtitles,
                    "failed_subtitles": failed_subtitles,
                    "tts_file_mapping": {
                        "source_method": "7단계 응답에서 직접 전달받음",
                        "file_location": "모든 파일이 ./static/audio/ 폴더에 통일 저장됨",
                        "tts_to_srt_mapping": [
                            {
                                "tts_filename_param": r.get("tts_filename_param", os.path.basename(r["audio_file"])),
                                "srt_filename": r["subtitle_filename"],
                                "status": "✅ 성공" if "subtitle_file" in r else "❌ 실패",
                                "example": f"{r.get('tts_filename_param', 'scene_01_20250714_015400.mp3')} → {r['subtitle_filename']}"
                            } for r in subtitle_results
                        ]
                    },
                    "summary": {
                        "total_files": len(tts_audio_files),
                        "successful": len(successful_subtitles),
                        "failed": len(failed_subtitles),
                        "success_rate": f"{(len(successful_subtitles) / len(tts_audio_files)) * 100:.1f}%" if tts_audio_files else "0%"
                    },
                    "next_step_info": {
                        "description": "TTS 파일명 기반으로 생성된 .srt 자막들을 영상에 순서대로 합칠 수 있습니다.",
                        "subtitle_files": [r["subtitle_file"] for r in successful_subtitles],
                        "recommended_endpoint": "/video/merge-with-tts-subtitles",
                        "tip": "7단계 응답의 tts_audio_files 배열을 8단계 요청에 그대로 전달하세요. 텍스트 파일이나 변수 저장 없이 직접 전달됩니다."
                    }
                }
                
            except HTTPException:
                raise  # HTTP 예외는 그대로 전달
            except Exception as e:
                print(f"❌ 자막 생성 실패: {e}")
                raise HTTPException(status_code=500, detail=f"자막 생성 실패: {str(e)}")

        @app.post("/video/merge-with-tts-subtitles")  # POST 요청으로 TTS + 자막 완전 합치기
        async def merge_videos_with_tts_and_subtitles(request: dict):  # TTS + 자막 완전 합치기 요청 처리
            """8-2단계: 영상에 TTS 오디오와 자막을 최종 합치기 (순서대로 자동 합치기)"""
            try:
                print(f"🎬 8-2단계: 영상 + TTS + 자막 완전 합치기 시작...")
                
                # 요청 데이터 추출
                video_urls = request.get("video_urls", [])  # 비디오 URL 리스트 (선택사항)
                audio_files = request.get("audio_files", [])  # TTS 오디오 파일들 (선택사항)
                subtitle_files = request.get("subtitle_files", [])  # 자막 파일들 (선택사항)
                auto_detect_files = request.get("auto_detect_files", True)  # 자동 파일 찾기
                output_filename = request.get("output_filename", "final_video_with_tts_subtitles.mp4")
                transition_type = request.get("transition_type", "fade")  # 트랜지션 타입
                tts_volume = request.get("tts_volume", 0.8)  # TTS 볼륨
                video_volume = request.get("video_volume", 0.3)  # 원본 비디오 볼륨
                enable_bgm = request.get("enable_bgm", True)  # BGM 사용 여부
                bgm_volume = request.get("bgm_volume", 0.2)  # BGM 볼륨
                
                # 1. 자동으로 최신 생성된 파일들 찾기
                if auto_detect_files:
                    print("🔍 최신 생성 파일들 자동 검색 중...")
                    
                    import glob
                    import time
                    current_time = time.time()
                    recent_time_limit = 1800  # 30분 = 1800초
                    
                    # 최신 비디오 파일들 찾기
                    if not video_urls:
                        video_dir = "./static/videos"
                        if os.path.exists(video_dir):
                            video_files = []
                            for ext in ['*.mp4', '*.avi', '*.mov']:
                                video_files.extend(glob.glob(os.path.join(video_dir, ext)))
                            
                            if video_files:
                                # 최근 파일들만 선택
                                recent_videos = []
                                for file_path in video_files:
                                    if current_time - os.path.getmtime(file_path) < recent_time_limit:
                                        recent_videos.append(file_path)
                                
                                if recent_videos:
                                    # 파일명에서 숫자 순서대로 정렬
                                    recent_videos.sort()
                                    video_urls = [f"/static/videos/{os.path.basename(f)}" for f in recent_videos]
                                    print(f"✅ 비디오 파일 {len(video_urls)}개 발견")
                    
                    # 최신 오디오 파일들 찾기
                    if not audio_files:
                        audio_dir = "./static/audio"
                        if os.path.exists(audio_dir):
                            audio_files_found = []
                            for ext in ['*.mp3', '*.wav']:
                                audio_files_found.extend(glob.glob(os.path.join(audio_dir, ext)))
                            
                            if audio_files_found:
                                # 최근 파일들만 선택
                                recent_audio = []
                                for file_path in audio_files_found:
                                    if current_time - os.path.getmtime(file_path) < recent_time_limit:
                                        recent_audio.append(file_path)
                                
                                if recent_audio:
                                    recent_audio.sort()
                                    audio_files = recent_audio
                                    print(f"✅ 오디오 파일 {len(audio_files)}개 발견")
                    
                    # 최신 자막 파일들 찾기
                    if not subtitle_files:
                        subtitle_dir = "./static/subtitles"
                        if os.path.exists(subtitle_dir):
                            subtitle_files_found = []
                            for ext in ['*.srt', '*.vtt']:
                                subtitle_files_found.extend(glob.glob(os.path.join(subtitle_dir, ext)))
                            
                            if subtitle_files_found:
                                # 최근 파일들만 선택
                                recent_subtitles = []
                                for file_path in subtitle_files_found:
                                    if current_time - os.path.getmtime(file_path) < recent_time_limit:
                                        recent_subtitles.append(file_path)
                                
                                if recent_subtitles:
                                    recent_subtitles.sort()
                                    subtitle_files = recent_subtitles
                                    print(f"✅ 자막 파일 {len(subtitle_files)}개 발견")
                
                # 입력 검증
                if not video_urls:
                    raise HTTPException(
                        status_code=400, 
                        detail="비디오 파일이 필요합니다. 먼저 5-6단계에서 비디오를 생성하고 합쳐주세요."
                    )
                
                if not audio_files:
                    raise HTTPException(
                        status_code=400, 
                        detail="TTS 오디오 파일이 필요합니다. 먼저 7단계에서 TTS를 생성해주세요."
                    )
                
                if not subtitle_files:
                    raise HTTPException(
                        status_code=400, 
                        detail="자막 파일이 필요합니다. 먼저 8-1단계에서 자막을 생성해주세요."
                    )
                
                print(f"📋 합치기 프로세스 정보:")
                print(f"   비디오 파일: {len(video_urls)}개")
                print(f"   오디오 파일: {len(audio_files)}개")
                print(f"   자막 파일: {len(subtitle_files)}개")
                print(f"   출력 파일명: {output_filename}")
                
                # 파일 순서 매칭 (최소 개수에 맞춤)
                min_count = min(len(video_urls), len(audio_files), len(subtitle_files))
                if min_count < len(video_urls) or min_count < len(audio_files) or min_count < len(subtitle_files):
                    print(f"⚠️ 파일 개수 불일치, 최소 개수 {min_count}개에 맞춰 처리합니다.")
                    video_urls = video_urls[:min_count]
                    audio_files = audio_files[:min_count]
                    subtitle_files = subtitle_files[:min_count]
                
                print(f"📝 순서대로 매칭:")
                for i in range(min_count):
                    print(f"   {i+1}. 비디오: {os.path.basename(video_urls[i])}")
                    print(f"       오디오: {os.path.basename(audio_files[i])}")
                    print(f"       자막: {os.path.basename(subtitle_files[i])}")
                
                # FFmpeg로 비디오 + TTS + 자막 합치기
                print("🎬 FFmpeg로 최종 합치기 실행...")
                
                from complete_video_workflow import FullVideoWorkflow
                
                workflow = FullVideoWorkflow(use_static_dir=True)
                
                final_result = await workflow.merge_videos_with_audio_and_subtitles(
                    video_urls=video_urls,
                    audio_files=audio_files,
                    subtitle_files=subtitle_files,
                    output_filename=output_filename,
                    transition_type=transition_type,
                    tts_volume=tts_volume,
                    video_volume=video_volume,
                    bgm_volume=bgm_volume if enable_bgm else 0
                )
                
                if final_result.get("success"):
                    final_video_url = f"/static/videos/{output_filename}"
                    
                    print(f"🎉 최종 영상 완성!")
                    print(f"📱 브라우저에서 확인: {final_video_url}")
                    
                    return {
                        "step": "8-2단계_최종_합치기",
                        "success": True,
                        "message": "영상 + TTS + 자막 완전 합치기 성공!",
                        "final_video_url": final_video_url,
                        "final_video_path": final_result["output_path"],
                        "processing_details": {
                            "videos_processed": len(video_urls),
                            "audio_files_added": len(audio_files),
                            "subtitle_files_added": len(subtitle_files),
                            "transition_type": transition_type,
                            "output_filename": output_filename
                        },
                        "file_details": {
                            "video_files": [os.path.basename(url) for url in video_urls],
                            "audio_files": [os.path.basename(f) for f in audio_files],
                            "subtitle_files": [os.path.basename(f) for f in subtitle_files]
                        }
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"최종 합치기 실패: {final_result.get('error', '알 수 없는 오류')}"
                    )
                
                # 성공 응답 생성
                final_video_url = f"http://localhost:8000/static/videos/{os.path.basename(result['final_video_path'])}"
                
                return {
                    "success": True,
                    "message": f"TTS + 자막이 포함된 {len(video_urls)}개 비디오 완전 합치기 완료!",
                    "final_video_url": final_video_url,
                    "final_video_path": result["final_video_path"],
                    "processing_details": {
                        "video_count": len(video_urls),
                        "tts_count": len(tts_scripts),
                        "transition_type": transition_type,
                        "voice_id": voice_id or "기본값",
                        "tts_volume": tts_volume,
                        "video_volume": video_volume,
                        "has_subtitles": add_subtitles,
                        "subtitle_info": result.get("subtitle_info")
                    },
                    "files_generated": {
                        "final_video": os.path.basename(result["final_video_path"]),
                        "tts_files": result.get("tts_files", []),
                        "subtitle_files": result.get("subtitle_files", [])
                    }
                }
                
            except HTTPException:
                raise  # HTTP 예외는 그대로 전달
            except Exception as e:
                print(f"❌ TTS + 자막 완전 합치기 실패: {e}")
                raise HTTPException(status_code=500, detail=f"TTS + 자막 완전 합치기 실패: {str(e)}")

        print("✅ 비디오 기능 추가 완료!")  # 모든 기능 추가 완료 알림
        print("📋 추가된 API 엔드포인트:")  # 추가된 엔드포인트 목록 출력 시작
        print("   - GET  /video/status (상태 확인)")  # 상태 확인 API
        print("   - POST /video/generate-videos (5단계: Runway API 비디오 생성)")  # AI 비디오 생성 API
        print("   - POST /video/merge-with-transitions (6단계: 랜덤 트랜지션 합치기)")  # 생성된 비디오 합치기 API
        print("   - POST /video/create-tts-from-storyboard (7단계: 스토리보드 기반 TTS 생성)")  # 스토리보드 TTS 생성 API
        print("   - POST /video/generate-subtitles (8-1단계: TTS에서 자막(.srt) 생성)")  # 자막 생성 API
        print("   - POST /video/merge-with-tts-subtitles (8-2단계: TTS+자막 완전 합치기)")  # TTS+자막 완전 합치기 API
        print("   - GET  /tts/voices (사용 가능한 TTS 음성 목록 조회)")  # TTS 음성 목록 조회 API
        print("   - POST /tts/create-samples (음성 샘플 생성)")  # 음성 샘플 생성 API
        print("   - POST /tts/select-voice (음성 선택 및 테스트)")  # 음성 선택 및 테스트 API 안내
        
        return app  # 설정이 완료된 FastAPI app 반환
        
    except ImportError as e:  # 필요한 모듈을 import할 수 없는 경우
        print(f"❌ Import 오류: {e}")  # import 에러 출력
        print("필요한 파일들이 없는 것 같습니다.")  # 추가 안내 메시지
        return None  # 실패 시 None 반환
    except Exception as e:  # 기타 모든 예외 처리
        print(f"❌ 기능 추가 실패: {e}")  # 일반적인 에러 출력
        return None  # 실패 시 None 반환

def start_video_server():
    """비디오 서버 시작"""
    print("🎬 비디오 합치기 서버를 시작합니다...")  # 서버 시작 알림
    print("📋 서버 정보:")  # 서버 설정 정보 출력 시작
    print("   - 포트: 8001")  # 서버가 실행될 포트 번호
    print("   - 주소: http://127.0.0.1:8001")  # 로컬 접속 주소
    print("   - API 문서: http://127.0.0.1:8001/docs")  # FastAPI 자동 생성 API 문서 주소
    print("   - 상태 확인: http://127.0.0.1:8001/video/status")  # 비디오 기능 상태 확인 주소
    
    print("\n🔧 비디오 기능 추가 중...")  # 기능 추가 시작 알림
    
    # 기존 client.py 서버에 비디오 기능 추가
    app = add_video_features_to_server()  # 위에서 정의한 함수 호출하여 비디오 기능 추가
    
    if app is None:  # 기능 추가가 실패한 경우
        print("❌ 기능 추가에 실패했습니다.")  # 실패 메시지 출력
        return  # 함수 종료 (서버 시작하지 않음)
    
    print("\n🚀 비디오 서버를 시작합니다...")  # 서버 시작 최종 알림
    print("📋 주요 기능:")  # 제공하는 주요 기능 목록 출력 시작
    print("   🤖 5단계 AI 비디오 생성: POST /video/generate-videos")  # AI 비디오 생성 API 안내
    print("   🎬 6단계 랜덤 트랜지션 합치기: POST /video/merge-with-transitions")  # 생성된 비디오 합치기 API 안내
    print("   📱 사용자 비디오 합치기: POST /video/merge-custom")  # 사용자 비디오 합치기 API 안내
    print("    TTS 포함 비디오 합치기: POST /video/merge-with-tts")  # 단일 비디오 TTS 추가 API 안내
    print("   🎙️ 스토리보드 기반 TTS 생성: POST /video/create-tts-from-storyboard")  # 스토리보드 TTS 생성 API 안내
    print("   📝 자막 생성: POST /video/generate-subtitles")  # 자막 생성 API 안내
    print("   🎬 TTS+자막 완전 합치기: POST /video/merge-with-tts-subtitles")  # TTS+자막 완전 합치기 API 안내
    print("   📜 사용 가능한 TTS 음성 목록 조회: GET /tts/voices")  # TTS 음성 목록 조회 API 안내
    print("   🎵 음성 샘플 생성: POST /tts/create-samples")  # 음성 샘플 생성 API 안내
    print("   🎤 음성 선택 및 테스트: POST /tts/select-voice")  # 음성 선택 및 테스트 API 안내
    
    # uvicorn ASGI 서버로 FastAPI 앱 실행
    uvicorn.run(
        app,  # 실행할 FastAPI 애플리케이션 객체
        host="127.0.0.1",  # 서버 호스트 주소 (로컬호스트)
        port=8001,  # 서버 포트 번호 (8000 대신 8001 사용)
        reload=False,  # 코드 변경 시 자동 재시작 비활성화 (프로덕션 모드)
        log_level="info"  # 로그 레벨 설정 (정보 수준)
    )

if __name__ == "__main__":  # 스크립트가 직접 실행될 때만 실행
    start_video_server()  # 비디오 서버 시작 함수 호출
