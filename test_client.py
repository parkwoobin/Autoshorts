import requests
import json
from typing import List

class VideoGenerationClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def get_status(self):
        """프로젝트 상태 확인"""
        try:
            response = requests.get(f"{self.base_url}/project")
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"서버 연결 실패: {e}"}
    
    def set_target_customer(self, country: str, age_range: str, gender: str, language: str, interests: List[str]):
        """1단계: 타겟 고객 정보 설정"""
        data = {
            "country": country,
            "age_range": [age_range],  # 문자열을 리스트로 변환
            "gender": gender,
            "language": language,
            "interests": interests
        }
        
        try:
            response = requests.post(f"{self.base_url}/step1/target-customer", json=data)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"요청 실패: {e}"}
    
    def get_example_prompts(self):
        """2단계: 예시 프롬프트 가져오기"""
        try:
            response = requests.get(f"{self.base_url}/step2/example-prompts")
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"요청 실패: {e}"}
    
    def set_video_input(self, description: str):
        """2단계: 사용자 비디오 입력 설정"""
        data = {"user_description": description}  # 올바른 필드명으로 수정
        
        try:
            response = requests.post(f"{self.base_url}/step2/video-input", json=data)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"요청 실패: {e}"}
    
    def generate_storyboard(self):
        """3단계: 스토리보드 생성"""
        try:
            response = requests.post(f"{self.base_url}/step3/generate-storyboard")
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"요청 실패: {e}"}
    
    def generate_images(self):
        """4단계: 스토리보드 이미지 생성"""
        try:
            # 타임아웃을 5분으로 설정 (Runway API 처리 시간 고려)
            response = requests.post(f"{self.base_url}/step4/generate-images", timeout=300)
            return response.json()
        except requests.exceptions.Timeout:
            return {"error": "요청 시간 초과 (5분) - Runway API 처리가 오래 걸리고 있습니다."}
        except requests.exceptions.RequestException as e:
            return {"error": f"요청 실패: {e}"}

def print_separator():
    print("=" * 60)

def print_json_pretty(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))

def get_user_input_step1():
    """1단계 사용자 입력 받기"""
    print("\n🎯 1단계: 타겟 고객 정보 입력")
    print_separator()
    
    print("목표 고객을 설정해주세요:")
    
    # 국가 선택
    countries = ["한국", "미국", "일본", "중국", "영국", "독일", "프랑스", "기타"]
    print("\n📍 국가를 선택하세요:")
    for i, country in enumerate(countries, 1):
        print(f"{i}. {country}")
    
    while True:
        try:
            choice = int(input("선택 (번호): "))
            if 1 <= choice <= len(countries):
                if choice == len(countries):  # 기타
                    country = input("국가명을 직접 입력하세요: ")
                else:
                    country = countries[choice - 1]
                break
            else:
                print("올바른 번호를 선택하세요.")
        except ValueError:
            print("숫자를 입력하세요.")
    
    # 연령대 선택
    age_ranges = ["10대", "20대", "30대", "40대", "50대", "60대 이상"]
    print("\n👥 연령대를 선택하세요:")
    for i, age in enumerate(age_ranges, 1):
        print(f"{i}. {age}")
    
    while True:
        try:
            choice = int(input("선택 (번호): "))
            if 1 <= choice <= len(age_ranges):
                age_range = age_ranges[choice - 1]
                break
            else:
                print("올바른 번호를 선택하세요.")
        except ValueError:
            print("숫자를 입력하세요.")
    
    # 성별 선택
    genders = ["남성", "여성", "전체"]
    print("\n⚤ 성별을 선택하세요:")
    for i, gender in enumerate(genders, 1):
        print(f"{i}. {gender}")
    
    while True:
        try:
            choice = int(input("선택 (번호): "))
            if 1 <= choice <= len(genders):
                gender = genders[choice - 1]
                break
            else:
                print("올바른 번호를 선택하세요.")
        except ValueError:
            print("숫자를 입력하세요.")
    
    # 언어 선택
    languages = ["한국어", "영어", "일본어", "중국어", "스페인어", "기타"]
    print("\n🗣️ 언어를 선택하세요:")
    for i, lang in enumerate(languages, 1):
        print(f"{i}. {lang}")
    
    while True:
        try:
            choice = int(input("선택 (번호): "))
            if 1 <= choice <= len(languages):
                if choice == len(languages):  # 기타
                    language = input("언어를 직접 입력하세요: ")
                else:
                    language = languages[choice - 1]
                break
            else:
                print("올바른 번호를 선택하세요.")
        except ValueError:
            print("숫자를 입력하세요.")
    
    # 관심사 입력
    print("\n💡 고객이 흥미를 가질만한 관심사를 입력하세요:")
    print("(쉼표로 구분하여 여러 개 입력 가능, 예: 패션, 뷰티, 테크)")
    interests_input = input("관심사: ")
    interests = [interest.strip() for interest in interests_input.split(",") if interest.strip()]
    
    return country, age_range, gender, language, interests

def get_user_input_step2(example_prompt):
    """2단계 사용자 입력 받기"""
    print("\n🎬 2단계: 광고 영상 프롬프트 작성")
    print_separator()
    
    print("📋 페르소나 기반 예시 프롬프트:")
    print(example_prompt)
    print_separator()
    
    print("\n✏️ 위 예시를 참고하여 원하는 광고 영상을 설명해주세요:")
    print("(제품/서비스, 메시지, 구성 등을 자유롭게 작성)")
    print()
    
    lines = []
    print("여러 줄 입력 가능합니다. 완료하려면 빈 줄에서 Enter를 두 번 누르세요.")
    print("-" * 50)
    
    empty_line_count = 0
    while True:
        line = input()
        if line == "":
            empty_line_count += 1
            if empty_line_count >= 2:
                break
        else:
            empty_line_count = 0
            lines.append(line)
    
    description = "\n".join(lines)
    
    # 빈 입력인 경우 예시 프롬프트를 그대로 사용
    if not description.strip():
        print("\n💡 입력이 없어서 위의 예시 프롬프트를 그대로 사용합니다.")
        description = example_prompt
    
    return description

def main():
    client = VideoGenerationClient()
    
    print("🎥 영상 생성 프로토타입")
    print("FastAPI 서버가 실행되어 있는지 확인하세요. (http://localhost:8000)")
    print_separator()
    
    # 서버 상태 확인
    status = client.get_status()
    if "error" in status:
        print(f"❌ {status['error']}")
        print("서버를 먼저 실행해주세요: python client.py")
        return
    
    print("✅ 서버 연결 성공!")
    
    try:
        # 1단계: 타겟 고객 설정
        country, age_range, gender, language, interests = get_user_input_step1()
        
        print("\n⏳ 타겟 고객 정보를 설정하고 페르소나를 생성하는 중...")
        result1 = client.set_target_customer(country, age_range, gender, language, interests)
        
        if "error" in result1:
            print(f"❌ 오류: {result1['error']}")
            return
        
        print("\n✅ 1단계 완료!")
        print("\n🎯 생성된 페르소나:")
        print("디버깅 - 응답 구조:", result1.keys())
        print("디버깅 - 전체 응답:", result1)
        
        # 안전한 방식으로 페르소나 출력
        if "persona" in result1 and "persona_description" in result1["persona"]:
            print(result1["persona"]["persona_description"])
        else:
            print("페르소나 정보가 올바르지 않습니다.")
            return
        
        input("\nEnter를 눌러 2단계로 진행하세요...")
        
        # 2단계: 예시 프롬프트 가져오기
        example_result = client.get_example_prompts()
        if "error" in example_result:
            print(f"❌ 오류: {example_result['error']}")
            return
        
        # 2단계: 사용자 프롬프트 입력
        description = get_user_input_step2(example_result["example_prompts"])
        
        print("\n⏳ 사용자 비디오 입력을 처리하는 중...")
        result2 = client.set_video_input(description)
        
        if "error" in result2:
            print(f"❌ 오류: {result2['error']}")
            return
        
        print("\n✅ 2단계 완료!")
        print("\n📝 사용자 입력:")
        print("디버깅 - 2단계 응답 구조:", result2.keys())
        print("디버깅 - 2단계 전체 응답:", result2)
        
        # 안전한 방식으로 사용자 입력 출력
        if "video_input" in result2 and "user_description" in result2["video_input"]:
            print(result2["video_input"]["user_description"])
        else:
            print("사용자 입력 정보가 올바르지 않습니다.")
            return
        
        input("\nEnter를 눌러 3단계로 진행하세요...")
        
        # 3단계: 스토리보드 생성
        print("\n⏳ 스토리보드를 생성하는 중...")
        result3 = client.generate_storyboard()
        
        if "error" in result3:
            print(f"❌ 오류: {result3['error']}")
            return
        
        print("\n✅ 3단계 완료!")
        print("\n🎬 생성된 스토리보드:")
        print_separator()
        
        storyboard = result3["storyboard"]
        print(f"📊 총 장면 수: {len(storyboard['scenes'])}개")
        print(f"🎭 비디오 컨셉: {storyboard.get('video_concept', 'N/A')}")
        print(f"⏱️ 총 지속시간: {storyboard.get('total_duration', 'N/A')}초")
        print()
        
        for i, scene in enumerate(storyboard["scenes"], 1):
            print(f"🎬 장면 {i}")
            # SceneImagePrompt 구조로 직접 접근
            print(f"   🎨 이미지 프롬프트: {scene.get('promptText', 'N/A')}")
            print(f"   📐 비율: {scene.get('ratio', 'N/A')}")
            print(f"   🎲 시드: {scene.get('seed', 'N/A')}")
            print(f"   🖼️ 참조 이미지: {len(scene.get('referenceImages', []))}개")
            print()
        
        input("\nEnter를 눌러 4단계(이미지 생성)로 진행하세요...")
        
        # 4단계: 이미지 생성
        print("\n⏳ Runway API를 사용하여 이미지를 생성하는 중...")
        print("   (이미지 생성에는 30초~3분 정도 소요될 수 있습니다)")
        result4 = client.generate_images()
        
        if "error" in result4:
            print(f"❌ 오류: {result4['error']}")
            return
        
        print("\n✅ 4단계 완료!")
        print("\n🖼️ 생성된 이미지들:")
        print_separator()
        
        if "generated_images" in result4:
            for img in result4["generated_images"]:
                scene_num = img.get("scene_number", "?")
                status = img.get("status", "unknown")
                
                if status == "success":
                    print(f"🎬 장면 {scene_num}: ✅ 성공")
                    print(f"   📸 이미지 URL: {img.get('image_url', 'N/A')}")
                else:
                    print(f"🎬 장면 {scene_num}: ❌ 실패")
                    print(f"   🚫 오류: {img.get('error', 'N/A')}")
                print()
        
        if "summary" in result4:
            summary = result4["summary"]
            print(f"📊 결과 요약:")
            print(f"   총 장면: {summary.get('total_scenes', 0)}개")
            print(f"   성공: {summary.get('successful', 0)}개")
            print(f"   실패: {summary.get('failed', 0)}개")
            print(f"   성공률: {summary.get('success_rate', '0%')}")
        
        print("\n🎉 모든 단계가 완료되었습니다!")
        
    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    main()
