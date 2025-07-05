"""
기존 client.py 서버에 영상 생성 기능(5단계)을 추가하는 스크립트
기존 파일들은 전혀 수정하지 않고, 영상 생성 기능만 추가
"""
import uvicorn
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from typing import List

# 기존 client.py의 app을 import해서 확장
import sys
sys.path.append('.')

def add_video_generation_to_existing_server():
    """기존 client.py 서버에 영상 생성 기능 추가"""
    try:
        # 기존 client.py의 app을 import
        from client import app
        
        # 영상 생성 모델들 import
        from video_models import (
            VideoGenerationInput, VideoGenerationResult, 
            ImageToVideoRequest, StoryboardVideoOutput,
            VideoMergeRequest, VideoMergeResult
        )
        
        # 영상 생성 유틸리티 함수들 import
        from video_utils import (
            create_video_with_runway, generate_videos_from_images
        )
        
        # 영상 합치기 유틸리티 import
        from video_merger import merge_storyboard_videos, VideoTransitionMerger
        
        # 정적 파일 서빙 추가
        app.mount("/static", StaticFiles(directory="static"), name="static")
        
        print("🎬 기존 서버에 영상 생성 기능(5단계)을 추가합니다...")
        print("📁 정적 파일 서빙 활성화: /static")
        
        # 5단계 영상 생성 API - 4단계에서 생성된 이미지들을 영상으로 변환

        @app.post("/step5/generate-videos-from-storyboard")
        async def generate_videos_from_storyboard():
            """
            5단계: 4단계에서 생성된 이미지들을 자동으로 영상으로 변환
            """
            # 기존 client.py의 current_project에 접근
            from client import current_project
            import httpx
            
            if not current_project["storyboard"]:
                raise HTTPException(
                    status_code=400, 
                    detail="먼저 1-4단계를 완료해주세요."
                )
            
            print("📸 4단계 이미지 생성 결과를 확인하는 중...")
            
            # 4단계 API를 직접 호출해서 최신 이미지 생성 결과 가져오기
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post("http://127.0.0.1:8000/step4/generate-images")
                    
                    if response.status_code == 200:
                        result = response.json()
                        generated_images = result.get("generated_images", [])
                        
                        # 성공적으로 생성된 이미지 URL들만 추출
                        actual_image_urls = []
                        for img_data in generated_images:
                            if img_data["status"] == "success" and img_data["image_url"]:
                                actual_image_urls.append(img_data["image_url"])
                        
                        if not actual_image_urls:
                            raise HTTPException(
                                status_code=400,
                                detail="4단계에서 성공적으로 생성된 이미지가 없습니다."
                            )
                        
                        print(f"📸 4단계에서 생성된 {len(actual_image_urls)}개 이미지로 영상 생성 시작...")
                        for i, url in enumerate(actual_image_urls):
                            print(f"  - 이미지 {i+1}: {url[:80]}...")
                        
                        request = ImageToVideoRequest(
                            image_urls=actual_image_urls,
                            duration_per_scene=5,  # 5초씩
                            resolution="768:1280",  # 성공한 해상도 설정
                            model="gen3a_turbo"  # 성공한 모델
                        )
                        
                        # generate_videos_from_images 함수를 직접 사용
                        runway_api_key = os.getenv("RUNWAY_API_KEY")
                        if not runway_api_key:
                            raise HTTPException(
                                status_code=500,
                                detail="RUNWAY_API_KEY 환경 변수가 설정되지 않았습니다."
                            )
                        
                        video_results = await generate_videos_from_images(
                            image_urls=request.image_urls,
                            duration_per_scene=request.duration_per_scene,
                            resolution=request.resolution,
                            api_key=runway_api_key
                        )
                        
                        # 성공/실패 통계 계산
                        successful_count = sum(1 for result in video_results if result.status == "success")
                        failed_count = len(video_results) - successful_count
                        total_videos = len(video_results)
                        success_rate = f"{(successful_count / total_videos) * 100:.1f}%" if total_videos > 0 else "0%"
                        
                        return StoryboardVideoOutput(
                            message=f"{len(request.image_urls)}개 이미지의 영상 변환이 완료되었습니다.",
                            generated_videos=video_results,
                            summary={
                                "total_scenes": total_videos,
                                "successful": successful_count,
                                "failed": failed_count,
                                "success_rate": success_rate,
                                "total_duration": f"{successful_count * request.duration_per_scene}초",
                                "resolution": request.resolution,
                                "settings": {
                                    "duration_per_scene": f"{request.duration_per_scene}초",
                                    "resolution": request.resolution,
                                    "model": request.model
                                }
                            }
                        )
                    
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"4단계 이미지 생성 실패: {response.status_code} - {response.text}"
                        )
                        
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"4단계 API 호출 실패: {str(e)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"4단계 결과 처리 실패: {str(e)}"
                )

        @app.get("/step5/generate-videos-from-images-simple")
        async def generate_videos_from_images_simple():
            """
            5단계: 4단계에서 생성된 이미지들로 영상 생성 (GET 방식, 브라우저 테스트용)
            4단계가 실행되지 않았으면 오류 반환
            """
            runway_api_key = os.getenv("RUNWAY_API_KEY")
            if not runway_api_key:
                raise HTTPException(
                    status_code=500,
                    detail="RUNWAY_API_KEY 환경 변수가 설정되지 않았습니다."
                )
            
            # 기존 client.py의 current_project에 접근
            from client import current_project
            
            # 스토리보드가 없으면 오류
            if not current_project["storyboard"]:
                raise HTTPException(
                    status_code=400,
                    detail="먼저 1-4단계를 완료해주세요. 스토리보드가 없습니다."
                )
            
            print("📸 스토리보드가 있습니다. 4단계를 실행하여 최신 이미지를 가져옵니다...")
            try:
                async with httpx.AsyncClient(timeout=300.0) as client:  # 5분 타임아웃
                    response = await client.post("http://127.0.0.1:8000/step4/generate-images")
                    
                    if response.status_code == 200:
                        result = response.json()
                        generated_images = result.get("generated_images", [])
                        
                        # 성공적으로 생성된 이미지 URL들만 추출
                        actual_image_urls = []
                        for img_data in generated_images:
                            if img_data["status"] == "success" and img_data["image_url"]:
                                actual_image_urls.append(img_data["image_url"])
                        
                        if not actual_image_urls:
                            raise HTTPException(
                                status_code=400,
                                detail="4단계에서 성공적으로 생성된 이미지가 없습니다."
                            )
                        
                        print(f"📸 4단계에서 {len(actual_image_urls)}개 이미지를 새로 생성했습니다.")
                        
                        request = ImageToVideoRequest(
                            image_urls=actual_image_urls,
                            duration_per_scene=5,  # 5초씩
                            resolution="768:1280",  # 성공한 해상도 설정
                            model="gen3a_turbo"  # 성공한 모델
                        )
                        
                        # generate_videos_from_images 함수를 직접 사용
                        video_results = await generate_videos_from_images(
                            image_urls=request.image_urls,
                            duration_per_scene=request.duration_per_scene,
                            resolution=request.resolution,
                            api_key=runway_api_key
                        )
                        
                        # 성공/실패 통계 계산
                        successful_count = sum(1 for result in video_results if result.status == "success")
                        failed_count = len(video_results) - successful_count
                        total_videos = len(video_results)
                        success_rate = f"{(successful_count / total_videos) * 100:.1f}%" if total_videos > 0 else "0%"
                        
                        return StoryboardVideoOutput(
                            message=f"{len(request.image_urls)}개 이미지의 영상 변환이 완료되었습니다.",
                            generated_videos=video_results,
                            summary={
                                "total_scenes": total_videos,
                                "successful": successful_count,
                                "failed": failed_count,
                                "success_rate": success_rate,
                                "total_duration": f"{successful_count * request.duration_per_scene}초",
                                "resolution": request.resolution,
                                "settings": {
                                    "duration_per_scene": f"{request.duration_per_scene}초",
                                    "resolution": request.resolution,
                                    "model": request.model
                                }
                            }
                        )
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"4단계 실행 실패: {response.status_code} - {response.text}"
                        )
                        
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"4단계 API 호출 실패: {str(e)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"4단계 결과 처리 실패: {str(e)}"
                )

        @app.get("/step5/video-status")
        async def get_video_generation_status():
            """
            5단계: 영상 생성 기능 상태 확인 및 사용 가능한 엔드포인트 안내
            """
            runway_api_key = os.getenv("RUNWAY_API_KEY")
            
            return {
                "status": "active",
                "message": "영상 생성 및 합치기 기능(5-6단계)이 활성화되었습니다.",
                "api_key_configured": bool(runway_api_key),
                "available_endpoints": {
                    "POST /step5/generate-videos-from-storyboard": "4단계 스토리보드 이미지들을 영상으로 변환",
                    "GET /step5/generate-videos-from-images-simple": "4단계 이미지로 영상 생성 (브라우저 테스트용)",
                    "GET /step5/video-status": "현재 페이지 - 영상 생성 기능 상태 확인",
                    "POST /step6/merge-videos": "5단계에서 생성된 영상들을 랜덤 트랜지션으로 합치기",
                    "GET /step6/merge-videos-simple": "브라우저에서 영상 합치기 테스트",
                    "GET /step6-1/merge-sample-videos": "샘플 영상 URL로 합치기 테스트 (비용 절약)",
                    "GET /step6-1/merge-sample-videos-simple": "스트리밍 영상 합치기 (다운로드 없음)",
                    "GET /step6-1/merge-sample-videos-with-transitions": "랜덤 트랜지션 영상 합치기 (추천)",
                    "POST /step6-1/merge-custom-videos": "사용자 제공 영상 URL들로 합치기",
                    "GET /step6-2/merge-with-frame-animations": "Frame-level animation 트랜지션으로 샘플 영상 합치기 (고급)",
                    "POST /step6-2/merge-custom-videos-frame-animations": "사용자 영상을 frame-level animation 트랜지션으로 합치기",
                    "GET /step6-3/showcase-all-transitions": "모든 트랜지션 효과를 순서대로 보여주는 긴 영상 (데모)"
                },
                "sample_usage": {
                    "browser_test": "http://127.0.0.1:8000/step5/generate-videos-from-images-simple",
                    "merge_test": "http://127.0.0.1:8000/step6/merge-videos-simple",
                    "sample_merge": "http://127.0.0.1:8000/step6-1/merge-sample-videos",
                    "streaming_merge": "http://127.0.0.1:8000/step6-1/merge-sample-videos-simple",
                    "transitions_merge": "http://127.0.0.1:8000/step6-1/merge-sample-videos-with-transitions",
                    "frame_animations": "http://127.0.0.1:8000/step6-2/merge-with-frame-animations",
                    "all_transitions_showcase": "http://127.0.0.1:8000/step6-3/showcase-all-transitions",
                    "api_docs": "http://127.0.0.1:8000/docs"
                },
                "requirements": "4단계(이미지 생성)가 완료되어야 영상 생성이 가능합니다. 6-1단계는 직접 영상 URL로 테스트 가능합니다."
            }

        # 6단계: 영상 합치기 API
        
        @app.post("/step6/merge-videos")
        async def merge_videos_with_transitions():
            """
            6단계: 5단계에서 생성된 영상들을 랜덤 트랜지션 효과와 함께 합치기
            """
            from client import current_project
            import tempfile
            import shutil
            import time
            
            # 5단계 실행하여 영상 생성
            print("🎬 5단계를 실행하여 영상을 생성합니다...")
            try:
                async with httpx.AsyncClient(timeout=600.0) as client:  # 10분 타임아웃
                    response = await client.post("http://127.0.0.1:8000/step5/generate-videos-from-storyboard")
                    
                    if response.status_code == 200:
                        result = response.json()
                        generated_videos = result.get("generated_videos", [])
                        
                        # 성공적으로 생성된 영상들만 추출
                        successful_videos = [
                            video for video in generated_videos 
                            if video.get("status") == "success" and video.get("video_url")
                        ]
                        
                        if not successful_videos:
                            raise HTTPException(
                                status_code=400,
                                detail="5단계에서 성공적으로 생성된 영상이 없습니다."
                            )
                        
                        print(f"🎬 {len(successful_videos)}개의 성공한 영상을 합칩니다.")
                        
                        # 영상 합치기 실행
                        timestamp = int(time.time())
                        output_filename = f"final_advertisement_{timestamp}.mp4"
                        
                        final_video_path = await merge_storyboard_videos(
                            video_results=successful_videos,
                            output_filename=output_filename
                        )
                        
                        # 최종 영상을 프로젝트에 저장
                        if "final_videos" not in current_project:
                            current_project["final_videos"] = []
                        
                        current_project["final_videos"].append({
                            "filename": output_filename,
                            "path": final_video_path,
                            "created_at": timestamp,
                            "source_videos_count": len(successful_videos),
                            "total_duration": f"{len(successful_videos) * 5}초 (예상)"
                        })
                        
                        return {
                            "message": "영상 합치기가 완료되었습니다!",
                            "final_video": {
                                "filename": output_filename,
                                "path": final_video_path,
                                "source_videos_count": len(successful_videos),
                                "created_at": timestamp
                            },
                            "summary": {
                                "total_source_videos": len(successful_videos),
                                "transitions_applied": len(successful_videos) - 1 if len(successful_videos) > 1 else 0,
                                "output_filename": output_filename,
                                "file_path": final_video_path
                            },
                            "source_videos": successful_videos
                        }
                    
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"5단계 영상 생성 실패: {response.status_code} - {response.text}"
                        )
                        
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"5단계 API 호출 실패: {str(e)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"영상 합치기 실패: {str(e)}"
                )

        @app.get("/step6/merge-videos-simple")
        async def merge_videos_simple():
            """
            6단계: 브라우저에서 테스트하기 쉬운 영상 합치기 (GET 방식)
            """
            from client import current_project
            import time
            
            # 먼저 스토리보드가 있는지 확인
            if not current_project["storyboard"]:
                raise HTTPException(
                    status_code=400,
                    detail="먼저 1-4단계를 완료해주세요. 스토리보드가 없습니다."
                )
            
            print("🎬 전체 워크플로우를 실행합니다: 5단계(영상 생성) → 6단계(영상 합치기)")
            
            try:
                # 5단계 실행
                async with httpx.AsyncClient(timeout=600.0) as client:  # 10분 타임아웃
                    print("📹 5단계: 영상 생성 중...")
                    response = await client.post("http://127.0.0.1:8000/step5/generate-videos-from-storyboard")
                    
                    if response.status_code == 200:
                        result = response.json()
                        generated_videos = result.get("generated_videos", [])
                        
                        # 성공적으로 생성된 영상들만 추출
                        successful_videos = [
                            video for video in generated_videos 
                            if video.get("status") == "success" and video.get("video_url")
                        ]
                        
                        if not successful_videos:
                            raise HTTPException(
                                status_code=400,
                                detail="5단계에서 성공적으로 생성된 영상이 없습니다."
                            )
                        
                        print(f"✅ 5단계 완료: {len(successful_videos)}개 영상 생성됨")
                        print("🎬 6단계: 영상 합치기 시작...")
                        
                        # 영상 합치기 실행
                        timestamp = int(time.time())
                        output_filename = f"final_advertisement_{timestamp}.mp4"
                        
                        final_video_path = await merge_storyboard_videos(
                            video_results=successful_videos,
                            output_filename=output_filename
                        )
                        
                        # 최종 영상을 프로젝트에 저장
                        if "final_videos" not in current_project:
                            current_project["final_videos"] = []
                        
                        current_project["final_videos"].append({
                            "filename": output_filename,
                            "path": final_video_path,
                            "created_at": timestamp,
                            "source_videos_count": len(successful_videos),
                            "total_duration": f"{len(successful_videos) * 5}초 (예상)"
                        })
                        
                        return {
                            "message": "🎉 완전한 광고 영상이 생성되었습니다!",
                            "workflow_status": "완료 (1단계~6단계)",
                            "final_video": {
                                "filename": output_filename,
                                "path": final_video_path,
                                "source_videos_count": len(successful_videos),
                                "created_at": timestamp
                            },
                            "summary": {
                                "total_source_videos": len(successful_videos),
                                "transitions_applied": len(successful_videos) - 1 if len(successful_videos) > 1 else 0,
                                "output_filename": output_filename,
                                "file_path": final_video_path
                            },
                            "source_videos": successful_videos,
                            "next_steps": [
                                f"영상 파일 위치: {final_video_path}",
                                "브라우저에서 다운로드하거나 미디어 플레이어로 재생 가능"
                            ]
                        }
                        
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"5단계 영상 생성 실패: {response.status_code} - {response.text}"
                        )
                        
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"워크플로우 실행 실패: {str(e)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"영상 합치기 실패: {str(e)}"
                )

        # 6-1단계: 직접 영상 URL로 합치기 (테스트용)
        
        @app.get("/step6-1/merge-sample-videos")
        async def merge_sample_videos():
            """
            6-1단계: 샘플 영상 URL들을 직접 사용해서 영상 합치기 테스트 (URL 결과 제공)
            """
            import time
            
            # 테스트용 샘플 영상 URL들 (3개 모두 사용)
            sample_video_urls = [
                "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
                "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4",
                "https://dnznrvs05pmza.cloudfront.net/606e42bf-f1c8-4e72-bcd6-58bb3510a83c.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk4ZDU5OTA4MTFmMmUwNCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.__LNtAR_id8J-SlQsxobOGiDLAWgJiESavXTqLlZvSQ"
            ]
            
            print(f"🎬 샘플 영상 {len(sample_video_urls)}개를 스트리밍으로 합칩니다...")
            
            try:
                # 영상 합치기 실행 (static 디렉토리 사용)
                merger = VideoTransitionMerger(use_static_dir=True)
                timestamp = int(time.time())
                output_filename = f"sample_merged_{timestamp}.mp4"
                
                final_video_path = merger.merge_videos_streaming(sample_video_urls, output_filename)
                video_url = merger.get_video_url(output_filename)
                
                return {
                    "message": "🎉 샘플 영상 합치기가 완료되었습니다!",
                    "test_mode": "샘플 영상 URL 사용 (스트리밍)",
                    "video_url": video_url,
                    "final_video": {
                        "filename": output_filename,
                        "url": video_url,
                        "local_path": final_video_path,
                        "source_videos_count": len(sample_video_urls),
                        "created_at": timestamp
                    },
                    "summary": {
                        "total_source_videos": len(sample_video_urls),
                        "output_filename": output_filename,
                        "video_url": video_url,
                        "processing_method": "스트리밍 (다운로드 없음)"
                    },
                    "access": {
                        "direct_url": video_url,
                        "browser_view": f"브라우저에서 {video_url} 접속하여 영상 재생 가능"
                    },
                    "note": "이 기능은 5단계 없이 직접 영상 URL로 테스트하는 용도입니다."
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"샘플 영상 합치기 실패: {str(e)}"
                )

        @app.post("/step6-1/merge-custom-videos")
        async def merge_custom_videos(video_urls: List[str]):
            """
            6-1단계: 사용자가 직접 입력한 영상 URL들을 합치기
            """
            import time
            
            if not video_urls or len(video_urls) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="영상 URL 목록이 비어있습니다."
                )
            
            print(f"🎬 사용자 제공 영상 {len(video_urls)}개를 랜덤 트랜지션으로 합칩니다...")
            
            try:
                # 사용자 영상들을 VideoGenerationResult 형태로 변환
                custom_videos = []
                for i, url in enumerate(video_urls):
                    custom_videos.append({
                        "scene_number": i + 1,
                        "status": "success", 
                        "video_url": url,
                        "duration": 5,  # 기본값
                        "resolution": "768:1280"  # 기본값
                    })
                
                # 영상 합치기 실행
                timestamp = int(time.time())
                output_filename = f"custom_merged_video_{timestamp}.mp4"
                
                final_video_path = await merge_storyboard_videos(
                    video_results=custom_videos,
                    output_filename=output_filename
                )
                
                return {
                    "message": "🎉 사용자 영상 합치기가 완료되었습니다!",
                    "input_mode": "사용자 제공 영상 URL",
                    "final_video": {
                        "filename": output_filename,
                        "path": final_video_path,
                        "source_videos_count": len(custom_videos),
                        "created_at": timestamp
                    },
                    "summary": {
                        "total_source_videos": len(custom_videos),
                        "transitions_applied": len(custom_videos) - 1 if len(custom_videos) > 1 else 0,
                        "output_filename": output_filename,
                        "file_path": final_video_path,
                        "transitions_used": "랜덤 (zoom, pan, slide, fade)"
                    },
                    "source_videos": custom_videos
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"사용자 영상 합치기 실패: {str(e)}"
                )

        @app.get("/step6-1/merge-sample-videos-simple")
        async def merge_sample_videos_simple():
            """
            6-1단계: 샘플 영상을 스트리밍으로 합치기 (다운로드 없음, URL 결과 제공)
            """
            import time
            
            # 테스트용 샘플 영상 URL들 (일부만 사용해서 빠르게 테스트)
            sample_video_urls = [
                "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
                "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4"
            ]
            
            print(f"🎬 샘플 영상 {len(sample_video_urls)}개를 스트리밍으로 합칩니다...")
            
            try:
                # 영상 합치기 실행 (static 디렉토리 사용)
                merger = VideoTransitionMerger(use_static_dir=True)
                timestamp = int(time.time())
                output_filename = f"simple_merged_{timestamp}.mp4"
                
                final_video_path = merger.merge_videos_streaming(sample_video_urls, output_filename)
                video_url = merger.get_video_url(output_filename)
                
                # static 파일은 정리하지 않음
                
                return {
                    "message": "🎉 스트리밍 영상 합치기가 완료되었습니다!",
                    "method": "스트리밍 (다운로드 없음)",
                    "video_url": video_url,
                    "final_video": {
                        "filename": output_filename,
                        "url": video_url,
                        "local_path": final_video_path,
                        "source_videos_count": len(sample_video_urls),
                        "created_at": timestamp
                    },
                    "performance": {
                        "no_download": True,
                        "memory_efficient": True,
                        "processing_time": "단축됨"
                    },
                    "access": {
                        "direct_url": video_url,
                        "browser_view": f"브라우저에서 {video_url} 접속하여 영상 재생 가능"
                    },
                    "note": "다운로드 없이 URL에서 직접 스트리밍으로 처리했습니다."
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"스트리밍 영상 합치기 실패: {str(e)}"
                )

        @app.get("/step6-1/merge-sample-videos-with-transitions")
        async def merge_sample_videos_with_transitions():
            """
            6-1단계: 샘플 영상을 스트리밍으로 합치기 (랜덤 트랜지션 포함)
            """
            import time
            
            # 테스트용 샘플 영상 URL들
            sample_video_urls = [
                "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
                "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4",
                "https://dnznrvs05pmza.cloudfront.net/606e42bf-f1c8-4e72-bcd6-58bb3510a83c.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk4ZDU5OTA4MTFmMmUwNCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.__LNtAR_id8J-SlQsxobOGiDLAWgJiESavXTqLlZvSQ"
            ]
            
            print(f"🎬 샘플 영상 {len(sample_video_urls)}개를 랜덤 트랜지션으로 합칩니다...")
            
            try:
                # 영상 합치기 실행 (랜덤 트랜지션)
                merger = VideoTransitionMerger()
                timestamp = int(time.time())
                output_filename = f"transitions_merged_{timestamp}.mp4"
                
                # static 디렉토리에 저장
                static_path = os.path.join("static", "videos", output_filename)
                os.makedirs(os.path.dirname(static_path), exist_ok=True)
                
                # 임시 파일로 생성 후 static으로 복사
                temp_path = merger.merge_videos_with_transitions(sample_video_urls, output_filename)
                
                # static 디렉토리로 복사
                import shutil
                shutil.copy2(temp_path, static_path)
                
                # 브라우저에서 접근 가능한 URL 생성
                video_url = f"http://127.0.0.1:8001/static/videos/{output_filename}"
                
                merger.cleanup()
                
                return {
                    "message": "🎉 랜덤 트랜지션 영상 합치기가 완료되었습니다!",
                    "method": "스트리밍 + 랜덤 트랜지션",
                    "video_url": video_url,
                    "final_video": {
                        "filename": output_filename,
                        "url": video_url,
                        "local_path": static_path,
                        "source_videos_count": len(sample_video_urls),
                        "created_at": timestamp
                    },
                    "transitions": {
                        "applied": True,
                        "types": ["fade", "zoom", "crossfade"],
                        "count": len(sample_video_urls) - 1 if len(sample_video_urls) > 1 else 0
                    },
                    "access_info": {
                        "direct_url": video_url,
                        "download_url": f"{video_url}?download=true"
                    },
                    "note": "트랜지션이 적용된 영상을 브라우저에서 바로 확인할 수 있습니다."
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"트랜지션 영상 합치기 실패: {str(e)}"
                )
        
        # 6-2단계: frame-level animation 트랜지션으로 영상 합치기
        
        @app.get("/step6-2/merge-with-frame-animations")
        async def merge_videos_with_frame_animations():
            """
            6-2단계: 샘플 영상을 frame-level animation 트랜지션으로 합치기 (고급)
            """
            try:
                from video_merger import VideoTransitionMerger
                import time
                
                # 샘플 영상 URL들 (성공적으로 테스트된 것들)
                sample_video_urls = [
                    "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
                    "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4",
                    "https://dnznrvs05pmza.cloudfront.net/606e42bf-f1c8-4e72-bcd6-58bb3510a83c.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk4ZDU5OTA4MTFmMmUwNCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.__LNtAR_id8J-SlQsxobOGiDLAWgJiESavXTqLlZvSQ"
                ]
                
                print(f"🎬 Frame-level animation 트랜지션으로 {len(sample_video_urls)}개 샘플 영상을 합칩니다...")
                
                # static 디렉토리 사용하여 URL 접근 가능하게 설정
                merger = VideoTransitionMerger(use_static_dir=True)
                
                # 유니크한 파일명 생성
                timestamp = int(time.time())
                output_filename = f"frame_animated_merged_{timestamp}.mp4"
                
                # Frame-level animation으로 영상 합치기
                final_video_path = merger.merge_videos_with_frame_transitions(
                    sample_video_urls, 
                    output_filename
                )
                
                # URL 생성
                video_url = merger.get_video_url(output_filename)
                
                result = {
                    "status": "success",
                    "message": "Frame-level animation 트랜지션으로 영상 합치기 완료!",
                    "final_video_path": final_video_path,
                    "video_url": video_url,
                    "num_videos_merged": len(sample_video_urls),
                    "transition_types": ["zoom_in", "zoom_out", "pan_right", "pan_left", "pan_up", "pan_down", 
                                       "slide_right", "slide_left", "slide_up", "slide_down", 
                                       "rotate_clockwise", "rotate_counter", "scale_grow", "scale_shrink", "fade"],
                    "features": [
                        "🔄 Frame-by-frame zoom transitions (더 강한 효과)",
                        "📱 Smooth pan animations (올바른 방향, 왼쪽→오른쪽, 오른쪽→왼쪽)", 
                        "⬅️ Slide transitions with precise timing (부드러운 곡선)",
                        "🌀 Rotation effects (clockwise/counterclockwise)",
                        "📏 Scale transitions (grow/shrink with smooth curves)",
                        "🎨 OpenCV-powered frame manipulation",
                        "🎬 Professional-grade video effects"
                    ]
                }
                
                print(f"✅ Frame-level animation 합치기 완료!")
                print(f"📺 브라우저에서 확인: {video_url}")
                
                return result
                
            except Exception as e:
                print(f"❌ Frame-level animation 영상 합치기 실패: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "status": "error",
                    "message": f"Frame-level animation 영상 합치기 중 오류 발생: {str(e)}",
                    "error_type": type(e).__name__
                }

        @app.post("/step6-2/merge-custom-videos-frame-animations") 
        async def merge_custom_videos_with_frame_animations(request: VideoMergeRequest):
            """
            6-2단계: 사용자 제공 영상 URL들을 frame-level animation 트랜지션으로 합치기
            """
            try:
                from video_merger import VideoTransitionMerger
                import time
                
                if not request.video_urls:
                    raise HTTPException(status_code=400, detail="video_urls가 비어있습니다.")
                
                print(f"🎬 Frame-level animation 트랜지션으로 {len(request.video_urls)}개 영상을 합칩니다...")
                
                # static 디렉토리 사용하여 URL 접근 가능하게 설정
                merger = VideoTransitionMerger(use_static_dir=True)
                
                # 유니크한 파일명 생성
                timestamp = int(time.time())
                output_filename = f"custom_frame_animated_{timestamp}.mp4"
                
                # Frame-level animation으로 영상 합치기
                final_video_path = merger.merge_videos_with_frame_transitions(
                    request.video_urls, 
                    output_filename
                )
                
                # URL 생성
                video_url = merger.get_video_url(output_filename)
                
                result = {
                    "status": "success",
                    "message": "Frame-level animation 트랜지션으로 사용자 영상 합치기 완료!",
                    "final_video_path": final_video_path,
                    "video_url": video_url,
                    "num_videos_merged": len(request.video_urls),
                    "input_video_urls": request.video_urls,
                    "transition_types": ["zoom_in", "zoom_out", "pan_right", "pan_left", "pan_up", "pan_down", 
                                       "slide_right", "slide_left", "slide_up", "slide_down", 
                                       "rotate_clockwise", "rotate_counter", "scale_grow", "scale_shrink", "fade"],
                    "features": [
                        "🔄 Frame-by-frame zoom transitions (더 강한 효과)",
                        "📱 Smooth pan animations (올바른 방향, 왼쪽→오른쪽, 오른쪽→왼쪽)", 
                        "⬅️ Slide transitions with precise timing (부드러운 곡선)",
                        "🌀 Rotation effects (clockwise/counterclockwise)",
                        "📏 Scale transitions (grow/shrink with smooth curves)",
                        "🎨 OpenCV-powered frame manipulation",
                        "🎬 Professional-grade video effects"
                    ]
                }
                
                print(f"✅ Frame-level animation 사용자 영상 합치기 완료!")
                print(f"📺 브라우저에서 확인: {video_url}")
                
                return result
                
            except Exception as e:
                print(f"❌ Frame-level animation 사용자 영상 합치기 실패: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "status": "error",
                    "message": f"Frame-level animation 사용자 영상 합치기 중 오류 발생: {str(e)}",
                    "error_type": type(e).__name__
                }
        
        # 6-3단계: 모든 트랜지션 쇼케이스 영상 생성 추가
        @app.get("/step6-3/showcase-all-transitions")
        async def showcase_all_transitions():
            """
            6-3단계: 모든 트랜지션 효과를 순서대로 보여주는 긴 영상 생성
            """
            try:
                from video_merger import VideoTransitionMerger
                import time
                
                # 하나의 샘플 영상을 여러 번 사용 (모든 트랜지션을 보여주기 위해)
                base_video_url = "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A"
                
                # 모든 트랜지션 유형 (순서대로 적용)
                all_transitions = [
                    'zoom_in', 'zoom_out', 'pan_right', 'pan_left', 'pan_up', 'pan_down',
                    'slide_right', 'slide_left', 'slide_up', 'slide_down', 
                    'rotate_clockwise', 'rotate_counter', 'scale_grow', 'scale_shrink', 'fade'
                ]
                
                # 트랜지션 개수만큼 영상 URL 복제 (16개 - 첫 번째 + 15가지 트랜지션)
                video_urls = [base_video_url] * 16
                
                print(f"🎬 모든 트랜지션 쇼케이스: {len(all_transitions)}가지 효과를 순서대로 적용합니다...")
                
                # static 디렉토리 사용하여 URL 접근 가능하게 설정
                merger = VideoTransitionMerger(use_static_dir=True)
                
                # 유니크한 파일명 생성
                timestamp = int(time.time())
                output_filename = f"all_transitions_showcase_{timestamp}.mp4"
                
                # 특별한 순차 트랜지션 함수 호출
                final_video_path = merger.create_sequential_showcase(
                    video_urls, 
                    output_filename
                )
                
                # URL 생성
                video_url = merger.get_video_url(output_filename)
                
                result = {
                    "status": "success",
                    "message": "🎬 모든 트랜지션 쇼케이스 영상 생성 완료!",
                    "final_video_path": final_video_path,
                    "video_url": video_url,
                    "total_transitions": len(all_transitions),
                    "transitions_showcase": [
                        {"order": i+1, "transition": trans, "description": get_transition_description(trans)}
                        for i, trans in enumerate(all_transitions)
                    ],
                    "features": [
                        f"🎯 총 {len(all_transitions)}가지 트랜지션 순차 적용",
                        "📱 각 트랜지션별 명확한 구분",
                        "🎬 전문적인 영상 효과 데모",
                        "⏱️ 트랜지션별 1.5초 적용",
                        "🔄 모든 효과를 한 번에 체험 가능"
                    ],
                    "estimated_duration": f"약 {len(video_urls) * 3 + len(all_transitions) * 1.5:.1f}초"
                }
                
                print(f"✅ 모든 트랜지션 쇼케이스 완료!")
                print(f"📺 브라우저에서 확인: {video_url}")
                
                return result
                
            except Exception as e:
                print(f"❌ 트랜지션 쇼케이스 생성 실패: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "status": "error",
                    "message": f"트랜지션 쇼케이스 생성 중 오류 발생: {str(e)}",
                    "error_type": type(e).__name__
                }
        
        def get_transition_description(transition):
            """트랜지션 설명 반환"""
            descriptions = {
                'zoom_in': '줌 인 - 확대에서 원본으로',
                'zoom_out': '줌 아웃 - 원본에서 확대로',
                'pan_right': '팬 우측 - 왼쪽에서 오른쪽으로',
                'pan_left': '팬 좌측 - 오른쪽에서 왼쪽으로',
                'pan_up': '팬 상단 - 아래에서 위로',
                'pan_down': '팬 하단 - 위에서 아래로',
                'rotate_clockwise': '시계방향 회전',
                'rotate_counter': '반시계방향 회전',
                'fade': '페이드 - 기본 페이드 인/아웃'
            }
            return descriptions.get(transition, transition)

        print("✅ 영상 생성 및 합치기 기능(5-6단계) 추가 완료!")
        print("📋 추가된 API 엔드포인트:")
        print("   - POST /step5/generate-videos-from-storyboard (5단계: 영상 생성)")
        print("   - GET  /step5/generate-videos-from-images-simple (5단계: 브라우저 테스트용)")
        print("   - GET  /step5/video-status (상태 확인)")
        print("   - POST /step6/merge-videos (6단계: 영상 합치기)")
        print("   - GET  /step6/merge-videos-simple (6단계: 브라우저 영상 합치기 테스트)")
        print("   - GET  /step6-1/merge-sample-videos (6-1단계: 샘플 영상으로 테스트)")
        print("   - GET  /step6-1/merge-sample-videos-simple (6-1단계: 스트리밍, 다운로드 없음)")
        print("   - GET  /step6-1/merge-sample-videos-with-transitions (6-1단계: 랜덤 트랜지션 ⭐)")
        print("   - POST /step6-1/merge-custom-videos (6-1단계: 사용자 영상 URL로 테스트)")
        print("   - GET  /step6-2/merge-with-frame-animations (6-2단계: 프레임 애니메이션 트랜지션)")
        print("   - POST /step6-2/merge-custom-videos-frame-animations (6-2단계: 사용자 영상 프레임 애니메이션)")
        print("   - GET  /step6-3/showcase-all-transitions (6-3단계: 모든 트랜지션 쇼케이스)")
        print("⚠️  주의: 4단계(이미지 생성)가 완료되어야 영상 생성이 가능합니다.")
        print("💡 비용 절약: 6-1단계로 영상 합치기만 테스트할 수 있습니다!")
        print("🚀 성능 개선: 스트리밍 방식으로 다운로드 없이 처리 가능!")
        print("🎬 트랜지션 추가: 랜덤 페이드, 줌, 크로스페이드 효과 적용!")
        
        return app
        
    except ImportError as e:
        print(f"❌ Import 오류: {e}")
        print("필요한 파일들이 없는 것 같습니다.")
        return None
    except Exception as e:
        print(f"❌ 기능 추가 실패: {e}")
        return None

def start_video_server():
    """기존 서버에 영상 생성 기능을 추가하고 시작"""
    print("🎬 기존 Storyboard API 서버에 영상 생성 기능을 추가합니다...")
    print("📋 서버 정보:")
    print("   - 포트: 8001 (기존 서버)")
    print("   - 주소: http://127.0.0.1:8001")
    print("   - API 문서: http://127.0.0.1:8001/docs")
    
    # 환경 변수 확인
    runway_api_key = os.getenv("RUNWAY_API_KEY")
    if runway_api_key:
        print("   ✅ Runway API 키 설정됨")
    else:
        print("   ⚠️  Runway API 키가 설정되지 않음 (.env 파일 확인 필요)")
    
    print("\n� 영상 생성 기능 추가 중...")
    
    # 기존 서버에 영상 생성 기능 추가
    app = add_video_generation_to_existing_server()
    
    if app is None:
        print("❌ 기능 추가에 실패했습니다.")
        return
    
    print("\n🚀 영상 생성/합치기 서버를 포트 8000에서 시작합니다...")
    print("📋 전체 워크플로우:")
    print("   1단계: POST /step1/target-customer")
    print("   2단계: GET  /step2/example-prompts")
    print("   3단계: POST /step2/video-input")
    print("   4단계: POST /step3/generate-storyboard")
    print("   5단계: POST /step4/generate-images")
    print("   🎬 6단계: POST /step5/generate-videos-from-storyboard (영상 생성)")
    print("   🎞️  7단계: GET  /step6/merge-videos-simple (영상 합치기 + 완성!)")
    print("   💡 6-1단계: GET  /step6-1/merge-sample-videos (샘플 영상으로 테스트)")
    print("   🚀 6-2단계: GET  /step6-2/merge-with-frame-animations (고급 트랜지션)")
    
    # 서버 시작 - 포트 8000 고정
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,  # 동적 추가이므로 reload 비활성화
        log_level="info"
    )

if __name__ == "__main__":
    start_video_server()
