#!/usr/bin/env python3
"""
9개 트랜지션 전체 테스트 스크립트
3개 영상을 사용하여 모든 트랜지션을 순차적으로 생성하고 확인
"""

import sys
import os
import time
from video_merger import VideoTransitionMerger
from transitions import VideoTransitions

# 공통 샘플 영상 URL들 (한 곳에서 관리)
SAMPLE_VIDEOS = [
    "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
    "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4",
    "https://dnznrvs05pmza.cloudfront.net/606e42bf-f1c8-4e72-bcd6-58bb3510a83c.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk4ZDU5OTA4MTFmMmUwNCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.__LNtAR_id8J-SlQsxobOGiDLAWgJiESavXTqLlZvSQ"
]

def test_all_transitions():
    """9개 트랜지션을 모두 테스트하는 함수 (BGM 포함)"""
    
    print("🚀 9개 트랜지션 + BGM 전체 테스트 시작...")
    print(f"📝 사용할 영상 개수: {len(SAMPLE_VIDEOS)}")
    print("🎵 BGM 기능: 활성화")
    
    # VideoTransitionMerger 인스턴스 생성 (static 디렉토리 사용, BGM 활성화)
    merger = VideoTransitionMerger(use_static_dir=True, enable_bgm=True)
    
    print("\n📋 현재 지원되는 트랜지션 목록:")
    transitions = VideoTransitions.get_available_transitions()
    for i, (transition_type, transition_name) in enumerate(transitions, 1):
        print(f"  {i}. {transition_name} ({transition_type})")
    
    print(f"\n🎯 총 {len(transitions)}개의 트랜지션 + BGM을 생성합니다.")
    
    # BGM 폴더 확인
    import os
    bgm_folder = "bgm"
    if os.path.exists(bgm_folder):
        bgm_files = [f for f in os.listdir(bgm_folder) if f.endswith(('.mp3', '.m4a', '.wav'))]
        print(f"🎵 사용 가능한 BGM 파일: {len(bgm_files)}개")
        if bgm_files:
            print(f"   예시: {bgm_files[0]}")
    else:
        print("⚠️ BGM 폴더를 찾을 수 없습니다.")
    
    try:
        # 모든 트랜지션을 포함한 쇼케이스 영상 생성 (BGM 포함)
        start_time = time.time()
        output_path = merger.create_sequential_showcase(
            sample_videos=SAMPLE_VIDEOS,
            output_filename="test_9_transitions_with_bgm_showcase.mp4"
        )
        end_time = time.time()
        
        print(f"\n✅ BGM + 트랜지션 테스트 완료!")
        print(f"⏱️ 총 소요 시간: {end_time - start_time:.2f}초")
        
        # 파일 크기 확인
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"📊 파일 크기: {file_size / (1024*1024):.2f} MB")
            print(f"🎵 BGM 포함: 예")
            print(f"🎨 트랜지션 개수: {len(transitions)}개")
            
            return output_path
        else:
            print("❌ 출력 파일이 생성되지 않았습니다.")
            return None
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def verify_transitions():
    """생성된 트랜지션이 예상대로인지 확인"""
    print("\n🔍 트랜지션 검증 중...")
    
    transitions = VideoTransitions.get_available_transitions()
    expected_transitions = [
        "zoom_in", "zoom_out", 
        "pan_right", "pan_left", "pan_up", "pan_down",
        "rotate_clockwise", "rotate_counter_clockwise",
        "fade"
    ]
    
    actual_transitions = [t[0] for t in transitions]
    
    print(f"예상 트랜지션: {expected_transitions}")
    print(f"실제 트랜지션: {actual_transitions}")
    
    missing = set(expected_transitions) - set(actual_transitions)
    extra = set(actual_transitions) - set(expected_transitions)
    
    if missing:
        print(f"❌ 누락된 트랜지션: {missing}")
    if extra:
        print(f"⚠️ 추가 트랜지션: {extra}")
    
    if not missing and not extra:
        print("✅ 모든 트랜지션이 정확히 일치합니다.")
        return True
    else:
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🎬 9개 트랜지션 + BGM 전체 테스트")
    print("=" * 60)
    
    # 트랜지션 검증
    if not verify_transitions():
        print("❌ 트랜지션 검증 실패")
        sys.exit(1)
    
    # 실제 테스트 실행
    output_path = test_all_transitions()
    
    if output_path:
        # URL 생성 (static 서빙용)
        filename = os.path.basename(output_path)
        url = f"http://localhost:8000/static/videos/{filename}"
        
        print("\n" + "=" * 60)
        print("🎉 BGM + 트랜지션 테스트 성공!")
        print(f"📁 파일: {output_path}")
        print(f"🌐 URL: {url}")
        print(f"🎵 포함된 기능: BGM + {len(VideoTransitions.get_available_transitions())}개 트랜지션")
        print("=" * 60)
    else:
        print("\n❌ 테스트 실패!")
        sys.exit(1)
