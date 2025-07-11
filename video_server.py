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

        @app.get("/llm-tts-test", response_class=HTMLResponse)
        async def llm_tts_test_page():
            """OpenAI LLM TTS 테스트 웹 인터페이스"""
            try:
                with open("static/llm_tts_test.html", "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            except FileNotFoundError:
                return HTMLResponse(
                    content="<h1>LLM TTS Test Page not found</h1>", 
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
                    "POST /video/merge-custom": "사용자 비디오 URL로 합치기",  # 사용자 비디오 합치기 API
                    "POST /video/merge-user-videos": "6-1단계: 사용자 비디오 랜덤 트랜지션 합치기",  # 사용자 비디오 랜덤 트랜지션 API
                    "POST /video/create-complete": "🆕 완전한 비디오 제작: 스토리보드 → 비디오 → TTS → 자막",  # 완전한 워크플로우 API
                    "POST /video/create-tts-from-storyboard": "🎙️ OpenAI LLM 기반 TTS 자동 생성",  # 스토리보드 기반 TTS 생성
                    "POST /video/test-llm-tts": "🧪 OpenAI LLM TTS 테스트 (기본값)",  # LLM TTS 테스트
                    "POST /video/create-simple-tts": "🎤 간단한 텍스트 TTS 생성",  # 간단한 TTS 생성
                    "POST /video/generate-subtitles": "📝 TTS 오디오에서 자막 파일(.srt) 생성",  # 자막 생성 API
                    "POST /video/merge-with-tts-subtitles": "🎬 비디오 + TTS + 자막 완전 합치기"  # TTS와 자막 포함 완전 합치기
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

        # === 5단계: Runway API 영상 생성 API 엔드포인트 ===
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
                test_image_urls = []
                
                print(f"🔧 current_project['images'] 내용: {len(image_data_list)}개")
                print(f"🔧 이미지 데이터 타입: {type(image_data_list)}")
                
                for i, img_data in enumerate(image_data_list):
                    print(f"🔧 이미지 {i+1} 데이터: {type(img_data)} - {str(img_data)[:100]}...")
                    
                    # 다양한 형태의 이미지 데이터 처리
                    if isinstance(img_data, dict):
                        # dict 형태: {"url": "...", "status": "success", ...}
                        if img_data.get("url"):
                            test_image_urls.append(img_data["url"])
                        elif img_data.get("image_url"):
                            test_image_urls.append(img_data["image_url"])
                        elif img_data.get("generated_image_url"):
                            test_image_urls.append(img_data["generated_image_url"])
                    elif isinstance(img_data, str):
                        # string 형태: 직접 URL
                        test_image_urls.append(img_data)
                
                if not test_image_urls:
                    print(f"❌ 추출된 URL이 없습니다. 원본 데이터:")
                    for i, img_data in enumerate(image_data_list):
                        print(f"   데이터 {i+1}: {img_data}")
                    raise HTTPException(
                        status_code=400,
                        detail="4단계 이미지 데이터에서 유효한 URL을 찾을 수 없습니다."
                    )
                
                print(f"✅ 4단계에서 가져온 이미지: {len(test_image_urls)}개")
                for i, url in enumerate(test_image_urls, 1):
                    print(f"   이미지 {i}: {url[:80]}...")
                
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="client.py를 찾을 수 없습니다. 워크플로우를 먼저 실행해주세요."
                )
            
            print("🎬 5단계: 4단계 이미지들 → 비디오 변환 시작...")
            print(f"🖼️ 총 {len(test_image_urls)}개의 이미지를 비디오로 변환합니다...")
            
            # video_models.py 설정 사용
            from video_models import ImageToVideoRequest, VideoGenerationResult, VideoConfig
            
            # 비디오 생성 설정
            video_request = ImageToVideoRequest(
                image_urls=test_image_urls,
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
                    for i, image_url in enumerate(test_image_urls, 1):
                        print(f"\n🎬 [{i}/{len(test_image_urls)}] 이미지 → 동영상 변환 중...")
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

        # === 6단계: 트랜지션 적용 영상 합치기 API 엔드포인트 ===
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

        
        # === 6-1단계: 사용자 영상 랜덤 트랜지션 합치기 API 엔드포인트 ===
        @app.post("/video/merge-user-videos")  # POST 요청으로 /video/merge-user-videos 경로에 접근 시 실행
        async def merge_user_videos_with_random_transitions(request: VideoMergeRequest):  # 비동기 함수, 요청 데이터를 VideoMergeRequest 모델로 받음
            """6-1단계: 사용자 제공 영상 URL들을 랜덤 트랜지션으로 합치기"""
            if not request.video_urls:  # 영상 URL 리스트가 비어있으면 에러
                raise HTTPException(  # HTTP 400 에러 발생
                    status_code=400,  # 잘못된 요청 상태 코드
                    detail="video_urls가 비어있습니다."  # 에러 메시지
                )
            
            if len(request.video_urls) < 2:  # 영상이 2개 미만이면 에러 (트랜지션을 위해 최소 2개 필요)
                raise HTTPException(  # HTTP 400 에러 발생
                    status_code=400,  # 잘못된 요청 상태 코드
                    detail="최소 2개 이상의 영상 URL이 필요합니다."  # 에러 메시지
                )
            
            print(f"🎲 6-1단계: 사용자 영상 {len(request.video_urls)}개를 랜덤 트랜지션으로 합치기 시작...")  # 작업 시작 알림과 영상 개수 출력
            
            # URL들의 유효성 확인 (각 URL이 올바른 형식인지 검증)
            for i, url in enumerate(request.video_urls):  # 각 URL에 대해 반복 처리
                if not url or not url.strip():  # URL이 비어있거나 공백만 있으면 에러
                    raise HTTPException(  # HTTP 400 에러 발생
                        status_code=400,  # 잘못된 요청 상태 코드
                        detail=f"영상 URL {i+1}이 비어있습니다."  # 몇 번째 URL인지 명시한 에러 메시지
                    )
                if not (url.startswith('http://') or url.startswith('https://')):  # HTTP/HTTPS로 시작하지 않으면 에러
                    raise HTTPException(  # HTTP 400 에러 발생
                        status_code=400,  # 잘못된 요청 상태 코드
                        detail=f"영상 URL {i+1}이 유효하지 않습니다: {url}"  # 구체적인 URL과 함께 에러 메시지
                    )
            
            print(f"📋 입력 영상 URL들:")  # 입력으로 받은 URL들 출력 시작
            for i, url in enumerate(request.video_urls):  # 각 URL을 번호와 함께 출력
                print(f"   {i+1}. {url}")  # URL 번호와 실제 URL 출력
            
            try:  # 영상 합치기 처리 시도
                merger = create_merger_instance(use_static_dir=True)  # 영상 합치기 객체 생성 (static 디렉토리 사용)
                output_filename = generate_output_filename("user_random_transitions")  # 타임스탬프 포함 출력 파일명 생성
                
                # 랜덤 트랜지션으로 영상 합치기 실행
                final_video_path = merger.merge_videos_with_frame_transitions(  # 프레임 단위 트랜지션으로 영상 합치기 실행
                    request.video_urls,  # 사용자가 제공한 영상 URL 리스트
                    output_filename  # 출력 파일명
                )
                video_url = merger.get_video_url(output_filename)  # 웹에서 접근 가능한 URL 생성
                
                response = create_video_response(  # 표준화된 응답 객체 생성
                    message="🎉 6-1단계: 사용자 영상 랜덤 트랜지션 합치기가 완료되었습니다!",  # 완료 메시지
                    filename=output_filename,  # 출력 파일명
                    video_url=video_url,  # 접근 URL
                    local_path=final_video_path,  # 로컬 파일 경로
                    video_count=len(request.video_urls),  # 합쳐진 영상 개수
                    method="랜덤 트랜지션 (Frame-level animation)"  # 사용된 처리 방법
                )
                
                # 사용자 워크플로우 관련 추가 정보
                response["user_workflow"] = {  # 사용자 워크플로우 정보 추가
                    "step": "6-1단계",  # 현재 단계
                    "description": "사용자 제공 영상 URL로 랜덤 트랜지션 합치기",  # 단계 설명
                    "input_videos": request.video_urls,  # 입력으로 받은 영상 URL들
                    "video_count": len(request.video_urls),  # 영상 개수
                    "transition_count": len(request.video_urls) - 1 if len(request.video_urls) > 1 else 0  # 트랜지션 개수 (영상 개수 - 1)
                }
                
                # 트랜지션 효과 관련 정보
                response["transitions"] = {  # 트랜지션 정보 추가
                    "applied": True,  # 트랜지션 적용 여부
                    "type": "random",  # 트랜지션 타입: 랜덤
                    "count": len(request.video_urls) - 1 if len(request.video_urls) > 1 else 0,  # 적용된 트랜지션 개수
                    "features": [  # 트랜지션 기능 목록
                        "🎲 매번 다른 랜덤 트랜지션",  # 랜덤 선택
                        "🔄 Frame-by-frame 애니메이션",  # 프레임 단위 애니메이션
                        "📱 부드러운 패닝 효과",  # 패닝 트랜지션
                        "🌀 회전 및 확대/축소",  # 회전과 줌 트랜지션
                        "🎨 fade 및 blend 효과",  # 페이드 트랜지션
                        "🎵 트랜지션별 오디오 효과"  # 오디오 효과
                    ]
                }
                
                print(f"✅ 6-1단계 완료: {output_filename}")  # 완료 메시지와 파일명 출력
                print(f"🔗 접속 URL: {video_url}")  # 접근 URL 출력
                
                return response  # 완성된 응답 반환
                
            except Exception as e:  # 영상 합치기 처리 중 예외 발생
                raise HTTPException(  # HTTP 500 에러 발생
                    status_code=500,  # 서버 내부 오류 상태 코드
                    detail=f"6-1단계 사용자 영상 랜덤 트랜지션 합치기 실패: {str(e)}"  # 구체적인 에러 메시지 포함
                )

        # === 스토리보드 기반 TTS 내레이션 생성 API 엔드포인트 ===
        @app.post("/video/create-tts-from-storyboard")  # POST 요청으로 스토리보드 기반 TTS 생성
        async def create_tts_from_storyboard(request: dict):  # 스토리보드 기반 TTS 생성 요청 처리
            """persona_description, marketing_insights, ad_concept를 OpenAI LLM으로 TTS 내레이션 자동 생성"""
            try:
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
                
                # 기본 정보가 없으면 에러
                if not any([persona_description, marketing_insights, ad_concept, storyboard_scenes]):
                    raise HTTPException(
                        status_code=400, 
                        detail="persona_description, marketing_insights, ad_concept, storyboard_scenes 중 최소 하나는 필요합니다."
                    )
                
                print(f"🎙️ OpenAI LLM 기반 TTS 내레이션 자동 생성 시작...")
                print(f"   페르소나: {persona_description[:50]}{'...' if len(persona_description) > 50 else ''}")
                print(f"   마케팅 인사이트: {marketing_insights[:50]}{'...' if len(marketing_insights) > 50 else ''}")
                print(f"   광고 컨셉: {ad_concept[:50]}{'...' if len(ad_concept) > 50 else ''}")
                print(f"   스토리보드 장면: {len(storyboard_scenes)}개")
                print(f"   상품명: {product_name}")
                print(f"   브랜드명: {brand_name}")
                print(f"   음성 설정: {voice_gender} ({voice_language})")
                
                # OpenAI API 키 확인
                import os
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    raise HTTPException(
                        status_code=500,
                        detail="OpenAI API 키가 설정되지 않았습니다. .env 파일의 OPENAI_API_KEY를 확인해주세요."
                    )
                
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
                    "Authorization": f"Bearer {openai_api_key}",
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
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers=headers,
                            json=payload
                        )
                        
                        if response.status_code != 200:
                            raise Exception(f"OpenAI API 요청 실패: {response.status_code} - {response.text}")
                        
                        response_data = response.json()
                        generated_script = response_data["choices"][0]["message"]["content"]
                        
                        print(f"✅ OpenAI LLM 스크립트 생성 완료:")
                        print(f"   생성된 스크립트 길이: {len(generated_script)}자")
                        print(f"   미리보기: {generated_script[:100]}...")
                        
                except Exception as llm_error:
                    print(f"⚠️ OpenAI LLM 호출 실패: {llm_error}")
                    # LLM 실패 시 기본 스크립트 생성
                    generated_script = f"""1. 안녕하세요, {brand_name}와 함께하세요.
2. {product_name}는 {persona_description if persona_description else '고객'}을 위한 특별한 제품입니다.
3. {marketing_insights if marketing_insights else '최고의 품질과 가치'}를 제공합니다.
4. {ad_concept if ad_concept else '신뢰할 수 있는 브랜드'}로 여러분과 함께하겠습니다.
5. 지금 바로 {product_name}를 만나보세요."""
                    print(f"🔄 기본 스크립트로 대체: {generated_script[:50]}...")
                
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
                
                # 3단계: ElevenLabs API 키 확인 및 TTS 변환
                from tts_utils import get_elevenlabs_api_key
                api_key = get_elevenlabs_api_key()
                if not api_key:
                    raise HTTPException(
                        status_code=500, 
                        detail="ElevenLabs API 키가 설정되지 않았습니다. .env 파일의 ELEVENLABS_API_KEY를 확인해주세요."
                    )
                
                # 4단계: 각 스크립트를 TTS로 변환
                from tts_utils import create_multiple_tts_audio
                
                # 스크립트 텍스트만 추출
                script_texts = [script["text"] for script in tts_scripts]
                
                print(f"🎤 {len(script_texts)}개 스크립트를 TTS로 변환 중...")
                print(f"   사용할 음성 ID: {voice_id or '21m00Tcm4TlvDq8ikWAM'} (기본값: Rachel)")
                
                # 다중 TTS 오디오 생성 (voice_id가 None이면 기본값 사용)
                tts_results = await create_multiple_tts_audio(
                    text_list=script_texts,
                    voice_id=voice_id or '21m00Tcm4TlvDq8ikWAM',  # 기본값 보장
                    api_key=api_key,
                    output_dir="./static/audio"
                )
                
                # 3단계: 결과 정리
                successful_tts = []
                failed_tts = []
                
                for i, (script, result) in enumerate(zip(tts_scripts, tts_results)):
                    if result.success:
                        # 웹 접근 가능한 URL로 변환
                        audio_filename = os.path.basename(result.audio_file_path)
                        audio_url = f"/static/audio/{audio_filename}"
                        
                        successful_tts.append({
                            "scene_number": script["scene_number"],
                            "script_type": script["script_type"],
                            "description": script["description"],
                            "text": script["text"],
                            "audio_url": audio_url,
                            "audio_file_path": result.audio_file_path,
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
                
                # 4단계: 응답 생성
                return {
                    "success": True,
                    "message": f"OpenAI LLM으로 TTS 내레이션 자동 생성 완료! {len(successful_tts)}개 오디오 파일 생성",
                    "generated_script": generated_script,
                    "tts_scripts": tts_scripts,
                    "successful_tts": successful_tts,
                    "failed_tts": failed_tts,
                    "summary": {
                        "total_scripts": len(tts_scripts),
                        "successful": len(successful_tts),
                        "failed": len(failed_tts),
                        "success_rate": f"{(len(successful_tts) / len(tts_scripts)) * 100:.1f}%" if tts_scripts else "0%"
                    },
                    "llm_generation": {
                        "used_openai": True,
                        "script_length": len(generated_script),
                        "sentences_extracted": len(tts_scripts)
                    },
                    "input_data": {
                        "persona_description": persona_description,
                        "marketing_insights": marketing_insights,
                        "ad_concept": ad_concept,
                        "product_name": product_name,
                        "brand_name": brand_name,
                        "scene_count": len(storyboard_scenes),
                        "voice_settings": {
                            "voice_id": voice_id,
                            "voice_gender": voice_gender,
                            "voice_language": voice_language
                        }
                    }
                }
                
            except HTTPException:
                raise  # HTTP 예외는 그대로 전달
            except Exception as e:
                print(f"❌ 스토리보드 기반 TTS 생성 실패: {e}")
                raise HTTPException(status_code=500, detail=f"스토리보드 기반 TTS 생성 실패: {str(e)}")

        # === 자막 생성 API 엔드포인트 ===
        @app.post("/video/generate-subtitles")  # POST 요청으로 자막 생성
        async def generate_subtitles_from_tts(request: dict):  # TTS 오디오에서 자막 생성 요청 처리
            """TTS 오디오 파일들에서 자막(.srt) 파일 생성"""
            try:
                # 요청 데이터 추출
                tts_audio_files = request.get("tts_audio_files", [])  # TTS 오디오 파일 경로들
                output_filename = request.get("output_filename", "generated_subtitles.srt")  # 출력 자막 파일명
                
                # 입력 검증
                if not tts_audio_files:
                    raise HTTPException(status_code=400, detail="tts_audio_files가 필요합니다.")
                
                print(f"📝 TTS 오디오에서 자막 생성 요청 처리 시작...")
                print(f"   오디오 파일 수: {len(tts_audio_files)}")
                print(f"   출력 파일명: {output_filename}")
                
                # 자막 생성
                from subtitle_utils import generate_subtitles_with_whisper
                
                subtitle_results = []
                
                for i, audio_file in enumerate(tts_audio_files, 1):
                    print(f"📝 [{i}/{len(tts_audio_files)}] 자막 생성 중: {os.path.basename(audio_file)}")
                    
                    try:
                        # 개별 오디오 파일에서 자막 생성
                        subtitle_result = await generate_subtitles_with_whisper(
                            audio_path=audio_file,
                            output_dir="./static/subtitles"
                        )
                        
                        if subtitle_result.get("success"):
                            subtitle_results.append({
                                "audio_file": audio_file,
                                "subtitle_file": subtitle_result["subtitle_file"],
                                "subtitle_url": f"/static/subtitles/{os.path.basename(subtitle_result['subtitle_file'])}",
                                "duration": subtitle_result.get("duration", 0),
                                "subtitle_count": subtitle_result.get("subtitle_count", 0)
                            })
                        else:
                            print(f"⚠️ 자막 생성 실패: {audio_file}")
                            subtitle_results.append({
                                "audio_file": audio_file,
                                "error": subtitle_result.get("error", "알 수 없는 오류")
                            })
                    
                    except Exception as e:
                        print(f"❌ 자막 생성 중 오류: {e}")
                        subtitle_results.append({
                            "audio_file": audio_file,
                            "error": str(e)
                        })
                
                # 성공/실패 통계
                successful_subtitles = [r for r in subtitle_results if "subtitle_file" in r]
                failed_subtitles = [r for r in subtitle_results if "error" in r]
                
                print(f"✅ 자막 생성 완료: {len(successful_subtitles)}개 성공, {len(failed_subtitles)}개 실패")
                
                return {
                    "success": True,
                    "message": f"TTS 오디오에서 자막 생성 완료! {len(successful_subtitles)}개 자막 파일 생성",
                    "subtitle_results": subtitle_results,
                    "successful_subtitles": successful_subtitles,
                    "failed_subtitles": failed_subtitles,
                    "summary": {
                        "total_files": len(tts_audio_files),
                        "successful": len(successful_subtitles),
                        "failed": len(failed_subtitles),
                        "success_rate": f"{(len(successful_subtitles) / len(tts_audio_files)) * 100:.1f}%" if tts_audio_files else "0%"
                    }
                }
                
            except HTTPException:
                raise  # HTTP 예외는 그대로 전달
            except Exception as e:
                print(f"❌ 자막 생성 실패: {e}")
                raise HTTPException(status_code=500, detail=f"자막 생성 실패: {str(e)}")

        # === TTS + 자막 완전 합치기 API 엔드포인트 ===
        @app.post("/video/merge-with-tts-subtitles")  # POST 요청으로 TTS + 자막 완전 합치기
        async def merge_videos_with_tts_and_subtitles(request: dict):  # TTS + 자막 완전 합치기 요청 처리
            """비디오들에 TTS 음성과 자막을 모두 추가한 후 트랜지션과 함께 합치기"""
            try:
                # 요청 데이터 추출
                video_urls = request.get("video_urls", [])  # 비디오 URL 리스트
                tts_scripts = request.get("tts_scripts", [])  # TTS 스크립트 리스트
                transition_type = request.get("transition_type", "fade")  # 트랜지션 타입
                voice_id = request.get("voice_id")  # 음성 ID
                tts_volume = request.get("tts_volume", 0.8)  # TTS 볼륨
                video_volume = request.get("video_volume", 0.3)  # 원본 비디오 볼륨
                add_subtitles = request.get("add_subtitles", True)  # 자막 추가 여부
                enable_bgm = request.get("enable_bgm", True)  # BGM 사용 여부
                bgm_volume = request.get("bgm_volume", 0.2)  # BGM 볼륨
                bgm_file = request.get("bgm_file")  # BGM 파일 경로 (옵션)
                
                # 입력 검증
                if not video_urls:
                    raise HTTPException(status_code=400, detail="video_urls가 필요합니다.")
                
                if not tts_scripts:
                    raise HTTPException(status_code=400, detail="tts_scripts가 필요합니다.")
                
                print(f"🎬 TTS + 자막 완전 합치기 요청 처리 시작...")
                print(f"   비디오 개수: {len(video_urls)}")
                print(f"   TTS 스크립트 수: {len(tts_scripts)}")
                print(f"   트랜지션: {transition_type}")
                print(f"   자막 추가: {add_subtitles}")
                
                # ElevenLabs API 키 확인
                from tts_utils import get_elevenlabs_api_key
                api_key = get_elevenlabs_api_key()
                if not api_key:
                    raise HTTPException(
                        status_code=500, 
                        detail="ElevenLabs API 키가 설정되지 않았습니다."
                    )
                
                # 완전한 비디오 + TTS + 자막 합치기 실행
                from subtitle_utils import merge_video_with_tts_and_subtitles
                
                result = await merge_video_with_tts_and_subtitles(
                    video_urls=video_urls,
                    tts_scripts=tts_scripts,
                    transition_type=transition_type,
                    voice_id=voice_id,
                    tts_volume=tts_volume,
                    video_volume=video_volume,
                    add_subtitles=add_subtitles,
                    api_key=api_key,
                    enable_bgm=enable_bgm,
                    bgm_volume=bgm_volume,
                    bgm_file=bgm_file
                )
                
                if not result.get("success"):
                    raise HTTPException(
                        status_code=500,
                        detail=f"TTS + 자막 완전 합치기 실패: {result.get('error', '알 수 없는 오류')}"
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

        # === OpenAI LLM TTS 스크립트 생성 테스트 엔드포인트 ===
        @app.post("/video/test-llm-tts")  # POST 요청으로 LLM TTS 테스트
        async def test_llm_tts_generation():  # 간단한 LLM TTS 테스트, 전 단계 인자를 넣고 생성
            """OpenAI LLM으로 TTS 스크립트 자동 생성 테스트 (1-4단계 워크플로우 데이터 사용)"""
            try:
                print(f"🧪 OpenAI LLM TTS 스크립트 자동 생성 테스트 시작...")
                
                # 1-4단계 워크플로우 데이터를 활용한 테스트 요청 구성
                test_request = {
                    # 1단계: 페르소나 데이터
                    "persona_description": "20-30대 직장인, 건강에 관심이 많고 시간이 부족한 바쁜 현대인. 온라인 쇼핑을 선호하며 제품 리뷰를 꼼꼼히 확인하는 성향.",
                    
                    # 2단계: 마케팅 인사이트
                    "marketing_insights": "편리함과 건강함을 동시에 추구하는 성향, SNS를 통한 정보 습득 선호, 시간 절약에 높은 가치를 두며 신뢰할 수 있는 브랜드를 선호",
                    
                    # 3단계: 광고 컨셉
                    "ad_concept": "바쁜 일상 속에서도 간편하게 건강을 챙길 수 있는 혁신적인 솔루션 제안. 시간은 절약하고 건강은 업그레이드하는 스마트한 선택",
                    
                    # 4단계: 스토리보드 장면들
                    "storyboard_scenes": [
                        {
                            "scene_number": 1,
                            "description": "바쁜 아침, 시간에 쫓기며 준비하는 직장인의 모습",
                            "prompt_text": "busy office worker rushing in the morning, preparing for work",
                            "duration": 5.0,
                            "emotion": "stressed"
                        },
                        {
                            "scene_number": 2,
                            "description": "제품을 간편하게 섭취하며 만족스러워하는 모습",
                            "prompt_text": "person easily consuming health product with satisfaction",
                            "duration": 5.0,
                            "emotion": "satisfied"
                        },
                        {
                            "scene_number": 3,
                            "description": "활기찬 하루를 보내며 에너지가 넘치는 모습",
                            "prompt_text": "energetic person having a productive day at work",
                            "duration": 5.0,
                            "emotion": "confident"
                        }
                    ],
                    
                    # 추가 설정
                    "product_name": "헬시타임",
                    "brand_name": "웰니스랩",
                    "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel 음성
                    "voice_gender": "female",
                    "voice_language": "ko"
                }
                
                print(f"📋 1-4단계 워크플로우 테스트 데이터:")
                print(f"   1단계 페르소나: {test_request['persona_description'][:50]}...")
                print(f"   2단계 마케팅 인사이트: {test_request['marketing_insights'][:50]}...")
                print(f"   3단계 광고 컨셉: {test_request['ad_concept'][:50]}...")
                print(f"   4단계 스토리보드: {len(test_request['storyboard_scenes'])}개 장면")
                
                # 기존 엔드포인트 재사용
                result = await create_tts_from_storyboard(test_request)
                
                # 테스트 결과에 추가 정보 포함
                result["test_mode"] = True
                result["test_description"] = "1-4단계 워크플로우 데이터 기반 OpenAI LLM TTS 스크립트 자동 생성 테스트"
                result["test_data"] = test_request
                result["workflow_stages"] = {
                    "step1": "타겟 페르소나",
                    "step2": "마케팅 인사이트", 
                    "step3": "광고 컨셉",
                    "step4": "스토리보드 장면"
                }
                
                return result
                
            except Exception as e:
                print(f"❌ LLM TTS 테스트 실패: {e}")
                raise HTTPException(status_code=500, detail=f"LLM TTS 테스트 실패: {str(e)}")

        # === 간단한 텍스트 입력 TTS 생성 엔드포인트 ===
        @app.post("/video/create-simple-tts")  # POST 요청으로 간단한 TTS 생성
        async def create_simple_tts(request: dict):  # 간단한 텍스트로 TTS 생성
            """간단한 텍스트 입력으로 바로 TTS 생성 (LLM 없이)"""
            try:
                # 요청 데이터 추출
                text_input = request.get("text", "")  # 입력 텍스트
                voice_id = request.get("voice_id")  # 음성 ID
                
                if not text_input:
                    raise HTTPException(status_code=400, detail="text가 필요합니다.")
                
                print(f"🎤 간단한 TTS 생성 시작...")
                print(f"   텍스트: {text_input[:100]}{'...' if len(text_input) > 100 else ''}")
                
                # ElevenLabs API 키 확인
                from tts_utils import get_elevenlabs_api_key, create_tts_audio
                api_key = get_elevenlabs_api_key()
                if not api_key:
                    raise HTTPException(
                        status_code=500, 
                        detail="ElevenLabs API 키가 설정되지 않았습니다."
                    )
                
                # TTS 생성
                tts_result = await create_tts_audio(
                    text=text_input,
                    voice_id=voice_id or '21m00Tcm4TlvDq8ikWAM',  # Rachel 기본값
                    api_key=api_key,
                    output_dir="./static/audio"
                )
                
                if tts_result.success:
                    audio_filename = os.path.basename(tts_result.audio_file_path)
                    audio_url = f"/static/audio/{audio_filename}"
                    
                    return {
                        "success": True,
                        "message": "간단한 TTS 생성 완료!",
                        "audio_url": audio_url,
                        "audio_file_path": tts_result.audio_file_path,
                        "duration": tts_result.duration,
                        "file_size": tts_result.file_size,
                        "text": text_input,
                        "voice_id": voice_id or '21m00Tcm4TlvDq8ikWAM'
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"TTS 생성 실패: {tts_result.error}"
                    )
                
            except HTTPException:
                raise
            except Exception as e:
                print(f"❌ 간단한 TTS 생성 실패: {e}")
                raise HTTPException(status_code=500, detail=f"간단한 TTS 생성 실패: {str(e)}")

        # === 스토리보드 → OpenAI LLM → TTS 전용 엔드포인트 ===
        @app.post("/video/storyboard-to-tts")  # POST 요청으로 스토리보드 → LLM → TTS 변환
        async def storyboard_to_tts_conversion(request: dict):  # 스토리보드 → LLM → TTS 전체 프로세스
            """스토리보드 내용을 OpenAI LLM으로 TTS 대본 작성 후 음성 변환"""
            try:
                # 요청 데이터 추출
                storyboard_data = request.get("storyboard_data", {})  # 스토리보드 데이터
                product_name = request.get("product_name", "상품")  # 상품명
                brand_name = request.get("brand_name", "브랜드")  # 브랜드명
                target_audience = request.get("target_audience", "일반 소비자")  # 타겟 고객
                ad_concept = request.get("ad_concept", "매력적인 광고")  # 광고 컨셉
                script_style = request.get("script_style", "친근하고 자연스러운")  # 스크립트 스타일
                voice_id = request.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # 음성 ID (Rachel 기본값)
                output_dir = request.get("output_dir", "./static/audio")  # 출력 디렉토리
                
                # 입력 검증
                if not storyboard_data:
                    raise HTTPException(status_code=400, detail="storyboard_data가 필요합니다.")
                
                print(f"🎬 스토리보드 → OpenAI LLM → TTS 변환 요청 처리 시작...")
                print(f"   상품명: {product_name}")
                print(f"   브랜드명: {brand_name}")
                print(f"   타겟 고객: {target_audience}")
                print(f"   광고 컨셉: {ad_concept}")
                print(f"   스크립트 스타일: {script_style}")
                print(f"   음성 ID: {voice_id}")
                
                # 스토리보드 → LLM → TTS 변환기 import 및 실행
                from storyboard_to_tts import StoryboardToTTSGenerator
                
                generator = StoryboardToTTSGenerator()
                
                # 전체 프로세스 실행
                result = await generator.process_storyboard_to_tts(
                    storyboard_data=storyboard_data,
                    product_name=product_name,
                    brand_name=brand_name,
                    target_audience=target_audience,
                    ad_concept=ad_concept,
                    script_style=script_style,
                    voice_id=voice_id,
                    output_dir=output_dir
                )
                
                if result.get("success"):
                    print(f"✅ 스토리보드 → LLM → TTS 변환 완료!")
                    print(f"   총 {result['successful_count']}개 오디오 파일 생성")
                    
                    return {
                        "success": True,
                        "message": f"스토리보드 → OpenAI LLM → TTS 변환 완료! {result['successful_count']}개 오디오 생성",
                        "storyboard_scenes": result["scenes"],
                        "generated_scripts": result["tts_scripts"],
                        "tts_results": result["results"],
                        "summary": {
                            "total_scenes": len(result["scenes"]),
                            "successful_tts": result["successful_count"],
                            "failed_tts": result["failed_count"],
                            "success_rate": result["success_rate"]
                        },
                        "processing_info": result["processing_info"],
                        "workflow_type": "storyboard_to_tts"
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"스토리보드 → LLM → TTS 변환 실패: {result.get('error', '알 수 없는 오류')}"
                    )
                
            except HTTPException:
                raise  # HTTP 예외는 그대로 전달
            except Exception as e:
                print(f"❌ 스토리보드 → LLM → TTS 변환 실패: {e}")
                raise HTTPException(status_code=500, detail=f"스토리보드 → LLM → TTS 변환 실패: {str(e)}")

        # === 스토리보드 → LLM → TTS 테스트 엔드포인트 ===
        @app.post("/video/test-storyboard-tts")  # POST 요청으로 스토리보드 TTS 테스트
        async def test_storyboard_tts():  # 스토리보드 TTS 테스트 (샘플 데이터 사용)
            """스토리보드 → OpenAI LLM → TTS 변환 테스트 (샘플 데이터)"""
            try:
                # 테스트용 샘플 스토리보드 데이터
                sample_storyboard = {
                    "scenes": [
                        {
                            "scene_number": 1,
                            "description": "밝은 미소를 지으며 제품을 들고 있는 모델의 모습",
                            "image_prompt": "beautiful model holding skincare product with bright smile in natural lighting",
                            "duration": 5.0,
                            "emotion": "happy",
                            "action": "product_introduction"
                        },
                        {
                            "scene_number": 2,
                            "description": "제품을 사용하는 자연스러운 모습, 부드러운 텍스처 강조",
                            "image_prompt": "person applying skincare product gently, smooth texture close-up",
                            "duration": 6.0,
                            "emotion": "satisfied",
                            "action": "product_usage"
                        },
                        {
                            "scene_number": 3,
                            "description": "건강하고 빛나는 피부를 보여주는 클로즈업",
                            "image_prompt": "close-up of healthy glowing skin, natural radiance",
                            "duration": 4.0,
                            "emotion": "confident",
                            "action": "result_showcase"
                        },
                        {
                            "scene_number": 4,
                            "description": "제품 라인업과 브랜드 로고가 나타나는 마무리 장면",
                            "image_prompt": "product lineup display with elegant brand logo",
                            "duration": 5.0,
                            "emotion": "trustworthy",
                            "action": "brand_closing"
                        }
                    ]
                }
                
                # 테스트용 요청 데이터 구성
                test_request = {
                    "storyboard_data": sample_storyboard,
                    "product_name": "글로우 에센스",
                    "brand_name": "네이처뷰티",
                    "target_audience": "20-40대 여성, 자연주의 스킨케어 선호층",
                    "ad_concept": "자연의 힘으로 빛나는 건강한 아름다움",
                    "script_style": "따뜻하고 신뢰감 있는, 자연스러운 톤",
                    "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel 음성
                    "output_dir": "./static/audio"
                }
                
                print(f"🧪 스토리보드 → OpenAI LLM → TTS 변환 테스트 시작...")
                
                # 기존 엔드포인트 재사용
                result = await storyboard_to_tts_conversion(test_request)
                
                # 테스트 결과에 추가 정보 포함
                result["test_mode"] = True
                result["test_description"] = "스토리보드 기반 OpenAI LLM TTS 변환 테스트"
                result["sample_storyboard"] = sample_storyboard
                result["test_settings"] = {
                    "product_name": test_request["product_name"],
                    "brand_name": test_request["brand_name"],
                    "target_audience": test_request["target_audience"],
                    "ad_concept": test_request["ad_concept"],
                    "script_style": test_request["script_style"]
                }
                
                return result
                
            except Exception as e:
                print(f"❌ 스토리보드 TTS 테스트 실패: {e}")
                raise HTTPException(status_code=500, detail=f"스토리보드 TTS 테스트 실패: {str(e)}")

        print("✅ 비디오 기능 추가 완료!")  # 모든 기능 추가 완료 알림
        print("📋 추가된 API 엔드포인트:")  # 추가된 엔드포인트 목록 출력 시작
        print("   - GET  /video/status (상태 확인)")  # 상태 확인 API
        print("   - POST /video/generate-videos (5단계: Runway API 비디오 생성)")  # AI 비디오 생성 API
        print("   - POST /video/merge-with-transitions (6단계: 랜덤 트랜지션 합치기)")  # 생성된 비디오 합치기 API
        print("   - POST /video/merge-user-videos (6-1단계: 사용자 비디오 랜덤 트랜지션 합치기)")  # 사용자 비디오 합치기 API
        print("   - POST /video/merge-with-tts (TTS 포함 비디오 합치기)")  # 단일 비디오 TTS 추가 API
        print("   - POST /video/create-tts-from-storyboard (🎙️ 스토리보드 기반 TTS 생성)")  # 스토리보드 TTS 생성 API
        print("   - POST /video/generate-subtitles (📝 TTS에서 자막(.srt) 생성)")  # 자막 생성 API
        print("   - POST /video/merge-with-tts-subtitles (🎬 TTS+자막 완전 합치기)")  # TTS+자막 완전 합치기 API
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
    print("   - LLM TTS 테스트: http://127.0.0.1:8001/llm-tts-test")  # LLM TTS 테스트 페이지
    
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
    print("   🎲 6-1단계 사용자 비디오 랜덤 트랜지션: POST /video/merge-user-videos")  # 사용자 비디오 랜덤 트랜지션 API 안내
    print("   🎤 TTS 포함 비디오 합치기: POST /video/merge-with-tts")  # 단일 비디오 TTS 추가 API 안내
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
