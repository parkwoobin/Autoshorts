"""
비디오 서버를 위한 유틸리티 함수들
"""
import time
import os
from typing import List
from video_merger import VideoTransitionMerger

# 공통 샘플 영상 URL들
SAMPLE_VIDEO_URLS = [
    "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
    "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4",
    "https://dnznrvs05pmza.cloudfront.net/606e42bf-f1c8-4e72-bcd6-58bb3510a83c.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk4ZDU5OTA4MTFmMmUwNCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.__LNtAR_id8J-SlQsxobOGiDLAWgJiESavXTqLlZvSQ"
]

def create_merger_instance(use_static_dir: bool = True, enable_bgm: bool = True) -> VideoTransitionMerger:
    """VideoTransitionMerger 인스턴스 생성"""
    return VideoTransitionMerger(use_static_dir=use_static_dir, enable_bgm=enable_bgm)

def generate_output_filename(prefix: str) -> str:
    """타임스탬프를 포함한 출력 파일명 생성"""
    timestamp = int(time.time())
    return f"{prefix}_{timestamp}.mp4"

def create_video_response(message: str, filename: str, video_url: str, 
                         local_path: str, video_count: int, method: str = None):
    """비디오 응답 객체 생성"""
    timestamp = int(time.time())
    response = {
        "message": message,
        "video_url": video_url,
        "final_video": {
            "filename": filename,
            "url": video_url,
            "local_path": local_path,
            "source_videos_count": video_count,
            "created_at": timestamp
        },
        "summary": {
            "total_source_videos": video_count,
            "output_filename": filename,
            "video_url": video_url
        },
        "access": {
            "direct_url": video_url,
            "browser_view": f"브라우저에서 {video_url} 접속하여 영상 재생 가능"
        }
    }
    
    if method:
        response["method"] = method
        response["summary"]["processing_method"] = method
    
    return response

def get_transition_description(transition: str) -> str:
    """트랜지션 설명 반환"""
    descriptions = {
        'zoom_in': '줌 인 - 확대에서 원본으로',
        'zoom_out': '줌 아웃 - 원본에서 확대로',
        'pan_right': '팬 우측 - 왼쪽에서 오른쪽으로',
        'pan_left': '팬 좌측 - 오른쪽에서 왼쪽으로',
        'pan_up': '팬 상단 - 아래에서 위로',
        'pan_down': '팬 하단 - 위에서 아래로',
        'rotate_clockwise': '시계방향 회전',
        'rotate_counter_clockwise': '반시계방향 회전',
        'fade': '페이드 - 기본 페이드 인/아웃'
    }
    return descriptions.get(transition, transition)
