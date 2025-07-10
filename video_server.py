"""
간소화된 비디오 서버: 트랜지션 및 비디오 합치기 전용
기존 client.py 서버에 비디오 합치기 기능만 추가
"""
import uvicorn  # ASGI 서버 (FastAPI 실행용)
import os  # 운영체제 기능 (파일 경로 등)
import httpx  # HTTP 클라이언트 (비동기 요청용)
from fastapi import FastAPI, HTTPException  # 웹 프레임워크와 예외 처리
from fastapi.staticfiles import StaticFiles  # 정적 파일 서빙용 (CSS, JS, 이미지 등)
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

def add_video_features_to_server():
    """기존 client.py 서버에 비디오 합치기 기능 추가"""
    try:
        # 기존 client.py의 FastAPI app 객체를 import
        from client import app  # client.py에서 생성된 FastAPI 인스턴스 가져오기
        
        # 정적 파일 서빙 설정 (HTML, CSS, JS, 영상 파일 등을 웹에서 접근 가능하게 함)
        app.mount("/static", StaticFiles(directory="static"), name="static")  # /static 경로로 static 폴더 내용 서빙
        
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
                    "POST /video/generate-videos": "5단계: 4단계 이미지 + 설명 → Runway API 영상 생성",  # AI 영상 생성 API
                    "POST /video/merge-with-transitions": "6단계: 생성된 영상들을 랜덤 트랜지션으로 합치기",  # 생성된 영상 합치기 API
                    "POST /video/merge-custom": "사용자 영상 URL로 합치기",  # 사용자 영상 합치기 API
                    "POST /video/merge-user-videos": "6-1단계: 사용자 영상 랜덤 트랜지션 합치기"  # 사용자 영상 랜덤 트랜지션 API
                },
                "features": [  # 제공하는 주요 기능 목록
                    "🎬 9가지 트랜지션 효과 (랜덤 선택)",  # 다양한 트랜지션 효과
                    "🚀 스트리밍 방식 처리 (다운로드 없음)",  # 스트리밍 처리
                    "📱 브라우저에서 바로 재생 가능",  # 웹 브라우저 호환성
                    "🎨 Frame-level animation 지원",  # 프레임 단위 애니메이션
                    "🤖 AI 워크플로우 연동 (1-6단계)",  # AI 워크플로우 통합
                    "🎥 Runway API 영상 생성 (이미지 + 설명)"  # Runway API 연동
                ]
            }

        # === 5단계: Runway API 영상 생성 API 엔드포인트 ===
        @app.post("/video/generate-videos")  # POST 요청으로 /video/generate-videos 경로에 접근 시 실행
        async def generate_videos():  # 비동기 함수로 AI 영상 생성 처리
            """5단계: 4단계 이미지 + 설명을 사용하여 Runway API로 영상 생성"""
            
            # client.py의 현재 프로젝트 상태에서 생성된 이미지 정보 가져오기
            try:
                from client import current_project  # client.py에서 관리하는 프로젝트 상태 import
                
                if not current_project.get("storyboard"):  # 스토리보드가 없으면 에러
                    raise HTTPException(  # HTTP 400 에러 발생
                        status_code=400,  # 잘못된 요청 상태 코드
                        detail="먼저 client.py에서 1-4단계(스토리보드 생성 및 이미지 생성)를 완료해주세요."  # 에러 메시지
                    )
                
                print("📋 5단계: 4단계에서 생성된 이미지들과 설명을 확인합니다...")  # 작업 시작 알림
                
                # 스토리보드에서 이미지와 설명 추출
                scenes = current_project["storyboard"]  # 스토리보드 데이터 가져오기
                generated_videos = []  # 생성된 영상 정보를 저장할 리스트
                
                print(f"🎬 총 {len(scenes)}개 장면의 영상을 생성합니다...")  # 총 장면 개수 출력
                
                for i, scene in enumerate(scenes):  # 각 장면에 대해 순차적으로 처리
                    image_path = scene.get("image_path", "")  # 장면의 이미지 경로 추출 (기본값: 빈 문자열)
                    description = scene.get("description", "")  # 장면의 설명 추출 (기본값: 빈 문자열)
                    
                    if not image_path or not description:  # 이미지 경로나 설명이 없으면
                        print(f"⚠️ 장면 {i+1}: 이미지 또는 설명이 누락되었습니다.")  # 경고 메시지 출력
                        continue  # 다음 장면으로 넘어감
                    
                    print(f"🎥 장면 {i+1} 영상 생성 중...")  # 현재 처리 중인 장면 번호 출력
                    print(f"   📷 이미지: {image_path}")  # 사용할 이미지 경로 출력
                    print(f"   📝 설명: {description}")  # 사용할 설명 출력
                    
                    # TODO: 실제 Runway API 호출로 영상 생성
                    # 현재는 개발 단계이므로 모킹된 결과 반환
                    mock_video_url = f"https://example.com/videos/generated_scene_{i+1}.mp4"  # 가짜 영상 URL 생성
                    
                    video_result = {  # 영상 생성 결과 정보 객체
                        "scene_id": i + 1,  # 장면 번호 (1부터 시작)
                        "image_path": image_path,  # 소스 이미지 경로
                        "description": description,  # 영상 설명
                        "video_url": mock_video_url,  # 생성된 영상 URL (현재는 모킹)
                        "status": "completed",  # 생성 상태: 완료
                        "duration": 3.0  # 영상 길이: 3초
                    }
                    
                    generated_videos.append(video_result)  # 결과 리스트에 추가
                    print(f"✅ 장면 {i+1} 영상 생성 완료: {mock_video_url}")  # 완료 메시지 출력
                
                # 결과를 current_project에 저장 (다음 단계에서 사용하기 위해)
                current_project["generated_videos"] = generated_videos  # 생성된 영상 정보 저장
                
                print(f"🎉 5단계 완료: 총 {len(generated_videos)}개 영상이 생성되었습니다!")  # 전체 완료 메시지
                
                return {  # API 응답 반환
                    "step": "5단계_영상_생성",  # 현재 단계
                    "status": "success",  # 처리 상태: 성공
                    "message": f"총 {len(generated_videos)}개 영상이 성공적으로 생성되었습니다.",  # 성공 메시지
                    "generated_videos": generated_videos,  # 생성된 영상 리스트
                    "next_step": "6단계: /video/merge-with-transitions 엔드포인트를 호출하여 영상을 합치세요."  # 다음 단계 안내
                }
                
            except ImportError:  # client.py 파일을 찾을 수 없는 경우
                raise HTTPException(  # HTTP 500 에러 발생
                    status_code=500,  # 서버 내부 오류 상태 코드
                    detail="client.py를 찾을 수 없습니다. 워크플로우를 먼저 실행해주세요."  # 에러 메시지
                )
            except Exception as e:  # 기타 모든 예외 처리
                raise HTTPException(  # HTTP 500 에러 발생
                    status_code=500,  # 서버 내부 오류 상태 코드
                    detail=f"5단계 영상 생성 중 오류 발생: {str(e)}"  # 구체적인 에러 메시지 포함
                )

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
                video_urls = [video["video_url"] for video in generated_videos]  # 각 영상의 URL만 추출하여 리스트 생성
                
                print(f"🎬 총 {len(video_urls)}개 영상을 랜덤 트랜지션으로 합칩니다...")  # 합칠 영상 개수 출력
                
                # TODO: 실제 영상 URL들을 사용한 합치기
                # 현재는 개발 단계이므로 샘플 영상들로 대체
                sample_videos = [  # 테스트용 샘플 영상 파일들 (로컬 파일 경로)
                    "d:\\shortpilot\\static\\videos\\temp_video_0.mp4",  # 첫 번째 샘플 영상
                    "d:\\shortpilot\\static\\videos\\temp_video_1.mp4",  # 두 번째 샘플 영상
                    "d:\\shortpilot\\static\\videos\\temp_video_2.mp4"   # 세 번째 샘플 영상
                ]
                
                print("⚠️ 임시로 샘플 영상들을 사용합니다 (실제 Runway API 연동 예정)")  # 개발 단계 알림
                
                # 랜덤 트랜지션으로 영상 합치기 실행
                merger = create_merger_instance(use_static_dir=True)  # 영상 합치기 객체 생성 (static 디렉토리 사용)
                output_filename = generate_output_filename("merged_ai_videos")  # 타임스탬프 포함 출력 파일명 생성
                
                final_video_path = merger.merge_videos_with_frame_transitions(  # 프레임 단위 트랜지션으로 영상 합치기 실행
                    sample_videos,  # 합칠 영상 파일 리스트
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

        print("✅ 비디오 기능 추가 완료!")  # 모든 기능 추가 완료 알림
        print("📋 추가된 API 엔드포인트:")  # 추가된 엔드포인트 목록 출력 시작
        print("   - GET  /video/status (상태 확인)")  # 상태 확인 API
        print("   - POST /video/generate-videos (5단계: Runway API 영상 생성)")  # AI 영상 생성 API
        print("   - POST /video/merge-with-transitions (6단계: 랜덤 트랜지션 합치기)")  # 생성된 영상 합치기 API
        print("   - POST /video/merge-user-videos (6-1단계: 사용자 영상 랜덤 트랜지션 합치기)")  # 사용자 영상 합치기 API
        
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
    print("   🤖 5단계 AI 영상 생성: POST /video/generate-videos")  # AI 영상 생성 API 안내
    print("   🎬 6단계 랜덤 트랜지션 합치기: POST /video/merge-with-transitions")  # 생성된 영상 합치기 API 안내
    print("   📱 사용자 영상 합치기: POST /video/merge-custom")  # 사용자 영상 합치기 API 안내
    print("   🎲 6-1단계 사용자 영상 랜덤 트랜지션: POST /video/merge-user-videos")  # 사용자 영상 랜덤 트랜지션 API 안내
    
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
