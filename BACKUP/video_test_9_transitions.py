#!/usr/bin/env python3
"""
9개 트랜지션 전체 테스트 스크립트
3개 영상을 사용하여 모든 트랜지션을 순차적으로 생성하고 확인
"""

import sys  # 시스템 관련 기능 (종료 코드 등)
import os  # 운영체제 기능 (파일 경로, 디렉토리 등)
import time  # 시간 측정용
from video_merger import VideoTransitionMerger  # 영상 합치기 클래스
from transitions import VideoTransitions  # 트랜지션 효과 클래스

# 테스트용 샘플 영상 URL들 (Runway API로 생성된 실제 영상들)
SAMPLE_VIDEOS = [
    # 첫 번째 샘플 영상 (CloudFront CDN + JWT 토큰 인증)
    "https://dnznrvs05pmza.cloudfront.net/9f36c808-ddef-4670-876b-06a10c531075.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiM2U4Y2FjYmZlOTNhZWM4ZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.vykV2ciAAd-6SzlgVBr2hqqGUeTOPKffdV7dKdSGc7A",
    # 두 번째 샘플 영상 (보안 URL, 만료 시간 설정됨)
    "https://dnznrvs05pmza.cloudfront.net/d947f629-52ee-42c5-a5cc-d4780cd74aff.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiOTI4MWViODUyNzQ2YzIyYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.OfYJy0Tvvh8eVXl7McOQEz5_fJdDZdceG6nD7TIQyt4",
    # 세 번째 샘플 영상 (JWT 토큰으로 인증된 임시 URL)
    "https://dnznrvs05pmza.cloudfront.net/606e42bf-f1c8-4e72-bcd6-58bb3510a83c.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTk4ZDU5OTA4MTFmMmUwNCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc1MTg0NjQwMH0.__LNtAR_id8J-SlQsxobOGiDLAWgJiESavXTqLlZvSQ"
]

def test_all_transitions():
    """9개 트랜지션을 모두 테스트하는 함수 (BGM 포함)"""
    
    print("🚀 9개 트랜지션 + BGM 전체 테스트 시작...")  # 테스트 시작 알림
    print(f"📝 사용할 영상 개수: {len(SAMPLE_VIDEOS)}")  # 사용할 영상 개수 출력
    print("🎵 BGM 기능: 활성화")  # BGM 기능 상태 출력
    
    # VideoTransitionMerger 인스턴스 생성 (static 디렉토리 사용, BGM 기능 활성화)
    merger = VideoTransitionMerger(use_static_dir=True, enable_bgm=True)  # 영상 합치기 객체 생성
    
    print("\n📋 현재 지원되는 트랜지션 목록:")  # 지원되는 트랜지션 출력 시작
    transitions = VideoTransitions.get_available_transitions()  # 사용 가능한 모든 트랜지션 가져오기
    for i, (transition_type, transition_name) in enumerate(transitions, 1):  # 각 트랜지션을 번호와 함께 출력
        print(f"  {i}. {transition_name} ({transition_type})")  # 트랜지션 번호, 이름, 타입 출력
    
    print(f"\n🎯 총 {len(transitions)}개의 트랜지션 + BGM을 생성합니다.")  # 생성할 트랜지션 개수 출력
    
    # BGM 폴더 존재 여부 및 파일 개수 확인
    import os  # os 모듈 임포트 (파일 시스템 접근용)
    bgm_folder = "bgm"  # BGM 파일들이 저장된 폴더명
    if os.path.exists(bgm_folder):  # BGM 폴더가 존재하는지 확인
        bgm_files = [f for f in os.listdir(bgm_folder) if f.endswith(('.mp3', '.m4a', '.wav'))]  # 오디오 파일만 필터링
        print(f"🎵 사용 가능한 BGM 파일: {len(bgm_files)}개")  # BGM 파일 개수 출력
        if bgm_files:  # BGM 파일이 있으면
            print(f"   예시: {bgm_files[0]}")  # 첫 번째 BGM 파일 이름 출력
    else:  # BGM 폴더가 없으면
        print("⚠️ BGM 폴더를 찾을 수 없습니다.")  # 경고 메시지 출력
    
    try:  # 트랜지션 테스트 실행 시도
        # 모든 트랜지션을 포함한 쇼케이스 영상 생성 (BGM 포함)
        start_time = time.time()  # 시작 시간 기록
        output_path = merger.create_sequential_showcase(  # 순차적 쇼케이스 영상 생성
            sample_videos=SAMPLE_VIDEOS,  # 사용할 샘플 영상들
            output_filename="test_9_transitions_with_bgm_showcase.mp4"  # 출력 파일명
        )
        end_time = time.time()  # 종료 시간 기록
        
        print(f"\n✅ BGM + 트랜지션 테스트 완료!")  # 테스트 완료 메시지
        print(f"⏱️ 총 소요 시간: {end_time - start_time:.2f}초")  # 총 소요 시간 출력 (소수점 2자리)
        
        # 생성된 파일의 크기와 정보 확인
        if os.path.exists(output_path):  # 출력 파일이 존재하는지 확인
            file_size = os.path.getsize(output_path)  # 파일 크기 가져오기 (바이트 단위)
            print(f"📊 파일 크기: {file_size / (1024*1024):.2f} MB")  # MB 단위로 변환하여 출력
            print(f"🎵 BGM 포함: 예")  # BGM 포함 여부 출력
            print(f"🎨 트랜지션 개수: {len(transitions)}개")  # 포함된 트랜지션 개수 출력
            
            return output_path  # 성공 시 출력 파일 경로 반환
        else:  # 출력 파일이 없으면
            print("❌ 출력 파일이 생성되지 않았습니다.")  # 실패 메시지 출력
            return None  # 실패 시 None 반환
            
    except Exception as e:  # 예외 발생 시
        print(f"❌ 테스트 실패: {e}")  # 에러 메시지 출력
        import traceback  # 상세한 에러 정보를 위한 traceback 모듈
        traceback.print_exc()  # 전체 에러 스택 출력
        return None  # 실패 시 None 반환

def verify_transitions():
    """생성된 트랜지션이 예상대로인지 확인"""
    print("\n🔍 트랜지션 검증 중...")  # 검증 시작 알림
    
    transitions = VideoTransitions.get_available_transitions()  # 현재 사용 가능한 트랜지션 목록 가져오기
    expected_transitions = [  # 예상되는 트랜지션 목록 (9개)
        "zoom_in", "zoom_out",  # 줌 관련 트랜지션
        "pan_right", "pan_left", "pan_up", "pan_down",  # 패닝 관련 트랜지션
        "rotate_clockwise", "rotate_counter_clockwise",  # 회전 관련 트랜지션
        "fade"  # 페이드 트랜지션
    ]
    
    actual_transitions = [t[0] for t in transitions]  # 실제 트랜지션 타입들만 추출
    
    print(f"예상 트랜지션: {expected_transitions}")  # 예상 트랜지션 목록 출력
    print(f"실제 트랜지션: {actual_transitions}")  # 실제 트랜지션 목록 출력
    
    missing = set(expected_transitions) - set(actual_transitions)  # 누락된 트랜지션 찾기
    extra = set(actual_transitions) - set(expected_transitions)  # 추가된 트랜지션 찾기
    
    if missing:  # 누락된 트랜지션이 있으면
        print(f"❌ 누락된 트랜지션: {missing}")  # 누락된 트랜지션 출력
    if extra:  # 추가된 트랜지션이 있으면
        print(f"⚠️ 추가 트랜지션: {extra}")  # 추가된 트랜지션 출력
    
    if not missing and not extra:  # 누락도 추가도 없으면
        print("✅ 모든 트랜지션이 정확히 일치합니다.")  # 완벽 일치 메시지
        return True  # 검증 성공
    else:  # 차이가 있으면
        return False  # 검증 실패

if __name__ == "__main__":  # 스크립트가 직접 실행될 때만 실행
    print("=" * 60)  # 구분선 출력
    print("🎬 9개 트랜지션 + BGM 전체 테스트")  # 테스트 제목 출력
    print("=" * 60)  # 구분선 출력
    
    # 트랜지션 검증 (예상 트랜지션과 실제 트랜지션 비교)
    if not verify_transitions():  # 트랜지션 검증이 실패하면
        print("❌ 트랜지션 검증 실패")  # 실패 메시지 출력
        sys.exit(1)  # 프로그램 종료 (종료 코드 1: 오류)
    
    # 실제 트랜지션 테스트 실행
    output_path = test_all_transitions()  # 모든 트랜지션 테스트 함수 호출
    
    if output_path:  # 테스트가 성공해서 출력 파일이 생성된 경우
        # 웹 서버용 URL 생성 (static 파일 서빙용)
        filename = os.path.basename(output_path)  # 파일명만 추출 (경로 제거)
        url = f"http://localhost:8000/static/videos/{filename}"  # 로컬 서버 URL 생성
        
        print("\n" + "=" * 60)  # 구분선 출력
        print("🎉 BGM + 트랜지션 테스트 성공!")  # 성공 메시지
        print(f"📁 파일: {output_path}")  # 생성된 파일 경로 출력
        print(f"🌐 URL: {url}")  # 웹에서 접근 가능한 URL 출력
        print(f"🎵 포함된 기능: BGM + {len(VideoTransitions.get_available_transitions())}개 트랜지션")  # 포함된 기능 요약
        print("=" * 60)  # 구분선 출력
    else:  # 테스트가 실패한 경우
        print("\n❌ 테스트 실패!")  # 실패 메시지 출력
        sys.exit(1)  # 프로그램 종료 (종료 코드 1: 오류)
