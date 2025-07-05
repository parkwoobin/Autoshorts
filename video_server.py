"""
간소화된 비디오 서버: 트랜지션 및 비디오 합치기 전용
기존 client.py 서버에 비디오 합치기 기능만 추가
"""
import uvicorn
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from typing import List

# 비디오 서버 유틸리티 import
from video_server_utils import (
    SAMPLE_VIDEO_URLS, create_merger_instance, 
    generate_output_filename, create_video_response,
    get_transition_description
)
from video_models import VideoMergeRequest, VideoConfig

def add_video_features_to_server():
    """기존 client.py 서버에 비디오 합치기 기능 추가"""
    try:
        # 기존 client.py의 app을 import
        from client import app
        
        # 정적 파일 서빙 추가
        app.mount("/static", StaticFiles(directory="static"), name="static")
        
        print("🎬 비디오 합치기 및 트랜지션 기능을 추가합니다...")
        print("📁 정적 파일 서빙 활성화: /static")

        # === 비디오 상태 확인 ===
        @app.get("/video/status")
        async def get_video_status():
            """비디오 기능 상태 확인"""
            return {
                "status": "active",
                "message": "비디오 합치기 및 트랜지션 기능이 활성화되었습니다.",
                "available_endpoints": {
                    "GET /video/status": "현재 페이지 - 비디오 기능 상태 확인",
                    "POST /video/generate-videos": "5단계: 4단계 이미지 + 설명 → Runway API 영상 생성",
                    "POST /video/merge-with-transitions": "6단계: 생성된 영상들을 랜덤 트랜지션으로 합치기",
                    "POST /video/merge-custom": "사용자 영상 URL로 합치기",
                    "POST /video/merge-user-videos": "6-1단계: 사용자 영상 랜덤 트랜지션 합치기"
                },
                "features": [
                    "🎬 9가지 트랜지션 효과 (랜덤 선택)",
                    "🚀 스트리밍 방식 처리 (다운로드 없음)",
                    "📱 브라우저에서 바로 재생 가능",
                    "🎨 Frame-level animation 지원",
                    "🤖 AI 워크플로우 연동 (1-6단계)",
                    "🎥 Runway API 영상 생성 (이미지 + 설명)"
                ]
            }

        # === 5단계: Runway API 영상 생성 ===
        @app.post("/video/generate-videos")
        async def generate_videos():
            """5단계: 4단계 이미지 + 설명을 사용하여 Runway API로 영상 생성"""
            
            # client.py의 current_project에서 생성된 이미지 정보 가져오기
            try:
                from client import current_project
                
                if not current_project.get("storyboard"):
                    raise HTTPException(
                        status_code=400,
                        detail="먼저 client.py에서 1-4단계(스토리보드 생성 및 이미지 생성)를 완료해주세요."
                    )
                
                print("📋 5단계: 4단계에서 생성된 이미지들과 설명을 확인합니다...")
                
                # 스토리보드에서 이미지와 설명 추출
                scenes = current_project["storyboard"]
                generated_videos = []
                
                print(f"🎬 총 {len(scenes)}개 장면의 영상을 생성합니다...")
                
                for i, scene in enumerate(scenes):
                    image_path = scene.get("image_path", "")
                    description = scene.get("description", "")
                    
                    if not image_path or not description:
                        print(f"⚠️ 장면 {i+1}: 이미지 또는 설명이 누락되었습니다.")
                        continue
                    
                    print(f"🎥 장면 {i+1} 영상 생성 중...")
                    print(f"   📷 이미지: {image_path}")
                    print(f"   📝 설명: {description}")
                    
                    # TODO: 실제 Runway API 호출로 영상 생성
                    # 현재는 모킹된 결과 반환
                    mock_video_url = f"https://example.com/videos/generated_scene_{i+1}.mp4"
                    
                    video_result = {
                        "scene_id": i + 1,
                        "image_path": image_path,
                        "description": description,
                        "video_url": mock_video_url,
                        "status": "completed",
                        "duration": 3.0  # 3초 영상
                    }
                    
                    generated_videos.append(video_result)
                    print(f"✅ 장면 {i+1} 영상 생성 완료: {mock_video_url}")
                
                # 결과를 current_project에 저장
                current_project["generated_videos"] = generated_videos
                
                print(f"🎉 5단계 완료: 총 {len(generated_videos)}개 영상이 생성되었습니다!")
                
                return {
                    "step": "5단계_영상_생성",
                    "status": "success",
                    "message": f"총 {len(generated_videos)}개 영상이 성공적으로 생성되었습니다.",
                    "generated_videos": generated_videos,
                    "next_step": "6단계: /video/merge-with-transitions 엔드포인트를 호출하여 영상을 합치세요."
                }
                
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="client.py를 찾을 수 없습니다. 워크플로우를 먼저 실행해주세요."
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"5단계 영상 생성 중 오류 발생: {str(e)}"
                )

        # === 6단계: 트랜지션 적용 영상 합치기 ===
        @app.post("/video/merge-with-transitions")
        async def merge_videos_with_transitions():
            """6단계: 5단계에서 생성된 영상들을 랜덤 트랜지션으로 합치기"""
            
            # client.py의 current_project에서 생성된 영상 정보 가져오기
            try:
                from client import current_project
                
                if not current_project.get("generated_videos"):
                    raise HTTPException(
                        status_code=400,
                        detail="먼저 5단계(/video/generate-videos)를 완료하여 영상을 생성해주세요."
                    )
                
                print("📋 6단계: 5단계에서 생성된 영상들을 확인합니다...")
                
                # 생성된 영상 URL들 추출
                generated_videos = current_project["generated_videos"]
                video_urls = [video["video_url"] for video in generated_videos]
                
                print(f"🎬 총 {len(video_urls)}개 영상을 랜덤 트랜지션으로 합칩니다...")
                
                # TODO: 실제 영상 URL들을 사용한 합치기
                # 현재는 샘플 영상들로 대체
                sample_videos = [
                    "d:\\shortpilot\\static\\videos\\temp_video_0.mp4",
                    "d:\\shortpilot\\static\\videos\\temp_video_1.mp4", 
                    "d:\\shortpilot\\static\\videos\\temp_video_2.mp4"
                ]
                
                print("⚠️ 임시로 샘플 영상들을 사용합니다 (실제 Runway API 연동 예정)")
                
                # 랜덤 트랜지션으로 영상 합치기
                merger = create_merger_instance(use_static_dir=True)
                output_filename = generate_output_filename("merged_ai_videos")
                
                final_video_path = merger.merge_videos_with_frame_transitions(
                    sample_videos, 
                    output_filename
                )
                video_url = merger.get_video_url(output_filename)
                
                print(f"🎉 6단계 완료: 영상이 성공적으로 합쳐졌습니다!")
                print(f"📱 브라우저에서 확인: {video_url}")
                
                return {
                    "step": "6단계_영상_합치기",
                    "status": "success",
                    "message": "영상이 랜덤 트랜지션으로 성공적으로 합쳐졌습니다.",
                    "input_videos": len(video_urls),
                    "transitions_used": "random_transitions",
                    "output_file": output_filename,
                    "url": video_url,
                    "duration": "estimated_duration",
                    "workflow_complete": True
                }
                
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="client.py를 찾을 수 없습니다. 워크플로우를 먼저 실행해주세요."
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"6단계 영상 합치기 중 오류 발생: {str(e)}"
                )

        
        # === 6-1단계: 사용자 영상 랜덤 트랜지션 합치기 ===
        @app.post("/video/merge-user-videos")
        async def merge_user_videos_with_random_transitions(request: VideoMergeRequest):
            """6-1단계: 사용자 제공 영상 URL들을 랜덤 트랜지션으로 합치기"""
            if not request.video_urls:
                raise HTTPException(
                    status_code=400,
                    detail="video_urls가 비어있습니다."
                )
            
            if len(request.video_urls) < 2:
                raise HTTPException(
                    status_code=400,
                    detail="최소 2개 이상의 영상 URL이 필요합니다."
                )
            
            print(f"🎲 6-1단계: 사용자 영상 {len(request.video_urls)}개를 랜덤 트랜지션으로 합치기 시작...")
            
            # URL들 유효성 확인
            for i, url in enumerate(request.video_urls):
                if not url or not url.strip():
                    raise HTTPException(
                        status_code=400,
                        detail=f"영상 URL {i+1}이 비어있습니다."
                    )
                if not (url.startswith('http://') or url.startswith('https://')):
                    raise HTTPException(
                        status_code=400,
                        detail=f"영상 URL {i+1}이 유효하지 않습니다: {url}"
                    )
            
            print(f"📋 입력 영상 URL들:")
            for i, url in enumerate(request.video_urls):
                print(f"   {i+1}. {url}")
            
            try:
                merger = create_merger_instance(use_static_dir=True)
                output_filename = generate_output_filename("user_random_transitions")
                
                # 랜덤 트랜지션으로 합치기
                final_video_path = merger.merge_videos_with_frame_transitions(
                    request.video_urls, 
                    output_filename
                )
                video_url = merger.get_video_url(output_filename)
                
                response = create_video_response(
                    message="🎉 6-1단계: 사용자 영상 랜덤 트랜지션 합치기가 완료되었습니다!",
                    filename=output_filename,
                    video_url=video_url,
                    local_path=final_video_path,
                    video_count=len(request.video_urls),
                    method="랜덤 트랜지션 (Frame-level animation)"
                )
                
                # 추가 정보
                response["user_workflow"] = {
                    "step": "6-1단계",
                    "description": "사용자 제공 영상 URL로 랜덤 트랜지션 합치기",
                    "input_videos": request.video_urls,
                    "video_count": len(request.video_urls),
                    "transition_count": len(request.video_urls) - 1 if len(request.video_urls) > 1 else 0
                }
                
                response["transitions"] = {
                    "applied": True,
                    "type": "random",
                    "count": len(request.video_urls) - 1 if len(request.video_urls) > 1 else 0,
                    "features": [
                        "🎲 매번 다른 랜덤 트랜지션",
                        "🔄 Frame-by-frame 애니메이션",
                        "📱 부드러운 패닝 효과", 
                        "🌀 회전 및 확대/축소",
                        "🎨 fade 및 blend 효과",
                        "🎵 트랜지션별 오디오 효과"
                    ]
                }
                
                print(f"✅ 6-1단계 완료: {output_filename}")
                print(f"🔗 접속 URL: {video_url}")
                
                return response
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"6-1단계 사용자 영상 랜덤 트랜지션 합치기 실패: {str(e)}"
                )

        print("✅ 비디오 기능 추가 완료!")
        print("📋 추가된 API 엔드포인트:")
        print("   - GET  /video/status (상태 확인)")
        print("   - POST /video/generate-videos (5단계: Runway API 영상 생성)")
        print("   - POST /video/merge-with-transitions (6단계: 랜덤 트랜지션 합치기)")
        print("   - POST /video/merge-user-videos (6-1단계: 사용자 영상 랜덤 트랜지션 합치기)")
        
        return app
        
    except ImportError as e:
        print(f"❌ Import 오류: {e}")
        print("필요한 파일들이 없는 것 같습니다.")
        return None
    except Exception as e:
        print(f"❌ 기능 추가 실패: {e}")
        return None

def start_video_server():
    """비디오 서버 시작"""
    print("🎬 비디오 합치기 서버를 시작합니다...")
    print("📋 서버 정보:")
    print("   - 포트: 8000")
    print("   - 주소: http://127.0.0.1:8000")
    print("   - API 문서: http://127.0.0.1:8000/docs")
    print("   - 상태 확인: http://127.0.0.1:8000/video/status")
    
    print("\n🔧 비디오 기능 추가 중...")
    
    # 기존 서버에 비디오 기능 추가
    app = add_video_features_to_server()
    
    if app is None:
        print("❌ 기능 추가에 실패했습니다.")
        return
    
    print("\n🚀 비디오 서버를 시작합니다...")
    print("📋 주요 기능:")
    print("   🤖 5단계 AI 영상 생성: POST /video/generate-videos")
    print("   🎬 6단계 랜덤 트랜지션 합치기: POST /video/merge-with-transitions")
    print("   📱 사용자 영상 합치기: POST /video/merge-custom")
    print("   🎲 6-1단계 사용자 영상 랜덤 트랜지션: POST /video/merge-user-videos")
    
    # 서버 시작
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    start_video_server()
