"""
API 테스트 스크립트 - 스토리보드 생성 API의 완전한 워크플로우를 테스트합니다.
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_complete_workflow():
    """전체 워크플로우 테스트"""
    print("=== 스토리보드 생성 API 완전 워크플로우 테스트 ===\n")
    
    # 0. 서버 상태 확인
    print("0. 서버 상태 확인...")
    response = requests.get(f"{BASE_URL}/")
    print(f"서버 응답: {response.json()}\n")
    
    # 1단계: 타겟 고객 정보 설정 (개선된 워크플로우)
    print("1. 타겟 고객 정보 설정 및 페르소나 생성...")
    target_customer = {
        "country": "한국",
        "age_range": ["25-34"],
        "gender": "여성",
        "language": "한국어",
        "interests": ["뷰티", "건강", "라이프스타일"]
    }
    
    response = requests.post(f"{BASE_URL}/step1/target-customer", json=target_customer)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 성공: {result['message']}")
        print(f"페르소나: {result['persona']['persona_description'][:100]}...")
        print(f"제안 테마: {result['persona']['suggested_video_themes']}\n")
    else:
        print(f"❌ 실패: {response.status_code} - {response.text}\n")
        return
    
    # 2단계-1: AI 생성 예시 프롬프트 확인
    print("2-1. AI 생성 예시 프롬프트 확인...")
    response = requests.get(f"{BASE_URL}/step2/example-prompts")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 성공: {result['message']}")
        print(f"예시 개수: {len(result['example_prompts'])}개")
        for i, example in enumerate(result['example_prompts']):
            print(f"  - {example['scenario_title']}: {example['tone_and_manner']}")
        print()
    else:
        print(f"❌ 실패: {response.status_code} - {response.text}\n")
    
    # 2단계-2: 사용자 영상 아이디어 입력
    print("2-2. 사용자 영상 아이디어 입력 및 최적화...")
    user_input = {
        "user_description": "새로운 스킨케어 제품을 소개하는 영상을 만들고 싶어요. 자연스럽고 믿을 수 있는 느낌으로 제품의 효과를 보여주고 싶습니다.",
        "selected_themes": ["감성적 스토리텔링", "라이프스타일 개선"],
        "additional_requirements": "실제 사용 후기와 before/after 비교 장면 포함"
    }
    
    response = requests.post(f"{BASE_URL}/step2/user-video-input", json=user_input)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 성공: {result['message']}")
        print(f"최적화된 프롬프트: {result['optimized_prompt'][:150]}...")
        print(f"주요 장면: {result['key_scenes']}")
        print(f"목표 길이: {result['target_duration']}초\n")
    else:
        print(f"❌ 실패: {response.status_code} - {response.text}\n")
        return
    
    # 3단계: 상세 스토리보드 생성
    print("3. 상세 스토리보드 생성...")
    response = requests.post(f"{BASE_URL}/step3/generate-enhanced-storyboard")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 성공: {result['message']}")
        storyboard = result['storyboard']
        print(f"총 장면 수: {len(storyboard['scenes'])}개")
        print(f"총 재생 시간: {storyboard['total_duration']}초")
        print(f"예상 제작비: {storyboard['budget_estimate']}")
        print(f"추천 플랫폼: {storyboard['target_platforms']}")
        
        print("\n장면별 상세 정보:")
        for scene in storyboard['scenes']:
            print(f"  씬 {scene['scene_number']}: {scene['title']}")
            print(f"    설명: {scene['description'][:80]}...")
            print(f"    시간: {scene['duration_seconds']}초")
            print(f"    카메라: {scene['camera_work']}")
        print()
    else:
        print(f"❌ 실패: {response.status_code} - {response.text}\n")
    
    # 프로젝트 상태 확인
    print("4. 최종 프로젝트 상태 확인...")
    response = requests.get(f"{BASE_URL}/project/status")
    if response.status_code == 200:
        result = response.json()
        print("✅ 프로젝트 상태:")
        for step, completed in result['project_status'].items():
            status = "✅ 완료" if completed else "❌ 미완료"
            print(f"  {step}: {status}")
    else:
        print(f"❌ 실패: {response.status_code} - {response.text}")

if __name__ == "__main__":
    try:
        # 새로운 개선된 워크플로우 테스트
        test_complete_workflow()
        
        print("\n=== 테스트 완료 ===")
        
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        print("서버 실행: python client.py 또는 uvicorn client:app --reload")
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
