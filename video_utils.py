"""
영상 생성을 위한 유틸리티 함수들
"""
import asyncio
import os
from typing import List, Optional
from video_models import VideoGenerationResult, VideoConfig

async def create_video_with_runway(
    image_url: str,
    duration: int = VideoConfig.DEFAULT_DURATION,
    resolution: str = f"{VideoConfig.RESOLUTION_WIDTH}:{VideoConfig.RESOLUTION_HEIGHT}",
    model: str = "gen4_image",  # 성공한 모델 설정
    seed: Optional[int] = None,
    api_key: str = None
) -> str:
    """
    Runway API를 사용하여 이미지를 영상으로 변환
    
    Args:
        image_url: 소스 이미지 URL
        duration: 영상 길이 (초)
        resolution: 해상도 (기본값: 768x1280)
        model: Runway 영상 모델
        seed: 시드값 (선택사항)
        api_key: Runway API 키
        
    Returns:
        str: 생성된 영상 URL
    """
    import httpx
    
    if not api_key:
        raise ValueError("Runway API 키가 필요합니다.")
    
    print(f"🎬 영상 생성 시작 - 길이: {duration}초, 해상도: {resolution}")
    print(f"   소스 이미지: {image_url}")
    
    # 성공한 API 설정 적용
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06"  # 성공한 버전 헤더 추가
    }
    
    # 성공한 payload 구조 적용
    payload = {
        "promptImage": image_url,
        "model": model,  # 파라미터로 받은 모델 사용
        "duration": duration,
        "ratio": resolution  # ratio 필드명 사용
    }
    
    # 시드값이 있으면 추가
    if seed is not None:
        payload["seed"] = seed
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 성공한 엔드포인트 사용
        response = await client.post(
            "https://api.dev.runwayml.com/v1/image_to_video",  # 성공한 엔드포인트
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            error_msg = f"영상 생성 요청 실패: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            print(f"🔍 디버깅 정보:")
            print(f"   요청 URL: https://api.dev.runwayml.com/v1/image_to_video")  # 성공한 엔드포인트
            print(f"   요청 헤더: {headers}")
            print(f"   요청 데이터: {payload}")
            print(f"   응답 상태: {response.status_code}")
            print(f"   응답 내용: {response.text}")
            try:
                error_json = response.json()
                print(f"   응답 JSON: {error_json}")
            except:
                print("   JSON 파싱 실패")
            raise Exception(error_msg)
        
        task_data = response.json()
        task_id = task_data.get("id")
        
        if not task_id:
            raise Exception("작업 ID를 받을 수 없습니다.")
        
        print(f"   작업 ID: {task_id}")
        
        # 2. 작업 상태 확인 (최대 10분 대기) - 성공한 엔드포인트 사용
        max_attempts = 120  # 5초씩 120번 = 10분
        for attempt in range(max_attempts):
            print(f"   상태 확인 중... ({attempt + 1}/{max_attempts})")
            
            status_response = await client.get(
                f"https://api.dev.runwayml.com/v1/tasks/{task_id}",  # 성공한 엔드포인트
                headers=headers
            )
            
            if status_response.status_code != 200:
                print(f"❌ 상태 확인 실패: {status_response.status_code}")
                await asyncio.sleep(5)
                continue
            
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            
            print(f"   상태: {status}, 진행도: {progress}%")
            
            if status == "SUCCEEDED":
                # 성공! 영상 URL 반환
                video_output = status_data.get("output")
                if not video_output:
                    raise Exception("영상 URL을 찾을 수 없습니다.")
                
                # Runway API가 리스트로 반환하는 경우 첫 번째 요소 추출
                if isinstance(video_output, list) and len(video_output) > 0:
                    video_url = video_output[0]
                else:
                    video_url = video_output
                
                print(f"✅ 영상 생성 완료: {video_url}")
                return video_url
                
            elif status == "FAILED":
                error_msg = status_data.get("error", "알 수 없는 오류")
                print(f"❌ 영상 생성 실패: {error_msg}")
                raise Exception(f"영상 생성 실패: {error_msg}")
                
            elif status in ["PENDING", "RUNNING"]:
                # 아직 진행 중, 5초 대기 후 재시도
                await asyncio.sleep(5)
                continue
            else:
                print(f"❌ 알 수 없는 상태: {status}")
                raise Exception(f"알 수 없는 작업 상태: {status}")
        
        # 최대 시도 횟수 초과
        print("❌ 영상 생성 시간 초과")
        raise Exception("영상 생성 시간 초과 (10분)")

async def generate_videos_from_images(
    image_urls: List[str],
    duration_per_scene: int = VideoConfig.DEFAULT_DURATION,
    resolution: str = f"{VideoConfig.RESOLUTION_WIDTH}:{VideoConfig.RESOLUTION_HEIGHT}",
    api_key: str = None
) -> List[VideoGenerationResult]:
    """
    여러 이미지를 순차적으로 영상으로 변환
    
    Args:
        image_urls: 이미지 URL 리스트
        duration_per_scene: 각 영상의 길이 (초)
        resolution: 해상도
        api_key: Runway API 키
        
    Returns:
        List[VideoGenerationResult]: 각 영상 생성 결과
    """
    if not api_key:
        raise ValueError("Runway API 키가 필요합니다.")
    
    if not image_urls:
        raise ValueError("이미지 URL이 하나 이상 필요합니다.")
    
    results = []
    successful_count = 0
    failed_count = 0
    
    print(f"🎬 총 {len(image_urls)}개 이미지를 영상으로 변환을 시작합니다...")
    print(f"   설정: {duration_per_scene}초씩, {resolution} 해상도")
    
    for i, image_url in enumerate(image_urls):
        scene_num = i + 1
        print(f"\n⏳ 영상 {scene_num}/{len(image_urls)} 생성 시작...")
        
        try:
            video_url = await create_video_with_runway(
                image_url=image_url,
                duration=duration_per_scene,
                resolution=resolution,
                api_key=api_key
            )
            
            print(f"✅ 영상 {scene_num} 생성 완료!")
            result = VideoGenerationResult(
                scene_number=scene_num,
                status="success",
                video_url=video_url,
                error=None,
                duration=duration_per_scene,
                resolution=resolution
            )
            results.append(result)
            successful_count += 1
            
        except Exception as e:
            print(f"❌ 영상 {scene_num} 생성 실패: {e}")
            result = VideoGenerationResult(
                scene_number=scene_num,
                status="failed",
                video_url=None,
                error=str(e),
                duration=duration_per_scene,
                resolution=resolution
            )
            results.append(result)
            failed_count += 1
    
    print(f"\n🎉 영상 생성 완료!")
    print(f"   성공: {successful_count}/{len(image_urls)}")
    print(f"   실패: {failed_count}/{len(image_urls)}")
    print(f"   총 영상 길이: {successful_count * duration_per_scene}초")
    
    return results
