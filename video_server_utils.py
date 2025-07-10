"""
비디오 서버를 위한 유틸리티 함수들
"""
import time  # 타임스탬프 생성용
import os  # 운영체제 관련 기능 (파일 경로 등)
from typing import List  # 타입 힌트용 (리스트 타입 명시)
from video_merger import VideoTransitionMerger  # 영상 합치기 클래스 import

# 테스트용 샘플 영상 URL들 (Runway API로 생성된 실제 영상들)
SAMPLE_VIDEO_URLS = [
    # 첫 번째 샘플 영상 (CloudFront CDN을 통해 제공)
    "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
    # 두 번째 샘플 영상 (JWT 토큰으로 인증된 URL)
    "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4",
    # 세 번째 샘플 영상 (만료 시간이 설정된 보안 URL)
    "https://dnznrvs05pmza.cloudfront.net/606e42bf-f1c8-4e72-bcd6-58bb3510a83c.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk4ZDU5OTA4MTFmMmUwNCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.__LNtAR_id8J-SlQsxobOGiDLAWgJiESavXTqLlZvSQ"
]

def create_merger_instance(use_static_dir: bool = True, enable_bgm: bool = True) -> VideoTransitionMerger:
    """VideoTransitionMerger 인스턴스 생성"""
    return VideoTransitionMerger(use_static_dir=use_static_dir, enable_bgm=enable_bgm)  # 영상 합치기 객체 생성 후 반환

def generate_output_filename(prefix: str) -> str:
    """타임스탬프를 포함한 출력 파일명 생성"""
    timestamp = int(time.time())  # 현재 시간을 유닉스 타임스탬프로 변환 (정수형)
    return f"{prefix}_{timestamp}.mp4"  # "접두사_타임스탬프.mp4" 형식으로 파일명 생성

def create_video_response(message: str, filename: str, video_url: str, 
                         local_path: str, video_count: int, method: str = None):
    """비디오 응답 객체 생성"""
    timestamp = int(time.time())  # 응답 생성 시간을 타임스탬프로 기록
    response = {  # API 응답으로 보낼 딕셔너리 객체 생성
        "message": message,  # 처리 완료 메시지
        "video_url": video_url,  # 생성된 영상에 접근할 수 있는 URL
        "final_video": {  # 최종 영상에 대한 상세 정보
            "filename": filename,  # 저장된 파일명
            "url": video_url,  # 웹에서 접근 가능한 URL
            "local_path": local_path,  # 서버 내 파일 경로
            "source_videos_count": video_count,  # 원본 영상 개수
            "created_at": timestamp  # 생성 시간 (유닉스 타임스탬프)
        },
        "summary": {  # 처리 결과 요약 정보
            "total_source_videos": video_count,  # 합쳐진 원본 영상 총 개수
            "output_filename": filename,  # 출력 파일명
            "video_url": video_url  # 접근 URL (중복이지만 편의를 위해 포함)
        },
        "access": {  # 영상 접근 방법 안내
            "direct_url": video_url,  # 직접 접근 URL
            "browser_view": f"브라우저에서 {video_url} 접속하여 영상 재생 가능"  # 사용법 안내 메시지
        }
    }
    
    if method:  # 처리 방법이 지정된 경우
        response["method"] = method  # 응답에 처리 방법 정보 추가
        response["summary"]["processing_method"] = method  # 요약에도 처리 방법 추가
    
    return response  # 완성된 응답 객체 반환

def get_transition_description(transition: str) -> str:
    """트랜지션 설명 반환"""
    descriptions = {  # 각 트랜지션 효과에 대한 한국어 설명 딕셔너리
        'zoom_in': '줌 인 - 확대에서 원본으로',  # 확대된 상태에서 원본 크기로 줄어드는 효과
        'zoom_out': '줌 아웃 - 원본에서 확대로',  # 원본 크기에서 확대되는 효과
        'pan_right': '팬 우측 - 왼쪽에서 오른쪽으로',  # 왼쪽에서 시작해서 오른쪽으로 이동하는 효과
        'pan_left': '팬 좌측 - 오른쪽에서 왼쪽으로',  # 오른쪽에서 시작해서 왼쪽으로 이동하는 효과
        'pan_up': '팬 상단 - 아래에서 위로',  # 아래에서 시작해서 위로 이동하는 효과
        'pan_down': '팬 하단 - 위에서 아래로',  # 위에서 시작해서 아래로 이동하는 효과
        'rotate_clockwise': '시계방향 회전',  # 시계 방향으로 회전하는 효과
        'rotate_counter_clockwise': '반시계방향 회전',  # 반시계 방향으로 회전하는 효과
        'fade': '페이드 - 기본 페이드 인/아웃'  # 서서히 나타나거나 사라지는 기본 효과
    }
    return descriptions.get(transition, transition)  # 딕셔너리에서 설명 찾기, 없으면 원본 이름 반환
