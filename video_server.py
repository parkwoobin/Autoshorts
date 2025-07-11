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
                    "POST /video/create-tts-from-storyboard": "🎙️ 스토리보드에서 TTS 생성",  # 스토리보드 기반 TTS 생성
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
                    "🎵 스토리보드 기반 내레이션 추가"  # 스토리보드 내레이션
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
            """persona_description, marketing_insights, ad_concept, 스토리보드 scene 설명을 결합하여 TTS 내레이션 생성"""
            try:
                # 요청 데이터 추출
                persona_description = request.get("persona_description", "")  # 페르소나 설명
                marketing_insights = request.get("marketing_insights", "")  # 마케팅 인사이트
                ad_concept = request.get("ad_concept", "")  # 광고 컨셉
                storyboard_scenes = request.get("storyboard_scenes", [])  # 스토리보드 장면들
                voice_id = request.get("voice_id")  # 음성 ID (선택사항)
                voice_gender = request.get("voice_gender", "female")  # 음성 성별
                voice_language = request.get("voice_language", "ko")  # 음성 언어
                
                # 입력 검증
                if not storyboard_scenes:
                    raise HTTPException(status_code=400, detail="storyboard_scenes가 필요합니다.")
                
                print(f"🎙️ 스토리보드 기반 TTS 내레이션 생성 요청 처리 시작...")
                print(f"   페르소나: {persona_description[:50]}{'...' if len(persona_description) > 50 else ''}")
                print(f"   마케팅 인사이트: {marketing_insights[:50]}{'...' if len(marketing_insights) > 50 else ''}")
                print(f"   광고 컨셉: {ad_concept[:50]}{'...' if len(ad_concept) > 50 else ''}")
                print(f"   장면 수: {len(storyboard_scenes)}")
                print(f"   음성 설정: {voice_gender} ({voice_language})")
                
                # ElevenLabs API 키 확인
                from tts_utils import get_elevenlabs_api_key
                api_key = get_elevenlabs_api_key()
                if not api_key:
                    raise HTTPException(
                        status_code=500, 
                        detail="ElevenLabs API 키가 설정되지 않았습니다. .env 파일의 ELEVENLABS_API_KEY를 확인해주세요."
                    )
                
                # 1단계: 각 장면별 TTS 스크립트 생성
                tts_scripts = []
                
                # 인트로 스크립트 생성 (페르소나, 마케팅 인사이트, 광고 컨셉 결합)
                intro_script = ""
                if persona_description:
                    intro_script += f"타겟 고객은 {persona_description}입니다. "
                if marketing_insights:
                    intro_script += f"마케팅 포인트는 {marketing_insights}입니다. "
                if ad_concept:
                    intro_script += f"이 광고의 핵심 컨셉은 {ad_concept}입니다. "
                
                if intro_script:
                    intro_script += "이제 광고 영상을 시작하겠습니다."
                    tts_scripts.append({
                        "scene_number": 0,
                        "script_type": "intro",
                        "text": intro_script,
                        "description": "인트로 - 페르소나, 마케팅 인사이트, 광고 컨셉 소개"
                    })
                
                # 각 장면별 스크립트 생성
                for i, scene in enumerate(storyboard_scenes, 1):
                    scene_text = ""
                    
                    # 장면 정보 추출
                    if isinstance(scene, dict):
                        prompt_text = scene.get("promptText", scene.get("prompt_text", scene.get("description", "")))
                        scene_number = scene.get("scene_number", i)
                        duration = scene.get("duration", 5)
                    else:
                        prompt_text = str(scene)
                        scene_number = i
                        duration = 5
                    
                    if prompt_text:
                        # 장면 설명을 자연스러운 내레이션으로 변환
                        scene_text = f"장면 {scene_number}: {prompt_text}"
                        
                        # 장면 설명을 좀 더 자연스럽게 변환
                        if "A woman" in prompt_text or "woman" in prompt_text:
                            scene_text = prompt_text.replace("A woman", "한 여성이").replace("woman", "여성")
                        elif "A man" in prompt_text or "man" in prompt_text:
                            scene_text = prompt_text.replace("A man", "한 남성이").replace("man", "남성")
                        
                        # 영어 표현을 한국어로 자연스럽게 변환
                        scene_text = scene_text.replace("holding", "들고 있는").replace("using", "사용하는")
                        scene_text = scene_text.replace("with", "와 함께").replace("and", "그리고")
                        
                        tts_scripts.append({
                            "scene_number": scene_number,
                            "script_type": "scene",
                            "text": scene_text,
                            "description": f"장면 {scene_number} 설명",
                            "duration": duration
                        })
                
                # 아웃트로 스크립트 생성
                outro_script = "이상으로 광고 영상을 마치겠습니다. 감사합니다."
                tts_scripts.append({
                    "scene_number": len(storyboard_scenes) + 1,
                    "script_type": "outro",
                    "text": outro_script,
                    "description": "아웃트로 - 광고 마무리"
                })
                
                print(f"✅ 총 {len(tts_scripts)}개의 TTS 스크립트 생성 완료:")
                for script in tts_scripts:
                    print(f"   - {script['description']}: {script['text'][:50]}...")
                
                # 2단계: 각 스크립트를 TTS로 변환
                from tts_utils import create_multiple_tts_audio
                
                # 스크립트 텍스트만 추출
                script_texts = [script["text"] for script in tts_scripts]
                
                print(f"🎤 {len(script_texts)}개 스크립트를 TTS로 변환 중...")
                
                # 다중 TTS 오디오 생성
                tts_results = await create_multiple_tts_audio(
                    text_list=script_texts,
                    voice_id=voice_id,
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
                    "message": f"스토리보드 기반 TTS 내레이션 생성 완료! {len(successful_tts)}개 오디오 파일 생성",
                    "tts_scripts": tts_scripts,
                    "successful_tts": successful_tts,
                    "failed_tts": failed_tts,
                    "summary": {
                        "total_scripts": len(tts_scripts),
                        "successful": len(successful_tts),
                        "failed": len(failed_tts),
                        "success_rate": f"{(len(successful_tts) / len(tts_scripts)) * 100:.1f}%" if tts_scripts else "0%"
                    },
                    "input_data": {
                        "persona_description": persona_description,
                        "marketing_insights": marketing_insights,
                        "ad_concept": ad_concept,
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
    print("   - 포트: 8000")  # 서버가 실행될 포트 번호
    print("   - 주소: http://127.0.0.1:8000")  # 로컬 접속 주소
    print("   - API 문서: http://127.0.0.1:8000/docs")  # FastAPI 자동 생성 API 문서 주소
    print("   - 상태 확인: http://127.0.0.1:8000/video/status")  # 비디오 기능 상태 확인 주소
    
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
        port=8000,  # 서버 포트 번호
        reload=False,  # 코드 변경 시 자동 재시작 비활성화 (프로덕션 모드)
        log_level="info"  # 로그 레벨 설정 (정보 수준)
    )

if __name__ == "__main__":  # 스크립트가 직접 실행될 때만 실행
    start_video_server()  # 비디오 서버 시작 함수 호출
