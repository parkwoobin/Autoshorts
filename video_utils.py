"""
영상 생성을 위한 유틸리티 함수들
"""
import asyncio  # 비동기 처리를 위한 모듈
import os  # 환경변수 읽기용
from typing import List, Optional  # 타입 힌트용
from video_models import VideoGenerationResult, VideoConfig  # 데이터 모델 import

async def create_video_with_runway(
    image_url: str,  # 변환할 이미지 URL
    duration: int = VideoConfig.DEFAULT_DURATION,  # 영상 길이 (기본값 5초)
    resolution: str = f"{VideoConfig.RESOLUTION_WIDTH}:{VideoConfig.RESOLUTION_HEIGHT}",  # 해상도 (기본값 768:1280)
    model: str = "gen4_image",  # Runway AI 모델명 (가장 안정적인 버전)
    seed: Optional[int] = None,  # 재현 가능한 결과를 위한 시드값 (선택사항)
    api_key: str = None  # Runway API 인증키
) -> str:  # 리턴: 생성된 영상의 다운로드 URL
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
    import httpx  # HTTP 클라이언트 라이브러리 (requests의 비동기 버전)
    
    if not api_key:  # API 키가 없으면 에러 발생
        raise ValueError("Runway API 키가 필요합니다.")
    
    print(f"🎬 영상 생성 시작 - 길이: {duration}초, 해상도: {resolution}")  # 진행 상황 출력
    print(f"   소스 이미지: {image_url}")  # 처리할 이미지 URL 출력
    
    # Runway API 요청에 필요한 HTTP 헤더 설정
    headers = {
        "Authorization": f"Bearer {api_key}",  # API 키를 Bearer 토큰으로 인증
        "Content-Type": "application/json",  # JSON 형식으로 데이터 전송
        "X-Runway-Version": "2024-11-06"  # API 버전 명시 (안정적인 버전)
    }
    
    # Runway API로 전송할 요청 데이터 구성
    payload = {
        "promptImage": image_url,  # 변환할 소스 이미지 URL
        "model": model,  # 사용할 AI 모델 (gen4_image가 가장 안정적)
        "duration": duration,  # 생성할 영상 길이 (초 단위)
        "ratio": resolution  # 영상 해상도 비율 (width:height 형식)
    }
    
    # 시드값이 제공된 경우 재현 가능한 결과를 위해 추가
    if seed is not None:  # 시드값이 있으면
        payload["seed"] = seed  # 요청 데이터에 시드값 추가
    
    async with httpx.AsyncClient(timeout=120.0) as client:  # HTTP 클라이언트 생성 (120초 타임아웃)
        # 1단계: Runway API에 영상 생성 작업 요청
        response = await client.post(  # POST 요청으로 작업 시작
            "https://api.dev.runwayml.com/v1/image_to_video",  # Runway 영상 생성 API 엔드포인트
            headers=headers,  # 인증 헤더 포함
            json=payload  # 요청 데이터를 JSON으로 전송
        )
        
        if response.status_code != 200:  # 요청이 실패한 경우
            error_msg = f"영상 생성 요청 실패: {response.status_code} - {response.text}"  # 에러 메시지 생성
            print(f"❌ {error_msg}")  # 에러 출력
            print(f"🔍 디버깅 정보:")  # 디버깅용 상세 정보 출력 시작
            print(f"   요청 URL: https://api.dev.runwayml.com/v1/image_to_video")  # 요청한 URL 출력
            print(f"   요청 헤더: {headers}")  # 전송한 헤더 출력
            print(f"   요청 데이터: {payload}")  # 전송한 데이터 출력
            print(f"   응답 상태: {response.status_code}")  # 응답 상태 코드 출력
            print(f"   응답 내용: {response.text}")  # 응답 내용 출력
            try:
                error_json = response.json()  # JSON으로 파싱 시도
                print(f"   응답 JSON: {error_json}")  # 파싱된 JSON 출력
            except:
                print("   JSON 파싱 실패")  # JSON 파싱 실패시 출력
            raise Exception(error_msg)  # 예외 발생으로 함수 종료
        
        task_data = response.json()  # 성공한 응답을 JSON으로 파싱
        task_id = task_data.get("id")  # 작업 ID 추출 (상태 확인에 사용)
        
        if not task_id:  # 작업 ID를 받지 못한 경우
            raise Exception("작업 ID를 받을 수 없습니다.")  # 예외 발생
        
        print(f"   작업 ID: {task_id}")  # 받은 작업 ID 출력
        
        # 2단계: 영상 생성 완료까지 상태 모니터링 (폴링)
        max_attempts = 120  # 최대 시도 횟수 (5초 * 120번 = 10분)
        for attempt in range(max_attempts):  # 최대 시도 횟수만큼 반복
            print(f"   상태 확인 중... ({attempt + 1}/{max_attempts})")  # 현재 시도 횟수 출력
            
            # 작업 상태 확인 API 호출
            status_response = await client.get(  # GET 요청으로 상태 조회
                f"https://api.dev.runwayml.com/v1/tasks/{task_id}",  # 작업 상태 확인 API 엔드포인트
                headers=headers  # 인증 헤더 포함
            )
            
            if status_response.status_code != 200:  # 상태 확인 요청이 실패한 경우
                print(f"❌ 상태 확인 실패: {status_response.status_code}")  # 실패 출력
                await asyncio.sleep(5)  # 5초 대기 후 재시도
                continue  # 다음 반복으로 넘어감
            
            status_data = status_response.json()  # 상태 응답을 JSON으로 파싱
            status = status_data.get("status")  # 작업 상태 추출 (PENDING, RUNNING, SUCCEEDED, FAILED 등)
            progress = status_data.get("progress", 0)  # 진행도 추출 (0-100, 기본값 0)
            
            print(f"   상태: {status}, 진행도: {progress}%")  # 현재 상태와 진행도 출력
            
            if status == "SUCCEEDED":  # 영상 생성이 성공적으로 완료된 경우
                # 생성된 영상 URL 추출
                video_output = status_data.get("output")  # 응답에서 output 필드 추출
                if not video_output:  # output이 없는 경우
                    raise Exception("영상 URL을 찾을 수 없습니다.")  # 예외 발생
                
                # Runway API는 때때로 영상 URL을 리스트로 반환함
                if isinstance(video_output, list) and len(video_output) > 0:  # 리스트인 경우
                    video_url = video_output[0]  # 첫 번째 URL 사용
                else:  # 단일 문자열인 경우
                    video_url = video_output  # 그대로 사용
                
                print(f"✅ 영상 생성 완료: {video_url}")  # 성공 메시지와 URL 출력
                return video_url  # 영상 URL 반환하고 함수 종료
                
            elif status == "FAILED":  # 영상 생성이 실패한 경우
                error_msg = status_data.get("error", "알 수 없는 오류")  # 에러 메시지 추출 (기본값: "알 수 없는 오류")
                print(f"❌ 영상 생성 실패: {error_msg}")  # 실패 메시지 출력
                raise Exception(f"영상 생성 실패: {error_msg}")  # 예외 발생으로 함수 종료
                
            elif status in ["PENDING", "RUNNING"]:  # 아직 진행 중인 경우 (대기 중이거나 실행 중)
                await asyncio.sleep(5)  # 5초 대기
                continue  # 다음 반복으로 넘어가서 다시 상태 확인
            else:  # 알 수 없는 상태인 경우
                print(f"❌ 알 수 없는 상태: {status}")  # 알 수 없는 상태 출력
                raise Exception(f"알 수 없는 작업 상태: {status}")  # 예외 발생
        
        # 최대 시도 횟수를 초과한 경우 (10분 초과)
        print("❌ 영상 생성 시간 초과")  # 타임아웃 메시지 출력
        raise Exception("영상 생성 시간 초과 (10분)")  # 타임아웃 예외 발생

async def generate_videos_from_images(
    image_urls: List[str],  # 변환할 이미지 URL들의 리스트
    duration_per_scene: int = VideoConfig.DEFAULT_DURATION,  # 각 영상의 길이 (기본값 5초)
    resolution: str = f"{VideoConfig.RESOLUTION_WIDTH}:{VideoConfig.RESOLUTION_HEIGHT}",  # 해상도 (기본값 768:1280)
    api_key: str = None  # Runway API 인증키
) -> List[VideoGenerationResult]:  # 리턴: 각 영상 생성 결과를 담은 리스트
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
    if not api_key:  # API 키가 없으면 에러 발생
        raise ValueError("Runway API 키가 필요합니다.")
    
    if not image_urls:  # 이미지 URL 리스트가 비어있으면 에러 발생
        raise ValueError("이미지 URL이 하나 이상 필요합니다.")
    
    results = []  # 각 영상 생성 결과를 저장할 리스트
    successful_count = 0  # 성공한 영상 개수 카운터
    failed_count = 0  # 실패한 영상 개수 카운터
    
    print(f"🎬 총 {len(image_urls)}개 이미지를 영상으로 변환을 시작합니다...")  # 전체 작업 시작 메시지
    print(f"   설정: {duration_per_scene}초씩, {resolution} 해상도")  # 설정 정보 출력
    
    for i, image_url in enumerate(image_urls):  # 각 이미지 URL에 대해 순차적으로 처리
        scene_num = i + 1  # 씬 번호 (1부터 시작)
        print(f"\n⏳ 영상 {scene_num}/{len(image_urls)} 생성 시작...")  # 현재 처리 중인 영상 번호 출력
        
        try:  # 영상 생성 시도
            video_url = await create_video_with_runway(  # 위에서 정의한 함수 호출
                image_url=image_url,  # 현재 처리할 이미지 URL
                duration=duration_per_scene,  # 영상 길이
                resolution=resolution,  # 해상도
                api_key=api_key  # API 키
            )
            
            print(f"✅ 영상 {scene_num} 생성 완료!")  # 성공 메시지 출력
            result = VideoGenerationResult(  # 성공 결과 객체 생성
                scene_number=scene_num,  # 씬 번호
                status="success",  # 상태: 성공
                video_url=video_url,  # 생성된 영상 URL
                error=None,  # 에러 없음
                duration=duration_per_scene,  # 영상 길이
                resolution=resolution  # 해상도
            )
            results.append(result)  # 결과 리스트에 추가
            successful_count += 1  # 성공 카운터 증가
            
        except Exception as e:  # 영상 생성 실패한 경우
            print(f"❌ 영상 {scene_num} 생성 실패: {e}")  # 실패 메시지 출력
            result = VideoGenerationResult(  # 실패 결과 객체 생성
                scene_number=scene_num,  # 씬 번호
                status="failed",  # 상태: 실패
                video_url=None,  # 영상 URL 없음
                error=str(e),  # 에러 메시지 저장
                duration=duration_per_scene,  # 영상 길이 (설정값)
                resolution=resolution  # 해상도 (설정값)
            )
            results.append(result)  # 결과 리스트에 추가 (실패해도 기록)
            failed_count += 1  # 실패 카운터 증가
    
    print(f"\n🎉 영상 생성 완료!")  # 전체 작업 완료 메시지
    print(f"   성공: {successful_count}/{len(image_urls)}")  # 성공/전체 비율 출력
    print(f"   실패: {failed_count}/{len(image_urls)}")  # 실패/전체 비율 출력
    print(f"   총 영상 길이: {successful_count * duration_per_scene}초")  # 성공한 영상들의 총 길이
    
    return results  # 모든 결과 리스트 반환
